# resultados_H0 (parte 2) — XFA por WR, régimen, costos y experiencia viva

XFA 3 micros, SL = TP = 364, stop 0.5, reglas oficiales verificadas (20-oct), sin RTP; **la ventaja se impone con una deriva calibrada para fijar WR_dec** (MODELADO: el WR real de cada escenario es una hipótesis, no un dato). IC95: 20 remuestras de bloques de 5 días de la historia limpia (W2 = sin la ventana de oro, 443 días), bancos de 5,000; punto: 40,000 vidas.

## Fila 6. Vida de la XFA por escenario de WR (W2)

| WR_dec | P(≥1 pago) | P($0 en la vida) | cobrado medio por XFA | pago medio (si cobra) | días de trading al 1.er pago (mediana) | vida media (días) | P(perderla antes del 1.er pago) | estado |
|---|---|---|---|---|---|---|---|---|
| 45.0 % | 18.0 % [16.5, 19.4] | 82.0 % | $244 [201, 290] | $1,352 | 8 | 7.2 | 82.0 % | MODELADO (WR = hipótesis) |
| 47.4 % | 25.7 % [23.3, 28.7] | 74.3 % | $406 [370, 446] | $1,580 | 7 | 8.4 | 74.3 % | MODELADO (WR = hipótesis) |
| 48.5 % | 29.9 % [27.7, 31.6] | 70.1 % | $508 [461, 553] | $1,699 | 7 | 9.0 | 70.1 % | MODELADO (WR = hipótesis) |
| 50.0 % | 33.0 % [31.0, 35.6] | 67.0 % | $647 [603, 684] | $1,958 | 7 | 9.9 | 67.0 % | MODELADO (WR = hipótesis) |
| 52.0 % | 38.6 % [35.9, 42.7] | 61.4 % | $911 [844, 1,028] | $2,357 | 7 | 11.5 | 61.4 % | MODELADO (WR = hipótesis) |
| 55.0 % | 49.8 % [45.2, 56.7] | 50.2 % | $1,905 [1,649, 2,436] | $3,822 | 7 | 17.8 | 50.2 % | MODELADO (WR = hipótesis) |

**P(activar la XFA tras pasar):** SUPUESTO = 100 % (decisión de Eric, $149 y un día de retraso manual); no es una probabilidad de mercado.

## Fila 8. Dependencia de régimen (ventana de oro 14-nov-2025 → 26-ene-2026), WR_dec = 50 % (sin deriva) y con el WR observado de `alternate`

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