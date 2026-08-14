"""
Glitch — Backtest real 2 años MES via Massive (paginado)
"""
import sys, os, warnings, time, datetime
warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
import numpy as np
from zoneinfo import ZoneInfo

from massive import RESTClient
from strategies.orb import ORBConfig, generate_orb_signals
from simulation.triple_barrier import BarrierConfig, label_triple_barrier
from simulation.monte_carlo import DailyReturnDist, TopstepMonteCarloSimulator
from core.prop_firm import TOPSTEP_50K

CT      = ZoneInfo("America/Chicago")
API_KEY = os.environ.get("POLYGON_API_KEY", "")
if not API_KEY:
    print("ERROR: falta POLYGON_API_KEY"); sys.exit(1)

N_CONTRACTS = 10
CACHE_FILE  = "data_cache/mes_5min_2y.parquet"
MES_PTS_USD = 5.0  # $5 por punto por contrato

# Front month por período (verificado con volumen real)
CONTRACTS = [
    ("MESZ4", "2024-08-12", "2024-12-19"),
    ("MESH5", "2024-12-19", "2025-03-21"),
    ("MESM5", "2025-03-21", "2025-06-20"),
    ("MESU5", "2025-06-20", "2025-09-19"),
    ("MESZ5", "2025-09-19", "2025-12-19"),
    ("MESH6", "2025-12-19", "2026-03-20"),
    ("MESM6", "2026-03-20", "2026-06-20"),
    ("MESU6", "2026-06-20", "2026-08-12"),
]

def fetch_contract(client, ticker, start, end):
    """Descarga todas las barras de 5min paginando hasta agotar."""
    all_bars = []
    # Pagina en chunks de 30 días para no exceder límites
    t0 = datetime.date.fromisoformat(start)
    t1 = datetime.date.fromisoformat(end)
    chunk = datetime.timedelta(days=30)
    cur = t0
    while cur < t1:
        nxt = min(cur + chunk, t1)
        try:
            bars = list(client.list_futures_aggregates(
                ticker,
                resolution="5min",
                window_start_gte=cur.isoformat(),
                window_start_lte=nxt.isoformat(),
                limit=50000,
                sort="asc",
            ))
            all_bars.extend(bars)
        except Exception as e:
            print(f"    WARNING {ticker} {cur}->{nxt}: {str(e)[:60]}")
        cur = nxt
        time.sleep(0.2)
    return all_bars

def load_prices():
    os.makedirs("data_cache", exist_ok=True)
    if os.path.exists(CACHE_FILE):
        print(f"Cache encontrado: {CACHE_FILE}")
        df = pd.read_parquet(CACHE_FILE)
        print(f"  {len(df):,} barras RTH, {df.index.min().date()} -> {df.index.max().date()}")
        return df

    print("Descargando 2 años de MES (front month chain)...")
    client   = RESTClient(API_KEY)
    all_rows = []

    for ticker, start, end in CONTRACTS:
        print(f"  {ticker} {start} -> {end}...", flush=True)
        bars = fetch_contract(client, ticker, start, end)
        print(f"    {len(bars):,} barras brutas")
        for b in bars:
            ts = datetime.datetime.fromtimestamp(
                b.window_start / 1e9, tz=datetime.timezone.utc
            ).astimezone(CT)
            all_rows.append({
                "dt": ts, "open": b.open, "high": b.high,
                "low": b.low, "close": b.close,
                "volume": b.volume or 0,
            })

    df = pd.DataFrame(all_rows).set_index("dt").sort_index()
    df = df[["open","high","low","close","volume"]]

    # RTH: 9:30-15:14 CT, lun-vie
    t = df.index.hour * 60 + df.index.minute
    df = df[(t >= 9*60+30) & (t <= 15*60+14) & (df.index.dayofweek < 5)]
    df = df[~df.index.duplicated(keep="first")]

    # Filtra barras de muy bajo volumen (roll artifacts)
    df = df[df["volume"] >= 50]

    print(f"\nTotal RTH: {len(df):,} barras")
    print(f"Rango: {df.index.min().date()} -> {df.index.max().date()}")
    print(f"Días únicos: {df.index.normalize().nunique()}")
    df.to_parquet(CACHE_FILE)
    return df

def compute_daily_pnl(labels, prices, n_contracts):
    """PnL en USD usando precio real de entrada."""
    records = []
    for _, row in labels.iterrows():
        if row["label"] == 0:
            continue
        idx = int(row["entry_idx"])
        if idx >= len(prices):
            continue
        entry_px = float(prices.iloc[idx]["close"])
        pnl_pts  = row["pnl_pct"] * entry_px
        pnl_usd  = pnl_pts * MES_PTS_USD * n_contracts
        records.append({"date": prices.index[idx].date(), "pnl": pnl_usd})
    if not records:
        return np.array([])
    df = pd.DataFrame(records)
    return df.groupby("date")["pnl"].sum().values

