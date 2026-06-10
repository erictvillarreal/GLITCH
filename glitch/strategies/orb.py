"""
Glitch — Opening Range Breakout (ORB) Strategy
===============================================
Entry logic:
  - Define the opening range: first N minutes after RTH open (9:30 AM CT)
  - Long signal:  price breaks ABOVE the opening range high
  - Short signal: price breaks BELOW the opening range low
  - One trade per day max
  - Exit via triple barrier (TP / SL / time)

Parameters to optimize:
  orb_minutes : width of opening range (5, 10, 15, 30)
  tp_atr_mult : take profit in ATR multiples
  sl_atr_mult : stop loss in ATR multiples
  atr_window  : ATR lookback period
  max_hold_bars : vertical barrier (time stop)
  direction   : "long", "short", "both"
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass


@dataclass
class ORBConfig:
    orb_minutes:    int   = 15      # opening range window
    tp_atr_mult:    float = 2.0     # take profit
    sl_atr_mult:    float = 1.0     # stop loss
    atr_window:     int   = 20      # ATR lookback
    max_hold_bars:  int   = 30      # time stop in bars
    direction:      str   = "both"  # "long", "short", "both"
    session_open:   str   = "09:30" # CT
    session_close:  str   = "14:30" # CT — no entries after this


def compute_atr(df: pd.DataFrame, window: int = 20) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low  - prev_close).abs(),
    ], axis=1).max(axis=1)
    return tr.rolling(window, min_periods=1).mean()


def generate_signals(
    df: pd.DataFrame,
    cfg: ORBConfig = None,
    tz: str = "America/Chicago",
) -> pd.DataFrame:
    """
    Scan all bars and return a DataFrame of entry signals.

    Input:  df with DatetimeIndex (UTC), columns: open high low close volume
    Output: DataFrame with columns:
              entry_idx    (integer position in df)
              entry_bar    (timestamp)
              direction    (+1 long / -1 short)
              entry_price
              orb_high
              orb_low
              atr
    """
    if cfg is None:
        cfg = ORBConfig()

    # Work in CT for session logic
    local = df.copy()
    local.index = local.index.tz_convert(tz)

    atr = compute_atr(local, cfg.atr_window)

    open_time  = pd.Timestamp(f"1970-01-01 {cfg.session_open}").time()
    close_time = pd.Timestamp(f"1970-01-01 {cfg.session_close}").time()

    signals = []
    dates = local.index.normalize().unique()

    for date in dates:
        day_mask = local.index.normalize() == date
        day = local[day_mask]

        if len(day) < cfg.orb_minutes + 1:
            continue

        # Opening range bars: first N minutes after 9:30
        orb_mask = (
            (day.index.time >= open_time) &
            (day.index.time <  pd.Timestamp(f"1970-01-01 {cfg.session_open}")
                               .time().__class__(
                                   (pd.Timestamp(f"1970-01-01 {cfg.session_open}") +
                                    pd.Timedelta(minutes=cfg.orb_minutes)).hour,
                                   (pd.Timestamp(f"1970-01-01 {cfg.session_open}") +
                                    pd.Timedelta(minutes=cfg.orb_minutes)).minute
                               ))
        )
        orb_bars = day[orb_mask]

        if len(orb_bars) < 2:
            continue

        orb_high = orb_bars["high"].max()
        orb_low  = orb_bars["low"].min()
        orb_range = orb_high - orb_low

        if orb_range <= 0:
            continue

        # Scan bars AFTER the opening range for breakout
        post_orb = day[day.index > orb_bars.index[-1]]
        post_orb = post_orb[post_orb.index.time <= close_time]

        traded_today = False

        for bar_time, bar in post_orb.iterrows():
            if traded_today:
                break

            bar_atr = atr.loc[bar_time] if bar_time in atr.index else orb_range

            # Long breakout
            if cfg.direction in ("long", "both"):
                if bar["close"] > orb_high:
                    # Find integer position in original df
                    bar_utc = bar_time.tz_convert("UTC")
                    if bar_utc in df.index:
                        idx = df.index.get_loc(bar_utc)
                        signals.append({
                            "entry_idx":   idx,
                            "entry_bar":   bar_utc,
                            "direction":   1,
                            "entry_price": bar["close"],
                            "orb_high":    orb_high,
                            "orb_low":     orb_low,
                            "atr":         bar_atr,
                        })
                        traded_today = True

            # Short breakout
            if cfg.direction in ("short", "both") and not traded_today:
                if bar["close"] < orb_low:
                    bar_utc = bar_time.tz_convert("UTC")
                    if bar_utc in df.index:
                        idx = df.index.get_loc(bar_utc)
                        signals.append({
                            "entry_idx":   idx,
                            "entry_bar":   bar_utc,
                            "direction":   -1,
                            "entry_price": bar["close"],
                            "orb_high":    orb_high,
                            "orb_low":     orb_low,
                            "atr":         bar_atr,
                        })
                        traded_today = True

    if not signals:
        return pd.DataFrame()

    return pd.DataFrame(signals).set_index("entry_bar")
