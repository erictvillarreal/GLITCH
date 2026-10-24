"""Parte H, H0 (2.ª parte): XFA por WR, dependencia de régimen, costos, experiencia viva. -> resultados_H0_parte2.md
    GLITCH_MGC_PARQUET=... python h0_mapa2.py [--quick]"""
import argparse, math, os, sys, time
import numpy as np
from scipy.stats import binom
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "..", "xfa")); sys.path.insert(0, os.path.join(HERE, "..", "preservacion"))
from worlds import MGC, drift_for_wr, gold_mask, mgc_days
from xfa_engine import BarDays, Rules, pol_fixed, simulate_life
ap = argparse.ArgumentParser(); ap.add_argument("--quick", action="store_true"); a = ap.parse_args()
B = 20 if a.quick else 60; N0 = 40000; NB_ = 5000 if a.quick else 8000; SEED = 20261024
t0 = time.time(); out = []; P = lambda s="": (print(s, flush=True), out.append(s))
clean = mgc_days(True); mk = gold_mask(clean, True); rng = np.random.default_rng(SEED)
def ci(x): return np.percentile(x, 2.5), np.percentile(x, 97.5)
def metrics(days, n, seed):
    r = simulate_life(days, Rules(), pol_fixed(3, 364, 364), n=n, seed=seed, record_k=14)
    net = r["pay_net"].sum(1); pay = r["npay"] > 0; fp = r["first_pay_day"]
    return dict(p1=pay.mean(), cob=net.mean(), cond=net[pay].mean() if pay.any() else float("nan"), t1=np.median(fp[pay]) if pay.any() else float("nan"),
                life=r["life"].mean(), lose=((r["npay"] == 0) & (~r["alive"])).mean())
P("# resultados_H0 (parte 2) — XFA por WR, régimen, costos y experiencia viva\n")
P(f"XFA 3 micros, SL = TP = 364, stop 0.5, reglas oficiales verificadas (20-oct), sin RTP; **la ventaja se impone con una deriva calibrada para fijar WR_dec** (MODELADO: el WR real de cada escenario es una hipótesis, no un dato). IC95: {B} remuestras de bloques de 5 días de la historia limpia (W2 = sin la ventana de oro, {int(mk.sum())} días), bancos de {NB_:,}; punto: {N0:,} vidas.\n")
P("## Fila 6. Vida de la XFA por escenario de WR (W2)\n")
P("| WR_dec | P(≥1 pago) | P($0 en la vida) | cobrado medio por XFA | pago medio (si cobra) | días de trading al 1.er pago (mediana) | vida media (días) | P(perderla antes del 1.er pago) | estado |\n|---|---|---|---|---|---|---|---|---|")
pool_all = np.nonzero(mk)[0]
for wr in (0.45, 0.474, 0.485, 0.50, 0.52, 0.55):
    dm = 0.0 if abs(wr - 0.50) < 1e-9 else drift_for_wr(clean, mk, wr)
    days = BarDays(clean, MGC["tick_usd"], MGC["fee"], 364, 364, slip=(0.0,), mask=mk, cush_max=9000.0, drift=dm, stop_frac=0.5)
    m0 = metrics(days, N0, 21)
    bt = []
    for b in range(B):
        st = rng.integers(0, len(pool_all) - 4, size=math.ceil(len(pool_all) / 5)); days.pool = pool_all[(st[:, None] + np.arange(5)[None, :]).ravel()[:len(pool_all)]]
        bt.append(metrics(days, NB_, 100 + b))
    g = lambda k: np.array([x[k] for x in bt])
    P(f"| {wr * 100:.1f} % | {m0['p1'] * 100:.1f} % [{ci(g('p1'))[0] * 100:.1f}, {ci(g('p1'))[1] * 100:.1f}] | {(1 - m0['p1']) * 100:.1f} % | ${m0['cob']:,.0f} [{ci(g('cob'))[0]:,.0f}, {ci(g('cob'))[1]:,.0f}] | ${m0['cond']:,.0f} | {m0['t1']:.0f} | {m0['life']:.1f} | {m0['lose'] * 100:.1f} % | MODELADO (WR = hipótesis) |")
    print("  wr", wr, round(time.time() - t0), "s", flush=True)
