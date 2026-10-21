"""Parte B: reglas de direccion R1-R3 vs controles, con los criterios FIJADOS en PREREGISTRO.md (enmiendas 1-3).

    python run_partB.py            # completo
Escribe resultados_B.md. Semillas fijas. NO ajusta parametros (sin barrido).
"""
from __future__ import annotations

import datetime as dt
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(__file__)
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "..", "preservacion"))
from daydata import TICK_USD, load_days, sim_day  # noqa: E402
from series import WARMUP, add_indicators, daily_series, dominant_window, eval_index  # noqa: E402
from sim import FLOOR_CAP, MLL, TARGET, OutcomeTable, pol_fixed, pol_p3, Ctx  # noqa: E402

NC, CUSH = 40, 2000.0
SLIPS = [1, 3]
EXIT_SLIP = 3.0
NBLK = 10
SEED = 20261020
EPOCH = dt.date(2020, 1, 1)
DOM = (dt.date(2025, 4, 9), dt.date(2025, 7, 8))       # Enmienda 2
START = dict(bal=51401.2, peak=51401.2)


def tdi(d):
    return int(np.busday_count(EPOCH, d))


def md_table(rows, header):
    out = ["| " + " | ".join(header) + " |", "|" + "|".join(["---"] * len(header)) + "|"]
    return "\n".join(out + ["| " + " | ".join(str(c) for c in r) + " |" for r in rows])


def per_day_outcomes(dd):
    """Para cada dia de dd y cada lado: P(TP-primero), P(LIQ), ticks netos medios (promedio sobre slip {1,3})."""
    res = {}
    for side in (1, -1):
        tp = np.zeros(dd.D); lq = np.zeros(dd.D); tk = np.zeros(dd.D)
        for s in SLIPS:
            k, p = sim_day(dd, side, NC, CUSH, slip=s, exit_slip=EXIT_SLIP)
            tp += (k == 0) / len(SLIPS); lq += (k == 2) / len(SLIPS); tk += p / (NC * TICK_USD) / len(SLIPS)
        res[side] = dict(tp=tp, liq=lq, ticks=tk)
    return res


def rule_sides(df, dd, ev_pos):
    """Lado (+1/-1) o 0 (no operar) por dia de evaluacion y regla. Usa SOLO la fila del dia habil previo (df posicion-1)."""
    dpos = {d: i for i, d in enumerate(df.index)}
    out = {k: [] for k in ("R1", "R2", "R3", "alternate", "always_long", "always_short")}
    for i in ev_pos:
        prev = df.iloc[i - 1]
        c, s20, s50, atr = prev.adj_close, prev.sma20, prev.sma50, prev.atr14
        out["R1"].append(1 if c > s20 else -1)
        down = (c < s20) and (s20 < s50)
        out["R2"].append(-1 if down else 1)
        out["R3"].append(0 if abs(c - s20) < 0.5 * atr else (-1 if down else 1))
        out["alternate"].append(1 if tdi(df.index[i]) % 2 == 0 else -1)
        out["always_long"].append(1); out["always_short"].append(-1)
    return {k: np.array(v) for k, v in out.items()}


def blocks(n, nb=NBLK):
    size = n // nb
    edges = [i * size for i in range(nb)] + [n]
    return [(edges[i], edges[i + 1]) for i in range(nb)]


def metric(sides, po, mask=None):
    """Por dia: P(TP-primero), liq, ticks del lado elegido (0 operan -> nan)."""
    tp = np.where(sides == 1, po[1]["tp"], po[-1]["tp"]).astype(float)
    lq = np.where(sides == 1, po[1]["liq"], po[-1]["liq"]).astype(float)
    tk = np.where(sides == 1, po[1]["ticks"], po[-1]["ticks"]).astype(float)
    for a in (tp, lq, tk): a[sides == 0] = np.nan
    return tp, lq, tk


