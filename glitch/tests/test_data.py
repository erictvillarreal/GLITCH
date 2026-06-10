"""
Glitch — Data loader tests
"""
import pytest
import numpy as np
import pandas as pd
from data.loader import (
    DataLoader, INSTRUMENT_SPECS, resample_ohlcv,
    filter_rth, add_session_labels, _validate, _generate_synthetic
)

REQUIRED_COLS = {"open","high","low","close","volume"}


class TestInstrumentSpecs:
    def test_mes_mnq_defined(self):
        assert "MES" in INSTRUMENT_SPECS and "MNQ" in INSTRUMENT_SPECS

    def test_tick_values_correct(self):
        assert INSTRUMENT_SPECS["MES"]["tick_value_usd"] == 1.25
        assert INSTRUMENT_SPECS["MNQ"]["tick_value_usd"] == 0.50

    def test_mnq_more_volatile_than_mes(self):
        assert INSTRUMENT_SPECS["MNQ"]["daily_vol_pct"] > INSTRUMENT_SPECS["MES"]["daily_vol_pct"]


class TestSyntheticLoader:
    def _load(self, sym="MES", start="2023-01-01", end="2023-06-30", schema="ohlcv-1m"):
        return DataLoader(source="synthetic").fetch(sym, start, end, schema)

    def test_returns_dataframe(self):
        df = self._load()
        assert isinstance(df, pd.DataFrame)

    def test_required_columns(self):
        df = self._load()
        assert REQUIRED_COLS.issubset(set(df.columns))

    def test_utc_index(self):
        df = self._load()
        assert str(df.index.tz) == "UTC"

    def test_sorted_index(self):
        df = self._load()
        assert df.index.is_monotonic_increasing

    def test_high_gte_low(self):
        df = self._load()
        assert (df["high"] >= df["low"]).all()

    def test_high_gte_close(self):
        df = self._load()
        assert (df["high"] >= df["close"]).all()

    def test_low_lte_close(self):
        df = self._load()
        assert (df["low"] <= df["close"]).all()

    def test_volume_positive(self):
        df = self._load()
        assert (df["volume"] > 0).all()

    def test_mes_vol_calibrated(self):
        """Daily vol should be within 0.5% of target."""
        df = DataLoader(source="synthetic").fetch("MES","2022-01-01","2024-12-31","ohlcv-1m")
        daily = resample_ohlcv(df, "1D")
        vol = daily["close"].pct_change().dropna().std() * 100
        target = INSTRUMENT_SPECS["MES"]["daily_vol_pct"] * 100
        assert abs(vol - target) < 0.5, f"Vol {vol:.2f}% too far from target {target:.1f}%"

    def test_mnq_vol_calibrated(self):
        df = DataLoader(source="synthetic").fetch("MNQ","2022-01-01","2024-12-31","ohlcv-1m")
        daily = resample_ohlcv(df, "1D")
        vol = daily["close"].pct_change().dropna().std() * 100
        target = INSTRUMENT_SPECS["MNQ"]["daily_vol_pct"] * 100
        assert abs(vol - target) < 0.5

    def test_reproducible_with_same_seed(self):
        df1 = DataLoader(source="synthetic").fetch("MES","2023-01-01","2023-06-30",seed=99)
        df2 = DataLoader(source="synthetic").fetch("MES","2023-01-01","2023-06-30",seed=99)
        pd.testing.assert_frame_equal(df1, df2)

    def test_different_seeds_differ(self):
        df1 = DataLoader(source="synthetic").fetch("MES","2023-01-01","2023-06-30",seed=1)
        df2 = DataLoader(source="synthetic").fetch("MES","2023-01-01","2023-06-30",seed=2)
        assert not df1["close"].equals(df2["close"])

    def test_mnq_higher_price_than_mes(self):
        d_mes = DataLoader(source="synthetic").fetch("MES","2023-01-01","2023-06-30")
        d_mnq = DataLoader(source="synthetic").fetch("MNQ","2023-01-01","2023-06-30")
        assert d_mnq["close"].mean() > d_mes["close"].mean()

    def test_bar_count_reasonable(self):
        # ~6 months = ~130 trading days × 1330 min/day
        df = self._load(start="2023-01-01", end="2023-06-30")
        assert 100_000 < len(df) < 300_000

    def test_unknown_symbol_raises(self):
        with pytest.raises(ValueError, match="Unknown symbol"):
            DataLoader(source="synthetic").fetch("ZZZ","2023-01-01","2023-06-30")


class TestResample:
    def test_resample_to_daily(self):
        df = DataLoader(source="synthetic").fetch("MES","2023-01-01","2023-06-30","ohlcv-1m")
        daily = resample_ohlcv(df, "1D")
        assert len(daily) < len(df) // 100
        assert (daily["high"] >= daily["low"]).all()

    def test_resample_preserves_session_extremes(self):
        df = DataLoader(source="synthetic").fetch("MES","2023-06-01","2023-06-30","ohlcv-1m")
        hourly = resample_ohlcv(df, "1h")
        daily  = resample_ohlcv(df, "1D")
        # Daily high should be >= max of hourly highs on same day
        assert (daily["high"].max() >= hourly["high"].max())


class TestSessionFilter:
    def test_rth_reduces_bars(self):
        df  = DataLoader(source="synthetic").fetch("MES","2023-01-01","2023-06-30","ohlcv-1m")
        rth = filter_rth(df)
        assert len(rth) < len(df)
        assert len(rth) > 0

    def test_rth_index_still_utc(self):
        df  = DataLoader(source="synthetic").fetch("MES","2023-01-01","2023-06-30","ohlcv-1m")
        rth = filter_rth(df)
        assert str(rth.index.tz) == "UTC"

    def test_session_labels_cover_all_bars(self):
        df = DataLoader(source="synthetic").fetch("MES","2023-01-01","2023-03-31","ohlcv-1m")
        labeled = add_session_labels(df)
        assert "session" in labeled.columns
        assert labeled["session"].notna().all()
        sessions = set(labeled["session"].unique())
        assert sessions == {"overnight","open","midday","close"}


class TestValidation:
    def test_missing_column_raises(self):
        df = pd.DataFrame({"open":[1],"high":[2],"low":[0],"close":[1]}, index=[pd.Timestamp.now(tz="UTC")])
        with pytest.raises(ValueError, match="Missing columns"):
            _validate(df, "MES")
