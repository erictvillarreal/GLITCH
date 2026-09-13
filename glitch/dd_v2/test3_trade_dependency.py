"""
DD v2 -- Test 3: Trade Dependency (autocorrelacion lag-1, rachas) sobre
la secuencia REAL cronologica de 1 trade/dia (no el bar-walk denso),
para G2 (MES) y MGC_XFA (MGC). Compara contra lo que un proceso i.i.d.
Bernoulli(wr) predeciria para el mismo N y WR.
"""
from __future__ import annotations
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from dd_v2.common import build_daily_trades, MES_PATH, MGC_PATH, G2, MGC_XFA


def streak_stats(seq: np.ndarray) -> dict:
    """seq: array de 1 (win) / 0 (loss), SOLO trades resueltos (sin time-exits)."""
    if len(seq) == 0:
        return {}
    changes = np.diff(seq) != 0
    streak_ids = np.concatenate([[0], np.cumsum(changes)])
    streaks = []
    for sid in np.unique(streak_ids):
        mask = streak_ids == sid
        streaks.append((seq[mask][0], mask.sum()))
    win_streaks = [length for val, length in streaks if val == 1]
    loss_streaks = [length for val, length in streaks if val == 0]
    return {
        "n_win_streaks": len(win_streaks), "avg_win_streak": np.mean(win_streaks) if win_streaks else 0,
        "max_win_streak": max(win_streaks) if win_streaks else 0,
        "n_loss_streaks": len(loss_streaks), "avg_loss_streak": np.mean(loss_streaks) if loss_streaks else 0,
        "max_loss_streak": max(loss_streaks) if loss_streaks else 0,
    }


def lag1_autocorr(seq: np.ndarray) -> float:
    if len(seq) < 3:
        return float("nan")
    x, y = seq[:-1].astype(float), seq[1:].astype(float)
    if x.std() == 0 or y.std() == 0:
        return 0.0
    return float(np.corrcoef(x, y)[0, 1])


def theoretical_iid_streak(wr: float) -> dict:
    """Para Bernoulli(wr) i.i.d.: E[longitud de racha de winners] = 1/(1-wr);
    E[longitud de racha de losers] = 1/wr. (Formula estandar de rachas
    geometricas.)"""
    return {"expected_avg_win_streak": 1 / (1 - wr) if wr < 1 else float("inf"),
            "expected_avg_loss_streak": 1 / wr if wr > 0 else float("inf"),
            "expected_lag1_autocorr": 0.0}


def analyze(label: str, df, wr_for_theory: float):
    resolved = df[df["label"] != 0].reset_index(drop=True)
    seq = (resolved["label"] == 1).astype(int).values
    n = len(seq)
    print(f"\n{'='*80}\n{label} -- N resuelto (sin time-exits) = {n}\n{'='*80}")

    ac = lag1_autocorr(seq)
    print(f"Autocorrelacion lag-1 (win=1/loss=0): {ac:+.4f}  (i.i.d. esperaria ~0.0)")

    st = streak_stats(seq)
    th = theoretical_iid_streak(wr_for_theory)
    print(f"Rachas de GANADORAS -- observado: avg={st['avg_win_streak']:.2f}  max={st['max_win_streak']}"
          f"  (n={st['n_win_streaks']})  |  i.i.d. Bernoulli({wr_for_theory:.3f}) esperaria avg={th['expected_avg_win_streak']:.2f}")
    print(f"Rachas de PERDEDORAS -- observado: avg={st['avg_loss_streak']:.2f}  max={st['max_loss_streak']}"
          f"  (n={st['n_loss_streaks']})  |  i.i.d. esperaria avg={th['expected_avg_loss_streak']:.2f}")

    # Test de rachas de Wald-Wolfowitz (aproximacion normal) -- exceso/defecto
    # de rachas totales vs lo esperado bajo independencia.
    n1, n0 = seq.sum(), n - seq.sum()
    n_runs_obs = 1 + np.sum(np.diff(seq) != 0)
    mu_runs = 2 * n1 * n0 / n + 1
    var_runs = (2 * n1 * n0 * (2 * n1 * n0 - n)) / (n**2 * (n - 1)) if n > 1 else 0
    z_runs = (n_runs_obs - mu_runs) / np.sqrt(var_runs) if var_runs > 0 else 0
    from scipy import stats as sstats
    p_runs = 2 * (1 - sstats.norm.cdf(abs(z_runs)))
    print(f"Test de rachas (Wald-Wolfowitz): rachas observadas={n_runs_obs}  esperadas={mu_runs:.1f}  "
          f"z={z_runs:+.3f}  p-value={p_runs:.4f}  "
          f"({'RECHAZA independencia' if p_runs < 0.05 else 'NO rechaza independencia'} al 5%)")

    return {"autocorr": ac, "runs_p_value": p_runs, **st}


if __name__ == "__main__":
    g2_df = build_daily_trades(MES_PATH, "MES", G2.sl_ticks, G2.tp_ticks, G2.max_holding_bars, G2.direction)
    mgc_df = build_daily_trades(MGC_PATH, "MGC", MGC_XFA.sl_ticks, MGC_XFA.tp_ticks, MGC_XFA.max_holding_bars, MGC_XFA.direction,
                                 open_hour=7, open_minute=13)  # entrada real de produccion, ver GLITCH_RESEARCH_LOG.md

    analyze("G2 (MES, SL=100/TP=40, 1 trade/dia real)", g2_df, wr_for_theory=0.7096)
    analyze("MGC_XFA (MGC, SL=TP=364, 1 trade/dia real)", mgc_df, wr_for_theory=0.5020)
