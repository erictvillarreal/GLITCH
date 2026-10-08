# ¿Cuándo sumar la segunda cuenta Topstep 50K?
*Rama `research/stacking-timing`, sandbox, oct-2026, sin tocar producción. Motor `dd_cash/lever_engine.py` (ahora con arranque diferido por trayectoria `start`, estado diario y slippage de entrada; pruebas en `tests/test_lever_engine.py`). Misma convención que `structural-levers`: 12 meses desde 19-oct-2026, liquidación explícita de la XFA, slip de stop 0.5, fees completos (tarifa inicial incluida), costo compartido $714 una vez. Configuración principal = "paso 2" (TP 32 + bracket XFA 728×3, propuesta pendiente de tu aprobación); sensibilidad con el paso 1 (364×3) al final. Tablas completas: `dd_cash/stacking_timing_report.txt`, `dd_cash/stacking_info_friction_report.txt`.*

## 0. Recomendación (una línea) y por qué
**Sumar la segunda cuenta a las 4 semanas (lunes 16-nov-2026), con señales distintas (MES + MCL), solo si la cuenta 1 pasa la compuerta de fricción de §3 y el ejecutor de 2 cuentas ya está auditado; no esperar a que la 1.ª pase, cobre o "siga viva".**
Criterio: maximizar el neto sin aumentar P(año negativo) ni el colchón; la razón: esperar más cuesta ≈ $65–140 por semana de retraso sin bajar el riesgo, y las 4 semanas compran justo lo que sí se puede medir rápido (fricción de ejecución), no lo que no se puede medir en meses (tasa de pase).

Cinco hechos que sostienen esto:
1. **Esperar no reduce el riesgo, solo el dinero.** Con señales distintas: P(año negativo) es 22% si se suma el mismo día y 22% a las 4 semanas (26% / 27% sin oro; 14% / 15% mundo justo); el colchón p95 es $6,891 vs $6,808. Cuesta $311 (con oro), $341 (sin oro) o $444 (mundo justo) de media.
2. **Condicionar al estado de la 1.ª cuenta cuesta mucho y tampoco ayuda a la cola.** "Solo si la caja ≥ 0 en el mes 3" baja la media de $6,442 a $4,259 (−34%) y sube P(<0) de 22% a 30%; "solo si tiene XFA viva en el mes 3": $4,714 y 27%. Ningún condicional reduce P(<0).
3. **Esperar a que la 1.ª pase equivale al mismo día** (la 1.ª ya pasó en 91% de las trayectorias a los 10 días hábiles); **esperar su primer payout cuesta $814–$1,228** (mediana ≈ día 41) y sube P(<0) 2–4 puntos.
4. **La palanca grande de riesgo no es el momento sino las señales.** Mismas señales: 52 días al año con ≥2 cuentas tocando el MLL (el RTP lista "multiple accounts hit the Maximum Loss Limit in one day"), colchón p95 ~$9.6k, P(<0) 29%. Señales distintas: 12 días, colchón ~$6.9k, P(<0) 22%. **Si el ejecutor MES+MCL no está listo, es mejor retrasar la 2.ª cuenta que sumarla idéntica** (8 semanas de retraso cuestan ~$650; 52 días de coincidencia con RTP no tienen precio estimable).
5. **Cuatro semanas son 5.9 Combines resueltos: no alcanzan para validar el pase** (§2), pero sí para ~15–20 entradas con las que medir slippage y fallos (§3).

## 1. Comparación de los momentos
Neto total a 12 meses de **2 cuentas** (después de $714 compartido). "Colchón" = p95 de la mayor caja acumulada negativa; "Pico" = p99. "≥2 MLL" = días al año con ambas cuentas tocando el MLL. "Int. tot." = intentos de Combine al año, ambas cuentas (cada cuenta: ~53–57 por año activo; la segunda se reporta por año activo). "Apila" = % de trayectorias en las que sí se suma. La referencia "solo 1 cuenta" y las filas (a)–(e) usan las mismas trayectorias de días.

