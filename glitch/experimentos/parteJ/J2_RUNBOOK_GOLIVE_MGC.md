# J2 — Runbook de go-live de Cerebro 2 (MGC / XFA)

Lunes 26-oct-2026 · BORRADOR para decidir con Eric el martes 27-oct por la noche · **NEEDS HUMAN REVIEW**. Todo comando de abajo lo corres **tú**; yo no tengo acceso al Pi, a Railway, al Gist ni a TopstepX y **no vi ningún valor de credencial** (no los pegues en el chat). Cada comando dice dónde corre: **[PI]** SSH al Pi · **[RW]** dashboard de Railway · **[TSX]** TopstepX · **[MAC]**.

Fuentes: código de `golive/cerebro2-mgc-candidate` (= `origin/main` a387a70 + `cerebro2-dev` ab4ceac; ver J1): `pi/pi_executor.py`, `pi/ops/install_service.sh`, `check_contracts.py`, `scheduler/geometry_mgc_scheduler.py`, `execution/contracts.py`; salida del Pi pegada por Eric. Todo lo que dice "el Pi hace X" sale de leer ese código (MEDIDO en código), no de ver el Pi funcionando (DESCONOCIDO en vivo).

## 0. Qué se sabe y qué no (antes de tocar nada)

| hecho | estado |
|---|---|
| El Pi corre `a387a70` = `origin/main` (con soporte MGC) | MEDIDO (pegado por Eric) |
| Cambios locales sin commitear en el Pi | DESCONOCIDO — correr `git -C ~/glitch status -sb` (el intento anterior falló por correrse fuera del repo) |
| Rama/commit y variables de Railway GEOMETRY-MGC (`DRY_RUN`, `GLITCH_PRODUCT`) | DESCONOCIDO |
| Valores no secretos del `.env` del Pi MES (`TOPSTEP_ACCOUNT_ID`, `TOPSTEP_ACCOUNT_DENY`, `GLITCH_PI_NC_MAX`, `GLITCH_PI_PHASE3`, `GLITCH_PI_ENTRY_DEADLINE_CT`) | DESCONOCIDO |
| Si existe `pi/orderside_verified.json` en el Pi (gitignored; sin él **no se coloca ninguna orden**) | DESCONOCIDO |
| Si la API de ProjectX trae `activeContract` para MGC | DESCONOCIDO — `check_contracts.py` lo dice (paso 2) |
| Hora de entrada del scheduler MGC | MEDIDO en código: espera hasta **7:13 CT** (7:00 + `ENTRY_WAIT_MINUTES = 13`); el Pi lee el Gist cada **120 s**, o sea entra entre 7:13 y 7:15 CT |
| Dirección del mié 28-oct | MEDIDO (calculada con `decide_side(trading_day_index(fecha), 'alternate')`): **LARGO** (mar 27 CORTO, jue 29 CORTO) |
| Reglas de cuenta de la XFA (MLL $2,000 → $0, 5 días ≥ $150, pagos) | `xfa/RULEBOOK_XFA.md` (parafraseado de Topstep Help; no pego su texto) |

Qué hace el Pi que importa para este runbook (código `pi_executor.py`):
- Se niega a colocar **cualquier** orden sin `GLITCH_PI_PHASE3=si` **y** `pi/orderside_verified.json`.
- Opera solo la cuenta de `TOPSTEP_ACCOUNT_ID` (obligatoria); lo valida contra las cuentas activas y contra `TOPSTEP_ACCOUNT_DENY` (si la variable no existe, el default niega la Combine `28197705`; si existe, **reemplaza** el default).
- Una señal con fecha de un día anterior se **descarta con aviso y se limpia**; una señal de hoy más allá de `GLITCH_PI_ENTRY_DEADLINE_CT` (default **10:00**) se descarta. Una señal se ejecuta como máximo una vez al día (marcador en `GLITCH_PI_STATE_DIR`).
- Valida la señal contra su config local como **cota superior**: `nc ≤ CFG.nc` (3 para `MGC`), `sl_ticks`/`tp_ticks` entre 1 y 4× lo configurado (364 → ≤ 1,456), `product_code` e igualdad de `direction`/`side`. `GLITCH_PI_NC_MAX` solo **reduce** contratos (ticks sin cambio).
- Flatten **fijo a las 14:30 CT**; no conoce cierres anticipados (J4-b).
- Elige el contrato con `activeContract: true` de la API, o el de vencimiento más cercano si ninguno lo trae (con aviso).

## 1. Hoy / mañana — sin riesgo (solo lectura), antes de que exista la XFA