def run_variant(name, sig, prices, pt_mult, sl_mult, nc=N_CONTRACTS):
    bcfg = BarrierConfig(
        pt_multiplier=pt_mult, sl_multiplier=sl_mult,
        max_holding_bars=60, volatility_window=100,
    )
    longs  = sig[sig.side ==  1]["entry_idx"].values
    shorts = sig[sig.side == -1]["entry_idx"].values
    ll = label_triple_barrier(prices, longs,  bcfg, side= 1) if len(longs)  else pd.DataFrame()
    ls = label_triple_barrier(prices, shorts, bcfg, side=-1) if len(shorts) else pd.DataFrame()
    labels = pd.concat([ll, ls], ignore_index=True) if (len(ll) or len(ls)) else pd.DataFrame()

    if labels.empty or len(labels) < 30:
        print(f"  [{name}] pocos trades ({len(labels)}), skip")
        return None

    wr        = (labels["label"] == 1).mean()
    daily_pnl = compute_daily_pnl(labels, prices, nc)

    if len(daily_pnl) < 15:
        print(f"  [{name}] pocos días ({len(daily_pnl)}), skip")
        return None

    dist = DailyReturnDist.from_trade_log(daily_pnl, name=name)
    sim  = TopstepMonteCarloSimulator(
        dist, TOPSTEP_50K, n_paths=10000, max_days=15, seed=7
    )
    r = sim.run()

    wins   = daily_pnl[daily_pnl > 0]
    losses = daily_pnl[daily_pnl < 0]
    print(f"  [{name}] N={len(labels)} WR={wr:.1%} "
          f"avgW=${wins.mean():.0f} avgL=${losses.mean():.0f} "
          f"EV/dia=${dist.expected_daily_pnl:.0f} "
          f"pass15d={r.pass_rate:.1%} blow={r.blow_rate:.1%}")

    return dict(
        variant=name, n_trades=len(labels), n_days=len(daily_pnl),
        win_rate=round(wr, 3),
        avg_win=round(wins.mean(), 1)    if len(wins)   else 0,
        avg_loss=round(losses.mean(), 1) if len(losses) else 0,
        ev_day=round(dist.expected_daily_pnl, 1),
        pass_rate_15d=round(r.pass_rate, 4),
        blow_rate=round(r.blow_rate, 4),
        avg_pass_days=round(r.avg_pass_days, 1) if r.avg_pass_days else None,
    )

# ── MAIN ──────────────────────────────────────────────────────────────────
prices = load_prices()
assert len(prices) >= 500, f"Solo {len(prices)} barras — revisa la descarga"

results = []

# V1: ORB baseline
print("\n=== V1: ORB baseline (15min, pt=3.0, sl=1.5) ===")
cfg      = ORBConfig(or_minutes=15, confirm_close=True)
sig_base = generate_orb_signals(prices, cfg)
print(f"  Señales totales: {len(sig_base)}")
r = run_variant("ORB_baseline", sig_base, prices, 3.0, 1.5)
if r: results.append(r)

# V2: Sweep pt/sl
print("\n=== V2: sweep pt/sl ===")
for pt in [2.0, 2.5, 3.0, 4.0]:
    for sl in [1.0, 1.5, 2.0]:
        r = run_variant(f"ORB_pt{pt}_sl{sl}", sig_base, prices, pt, sl)
        if r: results.append(r)

# V3: Regime filter sin lookahead (shift 1)
print("\n=== V3: ORB + regime filter (no lookahead) ===")
daily_df             = prices.resample("1D").agg({"high":"max","low":"min"})
daily_df["range"]    = daily_df["high"] - daily_df["low"]
daily_df["median20"] = daily_df["range"].shift(1).rolling(20, min_periods=10).median()
daily_df["prev_rng"] = daily_df["range"].shift(1)
trending             = set(
    daily_df[daily_df["prev_rng"] >= daily_df["median20"]].index.date
)
sig2    = sig_base.copy()
sig2["d"] = prices.index[sig2["entry_idx"].values].date
sig_r   = sig2[sig2["d"].isin(trending)].drop(columns=["d"])
print(f"  Señales con filtro: {len(sig_r)} / {len(sig_base)}")
r = run_variant("ORB_regime", sig_r, prices, 3.0, 1.5)
if r: results.append(r)

# ── Tabla final ────────────────────────────────────────────────────────────
df_res = pd.DataFrame(results).sort_values("pass_rate_15d", ascending=False)
print("\n" + "="*100)
print("RESULTADOS — datos REALES 2 años MES via Massive")
print("="*100)
pd.set_option("display.width", 200)
print(df_res.to_string(index=False) if len(df_res) else "SIN RESULTADOS")
df_res.to_csv("real_backtest_results.csv", index=False)
print("\nGuardado: real_backtest_results.csv")
