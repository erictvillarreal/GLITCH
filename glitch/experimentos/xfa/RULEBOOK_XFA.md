# RULEBOOK_XFA — Express Funded Account 50K (Topstep) — leído el 20-oct-2026

**Método y límite de este documento.** Cada regla se leyó directamente en el Help Center oficial (`help.topstep.com/en/articles/<id>`; el sitemap oficial da la fecha de última modificación de cada artículo). El tamaño de la cuenta es 50K y el producto de Cerebro 2 es MGC. **No incluyo citas textuales largas** (el contenido es de Topstep y no lo reproduzco): cada regla va **parafraseada, con artículo, sección y fecha**, y el estado es VERIFICADO / AMBIGUO / DESCONOCIDO. Quien necesite el texto exacto para un ticket puede abrir la URL indicada. Los artículos usados (id · modificado según sitemap): XFA Parameters `8284215` (5-ago-2026) · XFA Activation `8284217` (24-sep) · MLL `8284204` (18-sep) · Consistency `8284208` (17-sep) · Scaling Plan `8284223` (16-jul) · Payout Policy `8284233` (13-oct) · DLL `10490293` (30-jun) · Risk Adjustments `13613539` (**19-oct**) · Holiday Hours `13350348` (18-sep) · Economic Releases `8284211` (15-oct) · Hours/Products `8284206` (13-jul) · Pricing `14289835` (15-oct) · Subscriptions `8284121` (12-oct) · Reset `8284128` (25-sep) · Combine Parameters `8284197` (24-sep) · Back2Funded `12060405` (29-sep) · RTP `13620045` (15-oct) · Prohibited Conduct `10296582` (30-sep) · Prohibited Strategies `10305426` (10-jun) · API Access `11187768` (17-sep) · Eligibility `8284116` (4-sep) · Tax `8284238` (29-may). La tabla del Plan de Escalado es una **imagen**: la leí en pantalla (20-oct).

Leyenda: **V** = VERIFICADO (texto oficial explícito) · **A** = AMBIGUO (el texto admite dos lecturas o dos artículos no coinciden) · **D** = DESCONOCIDO (no está publicado). Los **escenarios** (A1/A2/…) son las lecturas con las que el motor modela mientras no haya respuesta (ver `PREGUNTAS_TOPSTEP.md`).

---

## 1. Parámetros de la XFA 50K

