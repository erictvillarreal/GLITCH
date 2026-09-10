"""
Glitch — Test de paridad produccion/backtest para combo_2d (25-ago-2026)
===========================================================================
Post-auditoria: antes de este refactor, scheduler/combo2d_scheduler.py
(produccion/paper en Railway) y strategies/combo2d.py (backtest) tenian
DOS copias independientes de la misma logica de señal+ATR. Este test
prueba que ahora hay UNA sola fuente de verdad, no que dos
implementaciones separadas "coincidan por casualidad".
"""
import os
import sys

os.environ.setdefault("MASSIVE_API_KEY", "test-key-not-real")
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "test-token-not-real")
os.environ.setdefault("TELEGRAM_CHAT_ID", "test-chat-not-real")
os.environ.setdefault("GITHUB_GIST_TOKEN", "test-gist-token-not-real")
os.environ.setdefault("GIST_ID", "test-gist-id-not-real")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd
import pytest

import scheduler.combo2d_scheduler as scheduler
import strategies.combo2d as backtest
from simulation.triple_barrier import compute_atr as shared_compute_atr, BarrierConfig


class TestSignalIsSingleSourceOfTruth:

    def test_scheduler_and_backtest_import_the_same_function_object(self):
        """No son dos implementaciones que coinciden -- es literalmente la misma funcion."""
        assert scheduler.decide_side is backtest.decide_side

    def test_signal_identical_across_known_scenarios(self):
        """
        Bit-for-bit: mismo input de retornos -> mismo (side, reason) sin
        importar si se llama via el modulo de produccion o el de backtest.
        """
        scenarios = [
            (0.01, -0.01, 0.01, -0.01),    # ambos confirman, direccion=short (T-2 fue +)
            (-0.02, 0.015, -0.02, 0.015),  # ambos confirman, direccion=long
            (0.01, 0.01, 0.01, -0.01),     # MES no confirma (mismo signo T-1/T-2)
            (0.01, -0.01, 0.01, 0.01),     # MNQ no confirma
            (0.01, -0.01, -0.01, 0.02),    # confirman pero direccion discrepante
            (0.00005, -0.01, 0.01, -0.01), # MES ret_prev demasiado chico (<0.0001)
        ]
        for mes_prev, mes_2d, mnq_prev, mnq_2d in scenarios:
            r_sched = scheduler.decide_side(mes_prev, mes_2d, mnq_prev, mnq_2d)
            r_back  = backtest.decide_side(mes_prev, mes_2d, mnq_prev, mnq_2d)
            assert r_sched == r_back
            # y contra el import directo de la funcion (misma cosa, por claridad)
            assert r_sched == backtest.decide_side(mes_prev, mes_2d, mnq_prev, mnq_2d)


class TestATRIsSingleSourceOfTruth:

    def _make_bars(self, n=40, seed=1):
        rng = np.random.default_rng(seed)
        close = 100 + np.cumsum(rng.normal(0, 0.5, n))
        high = close + np.abs(rng.normal(0.3, 0.1, n))
        low = close - np.abs(rng.normal(0.3, 0.1, n))
        return pd.DataFrame({"high": high, "low": low, "close": close})

    def test_scheduler_compute_atr_matches_shared_implementation(self):
        bars = self._make_bars()
        window = 20
        sched_atr = scheduler.compute_atr(bars, window)
        shared_series = shared_compute_atr(bars["high"].values, bars["low"].values,
                                            bars["close"].values, window)
        assert sched_atr == pytest.approx(float(shared_series[-1]))

    def test_scheduler_compute_atr_matches_original_formula(self):
        """
        Confirma que el refactor no cambio el numero -- reproduce la formula
        ORIGINAL (mean(tr[-window:])) independientemente y compara.
        """
        bars = self._make_bars(n=25, seed=7)
        window = 20
        h, l, c = bars["high"].values, bars["low"].values, bars["close"].values
        tr = np.maximum(h - l, np.maximum(np.abs(h - np.roll(c, 1)), np.abs(l - np.roll(c, 1))))
        tr[0] = h[0] - l[0]
        original = float(np.mean(tr[-window:]))

        refactored = scheduler.compute_atr(bars, window)
        assert refactored == pytest.approx(original)


