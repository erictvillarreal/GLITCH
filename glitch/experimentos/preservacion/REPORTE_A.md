# REPORTE A — Preservación de capital (Combine 50K, intento #2) — 20-oct-2026

Rama `experimentos-research` (desde `origin/main` a387a70). **Nada desplegado, nada tocó producción, Pi ni Railway.** Todo reproducible: `python run_partA.py`, `python run_partA2.py`, `python extra_stats.py`, `python -m pytest -q test_regression.py` (18 pruebas) desde `glitch/experimentos/preservacion/`. Semilla base 20261020. Datos: `data_cache/mes_5min_2y.parquet` (MES, barras de 5 min RTH, 2024-08-26 → 2026-08-25).

## 0. Resumen (10 líneas)

1. **Techo teórico sin deriva: 55.6 %** = (51,401 − 49,401)/(53,000 − 49,401). La DP exacta (lado-neutral, 60 días) llega a **50.3 %** y la DP con los lados reales a 52.7 %; ninguna política heurística la supera. Nada de lo que cambie el tamaño puede pasar de ~55 % sin deriva.
2. **Con 40 contratos fijos: P(pase) 33.8 %, P(liquidar mañana) 44.2 %.** Con la regla *finish-line* (40 mientras falte mucho y achicar cuando un TP ya cubre el faltante): **51.4 %** y 5.5 % de liquidar estando a ≤ $100 de la meta (vs 38.1 % con 40 fijos). Es el único cambio que mueve el resultado: **+17.6 pp** (robusto en 5 modelos de camino: 48.0–51.7 % vs 32.5–34.0 %).
3. **Por qué:** desde 51,401 faltan $1,599 y un TP de 40 contratos deja ≤ $1,551 neto: *ningún* día de 40 contratos alcanza. Hacen falta dos TP; el segundo, con 40 contratos, arriesga el 36–39 % de liquidar a $100 de la meta. Con 3 contratos ese cierre pasa 94.7 % (5.3 % liquida).
4. **Mañana (miér 21, SHORT):** el máximo de contratos que hace *imposible* liquidar en un día es **14** (margen $127.92 con slip de entrada 3 + salida 3). Con 14 contratos P(TP) 72.4 %, P(SL) 18.7 %, **P(liquidar) 0 %**; con 40: P(TP) 55.4 %, P(liquidar) 44.2 %.
5. **Costo de ser conservador mañana (continuación óptima, DP):** P(pase) 46.5 % con 14 contratos vs 49.8 % con 40 (−3.3 pp). El **costo de bolsillo esperado hasta pasar es el mismo (≈ $72–80)**: perder la cuenta cuesta $49 de reset + ~$2.3/día, no capital. Lo que sí cuesta es tiempo.
6. **Cuidado:** 14 contratos no son “seguro” para el *intento*: un SL cuesta $1,872 y deja ~$128 sobre el piso (cuenta prácticamente muerta). Evita la liquidación, no la pérdida del intento.
7. **Con el heurístico “SL-safe” puro (P2/P4/P5)** el P(pase) cae a 42–44.5 % y el tiempo esperado a ~30–39 días hábiles: sale caro. No lo recomiendo.
8. **Hallazgo operativo:** el Pi ya trae un tope local `GLITCH_PI_NC_MAX` (pi_executor.py:1074-1085) que recorta `nc` sin tocar código: el *sizing adaptativo manual* es viable hoy con una variable de entorno (decisión y ejecución de Eric; no la toqué).
9. **Hallazgo grande no previsto — el acantilado del slippage de entrada** (ver §6): TP/SL se anclan a la *referencia*, no al fill; con nc = 40 y TP 32, dos TP netos suman $3,002 con slip 1 pero $2,802 con slip 3 → un tercer TP → el pase por intento de una cuenta nueva cae de ~30 % a ~17 %.
10. **Recomendación para mañana (una página, §8): quedarse en 40 contratos y activar la regla finish-line desde el día siguiente al TP**; la decisión es de Eric.

## 1. Mecánica modelada (M2: replay de días reales) — fuentes

