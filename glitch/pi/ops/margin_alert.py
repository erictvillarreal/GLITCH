#!/usr/bin/env python3
"""GLITCH -- Alerta de margen (T3, 12-oct-2026). SOLO LECTURA: autentica en ProjectX, lee saldo, posiciones y la ultima barra, y avisa por Telegram si el cojin del MLL baja del umbral.
Corre EN EL PI (cron cada 5 min; decide solo la ventana horaria en CT). No coloca ni cancela ordenes. NEEDS HUMAN REVIEW.
  Practice:  alerta si saldo + no realizado - piso < $1,500.
  Combine:   alerta por exposicion de liquidacion: distancia en ticks hasta el precio de liquidacion del MLL (amarillo <= 20, rojo <= 10).
El PISO del MLL no lo da la API (NO VERIFICADO): se lleva con un libro propio de maximos de cierre (--ledger-file); --floor-override fija el piso a mano.
Uso: python3 pi/ops/margin_alert.py --kind combine --account-id 28197705 --product MES --start-balance 50000 --mll 2000 [--dry-run]"""
from __future__ import annotations
import argparse, datetime as dt, json, os, sys
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from monitoring import margin as M                       # noqa: E402
from monitoring.notify import parse_env_file, send, PREFIX  # noqa: E402

CT = ZoneInfo("America/Chicago")
WINDOW_START, WINDOW_END = 8 * 60 + 30, 15 * 60 + 10      # minutos CT; 15:10 = cierre de ventana, se actualiza el libro EOD


def in_window(now_ct: dt.datetime) -> bool:
    return now_ct.weekday() < 5 and WINDOW_START <= now_ct.hour * 60 + now_ct.minute <= WINDOW_END


def load_json(path: str) -> dict:
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return {}


def save_json(path: str, data: dict) -> None:
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(data, f)
    os.replace(tmp, path)


def unrealized_usd(positions: list, last_price: float, tick: float, tick_value: float) -> tuple:
    """(no realizado USD, contratos abiertos, lado) a partir de Position/searchOpen: type 1=Long, 2=Short; size; averagePrice."""
    total = 0.0; size_tot = 0; side = 0
    for p in positions:
        sz = int(p.get("size") or 0)
        if sz <= 0:
            continue
        sd = 1 if p.get("type") == 1 else -1
        total += (last_price - float(p["averagePrice"])) * sd * tick_value / tick * sz
        size_tot += sz; side = sd
    return total, size_tot, side


def main(argv=None, client=None) -> int:
    ap = argparse.ArgumentParser(description="Alerta de margen (solo lectura)")
    ap.add_argument("--kind", choices=("practice", "combine"), required=True)
    ap.add_argument("--account-id", type=int, required=True)
    ap.add_argument("--product", default="MES")
    ap.add_argument("--start-balance", type=float, required=True)
    ap.add_argument("--mll", type=float, required=True, help="distancia del MLL en USD (50K Combine: 2000; Practice 150K: ver nota NO VERIFICADO)")
    ap.add_argument("--floor-override", type=float, default=None)
    ap.add_argument("--env-file", default=os.path.expanduser("~/.glitch_pi.env"))
    ap.add_argument("--state-file", default=os.path.expanduser("~/.glitch_margin_state.json"))
    ap.add_argument("--ledger-file", default=os.path.expanduser("~/.glitch_eod_ledger.json"))
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--force-window", action="store_true", help="ignora la ventana horaria (pruebas)")
    args = ap.parse_args(argv)

    now = dt.datetime.now(CT)
    if not (in_window(now) or args.force_window):
        return 0
    env = parse_env_file(args.env_file)
    for k, v in env.items():
        os.environ.setdefault(k, v)
    if client is None:
        from brokers.projectx import ProjectXClient, ProjectXCredentials   # noqa: E402 (venv del ejecutor)
        client = ProjectXClient(ProjectXCredentials.from_env(), verbose=False)
    from strategies.geometry_pure import CANDIDATES                         # noqa: E402
    spec = CANDIDATES[args.product].spec

    acct = next((a for a in client.get_accounts(only_active=True) if a.get("id") == args.account_id), None)
    if acct is None:
        print(f"margin_alert: la cuenta {args.account_id} no esta entre las activas (reiniciada o con otro id?)", file=sys.stderr)
        return 3
    balance = float(acct.get("balance", 0.0))
    ledger = load_json(args.ledger_file)
    if now.hour * 60 + now.minute >= 15 * 60:        # despues del cierre: el saldo es de cierre (EOD)
        ledger = M.update_eod_ledger(ledger, balance, now.date().isoformat(), args.start_balance)
        if not args.dry_run:
            save_json(args.ledger_file, ledger)
    eod_high = ledger.get("eod_high", args.start_balance)
    floor = args.floor_override if args.floor_override is not None else M.mll_floor(args.kind, eod_high, args.start_balance, args.mll)

    positions = client.get_positions(args.account_id)
    unreal, nc, side = 0.0, 0, 0
    if positions:
        cid = positions[0].get("contractId")
        bars = client.get_recent_bars(cid, minutes_back=15, live=False)
        if bars:
            unreal, nc, side = unrealized_usd(positions, float(bars[-1]["close"]), spec.tick_size, spec.tick_value_usd)
    cushion = M.cushion_usd(balance, unreal, floor)
    state = load_json(args.state_file)
    lvl, action, new_state = M.decide(args.kind, cushion, nc, spec.tick_value_usd, now.date().isoformat(), now.timestamp(), state)
    ticks = M.liquidation_ticks(cushion, nc, spec.tick_value_usd)
    print(f"margin_alert: kind={args.kind} nivel={lvl} accion={action} saldo={balance:,.0f} piso={floor:,.0f} no_realizado={unreal:,.0f} cojin={cushion:,.0f} "
          f"contratos={nc} ticks_a_liquidacion={'n/a' if ticks is None else f'{ticks:.1f}'}")
    if action == "none" or args.dry_run:
        return 0
    token, chat = env.get("TELEGRAM_BOT_TOKEN"), env.get("TELEGRAM_CHAT_ID")
    if not token or not chat:
        print("margin_alert: faltan TELEGRAM_BOT_TOKEN/TELEGRAM_CHAT_ID", file=sys.stderr)
        return 2
    label = {"alert": "ALERTA", "escalate": "ESCALA", "recovered": "RECUPERADO"}[action]
    body = (f"{PREFIX} | MARGEN {args.kind.upper()} {label} ({lvl.upper()})\nCuenta {args.account_id} | saldo ${balance:,.0f} | piso MLL ${floor:,.0f} (estimado) | "
            f"no realizado ${unreal:,.0f}\nCojin ${cushion:,.0f}" + (f" | {nc} contratos a {ticks:.1f} ticks de la liquidacion" if ticks is not None and nc else ""))
    if send(token, chat, body):
        save_json(args.state_file, new_state)       # solo se marca como avisado si el Telegram SE ENVIO
    return 0


if __name__ == "__main__":
    sys.exit(main())