| # | Regla | Estado | Fuente |
|---|---|---|---|
| 1.1 | El balance de la XFA **empieza en $0**; los $50,000 son poder de compra, no saldo. El balance del Combine no se transfiere. | **V** | 8284215; 8284217 |
| 1.2 | Hasta **5 XFA activas** a la vez; si se pasa un Combine estando en el límite, la XFA nueva queda en espera. Se puede mezclar Standard y Consistency (salvo plan FTP). | **V** | 8284215 |
| 1.3 | **MLL 50K = $2,000.** En la XFA arranca en **−$2,000** (relativo al balance $0) y **sube** con el balance de **cierre del día**, nunca baja; cuando el balance llega a **+$2,000** el MLL se **fija en $0 para siempre**. Se **monitorea en tiempo real** con P&L realizado **y no realizado**; al tocarlo la cuenta se liquida de inmediato con órdenes de mercado y el slippage de la salida no lo deshace. Al liquidarse, **la XFA se cierra para siempre** (se “cierra al final del día”) salvo Back2Funded. | **V** | 8284204; 8284215 |
| 1.4 | **Tras el primer pago** el MLL se fija en **$0** sin importar dónde estaba; el balance restante pasa a ser el piso efectivo. Si ya estaba en $0, se queda. | **V** | 8284204; 8284233 |
| 1.5 | **DLL**: opcional ($1,000 en 50K). Si se elige **al activar** (o al comprar el Combine) queda **fijo**. Tocarlo **no es violación**: liquida y bloquea hasta las 5 PM CT siguientes. Elegirlo duplica el tope por pago (oferta “temporal”, sin fecha de fin publicada). | **V** (regla) · **A** (vigencia de la oferta) | 10490293; 8284233 |
| 1.6 | **Plan de escalado XFA 50K** (lotes = minis; micros ×10): saldo **< $1,500 → 2 lotes (20 micros)**; **$1,500–$2,000 → 3 (30)**; **> $2,000 → 5 (50)**. El máximo **no sube a mitad de sesión**; excederlo > 10 s puede ser revisado. Un pago que baja el saldo a un tramo inferior baja el máximo. | **V** | 8284223 (imagen); 8284233 |
| 1.7 | **Productos “restringidos” (temporal, modificado 19-oct):** MGC y MCL en XFA 50K tienen tope de **30 micros** como máximo, y por saldo el plan es **12 micros (< $1,500) / 18 ($1,500) / 31 (≥ $2,000)**. Con nc = 3 micros de MGC **no limita**. | **V** (vigente hoy; Topstep puede cambiarlo) | 13613539 |
| 1.8 | **Noticias Tier 1** (CPI, NFP, PPI 7:25–7:35 CT; FOMC 12:55–1:05 y 1:25–1:35 CT): no se pueden **abrir** posiciones nuevas en minis; en micros hay un tope de aperturas. **XFA 50K: 1 micro con saldo < $2,000 y 3 micros con saldo > $2,000 (MGC incluido).** Las posiciones ya abiertas antes de la ventana se pueden mantener; los TP/SL que **reducen** posición se aceptan. La entrada de Cerebro 2 es 7:13 CT: **cae antes** de la ventana de 7:25 en días CPI/NFP/PPI. | **V** | 13613539 |
| 1.9 | **Horario:** el día de trading va de 5:00 PM CT a **3:10 PM CT**; todo debe estar plano a las 3:10 PM. **Feriados/cierres anticipados:** hay que cerrar **15 min antes** del cierre; posiciones abiertas se liquidan. 2026: **26-nov 11:45 CT, 27-nov 12:00 CT, 24-dic 12:00 CT**; 25-dic y 1-ene cerrado. **No hay pagos durante horas de feriado.** El flatten del Pi es fijo a 14:30 CT → **viola** esos días (hueco ya conocido). | **V** | 8284206; 13350348 |
| 1.10 | Inactividad: una XFA sin operar > 30 días **puede cerrarse**. No se puede poner en pausa. | **V** | 8284215 |
| 1.11 | Las XFA no pagan mensualidad. No hay límite de tiempo. No hay profit target. | **V** | 8284215 |
| 1.12 | Tamaño y camino (**Standard / Consistency**) se eligen **una vez, al activar**, y no se pueden cambiar. | **V** | 8284215; 8284217 |
| 1.13 | Slippage: Topstep no ajusta cuentas por slippage; los stops son órdenes de mercado. | **V** | 8284211; 8284204 |

## 2. Elegibilidad y cálculo del pago (Standard)

