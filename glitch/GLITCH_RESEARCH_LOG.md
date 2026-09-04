# GLITCH — Research Log
## Quant Research Journal
**Fecha:** 13-ago-2026  
**Deadline:** 6-sep-2026 (24 días hábiles restantes)  
**Objetivo:** Edge estadísticamente robusto para Combine + Cerebro 2 (funded account)

---

## Estado del Arte — Lo que sabemos con certeza

### Dataset disponible
- MES 5min, 2 años: ago-2024 a ago-2026, 34,619 barras RTH
- Fuente: Massive/Polygon, Futures Starter plan ($29/mes, vence sep-2026)
- Cache: `data_cache/mes_5min_2y.parquet`

> **AUDITORIA (25-ago-2026):** el `data_cache/mes_5min_2y.parquet` que existe
> HOY en el checkout fue re-descargado el 25-ago-2026 (39,256 barras RTH,
> distinto conteo al 34,619 citado arriba) — es un dataset DISTINTO al que
> produjo los numeros de esta pagina, no una confirmacion de que sigan
> vigentes. Ningun numero de esta pagina tiene un script en este checkout
> que lo reproduzca exactamente. Regla aplicada sin excepciones (hubo un
> caso confirmado de un numero fabricado por otra sesion de IA colandose
> como real -- $134,174 en el analisis de Cerebro 2): todo numero abajo
> queda marcado **[NO VERIFICADO — posible contaminación de otra sesión,
> no usar hasta reproducir]** hasta que exista un comando/script en este
> repo que lo reproduzca.

### Señales con base estadística real (correlaciones brutas, sin estrategia)
| Factor | r | p-val | Interpretación | Estado |
|--------|---|-------|----------------|--------|
| ret_prev día→día | -0.224 | 0.0000 | Mean-reversion diaria real | [NO VERIFICADO] |
| ret_2d_atras | +0.177 | 0.0001 | Continuación T-2 | [NO VERIFICADO] |
| Autocorr intradiaria lag-1 | -0.012 | 0.031 | MR intradía débil | [NO VERIFICADO] |
| 14:xx lag-1 | -0.063 | 0.0002 | MR fuerte en última hora | [NO VERIFICADO] |
| 9:xx lag-1 | -0.046 | 0.021 | MR apertura | [NO VERIFICADO] |
| 12:xx lag-1 | +0.061 | 0.0000 | MOMENTUM mediodía | [NO VERIFICADO] |

### Estrategias probadas y descartadas
| Estrategia | Walk-forward p | mean_pass (15d) | Veredicto | Estado |
|-----------|---------------|-----------------|-----------|--------|
| S10 ORB Fade | ~0.50 (no testado limpio) | 4.1% | Descartado | [NO VERIFICADO] |
| ORB Breakout | EV negativo todas configs | <47% | Descartado | [NO VERIFICADO] |
| MR día-a-día (base) | p=0.165 | 56.2% (15d) | Insuficiente | [NO VERIFICADO — ver scripts/wf_mr_pure.py, reproduccion fresca del 25-ago-2026 dio p=0.4444, no 0.165, causa aun sin resolver] |
| MR día-a-día (combo_2d) | p=0.081 | 64.8% (15d) / 55.9% (25d) | Candidato débil | [NO VERIFICADO — ver scripts/wf_combo2d.py, reproduccion fresca del 25-ago-2026 dio p=0.4537, no 0.081, causa aun sin resolver] |
| Fade intradía multi-ventana | Bug en WF, EV<0 muestra limpia | Inválido | Descartado | [NO VERIFICADO] |

### Lecciones metodológicas críticas
1. **Nunca reportar muestra completa sin walk-forward** — combo_2d dio 77% en muestra, 56% en WF *(cifras [NO VERIFICADO] — no reproducidas en este checkout, 25-ago-2026)*
2. **Verificar EV simple antes de triple barrier** — el fade intradía tenía EV=-0.000409 simple, el bug de WF lo ocultó *(cifra [NO VERIFICADO])*
3. **La correlación bruta no implica PnL** — r=-0.063 en 14:xx es real pero no se convierte en estrategia rentable directamente *(cifra [NO VERIFICADO], ver tabla de arriba)*
4. **La geometría del video (RR=0.33, WR=75%) es EV=0 sin edge** — solo funciona si la señal tiene esa geometría natural. *(Este principio SI fue re-verificado el 25-ago-2026 contra MES real con el bug de barreras ambiguas corregido — ver scripts/revalidate_geometry_table.py: WR empirico para RR=0.33 fue 71.7%, no exactamente 75%, con sesgo sistematico documentado abajo. El principio cualitativo se sostiene; el numero exacto no.)*
5. **p<0.05 en WF con N_trades>200 es el criterio mínimo** — no negociable *(regla metodologica, no un numero a verificar — sigue vigente; ninguno de los dos candidatos reproducidos el 25-ago-2026 la cumple: combo_2d N=193, MR-pura N=501 pero p=0.44 en ambos)*

---

## Lo que NO hemos probado correctamente

### Pendiente prioritario 1: MR intradía en 14:xx limpio
- La correlación r=-0.063 es real (p=0.0002, N=3,455)
- El intento anterior tenía bug: EV simple era negativo porque `ret_prev` cruzaba días
- **Hipótesis sin validar:** ¿el fade barra-a-barra en 14:xx tiene EV positivo cuando se implementa correctamente (solo dentro del mismo día, sin cruzar)?
- Prueba requerida: EV simple limpio → si positivo → triple barrier → walk-forward

### Pendiente prioritario 2: Momentum en 12:xx
- r=+0.061 en mediodía es la correlación más fuerte de todas (p=0.0000)
- Nunca se probó como estrategia de continuación
- **Hipótesis:** seguir la dirección de la barra de 12:xx en vez de faderla

### Pendiente prioritario 3: Combinación señal día-a-día + hora
- combo_2d (WF p=0.081) tiene algo real pero insuficiente solo
- ¿Condicionarlo a que la señal ocurra en una hora específica sube el WR?
- Ejemplo: solo operar combo_2d si la primera hora confirma la dirección

### Pendiente prioritario 4: MNQ como confirmación
- Si la MR día-a-día es real en índices, debería aparecer en MNQ también
- Si NO aparece en MNQ: sospecha de idiosincrasia/ruido de MES específicamente
- Costo: $0 adicional (ya tenemos acceso Massive)

---

## Cerebro 2 — Funded Account (NO iniciado)

**Estado actual:** No hay ni una línea de código de investigación para la fase funded.

**El problema del Cerebro 2 es diferente al del Combine:**
- Combine: maximizar probabilidad de llegar a $3,000 antes de tocar el floor
- Funded: maximizar EV realizado neto bajo restricciones de Topstep XFA
  - Sin profit target (no hay $3,000 que alcanzar)
  - Sin trailing MLL (el floor no sube)
  - Regla de consistencia: mejor día <40% del total
  - Payout trigger: 5 días ganadores de $150+ O balance ≥ $55k
  - Max payout: $5,000 por retiro (90/10 split)

