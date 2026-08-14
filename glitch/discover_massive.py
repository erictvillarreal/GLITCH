"""
Glitch — Descubrimiento de API de Massive (Futures, SDK nuevo)
==================================================================
Massive tiene un SDK/API separado para futuros (no el `polygon-api-client`
viejo que usa data/loader.py). Este script solo EXPLORA: encuentra el
ticker correcto de MES vigente (o el contrato continuo si existe) antes
de pedir 2 anios de datos de verdad.

Requiere: export POLYGON_API_KEY="tu-key-NUEVA-despues-de-rotarla"

Uso:
    pip install massive
    python scripts/discover_massive.py
"""
import os, sys, json

API_KEY = os.environ.get("POLYGON_API_KEY", "")
if not API_KEY:
    print("ERROR: falta POLYGON_API_KEY")
    sys.exit(1)

try:
    from massive import RESTClient
except ImportError:
    print("Falta el paquete nuevo. Corre: pip install massive")
    sys.exit(1)

client = RESTClient(API_KEY)

print("=== 1. Contratos MES listados (para ver el formato real de ticker) ===")
try:
    contracts = list(client.list_futures_contracts(product_code="MES", limit=10))
    for c in contracts:
        print(c)
except Exception as e:
    print(f"Error en list_futures_contracts: {e}")

print("\n=== 2. Productos disponibles que contengan 'MES' (por si el codigo cambia) ===")
try:
    products = list(client.list_futures_products(search="MES", limit=10))
    for p in products:
        print(p)
except Exception as e:
    print(f"Error en list_futures_products: {e}")

print("\n=== 3. Intento de aggregates con el primer contrato encontrado en el paso 1 ===")
try:
    if contracts:
        ticker = contracts[0].ticker if hasattr(contracts[0], "ticker") else contracts[0].get("ticker")
        print(f"Probando ticker: {ticker}")
        aggs = list(client.list_futures_aggregates(
            ticker=ticker, resolution="5min",
            window_start_gte="2026-07-01", window_start_lte="2026-08-01",
            sort="window_start.asc", limit=10,
        ))
        print(f"Barras devueltas: {len(aggs)}")
        for a in aggs[:3]:
            print(a)
    else:
        print("No hay contratos del paso 1 para probar.")
except Exception as e:
    print(f"Error en list_futures_aggregates: {e}")
