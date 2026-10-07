"""EXP 3 — Pipeline completo por plan de Bulenox (Qualification+Master, Momentum, Fast Track; 50K Opcion 2) y ESCALA a varias cuentas con el costo fijo de API de terceros ($100/mes por conexion).
Ciclo: calificacion (intentos con reinicios/recompras, ventana de 21 dias) -> cuenta fondeada (vida hasta quiebre o 126 dias) -> nueva compra. Se muestrean intentos y vidas de las simulaciones por barra
(bulenox/barsim.py; slip del stop 0.5, orden conservador). Dos escenarios: REAL-CONSISTENTE (configs consistentes en ambas mitades de la serie real, exp1/exp2) y MUNDO JUSTO (mismas configs, trayectorias
sinteticas sin deriva ni persistencia = piso prudente). Costos por cuenta: compras, reinicios, activacion del Master; costos compartidos: API $100/mes + datos Massive $43.5 + Pi $1.5 por mes (21 dias).
Escala: N 'slots' independientes o perfectamente correlacionados (mismas senales); maximo 5 cuentas Master-level activas (Bulenox [HC master]); la API cuesta $100 sin importar N.
SANDBOX / R&D. Uso: python bulenox/experiments/exp3_pipeline_scale.py"""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import numpy as np
from bulenox.rules import plan, API_THIRD_PARTY_MONTHLY, ACCESS_TRADING_DAYS
from bulenox import barsim

SLIP = 0.5; HOR = 126; ACT_LAG = 2
SHARED_MONTHLY = API_THIRD_PARTY_MONTHLY + 43.5 + 1.5
PLANS = {
    "Qualification Opc.2 + Master ($175 + $148)": dict(q=plan("qualification", 50_000, 2), stage="master", fp=plan("qualification", 50_000, 2), qcfg=("MGC", 433, 100, 1.0), fcfg=dict(real=("MGC", 433, 400, 1.0, 167), fair=("MNQ", 525, 900, 1.0, 513))),
    "Momentum Opc.2 ($143, Master gratis)": dict(q=plan("momentum", 50_000, 2), stage="momentum_master", fp=plan("momentum", 50_000, 2), qcfg=("MGC", 433, 160, 1.0), fcfg=dict(real=("MES", 525, 900, 1.0, 104), fair=("MNQ", 525, 250, 1.0, 513))),
    "Fast Track Opc.2 ($488, sin evaluacion)": dict(q=None, stage="fast_track", fp=plan("fast_track", 50_000, 2), qcfg=None, fcfg=dict(real=("MES", 525, 900, 1.0, 104), fair=("MES", 525, 900, 1.0, 104))),
}


def samples(world, cfg, rng, nrep=8):
    """Devuelve (res_qual (n,3) o None, raw_funded (n,5)). world: 'real' o 'fair' (sintetico, nrep replicas agrupadas)."""
    out_q = []; out_f = []
    def bars_for(prod, em):
        return [barsim.build_bars(prod, em)] if world == "real" else [barsim.build_bars_synthetic(prod, em, rng) for _ in range(nrep)]
    if cfg["q"] is not None:
        prod, em, tp, gf = cfg["qcfg"]
        for i, b in enumerate(bars_for(prod, em)):
            out_q.append(barsim.run_qual(b, cfg["q"], tp, gf, n=12000 if world == "real" else 2500, seed0=11 + i, slip=SLIP))
    prod, em, g, rho, tp = cfg["fcfg"]["real" if world == "real" else "fair"]
    for i, b in enumerate(bars_for(prod, em)):
        out_f.append(barsim.run_funded(b, cfg["stage"], cfg["fp"], g, rho, tp, n=6000 if world == "real" else 1200, seed0=21 + i, horizon=HOR, slip=SLIP)["raw"])
    return (np.vstack(out_q) if out_q else None), np.vstack(out_f)


