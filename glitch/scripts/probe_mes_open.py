"""
Glitch — Sonda en tiempo real de MES=F durante la apertura RTH (27-ago/31-ago-2026)
======================================================================================
Diagnostico, NO parte de ningun scheduler de trading. Corre standalone
durante la ventana critica (~9:20-9:40 CT) para capturar minuto a
minuto que trae realmente yf.Ticker("MES=F").history() mientras el
problema esta ocurriendo -- las verificaciones post-hoc (horas
despues) siempre mostraron datos completos, porque para entonces
Yahoo ya habia rellenado el hueco. Esta es la unica forma de ver el
estado real durante la ventana en la que geometry_scheduler.py
reporto 12/12 intentos vacios el 31-ago-2026 (09:27-09:37 CT).

DISEÑO PARA RAILWAY (28-ago-2026): pensado para correr como servicio
Cron Schedule separado, temporal, disparado UNA VEZ antes de la
apertura -- NO como el script manual original (que esperaba Ctrl+C).
Corre por DURATION_MINUTES, termina solo, y manda un resumen completo
a Telegram al final -- asi el resultado llega al telefono sin tener
que entrar a Railway a buscar logs.

Variables de entorno requeridas: SOLO TELEGRAM_BOT_TOKEN y
TELEGRAM_CHAT_ID (mismo bot/chat que los schedulers reales) -- nada de
GITHUB_GIST_TOKEN/GIST_ID, este script no persiste nada, es una
corrida unica de diagnostico.

IMPORTANTE (cron): una expresion cron estandar de 5 campos (ej.
"20 14 * * 2") NO puede expresar "solo esta vez" -- disparara TODOS
los martes indefinidamente si el servicio se deja configurado asi.
Borrar el Cron Schedule (o el servicio completo) despues de confirmar
el resultado de mañana para no seguir gastando llamadas de Yahoo/
Telegram cada semana sin necesidad.

Uso local (manual, comportamiento original):
    python scripts/probe_mes_open.py
Uso en Railway: Start Command = "python glitch/scripts/probe_mes_open.py",
Cron Schedule apuntado unos minutos antes de la apertura real.
"""
from __future__ import annotations
import os
import sys
import time
from datetime import date, datetime
from zoneinfo import ZoneInfo

import pandas as pd
import yfinance as yf

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scheduler.telegram_bot import send

CT = ZoneInfo("America/Chicago")
TICKERS = ["MES=F", "MNQ=F"]
POLL_INTERVAL = 15   # segundos -- mas fino que los 30s del scheduler real, para ver el hueco con mas resolucion
DURATION_MINUTES = 20  # corre esto y termina solo, no espera Ctrl+C


def ct_now():
    return datetime.now(CT)


def probe(ticker: str) -> dict:
    raw = yf.Ticker(ticker).history(period="5d", interval="1m", prepost=False)
    if raw.empty:
        return {"ticker": ticker, "raw_rows": 0, "last_raw_ts": None, "rth_rows_today": 0, "last_rth_ts": None}

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


def build_summary(history: dict) -> str:
    """
    history: {ticker: [(poll_ct_time_str, rth_rows_today), ...]} -- solo
    transiciones (cuando rth_rows_today cambia respecto al poll anterior),
    para que el mensaje de Telegram sea legible en un telefono en vez de
    un dump de 80 lineas identicas.
    """
    lines = ["GLITCH - SONDA MES=F | RESULTADO"]
    for ticker, polls in history.items():
        first_time, first_rows = polls[0]
        first_nonzero = next(((t, r) for t, r in polls if r > 0), None)
        lines.append(f"\n{ticker}:")
        lines.append(f"  Inicio sonda: {first_time} CT, rth_rows={first_rows}")
        if first_nonzero:
            lines.append(f"  Primera fila RTH detectada: {first_nonzero[0]} CT (rows={first_nonzero[1]})")
        else:
            lines.append(f"  NUNCA aparecio una fila RTH en toda la ventana de {DURATION_MINUTES} min")
        lines.append(f"  Transiciones observadas: {len(polls)}")
        for t, r in polls:
            lines.append(f"    {t} CT -> rth_rows={r}")
    return "\n".join(lines)


def main():
    start = ct_now()
    print(f"Sonda iniciada {start.strftime('%Y-%m-%d %H:%M:%S')} CT -- correra {DURATION_MINUTES} min y terminara sola")

    end_time = time.time() + DURATION_MINUTES * 60
    history: dict[str, list] = {t: [] for t in TICKERS}
    last_seen: dict[str, int | None] = {t: None for t in TICKERS}

    while time.time() < end_time:
        now_str = ct_now().strftime("%H:%M:%S")
        for ticker in TICKERS:
            try:
                r = probe(ticker)
                rows = r["rth_rows_today"]
            except Exception as e:
                print(f"{now_str}  {ticker}  ERROR: {e}")
                continue

            last_raw = str(r["last_raw_ts"]) if r["last_raw_ts"] is not None else "N/A"
            last_rth = str(r.get("last_rth_ts")) if r.get("last_rth_ts") is not None else "N/A"
            print(f"{now_str}  {ticker:>7}  raw_rows={r['raw_rows']:>5}  ultimo_raw={last_raw}  "
                  f"rth_rows_hoy={rows:>4}  ultimo_rth={last_rth}")

            if last_seen[ticker] is None or rows != last_seen[ticker]:
                history[ticker].append((now_str, rows))
                last_seen[ticker] = rows

        time.sleep(POLL_INTERVAL)

    print("Sonda terminada -- enviando resumen a Telegram.")
    summary = build_summary(history)
    print(summary)
    # Telegram limita mensajes a 4096 caracteres -- esto es una corrida
    # unica sin reintento si send() falla por longitud, asi que se recorta
    # con margen en vez de arriesgar perder el resultado por completo.
    if len(summary) > 3800:
        summary = summary[:3800] + "\n\n[... recortado, ver logs de Railway para el detalle completo]"
    send(summary)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nSonda detenida manualmente (Ctrl+C).")