| # | Regla | Estado | Fuente |
|---|---|---|---|
| 2.1 | Ruta **Standard**: **5 días ganadores de ≥ $150 de P&L neto**, **no consecutivos**; el día se “cierra” a las 4:00 PM CT; el **día en que se solicita el pago no cuenta** para el siguiente ciclo; tras cada pago el contador **vuelve a 0**. | **V** | 8284233 |
| 2.2 | “P&L neto” incluye comisiones y cargos (se descuentan del balance con cada fill y aparecen en el Net P&L). Por tanto un “día de $150” es **neto de comisión**. | **V** (por dos artículos que se complementan) | 14289835 + 8284233 |
| 2.3 | Además, desde el 2º pago hace falta **ganancia neta ≥ $0.01 desde el último pago**; el **primero está exento**. | **V** | 8284233 |
| 2.4 | **Monto**: hasta el **50 % del saldo** con tope **$2,000 por solicitud en 50K Standard** ($3,000 en Consistency). Con DLL comprado (oferta temporal): $4,000 / $6,000. (La tabla comparativa de `8284215` dice “hasta $5,000/$6,000”: es el tope **más alto entre tamaños**; el de 50K es el de la tabla de `8284233`.) | **V** | 8284233; 8284215 |
| 2.5 | **Mínimo por pago: $125.** | **V** | 8284233 |
| 2.6 | **Saldo mínimo para retirar:** no se publica un saldo mínimo aparte; implícitamente el 50 % del saldo debe ser ≥ $125 (saldo ≥ $250). El `run_glitch_xfa.py` viejo usaba 55,000 (balance de cuenta de $50k + $5k): **no corresponde** a la XFA actual (balance arranca en $0). | **A** (¿hay mínimo implícito mayor?) → pregunta 4 | 8284233 |
| 2.6b | Recomendación (no regla): empezar a cobrar cuando el MLL ya está en $0. | informativa | 8284233 |
| 2.7 | **Reparto 90/10.** **Primeros $10,000 de ganancia de por vida al 100 %** solo para quien entró al **dashboard nuevo antes del 12-ene-2026** (pagos del dashboard “Legacy” no cuentan). **Elegibilidad de Eric: NO VERIFICADA.** | **V** (regla) · **D** (si Eric califica) | 8284233 |
| 2.8 | **Frecuencia:** se puede solicitar cada vez que se cumplan los requisitos (no hay límite diario/semanal explícito). Cada XFA tiene su política **independiente**. | **A** (no hay tope de frecuencia explícito) | 8284233 |
| 2.9 | **Solicitar un pago deduce el monto de inmediato** del balance y se puede seguir operando; si luego se toca el MLL, el pago ya deducido **no se pierde**. Aprobación interna 1–3 días hábiles. | **V** | 8284233 |
| 2.10 | **Métodos y comisiones de pago:** ACH (solo bancos de EE. UU., $30), **Wire/SWIFT internacional $30, 5–10 días**; Aeropay (solo EE. UU.), Wise (**solo China, Canadá y Reino Unido**), prop-to-brokerage (solo EE. UU.). **Solo a una cuenta bancaria a nombre del trader.** Para un trader fuera de esos países la opción práctica es **wire con $30 por pago** (a un pago de $125 le queda $82.5). | **V** (la elegibilidad de Eric por país es **D**) | 8284233 |
| 2.11 | El día de un pago se bloquea por DLL **no** impide pedirlo después de que levante; los lock-outs personales igual. | **V** | 8284233 |
| 2.12 | Hay un desajuste entre artículos: el pago dice que el día se cierra a las **4:00 PM CT**; el artículo de consistencia del Combine dice **3:10 PM CT**; el día de trading termina 3:10 PM. | **A** (impacto bajo) → pregunta 9 | 8284233; 8284208 |

## 3. Consistencia

| # | Regla | Estado | Fuente |
|---|---|---|---|
| 3.1 | **La ruta Standard de la XFA no tiene consistencia.** La consistencia del 40 % existe **solo** en la ruta **Consistency** de la XFA. | **V** | 8284215 |
| 3.2 | Consistency: pago con **3 días operados** (≥ 1 trade por día) **y** consistencia **≤ 40 %**, definida como (mayor día ganador) ÷ (ganancia neta total). “No se redondea.” Si se supera, se sigue operando hasta que el porcentaje baje; **no hay castigo**. Tope por pago 50K: $3,000. | **V** | 8284215; 8284208; 8284233 |
| 3.3 | La ganancia neta total y el mayor día se miden **dentro de la ventana desde el último pago** (se reinician en cada pago; las ganancias previas quedan en el saldo pero no cuentan). El día del pago no cuenta. | **V** | 8284208; 8284215 |
| 3.4 | Consecuencia aritmética para Cerebro 2 (1 TP ≈ $1,092 bruto con 3 micros × 364 ticks): con **un solo** día grande la consistencia es 100 %; **dos** TP de $1,092 dan 50 % (no elegible); **tres** dan 33 %. Solo aplica si la cuenta es **Consistency** (o el RTP la impone). | derivado de **V** | — |
| 3.5 | **Combine:** mejor día ≤ 55 % de la ganancia total; si se excede, el objetivo sube a (mejor día)/0.55; los días perdedores no reinician el mejor día; para resolverlo hay que ganar el resto en **otro** día. Con TP 32 y nc ≤ 40 no liga. | **V** | 8284208; 8284197 |

## 4. Estado tras un retiro

