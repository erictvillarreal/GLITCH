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

## Fix: logger UTC-mislabeled-como-CT en los 3 schedulers (07-sep-2026)

**Contexto de por qué se encontró esto:** mientras se construía el
reporte de GitHub Pages del proyecto (documentación, rama
`docs/glitch-report`), se intentó listar "el bug del logger
UTC-como-CT" como uno de los bugs ya encontrados-y-arreglados de la
sesión de búsqueda de edge original. **Verificación antes de
afirmarlo reveló que NUNCA se había arreglado — es un bug latente que
seguía vivo hoy** en `geometry_scheduler.py`, `combo2d_scheduler.py`,
y `glitch_scheduler.py` (los 3 usaban el mismo patrón
`logging.basicConfig(format="%(asctime)s CT ...")`).

**El bug real:** `%(asctime)s` usa `time.localtime()` por defecto —
el "CT" en el format string es un literal fijo, no algo derivado del
valor real. El patrón mostraba la hora correcta SOLO porque Railway
tiene la variable de entorno `TZ=America/Chicago` configurada — si esa
variable faltara alguna vez (default típico de un contenedor Docker:
UTC), los logs mostrarían hora UTC etiquetada incorrectamente como
"CT", sin ningún error visible. Confirmado con prueba manual directa
(`TZ=UTC` vs `TZ=America/Chicago`) antes de aplicar el fix — ver commit.

**Fix aplicado:** nuevo módulo `execution/ct_logging.py` (única fuente
de verdad, reemplaza el patrón duplicado en los 3 archivos) —
`CTFormatter` con `converter` explícito a `zoneinfo.ZoneInfo("America/Chicago")`,
independiente de `time.localtime()`/el TZ del proceso. Test permanente
en `tests/test_ct_logging.py`: fuerza `TZ=UTC` a nivel de proceso y
confirma que el timestamp logueado sigue siendo la hora real de
Chicago (incluyendo un caso en verano para confirmar que respeta DST
correctamente, no un offset fijo).

**Hallazgo lateral, no relacionado al fix:** al hacer el smoke test de
`scheduler/glitch_scheduler.py` se descubrió que el archivo **no puede
importarse en absoluto** — `from scheduler.telegram_bot import
notify_signal, notify_exit, ...` falla porque esas funciones ya no
existen en `telegram_bot.py` (reemplazadas en algún punto por el
rework de templates Brain1/Brain2). Esto es un `ImportError` real,
confirmado con `git diff` como preexistente a este fix (mi cambio solo
tocó el bloque de logging, no el import de arriba). Esto es evidencia
fuerte (no definitiva — pendiente que el usuario confirme contra el
dashboard de Railway) de que `scheduler/glitch_scheduler.py` es código
huérfano: si fuera el servicio activo detrás de la línea `worker:` del
Procfile raíz, estaría crash-loopeando de forma visible desde el
rework de Brain1/Brain2, algo que difícilmente hubiera pasado
inadvertido en toda esta sesión. **No se corrigió ese `ImportError`** —
fuera del alcance de este fix específico, pendiente de decisión del
usuario sobre si vale la pena arreglarlo o el archivo debe eliminarse.

**Corrección a la lista de "bugs encontrados" para el reporte de
documentación:** de los 4 bugs que se iban a listar, solo 2 están
confirmados como parte de la búsqueda de edge original con causa raíz
y fix documentados en su momento: (1) barras ambiguas de
`triple_barrier.py` (25-ago-2026), (2) unidad de tick de ZC
cents-vs-dollars. "MES/MNQ tick value confusion" se descarta de la
lista — no se encontró evidencia de que fuera un bug real, solo una
nota aclaratoria de que MES (no MNQ) fue el producto correcto usado.
El logger UTC-como-CT se documenta aquí como lo que realmente es: un
hallazgo y fix de HOY (07-sep-2026), no un bug histórico de la
búsqueda de edge — timelines separados, no mezclados.

## CERRADO: roll dinámico de MES/MNQ verificado ante el vencimiento de MESU6/MNQU6 (08-sep-2026)

