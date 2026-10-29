"""Efecto en el NETO ANUAL por cuenta de las reglas encontradas (tamaño de la XFA 5 micros → 1 al llegar a $1,500; bracket 728; finish-line), con la cadena completa. -> resultados_OPT_CADENA.md
    cd glitch/experimentos/optimo; GLITCH_MGC_PARQUET=... PYTHONPATH=../.. python3 opt_cadena.py
MODELADO e INDICATIVO: las reglas se eligieron en el 60 % viejo de los días y aquí se evalúan con todos (la mitad es dentro de muestra); la robustez fuera de muestra está en resultados_OPT_XFA_ROBUSTEZ.md. Slippage empírico de 8 obs. (8.ª inferida = 0, NO VERIFICADA); OPS $245 y $290."""
import os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [os.path.join(HERE, "..", "xfa"), os.path.join(HERE, "..", "preservacion")]
from chain import combine_bank, run_chain, xfa_bank
from daydata import load_days
from worlds import MGC, drift_for_wr, gold_mask, mgc_days
from xfa_engine import BarDays, Policy, Rules, pol_fixed
NB = 60000; out = []; P = lambda s="": (print(s), out.append(s))
mes = load_days(); clean = mgc_days(True); mk = gold_mask(clean, True); sig_m = float(np.std(clean.cl[mk][:, -1])); sig_s = float(np.std(mes.cl[:, -1]))
EMP8 = (-1.0, 0.0, 1.0, 3.0); EMP8_P = (1 / 8, 3 / 8, 2 / 8, 2 / 8)
def rule(hi, U, lo, sl): return Policy("r", lambda st: np.where(st.b < U, hi, lo).astype(int), "max", sl, sl)
XPLANS = (("3×364 fijo (hoy)", 364, pol_fixed(3, 364, 364)), ("regla 5→1 @ $1,500, bracket 364", 364, rule(5, 1500, 1, 364)), ("3×728 fijo", 728, pol_fixed(3, 728, 728)), ("regla 5→1 @ $1,500, bracket 728", 728, rule(5, 1500, 1, 728)))
P("# resultados_OPT_CADENA — neto anual por cuenta con las reglas encontradas (indicativo)\n")
P("MODELADO e INDICATIVO (ver docstring). Las pruebas fuera de muestra de la regla de tamaño: `resultados_OPT_XFA_ROBUSTEZ.md` (+$72 a +$257 por XFA según periodo y WR). Costos operativos al año: $245 (base de la Parte J), $290 (con Massive Futures sustituido) y $640 (recurrente actual de Eric, SUPUESTO hasta ver los estados de cuenta).\n")
for wr in (0.474, 0.50):
    dm = 0.0 if abs(wr - 0.5) < 1e-9 else drift_for_wr(clean, mk, wr); ds = dm / sig_m * sig_s
    cb = {pol: combine_bank(mes, NB, pol, EMP8, EMP8_P, seed=11, exit_slip=3.0, drift=ds) for pol in ("P0", "P3")}
    xb = {}
    for nm, sl, pol in XPLANS:
        days = BarDays(clean, MGC["tick_usd"], MGC["fee"], sl, sl, slip=(0.0,), mask=mk, cush_max=9000.0, drift=dm, stop_frac=0.5)
        xb[nm] = xfa_bank(days, Rules(), pol, NB, seed=21)
    P(f"\n## WR {wr * 100:.1f} %\n"); P("| Combine | XFA | cobros brutos / año | **neto anual (costos $245)** | (costos $290) | (costos $640) |\n|---|---|---|---|---|---|")
    for cn in ("P0", "P3"):
        for nm, sl, pol in XPLANS:
            life, pday, pnet = xb[nm]; ps, cd = cb[cn]
            r = run_chain(ps, cd, life, pday, pnet, n=40000, seed=5, ops=245.0)
            P(f"| {'hoy (40 fijos)' if cn == 'P0' else 'finish-line'} | {nm} | ${r['cash'].mean():,.0f} | **${r['net'].mean():+,.0f}** | ${r['net'].mean() + 245 - 290:+,.0f} | ${r['net'].mean() + 245 - 640:+,.0f} |")
open(os.path.join(HERE, "resultados_OPT_CADENA.md"), "w", encoding="utf-8").write("\n".join(out) + "\n")
