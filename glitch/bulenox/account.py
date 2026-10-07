"""Motor de reglas de una cuenta Bulenox a nivel de barra/extremo de precio (para probar ejecutores y estrategias SIN tocar la plataforma real).
Implementa, con las reglas de bulenox/rules.py: drawdown dinamico (Opcion 1, en tiempo real incl. no realizado y comisiones) y de cierre/EOD (Opcion 2), lock en saldo inicial+$100,
DLL suave (pausa la jornada), escalado de contratos por efectivo disponible, cierre de posiciones antes de las 15:59 CT, comisiones por lado, pase de la calificacion y solicitudes de pago
(Master, Momentum Master, Fast Track) con consistencia, reserva, topes y el 100% de los primeros $10,000. Todos los montos son RELATIVOS al saldo inicial (balance=0 al abrir).
SANDBOX / R&D."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, List
from bulenox.rules import Plan, PayoutRules, plan as make_plan, payout_rules, split, commission_rt, LOCK_OFFSET, COMMISSION_PER_SIDE


class Breach(Exception):
    pass


@dataclass
class Position:
    side: int
    qty: int
    entry: float
    tp: Optional[float] = None
    sl: Optional[float] = None


@dataclass
class DayLog:
    pnl: float
    traded: bool
    dll_hit: bool


class BulenoxAccount:
    def __init__(self, plan: Plan, stage: str = "qualification", prod: str = "MES", tick: float = 0.25, tv: float = 1.25):
        self.plan, self.stage = plan, stage          # stage: qualification | master | fast_track | momentum_master
        self.prod, self.tick, self.tv = prod, tick, tv
        self.size = plan.size
        self.balance = 0.0                           # realizado, relativo al saldo inicial (incluye comisiones)
        self.status = "active"                       # active | suspended | passed
        self.pos: Optional[Position] = None
        self.max_close = 0.0                         # maximo cierre EOD (Opcion 2)
        self.peak_equity = 0.0                       # maximo valor de la cuenta (Opcion 1)
        self.threshold = -plan.drawdown              # umbral de drawdown relativo
        self.locked = False
        self.day_realized = 0.0                      # realizado del dia (incl. comisiones)
        self.day_traded = False
        self.dll_hit = False
        self.trading_days = 0
        self.days: List[DayLog] = []
        self.best_day = 0.0
        # pagos
        self.pay_n = 0
        self.paid_gross = 0.0
        self.cycle_start_balance = 0.0
        self.cycle_best_day = 0.0
        self.cycle_days = 0
        self.cycle_win_days = 0
        self.cushion = 0.0                           # Fast Track: nivel que permanece tras cada pago
        self.events: List[str] = []

    # ---------------- utilidades
    @property
    def lock_level(self) -> float:
        return LOCK_OFFSET

    def cash_on_hand(self) -> float:
        return self.balance

    def micros_cap(self) -> int:
        if self.plan.option == 2 and self.stage in ("qualification",) and len(self.plan.contracts) > 1:
            return self.plan.micros_cap(self.balance)
        if self.stage == "master" and self.plan.option == 2 and len(self.plan.contracts) > 1:
            return self.plan.micros_cap(self.balance)           # [HC master] el plan de escalado se mantiene en Master
        return self.plan.max_micros

    def unrealized(self, price: float) -> float:
        if not self.pos: return 0.0
        return (price - self.pos.entry) * self.pos.side / self.tick * self.tv * self.pos.qty

    def equity(self, price: float) -> float:
        return self.balance + self.unrealized(price)

    def _comm_side(self, qty: int) -> float:
        return COMMISSION_PER_SIDE[self.prod] * qty

    def dll_active(self) -> bool:
        if self.plan.dll is None: return False
        if self.stage in ("master",) and self.locked: return False        # [HC master] se elimina permanentemente al fijarse el drawdown
        return True

    # ---------------- operaciones
    def open(self, side: int, qty: int, price: float, tp: Optional[float] = None, sl: Optional[float] = None):
        if self.status != "active": raise Breach("cuenta no activa")
        if self.dll_hit: raise Breach("DLL alcanzado: trading desactivado el resto de la jornada")
        if self.pos: raise Breach("ya hay posicion")
        if qty > self.micros_cap(): raise Breach(f"excede el tope de contratos ({qty} > {self.micros_cap()} micros)")
        self.pos = Position(side, qty, price, tp, sl)
        c = self._comm_side(qty); self.balance -= c; self.day_realized -= c
        self.day_traded = True

    def _close(self, price: float, why: str):
        u = self.unrealized(price); c = self._comm_side(self.pos.qty)
        self.balance += u - c; self.day_realized += u - c
        self.events.append(f"close {why} @ {price} pnl {u - c:+.2f}"); self.pos = None

    def flatten(self, price: float):
        if self.pos: self._close(price, "flatten")

    # ---------------- seguimiento en tiempo real de un extremo de precio
    def _check_at(self, price: float):
        """Revisa umbral (Opcion 1 y 2) y DLL (Opcion 2) con el precio dado, con la posicion abierta."""
        eq = self.equity(price)
        if self.plan.option == 1 and not self.locked:
            if eq > self.peak_equity:
                self.peak_equity = eq
                self.threshold = min(self.peak_equity - self.plan.drawdown, self.lock_level if self.stage in ("master", "fast_track", "momentum_master") else float("inf"))
                if self.stage in ("master", "fast_track", "momentum_master") and self.peak_equity - self.plan.drawdown >= self.lock_level: self.locked = True
        if eq <= self.threshold:
            if self.pos: self._close(price, "BREACH")
            self.status = "suspended"; self.events.append("DRAWDOWN: cuenta suspendida"); raise Breach("drawdown")
        if self.dll_active() and not self.dll_hit:
            day_pnl = self.day_realized + self.unrealized(price)
            if day_pnl <= -self.plan.dll:
                if self.pos: self._close(price, "DLL")
                self.dll_hit = True; self.events.append("DLL: trading desactivado hasta la siguiente sesion")

    def step_extreme(self, price: float):
        """Mueve el precio a 'price' (un extremo de la barra), activa TP/SL si corresponde y revisa reglas. Orden: reglas de cuenta -> bracket."""
        if not self.pos: return
        p = self.pos
        # bracket primero si se cruza ANTES de la regla de cuenta (el nivel del bracket esta entre el precio previo y 'price')
        if p.sl is not None and ((p.side == 1 and price <= p.sl) or (p.side == -1 and price >= p.sl)):
            self._check_at(p.sl)
            if self.pos: self._close(p.sl, "SL")
            return
        if p.tp is not None and ((p.side == 1 and price >= p.tp) or (p.side == -1 and price <= p.tp)):
            self._check_at(p.tp)
            if self.pos: self._close(p.tp, "TP")
            return
        self._check_at(price)

    def bar(self, high: float, low: float, close: float, prev_close: float):
        """Una barra: convencion O-L-H-C si cierra >= cierre previo, O-H-L-C si no (neutral). Devuelve True si sigue activa."""
        order = (low, high) if close >= prev_close else (high, low)
        for ext in order:
            if self.pos is None: break
            self.step_extreme(ext)
        if self.pos is not None:
            self._check_at(close)
        return self.status == "active"

    # ---------------- cierre del dia
    def end_of_day(self):
        if self.pos: raise Breach("posiciones abiertas al cierre (deben cerrarse antes de las 15:59 CT)")
        if self.status == "suspended": return
        pnl = self.day_realized
        if self.day_traded:
            self.trading_days += 1; self.cycle_days += 1
            self.best_day = max(self.best_day, pnl); self.cycle_best_day = max(self.cycle_best_day, pnl)
            wmin = payout_rules("momentum_master", self.size).win_day_min if self.stage == "momentum_master" else 150.0
            if pnl >= wmin: self.cycle_win_days += 1
        self.days.append(DayLog(pnl, self.day_traded, self.dll_hit))
        if self.plan.option == 2 and not self.locked:
            if self.balance > self.max_close:
                self.max_close = self.balance
                cap = self.lock_level if self.stage in ("master", "fast_track", "momentum_master") else float("inf")
                self.threshold = min(self.max_close - self.plan.drawdown, cap)
                if self.stage in ("master", "fast_track", "momentum_master") and self.max_close - self.plan.drawdown >= self.lock_level: self.locked = True
        self.peak_equity = max(self.peak_equity, self.balance)
        self.day_realized = 0.0; self.day_traded = False; self.dll_hit = False
        if self.stage in ("qualification",) and self.balance >= (self.plan.target or 1e18):
            self.status = "passed"

    # ---------------- pagos
    def _rules(self) -> PayoutRules:
        return payout_rules({"master": "master", "momentum_master": "momentum_master", "fast_track": "fast_track"}[self.stage], self.size)

    def payout_limits(self):
        """Devuelve (max_solicitable, motivo) segun la etapa; max_solicitable<=0 => no se puede solicitar."""
        r = self._rules(); n = self.pay_n
        cap = r.caps[min(n, len(r.caps) - 1)]
        cons = r.consistency[min(n, len(r.consistency) - 1)]
        cyc_profit = self.balance - self.cycle_start_balance
        if self.stage == "master":
            if self.cycle_days < r.days_required: return 0.0, f"faltan dias de trading ({self.cycle_days}/{r.days_required})"
            room = self.balance - r.min_balance
            if cyc_profit <= 0 or self.cycle_best_day > cons * cyc_profit: return 0.0, "consistencia 40% no cumplida"
        elif self.stage == "momentum_master":
            if self.cycle_win_days < r.days_required: return 0.0, f"faltan dias rentables ({self.cycle_win_days}/{r.days_required})"
            if self.balance < r.min_balance: return 0.0, "saldo minimo no alcanzado"
            if cyc_profit <= 0 or self.cycle_best_day > cons * cyc_profit: return 0.0, "consistencia 35% no cumplida"
            room = self.balance
        else:   # fast_track
            target = r.first_cycle_target if n == 0 else r.next_cycle_target
            if cyc_profit < target: return 0.0, "objetivo del ciclo no alcanzado"
            if cyc_profit <= 0 or self.cycle_best_day > cons * cyc_profit: return 0.0, f"consistencia {cons:.0%} no cumplida"
            room = (self.balance - (self.cycle_start_balance + target)) if n > 0 else (self.balance - (self.threshold + 1.0))
        amt = min(cap, room)
        return (amt, "ok") if amt >= r.min_request else (0.0, "monto disponible menor al minimo de solicitud")

    def request_payout(self, amount: Optional[float] = None) -> float:
        mx, why = self.payout_limits()
        if mx <= 0: raise Breach(why)
        amount = mx if amount is None else amount
        if amount > mx + 1e-9 or amount < self._rules().min_request - 1e-9: raise Breach("monto fuera de limites")
        net = split(self.paid_gross, amount, self._rules())
        self.paid_gross += amount; self.balance -= amount; self.pay_n += 1
        self.cycle_start_balance = self.balance; self.cycle_days = 0; self.cycle_win_days = 0
        if self.stage != "master": self.cycle_best_day = self.cycle_best_day if False else 0.0
        else: pass     # Master: el mejor dia NO se reinicia [HC master]
        return net
