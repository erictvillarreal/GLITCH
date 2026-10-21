"""PROPUESTA -- NO DESPLEGAR (NEEDS HUMAN REVIEW, CLAUDE.md regla 4: toca el registro de ejecucion).

C3: slippage REAL de entrada en ticks. Convencion: positivo = ADVERSO (peor que la referencia pre-trade con la que se anclan TP/SL).
  LONG compra en `fill` > `ref` -> adverso; SHORT vende en `fill` < `ref` -> adverso.   slip_ticks = side * (fill - ref) / tick_size
Calculo manual para cualquier dia (lun 19 / mar 20-oct): side * (precio de fill de TopstepX - referencia del mensaje [OPEN] del Pi) / 0.25.
"""
from __future__ import annotations

from typing import Optional


def slippage_ticks(side: int, ref_price: Optional[float], fill_price: Optional[float], tick_size: float) -> Optional[float]:
    if side not in (1, -1) or ref_price is None or fill_price is None or tick_size <= 0:
        return None
    for v in (ref_price, fill_price):
        if isinstance(v, bool) or not isinstance(v, (int, float)) or v <= 0:
            return None
    return round(side * (fill_price - ref_price) / tick_size, 2)
