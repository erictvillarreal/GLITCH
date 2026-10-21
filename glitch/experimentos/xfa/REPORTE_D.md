# REPORTE D — Certeza en la etapa fondeada (XFA 50K) y los payouts — 20-oct-2026 (noche)

Rama `experimentos-research` (commits sobre `a51e879`). **Nada desplegado, nada tocó `main`, el Pi, Railway ni credenciales.** Archivos de esta parte, todos en `glitch/experimentos/xfa/`: [`RULEBOOK_XFA.md`](RULEBOOK_XFA.md) · [`PREGUNTAS_TOPSTEP.md`](PREGUNTAS_TOPSTEP.md) · [`INVENTARIO_XFA.md`](INVENTARIO_XFA.md) · [`EVIDENCIA_CEREBRO2.md`](EVIDENCIA_CEREBRO2.md) · [`PLAYBOOK_XFA.md`](PLAYBOOK_XFA.md) · motor `xfa_engine.py` + DP `xfa_dp.py` + cadena `chain.py` + 13 pruebas (`test_xfa_engine.py`) · resultados `resultados_D*.md` · pre-registro `PREREGISTRO_D.md` (commiteado **antes** de los resultados comparativos). Cada cifra sale de un script de esa carpeta (semilla 20261020).

## 1. Resumen de una página

**Qué se sabe con CERTEZA (reglas oficiales leídas el 20-oct, 22 artículos del Help Center; `RULEBOOK_XFA.md`):**
1. XFA 50K: balance $0; **MLL −$2,000 que sube con el cierre y se fija en $0 al llegar a +$2,000**, monitoreado en **tiempo real** (no realizado incluido); al tocarlo la cuenta **se cierra para siempre** (Back2Funded **$599**). Tras el **primer pago el piso es $0** y **el saldo restante es el colchón**.
2. Pago (Standard): **5 días ganadores de ≥ $150 NETOS** (no consecutivos), 50 % del saldo con **tope $2,000**, **mínimo $125**, 90/10, desde el 2º pago ganancia ≥ $0.01 desde el último; el día del pedido no cuenta (pedirlo **entre 4:00 y 5:00 PM CT**). **La consistencia del 40 % solo existe en la ruta Consistency**, no en la Standard; el RTP obliga a Consistency.
3. Plan de escalado 50K: **2 / 3 / 5 lotes (20 / 30 / 50 micros)** con saldo < $1,500 / hasta $2,000 / > $2,000; MGC, además, 12 / 18 / 31 micros (restringido, vigente al 19-oct).
4. Activación **manual** (**$149**, elegir Standard/Consistency **una sola vez**, DLL opcional fijo); el Combine se cierra solo al pasar. Automatización con la API **permitida** con condiciones (sin VPS/VPN: el Pi es el dispositivo personal), un solo perfil, pagos solo a cuenta propia; no hay pagos en feriados; wire/SWIFT cuesta **$30** por pago.
5. **Hallazgo operativo (§5.1 del encargo):** en modo real el scheduler **no detecta ni avisa el PASE**, y su detección usa P&L **bruto** sin consistencia; tras el pase el Pi falla seguro (cuenta cerrada), pero **re-apuntar la instancia MES a la XFA ejecutaría la señal de 40 contratos en la XFA** (pasa la validación) → **una instancia por producto y listas de denegación cruzadas** (`PLAYBOOK_XFA.md` §1–2).

**Qué NO se puede saber hoy y se ACOTA (no se inventa una cifra puntual):**
- **El WR de Cerebro 2.** Medir WR 50 % vs 45 % exige ≈ **1,400 sesiones** (≈ 5.6 años); las 3 sesiones vivas contienen **1** trade decidido. **El cobrado por XFA se divide por 2.6 con WR 45 % y se multiplica por 3 con WR 55 %.** El WR observado con la alternancia real es **47.4 % [40.9, 54.1]** y el equilibrio está en ≈ 46 %.
- El slippage real (N = 2 en MES; MGC no medido), los umbrales del RTP y de “compras excesivas”, y la elegibilidad al beneficio de $10k. Se llevan a 13 preguntas escritas (`PREGUNTAS_TOPSTEP.md`).

