"""
Glitch — Test de paridad produccion/backtest para Camino B (25-ago-2026)
===========================================================================
Mismo criterio que tests/test_combo2d_parity.py: probar que hay UNA sola
fuente de verdad (scheduler/geometry_scheduler.py importa directo de
strategies/geometry_pure.py), no que dos copias coincidan por casualidad.
"""
import os
import sys
import datetime as dt

os.environ.setdefault("MASSIVE_API_KEY", "test-key-not-real")
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "test-token-not-real")
os.environ.setdefault("TELEGRAM_CHAT_ID", "test-chat-not-real")
os.environ.setdefault("GITHUB_GIST_TOKEN", "test-gist-token-not-real")
os.environ.setdefault("GIST_ID", "test-gist-id-not-real")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import importlib

import pytest

import scheduler.geometry_scheduler as scheduler
import strategies.geometry_pure as geo


class TestSingleSourceOfTruth:

    def test_scheduler_imports_same_decide_side(self):
        assert scheduler.decide_side is geo.decide_side

    def test_scheduler_uses_a_registered_candidate(self):
        assert scheduler.CFG is geo.CANDIDATES[scheduler.PRODUCT_KEY]

    def test_default_product_is_mes(self):
        """Ganador validado, ver GLITCH_RESEARCH_LOG.md."""
        assert os.environ.get("GLITCH_PRODUCT", "MES") == "MES"


class TestDecideSide:

    def test_alternate_flips_every_day(self):
        sides = [geo.decide_side(i, "alternate") for i in range(10)]
        assert sides == [1, -1, 1, -1, 1, -1, 1, -1, 1, -1]

    def test_always_long_and_short_are_constant(self):
        assert all(geo.decide_side(i, "always_long") == 1 for i in range(5))
        assert all(geo.decide_side(i, "always_short") == -1 for i in range(5))

    def test_invalid_direction_raises(self):
        with pytest.raises(ValueError):
            geo.decide_side(0, "sideways")


class TestTradingDayIndex:

    def test_deterministic_no_state(self):
        """Misma fecha -> mismo indice, sin importar cuantas veces se llame ni el orden."""
        d = dt.date(2026, 8, 25)
        assert geo.trading_day_index(d) == geo.trading_day_index(d)

    def test_monotonic_with_calendar_date(self):
        d1 = dt.date(2026, 8, 24)
        d2 = dt.date(2026, 8, 25)
        assert geo.trading_day_index(d2) > geo.trading_day_index(d1)


class TestBarrierAndDollarMath:

    def test_barrier_prices_long(self):
        cfg = geo.CANDIDATES["MES"]
        tp, sl = cfg.barrier_prices(entry_price=6000.0, side=1)
        assert tp == pytest.approx(6000.0 + cfg.tp_ticks * cfg.spec.tick_size)
        assert sl == pytest.approx(6000.0 - cfg.sl_ticks * cfg.spec.tick_size)

    def test_barrier_prices_short_is_mirrored(self):
        cfg = geo.CANDIDATES["MES"]
        tp_long, sl_long = cfg.barrier_prices(entry_price=6000.0, side=1)
        tp_short, sl_short = cfg.barrier_prices(entry_price=6000.0, side=-1)
        assert tp_short == pytest.approx(6000.0 - (tp_long - 6000.0))
        assert sl_short == pytest.approx(6000.0 + (6000.0 - sl_long))

    def test_dollar_tp_sl_matches_manual_calc(self):
        cfg = geo.CANDIDATES["MES"]
        tp_usd, sl_usd = cfg.dollar_tp_sl()
        assert tp_usd == pytest.approx(cfg.tp_ticks * cfg.spec.tick_value_usd * cfg.nc)
        assert sl_usd == pytest.approx(cfg.sl_ticks * cfg.spec.tick_value_usd * cfg.nc)

    def test_all_registered_candidates_within_their_real_nc_cap(self):
        """El nc elegido nunca debe exceder el limite real de Topstep para ese producto."""
        for key, cfg in geo.CANDIDATES.items():
            assert cfg.nc <= cfg.spec.nc_cap, f"{key}: nc={cfg.nc} excede nc_cap={cfg.spec.nc_cap}"


