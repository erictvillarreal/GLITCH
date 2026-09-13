"""
Glitch — Cerebro 2 pivote: refinamientos sobre el candidato MES+MGC
weekly hold=5d/fade (04-sep-2026)
========================================================================
Rama cerebro2-dev. Tres pruebas de robustez/refinamiento sobre el
candidato pendiente mas prometedor de la ronda anterior
(weekly hold=5d/fade, MES+MGC pooled, p=0.048, N=170):

1. Split por dia de la semana de entrada -- descriptivo.
2. Variacion del punto de entrada intradia (mismo cierre vs. retraso a
   apertura/mediodia/cierre del dia siguiente).
3. Filtro de volumen/rango anomalo -- CONSTRUCCION PROPIA de esta
   sesion (el archivo `diagnostic_range_volume.py` que el usuario
   referencio como ya existente de Cerebro 1 NO EXISTE en este repo --
   busqueda exhaustiva confirmada, ver GLITCH_RESEARCH_LOG.md -- esto
   NO es una reutilizacion de codigo previo).

ADVERTENCIA para el punto 1: excluir un dia de la semana DESPUES de
verlo en la misma muestra que genero el candidato original es
refinamiento IN-SAMPLE, no confirmacion independiente -- se reporta
como hallazgo descriptivo, nunca como "mejora confirmada".
"""
from __future__ import annotations
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd
from scipy import stats as scipy_stats

from simulation.triple_barrier import BarrierConfig, label_triple_barrier
from scripts.wf_slow_mr import resample_daily, make_signal_indices, CFG, DATA_DIR

TZ = "America/Chicago"
CANDIDATE = dict(lookback=5, hold=5, direction="fade")  # weekly hold=5d/fade
PRODUCTS = [("MES", "mes"), ("MGC", "mgc")]


def trades_for(product: str, stem: str) -> pd.DataFrame:
    daily = resample_daily(pd.read_parquet(os.path.join(DATA_DIR, f"{stem}_5min_2y.parquet")))
    cfg = BarrierConfig(pt_multiplier=CFG.pt_multiplier, sl_multiplier=CFG.sl_multiplier,
                         max_holding_bars=CANDIDATE["hold"], volatility_window=CFG.volatility_window, use_atr=True)
    sig = make_signal_indices(daily, CANDIDATE["lookback"], CANDIDATE["hold"], CANDIDATE["direction"])
    entries, sides = sig[:, 0].astype(int), sig[:, 1].astype(int)
    longs, shorts = entries[sides == 1], entries[sides == -1]
    labels_l = label_triple_barrier(daily, longs, cfg, side=1) if len(longs) else pd.DataFrame()
    labels_s = label_triple_barrier(daily, shorts, cfg, side=-1) if len(shorts) else pd.DataFrame()
    full = pd.concat([labels_l, labels_s], ignore_index=True)
    full["entry_date"] = daily.index[full["entry_idx"].astype(int)]
    full["product"] = product
    return full


def fold_test(trades: pd.DataFrame, fold_days: int = 126) -> dict:
    if trades.empty or len(trades) < 10:
        return {"n_trades": len(trades), "p_one_sided": None}
    start, end = trades["entry_date"].min(), trades["entry_date"].max() + pd.Timedelta(days=1)
    bounds = pd.date_range(start, end, freq=f"{fold_days}D")
    if bounds[-1] < end:
        bounds = bounds.append(pd.DatetimeIndex([end]))
    evs = []
    for i in range(len(bounds) - 1):
        f = trades[(trades["entry_date"] >= bounds[i]) & (trades["entry_date"] < bounds[i + 1])]
        if len(f) >= 3:
            evs.append(f["pnl_pct"].mean() * 100)
    if len(evs) < 2:
        return {"n_trades": len(trades), "p_one_sided": None}
    t, p2 = scipy_stats.ttest_1samp(evs, 0)
    p1 = p2 / 2 if t > 0 else 1.0
    return {"n_trades": len(trades), "mean_ev_pct": round(float(sum(evs) / len(evs)), 4), "p_one_sided": round(float(p1), 4)}