def paired_boot_ci(diff, mask, block=5, B=10000, seed=SEED, level=0.983):
    """IC percentil de la media de diff[mask] con bootstrap por bloques de 5 dias CONSECUTIVOS, pareado (la misma remuestra de fechas)."""
    rng = np.random.default_rng(seed)
    n = len(diff); nb = int(np.ceil(n / block))
    d = np.where(mask, diff, np.nan)
    means = np.empty(B)
    starts = rng.integers(0, n - block + 1, size=(B, nb))
    for b in range(B):
        idx = (starts[b][:, None] + np.arange(block)[None, :]).ravel()[:n]
        x = d[idx]; x = x[~np.isnan(x)]
        means[b] = x.mean() if len(x) else np.nan
    lo = (1 - level) / 2
    return np.nanpercentile(means, [100 * lo, 100 * (1 - lo)]), np.nanmean(d)


def hist_attempts(side_arr, nc_policy, dd, ev_dd_idx, tabs, seed=SEED, maxdays=60, starts=None):
    """M2h: un intento por cada fecha de inicio de la muestra de evaluacion, con el lado/dia dado y resultados reales de cada dia."""
    rng = np.random.default_rng(seed)
    n_ev = len(ev_dd_idx)
    st = np.arange(0, n_ev) if starts is None else starts
    n = len(st)
    bal = np.full(n, START["bal"]); peak = np.full(n, START["peak"]); best = np.zeros(n)
    alive = np.ones(n, bool); passed = np.zeros(n, bool); liq = np.zeros(n, bool); valid = np.ones(n, bool)
    for t in range(maxdays):
        pos = st + t
        has = pos < n_ev
        a = alive & has
        if not a.any(): break
        p_ = np.where(has, pos, 0)
        side = side_arr[p_]
        floor = np.minimum(peak - MLL, FLOOR_CAP); cush = bal - floor
        ctx = Ctx(TARGET - bal, bal, peak, floor, cush, 0, t)
        nc = np.where(a, nc_policy(ctx), 0)
        nc = np.where(side == 0, 0, nc)
        kind = np.full(n, 3, dtype=np.int8); pnl = np.zeros(n)
        didx = ev_dd_idx[p_]
        sl_choice = rng.integers(0, len(SLIPS), size=n)
        for si, s in enumerate(SLIPS):
            for sd in (1, -1):
                for ncv in np.unique(nc[a & (sl_choice == si) & (side == sd)]):
                    if ncv == 0: continue
                    m = a & (sl_choice == si) & (side == sd) & (nc == ncv)
                    kt, pt = tabs[s].get(sd, int(ncv))
                    b = tabs[s].bin_of(cush[m])
                    kind[m] = kt[b, didx[m]]; pnl[m] = pt[b, didx[m]]
        was_liq = a & (kind == 2)
        liq |= was_liq
        ok = a & ~was_liq
        bal = np.where(ok, bal + pnl, bal); bal = np.where(was_liq, floor, bal)
        best = np.where(ok, np.maximum(best, pnl), best)
        peak = np.where(ok, np.maximum(peak, bal), peak)
        newly = ok & (bal >= TARGET) & (best < 1650.0)
        passed |= newly
        alive = alive & ~was_liq & ~newly
    complete = (st + maxdays <= n_ev) | passed | liq       # intentos con ventana completa o ya resueltos
    return passed, liq, complete


