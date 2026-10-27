# PREREGISTRO_K — K3 (estructura) y K4 (volatilidad como dimensionamiento)

Martes 27-oct-2026 · se commitea **antes** de calcular cualquier resultado de K3 o K4. El apartado K5 (reglas direccionales) se agrega en un commit **aparte, antes de correr K5**, con el MDE de cada prueba declarado. Todo lo no listado aquí es exploratorio y se etiqueta así. Semillas: 20261027 (remuestras), 21 y 11 (bancos de vidas e intentos, como en las Partes H/J).

## 0. Reglas de la casa
- Nada a `main`, Pi, Railway ni credenciales; parches NEEDS HUMAN REVIEW. Cada cifra: MEDIDO / MODELADO / SUPUESTO / DESCONOCIDO.
- **Etiqueta de WR** = deriva estandarizada por sesión calibrada en el bracket nominal simétrico del producto (como H1); se reporta a **47.4 % y 50 %**. Costos: $245, $290 y $640 al año; $49 por intento de Combine; $149 de activación; slippage de entrada = 8 observaciones de MES (media 0.9 tick, **8.ª inferida = 0, NO VERIFICADA**) tratadas como supuesto para todos los productos (en dólares por tick del producto); comisión de la página de Topstep (K2).
- Motor: `xfa_engine` (vidas de XFA con reglas verificadas: MLL $2,000 → $0, 5 días ≥ $150 netos, pago 50 % con tope $2,000, mínimo $125, escalado) y `chain.combine_bank` generalizado a `tick_usd`, comisión, tope de contratos y meta (cambio en `experimentos/`, no toca producción). Combine: meta $3,000, MLL $2,000, consistencia 55 %.
- **Línea base de comparación:** MGC 3×364 en la XFA y MES nc 40 (TP 32, liquidación a 40 ticks, P0) en el Combine, con el mismo conjunto de días y semillas.

## 1. Datos y particiones
- Fuente: la mejor disponible al cierre de K0: **(1)** barras de 5 min de sesión completa desde Databento o Massive (contratos grandes como proxy de los micros cuando el micro no existía, con el mismo número de ticks por unidad de precio y el valor del tick del micro); **(2)** si Eric no autoriza la descarga antes del **jueves 29-oct 12:00 Monterrey**, los 2 años locales (ventana CT 8:30–15:00; 7:00–15:00 en MGC). En el caso (2) **todo resultado de K3–K5 se etiqueta «sin potencia»** y K3 se reporta solo como cribado.
- Contrato continuo por volumen (regla de roll de Topstep); un solo contrato por día; días incompletos descartados con su motivo. Sesiones de 1 trade por día; lado `alternate` (función pura de la fecha) en K3 y K4 — **no hay ventaja direccional que buscar aquí**.
- Particiones: **holdout final = los últimos 6 meses de datos**, no se mira hasta que las finalistas estén declaradas en un commit previo; el resto se parte en bloques de 12 meses con **walk-forward anclado** (entrenar en [inicio, t), evaluar en [t, t+12m)); los parámetros que dependen de datos (rango mediano) se estiman solo con el tramo de entrenamiento.