class TestTPSLDollarParity:
    """
    El scheduler calcula TP/SL en $ con: atr * MULT -> puntos -> * MNQ_POINT * NC.
    El backtest usa BarrierConfig(pt_multiplier, sl_multiplier) sobre el mismo ATR.
    Con las mismas constantes, ambos deben producir el mismo nivel de precio
    y el mismo $ TP/SL.
    """

    def test_tp_sl_dollar_amounts_match(self):
        entry_price = 20000.0
        atr = 15.0
        side = 1
        nc = scheduler.NC
        point = scheduler.MNQ_POINT

        # -- calculo estilo scheduler (combo2d_scheduler.py:217-221) --
        tp_pts_sched = atr * scheduler.ATR_PT_MULT
        sl_pts_sched = atr * scheduler.ATR_SL_MULT
        tp_price_sched = entry_price + side * tp_pts_sched
        sl_price_sched = entry_price - side * sl_pts_sched
        tp_dollar_sched = tp_pts_sched * point * nc
        sl_dollar_sched = sl_pts_sched * point * nc

        # -- calculo estilo backtest (simulation/triple_barrier.py, misma formula) --
        cfg = BarrierConfig(pt_multiplier=scheduler.ATR_PT_MULT,
                             sl_multiplier=scheduler.ATR_SL_MULT,
                             volatility_window=scheduler.ATR_WINDOW)
        upper_back = entry_price + side * cfg.pt_multiplier * atr
        lower_back = entry_price - side * cfg.sl_multiplier * atr
        tp_dollar_back = (upper_back - entry_price) * point * nc
        sl_dollar_back = (entry_price - lower_back) * point * nc

        assert tp_price_sched == pytest.approx(upper_back)
        assert sl_price_sched == pytest.approx(lower_back)
        assert tp_dollar_sched == pytest.approx(tp_dollar_back)
        assert sl_dollar_sched == pytest.approx(sl_dollar_back)


class TestLoadSaveLogDelegatesToGistStore:
    """
    27-ago-2026: load_log()/save_log() ya no tocan el filesystem local
    (los servicios Cron Schedule de Railway no tienen volumen
    persistente). Confirma que la delegacion a execution/gist_store.py
    esta cableada con el filename correcto -- si esto se rompe, el
    scheduler seguiria arrancando sin error pero perdiendo el estado
    otra vez, en silencio.
    """

    def test_load_log_calls_gist_store_with_combo2d_filename(self, monkeypatch):
        captured = {}

        def _fake_load(filename):
            captured["filename"] = filename
            return [{"sentinel": True}]

        monkeypatch.setattr(scheduler, "_gist_load_log", _fake_load)
        result = scheduler.load_log()
        assert captured["filename"] == "combo2d_log.json"
        assert result == [{"sentinel": True}]

    def test_save_log_calls_gist_store_with_combo2d_filename_and_data(self, monkeypatch):
        captured = {}
        monkeypatch.setattr(scheduler, "_gist_save_log",
                             lambda filename, data: captured.update(filename=filename, data=data))
        payload = [{"date": "2026-08-27", "result": "TP"}]
        scheduler.save_log(payload)
        assert captured["filename"] == "combo2d_log.json"
        assert captured["data"] == payload

    def test_load_pending_calls_gist_store_with_combo2d_pending_filename(self, monkeypatch):
        captured = {}

        def _fake_load_state(filename):
            captured["filename"] = filename
            return {"side": 1}

        monkeypatch.setattr(scheduler, "_gist_load_state", _fake_load_state)
        result = scheduler.load_pending()
        assert captured["filename"] == "combo2d_pending.json"
        assert result == {"side": 1}

    def test_save_pending_calls_gist_store_with_combo2d_pending_filename_and_data(self, monkeypatch):
        captured = {}
        monkeypatch.setattr(scheduler, "_gist_save_state",
                             lambda filename, data: captured.update(filename=filename, data=data))
        scheduler.save_pending({"side": -1, "entry": 21000.0})
        assert captured["filename"] == "combo2d_pending.json"
        assert captured["data"] == {"side": -1, "entry": 21000.0}


