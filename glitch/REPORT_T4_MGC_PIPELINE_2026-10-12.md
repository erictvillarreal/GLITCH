# T4 — Tubería de Cerebro 2 (MGC, XFA): diagnóstico, handoff, geometría, segunda instancia del Pi y plan de ensayo
*Rama `feat/t4-pi-mgc` (desde `origin/main` `2ed2ec2`) + `feat/t4-mgc-handoff` (desde `origin/cerebro2-dev`, porque `geometry_mgc_scheduler.py` solo vive ahí y Railway MGC está conectado a esa rama). Todo es **propuesta, NEEDS HUMAN REVIEW** (CLAUDE.md regla 4); nada se desplegó ni se tocó en Railway/Pi. 22 pruebas nuevas en la rama del Pi (todas pasan junto a las suites Pi y de paridad existentes) y 20 en la del scheduler (156 pasan con las suites relacionadas). Python 3.9 en esta máquina; las suites completas con dependencias de 3.11 no se colectan aquí (preexistente).*

## Resumen (10 líneas)
1. **Causa raíz del feed MGC muerto desde ~1-oct**: `execution/contracts.py::resolve_front_month` elige el contrato de **vencimiento más cercano** (MGCV6, octubre, último día ≈ 28-oct), pero el contrato que Topstep exige (el de **mayor volumen**) es MGCZ6 desde finales de septiembre. El oro bimestral deja de imprimir barras al entrar en mes de entrega (el incidente del 1-oct, "MGCV6 sin ninguna barra nueva por 700+ minutos", ocurre justo después del primer día de aviso, 30-sep).
2. **`70b3ac0` sí está en `origin/cerebro2-dev`** (push del 1-oct 09:49 -0600). Que Railway lo haya **desplegado** no se puede verificar desde el repo (NO VERIFICADO); el log del 9-sep documenta que GEOMETRY-MGC redespliega en cada push a esa rama. El commit no creó el problema: **dejó de aceptar la barra congelada como precio vivo**, y por eso ahora aparece "no entry data available" (20 intentos × 30 s tras las 7:13 CT).
3. **El mismo error está en el Pi**: `resolve_contract_id` ordena por vencimiento y habría elegido MGCV6 para órdenes reales. Se corrige para preferir `activeContract: true` (NO VERIFICADO en vivo; `pi/ops/check_contracts.py` lo confirma en el Pi, solo lectura).
4. **Handoff real implementado** (`DRY_RUN=false` en `geometry_mgc_scheduler.py` → `orden_pendiente_mgc.json`, mismo contrato que MES, con las salvaguardas de MES: no sobrescribe una señal sin consumir, no envía después del flatten incluyendo cierres anticipados).
5. **Una sola geometría**: `CANDIDATES["MGC"]` = XFA 50K real (SL = TP = 364, **nc = 3**); `MGC_XFA_100K` (nc 4), `MGC_XFA_150K` (nc 6, paper). El "nc = 6" de `ARCHITECTURE.md` es la 150K del paper, no la cuenta real de Eric. El bracket 728×3 queda como propuesta aparte (cabe en el validador del Pi: ≤ 4× lo configurado).
6. **Peligro de contrato descubierto**: si `signal["product"]` ≠ `GLITCH_PRODUCT` del Pi, el Pi trata la señal como **ensayo** (≤ 2 contratos, sin marcador at-most-once ni ventana horaria). El scheduler usa la misma variable para evitarlo (hay prueba).
7. **Segunda instancia del Pi**: `install_service.sh --instance mgc` (unidad, entorno, log, estado y watchdog propios; se niega a instalar dos instancias del mismo producto). Las guardias de posición son por `contractId` y las de órdenes por id: MES y MGC **no se confunden**, ni siquiera en la misma cuenta (sí comparten el MLL de esa cuenta).
8. **Practice**: Topstep publica **1 cuenta Practice a la vez**, de **150K y 15 lotes**, con reset gratis (10/día); no hay segunda Practice documentada. Ensayo diseñado sobre la Practice `28514663` con ventanas separadas; la Practice **no reproduce** las reglas de la XFA 50K (MLL, escalado): valida el cableado, no la dinámica de la cuenta.
9. **Calendario**: el ensayo puede arrancar el **vie 30-oct** (nc = 1), pero con 10 sesiones limpias + 5 a nc = 3 la luz verde completa llega ≈ **20-nov**, y la 1.ª XFA se activará con 91% de probabilidad en los primeros 10 días hábiles (≈ 2–4-nov). Hay que decidir el plan puente (§6.3).
10. **Hueco abierto que afecta a MES y a MGC**: el Pi no maneja cierres anticipados (27-nov y 24-dic: flatten a las 11:30 CT, el Pi usa 14:30 fijo); el scheduler MGC sí se niega a enviar señales tarde, pero el flatten es del Pi.

