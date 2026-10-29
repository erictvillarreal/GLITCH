"""Robustez de las reglas de tamaño de la XFA: (a) IC95 por remuestreo de DÍAS (bloques de 5), (b) división invertida (probar en el 40 % más VIEJO), (c) tres periodos independientes (tercios), (d) WR 47.4 / 50 / 52.
-> resultados_OPT_XFA_ROBUSTEZ.md   cd glitch/experimentos/optimo; GLITCH_MGC_PARQUET=... PYTHONPATH=../.. python3 opt_xfa_robustez.py
MODELADO (MGC, XFA 50K; stop 0.5; slippage empírico de 8 obs., 8.ª inferida = 0, NO VERIFICADA). Regla = «n_alto micros mientras el saldo < U, luego n_bajo»; cobro máximo inmediato."""
import math, os, sys, time
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [os.path.join(HERE, "..", "xfa"), os.path.join(HERE, "..", "preservacion"), os.path.join(HERE, "..", "labs")]
from labs_motor import calib_drift
from worlds import MGC, gold_mask, mgc_days
from xfa_engine import BarDays, Policy, Rules, pol_fixed, simulate_life
t0 = time.time(); out = []; P = lambda s="": (print(s, flush=True), out.append(s))
EMP8 = (-1.0, 0.0, 1.0, 3.0); EMP8_P = (1 / 8, 3 / 8, 2 / 8, 2 / 8)
clean = mgc_days(True); gm = gold_mask(clean, True); D = clean.D; R = Rules(); N = 20000
r_ = np.maximum(clean.hi.max(1), 0) - np.minimum(clean.lo.min(1), 0); HALF = int(round(np.median(r_) / 2))
rng = np.random.default_rng(20261028)
def mask_range(lo, hi):
    m = gm.copy(); m[:lo] = False; m[hi:] = False; return m
def prov(sl, mask, drift=0.0): return BarDays(clean, MGC["tick_usd"], MGC["fee"], sl, sl, slip=EMP8, slip_p=EMP8_P, mask=mask, cush_max=9000.0, stop_frac=0.5, drift=drift)
def pol(hi, U, lo, sl): return Policy("r", lambda st: np.where(st.b < U, hi, lo).astype(int), "max", sl, sl)
def paired(dprov, pols, sl, pool=None, n=N, seed=22):
    if pool is not None: dprov.pool = pool
    b = simulate_life(dprov, R, pol_fixed(3, sl, sl), n=n, seed=seed); r = simulate_life(dprov, R, pols, n=n, seed=seed)
    return float(r["paid"].mean()), float(b["paid"].mean()), float(r["paid"].mean() - b["paid"].mean()), float((r["npay"] >= 1).mean()), float((b["npay"] >= 1).mean()), float(r["life"].mean()), float(b["life"].mean())
RULES = (("5 micros hasta $1,500, luego 1", 5, 1500, 1), ("4 micros hasta $1,500, luego 1", 4, 1500, 1), ("5 micros hasta $2,000, luego 1", 5, 2000, 1))
P("# resultados_OPT_XFA_ROBUSTEZ — ¿la ventaja de las reglas de tamaño es real o ruido de selección?\n")
P("## (a) y (b) Periodos de prueba distintos y WR (cobrado por XFA; Δ = regla − 3 micros fijos, pareado)\n")
P("| bracket | regla | periodo de prueba | WR | cobrado regla | cobrado 3 fijos | Δ [IC95 por días] | P(≥ 1 pago) regla / 3 fijos | vida regla / 3 fijos |\n|---|---|---|---|---|---|---|---|---|")
periods = (("40 % reciente (≈ 151 d)", mask_range(int(0.6 * D), D)), ("40 % más viejo (≈ 151 d)", mask_range(0, int(0.4 * D))), ("tercio central", mask_range(int(D / 3), int(2 * D / 3))))
for sl in (364, 728):
    for nm, hi, U, lo in RULES[:2]:
        for pn, m in periods:
            for wr in ((0.50,) if pn != periods[0][0] else (0.474, 0.50, 0.52)):
                dm_ = 0.0 if wr == 0.5 else calib_drift(clean, wr, HALF)
                dprov = prov(sl, m, dm_); base_pool = dprov.pool.copy(); pr = pol(hi, U, lo, sl)
                pt = paired(dprov, pr, sl, base_pool)
                ds = []
                for b in range(24):
                    nb = math.ceil(len(base_pool) / 5); st = rng.integers(0, len(base_pool) - 4, size=nb); q = (st[:, None] + np.arange(5)).reshape(-1)[:len(base_pool)]
                    ds.append(paired(dprov, pr, sl, base_pool[q], n=6000)[2])
                P(f"| {sl} | {nm} | {pn} | {wr * 100:.1f} % | ${pt[0]:,.0f} | ${pt[1]:,.0f} | **{pt[2]:+,.0f}** [{np.percentile(ds, 2.5):+,.0f}, {np.percentile(ds, 97.5):+,.0f}] | {pt[3] * 100:.0f} % / {pt[4] * 100:.0f} % | {pt[5]:.1f} / {pt[6]:.1f} |")
        print("  ", sl, nm, round(time.time() - t0), "s", flush=True)
open(os.path.join(HERE, "resultados_OPT_XFA_ROBUSTEZ.md"), "w", encoding="utf-8").write("\n".join(out) + "\n"); print("OK", round(time.time() - t0), "s")
