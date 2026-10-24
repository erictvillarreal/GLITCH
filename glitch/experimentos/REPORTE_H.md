# REPORTE H — Mapa de probabilidades, descomposición del equilibrio y palancas exhaustivas — sábado 24-oct-2026

> **ACTUALIZACIÓN 24-oct (tarde): la cascada de §1(b), el top-5 de §1(c) y las confianzas de §3 sobre costos operativos y finish-line quedaron reemplazadas por `REPORTE_H1b.md`** (slippage empírico de 7 obs., costos A/B/C, sin el paso «costos → $0»). Las líneas afectadas abajo llevan «[REEMPLAZADO]».

Rama `experimentos-research` (local; el `git push` sigue denegado: entregables en `auditoria_experimentos/`). **No se tocó `main`, el Pi, Railway ni credenciales; ningún parche está aplicado.** Pre-registros firmados **antes** de los resultados: `direccion_e/PREREGISTRO_G2.md` (5ca5252) y `PREREGISTRO_H3.md` (6e2cd85). Todo se reproduce con un comando de `experimentos/direccion_e/` (semillas fijas). **MEDIDO** = datos reales; **MODELADO** = sale del motor de las Partes A/D con supuestos declarados; **SUPUESTO** = número puesto a mano; **DESCONOCIDO** = no hay forma de saberlo hoy.

## 1. Una página

**(a) Dónde están las probabilidades (resumen; la tabla completa con IC95, N, fuente y sensibilidad está en `direccion_e/resultados_H0.md`).**

| cantidad | valor [IC95] | N / sims | estado | sensibilidad principal |
|---|---|---|---|---|
| MGC `alternate`: TP / SL / FLATTEN | 20.9 [17.7, 24.5] / 23.2 [19.6, 27.4] / 55.9 [49.2, 59.6] % | 488 días limpios | MEDIDO (un solo camino de precios) | cargador mezclado: FLATTEN 49.6 %; régimen reciente: FLATTEN ≈ 30 % |
| MGC WR_dec = TP/(TP+SL) (FLATTEN **fuera**) | `alternate` **47.4 [41.1, 54.0]**; siempre LARGO 46.0 [40.7, 51.7]; siempre CORTO 54.0 [48.3, 59.3] | 215 decididos | MEDIDO | LARGO + CORTO = 100 %: el ±4 pp es qué lado cae, no señal |
| MES, un día nc 40 (LARGO, slip 0): TP / **liquidación por MLL** / SL / FLATTEN | 52.8 [48.5, 56.3] / **47.2** [43.7, 51.5] / **0.0** / 0.0 % | 492 días | MODELADO | slip 3: 50.8 / 49.2; CORTO: 56.7 / 42.9 |
| Barrera efectiva MES | liquidación a **40 ticks** ($2,000 / ($1.25 × 40)); el SL de 100 **nunca opera**; martingala ⇒ P(TP) = 40/72 = **55.6 %** | — | hecho aritmético + MODELADO | — |
| P(pasar) cuenta nueva, 40 fijos | slip 0: **29.9** [29.1, 31.2]; 1: 29.0; 2: **18.0**; 3: **17.2**; 4: 16.1 % | 100k intentos × remuestras | MODELADO (slip = SUPUESTO) | escalón entre 1 y 2 ticks (dos TP de $1,501 suman $3,002; con 2 ticks, $2,902) |
| P(pasar) desde el estado actual (+$1,401.20), 40 fijos / finish-line | slip 1: **34.0 / 49.4**; slip 3: 32.6 / 46.2 % | ídem | MODELADO | un TP del lunes **no** alcanza ($1,598.80 faltantes) |
| Intentos hasta pasar | 3.3 (slip 0) a 5.8 (slip 3) cuenta nueva; 2.9–3.1 desde el estado actual; 1.5–1.9 días por intento | — | MODELADO | ≈ 52 compras de Combine al año × $49 = **$2.5k/año**: el mayor costo |
| XFA (3×364), por WR_dec 45 / **47.4** / 48.5 / **50** / 52 / 55 % | P(≥1 pago) 18 / **25.7** / 29.9 / **33.0** / 38.6 / 49.8 %; cobrado por XFA $244 / **$406** / $508 / **$647** / $911 / $1,905; P($0 en la vida) = 1 − P(≥1 pago); mediana al 1.er pago 7–8 días de trading | 40k vidas; 60 remuestras | MODELADO (WR = hipótesis) | el WR de cada escenario es una hipótesis, no un dato |
| Dependencia de régimen | con / sin la ventana de oro: $638 / $647 por XFA; solo la ventana: $632, P(≥1 pago) 27 % | 488 / 443 / 45 días | MEDIDO | casi nula tras limpiar contratos |
| Costos | comisión round-turn MES/MNQ/M2K/MYM $1.22, MGC $1.92; reset/mensualidad $49 por intento, activación $149, wire $30 | Help Center (24-oct / 20-oct) | MEDIDO (fuente primaria) | — |
| Slippage de entrada medido | [ACTUALIZADO] 7 obs.: 0, +1, 0, +3, −1, +1, +3 ticks (media +1.0, IC95 [−0.41, +2.41]); antes: +1 y +3 | **N = 7** (antes 2) | **NO VERIFICADO** (dado por Eric en el chat; sin CSV) · sin potencia | σ de ruido por demora ≈ ±1.4 a ±2.4 ticks a 1–3 s (MODELADO): ambos son compatibles con ruido puro |
| Experiencia viva | MES real: 3 TP de 7 decididos = 43 % [10, 82] vs modelo 55 % (P(≤3 de 7) = 39 %); MGC Practice: 1 decidido | 8 + 3 | MEDIDO **sin información** | hacen falta **620** decididos para 55 % vs 50 %, **2,306** para 47.4 % vs 50 % (≈ 2.5 y ≈ 9 años en MES) |