### 1.1 Señales DISTINTAS (A: MES>MGC; B: MCL>MCL) — escenario recomendado
| Momento de la 2.ª cuenta | Mundo justo: media / mediana / P(<0) | Real CON oro | Real SIN oro | Colchón p95 / pico p99 (CON / SIN / justo) | ≥2 MLL (CON) | Int. tot. (CON) |
|---|---|---|---|---|---|---|
| solo 1 cuenta | 5,332 / 4,427 / 25% | 3,190 / 2,419 / 31% | 2,011 / 1,310 / 39% | 5,148/6,508 · 5,490/6,828 · 5,585/7,228 | 0 | 53 |
| (a) mismo día (19-oct) | 9,948 / 9,102 / 14% | 6,442 / 5,684 / 22% | 5,163 / 4,501 / 26% | 6,891/9,073 · 7,421/9,721 · 6,731/9,402 | 11.7 | 110 |
| (b) cuando la 1.ª pasa el Combine | 9,828 / 8,981 / 14% | 6,372 / 5,575 / 22% | 5,076 / 4,417 / 26% | 6,872/9,154 · 7,416/9,684 · 6,750/9,368 | 11.0 | 109 |
| (c) cuando la 1.ª cobra su 1.er payout | 8,720 / 7,798 / 18% | 5,628 / 4,789 / 24% | 4,291 / 3,560 / 30% | 6,575/8,336 · 7,075/8,769 · 6,571/8,314 | 9.0 | 99 |
| (d) 2 semanas (2-nov) | 9,737 / 8,865 / 15% | 6,299 / 5,515 / 22% | 4,985 / 4,342 / 26% | 6,823/9,130 · 7,385/9,626 · 6,738/9,326 | 11.0 | 108 |
| **(d) 4 semanas (16-nov)** | **9,504 / 8,705 / 15%** | **6,131 / 5,359 / 22%** | **4,822 / 4,121 / 27%** | 6,808/8,991 · 7,291/9,615 · 6,671/9,228 | 10.5 | 106 |
| (d) 8 semanas (15-dic) | 9,054 / 8,242 / 16% | 5,831 / 5,096 / 23% | 4,516 / 3,834 / 28% | 6,729/8,877 · 7,255/9,604 · 6,719/9,165 | 9.6 | 102 |
| (e1) mes 3, solo si la 1.ª tiene XFA viva (apila 66–67%) | 7,418 / 6,290 / 20% | 4,714 / 3,770 / 27% | 3,434 / 2,503 / 33% | 6,071/8,070 · 6,519/8,734 · 6,170/8,214 | 5.7 | 83 |
| (e2) mes 3, solo si la caja de la 1.ª ≥ 0 (apila 43–53%) | 6,992 / 5,687 / 23% | 4,259 / 3,078 / 30% | 2,906 / 1,784 / 37% | 5,450/6,928 · 5,778/7,182 · 5,837/7,581 | 4.0 | 74 |
| (e1) mes 6, XFA viva (apila 67–68%) | 6,582 / 5,507 / 22% | 4,017 / 3,120 / 29% | 2,770 / 1,995 / 36% | 5,885/7,678 · 6,283/8,117 · 6,110/8,148 | 3.9 | 74 |
| (e2) mes 6, caja ≥ 0 (apila 54–66%) | 6,509 / 5,436 / 24% | 3,933 / 2,832 / 31% | 2,612 / 1,526 / 39% | 5,282/6,584 · 5,595/6,877 · 5,676/7,316 | 3.5 | 71 |

