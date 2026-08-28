"""
Glitch — Tests de execution/gist_store.py (27-ago-2026)
==========================================================
Sin red real -- todas las llamadas HTTP a la API de Gists se mockean.
Cubre la filosofia de fallos deliberadamente asimetrica documentada en
el modulo: config ausente = raise inmediato; fallo de red/API en una
corrida bien configurada = log + [] (load) o log silencioso (save),
nunca un crash del scheduler.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

import execution.gist_store as gist_store


class FakeResponse:
    def __init__(self, json_data=None, status_code=200, raise_exc=None):
        self._json_data = json_data or {}
        self.status_code = status_code
        self._raise_exc = raise_exc

    def json(self):
        return self._json_data

    def raise_for_status(self):
        if self._raise_exc:
            raise self._raise_exc
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


@pytest.fixture
def configured(monkeypatch):
    """Simula GITHUB_GIST_TOKEN/GIST_ID presentes, sin tocar el entorno real."""
    monkeypatch.setattr(gist_store, "GITHUB_GIST_TOKEN", "fake-token-not-real")
    monkeypatch.setattr(gist_store, "GIST_ID", "fake-gist-id")


class TestConfigRequired:

    def test_load_log_raises_without_config(self, monkeypatch):
        monkeypatch.setattr(gist_store, "GITHUB_GIST_TOKEN", None)
        monkeypatch.setattr(gist_store, "GIST_ID", None)
        with pytest.raises(RuntimeError, match="GITHUB_GIST_TOKEN"):
            gist_store.load_log("whatever.json")

    def test_save_log_raises_without_config(self, monkeypatch):
        monkeypatch.setattr(gist_store, "GITHUB_GIST_TOKEN", "present")
        monkeypatch.setattr(gist_store, "GIST_ID", None)
        with pytest.raises(RuntimeError, match="GIST_ID"):
            gist_store.save_log("whatever.json", [])


class TestLoadLog:

    def test_returns_parsed_content_when_file_present(self, configured, monkeypatch):
        data = [{"date": "2026-08-27", "result": "TP", "pnl": 100.0}]
        fake_gist = {"files": {"combo2d_log.json": {"content": '[{"date": "2026-08-27", "result": "TP", "pnl": 100.0}]'}}}
        monkeypatch.setattr(gist_store.requests, "get", lambda *a, **k: FakeResponse(fake_gist))
        result = gist_store.load_log("combo2d_log.json")
        assert result == data

    def test_returns_empty_list_when_file_absent_from_gist(self, configured, monkeypatch):
        fake_gist = {"files": {"other_file.json": {"content": "[]"}}}
        monkeypatch.setattr(gist_store.requests, "get", lambda *a, **k: FakeResponse(fake_gist))
        assert gist_store.load_log("combo2d_log.json") == []

    def test_returns_empty_list_when_content_is_empty_string(self, configured, monkeypatch):
        fake_gist = {"files": {"combo2d_log.json": {"content": ""}}}
        monkeypatch.setattr(gist_store.requests, "get", lambda *a, **k: FakeResponse(fake_gist))
        assert gist_store.load_log("combo2d_log.json") == []

    def test_returns_empty_list_on_network_error_not_a_crash(self, configured, monkeypatch):
        def _boom(*a, **k):
            raise ConnectionError("simulated network failure")
        monkeypatch.setattr(gist_store.requests, "get", _boom)
        # No debe lanzar -- mismo criterio que un archivo local ausente.
        assert gist_store.load_log("combo2d_log.json") == []

    def test_returns_empty_list_on_malformed_json_content(self, configured, monkeypatch):
        fake_gist = {"files": {"combo2d_log.json": {"content": "{not valid json"}}}
        monkeypatch.setattr(gist_store.requests, "get", lambda *a, **k: FakeResponse(fake_gist))
        assert gist_store.load_log("combo2d_log.json") == []


class TestSaveLog:

    def test_patches_gist_with_correct_payload(self, configured, monkeypatch):
        captured = {}

        def _fake_patch(url, headers=None, json=None, timeout=None):
            captured["url"] = url
            captured["headers"] = headers
            captured["json"] = json
            return FakeResponse({})

        monkeypatch.setattr(gist_store.requests, "patch", _fake_patch)
        data = [{"date": "2026-08-27", "result": "SL", "pnl": -50.0}]
        gist_store.save_log("geometry_mes_log.json", data)

        assert captured["url"] == f"{gist_store._API}/gists/fake-gist-id"
        assert "geometry_mes_log.json" in captured["json"]["files"]
        assert captured["headers"]["Authorization"] == "Bearer fake-token-not-real"

    def test_does_not_raise_on_network_error(self, configured, monkeypatch):
        def _boom(*a, **k):
            raise ConnectionError("simulated network failure")
        monkeypatch.setattr(gist_store.requests, "patch", _boom)
        # No debe lanzar -- el trade del dia ya se ejecuto y notifico antes
        # de llegar aqui, un fallo de persistencia no debe tumbar el proceso.
        gist_store.save_log("combo2d_log.json", [{"date": "2026-08-27"}])

    def test_does_not_raise_on_http_error_status(self, configured, monkeypatch):
        monkeypatch.setattr(gist_store.requests, "patch",
                             lambda *a, **k: FakeResponse({}, status_code=404))
        gist_store.save_log("combo2d_log.json", [])
