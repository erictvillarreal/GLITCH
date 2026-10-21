# REPORTE E — Búsqueda de ventaja direccional real (objetivo WR 51–52 %) — 21-oct-2026

Rama `experimentos-research` (local, sin push). **Nada desplegado; nada tocó `main`, el Pi, Railway ni credenciales.** Carpeta `glitch/experimentos/direccion_e/`. Todo reproducible (semilla 20261021); pre-registro [`PREREGISTRO_E.md`](PREREGISTRO_E.md) (G0, commit `e1218a1`, antes de calcular ninguna regla) + Enmiendas 1 y 2 (fechadas; la 2 se escribió sabiendo E1/E2 y antes de E4/E5).

## 1. Resumen (10 líneas)
1. **Ninguna de las 16 pruebas calculadas pasa G2.** Tres pasan G2(1) (Holm < 0.05): E1 MES r12 (p Holm 0.007), E4 cambio de mes (0.015), E1 MES SMA (0.035) — **las tres son el sesgo LARGO del S&P** (sube el 53.5 % de los días apertura→cierre en 36 años), no una señal: ninguna supera a «siempre LARGO» (E1: 2/10 y 1/10 bloques; E4: empate por construcción; diferencia de E4 contra el resto de días +0.9 pp [−1.5, +3.2]). [`RESULTADOS_E_G2.md`](RESULTADOS_E_G2.md)
2. **MGC (oro): cero señal.** E1 sobre GLD 2004→2026: 51.0 % [49.3, 52.7] (p 0.51); SMA 50.2 %. Intradía (7:15 CT, 2 años): la mejor, continuación 53.6 %, **iguala a «siempre LARGO» (53.4 %, el oro subió en la ventana)** y su p ajustado es 1.0.
3. **Las pruebas intradía no tienen potencia**: n ≈ 490 días → IC95 ±4.5 pp; hace falta una exactitud puntual ≳ 56–57 % para pasar G2(1) con 18 comparaciones, y G2(3) no es evaluable con 2 años. Se reportan como «sin potencia», no «sin efecto».
4. **Hallazgo metodológico (importante para el protocolo):** el umbral «exactitud > 51 %» de G2(1) está **por debajo de la tasa base de días alcistas de un índice (53.5 %)**: «siempre LARGO» lo pasa solo. Y exactitud de signo ≠ valor: 53.5 % de días alcistas equivale a **μ/σ = +0.024**, es decir **≈ WR 51 % en la tabla de valor**, y vale **≈ +$170/año** en el Combine (P0 mezcla $1,481 → $1,647), **menos que el umbral de $500 de G3**. En la ventana real de MES (2024–26) «siempre LARGO» tuvo μ/σ = −0.003.
5. **Valor de un punto de WR** (cadena Combine → XFA, reglas verificadas, plan 3×364, mezcla de slip): **50→51 %: +$1.1k/año por cuenta; 51→52 %: +$1.4k** (728×3: +$1.3k / +$1.9k; 4→1 micros: +$0.9k / +$1.1k). WR de equilibrio **48.6 %** (47.4–49.3 % según slip del Combine). Alcanzar 51–52 % valdría **+$1.1k a +$2.5k/año por cuenta** sobre los $1.3k de hoy: **eso es lo que está en juego, y no existe evidencia de que se pueda obtener.** [`resultados_E_valor.md`](resultados_E_valor.md)
6. **No se puede medir en vivo**: distinguir 52 % de 50 % con potencia 80 % exige **3,886 trades decididos ≈ 8,800 sesiones de MGC (~35 años)**; 55 % exige 620 (≈ 1,400 sesiones). Una ventaja de 1–2 pp **solo puede validarse con historia larga**, no con paper en sombra de 30 días.
7. **Riesgo/kill-switch:** la especificación (60 decisiones, piso 45 %) dispara en **68 % de los años aun si la regla acierta de verdad 52 %** (215 decisiones/año); con 200 decisiones y piso 44 % baja a 2 % y detecta una regla de 45 % en 46 % de los años. Función pura + 6 pruebas deterministas: `killswitch_NO_DESPLEGAR.py` (**NO DESPLEGAR / NEEDS HUMAN REVIEW**, regla 4 de CLAUDE.md).
8. **Omitido, declarado:** E3 (CPI/NFP/PPI: sin calendario verificable, BLS devuelve 403) y E6 (sin intradía nocturno limpio). Cuentan como p = 1 en Holm.
9. **Recomendación:** **no cambiar la lógica de dirección** (`alternate` se queda); ninguna regla justifica tocar capital. La palanca que sí está medida está en la estructura (Partes A/D: +$1.0–1.5k/año con finish-line y 728×3), no en la dirección.
10. Verificación: suite base 492 pasa; `git diff origin/main -- glitch/ ':!glitch/experimentos'` vacío (ver §6).

