# Raspberry Pi Migration Playbook — Cerebro 1/2 Real Execution

**Propósito:** que el día que el Raspberry Pi llegue físicamente, exista una secuencia de pasos ejecutable, sin tener que investigar ni decidir nada en el momento. Este documento no diseña nada nuevo — consolida el diseño ya hecho en la rama `design/pi-execution` (`pi/pi_executor.py`, commit `c47efb7`, 11-sep-2026) en forma de checklist, y agrega lo que faltaba: pre-requisitos, setup de hardware/OS, plan de fallas, y secuencia de transición.

**Estado del diseño verificado hoy (22-sep-2026):** `pi/pi_executor.py` sigue siendo pseudocódigo puro — 8 funciones con `raise NotImplementedError`, cero cambios desde el 11-sep. Nada de esto está implementado todavía.

**Una fecha en este documento NO está verificada contra el research log:** la ventana de paper trading del Pi "1–15 de octubre" viene de la instrucción del usuario ("ya acordado"), no encontré ningún registro de esa fecha en `GLITCH_RESEARCH_LOG.md`. La uso tal cual me la dieron, marcada explícitamente aquí para que quede claro que no es un hecho que yo haya confirmado de forma independiente.

---

## 1. Inventario — qué se mueve exactamente

### 1.1 Archivos/módulos que viven en el Pi