**1.1 [PI] Estado del Pi** (pegar la salida; sin secretos):
```bash
git -C ~/glitch log -1 --oneline
git -C ~/glitch status -sb
ls -l ~/glitch/glitch/pi/orderside_verified.json
systemctl list-units 'glitch-pi-executor*' --no-legend
grep -E '^(GLITCH_|TOPSTEP_ACCOUNT)' ~/.glitch_pi.env
```
(El `grep` solo imprime líneas `GLITCH_*` y `TOPSTEP_ACCOUNT_*`; no imprime usuario, llaves ni tokens. Si `~/glitch` no es la raíz del repo en tu Pi, ajusta la ruta: lo que importa es llegar a la carpeta donde vive `pi/pi_executor.py`.)

**1.2 [PI] Contrato correcto del oro — BLOQUEANTE para el miércoles.** El oro de octubre (**MGCV6**) vence esta misma semana (el código lo estima ~28-oct) y su liquidez migró a diciembre (MGCZ6) tras su aviso de entrega del 30-sep. Si la API no marca `activeContract`, el Pi elegiría el **vencimiento más cercano = MGCV6**.
```bash
cd ~/glitch/glitch && ~/glitch-env/bin/python pi/ops/check_contracts.py --products MES,MGC --env-file ~/.glitch_pi.env
```
Solo lectura: no coloca ni cancela nada. **Resultado esperado:** `MGC: elegido=MGCZ6` y `OK: sin hallazgos`. **Si dice** `la API NO trae el campo activeContract`, `ningún contrato marcado activo`, o `elegido=MGCV6`: **no operar MGC el miércoles sin resolverlo** — opciones: (a) aprobar el parche J4-f (el Pi aplica la misma regla de roll que el scheduler cuando falta `activeContract`), (b) esperar al jueves 29, cuando MGCV6 ya no es el más cercano (decisión de Eric; cuesta un día de 5), (c) confirmar con Topstep/ProjectX por qué no viene el campo.

**1.3 [PI] Ver qué hay en el Gist (solo lectura; imprime los primeros 160 caracteres de los archivos de señal/estado, nada más):**
```bash
cd ~/glitch/glitch && ~/glitch-env/bin/python - <<'EOF'
import os, requests
for ln in open(os.path.expanduser("~/.glitch_pi.env")):
    ln = ln.strip()
    if ln and not ln.startswith("#") and "=" in ln:
        k, v = ln.replace("export ", "", 1).split("=", 1); os.environ.setdefault(k.strip(), v.strip().strip("'\""))
r = requests.get(f"https://api.github.com/gists/{os.environ['GIST_ID']}", headers={"Authorization": f"Bearer {os.environ['GITHUB_GIST_TOKEN']}"}, timeout=15); r.raise_for_status()
for name, f in sorted(r.json()["files"].items()):
    c = f.get("content") or ""
    show = c[:160].replace("\n", " ") if name.startswith(("orden_pendiente", "pi_position", "pi_block", "geometry_mgc_pending")) else ""
    print(f"{name:42s} {len(c):>8} bytes  {show}")
EOF
```
Buscar `orden_pendiente_mgc.json`: **debe valer `{}`**. Si trae la orden vieja del 19-oct: el scheduler real **se niega a escribir** una señal nueva mientras haya una sin consumir (Telegram "BLOCKED"); el Pi MGC la descartaría solo al primer ciclo con alerta, pero no cuentes con eso. Límpiala **antes** (comando 1.4). `pi_position_mgc.json` debe ser `{}` (sin posición registrada).

**1.4 [PI] Limpiar la orden MGC vieja (escribe en el Gist; solo si 1.3 mostró algo distinto de `{}`):**
```bash
cd ~/glitch/glitch && ~/glitch-env/bin/python - <<'EOF'
import os, requests
for ln in open(os.path.expanduser("~/.glitch_pi.env")):
    ln = ln.strip()
    if ln and not ln.startswith("#") and "=" in ln:
        k, v = ln.replace("export ", "", 1).split("=", 1); os.environ.setdefault(k.strip(), v.strip().strip("'\""))
r = requests.patch(f"https://api.github.com/gists/{os.environ['GIST_ID']}", headers={"Authorization": f"Bearer {os.environ['GITHUB_GIST_TOKEN']}"},
                   json={"files": {"orden_pendiente_mgc.json": {"content": "{}"}}}, timeout=15)
print("HTTP", r.status_code)
EOF
```
Repite 1.3 para confirmar `{}`.

