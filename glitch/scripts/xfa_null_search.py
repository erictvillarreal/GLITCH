"""Busqueda de geometria para la etapa fondeada OPTIMIZANDO EN UN MUNDO SIN DIRECCION: para cada producto x hora, los signos de cada dia se aleatorizan (permutaciones) preservando la estructura
intradia real (rangos, volatilidad, costos); el payout esperado por XFA se promedia sobre las permutaciones. Una estructura buena aqui no depende de la suerte direccional de la muestra
(prueba de permutacion de scripts/cerebro2_xfa_geometry.py: el 'mejor TP=SL=200' observado no sobrevive a esta prueba). Luego se reporta el payout sobre la serie real (alternar) como UNA realizacion.
SANDBOX / R&D, offline. Uso: python scripts/xfa_null_search.py "Topstep XFA 50K" [n_perm]"""
import os, sys, itertools, time, csv
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
from scripts.tables_generic import build, median_range_ticks
from scripts.xfa_search import ENTRIES, EARLY_MGC
from dd_cash.xfa_lab import run_life

GS = (150, 250, 400, 600, 900, 1300)
RHOS = (0.2, 0.35, 0.5, 0.75, 1.0)
QS = (0.2, 0.35, 0.5)


def mix(L, S, sg):
    t = dict(L); sel = sg[:, None]
    t["adv"] = np.where(sel, L["adv"], S["adv"]); t["tpt"] = np.where(sel, L["tpt"], S["tpt"]); t["flat"] = np.where(sg, L["flat"], S["flat"]); return t


if __name__ == "__main__":
    firm = sys.argv[1] if len(sys.argv) > 1 else "Topstep XFA 50K"
    NP = int(sys.argv[2]) if len(sys.argv) > 2 else 20
    if firm.startswith("Tradeify"):
        prods = ("MES", "MNQ"); cmap = {"MES": 1.82, "MNQ": 1.82}
    elif firm.startswith("Bulenox"):
        prods = ("MES", "MNQ", "M2K", "MGC", "MCL", "M6E"); cmap = {"MES": 1.22, "MNQ": 1.22, "M2K": 1.22, "MGC": 1.52, "MCL": 1.52, "M6E": 1.00}
    else:
        prods = ("MES", "MNQ", "M2K", "MGC", "MCL", "M6E"); cmap = None
    slug = firm.replace(" ", "_")
    out = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dd_cash", f"xfa_null_{slug}.csv")
    rng = np.random.default_rng(5); rows = []; t0 = time.time()
    for prod in prods:
        ents = dict(ENTRIES)
        if prod == "MGC": ents.update(EARLY_MGC)
        for en, em in ents.items():
            L = build(prod, em, side_mode="always_long"); S = build(prod, em, side_mode="always_short"); A = build(prod, em)
            n = len(L["adv"]); R = median_range_ticks(prod, em)
            perms = [mix(L, S, rng.random(n) < 0.5) for _ in range(NP)]
            for g, rho, q in itertools.product(GS, RHOS, QS):
                tp = max(1, int(round(q * R)))
                cm = None if cmap is None else cmap[prod]
                pays = [run_life(t, firm, g, rho, tp, H=126, n=700, seed0=11 + i, comm=cm) for i, t in enumerate(perms)]
                obs = run_life(A, firm, g, rho, tp, H=126, n=3000, seed0=3, comm=cm)
                rows.append(dict(prod=prod, entry=en, g=g, rho=rho, q=q, tp=tp, null_mean=np.mean([p["payout"] for p in pays]), null_sd=np.std([p["payout"] for p in pays]),
                                 null_p1=np.mean([p["p1"] for p in pays]), null_life=np.mean([p["life"] for p in pays]), obs=obs["payout"], obs_p1=obs["p1"]))
        print(f"{prod} listo {time.time()-t0:.0f}s", flush=True)
        with open(out, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
