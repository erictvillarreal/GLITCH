"""
Glitch — Auditoria retrospectiva: MLL trailing REAL vs. umbral fijo
desplegado, sobre el intento actual (o cualquiera que se pida) de
MGC_XFA_150K (16-sep-2026, ver GLITCH_RESEARCH_LOG.md)
==============================================================================
HALLAZGO QUE MOTIVA ESTE SCRIPT: `_check_attempt_reset()` en
scheduler/geometry_mgc_scheduler.py compara el PnL acumulado del
intento contra MLL_THRESHOLD FIJO (-$4,500 desde $0) -- nunca contra
un floor trailing real. `simulation/monte_carlo.py::TopstepMonteCarloSimulator`
(el motor YA validado y usado para las cifras de negocio) SI implementa
el floor trailing real de Topstep: el floor sube con cada nuevo maximo
de balance (EOD) alcanzado, y NUNCA baja. Esto puede hacer que el
tracking en vivo sea MAS PERMISIVO que la regla real -- una cuenta que
alcanzo un pico y luego cayo podria haber tronado bajo la regla real
sin que el codigo desplegado lo detecte.

Este script reconstruye, entrada por entrada, en orden cronologico, el
floor trailing REAL (misma logica exacta de TopstepMonteCarloSimulator.run(),
aplicada a los datos REALES en vez de a trayectorias simuladas) y lo
compara contra lo que el codigo desplegado (_check_attempt_reset con
umbral fijo) realmente decidio en cada punto.

Solo LEE el Gist -- no escribe nada, no corrige nada. Diseño para
correr AHORA, antes de decidir cualquier fix.

Variables de entorno requeridas: SOLO GITHUB_GIST_TOKEN y GIST_ID
(no importa el scheduler completo, evita su require_env de
Telegram/Massive que este audit no necesita).

Uso:
    python scripts/audit_mgc_trailing_mll_2026_09_16.py
    python scripts/audit_mgc_trailing_mll_2026_09_16.py --intento 3   (para auditar un intento especifico, no solo el actual)
"""
from __future__ import annotations
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from execution.gist_store import load_log
from core.prop_firm import TOPSTEP_150K

LOG_FILE = "geometry_mgc_log.json"
PROFIT_TARGET = TOPSTEP_150K.profit_target      # $9,000
MLL_THRESHOLD = -TOPSTEP_150K.mll_distance      # -$4,500 (umbral FIJO, el desplegado)
MLL_DISTANCE = TOPSTEP_150K.mll_distance        # $4,500 (distancia trailing real)


def _attempt_entries(paper_log, intento):
    return [e for e in paper_log
            if e.get("result") in ("TP", "SL", "FLATTEN") and e.get("intento", 1) == intento]


def _attempt_pnl(paper_log, intento):
    return sum(e.get("pnl", 0) for e in _attempt_entries(paper_log, intento))


def _check_attempt_reset_fixed(attempt_pnl_after, profit_target=PROFIT_TARGET, mll_threshold=MLL_THRESHOLD):
    """EXACTA replica de la logica desplegada en geometry_mgc_scheduler.py."""
    if attempt_pnl_after >= profit_target:
        return "PASE"
    if attempt_pnl_after <= mll_threshold:
        return "QUIEBRE"
    return None


def _current_intento(paper_log):
    tags = [e.get("intento") for e in paper_log if e.get("intento") is not None]
    if not tags:
        return 1
    latest = max(tags)
    latest_pnl = _attempt_pnl(paper_log, latest)
    if _check_attempt_reset_fixed(latest_pnl) is not None:
        return latest + 1
    return latest


