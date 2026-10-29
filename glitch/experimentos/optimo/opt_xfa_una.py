"""Cobrado de UNA XFA (50K, MGC) a WR 47.4 % (y 50 % como referencia), con IC95 por remuestreo de días (bloques de 5). Planes y periodos fijados ANTES de correr:
planes = 3x364 fijo (hoy), 3x728 fijo, regla 5->1 @ $1,500 con bracket 364 y con 728; periodos = todos los días y el 40 % reciente (fuera de muestra de la regla, que se eligió en el 60 % viejo).
-> resultados_OPT_XFA_UNA.md   cd glitch/experimentos/optimo; GLITCH_MGC_PARQUET=... PYTHONPATH=../.. python3 opt_xfa_una.py
MODELADO (MGC, XFA 50K, reglas completas del motor; `paid` = neto al trader tras el 90/10; antes de restar los $149 de activación; stop 0.5; slippage empírico de 8 obs., 8.ª inferida = 0, NO VERIFICADA)."""
import math, os, sys, time
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [os.path.join(HERE, "..", "xfa"), os.path.join(HERE, "..", "preservacion"), os.path.join(HERE, "..", "labs")]
from labs_motor import calib_drift
from worlds import MGC, gold_mask, mgc_days
from xfa_engine import BarDays, Policy, Rules, pol_fixed, simulate_life
t0 = time.time(); out = []; P = lambda s="": (print(s, flush=True), out.append(s))
EMP8 = (-1.0, 0.0, 1.0, 3.0); EMP8_P = (1 / 8, 3 / 8, 2 / 8, 2 / 8)
clean = mgc_days(True); gm = gold_mask(clean, True); D = clean.D; R = Rules(); N = 40000
r_ = np.maximum(clean.hi.max(1), 0) - np.minimum(clean.lo.min(1), 0); HALF = int(round(np.median(r_) / 2))
rng = np.random.default_rng(20261029)
def mask_range(lo, hi):
    m = gm.copy(); m[:lo] = False; m[hi:] = False; return m
def prov(sl, mask, drift): return BarDays(clean, MGC["tick_usd"], MGC["fee"], sl, sl, slip=EMP8, slip_p=EMP8_P, mask=mask, cush_max=9000.0, stop_frac=0.5, drift=drift)
def rule(hi, U, lo, sl): return Policy("r", lambda st: np.where(st.b < U, hi, lo).astype(int), "max", sl, sl)
PLANS = (("3×364 fijo (hoy)", 364, lambda sl: pol_fixed(3, sl, sl)), ("3×728 fijo", 728, lambda sl: pol_fixed(3, sl, sl)),
         ("regla 5→1 @ $1,500, bracket 364", 364, lambda sl: rule(5, 1500, 1, sl)), ("regla 5→1 @ $1,500, bracket 728", 728, lambda sl: rule(5, 1500, 1, sl)))
PERIODS = (("todos los días (≈ 377 d; la regla se eligió en el 60 % viejo)", mask_range(0, D)), ("40 % reciente (≈ 151 d, fuera de muestra de la regla)", mask_range(int(0.6 * D), D)))
P("# resultados_OPT_XFA_UNA — cobrado de UNA XFA (neto al trader tras el 90/10, antes de los $149 de activación)\n")
P("MODELADO. IC95 por remuestreo de días en bloques de 5 (24 remuestras de 6,000 vidas). Semillas 20261029 / 22.\n")
for wr in (0.474, 0.50):
    dm = 0.0 if wr == 0.5 else calib_drift(clean, wr, HALF)
    for pn, m in PERIODS:
        P(f"\n## WR {wr * 100:.1f} % — {pn}\n")
        P("| plan | cobrado medio [IC95] | mediana | p90 | P(≥ 1 pago) | P(cobrado ≥ $1,000) | vida media (días) | cobrado − $149 |\n|---|---|---|---|---|---|---|---|")
        for nm, sl, mk in PLANS:
            dprov = prov(sl, m, dm); base_pool = dprov.pool.copy(); pol = mk(sl)
            r = simulate_life(dprov, R, pol, n=N, seed=22); pd = r["paid"]; ms = []
            for b in range(24):
                nb = math.ceil(len(base_pool) / 5); st = rng.integers(0, len(base_pool) - 4, size=nb); q = (st[:, None] + np.arange(5)).reshape(-1)[:len(base_pool)]
                dprov.pool = base_pool[q]; ms.append(float(simulate_life(dprov, R, mk(sl), n=6000, seed=22)["paid"].mean()))
            dprov.pool = base_pool
            P(f"| {nm} | **${pd.mean():,.0f}** [{np.percentile(ms, 2.5):,.0f}, {np.percentile(ms, 97.5):,.0f}] | ${np.median(pd):,.0f} | ${np.percentile(pd, 90):,.0f} | {(r['npay'] >= 1).mean() * 100:.0f} % | {(pd >= 1000).mean() * 100:.0f} % | {r['life'].mean():.1f} | ${pd.mean() - 149:+,.0f} |")
            print("  ", wr, pn[:12], nm, round(time.time() - t0), "s", flush=True)
open(os.path.join(HERE, "resultados_OPT_XFA_UNA.md"), "w", encoding="utf-8").write("\n".join(out) + "\n"); print("OK", round(time.time() - t0), "s")
