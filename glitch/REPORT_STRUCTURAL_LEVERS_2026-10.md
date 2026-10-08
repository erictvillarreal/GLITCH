# Palancas estructurales para llegar a US$6,000–10,000 al año (sin buscar edge)
*Rama `research/structural-levers`, sandbox, oct-2026. Cero cambios a main, Railway, Pi o producción; todo cambio de lógica de capital aquí es solo PROPUESTA (CLAUDE.md regla 4). Reproducible: `scripts/lever_t{1..5}_*.py`, `scripts/lever_final.py` (salidas en `dd_cash/lever_*_report.txt`); motor `dd_cash/lever_engine.py` + `lever_data.py`, con prueba de equivalencia contra el motor validado (`tests/test_lever_engine.py`).*

## 0. Respuesta corta
**Meta mínima US$6,000 / ideal US$10,000, neto anual, 12 meses desde 19-oct-2026, tras todos los costos ($714 compartido incluido).** Tres cifras por celda, siempre en este orden: **mundo justo** (estimador estructural: 60 mundos sintéticos sin deriva ni edge) / **historia real CON** la ventana de oro 14-nov-2025→26-ene-2026 / **historia real SIN** esa ventana. Slip 0.5. "Paso 2" = TP 32 + bracket de la XFA 728 ticks × 3 micros (propuesta, §4).

| Paquete (50K) | Justo | Real CON oro | Real SIN oro | P(≥$6k) j / c / s | P(≥$10k) j / c / s | Intentos Combine/año | Días con ≥2 cuentas en MLL |
|---|---|---|---|---|---|---|---|
| Hoy (TP40, XFA 364×3), 1 cuenta | 2,067 | 1,707 | 390 | — | — | 64 | 0 |
| Paso 1 (TP32), 1 cuenta | 3,026 | 2,580 | 1,160 | — | — | 55 | 0 |
| Paso 1, 2 cuentas MISMA señal | 6,766 | 5,874 | 3,034 | ≈49% (T2, justo) | ≈34% (T2, justo) | ~108 | n/c |
| **Paso 2, 1 cuenta** | **5,384** | **3,240** | **1,821** | — | — | 54 | 0 |
| **Paso 2, 2 cuentas señales distintas (MES + MCL)** | **10,187** | **6,348** | **4,567** | 64% / 48% / 39% | 47% / 29% / 22% | 111 | 12 |
| **Paso 2, 3 cuentas distintas (MES + MCL + MGC 9:45)** | **14,715** | **7,566** | **5,556** | 77% / 53% / 44% | 63% / 37% / 29% | 167 | 34 |
(Hoy y paso 1: neto por cuenta de §2.1 menos $714. El resto, de la Tarea 5. Las celdas "—" no se calcularon como paquete.)

**Veredicto por meta**
- **US$6,000 — SOLO SI** (a) se aprueba y valida en paper el bracket de la XFA 728×3 (cambia lógica de capital) **y** (b) se opera con ≥2 cuentas de señales distintas **y** (c) Topstep acepta ~110 intentos de Combine al año. Con oro: sí, justo (6.3k; 48% de probabilidad de llegar). **Sin oro: NO** (4.6k con 2 cuentas, 5.6k con 3). Con 1 cuenta: NO en ningún escenario (3.2k con oro, 1.8k sin oro, 5.4k incluso en mundo justo).
- **US$10,000 — SOLO SI** el régimen es el justo (sin deriva negativa) **y** se operan 3 cuentas distintas (14.7k) o 2 con 47% de probabilidad (10.2k). **En historia real: NO** (7.6k con 3 cuentas con oro; 5.6k sin oro).
- **Extraordinario (>$10k):** solo en mundo justo con ≥3 cuentas; no lo recomiendo planear: depende de 160+ compras de Combine al año, algo que Topstep puede interpretar como "compras excesivas" (§5).