**Cifra de referencia por XFA 50K (motor nuevo, reglas verificadas, MGC limpio, plan 3×364/364):** cobrado medio **$736 ± 15** (stop exacto) / **$648 ± 13** (stop llenado a 0.5 de la barra, convención de C1), P(≥1 pago) 36 % / 33 %, **P($0) 64 % / 67 %**, mediana $0, p90 $2.2k / $1.8k, vida 10 días. Regresión contra lo publicado: **$618 / 31.7 % vs $616–620 / 31.6 %** (mismas tablas y supuestos); la diferencia con $736 = reglas oficiales (mínimo $125 y ganancia desde el último pago, que el motor publicado no tenía) y datos limpios.

**Veredicto pre-registrado para Cerebro 2 en la 50K (escenario Standard, reglas verificadas):** **NO es la mejor opción tal como está.** El bracket **728×3 (stop = piso)** cobra **+$102 ± 19 (W2) y +$107 ± 21 (W3)** más por XFA (+14 %), y la re-optimización con selección en una mitad y evaluación en la otra da **+$74 y +$128** (+10 % a +19 %) con brackets más anchos y nc 4–6. **Pero** ninguna alternativa distinta de MGC lo supera (MES micros $604, TP corto/SL ancho −$390…−$410, 1 micro −$56, payout-first −$21, cobro al mínimo −$570) y **ninguna mejora el problema de fondo: depende del WR**. Qué dato lo cambiaría: un WR medido (≥ 600 decisiones), el slippage de MGC, y la respuesta sobre RTP.

**El tamaño/cobro óptimo tiene un costado que no recomiendo:** la DP (y la regla simple 8 micros hasta $1,500 de saldo) sube el cobrado **+$220–$290 por XFA (+30 %) fuera de muestra**, **pero es una lotería** (con 8 micros el piso, no el SL, manda: 33 % de liquidar el día 1 y 20 % de TP) que usa el 67 % del máximo y el MLL como único stop — justo los patrones que el RTP y “conducta prohibida” citan. **No la propongo sin respuesta escrita de Topstep.** La versión sin lotería (4 micros hasta $1,500 y 1 después, pedir al llegar a $1,500) da **$808 vs $737 (+$70, +10 %)**, estable en ambas mitades.

**Un solo rango anual por cuenta (cadena Combine → XFA → Combine, motor nuevo en las dos etapas; reglas verificadas; sin RTP; $714/año compartidos; `resultados_D8.md`), media [P(neto < 0)]:**

| sistema | slip de entrada del Combine = 1 | mezcla {1,3} (observado, N = 2) | = 3 |
|---|---|---|---|
| **hoy:** Combine 40 fijos + Cerebro 2 3×364 (stop 0.5) | **$2.7k** [32 %] | **$1.2k** [46 %] | **$0.5k** [53 %] |
| + sizing finish-line (Parte A) | $2.7k [32 %] | $2.2k [36 %] | $1.9k [39 %] |
| + finish-line + bracket 728×3 | $4.3k [26 %] | $3.7k [29 %] | $3.4k [32 %] |
| (stop exacto, hoy) | $3.5k [26 %] | $1.9k [40 %] | $1.2k [47 %] |

Con WR 45 %: **−$2.1k a −$2.6k** (P(neto < 0) 80–86 %); con WR 55 %: **+$9.8k a +$12.5k**. **El rango único honesto es $0.5k–$2.7k con el sistema de hoy (centro ≈ $1.2k), $1.9k–$4.3k con las mejoras, y el WR lo mueve entre −$2.6k y +$12k.** **Ninguno alcanza ~$7,000 al año por cuenta sin una ventaja real.**

**Qué hacer antes de llegar a la XFA (en orden):** (1) enviar las 13 preguntas; (2) aprobar o no los parches A–C (sobre todo el registro de slippage y la detección de liquidación); (3) corregir/sustituir el cargador de MGC que ignora la etiqueta del contrato; (4) decidir con Eric si Cerebro 2 sigue en 3×364/364, pasa a 728×3, o espera a medir; (5) el playbook (§1 en particular: nunca re-apuntar la instancia MES).

## 2. Hallazgos que cambian cosas

