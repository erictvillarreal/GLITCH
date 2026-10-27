# J5 — Parte H pendiente: estado y lo que faltaba

Lunes 26-oct-2026 · BORRADOR. Cada punto remite al archivo donde está el detalle; lo único calculado hoy es el intervalo del «+$206».

| pendiente de J5 | estado | dónde | resultado en una línea |
|---|---|---|---|
| **H0-0** (P&L neto por sesión y las definiciones de WR) | **hecho el 24-oct**; en J8 se repite **para cada candidata XFA** (3×364, 3×728, 1 micro, 4 micros, flatten 13:30/12:00/10:30; alternate histórico, LARGO, CORTO, promedio L/C) | `direccion_e/resultados_H1c.md` (Parte 1), `parteJ/resultados_J8.md` (A), `REPORTE_H1b.md` §4 | MGC `alternate` 3×364: **−$48/sesión [−114, +28]**, WR_dec 47.4 %, WR_todos 20.9 %, WR_signo 50.0 %, WR_pnl 49.2 %, 43 % de sesiones ≥ +$150. Es la config XFA, no la del Combine (J8 §2) |
| **Rerun de H1 con slippage empírico** | **hecho el 24-oct** con 7 observaciones (`REPORTE_H1b.md`); en J3/J8/J5 se usan 8 (la 8.ª inferida = 0, NO VERIFICADA) | `direccion_e/resultados_H1b.md`, `cascada_H1b.svg` | equilibrio de la cadena 47.47 % (costos A $240) / 48.03 % (B $827) |
| **Escenarios OPS** | **hecho el 24-oct** (A $240, B $827, C = facturas pendientes); desde J usamos la base **$245/año** | `REPORTE_H1b.md` §2, `resultados_G4b.md` | cada $100/año de costos mueve el equilibrio +0.10 pp; «costos → $0» se quitó de la cascada |
| **Caída del equilibrio con 728×3 y si el WR se remidió** | **hecho el 24-oct**: el WR **no** se remidió (el eje es una etiqueta calibrada en 364/364); remedido por sesión es 4–6 pp menor y no comparable; la caída (0.5–0.8 pp según el método) viene de la estructura de pagos | `REPORTE_H1b.md` §5, `resultados_H1c.md` (Parte 2) | primer pago $1,051 → $1,335; el efecto existe a deriva 0 y no depende de la simetría 667/728 |
| **Intervalo del «+$206»** | **hecho hoy** | `parteJ/resultados_J5.md`, `j5_intervalo_206.py` | ver abajo |
| **Corrección H4 (≈ 80 % abierto a las 13:00)** | **corregido hoy**: 57.8 % | `J8_PRIMER_DIA_XFA.md` §6, `h4_noticias.py` | error del script (ignoraba el SL de 364) |

## El «+$206» con intervalo

El «+$206» (H6 §2.5) era el neto anual por cuenta de **finish-line + 728×3 a WR 47.4 %** con slippage {1,3} y OPS $714, **sin intervalo**. Rehecho con slippage empírico de 8 observaciones y OPS $245 (bloques de 5 días, 30 remuestras de 30,000 vidas; diferencias pareadas con «hoy»):

| neto anual por cuenta | WR 47.4 % (≈ el medido) | WR 50 % |
|---|---|---|
| hoy (Combine P0 nc 40, XFA 3×364) | **−$145 [−356, +319]** | $2,543 [2,336, 2,939] |
| + finish-line | $188 [−9, +701] | $2,981 [2,786, 3,417] |
| P0 + 728×3 | $319 [+96, +991] | $4,051 [3,836, 4,563] |
| **finish-line + 728×3** | **$702 [+470, +1,421]** | $4,585 [4,372, 5,098] |

Diferencias pareadas frente a «hoy» a WR 47.4 %: finish-line **+$334 [+319, +385]**; 728×3 **+$464 [+106, +952]**; finish-line + 728×3 **+$848 [+488, +1,354]** (todas con IC que excluye 0).

**Lectura sin adornos:** (i) el «+$206» no era robusto ni en signo ni en tamaño: con otros supuestos de costos y slippage el mismo escenario da ≈ **$702** y la parte de la mejora respecto de «hoy» es **+$848**; (ii) **«hoy» a WR 47.4 % es −$145 [−356, +319]: el IC incluye 0 y no se puede decir que sea positivo**; (iii) el IC solo cuenta la incertidumbre del conjunto de días históricos y el ruido de simulación (las remuestras entre corridas difieren en ≈ ±$100: la corrida de J4-a dio −$244 para «hoy» con otra semilla de bancos), **no** el WR verdadero (47.4 vs 50 mueve el neto de −$145 a $2,543), **no** la distribución real de slippage (N = 8, sin CSV) y **no** el significado de «WR» con 728×3 (etiqueta); (iv) finish-line y 728×3 son parches NO aplicados; 728×3 toca RTP/conducta (J3).
