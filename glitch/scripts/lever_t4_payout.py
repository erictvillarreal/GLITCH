"""Tarea 4 — politica de payout del XFA con fills realistas. Vida de UNA XFA (arranca en la XFA, K=0: no se vuelve a comprar), payout al trader tras el -25%, en (i) mundo de juego justo (estructural),
(ii) historia real CON oro, (iii) historia real SIN oro. Parametros: bracket simetrico SL=TP=S ticks (1:1, sin 'loteria'), contratos nc_x, tamano adaptativo rho, ruta (std/consistency), tope, umbral de retiro,
DLL de la XFA, slip 0.5/1.0. La seleccion de la geometria se hace en el mundo de JUEGO JUSTO (economia de las reglas), nunca en la historia real; la historia real solo se reporta como robustez.
Uso: python -m scripts.lever_t4_payout"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np, dataclasses as dc, itertools
from dd_cash import lever_data as LD
from dd_cash.lever_engine import simulate
from scripts.lever_common import HAIR

lines = []; P = lambda s: (print(s), lines.append(s))
HX = 126; T = 12000


def life(S, axis, mask=None, seed=3):
    pool = np.arange(len(axis)) if mask is None else np.nonzero(mask)[0]
    D = pool[np.random.default_rng(seed).integers(0, len(pool), (T, HX))]
    r = simulate(dc.replace(S, K=0), D, lag=0, skip=None, start_mode=1)
    pay = r["take_d"].astype(float).sum(1) * (1.0 if S.xliq else HAIR)
    return dict(pay=pay, p1=np.mean(r["n_pay"] > 0), npay=r["n_pay"].mean(), life=np.mean(np.where(r["blow_d"].any(1), r["blow_d"].argmax(1) + 1, HX)), died=r["blow_d"].any(1).mean())


def spec_for(S0, x_sl, x_tp, slip, **kw):
    """Re-hace la serie de la XFA con bracket (x_sl, x_tp) y slip; usa la tabla MGC del pool correspondiente."""
    return dc.replace(S0, **kw)


worlds = {}
def build_world(nw, slip, x_s):
    key = (nw, slip, x_s)
    if key not in worlds: worlds[key] = LD.make_pool_spec(n_worlds=nw, tp=32, x_sl=x_s, x_tp=x_s, slip=slip)
    return worlds[key]

P("TAREA 4 — payout esperado por XFA 50K al trader (una vida, 126 dias; liquidacion en tiempo real EXPLICITA en el motor, sin ajuste -25 por ciento), MGC 7:13 CT, bracket SL=TP=S ticks (1 tick = $1 por contrato), comision $1.92")
P("Techo de juego justo del payout esperado por XFA (DP, scripts/xfa_dp_ceiling.py, sin ajuste -25 por ciento): ~US$1,341 al trader (ya incluye la liquidacion en tiempo real; cualquier politica, incluso de loteria; comparable directamente con las cifras de abajo).")
def lottery_free(S_, nc_x, tv=1.0, mll=2000.0, ratio=1.25):
    """Regla anti-loteria: TP/SL efectivo inicial <= ratio (el SL efectivo es min(bracket, distancia al piso)); evita brackets con TP mucho mayor que el riesgo real."""
    sl_eff = min(S_, mll / (nc_x * tv))
    return S_ / sl_eff <= ratio


P("\n--- (A) geometria del bracket y tamano (SOLO brackets sin loteria: TP <= 1.25 x SL efectivo), mundo justo (20 mundos), slip 0.5, ruta Standard, cap $2,000, retiro en cuanto es elegible ---")
P(f"{'S':>5s}{'nc_x':>5s}{'rho':>6s}{'riesgo $/trade':>15s}{'E[payout]':>10s}{'mediana':>9s}{'P(>=1 pago)':>12s}{'pagos':>6s}{'vida d':>7s}")
rows = []
for S_, nc_x, rho in itertools.product((182, 273, 364, 455, 546, 637, 728), (1, 2, 3, 4, 5, 6), (None, 1.0, 0.5)):
    if not lottery_free(S_, nc_x): continue
    S0, axis = build_world(20, 0.5, S_)
    o = life(dc.replace(S0, nc_x=nc_x, x_rho=rho, x_unit=float(S_)), axis)
    rows.append((o["pay"].mean(), S_, nc_x, rho, o))
rows.sort(key=lambda r: -r[0])
for m, S_, nc_x, rho, o in rows[:12]:
    P(f"{S_:>5d}{nc_x:>5d}{str(rho):>6s}{S_*nc_x:>15,d}{m:>10,.0f}{np.median(o['pay']):>9,.0f}{o['p1']:>12.0%}{o['npay']:>6.1f}{o['life']:>7.0f}")
cur = [r for r in rows if r[1] == 364 and r[2] == 3 and r[3] is None][0]
P(f"  hoy (Cerebro 2: S=364, nc 3, fijo): E[payout] ${cur[0]:,.0f}")
best = rows[0]; P(f"  mejor sin loteria: S={best[1]}, nc_x={best[2]}, rho={best[3]}: ${best[0]:,.0f}")
Sb, ncb, rhob = best[1], best[2], best[3]
P("\n--- (B) momento de retiro (umbral de balance para pedir el pago) x ruta x tope, geometria de hoy (364x3) y la mejor, mundo justo, slip 0.5 ---")
P(f"{'geometria':>14s}{'ruta':>6s}{'tope':>7s}{'umbral':>8s}{'E[payout]':>10s}{'P(>=1 pago)':>12s}{'pagos':>6s}")
for lab, (S_, ncx, rho) in (("hoy 364x3", (364, 3, None)), (f"mejor {Sb}x{ncb}", (Sb, ncb, rhob))):
    S0, axis = build_world(20, 0.5, S_)
    for path, cap in (("std", 2000.0), ("std", 4000.0), ("cons", 3000.0), ("cons", 6000.0)):
        for thr in (0, 500, 1000, 2000, 3000, 4000, 6000):
            if thr > 0 and thr < 2 * 125: continue
            o = life(dc.replace(S0, nc_x=ncx, x_rho=rho, x_unit=float(S_), path=path, cap=cap, pay_thr=float(thr)), axis)
            P(f"{lab:>14s}{path:>6s}{cap:>7,.0f}{thr:>8d}{o['pay'].mean():>10,.0f}{o['p1']:>12.0%}{o['npay']:>6.1f}")
P("\n--- (C) slip del stop (llenado en el extremo de la barra: 0 = exacto, 0.5, 1.0 = peor caso dentro de la barra), ruta Standard cap $2,000, retiro asap ---")
P(f"{'geometria':>14s}{'slip':>6s}{'mundo justo':>12s}{'real CON oro':>13s}{'real SIN oro':>13s}")
for lab, (S_, ncx, rho) in (("hoy 364x3", (364, 3, None)), (f"mejor {Sb}x{ncb}", (Sb, ncb, rhob))):
    for slip in (0.0, 0.5, 1.0):
        S0, axis = build_world(20, slip, S_)
        a = life(dc.replace(S0, nc_x=ncx, x_rho=rho, x_unit=float(S_)), axis)["pay"].mean()
        R0, axr = LD.make_spec(x_sl=S_, x_tp=S_, nc_x=ncx, slip=slip, x_rho=rho, x_unit=float(S_))
        b = life(R0, axr)["pay"].mean(); c = life(R0, axr, mask=LD.gold_mask(axr))["pay"].mean()
        P(f"{lab:>14s}{slip:>6.1f}{a:>12,.0f}{b:>13,.0f}{c:>13,.0f}")
P("\n--- (E) paquete DLL ($1,000 comprado con el Combine; la XFA hereda el DLL; tope Standard $4,000 = oferta temporal): geometria sin loteria bajo el DLL, mundo justo, slip 0.5 ---")
P(f"{'nc_x':>5s}{'TP/SLeff':>9s}{'SLeff tk':>9s}{'TP tk':>7s}{'riesgo $':>9s}{'E[payout]':>10s}{'P(>=1 pago)':>12s}{'pagos':>6s}")
rowsE = []
for ncx in (2, 3, 4, 5):
    sl_eff = int(max(np.floor((1000.0 - 1.92 * ncx) / (ncx * 1.0)), 1))
    for fac in (1.0, 1.25):
        tp_t = int(round(sl_eff * fac))
        S0, axis = LD.make_pool_spec(n_worlds=20, tp=32, x_sl=sl_eff, x_tp=tp_t, x_dll=1000.0, slip=0.5)
        o = life(dc.replace(S0, nc_x=ncx, cap=4000.0, xdll=1000.0), axis)
        rowsE.append((o["pay"].mean(), ncx, fac, sl_eff, tp_t, o))
rowsE.sort(key=lambda r: -r[0])
for m, ncx, fac, sl_eff, tp_t, o in rowsE:
    P(f"{ncx:>5d}{fac:>9.2f}{sl_eff:>9d}{tp_t:>7d}{sl_eff*ncx:>9,d}{m:>10,.0f}{o['p1']:>12.0%}{o['npay']:>6.1f}")
open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dd_cash", "lever_t4_report.txt"), "w").write("\n".join(lines))
