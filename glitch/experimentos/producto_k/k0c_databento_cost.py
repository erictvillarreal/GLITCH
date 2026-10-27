#!/usr/bin/env python3
"""GLITCH — Parte K, K0(c): costo EXACTO de bajar barras de 1 min de CME Globex (GLBX.MDP3) en Databento. Solo llama a `metadata.get_cost` y `get_dataset_range`
(no descargan datos; no consumen créditos). Correr en la Mac con DATABENTO_API_KEY en el entorno (nunca en el chat) y `pip install databento`.
Uso:  DATABENTO_API_KEY=... python3 k0c_databento_cost.py [--start 2010-06-06] [--symbols ES,NQ,YM,RTY,GC,CL,6E,ZN,MES,MNQ,MYM,M2K,MGC,MCL,M6E]"""
from __future__ import annotations
import argparse, datetime as dt, os, sys

DEFAULT = "ES,NQ,YM,RTY,GC,CL,6E,ZN,MES,MNQ,MYM,M2K,MGC,MCL,M6E"


def costs(client, symbols, start, end, schema="ohlcv-1m", dataset="GLBX.MDP3", log=print):
    rows = []
    for s in symbols:
        sym = f"{s}.v.0"                                   # continuo por volumen (front month por volumen: la regla que exige Topstep)
        try:
            usd = client.metadata.get_cost(dataset=dataset, symbols=[sym], schema=schema, stype_in="continuous", start=start, end=end)
            n = client.metadata.get_record_count(dataset=dataset, symbols=[sym], schema=schema, stype_in="continuous", start=start, end=end)
            sz = client.metadata.get_billable_size(dataset=dataset, symbols=[sym], schema=schema, stype_in="continuous", start=start, end=end)
            rows.append({"symbol": sym, "usd": float(usd), "records": int(n), "bytes": int(sz)})
        except Exception as e:
            rows.append({"symbol": sym, "error": str(e)[:160]})
        log(rows[-1])
    return rows


def main(argv=None, client=None) -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--start", default="2010-06-06"); ap.add_argument("--symbols", default=DEFAULT)
    a = ap.parse_args(argv)
    if client is None:
        key = os.environ.get("DATABENTO_API_KEY")
        if not key:
            print("FALTA DATABENTO_API_KEY en el entorno", file=sys.stderr); return 2
        import databento as db
        client = db.Historical(key)
    end = dt.date.today().isoformat()
    try:
        print("rango del dataset:", client.metadata.get_dataset_range(dataset="GLBX.MDP3"))
    except Exception as e:
        print("get_dataset_range falló:", str(e)[:120])
    rows = costs(client, [s.strip() for s in a.symbols.split(",") if s.strip()], a.start, end)
    ok = [r for r in rows if "usd" in r]
    print(f"# total estimado ohlcv-1m {a.start} → {end}: ${sum(r['usd'] for r in ok):,.2f} para {len(ok)} símbolos; {sum(r['records'] for r in ok):,} registros; {sum(r['bytes'] for r in ok) / 1e9:.2f} GB facturables")
    return 0


if __name__ == "__main__":
    sys.exit(main())
