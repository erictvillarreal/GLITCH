"""
Motor de flujo de caja DIARIO (Combine -> XFA -> nuevo Combine ... ) con distribucion EMPIRICA de PnL por contrato
(bar-walk real de sesion, FLATTEN incluido), vectorizado sobre trayectorias, con TIMING real de cada fee y cada payout
(mes calendario = 21 dias de trading). Reglas copiadas de simulation/monte_carlo.py (Combine: DLL clip, MLL EOD trailing,
consistencia 50%) y core/funded_account.py (XFA: MLL trailing, 5 dias >= $150, payout 50% del balance con tope, split 90%,
piso resetea a 0 en cada payout, Scaling Plan dyn-nc). NO usa el motor binario.
Fees (declarado): monthly_fee al iniciar cada intento de Combine y cada 21 dias que siga activo; activation_fee al pasar.
XFA sin fee mensual (igual que el modelo publicado). Payout: fix balance>0 (variante corregida) o as-is (fix_neg=False).
"""
from __future__ import annotations
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
from core.funded_account import dynamic_nc_for_balance

DAYS_PER_MONTH = 21


class Account:
    def __init__(self, combine_spec, xfa_spec, nc_c, nc_x, samp_c, samp_x, name=""):
        self.cs, self.xs, self.nc_c, self.nc_x, self.samp_c, self.samp_x, self.name = combine_spec, xfa_spec, nc_c, nc_x, samp_c, samp_x, name