**Lo que más importa saber antes de decidir**
1. **No hay una palanca individual que lleve una cuenta a $6k.** Cada palanca se evaluó sola (§2): precio del intento, pase %, payout por XFA, intentos/año. Ninguna lo logra salvo multiplicar el payout por XFA ×1.31 ($708 vs $539 hoy); el resto es inalcanzable sin romper el techo de pase de 32.7% o el precio ≥ $0.
2. **La palanca real es el payout por XFA** (cada +$1 por XFA = +$16.8 al año por cuenta) y el **número de cuentas**. El bracket de 728 ticks sube el payout de $531 a $678 por XFA en el pipeline (+28%; en historia +7% a +8%).
3. **El dinero depende de que el régimen no sea el de la historia real.** En mundo justo una cuenta rinde $5.4k; en la historia real, $3.2k con la ventana de oro y $1.8k sin ella. La historia real cae dentro del rango de una sola historia justa (§2.3), así que no se puede concluir que el mundo justo sea optimista, pero tampoco que se vaya a cumplir.
4. **Dos hallazgos que cambian decisiones:** (i) comprar el DLL del Combine para duplicar el tope de pago **destruye** el resultado (−58%); (ii) el ajuste "−25%" que usaba el reporte previo no es una constante: es el efecto de la liquidación en tiempo real, que depende del bracket (modelada ahora explícitamente, §1).

## 1. Tarea 1 — Reglas verificadas y correcciones al motor
Fuente: help.topstep.com leído entre el 07 y el 09-oct-2026 (artículos 8284215, 8284233, 8284204, 8284208, 8284197, 14289835, 13620045, 10490293, 15520357, 13613539).

| Regla | Valor verificado | Motor anterior | Acción |
|---|---|---|---|
| Pago mínimo | **$125** | no modelado | agregado |
| Pago Standard (50K) | 50% del balance, tope **$2,000**; 5 días ≥$150 netos; **ganancia neta ≥ $0.01 desde el último pago (el primero exento)** | solo `balance>0` | agregada la regla de ganancia neta |
| Pago Consistency (50K) | 50%, tope **$3,000**; ≥3 días con operación; mejor día ≤40% de la ganancia neta del periodo | no modelado | agregado (`path="cons"`) |
| Tope doble con DLL | $4,000 Standard / $6,000 Consistency **solo** si se agrega DLL al comprar el Combine; "oferta temporal" desde el 2-jun, sin fecha de fin | no modelado | modelado; **resultado: no conviene** (§3) |
| Reparto | 90/10; **primeros $10,000 de ganancia de por vida al 100%** solo para traders que entraron al dashboard nuevo antes del 12-ene-2026 | 90/10 | opcional (`first100`); **no sé si aplica a ti** |
| MLL en la XFA | 50K: arranca −$2,000, sube con el balance EOD, **se traba en $0 permanente** al llegar a $2,000; tras cada pago el MLL queda en $0; monitoreado en tiempo real con P&L no realizado | igual | sin cambio |
| Escalado de contratos XFA 50K | **No pude verificarlo en fuente propia**: el artículo del Scaling Plan no trae la tabla. Labs: 2/3/4 para la cuenta estática; terceros: 2/3/5. Para símbolos restringidos (MGC, MCL, GC, CL…): 12 / 18 / 31 micros (<$1,500 / $1,500 / $2,000) | 20/30/40 (xfa_lab) y 20/30/50 (funded_account) | **inmaterial**: Cerebro 2 usa 3 micros; la propuesta usa 3; la cuenta MCL del portafolio 11. Agregado el tope de símbolos restringidos |
| Combine 50K | MLL $2,000 trailing EOD con liquidación en tiempo real; target $3,000; consistencia 55% del target (mejor día/0.55 si se excede); ≥2 días; máx. 5 minis/50 micros | igual | sin cambio |
| Precios Combine | Standard **$49/$99/$199** + activación **$149** por XFA; "No Activation Fee" **$95/$149/$229** y activación $0; **el reinicio cuesta exactamente lo mismo que el plan** (tabla oficial); no hay tope de Combines simultáneos | $49 / $149 | sin cambio |
| Discrepancia $85/$129/$199 vs $95/$149/$229 | **Resuelta**: $95/$149/$229 es la lista del plan NAF; $85/$129/$199 es ese plan con el "Responsible Trading Discount" (−$10/−$20/−$30) **si se agrega DLL al comprar**, recurrente cada mes | — | modelado (paso 7: no conviene) |
| Promociones | Un código aplica a una compra nueva **o** a un reinicio; el precio promo es solo del primer mes; referido: 15% la primera compra, hasta 5 códigos de recompensa por 90 días | — | efecto ≈ $7 por código sobre $49: **despreciable**, no es palanca |
| Back2Funded | Reactivar una XFA perdida antes del primer pago en 30 días: **$599** ($549 con DLL) | — | no conviene (un Combine nuevo cuesta $49) |
| DLL | 50K: $1,000; optativo al comprar; fijo después; al tocarlo se liquida y se bloquea la sesión (no es infracción); hereda a la XFA | — | modelado |
| RTP | Señales: "multiple accounts hit the Maximum Loss Limit in one day", "you max position a majority of your trades", entre otras. Consecuencias: DLL automático (−$1,000 en 50K), XFA solo Consistency (<40% por periodo), XFA Standard no disponible hasta salir; hasta 5 XFAs; salir exige $10,000 de ganancia en una Live. **Sin umbrales numéricos públicos** | — | métricas de conducta reportadas, sin poder juzgarlas |

