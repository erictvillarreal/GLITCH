# T3 — Notificaciones por Telegram: diseño e implementación base
*Rama `feat/t3-telegram-monitoring`, desde `origin/main` (`2ed2ec2`). Código nuevo, **sin tocar `pi/pi_executor.py` ni ningún scheduler existente**; 25 pruebas nuevas (`tests/test_monitoring.py`) y las suites del Pi existentes (`test_pi_ops/executor/audit_patches/nc_cap`), todas en verde en Python 3.9 (la suite completa no se pudo colectar aquí por `test_combo2d_parity`, que necesita dependencias de otra versión de Python: preexistente, no tocado). Todo está marcado **NEEDS HUMAN REVIEW** (CLAUDE.md regla 4 aplica a cualquier cambio de lógica de capital; esto es solo lectura, pero conviene que Eric lo revise antes de instalarlo en el Pi).*

## Resumen (10 líneas)
1. **Hoy no existe nada de esto**: lo que hay es `scheduler/telegram_bot.py` (envío de OPEN/CLOSE de los schedulers), los mensajes propios del ejecutor (OPEN/CLOSE/BLOCKED/ALERTA) y `pi/ops/watchdog.py` (avisa si el log del ejecutor deja de crecer). Ninguna alerta de margen, ningún registro de fricción, ningún resumen ni recordatorio.
2. **Se agregan 4 funciones, todas de solo lectura**: alerta de margen (Pi), registro diario de fricción (Pi → Gist), resumen semanal con semáforo (Railway) y recordatorios con fecha (Railway).
3. **Dónde corre cada una**: lo que necesita el broker corre en el **Pi** (margen, fricción); lo que solo necesita el Gist y Telegram corre en **Railway** (resumen, recordatorios). Railway **nunca** habla con ProjectX (regla de fondo de `pi/ARCHITECTURE.md`).
4. **La lógica de decisión es pura y probada** (umbrales, semáforo, dedupe de alertas, prueba de pase N=10/20, calendario de recordatorios); el I/O vive en 4 scripts delgados.
5. **El registro de fricción es un archivo nuevo del Gist** (`friction_<producto>_log.json`, un solo escritor): no toca el historial compartido `geometry_<producto>_log.json` del que el scheduler deriva PASE/QUIEBRE.
6. **Semáforo = §3 de `REPORT_STACKING_TIMING`**: entrada ≤ 1 / ≤ 2 ticks, TP cruzado ≤ 1 / ≤ 2, flatten ≤ 1 / ≤ 2, fallos ≤ 1 / 2 por 20 sesiones, costo ≤ +5% / +10%; la compuerta de la 2.ª cuenta sale en el resumen semanal.
7. **NO VERIFICADO contra la API real** (se confirma en el ensayo de Practice del 30-oct): los campos de `Order/search` y `Trade/search`, que `Account/search` entregue saldo en tiempo real, y que el piso del MLL no está en la API (se estima con un libro propio de máximos de cierre).
8. **Alerta de margen**: Practice avisa con cojín < $1,500; Combine avisa por distancia a la liquidación (amarillo ≤ 20 ticks, rojo ≤ 10) y no repite el mismo nivel en el día (re-aviso a las 6 h si sigue en rojo).
9. **Recordatorios**: lun 9-nov (resumen), 15-nov o 5 intentos (presupuesto), lun 16-nov (evaluar 2.ª cuenta), 10-dic con 10 Combines resueltos (prueba de pase), lun 14-dic (evaluar 3.ª), 16-feb-2027 con 20 resueltos (prueba N = 20).
10. **Plan**: diseño hoy; ensayo en Practice el 30-oct (verificar campos reales); instalación en el Pi y en Railway antes del 6-nov. El cron de Railway es UTC: se programan 13:00 y 14:00 UTC y el script solo actúa a las 8:00 de Chicago (horario de verano hasta el 1-nov).

