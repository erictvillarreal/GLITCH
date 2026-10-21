"""Evaluacion comun de una regla direccional en la ventana real de 5 min (E2, E4, E5): exactitud del signo, controles, bloques, mecanica exacta."""
import math
import numpy as np
from common_e import SEED, block_bootstrap_acc, blocks10, eval_sides, pval_gt
from strategies.geometry_pure import decide_side, trading_day_index


def _ratio_boot(num, den, block=5, B=10000, seed=SEED):
    n = len(num)
    if n < 2 * block: return (np.nan, np.nan, np.array([np.nan]))
    rng = np.random.default_rng(seed); nb = int(math.ceil(n / block))
    starts = rng.integers(0, n - block + 1, size=(B, nb))
    idx = (starts[:, :, None] + np.arange(block)[None, None, :]).reshape(B, -1)[:, :n]
    r = num[idx].sum(1) / np.maximum(den[idx].sum(1), 1)
    return float(num.sum() / max(den.sum(), 1)), (float(np.percentile(r, 2.5)), float(np.percentile(r, 97.5))), r


def evaluate(side, dd, res_by_slip, bear=None, seed=SEED):
    """side: (D,) con +1/-1/0 (0 = no opera). dd: DayData; res_by_slip: {slip: day_results}. Resultado de signo = signo de (cierre del flatten - referencia)."""
    side = np.nan_to_num(np.asarray(side, float))
    out = np.sign(dd.cl[:, -1]); dates = dd.dates
    m = (side != 0) & (out != 0)
    ds = [d for d, k in zip(dates, m) if k]; s = side[m]; o = out[m]
    alt = np.array([decide_side(trading_day_index(d), "alternate") for d in ds])
    hit = (s == o).astype(float); ah = (alt == o).astype(float); lh = (o == 1).astype(float); sh = (o == -1).astype(float)
    acc, ci, boots = block_bootstrap_acc(hit, seed=seed)
    r = dict(n=int(m.sum()), n_sig=int((side != 0).sum()), acc=acc, ci=ci, p51=pval_gt(boots, 0.51), alt=ah.mean() if len(ah) else np.nan, long=lh.mean() if len(lh) else np.nan, short=sh.mean() if len(sh) else np.nan)
    rng = np.random.default_rng(seed); rd = []
    for _ in range(1000): rd.append((np.where(rng.random(len(o)) < 0.5, 1, -1) == o).mean())
    r["rand"] = (float(np.percentile(rd, 50)), float(np.percentile(rd, 2.5)), float(np.percentile(rd, 97.5)))
    wa = wl = 0
    for a, b in blocks10(len(o)):
        if b > a:
            wa += hit[a:b].mean() > ah[a:b].mean(); wl += hit[a:b].mean() > lh[a:b].mean()
    r["wins_alt"], r["wins_long"] = int(wa), int(wl)
    yrs = {}
    for y in sorted(set(d.year for d in ds)):
        k = np.array([d.year == y for d in ds]); yrs[y] = (hit[k].mean(), int(k.sum()), ah[k].mean(), lh[k].mean())
    r["years"] = yrs
    r["mech"] = {}
    for slip, res in res_by_slip.items():
        ev = eval_sides(res, np.where(m, side, 0))
        alt_full = np.array([decide_side(trading_day_index(d), "alternate") for d in dates])
        ca = eval_sides(res, np.where(m, alt_full, 0)); cl = eval_sides(res, np.where(m, 1, 0)); cs = eval_sides(res, np.where(m, -1, 0))
        k_ = np.where(np.where(m, side, 0)[m] == 1, res[1][0][m], res[-1][0][m])
        tp = (k_ == 0).astype(float); dec = (k_ <= 2).astype(float)
        _, wci, wb = _ratio_boot(tp, dec, seed=seed)
        rw = []
        for _ in range(1000):
            sd = np.where(rng.random(len(dates)) < 0.5, 1, -1); rw.append(eval_sides(res, np.where(m, sd, 0))["wr"])
        r["mech"][slip] = dict(ev=ev, alt=ca, long=cl, short=cs, wr_ci=wci, wr_p51=pval_gt(wb, 0.51), rand=(float(np.nanpercentile(rw, 50)), float(np.nanpercentile(rw, 2.5)), float(np.nanpercentile(rw, 97.5))))
    return r


def row(label, r, slip=0.0):
    mc = r["mech"][slip]; ev = mc["ev"]
    return (f"| {label} | {r['n_sig']} / {r['n']} | {r['acc'] * 100:.1f} % [{r['ci'][0] * 100:.1f}, {r['ci'][1] * 100:.1f}] | {r['alt'] * 100:.1f} % | {r['long'] * 100:.1f} % | {r['short'] * 100:.1f} % | {r['rand'][0] * 100:.1f} % ({r['rand'][1] * 100:.1f}–{r['rand'][2] * 100:.1f}) | {r['p51']:.3f} | {r['wins_alt']}/10 | {r['wins_long']}/10 |"
            f" {ev['tp'] * 100:.0f}/{ev['sl'] * 100:.0f}/{ev['fl'] * 100:.0f} % | {ev['wr'] * 100:.1f} % [{mc['wr_ci'][0] * 100:.1f}, {mc['wr_ci'][1] * 100:.1f}] ({ev['dec']} dec.) | {mc['alt']['wr'] * 100:.1f} % | {mc['long']['wr'] * 100:.1f} % | {mc['short']['wr'] * 100:.1f} % | {mc['rand'][0] * 100:.1f} % | ${ev['pnl']:+.1f} |")


HEAD = ("| regla | señales / días con resultado | exactitud signo [IC95] | `alternate` | siempre LARGO | siempre CORTO | aleatorio (p2.5–p97.5) | p vs 51 % (sin ajustar) | bloques > alt. | bloques > LARGO |"
        " TP/SL/FL | WR entre decididos [IC95] | WR alt. | WR LARGO | WR CORTO | WR aleat. | pnl/día |\n|" + "---|" * 17)
