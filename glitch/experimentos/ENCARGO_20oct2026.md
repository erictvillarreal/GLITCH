# ENCARGO PARA CLAUDE CODE — Rama `experimentos-research` (20-oct-2026)

Autor: Claude (sesión de gobierno) para Eric Treviño. Se pega completo a Claude Code.
Orden de trabajo: **Parte A (preservación de capital) → Parte B (dirección práctica) → Parte C (sesión extra)**. No saltar el orden.

---

## 0. Reglas duras (aplican a todo)

1. Trabajar SOLO en la rama `experimentos-research` (crearla desde `main`). **Nada se mergea a `main`, nada se despliega al Pi/Railway, nada toca producción.** Todo cambio de producción propuesto va como patch separado + test, marcado "NO DESPLEGAR", y espera aprobación explícita de Eric.
2. **Cero números inventados.** Cada cifra del reporte lleva su fuente (archivo:línea, doc del Project, log, API, o "supuesto: X"). Si un dato no existe, se escribe "no disponible" y se dice cómo conseguirlo. Prohibido rellenar con "típico" o "razonable".
3. **Pre-registro.** Hipótesis, parámetros, métricas y criterios de la Parte B están FIJADOS en este documento. Se commitean tal cual (`PREREGISTRO.md`) ANTES de correr cualquier resultado. Si algo se quiere cambiar después, se registra como enmienda con fecha y se reportan ambas versiones.
4. Semillas fijas, scripts reproducibles con un solo comando, tests que corran limpio. Reportar también lo que NO salió o contradice nuestras ideas.
5. El estado actual de la cuenta debe confirmarse con Eric (ver §1). Hasta entonces, parametrizar, no asumir.

---

## 1. Estado de partida (parametrizar; Eric confirma con el encabezado de TopstepX: BAL y MLL)

- Cuenta Combine 50K actual (id API `28773715`), intento #2 de la sesión de 19–20 oct.
- Balance ≈ **$51,401** (hoy TP +$1,450 bruto; confirmar neto). Pico ≈ $51,401 → piso MLL ≈ **$49,401**. Meta **$53,000**. Faltan ≈ **$1,599**.
- Reglas Combine (dashboard TopstepX): MLL $2,000 en tiempo real (piso = min(pico − 2,000, 50,000); liquida al tocarlo), meta $3,000, **consistencia: mejor día < 55% de la meta (< $1,650)**, sin DLL.
- Costos: reset **$49** (confirmado 19-oct, crea nuevo accountId), suscripción $49/mes (rebill sáb 31-oct). Comisión ≈ **$1.22 por contrato round trip**.
- Estrategia MES (Cerebro 1): 40 contratos, SL 100 ticks, TP 32 ticks, `mode=alternate`, $50/tick con 40 contratos ($1.25/tick/contrato). TP/SL se anclan al precio de **referencia**, no al fill. Slippage de entrada observado: 1 tick (lun 19), ≈3 ticks (mar 20, inferido). Flatten 14:30 CT; entrada hasta 10:00 CT; la señal sale ~8:35 Monterrey. Mañana miércoles 21 toca SHORT por paridad (`trading_day_index` 1775).
- Definir con Eric si el "pnl" que cuenta Topstep es neto de comisiones (`pnl` vs `pnl_real` en los logs) y usar ESE para consistencia y piso.

---

## 2. PARTE A — Preservación de capital (prioridad 1)

### 2.1 Qué quiere Eric (literal)
No quedarse a ~$100 de la meta y quemar la cuenta, y —peor— **no perder todo mañana** (liquidación en un solo día). Quiere ver cómo mitigarlo, con análisis robusto y exacto, simulación y sizing adaptativo. Hoy el riesgo estructural es este: con 40 contratos el colchón ($2,000) equivale a **40 ticks**, menor que el SL nominal (100 ticks = $5,000). El MLL liquida mucho antes de que el SL actúe.

### 2.2 Chequeo de cordura teórico (obligatorio, primer test)
Si el balance fuera una martingala continua sin fricciones y con piso fijo f, la probabilidad de llegar a la meta T antes del piso para CUALQUIER política de tamaños es `(b − f)/(T − f)` = (51,401 − 49,401)/(53,000 − 49,401) ≈ **55.6%** (teorema de parada opcional). El trailing del piso, las comisiones, el slippage, los saltos discretos (TP/SL) y la regla de consistencia solo la bajan. **Ninguna política sin deriva puede superar ~55.6%**; si el simulador lo supera, hay un bug. Con deriva positiva a favor sí (conecta con Parte B).

