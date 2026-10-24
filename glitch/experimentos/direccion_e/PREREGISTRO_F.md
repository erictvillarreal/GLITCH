# PREREGISTRO_F — hipótesis nuevas de WR/valor (F4) — 24-oct-2026

**G0.** Este archivo se escribe y se commitea **antes de calcular cualquier resultado de F4**: ninguna de las cuatro hipótesis se ha corrido. Lo único conocido de antemano son los resultados de las Partes A–E y F1–F3 (equilibrio, valor por punto de WR, FLATTEN 56 %, deriva de volatilidad del oro, slippage). Parámetros FIJOS, sin barridos; cualquier cambio es una enmienda fechada al final. **Familia de comparaciones de F4 = 4** (Holm con α = 0.05 sobre las 4; independiente de la familia de 18 de la Parte E). Las pruebas con ~500 días intradía tienen IC95 de ±4.5 pp en proporciones y no detectan efectos de 1–2 pp: se dirá **«sin potencia»**, no «sin efecto».

**Medida común (salvo H3 y H4):** diferencia **pareada** contra el plan de hoy (3 micros, SL = TP = 364, stop 0.5, entrada 7:15 CT, flatten 14:30 CT) en (i) cobrado medio por XFA y (ii) neto anual por cuenta (cadena Combine → XFA, Combine hoy P0, mezcla de slip {1,3}, bancos ≥ 150,000, semilla fija), con IC95 por bootstrap de bloques de 5 días **sobre los 488 días** reales (≥ 300 remuestras de la historia, cada una con su banco); más (iii) el WR de equilibrio por interpolación en la malla de `f1_equilibrio_por_etapa.py` (plan de hoy: 48.3 % si la ventaja vive en la XFA). Las simulaciones asumen deriva 0 (martingala) salvo que la hipótesis diga lo contrario; el único dato direccional es el de `alternate` real (47.4 %), que no se usa para elegir parámetros.

## H1 — Geometría que reduce FLATTEN (barreras simétricas más cortas)
- **Mecanismo.** Con SL = TP = 364 el 56 % de los días terminan en FLATTEN (P&L continuo, media ≈ $0, desvío ≈ $420): son días «desperdiciados» para el contador de días ≥ $150 y para el MLL. Una barrera más cercana convierte una parte en TP/SL.
- **Qué cambia.** SL = TP = **300 ticks** (≈ 0.7 × el rango mediano del día, 423 ticks; el valor actual es 0.86×), nc = 3, todo lo demás igual. Un solo valor, sin barrido.
- **Predicción (dirección esperada y por qué).** FLATTEN baja a ≈ 45–50 %. **Se espera RECHAZO en valor**: la Parte D mostró que barreras cortas con 3 micros reparten pagos pequeños y *bajan* el cobrado (−$400 por XFA en los brackets de 100–150 ticks), y 728×3 (que sube FLATTEN) paga +$100. Se pre-registra para cerrarla, no porque se espere que gane.
- **Rechazo.** H1 se rechaza si el límite superior del IC95 de la diferencia pareada de cobrado por XFA es < 0, **o** si el WR de equilibrio sube a > 48.6 %. **Se acepta como candidata** solo si el límite inferior del IC95 > 0 con Holm (α/4) **y** el equilibrio ≤ 48.3 %.
- **Potencia.** Diferencias de cobrado de ≈ $50 (7 %) tienen EE de bootstrap ≈ $20–35 por la varianza de 488 días: detecta ≥ ~$70; efectos menores = «sin potencia».
- **Gates.** G1 (cargador limpio, parche `mgc_loader_contract_filter`), G2 (Holm sobre 4), G3 (neto anual adicional ≥ $500 con IC), G4 (paper en sombra ≥ 30 días + kill-switch + aprobación; requiere revisión humana, regla 4).

