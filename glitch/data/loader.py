"""
Glitch — Market Data Loader
============================
Handles data acquisition for MES / MNQ futures.

ARCHITECTURE: Three-tier fallback system
─────────────────────────────────────────
Tier 1 — Databento (production, requires API key + $)
  Best source for CME micro futures tick/OHLCV data.
  Dataset: GLBX.MDP3 (CME Globex MDP 3.0)
  Schemas: ohlcv-1m, ohlcv-1h, ohlcv-1d, trades, mbp-1
  Cost: ~$0.30–2.00 per symbol-month at 1-min resolution
  Continuous contracts: supported via front-month roll

Tier 2 — Polygon.io (production, requires API key, Starter $29/mo)
  Has CME futures OHLCV + snapshots.
  Tickers: MES (micro ES), MNQ (micro NQ)
  Note: historical bars API for futures is newer — verify coverage

Tier 3 — Synthetic calibrated data (zero cost, local, always works)
  GBM + volatility clustering calibrated to real MES/MNQ statistics.
  Use for: unit tests, algorithm development, parameter sensitivity.
  NOT for: final edge validation before paying a challenge.

USAGE
─────
# Production (Databento):
loader = DataLoader(source="databento", api_key="db-xxx")
df = loader.fetch("MES", start="2023-01-01", end="2024-12-31", schema="ohlcv-1m")

# Production (Polygon):
loader = DataLoader(source="polygon", api_key="your-key")
df = loader.fetch("MES", start="2023-01-01", end="2024-12-31", timespan="minute")

# Development / simulated environment (no key needed):
loader = DataLoader(source="synthetic")
df = loader.fetch("MES", start="2023-01-01", end="2024-12-31", schema="ohlcv-1m")

OUTPUT FORMAT (all tiers produce identical schema)
──────────────────────────────────────────────────
DataFrame with DatetimeIndex (UTC), columns:
  open, high, low, close, volume
  [optional] symbol, session  (trading session label)
"""

from __future__ import annotations
import os
import warnings
from pathlib import Path
from typing import Optional, Literal
from dataclasses import dataclass

import numpy as np
import pandas as pd


# ── Instrument specs (CME micro futures) ──────────────────────────────────

INSTRUMENT_SPECS = {
    "MES": {
        "full_name":        "Micro E-mini S&P 500",
        "exchange":         "CME",
        "tick_size":        0.25,
        "tick_value_usd":   1.25,       # $1.25 per tick
        "point_value_usd":  5.0,        # $5 per full point
        "typical_price":    5000,       # approximate current level
        "daily_vol_pct":    0.012,      # ~1.2% daily volatility (annualised ~19%)
        "annual_vol_pct":   0.18,
        "mean_daily_ret":   0.0003,     # slight upward drift (~7.5%/yr)
        "session_open_ct":  "17:00",    # 5 PM CT previous day
        "session_close_ct": "15:10",    # 3:10 PM CT
        "databento_symbol": "MES",
        "polygon_ticker":   "MES",
    },
    "MNQ": {
        "full_name":        "Micro E-mini Nasdaq-100",
        "exchange":         "CME",
        "tick_size":        0.25,
        "tick_value_usd":   0.50,       # $0.50 per tick
        "point_value_usd":  2.0,        # $2 per full point
        "typical_price":    20000,
        "daily_vol_pct":    0.016,      # ~1.6% daily vol (NQ more volatile than ES)
        "annual_vol_pct":   0.24,
        "mean_daily_ret":   0.0004,
        "session_open_ct":  "17:00",
        "session_close_ct": "15:10",
        "databento_symbol": "MNQ",
        "polygon_ticker":   "MNQ",
    },
}


# ── Output schema validation ───────────────────────────────────────────────

REQUIRED_COLUMNS = {"open", "high", "low", "close", "volume"}

def _validate(df: pd.DataFrame, symbol: str) -> pd.DataFrame:
    """Enforce standard output schema."""
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"[{symbol}] Missing columns: {missing}")
    df = df[sorted(REQUIRED_COLUMNS)].copy()
    df.index = pd.to_datetime(df.index, utc=True)
    df = df.sort_index()
    # Sanity: high >= low, high >= open/close, low <= open/close
    bad = (df["high"] < df["low"]).sum()
    if bad > 0:
        warnings.warn(f"[{symbol}] {bad} bars with high < low — clipping")
        df["high"] = df[["high", "low", "open", "close"]].max(axis=1)
        df["low"]  = df[["high", "low", "open", "close"]].min(axis=1)
    return df