def simulate(acc: Account, D: np.ndarray, fix_neg=True, start_mode=0, single_episode=False, lag=0, real=None):
    """D: (T,H) indices de dia (compartidos entre cuentas de la misma trayectoria). Devuelve dict de matrices."""
    T, H = D.shape
    cs, xs = acc.cs, acc.xs
    mode = np.full(T, start_mode, np.int8)
    cb = np.zeros(T); cfl = np.full(T, -cs.mll_distance)
    ccum = np.zeros(T); cbest = np.zeros(T); cdays = np.zeros(T, np.int64)
    xb = np.zeros(T); xfl = np.full(T, -xs.mll_distance); xwd = np.zeros(T, np.int64)
    cash = np.zeros(T); n_att = np.zeros(T, np.int64); wait = np.zeros(T, np.int64)
    take_d = np.zeros((T, H), np.float32); fee_d = np.zeros((T, H), np.float32)
    if start_mode == 0:
        cash -= cs.monthly_fee; n_att += 1
    cum = np.zeros((T, H), np.float32); pay_m = np.zeros((T, H // DAYS_PER_MONTH)); fee_m = np.zeros_like(pay_m)
    fee_c_m = np.zeros_like(pay_m); fee_a_m = np.zeros_like(pay_m)
    first_pass = np.zeros(T, np.int8); first_day = np.zeros(T, np.int64)
    n_pay = np.zeros(T, np.int64); n_pass = np.zeros(T, np.int64)
    for day in range(H):
        mo = min(day // DAYS_PER_MONTH, pay_m.shape[1] - 1)
        idx = D[:, day]
        m0 = mode == 0; m1 = mode == 1
        fee_today = np.zeros(T)
        # ---- Combine (REGLAS REALES: liquidacion MLL en tiempo real, consistencia 55% que sube el target, minimo 2 dias)
        R = real
        unit = R["nc"] * R["tv"]
        dist = cb - cfl                       # cb = profit neto del intento, cfl = piso relativo (arranca en -MLL)
        k = np.clip(np.minimum(R["sl"], np.ceil(dist / unit - 1e-9)), 1, R["kmax"]).astype(int)
        ab = R["adv"][idx, k]; tb = R["tp"][idx, R["tp_ticks"]]
        tp_hit = tb < ab; sl_hit = ~tp_hit & (ab < R["inf"])
        pnl = np.where(tp_hit, R["tp_ticks"] * unit, np.where(sl_hit, -k * unit, R["flat"][idx] * unit)) - R["comm"] * R["nc"]
        pnl = np.where(m0, pnl, 0.0)
        cb = cb + pnl
        ratchet = m0 & (cb - cs.mll_distance > cfl)
        cfl = np.where(ratchet, np.minimum(cb - cs.mll_distance, 0.0), cfl)
        blown0 = m0 & (cb <= cfl)
        alive0 = m0 & ~blown0
        cdays = cdays + m0
        cbest = np.where(alive0 & (pnl > cbest), pnl, cbest)
        need = np.maximum(cs.profit_target, cbest / R["cons"])
        passed = alive0 & (cb >= need) & (cdays >= 2)
        renew = alive0 & ~passed & (cdays % DAYS_PER_MONTH == 0)
        fee_today += np.where(renew, cs.monthly_fee, 0.0)
        fee_c_today = np.where(renew, cs.monthly_fee, 0.0)
        # ---- XFA
        nc_t = np.minimum(dynamic_nc_for_balance(xb, xs.mll_distance, "MGC"), acc.nc_x)
        p1 = np.where(m1, nc_t * acc.samp_x[idx], 0.0)
        xb = xb + p1
        cand = xb - xs.mll_distance
        xfl = np.where(m1 & (cand > xfl), np.minimum(cand, xs.floor_lock_level), xfl)
        blown1 = m1 & (xb <= xfl)
        still = m1 & ~blown1
        xwd = np.where(still & (p1 >= xs.min_winning_day_usd), xwd + 1, xwd)
        elig = still & (xwd >= xs.winning_days_required)
        if fix_neg: elig = elig & (xb > 0)
        take = np.zeros(T)
        if elig.any():
            g = np.minimum(xb[elig] * xs.payout_pct_of_balance, xs.payout_cap_usd)
            xb = xb.copy(); xb[elig] -= g
            xfl = xfl.copy(); xfl[elig] = 0.0
            xwd = xwd.copy(); xwd[elig] = 0
            take[elig] = g * xs.profit_split_trader
            n_pay = n_pay + elig
        # ---- transiciones
        new_fee = blown0 | blown1
        if single_episode: new_fee = blown0
        fee_today += np.where(new_fee, cs.monthly_fee, 0.0)
        fee_c_today = fee_c_today + np.where(new_fee, cs.monthly_fee, 0.0)
        fee_a_today = np.where(passed, cs.activation_fee, 0.0)
        fee_today += fee_a_today
        n_att = n_att + new_fee; n_pass = n_pass + passed
        newfirst = (first_pass == 0) & (blown0 | passed)
        first_pass = np.where(newfirst, np.where(passed, 1, 2), first_pass); first_day = np.where(newfirst, day + 1, first_day)
        reset_c = blown0 | blown1
        if single_episode: reset_c = blown0
        cb = np.where(reset_c, 0.0, cb); cfl = np.where(reset_c, -cs.mll_distance, cfl)
        ccum = np.where(reset_c, 0.0, ccum); cbest = np.where(reset_c, 0.0, cbest); cdays = np.where(reset_c, 0, cdays)
        xb = np.where(passed, 0.0, xb); xfl = np.where(passed, -xs.mll_distance, xfl); xwd = np.where(passed, 0, xwd)
        m3 = mode == 3
        wait = np.where(m3, wait - 1, wait)
        wait = np.where(passed, lag, wait)
        mode = np.where(passed, 1 if lag == 0 else 3, np.where(reset_c, 0, mode)).astype(np.int8)
        mode = np.where(m3 & (wait <= 0), 1, mode).astype(np.int8)
        if single_episode: mode = np.where(blown1, 2, mode).astype(np.int8)
        cash = cash + take - fee_today
        pay_m[:, mo] += take; fee_m[:, mo] += fee_today; fee_c_m[:, mo] += fee_c_today; fee_a_m[:, mo] += fee_a_today
        cum[:, day] = cash
        take_d[:, day] = take; fee_d[:, day] = fee_today
    return dict(take_d=take_d, fee_d=fee_d, cum=cum, pay_m=pay_m, fee_m=fee_m, fee_c_m=fee_c_m, fee_a_m=fee_a_m,
                n_att=n_att, n_pass=n_pass, n_pay=n_pay, first_pass=first_pass, first_day=first_day)