**Resuelto.** El vencimiento de MESU6/MNQU6 (18-sep-2026, 8 días
hábiles desde que se abrió este hallazgo) está cubierto por el roll
dinámico de `execution/contracts.py::resolve_front_month()` — **no
requiere ninguna acción humana.**

**Cadena de verificación completa:**
1. Revisión de código: `resolve_front_month()` selecciona el contrato
   correcto por construcción (mismo método `date=`point-in-time +
   `last_trade_date` ascendente ya validado en `scripts/fetch_mes_2y.py`),
   y no requiere intervención manual (`_front_month_cache` es puramente
   en memoria, se re-resuelve contra la API en vivo en cada invocación
   del cron, sin ningún dato persistido entre días).
2. Lo único que el código no podía confirmar por sí solo — el timing
   exacto del roll relativo al `last_trade_date` real de un contrato,
   un comportamiento externo de la API de Massive — se verificó
   empíricamente con `scripts/verify_front_month_roll_history.py`
   contra el roll MESM6→MESU6 (jun-2026), que ya ocurrió, en vez de
   esperar a observar el de MESU6→MESZ6 en vivo.
3. **Bug encontrado y corregido en el script de verificación mismo**
   (no en `resolve_front_month()`): la primera versión calculaba el
   veredicto final ("RESULTADO") a partir de una variable que medía
   el PRIMER día en que aparecía el contrato NUEVO, pero lo
   interpretaba como si midiera el ÚLTIMO día en que seguía
   apareciendo el contrato VIEJO — dos condiciones distintas. Esto
   producía un mensaje de "peligroso" que contradecía la propia tabla
   impresa (que sí mostraba el comportamiento correcto). Corregido
   para derivar el veredicto de `last_offset_still_prior` — el último
   offset en que el front month resuelto fue el contrato viejo,
   calculado con la misma condición por fila que ya se imprime en la
   tabla — y re-verificado contra 3 escenarios sintéticos (caso
   reportado por el usuario, caso peligroso genuino, caso de roll
   temprano) antes de pedir la re-corrida real.
4. **Resultado real, confirmado por el usuario en MES y MNQ:** el
   script corregido da veredicto **SEGURO** en ambos productos, y el
   RESULTADO coincide con la tabla impresa. `resolve_front_month()`
   queda confirmado correcto tal como está — **sin ningún cambio**,
   evitando tocar una función que ya usan GEOMETRY y COMBO2D en
   producción por un bug que resultó estar solo en la herramienta de
   diagnóstico.

**Script de verificación commiteado a `main`** (útil para el próximo
roll trimestral, MESZ6/MNQZ6 en dic-2026, y para cualquier producto
nuevo que se agregue): `scripts/verify_front_month_roll_history.py`.

## Rediseño de templates de Telegram — Cerebro 1, Cerebro 2, COMBO2D (09-sep-2026)

**Objetivo:** distinguir de un vistazo cuál mensaje es de cuál
cerebro/producto en Telegram, sin ambigüedad, texto plano sin emojis.
Prefijo nuevo en TODO mensaje de cada scheduler: `S10GLITCH - COMBINE -
[PRODUCTO]` (Cerebro 1, `geometry_scheduler.py`), `S10GLITCH - XFA -
[PRODUCTO]` (Cerebro 2, `geometry_mgc_scheduler.py`), `S10GLITCH -
COMBO2D - MNQ` (estrategia descartada, aplicado por consistencia visual
según confirmación explícita del usuario). Timestamps cambiados de CT a
UTC en los mensajes (no en los logs del servidor — `setup_ct_logging()`
sigue en CT, sin cambios).

**Decisiones de campo, reportadas y confirmadas ANTES de implementar**
(ver mapeo completo campo-por-campo en el turno anterior de esta
sesión):

1. **"WR:" no "Pass Rate:" en el template XFA.** Evita reintroducir la
   confusión WR-vs-pass-rate que este proyecto ya resolvió una vez (ver
   "HALLAZGO ESTRUCTURAL CENTRAL DE CEREBRO 2" en `cerebro2-dev`) — WR
   (~50%) y el pass rate de Combine de ese mismo candidato (46.9%/47.5%)
   son números distintos, y el template de Combine sí usa "Pass Rate"
   correctamente para SU propia métrica.
