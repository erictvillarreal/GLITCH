"""Laboratorio de la etapa FONDEADA (XFA o equivalente) en una sola vida de cuenta: payout esperado por cuenta, P(>=1 payout), vida, para cualquier producto/hora/geometria.
Mismas reglas de pago que dd_cash/engine_firms.py (Topstep XFA estandar, Tradeify Select Flex/Daily, Growth, Bulenox Momentum), con tv por producto, SL fijo opcional (Cerebro 2 MGC 364/364)
y liquidacion en el piso (el stop nunca excede la distancia al piso). SANDBOX / R&D, offline."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
from numba import njit
from dd_cash.engine_firms import (F_DD, F_LOCK, F_DLL, F_CAPT, F_CAPF, F_COMM, F_G, F_RHO, F_TP, P_WINTHR, P_CAP1, P_CAP2, P_CAP3, P_CAP4, P_SPLIT, P_MINPAY, P_CONS,
                                  P_REQD, P_BAL, P_PCT, P_MULT, P_FIRST100, K_TOPSTEP, K_FLEX, K_DAILY, K_GROWTH, K_MOMENTUM, cap_nc, firm_specs)
L_TV, L_SLFIX = 9, 10
INF = 10 ** 6


@njit(cache=True)
def play(adv, tpt, flat, di, G, dist, dll, rho, cap, comm, tp_ticks, tv, slfix, amag, slip):
    kmax = adv.shape[1] - 1; tmax = tpt.shape[1] - 1
    nc = int(np.rint(G / (tp_ticks * tv)))
    if nc < 1: nc = 1
    if nc > cap: nc = cap
    unit = nc * tv
    tpk = int(np.ceil((G + comm * nc) / unit - 1e-9))
    if tpk < 1: tpk = 1
    if tpk > tmax: tpk = tmax
    kfloor = int(np.ceil(dist / unit - 1e-9))
    if slfix > 0.0:
        k = int(slfix)
        if kfloor < k: k = kfloor
    elif rho >= 0.999:
        k = kfloor
    else:
        k = int(np.floor(rho * dist / unit))
    if k < 1: k = 1
    if k > kmax: k = kmax
    if dll > 0.0 and dist > dll:
        kd = int(np.floor((dll - comm * nc) / unit))
        if kd < 1: kd = 1
        if kd < k: k = kd
    ab = adv[di, k]; tb = tpt[di, tpk]
    if tb < ab: pnl = tpk * unit
    elif ab < INF:
        loss = k
        if slip > 0.0:                      # llenado del stop: k + slip * (extremo adverso de la barra - k)  (slip=1: peor caso dentro de la barra)
            loss = k + slip * (amag[di, k] - k)
        pnl = -loss * unit
    else: pnl = flat[di] * unit
    return pnl - comm * nc


@njit(cache=True)
def life(adv, tpt, flat, amag, idx, H, F, PF, fkind, seed, slip):
    np.random.seed(seed)
    nidx = len(idx)
    fb = 0.0; ff = -F[F_DD]; peak = 0.0; ref = 0.0; win_days = 0; pay_n = 0; paid_gross = 0.0; best_c = 0.0
    total = 0.0; first = -1; died = 0; days = H; maxtake = 0.0
    for day in range(H):
        di = idx[np.random.randint(0, nidx)]
        dll = F[F_DLL]
        if fkind == K_GROWTH and fb >= 3000.0: dll = 2000.0
        cap = cap_nc(int(F[F_CAPT]), F[F_CAPF], fb, peak)
        pnl = play(adv, tpt, flat, di, F[F_G], fb - ff, dll, F[F_RHO], cap, F[F_COMM], F[F_TP], F[L_TV], F[L_SLFIX], amag, slip)
        fb += pnl
        if fb <= ff:
            died = 1; days = day + 1
            break
        if fb > peak: peak = fb
        if fb - F[F_DD] > ff: ff = min(fb - F[F_DD], F[F_LOCK])
        if pnl >= PF[P_WINTHR]: win_days += 1
        if pnl > best_c: best_c = pnl
        cyc = fb - ref
        g = 0.0
        if fkind == K_TOPSTEP:
            if win_days >= 5 and fb > 0.0:
                g = min(PF[P_PCT] * fb, PF[P_CAP1])
                if g < PF[P_MINPAY]: g = 0.0
        elif fkind == K_FLEX:
            if win_days >= 5 and (pay_n == 0 or cyc > 0.0):
                g = min(PF[P_PCT] * fb, PF[P_CAP1])
                if g < PF[P_MINPAY]: g = 0.0
        elif fkind == K_DAILY:
            if cyc > 0.0:
                g = min(PF[P_MULT] * cyc, PF[P_CAP1], fb - PF[P_BAL])
                if g < PF[P_MINPAY]: g = 0.0
        else:   # K_GROWTH / K_MOMENTUM
            if win_days >= 5 and fb >= PF[P_BAL] and cyc > 0.0 and best_c <= PF[P_CONS] * cyc:
                cp = PF[P_CAP1] if pay_n == 0 else (PF[P_CAP2] if pay_n == 1 else (PF[P_CAP3] if pay_n == 2 else PF[P_CAP4]))
                g = min(cp, fb)
                if g < PF[P_MINPAY]: g = 0.0
        if g > 0.0:
            if PF[P_FIRST100] > 0.0:
                r100 = max(PF[P_FIRST100] - paid_gross, 0.0)
                take = min(g, r100) + (g - min(g, r100)) * PF[P_SPLIT]
            else:
                take = g * PF[P_SPLIT]
            paid_gross += g; fb -= g; ref = fb; win_days = 0; pay_n += 1; best_c = 0.0
            total += take
            if take > maxtake: maxtake = take
            if first < 0: first = day
            if fkind == K_TOPSTEP: ff = 0.0
            elif fkind == K_FLEX or fkind == K_DAILY: ff = max(ff, F[F_LOCK])
    return total, pay_n, days, first, died, maxtake


@njit(cache=True)
def life_many(adv, tpt, flat, amag, idx, H, F, PF, fkind, n, seed0, slip):
    out = np.zeros((n, 6))
    for p in range(n):
        t, k, d, f, x, m = life(adv, tpt, flat, amag, idx, H, F, PF, fkind, seed0 + p, slip)
        out[p, 0] = t; out[p, 1] = k; out[p, 2] = d; out[p, 3] = f; out[p, 4] = x; out[p, 5] = m
    return out


FIRM_KEYS = {"Topstep XFA 50K": ("Topstep 50K (control; escalado XFA supuesto 20/30/40)", K_TOPSTEP),
             "Tradeify Select Flex 50K": ("Tradeify Select Flex 50K", K_FLEX),
             "Tradeify Select Daily 50K": ("Tradeify Select Daily 50K", K_DAILY),
             "Tradeify Growth fondeada 50K": ("Tradeify Growth 50K", K_GROWTH),
             "Bulenox Momentum Master 50K": ("Bulenox Momentum 50K (Opcion 2)", K_MOMENTUM)}


def funded_spec(firm_key, tv, comm, g, rho, tp, slfix=0.0):
    name, kind = FIRM_KEYS[firm_key]
    E, F, PF, k = firm_specs(g_f=g, rho=rho, tp_f=tp)[name]
    F2 = np.zeros(11); F2[:9] = F; F2[F_COMM] = comm; F2[F_G] = g; F2[F_RHO] = rho; F2[F_TP] = tp; F2[L_TV] = tv; F2[L_SLFIX] = slfix
    return F2, PF, kind


def run_life(tab, firm_key, g, rho, tp, slfix=0.0, H=126, n=2000, seed0=1000, idx=None, comm=None, slip=0.0):
    F, PF, kind = funded_spec(firm_key, tab["tv"], tab["comm"] if comm is None else comm, g, rho, tp, slfix)
    idx = np.arange(len(tab["adv"])) if idx is None else idx
    o = life_many(tab["adv"], tab["tpt"], tab["flat"], tab["amag"], idx.astype(np.int64), H, F, PF, kind, n, seed0, float(slip))
    return dict(payout=o[:, 0].mean(), p1=(o[:, 3] >= 0).mean(), npay=o[:, 1].mean(), life=o[:, 2].mean(), died=o[:, 4].mean(), pmedian=float(np.median(o[:, 0])),
                p90=float(np.percentile(o[:, 0], 90)), maxtake=float(o[:, 5].max()))
