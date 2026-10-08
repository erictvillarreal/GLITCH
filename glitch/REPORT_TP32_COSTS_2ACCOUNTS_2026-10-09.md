# TP 32 fuera de muestra, desglose de costos A–F y diseño de 2 cuentas en el Pi
*Rama `research/scale-what-it-takes`, sandbox, 09-oct-2026. Sin código de producción. Scripts: `scripts/tp32_oos_validation.py`, `scripts/cost_breakdown.py` (salidas en `dd_cash/`); el diseño se apoya en el código real de `origin/main` (`2ed2ec2`) y en artículos oficiales de help.topstep.com leídos hoy.*

## 0. Lo más importante (en este orden)
1. **TP 32 sí sobrevive fuera de muestra.** P(pasar el Combine) +7.1 pp (IC95% por bloques [+5.7, +8.2]); gana en los 10 bloques; el reality check sobre 13 TP da p < 0.005. La ventaja es de **estructura** (dos TP netos de $1,551 suman $3,102 ≥ $3,000), no de acertar más: el win rate de TP 32 (56.5%) está en su punto de equilibrio (56.9% con comisión).
2. **El nivel de ganancia, en cambio, depende de una sola ventana de 10 semanas.** Entre el 14-nov-2025 y el 26-ene-2026 la serie de Cerebro 2 (MGC) ganó +$77.5 por contrato y día; en los otros 9 bloques fue negativa (−$5.9 a −$50.3). **Sin ese bloque, el pipeline con TP 32 rinde $1,302 por cuenta (no $2,915) y con 2 cuentas $3,318 (no $6,544), con 36% de pérdida y 28% de llegar a $7,000.** El número de $6.6k que aceptaste está en el extremo optimista de ese rango.
3. **Dos cuentas con las mismas señales chocan con una señal explícita del Responsible Trading Program de Topstep:** "multiple accounts hitting the Maximum Loss Limit in one day" (y "you max position a majority of your trades"). Además el pipeline compra **~44–53 intentos de Combine por cuenta al año** (88 con 2 cuentas).
4. **El ejecutor actual del Pi no soporta 2 instancias tal como está:** comparten el archivo de estado del Gist, el de la señal, el historial y el aviso de Telegram. La instancia B **adoptaría el bracket de la A** en su primer `reconcile_if_needed()`.

## 1. Validación fuera de muestra de TP 32 vs TP 40 (G2/MES, nc 40, SL 100)
Datos: 515 días de MES; 10 bloques contiguos de ~51 días; Combine 50K con reglas reales (MLL en tiempo real, consistencia 55%, mínimo 2 días); pipeline con el motor validado (Combine + XFA Cerebro 2), payouts −25%, costo compartido $714/año. Supuesto de todo el bloque: los días de cada bloque son una muestra independiente de ese bloque (bootstrap de días dentro del bloque).

**Parámetros probados y corrección por búsqueda múltiple:** en este análisis se probaron **13 valores de TP** (20, 25, 28, 30, 31, 32, 33, 34, 35, 36, 40, 45, 50). En todo el proyecto, los grids de geometría suman >1,800 configuraciones (1,080 del Camino B bajo reglas reales, 767 de la Parte B y los barridos del 5–8 oct). Corrección aplicada: **reality check de White** con bootstrap por bloques de 10 días (200 réplicas) sobre los 13 TP contra TP 40. Como además el TP 32 es el mínimo entero que hace que dos TP cubran el objetivo con margen (fórmula: 2·(50·TP − 48.8) ≥ 3,000 ⇒ TP ≥ 31.5), el número de parámetros libres efectivos es ~1.

