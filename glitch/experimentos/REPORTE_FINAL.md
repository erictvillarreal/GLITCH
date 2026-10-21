# REPORTE FINAL — rama `experimentos-research` (20-oct-2026)

Detalle: [Parte A](preservacion/REPORTE_A.md) · [Parte B](direccion/REPORTE_B.md) · [Parte C](REPORTE_C.md) · [Propuestas](PROPUESTAS.md) · [cómo reproducir](README.md). **Nada se mergeó a `main`, nada se desplegó, no se tocó el Pi, Railway ni credenciales.** Todo cambio de producción propuesto es un `.diff` + módulo nuevo + pruebas dentro de `glitch/experimentos/`, marcado NO DESPLEGAR / NEEDS HUMAN REVIEW.

## Resumen de 1 página

**Qué se hará mañana (miércoles 21-oct, SHORT por paridad): nada cambia — 40 contratos —, salvo que Eric decida otra cosa antes de las 8:25 Monterrey.**
- Estado de partida usado (a confirmar con TopstepX): balance 51,401.2, piso 49,401.2, meta 53,000.
- Con 40 contratos: P(TP) 55.4 %, **P(liquidar mañana) 44.2 %**. La pérdida no es capital: es un reset de $49 y ~3–5 días. El costo de bolsillo esperado hasta pasar es el mismo (≈ $72–80) con 14 que con 40 contratos.
- Si Eric prefiere no arriesgar la liquidación mañana: `GLITCH_PI_NC_MAX=14` en el Pi (hace *imposible* liquidar en un día: margen $127.92, supuesto de slip de salida 3) cuesta ≈ −3.3 pp de P(pase) con continuación óptima (46.5 % vs 49.8 %), pero tras un SL (18.7 %) el intento queda casi muerto.
- **Lo que sí vale la pena y es gratis:** si mañana sale TP, el balance quedará en ≈ 52,802–52,902; al día siguiente usar `nc = ⌈faltante/35⌉` (≈ 3–6 contratos) vía `GLITCH_PI_NC_MAX`. Sube el pase de ese tramo de ~62 % a ~91–95 % y baja de ~38 % a 5–9 % la probabilidad de “quemar la cuenta a $100 de la meta”.

**Qué se propone (priorizado en [PROPUESTAS.md](PROPUESTAS.md)):**
1. **Sizing finish-line** (40 mientras falte mucho; achicar cuando un TP ya cubre el faltante): **33.8 % → 51.4 %** de pase en el intento actual (robusto en 5 modelos). Techo teórico 55.6 %. Parche listo, apagado por defecto.
2. **Medir y neutralizar el slippage de entrada.** Hallazgo no previsto: TP/SL se anclan a la *referencia*, no al fill. Con nc 40 y TP 32, dos TP suman $3,002 (slip 1) o $2,802 (slip 3): con slip ≥ 2 hace falta un tercer TP y el pase de una cuenta nueva cae de ~30 % a ~17 %. Con la mezcla observada (1 y ≈3, **N = 2**) la economía de una cuenta es ≈ **$1.2k/año (rango −$0.1k a +$1.6k)**, no los $2,000 del 13-oct. Ejecutar C3 (parche listo) y probar brackets anclados al fill en Practice.
3. **Detección de liquidación en el Pi** (C2, parche listo): evita el `UNKNOWN`/pnl 0 del 19-oct y la edición manual del Gist.
4. **Preguntas escritas a Topstep:** RTP (umbrales), compras masivas de Combines, beneficio de “primeros $10k al 100 %”.

**Resultados negativos que cuentan:** (Parte B) **ninguna de las tres reglas de dirección pasa D2**; `alternate` queda dentro del intervalo del azar (55.5 % vs 49.3–57.7 %); un rally de 12 meses no dio ventaja al lado largo; no hay efecto de hora de entrada (7 horas, 28.9–32.4 %, ruido). “SL-safe” puro (P2/P4/P5) cuesta 7–9 pp de pase y 27+ días. Esperar cuando el colchón es bajo (P6) deja 57 % de intentos abiertos.

**Riesgos:** (i) una sola historia de 492 días, un solo producto; (ii) el slippage real tiene N = 2; (iii) el RTP desplaza la economía a ≈ $0.5k (CON oro) / −$0.5k (SIN oro) y no hay umbrales publicados; (iv) el patrón de 44–53 intentos/año puede tocar “excessive purchases”; (v) los parches no se probaron en vivo (Practice) — `canTrade` y `onlyActiveAccounts=false` son NO VERIFICADO.

