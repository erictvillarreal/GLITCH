# PREREGISTRO_EDGE — brazo de investigación: ¿hay ventaja direccional intradía en futuros? (28-oct-2026)

Se commitea **antes** de calcular nada. Semilla: 20261028. Reglas de la casa: nada a producción; MODELADO/MEDIDO; lo que no tenga potencia se reporta «sin potencia», no «sin efecto».

## 0. Punto de partida (honesto)
- El WR de 47.4 % del `alternate` de MGC tiene IC95 [41, 54] con 215 sesiones decididas: **no es una debilidad medida**, es compatible con 50 % (y con 54 %). «Subir el WR» no es un número que podamos mover con los datos de hoy ni comprobar en semanas.
- Con 2 años (≈ 505 sesiones por producto) una prueba de acierto solo detecta efectos ≥ 6.2 pp (8.8 pp con Holm sobre 26 pruebas); con 5 años (Massive Developer), 3.9 / 5.6 pp; con 16 años (Databento), 2.2 / 3.1 pp (`resultados_K0_mde.md`). Un punto de acierto vale ≈ $1.0k al año por cuenta.
- Las 16 pruebas de la Parte E (solo MGC/MES, 2 años) dieron 0 de 16. Aquí **no se repiten**: son familias distintas con antecedente en la literatura, y se aplican a más productos.

## 1. Hipótesis (3 familias, 17 pruebas; Holm sobre m = 16 (E) + 17 = **33**)
Reloj en CT, barras de 5 min, un trade por día, sin parámetros que afinar. Los precios son el cierre de la barra indicada (p. ej. «precio de las 9:00» = cierre de la barra que empieza 8:55).
- **H-A, momentum intradía** (primera media hora predice la última; antecedente: literatura de «market intraday momentum» en índices, extendida a materias primas, divisas y bonos): señal = signo de (precio 9:00 − apertura 8:30); trade = misma dirección de 14:00 a 14:30. Productos: MES, MNQ, M2K, MGC, MCL, M6E, ZN (7 pruebas).
- **H-B, relleno de brecha** (la brecha de apertura tiende a cerrarse parcialmente durante la mañana): brecha = apertura 8:30 − cierre de las 15:00 del día hábil anterior; se opera **solo** si |brecha| ≥ la mediana de |brecha| del producto en la muestra; trade = hacia el cierre previo desde el precio de las 8:35 hasta el de las 12:00. Mismos 7 productos (7 pruebas).
- **H-C, deriva de cierre** (último tramo alcista en índices): largo de 13:30 a 14:30 CT; MES, MNQ, M2K (3 pruebas; a efectos de potencia cuentan como ≈ 1.3 pruebas independientes por la correlación del índice).
**Estadístico:** (i) exactitud = P(el trade gana en ticks) entre días con movimiento ≠ 0, contra 0.5 (binomial exacta, bilateral); (ii) media de ticks por trade con IC95 por bloques de 5 días. Corrección: Holm sobre las 33 pruebas (las 16 de E cuentan con p = 1 salvo las ya reportadas).
**Criterio de éxito (declarado antes):** una prueba «pasa» solo si p_Holm < 0.05 **y** la exactitud ≥ 52 % **y** su signo se repite en las dos mitades cronológicas de la muestra. Se reporta además el MDE de cada prueba (80 % de potencia) y las que no tengan MDE ≤ 3 pp se marcan **«sin potencia»**.

## 2. Datos
- **Dry-run hoy** (solo para validar el código): los 2 años locales (MES, MNQ, M2K, MGC, MCL, M6E, ZN); todo se etiqueta «sin potencia».
- **Corrida real:** 5–16 años de barras de 5 min con los contratos grandes como proxy de los micros (`k0a`/`k0c` dicen qué plan y qué costo); script de descarga: `fetch_long.py` (misma metodología que `fetch_mes_2y.py`, argumentos de producto y años). Hasta tener datos largos **no se saca ninguna conclusión direccional**.
- Si alguna prueba pasa, **no** va a producción: pasa a un periodo de confirmación fuera de muestra con reglas escritas antes, y a la revisión humana de CLAUDE.md (regla 4).
