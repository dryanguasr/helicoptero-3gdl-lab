import json, copy
import numpy as np
from plant import PARAMS,C,nominal,friction,apply_coulomb,rk4,disturbance,Delay,deadzone,inverse_deadzone
from trajectory import Trajectory,WAYPOINTS
from control import Controller,Observer

DEFAULT = dict(version=1,level=1,dt=.02,seed=2026,duration=25.,controller='state',gainMethod='lqr',
    observer='exact',plantModel='nonlinear',reference='smooth',setpoint=[15.,20.],waypoints=WAYPOINTS,
    segmentDuration=10.,transitionDuration=3.,trim=15.,params=PARAMS,nominal=PARAMS,linked=True,
    kp=[6.,2.,14.],kd=[4.,2.,6.],ki=[.8,.2,.5],lqrQ=[30.,3.,15.,2.,20.,3.],lqrR=[1.,1.],
    integralWeight=10.,desiredPoles=[-1.0,-1.25,-1.5,-1.8,-2.1,-2.4],
    integralPoles=[-0.65,-0.85,-1.05,-1.3,-1.55,-1.8,-2.05,-2.3],rollLimit=38.,
    smcLambda=[1.5,.8,3.0],smcEta=[.3,.15,.6],smcPhi=[.2,.2,.2],
    counterweightBias=0.,constantDisturbance=[0.,0.,0.],
    observerSpeed=5.,filterHz=3.,ekfQ=1.,ekfR=[.55,.55,.75],sensorStd=[.55,.55,.75],processStd=[.02,.02,.024],
    initial=[15.,0.,0.,0.,0.,0.],
    flags=dict(saturation=False,deadzone=False,delay=False,coulomb=False,measurement=False,process=False,disturbance=False,
               counterweight=False,constantDisturbance=False,
               compensateDeadzone=False,compensateFriction=False,compensateDelay=False))


def upgrade(c):
    """Backward-compatible enrichment of legacy v1 experiments."""
    c=copy.deepcopy(c)
    if c.get('controller')=='lqr': c['controller']='prefilter'
    if c.get('controller')=='lqi': c['controller']='integral'
    unknown=set(c)-set(DEFAULT)
    if unknown: raise ValueError('Campos desconocidos: '+', '.join(sorted(unknown)))
    for k,v in DEFAULT.items():
        if k not in c: c[k]=copy.deepcopy(v)
    if not isinstance(c.get('flags'),dict): raise ValueError('Conmutadores inválidos.')
    for k,v in DEFAULT['flags'].items():
        if k not in c['flags']: c['flags'][k]=v
    return c


def validate(c):
    c=upgrade(c)
    if c['version']!=1: raise ValueError('Versión de experimento no compatible.')
    for k,options in dict(controller=['state','prefilter','integral','smc','nonlinear','pid'],
                          gainMethod=['lqr','poles'],observer=['exact','filtered','luenberger','ekf'],
                          plantModel=['nonlinear','linear'],reference=['multipoint','step','smooth']).items():
        if c[k] not in options: raise ValueError('Selección inválida: '+k)
    def number(v,lo,hi):
        if isinstance(v,bool) or not isinstance(v,(int,float)) or not np.isfinite(v) or not lo<=v<=hi:
            raise ValueError(f'Valor fuera de rango [{lo}, {hi}]: {v}')
    for k,lo,hi in [('dt',.005,.05),('duration',.1,600),('seed',0,4294967295),('segmentDuration',.5,60),
                    ('transitionDuration',.2,30),('trim',-60,60),('rollLimit',1,60),('observerSpeed',.1,30),
                    ('filterHz',.1,25),('ekfQ',.001,100),('integralWeight',.001,1000),('level',1,6),
                    ('counterweightBias',-10,10)]: number(c[k],lo,hi)
    if c['seed']!=int(c['seed']): raise ValueError('La semilla debe ser entera.')
    if c['level']!=int(c['level']): raise ValueError('El nivel debe ser entero.')
    arrays=[('setpoint',2,-60,60),('initial',6,-80,80),('kp',3,0,100),('kd',3,0,100),('ki',3,0,30),
            ('lqrQ',6,.001,1000),('lqrR',2,.001,1000),('sensorStd',3,0,10),('processStd',3,0,1),
            ('ekfR',3,.001,10),('desiredPoles',6,-20,-.01),('integralPoles',8,-20,-.01),
            ('smcLambda',3,.05,30),('smcEta',3,.01,30),('smcPhi',3,.001,1),
            ('constantDisturbance',3,-10,10)]
    for k,n,lo,hi in arrays:
        if not isinstance(c[k],list) or len(c[k])!=n: raise ValueError('Dimensión inválida: '+k)
        for v in c[k]: number(v,lo,hi)
    if not isinstance(c['linked'],bool) or set(c['flags'])!=set(DEFAULT['flags']) or not all(isinstance(v,bool) for v in c['flags'].values()):
        raise ValueError('Conmutadores inválidos.')
    for group in ['params','nominal']:
        if set(c[group])!=set(PARAMS): raise ValueError('Parámetros incompletos.')
        for k,v in c[group].items():
            lo=.001 if k.startswith('a_') or k in ['coulomb_smoothing','u_c_max','u_d_max'] else 0
            number(v,lo,2 if k=='delay_seconds' else 20)
    if not isinstance(c['waypoints'],list) or not 2<=len(c['waypoints'])<=30: raise ValueError('Se requieren entre 2 y 30 puntos.')
    for pt in c['waypoints']:
        if len(pt)!=3 or not isinstance(pt[0],str) or len(pt[0])>30: raise ValueError('Punto inválido.')
        number(pt[1],-60,60); number(pt[2],-60,60)
    if c['linked']: c['nominal']=copy.deepcopy(c['params'])
    return c


