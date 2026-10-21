"""Utilidades de la Parte E: series largas, señales (solo informacion previa a la entrada), sesiones de 5 min, resultados con la mecanica exacta, bootstrap de bloques y Holm."""
from __future__ import annotations

import datetime as dt
import math
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "..", "xfa")); sys.path.insert(0, os.path.join(HERE, "..", "preservacion"))
DATA = os.environ.get("GLITCH_E_DATA", os.path.join(HERE, "data"))
SEED = 20261021


# ── series largas (Yahoo, crudas) ────────────────────────────────────────────────────────────────────────────────────────
def load_daily(name: str) -> pd.DataFrame:
    fn = {"GLD": "GLD", "GC=F": "GC_F", "^GSPC": "GSPC", "SPY": "SPY", "ES=F": "ES_F"}[name]
    d = pd.read_csv(os.path.join(DATA, fn + ".csv"), index_col=0, parse_dates=True)
    d = d[["Open", "High", "Low", "Close", "Volume"]].dropna(subset=["Open", "Close"])
    return d[~d.index.duplicated(keep="first")].sort_index()


def e1_signals(df: pd.DataFrame) -> pd.DataFrame:
    """E1 (PREREGISTRO_E §2). Todo con desplazamientos >= 1 dia: la fila t usa solo cierres hasta t-1 (r12 hasta t-2).
    r12_t = ln(C_{t-2}/C_{t-254}); sigma_a,t = std expansiva (>= 252 dias) de los retornos log diarios hasta t-2, x sqrt(252).
    side_r12 = sign(r12) si |r12| >= 0.5 sigma_a si no 0 (NO OPERAR); side_sma = sign(SMA50_{t-1} - SMA200_{t-1})."""
    c = df["Close"].astype(float)
    ret = np.log(c / c.shift(1))
    r12 = np.log(c.shift(2) / c.shift(254))
    sig = ret.shift(2).expanding(min_periods=252).std() * math.sqrt(252)
    side_r12 = np.where(r12.abs() >= 0.5 * sig, np.sign(r12), 0.0)
    side_r12 = np.where(r12.isna() | sig.isna(), np.nan, side_r12)
    sma = c.rolling(50).mean().shift(1) - c.rolling(200).mean().shift(1)
    side_sma = np.where(sma.isna(), np.nan, np.sign(sma))
    out = pd.DataFrame({"r12": r12, "sig_a": sig, "side_r12": side_r12, "side_sma": side_sma}, index=df.index)
    out["oc"] = np.sign(np.log(df["Close"] / df["Open"])); out["cc"] = np.sign(ret)
    out["oc_ret"] = np.log(df["Close"] / df["Open"]); out["cc_ret"] = ret
    return out


# ── sesiones de 5 min (cierre previo, apertura de la sesion, contrato dominante) ──────────────────────────────────────────
def session_table(path: str) -> pd.DataFrame:
    """Por fecha CT: contrato dominante (mayor volumen), primer open y ultimo close de ESA sesion con el contrato dominante. Husos: America/Chicago (maneja DST)."""
    d = pd.read_parquet(path).tz_convert("America/Chicago")
    d["date"] = d.index.date
    rows = []
    for dtt, x in d.groupby("date"):
        vol = x.groupby("contract")["volume"].sum(); c = vol.idxmax(); x = x[x.contract == c]
        rows.append((dtt, c, float(x["open"].iloc[0]), float(x["close"].iloc[-1]), int(x.index[0].hour * 60 + x.index[0].minute), int(x.index[-1].hour * 60 + x.index[-1].minute), x.contract.nunique(), len(x)))
    t = pd.DataFrame(rows, columns=["date", "contract", "open0", "close_last", "first_hm", "last_hm", "n_contracts_dom", "n_bars"]).set_index("date")
    return t


def overnight_returns(st: pd.DataFrame, ref: dict, dd_dates) -> pd.DataFrame:
    """R = ln(P_ref / C_prev) y gap = ln(open0/C_prev) para cada fecha de dd_dates; NaN si el contrato dominante cambio respecto a la sesion previa o no hay sesion previa."""
    dates = list(st.index)
    pos = {d: i for i, d in enumerate(dates)}
    out = []
    for d in dd_dates:
        i = pos[d]
        if i == 0 or st["contract"].iloc[i - 1] != st["contract"].iloc[i]:
            out.append((d, np.nan, np.nan)); continue
        cprev = st["close_last"].iloc[i - 1]
        out.append((d, math.log(ref[d] / cprev), math.log(st["open0"].iloc[i] / cprev)))
    return pd.DataFrame(out, columns=["date", "R", "gap"]).set_index("date")


# ── resultados con la mecanica exacta ───────────────────────────────────────────────────────────────────────────────────────
def day_results(dd, nc, cushion, sl, tp, fee, tick_usd, slip=0.0):
    """Para cada dia de dd y cada lado: (kind, pnl). kind 0=TP, 1=SL, 2=LIQ, 3=FLATTEN."""
    from daydata import sim_day
    res = {}
    for side in (1, -1):
        res[side] = sim_day(dd, side, nc, cushion, slip=slip, exit_slip=0.0, sl=sl, tp=tp, fee=fee, tick_usd=tick_usd)
    return res


