"""Brazo de investigación (28-oct-2026): arnés pre-registrado (PREREGISTRO_EDGE.md) para H-A/H-B/H-C. Acepta cualquier parquet de 5 min (índice UTC; columnas open, high, low, close, volume, contract).
    cd glitch/experimentos/accion; PYTHONPATH=../.. python3 edge_busqueda.py [--data-dir ../../data_cache] [--suffix _5min_2y]  -> resultados_EDGE_<etiqueta>.md
Con los 2 años locales es un DRY-RUN: todo «sin potencia»."""
import argparse, math, os, sys
import numpy as np, pandas as pd
from scipy.stats import binomtest
ap = argparse.ArgumentParser(); ap.add_argument("--data-dir", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data_cache")); ap.add_argument("--tag", default="dryrun_2y")
ap.add_argument("--files", default="MES:mes_5min_2y.parquet,MNQ:mnq_5min_2y.parquet,M2K:m2k_5min_2y.parquet,MGC:mgc_5min_2y_corrected_window.parquet,MCL:mcl_5min_2y.parquet,M6E:m6e_5min_2y.parquet,ZN:zn_5min_2y.parquet")
A = ap.parse_args()
TICK = {"MES": 0.25, "MNQ": 0.25, "M2K": 0.1, "MGC": 0.1, "MCL": 0.01, "M6E": 0.0001, "ZN": 0.015625}
rng = np.random.default_rng(20261028)
def daily_prices(path):
    d = pd.read_parquet(path).tz_convert("America/Chicago"); d["date"] = d.index.date; d["hm"] = d.index.hour * 60 + d.index.minute
    rows = []
    for dt_, x in d.groupby("date"):
        if x.contract.nunique() > 1: x = x[x.contract == x.groupby("contract")["volume"].sum().idxmax()]
        x = x.drop_duplicates("hm").set_index("hm")
        need = [510, 535, 515, 715, 835, 865, 805, 885]       # barras que empiezan 8:30, 8:55, 8:35, 11:55, 13:55, 14:25, 13:25 (para 13:30), 14:45
        if not {510, 515, 535, 715, 835, 865, 805}.issubset(set(x.index)): continue
        rows.append(dict(date=dt_, o830=x.loc[510, "open"], c835=x.loc[515, "close"], c900=x.loc[535, "close"], c1200=x.loc[715, "close"], c1400=x.loc[835, "close"], c1430=x.loc[865, "close"], c1330=x.loc[805, "close"],
                         c1500=float(x.loc[885, "close"]) if 885 in x.index else float(x["close"].iloc[-1])))
    df = pd.DataFrame(rows).sort_values("date").reset_index(drop=True); df["prev_close"] = df["c1500"].shift(1); return df
def blockci(x, B=2000):
    n = len(x); nb = math.ceil(n / 5); st = rng.integers(0, max(n - 4, 1), size=(B, nb)); idx = (st[:, :, None] + np.arange(5)).reshape(B, -1)[:, :n] % n
    m = x[idx].mean(1); return np.percentile(m, 2.5), np.percentile(m, 97.5)
def mde_pp(n, alpha): from statistics import NormalDist; Z = NormalDist().inv_cdf; return (Z(1 - alpha / 2) + Z(0.8)) * 0.5 / math.sqrt(n) * 100
tests = []
for item in A.files.split(","):
    p, fn = item.split(":"); df = daily_prices(os.path.join(A.data_dir, fn)); t = TICK[p]
    s1 = np.sign(df.c900 - df.o830); r_last = (df.c1430 - df.c1400) / t
    tests.append((f"H-A {p}", p, (s1 * r_last).to_numpy(), df.date))
    gap = df.o830 - df.prev_close; thr = np.nanmedian(np.abs(gap)); sel = np.abs(gap) >= thr
    tests.append((f"H-B {p}", p, np.where(sel, (-np.sign(gap)) * (df.c1200 - df.c835) / t, np.nan), df.date))
    if p in ("MES", "MNQ", "M2K"): tests.append((f"H-C {p}", p, ((df.c1430 - df.c1330) / t).to_numpy(), df.date))
rows = []
for nm, p, x, dates in tests:
    x = np.asarray(x, float); ok = np.isfinite(x) & (x != 0); xs = x[ok]; n = len(xs); k = int((xs > 0).sum())
    bt = binomtest(k, n, 0.5); half = n // 2
    acc1, acc2 = (xs[:half] > 0).mean(), (xs[half:] > 0).mean(); lo, hi = blockci(xs)
    rows.append(dict(nm=nm, n=n, acc=k / n, p=bt.pvalue, mean=xs.mean(), lo=lo, hi=hi, a1=acc1, a2=acc2, mde=mde_pp(n, 0.05 / 33)))
m = 33; order = sorted(range(len(rows)), key=lambda i: rows[i]["p"]); adj = {}; running = 0.0
for rank, i in enumerate(order): running = max(running, min(1.0, rows[i]["p"] * (m - rank))); adj[i] = running
out = [f"# resultados_EDGE_{A.tag} — arnés pre-registrado (H-A, H-B, H-C)\n", f"**Datos:** `{A.data_dir}` ({A.tag}). Holm sobre m = 33 (16 de la Parte E con p = 1 + estas {len(rows)} + hipótesis futuras de la familia). «Sin potencia» = MDE (80 %, α = 0.05/33) > 3 pp.\n",
       "| prueba | n | exactitud | p bilateral | p Holm | ticks medios por trade [IC95 bloques] | exactitud mitad 1 / mitad 2 | MDE (pp) | veredicto |\n|---|---|---|---|---|---|---|---|---|"]
for i, r in enumerate(rows):
    npw = r["mde"] > 3.0; passes = adj[i] < 0.05 and r["acc"] >= 0.52 and (r["a1"] - 0.5) * (r["a2"] - 0.5) > 0
    out.append(f"| {r['nm']} | {r['n']} | {r['acc'] * 100:.1f} % | {r['p']:.3f} | {adj[i]:.2f} | {r['mean']:+.2f} [{r['lo']:+.2f}, {r['hi']:+.2f}] | {r['a1'] * 100:.0f} / {r['a2'] * 100:.0f} % | {r['mde']:.1f} | " + ("PASA" if passes else ("sin potencia" if npw else "no pasa")) + " |")
out.append(f"\n**Pasan: {sum(1 for i, r in enumerate(rows) if adj[i] < 0.05 and r['acc'] >= 0.52 and (r['a1'] - 0.5) * (r['a2'] - 0.5) > 0)} de {len(rows)}.** Con n ≈ 500 el MDE ronda 8–9 pp: «no pasa» aquí NO significa «no hay efecto».")
open(os.path.join(os.path.dirname(os.path.abspath(__file__)), f"resultados_EDGE_{A.tag}.md"), "w", encoding="utf-8").write("\n".join(out) + "\n"); print("\n".join(out))
