"""
Motor de flujo de caja Evaluacion -> Fondeada -> (quiebre) -> nueva Evaluacion, por firma, sobre barras REALES de MES (tablas first-touch de
scripts/g2_real_rules_scan.py, 515 dias, bootstrap de dias). SANDBOX / R&D: 100% offline, sin credenciales, no importa nada de scheduler/ ni de Pi.

Firmas modeladas (reglas verificadas en fuente propia el 05-oct-2026; ver GLITCH_RESEARCH_LOG.md, secciones del 05-oct):
  * Topstep 50K Combine + XFA estandar (control; las reglas XFA vienen del log del 24/25-sep, tiers de escalado NO verificados),
  * Tradeify Growth 50K (evaluacion sin consistencia; fondeada: 35% consistencia, balance minimo $3,000, topes por pago 1500/2000/2500/3000),
  * Tradeify Select 50K: evaluacion (40% cons., min 3 dias, sin DLL) + fondeada Flex (5 dias ganadores, 50% de la ganancia, tope $2,500, sin DLL)
    o Daily (buffer $2,100, 2x ganancia del ciclo, tope $1,250, DLL $1,000),
  * Bulenox Opcion 2 50K Qualification (escalado 20/40/70, DLL $1,100, ventana de 21 dias de trading) + Master (10 dias, reserva $2,600,
    consistencia 40%, tope $1,500 en los 3 primeros pagos, 100% de los primeros $10,000).
Politica de EVALUACION: "TP dimensionado al target restante, stop propio" (scripts/pass_rate_bold_real.py). Politica de FONDEADA (misma familia en todas las firmas
para comparar): un bracket diario con TP bruto G_f dolares (nc = G_f/(tp_ticks*1.25) acotado por el tope de contratos) y stop = rho * distancia al piso (rho=1: el piso).
Supuestos declarados: el trailing se actualiza al cierre del dia y se vigila en tiempo real (aqui: el stop es la distancia al piso); un dia siempre se opera; ciclo de pago =
desde el ultimo pago; consistencia de Growth medida sobre el ciclo; no se modela la demora de procesamiento de pagos ni la revision humana. Una sola historia de 515 dias.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
from numba import njit
from scripts.g2_real_rules_scan import TV, KMAX, TMAX, INF

# ---- indices de los vectores de parametros
(E_DD, E_LOCK, E_T, E_CONS, E_MIND, E_DLL, E_CAPT, E_CAPF, E_COMM, E_GCAP, E_TP, E_FEE, E_RESET, E_WIN, E_ACT, E_RENEW,
 E_RESETCAP, E_RESETS_ACCESS, E_DIRECT, E_G2) = range(20)
F_DD, F_LOCK, F_DLL, F_CAPT, F_CAPF, F_COMM, F_G, F_RHO, F_TP = range(9)
(P_WINTHR, P_CAP1, P_CAP2, P_CAP3, P_CAP4, P_SPLIT, P_MINPAY, P_CONS, P_REQD, P_BAL, P_PCT, P_MULT, P_FIRST100) = range(13)
K_TOPSTEP, K_FLEX, K_DAILY, K_GROWTH, K_BULENOX, K_MOMENTUM, K_FT = range(7)
DAYS_PER_MONTH = 21


@njit(cache=True)
def cap_nc(captype, capfixed, bal, peak):
    if captype == 0:
        return int(capfixed)
    if captype == 1:                      # Bulenox: por efectivo disponible (saldo - saldo inicial), sube y baja
        if bal <= 1500.0: return 20
        if bal <= 4000.0: return 40
        return 70
    if peak < 1500.0: return 20           # captype 2: Tradeify Select fondeada, escalado acumulativo por equity EOD maximo
    if peak < 2000.0: return 30
    return 40


@njit(cache=True)
def play_day(adv, tpt, flat, di, G, dist, dll, rho_full, rho, cap, comm, tp_ticks):
    nc = int(np.rint(G / (tp_ticks * TV)))
    if nc < 1: nc = 1
    if nc > cap: nc = cap
    unit = nc * TV
    tpk = int(np.ceil((G + comm * nc) / unit - 1e-9))
    if tpk < 1: tpk = 1
    if tpk > TMAX: tpk = TMAX
    if rho_full:
        k = int(np.ceil(dist / unit - 1e-9))
    else:
        k = int(np.floor(rho * dist / unit))
    if k < 1: k = 1
    if k > KMAX: k = KMAX
    if dll > 0.0 and dist > dll:
        kd = int(np.floor((dll - comm * nc) / unit))
        if kd < 1: kd = 1
        if kd < k: k = kd
    ab = adv[di, k]; tb = tpt[di, tpk]
    if tb < ab:
        pnl = tpk * unit
    elif ab < INF:
        pnl = -k * unit
    else:
        pnl = flat[di] * unit
    return pnl - comm * nc


@njit(cache=True)
def play_fixed(adv, tpt, flat, di, nc, tp, sl, dist, dll, comm):
    """G2 tal cual (nc fijo, TP/SL nominales en ticks); la liquidacion del piso y el DLL de la plataforma recortan el SL, como en g2_real_rules_scan.simulate."""
    unit = nc * TV
    k = sl
    kd = int(np.ceil(dist / unit - 1e-9))
    if kd < k: k = kd
    if dll > 0.0 and dist > dll:
        kl = int(np.ceil(dll / unit - 1e-9))
        if kl < k: k = kl
    if k < 1: k = 1
    ab = adv[di, k]; tb = tpt[di, tp]
    if tb < ab:
        pnl = tp * unit
    elif ab < INF:
        pnl = -k * unit
    else:
        pnl = flat[di] * unit
    return pnl - comm * nc


@njit(cache=True)
def sim_path(adv, tpt, flat, idx, H, E, F, PF, fkind, seed):
    np.random.seed(seed)
    M = H // DAYS_PER_MONTH
    pay = np.zeros(M); fee = np.zeros(M)
    n_eval = 1; n_funded = 0; n_pay = 0; first_pay = -1; n_resets = 0; max_resets_win = 0
    out = np.zeros(8)
    first_res = 0                                              # 1 = primera evaluacion pasada, 2 = primera evaluacion quebrada
    maxtake = 0.0; gross_total = 0.0
    nidx = len(idx)
    mo0 = 0
    fee[0] += E[E_FEE]
    # estado de evaluacion
    mode = 0
    b = 0.0; fl = -E[E_DD]; best = 0.0; edays = 0; access = 0; rw = 0; rused = 0
    # estado fondeada
    fb = 0.0; ff = 0.0; peak = 0.0; ref = 0.0; win_days = 0; fdays = 0; pay_n = 0; paid_gross = 0.0; best_c = 0.0
    if E[E_DIRECT] > 0.0:                                  # Fast Track: sin evaluacion
        mode = 1; n_funded = 1; ff = -F[F_DD]
    for day in range(H):
        mo = day // DAYS_PER_MONTH
        if mo >= M: mo = M - 1
        di = idx[np.random.randint(0, nidx)]
        if mode == 0:
            # ventana de acceso (Bulenox) y renovacion mensual (Topstep)
            if E[E_WIN] > 0.0 and access >= E[E_WIN]:
                fee[mo] += E[E_FEE]; n_eval += 1
                b = 0.0; fl = -E[E_DD]; best = 0.0; edays = 0; access = 0; rused = 0; rw = 0
            if E[E_RENEW] > 0.0 and access > 0 and access % DAYS_PER_MONTH == 0:
                fee[mo] += E[E_RENEW]
            access += 1; edays += 1
            if E[E_CONS] > 0.0:
                need_tot = max(E[E_T], best / E[E_CONS])
            else:
                need_tot = E[E_T]
            R = max(need_tot - b, 1.0)
            G = min(R, E[E_GCAP])
            cap = cap_nc(int(E[E_CAPT]), E[E_CAPF], b, b)
            if E[E_G2] > 0.0:
                ncg = 40 if cap > 40 else cap
                pnl = play_fixed(adv, tpt, flat, di, ncg, int(E[E_TP]), 100, b - fl, E[E_DLL], E[E_COMM])
            else:
                pnl = play_day(adv, tpt, flat, di, G, b - fl, E[E_DLL], True, 1.0, cap, E[E_COMM], E[E_TP])
            b += pnl
            if b <= fl:                                   # quiebre
                if first_res == 0: first_res = 2
                n_resets += 1
                rw += 1
                if E[E_RESETCAP] > 0.0:
                    if rw > 0 and (day % DAYS_PER_MONTH) == 0:
                        rused = 0
                    rused += 1
                    if rused > E[E_RESETCAP]:
                        fee[mo] += E[E_FEE]; n_eval += 1; rused = 0
                    else:
                        fee[mo] += E[E_RESET]
                else:
                    fee[mo] += E[E_RESET]
                if E[E_RESETS_ACCESS] > 0.0:
                    access = 0
                b = 0.0; fl = -E[E_DD]; best = 0.0; edays = 0
                continue
            if b - E[E_DD] > fl:
                fl = min(b - E[E_DD], E[E_LOCK])
            if pnl > best: best = pnl
            if E[E_CONS] > 0.0:
                need = max(E[E_T], best / E[E_CONS])
            else:
                need = E[E_T]
            if b >= need and edays >= int(E[E_MIND]):
                if first_res == 0: first_res = 1
                fee[mo] += E[E_ACT]
                mode = 1; n_funded += 1
                fb = 0.0; ff = -F[F_DD]; peak = 0.0; ref = 0.0; win_days = 0; fdays = 0; pay_n = 0; paid_gross = 0.0; best_c = 0.0
        else:
            dll = F[F_DLL]
            if fkind == K_BULENOX and ff >= F[F_LOCK] - 1e-9:
                dll = 0.0
            if fkind == K_GROWTH and fb >= 3000.0:
                dll = 2000.0
            cap = cap_nc(int(F[F_CAPT]), F[F_CAPF], fb, peak)
            dist = fb - ff
            full = F[F_RHO] >= 0.999
            pnl = play_day(adv, tpt, flat, di, F[F_G], dist, dll, full, F[F_RHO], cap, F[F_COMM], F[F_TP])
            fb += pnl
            if fb <= ff:                                  # fondeada terminada -> nueva evaluacion (o recompra directa en Fast Track)
                fee[mo] += E[E_FEE]; n_eval += 1
                if E[E_DIRECT] > 0.0:
                    fb = 0.0; ff = -F[F_DD]; peak = 0.0; ref = 0.0; win_days = 0; fdays = 0; pay_n = 0; best_c = 0.0
                    n_funded += 1
                else:
                    mode = 0
                    b = 0.0; fl = -E[E_DD]; best = 0.0; edays = 0; access = 0; rused = 0; rw = 0
                continue
            if fb > peak: peak = fb
            if fb - F[F_DD] > ff:
                ff = min(fb - F[F_DD], F[F_LOCK])
            fdays += 1
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
                    avail = fb - PF[P_BAL]
                    g = min(PF[P_MULT] * cyc, PF[P_CAP1], avail)
                    if g < PF[P_MINPAY]: g = 0.0
            elif fkind == K_FT:
                if pay_n == 0:
                    okc = fb >= PF[P_BAL] and cyc > 0.0 and best_c <= 0.20 * cyc
                    room = fb - (ff + 1.0)
                else:
                    consk = 0.25 if pay_n == 1 else 0.30
                    okc = cyc >= PF[P_REQD] and best_c <= consk * cyc
                    room = fb - (ref + PF[P_REQD])
                if okc:
                    cp = PF[P_CAP1] if pay_n < 3 else PF[P_CAP4]
                    g = min(cp, room)
                    if g < PF[P_MINPAY]: g = 0.0
            elif fkind == K_GROWTH or fkind == K_MOMENTUM:
                if win_days >= 5 and fb >= PF[P_BAL] and cyc > 0.0 and best_c <= PF[P_CONS] * cyc:
                    cp = PF[P_CAP1] if pay_n == 0 else (PF[P_CAP2] if pay_n == 1 else (PF[P_CAP3] if pay_n == 2 else PF[P_CAP4]))
                    g = min(cp, fb)
                    if g < PF[P_MINPAY]: g = 0.0
            else:
                if fdays >= int(PF[P_REQD]) and fb - PF[P_BAL] >= PF[P_MINPAY] and cyc > 0.0 and best_c <= PF[P_CONS] * cyc:
                    cp = PF[P_CAP1] if pay_n < 3 else 1e12
                    g = min(fb - PF[P_BAL], cp)
                    if g < PF[P_MINPAY]: g = 0.0
            if g > 0.0:
                if PF[P_FIRST100] > 0.0:
                    r100 = max(PF[P_FIRST100] - paid_gross, 0.0)
                    take = min(g, r100) + (g - min(g, r100)) * PF[P_SPLIT]
                else:
                    take = g * PF[P_SPLIT]
                paid_gross += g
                fb -= g; ref = fb; win_days = 0; fdays = 0; pay_n += 1; n_pay += 1
                if fkind != K_BULENOX: best_c = 0.0   # Bulenox Master: el mejor dia no se reinicia
                pay[mo] += take
                if take > maxtake: maxtake = take
                gross_total += g
                if first_pay < 0: first_pay = day
                if fkind == K_TOPSTEP:
                    ff = 0.0                                  # tras un pago el piso del MLL pasa a $0
                elif fkind in (K_FLEX, K_DAILY):
                    ff = max(ff, F[F_LOCK])                  # el piso se fija en saldo inicial + $100 al solicitar pago
    out[0] = n_eval; out[1] = n_funded; out[2] = n_pay; out[3] = first_pay; out[4] = n_resets; out[5] = first_res; out[6] = maxtake; out[7] = gross_total
    return pay, fee, out


@njit(cache=True)
def sim_many(adv, tpt, flat, idx, H, E, F, PF, fkind, n_paths, seed0):
    M = H // DAYS_PER_MONTH
    pay = np.zeros((n_paths, M)); fee = np.zeros((n_paths, M)); out = np.zeros((n_paths, 8))
    for p in range(n_paths):
        a, b, c = sim_path(adv, tpt, flat, idx, H, E, F, PF, fkind, seed0 + p)
        pay[p, :] = a; fee[p, :] = b; out[p, :] = c
    return pay, fee, out


def vec(names_vals, size):
    v = np.zeros(size)
    for k, x in names_vals.items(): v[k] = x
    return v


def firm_specs(g_f=300.0, rho=0.5, tp_f=40, eval_tp=40, eval_gfrac=1.0, g2=False):
    """Devuelve {nombre: (E, F, PF, kind)}; los parametros de politica de evaluacion son los mejores hallados en pass_rate_firms_verified.py."""
    S = {}
    T = 3000.0
    # Topstep 50K (control)
    E = vec({E_DD: 2000, E_LOCK: 0, E_T: T, E_CONS: 0.55, E_MIND: 2, E_DLL: 0, E_CAPT: 0, E_CAPF: 40, E_COMM: 1.22, E_GCAP: 0.55 * T, E_TP: 30,
             E_FEE: 49, E_RESET: 49, E_WIN: 0, E_ACT: 149, E_RENEW: 49, E_RESETCAP: 0, E_RESETS_ACCESS: 1}, 20)
    F = vec({F_DD: 2000, F_LOCK: 0, F_DLL: 0, F_CAPT: 2, F_CAPF: 0, F_COMM: 1.22, F_G: g_f, F_RHO: rho, F_TP: tp_f}, 9)
    PF = vec({P_WINTHR: 150, P_CAP1: 2000, P_SPLIT: 0.9, P_MINPAY: 0, P_PCT: 0.5}, 13)
    S["Topstep 50K (control; escalado XFA supuesto 20/30/40)"] = (E, F, PF, K_TOPSTEP)
    # Tradeify Growth
    E = vec({E_DD: 2000, E_LOCK: 100, E_T: T, E_CONS: 0, E_MIND: 1, E_DLL: 1250, E_CAPT: 0, E_CAPF: 40, E_COMM: 1.82, E_GCAP: eval_gfrac * T, E_TP: eval_tp,
             E_FEE: 145, E_RESET: 95, E_WIN: 0, E_ACT: 0, E_RENEW: 0, E_RESETCAP: 0, E_RESETS_ACCESS: 0}, 20)
    F = vec({F_DD: 2000, F_LOCK: 100, F_DLL: 1250, F_CAPT: 0, F_CAPF: 40, F_COMM: 1.82, F_G: g_f, F_RHO: rho, F_TP: tp_f}, 9)
    PF = vec({P_WINTHR: 150, P_CAP1: 1500, P_CAP2: 2000, P_CAP3: 2500, P_CAP4: 3000, P_SPLIT: 0.9, P_MINPAY: 500, P_CONS: 0.35, P_BAL: 3000}, 13)
    S["Tradeify Growth 50K"] = (E, F, PF, K_GROWTH)
    # Tradeify Select (evaluacion comun) + Flex / Daily
    Es = vec({E_DD: 2000, E_LOCK: 100, E_T: T, E_CONS: 0.40, E_MIND: 3, E_DLL: 0, E_CAPT: 0, E_CAPF: 40, E_COMM: 1.82, E_GCAP: 0.30 * T, E_TP: 30,
              E_FEE: 165, E_RESET: 109, E_WIN: 0, E_ACT: 0, E_RENEW: 0, E_RESETCAP: 10, E_RESETS_ACCESS: 0}, 20)
    F = vec({F_DD: 2000, F_LOCK: 100, F_DLL: 0, F_CAPT: 2, F_CAPF: 0, F_COMM: 1.82, F_G: g_f, F_RHO: rho, F_TP: tp_f}, 9)
    PF = vec({P_WINTHR: 150, P_CAP1: 2500, P_SPLIT: 0.9, P_MINPAY: 250, P_PCT: 0.5}, 13)
    S["Tradeify Select Flex 50K"] = (Es, F, PF, K_FLEX)
    F = vec({F_DD: 2000, F_LOCK: 100, F_DLL: 1000, F_CAPT: 2, F_CAPF: 0, F_COMM: 1.82, F_G: g_f, F_RHO: rho, F_TP: tp_f}, 9)
    PF = vec({P_WINTHR: 150, P_CAP1: 1250, P_SPLIT: 0.9, P_MINPAY: 250, P_BAL: 2100, P_MULT: 2}, 13)
    S["Tradeify Select Daily 50K"] = (Es.copy(), F, PF, K_DAILY)
    # Bulenox Opcion 2 50K
    E = vec({E_DD: 2500, E_LOCK: 100, E_T: T, E_CONS: 0, E_MIND: 1, E_DLL: 1100, E_CAPT: 1, E_CAPF: 0, E_COMM: 1.22, E_GCAP: eval_gfrac * T, E_TP: 100,
             E_FEE: 175, E_RESET: 78, E_WIN: 21, E_ACT: 148, E_RENEW: 0, E_RESETCAP: 0, E_RESETS_ACCESS: 0}, 20)
    F = vec({F_DD: 2500, F_LOCK: 100, F_DLL: 1100, F_CAPT: 1, F_CAPF: 0, F_COMM: 1.22, F_G: g_f, F_RHO: rho, F_TP: tp_f}, 9)
    PF = vec({P_WINTHR: 150, P_CAP1: 1500, P_SPLIT: 0.9, P_MINPAY: 1000, P_CONS: 0.40, P_REQD: 10, P_BAL: 2600, P_FIRST100: 10000}, 13)
    S["Bulenox Qualification Opcion 2 50K + Master"] = (E, F, PF, K_BULENOX)
    # Bulenox Momentum (Opcion 2, 50K): un pago de $143 cubre calificacion + Master gratis; 40 micros fijos; DD $2,250; DLL $1,200 (se asume permanente);
    # sin resets documentados en la pagina de Momentum -> se asume recompra a $143
    E = vec({E_DD: 2250, E_LOCK: 100, E_T: T, E_CONS: 0, E_MIND: 1, E_DLL: 1200, E_CAPT: 0, E_CAPF: 40, E_COMM: 1.22, E_GCAP: eval_gfrac * T, E_TP: 100,
             E_FEE: 143, E_RESET: 143, E_WIN: 21, E_ACT: 0, E_RENEW: 0, E_RESETCAP: 0, E_RESETS_ACCESS: 1}, 20)
    F = vec({F_DD: 2250, F_LOCK: 100, F_DLL: 1200, F_CAPT: 0, F_CAPF: 40, F_COMM: 1.22, F_G: g_f, F_RHO: rho, F_TP: tp_f}, 9)
    PF = vec({P_WINTHR: 150, P_CAP1: 1500, P_CAP2: 2000, P_CAP3: 2500, P_CAP4: 3000, P_SPLIT: 0.9, P_MINPAY: 1000, P_CONS: 0.35, P_BAL: 3000, P_FIRST100: 10000}, 13)
    S["Bulenox Momentum 50K (Opcion 2)"] = (E, F, PF, K_MOMENTUM)
    # Bulenox Fast Track (Opcion 2, 50K): $488 pago unico, fondeada desde el dia 1, sin evaluacion
    E = vec({E_DD: 2250, E_LOCK: 100, E_T: T, E_FEE: 488, E_RESET: 488, E_DIRECT: 1, E_COMM: 1.22}, 20)
    F = vec({F_DD: 2250, F_LOCK: 100, F_DLL: 1200, F_CAPT: 0, F_CAPF: 40, F_COMM: 1.22, F_G: g_f, F_RHO: rho, F_TP: tp_f}, 9)
    PF = vec({P_WINTHR: 150, P_CAP1: 2000, P_CAP4: 2500, P_SPLIT: 0.9, P_MINPAY: 1000, P_BAL: 3000, P_REQD: 2000, P_FIRST100: 10000}, 13)
    S["Bulenox Fast Track 50K (Opcion 2)"] = (E, F, PF, K_FT)
    if g2:                                   # evaluacion con G2 tal cual (nc=40, TP 40, SL 100 nominal); misma fondeada
        for k, (E, F, PF, kind) in list(S.items()):
            if kind != K_FT:
                E = E.copy(); E[E_G2] = 1.0; E[E_TP] = 40.0
                S[k] = (E, F, PF, kind)
    return S


OPS_MONTHLY = {"Topstep": 43.5 + 1.5 + 14.5, "Bulenox": 43.5 + 1.5 + 100.0, "Tradeify": 43.5 + 1.5}   # Massive + Pi + API (Tradeify: API de eval sin verificar -> $0)


def run_firm(tables, name, spec, n_paths=20000, H=252, seed0=1000, idx=None):
    adv, tpt, flat = tables
    E, F, PF, kind = spec
    idx = np.arange(len(adv)) if idx is None else idx
    return sim_many(adv, tpt, flat, idx.astype(np.int64), H, E, F, PF, kind, n_paths, seed0)


def summarize(name, pay, fee, out, ops=0.0):
    net = pay - fee - ops
    cum = np.cumsum(net, axis=1)
    run_min = np.minimum.accumulate(cum, axis=1)
    cushion = -np.minimum(run_min[:, -1], 0.0)                       # capital maximo hundido en algun momento de los 12 meses (por trayectoria)
    med = np.median(cum, axis=0)
    be = int(np.argmax(med >= 0)) + 1 if (med >= 0).any() else 0     # primer mes con acumulado MEDIANO >= 0
    p_end = (out[:, 3] >= 0)
    return dict(name=name, net_mes_medio=float(net[:, 2:].mean()), net_mes_mediano=float(np.median(net[:, 2:])),
                payout_anual_p50=float(np.percentile(pay.sum(1), 50)), payout_anual_medio=float(pay.sum(1).mean()), fees_anual=float(fee.sum(1).mean()),
                ops_anual=float(ops * pay.shape[1]),
                acum12_p10=float(np.percentile(cum[:, -1], 10)), acum12_p50=float(np.percentile(cum[:, -1], 50)),
                acum12_p90=float(np.percentile(cum[:, -1], 90)), acum12_medio=float(cum[:, -1].mean()), p_neg=float((cum[:, -1] < 0).mean()),
                colchon_p90=float(np.percentile(cushion, 90)), colchon_p95=float(np.percentile(cushion, 95)), colchon_p99=float(np.percentile(cushion, 99)),
                mes_equilibrio_mediana=be, net_mensual_p10=np.percentile(net, 10, axis=0), net_mensual_p50=np.percentile(net, 50, axis=0),
                net_mensual_p90=np.percentile(net, 90, axis=0), net_mensual_medio=net.mean(axis=0),
                evals=float(out[:, 0].mean()), fondeadas=float(out[:, 1].mean()), pagos=float(out[:, 2].mean()),
                p_pago=float(p_end.mean()), dia_primer_pago_p50=float(np.median(out[p_end, 3])) if p_end.any() else float("nan"),
                resets=float(out[:, 4].mean()), pass_primera=float((out[:, 5] == 1).sum() / max((out[:, 5] > 0).sum(), 1)),
                max_pago_neto=float(out[:, 6].max()), pago_bruto_medio=float(out[:, 7].mean()))
