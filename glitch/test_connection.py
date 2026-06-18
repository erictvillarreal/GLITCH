"""
Test de conexión a Tradovate API.
Edita .tradovate_creds.json con tu email y password primero.
"""
import sys
sys.path.insert(0, '.')

from brokers.tradovate import TradovateCredentials, TradovateClient, TradovateEnv

print("Loading credentials...")
try:
    creds = TradovateCredentials.from_file(".tradovate_creds.json")
    print(f"  Name: {creds.name}")
    print(f"  CID:  {creds.cid}")
    print(f"  DeviceId: {creds.device_id}")
except Exception as e:
    print(f"  Error: {e}")
    sys.exit(1)

print("\nConnecting to DEMO...")
try:
    client = TradovateClient(creds, TradovateEnv.DEMO)
    token  = client.authenticate()
    print(f"  Token expires in: {token.seconds_until_expiry/60:.0f} min")
    print(f"  User ID: {token.user_id}")
except Exception as e:
    print(f"  Auth failed: {e}")
    sys.exit(1)

print("\nFetching accounts...")
try:
    accounts = client.get_accounts()
    for a in accounts:
        print(f"  Account: {a.get('name')} | ID: {a.get('id')} | "
              f"Balance: ${a.get('balance', 0):,.0f}")
    if accounts:
        account_id = accounts[0]['id']
        print(f"\nUsing account: {account_id}")
        status = client.check_combine_status(account_id)
        print(f"  Equity:      ${status['total_equity']:,.2f}")
        print(f"  Daily PnL:   ${status['realized_pnl']:+,.2f}")
except Exception as e:
    print(f"  Error: {e}")

print("\nConnection test complete.")
print("Next: python run_glitch.py --env demo --account ACCOUNT_ID --dry-run")
