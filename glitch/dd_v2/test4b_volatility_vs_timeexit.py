"""
DD v2 -- Investigacion en paralelo (no bloqueante a Fase B): ¿la caida
del time-exit share de MGC_XFA (71.9% Q1 -> 9.3% Q3 -> 14.0% Q4, ver
Test 4) se explica por un aumento real de volatilidad realizada de
MGC a lo largo de los 2 años? Confirmar con evidencia, no intuicion.

Metodologia: ATR diario (14 dias, misma convencion que
simulation/triple_barrier.py) y rango diario promedio (high-low),
calculados sobre barras DIARIAS agregadas del mismo parquet 5min ya
usado en todo el resto de esta due diligence -- mismos 4 cuartiles
cronologicos que Test 4, para comparacion directa.
"""
from __future__ import annotations
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd
from scipy import stats

from dd_v2.common import MGC_PATH


def daily_bars(prices: pd.DataFrame) -> pd.DataFrame:
    local = prices.copy()
    local.index = local.index.tz_convert("America/Chicago")
    local["session_date"] = local.index.date
    daily = local.groupby("session_date").agg(
        open=("open", "first"), high=("high", "max"), low=("low", "min"), close=("close", "last"))
    return daily


def atr(daily: pd.DataFrame, window: int = 14) -> pd.Series:
    high, low, close = daily["high"], daily["low"], daily["close"]
    prev_close = close.shift(1)
    tr = pd.concat([high - low, (high - prev_close).abs(), (low - prev_close).abs()], axis=1).max(axis=1)
    return tr.rolling(window, min_periods=1).mean()


if __name__ == "__main__":
    mgc = pd.read_parquet(MGC_PATH)
    daily = daily_bars(mgc)
    daily["range"] = daily["high"] - daily["low"]
    daily["atr14"] = atr(daily)

    n = len(daily)
    edges = np.linspace(0, n, 5).astype(int)  # 4 cuartiles, mismo split que Test 4 (por conteo de dias, no de trades -- ver nota abajo)

    # Time-exit share por cuartil, TOMADO DIRECTO de Test 4 (corregido,
    # 7:13 CT) -- no recalculado aqui, para comparar contra exactamente
    # esos mismos numeros ya reportados.
    time_exit_share = [0.719, 0.473, 0.093, 0.140]  # Q1..Q4, ver dd_v2/test4_subperiods.py (corregido)

    print("=" * 90)
    print("Volatilidad realizada de MGC por cuartil cronologico (barras diarias agregadas)")
    print("=" * 90)
    print(f"Total dias con barra: {n}  ({daily.index.min()} -> {daily.index.max()})")

    quartile_stats = []
    for i in range(4):
        sub = daily.iloc[edges[i]:edges[i+1]]
        d0, d1 = sub.index.min(), sub.index.max()
        avg_range = sub["range"].mean()
        avg_atr = sub["atr14"].mean()
        quartile_stats.append((avg_range, avg_atr))
        print(f"  Q{i+1} [{d0} -> {d1}]  N_dias={len(sub)}  rango_diario_prom=${avg_range:.2f}  "
              f"ATR14_prom=${avg_atr:.2f}  time_exit_share={time_exit_share[i]:.1%}")

    ranges = [q[0] for q in quartile_stats]
    atrs = [q[1] for q in quartile_stats]

    corr_range, p_range = stats.pearsonr(ranges, time_exit_share)
    corr_atr, p_atr = stats.pearsonr(atrs, time_exit_share)
    print(f"\nCorrelacion (rango diario promedio) vs (time-exit share) entre los 4 cuartiles: "
          f"r={corr_range:+.4f}  (n=4, p={p_range:.4f} -- N MUY chico, orientativo, no una prueba formal)")
    print(f"Correlacion (ATR14 promedio) vs (time-exit share) entre los 4 cuartiles: "
          f"r={corr_atr:+.4f}  (n=4, p={p_atr:.4f} -- N MUY chico, orientativo, no una prueba formal)")

    print(f"\nCambio relativo Q1->Q4: rango diario {ranges[0]:.2f} -> {ranges[3]:.2f} "
          f"({(ranges[3]/ranges[0]-1)*100:+.1f}%)   ATR14 {atrs[0]:.2f} -> {atrs[3]:.2f} "
          f"({(atrs[3]/atrs[0]-1)*100:+.1f}%)")

    # Bracket width en $ para contexto directo -- SL=TP=364 ticks x $0.10/tick = $36.40
    bracket_pts = 364 * 0.10
    print(f"\nAncho del bracket MGC_XFA en puntos de precio: {bracket_pts:.2f} (SL=TP=364 ticks x $0.10/tick)")
    for i in range(4):
        ratio = quartile_stats[i][1] / bracket_pts
        print(f"  Q{i+1}: ATR14/ancho_bracket = {ratio:.3f}  (mayor = el rango diario tipico cubre mas del bracket -> resuelve mas rapido)")
