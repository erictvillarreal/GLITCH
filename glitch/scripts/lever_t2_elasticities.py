"""Tarea 2 — elasticidades del neto anual (motor de palancas, mundo de juego justo con 40 mundos sinteticos, TP32/nc40/50K, XFA 364x3 vigente, slip 0.5, liquidacion explicita de la XFA) respecto de: costo por intento, pase %, payout por XFA,
intentos/ano (tope K) y numero de cuentas; ingenieria inversa para US$6k y US$10k. Uso: python -m scripts.lever_t2_elasticities"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np, dataclasses as dc
from dd_cash import lever_data as LD
from scripts.lever_common import run, summ, fmt, OPS12

lines = []; P = lambda s: (print(s), lines.append(s))
T = 30000; NW = 40
S0, axis = LD.make_pool_spec(n_worlds=NW, tp=32)
D = LD.draw(len(axis), T, 2026)
base = run(S0, axis, D=D)
sb = summ(base["net"])
pass_rate = lambda o: o["npass"].sum() / o["att"].sum()
pxfa = lambda o: o["pay"].sum() / max(o["npass"].sum(), 1)
P(f"BASE (mundo justo, {NW} mundos x {len(axis)//NW} dias, TP32 nc40 50K, slip 0.5, std path, 1 cuenta): neto/cuenta ${sb['mean']:,.0f} (mediana {sb['med']:,.0f}, p10 {sb['p10']:,.0f}, p90 {sb['p90']:,.0f}, P(<0)={sb['pneg']:.0%})")
P(f"  descomposicion: intentos/ano A={base['att'].mean():.1f} | pase p={pass_rate(base):.3f} | payout por XFA (al trader, liquidacion explicita, cobrado en el ano) Pxfa=${pxfa(base):,.0f} | precio por intento c=$49 | activacion $149 | tarifa inicial $49 incluida en c*A")
P(f"  identidad: neto = pagos ${base['pay'].mean():,.0f} - fees Combine ${base['fee_c'].mean():,.0f} - activaciones ${base['fee_a'].mean():,.0f}   (el costo compartido $714 se resta una vez por TODAS las cuentas)")
P(f"  XFA/ano {base['npass'].mean():.1f}; pagos/ano {base['npay'].mean():.1f}; dias de MLL tocado/ano {base['touch'].mean():.1f}")
res = {}
def point(name, S):
    o = run(S, axis, D=D); res[name] = o; return o
P("\n--- (a) costo por intento (precio del Combine = reinicio) ---")
P(f"{'precio por intento':>20s}{'neto/cta':>10s}{'dNeto/d$1':>11s}")
prev = None
for c in (0, 25, 49, 70, 95, 120):
    o = point(f"c{c}", dc.replace(S0, fee=float(c)))
    P(f"{'$'+str(c):>20s}{o['net'].mean():>10,.0f}{(o['net'].mean()-sb['mean'])/(c-49) if c!=49 else float('nan'):>11.1f}")
P("--- (b) activacion ($0 = plan No Activation Fee, que cobra $95 o $85 con DLL por intento) ---")
for lab, fee, act in (("Standard $49 + act $149", 49, 149), ("Standard $49 + act $0 (hipotetico)", 49, 0), ("NAF $95 + act $0", 95, 0), ("NAF con DLL $85 + act $0 (DLL mandatorio: ver Tarea 4)", 85, 0), ("Standard act $75", 49, 75)):
    o = point(lab, dc.replace(S0, fee=float(fee), act=float(act))); P(f"{lab:62s}{o['net'].mean():>9,.0f}")
P("--- (c) pase % (palanca EXOGENA: convierte quiebres en pases o viceversa, sin cambiar duraciones) ---")
P(f"{'p realizado':>14s}{'neto/cta':>10s}{'intentos':>10s}{'XFA/ano':>9s}")
for up, dn in ((0, 0.6), (0, 0.35), (0, 0.15), (0, 0), (0.1, 0), (0.25, 0), (0.5, 0), (1.0, 0)):
    o = point(f"p{up}_{dn}", dc.replace(S0, p_up=up, p_dn=dn, seed=5)); P(f"{pass_rate(o):>14.3f}{o['net'].mean():>10,.0f}{o['att'].mean():>10.1f}{o['npass'].mean():>9.1f}")
P("--- (d) payout por XFA (multiplicador sobre el pago, vida de la XFA constante) ---")
P(f"{'multiplicador':>14s}{'Pxfa $':>9s}{'neto/cta':>10s}")
for m in (0.5, 0.75, 1.0, 1.25, 1.5, 2.0, 3.0):
    o = point(f"m{m}", dc.replace(S0, pay_scale=m)); P(f"{m:>14.2f}{pxfa(o):>9,.0f}{o['net'].mean():>10,.0f}")
P("--- (e) intentos al ano (tope K de compras de Combine por cuenta; incluye la inicial) ---")
P(f"{'K':>6s}{'intentos':>10s}{'neto/cta':>10s}{'P(<0)':>8s}{'dias MLL':>10s}")
for K in (5, 10, 15, 20, 30, 40, None):
    o = point(f"K{K}", dc.replace(S0, K=K)); P(f"{str(K):>6s}{o['att'].mean():>10.1f}{o['net'].mean():>10,.0f}{np.mean(o['net']<0):>8.0%}{o['touch'].mean():>10.1f}")
P("--- (f) numero de cuentas con las MISMAS senales (perfectamente correlacionadas), costo compartido $714 una vez ---")
P(f"{'N':>4s}{'neto total':>11s}{'mediana':>9s}{'p10':>8s}{'P(<0)':>7s}{'P(>=6k)':>8s}{'P(>=10k)':>9s}{'intentos tot':>13s}")
for N in (1, 2, 3, 4, 5):
    tot = N * base["net"] - OPS12; s = summ(tot)
    P(f"{N:>4d}{s['mean']:>11,.0f}{s['med']:>9,.0f}{s['p10']:>8,.0f}{s['pneg']:>7.0%}{s['p6']:>8.0%}{s['p10k']:>9.0%}{N*base['att'].mean():>13.0f}")
open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dd_cash", "lever_t2_report.txt"), "w").write("\n".join(lines))
