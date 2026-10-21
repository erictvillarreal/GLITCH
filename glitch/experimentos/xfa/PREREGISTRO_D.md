# PREREGISTRO_D — etapa fondeada (XFA 50K) y auditoría de Cerebro 2 — 20-oct-2026 (noche)

Se commitea **antes** de correr cualquier resultado comparativo. Ya existen, antes de este registro: (i) la regresión del `xfa_engine` contra el motor publicado (`regress_lever.txt`: $618 vs $616–620, P(≥1) 0.317 vs 0.316) y (ii) un hallazgo de datos (el archivo MGC intercala barras de dos contratos: ver `EVIDENCIA_CEREBRO2.md`), medido solo como fracción de días TP/SL/FLATTEN de un bracket de 364 ticks (contaminada 25.2/25.2/49.6 %, limpia 22.0/22.0/55.9 %). Nada más se había calculado.

## 1. Mundos (trayectorias)
- **W1** MGC *limpio* (contrato dominante del día = mayor volumen), **CON** la ventana de oro 14-nov-2025 → 26-ene-2026. 488 días.
- **W2** MGC limpio **SIN** esa ventana. **Mundo primario del veredicto junto con W3** (la ventana concentra el nivel de la historia).
- **W3** Browniano sin deriva calibrado a la volatilidad y al perfil intradía de W1 (σ y lognormal por día por método de momentos contra P(TP-primero), P(SL-primero) y P(FLATTEN) de un bracket de 364 ticks). **Sin deriva a favor.**
- **W4** Pesimista: días binarios con WR 45 % (TP vs SL, SL = TP) entre los días decididos, con la fracción de días decididos y el P&L de los FLATTEN tomados de W2. (WR 50 % = caso base sin deriva.)
- **W0** (solo auditoría): MGC *contaminado* como lo cargaba el código previo (todas las barras del día sin mirar el contrato).
- MES (competidor d): serie de la Parte A (492 días), referencia 9:30 CT.

## 2. Reglas (escenario base = VERIFICADO del RULEBOOK; lo ambiguo se barre)
Base: MLL $2,000 con piso → $0 al llegar a +$2,000 y tras el primer pago; liquidación en tiempo real; día ganador ≥ $150 **neto**; 5 días; 50 % del saldo, tope $2,000, mínimo $125; 90/10; desde el 2º pago ganancia ≥ $0.01; escalado 20/30/50 micros (MGC 12/18/31); sin DLL; ruta **Standard**; sin beneficio de $10k; sin comisión de transferencia; el pago se solicita al cierre del día (el día del pago no cuenta).
Escenarios (cada uno cambia **una** regla): **C** ruta Consistency (40 %, 3 días, tope $3,000); **R1** RTP (DLL $1,000 + ruta Consistency); **F1** primeros $10k al 100 %; **T30** comisión de transferencia $30 por pago; **P2** saldo mínimo $1,500 para pedir; **W2** día ganador bruto; **D4** tope $4,000 (DLL comprado; Standard).

## 3. Entrada de Cerebro 2 y fricción
MGC, referencia = close de la barra 7:15 CT (primera barra con inicio ≥ 7:13), TP/SL desde la **referencia**, flatten 14:30 CT, lado alternado, comisión $1.92/contrato, $1/tick. Slippage de entrada de MGC **NO medido**: se reportan 0 y 3 ticks (supuesto) y la sensibilidad.

## 4. Candidatos (mismo motor, mismas reglas, mismos mundos)
- **a** plan actual: 3 micros, SL = TP = 364, pago al máximo.
- **b** “728×3”: 3 micros, SL nominal = TP = 728 (el SL efectivo es el **piso**: liquida antes del stop mientras el colchón < $2,184).
- **c** 1 micro los primeros 5 días operados, luego 3 (plan a).
- **d** MES micros: 3 contratos, SL = TP = 291 ticks (≈ $1,092 de riesgo, igual que a).
- **e1** TP corto/SL ancho: 3 micros, TP = 60, SL = 364. **e2** 3 micros, TP = 70, SL = 250.
- **f** *payout-first*: 3 micros, pasando a 1 micro cuando llevan ≥ 4 días ganadores y volviendo a 3 tras el pago.
- Heurísticas de cobro sobre *a*: **H4a** pago al máximo (base) · **H4b** pago al mínimo ($125).
- **H6** no operar el día siguiente a un rango de apertura bajo (rango de la barra 7:00–7:15 del día previo < percentil 25 de los 60 días anteriores): variante de *a*.
- **Re-optimización 50K** (hallazgo 1 de la auditoría): rejilla nc ∈ {1,2,3,4,5,6,8} × SL = TP ∈ {150, 200, 250, 300, 364, 450, 550, 728}. Selección con la **primera mitad** cronológica de los días y evaluación en la **segunda** (y viceversa); se declara que son 56 comparaciones.
- **Óptimo de (tamaño, cobro)** por programación dinámica sobre W2 (estado reducido: ver REPORTE_D) y validación por Monte Carlo.

## 5. Métricas y criterios
Por candidato y mundo, 50,000 vidas de XFA, semilla 20261020 (misma semilla de trayectorias entre candidatos = comparación pareada), máx. 756 días: P(≥1 pago), P($0 en la vida), media/mediana/p10/p90 de lo **cobrado al trader**, días al primer pago, P(perder la XFA antes del primer pago), nº esperado de pagos, vida media. **Neto por XFA** = media cobrada − costo de obtenerla, con costo = $49/P(pase) + $149 y P(pase) ∈ {0.30 (slip ≤ 1), 0.17 (slip ≥ 2), 0.20 (mezcla)} (de la Parte A / C1); **neto anual** = neto por XFA × XFA por año (252 / (días esperados hasta pasar + vida de la XFA)).
**Veredicto (criterio fijado):** “Cerebro 2 es la mejor opción para la 50K bajo el escenario de reglas X” si **ningún** competidor tiene una media cobrada mayor con límite inferior del IC95 % de la diferencia pareada > 0 **en W2 y en W3 a la vez**; en caso contrario “no es”, con el ganador. Diferencias en W1 se reportan como informativas (contiene la ventana ganadora). **Cualquier resultado que dependa de W1 y no de W2/W3 se rotula “dependiente de la ventana”.**
**Pruebas obligatorias antes de reportar:** reproducir $620 / 31.6 % (hecho) y mostrar por qué difiere de `engine_real` p50 $3,532 (convenciones, ver inventario).