**Correcciones al motor y su efecto** (1 cuenta, TP32, mismas semillas; tabla completa en `dd_cash/lever_t1_report.txt`):
| Cambio | CON oro | SIN oro |
|---|---|---|
| Motor previo: serie MGC + ajuste −25% (neto/cuenta, con tarifa inicial) | 3,674 | 2,010 |
| + pago mínimo, regla de ganancia neta, tarifa inicial en caja, tope de símbolos restringidos | 3,628 (−1%) | 1,974 |
| **+ liquidación en tiempo real EXPLÍCITA de la XFA en lugar del ajuste −25%** (slip 0) | **4,269** | **2,593** |
| + slip 0.5 (llenado del stop en el extremo de la barra; base de este reporte) | **3,346** | **1,841** |
| slip 1.0 | 2,631 | 1,199 |
**Por qué sustituí el −25%:** la liquidación explícita reproduce el log (XFA 364×3, slip 0: $623 por XFA y 31.9% de P(≥1 pago) contra $620 y 31.6% del log) y la serie con −25% da el mismo pago por XFA (0.75 × 849 = 637), pero **la vida de la XFA es más corta**, así que el pipeline rota más rápido (54 vs 49 intentos al año). El −25% sobre la serie subestima el flujo anual (~+$600 por cuenta) y, sobre todo, **no vale para otros brackets**: en el 728×3 el stop casi siempre es la liquidación. Para comparar con las cifras anteriores: la convención "serie −25%" da $3,258 por cuenta para TP32 en mundo justo; la liquidación explícita, $3,880.

## 2. Tarea 2 — Elasticidades e ingeniería inversa
### 2.1 Base y descomposición (mundo justo, 40 mundos, TP32, XFA 364×3 vigente, slip 0.5; 1 cuenta)
Neto/cuenta **$3,880** (mediana 3,203; p10 −2,222; p90 10,747; P(<0) 24%) = pagos **$9,032** − fees de Combine **$2,653** − activaciones **$2,499**; intentos **54.1**/año; pase **31.0%** (techo justo 32.7%); XFA **16.8**/año; payout por XFA **$539**; precio por intento $49; activación $149; días con MLL tocado **53**. Identidad: neto ≈ A × [p × (Pxfa − act) − c].

