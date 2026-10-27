# resultados_K0_mde — potencia (MDE en puntos de acierto) por fuente

**Fuente y estado.** Fórmula normal para una proporción contra 0.5, potencia 80 %, bilateral. n = sesiones independientes (1 trade por día). MODELADO; **no** corrige dependencia serial ni cambios de régimen. Las profundidades de Massive, Databento y Yahoo vienen de sus páginas/consultas del 26-oct-2026 (ver `RESULTADOS_K0.md`); la profundidad **por producto** de Massive y de ProjectX es DESCONOCIDA hasta correr los scripts `k0a`/`k0b`.

| fuente | sesiones n | MDE, α = 0.05 (una prueba) | MDE, Holm, m = 26 (E: 16 + K5: 10), la más exigente: α = 0.05/26 |
|---|---|---|---|
| Datos locales actuales (Massive Starter, 5 min, 2 años) | 505 | **6.2 pp** | **8.8 pp** |
| Massive Developer ($79/mes): «5 años» según su página | 1,260 | **3.9 pp** | **5.6 pp** |
| Massive Advanced ($199/mes): «7+ años» según su página (se usa 7) | 1,764 | **3.3 pp** | **4.7 pp** |
| Databento GLBX.MDP3: «16+ años»; con ES/NQ/GC/CL como proxy de los micros (≈ 2010-06 → hoy) | 4,030 | **2.2 pp** | **3.1 pp** |
| Yahoo diario (=F), ES/NQ/GC/CL/6E/ZN desde 2000 (≈ 6,600 días); solo reglas diarias (cierre/apertura) | 6,600 | **1.7 pp** | **2.4 pp** |
| Yahoo diario RTY=F (desde 2017-07) — proxy de M2K | 2,344 | **2.9 pp** | **4.1 pp** |

**n necesario para detectar un efecto dado** (potencia 80 %):

| efecto a detectar | α = 0.05 (una prueba) | Holm, m = 26 (E: 16 + K5: 10), la más exigente: α = 0.05/26 |
|---|---|---|
| 4.0 pp | 1,227 sesiones | 2,430 sesiones |
| 3.0 pp | 2,181 sesiones | 4,320 sesiones |
| 2.0 pp | 4,906 sesiones | 9,720 sesiones |
| 1.5 pp | 8,721 sesiones | 17,279 sesiones |
| 1.0 pp | 19,623 sesiones | 38,878 sesiones |

**Cuánto vale 1 pp de acierto:** ≈ $1.0k/año por cuenta en la cadena (H1b, pendiente local $1,038/pp). Un efecto que importe en dinero (≥ 1.5 pp) con la corrección de Holm de 26 pruebas pide ≈ 17,000 sesiones: **ningún producto solo lo alcanza**, ni con 26 años de datos diarios.

**Agrupar productos NO correlacionados con la misma regla** multiplica n por k_eff = k / (1 + (k − 1)·ρ̄) donde ρ̄ es la correlación media de los resultados diarios de la regla entre productos (se mide en K2; con ρ̄ = 0.17 como MES–MGC, 4 productos dan k_eff = 2.6; con ρ̄ = 0.5, 1.6; con ρ̄ = 0.97 como MES–MNQ, 1.0):

| k productos | ρ̄ = 0 | ρ̄ = 0.17 | ρ̄ = 0.5 |
|---|---|---|---|
| 2 | 2.0 | 1.7 | 1.3 |
| 4 | 4.0 | 2.6 | 1.6 |
| 6 | 6.0 | 3.2 | 1.7 |
| 8 | 8.0 | 3.7 | 1.8 |

Ejemplo: 6 productos con ρ̄ = 0.17 y 16 años de datos intradía (Databento) ⇒ n efectivo ≈ 4,030 × 3.2 ≈ 12,900 ⇒ MDE Holm-26 ≈ 1.7 pp; con 2 años de datos locales (n ≈ 505 × 3.2) ⇒ 4.9 pp.
