"""Descarga las series diarias de Yahoo Finance usadas por la Parte E (SIN auto_adjust: precios crudos) a data/ (CSV ignorados por git). Fecha de descarga en data/LEEME.txt.
    python fetch_yahoo.py"""
import datetime as dt, os
import pandas as pd
import yfinance as yf
HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.environ.get("GLITCH_E_DATA", os.path.join(HERE, "data")); os.makedirs(OUT, exist_ok=True)
TICKERS = ["GLD", "GC=F", "^GSPC", "SPY", "ES=F", "DX-Y.NYB", "CL=F", "EURUSD=X", "ZN=F"]
log = []
for t in TICKERS:
    d = yf.download(t, start="1990-01-01", end=(dt.date.today() + dt.timedelta(days=1)).isoformat(), interval="1d", progress=False, auto_adjust=False)
    d.columns = [c[0] if isinstance(c, tuple) else c for c in d.columns]
    d.index = pd.to_datetime(d.index).tz_localize(None)
    fn = os.path.join(OUT, t.replace("^", "").replace("=", "_").replace(".", "_") + ".csv"); d.to_csv(fn)
    log.append(f"{t}: {len(d)} dias {d.index.min().date()} -> {d.index.max().date()} ({os.path.basename(fn)})")
open(os.path.join(OUT, "LEEME.txt"), "w").write(f"Descarga {dt.datetime.now():%Y-%m-%d %H:%M} (hora local); yfinance auto_adjust=False\n" + "\n".join(log) + "\n"); print("\n".join(log))
