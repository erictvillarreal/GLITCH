# RESULTADOS_E_riesgo — §5: inversión de régimen, kill-switch y mezcla segura

## (a) Inversión de régimen por año — reglas E1 (apertura→cierre, días operados) frente a siempre LARGO

| regla | años evaluados | años con exactitud < 50 % | peor año | racha más larga de años < 50 % | años regla > LARGO / igual / < LARGO | cambios de signo de la señal por año (mediana) | % de días con señal fuerte |
|---|---|---|---|---|---|---|---|
| MGC r12 (GLD) | 22 | 9 (41 %) | 2016: 38 % | 3 | 5 / 12 / 5 | 8 | 57 % |
| MGC sma (GLD) | 22 | 10 (45 %) | 2016: 43 % | 3 | 3 / 7 / 12 | 1 | 96 % |
| MES r12 (^GSPC) | 36 | 10 (28 %) | 2016: 41 % | 3 | 4 / 24 / 8 | 8 | 72 % |
| MES sma (^GSPC) | 37 | 10 (27 %) | 1990: 45 % | 2 | 8 / 12 / 17 | 1 | 98 % |

Lectura: en los índices la regla de tendencia es SIEMPRE LARGO en la mayoría de los años (igual a LARGO), de modo que su exactitud es la deriva del mercado, no una señal propia. Una regla de tendencia lenta que acierta >50 % en promedio sigue teniendo años por debajo de 50 %; el kill-switch debe soportar rachas así sin disparar por ruido (b).

## (b) Kill-switch (WR móvil de las últimas W decisiones cerradas < piso → `alternate`): falsos disparos y potencia

Simulación de decisiones TP/SL independientes con WR verdadero w (semilla 20261021, 4,000 trayectorias). “Año” = 215 decisiones (MGC: 488 días × 44 % decididos) o 480 (MES). Disparo = al menos una ventana con WR < piso.

| W | piso | N decisiones | w = 40 % (rule rota) | w = 45 % | w = 50 % | w = 52 % (regla buena) | w = 55 % | mediana de decisiones hasta el disparo si w = 45 % |
|---|---|---|---|---|---|---|---|---|
| 60 | 45 % | 215 | 100 % | 98 % | 81 % | 68 % | 42 % | 62 |
| 60 | 45 % | 480 | 100 % | 100 % | 99 % | 93 % | 74 % | 63 |
| 120 | 45 % | 215 | 99 % | 83 % | 38 % | 21 % | 6 % | 120 |
| 120 | 45 % | 480 | 100 % | 99 % | 74 % | 51 % | 18 % | 122 |
| 120 | 43 % | 215 | 97 % | 69 % | 24 % | 12 % | 3 % | 121 |
| 120 | 43 % | 480 | 100 % | 97 % | 55 % | 31 % | 8 % | 143 |
| 200 | 45 % | 215 | 95 % | 58 % | 11 % | 4 % | 0 % | 200 |
| 200 | 45 % | 480 | 100 % | 93 % | 38 % | 16 % | 2 % | 200 |
| 200 | 44 % | 215 | 91 % | 46 % | 6 % | 2 % | 0 % | 200 |
| 200 | 44 % | 480 | 100 % | 88 % | 24 % | 9 % | 1 % | 212 |

Lectura: con W = 60 y piso 45 % (la especificación del encargo), una regla que SÍ acierta 52 % dispara casi seguro en un año de decisiones: el kill-switch protege, pero también descarta ventajas reales por ruido. Es una decisión de diseño (costo de un falso disparo = volver a `alternate`, que es el estado actual; costo de un falso negativo = operar una regla rota con capital): lo conservador es aceptar los falsos disparos. Propuesta con tests deterministas: `killswitch_NO_DESPLEGAR.py` + `test_killswitch.py` (NO DESPLEGAR).

## (c) Mezcla parcial segura (la regla decide solo con señal fuerte; `alternate` en el resto)

E1 con lectura 1 ya es una mezcla: opera solo si |r12| ≥ 0.5 σ anual. Fracción de días con señal fuerte (arriba) = peso de la regla; el valor de una ventaja Δ pp se prorratea por esa fracción. Con la ventaja que haría falta (≥ 1–2 pp de WR, §4), una mezcla con 50 % de días con señal da ≈ la mitad del valor ($/pp de §4 × fracción). No se mide ventaja nueva aquí: como ninguna regla pasa G2, la mezcla queda como diseño, no como resultado.
