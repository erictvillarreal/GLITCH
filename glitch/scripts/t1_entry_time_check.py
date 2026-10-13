"""T1 addendum — el scheduler de produccion (origin/main) usa ENTRY_GATE_MINUTES = 9:35 CT para la entrada real de MES, mientras todo el modelo (tablas, structural-levers, T1) entra a las 9:45 CT.
Sensibilidad del Combine (nc 40, TP32/TP40, SL100) a la hora de entrada. SANDBOX. Uso: python -m scripts.t1_entry_time_check"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np, dataclasses as dc
from dd_cash import lever_data as LD
from dd_cash.lever_engine import simulate
from scripts.lever_common import run, OPS12
lines = []; P = lambda s: (print(s), lines.append(s))
T = 20000
P("Hora de entrada de MES en el Combine (CT) vs. modelo (9:45). XFA vigente 364x3. Pase por intento (1 intento) y neto anual 1 cuenta tras $714, justo / CON oro / SIN oro")
P(f"{'entrada':>8s} {'TP':>3s} | {'pase j/CON/SIN':>20s} | {'neto j/CON/SIN':>24s}")
for em, lab in ((9 * 60 + 35, "9:35"), (9 * 60 + 40, "9:40"), (9 * 60 + 45, "9:45"), (9 * 60 + 50, "9:50"), (10 * 60, "10:00")):
    for tp in (32, 40):
        ps = []; ns = []
        Sf, axf = LD.make_pool_spec(n_worlds=60, c_entry=em, nc=40, tp=tp, slip=0.5, x_sl=364, x_tp=364, nc_x=3)
        Sr, axr = LD.make_spec(c_entry=em, nc=40, tp=tp, slip=0.5, x_sl=364, x_tp=364, nc_x=3)
        for S, ax, mask in ((Sf, axf, None), (Sr, axr, None), (Sr, axr, LD.gold_mask(axr))):
            pool = np.arange(len(ax)) if mask is None else np.nonzero(mask)[0]
            D = pool[np.random.default_rng(7).integers(0, len(pool), (T, 40))]
            r = simulate(dc.replace(S, K=1), D, lag=2, skip=None); ps.append((r["pass_day"] > 0).mean())
            ns.append(run(S, ax, mask=mask, T=T)["net"].mean() - OPS12)
        P(f"{lab:>8s} {tp:>3d} | {ps[0]:>6.1%} {ps[1]:>6.1%} {ps[2]:>6.1%} | {ns[0]:>7,.0f} {ns[1]:>7,.0f} {ns[2]:>7,.0f}")
open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dd_cash", "t1_entry_time_report.txt"), "w").write("\n".join(lines))
