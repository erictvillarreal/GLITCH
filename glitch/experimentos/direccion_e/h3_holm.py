"""Parte H, H3: consolida P1-P7 con Holm (m = 7) y ensambla resultados_H3.md.   python h3_holm.py"""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from common_e import holm
pv = {}
for f in ("stats", "hour", "dinero"): pv.update(json.load(open(os.path.join(HERE, f"h3_pvals_{f}.json"), encoding="utf-8")))
H = holm(pv, 7)
parts = [open(os.path.join(HERE, f"resultados_H3_{f}.md"), encoding="utf-8").read() for f in ("stats", "hour", "dinero")]
out = [parts[0], parts[1].split("\n", 2)[-1] if parts[1].startswith("# resultados_H3") else parts[1], "\n" + parts[2].replace("# resultados_H3 (dinero) — P7 y prueba 8\n", "## Dinero: P7 y prueba 8\n")]
tab = ["\n## Holm sobre las 7 pruebas estadísticas (α = 0.05)\n", "| prueba | p sin ajustar | p Holm (m = 7) | ¿rechaza H₀? |", "|---|---|---|---|"]
for k in sorted(pv, key=lambda k: pv[k]): tab.append(f"| {k} | {pv[k]:.4f} | {H[k][0]:.3f} | {'**sí**' if H[k][1] else 'no'} |")
tab += ["", "**Lectura.** Solo **P1 (VIX mejora el pronóstico del rango de índices, ΔR² = +1.7 pp)** sobrevive a Holm. GVZ no mejora el del oro (+0.3 pp, p = 0.25), el día de la semana no aporta (≈ 0), la hora de entrada no cambia P(pasar) de forma distinguible (10:30: +1.4 pp, IC [−0.3, +3.3]; 12:30: −0.1 pp) y el tamaño por volatilidad en la XFA (p = 0.07) no es significativo. En la prueba de dinero (WR 47.4 / 48.5 / 50 / 52 %): **filtro** −$558 a WR 50 y −$1,377 a 52 % (solo +$172 a 47.4 %, dentro del ruido); **ATR** −$130 / −$49 / +$182 / +$268; **tamaño** −$116 / +$6 / +$328 / +$790. **Ningún uso del pronóstico supera +$500/año/cuenta en el escenario central (WR 50 %); el tamaño por volatilidad solo lo supera si existiera un WR ≥ 52 %** (donde cualquier palanca se amplifica porque la ventaja ya existe). Objetivo declarado (subir la fracción decidida sin subir el equilibrio): el filtro la sube +44 pp pero **sube el costo por saltar días y baja P(≥1 pago)**; ATR/tamaño la mantienen ≈ constante.",
        "", "**Estacionalidad intradía (descriptiva):** ver `resultados_H2.md` §2 (patrón en U de rango y volumen; proxy de costo; 40 contratos = 0.2–0.7 % de la barra en MES)."]
open(os.path.join(HERE, "resultados_H3.md"), "w", encoding="utf-8").write("\n".join(out + tab))
print("\n".join(tab))
