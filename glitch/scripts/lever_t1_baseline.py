"""Tarea 1 (cuantificacion): efecto de las correcciones de reglas y del slip sobre la linea base (50K, TP32 y TP40, 1 cuenta), CON y SIN la ventana de oro 14-nov-2025..26-ene-2026, y en el mundo de juego justo (sintetico).
Uso: python -m scripts.lever_t1_baseline"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
from dd_cash import lever_data as LD
from scripts.lever_common import run, summ, fmt, OPS12

lines = []; P = lambda s: (print(s), lines.append(s))
T = 20000
P(f"TAREA 1 — linea base y correcciones de reglas (neto anual POR CUENTA; filas 'legacy' = serie + ajuste -25 por ciento (convencion previa), filas 'corregidas' = liquidacion explicita de la XFA sin ajuste; fees completos incl. tarifa inicial, SIN costo compartido; 12 meses desde 19-oct-2026; T={T})")
P(f"{'configuracion':58s}{'media':>8s}{'mediana':>8s}{'p10':>8s}{'p90':>8s}   intentos/ano  dias-MLL  pagos/ano")
rows = []
for tp in (32, 40):
    for lab, kw in (("legacy (reglas del motor validado, slip 0)", dict(legacy=True, slip=0.0)),
                    ("reglas corregidas, slip 0", dict(legacy=False, slip=0.0)),
                    ("reglas corregidas, slip 0.5 (BASE)", dict(legacy=False, slip=0.5)),
                    ("reglas corregidas, slip 1.0", dict(legacy=False, slip=1.0))):
        S, axis = LD.make_spec(tp=tp, **kw)
        for gl, gm in (("CON oro", None), ("SIN oro", LD.gold_mask(axis))):
            o = run(S, axis, mask=gm, T=T)
            s = summ(o["net"])
            P(f"TP{tp} {lab:42s} {gl:8s}{s['mean']:>8,.0f}{s['med']:>8,.0f}{s['p10']:>8,.0f}{s['p90']:>8,.0f}   {o['att'].mean():>8.1f}   {o['touch'].mean():>7.1f}  {o['npay'].mean():>6.1f}")
P("\nMUNDO DE JUEGO JUSTO (barras con signo volteado al azar, misma volatilidad; sin deriva ni persistencia) — lo que es ESTRUCTURAL (sin edge ni ventana de oro):")
for tp in (32, 40):
    for sd in (0, 1, 2):
        S, axis = LD.make_spec(tp=tp, legacy=False, slip=0.5, synthetic=True, seed=100 + sd)
        o = run(S, axis, T=T // 2, seed=7 + sd)
        s = summ(o["net"])
        P(f"TP{tp} sintetico semilla {sd} (slip 0.5)                              {s['mean']:>8,.0f}{s['med']:>8,.0f}{s['p10']:>8,.0f}{s['p90']:>8,.0f}   {o['att'].mean():>8.1f}   {o['touch'].mean():>7.1f}  {o['npay'].mean():>6.1f}")
open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dd_cash", "lever_t1_report.txt"), "w").write("\n".join(lines))
