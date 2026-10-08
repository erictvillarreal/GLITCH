"""Stacking — (1) cuanto informan los primeros N intentos; (2) sensibilidad del neto por cuenta a la friccion medible (slippage de entrada y de stop, llenado del TP, comision, dias perdidos por fallos de API, costo por intento)
y valor de esperar a validar. Configuracion 'paso 2' (TP32 + XFA 728x3), liquidacion explicita. SANDBOX / R&D. Uso: python -m scripts.stacking_info_friction"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np, dataclasses as dc
from math import comb
from dd_cash import lever_data as LD
from dd_cash.lever_engine import simulate, INF
from scripts.stacking_timing import acct, OPS_CUM
from scripts.lever_common import OPS12

lines = []; P = lambda s: (print(s), lines.append(s))
T = 20000; H = LD.H


def binom_cdf(k, n, p): return sum(comb(n, i) * p ** i * (1 - p) ** (n - i) for i in range(k + 1))


def worlds():
    geo = LD.structural_geometry("MES", 585, "MGC", 433)
    S_f, ax_f = LD.make_pool_spec(n_worlds=60, **{k: geo[k] for k in ("nc", "tp", "x_sl", "x_tp", "nc_x")}, slip=0.5)
    S_r, ax_r = LD.make_spec(nc=geo["nc"], tp=geo["tp"], x_sl=geo["x_sl"], x_tp=geo["x_tp"], nc_x=geo["nc_x"], slip=0.5)
    return {"justo": (S_f, ax_f, None), "real CON oro": (S_r, ax_r, None), "real SIN oro": (S_r, ax_r, LD.gold_mask(ax_r))}


def dummy(S):
    """Agrega un dia 'sin operar' (P&L 0, sin comision neta) al final de las tablas para modelar dias perdidos por fallos de API. Devuelve (Spec, indice del dia)."""
    n = S.flat.shape[0]
    row = lambda a, v: np.concatenate([a, np.full((1,) + a.shape[1:], v, a.dtype)])
    S2 = dc.replace(S, adv=row(S.adv, INF), tpt=row(S.tpt, INF), flat=np.concatenate([S.flat, [S.comm / S.tv]]), amag=row(S.amag, 0.0),
                    xadv=row(S.xadv, INF), xtpt=row(S.xtpt, INF), xflat=np.concatenate([S.xflat, [S.x_comm / S.x_tv]]), xamag=row(S.xamag, 0.0), xser=np.concatenate([S.xser, [0.0]]))
    return S2, n


def net(S, ax, mask, skipf=0.0, seed=5):
    pool = np.arange(len(ax)) if mask is None else np.nonzero(mask)[0]
    D = pool[np.random.default_rng(seed).integers(0, len(pool), (T, H))]
    if skipf > 0:
        S, dn = dummy(S); D = np.where(np.random.default_rng(seed + 1).random(D.shape) < skipf, dn, D)
    r = acct(S, D)
    return r["cash"][:, -1], r


if __name__ == "__main__":
    W = worlds()
    P("PARTE 1 — cuanto informan los primeros N intentos")
    P(f"{'mundo':14s}{'p pase/intento':>15s}{'dias hasta el intento N (mediana)':>0s}")
    stats = {}
    for name, (S, ax, mask) in W.items():
        pool = np.arange(len(ax)) if mask is None else np.nonzero(mask)[0]
        D = pool[np.random.default_rng(11).integers(0, len(pool), (T, H))]
        r = acct(S, D)
        p = r["n_pass"].sum() / r["n_att"].sum(); stats[name] = p
        att_at = 1 + np.cumsum(r["blow_d"], axis=1)             # intentos iniciados al cierre de cada dia
        md = r["mode_d"]; prev = np.concatenate([np.zeros((T, 1), np.int8), md[:, :-1]], axis=1)
        res_ev = (r["blow_d"] & (prev == 0)) | ((prev == 0) & np.isin(md, (1, 3)))            # Combine resuelto: quiebre (MLL) o pase
        res_at = np.cumsum(res_ev, axis=1)
        row = f"{name:14s}{p:>15.3f}   dias (med.) hasta N Combines RESUELTOS: "
        for N in (3, 5, 10, 20):
            d = np.where((res_at >= N).any(1), (res_at >= N).argmax(1) + 1, H + 1); row += f"N={N}: {np.median(d):.0f}d  "
        P(row)
        by = lambda d: np.mean(res_at[:, d - 1])
        paid = r["take_d"] > 0
        P(f"{'':14s}   Combines resueltos a 10/20/40/60 dias: {by(10):.1f} / {by(20):.1f} / {by(40):.1f} / {by(60):.1f};  P(>=1 pase a 10/20/40/60 dias)= " + " / ".join(f"{np.mean((r['pass_day']>0)&(r['pass_day']<=d)):.0%}" for d in (10, 20, 40, 60)) +
          ";  P(>=1 payout a 20/40/60 dias)= " + " / ".join(f"{paid[:, :d].any(1).mean():.0%}" for d in (20, 40, 60)))
    p0 = stats["justo"]
    P(f"\nSi el modelo es correcto (p = {p0:.3f}, intentos independientes; un 'pase' = Combine pasado). Alternativas de 'el modelo falla': p = 0.20 y p = 0.15 (la mitad). Regla: rechazar el modelo si pases <= k* con alfa <= 5%.")
    P(f"{'N':>4s}{'P(0 pases)':>12s}{'P(<=1 pase)':>13s}{'k*':>4s}{'alfa real':>10s}{'poder si p=0.20':>17s}{'poder si p=0.15':>17s}{'P(0 pases | p=0.15)':>21s}")
    for N in (3, 5, 10, 20, 40):
        ks = [k for k in range(N + 1) if binom_cdf(k, N, p0) <= 0.05]; k_star = max(ks) if ks else -1
        pw = lambda pp: binom_cdf(k_star, N, pp) if k_star >= 0 else 0.0
        P(f"{N:>4d}{binom_cdf(0,N,p0):>12.3f}{binom_cdf(1,N,p0):>13.3f}{k_star:>4d}{(binom_cdf(k_star,N,p0) if k_star>=0 else 0):>10.3f}{pw(0.20):>17.2f}{pw(0.15):>17.2f}{(1-0.15)**N:>21.3f}")
    # ------------------------------------------------------------- Parte 2
    P("\nPARTE 2 — neto anual por cuenta (paso 2) bajo friccion adicional, justo / real CON oro / real SIN oro. 'dEV' = cambio vs base. Cada fila cambia UNA friccion.")
    base = {k: net(*v)[0].mean() for k, v in W.items()}
    P(f"{'friccion':58s}{'justo':>8s}{'CON oro':>9s}{'SIN oro':>9s}{'dEV SIN oro':>13s}")
    P(f"{'base (slip stop 0.5, entrada exacta, TP al tocar, comision modelada)':58s}{base['justo']:>8,.0f}{base['real CON oro']:>9,.0f}{base['real SIN oro']:>9,.0f}{0:>13,.0f}{stats['justo']:>9.3f}")
    def row(label, f):
        vals = {}
        for k, (S, ax, mask) in W.items():
            S2, skipf = f(S); nn, rr = net(S2, ax, mask, skipf); vals[k] = nn.mean()
            if k == "justo": pj = rr["n_pass"].sum() / rr["n_att"].sum()
        P(f"{label:58s}{vals['justo']:>8,.0f}{vals['real CON oro']:>9,.0f}{vals['real SIN oro']:>9,.0f}{vals['real SIN oro']-base['real SIN oro']:>13,.0f}{pj:>9.3f}")
        return vals
    sens = {}
    for e in (1, 2, 3, 4): sens[f"entrada adversa {e} tick(s)"] = row(f"slippage de ENTRADA adverso {e} tick(s) por contrato", lambda S, e=e: (dc.replace(S, entry_slip=e), 0.0))
    for s_ in (0.0, 1.0, 1.5, 2.0): sens[f"stop slip {s_}"] = row(f"slippage de STOP {s_} (fraccion hasta el extremo de la barra; >1 = peor que el extremo)", lambda S, s_=s_: (dc.replace(S, slip=s_), 0.0))
    for t in (1, 2): sens[f"TP +{t}"] = row(f"TP solo se llena si el precio lo cruza {t} tick(s)", lambda S, t=t: (dc.replace(S, tp_fill_extra=t), 0.0))
    for c in (1.2, 1.5): sens[f"comision x{c}"] = row(f"comision x{c}", lambda S, c=c: (dc.replace(S, comm=S.comm * c, x_comm=S.x_comm * c), 0.0))
    for f_ in (1.1, 1.25): sens[f"fee x{f_}"] = row(f"costo por intento (Combine y reinicio) x{f_}", lambda S, f_=f_: (dc.replace(S, fee_scale=f_), 0.0))
    for sk in (0.02, 0.05, 0.10): sens[f"skip {sk}"] = row(f"{sk:.0%} de los dias sin operar (fallo de API / senal perdida)", lambda S, sk=sk: (S, sk))
    sens["combo"] = row("COMBINADO: entrada 1 tick + stop slip 1.0 + TP +1 + comision x1.2 + 2% dias", lambda S: (dc.replace(S, entry_slip=1, slip=1.0, tp_fill_extra=1, comm=S.comm * 1.2, x_comm=S.x_comm * 1.2), 0.02))
    sens["combo2"] = row("ADVERSO: entrada 2 ticks + stop slip 1.5 + TP +1 + comision x1.5 + 5% dias", lambda S: (dc.replace(S, entry_slip=2, slip=1.5, tp_fill_extra=1, comm=S.comm * 1.5, x_comm=S.x_comm * 1.5), 0.05))
    # modelo de pase roto (para el valor de esperar)
    P("\nMUNDO 'EL MODELO FALLA' (pase exogeno reducido a la mitad con todo lo demas igual): neto por cuenta")
    vals = {}
    for k, (S, ax, mask) in W.items():
        vals[k] = net(dc.replace(S, p_dn=0.5, seed=9), ax, mask)[0].mean()
    P(f"  justo {vals['justo']:,.0f} | CON oro {vals['real CON oro']:,.0f} | SIN oro {vals['real SIN oro']:,.0f}")
    S, ax, mask = W["justo"]
    rr = simulate(dc.replace(S, K=0), np.random.default_rng(3).integers(0, len(ax), (T, 126)), lag=0, skip=None, start_mode=1)
    pay = rr["take_d"].astype(float).sum(1); cv = pay.std() / pay.mean()
    P(f"\nPAYOUT por XFA (mundo justo, una vida): media ${pay.mean():,.0f}, desv. est. ${pay.std():,.0f}, CV {cv:.2f}, P(pago>0) {np.mean(pay>0):.0%} -> XFAs necesarias para estimar la media con +-25% (IC95%): {(1.96*cv/0.25)**2:.0f}; con +-50%: {(1.96*cv/0.5)**2:.0f}")
    tx = LD.tab("MGC", 433, kmax=800, tmax=800)
    k = geo_x = 728
    hit = (tx["adv"][:, k] < INF) & ~(tx["tpt"][:, k] < tx["adv"][:, k])
    ex = (tx["amag"][hit, k] - k)
    P(f"Slippage de stop MODELADO en la XFA (MGC, stop 728 ticks, dias con stop: {hit.sum()} de {len(hit)}): exceso hasta el extremo de la barra, mediana {np.median(ex):.0f} ticks, media {ex.mean():.0f}; con slip 0.5 el modelo cobra {0.5*ex.mean():.0f} ticks (= ${0.5*ex.mean():.0f} por contrato y stop) en promedio, p90 {0.5*np.percentile(ex,90):.0f}")
    from scripts.tables_generic import median_range_ticks
    P(f"Rango mediano entrada->flatten: MES 9:45 {median_range_ticks('MES',585):.0f} ticks; MGC 7:13 {median_range_ticks('MGC',433):.0f} ticks; MCL 8:43 {median_range_ticks('MCL',523):.0f} ticks")
    open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dd_cash", "stacking_info_friction_report.txt"), "w").write("\n".join(lines))