def eval_sides(res, sides):
    """sides: array (+1/-1/0=no opera). Devuelve dict con n, TP, SL(+LIQ), FLATTEN, WR entre decididos y pnl medio por dia operado."""
    sides = np.asarray(sides)
    k = np.where(sides == 1, res[1][0], res[-1][0]); p = np.where(sides == 1, res[1][1], res[-1][1])
    m = sides != 0
    k, p = k[m], p[m]
    n = len(k)
    if n == 0: return dict(n=0, tp=np.nan, sl=np.nan, fl=np.nan, wr=np.nan, dec=0, pnl=np.nan)
    tp = (k == 0).sum(); sl = ((k == 1) | (k == 2)).sum(); fl = (k == 3).sum()
    return dict(n=n, tp=tp / n, sl=sl / n, fl=fl / n, wr=tp / (tp + sl) if tp + sl else np.nan, dec=int(tp + sl), pnl=float(p.mean()))


# ── estadistica ───────────────────────────────────────────────────────────────────────────────────────────────────────────
def block_bootstrap_acc(hits, block=5, B=10000, seed=SEED):
    """hits: vector 0/1 (o NaN descartado) en orden cronologico. Devuelve (media, [IC95], distribucion bootstrap)."""
    h = np.asarray(hits, float); h = h[~np.isnan(h)]
    n = len(h)
    if n < block * 2: return float(h.mean()) if n else np.nan, (np.nan, np.nan), np.array([np.nan])
    rng = np.random.default_rng(seed); nb = int(math.ceil(n / block))
    starts = rng.integers(0, n - block + 1, size=(B, nb))
    idx = (starts[:, :, None] + np.arange(block)[None, None, :]).reshape(B, -1)[:, :n]
    means = h[idx].mean(axis=1)
    return float(h.mean()), (float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))), means


def pval_gt(means, thr):
    """p-valor bootstrap (percentil) de H0: exactitud <= thr contra exactitud > thr."""
    m = means[~np.isnan(means)]
    return float((m <= thr).mean()) if len(m) else np.nan


def holm(pvals: dict, m_total: int, alpha=0.05):
    """Holm sobre m_total comparaciones declaradas (las no calculadas cuentan con p = 1). Devuelve {clave: (p_ajustado, rechaza)}."""
    items = sorted(pvals.items(), key=lambda kv: (np.inf if np.isnan(kv[1]) else kv[1]))
    out = {}; running = 0.0
    for i, (k, p) in enumerate(items):
        p = 1.0 if np.isnan(p) else p
        adj = min(1.0, (m_total - i) * p); running = max(running, adj)
        out[k] = (running, running < alpha)
    return out


def blocks10(n):
    """10 bloques cronologicos contiguos (el ultimo absorbe el resto)."""
    size = n // 10
    return [(i * size, (i + 1) * size if i < 9 else n) for i in range(10)]


# ── señales de 5 min (E2 / E5): solo informacion disponible hasta la barra de referencia ──────────────────────────────────
def intraday_signals(df: pd.DataFrame, ref_hm: int) -> pd.DataFrame:
    """df: barras de 5 min (indice UTC; columnas open, high, low, close, volume, contract). Por fecha CT: contrato dominante, open0 (primer open), p_ref (close de la barra que empieza en ref_hm),
    close_last (ultimo close). R = ln(p_ref/close_last de la sesion previa) y gap = ln(open0/close_last previo); NaN si el contrato dominante cambio. Para el dia t solo usa barras de t hasta ref_hm y la sesion previa."""
    d = df.tz_convert("America/Chicago").copy()
    d["date"] = d.index.date; d["hm"] = d.index.hour * 60 + d.index.minute
    rows = []
    for dtt, x in d.groupby("date"):
        vol = x.groupby("contract")["volume"].sum(); c = vol.idxmax(); x = x[x.contract == c]
        xr = x[x.hm == ref_hm]
        rows.append((dtt, c, float(x["open"].iloc[0]), float(xr["close"].iloc[0]) if len(xr) else np.nan, float(x["close"].iloc[-1])))
    t = pd.DataFrame(rows, columns=["date", "contract", "open0", "p_ref", "close_last"]).set_index("date")
    prev_close = t["close_last"].shift(1); same = t["contract"].shift(1) == t["contract"]
    t["R"] = np.where(same, np.log(t["p_ref"] / prev_close), np.nan)
    t["gap"] = np.where(same, np.log(t["open0"] / prev_close), np.nan)
    return t


def prior_stat(series: pd.Series, window: int, fn: str, q: float = 0.5) -> pd.Series:
    """Estadistico movil de |serie| sobre los `window` valores disponibles PREVIOS (excluye el actual)."""
    r = series.abs().dropna()
    s = r.rolling(window, min_periods=window).median() if fn == "median" else r.rolling(window, min_periods=window).quantile(q)
    return s.shift(1).reindex(series.index, method="ffill")