2. **"Progreso a Target" y "Dias vs. Estimado" son acumulados sin límite
   de intento**, documentado explícitamente en comentarios inline en
   ambos schedulers — el código no detecta pass/blow del Combine ni
   resetea nada; tracking real de límites de intento queda como tarea
   futura separada, fuera de este cambio puramente de formato.
3. **"Dias vs. Estimado" calculado formalmente, no a mano.** G2 ya tenía
   el número documentado (`dias_calendario_esperados=4.49`, ver
   "Duración recomendada del período de paper trading", 25-ago-2026) —
   se reusó tal cual. Para MGC, el número que se había mencionado
   informalmente (~4.5 días) resultó ser un mix-up con el propio número
   de G2 — se calculó desde cero con `scripts/mgc_dias_esperados.py`
   (mismo motor `TopstepMonteCarloSimulator` ya auditado, misma fórmula
   que G2): **13.87 días** (WR=0.5020 empírico, ventana corregida) /
   13.99 días (WR=0.50 teórico) — prácticamente insensible a cuál WR se
   use. `DIAS_ESPERADOS=13.9` en `geometry_mgc_scheduler.py`
   (`cerebro2-dev`).
4. **"Peak" (Cerebro 1) implementado sin nuevo estado persistido** —
   `_peak_equity()`, máximo histórico rodante del PnL acumulado,
   calculado en el momento desde `paper_log` existente en cada corrida.
5. **"Next Payout"/"Payout Total" (Cerebro 2) con placeholder estático**
   ("sin tracking de elegibilidad implementado todavia") — implementar
   la regla real de elegibilidad de Topstep (5 días ganadores de $150+
   neto, O balance ≥$55k) es lógica nueva, explícitamente fuera de
   alcance de este cambio.
6. **`telegram_bot.py` sin tocar** — mantiene el patrón existente
   (f-strings inline por scheduler); las funciones `notify_brain1_*`/
   `notify_brain2_*` (con emojis, ya existentes pero nunca usadas por
   ningún scheduler real) quedan sin usar, tal como estaban.

**Hallazgo no relacionado, encontrado y corregido al tocar
`combo2d_scheduler.py` para este mismo cambio:** los mensajes de
OPEN/CLOSE ya usaban `datetime.now(UTC)`, pero `UTC` nunca estaba
importado en el archivo (`NameError` latente). Nunca se había disparado
porque la única corrida exitosa confirmada de este scheduler (02-sep-2026,
ver sección de arriba) tomó la rama NO_SIGNAL, que no llega a ese
código — la primera vez que combo_2d generara una señal real, habría
crasheado. Corregido como parte de este mismo cambio (import de
`timezone` agregado, helper `utc_now_str()` nuevo) — no es una
consecuencia del rediseño de templates, es un bug preexistente
descubierto al tocar ese bloque de código.

**Fuera de alcance, observado pero no tocado:** `check_expiry_alerts()`
(`execution/contracts.py`, compartida por los 3 schedulers) sigue
usando un emoji (⚠️) en su mensaje de alerta de vencimiento de
contrato — contradice el objetivo de "sin emojis" de este cambio, pero
modificar esa función no fue parte de lo pedido y afecta a los 3
schedulers a la vez; se deja para una decisión futura explícita.

**Cambio puramente de formato/presentación** — ninguna lógica de
trading, cálculo de señal, ni persistencia en Gist fue tocada (aparte
del fix del `NameError` de arriba, que es una corrección de bug, no un
cambio de comportamiento de trading). Suite completa de tests verde en
los 3 archivos antes de cada commit.

## Dos problemas reportados tras el primer día en producción del rediseño de templates (09-sep-2026)

**1. `check_expiry_alerts()` (`execution/contracts.py`) nunca se
actualizó al prefijo nuevo — corregido.** Quedó explícitamente fuera
del cambio anterior por decisión de scope (afecta a los 3 schedulers a
la vez), pero el usuario reportó que rompía la consistencia visual que
era el objetivo del rediseño — seguía mandando `GLITCH - GEOMETRY-MES`
con emoji (⚠️) en vez de `S10GLITCH - COMBINE - MES` sin emoji.

