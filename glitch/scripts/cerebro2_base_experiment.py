"""
Glitch — Cerebro 2: experimento base (01-sep-2026)
=====================================================
Rama cerebro2-dev. Primer experimento: ¿que pasa si la MISMA geometria
ya validada de Cerebro 1 (G2: SL=100/TP=40 ticks, alternar, nc=40, WR
empirico ~70.6%) se usara en una cuenta XFA, SIN la ventana de tiempo
protectora del Combine? No es una propuesta de diseño para Cerebro 2 --
es el punto de partida honesto antes de diseñar algo especifico para
XFA.

Corre AMBOS escenarios del MLL post-payout (every_payout /
first_payout_only) como sensibilidad explicita -- ver
core/funded_account.py::XFAAccount.mll_reset_policy y
GLITCH_RESEARCH_LOG.md para la pregunta sin resolver contra fuente
primaria completa que esto representa.

NO reporta un solo numero de "payout esperado" -- ambos escenarios,
lado a lado, siempre.
"""
from __future__ import annotations
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.funded_account import XFA_50K, simulate_xfa_lifetime
from scripts.camino_b_grid import ExactDayDist

# Misma geometria G2 de Cerebro 1, misma fuente (strategies/geometry_pure.py
# CANDIDATES["MES"] / SPECS["MES"]) -- NO una distribucion nueva inventada
# para XFA.
SL_TICKS = 100
TP_TICKS = 40
NC = 40
TICK_VALUE_USD = 1.25   # MES
COMMISSION_RT = 1.22    # MES, fuente Topstep
WR = 0.706              # punto medio del bracket empirico, ver GLITCH_RESEARCH_LOG.md

N_PATHS = 10_000
MAX_DAYS = 756  # ~3 años habiles -- horizonte largo, no un numero de negocio en si


def build_g2_distribution() -> ExactDayDist:
    avg_win_usd = TP_TICKS * TICK_VALUE_USD * NC
    avg_loss_usd = SL_TICKS * TICK_VALUE_USD * NC
    commission_usd = COMMISSION_RT * NC
    return ExactDayDist(WR, avg_win_usd, avg_loss_usd, commission_usd, trades_per_day=1)


def main():
    dist = build_g2_distribution()
    print(f"Distribucion G2: WR={WR:.1%}  avg_win=${dist.net_win + COMMISSION_RT*NC:.0f}  "
          f"avg_loss=${-dist.net_loss - COMMISSION_RT*NC:.0f}  comision=${COMMISSION_RT*NC:.2f}/trade")
    print(f"n_paths={N_PATHS}  max_days_horizon={MAX_DAYS}\n")

    results = {}
    for policy in ("every_payout", "first_payout_only"):
        r = simulate_xfa_lifetime(dist, spec=XFA_50K, mll_reset_policy=policy,
                                   n_paths=N_PATHS, max_days=MAX_DAYS, seed=7)
        results[policy] = r

    print(f"{'':35s} {'every_payout':>18s} {'first_payout_only':>18s}")
    fields = [
        ("prob_never_reached_first_payout", "{:.2%}"),
        ("prob_still_alive_at_horizon", "{:.2%}"),
        ("avg_lifetime_payouts", "{:.2f}"),
        ("median_lifetime_payouts", "{:.2f}"),
        ("avg_lifetime_days", "{:.1f}"),
        ("median_lifetime_days", "{:.1f}"),
        ("avg_lifetime_payout_usd", "${:,.0f}"),
        ("median_lifetime_payout_usd", "${:,.0f}"),
    ]
    for key, fmt in fields:
        a = fmt.format(results["every_payout"][key])
        b = fmt.format(results["first_payout_only"][key])
        print(f"{key:35s} {a:>18s} {b:>18s}")

    print()
    for policy in ("every_payout", "first_payout_only"):
        p10, p90 = results[policy]["payout_usd_p10_p90"]
        print(f"{policy}: payout_usd p10-p90 = ${p10:,.0f} - ${p90:,.0f}")


if __name__ == "__main__":
    main()
