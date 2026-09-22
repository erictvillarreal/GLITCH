"""Colchon inicial recomendado, 1 cuenta 50K-B (G2 Combine -> transicion manual -> MGC XFA). Motor diario empirico.
cash_d = payouts (con lag de cobro) - fees - operacion ($45/mes, cobrada el dia 0 y cada 21 dias)."""
import numpy as np
from dd_cash.data import build
from dd_cash.engine import Account, simulate
from core.prop_firm import TOPSTEP_50K
from core.funded_account import XFA_50K
OPS = 45.0; T = 40000; H = 252; M = 21
df = build(); n = len(df); third = n // 3
def cash_path(r, pay_lag):
    take = r["take_d"].astype(np.float64)
    if pay_lag: take = np.concatenate([np.zeros((take.shape[0], pay_lag)), take[:, :-pay_lag]], axis=1)
    ops = np.zeros(H); ops[::M] = OPS
    return np.cumsum(take - r["fee_d"], axis=1) - np.cumsum(ops)[None, :]
def run(lo, hi, lag=0, pay_lag=0, seed=11):
    sub = df.iloc[lo:hi]; D = np.random.default_rng(seed).integers(0, len(sub), (T, H))
    a = Account(TOPSTEP_50K, XFA_50K, 40, 3, sub.mes.values, sub.mgc.values)
    r = simulate(a, D, lag=lag); return r, cash_path(r, pay_lag)
def cushion(c, h): return -np.minimum(c[:, :h].min(axis=1), 0)
P = [50, 75, 90, 95, 99]
def line(lbl, r, c):
    c3, c6, c12 = cushion(c, 63), cushion(c, 126), cushion(c, 252)
    print(f"{lbl:34s} colchon 3m p50/75/90/95/99: {'/'.join(f'{v:,.0f}' for v in np.percentile(c3,P))} | 6m: {'/'.join(f'{v:,.0f}' for v in np.percentile(c6,P))} | 12m p95/p99: {np.percentile(c12,95):,.0f}/{np.percentile(c12,99):,.0f}", flush=True)
scen = {"base (2 años)": (0, n), "T1 baja vol": (0, third), "T3 reciente": (n - third, n)}
res = {}
for name, (lo, hi) in scen.items():
    for lag, pl in ((0, 0), (2, 5)):
        r, c = run(lo, hi, lag, pl); res[(name, lag, pl)] = (r, c)
        line(f"{name} | lag transic {lag}d cobro {pl}d", r, c)
r, c = res[("base (2 años)", 0, 0)]
print("\n-- Perfil de caja (base, sin lags): acumulado neto por mes calendario, p10/p50/p90 y P(<0)")
for m in (1, 2, 3, 4, 5, 6, 9, 12):
    v = c[:, m * M - 1]; print(f"  fin mes {m:2d}: {np.percentile(v,10):8,.0f} / {np.percentile(v,50):8,.0f} / {np.percentile(v,90):8,.0f} | P(caja acumulada<0) {np.mean(v<0):.2f}")
print("\n-- Dia del valle y de recuperacion (caja acumulada media/mediana por dia)")
med = np.median(c, axis=0); mean = c.mean(axis=0)
print(f"  mediana: valle ${med[:63].min():,.0f} en dia {med[:63].argmin()+1}; primer dia con mediana>=0: {int(np.argmax(med>=0))+1 if (med>=0).any() else 'nunca'}")
print(f"  media:   valle ${mean[:63].min():,.0f} en dia {mean[:63].argmin()+1}; primer dia con media>=0: {int(np.argmax(mean>=0))+1}")
pay_d = r["take_d"] > 0; first = np.where(pay_d.any(1), pay_d.argmax(1) + 1, 10**6)
print("  dia del PRIMER payout p10/p25/p50/p75/p90:", np.percentile(first[first < 10**6], [10, 25, 50, 75, 90]).round(0), f"| P(sin payout en 3m) {np.mean(first>63):.2f}, 6m {np.mean(first>126):.2f}")
pm = r["pay_m"]
zero = pm[:, :6] <= 0
def longest(row):
    best = cur = 0
    for z in row: cur = cur + 1 if z else 0; best = max(best, cur)
    return best
L = np.array([longest(z) for z in zero[:20000]])
print("  racha maxima de meses seguidos con payout=0 (meses 1-6): P(>=2) %.2f  P(>=3) %.2f  P(>=4) %.2f" % ((L >= 2).mean(), (L >= 3).mean(), (L >= 4).mean()))
fees = r["fee_d"] > 0
print("  fees en el mes 1: media $%.0f (p90 $%.0f) | fees por mes calendario (media): %s" % (r["fee_m"][:, 0].mean(), np.percentile(r["fee_m"][:, 0], 90), " ".join(f"{r['fee_m'][:,m].mean():.0f}" for m in range(6))))
print("  payout medio por mes (1..6): " + " ".join(f"{pm[:,m].mean():.0f}" for m in range(6)))
# P(cushion insuficiente) para colchones concretos
print("\n-- P(la caja acumulada cae por debajo de -C alguna vez) (base | T1 | T3, con lags 2d/5d), horizonte 6 meses")
for C in (500, 1000, 1500, 2000, 2500, 3000, 4000, 5000):
    row = []
    for nm in scen: row.append(f"{np.mean(cushion(res[(nm,2,5)][1],126)>C):.3f}")
    print(f"  colchon ${C:>5,}: " + " | ".join(row))
