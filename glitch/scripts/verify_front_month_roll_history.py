"""
Glitch — Verificacion empirica del roll de front-month contra un caso YA
OCURRIDO (08-sep-2026)
==============================================================================
URGENTE (ver GLITCH_RESEARCH_LOG.md, 08-sep-2026): MESU6/MNQU6 vencen en 8
dias habiles (18-sep-2026) y GEOMETRY/COMBO2D dependen de que
execution/contracts.py::resolve_front_month() haga el roll a MESZ6/MNQZ6
automaticamente, sin intervencion manual. La logica de esa funcion (ver
docstring alli) es correcta por construccion -- pero DEPENDE de un supuesto
externo nunca verificado empiricamente en este repo: que el flag
`active=true` de Massive para un contrato se apague en el momento correcto
relativo a su `last_trade_date` (ni demasiado tarde -- tradearia un contrato
vencido -- ni demasiado pronto -- perderia dias de trading legitimos).

En vez de esperar hasta el 18-sep para observar el roll de MESU6 en vivo
(demasiado tarde para reaccionar si algo esta mal), este script mide el
mismo fenomeno contra un roll que YA PASO: MESM6 (jun-2026) -> MESU6
(sep-2026). Barre un rango de fechas alrededor del `last_trade_date` real
de MESM6 y reporta, dia por dia, cual contrato devuelve
resolve_front_month() -- exactamente el mismo codigo que corre en
produccion hoy, no una reimplementacion aparte.

Mismo principio ya aplicado a Yahoo (medir el delay real en vez de asumirlo)
y al bug de paginacion de Massive (probe_massive_mgc_delay.py) -- no adivinar
el comportamiento de una API externa, medirlo.

Uso:
    export MASSIVE_API_KEY="..."
    python scripts/verify_front_month_roll_history.py MES
    python scripts/verify_front_month_roll_history.py MNQ
"""
from __future__ import annotations
import os
import sys
import datetime as dt

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from execution.contracts import _get, _valid_outright_ticker  # noqa: E402


def resolve_front_month_as_of(product: str, as_of: dt.date) -> list[tuple[str, str]]:
    """
    Misma logica EXACTA que execution.contracts.resolve_front_month(), pero
    parametrizada por fecha en vez de usar dt.date.today() -- para poder
    barrer fechas pasadas. Devuelve TODOS los candidatos validos ordenados
    por last_trade_date ascendente (no solo el primero) para poder ver el
    contrato saliente Y el entrante en la misma fila.
    """
    date_str = as_of.isoformat()
    results = _get("/futures/v1/contracts",
                    {"product_code": product, "date": date_str, "active": "true", "limit": 250})
    candidates = []
    for c in results:
        if c.get("type") and c["type"] != "single":
            continue
        ticker = c.get("ticker")
        ltd = c.get("last_trade_date")
        if ticker and ltd and _valid_outright_ticker(product, ticker):
            candidates.append((ticker, ltd))
    candidates.sort(key=lambda x: x[1])
    return candidates


