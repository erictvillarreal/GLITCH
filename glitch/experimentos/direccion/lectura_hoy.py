"""Lectura de hoy (informativa, NO se aplica): que dirian R1-R3 para el 21-oct con Yahoo MES=F (menor calidad que el parquet)."""
import datetime as dt
import sys

import numpy as np
import pandas as pd
import yfinance as yf

df = yf.download("MES=F", start="2026-05-01", end="2026-10-22", interval="1d", progress=False, auto_adjust=False)
df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
df.index = pd.to_datetime(df.index).date
ROLL = dt.date(2026, 9, 18)                         # tercer viernes de septiembre (mismo patron que los 8 rolls del parquet)
close, open_, high, low = df.Close, df.Open, df.High, df.Low
same = np.array([d != ROLL for d in df.index])
chg = np.where(same, close.diff(), close - open_); chg[0] = 0
adj = close.iloc[0] + np.cumsum(chg)
tr = np.maximum(high - low, np.maximum((high - close.shift()).abs(), (low - close.shift()).abs())); tr = np.where(same, tr, high - low)
a = pd.DataFrame({"adj": adj, "tr": tr}, index=df.index)
a["sma20"] = a.adj.rolling(20).mean(); a["sma50"] = a.adj.rolling(50).mean(); a["atr14"] = a.tr.rolling(14).mean()
for label, last in (("cierre COMPLETO mas reciente (19-oct)", dt.date(2026, 10, 19)), ("20-oct PROVISIONAL (barra diaria incompleta de Yahoo)", dt.date(2026, 10, 20))):
    r = a.loc[last]
    c, s20, s50, atr = r.adj, r.sma20, r.sma50, r.atr14
    down = (c < s20) and (s20 < s50)
    r1 = "LONG" if c > s20 else "SHORT"; r2 = "SHORT" if down else "LONG"
    r3 = "NO OPERAR" if abs(c - s20) < 0.5 * atr else r2
    print(f"{label}: cierre_ajustado={c:.2f} SMA20={s20:.2f} SMA50={s50:.2f} ATR14={atr:.2f} | c-SMA20={c - s20:+.2f} (0.5*ATR14={0.5 * atr:.2f}) | R1={r1} R2={r2} R3={r3}")
