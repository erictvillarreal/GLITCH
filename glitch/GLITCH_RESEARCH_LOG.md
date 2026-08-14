# GLITCH — Research Log
## Quant Research Journal
**Fecha:** 13-ago-2026  
**Deadline:** 6-sep-2026 (24 días hábiles restantes)  
**Objetivo:** Edge estadísticamente robusto para Combine + Cerebro 2 (funded account)

---

## Estado del Arte — Lo que sabemos con certeza

### Dataset disponible
- MES 5min, 2 años: ago-2024 a ago-2026, 34,619 barras RTH
- Fuente: Massive/Polygon, Futures Starter plan ($29/mes, vence sep-2026)
- Cache: `data_cache/mes_5min_2y.parquet`

### Señales con base estadística real (correlaciones brutas, sin estrategia)
| Factor | r | p-val | Interpretación |
|--------|---|-------|----------------|
| ret_prev día→día | -0.224 | 0.0000 | Mean-reversion diaria real |
| ret_2d_atras | +0.177 | 0.0001 | Continuación T-2 |
| Autocorr intradiaria lag-1 | -0.012 | 0.031 | MR intradía débil |
| 14:xx lag-1 | -0.063 | 0.0002 | MR fuerte en última hora |
| 9:xx lag-1 | -0.046 | 0.021 | MR apertura |
| 12:xx lag-1 | +0.061 | 0.0000 | MOMENTUM mediodía |

### Estrategias probadas y descartadas
| Estrategia | Walk-forward p | mean_pass (15d) | Veredicto |
|-----------|---------------|-----------------|-----------|
| S10 ORB Fade | ~0.50 (no testado limpio) | 4.1% | Descartado |
| ORB Breakout | EV negativo todas configs | <47% | Descartado |
| MR día-a-día (base) | p=0.165 | 56.2% (15d) | Insuficiente |
| MR día-a-día (combo_2d) | p=0.081 | 64.8% (15d) / 55.9% (25d) | Candidato débil |
| Fade intradía multi-ventana | Bug en WF, EV<0 muestra limpia | Inválido | Descartado |

### Lecciones metodológicas críticas
1. **Nunca reportar muestra completa sin walk-forward** — combo_2d dio 77% en muestra, 56% en WF
2. **Verificar EV simple antes de triple barrier** — el fade intradía tenía EV=-0.000409 simple, el bug de WF lo ocultó
3. **La correlación bruta no implica PnL** — r=-0.063 en 14:xx es real pero no se convierte en estrategia rentable directamente
4. **La geometría del video (RR=0.33, WR=75%) es EV=0 sin edge** — solo funciona si la señal tiene esa geometría natural
5. **p<0.05 en WF con N_trades>200 es el criterio mínimo** — no negociable

---

## Lo que NO hemos probado correctamente

### Pendiente prioritario 1: MR intradía en 14:xx limpio
- La correlación r=-0.063 es real (p=0.0002, N=3,455)
- El intento anterior tenía bug: EV simple era negativo porque `ret_prev` cruzaba días
- **Hipótesis sin validar:** ¿el fade barra-a-barra en 14:xx tiene EV positivo cuando se implementa correctamente (solo dentro del mismo día, sin cruzar)?
- Prueba requerida: EV simple limpio → si positivo → triple barrier → walk-forward

### Pendiente prioritario 2: Momentum en 12:xx
- r=+0.061 en mediodía es la correlación más fuerte de todas (p=0.0000)
- Nunca se probó como estrategia de continuación
- **Hipótesis:** seguir la dirección de la barra de 12:xx en vez de faderla

### Pendiente prioritario 3: Combinación señal día-a-día + hora
- combo_2d (WF p=0.081) tiene algo real pero insuficiente solo
- ¿Condicionarlo a que la señal ocurra en una hora específica sube el WR?
- Ejemplo: solo operar combo_2d si la primera hora confirma la dirección

### Pendiente prioritario 4: MNQ como confirmación
- Si la MR día-a-día es real en índices, debería aparecer en MNQ también
- Si NO aparece en MNQ: sospecha de idiosincrasia/ruido de MES específicamente
- Costo: $0 adicional (ya tenemos acceso Massive)

