"""
Prioridad 2: barrido producto x ancho de SL x RR con el motor EMPIRICO (bar-walk real de sesion por
producto + cadena Combine->XFA con bootstrap del PnL real). NUNCA el motor binario.

Convenciones (declaradas):
- Entrada: primera barra >= open+13min (misma regla que MGC: ENTRY_WAIT_MINUTES=13), con open = 1a barra
  disponible del dataset del producto (8:30 CT para todos salvo MGC=7:00 CT), MGC exacto como produccion.
- Flatten: 30 min antes del fin de la ventana de datos (regla de geometry_mgc_scheduler: 14:30 para
  ventana hasta 15:00 CT). ZC: ventana termina 13:15 -> 12:45.
- SL$ objetivo ~= $2,184 (MLL 4500 / k=2, como MGC); nc = clip(round(2184 / SL$ por contrato), 1, nc_cap).
- TP neto por dia ganador debe ser >= $150 (regla XFA) o la config se descarta.
- Ambiguedad de barra (TP y SL tocados): SL primero (conservador).
- Motor XFA: nc fijo (equivalente a dyn-nc para MGC, verificado: $16,043 vs $16,048), sin fix balance>0
  (mismo semantica que Prioridad 1); Combine con bootstrap empirico, 150K.
"""
from __future__ import annotations
import os, sys, itertools, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np, pandas as pd
from strategies.geometry_pure import trading_day_index, decide_side
from dd_wr.rr_experiment import combine_pool, Emp, xfa_pool_fixed_nc, summarize

D = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data_cache")
SL_USD_TARGET = 2184.0
RRS = [1.0, 0.67, 0.43, 0.33, 0.25, 0.18]
CS = [0.5, 0.75, 1.0, 1.5]
# label: (parquet, tick_size, tick_value, commission_rt, nc_cap, entry_open_min, flatten_min, extra_entry_opens)
PRODUCTS = {
    "MGC": ("mgc_5min_2y_corrected_window", 0.10, 1.00, 1.92, 30, 7 * 60, 14 * 60 + 30, []),
    "M2K": ("m2k_5min_2y", 0.10, 0.50, 1.22, 50, 8 * 60 + 30, 14 * 60 + 30, []),
    "MCL": ("mcl_5min_2y", 0.01, 1.00, 1.52, 30, 8 * 60 + 30, 14 * 60 + 30, []),
    "M6E": ("m6e_5min_2y", 0.0001, 1.25, 1.00, 50, 8 * 60 + 30, 14 * 60 + 30, [9 * 60]),
    "ZN":  ("zn_5min_2y", 0.015625, 15.625, 2.62, 5, 8 * 60 + 30, 14 * 60 + 30, [9 * 60]),
    "ZC":  ("zc_5min_2y", 0.25, 12.50, 5.28, 5, 8 * 60 + 30, 12 * 60 + 45, []),
}


def load_sessions(stem):
    d = pd.read_parquet(os.path.join(D, f"{stem}.parquet"))
    i = d.index.tz_convert("America/Chicago")
    d = d.assign(day=i.date, m=i.hour * 60 + i.minute)
    return [(day, g["high"].values, g["low"].values, g["close"].values, g["m"].values) for day, g in d.groupby("day", sort=True)]


def median_range_ticks(sessions, tick, entry_m, flat_m):
    r = []
    for _, h, l, c, m in sessions:
        k = (m >= entry_m) & (m <= flat_m)
        if k.sum() > 10: r.append((h[k].max() - l[k].min()) / tick)
    return float(np.median(r))


def walk_all(sessions, tick, tv, comm, nc, sl_t, tp_t, entry_m, flat_m):
    pp = tv / tick
    out = []
    for day, h, l, c, m in sessions:
        a = np.nonzero(m >= entry_m)[0]
        if len(a) == 0: continue
        ep = int(a[0]); side = decide_side(trading_day_index(day), "alternate")
        e = c[ep]; tp = e + side * tp_t * tick; sl = e - side * sl_t * tick
        res = None
        for j in range(ep + 1, len(c)):
            w, lo = (h[j] >= tp, l[j] <= sl) if side == 1 else (l[j] <= tp, h[j] >= sl)
            if w or lo:
                res = ("TP", (tp - e) * side * pp * nc - comm * nc) if (w and not lo) else ("SL", (sl - e) * side * pp * nc - comm * nc)
                break
            if m[j] >= flat_m:
                res = ("FLATTEN", (c[j] - e) * side * pp * nc - comm * nc); break
        if res is None: res = ("FLATTEN", (c[-1] - e) * side * pp * nc - comm * nc)
        out.append((str(day), side, res[0], res[1]))
    return pd.DataFrame(out, columns=["date", "side", "result", "pnl"])


def configs(label, tick, tv, comm, cap, R):
    seen = set()
    widths = [max(2, int(round(c * R))) for c in CS]
    if label == "MGC": widths.append(364)
    for sl in sorted(set(widths)):
        nc = int(np.clip(round(SL_USD_TARGET / (sl * tv)), 1, cap))
        for rr in RRS:
            tp = max(1, int(round(sl * rr)))
            if (sl, tp) in seen: continue
            seen.add((sl, tp))
            yield sl, tp, nc, rr


if __name__ == "__main__":
    rows = []; t0 = time.time()
    for label, (stem, tick, tv, comm, cap, open_m, flat_m, extra) in PRODUCTS.items():
        sessions = load_sessions(stem)
        for eo in [open_m] + extra:
            entry_m = eo + 13
            R = median_range_ticks(sessions, tick, entry_m, flat_m)
            for sl, tp, nc, rr in configs(label, tick, tv, comm, cap, R):
                tp_net = tp * tv * nc - comm * nc
                sl_usd = sl * tv * nc + comm * nc
                if tp_net < 150: 
                    rows.append({"product": label, "entry_open": eo, "sl": sl, "tp": tp, "rr": rr, "nc": nc, "R": R, "skipped": "TP$<150"}); continue
                t = walk_all(sessions, tick, tv, comm, nc, sl, tp, entry_m, flat_m)
                n = len(t); ntp = (t.result == "TP").sum(); nsl = (t.result == "SL").sum(); nfl = (t.result == "FLATTEN").sum()
                if ntp + nsl < 10: continue
                pnl = t.pnl.values
                cp = combine_pool(Emp(pnl)); xp = xfa_pool_fixed_nc(pnl, False)
                s = summarize(cp, xp)
                h = n // 2
                wr = lambda x: (x.result == "TP").sum() / max(1, (x.result == "TP").sum() + (x.result == "SL").sum())
                rows.append({"product": label, "entry_open": eo, "sl": sl, "tp": tp, "rr": rr, "nc": nc, "R": R, "sl_over_R": sl / R,
                             "sl_usd": sl_usd, "tp_net_usd": tp_net, "n": n, "tp_n": ntp, "sl_n": nsl, "flat_n": nfl,
                             "wr_cond": ntp / (ntp + nsl), "flat_share": nfl / n, "ev_trade": pnl.mean(),
                             "wr_h1": wr(t.iloc[:h]), "wr_h2": wr(t.iloc[h:]), **s})
                r = rows[-1]
                print(f"{label} eo={eo//60}:{eo%60:02d} SL={sl} TP={tp} rr={rr} nc={nc} WRc={r['wr_cond']:.3f} flat={r['flat_share']:.2f} p50=${r['p50']:,.0f} ({time.time()-t0:.0f}s)", flush=True)
        pd.DataFrame(rows).to_csv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "product_sweep_results.csv"), index=False)
