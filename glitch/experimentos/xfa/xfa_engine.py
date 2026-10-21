"""xfa_engine -- motor exacto de la VIDA de una XFA 50K (Parte D). Vectorizado sobre trayectorias; semilla fija.

Estado por trayectoria: balance b (neto, empieza en 0), piso f (empieza en -MLL, sube con el balance de CIERRE, se fija en $0 al llegar a +MLL y tras el primer pago),
dias ganadores wd, ganancia desde el ultimo pago, mejor dia (ruta Consistency), dias operados, pagos.
Dinamica diaria: un trade (tamano nc decidido por la politica; 0 = no operar) con la mecanica del engine real: referencia, TP/SL en ticks desde la REFERENCIA,
slippage de entrada adverso, comision, liquidacion en TIEMPO REAL cuando la perdida flotante toca el piso (cierra la XFA), flatten de fin de sesion.
Reglas: dataclass Rules (cada campo = una regla del RULEBOOK; los AMBIGUO/DESCONOCIDO son escenarios).
Proveedores de dias (Days): BarDays (replay de barras reales de 5 min con la mecanica exacta), TableDays (tablas de primer toque: SOLO para la regresion contra lever_engine),
Brownian (DayData sintetico).

Nada de esto toca produccion. Marcado SANDBOX / R&D.
"""
from __future__ import annotations

import dataclasses as dc
import os
import sys
from dataclasses import dataclass

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "preservacion"))
from daydata import DayData, sim_day  # noqa: E402

INF = 10 ** 6


@dataclass
class Rules:
    """Reglas de la XFA 50K. Defaults = RULEBOOK_XFA.md (VERIFICADO) con escenario base de las preguntas abiertas."""
    mll: float = 2000.0               # RULEBOOK 1.3
    lock: float = 0.0                 # el MLL se fija en $0 (1.3/1.4); el codigo viejo usaba +MLL
    win_usd: float = 150.0            # 2.1 dia ganador >= $150 NETO de comision (2.2)
    win_days: int = 5                 # 2.1
    pct: float = 0.5                  # 2.4
    cap: float = 2000.0               # 2.4 (4000 con DLL comprado: oferta temporal, 1.5)
    minpay: float = 125.0             # 2.5
    split: float = 0.9                # 2.7
    first100: float = 0.0             # 2.7: primeros $10,000 al 100 % (0 = sin beneficio; 10000 = beneficio)
    wire_fee: float = 0.0             # 2.10: $30 por pago internacional (se descuenta del neto cobrado)
    profit_rule: bool = True          # 2.3: desde el 2o pago hace falta ganancia neta >= $0.01 desde el ultimo
    path: str = "std"                 # "std" | "cons" (3.2)
    cons_pct: float = 0.40
    cons_days: int = 3
    dll: float | None = None          # 1.5: DLL fijo (1000 en 50K); recorta el stop del dia y no cierra la cuenta
    min_request_balance: float = 0.0  # 2.6 (escenario P2: 1500)
    scaling: bool = True              # 1.6/1.7: tope de contratos por saldo
    product: str = "MGC"              # "MGC": 12/18/31 micros (restringido); "MES": 20/30/50
    idle_close_days: int = 30         # 1.10


def plan_cap(b, product="MGC"):
    """Max micros por saldo (RULEBOOK 1.6 y 1.7). El tramo se evalua con el saldo al inicio de la sesion."""
    if product == "MGC":
        return np.where(b < 1500.0, 12, np.where(b < 2000.0, 18, 31))
    return np.where(b < 1500.0, 20, np.where(b < 2000.0, 30, 50))


