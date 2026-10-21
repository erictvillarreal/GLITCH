"""M1 -- caminos brownianos sin deriva (sinteticos), formato DayData para reutilizar sim_day/OutcomeTable.

M1a: volatilidad constante por dia (un parametro: sigma_dia en ticks de desviacion estandar del cierre).
M1b: volatilidad por dia lognormal (sigma_dia, s) + perfil intradia de varianza por barra tomado de los datos reales (forma, no nivel).
Cada barra de 5 min se genera con m sub-pasos gaussianos para obtener open/high/low/close consistentes.
"""
from __future__ import annotations

import numpy as np

from daydata import SL_TICKS, TP_TICKS, DayData, sim_day


def real_profile(dd: DayData):
    """Fraccion de la varianza diaria por barra (suma 1), estimada de var(cl_k - cl_{k-1}) en los datos reales."""
    prev = np.concatenate([np.zeros((dd.D, 1)), dd.cl[:, :-1]], axis=1)
    v = ((dd.cl - prev) ** 2).mean(axis=0)
    return v / v.sum()


def make_days(D, sigma_day, s_ln, profile, seed=0, m=8, K=None):
    rng = np.random.default_rng(seed)
    K = len(profile)
    mult = np.exp(s_ln * rng.standard_normal(D) - s_ln ** 2) if s_ln > 0 else np.ones(D)   # E[mult^2] = 1
    sd_bar = sigma_day * np.sqrt(profile)                     # sd del incremento de cada barra
    inc = rng.standard_normal((D, K, m)) * (sd_bar[None, :, None] / np.sqrt(m)) * mult[:, None, None]
    path = np.cumsum(inc.reshape(D, K * m), axis=1).reshape(D, K, m)
    cl = path[:, :, -1]
    prev = np.concatenate([np.zeros((D, 1)), cl[:, :-1]], axis=1)
    op = prev
    hi = np.maximum(path.max(axis=2), prev); lo = np.minimum(path.min(axis=2), prev)
    return DayData([None] * D, np.zeros(D), op, hi, lo, cl, [])


def shares(dd: DayData, sl=SL_TICKS, tp=40):
    """(P(TP), P(SL), P(ninguno)) promediado sobre long y short, sin slippage ni liquidacion ni comision."""
    out = []
    for side in (1, -1):
        k, _ = sim_day(dd, side, 1, 1e9, slip=0, sl=sl, tp=tp, fee=0)
        out.append([(k == 0).mean(), (k == 1).mean(), (k == 3).mean()])
    return np.mean(out, axis=0)


def fit(profile, targets=(0.59, 0.24, 0.17), sl=SL_TICKS, tp=40, with_ln=True, D=20000, seed=11):
    """Busqueda en rejilla de (sigma_dia, s) minimizando el error cuadratico de las tres proporciones (metodo de momentos)."""
    best = None
    sig_grid = np.arange(60, 260, 10)
    s_grid = np.arange(0.0, 1.01, 0.1) if with_ln else [0.0]
    for sg in sig_grid:
        for s in s_grid:
            r = shares(make_days(D, float(sg), float(s), profile, seed=seed), sl, tp)
            err = float(((r - np.array(targets)) ** 2).sum())
            if best is None or err < best[0]:
                best = (err, float(sg), float(s), r)
    return best
