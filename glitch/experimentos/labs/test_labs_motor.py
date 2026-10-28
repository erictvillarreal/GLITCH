"""Pruebas de labs_motor.py. Correr: cd glitch/experimentos/labs && python3 -m pytest -q test_labs_motor.py -p no:warnings"""
import datetime as dt, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from labs_motor import BarDays, DayData, chal_life, fixed_nc, calib_drift


def brownian_days(D=3000, K=58, step=30.0, seed=7):
    r = np.random.default_rng(seed); inc = r.normal(0, step, (D, K)); cl = np.cumsum(inc, 1); op = np.concatenate([np.zeros((D, 1)), cl[:, :-1]], 1)
    wick = np.abs(r.normal(0, step * 0.3, (D, K, 2)))
    hi = np.maximum(op, cl) + wick[:, :, 0]; lo = np.minimum(op, cl) - wick[:, :, 1]
    return DayData([dt.date(2020, 1, 1) + dt.timedelta(days=i) for i in range(D)], np.full(D, 1000.0), op, hi, lo, cl, [])


def make(dd, sl, tp, cush_max=3000.0, step=25.0):
    return BarDays(dd, 1.0, 0.0, sl, tp, slip=(0.0,), exit_slip=0.0, cush_max=cush_max, step=step)


def test_zero_drift_pass_probability_respects_the_martingale_bound():
    # $25K estático: meta 2,000, piso −1,000: sin ventaja ningún plan puede pasar con más de L/(T+L) = 1/3 (teorema de parada opcional)
    dd = brownian_days(); days = make(dd, 200, 400)                      # SL = 200 ticks × 5 contratos = $1,000 (el colchón completo); TP = 2× ⇒ $2,000
    r = chal_life(days, 20000, 1, 2000.0, 1000.0, 1.0, 0.0, 200, fixed_nc(5), consist=None, min_days=1, max_days=63)
    p = r["passed"].mean()
    assert 0.20 <= p <= 0.36, p                                          # cerca de 1/3, nunca por encima de la cota (+ruido)


def test_trailing_floor_makes_passing_harder_than_static():
    dd = brownian_days(); days = make(dd, 200, 400, cush_max=4000.0)
    st = chal_life(days, 15000, 2, 2000.0, 1000.0, 1.0, 0.0, 200, fixed_nc(5), trailing=False, consist=None, min_days=1)["passed"].mean()
    tr = chal_life(days, 15000, 2, 2000.0, 1000.0, 1.0, 0.0, 200, fixed_nc(5), trailing=True, consist=None, min_days=1)["passed"].mean()
    assert tr <= st + 0.01


def test_dll_clips_the_stop_and_lowers_exposure():
    dd = brownian_days(); days = make(dd, 200, 400)
    free = chal_life(days, 8000, 3, 2000.0, 1000.0, 1.0, 0.0, 200, fixed_nc(5), dll=None, consist=None, min_days=1)
    capped = chal_life(days, 8000, 3, 2000.0, 1000.0, 1.0, 0.0, 200, fixed_nc(5), dll=500.0, consist=None, min_days=1)
    assert capped["fail_liq"].mean() <= free["fail_liq"].mean()


def test_consistency_raises_the_effective_target():
    dd = brownian_days(); days = make(dd, 200, 400)
    a = chal_life(days, 8000, 4, 2000.0, 1000.0, 1.0, 0.0, 200, fixed_nc(5), consist=None, min_days=1)["passed"].mean()
    b = chal_life(days, 8000, 4, 2000.0, 1000.0, 1.0, 0.0, 200, fixed_nc(5), consist=0.55, min_days=2)["passed"].mean()
    assert b <= a + 0.005


def test_calibrated_drift_hits_the_requested_wr():
    dd = brownian_days(D=2000)
    d = calib_drift(dd, 0.55, 150)
    t = s = 0
    from daydata import sim_day
    for side in (1, -1):
        k, _ = sim_day(dd, side, 1, 1e9, slip=0.0, sl=150, tp=150, fee=0.0, tick_usd=1.0, drift=d); t += (k == 0).mean(); s += ((k == 1) | (k == 2)).mean()
    assert abs(t / (t + s) - 0.55) < 0.005 and d > 0
