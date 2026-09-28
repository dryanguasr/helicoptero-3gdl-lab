"""Six-state model extracted from the supplied teaching notebook. SI units internally."""
import numpy as np

PARAMS = dict(a_alpha=2.8, a_theta=4.2, a_psi=2.8, k_alpha=4.5, k_theta=2.1,
              b_alpha=.9, b_theta=.48, b_psi=.32, coulomb_alpha=.055,
              coulomb_theta=.05, coulomb_psi=.04, coulomb_smoothing=.04,
              u_c_max=1.8, u_d_max=1.2, deadzone_c=.07, deadzone_d=.06, delay_seconds=.08)
C = np.eye(6)[[0,2,4]]

def nominal(x, u, p):
    a, av, r, rv, y, yv = x
    return np.array([av, p['a_alpha']*u[0]*np.cos(r)-p['k_alpha']*np.sin(a)-p['b_alpha']*av,
                     rv, p['a_theta']*u[1]-p['k_theta']*np.sin(r)-p['b_theta']*rv,
                     yv, p['a_psi']*u[0]*np.sin(r)*np.cos(a)-p['b_psi']*yv])

def friction(x, p):
    return np.array([p['coulomb_alpha'],p['coulomb_theta'],p['coulomb_psi']])*np.tanh(x[[1,3,5]]/p['coulomb_smoothing'])

def rk4(f, x, u, dt):
    k1=f(x,u); k2=f(x+dt*k1/2,u); k3=f(x+dt*k2/2,u); k4=f(x+dt*k3,u)
    return x+dt*(k1+2*k2+2*k3+k4)/6

def jacobian(f, x, eps=1e-6):
    eye=np.eye(len(x))*eps
    return np.column_stack([(f(x+d)-f(x-d))/(2*eps) for d in eye])

def linearize(p, elevation):
    xe=np.array([elevation,0,0,0,0,0.]); ue=np.array([p['k_alpha']*np.sin(elevation)/p['a_alpha'],0.])
    return xe,ue,jacobian(lambda x:nominal(x,ue,p),xe),jacobian(lambda u:nominal(xe,u,p),ue)

def disturbance(t):
    d=np.zeros(3)
    if 24 <= t <= 25: d+=np.deg2rad([0,4,-3.5])
    if 42 <= t <= 48: d+=np.deg2rad([0,0,1.2])
    return d

class Delay:
    def __init__(self): self.history=[]
    def step(self,u,n):
        # Append first: n=0 returns this exact sample; n=4 returns k-4.
        self.history.append(np.array(u,copy=True))
        value=self.history[-n-1].copy() if len(self.history)>n else np.zeros(2)
        if len(self.history)>1002: self.history.pop(0)
        return value

def deadzone(u,p):
    return np.sign(u)*np.maximum(np.abs(u)-[p['deadzone_c'],p['deadzone_d']],0)

def inverse_deadzone(u,p):
    return u+np.where(np.isclose(u,0),0,np.sign(u)*[p['deadzone_c'],p['deadzone_d']])