| Archivo | Estado hoy | Acción antes del hardware |
|---|---|---|
| `pi/pi_executor.py` | Pseudocódigo (8 `NotImplementedError`) | Implementar y probar contra cuenta de práctica — ver Sección 2 |
| `execution/gist_store.py` | Completo, en producción (Railway) | Ninguna — se reusa **sin modificar**, mismo `GIST_ID` |
| `scheduler/telegram_bot.py` | Completo, en producción | Ninguna — se reusa **sin modificar**, mismo bot/chat |
| `brokers/projectx.py` | Huérfano, no lo importa ningún scheduler actual | **NO usar como base** — tiene el `OrderSide` invertido respecto a la doc oficial confirmada (ver Sección 2, bloqueante #1). Solo se rescataron ideas de arquitectura (patrón `ensure_auth`, nombres de env vars), no sus valores |

**Lo que se queda en Railway, sin tocar:** cálculo de señal (`decide_side`, `strategies/geometry_pure.py`), resolución de front-month para logging/alertas (Massive, `execution/contracts.py`), todo el tracking histórico (`_current_intento`, `_attempt_pnl`, `_paper_progress`, y ahora también `_replay_payout_cycles` en `geometry_mgc_scheduler.py`) — sigue leyendo el mismo `geometry_{producto}_log.json`, ahora alimentado por datos reales el día que se active ejecución real, sin ningún cambio de código ahí.

### 1.2 Dependencias de Python en el Pi

**Solo `requests`.** Confirmado en el diseño original: tiene wheels universales (`py3-none-any`), sin compilación nativa en ARM64. Sus propias dependencias (`urllib3`, `certifi`, `idna`, `charset-normalizer`) también tienen soporte ARM64 estándar en PyPI.

**Explícitamente NO en el Pi:** numpy, pandas, scipy, polars, plotly, pydantic, ningún SDK de terceros (project-x-py, tsxapi4py, etc. — evaluados y descartados en el diseño original, ver research log 11-sep-2026). Todo eso es responsabilidad exclusiva de Railway.

### 1.3 Variables de entorno / credenciales del Pi

| Variable | Dónde vive | Compartida con Railway? |
|---|---|---|
| `TOPSTEP_USERNAME` | **Solo en el Pi** | NO — nunca en Railway (misma razón por la que la ejecución no puede vivir ahí) |
| `TOPSTEP_API_KEY` | **Solo en el Pi** | NO |
| `TOPSTEP_ACCOUNT_ID` | **Solo en el Pi** | NO — confirmar via `Account/search` la primera vez, no adivinar por posición en una lista |
| `GITHUB_GIST_TOKEN` | Pi (reusa el valor de Railway) | Sí — mismo Gist compartido, mismo token, mismo `GIST_ID` |
| `GIST_ID` | Pi (reusa el valor de Railway) | Sí |
| `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID` | Pi (reusa el valor de Railway) | Sí — mismo bot, mismas alertas en el mismo chat |
| `GLITCH_PRODUCT` | Pi | Concepto compartido (mismo patrón que `PRODUCT_KEY` en los schedulers), valor específico al producto que ese Pi ejecuta |

**No necesita:** `MASSIVE_API_KEY` — el Pi resuelve su propio `contractId` contra la API de ProjectX (namespace de ticker distinto al de Massive, sin traducción confiable entre ambos, ver diseño original punto 4).

---

## 2. Pre-requisitos — completar ANTES de que llegue el hardware

Nada de esto necesita el Raspberry Pi físico. Todo se puede hacer desde cualquier máquina con internet (laptop, o temporalmente en Railway) contra una cuenta de práctica de ProjectX/TopstepX.

- [ ] **BLOQUEANTE #1 — el más crítico de todos:** verificar empíricamente el `OrderSide` (¿0 = compra o 0 = venta?) contra una orden real en cuenta de PRÁCTICA. La documentación oficial dice `0=Bid=buy, 1=Ask=sell`; el código huérfano `brokers/projectx.py` dice lo contrario. Una de las dos fuentes está invertida — operar con el lado equivocado mueve dinero real en la dirección contraria a la señal. **No colocar ninguna orden en cuenta fondeada sin haber confirmado esto con un fill real en demo.**
- [ ] Solicitar credenciales de cuenta de práctica/demo de ProjectX/TopstepX (necesarias para el punto anterior y para todo lo que sigue).
- [ ] Confirmar si la cuenta está en modo **"Auto OCO Brackets"** — determina si `place_bracket_order()` puede usar el bracket nativo (`stopLossBracket`/`takeProfitBracket` en una sola orden) o necesita el fallback de 3 órdenes separadas (entry + TP + SL, cancelando la que no se llene) que ya está documentado como alternativa válida en el diseño, no como bug.
- [ ] Confirmar cuál `accountId` corresponde a la cuenta de práctica y cuál a la futura cuenta fondeada, vía `Account/search` — nunca asumir por posición en una lista.
- [ ] Implementar las 8 funciones de `pi/pi_executor.py` (`authenticate`, `ensure_fresh_token`, `resolve_contract_id`, `place_bracket_order`, `poll_position_until_closed`, `reconcile_if_needed`, `append_to_historic_log`, `run_once`) y probarlas contra la cuenta de práctica. Objetivo: que el día que el hardware llegue, el trabajo sea **desplegar**, no **programar**.
- [ ] Confirmar el mecanismo de comunicación Gist (`orden_pendiente_{producto}.json`, ya diseñado 11-sep-2026) sigue siendo el plan — **confirmado hoy**: sin cambios desde el diseño original, nada lo contradice.
- [ ] Implementar el cambio de código **en Railway** (no en el Pi) que el diseño original marcó como necesario: `DRY_RUN` en `geometry_scheduler.py`/`geometry_mgc_scheduler.py` hoy es solo una etiqueta (se loguea, se guarda, pero el `run()` siempre simula el ciclo completo sin importar su valor — confirmado de nuevo hoy, sin cambios). Antes de activar ejecución real, `run()` necesita una rama real: si `DRY_RUN=false`, escribir `orden_pendiente_{producto}.json` y terminar ahí (no simular, no mandar CLOSE, no hacer `append` al log histórico ese día — eso pasa a ser trabajo del Pi).
- [ ] Confirmar el `Retry-After`/backoff ante un 429 real (la doc no lo especificaba al momento del diseño) — verificar si la cuenta de práctica expone ese header antes de confiar en el backoff fijo ya propuesto.

---

## 3. Setup del hardware — primera vez

- [ ] **Sistema operativo:** Raspberry Pi OS 64-bit (Bookworm o más reciente), grabado con Raspberry Pi Imager.
- [ ] **Python:** confirmar la versión preinstalada (Bookworm trae 3.11+ típicamente); si no, instalar 3.11+ vía `apt` o `pyenv`.
- [ ] **Entorno aislado:** crear un venv dedicado (`python3 -m venv ~/glitch-pi/venv`), `pip install requests` — nada más.
- [ ] **Red — verificación de salida, antes de correr nada:**
  ```bash
  curl -sS https://api.topstepx.com/ -o /dev/null -w "%{http_code}\n"
  curl -sS https://api.github.com/ -o /dev/null -w "%{http_code}\n"
  curl -sS https://api.telegram.org/ -o /dev/null -w "%{http_code}\n"
  ```
  Confirmar que ninguno está bloqueado por el firewall del router/ISP antes de asumir que el diseño funciona igual que desde Railway (datacenter).
- [ ] **IP estática local:** no es un requisito funcional (el Pi solo hace llamadas salientes, no expone ningún servicio) — pero conviene una reserva DHCP en el router para que SSH de administración remota sea predecible.
- [ ] **SSH:** habilitar, cambiar la contraseña default, preferir autenticación por llave sobre contraseña.
- [ ] **Arranque automático — systemd, NO cron:** `pi_executor.py` está diseñado como un daemon de larga duración (`while True`, mantiene el JWT en memoria entre polls) — cron es para invocaciones puntuales periódicas (así corren los schedulers de Railway), no para un proceso persistente. Ejemplo de unit file:
  ```ini
  # /etc/systemd/system/glitch-pi-executor.service
  [Unit]
  Description=GLITCH Pi Executor
  After=network-online.target
  Wants=network-online.target

  [Service]
  Type=simple
  User=pi
  WorkingDirectory=/home/pi/glitch-pi
  EnvironmentFile=/home/pi/glitch-pi/.env
  ExecStart=/home/pi/glitch-pi/venv/bin/python pi/pi_executor.py
  Restart=on-failure
  RestartSec=30

  [Install]
  WantedBy=multi-user.target
  ```
  `EnvironmentFile` mantiene las credenciales fuera del unit file mismo (permisos `600`, nunca en git).

---

## 4. Plan de fallas — anticipado con la experiencia real de esta sesión

| Escenario | Ya visto en Railway | Respuesta en el Pi |
|---|---|---|
| **Pérdida de conexión a mitad de una posición abierta** | Sí — incidente SHORT MGCV6 (09-sep-2026), resuelto con reconciliación de crash | `reconcile_if_needed()` ya está diseñado exactamente para esto, y es **estructuralmente mejor** que el de Railway: le pregunta al broker (`Position/searchOpen`, `Order/search`) qué pasó de verdad, en vez de estimar contra precio de mercado. Se porta tal cual, sin cambios de diseño — confirmar que se implementó (Sección 2) antes de confiar en él. |
| **Corte de luz** | Nunca — Railway es nube, no tiene este riesgo | **Riesgo nuevo, real.** Aclaración importante: si el Pi se apaga con una posición abierta, la posición **no queda descubierta** — el bracket SL/TP ya está colocado del lado del broker (Topstep), sigue activo aunque el Pi esté muerto. El riesgo real es que el Pi no se entera de cuándo cerró y no lo registra a tiempo (mismo tipo de gap que MGCV6, pero el capital sigue protegido por el bracket real, no por el Pi). Mitigación recomendada: un UPS chico (~$30–60, autonomía de minutos a un par de horas según carga) para dar tiempo a reiniciar sin perder la sesión de monitoreo; si no se consigue antes del hardware, aceptar el riesgo con la reconciliación como red de seguridad — no es bloqueante, pero sí conviene resolverlo pronto. |
| **El delay de red desde el Pi es distinto al medido desde Railway** | Sí — dos veces (Yahoo errático con MES=F, costó 2.5 semanas; Massive medido explícitamente para MGC, 2 corridas en horarios distintos) | **No asumir que el delay medido desde un datacenter aplica igual desde una IP residencial.** Mismo estándar ya aplicado dos veces en este proyecto ("medir, no asumir"): repetir el mismo patrón de `probe_massive_mgc_delay.py` pero contra la API de ProjectX, desde el Pi real, en al menos 2 corridas en horarios distintos, durante los primeros días del período de paper trading (Sección 5b) — no antes de eso, porque necesita el hardware real conectado a la red real. |
| **Bugs de import, rutas de archivo, variables de entorno faltantes** | Sí — 2.5 semanas de incidentes uno-a-la-vez en combo2d (14-ago a 01-sep-2026), resuelto con `execution/env_check.py` (chequeo unificado al arranque, fail-loud) | El Pi debería tener su **propio chequeo unificado** de env vars al arranque, mismo principio que `env_check.py` — fallar ruidosamente con un mensaje que liste TODAS las variables faltantes de una vez, no una por una en crashes sucesivos. Agregar esto durante la implementación de Sección 2, no como ocurrencia tardía. |
| **Confiar en código sin probarlo primero** | Sí — combo2d necesitó un "Run manual" para confirmar limpio antes de dejarlo desatendido | Mismo principio: correr `run_once()` manualmente, una vez, contra la cuenta de práctica, con supervisión activa, **antes** de habilitar el systemd service en modo desatendido. |
| **Ventana de mantenimiento / "freeze window" equivalente** | Sí — `main`/`cerebro2-dev` tienen freeze windows durante horario de mercado del producto que despliegan | No es idéntico (el Pi no recibe "pushes" de código en caliente de la misma forma), pero el análogo real es: no reiniciar el systemd service ni actualizar `pi_executor.py` mientras haya una posición abierta o durante la ventana de mercado activo del producto que ese Pi opera. Reservar cambios/actualizaciones para fuera de horario. |

---

## 5. Secuencia de transición — el día que el Pi esté listo

### 5a. Setup y pruebas en aislamiento (sin tocar producción de Railway)
1. Completar Sección 3 (hardware/OS).
2. Correr `pi_executor.py` contra la cuenta de **práctica**, usando un `GIST_ID`/archivo de prueba **separado** del de producción — para no interferir con el estado real de Railway mientras se prueba.
3. Confirmar, en este orden: autenticación → resolución de `contractId` → una orden simulada contra la cuenta demo → polling de posición → reconciliación (matar el proceso a propósito a mitad de una posición demo, confirmar que se recupera sin intervención manual).

### 5b. Periodo de paper trading en el Pi (1–15 de octubre, según lo indicado — ver nota de la cabecera sobre esta fecha)
- **Recomendación: el Pi corre en paralelo a Railway, no lo reemplaza ni lo pausa.** El Pi en modo `DRY_RUN=true` (paper), comparando sus propios resultados día a día contra los de Railway — esto valida el pipeline de ejecución completo (auth, red, resolución de contrato, polling) contra datos reales de mercado, sin arriesgar capital, mientras Railway sigue operando exactamente como hoy. Nada en el diseño actual requiere pausar Railway durante este período.
- Durante este período: ejecutar las mediciones de delay de red pendientes de la Sección 4 (mínimo 2 corridas en horarios distintos).

### 5c. Criterio de "listo para Combine real"
Mismo tipo de criterio ya usado para la ventana de 20 días de Cerebro 1 (pass_rate empírico no cae más de ~15-20pp del teórico, evaluado por un humano al cierre, no automatizado) — adaptado a lo que es específico de esta transición de infraestructura:

- [ ] El bloqueante #1 (`OrderSide`) está **resuelto y verificado** contra la cuenta de práctica — esto es un prerequisito de la Sección 2, no algo que se resuelve durante este período.
- [ ] Cero errores de infraestructura no manejados durante los 15 días (auth, red, Gist) — cualquier falla real debe haber sido capturada por las alertas fail-loud, no un crash silencioso sin registro.
- [ ] Al menos 2 mediciones de delay de red completadas desde el Pi real, en horarios distintos.
- [ ] La reconciliación se probó al menos una vez con un kill deliberado del proceso a mitad de una posición (demo o paper), confirmando recuperación sin intervención manual.
- [ ] Evaluación final: un humano decide al cierre del período, igual que con Cerebro 1 — este documento no automatiza esa decisión.

---

## 6. Estado actual vs. pendiente

| Pieza | Estado hoy (22-sep-2026) |
|---|---|
| Diseño Railway↔Pi (qué se queda, qué se mueve) | ✅ Completo (11-sep-2026) |
| Investigación de la API oficial de ProjectX | ✅ Completo (auth, órdenes, posiciones, rate limits) |
| Evaluación de SDKs de terceros | ✅ Completo — decisión: ninguno, `requests` directo |
| Mecanismo de comunicación Gist (`orden_pendiente_{producto}.json`) | ✅ Diseñado, confirmado hoy sin cambios |
| `pi/pi_executor.py` | ❌ Pseudocódigo puro, 8 `NotImplementedError`, sin cambios desde el diseño |
| Bloqueante `OrderSide` (buy/sell invertido) | ❌ **Sin resolver** — bloqueante para cualquier orden real |
| Cambio de `DRY_RUN` real en Railway (`geometry_scheduler.py`/`geometry_mgc_scheduler.py`) | ❌ Sin implementar — hoy es solo una etiqueta |
| Confirmación de modo "Auto OCO Brackets" de la cuenta | ❌ Sin confirmar |
| Credenciales de cuenta de práctica | ❌ Pendiente de solicitar |
| Hardware físico (Raspberry Pi) | ❌ Todavía no comprado |
| Setup de OS/systemd | ❌ No aplica todavía (sin hardware) |
| Medición de delay de red desde el Pi | ❌ No aplica todavía (necesita hardware + red real) |

**Para que este playbook sea 100% ejecutable el día que el hardware llegue, falta completar la Sección 2 completa (pre-requisitos) — ninguno de esos ítems necesita el Pi físico.**
