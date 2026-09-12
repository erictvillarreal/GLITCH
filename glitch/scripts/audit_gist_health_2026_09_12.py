"""
Glitch — Auditoria puntual del Gist real, Cerebro 1 (MES) + Cerebro 2 (MGC)
(checkpoint de mitad de ventana, dia 12/20, 12-sep-2026)
==============================================================================
NO exhaustiva -- diagnostico puntual pedido por el usuario para
descartar entradas huerfanas/mal etiquetadas que se hayan podido colar
durante los incidentes recientes (yaml ModuleNotFoundError, intento
stale, ambos ~10-sep-2026). Solo LEE el Gist, no escribe nada.

Variables de entorno requeridas: SOLO GITHUB_GIST_TOKEN y GIST_ID
(mismo patron que scripts/verify_fix_intento_today.py -- no importa
los schedulers completos para evitar su require_env de Telegram/
market-data, que este audit no necesita).

Uso:
    python scripts/audit_gist_health_2026_09_12.py
"""
from __future__ import annotations
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from execution.gist_store import load_log, load_state
from core.prop_firm import TOPSTEP_50K, TOPSTEP_150K

REQUIRED_FIELDS_RESOLVED = {"date", "side", "direction", "entry", "exit", "result", "pnl", "intento"}
KNOWN_RESULTS = {"TP", "SL", "FLATTEN", "RECONCILED"}
KNOWN_NOTES = {"no_data_entry"}  # entradas de señal sin resultado (sin "result", solo "note")

SCHEDULERS = [
    {
        "label": "Cerebro 1 -- GEOMETRY (MES)",
        "log_file": "geometry_mes_log.json",
        "pending_file": "geometry_mes_pending.json",
        "profit_target": TOPSTEP_50K.profit_target,
        "mll_threshold": -TOPSTEP_50K.mll_distance,
    },
    {
        "label": "Cerebro 2 -- GEOMETRY-MGC (MGC)",
        "log_file": "geometry_mgc_log.json",
        "pending_file": "geometry_mgc_pending.json",
        "profit_target": TOPSTEP_150K.profit_target,
        "mll_threshold": -TOPSTEP_150K.mll_distance,
    },
]


def _attempt_pnl(paper_log, intento):
    return sum(e.get("pnl", 0) for e in paper_log
               if e.get("result") in ("TP", "SL", "FLATTEN") and e.get("intento", 1) == intento)


