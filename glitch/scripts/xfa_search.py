"""Busqueda de estructuras para maximizar el payout por cuenta fondeada (XFA / equivalente), con validacion FUERA DE MUESTRA en dos pliegues:
pliegue 1 = seleccionar con la 1a mitad de los dias y evaluar en la 2a; pliegue 2 = al reves. Espacio: producto x hora de entrada (CT) x geometria (G bruto del bracket, rho = stop como
fraccion de la distancia al piso, TP como fraccion q del rango diario mediano). SANDBOX / R&D, offline. Uso: python scripts/xfa_search.py "Topstep XFA 50K" """
import os, sys, itertools, time, csv, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
from scripts.tables_generic import build, median_range_ticks, SPEC
from dd_cash.xfa_lab import run_life

ENTRIES = {"8:45": 525, "9:15": 555, "9:45": 585, "10:30": 630, "11:30": 690, "12:30": 750, "13:15": 795}
EARLY_MGC = {"7:13": 433, "7:45": 465, "8:15": 495}
GS = (150, 250, 400, 600, 900, 1300)
RHOS = (0.2, 0.35, 0.5, 0.75, 1.0)
QS = (0.1, 0.2, 0.35, 0.5)
N = 3000; H = 126
SLIP = float(os.environ.get('XFA_SLIP', '0.5'))   # llenado del stop: 0 = exacto (optimista), 1 = extremo de la barra (pesimista)


def combos(prod):
    ents = dict(ENTRIES); 
    if prod == "MGC": ents.update(EARLY_MGC)
    for en, em in ents.items():
        yield en, em


def search(firm, products=("MES", "MNQ", "M2K", "MGC", "MCL", "M6E"), sides=("alternate",), comm_map=None):
    rows = []
    t0 = time.time()
    for prod in products:
        for en, em in combos(prod):
            for side in sides:
                tab = build(prod, em, side_mode=side)
                n = len(tab["adv"]); h1 = np.arange(n // 2); h2 = np.arange(n // 2, n)
                R = median_range_ticks(prod, em)
                for g, rho, q in itertools.product(GS, RHOS, QS):
                    tp = max(1, int(round(q * R)))
                    cm = None if comm_map is None else comm_map[prod]
                    a = run_life(tab, firm, g, rho, tp, H=H, n=N, seed0=1000, idx=h1, comm=cm, slip=SLIP)       # seleccion en H1
                    b = run_life(tab, firm, g, rho, tp, H=H, n=N, seed0=1000, idx=h2, comm=cm, slip=SLIP)       # seleccion en H2
                    rows.append(dict(prod=prod, entry=en, side=side, g=g, rho=rho, q=q, tp=tp, h1=a["payout"], h2=b["payout"], p1_h1=a["p1"], p1_h2=b["p1"],
                                     life_h1=a["life"], life_h2=b["life"]))
        print(f"  {prod} listo ({time.time()-t0:.0f}s)", flush=True)
    return rows


def oos_report(rows, label, pred=lambda r: True):
    sub = [r for r in rows if pred(r)]
    out = []
    # global: elegir en H1 -> evaluar en H2, y al reves
    b1 = max(sub, key=lambda r: r["h1"]); b2 = max(sub, key=lambda r: r["h2"])
    out.append(f"{label}\n  global: mejor en H1 = {b1['prod']} {b1['entry']} G={b1['g']} rho={b1['rho']} q={b1['q']} (H1 ${b1['h1']:,.0f} -> OOS H2 ${b1['h2']:,.0f}) | mejor en H2 = {b2['prod']} {b2['entry']} G={b2['g']} rho={b2['rho']} q={b2['q']} (H2 ${b2['h2']:,.0f} -> OOS H1 ${b2['h1']:,.0f}) | OOS promedio ${(b1['h2']+b2['h1'])/2:,.0f}")
    # por producto
    for prod in sorted({r["prod"] for r in sub}):
        s = [r for r in sub if r["prod"] == prod]
        p1 = max(s, key=lambda r: r["h1"]); p2 = max(s, key=lambda r: r["h2"])
        out.append(f"  {prod}: mejor H1 -> OOS H2 ${p1['h2']:,.0f} ({p1['entry']} G={p1['g']} rho={p1['rho']} q={p1['q']}) | mejor H2 -> OOS H1 ${p2['h1']:,.0f} ({p2['entry']} G={p2['g']} rho={p2['rho']} q={p2['q']}) | OOS prom ${(p1['h2']+p2['h1'])/2:,.0f}")
    # robustez: promedio del grid, y top-k por promedio de ambas mitades
    avg = sorted(sub, key=lambda r: -(r["h1"] + r["h2"]) / 2)
    out.append("  top-8 por promedio de H1 y H2 (estructuras consistentes en ambas mitades):")
    for r in avg[:8]:
        out.append(f"     {r['prod']} {r['entry']} G={r['g']} rho={r['rho']} q={r['q']} tp={r['tp']}: H1 ${r['h1']:,.0f} / H2 ${r['h2']:,.0f}  P(>=1 pago) {r['p1_h1']:.0%}/{r['p1_h2']:.0%}  vida {r['life_h1']:.0f}/{r['life_h2']:.0f} dias")
    out.append(f"  mediana del grid: H1 ${np.median([r['h1'] for r in sub]):,.0f} / H2 ${np.median([r['h2'] for r in sub]):,.0f}; correlacion H1-H2 del payout entre estructuras: {np.corrcoef([r['h1'] for r in sub],[r['h2'] for r in sub])[0,1]:.2f}")
    return "\n".join(out)


if __name__ == "__main__":
    firm = sys.argv[1] if len(sys.argv) > 1 else "Topstep XFA 50K"
    # comisiones round-turn por fuente propia: Tradeify (Pricing Reference): MES/MNQ $1.82; Bulenox (Bulenox-Rates.pdf): MES/MNQ/M2K 1.22, MGC/MCL 1.52, M6E 1.00
    if firm.startswith("Tradeify"):
        prods = ("MES", "MNQ"); cmap = {"MES": 1.82, "MNQ": 1.82}
    elif firm.startswith("Bulenox"):
        prods = ("MES", "MNQ", "M2K", "MGC", "MCL", "M6E"); cmap = {"MES": 1.22, "MNQ": 1.22, "M2K": 1.22, "MGC": 1.52, "MCL": 1.52, "M6E": 1.00}
    else:
        prods = ("MES", "MNQ", "M2K", "MGC", "MCL", "M6E"); cmap = None
    rows = search(firm, products=prods, comm_map=cmap)
    slug = firm.replace(" ", "_") + f"_slip{SLIP:g}"
    with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dd_cash", f"xfa_search_{slug}.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    txt = [f"BUSQUEDA XFA — {firm} — slip del stop={SLIP:g} — payout esperado por cuenta (al trader, 90%), vida hasta {H} dias, {N} trayectorias por celda"]
    txt.append(oos_report(rows, "SIN RESTRICCIONES DE CONDUCTA"))
    txt.append(oos_report(rows, "CONDUCTA-COMPATIBLE (rho<=0.5 y G<=400)", lambda r: r["rho"] <= 0.5 and r["g"] <= 400))
    s = "\n\n".join(txt)
    print(s)
    open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dd_cash", f"xfa_search_{slug}.txt"), "w").write(s)
