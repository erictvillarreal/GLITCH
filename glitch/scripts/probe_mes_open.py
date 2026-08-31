"""
Glitch — Sonda en tiempo real de MES=F durante la apertura RTH (28-ago/31-ago-2026)
======================================================================================
Diagnostico, NO parte de ningun scheduler. Corre standalone durante la
ventana critica (9:25-9:45 CT) para capturar minuto a minuto que trae
realmente yf.Ticker("MES=F").history() mientras el problema esta
ocurriendo -- las verificaciones post-hoc (horas despues) siempre
mostraron datos completos, porque para entonces Yahoo ya habia
rellenado el hueco. Esta es la unica forma de ver el estado real
durante la ventana en la que geometry_scheduler.py reporto 12/12
intentos vacios el 31-ago-2026 (09:27-09:37 CT).

Loguea, en cada poll (cada 15s):
  - filas totales devueltas por el fetch crudo (sin filtrar)
  - la fecha/hora del ULTIMO timestamp en el DataFrame crudo (antes de
    cualquier filtro RTH) -- esto muestra directamente si Yahoo esta
    "atrasado" (el ultimo dato es de ayer o de hace horas) o si SI hay
    datos de hoy pero el filtro de dia/hora los descarta por otro motivo
  - filas que sobreviven al mismo filtro RTH exacto que usa
    geometry_scheduler.py (9:30-14:30 CT)
  - lo mismo para MNQ=F en paralelo, para comparar directamente contra
    el simbolo que combo2d SI usa sin este problema

Uso:
    python scripts/probe_mes_open.py
Correr manualmente, arrancando unos minutos antes de las 9:25 CT.
Detener con Ctrl+C cuando ya haya pasado 9:45 CT o el problema se
haya resuelto solo.
"""
from __future__ import annotations
import time
from datetime import date, datetime
from zoneinfo import ZoneInfo

import pandas as pd
import yfinance as yf

CT = ZoneInfo("America/Chicago")
TICKERS = ["MES=F", "MNQ=F"]
POLL_INTERVAL = 15  # segundos -- mas fino que los 30s del scheduler real, para ver el hueco con mas resolucion


def ct_now():
    return datetime.now(CT)


def probe(ticker: str) -> dict:
    raw = yf.Ticker(ticker).history(period="5d", interval="1m", prepost=False)
    if raw.empty:
        return {"ticker": ticker, "raw_rows": 0, "last_raw_ts": None, "rth_rows_today": 0}

    last_raw_ts = raw.index[-1]

    d = raw.reset_index()
    d.columns = [c.lower() for c in d.columns]
    tcol = [c for c in d.columns if "date" in c or "time" in c][0]
    d["dt"] = pd.to_datetime(d[tcol], utc=True).dt.tz_convert(CT)
    d["t"] = d["dt"].dt.hour * 60 + d["dt"].dt.minute
    d["day"] = d["dt"].dt.date
    today = date.today()
    rth = d[(d["day"] == today) & (d["t"] >= 9 * 60 + 30) & (d["t"] <= 14 * 60 + 30)]

    return {
        "ticker": ticker,
        "raw_rows": len(raw),
        "last_raw_ts": last_raw_ts,
        "rth_rows_today": len(rth),
        "last_rth_ts": rth["dt"].iloc[-1] if len(rth) else None,
    }


def main():
    print(f"Sonda iniciada {ct_now().strftime('%Y-%m-%d %H:%M:%S')} CT -- Ctrl+C para detener")
    print(f"{'hora CT':>10}  {'ticker':>7}  {'raw_rows':>8}  {'ultimo_raw_ts (CT origen)':>28}  {'rth_rows_hoy':>13}  {'ultimo_rth_ts':>20}")
    while True:
        now_str = ct_now().strftime("%H:%M:%S")
        for ticker in TICKERS:
            try:
                r = probe(ticker)
            except Exception as e:
                print(f"{now_str:>10}  {ticker:>7}  ERROR: {e}")
                continue
            last_raw = str(r["last_raw_ts"]) if r["last_raw_ts"] is not None else "N/A"
            last_rth = str(r.get("last_rth_ts")) if r.get("last_rth_ts") is not None else "N/A"
            print(f"{now_str:>10}  {r['ticker']:>7}  {r['raw_rows']:>8}  {last_raw:>28}  {r['rth_rows_today']:>13}  {last_rth:>20}")
        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nSonda detenida.")
