"""Utilidades comunes de la rama research/structural-levers: corrida del motor de palancas con la contabilidad de caja del reporte (payouts x0.75 cobrados 5 dias despues, fees completos incluida la tarifa inicial,
costo compartido $59.5/mes x12 una sola vez) y las metricas de conducta (RTP). SANDBOX / R&D."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
from dd_cash import lever_data as LD
from dd_cash.lever_engine import simulate

OPS12 = 59.5 * 12; HAIR = 0.75; TARGET_6K = 6000.0; TARGET_10K = 10000.0


def run(S, axis, mask=None, T=20000, seed=2026, lag=2, D=None):
    nd = len(axis)
    if D is None: D = LD.draw(nd, T, seed, mask)
    r = simulate(S, D, lag=lag, skip=LD.SKIP)
    gross = r["take_d"].astype(np.float64)
    hair = 1.0 if (S.xliq and not S.legacy) else HAIR            # con liquidacion explicita de la XFA el -25 por ciento ya esta dentro del motor (validado: $623 / 31.9% vs log $620 / 31.6%)
    take = np.concatenate([np.zeros((D.shape[0], 5)), gross[:, :-5]], axis=1) * hair
    cash = np.cumsum(take - r["fee_d"].astype(np.float64), axis=1)                 # por cuenta, SIN costo compartido
    out = dict(net=cash[:, -1], cash=cash, pay=take.sum(1), fees=r["fee_d"].astype(np.float64).sum(1), fee_c=r["fee_c"], fee_a=r["fee_a"],
               att=r["n_att"].astype(float), b0=r["n_b0"].astype(float), b1=r["n_b1"].astype(float), npass=r["n_pass"].astype(float), npay=r["n_pay"].astype(float),
               touch=r["blow_d"].sum(1).astype(float), blow_d=r["blow_d"], stopped=r["stopped"], cmax=r["n_trades_cmax"] / np.maximum(r["n_trades_c"], 1),
               c80=r["n_trades_c80"] / np.maximum(r["n_trades_c"], 1), xmax=r["n_xmax"] / np.maximum(r["n_xtrades"], 1), D=D)
    return out


def total(outs, ops=OPS12):
    """Neto total de N cuentas (lista de salidas con el MISMO D) menos costo compartido una vez."""
    return sum(o["net"] for o in outs) - ops


def summ(x):
    return dict(mean=float(np.mean(x)), med=float(np.median(x)), p10=float(np.percentile(x, 10)), p90=float(np.percentile(x, 90)), pneg=float(np.mean(x < 0)),
                p6=float(np.mean(x >= TARGET_6K)), p10k=float(np.mean(x >= TARGET_10K)))


def fmt(s):
    return f"{s['mean']:>7,.0f} {s['med']:>7,.0f} {s['p10']:>7,.0f} {s['p90']:>7,.0f}  P(<0)={s['pneg']:>4.0%} P(>=6k)={s['p6']:>4.0%} P(>=10k)={s['p10k']:>4.0%}"