### 1.2 Señales IDÉNTICAS (A + A, misma serie de días)
| Momento | Justo: media / P(<0) | CON oro: media / mediana / P(<0) | SIN oro: media / mediana / P(<0) | Colchón p95 CON / SIN / justo | ≥2 MLL (CON) | Int. tot. (CON) |
|---|---|---|---|---|---|---|
| solo 1 cuenta | 5,332 / 25% | 3,190 / 2,419 / 31% | 2,011 / 1,310 / 39% | 5,148 / 5,490 / 5,585 | 0 | 53 |
| (a) mismo día | 11,318 / 23% | 7,035 / 5,493 / 29% | 4,676 / 3,275 / 36% | 9,616 / 10,287 / 10,503 | 52.4 | 107 |
| (b) la 1.ª pasa | 11,176 / 23% | 6,942 / 5,421 / 29% | 4,607 / 3,194 / 36% | 9,471 / 10,174 / 10,251 | 48.8 | 106 |
| (c) 1.er payout | 9,754 / 25% | 6,090 / 4,477 / 31% | 3,975 / 2,563 / 38% | 8,337 / 8,873 / 8,552 | 39.2 | 97 |
| (d) 2 semanas | 11,045 / 23% | 6,844 / 5,355 / 29% | 4,533 / 3,138 / 36% | 9,442 / 10,124 / 10,229 | 48.6 | 105 |
| (d) 4 semanas | 10,741 / 23% | 6,648 / 5,178 / 29% | 4,416 / 3,058 / 36% | 9,257 / 9,941 / 10,092 | 46.4 | 103 |
| (d) 8 semanas | 10,204 / 24% | 6,279 / 4,855 / 30% | 4,149 / 2,879 / 37% | 8,985 / 9,632 / 9,758 | 42.4 | 99 |
| (e1) mes 3, XFA viva | 8,105 / 25% | 4,970 / 3,343 / 32% | 3,203 / 1,827 / 39% | 7,476 / 8,149 / 7,873 | 24.9 | 81 |
| (e2) mes 3, caja ≥ 0 | 7,532 / 27% | 4,405 / 2,576 / 34% | 2,787 / 1,200 / 42% | 6,108 / 6,392 / 6,718 | 17.6 | 73 |
| (e1) mes 6, XFA viva | 6,946 / 26% | 4,195 / 2,876 / 33% | 2,672 / 1,559 / 40% | 6,711 / 7,208 / 7,068 | 16.3 | 72 |
| (e2) mes 6, caja ≥ 0 | 6,891 / 28% | 4,037 / 2,297 / 36% | 2,512 / 936 / 44% | 5,547 / 5,881 / 6,036 | 14.9 | 70 |
Pico de caja negativa p99 con señales idénticas: $12.3k (a) y $11.9k (4 semanas) con oro; $12.9k / $12.5k sin oro; $13.7k / $13.2k en mundo justo.
Sensibilidad con el paso 1 (TP32, XFA 364×3, mundo justo, idénticas): sola $3,040; (a) $6,734 · 28%; 4 semanas $6,376 · 29%; 8 semanas $6,048 · 29%; primer payout $5,901 · 31%; mes 3 con XFA viva $4,773 · 31%. **Misma conclusión.**

### 1.3 Lectura
- **Costo de esperar** (media, señales distintas, de (a) a 2/4/8 semanas): CON oro −$143 / −$311 / −$611; SIN oro −$178 / −$341 / −$647; justo −$211 / −$444 / −$894. ≈ **$75–110 por semana** (con señales idénticas $66–139). Es el tiempo de operación perdido de la 2.ª cuenta (8 semanas = 40 de 255 días hábiles = 16%).
- **Riesgo**: P(<0), colchón y pico casi no cambian entre (a) y 8 semanas, porque la 1.ª cuenta aporta poca información sobre la 2.ª (días independientes año a año). Los condicionales (e) sí bajan el colchón (−$0.8k a −$1.6k) y la coincidencia de MLL, pero **a cambio de 27%–40% menos media y P(<0) igual o peor**: no son una buena compra.
- **Intentos de Combine**: ≈ 53–57 por cuenta y año (la 2.ª se normaliza por año activo); total 106 (4 semanas) a 110 (mismo día) con señales distintas. Esperar a las 8 semanas baja el total a 102; ninguna política de momento acerca el total a lo que podría considerarse "no excesivo", cuyo umbral Topstep no publica.
- **Coincidencia de MLL**: con señales distintas 12 → 10 días al año de (a) a 4–8 semanas. Con señales idénticas 52 → 42–46. Con 53 quiebres por cuenta al año, dos cuentas *independientes* coinciden ~11 días por azar; el piso estructural no es cero.

