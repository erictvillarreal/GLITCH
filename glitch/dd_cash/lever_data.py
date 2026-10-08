"""Construccion de Spec alineados en un eje de dias comun (interseccion de fechas de los productos usados) para el motor de palancas. Reproduce el pipeline vigente (Combine G2/MES 9:45 CT +
XFA Cerebro 2/MGC 364/364 7:13 CT) y permite otros productos/horas con geometria estructural. SANDBOX / R&D."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np, pandas as pd
from scripts.tables_generic import build as build_tab, build_synthetic, SPEC as TSPEC
from dd_cash.lever_engine import Spec

GOLD = (pd.Timestamp("2025-11-14"), pd.Timestamp("2026-01-26"))
HOL = {pd.Timestamp(d) for d in ("2026-11-26", "2026-12-25", "2027-01-01", "2027-04-02", "2027-05-31", "2027-07-05", "2027-09-06")}
EARLY = {pd.Timestamp("2026-11-27"), pd.Timestamp("2026-12-24")}
DAYS = [d for d in pd.bdate_range("2026-10-19", "2027-10-19") if d not in HOL]
H = len(DAYS); SKIP = np.array([d in EARLY for d in DAYS])
MGC_XFA_ENTRY = 7 * 60 + 13
_CACHE = {}


def tab(prod, entry_m, kmax=400, tmax=400, synthetic=False, seed=0):
    key = (prod, entry_m, kmax, tmax, synthetic, seed)
    if key not in _CACHE:
        _CACHE[key] = build_synthetic(prod, entry_m, np.random.default_rng(seed), kmax=kmax, tmax=tmax) if synthetic else build_tab(prod, entry_m, kmax=kmax, tmax=tmax)
    return _CACHE[key]


def xfa_series(t, sl, tp, slip=0.0, tp_extra=0):
    """P&L por contrato y dia (USD) de un bracket fijo sl/tp ticks sobre la tabla t, con llenado del stop k + slip*(extremo-k) (peor caso dentro de la barra)."""
    a = t["adv"][:, sl]; b = t["tpt"][:, tp + tp_extra]
    tp_hit = b < a; sl_hit = ~tp_hit & (a < 10 ** 6)
    loss = sl + slip * (t["amag"][:, sl] - sl)
    return np.where(tp_hit, tp * t["tv"], np.where(sl_hit, -loss * t["tv"], t["flat"] * t["tv"])) - t["comm"]


def common_axis(tabs):
    ds = None
    for t in tabs:
        s = set(pd.to_datetime(t["dates"]))
        ds = s if ds is None else ds & s
    return sorted(ds)


def reindex(arr, dates, axis):
    pos = {d: i for i, d in enumerate(pd.to_datetime(dates))}
    return arr[[pos[d] for d in axis]]


def make_spec(c_prod="MES", c_entry=9 * 60 + 45, x_prod="MGC", x_entry=MGC_XFA_ENTRY, nc=40, tp=32, sl=100, x_sl=364, x_tp=364, nc_x=3, slip=0.0, synthetic=False, seed=0, x_dll=None, tp_extra=0, axis=None, **kw):
    kw.setdefault("xliq", True)
    tc = tab(c_prod, c_entry, kmax=800, tmax=800, synthetic=synthetic, seed=seed)
    tx = tab(x_prod, x_entry, kmax=800, tmax=800, synthetic=synthetic, seed=seed + 1) if (x_prod, x_entry) != (c_prod, c_entry) else tc
    axis = common_axis([tc, tx]) if axis is None else axis
    sl_eff = x_sl if x_dll is None else int(min(x_sl, max(np.floor((x_dll - tx["comm"] * nc_x) / (nc_x * tx["tv"])), 1)))
    ser = reindex(xfa_series(tx, sl_eff, x_tp, slip, tp_extra), tx["dates"], axis)
    S = Spec(adv=reindex(tc["adv"], tc["dates"], axis), tpt=reindex(tc["tpt"], tc["dates"], axis), flat=reindex(tc["flat"], tc["dates"], axis),
             amag=reindex(tc["amag"], tc["dates"], axis), tv=tc["tv"], comm=tc["comm"], nc=nc, tp_ticks=tp, sl=sl, slip=slip, xser=ser, nc_x=nc_x, tp_fill_extra=tp_extra,
             xadv=reindex(tx["adv"], tx["dates"], axis), xtpt=reindex(tx["tpt"], tx["dates"], axis), xflat=reindex(tx["flat"], tx["dates"], axis), xamag=reindex(tx["amag"], tx["dates"], axis),
             x_tv=tx["tv"], x_comm=tx["comm"], x_sl=x_sl, x_tp=x_tp, **kw)
    return S, np.array(axis)


def draw(nd, T, seed=2026, mask=None):
    rng = np.random.default_rng(seed)
    pool = np.arange(nd) if mask is None else np.nonzero(mask)[0]
    return pool[rng.integers(0, len(pool), (T, H))]


def gold_mask(axis, exclude=True):
    ax = pd.to_datetime(axis)
    return ~((ax >= GOLD[0]) & (ax <= GOLD[1])) if exclude else np.ones(len(ax), bool)


def make_pool_spec(n_worlds=16, c_prod="MES", c_entry=9 * 60 + 45, x_prod="MGC", x_entry=MGC_XFA_ENTRY, nc=40, tp=32, sl=100, x_sl=364, x_tp=364, nc_x=3, slip=0.5, seed0=1000, x_dll=None, tp_extra=0, **kw):
    """Estimador ESTRUCTURAL de juego justo: concatena n_worlds mundos sinteticos independientes (barras con signo volteado al azar, misma volatilidad) -> un pool de dias iid sin deriva muestral.
    Los productos del Combine y de la XFA se voltean de forma independiente (la correlacion entre productos solo se mide con datos reales)."""
    kw.setdefault("xliq", True)
    parts = []
    for w in range(n_worlds):
        tc = tab(c_prod, c_entry, kmax=800, tmax=800, synthetic=True, seed=seed0 + 2 * w)
        tx = tab(x_prod, x_entry, kmax=800, tmax=800, synthetic=True, seed=seed0 + 2 * w + 1) if (x_prod, x_entry) != (c_prod, c_entry) else tc
        axis = common_axis([tc, tx])
        sl_eff = x_sl if x_dll is None else int(min(x_sl, max(np.floor((x_dll - tx["comm"] * nc_x) / (nc_x * tx["tv"])), 1)))
        parts.append((reindex(tc["adv"], tc["dates"], axis), reindex(tc["tpt"], tc["dates"], axis), reindex(tc["flat"], tc["dates"], axis), reindex(tc["amag"], tc["dates"], axis),
                      reindex(xfa_series(tx, sl_eff, x_tp, slip, tp_extra), tx["dates"], axis), tc, tx, axis))
    tc = parts[0][5]
    S = Spec(adv=np.concatenate([p[0] for p in parts]), tpt=np.concatenate([p[1] for p in parts]), flat=np.concatenate([p[2] for p in parts]), amag=np.concatenate([p[3] for p in parts]),
             tv=tc["tv"], comm=tc["comm"], nc=nc, tp_ticks=tp, sl=sl, slip=slip, xser=np.concatenate([p[4] for p in parts]), nc_x=nc_x, tp_fill_extra=tp_extra,
             xadv=np.concatenate([reindex(p[6]["adv"], p[6]["dates"], p[7]) for p in parts]), xtpt=np.concatenate([reindex(p[6]["tpt"], p[6]["dates"], p[7]) for p in parts]),
             xflat=np.concatenate([reindex(p[6]["flat"], p[6]["dates"], p[7]) for p in parts]), xamag=np.concatenate([reindex(p[6]["amag"], p[6]["dates"], p[7]) for p in parts]),
             x_tv=parts[0][6]["tv"], x_comm=parts[0][6]["comm"], x_sl=x_sl, x_tp=x_tp, **kw)
    return S, np.arange(len(S.flat))


def structural_geometry(prod, entry_m, x_prod=None, x_entry=None, mes_ref=("MES", 9 * 60 + 45), mgc_ref=("MGC", MGC_XFA_ENTRY), cap_nc=50):
    """Geometria ESTRUCTURAL (no depende del rendimiento): el stop del Combine es la liquidacion del MLL y su distancia en ticks es la misma fraccion del rango mediano (entrada->flatten) que en MES (40 ticks);
    nc = 2000/(stop*tv) acotado a [1, cap_nc]; TP = ticks para que cada TP neto sea ~$1,550 (2 TP >= $3,100). XFA: bracket 1:1 de S = mismo multiplo del rango mediano que en Cerebro 2 (728 ticks / rango MGC 7:13),
    contratos para ~$2,184 de riesgo por trade."""
    from scripts.tables_generic import median_range_ticks, SPEC as TS
    import math
    r_mes = median_range_ticks(*mes_ref); r_mgc = median_range_ticks(*mgc_ref)
    stop_ratio = 40.0 / r_mes; x_ratio = 728.0 / r_mgc
    _, tick, tv, comm = TS[prod]
    R = median_range_ticks(prod, entry_m)
    nc = int(np.clip(round(2000.0 / (max(round(stop_ratio * R), 1) * tv)), 1, cap_nc))
    tp = math.ceil((1550.0 + comm * nc) / (tv * nc) - 1e-9)
    xp = x_prod or prod; xe = x_entry or entry_m
    _, _, xtv, xcomm = TS[xp]; Rx = median_range_ticks(xp, xe)
    S = max(int(round(x_ratio * Rx)), 20); ncx = int(np.clip(round(2184.0 / (S * xtv)), 1, 12))
    return dict(nc=nc, tp=tp, x_sl=S, x_tp=S, nc_x=ncx, R=R, Rx=Rx)
