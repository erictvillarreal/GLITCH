"""
Glitch — Tests de execution/env_check.py (01-sep-2026)
==========================================================
Cubre la razon de ser del modulo: reportar TODAS las variables
faltantes de un jalon, no una a la vez via crash-arreglo-siguiente-
crash (ver GLITCH_RESEARCH_LOG.md, 2.5 semanas asi en combo2d).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

import execution.env_check as env_check


class TestRequireEnv:

    def test_returns_silently_when_all_present(self, monkeypatch):
        monkeypatch.setenv("FOO", "x")
        monkeypatch.setenv("BAR", "y")
        env_check.require_env(["FOO", "BAR"], "TEST")  # no debe lanzar ni salir

    def test_alternative_tuple_satisfied_by_either_option(self, monkeypatch):
        monkeypatch.delenv("OPT_A", raising=False)
        monkeypatch.setenv("OPT_B", "present")
        env_check.require_env([("OPT_A", "OPT_B")], "TEST")  # no debe lanzar ni salir

    def test_reports_all_missing_vars_in_one_shot_not_just_the_first(self, monkeypatch):
        """
        La razon de ser del modulo: con 4 variables faltantes, deben
        aparecer las 4 en el SystemExit, no solo la primera que se
        hubiera encontrado en una cadena de imports secuencial.
        """
        monkeypatch.delenv("MISS_1", raising=False)
        monkeypatch.delenv("MISS_2", raising=False)
        monkeypatch.delenv("MISS_3", raising=False)
        monkeypatch.delenv("MISS_4", raising=False)
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "t")
        monkeypatch.setenv("TELEGRAM_CHAT_ID", "c")

        captured = {}
        monkeypatch.setattr(env_check.requests, "post",
                             lambda url, json=None, timeout=None: captured.setdefault("payload", json))

        with pytest.raises(SystemExit):
            env_check.require_env(["MISS_1", "MISS_2", "MISS_3", "MISS_4"], "TEST")

        sent_text = captured["payload"]["text"]
        for name in ["MISS_1", "MISS_2", "MISS_3", "MISS_4"]:
            assert name in sent_text

    def test_alternative_tuple_reported_as_single_combined_line_when_missing(self, monkeypatch):
        monkeypatch.delenv("OPT_A", raising=False)
        monkeypatch.delenv("OPT_B", raising=False)
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "t")
        monkeypatch.setenv("TELEGRAM_CHAT_ID", "c")
        sent = {}
        monkeypatch.setattr(env_check.requests, "post",
                             lambda url, json=None, timeout=None: sent.setdefault("payload", json))

        with pytest.raises(SystemExit):
            env_check.require_env([("OPT_A", "OPT_B")], "TEST")

        assert "OPT_A o OPT_B" in sent["payload"]["text"]

    def test_does_not_crash_if_telegram_creds_also_missing(self, monkeypatch):
        """
        Si TODO falta (incluyendo las credenciales de Telegram), el
        intento de notificar debe degradarse a un print, no sumar un
        segundo traceback no manejado encima del primero.
        """
        monkeypatch.delenv("MISS_1", raising=False)
        monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
        monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)

        with pytest.raises(SystemExit):
            env_check.require_env(["MISS_1"], "TEST")

    def test_does_not_crash_if_telegram_send_itself_fails(self, monkeypatch):
        monkeypatch.delenv("MISS_1", raising=False)
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "t")
        monkeypatch.setenv("TELEGRAM_CHAT_ID", "c")

        def _boom(*a, **k):
            raise ConnectionError("simulated network failure")

        monkeypatch.setattr(env_check.requests, "post", _boom)

        with pytest.raises(SystemExit):
            env_check.require_env(["MISS_1"], "TEST")  # no debe lanzar ConnectionError, solo SystemExit