## 1. (a) Diagnóstico del feed MGC
**Evidencia (repo)**
| Hecho | Fuente |
|---|---|
| `resolve_front_month(product)` devuelve el contrato `single` activo de **menor `last_trade_date`**; no mira volumen | `execution/contracts.py` (rama `cerebro2-dev`) |
| `fetch_latest_price()` pide la última barra de 1 min (luego 5 min) de `MGCV6` y, desde `70b3ac0`, devuelve `(precio, antigüedad)`; el llamador descarta barras de más de `STALE_BAR_MAX_AGE_SECONDS = 20 min` | `scheduler/geometry_mgc_scheduler.py` |
| El bucle de entrada hace 20 intentos × 30 s a partir de las 7:13 CT; si ninguno trae una barra fresca, envía "ERROR: no entry data available" y registra `note: no_data_entry` | mismo archivo |
| El 1-oct se documentó "MGCV6 se quedó sin ninguna barra nueva por 700+ minutos, mientras `unreal=$0.00` se reportaba como precio en vivo" | comentario en el scheduler + `GLITCH_RESEARCH_LOG.md` |
| `70b3ac0` ("fetch_latest_price() now reports bar staleness...") está en `origin/cerebro2-dev`, autor/fecha: 1-oct-2026 09:49 -0600 | `git log origin/cerebro2-dev` |
| GEOMETRY-MGC está conectado a `cerebro2-dev` y redespliega en cada push | log del 9-sep (diagnóstico del incidente SHORT MGCV6) |
| MGC lista febrero/abril/junio/agosto/octubre/diciembre; último día de negociación = tercer último día hábil del mes de entrega → **28-oct-2026** para octubre | CME Group, especificaciones de Micro Gold (cálculo mío de la fecha; un documento de CME lo redacta distinto: confirmar en el calendario de CME) |
| Topstep: se debe operar el **front month = mayor volumen**; la plataforma rola en la ventana 4:00–5:00 PM CT con un algoritmo interno | help.topstep.com/8284108 |
**Mecanismo.** El contrato octubre entra en mes de entrega el 1-oct (primer día de aviso = último día hábil de septiembre, **30-sep**: regla de COMEX para metales, NO VERIFICADO con CME en esta sesión). La liquidez migra a diciembre antes de esa fecha; MGCV6 queda sin operaciones, Massive no tiene barra nueva, y como `resolve_front_month` sigue devolviendo MGCV6 (vence el 28-oct), el scheduler pide datos de un contrato muerto. Antes de `70b3ac0` la barra congelada se aceptaba como precio actual (el $0.00 de P&L no realizado del incidente); ahora se rechaza y el día se pierde con "no entry data".
**¿Se desplegó `70b3ac0`? NO VERIFICADO desde aquí.** Comprobación de 1 minuto en Railway (servicio GEOMETRY-MGC → Deployments): el hash del despliegue activo debe ser `70b3ac0` o posterior. Pistas en el log de un cron del 2-oct en adelante: si aparece "barra recibida pero vieja (N min > 20 min) -- descartada" el código nuevo está activo y Massive devuelve barras congeladas; si solo aparece "Esperando precio MGCV6 (n/20)…", Massive no devuelve barras para ese ticker. **Ambas causan el mismo síntoma y las dos se resuelven cambiando de contrato.**
**Qué no sé**: no puedo llamar a Massive (sin clave); que el flujo de MGCZ6 sí esté sano ahora es una **inferencia**. Prueba: `scripts/probe_massive_mgc_delay.py` (rama `cerebro2-dev`) contra `MGCV6` y `MGCZ6`.
**Corrección propuesta (en `feat/t4-mgc-handoff`)**: regla de roll determinista para el oro (`execution/contracts.py::ROLL_RULES`): el contrato se descarta a 2 días hábiles de su primer día de aviso y solo se consideran los meses activos (feb/abr/jun/ago/oct/dic). Con la regla: MGCV6 hasta el 25-sep, **MGCZ6 desde el 28-sep hasta ≈ 25-nov**, MGCG7 desde el 26-nov (probado). Si el filtro dejara cero candidatos se vuelve al comportamiento anterior. Alternativa más fiel a Topstep (selección por volumen vía `aggs` de 1 día) **NO VERIFICADA** contra la API de Massive y por eso no implementada. Efecto colateral: el paper de MGC vuelve a tener datos hoy, no el 29-oct.