| # | Hallazgo | Evidencia | Consecuencia |
|---|---|---|---|
| **H1** | **El archivo de MGC intercala barras de dos contratos simultáneos** (225/515 días, 2,095 cambios de etiqueta con saltos de ≈ 25 puntos = 250 ticks). El código previo ignora la etiqueta. | `EVIDENCIA_CEREBRO2.md` §1.1 | Los días TP/SL de MGC estaban inflados 14 %. Efecto en el pago por XFA: P(≥1 pago) −3.5 pp, cobrado igual. **Todo resultado histórico de MGC (grids, WR 49.97 %, “$620”) usó esa serie.** |
| H2 | **La dependencia de la “ventana de oro” desaparece en el pago por XFA**: con la serie limpia, quitarla cambia el cobrado ≤ 2 % ($721 con oro / $736 sin). El neto anual con/sin oro tampoco difiere ($1.25k / $1.22k). | `resultados_D5/D8.md` | Lo que parecía “nivel de la historia” era, al menos en parte, la **paridad de las fechas** (lado `alternate` fijo por día en una tendencia): suerte de muestra, no estructura. |
| H3 | **El WR de producción no es 50 %**: con la alternancia real por fecha sale **47.4 % [40.9, 54.1]**; el “49.97 %” excluye los FLATTEN y no usa la alternancia. | `evidencia_stats.md` | El caso base “WR 50 %” es una **hipótesis de cero ventaja**, no una medición. |
| H4 | **Los FLATTEN son el 56 % de los días y aportan 49 % de los días ganadores**; mover la hora del flatten cambia el cobrado ≤ 3 %. | `resultados_D4.md` | El flatten no ayuda ni perjudica de forma material. |
| H5 | **Régimen**: el oro hoy es mucho más volátil que en 2024–25 (FLATTEN 28 % vs 90 % de los días). Últimos 250 días: P(≥1 pago) 29 %, cobrado $773. | `resultados_D4.md` | El replay de 2 años mezcla regímenes. |
| H6 | **La ruta Consistency baja P(≥1 pago) de 36 % a 28 %** con el bracket actual (un TP de $1,086 = 50 % de la ganancia tras 2 TP; 33 % tras 3 TP); los brackets de 100–250 ticks son compatibles (38–61 %) pero pagan menos. | `resultados_D2.md` §C | Elegir **Standard** al activar (irreversible). |
| H7 | **Slippage en MGC** pesa menos que en el Combine: 3 ticks bajan el cobrado ≈ 8 % (plan actual) y 10 ticks ≈ 25 %; en el Combine el mismo efecto es un acantilado (−45 % de P(pase)). Un TP corto (60 ticks) con slip ≥ 10 queda en **$0** (el neto del TP cae bajo $150 y deja de contar como día ganador). | `resultados_D2.md` §B | Brackets anchos son robustos a slippage; los cortos no. |
| H8 | **El efecto del RTP sobre la XFA es pequeño; sobre el Combine es grande** (DLL automático + Combine Consistency). | `resultados_D2.md`, C1 | El riesgo RTP vive sobre todo en el Combine. |
| H9 | **El “79 % pagan $0”** del 13-oct **no se reproduce**: con las reglas verificadas P($0) = 64–67 %; $760 de media es compatible con $648–736. | `resultados_D5.md` | Se retira la cifra de 79 % del inventario. |

## 3. Puentes desde cada versión previa al rango nuevo

| versión previa | cifra | qué difiere de la cadena nueva | en la cadena nueva |
|---|---|---|---|
| 26-sep `engine_real` | p50 $3,532 (media ≈ $4.6k) | sin haircut ni liquidación en tiempo real, sin slip, TP 40 (C1 paso S0) | no comparable: ver C1 (S0 → S6) |
| 7-oct `lever_engine` | $1.8k–$3.2k (SIN/CON oro), $5.4k (justo) | sin slippage de entrada; ancla al fill; **XFA con serie contaminada y paridad baked** | slip ≈ 0–1: $2.7k–$3.8k, **sin diferencia con/sin oro** |
| 13-oct (T1) | $1.1k–$3.0k (≈ $2k de planeación) | stop 0.5 sin slip de entrada, ancla al fill | slip 1: $2.7k |
| 20-oct (C1) | **≈ $1.2k** (−$0.1k a +$1.6k) | XFA con serie contaminada y reglas del motor; la banda inferior (−$0.1k) venía de la ventana de oro | **$1.2k** con la mezcla observada y **sin banda inferior por oro**; el rango inferior ahora lo da el slippage (3 ticks: $0.5k) |
| encargo (13-oct, cuenta de servilleta) | costo de obtener una XFA $312–$437, payout $620–$760, margen $180–$450 | el motor sustituye la cuenta | costo $317–$446, cobrado $648–$736 → margen **$200–$420** por XFA; neto por XFA positivo solo si P(pase) ≳ 17 % **y** WR ≳ 46 % |

