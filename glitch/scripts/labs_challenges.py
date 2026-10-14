"""Topstep Labs — retos de dos rondas (#003 $3K, #004 $1.5K, #005 $6K, #007 $1.5K) y la Combine estatica de $50K (#006). SANDBOX / R&D. Estado de los datos: los 7 'drops' aparecen bajo 'Past Lab Drops' en
topstep.com/labs (13-oct-2026): NINGUNO se puede comprar hoy; este modelo sirve para evaluar el SIGUIENTE drop y para entender la estructura.
Reglas usadas (help.topstep.com/15520357, leidas 13-oct-2026): ronda = alcanzar el objetivo antes de tocar el MLL ESTATICO (sin DLL, sin consistencia, sin minimo de dias); dos rondas identicas; pago FIJO una vez (sin 90/10)
al pasar la 2.a; 90 dias de vida (cada ronda) y cierre por 30 dias sin operar; limites de contratos por drop. NO VERIFICADO: si el objetivo se evalua intradia o al cierre y si el MLL cuenta el P&L no realizado en
tiempo real (se modela: liquidacion en tiempo real, objetivo cumplido al llenarse el TP). Politica estructural (no optimizada): TP = objetivo restante; stop = distancia al piso (liquidacion).
Uso: python -m scripts.labs_challenges"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np, dataclasses as dc
from scripts.tables_generic import build, build_synthetic, SPEC, median_range_ticks
from dd_cash import lever_data as LD
from scripts.lever_common import run, summ

lines = []; P = lambda s: (print(s), lines.append(s))
INF = 10 ** 6
ENTRY = 9 * 60 + 45
KM = TM = 2600
T = 30000


def tabs_for(prod, synthetic, nw=40):
    if not synthetic:
        return [build(prod, ENTRY, kmax=KM, tmax=TM)]
    return [build_synthetic(prod, ENTRY, np.random.default_rng(100 + w), kmax=KM, tmax=TM) for w in range(nw)]


def stack(tabs):
    return dict(adv=np.concatenate([t["adv"] for t in tabs]), tpt=np.concatenate([t["tpt"] for t in tabs]), flat=np.concatenate([t["flat"] for t in tabs]),
                amag=np.concatenate([t["amag"] for t in tabs]), tv=tabs[0]["tv"], comm=tabs[0]["comm"])


def sim_round(tab, nc, target, mll, max_days=60, n=T, seed=1, slip=0.5, tp_cap=None):
    """Una ronda con MLL estatico. Devuelve (P(pasar), dias medios de los que pasan)."""
    rng = np.random.default_rng(seed); nd = len(tab["flat"])
    b = np.zeros(n); alive = np.ones(n, bool); passed = np.zeros(n, bool); dpass = np.zeros(n)
    unit = nc * tab["tv"]; comm = tab["comm"] * nc
    for d in range(1, max_days + 1):
        di = rng.integers(0, nd, n)
        R = np.maximum(target - b, 1.0)
        dist = b + mll
        k = np.clip(np.ceil(dist / unit - 1e-9), 1, KM).astype(int)
        tpk = np.clip(np.ceil((R + comm) / unit - 1e-9), 1, TM).astype(int)
        if tp_cap: tpk = np.minimum(tpk, tp_cap)
        ab = tab["adv"][di, k]; tb = tab["tpt"][di, tpk]
        tp_hit = tb < ab; sl_hit = ~tp_hit & (ab < INF)
        loss = k + slip * (tab["amag"][di, k] - k)
        pnl = np.where(tp_hit, tpk * unit, np.where(sl_hit, -loss * unit, tab["flat"][di] * unit)) - comm
        pnl = np.where(alive & ~passed, pnl, 0.0)
        b = b + pnl
        now_pass = alive & ~passed & (b >= target - 1e-6)
        dpass = np.where(now_pass, d, dpass); passed |= now_pass
        alive &= ~(b <= -mll + 1e-9)
    return passed.mean(), (dpass[passed].mean() if passed.any() else float("nan"))


DROPS = [("#003 $3K Challenge", 49, 3000, 1000, 3000, {"MNQ": 10, "MES": 10, "MGC": 6}),
         ("#004 $1.5K Challenge", 39, 1500, 500, 1500, {"MNQ": 2, "MES": 2, "MGC": 1}),
         ("#005 $6K Challenge", 149, 6000, 2000, 6000, {"MNQ": 10, "MES": 10, "MGC": 6}),
         ("#007 $1.5K Challenge (precio NO publicado; objetivo $1,000, MLL $500, premio $1,500)", None, 1000, 500, 1500, {"MNQ": 20, "MES": 20, "MGC": 6})]

if __name__ == "__main__":
    P("TOPSTEP LABS — retos de dos rondas con MLL estatico (politica: TP = objetivo restante, stop = liquidacion; slip 0.5; comision incluida; 60 dias de trading por ronda)")
    P(f"{'reto':44s}{'prod':>5s}{'nc':>4s} | {'P(ronda) justo':>14s}{'real':>7s}{'dias':>6s} | {'P(2 rondas) j / r':>18s}{'EV por compra j / r':>21s} | teorico M/(M+T)")
    res = {}
    for name, fee, tgt, mll, rew, ncs in DROPS:
        for prod, nc in ncs.items():
            st = stack(tabs_for(prod, True)); rt = tabs_for(prod, False)[0]
            pj, dj = sim_round(st, nc, tgt, mll, seed=3); pr, dr = sim_round(rt, nc, tgt, mll, seed=4)
            both_j, both_r = pj ** 2, pr ** 2
            ev = lambda p: (p * rew - fee) if fee is not None else float("nan")
            res[(name, prod)] = (pj, pr, dj)
            ev_txt = f"{ev(both_j):>8,.0f} / {ev(both_r):>6,.0f}" if fee is not None else f"(precio?) pago esperado {both_j*rew:,.0f} / {both_r*rew:,.0f}"
            P(f"{name[:44]:44s}{prod:>5s}{nc:>4d} | {pj:>14.1%}{pr:>7.1%}{dj:>6.1f} | {both_j:>8.2%} / {both_r:>6.2%}  {ev_txt:>21s} | {mll/(mll+tgt):.1%}")
    P("\nSensibilidad (reto #003, MNQ x10): dias por ronda, TP limitado al rango mediano diario, slip")
    st = stack(tabs_for("MNQ", True)); rt = tabs_for("MNQ", False)[0]
    R_med = int(median_range_ticks("MNQ", ENTRY))
    for lab, kw in (("60 dias (base)", {}), ("30 dias", dict(max_days=30)), ("90 dias", dict(max_days=90)), ("TP <= rango mediano diario", dict(tp_cap=R_med)), ("slip 1.0", dict(slip=1.0)), ("slip 0.0", dict(slip=0.0))):
        pj, _ = sim_round(st, 10, 3000, 1000, seed=5, **kw); pr, _ = sim_round(rt, 10, 3000, 1000, seed=6, **kw)
        P(f"  {lab:32s} P(ronda) justo {pj:.1%} real {pr:.1%}  -> EV/compra justo {pj**2*3000-49:>6,.0f} real {pr**2*3000-49:>6,.0f}")
    # tickets: distribucion de n compras de #003 (sin tope de compra segun la pagina)
    pj, pr, _ = res[("#003 $3K Challenge", "MNQ")]
    P("\nRESULTADO DE COMPRAR n retos #003 (MNQ x10), cada uno gana $3,000 con prob. p2 = P(ronda)^2 (binomial, independientes)")
    rng = np.random.default_rng(11)
    for n in (5, 20, 50, 100):
        for lab, p in (("justo", pj ** 2), ("real", pr ** 2)):
            w = rng.binomial(n, p, 200000); net = w * 3000 - 49 * n
            P(f"  n={n:>3d} ({lab:5s}, p2={p:.2%}): costo ${49*n:>5,d} | neto medio ${net.mean():>8,.0f} mediana ${np.median(net):>8,.0f} | P(<0) {np.mean(net<0):>5.1%} P(>=$10k) {np.mean(net>=10000):>5.1%} p5 ${np.percentile(net,5):>7,.0f}")
    # ---- #006: Combine estatica de $50K + XFA (MLL estatico, tope $8,000, DLL $1,000)
    P("\n#006 $50K STATIC Trading Combine ($149 pago unico, sin reinicios): objetivo $4,000, MLL estatico $2,000, DLL obligatorio $1,000 (suave: al tocarlo se liquida y se bloquea la sesion, no es falla), consistencia 55%, 4 minis/40 micros;")
    P("XFA: tope de pago $8,000 (supuesto: 50% del balance, 5 dias >= $150), MLL estatico $2,000 -> $0 tras el 1er pago, DLL $1,000. Etapa 1 con politica 'audaz' (TP = objetivo restante limitado a 55% del objetivo por dia, stop = min(distancia al piso, DLL)); etapa 2 con el motor de palancas.")
    def sim_static_combine(tab, nc, target=4000.0, mll=2000.0, dll=1000.0, cons=0.55, max_days=60, n=T, seed=1, slip=0.5):
        rng = np.random.default_rng(seed); nd = len(tab["flat"])
        b = np.zeros(n); alive = np.ones(n, bool); passed = np.zeros(n, bool); best = np.zeros(n); days = np.zeros(n)
        unit = nc * tab["tv"]; comm = tab["comm"] * nc
        for d in range(1, max_days + 1):
            di = rng.integers(0, nd, n)
            need = np.maximum(target, best / cons)
            R = np.maximum(need - b, 1.0)
            G = np.minimum(R, cons * target)
            dist = np.minimum(b + mll, dll)
            k = np.clip(np.floor((dist - comm) / unit), 1, KM).astype(int)
            tpk = np.clip(np.ceil((G + comm) / unit - 1e-9), 1, TM).astype(int)
            ab = tab["adv"][di, k]; tb = tab["tpt"][di, tpk]
            tp_hit = tb < ab; sl_hit = ~tp_hit & (ab < INF)
            loss = k + slip * (tab["amag"][di, k] - k)
            pnl = np.where(tp_hit, tpk * unit, np.where(sl_hit, -loss * unit, tab["flat"][di] * unit)) - comm
            act = alive & ~passed
            pnl = np.where(act, pnl, 0.0)
            b = b + pnl
            best = np.where(act & (pnl > best), pnl, best)
            need = np.maximum(target, best / cons)
            ok = act & (b >= need) & (d >= 2)
            days = np.where(ok, d, days); passed |= ok
            alive &= ~(b <= -mll + 1e-9)
        return passed.mean(), (days[passed].mean() if passed.any() else float("nan"))
    from dd_cash.lever_engine import simulate as simL
    xg = dict(x_sl=498, x_tp=622, nc_x=2, x_dll=1000.0, xdll=1000.0, cap=8000.0, static_x=True, slip=0.5)
    def xfa_life(S, ax, mask, hx=126):
        pool = np.arange(len(ax)) if mask is None else np.nonzero(mask)[0]
        D = pool[np.random.default_rng(13).integers(0, len(pool), (20000, hx))]
        r = simL(dc.replace(S, K=0), D, lag=0, skip=None, start_mode=1)
        return r["take_d"].astype(float).sum(1)
    for lab, synth in (("justo", True), ("real", False)):
        for prod, nc in (("MNQ", 40), ("MES", 40)):
            tab = stack(tabs_for(prod, synth)); pp, dd = sim_static_combine(tab, nc, seed=31)
            if synth: S, ax = LD.make_pool_spec(n_worlds=40, **xg)
            else: S, ax = LD.make_spec(**xg)
            for xl, mask in (("", None), (" (sin oro)", None if synth else LD.gold_mask(ax))):
                if synth and xl: continue
                pay = xfa_life(S, ax, mask); ev = pp * pay.mean() - 149
                P(f"  {lab+xl:14s} Combine en {prod} x{nc}: P(pasar) {pp:.1%} ({dd:.1f} dias) | pago medio por XFA ${pay.mean():,.0f} (P(>=1 pago) {np.mean(pay>0):.0%}) | EV por compra = P x pago - $149 = ${ev:,.0f}")
    S, ax = LD.make_spec(**dict(xg, c_prod="MNQ", c_entry=ENTRY, nc=40, tp=105, sl=100, mll=2000.0, target=4000.0, static_c=True, dll=1000.0, fee=149.0, act=0.0, K=1, cons=0.55))
    o = run(S, ax, T=20000, seed=21)
    P(f"  (control) bracket FIJO tipo G2 en el motor completo (MNQ x40, TP 105 ticks): P(pasar) {o['npass'].mean():.1%}, EV por compra ${o['net'].mean():,.0f} -> la politica importa: la 'audaz' es la comparable con el techo de juego justo (M/(M+T) = 33.3%)")
    open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dd_cash", "labs_challenges_report.txt"), "w").write("\n".join(lines))