Fix: `check_expiry_alerts(cache, send_fn, prefix)` ahora recibe el
prefijo COMPLETO ya construido por el llamador (mismo `PREFIX` que cada
scheduler ya usa en sus propios mensajes), no lo construye internamente
— cada scheduler sigue siendo la única fuente de verdad de su propia
identificación visual. Emoji removido, timestamp UTC agregado para
consistencia con el resto de los mensajes. Los 3 call sites
actualizados: `geometry_scheduler.py` (`PREFIX`),
`geometry_mgc_scheduler.py` (`PREFIX`, rama `cerebro2-dev`),
`combo2d_scheduler.py` (`PREFIX`).

**Imprecisión menor heredada, no nueva:** el cache de `combo2d_scheduler.py`
contiene AMBOS productos (MES y MNQ) bajo el mismo `PREFIX = "S10GLITCH
- COMBO2D - MNQ"` — una alerta de vencimiento de la pata MES muestra el
encabezado "- MNQ" aunque el cuerpo del mensaje sí dice correctamente
"MES: MESU6". Este comportamiento ya existía antes (el `label` plano
"COMBO2D" tampoco distinguía producto) — no se empeoró, pero tampoco se
resolvió; queda como posible refinamiento futuro si se decide que vale
la pena.

**2. Bug real: la alerta de vencimiento se dispara de forma
independiente en CADA servicio que comparte el mismo contrato**
(GEOMETRY-MES y COMBO2D ambos alertan sobre MESU6 el mismo día, todos
los días dentro de la ventana de 10 días hábiles) — reportado como
spam, va a repetirse en cada roll futuro. Tres opciones evaluadas:

- **(a) Deduplicar via estado compartido** (Gist): requiere una clave
  nueva, coordinación read-then-write entre servicios con cron
  independientes, y riesgo real de condición de carrera (la API REST
  de Gist no tiene check-and-set atómico) — la opción más compleja y
  frágil, y acopla operacionalmente servicios que hoy son
  independientes.
- **(b) Reducir frecuencia** a puntos de control clave (10, 5, 2, 1
  días restantes) en vez de cada día dentro de la ventana — cambio de
  una línea en una sola función compartida, sin estado nuevo, sin
  acoplamiento entre servicios.
- **(c) Consolidar** en un solo mensaje diario de estado de contratos:
  requiere un nuevo servicio de Railway dedicado, o designar a uno de
  los 3 schedulers existentes como dueño único (crea un hueco
  silencioso si ese scheduler no corre ese día por cualquier razón —
  ej. la salida temprana NO_SIGNAL de combo2d) — la opción más invasiva
  arquitectónicamente.

**Recomendado: (b).** No elimina el todo la duplicación del mismo día
(GEOMETRY y COMBO2D seguirían alertando cada uno sobre MES en los días
10/5/2/1), pero reduce el volumen real (~60%+) sin estado nuevo, sin
riesgo de condición de carrera, y sin cambio de arquitectura — el
trade-off honesto de "más simple, sin tocar lógica de trading".

## Opción (b) implementada — checkpoints con detección de salto por feriado, sin estado (09-sep-2026)

**Aprobado y aplicado.** `check_expiry_alerts()` ahora dispara solo en
`FRONT_MONTH_ALERT_CHECKPOINTS = (10, 5, 2, 1)` días hábiles restantes,
no cada día dentro de la ventana.

**Caso pedido explícitamente por el usuario antes de implementar:** ¿qué
pasa si un feriado/fin de semana hace que el conteo salte sobre un
checkpoint exacto entre dos corridas reales (ej. `days_left` pasa de 11
a 9 sin nunca valer 10 exactamente, porque el scheduler no corrió el
día del feriado)? `np.busday_count` no conoce el calendario de
feriados custom del proyecto — solo excluye fines de semana — así que
un feriado SÍ puede producir un salto de 2 en vez de 1.

