#!/usr/bin/env bash
# GLITCH -- Instala pi_executor como servicio systemd (03-oct-2026). Correr EN EL PI.
#
#   bash pi/ops/install_service.sh            # instala + habilita (arranca solo al prender el Pi), NO lo arranca
#   bash pi/ops/install_service.sh --start    # ademas lo arranca ahora (solo si NO hay un pi_executor.py suelto corriendo)
#
# Que hace (y que NO):
#   * Genera /etc/systemd/system/glitch-pi-executor.service desde la plantilla (pide sudo SOLO para eso
#     y para `systemctl`; el resto corre como tu usuario).
#   * Si falta el archivo de entorno (~/.glitch_pi.env) crea una PLANTILLA con los NOMBRES de las variables
#     y valores VACIOS, chmod 600. Los valores los escribes TU, a mano, en el Pi. Este script nunca lee, imprime
#     ni escribe un valor de credencial.
#   * NO exporta GLITCH_PI_PHASE3: el gate de Fase 3 (instruccion del 22-sep) sigue cerrado hasta que lo abras tu.
#   * NO mata procesos. Si encuentra un `pi_executor.py` corriendo por fuera de systemd (el de nohup), se NIEGA a
#     arrancar el servicio: dos ejecutores a la vez = dos lectores de la misma señal/estado. Te da el comando para
#     detenerlo; lo detienes tu cuando no haya un bracket abierto.
#
# Variables de entorno opcionales para sobreescribir defaults: PI_VENV, PI_ENV_FILE, PI_LOG_DIR.
set -euo pipefail

START_NOW=0
[ "${1:-}" = "--start" ] && START_NOW=1

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GLITCH_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"          # .../glitch (donde vive pi/pi_executor.py)
PI_USER="$(id -un)"
VENV="${PI_VENV:-$HOME/glitch-env}"
ENV_FILE="${PI_ENV_FILE:-$HOME/.glitch_pi.env}"
LOG_DIR="${PI_LOG_DIR:-$HOME/glitch-logs}"
LOG_FILE="$LOG_DIR/pi_executor.log"
UNIT_NAME="glitch-pi-executor.service"
UNIT_DEST="/etc/systemd/system/$UNIT_NAME"
TEMPLATE="$SCRIPT_DIR/glitch-pi-executor.service.template"

die() { echo "ERROR: $*" >&2; exit 1; }

[ "$(id -u)" -ne 0 ] || die "No correr como root: el servicio debe correr como tu usuario ($PI_USER). El script llama sudo solo donde hace falta."
[ -f "$GLITCH_DIR/pi/pi_executor.py" ] || die "No encuentro $GLITCH_DIR/pi/pi_executor.py -- correr este script desde dentro del repo clonado en el Pi."
[ -x "$VENV/bin/python" ] || die "No existe $VENV/bin/python -- define PI_VENV=/ruta/al/venv o crea el venv primero."
[ -f "$TEMPLATE" ] || die "Falta la plantilla $TEMPLATE"
command -v systemctl >/dev/null || die "systemctl no existe -- este script es solo para el Pi (Linux con systemd)."

mkdir -p "$LOG_DIR"

# --- Archivo de entorno: crear plantilla vacia si no existe; nunca tocar uno existente ---
REQUIRED_VARS="TOPSTEP_USERNAME TOPSTEP_API_KEY TOPSTEP_ACCOUNT_ID TELEGRAM_BOT_TOKEN TELEGRAM_CHAT_ID GITHUB_GIST_TOKEN GIST_ID GLITCH_PRODUCT"
if [ ! -f "$ENV_FILE" ]; then
  umask 077
  {
    echo "# GLITCH Pi Executor -- variables de entorno para systemd (EnvironmentFile)."
    echo "# Formato: NOMBRE=valor, sin 'export' y sin espacios alrededor del '='. chmod 600. NUNCA en git."
    echo "# Llena los valores TU, a mano, en el Pi."
    for v in $REQUIRED_VARS; do echo "$v="; done
    echo "# TOPSTEP_ACCOUNT_ID es OBLIGATORIA: la cuenta sobre la que opera el Pi (Demo Pi = Practice). Nunca la Combine."
    echo
    echo "# Gate de Fase 3 (22-sep-2026). Descomentar SOLO cuando se llegue a Fase 3 y exista pi/orderside_verified.json:"
    echo "# GLITCH_PI_PHASE3=si"
  } > "$ENV_FILE"
  echo "Creada plantilla $ENV_FILE (valores VACIOS, chmod 600). Edítala con tus valores y vuelve a correr este script."
  exit 0
fi
chmod 600 "$ENV_FILE"

# Verificar que cada variable requerida tenga un valor NO vacio -- solo se reportan NOMBRES, nunca valores.
MISSING=""
for v in $REQUIRED_VARS; do
  if ! grep -Eq "^[[:space:]]*${v}=.+" "$ENV_FILE"; then MISSING="$MISSING $v"; fi
done
[ -z "$MISSING" ] || die "En $ENV_FILE faltan valores para:$MISSING (completalos a mano y reintenta)."

# --- Detectar un pi_executor suelto (nohup) -- no se mata, se avisa ---
SVC_PID="$(systemctl show -p MainPID --value "$UNIT_NAME" 2>/dev/null || echo 0)"   # el propio servicio (si ya existe) no cuenta como "suelto"
LOOSE="$(pgrep -af 'pi_executor.py' | grep -v "install_service" | awk -v svc="${SVC_PID:-0}" '$1 != svc' || true)"
if [ -n "$LOOSE" ]; then
  echo "Se encontro un pi_executor.py corriendo FUERA de systemd:"
  echo "$LOOSE"
  if [ "$START_NOW" = "1" ]; then
    die "No se arranca el servicio con otro ejecutor vivo. Detenlo tu (kill <PID>, cuando no haya bracket abierto) y reintenta con --start."
  fi
  echo "(Se instala y habilita igual; NO arranques el servicio hasta detener ese proceso.)"
fi

# --- Renderizar la plantilla e instalar ---
TMP="$(mktemp)"
sed -e "s|@PI_USER@|$PI_USER|g" \
    -e "s|@GLITCH_DIR@|$GLITCH_DIR|g" \
    -e "s|@ENV_FILE@|$ENV_FILE|g" \
    -e "s|@VENV@|$VENV|g" \
    -e "s|@LOG_FILE@|$LOG_FILE|g" \
    "$TEMPLATE" > "$TMP"
grep -q '@[A-Z_]*@' "$TMP" && { rm -f "$TMP"; die "Quedaron placeholders sin reemplazar en la unidad."; }

echo "Instalando $UNIT_DEST (sudo)..."
sudo install -m 644 "$TMP" "$UNIT_DEST"
rm -f "$TMP"
sudo systemctl daemon-reload
sudo systemctl enable "$UNIT_NAME"
echo "Habilitado: arrancara solo en cada inicio del Pi."

if [ "$START_NOW" = "1" ]; then
  sudo systemctl start "$UNIT_NAME"
  sleep 3
  sudo systemctl --no-pager --lines=0 status "$UNIT_NAME" || true
fi

cat <<EOF

Listo. Comandos utiles:
  sudo systemctl start   $UNIT_NAME      # arrancar
  sudo systemctl restart $UNIT_NAME      # reiniciar (p. ej. tras actualizar el codigo)
  sudo systemctl status  $UNIT_NAME      # estado
  sudo systemctl reset-failed $UNIT_NAME # si llego al limite de reintentos (5 fallos en 15 min)
  tail -f $LOG_FILE
EOF
