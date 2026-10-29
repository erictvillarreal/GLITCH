# resultados_ACCION — XFA 50K ya fondeada: MES vs MGC (Cerebro 2) con el motor exacto, objetivo de corto plazo

**Fuentes y estado.** MODELADO sobre días reales de 5 min (MES 496 días 9:35→14:25 CT; MGC 443 días sin la ventana de oro, 7:15→14:25 CT). Motor `xfa_engine` con las reglas verificadas de la Parte D (`RULEBOOK_XFA.md`): MLL $2,000 trailing que se fija en $0 al llegar a +$2,000 y tras el 1.er pago; día ganador ≥ $150 netos, 5 días; pago = 50 % del saldo (tope $2,000, mínimo $125); desde el 2.º pago hace falta ganancia desde el pago anterior; **escalado XFA 50K: MES 20 / 30 / 50 micros (saldo < $1,500 / < $2,000 / ≥ $2,000); MGC 12 / 18 / 31**. Comisión por contrato round-turn: MES $1.22, MGC $1.92. Plan elegido en el 60 % más viejo, reportado en el 40 % reciente. Etiqueta de WR (deriva calibrada en el bracket nominal ½ rango): 47.4 / 50 / 52 %. Slippage en la selección: 1 tick; en el reporte, la distribución empírica de 8 obs. de MES (8.ª inferida = 0, NO VERIFICADA).

## 1. Tabla principal (tramo reciente; EMP8; IC95 = bloques de 5 días)


### WR 47.4 %

| plan | cobrado a 10 d | a 20 d | **a 30 d** [IC95] | a 60 d | vida entera [IC95] | P(1.er pago ≤ 10 d / 20 d / 30 d) | mediana días al 1.er pago | P(muerte ≤ 3 d) | P(muerte sin cobrar nada) | tamaño / tope |
|---|---|---|---|---|---|---|---|---|---|---|
| MGC 3×364 (Cerebro 2 hoy): MGC SL 364 / TP 364 / 3 micros | $289 | $401 | **$445** [411, 500] | $477 | $483 [446, 549] | 21 / 22 / 22 % | 7 | 36 % | 78 % | 3 de 12 (tope inicial) |
| MGC mejor del grid: MGC SL 273 / TP 546 / 4 micros | $235 | $342 | **$398** [324, 459] | $463 | $507 [379, 652] | 14 / 15 / 15 % | 8 | 53 % | 85 % | 4 de 12 (tope inicial) |
| MES mejor del grid: MES SL 80 / TP 160 / 8 micros | $210 | $295 | **$328** [245, 489] | $353 | $357 [264, 590] | 15 / 17 / 17 % | 8 | 26 % | 83 % | 8 de 20 (tope inicial) |
| MES 2.º: MES SL 100 / TP 200 / 8 micros | $206 | $286 | **$318** [220, 475] | $341 | $345 [235, 581] | 14 / 16 / 16 % | 8 | 39 % | 84 % | 8 de 20 (tope inicial) |
| MES 3.º: MES SL 170 / TP 170 / 8 micros | $243 | $341 | **$383** [322, 409] | $421 | $432 [364, 465] | 16 / 17 / 17 % | 8 | 45 % | 83 % | 8 de 20 (tope inicial) |

### WR 50.0 %

| plan | cobrado a 10 d | a 20 d | **a 30 d** [IC95] | a 60 d | vida entera [IC95] | P(1.er pago ≤ 10 d / 20 d / 30 d) | mediana días al 1.er pago | P(muerte ≤ 3 d) | P(muerte sin cobrar nada) | tamaño / tope |
|---|---|---|---|---|---|---|---|---|---|---|
| MGC 3×364 (Cerebro 2 hoy): MGC SL 364 / TP 364 / 3 micros | $326 | $466 | **$525** [499, 573] | $573 | $585 [545, 656] | 24 / 24 / 24 % | 7 | 35 % | 76 % | 3 de 12 (tope inicial) |
| MGC mejor del grid: MGC SL 273 / TP 546 / 4 micros | $266 | $394 | **$464** [375, 548] | $555 | $647 [467, 860] | 16 / 17 / 17 % | 8 | 51 % | 83 % | 4 de 12 (tope inicial) |
| MES mejor del grid: MES SL 80 / TP 160 / 8 micros | $277 | $402 | **$460** [348, 650] | $516 | $536 [387, 888] | 19 / 22 / 22 % | 8 | 24 % | 78 % | 8 de 20 (tope inicial) |
| MES 2.º: MES SL 100 / TP 200 / 8 micros | $269 | $383 | **$435** [317, 627] | $486 | $506 [353, 898] | 18 / 20 / 20 % | 8 | 36 % | 80 % | 8 de 20 (tope inicial) |
| MES 3.º: MES SL 170 / TP 170 / 8 micros | $316 | $464 | **$538** [473, 557] | $621 | $671 [585, 700] | 20 / 21 / 21 % | 7 | 42 % | 79 % | 8 de 20 (tope inicial) |