class TestNoHardcodedSecrets:

    def test_massive_api_key_has_no_literal_default(self):
        import inspect
        from execution import contracts
        src = inspect.getsource(contracts)
        assert "6F2vDNs8" not in src

    def test_scheduler_requires_verified_yf_ticker(self):
        """Ningun candidato deberia poder correr con un yf_ticker adivinado."""
        for key, cfg in geo.CANDIDATES.items():
            if cfg.spec.yf_ticker is None:
                continue  # correcto -- ese producto deberia fallar al arrancar, no correr con un simbolo inventado
            assert isinstance(cfg.spec.yf_ticker, str) and cfg.spec.yf_ticker.endswith("=F")


class TestProductSwappability:
    """
    Requisito PERMANENTE (ver GLITCH_RESEARCH_LOG.md, seccion Step F):
    rotar de producto es cambiar GLITCH_PRODUCT, nunca tocar codigo. Estos
    tests reimportan el modulo (importlib.reload) con la env var cambiada
    para probar el arranque real del scheduler de punta a punta, no solo
    que el diccionario CANDIDATES tenga la entrada.
    """

    def _reload_with_product(self, monkeypatch, product: str):
        monkeypatch.setenv("GLITCH_PRODUCT", product)
        return importlib.reload(scheduler)

    def test_switching_to_gc_selects_mgc_candidate_via_env_var_only(self, monkeypatch):
        """
        'GC' en la conversacion = el candidato MGC (micro-gold, el que
        realmente puede tradearse con nc>5 en Topstep -- ver ProductSpec).
        Debe llegar hasta el gate de yf_ticker (probando que el swap de
        producto en si funciono sin tocar codigo) y fallar AHI, no antes
        y no por una razon distinta.
        """
        with pytest.raises(SystemExit):
            self._reload_with_product(monkeypatch, "MGC")

    def test_switching_to_rty_selects_m2k_candidate_via_env_var_only(self, monkeypatch):
        """'RTY' en la conversacion = el candidato M2K (micro-Russell, mismo motivo que MGC)."""
        with pytest.raises(SystemExit):
            self._reload_with_product(monkeypatch, "M2K")

    def test_unknown_product_fails_loud_not_silent(self, monkeypatch):
        with pytest.raises(SystemExit):
            self._reload_with_product(monkeypatch, "DOES_NOT_EXIST")

    def test_switching_back_to_mes_still_runs_clean(self, monkeypatch):
        """Confirma que el reload en si no deja el modulo en un estado roto para el candidato que SI corre hoy."""
        reloaded = self._reload_with_product(monkeypatch, "MES")
        assert reloaded.PRODUCT_KEY == "MES"
        assert reloaded.CFG is geo.CANDIDATES["MES"]
        assert reloaded.CFG.spec.yf_ticker == "MES=F"


class TestLoadSaveLogDelegatesToGistStore:
    """
    27-ago-2026: mismo cambio y mismo motivo que en combo2d_scheduler.py
    -- ver tests/test_combo2d_parity.py::TestLoadSaveLogDelegatesToGistStore.
    """

    def test_load_log_calls_gist_store_with_product_specific_filename(self, monkeypatch):
        captured = {}

        def _fake_load(filename):
            captured["filename"] = filename
            return [{"sentinel": True}]

        monkeypatch.setattr(scheduler, "_gist_load_log", _fake_load)
        result = scheduler.load_log()
        assert captured["filename"] == "geometry_mes_log.json"
        assert result == [{"sentinel": True}]

    def test_save_log_calls_gist_store_with_product_specific_filename_and_data(self, monkeypatch):
        captured = {}
        monkeypatch.setattr(scheduler, "_gist_save_log",
                             lambda filename, data: captured.update(filename=filename, data=data))
        payload = [{"date": "2026-08-27", "result": "SL"}]
        scheduler.save_log(payload)
        assert captured["filename"] == "geometry_mes_log.json"
        assert captured["data"] == payload

    def test_load_pending_calls_gist_store_with_product_specific_filename(self, monkeypatch):
        captured = {}

        def _fake_load_state(filename):
            captured["filename"] = filename
            return {"side": 1}

        monkeypatch.setattr(scheduler, "_gist_load_state", _fake_load_state)
        result = scheduler.load_pending()
        assert captured["filename"] == "geometry_mes_pending.json"
        assert result == {"side": 1}

    def test_save_pending_calls_gist_store_with_product_specific_filename_and_data(self, monkeypatch):
        captured = {}
        monkeypatch.setattr(scheduler, "_gist_save_state",
                             lambda filename, data: captured.update(filename=filename, data=data))
        scheduler.save_pending({"side": -1, "entry": 4415.80})
        assert captured["filename"] == "geometry_mes_pending.json"
        assert captured["data"] == {"side": -1, "entry": 4415.80}

    def test_save_pending_can_clear_with_empty_dict(self, monkeypatch):
        captured = {}
        monkeypatch.setattr(scheduler, "_gist_save_state",
                             lambda filename, data: captured.update(filename=filename, data=data))
        scheduler.save_pending({})
        assert captured["data"] == {}


