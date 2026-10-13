"""T1 — Tamano de posicion del Combine (nc = 10/16/25/40; TP40 vs TP32, SL 100 ticks; perfil nc=25 TP50 SL40). Motor dd_cash/lever_engine.py, convencion structural-levers
(liquidacion explicita XFA, slip stop 0.5, fees completos, 12 meses desde 19-oct-2026; mundo justo / real CON oro / real SIN oro). El efecto del tope local GLITCH_PI_NC_MAX del Pi (mismos ticks, menos contratos) es
exactamente una fila nc<40. SANDBOX / R&D. Uso: python -m scripts.t1_combine_size"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import math, numpy as np, dataclasses as dc
from dd_cash import lever_data as LD
from dd_cash.lever_engine import simulate
from scripts.lever_common import run, OPS12

lines = []; P = lambda s: (print(s), lines.append(s))
T = 20000; H = LD.H
CONFIGS = [(10, 40, 100), (10, 32, 100), (16, 40, 100), (16, 32, 100), (25, 40, 100), (25, 32, 100), (25, 50, 40), (40, 40, 100), (40, 32, 100)]
COMM = 1.22; TV = 1.25


def tp_days(nc, tp):
    net = tp * TV * nc - COMM * nc
    return net, max(2, math.ceil(3000.0 / net - 1e-9))


def worlds(nc, tp, sl, x):
    out = {}
    Sf, axf = LD.make_pool_spec(n_worlds=60, nc=nc, tp=tp, sl=sl, slip=0.5, **x); out["justo"] = (Sf, axf, None)
    Sr, axr = LD.make_spec(nc=nc, tp=tp, sl=sl, slip=0.5, **x); out["CON oro"] = (Sr, axr, None); out["SIN oro"] = (Sr, axr, LD.gold_mask(axr))
    return out


def single_attempt(S, ax, mask):
    pool = np.arange(len(ax)) if mask is None else np.nonzero(mask)[0]
    D = pool[np.random.default_rng(7).integers(0, len(pool), (T, 40))]
    r = simulate(dc.replace(S, K=1), D, lag=2, skip=None)
    passed = r["pass_day"] > 0
    return passed.mean(), (np.median(r["pass_day"][passed]) if passed.any() else float("nan")), (r["n_b0"] > 0).mean()


if __name__ == "__main__":
    for xlab, x in (("XFA vigente Cerebro 2 (MGC 364x3)", dict(x_sl=364, x_tp=364, nc_x=3)), ("XFA propuesta (MGC 728x3, pendiente de aprobacion)", dict(x_sl=728, x_tp=728, nc_x=3))):
        P(f"\n=== {xlab} ===")
        P(f"{'nc':>3s} {'TP':>3s} {'SL':>4s} | {'TP neto$':>8s} {'dias TP':>7s} | {'pase/intento (j/CON/SIN)':>25s} {'dias a pase':>11s} {'liq<SL':>7s} {'stop/dia':>8s} | {'neto 1 cta: justo':>17s} {'CON oro':>8s} {'SIN oro':>8s} | {'P(<0) j/CON/SIN':>16s} | {'intent.':>7s} {'$/intento':>9s} {'$/pase':>7s}")
        for nc, tp, sl in CONFIGS:
            W = worlds(nc, tp, sl, x); nets = {}; pneg = {}; ps = {}; extra = {}
            for k, (S, ax, mask) in W.items():
                o = run(S, ax, mask=mask, T=T); n = o["net"] - OPS12
                nets[k] = n.mean(); pneg[k] = np.mean(n < 0)
                p1, dpass, _ = single_attempt(S, ax, mask); ps[k] = p1
                if k == "justo":
                    r = simulate(S, LD.draw(len(ax), 8000, 9), lag=2, skip=LD.SKIP)
                    extra = dict(dpass=dpass, liq=r["n_liq"].sum() / max(r["n_ctr"].sum(), 1), slh=r["n_slhit"].sum() / max(r["n_ctr"].sum(), 1), att=o["att"].mean(),
                                 comm=(r["n_trades_c"].sum() / r["n_att"].sum()) * nc * COMM, pas=r["n_pass"].sum())
            net_tp, dtp = tp_days(nc, tp)
            cost_att = 49.0 + extra["comm"]; cost_pass = cost_att / max(ps["justo"], 1e-9) + 149.0
            P(f"{nc:>3d} {tp:>3d} {sl:>4d} | {net_tp:>8,.0f} {dtp:>7d} | {ps['justo']:>7.1%} {ps['CON oro']:>8.1%} {ps['SIN oro']:>8.1%} {extra['dpass']:>11.0f} {extra['liq']:>7.0%} {extra['slh']:>8.0%} | {nets['justo']:>17,.0f} {nets['CON oro']:>8,.0f} {nets['SIN oro']:>8,.0f} | {pneg['justo']:>5.0%}/{pneg['CON oro']:>4.0%}/{pneg['SIN oro']:>4.0%} | {extra['att']:>7.0f} {cost_att:>9,.0f} {cost_pass:>7,.0f}")
    open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dd_cash", "t1_combine_size_report.txt"), "w").write("\n".join(lines))
