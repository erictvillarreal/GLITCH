# resultados_H5 — productos: riesgo por dólar, correlaciones y límites

## 1. Riesgo por dólar con la geometría del Combine escalada al rango del producto (MLL $2,000)

Geometría de MES (liquidación a 40 ticks = 0.23 del rango mediano de la ventana, TP 32 = 0.19) trasladada a cada producto **en unidades de su propio rango**; nc = lo necesario para que la liquidación cueste $2,000, topado por el límite del plan. **Si el tope impide usar todo el presupuesto, el TP paga menos y hacen falta más TP para los $3,000 (proxy de dificultad).**

| producto | rango mediano ticks | liquidación (ticks) | TP (ticks) | nc necesarios para $2,000 | tope Combine 50K | nc usable | $ por TP (neto de comisión) | TP necesarios para $3,000 | comisión % del $ por TP | volumen/barra de entrada | estado |
|---|---|---|---|---|---|---|---|---|---|---|---|
| MES | 172 | 40 | 32 | 40 | 50 | 40 | $1,551 | 2 | 3.0 % | 13,817 | rango MEDIDO (2 años); topes: SPECS 25-ago |
| MNQ | 866 | 201 | 161 | 20 | NO VERIFICADO | — | $1,586 | — | 1.5 % | 20,988 | rango MEDIDO (2 años); topes: SPECS 25-ago |
| M2K | 246 | 57 | 46 | 70 | 50 | 50 | $1,089 | 3 | 5.3 % | 909 | rango MEDIDO (2 años); topes: SPECS 25-ago |
| MGC | 420 | 98 | 78 | 20 | 30 | 21 | $1,598 | 2 | 2.5 % | 1,102 | rango MEDIDO (2 años); topes: SPECS 25-ago |
| MCL | 109 | 25 | 20 | 80 | 30 | 30 | $548 | 6 | 8.6 % | 559 | rango MEDIDO (2 años); topes: SPECS 25-ago |

Lectura: con la geometría relativa al rango, MES necesita ≈ 40 contratos y 2 TP (hoy). **MGC sí puede usar todo el presupuesto de $2,000 con ≈ 20 micros (tope 30) y 2 TP; M2K (necesita 70, tope 50) y MCL (necesita 80, tope 30) no pueden**, y MCL además paga el doble de fricción (8.6 % del TP) y necesita 6 TP; MNQ necesita ≈ 20 contratos (tope NO VERIFICADO). La fricción (comisión como % del $ por TP) va de 1.5 % (MNQ) a 8.6 % (MCL). **Las diferencias reales son el tope de contratos, la fricción y el volumen de la barra de entrada.**

## 2. Correlación de los retornos de la ventana (misma ventana de cada producto, 2 años, días comunes)

| | MES | MNQ | M2K | MGC | MCL |
|---|---|---|---|---|---|
| **MES** | 1.00 | 0.97 | 0.90 | 0.17 | 0.13 |
| **MNQ** | 0.97 | 1.00 | 0.87 | 0.19 | 0.12 |
| **M2K** | 0.90 | 0.87 | 1.00 | 0.17 | 0.06 |
| **MGC** | 0.17 | 0.19 | 0.17 | 1.00 | -0.07 |
| **MCL** | 0.13 | 0.12 | 0.06 | -0.07 | 1.00 |

(444 días comunes; los retornos van de la entrada al flatten de cada producto, **no del mismo intervalo**: MGC 7:15–14:30, el resto 9:35–14:30. Estado: MEDIDO.) **Hecho clave:** MES, MNQ y M2K se mueven casi juntos (ρ 0.87–0.97): un segundo producto *de índices* no diversifica nada; **MGC y MCL tienen ρ ≈ 0.1–0.2 con MES.** **MYM:** sin datos de 5 min locales y sin descargar el Dow diario: **DESCONOCIDO** (se espera ρ alta con los demás índices; NO medido).

## 3. Dos preguntas separadas

**(a) Producto para el Combine (hoy MES).** Criterios: liquidez a la hora de entrada, tope que permita el presupuesto completo de $2,000, comisión relativa, geometría validada. **MES cumple los cuatro; MNQ cumple liquidez y costo relativo pero su tope y su geometría no están verificados; M2K/MGC/MCL tienen barras 15× más delgadas (40 contratos = 4–7 % de la barra) y, MGC/MCL, tope 30.** No hay evidencia en este repo de que otro producto mejore P(pasar) a igualdad de presupuesto: **la barrera efectiva es el MLL, no el producto**, y P(TP antes de liquidación) con martingala es 55.6 % en cualquiera.

**(b) Producto para la XFA (hoy MGC).** Criterios: rango por contrato, comisión, tope de micros de la XFA (MGC: 12/18/31 según saldo, `RULEBOOK_XFA.md`), reglas de noticias, correlación con el Combine. **MGC ($420 de rango mediano por contrato en la ventana de 7:15 a 14:30; ρ ≈ 0.17 con MES)** es coherente con el Combine de MES como par poco correlacionado. No se probó otro producto en la XFA con el motor de la Parte D (no hay geometría validada ni historia de pagos): **DESCONOCIDO**; cualquier cambio sería sobre todo de correlación entre cuentas (G4) y de comisión, no de dólares por cuenta demostrados.

**Hallazgo para G4 (b):** el par realista de dos productos para diversificar es **MES + MGC (ρ de retornos ≈ 0.17, MEDIDO)**, no MES + MNQ/M2K (ρ ≥ 0.87). Un Combine de **MGC con ≈ 20 micros** cabe en el tope y presupuesto (modelado, **sin geometría validada ni slippage medido**): es la prueba de segundo producto con más sentido.

**Qué marcaría la diferencia y cómo medirlo:** un segundo producto en una **cuenta Practice** durante 20–30 sesiones (slippage, liquidez, fills) antes de cualquier prueba en Combine/XFA.