## 2. K3 — búsqueda estructural (grilla fija)
**Productos:** MES, MNQ, M2K, MGC, MCL, M6E, ZN (y MYM, M6B si K0 trae datos); ZC solo como control de agrícola. Se excluye cualquier producto con < 3 años de historia en la descarga larga o < 500 días locales (MBT, MET).
**Para cada producto, grilla:**
1. **Hora de entrada E** ∈ {apertura líquida del producto + 5 min, +1 h, +2 h}; apertura líquida (CT): índices 8:30, metales 7:20, energía 8:00, divisas 7:00, tasas 7:20 (ZN 7:20). Con datos locales solo caben las E dentro de la ventana disponible.
2. **Flatten F** ∈ {12:00, 14:25 CT}.
3. **Bracket:** R = mediana del rango E→F en el tramo de entrenamiento (ticks); **SL = k·R con k ∈ {0.25, 0.5, 0.75, 1.0, 1.5}** y **TP/SL = ρ ∈ {0.5, 1, 2}**.
4. **Tamaño XFA:** nc_x = ⌊f·$2,000 / (SL en $ por contrato + comisión)⌋ con f ∈ {0.25, 0.5, 0.75}, acotado por [1, tope del escalado XFA / de riesgo]. **Tamaño Combine:** nc_c = ⌊f_c·$2,000 / (…)⌋ con f_c ∈ {0.5, 1.0}, acotado por el tope de la Combine (K2); política P0 (fijo) y P3 (finish-line).
**Total declarado de configuraciones por producto:** 3·2·5·3 = 90 brackets × (3 tamaños XFA + 2×2 tamaños/política Combine) = **630**; **m = 630 × 7 productos = 4,410** pruebas de configuración. Se ejecutan **en dos etapas separables** (la cadena se separa en Combine y XFA porque los bancos de intentos y de vidas son independientes): (A) todas las configuraciones de XFA con un Combine de referencia (MES P0); (B) todas las del Combine con una XFA de referencia (MGC 3×364); luego se combinan las mejores de cada etapa **entre productos** (el producto del Combine y el de la XFA pueden ser distintos).
**Objetivo (primario):** neto anual por cuenta de la cadena, a WR 50 % **y** 47.4 %, con los costos de $245/$290/$640. **Secundarios:** cobrado por XFA, P(≥ 1 pago), P(muerte en 3 días), P(pasar), P(neto > 0 en 12 meses).
**Selección y corrección por multiplicidad:** (i) en cada producto y etapa se elige la configuración con **mayor media de neto en los folds de walk-forward**; (ii) se reporta el **holdout** de esa configuración **una sola vez** y también el del baseline, con IC95 por bloques de 5 días y diferencia **pareada**; (iii) *haircut* de selección = (media de la ganadora en entrenamiento/validación) − (su valor en holdout), reportado siempre; (iv) se reporta el **ranking de estabilidad** (en cuántos folds queda entre el 10 % superior) y la distribución de los netos de las 4,410 configuraciones (para mostrar cuánto de la ganadora es «mejor de m»).
**Criterio de victoria (declarado antes):** una configuración «supera al baseline» solo si, **en el holdout**, la diferencia pareada de neto anual es **≥ +$500** (el umbral de las Partes G/H) y su IC95 excluye 0; «robusta» si además lo cumple a WR 47.4 % y 50 % y con costos $640 y $245. Si ninguna lo cumple, se reporta «ninguna supera al baseline» y se muestra la mejor en holdout con su IC.
**Sin potencia:** con holdout < 250 días, la comparación se etiqueta **«sin potencia para diferencias < $X»** con X = el semiancho del IC pareado.

## 3. K4 — volatilidad como dimensionamiento y selección de producto del día
**Pronóstico (no direccional):** rango de la sesión E→F del día t con HAR sobre {rango de ayer, media de 5 días, media de 20 días} + indicador de dato macro programado (FOMC de `fomc_dates.txt`; CPI/NFP/PPI si el calendario BLS se consigue; si no, solo FOMC) + hora de entrada; estimado solo con datos hasta t − 1 (*expanding*); métrica de pronóstico: R² fuera de muestra.
**Reglas (4, declaradas; sin reparametrizar después de ver resultados):**
- **V1 — tamaño inverso al rango pronosticado:** nc_t = ⌊clip(f·$2,000 / (SL$ · rango_pronosticado/R))⌋, f ∈ {0.5} (un solo f).
- **V2 — recorte de riesgo:** nc_t = 1 los días con rango pronosticado en el decil superior de entrenamiento, nc normal el resto.
- **V3 — producto del día (XFA):** operar el producto, de {MGC, MCL, M6E}, con el mayor cociente rango pronosticado / (comisión + 3 ticks de slippage); un trade por día.
- **V4 — V1 + V3.**
**Diferencia con G2 (que dio −$558/año):** G2 era un **filtro de entrada** (operar solo si el rango pronosticado ≥ la barrera), lo que sube la fracción de sesiones decididas pero **reduce los días FLATTEN que cuentan como días ganadores** y estira el calendario. K4 **no salta días**: ajusta el tamaño (V1, V2) o elige producto (V3, V4). Si K4 también resulta negativo o nulo, se explicará con la misma causa (los días FLATTEN positivos ≥ $150 aportan la mitad de los días ganadores); si resulta positivo, se medirá cuánto viene de menos muertes tempranas y cuánto de pagos mayores.
**Contraste y criterio:** mismo que K3 (diferencia pareada en holdout ≥ +$500, IC95 excluye 0).

## 4. K6 (ya fijado)
Tabla final producto × plan ordenada por **neto anual esperado en holdout** con IC; P(neto > 0 en 12 meses) por simulación de 1,000 años de la cadena; P(≥ 1 pago en los primeros 30 días hábiles); robustez a WR 47.4/50 y a costos $245/$290/$640; (i) para 2 cuentas, la combinación de productos con menor probabilidad de que **ambas** toquen el MLL el mismo día (ρ de resultados de K2 y simulación conjunta con cópula supuesta); (ii) la mejor opción si el WR verdadero fuera 47.4 %; (iii) lo que no se puede saber. Si ninguna opción tiene neto esperado positivo con IC razonable, se dice.

## 5. Qué NO se hace
No se repiten las 16 pruebas de la Parte E ni G2/G3 tal cual; no se barren parámetros después de ver resultados; no se usa el holdout para elegir; no se promueve nada a producción desde este trabajo.
