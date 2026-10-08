"""Motor de PALANCAS ESTRUCTURALES (SANDBOX / R&D, no produccion). Copia extendida de dd_cash/engine_real_cal.py (validado) con:
  * reglas de pago verificadas en help.topstep.com (09-oct-2026): pago minimo $125, "ganancia neta > $0.01 desde el ultimo pago (el primero exento)", ruta Consistency (40% del mejor dia, >=3 dias de trading, tope
    $3,000 en 50K), tope Standard $2,000 (o $4,000/$6,000 con DLL comprado con el Combine = oferta temporal), split 90/10 con primer tramo opcional al 100% (supuesto del usuario, no verificado);
  * precios por plan (Standard $49 + $149 de activacion; No Activation Fee $95 / $85 con DLL); el reinicio cuesta lo mismo que la mensualidad;
  * tablas genericas por producto (tables_generic) con slippage de stop (llenado en el extremo de la barra, `slip` en [0,1]) y DLL opcional en el Combine;
  * politicas de ciclo: tope K de compras de Combine por ano, paro por perdida acumulada, bloqueo de ganancia;
  * contadores de conducta (RTP): intentos, dias con MLL tocado (Combine o XFA), operaciones al tamano maximo.
Con `legacy=True` y tablas MES/MGC reproduce engine_real_cal.simulate exactamente (ver tests/test_lever_engine.py).
No toca produccion. Cualquier cambio de logica de capital es solo propuesta."""
from __future__ import annotations
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dataclasses import dataclass, field
import numpy as np

DAYS_PER_MONTH = 21
INF = 10 ** 6


@dataclass
class Spec:
    # ---- Combine (tablas first-touch por dia; indices alineados con el eje de dias comun)
    adv: np.ndarray; tpt: np.ndarray; flat: np.ndarray; amag: np.ndarray | None
    tv: float = 1.25; comm: float = 1.22; nc: int = 40; tp_ticks: int = 32; sl: int = 100; slip: float = 0.0
    kmax: int = 400; dll: float | None = None; mll: float = 2000.0; target: float = 3000.0
    cons: float = 0.55; min_days: int = 2; cap_micros: int = 50
    # ---- precios
    fee: float = 49.0; act: float = 149.0
    # ---- XFA (serie P&L por contrato y dia; alineada con el mismo eje)
    xser: np.ndarray | None = None; nc_x: int = 3; xmll: float = 2000.0
    xadv: np.ndarray | None = None; xtpt: np.ndarray | None = None; xflat: np.ndarray | None = None; xamag: np.ndarray | None = None   # tablas del bracket de la XFA (liquidacion en tiempo real explicita)
    x_tv: float = 1.0; x_comm: float = 1.92; x_sl: int = 364; x_tp: int = 364; xliq: bool = False; xkmax: int = 800
    win_usd: float = 150.0; win_days: int = 5; pct: float = 0.5; cap: float = 2000.0; split: float = 0.9; first100: float = 0.0
    minpay: float = 125.0; profit_rule: bool = True; path: str = "std"; cons_x: float = 0.4; cons_days: int = 3
    pay_thr: float = 0.0              # balance minimo para pedir el pago (politica de retiro)
    xdll: float | None = None         # DLL de la XFA (suave: recorta el P&L del dia)
    x_rho: float | None = None; x_unit: float = 364.0   # tamano adaptativo: contratos <= rho*(distancia al piso)/x_unit (x_unit = USD por contrato del bracket; None = nc_x fijo)
    mgc_restricted: bool = True       # tope de contratos MGC bajo $1,500 = 12 micros, $1,500 = 18, $2,000+ = 31 (help.topstep.com 13613539, tabla de simbolos restringidos)
    legacy: bool = False              # True = reglas del motor validado (sin pago minimo, sin regla de ganancia neta, sin slip/DLL)
    # ---- politicas de ciclo
    K: int | None = None              # maximo de compras de Combine en el horizonte (incluye la inicial)
    stop_loss: float | None = None    # dejar de comprar si la caja acumulada <= -stop_loss
    lock_gain: float | None = None    # dejar de comprar si la caja acumulada >= lock_gain
    fee_scale: float = 1.0; pay_scale: float = 1.0
    haircut: float = 1.0              # el -25% se aplica fuera del motor (en el reporte)
    entry_slip: int = 0               # slippage de ENTRADA adverso en ticks (llenado de mercado peor que el cierre de la barra de referencia), ambos stages
    tp_fill_extra: int = 0            # el TP limite solo se considera lleno si el precio lo cruza este numero de ticks (sensibilidad de colocacion)
    p_up: float = 0.0; p_dn: float = 0.0; seed: int = 0   # palanca EXOGENA de elasticidad: prob. de convertir un quiebre del Combine en pase (p_up) o un pase en quiebre (p_dn); NO es una estrategia