class Engine:
    def __init__(self,c,events=None):
        self.c=validate(c); self.initial_config=copy.deepcopy(self.c); self.events=[]; self.pending=copy.deepcopy(events or [])
        last=-1
        for event in self.pending:
            if not isinstance(event['step'],int) or event['step']<last: raise ValueError('Eventos fuera de orden.')
            event['config']=validate(event['config']); last=event['step']
        self.controller=Controller(self.c); self.observer=Observer(self.c); self.trajectory=Trajectory(self.c)
        self.x=np.deg2rad(self.c['initial']); self.xhat=self.x.copy() if self.c['observer']=='exact' else self.observer.x.copy()
        self.k=0; self.delay=Delay(); self.model_delay=Delay(); self.previous_model_u=np.zeros(2)
        self.noise=np.random.default_rng(np.random.SeedSequence([int(self.c['seed']),1])); self.sensor_noise=np.random.default_rng(np.random.SeedSequence([int(self.c['seed']),2]))
        self.history=[]; self.stopped=False; self.reason=''; self.waypoint_errors=[]
        self.history.append(self.record(self.trajectory.sample(0),C@self.x,np.zeros(2),np.zeros(2),np.zeros(2),np.zeros(2),0,False,False))

    def update(self,c,record=True):
        c=validate(c)
        for k in ['controller','gainMethod','observer','dt','seed','initial','plantModel','trim']:
            if c[k]!=self.c[k]: raise ValueError('Este cambio requiere una corrida nueva: '+k)
        controller=Controller(c); observer=Observer(c)
        controller.integral=self.controller.integral.copy(); observer.x=self.observer.x.copy(); observer.P=self.observer.P.copy(); observer.previous_y=self.observer.previous_y
        self.trajectory.update(c,self.k*self.c['dt']); self.c=c; self.controller=controller; self.observer=observer
        if record:self.events.append(dict(step=self.k,time=self.k*c['dt'],config=copy.deepcopy(c)))

    def record(self,ref,y,cmd,pre,sat,eff,theta,saturated,limited):
        return dict(t=round(self.k*self.c['dt'],10),x=self.x.tolist(),hat=self.xhat.tolist(),y=y.tolist(),ref=ref[:,0].tolist(),
                    u=cmd.tolist(),pre=pre.tolist(),sat=sat.tolist(),effective=eff.tolist(),theta=theta,saturated=bool(saturated),limited=bool(limited))

    def step(self):
        if self.stopped:return None
        while self.pending and self.pending[0]['step']==self.k:
            self.update(self.pending.pop(0)['config'])
        c=self.c; p=c['params']; pn=c['nominal']; f=c['flags']; dt=c['dt']; t=self.k*dt
        if t>=c['duration']-1e-10:self.stopped=True; self.reason='Experimento completado'; return None
        ref=self.trajectory.sample(t); feedback=self.x.copy() if c['observer']=='exact' else self.xhat.copy()
        if f['compensateDelay'] and f['delay']:
            for _ in range(int(round(pn['delay_seconds']/dt))): feedback=rk4(lambda z,u:nominal(z,u,pn),feedback,self.previous_model_u,dt)
        cmd,theta,limited=self.controller.command(feedback,ref)
        if f['compensateFriction']:
            fr=friction(feedback,pn); cmd+=np.array([fr[0]/pn['a_alpha']+.35*fr[2]/pn['a_psi'],fr[1]/pn['a_theta']])
        pre=inverse_deadzone(cmd,pn) if f['compensateDeadzone'] else cmd.copy()
        sat=np.clip(pre,[-p['u_c_max'],-p['u_d_max']],[p['u_c_max'],p['u_d_max']]) if f['saturation'] else pre.copy()
        saturated=bool(np.any(abs(pre-sat)>1e-10)); self.controller.antiwindup(saturated or limited)
        delayed=self.delay.step(sat,int(round(p['delay_seconds']/dt)) if f['delay'] else 0)
        eff=deadzone(delayed,p) if f['deadzone'] else delayed
        model_sat=np.clip(pre,[-pn['u_c_max'],-pn['u_d_max']],[pn['u_c_max'],pn['u_d_max']]) if f['saturation'] else pre.copy()
        model_u=self.model_delay.step(model_sat,int(round(pn['delay_seconds']/dt)) if f['delay'] else 0)
        self.previous_model_u=model_u.copy()
        if c['plantModel']=='linear':
            from plant import linearize
            xe,ue,A,B=linearize(p,np.deg2rad(c['trim']))
        def dynamics(x,u):
            dx=A@(x-xe)+B@(u-ue) if c['plantModel']=='linear' else nominal(x,u,p)
            # Positive counterweightBias means positive course beta acceleration (motors down).
            if f['counterweight']:
                dx[1]-=np.deg2rad(c['counterweightBias'])*np.cos(x[0])
            if f['constantDisturbance']:
                d=np.deg2rad(np.array(c['constantDisturbance'])) # course [alpha,beta,gamma]
                dx[[3,1,5]]+=np.array([d[0],-d[1],d[2]])
            if f['disturbance']: dx[[1,3,5]]+=disturbance(t)
            if f['coulomb']: dx=apply_coulomb(dx,x,p)
            return dx
        xn=rk4(dynamics,self.x,eff,dt)
        process=self.noise.normal(size=3); sensor=self.sensor_noise.normal(size=3)
        if f['process']: xn[[1,3,5]]+=process*np.array(c['processStd'])*np.sqrt(dt)
        if not np.all(np.isfinite(xn)) or abs(xn[0])>=np.deg2rad(80) or abs(xn[2])>=np.deg2rad(80) or abs(xn[4])>=np.deg2rad(360):
            self.stopped=True; self.reason='Detenido: se salió del dominio del modelo (elevación/roll ±80°, yaw ±360°).'; return None
        self.x=xn; self.k+=1; y=C@self.x
        if f['measurement']: y+=sensor*np.deg2rad(c['sensorStd'])
        self.xhat=self.x.copy() if c['observer']=='exact' else self.observer.step(y,model_u)
        if not np.all(np.isfinite(self.xhat)):
            self.stopped=True; self.reason='Detenido: el observador produjo valores no finitos.'; return None
        row=self.record(self.trajectory.sample(self.k*dt),y,cmd,pre,sat,eff,theta,saturated,limited); self.history.append(row)
        if c['reference']=='multipoint':
            for i,pt in enumerate(c['waypoints'][1:],1):
                arrival=i*c['segmentDuration']
                if t<arrival<=self.k*dt+1e-10:self.waypoint_errors.append(dict(point=pt[0],t=arrival,error=np.rad2deg(np.array(row['ref'])-self.x[[0,4]]).tolist()))
        return row

    def metrics(self):
        rows=self.history; x=np.array([r['x'] for r in rows]); h=np.array([r['hat'] for r in rows]); ref=np.array([r['ref'] for r in rows])
        return dict(rmse=np.sqrt(np.mean(np.rad2deg(x[:,[0,4]]-ref)**2,axis=0)).tolist(),
                    estimation=np.sqrt(np.mean(np.rad2deg(x-h)**2,axis=0)).tolist(),
                    saturation=100*np.mean([r['saturated'] for r in rows[1:]]) if len(rows)>1 else 0,
                    effort=float(sum(np.dot(r['effective'],r['effective'])*self.c['dt'] for r in rows[1:])),waypoints=self.waypoint_errors)

    def advance(self,n=1):
        rows=[]
        for _ in range(min(n,100)):
            row=self.step()
            if row is None:break
            rows.append(row)
        return dict(rows=rows,metrics=self.metrics(),stopped=self.stopped,reason=self.reason,config=self.c,events=self.events+self.pending)

engine=None
def dispatch(message):
    global engine
    m=json.loads(message); op=m['op']
    if op=='defaults':return json.dumps(DEFAULT)
    if op=='reset':
        candidate=Engine(m['config'],m.get('events')); engine=candidate
        result=dict(rows=engine.history,metrics=engine.metrics(),stopped=False,reason='',config=engine.c)
    elif op=='update':
        engine.update(m['config']); engine.pending=[]
        result=dict(config=engine.c,event=engine.events[-1],events=engine.events)
    elif op=='advance':result=engine.advance(m.get('n',1))
    else:raise ValueError('Comando desconocido')
    return json.dumps(result,allow_nan=False)
