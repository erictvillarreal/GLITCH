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
- `tests/test_geometry_parity.py` — 14 tests: identidad de función
  compartida, aritmética de barreras/dólares, nc nunca excede el cap
  real de Topstep por producto, sin key hardcodeada
- `DRY_RUN=true` por default — paper trading, sin excepción, hasta
  decisión explícita separada

**>>> Esto resuelve ÚNICAMENTE Cerebro 1 (pasar el Combine). <<<**
Cerebro 2 (XFA, maximizar payouts) sigue exactamente donde estaba:
bloqueado en la pregunta sin resolver del MLL post-payout (¿se resetea
solo la primera vez o cada vez? — ver sección "Cerebro 2" arriba, fuente
primaria de help.topstep.com nunca confirmada con el texto completo).
Nada de este Paso F asume esa pregunta resuelta ni la toca.

