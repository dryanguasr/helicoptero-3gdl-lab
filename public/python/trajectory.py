import numpy as np

# Course convention: (name, beta positive down, gamma). Serialized v1 routes
# retain their original (name, internal yaw, internal elevation-up) schema.
COURSE_POINTS = [['D',0,0],['A',-45,-45],['B',-45,45],['C',45,0]]
_points = {name: [name, gamma, -beta] for name,beta,gamma in COURSE_POINTS}
WAYPOINTS = [_points[name].copy() for name in ['D','A','D','B','D','C','D']]

def trapezoid(t,T,q0,q1):
    if t<=0: return np.array([q0,0.,0.])
    if t>=T: return np.array([q1,0.,0.])
    ta=T/4; tc=T/2; a=(q1-q0)/(ta*(ta+tc)); v=a*ta
    if t<ta: return np.array([q0+a*t*t/2,a*t,a])
    if t<ta+tc: return np.array([q0+a*ta*ta/2+v*(t-ta),v,0])
    td=t-ta-tc
    return np.array([q0+a*ta*ta/2+v*tc+v*td-a*td*td/2,v-a*td,-a])

class Trajectory:
    def __init__(self,c):
        self.c=c; self.start=0.; self.coeff=None
        if c['reference']=='smooth':
            self.c=dict(c,setpoint=[c['initial'][0],c['initial'][4]])
            self.coeff=np.zeros((2,6)); self.coeff[:,0]=np.deg2rad(self.c['setpoint']); self.coeff[:,1]=np.deg2rad([c['initial'][1],c['initial'][5]])
            self.update(c,0,force=True)
    def sample(self,t):
        c=self.c
        if c['reference']=='multipoint':
            pts=c['waypoints']; T=c['segmentDuration']; i=min(int(max(0,t)/T),len(pts)-2)
            return np.array([trapezoid(t-i*T,T,np.deg2rad(pts[i][j]),np.deg2rad(pts[i+1][j])) for j in [2,1]])
        if self.coeff is not None and c['reference']=='smooth':
            z=np.clip(t-self.start,0,c['transitionDuration']); a=self.coeff
            return np.column_stack([a@np.array([1,z,z*z,z**3,z**4,z**5]),a@np.array([0,1,2*z,3*z*z,4*z**3,5*z**4]),a@np.array([0,0,2,6*z,12*z*z,20*z**3])])
        return np.column_stack([np.deg2rad(c['setpoint']),np.zeros((2,2))])
    def update(self,c,t,force=False):
        old=self.sample(t); changed=force or any(c[k]!=self.c[k] for k in ['setpoint','reference','transitionDuration'])
        self.c=c
        if changed and c['reference']=='smooth':
            T=c['transitionDuration']; self.start=t
            self.coeff=np.zeros((2,6)); self.coeff[:,:3]=old/np.array([1,1,2])
            M=np.array([[T**3,T**4,T**5],[3*T*T,4*T**3,5*T**4],[6*T,12*T*T,20*T**3]])
            for i in range(2):
                a=self.coeff[i]; target=np.deg2rad(c['setpoint'][i])
                a[3:]=np.linalg.solve(M,[target-a[0]-a[1]*T-a[2]*T*T,-a[1]-2*a[2]*T,-2*a[2]])
        elif changed: self.coeff=None
