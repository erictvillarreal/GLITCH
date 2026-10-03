#!/usr/bin/env bash
# GLITCH -- Diagnostico de reinicio del Pi (03-oct-2026). SOLO LECTURA: no cambia
# ninguna configuracion, no instala nada, no reinicia nada.
#
# Uso (en el Pi, por SSH):
#     bash diagnose_reboot.sh
# Guarda una copia en ~/glitch_reboot_diagnosis.txt (para pegarla de vuelta).
#
# Que busca (en este orden, porque la causa mas probable depende de lo anterior):
#   1. Cuando fue el ultimo arranque y si el apagado anterior fue LIMPIO o abrupto.
#   2. Si el journal es persistente -- en Raspberry Pi OS suele ser VOLATIL, y entonces
#      `journalctl -b -1` no existe: sin eso no se puede probar nada del arranque anterior.
#   3. Si unattended-upgrades esta instalado, si tiene Automatic-Reboot activo, y si hubo
#      una corrida de apt cerca de la hora del reinicio (apt history + su propio log).
#   4. Causas alternativas: bajo voltaje (fuente de poder), OOM, kernel panic.
# Al final imprime un VEREDICTO conservador: solo dice "unattended-upgrades" si hay
# evidencia directa; si no, dice "NO CONCLUYENTE" y por que -- nunca adivina.

set -u
OUT="$HOME/glitch_reboot_diagnosis.txt"
exec > >(tee "$OUT") 2>&1

hr() { printf '\n==== %s ====\n' "$1"; }
have() { command -v "$1" >/dev/null 2>&1; }
# journalctl puede requerir sudo segun el grupo del usuario; probar sin sudo, luego con sudo -n (sin pedir clave)
jc() { journalctl "$@" 2>/dev/null || sudo -n journalctl "$@" 2>/dev/null; }

EVIDENCE_UU=0       # evidencia directa de unattended-upgrades como causa del reinicio
EVIDENCE_POWER=0    # evidencia de bajo voltaje / corte
EVIDENCE_ABRUPT=0   # el boot anterior termino sin secuencia de apagado limpio
JOURNAL_PERSISTENT=0

hr "1. Arranque actual y reinicios recientes"
echo "Ahora:                 $(date '+%Y-%m-%d %H:%M:%S %Z')"
echo "Arranque actual desde: $(uptime -s 2>/dev/null)  ($(uptime -p 2>/dev/null))"
echo "--- last -x reboot shutdown (ultimos 8) ---"
last -x reboot shutdown 2>/dev/null | head -8

hr "2. Journal: es persistente? (sin esto no hay forma de leer el arranque anterior)"
if [ -d /var/log/journal ]; then
  JOURNAL_PERSISTENT=1
  echo "SI: /var/log/journal existe -> journalctl -b -1 deberia tener el arranque anterior."
else
  echo "NO: /var/log/journal no existe -> el journal es VOLATIL (se borra en cada reinicio)."
  echo "    Consecuencia: 'journalctl -b -1' NO puede decirte por que se reinicio."
  echo "    Para que la proxima vez SI quede registro (requiere sudo, lo aplicas tu):"
  echo "        sudo mkdir -p /var/log/journal && sudo systemctl restart systemd-journald"
fi
echo "--- journalctl --list-boots (ultimos 4) ---"
jc --list-boots | tail -4

hr "3. Arranque ANTERIOR (-b -1): como termino?"
if [ "$JOURNAL_PERSISTENT" = "1" ] && jc -b -1 -n 1 --no-pager >/dev/null 2>&1; then
  jc -b -1 --no-pager -n 400 > /tmp/glitch_prevboot.txt
  echo "--- ultimas 40 lineas del boot anterior ---"
  tail -40 /tmp/glitch_prevboot.txt
  if grep -qiE "Reached target (Reboot|Power-Off|Shutdown)|systemd-shutdown|Journal stopped" /tmp/glitch_prevboot.txt; then
    echo ">>> El boot anterior tiene secuencia de apagado LIMPIO (reboot/shutdown ordenado)."
  else
    EVIDENCE_ABRUPT=1
    echo ">>> El boot anterior NO muestra secuencia de apagado limpio -> corte de energia, cuelgue o panic."
  fi
  if grep -qiE "unattended-upgrade|apt-daily-upgrade" /tmp/glitch_prevboot.txt; then
    echo ">>> El boot anterior menciona unattended-upgrades / apt-daily-upgrade (ver lineas abajo):"
    grep -iE "unattended-upgrade|apt-daily-upgrade" /tmp/glitch_prevboot.txt | tail -8
  fi
else
  echo "No hay journal del arranque anterior disponible (ver punto 2). Se sigue con apt/logs de archivo."
fi

hr "4. unattended-upgrades: instalado, configuracion de reinicio y corridas recientes"
if dpkg -s unattended-upgrades >/dev/null 2>&1; then
  echo "unattended-upgrades: INSTALADO"
else
  echo "unattended-upgrades: NO instalado (entonces no es la causa)"
