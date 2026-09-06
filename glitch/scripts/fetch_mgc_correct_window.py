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

ACTUALIZADO (07-sep-2026): el filesystem de Railway es efímero (misma
lección de siempre) -- mover el parquet completo de vuelta a esta
sesión no es práctico. Este script ahora imprime un RESUMEN
AUTOSUFICIENTE (conteo de filas, rango de fechas, perfil de volumen
por hora, Y el WR condicional recalculado con la ventana corregida --
comparable directamente contra el 49.97% ya validado) para poder
decidir el siguiente paso leyendo el log de Railway, sin necesitar el
archivo de vuelta. También intenta guardar ese mismo resumen (JSON
pequeño, no el parquet binario) en el Gist compartido ya usado para
persistencia (`execution/gist_store.py`) bajo la clave
"mgc_window_validation_summary.json" -- un parquet de varios MB no
tiene buen encaje en un Gist de texto, pero el resumen estadístico sí,
y es lo único que realmente hace falta para decidir. Si faltan las
credenciales del Gist o falla la subida, el script sigue funcionando
igual -- el log impreso es la fuente de verdad primaria, el Gist es
solo una comodidad adicional.

Una vez corrido, ANTES de usar este dataset para el scheduler:
  1. Leer el resumen impreso (o el Gist) -- ya incluye el WR
     condicional recalculado, no hace falta correr un script aparte
     para eso.
  2. Comparar el WR viejo (49.97%) vs nuevo explícitamente antes de
     descartar el dataset anterior -- documentar la diferencia, no
     solo asumir que "más datos es mejor" sin medirlo.
"""
from __future__ import annotations
import os, re, sys, json, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd
import requests

from scripts.camino_b_grid import _label_fixed_ticks
from strategies.geometry_pure import SPECS

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
    print(f"\nGuardado localmente: {OUT_PATH} (filesystem efimero de Railway -- "
          f"no depender de recuperar este archivo, ver resumen abajo)")

    summary = build_summary(prices_rth)
    print("\n" + "=" * 100)
    print("RESUMEN AUTOSUFICIENTE -- suficiente para decidir el siguiente paso sin mover el parquet")
    print("=" * 100)
    print(json.dumps(summary, indent=2, default=str))

    persist_summary_to_gist(summary)


def build_summary(prices_rth: pd.DataFrame) -> dict:
    """Conteo/rango + perfil de volumen por hora + WR condicional
    recalculado con la ventana corregida -- todo lo necesario para
    decidir sin el parquet completo de vuelta."""
    local = prices_rth.copy()
    local.index = local.index.tz_convert("America/Chicago")

    vol_by_hour = local.groupby(local.index.hour)["volume"].mean()
    total_vol = float(local["volume"].sum())
    first_hour_vol = float(local[local.index.hour == 7]["volume"].sum())

    wr = compute_wr_conditional(prices_rth)

    return {
        "n_rows": int(len(prices_rth)),
        "date_range": [str(prices_rth.index.min()), str(prices_rth.index.max())],
        "contracts": sorted(prices_rth["contract"].unique().tolist()),
        "avg_volume_by_hour_ct": {int(h): round(float(v), 1) for h, v in vol_by_hour.items()},
        "volume_pct_hour_7_of_total": round(first_hour_vol / total_vol, 4) if total_vol else None,
        "wr_conditional_corrected_window": wr,
        "wr_conditional_old_window_reference": 0.4997,  # ya validado, ver GLITCH_RESEARCH_LOG.md 07-sep-2026
    }


def compute_wr_conditional(prices_rth: pd.DataFrame) -> dict:
    """Mismo calculo (SL=TP=364 ticks, max_holding=100, alternando sin
    señal) ya usado en validate_mgc_wr_empirical.py -- reproducido aqui
    para no depender de una segunda corrida de script separada."""
    tick_size = SPECS["MGC"].tick_size
    sl_pts = tp_pts = 364 * tick_size
    max_holding = 100

    n = len(prices_rth)
    signal_indices = np.arange(0, n - max_holding - 1, 1)
    longs = signal_indices[np.arange(len(signal_indices)) % 2 == 0]
    shorts = signal_indices[np.arange(len(signal_indices)) % 2 == 1]

    ll = _label_fixed_ticks(prices_rth, longs, tp_pts, sl_pts, max_holding, side=1, win_first=False)
    ls = _label_fixed_ticks(prices_rth, shorts, tp_pts, sl_pts, max_holding, side=-1, win_first=False)
    all_labels = np.concatenate([ll, ls])
    n_tp, n_sl, n_time = int((all_labels == 1).sum()), int((all_labels == -1).sum()), int((all_labels == 0).sum())
    total = len(all_labels)

    return {
        "n_trades": total,
        "tp_pct": round(n_tp / total, 4) if total else None,
        "sl_pct": round(n_sl / total, 4) if total else None,
        "time_exit_pct": round(n_time / total, 4) if total else None,
        "wr_conditional": round(n_tp / (n_tp + n_sl), 4) if (n_tp + n_sl) else None,
        "wr_long": round((ll == 1).sum() / ((ll == 1).sum() + (ll == -1).sum()), 4) if len(ll) else None,
        "wr_short": round((ls == 1).sum() / ((ls == 1).sum() + (ls == -1).sum()), 4) if len(ls) else None,
    }


def persist_summary_to_gist(summary: dict) -> None:
    """Sube el resumen (JSON pequeño) al Gist compartido de persistencia
    -- NO el parquet binario (mal encaje en un Gist de texto). Clave
    deliberadamente distinta de los logs de geometry_mes/combo2d. Si
    faltan credenciales o falla la subida, se loguea y se sigue -- el
    log impreso arriba ya es la fuente de verdad primaria."""
    try:
        from execution.gist_store import save_log
        save_log("mgc_window_validation_summary.json", [summary])
        print("\nResumen tambien guardado en el Gist compartido "
              "(clave: mgc_window_validation_summary.json) -- recuperable sin este shell.")
    except Exception as e:
        print(f"\n[warn] No se pudo guardar el resumen en el Gist ({e}) -- "
              "el log impreso arriba sigue siendo suficiente para decidir el siguiente paso.")


if __name__ == "__main__":
    main()
