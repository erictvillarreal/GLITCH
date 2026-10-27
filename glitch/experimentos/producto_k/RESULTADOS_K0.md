# RESULTADOS_K0 — Inventario de datos (producto × fuente × años × granularidad)

Martes 27-oct-2026 · BORRADOR · Fuentes revisadas: archivos locales (`data_cache/*.parquet`, leídos hoy), páginas públicas de Massive, Databento y ProjectX (consultadas hoy con WebFetch/WebSearch: **extracciones automáticas de la página, no la página literal ⇒ confirmar antes de pagar**), consultas directas a Yahoo (hoy). **No tengo llaves** de Massive, Databento ni ProjectX en esta sesión: lo que depende de ellas queda **DESCONOCIDO** y se cierra con tres scripts de solo lectura que Eric corre (sección 5). Estados: MEDIDO (lo corrí hoy), DOCUMENTADO (lo dice la página de la fuente), DESCONOCIDO.

## 1. Resumen

1. **Hoy solo tenemos 2 años de barras de 5 min** (27-ago-2024 → 26-ago-2026), en ventanas de sesión fijas (CT 8:30–15:00; MGC 7:00–15:00; ZC 8:30–13:15) y solo para MES, MNQ, M2K, M6E, MCL, MGC, ZN, ZC y MBT (223 días). **MYM no tiene datos locales.** MEDIDO.
2. **Con 2 años una prueba direccional solo detecta efectos ≥ 6.2 pp (una prueba) u 8.8 pp (Holm sobre 26)** a 80 % de potencia (`resultados_K0_mde.md`). Un punto de acierto vale ≈ $1.0k/año por cuenta: **los datos actuales no pueden validar ningún efecto que importe en dinero.** MODELADO.
3. **Ampliar la historia intradía cuesta poco y se puede hacer una sola vez:** Massive Futures Developer ($79/mes, «5 años») o Advanced ($199/mes, «7+ años»; en vivo) — pagar **un mes**, bajar todo y cancelar; Databento: «16+ años» de barras de 1 min con costo por GB (la página no publica la tarifa; el script `k0c` da el costo exacto sin gastar créditos) y $125 de créditos gratis. DOCUMENTADO.
4. **Los micros siguen el precio de los contratos grandes** (MES≈ES, MNQ≈NQ, MYM≈YM, M2K≈RTY, MGC≈GC, MCL≈CL, M6E≈6E): para estructura y volatilidad la historia larga de los grandes es válida con el mismo número de ticks por unidad de precio; el valor del tick y el tope de contratos sí son los del micro (K2). Supuesto declarado (SUPUESTO), a confirmar con una ventana de traslape.
5. **ProjectX `retrieveBars`:** máximo 20,000 barras por llamada (DOCUMENTADO); **profundidad y límites de tasa no documentados** ⇒ DESCONOCIDO hasta correr `k0b` en el Pi. Es además la única fuente con datos casi en tiempo real incluida en lo que ya pagamos (Massive Starter va con 10 minutos de retraso).
6. **Yahoo diario sigue siendo la única historia larga gratuita** (6,600 días ≈ 26 años en ES/NQ/GC/CL/6E/ZN…): sirve para volatilidad y reglas diarias, **no** para brackets intradía (los dos extremos del bracket pueden tocarse el mismo día y OHLC diario no dice cuál primero); sus series `=F` son continuas **sin ajuste** (saltos en cada roll) — SUPUESTO conocido, no medido aquí.

## 2. Lo que hay hoy en disco (MEDIDO)

| archivo | filas (5 min) | rango | días | contratos distintos | ventana de sesión | barras/día |
|---|---|---|---|---|---|---|
| `mes_5min_2y` | 39,967 | 2024-08-27 → 2026-08-26 | 515 | 9 | 8:30–15:00 CT | 78 |
| `mnq_5min_2y` | 39,256 | 2024-08-26 → 2026-08-24 | 506 | 9 | 8:30–15:00 CT | 78 |
| `m2k_5min_2y` | 39,967 | 2024-08-27 → 2026-08-26 | 515 | 9 | 8:30–15:00 CT | 78 |
| `mgc_5min_2y_corrected_window` | 49,496 | 2024-09-06 → 2026-09-04 | 515 | 13 (⚠ barras de 2 contratos intercaladas en 44 % de los días: usar el filtro de contrato dominante, Parte D) | 7:00–15:00 CT | 96 |
| `mcl_5min_2y` | 40,325 | 2024-08-27 → 2026-08-26 | 516 | **25** (⚠ rolls: verificar contrato dominante por día antes de usar) | 8:30–15:00 CT | 78 |
| `m6e_5min_2y` | 40,494 | 2024-08-27 → 2026-08-26 | 517 | 9 | 8:30–15:00 CT (**no** cubre las horas líquidas del euro en Londres/NY temprano) | 78 |
| `zn_5min_2y` | 40,069 | 2024-08-27 → 2026-08-26 | 517 | 9 | 8:30–15:00 CT (cubre solo parte de la sesión líquida de bonos) | 78 |
| `zc_5min_2y` | 29,028 | 2024-08-27 → 2026-08-26 | 502 | 11 | 8:30–13:15 CT | 58 |
| `mbt_5min_2y` | 16,971 | 2024-08-26 → 2026-08-25 | **223** | 11 | 8:30–15:00 CT | 76 (volumen bajo: cobertura parcial) |
| MYM | — | — | — | — | — | **sin datos** |