# ── proveedores de dias ────────────────────────────────────────────────────────────────────────────────────────────────
class BarDays:
    """Replay de barras reales con sim_day (mecanica exacta). Cache perezoso por (lado, nc, sl) y bin de colchon ($10, redondeo ABAJO = conservador)."""

    def __init__(self, dd: DayData, tick_usd: float, fee: float, sl: int, tp: int, slip=(0.0,), slip_p=None, exit_slip: float = 0.0, order: str = "adverse",
                 cush_max: float = 9000.0, step: float = 10.0, mask=None):
        self.dd, self.tick_usd, self.fee, self.sl, self.tp, self.exit_slip, self.order = dd, tick_usd, fee, sl, tp, exit_slip, order
        self.slips = tuple(slip); self.slip_p = np.full(len(self.slips), 1.0 / len(self.slips)) if slip_p is None else np.asarray(slip_p, float)
        self.step, self.nb = step, int(cush_max / step) + 1
        self.pool = np.arange(dd.D) if mask is None else np.nonzero(mask)[0]
        self._c = {}

    def table(self, side, nc, sl, si):
        key = (side, nc, sl, si)
        if key not in self._c:
            K = np.empty((self.nb, self.dd.D), np.int8); Pn = np.empty((self.nb, self.dd.D))
            for b in range(self.nb):
                k, p = sim_day(self.dd, side, nc, max(b * self.step, 1e-9), slip=self.slips[si], exit_slip=self.exit_slip, sl=sl, tp=self.tp, order=self.order,
                               fee=self.fee, tick_usd=self.tick_usd)
                K[b], Pn[b] = k, p
            self._c[key] = (K, Pn)
        return self._c[key]

    def draw(self, rng, n):
        return self.pool[rng.integers(0, len(self.pool), n)], rng.choice(len(self.slips), size=n, p=self.slip_p)

    def resolve(self, idx, si, side, nc, cush, sl):
        """idx, si, side, nc, cush, sl: arrays (n,). Devuelve (kind, pnl). nc = 0 -> sin trade (kind 3, pnl 0)."""
        n = len(idx); kind = np.full(n, 3, np.int8); pnl = np.zeros(n)
        bins = np.clip(np.floor(cush / self.step + 1e-9).astype(int), 0, self.nb - 1)
        for ncv in np.unique(nc):
            if ncv == 0: continue
            for slv in np.unique(sl[nc == ncv]):
                for sd in (1, -1):
                    for s_i in range(len(self.slips)):
                        m = (nc == ncv) & (sl == slv) & (side == sd) & (si == s_i)
                        if not m.any(): continue
                        K, Pn = self.table(sd, int(ncv), int(slv), s_i)
                        kind[m] = K[bins[m], idx[m]]; pnl[m] = Pn[bins[m], idx[m]]
        return kind, pnl


class TableDays:
    """SOLO para la regresion: replica exacta de scripts/xfa_liquidation_check.xfa (tablas de primer toque, lado ya 'horneado' en cada dia, sin slippage)."""

    def __init__(self, adv, tpt, flat, tv, comm, sl, tp, kmax=500):
        self.adv, self.tpt, self.flat, self.tv, self.comm, self.sl, self.tp, self.kmax = adv, tpt, flat, tv, comm, sl, tp, kmax
        self.pool = np.arange(len(adv))

    def draw(self, rng, n):
        return rng.integers(0, len(self.adv), n), np.zeros(n, int)

    def resolve(self, idx, si, side, nc, cush, sl):
        unit = np.maximum(nc, 1) * self.tv
        k = np.clip(np.minimum(sl, np.ceil(cush / unit - 1e-9)), 1, self.kmax).astype(int)
        ab = self.adv[idx, k]; tb = self.tpt[idx, self.tp]
        tp_hit = tb < ab; sl_hit = ~tp_hit & (ab < INF)
        pnl = np.where(tp_hit, self.tp * unit, np.where(sl_hit, -k * unit, self.flat[idx] * unit)) - self.comm * nc
        kind = np.where(tp_hit, 0, np.where(sl_hit, np.where(k < sl, 2, 1), 3)).astype(np.int8)
        return kind, np.where(nc > 0, pnl, 0.0)


# ── politicas ──────────────────────────────────────────────────────────────────────────────────────────────────────────────
@dataclass
class State:
    t: int
    b: np.ndarray
    f: np.ndarray
    wd: np.ndarray
    first: np.ndarray
    npay: np.ndarray
    cushion: np.ndarray


@dataclass
class Policy:
    """nc_fn(State)->array nc (0 = no operar). pay: 'max' | 'min' | 'wait' | callable(State, gmax)->g (0 = esperar). sl_fn opcional (SL por trayectoria)."""
    name: str
    nc_fn: object
    pay: object = "max"
    sl: int = 364
    tp: int = 364


def pol_fixed(nc, sl=364, tp=364, pay="max", name=None):
    return Policy(name or f"fijo nc={nc}", lambda s: np.full(s.b.shape, int(nc)), pay, sl, tp)


