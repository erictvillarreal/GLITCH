"""
Glitch — Combo2d Mean-Reversion Dia-a-Dia (MES+MNQ doble confirmacion)
========================================================================
UNICA fuente de verdad de la logica de decision combo_2d (25-ago-2026,
post-auditoria). `decide_side()` es importada directamente por
scheduler/combo2d_scheduler.py (produccion/paper) Y por
generate_combo2d_signal_table() de este mismo modulo (backtest) — antes
eran dos copias inline de la misma logica que podian divergir en
silencio. Ver tests/test_combo2d_parity.py.

Señal: -sign(ret_prev) cuando sign(ret_2d) != sign(ret_prev) EN AMBOS
       instrumentos (MES y MNQ), y ambas direcciones coinciden.
Entrada: apertura RTH del dia (primera barra >= 9:30 CT, convencion ya
         usada en ORBConfig/combo2d_scheduler.py de este repo).
Ejecucion: sobre MNQ (el scheduler tradea MNQ usando MES como confirmacion).

NOTA: ret_prev/ret_2d aqui se calculan como (close_sesion - open_sesion) /
open_sesion por dia — el mismo calculo open-to-close intradiario que usa
compute_signal() en combo2d_scheduler.py (via fetch_daily), NO un retorno
close-to-close entre dias.
"""
from __future__ import annotations
import numpy as np
import pandas as pd


def decide_side(mes_ret_prev: float, mes_ret_2d: float,
                 mnq_ret_prev: float, mnq_ret_2d: float) -> tuple[int, str]:
    """
    Funcion de decision PURA de combo_2d (sin I/O, sin fechas) — dado el
    retorno open-to-close de ayer (T-1) y anteayer (T-2) para MES y MNQ,
    devuelve (side, reason).

    side: 1 (long), -1 (short), 0 (no trade)

    Extraida bit-a-bit de compute_signal() en scheduler/combo2d_scheduler.py
    (version original, previa a este refactor) — NO reimplementada desde la
    descripcion, copiada de la logica que ya corria en Railway.
    """
    mes_ok = np.sign(mes_ret_2d) != np.sign(mes_ret_prev) and abs(mes_ret_prev) > 0.0001
    mnq_ok = np.sign(mnq_ret_2d) != np.sign(mnq_ret_prev) and abs(mnq_ret_prev) > 0.0001

    if not mes_ok:
        return 0, f"mes_no_signal (ret_2d={mes_ret_2d:.4f} ret_prev={mes_ret_prev:.4f})"
    if not mnq_ok:
        return 0, f"mnq_no_confirm (ret_2d={mnq_ret_2d:.4f} ret_prev={mnq_ret_prev:.4f})"

    mes_side = 1 if mes_ret_2d > 0 else -1
    mnq_side = 1 if mnq_ret_2d > 0 else -1

    if mes_side != mnq_side:
        return 0, f"direccion_discrepante (mes={mes_side} mnq={mnq_side})"

    return mes_side, f"combo_2d_confirmed (mes_2d={mes_ret_2d:.4f} mes_prev={mes_ret_prev:.4f})"


def session_daily_returns(prices: pd.DataFrame, tz: str = "America/Chicago") -> pd.Series:
    """
    Retorno open-to-close por sesion RTH, indexado por fecha de sesion.
    prices: DataFrame OHLC con DatetimeIndex UTC, ya filtrado a RTH.
    """
    local = prices.copy()
    local.index = local.index.tz_convert(tz)
    local["session_date"] = local.index.date
    daily = local.groupby("session_date").agg(
        day_open=("open", "first"),
        day_close=("close", "last"),
    )
    daily["ret"] = (daily["day_close"] - daily["day_open"]) / daily["day_open"]
    return daily["ret"]


def session_open_bar_positions(prices: pd.DataFrame, tz: str = "America/Chicago",
                                open_hour: int = 9, open_minute: int = 30) -> pd.Series:
    """Posicion (integer, 0-indexed) de la primera barra >= open_hour:open_minute local, por sesion."""
    local = prices.copy()
    local.index = local.index.tz_convert(tz)
    local["session_date"] = local.index.date
    open_t = pd.Timestamp(f"{open_hour:02d}:{open_minute:02d}").time()
    local["pos"] = np.arange(len(local))
    after_open = local[local.index.time >= open_t]
    first_pos = after_open.groupby("session_date")["pos"].min()
    return first_pos


def generate_combo2d_signal_table(mes_prices: pd.DataFrame, mnq_prices: pd.DataFrame) -> pd.DataFrame:
    """
    Genera la tabla completa de señales combo_2d sobre toda la historia
    disponible (sin walk-forward — eso se aplica despues filtrando por fecha).

    Devuelve DataFrame indexado por session_date con columnas:
        side (1/-1/0), mnq_entry_pos (posicion de barra en mnq_prices)
    """
    mes_ret = session_daily_returns(mes_prices)
    mnq_ret = session_daily_returns(mnq_prices)
    mnq_open_pos = session_open_bar_positions(mnq_prices)

    dates = sorted(set(mes_ret.index) & set(mnq_ret.index) & set(mnq_open_pos.index))
    rows = []
    for i, d in enumerate(dates):
        if i < 2:
            continue
        d_prev, d_2d = dates[i - 1], dates[i - 2]
        mes_prev, mes_2d = mes_ret[d_prev], mes_ret[d_2d]
        mnq_prev, mnq_2d = mnq_ret[d_prev], mnq_ret[d_2d]

        side, reason = decide_side(mes_prev, mes_2d, mnq_prev, mnq_2d)

        rows.append({"session_date": d, "side": side, "reason": reason,
                      "mnq_entry_pos": int(mnq_open_pos[d])})

    return pd.DataFrame(rows).set_index("session_date")
