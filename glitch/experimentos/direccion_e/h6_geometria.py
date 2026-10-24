"""Parte H, H6: horario de flatten, razón de barreras, interacciones y barrera efectiva del Combine. -> resultados_H6.md
    GLITCH_MGC_PARQUET=... python h6_geometria.py"""
import math, os, sys, time
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "..", "xfa")); sys.path.insert(0, os.path.join(HERE, "..", "preservacion"))
from chain import combine_bank, run_chain, xfa_bank
from daydata import load_days, sim_day
from strategies.geometry_pure import decide_side, trading_day_index
from worlds import MGC, MGC_PARQUET, drift_for_wr, gold_mask, mgc_days
from xfa_engine import BarDays, Policy, Rules, pol_fixed
t0 = time.time(); out = []; P = lambda s="": (print(s, flush=True), out.append(s))
mes = load_days(); clean = mgc_days(True); mk = gold_mask(clean, True); sig_m = float(np.std(clean.cl[mk][:, -1])); sig_s = float(np.std(mes.cl[:, -1]))
NB, NC = 80000, 30000
cb0 = combine_bank(mes, NB, "P0", (1.0, 3.0), (0.5, 0.5), seed=11)
P("# resultados_H6 — geometría del trade y salida por tiempo\n")
# 1. flatten
P("## 1. Horario de FLATTEN en MGC (3 micros, SL = TP = 364, entrada 7:15 CT; datos limpios)\n")
P("| flatten (CT) | días | TP % | SL % | FLATTEN % | WR_dec `alternate` | cobrado por XFA (WR 50 %, W2) | P(≥1 pago) | neto $/año/cuenta |\n|---|---|---|---|---|---|---|---|---|")
for lab, last in (("10:30", 10 * 60 + 25), ("12:00", 11 * 60 + 55), ("13:30", 13 * 60 + 25), ("14:30 (hoy)", 14 * 60 + 25)):
    dd = load_days(MGC_PARQUET, MGC["ref_hm"], last, MGC["tick"], fill_gaps=True, dominant_contract=True); mk_ = gold_mask(dd, True)
    alt = np.array([decide_side(trading_day_index(d), "alternate") for d in dd.dates])
    r = {s: sim_day(dd, s, 3, 9000.0, slip=0.0, exit_slip=0.0, sl=364, tp=364, fee=MGC["fee"], tick_usd=MGC["tick_usd"], stop_frac=0.5) for s in (1, -1)}
    k = np.where(alt == 1, r[1][0], r[-1][0]); tp, sl_, fl = np.mean(k == 0), np.mean((k == 1) | (k == 2)), np.mean(k == 3)
    days = BarDays(dd, MGC["tick_usd"], MGC["fee"], 364, 364, slip=(0.0,), mask=mk_, cush_max=9000.0, stop_frac=0.5)
    life, pday, pnet = xfa_bank(days, Rules(), pol_fixed(3, 364, 364), NB, seed=21); net = run_chain(cb0[0], cb0[1], life, pday, pnet, n=NC, seed=5)["net"].mean()
    P(f"| {lab} | {dd.D} | {tp * 100:.1f} | {sl_ * 100:.1f} | {fl * 100:.1f} | {tp / (tp + sl_) * 100:.1f} % | ${pnet.sum(1).mean():,.0f} | {(pnet.sum(1) > 0).mean() * 100:.1f} % | ${net:,.0f} |")
    print("  flatten", lab, round(time.time() - t0), "s", flush=True)
