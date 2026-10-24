# resultados_G3 — comparación de productos (ventana real de cada producto; 2 años de 5 min; contrato dominante por día)

Costos: round-turn **todo incluido** (comisión + exchange + regulatorio) por contrato, del artículo de comisiones y tarifas del Help Center de Topstep (consultado el 24-oct-2026; sin fecha de vigencia en la página). Hay un aviso de que CME sube cuotas desde el 1-oct-2026 y para MCL la tabla y el aviso no son consistentes entre sí (NO VERIFICADO cuál es el valor vigente; se usa $1.72). **MYM:** el artículo lo lista a $1.22 pero no hay datos de 5 min locales → sin filas de rango/liquidez. Topes de contratos del Combine 50K: de `geometry_pure.SPECS` (leídos del Help Center el 25-ago-2026; **MNQ y MYM no están en esa tabla: NO VERIFICADO**). Topes del XFA: MGC restringido a 12/18/31 micros según saldo (`RULEBOOK_XFA.md`).

| producto | días | rango mediano de la ventana (ticks) | rango mediano $/contrato | round-turn $ | costo % del rango | volumen mediano por barra de 5 min en la hora de entrada (contratos) | 40 contratos como % de esa barra | tope Combine 50K (micros) |
|---|---|---|---|---|---|---|---|---|
| MES | 496 | 172 | $216 | $1.22 | 0.566 % | 13,817 | 0.3 % | 50 |
| MNQ | 487 | 866 | $433 | $1.22 | 0.282 % | 20,988 | 0.2 % | NO VERIFICADO |
| M2K | 496 | 246 | $123 | $1.22 | 0.990 % | 909 | 4.4 % | 50 |
| MGC | 503 | 420 | $420 | $1.92 | 0.457 % | 1,102 | 3.6 % | 30 |
| MCL | 488 | 109 | $109 | $1.72 | 1.571 % | 559 | 7.2 % | 30 |

Lectura: el round-turn es **0.3–1.6 % del rango de la ventana** (MNQ el más barato en proporción, MCL el más caro): importa poco frente al tamaño de las barreras (en MES, 40 contratos pagan $48.80 de comisión contra un TP de $1,600, 3 %). **La diferencia real entre productos es la liquidez a la hora de entrada**: 40 contratos son 0.2–0.3 % de una barra de 5 min en MES/MNQ, pero 3.6–7.2 % en MGC, M2K y MCL (barras de ≈ 560–1,100 contratos): ahí el slippage sistemático de tamaño grande **sí** puede ser mayor que en MES (inferencia, sin medir). Un segundo producto vale sobre todo por la **correlación** con el primero (G4), no por costo. Geometría validada en este repo: solo MES (Combine) y MGC (XFA); en la consolidación de Camino B (GLITCH_RESEARCH_LOG) M2K quedó casi empatado (≈ 1.4 %); MNQ/MYM/MCL no tienen geometría validada. Los rangos son de 2 años de 5 min; **no hay fills de ningún otro producto**.