"""Estadisticas para EVIDENCIA_CEREBRO2.md: dia real de Cerebro 2 (TP/SL/FLATTEN), WR con IC, bloques, dias ganadores >= $150 netos, y N necesario para distinguir WR 45/50/55 %."""
import os, sys, math
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "..", "preservacion"))
from worlds import MGC, gold_mask, mgc_days
from daydata import sim_day
from scipy.stats import binom, norm
from strategies.geometry_pure import decide_side, trading_day_index
out = []; P = lambda s="": (print(s), out.append(s))
def wilson(k, n, z=1.96):
    p = k / n; d = 1 + z * z / n; c = (p + z * z / (2 * n)) / d; h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return c - h, c + h
clean = mgc_days(True); mixed = mgc_days(False); ng = gold_mask(clean, True)
P("# evidencia_stats (generado por evidencia_stats.py)\n")
P("## 1. El día real de Cerebro 2 (bracket 364/364, 3 micros, ref 7:15 CT, flatten 14:30, comisión $1.92, sin slippage); lado = `alternate` por fecha real\n")
P("| serie | días | TP | SL | FLATTEN | WR = TP/(TP+SL) [IC95] | pnl medio por trade | P(día ≥ $150 neto) | P(día ≤ −$150) |\n|---|---|---|---|---|---|---|---|---|")
def alt_outcomes(dd, nc=3):
    """Resultado diario con el lado que produccion habria usado ese dia (alternate por trading_day_index de la fecha real)."""
    kl, pl = sim_day(dd, 1, nc, 2000.0, slip=0, exit_slip=0, sl=364, tp=364, fee=1.92, tick_usd=1.0)
    ks, ps = sim_day(dd, -1, nc, 2000.0, slip=0, exit_slip=0, sl=364, tp=364, fee=1.92, tick_usd=1.0)
    side = np.array([decide_side(trading_day_index(d), "alternate") for d in dd.dates])
    return np.where(side == 1, kl, ks), np.where(side == 1, pl, ps)


def day_stats(dd, mask, label):
    k, p = alt_outcomes(dd); k = k[mask]; p = p[mask]; n = len(k)
    tp = (k == 0).sum(); sl = (k == 1).sum(); fl = (k == 3).sum()
    lo, hi = wilson(tp, tp + sl)
    P(f"| {label} | {mask.sum()} | {tp / n * 100:.1f} % | {sl / n * 100:.1f} % | {fl / n * 100:.1f} % | {tp / (tp + sl) * 100:.1f} % [{lo * 100:.1f}, {hi * 100:.1f}] | ${p.mean():+,.1f} | {np.mean(p >= 150) * 100:.1f} % | {np.mean(p <= -150) * 100:.1f} % |")
    return k, p
day_stats(mixed, np.ones(mixed.D, bool), "CONTAMINADA (como el código previo)")
k, p = day_stats(clean, np.ones(clean.D, bool), "limpia, todos los días")
day_stats(clean, ng, "limpia, SIN ventana de oro")
k_, p_ = k, p
fl = p[k == 3]
P(f"\nDías FLATTEN (limpia, todos): pnl medio ${fl.mean():+,.0f}, sd ${fl.std():,.0f}; P(FLATTEN ≥ +$150) {np.mean(fl >= 150) * 100:.1f} %, P(FLATTEN ≤ −$150) {np.mean(fl <= -150) * 100:.1f} %. "
  f"De todos los días: {np.mean(p >= 150) * 100:.1f} % son 'días ganadores' de la regla (≥ $150 neto): {np.mean((k == 0)) / max(np.mean(p >= 150), 1e-9) * 100:.0f} % de ellos son TP y el resto son FLATTEN positivos.\n")
P("## 2. WR por bloques cronológicos (limpia, 4 bloques; la serie contiene la ventana de oro 14-nov-2025 → 26-ene-2026)\n")
P("| bloque | fechas | TP | SL | FLATTEN | WR [IC95] |\n|---|---|---|---|---|---|")
idx = np.arange(clean.D); blocks = np.array_split(idx, 4)
for bi, b in enumerate(blocks):
    kk, _ = alt_outcomes(clean); kb = kk[b]
    t = (kb == 0).sum(); s = (kb == 1).sum(); f = (kb == 3).sum()
    lo, hi = wilson(t, t + s)
    P(f"| {bi + 1} | {clean.dates[b[0]]} → {clean.dates[b[-1]]} | {t / len(b) * 100:.1f} % | {s / len(b) * 100:.1f} % | {f / len(b) * 100:.1f} % | {t / (t + s) * 100:.1f} % [{lo * 100:.1f}, {hi * 100:.1f}] |")
P("\n## 3. ¿Cuántas sesiones hacen falta para distinguir el WR? (decisiones TP/SL; solo 44 % de las sesiones terminan en TP o SL — el resto es FLATTEN)\n")
dec = 0.44
P("Prueba binomial exacta de una cola al 5 %, potencia 80 %: **n de operaciones decididas** y **sesiones** (÷ 0.44) para rechazar WR = 50 % cuando el verdadero es 45 % o 55 %, y para decidir entre 45 % y 55 % con errores de 5 % en ambos sentidos.\n")
def n_needed(p0, p1, alpha=0.05, power=0.80):
    for n in range(10, 20000):
        if p1 > p0:
            c = binom.ppf(1 - alpha, n, p0) + 1
            if 1 - binom.cdf(c - 1, n, p1) >= power: return n
        else:
            c = binom.ppf(alpha, n, p0) - 1
            if binom.cdf(c, n, p1) >= power: return n
    return None
rows = [("WR 50 % vs 45 % (¿es peor que 50?)", 0.50, 0.45), ("WR 50 % vs 55 % (¿es mejor que 50?)", 0.50, 0.55)]
P("| pregunta | trades decididos | sesiones |\n|---|---|---|")
for lab, p0, p1 in rows:
    n = n_needed(p0, p1); P(f"| {lab} | {n} | {math.ceil(n / dec)} |")
n = math.ceil((norm.ppf(0.95) * 0.5 / 0.05) ** 2); P(f"| decidir entre 45 % y 55 % (umbral 50 %, error 5 % en ambos) | {n} | {math.ceil(n / dec)} |")
P("\nCon las 3 sesiones vivas (SL, FLATTEN, FLATTEN) hay **1 trade decidido**: ninguna inferencia posible sobre el WR. Ni siquiera las 488 sesiones históricas limpias (≈ 215 decididas) bastan para separar 50 % de 45 % con potencia 80 %.\n")
open(os.path.join(HERE, "evidencia_stats.md"), "w").write("\n".join(out))
