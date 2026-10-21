"""E1 — tendencia lenta (PREREGISTRO_E §2). Historia larga (GLD para MGC, ^GSPC para MES) + confirmacion en la ventana real de 5 min. -> RESULTADOS_E1.md y e1_pvals.json
    GLITCH_MGC_PARQUET=... python run_e1.py"""
import json, os, sys
import numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from common_e import SEED, block_bootstrap_acc, blocks10, day_results, e1_signals, eval_sides, load_daily, pval_gt
from daydata import DEFAULT_PARQUET, load_days
from strategies.geometry_pure import decide_side, trading_day_index
from worlds import MGC, mgc_days
out = []; P = lambda s="": (print(s, flush=True), out.append(s))
pvals = {}; extra = {}
P("# RESULTADOS_E1 — tendencia lenta (E1), pre-registrada\n")
P("Resultado primario: signo del retorno apertura→cierre del proxy (ventana de EE. UU. ≈ la ventana real); secundario: cierre→cierre. Lado = señal con información previa a la entrada; NO OPERAR si |r12| < 0.5 σ anual (lectura 1, la de G2).\n")
BEAR = {"GLD": [2008, 2013, 2015, 2022], "^GSPC": [2008, 2020, 2022]}
def study(inst, proxy, variant, key):
    df = load_daily(proxy); sg = e1_signals(df)
    col = {"r12": "side_r12", "sma": "side_sma"}[variant]
    d = pd.DataFrame({"side": sg[col], "oc": sg["oc"], "cc": sg["cc"]}, index=df.index).dropna(subset=["side"])
    ops = d[d.side != 0]
    res = {}
    for oname in ("oc", "cc"):
        x = ops[ops[oname] != 0]
        hit = (x.side == x[oname]).astype(float).values
        m, ci, boots = block_bootstrap_acc(hit, seed=SEED)
        alt = np.array([decide_side(trading_day_index(i.date()), "alternate") for i in x.index]); alt_hit = (alt == x[oname].values).astype(float)
        lng = (x[oname].values == 1).astype(float)
        res[oname] = dict(n=len(x), acc=m, ci=ci, p51=pval_gt(boots, 0.51), alt=alt_hit.mean(), long=lng.mean(), x=x, hit=hit, alt_hit=alt_hit, lng=lng)
    r = res["oc"]
    pvals[key] = r["p51"]
    # 10 bloques cronologicos
    bl = blocks10(r["n"]); wins_alt = wins_lng = 0
    for a, b in bl:
        h, ah, lh = r["hit"][a:b].mean(), r["alt_hit"][a:b].mean(), r["lng"][a:b].mean()
        wins_alt += h > ah; wins_lng += h > lh
    # ventanas anuales
    x = r["x"]; yrs = {}
    for y in sorted(set(x.index.year)):
        m_ = (x.index.year == y); yrs[y] = (r["hit"][m_].mean(), int(m_.sum()), r["alt_hit"][m_].mean(), r["lng"][m_].mean())
    last3 = sorted(yrs)[-3:]
    extra[key] = dict(inst=inst, proxy=proxy, variant=variant, n=r["n"], acc=r["acc"], ci=r["ci"], p51=r["p51"], alt=r["alt"], long=r["long"], wins_alt=int(wins_alt), wins_lng=int(wins_lng),
                      last3={y: yrs[y][0] for y in last3}, bear={y: (yrs[y][0], yrs[y][1]) for y in BEAR[proxy] if y in yrs}, cc=(res["cc"]["acc"], res["cc"]["ci"], res["cc"]["long"]), n_all=len(d), op_share=r["n"] / max(len(d[d.oc != 0]), 1))
    return res, yrs, d
tests = {}
for inst, proxy in (("MGC", "GLD"), ("MES", "^GSPC")):
    for variant in ("r12", "sma"):
        key = f"E1 {inst} {variant}"; tests[key] = study(inst, proxy, variant, key)
