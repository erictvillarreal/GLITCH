"""PROPUESTA -- NO DESPLEGAR (NEEDS HUMAN REVIEW, CLAUDE.md regla 4: toca el registro de resultados del intento).

Deteccion DETERMINISTA de liquidacion por MLL (cuenta terminada por TopstepX) cuando el Pi ve "ambas patas ausentes y
cuenta plana" (hoy: result="UNKNOWN", pnl 0, el intento no avanza -- caso real del 19-oct-2026).

Evidencia aceptada (ninguna requiere un endpoint nuevo; solo Account/search, que el Pi ya usa en _resolve_account_id):
  E1  la cuenta operada YA NO aparece entre las cuentas activas pero la lista NO esta vacia (descarta un glitch de la API
      que devuelva []), o
  E2  la cuenta aparece con canTrade == False.
Con E1 o E2 -> "LIQ". Si solo hay una pista debil (balance <= piso + tolerancia) -> "UNKNOWN" + liq_suspected (alerta fuerte,
sigue needs_review). Sin pistas -> "UNKNOWN" como hoy. Nunca se infiere LIQ solo por el balance ni solo por tiempo.

P&L de un LIQ: SIEMPRE estimado y marcado (pnl_estimated). Se fija en  piso_relativo - pnl_acumulado_previo  para que el
acumulado del intento quede EXACTAMENTE en el piso (la cuenta termina en el piso: el MLL liquida al tocarlo) y
_check_attempt_reset() devuelva "QUIEBRE". Si la señal no trae esos dos campos, no se convierte a LIQ (queda UNKNOWN).

Campos Account/search que se leen (`id`, `balance`, `canTrade`): segun la documentacion publica de ProjectX; `canTrade`
NO VERIFICADO en vivo contra esta cuenta -- por eso E2 es solo una de dos vias y los tests usan registros sinteticos.
"""
from __future__ import annotations

from typing import Optional

LIQ_BALANCE_TOLERANCE_USD = 50.0


def _find(accounts, account_id):
    for a in accounts or []:
        if a.get("id") == account_id:
            return a
    return None


def classify_unknown_exit(*, account_id, active_accounts: Optional[list], all_accounts: Optional[list] = None,
                          floor_abs: Optional[float] = None, tol_usd: float = LIQ_BALANCE_TOLERANCE_USD) -> dict:
    """Devuelve {"result": "LIQ"|"UNKNOWN", "evidence": str|None, "suspected": bool}. Pura: no toca la red."""
    if active_accounts is None:
        return {"result": "UNKNOWN", "evidence": None, "suspected": False}
    rec = _find(active_accounts, account_id)
    if rec is None and active_accounts:
        return {"result": "LIQ", "evidence": "E1: la cuenta ya no figura entre las cuentas activas de Account/search", "suspected": False}
    if rec is None:
        # lista vacia: puede ser un glitch de la API o que esta era la unica cuenta. Se consulta el listado completo.
        rec = _find(all_accounts, account_id)
        if rec is None:
            return {"result": "UNKNOWN", "evidence": None, "suspected": True}   # ambiguo: se alerta, no se clasifica
    if rec.get("canTrade") is False:
        return {"result": "LIQ", "evidence": "E2: canTrade=false en Account/search", "suspected": False}
    bal = rec.get("balance")
    if floor_abs is not None and isinstance(bal, (int, float)) and not isinstance(bal, bool) and bal <= floor_abs + tol_usd:
        return {"result": "UNKNOWN", "evidence": f"balance {bal:,.2f} <= piso {floor_abs:,.2f} + {tol_usd:.0f}, pero la cuenta sigue operable",
                "suspected": True}
    return {"result": "UNKNOWN", "evidence": None, "suspected": False}


def liq_pnl(attempt_pnl_before, attempt_floor) -> Optional[float]:
    """P&L estimado del dia de la liquidacion (<= 0): deja el acumulado del intento exactamente en el piso. None si faltan datos."""
    for v in (attempt_pnl_before, attempt_floor):
        if v is None or isinstance(v, bool) or not isinstance(v, (int, float)):
            return None
    return round(float(attempt_floor) - float(attempt_pnl_before), 2)