# ── Tier 1: Databento ─────────────────────────────────────────────────────

def _fetch_databento(
    symbol: str,
    start: str,
    end: str,
    schema: str = "ohlcv-1m",
    api_key: str = "",
    cache_dir: Optional[Path] = None,
) -> pd.DataFrame:
    """
    Fetch CME micro futures OHLCV from Databento.

    Requirements:
      - API key: https://databento.com/signup
      - Package: pip install databento
      - Cost: ~$0.30/symbol-month for 1-min OHLCV (GLBX.MDP3)

    Continuous contract note:
      Databento uses front-month roll. Symbol "MES" automatically
      returns the active front-month contract.

    Schema options:
      ohlcv-1m   : 1-minute OHLCV bars (recommended)
      ohlcv-1h   : 1-hour OHLCV bars
      ohlcv-1d   : daily OHLCV bars
      trades     : individual tick trades (large, expensive)
    """
    try:
        import databento as db
    except ImportError:
        raise ImportError("pip install databento")

    if not api_key:
        api_key = os.environ.get("DATABENTO_API_KEY", "")
    if not api_key:
        raise ValueError(
            "Databento API key required.\n"
            "Set env var DATABENTO_API_KEY or pass api_key=...\n"
            "Get a free key + $10 credit at https://databento.com"
        )

    # Check cache first
    if cache_dir:
        cache_dir = Path(cache_dir)
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_file = cache_dir / f"{symbol}_{start}_{end}_{schema}.parquet"
        if cache_file.exists():
            print(f"[databento] Loading from cache: {cache_file}")
            return pd.read_parquet(cache_file)

    client = db.Historical(api_key)

    print(f"[databento] Fetching {symbol} {schema} {start}→{end}...")
    data = client.timeseries.get_range(
        dataset="GLBX.MDP3",           # CME Globex
        symbols=[symbol],
        schema=schema,
        start=start,
        end=end,
        stype_in="continuous",         # front-month roll
    )

    df = data.to_df()

    # Databento column mapping
    col_map = {
        "open":   "open",
        "high":   "high",
        "low":    "low",
        "close":  "close",
        "volume": "volume",
        # Databento uses nanosecond timestamps
    }
    df = df.rename(columns={v: k for k, v in col_map.items() if v in df.columns})

    # Prices in Databento are in fixed-point (divide by 1e9 for futures)
    for col in ["open", "high", "low", "close"]:
        if col in df.columns and df[col].mean() > 1_000_000:
            df[col] = df[col] / 1_000_000_000

    if cache_dir:
        df.to_parquet(cache_file)
        print(f"[databento] Cached to {cache_file}")

    return _validate(df, symbol)


# ── Tier 2: Polygon.io ────────────────────────────────────────────────────

def _fetch_polygon(
    symbol: str,
    start: str,
    end: str,
    timespan: str = "minute",
    multiplier: int = 1,
    api_key: str = "",
    cache_dir: Optional[Path] = None,
) -> pd.DataFrame:
    """
    Fetch CME micro futures OHLCV from Polygon.io.

    Requirements:
      - API key: https://polygon.io (Starter plan $29/mo for futures)
      - Package: pip install polygon-api-client

    Note: Polygon's futures coverage for MES/MNQ extends back to ~2019.
    Verify coverage for your date range before use.
    """
    try:
        from polygon import RESTClient
    except ImportError:
        raise ImportError("pip install polygon-api-client")

    if not api_key:
        api_key = os.environ.get("POLYGON_API_KEY", "")
    if not api_key:
        raise ValueError(
            "Polygon API key required.\n"
            "Set env var POLYGON_API_KEY or pass api_key=...\n"
            "Get a free key at https://polygon.io (free tier has 2yr delay)"
        )

    if cache_dir:
        cache_dir = Path(cache_dir)
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_file = cache_dir / f"poly_{symbol}_{start}_{end}_{timespan}{multiplier}.parquet"
        if cache_file.exists():
            print(f"[polygon] Loading from cache: {cache_file}")
            return pd.read_parquet(cache_file)

    client = RESTClient(api_key)
    print(f"[polygon] Fetching {symbol} {multiplier}-{timespan} {start}→{end}...")

    aggs = []
    for bar in client.list_aggs(
        ticker=f"/{symbol}",           # Polygon uses /MES prefix for futures
        multiplier=multiplier,
        timespan=timespan,
        from_=start,
        to=end,
        limit=50_000,
        adjusted=False,
    ):
        aggs.append({
            "timestamp": pd.Timestamp(bar.timestamp, unit="ms", tz="UTC"),
            "open":   bar.open,
            "high":   bar.high,
            "low":    bar.low,
            "close":  bar.close,
            "volume": bar.volume or 0,
        })

    if not aggs:
        raise ValueError(f"[polygon] No data returned for {symbol} {start}→{end}")

    df = pd.DataFrame(aggs).set_index("timestamp")

    if cache_dir:
        df.to_parquet(cache_file)

    return _validate(df, symbol)


