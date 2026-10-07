"""Tablas first-touch genericas por producto, hora de entrada y regla de direccion (misma construccion que g2_real_rules_scan.build_tables, que es MES/9:45/alternar).
Para cada dia: entrada en la primera barra con minuto-CT >= entry_m (cierre de esa barra), flatten en la primera barra >= flat_m; adv[d,k] / tp[d,t] = indice de barra del primer toque de
k ticks en contra / t ticks a favor (INF si nunca); flat[d] = P&L en ticks si se llega al flatten. SANDBOX / R&D: lee data_cache, sin red."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
from dd_wr.product_sweep import load_sessions
from strategies.geometry_pure import trading_day_index, decide_side

INF = 10 ** 6
# stem, tick, valor por tick ($), comision round-turn Topstep (help.topstep.com, PARTE A del log 24-sep)
SPEC = {"MES": ("mes_5min_2y", 0.25, 1.25, 1.22), "MNQ": ("mnq_5min_2y", 0.25, 0.50, 1.22), "M2K": ("m2k_5min_2y", 0.10, 0.50, 1.22),
        "MGC": ("mgc_5min_2y_corrected_window", 0.10, 1.00, 1.92), "MCL": ("mcl_5min_2y", 0.01, 1.00, 1.52), "M6E": ("m6e_5min_2y", 0.0001, 1.25, 1.00)}
_SESS = {}


def sessions(prod):
    if prod not in _SESS: _SESS[prod] = load_sessions(SPEC[prod][0])
    return _SESS[prod]


def build(prod, entry_m, flat_m=14 * 60 + 30, side_mode="alternate", kmax=1000, tmax=1000):
    stem, tick, tv, comm = SPEC[prod]
    S = sessions(prod)
    lastc = [s[3][-1] for s in S]
    adv, tpt, flat, dates, sides, amag = [], [], [], [], [], []
    for i, (day, h, l, c, m) in enumerate(S):
        a = np.nonzero(m >= entry_m)[0]
        if len(a) == 0: continue
        ep = int(a[0]); e = c[ep]
        if side_mode in ("alternate", "always_long", "always_short"):
            side = decide_side(trading_day_index(day), {"alternate": "alternate", "always_long": "always_long", "always_short": "always_short"}[side_mode])
        else:
            if i < 2: continue
            r = lastc[i - 1] - lastc[i - 2]
            side = (-1 if r > 0 else 1) if side_mode == "fade_prev" else (1 if r > 0 else -1)
        jf = next((j for j in range(ep + 1, len(c)) if m[j] >= flat_m), len(c) - 1)
        if jf <= ep: continue
        hh, ll, cc = h[ep + 1:jf + 1], l[ep + 1:jf + 1], c[ep + 1:jf + 1]
        fav = ((hh - e) if side == 1 else (e - ll)) / tick
        ad = ((e - ll) if side == 1 else (hh - e)) / tick
        M, F = np.maximum.accumulate(ad), np.maximum.accumulate(fav)
        ai = np.searchsorted(M, np.arange(1, kmax + 1), side="left"); hit = ai < len(M)
        mg = np.where(hit, M[np.minimum(ai, len(M) - 1)], 0.0)            # extremo adverso de la barra que toco el stop (llenado de peor caso), en ticks
        ai = np.where(hit, ai, INF)
        ti = np.searchsorted(F, np.arange(1, tmax + 1), side="left"); ti = np.where(ti >= len(F), INF, ti)
        adv.append(np.concatenate([[INF], ai])); tpt.append(np.concatenate([[INF], ti])); amag.append(np.concatenate([[0.0], mg]))
        flat.append((cc[-1] - e) * side / tick); dates.append(str(day)); sides.append(side)
    return dict(adv=np.array(adv, dtype=np.int32), tpt=np.array(tpt, dtype=np.int32), flat=np.array(flat, dtype=np.float64), amag=np.array(amag, dtype=np.float32), dates=dates,
                tick=tick, tv=tv, comm=comm, prod=prod, entry_m=entry_m)


def median_range_ticks(prod, entry_m, flat_m=14 * 60 + 30):
    stem, tick, tv, comm = SPEC[prod]; r = []
    for _, h, l, c, m in sessions(prod):
        k = (m >= entry_m) & (m <= flat_m)
        if k.sum() > 10: r.append((h[k].max() - l[k].min()) / tick)
    return float(np.median(r))


def build_synthetic(prod, entry_m, rng, flat_m=14 * 60 + 30, kmax=1000, tmax=1000):
    """Mundo de JUEGO JUSTO con la volatilidad real: para cada barra despues de la entrada se toman (high-prev_close, low-prev_close, close-prev_close) y se voltea el signo al azar
    (high/low se intercambian), encadenando desde la entrada. Elimina deriva, persistencia/momentum y asimetrias de direccion; conserva el tamano, la forma intradia y las colas de la
    volatilidad por barra. Devuelve tablas con side=+1 (la direccion ya es irrelevante)."""
    stem, tick, tv, comm = SPEC[prod]
    adv, tpt, flat, dates, amag = [], [], [], [], []
    for day, h, l, c, m in sessions(prod):
        a = np.nonzero(m >= entry_m)[0]
        if len(a) == 0: continue
        ep = int(a[0])
        jf = next((j for j in range(ep + 1, len(c)) if m[j] >= flat_m), len(c) - 1)
        if jf <= ep: continue
        prev = c[ep:jf]                                   # cierre previo de cada barra ep+1..jf
        up = h[ep + 1:jf + 1] - prev; dn = l[ep + 1:jf + 1] - prev; ch = c[ep + 1:jf + 1] - prev
        s = rng.random(len(prev)) < 0.5
        up2 = np.where(s, up, -dn); dn2 = np.where(s, dn, -up); ch2 = np.where(s, ch, -ch)
        path = np.concatenate([[0.0], np.cumsum(ch2)])[:-1]          # nivel al inicio de cada barra
        hh = path + up2; ll = path + dn2; cc = path + ch2
        fav = hh / tick; ad = -ll / tick                                 # largo (side=+1)
        M, F = np.maximum.accumulate(ad), np.maximum.accumulate(fav)
        ai = np.searchsorted(M, np.arange(1, kmax + 1), side="left"); hit = ai < len(M)
        mg = np.where(hit, M[np.minimum(ai, len(M) - 1)], 0.0); ai = np.where(hit, ai, INF)
        ti = np.searchsorted(F, np.arange(1, tmax + 1), side="left"); ti = np.where(ti >= len(F), INF, ti)
        adv.append(np.concatenate([[INF], ai])); tpt.append(np.concatenate([[INF], ti])); amag.append(np.concatenate([[0.0], mg])); flat.append(cc[-1] / tick); dates.append(str(day))
    return dict(adv=np.array(adv, dtype=np.int32), tpt=np.array(tpt, dtype=np.int32), flat=np.array(flat, dtype=np.float64), amag=np.array(amag, dtype=np.float32), dates=dates, tick=tick, tv=tv, comm=comm, prod=prod, entry_m=entry_m)
