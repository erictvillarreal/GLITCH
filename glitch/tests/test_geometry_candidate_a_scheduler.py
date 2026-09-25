"""Tests de scheduler/geometry_candidate_a_scheduler.py (Candidato A, paper, NO desplegado) -- reglas oficiales reales (25-sep-2026)."""
import os
import datetime as dt

os.environ.setdefault("MASSIVE_API_KEY", "test-key-not-real")
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "test-token-not-real")
os.environ.setdefault("TELEGRAM_CHAT_ID", "test-chat-not-real")
os.environ.setdefault("GITHUB_GIST_TOKEN", "test-gist-token-not-real")
os.environ.setdefault("GIST_ID", "test-gist-id-not-real")

import pytest

import scheduler.geometry_candidate_a_scheduler as s


def E(pnl, intento=1, result=None, date="2026-10-01"):
    return {"date": date, "result": result or ("TP" if pnl > 0 else "SL"), "pnl": pnl, "intento": intento}


class TestConfig:
    def test_candidate_a_geometry(self):
        assert (s.CFG.nc, s.CFG.sl_ticks, s.CFG.tp_ticks, s.CFG.direction) == (16, 100, 100, "alternate")
        assert s.CFG.dollar_tp_sl() == (2000.0, 2000.0)          # nominal 1:1, igual al MLL ($2,000)

    def test_namespace_is_separate_from_g2_and_mgc(self):
        assert s.LOG_FILE == "geometry_candidatoa_log.json" and s.PENDING_FILE == "geometry_candidatoa_pending.json"
        assert s.LOG_FILE not in ("geometry_mes_log.json", "geometry_mgc_log.json")

    def test_rules_come_from_topstep_50k_and_official_consistency(self):
        assert s.PROFIT_TARGET == 3000 and s.MLL_DISTANCE == 2000
        assert s.CONSISTENCY_TARGET == 0.55 and s.MIN_TRADING_DAYS == 2

    def test_refuses_to_start_until_entry_wait_is_measured(self, monkeypatch):
        sent = []
        monkeypatch.setattr(s, "send", sent.append)
        assert s.ENTRY_WAIT_MINUTES is None
        with pytest.raises(SystemExit):
            s._fail_if_entry_wait_not_confirmed()
        assert sent and "ENTRY_WAIT_MINUTES" in sent[0]


class TestAttemptStateRealRules:
    def test_two_tps_pass_on_day_2_with_adjusted_target(self):
        log = [E(1980.5), E(1980.5)]
        st = s._attempt_state(log, 1)
        assert st["status"] == "PASE" and st["days"] == 2
        assert st["required_target"] == pytest.approx(1980.5 / 0.55)   # ~$3,601 > $3,000

    def test_single_tp_never_passes_before_day_2(self):
        assert s._attempt_state([E(3500)], 1)["status"] is None       # minimo 2 dias

    def test_consistency_raises_the_target(self):
        st = s._attempt_state([E(2500), E(600)], 1)                   # total 3,100 >= 3,000 pero mejor dia 2,500 -> target 4,545
        assert st["status"] is None and st["required_target"] == pytest.approx(2500 / 0.55)
        assert s._attempt_state([E(2500), E(600), E(1500)], 1)["status"] == "PASE"

    def test_losses_do_not_reset_best_day(self):
        st = s._attempt_state([E(2500), E(-300), E(-300), E(700), E(900)], 1)   # total 3,200, mejor dia sigue 2,500
        assert st["best_day"] == 2500 and st["status"] is None

    def test_full_loss_from_start_is_quiebre(self):
        assert s._attempt_state([E(-2019.5)], 1)["status"] == "QUIEBRE"

    def test_loss_from_peak_is_quiebre_via_trailing_floor(self):
        st = s._attempt_state([E(1980.5), E(-2019.5)], 1)               # piso previo = 1980-2000 = -19.5; run = -39
        assert st["status"] == "QUIEBRE"

    def test_partial_loss_does_not_blow(self):
        assert s._attempt_state([E(-1000)], 1)["status"] is None

    def test_reconciled_entries_never_count(self):
        log = [E(3900, result="RECONCILED"), E(-100)]
        assert s._attempt_state(log, 1)["pnl"] == -100

    def test_current_intento_advances_after_pase_and_quiebre(self):
        assert s._current_intento([E(1980.5), E(1980.5)]) == 2
        assert s._current_intento([E(-2019.5)]) == 2
        assert s._current_intento([E(500)]) == 1
        assert s._current_intento([]) == 1

    def test_intentos_do_not_leak(self):
        log = [E(1980.5), E(1980.5), E(-100, intento=2)]
        assert s._attempt_state(log, 2)["pnl"] == -100 and s._current_intento(log) == 2


