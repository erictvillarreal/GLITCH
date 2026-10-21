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
(ninguna al momento del registro)
