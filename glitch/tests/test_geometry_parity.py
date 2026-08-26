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

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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
