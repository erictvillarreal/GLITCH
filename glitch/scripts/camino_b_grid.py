"""
Glitch — Camino B: Grid Monte Carlo restringido a RR<=0.5 (25-ago-2026)
==========================================================================
Alcance decidido con el usuario tras revalidate_geometry_table.py: el
bracket [optimista pre-fix, conservador post-fix] es angosto (<10% de
barras ambiguas) solo para RR<=0.5 -- ahi es donde vive el mejor
candidato conocido (SL=30/TP=10). Este script:

  1. Para cada (sl_ticks, tp_ticks) con rr=tp/sl<=0.5 y cada
     max_holding_bars, mide el WR empirico REAL de ambos extremos del
     bracket (pre-fix/optimista, post-fix/conservador) directamente
     sobre MES real -- no interpola, no asume teoria.
  2. Usa el PUNTO MEDIO del bracket como WR de entrada al Monte Carlo
     (instruccion explicita del usuario: "usar el punto medio del
     bracket como input, no un extremo").
  3. Corre TopstepMonteCarloSimulator (motor YA existente,
     simulation/monte_carlo.py, sin reimplementar) para cada combinacion
     de nc x trades_por_dia x direccion, con comision real ($1.22
     round-turn MES por contrato) descontada.
  4. Objetivo compuesto: combines_por_año = (pass_rate_15d /
     dias_promedio_resolucion) x dias_habiles_año, NO pass_rate aislado.

Recorte de grid deliberado (ver docstring de main() para el tamaño
exacto y por que) -- disclosure explicito, no un barrido literal de
[1..50] en nc.
"""
from __future__ import annotations
import os, sys, itertools, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd

from core.prop_firm import TOPSTEP_50K
from simulation.monte_carlo import TopstepMonteCarloSimulator, SimResult

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data_cache")
MES_PATH = os.path.join(DATA_DIR, "mes_5min_2y.parquet")
OUT_CSV = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data_cache", "camino_b_grid_results.csv")

TICK_SIZE = 0.25
TICK_VALUE_USD = 1.25          # MES, ver INSTRUMENT_SPECS en data/loader.py
COMMISSION_ROUNDTURN = 1.22    # $1.22/contrato round-turn MES, fuente oficial Topstep
TRADING_DAYS_PER_YEAR = 252
N_PATHS = 8_000
MAX_DAYS = 15

SL_GRID = [10, 15, 20, 25, 30, 40, 50]
TP_CANDIDATES = [2, 3, 4, 5, 6, 8, 10, 12, 15, 20, 25]
HOLDING_GRID = [30, 45, 66, 100, 130]
NC_GRID = [10, 20, 30, 40, 50]
TRADES_PER_DAY_GRID = [1, 2]
DIRECTIONS = ["alternate", "always_long", "always_short"]


class ExactDayDist:
    """
    Distribucion diaria EXACTA (no aproximacion normal) para N trades/dia
    i.i.d. Bernoulli(wr). Mismo contrato .sample(n, rng) que DailyReturnDist
    -- TopstepMonteCarloSimulator la usa sin modificarse.
    """
    def __init__(self, wr, avg_win_usd, avg_loss_usd, commission_usd, trades_per_day, name="grid"):
        self.wr = wr
        self.net_win = avg_win_usd - commission_usd
        self.net_loss = -(avg_loss_usd + commission_usd)
        self.trades_per_day = trades_per_day
        self.name = name

    def sample(self, n, rng):
        total = np.zeros(n)
        for _ in range(self.trades_per_day):
            is_win = rng.random(n) < self.wr
            total += np.where(is_win, self.net_win, self.net_loss)
        return total

    def describe(self):
        return f"[{self.name}] WR={self.wr:.1%} trades/day={self.trades_per_day}"


def _label_fixed_ticks(prices: pd.DataFrame, signal_indices: np.ndarray,
                        tp_pts: float, sl_pts: float, max_holding_bars: int, side: int,
                        win_first: bool) -> np.ndarray:
    """
    Devuelve array de labels (1/-1/0). win_first=True replica la logica
    BUGGY original (pre-fix, optimista); win_first=False replica el fix
    conservador YA aplicado en simulation/triple_barrier.py.
    """
    close = prices["close"].values
    high  = prices["high"].values
    low   = prices["low"].values
    n = len(prices)
    labels = np.zeros(len(signal_indices), dtype=np.int8)

    for k, entry_i in enumerate(signal_indices):
        entry_i = int(entry_i)
        if entry_i >= n - 1:
            continue
        entry_price = close[entry_i]
        upper = entry_price + side * tp_pts
        lower = entry_price - side * sl_pts
        exit_i = min(entry_i + max_holding_bars, n - 1)

        for j in range(entry_i + 1, exit_i + 1):
            h, l = high[j], low[j]
            if side == 1:
                win_touch, loss_touch = h >= upper, l <= lower
            else:
                win_touch, loss_touch = l <= upper, h >= lower
            if win_touch or loss_touch:
                if win_touch and loss_touch:
                    labels[k] = 1 if win_first else -1
                elif win_touch:
                    labels[k] = 1
                else:
                    labels[k] = -1
                break
    return labels