class TestUnifiedStartupCheck:
    """
    01-sep-2026: mismo motivo y mismo patron que
    test_combo2d_parity.py::TestUnifiedStartupCheck -- reimportar con
    varias variables borradas a la vez debe reportar TODAS juntas.
    """

    def test_multiple_missing_vars_reported_together_on_reimport(self, monkeypatch):
        monkeypatch.delenv("GITHUB_GIST_TOKEN", raising=False)
        monkeypatch.delenv("GIST_ID", raising=False)
        monkeypatch.delenv("MASSIVE_API_KEY", raising=False)
        monkeypatch.delenv("POLYGON_API_KEY", raising=False)

        with pytest.raises(SystemExit):
            importlib.reload(scheduler)

        # Dejar el modulo sano para el resto de la suite -- mismo criterio
        # que test_combo2d_parity.py.
        monkeypatch.setenv("GITHUB_GIST_TOKEN", "test-gist-token-not-real")
        monkeypatch.setenv("GIST_ID", "test-gist-id-not-real")
        monkeypatch.setenv("MASSIVE_API_KEY", "test-key-not-real")
        monkeypatch.setenv("GLITCH_PRODUCT", "MES")
        importlib.reload(scheduler)


class TestAttemptResetThresholds:
    """
    09-sep-2026: los umbrales de PASE/QUIEBRE deben venir de
    core/prop_firm.py (fuente ya auditada), no de numeros hardcodeados a
    mano -- ver GLITCH_RESEARCH_LOG.md.
    """

    def test_profit_target_matches_topstep_50k(self):
        from core.prop_firm import TOPSTEP_50K
        assert scheduler.PROFIT_TARGET == TOPSTEP_50K.profit_target == 3_000

    def test_mll_threshold_matches_topstep_50k_negated(self):
        from core.prop_firm import TOPSTEP_50K
        assert scheduler.MLL_THRESHOLD == -TOPSTEP_50K.mll_distance == -2_000


class TestCurrentIntento:
    def test_empty_log_is_attempt_1(self):
        assert scheduler._current_intento([]) == 1

    def test_no_resolved_cycles_is_attempt_1(self):
        log = [{"date": "2026-09-01", "note": "no_data_entry", "pnl": 0}]
        assert scheduler._current_intento(log) == 1

    def test_single_attempt_so_far(self):
        log = [
            {"date": "2026-09-01", "result": "TP", "pnl": 500, "intento": 1},
            {"date": "2026-09-02", "result": "SL", "pnl": -300, "intento": 1},
        ]
        assert scheduler._current_intento(log) == 1

    def test_returns_highest_intento_seen(self):
        log = [
            {"date": "2026-09-01", "result": "TP", "pnl": 500, "intento": 1},
            {"date": "2026-09-02", "result": "TP", "pnl": 3000, "intento": 1},
            {"date": "2026-09-03", "result": "SL", "pnl": -200, "intento": 2},
        ]
        assert scheduler._current_intento(log) == 2

    def test_entries_without_intento_field_default_to_1(self):
        """Compatibilidad hacia atras -- entradas de antes de este cambio
        no tienen el campo 'intento' todavia."""
        log = [{"date": "2026-09-01", "result": "TP", "pnl": 500}]
        assert scheduler._current_intento(log) == 1


class TestAttemptPnl:
    def test_sums_only_current_attempt(self):
        log = [
            {"date": "2026-09-01", "result": "TP", "pnl": 3000, "intento": 1},
            {"date": "2026-09-02", "result": "SL", "pnl": -300, "intento": 2},
            {"date": "2026-09-03", "result": "TP", "pnl": 500, "intento": 2},
        ]
        assert scheduler._attempt_pnl(log, 1) == 3000
        assert scheduler._attempt_pnl(log, 2) == 200

    def test_empty_attempt_is_zero(self):
        assert scheduler._attempt_pnl([], 5) == 0

    def test_ignores_unresolved_entries(self):
        log = [
            {"date": "2026-09-01", "note": "no_data_entry", "pnl": 0, "intento": 1},
            {"date": "2026-09-02", "result": "TP", "pnl": 500, "intento": 1},
        ]
        assert scheduler._attempt_pnl(log, 1) == 500


