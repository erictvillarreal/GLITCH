"""Due diligence del candidato MGC 143/143 nc=15 (entrada 7:13 CT sin cambios) vs baseline 364/364 nc=6.
Motor EMPIRICO en TODO (bar-walk real + bootstrap del PnL real + Scaling Plan dyn-nc)."""
import sys, time
import numpy as np, pandas as pd
from math import sqrt
from scipy import stats
from dd_wr.mgc_dd_lib import *

S = load_sessions(STEM)
rng0 = np.random.default_rng(2026)
def tr(cfg): return config_trades(S, *cfg)
cand_t, base_t = tr(CAND), tr(BASE)
cp, bp = cand_t.pnl.values, base_t.pnl.values
n = len(cp); nc_c, nc_b = CAND[2], BASE[2]
print(f"MOTOR: empirico (FLATTEN modelado con su distribucion real; NO binario). n={n} sesiones. cand={CAND} base={BASE}\n")

# ---- 1. friccion
print("== 1. FRICCION (p50 cadena 1 año, motor completo). slip = ticks adversos en entrada + salida SL/FLATTEN")
for name, t, nc in (("cand", cand_t, nc_c), ("base", base_t, nc_b)):
    out = []
    for slip in (0, 1, 2, 3, 4):
        p = t.pnl.values - nc * TV * (slip + np.where(t.result.isin(["SL", "FLATTEN"]), slip, 0))
        out.append(f"slip{slip}=${chain(p, nc, 30_000)['p50']:,.0f}")
    p = t.pnl.values - 0.5 * nc * COMM
    out.append(f"comision+50%=${chain(p, nc, 30_000)['p50']:,.0f}")
    print(f"  {name}: " + " | ".join(out), flush=True)

# ---- 2. Kelly analogo
print("\n== 2. KELLY (analogo; el Kelly clasico p-(1-p)/b no aplica a juegos de payoff acotado, ver dd_v2/test2)")
for name, x, nc in (("cand", cp, nc_c), ("base", bp, nc_b)):
    ev, sd = x.mean(), x.std(ddof=1); tstat = ev / (sd / sqrt(len(x)))
    per = x / nc; W = 150_000.0
    def nck(v): return v.mean() * W / (v.var(ddof=1)) if v.var(ddof=1) > 0 else np.nan
    bs = [nck(per[rng0.integers(0, len(per), len(per))]) for _ in range(2000)]
    print(f"  {name}: EV/trade=${ev:,.0f} sd=${sd:,.0f} t={tstat:.2f} (p={2*(1-stats.norm.cdf(abs(tstat))):.3f}) | nc_Kelly(W=$150k)={nck(per):.0f} IC90=[{np.percentile(bs,5):.0f},{np.percentile(bs,95):.0f}] vs nc usado={nc}")

# ---- 3. dependencia
print("\n== 3. DEPENDENCIA ENTRE TRADES")
for name, t in (("cand", cand_t), ("base", base_t)):
    w = (t.pnl.values > 0).astype(int); n1, n0 = w.sum(), len(w) - w.sum()
    runs = 1 + (w[1:] != w[:-1]).sum(); mu = 2 * n1 * n0 / len(w) + 1; var = (mu - 1) * (mu - 2) / (len(w) - 1)
    z = (runs - mu) / sqrt(var)
    x = t.pnl.values - t.pnl.values.mean()
    ac = [np.corrcoef(x[:-k], x[k:])[0, 1] for k in range(1, 6)]
    dow = pd.to_datetime(t.date).dt.dayofweek
    by = t.assign(d=dow).groupby("d").pnl.mean().round(0).to_dict()
    ls = t.groupby("side").pnl.agg(["mean", "count"]).round(0)
    print(f"  {name}: runs z={z:.2f} (p={2*(1-stats.norm.cdf(abs(z))):.3f}) | autocorr lag1-5={[round(a,3) for a in ac]} (banda 95% ±{1.96/sqrt(len(x)):.3f}) | EV por dia-semana {by} | EV long={ls.loc[1,'mean']:.0f}(n={ls.loc[1,'count']}) short={ls.loc[-1,'mean']:.0f}(n={ls.loc[-1,'count']})", flush=True)

