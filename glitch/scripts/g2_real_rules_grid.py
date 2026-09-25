"""Barrido Camino B (sin edge, alternar) bajo las reglas reales (consistencia 55% + liquidacion MLL real; DLL off/on).
Primera pasada n=12000 -> top 12 por pases/año refinados con n=100000 y chequeo H1/H2 (mitades cronologicas de los 515 dias)."""
import itertools, time, numpy as np
from scripts.g2_real_rules_scan import build_tables, simulate
T = build_tables(); nd = len(T[0]); idx = np.arange(nd); H1, H2 = idx[: nd // 2], idx[nd // 2:]
NCS = [5, 8, 10, 15, 20, 25, 30, 40, 50]; TPS = [4, 6, 8, 10, 12, 16, 20, 24, 30, 40, 50, 60]; SLS = [10, 15, 20, 25, 30, 40, 50, 60, 80, 100]
t0 = time.time()
for dll in (False, True):
    rows = []
    for nc, tp, sl in itertools.product(NCS, TPS, SLS):
        r = simulate(T, idx, nc, tp, sl, dll=dll, n=12000)
        rows.append((r["passes_yr"], r["pass_rate"], r["days_pass"], nc, tp, sl))
    rows.sort(reverse=True)
    g2 = simulate(T, idx, 40, 40, 100, dll=dll, n=100000)
    print(f"\n===== DLL {'ON (-$1,000)' if dll else 'OFF (default)'}  [{len(rows)} configs, {time.time()-t0:.0f}s] G2 (40/40/100): pass={g2['pass_rate']:.3f} pases/año={g2['passes_yr']:.1f}")
    print("nc  TP  SL | pass  blow  dias_pase pases/año | H1 pass/pases-año  H2 pass/pases-año | SL$  TP$  SL/MLL")
    seen = 0
    for _, _, _, nc, tp, sl in rows[:12]:
        r = simulate(T, idx, nc, tp, sl, dll=dll, n=100000); a = simulate(T, H1, nc, tp, sl, dll=dll, n=60000); b = simulate(T, H2, nc, tp, sl, dll=dll, n=60000)
        print(f"{nc:2d} {tp:3d} {sl:3d} | {r['pass_rate']:.3f} {r['blow']:.3f} {r['days_pass']:6.2f}  {r['passes_yr']:6.1f} | {a['pass_rate']:.3f}/{a['passes_yr']:5.1f}  {b['pass_rate']:.3f}/{b['passes_yr']:5.1f} | ${sl*nc*1.25:,.0f} ${tp*nc*1.25:,.0f} {sl*nc*1.25/2000:.2f}", flush=True)
