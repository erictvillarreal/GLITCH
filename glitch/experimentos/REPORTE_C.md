# REPORTE C — Economía, liquidación en el Pi y slippage real — 20-oct-2026

Rama `experimentos-research`. **Nada desplegado.** Los parches C2/C3 son archivos `.diff` + módulos nuevos dentro de `experimentos/extras/` (marcados NO DESPLEGAR / NEEDS HUMAN REVIEW, regla 4). Verificados en un árbol temporal aparte: `git apply --check` limpio sobre `origin/main` y suite completa verde (492 base + 17 de C2 + 15 de C3 = **524 pasan**; con el sizing de la Parte A apilado, 529: `extras/PARCHES_TODOS_NO_DESPLEGAR.diff`).

---

## C1 — Conciliar las cifras económicas (una cuenta Topstep 50K, 12 meses desde 19-oct-2026)

**Script único y reproducible:** `economia/reconciliar.py --engine-root <checkout de research/firm-map-and-labs @6d4b069>/glitch` (≈ 40 s con 20,000 trayectorias; salida `economia/resultados_C1.md`). El motor (`dd_cash/lever_engine.py`) no está en `main`; el script lo importa sin modificarlo y una copia con un único cambio opcional (`economia/lever_engine_ref.py`, 6 pruebas, idéntica al original con el cambio apagado) modela el bracket anclado a la referencia.

### Las tres versiones eran correctas **para su convención**; el puente las reproduce

| versión publicada | cifra publicada | paso del puente que la reproduce | reproducido aquí (CON oro / SIN oro / justo, media) |
|---|---|---|---|
| `engine_real` 26-sep | media ~$4.6k (neto 12 m: p50 $3,532, p10 −$1,869, p90 $11,001; P(año<0) 22 %; fees $5,349) | S0 | **4,679** / 2,640 / 6,021 |
| `lever_engine` 7-oct | TP32: $3.3k / $1.9k / $3.7k | S4 | 3,555 / 1,879 / 4,836 |
| doc 13-oct (número de planeación ≈ $2,000; rango $1.1k–$3.0k) | nc40 TP32: $2.6k / $1.1k / $3.0k | S5 | 2,632 / 1,127 / 3,153 |

*(Mundos: “justo” = 40 mundos sintéticos con signo volteado al azar (sin deriva muestral); “CON oro” = historia real de 497 días comunes; “SIN oro” = sin la ventana 14-nov-2025..26-ene-2026 en la que MGC ganó +$77.5/contrato/día.)*

### Puente acumulativo (cada fila cambia UN supuesto respecto a la anterior; media / mediana / P(neto < 0))

| paso | justo | real CON oro | real SIN oro | Δ media CON oro |
|---|---|---|---|---|
| **S0** Convención 26-sep: TP 40, reglas del motor validado, XFA serie fija, slip 0, **sin** haircut | 6,021 / 5,307 / 16 % | 4,679 / 4,007 / 20 % | 2,640 / 2,027 / 32 % | — |
| S1 + haircut −25 % de payouts (proxy de liquidación XFA, desde 24-sep) | 3,177 / 2,633 / 28 % | 2,187 / 1,675 / 33 % | 609 / 141 / 48 % | **−2,492** |
| S2 + TP 32 (aprobado 12-oct, **no desplegado**) | 4,039 / 3,511 / 21 % | 2,960 / 2,478 / 26 % | 1,296 / 849 / 40 % | +773 |
| S3 + reglas de pago verificadas (mín. $125, ganancia neta desde el último pago, topes) | 3,944 / 3,428 / 21 % | 2,914 / 2,449 / 26 % | 1,260 / 841 / 40 % | −46 |
| **S4** + liquidación XFA en tiempo real **explícita** (reemplaza el haircut) | 4,836 / 4,093 / 21 % | 3,555 / 2,902 / 26 % | 1,879 / 1,310 / 37 % | +641 |
| **S5** + stop llenado en el extremo de la barra (slip 0.5) | 3,153 / 2,485 / 30 % | 2,632 / 1,997 / 32 % | 1,127 / 555 / 44 % | −923 |
| S6a + slippage de entrada 1 tick (lun 19-oct), **bracket anclado a la referencia** como el Pi real | 2,861 / 2,195 / 32 % | 2,381 / 1,760 / 34 % | 900 / 334 / 46 % | −252 |
| S6b + slippage de entrada 3 ticks (mar 20-oct, inferido), idem | 310 / −451 / 54 % | −45 / −718 / 57 % | −1,096 / −1,680 / 68 % | **−2,426** |

