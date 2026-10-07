"""EXP 1 — Calificacion a medida: plan (Qualification / Momentum) x opcion (1 dinamico / 2 EOD) x producto x hora x geometria, con las reglas verificadas de Bulenox.
Politica: TP al target restante (G=min(R, gfrac*target)), nc segun el tope de contratos/escalado, SL = distancia al umbral (liquidacion) limitada por el DLL. Resultado por intento: pase / quiebre / tiempo (21 dias).
Seleccion en una mitad de los dias y evaluacion en la otra (dos pliegues); la config ganadora tambien se mide en el mundo JUSTO sintetico para separar estructura de suerte. COSTO: fee de compra + reinicios
(Qualification $78; Momentum: sin reinicio documentado -> recompra al precio) + activacion del Master (Qualification $148; Momentum $0) + API de terceros $100/mes (21 dias de trading = 1 mes).
SANDBOX / R&D. Uso: python bulenox/experiments/exp1_qualification.py [size]"""
import os, sys, itertools, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import numpy as np
from bulenox.rules import plan, API_THIRD_PARTY_MONTHLY, ACCESS_TRADING_DAYS
from bulenox import barsim

ENTRIES = {"8:45": 525, "9:15": 555, "9:45": 585, "10:30": 630, "12:30": 750}
TPS = (20, 30, 40, 60, 100, 160)
GF = (0.3, 0.55, 0.75, 1.0)


def cost_to_master(res, pl, api=API_THIRD_PARTY_MONTHLY, reset_override=None, n_seq=20000, seed=1):
    """Costo esperado y dias esperados hasta pasar (tomando intentos i.i.d. de 'res'), con ventana de 21 dias, reinicios y API."""
    rng = np.random.default_rng(seed); m = len(res)
    reset = pl.reset_fee if reset_override is None else reset_override
    fee = pl.price; act = pl.master_activation
    cost = np.zeros(n_seq); days = np.zeros(n_seq); att = np.zeros(n_seq)
    for s in range(n_seq):
        c = fee; t = 0.0; tot = 0.0; a = 0
        for _ in range(300):
            j = rng.integers(0, m); r, d = res[j, 0], res[j, 1]; a += 1
            if t + d > ACCESS_TRADING_DAYS and r != 1:
                c += fee; t = 0.0                           # ventana vencida: recompra
            t += d; tot += d
            if r == 1: break
            c += (reset if reset is not None else fee)
        cost[s] = c + act + api * np.ceil(tot / ACCESS_TRADING_DAYS); days[s] = tot; att[s] = a
    return cost.mean(), days.mean(), att.mean()


def search(size=50_000):
    out = {}
    for pname in ("qualification", "momentum"):
        for opt in (2, 1):
            pl = plan(pname, size, opt); rows = []
            prods = ("MES", "MNQ", "M2K", "MGC")
            for prod in prods:
                ents = dict(ENTRIES)
                if prod == "MGC": ents = {"7:13": 433, "8:15": 495, "9:45": 585}
                for en, em in ents.items():
                    bars = barsim.build_bars(prod, em); n = len(bars["start"]); h1 = np.arange(n // 2); h2 = np.arange(n // 2, n)
                    for tp, gf in itertools.product(TPS, GF):
                        a = (barsim.run_qual(bars, pl, tp, gf, n=2500, seed0=1, idx=h1)[:, 0] == 1).mean()
                        b = (barsim.run_qual(bars, pl, tp, gf, n=2500, seed0=1, idx=h2)[:, 0] == 1).mean()
                        rows.append(dict(prod=prod, entry=en, em=em, tp=tp, gf=gf, h1=a, h2=b))
            out[(pname, opt)] = rows
    return out


if __name__ == "__main__":
    size = int(sys.argv[1]) if len(sys.argv) > 1 else 50_000
    res = search(size); lines = []; rng = np.random.default_rng(9)
    json.dump({f"{k[0]}|{k[1]}": v for k, v in res.items()}, open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "exp1_grid.json"), "w"))
    P = lambda s: (print(s), lines.append(s))
    P(f"EXP 1 — Calificacion {size//1000}K, reglas verificadas de Bulenox; pase por intento (21 dias de acceso), seleccion H1->H2 y H2->H1, config ganadora medida tambien en el mundo justo sintetico")
    for (pname, opt), rows in res.items():
        pl = plan(pname, size, opt)
        b1 = max(rows, key=lambda r: r["h1"]); b2 = max(rows, key=lambda r: r["h2"])
        oos = (b1["h2"] + b2["h1"]) / 2
        top = sorted(rows, key=lambda r: -(r["h1"] + r["h2"]) / 2)[0]
        bars = barsim.build_bars(top["prod"], top["em"])
        full = barsim.run_qual(bars, pl, top["tp"], top["gf"], n=20000, seed0=7)
        syn = np.mean([(barsim.run_qual(barsim.build_bars_synthetic(top["prod"], top["em"], rng), pl, top["tp"], top["gf"], n=1500, seed0=3 + i)[:, 0] == 1).mean() for i in range(10)])
        c, d, a = cost_to_master(full, pl)
        P(f"\n{pname} Opcion {opt} (${pl.price}, DD ${pl.drawdown:,.0f}, DLL {pl.dll}, contratos {pl.contracts} minis): OOS global H1->H2 {b1['h2']:.1%} ({b1['prod']} {b1['entry']} tp={b1['tp']} gf={b1['gf']}) | H2->H1 {b2['h1']:.1%} ({b2['prod']} {b2['entry']} tp={b2['tp']} gf={b2['gf']}) | OOS prom {oos:.1%}")
        P(f"   config consistente en ambas mitades: {top['prod']} {top['entry']} tp={top['tp']} gfrac={top['gf']}: H1 {top['h1']:.1%} / H2 {top['h2']:.1%}; serie completa pase {(full[:,0]==1).mean():.1%} quiebre {(full[:,0]==2).mean():.1%} dias/intento {full[:,1].mean():.1f}; mundo justo sintetico {syn:.1%}")
        P(f"   costo esperado hasta tener la Master ACTIVA (fees + reinicios + activacion + API $100/mes): ${c:,.0f}; dias de trading esperados {d:.1f}; intentos {a:.1f}")
    open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "exp1_qualification_output.txt"), "w").write("\n".join(lines))