## 1. Qué ya existe (verificado en `origin/main`)
| Pieza | Dónde | Qué hace | Relación con T3 |
|---|---|---|---|
| `scheduler/telegram_bot.py::send` | Railway | Envío HTML con `TELEGRAM_BOT_TOKEN/CHAT_ID`; `sys.exit` si faltan | No se reutiliza (aborta el proceso al importar); T3 usa un envío stdlib propio |
| Mensajes del ejecutor | Pi | OPEN / CLOSE / BLOCKED (una vez al día) / ALERTA, prefijo `S10GLITCH - PI EXECUTOR - <producto>` | Sin cambios |
| `pi/ops/watchdog.py` + `install_watchdog.sh` | Pi (cron 5 min) | Avisa si `pi_executor.log` no crece en 10 min; stdlib puro; estado en disco; no reenvía el token | **Es el patrón** de T3: función de decisión pura, estado que solo se guarda si el Telegram salió, cron idempotente |
| Resumen/recordatorios/margen/fricción | — | **No existe** (cero resultados en el repo) | T3 |

## 2. Qué se implementa y dónde corre
| Función | Archivo | Corre en | Lee | Escribe | Frecuencia |
|---|---|---|---|---|---|
| 1. Alerta de margen | `pi/ops/margin_alert.py` + `monitoring/margin.py` | **Pi** (venv del ejecutor; necesita `brokers/`) | ProjectX: `Account/search`, `Position/searchOpen`, barras de 1 min | libro EOD y estado de alertas en disco del Pi | cron cada 5 min, solo 8:30–15:10 CT lun–vie |
| 2. Registro diario de fricción | `pi/ops/friction_collect.py` + `monitoring/friction.py` | **Pi** | ProjectX: `Order/search`, `Trade/search`, barras, posiciones; `pi_executor.log` | Gist `friction_<producto>_log.json` (spool local si falla) | cron cada 5 min; actúa desde las 14:40 CT y **una vez por día** |
| 3. Resumen semanal con semáforo | `scheduler/weekly_summary.py` + `monitoring/weekly.py` | **Railway** (cron) | Gist: `geometry_<producto>_log.json`, `friction_<producto>_log.json`, `glitch_costs.json` (opcional) | solo Telegram | lunes 8:00 CT |
| 4. Recordatorios con fecha | `scheduler/reminders_job.py` + `monitoring/reminders.py` | **Railway** (cron) | Gist (historial y fricción) | Gist `reminders_sent.json` (solo si el envío salió) + Telegram | diario 8:00 CT, lun–vie |
Instalación en el Pi: `bash pi/ops/install_monitoring.sh --account-id <ID del API> --kind combine` (cron idempotente, `--remove` lo quita). Railway: dos servicios de cron con `0 13,14 * * 1` (resumen) y `0 13,14 * * 1-5` (recordatorios); el script solo actúa cuando en Chicago son las 8:00 (la mitad del año coincide la entrada de 13 UTC, la otra la de 14 UTC); `--any-hour` fuerza.

