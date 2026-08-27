"""
Glitch — Camino B: Geometria Pura, agnostica de producto (25-ago-2026)
==========================================================================
UNICA fuente de verdad de la logica de decision de Camino B (entrada sin
señal predictiva, barreras fijas en ticks) -- importada tanto por
scheduler/geometry_scheduler.py (produccion/paper) como por cualquier
backtest futuro. Mismo patron que strategies/combo2d.py.

CEREBRO 1 (lo que este modulo resuelve) vs. CEREBRO 2 (pausado, NO
tocar) — diferencia critica:

Cerebro 1 = pasar el Combine. Objetivo: maximizar pass_rate/dias_resolucion
dentro de una ventana ACOTADA de 15 dias, con perdida limitada a la fee
del intento (~$49-149). La geometria de este modulo (Camino B) explota
que esta ventana acotada + perdida acotada permite pasar con alta
probabilidad AUNQUE la estrategia subyacente pierda dinero en promedio
(EV negativo neto de comision) -- la convexidad del payout hace el
trabajo, no una prediccion de mercado.

Cerebro 2 = maximizar payouts reales una vez fondeado (cuenta XFA).
Objetivo DISTINTO: el horizonte es INDEFINIDO (sin ventana de 15 dias que
acote el riesgo), y el umbral relevante no es "$3,000 acumulados" sino
"5 dias de >=$150 netos". Una estrategia con EV negativo o cero que
funciona para pasar el Combine NO sobrevive en Cerebro 2 -- sin la
ventana de tiempo que te protege, el MLL eventualmente alcanza cualquier
estrategia sin edge real positivo.

Cerebro 2 esta PAUSADO porque depende de una pregunta sin resolver: ¿el
MLL de la cuenta XFA se resetea a $0 SOLO la primera vez que se solicita
un payout, o CADA vez? Esto se reporto una vez (fuente: help.topstep.com,
cita parcial) pero NUNCA se verifico el texto completo ni la URL exacta
contra la fuente oficial. Son dos economias completamente distintas para
Cerebro 2 y no se puede diseñar nada confiable sin resolver esto primero.

Regla practica: si una tarea es sobre pasar el Combine (geometria de
ticks, combines_por_año, pass_rate_15d) es Cerebro 1 -- procede. Si es
sobre payouts, XFA, simulate_xfa_lifetime, o el colchon post-payout -- es
Cerebro 2 -- DETENTE y pregunta antes de avanzar, no asumas que el exito
de Cerebro 1 aplica ahi.

DISEÑO: agnostico de producto a proposito. Un ProductSpec + un
GeometryConfig describen TODO lo necesario para tradear cualquier
candidato validado (MES, GC/MGC, RTY/M2K, CL/MCL, 6E/M6E) -- cambiar
de producto es cambiar CANDIDATES[label], no reescribir logica.
"""
from __future__ import annotations
import datetime as dt
from dataclasses import dataclass

import numpy as np

# Epoch fijo para el contador de dias de trading -- NO es estado
# persistente (no se guarda en ningun archivo/DB). day_index(fecha) es
# una funcion pura de la fecha, asi que "alternar" da el mismo resultado
# sin importar reinicios del proceso, sin necesitar recordar nada.
_EPOCH = dt.date(2020, 1, 1)


def trading_day_index(d: dt.date) -> int:
    """Dias habiles (Mon-Fri) transcurridos desde un epoch fijo -- deterministico, sin estado."""
    return int(np.busday_count(_EPOCH, d))


def decide_side(day_index: int, direction: str) -> int:
    """
    Funcion de decision PURA de Camino B. NO hay señal predictiva --
    direction="alternate" es el default validado (ver GLITCH_RESEARCH_LOG.md,
    consolidacion Camino B: el sesgo direccional encontrado es ruido con
    signo consistente por azar en la mayoria de los productos, no edge real).

    direction: "alternate" | "always_long" | "always_short"
    """
    if direction == "always_long":
        return 1
    if direction == "always_short":
        return -1
    if direction == "alternate":
        return 1 if day_index % 2 == 0 else -1
    raise ValueError(f"direction invalida: {direction!r}")


