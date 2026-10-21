"""Parte D (5): fill del stop (convencion del motor de caja: stop llenado a una fraccion del camino hacia el extremo adverso de la barra) y capa de costos / neto anual por cuenta. -> resultados_D5.md
    GLITCH_MGC_PARQUET=... python run_partD5.py [--quick]"""
import argparse, os, sys, time
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from run_partD import HDR, metrics, row
from worlds import MGC, brownian_like, gold_mask, mgc_days
from xfa_engine import BarDays, Policy, Rules, pol_fixed, simulate_life
SEED = 20261020
ap = argparse.ArgumentParser(); ap.add_argument("--quick", action="store_true"); a = ap.parse_args()
N = 4000 if a.quick else 50000
t0 = time.time(); out = []; P = lambda s="": (print(s, flush=True), out.append(s))
clean = mgc_days(True); mk_ng = gold_mask(clean, True); mk_all = np.ones(clean.D, bool)
brown, _ = brownian_like(clean, mk_ng, D=6000 if a.quick else 40000); mkb = np.ones(brown.D, bool)
W = {"W1 CON oro": (clean, mk_all), "W2 SIN oro": (clean, mk_ng), "W3 Browniano": (brown, mkb)}
cands = [("a  plan 3×364/364", 3, 364, 364, "max"), ("b  728×3 (stop = piso)", 3, 728, 728, "max"), ("c  1 micro siempre", 1, 364, 364, "max"), ("e1 TP 60/SL 364", 3, 364, 60, "max")]
P(f"# resultados_D5 (N={N} vidas; semilla {SEED}; reglas base; slip de entrada 0)\n")
res = {}
for frac in (0.0, 0.5):
    P(f"\n## Stop llenado a {frac:.1f} del camino hacia el extremo adverso de la barra ({'stop exacto' if frac == 0 else 'convención del motor de caja: C1/log 7-oct'})\n"); P(HDR)
    for wname, (dd, mask) in W.items():
        for cname, nc, sl, tp, pay in cands:
            days = BarDays(dd, MGC["tick_usd"], MGC["fee"], sl, tp, slip=(0.0,), mask=mask, cush_max=9000.0, stop_frac=frac)
            r = simulate_life(days, Rules(), pol_fixed(nc, sl, tp), n=N, seed=SEED)
            res[(frac, wname, cname)] = r
            P(row(f"{wname}: {cname}", metrics(r)))
# ── capa de costos ──
P("\n## Capa de costos: neto por XFA y neto anual por cuenta (una cuenta, ciclo secuencial Combine → XFA → Combine…)\n")
P("P(pase) y días por intento del Combine: Parte A, cuenta nueva, entrada 9:30 CT, slip de entrada {1, 3, mezcla}: P0 (40 fijo) .292/.165/.199 con 1.5/1.8/1.7 días por intento; P3 (finish-line) .292/.250/.269 con 1.5/1.9/1.8. "
  "Costo de obtener una XFA = $49 × (1/P(pase)) + $149 de activación (cada intento cuesta $49: compra o reset; sin mensualidad en la XFA). XFA por año = 252 / (días hasta pasar + vida de la XFA + 1 día de activación manual). Costos compartidos $714/año (C1).\n")
P("| combine | slip entrada | P(pase) | costo de obtener 1 XFA | días hasta pasar | candidato (mundo W2, stop 0.0 / 0.5) | cobrado por XFA | neto por XFA | XFA/año | **neto anual por cuenta** |\n|---|---|---|---|---|---|---|---|---|---|")
combine = [("P0 40 fijo (hoy)", "1", .292, 1.5), ("P0 40 fijo (hoy)", "3", .165, 1.8), ("P0 40 fijo (hoy)", "mezcla {1,3}", .199, 1.7), ("P3 finish-line", "mezcla {1,3}", .269, 1.8)]
for cn, sl_lab, p, d in combine:
    cost = 49 / p + 149; dpass = d / p
    for cname, *_ in cands[:3]:
        cells = []
        for frac in (0.0, 0.5):
            r = res[(frac, "W2 SIN oro", cname)]; paid = r["paid"].mean(); life = r["life"].mean()
            n_y = 252 / (dpass + life + 1)
            cells.append((paid, paid - cost, n_y, n_y * (paid - cost) - 714))
        P(f"| {cn} | {sl_lab} | {p * 100:.1f} % | ${cost:,.0f} | {dpass:.1f} | {cname} | ${cells[0][0]:,.0f} / ${cells[1][0]:,.0f} | ${cells[0][1]:,.0f} / ${cells[1][1]:,.0f} | {cells[0][2]:.1f} / {cells[1][2]:.1f} | **${cells[0][3]:,.0f} / ${cells[1][3]:,.0f}** |")
P(f"\n(tiempo {time.time() - t0:.0f}s)")
open(os.path.join(HERE, "resultados_D5.md"), "w").write("\n".join(out))
