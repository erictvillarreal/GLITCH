"""Geometria de Cerebro 2 en la XFA Topstep 50K (MGC 7:13 CT, direccion alternada): rejilla nc x (TP=SL en ticks) con stop fijo (recortado por la distancia al piso, como la liquidacion real).
Metricas por cuenta XFA (una vida, 126 dias): payout esperado al trader (90%), P(>=1 payout), vida media, payouts por cuenta; muestra completa y por mitades (H1/H2). Referencia actual: nc=3, 364/364.
SANDBOX / R&D, offline. Comparar con el techo de juego justo ($1,350, scripts/xfa_dp_ceiling.py)."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
from scripts.tables_generic import build
from dd_cash.xfa_lab import run_life

if __name__ == "__main__":
    tab = build("MGC", 7 * 60 + 13); n = len(tab["adv"]); h1 = np.arange(n // 2); h2 = np.arange(n // 2, n); allx = np.arange(n)
    print(f"MGC 7:13 CT, {n} dias, XFA Topstep 50K, payout esperado por cuenta al trader (P(>=1 pago)) | H1 / H2")
    ts = (100, 150, 200, 250, 300, 364)
    print("nc \\ TP=SL ticks".ljust(18) + "".join(f"{t:>26d}" for t in ts))
    best = []
    for nc in (1, 2, 3, 4, 5, 6):
        row = f"nc={nc}".ljust(18)
        for t in ts:
            G = nc * t * 1.0
            r = run_life(tab, "Topstep XFA 50K", g=G, rho=0, tp=t, slfix=t, H=126, n=8000, seed0=21, idx=allx)
            a = run_life(tab, "Topstep XFA 50K", g=G, rho=0, tp=t, slfix=t, H=126, n=4000, seed0=31, idx=h1)
            b = run_life(tab, "Topstep XFA 50K", g=G, rho=0, tp=t, slfix=t, H=126, n=4000, seed0=41, idx=h2)
            row += f"  ${r['payout']:>5,.0f} ({r['p1']:>3.0%}) {a['payout']:>5,.0f}/{b['payout']:>5,.0f}"
            best.append((r['payout'], nc, t, r, a, b))
        print(row)
    best.sort(key=lambda x: -x[0])
    cur = next(x for x in best if x[1] == 3 and x[2] == 364)
    print(f"\nActual (nc=3, 364/364): payout/XFA ${cur[0]:,.0f}, P(>=1) {cur[3]['p1']:.0%}, vida {cur[3]['life']:.0f} dias, pagos {cur[3]['npay']:.2f} (H1 ${cur[4]['payout']:,.0f} / H2 ${cur[5]['payout']:,.0f})")
    print("Top-5 de la rejilla (muestra completa):")
    for p, nc, t, r, a, b in best[:5]:
        print(f"   nc={nc} TP=SL={t}: ${p:,.0f}  P(>=1) {r['p1']:.0%} vida {r['life']:.0f}d pagos {r['npay']:.2f} | H1 ${a['payout']:,.0f} / H2 ${b['payout']:,.0f} | riesgo por trade <= ${nc*t:,.0f}")
