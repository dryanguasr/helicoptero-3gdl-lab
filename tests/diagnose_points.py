"""Check the four course targets using the corrected course beta convention."""
import copy, json, sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'public/python'))
from engine import Engine,DEFAULT

def main():
    results=[]
    for name,beta,gamma in [('D',0,0),('A',-45,-45),('B',-45,45),('C',45,0)]:
        c=copy.deepcopy(DEFAULT); c.update(controller='nonlinear',reference='smooth',setpoint=[-beta,gamma],duration=60.,initial=[1.5,0,3,0,-2,0])
        e=Engine(c)
        while not e.stopped: e.advance(100)
        target=np.array([0,beta,gamma]); entered=confirmed=None; longest=0.
        for row in e.history:
            course=np.rad2deg(np.array([row['x'][2],-row['x'][0],row['x'][4]]))
            if np.all(np.abs(course-target)<=5):
                if entered is None: entered=row['t']
                longest=max(longest,row['t']-entered)
                if confirmed is None and row['t']-entered>=3-1e-8: confirmed=row['t']
            else: entered=None
        results.append(dict(target=name,course_angles_target_deg=target.tolist(),final_course_angles_deg=np.rad2deg(np.array([e.x[2],-e.x[0],e.x[4]])).tolist(),confirmation_time_s=confirmed,longest_hold_s=longest,stopped=e.reason,dt=c['dt']))
    text=json.dumps(results,indent=2,ensure_ascii=False); (ROOT/'docs/point-validation.json').write_text(text,encoding='utf-8'); print(text)
if __name__=='__main__': main()
