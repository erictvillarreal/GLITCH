"""P&L 50K-B: EXTRAE de la MISMA simulacion ya corrida (motor diario empirico, seed 11, T=40000, base 2 años, sin lags),
no es un modelo nuevo. Caso mediano = cohorte de trayectorias cuya utilidad acumulada al mes 12 esta entre p45 y p55;
cada renglon = promedio de la cohorte por mes (renglones aditivos)."""
import numpy as np
from dd_cash.data import build
from dd_cash.engine import Account, simulate
from core.prop_firm import TOPSTEP_50K
from core.funded_account import XFA_50K
MASSIVE, PI = 43.5, 1.5; T, H, M = 40000, 252, 21
df = build(); n = len(df)
D = np.random.default_rng(11).integers(0, n, (T, H))
r = simulate(Account(TOPSTEP_50K, XFA_50K, 40, 3, df.mes.values, df.mgc.values), D)
take, fee = r["take_d"].astype(float), r["fee_d"].astype(float)
act_d = np.where(np.isclose(fee, TOPSTEP_50K.activation_fee), fee, 0.0); cmb_d = fee - act_d
def mon(x): return x.reshape(T, 12, M).sum(2)
pay, act, cmb = mon(take), mon(act_d), mon(cmb_d)
ops = MASSIVE + PI
net = pay - act - cmb - ops
cum = np.cumsum(net, axis=1)
p = np.percentile(cum[:, 11], [10, 45, 50, 55, 90]); print("cum mes12 p10/p45/p50/p55/p90:", p.round(0))
med = np.median(cum, axis=0); spread = np.percentile(cum, 75, axis=0) - np.percentile(cum, 25, axis=0)
dist = (((cum - med) / spread) ** 2).sum(1)
coh = dist <= np.sort(dist)[1000]; print("cohorte (1000 trayectorias mas cercanas a la trayectoria mediana en los 12 meses):", coh.sum())
row = lambda a: a[coh].mean(0)
P, A, C = row(pay), row(act), row(cmb); N = P - A - C - ops; CU = np.cumsum(N)
np.set_printoptions(linewidth=200, suppress=True)
print("Payouts   ", P.round(0)); print("FeesCombine", C.round(0)); print("Activacion", A.round(0)); print("Neta      ", N.round(0)); print("Acumulada ", CU.round(0))
print("Mediana de TODAS las trayectorias, acumulada mes 1..12:", np.median(cum, axis=0).round(0))
print("Media de TODAS, neta mensual meses 4-12: %.0f | meses 2-12: %.0f | cohorte meses 4-12: %.0f" % (net[:, 3:].mean(), net[:, 1:].mean(), N[3:].mean()))
print("Todas las trayectorias: mediana acumulada positiva por primera vez en mes:", int(np.argmax(np.median(cum, axis=0) > 0)) + 1)
print("p10/p90 acumulada mes 12:", np.percentile(cum[:, 11], [10, 90]).round(0))
print("Totales cohorte: ingresos %.0f egresos %.0f neta %.0f | fees combine %.0f activ %.0f massive %.0f pi %.0f" % (P.sum(), C.sum() + A.sum() + 12 * ops, N.sum(), C.sum(), A.sum(), 12 * MASSIVE, 12 * PI))
np.save("dd_cash/pnl_cohort_rows.npy", np.vstack([P, C, A, np.full(12, MASSIVE), np.full(12, PI), N, CU]))
