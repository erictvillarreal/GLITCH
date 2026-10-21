"""Programacion dinamica (value iteration hacia atras) del intento de Combine.

Estado: (peak, bal) en rejilla de $25 (bal 48,000..53,000; peak 50,000..52,000 -- con peak >= 52,000 el piso queda en
50,000, asi que se acota a 52,000). Accion: nc en {0..40}. Dia t usa el lado alternado desde START_IDX.
Recompensa: 1 si el balance de cierre >= 53,000 (la consistencia nunca liga: ver test_regression.py). Liquidacion = 0.
Transicion: distribucion EMPIRICA de resultados diarios (iid sobre los dias reales) para (lado, nc, colchon),
con el pnl repartido linealmente entre los dos nodos vecinos de la rejilla (insesgado para V lineal).
"""
from __future__ import annotations

import numpy as np

from daydata import DayData
from sim import FLOOR_CAP, MLL, NC_MAX, TARGET, OutcomeTable, side_of

G = 25.0
BAL0, BAL1 = 48000.0, 53000.0
NB = int((BAL1 - BAL0) / G) + 1          # 201 (el ultimo = 53,000 = pase)
P0, P1 = 50000.0, FLOOR_CAP + MLL        # 50,000 .. 52,000
NP = int((P1 - P0) / G) + 1              # 81
NM = int(3500 / G) + 1                   # colchones 0..3500 en pasos de 25
JMIN, JMAX = -150, 70                    # desplazamientos de rejilla del pnl (en unidades de $25)
NJ = JMAX - JMIN + 1


def build_hist(dd: DayData, slips, probs, exit_slip, order="adverse", sl=100, tp=32, ncs=range(1, NC_MAX + 1)):
    """H[side_idx, nc, m, j]: prob de pasar de colchon 25*m a un pnl en la rejilla (j+JMIN); LIQ[side_idx,nc,m]: prob de liquidacion."""
    H = np.zeros((2, NC_MAX + 1, NM, NJ)); LIQ = np.zeros((2, NC_MAX + 1, NM))
    for si, side in enumerate((1, -1)):
        for slip, w in zip(slips, probs):
            tab = OutcomeTable(dd, slip, exit_slip, order, sl, tp, step=G)
            for nc in ncs:
                kinds, pnls = tab.get(side, nc)           # (bins de 25, D) con bins = floor(cushion/25)
                for m in range(1, NM):
                    k, p = kinds[m], pnls[m]
                    liq = k == 2
                    LIQ[si, nc, m] += w * liq.mean()
                    pp = p[~liq] / G
                    if pp.size == 0: continue
                    lo = np.floor(pp).astype(int); fr = pp - lo
                    wt = w / len(p)
                    np.add.at(H[si, nc, m], np.clip(lo - JMIN, 0, NJ - 1), wt * (1 - fr))
                    np.add.at(H[si, nc, m], np.clip(lo + 1 - JMIN, 0, NJ - 1), wt * fr)
    return H, LIQ


def solve(H, LIQ, start_idx, horizon=60, target_idx=NB - 1, want_q0=False):
    """Devuelve V[t] y pol[t] (t = 0..horizon-1), arreglos (NP, NB). Con want_q0 tambien Q0[nc] (valor de empezar con nc hoy y seguir optimo)."""
    bal_val = BAL0 + G * np.arange(NB)
    peak_val = P0 + G * np.arange(NP)
    floor_val = np.minimum(peak_val - MLL, FLOOR_CAP)
    cush = bal_val[None, :] - floor_val[:, None]          # (NP, NB)
    valid = (cush >= G - 1e-9) & (bal_val[None, :] < BAL1) & ((bal_val[None, :] <= peak_val[:, None] + 1e-9) | (peak_val[:, None] >= P1 - 1e-9))
    mgrid = np.clip(np.round(cush / G).astype(int), 0, NM - 1)
    V = np.zeros((NP, NB)); V[:, -1] = 1.0                # pase absorbente
    pols = np.zeros((horizon, NP, NB), dtype=np.int8); Vs = np.zeros((horizon + 1, NP, NB)); Vs[horizon] = V
    ib = np.arange(NB)[None, :]; ip = np.arange(NP)[:, None]
    Q0 = np.zeros((NC_MAX + 1, NP, NB)) if want_q0 else None
    for t in range(horizon - 1, -1, -1):
        si = 0 if side_of(start_idx + t) == 1 else 1
        Vn = Vs[t + 1]
        best = Vn.copy(); bestn = np.zeros((NP, NB), dtype=np.int8)       # nc=0: no operar, el estado no cambia
        active = np.where(H[si].sum(axis=(0, 1)) > 0)[0]                 # j con masa para este lado
        for nc in range(1, NC_MAX + 1):
            ev = np.zeros((NP, NB))
            for j in active:
                pj = H[si, nc, :, j][mgrid]
                if not pj.any(): continue
                db = j + JMIN
                nb_idx = ib + db
                passed = nb_idx >= NB - 1
                nb_c = np.clip(nb_idx, 0, NB - 1)
                newbal = BAL0 + G * nb_c
                np_idx = np.clip(np.round((np.maximum(peak_val[:, None], newbal) - P0) / G).astype(int), 0, NP - 1)
                v_next = np.where(passed, 1.0, Vn[np_idx, nb_c])
                ev += pj * v_next
            if want_q0 and t == 0: Q0[nc] = ev
            better = ev > best + 1e-12
            best = np.where(better, ev, best); bestn = np.where(better, nc, bestn).astype(np.int8)
        best = np.where(valid, best, 0.0); best[:, -1] = 1.0
        Vs[t] = best; pols[t] = bestn
        if want_q0 and t == 0: Q0[0] = Vn
    return (Vs, pols, Q0) if want_q0 else (Vs, pols)


