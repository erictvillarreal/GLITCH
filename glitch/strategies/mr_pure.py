"""
Glitch — Mean-Reversion Dia-a-Dia PURA (solo MES, sin doble confirmacion)
============================================================================
Candidato SEPARADO de combo_2d (ver strategies/combo2d.py). Señal minima:
fade del retorno de sesion completa de ayer, sin condicion de T-2, sin
filtro de MNQ. Especificacion literal pedida en la auditoria del
25-ago-2026 para aislar si la discrepancia entre p=0.149 (candidato
original, MES puro) y p=0.4537 (combo_2d, MNQ+doble confirmacion) es
simplemente "son dos apuestas distintas" o un problema de reproducibilidad.

Señal: side = -sign(ret_prev), ret_prev = retorno open-to-close de la
sesion RTH de ayer. Sin umbral minimo de |ret_prev| (a diferencia de
combo_2d) -- especificacion literal, no una eleccion de diseño.
Entrada: apertura RTH del dia (misma convencion 9:30 local que el resto
del repo).
Ejecucion: MES (no hay instrumento secundario).
"""
from __future__ import annotations
import numpy as np
import pandas as pd

from strategies.combo2d import session_daily_returns, session_open_bar_positions


def generate_mr_pure_signal_table(mes_prices: pd.DataFrame) -> pd.DataFrame:
    """
    Tabla de señales para toda la historia disponible.
    Devuelve DataFrame indexado por session_date con columnas:
        side (1/-1), mes_entry_pos (posicion de barra en mes_prices)
    """
    mes_ret = session_daily_returns(mes_prices)
    mes_open_pos = session_open_bar_positions(mes_prices)

    dates = sorted(mes_ret.index)
    rows = []
    for i, d in enumerate(dates):
        if i < 1:
            continue
        d_prev = dates[i - 1]
        ret_prev = mes_ret[d_prev]
        side = -1 if ret_prev > 0 else (1 if ret_prev < 0 else 0)
        rows.append({"session_date": d, "side": side, "mes_entry_pos": int(mes_open_pos[d])})

    return pd.DataFrame(rows).set_index("session_date")
