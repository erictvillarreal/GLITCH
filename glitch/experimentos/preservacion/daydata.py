"""Datos y mecanica de un dia para la Parte A (M2: replay de dias reales).

Fuente de datos: glitch/data_cache/mes_5min_2y.parquet (barras de 5 min RTH, 2024-08-26 -> 2026-08-25,
515 dias CT). Se usan solo los dias COMPLETOS (barras 9:30..14:25 CT presentes); el resto se descarta y
se cuenta (cierres anticipados y huecos de datos).

Convenciones (todas tomadas de scheduler/geometry_scheduler.py y pi/pi_executor.py, ver REPORTE_A):
  * referencia = close de la barra que empieza 9:30 CT (la ultima barra completa en la compuerta de entrada
    9:35 CT; el Pi usa el close de la ultima barra de 15 min -- aqui se aproxima con la barra de 5 min).
  * TP/SL se anclan a la REFERENCIA; el fill sufre slippage adverso (entra peor que la referencia).
  * liquidacion por MLL en tiempo real: mark-to-market con el peor tick de cada barra (conservador).
  * flatten 14:30 CT al close de la barra que empieza 14:25.
  * dentro de una barra el orden de eventos es DESCONOCIDO: orden 'adverse' (default, conservador:
    el evento adverso se asume primero) u orden 'ohlc' (ruta O->L->H->C si cierra arriba, O->H->L->C si no).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

TICK = 0.25
TICK_USD = 1.25
FEE_RT = 1.22
SL_TICKS = 100
TP_TICKS = 32
DEFAULT_PARQUET = "/Users/anelvillarreal/Desktop/Kito/GLITCH-main.orphaned-2026-08-26/glitch/data_cache/mes_5min_2y.parquet"

REF_BAR_HM = 9 * 60 + 30     # barra cuyo close es la referencia
LAST_BAR_HM = 14 * 60 + 25   # ultima barra antes del flatten 14:30 CT
BAR_HMS = list(range(9 * 60 + 35, 14 * 60 + 30, 5))   # barras de monitoreo 9:35 .. 14:25 -> 59 barras


class DayData:
    """Arreglos por dia en ticks respecto a la referencia. Forma (D, K) con K=59 barras."""

    def __init__(self, dates, ref, op, hi, lo, cl, dropped):
        self.dates = list(dates)
        self.ref = ref          # (D,) precio de referencia
        self.op, self.hi, self.lo, self.cl = op, hi, lo, cl   # (D, K) en ticks respecto a ref
        self.dropped = dropped  # lista (fecha, motivo)
        self.D, self.K = op.shape

    def side_view(self, side: int, drift: float = 0.0):
        """Vista signada por el lado: u = side * x. Devuelve fav, adv, close, adverse_first (todos (D,K)).
        drift: deriva A FAVOR del lado, en ticks por dia (M3), repartida linealmente en el dia."""
        if side == 1:
            fav, adv = self.hi, self.lo
        else:
            fav, adv = -self.lo, -self.hi
        cl = side * self.cl
        if drift:
            f = (np.arange(self.K) + 1.0) / self.K
            fav = fav + drift * f; adv = adv + drift * f; cl = cl + drift * f
        # orden OHLC: barra alcista (cl>=op) -> precio pasa por el minimo primero; barra bajista -> por el maximo primero
        up_bar = self.cl >= self.op
        # long: adverso = minimo, llega primero en barra alcista; short: adverso = maximo, llega primero en barra bajista
        adverse_first_ohlc = up_bar if side == 1 else ~up_bar
        return fav, adv, cl, adverse_first_ohlc


def load_days(path: str = DEFAULT_PARQUET, ref_hm: int = REF_BAR_HM, last_hm: int = LAST_BAR_HM) -> DayData:
    """ref_hm = minuto-CT de INICIO de la barra cuyo close es la referencia; last_hm = inicio de la ultima barra monitoreada (flatten a su close).
    Los valores por defecto replican scheduler/Pi (ref 9:30, flatten 14:30 CT). Otros valores solo para validacion cruzada contra el motor de caja (entrada 9:45)."""
    bar_hms = list(range(ref_hm + 5, last_hm + 5, 5))
    d = pd.read_parquet(path).tz_convert("America/Chicago")
    d["date"] = d.index.date
    d["hm"] = d.index.hour * 60 + d.index.minute
    need = set([ref_hm] + bar_hms)
    dates, refs, ops, his, los, cls, dropped = [], [], [], [], [], [], []
    for dt, x in d.groupby("date"):
        if x.contract.nunique() > 1:
            dropped.append((dt, "cambio de contrato dentro del dia")); continue
        have = set(x.hm)
        if not need.issubset(have):
            dropped.append((dt, f"dia incompleto ({len(x)} barras, ultima {int(x.hm.max()) // 60}:{int(x.hm.max()) % 60:02d} CT)")); continue
        x = x.set_index("hm")
        ref = float(x.loc[ref_hm, "close"])
        b = x.loc[bar_hms]
        dates.append(dt); refs.append(ref)
        ops.append(((b.open - ref) / TICK).to_numpy()); his.append(((b.high - ref) / TICK).to_numpy())
        los.append(((b.low - ref) / TICK).to_numpy()); cls.append(((b.close - ref) / TICK).to_numpy())
    return DayData(dates, np.array(refs), np.array(ops), np.array(his), np.array(los), np.array(cls), dropped)


def sim_day(dd: DayData, side: int, nc: int, cushion: float, slip: float = 1.0, exit_slip: float = 0.0,
            sl: int = SL_TICKS, tp: int = TP_TICKS, order: str = "adverse", fee: float = FEE_RT, drift: float = 0.0):
    """Simula el engine un dia para TODOS los dias de dd a la vez.

    Devuelve (kind, pnl) arrays (D,). kind: 0=TP, 1=SL, 2=LIQ (cuenta liquidada), 3=FLATTEN.
    pnl = P&L NETO de comisiones en $ (en LIQ: -cushion exacto, la cuenta queda en el piso).
    slip: ticks de slippage de entrada (adverso). exit_slip: ticks extra al salir por SL (gap a traves del stop).
    """
    fav, adv, cl, adv_first_ohlc = dd.side_view(side, drift)
    D, K = fav.shape
    if nc <= 0:
        return np.full(D, 3), np.zeros(D)
    liq_ticks = cushion / (nc * TICK_USD)               # perdida en ticks (desde el fill) que toca el piso
    liq_trig = -(liq_ticks - slip)                      # nivel de adv (desde la referencia) donde se toca el piso
    cum_adv = np.minimum.accumulate(adv, axis=1)
    BIG = 10 ** 6
    def first_idx(mask):
        any_ = mask.any(axis=1)
        return np.where(any_, mask.argmax(axis=1), BIG)
    # eventos: el que ocurre primero; adverso gana empates dentro de la barra (orden 'adverse') o segun OHLC
    # El stop (-sl) se dispara ANTES que la liquidacion si el stop esta mas cerca que el piso; el precio no salta niveles
    # (el gap a traves del stop se modela aparte con exit_slip, que puede terminar en liquidacion).
    stop_closer = (-liq_trig) > sl
    i_liq = first_idx(adv <= liq_trig) if not stop_closer else np.full(D, BIG)
    i_sl = first_idx(adv <= -sl) if stop_closer else np.full(D, BIG)
    i_tp = first_idx(fav >= tp)
    i_adv = np.minimum(i_liq, i_sl)
    if order == "adverse":
        adv_wins = i_adv <= i_tp
    else:
        k = np.clip(i_tp, 0, K - 1)
        tie_adv_first = adv_first_ohlc[np.arange(D), k]
        adv_wins = (i_adv < i_tp) | ((i_adv == i_tp) & tie_adv_first)
    kind = np.full(D, 3); pnl = np.zeros(D)
    # flatten
    flat_ticks = cl[:, -1] - slip
    pnl_flat = flat_ticks * nc * TICK_USD - nc * fee
    kind[:] = 3; pnl[:] = pnl_flat
    # TP
    tp_mask = (i_tp < BIG) & ~(adv_wins & (i_adv < BIG))
    kind[tp_mask] = 0; pnl[tp_mask] = (tp - slip) * nc * TICK_USD - nc * fee
    # adverso primero
    am = adv_wins & (i_adv < BIG)
    liq_first = am & (i_liq <= i_sl)
    kind[liq_first] = 2; pnl[liq_first] = -cushion
    sl_only = am & ~liq_first
    loss_sl = (sl + slip + exit_slip) * nc * TICK_USD + nc * fee
    sl_liq = sl_only & (loss_sl >= cushion)           # el gap a traves del stop (o las comisiones) toca el piso
    kind[sl_only] = 1; pnl[sl_only] = -loss_sl
    kind[sl_liq] = 2; pnl[sl_liq] = -cushion
    # flatten que termina bajo el piso por comisiones
    fl = kind == 3
    bad = fl & (pnl_flat <= -cushion)
    kind[bad] = 2; pnl[bad] = -cushion
    return kind, pnl
