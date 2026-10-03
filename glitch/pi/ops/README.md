# `pi/ops/` — operar el Pi Executor de forma confiable

Todo esto corre **en el Pi** (por SSH). Nada aquí se ejecuta solo ni cambia nada sin que lo corras tú.
Qué vive en el Pi vs. Railway: ver [`../ARCHITECTURE.md`](../ARCHITECTURE.md).

## Orden recomendado

```bash
# 0. En el Pi, con el repo actualizado (git pull de la rama que se apruebe)
cd ~/<repo>/glitch

# 1. Diagnóstico del reinicio (solo lectura; guarda ~/glitch_reboot_diagnosis.txt)
bash pi/ops/diagnose_reboot.sh

# 2. Servicio systemd. La primera vez crea ~/.glitch_pi.env con NOMBRES y valores vacíos (chmod 600):
bash pi/ops/install_service.sh
#    -> llena los valores TÚ, a mano, con nano ~/.glitch_pi.env  (nunca por chat) y vuelve a correrlo.
#    -> instala y HABILITA el servicio (arranca solo al prender el Pi); todavía NO lo arranca.

# 3. Detén el pi_executor de nohup (cuando NO haya un bracket abierto) y arranca el servicio:
pgrep -af pi_executor.py            # ve el PID
kill <PID>                          # SIGTERM; el estado del bracket vive en el Gist, no en el proceso
bash pi/ops/install_service.sh --start
tail -f ~/glitch-logs/pi_executor.log

# 4. Watchdog (cron cada 5 min)
bash pi/ops/install_watchdog.sh
python3 pi/ops/watchdog.py --dry-run   # prueba en seco: imprime el estado, no envía nada
```

Para comprobar que sobrevive a un reinicio real: `sudo reboot`, y 1–2 min después
`systemctl is-active glitch-pi-executor` debe decir `active` y el log debe tener líneas nuevas.

## Qué hace cada pieza

| Archivo | Para qué |
|---|---|
| `diagnose_reboot.sh` | Solo lectura. Dice si el reinicio fue limpio o abrupto, si el journal es persistente, si hay `unattended-upgrades` con reinicio automático y una corrida de apt a minutos del arranque, y descarta bajo voltaje/OOM. Su veredicto es **conservador**: solo dice "unattended-upgrades" con evidencia directa. |
| `glitch-pi-executor.service.template` / `install_service.sh` | Servicio systemd con `Restart=always`. `RestartSec=30` y tope de 5 fallos en 15 min (porque `require_env` manda un Telegram por cada arranque fallido). Credenciales en `~/.glitch_pi.env`, nunca en la unidad. No abre el gate de Fase 3. |
| `watchdog.py` / `install_watchdog.sh` | Cada 5 min mira que `~/glitch-logs/pi_executor.log` haya crecido en los últimos 10 min. Alerta **una vez** por caída, avisa al recuperarse, gracia de 5 min tras un reinicio, solo stdlib. Funciona porque el ejecutor loguea cada 120 s (ocioso) y, con un bracket abierto, un heartbeat cada ~5 min. |

## Evitar reinicios en horario de mercado

Hechos primero: en Debian/Raspberry Pi OS, `unattended-upgrades` **instala** parches de seguridad pero **no
reinicia** salvo que `Unattended-Upgrade::Automatic-Reboot` esté en `"true"` (el default es `false`). Por eso el
diagnóstico no asume nada: corre `diagnose_reboot.sh` y mira el VEREDICTO. Otras causas comunes de un reinicio en un
Pi son la fuente de poder (bajo voltaje) y un corte de energía.

**Si el veredicto es `unattended-upgrades`**, dos opciones (requieren `sudo`, las aplicas tú):

```bash
# Opción A (recomendada): que NUNCA reinicie solo; reinicias tú un sábado cuando haya paquetes pendientes
echo 'Unattended-Upgrade::Automatic-Reboot "false";' | sudo tee /etc/apt/apt.conf.d/52glitch-no-auto-reboot
ls /var/run/reboot-required 2>/dev/null && echo "hay un reinicio pendiente -> hazlo en fin de semana"

# Opción B: que reinicie, pero a una hora segura. La hora es la del RELOJ DEL PI (revisa `timedatectl`:
# si está en UTC, 03:00 UTC = 22:00 CT). Evita 07:00–15:10 CT lun–vie (ventana de operación).
printf 'Unattended-Upgrade::Automatic-Reboot "true";\nUnattended-Upgrade::Automatic-Reboot-Time "03:00";\n' \
  | sudo tee /etc/apt/apt.conf.d/52glitch-reboot-window
```

**Sea cual sea la causa**, activa el journal persistente para que el próximo reinicio deje evidencia
(en Raspberry Pi OS suele ser volátil y `journalctl -b -1` no existe):

```bash
sudo mkdir -p /var/log/journal && sudo systemctl restart systemd-journald
```

## Lo que NO resuelve esto (para que no sorprenda)

* Si el Pi se apaga **con un bracket abierto**, el bracket (TP/SL) sigue en el broker; al volver, el servicio
  arranca y `reconcile_if_needed` retoma desde el estado en el Gist. Pero mientras el Pi esté caído nadie
  monitorea — el watchdog solo te avisa; no actúa. En particular, **el flatten de las 14:30 CT lo ejecuta el Pi**:
  con el Pi caído a esa hora, la posición no se cierra sola (Topstep exige estar plano antes de las 3:10 PM CT) y
  habría que cerrarla a mano en TopstepX.
* El watchdog corre **en el mismo Pi**: si el Pi está apagado o sin red, no puede avisar. Para eso haría falta un
  chequeo externo (p. ej. un cron en Railway que alerte si el Gist no se actualiza) — no está construido.
* `verify_orderside_demo.py` y el gate de Fase 3 no cambian: sin `orderside_verified.json` el ejecutor no coloca
  órdenes, esté el servicio corriendo o no.