## 4. Auditoría adversarial de Cerebro 2 (§3b): una a una

| hallazgo | resultado |
|---|---|
| **1. Elegido para otra cuenta (150K)** | **Confirmado.** Re-optimizado para 50K (56 combinaciones, mitades): el plan actual **no** está en el óptimo; la región buena es nc 4–6 y SL = TP 550–728 (+$74 a +$128 fuera de muestra, +10 % a +19 %); la diferencia es modesta frente a la incertidumbre del WR. `resultados_D2.md` §F |
| **2. Cifras superadas** | **Confirmado.** `CEREBRO2_G2_VS_MGC_SUMMARY.md` (81.4 %, 46.9 %, $2,169, $31,257) es de 150K, sin liquidación en tiempo real ni topes por tamaño y con la serie contaminada: **obsoleto** (`NOTA_OBSOLESCENCIA.md`). No se usa como evidencia. |
| **3. Métrica excluye los time-exits** | **Confirmado.** El día real es TP 21 % / SL 23 % / **FLATTEN 56 %**; WR de producción 47.4 %; 49 % de los días ganadores son FLATTEN positivos; el flatten no mueve el cobrado más de 3 %. |
| **4. Consistencia 40 %** | **Matizado.** No aplica a la ruta Standard. En Consistency: 2 TP → 50 % (no elegible), 3 TP → 33 % (elegible, **verificado por prueba determinista**); P(≥1 pago) 28 % vs 36 %. Brackets de 100–250 ticks son compatibles pero pagan $440–$715 en media. |
| **5. Competidores (mismo motor y reglas)** | Ver tabla de §5. |
| **6. Lado del costo** | La cuenta de servilleta queda **confirmada** ($317–$446 por XFA; margen $200–$420). Sensibilidad: neto por XFA = cobrado − (49/P(pase) + 149); con cobrado $648 y P(pase) 17 % → $202; con 29 % → $331. |
| **7. Slippage de MGC vs Combine** | **Confirmado**: ≈ −8 % del cobrado con 3 ticks en MGC; −45 % de P(pase) con 3 ticks en el Combine. |
| **8. Evidencia viva** | N = 3 sesiones, 1 trade decidido: **sin inferencia**. 616 sesiones para distinguir 45 % de 55 %; 1,410 para 50 % vs 45 %. |

**Veredicto explícito:** **bajo el escenario de reglas “Standard, VERIFICADO” (stop 0.5 y exacto), Cerebro 2 (3×364/364) NO es la mejor opción para la 50K**: 728×3 la supera en W2 y en W3 con IC95 > 0 (criterio pre-registrado) y otras re-parametrizaciones también. **No existe evidencia de que MGC sea mejor o peor que MES micros** (MES: $604 y P($0) 48 % vs MGC $736 y 64 %, historias distintas, no pareadas). **Es defendible llegar a la XFA con MGC solo como apuesta de cero ventaja** (cadena anual: +$0.5k a +$2.7k según el slippage del Combine; +$1.2k con el observado); **no es defendible como apuesta de edge**.

## 5. Competidores (W2: MGC limpio sin oro; 50,000 vidas; stop exacto / 0.5; slip de entrada 0)

