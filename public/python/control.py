import numpy as np
from scipy.linalg import expm, solve_discrete_are
from scipy.signal import place_poles
from plant import nominal, rk4, jacobian, linearize, C

def discrete_system(p,e,dt):
    xe,ue,A,B=linearize(p,e)
    block=np.zeros((8,8)); block[:6,:6]=A; block[:6,6:]=B
    disc=expm(block*dt)
    return xe,ue,A,B,disc[:6,:6],disc[:6,6:]

def require_stabilizable(A,B):
    for v in np.linalg.eigvals(A):
        if abs(v)>=1-1e-9 and np.linalg.matrix_rank(np.column_stack([v*np.eye(len(A))-A,B]),tol=1e-8)<len(A):
            raise ValueError('Equilibrio no estabilizable: con empuje cero se pierde autoridad lineal sobre yaw. Selecciona elevación distinta de cero (15° recomendado).')

class Controller:
    def __init__(self,c): self.integral=np.zeros(3); self.update(c)
    def update(self,c):
        self.c=c; p=c['nominal']; self.xe,self.ue,self.A,self.B,self.Ad,self.Bd=discrete_system(p,np.deg2rad(c['trim']),c['dt'])
        if c['controller'] in ['lqr','lqi']:
            A=self.Ad; B=self.Bd; Q=np.diag(c['lqrQ'])
            if c['controller']=='lqi':
                A=np.block([[A,np.zeros((6,2))],[C[[0,2]]*c['dt'],np.eye(2)]])
                B=np.vstack([B,np.zeros((2,2))]); Q=np.diag(c['lqrQ']+[c['integralWeight']]*2)
            require_stabilizable(A,B)
            R=np.diag(c['lqrR']); P=solve_discrete_are(A,B,Q,R)
            self.K=np.linalg.solve(R+B.T@P@B,B.T@P@A)
            self.poles=np.abs(np.linalg.eigvals(A-B@self.K)).tolist()
    def command(self,x,ref):
        c=self.c; p=c['nominal']; dt=c['dt']; a,av,r,rv,y,yv=x; limits=False
        err=ref[:,0]-x[[0,4]]
        if c['controller'] in ['lqr','lqi']:
            target=ref[:,0]-self.xe[[0,4]]
            M=np.block([[self.A,self.B],[C[[0,2]],np.zeros((2,2))]])
            steady=np.linalg.solve(M,np.r_[np.zeros(6),target])
            dx=x-self.xe-steady[:6]
            self.old_integral=self.integral.copy()
            self.integral[:2]-=err*dt
            state=np.r_[dx,self.integral[:2]] if c['controller']=='lqi' else dx
            return self.ue+steady[6:]-self.K@state,0.,limits
        kp=np.array(c['kp']); kd=np.array(c['kd']); ki=np.array(c['ki'])
        self.old_integral=self.integral.copy()
        self.integral[:2]+=err*dt
        acc=ref[:,2]+kp[:2]*err+kd[:2]*(ref[:,1]-x[[1,5]])
        if c['controller']=='pid':
            acc+=ki[:2]*self.integral[:2]
            # Local PID cascade, gravity feedforward, yaw -> desired roll.
            uc=(acc[0]+p['k_alpha']*np.sin(ref[0,0]))/p['a_alpha']
            authority=p['a_psi']*uc*np.cos(a)
            raw=(acc[1]/authority) if abs(authority)>.05 else 0.
            limits=abs(authority)<=.05 and abs(acc[1])>1e-5
        else:
            c1=(acc[0]+p['k_alpha']*np.sin(a)+p['b_alpha']*av)/p['a_alpha']
            c2=(acc[1]+p['b_psi']*yv)/(p['a_psi']*max(np.cos(a),.2))
            raw=np.arctan2(c2,c1)
            if raw>np.pi/2: raw-=np.pi
            if raw<-np.pi/2: raw+=np.pi
            uc=c1
        theta=np.clip(raw,-np.deg2rad(c['rollLimit']),np.deg2rad(c['rollLimit']))
        limits=bool(limits or abs(raw-theta)>1e-10)
        if c['controller']=='nonlinear': uc/=max(np.cos(theta),.2)
        self.integral[2]+=(theta-r)*dt
        rd=kp[2]*(theta-r)-kd[2]*rv
        if c['controller']=='pid': rd+=ki[2]*self.integral[2]
        ud=(rd+p['k_theta']*np.sin(r)+(p['b_theta']*rv if c['controller']=='nonlinear' else 0))/p['a_theta']
        return np.array([uc,ud]),float(theta),limits
    def antiwindup(self,limited):
        # Conditional integration: freeze all integrators when any actuator or allocation clips.
        if limited: self.integral=self.old_integral.copy()

class Observer:
    """Receives only measured angles and nominally reconstructed commanded input."""
    def __init__(self,c):
        self.x=np.zeros(6); self.P=np.eye(6)*.03; self.previous_y=None; self.update(c)
    def update(self,c):
        self.c=c
        if c['observer']=='luenberger':
            self.xe,self.ue,_,_,self.Ad,self.Bd=discrete_system(c['nominal'],np.deg2rad(c['trim']),c['dt'])
            poles=np.exp(-c['observerSpeed']*np.array([1,1.2,1.4,1.6,1.8,2])*c['dt'])
            self.L=place_poles(self.Ad.T,(C@self.Ad).T,poles).gain_matrix.T
    def step(self,y,u):
        c=self.c; dt=c['dt']; mode=c['observer']
        if mode=='filtered':
            v=np.zeros(3) if self.previous_y is None else (y-self.previous_y)/dt
            blend=1-np.exp(-dt*c['filterHz']*2*np.pi)
            self.x[::2]=y; self.x[1::2]+=blend*(v-self.x[1::2]); self.previous_y=y.copy()
        elif mode=='luenberger':
            # Innovation y(k+1) relative to the one-step output of x(k).
            prior=self.xe+self.Ad@(self.x-self.xe)+self.Bd@(u-self.ue)
            self.x=prior+self.L@(y-C@prior)
        elif mode=='ekf':
            f=lambda x:rk4(lambda z,v:nominal(z,v,c['nominal']),x,u,dt)
            F=jacobian(f,self.x); xp=f(self.x)
            Q=np.diag([2e-6,8e-4,2e-6,8e-4,2e-6,1.2e-3])*c['ekfQ']*(dt/.02)
            R=np.diag(np.deg2rad(c['ekfR'])**2)
            P=F@self.P@F.T+Q; S=C@P@C.T+R; L=np.linalg.solve(S,C@P).T
            self.x=xp+L@(y-C@xp); J=np.eye(6)-L@C
            self.P=J@P@J.T+L@R@L.T
        return self.x.copy()
