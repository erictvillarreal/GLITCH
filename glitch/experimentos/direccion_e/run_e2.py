"""E2 — momentum/reversion por reaccion inicial (PREREGISTRO_E §2), 8 pruebas: {MGC 7:15 CT, MES 9:30 CT} x {continuacion, reversion} x {todos, |R| > mediana de 60 dias previos}. -> RESULTADOS_E2.md, e2_pvals.json
    GLITCH_MGC_PARQUET=... python run_e2.py"""
import json, os, sys
import numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from common_e import day_results, intraday_signals, prior_stat
from daydata import DEFAULT_PARQUET, load_days
from rule_eval import HEAD, evaluate, row
from worlds import MGC, MGC_PARQUET, mgc_days
out = []; P = lambda s="": (print(s, flush=True), out.append(s))
CASES = {"MGC": dict(dd=mgc_days(True), path=MGC_PARQUET, ref_hm=MGC["ref_hm"], nc=3, cu=2000.0, sl=364, tp=364, fee=MGC["fee"], tv=MGC["tick_usd"], slips=(0.0,), label="MGC 7:15 CT, 3 micros SL=TP=364"),
         "MES": dict(dd=load_days(), path=DEFAULT_PARQUET, ref_hm=9 * 60 + 30, nc=40, cu=2000.0, sl=100, tp=32, fee=1.22, tv=1.25, slips=(0.0, 1.0, 3.0), label="MES 9:30 CT, nc 40 TP 32 / piso $2,000")}
P("# RESULTADOS_E2 — momentum intradía por reacción inicial (pre-registrada; ventana real de 5 min, 2 años)\n")
P("R = ln(P_ref / cierre previo) (contrato dominante sin cambio de contrato). Resultado = signo de (cierre del flatten − referencia). **Sin potencia para G2(1)/(3):** n ≈ 450 días → IC95 ≈ ±4.5 pp; estas pruebas generan hipótesis, no hallazgos (Enmienda 1, punto 4).\n")
pvals = {}; g2 = {}
for inst, c in CASES.items():
    dd = c["dd"]; sig = intraday_signals(pd.read_parquet(c["path"]), c["ref_hm"])
    thr = prior_stat(sig["R"], 60, "median")
    R = sig["R"].reindex(dd.dates).values; T = thr.reindex(dd.dates).values
    res = {sp: day_results(dd, c["nc"], c["cu"], c["sl"], c["tp"], c["fee"], c["tv"], sp) for sp in c["slips"]}
    P(f"\n## {inst} — {c['label']}: {dd.D} días con barras completas, {int(np.isfinite(R).sum())} con R definido; σ(R) = {np.nanstd(R) * 100:.2f} %\n")
    P(HEAD)
    for reading, sgn in (("continuación", 1.0), ("reversión", -1.0)):
        for var in ("todos", "|R| > mediana60"):
            side = sgn * np.sign(R)
            if var != "todos": side = np.where(np.abs(R) > T, side, 0)
            side = np.where(np.isfinite(side), side, 0)
            r = evaluate(side, dd, res); key = f"E2 {inst} {reading} {var}"; pvals[key] = r["p51"]; g2[key] = dict(acc=float(r["acc"]), p51=float(r["p51"]), wins_alt=r["wins_alt"], wins_long=r["wins_long"], years={str(y): float(v[0]) for y, v in r["years"].items()})
            P(row(f"{reading} / {var}", r))
            if inst == "MES":
                for sp in (1.0, 3.0): P(f"|  ↳ slip {sp:g} | | | | | | | | | | | {r['mech'][sp]['ev']['wr'] * 100:.1f} % | {r['mech'][sp]['alt']['wr'] * 100:.1f} % | {r['mech'][sp]['long']['wr'] * 100:.1f} % | | | ${r['mech'][sp]['ev']['pnl']:+.1f} |")
            yy = " · ".join(f"{y}: {a * 100:.0f} % (n={n}; alt {al * 100:.0f} %, LARGO {lg * 100:.0f} %)" for y, (a, n, al, lg) in r["years"].items())
            P(f"|  ↳ por año: {yy} |" + " |" * 16)
json.dump(pvals, open(os.path.join(HERE, "e2_pvals.json"), "w")); json.dump(g2, open(os.path.join(HERE, "e2_g2.json"), "w"))
open(os.path.join(HERE, "RESULTADOS_E2.md"), "w").write("\n".join(out))
