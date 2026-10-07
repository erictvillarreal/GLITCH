"""Reglas de Bulenox como datos. Cada valor lleva su fuente: [HC] help center bulenox.com/es/help-center/<pagina>, [FAQ] bulenox.com/es/faq, [PDF] legal/Bulenox-Rates.pdf (actualizado 11-ago-2026),
[ToU] legal/Terms_of_Use.pdf, [USR] paginas de precios pegadas por el usuario (07/08-oct-2026). Lo NO confirmado queda en UNKNOWN. Leido el 08-oct-2026."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, Dict, Tuple

SIZES = (25_000, 50_000, 100_000, 150_000)
MICROS_PER_MINI = 10                 # [HC qualification] "Un contrato estandar equivale a diez micro contratos"
API_THIRD_PARTY_MONTHLY = 100.0      # [HC qualification, FAQ] "Si te conectas a Rithmic mediante una API de terceros o software compuesto, se aplican $100 adicionales al mes"
DATA_PRO_MONTHLY_PER_EXCHANGE = 112.0  # [HC connection] estado profesional: $112/mes por bolsa; no profesional: incluido
ACCESS_DAYS_CALENDAR = 30            # [USR/HC] "Acceso valido durante 30 dias"; el reinicio NO lo amplia [HC qualification]
ACCESS_TRADING_DAYS = 21             # aproximacion de 30 dias naturales
SESSION = "17:00 CT -> 16:00 CT; todas las posiciones cerradas antes de 15:59 CT; sin overnight; noticias permitidas"   # [HC, FAQ]

# comision por lado (USD, todo incluido) [PDF]; round-turn = 2x
COMMISSION_PER_SIDE = {"ES": 2.09, "NQ": 2.09, "RTY": 2.09, "YM": 2.09, "MES": 0.61, "MNQ": 0.61, "M2K": 0.61, "MYM": 0.61, "MBT": 2.76, "MET": 0.46,
                       "6E": 2.36, "M6E": 0.50, "M6A": 0.50, "M6B": 0.50, "CL": 2.26, "MCL": 0.76, "GC": 2.31, "MGC": 0.76, "HG": 2.31, "SI": 2.31, "NG": 2.26, "QG": 1.26}


def commission_rt(prod: str) -> float:
    return 2 * COMMISSION_PER_SIDE[prod]


@dataclass(frozen=True)
class Plan:
    name: str                       # "qualification" | "momentum" | "fast_track"
    option: int                     # 1 = drawdown dinamico (tiempo real, incluye no realizado), 2 = EOD (+ DLL; sin escalado en Momentum/Fast Track, escalado en Qualification)
    size: int
    price: float                    # pago unico [USR/HC]
    target: Optional[float]         # objetivo de beneficio (Qualification/Momentum) o del primer pago (Fast Track)
    drawdown: float
    dll: Optional[float]            # limite de perdida diaria (suave: pausa la jornada, no es infraccion) o None
    contracts: Tuple[int, ...]      # topes en minis: tupla de 1 elemento (fijo) o escalon por efectivo disponible (Qualification Opcion 2)
    scaling_breaks: Tuple[float, ...] = ()   # umbrales de efectivo disponible para escalar
    reset_fee: Optional[float] = 78.0        # [HC qualification]; SOLO documentado para Qualification (UNKNOWN para Momentum/Fast Track)
    master_activation: float = 0.0
    note: str = ""

    @property
    def max_micros(self) -> int:
        return max(self.contracts) * MICROS_PER_MINI

    def micros_cap(self, cash_on_hand: float) -> int:
        """Tope de micros dado el efectivo disponible (saldo - saldo inicial); la Opcion 2 de Qualification sube y baja con el efectivo [HC qualification/master]."""
        if len(self.contracts) == 1:
            return self.contracts[0] * MICROS_PER_MINI
        i = 0
        for b in self.scaling_breaks:
            if cash_on_hand > b: i += 1
        return self.contracts[i] * MICROS_PER_MINI


# --- Qualification [HC qualification + USR] -------------------------------------------------------------------------------------------------------------
_Q = {  # size: (price, target, dd_opt1, dd_opt2, dll_opt2, contracts_opt1(max), scaling opt2 tupla, breaks, master_dd, master_activation)
    25_000: (145, 1_500, 1_500, 1_500, 500, 3, (2, 3), (1_500,), 1_500, 143),
    50_000: (175, 3_000, 2_500, 2_500, 1_100, 7, (2, 4, 7), (1_500, 4_000), 2_500, 148),
    100_000: (215, 6_000, 3_000, 3_000, 2_200, 12, (3, 5, 8, 12), (2_000, 3_000, 5_000), 3_000, 248),
    150_000: (325, 9_000, 4_500, 4_500, 3_300, 15, (5, 8, 10, 15), (4_000, 8_000, 12_000), 4_500, 498),
}
# --- Momentum [HC momentum] ------------------------------------------------------------------------------------------------------------------------------
_M = {25_000: (94, 1_500, 1_000, 1_000, 600, 3, 2), 50_000: (143, 3_000, 2_250, 2_250, 1_200, 7, 4), 100_000: (248, 6_000, 4_000, 4_000, 2_500, 12, 8), 150_000: (358, 9_000, 5_500, 5_500, 3_300, 15, 12)}
# --- Fast Track [HC fast-track] --------------------------------------------------------------------------------------------------------------------------
_F = {25_000: (338, 1_500, 1_000, 1_000, None, 3, 2), 50_000: (488, 3_000, 2_250, 2_250, 1_200, 7, 4), 100_000: (648, 6_000, 4_000, 4_000, 2_500, 12, 8), 150_000: (788, 9_000, 5_500, 5_500, 3_300, 15, 12)}


def plan(name: str, size: int = 50_000, option: int = 2) -> Plan:
    if name == "qualification":
        price, tgt, dd1, dd2, dll, c1, sc, br, mdd, act = _Q[size]
        if option == 1:
            return Plan(name, 1, size, price, tgt, dd1, None, (c1,), master_activation=act, note="[USR] Trailing: contratos fijos, sin DLL; DD dinamico en tiempo real incl. no realizado y comisiones [HC]")
        return Plan(name, 2, size, price, tgt, dd2, dll, sc, br, master_activation=act, note="[HC] EOD + DLL + escalado por efectivo disponible")
    if name == "momentum":
        price, tgt, dd1, dd2, dll, c1, c2 = _M[size]
        if option == 1:
            return Plan(name, 1, size, price, tgt, dd1, None, (c1,), reset_fee=None, note="[HC momentum] Opcion 1: DD dinamico, contratos fijos; Master incluido y gratis")
        return Plan(name, 2, size, price, tgt, dd2, dll, (c2,), reset_fee=None, note="[HC momentum] Opcion 2: EOD, sin escalado; Master incluido y gratis")
    if name == "fast_track":
        price, tgt, dd1, dd2, dll, c1, c2 = _F[size]
        if option == 1:
            return Plan(name, 1, size, price, tgt, dd1, None, (c1,), reset_fee=None, note="[HC fast-track] sin evaluacion; DD dinamico; fondeada simulada desde el dia 1; lock +$100")
        return Plan(name, 2, size, price, tgt, dd2, dll, (c2,), reset_fee=None, note="[HC fast-track] sin evaluacion; EOD; DLL permanente; lock +$100")
    raise ValueError(name)


LOCK_OFFSET = 100.0                  # [HC fast-track/master] el drawdown se fija en saldo inicial + $100 (Master y Fast Track; en Qualification NO esta documentado -> UNKNOWN, se asume igual)


@dataclass(frozen=True)
class PayoutRules:
    kind: str                        # "master" | "momentum_master" | "fast_track"
    size: int
    min_request: float
    caps: Tuple[float, ...]          # tope por numero de pago (el ultimo se repite); inf = sin tope
    consistency: Tuple[float, ...]   # fraccion maxima del mejor dia sobre el beneficio neto del ciclo, por numero de pago (el ultimo se repite)
    days_required: int               # dias de trading (Master) o dias rentables (Momentum)
    win_day_min: float = 0.0
    min_balance: float = 0.0         # saldo minimo para solicitar (Momentum) o reserva de seguridad sobre el saldo inicial (Master)
    first_cycle_target: float = 0.0  # Fast Track
    next_cycle_target: float = 0.0   # Fast Track
    split_first_100: float = 10_000.0   # [FAQ/HC] primeros $10,000 pagados: 100% del trader; luego 90/10 (Fast Track: "contados una sola vez por trader en todas las cuentas Fast Track y Master")
    split_after: float = 0.90
    processing: str = ""


def payout_rules(kind: str, size: int = 50_000) -> PayoutRules:
    i = SIZES.index(size)
    if kind == "master":      # [HC master]
        return PayoutRules("master", size, 1_000.0, ((1_000.0, 1_500.0, 1_750.0, 2_000.0)[i],) * 3 + (float("inf"),), (0.40,), 10,
                           min_balance=(1_600.0, 2_600.0, 3_100.0, 4_600.0)[i], processing="semanal (miercoles); solicitud antes de vie 23:59 CT")
    if kind == "momentum_master":   # [HC momentum]
        caps = {25_000: (1_000.0,), 50_000: (1_500.0, 2_000.0, 2_500.0, 3_000.0), 100_000: (2_000.0, 2_500.0, 3_000.0, 4_000.0), 150_000: (2_500.0, 3_000.0, 4_000.0, 5_000.0)}[size]
        return PayoutRules("momentum_master", size, (500.0, 1_000.0, 1_000.0, 1_000.0)[i], caps, (0.35,), 5, win_day_min=(100.0, 150.0, 200.0, 250.0)[i],
                           min_balance=(26_500.0, 53_000.0, 104_500.0, 156_500.0)[i] - size, processing="diaria (mismo dia)")
    if kind == "fast_track":        # [HC fast-track]
        caps = {25_000: (1_000.0, 1_000.0, 1_000.0, 1_250.0), 50_000: (2_000.0, 2_000.0, 2_000.0, 2_500.0), 100_000: (2_500.0, 2_500.0, 2_500.0, 3_000.0), 150_000: (3_000.0, 3_000.0, 3_000.0, 3_500.0)}[size]
        return PayoutRules("fast_track", size, 1_000.0, caps, (0.20, 0.25, 0.30), 0, first_cycle_target=(1_500.0, 3_000.0, 6_000.0, 9_000.0)[i],
                           next_cycle_target=(1_000.0, 2_000.0, 3_000.0, 4_500.0)[i], processing="diaria (solicitud antes de 12:01 CT)")
    raise ValueError(kind)


def split(paid_gross_before: float, request: float, rules: PayoutRules) -> float:
    """Neto al trader de una solicitud: 100% mientras el acumulado pagado no pase de $10,000 y 90% del resto [FAQ]."""
    r100 = max(rules.split_first_100 - paid_gross_before, 0.0)
    return min(request, r100) + (request - min(request, r100)) * rules.split_after


MULTI_ACCOUNT = {"qualification_unlimited": True, "max_active_master_level": 5, "one_profile_one_rithmic_user": True, "balances_not_combined": True}   # [HC master/qualification, FAQ]
FUNDED_TRANSITION = {"after_payouts": 3, "discretionary": True, "profit_cap_per_master": {25_000: 2_500, 50_000: 5_000, 100_000: 10_000, 150_000: 15_000}, "total_cap": 30_000}   # [HC funded]
INACTIVITY = "Master: al menos una operacion por semana; >1 semana inactiva puede pausarse o deshabilitarse [HC master]"

UNKNOWN = [
    "Reinicio de Momentum y Fast Track (precio, si existe): solo hay $78 para Qualification [HC qualification]",
    "Reinicio de Qualification para tamanos distintos de 50K (el texto dice $78 sin distinguir)",
    "Lock del drawdown (+$100) durante la CALIFICACION: solo documentado para Master/Fast Track",
    "Drawdown/DLL/lock exactos del Momentum Master (se asume = parametros de su Opcion 2 + lock +$100)",
    "Descuento del cupon BULENOX (el usuario indica 'siempre activo'; monto desconocido, NO se aplica en los calculos)",
    "Si los algoritmos propios requieren aprobacion previa y si Pi/VPS esta permitido (ToU: 'any third party algorithms must be approved'; FAQ: solo herramientas propias)",
    "API: protocolo/costo exacto de la API de Rithmic para uso propio (R|Trader Pro y NinjaTrader son solo Windows)",
    "Reglas de la cuenta financiada real (live): permiten API/algoritmos?",
]
