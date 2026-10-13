#!/usr/bin/env python3
"""GLITCH -- Resumen semanal por Telegram (T3, 12-oct-2026). Corre en RAILWAY (cron lunes 8:00 CT = 13:00 UTC en horario de verano; ajustar en invierno). Solo lee el Gist
(geometry_<producto>_log.json y friction_<producto>_log.json) y manda UN mensaje: Combines, prueba de pase, semaforo de friccion y compuerta de la 2.a cuenta. No habla con ProjectX ni
con ningun broker (Topstep exige ordenes desde un dispositivo personal; este job no transmite ordenes). Variables: GIST_ID, GITHUB_GIST_TOKEN, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID.
Uso: python scheduler/weekly_summary.py [--product MES] [--force] [--dry-run]. NEEDS HUMAN REVIEW."""
from __future__ import annotations
import argparse, datetime as dt, os, sys
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from monitoring.notify import send                     # noqa: E402
from monitoring.weekly import weekly_message           # noqa: E402

CT = ZoneInfo("America/Chicago")
WINDOW_DAYS = 28


def main(argv=None, store=None, today: dt.date = None, sender=send, now_ct: dt.datetime = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--product", default="MES")
    ap.add_argument("--force", action="store_true", help="envia aunque no sea lunes")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--any-hour", action="store_true", help="no exige que sean las 8:00 CT (el cron de Railway es UTC: se programa a las 13:00 y 14:00 UTC y solo una coincide con las 8 CT segun el horario de verano)")
    args = ap.parse_args(argv)
    now_ct = now_ct or dt.datetime.now(CT)
    if not args.any_hour and now_ct.hour != 8:
        return 0
    today = today or now_ct.date()
    if today.weekday() != 0 and not args.force:
        return 0
    if store is None:
        from execution import gist_store as store   # noqa: E402 -- exige GIST_ID/GITHUB_GIST_TOKEN
    p = args.product.lower()
    geometry = store.load_log(f"geometry_{p}_log.json")
    friction = store.load_state(f"friction_{p}_log.json").get("entries", [])
    cutoff = (today - dt.timedelta(days=WINDOW_DAYS)).isoformat()
    window = [r for r in friction if r.get("date", "") >= cutoff]
    costs = store.load_state("glitch_costs.json") or None
    msg = weekly_message(today, geometry, window, costs)
    print(msg)
    if args.dry_run:
        return 0
    token, chat = os.environ.get("TELEGRAM_BOT_TOKEN"), os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat:
        print("weekly_summary: faltan TELEGRAM_BOT_TOKEN/TELEGRAM_CHAT_ID", file=sys.stderr)
        return 2
    return 0 if sender(token, chat, msg) else 1


if __name__ == "__main__":
    sys.exit(main())