**Punto de equilibrio y win rate observado** (win = el TP se toca antes que el stop; barra ambigua = stop primero):
| | Stop efectivo 40 ticks (liquidación del MLL con nc=40) | | Stop nominal 100 ticks (Practice/paper) | |
|---|---|---|---|---|
| | TP 32 | TP 40 | TP 32 | TP 40 |
| Equilibrio sin comisión | 55.6% | 50.0% | 75.8% | 71.4% |
| Equilibrio con comisión | 56.9% | 51.2% | 76.5% | 72.1% |
| **Win rate observado** [IC95%] | **56.5%** [52.2, 60.7] | 49.3% [45.0, 53.6] | **71.5%** [67.4, 75.2] | 65.2% [61.0, 69.2] |
| Exceso sobre equilibrio (con comisión) | −0.4% | −1.9% | −5.0% | −6.9% |
| Rango entre bloques | 53%–63% | 43%–58% | 61%–83% | 51%–77% |
Ninguno de los dos supera su equilibrio: **no hay edge de dirección**. El win rate sube de 49% a 56% porque el TP queda más cerca, pero el equilibrio sube casi igual.

**P(pasar) por bloque (pareado, mismos números aleatorios)** TP 32 / TP 40: 41.9/34.4, 32.8/25.9, 39.4/31.4, 31.2/23.2, 30.6/29.2, 30.0/20.4, 30.8/22.8, 30.0/21.6, 30.9/24.5, 33.9/26.5 (%). Diferencia media **+7.1 pp**, TP 32 gana en **10/10** bloques (prueba de signos unilateral p = 0.001), IC95% bootstrap por bloques **[+5.7, +8.2]**.

**Pipeline anual por bloque** (media por cuenta, TP 32 / TP 40, con P(pérdida)): b1 $1,747/$1,353 (32%/37%); b2 $2,905/$2,254 (21%/28%); b3 −$224/−$510 (59%/63%); b4 −$1,127/−$1,863 (70%/78%); b5 $1,991/$1,925 (33%/34%); b6 $2,156/$727 (35%/49%); **b7 $27,526/$26,419 (0%/0%)**; b8 −$1,660/−$2,659 (72%/80%); b9 $1,090/$360 (44%/51%); b10 $3,496/$2,670 (24%/31%). TP 32 supera a TP 40 en **10/10**; diferencia media +$723 por cuenta y año (IC95% [+$490, +$958]). **La dispersión entre bloques ($−1.7k a $+27.5k) es la verdadera incertidumbre del nivel**, ver §1.1.

**Walk-forward** (entrenar con los bloques 1…j, elegir el mejor de los 13 TP, medir en el bloque j+1; j=2…9): el procedimiento elige **TP 31 en los 8 pasos**; fuera de muestra: elegido 33.4% | TP 40 25.1% | TP 32 fijo 32.2%; el elegido supera a TP 40 en 8/8 bloques y TP 32 también en 8/8. **TP 31 es un filo de navaja:** dos TP netos = $3,002 vs $3,000; con comisión $1.52 o más su P(pasar) cae de 34.1% a 23.3%. **TP 32 no se mueve** (33.1% con $1.22, $1.52, $1.82 y $2.44) y TP 33 solo baja a 31.1%. Por eso se recomienda 32, no 31.

**Reality check (13 TP vs TP 40):** diferencia en toda la muestra: TP 31 +8.3, TP 32 +7.3, TP 33 +5.5, TP 34 +4.4, TP 35 +4.0, TP 36 +3.7; TP 20, 28, 30, 45, 50 de −0.5 a −3.7; **p del máximo < 0.005** (ninguna de las 200 réplicas igualó la diferencia observada). TP 32 vs TP 40: **+7.3 pp, IC95% [+5.1, +9.1]**.

**Conclusión: SÍ, la ventaja de TP 32 sobrevive fuera de muestra** en P(pasar) (+7.1 pp, IC [+5.7, +8.2]) y en el anual por cuenta (+$723, IC [+$490, +$958]); bajo un DLL automático de $1,000 (escenario RTP) el pase es 29.0% con TP 32 contra 24.8% con TP 40. Es una mejora de **estructura** con riesgo operativo nulo (mismo tamaño y mismo stop); no es evidencia de edge.