| elemento | valor | fuente |
|---|---|---|
| referencia de entrada | close de la barra 9:30 CT (la última completa en la compuerta 9:35) | `geometry_scheduler.py:ENTRY_GATE_MINUTES`; `pi_executor.py::_reference_price` (último close) |
| TP/SL | desde la **referencia**, no desde el fill | `pi_executor.py:1189-1200` (se calculan *antes* de la orden de mercado) |
| flatten | 14:30 CT, close de la barra 14:25 | `geometry_scheduler.py:SESSION_FLATTEN_MINUTES` |
| liquidación | mark-to-market con el peor tick de cada barra; piso = min(pico − 2,000, 50,000) | encargo §1; `core/prop_firm.py` |
| comisión | $1.22/contrato round-trip | `geometry_pure.py::SPECS["MES"]` |
| slippage de entrada | {1, 3} ticks 50/50 | **N = 2** (lun 19-oct = 1 tick; mar 20-oct ≈ 3, inferido). `geometry_mestest_log.json` vive en el Gist (token): **no disponible** localmente |
| slippage de salida en SL | 3 ticks | **SUPUESTO sin medición** (= el peor de entrada observado); sensibilidad {0,1,3,5} en §7 |
| orden dentro de una barra | adverso primero (conservador); alternativa OHLC | desconocido; ambos reportados |
| consistencia | pase si balance ≥ 53,000 y mejor día < $1,650 | encargo §1. **Nunca liga** con TP 32 y nc ≤ 40 (máx. día posible $1,551 < $1,650; test). Ver nota de la regla en §9 |
| tiempo / costos de bolsillo | suscripción $49/mes ≈ $2.33/día hábil; reset $49 | encargo §1 |
| días | 492 completos de 515 (23 descartados: cierres anticipados y huecos) | `daydata.py` |

Una corrección que hice a mi propio simulador antes de correr las tablas finales: el stop (−100) se dispara **antes** que el piso cuando el stop está más cerca; la primera versión trataba cualquier barra que cruzara el piso como liquidación aunque el stop ya hubiera cerrado la posición (inflaba P(liq) con 8–14 contratos). Documentado en `daydata.py::sim_day` y en `test_regression.py::test_sl_safe_nunca_liquida_en_el_peor_caso`.

## 2. Verificaciones (pruebas de regresión del encargo §2.2)

`test_regression.py`, 18 pruebas, todas pasan:
- **Techo de martingala:** con barras brownianas sin fricción ninguna política (40, 20, P2, P3, P4b) tiene el límite inferior de su IC95 % por encima de 55.6 %.
- **Barrera nominal:** P(+32 antes de −40) = 55.6 % (40/72); dos victorias seguidas = 30.9 % (el engine del 12-oct daba 30.8 %).
- **20 contratos:** P(TP antes de liquidar) = 71.4 % (80/112) y 4 victorias para llegar a $3,000; 0.714⁴ = 26.0 % (cifra del 7-oct; no se re-simula con ratchet).
- **Mecánica:** TP, SL, liquidación, flatten, empates de barra (adverso-primero vs OHLC), simetría LONG/SHORT; fórmulas de `nc` de P2/P3 y que nunca excedan el tope (1 ≤ nc ≤ 40).
- **DP vs Monte Carlo** en la misma rejilla de $25: DP 52.7 % vs MC 52.8 % [52.3, 53.3] (lado-específica). Ese chequeo destapó un error mío (la máscara de estados con balance > 52,000 bajaba la DP a 49.7 %). **Advertencia:** la política de la DP es de “filo de navaja”: aplicada sobre estados fuera de su rejilla de $25 rinde 31–44 %. Por eso la DP sirve de referencia/techo y la política desplegable debe ser una regla simple (finish-line), no la tabla de la DP.
- **Validación cruzada con el motor de caja anterior** (`lever_engine`): coinciden con slip 0–1 (31 % vs 33 %, diferencias de barra de 9:45); ver `experimentos/economia` (C1).

La cifra “M1 calibrada a los 3 objetivos del 7-oct (59/24/17)” **no es reproducible con los datos reales**: M2 da 65.7/23.9/10.5 con la mecánica descrita. M1-doc (σ_día = 240 ticks, s = 0.8) ajusta los 3 objetivos del doc; M1-datos (σ = 100, s = 0.1) ajusta M2. Las conclusiones no dependen de cuál se use (§4).

## 3. Tabla principal — P(pase) desde el estado de partida (M2 iid, n = 50,000 por celda, 60 días máx.)

