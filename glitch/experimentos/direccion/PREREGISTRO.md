# PREREGISTRO — Parte B (dirección práctica) — 20-oct-2026

Este archivo se commitea ANTES de calcular cualquier resultado de la Parte B. Las secciones
de abajo son copia literal de §3 de `experimentos/ENCARGO_20oct2026.md` (líneas 102–139 del
encargo original). Cualquier cambio posterior va como ENMIENDA fechada al final de este
archivo; se reportan ambas versiones.

Estado al momento del registro: NO se ha corrido ningún cálculo de la Parte B (ni descriptivo
ni de reglas). Datos disponibles localmente: `glitch/data_cache/mes_5min_2y.parquet`
(2024-08-26 → 2026-08-25, barras de 5 min RTH). Cobertura posterior al 25-ago-2026: no
disponible localmente (ver REPORTE_B, "lectura de hoy").

---

## 3. PARTE B — Dirección práctica ("¿long o short hoy?" sin arbitrariedad)

### 3.1 Enfoque (distinto al de edge cuantitativo)
Eric NO pide un modelo alfa. Pide una regla simple, explicable, que diga **de qué lado operar según el régimen**, y usar el rally si existe. La pregunta práctica es: *¿qué lado tiene más probabilidad de tocar el TP de 32 ticks antes que el SL de 100 / la liquidación, dado el régimen de ayer?* Se mide con la mecánica real del engine, no con retornos genéricos.

Contexto honesto (no negociable en el reporte): más de 1,800 configuraciones previas no hallaron ventaja de dirección; en MGC una ventana de oro (nov-2025 a ene-2026) domina el nivel. Y "longs ganan, shorts pierden" en 8 sesiones es anecdótico (p≈0.14, alternancia por paridad confunde día con lado). Esta parte busca si el régimen (deriva alcista) aporta algo **usable**, y deja claro cuándo solo es deriva.

### 3.2 Datos (en este orden; documentar qué se usó)
1. Velas de TopstepX/ProjectX vía API (histórico disponible para MES y MGC); 2. los CSV/JSON de experimentos previos (serie MES de 515 días y MGC 7:13); 3. Yahoo Finance del contrato operado **solo** si lo anterior no alcanza (marcar como menor calidad). Reportar cobertura y huecos.

### 3.3 Medida base (contrafactual por día)
Para cada día, con la mecánica EXACTA del engine (referencia, slippage empírico, TP 32, SL 100, flatten 14:30 CT; piso MLL de 40 ticks a 40 contratos como evento aparte), simular **ambos lados** sobre la misma trayectoria: resultado LONG y resultado SHORT ∈ {TP, SL, LIQ, FLATTEN, ticks}. Métricas: P(TP-primero), P(liq), ticks medios netos de fricciones.

### 3.4 Reglas candidatas (máximo 3, parámetros FIJOS desde ya, solo información disponible antes de la señal)
- **R1 — Tendencia simple:** cierre de ayer > SMA20 de cierres diarios → LONG; si no → SHORT.
- **R2 — Sesgo largo con baja confirmada:** LONG, salvo que (cierre de ayer < SMA20 y SMA20 < SMA50) → SHORT.
- **R3 — R2 con día saltado:** igual a R2, pero si el cierre de ayer está a menos de 0.5×ATR14 de la SMA20 → NO OPERAR (esperar casi no cuesta; ver §2.4).
Controles: `alternate` (producción), siempre LONG, siempre SHORT, aleatorio (semilla, ≥1,000 corridas). Referencia informativa (no candidato): oráculo.
Sin ajuste de parámetros (sin barrido): calentamiento de 50 días y evaluación **walk-forward** (solo pasado disponible en cada fecha).

### 3.5 Criterios (fijados ahora, no se modifican después)
- **D1 (descriptivo, obligatorio):** asimetría LONG vs SHORT en P(TP-primero) por bloque (10 bloques consecutivos de igual tamaño), con y sin la ventana dominante; y la **misma tabla para las 8 sesiones en vivo** como anécdota (n pequeña, así se rotula).
- **D2 (candidata a paper-forward):** una regla pasa solo si (a) supera a `alternate` en ≥ 7 de 10 bloques, (b) la diferencia de P(TP-primero) vs `alternate` tiene IC bootstrap pareado (bloques de 5 días) al 98.3% (Bonferroni 0.05/3) estrictamente > 0, (c) no pierde contra "siempre LONG" en más de 3 de 10 bloques (debe aportar protección, no solo deriva), y (d) excluida la ventana dominante, la diferencia no es negativa.
- Si ninguna regla pasa D2: veredicto "no hay base para elegir lado; seguir con `alternate` o con el criterio de menor riesgo operativo". Un resultado negativo es un resultado válido.
- Si todas las ganancias vienen de un solo régimen/ventana: etiquetar "dependiente de régimen" y reportar qué pasa cuando el régimen se invierte (comportamiento de la regla en las caídas de la serie).

### 3.6 Puente con la Parte A
Con las tasas de TP-primero medidas de cada regla (y del control), correr el simulador de la Parte A para traducir "ventaja direccional" a **P(pase del Combine) y a costo esperado por pase**. Esa es la métrica que decide si importa.

### 3.7 Lectura de hoy (informativa, NO se aplica)
Calcular dónde está MES respecto a SMA20/SMA50 al cierre del 20-oct y qué diría cada regla para el 21-oct. Producción para mañana sigue siendo SHORT por paridad.

