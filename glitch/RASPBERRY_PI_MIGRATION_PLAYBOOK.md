# Raspberry Pi Migration Playbook — Cerebro 1/2 Real Execution

**Propósito:** que el día que el Raspberry Pi llegue físicamente, exista una secuencia de pasos ejecutable, sin tener que investigar ni decidir nada en el momento. Este documento no diseña nada nuevo — consolida el diseño ya hecho en la rama `design/pi-execution` (`pi/pi_executor.py`, commit `c47efb7`, 11-sep-2026) en forma de checklist, y agrega lo que faltaba: pre-requisitos, setup de hardware/OS, plan de fallas, y secuencia de transición.

**Estado del diseño re-verificado hoy (23-sep-2026):** `pi/pi_executor.py` sigue siendo pseudocódigo puro — 8 funciones con `raise NotImplementedError`, cero cambios desde el 11-sep. El cambio de `DRY_RUN` real en Railway sigue sin implementar (`grep "orden_pendiente"` en ambos schedulers: 0 resultados). `scripts/verify_orderside_demo.py` existe y está listo, pero gateado para no correr hasta Fase 3 (ver Sección 2). **Ninguno de los 5 bloqueantes está resuelto — la Sección 3 (hardware/OS) es segura de hacer ahora porque no depende de ninguno de ellos; la Sección 3.6 (systemd) se prepara pero NO se arranca por esta misma razón.**

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

## 3. Setup del hardware — primera vez, paso a paso desde Terminal de Mac

**Split explícito, por lo confirmado en la Sección 2:** todo 3.1–3.5 (hasta tener SSH, Python y `requests` funcionando) **no depende de ningún bloqueante pendiente — se puede hacer completo hoy.** 3.6 (systemd) se prepara pero **NO se arranca** — `pi_executor.py` sigue siendo pseudocódigo (Sección 6), arrancarlo no haría nada útil todavía.

### 3.1 Flashear la SD (GUI de Raspberry Pi Imager, desde el Mac)

```bash
# Terminal de Mac -- instalar Raspberry Pi Imager si no lo tienes
brew install --cask raspberry-pi-imager
open -a "Raspberry Pi Imager"
```
Si no usas Homebrew: descargar desde `raspberrypi.com/software` e instalar como cualquier `.dmg`.

En la ventana de Raspberry Pi Imager:
1. **Device:** el modelo de Pi que tengas.
2. **Operating System:** "Raspberry Pi OS (other)" → **"Raspberry Pi OS Lite (64-bit)"** — sin escritorio, es lo correcto para un daemon headless.
3. **Storage:** la SD card.
4. Click el ícono de engranaje (⚙️, esquina inferior derecha) o `Cmd+Shift+X` — **esto es lo que evita necesitar teclado/monitor en el Pi**:
   - Hostname: `glitch-pi` (queda como `glitch-pi.local` en la red)
   - Habilitar SSH → "Allow public-key authentication only" (ver 3.2 para generar la llave ANTES de esto)
   - Username: `glitch` (o el que prefieras — se usa en todos los comandos siguientes)
   - Configurar WiFi (SSID/password) si el Pi no va por cable Ethernet — **Ethernet es más confiable para algo que ejecuta órdenes reales, preferirlo si es posible**
   - Configurar timezone: `America/Chicago` (mismo TZ que Railway, evita el mismo tipo de bug de `ct_logging.py` que ya se encontró ahí)
5. Guardar, "Write", esperar a que termine y expulsar la SD.

### 3.2 Generar una llave SSH en el Mac (ANTES del paso 3.1.4 si aún no tienes una)

```bash
# Terminal de Mac
ls ~/.ssh/id_ed25519.pub 2>/dev/null || ssh-keygen -t ed25519 -C "glitch-pi" -f ~/.ssh/id_ed25519
cat ~/.ssh/id_ed25519.pub   # pegar este contenido en el campo de la llave publica del Imager (paso 3.1.4)
```

### 3.3 Primer arranque y conexión desde el Mac

Insertar la SD en el Pi, conectar Ethernet (o confirmar que el WiFi configurado alcanza), energizar. Esperar ~90 segundos al primer arranque.

```bash
# Terminal de Mac
ssh glitch@glitch-pi.local
```
La primera vez pedirá confirmar el fingerprint del host — escribir `yes`.

**Si `glitch-pi.local` no resuelve** (mDNS a veces falla entre Mac y Pi en la primera conexión):
```bash
# Terminal de Mac -- opción 1: refrescar cache de mDNS
sudo dscacheutil -flushcache
# opción 2: buscar la IP por MAC (los Pi empiezan con b8:27:eb, dc:a6:32, o e4:5f:01)
arp -a | grep -iE "b8:27:eb|dc:a6:32|e4:5f:01"
# luego: ssh glitch@<ip-encontrada>
```
Si ninguna funciona: entrar al router (típicamente `192.168.1.1` o `192.168.0.1` en un navegador) y buscar "glitch-pi" en la lista de dispositivos conectados.

### 3.4 Setup del sistema (ya dentro del Pi, vía SSH desde el Mac)

```bash
# Dentro de la sesion SSH (glitch@glitch-pi:~$)
sudo apt update && sudo apt full-upgrade -y
python3 --version                                   # confirmar 3.11+ (Bookworm lo trae por default)
sudo apt install -y python3-venv python3-pip git
```

