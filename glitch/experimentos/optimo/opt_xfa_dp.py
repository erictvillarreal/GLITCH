"""OPTIMIZACIÓN DE LA XFA (MGC): ¿cuánto más puede cobrar y durar una XFA con el tamaño y el momento de cobro ÓPTIMOS (DP exacta) frente a 3×364 fijo? -> resultados_OPT_XFA.md
    cd glitch/experimentos/optimo; GLITCH_MGC_PARQUET=... PYTHONPATH=../.. python3 opt_xfa_dp.py [--quick]
MODELADO. La DP se entrena en el 60 % cronológico más viejo (stop exacto, slip 0, como en la Parte D) y se EVALÚA en el 40 % reciente con fricciones (stop 0.5, slippage empírico de 8 obs.; 8.ª inferida = 0, NO VERIFICADA)
y con TODAS las reglas del motor (incluida «ganancia desde el último pago»). Objetivo de la DP: efectivo esperado cobrado hasta la liquidación (después de la división 90/10)."""
import os, sys, time
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [os.path.join(HERE, "..", "xfa"), os.path.join(HERE, "..", "preservacion")]
from worlds import MGC, gold_mask, mgc_days
from xfa_engine import BarDays, Policy, Rules, pol_fixed, simulate_life
from xfa_dp import build_hist, dp_policy, solve
QUICK = "--quick" in sys.argv; t0 = time.time(); out = []; P = lambda s="": (print(s, flush=True), out.append(s))
EMP8 = (-1.0, 0.0, 1.0, 3.0); EMP8_P = (1 / 8, 3 / 8, 2 / 8, 2 / 8)
clean = mgc_days(True); gm = gold_mask(clean, True); D = clean.D; cut = int(0.6 * D)
tr_mask = gm.copy(); tr_mask[cut:] = False; te_mask = gm.copy(); te_mask[:cut] = False
SLS = (364,) if QUICK else (273, 364, 546, 728); NSETS = (("seguro (≤ 4 micros)", (1, 2, 3, 4)),) if QUICK else (("seguro (≤ 4 micros)", (1, 2, 3, 4)), ("ancho (≤ 8 micros: «lotería»)", (1, 2, 3, 4, 6, 8)))
NEV = 12000 if QUICK else 40000
P("# resultados_OPT_XFA — techo de lo que cobra y dura una XFA con tamaño y cobro óptimos (MGC, XFA 50K)\n")
P(f"**Estado:** MODELADO. DP entrenada en {int(tr_mask.sum())} días (60 % más viejo), evaluada en {int(te_mask.sum())} días (40 % reciente) con fricciones y reglas completas. «seguro» = nunca más de 4 micros; «ancho» incluye 6 y 8 (con 8 micros el piso del MLL, no el SL, es la barrera: es una lotería que además se parece al patrón de «tamaño máximo» del RTP; se muestra como techo, no como recomendación).\n")
rows = []; shapes = {}; imm = {}
for sl in SLS:
    dtr = BarDays(clean, MGC["tick_usd"], MGC["fee"], sl, sl, slip=(0.0,), mask=tr_mask, cush_max=9000.0)
    dev = BarDays(clean, MGC["tick_usd"], MGC["fee"], sl, sl, slip=EMP8, slip_p=EMP8_P, mask=te_mask, cush_max=9000.0, stop_frac=0.5)
    R = Rules()
    base = simulate_life(dev, R, pol_fixed(3, sl, sl), n=NEV, seed=20261028, record_k=14)
    best_fixed = max(((nc, simulate_life(dev, R, pol_fixed(nc, sl, sl), n=NEV, seed=20261028)) for nc in (1, 2, 3, 4, 6)), key=lambda x: x[1]["paid"].mean())
    for nm, NCS in NSETS:
        H, PL = build_hist(dtr, NCS, sl); Vp, Vq, pp, pq, ypp, ypq, its, dl = solve(H, PL, NCS, Rules(profit_rule=False))
        nc_fn, pay_fn = dp_policy(NCS, pp, pq, ypp, ypq)
        r = simulate_life(dev, R, Policy("DP", nc_fn, pay_fn, sl, sl), n=NEV, seed=20261028, record_k=14)
        d = r["paid"] - base["paid"]; se = 1.96 * d.std() / np.sqrt(len(d))
        rows.append((sl, nm, base, best_fixed, r, d.mean(), se)); shapes[(sl, nm)] = (NCS, pp, pq, ypq, ypp)
        if nm.startswith("seguro"):                         # tamaño de la DP + COBRO INMEDIATO (la DP no tiene preferencia por el tiempo: cobrar antes no le cuesta ni le sirve)
            r2 = simulate_life(dev, R, Policy("DPnc", nc_fn, "max", sl, sl), n=NEV, seed=20261028, record_k=14); d2 = r2["paid"] - base["paid"]
            imm[sl] = (r2, d2.mean(), 1.96 * d2.std() / np.sqrt(len(d2)), base)
        print("  ", sl, nm, round(time.time() - t0), "s", flush=True)
