"""
DD PPP -- simulacion bar-a-bar (5min) de la geometria MGC_XFA_150K
(SL=TP=364 ticks, alternar, nc=6, entrada real 7:13 CT) con dos
variantes de proteccion de ganancia no realizada, sobre los 2 años
reales de datos ya validados (ventana horaria corregida).

A diferencia de scripts/camino_b_grid.py::_label_fixed_ticks (que solo
devuelve la etiqueta FINAL de cada trade), esto camina barra por barra
para poder detectar el cruce del umbral de ganancia no realizada en
CUALQUIER punto del camino, no solo en la resolucion -- necesario para
este experimento especifico (el caso motivador es exactamente un pico
intermedio que se erosiona antes de la resolucion final).

SUPUESTOS EXPLICITOS (declarados, no escondidos):
1. Ejecucion EXACTA al precio implicado por el umbral, sin slippage
   adicional -- misma convencion de simplificacion que el resto del
   backtest de este proyecto (la friccion se estudia por separado, ver
   Fase A del due diligence, Test 1).
2. El cruce del umbral se chequea usando el extremo FAVORABLE de cada
   barra (high para LONG, low para SHORT) -- misma fuente de datos
   (high/low) que ya usa _label_fixed_ticks para detectar toques de
   TP/SL, no una fuente de informacion nueva.
3. Dentro de una misma barra de 5min, el cruce del umbral de proteccion
   se evalua ANTES que un posible toque de TP/SL completo -- justificado
   porque el scheduler real en produccion poll-ea cada 60s (mucho mas
   fino que 5min), asi que reaccionaria al umbral de proteccion antes
   de que un TP completo se alcance dentro de la misma ventana de 5min,
   salvo un gap extremo (mayor al TP completo, $364/contrato en oro,
   dentro de 5min) -- no observado en los datos reales de este dataset.
4. Comision: se asume el mismo commission_roundturn total ($1.92 x nc)
   sin importar si el cierre se divide en 1 o 2 fills (Variante A) --
   la comision de Topstep/Massive es por contrato-round-turn, no por
   evento de transaccion. Declarado explicitamente, no verificado
   contra una tarifa real de broker para este caso especifico.
5. Umbral SIEMPRE menor al TP completo por contrato ($364) en el rango
   pedido ($800-$1,700 a nc=6 => $133-$283/contrato) -- confirmado
   antes de correr nada, asi que la proteccion siempre puede disparar
   antes de un TP completo en terminos de distancia de precio.
"""
from __future__ import annotations
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd

from strategies.geometry_pure import SPECS, CANDIDATES, trading_day_index, decide_side

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data_cache")
MGC_PATH = os.path.join(DATA_DIR, "mgc_5min_2y_corrected_window.parquet")

MGC_XFA = CANDIDATES["MGC_XFA_150K"]
SPEC = SPECS["MGC"]
NC = MGC_XFA.nc                       # 6
SL_TICKS = MGC_XFA.sl_ticks           # 364
TP_TICKS = MGC_XFA.tp_ticks           # 364
TICK_SIZE = SPEC.tick_size            # 0.10
TICK_VALUE = SPEC.tick_value_usd      # 1.00
USD_PER_POINT_PER_CONTRACT = TICK_VALUE / TICK_SIZE  # $10/punto/contrato
COMMISSION_RT = SPEC.commission_roundturn  # 1.92, por contrato

ENTRY_HOUR, ENTRY_MINUTE = 7, 13      # confirmado en geometry_mgc_scheduler.py
FLATTEN_HOUR, FLATTEN_MINUTE = 14, 30  # idem, FLATTEN_HOUR/FLATTEN_MINUTE reales


def _load_mgc_with_session_cols():
    df = pd.read_parquet(MGC_PATH)
    local = df.copy()
    local.index = local.index.tz_convert("America/Chicago")
    local["session_date"] = local.index.date
    local["minute_of_day"] = local.index.hour * 60 + local.index.minute
    return local


