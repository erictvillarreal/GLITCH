"""Simulador de un intento de Combine (Parte A): tablas de resultados diarios, politicas de sizing y Monte Carlo vectorizado.

Estado de un intento: (bal, peak, best_day). Piso = min(peak - MLL, FLOOR_CAP) con ratchet (se congela en 50,000).
Pase = balance al cierre >= objetivo Y mejor dia < CONSISTENCY_CAP. Liquidacion = el resultado diario es LIQ (kind=2).
Los dias salen de daydata.sim_day (replay del engine sobre barras reales) o de un DayData sintetico (M1).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from daydata import DayData, FEE_RT, SL_TICKS, TICK_USD, TP_TICKS, sim_day

MLL = 2000.0
FLOOR_CAP = 50000.0
TARGET = 53000.0
CONSIST_CAP = 1650.0          # mejor dia < 55% de la meta (encargo 1)
NC_MAX = 40
SUB_PER_DAY = 49.0 / 21.0     # $49/mes ~ 21 dias habiles -> ~$2.33/dia habil
RESET_FEE = 49.0
CUSH_STEP = 10.0              # resolucion de la tabla de colchon (se redondea ABAJO = conservador)
CUSH_MAX = 3500.0
START_IDX = 1775              # trading_day_index del miercoles 21-oct-2026 (encargo): impar -> SHORT


def side_of(day_index):
    """Misma regla que geometry_pure.decide_side('alternate'): par -> LONG, impar -> SHORT."""
    return 1 if (day_index % 2 == 0) else -1


class OutcomeTable:
    """(kind, pnl) por (lado, nc, bin de colchon) para todos los dias del DayData. Cache perezoso."""

    def __init__(self, dd: DayData, slip: float, exit_slip: float, order: str = "adverse",
                 sl: int = SL_TICKS, tp: int = TP_TICKS, step: float = CUSH_STEP, fee: float = FEE_RT, drift: float = 0.0):
        self.dd, self.slip, self.exit_slip, self.order, self.sl, self.tp, self.step, self.fee, self.drift = dd, slip, exit_slip, order, sl, tp, step, fee, drift
        self.nb = int(CUSH_MAX / step) + 1
        self._c: dict = {}

    def get(self, side: int, nc: int):
        key = (side, nc)
        if key not in self._c:
            D = self.dd.D
            kinds = np.empty((self.nb, D), dtype=np.int8); pnls = np.empty((self.nb, D), dtype=np.float64)
            for b in range(self.nb):
                cushion = max(b * self.step, 1e-9)
                k, p = sim_day(self.dd, side, nc, cushion, slip=self.slip, exit_slip=self.exit_slip, order=self.order,
                               sl=self.sl, tp=self.tp, fee=self.fee, drift=self.drift)
                kinds[b], pnls[b] = k, p
            self._c[key] = (kinds, pnls)
        return self._c[key]

    def bin_of(self, cushion):
        return np.clip(np.floor(cushion / self.step + 1e-9).astype(int), 0, self.nb - 1)


# ── Politicas (vectorizadas): f(ctx) -> nc (array int, 0 = no operar) ───────────────────────────────────────────
@dataclass
class Ctx:
    need: np.ndarray       # TARGET - bal
    bal: np.ndarray
    peak: np.ndarray
    floor: np.ndarray
    cushion: np.ndarray
    side: int
    t: int                 # dia (habil) desde el inicio del intento


SL_COST_SLIP_ENTRY = 3.0   # supuesto: peor slippage de entrada observado (mar 20-oct ~3 ticks, inferido; lun 19: 1)
SL_COST_SLIP_EXIT = 3.0    # SUPUESTO sin dato: no hay medicion empirica de slippage de salida en SL (ver REPORTE_A)


def sl_full_cost_per_contract(slip_in=SL_COST_SLIP_ENTRY, slip_out=SL_COST_SLIP_EXIT, sl=SL_TICKS, fee=FEE_RT):
    return (sl + slip_in + slip_out) * TICK_USD + fee


def tp_net_per_contract(slip=SL_COST_SLIP_ENTRY, tp=TP_TICKS, fee=FEE_RT):
    return (tp - slip) * TICK_USD - fee


def pol_fixed(n):
    return lambda c: np.full(c.bal.shape, int(n))


def pol_p2(min1=True, slip_in=SL_COST_SLIP_ENTRY, slip_out=SL_COST_SLIP_EXIT):
    cost = sl_full_cost_per_contract(slip_in, slip_out)
    def f(c):
        n = np.floor(c.cushion / cost + 1e-9).astype(int)
        n = np.clip(n, 1 if min1 else 0, NC_MAX)
        return n
    return f


def pol_p3(slip=SL_COST_SLIP_ENTRY):
    per = tp_net_per_contract(slip)
    def f(c):
        n = np.ceil(np.maximum(c.need, 0) / per - 1e-9).astype(int)
        return np.clip(n, 1, NC_MAX)
    return f


def pol_p4(min1=True):
    a, b = pol_p2(min1), pol_p3()
    return lambda c: np.minimum(a(c), b(c))


def pol_p4b(first_n=NC_MAX, first_days=1):
    p4 = pol_p4()
    def f(c):
        return np.full(c.bal.shape, first_n) if c.t < first_days else p4(c)
    return f


def pol_p5():
    p2, p3 = pol_p2(), pol_p3()
    def f(c):
        frozen = c.peak >= FLOOR_CAP + MLL      # piso congelado en 50,000
        return np.where(frozen, p3(c), p2(c))
    return f


def pol_p6(x, base):
    def f(c):
        n = base(c)
        return np.where(c.cushion < x, 0, n)
    return f


# ── Monte Carlo vectorizado ───────────────────────────────────────────────────────────────────────────────────
@dataclass
class McResult:
    n: int
    p_pass: float
    p_liq: float
    p_open: float
    ci_pass: tuple
    days_pass: tuple            # (mediana, p10, p90) sobre los que pasan
    p_liq_day1: float
    p_liq_near: dict            # {"<=200": p, "<=100": p}: P(liquidar | estuvo a <= X de la meta alguna vez)
    mean_days: float            # dias habiles promedio hasta resolverse (o maxdays si sigue abierto)
    sub_cost_mean: float
    reset_cost_mean: float
    bal_end_day1: np.ndarray = field(repr=False, default=None)
    worst_day: float = 0.0
    traded_days_mean: float = 0.0
    final_state: np.ndarray = field(repr=False, default=None)


def wilson(k, n, z=1.96):
    if n == 0: return (0.0, 1.0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0, c - h), min(1, c + h))


def run_mc(policy, tables, n=50000, seed=1, bal0=51401.2, peak0=None, start_idx=START_IDX, maxdays=60,
           slip_mix=None, block=1, target=TARGET, ratchet=True, mll=MLL, consistency=True, snap=None, best0=0.0, consistency_mode="abs"):
    """tables: OutcomeTable, o dict {slip: OutcomeTable} cuando slip_mix = (valores, probs) -> se sortea slip por (camino, dia).
    block: tamano de bloque de dias consecutivos (1 = iid)."""
    rng = np.random.default_rng(seed)
    peak0 = bal0 if peak0 is None else peak0
    tabs = tables if isinstance(tables, dict) else {0: tables}
    any_tab = next(iter(tabs.values())); D = any_tab.dd.D
    bal = np.full(n, bal0); peak = np.full(n, peak0); best = np.full(n, float(best0))
    alive = np.ones(n, bool); passed = np.zeros(n, bool); liq = np.zeros(n, bool)
    day_pass = np.full(n, -1); bal_day1 = None
    near200 = np.zeros(n, bool); near100 = np.zeros(n, bool); liq_near200 = np.zeros(n, bool); liq_near100 = np.zeros(n, bool)
    traded = np.zeros(n); days_active = np.zeros(n); worst = 0.0
    idx = rng.integers(0, D, size=n)
    for t in range(maxdays):
        a = alive
        if not a.any(): break
        floor_cap = FLOOR_CAP if ratchet else -1e18
        floor = np.minimum(peak - mll, floor_cap) if ratchet else peak - mll
        cush = bal - floor
        side = side_of(start_idx + t)
        ctx = Ctx(target - bal, bal, peak, floor, cush, side, t)
        nc = np.where(a, policy(ctx), 0)
        if block > 1 and t % block == 0:
            idx = rng.integers(0, D, size=n)
        elif block > 1:
            idx = (idx + 1) % D
        else:
            idx = rng.integers(0, D, size=n)
        if slip_mix is not None:
            vals, probs = slip_mix
            sl_choice = rng.choice(len(vals), size=n, p=probs)
        else:
            sl_choice = np.zeros(n, dtype=int)
        kind = np.full(n, 3, dtype=np.int8); pnl = np.zeros(n)
        for si in np.unique(sl_choice[a]):
            tab = tabs[(slip_mix[0][si] if slip_mix is not None else 0)]
            for ncv in np.unique(nc[a & (sl_choice == si)]):
                if ncv == 0: continue
                m = a & (sl_choice == si) & (nc == ncv)
                kinds_t, pnls_t = tab.get(side, int(ncv))
                b = tab.bin_of(cush[m])
                kind[m] = kinds_t[b, idx[m]]; pnl[m] = pnls_t[b, idx[m]]
        was_liq = a & (kind == 2)
        liq |= was_liq
        # seguimiento "cerca de la meta"
        need = target - bal
        near200 |= a & (need <= 200); near100 |= a & (need <= 100)
        liq_near200 |= was_liq & near200; liq_near100 |= was_liq & near100
        ok = a & ~was_liq
        bal = np.where(ok, bal + pnl, bal)
        bal = np.where(was_liq, floor, bal)
        if snap is not None:      # redondeo estocastico a la rejilla (para validar la DP: mismo espacio de estados)
            fl = np.floor((bal - 48000.0) / snap); fr = (bal - 48000.0) / snap - fl
            bal = np.where(ok, 48000.0 + snap * (fl + (rng.random(n) < fr)), bal)
        best = np.where(ok, np.maximum(best, pnl), best)
        peak = np.where(ok, np.maximum(peak, bal), peak)
        traded += np.where(ok & (nc > 0), 1, 0)
        days_active = np.where(a, t + 1, days_active)
        worst = min(worst, pnl[a].min() if a.any() else 0)
        if t == 0: bal_day1 = np.where(was_liq, floor, bal); liq1 = was_liq.copy()
        if not consistency:
            cons_ok = True
        elif consistency_mode == "abs":          # dashboard de Eric (encargo §1): mejor dia < 55% de la meta = $1,650
            cons_ok = best < CONSIST_CAP
        else:                                    # core/prop_firm.py: mejor dia < 50% del beneficio acumulado
            cons_ok = best < 0.5 * np.maximum(bal - 50000.0, 1e-9)
        newly = ok & (bal >= target) & cons_ok
        passed |= newly; day_pass = np.where(newly, t + 1, day_pass)
        alive = alive & ~was_liq & ~newly
    open_ = alive
    p_pass = passed.mean(); p_liq = liq.mean()
    dp = day_pass[passed]
    days = (np.median(dp), np.percentile(dp, 10), np.percentile(dp, 90)) if passed.any() else (np.nan,) * 3
    sub = SUB_PER_DAY * days_active.mean()
    res = McResult(n, p_pass, p_liq, open_.mean(), wilson(int(passed.sum()), n), days, float(liq1.mean()),
                   {"<=200": liq_near200.sum() / max(1, near200.sum()), "<=100": liq_near100.sum() / max(1, near100.sum())},
                   days_active.mean(), sub, RESET_FEE * p_liq, bal_day1, worst, traded.mean(), bal)
    return res
