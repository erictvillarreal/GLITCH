"""Techo de JUEGO JUSTO del payout esperado por cuenta fondeada (XFA / equivalente), por programacion dinamica.
Identidad: payouts_brutos = suma(P&L) - balance_final; al morir el balance final es el piso (<= 0 en terminos relativos), y E[suma P&L] = -costos en una martingala =>
E[payout bruto] = -E[piso al morir] - costos <= MLL - costos. El DP calcula el valor exacto (<= esa cota) eligiendo cada dia CUALQUIER distribucion de P&L con media -costo.
Estado: balance b, piso f (trailing EOD, tope = lock), dias ganadores wd (0..wdreq); accion: distribucion del P&L del dia; al cierre se puede cobrar si hay elegibilidad.
Topstep XFA 50K: 5 dias >=$150, payout = min(50% del balance, $2,000), 90% al trader, tras el pago el piso pasa a $0.  Tradeify Select Flex 50K (aprox.): pago min(50% del balance, $2,500), piso se fija en +$100 al pagar.
SANDBOX / R&D."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
from numba import njit
from scripts.pass_rate_ceiling_dp import _hull_eval


@njit(cache=True)
def solve(h, D, dd, lock, cap, pct, minpay, split, wdthr, wdreq, floor_after, days, cost, bmax, dmax):
    n_dd = int(round(dd / h)); lock_n = int(round(lock / h)); cap_n = int(round(cap / h)); min_n = int(round(minpay / h))
    after_n = int(round(floor_after / h)); wd_n = int(round(wdthr / h)); bmax_n = int(round(bmax / h)); dmax_n = int(round(dmax / h))
    nb = bmax_n + n_dd + 1            # b en [-n_dd, bmax_n]
    nf = n_dd + lock_n + 1            # piso en [-n_dd, lock_n]
    V = np.zeros((days + 1, nb, nf, wdreq + 1))
    xs = np.empty(nb + dmax_n + 4); gs = np.empty(nb + dmax_n + 4)
    for d in range(days - 1, -1, -1):
        for fi in range(nf):
            f = fi - n_dd
            for wd in range(wdreq + 1):
                for ib in range(nb):
                    b = ib - n_dd
                    if b <= f: continue
                    n = 0
                    for dk in range(-(b - f), dmax_n + 1):
                        if dk == -(b - f):
                            g = 0.0
                        else:
                            b2 = b + dk
                            wd2 = wd + (1 if dk >= wd_n else 0)
                            if wd2 > wdreq: wd2 = wdreq
                            f2 = f
                            if b2 - n_dd > f2: f2 = min(b2 - n_dd, lock_n)
                            bi = b2 + n_dd
                            if bi >= nb: bi = nb - 1
                            keep = V[d + 1, bi, f2 + n_dd, wd2] if d + 1 < days else 0.0
                            best = keep
                            if wd2 >= wdreq and b2 > 0:
                                p = int(np.floor(pct * b2))
                                if p > cap_n: p = cap_n
                                if p >= min_n and p > 0:
                                    b3 = b2 - p
                                    f3 = after_n
                                    if f3 < f2 and False: f3 = f2
                                    bi3 = b3 + n_dd
                                    if bi3 >= nb: bi3 = nb - 1
                                    if bi3 < 0: bi3 = 0
                                    vv = split * p * h + (V[d + 1, bi3, f3 + n_dd, 0] if d + 1 < days else 0.0)
                                    if vv > best: best = vv
                            g = best
                        xs[n] = dk * h; gs[n] = g; n += 1
                    V[d, ib, fi, wd] = _hull_eval(xs, gs, n, -cost)
    return V[0, n_dd, 0, 0]


def topstep(days=60, cost=0.0, h=50.0):
    return solve(h, 0, 2000.0, 0.0, 2000.0, 0.5, 0.0, 0.9, 150.0, 5, 0.0, days, cost, 8000.0, 6000.0)


def flex(days=60, cost=0.0, h=50.0):
    return solve(h, 0, 2000.0, 100.0, 2500.0, 0.5, 250.0, 0.9, 150.0, 5, 100.0, days, cost, 8000.0, 6000.0)


if __name__ == "__main__":
    import time
    print("Techo de juego justo del payout esperado por XFA 50K (al trader, 90%), cualquier politica; cota analitica: 0.9*(MLL=$2,000) - costos = $1,800 - 0.9*costos")
    for days in (20, 40, 80):
        t = time.time(); v = topstep(days=days); print(f"  Topstep XFA, horizonte {days} dias, sin costos: ${v:,.0f}  ({time.time()-t:.0f}s)", flush=True)
    for c in (25.0, 50.0, 100.0):
        print(f"  Topstep XFA, horizonte 40 dias, costo ${c:.0f}/dia: ${topstep(days=40, cost=c):,.0f}", flush=True)
    for days in (40,):
        print(f"  Tradeify Select Flex (aprox.), horizonte {days} dias, sin costos: ${flex(days=days):,.0f}; con $50/dia: ${flex(days=days, cost=50.0):,.0f}", flush=True)