## 3. Definiciones
### 3.1 Alerta de margen
- **Cojín** = saldo + no realizado − piso del MLL. El **piso no viene de la API (NO VERIFICADO)**: se lleva con un libro de máximos de cierre (EOD) que el propio script actualiza una vez al día después de las 15:00 CT; piso = mín(máximo EOD − MLL, saldo inicial) (Combine: se traba en el saldo inicial). `--floor-override` lo fija a mano.
- **Practice** (150K, 15 lotes, MLL de ~$4,474 de margen según el commit `2ed2ec2`): rojo si cojín < **$1,500**.
- **Combine**: exposición de liquidación = cojín ÷ (contratos × valor del tick) = **ticks hasta el precio de liquidación**; amarillo ≤ 20, rojo ≤ 10, verde sin posición. Con nc = 40 y $2,000 de cojín arranca en 40 ticks (verde). Un movimiento de 20 ticks en contra ya es amarillo: es información, no ruido, porque con nc = 40 el stop **es** la liquidación.
- **Dedupe**: una alerta por nivel y día; escalada (amarillo → rojo) sí avisa; recuperación avisa; re-aviso cada 6 h si sigue en rojo. El estado solo se guarda si Telegram respondió 2xx.
### 3.2 Registro diario de fricción (una fila por sesión)
Reconstruido **sin tocar el ejecutor**: órdenes del día (entrada a mercado, TP límite, SL stop, salida a mercado posterior = flatten), barras de 1 min, `Trade/search` (comisiones), `pi_executor.log` (fallos y eventos duros).
| Campo | Cálculo | Verde / amarillo / rojo |
|---|---|---|
| `entry_slip_ticks` | lado × (fill − cierre de la última barra de 1 min completa al momento de la orden) ÷ tick | ≤ 1 / ≤ 2 / > 2 |
| `tp_cross_ticks` | ticks que el extremo entre entrada y salida cruzó el TP **sin** que el límite se llenara (0 si se llenó) | ≤ 1 / ≤ 2 / > 2 |
| `flatten_slip_ticks` | salida de las 14:30 vs. cierre de la barra de referencia | ≤ 1 / ≤ 2 / > 2 |
| `stop_slip_usd_per_ct` | exceso del llenado de un SL sobre su precio, USD por contrato | ≤ 70 / ≤ 140 / > 140 |
| `api_errors` | líneas ERROR/CRITICAL del log del día; agregado: fallos por 20 sesiones | ≤ 1 / 2 / ≥ 3 |
| `commission_per_contract_rt` | suma de `fees` ÷ contratos | costo real / modelo: ≤ 1.05 / ≤ 1.10 |
| `hard_red` | bracket sin proteger, orden duplicada, posición no conciliada, cuenta equivocada, posición abierta después de las 14:35 | **rojo inmediato** |
Los campos que no se pueden calcular quedan en `null` (“sin datos”), nunca se inventan; cada fila guarda `raw` (ids de órdenes, marcas de tiempo, precio de referencia) para depurar en el ensayo.
### 3.3 Resumen semanal (lunes 8:00 CT) — formato (cifras ILUSTRATIVAS, inventadas solo para mostrar el formato)
```
S10GLITCH - MONITOR | RESUMEN SEMANAL 2026-11-09
Combines: 14 iniciados, 13 resueltos (4 pases, 9 quiebres)
Prueba de pase: 4 pases en 13 resueltos (p = 0.63): consistente con el modelo (30.8%)

FRICCION (ultimas 4 semanas):
Sesiones con registro: 14
- slippage entrada (ticks): 0.60 -> VERDE
- TP cruzado sin llenar (ticks, peor caso): 1.00 -> VERDE
- salida flatten (ticks): 0.40 -> VERDE
- fallos por 20 sesiones: 0.00 -> VERDE
- eventos rojos duros: 0
COMPUERTA 2.a CUENTA: LUZ VERDE
Costo por intento: $135 vs modelo $127 -> VERDE (x1.06)
```
Los intentos y los pases/quiebres se derivan del historial de trades con la misma regla simple del scheduler (acumulado ≥ $3,000 = pase; piso trailing EOD = quiebre); **la consistencia del 55% no está en esa regla (NO VERIFICADO si cambia algún caso límite)**. La compuerta aplica la regla de `REPORT_STACKING_TIMING` §3: todas en verde o a lo más una en amarillo, ninguna en rojo y cero eventos duros.
### 3.4 Prueba de pase (de `REPORT_STACKING_TIMING` §2)
Rechaza el modelo (30.8%) si P(pases ≤ k | N resueltos) ≤ 5%: **N = 10 → 0 pases; N = 20 → ≤ 2; N = 40 → ≤ 7**; con N < 10 el mensaje dice explícitamente que no hay poder.
### 3.5 Recordatorios
| Fecha / condición | Mensaje |
|---|---|
| lun 9-nov-2026 | resumen de las primeras 3 semanas y semáforo |
| **15-nov o ≥ 5 intentos** (lo que ocurra primero) | revisión de presupuesto: costo real por intento vs. $127 y neto acumulado |
| lun 16-nov | **evaluar la 2.ª cuenta** (MES + MCL) con el semáforo |
| 10-dic o 10 Combines resueltos | prueba de pase N = 10 |
| lun 14-dic | **evaluar la 3.ª cuenta** (MGC 9:45) con las condiciones de T2 |
| 16-feb-2027 o 20 Combines resueltos | prueba N = 20 y decisión del programa |
No se envía nada antes del 19-oct-2026; los ya enviados se guardan en `reminders_sent.json` (idempotente).

