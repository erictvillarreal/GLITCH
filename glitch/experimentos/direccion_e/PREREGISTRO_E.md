# PREREGISTRO_E — búsqueda de ventaja direccional real (objetivo WR 51–52 %) — 21-oct-2026

**G0.** Este archivo se commitea **antes de calcular cualquier resultado direccional** (ninguna señal, regla, control ni precisión se ha calculado al escribirlo). Lo único que existe antes: (i) el inventario de datos de Yahoo (solo longitud/fechas de las series descargadas) y (ii) los resultados de las Partes A–D (en particular la Parte B: 3 reglas de dirección con SMA20/SMA50 en MES, que **fallaron**; y D: valor del WR). Las reglas y parámetros de abajo son FIJOS: sin barridos. Cualquier cambio posterior es una enmienda fechada al final del archivo; se reportan ambas versiones.

## 1. Datos (fuente y uso fijados)
| serie | uso | fuente | nota |
|---|---|---|---|
| **MGC 5 min** (`mgc_5min_2y_corrected_window.parquet`) | ventana real 7:15 CT → flatten 14:30 CT, mecánica exacta | local | **contrato dominante del día** (mayor volumen); sin días de cierre anticipado; 488 días |
| **MES 5 min** (`mes_5min_2y.parquet`) | ventana real 9:30 CT → 14:30 CT | local | 1 contrato por día; 492 días |
| **Gold diario largo: `GLD`** (2004-11-18 → 2026-10-20) | precisión del signo de señales lentas (E1) y tramos bajistas (2008, 2013, 2015, 2022) | Yahoo Finance | **ETF que replica el spot: sin rolls**; resultado = signo del retorno apertura→cierre (primario) y cierre→cierre (secundario) |
| **Gold diario largo secundario: `GC=F`** (2000-08-30 →) | robustez | Yahoo | **splice de contratos sin ajustar**: se usa SOLO apertura→cierre del día (no cruza el roll); el cierre→cierre se descarta salvo ajuste |
| **Índice diario largo: `^GSPC`** (1990-01-02 →) y `SPY` (1993 →) | E1/E4 en índices (proxy de MES) | Yahoo | sin rolls |
| `DX-Y.NYB`, `ES=F`, `CL=F`, `EURUSD=X`, `ZN=F` | disponibles en Yahoo pero **solo diarios** | Yahoo | E6 (movimiento nocturno hasta 7:15 CT) **requiere intradía nocturno limpio: no existe en las series locales (solo RTH) ni gratis en Yahoo** → **E6 queda OMITIDA** (declarado ahora) |
| `retrieveBars` de ProjectX | profundidad real por producto/contrato | requiere credenciales que este agente no maneja | **no disponible** |

Toda señal usa **solo información previa a la entrada** (se prueba con desplazamientos en G1). Los retornos nocturnos de las series de 5 min (cierre previo → referencia) **se descartan si el contrato dominante cambió entre los dos días** (el salto incluye el spread del calendario).

