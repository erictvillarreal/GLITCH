"""
Glitch — Triple Barrier Labeling (de Prado 2018)
=================================================
Labels each entry signal with one of three outcomes:
  +1  upper barrier hit (take profit)
  -1  lower barrier hit (stop loss)
   0  vertical barrier hit (time / max holding)

This is the industry-standard method for financial ML labeling.
It avoids look-ahead bias because labels are generated causally.

Used here to:
  1. Convert raw OHLCV bars into labeled training examples
  2. Feed win_rate / avg_win / avg_loss into the Monte Carlo engine
  3. Validate that a strategy has out-of-sample edge before paying
     for any Combine

References:
  de Prado, M.L. (2018). Advances in Financial Machine Learning.
  Chapter 3: Labeling.
"""

from __future__ import annotations
import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass
class BarrierConfig:
    """Barrier settings for labeling."""
    pt_multiplier: float = 2.0    # Take profit = pt_multiplier * volatility
    sl_multiplier: float = 1.0    # Stop loss   = sl_multiplier * volatility
    max_holding_bars: int = 20    # Vertical (time) barrier
    volatility_window: int = 20   # Lookback for ATR / rolling std
    use_atr: bool = True           # True = ATR, False = rolling close std


def compute_atr(high: np.ndarray, low: np.ndarray, close: np.ndarray,
                window: int = 20) -> np.ndarray:
    """Average True Range."""
    tr = np.maximum(
        high - low,
        np.maximum(
            np.abs(high - np.roll(close, 1)),
            np.abs(low  - np.roll(close, 1))
        )
    )
    tr[0] = high[0] - low[0]
    atr = pd.Series(tr).rolling(window, min_periods=1).mean().values
    return atr


def label_triple_barrier(
    prices: pd.DataFrame,          # Must have columns: open, high, low, close
    signal_indices: np.ndarray,    # Bar indices where we enter (integer positions)
    cfg: BarrierConfig = None,
    side: int = 1,                 # +1 long, -1 short
) -> pd.DataFrame:
    """
    Apply triple barrier labeling to a set of entry signals.

    Parameters
    ----------
    prices : DataFrame with OHLC columns
    signal_indices : array of integer bar positions where entries occur
    cfg : BarrierConfig
    side : trade direction (+1 long, -1 short)

    Returns
    -------
    DataFrame with columns:
        entry_idx, entry_price, exit_idx, exit_price,
        label (+1/-1/0), pnl_pct, holding_bars,
        upper_barrier, lower_barrier
    """
    if cfg is None:
        cfg = BarrierConfig()

    close = prices["close"].values
    high  = prices["high"].values
    low   = prices["low"].values

    # Compute volatility at each bar
    if cfg.use_atr:
        vol = compute_atr(high, low, close, cfg.volatility_window)
    else:
        vol = pd.Series(close).pct_change().rolling(cfg.volatility_window).std().values
        vol = np.abs(vol * close)   # Convert to price units
        vol = np.nan_to_num(vol, nan=close * 0.001)

    records = []
    n = len(prices)

    for entry_i in signal_indices:
        entry_i = int(entry_i)
        if entry_i >= n - 1:
            continue

        entry_price = close[entry_i]
        v = vol[entry_i]

        upper = entry_price + side * cfg.pt_multiplier * v
        lower = entry_price - side * cfg.sl_multiplier * v

        label        = 0
        exit_price   = entry_price
        exit_i       = min(entry_i + cfg.max_holding_bars, n - 1)

        # Walk bars forward to find first barrier touch
        for j in range(entry_i + 1, exit_i + 1):
            h, l = high[j], low[j]

            if side == 1:   # Long
                if h >= upper:
                    label = 1;  exit_price = upper; exit_i = j; break
                if l <= lower:
                    label = -1; exit_price = lower; exit_i = j; break
            else:            # Short
                if l <= upper:
                    label = 1;  exit_price = upper; exit_i = j; break
                if h >= lower:
                    label = -1; exit_price = lower; exit_i = j; break
        else:
            # BUGFIX (12-ago-2026): si el loop termina SIN hacer break (no toco
            # ni TP ni SL dentro de max_holding_bars), exit_price se quedaba
            # pegado a entry_price -> todo trade "time-barrier" se registraba
            # con PnL exactamente $0, sin importar el precio real de salida.
            # Fix: usar el close real de la barra de vencimiento (exit_i).
            exit_price = close[exit_i]

        pnl_pct = side * (exit_price - entry_price) / entry_price

        records.append({
            "entry_idx":    entry_i,
            "entry_price":  entry_price,
            "exit_idx":     exit_i,
            "exit_price":   exit_price,
            "label":        label,
            "pnl_pct":      pnl_pct,
            "pnl_usd":      pnl_pct * entry_price,  # per unit
            "holding_bars": exit_i - entry_i,
            "upper_barrier": upper,
            "lower_barrier": lower,
            "volatility":   v,
        })

    if not records:
        return pd.DataFrame()

    return pd.DataFrame(records)


