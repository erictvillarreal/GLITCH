"""EXP 2 — Etapa fondeada a medida (Master / Momentum Master / Fast Track, 50K, Opcion 2) con las reglas de pago verificadas de Bulenox: payout esperado por cuenta (neto al trader, con el 100% de los
primeros $10,000), P(>=1 pago) y vida, por producto x hora x geometria (G bruto del bracket, rho = stop como fraccion de la distancia al umbral, TP = q x rango diario mediano).
Llenado del stop con slip=0.5 (mitad del sobrepaso de la barra) y orden de barra conservador; seleccion en una mitad -> evaluacion en la otra; la config consistente tambien se mide en el mundo justo sintetico.
SANDBOX / R&D. Uso: python bulenox/experiments/exp2_funded.py"""
import os, sys, itertools, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import numpy as np
from bulenox.rules import plan
from bulenox import barsim
from scripts.tables_generic import median_range_ticks

SLIP = 0.5
COMBOS = [("MES", "8:45", 525), ("MES", "9:45", 585), ("MES", "12:30", 750), ("MNQ", "8:45", 525), ("MNQ", "12:30", 750), ("MGC", "7:13", 433), ("MGC", "8:15", 495), ("MGC", "9:45", 585), ("M2K", "9:15", 555)]
GS = (150, 250, 400, 600, 900, 1300); RHOS = (0.2, 0.35, 0.5, 0.75, 1.0); QS = (0.2, 0.35, 0.5)
STAGES = {"master": ("Master (Qualification Opc.2, 10 dias, 40%, reserva $2,600)", plan("qualification", 50_000, 2)),
          "momentum_master": ("Momentum Master (5 dias rentables, 35%, saldo $53,000)", plan("momentum", 50_000, 2)),
          "fast_track": ("Fast Track (objetivo $3,000, consistencia 20/25/30%)", plan("fast_track", 50_000, 2))}


def search():
    out = {s: [] for s in STAGES}
    for prod, en, em in COMBOS:
        bars = barsim.build_bars(prod, em); n = len(bars["start"]); h1 = np.arange(n // 2); h2 = np.arange(n // 2, n); R = median_range_ticks(prod, em)
        for g, rho, q in itertools.product(GS, RHOS, QS):
            tp = max(1, int(round(q * R)))
            for st, (_, pl) in STAGES.items():
                a = barsim.run_funded(bars, st, pl, g, rho, tp, n=1200, seed0=1, idx=h1, slip=SLIP)
                b = barsim.run_funded(bars, st, pl, g, rho, tp, n=1200, seed0=1, idx=h2, slip=SLIP)
                out[st].append(dict(prod=prod, entry=en, em=em, g=g, rho=rho, q=q, tp=tp, h1=a["payout"], h2=b["payout"], p1_h1=a["p1"], p1_h2=b["p1"], life_h1=a["life"], life_h2=b["life"]))
        print(f"  {prod} {en} listo", flush=True)
    return out


if __name__ == "__main__":
    res = search(); lines = []; rng = np.random.default_rng(4)
    json.dump(res, open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "exp2_grid.json"), "w"))
    P = lambda s: (print(s), lines.append(s))
    P(f"EXP 2 — Etapa fondeada 50K (Opcion 2), slip del stop={SLIP}, orden de barra conservador; payout esperado por cuenta al trader; seleccion H1->H2 y H2->H1")
    for st, rows in res.items():
        label, pl = STAGES[st]
        b1 = max(rows, key=lambda r: r["h1"]); b2 = max(rows, key=lambda r: r["h2"])
        top = sorted(rows, key=lambda r: -min(r["h1"], r["h2"]))[:6]
        P(f"\n{label}\n  global: mejor en H1 = {b1['prod']} {b1['entry']} G={b1['g']} rho={b1['rho']} tp={b1['tp']} (H1 ${b1['h1']:,.0f} -> OOS H2 ${b1['h2']:,.0f}) | mejor en H2 = {b2['prod']} {b2['entry']} G={b2['g']} rho={b2['rho']} tp={b2['tp']} (H2 ${b2['h2']:,.0f} -> OOS H1 ${b2['h1']:,.0f}) | OOS prom ${(b1['h2']+b2['h1'])/2:,.0f}")
        P(f"  mediana del grid: H1 ${np.median([r['h1'] for r in rows]):,.0f} / H2 ${np.median([r['h2'] for r in rows]):,.0f}")
        P("  top-6 por el MINIMO de H1 y H2 (consistentes en ambas mitades) y su payout en el mundo justo sintetico:")
        for r in top:
            syn = np.mean([barsim.run_funded(barsim.build_bars_synthetic(r["prod"], r["em"], rng), st, pl, r["g"], r["rho"], r["tp"], n=600, seed0=3 + i, slip=SLIP)["payout"] for i in range(8)])
            P(f"     {r['prod']} {r['entry']} G={r['g']} rho={r['rho']} q={r['q']} tp={r['tp']}: H1 ${r['h1']:,.0f} / H2 ${r['h2']:,.0f}  P(>=1) {r['p1_h1']:.0%}/{r['p1_h2']:.0%}  vida {r['life_h1']:.0f}/{r['life_h2']:.0f} dias | mundo justo ${syn:,.0f}")
    open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "exp2_funded_output.txt"), "w").write("\n".join(lines))
