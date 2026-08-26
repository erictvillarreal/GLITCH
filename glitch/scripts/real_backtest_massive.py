import os, sys, itertools, datetime, warnings
warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from massive import RESTClient

from strategies.orb import ORBConfig, generate_orb_signals
from simulation.triple_barrier import BarrierConfig, label_triple_barrier, extract_daily_pnl_from_labels
from simulation.monte_carlo import DailyReturnDist, TopstepMonteCarloSimulator
from core.prop_firm import TOPSTEP_50K

API_KEY = os.environ.get("POLYGON_API_KEY", "")
client = RESTClient(API_KEY)

TICKER = "MESH7"
START = "2025-12-19"
END = datetime.date.today().isoformat()
POINT_VALUE_USD = 5.0   # MES = $5/point (ver INSTRUMENT_SPECS en data/loader.py)
N_CONTRACTS = 10

print(f"Descargando {TICKER} 5min {START} -> {END}...")
rows = []
gen = client.list_futures_aggregates(
    ticker=TICKER, resolution="5min",
    window_start_gte=START, window_start_lte=END,
    sort="window_start.asc",
)
for a in gen:
    rows.append({
        "ts": pd.to_datetime(a.window_start, unit="ns", utc=True),
        "open": a.open, "high": a.high, "low": a.low, "close": a.close,
        "volume": a.volume,
    })
prices = pd.DataFrame(rows).set_index("ts").sort_index()
print(f"{len(prices):,} barras, {prices.index.min()} -> {prices.index.max()}")
prices.to_csv("mesh7_5min.csv")

if len(prices) < 500:
    print("Muy pocos datos, revisar.")
    sys.exit(1)

cfg = ORBConfig(or_minutes=15, confirm_close=True)
sig = generate_orb_signals(prices, cfg)
print(f"Señales: {len(sig)}")

bcfg = BarrierConfig(pt_multiplier=3.0, sl_multiplier=1.5, max_holding_bars=60, volatility_window=100)
longs = sig[sig.side == 1]["entry_idx"].values
shorts = sig[sig.side == -1]["entry_idx"].values
labels_l = label_triple_barrier(prices, longs, bcfg, side=1) if len(longs) else pd.DataFrame()
labels_s = label_triple_barrier(prices, shorts, bcfg, side=-1) if len(shorts) else pd.DataFrame()
labels = pd.concat([labels_l, labels_s], ignore_index=True) if len(labels_l) or len(labels_s) else pd.DataFrame()
print(f"Trades etiquetados: {len(labels)}")

if labels.empty:
    print("Sin trades.")
    sys.exit(0)

wr = (labels["label"] == 1).mean()
wins = labels.loc[labels.label == 1, "pnl_usd"] * POINT_VALUE_USD * N_CONTRACTS
losses = (labels.loc[labels.label == -1, "pnl_usd"] * POINT_VALUE_USD * N_CONTRACTS).abs()
daily_pnl = extract_daily_pnl_from_labels(labels, prices, point_value_usd=POINT_VALUE_USD, n_contracts=N_CONTRACTS)

print(f"\nMuestra: {len(labels)} trades en {len(daily_pnl)} dias")
print(f"Win rate: {wr:.1%}")
print(f"Avg win:  ${wins.mean():.0f}" if len(wins) else "sin wins")
print(f"Avg loss: ${losses.mean():.0f}" if len(losses) else "sin losses")

if len(daily_pnl) >= 15:
    dist = DailyReturnDist.from_trade_log(daily_pnl, name="ORB_MESH7_real")
    print(f"\n{dist.describe()}")
    sim = TopstepMonteCarloSimulator(dist, TOPSTEP_50K, n_paths=10000, max_days=15, seed=7)
    r = sim.run()
    print(f"Pass rate (15 dias): {r.pass_rate:.1%}")
    print(f"Blow rate: {r.blow_rate:.1%}")
    print(f"Avg dias a pasar: {r.avg_pass_days}")
else:
    print(f"\nSolo {len(daily_pnl)} dias -- todavia ruidoso, pero mas solido que Yahoo (6 dias).")
