"""E4 — calendario (PREREGISTRO_E Enmienda 2): (i) pre-FOMC LARGO el dia del anuncio (46 reuniones 2021-2026), (ii) cambio de mes LARGO (ultimos 2 y primeros 3 dias habiles).
Primaria: ^GSPC apertura->cierre; confirmacion: MES 9:30->14:30 CT. -> RESULTADOS_E4.md, e4_pvals.json
    python run_e4.py"""
import datetime as dt, json, math, os, sys
import numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from common_e import SEED, block_bootstrap_acc, blocks10, day_results, load_daily, pval_gt
from daydata import load_days
from rule_eval import HEAD, evaluate, row
from strategies.geometry_pure import decide_side, trading_day_index
out = []; P = lambda s="": (print(s, flush=True), out.append(s))
fomc = [dt.date.fromisoformat(l.strip()) for l in open(os.path.join(HERE, "fomc_dates.txt")) if l[0] != "#" and l.strip()]
gs = load_daily("^GSPC"); oc = np.sign(np.log(gs["Close"] / gs["Open"])).values; idx = gs.index; dates = np.array([d.date() for d in idx])
last_month = (idx[-1].year, idx[-1].month)
def tom_flags(dates_):
    s = pd.Series(range(len(dates_)), index=pd.to_datetime(dates_)); f = np.zeros(len(dates_), bool)
    for (y, m), g in s.groupby([s.index.year, s.index.month]):
        pos = list(g.values)
        f[pos[:3]] = True
        if (y, m) != last_month: f[pos[-2:]] = True
    return f
def diff_boot(up, flag, block=5, B=10000, seed=SEED):
    n = len(up); rng = np.random.default_rng(seed); nb = math.ceil(n / block)
    st = rng.integers(0, n - block + 1, size=(B, nb)); ix = (st[:, :, None] + np.arange(block)[None, None, :]).reshape(B, -1)[:, :n]
    u = up[ix]; f = flag[ix]
    a = (u * f).sum(1) / np.maximum(f.sum(1), 1); b = (u * ~f).sum(1) / np.maximum((~f).sum(1), 1)
    d = a - b; return float(up[flag].mean() - up[~flag].mean()), (float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5))), float((d <= 0).mean())
P("# RESULTADOS_E4 — calendario (pre-registrada; Enmienda 2)\n")
P("Regla LARGA ⇒ “siempre LARGO” coincide con ella en los mismos días: **G2(2) frente a LARGO no se puede superar por construcción**; la pregunta pertinente es si esos días suben más que el resto (diferencia de exactitud con IC por bloques de 5 días).\n")
pv = {}; g2 = {}; ok = oc != 0
for name, flag_full in (("cambio de mes (últimos 2 + primeros 3 días hábiles)", tom_flags(dates)), ("pre-FOMC (día del anuncio, 2021-2026)", np.isin(dates, fomc))):
    key = "E4 " + ("TOM" if "mes" in name else "FOMC")
    if key == "E4 FOMC": sel = ok & (idx >= pd.Timestamp("2021-01-01"))
    else: sel = ok.copy()
    up = (oc[sel] == 1).astype(float); fl = flag_full[sel]; ix_ = idx[sel]
    hit = up[fl]; m, ci, boots = block_bootstrap_acc(hit, seed=SEED); pv[key] = pval_gt(boots, 0.51)
    dd_, dci, dp = diff_boot(up, fl)
    alt = np.array([decide_side(trading_day_index(d.date()), "alternate") for d in ix_[fl]]); ah = (alt == oc[sel][fl]).astype(float)
    P(f"\n## ^GSPC apertura→cierre — {name}\n")
    P(f"- Días con la regla: {int(fl.sum())}; exactitud (sube) **{m * 100:.2f} %** [IC95 {ci[0] * 100:.1f}, {ci[1] * 100:.1f}]; p vs 51 % (sin ajustar) = {pv[key]:.3f}; `alternate` en los mismos días {ah.mean() * 100:.1f} %.")
    P(f"- Resto de días: {up[~fl].mean() * 100:.2f} % (n={int((~fl).sum())}); **diferencia = {dd_ * 100:+.2f} pp** [IC95 {dci[0] * 100:+.1f}, {dci[1] * 100:+.1f}], p unilateral = {dp:.3f}.")
    wa = wb = 0; rows = []
    xs = np.where(fl)[0]
    for a, b in blocks10(len(xs)):
        bh = hit[a:b].mean(); wa += bh > ah[a:b].mean(); rows.append(f"{bh * 100:.0f}")
    base = up[~fl]; P(f"- 10 bloques cronológicos (exactitud de la regla): {' · '.join(rows)}; bloques > `alternate`: {wa}/10.")
    ys = pd.Series(hit, index=ix_[fl]); by = ys.groupby(ys.index.year).agg(["mean", "size"])
    P("- Por año (últimos 5): " + " · ".join(f"{y}: {r['mean'] * 100:.0f} % (n={int(r['size'])})" for y, r in by.tail(5).iterrows()))
    g2[key] = dict(acc=float(m), p51=float(pv[key]), wins_alt=int(wa), wins_long=0, diff_pp=float(dd_ * 100), diff_ci=[float(dci[0] * 100), float(dci[1] * 100)], last3={str(y): float(r_["mean"]) for y, r_ in by.tail(3).iterrows()})
    bear = [y for y in (2008, 2020, 2022) if y in by.index]
    P("- Tramos bajistas: " + " · ".join(f"{y}: {by.loc[y, 'mean'] * 100:.0f} % (n={int(by.loc[y, 'size'])})" for y in bear))
# ── confirmación en MES (5 min) ──
dd = load_days(); res = {sp: day_results(dd, 40, 2000.0, 100, 32, 1.22, 1.25, sp) for sp in (0.0, 1.0, 3.0)}
P("\n## Confirmación en MES (9:30→14:30 CT, nc 40 TP 32 / piso $2,000; sin potencia)\n"); P(HEAD)
dsd = np.array(dd.dates); tf = pd.Series(tom_flags(dates), index=dates)
side_tom = np.array([1.0 if tf.get(d, False) else 0.0 for d in dsd]); side_fomc = np.isin(dsd, fomc).astype(float)
for lab, sd in (("cambio de mes", side_tom), ("pre-FOMC", side_fomc)):
    r = evaluate(sd, dd, res); P(row(lab, r))
fo = [(d, "↑" if dd.cl[i, -1] > 0 else "↓") for i, d in enumerate(dd.dates) if d in set(fomc)]
P("\nDías FOMC en la ventana real (signo de referencia→flatten): " + " ".join(f"{d.isoformat()}{s}" for d, s in fo) + f"  → suben {sum(1 for _, s in fo if s == '↑')} de {len(fo)}.")
json.dump(pv, open(os.path.join(HERE, "e4_pvals.json"), "w")); json.dump(g2, open(os.path.join(HERE, "e4_g2.json"), "w"))
open(os.path.join(HERE, "RESULTADOS_E4.md"), "w").write("\n".join(out))
