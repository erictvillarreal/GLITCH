# Parte J (26-oct-2026) — Cerebro 2 (MGC / XFA) listo para vivo

Índice (todo BORRADOR, **NEEDS HUMAN REVIEW**; nada aplicado, nada empujado):

| archivo | contenido |
|---|---|
| `J8_PRIMER_DIA_XFA.md` | **prioridad máxima**: estrategia del primer día XFA (mié 28-oct, FOMC): H0-0 por candidata, tabla de decisión con IC95, efecto FOMC, desconocidos |
| `J1_DIVERGENCIA.md` | `main` vs `cerebro2-dev`, rama candidata de go-live (618 pruebas verdes), `J1_merge_candidate.patch`, `J1_resultado_pruebas.txt`, bundle `golive-candidate.bundle` |
| `J2_RUNBOOK_GOLIVE_MGC.md` | runbook con comandos copiables (Pi / Railway / TopstepX) |
| `J3_GEOMETRIA_XFA.md` | 3×364, 3×728, 4→1, 1 micro la primera semana |
| `J4_PARCHES.md` + `j4-patches/*.patch` | b (flatten por calendario), f (roll del oro en el Pi), a (guardia de colchón, apagada), c (guardia de PASE), d (C3); 683 pruebas verdes; bundle `golive-candidate-j4.bundle` |
| `J5_PARTE_H_PENDIENTE.md` | estado de los pendientes de H + intervalo del «+$206» |
| `J6_PARTE_I_PENDIENTE.md` | **no realizado**: falta la definición de «planes angostos» |
| `J7_VEREDICTO.md` | veredicto honesto |

Scripts (desde `glitch/experimentos/parteJ`, con `GLITCH_MGC_PARQUET=<…mgc_5min_2y_corrected_window.parquet> PYTHONPATH=../..`): `j8_primer_dia_xfa.py [--quick]` → `resultados_J8.md`; `j5_intervalo_206.py [--quick]` → `resultados_J5.md`; `j4a_killswitch_sim.py [--quick]` → `resultados_J4a.md`. Semillas fijas. Necesitan los módulos `xfa/xfa_engine.py`, `xfa/worlds.py`, `xfa/chain.py` y `preservacion/daydata.py` de esta rama.