**Implicación:** la estrategia óptima para el Cerebro 2 NO es la misma que para el Combine.
- En el Combine queremos pocas trades de alto impacto (minimizar varianza del camino)
- En funded queremos muchos trades de bajo riesgo (acumular días ganadores de $150+)
- Específicamente: con 10 contratos MES, necesitamos $150/día = 3 puntos de ganancia
- Eso es un TP de 3 puntos con cualquier WR razonable

**Preguntas sin responder para Cerebro 2:**
1. ¿Cuántos días ganadores de $150+ podemos esperar con cada estrategia candidata?
2. ¿Cuál es el EV realizado neto (después de payouts) por cuenta por mes?
3. ¿Cómo se comporta la regla de consistencia con la estrategia elegida?
4. ¿Cuál es el tiempo esperado entre payouts?

---

## Plan de trabajo — 24 días hábiles hasta 6-sep-2026

### Semana 1 (13-19 ago): Validar señales intradía limpias
- [ ] Día 1: EV simple limpio de 14:xx fade (sin cruzar días)
- [ ] Día 2: EV simple limpio de 12:xx momentum
- [ ] Día 3: Walk-forward de lo que tenga EV>0
- [ ] Día 4: MNQ como confirmación de señal día-a-día
- [ ] Día 5: Documentar veredicto — ¿hay algo que supere p<0.05?

### Semana 2 (20-26 ago): Combinaciones y Cerebro 2
- [ ] Día 1-2: Combinar mejor señal intradía con combo_2d
- [ ] Día 3-4: Primer diseño de Cerebro 2 (reglas XFA, sizing, trigger de payout)
- [ ] Día 5: Monte Carlo del Cerebro 2 con datos reales

### Semana 3 (27 ago - 2 sep): Decisión de Combine
- [ ] Si hay estrategia con WF p<0.05 y mean_pass≥70%: preparar para pagar
- [ ] Si no: evaluar pagar con combo_2d (p=0.081, mean_pass=56%) como experimento controlado
- [ ] Documentar criterio de decisión explícito antes de pagar

### Semana 4 (3-6 sep): Cierre y setup
- [ ] Commit de todo el código de investigación al repo
- [ ] Actualizar Railway con estrategia final
- [ ] Decisión final: pagar o no pagar el Combine

---

## Criterios de decisión explícitos (no negociables)

### Para pagar el Combine:
- **Mínimo aceptable:** WF p<0.10 Y mean_pass≥60% en 25 días
- **Preferido:** WF p<0.05 Y mean_pass≥70% en 25 días
- **Si no se alcanza para el 6-sep:** pagar de todas formas con combo_2d y documentar que es un experimento, no certeza

### Para activar Cerebro 2:
- Estrategia con ≥3 días ganadores de $150+ esperados por semana
- Blow rate en funded <20% en 90 días de simulación
- Consistencia verificada: nunca viola regla del 40%

---

## Próximo experimento — INMEDIATO

**Exp-001: EV simple limpio de 14:xx fade**
- Hipótesis: r=-0.063 en 14:xx se convierte en EV>0 cuando se implementa correctamente
- Método: calcular `ret_prev` solo dentro del mismo día, sin cruzar días
- Criterio de éxito: EV simple >0 con t-test p<0.05
- Si pasa: proceder a triple barrier y walk-forward
- Si falla: descartar señal 14:xx definitivamente

---

## Consolidación — Camino B: geometría pura (25-ago-2026)

A diferencia de todo lo demás en este log, lo que sigue **SÍ tiene script
reproducible en este checkout** (listado en cada sección) y fue corrido
sobre datos reales descargados el mismo 25-ago-2026 — no hereda el
`[NO VERIFICADO]` del resto del documento. Contexto completo: bug de
barreras ambiguas (`simulation/triple_barrier.py`) confirmado y
corregido, `combo_2d`/MR-pura NO reprodujeron el p=0.149 histórico (ver
tabla de arriba, sigue sin resolver — Camino B no depende de eso, es
edge-free por diseño).

### Candidato ganador MES/MNQ

- **Geometría:** SL=100/TP=40 ticks (RR=0.40), triple-barrier ATR NO
  aplica aquí — son ticks fijos, no ATR-escalados
- **Dirección:** alternar (no direccional — el sesgo direccional
  encontrado es ruido, ver abajo)
- **nc=40** (no 50 — doble margen de seguridad: límite duro de Topstep
  + sospecha de sobreajuste en la dimensión dirección)
- **Resultado:** WR≈70.6% (punto medio del bracket empírico
  optimista/conservador), pass_rate≈81.6%, blow_rate≈18.5%,
  **53.6 combines/año**, ~3.8 días promedio de resolución
- Reproducir: `scripts/camino_b_direction_check.py` (geometría "G2")

**Sesgo direccional (always_short vs. alternar):** +0.24 a +0.75
combines/año (0.6-1.4% relativo), consistente en ambas mitades
temporales, pero del mismo orden que el error estándar del WR a ese N de
trades (~0.32pp) — se lee como ruido con signo consistente por azar, no
como edge real. No se usó para el candidato final.

### Extensión a 6 productos (7 pedidos, MBT excluido por hueco de datos
de 13 meses — ver `scripts/camino_b_products.py`)

> **BUG encontrado y corregido (25-ago-2026, mismo día):** el primer
> corrido de esta tabla tenía ZC con `tick_size=0.0025` (dólares/bushel)
> aplicado a un feed de precios cotizado en CENTAVOS/bushel (close~437 =
> $4.37) — mismatch de unidades de 100x, específico de ZC porque es el
> único de los 6 productos cotizado en centavos en vez de dólares/puntos/
> indice directamente. El labeling de win/loss de barras no se vio
> afectado (se cancelaba internamente en términos de distancia de
> precio), pero `avg_win_usd`/`avg_loss_usd` sí — inflados 100x, lo que
> hacía que un solo trade casi siempre pasara o quebrara la cuenta de
> inmediato. Eso es lo que producía el 55.7 combines/año original y el
> "ZC lidera" — un artefacto de bug, no una señal real. Corregido
> (`tick_size=0.25`) y re-corrido. Los otros 5 productos se verificaron
> contra su unidad de cotización natural (ZN en puntos, MGC en $/oz, M6E
> en tasa decimal, M2K en puntos de índice, MCL en $/barril) — todos
> consistentes, sin el mismo problema.

