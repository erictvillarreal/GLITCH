"""Parte D: comparacion de candidatos de la XFA 50K en el MISMO motor, reglas y trayectorias (PREREGISTRO_D.md). Un solo comando:

    GLITCH_MGC_PARQUET=/ruta/mgc_5min_2y_corrected_window.parquet python run_partD.py [--quick]

Escribe resultados_D.md. Semilla 20261020; 50,000 vidas por celda (misma semilla entre candidatos del mismo mundo = comparacion pareada).
"""
from __future__ import annotations

import argparse
import dataclasses as dc
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from worlds import MGC, brownian_like, gold_mask, mgc_days  # noqa: E402
from xfa_engine import BarDays, BinaryDays, Policy, Rules, SeqDays, pol_fixed, simulate_life  # noqa: E402

SEED = 20261020


def fmt(x): return f"${x:,.0f}"


def metrics(res, cost_obtain=None):
    paid = res["paid"]; n = len(paid)
    any_ = res["npay"] > 0
    m = dict(mean=paid.mean(), se=paid.std() / np.sqrt(n), med=float(np.median(paid)), p10=float(np.percentile(paid, 10)), p90=float(np.percentile(paid, 90)), p_any=any_.mean(),
             p0=(~any_).mean(), t1=float(np.median(res["first_pay_day"][any_] + 1)) if any_.any() else float("nan"), lose_before=float(np.mean(~any_ & ~res["alive"])),
             npay=res["npay"].mean(), life=res["life"].mean())
    return m


def row(label, m):
    return (f"| {label} | {fmt(m['mean'])} ± {m['se'] * 1.96:,.0f} | {fmt(m['med'])} | {fmt(m['p10'])} / {fmt(m['p90'])} | {m['p_any'] * 100:.1f} % | {m['p0'] * 100:.1f} % | "
            f"{m['t1']:.0f} | {m['lose_before'] * 100:.1f} % | {m['npay']:.2f} | {m['life']:.1f} |")


HDR = "| candidato | cobrado medio ± IC95 | mediana | p10 / p90 | P(≥1 pago) | P($0) | días al 1er pago (med.) | P(perder antes del 1er pago) | pagos esp. | vida (días) |\n|---|---|---|---|---|---|---|---|---|---|"


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--quick", action="store_true"); a = ap.parse_args()
    N = 4000 if a.quick else 50000
    t0 = time.time(); out = []
    P = lambda s="": (print(s, flush=True), out.append(s))
    if not os.environ.get("GLITCH_MGC_PARQUET"): sys.exit("falta GLITCH_MGC_PARQUET")
    clean = mgc_days(True); mixed = mgc_days(False)
    mk_all = np.ones(clean.D, bool); mk_ng = gold_mask(clean, True)
    brown, binfo = brownian_like(clean, mk_ng, D=6000 if a.quick else 40000)
    P(f"# resultados_D (generado por run_partD.py; N={N} vidas por celda; semilla {SEED})\n")
    P(f"MGC limpio: {clean.D} dias ({mk_ng.sum()} sin la ventana de oro); MGC contaminado (como el codigo previo): {mixed.D} dias. Browniano W3: sigma_dia={binfo['sigma']:.0f} ticks, s={binfo['s']:.1f}; "
      f"objetivo TP/SL/FLAT (364/364, W2) {np.round(binfo['target'], 3)}, ajuste {np.round(binfo['fit'], 3)}.\n")

    def bar(dd, mask, sl, tp, slip=(0.0,), cls=BarDays, **k):
        return cls(dd, MGC["tick_usd"], MGC["fee"], sl, tp, slip=slip, mask=mask, cush_max=9000.0, **k)

    worlds = {
        "W1 MGC limpio CON oro": lambda sl, tp, slip=(0.0,), cls=BarDays: bar(clean, mk_all, sl, tp, slip, cls),
        "W2 MGC limpio SIN oro": lambda sl, tp, slip=(0.0,), cls=BarDays: bar(clean, mk_ng, sl, tp, slip, cls),
        "W3 Browniano sin deriva": lambda sl, tp, slip=(0.0,), cls=BarDays: bar(brown, np.ones(brown.D, bool), sl, tp, slip, cls),
        "W0 MGC CONTAMINADO (codigo previo)": lambda sl, tp, slip=(0.0,), cls=BarDays: bar(mixed, np.ones(mixed.D, bool), sl, tp, slip, cls),
    }
    R = Rules()
    cands = [
        ("a  plan actual 3×364/364", lambda s: pol_fixed(3, 364, 364), 364, 364),
        ("b  728×3 (stop = piso)", lambda s: pol_fixed(3, 728, 728), 728, 728),
        ("c  1 micro 5 días y luego plan", lambda s: Policy("c", lambda st: np.where(st.t < 5, 1, 3), "max", 364, 364), 364, 364),
        ("e1 TP 60 / SL 364 (3 micros)", lambda s: pol_fixed(3, 364, 60), 364, 60),
        ("e2 TP 70 / SL 250 (3 micros)", lambda s: pol_fixed(3, 250, 70), 250, 70),
        ("f  payout-first (1 micro con ≥4 días ganadores)", lambda s: Policy("f", lambda st: np.where(st.wd >= 4, 1, 3), "max", 364, 364), 364, 364),
        ("H4b cobro mínimo ($125)", lambda s: pol_fixed(3, 364, 364, pay="min"), 364, 364),
    ]
    res_all = {}
    for wname, mk in worlds.items():
        P(f"\n## {wname}: reglas base del RULEBOOK, slip de entrada 0\n"); P(HDR)
        for cname, mkpol, sl, tp in cands:
            days = mk(sl, tp)
            r = simulate_life(days, R, mkpol(None), n=N, seed=SEED)
            res_all[(wname, cname)] = r
            P(row(cname, metrics(r)))
    # W4 pesimista: deriva ADVERSA calibrada para que WR = TP/(TP+SL) = 45 % entre los dias decididos (conserva las trayectorias intradia reales y la liquidacion en tiempo real)
    from worlds import drift_for_wr
    P("\n## W4 pesimista (MGC limpio SIN oro con deriva calibrada a WR): reglas base, slip 0\n"); P(HDR)
    for wr in (0.50, 0.45):
        dr = 0.0 if wr == 0.50 else drift_for_wr(clean, mk_ng, wr)
        days = BarDays(clean, MGC["tick_usd"], MGC["fee"], 364, 364, slip=(0.0,), mask=mk_ng, drift=dr)
        r = simulate_life(days, R, pol_fixed(3, 364, 364), n=N, seed=SEED)
        res_all[(f"W4 WR{int(wr * 100)}", cands[0][0])] = r
        P(row(f"a plan actual, WR {wr * 100:.0f} % (deriva {dr:+.1f} ticks/dia)", metrics(r)))
    # diferencias pareadas respecto a 'a'
    P("\n## Diferencia pareada de lo cobrado respecto al plan actual (a): media ± IC95, por mundo\n")
    P("| candidato | " + " | ".join(worlds) + " |\n|---|" + "---|" * len(worlds))
    for cname, *_ in cands[1:]:
        cells = []
        for wname in worlds:
            d = res_all[(wname, cname)]["paid"] - res_all[(wname, cands[0][0])]["paid"]
            cells.append(f"{d.mean():+,.0f} ± {1.96 * d.std() / np.sqrt(len(d)):,.0f}")
        P(f"| {cname} | " + " | ".join(cells) + " |")
    P(f"\n(tiempo {time.time() - t0:.0f}s)")
    open(os.path.join(HERE, "resultados_D.md"), "w").write("\n".join(out))


if __name__ == "__main__":
    main()
