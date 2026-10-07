"""Puerto de broker para un ejecutor a medida de Bulenox + implementacion SIMULADA (SimBroker) que aplica las reglas de la cuenta. NO hay ninguna conexion real:
RithmicBroker es solo el contrato de lo que habria que implementar (ver bulenox/EXECUTOR_DESIGN.md). SANDBOX / R&D: sin credenciales, sin red, sin produccion."""
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional
from bulenox.account import BulenoxAccount, Breach


@dataclass
class AccountState:
    balance: float            # realizado relativo al saldo inicial
    threshold: float          # umbral de drawdown relativo
    micros_cap: int
    dll_hit: bool
    status: str
    position_qty: int
    position_side: int


class BrokerPort(ABC):
    """Lo minimo que necesita el ejecutor (un bracket al dia, cierre antes de las 15:59 CT)."""
    @abstractmethod
    def account_state(self) -> AccountState: ...
    @abstractmethod
    def place_bracket(self, side: int, qty: int, entry_px: float, tp_px: float, sl_px: float) -> None: ...
    @abstractmethod
    def flatten(self, px: float) -> None: ...
    @abstractmethod
    def cancel_all(self) -> None: ...


class SimBroker(BrokerPort):
    """Broker simulado con las reglas de Bulenox (bulenox/account.py). Se alimenta con barras (high, low, close) via on_bar()."""
    def __init__(self, acct: BulenoxAccount):
        self.acct = acct
        self.prev_close: Optional[float] = None
        self.log: List[str] = []

    def account_state(self) -> AccountState:
        a = self.acct
        return AccountState(a.balance, a.threshold, a.micros_cap(), a.dll_hit, a.status, a.pos.qty if a.pos else 0, a.pos.side if a.pos else 0)

    def place_bracket(self, side, qty, entry_px, tp_px, sl_px):
        self.acct.open(side, qty, entry_px, tp=tp_px, sl=sl_px)       # lanza Breach si excede el tope de contratos, DLL activo o cuenta suspendida
        self.prev_close = entry_px

    def flatten(self, px):
        self.acct.flatten(px)

    def cancel_all(self):
        if self.acct.pos: self.acct.pos.tp = None; self.acct.pos.sl = None

    def on_bar(self, high: float, low: float, close: float):
        a = self.acct
        if a.pos is None or a.status != "active":
            self.prev_close = close; return a.status == "active"
        try:
            ok = a.bar(high, low, close, self.prev_close if self.prev_close is not None else close)
        except Breach:
            ok = False                                                  # cuenta suspendida por drawdown
        self.prev_close = close
        return ok

    def end_of_day(self):
        self.acct.end_of_day()


class RithmicBroker(BrokerPort):   # pragma: no cover - contrato, sin implementacion
    """Requisitos (a confirmar con Bulenox/Rithmic; ver EXECUTOR_DESIGN.md): API de Rithmic de terceros (+$100/mes), Rithmic Paper Trading (Chicago), ordenes bracket OCO gestionadas por el servidor
    (OCO local de NinjaTrader NO sirve: puede dejar posiciones extra si se cae la conexion [HC connection]), cierre antes de las 15:59 CT, un unico Rithmic User ID para todas las cuentas."""
    def account_state(self): raise NotImplementedError
    def place_bracket(self, side, qty, entry_px, tp_px, sl_px): raise NotImplementedError
    def flatten(self, px): raise NotImplementedError
    def cancel_all(self): raise NotImplementedError
