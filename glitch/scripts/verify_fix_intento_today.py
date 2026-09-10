"""
Glitch — Verificacion puntual del tag "intento" de la entrada de HOY,
GEOMETRY (MES) (10-sep-2026, ver GLITCH_RESEARCH_LOG.md)
======================================================================
Diagnostico standalone para el bug de _current_intento() ya corregido
en scheduler/geometry_scheduler.py (commit local, push pendiente hasta
salir del freeze window de `main`): la entrada de MES abierta hoy
(LONG, entry ~7610.25) se abrio con el scheduler VIEJO todavia
desplegado, asi que es probable que haya quedado tageada con el
intento YA COMPLETADO (el que disparo el PASE ayer) en vez del
intento nuevo que le corresponde.

Chequea DOS lugares posibles, porque el trade puede seguir abierto o ya
haber cerrado para cuando esto se corre:
  1. geometry_mes_log.json (LOG_FILE) -- si el trade ya cerro (TP/SL/
     FLATTEN), la entrada final vive aqui, con "intento" fijado en el
     momento del CLOSE.
  2. geometry_mes_pending.json (PENDING_FILE) -- si el trade sigue
     abierto, el registro "posicion pendiente" (para reconciliacion
     ante crash, 09-sep-2026) vive aqui, con "intento" fijado en el
     momento del OPEN.

Solo LEE el Gist por default. Con --fix, corrige el campo "intento" de
esa UNICA entrada/registro in place (no toca ninguna otra entrada, no
borra nada) -- pide confirmacion explicita ("si") antes de escribir.

Variables de entorno requeridas: SOLO GITHUB_GIST_TOKEN y GIST_ID (no
importa el modulo completo de geometry_scheduler.py para evitar su
require_env de MASSIVE_API_KEY/TELEGRAM_* -- esto es una lectura/
correccion puntual del Gist, no necesita feed de precio ni Telegram).
La logica de _current_intento()/_attempt_pnl()/_check_attempt_reset()
esta duplicada aqui a proposito, en sync con la version ya corregida
de scheduler/geometry_scheduler.py -- mismo principio de scripts
standalone ya usado en probe_mes_open.py.

Uso:
    python scripts/verify_fix_intento_today.py           # solo verifica
    python scripts/verify_fix_intento_today.py --fix      # verifica y, si hace falta, corrige (pide confirmacion)
"""
from __future__ import annotations
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from execution.gist_store import load_log, save_log, load_state, save_state
from core.prop_firm import TOPSTEP_50K

LOG_FILE = "geometry_mes_log.json"
PENDING_FILE = "geometry_mes_pending.json"
TODAY = "2026-09-10"
EXPECTED_ENTRY_PRICE = 7610.25
EXPECTED_DIRECTION = "LONG"

PROFIT_TARGET = TOPSTEP_50K.profit_target
MLL_THRESHOLD = -TOPSTEP_50K.mll_distance


def _attempt_entries(paper_log: list, intento: int) -> list:
    return [e for e in paper_log
            if e.get("result") in ("TP", "SL", "FLATTEN") and e.get("intento", 1) == intento]


def _attempt_pnl(paper_log: list, intento: int) -> float:
    return sum(e.get("pnl", 0) for e in _attempt_entries(paper_log, intento))


def _check_attempt_reset(attempt_pnl_after: float, profit_target: float, mll_threshold: float):
    if attempt_pnl_after >= profit_target:
        return "PASE"
    if attempt_pnl_after <= mll_threshold:
        return "QUIEBRE"
    return None


def _current_intento(paper_log: list) -> int:
    """Misma logica YA CORREGIDA de geometry_scheduler.py -- ver ese
    archivo y GLITCH_RESEARCH_LOG.md para el razonamiento completo."""
    tags = [e.get("intento") for e in paper_log if e.get("intento") is not None]
    if not tags:
        return 1
    latest = max(tags)
    latest_pnl = _attempt_pnl(paper_log, latest)
    if _check_attempt_reset(latest_pnl, PROFIT_TARGET, MLL_THRESHOLD) is not None:
        return latest + 1
    return latest