def measure_wr_bracket(mes: pd.DataFrame, sl_ticks: int, tp_ticks: int, max_holding_bars: int,
                        tick_size: float = TICK_SIZE) -> dict:
    """
    tick_size default = TICK_SIZE (MES, 0.25) para no romper las llamadas
    existentes de este script. BUG (25-ago-2026): scripts/camino_b_products.py
    llamaba a esta funcion para otros productos (ZN, ZC, M6E, MCL, MGC, M2K)
    SIN pasar su tick_size real -- la funcion usaba silenciosamente 0.25 de
    MES para todos, produciendo barreras 25x-2500x mas anchas de lo
    pretendido (WR colapsando a ~0 para los productos con tick_size << 0.25).
    Ver reporte -- todos los resultados de productos != MES/MNQ generados
    antes de este fix son invalidos y fueron re-corridos despues.
    """
    n = len(mes)
    sl_pts = sl_ticks * tick_size
    tp_pts = tp_ticks * tick_size
    signal_indices = np.arange(0, n - max_holding_bars - 1, 1)
    longs = signal_indices[np.arange(len(signal_indices)) % 2 == 0]
    shorts = signal_indices[np.arange(len(signal_indices)) % 2 == 1]

    out = {}
    for tag, win_first in (("opt", True), ("cons", False)):
        ll = _label_fixed_ticks(mes, longs, tp_pts, sl_pts, max_holding_bars, side=1, win_first=win_first)
        ls = _label_fixed_ticks(mes, shorts, tp_pts, sl_pts, max_holding_bars, side=-1, win_first=win_first)
        out[f"wr_long_{tag}"]  = float((ll == 1).mean())
        out[f"wr_short_{tag}"] = float((ls == 1).mean())
        out[f"wr_all_{tag}"]   = float((np.concatenate([ll, ls]) == 1).mean())
    out["n_trades"] = len(longs) + len(shorts)
    return out


def main():
    t0 = time.time()
    mes = pd.read_parquet(MES_PATH)
    print(f"MES: {len(mes):,} barras RTH")

    pairs = sorted({(sl, tp) for sl in SL_GRID for tp in TP_CANDIDATES if tp / sl <= 0.5})
    print(f"Pares (sl,tp) con rr<=0.5: {len(pairs)}")
    print(f"max_holding_bars: {HOLDING_GRID}")
    print(f"Total mediciones de bracket (bar-walk): {len(pairs) * len(HOLDING_GRID)}")
    print(f"nc grid: {NC_GRID}  (recorte deliberado de [1..50] -- ver reporte)")
    print(f"trades_per_day: {TRADES_PER_DAY_GRID}  direcciones: {DIRECTIONS}\n")

    brackets = {}
    n_done = 0
    total_walks = len(pairs) * len(HOLDING_GRID)
    for sl, tp in pairs:
        for hold in HOLDING_GRID:
            brackets[(sl, tp, hold)] = measure_wr_bracket(mes, sl, tp, hold)
            n_done += 1
            if n_done % 25 == 0:
                print(f"  bracket {n_done}/{total_walks}  ({time.time()-t0:.0f}s elapsed)")

    print(f"\nBrackets listos ({time.time()-t0:.0f}s). Corriendo Monte Carlo...")

    rows = []
    for (sl, tp, hold), br in brackets.items():
        for direction in DIRECTIONS:
            if direction == "alternate":
                wr_opt, wr_cons = br["wr_all_opt"], br["wr_all_cons"]
            elif direction == "always_long":
                wr_opt, wr_cons = br["wr_long_opt"], br["wr_long_cons"]
            else:
                wr_opt, wr_cons = br["wr_short_opt"], br["wr_short_cons"]
            wr_mid = (wr_opt + wr_cons) / 2

            for nc in NC_GRID:
                avg_win_usd = tp * TICK_VALUE_USD * nc
                avg_loss_usd = sl * TICK_VALUE_USD * nc
                commission_usd = COMMISSION_ROUNDTURN * nc

                for tpd in TRADES_PER_DAY_GRID:
                    dist = ExactDayDist(wr_mid, avg_win_usd, avg_loss_usd, commission_usd, tpd)
                    sim = TopstepMonteCarloSimulator(dist, TOPSTEP_50K, n_paths=N_PATHS, max_days=MAX_DAYS, seed=42)
                    r = sim.run()

                    avg_days = r.avg_pass_days
                    if r.pass_rate > 0 and avg_days:
                        combines_por_ano = (r.pass_rate / avg_days) * TRADING_DAYS_PER_YEAR
                        costo_por_combine = TOPSTEP_50K.monthly_fee / r.pass_rate
                    else:
                        combines_por_ano = 0.0
                        costo_por_combine = float("inf")

                    rows.append({
                        "sl_ticks": sl, "tp_ticks": tp, "rr": round(tp / sl, 3),
                        "max_holding_bars": hold, "direction": direction,
                        "nc": nc, "trades_per_day": tpd,
                        "wr_used_mid_bracket": round(wr_mid, 4),
                        "wr_bracket_width": round(wr_opt - wr_cons, 4),
                        "pass_rate_15d": round(r.pass_rate, 4),
                        "blow_rate": round(r.blow_rate, 4),
                        "avg_days_to_pass": round(avg_days, 2) if avg_days else None,
                        "combines_por_ano": round(combines_por_ano, 2),
                        "costo_esperado_por_combine": round(costo_por_combine, 2) if costo_por_combine != float("inf") else None,
                    })

    df = pd.DataFrame(rows)
    df = df.sort_values("combines_por_ano", ascending=False).reset_index(drop=True)
    df.to_csv(OUT_CSV, index=False)

    print(f"\nTotal configs evaluadas: {len(df):,}  ({time.time()-t0:.0f}s total)")
    print(f"Guardado: {OUT_CSV}\n")
    print("=" * 100)
    print("TOP 20 por combines_por_año")
    print("=" * 100)
    cols = ["sl_ticks", "tp_ticks", "rr", "max_holding_bars", "direction", "nc", "trades_per_day",
            "wr_used_mid_bracket", "pass_rate_15d", "blow_rate", "avg_days_to_pass",
            "combines_por_ano", "costo_esperado_por_combine"]
    print(df[cols].head(20).to_string(index=False))


if __name__ == "__main__":
    main()
