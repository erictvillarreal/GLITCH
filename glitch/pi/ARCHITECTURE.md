# Railway vs. Pi — división de responsabilidades (referencia fija)

Estado verificado contra el código el **03-oct-2026** (rama `origin/main` @ `9378116` + `pi/ops-hardening`).
Si el código cambia, este documento cambia en el mismo commit — no es un resumen de memoria.

## Regla de fondo

**Quien calcula la señal vive en Railway. Quien transmite órdenes al broker vive en el Pi.**

Topstep exige que las órdenes se originen desde un dispositivo personal (sin VPS/VPN/servidor remoto —
help center + Términos de Uso §28, ver `GLITCH_RESEARCH_LOG.md`, 24–25 sep y 30 sep). Railway es un servidor
remoto, así que **nunca** habla con ProjectX/TopstepX. El Pi sí, y **nunca** calcula una señal.

## Qué hace cada lado

| | **Railway** (`scheduler/geometry_scheduler.py`) | **Pi** (`pi/pi_executor.py`) |
|---|---|---|
| Decide la dirección del día (`decide_side`, `trading_day_index`) | ✅ | ❌ nunca |
| Resuelve el front-month **de datos** (Massive) y obtiene precios de mercado de Massive | ✅ | ❌ no usa Massive |
| Lleva el historial/intento (PASE / QUIEBRE, `_current_intento`, `_attempt_pnl`) | ✅ | ❌ solo **agrega** su resultado al mismo historial |
| Telegram de inicio de día / resumen | ✅ | solo OPEN / CLOSE / BLOCKED / ALERTA del ejecutor |
| `DRY_RUN=true` (paper) | ✅ simula el ciclo completo y escribe el resultado | ❌ no hace nada con una señal paper |
| `DRY_RUN=false` | escribe la señal a `ORDER_FILE` y **termina** (no simula, no monitorea) | ✅ consume la señal |
| Se autentica contra ProjectX, resuelve `accountId` y `contractId` (de ProjectX, no de Massive) | ❌ | ✅ |
| Precio de referencia para TP/SL | — | ✅ barras de ProjectX (`_reference_price`), no Massive |
| Coloca el bracket (entrada de mercado + TP límite + SL stop, **las tres juntas**) | ❌ | ✅ |
| Monitorea hasta TP / SL / flatten de fin de sesión (poll 30 s, heartbeat cada ~5 min) | ❌ | ✅ |
| Flatten de fin de sesión (14:30 CT) | — | ✅ `closeContract` (no depende del lado) |
| Reconciliación tras un reinicio | `_reconcile_pending_position` (**estima** desde el precio, marca `RECONCILED`) | `reconcile_if_needed` (**pregunta al broker**: `get_open_orders`) |
| Guardia contra una posición huérfana antes de operar | — | ✅ `_has_untracked_position` |

## Estado compartido — todo en el mismo Gist (`execution/gist_store.py`, mismo `GIST_ID`)

| Archivo en el Gist | Tipo | Lo escribe | Lo lee / consume |
|---|---|---|---|
| `orden_pendiente_{producto}.json` | estado | Railway (solo con `DRY_RUN=false`; se niega a sobrescribir una señal sin consumir) | Pi — lo limpia a `{}` al cerrar el ciclo |
| `pi_position_{producto}.json` | estado | Pi (bracket en curso: ids de órdenes, TP/SL, `phase`) | Pi (reconciliación) — Railway nunca lo toca |
| `pi_block_notice_{producto}.json` | estado | Pi (una alerta BLOCKED por día y razón) | Pi |
| `geometry_{producto}_log.json` | historial | **Ambos**, mismo esquema de entrada | Railway (intento/PASE/QUIEBRE/pass rate) |

El historial mixto paper+real funciona sin cambios en Railway porque el Pi escribe el mismo esquema.

## Variables de entorno — quién necesita qué

| Variable | Railway | Pi |
|---|---|---|
| `MASSIVE_API_KEY` (o `POLYGON_API_KEY`) | ✅ | ❌ no la necesita |
| `TOPSTEP_USERNAME`, `TOPSTEP_API_KEY` | ❌ **nunca** | ✅ solo en el Pi |
| `GITHUB_GIST_TOKEN`, `GIST_ID` | ✅ | ✅ mismo valor (mismo Gist) |
| `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` | ✅ | ✅ mismo bot y chat |
| `GLITCH_PRODUCT` | ✅ (`MES`, …) | ✅ (debe coincidir con el scheduler que alimenta) |
| `DRY_RUN` | ✅ (`true` por default) | — |
| `GLITCH_PI_PHASE3` | — | ✅ gate de Fase 3 (ver abajo) |
| `TOPSTEP_ACCOUNT_ID` | — | ✅ **obligatoria**: la cuenta fijada (Demo Pi = Practice `28197753`) |
| `TOPSTEP_ACCOUNT_DENY` | — | opcional: cuentas vetadas (default `28197705`, la Combine; vacía = sin lista) |
| `GLITCH_PI_ENTRY_DEADLINE_CT` | — | opcional: hora límite de entrada `HH:MM` CT (default `10:00`) |
| `GLITCH_PI_STATE_DIR` | — | opcional: dónde guarda el Pi su estado local (default: el HOME del servicio) |

