# PLAYBOOK_XFA — reglas, estados, variables multiobjetivo y registro de decisiones (21-nov-2026)

**Para qué sirve:** que una cuenta XFA nueva (otro monto, otro producto, otra firma) se pueda decidir y desplegar con el mismo esquema: (1) qué reglas mandan, (2) qué pasa cuando ocurre cada evento, (3) qué variables se optimizan y cuáles no, (4) por qué se tomó cada decisión y con qué evidencia. Etiquetas: **V** verificado en fuente primaria, **M** MEDIDO (datos), **MOD** MODELADO (simulación), **S** supuesto, **NV** no verificado. Todo número de este documento sale de un script con semilla fija en `glitch/experimentos/estructura/` (índice en §4). Un agente propone; **la revisión y el despliegue son humanos** (CLAUDE.md regla 4).

## 0. Cómo usarlo con una cuenta nueva
1. Copiar §1 (reglas) y corregir cada fila con la fuente de la nueva firma o cuenta.
2. Copiar §2 (estados) y §3 (variables); marcar qué variables existen en el nuevo producto.
3. Medir el régimen real (rango diario, probabilidad de TP por geometría) con barras propias (§4, paso LUNES8A).
4. Declarar prioridades (§5) **antes** de correr y registrar la decisión en §6 con fecha, evidencia y reversibilidad.
5. Desplegar con un runbook (`ACTIVAR_*.md`) y verificar con los comandos de verificación; anotar la fecha del cambio para separar datos reales.

## 1. Reglas del instrumento (XFA 50K de MGC, Topstep)
| regla | valor | estado | fuente |
|---|---|---|---|
| MLL | $2,000 desde el saldo máximo al cierre; se vigila en tiempo real con P&L no realizado (un stop mayor que el MLL está permitido) | V | respuestas de Topstep Support, 28-oct; `auditoria_envio/REGLAS_XFA_VERIFICADAS_2026-10-31.md` |
| Piso antes del primer cobro | `min($0, pico − $2,000)` | V | Help Center de Topstep |
| **Piso después del primer cobro** | **$0** (el saldo que queda ES el colchón) | V | confirmado con Topstep el 14-ago-2026 |
| Monto del cobro | **hasta** 50 % del saldo, tope $2,000 por solicitud, **mínimo $125**; se descuenta del saldo de inmediato; el trader recibe 90 % | V (monto) / S (90 %, modelado) | `REGLAS_XFA_VERIFICADAS` fila «Monto» |
| Requisito del cobro | 5 días con al menos $150 netos; tras el cobro el contador vuelve a 0; el siguiente cobro exige 5 días nuevos, saldo >= $250 y mayor que el saldo que quedó tras el cobro anterior | V / S (la regla del saldo mayor, omitida en el DP) | `REGLAS_XFA_VERIFICADAS`, LUNES3 |
| Plazos y costos | aprobación 1-3 días hábiles; desembolso 7-10 días hábiles; wire $30 | V | `REGLAS_XFA_VERIFICADAS`; wire NO estaba en los modelos hasta LUNES9 |
| Contratos máximos (MGC, 50K) | 12 micros con saldo < $1,500; 18 con $1,500-$2,000; 31 con más de $2,000 (no sube a mitad de sesión; un cobro que baja el saldo baja el máximo) | V (plan de escalado) | `REGLAS_XFA_VERIFICADAS`; `pi_executor` |
| RTP (Responsible Trading Program) | motivos citados: tamaño máximo en la mayoría de los trades, perdedores mayores que ganadores, operar sin stops, varias cuentas en el MLL el mismo día; **umbrales no publicados**; cambiar el tamaño según el saldo NO es disparador (Support, 28-oct) | V (motivos) / NV (umbrales) | `REGLAS_XFA_VERIFICADAS`; Support |
| Sesión | entrada 07:15 CT, flatten 14:20 CT en el modelo; cierres anticipados (27-nov: flatten 11:30 CT); Thanksgiving cerrado | M | `execution/session_calendar.py` |
| Costos del modelo | $1.92 por micro y por viaje redondo + 1 tick de slippage | S | `selectivo_lib`, `manual_auto_run.cfg` |

