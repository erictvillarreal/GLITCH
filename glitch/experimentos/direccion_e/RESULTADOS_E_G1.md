# RESULTADOS_E_G1 — auditoría de datos (generado por data_audit.py)

## 1. Series de 5 minutos (hora de Chicago, con DST)

| serie | días | días con >1 contrato | primer bar CT (distribución) | último bar CT | cambios de contrato dominante entre días consecutivos |
|---|---|---|---|---|---|
| MES | 515 | 0 | 8:30 (515) | 15:00 (495), 11:55 (14), 12:10 (5) | 8 |

  - MES: primer bar de la sesión por mes (mín–máx): 1:8:30; 3:8:30; 4:8:30; 7:8:30; 10:8:30; 11:8:30
| MGC | 515 | 225 | 7:00 (493), 7:05 (8), 7:10 (2) | 15:00 (477), 14:55 (13), 13:25 (10) | 14 |

  - MGC: primer bar de la sesión por mes (mín–máx): 1:7:00; 3:7:00; 4:7:00; 7:7:00; 10:7:00; 11:7:00

  El archivo **MGC intercala barras de dos contratos** en los días contados arriba (H1 de la Parte D): toda señal y todo resultado de MGC usa el **contrato dominante del día (mayor volumen)**; las señales nocturnas se descartan cuando el contrato dominante cambia entre sesiones.

## 2. Series diarias largas (Yahoo, precios crudos)

| serie | días | desde | hasta | duplicadas | volumen cero | |ret c/c| > 8 % | |ret a/c| > 8 % | P(c/c > 0) | P(a/c > 0) |
|---|---|---|---|---|---|---|---|---|---|
| GLD | 5514 | 2004-11-18 | 2026-10-20 | 0 | 0 | 3 | 1 | 53.15 % | 50.24 % |
| GC=F | 6560 | 2000-08-30 | 2026-10-20 | 0 | 418 | 3 | 3 | 52.54 % | 44.04 % |
| ^GSPC | 9268 | 1990-01-02 | 2026-10-20 | 0 | 1 | 10 | 7 | 53.64 % | 53.43 % |
| SPY | 8489 | 1993-01-29 | 2026-10-20 | 0 | 0 | 11 | 4 | 53.58 % | 52.28 % |
| ES=F | 6587 | 2000-09-18 | 2026-10-20 | 0 | 11 | 12 | 10 | 53.81 % | 54.11 % |

### 2.1 Sesgo de los rolls en `GC=F` y `ES=F` (splice sin ajustar): comparación con series sin rolls en las mismas fechas

- GC=F vs GLD (5502 días comunes): P(c/c>0) 52.67 % vs 53.14 % (spot); P(a/c>0) de GC=F 46.19 %. Días con |ret_fut − ret_spot| > 0.4 %: 1449 (26.3 % de los días); de ellos 51 % con el futuro por ENCIMA del spot (días de roll con contango).
- ES=F vs SPY (6558 días comunes): P(c/c>0) 53.87 % vs 54.10 % (spot); P(a/c>0) de ES=F 54.09 %. Días con |ret_fut − ret_spot| > 0.3 %: 449 (6.8 % de los días); de ellos 55 % con el futuro por ENCIMA del spot (días de roll con contango).

**Conclusión G1 (datos):** (a) el cierre→cierre de los futuros continuos de Yahoo **no se usa** (los rolls sesgan P(subir) unos décimos a puntos); se usan las series sin rolls (`GLD`, `^GSPC`, `SPY`) y el apertura→cierre de los futuros solo como robustez; (b) las series de 5 min traen DST correcto (primer bar fijo en hora CT todo el año); (c) las señales nocturnas se anulan en los días en que cambia el contrato dominante.