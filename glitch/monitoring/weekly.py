"""Resumen semanal (lunes) — funciones PURAS: intentos desde el historial del Gist, semaforo de friccion, prueba de pase y compuerta de la 2.a cuenta."""
from __future__ import annotations
import datetime as dt
from math import comb
from typing import Optional

from monitoring import thresholds as TH
from monitoring.friction import aggregate

MODEL_PASS_RATE = 0.308          # mundo justo, nc=40 TP32 (REPORT_T1_COMBINE_SIZE)
PROFIT_TARGET, MLL_DIST = 3000.0, 2000.0


def attempt_outcomes(log: list, profit_target: float = PROFIT_TARGET, mll: float = MLL_DIST) -> dict:
    """Resultado por intento a partir de las entradas resueltas (TP/SL/FLATTEN) del historial: PASE si el acumulado llega al objetivo, QUIEBRE si toca el piso trailing EOD
    (piso = min(maximo - MLL, 0)), 'en curso' si ninguno. Replica la regla simple del scheduler (sin la consistencia del 55%: NO VERIFICADO si coincide en todos los casos)."""
    by: dict = {}
    for e in log:
        if e.get("result") in ("TP", "SL", "FLATTEN") and e.get("intento") is not None:
            by.setdefault(e["intento"], []).append(e)
    out = {}
    for k, es in by.items():
        cum = 0.0; peak = 0.0; res = "en curso"
        for e in sorted(es, key=lambda x: x.get("date", "")):
            cum += float(e.get("pnl", 0)); peak = max(peak, cum)
            if cum >= profit_target:
                res = "PASE"; break
            if cum <= min(peak - mll, 0.0):
                res = "QUIEBRE"; break
        out[k] = res
    return out


def binom_cdf(k: int, n: int, p: float) -> float:
    return sum(comb(n, i) * p ** i * (1 - p) ** (n - i) for i in range(k + 1))


def pass_test(passes: int, resolved: int, p0: float = MODEL_PASS_RATE, alpha: float = 0.05) -> dict:
    """Rechaza el modelo (pase = p0) si P(X <= passes | p0) <= alpha. Con resolved < 10 no hay poder: lo dice."""
    if resolved <= 0:
        return {"status": "sin datos", "p_value": None, "text": "sin Combines resueltos"}
    pv = binom_cdf(passes, resolved, p0)
    if resolved < 10:
        return {"status": "sin poder", "p_value": pv, "text": f"{passes} pases en {resolved} resueltos (p = {pv:.2f}): con N < 10 no se puede distinguir mala suerte de modelo roto"}
    if pv <= alpha:
        return {"status": "rojo", "p_value": pv, "text": f"{passes} pases en {resolved} resueltos (p = {pv:.3f} <= {alpha}): el modelo NO se sostiene, revisar friccion y detener altas"}
    return {"status": "verde", "p_value": pv, "text": f"{passes} pases en {resolved} resueltos (p = {pv:.2f}): consistente con el modelo (30.8%)"}


def summarize_attempts(log: list) -> dict:
    oc = attempt_outcomes(log)
    passed = sum(1 for v in oc.values() if v == "PASE"); busted = sum(1 for v in oc.values() if v == "QUIEBRE")
    return {"started": len(oc), "passed": passed, "busted": busted, "resolved": passed + busted}


def semaforo_text(friction_records: list) -> str:
    a = aggregate(friction_records)
    names = {"entry_slip_ticks": "slippage entrada (ticks)", "tp_cross_ticks": "TP cruzado sin llenar (ticks, peor caso)", "flatten_slip_ticks": "salida flatten (ticks)",
             "stop_slip_usd_per_ct": "stop XFA ($/contrato)", "api_failures_per_20": "fallos por 20 sesiones"}
    icon = {TH.GREEN: "VERDE", TH.YELLOW: "AMARILLO", TH.RED: "ROJO", TH.NODATA: "sin datos"}
    lines = [f"Sesiones con registro: {a['sessions']}"]
    for k, nm in names.items():
        v = a[k]; lines.append(f"- {nm}: {'n/d' if v is None else f'{v:.2f}'} -> {icon[a['colors'][k]]}")
    gate = TH.gate_decision(list(a["colors"].values()), a["hard_red_events"])
    lines.append(f"- eventos rojos duros: {a['hard_red_events']}")
    lines.append(f"COMPUERTA 2.a CUENTA: {'LUZ VERDE' if gate == TH.GREEN else ('ESPERAR (amarillo)' if gate == TH.YELLOW else 'NO (rojo)')}")
    return "\n".join(lines)


def weekly_message(today: dt.date, geometry_log: list, friction_records: list, costs: Optional[dict] = None) -> str:
    s = summarize_attempts(geometry_log); pt = pass_test(s["passed"], s["resolved"])
    msg = [f"{'S10GLITCH - MONITOR'} | RESUMEN SEMANAL {today.isoformat()}",
           f"Combines: {s['started']} iniciados, {s['resolved']} resueltos ({s['passed']} pases, {s['busted']} quiebres)",
           f"Prueba de pase: {pt['text']}", "", "FRICCION (ultimas 4 semanas):", semaforo_text(friction_records)]
    if costs:
        rate = costs.get("attempt_fee_actual")
        if rate is not None:
            ratio = rate / costs.get("attempt_fee_model", 127.0)
            msg.append(f"Costo por intento: ${rate:,.0f} vs modelo ${costs.get('attempt_fee_model', 127.0):,.0f} -> {TH.classify('cost_ratio', ratio).upper()} (x{ratio:.2f})")
    return "\n".join(msg)