## 2. ¿Cuánto informan los primeros N intentos? (modelo: p = 30.8% de pase por Combine; historia real 32.4% / 32.6%)
Ritmo: un Combine se resuelve (quiebre o pase) cada ~2–4 días (más lento cuando la cuenta pasa y entra a la XFA); medianas de días hasta N Combines resueltos: **N = 3: 8 d (28-oct), 5: 16 d (9-nov), 10: 38 d (10-dic), 20: 84 d (16-feb-2027)** (mundo justo; con historia, 8/17/41/91). A 10/20/40/60 días: 3.5 / 5.9 / 10.2 / 14.3 resueltos; P(≥1 pase) 91% / 99% / 100% / 100%; P(≥1 payout) a 20/40/60 días: 22% / 48% / 66% (CON oro 25/53/71%).
Supuesto: intentos independientes (cada uno usa días nuevos); **dos cuentas con la misma señal no agregan información sobre p** (resultados perfectamente correlacionados).
| N | P(0 pases) si el modelo es correcto | P(≤1 pase) | Umbral k\* (rechazar si pases ≤ k\*, α ≤ 5%) | α real | Poder si p = 0.20 | Poder si p = 0.15 | P(0 pases \| p = 0.15) |
|---|---|---|---|---|---|---|---|
| 3 | 33.2% | 77.4% | ninguno | — | 0% | 0% | 61% |
| 5 | 15.9% | 51.2% | ninguno | — | 0% | 0% | 44% |
| 10 | 2.5% | 13.8% | **0 pases** | 2.5% | 11% | 20% | 20% |
| 20 | 0.1% | 0.6% | **≤ 2 pases** | 3.0% | 21% | 40% | 3.9% |
| 40 | 0.0% | 0.0% | **≤ 7 pases** | 4.5% | 44% | 76% | 0.2% |
**Qué distingue "el modelo falla" de "mala suerte":**
- Con N ≤ 5 **nada**: cero pases ocurre en 1 de 3 (N = 3) o 1 de 6 (N = 5) si el modelo es correcto. No hay decisión que tomar con 4 semanas de pase.
- Con N = 10 (mediados de diciembre), **cero pases** es evidencia (p = 2.5%), pero un modelo con la mitad del pase solo se detecta el 20% de las veces.
- La prueba sólida llega con **N = 20 (≈ 16-feb-2027): ≤ 2 pases** rechaza el modelo (α = 3%); poder 40% contra p = 0.15. Con N = 40 (≈ abril): ≤ 7 pases, poder 76%.
- El **payout por XFA** es aún menos informativo: media $760, desviación $2,261 (CV 2.98; 79% de las XFA pagan $0); para estimar la media a ±50% con 95% de confianza hacen falta **~136 XFA** (≈ 8 años de una cuenta, a ~16 XFA por año), a ±25% ~545 (≈ 34 años). El payout no se valida con datos vivos en el horizonte del proyecto.
- Consecuencia: **la señal de que "el modelo falla" que sí llega a tiempo no es el pase ni el payout, sino la fricción de ejecución** (§3), porque cambia el pase directamente: cada tick de slippage de entrada baja el pase 1.9 puntos (30.8% → 28.9% → 27.1% con 1 y 2 ticks).