En el Pi viven en `~/.glitch_pi.env` (`chmod 600`, fuera de git) y los lee systemd (`EnvironmentFile`).

## Gates e invariantes (no negociables)

1. **Gate de Fase 3 (22-sep).** `pi_executor` no coloca ninguna orden real sin `GLITCH_PI_PHASE3=si` **y**
   `pi/orderside_verified.json`. Sin ambos, solo avisa BLOCKED (una vez al día) y no toca la red del broker.
2. **El lado compra/venta nunca sale de `brokers.projectx.OrderSide`.** Verificado en vivo el 4-oct-2026: `side=0`
   abre una posición LONG, o sea `0=Buy` (la doc oficial tenía razón; los nombres/comentarios del enum están
   invertidos y siguen así a propósito para no cambiar en silencio a los llamadores legados). El lado sale
   únicamente de `orderside_verified.json` (`{"BUY_SIDE_INT": 0, "SELL_SIDE_INT": 1}`), que escribió
   `pi/verify_orderside_demo.py` tras una orden real de prueba en la cuenta Practice.
3. **Entrada y protección siempre juntas:** nunca hay una entrada sin su SL ya colocado.
4. **Una sola instancia del ejecutor.** Nunca `nohup` y systemd a la vez. `install_service.sh` se niega a arrancar
   el servicio si encuentra un `pi_executor.py` suelto.
5. **Cuenta fijada, siempre:** `TOPSTEP_ACCOUNT_ID` es **obligatoria** (`require_env` impide arrancar sin ella) y se valida
   contra las cuentas activas; nunca se adivina ni se toma "la única activa". Además, la Combine `28197705` está en una
   lista de denegación por defecto (`TOPSTEP_ACCOUNT_DENY`; vacía la desactiva para la Fase 3 real).
6. **Límites duros de riesgo en código determinista, nunca en un LLM** (`CLAUDE.md`, regla 1). El Pi no tiene
   ninguna llamada a un LLM en el camino crítico.
7. **Todo cambio a este código requiere revisión humana antes de merge** (`CLAUDE.md`, regla 4).

## Salvaguardas de ejecución (auditoría del 04-oct-2026; detalle en `AUDIT_2026-10-04.md`)

Orden real de `run_once()` para una señal: reconcile → señal vacía → `_signal_is_current` (fecha CT) → **`_validate_signal`**
(cota superior contra `CFG`: nc ≤ 40, ticks ≤ 4× lo configurado, producto, lado) → **ventana de entrada** (default hasta 10:00 CT)
→ **marcador local at-most-once** → gate Fase 3 → cuenta fijada + denylist → guard de posición huérfana → precio de referencia →
**reclamar la señal (marcador en disco, ANTES de la orden)** → entrada + TP + SL → **confirmar que la posición existe** → poll →
**verificar cuenta plana y sin órdenes huérfanas** antes de dar el ciclo por cerrado → historial (lectura estricta, spool si falla).

* **Una señal real se ejecuta a lo más una vez**, aunque el PATCH que la limpia falle en silencio (`gist_store._write_file` traga
  errores). El marcador vive en el disco del Pi (`.glitch_pi_executed_<producto>.json`), no en el Gist.
* **Un ciclo no se cierra a ciegas.** TP y SL son dos órdenes sueltas, no un OCO: "una pata desapareció ⇒ se llenó" es una inferencia.
  Se re-lee y se comprueba contra el broker; una posición abierta (invertida, parcial) se cierra y se avisa.
* **El historial compartido no se sobrescribe a ciegas.** Si falla la lectura o la escritura, la entrada queda en un spool local
  (`.glitch_pi_unsynced_log_<producto>.jsonl`) y se avisa con la entrada completa.
* **Señales de ensayo** (`product != GLITCH_PRODUCT`, p. ej. `MEStest`, ≤ 2 contratos) escriben a su propio historial y están
  exentas del marcador y de la ventana horaria para poder repetir ensayos después de las 14:30.
* Los `200` con `success:false` de la API ya no se leen como "lista vacía" (`brokers/projectx._items` lanza).

## Operación en el Pi (`pi/ops/`)