Consecuencia para K3: las **horas de entrada** a barrer solo pueden caer dentro de esas ventanas (en MGC 7:00 en adelante; en FX, energía y bonos faltan las horas líquidas de la mañana); para barrerlas hay que bajar sesiones completas (Databento/Massive).

## 3. Producto × fuente (años de historia útil)

| producto (micro) | proxy grande | local (5 min) | Yahoo diario del proxy | Massive Futures (todos los tiers cubren CME/CBOT/NYMEX/COMEX) | Databento GLBX.MDP3 | ProjectX |
|---|---|---|---|---|---|---|
| MES | ES | 2.0 a | 2000-09 → hoy (≈ 26 a, 6,635 d) | Starter/Basic 2 a · Developer 5 a · Advanced 7+ a (por producto: DESCONOCIDO, `k0a`) | 16+ a (ES) | DESCONOCIDO (`k0b`) |
| MNQ | NQ | 2.0 a | 2000-09 → hoy (6,635 d) | ídem | 16+ a (NQ) | ídem |
| MYM | YM | **0** | 2002-04 → hoy (6,231 d) | ídem | 16+ a (YM) | ídem |
| M2K | RTY | 2.0 a | **2017-07** → hoy (2,344 d) | ídem | 16+ a (RTY) | ídem |
| MGC | GC | 2.0 a | 2000-08 → hoy (6,648 d) | ídem | 16+ a (GC) | ídem |
| MCL | CL | 2.0 a | 2000-08 → hoy (6,653 d) | ídem | 16+ a (CL) | ídem |
| M6E | 6E | 2.0 a | 2000-09 → hoy (6,639 d) | ídem | 16+ a (6E) | ídem |
| M6B | 6B | — | 2000-10 → hoy (6,622 d) | ídem | 16+ a (6B) | ídem |
| ZN | ZN | 2.0 a | 2000-09 → hoy (6,632 d) | ídem | 16+ a | ídem |
| ZB / ZF / ZT | — | — | 2000-09 / 2000-09 / 2000-06 (≈ 6,600 d) | ídem | 16+ a | ídem |
| ZC / ZS / ZW | — | ZC 2.0 a | 2000-07 / 2000-09 / 2000-07 (≈ 6,650 d) | ídem | 16+ a | ídem |
| MBT / BTC (cripto) | BTC=F | 223 d | 2017-12 → hoy (2,231 d) | ídem | CME BTC: desde su lanzamiento (fecha: DESCONOCIDO) | ídem |
| HG, SI (SIL), NG | — | — | 2000-08 (≈ 6,650 d) | ídem | 16+ a | ídem |

«16+ a» es lo que dice la página de Databento para L0 (OHLCV); la fecha de inicio de cada producto en GLBX.MDP3 y la de lanzamiento de cada micro: DESCONOCIDO (`k0c` imprime `get_dataset_range`). Los micros de índice nacieron en 2019 y MGC/MCL después; **antes de su lanzamiento solo existe el contrato grande**, por eso el proxy.

## 4. Fuentes — condiciones y costos

