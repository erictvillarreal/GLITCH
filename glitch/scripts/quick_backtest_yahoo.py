"""
Glitch — Backtest rapido con datos recientes de Yahoo Finance
=================================================================
GRATIS, sin cuenta de Topstep ni de Massive. Sirve como PRIMER FILTRO
antes de pagar nada: si el ORB ni siquiera se ve razonable en esta
muestra chica, no vale la pena pagar Massive+Topstep todavia.

LIMITACION: Yahoo solo da ~7 dias de historia intradia de 1min (a veces
menos). Esto es una muestra MUY chica -- no reemplaza el backtest de
2 anios con Massive, solo filtra "obviamente roto" vs "vale la pena
seguir".

Uso:
    cd glitch
    python scripts/quick_backtest_yahoo.py
"""
import sys, os, warnings
warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import yfinance as yf
import pandas as pd

from strategies.orb import ORBConfig, generate_orb_signals
from simulation.triple_barrier import BarrierConfig, label_triple_barrier, extract_daily_pnl_from_labels
from simulation.monte_carlo import DailyReturnDist, TopstepMonteCarloSimulator
from core.prop_firm import TOPSTEP_50K

CONTRACT_VALUE_PER_PCT = 25000.0  # MES ~5000 * point_value $5 (ver nota en triple_barrier.py)
N_CONTRACTS = 10

print("Descargando ~7 dias de MES=F 1min via Yahoo Finance...")
raw = yf.Ticker("MES=F").history(period="7d", interval="1m", prepost=True)
if raw.empty:
    print("ERROR: Yahoo no devolvio datos. Prueba de nuevo en unos minutos o revisa tu red.")
    sys.exit(1)

raw = raw.reset_index()
raw.columns = [c.lower() for c in raw.columns]
tcol = [c for c in raw.columns if "date" in c or "time" in c][0]
raw["ts"] = pd.to_datetime(raw[tcol], utc=True)
prices = raw.set_index("ts").sort_index()[["open", "high", "low", "close", "volume"]]
print(f"{len(prices):,} barras, {prices.index.min()} -> {prices.index.max()}")

cfg = ORBConfig(or_minutes=15, confirm_close=True)
sig = generate_orb_signals(prices, cfg)
print(f"Señales generadas: {len(sig)}")

if len(sig) < 5:
    print("Muy pocas señales en esta ventana chica -- normal con solo ~5 dias de datos. "
          "No es evidencia de nada, solo confirma que el pipeline corre sin errores.")
    sys.exit(0)

bcfg = BarrierConfig(pt_multiplier=3.0, sl_multiplier=1.5, max_holding_bars=60, volatility_window=100)
longs = sig[sig.side == 1]["entry_idx"].values
shorts = sig[sig.side == -1]["entry_idx"].values
labels_l = label_triple_barrier(prices, longs, bcfg, side=1) if len(longs) else pd.DataFrame()
labels_s = label_triple_barrier(prices, shorts, bcfg, side=-1) if len(shorts) else pd.DataFrame()
labels = pd.concat([labels_l, labels_s], ignore_index=True) if len(labels_l) or len(labels_s) else pd.DataFrame()

print(f"Trades etiquetados: {len(labels)}")
if labels.empty:
    print("Sin trades etiquetados -- revisar ventana de datos.")
    sys.exit(0)

wr = (labels["label"] == 1).mean()
wins = labels.loc[labels.label == 1, "pnl_pct"]
losses = labels.loc[labels.label == -1, "pnl_pct"].abs()

daily_pnl = extract_daily_pnl_from_labels(labels, prices, contract_value_per_pct=CONTRACT_VALUE_PER_PCT * N_CONTRACTS)
print(f"\nMuestra: {len(labels)} trades en {len(daily_pnl)} dias (MUY CHICA -- no concluyente)")
print(f"Win rate: {wr:.1%}")
if len(wins):
    print(f"Avg win:  ${wins.mean()*CONTRACT_VALUE_PER_PCT*N_CONTRACTS:.0f}")
if len(losses):
    print(f"Avg loss: ${losses.mean()*CONTRACT_VALUE_PER_PCT*N_CONTRACTS:.0f}")

if len(daily_pnl) >= 3:
    dist = DailyReturnDist.from_trade_log(daily_pnl, name="ORB_yahoo_quick")
    print(f"\n{dist.describe()}")
    sim = TopstepMonteCarloSimulator(dist, TOPSTEP_50K, n_paths=5000, max_days=15, seed=7)
    r = sim.run()
    print(f"Pass rate (15 dias, extrapolado de {len(daily_pnl)} dias de muestra): {r.pass_rate:.1%}")
    print("^ ADVERTENCIA: con <10 dias de muestra este numero es puro ruido, "
          "usalo solo para ver si es 'obviamente cero' o 'no descartable', nada mas.")
else:
    print("\nMenos de 3 dias con trades -- insuficiente hasta para una lectura ruidosa.")
