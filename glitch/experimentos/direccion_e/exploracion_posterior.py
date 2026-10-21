"""EXPLORACION POSTERIOR (post-hoc: se origino al ver los resultados de E1/E4; NO es un hallazgo ni cuenta para G2).
Pregunta: el unico patron robusto es el sesgo LARGO de los indices. ¿Cuanto valdria para la cadena si persistiera, aplicado solo al Combine de MES (el XFA de MGC sin ventaja)? -> RESULTADOS_E_posterior.md
    GLITCH_MGC_PARQUET=... python exploracion_posterior.py"""
import math, os, sys
import numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from common_e import load_daily
from chain import combine_bank, run_chain, xfa_bank
from daydata import load_days
from worlds import MGC, gold_mask, mgc_days
from xfa_engine import BarDays, Rules, pol_fixed
out = []; P = lambda s="": (print(s, flush=True), out.append(s))
P("# RESULTADOS_E_posterior — EXPLORACIÓN POSTERIOR (post-hoc; no es hallazgo; no cuenta para G2)\n")
P("## 1. ¿Es estable el sesgo LARGO de los índices? P(apertura→cierre > 0) por década\n")
P("| serie | " + " | ".join(["1990s", "2000s", "2010s", "2020s"]) + " | todo |\n|---|---|---|---|---|---|")
for nm in ("^GSPC", "GLD"):
    df = load_daily(nm); o = np.sign(np.log(df.Close / df.Open)); o = o[o != 0]
    cells = []
    for lo, hi in ((1990, 1999), (2000, 2009), (2010, 2019), (2020, 2026)):
        x = o[(o.index.year >= lo) & (o.index.year <= hi)]
        cells.append(f"{(x == 1).mean() * 100:.1f} % (n={len(x)})" if len(x) else "—")
    P(f"| {nm} | " + " | ".join(cells) + f" | {(o == 1).mean() * 100:.1f} % |")
gs = load_daily("^GSPC"); r = np.log(gs.Close / gs.Open); z_long = float(r.mean() / r.std())
P(f"\nμ/σ diario apertura→cierre de ^GSPC (1990→2026) = {z_long:+.3f} (media {r.mean() * 1e4:+.2f} pb/día, σ {r.std() * 100:.2f} %).")
mes = load_days(); c = mes.cl[:, -1]; z_win = float(c.mean() / c.std())
P(f"Ventana real MES (9:30→14:30 CT, {mes.D} días): media {c.mean():+.2f} ticks/día, σ {c.std():.0f}; μ/σ = {z_win:+.3f}.")
P("\nEquivalencia con la tabla A de `resultados_E_valor.md` (μ/σ → WR entre decididos del bracket de MGC): 0.020 ↔ 51 %, 0.049 ↔ 52 %, 0.081 ↔ 53 %.\n")
P("## 2. Valor si ese sesgo persistiera, aplicado SOLO al Combine de MES (XFA de MGC sin deriva; plan 3×364; stop 0.5; reglas verificadas)\n")
NB, NC = 60000, 30000
clean = mgc_days(True); mk = gold_mask(clean, True); sig_s = float(np.std(mes.cl[:, -1]))
days = BarDays(clean, MGC["tick_usd"], MGC["fee"], 364, 364, slip=(0.0,), mask=mk, cush_max=9000.0, drift=0.0, stop_frac=0.5)
life, pday, pnet = xfa_bank(days, Rules(), pol_fixed(3, 364, 364), NB, seed=21)
P("| deriva MES | z = μ/σ | Combine hoy (P0) pasa | neto anual P0 mezcla slip{1,3} | neto anual P0 slip 3 | P3 mezcla |\n|---|---|---|---|---|---|")
rows = []
for lab, z in (("ninguna (alternate)", 0.0), ("larga en 36 años (^GSPC)", z_long), ("0.020 (≈WR 51 %)", 0.020), ("larga ventana 2 años MES", z_win)):
    dr = z * sig_s; vals = []; pas = None
    for pol, sl, sp in (("P0", (1.0, 3.0), (0.5, 0.5)), ("P0", (3.0,), (1.0,)), ("P3", (1.0, 3.0), (0.5, 0.5))):
        ps, cd = combine_bank(mes, NB, pol, sl, sp, seed=11, drift=dr)
        res = run_chain(ps, cd, life, pday, pnet, n=NC, seed=5)
        vals.append(res["net"].mean())
        if pas is None: pas = float(np.mean(ps))
    P(f"| {lab} | {z:+.3f} | {pas * 100:.0f} % | ${vals[0]:,.0f} | ${vals[1]:,.0f} | ${vals[2]:,.0f} |")
P("\nLectura: es un límite superior condicional (“si el sesgo largo de 2 años o de 36 años persistiera”); no es evidencia de ventaja futura. Para actuar sobre esto haría falta pre-registrar la hipótesis ‘siempre LARGO en el Combine de MES’ y probarla en paper en sombra (G4). El sesgo largo de los índices es una prima de riesgo (explicación económica simple, G2(4)), pero un sesgo así también invierte en mercados bajistas (LARGO sube el 50.3 % de los días en 2008 y el 47.7 % en 2022, `RESULTADOS_E1.md`), y un Combine con SL/liquidación asimétricos es sensible a una caída sostenida.")
open(os.path.join(HERE, "RESULTADOS_E_posterior.md"), "w").write("\n".join(out))