## 2. Hipótesis y reglas (fijas)
Resultado de cada regla: lado `s_t ∈ {+1, −1}` (o NO OPERAR) para el día t con información hasta t−1 (E1, E4) o hasta la referencia (E2, E3, E5).
- **E1 — Tendencia lenta.** `r12_t = ln(C_{t−2} / C_{t−254})` (252 sesiones, excluyendo la última sesión); `σ_a,t` = desviación estándar de los retornos logarítmicos diarios de todo el historial hasta t−2 (expansiva, ≥ 252 días) × √252. Lado = signo(r12) si |r12| ≥ 0.5 σ_a; si no, **NO OPERAR** (lectura 1) o `alternate` (lectura 2; se reportan ambas, la prueba G2 usa la lectura 1). Variante única: lado = signo(SMA50_{t−1} − SMA200_{t−1}). **Instrumentos: MGC (GLD y GC=F) y MES (^GSPC, SPY).**
- **E2 — Momentum intradía por reacción inicial.** `R = ln(P_ref / C_prev)` (cierre previo de la sesión regular → referencia: MGC 7:15 CT, MES 9:30 CT). Lecturas: **continuación** (lado = signo(R)) y **reversión** (lado = −signo(R)). Variante: solo si |R| > mediana de |R| de los 60 días previos. Instrumentos: MGC y MES.
- **E3 — Días con dato macro (MGC, 7:15 CT).** Calendario de CPI, NFP, PPI y reclamos semanales (7:30 CT = 8:30 ET; el FOMC es 13:00 CT y queda fuera de la ventana de entrada). (i) deriva de 7:15 a 7:30 CT en días con dato (¿signo no nulo?); (ii) entrada alternativa a las 7:40 CT con lado = signo del movimiento 7:15→7:40 (continuación). Si no se reconstruye el calendario completo con fuente pública verificable, **E3 se omite** (se dirá).
- **E4 — Calendario de MES.** (i) deriva previa al FOMC: lado LARGO en la sesión del día de la reunión (12:00–14:00 CT cae dentro de la ventana; se documenta la hora real del anuncio); (ii) cambio de mes: lado LARGO en los últimos 2 y primeros 3 días hábiles. Solo estas dos.
- **E5 — Brecha en MES.** `gap = open_8:30 / C_prev − 1`; si |gap| > percentil 75 de |gap| de los 60 días previos: lado = −signo(gap) (**reversión**) y también lado = +signo(gap) (**continuación**; si ya existe resultado en el repo se cita; no existe en el repo local: se corren ambas).
- **E6 — OMITIDA** (ver §1).
- **Hipótesis adicionales:** ninguna pre-registrada. Lo que se explore después de ver datos se rotula “exploración posterior” y no puede dar un hallazgo.

## 3. Comparaciones declaradas (corrección de Holm)
E1: 2 instrumentos × 2 señales (r12, SMA50/200) = **4**. E2: 2 instrumentos × 2 lecturas × 2 variantes (todos / solo |R| > mediana) = **8**. E3: **2** (si se reconstruye el calendario). E4: **2**. E5: 2 direcciones = **2**. **Total = 18** (E6 omitida no cuenta; si E3 se omite se conservan 18, criterio conservador). Los controles (`alternate`, siempre LARGO, siempre CORTO, aleatorio ≥ 1,000 corridas, semilla 20261021) no cuentan como pruebas.

## 4. Medidas
(a) **Exactitud del signo** = P(signo del resultado del día = lado) en la ventana real (5 min: retorno referencia → flatten; largo plazo: apertura→cierre de GLD/GC=F/^GSPC/SPY), sobre los días con señal; (b) **mecánica exacta del engine** (referencia, TP/SL, flatten, comisión; slip 0 y {1,3} para MES): fracción TP / SL / FLATTEN, **WR entre decididos**, P&L medio por día. Bracket: MGC 3 micros, SL = TP = 364 ticks (el de Cerebro 2); MES nc 40, TP 32, SL 100 con piso de $2,000 (el de Cerebro 1; WR = TP/(TP+LIQ)). (c) IC95 % por bootstrap de bloques de 5 días (10,000 remuestras, semilla 20261021).

## 5. Compuertas (Claude audita cada una antes de declarar “hallazgo”)
- **G1 — Auditoría de datos** (`data_audit.py` + `test_data_audit.py`): contrato dominante y cambios de contrato, rollovers, husos y DST de cada serie, fechas duplicadas/faltantes, retornos extremos, y **ausencia de mirada hacia adelante** (cada señal se recalcula con la serie truncada en la fecha de decisión y debe coincidir).
- **G2 — Candidata a paper en sombra** (todas, con Holm sobre las 18 comparaciones): (1) **p-valor ajustado por Holm < 0.05 de H₀: exactitud (o WR entre decididos) ≤ 51 %** (equivale a “límite inferior del IC95 % ≥ 51 %” con corrección); (2) supera a `alternate` **y** a “siempre LARGO” (misma ventana) en **≥ 7 de 10 bloques cronológicos**; (3) positiva (exactitud > 50 %) en cada una de las **últimas 3 ventanas anuales** y se reporta el desempeño en cada tramo bajista (oro 2008, 2013, 2015, 2022; índices 2008, 2020, 2022); (4) explicación económica sencilla.
- **G3 — Valor:** traducir el WR medido a neto anual por cuenta con el motor de la Parte D (cadena Combine → XFA), con IC. Si el neto adicional < $500/año o es indistinguible de cero → se archiva aunque pase G2.
- **G4 — Producción:** solo paper en sombra ≥ 30 días hábiles + kill-switch determinista (`alternate` si el WR móvil de las últimas 60 decisiones < 45 % o si cambia el signo de la señal en E1) + aprobación explícita de Eric.
- **Potencia (declarada ahora):** con n = 488 días el semi-ancho del IC95 % de una exactitud es ≈ ±4.4 pp en WR entre decididos (n_dec ≈ 215) y ≈ ±4.4 pp en exactitud de signo con n = 488 (SE 2.3 pp → ±4.5 pp con IC95; **el encargo cita ±2.3 pp = 1 SE**). **G2(1) en las series de 5 min exige una exactitud puntual ≳ 56 % para pasar: casi imposible para un efecto de 51–52 %.** Esto se reporta como “sin potencia”, no como “sin efecto”.