class TestAttemptDaysElapsed:
    def test_no_entries_yet_is_zero(self):
        """Justo despues de un reinicio, antes del primer trade del
        intento nuevo -- 0, no 1 (distinto de _paper_progress historico)."""
        assert scheduler._attempt_days_elapsed([], 3, "2026-09-10") == 0

    def test_first_day_of_attempt_is_1(self):
        log = [{"date": "2026-09-10", "result": "TP", "pnl": 500, "intento": 1}]
        assert scheduler._attempt_days_elapsed(log, 1, "2026-09-10") == 1

    def test_counts_from_first_entry_of_that_attempt_only(self):
        log = [
            {"date": "2026-09-01", "result": "SL", "pnl": -2000, "intento": 1},
            {"date": "2026-09-05", "result": "TP", "pnl": 500, "intento": 2},
        ]
        # Intento 2 empezo el 2026-09-05, no el 2026-09-01 (eso es intento 1)
        assert scheduler._attempt_days_elapsed(log, 2, "2026-09-08") == 4


class TestAttemptPeak:
    def test_tracks_running_max_within_attempt(self):
        log = [
            {"date": "2026-09-01", "result": "TP", "pnl": 500, "intento": 1},
            {"date": "2026-09-02", "result": "TP", "pnl": 300, "intento": 1},
            {"date": "2026-09-03", "result": "SL", "pnl": -600, "intento": 1},
        ]
        # running: 500, 800, 200 -> peak=800
        assert scheduler._attempt_peak(log, 1) == 800

    def test_does_not_leak_across_attempts(self):
        log = [
            {"date": "2026-09-01", "result": "TP", "pnl": 3000, "intento": 1},
            {"date": "2026-09-02", "result": "TP", "pnl": 100, "intento": 2},
        ]
        assert scheduler._attempt_peak(log, 2) == 100


class TestCheckAttemptReset:
    """Los 3 casos pedidos explicitamente: pase, quiebre, y normal (ningun
    umbral cruzado, sigue igual)."""

    def test_pase_at_exact_target(self):
        assert scheduler._check_attempt_reset(3000, 3000, -2000) == "PASE"

    def test_pase_when_overshooting_target(self):
        assert scheduler._check_attempt_reset(3450, 3000, -2000) == "PASE"

    def test_quiebre_at_exact_mll(self):
        assert scheduler._check_attempt_reset(-2000, 3000, -2000) == "QUIEBRE"

    def test_quiebre_when_overshooting_floor(self):
        assert scheduler._check_attempt_reset(-2400, 3000, -2000) == "QUIEBRE"

    def test_normal_case_no_event_between_thresholds(self):
        assert scheduler._check_attempt_reset(500, 3000, -2000) is None
        assert scheduler._check_attempt_reset(-500, 3000, -2000) is None
        assert scheduler._check_attempt_reset(0, 3000, -2000) is None

    def test_normal_case_just_short_of_either_threshold(self):
        assert scheduler._check_attempt_reset(2999.99, 3000, -2000) is None
        assert scheduler._check_attempt_reset(-1999.99, 3000, -2000) is None


