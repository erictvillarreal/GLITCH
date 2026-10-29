"""REGLAS SIMPLES de tamaño para la XFA (implementables): nc_alto mientras el saldo < U, luego nc_bajo; cobro máximo inmediato. Se eligen en el 60 % viejo y se reportan en el 40 % reciente, junto al techo de la DP.
-> resultados_OPT_XFA_REGLAS.md      cd glitch/experimentos/optimo; GLITCH_MGC_PARQUET=... PYTHONPATH=../.. python3 opt_xfa_reglas.py
MODELADO (MGC, XFA 50K, reglas completas del motor; stop 0.5; slippage empírico de 8 obs., 8.ª inferida = 0, NO VERIFICADA)."""
import os, sys, time
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [os.path.join(HERE, "..", "xfa"), os.path.join(HERE, "..", "preservacion")]
from worlds import MGC, gold_mask, mgc_days
from xfa_engine import BarDays, Policy, Rules, pol_fixed, simulate_life
t0 = time.time(); out = []; P = lambda s="": (print(s, flush=True), out.append(s))
EMP8 = (-1.0, 0.0, 1.0, 3.0); EMP8_P = (1 / 8, 3 / 8, 2 / 8, 2 / 8)
clean = mgc_days(True); gm = gold_mask(clean, True); cut = int(0.6 * clean.D)
trm = gm.copy(); trm[cut:] = False; tem = gm.copy(); tem[:cut] = False
N = 15000; NT = 40000; R = Rules()
def prov(sl, mask): return BarDays(clean, MGC["tick_usd"], MGC["fee"], sl, sl, slip=EMP8, slip_p=EMP8_P, mask=mask, cush_max=9000.0, stop_frac=0.5)
def pol(hi, U, lo, sl): return Policy(f"{hi}->{lo}@{U}", lambda st: np.where(st.b < U, hi, lo).astype(int), "max", sl, sl)
res = []
P("# resultados_OPT_XFA_REGLAS — ¿una regla simple (n micros hasta un saldo U, luego menos) se acerca al techo de la DP?\n")
for sl in (364, 546, 728):
    dtr, dte = prov(sl, trm), prov(sl, tem); cands = []
    for hi in (2, 3, 4, 5):
        for U in (500, 1000, 1500, 2000):
            for lo in (1, 2):
                if lo >= hi: continue
                r = simulate_life(dtr, R, pol(hi, U, lo, sl), n=N, seed=21); cands.append((float(r["paid"].mean()), hi, U, lo))
    cands.sort(reverse=True); top = cands[:3]
    base = simulate_life(dte, R, pol_fixed(3, sl, sl), n=NT, seed=22)
    for sc, hi, U, lo in top:
        r = simulate_life(dte, R, pol(hi, U, lo, sl), n=NT, seed=22); d = r["paid"] - base["paid"]
        res.append((sl, hi, U, lo, sc, float(r["paid"].mean()), float(d.mean()), float(1.96 * d.std() / np.sqrt(len(d))), float((r["npay"] >= 1).mean()), float(r["life"].mean()), float(base["paid"].mean())))
    print("  sl", sl, round(time.time() - t0), "s", flush=True)
P("Plan elegido en el 60 % viejo (entrenamiento) y evaluado en el 40 % reciente (prueba), con 3 micros fijos como base pareada. Se muestran las 3 mejores reglas por bracket.\n")
P("| bracket SL = TP | regla | cobrado (entrenamiento) | **cobrado (prueba)** | 3 fijos (prueba) | Δ pareado ± IC95 | P(≥ 1 pago) | vida (días) |\n|---|---|---|---|---|---|---|---|")
for sl, hi, U, lo, sc, pa, dm, se, p1, life, bpaid in res:
    P(f"| {sl} | {hi} micros mientras saldo < ${U:,}, luego {lo} | ${sc:,.0f} | **${pa:,.0f}** | ${bpaid:,.0f} | {dm:+,.0f} ± {se:,.0f} | {p1 * 100:.0f} % | {life:.1f} |")
open(os.path.join(HERE, "resultados_OPT_XFA_REGLAS.md"), "w", encoding="utf-8").write("\n".join(out) + "\n")