@dataclass(frozen=True)
class ProductSpec:
    """Hechos de mercado/Topstep verificados contra fuente primaria (ver reporte 25-ago-2026)."""
    label: str            # nombre legible, ej. "MES"
    product_code: str     # codigo para resolve_front_month(), ej. "MES"
    tick_size: float       # en las MISMAS unidades que el feed de precios (ver nota ZC abajo)
    tick_value_usd: float  # $ por tick, 1 contrato -- fuente: help.topstep.com/commissions-and-fees
    commission_roundturn: float  # $ round-turn, 1 contrato -- misma fuente
    nc_cap: int            # limite real de contratos para cuenta 50K -- fuente: help.topstep.com
    familia: str
    yf_ticker: str | None = None  # simbolo continuo de yfinance para precio intradia en vivo.
    # None = NO VERIFICADO -- el scheduler debe negarse a correr ese producto
    # en vez de adivinar un simbolo. Solo MES esta verificado (mismo simbolo
    # ya usado y probado en scheduler/combo2d_scheduler.py).


@dataclass(frozen=True)
class GeometryConfig:
    """El resultado de una corrida de scripts/camino_b_grid.py o camino_b_products.py."""
    spec: ProductSpec
    sl_ticks: int
    tp_ticks: int
    max_holding_bars: int  # bars de 5min del backtest -- ver nota de traduccion a tiempo real abajo
    nc: int                 # <= spec.nc_cap, puede ser menor por margen de seguridad
    direction: str          # "alternate" (default validado) | "always_long" | "always_short"

    def barrier_prices(self, entry_price: float, side: int) -> tuple[float, float]:
        """(tp_price, sl_price) para una entrada a entry_price en la direccion `side`."""
        tp_price = entry_price + side * self.tp_ticks * self.spec.tick_size
        sl_price = entry_price - side * self.sl_ticks * self.spec.tick_size
        return tp_price, sl_price

    def dollar_tp_sl(self) -> tuple[float, float]:
        """($ TP, $ SL) para self.nc contratos -- para logging/alertas, no para el walk de barras."""
        tp_usd = self.tp_ticks * self.spec.tick_value_usd * self.nc
        sl_usd = self.sl_ticks * self.spec.tick_value_usd * self.nc
        return tp_usd, sl_usd


# ── Especificaciones verificadas (help.topstep.com, 25-ago-2026) ──────────
SPECS = {
    "MES":  ProductSpec("MES",            "MES", 0.25,     1.25,   1.22, 50, "Equity index", yf_ticker="MES=F"),
    "MGC":  ProductSpec("GC/MGC (Gold)",  "MGC", 0.10,     1.00,   1.92, 30, "Metales"),
    "M2K":  ProductSpec("RTY/M2K",        "M2K", 0.10,     0.50,   1.22, 50, "Equity index (control)"),
    "MCL":  ProductSpec("CL/MCL (Crude)", "MCL", 0.01,     1.00,   1.52, 30, "Energia"),
    "M6E":  ProductSpec("6E/M6E (EuroFX)","M6E", 0.0001,   1.25,   1.00, 50, "FX mayor"),
    "ZN":   ProductSpec("ZN (10Y Note)",  "ZN",  0.015625, 15.625, 2.62, 5,  "Tasas"),
    "ZC":   ProductSpec("ZC (Corn)",      "ZC",  0.25,     12.50,  5.28, 5,  "Agricola"),
}

# ── Candidatos validados (ver GLITCH_RESEARCH_LOG.md, consolidacion Camino B) ──
# Ganador: MES, 53.6 combines/año (backtest corrido sobre MES directamente,
# no MNQ -- ver camino_b_grid.py::TICK_VALUE_USD=1.25, el tick value real de
# MES). GC/MGC y RTY/M2K quedan en near-tie
# (~1.4% de diferencia) como alternativas -- cambiar CANDIDATES["MES"] por
# CANDIDATES["MGC"] o CANDIDATES["M2K"] es la unica accion necesaria para
# rotar de producto.
CANDIDATES = {
    "MES": GeometryConfig(SPECS["MES"], sl_ticks=100, tp_ticks=40, max_holding_bars=100, nc=40, direction="alternate"),
    "MGC": GeometryConfig(SPECS["MGC"], sl_ticks=136, tp_ticks=45, max_holding_bars=100, nc=30, direction="alternate"),
    "M2K": GeometryConfig(SPECS["M2K"], sl_ticks=200, tp_ticks=80, max_holding_bars=100, nc=50, direction="alternate"),
}

# NOTA (max_holding_bars): viene del backtest en barras de 5min. En vivo,
# el flatten obligatorio de fin de sesion de Topstep casi siempre llega
# primero (100 barras de 5min = ~8.3h, mas largo que una sesion RTH) --
# ver scheduler/geometry_scheduler.py, la barrera de tiempo real
# vinculante en produccion es el cierre de sesion, no max_holding_bars.
