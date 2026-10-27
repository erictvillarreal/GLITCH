"""Parte K, K1: equilibrio de la cadena Combine → XFA con costos operativos de $640, $290 y $245 al año (reemplaza el OPS = $714). -> resultados_K1_equilibrio.md
    cd glitch/experimentos/producto_k; GLITCH_MGC_PARQUET=... PYTHONPATH=../.. python3 k1_equilibrio.py [--quick]
MODELADO. Mismo motor que H1b/J5 (xfa/chain.py); slippage de entrada del Combine = 8 obs. (8.ª inferida = 0, NO VERIFICADA); XFA MGC 3×364, slip 0, stop 0.5. Semillas fijas.
El neto es lineal en los costos: se calcula con ops = 0 y se restan después. Equilibrio = WR de la etiqueta de deriva (calibrada en el bracket nominal 364/364) donde el neto anual = 0, por interpolación lineal en una rejilla de WR."""
import argparse, os, sys, time
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "..", "xfa")); sys.path.insert(0, os.path.join(HERE, "..", "preservacion"))
from chain import combine_bank, run_chain, xfa_bank
from daydata import load_days
from worlds import MGC, drift_for_wr, gold_mask, mgc_days
from xfa_engine import BarDays, Rules, pol_fixed
ap = argparse.ArgumentParser(); ap.add_argument("--quick", action="store_true"); A = ap.parse_args()
NB = 20000 if A.quick else 80000; NC = 20000 if A.quick else 40000
t0 = time.time(); out = []; P = lambda s="": (print(s, flush=True), out.append(s))
mes = load_days(); clean = mgc_days(True); mk = gold_mask(clean, True)
sig_m = float(np.std(clean.cl[mk][:, -1])); sig_s = float(np.std(mes.cl[:, -1]))
EMP8 = (-1.0, 0.0, 1.0, 3.0); EMP8_P = (1 / 8, 3 / 8, 2 / 8, 2 / 8)
CFG = (("hoy (P0, 3×364)", "P0", 364), ("+ finish-line", "P3", 364), ("+ 728×3", "P0", 728), ("finish-line + 728×3", "P3", 728))
COSTS = (("OPS heredado de la Parte D", 714.0), ("recurrente GLITCH hoy ($54/mes)", 640.0), ("con Massive Futures sustituido ($25/mes)", 290.0), ("base de la Parte J", 245.0))
WRS = (0.46, 0.47, 0.474, 0.48, 0.49, 0.50)
net0 = {}
for wr in WRS:
    dm = 0.0 if abs(wr - 0.5) < 1e-9 else drift_for_wr(clean, mk, wr); ds = dm / sig_m * sig_s
    cbs = {pol: combine_bank(mes, NB, pol, EMP8, EMP8_P, seed=11, exit_slip=3.0, drift=ds) for pol in ("P0", "P3")}
    xbs = {}
    for sl in (364, 728):
        days = BarDays(clean, MGC["tick_usd"], MGC["fee"], sl, sl, slip=(0.0,), mask=mk, cush_max=9000.0, drift=dm, stop_frac=0.5)
        xbs[sl] = xfa_bank(days, Rules(), pol_fixed(3, sl, sl), NB, seed=21)
    for nm, pol, sl in CFG:
        ps, cd = cbs[pol]; life, pday, pnet = xbs[sl]
        net0[(nm, wr)] = float(run_chain(ps, cd, life, pday, pnet, n=NC, seed=5, ops=0.0)["net"].mean())
    print("  WR", wr, round(time.time() - t0), "s", flush=True)
def equilibrium(nm, ops):
    y = np.array([net0[(nm, w)] - ops for w in WRS]); x = np.array(WRS)
    if y.max() < 0: return None
    if y.min() > 0: return float("nan")
    # regresión lineal sobre toda la rejilla (el neto es casi lineal en WR en este rango) para amortiguar el ruido de simulación
    b, a = np.polyfit(x, y, 1); return -a / b
P("# resultados_K1_equilibrio — equilibrio de la cadena con los costos reales de Eric\n")
P(f"**Fuente y estado.** MODELADO (motor de las Partes A/D; MES 492 días, MGC 443 días; {NB:,} intentos y vidas por punto de la rejilla de WR, ruido de simulación ≈ ± $100 por celda). Costos anuales: los **totales** los dio Eric en el chat (recurrente GLITCH ≈ $54/mes ≈ $640/año; con Massive Futures sustituido ≈ $25/mes ≈ $290/año; $245 = base de la Parte J); **el desglose por rubro NO lo tengo** (SUPUESTO que el recurrente incluye Massive Futures Starter $29/mes, Railway, API de ProjectX). Los $49 por intento de Combine y los $149 de activación ya están dentro del motor. Slippage de entrada del Combine: 8 observaciones de MES (la 8.ª inferida = 0, NO VERIFICADA). La etiqueta de WR es la de H1 (deriva calibrada en el bracket nominal 364/364).\n")
P("## Neto anual por cuenta ($) a WR 47.4 % y 50 %, según costos\n")
P("| costos al año | " + " | ".join(f"{nm} (47.4 / 50 %)" for nm, _, _ in CFG) + " |\n|---|" + "---|" * len(CFG))
for cl, c in COSTS:
    P(f"| {cl}: ${c:,.0f} | " + " | ".join(f"${net0[(nm, 0.474)] - c:,.0f} / ${net0[(nm, 0.50)] - c:,.0f}" for nm, _, _ in CFG) + " |")
P("\n## Equilibrio de la cadena (WR de la etiqueta con neto anual = 0)\n")
P("| costos al año | " + " | ".join(nm for nm, _, _ in CFG) + " |\n|---|" + "---|" * len(CFG))
for cl, c in COSTS:
    cells = []
    for nm, _, _ in CFG:
        e = equilibrium(nm, c); cells.append("neto < 0 en toda la rejilla" if e is None else ("neto > 0 en toda la rejilla" if e != e else f"{e * 100:.2f} %"))
    P(f"| {cl}: ${c:,.0f} | " + " | ".join(cells) + " |")
sl = (net0[("hoy (P0, 3×364)", 0.50)] - net0[("hoy (P0, 3×364)", 0.47)]) / 3.0
P(f"\nPendiente local (hoy): ≈ ${sl:,.0f} por punto de WR ⇒ cada $100 de costos al año mueve el equilibrio ≈ {100 / sl:.2f} pp. De $714 a $290 el equilibrio baja ≈ {(714 - 290) / sl:.2f} pp; de $640 a $290, ≈ {(640 - 290) / sl:.2f} pp.")
P("\n(El motor resta los costos como una constante anual; la API de ProjectX en realidad se cobra por cuenta **activa** y por mes: ver `RESULTADOS_K1.md`.)")
open(os.path.join(HERE, "resultados_K1_equilibrio.md"), "w", encoding="utf-8").write("\n".join(out) + "\n"); print("OK", round(time.time() - t0), "s")
