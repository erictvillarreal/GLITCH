"""Parte F, F2: MGC con datos limpios (contrato dominante) vs el cargador anterior (barras mezcladas). alternate / siempre LARGO / siempre CORTO.
Definiciones de WR (ver resultados_F2.md). -> resultados_F2.md.   GLITCH_MGC_PARQUET=... python f2_datos_limpios.py"""
import os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from common_e import SEED, day_results
from rule_eval import _ratio_boot
from strategies.geometry_pure import decide_side, trading_day_index
from worlds import MGC, gold_mask, mgc_days
out = []; P = lambda s="": (print(s, flush=True), out.append(s))
P("# resultados_F2 — MGC con datos limpios vs mezclados (3 micros, SL = TP = 364 ticks, entrada 7:15 CT, flatten 14:30 CT, comisión $1.92/micro, slip 0)\n")
P("## Definiciones de WR (una línea cada una; el reporte usa **WR_dec** salvo que diga otra cosa)\n")
P("- **WR_dec = TP / (TP + SL)** entre los días que tocan TP o SL; FLATTEN (cierre a las 14:30 CT sin tocar barrera) queda **fuera** del denominador. Es la WR del modelo de valor (la deriva se calibra para fijarla).")
P("- **WR_todos = TP / n** (FLATTEN cuenta como no-ganador). **WR_signo = P(cierre del flatten > referencia en el lado jugado)** (exactitud de dirección, E1–E5). **WR_pnl = días con P&L neto > 0 / días con P&L ≠ 0** (FLATTEN cuenta por su signo; es lo que mira el ‘día ganador ≥ $150’ del pago).\n")
rows = {}
for lab, clean in (("limpio (contrato dominante)", True), ("mezclado (cargador anterior)", False)):
    dd = mgc_days(clean); dates = dd.dates; D = dd.D
    res = day_results(dd, 3, 2000.0, 364, 364, MGC["fee"], MGC["tick_usd"], 0.0)
    alt = np.array([decide_side(trading_day_index(d), "alternate") for d in dates])
    P(f"\n## {lab}: {D} días\n")
    P("| regla | TP % | SL % | FLATTEN % | WR_dec [IC95] | WR_todos | WR_signo | WR_pnl | P&L neto medio/día [IC95] |\n|---|---|---|---|---|---|---|---|---|")
    for rule, sd in (("alternate", alt), ("siempre LARGO", np.ones(D, int)), ("siempre CORTO", -np.ones(D, int))):
        k = np.where(sd == 1, res[1][0], res[-1][0]); p = np.where(sd == 1, res[1][1], res[-1][1])
        tp = (k == 0).astype(float); sl = ((k == 1) | (k == 2)).astype(float); fl = (k == 3).astype(float)
        w, ci, _ = _ratio_boot(tp, tp + sl, seed=SEED)
        sign = np.sign(dd.cl[:, -1]) * sd; ws = (sign > 0).sum() / max((sign != 0).sum(), 1)
        wp = (p > 0).sum() / max((p != 0).sum(), 1)
        rng = np.random.default_rng(SEED); nb = int(np.ceil(D / 5)); st = rng.integers(0, D - 4, size=(10000, nb)); ix = (st[:, :, None] + np.arange(5)).reshape(10000, -1)[:, :D]
        mp = p[ix].mean(1)
        P(f"| {rule} | {tp.mean() * 100:.1f} | {sl.mean() * 100:.1f} | {fl.mean() * 100:.1f} | **{w * 100:.1f} %** [{ci[0] * 100:.1f}, {ci[1] * 100:.1f}] ({int((tp + sl).sum())} dec.) | {tp.mean() * 100:.1f} % | {ws * 100:.1f} % | {wp * 100:.1f} % | ${p.mean():+.1f} [{np.percentile(mp, 2.5):+.1f}, {np.percentile(mp, 97.5):+.1f}] |")
        rows[(lab, rule)] = (tp.mean(), sl.mean(), fl.mean(), w)
    mk = gold_mask(dd, True)
    if clean:
        k = np.where(alt == 1, res[1][0], res[-1][0])[mk]
        P(f"\nSin la ventana de oro (14-nov-2025 → 26-ene-2026), `alternate`: {mk.sum()} días; TP {np.mean(k == 0) * 100:.1f} %, SL {np.mean((k == 1) | (k == 2)) * 100:.1f} %, FLATTEN {np.mean(k == 3) * 100:.1f} %; WR_dec = {np.mean(k == 0) / (np.mean(k == 0) + np.mean((k == 1) | (k == 2))) * 100:.1f} %.")
P("\n## Cómo se trata FLATTEN\nEn el modelo del XFA, un FLATTEN es un día cerrado a precio de mercado con P&L continuo (media ≈ $0, desvío ≈ $420): entra al P&L, al contador de días ≥ $150 y al MLL, pero **no** a WR_dec. 56 % de los días son FLATTEN con la geometría de hoy, por lo que WR_dec descansa en solo ≈ 215 días decididos (IC95 ±6.6 pp); WR_signo (n ≈ 480) es la medida con más potencia (±4.5 pp) y WR_pnl es la que ve el pago.")
open(os.path.join(HERE, "resultados_F2.md"), "w").write("\n".join(out))
