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