| política | P(pase) [IC95 %] | P(liquidar) | P(liq mañana) | días a pase (med) | costo de bolsillo hasta pasar | días hábiles esperados hasta pasar |
|---|---|---|---|---|---|---|
| **P0** 40 fijo (hoy) | 33.8 % [33.4, 34.2] | 66.2 % | 44.2 % | 2 | $172 | 7.2 |
| P1 5 fijo | 30.2 % | 65.4 % (+4.4 % abierta) | 0 % | 20 | $809 | 209 |
| P1 10 fijo | 38.3 % | 61.7 % | 0 % | 5 | $272 | 38.7 |
| P1 15 fijo | 43.4 % | 56.6 % | 9.4 % | 3 | $180 | 15.9 |
| P1 20 fijo | 39.7 % | 60.3 % | 24.0 % | 3 | $172 | 11.7 |
| P1 25 fijo | 45.6 % [45.1, 46.0] | 54.4 % | 31.0 % | 2 | $147 | 8.2 |
| P1 30 fijo | 41.1 % | 58.9 % | 36.2 % | 2 | $136 | 6.7 |
| P1 35 fijo | 36.9 % | 63.1 % | 40.7 % | 2 | $166 | 7.5 |
| **P2** SL-safe (14 al inicio) | 42.2 % [41.7, 42.6] | 57.8 % | **0 %** | 3 | $245 | 39.0 |
| **P3** finish-line | **51.4 %** [51.0, 51.8] | 48.6 % | 44.2 % | 2 | **$100** | 5.1 |
| P4 min(P2, P3) | 44.3 % | 55.6 % | 0 % | 3 | $219 | 35.7 |
| **P4b** 40 hoy y luego P4 | 51.2 % [50.7, 51.6] | 48.8 % | 44.2 % | 2 | $125 | 12.1 |
| P5 P2 → P3 con piso congelado | 44.5 % | 55.5 % | 0 % | 3 | $203 | 30.8 |
| P6 P4 + saltar si colchón < $500 / < $1,000 | 43.1 % / 42.4 % | 0.2 % | 0 % | — | — | **≈ 57 % queda abierta a 60 días** |
| PD DP óptima lado-neutral (rejilla $25) | 48.8 % | 51.2 % | — | — | — | — |

Notas: la no-monotonía de P1 (25 contratos > 20 y > 30) es **discretización**: con 25 contratos dos TP (2 × $938 = $1,876) cubren el faltante de $1,599; con 20 hacen falta tres. P6 degenera como se esperaba: con días iid sin deriva, esperar no cambia el estado (queda abierta) — solo sirve si el colchón puede recuperarse, y aquí no. P7 (SL más corto) **no se corrió**: es exploratorio, no es candidato y cambia la razón de barreras que el resto del análisis fija; queda en `PROPUESTAS.md`.

**Robustez a la forma del camino** (P0 / P2 / P3 / P4b): M2 iid 33.8/42.2/51.4/51.2 · M2 bloques de 5 días 32.8/42.1/51.4/50.9 · M2 orden OHLC 34.0/42.5/51.7/51.4 · M1-datos 33.8/40.3/49.6/49.4 · M1-doc 32.5/36.4/48.0/47.0. **El orden y el signo de las diferencias no cambian en ninguno.**

## 4. Métricas del “miedo literal” (§2.7; n = 50,000, `extra_stats.py`)

| política | P(pase) | P(liq | llegué a ≤ $200 de la meta) | P(liq | llegué a ≤ $100) | P(cierre mañana < 50,000) | balance mediano al cierre de mañana |
|---|---|---|---|---|---|
| P0 40 fijo | 33.7 % | **39.1 %** | **38.1 %** | 44.4 % | 52,802 |
| P1 25 fijo | 45.3 % | 31.1 % | 33.3 % | 31.1 % | 52,277 |
| P2 SL-safe (14) | 42.4 % | 23.6 % | 23.1 % | 0.0 % | 51,892 |
| **P3 finish-line** | 51.2 % | **7.3 %** | **5.5 %** | 44.4 % | 52,802 |
| P4b 40 hoy y P4 | 51.0 % | 7.6 % | 5.3 % | 44.4 % | 52,802 |

