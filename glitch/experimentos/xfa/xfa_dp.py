"""Programacion dinamica (value iteration) de la politica de (tamano, cobro) de una XFA 50K. Maximiza el EFECTIVO esperado cobrado al trader hasta la liquidacion.

Estado (rejilla de $50): fase PRE-lock (piso < 0: se conoce (peak, b)) o POST (piso = $0: solo b), dias ganadores wd en 0..5.
Acciones: nc en NCS (siempre se opera: esperar sin riesgo daria un valor ilusorio) y, con wd = 5, 'pedir el pago maximo (50 % o tope) ahora' vs 'seguir'.
Transicion: distribucion EMPIRICA de resultados diarios (mezcla de los dos lados, dias reales de la mascara) con la mecanica exacta (sim_day) por (nc, colchon).
SIMPLIFICACION declarada: no impone la regla 'ganancia >= $0.01 desde el ultimo pago' (el estado necesario seria demasiado grande); se valida con Monte Carlo sobre el motor completo sin esa regla.
"""
from __future__ import annotations

import numpy as np

from xfa_engine import BarDays, Policy, Rules, State, simulate_life

G = 50.0
NJ_MIN, NJ_MAX = -50, 50
NNODE = NJ_MAX - NJ_MIN + 1
NB_POST = 161                      # b = 0..8000
NP = 40                            # peak = 0..1950 (peak >= 2000 -> POST)
NJ_PRE = 41                        # j = 0..40 -> b = peak - 2000 + 50 j  (j = 0 es el piso)
NC_CUSH = NB_POST                  # colchones 0..8000 en pasos de 50


def build_hist(days: BarDays, ncs, sl):
    """H[k, cm, win, node], PL[k, cm] (prob. de liquidacion), para nc = ncs[k] y colchon 50*cm."""
    H = np.zeros((len(ncs), NC_CUSH, 2, NNODE)); PL = np.zeros((len(ncs), NC_CUSH))
    pool = days.pool
    for k, nc in enumerate(ncs):
        for side in (1, -1):
            K, Pn = days.table(side, nc, sl, 0)
            for cm in range(1, NC_CUSH):
                row = min(5 * cm, K.shape[0] - 1)
                kk, pp = K[row][pool], Pn[row][pool]
                liq = kk == 2
                PL[k, cm] += 0.5 * liq.mean()
                x = pp[~liq] / G; win = (pp[~liq] >= 150.0).astype(int)
                lo = np.floor(x).astype(int); fr = x - lo
                w = 0.5 / len(pp)
                for wi in (0, 1):
                    m = win == wi
                    if not m.any(): continue
                    np.add.at(H[k, cm, wi], np.clip(lo[m] - NJ_MIN, 0, NNODE - 1), w * (1 - fr[m]))
                    np.add.at(H[k, cm, wi], np.clip(lo[m] + 1 - NJ_MIN, 0, NNODE - 1), w * fr[m])
    return H, PL


