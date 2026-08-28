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