(Peor día simulado: −$2,362 a −$2,990; en estados con piso congelado el colchón llega a ~$2,900.)

## 5. Escenarios obligatorios (§2.8)

### 5.1 Mañana, miércoles 21-oct (SHORT por paridad; colchón $2,000.0)

| nc | P(TP) | P(SL) | P(**liquida**) | P(flatten) | P&L esp. | neto del TP (slip 1/3) | P(pase) con continuación óptima (DP) | costo de bolsillo esp. hasta pasar |
|---|---|---|---|---|---|---|---|---|
| 1–5 | 72.4 % | 18.7 % | 0 % | 8.9 % | −3…−15 | +38/+35 … +188/+175 | 49.9 … 48.7 % | $72–73 |
| 10 | 72.4 % | 18.7 % | 0 % | 8.9 % | −30 | +375/+350 | 46.8 % | $72 |
| **14** (máx. imposible-liquidar) | 72.4 % | 18.7 % | **0 %** | 8.9 % | −41 | +525/+490 | **46.5 %** | $74 |
| 15 | 72.4 % | 9.3 % | 9.3 % | 8.9 % | −44 | +563/+525 | 46.6 % | $77 |
| 20 | 70.5 % | 0 % | 24.0 % | 5.5 % | −15 | +751/+701 | 47.9 % | $75 |
| 25 | 66.4 % | 0 % | 30.9 % | 2.7 % | −38 | +938/+876 | 48.3 % | $77 |
| 30 | 62.4 % | 0 % | 36.2 % | 1.4 % | −55 | +1,126/+1,051 | 48.4 % | $79 |
| 35 | 58.6 % | 0 % | 40.9 % | 0.5 % | −77 | +1,314/+1,226 | 48.9 % | $80 |
| **40** (hoy) | 55.4 % | 0 % | **44.2 %** | 0.4 % | −84 | +1,501/+1,401 | **49.8 %** | $79 |

- **nc mínimo que hace imposible liquidar en un día = 14**, margen **$127.92**: costo por contrato de un SL completo = (100 + 3 + 3) ticks × $1.25 + $1.22 = $133.72; 2,000/133.72 = 14.96 → 14. Con 15 contratos un SL con slip 3/3 ($2,006) ya toca el piso. El replay de los 492 días reales confirma 14 (0 liquidaciones). El margen depende del slip de salida supuesto: **la salida de 3 ticks es un supuesto sin medición**.
- Estado tras el día (nc = 40): TP → ≈ 52,802–52,902 (faltan $98–$198; **no** alcanza para pasar); liquidación → 49,401 (reset $49).
- **El costo de P(pase) de proteger mañana es pequeño (−3 pp) solo si después se sigue la política óptima**, que *requiere sizing adaptativo*. Con una continuación heurística la diferencia es de 7–8 pp (P4/P5 vs P3/P4b).

### 5.2 “A $100 de la meta” (balance con pico ≥ 52,000 → piso congelado en 50,000; promedio de empezar SHORT/LONG)

| balance (faltan) | 40 fijo: pasa / liquida | 10 fijo | 5 fijo | 3 fijo | **P3 finish-line** | DP óptima |
|---|---|---|---|---|---|---|
| 52,700 (300) | 61.0 % / 39.0 % | 83.9 % / 16.1 % | 79.1 % / 19.5 % | 71.2 % / 13.7 % (+15 % abierta) | **86.4 % / 13.6 %** | 87.4 % |
| 52,800 (200) | 62.0 % / 38.0 % | 84.7 % / 15.3 % | 81.5 % / 17.3 % | 79.5 % / 9.7 % | **90.6 % / 9.4 %** | 91.2 % |
| 52,900 (100) | 62.9 % / 37.1 % | 86.0 % / 14.0 % | 89.4 % / 9.8 % | 89.3 % / 5.1 % | **94.7 % / 5.3 %** | 95.1 % |
| 52,950 (50) | 63.6 % / 36.4 % | 86.4 % / 13.6 % | 90.3 % / 9.0 % | 90.1 % / 4.6 % | **96.5 % / 3.5 %** | 97.3 % |

