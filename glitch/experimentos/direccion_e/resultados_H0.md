# resultados_H0 — mapa de probabilidades (Parte H)

IC95 = percentiles 2.5–97.5 de **20** remuestras (modo `--quick`; con 20 el IC es aproximado y tiende a ser algo ancho; `python h0_mapa.py` sin `--quick` usa 100 y tarda ≈ 1 h) de la HISTORIA REAL (bloques de 5 días; MGC 488 días limpios, MES 492 días), cada una con su banco de 20,000 intentos/vidas. Cuenta lo incierto del conjunto de días, **no** lo incierto del futuro (cambio de régimen). Estados: MEDIDO / MODELADO / SUPUESTO / DESCONOCIDO.

## Filas 1–2. MGC (3 micros, SL = TP = 364 ticks, 7:15→14:30 CT, datos limpios de contrato; FLATTEN = cierre a las 14:30 sin tocar barrera)

| regla | TP % | SL % | FLATTEN % | WR_dec = TP/(TP+SL) | N | estado |
|---|---|---|---|---|---|---|
| alternate | 20.9 % [17.7, 24.5] | 23.2 % [19.6, 27.4] | 55.9 % [49.2, 59.6] | **47.4 % [41.1, 54.0]** | 488 días (215 decididos) | MEDIDO (2024-09→2026-09; el WR sale de un solo camino de precios) |
| siempre LARGO | 20.3 % [17.2, 23.6] | 23.8 % [21.0, 28.2] | 55.9 % [49.2, 59.6] | **46.0 % [40.7, 51.7]** | 488 días (215 decididos) | MEDIDO (2024-09→2026-09; el WR sale de un solo camino de precios) |
| siempre CORTO | 23.8 % [21.0, 28.2] | 20.3 % [17.2, 23.6] | 55.9 % [49.2, 59.6] | **54.0 % [48.3, 59.3]** | 488 días (215 decididos) | MEDIDO (2024-09→2026-09; el WR sale de un solo camino de precios) |

WR_todos = TP/n (FLATTEN como no-ganador) = la columna TP %. WR_signo y WR_pnl: ver `resultados_F2.md`. En LARGO y CORTO FLATTEN cuenta igual: queda fuera del denominador de WR_dec.

## Fila 1b. MES (nc 40, TP 32, SL 100 pero **la liquidación por MLL ocurre a 40 ticks**; ventana 9:35→14:30 CT)

| slip de entrada | lado | TP % | SL % | **LIQ (MLL) %** | FLATTEN % | estado |
|---|---|---|---|---|---|---|
| 0 | LARGO | 52.8 % [48.5, 56.3] | 0.0 % [0.0, 0.0] | 47.2 % [43.7, 51.5] | 0.0 % [0.0, 0.0] | MODELADO sobre 492 días reales (slip: SUPUESTO/N=2) |
| 0 | CORTO | 56.7 % [54.2, 59.3] | 0.0 % [0.0, 0.0] | 42.9 % [40.3, 45.2] | 0.4 % [0.0, 0.7] | MODELADO sobre 492 días reales (slip: SUPUESTO/N=2) |
| 1 | LARGO | 51.8 % [48.3, 54.8] | 0.0 % [0.0, 0.0] | 48.2 % [45.2, 51.7] | 0.0 % [0.0, 0.0] | MODELADO sobre 492 días reales (slip: SUPUESTO/N=2) |
| 1 | CORTO | 56.1 % [53.7, 58.8] | 0.0 % [0.0, 0.0] | 43.5 % [40.8, 45.7] | 0.4 % [0.0, 0.7] | MODELADO sobre 492 días reales (slip: SUPUESTO/N=2) |
| 3 | LARGO | 50.8 % [47.0, 53.8] | 0.0 % [0.0, 0.0] | 49.2 % [46.2, 53.0] | 0.0 % [0.0, 0.0] | MODELADO sobre 492 días reales (slip: SUPUESTO/N=2) |
| 3 | CORTO | 54.7 % [52.0, 57.7] | 0.0 % [0.0, 0.0] | 44.9 % [41.8, 47.7] | 0.4 % [0.0, 0.7] | MODELADO sobre 492 días reales (slip: SUPUESTO/N=2) |

## Fila 3. Un día del Combine con nc 40 desde el estado actual (balance $51,401.20, piso $49,401.20 ⇒ colchón $2,000; lado de lunes 26-oct = LARGO)

El colchón es el de una cuenta nueva ($2,000): la probabilidad de TP/liquidación de UN día es la de la tabla anterior (LARGO). Lo que cambia con el estado es **pasar** (fila 4).

## Filas 4–5. P(pasar el Combine) y duración, nc 40 fijo (P0) y finish-line (P3); slip 0–4 ticks (M2 = costo de ejecución; M1 = movimiento de precio)