| Producto | Familia | RR | nc | combines/año | Lectura |
|---|---|---|---|---|---|
| MES/MNQ | Equity index | 0.40 | 40 | **53.6** | consistente, sesgo despreciable (~1%) |
| GC/MGC (Gold) | Metales | 0.33 | 30 | **52.7** | consistente, sesgo despreciable |
| RTY/M2K (Russell) | Equity index (control) | 0.40 | 50 | **51.9** | consistente, sesgo despreciable — a 1.4% de Gold, esencialmente empatados |
| CL/MCL (Crude) | Energía | 0.40 | 30 | 48.2 | consistente, sesgo moderado (4-8%) |
| 6E/M6E (Euro FX) | FX mayor | 0.50 | 50 | 37.4 | consistente, sesgo **~10% — el más grande de la sesión, marcar para escrutinio futuro** |
| ZN (10Y Note) | Tasas | 0.50 | 5 | 21.4 | dirección NO consistente entre mitades — usar alternar |
| ZC (Corn) | Agrícola | 0.48 | 5 | 14.1 | **último lugar, ya corregido** — dirección tampoco consistente. Handicap estructural: nc≤5 (sin micro-contrato) no genera suficiente velocidad de $ contra el profit target fijo de $3,000, igual que ZN |

Reproducir: `scripts/camino_b_products.py` → `data_cache/camino_b_products_grid.csv`,
`_overfit.csv`, `_final.csv` (versionados en git, no son output efímero).

### Conclusión explícita

