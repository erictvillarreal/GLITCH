"""
Glitch — Opening Range Breakout (ORB) Strategy
================================================
Mecanica:
  1. Definir el "opening range" = high/low de los primeros N minutos
     tras la apertura de la sesion RTH (9:30 AM CT para el cash open de ES/MES,
     que es la ventana de mayor liquidez/volumen intradia).
  2. Señal LONG: primer cierre por encima del OR high.
     Señal SHORT: primer cierre por debajo del OR low.
  3. Un solo trade por lado por dia (evita overtrading / viola DLL rapido).
  4. Salida via triple-barrier (ATR-based TP/SL) ya existente en el repo.

Por que ORB:
  - Mecanico y objetivo (cero discrecion) -> facil de paper-tradear y auditar.
  - Encaja con la ventana de sesion CME ya definida en prop_firm.py.
  - Tipicamente WR 35-50% / RR 2-4, que es una de las zonas ganadoras
    identificadas en el grid search (ver find_geometry2.py).
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from dataclasses import dataclass


@dataclass
class ORBConfig:
    or_minutes: int = 15          # ventana del opening range (minutos)
    session_open_hour: int = 9    # 9:30 AM CT cash open (aprox, ver nota abajo)
    session_open_minute: int = 30
    max_entries_per_day: int = 2  # 1 long + 1 short posibles, no mas
    confirm_close: bool = True    # exigir CIERRE fuera del rango (no solo mecha)


def compute_opening_range(prices: pd.DataFrame, cfg: ORBConfig, tz: str = "America/Chicago"):
    """
    Calcula el OR high/low por dia de sesion.
    prices: DataFrame OHLCV con DatetimeIndex UTC (formato estandar del data/loader.py)
    Devuelve DataFrame indexado por fecha de sesion con columnas or_high, or_low, or_end_ts
    """
    local = prices.copy()
    local.index = local.index.tz_convert(tz)

    open_t = pd.Timestamp(f"{cfg.session_open_hour:02d}:{cfg.session_open_minute:02d}").time()
    end_t  = (pd.Timestamp(f"{cfg.session_open_hour:02d}:{cfg.session_open_minute:02d}")
              + pd.Timedelta(minutes=cfg.or_minutes)).time()

    local["session_date"] = local.index.date
    mask = (local.index.time >= open_t) & (local.index.time < end_t)
    or_window = local[mask]

    or_stats = or_window.groupby("session_date").agg(
        or_high=("high", "max"),
        or_low=("low", "min"),
    )
    or_stats["or_end_ts"] = [
        pd.Timestamp.combine(pd.Timestamp(d), end_t).tz_localize(tz)
        for d in or_stats.index
    ]
    return or_stats


def generate_orb_signals(prices: pd.DataFrame, cfg: ORBConfig = None, tz: str = "America/Chicago"):
    """
    Genera señales de entrada ORB.
    Devuelve DataFrame: entry_idx (posicion entera en `prices`), side (+1/-1), session_date
    """
    if cfg is None:
        cfg = ORBConfig()

    or_stats = compute_opening_range(prices, cfg, tz)

    local = prices.copy()
    local.index = local.index.tz_convert(tz)
    local["session_date"] = local.index.date
    local["pos"] = np.arange(len(local))

    signals = []
    for session_date, row in or_stats.iterrows():
        day_bars = local[(local["session_date"] == session_date) & (local.index > row["or_end_ts"])]
        if day_bars.empty:
            continue

        broke_long = False
        broke_short = False
        for _, bar in day_bars.iterrows():
            ref_price = bar["close"] if cfg.confirm_close else bar["high"]
            ref_price_low = bar["close"] if cfg.confirm_close else bar["low"]

            if not broke_long and ref_price > row["or_high"]:
                signals.append({"entry_idx": int(bar["pos"]), "side": 1, "session_date": session_date})
                broke_long = True
            if not broke_short and ref_price_low < row["or_low"]:
                signals.append({"entry_idx": int(bar["pos"]), "side": -1, "session_date": session_date})
                broke_short = True
            if broke_long and broke_short:
                break  # ya se dispararon ambos lados posibles (max_entries_per_day=2)

    return pd.DataFrame(signals)
