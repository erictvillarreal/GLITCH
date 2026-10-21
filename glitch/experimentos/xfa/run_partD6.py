"""Parte D (6): estructura de la politica optima de la DP (en que estados reduce/aumenta el tamano y cuando cobra). -> resultados_D6.md
    GLITCH_MGC_PARQUET=... python run_partD6.py"""
import os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from worlds import MGC, gold_mask, mgc_days
from xfa_dp import G, build_hist, solve
from xfa_engine import BarDays, Rules
clean = mgc_days(True); mk = gold_mask(clean, True); NCS = (1, 2, 3, 4, 5, 6, 8)
out = []; P = lambda s="": (print(s, flush=True), out.append(s))
P("# resultados_D6: estructura de la politica optima (DP, W2, reglas base sin la regla de ganancia desde el ultimo pago)\n")
for sl in (364, 728):
    days = BarDays(clean, MGC["tick_usd"], MGC["fee"], sl, sl, slip=(0.0,), mask=mk, cush_max=9000.0)
    H, PL = build_hist(days, NCS, sl)
    Vpre, Vpost, pp, pq, ypp, ypq, its, delta = solve(H, PL, NCS, Rules(profit_rule=False))
    P(f"\n## SL = TP = {sl}  (V0 = ${Vpre[0, 0, 40]:,.0f})\n")
    P("nc optimo en la fase POST (piso = $0 o ya pagado), por balance b (columnas) y dias ganadores wd (filas):\n")
    bs = [250, 500, 750, 1000, 1500, 2000, 3000, 4000, 6000]
    P("| wd \\ b | " + " | ".join(f"${b:,}" for b in bs) + " |\n|---|" + "---|" * len(bs))
    for wd in range(6):
        P(f"| {wd} | " + " | ".join(str(NCS[pq[wd, int(b / G)]]) + ("*" if ypq[wd, int(b / G)] else "") for b in bs) + " |")
    P("\n(* = pedir el pago maximo en ese estado). nc optimo en la fase PRE-lock (piso < 0): filas = pico de balance, columnas = balance, wd = 0:\n")
    pk = [0, 500, 1000, 1500]; bsel = [-1000, -500, 0, 500, 1000, 1500]
    P("| pico \\ b | " + " | ".join(f"${b:,}" for b in bsel) + " |\n|---|" + "---|" * len(bsel))
    for peak in pk:
        cells = []
        for b in bsel:
            j = int(round((b - (peak - 2000)) / G))
            cells.append(str(NCS[pp[0, int(peak / G), j]]) if 1 <= j <= 40 else "-")
        P(f"| ${peak:,} | " + " | ".join(cells) + " |")
    first_pay = [(b, wd) for wd in (5,) for b in range(250, 8000, 50) if ypq[wd, int(b / G)]]
    P(f"\nCon wd = 5 en fase POST, el primer balance en el que conviene PEDIR el pago maximo: {first_pay[0][0] if first_pay else 'nunca (dentro de $8,000)'}")
open(os.path.join(HERE, "resultados_D6.md"), "w").write("\n".join(out))