**Solución, sin estado persistido (evita exactamente la coordinación
que se descartó en la opción (a)):** `_previous_trading_day()` calcula
el día hábil anterior de forma puramente determinística (mismo
calendario de feriados que los 3 schedulers, duplicado aquí con el
mismo criterio ya establecido). `check_expiry_alerts()` compara
`days_left` de hoy contra `days_left` calculado para ese día hábil
anterior — si algún checkpoint cae estrictamente entre ambos valores,
se considera "cruzado" y dispara, incluso si el salto fue de 2 días en
vez de 1. El checkpoint nunca se pierde por un feriado, y no requiere
ningún Gist ni coordinación entre servicios — es una función pura de la
fecha de hoy y el calendario ya conocido.

**Verificado con `tests/test_contracts.py` (9 tests nuevos), no solo
revisado:** dispara exactamente en checkpoint 10 (caso normal), no
dispara en días intermedios, no re-dispara el día siguiente a un
checkpoint ya disparado, y — el caso crítico — un escenario que
reproduce exactamente el feriado del 07-sep-2026 (última corrida real
viernes 04-sep con `days_left=11`, siguiente corrida real martes 08-sep
con `days_left=9`, saltándose el 10 exacto) confirma que el checkpoint
10 SÍ dispara en la corrida del martes, no se pierde. También verificado:
el prefijo pasado por el llamador se usa tal cual, sin hardcodear nada
internamente.

Aplicado en ambas ramas: `main` (`geometry_scheduler.py`,
`combo2d_scheduler.py`) y `cerebro2-dev` (`geometry_mgc_scheduler.py`,
copia separada de `execution/contracts.py`). Suite completa verde en
ambas ramas antes de cada push.

## Lógica de reinicio de intento de Combine — geometry_scheduler.py (09-sep-2026)

**Cambio de LÓGICA real, no de formato** — cierra el gap documentado
explícitamente en el rediseño de templates anterior ("Progreso a
Target"/"Equity"/"Peak"/"Dias vs. Estimado" eran acumulados sin límite
de intento, sin detección de pase/quiebre).

**Umbrales confirmados contra `core/prop_firm.py`** (fuente ya
auditada, usada por `scripts/cerebro2_cashflow_monte_carlo.py`) — NO
hardcodeados a mano: `TOPSTEP_50K.profit_target = $3,000`,
`TOPSTEP_50K.mll_distance = $2,000` (umbral de quiebre = -$2,000).
Cuenta 50K es correcta para este scheduler independientemente de qué
producto esté activo vía `GLITCH_PRODUCT` — todo Camino B se diseñó y
validó contra el `nc_cap` de una cuenta 50K.

**Diseño — sin estado separado, todo derivado de `paper_log`** (mismo
principio que `_paper_progress()` ya establecido): cada trade cerrado
se etiqueta con `"intento": N` en el entry que se appendea al Gist.
`_current_intento()` deriva el intento activo como el máximo valor de
`"intento"` visto en el log (1 si está vacío — compatibilidad hacia
atrás con entradas de antes de este cambio, que no tienen el campo).
`_attempt_pnl()`, `_attempt_days_elapsed()`, `_attempt_peak()` filtran
por ese intento específico.

**Reinicio:** al cerrar cada trade, `_check_attempt_reset()` (función
pura, sin efectos secundarios — testeada en aislamiento) compara el
PnL acumulado del intento contra los 2 umbrales. Si cruza cualquiera,
se envía un mensaje NUEVO y separado del resumen diario:

```
S10GLITCH - COMBINE - MES [INTENTO #N COMPLETADO: PASE/QUIEBRE]
PnL final del intento: $X
Dias que tomo este intento: X
Pass Rate acumulado historico: X% empirico vs 81.4% teorico
Iniciando intento #N+1 desde $0
```

**Confirmado explícitamente por el usuario (punto 3): Pass Rate y
Ciclos NO se reinician** — siguen siendo históricos de TODOS los
intentos (pasados y quebrados), porque esa es la métrica que importa
para juzgar si la geometría se sostiene con más muestra. "Dia de
paper" (histórico, desde el inicio del paper trading) tampoco cambia
de significado. Solo "Progreso a Target"/"Equity"/"Peak"/"Dias vs.
Estimado" (en OPEN/CLOSE/SUMMARY) pasan a estar acotados al intento
actual — resolviendo correctamente la limitación ya documentada, no
como un cambio nuevo sin relación.