fi
echo "--- Automatic-Reboot en la config efectiva (apt-config) ---"
apt-config dump 2>/dev/null | grep -iE "Unattended-Upgrade::(Automatic-Reboot|Automatic-Reboot-Time|Automatic-Reboot-WithUsers)" || echo "(sin entradas -> Automatic-Reboot usa su default, 'false')"
echo "--- /var/run/reboot-required (existe = hay un reinicio pendiente por paquetes) ---"
if [ -f /var/run/reboot-required ]; then cat /var/run/reboot-required; cat /var/run/reboot-required.pkgs 2>/dev/null; else echo "no existe"; fi
echo "--- timers de apt (cuando corre la actualizacion automatica) ---"
systemctl list-timers --all 2>/dev/null | grep -E "NEXT|apt-daily" || true
echo "--- /var/log/apt/history.log: ultimas 3 corridas ---"
if [ -f /var/log/apt/history.log ]; then
  grep -E "^(Start-Date|Commandline|Upgrade|End-Date)" /var/log/apt/history.log | tail -16
else
  echo "(no existe /var/log/apt/history.log)"
fi
echo "--- /var/log/unattended-upgrades/unattended-upgrades.log (lineas relevantes recientes) ---"
UU_LOG=/var/log/unattended-upgrades/unattended-upgrades.log
if [ -r "$UU_LOG" ] || sudo -n test -r "$UU_LOG" 2>/dev/null; then
  { cat "$UU_LOG" 2>/dev/null || sudo -n cat "$UU_LOG" 2>/dev/null; } \
    | grep -iE "Packages that will be upgraded|Packages that were upgraded|reboot|Rebooting|No packages found" | tail -12
else
  echo "(sin acceso de lectura a $UU_LOG -- probar: sudo cat $UU_LOG)"
fi

# Evidencia directa: el reinicio ocurrio dentro de +-45 min de una corrida de apt/UU Y Automatic-Reboot=true
BOOT_EPOCH=$(date -d "$(uptime -s 2>/dev/null)" +%s 2>/dev/null || echo 0)
AUTO_REBOOT=$(apt-config dump 2>/dev/null | grep -iE "Unattended-Upgrade::Automatic-Reboot\b" | grep -ci "true")
if [ "$BOOT_EPOCH" -gt 0 ] && [ -f /var/log/apt/history.log ]; then
  LAST_APT=$(grep -E "^End-Date" /var/log/apt/history.log | tail -1 | sed 's/End-Date: //')
  if [ -n "$LAST_APT" ]; then
    APT_EPOCH=$(date -d "$(echo "$LAST_APT" | sed 's/  */ /')" +%s 2>/dev/null || echo 0)
    if [ "$APT_EPOCH" -gt 0 ]; then
      DIFF=$(( BOOT_EPOCH - APT_EPOCH ))
      echo "--- Cercania: ultimo End-Date de apt = $LAST_APT; segundos hasta el arranque actual = $DIFF ---"
      if [ "$DIFF" -ge -300 ] && [ "$DIFF" -le 2700 ] && [ "$AUTO_REBOOT" -ge 1 ]; then EVIDENCE_UU=1; fi
    fi
  fi
fi

hr "5. Causas alternativas: bajo voltaje, OOM, panic"
if have vcgencmd; then
  T=$(vcgencmd get_throttled 2>/dev/null); echo "vcgencmd get_throttled: $T   (0x0 = sin problemas; bit 0x1/0x10000 = bajo voltaje actual/historico)"
  case "$T" in *"0x0") ;; *) EVIDENCE_POWER=1;; esac
fi
echo "--- dmesg / kernel del boot actual: voltaje, OOM, panic ---"
{ dmesg 2>/dev/null || sudo -n dmesg 2>/dev/null; } | grep -iE "under-voltage|undervoltage|voltage|Out of memory|Killed process|panic|Oops" | tail -8 || true
if [ -f /tmp/glitch_prevboot.txt ]; then
  echo "--- boot anterior: voltaje/OOM/panic ---"
  grep -iE "under-voltage|undervoltage|Out of memory|Killed process|panic|Oops" /tmp/glitch_prevboot.txt | tail -8 || true
  grep -qiE "under-voltage|undervoltage" /tmp/glitch_prevboot.txt && EVIDENCE_POWER=1
fi

hr "VEREDICTO (conservador: solo afirma lo que tiene evidencia directa)"
if [ "$EVIDENCE_UU" = "1" ]; then
  echo "PROBABLE: unattended-upgrades con Automatic-Reboot=true (corrida de apt a minutos del reinicio)."
  echo "  Accion sugerida (la aplicas tu, requiere sudo): ver glitch/pi/ops/README.md -> 'Evitar reinicios en horario de mercado'."
elif [ "$EVIDENCE_POWER" = "1" ]; then
  echo "PROBABLE: problema de ENERGIA / bajo voltaje (fuente de poder o cable). unattended-upgrades NO esta probado."
  echo "  Accion sugerida: usar la fuente oficial de 5V/3A (Pi 4) o 5V/5A (Pi 5) y un cable corto; revisar get_throttled."
elif [ "$EVIDENCE_ABRUPT" = "1" ]; then
  echo "PROBABLE: apagado abrupto (corte de energia/cuelgue) -- el boot anterior no cerro limpio y apt no esta implicado."
else
  if [ "$JOURNAL_PERSISTENT" = "0" ]; then
    echo "NO CONCLUYENTE: el journal es volatil, asi que el arranque anterior no se puede inspeccionar."
    echo "  Activa el journal persistente (punto 2) para que el PROXIMO reinicio deje evidencia, y revisa si hay"
    echo "  corrida de apt cerca de la hora del arranque (punto 4)."
  else
    echo "NO CONCLUYENTE: sin evidencia directa de apt, voltaje ni apagado abrupto. Pega este archivo completo para revisarlo."
  fi
fi
echo
echo "Copia guardada en: $OUT"
