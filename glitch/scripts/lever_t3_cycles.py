"""Tarea 3 — politica de ciclos: reiniciar / comprar nuevo / detenerse con restriccion de intentos al ano K y paro por perdida o bloqueo de ganancia; huella nc=40 vs 25 vs 16 con TP estructural (2 TP netos >= $3,100),
y el paquete DLL (Combine DLL $1,000 + XFA DLL $1,000 + tope de pago $4,000 [oferta temporal] + plan No Activation Fee $85). Mundo justo (30 mundos) = estimador estructural; historia real CON/SIN oro = robustez.
Uso: python -m scripts.lever_t3_cycles"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np, dataclasses as dc, math
from dd_cash import lever_data as LD
from scripts.lever_common import run, summ, OPS12

lines = []; P = lambda s: (print(s), lines.append(s))
T = 20000; NW = 30
def tp_rule(nc, tv=1.25, comm=1.22, net=1550.0): return math.ceil((net + comm * nc) / (tv * nc) - 1e-9)

def pool(nc, **kw):
    kw = {**dict(x_sl=728, x_tp=728, nc_x=3), **kw}
    return LD.make_pool_spec(n_worlds=NW, nc=nc, tp=tp_rule(nc), **kw)

def row(lab, o, extra=""):
    s = summ(o["net"])
    P(f"{lab:46s}{s['mean']:>8,.0f}{s['med']:>8,.0f}{s['p10']:>8,.0f}{s['pneg']:>7.0%}{o['att'].mean():>8.1f}{o['touch'].mean():>8.1f}{o['c80'].mean():>7.0%}{extra}")

P(f"TAREA 3 — politica de ciclos (50K, 1 cuenta, neto/ano POR CUENTA con liquidacion explicita de la XFA (sin ajuste -25 por ciento) y todos los fees, sin costo compartido). T={T}, {NW} mundos sinteticos. XFA: bracket 728x3 (la mejor sin loteria de la Tarea 4), slip 0.5")
P(f"{'politica':46s}{'media':>8s}{'mediana':>8s}{'p10':>8s}{'P(<0)':>7s}{'intent.':>8s}{'dias MLL':>8s}{'nc>=80%':>7s}")
P("\n--- (A) huella del Combine (nc) con TP estructural, sin tope de intentos ---")
for nc in (50, 40, 25, 16):
    S, axis = pool(nc)
    o = run(S, axis, T=T); row(f"nc={nc} TP={tp_rule(nc)} (stop = liquidacion del MLL)", o, f"   pase={o['npass'].sum()/o['att'].sum():.3f}")
P("\n--- (B) tope de intentos K x huella (reinicio = compra nueva al mismo precio; al llegar a K se detiene) ---")
base = {}
for nc in (40, 25, 16):
    S, axis = pool(nc)
    for K in (10, 15, 20, 30, None):
        o = run(dc.replace(S, K=K), axis, T=T); base[(nc, K)] = o
        row(f"nc={nc} K={K}", o, f"   $/intento={o['net'].mean()/o['att'].mean():.0f}")
P("\n--- (C) paro por perdida acumulada S y bloqueo de ganancia Z (nc=40, K libre): minimizar P(<0) para una media dada ---")
S, axis = pool(40)
for sl, lg in ((None, None), (500, None), (1000, None), (2000, None), (None, 3000), (None, 6000), (1000, 6000), (2000, 6000), (1000, 3000)):
    o = run(dc.replace(S, stop_loss=sl, lock_gain=lg), axis, T=T); row(f"paro perdida {sl} / bloqueo ganancia {lg}", o)
P("\n--- (D) paquete DLL: Combine DLL $1,000 + XFA DLL $1,000 (bracket 622/498 x2, sin loteria) + tope $4,000 (oferta temporal; verificar vigencia) ---")
for nc in (40, 25, 16, 10):
    for lab, fee, act in (("Standard $49 + act $149", 49, 149), ("No Activation Fee con DLL $85", 85, 0)):
        S, axis = pool(nc, dll=1000.0, x_dll=1000.0, x_sl=498, x_tp=622, nc_x=2, cap=4000.0, fee=float(fee), act=float(act))
        o = run(S, axis, T=T); row(f"DLL nc={nc} TP={tp_rule(nc)} {lab}", o, f"   pase={o['npass'].sum()/o['att'].sum():.3f}")
open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dd_cash", "lever_t3_report.txt"), "w").write("\n".join(lines))
