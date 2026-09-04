"""
Glitch — Topstep Express Funded Account (XFA) — Standard Path
=================================================================
CONFIRMADO por el usuario via help.topstep.com (fuente oficial, no
de terceros) el 11-ago-2026. Reglas de la XFA Standard:

  - Balance arranca en $0 (no en el tamaño de la cuenta).
  - MLL: igual mecanica que el Combine (trailing EOD-only, solo sube),
    pero el rango es NEGATIVO: arranca en -mll_distance y se bloquea
    al llegar a +mll_distance (no al account_size como en el Combine).
  - Sin profit target — no hay "meta" que cierre el ciclo.
  - Payout Standard Path: 5 dias ganadores de >= $150 netos c/u.
    (Alternativa "XFA Consistency": 3 dias, consistencia <=40% —
    el usuario decidio NO usar este camino: el primer dia SIEMPRE
    viola el 40% por definicion matematica -- ver nota abajo.)
  - Payout maximo por solicitud: 50% del balance, tope $5,000
    (Standard) / $6,000 (Consistency).
  - Split 90/10.
  - Maximo 5 XFAs activas simultaneas.
  - Sin fee mensual despues de pasar el Combine.
  - Cuenta inactiva 30 dias -> se cierra.

NOTA sobre por que XFA Consistency queda descartado por diseño:
  La regla de consistencia (mejor dia < 40% del profit acumulado) es
  matematicamente imposible de cumplir el primer dia con profit>0,
  porque ese unico dia ES el 100% del acumulado. Se resuelve solo
  con dias adicionales despues -- pero como Standard Path (5 dias de
  $150+) ya es el camino natural para una estrategia calibrada a
  producir dias de ~$150-300 con contratos moderados, no tiene sentido
  cargar la complejidad extra de la regla de consistencia para ganar
  solo 1 payout mas rapido (3 dias vs 5) y $1,000 mas de tope.

VERIFICAR SIEMPRE contra help.topstep.com antes de operar dinero real --
Topstep puede cambiar estos numeros sin aviso (igual que TopstepCombineSpec).
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional
from enum import Enum


class XFAStatus(Enum):
    ACTIVE          = "active"
    BLOWN_MLL       = "blown_mll"        # equity <= floor -> cuenta cerrada (permanente)
    INACTIVE_CLOSED = "inactive_closed"  # 30 dias sin operar -> cerrada
    PAYOUT_ELIGIBLE = "payout_eligible"  # >=5 dias ganadores de $150+, listo para solicitar


@dataclass(frozen=True)
class XFASpec:
    label: str
    mll_distance: float          # 2_000 / 3_000 / 4_500 segun tamaño del Combine que pasaste
    min_winning_day_usd: float = 150.0
    winning_days_required: int = 5
    payout_pct_of_balance: float = 0.50
    payout_cap_usd: float = 5_000.0
    profit_split_trader: float = 0.90
    max_simultaneous_accounts: int = 5
    inactivity_close_days: int = 30

    @property
    def floor_start(self) -> float:
        return -self.mll_distance

    @property
    def floor_lock_level(self) -> float:
        return self.mll_distance


XFA_50K  = XFASpec(label="XFA-50K",  mll_distance=2_000)
XFA_100K = XFASpec(label="XFA-100K", mll_distance=3_000)
XFA_150K = XFASpec(label="XFA-150K", mll_distance=4_500)

XFA_SPECS = {"50K": XFA_50K, "100K": XFA_100K, "150K": XFA_150K}


def get_xfa_spec(size: str = "50K") -> XFASpec:
    if size not in XFA_SPECS:
        raise ValueError(f"Unknown size '{size}'. Choose from {list(XFA_SPECS)}")
    return XFA_SPECS[size]


@dataclass
class DayRecord:
    day_number: int
    pnl: float
    eod_balance: float
    mll_floor_after: float
    counted_as_winning: bool


@dataclass
class XFAAccount:
    """
    Maquina de estados de una Express Funded Account (Standard Path).

    A diferencia del Combine (core/account.py), aqui NO hay profit_target
    ni regla de consistencia -- el unico objetivo es acumular dias
    ganadores de >= min_winning_day_usd sin tocar el MLL.

    Uso:
        acct = XFAAccount(XFA_50K)
        for cada_dia:
            acct.start_day()
            acct.record_trade_pnl(pnl)
            acct.end_of_day()
            if acct.status == XFAStatus.PAYOUT_ELIGIBLE:
                acct.request_payout()   # resetea el contador de dias ganadores
            if not acct.is_alive: break
    """
    spec: XFASpec = field(default_factory=lambda: XFA_50K)

    # SIN RESOLVER contra fuente primaria completa (01-sep-2026): ¿el MLL
    # se fija en $0 SOLO en el primer payout, o EN CADA payout? El codigo
    # anterior a este cambio asumia "cada payout" de forma hardcodeada,
    # sin exponer la alternativa -- eso NO es lo mismo que "confirmado".
    # "every_payout" preserva el comportamiento anterior (default, para no
    # romper nada que ya dependiera de el); "first_payout_only" es la
    # alternativa sin probar. NUNCA reportar un numero de negocio usando
    # solo uno de los dos sin el otro al lado como sensibilidad.
    mll_reset_policy: str = "every_payout"  # "every_payout" | "first_payout_only"

    balance: float           = field(init=False)
    mll_floor: float         = field(init=False)
    status: XFAStatus        = field(init=False)
    day_number: int          = field(default=0, init=False)
    day_pnl: float           = field(default=0.0, init=False)
    winning_days_count: int  = field(default=0, init=False)
    lifetime_payouts: int    = field(default=0, init=False)
    lifetime_payout_usd: float = field(default=0.0, init=False)
    days_since_last_trade: int = field(default=0, init=False)
    day_log: List[DayRecord] = field(default_factory=list, init=False)
    _has_had_first_payout: bool = field(default=False, init=False)

    def __post_init__(self):
        self.balance   = 0.0
        self.mll_floor = self.spec.floor_start
        self.status    = XFAStatus.ACTIVE

    def start_day(self):
        self.day_number += 1
        self.day_pnl = 0.0

    def record_trade_pnl(self, realized_pnl: float):
        if self.status not in (XFAStatus.ACTIVE, XFAStatus.PAYOUT_ELIGIBLE):
            return
        self.balance += realized_pnl
        self.day_pnl += realized_pnl
        self.days_since_last_trade = 0

    def end_of_day(self, no_trade_today: bool = False):
        if no_trade_today:
            self.days_since_last_trade += 1
            if self.days_since_last_trade >= self.spec.inactivity_close_days:
                self.status = XFAStatus.INACTIVE_CLOSED
            return

        # 1. Floor solo sube, EOD-only (misma mecanica que el Combine)
        new_floor = self.balance - self.spec.mll_distance
        if new_floor > self.mll_floor:
            self.mll_floor = min(new_floor, self.spec.floor_lock_level)

        # 2. Blow check (permanente)
        if self.balance <= self.mll_floor:
            self.status = XFAStatus.BLOWN_MLL
            self._log_day(counted=False)
            return

        # 3. Dia ganador cuenta si el PnL neto del dia >= min_winning_day_usd
        counted = self.day_pnl >= self.spec.min_winning_day_usd
        if counted:
            self.winning_days_count += 1

        # 4. Elegibilidad de payout
        if self.winning_days_count >= self.spec.winning_days_required:
            self.status = XFAStatus.PAYOUT_ELIGIBLE
        elif self.status != XFAStatus.PAYOUT_ELIGIBLE:
            self.status = XFAStatus.ACTIVE

        self._log_day(counted=counted)

    def request_payout(self) -> float:
        """
        Solicita el payout maximo permitido y resetea el contador de dias
        ganadores (el balance NO se resetea -- solo baja por el monto pagado).
        Devuelve el monto (para el trader, ya con el split 90/10 aplicado).
        """
        if self.status != XFAStatus.PAYOUT_ELIGIBLE:
            raise RuntimeError("Cuenta no elegible para payout todavia")

        gross = min(self.balance * self.spec.payout_pct_of_balance, self.spec.payout_cap_usd)
        trader_take = gross * self.spec.profit_split_trader

        self.balance -= gross
        # SIN RESOLVER (ver mll_reset_policy arriba): la cita original de
        # help.topstep.com decia "el MLL se fija en $0 tras el primer
        # payout" -- pero nunca se verifico si eso aplica SOLO la primera
        # vez o CADA vez. "every_payout" fuerza el floor a 0 siempre (el
        # comportamiento que este codigo tenia hardcodeado antes de esto);
        # "first_payout_only" solo lo fuerza la primera vez, dejando que
        # el trailing normal de end_of_day() gobierne despues.
        if self.mll_reset_policy == "every_payout" or not self._has_had_first_payout:
            self.mll_floor = 0.0
        self._has_had_first_payout = True
        self.winning_days_count = 0
        self.lifetime_payouts += 1
        self.lifetime_payout_usd += trader_take
        self.status = XFAStatus.ACTIVE
        return trader_take

    @property
    def is_alive(self) -> bool:
        return self.status not in (XFAStatus.BLOWN_MLL, XFAStatus.INACTIVE_CLOSED)

    @property
    def mll_buffer(self) -> float:
        return self.balance - self.mll_floor

    @property
    def days_to_next_payout(self) -> int:
        return max(0, self.spec.winning_days_required - self.winning_days_count)

    def _log_day(self, counted: bool):
        self.day_log.append(DayRecord(
            day_number=self.day_number, pnl=round(self.day_pnl, 2),
            eod_balance=round(self.balance, 2), mll_floor_after=round(self.mll_floor, 2),
            counted_as_winning=counted,
        ))

    def summary(self) -> dict:
        return {
            "status": self.status.value, "day": self.day_number,
            "balance": round(self.balance, 2), "mll_floor": round(self.mll_floor, 2),
            "mll_buffer": round(self.mll_buffer, 2),
            "winning_days": self.winning_days_count,
            "days_to_next_payout": self.days_to_next_payout,
            "lifetime_payouts": self.lifetime_payouts,
            "lifetime_payout_usd": round(self.lifetime_payout_usd, 2),
        }


def simulate_xfa_paths(dist, spec: XFASpec = XFA_50K, n_paths: int = 5000,
                        max_days: int = 60, seed: int = 7) -> dict:
    """
    Simula N intentos de XFA (primer ciclo, desde balance=$0). Devuelve
    tambien el balance/payout real al momento del trigger.
    """
    import numpy as np
    rng = np.random.default_rng(seed)
    n_eligible = 0
    n_blown = 0
    days_to_eligible = []
    balance_at_eligible = []
    for _ in range(n_paths):
        acct = XFAAccount(spec)
        daily_pnls = dist.sample(max_days, rng)
        for day_pnl in daily_pnls:
            acct.start_day()
            acct.record_trade_pnl(float(day_pnl))
            acct.end_of_day()
            if acct.status == XFAStatus.PAYOUT_ELIGIBLE:
                n_eligible += 1
                days_to_eligible.append(acct.day_number)
                balance_at_eligible.append(acct.balance)
                break
            if not acct.is_alive:
                n_blown += 1
                break
    payouts_usd = None
    if balance_at_eligible:
        bal = np.array(balance_at_eligible)
        gross = np.minimum(bal * spec.payout_pct_of_balance, spec.payout_cap_usd)
        trader_take = gross * spec.profit_split_trader
        payouts_usd = {
            "avg_balance_at_trigger": float(bal.mean()),
            "median_balance_at_trigger": float(np.median(bal)),
            "avg_payout_usd": float(trader_take.mean()),
            "median_payout_usd": float(np.median(trader_take)),
            "pct_hit_cap": float((bal * spec.payout_pct_of_balance >= spec.payout_cap_usd).mean()),
        }
    return {
        "n_paths": n_paths,
        "prob_eligible": n_eligible / n_paths,
        "prob_blown": n_blown / n_paths,
        "prob_neither_yet": 1 - (n_eligible + n_blown) / n_paths,
        "avg_days_to_eligible": float(np.mean(days_to_eligible)) if days_to_eligible else None,
        "payout": payouts_usd,
    }


def simulate_xfa_lifetime(dist, spec: XFASpec = XFA_50K, mll_reset_policy: str = "every_payout",
                           n_paths: int = 5000, max_days: int = 756, seed: int = 7) -> dict:
    """
    Simula la VIDA COMPLETA de N cuentas XFA -- a diferencia de
    simulate_xfa_paths() (que se detiene en el primer payout o blow),
    esto encadena payouts sucesivos: la cuenta sigue operando despues de
    cada payout (balance reducido, NO reseteado a cero) hasta que truena
    (BLOWN_MLL) o se acaba max_days sin haber truenado (right-censored --
    ver prob_still_alive_at_horizon, un promedio que ignora esto
    SUBESTIMA el verdadero valor esperado).

    max_days=756 (~3 años habiles) por default -- horizonte largo a
    proposito, no un numero de negocio en si.

    mll_reset_policy: "every_payout" o "first_payout_only" -- ver
    XFAAccount.mll_reset_policy. SIEMPRE correr ambos y reportarlos
    lado a lado, nunca uno solo como respuesta final (pregunta sin
    resolver contra fuente primaria completa -- ver docstring del modulo
    y GLITCH_RESEARCH_LOG.md).

    Vectorizado sobre el eje de paths (04-sep-2026): la version anterior
    era un loop Python escalar path-por-path/dia-por-dia -- su costo
    real depende de cuantos dias corre cada path antes de tronar
    (`break` temprano), y ese costo varia ~75x entre combinaciones de
    bajo blow-rate (WR cerca de WR_natural, ~12ms/corrida) y alto
    blow-rate cercano a 0 -- osea alta supervivencia, RR/WR altos, que
    corren el horizonte casi completo (~900ms/corrida). Un benchmark de
    un solo punto no representa ese rango. Validado bit-a-bit contra la
    version escalar anterior en 32 casos (deterministas y estocasticos,
    las 3 cuentas, ambas politicas, WR/RR bajos y altos) antes de
    reemplazarla -- ver GLITCH_RESEARCH_LOG.md.
    """
    import numpy as np
    rng = np.random.default_rng(seed)
    pnls = dist.sample(n_paths * max_days, rng).reshape(n_paths, max_days)

    mll_distance = spec.mll_distance
    floor_lock_level = spec.floor_lock_level
    min_winning_day_usd = spec.min_winning_day_usd
    winning_days_required = spec.winning_days_required
    payout_pct = spec.payout_pct_of_balance
    payout_cap = spec.payout_cap_usd
    split = spec.profit_split_trader

    balance = np.zeros(n_paths)
    mll_floor = np.full(n_paths, spec.floor_start)
    alive = np.ones(n_paths, dtype=bool)
    winning_days_count = np.zeros(n_paths, dtype=np.int64)
    lifetime_payouts = np.zeros(n_paths, dtype=np.int64)
    lifetime_payout_usd = np.zeros(n_paths)
    has_had_first_payout = np.zeros(n_paths, dtype=bool)
    day_number = np.zeros(n_paths, dtype=np.int64)

    for day in range(max_days):
        active_at_start = alive
        day_pnl = pnls[:, day]

        balance = np.where(active_at_start, balance + day_pnl, balance)
        day_number = np.where(active_at_start, day + 1, day_number)

        new_floor_candidate = balance - mll_distance
        floor_should_update = active_at_start & (new_floor_candidate > mll_floor)
        mll_floor = np.where(floor_should_update, np.minimum(new_floor_candidate, floor_lock_level), mll_floor)

        newly_blown = active_at_start & (balance <= mll_floor)
        alive = alive & ~newly_blown

        still_active_today = active_at_start & ~newly_blown
        counted = still_active_today & (day_pnl >= min_winning_day_usd)
        winning_days_count = np.where(counted, winning_days_count + 1, winning_days_count)

        eligible = still_active_today & (winning_days_count >= winning_days_required)
        if eligible.any():
            gross = np.minimum(balance[eligible] * payout_pct, payout_cap)
            trader_take = gross * split
            balance = balance.copy()
            balance[eligible] -= gross
            if mll_reset_policy == "every_payout":
                mll_floor = mll_floor.copy()
                mll_floor[eligible] = 0.0
            else:
                reset_now = eligible & (~has_had_first_payout)
                if reset_now.any():
                    mll_floor = mll_floor.copy()
                    mll_floor[reset_now] = 0.0
            has_had_first_payout = has_had_first_payout.copy()
            has_had_first_payout[eligible] = True
            winning_days_count = winning_days_count.copy()
            winning_days_count[eligible] = 0
            lifetime_payouts = lifetime_payouts.copy()
            lifetime_payouts[eligible] += 1
            lifetime_payout_usd = lifetime_payout_usd.copy()
            lifetime_payout_usd[eligible] += trader_take

    n_never_eligible = int((lifetime_payouts == 0).sum())
    n_still_alive_at_horizon = int(alive.sum())
    payouts_arr = lifetime_payouts.astype(float)
    days_arr = day_number.astype(float)
    usd_arr = lifetime_payout_usd

    return {
        "n_paths": n_paths,
        "mll_reset_policy": mll_reset_policy,
        "max_days_horizon": max_days,
        "prob_still_alive_at_horizon": n_still_alive_at_horizon / n_paths,
        "prob_never_reached_first_payout": n_never_eligible / n_paths,
        "avg_lifetime_payouts": float(payouts_arr.mean()),
        "median_lifetime_payouts": float(np.median(payouts_arr)),
        "payouts_p10_p90": (float(np.percentile(payouts_arr, 10)), float(np.percentile(payouts_arr, 90))),
        "avg_lifetime_days": float(days_arr.mean()),
        "median_lifetime_days": float(np.median(days_arr)),
        "avg_lifetime_payout_usd": float(usd_arr.mean()),
        "median_lifetime_payout_usd": float(np.median(usd_arr)),
        "payout_usd_p10_p90": (float(np.percentile(usd_arr, 10)), float(np.percentile(usd_arr, 90))),
    }
