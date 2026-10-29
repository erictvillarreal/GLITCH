# XFA ya fondeada — dos brazos: ACTUAR ahora y BUSCAR ventaja (28-oct-2026)

MODELADO, no auditado. Detalle: `resultados_ACCION.md` (MES vs MGC, motor exacto de la XFA), `resultados_ACCION_JOINT.md` (dos trades el mismo día), `resultados_EDGE_dryrun_2y.md` (arnés del brazo de investigación, dry-run), `PREREGISTRO_EDGE.md` (commit 81422a9, antes de calcular). Código: `xfa_accion.py`, `xfa_joint.py`, `accion_lib.py`, `edge_busqueda.py`, `fetch_long.py`; 4 pruebas en `test_joint.py`.

## 1. Brazo ACTUAR (la cuenta que ya tenemos)

**¿MES en la XFA es mejor que Cerebro 2 (MGC 3×364)? No, con la evidencia que hay.** Tramo reciente (≈ 200 días), slippage empírico de 8 obs. (8.ª inferida = 0, NO VERIFICADA), escalado XFA verificado (MES 20/30/50 micros; MGC 12/18/31), comisiones MES $1.22 / MGC $1.92:

| cobrado en los primeros 30 días hábiles [IC95] | WR 47.4 % | WR 50 % | WR 52 % |
|---|---|---|---|
| **MGC 3×364 (Cerebro 2 hoy)** | $445 [411, 500] | **$525** [499, 573] | $600 [550, 656] |
| MES mejor plan del grid (SL 80 / TP 160 / 8 micros) | $328 [245, 489] | $460 [348, 650] | $594 [440, 799] |
| Diferencia MES − MGC | −$117 [−239, +58] | −$66 [−206, +137] | −$6 [−192, +217] |

- Las diferencias **no se distinguen de cero**, y su signo es negativo en el centro. Los tres mejores planes de MES por entrenamiento quedan en $435–$538 a WR 50 %: el orden entre ellos cambia de un tramo a otro (ruido de selección, no una receta).
- MES muere menos rápido en 3 días (24–26 % vs 35 %) pero **cobra lo mismo o menos**: P(1.er pago ≤ 20 días) = 22 % vs 24 %.
- **Dos trades el mismo día (MGC 7:15 + MES 9:35)** empeora: −$17 a −$55 a 30 días (pareado, IC que no incluye 0 a WR 47.4 %); sin vigilar el colchón compartido era mucho peor (−$250). El MLL es uno solo y sin ventaja más varianza no ayuda.
- **Política de cobro:** pedir **todo lo permitido** en cuanto sea elegible es lo mejor (MGC: $525 a 30 días; pedir la mitad $368; pedir el mínimo $49; esperar a $2,000 no cambia). No esperar ni dosificar.
- **Realidad del corto plazo:** ≈ 76–78 % de las XFA mueren sin cobrar nada; solo ≈ 24 % cobran algo en 30 días (mediana al 1.er pago: 7–8 días hábiles). El motor no encontró un plan que cambie eso de forma distinguible: **mantener MGC 3×364 es lo mejor que se puede demostrar hoy.**
- Tamaño: MGC 3 de 12 micros (25 % del tope) y MES 8 de 20 (40 %) no caen en el patrón de «tamaño máximo» que Topstep cita como motivo de RTP.

**Qué hacer ahora (acciones, no hipótesis):** (1) seguir con la producción (MGC 3×364; el día 1 con 1 micro ya pasó o no según el calendario); (2) pedir el pago completo apenas se cumplan los 5 días ≥ $150 y el saldo lo permita; (3) no cambiar de producto ni abrir un segundo trade el mismo día; (4) si me das el estado actual (saldo relativo, piso del MLL, días ganadores y día número de la XFA) recalculo las probabilidades **desde ese estado** y reviso si conviene ajustar el tamaño de los días que faltan.

## 2. Brazo BUSCAR (ventaja direccional, datos de Massive)

- **Punto de partida honesto:** el 47.4 % tiene IC95 [41, 54]: es compatible con 50 %. Con los 2 años actuales una prueba de acierto solo detecta ≥ 6.2 pp (8.8 pp con Holm); con 5 años (Massive Developer, $79/mes por un mes) 3.9 / 5.6 pp; con 16 años (Databento) 2.2 / 3.1 pp. **Buscar +3 pp con los datos de hoy no es posible; con 5 años, apenas.**
- **Qué dejé listo:** preregistro de 3 familias con antecedente (momentum intradía primera→última media hora, relleno de brecha, deriva de cierre; 17 pruebas, Holm sobre 33 con las 16 de la Parte E), arnés `edge_busqueda.py` y el descargador `fetch_long.py` (misma metodología que `fetch_mes_2y.py`, argumentos de producto y años; NO probado contra la API real). **Dry-run en los 2 años locales: 0 de 17 pasan, todas «sin potencia»** (MDE 9–14 pp): sirve para validar el código, no dice nada del mercado (la más «tentadora», H-A MES, 54.3 % con p = 0.07 ≈ el ruido esperado de 17 pruebas).
- **Mi prior (juicio, no medido):** baja probabilidad (≈ 10 % o menos) de que alguna familia sobreviva a Holm con 5 años, y aun así el efecto sería chico; pero el costo es bajo (un mes de plan y una tarde de cómputo). Si se hace, hay que descargar contratos grandes (ES, NQ, YM, RTY, GC, CL, 6E, ZN) como proxy de los micros.

## 3. Lo que necesito de Eric
1. **Estado de la XFA** (saldo relativo, piso del MLL, días ganadores ≥ $150 hasta hoy, número de sesión) → recálculo desde el estado.
2. **¿Autorizas un mes de Massive Developer ($79) o créditos de Databento** para el brazo de búsqueda? (Cualquiera de los dos; correr `k0a`/`k0c` antes decide.) Hasta entonces el brazo de búsqueda no produce conclusiones.
3. Confirmar que el servicio MGC sigue en 3×364 y qué día de la XFA es hoy.
