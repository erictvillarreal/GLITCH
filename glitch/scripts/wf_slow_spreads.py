"""
Glitch — Cerebro 2 pivote, Dirección 3: mean-reversion/momentum en
SPREADS (par de productos correlacionados) (04-sep-2026)
========================================================================
Rama cerebro2-dev. Nunca probado esta sesión -- toda la investigación
anterior (Cerebro 1 y la Dirección 1 del pivote) usó productos
individuales. Aquí se prueba si el spread MES-vs-M2K (equity index,
mismo tipo de activo, alta correlación esperada) tiene una señal de
reversión/momentum más robusta que cualquiera de los dos productos
solos.

Par oro-vs-plata (GC/MGC vs SI/SIL) pedido explícitamente por el
usuario NO se corre en este pase -- no hay datos de plata (SI/SIL) en
data_cache/, y obtenerlos requiere MASSIVE_API_KEY (vive en Railway,
no disponible en este shell local). Reportado como bloqueo explícito,
no omitido en silencio -- ver GLITCH_RESEARCH_LOG.md.

Construcción del spread -- CORREGIDA tras un primer intento fallido
(ver GLITCH_RESEARCH_LOG.md): la primera versión aproximaba
high/low del spread como high_A/low_B y low_A/high_B (combinando el
extremo de una pata con el extremo OPUESTO de la otra, que casi nunca
ocurren en el mismo instante) -- esto infla artificialmente el rango
intradía aparente del spread, dando un ATR muchas veces mayor al
movimiento real, y como consecuencia casi ningún trade tocaba TP
(0-1 de 84-126 trades por config) en NINGUNA combinación -- un patron
mecanico degenerado, no un hallazgo economico de "sin edge". Corregido
usando SOLO el cierre (close-to-close) del spread, sin fabricar un
rango intradía que no se puede reconstruir sin datos tick-a-tick
sincronizados:
    spread_close = closeA / closeB
    spread_open = spread_high = spread_low = spread_close
Volatilidad via `use_atr=False` (rolling std de pct_change del cierre,
BarrierConfig ya lo soporta) en vez de ATR de rango intradía. El
"toque" de barrera queda definido sobre el CIERRE diario unicamente
(¿el cierre de algun dia dentro del holding cruzo la barrera?), no
sobre un intradia fabricado -- simplificacion honesta y estandar para
backtests de spreads sin datos sincronizados a nivel de tick.

Misma metodología ya validada: triple_barrier + walk-forward por folds
+ t-test OOS, fade Y momentum, N>200 Y p<0.05 como criterio combinado
no negociable, split de mitades temporales para reproducibilidad.
"""
from __future__ import annotations
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from scipy import stats as scipy_stats

from simulation.triple_barrier import BarrierConfig, label_triple_barrier
from scripts.wf_slow_mr import resample_daily, make_signal_indices, DATA_DIR, CFG, FOLD_DAYS

PAIRS = [
    ("MES-M2K", "mes", "m2k"),
    # ("MGC-SIL", "mgc", "sil"),  -- BLOQUEADO: sin datos de plata (SI/SIL), requiere fetch con MASSIVE_API_KEY
]
EXPERIMENTS = [
    ("daily hold=3d", 1, 3),
    ("daily hold=5d", 1, 5),
    ("weekly hold=5d", 5, 5),
]


def build_spread_daily(stem_a: str, stem_b: str) -> pd.DataFrame:
    daily_a = resample_daily(pd.read_parquet(os.path.join(DATA_DIR, f"{stem_a}_5min_2y.parquet")))
    daily_b = resample_daily(pd.read_parquet(os.path.join(DATA_DIR, f"{stem_b}_5min_2y.parquet")))
    common = daily_a.index.intersection(daily_b.index)
    a, b = daily_a.loc[common], daily_b.loc[common]
    spread = pd.DataFrame(index=common)
    spread["close"] = a["close"] / b["close"]
    spread["open"] = spread["high"] = spread["low"] = spread["close"]
    return spread