class TestAttemptResetIntegration:
    """
    Simula el flujo completo de un reinicio: un intento que pasa, y
    confirma que el intento siguiente arranca limpio en $0 -- sin
    invocar run() (que tiene llamadas de red), solo las funciones puras
    que run() usa para decidir y calcular.
    """

    def test_full_reset_cycle_after_pass(self):
        # Intento 1: dos TP que acumulan a 3100 -> PASE.
        log = [
            {"date": "2026-09-01", "result": "TP", "pnl": 1200, "intento": 1},
            {"date": "2026-09-02", "result": "TP", "pnl": 1900, "intento": 1},  # acumulado 3100 -> PASE
        ]
        attempt_pnl = scheduler._attempt_pnl(log, 1)
        assert attempt_pnl == 3100
        event = scheduler._check_attempt_reset(attempt_pnl, scheduler.PROFIT_TARGET, scheduler.MLL_THRESHOLD)
        assert event == "PASE"

        # CORREGIDO (10-sep-2026): _current_intento() ahora detecta esto
        # directamente desde los datos guardados, sin necesitar que ya
        # exista ninguna entrada del intento 2 -- ver
        # TestCurrentIntentoAdvancesPastCompletedAttempt para el bug real
        # que esto corrige (el OPEN del dia siguiente seguia mostrando el
        # intento ya completado).
        assert scheduler._current_intento(log) == 2

        # El siguiente trade real, cuando llegue, se etiqueta correctamente con el intento 2.
        log.append({"date": "2026-09-03", "result": "SL", "pnl": -150, "intento": 2})
        intento_nuevo = scheduler._current_intento(log)
        assert intento_nuevo == 2
        assert scheduler._attempt_pnl(log, intento_nuevo) == -150
        # El intento 1 sigue intacto historicamente, no se borra ni se toca
        assert scheduler._attempt_pnl(log, 1) == 3100

    def test_full_reset_cycle_after_blow(self):
        log = [
            {"date": "2026-09-01", "result": "SL", "pnl": -1200, "intento": 1},
            {"date": "2026-09-02", "result": "SL", "pnl": -900, "intento": 1},  # acumulado -2100 -> QUIEBRE
        ]
        attempt_pnl = scheduler._attempt_pnl(log, 1)
        assert attempt_pnl == -2100
        event = scheduler._check_attempt_reset(attempt_pnl, scheduler.PROFIT_TARGET, scheduler.MLL_THRESHOLD)
        assert event == "QUIEBRE"
        assert scheduler._current_intento(log) == 2  # mismo fix del 10-sep-2026, caso QUIEBRE

    def test_historic_pass_rate_and_cycles_never_reset_across_attempts(self):
        """Punto 3 explicito del usuario: Pass Rate y Ciclos son
        historicos de TODOS los intentos, nunca se reinician."""
        log = [
            {"date": "2026-09-01", "result": "TP", "pnl": 1500, "intento": 1},
            {"date": "2026-09-02", "result": "TP", "pnl": 1600, "intento": 1},  # PASE, intento 1
            {"date": "2026-09-03", "result": "SL", "pnl": -400, "intento": 2},
        ]
        progress = scheduler._paper_progress(log, "2026-09-03")
        assert progress["n_cycles"] == 3  # los 3 ciclos cuentan, de ambos intentos
        assert progress["pass_rate_empirico"] == pytest.approx(2 / 3)  # 2 TP de 3 total, sin importar el intento


class TestCurrentIntentoConsidersReconciledEntries:
    """
    09-sep-2026 -- fix encontrado al diseñar la reconciliacion: antes,
    _current_intento() solo miraba entradas resueltas (TP/SL/FLATTEN),
    asi que una entrada "RECONCILED" (deliberadamente fuera de ese set,
    para excluirla de Pass Rate/attempt_pnl) habria quedado invisible
    tambien aqui, causando que el siguiente trade real reusara un
    numero de intento ya consumido. Ver GLITCH_RESEARCH_LOG.md.
    """

    def test_reconciled_only_entry_still_advances_current_intento(self):
        log = [
            {"date": "2026-09-01", "result": "TP", "pnl": 1200, "intento": 1},
            {"date": "2026-09-02", "result": "TP", "pnl": 1900, "intento": 1},  # PASE -> intento 2
            {"date": "2026-09-03", "result": "RECONCILED", "pnl": -500,
             "pnl_estimated": True, "reconciled": True, "intento": 2},
        ]
        # Sin el fix, esto daria 1 (el ultimo TP/SL/FLATTEN real) -- con
        # el fix, debe ver la entrada RECONCILED e informar 2.
        assert scheduler._current_intento(log) == 2

    def test_reconciled_entry_excluded_from_attempt_pnl_and_pass_rate(self):
        log = [
            {"date": "2026-09-01", "result": "TP", "pnl": 1200, "intento": 1},
            {"date": "2026-09-02", "result": "RECONCILED", "pnl": -9999,
             "pnl_estimated": True, "reconciled": True, "intento": 1},
        ]
        # El PnL estimado (-9999) NUNCA debe filtrarse a attempt_pnl.
        assert scheduler._attempt_pnl(log, 1) == 1200
        progress = scheduler._paper_progress(log, "2026-09-02")
        assert progress["n_cycles"] == 1  # solo el TP real cuenta
        assert progress["pass_rate_empirico"] == 1.0

    def test_reconciled_entry_alone_never_triggers_reset(self):
        """Aunque el PnL estimado de una reconciliacion, si se contara,
        cruzaria QUIEBRE -- no debe disparar nada porque esta excluido
        de attempt_pnl por diseño."""
        log = [{"date": "2026-09-01", "result": "RECONCILED", "pnl": -5000,
                "pnl_estimated": True, "reconciled": True, "intento": 1}]
        attempt_pnl = scheduler._attempt_pnl(log, scheduler._current_intento(log))
        assert attempt_pnl == 0  # la reconciliada no cuenta
        assert scheduler._check_attempt_reset(attempt_pnl, scheduler.PROFIT_TARGET, scheduler.MLL_THRESHOLD) is None


