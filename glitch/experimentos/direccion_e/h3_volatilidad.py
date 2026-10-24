"""Parte H, H3: pruebas P1-P7 de PREREGISTRO_H3.md + prueba 8 (usos del pronóstico bajo escenarios de WR) + estacionalidad intradía descriptiva. -> resultados_H3.md
    GLITCH_MGC_PARQUET=... python h3_volatilidad.py [--part stats|money|season|all]"""
import argparse, datetime as dt, json, math, os, sys, time
import numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "..", "xfa")); sys.path.insert(0, os.path.join(HERE, "..", "preservacion"))
from common_e import load_daily
from chain import combine_bank, run_chain, xfa_bank
from daydata import DEFAULT_PARQUET, load_days, sim_day
from strategies.geometry_pure import decide_side, trading_day_index
from worlds import MGC, drift_for_wr, gold_mask, mgc_days
from xfa_engine import BarDays, Rules, pol_fixed, simulate_life
from scaled_days import ScaledDays
ap = argparse.ArgumentParser(); ap.add_argument("--part", default="all"); a = ap.parse_args()
SEED = 20261024; t0 = time.time(); out = []; P = lambda s="": (print(s, flush=True), out.append(s)); pv = {}
rng = np.random.default_rng(SEED)
def block_idx(n, block, B, r):
    nb = math.ceil(n / block); st = r.integers(0, n - block + 1, size=(B, nb)); return (st[:, :, None] + np.arange(block)[None, None, :]).reshape(B, -1)[:, :n]
def oos_se(y, X, min_train=756):
    d = pd.concat([y.rename("y"), X], axis=1).dropna(); cols = list(X.columns); se, idx = [], []
    for Y in sorted(set(d.index.year)):
        tr, te = d[d.index < f"{Y}-01-01"], d[d.index.year == Y]
        if len(tr) < min_train or len(te) == 0: continue
        A = np.c_[np.ones(len(tr)), tr[cols].values]; beta = np.linalg.lstsq(A, tr.y.values, rcond=None)[0]
        pr = (np.c_[np.ones(len(te)), te[cols].values] * beta).sum(1); se += list((te.y.values - pr) ** 2); idx += list(te.index)
    return pd.Series(se, index=idx), d
def gain_test(label, key, y, base, add):
    se0, d0 = oos_se(y, base); X1 = pd.concat([base, add], axis=1); se1, d1 = oos_se(y, X1)
    common = se0.index.intersection(se1.index); se0, se1 = se0[common], se1[common]
    ybar = y.reindex(common); bench = np.array([y[y.index < f"{i.year}-01-01"].mean() for i in common]); sseb = ((ybar.values - bench) ** 2).sum()
    r0, r1 = 1 - se0.sum() / sseb, 1 - se1.sum() / sseb; diff = (se0 - se1).values
    ix = block_idx(len(diff), 20, 5000, np.random.default_rng(SEED)); p = float((diff[ix].mean(1) <= 0).mean()); pv[key] = p
    yrs = {Y: (se0[[i.year == Y for i in common]].sum() - se1[[i.year == Y for i in common]].sum()) for Y in sorted(set(i.year for i in common))}
    P(f"\n### {key} — {label}\n- R²_OOS sin = {r0 * 100:.2f} %, con = {r1 * 100:.2f} % ⇒ **ΔR² = {(r1 - r0) * 100:+.2f} pp** ({len(diff):,} días, {common.min().year}–{common.max().year}); años con mejora: {sum(v > 0 for v in yrs.values())}/{len(yrs)}; p unilateral = {p:.4f}.")
def har(y):
    return pd.DataFrame({"l1": y.shift(1), "m5": y.shift(1).rolling(5).mean(), "m20": y.shift(1).rolling(20).mean()})
