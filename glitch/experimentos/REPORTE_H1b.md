# REPORTE H1b — H1 rehecho con slippage empírico, costos A/B/C, H0-0 y el caso 728×3 — sábado 24-oct-2026

Rama `experimentos-research` (local; `git push` denegado: entregables en `auditoria_experimentos/`). **No se tocó `main`, el Pi, Railway ni credenciales; ningún parche está aplicado.** Reemplaza las cifras de la cascada y de «costos operativos» de `REPORTE_H.md` §1(b)(c) y §3. Fuentes revisadas: motor de las Partes A/D (`xfa/chain.py`, `preservacion/daydata.py::sim_day`, `xfa/worlds.py::drift_for_wr`), barras reales de 5 min (MGC 488 días, MES 492) y los números que dio Eric en el chat. **No** revisé el CSV de TopstepX, `geometry_*_log.json`, Telegram ni el Pi (esta sesión no los alcanza). Estados: MEDIDO / MODELADO / SUPUESTO / DESCONOCIDO.

## 1. Resumen (10 líneas)

1. **Con el slippage empírico de 7 observaciones el equilibrio de la cadena es 47.47 % (costos A $240) y 48.03 % (B $827)**; con la mezcla {1,3}: 48.05 % y 48.67 %. El WR_dec medido de MGC (47.4 %) queda **en el equilibrio, no por debajo**: el neto esperado a ese WR es ≈ $0 (MODELADO; el WR medido tiene IC95 [40.8, 54.2]). Las 7 observaciones (media +1.0, IC95 [−0.41, +2.41]) son **NO VERIFICADAS** (no las puedo rastrear a un CSV) y **N = 7 no distingue 0, 1 o 2 ticks**.
2. **Cascada nueva (costos A):** 47.47 → + finish-line 47.11 (−0.36 pp, +$480/año a WR 50 %) → + 728×3 46.47 (−0.63 pp) → + slip adverso acotado ≤ 1 tick (hipotético) 46.35. Con costos B: 48.03 → 47.65 → 46.92 → 46.78. **Se eliminó el paso «costos operativos → $0»** y ya no figura entre las palancas; los costos son escenario (A/B/C), no palanca.
3. **Escenario C (facturas):** el neto es lineal: cada **$100/año** de costos mueve el equilibrio **+0.10 pp** (equilibrio(C) = equilibrio(A) + (C − 240)/$1,038 pp). Pendiente: **las facturas**. **Pregunta abierta:** si la mensualidad de $49 ya está incluida en el reset de $49 por intento que usa el modelo, B **cuenta doble**.
4. **Con la finish-line el efecto baja de $972 a $480/año (< $500)** porque con el slippage empírico menos días caen en el escalón de +2/+3 ticks; con la mezcla {1,3} sigue siendo −0.79 pp. El resultado de la finish-line depende de una distribución de slippage con N = 7.
5. **G4b (API por cuenta):** a N = 5 los costos operativos son $936 (A) o $3,871 (B), no $714. El ingreso es lineal en N: hoy ≈ $2.6k/cuenta, con finish-line ≈ $3.2k, con finish-line + 728×3 ≈ $4.7k **a WR 50 %**; a WR 47.4 % el neto por cuenta es ≈ $0, así que añadir cuentas **multiplica el riesgo sin multiplicar el neto esperado**. ρ entre cuentas **supuesto**.
6. **H0-0 (MGC `alternate`, 488 días):** P&L neto medio por sesión **−$48** [−117, +26]; **43 %** de las sesiones ≥ +$150 netos (51 % de ellas FLATTEN) y 43 % ≤ −$150; WR_dec 47.4 %, WR_todos 20.9 %, WR_signo 50.0 %, WR_pnl 49.2 %. **MES** (492 días): +$54 [−106, +190]; WR_dec = WR_todos = WR_pnl = 58.0 % (LARGO 52.8 %), WR_signo 51.2 %. Tablas completas en §4.
7. **728×3 — el WR NO se remidió con esa geometría.** El eje «WR» de H1 es una etiqueta: la deriva se calibra una vez con el bracket nominal 364/364 (`drift_for_wr(..., sl=364, tp=364)`, 1 contrato, sin MLL) y se aplica a la geometría evaluada. Remedido por sesión con colchón $2,000, el WR_dec de 3×728 es **≈ 4–5 pp menor** que la etiqueta a la misma deriva (liquidación a 667 < TP 728): ese WR no es comparable con el de 3×364.
8. **Por qué baja el equilibrio, entonces:** no es simetría (TP 728 / SL 667 ≈ 728 / 728) ni puntería ni «cosecha de deriva» (el efecto existe a deriva 0: $824 vs $647 cobrado por XFA). Es **estructura de pagos**: pago medio sube de $1,235 a $1,519 (primer pago $1,051 → $1,335) con P(≥ 1 pago) menor (33.0 → 28.1 %). Una sola sesión ganadora (≈ $2,178) fija el piso del MLL en $0.
9. **Reconciliación de 0.72 / 0.67 / 0.63 / 0.50 pp:** 0.72 = paso de la cascada H1 (mezcla {1,3}, costos $714, después de la finish-line); 0.67 = componente aislado en H1b (empírica, A); 0.63 = paso de la cascada H1b; 0.50 = rejilla de z de H1c (resolución ± 0.2 pp, convención distinta). Son la misma cantidad medida de cuatro maneras: **entre 0.5 y 0.8 pp, no 0.72 exacto**.
10. **NO VERIFICADO / pendiente:** las 7 observaciones de slippage (fecha, lado, tamaño); los montos A/B (de Eric, sin factura); el escenario C; el doble conteo de B; ρ entre cuentas; IC de H0 con 20 remuestras; no cruzé las sesiones vivas (8 de MES, 3 de MGC) con el motor por falta del CSV de TopstepX.

