"""Silencio de Telegram SOLO para el paper del scheduler de MES (NEEDS HUMAN REVIEW, no toca logica de capital).

Motivo (20-nov-2026): el scheduler de MES corre en paper (DRY_RUN=true) para acumular el historial en el Gist, pero sus avisos de rutina
(INICIO DE DIA, OPEN, CLOSE) se confunden con los de produccion. Con GLITCH_PAPER_SILENT=true esos avisos van solo al log.

Reglas (funciones puras, sin red):
 · El silencio exige las DOS condiciones: DRY_RUN=true Y GLITCH_PAPER_SILENT=true. Con DRY_RUN=false jamas se silencia nada.
 · Aunque este activo, los avisos de falla (STATUS: ERROR / ALERTA) siguen llegando por Telegram: si el paper deja de guardar el historial hay que enterarse.
 · Por defecto (variable ausente o cualquier otro valor) el comportamiento es identico al actual.
No modifica scheduler/telegram_bot.py, que comparten el Pi y el scheduler de MGC."""
AUDIBLE_MARKERS = ("STATUS: ERROR", "STATUS: ALERTA", "STATUS: BLOCKED")


def paper_silent(dry_run: bool, raw) -> bool:
    return bool(dry_run) and str(raw or "").strip().lower() == "true"


def wrap_send(send_fn, silent: bool, log):
    if not silent:
        return send_fn

    def _quiet(msg):
        text = str(msg)
        if any(m in text for m in AUDIBLE_MARKERS):
            return send_fn(msg)
        log.info("[telegram silenciado, paper] " + text.replace("\n", " | "))
    return _quiet
