"""Consolidacion — escalera de palancas (neto anual por cuenta y por paquete de cuentas), mundo justo (60 mundos) vs historia real CON/SIN oro, con estres de slip y de colocacion del TP, y metricas de conducta.
Uso: python -m scripts.lever_final"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np, dataclasses as dc
from dd_cash import lever_data as LD
from scripts.lever_common import run, summ, OPS12

lines = []; P = lambda s: (print(s), lines.append(s))
T = 30000; NW = 60
hdr = f"{'paso':54s}{'media':>8s}{'mediana':>8s}{'p10':>8s}{'p90':>8s}{'P(<0)':>7s}{'intent.':>8s}{'dias MLL':>9s}{'Pxfa':>6s} | {'real CON oro':>12s}{'real SIN oro':>13s}"
P("ESCALERA DE PALANCAS — 1 cuenta 50K, neto anual por cuenta (sin costo compartido $714), 12 meses desde 19-oct-2026, slip 0.5, liquidacion explicita de la XFA (sin ajuste -25 por ciento), fees completos")
P(hdr)
STEPS = [("0. Hoy: TP40, XFA 364x3 (Cerebro 2), plan Standard", dict(tp=40, x_sl=364, x_tp=364, nc_x=3)),
         ("1. + TP32 (aprobable: mismo tamano y stop)", dict(tp=32, x_sl=364, x_tp=364, nc_x=3)),
         ("2. + bracket XFA 728x3 (propuesta; cambia logica de capital)", dict(tp=32, x_sl=728, x_tp=728, nc_x=3)),
         ("3. paso 2 + bloqueo de ganancia $3,000 (control de conducta)", dict(tp=32, x_sl=728, x_tp=728, nc_x=3, lock_gain=3000.0)),
         ("4. paso 2 + huella nc=25 (TP51; ~mitad del tamano maximo)", dict(nc=25, tp=51, x_sl=728, x_tp=728, nc_x=3)),
         ("5. paso 2 con No Activation Fee $95 + act $0", dict(tp=32, x_sl=728, x_tp=728, nc_x=3, fee=95.0, act=0.0)),
         ("6. paso 2 + primer tramo de $10k al 100% (supuesto, solo 1er ano)", dict(tp=32, x_sl=728, x_tp=728, nc_x=3, first100=10000.0)),
         ("7. paso 2 + DLL comprado (Combine+XFA $1,000, tope $4,000)", dict(tp=32, nc=40, x_sl=498, x_tp=622, nc_x=2, x_dll=1000.0, dll=1000.0, cap=4000.0))]
res = {}
for lab, kw in STEPS:
    kwp = dict(kw)
    S, axis = LD.make_pool_spec(n_worlds=NW, **kwp)
    o = run(S, axis, T=T, seed=31); s = summ(o["net"]); res[lab] = (o, s)
    Sr, axr = LD.make_spec(slip=0.5, **{k: v for k, v in kwp.items()})
    ocon = run(Sr, axr, T=T, seed=32); osin = run(Sr, axr, mask=LD.gold_mask(axr), T=T, seed=33)
    P(f"{lab:54s}{s['mean']:>8,.0f}{s['med']:>8,.0f}{s['p10']:>8,.0f}{s['p90']:>8,.0f}{s['pneg']:>7.0%}{o['att'].mean():>8.1f}{o['touch'].mean():>9.1f}{o['pay'].sum()/max(o['npass'].sum(),1):>6.0f} | {ocon['net'].mean():>12,.0f}{osin['net'].mean():>13,.0f}")
P("\nESTRES del paso 2 (bracket XFA 728x3) y del paso 1: neto por cuenta, mundo justo / real CON oro / real SIN oro")
P(f"{'estres':54s}{'justo':>8s}{'CON oro':>9s}{'SIN oro':>9s}")
for lab0, kw0 in (STEPS[1], STEPS[2]):
    for slab, skw in (("slip 0.5 (base)", dict(slip=0.5)), ("slip 1.0", dict(slip=1.0)), ("slip 0.0", dict(slip=0.0)), ("TP necesita +1 tick para llenar (slip 0.5)", dict(slip=0.5, tp_extra=1)), ("slip 1.0 + TP +1 tick", dict(slip=1.0, tp_extra=1))):
        S, axis = LD.make_pool_spec(n_worlds=NW, **kw0, **skw); a = run(S, axis, T=T, seed=41)["net"].mean()
        Sr, axr = LD.make_spec(**kw0, **skw); b = run(Sr, axr, T=T, seed=42)["net"].mean(); c = run(Sr, axr, mask=LD.gold_mask(axr), T=T, seed=43)["net"].mean()
        P(f"{lab0[:30]:30s} {slab:42s}{a:>8,.0f}{b:>9,.0f}{c:>9,.0f}")
open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dd_cash", "lever_final_report.txt"), "w").write("\n".join(lines))