**Verificado con 23 tests nuevos** en `tests/test_geometry_parity.py`
(no solo revisado) — cubre exactamente los 3 casos pedidos
(`_check_attempt_reset`: pase exacto, pase con overshoot, quiebre
exacto, quiebre con overshoot, y el caso normal sin cruce de umbral en
ambas direcciones) más `_current_intento`/`_attempt_pnl`/
`_attempt_days_elapsed`/`_attempt_peak` en aislamiento, un test de
integración del ciclo completo (pase → el intento siguiente arranca en
$0, el intento anterior queda intacto sin tocarse), y un test explícito
confirmando que Pass Rate/Ciclos NO se reinician entre intentos.
Suite completa: 153 tests, verde.

`_peak_equity()` (histórico, todos los intentos sumados — ya no se usa
en ningún mensaje tras este cambio) se eliminó por no tener ningún call
site restante, reemplazada por `_attempt_peak()`.

## Incidente: posición SHORT MGCV6 sin CLOSE, hallazgo arquitectónico compartido por los 3 schedulers (09-sep-2026)

**Síntoma reportado por el usuario:** una posición GEOMETRY-MGC
(SHORT, MGCV6, entry 4,415.80, TP=4,379.40, SL=4,452.20, abierta
2026-09-09 12:13 UTC) nunca recibió su mensaje de CLOSE.

**Diagnóstico, con evidencia de código, no suposición:** el ciclo
completo OPEN→monitoreo→CLOSE vive dentro de UNA sola invocación de
`run()`, sostenida por un `while True` que hace poll cada 60s hasta
TP/SL o el flatten de las 14:30 CT. `paper_log.append()` solo se llama
al cerrar (o en el caso de "no entry data") — **nunca al abrir**. Si el
proceso muere en cualquier punto entre el mensaje de OPEN y el cierre
normal, la posición desaparece sin dejar rastro: ni un registro
"abierto" huérfano, ni aviso — y la siguiente corrida, que no tiene
ningún mecanismo de reconciliación, simplemente abre una posición
nueva sin saber que la anterior existió.

**Causa más probable, por correlación temporal exacta (no confirmada
por Railway, el usuario lo está verificando por su cuenta):** las 3
corridas de push a `cerebro2-dev` de ese mismo día cayeron en
14:39:48 UTC, 14:48:48 UTC, y 23:19:43 UTC — las primeras DOS caen
dentro de la ventana de vida esperada de esa posición
(12:13–19:30 UTC). El servicio GEOMETRY-MGC está conectado a
`cerebro2-dev` y se redeploya automáticamente en cada push — un
redeploy en ese momento habría matado el proceso a mitad del loop de
monitoreo, exactamente el síntoma reportado. `main` no tuvo el mismo
riesgo hoy porque los pushes de hoy a esa rama se retuvieron
localmente hasta después de las 15:00 CT (freeze window normal),
mucho después del flatten de MES.

**Decisión del usuario:** NO pausar el cron manualmente — se acepta
perder el rastro de este trade específico mientras se construye la
solución estructural con el rigor de siempre. No es exclusivo de MGC:
`geometry_scheduler.py` y `combo2d_scheduler.py` comparten exactamente
el mismo patrón arquitectónico (un solo loop bloqueante sostiene la
posición, append-only al cierre, sin lógica de reanudación) — hoy se
manifestó en MGC porque fue el único servicio cuya rama recibió push
durante su propia ventana de mercado en vivo, pero el mismo riesgo
existe en los otros dos bajo el timing equivocado.

### Mitigación inmediata (opción b) — aplicada ya, sin código

`cerebro2-dev` ahora se trata con la misma disciplina de freeze window
que `main`, pero **solo durante la ventana de MGC (07:00–14:30 CT)** —
no un freeze general de la rama completa, que frenaría trabajo de
investigación de Cerebro 2 sin relación con este scheduler. Regla de
sesión, no un cambio de código; documentada aquí para que una sesión
futura la herede.

### Fix estructural (opción a) — implementado, con el mismo rigor de siempre

