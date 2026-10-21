"""PROPUESTA — NO DESPLEGAR (NEEDS HUMAN REVIEW, CLAUDE.md regla 4: decide el lado de una entrada con capital real).
Kill-switch DETERMINISTA para una regla direccional candidata (G4 del encargo E). Funcion pura: sin estado oculto, sin E/S, sin LLM (regla 1).
Vuelve a `alternate` cuando (a) el WR movil de las ultimas `window` decisiones es < `wr_floor`, o (b) la señal de E1 cambio de signo, o (c) aun no hay `window` decisiones.
Re-armar la regla es SIEMPRE una decision humana (esta funcion no lo hace)."""
from __future__ import annotations
from typing import Sequence

RULE, ALTERNATE = "rule", "alternate"


def killswitch(decided: Sequence[int], signal_flipped: bool = False, window: int = 60, wr_floor: float = 0.45) -> str:
    """decided: resultados 1 (TP) / 0 (SL) de las decisiones YA CERRADAS en orden cronologico (los FLATTEN no entran). Devuelve 'rule' o 'alternate'."""
    if signal_flipped or window <= 0:
        return ALTERNATE
    if len(decided) < window:
        return ALTERNATE
    last = decided[-window:]
    if any(x not in (0, 1) for x in last):
        raise ValueError("decided solo admite 0/1")
    return ALTERNATE if sum(last) / window < wr_floor else RULE
