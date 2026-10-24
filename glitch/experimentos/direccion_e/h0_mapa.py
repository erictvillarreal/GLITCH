"""Parte H, H0: mapa de probabilidades (valores + IC95 por bootstrap de bloques de 5 dias de la historia real + N + estado). -> resultados_H0.md
    GLITCH_MGC_PARQUET=... python h0_mapa.py [--quick]
Todo con el motor de las Partes A y D (orden de barra ambigua = 'adverse', conservador)."""
import argparse, math, os, sys, time
import numpy as np
from scipy.stats import binom
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "..", "xfa")); sys.path.insert(0, os.path.join(HERE, "..", "preservacion"))
from chain import combine_bank
from daydata import load_days, sim_day
from strategies.geometry_pure import decide_side, trading_day_index
from worlds import MGC, drift_for_wr, gold_mask, mgc_days
from xfa_engine import BarDays, Rules, pol_fixed, simulate_life
ap = argparse.ArgumentParser(); ap.add_argument("--quick", action="store_true"); a = ap.parse_args()
B = 20 if a.quick else 100; NBK = 20000 if a.quick else 40000; SEED = 20261024
t0 = time.time(); out = []; P = lambda s="": (print(s, flush=True), out.append(s))
mes = load_days(); clean = mgc_days(True); mk = gold_mask(clean, True)
rng = np.random.default_rng(SEED)
def block_pool(D, B_):
    nb = math.ceil(D / 5); st = rng.integers(0, D - 4, size=(B_, nb)); return (st[:, :, None] + np.arange(5)).reshape(B_, -1)[:, :D]
def ci(x): return np.percentile(x, 2.5), np.percentile(x, 97.5)
def fmt(v, c, pct=True): return (f"{v * 100:.1f} % [{c[0] * 100:.1f}, {c[1] * 100:.1f}]" if pct else f"{v:,.0f} [{c[0]:,.0f}, {c[1]:,.0f}]")
P("# resultados_H0 — mapa de probabilidades (Parte H)\n")
P(f"IC95 = percentiles 2.5–97.5 de {B} remuestras de la HISTORIA REAL (bloques de 5 días; MGC {clean.D} días limpios, MES {mes.D} días), cada una con su banco de {NBK:,} intentos/vidas. Cuenta lo incierto del conjunto de días, **no** lo incierto del futuro (cambio de régimen). Estados: MEDIDO / MODELADO / SUPUESTO / DESCONOCIDO.\n")
# ── Fila 1/2: fracciones y WR en MGC (limpio) ──
res = {s: sim_day(clean, s, 3, 9000.0, slip=0.0, exit_slip=0.0, sl=364, tp=364, fee=MGC["fee"], tick_usd=MGC["tick_usd"], stop_frac=0.5) for s in (1, -1)}
alt = np.array([decide_side(trading_day_index(d), "alternate") for d in clean.dates])
pools = block_pool(clean.D, B)
P("## Filas 1–2. MGC (3 micros, SL = TP = 364 ticks, 7:15→14:30 CT, datos limpios de contrato; FLATTEN = cierre a las 14:30 sin tocar barrera)\n")
P("| regla | TP % | SL % | FLATTEN % | WR_dec = TP/(TP+SL) | N | estado |\n|---|---|---|---|---|---|---|")
for nm, sd in (("alternate", alt), ("siempre LARGO", np.ones(clean.D, int)), ("siempre CORTO", -np.ones(clean.D, int))):
    k = np.where(sd == 1, res[1][0], res[-1][0])
    tp, sl_, fl = (k == 0).astype(float), ((k == 1) | (k == 2)).astype(float), (k == 3).astype(float)
    bt = [(tp[p].mean(), sl_[p].mean(), fl[p].mean(), tp[p].sum() / max((tp[p] + sl_[p]).sum(), 1)) for p in pools]; bt = np.array(bt)
    P(f"| {nm} | {fmt(tp.mean(), ci(bt[:, 0]))} | {fmt(sl_.mean(), ci(bt[:, 1]))} | {fmt(fl.mean(), ci(bt[:, 2]))} | **{fmt(tp.sum() / (tp + sl_).sum(), ci(bt[:, 3]))}** | {clean.D} días ({int((tp + sl_).sum())} decididos) | MEDIDO (2024-09→2026-09; el WR sale de un solo camino de precios) |")
