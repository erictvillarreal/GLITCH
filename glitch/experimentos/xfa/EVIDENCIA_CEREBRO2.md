# EVIDENCIA_CEREBRO2 — qué sabemos y qué falta sobre Cerebro 2 (MGC, XFA 50K) — 20-oct-2026

Cerebro 2 hoy: MGC, 3 micros, SL = TP = 364 ticks, entrada 7:13 CT (referencia = close de la barra de 7:15), flatten 14:30 CT, lado `alternate`. Cifras de este documento: `evidencia_stats.md`, `resultados_D*.md` (todo reproducible con los scripts de `experimentos/xfa/`).

## 1. Datos limpios que existen — y un hallazgo que los contamina

| fuente | N | uso | estado |
|---|---|---|---|
| `mgc_5min_2y_corrected_window.parquet`, 2024-09-06 → 2026-09-04 (515 días con barras de 5 min) | **488 días utilizables** (el resto: cierres anticipados o sin cobertura hasta el flatten tras filtrar el contrato) | simulación y replay | **ver 1.1** |
| Practice 14–16-oct (3 sesiones: SL, FLATTEN −$243, FLATTEN −$138; 0 TP) | **N = 3** | validación de mecánica | **[citado en el encargo; no leído `validacion_mgc_14oct2026`]**; “entrada = referencia exacta” en las sesiones 2 y 3 **POR CONFIRMAR** |
| paper de la fase de prueba de Cerebro 2 | — | — | **contaminado** (dicho en el encargo; no se usa) |

### 1.1 Hallazgo de datos: el archivo MGC intercala barras de DOS contratos simultáneos
- **225 de 515 días (44 %)** traen barras de dos contratos a la vez (p. ej. 23-sep-2024: MGCV4 ≈ $2,625 y MGCZ4 ≈ $2,653 alternándose bar a bar). Hay **2,095 cambios de etiqueta** dentro del día y el salto medio al cambiar es de **25 puntos** (p10 18, p90 33) = **250 ticks**: del tamaño del bracket de 364 ticks.
- El código previo (`dd_wr/product_sweep.py::load_sessions`, usado por `tables_generic.build`, el motor de caja y las pruebas de Cerebro 2) **ignora la etiqueta del contrato** y concatena las barras del día. Esos saltos son **artefactos**, no movimiento de mercado: inflan los toques de TP/SL.
- **Efecto medido** (bracket 364/364, 3 micros, sin slippage): fracción de días que terminan en TP/SL **25.2 % / 25.2 %** (contaminada) vs **22.0 % / 22.0 %** (limpia, contrato de mayor volumen del día): +14 % de “días decididos” falsos; rango mediano del día 486 vs 423 ticks.
- **Efecto en el pago por XFA** (reglas verificadas): P(≥1 pago) 32.1 % (contaminada) vs 35.6 % (limpia); **cobrado medio casi igual** ($731 vs $736). El $620/31.6 % publicado queda **reproducido** por el motor nuevo ($618/31.7 %) y es consistente con la serie contaminada; el efecto de la limpieza es pequeño pero real y a favor de P(≥1 pago).
- **Ventana de oro** (14-nov-2025 → 26-ene-2026): con la serie limpia, quitarla casi no mueve el pago por XFA (plan actual $721 con oro vs $736 sin oro). Lo que pesaba en el pasado ($77.5/contrato/día) **no sobrevive a la limpieza del contrato** en el pago por XFA (sí puede pesar en el Combine de MES; ver C1).
- **No estacionariedad:** FLATTEN 90 % de los días en el primer bloque (sep-2024 → mar-2025), 73 %, 33 %, 28 % en el último (mar → sep-2026). El oro **se volvió mucho más volátil**: con 364 ticks (36.4 puntos) de bracket, hoy ≈ 72 % de los días son TP o SL, antes ≈ 10 %. Un backtest de 2 años mezcla dos regímenes; el régimen reciente (últimos 250 días limpios) da **P(≥1 pago) 29 %** y $773 por XFA (plan actual) vs 36 % y $736 con toda la historia.

## 2. El día REAL de Cerebro 2 (no solo TP/SL)
Con `alternate` por fecha real (serie limpia, 488 días, comisión incluida, sin slippage): **TP 20.9 % · SL 23.2 % · FLATTEN 55.9 %**; **WR = TP/(TP+SL) = 47.4 % [IC95 40.9–54.1]** (45.7 % [38.7–52.9] sin la ventana de oro). La cifra “WR 49.97 %” excluye los FLATTEN y no usa la alternancia real: **no es evidencia de que el día promedio sea de 50/50 con el lado de producción**.
- Un trade medio rinde **−$25 a −$42** (WR < 50 % + comisión $5.76/día).
- **Los FLATTEN importan para el pago**: 43 % de los días son “días ganadores” (≥ $150 netos) y **49 % de ellos son FLATTEN en positivo**, no TP. Un FLATTEN medio es ≈ $0 con sd $422: 39.6 % ≥ +$150 y 35.9 % ≤ −$150.
- **¿El flatten ayuda o perjudica?** Variando la hora del cierre forzado (10:30, 12:00, 13:30, 14:30 CT): cobrado por XFA $715, $727, $729, $736 (plan actual) y $814, $809, $817, $838 (728×3): **diferencias ≤ 3 %**; cerrar antes sube P(≥1 pago) (38.9 % a las 10:30 vs 35.9 %) pero baja el cobrado medio. **Ni ayuda ni perjudica de forma material**; no hay razón para moverlo.