**Diseño aprobado antes de tocar `run()` en ningún scheduler** (ver
turno anterior de esta sesión para el análisis completo de opciones a
vs. b vs. c): un segundo archivo de Gist por scheduler
(`geometry_mes_pending.json`, `geometry_mgc_pending.json`,
`combo2d_pending.json`), separado del historial append-only, con a lo
sumo un registro: la posición actualmente abierta, o vacío.

- `execution/gist_store.py`: nuevas `load_state(filename) -> dict` /
  `save_state(filename, data: dict)`, refactorizadas para compartir el
  I/O de red con `load_log`/`save_log` vía helpers internos
  `_read_file`/`_write_file` — sin duplicar la lógica HTTP/manejo de
  errores. 10 tests nuevos en `tests/test_gist_store.py` (20 en total).
- Cada scheduler: `save_pending(...)` se llama **antes** del mensaje de
  Telegram de apertura (estado durable primero, notificación después —
  mismo criterio que el módulo ya documentaba), y se limpia
  (`save_pending({})`) en el cierre normal.
- Al inicio de `run()` (paso 0, antes de resolver el front-month de
  hoy — el registro pendiente ya trae su propio ticker): si hay una
  posición pendiente, se reconcilia con el precio actual ANTES de
  considerar abrir una posición nueva.

**Fix encontrado y corregido en el mismo trabajo, no como tarea
aparte:** `_current_intento()` (MES y MGC) filtraba por
`result in ("TP","SL","FLATTEN")` antes de tomar el máximo `intento`
visto. Una entrada `"RECONCILED"` (deliberadamente fuera de ese set,
para excluirla de Pass Rate/WR/attempt_pnl) habría quedado invisible
también ahí, causando que el siguiente trade real reutilizara un
número de intento ya consumido por el intento reconciliado. Corregido:
"qué intento vamos" ahora mira CUALQUIER entrada con el campo
`"intento"` presente (reconciliada o no); "qué entradas cuentan para
el desempeño de ese intento" sigue usando el filtro de resueltas —
misma exclusión de siempre, sin código nuevo en esos otros cálculos.

**Limitación honesta, documentada en el propio mensaje de Telegram, no
solo en un comentario de código:** comparar el precio ACTUAL contra
TP/SL no puede recuperar el camino real del precio durante el hueco —
si el precio tocó TP y luego se revirtió antes de la siguiente
corrida, esto no lo detecta. Por eso el resultado de una
reconciliación SIEMPRE es `"result": "RECONCILED"` (nunca
`"TP"/"SL"/"FLATTEN"`) y `"pnl_estimated": True` — decisión aprobada
explícitamente por el usuario: excluir por completo de Pass Rate/WR,
`attempt_pnl`, y detección de PASE/QUIEBRE, mismo trato que ya recibe
`"no_data_entry"`, sin necesitar código nuevo en `_paper_progress()`,
`_attempt_pnl()`, ni `_check_attempt_reset()` — la exclusión sale
gratis de reusar el mismo filtro ya existente.

**Verificado con tests nuevos, no solo revisado** (todos con `pytest`,
sin red real):
- `tests/test_gist_store.py`: `load_state`/`save_state` — config
  ausente lanza, vacío/ausente/malformado da `{}`, fallo de red no
  tumba el proceso, limpieza con `{}` explícito.
- `tests/test_geometry_parity.py`: `_build_pending_record`,
  `_reconcile_pending_position` (LONG y SHORT × TP confirmado / SL
  confirmado / inconcluso, siempre `result="RECONCILED"`), el fix de
  `_current_intento` (una entrada reconciliada sola SÍ avanza el
  intento; el PnL estimado NUNCA se filtra a `attempt_pnl`/dispara
  PASE-QUIEBRE aunque cruzaría el umbral si se contara), y un test de
  integración de extremo a extremo simulando el escenario real
  reportado (corrida interrumpida → reconciliación → trade nuevo sin
  colisionar).
- `tests/test_combo2d_parity.py`: mismos casos, sin el campo
  `"intento"` (combo2d no tiene lógica de reinicio de intento) — y un
  test explícito de que la entrada reconciliada nunca cuenta en
  `wins`/`total` del Win Rate, aunque su `estimated_outcome` sea "TP".

Suite completa: 216 tests, verde, antes de cada commit.

