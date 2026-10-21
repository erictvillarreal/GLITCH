"""Parte D (7): cotas por WR (45 / 50 / 55 %) para el plan actual y el candidato b, con stop exacto y stop 0.5, y neto por XFA / anual. -> resultados_D7.md"""
import os, sys, time
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from run_partD import HDR, metrics, row
from worlds import MGC, drift_for_wr, gold_mask, mgc_days
from xfa_engine import BarDays, Rules, pol_fixed, simulate_life
SEED = 20261020; N = 50000
clean = mgc_days(True); mk = gold_mask(clean, True)
out = []; P = lambda s="": (print(s, flush=True), out.append(s))
P(f"# resultados_D7 (cotas por WR sobre W2 con deriva calibrada; N={N}; semilla {SEED}; reglas base; slip de entrada 0)\n"); P(HDR)
tab = {}
for frac in (0.0, 0.5):
    for wr in (0.45, 0.50, 0.55):
        dr = 0.0 if wr == 0.50 else drift_for_wr(clean, mk, wr)
        for cname, sl in (("a plan 3×364", 364), ("b 728×3", 728)):
            days = BarDays(clean, MGC["tick_usd"], MGC["fee"], sl, sl, slip=(0.0,), mask=mk, cush_max=9000.0, drift=dr, stop_frac=frac)
            r = simulate_life(days, Rules(), pol_fixed(3, sl, sl), n=N, seed=SEED)
            tab[(frac, wr, cname)] = (r["paid"].mean(), r["life"].mean())
            P(row(f"stop {frac:.1f}, WR {wr * 100:.0f} % (deriva {dr:+.0f}): {cname}", metrics(r)))
P("\n## Neto por XFA y neto anual por cuenta según WR (Combine P0 con slip mezcla {1,3}: P(pase) 19.9 %, costo de obtener la XFA $395, 8.5 días hasta pasar; y Combine con finish-line: 26.9 %, $331, 6.7 días)\n")
P("| stop | WR | candidato | cobrado por XFA | neto por XFA (P0 / P3) | neto anual por cuenta (P0 / P3) |\n|---|---|---|---|---|---|")
for (frac, wr, cname), (paid, life) in tab.items():
    c0, c3 = 49 / .199 + 149, 49 / .269 + 149
    n0 = 252 / (1.7 / .199 + life + 1); n3 = 252 / (1.8 / .269 + life + 1)
    P(f"| {frac:.1f} | {wr * 100:.0f} % | {cname} | ${paid:,.0f} | ${paid - c0:,.0f} / ${paid - c3:,.0f} | ${n0 * (paid - c0) - 714:,.0f} / ${n3 * (paid - c3) - 714:,.0f} |")
open(os.path.join(HERE, "resultados_D7.md"), "w").write("\n".join(out))