### 2.2 Elasticidades (cada fila mueve una sola palanca; el resto en la base)
| Palanca | Rango probado | Efecto en neto/cuenta | Pendiente |
|---|---|---|---|
| Precio por intento (= reinicio) | $0 → $120 | $6,533 → $37 | **−$54 por cada $1** |
| Activación | $0 / $75 / $149 | $6,379 / $5,122 / $3,880 | −$16.8 por cada $1 |
| Plan NAF $95, act $0 | — | $3,889 (+$9) | neutro: el punto de equilibrio es p = 31% |
| Pase % (exógeno) | 12.4% → 99% | −62 → 7,494 | ≈ +$115 por punto; **techo justo 32.7%** |
| Payout por XFA | ×0.5 → ×3 | −636 → 21,944 | **+$9,032 por unidad** (+$16.8 por cada $1 de Pxfa) |
| Intentos/año (tope K) | 5 → sin tope | 449 → 3,880 | ≈ $34–89 por intento (marginal decreciente); P(<0) baja de 67% a 24% |
| Cuentas, misma señal | 1 → 5 | 3,166 → 18,688 (tras $714) | **+$3,880 cada una** |

### 2.3 Qué valor exige cada meta (una palanca, el resto en la base; N=1, neto tras $714)
| Palanca | Para US$6k | Para US$10k | ¿Alcanzable sin romper conducta ni fills? |
|---|---|---|---|
| Precio por intento | −$3 | imposible | **No** (precio ≥ $0; los códigos solo bajan el primer mes) |
| Pase % | ~72–75% | imposible (con 100% llega a $7.5k) | **No** (techo justo 32.7%) |
| Payout por XFA | **$708** (×1.31) | **$947** (×1.76) | **$6k: casi** (el bracket 728×3 da $678 en el pipeline, neto $5.4k); $10k: no (el techo DP es $1,341 solo con lotería irrealizable; mejor sin lotería: $779 en vida única) |
| Intentos/año | imposible | imposible | **No** (sin tope ya son 54) |
| Cuentas misma señal | 2 (7.0k) | 3 (10.9k) | Sí matemáticamente; choca con el RTP (§5) |
El rango de una sola historia justa de un año es enorme: tres historias sintéticas dieron $9.2k / $5.9k / $1.9k por cuenta con la misma estrategia. La historia real ($3.3k con oro) cae dentro de ese rango; **un año no distingue entre "mundo justo" y "la historia real"**.

## 3. Tarea 3 — Política de ciclos
Mundo justo, 30 mundos, XFA 728×3, 1 cuenta, neto/cuenta. **Reiniciar o comprar nuevo es la misma decisión** (mismo precio, verificado): la única decisión real es *seguir o detenerse*.
| Política | Media | Mediana | P(<0) | Intentos | Días MLL |
|---|---|---|---|---|---|
| Sin tope (nc=40) | 6,796 | 5,770 | 18% | 52 | 51 |
| K = 30 | 4,657 | 2,439 | 31% | 29 | 29 |
| K = 20 | 3,276 | 1,130 | 40% | 20 | 20 |
| K = 15 | 2,487 | 320 | 42% | 15 | 15 |
| K = 10 | 1,687 | −467 | 52% | 10 | 10 |
| **Bloqueo de ganancia $3,000** (deja de comprar al llegar a +$3,000) | 5,016 | 4,248 | **17%** | **34** | 34 |
| Bloqueo $6,000 | 6,006 | 6,312 | 18% | 43 | 42 |
| Paro por pérdida $2,000 | 5,691 | 4,360 | 34% | 42 | 41 |
| Paro por pérdida $1,000 | 4,062 | −1,030 | 55% | 30 | 29 |
- **Un tope de intentos K solo baja el promedio y sube el riesgo** (~$160–170 por intento, P(<0) 40–52% con K ≤ 20): cada intento tiene valor esperado positivo, así que quitar intentos quita dinero y quita la diversificación entre intentos. **Los paros por pérdida son peores** (matan los ciclos buenos que vienen después de rachas malas).
- **La política que minimiza P(<0) para una media dada es el bloqueo de ganancia:** con $3,000 conserva 74% de la media, mantiene P(<0)≈17% y baja los intentos a 34 (−35%) y los días con MLL tocado a 34.
- **Huella** (sin tope): nc=50 → 6,563; **nc=40 → 6,796**; nc=25 → 6,390 (−6%, 0% de trades al ≥80% del máximo); nc=16 → 5,497 (−19%). Con nc=25 se evita ser "máximo en la mayoría de los trades" (nc=40 es 80% del tope de 50 micros; no sé si Topstep lo cuenta como "max position") por ~$0.4k al año.
- **Paquete DLL (Combine y XFA con DLL $1,000, tope $4,000, plan NAF $85):** $2.6k–$3.3k por cuenta contra $6.8k: **−58%**. El DLL baja el pase de 31% a 20–24% y fuerza un bracket XFA menor; el tope doble solo agrega +$98 por XFA. No comprar el DLL.

