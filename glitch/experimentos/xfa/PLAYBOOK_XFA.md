# PLAYBOOK_XFA — del PASE del Combine a la primera semana y al primer cobro (20-oct-2026)

**Nada de esto se ejecutó ni se desplegó.** Cada comando lo corre Eric, a mano, en el Pi o en el panel de Railway; los valores de entorno son los que el código lee hoy (`pi/ARCHITECTURE.md`, `pi_executor.py`) y se marcan **(NO VERIFICADO en vivo)** cuando el comportamiento viene de la documentación y no de una corrida real. Los secretos (`TOPSTEP_API_KEY`, tokens) se escriben solo a mano en los archivos `.env` del Pi, nunca por chat.

## 1. El momento del PASE — qué hace hoy el sistema (verificado leyendo el código) y qué hay que cerrar ANTES

**Hecho (código):** en modo real (`DRY_RUN=false`) `geometry_scheduler.py` solo escribe la señal del día al Gist y termina (`run()` sale tras el paso 2c); **la detección de PASE/QUIEBRE y el mensaje “INTENTO COMPLETADO” viven en el camino de paper (paso 5b) y NO se ejecutan en modo real**. El Pi (`pi_executor.py`) no detecta ni avisa el PASE: solo registra cada ciclo en el historial. El “intento” se re-deriva en el scheduler del día siguiente desde ese historial (`_current_intento`).

| # | Qué pasa tras el PASE | Evidencia | Riesgo / acción |
|---|---|---|---|
| 1 | El Combine pasado **se cierra** en TopstepX y su suscripción se cancela sola (RULEBOOK 5.1). | RULEBOOK | El Pi está fijado a esa cuenta (`TOPSTEP_ACCOUNT_ID`). |
| 2 | Al día siguiente el scheduler de Railway **sigue escribiendo una señal MES de 40 contratos** (no sabe que el Combine cerró). | `geometry_scheduler.py` (real: escribe señal y sale) | **Fallo seguro hoy**: `_resolve_account_id` lanza porque la cuenta fijada ya no está entre las activas → el Pi manda un aviso BLOCKED por día y no opera. Pero la señal queda sin consumir y el scheduler ya no escribe otra mientras haya una sin consumir. |
| 3 | **Riesgo grave si se “re-apunta” el Pi MES a la XFA** (cambiando `TOPSTEP_ACCOUNT_ID`): la señal MES (40 contratos) **pasa la validación** (`nc ≤ 40`) y se ejecutaría en la XFA, donde el plan de escalado permite 20 micros con saldo < $1,500 (RULEBOOK 1.6) y el MLL arranca en −$2,000. | `_validate_signal`; RULEBOOK 1.6 | **Nunca re-apuntar la instancia MES a una XFA.** Una instancia del Pi por producto; la instancia MES lleva en `TOPSTEP_ACCOUNT_DENY` los ids de las XFA y la instancia MGC los ids de los Combines (§2). |
| 4 | **La detección de PASE del scheduler no es la de Topstep.** Compara el P&L acumulado **del log** (bruto de comisión: `pi_executor._compute_pnl`) con $3,000, sin mirar la consistencia (mejor día ≤ 55 % de la ganancia; si no, el objetivo sube a mejor día/0.55). Puede declarar “PASE” antes o después que TopstepX. | `geometry_scheduler.py::_check_attempt_reset`; RULEBOOK 3.5 | El sizing finish-line (si se aprueba) y el número de intento dependen de esa cifra. Propuesta lista, sin desplegar: `extras/PASE_guard_NO_DESPLEGAR/combine_state_pure.py` (estado oficial a partir de P&L neto diario, con pruebas). **La fuente de verdad del PASE es el panel de TopstepX, no el scheduler.** |
| 5 | Nadie avisa al operador del PASE en modo real. | código | Mirar TopstepX al cierre de cada día con ≥ $3,000 de ganancia; ver §1.1. |
| 6 | Cada **reset** de un Combine y la **activación** de la XFA cambian el `accountId` (casi seguro; **D**, pregunta 5): hay que actualizar `~/.glitch_pi*.env` y reiniciar el servicio. Con ≈ 40–55 intentos al año es una tarea manual frecuente. | `pi/ARCHITECTURE.md` (“Si la Practice se liquida… la cuenta nueva trae OTRO id”) | Procedimiento en §2; automatizarlo es una propuesta (no se hizo: el invariante “la cuenta nunca se adivina” es deliberado). |