**(b) Cascada del equilibrio [REEMPLAZADO por `REPORTE_H1b.md` §2]** (WR_dec en que el neto anual por cuenta = 0; slippage de entrada empírico de 7 obs., **NO VERIFICADO**; `direccion_e/resultados_H1b.md`, gráfico `direccion_e/cascada_H1b.svg`):
```
                                          costos A ($240)   costos B ($827)
hoy (P0, 3×364, slip empírico-7)          47.47 %           48.03 %
+ finish-line                             47.11 %  −0.36 pp 47.65 %   (+$480/año a WR 50 %)
+ 728×3                                   46.47 %  −0.63 pp 46.92 %
+ slip adverso acotado ≤ 1 (hipotético)   46.35 %  −0.12 pp 46.78 %
Sensibilidad, mezcla {1,3}, costos A:     48.05 → 47.26 → 46.63 %
Escenario C (facturas): +0.10 pp por cada $100/año sobre A.
```
Se **eliminó** el paso «costos operativos → $0» (no es palanca: es escenario). El WR medido (47.4 %) queda **en** el equilibrio de hoy con costos A (47.47 %), no por debajo; baja del WR medido con la finish-line (A) o con el 728×3 (B). El «−0.72 pp» del 728×3 (versión anterior) era el paso de la cascada con mezcla {1,3}; con slippage empírico es −0.63 (cascada) o −0.67 (aislado). **El WR no se remidió con la geometría 728×3** (eje = etiqueta de la deriva en 364/364): ver `REPORTE_H1b.md` §5.

Idea en tres líneas: el equilibrio no es la puntería sino la cuota del volado. **Cada costo que baja baja el listón.** El 47.4 % medido no distingue de 50 % (0.8 EE) y el listón de la cadena es 47.5–48.0 % (A–B): cerrar ese hueco vale **≈ $1.0k por punto** (pendiente local $1,038), y se consigue con estructura, no con puntería.

