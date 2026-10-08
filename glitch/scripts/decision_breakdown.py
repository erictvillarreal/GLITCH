"""Desglose de decision: ¿que combinaciones de palancas PROBADAS (TP 32, mas cuentas, cuenta 150K) alcanzan ~US$7,000 al año, y con que riesgo? Motor validado (dd_cash/engine_real, copia con calendario),
Combine con reglas reales (liquidacion MLL en tiempo real, consistencia 55%) + XFA con Cerebro 2/MGC; payouts con ajuste -25% (liquidacion en tiempo real de la XFA, log 24/25-sep); caja = cobrado (5 dias de
demora) - fees (Combine, reinicios, activacion) - costos operativos compartidos $59.5/mes (una sola vez aunque haya N cuentas); cuentas con las MISMAS senales (perfectamente correlacionadas, sin diversificacion).
Horizonte: 19-oct-2026 -> 19-oct-2027. SANDBOX / R&D. Uso: python scripts/decision_breakdown.py"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np, pandas as pd
from dd_cash.data import build
from dd_cash.engine_real import Account
from dd_cash.engine_real_cal import simulate
from scripts.g2_real_rules_scan import build_tables, KMAX, INF, TV
from core.prop_firm import TOPSTEP_50K, TOPSTEP_150K
from core.funded_account import XFA_50K, XFA_150K

OPS = 59.5; HAIR = 0.75; TARGET = 7000.0; FX = 18.0
HOL = {pd.Timestamp(d) for d in ("2026-11-26", "2026-12-25", "2027-01-01", "2027-04-02", "2027-05-31", "2027-07-05", "2027-09-06")}
EARLY = {pd.Timestamp("2026-11-27"), pd.Timestamp("2026-12-24")}
DAYS = [d for d in pd.bdate_range("2026-10-19", "2027-10-19") if d not in HOL]
H = len(DAYS); SKIP = np.array([d in EARLY for d in DAYS])
I31 = max(i for i, d in enumerate(DAYS) if d <= pd.Timestamp("2026-12-31"))


def setup(size, nc, tp, sl, nc_x):
    df = build(); (adv, tpt, flat), dates = build_tables(with_dates=True)
    pos = {d: i for i, d in enumerate(dates)}; keep = [d for d in df.index if d in pos]; rows = [pos[d] for d in keep]
    real = dict(adv=adv[rows], tp=tpt[rows], flat=flat[rows], nc=nc, tv=TV, sl=sl, tp_ticks=tp, comm=1.22, cons=0.55, kmax=KMAX, inf=INF)
    cs, xs = (TOPSTEP_50K, XFA_50K) if size == "50K" else (TOPSTEP_150K, XFA_150K)
    return Account(cs, xs, nc, nc_x, None, df.loc[keep, "mgc"].values), real, len(keep)


def per_account_cash(size, nc, tp, nc_x, T=30000, seed=2026):
    acc, real, nd = setup(size, nc, tp, 100, nc_x)
    D = np.random.default_rng(seed).integers(0, nd, (T, H))
    r = simulate(acc, D, real=real, lag=2, skip=SKIP)
    take = r["take_d"].astype(float) * HAIR
    take = np.concatenate([np.zeros((T, 5)), take[:, :-5]], axis=1)
    return np.cumsum(take - r["fee_d"].astype(float), axis=1)         # caja por cuenta SIN costos compartidos


if __name__ == "__main__":
    ops = np.zeros(H); ops[::21] = OPS; ops_cum = np.cumsum(ops)
    cfgs = [("A. Hoy: 50K, TP 40, 1 cuenta", "50K", 40, 40, 3, 1), ("B. 50K, TP 32, 1 cuenta", "50K", 40, 32, 3, 1), ("C. 50K, TP 32, 2 cuentas (mismas señales)", "50K", 40, 32, 3, 2),
            ("D. 50K, TP 32, 3 cuentas (mismas señales)", "50K", 40, 32, 3, 3), ("E. 150K, TP 32, 1 cuenta (nc 90, Cerebro 2 nc 6)", "150K", 90, 32, 6, 1), ("F. 150K, TP 32, 2 cuentas", "150K", 90, 32, 6, 2)]
    cache = {}; out = []
    P = lambda s: (print(s), out.append(s))
    P(f"Desglose de decision, 12 meses desde 19-oct-2026, payouts -25% por liquidación, costos compartidos $59.5/mes. Meta del usuario: ~US${TARGET:,.0f} al año (~${TARGET/12:,.0f}/mes ≈ {TARGET/12*FX:,.0f} MXN/mes a {FX:.0f} MXN/USD, supuesto)")
    P(f"{'Escenario':52s} {'media':>8s} {'mediana':>8s} {'p10':>8s} {'p90':>8s} {'P(<0)':>6s} {'P(>=7k)':>8s} {'MXN/mes':>8s} {'colchón p95':>11s}")
    for name, size, nc, tp, nx, n in cfgs:
        key = (size, nc, tp, nx)
        if key not in cache: cache[key] = per_account_cash(size, nc, tp, nx)
        c = n * cache[key] - ops_cum[None, :]
        f = c[:, -1]; cushion = -np.minimum(c.min(axis=1), 0)
        P(f"{name:52s} {f.mean():>8,.0f} {np.median(f):>8,.0f} {np.percentile(f,10):>8,.0f} {np.percentile(f,90):>8,.0f} {np.mean(f<0):>6.0%} {np.mean(f>=TARGET):>8.0%} {f.mean()/12*FX:>8,.0f} {np.percentile(cushion,95):>11,.0f}")
    open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dd_cash", "decision_breakdown_report.txt"), "w").write("\n".join(out))
