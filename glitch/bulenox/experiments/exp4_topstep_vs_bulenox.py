"""EXP 4 — Topstep vs Bulenox en el MISMO marco (simulador por barra, orden conservador, slip del stop 0.5, seleccion fuera de muestra, mismo protocolo de ciclos y de costos compartidos).
Topstep: Combine 50K ($49 por intento/reinicio y renovacion cada 21 dias, activacion $149, consistencia 55%, minimo 2 dias, piso en $0) + XFA estandar (5 dias >= $150, pago min(50% balance, $2,000), 90%, piso $0 tras pagar;
escalado XFA 20/30/40 SUPUESTO); costos compartidos $59.5/mes (API ProjectX $14.5 + Massive $43.5 + Pi $1.5). Bulenox: Qualification Opc.2 + Master y Momentum Opc.2 con costos compartidos $145/mes.
Escala: hasta 5 cuentas fondeadas (Topstep permite hasta 5 XFA segun el log del 24-sep; Bulenox hasta 5 Master-level) con los costos compartidos fijos; riesgo de conducta de multiples cuentas NO modelado.
SANDBOX / R&D. Uso: python bulenox/experiments/exp4_topstep_vs_bulenox.py"""
import os, sys, itertools, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import numpy as np
from bulenox.rules import Plan, plan
from bulenox import barsim
from bulenox.experiments import exp3_pipeline_scale as e3
from scripts.tables_generic import median_range_ticks

SLIP = 0.5; HOR = 126
TOP_Q = Plan("topstep_combine", 2, 50_000, 49.0, 3_000.0, 2_000.0, None, (4,), reset_fee=49.0, master_activation=149.0)
QCOMBOS = [("MES", "8:45", 525), ("MES", "9:45", 585), ("MES", "12:30", 750), ("MNQ", "8:45", 525), ("MGC", "7:13", 433), ("MGC", "8:15", 495), ("M2K", "9:15", 555)]
FCOMBOS = QCOMBOS + [("MNQ", "12:30", 750), ("MGC", "9:45", 585)]
TPS = (20, 30, 60, 100); GF = (0.3, 0.45, 0.55)
GS = (150, 250, 400, 600, 900, 1300); RHOS = (0.2, 0.35, 0.5, 0.75, 1.0); QS = (0.2, 0.35, 0.5)


