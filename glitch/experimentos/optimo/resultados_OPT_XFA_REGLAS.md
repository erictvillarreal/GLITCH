# resultados_OPT_XFA_REGLAS — ¿una regla simple (n micros hasta un saldo U, luego menos) se acerca al techo de la DP?

Plan elegido en el 60 % viejo (entrenamiento) y evaluado en el 40 % reciente (prueba), con 3 micros fijos como base pareada. Se muestran las 3 mejores reglas por bracket.

| bracket SL = TP | regla | cobrado (entrenamiento) | **cobrado (prueba)** | 3 fijos (prueba) | Δ pareado ± IC95 | P(≥ 1 pago) | vida (días) |
|---|---|---|---|---|---|---|---|
| 364 | 5 micros mientras saldo < $1,500, luego 1 | $787 | **$759** | $583 | +176 ± 16 | 30 % | 8.3 |
| 364 | 5 micros mientras saldo < $2,000, luego 2 | $785 | **$715** | $583 | +131 ± 15 | 21 % | 6.7 |
| 364 | 5 micros mientras saldo < $2,000, luego 1 | $780 | **$759** | $583 | +176 ± 17 | 25 % | 7.2 |
| 546 | 5 micros mientras saldo < $2,000, luego 1 | $893 | **$873** | $664 | +209 ± 23 | 27 % | 8.6 |
| 546 | 5 micros mientras saldo < $1,500, luego 1 | $886 | **$885** | $664 | +221 ± 22 | 30 % | 9.4 |
| 546 | 5 micros mientras saldo < $2,000, luego 2 | $883 | **$824** | $664 | +160 ± 20 | 22 % | 7.8 |
| 728 | 5 micros mientras saldo < $2,000, luego 1 | $960 | **$1,030** | $789 | +240 ± 29 | 27 % | 10.2 |
| 728 | 5 micros mientras saldo < $2,000, luego 2 | $944 | **$982** | $789 | +193 ± 26 | 22 % | 9.6 |
| 728 | 5 micros mientras saldo < $1,500, luego 1 | $942 | **$1,022** | $789 | +233 ± 28 | 29 % | 10.9 |
