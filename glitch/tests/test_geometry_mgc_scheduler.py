"""
Glitch — Tests para scheduler/geometry_mgc_scheduler.py (09-sep-2026)

Cubre la logica de reinicio de intento de Combine (misma logica que
geometry_scheduler.py, ver tests/test_geometry_parity.py, pero con los
umbrales de la cuenta 150K: profit_target=$9,000, mll_distance=$4,500,
confirmados contra core/prop_firm.py::TOPSTEP_150K, distintos de los
$3,000/$2,000 de G2/50K) y los umbrales de ENTRY_WAIT_MINUTES.
"""
import os

os.environ.setdefault("MASSIVE_API_KEY", "test-key-not-real")
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "test-token-not-real")
os.environ.setdefault("TELEGRAM_CHAT_ID", "test-chat-not-real")
os.environ.setdefault("GITHUB_GIST_TOKEN", "test-gist-token-not-real")
os.environ.setdefault("GIST_ID", "test-gist-id-not-real")

import pytest

import scheduler.geometry_mgc_scheduler as scheduler


class TestAttemptResetThresholds:
    def test_profit_target_matches_topstep_150k(self):
        from core.prop_firm import TOPSTEP_150K
        assert scheduler.PROFIT_TARGET == TOPSTEP_150K.profit_target == 9_000

    def test_mll_threshold_matches_topstep_150k_negated(self):
        from core.prop_firm import TOPSTEP_150K
        assert scheduler.MLL_THRESHOLD == -TOPSTEP_150K.mll_distance == -4_500

    def test_thresholds_distinct_from_g2_50k(self):
        """Confirma explicitamente que NO se reusaron por accidente los
        umbrales de la cuenta 50K de G2 -- ver instruccion del usuario de
        confirmar el tamaño de cuenta real antes de hardcodear."""
        assert scheduler.PROFIT_TARGET != 3_000
        assert scheduler.MLL_THRESHOLD != -2_000


class TestCurrentIntento:
    def test_empty_log_is_attempt_1(self):
        assert scheduler._current_intento([]) == 1

    def test_returns_highest_intento_seen(self):
        log = [
            {"date": "2026-09-01", "result": "TP", "pnl": 4500, "intento": 1},
            {"date": "2026-09-02", "result": "SL", "pnl": -300, "intento": 2},
        ]
        assert scheduler._current_intento(log) == 2

    def test_entries_without_intento_field_default_to_1(self):
        log = [{"date": "2026-09-01", "result": "TP", "pnl": 500}]
        assert scheduler._current_intento(log) == 1


class TestAttemptPnl:
    def test_sums_only_current_attempt(self):
        log = [
            {"date": "2026-09-01", "result": "TP", "pnl": 9000, "intento": 1},
            {"date": "2026-09-02", "result": "SL", "pnl": -600, "intento": 2},
        ]
        assert scheduler._attempt_pnl(log, 1) == 9000
        assert scheduler._attempt_pnl(log, 2) == -600

    def test_empty_attempt_is_zero(self):
        assert scheduler._attempt_pnl([], 1) == 0


class TestAttemptDaysElapsed:
    def test_no_entries_yet_is_zero(self):
        assert scheduler._attempt_days_elapsed([], 2, "2026-09-10") == 0

    def test_counts_from_first_entry_of_that_attempt_only(self):
        log = [
            {"date": "2026-09-01", "result": "SL", "pnl": -4500, "intento": 1},
            {"date": "2026-09-05", "result": "TP", "pnl": 600, "intento": 2},
        ]
        assert scheduler._attempt_days_elapsed(log, 2, "2026-09-08") == 4