def main():
    t0 = time.time(); out = []
    log = lambda s: (out.append(s), print(s, flush=True))
    dd = load_days(); df = add_indicators(daily_series())
    ev_pos = eval_index(df, dd)
    dd_pos = {d: i for i, d in enumerate(dd.dates)}
    ev_dates = [df.index[i] for i in ev_pos]
    ev_dd_idx = np.array([dd_pos[d] for d in ev_dates])
    n = len(ev_pos)
    log(f"# resultados_B (generado por run_partB.py; semilla {SEED})\n")
    log(f"Muestra de evaluacion: {n} dias ({ev_dates[0]} -> {ev_dates[-1]}), calentamiento {WARMUP} dias. Medida base: nc={NC}, colchon ${CUSH:,.0f}, TP32/SL100, slip entrada {{1,3}} promediado, salida SL supuesta {EXIT_SLIP:.0f}.")
    in_dom = np.array([DOM[0] <= d <= DOM[1] for d in ev_dates])
    log(f"Ventana dominante (Enmienda 2): {DOM[0]} -> {DOM[1]} ({in_dom.sum()} dias de evaluacion).\n")
    po_all = per_day_outcomes(dd)
    po = {sd: {k: v[ev_dd_idx] for k, v in po_all[sd].items()} for sd in (1, -1)}
    S = rule_sides(df, dd, ev_pos)
    S["oracle"] = np.where(po[1]["tp"] >= po[-1]["tp"], 1, -1)
    rng = np.random.default_rng(SEED)

    # ── D1: asimetria LONG vs SHORT por bloque ─────────────────────────────────────────────────────────────
    bl = blocks(n)
    for label, mask in (("TODA la muestra", np.ones(n, bool)), ("SIN la ventana dominante", ~in_dom)):
        rows = []
        for bi, (a, b) in enumerate(bl):
            m = mask[a:b]
            if m.sum() == 0: rows.append([bi + 1, f"{ev_dates[a]}..{ev_dates[b - 1]}", 0, "-", "-", "-"]); continue
            lt = po[1]["tp"][a:b][m].mean(); st = po[-1]["tp"][a:b][m].mean()
            rows.append([bi + 1, f"{ev_dates[a]}..{ev_dates[b - 1]}", int(m.sum()), f"{lt * 100:.1f}%", f"{st * 100:.1f}%", f"{(lt - st) * 100:+.1f} pp"])
        lt = po[1]["tp"][mask].mean(); st = po[-1]["tp"][mask].mean()
        rows.append(["**total**", "", int(mask.sum()), f"{lt * 100:.1f}%", f"{st * 100:.1f}%", f"{(lt - st) * 100:+.1f} pp"])
        log(f"## D1 - P(TP-primero) LONG vs SHORT por bloque ({label})\n")
        log(md_table(rows, ["bloque", "fechas", "dias", "LONG", "SHORT", "LONG - SHORT"]))
        diff = po[1]["tp"] - po[-1]["tp"]
        ci, mean = paired_boot_ci(diff, mask)
        log(f"\nDiferencia media LONG-SHORT = {mean * 100:+.2f} pp; IC 98.3% (bootstrap de bloques de 5 dias) = [{ci[0] * 100:+.2f}, {ci[1] * 100:+.2f}] pp.\n")
    log("Las 8 sesiones en vivo (anecdota): NO DISPONIBLE localmente (viven en el Gist `geometry_mestest_log.json`, requiere token; ver Enmienda 1 §8).\n")

    # ── D2: reglas vs controles ─────────────────────────────────────────────────────────────────────────────
    tp_alt, lq_alt, tk_alt = metric(S["alternate"], po); tp_lng, _, _ = metric(S["always_long"], po)
    rows = []; verdict = {}
    for r in ("R1", "R2", "R3"):
        tp_r, lq_r, tk_r = metric(S[r], po)
        traded = S[r] != 0
        d_alt = tp_r - tp_alt; d_lng = tp_r - tp_lng
        win_a = loss_c = 0
        for (a, b) in bl:
            m = traded[a:b]
            if m.sum() == 0: continue
            if np.nanmean(tp_r[a:b][m]) > np.nanmean(tp_alt[a:b][m]) + 1e-12: win_a += 1
            if np.nanmean(tp_r[a:b][m]) < np.nanmean(tp_lng[a:b][m]) - 1e-12: loss_c += 1
        ci, mean = paired_boot_ci(d_alt, traded)
        ci_x, mean_x = paired_boot_ci(d_alt, traded & ~in_dom)
        a_ok, b_ok, c_ok, d_ok = win_a >= 7, ci[0] > 0, loss_c <= 3, mean_x >= 0
        verdict[r] = a_ok and b_ok and c_ok and d_ok
        rows.append([r, int(traded.sum()), f"{np.nanmean(tp_r) * 100:.1f}%", f"{np.nanmean(tp_alt[traded]) * 100:.1f}%", f"{np.nanmean(tp_lng[traded]) * 100:.1f}%",
                     f"{win_a}/10 ({'OK' if a_ok else 'NO'})", f"{mean * 100:+.2f} [{ci[0] * 100:+.2f},{ci[1] * 100:+.2f}] ({'OK' if b_ok else 'NO'})",
                     f"{loss_c}/10 ({'OK' if c_ok else 'NO'})", f"{mean_x * 100:+.2f} ({'OK' if d_ok else 'NO'})", "**PASA D2**" if verdict[r] else "no pasa"])
    log("## D2 - reglas candidatas (P(TP-primero) sobre los dias que la regla opera)\n")
    log(md_table(rows, ["regla", "dias operados", "P(TP) regla", "P(TP) alternate", "P(TP) siempre LONG", "(a) gana a alternate en bloques", "(b) dif. media pp [IC98.3%]",
                        "(c) pierde vs siempre LONG", "(d) dif. sin ventana dominante (pp)", "veredicto"]))
    log("\nCriterios (PREREGISTRO.md): (a) >=7/10, (b) limite inferior del IC98.3% > 0, (c) <=3/10, (d) dif. sin ventana dominante >= 0. Pasa D2 solo si cumple las cuatro.\n")

    # ── controles y tabla completa ──────────────────────────────────────────────────────────────────────────
    rows = []
    rnd_tp = []
    for k in range(1000):
        sd = np.where(np.random.default_rng(k).random(n) < 0.5, 1, -1)
        rnd_tp.append(np.nanmean(metric(sd, po)[0]))
    for name in ("R1", "R2", "R3", "alternate", "always_long", "always_short", "oracle"):
        tp_, lq_, tk_ = metric(S[name], po)
        rows.append([name, int((S[name] != 0).sum()), f"{np.nanmean(tp_) * 100:.1f}%", f"{np.nanmean(lq_) * 100:.1f}%", f"{np.nanmean(tk_):+.2f}",
                     f"{np.nanmean(tp_[~in_dom]) * 100:.1f}%" if np.isfinite(np.nanmean(tp_[~in_dom])) else "-"])
    rows.append(["aleatorio (1000 corridas)", n, f"{np.mean(rnd_tp) * 100:.1f}% (p2.5-p97.5: {np.percentile(rnd_tp, 2.5) * 100:.1f}-{np.percentile(rnd_tp, 97.5) * 100:.1f})", "-", "-", "-"])
    log("## Controles y reglas: medida base (toda la muestra; dias operados de cada regla)\n")
    log(md_table(rows, ["regla/control", "dias operados", "P(TP-primero)", "P(liq 1 dia)", "ticks netos medios/dia", "P(TP) sin ventana dominante"]))

    # ── puente a P(pase) (M2h) ──────────────────────────────────────────────────────────────────────────────
    tabs = {s: OutcomeTable(dd, s, EXIT_SLIP, step=10.0) for s in SLIPS}
    log("\n## Puente a P(pase del Combine): repeticion historica M2h (un intento por fecha de inicio; solo intentos con ventana completa o ya resueltos)\n")
    rows = []
    sel = {k: S[k] for k in ("R1", "R2", "R3", "alternate", "always_long", "always_short", "oracle")}
    for pname, pol in (("P0 40 fijo", pol_fixed(40)), ("P3 finish-line", pol_p3())):
        for name, sd in sel.items():
            passed, liq_, comp = hist_attempts(sd, pol, dd, ev_dd_idx, tabs)
            p = passed[comp].mean(); k = int(passed[comp].sum()); m = int(comp.sum())
            # IC bootstrap de bloques de 20 fechas de inicio
            rng2 = np.random.default_rng(SEED); idx = np.where(comp)[0]
            bs = []
            for _ in range(2000):
                ss = rng2.integers(0, len(idx) - 20, size=int(np.ceil(len(idx) / 20)))
                sample = np.concatenate([idx[s_:s_ + 20] for s_ in ss])[:len(idx)]
                bs.append(passed[sample].mean())
            lo, hi = np.percentile(bs, [2.5, 97.5])
            rows.append([pname, name, m, f"{p * 100:.1f}% [{lo * 100:.1f},{hi * 100:.1f}]", f"{liq_[comp].mean() * 100:.1f}%"])
    log(md_table(rows, ["politica de tamano", "regla de lado", "intentos", "P(pase) [IC95% bloques]", "P(liquidacion)"]))
    log("\n(Los intentos de fechas de inicio vecinas comparten dias: las observaciones NO son independientes; el IC por bloques lo refleja solo en parte.)")
    open(os.path.join(HERE, "resultados_B.md"), "w").write("\n".join(out)); print(f"\nlisto en {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
