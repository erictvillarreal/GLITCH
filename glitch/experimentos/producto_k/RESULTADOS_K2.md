# RESULTADOS_K2 — Universo de productos (Combine / XFA 50K)

Martes 27-oct-2026 · BORRADOR (K2 se entregaba el jueves; adelantado). Fuentes: páginas de Topstep Help leídas hoy con WebFetch (**extracciones automáticas: confirmar cifras clave en el panel o en la página antes de decidir con dinero**): *When and What Products Can I Trade?* (8284206), *Trading Combine Parameters* (8284197), *What is the Scaling Plan?* (8284223), *Risk Adjustments: High Risk/High Volatility* (13613539), *TopstepX Commissions and Fees* (8284213); barras locales de 5 min (`resultados_K2_datos.md`, MODELADO sobre precios reales). Estados: DOCUMENTADO (lo dice la página), MEDIDO (calculado hoy con datos reales), SUPUESTO, DESCONOCIDO.

## 1. Resumen

1. **Hay 8 productos con datos locales y cap suficiente para operarse** (MES, MNQ, M2K, MGC, MCL, M6E, ZN, ZC) más MBT con solo 213 días y MYM sin datos. Los micros de índice, de oro, de crudo y de euro caben dentro del tope de la Combine 50K (**5 minis / 50 micros**, razón 10:1 en Combine y XFA, no en Live) salvo **MGC y MCL: 30 micros** por «ajuste de riesgo» (DOCUMENTADO; hoy vigente, temporal «mientras la volatilidad siga alta»).
2. **Hay solo tres «trades» distintos entre los 8 productos:** los resultados diarios de un trade de deriva cero (mismo lado, bracket ½ del rango) correlacionan **MES–MNQ 0.85, MES–M2K 0.66, MNQ–M2K 0.58** (un solo trade: el índice) y **MGC, MCL, M6E, ZN y ZC entre sí y con el índice quedan entre −0.15 y +0.19**. Correlación media de los 8: 0.09 ⇒ ≈ 4.8 trades independientes de 8; sin los dos índices redundantes, ≈ 6 de 6. MEDIDO (n = 403 fechas comunes; error estándar ≈ 0.05).
3. **La fricción por comisión es chica en todos los productos con micro** (0.3 % del rango diario en MNQ, 0.6 % MES, 0.7 % MGC, 1.0 % M2K, 1.6 % MCL, 2.6 % M6E, 1.1 % ZN, 2.5 % ZC), así que el costo no decide el ranking: lo decide el tamaño del movimiento en dólares frente al colchón del MLL ($2,000) y el tope de contratos. MEDIDO.
4. **Dato de costos desactualizado en el repo:** MCL cuesta **$1.72** por round-turn en la página de hoy (el repo usa $1.52); CME sube la cuota de MCL de $0.50 a $0.60 por lado desde el 1-oct-2026 y la página no dice si el $1.72 ya la incluye. Un resultado de la búsqueda menciona alzas de cuotas de metales desde el 20-jul-2026 (+$0.05–0.10 por lado): **el $1.92 de MGC podría estar por debajo del real** (≈ +$0.60 por trade con 3 micros). DESCONOCIDO hasta ver un extracto de TopstepX; efecto en dinero: despreciable frente a los $150 del día ganador.

## 2. Qué se puede operar y con qué tope (50K) — DOCUMENTADO

| tema | dato | página |
|---|---|---|
| Horario | sesión 5:00 PM → 3:10 PM CT (viernes cierra 3:10 PM); todo plano a las 3:10 PM CT; los Risk Managers aplanan desde 3:08 PM. **Excepción: agrícolas** (ZC, ZW, ZS, ZM, ZL): 8:30 AM–1:20 PM CT (pausa 7:45–8:30); ganado (LE, HE): hasta 1:05 PM CT | 8284206 |
| Productos permitidos | índices: ES, MES, NQ, MNQ, RTY, M2K, NKD, YM, MYM · metales: GC, MGC, SI, SIL, HG, MHG, PL · energía: CL, QM, MCL, NG, QG, MNG, RB, HO · divisas: 6A, 6B, 6C, 6E, 6J, 6S, E7, M6E, M6A, 6M, 6N, M6B · tasas: ZT, ZF, ZN, TN, ZB, UB · agrícolas: ZC, ZW, ZS, ZM, ZL, HE, LE · cripto: MBT, MET | 8284206 |
| Tope Combine 50K | **5 minis / 50 micros**; 10:1; consistencia: el mejor día debe quedar por debajo del 55 % de la meta; se puede pasar en 2 días | 8284197 |
| Ajustes de riesgo vigentes («temporales») | Combine/Express 50K: **MGC 30, MCL 30** micros; SIL 2, MHG 2; CL, QM, RB, HO, GC **3** minis; **SI, HG, PL: 0 (no permitidos)**. Live Funded: MGC 5, MCL 3. **MES, MNQ, M2K, M6E y ZN no figuran** como restringidos | 13613539 |
| Escalado XFA 50K | ejemplo de la página: **1 mini / 12 micros bajo $1,500 de saldo; 3 minis / 31 micros desde $2,000**; el escalón intermedio solo está en una imagen (el motor usa 18; DESCONOCIDO su valor oficial); los límites de la tabla de riesgo son techos (MGC 30) | 8284223, 13613539 |
| Noticias nivel 1 (CPI, FOMC, NFP, PPI) | Combine 50K: máx. **3 micros** abriendo en la ventana, minis de índice bloqueados; XFA 50K con saldo > $2,000: **0 minis / 3 micros**. Se puede mantener lo ya abierto | 13613539 |
| Comisiones round-turn | MES, MNQ, MYM, M2K **$1.22** · MGC **$1.92** · MCL **$1.72** · M6E, M6B **$1.00** · ZN **$2.62** · ZB $2.76 · ZC $5.28 · ES/NQ/YM/RTY $3.78 · GC $4.32 · CL $4.02 · 6E $4.22 | 8284213 |

