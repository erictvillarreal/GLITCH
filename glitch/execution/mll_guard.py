"""
Glitch — Guardia de colchon del MLL (J4-a, 26-oct-2026; NEEDS HUMAN REVIEW; APAGADA por defecto)
=================================================================================================
Funciones PURAS y deterministas (CLAUDE.md regla 1: ningun limite de riesgo duro es una llamada a un LLM). Dado el colchon actual de la cuenta
(balance − piso del MLL), limita el numero de contratos a los que caben con su pérdida maxima DENTRO del colchon; si no cabe ni uno, bloquea la entrada.

ADVERTENCIA (resultado del modelo, J4-a): como regla de TAMAÑO esta guardia BAJA el cobrado esperado por XFA (−$77 a −$226 segun la variante, diferencias
distinguibles; ver parteJ/resultados_J4a.md) porque una cuenta que ya no puede operar no cobra. Se entrega para que Eric decida SI quiere priorizar la
supervivencia de la cuenta sobre el cobro; no se recomienda encenderla por defecto.
"""
from __future__ import annotations

import math


def risk_per_contract(sl_ticks: int, tick_usd: float, fee_usd: float, margin_ticks: float = 3.0) -> float:
    """Perdida maxima por contrato: SL + comision round-turn + margen de slippage de salida (en ticks)."""
    return sl_ticks * tick_usd + fee_usd + margin_ticks * tick_usd


def cushion_usd(balance: float, floor: float) -> float:
    """Colchon = balance − piso del MLL (ambos absolutos, en USD). Nunca negativo."""
    return max(float(balance) - float(floor), 0.0)


def max_contracts_for_cushion(cushion: float, sl_ticks: int, tick_usd: float, fee_usd: float, margin_ticks: float = 3.0) -> int:
    """Mayor numero de contratos cuya perdida maxima conjunta cabe ESTRICTAMENTE dentro del colchon (0 si no cabe ni uno)."""
    r = risk_per_contract(sl_ticks, tick_usd, fee_usd, margin_ticks)
    if r <= 0 or cushion <= 0:
        return 0
    n = math.floor(cushion / r)
    return int(n - 1) if n * r >= cushion else int(n)          # estricto: si el colchon es exactamente n·r, n contratos lo liquidarian justo


def decide(nc_requested: int, cushion: float, sl_ticks: int, tick_usd: float, fee_usd: float, margin_ticks: float = 3.0):
    """(nc_permitido, motivo). nc_permitido = 0 significa BLOQUEAR la entrada de hoy."""
    allowed = max_contracts_for_cushion(cushion, sl_ticks, tick_usd, fee_usd, margin_ticks)
    nc = min(int(nc_requested), allowed)
    if nc >= nc_requested:
        return nc_requested, "ok"
    if nc <= 0:
        return 0, f"colchon ${cushion:,.0f} < perdida maxima de 1 contrato (${risk_per_contract(sl_ticks, tick_usd, fee_usd, margin_ticks):,.0f})"
    return nc, f"colchon ${cushion:,.0f}: se reduce de {nc_requested} a {nc} contratos"