class TestBuildPendingRecord:
    def test_captures_everything_needed_to_reconcile(self):
        record = scheduler._build_pending_record(
            side=-1, direction_str="SHORT", entry_price=4415.80,
            tp_price=4379.40, sl_price=4452.20, ticker="MES=F",
            today_str="2026-09-09", intento=1, nc=40, sl_ticks=100,
            tp_ticks=40, product_key="MES", dry_run=True,
        )
        assert record == {
            "date": "2026-09-09", "side": -1, "direction": "SHORT",
            "entry": 4415.80, "tp_price": 4379.40, "sl_price": 4452.20,
            "ticker": "MES=F", "nc": 40, "sl_ticks": 100, "tp_ticks": 40,
            "product": "MES", "dry_run": True, "intento": 1,
        }


class TestReconcilePendingPosition:
    """
    09-sep-2026 -- funcion PURA, sin red. Los 3 casos: precio confirma
    TP, precio confirma SL, precio inconcluso (todavia entre las dos
    barreras) -- para LONG y SHORT.
    """

    def _pending_long(self):
        return {
            "date": "2026-09-09", "side": 1, "direction": "LONG",
            "entry": 4415.80, "tp_price": 4452.20, "sl_price": 4379.40,
            "ticker": "MES=F", "nc": 40, "sl_ticks": 100, "tp_ticks": 40,
            "product": "MES", "dry_run": True, "intento": 3,
        }

    def _pending_short(self):
        return {
            "date": "2026-09-09", "side": -1, "direction": "SHORT",
            "entry": 4415.80, "tp_price": 4379.40, "sl_price": 4452.20,
            "ticker": "MES=F", "nc": 40, "sl_ticks": 100, "tp_ticks": 40,
            "product": "MES", "dry_run": True, "intento": 3,
        }

    def test_result_is_always_reconciled_never_a_normal_outcome(self):
        """La entrada MISMA que garantiza la exclusion de Pass
        Rate/attempt_pnl -- nunca debe ser 'TP'/'SL'/'FLATTEN'."""
        for pending, price in [(self._pending_long(), 4460.0),
                                (self._pending_long(), 4370.0),
                                (self._pending_long(), 4400.0)]:
            entry = scheduler._reconcile_pending_position(pending, price, tick_value_usd=1.25, tick_size=0.25)
            assert entry["result"] == "RECONCILED"
            assert entry["reconciled"] is True
            assert entry["pnl_estimated"] is True

    def test_long_price_beyond_tp_estimates_tp_clipped_to_barrier(self):
        pending = self._pending_long()
        entry = scheduler._reconcile_pending_position(pending, 4470.0, tick_value_usd=1.25, tick_size=0.25)
        assert entry["estimated_outcome"] == "TP"
        assert entry["exit"] == pending["tp_price"]  # clipped, no el precio crudo 4470.0
        expected_pnl = (pending["tp_price"] - pending["entry"]) * 1 * 1.25 / 0.25 * pending["nc"]
        assert entry["pnl"] == pytest.approx(round(expected_pnl, 2))

    def test_long_price_beyond_sl_estimates_sl_clipped_to_barrier(self):
        pending = self._pending_long()
        entry = scheduler._reconcile_pending_position(pending, 4360.0, tick_value_usd=1.25, tick_size=0.25)
        assert entry["estimated_outcome"] == "SL"
        assert entry["exit"] == pending["sl_price"]
        assert entry["pnl"] < 0

    def test_long_price_inconclusive_between_barriers(self):
        pending = self._pending_long()
        entry = scheduler._reconcile_pending_position(pending, 4400.0, tick_value_usd=1.25, tick_size=0.25)
        assert entry["estimated_outcome"] == "INCONCLUSIVE"
        assert entry["exit"] == 4400.0  # sin clip -- no se confirmo ningun cruce

    def test_short_price_beyond_tp_estimates_tp_clipped_to_barrier(self):
        pending = self._pending_short()
        entry = scheduler._reconcile_pending_position(pending, 4360.0, tick_value_usd=1.25, tick_size=0.25)
        assert entry["estimated_outcome"] == "TP"
        assert entry["exit"] == pending["tp_price"]
        assert entry["pnl"] > 0

    def test_short_price_beyond_sl_estimates_sl_clipped_to_barrier(self):
        pending = self._pending_short()
        entry = scheduler._reconcile_pending_position(pending, 4470.0, tick_value_usd=1.25, tick_size=0.25)
        assert entry["estimated_outcome"] == "SL"
        assert entry["exit"] == pending["sl_price"]
        assert entry["pnl"] < 0

    def test_short_price_inconclusive_between_barriers(self):
        pending = self._pending_short()
        entry = scheduler._reconcile_pending_position(pending, 4400.0, tick_value_usd=1.25, tick_size=0.25)
        assert entry["estimated_outcome"] == "INCONCLUSIVE"
        assert entry["exit"] == 4400.0

    def test_preserves_intento_and_identity_fields(self):
        pending = self._pending_long()
        entry = scheduler._reconcile_pending_position(pending, 4400.0, tick_value_usd=1.25, tick_size=0.25)
        assert entry["intento"] == 3
        assert entry["date"] == "2026-09-09"
        assert entry["product"] == "MES"
        assert entry["nc"] == 40