Tests de regresión del simulador (deben reproducir hechos ya establecidos):
- Barrera nominal 40 vs 72 ticks: P(+32 antes de −40) = 40/72 = 55.6%; dos victorias seguidas ≈ 30.9% (el engine daba 30.8%).
- A 20 contratos: ≈ 71% por día y ≈ 4 victorias necesarias, ≈ 26% de pase (cifra del análisis del 7-oct; verificar contra el doc).
- Intentos esperados para pasar ≈ 3.2 (mediana ≈ 2) con p ≈ 31%.

### 2.3 Modelos de camino intradía (comparar los tres; si divergen, reportar la divergencia)
- **M1 — Browniano sin deriva**, sigma (ticks/sesión) calibrada con el método de momentos contra los tres objetivos del doc 7-oct (TP40/SL100 ≈ 59% / 24% / 17% fin-de-día). Mi calibración preliminar (TP40/SL100, 20,000 trayectorias) NO ajustó los tres a la vez: σ=80 → TP 0.595 / SL 0.179 / ninguno 0.225; σ=100 → 0.656 / 0.244 / 0.100; σ=120 → 0.688 / 0.274 / 0.038. Mejorarla (p. ej. con volatilidad intradía no constante) o declarar que M1 no sirve y quedarse con M2. La simulación del apéndice usó σ=90 sin haberla calibrado de forma puntual.
- **M2 — Replay de días reales**: serie MES de 515 días (barras intradía, la misma usada en las pruebas de dirección). Para cada día, simular la mecánica EXACTA del engine desde la hora de referencia real del scheduler: entrada con slippage, TP/SL desde referencia, liquidación por piso en tiempo real (mark-to-market con el mejor/peor tick de la barra, conservador), flatten 14:30 CT. Bootstrap de bloques de días (bloques de 5) para intervalos de confianza.
- **M3 — M2 con deriva** (ver §2.9) para ver cuánto valdría una ventaja direccional.

### 2.4 Fricciones a modelar explícitamente
- Slippage de entrada: distribución EMPÍRICA (lun 1 tick, mar ≈3 ticks inferido, más las 6 entradas de `geometry_mestest_log.json` si traen precio de referencia/fill). Reportar con {0, 1, 2, 3, 5} fijos y con la distribución empírica. Slippage también en la salida SL (gap a través del stop): usar el peor caso empírico.
- Comisión $1.22/contrato.
- Piso con ratchet: piso = min(pico − 2,000, 50,000); se congela en $50,000 cuando el pico ≥ $52,000.
- Consistencia: pase solo si balance ≥ $53,000 **y** mejor día < $1,650. Un día de 40 contratos con TP limpio rinde ≈ $1,450–1,550: verificar si algún día (incluso con slippage 0) puede violarla y qué hace el sizing adaptativo en ese caso.
- Costo de tiempo: $49/mes de suscripción (≈ $2.3 por día hábil) y $49 por reset. **No hay límite de tiempo en el Combine** (verificar en reglas): ir despacio solo cuesta ≈ $2.3/día. Esto cambia el óptimo: lentitud casi gratis.

### 2.5 Políticas a comparar (cada una evaluada con M1, M2, M3)
- **P0** — 40 fijo (actual).
- **P1** — fijo en {5, 10, 15, 20, 25, 30, 35}.
- **P2 — "SL-safe"**: cada día `nc = floor(colchón / (costo por contrato de un SL completo))`, donde costo por contrato = (100 ticks + slippage de salida peor caso) × $1.25 + $1.22. Con esto **un solo SL nunca puede liquidar** (hipótesis de orden de magnitud: ≈15 contratos desde el estado actual; calcular el número exacto y su margen). Con el colchón actual el margen será de decenas de dólares: reportarlo.
- **P3 — "Finish-line"**: `nc = ceil(faltante / neto_por_contrato_en_TP)` acotado a [1, 40], con neto por contrato = (32 − slip) × $1.25 − $1.22. Se achica solo al acercarse a la meta. Respetar consistencia (< $1,650 por día).
- **P4 — Híbrido**: min(P2, P3) (sizing seguro, y chico al final). Variante P4b: 40 hoy/mañana y P2/P3 después (el "mañana" de Eric).
- **P5 — Híbrido con piso congelado**: P2 mientras el piso aún sube; P3 cuando el piso quedó en $50,000.
- **P6 — Día saltado**: política adicional "no operar" cuando el colchón sea < X (X a barrer), dado que esperar casi no cuesta.
- **P7 (exploratorio, marcado como tal)** — SL más corto (50/70/80 ticks) con el sizing de P2/P3. Cambia la razón de barreras; solo para ver si el SL de 100 ticks aporta algo cuando el MLL ya manda. No es candidato a producción sin su propia validación.

