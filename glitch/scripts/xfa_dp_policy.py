"""Forma de la politica OPTIMA (juego justo) de la XFA Topstep 50K: en cada estado, la distribucion optima del P&L del dia es la combinacion de dos puntos (vertices de la envolvente concava)
que rodea la media -costo. Se reporta en dolares: 'perder $a con prob. p' / 'ganar $b con prob. 1-p'. Mismos supuestos que scripts/xfa_dp_ceiling.py. SANDBOX / R&D."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
from numba import njit
from scripts.pass_rate_ceiling_dp import _hull_eval


@njit(cache=True)
def solve_full(h, days, dd, lock, cap, pct, split, wdthr, wdreq, cost, bmax, dmax):
    n_dd = int(round(dd / h)); lock_n = int(round(lock / h)); cap_n = int(round(cap / h)); wd_n = int(round(wdthr / h))
    bmax_n = int(round(bmax / h)); dmax_n = int(round(dmax / h)); nb = bmax_n + n_dd + 1; nf = n_dd + lock_n + 1
    V = np.zeros((days + 1, nb, nf, wdreq + 1)); xs = np.empty(nb + dmax_n + 4); gs = np.empty(nb + dmax_n + 4)
    for d in range(days - 1, -1, -1):
        for fi in range(nf):
            f = fi - n_dd
            for wd in range(wdreq + 1):
                for ib in range(nb):
                    b = ib - n_dd
                    if b <= f: continue
                    n = 0
                    for dk in range(-(b - f), dmax_n + 1):
                        if dk == -(b - f): g = 0.0
                        else:
                            b2 = b + dk; wd2 = wd + (1 if dk >= wd_n else 0)
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
                                if p > 0:
                                    b3 = b2 - p; bi3 = b3 + n_dd
                                    if bi3 >= nb: bi3 = nb - 1
                                    if bi3 < 0: bi3 = 0
                                    vv = split * p * h + (V[d + 1, bi3, 0 + n_dd, 0] if d + 1 < days else 0.0)
                                    if vv > best: best = vv
                            g = best
                        xs[n] = dk * h; gs[n] = g; n += 1
                    V[d, ib, fi, wd] = _hull_eval(xs, gs, n, -cost)
    return V


def gvec(V, d, b, f, wd, h, dd, lock, cap, pct, split, wdthr, wdreq):
    n_dd = int(round(dd / h)); lock_n = int(round(lock / h)); cap_n = int(round(cap / h)); wd_n = int(round(wdthr / h)); nb = V.shape[1]
    dks = np.arange(-(b - f), 121); gs = np.zeros(len(dks))
    for i, dk in enumerate(dks):
        if dk == -(b - f): continue
        b2 = b + dk; wd2 = min(wd + (1 if dk >= wd_n else 0), wdreq); f2 = f
        if b2 - n_dd > f2: f2 = min(b2 - n_dd, lock_n)
        keep = V[d + 1, min(b2 + n_dd, nb - 1), f2 + n_dd, wd2]; best = keep
        if wd2 >= wdreq and b2 > 0:
            p = min(int(np.floor(pct * b2)), cap_n)
            if p > 0:
                vv = split * p * h + V[d + 1, min(max(b2 - p + n_dd, 0), nb - 1), n_dd, 0]
                best = max(best, vv)
        gs[i] = best
    return dks * h, gs


def hull_support(x, g, x0=0.0):
    pts = sorted(zip(x, g)); H = []
    for p in pts:
        while len(H) >= 2 and (H[-1][0] - H[-2][0]) * (p[1] - H[-2][1]) - (H[-1][1] - H[-2][1]) * (p[0] - H[-2][0]) >= 0: H.pop()
        H.append(p)
    for a, b in zip(H[:-1], H[1:]):
        if a[0] <= x0 <= b[0]:
            w = (x0 - a[0]) / (b[0] - a[0]) if b[0] > a[0] else 0
            return a, b, 1 - w, w, (a[1] * (1 - w) + b[1] * w)
    return H[0], H[-1], 1, 0, H[0][1]


if __name__ == "__main__":
    h = 50.0; days = 40
    V = solve_full(h, days, 2000.0, 0.0, 2000.0, 0.5, 0.9, 150.0, 5, 0.0, 8000.0, 6000.0)
    n_dd = 40
    print(f"Valor optimo desde el inicio (juego justo, sin costos): ${V[0, n_dd, 0, 0]:,.0f}")
    cases = [("inicio: balance $0, piso -$2,000, 0 dias ganadores", 0, -2000, 0), ("balance +$500, piso -$1,500, 0 dias", 10, -1500 // 50 * 50, 0),
             ("balance +$1,000, piso -$1,000, 2 dias ganadores", 20, -1000, 2), ("balance +$2,000, piso $0 (bloqueado), 4 dias ganadores", 40, 0, 4),
             ("balance +$1,500, piso $0, 5 dias ganadores (elegible, ya cobrable)", 30, 0, 5), ("balance +$400, piso $0 (tras un pago), 0 dias", 8, 0, 0)]
    for lab, bsteps, fdollar, wd in cases:
        b = bsteps; f = fdollar // 50
        x, g = gvec(V, 1, b, f, wd, h, 2000.0, 0.0, 2000.0, 0.5, 0.9, 150.0, 5)
        a, bb, pa, pb, val = hull_support(x, g)
        print(f"  {lab}: valor ${val:,.0f} -> apuesta optima: perder ${-a[0]:,.0f} con prob {pa:.0%} / ganar ${bb[0]:,.0f} con prob {pb:.0%}")
