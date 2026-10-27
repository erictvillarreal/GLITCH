"""
Glitch — Pruebas del parche J4-b (26-oct-2026): flatten por calendario de cierres anticipados en el Pi y en el scheduler MES.
Sin red: FakeClient de tests/test_pi_executor.py y reloj inyectado. NEEDS HUMAN REVIEW (toca el camino de ejecucion de capital real).
"""
import datetime as dt
import os
import sys

os.environ.setdefault("TOPSTEP_USERNAME", "test-user-not-real")
os.environ.setdefault("TOPSTEP_API_KEY", "test-key-not-real")
os.environ.setdefault("TOPSTEP_ACCOUNT_ID", "555")
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "test-token-not-real")
os.environ.setdefault("TELEGRAM_CHAT_ID", "test-chat-not-real")
os.environ.setdefault("GITHUB_GIST_TOKEN", "test-gist-token-not-real")
os.environ.setdefault("GIST_ID", "test-gist-id-not-real")
os.environ.setdefault("GLITCH_PRODUCT", "MES")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

import pi.pi_executor as pe
from tests.test_pi_executor import FakeClient  # noqa: F401


class _StopPolling(Exception):
    pass


def _at(y, m, d, hh, mm):
    return dt.datetime(y, m, d, hh, mm, tzinfo=pe.CT)


class TestFlattenCutoffMinutes:
    def test_normal_day_is_1430(self):
        assert pe._flatten_cutoff_minutes(_at(2026, 10, 28, 9, 0)) == 14 * 60 + 30

    @pytest.mark.parametrize("day,expected", [
        (dt.date(2026, 11, 26), 11 * 60 + 15),     # Topstep: cerrar por 11:45 CT -> flatten 30 min antes
        (dt.date(2026, 11, 27), 11 * 60 + 30),     # cierre 12:00 CT
        (dt.date(2026, 12, 24), 11 * 60 + 30),
    ])
    def test_early_close_days(self, day, expected):
        assert pe._flatten_cutoff_minutes(dt.datetime.combine(day, dt.time(8, 0), tzinfo=pe.CT)) == expected

    def test_explicit_hour_and_minute_win(self):
        assert pe._flatten_cutoff_minutes(_at(2026, 11, 27, 8, 0), 9, 5) == 9 * 60 + 5

    def test_only_one_of_hour_minute_falls_back_to_calendar(self):
        assert pe._flatten_cutoff_minutes(_at(2026, 11, 27, 8, 0), 9, None) == 11 * 60 + 30


class TestPollFlattensAtTheCalendarTime:
    def _poll(self, client, monkeypatch, now):
        monkeypatch.setattr(pe, "ct_now", lambda: now)
        monkeypatch.setattr(pe, "send", lambda m: None)
        return pe.poll_position_until_closed(client, 555, "CON.MES.Z26", 1, 2, 6050.0, 5975.0, poll_interval=0)

    def test_early_close_day_flattens_at_1131(self, monkeypatch):
        client = FakeClient()
        client.open_order_ids = {1, 2}
        out = self._poll(client, monkeypatch, _at(2026, 11, 27, 11, 31))
        assert out["result"] == "FLATTEN"
        assert client.closed_contracts == [(555, "CON.MES.Z26")]

    def test_normal_day_does_NOT_flatten_at_1131(self, monkeypatch):
        client = FakeClient()
        client.open_order_ids = {1, 2}

        def _stop(_):
            raise _StopPolling()
        monkeypatch.setattr(pe.time, "sleep", _stop)
        with pytest.raises(_StopPolling):
            self._poll(client, monkeypatch, _at(2026, 11, 30, 11, 31))
        assert client.closed_contracts == []                      # sigue monitoreando, no cerro nada

    def test_normal_day_still_flattens_at_1431(self, monkeypatch):
        client = FakeClient()
        client.open_order_ids = {1, 2}
        out = self._poll(client, monkeypatch, _at(2026, 11, 30, 14, 31))
        assert out["result"] == "FLATTEN"


class TestMesSchedulerUsesTheCalendar:
    def test_both_flatten_checks_use_the_calendar_function(self):
        src = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scheduler", "geometry_scheduler.py"), encoding="utf-8").read()
        code = [l for l in src.splitlines() if not l.strip().startswith("#")]
        assert sum("flatten_minutes_ct(" in l for l in code) >= 2          # modo real (llegada tarde) y flatten del paper
        assert not any("t >= 14 * 60 + 30" in l for l in code)             # ya no queda la constante en el loop del paper
