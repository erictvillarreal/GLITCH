import os, sys, itertools, datetime

API_KEY = os.environ.get("POLYGON_API_KEY", "")
if not API_KEY:
    print("ERROR: falta POLYGON_API_KEY")
    sys.exit(1)

from massive import RESTClient
client = RESTClient(API_KEY)

today = datetime.date.today().isoformat()
print(f"=== Contratos MES con last_trade_date >= hoy ({today}) ===")
contracts = []
try:
    gen = client.list_futures_contracts(product_code="MES", last_trade_date_gte=today, limit=20)
    for c in itertools.islice(gen, 20):
        print(c)
        contracts.append(c)
except Exception as e:
    print(f"Error: {e}")

print(f"\nTotal encontrados: {len(contracts)}")

print("\n=== Aggregates con el primero (deberia ser el front month o cercano) ===")
try:
    if contracts:
        contracts.sort(key=lambda c: c.last_trade_date if hasattr(c, "last_trade_date") else c.get("last_trade_date"))
        ticker = contracts[0].ticker if hasattr(contracts[0], "ticker") else contracts[0].get("ticker")
        print(f"Ticker elegido: {ticker}")
        gen2 = client.list_futures_aggregates(
            ticker=ticker, resolution="5min",
            window_start_gte="2026-08-01", window_start_lte="2026-08-11",
            sort="window_start.asc",
        )
        for a in itertools.islice(gen2, 5):
            print(a)
    else:
        print("Sin contratos.")
except Exception as e:
    print(f"Error: {e}")