def idx_state(bal, peak):
    bi = int(round((bal - BAL0) / G)); pi = int(round((min(peak, P1) - P0) / G))
    return pi, bi


def policy_from_dp(pols, start_idx):
    horizon = pols.shape[0]
    def f(c):
        tt = min(c.t, horizon - 1)
        bi = np.clip(np.round((c.bal - BAL0) / G).astype(int), 0, NB - 1)
        pi = np.clip(np.round((np.minimum(c.peak, P1) - P0) / G).astype(int), 0, NP - 1)
        return pols[tt, pi, bi].astype(int)
    return f


def solve_cost(H, LIQ, sub, reset, delay=0.0, sweeps=500, tol=0.005, verbose=False, want_q=False):
    """Costo esperado de bolsillo (suscripcion por dia + reset por liquidacion + 'delay' por dia) hasta PASAR, con
    reinicio desde cuenta nueva (50,000/50,000) tras cada liquidacion. Horizonte infinito, estado incluye la paridad del dia.
    C[par] con par = (dia % 2): par 0 -> LONG, par 1 -> SHORT. Devuelve C (2,NP,NB), pol (2,NP,NB) y F (costo de cuenta nueva)."""
    bal_val = BAL0 + G * np.arange(NB); peak_val = P0 + G * np.arange(NP)
    floor_val = np.minimum(peak_val - MLL, FLOOR_CAP)
    cush = bal_val[None, :] - floor_val[:, None]
    valid = (cush >= G - 1e-9) & (bal_val[None, :] < BAL1) & ((bal_val[None, :] <= peak_val[:, None] + 1e-9) | (peak_val[:, None] >= P1 - 1e-9))
    mgrid = np.clip(np.round(cush / G).astype(int), 0, NM - 1)
    ib = np.arange(NB)[None, :]
    day = sub + delay
    C = np.full((2, NP, NB), 500.0); C[:, :, -1] = 0.0
    pol = np.zeros((2, NP, NB), dtype=np.int8)
    f_pi, f_bi = int(round((50000 - P0) / G)), int(round((50000 - BAL0) / G))
    Qc = np.zeros((2, NC_MAX + 1, NP, NB)) if want_q else None
    for it in range(sweeps):
        Cn = C.copy(); delta = 0.0
        for par in (0, 1):
            side_i = par                          # par 0 -> LONG (si=0), par 1 -> SHORT (si=1)
            Cnext = Cn[1 - par]; Fn = Cn[1 - par][f_pi, f_bi]
            best = day + Cnext; bestn = np.zeros((NP, NB), dtype=np.int8)
            if want_q: Qc[par, 0] = day + Cnext
            active = np.where(H[side_i].sum(axis=(0, 1)) > 0)[0]
            for nc in range(1, NC_MAX + 1):
                ev = np.zeros((NP, NB))
                for j in active:
                    pj = H[side_i, nc, :, j][mgrid]
                    if not pj.any(): continue
                    nb_idx = ib + j + JMIN
                    passed = nb_idx >= NB - 1
                    nb_c = np.clip(nb_idx, 0, NB - 1)
                    newbal = BAL0 + G * nb_c
                    np_idx = np.clip(np.round((np.maximum(peak_val[:, None], newbal) - P0) / G).astype(int), 0, NP - 1)
                    ev += pj * np.where(passed, 0.0, Cnext[np_idx, nb_c])
                ev += LIQ[side_i, nc, :][mgrid] * (reset + Fn)
                ev += day
                if want_q: Qc[par, nc] = ev
                better = ev < best - 1e-9
                best = np.where(better, ev, best); bestn = np.where(better, nc, bestn).astype(np.int8)
            best = np.where(valid, best, 0.0); best[:, -1] = 0.0
            delta = max(delta, float(np.abs(best - C[par]).max()))
            C[par] = best; pol[par] = bestn
        if verbose and it % 20 == 0: print(f"  sweep {it}: delta={delta:.4f}  F={C[0][f_pi, f_bi]:.2f}/{C[1][f_pi, f_bi]:.2f}", flush=True)
        if delta < tol: break
    return (C, pol, (C[0][f_pi, f_bi], C[1][f_pi, f_bi]), Qc) if want_q else (C, pol, (C[0][f_pi, f_bi], C[1][f_pi, f_bi]))