**(c) Las 5 palancas con más $/año/cuenta [REEMPLAZADO]** (Δ a WR 50 %, slippage empírico-7, costos A; `resultados_H1b.md` §2; ninguna requiere ventaja direccional):
1. **Más cuentas** (G4b): cada cuenta añadida suma ≈ su neto ($2.6k hoy / $3.2k con finish-line / $4.7k con finish-line + 728×3, **a WR 50 %**; a WR 47.4 % ≈ $0) — MODELADO; ρ entre cuentas **supuesta**; riesgo de reglas (RTP).
2. **728×3**: +$1,476 (−0.67 pp aislado) — MODELADO; mecanismo: pagos mayores, no WR; toca RTP/«conducta prohibida».
3. **Stop exacto en lugar de llenado a 0.5**: +$828 (−0.44 pp) — es un supuesto de llenado del modelo; palanca solo si el stop real se puede acercar al exacto (**DESCONOCIDO**).
4. **Slippage de entrada del Combine a 0 ticks fijos / acotado ≤ 1**: +$744 / +$699 — solo es palanca si es sistemático y reducible: **DESCONOCIDO** (N = 7, NO VERIFICADO).
5. **4→1 micros**: +$627 (−0.95 pp). La **finish-line** vale +$480 (−0.36 pp): **bajo el umbral de $500** con este slippage (+$972 con la mezcla {1,3}).
Los **costos operativos ya no son palanca** (escenarios A $240 / B $827 / C pendiente de facturas). Cotas teóricas no accionables: reset $49 → $0 (+$2,351), activación → $0 (+$1,771), comisión MES → $0 (+$535). Anclar al fill: +$55 a +$657 según σ y política — SUPUESTO/MODELADO. Volatilidad, noticias, producto, horario: ninguna ≥ $500 en el escenario central.

## 2. Por palanca: efecto en puntos de equilibrio y en $/año/cuenta por escenario de WR; esfuerzo; riesgo; qué medir y cuánto tardaría

### 2.1 Ejecución (`resultados_H2.md`, `resultados_G1.md`, `resultados_H1.md`)
- **Lo que el slippage es (derivado, no medido):** con σ(5 min) ≈ 24 ticks en la franja de entrada de MES, **una demora de 1–3 s produce ±1.4–2.4 ticks (1σ)** y 10 s ±4.4; el sondeo de 120 s no se paga (la referencia se toma al actuar). Los +1 y +3 observados (ahora 7 obs.: 0, +1, 0, +3, −1, +1, +3; NO VERIFICADAS) caben en ruido puro; el costo sistemático esperado (medio spread ≈ 0.5 tick) es menor que la dispersión. **N = 7 ⇒ sin potencia** (antes N = 2).
- **Valor de un tick sistemático (P0):** 0 → 4 ticks fijos: neto $2,900 / $2,791 / **$837** / $681 / $455 (equilibrio 47.40 / 47.46 / **49.06** / 49.22 / 49.47 %). El escalón 1→2 ticks vale **−$1,954**. Con finish-line el escalón casi desaparece (−$377 por tick).
- **Anclar al fill** (envío de TP/SL tras el fill, o brackets nativos): si el slippage fuera ruido de media cero con σ 1.4 / 2.4 / 4.4 ticks vale **+$237 / +$472 / +$657 (P0)** y **+$55 / +$153 / +$304 (con finish-line)** por cuenta y año; si fuera un costo fijo de 2–3 ticks, +$1.5k (G1c). **Corrección a G:** el +$1.5k suponía slippage adverso fijo; con ruido simétrico el valor es 3–10× menor. Efecto en el equilibrio: ≈ −0.1 a −0.5 pp. Esfuerzo alto, riesgo medio-alto (ventana de 1–5 s sin TP, o `errorCode 2`). **Brackets nativos:** la doc de ProjectX los trae (`stopLossBracket`/`takeProfitBracket`, ticks, solo con la cuenta en «Auto OCO Brackets»); en el modo por defecto se rechazan con `errorCode 2` **y la orden rechazada igual se crea**; la doc no dice desde dónde se miden los ticks. **Ensayo en Practice: 1 sesión.**
- **Tolerancia / límite marketable:** +$224 a +$344 con una distribución supuesta (σ 1–2): bajo el piso.
- **Salidas:** SL (stop de mercado) y FLATTEN: slip de salida de MGC 3 ticks = −$67/año (+0.05 pp); 6 ticks = −$125 (+0.11 pp). **Combine: el SL no opera (liquidación a 40 ticks) y el sobreimpulso de la liquidación no cuesta efectivo** (la cuenta se cierra; el motor pierde exactamente el colchón). TP (límite): fills parciales/cola: **DESCONOCIDO**. Caso real del 19-oct: **DESCONOCIDO** (sin precio de salida). `exec_exit` en el parche C3 lo medirá.
- **Hora del día** (proxy de Corwin-Schultz, patrón en U): 40 contratos = 0.23 % de la barra a las 8:30 y 0.66 % a las 13:30 en MES. **Cambiar la hora de entrada no cambia P(pasar)** (H3-P5/P6).
- **Esfuerzo / tiempo:** C3 listo (537 pruebas con los otros dos parches); **60 fills para ±0.5 tick de media con σ = 2** ≈ 3 meses; la exportación de TopstepX da una primera lectura en días.