P("\nLectura: cerrar antes baja la fracción decidida y el cobrado; **no hay un horario que suba el WR_dec de forma defendible** (con martingala es ≈ 50 % en cualquier horario; las diferencias son ruido de 215 decididos). El flatten tampoco puede moverse después de las 15:10 CT (regla de Topstep, `RULEBOOK_XFA.md` 1.9).\n")
# 2. razon de barreras: z* = deriva estandarizada necesaria para neto = 0
P("## 2. Razón TP:SL distinta de 1:1 en la XFA de MGC (3 micros). Se compara la **deriva necesaria para neto anual = 0** (z* = μ/σ por sesión), no el WR\n")
P("Una razón distinta de 1:1 cambia el WR_dec de equilibrio **mecánicamente** (con martingala WR₀ = SL/(TP+SL)); por eso la columna que cuenta es z*: cuánta deriva real hace falta. **Una razón con menor WR* pero mayor z* NO es una mejora.** Resolución de z*: ± ≈ 0.01 (interpolación en una malla de 0.03 y ruido de nivel de ±$100); **no hay bootstrap de días**: diferencias de Δz < 0.015 no se distinguen.\n")
P("| geometría (TP, SL) ticks | razón | WR₀ mecánico = SL/(TP+SL) | neto $/año a deriva 0 | z* (deriva necesaria) | WR_dec en z* (aprox.) | veredicto frente a 364/364 |\n|---|---|---|---|---|---|---|")
zs = (-0.08, -0.05, -0.02, 0.0, 0.02)
def zstar(tp, sl):
    vals = []
    for z in zs:
        dm = z * sig_m
        days = BarDays(clean, MGC["tick_usd"], MGC["fee"], sl, tp, slip=(0.0,), mask=mk, cush_max=9000.0, drift=dm, stop_frac=0.5)
        life, pday, pnet = xfa_bank(days, Rules(), pol_fixed(3, sl, tp), 50000, seed=21)
        vals.append(run_chain(cb0[0], cb0[1], life, pday, pnet, n=NC, seed=5)["net"].mean())
    vals = np.array(vals); ze = next((zs[i] + (zs[i + 1] - zs[i]) * (-vals[i]) / (vals[i + 1] - vals[i]) for i in range(len(zs) - 1) if vals[i] < 0 <= vals[i + 1]), float("nan"))
    return vals[3], ze
base_z = None
for tp, sl in ((364, 364), (546, 364), (364, 546), (485, 243), (243, 485)):
    n0, ze = zstar(tp, sl); base_z = ze if base_z is None else base_z
    wr0 = sl / (tp + sl)
    sub = type(clean)([d for d, m in zip(clean.dates, mk) if m], clean.ref[mk], clean.op[mk], clean.hi[mk], clean.lo[mk], clean.cl[mk], [])
    kk = [sim_day(sub, sd_, 3, 9000.0, slip=0.0, exit_slip=0.0, sl=sl, tp=tp, fee=0.0, tick_usd=1.0, drift=ze * sig_m)[0] for sd_ in (1, -1)]
    tpf = np.mean([np.mean(k_ == 0) for k_ in kk]); adf = np.mean([np.mean((k_ == 1) | (k_ == 2)) for k_ in kk]); wrz = tpf / (tpf + adf)
    P(f"| ({tp}, {sl}) | {tp / sl:.2f}:1 | {wr0 * 100:.1f} % | ${n0:,.0f} | {ze:+.3f} | {wrz * 100:.1f} % | {'base' if (tp, sl) == (364, 364) else ('posible mejora: HIPÓTESIS, sin IC de días' if ze < base_z - 0.015 else ('posible empeora: HIPÓTESIS, sin IC de días' if ze > base_z + 0.015 else 'sin diferencia distinguible (dentro del ruido de 443 días)'))} |")
    print("  razón", tp, sl, round(time.time() - t0), "s", flush=True)