class TestCheckAttemptReset:
    """Los 3 casos pedidos explicitamente, contra los umbrales reales de
    la cuenta 150K de este candidato."""

    def test_pase_at_exact_target(self):
        assert scheduler._check_attempt_reset(9000, 9000, -4500) == "PASE"

    def test_pase_when_overshooting_target(self):
        assert scheduler._check_attempt_reset(9800, 9000, -4500) == "PASE"

    def test_quiebre_at_exact_mll(self):
        assert scheduler._check_attempt_reset(-4500, 9000, -4500) == "QUIEBRE"

    def test_quiebre_when_overshooting_floor(self):
        assert scheduler._check_attempt_reset(-5200, 9000, -4500) == "QUIEBRE"

    def test_normal_case_no_event_between_thresholds(self):
        assert scheduler._check_attempt_reset(2000, 9000, -4500) is None
        assert scheduler._check_attempt_reset(-2000, 9000, -4500) is None
        assert scheduler._check_attempt_reset(0, 9000, -4500) is None

    def test_normal_case_just_short_of_either_threshold(self):
        assert scheduler._check_attempt_reset(8999.99, 9000, -4500) is None
        assert scheduler._check_attempt_reset(-4499.99, 9000, -4500) is None

    def test_uses_scheduler_own_constants_correctly(self):
        """Confirma que los umbrales reales del modulo (no numeros de
        prueba) tambien producen el veredicto esperado."""
        assert scheduler._check_attempt_reset(
            scheduler.PROFIT_TARGET, scheduler.PROFIT_TARGET, scheduler.MLL_THRESHOLD
        ) == "PASE"
        assert scheduler._check_attempt_reset(
            scheduler.MLL_THRESHOLD, scheduler.PROFIT_TARGET, scheduler.MLL_THRESHOLD
        ) == "QUIEBRE"


class TestAttemptResetIntegration:
    def test_full_reset_cycle_after_pass(self):
        log = [
            {"date": "2026-09-01", "result": "TP", "pnl": 5000, "intento": 1},
            {"date": "2026-09-02", "result": "TP", "pnl": 4200, "intento": 1},  # acumulado 9200 -> PASE
        ]
        intento = scheduler._current_intento(log)
        attempt_pnl = scheduler._attempt_pnl(log, intento)
        assert attempt_pnl == 9200
        event = scheduler._check_attempt_reset(attempt_pnl, scheduler.PROFIT_TARGET, scheduler.MLL_THRESHOLD)
        assert event == "PASE"

        log.append({"date": "2026-09-03", "result": "SL", "pnl": -300, "intento": 2})
        intento_nuevo = scheduler._current_intento(log)
        assert intento_nuevo == 2
        assert scheduler._attempt_pnl(log, intento_nuevo) == -300
        assert scheduler._attempt_pnl(log, 1) == 9200  # intento 1 no se toca

    def test_full_reset_cycle_after_blow(self):
        log = [
            {"date": "2026-09-01", "result": "SL", "pnl": -2500, "intento": 1},
            {"date": "2026-09-02", "result": "SL", "pnl": -2100, "intento": 1},  # acumulado -4600 -> QUIEBRE
        ]
        attempt_pnl = scheduler._attempt_pnl(log, scheduler._current_intento(log))
        assert attempt_pnl == -4600
        assert scheduler._check_attempt_reset(attempt_pnl, scheduler.PROFIT_TARGET, scheduler.MLL_THRESHOLD) == "QUIEBRE"

    def test_historic_wr_and_cycles_never_reset_across_attempts(self):
        log = [
            {"date": "2026-09-01", "result": "TP", "pnl": 4500, "intento": 1},
            {"date": "2026-09-02", "result": "TP", "pnl": 4600, "intento": 1},  # PASE
            {"date": "2026-09-03", "result": "SL", "pnl": -600, "intento": 2},
        ]
        progress = scheduler._paper_progress(log, "2026-09-03")
        assert progress["n_cycles"] == 3
        assert progress["wr_empirico"] == pytest.approx(2 / 3)


class TestPendingPositionWrappers:
    """09-sep-2026, ver GLITCH_RESEARCH_LOG.md -- hallazgo de la posicion
    SHORT MGCV6 que nunca recibio su CLOSE. Mismo mecanismo que
    geometry_scheduler.py."""

    def test_load_pending_calls_gist_store_with_mgc_pending_filename(self, monkeypatch):
        captured = {}

        def _fake_load_state(filename):
            captured["filename"] = filename
            return {"side": -1}

        monkeypatch.setattr(scheduler, "_gist_load_state", _fake_load_state)
        result = scheduler.load_pending()
        assert captured["filename"] == "geometry_mgc_pending.json"
        assert result == {"side": -1}

    def test_save_pending_calls_gist_store_with_mgc_pending_filename_and_data(self, monkeypatch):
        captured = {}
        monkeypatch.setattr(scheduler, "_gist_save_state",
                             lambda filename, data: captured.update(filename=filename, data=data))
        scheduler.save_pending({"side": -1, "entry": 4415.80})
        assert captured["filename"] == "geometry_mgc_pending.json"
        assert captured["data"] == {"side": -1, "entry": 4415.80}


