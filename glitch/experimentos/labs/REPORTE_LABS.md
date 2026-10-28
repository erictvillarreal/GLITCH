# Topstep Labs con el GLITCH — ¿vale la pena la lógica «pagas la cuota, el upside es tuyo»?

Miércoles 28-oct-2026 · **MODELADO RÁPIDO, NO AUDITADO** · Detalle, planes y todas las tablas: `resultados_LABS.md` (slippage 1 tick) y `resultados_LABS_emp8.md` (slippage empírico de 8 obs.); código `labs_motor.py`, `labs_retos.py`, 5 pruebas en `test_labs_motor.py`. Reglas de cada reto: el texto que pegó Eric + la página *Topstep Labs* del Help Center leída hoy (extracción automática ⇒ **confirmar en Topstep lo que decide dinero**); lo que la página no dice quedó marcado SUPUESTO.

## 1. Resumen

1. **Solo el $250K Freedom sale positivo y robusto en el modelo:** EV por compra **+$533** a WR 50 % (IC95 sobre los días históricos [+155, +819]), **+$216** a WR 47.4 % y +$808 a 52 %; ROI +107 % sobre la cuota de $499. Con slippage empírico no cambia (+$537 / +$218).
2. **Es una lotería, no un flujo:** P(pasar la Combine) ≈ 20 % y P(≥ 1 pago | XFA) ≈ 22 % ⇒ **solo ≈ 4.4 % de las compras cobran algo**; el EV viene de pagos grandes (~$23k cuando ocurren, porque el pago es 50 % del saldo con tope $25k y el MLL es de $10,000). Con 5 compras, ≈ 80 % de las veces no cobras nada.
3. **El $250K depende de supuestos que la página no fija:** si la XFA lleva DLL de $5,000, el EV baja a **+$225** (WR 50) y **+$18** (47.4); si el pago fuera 25 % del saldo, **+$380** y **+$66**. Pago = 50 % del saldo, división 90/10, mínimo $125 y ausencia de DLL en la XFA: SUPUESTO (la página remite a la política de pagos).
4. **$25K Static y $50K Static: no.** EV por compra **−$18** y **−$40** a WR 50 % (IC95 [−58, +18] y [−111, +25]; P(EV > 0) 12 %), negativos a 47.4 %. Con cuota única sin resets, P(pasar) ≈ 23 % (cota sin ventaja 33 %) y la XFA vale poco (MLL de $1,000 / $2,000).
5. **$1.5K Powered Up ($99): no, ni con ventaja.** Son **dos rondas** (ganar $1,500, y otra vez $1,500 con el mismo MLL de $500) ⇒ P(cobrar) = P(ronda)² ≈ 3.4 %; EV **−$26 a −$49** a cualquier WR probado; el techo teórico sin ventaja es 6.25 % × $1,500 − $99 = −$5.
6. **Por qué falla la «convexidad» en los retos chicos:** con deriva cero, ningún plan puede pasar con más de L/(T+L) (teorema de parada opcional; el modelo lo respeta: 23 % < 33 %). El EV por compra ≈ P(pasar) × valor de la XFA − cuota; solo es positivo si el valor esperado de la XFA es muy grande frente a la cuota (≈ 10× en el $250K; ≈ 3–5× en los Static).
7. **Referencia (mismo método):** el camino actual (Combine de $49 por intento + activación $149, plan de producción) da **+$73** por intento a WR 50 % (+$49 a 47.4), ROI ≈ +120–150 %: **mejor retorno por dólar que cualquier Labs**; el $250K da más dólares por compra pero con ROI menor. Con slippage empírico la referencia baja a +$58 / +$37 y los Labs de brackets anchos casi no se mueven (no dependen del escalón de 2–3 ticks).
8. **Extras (no pedidos, mismas reglas de la página):** $3K (#003, $49): +$52 a WR 50 (+$27 a 47.4); $6K (#005, $149): +$55 (+$22); $1.5K original ($39): +$11 (−$1); $3K Undead ($199): −$98; $3K Slasher ($65): −$30. Todos de dos rondas con P(cobrar) ≈ 3–5 %: EV chico y límite de 5 compras.
9. **Límites de compra:** $50K Static 5 por trader; $250K «hasta 5 por mes»; $1.5K 5 por trader; $25K no indicado. Varias cuentas con las mismas señales: **RTP/conducta, sin respuesta de Topstep**; y el plan ganador del $250K arriesga todo el MLL en un trade (muerte rápida): ¿lo permite «Responsible Trading Advantage»? DESCONOCIDO.
10. **NO VERIFICADO:** reglas de la XFA de cada reto (pago, DLL, escalado intermedio del $250K, escalón «2/3/4» del $50K Static); el slippage de MGC/MNQ; la 8.ª observación de slippage; que la extracción automática de las páginas sea fiel. Plan elegido en el 60 % más viejo de 2 años de datos y reportado en el 40 % más reciente (≈ 200 días): el IC solo cubre ese conjunto de días.

## 2. Reglas usadas (estado)

| reto | cuota | meta | MLL | DLL | contratos | consistencia | XFA / pago | estado |
|---|---|---|---|---|---|---|---|---|
| $25K Static #001 | $75 única, sin resets | $2,000 | $1,000 estático | $500 | 2 minis / 20 micros | 55 % | MLL $1,000 estático → $0 tras el 1.er pago; DLL $500; tope $4,000; Standard (5 días ≥ $150) o Consistencia (40 %); activación gratis | cuota, meta, MLL, DLL, tope: pegado por Eric y Help Center; % del pago: SUPUESTO |
| $50K Static #006 | $149 única | $4,000 | $2,000 estático | $1,000 | 4 minis / 40 micros | 55 % | MLL $2,000 → $0; DLL $1,000; tope $8,000; escalado «2/3/4» sin explicar (se asumió ≤ 20 micros) | ídem |
| $250K Freedom #002 | $499 única | $15,000 | $10,000 **de cierre (trailing EOD)** | $5,000 | 25 minis / 250 micros | 55 % | Standard: 5 días ≥ $1,000; tope $25,000 por pago; MLL $10,000 → $0 tras el 1.er pago; DLL de la XFA no indicado; escalado 3 lotes (< $1,500) a 25 (> $8,000) | pasos intermedios del escalado: SUPUESTO (irrelevante: el plan usa ≤ 30 micros) |
| $1.5K Powered Up #007 | $99 única | $1,500 | $500 estático | ninguno | 2 minis / 20 micros | ninguna | **dos rondas** (el pago fijo de $1,500 se cobra al ganar la 2.ª ronda); vence a 90 días / 30 sin operar | estructura de dos rondas: página de Labs + publicación de Topstep (búsqueda) — confirmar |

## 3. Cómo se modeló (rápido)

Días reales de 5 min (2 años): MES, MNQ, MCL (9:35 → 14:25 CT) y MGC (7:15); un trade por día, lado alternado; cada reto elige por separado producto, bracket (SL = k × rango mediano; TP = ρ × SL; ρ de 0.33 a 3), tamaño (fracción f del MLL, hasta 3×) y, en las Combine, si pasa a XFA con su propio plan. Combine: objetivo, MLL estático o de cierre, DLL (recorta el stop del día), consistencia 55 % (el mejor día no pasa del 55 % del beneficio), mínimo 2 días, vence a los 63 días hábiles. XFA: `xfa_engine` con las reglas del reto. Costos: cuota única; API $14.30/mes por cuenta activa mostrado aparte (resta ≈ $0–$10 por compra). WR 47.4 / 50 / 52 % = etiquetas de deriva calibradas en el bracket nominal (como H1). La tabla de P(pasar) respeta la cota de parada opcional.

## 4. Qué haría (juicio)

1. **No comprar** $25K Static, $50K Static ni $1.5K Powered Up.
2. **$250K Freedom:** es la única con convexidad real, pero su EV depende de reglas de pago/DLL que hay que **confirmar por escrito antes de gastar** ($499 × n): (a) % y tope del pago en la XFA, (b) DLL de la XFA, (c) si el escalado y «Responsible Trading Advantage» permiten arriesgar todo el MLL en un trade, (d) qué cuenta como «mismas señales en varias cuentas». Si se confirman (a)–(c), una compra piloto de $499 es una apuesta con ≈ 4 % de cobrar y EV positivo en el modelo; **no** es un flujo estable ni sustituye al camino actual.
3. **El camino actual ($49 por intento)** sigue teniendo mejor ROI por dólar en este marco; el $250K compite por dólares absolutos por compra.
4. Cierra el hueco más barato: preguntar a Topstep (ticket) las 4 preguntas de arriba y el % de pago de las XFA de Labs.
