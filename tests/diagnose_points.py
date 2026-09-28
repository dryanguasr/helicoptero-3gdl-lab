"""Diagnose fixed course objectives without treating completion as success.

Run from any directory: python tests/diagnose_points.py
Writes docs/point-validation.json. A failed goal is a reported result, not
an exception or a reason to change the controller under test.
"""
import copy
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'public/python'))
from engine import Engine, DEFAULT


def main():
    results = []
    for name, beta, gamma in [('D', 0, 0), ('A', -45, -45), ('B', -45, 45), ('C', 45, 0)]:
        config = copy.deepcopy(DEFAULT)
        config.update(reference='smooth', setpoint=[beta, gamma], duration=60)
        engine = Engine(config)
        while not engine.stopped:
            engine.advance(100)
        target = np.array([0, beta, gamma])
        entered = confirmed = None
        longest = 0.0
        for row in engine.history:
            angles = np.rad2deg(np.array(row['x'])[[2, 0, 4]])
            if np.all(np.abs(angles - target) <= 5):
                if entered is None:
                    entered = row['t']
                longest = max(longest, row['t'] - entered)
                if confirmed is None and row['t'] - entered >= 3 - 1e-8:
                    confirmed = row['t']
            else:
                entered = None
        results.append(dict(
            target=name,
            course_angles_target_deg=target.tolist(),
            final_course_angles_deg=np.rad2deg(engine.x[[2, 0, 4]]).tolist(),
            confirmation_time_s=confirmed, longest_hold_s=longest,
            stopped=engine.reason, dt=config['dt'],
        ))
    text = json.dumps(results, indent=2, ensure_ascii=False)
    (ROOT / 'docs/point-validation.json').write_text(text, encoding='utf-8')
    print(text)


if __name__ == '__main__':
    main()