## 4. Garantías de “solo lectura” y de seguridad
- Una prueba estática (AST) falla si algún script de monitoreo importa `pi_executor`, llama a métodos que colocan/cancelan/cierran órdenes (`place_*`, `cancel_*`, `close_contract`, `flatten_position`, …) o hace un `_post` a un endpoint que no sea de lectura (`search`, `searchOpen`, `balance`, `available`, `retrieveBars`).
- Las credenciales se leen del mismo archivo de entorno que el ejecutor (`~/.glitch_pi.env`), nunca se imprimen; el texto que sale por Telegram pasa por `sanitize()` (quita `bot<id>:<token>`). El envío usa stdlib (como el watchdog), así que sigue funcionando aunque el venv esté roto.
- **Topstep exige que las órdenes salgan de un dispositivo personal**; T3 no transmite órdenes. Aun así, los dos jobs del Pi hacen **lecturas autenticadas** de la cuenta: corren en el Pi (dispositivo personal), no en Railway.
- Único escritor por archivo del Gist (`friction_*` solo el Pi; `reminders_sent.json` solo Railway): sin la carrera de lectura-modificación-escritura que afecta al historial compartido.

## 5. Riesgos y límites (qué falta antes del 6-nov)
1. **Ensayo en Practice (30-oct)**: confirmar los nombres reales de campos (`type`, `status`, `limitPrice`, `stopPrice`, `filledPrice`, `creationTimestamp`; `Trade/search.fees`) y que `Account/search` actualiza el saldo con el no realizado. Si `balance` no incluye el no realizado, el cojín de Combine usará el precio de la última barra (ya se hace) sobre un saldo realizado.
2. **Piso del MLL**: hasta confirmar que la API lo entrega, el libro propio puede desviarse si el script arranca a mitad de vida de una cuenta; arrancar con `--floor-override` correcto y revisarlo semanalmente contra el dashboard.
3. **`accountId` cambia con cada reinicio/cuenta nueva** (NO VERIFICADO si un reinicio conserva el ID): los jobs del Pi reciben `--account-id` fijo, igual que el pin A5 del ejecutor; con ~50 intentos al año hay que actualizar ambos juntos. **Decisión de Eric**: si el ID cambia en cada reinicio, conviene un único archivo de entorno compartido (`TOPSTEP_ACCOUNT_ID`) que lean el ejecutor y los jobs.
4. Los patrones del log (`hard_red`) son heurísticas sobre el formato actual de `pi_executor.log`; se afinan con el primer log real.
5. Dos cuentas / dos productos: los archivos de fricción y los estados de alerta están claveados por producto, pero **el estado de margen en disco no**: con una segunda instancia (T4d) hay que pasar `--state-file`/`--ledger-file` distintos por cuenta (el instalador lo hará en la siguiente iteración).
6. Volumen de mensajes: 1 resumen por semana, ≤ 1 recordatorio por día laborable, alertas de margen deduplicadas; si molesta, los umbrales están en `monitoring/thresholds.py` y `monitoring/margin.py`.

## 6. Cronograma
- **Hoy 12-oct**: rama con módulos, scripts, instalador y pruebas (lista de pruebas en `tests/test_monitoring.py`).
- **Vie 23-oct**: revisión humana del diseño; decisión sobre el archivo de entorno compartido y sobre el umbral del cojín de Combine.
- **Vie 30-oct**: ensayo en Practice (con T4): `friction_collect.py --dry-run --force-window` y `margin_alert.py --force-window --dry-run` contra la cuenta Practice; corregir campos.
- **Vie 6-nov**: instalación en el Pi (`install_monitoring.sh`), dos crones en Railway, primer resumen real el lun 9-nov.
