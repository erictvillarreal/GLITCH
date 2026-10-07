"""Diagnostico de edge: para una estructura (producto, hora, TP, SL en ticks) mide P(TP), P(SL), EV por trade, t-stat y una PRUEBA DE PERMUTACION de la direccion.
Resultado de un bracket (ticks): +TP si toca TP antes que SL (SL primero si empatan), -SL si toca SL, P&L al flatten si ninguno. Tablas long/short construidas una vez; cualquier regla de
direccion es una seleccion por dia. Nulo: signos aleatorios por dia (10,000 permutaciones). SANDBOX / R&D."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
from scripts.tables_generic import build, SPEC, INF
from strategies.geometry_pure import trading_day_index, decide_side
import datetime as dt


def outcomes(tab, tp, sl):
    tb = tab["tpt"][:, tp]; ab = tab["adv"][:, sl]
    return np.where(tb < ab, float(tp), np.where(ab < INF, -float(sl), tab["flat"]))


def diag(prod, entry_m, tp, sl, label="", nperm=10000, seed=1):
    L = build(prod, entry_m, side_mode="always_long"); S = build(prod, entry_m, side_mode="always_short")
    tick, tv, comm = L["tick"], L["tv"], L["comm"]
    oL, oS = outcomes(L, tp, sl), outcomes(S, tp, sl)
    dates = L["dates"]; n = len(dates)
    alt = np.array([1 if trading_day_index(dt.date.fromisoformat(d)) % 2 == 0 else -1 for d in dates])
    pick = lambda sgn: np.where(sgn == 1, oL, oS)
    unit = tv  # $ por tick por contrato
    out = [f"{label or prod} {entry_m//60}:{entry_m%60:02d} CT tp={tp} sl={sl} ticks ({n} dias), martingala: P(TP)={sl/(tp+sl):.1%}"]
    def stats(name, o):
        mu = o.mean(); se = o.std(ddof=1) / np.sqrt(len(o)); h = len(o) // 2
        ptp = np.mean(o == tp)
        out.append(f"   {name:18s} P(TP)={ptp:.1%}  EV={mu:+.2f} ticks/trade (EV $/contrato {mu*unit-comm:+.2f}) t={mu/se:+.2f} | H1 {o[:h].mean():+.2f} H2 {o[h:].mean():+.2f}")
    stats("alternar", pick(alt)); stats("siempre largo", oL); stats("siempre corto", oS)
    rng = np.random.default_rng(seed); mus = np.empty(nperm)
    for i in range(nperm):
        mus[i] = pick(rng.choice([-1, 1], size=n)).mean()
    mu_alt = pick(alt).mean()
    out.append(f"   permutacion de signos (nulo): media {mus.mean():+.2f}, sd {mus.std():.2f} ticks; alternar cae en percentil {np.mean(mus < mu_alt):.1%} (p unilateral = {np.mean(mus >= mu_alt):.3f})")
    # medidas de drift y de estructura: retorno medio entrada->flatten por lado
    return "\n".join(out)


if __name__ == "__main__":
    for prod, em, tp, sl in (("MGC", 433, 167, 50), ("MGC", 495, 86, 50), ("MGC", 585, 142, 50), ("MES", 585, 60, 50), ("MES", 750, 60, 50), ("MNQ", 750, 100, 50), ("MCL", 690, 80, 50)):
        print(diag(prod, em, tp, sl)); print()
