"""engine_real_cal.simulate (copia con calendario) debe reproducir exactamente engine_real.simulate cuando lag es escalar y skip=None.
SANDBOX / R&D, offline. Se omite si faltan los parquets de MES/MGC en data_cache."""
import os, sys
import numpy as np
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
pytest.importorskip("numba") if False else None
pytestmark = pytest.mark.skipif(not (os.path.exists(os.path.join(ROOT, "data_cache", "mes_5min_2y.parquet"))
                                     and os.path.exists(os.path.join(ROOT, "data_cache", "mgc_5min_2y_corrected_window.parquet"))),
                                reason="faltan parquets de MES/MGC")


def _setup():
    from dd_cash.real_pnl import setup
    return setup(40, 40, 100)


@pytest.mark.parametrize("lag", [0, 2])
def test_matches_original_engine(lag):
    from dd_cash import engine_real, engine_real_cal
    acc, real, nd = _setup()
    D = np.random.default_rng(5).integers(0, nd, (800, 126))
    a = engine_real.simulate(acc, D, real=real, lag=lag)
    b = engine_real_cal.simulate(acc, D, real=real, lag=lag)
    for k in ("cum", "take_d", "fee_d", "n_pass", "n_att", "n_pay"):
        assert np.array_equal(a[k], b[k]), k


def test_per_day_lag_array_equal_to_scalar():
    from dd_cash import engine_real_cal
    acc, real, nd = _setup()
    D = np.random.default_rng(6).integers(0, nd, (500, 80))
    a = engine_real_cal.simulate(acc, D, real=real, lag=3)
    b = engine_real_cal.simulate(acc, D, real=real, lag=np.full(80, 3))
    assert np.array_equal(a["cum"], b["cum"])


def test_late_handoff_never_pays_before_handoff_day():
    from dd_cash import engine_real_cal
    acc, real, nd = _setup()
    H, start = 80, 50
    lag = np.array([max(2, start - d) for d in range(H)])
    D = np.random.default_rng(7).integers(0, nd, (1500, H))
    r = engine_real_cal.simulate(acc, D, real=real, lag=lag)
    assert (r["take_d"][:, :start] == 0).all()


def test_skip_days_have_no_pnl():
    from dd_cash import engine_real_cal
    acc, real, nd = _setup()
    H = 40
    skip = np.zeros(H, bool); skip[[10, 25]] = True
    D = np.random.default_rng(8).integers(0, nd, (600, H))
    r = engine_real_cal.simulate(acc, D, real=real, lag=0, skip=skip)
    assert (r["take_d"][:, skip] == 0).all()