# ── motor ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
def simulate_life(days, rules: Rules, policy: Policy, n=50000, seed=1, max_days=756, start_parity=None):
    """Vida de UNA XFA hasta liquidacion o max_days. Devuelve dict de arrays (n,)."""
    rng = np.random.default_rng(seed)
    b = np.zeros(n); f = np.full(n, -rules.mll); b_ref = np.zeros(n)
    alive = np.ones(n, bool); wd = np.zeros(n, int); first = np.ones(n, bool); npay = np.zeros(n, int)
    paid = np.zeros(n); gross_paid = np.zeros(n); life = np.zeros(n, int); dtrade = np.zeros(n, int); best = np.zeros(n); idle = np.zeros(n, int)
    first_pay_day = np.full(n, -1); liq_events = np.zeros(n, int); sl_events = np.zeros(n, int); tp_events = np.zeros(n, int); flat_events = np.zeros(n, int)
    paid_first = np.zeros(n); cd = np.zeros(n, int)
    par0 = rng.integers(0, 2, n) if start_parity is None else np.full(n, start_parity)
    for t in range(max_days):
        a = alive
        if not a.any(): break
        side = np.where((par0 + t) % 2 == 0, 1, -1)
        st = State(t, b, f, wd, first, npay, b - f)
        nc = np.where(a, policy.nc_fn(st), 0).astype(int)
        if rules.scaling:
            nc = np.minimum(nc, plan_cap(b, rules.product))
        sl = np.full(n, policy.sl)
        if rules.dll is not None:                       # DLL: el stop del dia no puede perder mas que el DLL (incl. comision); tocarlo NO cierra la cuenta
            tick_usd = days.tick_usd if hasattr(days, "tick_usd") else 1.0
            fee = days.fee if hasattr(days, "fee") else 0.0
            sl = np.minimum(sl, np.maximum(np.floor((rules.dll - fee * nc) / (np.maximum(nc, 1) * tick_usd)), 1)).astype(int)
        idx, si = days.draw(rng, n)
        kind, pnl = days.resolve(idx, si, side, nc, np.maximum(b - f, 0.0), sl)
        traded = a & (nc > 0)
        liq = traded & (kind == 2)
        tp_events += traded & (kind == 0); sl_events += traded & (kind == 1); liq_events += liq; flat_events += traded & (kind == 3)
        ok = a & ~liq
        b = np.where(ok, b + pnl, b)
        b = np.where(liq, f, b)                          # liquidada: queda en el piso y se cierra
        life += a
        dtrade += traded; cd = np.where(a & traded, cd + 1, cd)
        idle = np.where(a & (nc == 0), idle + 1, np.where(a, 0, idle))
        # fin de dia: sube el piso con el balance de CIERRE
        cand = np.minimum(b - rules.mll, rules.lock)
        f = np.where(ok & (cand > f), cand, f)
        dead = a & ((b <= f + 1e-9) | liq | (idle > rules.idle_close_days))
        alive = alive & ~dead
        # dias ganadores / ruta Consistency
        wd = np.where(alive & traded & (pnl >= rules.win_usd), wd + 1, wd)
        best = np.where(alive & traded, np.maximum(best, pnl), best)
        prof = b - b_ref
        if rules.path == "std":
            elig = alive & (wd >= rules.win_days)
        else:
            cons_ok = (prof > 0) & (best <= rules.cons_pct * prof + 1e-9)
            elig = alive & (cd >= rules.cons_days) & cons_ok
        if rules.profit_rule:
            elig &= first | (prof >= 0.01)
        elig &= b > 0
        cap = rules.cap
        gmax = np.minimum(b * rules.pct, cap)
        elig &= (gmax >= rules.minpay) & (b >= rules.min_request_balance)
        if elig.any():
            if policy.pay == "max": g = gmax
            elif policy.pay == "min": g = np.minimum(np.maximum(rules.minpay, 0.0), gmax)
            elif policy.pay == "wait": g = np.zeros(n)
            else: g = policy.pay(State(t, b, f, wd, first, npay, b - f), gmax)
            g = np.where(elig, np.minimum(g, gmax), 0.0)
            do = elig & (g > 0) & (g >= rules.minpay - 1e-9)
            g = np.where(do, g, 0.0)
            # monto neto al trader: 100 % hasta first100 acumulado, luego split; menos comision de transferencia
            r100 = np.maximum(rules.first100 - gross_paid, 0.0)
            net = np.minimum(g, r100) + (g - np.minimum(g, r100)) * rules.split - np.where(do, rules.wire_fee, 0.0)
            paid += np.where(do, net, 0.0); gross_paid += g
            paid_first = np.where(do & first, net, paid_first)
            first_pay_day = np.where(do & first, t, first_pay_day)
            b = b - g
            f = np.where(do, 0.0, f)
            wd = np.where(do, 0, wd); best = np.where(do, 0.0, best); b_ref = np.where(do, b, b_ref)
            first = first & ~do; npay += do; cd = np.where(do, 0, cd)
    return dict(paid=paid, gross=gross_paid, npay=npay, life=life, alive=alive, first_pay_day=first_pay_day, paid_first=paid_first, liq=liq_events, sl=sl_events, tp=tp_events,
                flat=flat_events, dtrade=dtrade, bal=b)