def samples_oos(name, cfg):
    """FUERA DE MUESTRA: la config se elige en una mitad de los dias (mejor pase / mejor payout) y se evalua en la OTRA mitad; se agrupan los dos pliegues."""
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    g1 = json.load(open(os.path.join(base, "exp1_grid.json"))); g2 = json.load(open(os.path.join(base, "exp2_grid.json")))
    rq = None
    if cfg["q"] is not None:
        key = ("qualification" if cfg["q"].name == "qualification" else "momentum") + "|2"
        rows = g1[key]; outs = []
        for pick, evalhalf in ((max(rows, key=lambda r: r["h1"]), 2), (max(rows, key=lambda r: r["h2"]), 1)):
            bars = barsim.build_bars(pick["prod"], pick["em"]); n = len(bars["start"]); idx = np.arange(n // 2, n) if evalhalf == 2 else np.arange(n // 2)
            outs.append(barsim.run_qual(bars, cfg["q"], pick["tp"], pick["gf"], n=8000, seed0=31, idx=idx, slip=SLIP))
        rq = np.vstack(outs)
    rows = g2[cfg["stage"]]; outs = []
    for pick, evalhalf in ((max(rows, key=lambda r: r["h1"]), 2), (max(rows, key=lambda r: r["h2"]), 1)):
        bars = barsim.build_bars(pick["prod"], pick["em"]); n = len(bars["start"]); idx = np.arange(n // 2, n) if evalhalf == 2 else np.arange(n // 2)
        outs.append(barsim.run_funded(bars, cfg["stage"], cfg["fp"], pick["g"], pick["rho"], pick["tp"], n=6000, seed0=41, idx=idx, horizon=HOR, slip=SLIP)["raw"])
    return rq, np.vstack(outs)


def cycle(rng, cfg, rq, rf):
    """Un ciclo: devuelve (costo_fijo_por_cuenta SIN api/datos, payout, dias)."""
    q = cfg["q"]; days = 0.0; cost = 0.0
    if q is None:                                                        # Fast Track: compra directa
        cost = cfg["fp"].price
    else:
        cost = q.price; t = 0.0
        for _ in range(300):
            j = rng.integers(0, len(rq)); r, d = rq[j, 0], rq[j, 1]
            if t + d > ACCESS_TRADING_DAYS and r != 1: cost += q.price; t = 0.0
            t += d; days += d
            if r == 1: break
            cost += (q.reset_fee if q.reset_fee is not None else q.price)
        cost += q.master_activation + cfg.get("renew", 0.0) * np.floor(days / ACCESS_TRADING_DAYS)
        days += ACT_LAG
    k = rng.integers(0, len(rf)); pay, life = rf[k, 0], rf[k, 2]
    return cost, pay, days + life


def sequence(rng, cfg, rq, rf, horizon_days=252):
    t = 0.0; net = 0.0; fees = 0.0; pays = 0.0; cycles = 0
    while t < horizon_days:
        c, p, d = cycle(rng, cfg, rq, rf)
        frac = min(1.0, (horizon_days - t) / d) if t + d > horizon_days else 1.0     # ciclo parcial: prorratea el payout/costo
        net += frac * (p - c); fees += frac * c; pays += frac * p; t += d; cycles += 1
    return net, fees, pays, cycles


def run(world, nseq=4000, seed=5):
    rng = np.random.default_rng(seed); res = {}
    for name, cfg in PLANS.items():
        rq, rf = samples_oos(name, cfg) if world == "oos" else samples(world, cfg, rng)
        seqs = np.array([sequence(rng, cfg, rq, rf) for _ in range(nseq)])      # net por cuenta SIN costos compartidos
        # metricas de ciclo
        cy = np.array([cycle(rng, cfg, rq, rf) for _ in range(8000)])
        res[name] = dict(seq=seqs, pass_q=(rq[:, 0] == 1).mean() if rq is not None else float("nan"), pay=cy[:, 1].mean(), cost=cy[:, 0].mean(), days=cy[:, 2].mean(),
                         p1=(rf[:, 3] >= 0).mean(), life=rf[:, 2].mean())
    return res


def scale_table(seqs, ns=(1, 2, 3, 5), rng=None):
    rng = rng or np.random.default_rng(1); rows = []
    shared = SHARED_MONTHLY * 12
    for n in ns:
        corr = n * seqs[:, 0] - shared                                                   # perfectamente correlacionado: N copias de la misma secuencia
        ind = np.array([seqs[rng.integers(0, len(seqs), n), 0].sum() for _ in range(len(seqs))]) - shared   # independientes
        rows.append((n, corr, ind))
    return rows


if __name__ == "__main__":
    lines = []; P = lambda s: (print(s), lines.append(s))
    P(f"EXP 3 — Pipeline por plan Bulenox (50K, Opcion 2), 12 meses (252 dias), slip del stop {SLIP}, costos compartidos ${SHARED_MONTHLY:.1f}/mes (API $100 + Massive $43.5 + Pi $1.5); las cifras por cuenta NO incluyen los compartidos")
    for world in ("oos", "real", "fair"):
        res = run(world)
        titulo = dict(oos="FUERA DE MUESTRA (config elegida en una mitad de los dias y evaluada en la otra) = EXPECTATIVA",
                      real="REAL-CONSISTENTE (config elegida mirando AMBAS mitades) = COTA SUPERIOR optimista, con sesgo de seleccion",
                      fair="MUNDO JUSTO sintetico (sin persistencia ni deriva) = PISO prudente")[world]
        P("\n" + "=" * 150 + f"\nESCENARIO: {titulo}\n" + "=" * 150)
        for name, r in res.items():
            s = r["seq"]; net = s[:, 0]
            P(f"\n{name}\n  por ciclo: pase calificacion {r['pass_q']:.1%} | costo de cuentas ${r['cost']:,.0f} | payout por cuenta fondeada ${r['pay']:,.0f} (P>=1 pago {r['p1']:.0%}, vida {r['life']:.0f} dias) | dias por ciclo {r['days']:.0f} | neto por ciclo ${r['pay']-r['cost']:,.0f}")
            P(f"  UNA cuenta, 12 meses, SIN compartidos: neto medio ${net.mean():,.0f} | p10/p50/p90 ${np.percentile(net,10):,.0f}/${np.percentile(net,50):,.0f}/${np.percentile(net,90):,.0f} | ciclos {s[:,3].mean():.1f}")
            for n, corr, ind in scale_table(s):
                P(f"  N={n} cuentas, CON compartidos ${SHARED_MONTHLY*12:,.0f}/año: correlacionadas media ${corr.mean():,.0f}, p10 ${np.percentile(corr,10):,.0f}, P(<0)={np.mean(corr<0):.0%} | independientes media ${ind.mean():,.0f}, p10 ${np.percentile(ind,10):,.0f}, P(<0)={np.mean(ind<0):.0%}")
    open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "exp3_pipeline_scale_output.txt"), "w").write("\n".join(lines))
