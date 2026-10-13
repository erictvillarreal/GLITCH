"""Semaforo de friccion — umbrales de REPORT_STACKING_TIMING_2026-10.md §3 (luz verde de la 2.a cuenta). Son juicio calibrado con la sensibilidad del motor
(dd_cash/lever_engine.py), NO reglas de Topstep. Cada metrica: (verde_max, amarillo_max); por encima de amarillo_max = rojo. Valores del modelo: entrada 0 ticks,
TP llena al tocar, flatten 0 ticks, stop XFA $34 por contrato (p90 $80), 0 fallos, costo por intento $49 + comisiones."""
from __future__ import annotations

GREEN, YELLOW, RED, NODATA = "verde", "amarillo", "rojo", "sin datos"

LIMITS = {
    "entry_slip_ticks":       (1.0, 2.0),    # adverso por contrato vs. cierre de la barra de 1 min de referencia
    "tp_cross_ticks":         (1.0, 2.0),    # ticks que el precio cruzo el TP SIN que se llenara (peor caso de la ventana)
    "flatten_slip_ticks":     (1.0, 2.0),    # salida de las 14:30 vs. cierre de la barra de referencia
    "stop_slip_usd_per_ct":   (70.0, 140.0), # exceso sobre el precio del stop, USD por contrato (pocas observaciones)
    "api_failures_per_20":    (1.0, 2.0),    # entradas fallidas/tardias (>60 s) por 20 sesiones
    "cost_ratio":             (1.05, 1.10),  # costo real por intento / costo del modelo
}
# Eventos que son ROJO inmediato sin importar la frecuencia.
HARD_RED_EVENTS = ("unprotected_bracket", "duplicate_order", "unreconciled_position", "wrong_account", "open_after_1435")


def classify(metric: str, value) -> str:
    if value is None:
        return NODATA
    lo, hi = LIMITS[metric]
    v = float(value)
    return GREEN if v <= lo else (YELLOW if v <= hi else RED)


def worst(colors) -> str:
    colors = [c for c in colors if c != NODATA]
    if not colors:
        return NODATA
    return RED if RED in colors else (YELLOW if YELLOW in colors else GREEN)


def gate_decision(colors, hard_red_events=0) -> str:
    """Regla de luz verde de la 2.a cuenta: todas en verde o a lo mas UNA en amarillo, ninguna en rojo, cero eventos rojos duros."""
    cs = [c for c in colors if c != NODATA]
    if hard_red_events or RED in cs:
        return RED
    return GREEN if cs.count(YELLOW) <= 1 else YELLOW