### 1.1 Lista de acciones al pasar (hacerlas en este orden)
1. **Confirmar el PASE en TopstepX** (puede tardar hasta 30 min en reflejarse) y que el Combine figura como “Passed”. No activar la XFA hasta tener los pasos 2–4.
2. **Apagar la señal MES de la mañana siguiente**: en Railway, el servicio MES con `DRY_RUN=true` (paper) *o* pausar el cron, hasta tener el id del siguiente Combine (si se sigue con Cerebro 1) — así no queda una señal huérfana. (Si no se hace, el Pi falla seguro y avisa BLOCKED; es ruido, no riesgo.)
3. **Si el pase fue en viernes**: la XFA no opera hasta el domingo 5 PM CT (RULEBOOK 5.2); no hay prisa.
4. Seguir con §2.

## 2. Activación de la XFA y puesta en marcha de Cerebro 2 (instancia MGC del Pi)

**Estado de código (según `pi/ARCHITECTURE.md`):** la instancia adicional del Pi existe en `main` (`install_service.sh --instance mgc`); el **scheduler MGC** (`geometry_mgc_scheduler.py`) y la geometría real de la XFA 50K (nc 3, SL = TP = 364) están en la rama `feat/t4-mgc-handoff`, **pendientes de revisión humana y de ensayo en Practice**. Es una compuerta: sin ese merge aprobado no hay Cerebro 2 real.

**Paso a paso (Eric):**
1. **Dashboard de Topstep → Trade Report del Combine pasado → “Activate Express Funded Account”.** Elegir **Standard** (la ruta Consistency baja P(≥1 pago) de ≈ 36 % a ≈ 28 % y no se puede cambiar después; solo el RTP obliga a Consistency). **No** marcar DLL (queda fijo para siempre; ver pregunta 7). Pagar $149 (ruta Standard). Verificar que se activa **la cuenta correcta** (sin reembolsos).
2. **Anotar el `accountId` de la XFA** (TopstepX → Settings/Account, o desde el Pi con el cliente de `brokers/projectx.py`: `python3 -c "from brokers.projectx import ProjectXClient, ProjectXCredentials as C; c=ProjectXClient(C.from_env()); [print(a['id'], a.get('name'), a.get('balance')) for a in c.get_accounts()]"` con el entorno cargado: `set -a; . ~/.glitch_pi.env; set +a`).
3. **Instancia MGC en el Pi:** `cd ~/<repo>/glitch && bash pi/ops/install_service.sh --instance mgc` (crea `~/.glitch_pi_mgc.env` vacío, `chmod 600`; se llena **a mano** con `nano ~/.glitch_pi_mgc.env`) y luego `bash pi/ops/install_watchdog.sh --instance mgc`. Nunca dos instancias con el mismo `GLITCH_PRODUCT`.
4. **Valores del `~/.glitch_pi_mgc.env`** (nombres exactos que lee el código):
   ```
   GLITCH_PRODUCT=MGC
   TOPSTEP_ACCOUNT_ID=<id de la XFA>
   TOPSTEP_ACCOUNT_DENY=<ids de los Combines MES, separados por coma>
   GLITCH_PI_NC_MAX=1            # primera semana; luego el valor que decida el §4
   GLITCH_PI_PHASE3=si           # gate de Fase 3 (exige además pi/orderside_verified.json)
   GLITCH_PI_ENTRY_DEADLINE_CT=08:00   # la entrada de MGC es 7:15 CT; el default 10:00 es el de MES
   GITHUB_GIST_TOKEN=...  GIST_ID=...  TELEGRAM_BOT_TOKEN=...  TELEGRAM_CHAT_ID=...  TOPSTEP_USERNAME=...  TOPSTEP_API_KEY=...   # a mano, nunca por chat
   ```
   Y en el `~/.glitch_pi.env` de la instancia **MES**: `TOPSTEP_ACCOUNT_DENY=<ids de las XFA>` (más el id de la Practice si procede). Así ninguna instancia puede operar la cuenta del otro producto aunque se edite mal `TOPSTEP_ACCOUNT_ID`. *(Comportamiento del `DENY` verificado en `_resolve_account_id`.)*
