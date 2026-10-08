"""Tarea 5 — portafolio de 2 a 3 cuentas 50K con senales DISTINTAS (producto/hora) y geometria ESTRUCTURAL (dd_cash.lever_data.structural_geometry, sin mirar rendimiento).
Seleccion por: correlacion de retornos diarios dirigidos (propiedad de los precios, no del P&L), liquidez, ejecutabilidad por API y costo de ingenieria. Mide: correlacion, dias con >=2 cuentas tocando el MLL,
P(ano negativo), colchon, neto (mundo justo independiente = cota optimista; misma senal = cota pesimista; historia real con correlacion real, CON/SIN oro).
Uso: python -m scripts.lever_t5_portfolio"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np, dataclasses as dc, pandas as pd
from dd_cash import lever_data as LD
from scripts.lever_common import run, summ, OPS12, HAIR

lines = []; P = lambda s: (print(s), lines.append(s))
T = 20000
ACC = {"A MES9:45>MGC7:13 (vigente)": ("MES", 585, "MGC", 433), "B MCL8:43>MCL8:43": ("MCL", 523, "MCL", 523), "C1 MGC9:45>MGC9:45": ("MGC", 585, "MGC", 585), "C2 M6E8:43>M6E8:43": ("M6E", 523, "M6E", 523),
       "E1 MNQ9:45>MGC7:13 (Combine equity, para contraste)": ("MNQ", 585, "MGC", 433)}
geo = {k: LD.structural_geometry(*v) for k, v in ACC.items()}
P("TAREA 5 — geometrias estructurales por cuenta (nc Combine / TP ticks / XFA bracket SL=TP ticks x nc_x):")
for k, g in geo.items(): P(f"  {k:48s} nc={g['nc']:>3d} TP={g['tp']:>4d} | XFA {g['x_sl']:>5d} ticks x {g['nc_x']:>2d}")
tabs = [LD.tab(v[0], v[1], kmax=800, tmax=800) for v in ACC.values()] + [LD.tab(v[2], v[3], kmax=800, tmax=800) for v in ACC.values()]
axis = LD.common_axis(tabs)
specs = {}
for k, v in ACC.items():
    g = geo[k]
    specs[k], _ = LD.make_spec(c_prod=v[0], c_entry=v[1], x_prod=v[2], x_entry=v[3], nc=g["nc"], tp=g["tp"], x_sl=g["x_sl"], x_tp=g["x_tp"], nc_x=g["nc_x"], slip=0.5, legacy=False, axis=axis)
nd = len(axis); P(f"\nEje comun: {nd} dias ({str(axis[0].date())}..{str(axis[-1].date())})")
gm = LD.gold_mask(axis)


def portfolio(keys, mask=None, same_signal_of=None, label=""):
    D = LD.draw(nd, T, 2026, mask)
    outs = [run(specs[k], np.array(axis), D=D) for k in keys] if same_signal_of is None else [run(specs[same_signal_of], np.array(axis), D=D)] * 2
    tot = sum(o["net"] for o in outs) - OPS12
    nacc = len(outs)
    cotouch = (sum(o["blow_d"].astype(int) for o in outs) >= 2).sum(1)
    cush = -np.minimum((sum(o["cash"] for o in outs) - np.cumsum(np.where(np.arange(LD.H) % 21 == 0, 59.5, 0.0))[None, :]).min(1), 0)
    s = summ(tot)
    P(f"{label:44s}{s['mean']:>8,.0f}{s['med']:>8,.0f}{s['p10']:>8,.0f}{s['pneg']:>7.0%}{s['p6']:>7.0%}{s['p10k']:>7.0%}{sum(o['att'].mean() for o in outs):>8.0f}{cotouch.mean():>9.1f}{np.percentile(cush,95):>9,.0f}")
    return outs, tot

hdr = f"{'portafolio':44s}{'media':>8s}{'mediana':>8s}{'p10':>8s}{'P(<0)':>7s}{'P>=6k':>7s}{'P>=10k':>7s}{'intent.':>8s}{'dias>=2MLL':>9s}{'colch p95':>9s}"
keys = list(ACC)
for gl, mask in (("HISTORIA REAL CON oro", None), ("HISTORIA REAL SIN oro", gm)):
    P(f"\n=== {gl} (neto total/ano de N cuentas, liquidacion explicita de la XFA (sin ajuste -25 por ciento), todos los fees y costo compartido $714; T={T}) ===")
    P(hdr)
    portfolio(keys[:1], mask, label="1 cuenta A")
    portfolio(keys[:1], mask, same_signal_of=keys[0], label="2 cuentas A+A (MISMA senal)")
    portfolio([keys[0], keys[1]], mask, label="2 cuentas A+B (MES>MGC, MCL)")
    portfolio([keys[0], keys[2]], mask, label="2 cuentas A+C1 (MES>MGC, MGC9:45)")
    portfolio([keys[0], keys[1], keys[2]], mask, label="3 cuentas A+B+C1")
    portfolio([keys[0], keys[1], keys[3]], mask, label="3 cuentas A+B+C2 (M6E)")
    portfolio([keys[0], keys[4]], mask, label="2 cuentas A+E1 (MNQ: equity, contraste)")
# niveles del mundo justo por cuenta (independientes)
P("\n=== MUNDO JUSTO (30 mundos sinteticos por cuenta, productos independientes): neto/ano POR CUENTA, sin costo compartido ===")
fair = {}
for k, v in ACC.items():
    g = geo[k]
    Sx, ax = LD.make_pool_spec(n_worlds=30, c_prod=v[0], c_entry=v[1], x_prod=v[2], x_entry=v[3], nc=g["nc"], tp=g["tp"], x_sl=g["x_sl"], x_tp=g["x_tp"], nc_x=g["nc_x"], slip=0.5, seed0=5000)
    o = run(Sx, ax, T=T, seed=17); fair[k] = o; s = summ(o["net"])
    P(f"  {k:48s}{s['mean']:>8,.0f}{s['med']:>8,.0f}{s['p10']:>8,.0f}  P(<0)={s['pneg']:.0%}  intentos {o['att'].mean():.0f}  dias MLL {o['touch'].mean():.0f}  pase {o['npass'].sum()/o['att'].sum():.3f}  Pxfa ${o['pay'].sum()/max(o['npass'].sum(),1):,.0f}")
P("\n  portafolios en mundo justo, cuentas INDEPENDIENTES (cota optimista de diversificacion) vs MISMA senal (cota pesimista):")
rng = np.random.default_rng(1)
def comb(keys_, indep=True):
    if indep:
        nets = [fair[k]["net"][rng.permutation(T)] for k in keys_]
    else:
        nets = [fair[keys_[0]]["net"]] * len(keys_)
    tot = sum(nets) - OPS12; return summ(tot)
for lab, ks, ind in (("A+B independientes", keys[:2], True), ("A+A misma senal", keys[:1] * 2, False), ("A+B+C1 independientes", [keys[0], keys[1], keys[2]], True), ("A+A+A misma senal", keys[:1] * 3, False),
                     ("A+B+C1+C2 independientes", [keys[0], keys[1], keys[2], keys[3]], True)):
    s = comb(ks, ind); P(f"  {lab:34s}{s['mean']:>8,.0f}{s['med']:>8,.0f}{s['p10']:>8,.0f}  P(<0)={s['pneg']:.0%}  P>=6k={s['p6']:.0%}  P>=10k={s['p10k']:.0%}")
open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dd_cash", "lever_t5_report.txt"), "w").write("\n".join(lines))