P("| bracket (SL = TP, ticks) | política | cobrado por XFA | Δ vs 3 micros fijos (pareado ± IC95) | P(≥ 1 pago) | vida (días) | P(muerte sin cobrar) | pagos por XFA |\n|---|---|---|---|---|---|---|---|")
for sl, nm, base, bf, r, dm, se in rows:
    f = lambda x: (f"${x['paid'].mean():,.0f}", f"{(x['npay'] >= 1).mean() * 100:.0f} %", f"{x['life'].mean():.1f}", f"{((x['npay'] == 0) & ~x['alive']).mean() * 100:.0f} %", f"{x['npay'].mean():.2f}")
    b = f(base); g = f(r); h = f(bf[1])
    P(f"| {sl} | 3 micros fijos | {b[0]} | — | {b[1]} | {b[2]} | {b[3]} | {b[4]} |")
    P(f"| {sl} | mejor tamaño FIJO ({bf[0]} micros) | {h[0]} | {bf[1]['paid'].mean() - base['paid'].mean():+,.0f} | {h[1]} | {h[2]} | {h[3]} | {h[4]} |")
    P(f"| {sl} | **DP óptima, {nm}** | **{g[0]}** | **{dm:+,.0f} ± {se:,.0f}** | {g[1]} | {g[2]} | {g[3]} | {g[4]} |")
P("\n## Tamaño de la DP (conjunto seguro) con **cobro inmediato** en cuanto sea elegible (lo que Eric quiere: cobrar ya)\n")
P("| bracket | cobrado por XFA | Δ vs 3 micros fijos (pareado ± IC95) | P(≥ 1 pago) | mediana de días al 1.er pago | cobrado a 30 días |\n|---|---|---|---|---|---|")
for sl, (r2, dm, se, base) in imm.items():
    fp = r2["first_pay_day"]; pd_, pn = r2["pay_day"], r2["pay_net"]; c30 = float(np.where((pd_ >= 0) & (pd_ < 30), pn, 0.0).sum(1).mean()); pdb, pnb = base["pay_day"], base["pay_net"]; b30 = float(np.where((pdb >= 0) & (pdb < 30), pnb, 0.0).sum(1).mean())
    P(f"| {sl} | ${r2['paid'].mean():,.0f} | {dm:+,.0f} ± {se:,.0f} | {(r2['npay'] >= 1).mean() * 100:.0f} % | {np.median(fp[fp >= 0]) + 1:.0f} | ${c30:,.0f} (3 fijos: ${b30:,.0f}) |")
# forma de la política (SL 364, conjunto seguro)
if (364, NSETS[0][0]) in shapes:
    NCS, pp, pq, ypq, ypp = shapes[(364, NSETS[0][0])]
    P("\n## Forma de la política DP (SL = TP = 364, conjunto seguro): contratos por saldo y días ganadores acumulados (fase con el piso ya en $0 = después de +$2,000 o del 1.er pago)\n")
    P("| saldo | wd = 0 | wd = 1 | wd = 2 | wd = 3 | wd = 4 | wd = 5 (¿cobra ya?) |\n|---|---|---|---|---|---|---|")
    for b in (100, 300, 500, 1000, 1500, 2000, 3000, 4000):
        i = int(round(b / 50)); cells = [str(NCS[int(pq[w][i])]) for w in range(5)] + [f"{NCS[int(pq[5][i])]} / " + ("cobra" if bool(ypq[5][i]) else "sigue")]
        P(f"| ${b:,.0f} | " + " | ".join(cells) + " |")
if (364, NSETS[0][0]) in shapes:
    P("\n## Fase inicial (el piso todavía puede subir: saldo < +$2,000 y sin pago): contratos de la DP según pico y saldo (SL = TP = 364, conjunto seguro, wd = 0)\n")
    P("| pico | saldo = pico (sin caída) | saldo = pico − $500 | saldo = pico − $1,000 | saldo = pico − $1,500 |\n|---|---|---|---|---|")
    for pk in (0, 500, 1000, 1500):
        ip = int(round(pk / 50)); cells = []
        for dd_ in (0, 500, 1000, 1500):
            j = 40 - int(round(dd_ / 50)); cells.append(str(NCS[int(pp[0][ip, j])]) if j >= 1 else "—")
        P(f"| ${pk:,.0f} | " + " | ".join(cells) + " |")
open(os.path.join(HERE, "resultados_OPT_XFA.md"), "w", encoding="utf-8").write("\n".join(out) + "\n"); print("OK", round(time.time() - t0), "s")