## H2 — Barreras escaladas por volatilidad (ATR) en lugar de ticks fijos
- **Mecanismo.** La volatilidad del oro no es estacionaria: la fracción de días TP/SL pasó de ≈ 10 % (primer bloque) a ≈ 72 % (último), y P(≥ 1 pago) del régimen reciente es 29 % vs 36 % histórico. Ticks fijos = geometría que cambia de significado con el régimen.
- **Qué cambia.** Para el día t: `W_t = round(k × R̄_{t−1})` ticks, con `R̄_{t−1}` = media de los 20 rangos diarios previos (máx − mín entre 7:15 y 14:30 CT, solo hasta t − 1), `k = 364 / mediana(R̄)` calibrado una vez sobre el historial completo (≈ 0.86; es una constante de calibración, no un resultado); SL = TP = W_t; `nc_t = max(1, min(6, round(3 × 364 / W_t)))` (riesgo en dólares ≈ constante); sujeto al plan de escalado de la XFA.
- **Predicción.** (a) La desviación estándar entre los 4 bloques cronológicos de la fracción TP/SL baja ≥ 30 % respecto a ticks fijos; (b) el cobrado por XFA en los **últimos 250 días** sube ≥ $50; (c) el cobrado sobre toda la historia no baja.
- **Rechazo.** Se rechaza si (a) no se cumple **o** el IC95 del cambio de cobrado en los últimos 250 días incluye 0 y la media < $50.
- **Potencia.** Un solo régimen reciente (≈ 250 días) y un solo cambio de nivel de volatilidad: la prueba es débil por construcción (efectivamente n de regímenes = 2). Se reportará como «sin potencia» si el IC es ancho. El estimador de ATR usa solo información previa (prueba de truncamiento en G1).
- **Gates.** Igual que H1, más G1 específico: la serie de `R̄` recalculada con la historia truncada en t − 1 debe coincidir.

## H3 — «No operar» / «operar solo» por calendario macro (cambia qué días entran, no la dirección)
- **Mecanismo.** En días con dato o FOMC la varianza intradía es mayor: más TP/SL y menos FLATTEN. Para el Combine (convexo, necesita varianza) podría convenir operar esos días; para la XFA (MLL), saltarlos.
- **Qué cambia.** Calendario **solo con fuente primaria verificada**: FOMC 2021–2026 (46 fechas, `federalreserve.gov`, ya en `fomc_dates.txt`; anuncio en convención 2:00 PM ET = 1:00 PM CT, **no verificado** en la página), más BEA (PIB/PCE) y BLS si se pueden bajar con fuente verificable. **Sin calendario completo la hipótesis se limita a FOMC.**
- **Predicción.** Cociente (rango de la sesión en día FOMC) / (rango en el resto) ≥ 1.15 en `^GSPC` 2021–2026 (n = 46 eventos, apertura→cierre); en la ventana real de 5 min solo hay 16 reuniones.
- **Rechazo.** El IC95 de bloques del log-cociente de rangos incluye 0 → se rechaza el mecanismo.
- **Potencia.** n = 46: EE del log-rango medio ≈ 0.06 → detecta ≥ ~0.15 (16 %) con 80 %; con n = 16 (ventana real) **sin potencia**. Corrección Holm α/4.
- **Gates.** G1 (fechas contra segunda fuente), G2, G3 (valor por días operados: ≈ 8 eventos/año ≈ 3 % de los días → el techo de valor es pequeño; si el neto adicional < $500/año se archiva aunque pase G2), G4.

## H4 — Ejecución: tolerancia / orden límite ‘marketable’ en la entrada (ligada a F3)
- **Mecanismo.** TP/SL se anclan a la referencia, no al fill: con ≥ 2 ticks adversos dos TP dejan de sumar $3,000 y P(pasar) cae de ≈ 29 % a ≈ 18–21 % (F3). Un tope de k ticks (si no llena, no se opera) trunca la distribución de slippage.
- **Qué cambia.** Primero **medir**: parche C3 (`ref_price`, `fill_price`, `slip_ticks`) durante ≥ 30 sesiones. Después, **una** regla: orden límite en `ref ± 1 tick` con vencimiento de 30 s; sin fill = sin operar.
- **Predicción.** La media del slippage adverso es ≥ 1.5 ticks **y** P(slip > 1) ≥ 0.4; en ese caso P(pasar) sube ≥ 5 pp (con el modelo M2 de F3).
- **Rechazo.** Si en 30 sesiones P(slip > 1) < 0.25 o la media < 1 tick, no se adopta (el acantilado casi no ocurre).
- **Potencia.** Con σ ≈ 2 ticks (**supuesto**, N = 2 hoy) el EE de la media con 30 sesiones es ≈ 0.37 ticks: distingue 1 de 2 ticks con ≈ 80 %; la proporción P(slip > 1) tiene IC de ±17 pp. Es un diseño de medición, no una prueba de ventaja.
- **Gates.** G1 (registro verificado contra TopstepX), G2 sobre la medición, G3 (valor con la distribución medida), G4 (cambia la forma de entrar con capital real: revisión humana).

## Enmiendas
(ninguna al momento de escribir)
