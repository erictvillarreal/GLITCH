#!/usr/bin/env bash
# GLITCH -- Instala el watchdog en el crontab de TU usuario (03-oct-2026). Correr EN EL PI.
#   bash pi/ops/install_watchdog.sh            # instala (idempotente: reemplaza la linea previa, no la duplica)
#   bash pi/ops/install_watchdog.sh --remove   # la quita
# No necesita sudo. Usa python3 del sistema (watchdog.py es solo stdlib) para que siga
# funcionando aunque el venv del executor este roto.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WATCHDOG="$SCRIPT_DIR/watchdog.py"
ENV_FILE="${PI_ENV_FILE:-$HOME/.glitch_pi.env}"
LOG_DIR="${PI_LOG_DIR:-$HOME/glitch-logs}"
MARK="# glitch-pi-watchdog"
LINE="*/5 * * * * /usr/bin/python3 $WATCHDOG --log-file $LOG_DIR/pi_executor.log --env-file $ENV_FILE >> $LOG_DIR/watchdog.log 2>&1 $MARK"

[ -f "$WATCHDOG" ] || { echo "ERROR: falta $WATCHDOG" >&2; exit 1; }
command -v crontab >/dev/null || { echo "ERROR: crontab no esta instalado (sudo apt install cron)." >&2; exit 1; }

CURRENT="$(crontab -l 2>/dev/null || true)"
CLEANED="$(printf '%s\n' "$CURRENT" | grep -v -F "$MARK" || true)"

if [ "${1:-}" = "--remove" ]; then
  printf '%s\n' "$CLEANED" | sed '/^$/N;/^\n$/D' | crontab -
  echo "Watchdog removido del crontab."
  exit 0
fi

mkdir -p "$LOG_DIR"
{ [ -n "$CLEANED" ] && printf '%s\n' "$CLEANED"; printf '%s\n' "$LINE"; } | crontab -
echo "Watchdog instalado (cada 5 min). Linea:"
echo "  $LINE"
echo
echo "Prueba en seco (no envia nada):  /usr/bin/python3 $WATCHDOG --log-file $LOG_DIR/pi_executor.log --env-file $ENV_FILE --dry-run"
echo "Su propio log:                   tail $LOG_DIR/watchdog.log"
