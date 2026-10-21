"""EXPLORACION POSTERIOR (hipotesis, NO evidencia): el 'acantilado' del slippage de entrada en una cuenta NUEVA (50,000/50,000, meta 3,000, MLL 2,000).
Con TP anclado a la referencia, el neto de un TP es (TP - slip) ticks x nc x $1.25 - nc x $1.22. El numero de TP necesarios para llegar a $3,000 es un entero:
si dos TP no alcanzan, hace falta un tercero y P(pase) cae a ~la mitad. Barre TP x nc x slip con P0 (nc fijo). Una sola historia de 492 dias, mismas barras que la Parte A."""
import sys, math, numpy as np
sys.path.insert(0, ".")
from daydata import load_days
from sim import OutcomeTable, pol_fixed, run_mc

dd = load_days()
out = []
P = lambda s: (print(s, flush=True), out.append(s))
P("# scan_cliff (EXPLORACION POSTERIOR; cuenta nueva, 40 dias max, n=20000, semilla 11; entrada 9:30 ref, orden adverso-primero; consistencia OFICIAL: mejor dia <= 55% de la ganancia total)\n")
P("| TP | nc | TP netos necesarios (slip 0/1/2/3) | P(pase) slip 0 | slip 1 | slip 2 | slip 3 | mezcla {1,3} |"); P("|---|---|---|---|---|---|---|---|")
for tp in (30, 32, 33, 34, 36):
    for nc in (36, 40, 44, 50):
        need = []; ps = []
        tabs = {}
        for s in (0, 1, 2, 3):
            net = (tp - s) * nc * 1.25 - nc * 1.22
            need.append(str(math.ceil(3000 / net - 1e-9)) if net > 0 else "inf")
            tabs[s] = OutcomeTable(dd, float(s), 3.0, "adverse", 100, tp, step=10.0)
            r = run_mc(pol_fixed(nc), {s: tabs[s]}, n=20000, seed=11, bal0=50000.0, peak0=50000.0, start_idx=1774, maxdays=40, slip_mix=([s], [1.0]), consistency_mode="pct55")
            ps.append(r.p_pass)
        rm = run_mc(pol_fixed(nc), {1: tabs[1], 3: tabs[3]}, n=20000, seed=11, bal0=50000.0, peak0=50000.0, start_idx=1774, maxdays=40, slip_mix=([1, 3], [0.5, 0.5]), consistency_mode="pct55")
        P(f"| {tp} | {nc} | {'/'.join(need)} | " + " | ".join(f"{p * 100:.1f}%" for p in ps) + f" | {rm.p_pass * 100:.1f}% |")
open("scan_cliff.md", "w").write("\n".join(out))