# ── Tier 3: Synthetic calibrated data ─────────────────────────────────────

def _generate_synthetic(
    symbol: str,
    start: str,
    end: str,
    freq: str = "1min",
    seed: int = 42,
    regime_changes: bool = True,
) -> pd.DataFrame:
    """
    Generate synthetic OHLCV calibrated to real MES/MNQ statistics.

    Model: Geometric Brownian Motion with:
      - Volatility clustering (GARCH-like: vol scales on |prev_return|)
      - Intraday vol profile (U-shape: high at open/close, low midday)
      - Session gaps (overnight move on re-open)
      - Regime changes (bull/bear/chop) if regime_changes=True

    Calibration targets (from CME data 2019-2024):
      MES: daily vol ~1.2%, mean drift ~+0.03%/day
      MNQ: daily vol ~1.6%, mean drift ~+0.04%/day

    USE FOR:
      ✓ Strategy development and debugging
      ✓ Monte Carlo parameter sensitivity
      ✓ Unit testing pipeline correctness
      ✗ Final edge validation (use real data)
    """
    spec = INSTRUMENT_SPECS.get(symbol, INSTRUMENT_SPECS["MES"])
    rng  = np.random.default_rng(seed)

    # Build trading session timestamps (5PM CT prev day → 3:10PM CT)
    # Approximate: 22.17 hours of trading per day, ~1330 minutes
    trading_minutes_per_day = 22 * 60 + 10  # 1330

    dt_start = pd.Timestamp(start, tz="America/Chicago")
    dt_end   = pd.Timestamp(end,   tz="America/Chicago")
    bdays    = pd.bdate_range(dt_start, dt_end, freq="B")
    n_days   = len(bdays)

    if n_days == 0:
        raise ValueError(f"No business days between {start} and {end}")

    freq_minutes = {
        "1min": 1, "5min": 5, "15min": 15,
        "30min": 30, "1h": 60, "1d": 390
    }.get(freq, 1)

    bars_per_day = trading_minutes_per_day // freq_minutes
    total_bars   = n_days * bars_per_day

    # ── Regime model ──────────────────────────────────────────────────────
    daily_vol  = spec["daily_vol_pct"]
    daily_ret  = spec["mean_daily_ret"]

    if regime_changes:
        # Three regimes: bull (drift+), bear (drift-), chop (low vol)
        regime_probs  = np.array([0.55, 0.25, 0.20])   # bull, bear, chop
        regime_drifts = np.array([daily_ret * 1.5, -daily_ret * 2.0, daily_ret * 0.2])
        regime_vols   = np.array([daily_vol * 0.9, daily_vol * 1.6, daily_vol * 0.7])
        # Regime transitions: Markov chain, mean duration ~40 days
        regime = 0
        day_regimes = []
        for _ in range(n_days):
            day_regimes.append(regime)
            if rng.random() < 0.025:   # ~4% chance of regime change per day
                regime = rng.choice(3, p=regime_probs)
        day_drifts = np.array([regime_drifts[r] for r in day_regimes])
        day_vols   = np.array([regime_vols[r]   for r in day_regimes])
    else:
        day_drifts = np.full(n_days, daily_ret)
        day_vols   = np.full(n_days, daily_vol)

    # ── Intraday vol profile (U-shape) ────────────────────────────────────
    # Normalised 0→1 across bars_per_day
    t        = np.linspace(0, 1, bars_per_day)
    vol_mult = 1.4 - 0.8 * np.sin(np.pi * t) + 0.3 * (t < 0.05) + 0.3 * (t > 0.95)
    vol_mult = vol_mult / vol_mult.mean()   # normalise to mean=1

    # ── GARCH-like vol clustering ─────────────────────────────────────────
    bar_vol_base = day_vols[:, None] / np.sqrt(bars_per_day)  # (n_days, 1)
    bar_vol      = bar_vol_base * vol_mult[None, :]            # (n_days, bars_per_day)

    # ── Generate returns ──────────────────────────────────────────────────
    returns = rng.normal(
        loc   = day_drifts[:, None] / bars_per_day,
        scale = bar_vol,
        size  = (n_days, bars_per_day)
    )

    # Vol clustering: scale bar vol by |prev bar return| (simplified ARCH)
    for i in range(1, total_bars):
        d, b = divmod(i, bars_per_day)
        prev_d, prev_b = divmod(i - 1, bars_per_day)
        arch_factor = 1.0 + 0.15 * abs(returns[prev_d, prev_b]) / bar_vol_base[prev_d, 0]
        returns[d, b] *= min(arch_factor, 3.0)   # cap at 3x

    # ── Build price series ────────────────────────────────────────────────
    p0     = spec["typical_price"]
    log_p  = np.log(p0) + np.cumsum(returns.flatten())
    closes = np.exp(log_p)

    # Round to tick size
    tick   = spec["tick_size"]
    closes = np.round(closes / tick) * tick

    # ── Build OHLCV bars ──────────────────────────────────────────────────
    bar_noise = bar_vol.flatten() * closes * 0.4    # range ~ 80% of bar vol
    highs  = closes + rng.uniform(0, bar_noise)
    lows   = closes - rng.uniform(0, bar_noise)
    opens  = np.roll(closes, 1)
    opens[0] = p0

    # Overnight gap on session open (first bar of each day)
    for d in range(1, n_days):
        i = d * bars_per_day
        gap = rng.normal(0, day_vols[d] * closes[i] * 0.3)   # 30% of daily vol
        opens[i] = closes[i - 1] + gap

    # Volumes: U-shaped with randomness
    base_vol      = 5_000 if symbol == "MES" else 3_000
    volumes       = (np.tile(vol_mult, n_days) * base_vol * rng.lognormal(0, 0.5, total_bars)).astype(int)
    volumes       = np.maximum(volumes, 100)

    # ── Build timestamps ──────────────────────────────────────────────────
    # Each day: 1330 minutes starting from 5:00 PM CT prev evening
    timestamps = []
    for d, bday in enumerate(bdays):
        # Session opens at 17:00 CT day before (simplified: 22h before session close)
        session_start = bday.tz_convert("America/Chicago").replace(
            hour=17, minute=0, second=0
        ) - pd.Timedelta(days=1)
        for b in range(bars_per_day):
            timestamps.append(session_start + pd.Timedelta(minutes=b * freq_minutes))

    ts = pd.DatetimeIndex(timestamps).tz_convert("UTC")

    df = pd.DataFrame({
        "open":   opens,
        "high":   highs,
        "low":    lows,
        "close":  closes,
        "volume": volumes,
    }, index=ts)

    # Clip high/low to valid range
    df["high"] = df[["high", "open", "close"]].max(axis=1)
    df["low"]  = df[["low",  "open", "close"]].min(axis=1)

    return _validate(df, symbol)


