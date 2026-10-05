# Reproducciones de la auditoría del 04-oct-2026

`test_repro_defects.py` demuestra, con el código real de `pi_executor` / `brokers/projectx` / `gist_store` y fakes
mínimos (sin red, sin broker, sin Gist), los defectos del reporte `../../AUDIT_2026-10-04.md`.

**Cada test PASA mientras el defecto EXISTE** (afirma el comportamiento defectuoso). Corre contra el commit auditado
(`5dd4573`). Después de aplicar los parches de `audit/2026-10-04`, estos tests dejan de pasar a propósito: ya no son
regresión, son evidencia histórica. Los tests permanentes de cada parche viven en `tests/test_pi_audit_patches.py`.
No se ejecutan con `pytest tests/` (están fuera de `tests/`).

    cd glitch && python -m pytest audit/2026-10-04/test_repro_defects.py -q -p no:cacheprovider