def simulate_trade(bars_today: pd.DataFrame, entry_pos_in_today: int, side: int,
                    threshold: float | None, variant: str | None) -> dict:
    """
    bars_today: barras de LA SESION de hoy (ya filtradas), ordenadas.
    entry_pos_in_today: indice (posicional, dentro de bars_today) de la
    barra de entrada -- el precio de entrada es su 'close'.
    threshold/variant: None,None para el baseline SIN proteccion.

    Devuelve dict con: result (TP/SL/FLATTEN), pnl_per_contract_total
    (a NC contratos, ya neto de comision), triggered (bool, si la
    proteccion disparo), trigger_price (o None).
    """
    entry_price = float(bars_today.iloc[entry_pos_in_today]["close"])
    sl_pts = SL_TICKS * TICK_SIZE
    tp_pts = TP_TICKS * TICK_SIZE
    tp_price = entry_price + side * tp_pts
    sl_price = entry_price - side * sl_pts

    n = len(bars_today)
    triggered = False
    trigger_price = None
    active_nc = NC

    for j in range(entry_pos_in_today + 1, n):
        bar = bars_today.iloc[j]
        past_flatten = bar["minute_of_day"] >= (FLATTEN_HOUR * 60 + FLATTEN_MINUTE)

        if not triggered and threshold is not None:
            favorable = bar["high"] if side == 1 else bar["low"]
            unrealized = (favorable - entry_price) * side * USD_PER_POINT_PER_CONTRACT * NC
            if unrealized >= threshold:
                triggered = True
                trigger_price = entry_price + side * (threshold / (USD_PER_POINT_PER_CONTRACT * NC))
                realized_partial = threshold * 0.5  # Variante A: mitad de los contratos, mitad del $ total
                if variant == "full":
                    exit_price = trigger_price
                    pnl_total = threshold - COMMISSION_RT * NC
                    return {"result": "PROTECTED_FULL", "pnl_per_contract_total": pnl_total,
                            "triggered": True, "trigger_price": trigger_price, "exit_price": exit_price}
                else:
                    active_nc = NC // 2  # Variante A: la mitad sigue corriendo
                    # continua el loop con active_nc reducido -- el resto se resuelve abajo

        # Chequeo TP/SL de la barra (high/low), MISMA convencion
        # conservadora (win_first=False) que _label_fixed_ticks: si
        # ambos se tocan en la misma barra ambigua, se asume que el SL
        # llego primero.
        high, low = bar["high"], bar["low"]
        if side == 1:
            win_touch, loss_touch = high >= tp_price, low <= sl_price
        else:
            win_touch, loss_touch = low <= tp_price, high >= sl_price

        if win_touch or loss_touch:
            if win_touch and loss_touch:
                exit_price, result = sl_price, "SL"
            elif win_touch:
                exit_price, result = tp_price, "TP"
            else:
                exit_price, result = sl_price, "SL"
            pnl_remaining_per_contract = (exit_price - entry_price) * side * USD_PER_POINT_PER_CONTRACT
            if triggered:  # Variante A ya disparo -- combinar con lo ya asegurado
                pnl_total = realized_partial + pnl_remaining_per_contract * active_nc - COMMISSION_RT * NC
                return {"result": f"PARTIAL_THEN_{result}", "pnl_per_contract_total": pnl_total,
                        "triggered": True, "trigger_price": trigger_price, "exit_price": exit_price}
            else:
                pnl_total = pnl_remaining_per_contract * NC - COMMISSION_RT * NC
                return {"result": result, "pnl_per_contract_total": pnl_total,
                        "triggered": False, "trigger_price": None, "exit_price": exit_price}

        if past_flatten:
            exit_price = float(bar["close"])
            pnl_remaining_per_contract = (exit_price - entry_price) * side * USD_PER_POINT_PER_CONTRACT
            if triggered:
                pnl_total = realized_partial + pnl_remaining_per_contract * active_nc - COMMISSION_RT * NC
                return {"result": "PARTIAL_THEN_FLATTEN", "pnl_per_contract_total": pnl_total,
                        "triggered": True, "trigger_price": trigger_price, "exit_price": exit_price}
            else:
                pnl_total = pnl_remaining_per_contract * NC - COMMISSION_RT * NC
                return {"result": "FLATTEN", "pnl_per_contract_total": pnl_total,
                        "triggered": False, "trigger_price": None, "exit_price": exit_price}

    # Se acabaron las barras del dia sin resolver -- usar el ultimo close disponible (mismo criterio que flatten)
    exit_price = float(bars_today.iloc[-1]["close"])
    pnl_remaining_per_contract = (exit_price - entry_price) * side * USD_PER_POINT_PER_CONTRACT
    if triggered:
        pnl_total = realized_partial + pnl_remaining_per_contract * active_nc - COMMISSION_RT * NC
    else:
        pnl_total = pnl_remaining_per_contract * NC - COMMISSION_RT * NC
    return {"result": "FLATTEN_EOD", "pnl_per_contract_total": pnl_total,
            "triggered": triggered, "trigger_price": trigger_price, "exit_price": exit_price}