## 4. Tarea 4 — Política de payout de la XFA (fills realistas, sin lotería)
Una XFA, 126 días, payout al trader; **liquidación en tiempo real explícita**; MGC 7:13 CT; bracket simétrico SL=TP (1:1); **regla anti-lotería: TP ≤ 1.25 × SL efectivo** (SL efectivo = mín(bracket, distancia al piso)). La geometría se eligió en el mundo justo (economía de las reglas), no en la historia real.
| Geometría | slip | Justo | Real CON oro | Real SIN oro |
|---|---|---|---|---|
| Hoy: 364 × 3 | 0.0 / 0.5 / 1.0 | 757 / **602** / 503 | 619 / **537** / 482 | 478 / **421** / 379 |
| **728 × 3** | 0.0 / 0.5 / 1.0 | 837 / **779** / 733 | 587 / **575** / 565 | 463 / **453** / 446 |
| Techo DP (cualquier política, incluida lotería) | — | 1,341 | — | — |
- **Mejor geometría sin lotería: 728 ticks × 3 micros** (riesgo $2,184 por trade ≈ la distancia al piso: el stop es casi siempre la liquidación). Meseta plana: 637×3 $763, 546×3 $743, 728×2 $765 (no es un filo de navaja). **+29% en mundo justo, +7% con oro, +8% sin oro.** Es menos sensible al slip (−12% de slip 0 a 1.0) que el bracket de hoy (−34%).
- **Momento de retiro:** pedirlo en cuanto es elegible es óptimo; esperar a un balance mínimo de $1,000–$2,000 no cambia nada y de $3,000 en adelante reduce el pago (728×3: 779 → 708 con umbral $6,000).
- **Ruta:** con el bracket de hoy, Consistency (tope $3,000, 3 días) rinde $631 contra $602 de Standard (+5%); con 728×3, Standard rinde $779 contra $702 (+11%). Bajo RTP solo existe Consistency.
- **Tope doble ($4,000)**: 728×3 pasa de 779 a 877 (+13%) pero exige DLL, que cuesta mucho más (§3).
- **Dependencia de la ventana de oro:** −22% del pago por XFA sin oro con ambos brackets; el efecto en el pipeline anual es mucho menor con el bracket de 728 (3.9k → 2.8k, −29%) que con el de hoy (2.4k → 1.1k, −54%).
- **Elegibilidad:** 5 días ≥$150 netos (Standard); el pago pedido no cuenta para el siguiente ciclo; el MLL queda en $0 tras cada pago, así que la distancia al piso tras un pago es el balance restante.