## 2. H1b — equilibrio, componentes y cascada (`direccion_e/resultados_H1b.md`, `cascada_H1b.svg`, `h1b_rehacer.py`)

Slippage de entrada del Combine: distribución empírica {−1: 1/7, 0: 2/7, +1: 2/7, +3: 2/7} (modelo M2: costo de ejecución; una realización por día). Sensibilidad: mezcla {1,3} 50/50.

| slippage del Combine | costos | equilibrio de la cadena | neto/año a WR 50 % | valor de 1 pp |
|---|---|---|---|---|
| empírica-7 | A $240 | **47.47 %** | $2,629 | $1,038 |
| empírica-7 | B $827 | **48.03 %** | $2,042 | $1,038 |
| mezcla {1,3} | A | 48.05 % | $1,839 | $945 |
| mezcla {1,3} | B | 48.67 % | $1,252 | $945 |

Cascada (costos A / B): hoy 47.47 / 48.03 → + finish-line 47.11 / 47.65 → + 728×3 46.47 / 46.92 → + slip ≤ 1 tick (hipotético) 46.35 / 46.78. Primer paso por debajo del WR medido (47.4 %): con A, la finish-line; con B, el 728×3. Por debajo de 46.5 %: con A, el 728×3; con B, ninguno.

**Componentes aislados (Δ$/año a WR 50 %, costos A, en orden de tamaño):** 728×3 +$1,476; reset $49 → $0 y activación $149 → $0 son cotas teóricas (+$2,351 / +$1,771; no son palancas: las tarifas las fija Topstep); stop exacto en lugar de 0.5 +$828; slip de entrada del Combine 0 ticks fijos +$744; slip acotado ≤ 1 (hipotético) +$699; 4→1 micros +$627; finish-line +$480; comisión MES a $0 +$535 (cota teórica). Ningún costo operativo figura como palanca.

## 3. G4b — escala con API por cuenta (`direccion_e/resultados_G4b.md`, `g4_ops_por_cuenta.py`)

Costos: A = $66 compartidos + $174 × N; B = $66 + ($174 + $587) × N. Ingreso esperado **a WR 50 %** (etiqueta), una realización por cuenta con cópula gaussiana de ρ supuesto.

| N | hoy A (ρ=0.5) | + finish-line A | + finish-line + 728×3 A | P(total < 0), hoy, ρ=0.5 | P(todas pierden), hoy, ρ=0.5 | costos A / B |
|---|---|---|---|---|---|---|
| 1 | $2,639 | $3,153 | $4,702 | 32 % | 32 % | $240 / $827 |
| 3 | $8,184 | $9,561 | $14,234 | 25 % | 11 % | $588 / $2,349 |
| 5 | $13,572 | $16,134 | $23,764 | 23 % | 6 % | $936 / $3,871 |

Lectura: el ingreso crece ≈ linealmente; lo que cambia con N es la dispersión. **Advertencia:** estas cifras valen a WR 50 %, que **no es el medido** (47.4 %); a ese WR el neto por cuenta es ≈ $0 con costos A y negativo con B. Sensibilidad con la mezcla {1,3}: la cuenta rinde menos en $0.76k (hoy), $0.29k (finish-line) y $0.36k (finish-line + 728×3). ρ entre cuentas: **supuesto**; el ρ de retornos MES–MGC medido (0.17) no es el de resultados. Mismos trades en todas las cuentas es el patrón que Topstep cita para RTP.

