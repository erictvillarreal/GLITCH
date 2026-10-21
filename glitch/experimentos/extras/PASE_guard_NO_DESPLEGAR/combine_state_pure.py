"""PROPUESTA -- NO DESPLEGAR (NEEDS HUMAN REVIEW, CLAUDE.md regla 4: define cuando el sistema da un Combine por PASADO o QUEBRADO).

Estado oficial de un Combine 50K a partir de los P&L diarios NETOS de comision (como los muestra TopstepX). Reglas leidas el 20-oct-2026 en help.topstep.com/8284208 y /8284197
(ver experimentos/xfa/RULEBOOK_XFA.md): meta $3,000; mejor dia <= 55 % de la ganancia total, si no el objetivo sube a mejor_dia / 0.55 (los dias perdedores NO reinician el mejor dia);
se puede pasar en 2 dias como minimo; MLL $2,000 sobre el balance de CIERRE (se monitorea en tiempo real) y se fija en el balance inicial al alcanzarlo.

Por que existe: geometry_scheduler.py::_check_attempt_reset compara el P&L ACUMULADO DEL LOG (bruto de comisiones: pi_executor._compute_pnl) contra $3,000 sin mirar la consistencia ni la comision;
podria declarar PASE antes (o despues) que Topstep, y entonces el sizing finish-line y el conteo de intentos se desincronizan de la cuenta real.
"""
from __future__ import annotations

PROFIT_TARGET = 3000.0
MLL = 2000.0
CONSISTENCY = 0.55
MIN_DAYS = 2


def combine_status(daily_net: list[float]) -> dict:
    """daily_net: P&L neto de cada dia operado del intento, en orden. Devuelve profit, mejor dia, objetivo vigente, faltante, piso y estado ('ACTIVO', 'PASE', 'QUIEBRE')."""
    bal = 0.0; peak = 0.0; best = 0.0
    for d in daily_net:
        bal += d; peak = max(peak, bal); best = max(best, d)
        floor = min(peak - MLL, 0.0)
        if bal <= floor + 1e-9:
            return dict(profit=bal, best_day=best, target=_target(best), need=_target(best) - bal, floor=floor, status="QUIEBRE", days=len(daily_net))
    target = _target(best)
    floor = min(peak - MLL, 0.0)
    status = "PASE" if (bal >= target - 1e-9 and len(daily_net) >= MIN_DAYS) else "ACTIVO"
    return dict(profit=bal, best_day=best, target=target, need=max(target - bal, 0.0), floor=floor, status=status, days=len(daily_net))


def _target(best_day: float) -> float:
    return max(PROFIT_TARGET, best_day / CONSISTENCY) if best_day > 0 else PROFIT_TARGET