### 1.1 Hallazgo crítico: el nivel depende de la ventana nov-2025/ene-2026
Media diaria por contrato de la serie MGC 7:13 (364/364) por bloque: −5.9, +4.6, −23.5, −33.3, −7.8, −14.2, **+77.5 (14-nov-2025 a 26-ene-2026)**, −50.3, −24.7, −8.5; promedio general −$8.6. Leave-one-block-out del pipeline (TP 32; neto por cuenta tras compartido; 2 cuentas = 2×neto − $714):
| Se excluye | 1 cuenta | 2 cuentas | P(pérdida), 2 cuentas | P(≥$7k), 2 cuentas |
|---|---|---|---|---|
| ninguno | $2,915 | $6,544 | 22% | 44% |
| bloque 1 / 2 / 5 / 6 / 9 / 10 | $2,842–$3,158 | $6,397–$7,030 | 22–24% | 43–45% |
| bloques 3 / 4 / 8 | $3,315 / $3,472 / $3,520 | $7,344 / $7,658 / $7,755 | 21% / 19% / 18% | 47% / 48% / 49% |
| **bloque 7** | **$1,302** | **$3,318** | **36%** | **28%** |
Con TP 40 sin el bloque 7: $628 por cuenta. La diferencia TP 32 − TP 40 se mantiene en todos los casos (+$0.7k a +$0.8k por cuenta). **Lectura:** el payout de la XFA proviene sobre todo de la ventana en que el oro tuvo tendencia; en el resto, el pipeline es casi de equilibrio. No es un edge demostrado (la prueba de realidad del 8-oct no encontró ninguno); es un régimen que puede o no repetirse.

## 2. Desglose de costos por escenario A–F
12 meses desde el 19-oct-2026 (255 días hábiles), motor validado con calendario, payouts **tras −25%** (liquidación en tiempo real de la XFA, log del 24/25-sep), cobro 5 días después de pedir el payout, costo compartido $59.5/mes × 12 = $714 **una sola vez**, cuentas con las **mismas señales** (correlación perfecta). Detalle completo en `dd_cash/cost_breakdown_report.txt`.

**Correcciones a mis tablas del 8-oct (declaradas):** (a) faltaba la **tarifa inicial** del Combine ($49 en 50K, $199 en 150K): −$49 por cuenta; (b) los scripts previos cobraban 13 cargos de costo compartido en vez de 12: +$59.5. Efecto neto en 50K ≈ −$10; en 150K −$140 por cuenta. El motor no registra renovaciones mensuales (los intentos duran ~2 días): la fila "renovaciones" es 0.

**USD por cuenta y año** (media / mediana / p10 / p90; "neto total" ya incluye el compartido y N cuentas):
| Escenario | Payouts brutos | Tras −25% | Fees Combine (reinicios + compras nuevas) | Activaciones | Tarifa inicial | Neto por cuenta (sin compartido) |
|---|---|---|---|---|---|---|
| A. 50K, TP 40 (lo que corre) | 9,950 / 9,375 / 4,431 / 16,211 | 7,462 / 7,031 / 3,323 / 12,159 | 2,539 / 2,499 / 1,813 / 3,283 | 1,991 / 1,937 / 1,639 / 2,384 | 49 | 2,883 / 2,399 / −2,050 / 8,419 |
| B. 50K, TP 32 | 10,583 / 10,010 / 4,976 / 16,869 | 7,938 / 7,507 / 3,732 / 12,652 | 2,110 / 2,107 / 1,519 / 2,744 | 2,119 / 2,086 / 1,639 / 2,533 | 49 | 3,660 / 3,178 / −1,293 / 9,178 |
| E. 150K, TP 32 | 18,330 / 16,993 / 7,414 / 30,931 | 13,747 / 12,745 / 5,561 / 23,198 | 10,042 / 9,950 / 7,164 / 12,935 | 1,680 / 1,639 / 1,341 / 1,937 | 199 | 1,826 / 852 / −8,466 / 13,543 |
(C y D usan las cifras de B por cuenta; F las de E.)