### 3.5 Clonar el repo y preparar el entorno (SOLO `requests`, nada de numpy/pandas)

```bash
# Dentro de la sesion SSH
git clone https://github.com/erictvillarreal/GLITCH.git ~/glitch-pi
cd ~/glitch-pi/glitch
git checkout design/pi-execution     # aqui vive pi_executor.py y este mismo playbook -- actualizar cuando el codigo se apruebe para main
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install requests                 # UNICA dependencia -- no correr `pip install -r requirements.txt` ni pyproject.toml completo, eso trae numpy/pandas/scipy que este dispositivo no necesita
```

**Verificación de red saliente** (correr DENTRO del Pi vía SSH, no desde el Mac — es la conexión del Pi la que importa):
```bash
curl -sS https://api.topstepx.com/ -o /dev/null -w "topstepx: %{http_code}\n"
curl -sS https://api.github.com/ -o /dev/null -w "github: %{http_code}\n"
curl -sS https://api.telegram.org/ -o /dev/null -w "telegram: %{http_code}\n"
```
Un código HTTP cualquiera (200, 401, 404...) confirma que la salida no está bloqueada — lo único preocupante es un timeout o error de conexión. Si alguno falla, revisar el firewall del router/ISP antes de asumir que el diseño funciona igual que desde Railway (datacenter).

**Endurecer SSH** (solo después de confirmar que el login por llave ya funciona — hacerlo antes te puede dejar fuera):
```bash
sudo sed -i 's/^#\?PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config
sudo systemctl restart ssh
```

### 3.6 Preparar (NO arrancar) el servicio systemd

Dejar el archivo escrito para cuando `pi_executor.py` esté implementado (Sección 6) — **no habilitar ni arrancar el servicio todavía**, correr un daemon con funciones `NotImplementedError` no hace nada útil y solo generaría ruido en los logs.

```bash
# Dentro de la sesion SSH
sudo tee /etc/systemd/system/glitch-pi-executor.service > /dev/null <<'EOF'
[Unit]
Description=GLITCH Pi Executor
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=glitch
WorkingDirectory=/home/glitch/glitch-pi/glitch
EnvironmentFile=/home/glitch/glitch-pi/glitch/.env
ExecStart=/home/glitch/glitch-pi/venv/bin/python pi/pi_executor.py
Restart=on-failure
RestartSec=30

[Install]
WantedBy=multi-user.target
EOF
sudo systemctl daemon-reload
# NO correr: sudo systemctl enable --now glitch-pi-executor
# -- esperar a que los 5 bloqueantes de la Seccion 2/6 esten resueltos.
```
`EnvironmentFile` (`.env`, permisos `600`, nunca en git) es donde van a vivir `TOPSTEP_USERNAME`/`TOPSTEP_API_KEY`/`TOPSTEP_ACCOUNT_ID`/`GITHUB_GIST_TOKEN`/`GIST_ID`/`TELEGRAM_BOT_TOKEN`/`TELEGRAM_CHAT_ID`/`GLITCH_PRODUCT` cuando llegue el momento — no crearlo todavía si las credenciales de práctica no están gestionadas (Sección 2).

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

| Pieza | Estado hoy (23-sep-2026) |
|---|---|
| Diseño Railway↔Pi (qué se queda, qué se mueve) | ✅ Completo (11-sep-2026) |
| Investigación de la API oficial de ProjectX | ✅ Completo (auth, órdenes, posiciones, rate limits) |
| Evaluación de SDKs de terceros | ✅ Completo — decisión: ninguno, `requests` directo |
| Mecanismo de comunicación Gist (`orden_pendiente_{producto}.json`) | ✅ Diseñado, confirmado sin cambios |
| Script de verificación de `OrderSide` (`scripts/verify_orderside_demo.py`) | ✅ Escrito y listo — **gateado explícitamente, NO correr hasta Fase 3** (ver Sección 2) |
| `pi/pi_executor.py` | ❌ Pseudocódigo puro, 8 `NotImplementedError`, sin cambios desde el diseño |
| Bloqueante `OrderSide` (buy/sell invertido) | ❌ **Sin resolver** — bloqueante para cualquier orden real |
| Cambio de `DRY_RUN` real en Railway (`geometry_scheduler.py`/`geometry_mgc_scheduler.py`) | ❌ Sin implementar — hoy es solo una etiqueta |
| Confirmación de modo "Auto OCO Brackets" de la cuenta | ❌ Sin confirmar |
| Credenciales de cuenta de práctica | ❌ Pendiente de solicitar |
| Hardware físico (Raspberry Pi) | 🟡 Llega este domingo |
| Setup de OS/SSH/Python (Sección 3.1–3.5) | 🟡 Ejecutable este domingo — no depende de ningún bloqueante de arriba |
| Servicio systemd (Sección 3.6) | 🟡 Se prepara este domingo, **no se arranca** hasta resolver los bloqueantes |
| Medición de delay de red desde el Pi | ❌ Pendiente hasta tener hardware conectado (domingo en adelante) |

**El domingo se puede completar toda la Sección 3 (hardware/OS/SSH/Python/`requests`). Lo que sigue bloqueado es instalar y arrancar `pi_executor.py` como servicio real — eso espera a que se resuelvan los 5 bloqueantes de la Sección 2, ninguno de los cuales necesita el Pi físico.**
