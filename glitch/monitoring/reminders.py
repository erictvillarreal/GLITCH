"""Recordatorios con fecha — funciones PURAS. Corre una vez al dia en Railway (cron, 8:00 CT); el estado 'ya enviados' vive en el Gist (reminders_sent.json), asi que es idempotente
si el cron corre dos veces. Fechas: calendario de REPORT_STACKING_TIMING / T2 / T1 (arranque del Combine real: lun 19-oct-2026)."""
from __future__ import annotations
import datetime as dt
from typing import Callable, Optional

# (id, fecha minima, predicado opcional sobre ctx, texto). Si hay predicado, el recordatorio sale en la PRIMERA de: la fecha, o el momento en que el predicado se cumple.
REMINDERS = [
    ("r_2026-11-09_resumen", dt.date(2026, 11, 9), None,
     "Lunes 9-nov: resumen de las primeras 3 semanas del Combine real. Revisar friccion (semaforo) y Combines resueltos. {semaforo}"),
    ("r_presupuesto_5_intentos", dt.date(2026, 11, 15), lambda c: c.get("attempts_started", 0) >= 5,
     "Revision de presupuesto: ya hay >= 5 intentos de Combine o llego el 15-nov. Comparar costo real por intento ($49 + comisiones) contra el modelo ($127 con nc=40 TP32) y el neto acumulado. {semaforo}"),
    ("r_2026-11-16_segunda", dt.date(2026, 11, 16), None,
     "Lunes 16-nov: EVALUAR 2.a CUENTA (MES + MCL, senales distintas). Luz verde solo si el semaforo de friccion esta todo en verde (a lo mas un amarillo), cero eventos rojos duros y el ejecutor de 2 cuentas esta auditado. {semaforo}"),
    ("r_n10_prueba", dt.date(2026, 12, 10), lambda c: c.get("attempts_resolved", 0) >= 10,
     "Prueba de pase con 10 Combines resueltos: {pass_test}. Con 0 pases se rechaza el modelo (p = 2.5% si es correcto)."),
    ("r_2026-12-14_tercera", dt.date(2026, 12, 14), None,
     "Lunes 14-dic: EVALUAR 3.a CUENTA (MGC 9:45). Condiciones (T2): respuesta escrita de Topstep sobre RTP/compras, friccion en verde 4 semanas, >= 1 pase en los primeros 10 Combines, reserva >= $12k, instancias MGC/MCL probadas. Si algo no esta en verde: posponer a N=20. {semaforo}"),
    ("r_2027-02-16_n20", dt.date(2027, 2, 16), lambda c: c.get("attempts_resolved", 0) >= 20,
     "Prueba N=20 Combines resueltos (~16-feb-2027): {pass_test}. <= 2 pases rechaza el modelo (alfa 3%, poder 40% contra p=15%). Decidir 3.a cuenta y tamano del programa."),
]


def due_reminders(today: dt.date, sent_ids, ctx: dict, reminders=REMINDERS) -> list:
    """Recordatorios que toca enviar hoy: no enviados aun, y (fecha alcanzada O predicado cumplido), nunca antes del arranque del Combine real (19-oct-2026)."""
    if today < dt.date(2026, 10, 19):
        return []
    sent = set(sent_ids)
    out = []
    for rid, on, pred, text in reminders:
        if rid in sent:
            continue
        if today >= on or (pred is not None and bool(pred(ctx))):
            out.append((rid, text))
    return out


def render(text: str, ctx: dict) -> str:
    return text.format(semaforo=ctx.get("semaforo_text", "(semaforo no disponible)"), pass_test=ctx.get("pass_test_text", "(sin datos)"))