## 2. ¿Pasa alguna regla G2? Tabla (detalle en `RESULTADOS_E_G2.md`)
| prueba | exactitud | p sin ajustar | p Holm | vs `alternate` / vs LARGO (bloques) | veredicto |
|---|---|---|---|---|---|
| E1 MES r12 (^GSPC 1990→) | 52.9 % | 0.0004 | 0.007 | 9/10 · **2/10** | = sesgo largo; **no pasa** |
| E4 cambio de mes (^GSPC) | 54.1 % | 0.0009 | 0.015 | 9/10 · empate por construcción | = sesgo largo (+0.9 pp vs resto, IC incluye 0); **no pasa** |
| E1 MES SMA50/200 | 52.5 % | 0.0022 | 0.035 | 9/10 · **1/10** | **no pasa** (G2(3) falla) |
| E2 MES continuación \|R\| > mediana | 54.9 % | 0.066 | 0.98 | 7/10 · 4/10 | sin potencia; 2 años |
| E2 MGC continuación (todos) | 53.6 % | 0.16 | 1.0 | 7/10 · 4/10 | = LARGO del oro (53.4 %) |
| E1 MGC r12 / SMA (GLD) | 51.0 % / 50.2 % | 0.51 / 0.88 | 1.0 | 6/10 · 2/10 / 5/10 · 4/10 | cero señal |
| E5 MES brecha (reversión / continuación) | 45.4 % / 54.6 % | 0.84 / 0.33 | 1.0 | 5/10 · 2/10 / 5/10 · 5/10 | sin potencia; ninguna |
| E4 FOMC (46 reuniones 2021–26; fechas de federalreserve.gov) | 45.7 % | 0.67 | 1.0 | 2/10 | ninguna (en la ventana real MES sube 6 de 16) |
| E2 reversiones (4 pruebas) | 45–48 % | 0.91–0.98 | 1.0 | 4/10 | ninguna |

## 3. Datos y límites (qué se puede y no se puede afirmar)
- **Largo plazo** (Yahoo, crudo, `data/LEEME.txt`): `GLD` (2004→) y `^GSPC` (1990→) como proxies sin rolls de MGC y MES; resultado primario apertura→cierre. `GC=F` se descartó antes de calcular reglas (Open no comparable, Enmienda 1). Los proxies no son MGC/MES (ETF/índice): la conclusión sobre MGC/MES es por analogía.
- **Corto plazo** (5 min, 2 años): contrato dominante por día (el parquet de MGC intercala dos contratos); noches con cambio de contrato descartadas. G1: `RESULTADOS_E_G1.md`, `test_data_audit.py` (5) y `test_signals_5min.py` (5: R/gap a mano, truncar la serie no cambia la señal, NaN al cambiar de contrato, umbral previo sin el día actual).
- **Oro nocturno:** GLD sube 53.2 % cierre→cierre pero 50.2 % apertura→cierre: la deriva del oro ocurre fuera del horario regular, y **Topstep exige estar plano a las 3:10 PM CT** (`RULEBOOK_XFA.md` 1.9, verificado) → no explotable con este esquema.
- **El WR de MES con TP 32 / SL 100 es ≈ 55–58 % para cualquier regla, incluso aleatoria** (asimetría del bracket); una ventaja se mide contra los controles de la misma ventana, no contra 50 %.

