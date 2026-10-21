"""Metricas adicionales de §2.7 (miedo literal de Eric): P(liquidar | llego a <= $200 / <= $100 de la meta), peor dia y balance al cierre de manana. M2 iid, estado de partida, n=50000, semilla 20261021."""
import sys
sys.path.insert(0, ".")
import numpy as np
from daydata import load_days
from sim import *
dd = load_days(); mix = ([1, 3], [0.5, 0.5])
tabs = {s: OutcomeTable(dd, float(s), 3.0, "adverse", 100, 32, step=10.0) for s in (1, 3)}
out = []; P = lambda s: (print(s), out.append(s))
P("| politica | P(pase) | P(liq) total | P(liq \\| llegue a <=$200 de la meta) | P(liq \\| llegue a <=$100) | peor dia ($) | P(cierre manana < 50,000) | balance mediano al cierre de manana |")
P("|---|---|---|---|---|---|---|---|")
for name, pol in (("P0 40 fijo", pol_fixed(40)), ("P1 25 fijo", pol_fixed(25)), ("P2 SL-safe (14)", pol_p2()), ("P3 finish-line", pol_p3()), ("P4b 40 hoy y P4", pol_p4b())):
    r = run_mc(pol, tabs, n=50000, seed=20261021, bal0=51401.2, peak0=51401.2, slip_mix=mix, consistency_mode="pct55")
    b1 = r.bal_end_day1
    P(f"| {name} | {r.p_pass * 100:.1f}% | {r.p_liq * 100:.1f}% | {r.p_liq_near['<=200'] * 100:.1f}% | {r.p_liq_near['<=100'] * 100:.1f}% | {r.worst_day:,.0f} | {np.mean(b1 < 49500) * 100:.1f}% | {np.median(b1):,.0f} |")
open("extra_stats.md", "w").write("\n".join(out))