## 2. Máquina de estados: qué pasa cuando sucede
**Estados.** E0 acumulando (saldo < X) · E1 meta alcanzada (saldo >= X y 5 días cumplidos; falta pedir el cobro) · E2 cobro pedido (colchón = saldo restante, piso $0, contador 0) · E3 fase 2 acumulando (5 días nuevos) · E4 segundo cobro pedido (se repite E2 con el colchón nuevo) · E5 cuenta liquidada.

| evento | qué cambia | qué hace el sistema | qué hace el humano |
|---|---|---|---|
| TP del día (E0) | el saldo sube n × (TP − 1 tick) − comisiones | si saldo >= U, la regla del Pi baja a `lo` (1 micro) hasta que se pida el cobro | pedir el cobro al cierre (4:00 PM CT) del mismo día |
| SL o MLL en contra | pérdida del trade; si saldo − adversión × n <= piso, **liquidación** (E5) | el exchange liquida; el Pi registra `UNKNOWN` | decidir cuenta nueva |
| Día sin TP ni SL (FLATTEN) | P&L aleatorio de ~cero con cierre a las 14:20 CT | nada | nada |
| Saldo llega a X (E0 → E1) | solo X cambia cuánto saldo se junta antes de cobrar | Pi opera `lo` micros | pedir el cobro; elegir el monto (de $125 a 50 %) |
| Cobro pedido (E1 → E2) | saldo − monto; **piso = $0**; colchón = saldo restante; contador = 0 | candado: si el saldo cae más de $100 bajo el esperado, opera `GLITCH_PI_XFA_POST_PAYOUT_NC` (1) micros y avisa por Telegram | confirmar el aviso; si no llegó, `GLITCH_PI_XFA_PAYOUT_DONE=si` y reiniciar con la cuenta plana |
| Viernes sin cobrar (E0) | último intento de la semana | `GLITCH_PI_XFA_LASTDAY=AAAA-MM-DD:n` sube a n micros ese día | nada (verificar el log) |
| Cierre anticipado | flatten 11:30 CT | `session_calendar` | nada |
| Señal sin barras (BLOCKED) | no se opera ese día | el Pi reintenta cada 120 s y avisa una vez al día | revisar el contrato activo (`pi/ops/check_contracts.py`) |
| Roll de contrato (Z26 a G27) | liquidez y spread | `roll_rules`: corte 2 días hábiles antes del FND (26-nov) | verificar contrato el lunes antes de las 7:00 de Monterrey |
| 5 días nuevos ganadores + saldo > saldo tras cobro (E3) | elegible para el 2.º cobro | nada | pedir el cobro (el máximo, salvo que se quiera conservar colchón) |
| Revisión del RTP | puede frenar un cobro | nada | escribir a Topstep; documentar la fecha |

## 3. Mapa de variables del problema multiobjetivo
**3.1 Control (se eligen).**
| variable | rango estudiado | dónde se activa | ¿código? | mapeo |
|---|---|---|---|---|
| geometría SL/TP | 728/80, 500/120, 500/250, 120/360, 364/364, 250/250, 300/150, 200/100, 364/182 (+364/728, 728/728 de referencia) | Railway `GLITCH_XFA_BRACKET_TICKS` + `GLITCH_XFA_TP_TICKS` | solo 364/364, 120/360, 364/728, 728/728 sin código; 364/182 y 500/250 con el parche | mapeada |
| contratos de fase 1 (n) | 1-12 (DP: 1, 2, 3, 4, 5, 6, 8, 12) | Pi `GLITCH_PI_XFA_SIZE_RULE=n:X:1` (n <= 12) | no | mapeada |
| palanca del último día | 12 micros el último día si no se cobró | Pi `GLITCH_PI_XFA_LASTDAY` | parche | mapeada (LUNES9B) |
| saldo X al que se pide el primer cobro | $250 a $3,350 | `U` de la regla del Pi (y manual en TopstepX) | no | mapeada (LUNES13, 16) |
| monto del primer cobro | 20 %-50 % del saldo, o mínimo $125 | manual en TopstepX | no | mapeada (LUNES15, 16) |
| fase 2: geometría y contratos | misma o 120/360; 1 o 2 micros | `GLITCH_PI_XFA_POST_PAYOUT_NC`; Railway para la geometría | no | mapeada (LUNES11, 16) |
| dirección | alternar / solo short / solo long | Railway `GLITCH_XFA_DIRECTION` + `_UNTIL` | parche | mapeada como escenario (LUNES12) |
| hora de entrada y de cierre | fijas (07:15 y 14:20 CT) | código de capital | sí | **sin mapear** |
| regla que cambia con la volatilidad | — | código | sí | **sin mapear** |
| no operar por evento o régimen | solo se probó no operar el viernes | código | sí | **sin mapear** |

