"""
DD v2 -- Test 2: Kelly optimo (fraccional, formula clasica de apuestas
binarias f* = p - (1-p)/b, b=RR en $ neto), comparado contra el riesgo
real por trade (SL_ticks x tick_value x nc) como fraccion de DOS
"bankrolls" posibles:
  (a) account_size (Kelly clasico, todo el capital de la cuenta)
  (b) mll_distance (el "bankroll" REAL de este juego -- la cantidad
      exacta que se puede perder antes de tronar, que es la condicion
      de ruina real de un Combine/XFA Topstep, no $0 de equity)
(b) es la lectura mas relevante para este producto especifico -- Topstep
no permite perder mas que mll_distance nunca (el floor te saca antes),
asi que ESE es el "bankroll en riesgo" real del juego, no el tamaño
total de la cuenta.
"""
from __future__ import annotations
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.prop_firm import TOPSTEP_50K, TOPSTEP_150K
from strategies.geometry_pure import SPECS
from dd_v2.common import G2, MGC_XFA

G2_WR = 0.7157
MGC_WR_DAILY = 0.4940  # CORREGIDO 13-sep-2026 -- ver dd_v2/test1_friction.py y research log
MGC_WR_DENSE = 0.5020


def kelly_fraction(p: float, net_win: float, net_loss_abs: float) -> float:
    """f* = p - (1-p)/b, b = net_win/net_loss_abs (RR en $ neto, no en ticks)."""
    b = net_win / net_loss_abs
    return p - (1 - p) / b


def analyze(label: str, wr: float, sl_ticks: int, tp_ticks: int, nc: int,
            tick_value: float, commission_rt: float, spec_acct, spec_label: str):
    net_win = tp_ticks * tick_value * nc - commission_rt * nc
    net_loss_abs = sl_ticks * tick_value * nc + commission_rt * nc
    f_star = kelly_fraction(wr, net_win, net_loss_abs)

    risk_per_trade = sl_ticks * tick_value * nc  # lo que se pierde si toca SL (bruto, antes de comision)
    frac_of_account = risk_per_trade / spec_acct.account_size
    frac_of_mll = risk_per_trade / spec_acct.mll_distance

    print(f"\n{'='*90}\n{label}  (WR={wr:.4f}, nc={nc}, SL={sl_ticks}/TP={tp_ticks} ticks, cuenta {spec_label})\n{'='*90}")
    print(f"  net_win=${net_win:,.2f}  net_loss=${-net_loss_abs:,.2f}  RR_neto={net_win/net_loss_abs:.3f}")
    print(f"  Kelly optimo f* = {f_star:+.4f}  ({f_star*100:+.2f}% del bankroll por trade)")
    print(f"  Riesgo real por trade (bruto, si toca SL): ${risk_per_trade:,.2f}")
    print(f"  Riesgo real / account_size ({spec_acct.account_size:,.0f})   = {frac_of_account:.4f} ({frac_of_account*100:.2f}%)")
    print(f"  Riesgo real / mll_distance ({spec_acct.mll_distance:,.0f})   = {frac_of_mll:.4f} ({frac_of_mll*100:.2f}%)  <- bankroll REAL del juego (condicion de ruina real)")

    if f_star <= 0:
        print(f"  VEREDICTO: Kelly <= 0 -- el EV neto de este trade es NEGATIVO al WR usado. "
              f"El candidato NO se sostiene por edge positivo -- depende por completo de la "
              f"convexidad del payout del Combine/XFA (bounded loss/bounded window), no de EV>0 por trade.")
    else:
        ratio_mll = frac_of_mll / f_star
        print(f"  Ratio (riesgo real / mll_distance) vs Kelly optimo: {ratio_mll:.2f}x "
              f"({'SOBRE-apalancado' if ratio_mll > 1 else 'SUB-apalancado'} vs Kelly puro sobre el bankroll real del juego)")


if __name__ == "__main__":
    mes = SPECS["MES"]
    mgc = SPECS["MGC"]

    analyze("G2 (MES, Combine)", G2_WR, G2.sl_ticks, G2.tp_ticks, G2.nc,
             mes.tick_value_usd, mes.commission_roundturn, TOPSTEP_50K, "50K")

    analyze("MGC_XFA (MGC, Combine hacia XFA) -- WR diario real", MGC_WR_DAILY,
             MGC_XFA.sl_ticks, MGC_XFA.tp_ticks, MGC_XFA.nc,
             mgc.tick_value_usd, mgc.commission_roundturn, TOPSTEP_150K, "150K")

    analyze("MGC_XFA (MGC, Combine hacia XFA) -- WR denso/calibracion", MGC_WR_DENSE,
             MGC_XFA.sl_ticks, MGC_XFA.tp_ticks, MGC_XFA.nc,
             mgc.tick_value_usd, mgc.commission_roundturn, TOPSTEP_150K, "150K")