## 2. (b) Handoff real (rama `feat/t4-mgc-handoff`)
Con `DRY_RUN=false`, `geometry_mgc_scheduler.py` (1) no simula ni reconcilia posición del paper (la ignora con aviso), (2) espera la compuerta de entrada de **7:13 CT** (la hora del backtest de Cerebro 2), (3) se niega a enviar si ya es la hora de flatten **de hoy** (`flatten_minutes_ct`, con calendario de cierres anticipados), (4) se niega a sobrescribir una señal sin consumir (avisa BLOCKED), (5) escribe `orden_pendiente_<GLITCH_PRODUCT>.json` (por defecto `…_mgc.json`) con **exactamente los campos de MES**: `date, side, direction, ticker, product_code, nc, sl_ticks, tp_ticks, product, intento, dry_run`, y termina. La geometría de la señal es la de la cuenta real (`REAL_CFG`, nc 3), no la del paper (`CFG`, 150K, nc 6). Un fallo de `get_front_month` (Massive caído) **ya no impide la señal** en modo real: el Pi resuelve su propio contrato. En modo real los umbrales de intento son los de la cuenta real (50K: $3,000 / $2,000 en lugar de $9,000 / $4,500); el paper no cambia.
**Riesgos que quedan (no resueltos aquí)**
- **Historial mezclado**: el Pi escribe el resultado real en `geometry_mgc_log.json`, el mismo archivo del paper de Railway (150K, nc 6). `_attempt_pnl` suma `pnl` crudo: paper y real contaminan el intento. **Antes de pasar a real hay que archivar el historial del paper** (renombrar el archivo del Gist) o empezar un historial limpio. Para ensayos usar el mecanismo de señal de ensayo del Pi (`product ≠ GLITCH_PRODUCT`, p. ej. `MGCtest`: ≤ 2 contratos, historial propio `geometry_mgctest_log.json`).
- **Dos líneas de código**: Railway MGC sigue a `cerebro2-dev`; el Pi corre `main`. El bloque de geometría es **idéntico** en ambas ramas para que el merge no choque; el handoff requiere desplegar `feat/t4-mgc-handoff` en `cerebro2-dev` y `feat/t4-pi-mgc` en `main`.
- **Cierres anticipados** (27-nov, 24-dic): el scheduler se niega a enviar tarde, pero el Pi aplana a las 14:30 fijo.
- **Cuenta nueva por cada pase/reinicio**: el pin `TOPSTEP_ACCOUNT_ID` de la instancia MGC debe actualizarse cuando la XFA tenga un `accountId` nuevo (el del API **no** es el del dashboard; si un reinicio conserva el ID: NO VERIFICADO).

## 3. (c) Alinear la geometría — una sola fuente de verdad
| Clave | Antes | Después | Uso |
|---|---|---|---|
| `CANDIDATES["MGC"]` | SL 136 / TP 45 / nc 30 (Combine descartado) | **SL = TP = 364 / nc 3** | Pi con `GLITCH_PRODUCT=MGC`; señal real XFA 50K |
| `CANDIDATES["MGC_XFA_100K"]` | — | 364 / 364 / nc 4 | XFA 100K |
| `CANDIDATES["MGC_XFA_150K"]` | (solo en `cerebro2-dev`) 364 / 364 / nc 6 | igual | paper de Railway (`DRY_RUN=true`) |
| `CANDIDATES["MGC_COMBINE_LEGACY"]` | — | el MGC anterior | referencia histórica, sin uso |
Fuente del nc por tamaño: `GLITCH_RESEARCH_LOG.md` ("A = MGC 364/364 en Combine y XFA, nc 3/4/6 para 50K/100K/150K"). Tope oficial de MGC en Combine/XFA: **30 micros** (`SPECS["MGC"].nc_cap = 30`; Risk Adjustments 13613539). El bracket de 728×3 (REPORT_STRUCTURAL_LEVERS) **sigue siendo propuesta no aprobada**: cambiarlo es editar `XFA_MGC_BRACKET_TICKS` (el validador del Pi acepta hasta 4× lo configurado, probado). Nota: el bloque `ARCHITECTURE.md` que decía "nc = 6" describe el paper de 150K; la cuenta real de Eric (50K) opera nc = 3.

