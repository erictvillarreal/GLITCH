# resultados_C1 (generado por reconciliar.py)

T=20000 trayectorias por celda, 12 meses desde 19-oct-2026, 1 cuenta 50K; neto = payouts cobrados - fees (incluye tarifa inicial y activaciones) - $714 de costos compartidos. Formato: media / mediana / P(neto<0).

## Puente acumulativo: de la cifra del 26-sep a la convencion actual (una cuenta, 12 meses)

| paso (acumulativo) | mundo justo | real CON oro | real SIN oro | intentos / pases por ano (prom. 3 mundos) |
|---|---|---|---|---|
| S0 Convencion 26-sep (`engine_real`): TP40, reglas del motor validado, XFA serie fija, slip 0, SIN haircut | 6,021 / 5,307 / P(<0) 16% | 4,679 / 4,007 / P(<0) 20% | 2,640 / 2,027 / P(<0) 32% | 54 / 13.5 |
| S1 + haircut -25% de payouts (proxy de liquidacion XFA usado desde el 24-sep) | 3,177 / 2,633 / P(<0) 28% | 2,187 / 1,675 / P(<0) 33% | 609 / 141 / P(<0) 48% | 54 / 13.5 |
| S2 + TP 32 (aprobado 12-oct, NO desplegado) | 4,039 / 3,511 / P(<0) 21% | 2,960 / 2,478 / P(<0) 26% | 1,296 / 849 / P(<0) 40% | 45 / 14.4 |
| S3 + reglas de pago verificadas (min $125, ganancia neta desde el ultimo pago, topes) | 3,944 / 3,428 / P(<0) 21% | 2,914 / 2,449 / P(<0) 26% | 1,260 / 841 / P(<0) 40% | 45 / 14.3 |
| S4 + liquidacion XFA en tiempo real EXPLICITA (reemplaza el haircut) | 4,836 / 4,093 / P(<0) 21% | 3,555 / 2,902 / P(<0) 26% | 1,879 / 1,310 / P(<0) 37% | 50 / 16.1 |
| S5 + stop llenado en el extremo de la barra (slip 0.5) | 3,153 / 2,485 / P(<0) 30% | 2,632 / 1,997 / P(<0) 32% | 1,127 / 555 / P(<0) 44% | 53 / 16.9 |
| S6a + slippage de entrada 1 tick (lunes 19-oct), bracket anclado a la REFERENCIA como el Pi real | 2,861 / 2,195 / P(<0) 32% | 2,381 / 1,760 / P(<0) 34% | 900 / 334 / P(<0) 46% | 54 / 16.8 |
| S6b + slippage de entrada 3 ticks (martes 20-oct, inferido), idem | 310 / -451 / P(<0) 54% | -45 / -718 / P(<0) 57% | -1,096 / -1,680 / P(<0) 68% | 69 / 12.8 |

### Efecto de cada supuesto (diferencia de la MEDIA respecto al paso anterior, $/ano)

