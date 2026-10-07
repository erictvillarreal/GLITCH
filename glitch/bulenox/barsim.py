"""Simulador RAPIDO (numba) a nivel de barra de 5 min con las reglas de Bulenox (mismo orden de eventos que bulenox/account.py, validado contra el en tests/test_bulenox_barsim.py).
Una operacion por dia (bracket TP/SL), convencion de barra O-L-H-C si cierra >= cierre previo y O-H-L-C si no. Opcion 1: umbral = pico de equity (incl. no realizado) - DD en tiempo real;
Opcion 2: umbral EOD fijo en la jornada + DLL suave (se calcula con realizado + no realizado + comisiones). SANDBOX / R&D, offline."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
from numba import njit
from dd_wr.product_sweep import load_sessions
from strategies.geometry_pure import trading_day_index, decide_side
from bulenox.rules import COMMISSION_PER_SIDE

SPEC = {"MES": ("mes_5min_2y", 0.25, 1.25), "MNQ": ("mnq_5min_2y", 0.25, 0.50), "M2K": ("m2k_5min_2y", 0.10, 0.50), "MGC": ("mgc_5min_2y_corrected_window", 0.10, 1.00),
        "MCL": ("mcl_5min_2y", 0.01, 1.00), "M6E": ("m6e_5min_2y", 0.0001, 1.25)}
_S = {}


def build_bars(prod, entry_m, flat_m=14 * 60 + 30, side_mode="alternate"):
    stem, tick, tv = SPEC[prod]
    if prod not in _S: _S[prod] = load_sessions(stem)
    Hs, Ls, Cs, starts, ends, sides, dates = [], [], [], [], [], [], []
    off = 0
    for day, h, l, c, m in _S[prod]:
        a = np.nonzero(m >= entry_m)[0]
        if len(a) == 0: continue
        ep = int(a[0]); jf = next((j for j in range(ep + 1, len(c)) if m[j] >= flat_m), len(c) - 1)
        if jf <= ep: continue
        side = decide_side(trading_day_index(day), {"alternate": "alternate", "always_long": "always_long", "always_short": "always_short"}[side_mode])
        n = jf - ep + 1
        Hs.append(h[ep:jf + 1]); Ls.append(l[ep:jf + 1]); Cs.append(c[ep:jf + 1]); starts.append(off); ends.append(off + n - 1); sides.append(side); dates.append(str(day)); off += n
    return dict(H=np.concatenate(Hs), L=np.concatenate(Ls), C=np.concatenate(Cs), start=np.array(starts, dtype=np.int64), end=np.array(ends, dtype=np.int64),
                side=np.array(sides, dtype=np.int64), dates=dates, tick=tick, tv=tv, comm_side=COMMISSION_PER_SIDE[prod], prod=prod, entry_m=entry_m)


@njit(cache=True)
def day_bar(H, L, C, s, e, side, nc, tp_ticks, sl_ticks, tick, tv, comm_side, bal, thr, peak, dll, opt, dd, lock_cap, locked, slip=0.0, conserv=0):
    """Una operacion en un dia. Devuelve (balance_final, umbral, pico, breach(0/1), dll_hit(0/1), dia_pnl, locked)."""
    ent = C[s]
    unit = nc * tv / tick                       # $ por unidad de precio
    commc = comm_side * nc
    day_real = -commc; bal = bal - commc
    tp_px = ent + side * tp_ticks * tick; sl_px = ent - side * sl_ticks * tick
    breach = 0; hit = 0; closed = False
    for j in range(s + 1, e + 1):
        prev = C[j - 1]
        if conserv == 1:
            # orden CONSERVADOR: extremo adverso -> extremo favorable -> adverso otra vez (el pico ya subio): peor caso para el stop y para el drawdown dinamico
            if side == 1: xa = L[j]; xf = H[j]
            else: xa = H[j]; xf = L[j]
            x1 = xa; x2 = xf
            nq = 3
        else:
            if C[j] >= prev: x1 = L[j]; x2 = H[j]
            else: x1 = H[j]; x2 = L[j]
            nq = 2
        for q in range(nq):
            if conserv == 1:
                x = x1 if q != 1 else x2
            else:
                x = x1 if q == 0 else x2
            # nivel de bracket cruzado antes que la regla de cuenta
            lvl = x; kind = 0
            if (side == 1 and x <= sl_px) or (side == -1 and x >= sl_px):
                lvl = sl_px + slip * (x - sl_px); kind = 1                  # llenado del stop: slip=1 -> en el extremo de la barra (peor caso)
            elif (side == 1 and x >= tp_px) or (side == -1 and x <= tp_px): lvl = tp_px; kind = 2
            eq = bal + (lvl - ent) * side * unit
            if opt == 1 and not locked:
                if eq > peak:
                    peak = eq; t2 = peak - dd
                    if t2 > lock_cap: t2 = lock_cap
                    thr = t2
                    if lock_cap < 1e17 and peak - dd >= lock_cap: locked = True
            if eq <= thr:
                bal = eq - commc; day_real = day_real + (lvl - ent) * side * unit - commc; breach = 1; closed = True; break
            if dll > 0.0 and hit == 0:
                dp = day_real + (lvl - ent) * side * unit
                if dp <= -dll:
                    bal = bal + (lvl - ent) * side * unit - commc; day_real = dp - commc; hit = 1; closed = True; break
            if kind != 0:
                bal = bal + (lvl - ent) * side * unit - commc; day_real = day_real + (lvl - ent) * side * unit - commc; closed = True; break
        if closed: break
    if not closed:
        px = C[e]
        eq = bal + (px - ent) * side * unit
        # chequeo final al cierre
        if opt == 1 and not locked:
            if eq > peak:
                peak = eq; t2 = peak - dd
                if t2 > lock_cap: t2 = lock_cap
                thr = t2
        bal = eq - commc; day_real = day_real + (px - ent) * side * unit - commc
        if eq <= thr: breach = 1
    return bal, thr, peak, breach, hit, day_real, locked


@njit(cache=True)
def scale_cap(kind, bal, c0, c1, c2, c3, b1, b2, b3):
    if kind == 0: return c0
    if bal > b3: return c3
    if bal > b2: return c2
    if bal > b1: return c1
    return c0


@njit(cache=True)
def qual_attempt(H, L, C, start, end, side, idx, tick, tv, comm_side, opt, dd, dll, target, lock_cap, caps, breaks, cap_kind, tp_ticks, gfrac, max_days, seed, slip, conserv, cons, min_days):
    """Un intento de Qualification/Momentum con politica 'TP al target restante': G=min(R, gfrac*target), nc segun el tope, SL = distancia al umbral (liquidacion) limitada por el DLL.
    Devuelve (resultado: 1 pase, 2 quiebre, 3 tiempo agotado, dias usados, balance)."""
    np.random.seed(seed)
    bal = 0.0; thr = -dd; peak = 0.0; locked = False; maxc = 0.0; bestd = 0.0
    n = len(idx)
    for d in range(max_days):
        di = idx[np.random.randint(0, n)]
        s = start[di]; e = end[di]
        need = target
        if cons > 0.0 and bestd / cons > need: need = bestd / cons
        R = max(need - bal, 1.0); G = min(R, gfrac * target)
        cap = scale_cap(cap_kind, bal, caps[0], caps[1], caps[2], caps[3], breaks[0], breaks[1], breaks[2])
        nc = int(np.rint(G / (tp_ticks * tv)))
        if nc < 1: nc = 1
        if nc > cap: nc = cap
        unit = nc * tv
        tpk = int(np.ceil((G + 2 * comm_side * nc) / unit - 1e-9))
        if tpk < 1: tpk = 1
        dist = bal - thr
        k = int(np.ceil(dist / unit - 1e-9))
        if dll > 0.0 and dist > dll:
            kd = int(np.floor((dll - 2 * comm_side * nc) / unit))
            if kd < 1: kd = 1
            if kd < k: k = kd
        if k < 1: k = 1
        bal, thr, peak, br, hit, dpnl, locked = day_bar(H, L, C, s, e, side[di], nc, tpk, k, tick, tv, comm_side, bal, thr, peak, dll, opt, dd, lock_cap, locked, slip, conserv)
        if br == 1: return 2, d + 1, bal
        if opt == 2 and bal > maxc:
            maxc = bal; t2 = maxc - dd
            if t2 > lock_cap: t2 = lock_cap
            thr = t2
        if opt == 1:
            if bal > peak: peak = bal
        if dpnl > bestd: bestd = dpnl
        need = target
        if cons > 0.0 and bestd / cons > need: need = bestd / cons
        if bal >= need and d + 1 >= min_days: return 1, d + 1, bal
    return 3, max_days, bal


@njit(cache=True)
def qual_many(H, L, C, start, end, side, idx, tick, tv, comm_side, opt, dd, dll, target, lock_cap, caps, breaks, cap_kind, tp_ticks, gfrac, max_days, n, seed0, slip, conserv, cons, min_days):
    res = np.zeros((n, 3))
    for p in range(n):
        a, b, c = qual_attempt(H, L, C, start, end, side, idx, tick, tv, comm_side, opt, dd, dll, target, lock_cap, caps, breaks, cap_kind, tp_ticks, gfrac, max_days, seed0 + p, slip, conserv, cons, min_days)
        res[p, 0] = a; res[p, 1] = b; res[p, 2] = c
    return res


def run_qual(bars, plan, tp_ticks, gfrac, n=20000, seed0=1, idx=None, max_days=21, lock_cap=1e18, slip=0.0, conserv=1, cons=0.0, min_days=1):
    """plan: bulenox.rules.Plan (qualification/momentum, opcion 1 o 2)."""
    caps = np.zeros(4); br = np.zeros(3)
    for i, c in enumerate(plan.contracts): caps[i] = c * 10
    for i in range(len(caps)):
        if i >= len(plan.contracts): caps[i] = caps[len(plan.contracts) - 1]
    for i, b in enumerate(plan.scaling_breaks): br[i] = b
    for i in range(len(plan.scaling_breaks), 3): br[i] = 1e18
    idx = np.arange(len(bars["start"])) if idx is None else idx
    out = qual_many(bars["H"], bars["L"], bars["C"], bars["start"], bars["end"], bars["side"], idx.astype(np.int64), bars["tick"], bars["tv"], bars["comm_side"], plan.option, float(plan.drawdown),
                    float(plan.dll or 0.0), float(plan.target), lock_cap, caps, br, 0 if len(plan.contracts) == 1 else 1, tp_ticks, gfrac, max_days, n, seed0, float(slip), int(conserv), float(cons), int(min_days))
    return out   # columnas: resultado, dias, balance


# ----------------------------------------------------------------------------------------------------------------------------------------------------------
# Etapa FONDEADA: Master (Qualification Opcion 2, escalado, 10 dias, reserva, 40%), Momentum Master (5 dias rentables, 35%, saldo minimo) y Fast Track (objetivo de ciclo, 20/25/30%)
KIND_MASTER, KIND_MOMENTUM, KIND_FT, KIND_TOPSTEP = 0, 1, 2, 3


@njit(cache=True)
def funded_life(H, L, C, start, end, side, idx, tick, tv, comm_side, kind, opt, dd, dll_plan, caps_micro, breaks, cap_kind, lock_off, g_f, rho, tp_ticks,
                req, wmin, mbal, mincheck, pay_caps, cons, tgt1, tgt2, first100, split_after, days_req, horizon, seed, slip, conserv):
    """Una vida de cuenta fondeada. Devuelve (neto al trader, n pagos, dias de vida, dia del 1er pago (-1 si ninguno), murio(0/1))."""
    np.random.seed(seed)
    bal = 0.0; thr = -dd; peak = 0.0; locked = False; maxc = 0.0
    cyc_start = 0.0; cdays = 0; wdays = 0; cbest = 0.0; pay_n = 0; paid = 0.0; total = 0.0; first = -1; died = 0; life = horizon
    n = len(idx)
    for day in range(horizon):
        di = idx[np.random.randint(0, n)]
        s = start[di]; e = end[di]
        dll = dll_plan
        if kind == KIND_MASTER and locked: dll = 0.0                                   # [HC master] el DLL se elimina al fijarse el drawdown
        cap = scale_cap(cap_kind, bal, caps_micro[0], caps_micro[1], caps_micro[2], caps_micro[3], breaks[0], breaks[1], breaks[2])
        nc = int(np.rint(g_f / (tp_ticks * tv)))
        if nc < 1: nc = 1
        if nc > cap: nc = cap
        unit = nc * tv
        tpk = int(np.ceil((g_f + 2 * comm_side * nc) / unit - 1e-9))
        if tpk < 1: tpk = 1
        dist = bal - thr
        if rho >= 0.999: k = int(np.ceil(dist / unit - 1e-9))
        else: k = int(np.floor(rho * dist / unit))
        if dll > 0.0 and dist > dll:
            kd = int(np.floor((dll - 2 * comm_side * nc) / unit))
            if kd < 1: kd = 1
            if kd < k: k = kd
        if k < 1: k = 1
        bal, thr, peak, br, hit, dpnl, locked = day_bar(H, L, C, s, e, side[di], nc, tpk, k, tick, tv, comm_side, bal, thr, peak, dll, opt, dd, lock_off, locked, slip, conserv)
        if br == 1:
            died = 1; life = day + 1; break
        if opt == 2 and not locked:
            if bal > maxc:
                maxc = bal; t2 = maxc - dd
                if t2 > lock_off: t2 = lock_off
                thr = t2
                if maxc - dd >= lock_off: locked = True
        if opt == 1 and bal > peak: peak = bal
        cdays += 1
        if dpnl > cbest: cbest = dpnl
        if dpnl >= wmin: wdays += 1
        # ---- solicitud de pago
        cyc = bal - cyc_start; amt = 0.0
        ci = pay_n if pay_n < len(pay_caps) - 1 else len(pay_caps) - 1
        cap_pay = pay_caps[ci]
        consi = cons[pay_n if pay_n < len(cons) - 1 else len(cons) - 1]
        if kind == KIND_MASTER:
            if cdays >= days_req and cyc > 0.0 and cbest <= consi * cyc:
                room = bal - mbal
                amt = min(cap_pay, room)
        elif kind == KIND_MOMENTUM:
            if wdays >= days_req and bal >= mbal and cyc > 0.0 and cbest <= consi * cyc:
                amt = min(cap_pay, bal)
        elif kind == KIND_TOPSTEP:
            if wdays >= days_req and bal > 0.0:
                amt = min(cap_pay, 0.5 * bal)
        else:
            tgt = tgt1 if pay_n == 0 else tgt2
            if cyc >= tgt and cyc > 0.0 and cbest <= consi * cyc:
                room = (bal - (thr + 1.0)) if pay_n == 0 else (bal - (cyc_start + tgt))
                amt = min(cap_pay, room)
        if amt >= req and amt > 0.0:
            r100 = max(first100 - paid, 0.0)
            take = min(amt, r100) + (amt - min(amt, r100)) * split_after
            paid += amt; bal -= amt; total += take; pay_n += 1
            if first < 0: first = day
            cyc_start = bal; cdays = 0; wdays = 0
            if kind == KIND_TOPSTEP:
                thr = 0.0; locked = True                                  # tras un pago el piso del MLL pasa a $0 de forma permanente [help.topstep.com/8284233]
            if kind != KIND_MASTER: cbest = 0.0
    return total, pay_n, life, first, died


@njit(cache=True)
def funded_many(H, L, C, start, end, side, idx, tick, tv, comm_side, kind, opt, dd, dll_plan, caps_micro, breaks, cap_kind, lock_off, g_f, rho, tp_ticks,
                req, wmin, mbal, mincheck, pay_caps, cons, tgt1, tgt2, first100, split_after, days_req, horizon, n, seed0, slip, conserv):
    out = np.zeros((n, 5))
    for p in range(n):
        a, b, c, d, e2 = funded_life(H, L, C, start, end, side, idx, tick, tv, comm_side, kind, opt, dd, dll_plan, caps_micro, breaks, cap_kind, lock_off, g_f, rho, tp_ticks,
                                     req, wmin, mbal, mincheck, pay_caps, cons, tgt1, tgt2, first100, split_after, days_req, horizon, seed0 + p, slip, conserv)
        out[p, 0] = a; out[p, 1] = b; out[p, 2] = c; out[p, 3] = d; out[p, 4] = e2
    return out


def run_funded(bars, stage, size_plan, g_f, rho, tp_ticks, n=3000, seed0=1, idx=None, horizon=126, slip=0.0, conserv=1):
    """stage: 'master' (size_plan = plan Qualification Opcion 2), 'momentum_master' (plan momentum), 'fast_track' (plan fast_track). Devuelve dict de metricas."""
    from bulenox.rules import payout_rules
    if stage == "topstep_xfa":
        return run_funded_topstep(bars, g_f, rho, tp_ticks, n, seed0, idx, horizon, slip, conserv)
    kind = {"master": KIND_MASTER, "momentum_master": KIND_MOMENTUM, "fast_track": KIND_FT}[stage]
    pr = payout_rules(stage, size_plan.size)
    caps_m = np.zeros(4); br = np.zeros(3)
    for i, c in enumerate(size_plan.contracts): caps_m[i] = c * 10
    for i in range(len(size_plan.contracts), 4): caps_m[i] = caps_m[len(size_plan.contracts) - 1]
    for i, b in enumerate(size_plan.scaling_breaks): br[i] = b
    for i in range(len(size_plan.scaling_breaks), 3): br[i] = 1e18
    caps_pay = np.array([min(c, 1e12) for c in pr.caps], dtype=np.float64)
    cons = np.array(pr.consistency, dtype=np.float64)
    idx = np.arange(len(bars["start"])) if idx is None else idx
    o = funded_many(bars["H"], bars["L"], bars["C"], bars["start"], bars["end"], bars["side"], idx.astype(np.int64), bars["tick"], bars["tv"], bars["comm_side"], kind, size_plan.option,
                    float(size_plan.drawdown), float(size_plan.dll or 0.0), caps_m, br, 0 if len(size_plan.contracts) == 1 else 1, 100.0, g_f, rho, tp_ticks,
                    float(pr.min_request), float(pr.win_day_min if stage == "momentum_master" else 150.0), float(pr.min_balance), 0.0, caps_pay, cons, float(pr.first_cycle_target),
                    float(pr.next_cycle_target), float(pr.split_first_100), float(pr.split_after), int(pr.days_required), horizon, n, seed0, float(slip), int(conserv))
    return dict(payout=o[:, 0].mean(), p1=(o[:, 3] >= 0).mean(), npay=o[:, 1].mean(), life=o[:, 2].mean(), died=o[:, 4].mean(), raw=o)


def build_bars_synthetic(prod, entry_m, rng, flat_m=14 * 60 + 30):
    """Mundo de JUEGO JUSTO con la volatilidad real (signo de cada barra volteado al azar, encadenado desde la entrada); misma estructura de arreglos que build_bars."""
    stem, tick, tv = SPEC[prod]
    if prod not in _S: _S[prod] = load_sessions(stem)
    Hs, Ls, Cs, starts, ends, sides = [], [], [], [], [], []
    off = 0
    for day, h, l, c, m in _S[prod]:
        a = np.nonzero(m >= entry_m)[0]
        if len(a) == 0: continue
        ep = int(a[0]); jf = next((j for j in range(ep + 1, len(c)) if m[j] >= flat_m), len(c) - 1)
        if jf <= ep: continue
        e0 = c[ep]; prev = c[ep:jf]
        up = h[ep + 1:jf + 1] - prev; dn = l[ep + 1:jf + 1] - prev; ch = c[ep + 1:jf + 1] - prev
        sg = rng.random(len(prev)) < 0.5
        up2 = np.where(sg, up, -dn); dn2 = np.where(sg, dn, -up); ch2 = np.where(sg, ch, -ch)
        lvl = e0 + np.concatenate([[0.0], np.cumsum(ch2)])                 # cierres sinteticos (primer elemento = entrada)
        Hs.append(np.concatenate([[e0], lvl[:-1] + up2])); Ls.append(np.concatenate([[e0], lvl[:-1] + dn2])); Cs.append(lvl)
        n = jf - ep + 1; starts.append(off); ends.append(off + n - 1); sides.append(1 if rng.random() < 0.5 else -1); off += n
    return dict(H=np.concatenate(Hs), L=np.concatenate(Ls), C=np.concatenate(Cs), start=np.array(starts, dtype=np.int64), end=np.array(ends, dtype=np.int64),
                side=np.array(sides, dtype=np.int64), dates=None, tick=tick, tv=tv, comm_side=COMMISSION_PER_SIDE[prod], prod=prod, entry_m=entry_m)


def run_funded_topstep(bars, g_f, rho, tp_ticks, n=3000, seed0=1, idx=None, horizon=126, slip=0.0, conserv=1):
    """XFA estandar Topstep 50K (help.topstep.com 8284204/8284233, log 24/25-sep): MLL $2,000 EOD, se traba en $0 al llegar el balance a +$2,000, 5 dias >= $150, pago = min(50% del balance, $2,000), 90% al trader,
    tras un pago el piso queda en $0; sin DLL; escalado de contratos 20/30/40 micros (SUPUESTO, no verificado)."""
    caps_m = np.array([20.0, 30.0, 40.0, 40.0]); br = np.array([1_500.0, 2_000.0, 1e18])
    idx = np.arange(len(bars["start"])) if idx is None else idx
    o = funded_many(bars["H"], bars["L"], bars["C"], bars["start"], bars["end"], bars["side"], idx.astype(np.int64), bars["tick"], bars["tv"], bars["comm_side"], KIND_TOPSTEP, 2, 2000.0, 0.0,
                    caps_m, br, 1, 0.0, g_f, rho, tp_ticks, 0.0, 150.0, 0.0, 0.0, np.array([2000.0]), np.array([1.0]), 0.0, 0.0, 0.0, 0.9, 5, horizon, n, seed0, float(slip), int(conserv))
    return dict(payout=o[:, 0].mean(), p1=(o[:, 3] >= 0).mean(), npay=o[:, 1].mean(), life=o[:, 2].mean(), died=o[:, 4].mean(), raw=o)