def extract_daily_pnl_from_labels(
    labels: pd.DataFrame,
    prices: pd.DataFrame,
    point_value_usd: float = 5.0,   # MES=$5/pt, MNQ=$2/pt (ver INSTRUMENT_SPECS)
    n_contracts: int = 1,
) -> np.ndarray:
    """
    Aggregate labeled trades into a daily PnL series.

    BUGFIX (12-ago-2026): version anterior usaba un "contract_value_per_pct"
    fijo para todo el dataset, asumiendo un nivel de precio constante
    (ej. MES~5000). Si el precio real se mueve mucho durante la ventana del
    backtest (MES paso de ~5000 a ~7690 en el dataset real), esa constante
    queda mal calibrada. Fix: usar el entry_price REAL de cada trade.
    """
    if labels.empty:
        return np.array([])

    labels = labels.copy()
    labels["date"] = pd.to_datetime(prices.index[labels["entry_idx"].astype(int)]).normalize()
    labels["pnl_points"] = labels["pnl_pct"] * labels["entry_price"]
    labels["pnl_dollar"] = labels["pnl_points"] * point_value_usd * n_contracts

    daily = labels.groupby("date")["pnl_dollar"].sum()
    return daily.values


# ── Walk-forward validation ────────────────────────────────────────────────

def walk_forward_validate(
    prices: pd.DataFrame,
    signal_fn,                   # function(prices_window) -> signal_indices
    cfg: BarrierConfig = None,
    train_bars: int = 252,       # ~1 year of daily bars
    test_bars: int = 63,         # ~1 quarter
    min_trades: int = 30,        # Minimum trades per window for statistical validity
    side: int = 1,
) -> pd.DataFrame:
    """
    Causal walk-forward validation of a signal generator.

    Splits data into rolling train/test windows.
    Signal is fitted on train, evaluated on test.
    NO LOOK-AHEAD BIAS: test window always follows train window in time.

    Returns DataFrame with per-fold metrics:
        fold, train_start, test_start, test_end,
        n_trades, win_rate, avg_win, avg_loss, rr,
        ev_per_trade, sharpe
    """
    if cfg is None:
        cfg = BarrierConfig()

    n = len(prices)
    folds = []
    fold_num = 0

    i = train_bars
    while i + test_bars <= n:
        train_prices = prices.iloc[i - train_bars : i]
        test_prices  = prices.iloc[i : i + test_bars]

        # Generate signals on test window using model fitted on train
        try:
            test_signals = signal_fn(train_prices, test_prices)
        except Exception as e:
            i += test_bars
            fold_num += 1
            continue

        if len(test_signals) < min_trades:
            i += test_bars
            fold_num += 1
            continue

        # Label test trades
        # Shift signal indices to be relative to full prices frame
        global_signals = np.array(test_signals) + i
        full_labels = label_triple_barrier(prices, global_signals, cfg, side)

        if full_labels.empty or len(full_labels) < min_trades:
            i += test_bars
            fold_num += 1
            continue

        wins   = full_labels[full_labels["label"] ==  1]["pnl_usd"]
        losses = full_labels[full_labels["label"] == -1]["pnl_usd"].abs()
        all_pnl = full_labels["pnl_usd"]

        n_trades  = len(full_labels)
        win_rate  = len(wins) / n_trades
        avg_win   = float(wins.mean())   if len(wins) > 0 else 0.0
        avg_loss  = float(losses.mean()) if len(losses) > 0 else 0.0
        ev        = float(all_pnl.mean())
        sharpe    = ev / all_pnl.std() * np.sqrt(252) if all_pnl.std() > 0 else 0.0

        folds.append({
            "fold":         fold_num,
            "train_start":  train_prices.index[0],
            "test_start":   test_prices.index[0],
            "test_end":     test_prices.index[-1],
            "n_trades":     n_trades,
            "win_rate":     round(win_rate, 4),
            "avg_win":      round(avg_win, 2),
            "avg_loss":     round(avg_loss, 2),
            "rr":           round(avg_win / avg_loss, 3) if avg_loss > 0 else 0.0,
            "ev_per_trade": round(ev, 2),
            "sharpe":       round(sharpe, 3),
        })

        i += test_bars
        fold_num += 1

    return pd.DataFrame(folds)


def statistical_summary(wf_df: pd.DataFrame) -> dict:
    """
    Compute statistical significance of walk-forward results.
    Tests whether mean EV per trade is significantly > 0 (one-sided t-test).
    """
    from scipy import stats as scipy_stats

    evs = wf_df["ev_per_trade"].values
    t_stat, p_two = scipy_stats.ttest_1samp(evs, 0)
    p_one = p_two / 2 if t_stat > 0 else 1.0

    return {
        "n_folds":         len(wf_df),
        "total_trades":    int(wf_df["n_trades"].sum()),
        "mean_ev":         round(float(evs.mean()), 3),
        "std_ev":          round(float(evs.std()), 3),
        "t_statistic":     round(t_stat, 3),
        "p_value_one_sided": round(p_one, 4),
        "significant_5pct": p_one < 0.05,
        "significant_1pct": p_one < 0.01,
        "mean_win_rate":   round(float(wf_df["win_rate"].mean()), 4),
        "mean_rr":         round(float(wf_df["rr"].mean()), 3),
        "mean_sharpe":     round(float(wf_df["sharpe"].mean()), 3),
        "min_fold_trades": int(wf_df["n_trades"].min()),
    }
