#!/usr/bin/env python3
"""GLITCH -- Recordatorios con fecha por Telegram (T3, 12-oct-2026). Corre en RAILWAY, una vez al dia (cron 8:00 CT dias habiles). Lee el Gist, decide cuales recordatorios tocan hoy
(monitoring/reminders.py), los envia y guarda los ids enviados en `reminders_sent.json` del Gist SOLO si el envio funciono (idempotente si el cron corre dos veces).
Uso: python scheduler/reminders_job.py [--product MES] [--dry-run]. NEEDS HUMAN REVIEW."""
from __future__ import annotations
import argparse, datetime as dt, os, sys
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from monitoring.notify import send, PREFIX              # noqa: E402
from monitoring.reminders import due_reminders, render  # noqa: E402
from monitoring.weekly import summarize_attempts, pass_test, semaforo_text  # noqa: E402

CT = ZoneInfo("America/Chicago")


def main(argv=None, store=None, today: dt.date = None, sender=send, now_ct: dt.datetime = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--product", default="MES")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--any-hour", action="store_true", help="no exige que sean las 8:00 CT (el cron de Railway es UTC: se programa a las 13:00 y 14:00 UTC y solo una coincide con las 8 CT segun el horario de verano)")
    args = ap.parse_args(argv)
    now_ct = now_ct or dt.datetime.now(CT)
    if not args.any_hour and now_ct.hour != 8:
        return 0
    today = today or now_ct.date()
    if today.weekday() >= 5:
        return 0
    if store is None:
        from execution import gist_store as store   # noqa: E402
    p = args.product.lower()
    geometry = store.load_log(f"geometry_{p}_log.json")
    friction = store.load_state(f"friction_{p}_log.json").get("entries", [])
    sent = store.load_state("reminders_sent.json").get("ids", [])
    s = summarize_attempts(geometry)
    ctx = {"attempts_started": s["started"], "attempts_resolved": s["resolved"],
           "semaforo_text": semaforo_text([r for r in friction if r.get("date", "") >= (today - dt.timedelta(days=28)).isoformat()]),
           "pass_test_text": pass_test(s["passed"], s["resolved"])["text"]}
    due = due_reminders(today, sent, ctx)
    if not due:
        return 0
    token, chat = os.environ.get("TELEGRAM_BOT_TOKEN"), os.environ.get("TELEGRAM_CHAT_ID")
    sent_now = []
    for rid, text in due:
        msg = f"{PREFIX} | RECORDATORIO {today.isoformat()}\n{render(text, ctx)}"
        print(msg)
        if args.dry_run:
            continue
        if token and chat and sender(token, chat, msg):
            sent_now.append(rid)
    if sent_now and not args.dry_run:
        store.save_state("reminders_sent.json", {"ids": list(sent) + sent_now})
    return 0


if __name__ == "__main__":
    sys.exit(main())
