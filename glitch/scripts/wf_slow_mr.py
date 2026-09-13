"""
Glitch — Cerebro 2 (pivote a edge real): mean-reversion en timeframes
LENTOS -- diario con holding multi-dia, y semanal (04-sep-2026)
========================================================================
Rama cerebro2-dev. Primera direccion del pivote de Cerebro 2 hacia
busqueda de edge real (ver GLITCH_RESEARCH_LOG.md) -- nunca explorada
con este rigor en la sesion: toda la investigacion de MES intradia usaba
barras de 5min con holding de 1 dia (combo_2d, mr_pure). Aqui se prueba
si un edge modesto pero REAL sobrevive a un horizonte de holding mas
largo (dias en vez de barras de 5min), donde Cerebro 2 no necesita
velocidad (a diferencia del Combine) -- solo necesita que la señal sea
estadisticamente real.

Reutiliza TODA la infraestructura ya construida y auditada:
  - simulation/triple_barrier.py (label_triple_barrier, BarrierConfig,
    con el fix de barras ambiguas ya aplicado)
  - la misma metodologia de walk-forward por folds secuenciales +
    t-test OOS que scripts/wf_mr_pure.py y scripts/wf_combo2d.py
    (regla FIJA, no se "entrena" -- cada fold es una muestra OOS
    independiente, no train/test en el sentido de ML)
  - strategies/combo2d.py::session_daily_returns() para el resample a
    barras DIARIAS (mismo criterio de sesion RTH/tz Chicago que el
    resto del repo)

Dos hipotesis, EXACTAMENTE la misma logica de fade ya usada para MR
diaria intradia (side = -sign(ret_prev)), pero:
  A) "daily_multiday_hold": señal diaria (fade el retorno del dia
     anterior), holding de H dias (no 1 dia como en combo_2d/mr_pure)
  B) "weekly": señal semanal (fade el retorno acumulado de los ultimos
     5 dias habiles), holding de H dias

Entradas NO solapadas (spacing fijo de H dias entre señales
consecutivas) -- evita que trades adyacentes compartan la mayor parte
de su periodo de holding, que rompe la independencia asumida por el
t-test entre folds (mismo espiritu que "reshuffle por dias, no por
trades" pedido explicitamente).

Barreras: ATR de 20 barras DIARIAS (no 5min), pt=2.5x/sl=1.5x -- misma
convencion ya usada en wf_mr_pure.py/wf_combo2d.py, aplicada aqui a la
escala diaria en vez de intradia.
"""
from __future__ import annotations
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd
from scipy import stats as scipy_stats

from simulation.triple_barrier import BarrierConfig, label_triple_barrier

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data_cache")
TZ = "America/Chicago"

CFG = BarrierConfig(pt_multiplier=2.5, sl_multiplier=1.5, max_holding_bars=None, volatility_window=20, use_atr=True)
FOLD_DAYS = 126          # ~6 meses de barras diarias (recalibrado de 63 -- con ~500 barras
                          # diarias totales en 2 años, 63 daria folds demasiado angostos)
MIN_TRADES_PER_FOLD = 3  # recalibrado hacia abajo -- señales lentas son necesariamente
                          # mucho menos frecuentes que intradia, ver caveat de N en el reporte


def resample_daily(prices_5min: pd.DataFrame) -> pd.DataFrame:
    """OHLC diario por sesion RTH (tz Chicago), mismo criterio de
    agrupacion por session_date que strategies/combo2d.py."""
    local = prices_5min.copy()
    local.index = local.index.tz_convert(TZ)
    local["session_date"] = local.index.date
    daily = local.groupby("session_date").agg(
        open=("open", "first"), high=("high", "max"),
        low=("low", "min"), close=("close", "last"),
    )
    daily.index = pd.to_datetime(daily.index)
    return daily


def make_signal_indices(daily: pd.DataFrame, lookback_days: int, hold_days: int,
                         direction: str = "fade") -> np.ndarray:
    """
    direction="fade": side = -sign(retorno acumulado de los ultimos
    `lookback_days` dias, terminando AYER) -- mean-reversion.
    direction="momentum": side = +sign(...) -- continuacion. Sin umbral
    minimo (misma especificacion literal que mr_pure.py). Entradas
    espaciadas al menos `hold_days` entre si (no solapadas).
    """
    close = daily["close"].values
    n = len(daily)
    signals = []  # (entry_idx, side)
    last_exit = -1
    sign_mult = -1 if direction == "fade" else 1
    for i in range(lookback_days, n - 1):
        if i <= last_exit:
            continue
        ret = (close[i] - close[i - lookback_days]) / close[i - lookback_days]
        if ret == 0:
            continue
        side = sign_mult * (1 if ret > 0 else -1)
        signals.append((i, side))
        last_exit = i + hold_days
    return np.array(signals)


