"""Pruebas de regresion de la Parte A (encargo §2.2) y de la mecanica del simulador.

    cd experimentos/preservacion && python -m pytest -q test_regression.py
"""
import math
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(__file__))
from daydata import DEFAULT_PARQUET, FEE_RT, TICK_USD, DayData, load_days, sim_day  # noqa: E402
from m1 import make_days  # noqa: E402
from sim import (NC_MAX, Ctx, OutcomeTable, pol_fixed, pol_p2, pol_p3, pol_p4, pol_p4b, pol_p5, run_mc,  # noqa: E402
                 sl_full_cost_per_contract, tp_net_per_contract)

K = 59


def one_day(hi_path, lo_path=None, cl_end=0.0):
    """DayData de UN dia con barras planas salvo las indicadas (ticks respecto a la referencia, lado LONG)."""
    hi = np.zeros((1, K)); lo = np.zeros((1, K)); cl = np.zeros((1, K)); op = np.zeros((1, K))
    for k, v in (hi_path or {}).items(): hi[0, k] = v
    for k, v in (lo_path or {}).items(): lo[0, k] = v
    cl[0, -1] = cl_end
    return DayData([None], np.zeros(1), op, hi, lo, cl, [])


# ── mecanica del dia ──────────────────────────────────────────────────────────────────────────────────────────
def test_tp_pnl_exacto():
    k, p = sim_day(one_day({10: 33}), 1, 10, 2000.0, slip=1.0, exit_slip=0)
    assert k[0] == 0 and p[0] == pytest.approx((32 - 1) * 10 * TICK_USD - 10 * FEE_RT)


def test_sl_cuando_stop_mas_cerca_que_el_piso():
    # nc=10: liquidacion a 160 ticks > SL 100 -> el stop se dispara primero
    k, p = sim_day(one_day(None, {10: -101}), 1, 10, 2000.0, slip=1.0, exit_slip=3.0)
    assert k[0] == 1 and p[0] == pytest.approx(-(100 + 1 + 3) * 10 * TICK_USD - 10 * FEE_RT)


def test_liquidacion_cuando_el_piso_esta_mas_cerca_que_el_stop():
    # nc=40: piso a 40 ticks del fill (slip 1 -> 39 desde la referencia) -> LIQ, perdida = colchon exacto
    k, p = sim_day(one_day(None, {10: -60}), 1, 40, 2000.0, slip=1.0, exit_slip=3.0)
    assert k[0] == 2 and p[0] == pytest.approx(-2000.0)


def test_barra_con_tp_y_liquidacion_asume_adverso_primero():
    d = one_day({10: 40}, {10: -60})
    k, _ = sim_day(d, 1, 40, 2000.0, slip=1.0, order="adverse")
    assert k[0] == 2
    # con orden OHLC y barra alcista (cl>=op) el minimo llega primero para LONG -> tambien adverso; barra bajista -> TP primero
    d2 = one_day({10: 40}, {10: -60}); d2.cl[0, 10] = -5.0; d2.op[0, 10] = 0.0
    k2, _ = sim_day(d2, 1, 40, 2000.0, slip=1.0, order="ohlc")
    assert k2[0] == 0


def test_flatten_pnl():
    k, p = sim_day(one_day(None, None, cl_end=10.0), 1, 10, 2000.0, slip=1.0)
    assert k[0] == 3 and p[0] == pytest.approx((10 - 1) * 10 * TICK_USD - 10 * FEE_RT)


def test_short_es_simetrico_al_long():
    d = one_day({10: 33})                      # sube 33: TP para LONG, adverso para SHORT
    ks, _ = sim_day(d, -1, 10, 2000.0, slip=0.0)
    assert ks[0] != 0                          # un short no toma TP con esa barra
    d2 = one_day(None, {10: -33})
    ks2, ps2 = sim_day(d2, -1, 10, 2000.0, slip=0.0)
    assert ks2[0] == 0                         # el short SI toma TP si el precio baja 33


# ── el nc maximo SL-safe nunca liquida (analitico, peor caso) ───────────────────────────────────────────────────
def test_sl_safe_nunca_liquida_en_el_peor_caso():
    cost = sl_full_cost_per_contract()
    cushion = 2000.0
    nc = int(math.floor(cushion / cost))
    assert nc == 14 and cushion - nc * cost > 0           # margen positivo
    d = one_day(None, {5: -150})                          # la peor barra: pasa el stop y mas
    k, p = sim_day(d, 1, nc, cushion, slip=3.0, exit_slip=3.0)
    assert k[0] == 1 and -p[0] <= cushion                 # SL, no LIQ, y la perdida cabe en el colchon
    k15, _ = sim_day(d, 1, nc + 1, cushion, slip=3.0, exit_slip=3.0)
    assert k15[0] == 2                                    # un contrato mas ya puede liquidar


# ── la consistencia nunca liga con TP 32 y nc <= 40 ───────────────────────────────────────────────────────────
@pytest.mark.parametrize("nc", [1, 10, 20, 40])
def test_mejor_dia_posible_menor_que_1650(nc):
    best = (32 * nc * TICK_USD) - nc * FEE_RT            # slip 0, mejor caso
    assert best < 1650.0


