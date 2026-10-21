"""Parte D (8): UN solo rango anual por cuenta con la cadena Combine -> XFA -> Combine (motor nuevo en las dos etapas). -> resultados_D8.md
    GLITCH_MGC_PARQUET=... python run_partD8.py [--quick]"""
import argparse, os, sys, time
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "..", "preservacion"))
from chain import combine_bank, run_chain, xfa_bank
from daydata import load_days
from worlds import MGC, drift_for_wr, gold_mask, mgc_days
from xfa_engine import BarDays, Rules, pol_fixed
ap = argparse.ArgumentParser(); ap.add_argument("--quick", action="store_true"); a = ap.parse_args()
NB = 20000 if a.quick else 200000; NC = 5000 if a.quick else 50000
t0 = time.time(); out = []; P = lambda s="": (print(s, flush=True), out.append(s))
mes = load_days()
import datetime as _dt
GOLDW = (_dt.date(2025, 11, 14), _dt.date(2026, 1, 26))
mk_mes = np.array([not (GOLDW[0] <= d <= GOLDW[1]) for d in mes.dates])
mes_ng = type(mes)([d for d, m in zip(mes.dates, mk_mes) if m], mes.ref[mk_mes], mes.op[mk_mes], mes.hi[mk_mes], mes.lo[mk_mes], mes.cl[mk_mes], [])
clean = mgc_days(True); mk_ng = gold_mask(clean, True); mk_all = np.ones(clean.D, bool)
P(f"# resultados_D8 (cadena anual de una cuenta; {NC} trayectorias; bancos de {NB} intentos/vidas; semilla fija; 252 días hábiles desde el 19-oct-2026)\n")
P("Combine: MES 492 días reales (Parte A), nc 40 (P0, hoy) o finish-line (P3), slip de entrada anclado a la referencia, salida 3 ticks, consistencia oficial. XFA: MGC limpio, reglas VERIFICADAS (RULEBOOK), slip de entrada 0. "
  "Activación $149 y 1 día manual; compra/reset $49; cobro 5 días hábiles después de pedir el pago; $714/año compartidos; sin RTP; sin beneficio de $10k.\n")
combines = {}
for wn, dm in (("CON oro", mes), ("SIN oro", mes_ng)):
    for pol in ("P0", "P3"):
        for lab, sl, sp in (("slip 1", (1.0,), (1.0,)), ("slip 3", (3.0,), (1.0,)), ("mezcla {1,3}", (1.0, 3.0), (0.5, 0.5))):
            ps, ds = combine_bank(dm, NB, pol, sl, sp, seed=11)
            combines[(pol, lab, wn)] = (ps, ds)
P("## Banco de intentos de Combine (cuenta nueva): P(pase) y días por intento\n\n| política | slip | historia MES | P(pase) | días por intento | intentos por pase |\n|---|---|---|---|---|---|")
for (pol, lab, wn), (ps, ds) in combines.items():
    P(f"| {pol} | {lab} | {wn} | {ps.mean() * 100:.1f} % | {ds.mean():.2f} | {1 / ps.mean():.1f} |")
xf = {}
for frac in (0.0, 0.5):
    for cname, sl in (("a plan 3×364", 364), ("b 728×3", 728)):
        for wname, mk in (("W2 sin oro", mk_ng), ("W1 con oro", mk_all)):
            days = BarDays(clean, MGC["tick_usd"], MGC["fee"], sl, sl, slip=(0.0,), mask=mk, cush_max=9000.0, stop_frac=frac)
            xf[(frac, cname, wname)] = xfa_bank(days, Rules(), pol_fixed(3, sl, sl), NB, seed=21)
P("\n## Neto anual por cuenta (media / mediana / p10–p90 / P(<0)), pases por año y pagos cobrados dentro del año\n")
P("| Combine (historia) | slip entrada | XFA (candidato, mundo, stop) | neto anual | pases/año | pagos cobrados/año | tarifas/año |\n|---|---|---|---|---|---|---|")
rows = {}
for (pol, lab, wn), (ps, ds) in combines.items():
    for (frac, cname, wname), (life, pday, pnet) in xf.items():
        if (wn == "CON oro") != (wname == "W1 con oro"): continue          # CON oro = MES y MGC completos; SIN oro = ambos sin la ventana
        r = run_chain(ps, ds, life, pday, pnet, n=NC, seed=5)
        n_ = r["net"]; rows[(pol, lab, wn, frac, cname)] = n_.mean()
        P(f"| {pol} ({wn}) | {lab} | {cname}, {wname}, stop {frac:.1f} | ${n_.mean():,.0f} / ${np.median(n_):,.0f} / ${np.percentile(n_, 10):,.0f}–${np.percentile(n_, 90):,.0f} / {np.mean(n_ < 0) * 100:.0f} % | {r['npass'].mean():.1f} | {r['npay'].mean():.1f} | ${r['fees'].mean():,.0f} |")
P(f"\n(tiempo {time.time() - t0:.0f}s)")
open(os.path.join(HERE, "resultados_D8.md"), "w").write("\n".join(out))
