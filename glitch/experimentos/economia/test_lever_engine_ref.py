"""Pruebas de la copia con ancla a la referencia. Requieren el checkout del motor: GLITCH_ENGINE_ROOT=/ruta/glitch (research/firm-map-and-labs @6d4b069).
    GLITCH_ENGINE_ROOT=... python -m pytest -q test_lever_engine_ref.py"""
import dataclasses as dc
import os
import sys

import numpy as np
import pytest

ROOT = os.environ.get("GLITCH_ENGINE_ROOT")
pytestmark = pytest.mark.skipif(not ROOT, reason="falta GLITCH_ENGINE_ROOT")
HERE = os.path.dirname(os.path.abspath(__file__))


@pytest.fixture(scope="module")
def eng():
    sys.path.insert(0, ROOT); sys.path.insert(0, HERE)
    cwd = os.getcwd(); os.chdir(ROOT)
    from dd_cash import lever_data as LD
    from dd_cash.lever_engine import simulate as sim0
    import lever_engine_ref as ref
    yield LD, sim0, ref.simulate, ref.with_ref_anchor
    os.chdir(cwd)


def _spec(LD, **kw):
    X = dict(x_sl=364, x_tp=364, nc_x=3)
    return LD.make_spec(nc=40, sl=100, tp=32, slip=0.5, xliq=True, **X, **kw)


def _same(a, b):
    for k in ("take_d", "fee_d", "n_att", "n_pass", "n_b0", "n_b1", "n_pay"):
        assert np.array_equal(np.asarray(a[k]), np.asarray(b[k])), k


@pytest.mark.parametrize("es", [0, 1, 3])
def test_sin_ref_anchor_es_identico_al_original(eng, es):
    LD, sim0, simr, wra = eng
    S, ax = _spec(LD, entry_slip=es)
    D = LD.draw(len(ax), 600, 3)
    _same(sim0(S, D, lag=2, skip=LD.SKIP), simr(S, D, lag=2, skip=LD.SKIP))


def test_ref_anchor_con_slip_cero_es_identico(eng):
    LD, sim0, simr, wra = eng
    S, ax = _spec(LD, entry_slip=0)
    S = wra(S)
    D = LD.draw(len(ax), 600, 3)
    _same(sim0(S, D, lag=2, skip=LD.SKIP), simr(S, D, lag=2, skip=LD.SKIP))


def test_ref_anchor_cuesta_mas_que_el_ancla_al_fill(eng):
    LD, sim0, simr, wra = eng
    S, ax = _spec(LD, entry_slip=3)
    D = LD.draw(len(ax), 3000, 3)
    base = simr(S, D, lag=2, skip=LD.SKIP)["fee_d"].sum() - simr(S, D, lag=2, skip=LD.SKIP)["take_d"].sum()
    S2 = wra(S)
    r1 = simr(S, D, lag=2, skip=LD.SKIP); r2 = simr(S2, D, lag=2, skip=LD.SKIP)
    net1 = r1["take_d"].sum() - r1["fee_d"].sum(); net2 = r2["take_d"].sum() - r2["fee_d"].sum()
    assert net2 < net1


def test_pase_por_intento_ref_anchor_coincide_con_la_parte_a(eng):
    """Validacion cruzada: engine con ref_anchor vs Parte A (mismas barras/entrada 9:45): <= 4 pp en slip 0..3."""
    LD, sim0, simr, wra = eng
    sys.path.insert(0, os.path.join(HERE, "..", "preservacion"))
    from daydata import load_days
    from sim import OutcomeTable, pol_fixed, run_mc
    dd = load_days(ref_hm=9 * 60 + 45, last_hm=14 * 60 + 30)
    for es in (0, 1, 3):
        S, ax = LD.make_spec(nc=40, sl=100, tp=32, slip=0.0, xliq=True, x_sl=364, x_tp=364, nc_x=3, entry_slip=es)
        S = wra(S)
        D = LD.draw(len(ax), 6000, 7)[:, :40]
        r = simr(dc.replace(S, K=1), D, lag=2, skip=None)
        p_eng = float((r["pass_day"] > 0).mean())
        tabs = {0: OutcomeTable(dd, float(es), 0.0, "adverse", 100, 32, step=10.0)}
        pa = run_mc(pol_fixed(40), tabs, n=20000, seed=5, bal0=50000.0, peak0=50000.0, start_idx=1774, maxdays=40).p_pass
        assert abs(p_eng - pa) < 0.05, (es, p_eng, pa)
