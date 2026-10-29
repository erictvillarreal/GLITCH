# ESTADO DEL PROYECTO GLITCH — 29-oct-2026

Documento de orientación para quien lea el repo por primera vez (persona o agente). Solo documentación: no cambia código. Regla de oro del repo: cada cifra lleva fuente y estatus **MEDIDO / MODELADO / SUPUESTO / DESCONOCIDO**; lo que no se pueda rastrear a una fuente primaria es **NO VERIFICADO**. Las reglas de gobernanza (nada de LLM en límites de riesgo, todo cambio a lógica de capital con revisión humana, ledgers append-only) viven en el `CLAUDE.md` y en el Protocolo de Gobernanza, que **no** están en este repo.

## 1. Dónde estamos
- **Cerebro 1 (MES, Combine de Topstep 50K): pasada** (según Eric, 28/29-oct-2026). La **XFA (MGC, Cerebro 2) está por pagar**.
- **`main` = `7813dcb`** (PR #4): incluye el scheduler MGC (Cerebro 2), los parches J4/K1 y **tres palancas de tamaño APAGADAS por defecto** (finish-line del Combine, bracket 728 de la XFA, regla 5→1 @ $1,500). Guía de activación: `docs/ACTIVAR_TRES_PALANCAS.md`.
- **Pi** (Raspberry, ejecuta las órdenes reales): actualizado a `7813dcb` el 29-oct según lo reportado por Eric; configurado todavía como MES (`GLITCH_PRODUCT=MES`, tope local 9). **Railway: NO VERIFICADO** (rama de despliegue por servicio y si redesplegó tras el merge).
- Reglas de Topstep confirmadas por Support el 28-oct (pegadas por Eric): cambiar el tamaño según el saldo no está prohibido ni es disparador del RTP; stop mayor que el MLL permitido; consistencia = mejor día ≤ 55 % de la meta original (si se excede, la meta sube); mínimo 2 días; el día se bloquea a las 4:00 PM CT; el MLL se vigila en tiempo real con P&L no realizado. **Sin respuesta:** umbrales numéricos del RTP (no publicados) y si el piso del MLL sube con el pico intradía o con el cierre del día (el motor supone el cierre).

## 2. Cifras clave (todas MODELADO salvo que se indique; motor y semillas en las ramas de investigación)
| cifra | valor | fuente |
|---|---|---|
| Neto anual por cuenta, WR 47.4 %, costos $245: hoy → con las 3 palancas | **$19 → $2,425** (con costos $640: −$376 → $2,030) | `experimentos-research`: `glitch/experimentos/optimo/resultados_OPT_CADENA.md` |
| Cobrado de UNA XFA, WR 47.4 %: hoy 3×364 → regla 5→1 + bracket 728 | **$397 → $621** (40 % reciente: $460 → $772); P(≥ 1 pago) ≈ 25 %, mediana $0 | `optimo/resultados_OPT_XFA_UNA.md` |
| Riesgo de morir pronto con la regla 5→1 + 728 | P(día 1) 20.1 %, P(≤ 3 días) 52.1 % (con 1 micro el día 1: 0 % y 42.4 %) | `optimo/resultados_OPT_XFA_DIA1.md` |
| Techo de P(pasar) el Combine | ≈ 30–33 % (hoy 25.5 %; el «80 % en 4 días» fue un artefacto del simulador legado) | `optimo/resultados_OPT_COMBINE_TECHO.md` |
| WR medido (MGC 3×364, TP/(TP+SL), 488 días) | 47.4 %, IC95 [41, 54] | `parteJ`/Partes E–H |
Lectura honesta: la regla de tamaño se eligió en el 60 % más viejo de los datos; fuera de muestra la ganancia por XFA fue de +$72 a +$257. El slippage usa 8 observaciones de MES (la 8.ª inferida = 0, **NO VERIFICADA**). Los $2,425 son el neto de una **cadena anual** (muchas Combines y XFAs), no lo que paga una XFA.

## 3. Mapa de ramas (ordenado por tema)
**Producción y despliegue**
- `main` — código desplegable. `cerebro2-dev`, `feat/t4-mgc-handoff`, `feat/t4-pi-mgc`, `feat/mes-tp32`, `feat/t3-telegram-monitoring`, `pi/ops-hardening`, `audit/2026-10-04` — historial de lo ya integrado (Pi, MGC, TP 32, monitoreo, auditoría 04-oct).
- `golive/cerebro1-finish-line` — rama de las tres palancas (ya mezclada en `main` por el PR #4).

**Investigación (no desplegar; cada rama termina en un reporte)**
- `experimentos-research` — **la rama más completa y reciente** (Partes A–K, `glitch/experimentos/`): motor de simulación, Combine/XFA, finish-line, optimización (`optimo/`), Labs, producto/costos (`producto_k/`), runbook de Cerebro 2 (`parteJ/J2_RUNBOOK_GOLIVE_MGC.md`), edge (`accion/`).
- `research/firm-map-and-labs` (mapa de 36 firmas, retos de Topstep Labs), `research/structural-levers`, `research/stacking-timing`, `research/scale-what-it-takes`, `research/pass-rate-levers`, `research/bulenox-tailored`, `research/t1-combine-size`, `research/t2-third-account`, `research/g2-consistency-check`, `research/mgc-partial-profit-protection` (pausada, con guía para retomar).
- `dd/statistical-due-diligence-v2`, `dd/withdrawal-policy-optimization` — debida diligencia estadística y política de retiros.
- `candidate-a/paper-scheduler`, `design/pi-execution`, `docs/glitch-report`, `gh-pages` — candidata A en paper, diseño del Pi, libro de documentación y su publicación.
- `archive/local-main-2026-10-29` — historia local previa (Camino B, paquete de despliegue en paper); raíz distinta a `main`.

## 4. Cómo leerlo
```bash
git fetch --all
git log --oneline origin/experimentos-research | head -40          # trabajo reciente de investigación
git show origin/experimentos-research:glitch/experimentos/optimo/REPORTE_OPTIMO.md
git diff origin/main origin/experimentos-research --stat           # qué agrega la investigación
```
Orden sugerido: este archivo → `docs/ACTIVAR_TRES_PALANCAS.md` → `optimo/REPORTE_OPTIMO.md` → `parteJ/J2_RUNBOOK_GOLIVE_MGC.md` → `producto_k/` → `labs/`.

## 5. Pendientes abiertos
1. Pagar la XFA y pasar el Pi a MGC con el ID de la cuenta nueva (primer día con 1 micro). Ensayo previo en la demo de 150K.
2. Verificar en Railway la rama y el despliegue de `worker-geometry-mgc` y pausar `worker-geometry` (MES).
3. Ticket a Topstep: piso del MLL (intradía o cierre), varias cuentas con las mismas señales, cobro de la API por cuenta, reglas de XFA en Labs.
4. Decidir compra de historia larga de datos (potencia estadística) antes de buscar ventaja direccional; el 47.4 % de WR no se puede distinguir de 50 % con ≈ 2 años de datos.
5. Para la próxima Combine de MES: quitar el tope local de 9 contratos del Pi (el modelo supone 40).
6. Orion Funded: evaluado y **descartado** para este sistema (sus T&C prohíben automatización que genere señales, compras múltiples «por suerte» y estrategias que explotan el modelo de evaluación).

## 6. Seguridad
Se escaneó el contenido publicado en busca de tokens/llaves (GitHub, Telegram, AWS, claves privadas): 0 coincidencias. Las credenciales viven fuera del repo (`~/.glitch_pi.env` en el Pi y variables de Railway). No se versionan archivos de datos de mercado (ningún `.parquet`); solo CSV de resultados derivados. Los datos crudos (Massive/Yahoo) se descargan con los scripts de `glitch/experimentos/`.