## 5. Tarea 5 — Portafolio de 2–3 cuentas con señales distintas
**Selección por estructura, no por rendimiento.** Correlación de los retornos diarios dirigidos (entrada→flatten normalizados por el rango mediano; 497 días comunes) con MES 9:45: MNQ **0.96**, M2K **0.89** (mismo trade), MGC 7:13 **0.17**, MGC 9:45 0.27, M6E 0.12–0.14, **MCL 0.01–0.02**. Escalonar la hora no ayuda dentro de la misma clase de activo (MES 8:43 vs 9:45: 0.87). Criterios: baja correlación, liquidez (MES > MGC ≈ MCL > M2K > M6E), ejecutabilidad por la API de TopstepX (los seis son micros CME), costo en el Pi (mismo código: `product` y hora). Geometría con regla estructural (`structural_geometry`): el stop es la liquidación del MLL con la misma fracción del rango que MES, TP para que dos TP netos sumen ≥$3,100, bracket XFA con el mismo múltiplo del rango que Cerebro 2.
| Cuenta | Combine → XFA | Geometría | Pase (justo) | Neto/cta justo |
|---|---|---|---|---|
| A (vigente) | MES 9:45 → MGC 7:13 | nc 40, TP 32 / 728×3 | 30.8% | 6,567 |
| B | MCL 8:43 → MCL 8:43 | nc 50, TP 33 / 195×11 | 29.0% | 4,334 |
| C1 | MGC 9:45 → MGC 9:45 | nc 26, TP 62 / 490×4 | 28.6% | 4,528 |
| C2 (descartada: iliquidez y ρ=0.32 con MGC) | M6E 8:43 | nc 50, TP 26 / 60×12 | 25.7% | 1,138 |
| Contraste: A + MNQ-Combine | MNQ 9:45 → MGC | nc 20, TP 158 | 21.2% | 3,547 |
Historia real, T=20,000 (neto total, tras $714): ver §0 para los paquetes. Conducta: **misma señal ×2: 52 días/año con ≥2 cuentas en el MLL** (cada quiebre coincide); **A+B: 12**; A+C1: 17; A+B+C1: 34; A+MNQ: 21. Con 53 quiebres por cuenta al año, dos cuentas *independientes* ya coinciden ~11 días al año: **la diversificación baja la coincidencia de 52 a 12 días, pero no la elimina**. Colchón p95 (pérdida máxima acumulada): 1 cuenta ~$5.2k; 2 cuentas distintas ~$6.9k; 3 ~$9.1k.
Advertencias: (i) las geometrías de B y C1 salen de una regla sin ajuste, y su Combine usa tamaños (MCL 50 micros, MGC 26) que **podrían estar limitados por la lista de símbolos restringidos**; no encontré el tope del Combine; (ii) en mundo justo los productos se voltean de forma independiente, así que la diversificación de las cifras "justo" es la cota optimista; (iii) tres cuentas = ~167 compras de Combine al año.

## 6. Tarea 6 — Otras firmas (solo análisis, nada construido)
| | Topstep 50K | Tradeify Growth 50K | Tradeify Select 50K | Bulenox Opción 2 50K |
|---|---|---|---|---|
| Techo de pase (juego justo, DP) | **32.7%** | 40.0% | 31.3% | **45.5%** |
| Pase simulado (G2/TP dimensionado, in-sample) | 31% (este reporte) | 38.2% | 31.1% | 43.2% |
| Techo de elegibilidad al 1er pago | — | 30.1% | — | 32.0% |
| Techo de payout por cuenta fondeada | **$1,341** (DP, al trader) | Select Flex $1,323 (aprox.) | — | primer pago $1,500 al 100% |
| Costo por intento / activación | $49 + $149 | $145 + reinicio $95 | $165 + $109 | $175 + $78; activación $148 |
| Costo esperado por pase | ~$299 | $301 | $407 | $292 + $148 |
| Reparto | 90/10 | 90/10 | 90/10 | **100% los primeros $10,000** (una vez por trader) |
| Cuentas simultáneas | 5 XFA, Combines sin tope | — | — | 5 Master + calificaciones ilimitadas |
| Esfuerzo del adaptador | **Ninguno** (ProjectX; ejecutor existente) | Nuevo (Tradovate/Rithmic/WealthCharts; API de Tradovate solo en cuentas live según un resumen no verificado) | Nuevo | **Nuevo: Rithmic**, API de terceros **+$100/mes**, aprobación de Bulenox, OCO local de NinjaTrader, solo Windows |
- La ventaja de Bulenox (techo 45.5%) es real, pero **el payout por cuenta fondeada no mejora** (techo de elegibilidad 32.0%, exige 10 días, consistencia 40%, pagos mínimos de $1,000 y reserva de $2,600): el costo de la fricción (+$100/mes, adaptador, aprobación discrecional del algoritmo) se come la ventaja de pase. **Los resultados de caja anteriores de estas firmas no son comparables con este reporte:** `dd_cash/firms_cashflow_report.txt` usó estructuras de lotería ("fondeada A óptima sin restricciones") y `bulenox/exp4` otro motor y otra geometría.
- **Recomendación: no construir.** Ninguna firma alternativa resuelve el problema de fondo (el payout por XFA/cuenta fondeada está acotado por el piso, y el pase por el techo de juego justo). Si el objetivo es más cuentas, Topstep permite 5 XFAs sin adaptador nuevo.

