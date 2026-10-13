#!/usr/bin/env bash
# GLITCH -- Instala el watchdog en el crontab de TU usuario (03-oct-2026). Correr EN EL PI.
#   bash pi/ops/install_watchdog.sh            # instala (idempotente: reemplaza la linea previa, no la duplica)
#   bash pi/ops/install_watchdog.sh --remove   # la quita
#   bash pi/ops/install_watchdog.sh --instance mgc [--remove]   # watchdog de la SEGUNDA instancia (T4, 12-oct-2026): su propio log, estado y linea de cron
# No necesita sudo. Usa python3 del sistema (watchdog.py es solo stdlib) para que siga
# funcionando aunque el venv del executor este roto.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WATCHDOG="$SCRIPT_DIR/watchdog.py"
LOG_DIR="${PI_LOG_DIR:-$HOME/glitch-logs}"
INSTANCE=""; REMOVE=0
while [ $# -gt 0 ]; do
  case "$1" in
    --remove) REMOVE=1; shift;;
    --instance) INSTANCE="${2:-}"; shift 2;;
    *) echo "ERROR: argumento desconocido: $1" >&2; exit 1;;
  esac
done
[ -z "$INSTANCE" ] || [[ "$INSTANCE" =~ ^[a-z0-9]+$ ]] || { echo "ERROR: --instance solo admite minusculas y digitos (ej. mgc)." >&2; exit 1; }
if [ -z "$INSTANCE" ]; then       # instancia por defecto: identico al comportamiento anterior
  ENV_FILE="${PI_ENV_FILE:-$HOME/.glitch_pi.env}"
  MARK="# glitch-pi-watchdog"
  LINE="*/5 * * * * /usr/bin/python3 $WATCHDOG --log-file $LOG_DIR/pi_executor.log --env-file $ENV_FILE >> $LOG_DIR/watchdog.log 2>&1 $MARK"
else                              # T4 (12-oct-2026): una linea de cron, un log del ejecutor y un archivo de estado por instancia
  ENV_FILE="${PI_ENV_FILE:-$HOME/.glitch_pi_$INSTANCE.env}"
  MARK="# glitch-pi-instance-watchdog-$INSTANCE"   # NO contiene "# glitch-pi-watchdog" (grep -F de la instancia por defecto no debe borrarla)
  LINE="*/5 * * * * /usr/bin/python3 $WATCHDOG --log-file $LOG_DIR/pi_executor_$INSTANCE.log --env-file $ENV_FILE --state-file $HOME/.glitch_watchdog_state_$INSTANCE.json --service glitch-pi-executor-$INSTANCE >> $LOG_DIR/watchdog_$INSTANCE.log 2>&1 $MARK"
fi

[ -f "$WATCHDOG" ] || { echo "ERROR: falta $WATCHDOG" >&2; exit 1; }
command -v crontab >/dev/null || { echo "ERROR: crontab no esta instalado (sudo apt install cron)." >&2; exit 1; }

CURRENT="$(crontab -l 2>/dev/null || true)"
CLEANED="$(printf '%s\n' "$CURRENT" | grep -v -F "$MARK" || true)"

if [ "$REMOVE" = "1" ]; then
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