## 6. §4 del encargo (valor de cada punto de WR) — plan
Motor de la Parte D: WR de 47 % a 56 % (paso 1 pp) fijado con deriva calibrada en MGC (W2 limpio sin oro) y la **misma deriva estandarizada (μ/σ)** en MES para el Combine; candidatos: plan 3×364, 728×3 y 4→1 micros (cobro a $1,500); stop 0 y 0.5; slip de entrada del Combine 1 / mezcla {1,3} / 3; con y sin finish-line. Salida: WR de equilibrio, valor de +1 pp, y n para distinguir cada WR de 50 % con 80 % de potencia.

## 7. §5 del encargo (riesgo) — plan
Prueba de inversión de régimen por año; diseño del kill-switch con prueba determinista (NO DESPLEGAR); mezcla segura (la regla decide en señal fuerte, `alternate` en el resto).

## Enmiendas

### Enmienda 1 — 21-oct-2026, ANTES de calcular cualquier resultado de reglas (aclaraciones tras la auditoría G1 de datos)
La auditoría G1 (`RESULTADOS_E_G1.md`) corrió solo propiedades de los datos (contratos, husos, rolls, P(subir) incondicional), no ninguna regla. Resultado y decisiones:
1. **`GC=F` se descarta como serie secundaria de E1**: su “Open” de Yahoo no es comparable (P(apertura→cierre > 0) = 44.0 % frente a 50.2 % de `GLD`; el cierre es el de liquidación de COMEX, no el de las 16:00 ET) y trae 418 días con volumen cero. Instrumentos de E1: **MGC → `GLD`** (2004-11-18 →) y **MES → `^GSPC`** (1990 →); `SPY` solo como robustez (no cuenta como comparación).
2. **Observación incondicional (solo para interpretar):** `GLD` sube el 53.2 % de los días cierre→cierre pero **solo 50.2 % apertura→cierre**: casi toda la deriva del oro ocurre fuera del horario de EE. UU. La ventana real de MGC (7:15–14:30 CT) cubre el horario de EE. UU. y no la deriva nocturna; por eso el resultado primario es **apertura→cierre**. En `^GSPC`, 53.4 % (a/c) y 53.6 % (c/c): “siempre LARGO” es un control duro en índices.
3. **Potencia (aclaración de §5):** con n = 488 días, SE de una exactitud = 0.5/√488 = 2.3 pp; el IC95 % tiene semi-ancho ≈ ±4.5 pp. Para que el p-valor ajustado por Holm (18 pruebas) contra 51 % sea < 0.05 hace falta una exactitud puntual ≳ 56–57 % en las series de 5 min. Se reporta como “sin potencia”.
4. G2(3) “últimas 3 ventanas anuales” **no es evaluable** en las series de 5 min (2 años): las hipótesis intradía (E2, E3, E5) solo pueden generar hipótesis para una ventana nueva, no un hallazgo.
5. **El calendario macro (E3) y las fechas del FOMC (E4)**: BLS bloquea la descarga automática (HTTP 403) y el calendario completo del FOMC desde 1994 requiere ~30 páginas históricas; si no se reconstruye con una fuente pública verificable, E3 se omite y E4 se prueba solo con las fechas que sí se verifiquen. Esto se declara aquí; el total de comparaciones se mantiene en 18.