| # | Regla | Estado | Fuente |
|---|---|---|---|
| 4.1 | Balance baja en el monto retirado (bruto, antes del 10 %). | **V** | 8284233; 8284204 |
| 4.2 | **MLL = $0** de forma permanente; el **balance restante es el piso efectivo** (la distancia a la liquidación = el saldo). Con el pago máximo (50 % o el tope) el saldo restante es ≥ 50 % del anterior. | **V** | 8284204; 8284233 |
| 4.3 | Contador de días ganadores = 0; consistencia = 0; el día del pago no cuenta. | **V** | 8284233; 8284208 |
| 4.4 | Si el pago baja el saldo a un tramo inferior del Plan de Escalado, baja el máximo de contratos. | **V** | 8284233 |
| 4.5 | Las ganancias del ciclo anterior **permanecen** en el saldo pero no cuentan para la consistencia nueva; para el **2º pago en adelante** se exige ganancia neta ≥ $0.01 desde el último. | **V** | 8284233; 8284208 |
| 4.6 | **Saldo y piso a la vez:** tras el primer pago el piso es $0, así que desde ese momento **un stop de SL=$1,092 con saldo restante < $1,092 puede liquidar antes del SL** (esto ya está modelado en el log del 24-sep). | derivado de **V** | — |

## 5. Transición Combine → XFA

| # | Regla | Estado | Fuente |
|---|---|---|---|
| 5.1 | Al **pasar**, el Combine **se cierra** y su suscripción **se cancela sola**; el estado “Passed” puede tardar hasta 30 min en verse y el Combine pasado **sigue en “Passed” hasta que se activa** la XFA (no se pierde). Los otros Combines activos **siguen cobrando** hasta cancelarlos a mano. | **V** | 8284197; 8284121; 8284217 |
| 5.2 | Activación **manual** desde el Trade Report (“Start/Activate Express Funded Account”): elegir tipo (Standard/Consistency), firmar el acuerdo, **pagar $149** (ruta Standard; $0 en la ruta “No Activation Fee”, cuyo Combine cuesta $95/mes), y opcionalmente DLL. La XFA queda lista **en minutos**; si se pasa un viernes, **no opera hasta el domingo 5 PM CT**. Hay que confirmar la cuenta correcta (sin reembolsos). | **V** | 8284217; 14289835 |
| 5.3 | ¿La XFA nueva crea **otro `accountId`**? El artículo no lo dice; es la cuenta nueva con su propio balance $0 y el Combine se cierra. | **D** (casi seguro sí) → pregunta 5 | — |
| 5.4 | ¿Se puede operar **el mismo día** de la activación? “Minutos después del pago”, sujeto a que el mercado esté abierto. | **A** | 8284215; 8284217 |
| 5.5 | **Costos de reponer:** Combine 50K $49/mes; **Reset $49**, 2 por cuenta por día, sin límite de compras de Combines; cada rebill suma 1 crédito de reset; **Back2Funded (reactivar una XFA liquidada antes del primer pago): $599** (50K), hasta 2 veces, ventana de 30 días, se reinicia todo en cero. Ni el motor ni los reportes previos modelan Back2Funded: reponer vía Combine nuevo cuesta $49/P(pase)+$149 (≈ $300–440), **menos** que $599. | **V** | 14289835; 8284128; 12060405 |

## 6. RTP y conducta

| # | Regla | Estado | Fuente |
|---|---|---|---|
| 6.1 | **Públicos como motivos de RTP:** varias cuentas tocando el MLL el mismo día; operar el tamaño máximo en la mayoría de los trades; no mantener perdedores menores que ganadores; no usar stops; operar a tope o por tilt/FOMO; no respetar límites diarios. **Sin umbrales numéricos.** | **V** (lista) · **D** (umbrales) | 13620045 |
| 6.2 | **Consecuencias del RTP:** DLL automático en Combines y XFA nuevos ($1,000 en 50K); si se pasa un Combine, solo XFA **Consistency**; XFA Standard no disponible hasta salir del RTP; un Combine reseteado bajo RTP es un “Consistency Trading Combine” con DLL (sus reglas **no** están publicadas); las XFA Standard existentes no cambian; XFA nuevas creadas durante el RTP son solo Consistency. | **V** · reglas del Combine Consistency: **D** | 13620045 |
| 6.3 | **Conducta prohibida (respuestas posibles: advertencia, borrar el día, reset, cierre permanente, o “retraso o negación de un pago”).** Incluye: compras excesivas de Combines o Resets; apilamiento de cuentas (pegar al MLL y pasar a otra); trading incoherente con el mercado real; “cualquier otra conducta” a discreción de Topstep. | **V** · umbral de “excesivo” **D** | 10296582 |
| 6.4 | **Estrategias prohibidas** (extracto): account stacking; abrir **el tamaño máximo directamente en un evento de noticias importante**; explotar el simulador (algoritmos de scalping para fills irreales, **brackets muy ajustados o auto-breakeven** para aprovechar fills favorables, stops “imposibles”). Los brackets de 364 ticks no son ajustados; los de 32 ticks de Cerebro 1 son un tema a preguntar. | **V** (lista) · aplicabilidad **A** | 10305426 |
| 6.5 | Patrones de **nuestra** operación que tocan esos criterios (no es un veredicto): ~44–53 compras de Combine por año por cuenta; SL de 100 ticks vs TP de 32 en Cerebro 1 (perdedor ≈ 3× ganador); nc = 40 de 50 micros (80 % del máximo) en Cerebro 1; Cerebro 2 usa **3 de 31** micros (~10 %) y SL = TP. | informativo | log; 13620045; 10296582 |