### WR 52.0 %

| plan | cobrado a 10 d | a 20 d | **a 30 d** [IC95] | a 60 d | vida entera [IC95] | P(1.er pago ≤ 10 d / 20 d / 30 d) | mediana días al 1.er pago | P(muerte ≤ 3 d) | P(muerte sin cobrar nada) | tamaño / tope |
|---|---|---|---|---|---|---|---|---|---|---|
| MGC 3×364 (Cerebro 2 hoy): MGC SL 364 / TP 364 / 3 micros | $357 | $523 | **$600** [550, 656] | $667 | $693 [616, 775] | 26 / 27 / 27 % | 7 | 34 % | 73 % | 3 de 12 (tope inicial) |
| MGC mejor del grid: MGC SL 273 / TP 546 / 4 micros | $308 | $470 | **$567** [450, 675] | $709 | $935 [615, 1,488] | 18 / 19 / 19 % | 8 | 50 % | 81 % | 4 de 12 (tope inicial) |
| MES mejor del grid: MES SL 80 / TP 160 / 8 micros | $334 | $504 | **$594** [440, 799] | $697 | $770 [522, 1,382] | 23 / 26 / 26 % | 8 | 22 % | 74 % | 8 de 20 (tope inicial) |
| MES 2.º: MES SL 100 / TP 200 / 8 micros | $318 | $471 | **$550** [412, 772] | $640 | $699 [482, 1,400] | 21 / 23 / 23 % | 8 | 34 % | 77 % | 8 de 20 (tope inicial) |
| MES 3.º: MES SL 170 / TP 170 / 8 micros | $376 | $582 | **$698** [620, 713] | $859 | $1,055 [896, 1,130] | 24 / 25 / 25 % | 7 | 39 % | 75 % | 8 de 20 (tope inicial) |

## 2. Diferencia pareada (misma remuestra de días del tramo reciente no es posible entre productos distintos: se comparan intervalos independientes)

- WR 47.4 %: cobrado a 30 días MES − MGC 3×364 = **$-117** (IC95 de la diferencia de medias por remuestras independientes: [-239, +58]).
- WR 50.0 %: cobrado a 30 días MES − MGC 3×364 = **$-66** (IC95 de la diferencia de medias por remuestras independientes: [-206, +137]).
- WR 52.0 %: cobrado a 30 días MES − MGC 3×364 = **$-6** (IC95 de la diferencia de medias por remuestras independientes: [-192, +217]).

## 3. Política de cobro (WR 50 %, tramo reciente): ¿cobrar todo lo permitido o menos?

| plan | política | cobrado a 30 d | vida entera | P(1.er pago ≤ 20 d) | vida (días) |
|---|---|---|---|---|---|
| MGC 3×364 (Cerebro 2 hoy) | max | $525 | $585 | 24 % | 7.5 |
| MGC 3×364 (Cerebro 2 hoy) | mitad | $368 | $501 | 24 % | 9.3 |
| MGC 3×364 (Cerebro 2 hoy) | min | $49 | $79 | 24 % | 17.4 |
| MGC 3×364 (Cerebro 2 hoy) | espera2000 | $525 | $586 | 23 % | 7.6 |
| MES mejor del grid | max | $460 | $536 | 22 % | 8.8 |
| MES mejor del grid | mitad | $318 | $460 | 22 % | 10.5 |
| MES mejor del grid | min | $40 | $66 | 22 % | 18.0 |
| MES mejor del grid | espera2000 | $457 | $534 | 20 % | 8.9 |
