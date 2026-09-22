import sys, numpy as np, pandas as pd
from dd_cash.data import build
from dd_cash.engine import Account, simulate, DAYS_PER_MONTH
from core.prop_firm import TOPSTEP_50K, TOPSTEP_100K, TOPSTEP_150K
from core.funded_account import XFA_50K, XFA_100K, XFA_150K

OPS = 45.0   # Massive $43.5 (rango $29-58) + Pi ~$1.5 (luz ~$0.5 + hardware amortizado ~$1); fijo, no escala con # de cuentas
T, H = 20000, 252
df = build(); mgc, mes = df.mgc.values, df.mes.values; n = len(df)
SIZES = {"50K": (TOPSTEP_50K, XFA_50K, 3, 40), "100K": (TOPSTEP_100K, XFA_100K, 4, 80), "150K": (TOPSTEP_150K, XFA_150K, 6, 120)}
def acct(size, pipe):
    cs, xs, ncx, ncg2 = SIZES[size]
    return Account(cs, xs, ncx if pipe == "A" else ncg2, ncx, mgc if pipe == "A" else mes, mgc, f"{size}-{pipe}")
def Dmat(seed): return np.random.default_rng(seed).integers(0, n, (T, H))
D0 = Dmat(2026)
PC = [10, 25, 50, 75, 90]
def pct(x): return " ".join(f"{v:9,.0f}" for v in np.percentile(x, PC))
def cushion(cum): return -np.minimum(cum.min(axis=1), 0)

print(f"MOTOR: diario empirico (FLATTEN real, timing real). T={T} trayectorias, {H} dias = 12 meses de {DAYS_PER_MONTH}d. Fix balance>0 en payout. OPS=${OPS}/mes\n")
R = {}
for size in SIZES:
    for pipe in "AB":
        R[(size, pipe)] = simulate(acct(size, pipe), D0)
        R[(size, pipe, "asis")] = simulate(acct(size, pipe), D0, fix_neg=False)

print("== 1. UNA CUENTA, 12 meses: payout total (p10 p25 p50 p75 p90) | media | P(>=1 payout) | fees/año | neto/año p10 p50 p90 | P(neto año<0)")
for size in SIZES:
    for pipe in "AB":
        r = R[(size, pipe)]; tot = r["pay_m"].sum(1); fees = r["fee_m"].sum(1); net = tot - fees - OPS * 12
        asis = R[(size, pipe, "asis")]["pay_m"].sum(1)
        print(f"{size:>4}-{pipe} payout: {pct(tot)} | media {tot.mean():8,.0f} | P>=1 {np.mean(r['n_pay']>0):.2f} | fees {fees.mean():6,.0f} | neto {np.percentile(net,10):8,.0f} {np.percentile(net,50):8,.0f} {np.percentile(net,90):8,.0f} | P(neto<0) {np.mean(net<0):.2f} | (as-is p50 {np.median(asis):,.0f})")

print("\n== 3. DISTRIBUCION MENSUAL (una cuenta). Meses 4-12 agrupados = regimen estable. payout p10 p25 p50 p75 p90 | P(payout=0) | neto mensual (payout-fees-OPS) p10 p50 p90 | P(neto<0)")
rows = []
for size in SIZES:
    for pipe in "AB":
        r = R[(size, pipe)]; pm = r["pay_m"][:, 3:].ravel(); nm = (r["pay_m"] - r["fee_m"] - OPS)[:, 3:].ravel()
        print(f"{size:>4}-{pipe} {pct(pm)} | P0 {np.mean(pm<=0):.2f} | neto {np.percentile(nm,10):7,.0f} {np.percentile(nm,50):7,.0f} {np.percentile(nm,90):7,.0f} | P(neto<0) {np.mean(nm<0):.2f} | media neto {nm.mean():7,.0f}")