# ── Resample utilities ─────────────────────────────────────────────────────

def resample_ohlcv(df: pd.DataFrame, freq: str) -> pd.DataFrame:
    """Resample minute bars to any higher timeframe."""
    return df.resample(freq).agg({
        "open":   "first",
        "high":   "max",
        "low":    "min",
        "close":  "last",
        "volume": "sum",
    }).dropna()


def filter_rth(df: pd.DataFrame, tz: str = "America/Chicago") -> pd.DataFrame:
    """
    Filter to Regular Trading Hours only (9:30 AM – 3:10 PM CT).
    Use for strategies that only trade the cash session.
    """
    local = df.copy()
    local.index = local.index.tz_convert(tz)
    mask = (
        (local.index.time >= pd.Timestamp("09:30").time()) &
        (local.index.time <= pd.Timestamp("15:10").time()) &
        (local.index.dayofweek < 5)   # Mon–Fri
    )
    result = local[mask].copy()
    result.index = result.index.tz_convert("UTC")
    return result


def add_session_labels(df: pd.DataFrame, tz: str = "America/Chicago") -> pd.DataFrame:
    """Add session column: 'overnight', 'open', 'midday', 'close'."""
    local = df.copy()
    local.index = local.index.tz_convert(tz)
    t = local.index.time

    local["session"] = "overnight"
    local.loc[(t >= pd.Timestamp("09:30").time()) & (t < pd.Timestamp("10:30").time()), "session"] = "open"
    local.loc[(t >= pd.Timestamp("10:30").time()) & (t < pd.Timestamp("14:00").time()), "session"] = "midday"
    local.loc[(t >= pd.Timestamp("14:00").time()) & (t <= pd.Timestamp("15:10").time()), "session"] = "close"

    local.index = local.index.tz_convert("UTC")
    return local