def grids():
    qrows = []; frows = []
    for prod, en, em in QCOMBOS:
        bars = barsim.build_bars(prod, em); n = len(bars["start"]); h1 = np.arange(n // 2); h2 = np.arange(n // 2, n)
        for tp, gf in itertools.product(TPS, GF):
            f = lambda idx: (barsim.run_qual(bars, TOP_Q, tp, gf, n=2500, seed0=1, idx=idx, slip=SLIP, lock_cap=0.0, cons=0.55, min_days=2, max_days=30)[:, 0] == 1).mean()
            qrows.append(dict(prod=prod, em=em, tp=tp, gf=gf, h1=f(h1), h2=f(h2)))
    for prod, en, em in FCOMBOS:
        bars = barsim.build_bars(prod, em); n = len(bars["start"]); h1 = np.arange(n // 2); h2 = np.arange(n // 2, n); R = median_range_ticks(prod, em)
        for g, rho, q in itertools.product(GS, RHOS, QS):
            tp = max(1, int(round(q * R)))
            a = barsim.run_funded(bars, "topstep_xfa", None, g, rho, tp, n=1200, seed0=1, idx=h1, slip=SLIP)["payout"]
            b = barsim.run_funded(bars, "topstep_xfa", None, g, rho, tp, n=1200, seed0=1, idx=h2, slip=SLIP)["payout"]
            frows.append(dict(prod=prod, em=em, g=g, rho=rho, tp=tp, h1=a, h2=b))
    return qrows, frows


def topstep_samples(qrows, frows, world, rng):
    if world == "oos":
        outq = []; outf = []
        for pick, half in ((max(qrows, key=lambda r: r["h1"]), 2), (max(qrows, key=lambda r: r["h2"]), 1)):
            bars = barsim.build_bars(pick["prod"], pick["em"]); n = len(bars["start"]); idx = np.arange(n // 2, n) if half == 2 else np.arange(n // 2)
            outq.append(barsim.run_qual(bars, TOP_Q, pick["tp"], pick["gf"], n=8000, seed0=31, idx=idx, slip=SLIP, lock_cap=0.0, cons=0.55, min_days=2, max_days=30))
        for pick, half in ((max(frows, key=lambda r: r["h1"]), 2), (max(frows, key=lambda r: r["h2"]), 1)):
            bars = barsim.build_bars(pick["prod"], pick["em"]); n = len(bars["start"]); idx = np.arange(n // 2, n) if half == 2 else np.arange(n // 2)
            outf.append(barsim.run_funded(bars, "topstep_xfa", None, pick["g"], pick["rho"], pick["tp"], n=6000, seed0=41, idx=idx, horizon=HOR, slip=SLIP)["raw"])
        return np.vstack(outq), np.vstack(outf)
    # mundo justo: misma config de control (MES 9:45 / MNQ 8:45) en trayectorias sinteticas
    outq = []; outf = []
    for i in range(8):
        b = barsim.build_bars_synthetic("MES", 585, rng)
        outq.append(barsim.run_qual(b, TOP_Q, 30, 0.55, n=2500, seed0=11 + i, slip=SLIP, lock_cap=0.0, cons=0.55, min_days=2, max_days=30))
        b2 = barsim.build_bars_synthetic("MNQ", 525, rng)
        outf.append(barsim.run_funded(b2, "topstep_xfa", None, 900, 1.0, 513, n=1200, seed0=21 + i, horizon=HOR, slip=SLIP)["raw"])
    return np.vstack(outq), np.vstack(outf)


def pipeline_stats(cfg, rq, rf, rng, shared_monthly, nseq=4000):
    seqs = np.array([e3.sequence(rng, cfg, rq, rf) for _ in range(nseq)])
    cy = np.array([e3.cycle(rng, cfg, rq, rf) for _ in range(8000)])
    return seqs, dict(pass_q=(rq[:, 0] == 1).mean(), pay=cy[:, 1].mean(), cost=cy[:, 0].mean(), days=cy[:, 2].mean(), p1=(rf[:, 3] >= 0).mean(), life=rf[:, 2].mean())


def table(seqs, shared_monthly, ns=(1, 2, 3, 5)):
    rng = np.random.default_rng(1); sh = shared_monthly * 12; rows = []
    for n in ns:
        corr = n * seqs[:, 0] - sh
        ind = np.array([seqs[rng.integers(0, len(seqs), n), 0].sum() for _ in range(len(seqs))]) - sh
        rows.append((n, corr, ind))
    return rows


if __name__ == "__main__":
    qrows, frows = grids()
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    json.dump(dict(q=qrows, f=frows), open(os.path.join(base, "exp4_grid_topstep.json"), "w"))
    rng = np.random.default_rng(3); lines = []; P = lambda s: (print(s), lines.append(s))
    P(f"EXP 4 — Topstep vs Bulenox en el mismo marco (barra conservadora, slip {SLIP}, 12 meses/252 dias, ciclos con reinicios, activacion y renovaciones)")
    top_cfg = dict(q=TOP_Q, stage="topstep_xfa", fp=None, renew=49.0)
    for world, titulo in (("oos", "FUERA DE MUESTRA = EXPECTATIVA"), ("fair", "MUNDO JUSTO = PISO PRUDENTE")):
        P("\n" + "=" * 140 + f"\n{titulo}\n" + "=" * 140)
        items = []
        rq, rf = topstep_samples(qrows, frows, world, rng); items.append(("Topstep 50K (Combine + XFA)", top_cfg, rq, rf, 59.5))
        for name in ("Qualification Opc.2 + Master ($175 + $148)", "Momentum Opc.2 ($143, Master gratis)"):
            cfg = e3.PLANS[name]
            if world == "oos": rq2, rf2 = e3.samples_oos(name, cfg)
            else: rq2, rf2 = e3.samples("fair", cfg, rng)
            items.append((name.replace(" ($175 + $148)", "").replace(" ($143, Master gratis)", ""), cfg, rq2, rf2, e3.SHARED_MONTHLY))
        for name, cfg, rq_, rf_, sh in items:
            seqs, st = pipeline_stats(cfg, rq_, rf_, rng, sh)
            net = seqs[:, 0]
            P(f"\n{name}: pase calif. {st['pass_q']:.1%} | costo cuentas/ciclo ${st['cost']:,.0f} | payout por cuenta fondeada ${st['pay']:,.0f} (P>=1 {st['p1']:.0%}, vida {st['life']:.0f} d) | ciclo {st['days']:.0f} d | neto por ciclo ${st['pay']-st['cost']:,.0f}")
            P(f"   1 cuenta/12m SIN compartidos: media ${net.mean():,.0f} (p10 ${np.percentile(net,10):,.0f}, p50 ${np.percentile(net,50):,.0f}, p90 ${np.percentile(net,90):,.0f}); compartidos ${sh*12:,.0f}/año")
            for n, corr, ind in table(seqs, sh):
                P(f"   N={n}: neto 12m correlacionadas ${corr.mean():,.0f} (P<0 {np.mean(corr<0):.0%}) | independientes ${ind.mean():,.0f} (P<0 {np.mean(ind<0):.0%}, p10 ${np.percentile(ind,10):,.0f})")
    open(os.path.join(base, "exp4_topstep_vs_bulenox_output.txt"), "w").write("\n".join(lines))