**Qué explica la diferencia entre versiones:** (1) el haircut −25 % (S1) fue más pesimista que la liquidación explícita (S4 recupera +$641); (2) el stop llenado en el extremo de la barra (S5, **−$923**) es un supuesto de fricción que S0–S4 no tenían; (3) **el supuesto que ninguna de las tres modelaba como el Pi real es el ancla del bracket**: los reportes del 7–13-oct trataban el slippage de entrada como si TP/SL se anclaran al *fill*; `pi_executor.py` (líneas 1189–1200) los ancla a la *referencia*. Con ancla al fill, 3 ticks de slip cuestan −$1.0k (CON oro: $2,634 → $1,663); con ancla a la referencia, **−$2.7k** ($2,632 → −$45): el segundo TP ya no completa los $3,000 y hace falta un tercero.

### Validación cruzada de P(pase) con la Parte A (misma entrada 9:45 CT, TP32/SL100, nc40, cuenta nueva, stop sin slip)

| slip de entrada | Parte A (replay 492 d, MC 20k) | motor, ancla a la **referencia** (CON / SIN / justo) | motor, ancla al **fill** (convención anterior) |
|---|---|---|---|
| 0 | 31.4 % | 33.8 / 32.3 / 31.1 % | 33.8 / 32.3 / 31.1 % |
| 1 | 30.9 % | 33.0 / 31.4 / 30.1 % | 31.6 / 29.8 / 29.0 % |
| 2 | 18.0 % | 20.6 / 19.8 / 19.5 % | 29.0 / 27.7 / 27.2 % |
| 3 | 16.9 % | 19.6 / 18.8 / 18.2 % | 27.7 / 26.3 / 25.5 % |

Con ancla a la referencia el motor reproduce el desplome de la Parte A (±3 pp; el motor además usa stop llenado en el extremo de la barra); con ancla al fill lo subestima por ~8 pp. **La P(pase) por intento que usa el rango final es la de este motor calibrado contra la Parte A**, no la asumida del 12-oct (32.7 % era el techo del juego justo con slip 0).

### Rango único (TP 32, liquidación XFA explícita, stop 0.5, XFA vigente MGC 364×3; media / mediana / P(<0))

| slippage de entrada (ticks) | justo | real CON oro | real SIN oro |
|---|---|---|---|
| 0 (optimista) | 3,153 / 2,485 / 30 % | 2,632 / 1,997 / 32 % | 1,127 / 555 / 44 % |
| 1 (lun 19-oct) | 2,861 / 2,195 / 32 % | 2,381 / 1,760 / 34 % | 900 / 334 / 46 % |
| **mezcla {1,3} 50/50 (observado, N = 2)** | 1,586 / 837 / 43 % | **1,168 / 464 / 46 %** | −98 / −709 / 57 % |
| 3 (mar 20-oct, inferido) | 310 / −451 / 54 % | −45 / −718 / 57 % | −1,096 / −1,680 / 68 % |

**Conclusión de C1:** no existe un “rango único” sin condicionarlo al slippage real. Con el slippage que sí observamos (1 y ≈3, N = 2) la expectativa de **una cuenta es ≈ $1.2k (real con oro) con rango −$0.1k (sin oro) a +$1.6k (justo)**, y P(neto < 0) de 43–57 %. El “$2,000/año” (13-oct) vale solo si el slip sostenido es ≈ 1 tick o menos. **Bajo el umbral de ~$7,000/año del propio Eric**, la brecha creció, no se achicó.

### RTP (nuevo) — modelado como régimen alterno, no como probabilidad

Fuente (`help.topstep.com/13620045`, **leído 20-oct-2026**, “Updated this week”): se dispara por “multiple accounts hit the MLL in one day”, “max position a majority of trades”, “don’t keep losers smaller than winners”, “don’t use stops”…; sin umbrales numéricos. Bajo RTP: todo Combine/XFA nuevo con **DLL** ($1,000 en 50K); si se resetea un Combine pasa a **Consistency Trading Combine con DLL**; las XFA nuevas son **solo Consistency (40 %)**; las XFA Standard existentes no se tocan. Resultado del régimen puro (slip 1): **CON oro $539 (vs $2,381), SIN oro −$517 (vs $900), justo $780 (vs $2,861)**. No hay base para estimar P(entrar al RTP); por el patrón de G2 (≈80 % del máximo, pérdidas 2.5× las ganancias nominales) varios criterios se tocan. El modelo cubre DLL + ruta Consistency de la XFA, **no** las reglas del “Consistency Trading Combine” (NO VERIFICADO: la página no las detalla).

### Reglas de pago vigentes (leídas 20-oct-2026, `help.topstep.com/8284233`)