def run_all_trades(threshold: float | None, variant: str | None) -> pd.DataFrame:
    """
    Agrupa por sesion directamente (en vez de traducir posiciones
    globales de session_open_bar_positions() a posiciones locales por
    dia, mas propenso a errores) -- misma logica exacta de esa funcion
    (primera barra con minute_of_day >= entry_hour:entry_minute),
    aplicada dentro de cada grupo ya indexado posicionalmente."""
    data = _load_mgc_with_session_cols()
    entry_cutoff = ENTRY_HOUR * 60 + ENTRY_MINUTE

    rows = []
    for session_date, bars_today in data.groupby("session_date", sort=True):
        bars_today = bars_today.reset_index(drop=True)
        after_open = bars_today.index[bars_today["minute_of_day"] >= entry_cutoff]
        if len(after_open) == 0:
            continue  # sesion sin barras despues de la hora de entrada (rara, ej. dia corto)
        entry_pos_in_today = int(after_open[0])

        side = decide_side(trading_day_index(session_date), MGC_XFA.direction)
        r = simulate_trade(bars_today, entry_pos_in_today, side, threshold, variant)
        r["date"] = str(session_date)
        r["side"] = side
        rows.append(r)

    return pd.DataFrame(rows).sort_values("date").reset_index(drop=True)


if __name__ == "__main__":
    print("Corriendo baseline (sin proteccion) para validar contra el WR ya establecido (49.40%)...")
    base = run_all_trades(threshold=None, variant=None)
    resolved = base[base["result"].isin(["TP", "SL", "FLATTEN", "FLATTEN_EOD"])]
    # FLATTEN_EOD no deberia ocurrir nunca en la practica (siempre hay flatten a las 14:30) -- confirmar
    n_flatten_eod = (base["result"] == "FLATTEN_EOD").sum()
    print(f"N trades: {len(base)}  FLATTEN_EOD (deberia ser 0): {n_flatten_eod}")
    n_tp = (base["result"] == "TP").sum()
    n_sl = (base["result"] == "SL").sum()
    n_flat = (base["result"] == "FLATTEN").sum()
    print(f"TP={n_tp}  SL={n_sl}  FLATTEN={n_flat}")
    wr_cond = n_tp / (n_tp + n_sl) if (n_tp + n_sl) > 0 else float("nan")
    print(f"WR condicional (TP/(TP+SL)): {wr_cond:.4f}  (referencia ya validada: 0.4940)")
    avg_pnl = base["pnl_per_contract_total"].mean()
    print(f"PnL promedio por trade (nc={NC}, neto de comision): ${avg_pnl:,.2f}")