class TestLiquidation:
    def test_fresh_attempt_distance_equals_mll_and_matches_the_sl(self):
        d = s._liquidation_distance_usd([], 1)
        assert d == 2000 and s._liquidation_ticks(d, 16, 1.25) == 100   # coincide con el SL de 100 ticks

    def test_distance_shrinks_after_a_loss(self):
        d = s._liquidation_distance_usd([E(-1000)], 1)                   # balance -1000, piso -2000
        assert d == 1000 and s._liquidation_ticks(d, 16, 1.25) == 50     # liquidacion ANTES del SL

    def test_distance_after_a_win_is_still_the_mll_from_peak(self):
        d = s._liquidation_distance_usd([E(1980.5)], 1)                  # piso = 1980.5-2000 = -19.5 -> distancia 2000
        assert d == pytest.approx(2000.0)

    def test_liquidation_binds_when_distance_is_smaller_than_sl(self):
        assert s._liquidation_ticks(600, 16, 1.25) < s.CFG.sl_ticks

    def test_trade_pnl_is_net_of_commission(self):
        assert s._trade_pnl(5000.0, 5025.0, 1, 16) == pytest.approx(2000.0 - 1.22 * 16)   # TP +100 ticks
        assert s._trade_pnl(5000.0, 4975.0, 1, 16) == pytest.approx(-2000.0 - 1.22 * 16)


class TestBarOutcome:
    def test_long_tp(self):
        assert s._bar_outcome(1, 5025.0, 4975.0, 5026.0, 5010.0) == "TP"

    def test_long_adverse(self):
        assert s._bar_outcome(1, 5025.0, 4975.0, 5010.0, 4974.0) == "ADVERSE"

    def test_short_side_mirrors(self):
        assert s._bar_outcome(-1, 4975.0, 5025.0, 4990.0, 4974.0) == "TP"
        assert s._bar_outcome(-1, 4975.0, 5025.0, 5026.0, 4990.0) == "ADVERSE"

    def test_ambiguous_bar_resolves_against_us(self):
        assert s._bar_outcome(1, 5025.0, 4975.0, 5030.0, 4970.0) == "ADVERSE"

    def test_inside_the_range_is_none(self):
        assert s._bar_outcome(1, 5025.0, 4975.0, 5010.0, 4990.0) is None


class TestPendingAndReconcile:
    def test_pending_record_captures_liquidation_price(self):
        rec = s._build_pending_record(1, "LONG", 5000.0, 5025.0, 4975.0, 4980.0, "MESZ6", "2026-10-01", 1, 16, 100, 100, True)
        assert rec["liq_price"] == 4980.0 and rec["product"] == "MES_A"

    def test_reconcile_is_always_reconciled_and_uses_the_nearer_adverse_level(self):
        rec = s._build_pending_record(1, "LONG", 5000.0, 5025.0, 4975.0, 4980.0, "MESZ6", "2026-10-01", 1, 16, 100, 100, True)
        out = s._reconcile_pending_position(rec, 4979.0)
        assert out["result"] == "RECONCILED" and out["estimated_outcome"] == "SL" and out["exit"] == 4980.0

    def test_reconciled_excluded_from_progress(self):
        log = [E(1980.5), E(1980.5), {"date": "2026-10-03", "result": "RECONCILED", "pnl": -5000, "intento": 2}]
        p = s._paper_progress(log, "2026-10-04")
        assert p["passes"] == 1 and p["blows"] == 0 and p["pass_rate"] == 1.0