## 3. Fricción medible en 2–4 semanas y luz verde
Todas las métricas se miden en la cuenta 1 sobre las ~15–20 sesiones de las primeras 4 semanas (≈ 5–6 Combines y, con 99% de probabilidad a las 4 semanas, al menos un Combine pasado). Impacto en el neto por cuenta (paso 2) al cambiar **una** fricción a la vez, justo / con oro / sin oro (base 6,105 / 3,989 / 2,713; pase base 30.8%):
| Fricción (modelo → degradación) | Neto justo | CON oro | SIN oro | dEV SIN oro | Pase |
|---|---|---|---|---|---|
| Entrada adversa 1 tick/contrato (modelo: 0) | 5,660 | 3,576 | 2,347 | −366 | 28.9% |
| Entrada adversa 2 ticks | 5,215 | 3,114 | 1,944 | −769 | 27.1% |
| Entrada adversa 4 ticks | 4,326 | 2,567 | 1,446 | −1,267 | 23.8% |
| Slippage de stop 1.0 / 2.0 (modelo 0.5) | 5,584 / 4,737 | 3,858 / 3,642 | 2,612 / 2,456 | −101 / −257 | 30.8% |
| TP solo llena si el precio lo cruza 1 / 2 ticks (modelo: al tocar) | 5,921 / 5,736 | 3,800 / 3,644 | 2,555 / 2,427 | −158 / −286 | 29.7% / 28.7% |
| Comisión ×1.2 / ×1.5 | 6,038 / 5,943 | 3,937 / 3,851 | 2,660 / 2,584 | −52 / −129 | 30.8% |
| Costo por intento ×1.1 / ×1.25 | 5,597 / 4,834 | 3,472 / 2,697 | 2,179 / 1,378 | −534 / −1,335 | 30.8% |
| 2% / 5% / 10% de los días sin operar (fallo de API) | 6,002 / 5,794 / 5,471 | 3,903 / 3,777 / 3,553 | 2,657 / 2,556 / 2,416 | −56 / −157 / −297 | 30.8% |
| **Combinado**: entrada 1 tick + stop 1.0 + TP +1 + comisión ×1.2 + 2% días | 4,812 | 3,167 | 2,010 | −703 | 27.8% |
| **Adverso**: entrada 2 ticks + stop 1.5 + TP +1 + comisión ×1.5 + 5% días | 3,636 | 2,422 | 1,358 | −1,355 | 25.3% |
| Modelo "falla": pase a la mitad, lo demás igual | 2,566 | 1,023 | 43 | −2,670 | ≈15% |
Hay que entender que **ninguna fricción realista vuelve negativo el valor de la 2.ª cuenta** (el peor caso combinado deja $1.4k sin oro); lo único que lo lleva a cero es que el pase caiga a la mitad. Por eso la compuerta vigila lo que mueve el pase (la entrada y el llenado del TP) y lo que no se modela (fallos operativos de cola).