def audit_log(label: str, log_file: str, profit_target: float, mll_threshold: float) -> None:
    print(f"\n{'=' * 70}\n{label} -- {log_file}\n{'=' * 70}")
    paper_log = load_log(log_file)
    print(f"Total de entradas: {len(paper_log)}")
    if not paper_log:
        print("  (vacio -- nada que auditar)")
        return

    # 1. Fechas duplicadas -- un solo trade por dia se asume por diseño.
    dates = [e.get("date") for e in paper_log if e.get("date")]
    dupes = [d for d, c in Counter(dates).items() if c > 1]
    if dupes:
        print(f"  ADVERTENCIA: fechas con MAS DE UNA entrada: {sorted(dupes)}")
    else:
        print("  OK: sin fechas duplicadas.")

    # 2. Campos faltantes en entradas resueltas (TP/SL/FLATTEN/RECONCILED).
    missing_field_entries = []
    for e in paper_log:
        if e.get("result") in KNOWN_RESULTS:
            missing = REQUIRED_FIELDS_RESOLVED - e.keys()
            if missing:
                missing_field_entries.append((e.get("date"), missing))
    if missing_field_entries:
        print(f"  ADVERTENCIA: entradas resueltas con campos faltantes:")
        for date, missing in missing_field_entries:
            print(f"    {date}: falta {sorted(missing)}")
    else:
        print("  OK: todas las entradas resueltas tienen los campos esperados.")

    # 3. Resultados desconocidos (ni un result conocido ni una note conocida).
    unexpected = [e for e in paper_log
                  if e.get("result") not in KNOWN_RESULTS and e.get("note") not in KNOWN_NOTES]
    if unexpected:
        print(f"  ADVERTENCIA: {len(unexpected)} entradas con result/note inesperado:")
        for e in unexpected:
            print(f"    {e.get('date')}: result={e.get('result')!r} note={e.get('note')!r}")
    else:
        print("  OK: todo result/note es uno de los valores conocidos.")

    # 4. Secuencia de "intento" -- no deberia retroceder nunca al ordenar por fecha.
    tagged = sorted([e for e in paper_log if e.get("intento") is not None and e.get("date")],
                     key=lambda e: e["date"])
    intento_seq = [e["intento"] for e in tagged]
    regressions = [(tagged[i - 1]["date"], tagged[i]["date"], intento_seq[i - 1], intento_seq[i])
                   for i in range(1, len(intento_seq)) if intento_seq[i] < intento_seq[i - 1]]
    if regressions:
        print(f"  ADVERTENCIA: 'intento' RETROCEDE en algun punto (imposible por diseño):")
        for d1, d2, i1, i2 in regressions:
            print(f"    {d1} (intento={i1}) -> {d2} (intento={i2})")
    else:
        print("  OK: 'intento' nunca retrocede.")

    # 5. Residuo del bug de "intento stale" (10-sep-2026, ya corregido en
    #    el codigo): para cada intento ya completado (cruzo umbral), NINGUNA
    #    entrada posterior deberia seguir tageada con ese mismo numero.
    intentos_presentes = sorted(set(intento_seq))
    stale_artifacts = []
    for intento in intentos_presentes:
        pnl = _attempt_pnl(paper_log, intento)
        crossed = pnl >= profit_target or pnl <= mll_threshold
        if not crossed:
            continue
        entries_this_intento = [e for e in tagged if e["intento"] == intento]
        last_date_this_intento = max(e["date"] for e in entries_this_intento)
        later_same_intento = [e for e in tagged if e["intento"] == intento and e["date"] > last_date_this_intento]
        # Si hay entradas de OTRO intento con fecha posterior a la ultima de
        # este, pero targeteando este intento otra vez -- no puede pasar por
        # construccion del filtro de arriba, esto solo detecta el caso real:
        # entradas del MISMO intento repartidas en mas dias de los que
        # deberian tras haber cruzado el umbral en un dia anterior.
        crossing_dates = sorted(e["date"] for e in entries_this_intento)
        # Si el intento tiene mas de un ciclo TP/SL/FLATTEN y el primero de
        # ellos YA cruzaba el umbral en solitario o acumulado hasta ahi, pero
        # se siguieron agregando entradas al MISMO intento despues -- señal
        # exacta del bug ya corregido.
        running = 0.0
        crossed_at = None
        for e in sorted(entries_this_intento, key=lambda x: x["date"]):
            if e.get("result") in ("TP", "SL", "FLATTEN"):
                running += e.get("pnl", 0)
                if crossed_at is None and (running >= profit_target or running <= mll_threshold):
                    crossed_at = e["date"]
        if crossed_at and crossed_at != crossing_dates[-1]:
            stale_artifacts.append((intento, crossed_at, crossing_dates[-1]))
    if stale_artifacts:
        print(f"  ADVERTENCIA -- POSIBLE RESIDUO DEL BUG DE INTENTO STALE (10-sep-2026):")
        for intento, crossed_at, last_date in stale_artifacts:
            print(f"    intento={intento} cruzo umbral el {crossed_at}, pero sigue "
                  f"recibiendo entradas hasta el {last_date} -- revisar a mano.")
    else:
        print("  OK: ningun intento completado sigue acumulando entradas despues de cruzar su umbral.")

    # 6. Entradas RECONCILED -- deben tener pnl_estimated=True (por diseño,
    #    nunca cuentan para Pass Rate/attempt_pnl, pero deben estar marcadas).
    reconciled = [e for e in paper_log if e.get("result") == "RECONCILED"]
    if reconciled:
        print(f"  {len(reconciled)} entrada(s) RECONCILED encontradas:")
        for e in reconciled:
            flag_ok = e.get("pnl_estimated") is True
            print(f"    {e.get('date')}: pnl_estimated={e.get('pnl_estimated')!r} "
                  f"{'OK' if flag_ok else '-- ADVERTENCIA: deberia ser True'}")
    else:
        print("  (sin entradas RECONCILED -- ningun crash-recovery activado hasta ahora)")

    # 7. Ventana de incidentes reciente (09-sep a 12-sep) -- listado para
    #    revision visual rapida, no un chequeo automatico adicional.
    window = [e for e in paper_log if e.get("date", "") >= "2026-09-09"]
    print(f"  Entradas del 09-sep al 12-sep (ventana de los incidentes recientes): {len(window)}")
    for e in sorted(window, key=lambda x: x.get("date", "")):
        print(f"    {e.get('date')}: result={e.get('result')!r} intento={e.get('intento')!r} "
              f"pnl={e.get('pnl')!r} note={e.get('note')!r}")


def audit_pending(label: str, pending_file: str) -> None:
    pending = load_state(pending_file)
    if not pending:
        print(f"\n{label} -- {pending_file}: VACIO (esperado -- hoy es sabado, sin posicion abierta).")
    else:
        print(f"\n{label} -- {pending_file}: ADVERTENCIA -- registro NO vacio encontrado:")
        print(f"    {pending}")
        print("    Revisar a mano si corresponde a una posicion real todavia abierta "
              "o a un residuo que deberia haberse limpiado.")


def main():
    for s in SCHEDULERS:
        audit_log(s["label"], s["log_file"], s["profit_target"], s["mll_threshold"])
        audit_pending(s["label"], s["pending_file"])
    print(f"\n{'=' * 70}\nAuditoria completa. Sin escritura -- ningun dato fue modificado.")


if __name__ == "__main__":
    main()