**Camino B queda validado como fenómeno de geometría/estructura de
payout del Combine, NO de microestructura específica de un instrumento
— con una salvedad importante que el bug de ZC dejó más clara, no
menos.** Cuatro familias de activos completamente distintas — equity
index (control), metales, energía, y el propio MES/MNQ — con drivers,
horarios de liquidez y comportamiento de participantes totalmente
diferentes entre sí, caen todas en la misma banda de 48-54 combines/año
bajo la misma regla de barrera fija sin señal predictiva. Eso es
exactamente lo que predice la premisa original de Camino B (WR≈SL/(SL+TP)
por geometría de gambler's ruin, no por edge de ningún activo particular).

La salvedad: ZN y ZC (los dos con nc≤5, sin micro-contrato disponible)
quedan bien por debajo de esa banda (21.4 y 14.1) — no porque la
geometría falle ahí, sino porque el profit target de $3,000 es fijo en
dólares mientras el tamaño de posición disponible no escala con el
instrumento. La conclusión correcta no es "la geometría funciona en
cualquier producto" sino **"la geometría funciona en cualquier producto
con suficiente nc disponible (vía micro-contrato o point-value alto) para
generar velocidad de $ comparable al profit target fijo"** — un matiz
que el bug original (que hacía ver a ZC como ganador) habría escondido
por completo.

La única grieta real: 6E muestra un sesgo direccional (~10%,
consistente en ambas mitades) más grande que cualquier otro producto,
incluyendo MES. Si eso se llegara a confirmar como edge real (no se ha
intentado romperlo todavía — mismo estándar que el resto de la sesión,
donde cero "edges" sobrevivieron escrutinio), Camino B dejaría de ser
"sin necesidad de edge" para ESE producto específico. No se ha
construido nada sobre esto — queda anotado, no usado.

### Paso F — módulo de producción (25-ago-2026)

Construido, agnóstico de producto, pendiente de revisión antes de
conectar a Railway:

- `strategies/geometry_pure.py` — única fuente de verdad de la lógica de
  decisión (dirección, cálculo de barreras), importada tanto por el
  scheduler como por cualquier backtest futuro. `CANDIDATES` registra
  MES (activo, ganador validado), MGC y M2K (specs cargadas, `yf_ticker`
  sin verificar — el scheduler se niega a correr esos productos hasta
  que se verifique un símbolo real de feed en vivo, no se adivina)
- `scheduler/geometry_scheduler.py` — loop de producción/paper. Rotar de
  producto = cambiar `GLITCH_PRODUCT` (env var), no reescribir código
- `execution/contracts.py` — resolución dinámica de front-month
  (`resolve_front_month()`), ahora compartida también por
  `combo2d_scheduler.py` (antes tenía su propia copia)
- `tests/test_geometry_parity.py` — 18 tests: identidad de función
  compartida, aritmética de barreras/dólares, nc nunca excede el cap
  real de Topstep por producto, sin key hardcodeada, **swappability real
  de producto** (ver abajo)
- `DRY_RUN=true` por default — paper trading, sin excepción, hasta
  decisión explícita separada

#### MES es el default — por qué, explícitamente (25-ago-2026)

**MES es el default por menor incertidumbre residual (mayor tiempo de
validación acumulado en la sesión), NO por ser la geometría con mejor
número.** GC/MGC y RTY/M2K están a 1-3% de diferencia en `combines_por_año`
— dentro del margen de ruido de los brackets empíricos (ver sección de
6 productos arriba). Esto es un requisito PERMANENTE del diseño, no un
detalle de implementación: cualquier decisión futura de cambiar el
default debe justificarse con evidencia nueva, no con la conveniencia de
"ya está configurado así".

**Swappability confirmada con test real, no solo con el diccionario:**
`tests/test_geometry_parity.py::TestProductSwappability` reimporta el
scheduler completo (`importlib.reload`) con `GLITCH_PRODUCT=MGC` ("GC"
en la conversación) y `GLITCH_PRODUCT=M2K` ("RTY") vía env var únicamente
— sin tocar código. Ambos casos llegan correctamente hasta el gate de
`yf_ticker` (que los detiene ahí porque ese símbolo de feed en vivo
todavía no está verificado — ver arriba) y NO antes ni por otra razón,
probando que el mecanismo de swap en sí funciona de punta a punta. Un
cuarto test confirma que volver a `GLITCH_PRODUCT=MES` deja el módulo en
estado limpio después del reload. 4/4 tests pasando.

#### Duración recomendada del período de paper trading (25-ago-2026)

Números del candidato ganador (G2: SL=100/TP=40 ticks, alternar, nc=40,
max_holding_bars=100), separados explícitamente por primera vez —
reproducir con el bloque de código en el historial de esta sesión
(usa `scripts/camino_b_grid.py::measure_wr_bracket` +
`simulation/monte_carlo.py::TopstepMonteCarloSimulator`, n_paths=8000, seed=42):

- `pass_rate_15d` = **0.8144**
- `avg_pass_days` (solo intentos que pasan) = 3.8361
- `avg_blown_days` (solo intentos que truenan) = 2.8721
- **`dias_promedio_resolucion`** (TODOS los intentos que se resuelven,
  pase o truene — el número correcto para este cálculo, no el de solo-pases)
  = **3.6571**
- `n_alive` a los 15 días (ni pasó ni tronó) = 0 de 8,000 paths (0.00% —
  cada intento se resuelve dentro de la ventana, no hay paths censurados)

> **Nota técnica:** `avg_pass_days` (usado en reportes anteriores de esta
> sesión para "días promedio de resolución") NO es el número correcto
> para este cálculo — solo promedia los intentos que pasan, que tardan
> más que los que truenan (3.84 vs 2.87 días). `avg_resolution_days`
> (nuevo, agregado a `simulation/monte_carlo.py::SimResult` en esta
> misma sesión) promedia TODOS los intentos resueltos. La diferencia
> importa: usar el número equivocado habría sobreestimado el tiempo
> esperado en ~5%.

**Cálculo:**
```
intentos_esperados_para_pasar = 1 / pass_rate_15d
                               = 1 / 0.8144
                               = 1.2279

dias_calendario_esperados = dias_promedio_resolucion × intentos_esperados_para_pasar
                           = 3.6571 × 1.2279
                           = 4.49 días
```

**Comparación contra el límite de 60 días:** 4.49 días vs. 60 días —
**13.4x de margen.** Cae extremadamente cómodo bajo el límite.

**Duración recomendada de paper trading: 30 días calendario** (no 4.49
días redondeados hacia arriba mecánicamente). Justificación: 4.49 días es
el tiempo *estadísticamente esperado* para pasar UN intento, pero un
período de paper trading sirve para más que confirmar el número
esperado — necesita observar ejecución real (slippage del feed, fiabilidad
del roll dinámico de contrato, comportamiento del alerta de vencimiento)
a través de **múltiples ciclos completos de intento**, no solo el
esperado. 30 días ≈ 6.5 ciclos completos al ritmo esperado, con margen
de sobra para ciclos más lentos que el promedio, y sigue dejando 30 días
adicionales de colchón contra el límite de 60.

#### Verificación de unidades de MES contra CME (25-ago-2026)

Re-verificado desde cero, no reusado de sesiones anteriores (mismo
chequeo que encontró el bug de ZC):

- **Fuente:** CME Group, especificaciones oficiales de Micro E-mini
  S&P 500 (`cmegroup.com/markets/equities/sp/micro-e-mini-sandp-500.contractSpecs.html`
  — la página de CME no permitió fetch directo, bloqueado por su propia
  protección anti-bot; confirmado en su lugar por múltiples fuentes
  independientes que citan esa página — Ironbeam, QuantVPS, DamnPropFirms
  — todas coinciden exactamente)
- **Multiplicador:** $5 × índice S&P 500
- **Tick size:** 0.25 puntos de índice
- **Tick value:** **$1.25/tick** — coincide con `tick_value_usd=1.25` ya
  usado en `strategies/geometry_pure.py`
- **Verificación empírica independiente** (mismo diagnóstico que
  destapó el bug de ZC, corrido contra `data_cache/mes_5min_2y.parquet`):
  100% de los precios de cierre observados en 39,967 barras son múltiplos
  exactos de 0.25 — el feed de precios real usado en todo el backtest de
  esta sesión es consistente con tick=0.25 sin excepción.

**Valor confirmado: correcto, sin cambios necesarios.**

#### Cerebro 1 vs. Cerebro 2 — aclaración explícita (25-ago-2026)

**>>> Este Paso F resuelve ÚNICAMENTE Cerebro 1 (pasar el Combine). <<<**

Cerebro 1 = pasar el Combine. Objetivo: maximizar `pass_rate/dias_resolucion`
dentro de una ventana ACOTADA de 15 días, con pérdida limitada a la fee
del intento (~$49-149). La geometría de este módulo (Camino B) explota
que esta ventana acotada + pérdida acotada permite pasar con alta
probabilidad AUNQUE la estrategia subyacente pierda dinero en promedio
(EV negativo neto de comisión) — la convexidad del payout hace el
trabajo, no una predicción de mercado.

Cerebro 2 = maximizar payouts reales una vez fondeado (cuenta XFA).
Objetivo DISTINTO: el horizonte es INDEFINIDO (sin ventana de 15 días que
acote el riesgo), y el umbral relevante no es "$3,000 acumulados" sino
"5 días de ≥$150 netos". Una estrategia con EV negativo o cero que
funciona para pasar el Combine NO sobrevive en Cerebro 2 — sin la
ventana de tiempo que te protege, el MLL eventualmente alcanza cualquier
estrategia sin edge real positivo.

Cerebro 2 está PAUSADO porque depende de una pregunta sin resolver: ¿el
MLL de la cuenta XFA se resetea a $0 SOLO la primera vez que se solicita
un payout, o CADA vez? Esto se reportó una vez (fuente: help.topstep.com,
cita parcial) pero NUNCA se verificó el texto completo ni la URL exacta
contra la fuente oficial. Son dos economías completamente distintas para
Cerebro 2 y no se puede diseñar nada confiable sin resolver esto primero.

**Regla práctica:** si una tarea es sobre pasar el Combine (geometría de
ticks, `combines_por_año`, `pass_rate_15d`) es Cerebro 1 — procede. Si es
sobre payouts, XFA, `simulate_xfa_lifetime`, o el colchón post-payout —
es Cerebro 2 — DETENTE y pregunta antes de avanzar, no asumas que el
éxito de Cerebro 1 aplica ahí.

Misma aclaración duplicada, palabra por palabra en espíritu, en los
comentarios de cabecera de `strategies/geometry_pure.py` y
`scheduler/geometry_scheduler.py`.

#### Criterio de graduación a DRY_RUN=false (25-ago-2026)

30 días sin errores técnicos NO es suficiente por sí solo. Criterio
agregado — **ambos** deben cumplirse:

1. 30 días calendario transcurridos sin errores técnicos (crashes,
   fallos de resolución de contrato, fallos de feed no recuperados)
2. **El `pass_rate` empírico observado en paper** (sobre todos los
   ciclos que se completen en esos 30 días — a ~3.66 días/ciclo
   promedio, se esperan ~8 ciclos, N pequeño) **debe estar dentro de
   ~15-20 puntos porcentuales del 81.4% teórico** (es decir, no bajar de
   ~61-66% empírico). Si cae más abajo que eso, es señal de que algo en
   producción real (slippage del feed, timing de ejecución contra el
   backtest de 5min) está erosionando la geometría — **no se pasa a
   `DRY_RUN=false` aunque los 30 días ya hayan transcurrido sin errores
   técnicos.** Revisar la causa antes de reconsiderar.

Este criterio vive por ahora solo en este documento — es una decisión
humana al final del período de paper, no algo que el scheduler evalúe
automáticamente todavía.

#### Despliegue a Railway — bloqueado en este ambiente, paquete listo (25-ago-2026)

**No se pudo conectar a Railway desde esta sesión: sin CLI de Railway
instalado, sin credenciales configuradas, sin git remote apuntando al
repo que Railway vigila.** Nada de lo que sigue se pudo ejecutar
directamente — es la preparación para que el usuario (u otra sesión con
acceso) lo haga.

**Inconsistencia encontrada en la configuración de deploy — 4 archivos,
3 comandos de arranque distintos:**

| Archivo | Comando de arranque |
|---|---|
| `nixpacks.toml` (raíz) | `python glitch/scheduler/glitch_scheduler.py` |
| `Procfile` (raíz) | `python glitch/scheduler/combo2d_scheduler.py` |
| `glitch/Procfile` | `python scheduler/glitch_scheduler.py` |
| `glitch/railway.json` | `python scheduler/glitch_scheduler.py` |

**Cuál gobierna el deploy real de combo2d hoy en Railway: DESCONOCIDO,
pendiente de confirmar por el usuario en el dashboard.** No se puede
inferir de forma confiable desde los archivos locales — 3 de los 4
apuntan a `glitch_scheduler.py` (no `combo2d_scheduler.py`, que es el
que el usuario confirmó que corre en Railway hoy en DRY_RUN).

**Corrección (25-ago-2026, mismo día):** la especulación original de
arriba — que el servicio activo probablemente tiene un Start Command
manual configurado en el dashboard, ignorando estos 4 archivos — quedó
DESCARTADA por el usuario al revisar directamente: **el Start Command
del servicio combo2d en Railway está VACÍO.** Eso significa que Railway
sí está leyendo alguno de los 4 archivos de config del repo, no un
override manual. Con 3 de 4 apuntando al script viejo
(`glitch_scheduler.py`) y siendo `combo2d_scheduler.py` el que
realmente corre, hay una discrepancia sin explicar — pendiente de que
el usuario confirme el **Root Directory** configurado en el dashboard
de Railway antes de cualquier push (si el Root Directory del servicio
está fijado a `glitch/`, por ejemplo, cambia por completo cuál de estos
4 archivos ve Railway y con qué rutas relativas). **No modificar
`nixpacks.toml` ni `glitch/Procfile` todavía** — solo el `Procfile` raíz
fue tocado (línea `worker-geometry` agregada, la de combo2d intacta).
**No proceder con push ni con la creación del segundo servicio hasta
que esto se resuelva.**

**Preparado, sin tocar la configuración de combo2d:**

- `Procfile` (raíz) — agregada una línea nueva, la de combo2d intacta:
  ```
  worker: python glitch/scheduler/combo2d_scheduler.py
  worker-geometry: python glitch/scheduler/geometry_scheduler.py
  ```
  Esto por sí solo NO crea un servicio nuevo en Railway — Railway
  necesita que el usuario cree explícitamente un segundo servicio
  apuntando a este mismo repo, y le asigne `worker-geometry` (o un
  Start Command manual equivalente) en su propia configuración. Dado
  que no se pudo confirmar qué archivo gobierna el deploy real, la
  ruta más segura para el usuario es fijar el Start Command a mano en
  el nuevo servicio, no confiar en que Railway detecte el Procfile
  automáticamente.

- **Variables de entorno requeridas para el servicio nuevo** (mismos
  nombres que combo2d, mismo patrón fail-loud si faltan — ver
  `execution/contracts.py` y `scheduler/telegram_bot.py`):
  - `MASSIVE_API_KEY` (o `POLYGON_API_KEY`)
  - `TELEGRAM_BOT_TOKEN`
  - `TELEGRAM_CHAT_ID`
  - `DRY_RUN=true` (default del código si no se setea, pero fijarla
    explícita en Railway evita ambigüedad)
  - `GLITCH_PRODUCT=MES` (default del código, mismo motivo)

- **Cron sugerido:** `25 14 * * 1-5` (9:25 AM CT L-V) — mismo horario
  que combo2d, punto de partida razonable dado que la entrada espera a
  las 9:30 CT internamente igual que combo2d. Ajustar si en algún
  momento ambos servicios necesitan coordinarse contra la MISMA cuenta
  real (no aplica todavía — los dos siguen en DRY_RUN).

**Confirmado antes de dejar esto listo para push:** suite completa
(96/96) pasando, `grep` de secretos limpio en todo el checkout (ver
comando abajo, repetir antes de cualquier push real).

```bash
grep -rn "6F2vDNs8WtwPJLl_TtnWSksMzYPFtdYs\|AAHdGlnbM0ACf6HvUS67f74tWaNowuUtsY" . 2>/dev/null | grep -v "assert\|not in src"
```

**No se hizo push a ningún remote — no hay remote configurado.**
Cuando el usuario conecte Railway (o dé acceso a esta sesión), el
siguiente paso es: confirmar el Start Command real de combo2d en el
dashboard, crear el servicio nuevo con las env vars de arriba, y
recién ahí evaluar el push.

### Persistencia de estado — hallazgo crítico (27-ago-2026)

**Confirmado en el dashboard de Railway: los servicios "Cron Schedule"
(GEOMETRY y, casi con certeza, COMBO2D — mismo tipo de servicio) no
tienen sección de Volumes disponible. El filesystem es efímero entre
ejecuciones del cron.**

Ambos schedulers guardaban su historial de trades (`combo2d_log.json`,
`geometry_{producto}_log.json`) en un archivo JSON local, leído/escrito
con `open()` plano. Con filesystem efímero, ese archivo se reseteaba a
cero en **cada** ejecución del cron — nunca acumuló nada entre días.

**Consecuencia — leer con cuidado antes de confiar en cualquier reporte
histórico de Telegram de cualquiera de los dos schedulers:**
- Cualquier "Día X de paper" reportado por GEOMETRY antes de este fix
  siempre fue "Día 1" en la práctica, sin importar cuántos días
  llevara corriendo.
- Cualquier "Resultado de ayer" reportado por GEOMETRY antes de este
  fix siempre fue "(sin ciclo previo registrado)".
- Cualquier "pass_rate acumulado" (GEOMETRY) o "Win Rate"/"PnL Total"
  (COMBO2D) reportado por Telegram antes de este fix reflejaba **como
  máximo el ciclo de un solo día**, nunca una acumulación real —
  aunque el mensaje se leyera como si fuera un total histórico.
- **CORRECCIÓN (01-sep-2026), con evidencia de `git log`/`git show` y del
  historial real de Cron Runs de Railway — reemplaza la nota anterior,
  que subestimaba el problema:** no es solo que los datos de COMBO2D
  sean "no confiables como serie histórica" por el filesystem efímero.
  **El servicio COMBO2D no ha ejecutado exitosamente NI UNA VEZ desde
  el 2026-08-13 — 12 ejecuciones consecutivas fallidas confirmadas en
  Railway, del 2026-08-14 al 2026-09-01, cada una crasheando en 3-4
  segundos (falla de importación, antes de llegar a `run()`).** No hay
  "datos contaminados" que reinterpretar — no hay datos en absoluto
  para ese período. Cronología completa reconstruida:

  | Fecha (UTC) | Commit | Qué pasó |
  |---|---|---|
  | Jul 8 – Aug 13 | — | El servicio corría `glitch_scheduler.py` — un script **distinto y anterior**, no combo2d. Confirmado via `git show e0b1ea3:Procfile`. Las corridas exitosas de 15-19 min de este período no tienen relación con combo2d. |
  | Aug 13, 21:31 | `1a3b714` | `combo2d_scheduler.py` creado; Procfile apuntado a él por primera vez |
  | Aug 13, 23:58 | `cb070a5` | Cambia a `massive`/`RESTClient` para datos — pero `massive` NUNCA estuvo en el `requirements.txt` de la raíz |
  | Aug 17, 14:45 | `321c747` | "fix: add massive to scheduler requirements" — agregó `massive` a `glitch/scheduler/requirements.txt` (confirmado via `git show 321c747`), el archivo QUE ESTE SERVICIO (Railpack) no lee. El fix nunca tuvo efecto real. |
  | Aug 17 – Aug 26 | — | **9 días sin ningún commit** — el servicio fallando en silencio, sin que nadie lo notara |
  | Aug 26-27 | `99497ec` | Merge del hardening de seguridad de esta sesión (sin fallback hardcodeado de Massive/Telegram) — pero `massive` seguía faltando del archivo correcto, así que la ejecución seguía muriendo ANTES de llegar al nuevo chequeo de Telegram |
  | Aug 28 | `44f07cf` | Fix del archivo correcto (`requirements.txt` de la raíz) — primera vez desde el 13-ago que el import de `massive` se resuelve |
  | Aug 31 | (deploy en curso) | Con el import resuelto, la ejecución llega por primera vez al siguiente requisito sin cumplir — el token de Telegram — y ahí aparece el error nuevo |

  **Conclusión explícita: el hardening de seguridad de esta sesión (que
  removió los fallbacks hardcodeados) NO es la causa original de esta
  falla — es una causa preexistente desde el 17-ago (un fix que tocó el
  archivo equivocado), sin relación con nada hecho en esta sesión hasta
  el 26-ago. Lo que el hardening sí hizo fue apilar un segundo requisito
  (variables de Telegram) detrás del primero, que solo se volvió visible
  una vez que el primer bloqueo (el import de `massive`) se resolvió de
  verdad el 28-ago.** Cualquier "Win Rate" o "PnL Total" de COMBO2D
  reportado por Telegram entre el 14-ago y hoy debe tratarse como
  **inexistente, no como dato contaminado** — el servicio simplemente no
  corrió.

**Fix aplicado:** `execution/gist_store.py` (nuevo, única fuente de
verdad de persistencia para ambos schedulers) reemplaza el filesystem
local por un Gist privado de GitHub vía la API REST. Mismo
`load_log()`/`save_log()`, mismos call sites en `combo2d_scheduler.py`
y `geometry_scheduler.py` — solo cambia el mecanismo de I/O. Requiere
dos variables de entorno nuevas por servicio:
- `GITHUB_GIST_TOKEN` — Personal Access Token **nuevo y separado**,
  scope **únicamente** `gist` (nunca `repo`, nunca reusar el token de
  push al repo)
- `GIST_ID` — id del gist privado ya creado, con dos archivos
  (`combo2d_log.json`, `geometry_mes_log.json`)

Filosofía de fallos (deliberadamente asimétrica, ver docstring del
módulo): configuración ausente → `RuntimeError` inmediato, no debe
arrancar un scheduler creyendo en silencio que está en su día 1. Fallo
de red/API transitorio en una corrida bien configurada → se loguea
pero no tumba el scheduler (el trade del día ya se ejecutó y notificó
para cuando se llama `save_log()`).

**Alternativas evaluadas y descartadas antes de elegir Gist** (ver
turno anterior de esta sesión para el detalle completo):
- Volumes de Railway: confirmado que no está disponible para este tipo
  de servicio, no hay botón que se nos haya pasado.
- Leer el historial propio del bot vía Telegram `getUpdates`:
  **técnicamente inviable**, no una alternativa "frágil" — la API de
  Bots de Telegram nunca devuelve al bot sus propios mensajes enviados
  vía `getUpdates`, confirmado contra documentación/discusión oficial.

**Tests:** `tests/test_gist_store.py` (10 tests, sin red real —
`requests.get`/`requests.patch` mockeados) + tests de integración en
`test_combo2d_parity.py`/`test_geometry_parity.py` confirmando que
`load_log()`/`save_log()` de cada scheduler delegan al filename
correcto dentro del gist compartido. Suite completa: 110/110 pasando.

**Pendiente antes de confiar en esto en producción — NO pusheado
todavía:** el usuario va a generar el token nuevo y crear el gist
privado; después de eso, correr una prueba manual conjunta antes de
confiar en que funciona (ver `scripts/setup_gist_store.py` para crear
el gist con la estructura correcta). El conteo de 30 días de paper de
Cerebro 1 sigue bloqueado hasta que esto quede confirmado funcionando
de punta a punta.

### Chequeo unificado de arranque — blindaje contra "un fallo a la vez" (01-sep-2026)

**Motivo:** 2.5 semanas (14-ago a 01-sep-2026) de fallos en COMBO2D
descubiertos uno a la vez vía crash-arreglo-siguiente-crash — cada
variable de entorno faltante se validaba en un módulo distinto
(`execution/contracts.py` al importarse, `scheduler/telegram_bot.py`
al importarse, `execution/gist_store.py` solo cuando `load_log()`/
`save_log()` se llamaban ya bien entrada la ejecución), así que
arreglar una revelaba la siguiente en la corrida del día siguiente, no
en la misma.

**Fix:** `execution/env_check.py`, nuevo, con una única función
`require_env(required, scheduler_label)`. Se llama en la primera línea
útil de `combo2d_scheduler.py` y `geometry_scheduler.py` — **antes**
de `scheduler.telegram_bot`, `execution.contracts`, y
`execution.gist_store` — verifica TODAS las variables requeridas de un
jalón y, si falta cualquiera, manda **un solo mensaje** a Telegram
listando todas juntas antes de salir. Deliberadamente sin depender de
ninguno de esos tres módulos (para no disparar sus propios chequeos
individuales antes de llegar al chequeo unificado) — usa `requests`
directo para el envío, duplicando 5 líneas a propósito.

Inventario completo de variables requeridas por ambos schedulers
(idéntico para los dos): `MASSIVE_API_KEY` o `POLYGON_API_KEY`,
`TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `GITHUB_GIST_TOKEN`,
`GIST_ID`. (`DRY_RUN`, `NC`, `GLITCH_PRODUCT` tienen default seguro en
código, no son requisitos duros.)

**Verificado, no solo revisado:**
- `tests/test_env_check.py` (6 tests) — incluye el caso central: 4
  variables faltantes a la vez se reportan las 4 juntas, no solo la
  primera.
- Tests de integración nuevos en ambos `test_*_parity.py` —
  reimportan el scheduler completo con varias variables borradas,
  confirman `SystemExit` con todas reportadas.
- **Smoke test de build real (Railpack, no nixpacks)**: import de
  `combo2d_scheduler.py` en un entorno limpio (`env -i`) con
  exactamente las 7 variables que Railway tiene configuradas hoy
  (`DRY_RUN`, `GIST_ID`, `GITHUB_GIST_TOKEN`, `MASSIVE_API_KEY`,
  `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `TZ`) — import limpio de
  principio a fin, no solo pasa el chequeo nuevo. Mismo test para
  `geometry_scheduler.py`. Suite completa: 118/118 pasando.

