"""dd_cash/lever_engine.simulate(legacy=True) debe reproducir engine_real_cal.simulate (take, pases, pagos, quiebres, fees salvo la tarifa inicial, que el motor de palancas SI cobra en fee_d).
SANDBOX / R&D, offline. Se omite si faltan los parquets de MES/MGC en data_cache."""
import os, sys
import numpy as np
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
pytestmark = pytest.mark.skipif(not (os.path.exists(os.path.join(ROOT, "data_cache", "mes_5min_2y.parquet"))
                                     and os.path.exists(os.path.join(ROOT, "data_cache", "mgc_5min_2y_corrected_window.parquet"))),
                                reason="faltan parquets de MES/MGC")


def test_legacy_matches_engine_real_cal():
    from scripts.decision_breakdown import setup, H, SKIP
    from dd_cash.engine_real_cal import simulate as sim0
    from dd_cash import lever_data as LD
    from dd_cash.lever_engine import simulate as simL
    acc, real, nd = setup("50K", 40, 32, 100, 3)
    S, axis = LD.make_spec(nc=40, tp=32, sl=100, nc_x=3, legacy=True)
    assert len(axis) == nd
    D = np.random.default_rng(5).integers(0, nd, (1500, H))
    a = sim0(acc, D, real=real, lag=2, skip=SKIP); b = simL(S, D, lag=2, skip=SKIP)
    for k in ("take_d", "n_pass", "n_pay", "n_b0", "n_b1"):
        assert np.array_equal(a[k], b[k]), k
    fd = b["fee_d"].copy(); fd[:, 0] -= 49.0
    assert np.array_equal(a["fee_d"], fd)


def test_corrected_rules_never_pay_more_than_legacy():
    from scripts.decision_breakdown import H, SKIP
    from dd_cash import lever_data as LD
    from dd_cash.lever_engine import simulate as simL
    S0, axis = LD.make_spec(legacy=True); S1, _ = LD.make_spec(legacy=False)
    D = np.random.default_rng(9).integers(0, len(axis), (3000, H))
    a = simL(S0, D, lag=2, skip=SKIP)["take_d"].sum(); b = simL(S1, D, lag=2, skip=SKIP)["take_d"].sum()
    assert b <= a * 1.02


def test_start_array_zero_equals_default_and_late_start_shifts():
    from scripts.decision_breakdown import H, SKIP
    from dd_cash import lever_data as LD
    from dd_cash.lever_engine import simulate as simL
    S, axis = LD.make_spec(legacy=False)
    D = np.random.default_rng(3).integers(0, len(axis), (2000, H))
    a = simL(S, D, lag=2, skip=SKIP); b = simL(S, D, lag=2, skip=SKIP, start=np.zeros(2000, int))
    for k in ("take_d", "fee_d", "n_att", "n_pass"):
        assert np.array_equal(a[k], b[k]), k
    st = np.full(2000, 40)
    c = simL(S, D, lag=2, skip=SKIP, start=st)
    assert c["take_d"][:, :40].sum() == 0 and c["fee_d"][:, :40].sum() == 0 and (c["fee_d"][:, 40] >= 49).all()
    never = simL(S, D, lag=2, skip=SKIP, start=np.full(2000, 10 ** 6))
    assert never["take_d"].sum() == 0 and never["fee_d"].sum() == 0


def test_entry_slip_never_helps():
    from scripts.decision_breakdown import H, SKIP
    import dataclasses as dc
    from dd_cash import lever_data as LD
    from dd_cash.lever_engine import simulate as simL
    S, axis = LD.make_spec(legacy=False, slip=0.5)
    D = np.random.default_rng(4).integers(0, len(axis), (4000, H))
    a = simL(S, D, lag=2, skip=SKIP); b = simL(dc.replace(S, entry_slip=2), D, lag=2, skip=SKIP)
    assert b["take_d"].sum() - b["fee_d"].sum() < a["take_d"].sum() - a["fee_d"].sum()