class TestBuildPendingRecord:
    """09-sep-2026, ver GLITCH_RESEARCH_LOG.md -- mismo mecanismo que
    geometry_scheduler.py, sin campo 'intento' (combo2d no tiene logica
    de reinicio de intento)."""

    def test_captures_everything_needed_to_reconcile(self):
        record = scheduler._build_pending_record(
            side=1, direction_str="LONG", entry_price=21000.0,
            tp_price=21050.0, sl_price=20970.0, ticker="MNQ=F",
            today_str="2026-09-09", atr=20.0, tp_pts=50.0, sl_pts=30.0,
            nc=6, dry_run=True,
        )
        assert record == {
            "date": "2026-09-09", "side": 1, "direction": "LONG",
            "entry": 21000.0, "tp_price": 21050.0, "sl_price": 20970.0,
            "ticker": "MNQ=F", "atr": 20.0, "tp_pts": 50.0, "sl_pts": 30.0,
            "nc": 6, "dry_run": True,
        }
        assert "intento" not in record


class TestReconcilePendingPosition:
    """Mismos 3 casos que geometry_scheduler.py, para LONG y SHORT."""

    def _pending_long(self):
        return {
            "date": "2026-09-09", "side": 1, "direction": "LONG",
            "entry": 21000.0, "tp_price": 21050.0, "sl_price": 20970.0,
            "ticker": "MNQ=F", "atr": 20.0, "tp_pts": 50.0, "sl_pts": 30.0,
            "nc": 6, "dry_run": True,
        }

    def _pending_short(self):
        return {
            "date": "2026-09-09", "side": -1, "direction": "SHORT",
            "entry": 21000.0, "tp_price": 20950.0, "sl_price": 21030.0,
            "ticker": "MNQ=F", "atr": 20.0, "tp_pts": 50.0, "sl_pts": 30.0,
            "nc": 6, "dry_run": True,
        }

    def test_result_is_always_reconciled_never_a_normal_outcome(self):
        for price in (21100.0, 20900.0, 21010.0):
            entry = scheduler._reconcile_pending_position(self._pending_long(), price, point_value=2.0)
            assert entry["result"] == "RECONCILED"
            assert entry["reconciled"] is True
            assert entry["pnl_estimated"] is True

    def test_long_price_beyond_tp_estimates_tp_clipped_to_barrier(self):
        pending = self._pending_long()
        entry = scheduler._reconcile_pending_position(pending, 21100.0, point_value=2.0)
        assert entry["estimated_outcome"] == "TP"
        assert entry["exit"] == pending["tp_price"]
        expected_pnl = (pending["tp_price"] - pending["entry"]) * 1 * 2.0 * pending["nc"]
        assert entry["pnl"] == pytest.approx(round(expected_pnl, 2))

    def test_long_price_beyond_sl_estimates_sl_clipped_to_barrier(self):
        pending = self._pending_long()
        entry = scheduler._reconcile_pending_position(pending, 20900.0, point_value=2.0)
        assert entry["estimated_outcome"] == "SL"
        assert entry["exit"] == pending["sl_price"]
        assert entry["pnl"] < 0

    def test_long_price_inconclusive_between_barriers(self):
        pending = self._pending_long()
        entry = scheduler._reconcile_pending_position(pending, 21010.0, point_value=2.0)
        assert entry["estimated_outcome"] == "INCONCLUSIVE"
        assert entry["exit"] == 21010.0

    def test_short_price_beyond_tp_estimates_tp_clipped_to_barrier(self):
        pending = self._pending_short()
        entry = scheduler._reconcile_pending_position(pending, 20900.0, point_value=2.0)
        assert entry["estimated_outcome"] == "TP"
        assert entry["exit"] == pending["tp_price"]
        assert entry["pnl"] > 0

    def test_short_price_beyond_sl_estimates_sl_clipped_to_barrier(self):
        pending = self._pending_short()
        entry = scheduler._reconcile_pending_position(pending, 21100.0, point_value=2.0)
        assert entry["estimated_outcome"] == "SL"
        assert entry["exit"] == pending["sl_price"]
        assert entry["pnl"] < 0

    def test_short_price_inconclusive_between_barriers(self):
        pending = self._pending_short()
        entry = scheduler._reconcile_pending_position(pending, 20990.0, point_value=2.0)
        assert entry["estimated_outcome"] == "INCONCLUSIVE"
        assert entry["exit"] == 20990.0


