# J3 — Geometría para la XFA: 3×364, 728×3, 4→1 micros, 1 micro la primera semana

Lunes 26-oct-2026 · BORRADOR. Las cifras salen de `resultados_J8.md` (tabla B; script `j8_primer_dia_xfa.py`); aquí se reordenan como pide J3. **MODELADO** sobre 443 días reales de MGC (sin la ventana de oro), motor `xfa_engine`, 60,000 vidas por celda, IC95 = 40 remuestras de bloques de 5 días, diferencias pareadas. Slippage de entrada de MGC = distribución empírica de **8 observaciones de MES** {−1: 1/8, 0: 3/8, +1: 2/8, +3: 2/8} (media 0.875 ≈ 0.9; **la 8.ª observación la inferí como 0 a partir de «media 0.9, N=8»: NO VERIFICADA**; MGC no tiene ninguna observación propia). OPS base **$245/año** (prorrateado por días de vida en «neto tras OPS»). Primer día = miércoles 28-oct = LARGO. «Cobrado» = pagos netos al trader (90/10, tope $2,000 por pago), **sin** restar la activación de $149.

| geometría | cobrado esperado por XFA [IC95] — WR 47.4 % | — WR 50 % | P(≥ 1 pago) 47.4 / 50 % | P(muerte en 3 días) 47.4 / 50 % | mediana de días al 1.er pago | neto tras OPS $245 (47.4 / 50 %) |
|---|---|---|---|---|---|---|
| **3×364** (producción) | $384 [362, 437] | $618 [592, 698] | 25.0 / 32.2 % | 20.8 / 18.4 % | 8 | $376 / $609 |
| **3×728** | $450 [405, 502] | $798 [730, 869] | 21.3 / 28.0 % | 33.4 / 30.7 % | 9 / 8 | $442 / $788 |
| **4→1 micros** (4 hasta saldo $1,500, luego 1) | $473 [443, 540] | $715 [671, 770] | 25.2 / 32.1 % | 38.3 / 34.8 % | 10 | $464 / $704 |
| **1 micro toda la vida** | $215 [196, 246] | $356 [343, 384] | 49.0 / 63.6 % | 0.0 / 0.0 % | 15 / 14 | $191 / $331 |
| **1 micro la 1.ª semana, luego 3** | $372 [354, 426] | $582 [561, 646] | 31.5 / 40.2 % | 0.0 / 0.0 % | 10 | $360 / $570 |

**Costo de la semana de 1 micro** (frente a 3×364 desde el día 1): **−$13 [−31, +13]** por XFA a WR 47.4 % (**no distinguible de 0**) y **−$36 [−56, −1]** a WR 50 % (distinguible, pequeño: ≈ 6 % del cobrado); además el 1.er pago llega ≈ 2 días después (mediana 10 vs 8) y la vida media sube de 9.7 a 12.8 días. A cambio la probabilidad de morir en los primeros 3 días baja de ≈ 18–21 % a 0 (con 1 micro un solo stop cuesta $364, y la cuenta tiene $2,000 de colchón). La semana de 1 micro **sube** P(≥ 1 pago) de 32.2 % a 40.2 % (WR 50 %) pero reduce el tamaño del primer pago ($1,044 → $804).

**Qué dice y qué no dice esta tabla**
- 3×728 y 4→1 superan a 3×364 en cobrado por XFA con diferencias *distinguibles* (3×728: +$65 [+20, +105] a WR 47.4 % y +$180 [+125, +253] a 50 %; 4→1: +$89 [+72, +109] y +$97 [+58, +122]), pero **ambos mueren más rápido** (P(muerte en 3 días) 30–38 %) y 3×728 pierde la XFA el **día 1 en 9 % de las vidas** (liquidación por MLL a 667 ticks < TP 728). La ganancia viene de la estructura de pagos (sesiones más grandes ⇒ saldo mayor cuando la cuenta es elegible), no de más acierto (`REPORTE_H1b.md` §5).
- **«1 micro toda la vida»** paga la mitad pero se cobra algo en 49–64 % de las vidas: es un perfil de menor varianza, no una mejora del valor esperado.
- La etiqueta «WR 47.4 %» es la de H1 (deriva calibrada en el bracket nominal 364/364): con 3×728 el WR por sesión no es comparable.
- El IC cubre el conjunto de días históricos y el ruido de simulación; **no** cubre el WR verdadero (47.4 vs 50 mueve el cobrado un 60 %), el slippage real de MGC, ni que el motor reproduzca la XFA real.

**Cuáles tocan RTP / «conducta prohibida» (ticket a Topstep SIN respuesta; marcar DESCONOCIDO, no asumir permitido)**

| geometría | toca RTP / conducta | por qué |
|---|---|---|
| 3×364 | no más que hoy | es la producción |
| 3×728 | **sí, pregunta abierta** | duplica la exposición por sesión (SL de $2,184 > colchón inicial de $2,000: la cuenta se liquida antes del SL); preguntas sobre umbrales de «conducta prohibida» sin respuesta |
| 4→1 micros | **sí, pregunta abierta** | cambia el tamaño según el saldo (4 → 1 al pasar $1,500) tras acumular saldo: patrón que Topstep podría leer como gestión de riesgo del pago; sin respuesta |
| 1 micro (semana o vida) | no hay razón conocida | reducir tamaño no figura entre las conductas citadas en las reglas leídas; DESCONOCIDO sin respuesta escrita |
| varias cuentas con las mismas señales | **sí** (RTP «varias cuentas tocando el MLL el mismo día», G4) | fuera del alcance de esta tabla |

Despliegue: 3×364 y 1 micro (con `GLITCH_PI_NC_MAX=1`) se pueden hacer sin tocar código; 3×728 requiere cambiar `XFA_MGC_BRACKET_TICKS` (el Pi sí acepta ticks hasta 4× lo configurado); 4→1 requiere cambiar Railway **y** el Pi (el Pi rechaza `nc` > 3).
