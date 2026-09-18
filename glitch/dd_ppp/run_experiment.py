"""
DD PPP -- corre las 10 combinaciones (5 umbrales x 2 variantes) +
baseline sin proteccion, todas con el MISMO motor bar-a-bar
(dd_ppp/bar_walk.py) para que la comparacion sea consistente entre si.

NOTA METODOLOGICA IMPORTANTE (ver GLITCH_RESEARCH_LOG.md): el baseline
SIN proteccion de ESTE experimento (forzando flatten real a las 14:30 CT,
mismo dia de sesion) difiere del baseline ya publicado
($31,257 mediana, scripts/cerebro2_cashflow_monte_carlo.py) porque ESE
usa la convencion de calibracion max_holding_bars=100 (que no fuerza
el flatten exactamente a las 14:30 CT ni limita la ventana a la misma
sesion) -- son dos metodologias distintas, cada una valida para su
propio proposito. La comparacion relevante AQUI es entre las 10
variantes y ESTE MISMO baseline (misma metodologia para las 11), no
contra el numero externo ya publicado.

Alimenta los PnL resultantes (empiricos, ya con proteccion aplicada)
a los MISMOS motores de Monte Carlo ya validados:
  - TopstepMonteCarloSimulator (etapa Combine, pass_rate) via WR/avg_win/avg_loss
    derivados empiricamente de la muestra modificada.
  - Bootstrap i.i.d. de los PnL reales (dia completo, ya neto de
    comision) para la etapa XFA -- reusa simulate_xfa_lifetime()
    (dist-based, nc YA incorporado en el pnl empirico -- no
    dynamic-nc aqui, ver nota abajo) para la distribucion de payout a
    1 año.

NOTA sobre nc dinamico: el $31,257 publicado usa nc DINAMICO (Scaling
Plan). Este experimento usa nc FIJO=6 (el ya usado en el bar-walk,
igual que el candidato original define su intento de diseño) por
simplicidad -- extender a nc dinamico requeriria recalcular el bar-walk
completo para cada nivel de balance posible, fuera de alcance de este
experimento puntual. Declarado explicitamente, no escondido.
"""
from __future__ import annotations
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd

from core.prop_firm import TOPSTEP_150K
from core.funded_account import XFA_150K
from simulation.monte_carlo import TopstepMonteCarloSimulator
from dd_ppp.bar_walk import run_all_trades, NC

THRESHOLDS = [800, 1000, 1200, 1500, 1700]
VARIANTS = {"A_partial50": "partial", "B_full100": "full"}
N_PATHS_COMBINE = 100_000
MAX_DAYS_COMBINE = 15
N_DAYS_1Y = 252
N_TRAJECTORIES_XFA = 30_000


class EmpiricalDist:
    """Bootstrap i.i.d. de la muestra real de PnL diarios (ya neto de
    comision) -- mismo contrato .sample(n, rng) que DailyReturnDist/
    ExactDayDist, para reusar TopstepMonteCarloSimulator/simulate_xfa_lifetime
    SIN modificarlos. Valido dado Test 3 de la Fase A del due diligence
    (autocorrelacion lag-1 ~0, sin rechazo de independencia) -- resamplear
    i.i.d. no viola ninguna estructura de dependencia real detectada."""
    def __init__(self, pnl_array: np.ndarray, name: str):
        self.pnl_array = pnl_array
        self.name = name

    def sample(self, n, rng):
        return rng.choice(self.pnl_array, size=n, replace=True)

    def describe(self):
        return f"[{self.name}] bootstrap empirico, n_muestra={len(self.pnl_array)}, mean=${self.pnl_array.mean():+.2f}"


def combine_stage(pnl_array: np.ndarray, label: str) -> dict:
    dist = EmpiricalDist(pnl_array, label)
    sim = TopstepMonteCarloSimulator(dist, TOPSTEP_150K, n_paths=N_PATHS_COMBINE, max_days=MAX_DAYS_COMBINE, seed=42)
    r = sim.run()
    return {"pass_rate_15d": r.pass_rate, "blow_rate": r.blow_rate,
            "avg_pass_days": r.avg_pass_days, "wr": float((pnl_array > 0).mean())}