**3.2 Ambiente (inciertas).** Probabilidad de acertar el mejor lado p (0.45 realista, 0.50 optimista) · distribución de los días (440 históricos en bloques de 5; 19 sesiones reales de MGCZ6 por separado; terciles de volatilidad) · slippage y comisión (probado hasta +4 ticks) · wire $30 · cierre anticipado · roll Z26 a G27 (**no medible**) · umbrales del RTP (**no medibles**; deslizadores de riesgo en el mapa) · calendario macro (**sin verificar**).

**3.3 Objetivos (vector).** f1 = P(pedir el primer cobro antes del cierre del viernes) · f2 = dinero total (cobro neto + fase 2 a 100 sesiones; también dinero a 21 sesiones del motor) · f3 = P(2.º cobro), incondicional y dado el primero · f4 = cobro neto medio y percentiles · f5 = colchón tras el cobro y «balas» (colchón / pérdida de un trade con 1 micro) · f6 = P(muere sin cobrar) · f7 = cuenta viva a 10 sesiones tras cobrar. **Restricciones duras:** contratos <= tope de escalado; geometría en `XFA_GEOMETRIES`; ninguna decisión de riesgo es una llamada a un LLM; el MLL nunca se desactiva. **Preferencias:** precio de un punto de f1 (unos $9-$15 según horizonte), tolerancia a perder la vida de la cuenta, tolerancia a banderas del RTP.

## 4. Método y reproducibilidad
Motor de simulación con barras de 5 minutos (07:00-14:20 CT; entrada 07:15, empates intrabarra en contra), bootstrap en bloques de 5 días, estado real inicial (saldo +$28.28, 5 días, colchón $2,000), semilla 20261121, validación cruzada de 3 tercios cronológicos para la fase 1 (la fase 2 usa todos los días), escenarios realista y optimista (sensibilidad, no intervalos). Cada paso se preregistró en un commit antes de ver resultados; los exploratorios se etiquetan.
| paso | pregunta | resultado | archivos |
|---|---|---|---|
| LUNES, 2, 3, 4, 5 | tamaño, TP, qué pasa tras el cobro, dos fases, doble objetivo | el tamaño manda; el 2.º cobro es raro con colchón chico | `LUNES*.md` |
| LUNES6, 7 | DP exacto + validación cruzada; dos fases con cambio de geometría | óptimo: entrar fuerte hasta cobrar, 12 micros la última sesión; DP = simulación (1.2 %) | `LUNES6.md`, `LUNES7.md` |
| LUNES8A/B/C | mapa de P(TP) por régimen; frontera práctica | TP 728: 6 % histórico, 3 % real; $11-$14 por punto | `LUNES8*.md` |
| LUNES9, 9B | variables nuevas: viernes, slippage, wire, 19 reales | palanca del viernes; 120/360 cae en el real | `LUNES9*.md` |
| LUNES10, 11, 11b | cómo termina la semana; después del cobro | cobras o muere; bajar a 1 micro | `LUNES10.md`, `LUNES11.md` |
| LUNES12, 12B | alternar contra solo short | 3 de 4 sesiones LONG alternando; sin persistencia en 440 sesiones | `LUNES12*.md` |
| LUNES13, 14, 14B | primer cobro de $1,000-$1,500 | TP mínimo para cruzar X en un golpe; 250/250 con 9-10 micros | `LUNES13.md`, `LUNES14*.md` |
| LUNES15, 16 | cobro parcial y saldo X | no mejoran el dinero; compran vida | `LUNES15.md`, `LUNES16.md` |
| LUNES17 | A contra B con prioridad «segundo cobro» | ver §7 | `LUNES17.md` |
Mapa interactivo: https://claude.ai/artifact/L9bpm4mMXUao48t4KqULDc (hasta LUNES9B).