### 2.6 "Exacto": programación dinámica + Monte Carlo
- Discretizar el estado `(balance, pico)` en pasos de $25–50 (más el mejor día para la consistencia). Para cada nc candidato estimar con M2 la distribución de resultados de un día: {TP, SL, FLATTEN con pnl parcial, LIQUIDACIÓN} con sus P&L.
- **Value iteration** (acción = nc ∈ {0 (saltar), 1…40}; recompensa = pase; costos = reset y suscripción) para obtener la política óptima y su P(pase), y comparar con P0–P7. La política óptima de la DP es la referencia: ninguna política heurística debe superarla.
- Validar la DP con Monte Carlo (≥ 50,000 intentos por política, semilla fija). DP y MC deben coincidir dentro del IC al 95%; si no, depurar antes de reportar.

### 2.7 Métricas (por política y por modelo)
P(pase de este intento) · P(liquidar) · P(sigue abierto tras 60 días) · días hasta pase (mediana, p10, p90) · **costo esperado por pase** = (resets + suscripción)/P(pase) + comisiones · **P(liquidar mañana)** · **P(liquidar estando a ≤ $200 / ≤ $100 de la meta)** (el miedo literal de Eric) · peor caso de un día · distribución del balance al cierre de mañana · número de días operados.

### 2.8 Escenarios específicos obligatorios
1. **Mañana (miér 21, SHORT por paridad):** tabla por nc ∈ {5…40}: P(TP), P(SL), P(liquidación), P(flatten), P&L esperado, estado resultante, y el **nc mínimo que hace imposible liquidar en un día** con su margen en dólares.
2. **"A $100 de la meta":** desde balances 52,700 / 52,800 / 52,900 / 52,950 con cada política: P(pase), P(liquidar antes de pasar), días esperados. ¿Qué nc minimiza el riesgo de quemar la cuenta ahí? (Esperado: pocos contratos, TP chico en dólares; verificar que el TP en ticks se alcance razonablemente rápido con tamaño pequeño y cuántos días toma.)
3. **Secuencia completa desde hoy** con P4b (40 mañana) vs P2 mañana: ¿cuánto "cuesta" en P(pase) y días ser conservador mañana?

### 2.9 Sensibilidades (obligatorias, tabla única)
sigma ±20% · deriva de −2 / 0 / +2 / +5 ticks por día a favor (para conectar con Parte B: cuánto sube P(pase) una ventaja direccional) · slippage {0,1,3,5} · cada día de TP con 31–33 ticks efectivos · con y sin ratchet · con y sin comisión · bloque de 5 días vs iid.

### 2.10 Cuatro hallazgos de trabajo — VERIFICAR, no asumir (mi corrida preliminar con M1/σ=90, slippage 1–3, comisión incluida)
Tabla preliminar (20,000 intentos; calibración imperfecta; NO es evidencia):

| Política | P(pase) | P(liquida) | Días al pase |
|---|---|---|---|
| 40 fijo | 33.5% | 66.5% | 2.0 |
| 30 fijo | 39.4% | 60.6% | 2.0 |
| 20 fijo | 38.0% | 62.0% | 3.3 |
| 10 fijo | 36.3% | 63.7% | 8.4 |
| Adaptativo (40 → se achica al acercarse) | 49.6% | 50.4% | 2.4 |