def xfa_cap_micros(xb, restricted=True):
    if not restricted: return np.full(xb.shape, 10 ** 6)
    return np.where(xb < 1500.0, 12, np.where(xb < 2000.0, 18, 31))


def simulate(S: Spec, D: np.ndarray, lag=2, skip=None, start_mode=0, start=None):
    """D: (T,H) indices de dia en el eje comun. Devuelve dict (arreglos por trayectoria y por dia)."""
    T, H = D.shape
    fee = S.fee * S.fee_scale; act = S.act * S.fee_scale
    mode = np.full(T, start_mode, np.int8)
    cb = np.zeros(T); cfl = np.full(T, -S.mll); cbest = np.zeros(T); cdays = np.zeros(T, np.int64)
    xb = np.zeros(T); xfl = np.full(T, -S.xmll); xwd = np.zeros(T, np.int64); xref = np.zeros(T); xbest = np.zeros(T); xdays = np.zeros(T, np.int64)
    first_pay = np.ones(T, bool); paid_gross = np.zeros(T)
    cash = np.zeros(T); n_att = np.zeros(T, np.int64); wait = np.zeros(T, np.int64)
    take_d = np.zeros((T, H), np.float32); fee_d = np.zeros((T, H), np.float32); blow_d = np.zeros((T, H), bool)
    cum = np.zeros((T, H), np.float32)
    n_b0 = np.zeros(T, np.int64); n_b1 = np.zeros(T, np.int64); n_pay = np.zeros(T, np.int64); n_pass = np.zeros(T, np.int64)
    n_trades_c = np.zeros(T, np.int64); n_trades_cmax = np.zeros(T, np.int64); n_trades_c80 = np.zeros(T, np.int64)
    n_xtrades = np.zeros(T, np.int64); n_xmax = np.zeros(T, np.int64)
    pass_day = np.zeros(T, np.int64); stopped = np.zeros(T, bool)
    fee_c_tot = np.zeros(T); fee_a_tot = np.zeros(T)
    if start is not None:
        start = np.asarray(start); mode[:] = 4                         # 4 = inactiva hasta su dia de arranque (start[t]; >=H = nunca)
    elif start_mode == 0: cash -= fee; n_att += 1; fee_d[:, 0] += fee; fee_c_tot += fee
    mode_d = np.zeros((T, H), np.int8)
    unit = S.nc * S.tv
    rng = np.random.default_rng(S.seed)
    for day in range(H):
        lg = int(lag[day]) if hasattr(lag, '__len__') else lag
        sk = bool(skip[day]) if skip is not None else False
        idx = D[:, day]
        fee_today = np.zeros(T)
        if start is not None:
            st = (mode == 4) & (start <= day)
            if st.any():
                mode = np.where(st, start_mode, mode).astype(np.int8); fee_today += np.where(st, fee, 0.0); n_att = n_att + st; fee_c_tot += np.where(st, fee, 0.0)
        m0 = mode == 0; m1 = mode == 1
        # ---------------- Combine
        dist = cb - cfl
        dist_eff = dist if S.dll is None else np.minimum(dist, S.dll - S.comm * S.nc)
        kliq = np.ceil(dist_eff / unit - 1e-9); kmll = np.ceil(dist / unit - 1e-9)
        k = np.clip(np.minimum(S.sl, kliq), 1, S.kmax).astype(int)
        e = S.entry_slip
        ab = S.adv[idx, np.maximum(k - e, 1)] if e else S.adv[idx, k]; tb = S.tpt[idx, S.tp_ticks + S.tp_fill_extra + e]
        tp_hit = tb < ab; sl_hit = ~tp_hit & (ab < INF)
        loss_ticks = k.astype(float)
        if S.slip > 0 and not S.legacy and S.amag is not None:
            loss_ticks = np.where(k < kmll, k + S.slip * (S.amag[idx, k] - k), k)      # solo si el stop es propio o del DLL (no es liquidacion del MLL)
        pnl = np.where(tp_hit, S.tp_ticks * unit, np.where(sl_hit, -loss_ticks * unit, (S.flat[idx] - e) * unit)) - S.comm * S.nc
        pnl = np.where(m0, pnl, 0.0)
        if sk: pnl = np.zeros(T)
        trade0 = m0 & (not sk)
        n_trades_c += trade0
        n_trades_cmax += trade0 & (S.nc >= S.cap_micros)
        n_trades_c80 += trade0 & (S.nc >= 0.8 * S.cap_micros)
        cb = cb + pnl
        ratchet = m0 & (cb - S.mll > cfl)
        cfl = np.where(ratchet, np.minimum(cb - S.mll, 0.0), cfl)
        blown0 = m0 & (cb <= cfl)
        alive0 = m0 & ~blown0
        cdays = cdays + m0
        cbest = np.where(alive0 & (pnl > cbest), pnl, cbest)
        need = np.maximum(S.target, cbest / S.cons)
        passed = alive0 & (cb >= need) & (cdays >= S.min_days)
        if S.p_up > 0 or S.p_dn > 0:
            u = rng.random(T); up = blown0 & (u < S.p_up); dn = passed & (u < S.p_dn)
            blown0 = (blown0 & ~up) | dn; passed = (passed & ~dn) | up; alive0 = m0 & ~blown0
        renew = alive0 & ~passed & (cdays % DAYS_PER_MONTH == 0)
        fee_c_today = np.where(renew, fee, 0.0)
        # ---------------- XFA
        nc_t = np.minimum(S.nc_x, xfa_cap_micros(xb, S.mgc_restricted)) if not S.legacy else np.full(T, S.nc_x)
        if S.x_rho is not None and not S.legacy: nc_t = np.minimum(nc_t, np.maximum(np.floor(S.x_rho * (xb - xfl) / S.x_unit), 1)).astype(int)
        if S.xliq and not S.legacy:
            unit_x = nc_t * S.x_tv
            dist_x = xb - xfl
            if S.xdll is not None: dist_xe = np.minimum(dist_x, S.xdll - S.x_comm * nc_t)
            else: dist_xe = dist_x
            kx_liq = np.ceil(dist_xe / unit_x - 1e-9); kx_mll = np.ceil(dist_x / unit_x - 1e-9)
            kx = np.clip(np.minimum(S.x_sl, kx_liq), 1, S.xkmax).astype(int)
            abx = S.xadv[idx, np.maximum(kx - e, 1)] if e else S.xadv[idx, kx]; tbx = S.xtpt[idx, S.x_tp + S.tp_fill_extra + e]
            tphx = tbx < abx; slhx = ~tphx & (abx < INF)
            lossx = np.where(kx < kx_mll, kx + S.slip * (S.xamag[idx, kx] - kx), kx) if S.slip > 0 else kx.astype(float)
            p1 = np.where(m1, np.where(tphx, S.x_tp * unit_x, np.where(slhx, -lossx * unit_x, (S.xflat[idx] - e) * unit_x)) - S.x_comm * nc_t, 0.0)
        else:
            ser = S.xser[idx]
            p1 = np.where(m1, nc_t * ser, 0.0)
        if sk: p1 = np.zeros(T)
        xtr = m1 & (not sk)
        n_xtrades += xtr; n_xmax += xtr & (nc_t >= xfa_cap_micros(xb, S.mgc_restricted))
        xb = xb + p1
        cand = xb - S.xmll
        xfl = np.where(m1 & (cand > xfl), np.minimum(cand, 0.0), xfl)
        blown1 = m1 & (xb <= xfl)
        still = m1 & ~blown1
        xdays = xdays + still
        xbest = np.where(still & (p1 > xbest), p1, xbest)
        xwd = np.where(still & (p1 >= S.win_usd), xwd + 1, xwd)
        prof = xb - xref
        if S.path == "std":
            elig = still & (xwd >= S.win_days)
        else:
            elig = still & (xdays >= S.cons_days) & (prof > 0) & (xbest <= S.cons_x * np.maximum(prof, 1e-9))
        if S.legacy: elig = elig & (xb > 0)
        else:
            if S.profit_rule: elig = elig & (first_pay | (prof > 0.01))
            elig = elig & (xb >= S.pay_thr) & (xb > 0)
        take = np.zeros(T)
        if elig.any():
            g = np.minimum(xb * S.pct, S.cap)
            if not S.legacy: elig = elig & (g >= S.minpay)
            g = np.where(elig, g, 0.0)
            r100 = np.maximum(S.first100 - paid_gross, 0.0)
            tk = np.where(elig, np.minimum(g, r100) + (g - np.minimum(g, r100)) * S.split, 0.0)
            xb = xb - g
            xfl = np.where(elig, 0.0, xfl)
            xwd = np.where(elig, 0, xwd); xref = np.where(elig, xb, xref); xbest = np.where(elig, 0.0, xbest); xdays = np.where(elig, 0, xdays)
            first_pay = first_pay & ~elig; paid_gross = paid_gross + g
            take = tk * S.pay_scale
            n_pay = n_pay + elig
        # ---------------- politica de compra
        blow_any = blown0 | blown1
        blow_d[:, day] = blow_any
        can_buy = np.ones(T, bool)
        if S.K is not None: can_buy &= n_att < S.K
        if S.stop_loss is not None: can_buy &= cash > -S.stop_loss
        if S.lock_gain is not None: can_buy &= cash < S.lock_gain
        buy = blow_any & can_buy
        stopped |= blow_any & ~can_buy
        fee_today += fee_c_today
        fee_c_today = fee_c_today + np.where(buy, fee, 0.0); fee_today += np.where(buy, fee, 0.0)
        fee_a_today = np.where(passed, act, 0.0); fee_today += fee_a_today
        n_att = n_att + buy; n_pass = n_pass + passed; n_b0 += blown0; n_b1 += blown1
        fee_c_tot += fee_c_today; fee_a_tot += fee_a_today
        reset_c = buy
        cb = np.where(reset_c | blown0 & ~can_buy, 0.0, cb); cfl = np.where(reset_c, -S.mll, cfl)
        cbest = np.where(reset_c, 0.0, cbest); cdays = np.where(reset_c, 0, cdays)
        xb = np.where(passed, 0.0, xb); xfl = np.where(passed, -S.xmll, xfl); xwd = np.where(passed, 0, xwd)
        xref = np.where(passed, 0.0, xref); xbest = np.where(passed, 0.0, xbest); xdays = np.where(passed, 0, xdays); first_pay = np.where(passed, True, first_pay)
        m3 = mode == 3
        wait = np.where(m3, wait - 1, wait); wait = np.where(passed, lg, wait)
        mode = np.where(passed, 1 if lg == 0 else 3, np.where(reset_c, 0, mode)).astype(np.int8)
        mode = np.where(blow_any & ~can_buy, 2, mode).astype(np.int8)
        pass_day = np.where((pass_day == 0) & passed, day + 1, pass_day)
        mode = np.where(m3 & (wait <= 0), 1, mode).astype(np.int8)
        cash = cash + take - fee_today
        mode_d[:, day] = mode
        take_d[:, day] = take; fee_d[:, day] += fee_today
        cum[:, day] = cash
    return dict(take_d=take_d, fee_d=fee_d, cum=cum, blow_d=blow_d, n_att=n_att, n_b0=n_b0, n_b1=n_b1, n_pay=n_pay, n_pass=n_pass, pass_day=pass_day, stopped=stopped,
                fee_c=fee_c_tot, fee_a=fee_a_tot, n_trades_c=n_trades_c, n_trades_cmax=n_trades_cmax, n_trades_c80=n_trades_c80, n_xtrades=n_xtrades, n_xmax=n_xmax, mode_end=mode, mode_d=mode_d)