P("## A. Resumen de las 4 pruebas pre-registradas (apertura→cierre del proxy; lectura 1 = NO OPERAR sin señal fuerte)\n")
P("| prueba | proxy | días operados | exactitud [IC95 bloques] | `alternate` | siempre LARGO | p vs 51 % (sin ajustar) | bloques > `alternate` | bloques > LARGO | cierre→cierre: exactitud (LARGO) |\n|---|---|---|---|---|---|---|---|---|---|")
for k, e in extra.items():
    P(f"| {k} | {e['proxy']} | {e['n']:,} de {e['n_all']:,} | {e['acc'] * 100:.2f} % [{e['ci'][0] * 100:.1f}, {e['ci'][1] * 100:.1f}] | {e['alt'] * 100:.2f} % | {e['long'] * 100:.2f} % | {e['p51']:.3f} | {e['wins_alt']}/10 | {e['wins_lng']}/10 | {e['cc'][0] * 100:.2f} % ({e['cc'][2] * 100:.1f} %) |")
P("\n## B. Por año (exactitud de la regla en días operados / n / `alternate` / siempre LARGO en los mismos días)\n")
for k, (res, yrs, d) in tests.items():
    P(f"\n**{k}**\n\n| año | exactitud | n | alternate | LARGO |\n|---|---|---|---|---|")
    for y, (a, n, al, lg) in yrs.items():
        mark = " ← tramo bajista" if y in BEAR[extra[k]["proxy"]] else ""
        P(f"| {y}{mark} | {a * 100:.1f} % | {n} | {al * 100:.1f} % | {lg * 100:.1f} % |")
# ── ventana real de 5 min ──
P("\n## C. Confirmación en la ventana real (series de 5 min; mecánica exacta; la señal viene del proxy diario)\n")
mgc = mgc_days(True); mes = load_days()
cases = [("MGC", mgc, "GLD", 3, 2000.0, 364, 364, MGC["fee"], MGC["tick_usd"], 0.0, "MGC 3 micros SL=TP=364"), ("MES", mes, "^GSPC", 40, 2000.0, 100, 32, 1.22, 1.25, 0.0, "MES nc 40 TP 32 / piso $2,000")]
P("| prueba | bracket | días con señal | TP / SL+LIQ / FLATTEN | WR entre decididos | pnl medio por día | `alternate` WR | siempre LARGO WR | siempre CORTO WR | aleatorio WR (p2.5–p97.5) |\n|---|---|---|---|---|---|---|---|---|---|")
rng = np.random.default_rng(SEED)
for inst, dd, proxy, nc, cu, sl, tp, fee, tv, slip, label in cases:
    res = day_results(dd, nc, cu, sl, tp, fee, tv, slip)
    df = load_daily(proxy); sg = e1_signals(df)
    dates = pd.to_datetime(dd.dates)
    alt = np.array([decide_side(trading_day_index(d), "alternate") for d in dd.dates])
    rnd = []
    for _ in range(1000):
        sd = np.where(rng.random(dd.D) < 0.5, 1, -1); rnd.append(eval_sides(res, sd)["wr"])
    for variant, col in (("r12", "side_r12"), ("sma", "side_sma")):
        s = sg[col].reindex(dates).values
        s = np.where(np.isnan(s), 0, s)
        ev = eval_sides(res, s); m = s != 0
        ca = eval_sides(res, np.where(m, alt, 0)); cl = eval_sides(res, np.where(m, 1, 0)); cs = eval_sides(res, np.where(m, -1, 0))
        P(f"| E1 {inst} {variant} | {label} | {int(m.sum())} de {dd.D} | {ev['tp'] * 100:.0f} / {ev['sl'] * 100:.0f} / {ev['fl'] * 100:.0f} % | {ev['wr'] * 100:.1f} % ({ev['dec']} decididos) | ${ev['pnl']:+.1f} | {ca['wr'] * 100:.1f} % | {cl['wr'] * 100:.1f} % | {cs['wr'] * 100:.1f} % | {np.nanpercentile(rnd, 50) * 100:.1f} % ({np.nanpercentile(rnd, 2.5) * 100:.1f}–{np.nanpercentile(rnd, 97.5) * 100:.1f}) |")
json.dump(pvals, open(os.path.join(HERE, "e1_pvals.json"), "w"))
json.dump({k: dict(acc=float(e["acc"]), p51=float(e["p51"]), wins_alt=e["wins_alt"], wins_long=e["wins_lng"], last3={str(y): float(v) for y, v in e["last3"].items()}) for k, e in extra.items()}, open(os.path.join(HERE, "e1_g2.json"), "w"))
open(os.path.join(HERE, "RESULTADOS_E1.md"), "w").write("\n".join(out))