**1.5 [PI] (opcional, recomendado) Archivar el historial de paper/Practice de MGC.** `geometry_mgc_log.json` contiene corridas de paper de la 150K (nc = 6) y de Practice; el Pi real **agrega en ese mismo archivo** y el scheduler deriva de él la etiqueta `intento` y los contadores de WR/días ganadores. **No afecta la seguridad de la orden** (el Pi no valida `intento`), pero contamina la contabilidad de la XFA real. Hacerlo = copiar el contenido a `geometry_mgc_paper_archive_20261026.json` y dejar `geometry_mgc_log.json` en `[]` (archivar, no borrar). **Decisión de Eric**; si prefieres, hazlo desde la interfaz web del Gist copiando el archivo a mano.

## 2. Instancia del Pi para MGC (se puede dejar lista antes de que exista la XFA)

**2.1 [PI]** Crear el entorno vacío y editarlo a mano (las llaves van **a mano en el Pi, nunca por chat**):
```bash
cd ~/glitch/glitch && bash pi/ops/install_service.sh --instance mgc      # 1.ª vez: crea ~/.glitch_pi_mgc.env (chmod 600) con nombres y valores VACÍOS, y sale
nano ~/.glitch_pi_mgc.env
```
Valores (copia las credenciales del `.env` del MES; las demás son estas):
```text
GLITCH_PRODUCT=MGC
TOPSTEP_ACCOUNT_ID=<id de la XFA — hasta que exista, un número que NO sea de ninguna de tus cuentas, p. ej. 1; no arrancar el servicio hasta cambiarlo>
GLITCH_PI_NC_MAX=3                      # 1 si decides 1 micro el día 1 (J8); sube a 3 después (ver 3.6)
GLITCH_PI_ENTRY_DEADLINE_CT=08:00       # el scheduler envía a las 7:13 CT; el default del Pi es 10:00
GLITCH_PI_PHASE3=si
# NO definir TOPSTEP_ACCOUNT_DENY aquí: sin la variable, el default niega la Combine 28197705
```
`install_service.sh` se niega a instalar si dos entornos fijan el mismo `GLITCH_PRODUCT`, y exige valores no vacíos (por eso el id provisional).

**2.2 [PI]** Instalar y habilitar (aún **sin** `--start`):
```bash
cd ~/glitch/glitch && bash pi/ops/install_service.sh --instance mgc
bash pi/ops/install_watchdog.sh --instance mgc          # alerta por Telegram si pi_executor_mgc.log deja de crecer
python3 pi/ops/watchdog.py --dry-run --log-file ~/glitch-logs/pi_executor_mgc.log --env-file ~/.glitch_pi_mgc.env --state-file ~/.glitch_watchdog_state_mgc.json
```
Unidad: `glitch-pi-executor-mgc.service`; log: `~/glitch-logs/pi_executor_mgc.log`; estado: `~/.glitch_pi_state_mgc/`.

## 3. Tras el PASE — orden exacto

| # | dónde | qué | por qué |
|---|---|---|---|
| 3.0 | TSX / correo | Confirmar el PASE y que la Combine quedó cerrada | el modelo supone 1 día de activación manual ($149); **si la activación tarda un día el primer día XFA es el jueves 29 (CORTO)**, no el miércoles |
| 3.1 | RW | Decidir qué pasa con el scheduler **MES** (GEOMETRY): detenerlo/pausar su cron si no vas a comprar otra Combine | con la Combine cerrada, el Pi MES intenta la cuenta fijada, no la encuentra entre las activas y alerta cada ciclo con señal pendiente |
| 3.2 | TSX | Activar la XFA (manual, $149) | — |
| 3.3 | PI | Id de la XFA (solo lectura): ver bloque abajo | `TOPSTEP_ACCOUNT_ID` debe ser un id **activo** |
| 3.4 | PI | **DENY en el Pi MES:** en `~/.glitch_pi.env` poner `TOPSTEP_ACCOUNT_DENY=<id XFA>` (la variable **reemplaza** el default: no incluir `28197705` si el MES sigue operando esa Combine) y `sudo systemctl restart glitch-pi-executor` (fuera de horario y sin bracket abierto) | el ejecutor MES nunca debe poder apuntar a la XFA |
| 3.5 | PI | En `~/.glitch_pi_mgc.env`: `TOPSTEP_ACCOUNT_ID=<id XFA>`; `sudo systemctl start glitch-pi-executor-mgc`; `tail -f ~/glitch-logs/pi_executor_mgc.log` | debe decir `PHASE3_ENABLED=True orderside_verified=True` y quedar en "Sin señal pendiente" |
| 3.6 | PI | Día 1 con 1 micro (si Eric lo decide): `GLITCH_PI_NC_MAX=1` y, **al terminar el día 1 y fuera de horario**, `GLITCH_PI_NC_MAX=3` + `sudo systemctl restart glitch-pi-executor-mgc` | el tope se lee al arrancar; cambiarlo con bracket abierto reinicia el ejecutor |
| 3.7 | RW | GEOMETRY-MGC: `DRY_RUN=false`; `GLITCH_PRODUCT=MGC` (es el default del código); comprobar que despliega un commit que contenga `3b8a5af` (J1); redeploy | con `DRY_RUN=false` el scheduler **deja de simular** y escribe `orden_pendiente_mgc.json`; el invariante es `signal["product"] == GLITCH_PRODUCT` del Pi, si no el Pi la trata como ENSAYO (≤ 2 contratos, sin ventana ni marcador) |
| 3.8 | RW | Cron de GEOMETRY-MGC (UTC): hasta el sáb 31-oct (CDT, UTC−5) `0 12 * * 1-5` = 7:00 CT; desde el dom 1-nov (CST, UTC−6) `0 13 * * 1-5` | el cron de Railway es UTC fijo; Monterrey es UTC−6 todo el año |
| 3.9 | PI/RW | MES tras el cambio de hora: `25 15 * * 1-5` (9:25 CT) a partir del 1-nov | ídem |
| 3.10 | PI | Mañana del primer día: ver la lista de la sección 4 | — |

