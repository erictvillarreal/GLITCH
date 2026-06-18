import yfinance as yf
import pandas as pd
import time
import os

print("Esperando 3 segundos antes de iniciar...")
time.sleep(3)

os.makedirs("./Downloads", exist_ok=True)

for ticker_sym in ["ES=F", "MES=F", "MNQ=F"]:
    print(f"Descargando datos para {ticker_sym}...")
    ticker = yf.Ticker(ticker_sym)
    data = ticker.history(period="60d", interval="15m", prepost=True)
    
    if data.empty:
        print(f"⚠️ {ticker_sym}: No se obtuvieron datos")
    else:
        filename = f"{ticker_sym.replace('=', '_')}_15m.csv"
        path = f"./Downloads/{filename}"
        data.to_csv(path)
        print(f"✅ {ticker_sym}: {len(data)} filas guardadas en: {path}")

print("\nProceso terminado.")
