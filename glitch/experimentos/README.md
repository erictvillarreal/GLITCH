# experimentos/ — rama `experimentos-research` (20-oct-2026)

Encargo: `ENCARGO_20oct2026.md`. Reportes: `REPORTE_FINAL.md` (empezar aquí) · `preservacion/REPORTE_A.md` · `direccion/REPORTE_B.md` · `REPORTE_C.md` · `PROPUESTAS.md`.

Todo es reproducible con un comando por parte (Python 3.9, `numpy pandas pyarrow scipy pytest`; los datos `glitch/data_cache/mes_5min_2y.parquet` no están en git — copiarlos al checkout):

| qué | comando (desde la carpeta indicada) | tiempo |
|---|---|---|
| Parte A: tablas principales | `cd preservacion && python run_partA.py` → `resultados_A.md` | ~25 min (N = 50,000) |
| Parte A: mañana, “a $100”, sensibilidades | `python run_partA2.py` → `resultados_A2.md` | ~25 min |
| Parte A: métricas de “miedo literal” | `python extra_stats.py` → `extra_stats.md` | 1 min |
| Parte A: pruebas de regresión (§2.2) | `python -m pytest -q test_regression.py` (18) | 1 min |
| Parte A: exploratorias (acantilado, hora) | `python scan_cliff.py`, `python scan_entry_time.py` | < 1 min c/u |
| Parte B | `cd direccion && python run_partB.py` → `resultados_B.md`; `python lectura_hoy.py` | 5 s |
| C1 (necesita el motor anterior) | `cd economia && python reconciliar.py --engine-root <checkout de research/firm-map-and-labs @6d4b069>/glitch` → `resultados_C1.md`; pruebas: `GLITCH_ENGINE_ROOT=... python -m pytest -q test_lever_engine_ref.py` (6) | ~40 s |
| Parte D (etapa fondeada) | `cd xfa` y leer `REPORTE_D.md`; reglas oficiales: `RULEBOOK_XFA.md`; preguntas: `PREGUNTAS_TOPSTEP.md`; motor: `GLITCH_MGC_PARQUET=<mgc_5min_2y_corrected_window.parquet> python run_partD.py` (+ `run_partD2.py` … `run_partD11.py`, `chain.py`/`run_partD8.py` para la cadena anual, `evidencia_stats.py`); regresión: `python regress_lever.py --engine-root <checkout @6d4b069>/glitch`; pruebas: `python -m pytest -q test_xfa_engine.py` (13) | cada script de 1 a 25 min |
| Parches NO DESPLEGAR | `extras/PARCHES_TODOS_NO_DESPLEGAR.diff` = sizing + C2 + C3 apilados en un solo diff (incluye archivos nuevos y pruebas; 529 pruebas pasan). Por separado: `extras/C2_*`, `extras/C3_*`, `extras/C2_C3_combinado.diff`, `preservacion/patch_NO_DESPLEGAR/` (el diff de sizing y el de C2/C3 **no apilan** textualmente: el scheduler cambia en las mismas líneas; usar el TODOS). Aplicar solo tras aprobación de Eric: `git apply --check <diff>` | — |

Semillas fijas (base 20261020). Ningún archivo bajo `glitch/` fuera de `glitch/experimentos/` fue modificado: `git diff origin/main --stat -- glitch/ ':!glitch/experimentos'` está vacío. Suite base del repo: 492 pasan (529 con sizing + C2 + C3 aplicados en un árbol temporal).