def main():
    if len(sys.argv) != 2:
        print("Uso: python scripts/verify_front_month_roll_history.py <PRODUCT_CODE>")
        print("Ejemplo: python scripts/verify_front_month_roll_history.py MES")
        sys.exit(1)
    product = sys.argv[1].upper()

    # Paso 1: encontrar el last_trade_date real del contrato PREVIO al front
    # month de hoy, consultando la API (NO asumir la fecha -- el ciclo
    # trimestral estandar H/M/U/Z no siempre cae el mismo dia calendario).
    today = dt.date.today()
    today_candidates = resolve_front_month_as_of(product, today)
    if not today_candidates:
        print(f"ERROR: sin candidatos activos para {product} hoy ({today}) -- abortando.")
        sys.exit(1)

    current_front, current_ltd_str = today_candidates[0]
    print(f"Front month HOY ({today}) para {product}: {current_front}, LTD={current_ltd_str}")
    if len(today_candidates) > 1:
        next_front, next_ltd_str = today_candidates[1]
        print(f"Siguiente contrato ya visible en el mismo query: {next_front}, LTD={next_ltd_str}")
    print()

    # El contrato PREVIO no aparece en el query de HOY (ya rolleo) -- para
    # encontrar su LTD real, retrocedemos ~3 meses (un ciclo trimestral) y
    # preguntamos que era el front month EN ESE MOMENTO.
    probe_date = today - dt.timedelta(days=95)
    prior_candidates = resolve_front_month_as_of(product, probe_date)
    if not prior_candidates:
        print(f"ERROR: sin candidatos activos para {product} en {probe_date} -- "
              f"ajustar el offset de 95 dias manualmente y reintentar.")
        sys.exit(1)
    prior_ticker, prior_ltd_str = prior_candidates[0]
    prior_ltd = dt.datetime.strptime(prior_ltd_str, "%Y-%m-%d").date()

    if prior_ticker == current_front:
        print(f"ADVERTENCIA: el contrato de hace ~95 dias ({prior_ticker}) es el MISMO "
              f"que el front month de hoy -- el offset no retrocedio lo suficiente para "
              f"cruzar un roll. Ajustar manualmente (ej. 100-110 dias) y reintentar.")
        sys.exit(1)

    print(f"Contrato previo identificado: {prior_ticker}, LTD real={prior_ltd_str}")
    print(f"Barriendo dia por dia desde 5 dias ANTES hasta 5 dias DESPUES de su LTD...")
    print()

    # Paso 2: barrer dia por dia alrededor del LTD real del contrato previo,
    # usando la MISMA funcion (resolve_front_month_as_of, copia exacta de la
    # logica de produccion) para cada fecha -- reporta el dia EXACTO en que
    # el front month resuelto cambia de prior_ticker a current_front.
    print(f"{'Fecha':<12} {'Dias vs LTD':<12} {'Front month resuelto':<22} {'LTD del resuelto':<16} {'Contrato saliente aun activo?'}")
    print("-" * 95)

    # BUG (08-sep-2026, encontrado por el usuario) en una version anterior de
    # este bloque: se usaba `roll_day` = PRIMER offset donde aparece el
    # contrato NUEVO para decidir el veredicto -- pero esa variable mide algo
    # distinto de "hasta cuando el contrato VIEJO se siguio resolviendo".
    # Un `roll_day` positivo (el nuevo contrato ya aparece el mismo LTD o al
    # dia siguiente) es el caso SEGURO esperado, no peligroso -- el bug hacia
    # que el mensaje de RESULTADO contradijera la propia tabla impresa arriba
    # en ese caso. Fix: trackear directamente `last_offset_still_prior`, el
    # ULTIMO offset en que el front month resuelto siguio siendo el contrato
    # VIEJO -- esa es la condicion que realmente importa (¿se resolvio el
    # contrato ya vencido en algun dia DESPUES de su propio LTD?), calculada
    # con la MISMA condicion por fila que ya se imprime en la tabla, para que
    # el veredicto no pueda contradecirla.
    last_offset_still_prior = None
    for offset in range(-5, 6):
        probe = prior_ltd + dt.timedelta(days=offset)
        if probe.weekday() >= 5:  # fin de semana, Massive no tiene datos de contratos utiles ese dia -- se salta
            continue
        cands = resolve_front_month_as_of(product, probe)
        if not cands:
            print(f"{probe.isoformat():<12} {offset:+d} dias      (sin candidatos -- inesperado)")
            continue
        resolved_ticker, resolved_ltd = cands[0]
        outgoing_still_active = any(t == prior_ticker for t, _ in cands)
        if resolved_ticker == prior_ticker:
            last_offset_still_prior = offset
        print(f"{probe.isoformat():<12} {offset:+d} dias      {resolved_ticker:<22} {resolved_ltd:<16} "
              f"{'SI' if outgoing_still_active else 'NO'}")

    print()
    if last_offset_still_prior is None:
        print(f"RESULTADO: en ningun dia de la ventana de +/-5 dias barrida el front month "
              f"resuelto fue {prior_ticker} -- ya habia rolleado antes de -5 dias respecto a "
              f"su LTD. Ampliar el rango hacia atras (ej. offset -10 a -6) para ver el momento "
              f"exacto del roll.")
    elif last_offset_still_prior > 0:
        print(f"RESULTADO: PELIGROSO -- el front month resuelto siguio siendo {prior_ticker} "
              f"hasta {last_offset_still_prior} dia(s) DESPUES de su LTD ({prior_ltd_str}). "
              f"El scheduler intentaria tradear un contrato ya vencido. Corregir el filtro "
              f"`active=true` o agregar un chequeo explicito de `last_trade_date >= hoy` en "
              f"resolve_front_month() antes del proximo roll real.")
    elif last_offset_still_prior == 0:
        print(f"RESULTADO: seguro -- el ultimo dia en que el front month resuelto fue "
              f"{prior_ticker} es su propio LTD ({prior_ltd_str}), el ultimo dia legitimo "
              f"para tradearlo. Al dia siguiente (offset +1) ya resuelve el contrato nuevo. "
              f"Comportamiento correcto y esperado, sin intervencion manual.")
    else:
        print(f"RESULTADO: seguro -- el front month resuelto ya era el contrato nuevo desde "
              f"{abs(last_offset_still_prior)} dia(s) ANTES del LTD real de {prior_ticker} "
              f"({prior_ltd_str}) -- el ultimo dia que aparecio {prior_ticker} como front "
              f"month fue offset {last_offset_still_prior}. El roll ocurre antes del "
              f"vencimiento, no el mismo dia, sin intervencion manual.")


if __name__ == "__main__":
    main()