5. **Railway:** servicio de MGC con `GLITCH_PRODUCT=MGC`, `DRY_RUN=false` **solo** después de §6 y del ensayo en Practice; el servicio de MES **no** debe compartir variables con el de MGC. Los archivos del Gist se nombran por producto (`orden_pendiente_mgc.json`, `geometry_mgc_log.json`, `pi_position_mgc…`): una señal MES vieja no puede consumirse en la instancia MGC (`signal["product"]` debe ser igual al `GLITCH_PRODUCT` del Pi; si no, la trata como señal de ensayo de ≤ 2 contratos).
6. **Antes de la primera sesión real:** (a) `python3 pi/ops/check_contracts.py` en el Pi para confirmar que `activeContract` (front month = mayor volumen, MGCZ6 en lugar del vencimiento más cercano) **(NO VERIFICADO en vivo)**; (b) señal de ensayo en la XFA con 1 micro ≤ 2 contratos en horario normal; (c) `systemctl is-active glitch-pi-executor-mgc`.
7. **Calendario:** 26-nov (cerrar 11:45 CT), 27-nov (12:00) y 24-dic (12:00): **el flatten fijo de 14:30 CT del Pi incumple** (RULEBOOK 1.9) → no operar esos días o poner el flatten antes (hueco ya conocido; no tocar el Pi sin aprobación). Entrada 7:15 CT: cae **antes** de la ventana de CPI/NFP/PPI de 7:25–7:35 CT (RULEBOOK 1.8): no se abren posiciones nuevas durante esa ventana, pero la de las 7:15 ya está abierta.

## 3. Primera semana a 1 contrato (decidido en el Project) — qué mirar cada día y semáforos

1 micro de MGC con SL = TP = 364 ticks arriesga **$364 + comisión $1.92** por día (el MLL inicial es $2,000: se necesitan **5 stops seguidos para liquidar**). Se registra cada día (Telegram/historial): lado, referencia vs fill (campos del parche C3 si se aprueba), resultado {TP, SL, FLATTEN} con P&L, balance, **colchón = balance − piso**, días ganadores (≥ $150 **neto**), mejor día.

| semáforo | condición (cualquiera) | acción |
|---|---|---|
| **VERDE** | colchón ≥ $1,200 **y** |fill − referencia| ≤ 3 ticks en todas las entradas **y** el contrato operado es el front month de mayor volumen | seguir tal cual |
| **AMARILLO** | colchón entre $700 y $1,200, **o** un fill con desvío de 4–10 ticks, **o** el balance sigue negativo al 3er día | seguir a 1 micro; registrar; **no subir el tamaño** |
| **ROJO** | colchón < $700 (quedan < 2 stops), **o** un fill con desvío > 10 ticks, **o** una posición mayor que el plan de escalado (RULEBOOK 1.6/1.7), **o** el Pi opera un producto/cuenta distintos de los previstos | **parar** (`systemctl stop glitch-pi-executor-mgc`) y revisar antes de la siguiente sesión |

Notas: con N = 3 sesiones vivas hay 1 trade decidido; **las primeras semanas no validan el WR** (se necesitan ≈ 600+ sesiones para separar 45 % de 50 %, `EVIDENCIA_CEREBRO2.md`): se usan para validar **mecánica** (fills, brackets, flatten, referencia), no rendimiento.