**Qué NO se sabe:** el slippage real (hay que pegar referencia y fill de los días 19 y 20); si el MLL liquida con el pico por saldo de cierre o intradía en este tipo de cuenta; el slip real de salida del SL (supuse 3 ticks); si Eric califica para los $10k al 100 %; el neto vs bruto del +$1,450; las 8 sesiones en vivo (están en el Gist).

## Supuestos clave y su fuente

| supuesto | valor | fuente / estado |
|---|---|---|
| mecánica de entrada | ref = close de la barra 9:30 CT; TP/SL desde la referencia; flatten 14:30 CT | `geometry_scheduler.py`, `pi_executor.py:1189-1200` |
| reglas del Combine | MLL $2,000 tiempo real, piso congelado en 50,000, meta $3,000, consistencia < $1,650 (dashboard) | encargo §1; el log del 24-sep da la regla oficial (55 % que sube el objetivo): no liga con TP 32/nc ≤ 40 |
| pago XFA | mín. $125 · 90/10 · 5 días ≥ $150 · tope $2,000 (50K Standard) · $10k al 100 % solo dashboard nuevo antes del 12-ene-2026 | `help.topstep.com/8284233`, **leído 20-oct-2026** |
| RTP | DLL $1,000, XFA solo Consistency 40 %, Combine de reset en Consistency con DLL; sin umbrales | `help.topstep.com/13620045`, **leído 20-oct-2026** |
| comisión / tick | $1.22 round-trip / $1.25 por tick MES | `geometry_pure.py::SPECS`, `help.topstep.com/commissions-and-fees` (log 25-ago) |
| costos de bolsillo | $49 por reset/mes (≈ $2.33 por día hábil); $149 activación; $59.5/mes compartidos | log 24-sep / 6-oct; encargo §1 |
| slippage de entrada | {1, 3} ticks 50/50 | **N = 2** (lun 1, mar ≈ 3 inferido) |
| slippage de salida SL | 3 ticks | **supuesto sin medición** |
| datos | MES 5 min, 2024-08-26 → 2026-08-25, 492 días completos | `data_cache/mes_5min_2y.parquet` |

## Verificación

- Suite base del repo: **492 pasan** en esta rama (sin cambios fuera de `glitch/experimentos/`); **529 pasan** con sizing + C2 + C3 apilados en un árbol temporal (492 + 5 + 17 + 15): `extras/PARCHES_TODOS_NO_DESPLEGAR.diff`, `git apply --check` limpio sobre `origin/main`. (Los diffs de sizing y de C2/C3 por separado también aplican limpios sobre `main`, pero no apilan entre sí; usar el combinado.)
- Pruebas nuevas: 18 (regresión Parte A, §2.2), 5 (sizing), 6 (copia del motor con ancla a la referencia, idéntica al original con el cambio apagado) + las 32 de los parches.
- `git diff origin/main --stat -- glitch/ ':!glitch/experimentos'` → vacío. `geometry_pure.py`, el scheduler y el Pi de `main` no se modificaron.
- Errores míos corregidos durante el trabajo (y por qué las tablas finales son las correctas): el stop disparaba como liquidación al cruzar el piso en la misma barra (inflaba P(liq) con 8–14 contratos); la máscara de estados > 52,000 de la DP; la DP aplicada fuera de su rejilla rinde 31–44 % (“filo de navaja”): se usa como techo, no como política.

## Decisiones que necesita de Eric

1. **Antes de las 8:25 Monterrey de mañana:** ¿40 (A, recomendada), 14 (B) o 25 (C)? Sin acción = 40.
2. **Si mañana hay TP:** ¿aplicar el tope manual `⌈faltante/35⌉` al día siguiente?
3. **Pegar** la referencia (mensaje `[OPEN]` del Pi) y el fill de TopstepX de los días 19 y 20, y/o **exportar** `geometry_mestest_log.json`: fija el slippage con datos.
4. **Confirmar** el estado de la cuenta (BAL, MLL, neto vs bruto; `pnl` vs `pnl_real`) y la regla de consistencia del dashboard.
5. **Aprobar o no** los parches: sizing finish-line (apagado por defecto), C2 (liquidación), C3 (slippage). Los tres exigen revisión humana antes de merge; recomiendo C3 primero (es solo registro).
6. **Probar en Practice** el bracket anclado al fill (propuesta 2) antes de cualquier cambio de TP/nc.
7. **Enviar a Topstep** las preguntas de RTP, compras masivas y beneficio de $10k.
8. **Actualizar el número de planeación**: hasta medir el slippage, “≈ $1.2k/año por cuenta (rango −$0.1k a +$1.6k)” sustituye a los $2,000.