## 4. H0-0 — P&L neto por sesión y definiciones de WR (`direccion_e/resultados_H1c.md`, parte 1, `h1c_728_h00.py`)

Fuente: barras reales de 5 min con el motor (`sim_day`); MODELADO sobre historia real, **no** son las sesiones vivas. Neto de comisión (MGC $1.92, MES $1.22 por contrato round-turn). Cinco medidas:
- **WR_dec = TP/(TP+SL+LIQ)**: FLATTEN fuera del denominador (la del modelo de valor).
- **WR_todos = TP/n**: FLATTEN cuenta como no ganador.
- **WR_signo**: P(cierre del flatten > referencia en el lado jugado): exactitud de dirección.
- **WR_pnl**: sesiones con P&L neto > 0 / sesiones con P&L ≠ 0.
- **Días ≥ +$150 netos**: lo que importa para el pago de la XFA Standard (5 días no consecutivos).

**MGC 3 micros, 364/364, 7:15 → 14:30 CT, slip 0**

| regla | n | P&L neto/sesión [IC95] | desvío | ≥ +$150 (FLATTEN) | ≤ −$150 | WR_dec | WR_todos | WR_signo | WR_pnl |
|---|---|---|---|---|---|---|---|---|---|
| alternate | 488 | −$47.9 [−117, +26] | $826 | 43.0 % (51 %) | 43.2 % | 47.4 % | 20.9 % | 50.0 % | 49.2 % |
| siempre LARGO | 488 | −$33.6 [−99, +37] | $832 | 44.9 % (55 %) | 41.6 % | 46.0 % | 20.3 % | 52.5 % | 50.8 % |
| siempre CORTO | 488 | −$19.7 [−86, +43] | $814 | 41.4 % (43 %) | 45.3 % | 54.0 % | 23.8 % | 47.5 % | 48.8 % |

**MES nc 40, TP 32, liquidación por MLL a 40 ticks, 9:35 → 14:30 CT**

| regla | slip | n | P&L neto/sesión [IC95] | ≥ +$150 | WR_dec = WR_todos = WR_pnl | WR_signo |
|---|---|---|---|---|---|---|
| alternate | 0 | 492 | +$54.3 [−106, +190] | 57.7 % | 58.0 % | 51.2 % |
| LARGO | 0 | 492 | −$123.3 [−282, +35] | 52.8 % | 52.8 % | 55.1 % |
| CORTO | 0 | 492 | +$18.2 [−122, +167] | 56.7 % | 56.9 % | 44.9 % |
| alternate | 1 | 492 | +$3.8 [−157, +139] | 57.1 % | 57.3 % | 51.2 % |

Lectura: la sesión media de MGC pierde ≈ $48 con IC que incluye 0 (con stop exacto, ≈ $20 mejor); la de MES es binaria (+$1,551 / −$2,000); WR_signo ≈ 50 % con `alternate` en ambas: **no hay información de dirección**. Un tick de slippage resta ≈ $50 por sesión de MES. (MES con `alternate`: WR_dec 58.0 % aquí frente a 52.8 % en `LARGO`; la diferencia es el lado que cae, no señal, y no es comparable con el 43 % [10, 82] de 7 decididos reales.)

## 5. 728×3: ¿se remidió el WR? y por qué baja el equilibrio (`resultados_H1c.md`, parte 2)

**No se remidió.** En H1, E §4, F1, G4 y H6 §3 el WR es una etiqueta de deriva calibrada en el bracket nominal 364/364. «Equilibrio 728×3 = 46.97 %» significa «la deriva equivalente a 46.97 % en un bracket 364 nominal». Remedido por sesión (443 días reales, a la misma deriva):

| etiqueta | 3×364 (colchón $2,000) | 3×728 nominal | 3×728 colchón $2,000 | 3×728 colchón $2,178 |
|---|---|---|---|---|
| 47.4 % | 47.5 % | 46.8 % | **42.1 %** | 46.8 % |
| 50.0 % | 50.0 % | 50.0 % | **45.2 %** | 50.0 % |