## 5. Prioridades y su historia
1. **Prioridad inicial (20-nov):** maximizar P(pedir el cobro esta semana) y el dinero; la vida de la cuenta y el número de cobros se sacrifican.
2. **Hallazgo que la cambia (21-nov):** al cobrar, el piso del MLL pasa a $0 y el colchón es el saldo restante (~$372 con 364/182 y cobro máximo: una sola pérdida de 1 micro). Eric reorienta: **poder tener una oportunidad real de un segundo cobro**, lo que exige colchón.
3. **Consecuencia:** el objetivo relevante pasa a f3 (2.º cobro), f5 (colchón/balas) y f7 (vida), además de f1 y f2. Hay dos maneras de comprar colchón: cobrar más (más contratos, geometría que cruce X de un golpe) o cobrar menos (monto parcial, hasta el mínimo de $125).

## 6. Registro de decisiones (ADR)
| id | fecha | contexto | opciones | evidencia | decisión | reversible | estado |
|---|---|---|---|---|---|---|---|
| D-01 | 28-oct | cambiar el tamaño por saldo, ¿está permitido? | tamaño fijo / regla `hi:U:lo` | Support (no es disparador del RTP); `optimo/` | regla de tamaño y tres palancas, APAGADAS por defecto | sí (variables) | vigente |
| D-02 | 29-oct | arranque de la XFA | MES / MGC | HITOS_PROYECTO | Pi y Railway en MGC, tamaño de la regla | sí | vigente |
| D-03 | 14-15-nov | TP del SL 364/728 | 728/728 / 364/728 con 1 micro | PR 6, `ACTIVAR_GEOMETRIA_XFA.md` | SL 364 / TP 728 con 1 micro | sí (Railway) | superada por D-07 |
| D-04 | 20-nov | MES Combine | seguir / apagar / silencio | LUNES (MES), análisis del paper | cron pausado; silencio preparado en `feat/mes-paper-silent` | sí | vigente |
| D-05 | 20-nov | TP 728 casi no se toca | mantener / TP <= 364 | LUNES8A (6 % hist., 3 % real) | frontera práctica con TP <= 364 | sí | vigente |
| D-06 | 20-nov | prioridad inicial | P(cobro) / dinero | LUNES6-8 | frontera con precio de $11-$14 por punto | sí | histórica (§5) |
| D-07 | 20-nov | configuración del lunes | ver LUNES8-11 | LUNES9B, 10, 11 | **A:** 364/182, 4 micros + 12 el viernes, X $250, cobro 50 %, luego misma con 1 micro; parche en `feat/xfa-lunes-364-182` | sí | vigente hasta D-09 |
| D-08 | 21-nov | 120/360 recomendado sin probar en el real | mantener / retirar | LUNES9 (19 sesiones: 54 % a 34 %) | retirado | — | cerrada |
| D-09 | 21-nov | prioridad = segundo cobro (MLL post-cobro) | A / B / C / D / E y cobro parcial | LUNES16, 17 (§7) | **propuesta:** B = 500/250, 12 micros, X $500, luego 1 micro; parche en `feat/xfa-lunes-500-250`. Falta decidir el monto del primer cobro (máximo o mínimo) | sí (variables) | **pendiente de confirmación de Eric** |
| D-10 | 21-nov | dirección de la semana | alternar / solo short / solo long | LUNES12, 12B | decide Eric el domingo; `GLITCH_XFA_DIRECTION*` con fecha de expiración | sí | pendiente |
Cada nueva decisión se agrega aquí con: contexto, opciones, evidencia (archivo y commit), decisión, reversibilidad y estado.

