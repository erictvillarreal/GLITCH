"""Parte K, K0: potencia estadística (MDE) de una prueba de exactitud direccional según la fuente de datos. -> resultados_K0_mde.md
    python3 k0_mde.py
Prueba: P(acierto) > 0.5 con n sesiones independientes; MDE = (z_{1−α/2} + z_{potencia}) · 0.5 / √n. MODELADO (fórmula normal; sin ajuste por dependencia serial)."""
import math, os
from statistics import NormalDist
Z = NormalDist().inv_cdf
HERE = os.path.dirname(os.path.abspath(__file__))
def mde_pp(n, alpha, power=0.8): return (Z(1 - alpha / 2) + Z(power)) * 0.5 / math.sqrt(n) * 100
def n_for(delta_pp, alpha, power=0.8): return math.ceil(((Z(1 - alpha / 2) + Z(power)) * 0.5 / (delta_pp / 100)) ** 2)
ALPHAS = (("α = 0.05 (una prueba)", 0.05), ("Holm, m = 26 (E: 16 + K5: 10), la más exigente: α = 0.05/26", 0.05 / 26))
FUENTES = (
    ("Datos locales actuales (Massive Starter, 5 min, 2 años)", 505),
    ("Massive Developer ($79/mes): «5 años» según su página", 1260),
    ("Massive Advanced ($199/mes): «7+ años» según su página (se usa 7)", 1764),
    ("Databento GLBX.MDP3: «16+ años»; con ES/NQ/GC/CL como proxy de los micros (≈ 2010-06 → hoy)", 4030),
    ("Yahoo diario (=F), ES/NQ/GC/CL/6E/ZN desde 2000 (≈ 6,600 días); solo reglas diarias (cierre/apertura)", 6600),
    ("Yahoo diario RTY=F (desde 2017-07) — proxy de M2K", 2344),
)
out = []; P = lambda s="": out.append(s)
P("# resultados_K0_mde — potencia (MDE en puntos de acierto) por fuente\n")
P("**Fuente y estado.** Fórmula normal para una proporción contra 0.5, potencia 80 %, bilateral. n = sesiones independientes (1 trade por día). MODELADO; **no** corrige dependencia serial ni cambios de régimen. Las profundidades de Massive, Databento y Yahoo vienen de sus páginas/consultas del 26-oct-2026 (ver `RESULTADOS_K0.md`); la profundidad **por producto** de Massive y de ProjectX es DESCONOCIDA hasta correr los scripts `k0a`/`k0b`.\n")
P("| fuente | sesiones n | " + " | ".join(f"MDE, {a[0]}" for a in ALPHAS) + " |\n|---|---|" + "---|" * len(ALPHAS))
for nm, n in FUENTES: P(f"| {nm} | {n:,} | " + " | ".join(f"**{mde_pp(n, a[1]):.1f} pp**" for a in ALPHAS) + " |")
P("\n**n necesario para detectar un efecto dado** (potencia 80 %):\n")
P("| efecto a detectar | " + " | ".join(a[0] for a in ALPHAS) + " |\n|---|---|---|")
for d in (4.0, 3.0, 2.0, 1.5, 1.0): P(f"| {d:.1f} pp | " + " | ".join(f"{n_for(d, a[1]):,} sesiones" for a in ALPHAS) + " |")
P("\n**Cuánto vale 1 pp de acierto:** ≈ $1.0k/año por cuenta en la cadena (H1b, pendiente local $1,038/pp). Un efecto que importe en dinero (≥ 1.5 pp) con la corrección de Holm de 26 pruebas pide ≈ 17,000 sesiones: **ningún producto solo lo alcanza**, ni con 26 años de datos diarios.")
P("\n**Agrupar productos NO correlacionados con la misma regla** multiplica n por k_eff = k / (1 + (k − 1)·ρ̄) donde ρ̄ es la correlación media de los resultados diarios de la regla entre productos (se mide en K2; con ρ̄ = 0.17 como MES–MGC, 4 productos dan k_eff = 2.6; con ρ̄ = 0.5, 1.6; con ρ̄ = 0.97 como MES–MNQ, 1.0):\n")
P("| k productos | ρ̄ = 0 | ρ̄ = 0.17 | ρ̄ = 0.5 |\n|---|---|---|---|")
for k in (2, 4, 6, 8): P(f"| {k} | {k:.1f} | {k / (1 + (k - 1) * 0.17):.1f} | {k / (1 + (k - 1) * 0.5):.1f} |")
P("\nEjemplo: 6 productos con ρ̄ = 0.17 y 16 años de datos intradía (Databento) ⇒ n efectivo ≈ 4,030 × 3.2 ≈ 12,900 ⇒ MDE Holm-26 ≈ " + f"{mde_pp(4030 * 6 / (1 + 5 * 0.17), 0.05 / 26):.1f} pp; con 2 años de datos locales (n ≈ 505 × 3.2) ⇒ {mde_pp(505 * 6 / (1 + 5 * 0.17), 0.05 / 26):.1f} pp.")
open(os.path.join(HERE, "resultados_K0_mde.md"), "w", encoding="utf-8").write("\n".join(out) + "\n"); print("\n".join(out))