### 2.2 Volatilidad (`resultados_G2.md`, `resultados_H3.md`)
- **Pronosticar el rango funciona** (R²_OOS oro 33.5 %, S&P 54.7 %); **VIX añade +1.7 pp** en índices (único resultado de H3 que sobrevive a Holm, p = 0.017); GVZ +0.3 pp (p = 0.25), día de la semana ≈ 0, hora de entrada (10:30: +1.4 pp, IC [−0.3, +3.3]) sin efecto.
- **Pero no es dinero** (Combine hoy P0 + XFA 3×364; Δ neto $/año/cuenta vs base):

| uso | WR 47.4 | 48.5 | 50 | 52 |
|---|---|---|---|---|
| filtro (operar si el rango pronosticado ≥ barrera) | +172 | −138 | **−558** | −1,377 |
| barreras por ATR | −130 | −49 | +182 | +268 |
| tamaño ∝ 1/rango pronosticado | −116 | +6 | +328 | +790 |

  Premisa refutada: **más sesiones decididas no acelera la XFA, la liquida antes** (los días FLATTEN —56 %— aportan la mitad de los días ganadores ≥ $150). El filtro sube la fracción decidida +44 pp y baja P(≥1 pago) 29 → 26 %; saltar 29–33 % de los días estira el calendario. Efecto en equilibrio: filtro/ATR/tamaño ≈ 0 (ATR: 48.4 % → 48.4 %).
- **Esfuerzo/tiempo:** medio-alto (cambian sizing de capital); no hay nada que medir en vivo antes de decidir: **no recomendado**.

### 2.3 Noticias (`resultados_H4.md`)
- Catálogo verificado en fuente primaria: **FOMC 27–28 oct, 2:00 PM EDT = 1:00 PM CDT** (comunicado del 16-sep: «For release at 2:00 p.m. EDT»); PIB/PCE jue 29-oct 8:30 ET; ECI vie 30-oct; NFP 6-nov; CPI 10-nov; reclamos jueves 8:30 ET (miércoles 25-nov); EIA miércoles 10:30 ET. **No verificados:** PPI, ISM, ventas minoristas, cierres CME (las fuentes discrepan); Topstep: 26-nov 11:45, 27-nov 12:00, 24-dic 12:00 CT.
- Los datos de 7:30 CT caen 15 min **después** de la entrada de MGC y **antes** de la de MES; el FOMC cae **dentro** de la ventana de ambos.
- **Efecto FOMC:** rango de la ventana ×1.30 (MES) y ×1.28 (MGC) (n = 16: ×1.43 en S&P diario, ×1.22 en oro, n = 45–46); en MES **solo ≈ 1 % de los días (0 de 16 en FOMC) sigue abierto a las 13:00 CT**, así que casi no toca al Combine; en MGC **≈ 80 %** sigue abierto: **el FOMC es un riesgo de la XFA, no del Combine de MES**. Rango de la barra de 13:00–13:15: 55 ticks (FOMC) vs 20 (resto).
- **Operar / saltar / reducir:** techo aritmético de saltar ≈ 3 % de los días ⇒ < $110/año/cuenta; reducir tamaño alarga el camino. **Miércoles 28-oct (MES, LARGO): operar normal** (P(TP) 52.8 % [48.5, 56.3]; sin potencia para decir que el FOMC cambia nada; saltar es decisión de aversión al riesgo, no de valor esperado). Reglas de Topstep: XFA verificadas (ventanas 7:25–7:35 y 12:55–13:05/13:25–13:35 CT, solo bloquean **abrir**); **Combine: DESCONOCIDO** (pregunta lista en `resultados_H4.md`).