### 3.8 Camino a producción (si alguna regla pasa D2)
Solo **paper forward en sombra ≥ 30 días hábiles** (registrar qué haría la regla sin ordenar nada, comparar contra lo ejecutado), con kill-switch automático que vuelva a `alternate` si el régimen se invierte. Después, Eric decide. Entregar el diseño de logging en sombra como patch NO desplegado, con tests.

### 3.9 Entregables Parte B
`experimentos/direccion/`: `PREREGISTRO.md` (commit ANTES de resultados), código, `REPORTE_B.md` (D1, D2 por regla, sensibilidad a la ventana dominante, puente a P(pase), lectura de hoy) y tablas por bloque.


---

## Registro de enmiendas

### Enmienda 1 — 20-oct-2026, ANTES de calcular cualquier resultado de reglas (aclaraciones operativas que el texto no define)
Ningún P(TP-primero), ninguna regla, ningún control ni ningún bloque se ha calculado al escribir esto. Lo que falta definir
(y que NO cambia ningún criterio D1/D2, solo fija cómo se mide):

1. **Serie diaria.** A partir de `mes_5min_2y.parquet` (barras de 5 min RTH, hora CT): cierre diario = close de la última barra RTH;
   high/low diarios = extremos RTH. Los 8 cambios de contrato (MESU4→…→MESU6) introducen saltos de carry de +30 a +150 puntos que NO son
   movimiento de mercado: el cambio diario del cierre ajustado es `close_t − close_{t−1}` si el contrato no cambió, y `close_t − open_t`
   (dentro del día) el día del roll. SMA20/SMA50/ATR14 se calculan sobre esa serie ajustada (suma acumulada de cambios). ATR14 = media simple
   de 14 rangos verdaderos (TR = max(H−L, |H−C_prev|, |L−C_prev|); el día del roll TR = H−L).
2. **Información disponible.** Para decidir el día d solo se usan días < d (cierre de ayer = cierre ajustado del día hábil previo de la muestra).
   Calentamiento: los primeros 50 días de la muestra no se evalúan.
3. **Medida base.** Para cada día de evaluación y cada lado se usa `daydata.sim_day` con nc=40, colchón $2,000 (piso MLL a 40 ticks), TP 32, SL 100,
   flatten 14:30 CT, referencia = close de la barra 9:30 CT, orden intra-barra "adverso primero", y slippage de entrada empírico {1,3} ticks
   (50/50, N=2 mediciones: lun 19-oct = 1, mar 20-oct ≈ 3 inferido) promediando ambos. TP-primero = el resultado del día es TP;
   liq = resultado LIQ; ticks netos = (pnl neto / (40 × $1.25)).
4. **Bloques D1/D2.** 10 bloques consecutivos de igual tamaño de días de evaluación (el resto, si lo hay, se agrega al último bloque).
5. **Control `alternate`.** Lado = `decide_side(trading_day_index(fecha), "alternate")` con la fecha real del día (igual que producción). Control aleatorio:
   1,000 corridas, semillas 0..999, lado ±1 con prob. 1/2 por día. Oráculo: el mejor lado ex post (referencia informativa, no candidato).
6. **Bootstrap D2(b).** Bootstrap por bloques de 5 días consecutivos, PAREADO (misma remuestra de fechas para la regla y para `alternate`), 10,000 remuestras, semilla 20261020,
   IC percentil al 98.3% de la diferencia media de P(TP-primero) por día (regla − alternate). "Estrictamente > 0" = límite inferior > 0.
7. **Ventana dominante (MES).** El encargo la define para MGC (oro, nov-2025→ene-2026) pero no para MES. Definición fijada ANTES de ver resultados de reglas y
   usando SOLO el precio: la ventana de 60 días hábiles consecutivos de la muestra de evaluación con mayor |Δ del cierre ajustado|. Sus fechas se registran en
   la Enmienda 2 antes de correr reglas. D2(d) y la parte "sin la ventana dominante" de D1 se evalúan excluyendo esos 60 días.
8. **Las 8 sesiones en vivo (D1, anécdota).** Los datos por sesión viven en el Gist (`geometry_mestest_log.json`), que requiere un token que este agente no maneja:
   NO DISPONIBLE localmente. La tabla se marca "no disponible" salvo que Eric exporte el JSON; no se rellena de memoria.
9. **Lectura de hoy (§3.7).** El parquet termina el 25-ago-2026. Para el cierre del 20-oct se intentará Yahoo (`MES=F`), marcado como menor calidad; si falla, "no disponible".
10. **Comparaciones múltiples.** Se contarán todas las reglas/controles evaluados en este documento (3 reglas candidatas; 4 controles). No se agregan reglas ni parámetros
    sin una enmienda fechada y sin una ventana de datos nueva.

### Enmienda 2 — 20-oct-2026, ventana dominante de MES (calculada SOLO con precio, antes de correr reglas)
Procedimiento de la Enmienda 1 §7 aplicado a la muestra de evaluación (443 días, 2024-11-04 → 2026-08-25, `series.py::dominant_window`):
**2025-04-09 → 2025-07-08** (60 días de evaluación consecutivos; Δ del cierre ajustado = +1,124.8 puntos). Ningún resultado de reglas, controles o P(TP-primero)
se había calculado al registrar esta enmienda.
