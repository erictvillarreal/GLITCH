"""
Glitch — Re-fetch de MGC con ventana horaria CORRECTA (07-sep-2026)
========================================================================
El mgc_5min_2y.parquet existente se descargó con fetch_mes_2y.py, cuyo
filtro RTH está hardcodeado para equity index: "8:30-15:00 CT (9:30-16:00
ET), estandar para indices". Gold NO comparte esa ventana:

  - CME/COMEX cita 8:20am-1:30pm ET (7:20am-12:30pm CT) como la sesión
    "regular" heredada del pit.
  - Fuentes independientes de mercado citan el overlap Londres-NY
    (8:00am-12:00pm ET = 7:00am-11:00am CT) como la ventana de mayor
    liquidez real de gold.
  - Evidencia interna: en el parquet YA existente, el volumen de la
    PRIMERA barra capturada (8:30 CT) ya es el pico (29.1% del volumen
    del día capturado) y decae monótonamente el resto del día -- la
    tendencia, extrapolada hacia atrás, sugiere que 7:00-8:30 CT
    (totalmente ausente del dataset actual) es probablemente MÁS
    activo, no menos. Ver GLITCH_RESEARCH_LOG.md, 07-sep-2026, para el
    detalle completo de ambas fuentes.

Este script reutiliza EXACTAMENTE la misma lógica de descubrimiento de
contratos y roll que fetch_mes_2y.py (mismo método, sin reimplementar)
-- el ÚNICO cambio es la ventana RTH: 7:00-15:00 CT en vez de
8:30-15:00 CT, para capturar la ventana de mayor liquidez documentada
sin excluir nada de lo que ya se tenía. NO se modifica fetch_mes_2y.py
directamente porque ese filtro SÍ es correcto para los productos de
equity index (MES, M2K) ya descargados con él -- cambiarlo ahí
rompería datos ya validados de otros productos.

NO EJECUTADO TODAVÍA -- requiere MASSIVE_API_KEY, no disponible en el
shell local de esta sesión. Correr en Railway (donde la key ya vive) o
en cualquier entorno donde el usuario la tenga exportada:

    export MASSIVE_API_KEY="..."
    python scripts/fetch_mgc_correct_window.py

Una vez corrido, ANTES de usar este dataset para el scheduler:
  1. Re-correr scripts/validate_mgc_wr_empirical.py y
     scripts/validate_mgc_subperiods_and_direction.py contra el nuevo
     parquet -- confirmar que WR≈50% se sostiene con la ventana
     correcta (podría cambiar si la ventana perdida tenía dinámica de
     precio distinta).
  2. Comparar el WR viejo vs nuevo explícitamente antes de descartar
     el dataset anterior -- documentar la diferencia, no solo asumir
     que "más datos es mejor" sin medirlo.
"""
from __future__ import annotations
import os, re, sys, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import requests

API_KEY = os.environ.get("MASSIVE_API_KEY") or os.environ.get("POLYGON_API_KEY", "")
if not API_KEY:
    print("ERROR: falta MASSIVE_API_KEY (o POLYGON_API_KEY)")
    sys.exit(1)

BASE = "https://api.massive.com"
HEADERS = {"Authorization": f"Bearer {API_KEY}"}


def _get(path: str, params: dict, max_pages: int = 20) -> list[dict]:
    url = BASE + path
    out = []
    for _ in range(max_pages):
        r = requests.get(url, headers=HEADERS, params=params, timeout=20)
        r.raise_for_status()
        data = r.json()
        out.extend(data.get("results", []))
        next_url = data.get("next_url")
        if not next_url:
            break
        url = next_url if next_url.startswith("http") else BASE + next_url
        params = {}
    return out


PRODUCT = "MGC"
END_DATE = dt.date.today()
START_DATE = END_DATE - dt.timedelta(days=730)
ROLL_BUFFER_DAYS = 8
OUT_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         "data_cache", "mgc_5min_2y_corrected_window.parquet")

REF_DATES = pd.date_range(START_DATE, END_DATE, freq="MS").tolist()
if not REF_DATES or REF_DATES[0] > pd.Timestamp(START_DATE):
    REF_DATES = [pd.Timestamp(START_DATE)] + REF_DATES
REF_DATES.append(pd.Timestamp(END_DATE))

_TICKER_RE = re.compile(rf"^{PRODUCT}[FGHJKMNQUVXZ]\d{{1,2}}$")


def _valid_outright_ticker(ticker: str) -> bool:
    return bool(_TICKER_RE.match(ticker))


