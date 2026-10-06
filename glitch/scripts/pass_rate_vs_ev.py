"""Pass rate vs EV neto: ¿subir el pass rate del Combine sube el neto mensual? Mismo motor de flujo de caja que dd_cash/real_pnl.py
(Combine reglas reales -> XFA MGC 50K, tope payout $2,000, fees oficiales), solo cambia la geometria del Combine."""
import numpy as np, sys
sys.path.insert(0, ".")
from dd_cash.real_pnl import run
OPS = 43.5 + 1.5 + 14.5
CASES = (("G2 actual (nc40 TP40 SL100)", (40, 40, 100)), ("nc40 TP32 SL100", (40, 32, 100)), ("nc40 TP33 SL100", (40, 33, 100)),
         ("nc25 TP50 SL40 (alt. del 24-sep)", (25, 50, 40)))
for seed in (2026, 7):
    print(f"--- seed {seed} (T=20000 trayectorias x 252 dias)")
    for label, (nc, tp, sl) in CASES:
        r, nd = run(nc, tp, sl, T=20000, seed=seed)
        fp = r["first_pass"]; pay, fc, fa = r["pay_m"], r["fee_c_m"], r["fee_a_m"]
        net = pay - fc - fa - OPS; cum = np.cumsum(net, axis=1)
        print(f"{label:34s} 1erCombine pase={np.mean(fp==1):.3f}  media neto/mes (m3-12)={net.mean(axis=0)[2:].mean():6.0f}  "
              f"payout anual p50={np.percentile(pay.sum(1),50):6.0f}  fees anuales media={(fc+fa).sum(1).mean():6.0f}  "
              f"acum12m p10/p50/p90={np.percentile(cum[:,-1],10):6.0f}/{np.percentile(cum[:,-1],50):6.0f}/{np.percentile(cum[:,-1],90):6.0f}  P(<0)={np.mean(cum[:,-1]<0):.2f}")