**Sin resolver — necesita evidencia que no se pudo obtener esta
sesión:** el traceback de `MASSIVE_API_KEY` faltante pegado por el
usuario hoy (01-sep) podría ser un log viejo (de antes de que la
variable se guardara en Railway) o un fallo real y distinto (typo en
el nombre, variable en el ambiente equivocado, etc.) — no se pudo
determinar cuál, porque el traceback pegado no trae timestamp propio
(a diferencia de los logs JSON de Cron Runs usados antes en esta
sesión, que sí lo traen) y no hay acceso al activity log de Railway
desde aquí para cruzar la fecha de guardado de la variable. **La
prueba manual ("Run now") que el usuario va a disparar es lo que
resuelve esto empíricamente**, no un análisis de timestamps que no se
pudo completar.

**No se pausó el Cron Schedule de COMBO2D** — decisión explícita del
usuario: se queda activo mientras se termina este fix, no antes.

#### Cierre confirmado con corrida manual real (02-sep-2026)

**Resuelto el punto que había quedado sin evidencia:** el usuario
disparó manualmente "Run now" para COMBO2D desde el dashboard de
Railway. Log real, 2026-09-02 19:58:24–27 CT: arrancó, pasó el
chequeo unificado de `execution/env_check.py` sin reportar ninguna
variable faltante, calculó la señal, determinó correctamente
`NO_TRADE` (razón: `mes_no_signal` — condición normal de la estrategia,
no un fallo), y terminó limpio sin traceback.