---

## Cerebro 2 — Funded Account (NO iniciado)

**Estado actual:** No hay ni una línea de código de investigación para la fase funded.

**El problema del Cerebro 2 es diferente al del Combine:**
- Combine: maximizar probabilidad de llegar a $3,000 antes de tocar el floor
- Funded: maximizar EV realizado neto bajo restricciones de Topstep XFA
  - Sin profit target (no hay $3,000 que alcanzar)
  - Sin trailing MLL (el floor no sube)
  - Regla de consistencia: mejor día <40% del total
  - Payout trigger: 5 días ganadores de $150+ O balance ≥ $55k
  - Max payout: $5,000 por retiro (90/10 split)

**Implicación:** la estrategia óptima para el Cerebro 2 NO es la misma que para el Combine.
- En el Combine queremos pocas trades de alto impacto (minimizar varianza del camino)
- En funded queremos muchos trades de bajo riesgo (acumular días ganadores de $150+)
- Específicamente: con 10 contratos MES, necesitamos $150/día = 3 puntos de ganancia
- Eso es un TP de 3 puntos con cualquier WR razonable

**Preguntas sin responder para Cerebro 2:**
1. ¿Cuántos días ganadores de $150+ podemos esperar con cada estrategia candidata?
2. ¿Cuál es el EV realizado neto (después de payouts) por cuenta por mes?
3. ¿Cómo se comporta la regla de consistencia con la estrategia elegida?
4. ¿Cuál es el tiempo esperado entre payouts?

---

## Plan de trabajo — 24 días hábiles hasta 6-sep-2026

### Semana 1 (13-19 ago): Validar señales intradía limpias
- [ ] Día 1: EV simple limpio de 14:xx fade (sin cruzar días)
- [ ] Día 2: EV simple limpio de 12:xx momentum
- [ ] Día 3: Walk-forward de lo que tenga EV>0
- [ ] Día 4: MNQ como confirmación de señal día-a-día
- [ ] Día 5: Documentar veredicto — ¿hay algo que supere p<0.05?

### Semana 2 (20-26 ago): Combinaciones y Cerebro 2
- [ ] Día 1-2: Combinar mejor señal intradía con combo_2d
- [ ] Día 3-4: Primer diseño de Cerebro 2 (reglas XFA, sizing, trigger de payout)
- [ ] Día 5: Monte Carlo del Cerebro 2 con datos reales

### Semana 3 (27 ago - 2 sep): Decisión de Combine
- [ ] Si hay estrategia con WF p<0.05 y mean_pass≥70%: preparar para pagar
- [ ] Si no: evaluar pagar con combo_2d (p=0.081, mean_pass=56%) como experimento controlado
- [ ] Documentar criterio de decisión explícito antes de pagar

### Semana 4 (3-6 sep): Cierre y setup
- [ ] Commit de todo el código de investigación al repo
- [ ] Actualizar Railway con estrategia final
- [ ] Decisión final: pagar o no pagar el Combine

---

## Criterios de decisión explícitos (no negociables)

### Para pagar el Combine:
- **Mínimo aceptable:** WF p<0.10 Y mean_pass≥60% en 25 días
- **Preferido:** WF p<0.05 Y mean_pass≥70% en 25 días
- **Si no se alcanza para el 6-sep:** pagar de todas formas con combo_2d y documentar que es un experimento, no certeza

### Para activar Cerebro 2:
- Estrategia con ≥3 días ganadores de $150+ esperados por semana
- Blow rate en funded <20% en 90 días de simulación
- Consistencia verificada: nunca viola regla del 40%

---

## Próximo experimento — INMEDIATO

**Exp-001: EV simple limpio de 14:xx fade**
- Hipótesis: r=-0.063 en 14:xx se convierte en EV>0 cuando se implementa correctamente
- Método: calcular `ret_prev` solo dentro del mismo día, sin cruzar días
- Criterio de éxito: EV simple >0 con t-test p<0.05
- Si pasa: proceder a triple barrier y walk-forward
- Si falla: descartar señal 14:xx definitivamente