P("# resultados_H3 — volatilidad ampliada (pre-registro `PREREGISTRO_H3.md`, commit 6e2cd85, antes de estos resultados)\n")
if a.part in ("stats", "all"):
    gs = load_daily("^GSPC"); gs = gs[gs.High > gs.Low]; gc = load_daily("GC=F"); gc = gc[(gc.Volume > 0) & (gc.High > gc.Low)]
    ygs, ygc = np.log(gs.High / gs.Low), np.log(gc.High / gc.Low)
    vix = pd.read_csv(os.path.join(HERE, "data", "VIX.csv"), index_col=0, parse_dates=True)["Close"]; gvz = pd.read_csv(os.path.join(HERE, "data", "GVZ.csv"), index_col=0, parse_dates=True)["Close"]
    gap = np.abs(np.log(gs.Open / gs.Close.shift(1)))
    bS = har(ygs).assign(gap=gap)
    vx = pd.DataFrame({"lvix": np.log(vix.shift(1)), "dlvix": np.log(vix).diff().shift(1)}).reindex(ygs.index)
    gz = pd.DataFrame({"lgvz": np.log(gvz.shift(1)), "dlgvz": np.log(gvz).diff().shift(1)}).reindex(ygc.index)
    dow = lambda idx: pd.DataFrame({f"d{k}": (idx.weekday == k).astype(float) for k in range(4)}, index=idx)
    gain_test("VIX (nivel y cambio de t−1) sobre HAR3 + |brecha|, ^GSPC", "P1 VIX ^GSPC", ygs, bS, vx)
    gain_test("GVZ (nivel y cambio de t−1) sobre HAR3, GC=F", "P2 GVZ GC=F", ygc, har(ygc), gz)
    gain_test("día de la semana sobre HAR3 + |brecha|, ^GSPC", "P3 DOW ^GSPC", ygs, bS, dow(ygs.index))
    gain_test("día de la semana sobre HAR3, GC=F", "P4 DOW GC=F", ygc, har(ygc), dow(ygc.index))
if a.part in ("hour", "all"):
    P("\n### P5/P6 — hora de entrada en MES (P(pasar) desde cuenta nueva, P0, nc 40, TP 32/liq 40, slip mezcla {1,3}, 15 días)")
    refs = {"9:35 (base)": 570, "10:30": 625, "11:30": 685, "12:30": 745}
    dds = {k: load_days(DEFAULT_PARQUET, ref_hm=v, last_hm=14 * 60 + 25) for k, v in refs.items()}
    common = sorted(set.intersection(*[set(d.dates) for d in dds.values()])); imap = {k: np.array([d.dates.index(x) for x in common]) for k, d in dds.items()}
    Bn = 200; r2 = np.random.default_rng(SEED); pools = block_idx(len(common), 5, Bn, r2)
    def passp(k, pool_c, nb=20000):
        ps, cd = combine_bank(dds[k], nb, "P0", (1.0, 3.0), (0.5, 0.5), seed=11, maxdays=15, pool=imap[k][pool_c]); return ps.mean(), cd.mean()
    res = {k: np.array([passp(k, p)[0] for p in pools]) for k in refs}
    pt = {k: passp(k, np.arange(len(common)), 100000) for k in refs}
    P(f"- {len(common)} días comunes a las 4 horas. P(pasar) [IC95 bootstrap]: " + " · ".join(f"{k}: {pt[k][0] * 100:.1f} % [{np.percentile(res[k], 2.5) * 100:.1f}, {np.percentile(res[k], 97.5) * 100:.1f}] (días {pt[k][1]:.2f})" for k in refs))
    for k, nm in (("10:30", "P5 hora 10:30"), ("12:30", "P6 hora 12:30")):
        d = res[k] - res["9:35 (base)"]; pv[nm] = float((d <= 0).mean())
        P(f"- **{nm}**: Δ P(pasar) = {(pt[k][0] - pt['9:35 (base)'][0]) * 100:+.1f} pp, IC95 [{np.percentile(d, 2.5) * 100:+.1f}, {np.percentile(d, 97.5) * 100:+.1f}]; p unilateral (Δ > 0) = {pv[nm]:.3f}")
    d = res["11:30"] - res["9:35 (base)"]; P(f"- 11:30 (solo descriptivo): Δ = {(pt['11:30'][0] - pt['9:35 (base)'][0]) * 100:+.1f} pp [{np.percentile(d, 2.5) * 100:+.1f}, {np.percentile(d, 97.5) * 100:+.1f}]")
json.dump(pv, open(os.path.join(HERE, "h3_pvals_%s.json" % a.part), "w"))
open(os.path.join(HERE, "resultados_H3_%s.md" % a.part), "w", encoding="utf-8").write("\n".join(out))
