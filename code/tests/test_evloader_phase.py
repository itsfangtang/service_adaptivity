"""Departure-phase tests for evloader.simulate_segment / run_plan.

Rule (paper, Section 3.4, "Departure timing after a frequency change"): when the action
changes at a grid time t0, the next departure is scheduled max{0, 60/f_new - phi} minutes
after the change, phi = time since the last departure; i.e. at max(t0, last_dep + 1/f_new).
A departure exactly at a segment end runs under the closing segment's action.

Run:  python code/tests/test_evloader_phase.py   (or with pytest)
"""
import os, sys
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from evloader import simulate_segment, run_plan, cost_of, KAPPA

W = dict(c0=1, cQ=1, cE=1, c_op=2)
LAM = np.full(24, 100.0)   # constant 100 pax/h
TOL = 1e-9


def test_offgrid_change_departs_immediately():
    # Reviewer's counterexample: lambda=100/h, segment [0.4, 0.6], last departure at 0,
    # P(t0)=40 (all arrived since that departure), new action (f,n)=(4,6), headway 0.25 h.
    # last_dep + H = 0.25 < t0, so one departure at t0 = 0.4 boards the 40 waiting;
    # the next would be at 0.65 > 0.6. Waiting on [0.4,0.6] = 100*0.2^2/2 = 2.0 pax-h,
    # 20 passengers remain at 0.6.
    q, ld, c, (P0, Q) = simulate_segment(LAM, 0.4, 0.6, 40.0, 0.0, (4, 6), W)
    assert abs(q - 20.0) < TOL, q
    assert abs(ld - 0.4) < TOL, ld
    assert c['deps'] == 1, c['deps']
    assert abs(c['boarded'] - 40.0) < TOL, c['boarded']
    assert abs(c['unused'] - (KAPPA * 6 - 40.0)) < TOL, c['unused']
    assert abs(c['wait0'] + c['waitQ'] - 2.0) < TOL, (c['wait0'], c['waitQ'])
    assert abs(P0 - 20.0) < TOL and abs(Q) < TOL, (P0, Q)


def test_change_with_headway_not_yet_elapsed():
    # Last departure at 0.3, change at 0.4 to f=4: next departure at 0.55 (phase kept).
    q, ld, c, _ = simulate_segment(LAM, 0.4, 0.6, 10.0, 0.3, (4, 6), W)
    assert c['deps'] == 1 and abs(ld - 0.55) < TOL, (c['deps'], ld)
    # waiting: 10 pax from 0.4 to 0.55 + arrivals 100*0.15^2/2, then 100*0.05^2/2 after
    assert abs(c['wait0'] + c['waitQ'] - (10 * 0.15 + 1.125 + 0.125)) < TOL
    assert abs(q - 5.0) < TOL, q


def test_hourly_aligned_plan():
    # Whole-hour change (2,8) -> (4,6) at 01:00 with f in {2,4}: phase is zero at the
    # change, so max(...) is inactive. Departures 0.5, 1.0 under (2,8) (the departure at
    # 1.0 closes the first interval and uses its 8 cars), then 1.25, 1.5, 1.75, 2.0 under (4,6).
    q, ld, tot = run_plan(LAM, [(0, (2, 8)), (1, (4, 6))], W, 0, 2)
    assert tot['deps'] == 6, tot['deps']
    assert abs(q) < TOL and abs(ld - 2.0) < TOL, (q, ld)
    assert abs(tot['wait0'] + tot['waitQ'] - (2 * 100 * 0.5**2 / 2 + 4 * 100 * 0.25**2 / 2)) < TOL
    assert abs(tot['unused'] - (2 * 450 - 100 + 4 * 337.5 - 100)) < TOL, tot['unused']
    assert abs(tot['op'] - (2 * 2 * 8 + 4 * 2 * 6)) < TOL, tot['op']
    # hour-by-hour evaluation (as in dayDP) gives the same totals
    q1, ld1, c1, _ = simulate_segment(LAM, 0, 1, 0.0, 0.0, (2, 8), W)
    q2, ld2, c2, _ = simulate_segment(LAM, 1, 2, q1, ld1, (4, 6), W)
    assert c1['deps'] == 2 and abs(ld1 - 1.0) < TOL
    assert abs(cost_of(c1, W) + cost_of(c2, W) - cost_of(tot, W)) < TOL


if __name__ == '__main__':
    for name, fn in list(globals().items()):
        if name.startswith('test_') and callable(fn):
            fn(); print('ok', name)
    print('all tests passed')