## 4. Valor de cada punto de WR (§4; `resultados_E_valor.md`, 40,000 trayectorias, bancos de 100,000)
Neto anual por cuenta, plan 3×364, stop 0.5, Combine hoy (P0), mezcla de slip {1,3}: WR 47 % **−$1.4k** · 48 % −$0.5k · 49 % +$0.3k · **50 % +$1.3k** · 51 % +$2.5k · 52 % +$3.8k · 53 % +$5.7k · 55 % +$11.1k. Con finish-line (P3): 50 % $2.3k · 52 % $5.0k. **WR de equilibrio 48.6 %** (P3: 47.7 %). El cobrado por XFA pasa de $644 (50 %) a $750 (51 %), $912 (52 %), $1,924 (55 %). Con stop exacto (convención optimista) los netos son ≈ +$0.8–1.1k mayores. Tabla D (muestra para distinguir de 50 %, binomial exacta, potencia 80 %): 47/53 %: 1,734 trades; 48/52 %: 3,886; 49/51 %: 15,486; 55 %: 620; 56 %: 438.

## 5. Riesgo (§5; `RESULTADOS_E_riesgo.md`)
- **Inversión de régimen:** las reglas E1 tienen 27–45 % de años por debajo de 50 % (peor año 38–45 %, hasta 3 años seguidos). En ^GSPC la regla r12 **es idéntica a «siempre LARGO» en 24 de 36 años**.
- **Kill-switch:** ver punto 7; el diseño (ventana, piso) es una decisión humana: se aceptan falsos disparos porque el estado de reposo es `alternate` (el actual). Re-armar es siempre humano.
- **Mezcla segura:** E1 ya opera solo con |r12| ≥ 0.5 σ (57–72 % de los días); el valor de cualquier ventaja se prorratea por esa fracción. No se mide ventaja nueva porque ninguna regla pasa G2.

## 6. Lista priorizada (máx. 8). [PR] = pre-registrable; [PH] = exploración posterior, no hallazgo
1. **[PR] Mantener `alternate`; no tocar la dirección.** Costo $0. Evita riesgo con una evidencia nula.
2. **[PR] Historia intradía larga (≥ 5–10 años de 5 min de MGC/MES vía `retrieveBars`, que requiere las credenciales de Eric/Pi, no de este agente)** y repetir E2/E5 pre-registrados con potencia real y G2(3) evaluable. Es el dato que más información aporta.
3. **[PR] E3 con calendario verificable** (BLS schedule, bajado a mano o con el navegador) + historia larga de 5 min; hoy sin potencia.
4. **[PR, para el protocolo] Cambiar la línea base de G2 en índices a «siempre LARGO» (o a una prueba de diferencia contra el resto de días) y traducir exactitud → μ/σ → WR con la tabla A antes de G3.** Evita falsos candidatos como E4/E1-MES.
5. **[PR] Aplicar las palancas estructurales ya medidas** (finish-line, 728×3 o 4→1): +$1.0–1.5k/año por cuenta, más seguro que buscar dirección (Partes A/D; requieren revisión humana).
6. **[PH] «Siempre LARGO» en el Combine de MES:** vale ≈ +$170/año con el μ/σ de 36 años (−$215 con el de la ventana real); **archivado por G3 (< $500)**.
7. **[PR] Otros productos no correlacionados (MCL, 6E, ZN: datos de 5 min locales ya existen)** con el mismo pre-registro y corrección de Holm ampliada; esperanza baja (cada producto añade comparaciones).
8. **[PH] Medir el slippage y el WR vivos con el parche C3** (Parte D): es lo único que cierra el hueco de «WR no medido» a su ritmo (≈ 1,400 sesiones para decidir 55 % vs 50 %).

## 7. Qué NO se hizo / limitaciones
Sin `retrieveBars` (credenciales); sin E3/E6; proxies diarios en vez de MGC/MES para el largo plazo; bootstrap por bloques de 5 días supone dependencia corta; el WR entre decididos usa la mecánica del motor con slip 0 (MES también 1 y 3); el valor usa deriva calibrada sobre la trayectoria real (supuesto). La exploración posterior (`exploracion_posterior.py`, `RESULTADOS_E_posterior.md`) **no es hallazgo**.
