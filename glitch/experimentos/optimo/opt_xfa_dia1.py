"""Riesgo de morir pronto (día 1 y primeros 3 días) de los planes de XFA, a WR 47.4 %: 3x364 (hoy), 3x728 fijo, regla 5->1 @ $1,500 con bracket 728, y la misma con 1 micro el día 1. Misma definición que parteJ/j8 (life <= d & dead).
GLITCH_MGC_PARQUET=... PYTHONPATH=../.. python3 opt_xfa_dia1.py   MODELADO (MGC XFA 50K, slippage empírico 8 obs., 8.ª inferida = 0, NO VERIFICADA)."""
import os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [os.path.join(HERE, "..", "xfa"), os.path.join(HERE, "..", "preservacion"), os.path.join(HERE, "..", "labs")]
from labs_motor import calib_drift
from worlds import MGC, gold_mask, mgc_days
from xfa_engine import BarDays, Policy, Rules, pol_fixed, simulate_life
EMP8 = (-1.0, 0.0, 1.0, 3.0); EMP8_P = (1 / 8, 3 / 8, 2 / 8, 2 / 8)
clean = mgc_days(True); gm = gold_mask(clean, True)
r_ = np.maximum(clean.hi.max(1), 0) - np.minimum(clean.lo.min(1), 0); HALF = int(round(np.median(r_) / 2))
dm = calib_drift(clean, 0.474, HALF)
def rule(hi, U, lo, sl): return Policy("r", lambda st: np.where(st.b < U, hi, lo).astype(int), "max", sl, sl)
def rule_d1(hi, U, lo, sl): return Policy("r1", lambda st: np.where(st.t == 0, 1, np.where(st.b < U, hi, lo)).astype(int), "max", sl, sl)
out = ["# resultados_OPT_XFA_DIA1 — riesgo de morir pronto, WR 47.4 % (MODELADO)\n", "| plan | cobrado medio | P(≥ 1 pago) | P(muerte día 1) | P(muerte ≤ 3 días) | vida media (días) |\n|---|---|---|---|---|---|"]
for nm, sl, pol in (("3×364 fijo (hoy)", 364, pol_fixed(3, 364, 364)), ("3×728 fijo", 728, pol_fixed(3, 728, 728)), ("regla 5→1 @ $1,500, bracket 728", 728, rule(5, 1500, 1, 728)), ("regla 5→1 @ $1,500, bracket 728, 1 micro el día 1", 728, rule_d1(5, 1500, 1, 728))):
    days = BarDays(clean, MGC["tick_usd"], MGC["fee"], sl, sl, slip=EMP8, slip_p=EMP8_P, mask=gm, cush_max=9000.0, stop_frac=0.5, drift=dm)
    r = simulate_life(days, Rules(), pol, n=40000, seed=22); dead = ~r["alive"] if "alive" in r else np.ones(len(r["life"]), bool)
    d1 = ((r["life"] <= 1) & dead).mean(); d3 = ((r["life"] <= 3) & dead).mean()
    out.append(f"| {nm} | ${r['paid'].mean():,.0f} | {(r['npay'] >= 1).mean() * 100:.1f} % | {d1 * 100:.1f} % | {d3 * 100:.1f} % | {r['life'].mean():.1f} |"); print(out[-1], flush=True)
open(os.path.join(HERE, "resultados_OPT_XFA_DIA1.md"), "w", encoding="utf-8").write("\n".join(out) + "\n")