class TestCurrentIntentoConsidersReconciledEntries:
    """Mismo fix que geometry_scheduler.py -- encontrado al diseñar la
    reconciliacion, aplicado aqui tambien (mismo bug, misma correccion)."""

    def test_reconciled_only_entry_still_advances_current_intento(self):
        log = [
            {"date": "2026-09-01", "result": "TP", "pnl": 4500, "intento": 1},
            {"date": "2026-09-02", "result": "TP", "pnl": 4600, "intento": 1},  # PASE -> intento 2
            {"date": "2026-09-03", "result": "RECONCILED", "pnl": -1000,
             "pnl_estimated": True, "reconciled": True, "intento": 2},
        ]
        assert scheduler._current_intento(log) == 2

    def test_reconciled_entry_alone_never_triggers_reset(self):
        log = [{"date": "2026-09-01", "result": "RECONCILED", "pnl": -8000,
                "pnl_estimated": True, "reconciled": True, "intento": 1}]
        attempt_pnl = scheduler._attempt_pnl(log, scheduler._current_intento(log))
        assert attempt_pnl == 0
        assert scheduler._check_attempt_reset(attempt_pnl, scheduler.PROFIT_TARGET, scheduler.MLL_THRESHOLD) is None


class TestBuildPendingRecord:
    def test_captures_everything_needed_to_reconcile(self):
        record = scheduler._build_pending_record(
            side=-1, direction_str="SHORT", entry_price=4415.80,
            tp_price=4379.40, sl_price=4452.20, ticker="MGCV6",
            today_str="2026-09-09", intento=1, nc=6, sl_ticks=364,
            tp_ticks=364, product_key="MGC_XFA_150K", dry_run=True,
        )
        assert record == {
            "date": "2026-09-09", "side": -1, "direction": "SHORT",
            "entry": 4415.80, "tp_price": 4379.40, "sl_price": 4452.20,
            "ticker": "MGCV6", "nc": 6, "sl_ticks": 364, "tp_ticks": 364,
            "product": "MGC_XFA_150K", "dry_run": True, "intento": 1,
        }


