"""
Glitch — Fetch 2 años de MES 5min (contrato continuo, front-month splice)
==========================================================================
Descarga barras 5min de los contratos trimestrales de MES (H/M/U/Z) que
cubrieron los ultimos ~2 anios, y las empalma en una sola serie continua
SIN back-adjustment (splice crudo en la fecha de roll).

Metodologia de descubrimiento de contratos (ver CLAUDE.md, root del repo Kito):
  - `date=<point-in-time>` para listar contratos activos ese dia
  - excluir spreads (tickers con "-")
  - el "front month" en cada fecha = el contrato NO-spread con last_trade_date
    mas cercana (>= fecha de referencia)

Roll: 8 dias calendario antes del last_trade_date de cada contrato (heuristica
simple — evita los ultimos dias de baja liquidez antes de expiracion, no es
back-adjustment de precio real).

LIMITACION CONOCIDA: esto es splice crudo, no back-adjusted. Los saltos de
precio en el punto de roll son reales (spread entre contratos) y pueden
introducir un salto discontinuo pequeno en la serie. Aceptable para un
diagnostico de barras ambiguas / walk-forward, NO para PnL de precision.

Uso:
    export MASSIVE_API_KEY="..."
    python scripts/fetch_mes_2y.py
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

# REFACTOR (25-ago-2026): se cambio de la SDK `massive` (RESTClient +
# iteradores con _paginate) a requests directo. La SDK colgaba
# indefinidamente en list_futures_contracts para algunos productos
# (confirmado con MBT) sin error visible -- probablemente pagina de mas
# cuando la respuesta trae muchas filas "combo" (spreads). requests
# directo con limite de paginas explicito es mas lento de escribir pero
# no se cuelga en silencio.
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
        params = {}  # next_url ya trae los params codificados
    return out

PRODUCT = sys.argv[1] if len(sys.argv) > 1 else "MES"
END_DATE = dt.date.today()
START_DATE = END_DATE - dt.timedelta(days=730)
ROLL_BUFFER_DAYS = 8
OUT_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         "data_cache", f"{PRODUCT.lower()}_5min_2y.parquet")

# Mensual, no trimestral -- productos como GC/MGC (oro) o ZC (agricolas)
# pueden tener ciclos de vencimiento mas frecuentes que MES (H/M/U/Z), asi
# que un snapshot trimestral se saltaria contratos intermedios.
REF_DATES = pd.date_range(START_DATE, END_DATE, freq="MS").tolist()
if not REF_DATES or REF_DATES[0] > pd.Timestamp(START_DATE):
    REF_DATES = [pd.Timestamp(START_DATE)] + REF_DATES
REF_DATES.append(pd.Timestamp(END_DATE))

# ticker outright valido: PRODUCT + 1 letra de mes (F,G,H,J,K,M,N,Q,U,V,X,Z)
# + 1-2 digitos de año. Rechaza spreads/combos y formatos raros (ej. el
# "ZC:CF U6Z6H7K7" que devolvio el descubrimiento inicial para ZC).
_TICKER_RE_CACHE: dict[str, "re.Pattern"] = {}
def _valid_outright_ticker(product: str, ticker: str) -> bool:
    if product not in _TICKER_RE_CACHE:
        _TICKER_RE_CACHE[product] = re.compile(rf"^{re.escape(product)}[FGHJKMNQUVXZ]\d{{1,2}}$")
    return bool(_TICKER_RE_CACHE[product].match(ticker))


def discover_contracts() -> pd.DataFrame:
    """Point-in-time snapshots -> roster de contratos outright (sin spreads)."""
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
                continue  # excluir combos/spreads explicitamente
            ticker = c.get("ticker")
            if not ticker or not _valid_outright_ticker(PRODUCT, ticker):
                continue
            ltd = c.get("last_trade_date")
            ftd = c.get("first_trade_date")
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
    df = df.sort_values("last_trade_date").reset_index(drop=True)
    return df


def build_roll_schedule(contracts: pd.DataFrame) -> list[dict]:
    """Asigna a cada contrato una ventana [seg_start, seg_end) sin solape."""
    contracts = contracts[
        (contracts["last_trade_date"] >= pd.Timestamp(START_DATE)) &
        (contracts["first_trade_date"] <= pd.Timestamp(END_DATE))
    ].sort_values("last_trade_date").reset_index(drop=True)

    schedule = []
    seg_start = pd.Timestamp(START_DATE)
    for i, row in contracts.iterrows():
        roll_date = row["last_trade_date"] - pd.Timedelta(days=ROLL_BUFFER_DAYS)
        seg_end = min(roll_date, pd.Timestamp(END_DATE))
        if seg_end <= seg_start:
            continue
        schedule.append({
            "ticker": row["ticker"],
            "start": seg_start.date().isoformat(),
            "end": seg_end.date().isoformat(),
        })
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
    print(f"\n{len(contracts)} contratos outright encontrados:")
    print(contracts.to_string(index=False))

    schedule = build_roll_schedule(contracts)
    print(f"\nSchedule de roll ({len(schedule)} segmentos):")
    for s in schedule:
        print(f"  {s['ticker']:8s} {s['start']} -> {s['end']}")

    all_frames = []
    for s in schedule:
        print(f"\nDescargando {s['ticker']} {s['start']} -> {s['end']}...")
        seg = fetch_segment(s["ticker"], s["start"], s["end"])
        print(f"  {len(seg)} barras")
        if not seg.empty:
            all_frames.append(seg)

    if not all_frames:
        print("Sin datos descargados. Abortando.")
        sys.exit(1)

    prices = pd.concat(all_frames, ignore_index=True).drop_duplicates(subset="ts")
    prices = prices.set_index("ts").sort_index()

    # Filtrar a RTH: 8:30-15:00 CT (9:30-16:00 ET), estandar para indices
    local = prices.index.tz_convert("America/Chicago")
    rth_mask = (
        ((local.hour == 8) & (local.minute >= 30)) |
        ((local.hour > 8) & (local.hour < 15)) |
        ((local.hour == 15) & (local.minute == 0))
    )
    prices_rth = prices[rth_mask]

    print(f"\nTotal barras (todas las sesiones): {len(prices):,}")
    print(f"Total barras RTH (8:30-15:00 CT):   {len(prices_rth):,}")
    print(f"Rango: {prices_rth.index.min()} -> {prices_rth.index.max()}")
    print(f"Contratos usados: {sorted(prices_rth['contract'].unique().tolist())}")

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    prices_rth.to_parquet(OUT_PATH)
    print(f"\nGuardado: {OUT_PATH}")


if __name__ == "__main__":
    main()