## 4. (d) Segunda instancia del Pi (`GLITCH_PRODUCT=MGC`)
| Aspecto | Resultado de la revisión |
|---|---|
| Servicio | `bash pi/ops/install_service.sh --instance mgc [--start]` → `glitch-pi-executor-mgc.service`, entorno `~/.glitch_pi_mgc.env`, log `pi_executor_mgc.log`, estado `~/.glitch_pi_state_mgc`; la instancia por defecto no cambia (`GLITCH_PI_STATE_DIR` = HOME). Detecta "ejecutor suelto" ignorando los PIDs de **todas** las unidades `glitch-pi-executor*` |
| Conflicto de producto | se niega a instalar si otro `~/.glitch_pi*.env` fija el mismo `GLITCH_PRODUCT` (los archivos del Gist son por producto: `orden_pendiente_`, `pi_position_`, `pi_block_notice_`, `geometry_…_log`) |
| Marcador at-most-once y spool | por producto **y** por directorio de estado: separados |
| Telegram | prefijo `S10GLITCH - PI EXECUTOR - MGC` ≠ `… - MES` |
| Watchdog | `install_watchdog.sh --instance mgc` (marca de cron, estado y log propios; la marca no contiene la de la instancia por defecto, probado) |
| **Guardia de posición huérfana** | `_has_untracked_position`, `_confirm_flat`, `_observed_size`, `_position_still_open` filtran por **`contractId`**; las verificaciones de órdenes comparan por **id**; el flatten es `close_contract(contrato)`. **No confunde MES con MGC**, aunque compartan cuenta |
| Lo que sí comparten dos instancias en la misma cuenta | el MLL y el P&L no realizado de la cuenta (una pérdida de MES reduce el cojín de MGC) y la hora (MGC entra 7:13, MES 9:45; ambos aplanan 14:30). Por eso la Practice se asigna **a un producto por vez** (§5) |
| Resolución del contrato | ver §1: `activeContract` primero, aviso si cae al vencimiento más cercano, aviso (una vez por arranque) si `tickSize`/`tickValue` del contrato no coinciden con la spec local |
| Riesgo residual | `product_code in name` sigue siendo una coincidencia por subcadena (`"MGC" in "MGCZ6"`); correcta para MES/MGC, no para códigos que contengan a otros (p. ej. `GC` dentro de `MGC`) |

## 5. (e) ¿Segunda cuenta Practice? Diseño seguro en una sola
**Oficial (help.topstep.com/8284134)**: la Practice es de **150K** (sin importar el tamaño del Combine), máximo **15 lotes**, **1 cuenta a la vez**, existe mientras haya un Combine activo, reset gratis hasta 10 veces al día. **No** se publica una segunda Practice ni acceso por API (que `28514663` funcione con el Pi es evidencia empírica de Eric, no documentación). Si hace falta una segunda: Trader Support.
**Diseño en la misma Practice `28514663`**
1. **Una instancia por producto y un producto por día en la Practice.** Desde el lun 19-oct la instancia MES pasa a la Combine real (`28197705`; hay que sacarla de `TOPSTEP_ACCOUNT_DENY`), así que la Practice queda libre para MGC. Dos instancias MES (una real, una Practice) están **prohibidas** (mismo producto = mismos archivos del Gist).
2. **Aislar el historial**: ensayar con señales de ensayo (`product = MGCtest`, ≤ 2 contratos, historial `geometry_mgctest_log.json`) hasta la etapa 4; recién entonces el producto real.
3. **Límite de la Practice**: es 150K con MLL ≈ $4,474 de margen (commit `2ed2ec2`): un stop de MGC 364×3 cuesta ≈ $1,092 + comisión, sin riesgo de liquidar la Practice; en cambio **no reproduce el MLL de $2,000, el trabado en $0, el escalado ni los pagos de la XFA 50K**. Valida: contrato activo, bracket, fills, flatten, conciliación, Telegram, historial; no valida la dinámica de la cuenta.
4. **Ventanas**: MGC 7:13–14:30; si se quiere ensayar MES en la misma Practice, otro día (alternar), nunca con una posición del otro abierta.