def run_fold_walk_forward(daily: pd.DataFrame, lookback_days: int, hold_days: int, direction: str) -> pd.DataFrame:
    # use_atr=False: el spread solo tiene "close" real (open=high=low=close
    # por construccion) -- un ATR de rango intradia sobre esto seria
    # siempre 0. Volatilidad via rolling std de pct_change del cierre.
    cfg = BarrierConfig(pt_multiplier=CFG.pt_multiplier, sl_multiplier=CFG.sl_multiplier,
                         max_holding_bars=hold_days, volatility_window=CFG.volatility_window, use_atr=False)
    sig = make_signal_indices(daily, lookback_days, hold_days, direction)
    if len(sig) == 0:
        return pd.DataFrame()
    entries, sides = sig[:, 0].astype(int), sig[:, 1].astype(int)
    longs, shorts = entries[sides == 1], entries[sides == -1]
    labels_l = label_triple_barrier(daily, longs, cfg, side=1) if len(longs) else pd.DataFrame()
    labels_s = label_triple_barrier(daily, shorts, cfg, side=-1) if len(shorts) else pd.DataFrame()
    full = pd.concat([labels_l, labels_s], ignore_index=True) if len(labels_l) or len(labels_s) else pd.DataFrame()
    if full.empty:
        return full
    full["entry_date"] = daily.index[full["entry_idx"].astype(int)]

    n = len(daily)
    folds = []
    fold_num = 0
    i = 0
    while i + FOLD_DAYS <= n:
        fold = full[(full["entry_idx"] >= i) & (full["entry_idx"] < i + FOLD_DAYS)]
        if len(fold) >= 3:
            wins = fold[fold["label"] == 1]["pnl_pct"]
            losses = fold[fold["label"] == -1]["pnl_pct"].abs()
            time_exits = fold[fold["label"] == 0]
            folds.append({
                "fold": fold_num, "n_trades": len(fold), "n_tp": len(wins), "n_sl": len(losses),
                "n_time_exit": len(time_exits), "ev_per_trade_pct": round(float(fold["pnl_pct"].mean() * 100), 4),
            })
        i += FOLD_DAYS
        fold_num += 1
    return pd.DataFrame(folds), full


def significance(wf_df: pd.DataFrame) -> dict:
    if wf_df.empty or len(wf_df) < 2:
        return {"n_folds": len(wf_df), "p_value_one_sided": None}
    evs = wf_df["ev_per_trade_pct"].values
    t_stat, p_two = scipy_stats.ttest_1samp(evs, 0)
    p_one = p_two / 2 if t_stat > 0 else 1.0
    total = int(wf_df["n_trades"].sum())
    return {
        "n_folds": len(wf_df), "total_trades": total,
        "n_tp": int(wf_df["n_tp"].sum()), "n_sl": int(wf_df["n_sl"].sum()), "n_time_exit": int(wf_df["n_time_exit"].sum()),
        "mean_ev_pct": round(float(evs.mean()), 4),
        "t_statistic": round(float(t_stat), 3), "p_value_one_sided": round(float(p_one), 4),
        "significant_5pct": bool(p_one < 0.05), "n_over_200": bool(total > 200),
    }


def main():
    print("BLOQUEADO: par oro-vs-plata (MGC-SIL) -- sin datos de plata en data_cache/, "
          "requiere MASSIVE_API_KEY (no disponible en este shell local). Solo se corre MES-M2K.\n")

    for pair_label, stem_a, stem_b in PAIRS:
        spread = build_spread_daily(stem_a, stem_b)
        print(f"\n{'='*95}\nSPREAD {pair_label}: {len(spread)} barras diarias, "
              f"{spread.index[0].date()} a {spread.index[-1].date()}\n{'='*95}")

        for label, lookback, hold in EXPERIMENTS:
            for direction in ("fade", "momentum"):
                result = run_fold_walk_forward(spread, lookback, hold, direction)
                if isinstance(result, tuple):
                    wf, full = result
                else:
                    wf, full = result, pd.DataFrame()
                summary = significance(wf)
                print(f"\n--- {pair_label} / {label} / {direction} ---")
                print(summary)

                if not full.empty and summary.get("n_folds", 0) >= 2:
                    mid = full["entry_date"].min() + (full["entry_date"].max() - full["entry_date"].min()) / 2
                    h1 = full[full["entry_date"] < mid]
                    h2 = full[full["entry_date"] >= mid]
                    if len(h1) >= 3 and len(h2) >= 3:
                        print(f"    mitad 1: N={len(h1)} EV%={h1['pnl_pct'].mean()*100:.4f}   "
                              f"mitad 2: N={len(h2)} EV%={h2['pnl_pct'].mean()*100:.4f}")


if __name__ == "__main__":
    main()