# ── chequeo de cordura: ninguna politica sin deriva supera (b-f)/(T-f) ───────────────────────────────────────────
@pytest.fixture(scope="module")
def brownian_days():
    prof = np.full(K, 1.0 / K)
    return make_days(8000, 100.0, 0.0, prof, seed=3, m=8)


def frictionless_tabs(dd):
    return {0: OutcomeTable(dd, 0.0, 0.0, "adverse", 100, 32, fee=0.0)}


def test_techo_teorico_martingala(brownian_days):
    tabs = frictionless_tabs(brownian_days)
    ceiling = (51401.2 - 49401.2) / (53000.0 - 49401.2)       # 55.6 %
    for pol in (pol_fixed(40), pol_p3(), pol_fixed(20), pol_p2(), pol_p4b()):
        r = run_mc(pol, tabs, n=20000, seed=7, bal0=51401.2, peak0=51401.2, consistency=False)
        assert r.ci_pass[0] <= ceiling + 0.004                 # el limite inferior del IC no puede superar el techo (+tolerancia discreta)


def test_barrera_nominal_32_antes_de_40(brownian_days):
    # P(+32 antes de -40) = 40/72 = 55.6 %: entre quienes resuelven (TP vs LIQ), sin slip ni comision
    k, _ = sim_day(brownian_days, 1, 40, 2000.0, slip=0.0, exit_slip=0.0, fee=0.0)
    tp, lq = (k == 0).sum(), (k == 2).sum()
    assert tp / (tp + lq) == pytest.approx(40 / 72, abs=0.02)
    # dos victorias seguidas ~ 30.9 % (el engine del 12-oct daba 30.8 %)
    assert (tp / (tp + lq)) ** 2 == pytest.approx(0.309, abs=0.02)


def test_20_contratos_71_por_dia_y_4_victorias(brownian_days):
    k, p = sim_day(brownian_days, 1, 20, 2000.0, slip=0.0, exit_slip=0.0, fee=0.0)
    tp, lq = (k == 0).sum(), (k == 2).sum()
    assert tp / (tp + lq) == pytest.approx(80 / 112, abs=0.02)           # 71.4 %
    assert math.ceil(3000 / (32 * 20 * TICK_USD)) == 4                   # ~4 victorias para llegar a $3,000 (slip 0, sin comision)
    # nota: el '~26 % de pase' del doc 7-oct es 0.714**4 = 26.0 % (ignora el ratchet); no se re-simula aqui.
    assert 0.714 ** 4 == pytest.approx(0.26, abs=0.005)


# ── politicas: formulas y tope ────────────────────────────────────────────────────────────────────────────────
def ctx(need, bal, peak, t=0, side=-1):
    bal = np.atleast_1d(np.asarray(bal, float)); peak = np.atleast_1d(np.asarray(peak, float)); need = np.atleast_1d(np.asarray(need, float))
    floor = np.minimum(peak - 2000.0, 50000.0)
    return Ctx(need, bal, peak, floor, bal - floor, side, t)


def test_politicas_nunca_exceden_el_tope_ni_bajan_de_1():
    rng = np.random.default_rng(0)
    bal = rng.uniform(48100, 52990, 2000); peak = np.maximum(bal, rng.uniform(50000, 52500, 2000))
    c = ctx(53000 - bal, bal, peak)
    for pol in (pol_p2(), pol_p3(), pol_p4(), pol_p4b(), pol_p5(), pol_fixed(40)):
        n = pol(c)
        assert n.min() >= 1 and n.max() <= NC_MAX


def test_p2_desde_el_estado_actual_es_14():
    assert pol_p2()(ctx([1598.8], [51401.2], [51401.2]))[0] == 14


def test_p3_cubre_el_faltante_si_cabe_en_el_tope():
    per = tp_net_per_contract()
    for need in (50.0, 100.0, 400.0, 1000.0):
        n = int(pol_p3()(ctx([need], [53000 - need], [53000 - need]))[0])
        assert n * per >= need - 1e-9 and (n - 1) * per < need


# ── DP vs Monte Carlo (misma rejilla) ───────────────────────────────────────────────────────────────────────────────
@pytest.mark.skipif(not os.path.exists(DEFAULT_PARQUET), reason="falta el parquet de MES")
def test_dp_coincide_con_mc():
    import dp as DP
    dd = load_days()
    H, LIQ = DP.build_hist(dd, [1, 3], [0.5, 0.5], 3.0)
    Vs, pols = DP.solve(H, LIQ, 1775, horizon=60)
    pi, bi = DP.idx_state(51400.0, 51400.0)
    tabs = {s: OutcomeTable(dd, s, 3.0, step=25.0) for s in (1, 3)}
    r = run_mc(DP.policy_from_dp(pols, 1775), tabs, n=30000, seed=2, bal0=51400.0, peak0=51400.0, slip_mix=([1, 3], [0.5, 0.5]), snap=25.0)
    assert abs(Vs[0, pi, bi] - r.p_pass) < 0.012
    assert Vs[0, pi, bi] <= (51400.0 - 49400.0) / 3600.0 + 1e-9          # y respeta el techo teorico