# ---- 4. sub-periodos
print("\n== 4. SUB-PERIODOS (motor completo por sub-muestra)")
def per_stats(t, nc, lo, hi):
    x = t.pnl.values[lo:hi]; r = t.result.values[lo:hi]
    tp_, sl_ = (r == "TP").sum(), (r == "SL").sum()
    return f"n={hi-lo} EV=${x.mean():,.0f} WRc={tp_/max(1,tp_+sl_):.3f} FLAT={(r=='FLATTEN').mean():.2f} p50=${chain(x, nc, 30_000)['p50']:,.0f}"
for lbl, (lo, hi) in {"H1": (0, n // 2), "H2": (n // 2, n), "T1": (0, n // 3), "T2": (n // 3, 2 * n // 3), "T3": (2 * n // 3, n)}.items():
    print(f"  {lbl} cand: {per_stats(cand_t, nc_c, lo, hi)}\n  {lbl} base: {per_stats(base_t, nc_b, lo, hi)}", flush=True)

# ---- 5. bootstrap pareado cand vs base (iid y bloques de 10)
print("\n== 5. BOOTSTRAP PAREADO de dias (S = payout esperado/año, estadistico rapido, Spearman 0.997 vs p50 cadena)")
def resample_idx(kind):
    if kind == "iid": return rng0.integers(0, n, n)
    B = 10; starts = rng0.integers(0, n, int(np.ceil(n / B))); return (starts[:, None] + np.arange(B)[None, :]).ravel()[:n] % n
S_c, S_b = fast_S(cp, nc_c), fast_S(bp, nc_b)
print(f"  S observado: cand=${S_c:,.0f} base=${S_b:,.0f} (dif=${S_c-S_b:,.0f}, x{S_c/S_b:.2f})")
for kind in ("iid", "bloque10"):
    d = []
    for _ in range(400):
        ix = resample_idx("iid" if kind == "iid" else "b")
        d.append(fast_S(cp[ix], nc_c) - fast_S(bp[ix], nc_b))
    d = np.array(d)
    print(f"  {kind}: dif media=${d.mean():,.0f} IC90=[${np.percentile(d,5):,.0f}, ${np.percentile(d,95):,.0f}] P(dif>0)={(d>0).mean():.3f}", flush=True)

# ---- 6. Reality Check de White sobre TODA la familia probada en MGC
print("\n== 6. DATA SNOOPING: Reality Check (White 2000) sobre toda la familia de configs MGC probadas en esta rama")
g = pd.read_csv("dd_wr/mgc_width_grid_results.csv"); ps = pd.read_csv("dd_wr/product_sweep_results.csv")
ps = ps[(ps["product"] == "MGC") & ps.p50.notna()]
fam = {(int(r.sl), int(r.tp), int(r.nc)) for _, r in g.iterrows()} | {(int(r.sl), int(r.tp), int(r.nc)) for _, r in ps.iterrows()}
fam.add(BASE); fam.add(CAND); fam = sorted(fam)
print(f"  familia: {len(fam)} configs distintas (grid extendido + barrido de productos MGC + baseline)")
P = {c: tr(c).pnl.values for c in fam}
S_obs = {c: fast_S(P[c], c[2]) for c in fam}
d_obs = {c: S_obs[c] - S_obs[BASE] for c in fam}
best = max(fam, key=lambda c: d_obs[c])
print(f"  mejor de la familia (observado): {best} dif vs base=${d_obs[best]:,.0f}; candidato {CAND} dif=${d_obs[CAND]:,.0f}")
for kind in ("iid", "bloque10"):
    Bn = 1000; V = []
    for b in range(Bn):
        ix = resample_idx("iid" if kind == "iid" else "b")
        Sb = {c: fast_S(P[c][ix], c[2]) for c in fam}
        V.append(max((Sb[c] - Sb[BASE]) - d_obs[c] for c in fam))
        if kind == "iid" and b % 250 == 0: print(f"    ...iid {b}/{Bn}", flush=True)
    V = np.array(V); vobs = max(d_obs[c] for c in fam)
    print(f"  {kind}: V_obs=${vobs:,.0f}; RC p-value = P(max*>=V_obs) = {(V>=vobs).mean():.3f}; percentil 95 de V* = ${np.percentile(V,95):,.0f}", flush=True)
