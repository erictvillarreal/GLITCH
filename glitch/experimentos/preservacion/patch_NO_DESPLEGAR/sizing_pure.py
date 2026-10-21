"""PROPUESTA -- NO DESPLEGAR (NEEDS HUMAN REVIEW, CLAUDE.md regla 4: toca sizing de capital).

Sizing diario determinista de Camino B para el Combine ("finish-line"): usa todos los contratos configurados
mientras falta mucho para la meta y se achica solo cuando un TP del tamano configurado ya cubriria el faltante.

Reglas del fondo respetadas: funcion PURA y determinista (regla 1: nada de LLM en el camino de riesgo); solo REDUCE
el tamano respecto a CFG.nc (nunca lo aumenta, el cap sigue siendo la config validada); no toca SL/TP en ticks;
apagada por defecto (modo "fixed" = comportamiento actual).

Destino sugerido si Eric lo aprueba: glitch/strategies/sizing_pure.py (junto a geometry_pure.py).
"""
from __future__ import annotations

import math

MODES = ("fixed", "finish_line")


def tp_net_per_contract(tp_ticks: int, tick_value_usd: float, commission_roundturn: float, slip_ticks: float) -> float:
    """$ netos de un TP por contrato, con slippage de entrada adverso supuesto (el TP se ancla a la referencia, el fill entra peor)."""
    return (tp_ticks - slip_ticks) * tick_value_usd - commission_roundturn


def nc_for_day(mode: str, nc_cap: int, *, need_usd: float, tp_ticks: int, tick_value_usd: float,
               commission_roundturn: float, slip_assumed_ticks: float = 3.0) -> int:
    """Contratos para HOY. need_usd = profit_target - pnl acumulado del intento (puede ser <= 0 si ya paso: se opera 1)."""
    if mode not in MODES:
        raise ValueError(f"modo invalido: {mode!r}")
    if nc_cap < 1:
        raise ValueError("nc_cap debe ser >= 1")
    if mode == "fixed":
        return int(nc_cap)
    per = tp_net_per_contract(tp_ticks, tick_value_usd, commission_roundturn, slip_assumed_ticks)
    if per <= 0:
        return int(nc_cap)              # TP no cubre costos: no hay base para achicar, se conserva la config validada
    n = math.ceil(max(need_usd, 0.0) / per - 1e-9)
    return int(min(max(n, 1), nc_cap))