**Neto total anual con N cuentas** (después del compartido de $714):
| Escenario | Media | Mediana | p10 | p90 | P(<0) | P(≥$7k) |
|---|---|---|---|---|---|---|
| A. 50K TP 40 ×1 | 2,169 | 1,685 | −2,764 | 7,705 | 33% | 13% |
| B. 50K TP 32 ×1 | 2,946 | 2,464 | −2,007 | 8,464 | 25% | 16% |
| C. 50K TP 32 ×2 | 6,606 | 5,642 | −3,299 | 17,643 | 22% | 44% |
| D. 50K TP 32 ×3 | 10,266 | 8,820 | −4,592 | 26,821 | 21% | 56% |
| E. 150K TP 32 ×1 | 1,112 | 138 | −9,180 | 12,829 | 49% | 23% |
| F. 150K TP 32 ×2 | 2,938 | 989 | −17,645 | 26,373 | 48% | 37% |

**Compras y reinicios de Combine por año** (intentos = 1 inicial + reinicios [quiebre del Combine, mismo precio que la mensualidad] + compras nuevas [quiebre de la XFA]):
| Escenario | Por cuenta (media; p90) | Reinicios | Compras nuevas | Activaciones de XFA | TOTAL (N cuentas) | Por mes (total) |
|---|---|---|---|---|---|---|
| A | 52.8 (68) | 39.1 | 12.7 + 1 | 13.4 | 53 | 4.4 |
| B | 44.1 (57) | 29.6 | 13.5 + 1 | 14.2 | 44 | 3.7 |
| C | 44.1 por cuenta | 59 | 29 | 28 | **88** | 7.3 |
| D | 44.1 por cuenta | 89 | 43 | 43 | **132** | 11.0 |
| E | 51.5 (66) | 39.8 | 10.7 + 1 | 11.3 | 51 | 4.3 |
| F | 51.5 por cuenta | 80 | 23 | 23 | **103** | 8.6 |

**Comparación con la regla de Topstep sobre compras excesivas.** La regla no da un número. Lo oficial leído hoy: no hay límite de Combines simultáneos ("Yes — no limit on how many you can have at once", artículo de suscripciones; ese artículo tampoco da precio de reinicio ni tope de compras). Pero la conducta prohibida del ToU incluye "excessive purchases of Combines or Resets" y "account stacking — repeatedly hitting the MLL in one account and switching to another to repeat high-risk attempts"; el Responsible Trading Program (help.topstep.com/13620045) se activa con "trading that isn't sustainable in live markets", entre cuyas señales figuran **"multiple accounts hitting the Maximum Loss Limit in one day"** y **"you max position a majority of your trades"**. El pipeline modelado (≈1 intento por semana por cuenta, hasta 11 al mes con 3 cuentas, siempre al máximo de contratos, y con cuentas que tocan el MLL el mismo día por construcción) coincide con esos patrones. **Consecuencias oficiales del RTP:** DLL automático ("50K = −$1,000, 100K = −$2,000, 150K = −$3,000") en todo Combine y XFA nuevo; la XFA queda limitada a Consistencia (mejor día < 40% de las ganancias del periodo de pago); la XFA estándar no está disponible hasta completar el RTP; hasta 5 XFA. **No modelé la consistencia de 40% de la XFA bajo RTP:** reduciría los payouts de este pipeline y es el principal riesgo no cuantificado del plan.

**Supuestos explícitos de §1 y §2:** una sola historia de 515 días (MES) alineada con la serie de MGC 7:13 (364/364); el −25% a payouts es un ajuste aproximado; el reinicio de un Combine cuesta lo mismo que la mensualidad ($49 / $199) y se puede hacer inmediatamente tras el quiebre (hasta 2 por día según el log del 24-sep); la activación de $149 para 150K no está verificada; nunca se han ejecutado 40 contratos reales.