Los cuatro puntos a confirmar o refutar con M1+M2+DP:
1. **Reducir el tamaño de forma fija casi no cambia la probabilidad de pase** (33%→39%, dentro de la incertidumbre de calibración): menos contratos reducen el riesgo diario pero alargan el camino y ambos efectos se compensan.
2. **Lo que sí mueve el resultado es el tamaño adaptativo al final** (≈50% vs 33.5%): un TP de 40 deja ≈ $1,450 y faltan $1,599, así que se cubre con un día grande y un cierre con pocos contratos, donde la liquidación casi no existe. La cota teórica (§2.2) dice que ≈ 55% es el techo sin deriva; verificar qué tan cerca llega la DP.
3. **Implementar sizing adaptativo exige cambiar código de producción** (hoy `nc` es fijo en `GeometryConfig`; revisar también la validación del Pi y su cap `GLITCH_PI_NC_MAX`). Entregar el diseño y el patch con tests, **sin desplegar**; requiere aprobación explícita de Eric.
4. **Mañana sigue con 40 salvo que el análisis demuestre otra cosa** con evidencia mecánica; la corrida preliminar no probó el híbrido (40 mañana y achicar después). Entregar la recomendación explícita para mañana con su P(liquidar mañana) por opción, y que Eric decida. Cualquier cambio de tamaño para mañana exige que el patch esté probado y desplegado ANTES de las 8:25 Monterrey; si no alcanza, la respuesta es "se queda en 40".

### 2.11 Entregables Parte A
`experimentos/preservacion/` con: simulador (M1, M2), DP, tests de regresión (§2.2), `REPORTE_A.md` (tablas §2.7–2.9, gráficos simples, **recomendación en una página** con riesgo de cada opción para mañana), y patch NO desplegado del sizing propuesto (con tests unitarios de las fórmulas de nc y de que nunca exceda el cap).

---

## 3. PARTE B — Dirección práctica ("¿long o short hoy?" sin arbitrariedad)

### 3.1 Enfoque (distinto al de edge cuantitativo)
Eric NO pide un modelo alfa. Pide una regla simple, explicable, que diga **de qué lado operar según el régimen**, y usar el rally si existe. La pregunta práctica es: *¿qué lado tiene más probabilidad de tocar el TP de 32 ticks antes que el SL de 100 / la liquidación, dado el régimen de ayer?* Se mide con la mecánica real del engine, no con retornos genéricos.

Contexto honesto (no negociable en el reporte): más de 1,800 configuraciones previas no hallaron ventaja de dirección; en MGC una ventana de oro (nov-2025 a ene-2026) domina el nivel. Y "longs ganan, shorts pierden" en 8 sesiones es anecdótico (p≈0.14, alternancia por paridad confunde día con lado). Esta parte busca si el régimen (deriva alcista) aporta algo **usable**, y deja claro cuándo solo es deriva.

### 3.2 Datos (en este orden; documentar qué se usó)
1. Velas de TopstepX/ProjectX vía API (histórico disponible para MES y MGC); 2. los CSV/JSON de experimentos previos (serie MES de 515 días y MGC 7:13); 3. Yahoo Finance del contrato operado **solo** si lo anterior no alcanza (marcar como menor calidad). Reportar cobertura y huecos.

### 3.3 Medida base (contrafactual por día)
Para cada día, con la mecánica EXACTA del engine (referencia, slippage empírico, TP 32, SL 100, flatten 14:30 CT; piso MLL de 40 ticks a 40 contratos como evento aparte), simular **ambos lados** sobre la misma trayectoria: resultado LONG y resultado SHORT ∈ {TP, SL, LIQ, FLATTEN, ticks}. Métricas: P(TP-primero), P(liq), ticks medios netos de fricciones.

### 3.4 Reglas candidatas (máximo 3, parámetros FIJOS desde ya, solo información disponible antes de la señal)
- **R1 — Tendencia simple:** cierre de ayer > SMA20 de cierres diarios → LONG; si no → SHORT.
- **R2 — Sesgo largo con baja confirmada:** LONG, salvo que (cierre de ayer < SMA20 y SMA20 < SMA50) → SHORT.
- **R3 — R2 con día saltado:** igual a R2, pero si el cierre de ayer está a menos de 0.5×ATR14 de la SMA20 → NO OPERAR (esperar casi no cuesta; ver §2.4).
Controles: `alternate` (producción), siempre LONG, siempre SHORT, aleatorio (semilla, ≥1,000 corridas). Referencia informativa (no candidato): oráculo.
Sin ajuste de parámetros (sin barrido): calentamiento de 50 días y evaluación **walk-forward** (solo pasado disponible en cada fecha).