`diagnose_reboot.sh` (solo lectura) · `glitch-pi-executor.service.template` + `install_service.sh` (systemd,
`Restart=always`) · `watchdog.py` + `install_watchdog.sh` (cron, alerta por Telegram si el log deja de crecer).
Detalle y comandos: `pi/ops/README.md`.

## Huecos conocidos (abiertos — no escondidos)

* **Cerebro 2 (MGC XFA): handoff y geometría en revisión (T4, 12-oct-2026).** Rama `feat/t4-mgc-handoff` (sobre `cerebro2-dev`): `geometry_mgc_scheduler.py`
  con `DRY_RUN=false` escribe `orden_pendiente_mgc.json` (mismo contrato que MES; `signal["product"]` DEBE ser idéntico al `GLITCH_PRODUCT` del Pi o éste la trata
  como señal de ensayo). Esta rama alinea `CANDIDATES["MGC"]` a la XFA 50K real (SL=TP=364, nc=3; antes SL136/TP45, nc=30, descartada) con alias `MGC_XFA_100K`/`MGC_XFA_150K`.
  **Pendiente de revisión humana y de ensayo en Practice**; `geometry_scheduler.py` (MES) sigue sin poder correr MGC (exige `yf_ticker`).
* **Front month = el de mayor volumen (Topstep), no el de vencimiento más cercano.** `resolve_contract_id` prefiere `activeContract: true` (campo de ProjectX, NO VERIFICADO en
  vivo: correr `pi/ops/check_contracts.py` en el Pi) y avisa si cae al vencimiento más cercano; avisa (una vez por arranque) si `tickSize`/`tickValue` del contrato difieren de la spec local.
* **Segunda instancia del Pi (otro producto).** `bash pi/ops/install_service.sh --instance mgc` crea `glitch-pi-executor-mgc.service` con su propio entorno (`~/.glitch_pi_mgc.env`),
  log, `GLITCH_PI_STATE_DIR` y watchdog (`install_watchdog.sh --instance mgc`); se niega a instalar dos instancias con el mismo `GLITCH_PRODUCT` (los archivos del Gist se nombran por producto).
  Las guardias de posición son por `contractId` y las de órdenes por id: una instancia MES y una MGC en la MISMA cuenta no se confunden (pero comparten el MLL de la cuenta).
* **El Pi no maneja cierres anticipados.** `FLATTEN_HOUR, FLATTEN_MINUTE = 14, 30` es fijo. En 27-nov y 24-dic
  (cierre 12:00 CT) el flatten debe ser 11:30 CT — ya existe para los schedulers de Railway
  (`execution/session_calendar.py`, commits locales `ba88626`/`d0d06ce`) pero **no está en `origin/main`** (la rama
  `main` local y `origin/main` divergieron) y `pi_executor` no lo usa. Hay que resolverlo antes del 27-nov.
* **Resuelto el 4-oct-2026 con la primera corrida real de `verify_orderside_demo.py` (Practice):** la forma real de
  una posición es `type` (1=Long, 2=Short) + `size` — **`netPos` no existe**; el endpoint que funciona es
  `Position/searchOpen` (y `Order/searchOpen` para órdenes abiertas); `closeContract` cerró la posición y la cuenta
  quedó plana. `get_positions`/`get_open_orders`/`_has_untracked_position` se corrigieron (`position_net`,
  `position_is_open` en `brokers/projectx.py`). Antes de esto la guardia de posición huérfana era ciega.
* **Todavía sin verificar contra la API real:** la colocación del *bracket* completo (entrada + TP límite + SL stop
  con el mapeo verificado), la forma de las órdenes en `Order/search` usada solo para leer el fill price
  (best-effort), y el flujo completo de `poll_position_until_closed`. La primera señal real en Practice es la prueba.
* **Cuenta del Pi:** desde el 1-oct hay DOS cuentas activas (Combine `28197705` y Practice `28197753`).
  `TOPSTEP_ACCOUNT_ID` en `~/.glitch_pi.env` fija la cuenta (obligatoria desde la auditoría del 4-oct) y se valida contra
  las cuentas activas y la lista de denegación. Para el Demo Pi debe ser `28197753`. Si la Practice se liquida o se
  reinicia, la cuenta nueva trae OTRO id: hay que actualizar la variable y reiniciar el servicio.
* **Señales viejas:** una señal sin consumir de un día anterior (CT) se descarta con aviso y se limpia
  (`_signal_is_current`), porque el scheduler de Railway no escribe una señal nueva mientras haya una sin consumir.
* **Riesgo residual documentado en `pi_executor.py`:** si el proceso muere entre colocar las 3 órdenes y guardar
  `pi_position_*.json`, queda una posición real sin registro; la guardia lo detecta pero no lo resuelve solo.
