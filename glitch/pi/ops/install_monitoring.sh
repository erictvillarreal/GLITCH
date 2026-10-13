#!/usr/bin/env bash
# GLITCH -- Instala los jobs de monitoreo del Pi en el crontab de TU usuario (T3, 12-oct-2026). Correr EN EL PI. Idempotente.
#   bash pi/ops/install_monitoring.sh --account-id 28197705 --kind combine [--product MES] [--start-balance 50000] [--mll 2000]
#   bash pi/ops/install_monitoring.sh --remove
# Instala: margin_alert.py (cada 5 min; decide solo la ventana CT) y friction_collect.py (cada 5 min; actua desde las 14:40 CT y una vez por dia). Usa el venv del ejecutor
# (necesitan brokers/ y strategies/). Los jobs de Railway (weekly_summary, reminders_job) se configuran en el panel de Railway, no aqui.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"; ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
ENV_FILE="${PI_ENV_FILE:-$HOME/.glitch_pi.env}"; LOG_DIR="${PI_LOG_DIR:-$HOME/glitch-logs}"; PY="${PI_PYTHON:-$ROOT/.venv/bin/python}"
MARK1="# glitch-pi-margin"; MARK2="# glitch-pi-friction"
ACCOUNT=""; KIND="combine"; PRODUCT="MES"; START="50000"; MLL="2000"; REMOVE=0
while [ $# -gt 0 ]; do case "$1" in
  --account-id) ACCOUNT="$2"; shift 2;; --kind) KIND="$2"; shift 2;; --product) PRODUCT="$2"; shift 2;;
  --start-balance) START="$2"; shift 2;; --mll) MLL="$2"; shift 2;; --remove) REMOVE=1; shift;; *) echo "arg desconocido: $1" >&2; exit 1;; esac; done
command -v crontab >/dev/null || { echo "ERROR: crontab no esta instalado." >&2; exit 1; }
CURRENT="$(crontab -l 2>/dev/null || true)"
CLEANED="$(printf '%s\n' "$CURRENT" | grep -v -F -e "$MARK1" -e "$MARK2" || true)"
if [ "$REMOVE" = 1 ]; then printf '%s\n' "$CLEANED" | sed '/^$/N;/^\n$/D' | crontab -; echo "Jobs de monitoreo removidos."; exit 0; fi
[ -n "$ACCOUNT" ] || { echo "ERROR: --account-id es obligatorio (el ID del API NO es el del dashboard)." >&2; exit 1; }
[ -x "$PY" ] || { echo "ERROR: no existe $PY (usa PI_PYTHON=/ruta/al/python del venv del ejecutor)." >&2; exit 1; }
mkdir -p "$LOG_DIR"
L1="*/5 * * * 1-5 cd $ROOT && $PY pi/ops/margin_alert.py --kind $KIND --account-id $ACCOUNT --product $PRODUCT --start-balance $START --mll $MLL --env-file $ENV_FILE >> $LOG_DIR/margin_alert.log 2>&1 $MARK1"
L2="*/5 * * * 1-5 cd $ROOT && $PY pi/ops/friction_collect.py --account-id $ACCOUNT --product $PRODUCT --env-file $ENV_FILE --log-file $LOG_DIR/pi_executor.log >> $LOG_DIR/friction_collect.log 2>&1 $MARK2"
{ [ -n "$CLEANED" ] && printf '%s\n' "$CLEANED"; printf '%s\n%s\n' "$L1" "$L2"; } | crontab -
echo "Instalado (cron del Pi; TZ del sistema irrelevante: los scripts usan America/Chicago):"; echo "  $L1"; echo "  $L2"
echo "Prueba en seco:  $PY pi/ops/margin_alert.py --kind $KIND --account-id $ACCOUNT --product $PRODUCT --start-balance $START --mll $MLL --force-window --dry-run"