El nc que minimiza el riesgo de quemar la cuenta ahí es **el de la regla finish-line = ⌈faltante / neto por contrato⌉** (≈ 3 contratos a $100, 6 a $200, 9 a $300), no “el menor posible” (1 contrato deja 29–65 % de las trayectorias abiertas a 60 días). **Regla manual para Eric** (neto de un TP por contrato con slip 3 = $35.0; $37.5 con slip 1): `nc = ⌈faltante / 35⌉`, tope 40.

### 5.3 Secuencia completa desde hoy: 40 mañana (P4b) vs P2 mañana

P4b (40 mañana, luego finish-line/SL-safe): **51.2 %**, costo $125, 12.1 días. P2 (14 mañana y SL-safe después): **42.2 %**, costo $245, 39.0 días. Costo de ser conservador mañana *con esas reglas*: −9.0 pp de P(pase), +$120 de bolsillo esperado y +27 días hábiles. Con continuación DP (no desplegable hoy) la diferencia baja a −3.3 pp y el costo de bolsillo queda igual.

## 6. Hallazgo: el acantilado del slippage de entrada (exploración posterior, `scan_cliff.py`)

El Pi calcula TP/SL desde el último close de ProjectX y *luego* manda la orden de mercado: el fill entra *slip* ticks peor y el TP sigue donde estaba. El neto de un TP es (32 − slip)·nc·$1.25 − nc·$1.22; con nc = 40: **$1,501 (slip 1) → $1,451 (slip 2) → $1,401 (slip 3)**. Dos TP son $3,002 / $2,902 / $2,802: **solo con slip ≤ 1 bastan dos días**; con slip ≥ 2 hace falta un tercero. Cuenta nueva, P0: **30.0 % (slip 0) / 29.1 % (1) / 17.2 % (2) / 16.5 % (3)**; con la mezcla {1,3} observada, 20.3 %. Con finish-line (P3): 29.2 % (slip 1) y **25.0 % (slip 3)**: el tercer día se hace con pocos contratos.

Combinaciones de TP y nc que no dependen del slip (cuenta nueva, mezcla {1,3}; regla de consistencia oficial): **TP 34/nc 40: 27.0 %** (26.2–28.5 % en slip 0–3) · TP 32/nc 44: 26.3 % · TP 32/nc 40: 20.3 %. El mecanismo es aritmético (enteros), no un hallazgo de datos, pero la elección concreta (34, 44) está calibrada en la misma historia de 492 días: **es una hipótesis, no evidencia**. Ver `PROPUESTAS.md`.

Efecto en la economía anual (C1, motor anterior con bracket anclado a la referencia): neto de una cuenta con slip 1 → $0.9k/$2.4k/$2.9k (SIN oro/CON oro/justo); con slip 3 → −$1.1k/−$0.05k/$0.3k. El número de planeación de $2,000/año **solo vale si el slippage real es ≤ 1 tick**.

## 7. Sensibilidades (P(pase) %, n = 30,000 por celda)

| escenario | P0 40 fijo | P2 SL-safe | P3 finish-line | P4 min(P2,P3) | P4b 40 hoy+P4 |
|---|---|---|---|---|---|
| BASE (M2 iid, slip {1,3}, salida 3, TP 32) | 33.8 | 41.8 | 51.5 | 44.0 | 51.2 |
| M1 σ × 0.8 / × 1.2 | 34.2 / 33.2 | 39.1 / 40.4 | 50.9 / 50.3 | 41.5 / 42.1 | 50.6 / 50.0 |
| deriva a favor −2 / +2 / +5 ticks por día | 32.8 / 34.6 / 35.0 | 39.2 / 42.7 / 43.7 | 50.3 / 52.4 / 52.9 | 41.3 / 45.1 / 46.1 | 50.0 / 52.2 / 52.7 |
| slip entrada fijo 0 / 1 / 3 / 5 | 35.8 / 34.8 / 32.8 / 31.0 | 44.4 / 43.6 / 33.5 / 32.2 | 54.9 / 53.3 / 49.6 / 44.3 | 46.8 / 45.5 / 42.4 / 38.4 | 54.9 / 53.3 / 49.1 / 44.0 |
| slip salida SL 0 / 1 / 5 | 33.8 | 42.3 / 42.1 / 41.5 | 51.6 / 51.5 / 51.4 | 44.6 / 44.5 / 43.6 | 51.5 / 51.4 / 51.2 |
| TP efectivo 31 / 33 ticks | 34.7 / 33.1 | 37.2 / 40.9 | 51.4 / 51.5 | 43.9 / 42.5 | 50.9 / 51.2 |
| orden OHLC | 34.3 | 42.0 | 52.1 | 44.2 | 51.8 |
| sin ratchet (piso = pico − 2,000) | 28.7 | 34.1 | 50.1 | 41.4 | 49.7 |
| sin comisión | 34.0 | 43.5 | 52.5 | 45.4 | 52.4 |
| bloques de 5 días (vs iid) | 33.0 | 42.0 | 51.5 | 44.0 | 51.2 |

