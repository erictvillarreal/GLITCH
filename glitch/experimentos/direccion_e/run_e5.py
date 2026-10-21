"""E5 — brecha en MES (PREREGISTRO_E §2): |gap| > p75 de |gap| de los 60 dias previos -> reversion (-signo) y continuacion (+signo). -> RESULTADOS_E5.md, e5_pvals.json
    python run_e5.py"""
import json, os, sys
import numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from common_e import day_results, intraday_signals, prior_stat
from daydata import DEFAULT_PARQUET, load_days
from rule_eval import HEAD, evaluate, row
out = []; P = lambda s="": (print(s, flush=True), out.append(s))
dd = load_days(); sig = intraday_signals(pd.read_parquet(DEFAULT_PARQUET), 9 * 60 + 30)
thr = prior_stat(sig["gap"], 60, "q", 0.75)
g = sig["gap"].reindex(dd.dates).values; T = thr.reindex(dd.dates).values
res = {sp: day_results(dd, 40, 2000.0, 100, 32, 1.22, 1.25, sp) for sp in (0.0, 1.0, 3.0)}
P("# RESULTADOS_E5 — brecha en MES (pre-registrada; ventana real 9:30→14:30 CT; 2 años: sin potencia para G2)\n")
P(f"gap = open 8:30 CT / cierre previo − 1 (sin cambio de contrato). {dd.D} días con barras completas; {int(np.isfinite(g).sum())} con gap; umbral = p75 de |gap| de los 60 días previos. σ(gap) = {np.nanstd(g) * 100:.2f} %.\n")
P(HEAD); pv = {}; g2 = {}
for reading, sgn in (("reversión", -1.0), ("continuación", 1.0)):
    side = np.where(np.abs(g) > T, sgn * np.sign(g), 0); side = np.where(np.isfinite(side), side, 0)
    r = evaluate(side, dd, res); key = f"E5 MES {reading}"; pv[key] = r["p51"]; g2[key] = dict(acc=float(r["acc"]), p51=float(r["p51"]), wins_alt=r["wins_alt"], wins_long=r["wins_long"], years={str(y): float(v[0]) for y, v in r["years"].items()})
    P(row(f"{reading}, |gap| > p75", r))
    for sp in (1.0, 3.0): P(f"|  ↳ slip {sp:g} | | | | | | | | | | | {r['mech'][sp]['ev']['wr'] * 100:.1f} % | {r['mech'][sp]['alt']['wr'] * 100:.1f} % | {r['mech'][sp]['long']['wr'] * 100:.1f} % | | | ${r['mech'][sp]['ev']['pnl']:+.1f} |")
    yy = " · ".join(f"{y}: {a * 100:.0f} % (n={n}; alt {al * 100:.0f} %, LARGO {lg * 100:.0f} %)" for y, (a, n, al, lg) in r["years"].items())
    P(f"|  ↳ por año: {yy} |" + " |" * 16)
json.dump(pv, open(os.path.join(HERE, "e5_pvals.json"), "w")); json.dump(g2, open(os.path.join(HERE, "e5_g2.json"), "w"))
open(os.path.join(HERE, "RESULTADOS_E5.md"), "w").write("\n".join(out))