## 3. Diseño: 2 cuentas en el Pi (solo documento)
### 3.1 Qué hace hoy el ejecutor (con referencias a `pi/pi_executor.py` de `origin/main`)
- **Un proceso, una cuenta, un trade a la vez y bloqueante:** `run_once()` coloca el bracket y se queda en `poll_position_until_closed()` hasta que resuelve o llega el flatten de las 14:30 CT (`:709–806`); luego `_finalize_cycle()` (`:841`).
- **Archivos en el Gist, nombrados solo por producto, no por cuenta** (`:158–161`): `orden_pendiente_mes.json` (señal), `pi_position_mes.json` (estado del bracket abierto), `pi_block_notice_mes.json` (aviso diario), `geometry_mes_log.json` (historial, el mismo del scheduler de Railway). `gist_store._write_file` hace PATCH por archivo; no hay control de concurrencia (`execution/gist_store.py`).
- **En disco, por instancia:** marcador de ejecución `.glitch_pi_executed_mes.json` y spool `.glitch_pi_unsynced_log_mes.jsonl` bajo `GLITCH_PI_STATE_DIR` (o `~`), `:232–275, :901`.
- **Cuenta fija (A5):** `_resolve_account_id()` exige `TOPSTEP_ACCOUNT_ID`, la valida contra las cuentas activas y contra `TOPSTEP_ACCOUNT_DENY` (`:298–334`).
- **El scheduler de Railway** escribe la señal una sola vez al día y **se niega si ya hay una sin consumir** (`geometry_scheduler.py:631–655`); el número de intento y el avance del Combine se derivan de **un solo historial** (`_current_intento`, `_attempt_pnl`, `_check_attempt_reset`, `:187–300`).
- **Telegram:** el prefijo es solo el producto (`PREFIX`, `:163`); `_notify_blocked_once_per_day` deduplica por texto en un archivo compartido del Gist (`:394–408`).

### 3.2 Opción evaluada: dos instancias, cada una con su `TOPSTEP_ACCOUNT_ID` y su `GLITCH_PI_STATE_DIR`
Lo que **sí** queda aislado: el marcador y el spool locales (por directorio), la cuenta fijada (A5), el flatten de las 14:30 CT y el tope de contratos (cada instancia cierra su propia cuenta con `close_contract(account_id, …)`). Lo que **se rompe**:
| # | Qué | Por qué | Gravedad |
|---|---|---|---|
| R1 | **Estado de recuperación compartido** (`pi_position_mes.json`) | `reconcile_if_needed()` es lo primero de cada ciclo (`:814, :1083`) y usa `state["account_id"]`: la instancia ociosa ve el bracket abierto de la otra y **lo adopta**: vigila sus órdenes durante horas, cierra su historial y limpia la señal y el estado; la propia cuenta no opera ese día. Además `save_pi_state({})` de la que termina primero borra el estado de la otra. | Crítica |
| R2 | **Limpieza de la señal** (`save_order_signal({})`) | Cualquier salida temprana de una instancia (señal inválida, tardía, "ya reclamada", bracket fallido, fill no confirmado, `_finalize_cycle`) borra la señal para la otra; si esta aún no la había leído (ventana ≤120 s), esa cuenta no opera sin aviso. | Alta |
| R3 | **Historial compartido** (`geometry_mes_log.json`) | Lectura-modificación-escritura sin bloqueo: dos cierres cercanos pierden una entrada (gana la última escritura). La deduplicación (`_entry_present`, llaves date/result/entry/exit/intento/nc/side) **descarta como duplicada** la segunda cuenta si ambas rellenan igual. Si se escriben las dos, el scheduler suma ambos P&L al mismo intento (`_attempt_pnl`) y adelanta pases o quiebres. Las entradas no llevan cuenta. | Alta |
| R4 | **Marcador si no se fija el directorio** | Con el default `~` las dos instancias comparten `.glitch_pi_executed_mes.json`: la segunda ve la señal "ya ejecutada" y no opera (falla segura, pero silenciosa). | Media |
| R5 | **Telegram** | Mensajes idénticos ("S10GLITCH - PI EXECUTOR - MES") sin indicar cuenta; el aviso diario compartido puede **suprimir** un aviso crítico de B porque coincide con el de A, y se escribe sin control de concurrencia. | Alta |
| R6 | **A5 con reinicios frecuentes** | El pipeline implica ~30–40 reinicios por cuenta y año (§2). Si cada reinicio crea una cuenta nueva con otro `accountId` (así lo registra el log del 3-oct), el ID fijo exige editar el entorno decenas de veces por cuenta: operativamente inviable. Por verificar con una compra real. La lista de denegación por defecto (`28197705`) también habría que vaciarla para operar Combines, perdiendo la protección. | Alta |
| R7 | **Señal única, estado distinto por cuenta** | `intento` y `nc` salen de un solo historial; si una cuenta pasa a XFA (otro producto: MGC) o se reinicia en otro momento, la señal ya no describe a la otra cuenta. | Media |
| R8 | **Sesión de API** | Dos procesos con la misma llave se autentican por separado; no sé si un login invalida el JWT del otro (hay que probarlo). El artículo oficial de la API dice que una suscripción y una llave cubren todas las cuentas elegibles, que se indica el `accountId` en cada orden y que toda la actividad debe originarse en un dispositivo personal (el Pi en casa cumple). | Por probar |
| R9 | **Operación** | La plantilla de systemd y `install_service.sh` crean una sola unidad; el watchdog vigila un solo log (`--log-file`). | Baja |