def run_fold_walk_forward(daily: pd.DataFrame, lookback_days: int, hold_days: int, direction: str = "fade") -> pd.DataFrame:
    cfg = BarrierConfig(pt_multiplier=CFG.pt_multiplier, sl_multiplier=CFG.sl_multiplier,
                         max_holding_bars=hold_days, volatility_window=CFG.volatility_window, use_atr=True)
    sig = make_signal_indices(daily, lookback_days, hold_days, direction)
    if len(sig) == 0:
        return pd.DataFrame()
    entries, sides = sig[:, 0].astype(int), sig[:, 1].astype(int)

    n = len(daily)
    folds = []
    fold_num = 0
    i = 0
    while i + FOLD_DAYS <= n:
        fold_mask = (entries >= i) & (entries < i + FOLD_DAYS)
        fold_entries = entries[fold_mask]
        fold_sides = sides[fold_mask]
        if len(fold_entries) < MIN_TRADES_PER_FOLD:
            i += FOLD_DAYS
            fold_num += 1
            continue

        longs = fold_entries[fold_sides == 1]
        shorts = fold_entries[fold_sides == -1]
        labels_l = label_triple_barrier(daily, longs, cfg, side=1) if len(longs) else pd.DataFrame()
        labels_s = label_triple_barrier(daily, shorts, cfg, side=-1) if len(shorts) else pd.DataFrame()
        full_labels = pd.concat([labels_l, labels_s], ignore_index=True) if len(labels_l) or len(labels_s) else pd.DataFrame()

        if full_labels.empty or len(full_labels) < MIN_TRADES_PER_FOLD:
            i += FOLD_DAYS
            fold_num += 1
            continue

        wins = full_labels[full_labels["label"] == 1]["pnl_pct"]
        losses = full_labels[full_labels["label"] == -1]["pnl_pct"].abs()
        time_exits = full_labels[full_labels["label"] == 0]["pnl_pct"]
        all_pnl = full_labels["pnl_pct"]

        n_trades = len(full_labels)
        # win_rate clasico (solo TP limpio) SUBESTIMA cuando hay muchos
        # time-exits (label=0, ni TP ni SL tocado en hold_days) -- con
        # hold_days chico (3-5) esto es la MAYORIA de los trades aqui, no
        # una minoria. La metrica que SI es correcta pase lo que pase es
        # ev_per_trade (usa el pnl real de TODOS los trades, incluidos
        # los de time-exit) -- ver n_tp/n_sl/n_time abajo para no leer
        # "win_rate" como si fuera comparable al WR de un sistema donde
        # casi todo resuelve por TP/SL limpio (ej. combo_2d intradia).
        win_rate = len(wins) / n_trades
        avg_win = float(wins.mean()) if len(wins) > 0 else 0.0
        avg_loss = float(losses.mean()) if len(losses) > 0 else 0.0
        ev = float(all_pnl.mean())

        folds.append({
            "fold": fold_num, "test_start": daily.index[i], "test_end": daily.index[min(i + FOLD_DAYS, n) - 1],
            "n_trades": n_trades, "n_tp": len(wins), "n_sl": len(losses), "n_time_exit": len(time_exits),
            "win_rate_tp_only": round(win_rate, 4),
            "avg_win_pct": round(avg_win * 100, 4), "avg_loss_pct": round(avg_loss * 100, 4),
            "avg_time_exit_pct": round(float(time_exits.mean() * 100), 4) if len(time_exits) else 0.0,
            "ev_per_trade_pct": round(ev * 100, 4),
        })
        i += FOLD_DAYS
        fold_num += 1

    return pd.DataFrame(folds)


def summarize(wf_df: pd.DataFrame, label: str) -> dict:
    if wf_df.empty or len(wf_df) < 2:
        return {"label": label, "n_folds": len(wf_df), "total_trades": int(wf_df["n_trades"].sum()) if not wf_df.empty else 0,
                "p_value_one_sided": None, "note": "Insuficientes folds para t-test"}
    evs = wf_df["ev_per_trade_pct"].values
    t_stat, p_two = scipy_stats.ttest_1samp(evs, 0)
    p_one = p_two / 2 if t_stat > 0 else 1.0
    total_trades = int(wf_df["n_trades"].sum())
    return {
        "label": label,
        "n_folds": len(wf_df),
        "total_trades": total_trades,
        "n_tp": int(wf_df["n_tp"].sum()), "n_sl": int(wf_df["n_sl"].sum()), "n_time_exit": int(wf_df["n_time_exit"].sum()),
        "mean_ev_pct": round(float(evs.mean()), 4),
        "t_statistic": round(float(t_stat), 3),
        "p_value_one_sided": round(float(p_one), 4),
        "significant_5pct": bool(p_one < 0.05),
        "n_over_200": bool(total_trades > 200),
    }


def main():
    for product, stem in [("MES", "mes"), ("MGC", "mgc")]:
        daily = resample_daily(pd.read_parquet(os.path.join(DATA_DIR, f"{stem}_5min_2y.parquet")))
        print(f"\n{'='*90}\n{product}: {len(daily)} barras diarias, {daily.index[0].date()} a {daily.index[-1].date()}\n{'='*90}")

        experiments = [
            ("A) daily (lookback=1d) hold=3d", 1, 3),
            ("A) daily (lookback=1d) hold=5d", 1, 5),
            ("B) weekly (lookback=5d) hold=5d", 5, 5),
        ]
        for label, lookback, hold in experiments:
            for direction in ("fade", "momentum"):
                wf = run_fold_walk_forward(daily, lookback, hold, direction)
                summary = summarize(wf, f"{product} / {label} / {direction}")
                print(f"\n--- {product} / {label} / {direction} ---")
                if not wf.empty:
                    print(wf.to_string(index=False))
                print(summary)


if __name__ == "__main__":
    main()