P("\n**P(activar la XFA tras pasar):** SUPUESTO = 100 % (decisión de Eric, $149 y un día de retraso manual); no es una probabilidad de mercado.\n")
P("## Fila 8. Dependencia de régimen (ventana de oro 14-nov-2025 → 26-ene-2026), WR_dec = 50 % (sin deriva)\n")
P("| días usados | cobrado medio por XFA | P(≥1 pago) | estado |\n|---|---|---|---|")
for nm, mask in (("todos (con la ventana de oro)", None), ("sin la ventana de oro (W2)", mk), ("solo la ventana de oro", ~mk)):
    days = BarDays(clean, MGC["tick_usd"], MGC["fee"], 364, 364, slip=(0.0,), mask=mask, cush_max=9000.0, drift=0.0, stop_frac=0.5)
    m = metrics(days, N0, 21); P(f"| {nm} ({clean.D if mask is None else int(mask.sum())} días) | ${m['cob']:,.0f} | {m['p1'] * 100:.1f} % | MEDIDO en esa ventana (régimen único) |")
P("\n(La Parte D ya mostró que sin la contaminación de contratos la ventana de oro casi no mueve el pago por XFA; el régimen reciente —últimos 250 días limpios— da P(≥1 pago) ≈ 29 % frente a 36 % histórico.)\n")
P("## Fila 7. Costos\n")
P("| concepto | valor | N / fuente | estado |\n|---|---|---|---|\n| comisión round-turn MES / MNQ / M2K / MYM | $1.22 por contrato (todo incluido) | Help Center de Topstep, artículo de comisiones y tarifas, consultado 24-oct-2026 | MEDIDO (fuente primaria; sin fecha de vigencia en la página) |\n| comisión round-turn MGC | $1.92 | ídem | MEDIDO (ídem) |\n| reset del Combine / mensualidad | $49 / $49 al mes | Help Center, leído el 20-oct (RULEBOOK_XFA.md) | MEDIDO (fuente primaria) |\n| activación de la XFA / pago por wire | $149 / $30 | ídem | MEDIDO |\n| slippage de entrada MES | +1 y +3 ticks adversos (19 y 20-oct) | N = 2 | MEDIDO pero **sin información** (ver más abajo) |\n| slippage de salida (SL, FLATTEN, liquidación) | 3 ticks asumidos | ninguna medición | **SUPUESTO / DESCONOCIDO** |\n")
P("## Fila 9. Experiencia viva: ¿qué información hay?\n")
mod = 0.548 / (0.548 + 0.450)
P(f"- **MES real:** 8 resueltos (3 TP, 4 SL, 1 desconocido). Entre los 7 decididos, 3 TP: p̂ = 43 %, IC95 exacto de Clopper-Pearson [{__import__('scipy.stats', fromlist=['beta']).beta.ppf(0.025, 3, 5) * 100:.0f}, {__import__('scipy.stats', fromlist=['beta']).beta.ppf(0.975, 4, 4) * 100:.0f}] %. El modelo dice P(TP | decidido) ≈ {mod * 100:.0f} %: P(X ≤ 3 de 7 | p = {mod:.2f}) = {binom.cdf(3, 7, mod) * 100:.0f} % → **consistente con el modelo y con 30 %, 43 % o 60 %: no hay información.**")
P("- **MGC Practice:** 3 sesiones (SL, FLATTEN, FLATTEN; 0 TP): 1 trade decidido. **Sin información.**")
def n_needed(p0, p1, alpha=0.05, power=0.8):
    for n in range(10, 5000):
        k = int(binom.ppf(1 - alpha, n, p0)) + 1
        if 1 - binom.cdf(k - 1, n, p1) >= power: return n
P(f"- **Cuántos trades decididos harían falta** (binomial exacta de una cola, α = 5 %, potencia 80 %): distinguir p = 0.55 de 0.50 → **{n_needed(0.50, 0.55)}**; 0.55 de 0.45 → **{n_needed(0.45, 0.55)}** (sin ajuste por esperar fallos); distinguir 50 % de 47.4 % → **{n_needed(0.474, 0.50) or '> 5,000'}**. A ≈ 1 trade por día hábil en MES (casi todos decididos) son ≈ {n_needed(0.50, 0.55)/252:.1f} años para el primer caso; en MGC (44 % decididos) el doble o más.")
open(os.path.join(HERE, "resultados_H0_parte2.md"), "w", encoding="utf-8").write("\n".join(out))