## 7. Supuestos no verificados (marca explícita)
1. Tabla de escalado real del XFA 50K (2/3/4 vs 2/3/5) y límites de símbolos restringidos **en el Combine** (MCL/MGC): inmaterial para el paquete A, **crítico para B y C1**.
2. La oferta de tope doble: sin fecha de fin; el modelo la trata como vigente en el paso 7.
3. El 100% de los primeros $10k aplica solo si entraste al dashboard nuevo antes del 12-ene-2026 (modelado como opcional; +$0.9k una sola vez, primer año).
4. Fills: un TP se llena cuando el precio lo toca (estrés "+1 tick": −$0.17k a −$0.18k por cuenta); el stop se llena en el extremo de la barra con slip 0.5; barras de 5 minutos, un trade por día, SL primero en barras ambiguas.
5. Productos independientes en los mundos sintéticos (no se preserva la correlación entre productos); lado alterno compartido entre cuentas (la correlación real se mide en historia).
6. Una sola historia de 497 días en común; el valor de la ventana de oro es parte de esa historia, no una propiedad del mercado.
7. RTP: no hay umbrales numéricos públicos; el reporte da las métricas, no el juicio.
8. Costos operativos: $59.5/mes compartidos por cualquier número de cuentas (el Pi actual soporta una sola; ver reporte del diseño de 2 cuentas).
9. Reinicio = mismo precio que la compra (verificado); no se confirmó que cada reinicio conserve el mismo `accountId`.

## 8. Decisiones que te corresponden
1. **¿Aprobar la propuesta de bracket XFA 728×3?** Es cambio de lógica de capital: requiere revisión humana y validación en paper con parámetros pre-registrados; mejora de +$0.6k a +$0.9k por cuenta en historia y +$2.4k en mundo justo.
2. **¿Cuántas cuentas y con qué señales?** Mi lectura: 1 cuenta no llega a $6k bajo ningún supuesto; 2 cuentas de señales distintas llegan a $6.3k con oro y a $4.6k sin oro. Requiere adaptar el Pi a N cuentas (diseño ya entregado) y una respuesta escrita de Topstep sobre ~110 compras de Combine al año y días con varias cuentas tocando el MLL.
3. **¿Con qué número planeas?** Propongo planear con el rango historia-real (CON/SIN oro) y tratar el mundo justo como cota superior: una cuenta $1.8k–$3.2k; dos cuentas distintas $4.6k–$6.3k.
4. **No comprar el DLL** para el tope doble (−58%).
5. **Política de conducta**: si quieres reducir intentos, usa bloqueo de ganancia ($3,000), no un tope K.
6. **Preguntas por escrito a Topstep**: ¿cuenta nc=40 sobre un máximo de 50 como "max position"? ¿los 110 intentos/año son "excessive purchases"? ¿límites del Combine para MCL/MGC? ¿sigue vigente el tope doble con DLL?
