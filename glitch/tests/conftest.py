"""
Fixtures globales de la suite.

Aislamiento del estado LOCAL del Pi (04-oct-2026, auditoria): pi/pi_executor.py guarda en disco un marcador de
"señal ya ejecutada" (y un spool del historial) bajo $GLITCH_PI_STATE_DIR (default: el HOME del usuario del servicio).
Sin esto, correr la suite escribiria en el HOME real y una corrida dejaria marcadores que romperian la siguiente.
"""
import pytest


@pytest.fixture(autouse=True)
def _isolate_pi_state_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("GLITCH_PI_STATE_DIR", str(tmp_path / "pi_state"))