### 3.3 Mínima modificación segura (propuesta; requiere revisión humana y auditoría nueva por tocar lógica de capital)
Principio: **ningún archivo mutable compartido entre cuentas.**
1. **Etiqueta de cuenta obligatoria** `GLITCH_PI_ACCOUNT_LABEL` (p. ej. `A`, `B`) que se agrega al nombre de: archivo de señal (`orden_pendiente_mes_A.json`), estado (`pi_position_mes_A.json`), aviso (`pi_block_notice_mes_A.json`), historial real (`geometry_mes_A_log.json`), marcador y spool. Arranque con error si falta, o si dos instancias comparten etiqueta (candado de archivo en `GLITCH_PI_STATE_DIR`).
2. **Fan-out de la señal en el origen:** el scheduler escribe **un archivo por etiqueta** (lista en una variable de entorno) y bloquea solo si alguno sigue sin consumir; cada instancia lee y limpia únicamente el suyo. Esto elimina R2 y R1 de raíz. El historial de papel que usa el scheduler para `intento` sigue siendo uno; se toma la cuenta A como líder.
3. **Verificación previa de la propia cuenta:** antes de entrar, comprobar que la cuenta está activa y en el estado esperado (no operar si fue liquidada o reiniciada; sin esto, A y B divergen).
4. **Telegram con la etiqueta en el prefijo** y avisos diarios por cuenta (archivo de aviso propio).
5. **A5 como lista permitida por etiqueta** (no solo denegada) con exclusión mutua entre etiquetas, y resolución de la cuenta tras un reinicio **por regla verificable** (p. ej. nombre/tamaño y estado) con paso humano de aprobación; hay que definir qué pasa con los ~30–40 reinicios anuales antes de escalar.
6. **Operación:** unidad de systemd con plantilla (`glitch-pi-executor@A`, `@B`), un `EnvironmentFile`, un log y un watchdog por instancia.

### 3.4 Pruebas necesarias (todas sandbox/Practice salvo las marcadas)
1. Fan-out: un día con dos etiquetas, cada instancia opera una vez; el scheduler no escribe si queda una señal sin consumir.
2. Aislamiento: la instancia A aborta temprano y B sigue; B ociosa no adopta el bracket de A; el cierre de A no borra el estado de B.
3. Concurrencia del historial: dos cierres simultáneos conservan las dos entradas, cada una con su cuenta; sin choque de deduplicación.
4. Marcadores: el reclamo de A no bloquea a B; dos instancias con la misma etiqueta no arrancan.
5. Telegram: mensajes con etiqueta; un aviso de A no suprime uno de B.
6. A5: una cuenta de otra etiqueta o no permitida se rechaza; reinicio de una cuenta con ID nuevo según la regla definida.
7. Aplanado de las 14:30 CT: cada cuenta cierra la suya; el fallo de una no frena a la otra.
8. Fallas inyectadas: Gist caído, `get_open_orders` con error, fill parcial, corte de red a media posición, en cada cuenta por separado y a la vez.
9. **Con la plataforma real:** sesiones simultáneas con la misma llave (¿se invalidan los tokens?), límites de tasa, y comportamiento tras un reinicio (¿nuevo `accountId`?). La Practice solo admite 1 cuenta y el Trade Copier no la admite, así que esto requiere al menos **dos Combines pagados** (≥ $98).