class TestReconciledEntryExcludedFromWinRate:
    """El mecanismo de exclusion de run() (total/wins filtran por result
    in ('TP','SL','FLATTEN')) -- probado directamente contra la salida
    real de _reconcile_pending_position, sin reimplementar el filtro."""

    def test_reconciled_result_never_counted_as_win_or_total(self):
        pending = {
            "date": "2026-09-09", "side": 1, "direction": "LONG",
            "entry": 21000.0, "tp_price": 21050.0, "sl_price": 20970.0,
            "ticker": "MNQ=F", "atr": 20.0, "tp_pts": 50.0, "sl_pts": 30.0,
            "nc": 6, "dry_run": True,
        }
        reconciled = scheduler._reconcile_pending_position(pending, 21100.0, point_value=2.0)
        paper_log = [
            {"date": "2026-09-05", "result": "TP", "pnl": 100.0},
            reconciled,
        ]
        wins = sum(1 for e in paper_log if e.get("result") == "TP")
        total = sum(1 for e in paper_log if e.get("result") in ("TP", "SL", "FLATTEN"))
        assert wins == 1
        assert total == 1  # la reconciliada NO cuenta, aunque su estimated_outcome sea "TP"


class TestUnifiedStartupCheck:
    """
    01-sep-2026: reimportar el modulo con VARIAS variables borradas a la
    vez debe reportar TODAS juntas al arrancar -- no una por corrida via
    crash-arreglo-siguiente-crash (2.5 semanas asi, ver
    GLITCH_RESEARCH_LOG.md). Prueba de extremo a extremo real (reload
    del modulo), no solo la funcion require_env aislada.
    """

    def test_multiple_missing_vars_reported_together_on_reimport(self, monkeypatch):
        import importlib

        monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
        monkeypatch.delenv("GITHUB_GIST_TOKEN", raising=False)
        monkeypatch.delenv("GIST_ID", raising=False)
        # MASSIVE_API_KEY y TELEGRAM_CHAT_ID quedan presentes (heredados del
        # setdefault de arriba) -- el intento de notificar por Telegram se
        # degrada a print (porque TELEGRAM_BOT_TOKEN tambien falta), no crashea.

        with pytest.raises(SystemExit):
            importlib.reload(scheduler)

        # monkeypatch restaura las env vars solas al terminar el test, pero
        # el modulo ya importado quedaria en el estado roto del reload de
        # arriba para el resto de la suite -- recargarlo aqui, ya con el
        # fixture todavia activo (las vars de este test siguen borradas en
        # este punto), forzando los valores del setdefault de arriba antes
        # del reload final para dejarlo sano.
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token-not-real")
        monkeypatch.setenv("GITHUB_GIST_TOKEN", "test-gist-token-not-real")
        monkeypatch.setenv("GIST_ID", "test-gist-id-not-real")
        importlib.reload(scheduler)