## 7. Automatización, API, cuentas

| # | Regla | Estado | Fuente |
|---|---|---|---|
| 7.1 | **Automatización en Combine y XFA: permitida con condiciones** (Topstep no ayuda a montarla ni cubre fallas; probar en Practice; no HFT). La API de TopstepX/ProjectX permite bots propios sujetos a las reglas estándar y a la prohibición de HFT. **La Live Funded Account no puede usar la API.** | **V** | 8284215; 11187768 |
| 7.2 | **Toda la actividad de órdenes debe salir de un dispositivo personal**: VPS, VPN y servidores remotos están prohibidos para transmitir órdenes (un servidor puede observar y registrar). Consistente con Pi (órdenes) + Railway (solo señales). | **V** | 11187768; 10296582 |
| 7.3 | API: $29/mes ($14.50 con código `topstep`); sin sandbox (usar Practice); las órdenes por API son definitivas. Una suscripción y una llave cubren todas las cuentas elegibles del perfil. | **V** | 11187768 |
| 7.4 | **Un solo perfil** por persona (Combines, XFA y LFA bajo el mismo perfil); el titular debe ser el **nombre legal individual** (excepciones: LLC unipersonal de EE. UU. para pagos/impuestos). El nombre que aparece en el dashboard (“Javier Lozano” según el encargo) vs. el operador real **debe ser la misma persona**; pagos solo a cuenta bancaria a nombre propio. **NO VERIFICADO** por mí: lo debe confirmar Eric. | **V** (regla) · **D** (caso de Eric) | 8284197; 8284238; 8284233 |
| 7.5 | Copiador de trades oficial: hasta $750K de poder de compra en XFA; se deshabilita durante un pago y hay que reactivarlo. **Cobertura entre cuentas y trading coordinado con otras personas están prohibidos.** | **V** | 8284215; 8284233; 10296582 |
| 7.6 | **Países:** México no aparece ni en la lista de inelegibles ni en la de “solo XFA”. Residencia/ciudadanía de Eric **no verificadas** por mí. | **V** (listas) · **D** (caso de Eric) | 8284116 |

## 8. Fiscal (solo compuerta, sin modelar)

Topstep no da asesoría fiscal. No-estadounidenses firman **W-8BEN**; EE. UU. **W-9** y reciben 1099-NEC por el monto **bruto** del pago antes de comisiones de pago. Las cuentas deben estar a nombre individual (no empresas C/S-corp ni LLC multimiembro). **No hay payout real sin contador y sin definir a nombre de quién** (ver §16 del doc del 26-sep). Fuente: 8284238; 8284233.

## 9. Resumen de lo que NO está publicado (alimenta `PREGUNTAS_TOPSTEP.md`)

(a) umbrales del RTP y de “compras excesivas”; (b) reglas del Consistency Trading Combine; (c) si hay un saldo mínimo implícito para retirar y si hay tope de frecuencia; (d) si la XFA nueva tiene otro `accountId` y si opera el mismo día; (e) elegibilidad de Eric para los $10k al 100 %; (f) vigencia de la oferta del DLL con tope doble; (g) si un día “ganador” se mide neto de comisión (casi seguro sí) y a qué hora cierra el día (3:10 vs 4:00 PM CT); (h) si un día de pagos duplicado (dos pagos el mismo día) es posible; (i) si 364 ticks de bracket con 3 micros y MLL = piso de $0 entra en “brackets ajustados/explotación del simulador” (no) y si el SL de 100 ticks de Cerebro 1 sí.