# ── Main DataLoader interface ──────────────────────────────────────────────

class DataLoader:
    """
    Unified data loader for Glitch.

    Parameters
    ----------
    source : "databento" | "polygon" | "synthetic"
    api_key : str  (required for databento and polygon)
    cache_dir : path to cache directory (avoids re-downloading)
    """

    def __init__(
        self,
        source: Literal["databento", "polygon", "synthetic"] = "synthetic",
        api_key: str = "",
        cache_dir: Optional[str] = None,
    ):
        self.source    = source
        self.api_key   = api_key or os.environ.get("DATABENTO_API_KEY", "") \
                                 or os.environ.get("POLYGON_API_KEY", "")
        self.cache_dir = Path(cache_dir) if cache_dir else None

    def fetch(
        self,
        symbol: str,
        start: str,
        end: str,
        schema: str = "ohlcv-1m",    # databento schema or synthetic freq
        timespan: str = "minute",    # polygon timespan
        seed: int = 42,
    ) -> pd.DataFrame:
        """
        Fetch OHLCV data. Returns standardised DataFrame.

        Parameters
        ----------
        symbol  : "MES" or "MNQ"
        start   : "YYYY-MM-DD"
        end     : "YYYY-MM-DD"
        schema  : databento schema (ohlcv-1m, ohlcv-1h, ohlcv-1d)
                  OR synthetic freq (1min, 5min, 15min, 1h, 1d)
        timespan: polygon timespan (minute, hour, day)
        """
        symbol = symbol.upper()
        if symbol not in INSTRUMENT_SPECS:
            raise ValueError(f"Unknown symbol '{symbol}'. Choose: {list(INSTRUMENT_SPECS)}")

        if self.source == "databento":
            return _fetch_databento(
                symbol, start, end,
                schema=schema,
                api_key=self.api_key,
                cache_dir=self.cache_dir,
            )
        elif self.source == "polygon":
            return _fetch_polygon(
                symbol, start, end,
                timespan=timespan,
                api_key=self.api_key,
                cache_dir=self.cache_dir,
            )
        elif self.source == "synthetic":
            freq_map = {
                "ohlcv-1m": "1min", "ohlcv-1h": "1h",
                "ohlcv-1d": "1d",   "1min": "1min",
                "5min": "5min",     "15min": "15min",
                "1h": "1h",         "1d": "1d",
            }
            freq = freq_map.get(schema, schema)
            return _generate_synthetic(symbol, start, end, freq=freq, seed=seed)
        else:
            raise ValueError(f"Unknown source '{self.source}'. Choose: databento, polygon, synthetic")

    def cost_estimate(self, symbol: str, start: str, end: str, schema: str = "ohlcv-1m") -> dict:
        """
        Estimate data cost before downloading (Databento only).
        Call this before fetch() to avoid surprise charges.
        """
        if self.source != "databento":
            return {"source": self.source, "cost_usd": 0.0, "note": "No cost"}
        try:
            import databento as db
            client = db.Historical(self.api_key)
            cost = client.metadata.get_cost(
                dataset="GLBX.MDP3",
                symbols=[symbol],
                schema=schema,
                start=start,
                end=end,
                stype_in="continuous",
            )
            return {
                "source": "databento",
                "symbol": symbol,
                "schema": schema,
                "start": start,
                "end": end,
                "cost_usd": cost / 100,   # Databento returns cents
                "note": "Estimated cost. Actual may vary."
            }
        except Exception as e:
            return {"error": str(e)}