**Conclusión: el traceback de `MASSIVE_API_KEY` faltante pegado el
01-sep era un log viejo (de antes de que la variable se guardara en
Railway), no un fallo nuevo o distinto.** El fix del `requirements.txt`
de la raíz (`44f07cf`) más el chequeo unificado (`a24400f`) resuelven
la cadena completa de fallos de infraestructura que empezó el 13-ago.
**El cron automático de COMBO2D puede reactivarse/mantenerse activo
con confianza — no queda pendiente de blindaje de infraestructura.**

**Recordatorio explícito, para no confundir higiene con viabilidad:**
COMBO2D ahora está técnicamente sano (no crashea, corre de principio a
fin) — **pero sigue siendo la estrategia ya descartada por edge no
significativo** (walk-forward p=0.44–0.45, ver sección de arriba sobre
la reproducción fresca del 25-ago-2026 que no logró acercarse al
p=0.149 histórico citado). Este fix es higiene de infraestructura —
que el proceso no truene — no evidencia de que la señal de
mean-reversión día-a-día con doble confirmación MES+MNQ tenga edge
real. Nada de lo arreglado en esta ronda cambia esa conclusión.

### Cerebro 2 — Pass 1 (MES + M6E) y corrección crítica del encuadre de WR (03-sep-2026)

