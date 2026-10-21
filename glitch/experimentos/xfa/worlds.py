"""Mundos (trayectorias) de la Parte D. Ver PREREGISTRO_D.md §1."""
from __future__ import annotations

import datetime as dt
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "..", "preservacion"))
from daydata import load_days, sim_day  # noqa: E402
from m1 import make_days, real_profile  # noqa: E402

MGC_PARQUET = os.environ.get("GLITCH_MGC_PARQUET", "")          # data_cache/mgc_5min_2y_corrected_window.parquet (no esta en git)
MGC = dict(tick=0.10, tick_usd=1.0, fee=1.92, ref_hm=7 * 60 + 15, last_hm=14 * 60 + 25)
GOLD = (dt.date(2025, 11, 14), dt.date(2026, 1, 26))


def mgc_days(clean=True):
    """clean=True: contrato dominante por dia; clean=False: TODAS las barras del dia (como cargaba el codigo previo, ignorando la etiqueta del contrato)."""
    path = MGC_PARQUET
    if not clean:
        d = pd.read_parquet(path); d["contract"] = "X"
        path = os.path.join("/tmp", "mgc_mixed_labels.parquet"); d.to_parquet(path)
    return load_days(path, MGC["ref_hm"], MGC["last_hm"], MGC["tick"], fill_gaps=True, dominant_contract=clean)


def gold_mask(dd, exclude=True):
    m = np.array([GOLD[0] <= d <= GOLD[1] for d in dd.dates])
    return ~m if exclude else np.ones(len(m), bool)


def shares364(dd, sl=364, tp=364):
    out = []
    for side in (1, -1):
        k, _ = sim_day(dd, side, 1, 1e9, slip=0, sl=sl, tp=tp, fee=0, tick_usd=1.0)
        out.append([(k == 0).mean(), (k == 1).mean(), (k == 3).mean()])
    return np.mean(out, axis=0)


def brownian_like(dd, mask, D=40000, seed=5):
    """Browniano sin deriva calibrado por momentos a P(TP-primero), P(SL-primero), P(FLATTEN) de un bracket de 364/364 sobre los dias reales de `mask`."""
    sub = type(dd)([d for d, m in zip(dd.dates, mask) if m], dd.ref[mask], dd.op[mask], dd.hi[mask], dd.lo[mask], dd.cl[mask], [])
    tgt = shares364(sub); prof = real_profile(sub)
    best = None
    for sg in np.arange(200, 700, 25):
        for s in np.arange(0.0, 0.9, 0.1):
            r = shares364(make_days(8000, float(sg), float(s), prof, seed=seed))
            e = float(((r - tgt) ** 2).sum())
            if best is None or e < best[0]: best = (e, float(sg), float(s), r)
    e, sg, s, r = best
    return make_days(D, sg, s, prof, seed=seed + 1), dict(sigma=sg, s=s, target=tgt, fit=r, err=e)


def drift_for_wr(dd, mask, wr, sl=364, tp=364):
    """Deriva (ticks/dia, a favor del lado) que da WR = TP/(TP+SL) = wr entre los dias decididos de un bracket sl/tp sobre los dias reales de `mask`. Biseccion."""
    sub = type(dd)([d for d, m in zip(dd.dates, mask) if m], dd.ref[mask], dd.op[mask], dd.hi[mask], dd.lo[mask], dd.cl[mask], [])
    def w(dr):
        t = s_ = 0.0
        for side in (1, -1):
            k, _ = sim_day(sub, side, 1, 1e9, slip=0, sl=sl, tp=tp, fee=0, tick_usd=1.0, drift=dr)
            t += (k == 0).mean(); s_ += (k == 1).mean()
        return t / (t + s_)
    lo, hi = -400.0, 400.0
    for _ in range(40):
        mid = (lo + hi) / 2
        if w(mid) < wr: lo = mid
        else: hi = mid
    return (lo + hi) / 2
