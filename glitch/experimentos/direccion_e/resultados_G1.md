# resultados_G1 — ejecución: valor del tick, anclaje al fill y estilos de entrada (MES Combine nc 40; XFA 3×364 sin ventaja; Combine P0 con finish-line P3 donde se indica)

Bancos de 100000, 40000 trayectorias, semillas fijas. Sin ventaja direccional. **El nivel del neto anual tiene ruido de simulación de ±$100** (ver F1); las diferencias pareadas entre filas usan los mismos números aleatorios y son más estables (±$20–40).

## G1e. Curva del slippage de entrada (0–4 ticks adversos, fijo en cada fila)

M1 = el precio se movió antes del fill (ruido); M2 = costo de ejecución puro (ver `resultados_F3_slippage.md`). Hoy: TP/SL anclados a la **referencia**.

| slip | M1 P(pasar) | M1 días a resolver | M1 neto $/año | M1 con finish-line P3 | M2 P(pasar) | M2 días | M2 neto $/año | M2 con P3 |
|---|---|---|---|---|---|---|---|---|
| 0 | 29.9 % | 1.6 | $2,867 | $2,868 | 29.9 % | 1.6 | $2,867 | $2,868 |
| 1 | 31.3 % | 1.6 | $3,027 | $3,029 | 29.0 % | 1.5 | $2,760 | $2,762 |
| 2 | 21.0 % | 1.9 | $1,352 | $2,659 | 18.0 % | 1.8 | $805 | $2,246 |
| 3 | 21.1 % | 1.9 | $1,356 | $2,591 | 17.2 % | 1.8 | $653 | $2,008 |
| 4 | 21.3 % | 1.9 | $1,383 | $2,464 | 16.1 % | 1.8 | $445 | $1,657 |

**Valor de 1 tick de slippage sistemático (entre 1 y 3 ticks, por tick):** M1: P(pasar) -5.1 pp, neto -836 $/año/cuenta · M2: P(pasar) -5.9 pp, neto -1,054 $/año/cuenta. Entre 0 y 4: M2 -605 $/año/cuenta por tick.

## G1c. Anclar TP/SL a la referencia (hoy) vs al fill

(ii) y (iii) producen la misma geometría: TP a +32 y SL a −100 ticks **del fill** (en (ii) el Pi confirma el fill y entonces envía TP/SL; en (iii) la API los pone como brackets nativos). Bajo **M1** el fill es el origen del camino ⇒ equivale a slip 0 de la tabla anterior (el slippage por movimiento de precio deja de importar). Bajo **M2** el camino real no cambia, el TP queda a 32 + s ticks de la referencia y paga 32 ticks.

| s | (i) hoy M1 | (i) hoy M2 | (ii)/(iii) M1 = slip 0 | (ii)/(iii) M2: P(pasar) / neto |
|---|---|---|---|---|
| 1 | 31.3 % / $3,027 | 29.0 % / $2,760 | 29.9 % / $2,867 | 27.9 % / $2,614 |
| 2 | 21.0 % / $1,352 | 18.0 % / $805 | 29.9 % / $2,867 | 26.9 % / $2,464 |
| 3 | 21.1 % / $1,356 | 17.2 % / $653 | 29.9 % / $2,867 | 25.5 % / $2,272 |

**Con finish-line (P3) ya adoptado** el acantilado ya está mitigado, así que anclar al fill vale menos:

| s | (i) hoy M1 / M2 (P3) | (ii)/(iii) M1 (P3) | (ii)/(iii) M2 (P3) |
|---|---|---|---|
| 1 | $3,029 / $2,762 | $2,868 | $2,615 |
| 2 | $2,659 / $2,246 | $2,868 | $2,465 |
| 3 | $2,591 / $2,008 | $2,868 | $2,275 |

Lectura: anclar al fill elimina el acantilado 2→3 TP (cada TP paga 32 ticks sin importar el slippage). No elimina el costo sistemático (bajo M2 el neto sigue cayendo con s, porque el camino real no se mueve a tu favor), pero evita que ese costo además cambie la forma del pago.

## G1d. Estilos de entrada (supuestos explícitos; NO hay distribución medida de slippage, N = 2)

**Supuesto, no medido:** el slippage por día es `s = 0.5 (sistemático, medio spread) + ruido`, con ruido normal de σ ∈ {1, 2} ticks, redondeado al tick. Solo sirve para comparar *políticas*; los niveles dependen del supuesto.

| σ del ruido | política | % de días sin entrar | P(pasar) por intento | neto $/año (días ajustados por 1/(1−f)) |
|---|---|---|---|---|
| 1 | mercado (hoy) | 0 % | 28.2 % | $2,619 |
| 1 | límite marketable, tope 1 tick | 15 % | 29.7 % | $2,843 |
| 1 | límite marketable, tope 2 ticks | 2 % | 28.5 % | $2,663 |
| 2 | mercado (hoy) | -0 % | 26.3 % | $2,335 |
| 2 | límite marketable, tope 1 tick | 31 % | 30.2 % | $2,564 |
| 2 | límite marketable, tope 2 ticks | 16 % | 28.7 % | $2,679 |

**(a) Partir las 40 en bloques:** el libro de MES tiene miles de contratos al inicio de la sesión; 40 micros no mueven el precio de forma medible (impacto ≈ 0 respecto del medio spread, **supuesto sin medir**), y partirlos añade latencia (el precio se mueve mientras se envían los bloques) y TP/SL por bloque. **No recomendado.**
**(c) Polling de 5–10 s en 9:34–9:40 CT:** acorta la espera del Pi de U(0, 120 s) (media 60 s) a ≈ 3–5 s. **No cambia el slippage** (la orden de mercado y la referencia se toman cuando el Pi actúa, no cuando Railway escribe), sí acerca la entrada a 9:35:00 (fidelidad con el paper, que entra ≈ 9:40) y acorta la ventana del plan B. Costo: ≈ 72 lecturas del Gist en la ventana de 6 min (cuota REST de GitHub autenticada: 5,000 por hora, hecho conocido; NO verificado en esta sesión). Complejidad baja. **Efecto en dólares: no medible (la Parte A no encontró efecto de la hora de entrada); se justifica por fiabilidad, no por costo.**