**Rama `cerebro2-dev`.** `scripts/cerebro2_grid_pass1.py` (commit
`8f7a3a4`) corrió un barrido k × RR × WR × 2 políticas de MLL sobre
MES + M6E (1,044 corridas de `simulate_xfa_lifetime`, pase barato:
N_PATHS=1000, MAX_DAYS=500). El mensaje de ese commit incluyó la
afirmación: *"At WR=0.50 (no edge) and RR>=1.5, expected payout is
already meaningfully positive — a non-edge-dependent direction worth
prioritizing"*.

**Esa afirmación es INCORRECTA y queda retractada aquí explícitamente**
(no se reescribe el commit ya pusheado — se documenta la corrección
hacia adelante, mismo criterio que el resto de esta bitácora).

**El error:** `cerebro2_grid_pass1.py` barre WR como parámetro LIBRE
(`ExactDayDist.wr`, Bernoulli independiente en
`scripts/camino_b_grid.py:72`) completamente desacoplado de RR
(`avg_win_usd = rr * avg_loss_usd`, ambos derivados de `sl_ticks`/`nc`).
En ningún punto del pipeline se calcula el WR que un proceso SIN sesgo
produciría dado el RR de esa fila — la misma lógica de gambler's ruin
ya usada para Camino B (`WR ≈ SL/(SL+TP)`) nunca se conectó a este
grid. Confundir "cualquier WR que aparece en el barrido" con
"geometría pura que no requiere señal" es el mismo tipo de error que
casi se cometió al principio de la sesión con Camino B — evitado ahí,
cometido aquí.

**Corrección aplicada** (`scripts/cerebro2_wr_natural_relabel.py`,
post-proceso puro sobre el CSV ya generado — **no se corrió ninguna
simulación nueva**): `WR_natural = 1/(1+RR)` por fila de RR (mismo nc,
mismo tick_value en ambos lados, confirmado en el script del grid):

| RR  | WR_natural |
|-----|-----------|
| 0.5 | 66.7% |
| 1.0 | 50.0% |
| 1.5 | 40.0% |
| 2.0 | 33.3% |
| 3.0 | 25.0% |

**Re-etiquetado del cuadrante marcado como "prometedor" (RR≥1.5,
WR≥0.50):** de las 504 filas de simulación en ese rango, **0 son
geometría pura — las 504 requieren edge real**, con edge requerido
entre 10% y 50% de probabilidad por encima del WR natural (promedio
30.2%; en R-múltiplos, EV requerido entre +0.25R y +2.0R por trade,
promedio +1.01R). Ese nivel de edge no se ha encontrado en ningún
candidato de esta sesión (mejor caso histórico p=0.149, nunca
reproducido en fresco — ver sección de arriba; todo lo demás p>0.4).

**Lo que SÍ sigue siendo geometría pura sin edge** (WR ≤ WR_natural
para su fila de RR): RR=0.5 hasta WR=0.65, RR=1.0 hasta WR=0.50, RR=1.5
hasta WR=0.40 — precisamente la región de payout más bajo/negativo de
la tabla original (consistente con Camino B/G2: SL=100/TP=40 → RR=0.4,
WR_natural=71.4%, casi idéntico al WR empírico ~70.6% de G2 — edge
requerido ≈0, que es exactamente por qué Camino B funciona sin señal
real y por qué NO transfiere directamente a XFA sin ese colchón de
tiempo/pérdida acotada del Combine).

**Conclusión operativa:** el "hallazgo" de que existía una zona de
payout alto sin necesidad de edge era un artefacto del desacople
WR/RR, no un resultado del diseño. Antes de extender el grid a más
productos o correr el stress test (Paso 4.4), el espacio de búsqueda
de Cerebro 2 necesita re-diseñarse para que WR sea reportado siempre
junto a su WR_natural y su edge requerido — no como un eje libre
independiente — o alternativamente, limitarse desde el diseño a la
región WR ≤ WR_natural si el objetivo es un resultado sin dependencia
de señal real (aunque esa región, por lo visto en el pase 1, tiene
payouts marginales o negativos en el rango de RR probado).

Ver `data_cache/cerebro2_grid_pass1_relabeled.csv` (gitignored) para
el detalle fila por fila (`wr_natural`, `edge_required`,
`ev_r_per_trade`, `needs_real_edge`).