**3.3 [PI] Id de la XFA (solo lectura):**
```bash
cd ~/glitch/glitch && ~/glitch-env/bin/python - <<'EOF'
import os
for ln in open(os.path.expanduser("~/.glitch_pi_mgc.env")):
    ln = ln.strip()
    if ln and not ln.startswith("#") and "=" in ln:
        k, v = ln.replace("export ", "", 1).split("=", 1); os.environ.setdefault(k.strip(), v.strip().strip("'\""))
from brokers.projectx import ProjectXClient, ProjectXCredentials
for a in ProjectXClient(ProjectXCredentials.from_env(), verbose=False).get_accounts(only_active=True):
    print(a.get("id"), a.get("name"), a.get("balance"), "canTrade=", a.get("canTrade"))
EOF
```
(Los nombres de campo `name`, `balance`, `canTrade` son los de la API de ProjectX; si alguno sale `None`, no importa: lo que necesitas es el `id` de la fila que sea la XFA.)

## 4. Mañana del primer día XFA (horas en CT; Monterrey = CT − 1 h hasta el 1-nov)

| CT | Monterrey | qué debe pasar | si no pasa |
|---|---|---|---|
| < 7:00 | < 6:00 | `systemctl is-active glitch-pi-executor-mgc` = `active`; `orden_pendiente_mgc.json` = `{}`; XFA sin posición abierta | no arrancar; resolver antes |
| 7:00 | 6:00 | Railway dispara GEOMETRY-MGC; Telegram "INICIO DE DIA" con la señal de hoy (LARGO el mié) | revisar cron/UTC; el Pi descarta señales después de las 08:00 CT |
| 7:13 | 6:13 | Telegram `[SEÑAL ENVIADA AL PI]` con Contracts = `REAL_CFG.nc` (3) y SL/TP 364/364 | si dice BLOCKED: había una señal sin consumir (1.3/1.4) |
| 7:13–7:15 | 6:13–6:15 | Pi: entrada a mercado + TP + SL; Telegram del Pi; en TopstepX ver 3 (o 1) micros del contrato **MGCZ6** | si la posición es de **MGCV6**: cerrar a mano y detener (1.2) |
| 13:00 | 12:00 | FOMC (2:00 PM ET); el bracket sigue en el broker | no tocar nada |
| 14:30 | 13:30 | Pi hace flatten si no tocó TP/SL; cuenta plana | si no está plana: cerrar a mano en TopstepX **antes de las 15:10 CT** (regla de Topstep) |

**Parar todo:** `sudo systemctl stop glitch-pi-executor-mgc` (los brackets abiertos siguen en el broker; **el flatten de las 14:30 lo hace el Pi**: parado, hay que cerrar a mano). Cancelar la señal del día: comando 1.4.

## 5. Lo que este runbook NO resuelve

- No prueba el flujo con dinero: la última evidencia real del handoff MGC es de **Practice** (3 sesiones). La primera señal real de la XFA es también la primera vez que el scheduler de Railway en modo real habla con el Pi MGC en producción.
- El Pi **no** hace flatten por calendario de cierres anticipados (J4-b) ni respeta `ROLL_RULES` (J4-f): los dos están como parches propuestos, sin aplicar.
- No hay kill-switch por colchón del MLL: el control de pérdida es el SL de 364 ticks por trade y la liquidación en tiempo real de Topstep (J4-a).