def discover_contracts() -> pd.DataFrame:
    seen = {}
    for ref in REF_DATES:
        ref_str = ref.date().isoformat()
        try:
            results = _get("/futures/v1/contracts",
                            {"product_code": PRODUCT, "date": ref_str, "active": "true", "limit": 250})
        except Exception as e:
            print(f"  [warn] contracts@{ref_str}: {e}")
            continue
        n_valid = 0
        for c in results:
            if c.get("type") and c["type"] != "single":
                continue
            ticker = c.get("ticker")
            if not ticker or not _valid_outright_ticker(ticker):
                continue
            ltd, ftd = c.get("last_trade_date"), c.get("first_trade_date")
            if not ltd or not ftd:
                continue
            seen[ticker] = {"ticker": ticker, "first_trade_date": ftd, "last_trade_date": ltd}
            n_valid += 1
        print(f"  contracts@{ref_str}: {len(results)} filas ({n_valid} validas), {len(seen)} tickers unicos acumulados")

    if not seen:
        raise RuntimeError(f"discover_contracts: cero contratos outright validos para {PRODUCT}")

    df = pd.DataFrame(seen.values())
    df["last_trade_date"] = pd.to_datetime(df["last_trade_date"])
    df["first_trade_date"] = pd.to_datetime(df["first_trade_date"])
    return df.sort_values("last_trade_date").reset_index(drop=True)


def build_roll_schedule(contracts: pd.DataFrame) -> list[dict]:
    contracts = contracts[
        (contracts["last_trade_date"] >= pd.Timestamp(START_DATE)) &
        (contracts["first_trade_date"] <= pd.Timestamp(END_DATE))
    ].sort_values("last_trade_date").reset_index(drop=True)

    schedule = []
    seg_start = pd.Timestamp(START_DATE)
    for _, row in contracts.iterrows():
        roll_date = row["last_trade_date"] - pd.Timedelta(days=ROLL_BUFFER_DAYS)
        seg_end = min(roll_date, pd.Timestamp(END_DATE))
        if seg_end <= seg_start:
            continue
        schedule.append({"ticker": row["ticker"], "start": seg_start.date().isoformat(), "end": seg_end.date().isoformat()})
        seg_start = seg_end + pd.Timedelta(days=1)
        if seg_start > pd.Timestamp(END_DATE):
            break
    return schedule


def fetch_segment(ticker: str, start: str, end: str) -> pd.DataFrame:
    rows = []
    try:
        results = _get(f"/futures/v1/aggs/{ticker}", {
            "resolution": "5min", "window_start_gte": start, "window_start_lte": end,
            "sort": "window_start.asc", "limit": 5000,
        }, max_pages=50)
        for a in results:
            rows.append({
                "ts": pd.to_datetime(a["window_start"], unit="ns", utc=True),
                "open": a["open"], "high": a["high"], "low": a["low"], "close": a["close"],
                "volume": a.get("volume", 0), "contract": ticker,
            })
    except Exception as e:
        print(f"  [warn] aggs {ticker} {start}->{end}: {e}")
    return pd.DataFrame(rows)


def main():
    print(f"Descubriendo contratos {PRODUCT} activos {START_DATE} -> {END_DATE}...")
    contracts = discover_contracts()
    schedule = build_roll_schedule(contracts)
    print(f"\nSchedule de roll ({len(schedule)} segmentos)")

    all_frames = []
    for s in schedule:
        print(f"Descargando {s['ticker']} {s['start']} -> {s['end']}...")
        seg = fetch_segment(s["ticker"], s["start"], s["end"])
        print(f"  {len(seg)} barras")
        if not seg.empty:
            all_frames.append(seg)

    if not all_frames:
        print("Sin datos descargados. Abortando.")
        sys.exit(1)

    prices = pd.concat(all_frames, ignore_index=True).drop_duplicates(subset="ts")
    prices = prices.set_index("ts").sort_index()

    # VENTANA CORREGIDA para gold: 7:00-15:00 CT (vs 8:30-15:00 CT usado
    # para equity index) -- cubre el overlap Londres-NY (7:00-11:00 CT)
    # documentado como la ventana de mayor liquidez real de gold, sin
    # excluir nada de lo que el dataset anterior ya tenia.
    local = prices.index.tz_convert("America/Chicago")
    rth_mask = (
        ((local.hour == 7) & (local.minute >= 0)) |
        ((local.hour > 7) & (local.hour < 15)) |
        ((local.hour == 15) & (local.minute == 0))
    )
    prices_rth = prices[rth_mask]

    print(f"\nTotal barras (todas las sesiones): {len(prices):,}")
    print(f"Total barras ventana corregida (7:00-15:00 CT):   {len(prices_rth):,}")
    print(f"Rango: {prices_rth.index.min()} -> {prices_rth.index.max()}")
    print(f"Contratos usados: {sorted(prices_rth['contract'].unique().tolist())}")

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    prices_rth.to_parquet(OUT_PATH)
    print(f"\nGuardado: {OUT_PATH}")
    print("\nNO reemplaza mgc_5min_2y.parquet automaticamente -- comparar WR de ambos antes de decidir cual usar.")


if __name__ == "__main__":
    main()