**Conexión con la Parte B (deriva direccional):** +5 ticks/día a favor suben P(pase) en solo +1.2 pp (P0) a +1.4 pp (P3). Una ventaja direccional realista no cambia el panorama; el diseño del tamaño sí.

## 8. Recomendación en una página (decide Eric)

**Mañana (miér 21-oct, 8:25 Monterrey es el límite para cualquier cambio):**

| opción | qué se hace | P(liquidar mañana) | P(pase) del intento* | costo de bolsillo esp. | riesgo operativo |
|---|---|---|---|---|---|
| **A (recomendada)** | dejar 40 contratos, sin cambios | 44.2 % | 49.8 % (óptima) / 51.2 % (P4b) | $79–125 | ninguno |
| B | `GLITCH_PI_NC_MAX=14` en el Pi y reiniciarlo antes de las 8:25 | **0 %** | 46.5 % (óptima) / 42.2 % (P2) | $74–245 | cambio de entorno en producción; si se olvida quitarlo queda en 14 siempre |
| C | `GLITCH_PI_NC_MAX=25` | 31.0 % | 48.3 % | $77 | idem |

\*Con continuación óptima (DP, requiere sizing adaptativo) / con la política heurística de la columna.

**Mi lectura:** A. (1) Perder el intento mañana cuesta $49 + ~3 días, no capital; (2) el costo de bolsillo esperado hasta pasar es prácticamente el mismo con cualquier tamaño; (3) B/C bajan P(pase) y alargan el tiempo si no vienen con una regla de continuación, y esa regla no está desplegada. **Lo que sí vale la pena hacer, y es gratis:** si mañana sale TP, el balance quedará en ≈ 52,802–52,902 y el día siguiente conviene `GLITCH_PI_NC_MAX = ⌈faltante/35⌉` (≈ 3–6 contratos): sube el pase de ese tramo de ~62 % a ~91–95 % y baja de 38 % a 5–9 % la probabilidad de “quemar la cuenta a $100 de la meta”.

Si Eric prioriza *no ver la liquidación mañana* sobre P(pase), B es la opción defendible: la pérdida es −3.3 pp (continuación óptima) y el costo de bolsillo igual, pero hay que aceptar que tras un SL (18.7 %) el intento queda casi muerto.

## 9. Supuestos y lo que NO sé

- **Estado de partida** (bal/pico 51,401.2; piso 49,401.2; neto vs bruto del +$1,450): parametrizado, **a confirmar con TopstepX** (`pnl` vs `pnl_real`).
- **Consistencia:** el encargo usa “mejor día < $1,650”; la regla oficial (log 24-sep; el dashboard de Eric debe confirmarlo) sube el objetivo a mejor_día/0.55 (= misma cosa solo si el beneficio es exactamente $3,000). `core/prop_firm.py` en `main` todavía dice 50 % estricto. No liga con TP 32 y nc ≤ 40.
- **El MLL se traba por saldo de cierre (EOD) o intradía:** asumido EOD para el pico, liquidación en tiempo real (encargo §1). NO VERIFICADO en la práctica.
- **Slippage:** N = 2 mediciones. Todo el análisis de tamaño es robusto a ello, **el de TP/nc no lo es** (§6).
- **Los días son iid** (o bloques de 5): una sola historia de 492 días, barras de 5 min, un solo producto. No hay deriva ni autocorrelación que explotar (Parte B).
- **Orden dentro de la barra** desconocido (ambos reportados).
- **El 14 es sensible al slip de salida supuesto** (3 ticks): sigue en 14 hasta 10 ticks de salida y baja a 13 con ≥ 11 (14·$142.47 = $1,995 con 10 ticks).