### Cerebro 2 — Grid exhaustivo k×RR×WR×producto×cuenta (04-sep-2026)

**Motivación de esta expansión — documentada explícitamente para no
perderla de vista:** un video/contenido de marketing de terceros citó
un payout promedio de **$9,000** en cuenta fondeada, **sin metodología
mostrada**. Se trata aquí como **hipótesis a explorar, NUNCA como cifra
validada** — de ahí extender RR hasta 8.0 (más allá de lo que
cualquier resultado propio de esta sesión sugería) y agregar las
cuentas 100K/150K. El grid (`scripts/cerebro2_grid_exhaustive.py`) NO
intenta reproducir ese número específico — es un mapa completo del
espacio de búsqueda para poder juzgar después, sin re-correr nada, si
alguna región de él es remotamente compatible con esa cifra o con
cualquier otra.

**Diseño** (preflight en `scripts/cerebro2_grid_exhaustive_preflight.py`,
aprobado antes de correr): k (24 valores, 2–100), RR (16 valores,
0.25–8.0), WR (11 valores, 0.30–0.80, barrido completo en TODO punto de
k/RR), 7 productos, 3 tamaños de cuenta XFA (50K/100K/150K), 2
políticas de MLL. 292,050 corridas de `simulate_xfa_lifetime`
estimadas (~2h), CSV íntegro (no solo top-N) en
`data_cache/cerebro2_grid_exhaustive.csv` (gitignored).

**Límite pendiente de verificación — `nc_cap` para 100K/150K:**
`SPECS[...].nc_cap` en `strategies/geometry_pure.py` está documentado
como límite real de contratos confirmado **solo para la cuenta 50K**
(help.topstep.com). No existe en este repo una cifra confirmada para
100K/150K. **Decisión del usuario (04-sep-2026): usar el cap de 50K
como aproximación conservadora para las 3 cuentas** — nunca sobreestima
combos viables, pero puede recortar de más justo la región de interés
para cuentas grandes. Columna `nc_cap_source` en el CSV marca cada fila
como `50K_confirmed` (cuenta 50K) o
`50K_cap_applied_as_proxy_unverified` (100K/150K) — cualquier filtrado
futuro del CSV debe tratar las filas `..._unverified` como una cota
inferior, no un resultado final. Búsqueda de la cifra real de Topstep
para 100K/150K en curso en paralelo a esta corrida (no bloqueante); si
se confirma, son esas filas (no todo el CSV) las que ameritarían
re-correrse.

#### Hallazgo crítico: `nc_cap` NO es el límite real de la XFA — es (probablemente) el del Combine (04-sep-2026)

**La búsqueda de arriba encontró algo más grave que "falta el número de
100K/150K".** Confirmado contra fuente primaria (help.topstep.com,
artículo "What is the Scaling Plan?"): la Express Funded Account (XFA)
**no tiene un cap fijo de contratos por tamaño de cuenta** — usa un
**Scaling Plan dependiente del BALANCE ACTUAL**, no del tamaño con el
que se fondeó. Cita textual: *"Your max contracts do not increase
mid-session"*; ejemplo citado en el artículo: 50K arranca en 2 lotes.

**Tabla completa, verificada por el usuario contra la imagen oficial
del artículo primario (help.topstep.com, "What is the Scaling Plan?"):**

| Balance de la cuenta | 50K | 100K | 150K |
|---|---|---|---|
| < $1,500 | 2 | 3 | 3 |
| $1,500–$2,000 | 3 | 4 | 4 |
| $2,000–$3,000 | 5 | 5 | 5 |
| $3,000–$4,500 | 5 | 5 | 10 |
| > $3,000 (100K) | — | 10 | — |
| > $4,500 (150K) | — | — | 15 |

Unidades en **lotes mini-equivalentes** (ratio 10:1 con micros, excepto
Micro Silver 5:1 y Micro Bitcoin/Micro Ether cap a lot-equivalente de
mini en vez de escala estándar — aplicar la excepción correspondiente
por producto al implementar).

**Patrón notable, ya observado por el usuario:** el techo de contratos
de cada cuenta coincide EXACTAMENTE con su `mll_distance` en dólares
(50K: techo de 5 lotes en balance=$2,000=mll_distance; 100K: techo de
10 lotes en balance=$3,000=mll_distance; 150K: techo de 15 lotes en
balance=$4,500=mll_distance). No parece coincidencia — es
probablemente el diseño intencional de Topstep para que el riesgo
máximo por posición esté acotado en términos similares una vez la
cuenta tiene colchón suficiente.

**Por qué esto invalida (parcialmente) todo el trabajo de Cerebro 2
hecho hasta ahora:** `SPECS[...].nc_cap` (50 para MES, 30 para MGC, 5
para ZN/ZC, etc., usado en el experimento base, el grid Pass-1, y el
grid exhaustivo `cerebro2_grid_exhaustive.py`) es casi con certeza el
límite del **Combine**, no el Scaling Plan de la XFA. `derive_nc()`
nunca modeló que el número de contratos permitido depende del balance
ACTUAL de la cuenta ni que arranca muy bajo (2-3 lotes) cerca de $0 —
exactamente donde la cuenta pasa la mayor parte del tiempo bajo diseños
de k bajo (pocas pérdidas consecutivas). `core/funded_account.py`
tampoco tiene ningún concepto de "nc depende del balance en cada paso
de la simulación" — asume nc fijo toda la vida de la cuenta.

**Decisión explícita del usuario (04-sep-2026):**
1. Dejar terminar el grid exhaustivo actual (`nc` FIJO, calculado por
   `derive_nc()` sin scaling) — se guarda y se documenta como **LÍMITE
   SUPERIOR OPTIMISTA**, nunca como resultado final. No representa lo
   que la cuenta real permitiría operar.
2. NO iniciar el rediseño en paralelo al grid actual, para no duplicar
   cómputo.
3. Una vez guardado el CSV del grid actual, revisarlo con el usuario
   como referencia (aun sabiendo que es optimista) ANTES de empezar el
   rediseño.
4. Rediseñar `simulate_xfa_lifetime()` para que `nc` sea DINÁMICO según
   el balance actual de la cuenta en cada paso, siguiendo la tabla de
   arriba (por tamaño de cuenta, respetando excepciones SIL/MBT/MET
   por producto).
5. Re-correr el MISMO grid (mismos ejes k/RR/WR/producto/cuenta) con
   `nc` dinámico y comparar contra la versión de `nc` fijo ya guardada
   — se espera que empeore, dado que el nc dinámico empieza más
   restringido cerca de $0 de balance, justo donde la cuenta es más
   frágil.
6. Documentar cuál de las 2 versiones (fija vs. dinámica) debe usarse
   para cualquier decisión de negocio futura — **la dinámica, siempre**,
   una vez disponible. La versión fija queda solo como referencia
   histórica de "qué tan optimista era el mapa original".