| inicio | política | slip | M2 P(pasar) | M1 P(pasar) | días a resolver (media) | intentos esperados hasta pasar (1/p, M2) | estado |
|---|---|---|---|---|---|---|---|
| cuenta nueva | P0 | 0 | 29.9 % [29.1, 31.2] | 29.9 % [29.1, 31.2] | 1.55 | 3.3 | MODELADO (reglas oficiales; slip SUPUESTO) |
| cuenta nueva | P0 | 1 | 29.0 % [27.8, 30.4] | 31.3 % [29.5, 32.6] | 1.54 | 3.4 | MODELADO (reglas oficiales; slip SUPUESTO) |
| cuenta nueva | P0 | 2 | 18.0 % [16.6, 19.1] | 21.0 % [19.3, 22.7] | 1.83 | 5.6 | MODELADO (reglas oficiales; slip SUPUESTO) |
| cuenta nueva | P0 | 3 | 17.2 % [15.9, 18.3] | 21.1 % [19.5, 22.4] | 1.81 | 5.8 | MODELADO (reglas oficiales; slip SUPUESTO) |
| cuenta nueva | P0 | 4 | 16.1 % [15.5, 17.8] | 21.3 % [20.0, 23.3] | 1.79 | 6.2 | MODELADO (reglas oficiales; slip SUPUESTO) |
| cuenta nueva | P3 | 0 | 29.9 % [29.0, 31.9] | 29.9 % [29.0, 31.9] | 1.55 | 3.3 | MODELADO (reglas oficiales; slip SUPUESTO) |
| cuenta nueva | P3 | 1 | 29.0 % [27.6, 29.9] | 31.3 % [30.1, 32.3] | 1.54 | 3.4 | MODELADO (reglas oficiales; slip SUPUESTO) |
| cuenta nueva | P3 | 2 | 27.0 % [26.2, 29.6] | 30.5 % [29.0, 32.9] | 1.93 | 3.7 | MODELADO (reglas oficiales; slip SUPUESTO) |
| cuenta nueva | P3 | 3 | 25.2 % [24.0, 26.2] | 29.9 % [28.6, 31.6] | 1.89 | 4.0 | MODELADO (reglas oficiales; slip SUPUESTO) |
| cuenta nueva | P3 | 4 | 23.0 % [21.4, 23.8] | 29.2 % [26.6, 30.3] | 1.93 | 4.3 | MODELADO (reglas oficiales; slip SUPUESTO) |
| estado actual (+$1,401.20) | P0 | 0 | 35.6 % [32.7, 38.2] | 35.6 % [32.7, 38.2] | 1.54 | 2.8 | MODELADO (reglas oficiales; slip SUPUESTO) |
| estado actual (+$1,401.20) | P0 | 1 | 34.0 % [32.7, 36.7] | 36.6 % [35.2, 39.6] | 1.53 | 2.9 | MODELADO (reglas oficiales; slip SUPUESTO) |
| estado actual (+$1,401.20) | P0 | 2 | 33.4 % [31.5, 35.6] | 36.5 % [34.8, 38.6] | 1.53 | 3.0 | MODELADO (reglas oficiales; slip SUPUESTO) |
| estado actual (+$1,401.20) | P0 | 3 | 32.6 % [30.2, 34.3] | 37.0 % [33.8, 38.8] | 1.52 | 3.1 | MODELADO (reglas oficiales; slip SUPUESTO) |
| estado actual (+$1,401.20) | P0 | 4 | 31.4 % [29.5, 32.4] | 37.3 % [35.7, 38.9] | 1.51 | 3.2 | MODELADO (reglas oficiales; slip SUPUESTO) |
| estado actual (+$1,401.20) | P3 | 0 | 51.5 % [47.8, 53.8] | 51.5 % [47.8, 53.8] | 1.72 | 1.9 | MODELADO (reglas oficiales; slip SUPUESTO) |
| estado actual (+$1,401.20) | P3 | 1 | 49.4 % [46.9, 51.8] | 51.6 % [49.0, 54.2] | 1.71 | 2.0 | MODELADO (reglas oficiales; slip SUPUESTO) |
| estado actual (+$1,401.20) | P3 | 2 | 47.7 % [44.8, 50.4] | 51.1 % [48.0, 55.0] | 1.68 | 2.1 | MODELADO (reglas oficiales; slip SUPUESTO) |
| estado actual (+$1,401.20) | P3 | 3 | 46.2 % [41.7, 48.9] | 50.8 % [47.7, 53.2] | 1.66 | 2.2 | MODELADO (reglas oficiales; slip SUPUESTO) |
| estado actual (+$1,401.20) | P3 | 4 | 43.8 % [40.4, 47.6] | 50.2 % [45.1, 53.7] | 1.75 | 2.3 | MODELADO (reglas oficiales; slip SUPUESTO) |