### 2.4 Producto (`resultados_H5.md`)
- Geometría de MES trasladada al rango de cada producto (liquidación = 0.23 del rango): **MES** 40 ctr., 2 TP; **MGC** ≈ 20 micros (cabe en el tope de 30), 2 TP; **M2K** necesita 70 (tope 50); **MCL** necesita 80 (tope 30), 6 TP y 8.6 % de fricción; **MNQ** ≈ 20 ctr. (tope **NO VERIFICADO**); MYM sin datos locales.
- **Correlación de retornos de la ventana (MEDIDO, 444 días): MES–MNQ 0.97, MES–M2K 0.90, MES–MGC 0.17, MES–MCL 0.13.** Un segundo producto *de índices* no diversifica; **MGC (y MCL) sí.** Dólares por cuenta de un segundo producto: **DESCONOCIDO** (sin geometría validada ni fills); su valor es de riesgo conjunto (G4: P(todas pierden) con 3 cuentas y finish-line 34 % → 13 % con ρ = 0.5 y 4 % con ρ = 0; el ρ de retornos medido, 0.17, cae entre esos dos casos: la correlación entre *resultados* de cuentas no se midió).
- Combine y XFA: pueden diferir (MES para el Combine por liquidez y presupuesto; MGC para la XFA por rango y correlación); no hay evidencia en este repo de un producto mejor para ninguno.

### 2.5 Geometría (`resultados_H6.md`)
- **FLATTEN (56 %):** horarios 10:30 / 12:00 / 13:30 / 14:30 CT: FLATTEN 66.6 / 61.4 / 58.2 / 55.9 %; WR_dec `alternate` 49.4 / 46.9 / 46.2 / 47.4 % (diferencias = ruido de ≈ 215 decididos); cobrado por XFA $634–$640; neto $1,205 / $1,281 / $1,335 / $1,365. **Cerrar antes baja el neto un poco; no hay horario que suba el WR de forma defendible.** Tope duro: plano antes de las 15:10 CT.
- **Razón TP:SL ≠ 1:1:** mueve el WR de equilibrio **mecánicamente** (WR₀ = SL/(TP+SL), de 33 % a 67 %); la comparación válida es la deriva necesaria z*. Resultado (z* base −0.037): (546, 364) −0.048 y (364, 546) −0.050 podrían ser algo mejores (+$340–390 a deriva 0), (485, 243) y (243, 485) iguales; **todas las diferencias son < 0.015 en z* y no tienen bootstrap de días: HIPÓTESIS, no mejora.**
- **Interacciones (neto $/año/cuenta; WR 47.4 / 48.5 / 50 / 52 %):** hoy −1,103 / −38 / 1,365 / 3,836 · finish-line −351 / 851 / 2,361 / 5,037 · P0 + 728×3 −652 / 943 / 2,670 / 5,846 · finish-line + 728×3 **206 / 1,992 / 3,841 / 7,232** · finish-line + 4→1 468 / 1,643 / 3,026 / 5,100. **Solo finish-line + 728×3 (y 4→1) son positivas con el WR medido de 47.4 %.**
- **Barrera efectiva del Combine:** liquidación a 40 ticks, no SL 100 (SL 0.0 %, LIQ 47.2 %); WR de equilibrio del Combine **no es comparable** con el de scripts que usaban SL 100.

