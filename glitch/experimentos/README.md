# experimentos/ — rama `experimentos-research` (20-oct-2026)

Encargo: `ENCARGO_20oct2026.md`. Reportes: `REPORTE_H.md` (Parte H, más reciente) · `REPORTE_G.md` · `REPORTE_F.md` · `direccion_e/REPORTE_E.md` · `REPORTE_FINAL.md` (empezar aquí) · `preservacion/REPORTE_A.md` · `direccion/REPORTE_B.md` · `REPORTE_C.md` · `PROPUESTAS.md`.

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
| Parte E (ventaja direccional) | `cd direccion_e` y leer `REPORTE_E.md`; `python fetch_yahoo.py`, `python data_audit.py`; `GLITCH_MGC_PARQUET=<…corrected_window.parquet> python run_e1.py`, `run_e2.py`, `run_e4.py`, `run_e5.py`, `python holm_g2.py`, `python riesgo_e.py`, `python value_wr.py` (§4, ~5 min con `--quick` 2 min), `desglose_valor.py` (equilibrio y desglose por etapa), `exploracion_posterior.py` (post-hoc); pruebas: `python -m pytest -q test_data_audit.py test_signals_5min.py test_killswitch.py` (16) | 1–6 min c/u |
| Parte F (verificación del lunes + continuidad) | leer `REPORTE_F.md`; `parteF/LEEME.md` (parches sin aplicar y pruebas); `direccion_e/`: `python f1_equilibrio_por_etapa.py`, `python f2_datos_limpios.py`, `python f3_slippage.py`, `python desglose_valor.py` (necesitan `GLITCH_MGC_PARQUET`) | 1–5 min c/u |
| Parte G (palancas de economía) | leer `REPORTE_G.md`, `G5_DISENO_SCHEDULER_PI.md`, `direccion_e/PREREGISTRO_G2.md`; `direccion_e/`: `python g1_ejecucion.py`, `python run_g2.py`, `python run_g2_t4.py`, `python g4_escala.py`, `python g3_productos.py`, `python g1b_slippage_estimator.py` (necesitan `GLITCH_MGC_PARQUET`) | 1–6 min c/u |
| Parte H (mapa de probabilidades, equilibrio, palancas) | leer `REPORTE_H.md`; `direccion_e/`: `python h0_mapa.py [--quick]` + `python h0_mapa2.py` + `python h0_ensamblar.py` (mapa; el IC publicado usa --quick = 20 remuestras), `h1_equilibrio.py` (cascada → `cascada_H1.svg`), `h8_ambiguas.py`, `h2_ejecucion.py`, `h3_volatilidad.py --part stats|hour`, `h3_dinero.py`, `h3_holm.py`, `h4_noticias.py`, `h6_geometria.py`, `h5_producto.py`; pre-registros `PREREGISTRO_G2.md`/`PREREGISTRO_H3.md`; inventario de métodos `H7_METODOS.md` (necesitan `GLITCH_MGC_PARQUET`) | 1–50 min c/u (el mapa completo ≈ 50 min) |
| Parches NO DESPLEGAR | `extras/PARCHES_TODOS_NO_DESPLEGAR.diff` = sizing + C2 + C3 apilados en un solo diff (incluye archivos nuevos y pruebas; 529 pruebas pasan). Por separado: `extras/C2_*`, `extras/C3_*`, `extras/C2_C3_combinado.diff`, `preservacion/patch_NO_DESPLEGAR/` (el diff de sizing y el de C2/C3 **no apilan** textualmente: el scheduler cambia en las mismas líneas; usar el TODOS). Aplicar solo tras aprobación de Eric: `git apply --check <diff>` | — |

Semillas fijas (base 20261020). Ningún archivo bajo `glitch/` fuera de `glitch/experimentos/` fue modificado: `git diff origin/main --stat -- glitch/ ':!glitch/experimentos'` está vacío. Suite base del repo: 492 pasan (529 con sizing + C2 + C3 aplicados en un árbol temporal).
