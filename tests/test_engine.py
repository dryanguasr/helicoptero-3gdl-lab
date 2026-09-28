import sys,copy,unittest,json,os
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'public/python'))
import numpy as np
from engine import Engine,DEFAULT,validate
from plant import Delay,deadzone,inverse_deadzone,PARAMS,nominal,rk4,linearize
from trajectory import Trajectory
from control import Controller,Observer

def cfg(**kw):
    c=copy.deepcopy(DEFAULT);c.update(kw);return c
def run(c,T=10):
    c['duration']=T;e=Engine(c)
    while not e.stopped:e.advance(100)
    return e

class EngineTests(unittest.TestCase):
    def test_delay_zero_and_four_steps(self):
        d=Delay();np.testing.assert_equal(d.step([2,3],0),[2,3])
        d=Delay()
        for k in range(8):np.testing.assert_equal(d.step([k+1,0],4),[max(0,k-3),0])
    def test_deadzone_inverse(self):
        for u in [np.array([0.,0.]),np.array([.4,-.2]),np.array([-.6,.3])]:np.testing.assert_allclose(deadzone(inverse_deadzone(u,PARAMS),PARAMS),u)
    def test_exact_state_feedback(self):
        c=cfg();c['flags']['measurement']=True;e=run(c,1)
        for r in e.history:np.testing.assert_array_equal(r['x'],r['hat'])
        self.assertTrue(any(not np.allclose(r['y'],np.array(r['x'])[::2]) for r in e.history[1:]))
    def test_observer_interface_has_no_truth(self):
        import inspect
        self.assertEqual(list(inspect.signature(Observer.step).parameters),['self','y','u'])
    def test_smooth_continuity(self):
        c=cfg(reference='smooth');tr=Trajectory(c);t=.8;old=tr.sample(t);new=copy.deepcopy(c);new['setpoint']=[-25,40];tr.update(new,t)
        np.testing.assert_allclose(tr.sample(t),old,atol=1e-12)
        np.testing.assert_allclose(tr.sample(t+new['transitionDuration'])[:,0],np.deg2rad(new['setpoint']),atol=1e-12)
        np.testing.assert_allclose(tr.sample(t+new['transitionDuration'])[:,1:],0,atol=1e-12)
    def test_linear_zero_trim_rejected(self):
        for kind in ['lqr','lqi']:
            with self.assertRaisesRegex(ValueError,'no estabilizable'):Controller(cfg(controller=kind,trim=0))
    def test_local_stabilization(self):
        for kind in ['nonlinear','pid','lqr','lqi']:
            with self.subTest(kind=kind):
                e=run(cfg(controller=kind,reference='step',setpoint=[15,0],initial=[16,0,.5,0,1,0]),15)
                self.assertEqual(e.reason,'Experimento completado')
                self.assertLess(np.linalg.norm(np.rad2deg(e.x[[0,2,4]])-[15,0,0]),.6)
    def test_signed_collective(self):
        c=Controller(cfg());x=np.deg2rad([-30,0,0,0,0,0]);u,theta,_=c.command(x,np.array([[x[0],0,0],[0,0,0]]))
        self.assertLess(u[0],0);self.assertLess(abs(theta),1e-9)
    def test_roll_limit(self):
        c=Controller(cfg());_,theta,limited=c.command(np.zeros(6),np.array([[0.,0,0],[1,0,0]]))
        self.assertTrue(limited);self.assertLessEqual(abs(theta),np.deg2rad(38))
    def test_saturation_antiwindup(self):
        c=cfg(controller='pid',reference='step',setpoint=[55,40],initial=[15,0,0,0,0,0]);c['flags']['saturation']=True
        e=run(c,1);self.assertGreater(e.metrics()['saturation'],0);self.assertLess(np.linalg.norm(e.controller.integral),2)
        recovery=copy.deepcopy(e.c);recovery['setpoint']=[15,0];recovery['duration']=25;e.stopped=False;e.update(recovery)
        while not e.stopped:e.advance(100)
        self.assertEqual(e.reason,'Experimento completado');self.assertLess(abs(np.rad2deg(e.x[0])-15),1)
    def test_observer_noise(self):
        for mode in ['filtered','luenberger','ekf']:
            c=cfg(observer=mode,reference='step',setpoint=[15,0],initial=[15,0,0,0,0,0]);c['flags']['measurement']=True;e=run(c,5)
            self.assertEqual(e.reason,'Experimento completado');self.assertTrue(np.all(np.isfinite(e.xhat)))
            self.assertLess(np.linalg.norm(np.rad2deg(e.xhat[::2]-e.x[::2])),3)
    def test_replay_exact(self):
        c=cfg(observer='ekf');c['flags']['measurement']=True;c['flags']['process']=True;e=Engine(c);e.advance(30)
        new=copy.deepcopy(c);new['reference']='smooth';new['setpoint']=[20,15];e.update(new);e.advance(40)
        replay=Engine(c,e.events);replay.advance(70)
        np.testing.assert_array_equal(e.x,replay.x);np.testing.assert_array_equal(e.xhat,replay.xhat)
    def test_noise_pairing(self):
        a=cfg(reference='step');b=copy.deepcopy(a);a['flags']['measurement']=True;b['flags']['measurement']=True;b['controller']='pid'
        ea=Engine(a);eb=Engine(b)
        for _ in range(10):
            ra=ea.step();rb=eb.step();np.testing.assert_allclose(np.array(ra['y'])-ea.x[::2],np.array(rb['y'])-eb.x[::2],atol=1e-15)
    def test_equilibrium_and_validation(self):
        xe,ue,_,_=linearize(PARAMS,np.deg2rad(15));np.testing.assert_allclose(nominal(xe,ue,PARAMS),0,atol=1e-15)
        for change in [dict(dt=0),dict(seed=float('nan')),dict(waypoints=[]),dict(sensorStd=[1,2])]:
            with self.assertRaises(ValueError):validate(cfg(**change))
    def test_domain_stop(self):
        c=cfg(initial=[60,60,60,60,0,0]);c['kp']=[0,0,0];c['kd']=[0,0,0];e=run(c,3)
        self.assertTrue(e.stopped);self.assertTrue(all(np.isfinite(r['x']).all() for r in e.history))
    def test_notebook_saved_reference(self):
        data=json.loads((Path(__file__).parent/'notebook_reference.json').read_text())
        ctrl=Controller(cfg());trajectory=Trajectory(cfg())
        for row in data:
            x=np.array(row['x']);u=np.array(row['u'])
            np.testing.assert_allclose(nominal(x,u,PARAMS),row['dx'],atol=1e-13)
            np.testing.assert_allclose(rk4(lambda x,u:nominal(x,u,PARAMS),x,u,.02),row['next'],atol=1e-13)
            cmd,theta,_=ctrl.command(x,trajectory.sample(row['t']))
            np.testing.assert_allclose(cmd,row['command'],atol=1e-13);self.assertAlmostEqual(theta,row['theta'])
    def test_six_levels_complete(self):
        for level in range(1,7):
            c=cfg(level=level)
            if level==2:c.update(reference='smooth',setpoint=[17,5],initial=[15,0,0,0,0,0])
            if level>=3:c['flags'].update(saturation=True,deadzone=True,delay=True)
            if level>=4:
                c['flags'].update(coulomb=True,disturbance=True);c['linked']=False;c['params']['a_alpha']*=.85;c['params']['a_psi']*=.85
            if level>=5:c['flags'].update(measurement=True,process=True);c['observer']='ekf'
            if level==6:c['flags'].update(compensateDeadzone=True,compensateFriction=True)
            with self.subTest(level=level):
                e=run(c,60);self.assertEqual(e.k,3000);self.assertEqual(e.reason,'Experimento completado')
    def test_notebook_nominal_and_allocation(self):
        path=os.environ.get('SOURCE_NOTEBOOK')
        if not path:self.skipTest('SOURCE_NOTEBOOK not supplied')
        nb=json.loads(Path(path).read_text(encoding='utf-8'));ns={'np':np};from dataclasses import dataclass;ns['dataclass']=dataclass;ns['dt']=.02
        for i in [4,5,9,14,15]:exec(''.join(nb['cells'][i]['source']),ns)
        ctrl=Controller(cfg());tr=Trajectory(cfg())
        for t in [0.,3.,13.,24.,43.,55.]:
            x=np.deg2rad([12,1,-4,.5,7,-.2]);u=np.array([.7,-.1])
            np.testing.assert_allclose(nominal(x,u,PARAMS),ns['nominal_dynamics'](x,u),atol=1e-14)
            np.testing.assert_allclose(rk4(lambda x,u:nominal(x,u,PARAMS),x,u,.02),ns['rk4_step'](ns['nominal_dynamics'],x,u,.02),atol=1e-14)
            expected,info=ns['trajectory_allocation_control'](x,t);actual,theta,_=ctrl.command(x,tr.sample(t))
            np.testing.assert_allclose(actual,expected,atol=1e-13);self.assertAlmostEqual(theta,info['theta_des'])

if __name__=='__main__':unittest.main(verbosity=2)