print("\nP(payout=0) y mediana de payout por mes calendario (1..12):")
for size in SIZES:
    for pipe in "AB":
        pm = R[(size, pipe)]["pay_m"]
        print(f"{size:>4}-{pipe} P0: " + " ".join(f"{np.mean(pm[:,m]<=0):.2f}" for m in range(12)) + " | mediana: " + " ".join(f"{np.median(pm[:,m]):5.0f}" for m in range(12)))

print("\n== 2. CINCO CUENTAS DEL MISMO TAMAÑO (correlacionado = mismas 5 replicas; independiente = referencia irreal)")
for size in SIZES:
    for pipe in "AB":
        r = R[(size, pipe)]; tot = 5 * r["pay_m"].sum(1); cu = 5 * cushion(r["cum"]); fees = 5 * r["fee_m"].sum(1)
        ind = [simulate(acct(size, pipe), Dmat(100 + k)) for k in range(5)]
        ind_tot = sum(x["pay_m"].sum(1) for x in ind); ind_cu = cushion(sum(x["cum"] for x in ind))
        net = tot - fees - OPS * 12
        print(f"5x{size:>4}-{pipe} CORR payout: {pct(tot)} | colchon p50/p90 {np.median(cu):7,.0f}/{np.percentile(cu,90):7,.0f} | neto año p10/p50/p90 {np.percentile(net,10):8,.0f}/{np.percentile(net,50):8,.0f}/{np.percentile(net,90):8,.0f}")
        print(f"{'':11}IND  payout: {pct(ind_tot)} | colchon p90 {np.percentile(ind_cu,90):7,.0f} (subestima {np.percentile(cu,90)/max(1,np.percentile(ind_cu,90)):.1f}x)")

print("\n== 5. MEZCLAS DE TAMAÑO (mismas D para todas las cuentas = mismo mercado). Pipeline A y B")
MIX = {"5x150K": {"150K": 5}, "5x100K": {"100K": 5}, "5x50K": {"50K": 5}, "2x150K+2x100K+1x50K": {"150K": 2, "100K": 2, "50K": 1}, "3x100K+2x50K": {"100K": 3, "50K": 2}, "1x150K": {"150K": 1}}
for pipe in "AB":
    print(f"-- pipeline {pipe}")
    for name, comp in MIX.items():
        pm = sum(k * R[(s, pipe)]["pay_m"] for s, k in comp.items()); fm = sum(k * R[(s, pipe)]["fee_m"] for s, k in comp.items())
        cum = sum(k * R[(s, pipe)]["cum"] for s, k in comp.items())
        tot = pm.sum(1); net_m = (pm - fm - OPS)[:, 3:].ravel(); net_y = tot - fm.sum(1) - OPS * 12
        cv = tot.std() / tot.mean()
        print(f"{name:>22}: payout/año {pct(tot)} | media {tot.mean():8,.0f} CV {cv:.2f} | mes(4-12) P(payout=0) {np.mean(pm[:,3:]<=0):.2f} P(neto<0) {np.mean(net_m<0):.2f} | neto/mes p10/p50/p90 {np.percentile(net_m,10):7,.0f}/{np.percentile(net_m,50):7,.0f}/{np.percentile(net_m,90):7,.0f} | colchon p90 {np.percentile(cushion(cum),90):7,.0f} | P(neto año<0) {np.mean(net_y<0):.2f}")
    ann = {s: R[(s, pipe)]["pay_m"].sum(1) for s in SIZES}
    print("   correlacion de payout anual entre tamaños (mismo mercado): 50K-100K %.2f | 50K-150K %.2f | 100K-150K %.2f" % (np.corrcoef(ann["50K"], ann["100K"])[0, 1], np.corrcoef(ann["50K"], ann["150K"])[0, 1], np.corrcoef(ann["100K"], ann["150K"])[0, 1]))
    print("   payout medio/año por $ de MLL: " + " | ".join(f"{s}: {ann[s].mean()/SIZES[s][1].mll_distance:.2f}" for s in SIZES))
