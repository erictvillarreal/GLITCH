# Mapa de firmas de futuros + modelo de los retos de Topstep Labs
*Rama `research/firm-map-and-labs` (sandbox, sin producción; parte de `research/t1-combine-size` porque el motor vive ahí). 13-oct-2026. Motor `dd_cash/lever_engine.py` (ahora con piso del MLL estático) y convención de `structural-levers`. Archivos: `scripts/firm_map.py` + `dd_cash/firm_map_2026-10-13.csv` + `tests/test_firm_map.py` (mapa); `scripts/labs_challenges.py` + `dd_cash/labs_challenges_report.txt` (Labs).*

## Resumen (10 líneas)
1. **No, no estábamos seguros ni teníamos todo mapeado.** Con tus dos directorios, el universo que pude armar es de **36 firmas de futuros** (antes solo 4 tenían algún grado de verificación). Los directorios solo dan nombres, planes, plataformas y splits; **ninguno trae reglas de automatización**. Qué tan sólido es cada dato: **3 firmas leídas directamente** (Topstep, Bulenox, Apex), **7 por resúmenes de páginas oficiales**, **20 solo por terceros** (blogs y vendedores de herramientas con interés comercial) y **6 sin nada**.
2. **Solo 8 de las 36 aparentan permitir bots propios con condiciones** (Topstep, Bulenox, Tradeify, MFFU, FundedNext Futures, FFN, DayTraders, FTMO Futures) y **solo 5 de esas** con texto de fuente propia; 6 prohíben (Apex, Alpha, FuturesElite, Funded Futures Family, E8 Futures, Leeloo), 6 son solo manual/semi, 3 se contradicen (Lucid, Goat, Earn2Trade) y 13 son desconocidas.
3. **Apex sigue descartada para automatizar**: su página oficial "Prohibited Activities" dice textualmente "No Automation or Algorithm Usage allowed". El artículo que pegaste ("Tradovate API Request Limit") habla del límite de solicitudes de Tradovate (loguearte, abrir módulos, colocar o cancelar órdenes a mano cuentan como "solicitudes"): **no autoriza bots**. La misma página prohíbe además el "Stockpiling Evaluation Accounts" (comprar evaluaciones baratas para ciclar/quebrarlas buscando un golpe de suerte).
4. **Nuestro modelo de negocio (ciclar evaluaciones) es el patrón que varias firmas nombran como prohibido** (Apex "stockpiling"; Alpha "apilar evaluaciones"; FuturesElite; Topstep "compras excesivas"). En cualquier firma el volumen de intentos (~54 al año por cuenta) es el principal riesgo de conducta, no la tecnología.
5. **La infraestructura es otra barrera**: ProjectX anunció en nov-2025 el fin de su servicio a firmas de terceros (efectivo 28-feb-2026 según una firma) y solo queda Topstep. Nuestro ejecutor del Pi es ProjectX; en cualquier otra firma haría falta un adaptador nuevo (Rithmic, Tradovate o NinjaTrader), con costos y reglas de acceso **NO VERIFICADOS**.
6. **Economía parecida en todas**: costo esperado por cuenta fondeada $240–$450 (Topstep $299, FFN $239–$292, Tradeify $301, Bulenox $440) y el valor máximo de una cuenta fondeada es similar (≈ 80–90% de un colchón de $2,000–$2,500). **Ninguna firma cambia el orden de magnitud**; sumar firmas solo sirve para subir el número de cuentas (cada firma tiene su propio tope) y diversificar, a costa de un adaptador por firma.
7. **Labs: hoy no se puede comprar nada.** topstep.com/labs (leída 13-oct) pone los 7 "drops" bajo "Past Lab Drops" y solo ofrece avisar del siguiente. Lo que sigue es para evaluar el próximo.
8. **Los retos de dos rondas (#003, #004, #005, #007) tienen valor esperado positivo en el modelo**: probabilidad por ronda 24–26% (teoría 25%), 6–7% las dos rondas; #003 ($49 → $3,000): **+$123 a +$155 por compra**; #005 ($149 → $6,000): **+$186 a +$227**; #004 ($39 → $1,500): +$42 a +$55. Las rondas se resuelven en ~1.4 días.
9. **Escala (solo si reaparece un reto sin tope de compra, como #003 decía en agosto)**: 100 retos #003 costarían $4,900 y darían un neto medio de **+$13.5k a +$15.2k**, con P(pérdida) ≈ 1%. Eso es lo más parecido a "usar el exponente" que encontré, **pero hoy no existe, la mayoría de los retos tiene tope de 5, y es un modelo no verificado en vivo** (reglas de paso intradía/cierre, comisiones y revisión de conducta).
10. **La Combine estática de $50K (#006) no es palanca**: pase 12–25% (DLL obligatorio de $1,000 y consistencia 55%) y EV por compra de **−$76 a +$24**.

## 1. Mapa de firmas
### 1.1 De dónde sale el universo (y por qué no es exhaustivo)
| Fuente | Qué trae | Límite |
|---|---|---|
| QuantVPS "List of Futures Prop Firms (2026): All 24 Compared" | 24 firmas, precios de lista (10-oct-2026), splits, drawdown, plataformas | sin dominios ni políticas de automatización; sitio de un vendedor de VPS |
| Prop Firm Match, directorio de futuros (leído en el navegador; el fetch daba 403) | 25 firmas (la lista cargada no se expandió con "Ver todo") con reseñas, años, activos, plataformas, descuentos | afiliados con códigos de descuento; no trae reglas |
| Track360 "Prop Trading Firms Directory 2026" | 63 entradas, 15 de futuros | solo nombre, modelo, plataformas, split |
| Resultados de búsqueda | Leeloo, Hyperticks, Tick Tock Trader, FuturesElite… | — |
**Unión: 36 firmas de futuros** (sin contar Trade The Pool, que es de acciones). Prop Firm Match tiene además una sección "Empresas no listadas" que no revisé: **el universo real puede ser mayor**.
### 1.2 Estado por firma (datos completos en `dd_cash/firm_map_2026-10-13.csv`)
| Automatización | Firmas | Qué respalda la clasificación |
|---|---|---|
| **Bots propios permitidos con condiciones** | Topstep ✔directa, Bulenox ✔directa, Tradeify (oficial, resumen), MyFundedFutures (oficial, resumen), FundedNext Futures (terceros), FFN (oficial, resumen), DayTraders (terceros), FTMO Futures (terceros) | condiciones típicas: sin HFT, probar propiedad del código (Tradeify), ≥50% del beneficio de trades >10 s (Tradeify), "a discreción" (FFN), aprobación para algoritmos de terceros (Bulenox) |
| **Contradictoria** | Lucid (ayuda: sí; LucidDirect Agreement: requiere aprobación escrita), Goat Funded Futures, Earn2Trade | pedir respuesta escrita |
| **Prohibida** | Apex ✔directa, Alpha (oficial, resumen), FuturesElite, Funded Futures Family, E8 Futures, Leeloo | — |
| **Solo manual / semiautomático** | TradeDay, Phidias, Elite Trader Funding, Top One Futures, Blue Guardian Futures, AquaFutures | un bot que solo coloca una orden al día **podría** encajar como "semi" si TÚ la confirmas, pero eso no es automatizar |
| **Desconocida** | Take Profit Trader (sin prohibición explícita; copiadores permitidos hasta 5 PRO), BluSky, Purdia, Legends, Traders Launch, NexGen, The Trading Pit, Finotive, The5ers Futures, Blueberry Futures, Ylos, Hyperticks, Tick Tock Trader | sin política clara |
### 1.3 Reglas transversales que importan para nuestro modelo
- **Cobertura entre cuentas prohibida** en casi todas; Lucid la prohíbe incluso **entre firmas**. Copiar entre cuentas **propias** y en la misma dirección suele estar permitido (Tradeify lo dice explícitamente), pero con la misma estrategia en todas las cuentas varias firmas lo revisan "caso por caso" (FTMO Futures, E8, FFN).
- **Topes de cuentas**: Topstep 5 XFA; MFFU 5 sim-fondeadas (25K/50K); Lucid 10 evaluaciones/5 financiadas; TPT 5 PRO; Bulenox 5 Master; FFN copia hasta 5; Tradeify contradictorio (1 vs 5 por hogar); FFF $100k de pagos por usuario.
- **Microscalping / retención mínima** (Tradeify, Lucid, Elite Trader Funding, FFN): una estrategia de un bracket al día no se ve afectada salvo que el stop se dispare en segundos.
- **Reglamentos que cambian y se contradicen** entre páginas de la misma firma (MFFU consistencia 30% vs 50%; Tradeify cuentas; Lucid automatización; FFN precio $89 vs $80/mes).
### 1.4 Economía por cuenta fondeada (50K; solo donde hay cifras; cota superior, no EV)
| Firma | Cuota evaluación | Objetivo / colchón | Techo de pase (D/(D+T)) | Costo esperado por cuenta fondeada |
|---|---|---|---|---|
| Topstep | $49/mes (+$149) | $3,000 / $2,000 | 32.7% (con consistencia y 2 días) | **$299** |
| FFN Standard MAX | $89 único, reinicio $100 | $3,000 / $2,000 | 40% | **$239–$292** (según p entre 40% y 33%) |
| Tradeify Growth | $145, reinicio $95 | $3,000 / $2,000 | 40% | **$301** (log 5-oct) |
| Bulenox Op. 2 | $175, reinicio $78 (+$148) | $3,000 / $2,500 | 45.5% | **$440** (log 5-oct) |
| TPT | ~$170/mes (promos ~$102), activación $130 | $3,000 / $2,000 | 40% | **~$250–$450** (reinicio nuevo desde may-2026: NO VERIFICADO) |
| FundedNext Flex | $134 lista | $2,500 / $1,500 | 37.5% | n/d (sin reinicio) |
| Lucid / MFFU / DayTraders / otras | n/d | $3,000 / $2,000–$2,500 | 40–45% | n/d |
Valor máximo de una cuenta fondeada en juego justo ≈ split × colchón (Topstep: $1,341 con DP; las demás, ≈ $1,600–$2,250 como cota); realizamos ~58% de esa cota con brackets sin lotería. **Conclusión de economía: sin salto de escala; sí hay cuentas más baratas que Topstep (FFN).**
### 1.5 Hallazgos que cambian la decisión de "otras firmas"
1. **El ejecutor es el cuello de botella, no la firma**: fuera de Topstep no hay ProjectX. Rutas posibles: Rithmic (Bulenox: +$100/mes y aprobación), Tradovate (acceso por API para cuentas de prop NO VERIFICADO), NinjaTrader (Windows). Cada una es un adaptador nuevo con su propia validación.
2. **Ciclar evaluaciones está explícitamente mal visto** en Apex, Alpha y FuturesElite y regulado por Topstep ("compras excesivas", RTP). Antes de escalar a otra firma hay que leer su cláusula exacta; un volumen de ~50 intentos al año por cuenta es justo el patrón.
3. **Prioridad si algún día se amplía** (por autorización de bots propios + ruta de API conocida + costo): (1) **Bulenox** (ya diseñado, `bulenox/EXECUTOR_DESIGN.md`), (2) **FFN** (la más barata; automatización "a discreción"; Rithmic), (3) **Tradeify** (bots personales con prueba de propiedad; condiciones de microscalping), (4) **MFFU** y **Lucid** tras respuesta escrita; TPT tras preguntar. Cada una exige una respuesta **por escrito** a: ¿bot propio de un bracket al día?, ¿misma estrategia en varias cuentas propias?, ¿tope de evaluaciones compradas?, ¿ruta de API permitida?

## 2. Topstep Labs
### 2.1 Qué dicen las reglas (help.topstep.com/15520357, leída 13-oct)
| Drop | Precio | Rondas | Objetivo / MLL | Premio | Tope de compra | Contratos |
|---|---|---|---|---|---|---|
| #003 $3K Challenge (ago) | $49 | 2 idénticas | $3,000 / $1,000 estático, sin DLL | $3,000 fijo, una vez (sin 90/10) | **sin tope de compra**; máx. 5 activos en la ronda de pago | 10 micros o 1 mini; MGC/MCL ≤ 6 |
| #004 $1.5K (sep) | $39 | 2 | $1,500 / $500 | $1,500 | 5 por trader; las cerradas cuentan | 2 micros |
| #005 $6K (sep) | $149 | 2 | $6,000 / $2,000 | $6,000 | 5 por trader (10,000 unidades) | 10 micros / 1 mini |
| #007 $1.5K (oct) | **no publicado** | 2 | $1,000 / $500 (premio $1,500) | $1,500 | no leído | 2 minis / 20 micros |
| #006 $50K Static (oct) | $149 | Combine → XFA | $4,000 / $2,000 estático, DLL $1,000, consistencia 55% | XFA con tope de pago $8,000 | 5 por trader | 4 minis / 40 micros |
Comunes: 90 días de vida, cierre por 30 días sin operar, sin reinicios, sin consistencia en los retos. **La página oficial no dice** si el objetivo se evalúa intradía o al cierre, ni si el MLL cuenta el P&L no realizado en tiempo real, ni nada sobre automatización o copiado (NO VERIFICADO).
**Estado**: en topstep.com/labs los siete drops están bajo "Past Lab Drops"; hay "Get Notified For The Next Drop". **Hoy no se puede comprar ninguno.**
### 2.2 Modelo
Política estructural (no optimizada): cada día un bracket con TP = objetivo restante y stop = distancia al piso (la liquidación); 60 días de trading por ronda; slip 0.5; comisiones incluidas. Datos: MNQ/MES/MGC (mundo justo con 40 mundos sintéticos / historia real). Producto elegido por estructura: el que, con el máximo de contratos permitido, tiene un rango diario en dólares comparable al objetivo (MNQ ×10 = 1 NQ).
| Reto | Prod. | P(ronda) justo / real | P(2 rondas) justo / real | **EV por compra** justo / real | Teoría M/(M+T) |
|---|---|---|---|---|---|
| #003 $3K ($49) | MNQ ×10 | 24.8% / 25.9% | 6.14% / 6.72% | **+$135 / +$153** | 25% |
| #003 | MES ×10 | 24.0% / 26.1% | 5.74% / 6.79% | +$123 / +$155 | 25% |
| #003 | MGC ×6 | 26.9% / 19.0% | 7.25% / 3.60% | +$168 / +$59 | 25% |
| #004 $1.5K ($39) | MNQ ×2 | 25.1% / 23.9% | 6.29% / 5.70% | +$55 / +$46 | 25% |
| #005 $6K ($149) | MNQ ×10 | 25.0% / 24.2% | 6.26% / 5.86% | **+$227 / +$202** | 25% |
| #007 (precio ?) | MNQ ×20 | 29.2% / 30.7% | 8.53% / 9.44% | pago esperado $128 / $142 | 33% |
| #006 Combine estática + XFA ($149) | MES ×40 | pase 20.0% / 24.5% | — | **+$24 / −$4** (sin oro: −$25) | 33% |
| #006 | MNQ ×40 | pase 12.5% / 14.5% | — | −$41 / −$63 | 33% |
- **Las rondas se resuelven rápido** (≈ 1.4 días de media para quienes pasan): por eso los días por ronda (30/60/90), el slip y limitar el TP al rango diario **no cambian el resultado** (el stop es la liquidación y el bracket de ~600 ticks se resuelve casi siempre el primer día).
- **#007**: si el precio es menor que ≈ $130–$180 (el pago esperado), tiene EV positivo; hasta conocerlo no se puede decir.
- **#006**: el DLL suave de $1,000 y la consistencia del 55% (el mejor día no puede pasar de 55% del total) frenan el pase muy por debajo del 33% teórico; con el bracket fijo tipo G2 da 13.7% (control). Pago medio por XFA $505–$864. **No es una palanca.**
### 2.3 Qué pasaría si se pudieran comprar muchos #003 (hipótesis, no disponible)
Cada compra es un billete con premio $3,000 (61× la cuota) y probabilidad ≈ 6–7%. Binomial independiente (premio fijo, costo $49):
| n compras | Costo | Neto medio justo / real | Mediana | P(neto<0) justo / real | P(≥ $10k) justo / real |
|---|---|---|---|---|---|
| 5 | $245 | $678 / $767 | −$245 | 73% / 71% | 0% / 0% |
| 20 | $980 | $2,713 / $3,052 | $2,020 | 28% / 25% | 3% / 4% |
| 50 | $2,450 | $6,774 / $7,623 | $6,550 | 4.3% / 3.1% | 19% / 24% |
| 100 | $4,900 | $13,539 / $15,246 | $13,100–$16,100 | 1.3% / 0.8% | 74% / 81% |
Es la estructura de pérdida truncada y pago convexo que preguntabas: **la cola negativa se mitiga por cantidad** (muchos billetes independientes), no por apalancamiento. **Por qué no es un plan**: (1) hoy no está en venta; (2) solo #003 tenía "sin tope de compra" y cada oferta es "limitada, el primero que llega"; (3) máximo 5 retos activos en la ronda de pago a la vez; (4) Topstep puede tratar comprar cientos de retos como abuso (los Términos de Uso hablan de "compras excesivas de Combines o reinicios"; si los retos de Labs entran en esa cláusula: NO VERIFICADO); (5) el modelo supone que el objetivo se cumple al llenarse el TP y que el MLL se liquida en tiempo real; (6) tendrías que ejecutar ~2 operaciones por compra con el ejecutor (señal con TP y stop que dependen del balance: ingeniería nueva en el Pi, sobre MNQ, que el ejecutor aún no soporta).
### 2.4 Regla de decisión para el próximo drop
Antes de comprar: premio R, cuota F, rondas r, MLL M, objetivo T. **EV justo ≈ (M/(M+T))^r × R − F**; conviene si R/F > ((M+T)/M)^r (para #003: 61× contra 16×). Luego leer: ¿intradía o cierre?, ¿tope de compra?, ¿automatización permitida?, ¿contratos y productos restringidos? Suscribirse a "Get Notified" es gratis.

## 3. Sin verificar
1. Reglas de automatización de 29 de las 36 firmas (resúmenes de terceros o ausentes); cuentas, cuotas y reinicios de la mayoría.
2. Si Prop Firm Match tiene más firmas de futuros que las 25 cargadas y qué hay en "Empresas no listadas".
3. Rutas de API de cada firma fuera de ProjectX (acceso y costo de Tradovate/Rithmic para cuentas de prop).
4. Si los retos de Labs vuelven a venderse, con qué reglas y si entran en las cláusulas de compras excesivas.
5. Intradía vs. cierre, MLL en tiempo real y comisiones en los retos de Labs.
6. El efecto del tope de pago de $8,000 de #006 (supuse 50% del balance y 5 días de $150).

## 4. Decisiones de Eric
1. ¿Pido respuesta escrita a Bulenox, FFN, Tradeify, MFFU, Lucid y TPT con las 4 preguntas de §1.5? (es lo que convertiría "desconocido" en dato).
2. ¿Quieres que lea con detalle las firmas "desconocidas" que más te interesen (por ejemplo TPT, BluSky, Purdia, Legends)?
3. ¿Me suscribo/te suscribes a "Get Notified" de Topstep Labs y fijamos la regla de §2.4 para el próximo drop?
4. Si reaparece un reto como #003 sin tope: ¿autorizas diseñar (solo diseño) el generador de señales de dos rondas para el Pi?