## 3. Tamaño del movimiento, fricción y cap (MEDIDO, 9:35 → 14:25 CT; `resultados_K2_datos.md`)

| producto | días | rango mediano ($/contrato) | p10–p90 | comisión / rango | cap Combine (contratos) | rango mediano a ese cap ($) | ¿cabe en el colchón de $2,000? |
|---|---|---|---|---|---|---|---|
| MES | 496 | $209 | $112–433 | 0.58 % | 50 micros | $10,450 | con nc ≤ 50 un movimiento mediano mueve 5× el colchón: **la liquidación por MLL, no el SL, es la barrera** (como en la Combine actual: liquidación a 40 ticks con nc 40) |
| MNQ | 487 | $416 | $226–837 | 0.29 % | 50 micros | $20,800 | ídem; nc ≈ 20–25 equivale al riesgo de MES nc 40 |
| M2K | 496 | $121 | $70–234 | 1.01 % | 50 micros | $6,050 | ídem |
| MGC | 490 | $275 | $115–660 | 0.70 % | **30 micros** | $8,250 | nc 3 (XFA actual) arriesga $825 por rango mediano |
| MCL | 476 | $108 | $61–275 | 1.60 % | **30 micros** | $3,240 | cabe holgado |
| M6E | 508 | $39 | $23–75 | 2.58 % | 50 micros | $1,950 | el cap llega a ≈ un colchón: único producto donde el tope, no el MLL, limita el tamaño |
| ZN | 483 | $234 | $141–450 | 1.12 % | 5 contratos | $1,170 | 5 contratos ≈ medio colchón |
| ZC | 454 | $212 | $125–350 | 2.48 % | 5 contratos, cierra 1:20 PM CT | $1,060 | ventana útil más corta |
| MBT | 213 días | $118 | $55–248 | — (comisión no consultada) | límite en mini-equivalentes (DESCONOCIDO) | — | datos escasos |
| MYM, M6B, ZB/ZF/ZT, 6E… | sin datos locales | — | — | — | — | — | requiere K0 (descarga larga) |

## 4. Qué productos son trades distintos (resultados diarios; 403 fechas comunes)

- **Un solo trade:** MES, MNQ, M2K (ρ 0.58–0.85; rendimientos 0.74–0.94; MYM y RTY/ES/NQ serían el mismo).
- **Trades distintos entre sí y del índice (|ρ| ≤ 0.19):** MGC, MCL, M6E, ZN, ZC. Pares más altos fuera del índice: MGC–ZN 0.19, MGC–M6E 0.18, MGC–MES 0.19; el resto ≤ 0.15 en valor absoluto.
- Los **rendimientos** sí se mueven juntos más que los resultados (p. ej. MGC–M6E 0.58, M6E–ZN 0.51, MCL–ZN −0.46): un bracket simétrico con lado alternado «diluye» esa dependencia, pero la dirección común (el mismo lado en todas las cuentas) deja un residuo (0.1–0.2).
- Para **dos cuentas** (K6-i): índice (MES) + un producto del bloque «distinto» tiene ρ ≤ 0.19; MGC + MCL ρ −0.04; MCL + ZN −0.15. Candidatos de menor riesgo conjunto: **MES + MCL**, **MGC + MCL**, **MCL + M6E**.

## 5. Lo que falta de K2

- Escalón intermedio del escalado XFA 50K (tabla en imagen) y los topes de MNQ/MYM/M2K en XFA (la página solo da el ejemplo): se confirman en el panel de TopstepX (*Risk Settings*) o con Topstep.
- Datos de MYM, M6B, tasas (ZB/ZF/ZT) y MBT/MET con historia suficiente (K0, descarga larga).
- Desgloses de comisión actualizados por producto tras los cambios de CME/COMEX de julio y octubre.
