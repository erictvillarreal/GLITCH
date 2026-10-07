"""Pruebas del laboratorio XFA (dd_cash/xfa_lab.py) y del techo de juego justo (scripts/xfa_dp_ceiling.py). SANDBOX / R&D, offline. Se omiten si faltan los parquets."""
import os, sys
import numpy as np
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
need = [os.path.join(ROOT, "data_cache", "mgc_5min_2y_corrected_window.parquet"), os.path.join(ROOT, "data_cache", "mes_5min_2y.parquet")]
pytestmark = pytest.mark.skipif(not all(os.path.exists(p) for p in need), reason="faltan parquets")


def test_dp_ceiling_value_and_bound():
    from scripts.xfa_dp_ceiling import topstep
    v = topstep(days=40)
    assert 1300 <= v <= 1380                     # $1,341 documentado
    assert v <= 0.9 * 2000                       # cota analitica: 0.9 * MLL
    assert topstep(days=40, cost=50.0) < v       # los costos solo restan


def test_cerebro2_baseline_matches_logged_xfa_number():
    """Log 24/25-sep (50K, nc3, MGC 364/364): payout medio $620 y P(>=1 pago) 31.6% con liquidacion en tiempo real."""
    from scripts.tables_generic import build
    from dd_cash.xfa_lab import run_life
    tab = build("MGC", 7 * 60 + 13)
    r = run_life(tab, "Topstep XFA 50K", g=1092, rho=0, tp=364, slfix=364, H=126, n=6000, seed0=1)
    assert 480 <= r["payout"] <= 720 and 0.25 <= r["p1"] <= 0.37


def test_tight_stop_gain_is_a_fill_assumption_artifact():
    """Con stops diminutos, el valor depende de asumir fills exactos: con llenado en el extremo de la barra desaparece."""
    from scripts.tables_generic import build
    from dd_cash.xfa_lab import run_life
    tab = build("MGC", 7 * 60 + 13)
    exact = run_life(tab, "Topstep XFA 50K", 4500, 0.1, 286, H=126, n=3000, seed0=2, slip=0.0)["payout"]
    worst = run_life(tab, "Topstep XFA 50K", 4500, 0.1, 286, H=126, n=3000, seed0=2, slip=1.0)["payout"]
    assert exact > 2000 and worst < exact / 5


def test_synthetic_world_is_symmetric_and_sized_like_real():
    from scripts.tables_generic import build, build_synthetic
    rng = np.random.default_rng(1)
    syn = build_synthetic("MES", 585, rng); real = build("MES", 585)
    assert len(syn["adv"]) == len(real["adv"]) and syn["adv"].shape == real["adv"].shape