## 6. (f) Plan de ensayo, criterios y duración
### 6.1 Etapas
| Etapa | Qué | Cuándo | Aprobado si | Falla si |
|---|---|---|---|---|
| 0. Revisión y verificación | Eric revisa las 2 ramas (regla 4); corre `pi/ops/check_contracts.py --products MES,MGC` en el Pi; confirma el despliegue de `70b3ac0` en Railway | 13–16-oct | La API trae `activeContract`; el activo de MGC es el de diciembre; sin hallazgos de spec | falta `activeContract` o la spec difiere: no avanzar |
| 1. Paper con la regla de roll | Desplegar la rama del scheduler en `cerebro2-dev` con `DRY_RUN=true` | 26–28-oct (3 sesiones) | ticker = `MGCZ6`; barra ≤ 20 min a las 7:13 en 3/3 sesiones; cero "no entry data" | cualquier "no entry data" o ticker ≠ Z6 |
| 2. Señal sin ejecución | `DRY_RUN=false` en Railway; Pi con el gate de Fase 3 **cerrado** | 29-oct (2 sesiones) | señal con campos exactos; Pi avisa BLOCKED una vez y **no toca el broker**; sin sobrescritura | señal ≠ contrato, o el Pi toca el broker |
| 3. Practice, nc = 1 | Instancia MGC pinneada a `28514663`, `GLITCH_PI_NC_MAX=1`, señales de ensayo | **vie 30-oct →** 10 sesiones (≈ 12-nov) | Por sesión: señal consumida una vez; bracket (entrada+TP+SL) confirmado ≤ 10 s; cierre por TP, SL o FLATTEN; cuenta plana a las 14:35; P&L del historial = P&L del broker ± $2; slippage de entrada ≤ 2 ticks. Global: ≥ 1 TP o SL **y** ≥ 1 FLATTEN observados; prueba de reinicio con posición abierta superada; día sin señal = sin operación | evento rojo duro (bracket sin proteger, orden duplicada, posición abierta tras 14:35, contrato no activo, cuenta equivocada) → reiniciar el conteo |
| 4. Practice, nc = 3 | Mismo, tamaño de la XFA 50K, producto real | 13–19-nov (5 sesiones) | mismos criterios | mismos |
| 5. XFA real | Pin a la cuenta XFA y gate de Fase 3 abierto para MGC | desde ≈ 20-nov (o antes: §6.3) | luz verde de Eric | — |
Duración mínima: **15 sesiones** (10 + 5) tras la etapa 2; pruebas obligatorias dentro de las etapas 3–4: reinicio del servicio con posición abierta, día sin señal, señal de un día anterior (descartada), Gist caído (spool), pérdida breve de red a media posición.
### 6.2 Métricas (reusan T3)
Registro diario de fricción (`friction_collect.py`), margen de la Practice (< $1,500), semáforo de `REPORT_STACKING_TIMING` §3; para MGC el tick es 0.1 ($1 por contrato): los umbrales se mantienen en **ticks** (entrada ≤ 1 verde / ≤ 2 amarillo).
### 6.3 El conflicto de calendario y el plan puente (decisión de Eric)
P(≥ 1 pase en 10 días hábiles) = 91% (`REPORT_STACKING_TIMING` §2): la 1.ª XFA se activará hacia **2–4-nov**, antes de terminar las etapas 3–4. Opciones: **(A)** no operar la XFA hasta la luz verde (la XFA se cierra tras 30 días de inactividad; se pierde ≈ 2 semanas de operación y los $149 de activación ya pagados no se recuperan); **(B)** operar la XFA a mano (Telegram) hasta el 20-nov (error humano a 7:13 CT; no replica el modelo); **(C)** acortar el ensayo: luz verde con **≥ 5 sesiones limpias a nc = 1** (con ≥ 1 salida por TP o SL, 1 FLATTEN y la prueba de reinicio) ≈ **vie 6-nov**, y subir a nc = 3 directamente en la XFA con vigilancia reforzada. **Recomendación: (C) si Eric acepta el riesgo; si no, (A).** Confianza media: la diferencia entre 5 y 15 sesiones es riesgo operativo, no de modelo.

## 7. Lista de lo no verificado
1. Que `70b3ac0` esté desplegado en Railway (verificar el hash del despliegue).
2. Que MGCZ6 hoy tenga barras frescas en Massive (inferencia).
3. Que ProjectX devuelva `activeContract` y que marque el contrato de mayor volumen (`check_contracts.py`).
4. El primer día de aviso del oro (30-sep) y el último de negociación (28-oct): confirmar con el calendario de CME.
5. Si un reinicio conserva el `accountId`.
6. Los campos reales de `Order/search` (ya mencionado en T3) y que `Account/search` entregue saldo en tiempo real.
7. Que la Practice permita 40/30 micros de MGC (15 lotes = 150 micros por la regla 10:1; no probado).

## 8. Decisiones de Eric
1. Revisar y aprobar (o no) las dos ramas; ¿se despliega `feat/t4-mgc-handoff` en `cerebro2-dev` y se mantiene Railway MGC allí?
2. ¿Archivar el historial del paper de MGC antes del primer día real? (recomendado)
3. Plan puente: (A), (B) o (C) del §6.3.
4. ¿Se acepta la regla de roll determinista como solución definitiva o se prefiere la selección por volumen tras verificarla contra Massive?
5. Resolver los cierres anticipados del Pi antes del 27-nov (afecta a MES y a MGC).