## 7. Comparativa A (parche del lunes) contra B (500/250 con 12 micros), LUNES17
A = 364/182, 4 micros + 12 el viernes, X $250. B = 500/250, 12 micros siempre, X $500. Ambas: cobro 50 %, luego misma geometría con 1 micro. **Nota:** «500/200» no existe en los estudios; se asume 500/250.
| métrica (realista / optimista) | A | B |
|---|---|---|
| P(pedir el cobro antes del viernes) | 68 / 72 % | 41 / 45 % |
| P(muere sin cobrar en la semana) | 30 / 26 % | 59 / 55 % |
| cobro neto mediana (p10 / p90) | $335 ($182 / $374) | $1,347 ($483 / $1,347) |
| colchón tras el cobro, mediana | $372 | $1,497 |
| «balas» (colchón / pérdida de 1 trade con 1 micro) | 1.0 | 3.0 |
| P(2.º cobro) incondicional | 21 / 28 % | 22 / 30 % |
| P(2.º cobro) si cobró el primero | 30 / 38 % | 54 / 66 % |
| dinero total (cobro + fase 2 a 100 sesiones) | $372 / $485 | $754 / $987 |
| cuenta viva 10 sesiones tras cobrar | 30 / 37 % | 75 / 80 % |
| primer día: P(meta) / P(liquida) | 50 % / 0 % | 48 % / 51 % |
| 19 sesiones reales: P(cobro) / dinero | 70 % / $416 | 39 % / $849 |
| banderas del RTP | TP < SL; 12 micros solo el viernes | TP < SL **y 12 micros en todas las sesiones** (tamaño máximo en todos los trades) |

**Diferencia de fondo.** A es una serie de apuestas chicas (4 micros, el MLL no llega nunca el primer día) que cobra poco y deja un colchón de una bala. B es una sola moneda al aire con el máximo de contratos: cada día gana +$3,000 con ~48 % o liquida la cuenta con ~51 %. B cobra menos veces (41 % contra 68 %), pero cuando cobra deja un colchón 4 veces mayor (3 balas) y la cuenta sigue viva a 10 sesiones el 75 % de las veces, contra 30 %.

**Lo que B NO hace.** Con la prioridad «segundo cobro», la probabilidad **incondicional** de un 2.º cobro es casi la misma en A y en B (21 % contra 22 %): B gana el colchón pero pierde el primer cobro. Las opciones que más probabilidad de 2.º cobro dan son otras (LUNES16): 364/182 con 10 micros (26 / 34 %, dinero $607 / $778) y, **con cobro mínimo de $125**, 364/182 con 6 micros + 12 el viernes pidiendo a $750 (P_semana 58 / 62 %, 2.º cobro 34 / 44 %, cuenta viva 76 %, dinero $416 / $619). B con cobro mínimo: P_semana 41 / 45 %, 2.º cobro 27 / 35 %, cuenta viva 91 %, dinero $619 / $961.

**Lectura.** Si la prioridad es el 2.º cobro con la mayor probabilidad posible, la frontera favorece **364/182 con 6 micros y cobro mínimo**. Si la prioridad es colchón grande y dólares, B (con cobro máximo $754 o mínimo $619; en ambos casos 12 micros siempre). La elección depende de cuánto pese el riesgo de RTP por tamaño máximo en todos los trades (umbral desconocido) y de cuántos puntos de P_semana se acepten perder.

## 8. Plantilla de despliegue de una cuenta nueva
1. Hechos: monto de cuenta, MLL, regla de cobro, escalado, RTP, comisiones (§1).
2. Datos: 440+ sesiones del producto y las sesiones reales disponibles; régimen actual y su percentil (LUNES8A).
3. Prioridades declaradas por escrito (§5) y precio de un punto de probabilidad.
4. Preregistro en un commit (reglas, grilla, criterio), luego correr; verificar el motor contra un resultado conocido.
5. Frontera con reglas deployables (contratos fijos, X, monto, fase 2) y, si hace falta, DP como techo.
6. Robustez: 19 sesiones reales, terciles de volatilidad, slippage, wire, cierres anticipados.
7. Decisión registrada en §6; parche con todo APAGADO por defecto y pruebas; runbook con verificación.
8. Monitoreo: comparar la primera semana contra la tabla de eventos de §2; criterios para revisar: ocurrencia de eventos no modelados, P_semana real contra modelada, cambio de régimen.

## 9. Pendientes y no verificado
Valor actual de `GLITCH_PI_NC_MAX` y `GLITCH_PI_MLL_GUARD` en el Pi · rama que despliega Railway MGC · calendario macro de la semana del 23-nov · umbrales del RTP · si el 20-nov hubo [OPEN] y [CLOSE] · el parche no se probó en vivo (solo pruebas simuladas) · las cifras de fase 2 usan todos los días (sin validación cruzada) · el DP no se rehízo con las variables nuevas (solo reglas deployables).