def xfa_stage_1y(pnl_array: np.ndarray, label: str, seed: int = 7) -> dict:
    """Bootstrap directo de simulate_xfa_lifetime(), horizonte 1 año
    (252 dias) -- nc YA incorporado en pnl_array (fijo=6, ver nota del
    modulo)."""
    from core.funded_account import simulate_xfa_lifetime
    dist = EmpiricalDist(pnl_array, label)
    r = simulate_xfa_lifetime(dist, spec=XFA_150K, mll_reset_policy="every_payout",
                               n_paths=N_TRAJECTORIES_XFA, max_days=N_DAYS_1Y, seed=seed)
    return r


def main():
    print("=" * 100)
    print("BASELINE (sin proteccion) -- metodologia bar-walk de ESTE experimento")
    print("=" * 100)
    base = run_all_trades(threshold=None, variant=None)
    base_pnl = base["pnl_per_contract_total"].values
    print(f"N={len(base_pnl)}  mean=${base_pnl.mean():+.2f}  median=${np.median(base_pnl):+.2f}  "
          f"WR(pnl>0)={float((base_pnl>0).mean()):.4f}")

    combine_base = combine_stage(base_pnl, "baseline")
    xfa_base = xfa_stage_1y(base_pnl, "baseline")
    print(f"Combine: pass_rate_15d={combine_base['pass_rate_15d']:.4f}  blow_rate={combine_base['blow_rate']:.4f}")
    print(f"XFA 1y: median_payout=${xfa_base['median_lifetime_payout_usd']:,.2f}  "
          f"avg_payout=${xfa_base['avg_lifetime_payout_usd']:,.2f}  "
          f"prob_never_first_payout={xfa_base['prob_never_reached_first_payout']:.4f}\n")

    rows = [{
        "variant": "baseline", "threshold": None,
        "n_trades": len(base_pnl), "mean_pnl_per_trade": base_pnl.mean(),
        "median_pnl_per_trade": np.median(base_pnl), "wr_pnl_positive": float((base_pnl > 0).mean()),
        "combine_pass_rate_15d": combine_base["pass_rate_15d"], "combine_blow_rate": combine_base["blow_rate"],
        "xfa_median_payout_1y": xfa_base["median_lifetime_payout_usd"],
        "xfa_avg_payout_1y": xfa_base["avg_lifetime_payout_usd"],
        "xfa_prob_never_first_payout": xfa_base["prob_never_reached_first_payout"],
    }]

    for variant_label, variant_code in VARIANTS.items():
        for threshold in THRESHOLDS:
            df = run_all_trades(threshold=threshold, variant=variant_code)
            pnl = df["pnl_per_contract_total"].values
            n_triggered = int(df["triggered"].sum())

            combine = combine_stage(pnl, f"{variant_label}_{threshold}")
            xfa = xfa_stage_1y(pnl, f"{variant_label}_{threshold}")

            rows.append({
                "variant": variant_label, "threshold": threshold,
                "n_trades": len(pnl), "n_triggered": n_triggered,
                "mean_pnl_per_trade": pnl.mean(), "median_pnl_per_trade": np.median(pnl),
                "wr_pnl_positive": float((pnl > 0).mean()),
                "combine_pass_rate_15d": combine["pass_rate_15d"], "combine_blow_rate": combine["blow_rate"],
                "xfa_median_payout_1y": xfa["median_lifetime_payout_usd"],
                "xfa_avg_payout_1y": xfa["avg_lifetime_payout_usd"],
                "xfa_prob_never_first_payout": xfa["prob_never_reached_first_payout"],
            })
            print(f"{variant_label} thresh=${threshold}: triggered={n_triggered}/{len(pnl)}  "
                  f"mean_pnl=${pnl.mean():+.2f}  pass_rate={combine['pass_rate_15d']:.4f}  "
                  f"xfa_avg_1y=${xfa['avg_lifetime_payout_usd']:,.2f}")

    out = pd.DataFrame(rows)
    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ppp_results.csv")
    out.to_csv(out_path, index=False)
    print(f"\nGuardado: {out_path}")

    print(f"\n{'='*100}\nMATRIZ COMPLETA\n{'='*100}")
    print(out[["variant", "threshold", "n_triggered", "mean_pnl_per_trade", "wr_pnl_positive",
                "combine_pass_rate_15d", "xfa_avg_payout_1y", "xfa_median_payout_1y"]].to_string(index=False))


if __name__ == "__main__":
    main()
