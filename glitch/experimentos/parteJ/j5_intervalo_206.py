"""Parte J, J5: intervalo del «+$206» (finish-line + 728×3 a WR 47.4 %, H6 §2.5) rehecho con slippage empírico de 8 obs. y OPS $245/año; bootstrap de bloques de 5 días sobre MES (Combine) y MGC (XFA). -> resultados_J5.md
    cd glitch/experimentos/parteJ; GLITCH_MGC_PARQUET=... PYTHONPATH=../.. python3 j5_intervalo_206.py [--quick]
MODELADO. Semillas fijas. La etiqueta de WR es la de H1 (deriva calibrada en el bracket nominal 364/364): ver REPORTE_H1b.md §5 para lo que significa con 728×3."""
import argparse, math, os, sys, time
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "..", "xfa")); sys.path.insert(0, os.path.join(HERE, "..", "preservacion"))
from chain import combine_bank, run_chain, xfa_bank
from daydata import load_days
from worlds import MGC, drift_for_wr, gold_mask, mgc_days
from xfa_engine import BarDays, Rules, pol_fixed
ap = argparse.ArgumentParser(); ap.add_argument("--quick", action="store_true"); A = ap.parse_args()
B = 8 if A.quick else 30; NB = 15000 if A.quick else 30000; NC = 15000 if A.quick else 30000; SEED = 20261026; OPS = 245.0
t0 = time.time(); out = []; P = lambda s="": (print(s, flush=True), out.append(s))
mes = load_days(); clean = mgc_days(True); mk = gold_mask(clean, True)
sig_m = float(np.std(clean.cl[mk][:, -1])); sig_s = float(np.std(mes.cl[:, -1]))
EMP8 = (-1.0, 0.0, 1.0, 3.0); EMP8_P = (1 / 8, 3 / 8, 2 / 8, 2 / 8)
rng = np.random.default_rng(SEED)
def blocks(npool, Bn):
    nb = math.ceil(npool / 5); st = rng.integers(0, npool - 4, size=(Bn, nb)); return (st[:, :, None] + np.arange(5)).reshape(Bn, -1)[:, :npool]
pm_all = blocks(mes.D, B); pg_all = blocks(int(mk.sum()), B)
pool_mgc = np.nonzero(mk)[0]
CFG = (("hoy (P0, 3×364)", "P0", 364), ("+ finish-line (P3, 3×364)", "P3", 364), ("P0 + 728×3", "P0", 728), ("finish-line + 728×3", "P3", 728))
def run(wr, mes_pool, mgc_pool_pos):
    dm = 0.0 if abs(wr - 0.5) < 1e-9 else drift_for_wr(clean, mk, wr); ds = dm / sig_m * sig_s
    cbs = {pol: combine_bank(mes, NB, pol, EMP8, EMP8_P, seed=11, exit_slip=3.0, drift=ds, pool=mes_pool) for pol in ("P0", "P3")}
    xbs = {}
    for sl in (364, 728):
        days = BarDays(clean, MGC["tick_usd"], MGC["fee"], sl, sl, slip=(0.0,), mask=mk, cush_max=9000.0, drift=dm, stop_frac=0.5)
        if mgc_pool_pos is not None: days.pool = pool_mgc[mgc_pool_pos]
        xbs[sl] = xfa_bank(days, Rules(), pol_fixed(3, sl, sl), NB, seed=21)
    res = {}
    for nm, pol, sl in CFG:
        ps, cd = cbs[pol]; life, pday, pnet = xbs[sl]
        res[nm] = float(run_chain(ps, cd, life, pday, pnet, n=NC, seed=5, ops=0.0)["net"].mean()) - OPS
    return res
P("# resultados_J5 — intervalo del «+$206» (H6 §2.5) y cascada rehecha\n")
P("**Fuentes y estado.** MODELADO sobre días reales de 5 min (MES 492 días para el Combine; MGC 443 días sin la ventana de oro para la XFA). Slippage de entrada del Combine = distribución empírica de 8 observaciones {−1: 1/8, 0: 3/8, +1: 2/8, +3: 2/8} (7 dadas por Eric + una 8.ª **inferida = 0** a partir de «media 0.9, N=8»: **NO VERIFICADA**); slippage de entrada MGC 0 (no medido), stop 0.5, comisión MES $1.22 y MGC $1.92, OPS $245/año. Neto anual por cuenta = efectivo cobrado − tarifas − OPS, horizonte 252 días hábiles (`xfa/chain.py`).")
P(f"IC95 = percentiles 2.5–97.5 de {B} remuestras de bloques de 5 días de la historia real (cada una con {NB:,} intentos y vidas); cuenta lo incierto del conjunto de días, **no** el cambio de régimen, **no** la distribución real de slippage, **no** la etiqueta de WR.\n")
tab = {}
for wr in (0.474, 0.50):
    pt = run(wr, None, None)
    bs = [run(wr, pm_all[b], pg_all[b]) for b in range(B)]
    tab[wr] = (pt, bs); print("  WR", wr, round(time.time() - t0), "s", flush=True)
P("## 1. Neto anual por cuenta ($, OPS $245) y su intervalo\n")
P("| configuración | WR 47.4 % (≈ el medido) | WR 50 % |\n|---|---|---|")
for nm, _, _ in CFG:
    cells = []
    for wr in (0.474, 0.50):
        pt, bs = tab[wr]; v = np.array([x[nm] for x in bs]); cells.append(f"${pt[nm]:,.0f} [{np.percentile(v, 2.5):,.0f}, {np.percentile(v, 97.5):,.0f}]")
    P(f"| {nm} | {cells[0]} | {cells[1]} |")
P("\n## 2. Diferencias pareadas (misma remuestra de días) frente a «hoy»\n")
P("| configuración | Δ a WR 47.4 % [IC95] | ¿IC excluye 0? | Δ a WR 50 % [IC95] | ¿IC excluye 0? |\n|---|---|---|---|---|")
for nm, _, _ in CFG[1:]:
    cells = []
    for wr in (0.474, 0.50):
        pt, bs = tab[wr]; d = np.array([x[nm] - x[CFG[0][0]] for x in bs]); lo, hi = np.percentile(d, 2.5), np.percentile(d, 97.5)
        cells += [f"${pt[nm] - pt[CFG[0][0]]:+,.0f} [{lo:+,.0f}, {hi:+,.0f}]", "SÍ" if (lo > 0 or hi < 0) else "NO"]
    P(f"| {nm} | {cells[0]} | {cells[1]} | {cells[2]} | {cells[3]} |")
v = np.array([x["finish-line + 728×3"] for x in tab[0.474][1]])
P(f"\n**Respuesta al «+$206»:** el valor de H6 (finish-line + 728×3, WR 47.4 %, slippage {{1,3}}, OPS $714) era un solo número sin intervalo. Rehecho con el slippage empírico de 8 observaciones y OPS $245: **${tab[0.474][0]['finish-line + 728×3']:,.0f} [{np.percentile(v, 2.5):,.0f}, {np.percentile(v, 97.5):,.0f}]**; la fracción de remuestras con neto > 0 es {np.mean(v > 0) * 100:.0f} %. La diferencia con $206 combina (i) OPS $714 → $245 (+$469/año) y (ii) el slippage empírico (media 0.9 ticks en vez de 2) y (iii) ruido de simulación; no se separó cada parte.")
open(os.path.join(HERE, "resultados_J5.md"), "w", encoding="utf-8").write("\n".join(out) + "\n")
print("OK", round(time.time() - t0), "s")