def _warn_if_details_mismatch(entry: dict, source: str):
    direction = entry.get("direction")
    entry_price = entry.get("entry")
    if direction != EXPECTED_DIRECTION or entry_price != EXPECTED_ENTRY_PRICE:
        print(f"ADVERTENCIA: la entrada encontrada en {source} no coincide exactamente con lo "
              f"reportado (direction={direction!r} vs esperado {EXPECTED_DIRECTION!r}, "
              f"entry={entry_price!r} vs esperado {EXPECTED_ENTRY_PRICE!r}). "
              f"Revisar a mano antes de confiar en el resto de este reporte.\n")


def main():
    fix = "--fix" in sys.argv

    paper_log = load_log(LOG_FILE)
    prior_log = [e for e in paper_log if e.get("date", "") < TODAY]
    expected_intento = _current_intento(prior_log)

    today_closed = [e for e in paper_log if e.get("date") == TODAY]

    if len(today_closed) > 1:
        print(f"ADVERTENCIA: hay {len(today_closed)} entradas con date == {TODAY!r} en {LOG_FILE} -- "
              f"revisar manualmente, este script asume una sola.")
        for e in today_closed:
            print(f"  {e}")
        return

    if today_closed:
        source = LOG_FILE
        entry = today_closed[0]
        idx = paper_log.index(entry)
        actual_intento = entry.get("intento")
        print(f"Trade de hoy YA CERRADO -- entrada encontrada en {LOG_FILE}:")
        print(f"  {entry}\n")
        _warn_if_details_mismatch(entry, LOG_FILE)
    else:
        pending = load_state(PENDING_FILE)
        if not pending:
            print(f"No hay ninguna entrada con date == {TODAY!r} en {LOG_FILE}, "
                  f"y {PENDING_FILE} esta vacio. Nada que verificar todavia.")
            return
        if pending.get("date") != TODAY:
            print(f"{PENDING_FILE} tiene un registro, pero su date es {pending.get('date')!r}, "
                  f"no {TODAY!r} -- no parece ser el trade de hoy. Revisar a mano:")
            print(f"  {pending}")
            return
        source = PENDING_FILE
        entry = pending
        idx = None
        actual_intento = entry.get("intento")
        print(f"Trade de hoy TODAVIA ABIERTO -- registro pendiente encontrado en {PENDING_FILE}:")
        print(f"  {entry}\n")
        _warn_if_details_mismatch(entry, PENDING_FILE)

    print(f"Intento tageado en la entrada: {actual_intento!r}")
    print(f"Intento correcto (derivado del log ANTES de hoy, con la logica ya corregida): {expected_intento!r}\n")

    if actual_intento == expected_intento:
        print("OK -- ya quedo tageada correctamente (por coincidencia o porque el fix ya estaba activo "
              "cuando se escribio). No hace falta ninguna correccion.")
        return

    print(f"MAL ETIQUETADA -- dice intento={actual_intento!r}, deberia ser intento={expected_intento!r}.")

    if not fix:
        print(f"\nCorre de nuevo con --fix para corregirlo en {source} (pedira confirmacion antes de escribir).")
        return

    print(f"\nSe va a corregir SOLO el campo 'intento' de esta entrada en {source}: "
          f"{actual_intento!r} -> {expected_intento!r}. Ningun otro campo ni ninguna otra entrada se toca.")
    confirm = input("Escribir 'si' para confirmar y aplicar el cambio al Gist real: ").strip().lower()
    if confirm != "si":
        print("Cancelado -- no se escribio nada.")
        return

    corrected = {**entry, "intento": expected_intento}
    if source == LOG_FILE:
        paper_log[idx] = corrected
        save_log(LOG_FILE, paper_log)
    else:
        save_state(PENDING_FILE, corrected)

    print(f"Corregido y guardado en {source}. Entrada actualizada:")
    print(f"  {corrected}")


if __name__ == "__main__":
    main()