### 2.6 Métodos de fondo (`H7_METODOS.md`)
Aplicables y ya usados: triple barrera con empate bien tratado (cotas adversa/favorable), block bootstrap, Holm, HAR, control de drawdown dentro del MLL (finish-line), walk-forward con embargo de 1 día. Aplicables pero redundantes o condicionados: White/SPA, PBO (solo con barridos), GARCH (solo índices), deflated Sharpe (solo si hubiera candidata). **No aplicables con nuestros datos:** microestructura/L2/VPIN, modelo de impacto (40 micros ≈ 0.2–0.7 % de la barra; sin datos para calibrar), Kelly (sin ventaja ⇒ 0), series largas de tick, ML.

### 2.7 Integridad de datos y backtests (H8; `resultados_H8.md`)
- **El defecto de `label_triple_barrier()` está corregido en `main`** (SL primero desde el 25-ago). Los motores de las Partes A–H empatan **a favor de la pérdida**; cota optimista: MGC 0 de 488 días cambian (47.4 % idéntico); MES 5–6 de 492 días (TP 52.8 → 54.1 % LARGO); P(pasar) 20.5 → 21.5 % y neto $1,365 → $1,527 (+$162 como cota superior).
- **Hallazgo nuevo:** el **«81.44 % teórico»** que muestra el scheduler cada día **se reproduce exactamente (81.44 %) y es un artefacto del DLL de $1,000 del simulador legado** (recorta cada día perdedor de −$5,048 a −$1,000); sin DLL da 34.0 %; con las reglas reales (MLL en tiempo real, liquidación a 40 ticks) el motor da **24.4 %** (TP 40) y **29.9 %** (TP 32). **Dejar de compararse contra 81.4 %.** (La cuenta no tiene DLL: NO VERIFICADO en TopstepX.)
- **`economia_historial_cifras_24oct2026.md`: no tengo el archivo** (vive en el Project); pásalo para marcar fila por fila. Mis cifras son reproducibles (47.4 %, fracciones, pass rates, equilibrios, pagos por XFA); el «+7.1 pp del TP 32» y la tabla «17–29 %» provienen del motor `dd_cash`/`dd_wr` (empate ⇒ adverso, conservador); no los recalculé aquí.

## 3. Declaraciones de confianza (formato fijo; ninguna prueba demuestra que algo no existe)
- **Ejecución — anclar al fill / tolerancia:** *Dado lo probado, la probabilidad de que exista un efecto ≥ $500/año/cuenta es **MEDIA** porque* con slippage de ruido σ ≥ 2.4 ticks y sin finish-line el modelo da +$472–657, y con un componente sistemático ≥ 2 ticks da +$1.5k; pero con finish-line ya adoptado baja a +$55–304, y el parámetro que decide (σ, parte sistemática) tiene **N = 7** (antes 2; potencia ≈ 0).
- **Ejecución — hora de entrada, polling, partir en bloques:** **BAJA** porque H3-P5/P6 no ven efecto en P(pasar) (IC95 de ±2 pp con 492 días: no descarta ±2 pp), el sondeo no entra en el slippage y 40 micros no mueven el libro de MES; la potencia solo excluye efectos grandes.
- **Volatilidad — filtro / ATR / tamaño:** **BAJA** porque tres usos con prueba de dinero en cuatro escenarios de WR dan −$558 a +$328 en el escenario central (el único > $500, el tamaño a WR 52 %, supone una ventaja que no tenemos); el pronóstico es real (R² 33–55 %) pero no se traduce en dólares; con 323 días de base el IC de cada diferencia es ±$300 aprox. (sin potencia para < $300).
- **Noticias (FOMC):** **BAJA** porque el techo aritmético es ≈ 3 % de los días (< $110/año) y en MES el 99 % de los días ya está resuelto a las 13:00; con n = 16 no hay potencia para detectar un sesgo del FOMC.
- **Producto:** **BAJA** como fuente de dólares por cuenta (sin geometría validada, sin fills, costos < 1.6 % del rango); **MEDIA** como reducción de riesgo conjunto (ρ MES–MGC 0.17 medida).
- **Geometría — horario de flatten:** **BAJA** (efecto ≤ $160/año, ruido de 215 decididos). **Razón TP:SL:** **BAJA a MEDIA** (+$340–390 a deriva 0 pero con Δz < 0.015 y sin IC de días).
- **Estructurales — 728×3, 4→1 [ACTUALIZADO]:** **ALTA** de que existan en el modelo con ≥ $500 (728×3 +$1,476; 4→1 +$627 con slippage empírico); la incertidumbre es de **reglas** (RTP), del WR operativo con 728×3 (no remedido en vivo) y de que el motor reproduzca la realidad. **Finish-line: MEDIA** (antes ALTA): +$480 con slippage empírico (< $500), +$752 a +$1,201 con la mezcla {1,3} y otros WR; depende de una distribución de slippage con N = 7.
- **Costos operativos [REEMPLAZADO]:** ya no se evalúan como palanca; son escenarios A $240 / B $827 / C pendiente. El $714 anterior era heredado (Parte D), no de una factura.
- **Métodos de fondo:** n/a (no son palancas de dinero).

