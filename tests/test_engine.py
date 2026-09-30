import sys,copy,unittest,json,os
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'public/python'))
import numpy as np
from engine import Engine,DEFAULT,validate
from plant import Delay,deadzone,inverse_deadzone,PARAMS,nominal,rk4,linearize,apply_coulomb
from trajectory import Trajectory,COURSE_POINTS
from control import Controller,Observer

LEGACY_WAYPOINTS = [['D',0,0],['A',-45,-45],['D',0,0],['B',45,-45],['D',0,0],['C',0,45],['D',0,0]]

def cfg(**kw):
    c=copy.deepcopy(DEFAULT);c.update(kw);return c
def run(c,T=10):
    c=copy.deepcopy(c);c['duration']=T;e=Engine(c)
    while not e.stopped:e.advance(100)
    return e

class EngineTests(unittest.TestCase):
    def test_default_full_course_route(self):
        for initial in [[0,0,0,0,0,0], [1.5,0,3,0,-2,0]]:
            with self.subTest(initial=initial):
                e=run(cfg(initial=initial),DEFAULT['duration'])
                self.assertEqual(e.reason,'Experimento completado')
                self.assertAlmostEqual(e.history[-1]['t'],60)
                self.assertLess(e.metrics()['rmse'][0],.2)
                self.assertLess(e.metrics()['rmse'][1],.75)
                arrivals=e.metrics()['waypoints']
                self.assertEqual([w['point'] for w in arrivals],['A','D','B','D','C','D'])
                for w in arrivals:self.assertLess(max(abs(v) for v in w['error']),1.1)
                self.assertLess(np.linalg.norm(np.rad2deg(e.x[[0,2,4]])),.1)
                self.assertEqual(e.metrics()['saturation'],0)

    def test_course_waypoint_signs_and_legacy_serialization(self):
        tr=Trajectory(cfg());targets={name:(beta,gamma) for name,beta,gamma in COURSE_POINTS}
        for i,(name,yaw,elevation) in enumerate(DEFAULT['waypoints']):
            np.testing.assert_allclose(np.rad2deg(tr.sample(10*i)[:,0]),[-targets[name][0],targets[name][1]])
        old=cfg(waypoints=LEGACY_WAYPOINTS)
        self.assertEqual(validate(old)['waypoints'],LEGACY_WAYPOINTS)
        np.testing.assert_allclose(np.rad2deg(Trajectory(old).sample(10)[:,0]),[-45,-45])

    def test_delay_zero_and_four_steps(self):
        d=Delay();np.testing.assert_equal(d.step([2,3],0),[2,3])
        d=Delay()
        for k in range(8):np.testing.assert_equal(d.step([k+1,0],4),[max(0,k-3),0])

    def test_deadzone_inverse(self):
        for u in [np.array([0.,0.]),np.array([.4,-.2]),np.array([-.6,.3])]:
            np.testing.assert_allclose(deadzone(inverse_deadzone(u,PARAMS),PARAMS),u)

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
        for kind in ['state','prefilter','integral']:
            with self.assertRaisesRegex(ValueError,'no estabilizable'):
                Controller(cfg(controller=kind,trim=0))

    def test_local_stabilization(self):
        for kind in ['state','prefilter','integral','nonlinear','pid','smc']:
            with self.subTest(kind=kind):
                e=run(cfg(controller=kind,reference='step',setpoint=[15,0],initial=[16,0,.5,0,1,0]),18)
                self.assertEqual(e.reason,'Experimento completado')
                self.assertLess(np.linalg.norm(np.rad2deg(e.x[[0,2,4]])-[15,0,0]),1.5)

    def test_yaw_integrator_state_and_prefilter_have_same_steady_target(self):
        finals=[]
        for kind in ['state','prefilter']:
            e=run(cfg(controller=kind,reference='step',setpoint=[15,20],initial=[15,0,0,0,0,0]),25)
            finals.append(np.rad2deg(e.x[[0,4]]))
        np.testing.assert_allclose(finals[0],finals[1],atol=1e-6)
        self.assertLess(abs(finals[0][1]-20),.05)

    def test_prefilter_removes_nominal_pitch_offset(self):
        state=run(cfg(controller='state',reference='step',setpoint=[5,0],initial=[15,0,0,0,0,0]),30)
        pre=run(cfg(controller='prefilter',reference='step',setpoint=[5,0],initial=[15,0,0,0,0,0]),30)
        es=abs(np.rad2deg(state.x[0])-5);ep=abs(np.rad2deg(pre.x[0])-5)
        self.assertGreater(es,2.0);self.assertLess(ep,.15)

    def test_integral_rejects_constant_pitch_disturbance(self):
        def disturbed(kind):
            c=cfg(controller=kind,reference='step',setpoint=[15,10],initial=[15,0,0,0,0,0]);c['flags']['constantDisturbance']=True;c['constantDisturbance']=[0,.8,0]
            return run(c,35)
        pre=disturbed('prefilter');integ=disturbed('integral')
        pre_err=abs(np.rad2deg(pre.x[0])-15);int_err=abs(np.rad2deg(integ.x[0])-15)
        self.assertGreater(pre_err,.03);self.assertLess(int_err,.01)

    def test_counterweight_positive_course_bias_pushes_internal_elevation_down(self):
        c=cfg(controller='state',reference='step',setpoint=[15,0],initial=[15,0,0,0,0,0]);c['flags']['counterweight']=True;c['counterweightBias']=2
        e=Engine(c);before=e.x[0];e.step();self.assertLess(e.x[0],before+.01)

    def test_coulomb_has_stiction_region(self):
        dx=np.array([0.,.02,0.,0.,0.,0.]);x=np.zeros(6);out=apply_coulomb(dx,x,PARAMS)
        self.assertEqual(out[1],0.)

    def test_smc_survives_moderate_constant_disturbance(self):
        c=cfg(controller='smc',reference='step',setpoint=[15,20],initial=[15,0,0,0,0,0]);c['flags']['constantDisturbance']=True;c['constantDisturbance']=[.1,.4,.15]
        e=run(c,30);self.assertEqual(e.reason,'Experimento completado');self.assertLess(abs(np.rad2deg(e.x[4])-20),2)

    def test_signed_collective_and_roll_limit_legacy_nonlinear(self):
        ctrl=Controller(cfg(controller='nonlinear'));x=np.deg2rad([-30,0,0,0,0,0]);u,theta,_=ctrl.command(x,np.array([[x[0],0,0],[0,0,0]]));self.assertLess(u[0],0);self.assertLess(abs(theta),1e-9)
        _,theta,limited=ctrl.command(np.zeros(6),np.array([[0.,0,0],[1,0,0]]));self.assertTrue(limited);self.assertLessEqual(abs(theta),np.deg2rad(38))

    def test_saturation_antiwindup(self):
        c=cfg(controller='pid',reference='step',setpoint=[55,40],initial=[15,0,0,0,0,0]);c['flags']['saturation']=True
        e=run(c,1);self.assertGreater(e.metrics()['saturation'],0);self.assertLess(np.linalg.norm(e.controller.integral),2)

    def test_observer_noise(self):
        for mode in ['filtered','luenberger','ekf']:
            c=cfg(observer=mode,controller='prefilter',reference='step',setpoint=[15,0],initial=[15,0,0,0,0,0]);c['flags']['measurement']=True;e=run(c,5)
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

    def test_equilibrium_validation_and_legacy_upgrade(self):
        xe,ue,_,_=linearize(PARAMS,np.deg2rad(15));np.testing.assert_allclose(nominal(xe,ue,PARAMS),0,atol=1e-15)
        for change in [dict(dt=0),dict(seed=float('nan')),dict(waypoints=[]),dict(sensorStd=[1,2])]:
            with self.assertRaises(ValueError):validate(cfg(**change))
        old={k:copy.deepcopy(v) for k,v in DEFAULT.items() if k not in ['gainMethod','desiredPoles','integralPoles','smcLambda','smcEta','smcPhi','counterweightBias','constantDisturbance']}
        old['controller']='lqr';old['flags'].pop('counterweight');old['flags'].pop('constantDisturbance')
        upgraded=validate(old);self.assertEqual(upgraded['controller'],'prefilter');self.assertIn('smcEta',upgraded)

    def test_domain_stop(self):
        c=cfg(controller='nonlinear',initial=[60,60,60,60,0,0]);c['kp']=[0,0,0];c['kd']=[0,0,0];e=run(c,3)
        self.assertTrue(e.stopped);self.assertTrue(all(np.isfinite(r['x']).all() for r in e.history))

    def test_notebook_saved_reference(self):
        data=json.loads((Path(__file__).parent/'notebook_reference.json').read_text())
        ctrl=Controller(cfg(controller='nonlinear'));trajectory=Trajectory(cfg(controller='nonlinear',reference='multipoint',waypoints=LEGACY_WAYPOINTS,duration=60,initial=[1.5,0,3,0,-2,0]))
        for row in data:
            x=np.array(row['x']);u=np.array(row['u'])
            np.testing.assert_allclose(nominal(x,u,PARAMS),row['dx'],atol=1e-13)
            np.testing.assert_allclose(rk4(lambda x,u:nominal(x,u,PARAMS),x,u,.02),row['next'],atol=1e-13)
            cmd,theta,_=ctrl.command(x,trajectory.sample(row['t']))
            np.testing.assert_allclose(cmd,row['command'],atol=1e-13);self.assertAlmostEqual(theta,row['theta'])

    def test_notebook_nominal_and_allocation(self):
        path=os.environ.get('SOURCE_NOTEBOOK')
        if not path:self.skipTest('SOURCE_NOTEBOOK not supplied')
        nb=json.loads(Path(path).read_text(encoding='utf-8'));ns={'np':np};from dataclasses import dataclass;ns['dataclass']=dataclass;ns['dt']=.02
        for i in [4,5,9,14,15]:exec(''.join(nb['cells'][i]['source']),ns)
        ctrl=Controller(cfg(controller='nonlinear'));tr=Trajectory(cfg(controller='nonlinear',reference='multipoint',waypoints=LEGACY_WAYPOINTS,duration=60,initial=[1.5,0,3,0,-2,0]))
        for t in [0.,3.,13.,24.,43.,55.]:
            x=np.deg2rad([12,1,-4,.5,7,-.2]);u=np.array([.7,-.1])
            np.testing.assert_allclose(nominal(x,u,PARAMS),ns['nominal_dynamics'](x,u),atol=1e-14)
            expected,info=ns['trajectory_allocation_control'](x,t);actual,theta,_=ctrl.command(x,tr.sample(t))
            np.testing.assert_allclose(actual,expected,atol=1e-13);self.assertAlmostEqual(theta,info['theta_des'])

if __name__=='__main__':unittest.main(verbosity=2)
