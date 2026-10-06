"""Pruebas de invariantes del motor de caja por firma (dd_cash/engine_firms.py). SANDBOX / R&D: offline, sin credenciales, solo lee data_cache/mes_5min_2y.parquet
(se omiten si el parquet no esta disponible). No toca produccion."""
import os, sys
import numpy as np
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
pytest.importorskip("numba")
pytestmark = pytest.mark.skipif(not os.path.exists(os.path.join(ROOT, "data_cache", "mes_5min_2y.parquet")), reason="falta data_cache/mes_5min_2y.parquet")

from dd_cash import engine_firms as ef          # noqa: E402


@pytest.fixture(scope="module")
def tables():
    from scripts.g2_real_rules_scan import build_tables
    return build_tables()


def _run(tables, name_part, n=1500, seed0=7, g2=False, **kw):
    specs = ef.firm_specs(g2=g2, **kw)
    name = next(k for k in specs if name_part in k)
    pay, fee, out = ef.run_firm(tables, name, specs[name], n_paths=n, seed0=seed0)
    return name, pay, fee, out


def test_cap_nc_values():
    assert ef.cap_nc(0, 40, 0.0, 0.0) == 40
    assert [ef.cap_nc(1, 0, b, b) for b in (0, 1500, 1501, 4000, 4001)] == [20, 20, 40, 40, 70]          # Bulenox: efectivo disponible, sube y baja
    assert [ef.cap_nc(2, 0, 0, p) for p in (0, 1499, 1500, 1999, 2000, 9999)] == [20, 20, 30, 30, 40, 40]  # Select: acumulativo por equity EOD maximo


def test_play_day_never_degenerate(tables):
    adv, tpt, flat = tables
    for G in (1.0, 50.0, 3000.0, 1e6):
        for dist in (1.0, 37.0, 2000.0, 1e6):
            for dll in (0.0, 1100.0):
                for rho_full in (True, False):
                    pnl = ef.play_day(adv, tpt, flat, 3, G, dist, dll, rho_full, 0.5, 40, 1.22, 40)
                    assert np.isfinite(pnl)


def test_reproducible_and_nonnegative(tables):
    for part in ("Topstep", "Tradeify Growth", "Select Flex", "Select Daily", "Qualification", "Momentum", "Fast Track"):
        a = _run(tables, part, n=300, g_f=600, rho=1.0)
        b = _run(tables, part, n=300, g_f=600, rho=1.0)
        assert np.array_equal(a[1], b[1]) and np.array_equal(a[2], b[2])
        assert (a[1] >= 0).all() and (a[2] >= 0).all()
        assert (a[3][:, 0] >= 1).all()                       # al menos una compra
        assert (a[3][:, 1] <= a[3][:, 0] + 1).all()          # fondeadas <= evaluaciones (+1 por Fast Track, que arranca fondeada)


def test_fees_at_least_initial_purchase(tables):
    for part, fee0 in (("Tradeify Growth", 145), ("Select Flex", 165), ("Qualification", 175), ("Momentum", 143), ("Fast Track", 488), ("Topstep", 49)):
        _, _, fee, _ = _run(tables, part, n=500, g_f=600, rho=1.0)
        assert (fee.sum(1) >= fee0 - 1e-9).all()


def test_payout_caps_respected(tables):
    caps = {"Topstep": 2000 * 0.9, "Tradeify Growth": 3000 * 0.9, "Select Flex": 2500 * 0.9, "Select Daily": 1250 * 0.9,
            "Momentum": 3000.0, "Fast Track": 2500.0}      # Bulenox: primeros $10,000 al 100%, por eso el tope neto = tope bruto
    for part, cap in caps.items():
        _, pay, _, out = _run(tables, part, n=3000, g_f=600, rho=1.0)
        assert out[:, 6].max() <= cap + 1e-6, (part, out[:, 6].max(), cap)


def test_no_payout_without_funded_account(tables):
    for part in ("Tradeify Growth", "Select Flex", "Qualification", "Momentum"):
        _, pay, _, out = _run(tables, part, n=1500, g_f=600, rho=1.0)
        no_funded = out[:, 1] == 0
        assert (pay[no_funded].sum(1) == 0).all()


def test_first_pass_consistent_with_rules_engine_and_dp(tables):
    """El primer pase de evaluacion del motor de caja debe caer cerca del motor de reglas ya validado y por debajo del techo de juego justo (+3pp de ruido)."""
    _, _, _, o = _run(tables, "Topstep", n=6000, g2=True)
    p_g2 = (o[:, 5] == 1).sum() / (o[:, 5] > 0).sum()
    assert 0.22 <= p_g2 <= 0.29                              # g2_real_rules_scan: 25.5-26.0%
    ceilings = {"Topstep": 0.327, "Tradeify Growth": 0.400, "Qualification": 0.455}
    for part, ceil in ceilings.items():
        _, _, _, o = _run(tables, part, n=6000)
        p = (o[:, 5] == 1).sum() / (o[:, 5] > 0).sum()
        assert 0.15 < p <= ceil + 0.03, (part, p)


def test_riskier_funded_policy_never_lowers_bust_churn(tables):
    """Politica fondeada muy conservadora => menos cuentas compradas por año que la mas agresiva (sanidad del modelo de quiebre)."""
    _, _, _, calm = _run(tables, "Tradeify Growth", n=1500, g_f=100, rho=0.2)
    _, _, _, bold = _run(tables, "Tradeify Growth", n=1500, g_f=600, rho=1.0)
    assert calm[:, 0].mean() < bold[:, 0].mean()


def test_summarize_shapes(tables):
    name, pay, fee, out = _run(tables, "Momentum", n=500)
    r = ef.summarize(name, pay, fee, out, ops=50.0)
    assert len(r["net_mensual_p50"]) == 12 and r["colchon_p95"] >= 0
