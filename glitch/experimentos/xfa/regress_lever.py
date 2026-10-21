"""Regresion del xfa_engine contra el motor publicado (scripts/xfa_liquidation_check.py, rama research/g2-consistency-check; mismas tablas MGC de 5 min).
Referencia publicada (50K nc3, SL=TP=364, 30,000 vidas): lock oficial $0 -> $620, P(>=1 pago) 31.6 %, vida 9.2 d ; lock del codigo (+MLL) -> $484, 29.2 %.
Uso: python regress_lever.py --engine-root <checkout research/firm-map-and-labs @6d4b069>/glitch"""
import argparse, os, sys
import numpy as np
ap = argparse.ArgumentParser(); ap.add_argument("--engine-root", required=True); ap.add_argument("--n", type=int, default=200000); a = ap.parse_args()
sys.path.insert(0, os.path.abspath(a.engine_root)); os.chdir(a.engine_root)
from scripts.xfa_liquidation_check import tables, xfa as ref_xfa
from core.funded_account import XFA_50K
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from xfa_engine import Rules, TableDays, pol_fixed, simulate_life
T = tables("mgc_5min_2y_corrected_window", 0.10, 7 * 60 + 13, 14 * 60 + 30)
days = TableDays(*T, tv=1.0, comm=1.92, sl=364, tp=364)
out = []
for lbl, lock in (("lock oficial $0", 0.0), ("lock del codigo +MLL", 2000.0)):
    r0 = ref_xfa(T, XFA_50K, 3, 364, 364, 1.0, 1.92, True, lock, n=60000, seed=7)
    R = Rules(lock=lock, minpay=0.0, profit_rule=False, scaling=False, idle_close_days=10 ** 6)
    res = simulate_life(days, R, pol_fixed(3), n=a.n, seed=11)
    p = (res["npay"] > 0).mean(); se = np.sqrt(p * (1 - p) / a.n)
    out.append(f"{lbl}: referencia (30k vidas) pago medio ${r0['mean']:,.0f}, P(>=1) {r0['p_any']:.3f}, vida {r0['life']:.1f} | xfa_engine ({a.n} vidas) pago medio ${res['paid'].mean():,.0f} (EE ${res['paid'].std() / np.sqrt(a.n):.1f}), P(>=1) {p:.3f} (EE {se:.3f}), vida {res['life'].mean():.1f}")
print("\n".join(out)); open(os.path.join(HERE, "regress_lever.txt"), "w").write("\n".join(out) + "\n")