### 3.5 Criterios (fijados ahora, no se modifican después)
- **D1 (descriptivo, obligatorio):** asimetría LONG vs SHORT en P(TP-primero) por bloque (10 bloques consecutivos de igual tamaño), con y sin la ventana dominante; y la **misma tabla para las 8 sesiones en vivo** como anécdota (n pequeña, así se rotula).
- **D2 (candidata a paper-forward):** una regla pasa solo si (a) supera a `alternate` en ≥ 7 de 10 bloques, (b) la diferencia de P(TP-primero) vs `alternate` tiene IC bootstrap pareado (bloques de 5 días) al 98.3% (Bonferroni 0.05/3) estrictamente > 0, (c) no pierde contra "siempre LONG" en más de 3 de 10 bloques (debe aportar protección, no solo deriva), y (d) excluida la ventana dominante, la diferencia no es negativa.
- Si ninguna regla pasa D2: veredicto "no hay base para elegir lado; seguir con `alternate` o con el criterio de menor riesgo operativo". Un resultado negativo es un resultado válido.
- Si todas las ganancias vienen de un solo régimen/ventana: etiquetar "dependiente de régimen" y reportar qué pasa cuando el régimen se invierte (comportamiento de la regla en las caídas de la serie).

### 3.6 Puente con la Parte A
Con las tasas de TP-primero medidas de cada regla (y del control), correr el simulador de la Parte A para traducir "ventaja direccional" a **P(pase del Combine) y a costo esperado por pase**. Esa es la métrica que decide si importa.

### 3.7 Lectura de hoy (informativa, NO se aplica)
Calcular dónde está MES respecto a SMA20/SMA50 al cierre del 20-oct y qué diría cada regla para el 21-oct. Producción para mañana sigue siendo SHORT por paridad.

### 3.8 Camino a producción (si alguna regla pasa D2)
Solo **paper forward en sombra ≥ 30 días hábiles** (registrar qué haría la regla sin ordenar nada, comparar contra lo ejecutado), con kill-switch automático que vuelva a `alternate` si el régimen se invierte. Después, Eric decide. Entregar el diseño de logging en sombra como patch NO desplegado, con tests.

### 3.9 Entregables Parte B
`experimentos/direccion/`: `PREREGISTRO.md` (commit ANTES de resultados), código, `REPORTE_B.md` (D1, D2 por regla, sensibilidad a la ventana dominante, puente a P(pase), lectura de hoy) y tablas por bloque.

---

## 4. PARTE C — Sesión extra de investigación (solo después de A y B)

- **C1 — Conciliar las cifras económicas.** Hoy hay tres versiones sin reconciliar: `engine_real` del 26-sep (neto p50 $3,532; p10 −$1,869; p90 $11,001; P(año<0) 22%; costos ≈ $5,349/año), doc del 13-oct ($1.1k–$3.0k) y `lever_engine` (1 cuenta $1.8k–$3.2k con historia real, $5.4k "fair"; 2 cuentas $4.6k–$6.3k, $10.2k "fair"). Entregar UN script reproducible con una tabla de supuestos, usando la P(pase) de la Parte A (no la asumida), reglas XFA/payout vigentes de Topstep (citar fuente oficial, fecha) y RTP no modelado hasta ahora. Salida: un rango único con la diferencia explicada supuesto por supuesto. Marcar baja confianza donde la evidencia sea paper.
- **C2 — Detectar liquidación en el Pi.** El 19-oct TopstepX liquidó la cuenta y el Pi registró `UNKNOWN` con pnl 0 (no avanzó el intento; lo corregimos a mano en el Gist). Diseñar la detección (posición cerrada + caída de balance al piso / historial de órdenes / trades de la API), clasificar como SL o `LIQ`, y garantizar que `_attempt_entries` y `_check_attempt_reset` lo cuenten. Patch + tests, NO desplegar.
- **C3 — Registrar slippage real** (T3 ítem 2 del plan previo): campos `ref_price`, `fill_price`, `slip_ticks` en `[OPEN]` y en el log; calcular de nuevo para los días 19 y 20-oct con la historia de trades de TopstepX (confirmando 1 y ≈3 ticks). Patch + tests, NO desplegar.

---

## 5. Formato de entrega y verificación

- Un `REPORTE_FINAL.md` con: resumen de 1 página (qué se hará mañana, qué se propone, riesgos, qué NO se sabe), enlaces a A/B/C, lista de supuestos con fuente, y lista de cosas que Eric debe decidir.
- Antes de reportar: correr todos los tests (la suite base tiene 492 pasando); confirmar que `git diff main -- glitch/` solo contiene cambios en archivos nuevos o patches marcados "NO DESPLEGAR".
- Prohibido: cambiar `geometry_pure.py`, el scheduler o el Pi en `main`; tocar secretos; reportar probabilidades sin intervalo o sin semilla.

---