## 3. Qué está validado por mecánica y qué no
- **Validado (por código/pruebas y la Practice del 14–16-oct, N = 3):** colocación de entrada + TP + SL ligados, flatten a 14:30, resolución del front month (T4, `activeContract`), señal por producto, tope de contratos, cuenta fijada y lista de denegación. [citado, no repetido por mí]
- **No validado:** WR real, **slippage de entrada y salida en MGC** (la entrada anclada a la referencia pesa distinto aquí: 3 ticks son 0.8 % de un TP de 364 y bajan el cobrado ≈ 8 %; 10 ticks lo bajan ≈ 25 %), la forma real de `Order/search` y los fills de salida, la liquidación en vivo, y que “precio de entrada = referencia” sea exacto (por confirmar).

## 4. Cotas: WR 45 % / 50 % / 55 % lado a lado (el WR es la palanca que NO podemos medir)
Mismo motor, W2 (MGC limpio sin la ventana), reglas verificadas, deriva calibrada para fijar el WR entre días decididos (la trayectoria intradía y la liquidación en tiempo real son las reales):

| WR (decididos) | plan actual: cobrado por XFA [P(≥1 pago)] | 728×3 | neto anual por cuenta con la cadena completa, plan actual (Combine hoy / con finish-line; mezcla de slip {1,3}; stop 0.5; `resultados_D9.md`) |
|---|---|---|---|
| **45 %** (peor caso razonable) | **$245** [18 %] (stop exacto $270) | $244 [14 %] | **−$2.6k / −$2.1k** (P(neto < 0) 86 % / 81 %) |
| **50 %** (caso base, sin deriva) | **$648** [33 %] (stop exacto $736) | $817 [28 %] | **+$1.3k / +$2.3k** (45 % / 35 %) |
| **55 %** (hipótesis optimista) | **$2,070** [50 %] | $7,020 [45 %] | **+$9.8k / +$11.5k** (9 % / 5 %) |

**El signo del negocio lo decide el WR**: el cobrado por XFA se multiplica por ≈ 3.2 de 50 % a 55 % y se divide por ≈ 2.6 de 50 % a 45 %. **El punto de equilibrio está en WR ≈ 46 %** (cobrado por XFA ≈ costo de obtenerla, $330–400); el WR observado con la alternancia real es **47.4 % [40.9, 54.1]**: **cabe el equilibrio, el caso base y el caso malo**. Con el flujo anual completo (cadena, `resultados_D8.md`) el caso base es positivo pero modesto y sensible al slippage del Combine.

## 5. Plan de evidencia mínimo y qué decisión se puede tomar con qué N
Cada sesión termina en TP o SL solo ≈ 44 % de las veces; el resto es FLATTEN.

| N sesiones | trades decididos (≈ 44 %) | qué se puede decidir | semi-ancho del IC95 del WR |
|---|---|---|---|
| **3 (hoy)** | 1 | **nada** sobre WR; solo mecánica | — |
| 20 | 9 | fills y slippage (media ± 1 tick), referencia exacta, flatten | ± 33 pp |
| 100 | 44 | acotar la fracción de FLATTEN (± 10 pp) y el slippage de salida; descartar WR < 30 % | ± 15 pp |
| 500 | 220 | acotar el WR a ± 6.6 pp: distingue 50 % de 40 % | ± 6.6 pp |
| **616** | 271 | decidir entre WR 45 % y 55 % con 5 % de error en ambos sentidos | — |
| **1,410** | 620 | rechazar 50 % cuando el verdadero es 45 % (o 55 %) con potencia 80 % | ± 3.9 pp |

A una sesión por día hábil, 616 sesiones son ≈ 2.4 años; 1,410 son ≈ 5.6 años. **El WR no se podrá medir a tiempo con sesiones vivas**: la decisión de llegar a la XFA con Cerebro 2 debe tomarse **sin** esa certeza, con las cotas de §4 y con la estructura de pagos como protección.
**Qué registrar desde la primera sesión** (parche C3 + historial): `ref_price`, `fill_price`, `slip_ticks`, resultado {TP, SL, FLATTEN}, precio y hora de salida, P&L neto, contrato y front month usado, balance, colchón, días ganadores. **Costo**: ≈ 15 líneas de código ya escritas (C3, NO DESPLEGAR) y las sesiones.
**Para que el WR deje de ser la apuesta:** un diseño que no dependa de él o lo mida más rápido (más decisiones por sesión, p. ej. varios brackets por día o brackets más cortos), pero ya se vio que los brackets cortos con 3 micros reparten pagos pequeños y **bajan** el cobrado medio (−$400 por XFA, `resultados_D.md`).

## 6. ¿Es defendible llegar a la XFA con Cerebro 2? (cotas, no cifra puntual)
- **Sí, bajo cero ventaja asumida (WR 50 %)** el negocio es positivo pero modesto (+$1.3k a +$2.3k al año por cuenta con la mezcla de slippage observada y las reglas verificadas; +$2.7k con slip 1 y +$0.5k con slip 3 en el Combine); el costo de obtener una XFA ($317–$446) deja un margen de $200–$420 por XFA.
- **No es defendible como apuesta de edge**: con WR 45 % cada XFA pierde ≈ $90–150 y la cuenta pierde ≈ $2–3k al año; el WR observado no excluye ese caso.
- **Qué cambiaría el veredicto:** (i) un WR medido ≥ 50 % con IC que excluya < 46 % (≥ 600 decisiones); (ii) slippage de MGC ≤ 3 ticks medido; (iii) la respuesta de Topstep sobre RTP/compras (preguntas 1 y 2); (iv) P(pase) del Combine ≥ 27 % (finish-line o brackets anclados al fill).