P("\n(La columna «WR_dec en z*» es el WR_dec simulado con la deriva z* sobre los días reales: muestra que **el WR de equilibrio cambia por la geometría aunque la deriva necesaria sea la misma**.)\n")
# 3. interacciones por escenario de WR
P("## 3. Interacciones (por cuenta, $/año; ventaja por deriva en ambas etapas con la misma μ/σ; Combine mezcla {1,3}; stop 0.5)\n")
def pol41(): return Policy("4→1", lambda st: np.where(st.b < 1500.0, 4, 1), lambda st, g: np.where(st.b >= 1500.0, g, 0.0), 364, 364)
CF = [("hoy: P0 + 3×364", "P0", 364, "fixed"), ("finish-line + 3×364", "P3", 364, "fixed"), ("P0 + 728×3", "P0", 728, "fixed"), ("finish-line + 728×3", "P3", 728, "fixed"), ("finish-line + 4→1 micros (cobro ≥ $1,500)", "P3", 364, "41")]
P("| configuración | WR 47.4 % | WR 48.5 % | WR 50 % | WR 52 % |\n|---|---|---|---|---|")
cb = {}
res = {c[0]: [] for c in CF}
for wr in (0.474, 0.485, 0.50, 0.52):
    dm = 0.0 if abs(wr - 0.5) < 1e-9 else drift_for_wr(clean, mk, wr); ds = dm / sig_m * sig_s
    for nm, pol, sl, plan in CF:
        if (pol, round(ds, 5)) not in cb: cb[(pol, round(ds, 5))] = combine_bank(mes, NB, pol, (1.0, 3.0), (0.5, 0.5), seed=11, drift=ds)
        days = BarDays(clean, MGC["tick_usd"], MGC["fee"], sl, sl, slip=(0.0,), mask=mk, cush_max=9000.0, drift=dm, stop_frac=0.5)
        life, pday, pnet = xfa_bank(days, Rules(), pol_fixed(3, sl, sl) if plan == "fixed" else pol41(), NB, seed=21)
        ps, cd = cb[(pol, round(ds, 5))]; res[nm].append(run_chain(ps, cd, life, pday, pnet, n=NC, seed=5)["net"].mean())
    print("  inter", wr, round(time.time() - t0), "s", flush=True)
for nm, *_ in CF: P(f"| {nm} | " + " | ".join(f"${v:,.0f}" for v in res[nm]) + " |")
P("\nPolítica de cobro: «cobrar ya» es la de las filas con 3×364/728×3; 4→1 espera a $1,500 de saldo (y baja a 1 micro). **728×3, 4→1 y el uso del tamaño máximo tocan los criterios públicos de RTP/«conducta prohibida»** (`RULEBOOK_XFA.md` 6.1–6.4): preguntas sin responder.\n")
# 4. barrera efectiva del Combine
P("## 4. La barrera efectiva del Combine (MES nc 40)\n")
ks = sim_day(mes, 1, 40, 2000.0, slip=0.0, exit_slip=3.0, sl=100, tp=32, fee=1.22, tick_usd=1.25)[0]; ks2 = sim_day(mes, 1, 40, 2000.0, slip=0.0, exit_slip=3.0, sl=40, tp=32, fee=1.22, tick_usd=1.25)[0]
P(f"- Con SL nominal de 100 ticks: SL {np.mean(ks == 1) * 100:.1f} %, liquidación por MLL {np.mean(ks == 2) * 100:.1f} %, TP {np.mean(ks == 0) * 100:.1f} % (LARGO, slip 0). Con un stop a 40 ticks: TP {np.mean(ks2 == 0) * 100:.1f} %. **El SL de 100 ticks no opera: la barrera real es la liquidación a $2,000/($1.25×40) = 40 ticks.**")
P("- Con martingala P(TP antes que liquidación) = 40/(40+32) = **55.6 %** (no 75.8 % = 100/132, que sería el número si el SL de 100 fuera efectivo). El resultado observado 52.8–56.7 % es esa cifra más la deriva de la muestra.")
P("- Por eso el WR «de equilibrio» del Combine **no es comparable** con el de la XFA ni con el de los scripts que usaban SL 100: la Parte E §4 y H1 ya usan la barrera efectiva.")
open(os.path.join(HERE, "resultados_H6.md"), "w", encoding="utf-8").write("\n".join(out))
