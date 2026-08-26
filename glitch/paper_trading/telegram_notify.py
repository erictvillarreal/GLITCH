"""
Glitch — Telegram Notifier
============================
Envio simple de mensajes a un chat de Telegram via el Bot API (HTTPS).
No requiere librerias externas mas alla de `requests`.

SETUP (hazlo tu, 5 minutos):
  1. Habla con @BotFather en Telegram -> /newbot -> copia el token.
  2. Agrega el bot a tu chat/canal, o hazle /start en DM.
  3. Para obtener tu chat_id: manda un mensaje al bot y visita
     https://api.telegram.org/bot<TOKEN>/getUpdates
     busca "chat":{"id": ...}
  4. Exporta las variables de entorno:
       export GLITCH_TG_TOKEN="123456:ABC-DEF..."
       export GLITCH_TG_CHAT_ID="-1001234567890"   # o tu user id
"""
from __future__ import annotations
import os
import requests

TOKEN = os.environ.get("GLITCH_TG_TOKEN", "")
CHAT_ID = os.environ.get("GLITCH_TG_CHAT_ID", "")

API_BASE = "https://api.telegram.org/bot{token}/{method}"


def _check_config():
    if not TOKEN or not CHAT_ID:
        raise RuntimeError(
            "Faltan GLITCH_TG_TOKEN / GLITCH_TG_CHAT_ID en variables de entorno. "
            "Ver docstring de este archivo para el setup de 5 minutos."
        )


def send_message(text: str, parse_mode: str = "Markdown") -> int:
    """Envia un mensaje y devuelve el message_id (para editarlo despues)."""
    _check_config()
    url = API_BASE.format(token=TOKEN, method="sendMessage")
    r = requests.post(url, json={"chat_id": CHAT_ID, "text": text, "parse_mode": parse_mode}, timeout=10)
    r.raise_for_status()
    return r.json()["result"]["message_id"]


def edit_message(message_id: int, text: str, parse_mode: str = "Markdown"):
    _check_config()
    url = API_BASE.format(token=TOKEN, method="editMessageText")
    r = requests.post(url, json={
        "chat_id": CHAT_ID, "message_id": message_id,
        "text": text, "parse_mode": parse_mode,
    }, timeout=10)
    r.raise_for_status()


def notify_signal(strategy: str, symbol: str, side: int, entry: float, stop: float,
                   target: float, contracts: int) -> int:
    dir_txt = "🟢 LONG" if side == 1 else "🔴 SHORT"
    risk = abs(entry - stop)
    reward = abs(target - entry)
    rr = round(reward / risk, 2) if risk > 0 else 0
    text = (
        f"*GLITCH — Señal Paper*\n"
        f"Estrategia: `{strategy}`\n"
        f"{dir_txt}  {symbol}  x{contracts}\n"
        f"Entrada: `{entry:.2f}`\n"
        f"Stop: `{stop:.2f}`  |  Target: `{target:.2f}`\n"
        f"R:R ≈ {rr}"
    )
    return send_message(text)


def notify_close(message_id: int, strategy: str, symbol: str, status: str, pnl_usd: float):
    emoji = {"win": "✅", "loss": "❌", "timeout": "⏱️"}.get(status, "•")
    text = (
        f"{emoji} *{strategy}* {symbol} — {status.upper()}\n"
        f"PnL: `${pnl_usd:+,.2f}`"
    )
    try:
        edit_message(message_id, text)
    except Exception:
        send_message(text)  # fallback si no se pudo editar


def notify_daily_digest(stats: dict, sample_target: int):
    n = stats["n_trades"]
    pct = min(100, round(100 * n / sample_target, 1)) if sample_target else 0
    text = (
        f"*GLITCH — Resumen diario*\n"
        f"Trades acumulados: {n} / {sample_target} ({pct}%)\n"
        f"Dias: {stats['n_days']}\n"
        f"WR: {stats['win_rate']}\n"
        f"Avg win: ${stats['avg_win']}  |  Avg loss: ${stats['avg_loss']}\n"
        f"EV/trade: ${stats['ev_per_trade']}"
    )
    send_message(text)
