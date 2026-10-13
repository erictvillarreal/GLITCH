"""GLITCH — monitoreo y notificaciones por Telegram (T3, 12-oct-2026). SOLO LECTURA: nada de este paquete coloca ni cancela ordenes ni toca la logica de
ejecucion de pi/pi_executor.py. Las funciones de decision son PURAS (sin red, sin disco, sin reloj) para poder probarlas; los scripts de entrada
(pi/ops/margin_alert.py, pi/ops/friction_collect.py, scheduler/weekly_summary.py, scheduler/reminders_job.py) hacen el I/O. NEEDS HUMAN REVIEW."""
