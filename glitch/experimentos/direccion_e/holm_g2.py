"""Consolida las 18 comparaciones declaradas: Holm sobre p vs 51 % y evaluacion de G2(1)-(3) -> RESULTADOS_E_G2.md.   python holm_g2.py"""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from common_e import holm
G = {}
for f in ("e1", "e2", "e4", "e5"): G.update(json.load(open(os.path.join(HERE, f"{f}_g2.json"))))
M = 18
p = {k: v["p51"] for k, v in G.items()}
H = holm(p, M)
out = []; P = lambda s="": (print(s), out.append(s))
P("# RESULTADOS_E_G2 — compuerta G2 sobre las 18 comparaciones declaradas\n")
P(f"Calculadas: {len(G)}; no calculadas (E3 omitida: 2) y las que falten para llegar a {M} cuentan con p = 1 en Holm (criterio conservador). Holm sobre H0: exactitud ≤ 51 % (bloques de 5 días, 10,000 remuestras, semilla 20261021).\n")
P("| prueba | exactitud | p sin ajustar | p Holm | G2(1) Holm < 0.05 | G2(2) bloques > alternate / > LARGO (≥ 7/10 en ambos) | G2(3) últimas 3 ventanas anuales > 50 % | pasa G2 |\n|---|---|---|---|---|---|---|---|")
passed = []
for k in sorted(G, key=lambda k: p[k]):
    v = G[k]; adj, rej = H[k]
    g2 = v["wins_alt"] >= 7 and v["wins_long"] >= 7 and not k.startswith("E4")
    if "last3" in v: g3 = "sí" if all(a > 0.5 for a in v["last3"].values()) else "no"
    elif "years" in v: g3 = "no evaluable (2 años)"
    else: g3 = "—"
    g2txt = f"{v['wins_alt']}/10 · {v['wins_long']}/10" if not k.startswith("E4") else f"{v['wins_alt']}/10 · LARGO ≡ la regla (empate por construcción)"
    ok = rej and g2 and g3 == "sí"
    if ok: passed.append(k)
    P(f"| {k} | {v['acc'] * 100:.1f} % | {v['p51']:.4f} | {adj:.3f} | {'sí' if rej else 'no'} | {g2txt} | {g3} | {'**SÍ**' if ok else 'no'} |")
P(f"\n**Pruebas que pasan G2(1): {sum(1 for k in G if H[k][1])} de {len(G)}; que pasan G2 completa: {len(passed)}.** " + ("Ninguna." if not passed else ", ".join(passed)))
open(os.path.join(HERE, "RESULTADOS_E_G2.md"), "w").write("\n".join(out))