class TestCalendar:
    def test_trading_day_calendar_matches_the_other_schedulers(self, monkeypatch):
        monkeypatch.setattr(s, "ct_now", lambda: dt.datetime(2026, 11, 27, 8, 0, tzinfo=s.CT))
        assert s.is_trading_day() is True
        monkeypatch.setattr(s, "ct_now", lambda: dt.datetime(2026, 11, 26, 8, 0, tzinfo=s.CT))
        assert s.is_trading_day() is False

    def test_loop_uses_conditional_flatten(self):
        import inspect
        assert "is_flatten_time(now)" in inspect.getsource(s.run)


class TestRunSmoke:
    """Corrida completa de run() con red/tiempo simulados: un dia normal (TP) y un dia con liquidacion MLL vinculante."""

    def _setup(self, monkeypatch, initial_log, bars, ct_times):
        store = {"log": list(initial_log), "pending": {}}
        sent = []
        monkeypatch.setattr(s, "ENTRY_WAIT_MINUTES", 13)
        monkeypatch.setattr(s, "send", sent.append)
        monkeypatch.setattr(s, "load_log", lambda: list(store["log"]))
        monkeypatch.setattr(s, "save_log", lambda l: store.__setitem__("log", list(l)))
        monkeypatch.setattr(s, "load_pending", lambda: dict(store["pending"]))
        monkeypatch.setattr(s, "save_pending", lambda d: store.__setitem__("pending", dict(d)))
        monkeypatch.setattr(s, "get_front_month", lambda *a, **k: "MESZ6")
        monkeypatch.setattr(s, "check_expiry_alerts", lambda *a, **k: None)
        monkeypatch.setattr(s, "is_trading_day", lambda: True)
        monkeypatch.setattr(s.time, "sleep", lambda *_: None)
        it = iter(bars)
        monkeypatch.setattr(s, "fetch_latest_bar", lambda t: next(it))
        times = iter(ct_times)
        last = {"t": ct_times[-1]}
        def fake_now():
            try: last["t"] = next(times)
            except StopIteration: pass
            return last["t"]
        monkeypatch.setattr(s, "ct_now", fake_now)
        return store, sent

    def _t(self, h, m): return dt.datetime.now(s.CT).replace(hour=h, minute=m, second=0, microsecond=0)

    def test_tp_day_appends_a_tagged_net_of_commission_entry(self, monkeypatch):
        bars = [{"open": 5000, "high": 5000.5, "low": 4999.5, "close": 5000.0},      # entrada
                {"open": 5000, "high": 5010, "low": 4995, "close": 5008},             # dentro del rango
                {"open": 5008, "high": 5026, "low": 5005, "close": 5024}]             # toca TP
        store, sent = self._setup(monkeypatch, [], bars, [self._t(8, 50)] * 3 + [self._t(9, 0), self._t(9, 5), self._t(9, 10)])
        monkeypatch.setattr(s, "decide_side", lambda *a, **k: 1)
        s.run()
        e = store["log"][-1]
        assert e["result"] == "TP" and e["intento"] == 1 and e["liquidated_mll"] is False
        assert e["pnl"] == pytest.approx(2000 - 1.22 * 16)
        assert store["pending"] == {}
        assert any("[OPEN]" in m for m in sent) and any("[CLOSE] [TP]" in m for m in sent)

    def test_binding_liquidation_after_a_loss_is_recorded_as_sl_and_quiebre(self, monkeypatch):
        prior = [E(-1000, date="2026-09-30")]                                          # distancia al piso = $1,000 -> 50 ticks
        bars = [{"open": 5000, "high": 5000.5, "low": 4999.5, "close": 5000.0},
                {"open": 5000, "high": 5001, "low": 4987, "close": 4990}]              # baja 13 pts = 52 ticks: liquida antes del SL de 100
        store, sent = self._setup(monkeypatch, prior, bars, [self._t(8, 50)] * 3 + [self._t(9, 0), self._t(9, 5)])
        monkeypatch.setattr(s, "decide_side", lambda *a, **k: 1)
        s.run()
        e = store["log"][-1]
        assert e["result"] == "SL" and e["liquidated_mll"] is True
        assert e["exit"] == pytest.approx(5000 - 50 * 0.25)
        assert any("LIQUIDADO POR MLL" in m for m in sent) and any("QUIEBRE" in m for m in sent)
        assert s._current_intento(store["log"]) == 2
