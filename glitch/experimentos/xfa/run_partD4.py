"""Parte D (4): hallazgo 3 (el flatten: ¿ayuda o perjudica?), regimen reciente de volatilidad, y capa de costos/anual. -> resultados_D4.md
    GLITCH_MGC_PARQUET=... python run_partD4.py [--quick]"""
import argparse, os, sys, time
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from run_partD import HDR, metrics, row
from worlds import MGC, gold_mask
from daydata import load_days
from xfa_engine import BarDays, Rules, pol_fixed, simulate_life
SEED = 20261020
ap = argparse.ArgumentParser(); ap.add_argument("--quick", action="store_true"); a = ap.parse_args()
N = 4000 if a.quick else 50000
t0 = time.time(); out = []; P = lambda s="": (print(s, flush=True), out.append(s))
path = os.environ["GLITCH_MGC_PARQUET"]
P(f"# resultados_D4 (N={N} vidas; semilla {SEED}; reglas base; MGC limpio; slip 0)\n")
# ── G. hora del flatten ──
P("## G. ¿Ayuda o perjudica el flatten? Hora de cierre forzado (CT; la barra indicada es la ultima monitoreada), plan a 3×364/364 y b 728×3, W2 sin oro\n"); P(HDR)
for hm, lab in ((10 * 60 + 25, "10:30"), (11 * 60 + 55, "12:00"), (13 * 60 + 25, "13:30"), (14 * 60 + 25, "14:30 (actual)")):
    dd = load_days(path, MGC["ref_hm"], hm, MGC["tick"], fill_gaps=True, dominant_contract=True)
    mk = gold_mask(dd, True)
    for cname, sl in (("a", 364), ("b", 728)):
        days = BarDays(dd, MGC["tick_usd"], MGC["fee"], sl, sl, slip=(0.0,), mask=mk, cush_max=9000.0)
        r = simulate_life(days, Rules(), pol_fixed(3, sl, sl), n=N, seed=SEED)
        tp = np.mean([ (days.table(sd, 3, sl, 0)[0][-1][mk] == 0).mean() for sd in (1, -1)]); fl = np.mean([(days.table(sd, 3, sl, 0)[0][-1][mk] == 3).mean() for sd in (1, -1)])
        P(row(f"flatten {lab}: {cname} (días TP {tp * 100:.0f} %, FLATTEN {fl * 100:.0f} %; {mk.sum()} días)", metrics(r)))
# ── H. regimen reciente ──
dd = load_days(path, MGC["ref_hm"], MGC["last_hm"], MGC["tick"], fill_gaps=True, dominant_contract=True)
rec = np.zeros(dd.D, bool); rec[-250:] = True
P(f"\n## H. Régimen reciente de volatilidad: solo los últimos 250 días limpios ({dd.dates[-250]} → {dd.dates[-1]}) vs toda la historia sin oro\n"); P(HDR)
mk_ng = gold_mask(dd, True)
for lab, mk in (("últimos 250 días", rec), ("toda la historia sin oro", mk_ng)):
    for cname, sl, nc in (("a plan 3×364", 364, 3), ("b 728×3", 728, 3), ("c 1 micro", 364, 1)):
        days = BarDays(dd, MGC["tick_usd"], MGC["fee"], sl, sl, slip=(0.0,), mask=mk, cush_max=9000.0)
        r = simulate_life(days, Rules(), pol_fixed(nc, sl, sl), n=N, seed=SEED)
        P(row(f"{lab}: {cname}", metrics(r)))
P(f"\n(tiempo {time.time() - t0:.0f}s)")
open(os.path.join(HERE, "resultados_D4.md"), "w").write("\n".join(out))