def solve(H, PL, ncs, rules: Rules, sweeps=400, tol=0.02, split=0.9):
    """Devuelve V_pre[6,NP,NJ_PRE], V_post[6,NB_POST], y las politicas (indice de nc, 1 = pedir pago)."""
    Vpre = np.zeros((6, NP, NJ_PRE)); Vpost = np.zeros((6, NB_POST))
    peak = G * np.arange(NP)[:, None]; jj = np.arange(NJ_PRE)[None, :]
    b_pre = peak - 2000.0 + G * jj                          # (NP, NJ_PRE)
    cm_pre = np.clip(np.round((b_pre - (peak - 2000.0)) / G).astype(int), 0, NC_CUSH - 1)
    valid_pre = jj >= 1
    b_post = G * np.arange(NB_POST); cm_post = np.arange(NB_POST)
    pol_pre = np.zeros((6, NP, NJ_PRE), np.int8); pol_post = np.zeros((6, NB_POST), np.int8)
    pay_pre = np.zeros((6, NP, NJ_PRE), bool); pay_post = np.zeros((6, NB_POST), bool)
    for it in range(sweeps):
        new_pre = np.zeros_like(Vpre); new_post = np.zeros_like(Vpost); delta = 0.0
        bestk_pre = np.zeros((6, NP, NJ_PRE), np.int8); bestk_post = np.zeros((6, NB_POST), np.int8)
        for wd in range(6):
            best_pre = np.full((NP, NJ_PRE), -1.0); best_post = np.full(NB_POST, -1.0)
            for k in range(len(ncs)):
                ev_pre = np.zeros((NP, NJ_PRE)); ev_post = np.zeros(NB_POST)
                for win in (0, 1):
                    wd2 = min(wd + win, 5)
                    for node in range(NNODE):
                        h_pre = H[k, cm_pre, win, node]; h_post = H[k, cm_post, win, node]
                        if not (h_pre.any() or h_post.any()): continue
                        dn = node + NJ_MIN
                        # ---- PRE
                        b2 = b_pre + G * dn; peak2 = np.maximum(peak, b2)
                        lock = peak2 >= 2000.0
                        p2 = np.clip(np.round(peak2 / G).astype(int), 0, NP - 1); j2 = np.clip(np.round((b2 - (peak2 - 2000.0)) / G).astype(int), 0, NJ_PRE - 1)
                        v = np.where(lock, Vpost[wd2][np.clip(np.round(b2 / G).astype(int), 0, NB_POST - 1)], Vpre[wd2][p2, j2])
                        v = np.where(~lock & (j2 == 0), 0.0, v)
                        ev_pre += h_pre * v
                        # ---- POST
                        b2p = b_post + G * dn
                        vp = np.where(b2p <= 0, 0.0, Vpost[wd2][np.clip(np.round(b2p / G).astype(int), 0, NB_POST - 1)])
                        ev_post += h_post * vp
                better = ev_pre > best_pre; best_pre = np.where(better, ev_pre, best_pre); bestk_pre[wd] = np.where(better, k, bestk_pre[wd])
                better = ev_post > best_post; best_post = np.where(better, ev_post, best_post); bestk_post[wd] = np.where(better, k, bestk_post[wd])
            if wd == 5:                                         # opcion de pagar ahora
                g_pre = np.minimum(np.maximum(b_pre, 0.0) * rules.pct, rules.cap); g_post = np.minimum(b_post * rules.pct, rules.cap)
                ok_pre = (g_pre >= rules.minpay) & valid_pre; ok_post = g_post >= rules.minpay
                after_pre = np.clip(np.round((b_pre - g_pre) / G).astype(int), 0, NB_POST - 1)
                after_post = np.clip(np.round((b_post - g_post) / G).astype(int), 0, NB_POST - 1)
                val_pre = split * g_pre + Vpost[0][after_pre]; val_post = split * g_post + Vpost[0][after_post]
                pp = ok_pre & (val_pre > best_pre); best_pre = np.where(pp, val_pre, best_pre); pay_pre[5] = pp
                pq = ok_post & (val_post > best_post); best_post = np.where(pq, val_post, best_post); pay_post[5] = pq
            new_pre[wd] = np.where(valid_pre, best_pre, 0.0); new_post[wd] = np.where(b_post > 0, best_post, 0.0)
        delta = max(np.abs(new_pre - Vpre).max(), np.abs(new_post - Vpost).max())
        Vpre, Vpost = new_pre, new_post; pol_pre, pol_post = bestk_pre, bestk_post
        if delta < tol: break
    return Vpre, Vpost, pol_pre, pol_post, pay_pre, pay_post, it + 1, delta


def dp_policy(ncs, pol_pre, pol_post, pay_pre, pay_post, name="DP"):
    """Politica del motor: lee la tabla de la DP por estado (wd, piso, balance)."""
    def lookup(st: State):
        wd = np.minimum(st.wd, 5)
        pre = st.f < -1e-9
        peak = np.where(pre, st.f + 2000.0, 0.0)
        p = np.clip(np.round(peak / G).astype(int), 0, NP - 1)
        j = np.clip(np.round((st.b - st.f) / G).astype(int), 0, NJ_PRE - 1)
        i = np.clip(np.round(st.b / G).astype(int), 0, NB_POST - 1)
        kpre = pol_pre[wd, p, j]; kpost = pol_post[wd, i]
        ppre = pay_pre[wd, p, j]; ppost = pay_post[wd, i]
        return np.where(pre, kpre, kpost), np.where(pre, ppre, ppost)
    nc_arr = np.asarray(ncs)
    def nc_fn(st): return nc_arr[lookup(st)[0]]
    def pay_fn(st, gmax): return np.where(lookup(st)[1], gmax, 0.0)
    return nc_fn, pay_fn