| paso | justo | CON oro | SIN oro |
|---|---|---|---|
| S1 haircut -25% de payouts (proxy de liquidacion XFA usado desde el 24-se | -2,845 | -2,492 | -2,031 |
| S2 TP 32 (aprobado 12-oct, NO desplegado) | +863 | +773 | +688 |
| S3 reglas de pago verificadas (min $125, ganancia neta desde el ultimo pa | -95 | -46 | -36 |
| S4 liquidacion XFA en tiempo real EXPLICITA (reemplaza el haircut) | +892 | +641 | +619 |
| S5 stop llenado en el extremo de la barra (slip 0.5) | -1,683 | -923 | -752 |
| S6a slippage de entrada 1 tick (lunes 19-oct), bracket anclado a la REFERE | -292 | -252 | -227 |
| S6b slippage de entrada 3 ticks (martes 20-oct, inferido), idem | -2,551 | -2,426 | -1,996 |

### Mapa: que version publicada corresponde a que paso

| version publicada | cifra publicada | paso que la reproduce | cifra reproducida aqui (real CON oro / SIN oro / justo, media) |
|---|---|---|---|
| `engine_real` 26-sep | media ~$4.6k (386/mes x12), mediana $3,532 | S0 | 4,679 / 2,640 / 6,021 |
| `lever_engine` 7-oct (structural-levers) | TP32: $3.3k / $1.9k / $3.7k (CON / SIN / justo) | S4 | 3,555 / 1,879 / 4,836 |
| doc 13-oct (T1, numero de planeacion ~$2,000) | nc40 TP32: $2.6k / $1.1k / $3.0k | S5 | 2,632 / 1,127 / 3,153 |

(Las tres cifras eran correctas PARA SU CONVENCION; difieren por supuestos concretos de la tabla de arriba, no por errores de calculo. El unico supuesto que ninguna de las tres modelaba como el Pi real es el ancla del bracket a la referencia.)

## Validacion cruzada: P(pase) por intento, Parte A vs motor (misma entrada 9:45 CT, TP32/SL100, nc40, cuenta nueva, slip de stop 0)

| slip de entrada (ticks) | Parte A (replay 492 dias, MC 20k) | motor ANCLA A LA REFERENCIA: real CON oro / SIN oro / justo | motor ancla al FILL (convencion anterior): real CON oro / SIN oro / justo |
|---|---|---|---|
| 0 | 31.4% [30.8,32.1] | 33.8% / 32.3% / 31.1% | 33.8% / 32.3% / 31.1% |
| 1 | 30.9% [30.3,31.6] | 33.0% / 31.4% / 30.1% | 31.6% / 29.8% / 29.0% |
| 2 | 18.0% [17.5,18.6] | 20.6% / 19.8% / 19.5% | 29.0% / 27.7% / 27.2% |
| 3 | 16.9% [16.3,17.4] | 19.6% / 18.8% / 18.2% | 27.7% / 26.3% / 25.5% |

Lectura: con slip 0 todos coinciden (31-34%). Con slip >= 2 solo la columna 'ancla a la referencia' (la mecanica REAL del Pi: pi_executor.py calcula TP/SL desde el ultimo close y luego manda la orden de mercado) reproduce el desplome de la Parte A; el ancla al fill (convencion de los reportes del 7 al 13-oct) lo subestima. Mecanismo: con nc=40 y TP 32, dos TP netos suman $3,002 con slip 1 (>= $3,000) pero $2,902 con slip 2 y $2,802 con slip 3 -> hace falta un TERCER TP y la probabilidad cae de ~30% a ~17%. Es un acantilado, no una pendiente.

## RTP (Responsible Trading Program), por primera vez modelado como REGIMEN alterno (no como probabilidad)

Fuente (help.topstep.com/13620045, leida 24-sep y citada en el log): el RTP es revision discrecional, no publica umbrales; consecuencias: DLL automatico en Combines nuevas ($1,000 en 50K) y XFA solo ruta Consistency (40%). NO existe dato para estimar la probabilidad de entrar al RTP; se reportan los dos regimenes puros y el neto de cada uno, y el lector pondera. El patron de G2 toca varios criterios (perdida mayor que ganancia, max position en la mayoria de trades, varias cuentas tocando el MLL el mismo dia).

| regimen (slip entrada 1, stop 0.5) | justo | CON oro | SIN oro |
|---|---|---|---|
| normal | 2,861 / 2,195 / P(<0) 32% | 2,381 / 1,760 / P(<0) 34% | 900 / 334 / P(<0) 46% |
| RTP: DLL $1,000 en el Combine + XFA ruta Consistency 40% | 780 / 63 / P(<0) 49% | 539 / -43 / P(<0) 51% | -517 / -1,135 / P(<0) 63% |

## Rango unico (una cuenta, TP32, liquidacion XFA explicita, stop 0.5, XFA vigente MGC 364x3)

| slippage de entrada | justo | CON oro | SIN oro |
|---|---|---|---|
| 0 ticks (optimista) | 3,153 / 2,485 / P(<0) 30% | 2,632 / 1,997 / P(<0) 32% | 1,127 / 555 / P(<0) 44% |
| 1 tick (lunes 19-oct) | 2,861 / 2,195 / P(<0) 32% | 2,381 / 1,760 / P(<0) 34% | 900 / 334 / P(<0) 46% |
| mezcla {1,3} 50/50 (observado, N=2) | 1,586 / 837 / P(<0) 43% | 1,168 / 464 / P(<0) 46% | -98 / -709 / P(<0) 57% |
| 3 ticks (martes 20-oct, inferido) | 310 / -451 / P(<0) 54% | -45 / -718 / P(<0) 57% | -1,096 / -1,680 / P(<0) 68% |

### Sensibilidad: primeros $10,000 de ganancias de por vida al 100% (help.topstep.com/8284233, leido 20-oct-2026: SOLO para traders que entraron al dashboard nuevo antes del 12-ene-2026; elegibilidad de Eric: NO VERIFICADA)

| slippage de entrada | sin beneficio | con beneficio (first100=10,000) |
|---|---|---|
| 1 tick, CON oro | 2,381 / 1,760 / P(<0) 34% | 3,145 / 2,616 / P(<0) 29% |
| 1 tick, SIN oro | 900 / 334 / P(<0) 46% | 1,584 / 1,037 / P(<0) 40% |
| mezcla {1,3}, CON oro | 1,168 / 464 / P(<0) 46% | 1,849 / 1,172 / P(<0) 40% |
| mezcla {1,3}, SIN oro | -98 / -709 / P(<0) 57% | 505 / -116 / P(<0) 51% |

(tiempo total 38s)