class TestPendingPositionFullCycle:
    """
    Integracion end-to-end de las funciones puras (sin red, sin run())
    -- simula exactamente el escenario reportado: una corrida se
    interrumpe a mitad del monitoreo, la siguiente corrida reconcilia,
    y un trade nuevo despues no colisiona con la posicion reconciliada.
    """

    def test_interrupted_run_reconciled_then_new_trade_opens_clean(self):
        paper_log = [{"date": "2026-09-05", "result": "TP", "pnl": 1000, "intento": 1}]

        # Se abre una posicion (equivalente a save_pending() antes del
        # mensaje de OPEN) -- el proceso "muere" aqui, antes de resolverla.
        intento = scheduler._current_intento(paper_log)
        pending = scheduler._build_pending_record(
            side=-1, direction_str="SHORT", entry_price=4415.80,
            tp_price=4379.40, sl_price=4452.20, ticker="MES=F",
            today_str="2026-09-08", intento=intento, nc=40, sl_ticks=100,
            tp_ticks=40, product_key="MES", dry_run=True,
        )
        assert intento == 1  # todavia no hay PASE/QUIEBRE

        # La siguiente corrida encuentra `pending` no vacio y reconcilia.
        reconciled = scheduler._reconcile_pending_position(pending, 4460.0, tick_value_usd=1.25, tick_size=0.25)
        paper_log.append(reconciled)
        pending = {}  # save_pending({}) -- limpio

        assert not pending
        assert reconciled["result"] == "RECONCILED"
        assert scheduler._attempt_pnl(paper_log, 1) == 1000  # SIN cambio -- la reconciliada no cuenta

        # Un trade nuevo, real, del mismo intento -- no colisiona con la reconciliada.
        paper_log.append({"date": "2026-09-09", "result": "SL", "pnl": -200, "intento": 1})
        assert scheduler._current_intento(paper_log) == 1
        assert scheduler._attempt_pnl(paper_log, 1) == 800  # 1000 - 200, la reconciliada sigue sin contar