XFA 3 micros, SL = TP = 364, stop 0.5, reglas oficiales verificadas (20-oct), sin RTP; **la ventaja se impone con una deriva calibrada para fijar WR_dec** (MODELADO: el WR real de cada escenario es una hipótesis, no un dato). IC95: 60 remuestras de bloques de 5 días de la historia limpia (W2 = sin la ventana de oro, 443 días), bancos de 8,000; punto: 40,000 vidas.

## Fila 6. Vida de la XFA por escenario de WR (W2)

| WR_dec | P(≥1 pago) | P($0 en la vida) | cobrado medio por XFA | pago medio (si cobra) | días de trading al 1.er pago (mediana) | vida media (días) | P(perderla antes del 1.er pago) | estado |
|---|---|---|---|---|---|---|---|---|
| 45.0 % | 18.0 % [16.6, 19.5] | 82.0 % | $244 [210, 297] | $1,352 | 8 | 7.2 | 82.0 % | MODELADO (WR = hipótesis; coincide con P($0): toda vida sin pago termina en liquidación) |
| 47.4 % | 25.7 % [23.3, 27.9] | 74.3 % | $406 [355, 443] | $1,580 | 7 | 8.4 | 74.3 % | MODELADO (WR = hipótesis; coincide con P($0): toda vida sin pago termina en liquidación) |
| 48.5 % | 29.9 % [27.1, 33.0] | 70.1 % | $508 [472, 553] | $1,699 | 7 | 9.0 | 70.1 % | MODELADO (WR = hipótesis; coincide con P($0): toda vida sin pago termina en liquidación) |
| 50.0 % | 33.0 % [30.6, 35.1] | 67.0 % | $647 [611, 682] | $1,958 | 7 | 9.9 | 67.0 % | MODELADO (WR = hipótesis; coincide con P($0): toda vida sin pago termina en liquidación) |
| 52.0 % | 38.6 % [35.4, 43.1] | 61.4 % | $911 [847, 1,003] | $2,357 | 7 | 11.5 | 61.4 % | MODELADO (WR = hipótesis; coincide con P($0): toda vida sin pago termina en liquidación) |
| 55.0 % | 49.8 % [45.8, 56.5] | 50.2 % | $1,905 [1,593, 2,410] | $3,822 | 7 | 17.8 | 50.2 % | MODELADO (WR = hipótesis; coincide con P($0): toda vida sin pago termina en liquidación) |

**P(activar la XFA tras pasar):** SUPUESTO = 100 % (decisión de Eric, $149 y un día de retraso manual); no es una probabilidad de mercado.

## Fila 8. Dependencia de régimen (ventana de oro 14-nov-2025 → 26-ene-2026), WR_dec = 50 % (sin deriva)

| días usados | cobrado medio por XFA | P(≥1 pago) | estado |
|---|---|---|---|
| todos (con la ventana de oro) (488 días) | $638 | 32.4 % | MEDIDO en esa ventana (régimen único) |
| sin la ventana de oro (W2) (443 días) | $647 | 33.0 % | MEDIDO en esa ventana (régimen único) |
| solo la ventana de oro (45 días) | $632 | 27.2 % | MEDIDO en esa ventana (régimen único) |

(La Parte D ya mostró que sin la contaminación de contratos la ventana de oro casi no mueve el pago por XFA; el régimen reciente —últimos 250 días limpios— da P(≥1 pago) ≈ 29 % frente a 36 % histórico.)

## Fila 7. Costos

| concepto | valor | N / fuente | estado |
|---|---|---|---|
| comisión round-turn MES / MNQ / M2K / MYM | $1.22 por contrato (todo incluido) | Help Center de Topstep, artículo de comisiones y tarifas, consultado 24-oct-2026 | MEDIDO (fuente primaria; sin fecha de vigencia en la página) |
| comisión round-turn MGC | $1.92 | ídem | MEDIDO (ídem) |
| reset del Combine / mensualidad | $49 / $49 al mes | Help Center, leído el 20-oct (RULEBOOK_XFA.md) | MEDIDO (fuente primaria) |
| activación de la XFA / pago por wire | $149 / $30 | ídem | MEDIDO |
| slippage de entrada MES | +1 y +3 ticks adversos (19 y 20-oct) | N = 2 | MEDIDO pero **sin información** (ver más abajo) |
| slippage de salida (SL, FLATTEN, liquidación) | 3 ticks asumidos | ninguna medición | **SUPUESTO / DESCONOCIDO** |

## Fila 9. Experiencia viva: ¿qué información hay?

