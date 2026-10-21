"""Cadena anual de UNA cuenta (Combine MES -> XFA MGC -> Combine ...) con el motor nuevo en cada etapa, rampa, retrasos y costos reales (Parte D, §3 'UN solo rango anual').

Combine: banco de intentos (P(pase), dias) con la mecanica de la Parte A (MES, nc 40 fijo = P0, o finish-line = P3; slip de entrada anclado a la referencia; consistencia oficial).
XFA: banco de vidas del xfa_engine (pagos con su dia). Cadena: intento -> si pasa, $149 de activacion, 1 dia de activacion manual, vida de la XFA; si la XFA muere o el Combine se liquida,
nueva compra/reset de $49 al dia siguiente. Efectivo: pagos cobrados 5 dias habiles despues de pedirlos (retraso de la politica de pagos) menos tarifas menos $714/ano compartidos.
Horizonte: 252 dias habiles desde el 19-oct-2026 (sin calendario de feriados). Semilla fija."""
from __future__ import annotations

import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "..", "preservacion"))
from sim import (FLOOR_CAP, MLL, NC_MAX, TARGET, OutcomeTable, side_of, tp_net_per_contract)  # noqa: E402

H = 252; LAG_CASH = 5; ACT_DAYS = 1; OPS = 714.0


def combine_bank(dd_mes, n, policy="P0", slips=(1.0, 3.0), slip_p=(0.5, 0.5), seed=1, maxdays=60, exit_slip=3.0, drift=0.0):
    """Intentos de Combine desde cuenta nueva (50,000/50,000, meta 3,000): devuelve passed (bool) y days (dias de trading consumidos)."""
    rng = np.random.default_rng(seed)
    tabs = {s: OutcomeTable(dd_mes, s, exit_slip, "adverse", 100, 32, step=10.0, drift=drift) for s in slips}
    D = dd_mes.D
    bal = np.zeros(n); peak = np.zeros(n); best = np.zeros(n)                # relativo: ganancia del intento
    alive = np.ones(n, bool); passed = np.zeros(n, bool); days = np.zeros(n, int); cdays = np.zeros(n, int)
    par0 = rng.integers(0, 2, n)
    for t in range(maxdays):
        a = alive
        if not a.any(): break
        floor = np.minimum(peak - MLL, 0.0)
        cush = bal - floor                                   # colchon = balance - piso (ambos relativos a $0 de ganancia)
        target = np.maximum(3000.0, best / 0.55)
        need = np.maximum(target - bal, 0.0)
        if policy == "P0": nc = np.full(n, NC_MAX)
        else: nc = np.clip(np.ceil(need / tp_net_per_contract(3.0) - 1e-9).astype(int), 1, NC_MAX)
        side = np.where((par0 + t) % 2 == 0, 1, -1)
        idx = rng.integers(0, D, n); sc = rng.choice(len(slips), size=n, p=slip_p)
        kind = np.full(n, 3, np.int8); pnl = np.zeros(n)
        for si, s in enumerate(slips):
            for sd in (1, -1):
                for ncv in np.unique(nc[a & (sc == si) & (side == sd)]):
                    m = a & (sc == si) & (side == sd) & (nc == ncv)
                    K, Pn = tabs[s].get(sd, int(ncv)); b = tabs[s].bin_of(cush[m] + 0.0)
                    kind[m] = K[b, idx[m]]; pnl[m] = Pn[b, idx[m]]
        liq = a & (kind == 2); ok = a & ~liq
        bal = np.where(ok, bal + pnl, bal); bal = np.where(liq, floor, bal)
        best = np.where(ok, np.maximum(best, pnl), best)
        peak = np.where(ok, np.maximum(peak, bal), peak)
        cdays += a; days = np.where(a, t + 1, days)
        target2 = np.maximum(3000.0, best / 0.55)
        newly = ok & (bal >= target2 - 1e-9) & (cdays >= 2)
        passed |= newly; alive = alive & ~liq & ~newly
    return passed, np.maximum(days, 1)


def xfa_bank(days, rules, policy, n, seed=2, k=14):
    from xfa_engine import simulate_life
    r = simulate_life(days, rules, policy, n=n, seed=seed, record_k=k)
    return r["life"].astype(int), r["pay_day"], r["pay_net"]


def run_chain(cb_passed, cb_days, xb_life, xb_pday, xb_pnet, n=50000, seed=3, first_cash_lag=LAG_CASH):
    rng = np.random.default_rng(seed)
    t = np.zeros(n, int); cash = np.zeros(n); fees = np.zeros(n); npass = np.zeros(n); npay_cash = np.zeros(n)
    active = np.ones(n, bool)
    for _ in range(400):
        a = active & (t < H)
        if not a.any(): break
        i = rng.integers(0, len(cb_passed), n)
        fees += np.where(a, 49.0, 0.0)                               # compra o reset al inicio de cada intento
        t_end = t + cb_days[i]
        ps = a & cb_passed[i] & (t_end < H)
        fees += np.where(ps, 149.0, 0.0); npass += ps
        j = rng.integers(0, len(xb_life), n)
        t_x = t_end + ACT_DAYS + 1
        K = xb_pday.shape[1]
        for kk in range(K):
            d = xb_pday[j, kk]; net = xb_pnet[j, kk]
            tc = t_x + d + first_cash_lag
            m = ps & (d >= 0) & (tc < H)
            cash += np.where(m, net, 0.0); npay_cash += m
        t = np.where(ps, t_x + xb_life[j], t_end + 1)
        t = np.where(a, t, t)
        active = active & (t < H)
    net = cash - fees - OPS
    return dict(net=net, cash=cash, fees=fees, npass=npass, npay=npay_cash)
