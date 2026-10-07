"""Validacion cruzada: el simulador numba por barra (bulenox/barsim.day_bar) debe coincidir con el motor de reglas Python (bulenox/account.py) dia por dia. SANDBOX / R&D."""
import os, sys
import numpy as np
import pytest
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
pytestmark = pytest.mark.skipif(not os.path.exists(os.path.join(ROOT, "data_cache", "mes_5min_2y.parquet")), reason="falta mes_5min_2y.parquet")
from bulenox.rules import plan
from bulenox.account import BulenoxAccount, Breach
from bulenox import barsim


@pytest.mark.parametrize("opt,dd,dll", [(2, 2500.0, 1100.0), (1, 2500.0, 0.0), (2, 2250.0, 1200.0)])
def test_day_bar_matches_account_engine(opt, dd, dll):
    bars = barsim.build_bars("MES", 585)
    rng = np.random.default_rng(3)
    p = plan("momentum", 50_000, opt) if dd == 2250.0 else plan("qualification", 50_000, opt)
    ok = 0
    for trial in range(400):
        di = int(rng.integers(0, len(bars["start"])))
        s, e, side = int(bars["start"][di]), int(bars["end"][di]), int(bars["side"][di])
        nc = int(rng.integers(1, 21)); tp = int(rng.integers(5, 200)); sl = int(rng.integers(5, 200))
        bal0 = float(rng.integers(-1500, 2500)); 
        # estado inicial coherente con Opcion/umbral
        if opt == 2: thr0 = max(-dd, bal0 - dd) if bal0 > 0 else -dd; peak0 = max(bal0, 0.0)
        else: thr0 = max(-dd, bal0 - dd) if bal0 > 0 else -dd; peak0 = max(bal0, 0.0)
        if bal0 <= thr0: continue
        r = barsim.day_bar(bars["H"], bars["L"], bars["C"], s, e, side, nc, tp, sl, bars["tick"], bars["tv"], bars["comm_side"], bal0, thr0, peak0, dll, opt, dd, 1e18, False)
        bal, thr, peak, br, hit, dpnl, lk = r
        a = BulenoxAccount(p, prod="MES", tick=0.25, tv=1.25)
        a.balance = bal0; a.threshold = thr0; a.peak_equity = peak0; a.max_close = max(bal0, 0.0)
        H, L, C = bars["H"][s:e + 1], bars["L"][s:e + 1], bars["C"][s:e + 1]
        ent = C[0]
        try:
            a.open(side, nc, float(ent), tp=float(ent + side * tp * 0.25), sl=float(ent - side * sl * 0.25))
            for j in range(1, len(C)):
                a.bar(float(H[j]), float(L[j]), float(C[j]), float(C[j - 1]))
                if a.pos is None or a.status != "active": break
            if a.pos is not None: a.flatten(float(C[-1]))
            if a.pos is None and a.status == "active" and a.balance <= a.threshold: a.status = "suspended"
        except Breach:
            pass
        assert (a.status == "suspended") == (br == 1), (trial, a.events, br)
        if br == 0:
            assert abs(a.balance - bal) < 1e-6, (trial, a.balance, bal, a.events)
            assert (a.dll_hit == bool(hit)) or opt == 1
        ok += 1
    assert ok > 250


def test_fair_world_respects_theoretical_ceilings():
    """En el mundo justo sintetico el pase por intento no puede superar los techos teoricos: Opcion 2 (D=2,500, T=3,000, sin consistencia) 45.5%; Opcion 1 (drawdown dinamico) ~30.1% + ruido."""
    rng = np.random.default_rng(5)
    syn = [barsim.build_bars_synthetic("MES", 585, rng) for _ in range(6)]
    for opt, cap in ((2, 0.47), (1, 0.34)):
        pl = plan("qualification", 50_000, opt)
        best = max(np.mean([(barsim.run_qual(b, pl, tp, gf, n=1000, seed0=3 + i)[:, 0] == 1).mean() for i, b in enumerate(syn)]) for tp in (20, 60, 100) for gf in (0.3, 0.75, 1.0))
        assert best <= cap, (opt, best)


def test_topstep_combine_in_barsim_matches_rules_engine():
    """Combine Topstep 50K (consistencia 55%, min 2 dias, piso en $0): ~33% por intento, igual que scripts/pass_rate_bold_real.py (33.6%)."""
    from bulenox.rules import Plan
    tq = Plan("topstep_combine", 2, 50_000, 49.0, 3_000.0, 2_000.0, None, (4,))
    bars = barsim.build_bars("MES", 585)
    r = barsim.run_qual(bars, tq, 30, 0.55, n=15000, seed0=3, slip=0.0, lock_cap=0.0, cons=0.55, min_days=2, max_days=30)
    assert 0.29 <= (r[:, 0] == 1).mean() <= 0.37


def test_topstep_xfa_baseline_close_to_logged_number():
    bars = barsim.build_bars("MGC", 433)
    r = barsim.run_funded(bars, "topstep_xfa", None, 1092, 1.0, 364, n=6000, seed0=2, slip=0.0)
    assert 450 <= r["payout"] <= 900
