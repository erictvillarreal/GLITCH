"""EXPLORACION POSTERIOR (generadora de hipotesis, NO evidencia): P(pase) de una cuenta NUEVA (nc=40 fijo, TP32/SL100) segun la hora de la referencia de entrada.
7 horas probadas (se cuentan como 7 comparaciones; no hay correccion formal y la historia es una sola de 492 dias). Slippage de entrada 0 para aislar el efecto de la hora."""
import sys
sys.path.insert(0, ".")
from daydata import load_days
from sim import OutcomeTable, pol_fixed, run_mc, pol_p3
out = []; P = lambda s: (print(s, flush=True), out.append(s))
P("# scan_entry_time (EXPLORACION POSTERIOR; cuenta nueva, n=30000, semilla 13, slip 0, flatten 14:30 CT)\n")
P("| referencia (close de la barra que empieza) | dias | P0 40 fijo: P(pase) [IC95] | P3 finish-line: P(pase) |"); P("|---|---|---|---|")
for hm in (8 * 60 + 30, 8 * 60 + 45, 9 * 60, 9 * 60 + 15, 9 * 60 + 30, 9 * 60 + 45, 10 * 60):
    dd = load_days(ref_hm=hm, last_hm=14 * 60 + 25)
    tabs = {0: OutcomeTable(dd, 0.0, 3.0, "adverse", 100, 32, step=10.0)}
    r0 = run_mc(pol_fixed(40), tabs, n=30000, seed=13, bal0=50000.0, peak0=50000.0, start_idx=1774, maxdays=40, consistency_mode="pct55")
    r3 = run_mc(pol_p3(), tabs, n=30000, seed=13, bal0=50000.0, peak0=50000.0, start_idx=1774, maxdays=40, consistency_mode="pct55")
    P(f"| {hm // 60}:{hm % 60:02d} CT | {dd.D} | {r0.p_pass * 100:.1f}% [{r0.ci_pass[0] * 100:.1f},{r0.ci_pass[1] * 100:.1f}] | {r3.p_pass * 100:.1f}% |")
open("scan_entry_time.md", "w").write("\n".join(out))
