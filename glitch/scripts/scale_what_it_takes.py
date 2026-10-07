"""¿Que hace falta para llegar a cinco cifras medias/altas? Pipeline Topstep (Combine + XFA) en el simulador por barra (slip del stop 0.5, orden conservador) variando la CALIDAD de la estrategia
(ratio de Sharpe anual de una operacion larga diaria; se inyecta con una inclinacion de la probabilidad de que cada barra de 5 min sea alcista) y el TAMAÑO de la cuenta (50K con Cerebro 2 nc3 364/364; 150K con nc6 364/364,
tope de pago $2,000 / $5,000), y luego el numero de cuentas. Combine: politica 'TP al target restante' (tp=30 ticks, G=55% del objetivo) sobre MES 9:45; XFA: Cerebro 2 sobre MGC 7:13.
Costos: Combine $49 (50K) / $199 (150K) por intento y renovacion cada 21 dias, activacion $149 (SUPUESTO para 150K: el log tiene datos contradictorios), compartidos $59.5/mes (API ProjectX + Massive + Pi).
SANDBOX / R&D, offline. Uso: python scripts/scale_what_it_takes.py"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
from bulenox.rules import Plan
from bulenox import barsim
from bulenox.experiments import exp4_topstep_vs_bulenox as e4

SLIP = 0.5; HOR = 126
PLANS = {"50K": dict(q=Plan("topstep50", 2, 50_000, 49.0, 3_000.0, 2_000.0, None, (4,), reset_fee=49.0, master_activation=149.0), renew=49.0, dd=2000.0, cap=2000.0, g=1092.0, caps=(40.0,) * 4, br=(1e18,) * 3),
         "150K": dict(q=Plan("topstep150", 2, 150_000, 199.0, 9_000.0, 4_500.0, None, (15,), reset_fee=199.0, master_activation=149.0), renew=199.0, dd=4500.0, cap=5000.0, g=2184.0, caps=(60.0,) * 4, br=(1e18,) * 3)}
TILTS = (0.5, 0.502, 0.504, 0.506, 0.508, 0.51, 0.515, 0.52)
SHARED = 59.5


def sharpe(prod, em, p_up, rng, n=40):
    v = []
    for _ in range(n):
        b = barsim.build_bars_synthetic(prod, em, rng, p_up=p_up, long_only=True)
        r = (b["C"][b["end"]] - b["C"][b["start"]]) / b["tick"] * b["tv"]
        v.append(r)
    r = np.concatenate(v)
    return r.mean() / r.std(ddof=1) * np.sqrt(252), r.mean()


def samples(p_up, size, rng, nrep=6):
    cfg = PLANS[size]; rq = []; rf = []
    for i in range(nrep):
        b = barsim.build_bars_synthetic("MES", 585, rng, p_up=p_up, long_only=True)
        rq.append(barsim.run_qual(b, cfg["q"], 30, 0.55, n=2500, seed0=11 + i, slip=SLIP, lock_cap=0.0, cons=0.55, min_days=2, max_days=30))
        g = barsim.build_bars_synthetic("MGC", 433, rng, p_up=p_up, long_only=True)
        rf.append(barsim.run_funded_topstep(g, cfg["g"], 1.0, 364, n=1200, seed0=21 + i, horizon=HOR, slip=SLIP, dd=cfg["dd"], cap=cfg["cap"], caps_micro=cfg["caps"], breaks=cfg["br"], slfix=364.0)["raw"])
    return np.vstack(rq), np.vstack(rf)


def run_all(seed, nrep=16, tilts=TILTS):
    rng = np.random.default_rng(seed); res = {}
    for p in tilts:
        shm, _ = sharpe("MES", 585, p, rng, n=30); shg, _ = sharpe("MGC", 433, p, rng, n=30)
        row = dict(sh_mes=shm, sh_mgc=shg)
        for size in PLANS:
            rq, rf = samples_big(p, size, rng, nrep)
            cfg = dict(q=PLANS[size]["q"], stage="topstep_xfa", fp=None, renew=PLANS[size]["renew"])
            seqs = np.array([e4.e3.sequence(rng, cfg, rq, rf) for _ in range(8000)])
            cy = np.array([e4.e3.cycle(rng, cfg, rq, rf) for _ in range(8000)])
            row[size] = dict(net=seqs[:, 0].mean(), p10=np.percentile(seqs[:, 0], 10), p90=np.percentile(seqs[:, 0], 90), pneg=np.mean(seqs[:, 0] - SHARED * 12 < 0), pay=cy[:, 1].mean(), cost=cy[:, 0].mean(), days=cy[:, 2].mean(), pass_q=(rq[:, 0] == 1).mean(), p1=(rf[:, 3] >= 0).mean())
        res[p] = row
    return res


def samples_big(p_up, size, rng, nrep):
    cfg = PLANS[size]; rq = []; rf = []
    for i in range(nrep):
        b = barsim.build_bars_synthetic("MES", 585, rng, p_up=p_up, long_only=True)
        rq.append(barsim.run_qual(b, cfg["q"], 30, 0.55, n=3000, seed0=int(rng.integers(1, 10**6)), slip=SLIP, lock_cap=0.0, cons=0.55, min_days=2, max_days=30))
        g = barsim.build_bars_synthetic("MGC", 433, rng, p_up=p_up, long_only=True)
        rf.append(barsim.run_funded_topstep(g, cfg["g"], 1.0, 364, n=1500, seed0=int(rng.integers(1, 10**6)), horizon=HOR, slip=SLIP, dd=cfg["dd"], cap=cfg["cap"], caps_micro=cfg["caps"], breaks=cfg["br"], slfix=364.0)["raw"])
    return np.vstack(rq), np.vstack(rf)


if __name__ == "__main__":
    tilts = (0.5, 0.504, 0.508, 0.512, 0.52)
    runs = [run_all(sd, tilts=tilts) for sd in (1, 2, 3)]
    lines = []; P = lambda s: (print(s), lines.append(s))
    P("¿Qué hace falta para cinco cifras? Pipeline Topstep por barra (slip 0.5), 3 semillas independientes (media y rango min-max entre semillas). Neto anual DESPUÉS de fees, reinicios, activaciones y costos compartidos ($714/año una sola vez).")
    for p in tilts:
        sh = np.mean([r[p]["sh_mes"] for r in runs]); shg = np.mean([r[p]["sh_mgc"] for r in runs])
        P(f"\ninclinación p_up={p}: Sharpe anual medido MES {sh:.2f} | MGC {shg:.2f} (error ~±0.1)")
        for size in PLANS:
            nets = np.array([r[p][size]["net"] - SHARED * 12 for r in runs]); pn = np.mean([r[p][size]["pneg"] for r in runs])
            pay = np.mean([r[p][size]["pay"] for r in runs]); cost = np.mean([r[p][size]["cost"] for r in runs]); pq = np.mean([r[p][size]["pass_q"] for r in runs]); p1 = np.mean([r[p][size]["p1"] for r in runs])
            p10 = np.mean([r[p][size]["p10"] for r in runs]) - SHARED * 12; p90 = np.mean([r[p][size]["p90"] for r in runs]) - SHARED * 12
            P(f"   {size}: pase Combine {pq:.0%} | payout por XFA ${pay:,.0f} (P>=1 {p1:.0%}) | costo por XFA ${cost:,.0f} | neto anual por cuenta ${nets.mean():,.0f} (rango entre semillas ${nets.min():,.0f}..${nets.max():,.0f}; p10 ${p10:,.0f}, p90 ${p90:,.0f}; P(<0) {pn:.0%})")
    P("\nTOTAL ANUAL con N cuentas (costos compartidos una sola vez) — media de 3 semillas [min..max]")
    for p in tilts:
        sh = np.mean([r[p]["sh_mes"] for r in runs]); out = []
        for size, n in (("50K", 1), ("50K", 5), ("150K", 1), ("150K", 5)):
            vals = np.array([n * r[p][size]["net"] - SHARED * 12 for r in runs]); out.append(f"{size} x{n} ${vals.mean():,.0f} [{vals.min():,.0f}..{vals.max():,.0f}]")
        P(f"   Sharpe {sh:.2f}: " + " | ".join(out))
    open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dd_cash", "scale_what_it_takes_report.txt"), "w").write("\n".join(lines))