Mínimo $125 · 90/10 · Standard: 5 días ≥ $150 de P&L neto y ganancia neta > $0.01 desde el último pago (el primero exento) · 50 % del saldo con tope **$2,000 (50K Standard)** / $3,000 (Consistency) · con DLL comprado al inicio (oferta temporal): topes duplicados ($4,000/$6,000) · MLL se fija en $0 tras el primer pago · **primeros $10,000 de ganancias de por vida al 100 % solo para quienes entraron al dashboard nuevo antes del 12-ene-2026** (elegibilidad de Eric **NO VERIFICADA**; si aplica: +$0.7–0.8k/año CON oro y +$0.6–0.7k SIN oro, con slip 1 o con la mezcla {1,3}). El motor ya usa estas reglas desde S3.

### Qué NO está resuelto en C1

Riesgo de que Topstep considere el patrón (varios Combines seguidos que se pierden, 44–53 intentos/año) “excessive purchases of Combines or Resets” (sin umbral). Cuentas correlacionadas (no modeladas aquí). Tabla de escalado XFA (imagen, sin texto). Todo sigue siendo **una historia de 515 días, un solo producto de Combine y otro de XFA**.

---

## C2 — Detección de liquidación en el Pi (`extras/C2_liquidacion_NO_DESPLEGAR/`)

**Problema (19-oct):** TopstepX liquidó la cuenta; el Pi vio “ambas patas ausentes + cuenta plana”, registró `UNKNOWN`, pnl 0, y `_attempt_entries` (`result in ("TP","SL","FLATTEN")`) lo excluyó: el intento no avanzó y hubo que corregir el Gist a mano.

**Diseño determinista (sin LLM, regla 1):** `pi/liquidation_pure.py::classify_unknown_exit` clasifica `LIQ` solo con evidencia fuerte de `Account/search` (el Pi ya lo usa): **E1** la cuenta operada ya no figura entre las activas *y la lista no está vacía* (descarta un glitch que devuelve `[]`), o **E2** `canTrade == false`. Con una lista vacía o solo una pista débil (balance ≤ piso + $50) queda `UNKNOWN` + `liq_suspected` y alerta fuerte. El P&L del `LIQ` es **estimado y marcado** (`pnl_estimated`): `piso_relativo − pnl_acumulado_previo`, que deja el acumulado del intento *exactamente* en el piso y hace que `_check_attempt_reset` devuelva `QUIEBRE`. Para eso el scheduler agrega `attempt_pnl_before` y `attempt_floor` a la señal; si faltan, no se convierte a ciegas. El scheduler cuenta `LIQ` como ciclo resuelto (`RESOLVED_RESULTS`), no como victoria.

**Qué NO está verificado:** el campo `canTrade` de `Account/search` sale de la documentación pública de ProjectX; no lo he visto en vivo en esta cuenta (E1 no lo necesita). El comportamiento de `onlyActiveAccounts=false` tampoco. **Antes de desplegar, validar en Practice con un reset real.**

**Pruebas (17 nuevas):** casos puros (E1, E2, lista vacía, balance cercano al piso, lectura fallida), `_finalize_cycle` extremo a extremo (LIQ con pnl en el piso, intento que avanza a #3 y dispara `QUIEBRE`, compatibilidad: `UNKNOWN` idéntico a hoy con la cuenta presente, sin estado previo, error de API, un TP normal no consulta cuentas) y scheduler (LIQ no suma victoria; UNKNOWN sigue excluido). Archivos: `liquidation_pure.py`, `test_liquidation_detection.py`, `C2_modificaciones.diff`.

## C3 — Registrar el slippage real (`extras/C3_slippage_NO_DESPLEGAR/`)

**Parche:** `pi/slippage_pure.py::slippage_ticks(side, ref, fill, tick)` = `side·(fill − ref)/tick` (positivo = adverso). `run_once` lee el fill de la orden de entrada justo después de confirmar la posición y lo muestra en el `[OPEN]` de Telegram; `_finalize_cycle` registra `ref_price`, `fill_price` y `slip_ticks` en el historial (solo si el fill es real, nunca inventado). 15 pruebas. Archivos: `slippage_pure.py`, `test_slippage_logging.py`, `C3_modificaciones.diff`. **C2 + C3 combinados:** `extras/C2_C3_combinado.diff` (los hunks de import chocan; el combinado está resuelto y probado).

**Recalcular el 19 y 20-oct: NO DISPONIBLE.** El historial de trades de TopstepX requiere una sesión autenticada (no manejo credenciales) y `geometry_mestest_log.json` está en el Gist. Cálculo manual para cualquier día: `slip = lado·(precio de fill de TopstepX − referencia del mensaje [OPEN] del Pi)/0.25`, con lado = +1 para LONG y −1 para SHORT (positivo = adverso). **Pegar ese par (referencia, fill) de los días 19 y 20 basta para fijar la mezcla de slippage con datos en vez de “1 y ≈3”.**
