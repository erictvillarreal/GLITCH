"""
Glitch — Pruebas del parche K1-a (27-oct-2026): Massive Futures es OPCIONAL en modo real (DRY_RUN=false). NEEDS HUMAN REVIEW. Sin red.
Motivo: poder cancelar la suscripcion sin romper el arranque ni impedir la señal del dia; el modo paper y COMBO2D siguen exigiendo la llave.
"""
import datetime as dt
import os
import subprocess
import sys

os.environ.setdefault("MASSIVE_API_KEY", "test-key-not-real")
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "test-token-not-real")
os.environ.setdefault("TELEGRAM_CHAT_ID", "test-chat-not-real")
os.environ.setdefault("GITHUB_GIST_TOKEN", "test-gist-token-not-real")
os.environ.setdefault("GIST_ID", "test-gist-id-not-real")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import pytest

import scheduler.geometry_scheduler as scheduler
import tests.test_geometry_parity as _tgp


def _env(**extra):
    e = {k: v for k, v in os.environ.items() if k not in ("MASSIVE_API_KEY", "POLYGON_API_KEY", "DRY_RUN")}
    e.update(TELEGRAM_BOT_TOKEN="t", TELEGRAM_CHAT_ID="c", GITHUB_GIST_TOKEN="g", GIST_ID="i", GLITCH_PRODUCT="MES")
    e.update(extra)
    return e


def _run(code, **env):
    pre = "import requests\nrequests.post = lambda *a, **k: (_ for _ in ()).throw(RuntimeError('sin red en pruebas'))\n"
    return subprocess.run([sys.executable, "-c", pre + code], cwd=ROOT, env=_env(**env), capture_output=True, text=True, timeout=120)


class TestContractsModule:
    def test_imports_without_a_key(self):
        r = _run("import execution.contracts as c; assert c.have_key() is False")
        assert r.returncode == 0, r.stderr[-400:]

    def test_get_fails_loudly_at_call_time_without_a_key(self, monkeypatch):
        import execution.contracts as c
        monkeypatch.delenv("MASSIVE_API_KEY", raising=False); monkeypatch.delenv("POLYGON_API_KEY", raising=False)
        monkeypatch.setattr(c.requests, "get", lambda *a, **k: (_ for _ in ()).throw(AssertionError("no debe salir a la red sin llave")))
        with pytest.raises(RuntimeError, match="MASSIVE_API_KEY"):
            c._get("/futures/v1/contracts", {})

    def test_header_is_built_per_call_from_the_current_env(self, monkeypatch):
        import execution.contracts as c
        monkeypatch.setenv("MASSIVE_API_KEY", "abc")
        assert c._headers() == {"Authorization": "Bearer abc"}


class TestStartup:
    @pytest.mark.parametrize("mod", ["scheduler.geometry_scheduler", "scheduler.geometry_mgc_scheduler"])
    def test_real_mode_starts_without_massive(self, mod):
        r = _run(f"import {mod}", DRY_RUN="false")
        assert r.returncode == 0, r.stderr[-500:]

    @pytest.mark.parametrize("mod", ["scheduler.geometry_scheduler", "scheduler.geometry_mgc_scheduler"])
    def test_paper_mode_still_requires_massive(self, mod):
        r = _run(f"import {mod}", DRY_RUN="true")
        assert r.returncode == 1 and "MASSIVE_API_KEY" in r.stderr

    def test_default_mode_is_paper_and_requires_massive(self):
        r = _run("import scheduler.geometry_scheduler")
        assert r.returncode == 1 and "MASSIVE_API_KEY" in r.stderr

    def test_combo2d_still_requires_massive(self):
        r = _run("import scheduler.combo2d_scheduler", DRY_RUN="false")
        assert r.returncode == 1 and "MASSIVE_API_KEY" in r.stderr


class TestMesRealModeToleratesContractFailure:
    """Reutiliza el arnes `_patch_common` de TestDryRunFalseDelegatesToPi (se instancia, no se hereda: no repite sus pruebas)."""

    _patch_common = staticmethod(lambda mp, sent, **kw: _tgp.TestDryRunFalseDelegatesToPi()._patch_common(mp, sent, **kw))

    def test_front_month_failure_does_not_block_the_real_signal(self, monkeypatch):
        monkeypatch.setattr(scheduler, "DRY_RUN", False)
        sent = []
        _tgp.TestDryRunFalseDelegatesToPi()._patch_common(monkeypatch, sent)
        monkeypatch.setattr(scheduler, "get_front_month", lambda code, cache: (_ for _ in ()).throw(RuntimeError("Massive 403")))
        monkeypatch.setattr(scheduler, "load_order_signal", lambda: {})
        captured = {}
        monkeypatch.setattr(scheduler, "save_order_signal", lambda d: captured.update(d))
        scheduler.run()
        assert captured.get("product") == "MES"                                  # la señal SE ESCRIBIO pese al fallo de Massive
        assert any("front-month resolution failed" in m for m in sent)           # y el fallo se avisa

    def test_without_key_in_real_mode_contract_resolution_is_skipped_silently(self, monkeypatch):
        monkeypatch.setattr(scheduler, "DRY_RUN", False)
        sent = []
        _tgp.TestDryRunFalseDelegatesToPi()._patch_common(monkeypatch, sent)
        monkeypatch.setattr(scheduler, "have_key", lambda: False)
        monkeypatch.setattr(scheduler, "get_front_month", lambda code, cache: (_ for _ in ()).throw(AssertionError("no debe llamarse sin llave")))
        monkeypatch.setattr(scheduler, "load_order_signal", lambda: {})
        captured = {}
        monkeypatch.setattr(scheduler, "save_order_signal", lambda d: captured.update(d))
        scheduler.run()
        assert captured.get("product") == "MES" and not any("front-month" in m for m in sent)

    def test_paper_mode_still_stops_on_front_month_failure(self, monkeypatch):
        monkeypatch.setattr(scheduler, "DRY_RUN", True)
        sent = []
        monkeypatch.setattr(scheduler, "is_trading_day", lambda: True)
        monkeypatch.setattr(scheduler, "send", lambda m: sent.append(m))
        monkeypatch.setattr(scheduler, "load_log", lambda: [])
        monkeypatch.setattr(scheduler, "load_pending", lambda: {})
        monkeypatch.setattr(scheduler, "get_front_month", lambda code, cache: (_ for _ in ()).throw(RuntimeError("Massive 403")))
        monkeypatch.setattr(scheduler, "ct_now", lambda: dt.datetime(2026, 9, 29, 9, 36, tzinfo=scheduler.CT))
        scheduler.run()
        assert any("front-month resolution failed" in m for m in sent)
