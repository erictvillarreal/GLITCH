# J1 — Divergencia `main` vs `cerebro2-dev` y rama única de go-live para Cerebro 2 (MGC / XFA)

Lunes 26-oct-2026 · BORRADOR · **NEEDS HUMAN REVIEW** (CLAUDE.md regla 4: toca el camino de ejecución de capital real; yo propongo el diff, no lo apruebo ni lo mergeo). **No se tocó `origin/main`, el Pi, Railway ni credenciales; nada se empujó.**

Fuentes revisadas: repo `erictvillarreal/GLITCH` clonado en la Mac, `git fetch` del 26-oct (refs `origin/main` = `a387a70`, `origin/cerebro2-dev` = `ab4ceac`, base común `484187c` del 6-sep); salida del Pi pegada por Eric (`git -C ~/glitch log -1 --oneline` → `a387a70 (HEAD -> main, origin/main, origin/HEAD)`); suite de pruebas corrida por mí en un worktree desechable. **No** tengo acceso a Railway, al Gist, a TopstepX ni a Telegram. Estado de cada cifra: MEDIDO (lo corrí / lo leí en el código), DESCONOCIDO (no lo puedo ver desde aquí).

## 1. Resumen (10 líneas)

1. **El Pi corre exactamente `origin/main` (`a387a70`)** — MEDIDO (pegado por Eric). Ya tiene el soporte MGC (PR #2) y `CANDIDATES["MGC"]` = 364/364, nc = 3. **El Pi no necesita cambio de código para Cerebro 2.** (`git status -sb` falló porque se corrió fuera del repo: es `git -C ~/glitch status -sb`; falta ver si hay cambios locales sin commitear.)
2. **`geometry_mgc_scheduler.py` solo existe en `cerebro2-dev`** (con el handoff real al Pi del T4, `3b8a5af`). Eso corre en Railway, no en el Pi. **Qué rama/commit corre hoy el servicio GEOMETRY-MGC: DESCONOCIDO** — Eric debe entregarlo.
3. Las dos ramas tienen **ancestro común (6-sep)**: `main` aportó 47 commits (Pi real, auditoría A1–A7, TP 32 de MES, T4-Pi) y `cerebro2-dev` 50 (scheduler MGC, calendario de cierres anticipados, regla de roll del oro, handoff T4). Diferencia punta a punta: 69 archivos, +8,427 / −8,958 (+8,427 = lo que solo tiene `cerebro2-dev`; −8,958 = lo que solo tiene `main`, sobre todo el Pi y sus pruebas).
4. **Un merge de prueba (`main` + `cerebro2-dev`) tiene 4 conflictos, todos triviales** (comentarios/pruebas duplicadas, el bloque de variantes *strict* del Gist que solo `main` tiene, el log de investigación); resueltos, **la suite da 618 pruebas verdes** (`main` sola: 492; `cerebro2-dev` sola: 265) y **ningún identificador de prueba de `main` ni de `cerebro2-dev` se perdió** (comparado prueba por prueba).
5. **Contra `origin/main`, el merge agrega solo**: el scheduler MGC, `execution/session_calendar.py`, la regla de roll del oro en `execution/contracts.py` (+76 líneas), `core/funded_account.py` (módulo de investigación; no lo importa el Pi), un alias en `geometry_pure.py`, una línea en `Procfile` (`worker-geometry-mgc`), 4 archivos de prueba y documentos. **No cambia `pi_executor.py`, `gist_store.py`, `geometry_scheduler.py` (MES) ni nada del camino MES.**
6. **Propuesta: rama local `golive/cerebro2-mgc-candidate` (`2d45c71`)** = ese merge, sin empujar. Parche de revisión: `J1_merge_candidate.patch` (2,995 líneas); bundle para traerla a otra máquina: `golive-candidate.bundle`.
7. **Riesgo que sí importa y NO lo resuelve este merge:** el Pi **no** conoce los cierres anticipados (flatten fijo 14:30 CT); el calendario solo lo usa el scheduler MGC para decidir si enviar la señal. Afecta 26/27-nov y 24-dic, no el 28-oct (patch J4-b).
8. **Riesgo de ejecución del miércoles 28-oct (BLOQUEANTE a verificar antes):** el Pi elige contrato con `activeContract` de la API o, si falta, el de vencimiento más cercano. Para oro el más cercano es **MGCV6 (oct), que vence esa misma semana (~28-oct)** y perdió liquidez tras su aviso de entrega (30-sep). Correr `pi/ops/check_contracts.py` en el Pi (J2, paso 2). Si la API no trae el campo, hay que parchear (J4-f) o el Pi operaría el contrato equivocado.
9. **Otro riesgo:** el log `geometry_mgc_log.json` del Gist ya contiene historial de paper (150K, nc = 6) y de Practice; el Pi real escribe en el mismo archivo y el scheduler deriva `intento` de él. Archivar antes de operar (J2, paso 6).
10. **DESCONOCIDO / pendiente de Eric:** rama y variables de Railway GEOMETRY-MGC (`DRY_RUN`, `GLITCH_PRODUCT`); valores no secretos del `.env` del Pi MES (`TOPSTEP_ACCOUNT_ID`, `TOPSTEP_ACCOUNT_DENY`, `GLITCH_PI_NC_MAX`, `GLITCH_PI_PHASE3`); si `activeContract` viene en la API; `git status` del Pi; si existe `pi/orderside_verified.json` en el Pi (está en `.gitignore`).

## 2. Qué tiene cada rama que la otra no (base `484187c`)

| | `origin/main` (`a387a70`, 18-oct) | `origin/cerebro2-dev` (`ab4ceac`, 12-oct) |
|---|---|---|
| Commits propios | 47 | 50 |
| **Pi / ejecución** | `pi_executor.py` real (29-sep); servicio systemd + watchdog (`pi/ops/`); auditoría 4-oct A1 (señal una sola vez), A2 (plano antes de cerrar ciclo), A3 (ventana de entrada), A4 (Gist *strict*), A5 (cuenta fijada + lista de denegación), A6 (fill de flatten), A7 (validar señal contra config local); M1 (confirmar fill), M6/M7; P0-10; `GLITCH_PI_NC_MAX`; **T4-Pi: MGC**, segunda instancia (`install_service.sh --instance mgc`), `check_contracts.py` | — (sin Pi real) |
| **Scheduler MES** | modo real (`DRY_RUN=false`) que entra a la misma hora que el paper; **TP 32** (PR #3; "not deployed" según su mensaje); piso MLL *trailing* real (16-sep) | MES sin esos cambios (TP 40) |
| **Scheduler MGC (Cerebro 2)** | **no existe** | `geometry_mgc_scheduler.py` (1,118 líneas): paper por Massive; `DRY_RUN=false` ⇒ escribe `orden_pendiente_mgc.json` y el Pi ejecuta (T4 `3b8a5af`) |
| **Calendario / roll** | — | `session_calendar.py` (cierres 26-nov 11:45, 27-nov 12:00, 24-dic 12:00 CT) y feriado 1-ene-2027; **`ROLL_RULES` del oro** (descarta el contrato a ≤ 2 días hábiles de su aviso de entrega) |
| **Pruebas únicas** | 353 (`test_pi_audit_patches` 140, `test_pi_executor` 64, `test_geometry_parity` 58, `test_pi_ops` 44, `test_t4_pi_mgc` 22, `test_pi_nc_cap` 14, `test_combo2d_parity` 11) | 126 (`test_geometry_mgc_scheduler` 77, `test_funded_account` 20, `test_mgc_handoff` 20, `test_session_calendar` 9) |
| Pruebas comunes | 139 | 139 |
| Investigación | auditoría Pi del 4-oct | ~25 scripts `cerebro2_*`, `wf_slow_*`, sondas de Massive, `core/funded_account.py` (`simulate_xfa_lifetime`) — **ningún módulo de producción los importa** (verificado con `git grep`) |

Archivos que ambas ramas tocaron (los únicos que podían chocar): `GLITCH_RESEARCH_LOG.md`, `core/prop_firm.py`, `execution/contracts.py`, `execution/gist_store.py`, `strategies/geometry_pure.py`, `tests/test_contracts.py`, `tests/test_gist_store.py`.

**Aviso de higiene:** la rama `main` **local** de la carpeta del repo en la Mac (`d8863c2`, "orphaned") tiene una historia **sin ancestro común** con `origin/main`. No partir de ella para ningún parche de producción.

## 3. Resultado del merge de prueba

Worktree desechable, `git merge origin/cerebro2-dev` sobre `origin/main`. Conflictos y resolución:

| archivo | tipo | resolución | por qué |
|---|---|---|---|
| `execution/gist_store.py` | `cerebro2-dev` no tiene el bloque `*_strict` | **conservar `main`** | el Pi usa `load_log_strict`/`save_log_strict` (hallazgo A4); `cerebro2-dev` no los tiene |
| `strategies/geometry_pure.py` | mismo comentario redactado distinto | conservar `main` | es solo texto; el código de `xfa_mgc_config` y los alias es idéntico |
| `tests/test_contracts.py` | add/add, un comentario | conservar `main` | las pruebas son las mismas |
| `GLITCH_RESEARCH_LOG.md` | ambos agregaron secciones | **conservar ambos lados** | documento, no código |

`execution/contracts.py` y `tests/test_gist_store.py` se fusionaron solos (el roll del oro y las pruebas de `load_state`/`save_state` de `cerebro2-dev` conviven con lo de `main`).

| suite | pruebas verdes | ids perdidos respecto de `main` | respecto de `cerebro2-dev` |
|---|---|---|---|
| `origin/main` sola | 492 | — | — |
| `origin/cerebro2-dev` sola | 265 | — | — |
| **candidata (merge)** | **618** (= 492 + 126 únicas de `cerebro2-dev`) | **0** | **0** |

Archivo de salida de las pruebas: `J1_resultado_pruebas.txt`. `git diff origin/main golive/cerebro2-mgc-candidate -- glitch/pi glitch/scheduler/geometry_scheduler.py glitch/scheduler/combo2d_scheduler.py glitch/execution/gist_store.py` → **vacío** (MEDIDO).

## 4. Propuesta

**Rama de go-live única: `golive/cerebro2-mgc-candidate` (`2d45c71`)** = `origin/main` + `origin/cerebro2-dev`. Para revisar: `git diff origin/main golive/cerebro2-mgc-candidate -- Procfile glitch/execution glitch/strategies glitch/core glitch/scheduler glitch/tests` (= `J1_merge_candidate.patch`). Si prefieres un go-live más pequeño, la alternativa mínima es llevar a `main` solo `scheduler/geometry_mgc_scheduler.py`, `execution/session_calendar.py`, `execution/contracts.py`, `core/funded_account.py`, el alias de `geometry_pure.py`, la línea de `Procfile` y las 4 pruebas nuevas, dejando los scripts de investigación en `cerebro2-dev`; las pruebas dicen lo mismo (618).

**Quién necesita qué (para no confundir):**
- **Pi**: ya está en `a387a70`. **No cambiar.** Solo se agrega la segunda instancia (`--instance mgc`) con su `.env`. Si se aprueba el patch J4-b/J4-f (flatten por calendario, roll por regla), entonces sí habría que actualizar el Pi.
- **Railway GEOMETRY-MGC**: debe correr un commit que **tenga** `3b8a5af` (el handoff real). `cerebro2-dev@ab4ceac` lo tiene; la candidata también. Cualquiera sirve; la candidata además trae las pruebas de `main`. **No poner `DRY_RUN=false` en un commit anterior a `3b8a5af`**: ese código no escribe al Pi.
- **Railway GEOMETRY (MES)**: sin cambios por J1. Nota: el TP 32 está en `main` pero "not deployed" según su propio commit; qué TP envía hoy el servicio MES de Railway: DESCONOCIDO. El Pi acepta señales con `tp_ticks` de 1 a 4× lo configurado (A7), así que un TP 40 o 32 no sería rechazado: ejecuta el que traiga la señal.

**Parches J4 (sin aplicar):** se hicieron *sobre* la candidata (necesitan `session_calendar.py` y las reglas de roll). Si se aprueban, la rama para el Pi y Railway sería `golive/cerebro2-mgc-candidate-j4` (candidata + 5 parches, **683 pruebas verdes**); ver `J4_PARCHES.md`. Bundle: `golive-candidate-j4.bundle`.

## 5. Qué no sé y qué lo cierra

| DESCONOCIDO | cómo se cierra |
|---|---|
| Rama/commit y variables del servicio Railway GEOMETRY-MGC | captura del dashboard (Deployments → commit; Variables → solo nombres y valores de `DRY_RUN`, `GLITCH_PRODUCT`) |
| Cambios sin commitear en el Pi | `git -C ~/glitch status -sb` (no `git status` suelto) |
| Si `activeContract` viene en la API para MGC | `check_contracts.py` en el Pi (J2) |
| Si existe `orderside_verified.json` en el Pi | `ls -l ~/glitch/glitch/pi/orderside_verified.json` |
| Cómo arranca Railway (Procfile vs comando de inicio) | dashboard; el commit `d8863c2` de la rama local dice que el *Start Command* está vacío, o sea que depende de `Procfile`/Nixpacks |