| fuente | granularidad | profundidad | latencia | costo (documentado) | notas |
|---|---|---|---|---|---|
| **Massive Futures** (página `massive.com/futures`, hoy) | minuto y segundo (Basic: solo minuto) | Basic $0: 2 a, **5 llamadas/min** · Starter $29: 2 a · Developer $79: 5 a · Advanced $199: «7+ años» | Basic: no listado · Starter y Developer: **10 min de retraso** · Advanced: tiempo real | $0 / $29 / $79 / $199 al mes (facturación anual −20 %; «solo no profesionales») | el log del repo (4-sep) decía Developer $79 y «enterprise $999 por exchange»: **la página de hoy lista Advanced $199 y no menciona los $999** — confirmar. Roll y contratos: hay que armar el calendario propio (`/futures/v1/contracts`) y filtrar el contrato dominante por día |
| **Databento** (`databento.com/pricing`, hoy) | OHLCV-1s/1m/1h/1d (L0); trades y libro (L1–L3) | «16+ años» L0 | histórico | pago por uso: **$/GB sin publicar** (estimación de ejemplo «< $0.01» para 30 días de un símbolo); planes: Standard $199/mes (datos en vivo, sin cuota de licencia), Plus $1,750 y Unlimited $4,500 (anuales, con ventas); **$125 de créditos gratis** para cuentas nuevas (vencen a los 6 meses) | las barras de 1 min de ~15 símbolos × 16 años ≈ 3–4 GB sin comprimir (estimación mía: 56 bytes por barra × ~350k barras/año/símbolo; MODELADO) — el script `k0c` da el costo exacto |
| **ProjectX / TopstepX** `History/retrieveBars` | segundo, minuto, hora, día, semana, mes; `unitNumber` agrega | **no documentada** | casi tiempo real (a medir: edad de la última barra) | ya incluido en la API de $14.30/mes por cuenta | máx. **20,000 barras por llamada**; cada `contractId` es un vencimiento concreto (la serie continua hay que armarla); los vencidos pueden no estar listados |
| **Yahoo** `=F` | diario (1 m: 8 días; 5 m–15 m: 60 días; 1 h: ≈ 2 años) | ver sección 3 | — | $0 | continuas sin ajuste; no sirve para brackets intradía |

## 5. Scripts de solo lectura para cerrar los DESCONOCIDOS (los corre Eric)

| script | dónde | qué cierra | cómo |
|---|---|---|---|
| `k0b_projectx_depth.py` | **Pi** | profundidad real de ProjectX por producto, contrato activo (`activeContract`), precio actual, **latencia de la barra**, horario de la última sesión, si lista contratos vencidos y su profundidad | copiar el archivo al Pi (`scp`) y `cd ~/glitch/glitch && ~/glitch-env/bin/python ~/k0b_projectx_depth.py --env-file ~/.glitch_pi.env \| tee ~/k0b_salida.txt`; ≤ 400 llamadas, ≈ 3/s; **no** toca órdenes ni posiciones (6 pruebas con cliente falso lo verifican) |
| `k0a_massive_probe.py` | Mac o Pi con `MASSIVE_API_KEY` en el entorno | profundidad por producto de **tu** plan de Massive (contratos + barras de 5 min a 0, 1, 2, 3, 5, 7, 10 años), resoluciones de 1 s/1 min/5 min y su retraso | `MASSIVE_API_KEY=… python3 k0a_massive_probe.py --json k0a.json` (con plan Basic: `--sleep 13`) |
| `k0c_databento_cost.py` | Mac con `DATABENTO_API_KEY` (y `pip install databento`) | costo exacto, registros y GB facturables de 1 min de ~15 símbolos desde 2010-06-06; rango real del dataset | `DATABENTO_API_KEY=… python3 k0c_databento_cost.py` — solo `metadata.*`: **no descarga ni gasta créditos** (no verificado contra la API real: no tengo llave) |

Pruebas: `test_k0b.py` (6), `test_k0ac.py` (3) — clientes falsos, sin red.

## 6. Potencia (MDE) — `resultados_K0_mde.md`

| fuente | n sesiones | MDE una prueba | MDE Holm-26 |
|---|---|---|---|
| local, 2 años | 505 | 6.2 pp | 8.8 pp |
| Massive Developer (5 a) | 1,260 | 3.9 pp | 5.6 pp |
| Massive Advanced (7+ a) | 1,764 | 3.3 pp | 4.7 pp |
| Databento (16+ a, proxy de los grandes) | 4,030 | 2.2 pp | 3.1 pp |
| Yahoo diario (26 a, reglas diarias) | 6,600 | 1.7 pp | 2.4 pp |
| 6 productos con ρ̄ = 0.17 y Databento 16 a (n efectivo ≈ 12,900) | — | — | 1.7 pp |

Un efecto que valga ≥ $1.5k/año (1.5 pp) con Holm-26 necesita ≈ 17,000 sesiones efectivas: solo se alcanza **agrupando varios productos poco correlacionados con 15–16 años de datos**. Para K5 esto significa: con datos locales **todas** las pruebas direccionales son «sin potencia»; con Databento solo las reglas agrupadas llegan a ≈ 1.7 pp.

## 7. Qué decide K0 sobre el alcance

- K3 (estructura) y K4 (volatilidad) **no necesitan potencia sobre el acierto** pero sí **más historia y sesiones completas** para que el neto anual no dependa de 2 años de régimen: conviene **una descarga única** (Databento si el costo de `k0c` es de pocas decenas de dólares; si no, un mes de Massive Developer/Advanced).
- K5 (direccional) solo tiene sentido si la descarga larga se hace; con 2 años sería repetir la Parte E.
- **Decisión que necesito de Eric:** ¿qué cuentas de datos tiene (Massive: plan y fecha de renovación; Databento: créditos; Tradovate: ¿acceso a datos históricos?) y los tres scripts corridos.