def audit_intento(paper_log, intento):
    entries = sorted(
        [e for e in paper_log if e.get("intento", 1) == intento and e.get("result") in ("TP", "SL", "FLATTEN")],
        key=lambda e: e.get("date", ""),
    )
    if not entries:
        print(f"Intento {intento}: sin entradas resueltas. Nada que auditar.")
        return

    print(f"{'='*100}\nAuditoria retrospectiva -- Intento {intento} ({len(entries)} ciclos resueltos)\n{'='*100}")
    print(f"{'Fecha':<12} {'Result':<8} {'PnL':>10} {'Acumulado':>12} {'Peak(EOD)':>12} "
          f"{'Floor trailing':>15} {'Floor FIJO':>12} {'Quiebre REAL?':>15} {'Quiebre FIJO (desplegado)?':>28}")

    balance = 0.0          # PnL acumulado del intento, "balance" en terminos de attempt_pnl-desde-cero
    floor_trailing = -MLL_DISTANCE   # floor inicial, misma convencion que TopstepMonteCarloSimulator (starting_floor)
    quiebre_real_en = None
    quiebre_fijo_en = None

    for e in entries:
        balance += e.get("pnl", 0)

        # Ratchet del floor trailing REAL -- EXACTA misma logica que
        # TopstepMonteCarloSimulator.run(): floor sube si el nuevo balance
        # justifica un floor mas alto, nunca baja, se limita a 0 (el
        # "floor_lock_level" en terminos de attempt_pnl-desde-cero, ya
        # que el equivalente de "balance = starting account_size" aqui es 0).
        new_floor_candidate = balance - MLL_DISTANCE
        if new_floor_candidate > floor_trailing:
            floor_trailing = min(new_floor_candidate, 0.0)

        # Quiebre REAL: se checa DESPUES de actualizar el floor con el balance
        # de HOY -- pero como el floor solo sube en dias positivos, un dia
        # negativo nunca puede disparar su propio ratchet, asi que esto es
        # equivalente a chequear contra el floor establecido HASTA AYER.
        quiebre_real = balance <= floor_trailing
        if quiebre_real and quiebre_real_en is None:
            quiebre_real_en = e.get("date")

        quiebre_fijo = _check_attempt_reset_fixed(balance) == "QUIEBRE"
        if quiebre_fijo and quiebre_fijo_en is None:
            quiebre_fijo_en = e.get("date")

        print(f"{e.get('date',''):<12} {e.get('result',''):<8} {e.get('pnl',0):>10,.2f} {balance:>12,.2f} "
              f"{max(0.0, balance):>12,.2f} {floor_trailing:>15,.2f} {MLL_THRESHOLD:>12,.2f} "
              f"{'SI <---' if quiebre_real else 'no':>15} {'SI <---' if quiebre_fijo else 'no':>28}")

    print(f"\nBalance final del intento: ${balance:,.2f}")
    print(f"Floor trailing REAL final: ${floor_trailing:,.2f}  (margen real restante: ${balance - floor_trailing:,.2f})")
    print(f"Floor FIJO desplegado:     ${MLL_THRESHOLD:,.2f}  (margen fijo restante: ${balance - MLL_THRESHOLD:,.2f})")

    if quiebre_real_en:
        print(f"\n*** BAJO LA REGLA REAL DE TOPSTEP, ESTE INTENTO DEBIO MARCARSE QUIEBRE EL {quiebre_real_en} ***")
    else:
        print("\nBajo la regla REAL de Topstep (trailing), este intento NUNCA cruzo el floor -- sigue activo.")

    if quiebre_fijo_en:
        print(f"El codigo DESPLEGADO (umbral fijo) marco/marcaria QUIEBRE el {quiebre_fijo_en}.")
    else:
        print("El codigo DESPLEGADO (umbral fijo) NUNCA marco QUIEBRE -- consistente con el estado 'activa' reportado.")

    if quiebre_real_en and not quiebre_fijo_en:
        print("\n>>> DISCREPANCIA CONFIRMADA: la regla real habria terminado este intento, "
              "el codigo desplegado (mas permisivo) lo mantuvo activo -- ver research log para el fix propuesto.")
    elif quiebre_real_en and quiebre_fijo_en and quiebre_real_en != quiebre_fijo_en:
        print(f"\n>>> Ambas reglas detectan QUIEBRE pero en fechas DISTINTAS "
              f"(real: {quiebre_real_en} vs fijo: {quiebre_fijo_en}) -- la real dispara mas temprano.")
    elif not quiebre_real_en and not quiebre_fijo_en:
        print("\nSin discrepancia en este intento -- ambas reglas coinciden en que sigue activo.")


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--intento", type=int, default=None, help="Intento especifico a auditar (default: el actual)")
    parser.add_argument("--all", action="store_true", help="Auditar TODOS los intentos encontrados en el log, no solo uno")
    args = parser.parse_args()

    paper_log = load_log(LOG_FILE)
    if not paper_log:
        print(f"{LOG_FILE} esta vacio o no se pudo leer. Nada que auditar.")
        return

    if args.all:
        intentos = sorted({e.get("intento") for e in paper_log if e.get("intento") is not None})
        for intento in intentos:
            audit_intento(paper_log, intento)
            print()
    else:
        intento = args.intento if args.intento is not None else _current_intento(paper_log)
        print(f"Intento actual detectado (o especificado): {intento}\n")
        audit_intento(paper_log, intento)


if __name__ == "__main__":
    main()
