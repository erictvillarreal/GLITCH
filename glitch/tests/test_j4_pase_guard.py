"""
Glitch — Pruebas del parche J4-c (26-oct-2026): el scheduler MES en modo real deja de enviar señales cuando el intento ya cruzo la meta del Combine
(posible PASE) hasta que el operador lo reconoce. NEEDS HUMAN REVIEW. Sin red.
"""
import os
import sys

os.environ.setdefault("MASSIVE_API_KEY", "test-key-not-real")
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "test-token-not-real")
os.environ.setdefault("TELEGRAM_CHAT_ID", "test-chat-not-real")
os.environ.setdefault("GITHUB_GIST_TOKEN", "test-gist-token-not-real")
os.environ.setdefault("GIST_ID", "test-gist-id-not-real")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import scheduler.geometry_scheduler as gs


def _e(date, result, pnl, intento):
    return {"date": date, "result": result, "pnl": pnl, "intento": intento}


class TestPaseGuardReason:
    def test_empty_log_allows(self):
        assert gs._pase_guard_reason([], "") is None

    def test_below_target_allows(self):
        assert gs._pase_guard_reason([_e("2026-10-26", "TP", 1551.2, 1)], "") is None

    def test_two_tps_cross_the_target_and_block(self):
        log = [_e("2026-10-26", "TP", 1551.2, 1), _e("2026-10-27", "TP", 1551.2, 1)]
        why = gs._pase_guard_reason(log, "")
        assert why and "PASE" in why and "#1" in why and "GLITCH_ACK_PASE_INTENTO=1" in why

    def test_acknowledging_the_intento_releases_the_block(self):
        log = [_e("2026-10-26", "TP", 1551.2, 1), _e("2026-10-27", "TP", 1551.2, 1)]
        assert gs._pase_guard_reason(log, "1") is None

    def test_a_different_ack_does_not_release(self):
        log = [_e("2026-10-26", "TP", 1551.2, 3), _e("2026-10-27", "TP", 1551.2, 3)]
        assert gs._pase_guard_reason(log, "2") is not None

    def test_only_the_latest_intento_counts(self):
        log = [_e("2026-10-01", "TP", 1551.2, 1), _e("2026-10-02", "TP", 1551.2, 1),       # intento 1 ya paso (historico)
               _e("2026-10-20", "TP", 1551.2, 2)]                                           # intento 2 sigue por debajo de la meta
        assert gs._pase_guard_reason(log, "") is None

    def test_entries_without_intento_are_ignored(self):
        assert gs._pase_guard_reason([{"date": "2026-10-26", "pnl": 5000, "result": "TP"}], "") is None

    def test_paper_mode_is_not_affected_by_the_guard_source_check(self):
        src = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scheduler", "geometry_scheduler.py"), encoding="utf-8").read()
        i = src.index("_pase_why = _pase_guard_reason(")
        assert "if not DRY_RUN:" in src[i - 120:i]                                          # la guardia vive SOLO dentro del bloque de modo real