## 4. Qué exportar o enviar para cerrar los DESCONOCIDOS (ordenado por valor de información por esfuerzo)
1. **Historial de operaciones de TopstepX desde el 5-oct** (MES nc 10 y 40, MEStest, MGC Practice) con precio y hora de entrada **y salida** + los `[OPEN]/[CLOSE]` de Telegram de esos días — *horas de esfuerzo; resuelve σ del slippage, sistemático vs aleatorio (nc 10 vs 40), sobreimpulso de liquidación, fills de TP/SL; decide si anclar al fill vale $55 o $657.*
2. **Aprobar y desplegar C3** (`c3_slippage_timing.patch`, 537 pruebas con los otros dos) — *revisión humana; da tiempos y `exec_exit` de cada operación desde ese día.*
3. **Un ticket a Topstep** con 6 preguntas: (a) ¿el Combine 50K tiene DLL y restricciones de noticias Tier 1?; (b) umbrales de RTP y «compras excesivas»; (c) ¿se puede copiar la misma estrategia en cuentas propias en paralelo? ¿máximo de Combines simultáneos?; (d) ¿se puede elegir el modo de brackets «Auto OCO» en Combine/XFA?; (e) ¿qué incluye el tope de 50 micros y existe tope de MNQ/MYM?; (f) calendario de cierres de CME de 26/27-nov y 24-dic.
4. **Ensayo en Practice de brackets nativos** (1 sesión): semántica de los ticks (¿desde el fill?), modo OCO, comportamiento con `errorCode 2`.
5. **`economia_historial_cifras_24oct2026.md`** y las **facturas** de la API (por cuenta), Railway y la mensualidad del Combine (cerrar el escenario C y ver si el reset de $49 ya incluye la mensualidad: B puede contar doble).
6. **Logs del Pi del 19–23 oct** (`pi_executor.log`): latencia real señal → orden → fill.
7. **Calendarios primarios restantes:** PPI, ISM, ventas minoristas (BLS/ISM/Census) y CME — minutos.

## 5. Correcciones a partes anteriores y límites
- **H1 (cascada) → H1b:** slippage {1,3} sustituido por la distribución de 7 obs.; paso «costos → $0» eliminado; equilibrio de hoy 48.55 % → 47.47 % (A). **G4:** costos operativos ahora por cuenta (G4b). **Explicación del −0.72 pp de 728×3:** el WR no se remidió con esa geometría (`REPORTE_H1b.md` §5).
- **G1c (+$1.5k por anclar al fill)** valía para slippage adverso **fijo** de 2–3 ticks; con ruido de media cero vale $55–657 (H2 §5).
- **«Pass rate vs 81.4 % teórico»** (scheduler): artefacto del DLL; no usar.
- Límites: IC95 del mapa = remuestras de la historia real (no cubren cambios de régimen); la dependencia entre cuentas y el WR de cada escenario son supuestos; sin tick data ni libro; `git push` denegado.
