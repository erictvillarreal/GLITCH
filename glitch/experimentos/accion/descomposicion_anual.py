"""¿De dónde sale y a dónde se va el dinero de UNA cuenta en un año? Descomposición de la cadena Combine → XFA (252 días hábiles). -> resultados_DESCOMPOSICION.md
    cd glitch/experimentos/accion; GLITCH_MGC_PARQUET=... PYTHONPATH=../.. python3 descomposicion_anual.py
MODELADO (mismo motor que H1b/J5/K1; slippage empírico de 8 obs., 8.ª inferida = 0, NO VERIFICADA; OPS $245)."""
import os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
for p in ("../xfa", "../preservacion"): sys.path.insert(0, os.path.join(HERE, p))
from chain import combine_bank, run_chain, xfa_bank
from daydata import load_days
from worlds import MGC, drift_for_wr, gold_mask, mgc_days
from xfa_engine import BarDays, Rules, pol_fixed
NB = 60000; OPS = 245.0
mes = load_days(); clean = mgc_days(True); mk = gold_mask(clean, True)
sig_m = float(np.std(clean.cl[mk][:, -1])); sig_s = float(np.std(mes.cl[:, -1]))
EMP8 = (-1.0, 0.0, 1.0, 3.0); EMP8_P = (1 / 8, 3 / 8, 2 / 8, 2 / 8)
CFG = (("hoy: Combine P0 + XFA 3×364", "P0", 364), ("+ finish-line", "P3", 364), ("+ 728×3", "P0", 728), ("finish-line + 728×3", "P3", 728))
out = []; P = lambda s="": (print(s), out.append(s))
P("# resultados_DESCOMPOSICION — de dónde sale el dinero de una cuenta en un año (252 días hábiles)\n")
P("MODELADO; promedios por cuenta y año. «Intentos» = compras o resets de Combine ($49); «XFA alcanzadas» = Combines pasadas (activación $149). Slippage empírico de 8 obs. (8.ª inferida = 0, NO VERIFICADA). OPS $245/año (los $14.30/mes de API por cuenta activa ya están dentro de ese orden de magnitud).\n")
for wr in (0.474, 0.50):
    dm = 0.0 if abs(wr - 0.5) < 1e-9 else drift_for_wr(clean, mk, wr); ds = dm / sig_m * sig_s
    cbs = {pol: combine_bank(mes, NB, pol, EMP8, EMP8_P, seed=11, exit_slip=3.0, drift=ds) for pol in ("P0", "P3")}
    xbs = {}
    for sl in (364, 728):
        days = BarDays(clean, MGC["tick_usd"], MGC["fee"], sl, sl, slip=(0.0,), mask=mk, cush_max=9000.0, drift=dm, stop_frac=0.5)
        xbs[sl] = xfa_bank(days, Rules(), pol_fixed(3, sl, sl), NB, seed=21)
    P(f"\n## WR {wr * 100:.1f} %\n")
    P("| plan | intentos de Combine / año | XFA alcanzadas / año | XFA que cobran / año | **cobros brutos** | − compras y resets ($49) | − activaciones ($149) | − OPS | **neto** | cobro medio por pago |\n|---|---|---|---|---|---|---|---|---|---|")
    for nm, pol, sl in CFG:
        ps, cd = cbs[pol]; life, pday, pnet = xbs[sl]
        r = run_chain(ps, cd, life, pday, pnet, n=40000, seed=5, ops=OPS)
        npass = r["npass"].mean(); act = 149.0 * npass; att = (r["fees"].mean() - act) / 49.0; reset = 49.0 * att
        P(f"| {nm} | {att:.1f} | {npass:.1f} | {(r['npay'] > 0).mean() * 0 + r['npay'].mean():.1f} pagos | **${r['cash'].mean():,.0f}** | −${reset:,.0f} | −${act:,.0f} | −${OPS:,.0f} | **${r['net'].mean():+,.0f}** | ${r['cash'].mean() / max(r['npay'].mean(), 1e-9):,.0f} |")
open(os.path.join(HERE, "resultados_DESCOMPOSICION.md"), "w", encoding="utf-8").write("\n".join(out) + "\n")
