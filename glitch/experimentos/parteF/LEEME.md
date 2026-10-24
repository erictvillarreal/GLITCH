# parteF/ — entregables de la Parte F (24-oct-2026). NADA de esto está aplicado en `main`, el Pi ni Railway.

| archivo | qué es | cómo se usa |
|---|---|---|
| `test_v1_gist_401.py`, `fake_gist.py` | reproducción del fallo silencioso (V1) | `cd glitch && python -m pytest -q experimentos/parteF/test_v1_gist_401.py` |
| `v1_gist_strict.patch` | parche para `main` (a387a70): lectura/escritura estricta + verificación en modo real | `git apply --check v1_gist_strict.patch` (492 → 498 pruebas) |
| `v1_gist_strict_mgc_cerebro2dev.patch` | el mismo parche para `origin/cerebro2-dev` (scheduler de MGC) | `git apply --check` sobre `cerebro2-dev` (265 → 269) |
| `manual_signal.patch`, `manual_signal/` | plan B: señal manual segura (+ 16 pruebas); solo agrega archivos nuevos | `python -m pi.manual_signal` (dry-run); con v1: 514 pruebas |
| `mgc_loader_contract_filter.patch` | filtra por contrato dominante en `dd_wr/product_sweep.py::load_sessions` | para `research/firm-map-and-labs` @6d4b069 (no está en `main`) |
| `test_v4_restart.py` | reinicio del Pi con posición abierta: retoma el bracket sin duplicar | pytest igual que arriba |
| `env_map.py` | mapa de variables de entorno desde el grafo de imports (AST) | `python experimentos/parteF/env_map.py` |
Orden sugerido si Eric aprueba: `manual_signal.patch` (solo agrega) → `v1_gist_strict.patch`. Los dos de `main` no se pisan (514 pruebas con ambos).
Resultados F1–F3: `../direccion_e/resultados_E_desglose.md`, `resultados_F1_equilibrio.md`, `resultados_F2.md`, `resultados_F3_slippage.md`; pre-registro F4: `../direccion_e/PREREGISTRO_F.md`.