# ── Parte 1: dia de la semana ──────────────────────────────────────────
def part1_day_of_week():
    print("=" * 90 + "\nPARTE 1: split por dia de la semana (descriptivo)\n" + "=" * 90)
    pooled = pd.concat([trades_for(p, s) for p, s in PRODUCTS], ignore_index=True).sort_values("entry_date")
    pooled["dow"] = pooled["entry_date"].dt.day_name()
    g = pooled.groupby("dow")["pnl_pct"].agg(["count", "mean"])
    g["mean_pct"] = g["mean"] * 100
    print(g[["count", "mean_pct"]].reindex(["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]).to_string())

    no_friday = pooled[pooled["dow"] != "Friday"]
    print(f"\nCon viernes (baseline): {fold_test(pooled)}")
    print(f"Sin viernes (ADVERTENCIA: refinamiento in-sample, no confirmacion): {fold_test(no_friday)}")
    mid = no_friday["entry_date"].min() + (no_friday["entry_date"].max() - no_friday["entry_date"].min()) / 2
    h1, h2 = no_friday[no_friday["entry_date"] < mid], no_friday[no_friday["entry_date"] >= mid]
    print(f"  sin viernes, mitad1: N={len(h1)} EV%={h1['pnl_pct'].mean()*100:.4f}  "
          f"mitad2: N={len(h2)} EV%={h2['pnl_pct'].mean()*100:.4f}")


# ── Parte 2: punto de entrada intradia ─────────────────────────────────
def intraday_price_at(prices_5min: pd.DataFrame, target_hour: int, target_minute: int) -> pd.Series:
    local = prices_5min.copy()
    local.index = local.index.tz_convert(TZ)
    local["session_date"] = local.index.date
    mins = local.index.hour.values * 60 + local.index.minute.values - (target_hour * 60 + target_minute)
    local["mins_from_target"] = np.abs(mins)
    idx = local.groupby("session_date")["mins_from_target"].idxmin()
    out = local.loc[idx, ["session_date", "close"]].set_index("session_date")["close"]
    out.index = pd.to_datetime(out.index)
    return out


def trades_entry_variant(product: str, stem: str, entry_variant: str) -> pd.DataFrame:
    prices_5min = pd.read_parquet(os.path.join(DATA_DIR, f"{stem}_5min_2y.parquet"))
    daily = resample_daily(prices_5min)
    cfg = BarrierConfig(pt_multiplier=CFG.pt_multiplier, sl_multiplier=CFG.sl_multiplier,
                         max_holding_bars=CANDIDATE["hold"], volatility_window=CFG.volatility_window, use_atr=True)
    sig = make_signal_indices(daily, CANDIDATE["lookback"], CANDIDATE["hold"], CANDIDATE["direction"])
    entries, sides = sig[:, 0].astype(int), sig[:, 1].astype(int)

    daily2 = daily.copy()
    if entry_variant != "baseline_same_close":
        entries = entries + 1
        keep = entries < len(daily2) - 1
        entries, sides = entries[keep], sides[keep]
        target = {"next_open": (8, 35), "next_midday": (12, 0), "next_close": (14, 55)}[entry_variant]
        alt = intraday_price_at(prices_5min, *target).reindex(daily2.index)
        mask = alt.notna()
        daily2.loc[mask, "close"] = alt[mask]

    longs, shorts = entries[sides == 1], entries[sides == -1]
    labels_l = label_triple_barrier(daily2, longs, cfg, side=1) if len(longs) else pd.DataFrame()
    labels_s = label_triple_barrier(daily2, shorts, cfg, side=-1) if len(shorts) else pd.DataFrame()
    full = pd.concat([labels_l, labels_s], ignore_index=True) if len(labels_l) or len(labels_s) else pd.DataFrame()
    if full.empty:
        return full
    full["entry_date"] = daily.index[full["entry_idx"].astype(int)]
    return full


def part2_entry_timing():
    print("\n" + "=" * 90 + "\nPARTE 2: variacion del punto de entrada intradia\n" + "=" * 90)
    for variant in ["baseline_same_close", "next_open", "next_midday", "next_close"]:
        pooled = pd.concat([trades_entry_variant(p, s, variant) for p, s in PRODUCTS], ignore_index=True).sort_values("entry_date")
        print(f"{variant}: {fold_test(pooled)}")


# ── Parte 3: filtro de volumen/rango (construccion propia) ─────────────
def resample_daily_with_volrange(prices_5min: pd.DataFrame) -> pd.DataFrame:
    daily = resample_daily(prices_5min)
    local = prices_5min.copy()
    local.index = local.index.tz_convert(TZ)
    local["session_date"] = local.index.date
    vol = local.groupby("session_date")["volume"].sum()
    vol.index = pd.to_datetime(vol.index)
    daily["volume"] = vol.reindex(daily.index)
    daily["range"] = daily["high"] - daily["low"]
    return daily


def trades_with_anomaly(product: str, stem: str, window: int = 20) -> pd.DataFrame:
    daily = resample_daily_with_volrange(pd.read_parquet(os.path.join(DATA_DIR, f"{stem}_5min_2y.parquet")))
    cfg = BarrierConfig(pt_multiplier=CFG.pt_multiplier, sl_multiplier=CFG.sl_multiplier,
                         max_holding_bars=CANDIDATE["hold"], volatility_window=CFG.volatility_window, use_atr=True)
    sig = make_signal_indices(daily, CANDIDATE["lookback"], CANDIDATE["hold"], CANDIDATE["direction"])
    entries, sides = sig[:, 0].astype(int), sig[:, 1].astype(int)
    longs, shorts = entries[sides == 1], entries[sides == -1]
    labels_l = label_triple_barrier(daily, longs, cfg, side=1) if len(longs) else pd.DataFrame()
    labels_s = label_triple_barrier(daily, shorts, cfg, side=-1) if len(shorts) else pd.DataFrame()
    full = pd.concat([labels_l, labels_s], ignore_index=True)
    full["entry_date"] = daily.index[full["entry_idx"].astype(int)]

    vol_median = daily["volume"].rolling(window, min_periods=5).median()
    range_median = daily["range"].rolling(window, min_periods=5).median()
    full["vol_high"] = daily["volume"].values[full["entry_idx"].astype(int)] > vol_median.values[full["entry_idx"].astype(int)]
    full["range_high"] = daily["range"].values[full["entry_idx"].astype(int)] > range_median.values[full["entry_idx"].astype(int)]
    full["product"] = product
    return full


def part3_volume_range_filter():
    print("\n" + "=" * 90 + "\nPARTE 3: filtro de volumen/rango (construccion PROPIA -- ver docstring)\n" + "=" * 90)
    pooled = pd.concat([trades_with_anomaly(p, s) for p, s in PRODUCTS], ignore_index=True).sort_values("entry_date")
    print("Filtro VOLUMEN (dia de entrada vs mediana movil 20d):")
    print("  volumen alto:", fold_test(pooled[pooled["vol_high"]]))
    print("  volumen bajo:", fold_test(pooled[~pooled["vol_high"]]))
    print("Filtro RANGO (dia de entrada vs mediana movil 20d):")
    print("  rango alto:", fold_test(pooled[pooled["range_high"]]))
    print("  rango bajo:", fold_test(pooled[~pooled["range_high"]]))


if __name__ == "__main__":
    part1_day_of_week()
    part2_entry_timing()
    part3_volume_range_filter()