## 6. Mandato abierto: la investigación propone, no se limita

Las Partes A, B y C son el **mínimo obligatorio**, no el techo. Claude Code debe abrir la investigación a todo lo que pueda mejorar el proyecto, incluyendo **edge** (ventaja estadística real), y debe hacerlo, no solo permitírselo. Concretamente:

1. **Proponer hipótesis nuevas** más allá de dirección: horario y ventana de entrada, volatilidad o régimen de volatilidad como filtro (operar/no operar), TP/SL y su razón por régimen, calendario (FOMC, CPI, vencimientos, cierres anticipados), estructura de la sesión, selección de producto (MES vs MGC vs otros), y cualquier otra palanca que los datos sugieran. También puede sugerir qué falta medir o registrar.
2. **Buscar edge de forma legítima.** Si encuentra algo prometedor, tratarlo con el mismo rigor: pre-registro antes de ver resultados, walk-forward, bloques, corrección por múltiples comparaciones (contar TODAS las configuraciones probadas, incluidas las más de 1,800 previas), y reporte de lo que no funcionó. Un hallazgo que no sobreviva a esto se reporta como "no confirmado", no se esconde ni se vende.
3. **Separar claramente dos categorías en el reporte:** (a) *hipótesis pre-registradas* (las de este documento y las que Claude Code registre antes de correr) y (b) *exploración posterior*, rotulada como generadora de hipótesis, nunca como evidencia. Lo explorado después de ver datos solo puede pasar a (a) con una nueva ventana de datos o paper forward.
4. **Priorizar por valor para el objetivo** (pasar el Combine, luego XFA y payouts, con la menor tasa de errores operativos): para cada propuesta estimar el impacto en P(pase) y en costo esperado por pase usando el simulador de la Parte A, y el esfuerzo/riesgo de implementarla.
5. **Entregar al final una lista priorizada de propuestas** (máx. 10) con: hipótesis, datos necesarios, costo de probarla, impacto estimado con su incertidumbre, y qué la haría fallar. Eric decide cuáles se abren.
6. **Las reglas duras del §0 siguen vigentes:** nada a producción sin evidencia, prueba mecánica y aprobación explícita de Eric; cero números inventados; todo en la rama `experimentos-research`.

---

## Apéndice — Semilla de simulación (primera pasada, con defectos conocidos)

Defectos conocidos: σ no calibrada a los tres objetivos; slippage aleatorio {1,2,3} no empírico; 300 pasos por sesión (no barras reales); la liquidación se mide desde el fill y el TP/SL desde la referencia; sin DP; la política adaptativa usa slip fijo de 2 ticks; no modela saltar días; el bloque de consistencia es aproximado.

```python
import numpy as np, math
rng = np.random.default_rng(7)
SIG, STEPS, TICK, FEE, TP, SL = 90.0, 300, 1.25, 1.22, 32, 100

def day(nc, bal, floor, slip):
    liq_ticks = (bal - floor) / (nc * TICK)
    path = np.cumsum(rng.normal(0, SIG / np.sqrt(STEPS), STEPS))   # ticks desde la referencia
    p = path - slip                                                # ticks desde el fill (slip adverso)
    f = lambda m: np.argmax(m) if m.any() else 10**9
    hit_tp, hit_sl, hit_lq = f(path >= TP), f(path <= -SL), f(p <= -liq_ticks)
    first = min(hit_tp, hit_sl, hit_lq)
    fees = nc * FEE
    if first == 10**9: return p[-1] * nc * TICK - fees, False
    if hit_lq <= min(hit_tp, hit_sl): return None, True
    if first == hit_tp: return (TP - slip) * nc * TICK - fees, False
    return (-SL - slip) * nc * TICK - fees, False

def attempt(policy, bal=51401.2, peak=51401.2, maxdays=40):
    best = 1401.2
    for d in range(maxdays):
        floor = min(peak - 2000, 50000)
        nc = policy(53000 - bal, bal, floor)
        r, liq = day(nc, bal, floor, rng.choice([1, 2, 3]))
        if liq: return 'liq', d + 1
        bal += r; best = max(best, r); peak = max(peak, bal)
        if bal >= 53000 and best < 1650: return 'pass', d + 1
    return 'open', maxdays

fixed = lambda n: (lambda need, bal, floor: n)
def adaptive(need, bal, floor):
    per = (TP - 2) * TICK - FEE
    return int(max(1, min(40, math.ceil(need / per))))
```
