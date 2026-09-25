"""Tests de execution/session_calendar.py -- flatten condicional en dias de cierre anticipado (25-sep-2026)."""
import datetime as dt
from zoneinfo import ZoneInfo

from execution import session_calendar as sc

CT = ZoneInfo("America/Chicago")


def _at(y, m, d, hh, mm):
    return dt.datetime(y, m, d, hh, mm, tzinfo=CT)


class TestFlattenMinutes:
    def test_normal_day_is_1430(self):
        assert sc.flatten_minutes_ct(dt.date(2026, 9, 28)) == 14 * 60 + 30

    def test_day_after_thanksgiving_flattens_30min_before_1200(self):
        assert sc.flatten_minutes_ct(dt.date(2026, 11, 27)) == 11 * 60 + 30

    def test_christmas_eve_flattens_30min_before_1200(self):
        assert sc.flatten_minutes_ct(dt.date(2026, 12, 24)) == 11 * 60 + 30

    def test_thanksgiving_defense_in_depth(self):
        assert sc.flatten_minutes_ct(dt.date(2026, 11, 26)) == 11 * 60 + 15

    def test_early_close_is_always_earlier_than_normal(self):
        for d in sc.EARLY_CLOSE_BY_CT:
            assert sc.flatten_minutes_ct(d) < sc.NORMAL_FLATTEN_MIN

    def test_flatten_is_always_before_official_close_by(self):
        for d, (h, m) in sc.EARLY_CLOSE_BY_CT.items():
            assert sc.flatten_minutes_ct(d) < h * 60 + m


class TestIsFlattenTime:
    def test_normal_day_before_and_at_1430(self):
        assert sc.is_flatten_time(_at(2026, 9, 28, 14, 29)) is False
        assert sc.is_flatten_time(_at(2026, 9, 28, 14, 30)) is True

    def test_early_close_day_flattens_at_1130_not_1430(self):
        assert sc.is_flatten_time(_at(2026, 11, 27, 11, 29)) is False
        assert sc.is_flatten_time(_at(2026, 11, 27, 11, 30)) is True
        assert sc.is_flatten_time(_at(2026, 11, 27, 13, 0)) is True   # con el flatten fijo viejo (14:30) esto seguia siendo False

    def test_christmas_eve(self):
        assert sc.is_flatten_time(_at(2026, 12, 24, 11, 30)) is True
        assert sc.is_flatten_time(_at(2026, 12, 24, 10, 0)) is False
