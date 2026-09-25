"""P&L 50K-B con el Combine bajo las REGLAS OFICIALES REALES (liquidacion MLL en tiempo real, consistencia 55%, min 2 dias),
XFA con tope de payout OFICIAL del 50K ($2,000, Standard path), fees oficiales ($49 Combine, $149 activacion).
Costos fijos: Massive $43.5 + Pi $1.5 + API ProjectX $14.5 (con codigo 'topstep')."""
import sys, dataclasses, numpy as np
from dd_cash.data import build
from dd_cash.engine_real import Account, simulate
from scripts.g2_real_rules_scan import build_tables, KMAX, INF, TV
from core.prop_firm import TOPSTEP_50K
from core.funded_account import XFA_50K

def setup(nc=40, tp=40, sl=100):
    df = build(); (adv, tpt, flat), dates = build_tables(with_dates=True)
    pos = {d: i for i, d in enumerate(dates)}
    keep = [d for d in df.index if d in pos]; rows = [pos[d] for d in keep]
    mgc = df.loc[keep, "mgc"].values
    real = dict(adv=adv[rows], tp=tpt[rows], flat=flat[rows], nc=nc, tv=TV, sl=sl, tp_ticks=tp, comm=1.22, cons=0.55, kmax=KMAX, inf=INF)
    xfa = dataclasses.replace(XFA_50K, payout_cap_usd=2000.0)
    return Account(TOPSTEP_50K, xfa, nc, 3, None, mgc), real, len(keep)

def run(nc=40, tp=40, sl=100, T=20000, H=252, seed=2026, lag=0):
    acc, real, nd = setup(nc, tp, sl)
    D = np.random.default_rng(seed).integers(0, nd, (T, H))
    return simulate(acc, D, real=real, lag=lag), nd

if __name__ == "__main__":
    OPS = 43.5 + 1.5 + 14.5
    for label, (nc, tp, sl) in (("G2 actual (nc40 TP40 SL100)", (40, 40, 100)), ("alt. mejor bajo reglas reales (nc25 TP50 SL40)", (25, 50, 40))):
        r, nd = run(nc, tp, sl)
        fp = r["first_pass"]
        print(f"\n########## {label} | dias alineados={nd} | validacion 1er Combine: pase={np.mean(fp==1):.3f} dias={r['first_day'][fp==1].mean():.2f}")
        pay, fc, fa = r["pay_m"], r["fee_c_m"], r["fee_a_m"]
        net = pay - fc - fa - OPS; cum = np.cumsum(net, axis=1)
        print("mes:      " + " ".join(f"{m+1:6d}" for m in range(12)))
        print("payout:   " + " ".join(f"{v:6.0f}" for v in np.median(pay, axis=0)))
        print("fee_comb: " + " ".join(f"{v:6.0f}" for v in np.median(fc, axis=0)))
        print("fee_act:  " + " ".join(f"{v:6.0f}" for v in np.median(fa, axis=0)))
        print("neto mes: " + " ".join(f"{v:6.0f}" for v in np.median(net, axis=0)))
        for q in (10, 50, 90): print(f"acum p{q}: " + " ".join(f"{v:6.0f}" for v in np.percentile(cum, q, axis=0)))
        print("MEDIA neto/mes: " + " ".join(f"{v:6.0f}" for v in net.mean(axis=0)), "| media steady m3-12:", round(net.mean(axis=0)[2:].mean()))
        print("Q1..Q4 (suma medianas mensuales):", [round(np.median(net, axis=0)[q*3:q*3+3].sum()) for q in range(4)],
              "| payout", [round(np.median(pay, axis=0)[q*3:q*3+3].sum()) for q in range(4)],
              "| fees", [round(np.median(fc+fa, axis=0)[q*3:q*3+3].sum()) for q in range(4)])
        tot = pay.sum(1); fees = (fc + fa).sum(1)
        print(f"ANUAL: payout p10/p50/p90 = {np.percentile(tot,10):,.0f}/{np.percentile(tot,50):,.0f}/{np.percentile(tot,90):,.0f} | fees media {fees.mean():,.0f} | neto acumulado 12m p10/p50/p90 = {np.percentile(cum[:,-1],10):,.0f}/{np.percentile(cum[:,-1],50):,.0f}/{np.percentile(cum[:,-1],90):,.0f} | P(año<0)={np.mean(cum[:,-1]<0):.2f}")
        med = np.percentile(np.cumsum(r["take_d"] - r["fee_d"] - OPS / 21, axis=1), 50, axis=0)
        fd = int(np.argmax(med >= 0)) + 1 if (med >= 0).any() else None
        print(f"primer dia con caja acumulada MEDIANA >= 0: dia {fd} (mes {-(-fd//21) if fd else None})")
        first = np.where((r['take_d'] > 0).any(1), (r['take_d'] > 0).argmax(1) + 1, 10**6)
        print(f"dia del primer payout p10/p50/p90: {np.percentile(first[first<10**6],[10,50,90])} | P(sin payout en 3m)={np.mean(first>63):.2f} 6m={np.mean(first>126):.2f}")
        for lag, pl in ((0, 0), (2, 5)):
            r2, _ = run(nc, tp, sl, T=30000, seed=11, lag=lag)
            take = r2["take_d"].astype(float)
            if pl: take = np.concatenate([np.zeros((take.shape[0], pl)), take[:, :-pl]], axis=1)
            ops = np.zeros(252); ops[::21] = OPS
            c = np.cumsum(take - r2["fee_d"], axis=1) - np.cumsum(ops)[None, :]
            cu6 = -np.minimum(c[:, :126].min(axis=1), 0); cu3 = -np.minimum(c[:, :63].min(axis=1), 0)
            print(f"COLCHON (lag transic {lag}d, cobro {pl}d): 3m p90/p95/p99 = {np.percentile(cu3,90):,.0f}/{np.percentile(cu3,95):,.0f}/{np.percentile(cu3,99):,.0f} | 6m p90/p95/p99 = {np.percentile(cu6,90):,.0f}/{np.percentile(cu6,95):,.0f}/{np.percentile(cu6,99):,.0f} | P(caja acum<0) fin m1/m3/m6 = {np.mean(c[:,20]<0):.2f}/{np.mean(c[:,62]<0):.2f}/{np.mean(c[:,125]<0):.2f}")
