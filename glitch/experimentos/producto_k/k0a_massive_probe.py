#!/usr/bin/env python3
"""GLITCH — Parte K, K0(a): profundidad REAL de Massive Futures por producto (SOLO LECTURA; consume llamadas de TU plan). Correr en la Mac o el Pi con MASSIVE_API_KEY
en el entorno (nunca pegarla en el chat). Usa los mismos endpoints y parámetros que ya funcionan en producción (`/futures/v1/contracts`, `/futures/v1/aggs/{ticker}`).
Para cada producto y cada antigüedad de referencia (0, 1, 2, 3, 5, 7, 10 años): ¿hay contratos activos ese día?, ¿devuelve barras de 5 min el contrato más próximo a vencer
en una ventana de 7 días?, primera fecha de negociación del contrato (≈ fecha de lanzamiento del micro) y el texto de error HTTP si el plan no lo permite.
Uso:  MASSIVE_API_KEY=... python3 k0a_massive_probe.py [--products MES,MNQ,...] [--json salida.json] [--sleep 0.25]   (con el plan Basic: --sleep 13 por el límite de 5 llamadas/min)"""
from __future__ import annotations
import argparse, datetime as dt, json, os, re, sys, time
import requests

BASE = "https://api.massive.com"
DEFAULT_PRODUCTS = "MES,MNQ,MYM,M2K,MGC,MCL,M6E,M6B,ZN,ZB,ZC,ES,NQ,YM,RTY,GC,CL,6E"
REF_YEARS = (0, 1, 2, 3, 5, 7, 10)


def _valid(product: str, ticker: str) -> bool:
    return bool(re.match(rf"^{re.escape(product)}[FGHJKMNQUVXZ]\d{{1,2}}$", ticker or ""))


def probe_product(get, product: str, today: dt.date, years=REF_YEARS) -> dict:
    out = {"product": product, "refs": []}
    for y in years:
        ref = today - dt.timedelta(days=int(365.25 * y))
        row = {"years_back": y, "date": ref.isoformat()}
        try:
            st, js = get("/futures/v1/contracts", {"product_code": product, "date": ref.isoformat(), "active": "true", "limit": 250})
            res = [c for c in (js or {}).get("results", []) if (not c.get("type") or c["type"] == "single") and _valid(product, c.get("ticker"))]
            row["contracts_http"] = st; row["n_contracts"] = len(res)
            if res:
                res.sort(key=lambda c: c.get("last_trade_date") or "")
                c0 = res[0]; row["nearest"] = c0.get("ticker"); row["first_trade_date"] = c0.get("first_trade_date"); row["last_trade_date"] = c0.get("last_trade_date")
                end = (ref + dt.timedelta(days=7)).isoformat()
                st2, js2 = get(f"/futures/v1/aggs/{c0['ticker']}", {"resolution": "5min", "window_start_gte": ref.isoformat(), "window_start_lte": end, "sort": "window_start.asc", "limit": 100})
                bars = (js2 or {}).get("results", []) if st2 == 200 else []
                row["aggs_http"] = st2; row["n_bars_5m_in_7d_sample"] = len(bars)
                if st2 != 200:
                    row["aggs_error"] = str(js2)[:120]
        except Exception as e:
            row["error"] = str(e)[:160]
        out["refs"].append(row)
    return out


def probe_resolutions(get, product: str, today: dt.date) -> dict:
    """¿Qué resoluciones devuelve el plan para el contrato más próximo de HOY? (1sec, 1min, 5min) y la edad de la última barra (retraso del dato)."""
    st, js = get("/futures/v1/contracts", {"product_code": product, "date": today.isoformat(), "active": "true", "limit": 250})
    res = sorted([c for c in (js or {}).get("results", []) if (not c.get("type") or c["type"] == "single") and _valid(product, c.get("ticker"))], key=lambda c: c.get("last_trade_date") or "")
    if not res:
        return {"note": "sin contratos activos hoy"}
    t = res[0]["ticker"]; out = {"ticker": t}
    for r in ("1sec", "1min", "5min"):
        st2, js2 = get(f"/futures/v1/aggs/{t}", {"resolution": r, "sort": "window_start.desc", "limit": 1})
        rr = (js2 or {}).get("results", []) if st2 == 200 else []
        age = None
        if rr and rr[0].get("window_start"):
            age = (dt.datetime.now(dt.timezone.utc) - dt.datetime.fromtimestamp(rr[0]["window_start"] / 1e9, tz=dt.timezone.utc)).total_seconds()
        out[r] = {"http": st2, "age_s_of_last_bar": age}
    return out


def main(argv=None, get=None, today=None) -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--products", default=DEFAULT_PRODUCTS); ap.add_argument("--json", default=None); ap.add_argument("--sleep", type=float, default=0.25)
    a = ap.parse_args(argv)
    if get is None:
        key = os.environ.get("MASSIVE_API_KEY") or os.environ.get("POLYGON_API_KEY")
        if not key:
            print("FALTA MASSIVE_API_KEY en el entorno", file=sys.stderr); return 2
        s = requests.Session(); s.headers["Authorization"] = f"Bearer {key}"
        def get(path, params):
            time.sleep(a.sleep)
            r = s.get(BASE + path, params=params, timeout=30)
            try: js = r.json()
            except ValueError: js = {"raw": r.text[:120]}
            return r.status_code, js
    today = today or dt.date.today(); rep = []
    print(f"# K0(a) Massive {today} (solo lectura)")
    for p in [x.strip() for x in a.products.split(",") if x.strip()]:
        r = probe_product(get, p, today); r["resolutions_today"] = probe_resolutions(get, p, today); rep.append(r)
        ok = [x["years_back"] for x in r["refs"] if x.get("n_bars_5m_in_7d_sample")]
        print(f"== {p}: mayor antigüedad con barras de 5 min = {max(ok) if ok else None} años | " + " ".join(f"{x['years_back']}a:{x.get('n_contracts')}c/{x.get('n_bars_5m_in_7d_sample')}b/{x.get('aggs_http', x.get('contracts_http'))}" for x in r["refs"]) +
              f" | primer contrato hist.: {next((x.get('first_trade_date') for x in reversed(r['refs']) if x.get('first_trade_date')), None)} | hoy: {r['resolutions_today']}")
    if a.json: json.dump(rep, open(a.json, "w"), indent=2, default=str)
    return 0


if __name__ == "__main__":
    sys.exit(main())