### 3.5 Comparación con el Trade Copier oficial de Topstep (help.topstep.com, TopstepX, leído hoy)
Lo oficial: copia de una cuenta Líder a una o más Seguidoras; solo Combine y XFA (no Practice ni Live); el Líder debe tener el menor tamaño máximo de posición; las ejecuciones se reflejan pero "exact fill price and timing may vary"; una Seguidora conectada **no se puede operar directamente**; si el Líder toca el DLL o se auto-liquida, las Seguidoras se aplanan y no se copia hasta que el Líder pueda operar; si el Líder rompe el MLL, hay que desvincular las Seguidoras; apagar el copiador a media operación aplana las Seguidoras; **al solicitar un pago las Seguidoras se desvinculan solas**; con niveles de escalado distintos el copiador puede desconectarse al inicio del día; las Seguidoras no tienen límites de contratos ni bloqueos de símbolo. El artículo de la API no dice si el copiador replica órdenes enviadas por API.
| | Dos instancias del ejecutor | Trade Copier de Topstep |
|---|---|---|
| Cambios de código | Sí (§3.3), revisión humana y auditoría nueva | Ninguno en el Pi (solo el Líder) |
| Protección de la Seguidora | TP/SL propios en cada cuenta | Dependen de que el copiador replique; la Seguidora no se puede gestionar directamente |
| Reinicios (~30–40 al año por cuenta) | El ejecutor debe adaptarse al ID nuevo | El vínculo se rehace a mano en la interfaz tras cada reinicio o cuenta nueva; desvinculación automática en cada payout |
| Pruebas sin dinero | Posibles con simuladores y mocks; la parte real requiere 2 Combines | **No hay prueba sin dinero:** la Practice no admite copiador |
| Incertidumbres | Sesiones simultáneas de API (R8) | Compatibilidad con órdenes de API; fills y tiempos distintos; discrepancias de escalado |
| Riesgo de conducta (RTP) | Igual en ambas: cuentas correlacionadas que tocan el MLL el mismo día | Igual (la propia documentación advierte sobre coberturas) |
**Recomendación de diseño:** si Topstep confirma por escrito que dos cuentas con las mismas señales son aceptables (mi pendiente principal), la ruta menos arriesgada es **dos instancias con la señal en abanico y todo con etiqueta** (control total sobre cada cuenta y los reinicios), no el copiador, porque este se rehace a mano en cada reinicio y no se puede probar sin gastar. Pero con la advertencia del RTP y con el nivel real de ganancia de §1.1, **no construiría nada de esto antes de resolver la pregunta de conducta y de decidir si el número realista (~$3.3k con 2 cuentas, hasta ~$6.5k si el régimen de oro se repite) justifica el trabajo.**

## 4. Decisiones y pendientes
1. **Aprobar TP 32** (no 31): mejora probada, sin cambio operativo.
2. **Reevaluar tu umbral con el rango real:** 2 cuentas ≈ $3.3k–$7.8k al año (según la dependencia de la ventana de oro), con 18–36% de terminar en pérdida y un colchón de ~$6.7k.
3. **Preguntar a Topstep por escrito:** ¿dos cuentas con las mismas señales y ~40 reinicios al año por cuenta son aceptables dentro del RTP? ¿Cada reinicio crea un `accountId` nuevo? ¿El copiador replica órdenes de API?
4. **Cuantificar el RTP:** modelar la consistencia de 40% de la XFA (reduce los payouts) y el DLL automático en todo el pipeline.