**Límites para dar luz verde a la segunda cuenta** (promedios sobre ≥ 15 entradas de la 1.ª cuenta, salvo indicación):
| Métrica (cómo se mide) | Valor del modelo | 🟢 Verde | 🟡 Amarillo (más datos / revisar) | 🔴 Rojo (no sumar) |
|---|---|---|---|---|
| **Slippage de entrada** (precio de llenado vs. cierre de la barra de 5 min de referencia, ticks MES por contrato, adverso positivo) | 0 | ≤ 1.0 | 1.0–2.0 | > 2.0 (dEV ≥ −$0.77k/cuenta y pase ≤ 27%) |
| **Llenado del TP** (ticks que el precio debe cruzar el TP para que el límite se llene; o % de toques de la barra con llenado) | llena al tocar | ≤ 1 tick (≥ 90% de toques llenos) | 1–2 ticks | > 2 ticks o < 75% de toques llenos |
| **Salida de flatten 14:30 CT** (market vs. cierre de la barra, ticks) y posición plana a las 14:35 | 0 | ≤ 1 tick, 100% planas a las 14:35 | 1–2 ticks | > 2 ticks, o cualquier sesión con posición abierta después de las 14:35 |
| **Stop / liquidación en la XFA** (exceso sobre el precio del stop, USD por contrato; pocas observaciones: ~1 por vida de XFA) | $34 medio (p90 $80) | ≤ $70 | $70–140 | > $140, o cualquier stop no ejecutado |
| **Fallos de API / ejecución** (entradas fallidas o tardías > 60 s, por 20 sesiones) | 0 | ≤ 1 (≤ 5% de días: −$0.16k) | 2 (10%: −$0.30k) | ≥ 3, **o** cualquier bracket sin confirmar > 5 s, orden duplicada, posición no conciliada, o `accountId` equivocado (cualquiera de estos = rojo inmediato, sin importar la frecuencia) |
| **Costo real por intento** (facturación Topstep de Combine/reinicio, comisión por RT por contrato, cuota de datos/API) | $49 · $1.22 · $59.5/mes | dentro de +5% | +5% a +10% (−$0.53k por +10%) | > +10% en cualquiera |
| **Pases observados** (no se decide con esto hasta N = 20, ≈ 16-feb-2027) | 30.8% | registrar | — | N = 10 con 0 pases → revisar; N = 20 con ≤ 2 → detener |
**Regla de luz verde:** todas las métricas en verde o a lo más una en amarillo, ninguna en rojo, y el **combinado** de las degradaciones medidas dentro del escenario "Combinado" de arriba (valor de la 2.ª cuenta ≥ $2.0k sin oro). Si queda en amarillo, se espera 2 semanas más; el retraso cuesta $75–110 por semana, menos que cualquier error de ejecución duplicado (un trade de 40 contratos con el bracket mal puesto arriesga $2,000 = una cuenta).

## 4. Recomendación explícita
1. **Momento óptimo: 4 semanas después del arranque = lunes 16-nov-2026**, con la compuerta de §3 en verde. Si el ejecutor de 2 cuentas aún no está auditado, **no sumar una cuenta idéntica** para no perder la fecha: usar la fecha de disponibilidad con señales distintas (cada semana de retraso ≈ −$75–110).
2. **Qué no hacer:** no esperar al pase (equivale al mismo día), no esperar al primer payout (−$0.8k a −$1.2k, P(<0) +2 a +4 puntos), no condicionar a "viva" (−$1.7k a −$3.0k de media sin mejorar P(<0)).
3. **Señales distintas siempre** (MES + MCL): bajan P(<0) de 29% a 22% (con oro), el colchón p95 de $9.6k a $6.9k y los días con ambas en el MLL de 46–52 a 10–12.
4. **Dependencias que no resuelve este análisis:** el ejecutor del Pi aún soporta una sola cuenta (diseño y pruebas entregados en el reporte de las 2 cuentas); el límite de tamaño del Combine para MCL no está verificado; Topstep no ha respondido por escrito sobre ~106 intentos al año ni sobre días con ambas cuentas en el MLL.

## 5. Supuestos y límites
- Días independientes entre años (bootstrap): el análisis de momento no puede capturar persistencia ni regímenes; por eso la información de la 1.ª cuenta sobre la 2.ª es casi nula salvo en el estado de la propia trayectoria.
- "Viva" no tiene definición oficial: se probaron dos (XFA activa; caja acumulada ≥ 0); el resultado no depende de la definición.
- La 2.ª cuenta idéntica usa exactamente la misma serie de días (correlación perfecta); la distinta usa el eje común de 497 días (historia, correlación real) o mundos independientes (justo: cota optimista de diversificación).
- Fricción: las barras son de 5 minutos; el slippage de entrada es un desplazamiento fijo en ticks aplicado a ambos stages; el stop del Combine es la liquidación del MLL (por eso el slip de stop pesa poco ahí).
- Los límites de §3 son juicio mío calibrado con la sensibilidad del propio motor, no reglas de Topstep; el umbral "excesivo" del RTP/ToU no se conoce.
- Mundo justo = cota superior; la historia real (con/sin oro) es el rango de planeación recomendado en `structural-levers`.