## 4. Política de cobro y tamaño (resultado de la Parte D; ver `REPORTE_D.md` §6 y `resultados_D10/D11.md`)
**Regla base (sin cambios de código):** ruta **Standard**; plan actual 3 micros, SL = TP = 364; **pedir el pago máximo (50 % del saldo, tope $2,000) cuando haya ≥ 5 días ganadores y el saldo ≥ $1,500** (si el saldo es menor, esperar; la política “pedir apenas se pueda” rinde $20–$25 menos por XFA). **Primera semana a 1 micro** (decidido en el Project). Cobrar **al mínimo ($125)** está descartado: −$570 por XFA (y con wire $30 por pago, peor).
**Variante con soporte exploratorio (NO aplicar sin medir slippage y sin la respuesta de Topstep sobre RTP):** 4 micros mientras el saldo sea < $1,500 y 1 micro después (vía `GLITCH_PI_NC_MAX`; el tope solo reduce): cobrado $808 vs $737 (+$70, +10 %), estable en las dos mitades de la historia. **No usar 6–8 micros al inicio** (la DP los prefiere, +30 % en promedio, pero con 8 micros el piso del MLL —no el SL— manda: 33 % de liquidar el día 1; usa el 67 % del máximo de micros y el MLL es el único stop: patrones que el RTP y la conducta prohibida citan).
**Lista de verificación antes de solicitar cada pago:** (1) el panel muestra **≥ 5 días ganadores de ≥ $150 netos** desde el último pago (el día del pago no cuenta); (2) desde el 2º pago: ganancia neta ≥ $0.01 desde el último pago; (3) monto = min(50 % del saldo, $2,000) y ≥ $125; (4) **no es feriado** (no hay pagos); (5) pedirlo **entre las 4:00 y las 5:00 PM CT** (después de las 5:00 el día cuenta como el siguiente y se pierde un día del nuevo ciclo); (6) método de pago y datos fiscales listos (§6); (7) el saldo restante tras el pago será el colchón (piso = $0): si queda < $1,100, operar 1 micro hasta recuperar.

## 5. Reglas de parada y protección (no perder la XFA)
1. **Tras el primer pago el piso es $0**: el colchón = saldo. Con SL = 364 ticks cada micro arriesga $364 + $1.92 ≈ $366: operar como máximo `floor(saldo / 366)` micros mientras el saldo sea < $2,000 (así **un solo SL no puede liquidar**); con 3 micros hacen falta ≥ $1,098 de saldo. **Con menos saldo la liquidación llega antes que el SL** (RULEBOOK 4.6).
2. **No operar** los 3 días de cierre anticipado ni la ventana de noticias si el sistema llegara a abrir en esos minutos.
3. **Tras un SL grande** (colchón < $700): bajar a 1 micro (`GLITCH_PI_NC_MAX=1`, reiniciar el servicio) hasta recuperar colchón ≥ $1,200.
4. **Kill-switch determinista** (código, no LLM; CLAUDE.md regla 1): el Pi ya tiene tope de contratos, ventana de entrada, cuenta fijada y lista de denegación; una **parada por colchón** (no abrir si `balance − piso < SL$ + comisión`) es **propuesta**, no existe hoy → `PROPUESTAS.md`.
5. Inactividad: > 30 días sin operar puede cerrar la XFA.

## 6. Compuertas previas a cualquier payout real (todas deben estar en “sí”)
- [ ] Respuesta **escrita** de Topstep a las preguntas 1, 2, 3, 4 y 13 de `PREGUNTAS_TOPSTEP.md` (guardar número de ticket y fecha).
- [ ] **Titularidad:** un solo perfil de Topstep a nombre legal de **la persona que opera y cobra**; el nombre que muestra el dashboard debe coincidir (en el encargo aparece un nombre distinto del operador: **confirmarlo**); IDV completado; cuenta bancaria **a nombre propio** (no a terceros).
- [ ] **Fiscal:** contador identificado; formulario **W-8BEN** (no estadounidense) o W-9; definir quién declara qué (México: Topstep no da asesoría fiscal ni reporta a México); **no hay payout real sin esto** (ver §16 del doc del 26-sep).
- [ ] **País:** residencia/ciudadanía de Eric vs la lista de elegibilidad (México no figura en las listas de inelegibles; **verificarlo con soporte**).
- [ ] **Método de pago** definido y su costo: para quien no está en EE. UU./China/Canadá/Reino Unido la opción es wire/SWIFT con **$30 por pago** (5–10 días): con pagos de $125 ese costo pesa; ver el escenario T30.
- [ ] Parches NO DESPLEGAR de las partes A–C revisados y aprobados (en particular C2: detección de liquidación) y Cerebro 2 probado en Practice con 1 micro.
- [ ] Plan de **evidencia** (`EVIDENCIA_CEREBRO2.md`) en marcha: registrar slippage (C3) y el resultado diario completo (TP/SL/FLATTEN).