P("\nWR_todos = TP/n (FLATTEN como no-ganador) = la columna TP %. WR_signo y WR_pnl: ver `resultados_F2.md`. En LARGO y CORTO FLATTEN cuenta igual: queda fuera del denominador de WR_dec.\n")
# ── MES: fracciones con liquidacion ──
P("## Fila 1b. MES (nc 40, TP 32, SL 100 pero **la liquidación por MLL ocurre a 40 ticks**; ventana 9:35→14:30 CT)\n")
P("| slip de entrada | lado | TP % | SL % | **LIQ (MLL) %** | FLATTEN % | estado |\n|---|---|---|---|---|---|---|")
pm = block_pool(mes.D, B)
for sp in (0.0, 1.0, 3.0):
    for sd, nm in ((1, "LARGO"), (-1, "CORTO")):
        k, _ = sim_day(mes, sd, 40, 2000.0, slip=sp, exit_slip=3.0, sl=100, tp=32, fee=1.22, tick_usd=1.25)
        f = [(np.mean(k == 0), np.mean(k == 1), np.mean(k == 2), np.mean(k == 3)) for _ in [0]][0]
        bt = np.array([[np.mean(k[p] == j) for j in range(4)] for p in pm])
        P(f"| {sp:g} | {nm} | {fmt(f[0], ci(bt[:, 0]))} | {fmt(f[1], ci(bt[:, 1]))} | {fmt(f[2], ci(bt[:, 2]))} | {fmt(f[3], ci(bt[:, 3]))} | MODELADO sobre {mes.D} días reales (slip: SUPUESTO/N=2) |")
# ── Fila 3: un dia desde el estado actual ──
P("\n## Fila 3. Un día del Combine con nc 40 desde el estado actual (balance $51,401.20, piso $49,401.20 ⇒ colchón $2,000; lado de lunes 26-oct = LARGO)\n")
P("El colchón es el de una cuenta nueva ($2,000): la probabilidad de TP/liquidación de UN día es la de la tabla anterior (LARGO). Lo que cambia con el estado es **pasar** (fila 4).\n")
# ── Fila 4: pasar ──
P("## Filas 4–5. P(pasar el Combine) y duración, nc 40 fijo (P0) y finish-line (P3); slip 0–4 ticks (M2 = costo de ejecución; M1 = movimiento de precio)\n")
P("| inicio | política | slip | M2 P(pasar) | M1 P(pasar) | días a resolver (media) | intentos esperados hasta pasar (1/p, M2) | estado |\n|---|---|---|---|---|---|---|---|")
ST = (1401.2, 1401.2, 1401.2, 1)
for start, init, fs in (("cuenta nueva", None, None), ("estado actual (+$1,401.20)", ST, 1)):
    for pol in ("P0", "P3"):
        for s in (0, 1, 2, 3, 4):
            def one(pool, nb):
                m2 = combine_bank(mes, nb, pol, (float(s),), (1.0,), seed=11, init=init, first_side=fs, pool=pool)
                m1 = combine_bank(mes, nb, pol, (0.0,), (1.0,), seed=11, init=init, first_side=fs, pool=pool, sl_ticks=100 + s, tp_ticks=32 - s)
                return m2[0].mean(), m1[0].mean(), m2[1].mean()
            v = np.array(one(None, 100000)); bt = np.array([one(p, NBK) for p in pools_m]) if False else None
            pm_s = block_pool(mes.D, B); bt = np.array([one(p, NBK // 2) for p in pm_s])
            P(f"| {start} | {pol} | {s} | {fmt(v[0], ci(bt[:, 0]))} | {fmt(v[1], ci(bt[:, 1]))} | {v[2]:.2f} | {1 / v[0]:.1f} | MODELADO (reglas oficiales; slip SUPUESTO) |")
        print("   ", start, pol, round(time.time() - t0), "s", flush=True)
open(os.path.join(HERE, "resultados_H0_parte1.md"), "w", encoding="utf-8").write("\n".join(out))