- **MES real:** 8 resueltos (3 TP, 4 SL, 1 desconocido). Entre los 7 decididos, 3 TP: p̂ = 43 %, IC95 exacto de Clopper-Pearson [10, 82] %. El modelo dice P(TP | decidido) ≈ 55 %: P(X ≤ 3 de 7 | p = 0.55) = 39 % → **consistente con el modelo y con 30 %, 43 % o 60 %: no hay información.**
- **MGC Practice:** 3 sesiones (SL, FLATTEN, FLATTEN; 0 TP): 1 trade decidido. **Sin información.**
- **Cuántos trades decididos harían falta** (binomial exacta de una cola, α = 5 %, potencia 80 %): distinguir p = 0.55 de 0.50 → **620**; 0.55 de 0.45 → **154** (sin ajuste por esperar fallos); distinguir 50 % de 47.4 % → **2306**. A ≈ 1 trade por día hábil en MES (casi todos decididos) son ≈ 2.5 años para el primer caso; en MGC (44 % decididos) el doble o más.

## Dónde NO hay probabilidades (DESCONOCIDO): por qué, qué dato lo resolvería, costo y fecha estimada

| cantidad | por qué no se sabe hoy | qué dato lo resolvería | costo de obtenerlo | fecha estimada |
|---|---|---|---|---|
| **WR real de la estrategia (MES y MGC)** | 8 trades reales de MES (7 decididos) y 1 decidido en MGC Practice; el histórico de 2 años es un solo camino de precios (IC95 de WR_dec en MGC ±6.6 pp) | ≥ 620 trades decididos para distinguir 55 % de 50 %; ≥ 2,306 para 47.4 % de 50 % (binomial exacta, α 5 %, potencia 80 %) | tiempo: MES ≈ 1 decidido/día ⇒ **2.5 años** (620) o **≈ 9 años** (2,306); MGC (≈ 44 % decididos) el doble | **no hay forma rápida**; se decide con cotas (equilibrio 48.6 %), no con el WR medido |
| **Slippage de entrada: media, σ y parte sistemática vs aleatoria** | N = 2 (+1, +3 ticks) | C3 (parche listo) + exportación de fills de TopstepX cruzada con los `[OPEN]` | desplegar C3 (revisión humana) y 30–60 sesiones | ≈ **6–12 semanas** tras desplegar (hacia mediados de enero si se despliega el 27-oct); la exportación de TopstepX puede dar una primera lectura en **días** |
| **Slippage de salida y sobreimpulso de la liquidación por MLL** | ningún precio de salida real en el repo (el caso del 19-oct no está) | historial de operaciones de TopstepX (salida y hora) + `exec_exit` de C3 | 1–2 h de exportación | **días** |
| **TP: fills parciales o espera en cola** | sin detalle de fills | misma exportación | — | días |
| **Latencia real señal → orden → fill** | sin logs/timestamps del Pi en esta sesión | `~/glitch-logs/pi_executor.log` (19–23 oct) y C3 | minutos | días |
| **¿El Combine tiene DLL? ¿restricciones de noticias Tier 1 en el Combine?** | el artículo leído es de la XFA | ticket a Topstep o pantalla de la cuenta en TopstepX | 1 ticket | días |
| **Umbrales de RTP / «compras excesivas» / copia de la estrategia en varias cuentas** | no publicados | ticket a Topstep | 1 ticket | días–semanas |
| **Semántica de los brackets nativos (ticks desde el fill o desde otro precio; modo OCO elegible; efecto del rechazo con `errorCode 2`)** | la doc de ProjectX no lo dice | ensayo en Practice (una sesión) | bajo | **1 día** de Practice |
| **Régimen futuro de volatilidad del oro / FLATTEN** | no estacionario (FLATTEN 90 % → 28 % por bloques) | monitoreo de la fracción FLATTEN por bloque; no se puede «medir» el futuro | — | continuo |
| **Correlación entre resultados de cuentas / de dos productos** | solo existe la correlación de retornos de la ventana (MES–MGC 0.17, MES–MNQ 0.97) | un segundo producto en Practice ≥ 60 sesiones | medio | ≈ 3 meses |
| **Fiabilidad operativa de la cadena (Railway → Gist → Pi)** | un incidente documentado, sin tasa | registro de fallos con fecha desde el 21-oct | — | ≈ 3 meses |
| **P(activar la XFA tras pasar)** | decisión humana | — | — | SUPUESTO = 100 % |
| **Cierres de CME (26/27-nov, 24-dic); PPI, ISM, ventas minoristas** | no consultados en fuente primaria (las fuentes de terceros discrepan) | calendario de CME y de cada agencia | minutos | días |
| **Costos operativos de $714/año** | cifra heredada de la Parte D; no se verificó qué incluye | factura de Railway/datos | minutos | días |