| candidato | cobrado por XFA (exacto / 0.5) | P(≥1 pago) | P($0) | dif. pareada vs plan actual (W2 / W3) |
|---|---|---|---|---|
| **a** plan 3×364/364 | **$736 / $648** | 36 % / 33 % | 64 % / 67 % | — |
| **b** 728×3 (stop = piso) | **$838 / $817** | 29 % / 28 % | 71 % / 72 % | **+$102 ± 19 / +$107 ± 21** (exacto) |
| c 1 micro 5 días y luego plan | $680 | 44 % | 56 % | −$56 ± 13 / −$47 ± 13 |
| c′ 1 micro siempre | $421 / $367 | 70 % / 64 % | 30 % / 36 % | **más certeza (P($0) 30 %), menos cobrado** |
| d MES micros 3 × 291 ticks (historia MES) | $604 / — | 52 % | 48 % | no pareado |
| e1 TP 60 / SL 364 | $328 | 68 % | 32 % | −$408 ± 15 / −$425 ± 15 |
| e2 TP 70 / SL 250 | $349 | 72 % | 28 % | −$387 ± 15 / −$433 ± 15 |
| f payout-first (1 micro con ≥ 4 días ganadores) | $715 | 42 % | 58 % | −$21 ± 9 / −$13 ± 9 |
| H4b cobro al mínimo ($125) | $157 | 36 % | 64 % | −$571 ± 13 (y con $30 de wire por pago, peor) |
| H6 no operar tras rango bajo | $394 vs $508 sin filtro (secuencial) | 33 % | 67 % | peor (−$114 ± ~12) |
| DP 4 micros → 1 y cobro a $1,500 (sin lotería) | $808 vs $737 | 35 % | 65 % | **+$70** (estable en H1 y H2) |
| DP / 8 micros → 1–3 (**lotería**, no recomendada) | $986–$996 | 35 % | 65 % | +$220…+$290 fuera de muestra |

La **certeza** (P(≥1 pago)) y el **cobrado medio** se oponen: 1 micro siempre da P($0) 30 % pero $421; 3×364 da P($0) 64 % y $736. **Si el objetivo de Eric es “no llegar con incertidumbre”, el bracket de 1 micro es el que más reduce la incertidumbre de recibir algo, a costa de ≈ 43 % del cobrado esperado y de un neto por XFA ≈ $0 a +$100** (el costo de obtenerla es $317–$446).

## 6. Política de cobro y tamaño (regla simple, sin lotería) — `resultados_D11.md`
Operar **4 micros mientras el saldo sea < $1,500 y 1 micro después; pedir el pago máximo cuando haya ≥ 5 días ganadores y el saldo ≥ $1,500** (si el saldo es menor, esperar). Cobrado $808 vs $737 del plan actual (H1 $758 vs $658, H2 $832 vs $770). Con SL = TP = 364 los 4 micros arriesgan $1,456 + comisión, menos que el colchón inicial ($2,000): **no es lotería**. Es una **hipótesis exploratoria** (selección en las mismas 443 días): se valida en paper/Practice con 1 micro y se decide con Topstep sobre “max position”.

## 7. Lo que decide Eric
1. ¿Se envían hoy las 13 preguntas (en particular 1, 2, 3, 4, 13)?  2. Cerebro 2 al pasar el Combine: ¿3×364 (hoy), 728×3 o 4→1 micros? Mi lectura: **no cambiar parámetros sin medir slippage y sin la respuesta de RTP; si se cambia, el candidato con más soporte es 728×3 o 4→1 micros**; 1 micro la primera semana.  3. ¿Se aprueban los parches A–C y se corrige el cargador de MGC?  4. Titularidad/perfil/fiscal antes de cualquier payout (`PLAYBOOK_XFA.md` §6).

## 8. Verificación y límites
Suite base del repo: **492 pasan**; `git diff origin/main -- glitch/ ':!glitch/experimentos'` vacío. Pruebas nuevas: 13 del motor (incluye la regresión contra el motor publicado) + 7 del estado oficial del Combine (propuesta, NO DESPLEGAR). Los documentos del Project (`estado_y_expectativas_26sep2026`, `rd_palancas…`, `validacion_mgc_14oct2026`, etc.) **no son accesibles** para este agente y se marcan [citado, no leído] en el inventario. La DP no impone la regla de “ganancia desde el último pago” (se valida por Monte Carlo del motor completo, que sí la impone en los comparativos y no en la validación de la DP); el slippage de MGC y el WR **no están medidos**; una sola historia de 488 días; no se modelan correlaciones MES–MGC ni RTP en la cadena.