class TestReconcilePendingPosition:
    """
    Reproduce el escenario real reportado: SHORT MGCV6, entry=4415.80,
    TP=4379.40, SL=4452.20.
    """

    def _pending_short(self):
        return {
            "date": "2026-09-09", "side": -1, "direction": "SHORT",
            "entry": 4415.80, "tp_price": 4379.40, "sl_price": 4452.20,
            "ticker": "MGCV6", "nc": 6, "sl_ticks": 364, "tp_ticks": 364,
            "product": "MGC_XFA_150K", "dry_run": True, "intento": 1,
        }

    def _pending_long(self):
        return {
            "date": "2026-09-09", "side": 1, "direction": "LONG",
            "entry": 4415.80, "tp_price": 4452.20, "sl_price": 4379.40,
            "ticker": "MGCV6", "nc": 6, "sl_ticks": 364, "tp_ticks": 364,
            "product": "MGC_XFA_150K", "dry_run": True, "intento": 1,
        }

    def test_result_is_always_reconciled_never_a_normal_outcome(self):
        for price in (4360.0, 4460.0, 4415.0):
            entry = scheduler._reconcile_pending_position(self._pending_short(), price,
                                                            tick_value_usd=1.00, tick_size=0.10)
            assert entry["result"] == "RECONCILED"
            assert entry["reconciled"] is True
            assert entry["pnl_estimated"] is True

    def test_short_price_beyond_tp_estimates_tp_clipped_to_barrier(self):
        pending = self._pending_short()
        entry = scheduler._reconcile_pending_position(pending, 4360.0, tick_value_usd=1.00, tick_size=0.10)
        assert entry["estimated_outcome"] == "TP"
        assert entry["exit"] == pending["tp_price"]  # clipped, no el precio crudo
        expected_pnl = (pending["tp_price"] - pending["entry"]) * -1 * 1.00 / 0.10 * pending["nc"]
        assert entry["pnl"] == pytest.approx(round(expected_pnl, 2))
        assert entry["pnl"] > 0

    def test_short_price_beyond_sl_estimates_sl_clipped_to_barrier(self):
        pending = self._pending_short()
        entry = scheduler._reconcile_pending_position(pending, 4460.0, tick_value_usd=1.00, tick_size=0.10)
        assert entry["estimated_outcome"] == "SL"
        assert entry["exit"] == pending["sl_price"]
        assert entry["pnl"] < 0

    def test_short_price_inconclusive_between_barriers(self):
        pending = self._pending_short()
        entry = scheduler._reconcile_pending_position(pending, 4415.0, tick_value_usd=1.00, tick_size=0.10)
        assert entry["estimated_outcome"] == "INCONCLUSIVE"
        assert entry["exit"] == 4415.0

    def test_long_price_beyond_tp_estimates_tp_clipped_to_barrier(self):
        pending = self._pending_long()
        entry = scheduler._reconcile_pending_position(pending, 4460.0, tick_value_usd=1.00, tick_size=0.10)
        assert entry["estimated_outcome"] == "TP"
        assert entry["exit"] == pending["tp_price"]
        assert entry["pnl"] > 0

    def test_long_price_beyond_sl_estimates_sl_clipped_to_barrier(self):
        pending = self._pending_long()
        entry = scheduler._reconcile_pending_position(pending, 4360.0, tick_value_usd=1.00, tick_size=0.10)
        assert entry["estimated_outcome"] == "SL"
        assert entry["exit"] == pending["sl_price"]
        assert entry["pnl"] < 0

    def test_long_price_inconclusive_between_barriers(self):
        pending = self._pending_long()
        entry = scheduler._reconcile_pending_position(pending, 4415.0, tick_value_usd=1.00, tick_size=0.10)
        assert entry["estimated_outcome"] == "INCONCLUSIVE"
        assert entry["exit"] == 4415.0

    def test_preserves_intento_and_identity_fields(self):
        pending = self._pending_short()
        entry = scheduler._reconcile_pending_position(pending, 4415.0, tick_value_usd=1.00, tick_size=0.10)
        assert entry["intento"] == 1
        assert entry["date"] == "2026-09-09"
        assert entry["product"] == "MGC_XFA_150K"
        assert entry["nc"] == 6


class TestPendingPositionFullCycle:
    """Simula exactamente el escenario reportado: SHORT MGCV6 se abre,
    el proceso 'muere' antes del CLOSE, la siguiente corrida reconcilia,
    y un trade nuevo despues no colisiona."""

    def test_interrupted_short_reconciled_then_new_trade_opens_clean(self):
        paper_log = [{"date": "2026-09-05", "result": "TP", "pnl": 2000, "intento": 1}]

        intento = scheduler._current_intento(paper_log)
        pending = scheduler._build_pending_record(
            side=-1, direction_str="SHORT", entry_price=4415.80,
            tp_price=4379.40, sl_price=4452.20, ticker="MGCV6",
            today_str="2026-09-09", intento=intento, nc=6, sl_ticks=364,
            tp_ticks=364, product_key="MGC_XFA_150K", dry_run=True,
        )
        assert intento == 1

        # La siguiente corrida reconcilia con el precio actual.
        reconciled = scheduler._reconcile_pending_position(pending, 4420.0, tick_value_usd=1.00, tick_size=0.10)
        paper_log.append(reconciled)
        pending = {}  # save_pending({}) -- limpio

        assert not pending
        assert reconciled["result"] == "RECONCILED"
        assert reconciled["estimated_outcome"] == "INCONCLUSIVE"  # 4420 esta entre TP y SL
        assert scheduler._attempt_pnl(paper_log, 1) == 2000  # sin cambio -- la reconciliada no cuenta

        # Trade nuevo, real, mismo intento.
        paper_log.append({"date": "2026-09-10", "result": "TP", "pnl": 2184, "intento": 1})
        assert scheduler._current_intento(paper_log) == 1
        assert scheduler._attempt_pnl(paper_log, 1) == 4184  # 2000 + 2184, la reconciliada sigue sin contar