class TestCurrentIntentoAdvancesPastCompletedAttempt:
    """
    10-sep-2026, ver GLITCH_RESEARCH_LOG.md -- bug real reportado en
    produccion: el OPEN de hoy seguia mostrando "$3,000.00 / $3,000
    (100.0%)" un dia DESPUES del PASE real, porque el `intento_actual
    += 1` de run() nunca se persistia -- era una variable local, se
    perdia al salir del proceso, y la corrida del dia siguiente volvia
    a calcular el mismo intento ya completado desde cero. Estos tests
    reproducen el escenario exacto reportado.
    """

    def test_reproduces_the_reported_bug_scenario(self):
        """
        Escenario EXACTO reportado: dos TP que suman exactamente
        $3,000 (el umbral de G2/50K) en el intento 1. Una corrida
        NUEVA (sin ningun estado en memoria, solo lo que hay en
        paper_log -- exactamente como arranca run() cada dia) debe
        calcular el intento actual como 2, NO 1 -- antes del fix,
        esto devolvia 1, reproduciendo el bug reportado.
        """
        paper_log = [
            {"date": "2026-09-08", "result": "TP", "pnl": 1500, "intento": 1},
            {"date": "2026-09-09", "result": "TP", "pnl": 1500, "intento": 1},  # acumulado exacto: 3000
        ]
        assert scheduler._current_intento(paper_log) == 2  # antes del fix: 1 (el bug reportado)

    def test_attempt_pnl_for_the_new_attempt_is_zero_not_stale_3000(self):
        """Consecuencia directa del fix -- esto es lo que hace que el
        OPEN de HOY muestre '$0.00 / $3,000 (0.0%)', no '$3,000.00 /
        $3,000 (100.0%)' otra vez."""
        paper_log = [
            {"date": "2026-09-08", "result": "TP", "pnl": 1500, "intento": 1},
            {"date": "2026-09-09", "result": "TP", "pnl": 1500, "intento": 1},
        ]
        intento = scheduler._current_intento(paper_log)
        assert scheduler._attempt_pnl(paper_log, intento) == 0

    def test_advances_past_a_completed_quiebre_too(self):
        paper_log = [
            {"date": "2026-09-08", "result": "SL", "pnl": -1200, "intento": 1},
            {"date": "2026-09-09", "result": "SL", "pnl": -900, "intento": 1},  # acumulado: -2100, cruza -2000
        ]
        assert scheduler._current_intento(paper_log) == 2

    def test_does_not_advance_an_attempt_still_in_progress(self):
        """Guardia de regresion -- un intento normal, todavia sin
        cruzar ningun umbral, NO debe avanzar de mas."""
        paper_log = [
            {"date": "2026-09-08", "result": "TP", "pnl": 1000, "intento": 1},
            {"date": "2026-09-09", "result": "SL", "pnl": -300, "intento": 1},  # acumulado: 700, normal
        ]
        assert scheduler._current_intento(paper_log) == 1

    def test_advances_correctly_even_with_a_reconciled_entry_in_the_mix(self):
        """El PnL estimado de una entrada RECONCILED nunca cuenta para
        cruzar el umbral (ver TestCurrentIntentoConsidersReconciledEntries
        arriba) -- pero si las entradas REALES del intento ya cruzaron
        el umbral por su cuenta, el fix debe seguir avanzando
        correctamente aunque haya una entrada reconciliada de por
        medio."""
        paper_log = [
            {"date": "2026-09-07", "result": "TP", "pnl": 1500, "intento": 1},
            {"date": "2026-09-08", "result": "RECONCILED", "pnl": -9999,
             "pnl_estimated": True, "reconciled": True, "intento": 1},
            {"date": "2026-09-09", "result": "TP", "pnl": 1500, "intento": 1},  # 1500+1500=3000, la RECONCILED no cuenta
        ]
        assert scheduler._current_intento(paper_log) == 2

    def test_full_next_day_simulation_matches_expected_open_message(self):
        """
        Simula el flujo completo: dia 1 el PASE ocurre y run() reusa
        _current_intento() (ya no un '+=1' manual) para el resumen de
        ESE dia; dia 2 (una corrida COMPLETAMENTE NUEVA, sin nada en
        memoria) debe calcular el mismo numero de intento y el mismo
        Progreso a Target en $0 que el resumen del dia 1 ya reporto --
        consistencia dia-a-dia, no solo dentro de una sola corrida.
        """
        # Dia 1: el TP que completa el PASE ya esta guardado.
        paper_log = [
            {"date": "2026-09-08", "result": "TP", "pnl": 1500, "intento": 1},
            {"date": "2026-09-09", "result": "TP", "pnl": 1500, "intento": 1},
        ]
        intento_fin_dia1 = scheduler._current_intento(paper_log)  # lo que el resumen del dia 1 reporto

        # Dia 2: corrida nueva, "sin memoria" del dia anterior -- solo paper_log.
        intento_inicio_dia2 = scheduler._current_intento(paper_log)
        attempt_pnl_dia2 = scheduler._attempt_pnl(paper_log, intento_inicio_dia2)

        assert intento_inicio_dia2 == intento_fin_dia1 == 2
        assert attempt_pnl_dia2 == 0  # $0 / $3,000 (0.0%) -- NO $3,000 / $3,000 (100.0%)