En 3×364 la etiqueta se cumple (la liquidación a 667 ticks no toca el bracket de 364). En 3×728 el WR por sesión con el colchón inicial es 4–5 pp menor (martingala: 667/(667+728) = 47.8 % antes de efectos de tiempo) y vuelve a ≈ la etiqueta tras el primer TP (liquidación a ≈ 726). Sólo ≈ 14 % de las sesiones son decididas ⇒ ± 4–5 pp de ruido.

**Respuesta a la pregunta («stop ≈ 667 y TP 728 casi simétricos»):** correcto, y justo por eso la simetría **no** explica el efecto. Geometrías contrafactuales a la misma deriva (etiqueta 50 %): cobrado por XFA TP 364/SL 364 $647 → 546/546 $728 → 667/667 $804 → 728/667 $820 → 728/728 $824; el efecto es monótono y 728/667 ≈ 728/728. Existe **a deriva 0**, así que no es puntería ni cosecha de deriva.

**El mecanismo (lo que muestran las cifras; la causa dentro del motor no se aisló con un experimento de apagado):** con 3×728 cada sesión ganadora suma ≈ $2,178 (en vez de ≈ $1,092) y la cuenta llega a ser elegible con más saldo (mecanismo inferido de las cifras); el 50 % retirable (tope $2,000) sube: **primer pago $1,051 → $1,335, pago medio $1,235 → $1,519**, con la misma fracción de vidas con ≥ 2 pagos (10.1 vs 10.3 %). A cambio P(≥ 1 pago) baja 33.0 → 28.1 %, las decididas por vida caen de ≈ 3.5 a ≈ 0.9 y los FLATTEN suben de 5.4 a 8.8. Además un TP de $2,178 supera los +$2,000 que bloquean el piso del MLL en $0 (en 3×364 hacen falta dos TP).

**Medida comparable entre geometrías (deriva z* con neto = 0, costos A, slippage empírico):** 3×364 z* = −0.070 (etiqueta 47.47 %); 3×728 z* = −0.084 (46.97 %). WR_dec remedido en z*: 47.47 % vs 41.67 % (colchón $2,000) / 45.45 % ($2,178). **Entonces 728×3 baja la *deriva* necesaria, no un WR operativo comparable.** En 3×728 el WR_dec de equilibrio remedido es más bajo (41.7 % con colchón $2,000), pero el WR_dec a deriva 0 de esa geometría también es 4–5 pp menor que el de 3×364 (45.2 % vs 50 %): el WR_dec de 3×728 y el de 3×364 **no son comparables**; la comparación válida es la deriva (z* −0.084 vs −0.070). Por esto el «equilibrio baja a 46.5 % con 728×3» **no se puede contrastar** con el 47.4 % medido en 364/364: para hacerlo hay que medir WR_dec *con la geometría 728×3* (≈ 14 % de sesiones decididas ⇒ aún más lento que los ≈ 2.3k decididos que ya exige distinguir 47.4 de 50 %).

## 6. Confianza y correcciones

- **Finish-line:** antes **ALTA** (≥ $500 en todos los escenarios de WR); con el slippage empírico de 7 obs. el efecto es **+$480 a WR 50 %** y −0.36 pp: **MEDIA**, porque depende de que el slippage no caiga en el escalón de +2/+3 ticks (la mezcla {1,3} da −0.79 pp).
- **728×3:** **ALTA** de que mejore el neto *en el modelo* (+$1,476, −0.63 a −0.67 pp); incertidumbre de reglas (RTP / «conducta prohibida») y de WR operativo remedido (4–6 pp menor al inicio).
- **Costos operativos:** ya no son palanca; el efecto de cualquier costo C es lineal (+0.10 pp por $100/año). **DESCONOCIDO** hasta tener las facturas.
- **Correcciones a `REPORTE_H.md`:** (a) cascada y top-5 reescritos (sin «costos → $0»); (b) «slippage medido N = 2» pasa a N = 7 NO VERIFICADO; (c) «ALTA» de costos y de finish-line corregidas (finish-line pasa a MEDIA); (d) la explicación del −0.72 pp de 728×3 (§1(b)) era incompleta: no medía WR con esa geometría.

## 7. Reproducibilidad

Desde `experimentos/direccion_e/` con semillas fijas: `python3 h1b_rehacer.py` (→ `resultados_H1b.md`, `cascada_H1b.svg`), `python3 g4_ops_por_cuenta.py` (→ `resultados_G4b.md`), `python3 h1c_728_h00.py` (→ `resultados_H1c.md`). Archivos sin auditar por Eric: marcar NO AUDITADOS hasta su lectura.
