"""Parte H (rehecho, 24-oct): (1) H0-0: P&L neto por sesión y las definiciones de WR; (2) por qué 728×3 baja el equilibrio y si el WR se remidió con esa geometría. -> resultados_H1c.md
    GLITCH_MGC_PARQUET=... python h1c_728_h00.py"""
import math, os, sys, time
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "..", "xfa")); sys.path.insert(0, os.path.join(HERE, "..", "preservacion"))
from chain import combine_bank, run_chain, xfa_bank
from daydata import load_days, sim_day
from strategies.geometry_pure import decide_side, trading_day_index
from worlds import MGC, drift_for_wr, gold_mask, mgc_days
from xfa_engine import BarDays, Rules, pol_fixed, simulate_life
SEED = 20261024; t0 = time.time(); out = []; P = lambda s="": (print(s, flush=True), out.append(s))
mes = load_days(); clean = mgc_days(True); mk = gold_mask(clean, True); sig_m = float(np.std(clean.cl[mk][:, -1]))
rng = np.random.default_rng(SEED)
def pools(D, B=2000):
    nb = math.ceil(D / 5); st = rng.integers(0, D - 4, size=(B, nb)); return (st[:, :, None] + np.arange(5)).reshape(B, -1)[:, :D]
def ci(x): return np.percentile(x, 2.5), np.percentile(x, 97.5)
P("# resultados_H1c — H0-0 (P&L neto por sesión y definiciones de WR) y por qué 728×3 baja el equilibrio\n")
P("## Parte 1 — H0-0: P&L neto por sesión y las definiciones de WR\n")
P("**Fuente y estado.** Días reales de 5 min (MGC: 488 días limpios, contrato dominante; MES: 492 días) reproducidos con el motor de las Partes A/D (`sim_day`): MODELADO sobre historia real, **no** son las sesiones vivas (no tengo el CSV de TopstepX ni `geometry_mes_log.json`: las 8 sesiones reales de MES y las 3 de MGC Practice **no se pudieron cruzar**). P&L **neto de comisión** (MGC $1.92 y MES $1.22 por contrato round-turn), slip de entrada 0, stop de MGC llenado a 0.5 (convención C1), liquidación del Combine = pérdida exacta del colchón.\n")
P("**Definiciones de WR** (cuatro; la quinta métrica es la que importa para el pago):\n- **WR_dec = TP / (TP + SL + LIQ)**: solo sesiones que tocan una barrera; **FLATTEN queda fuera del denominador**. Es la del modelo de valor (la deriva se calibra para fijarla).\n- **WR_todos = TP / n**: FLATTEN cuenta como no ganador.\n- **WR_signo = P(cierre del flatten > referencia en el lado jugado)**: exactitud de dirección (E1–E5); no mira barreras.\n- **WR_pnl = sesiones con P&L neto > 0 / sesiones con P&L ≠ 0**: FLATTEN cuenta por su signo.\n- **Días ganadores ≥ $150 netos** (lo que mira el pago de la XFA Standard: 5 días ≥ $150, no consecutivos): fracción de sesiones con P&L neto ≥ +$150.\n")
STAT = {}
def block(label, dd, nc, cush, sl, tp, fee, tv, sf, slips):
    D = dd.D; alt = np.array([decide_side(trading_day_index(d), "alternate") for d in dd.dates]); pl = pools(D)
    for sp in slips:
        r = {s: sim_day(dd, s, nc, cush, slip=sp, exit_slip=3.0 if cush < 5000 else 0.0, sl=sl, tp=tp, fee=fee, tick_usd=tv, stop_frac=sf) for s in (1, -1)}
        P(f"\n**{label}, slip de entrada {sp:g} ticks**\n")
        P("| regla | n | P&L neto medio/sesión [IC95] | mediana | desvío | p10 – p90 | mejor / peor | ≥ +$150 (de ellas, FLATTEN) | ≤ −$150 | WR_dec | WR_todos | WR_signo | WR_pnl |\n|---|---|---|---|---|---|---|---|---|---|---|---|---|")
        for nm, sd in (("alternate", alt), ("siempre LARGO", np.ones(D, int)), ("siempre CORTO", -np.ones(D, int))):
            k = np.where(sd == 1, r[1][0], r[-1][0]); p = np.where(sd == 1, r[1][1], r[-1][1])
            tpf = (k == 0).astype(float); adv = ((k == 1) | (k == 2)).astype(float)
            sign = np.sign(dd.cl[:, -1] - sp) * sd                      # exactitud de dirección con el slip descontado
            mp = np.array([p[q].mean() for q in pl]); wd = np.array([tpf[q].sum() / max((tpf[q] + adv[q]).sum(), 1) for q in pl])
            wsg = (sign > 0).sum() / max((sign != 0).sum(), 1); wpn = (p > 0).sum() / max((p != 0).sum(), 1)
            STAT[(label[:3], sp, nm)] = dict(mean=p.mean(), med=np.median(p), sd=p.std(), ge=np.mean(p >= 150), le=np.mean(p <= -150), fl=np.mean(k[p >= 150] == 3), tp=tpf.mean())
            P(f"| {nm} | {D} | ${p.mean():+,.1f} [{ci(mp)[0]:+,.1f}, {ci(mp)[1]:+,.1f}] | ${np.median(p):+,.1f} | ${p.std():,.0f} | ${np.percentile(p, 10):+,.0f} – ${np.percentile(p, 90):+,.0f} | ${p.max():+,.0f} / ${p.min():+,.0f} | {np.mean(p >= 150) * 100:.1f} % ({np.mean(k[p >= 150] == 3) * 100:.0f} %) | {np.mean(p <= -150) * 100:.1f} % | **{tpf.sum() / (tpf + adv).sum() * 100:.1f} %** [{ci(wd)[0] * 100:.1f}, {ci(wd)[1] * 100:.1f}] | {tpf.mean() * 100:.1f} % | {wsg * 100:.1f} % | {wpn * 100:.1f} % |")
block("MGC 3 micros, SL = TP = 364, entrada 7:15 CT, flatten 14:30 CT", clean, 3, 9000.0, 364, 364, MGC["fee"], MGC["tick_usd"], 0.5, (0.0,))
block("MES nc 40, TP 32, SL 100 (liquidación por MLL a 40 ticks), 9:35 → 14:30 CT", mes, 40, 2000.0, 100, 32, 1.22, 1.25, 0.0, (0.0, 1.0))
g = lambda k_, f_: STAT[k_][f_]
P(f"\nLectura (cifras de las tablas). **MGC (stop llenado a 0.5; con stop exacto, como en `resultados_F2.md`, la sesión media es ≈ $20 mejor):** la sesión media pierde ${-g(('MGC', 0.0, 'alternate'), 'mean'):,.0f} (`alternate`), ${-g(('MGC', 0.0, 'siempre LARGO'), 'mean'):,.0f} (LARGO) y ${-g(('MGC', 0.0, 'siempre CORTO'), 'mean'):,.0f} (CORTO), con IC95 que incluye 0; desvío ≈ ${g(('MGC', 0.0, 'alternate'), 'sd'):,.0f} por sesión; {g(('MGC', 0.0, 'alternate'), 'ge') * 100:.0f} % de las sesiones llega a +$150 netos (de ellas, {g(('MGC', 0.0, 'alternate'), 'fl') * 100:.0f} % son FLATTEN) y {g(('MGC', 0.0, 'alternate'), 'le') * 100:.0f} % cae a −$150 o peor. El peor día (−$2,404) es el stop con salto; con el colchón inicial de la XFA ($2,000) esa sesión sería una liquidación de −$2,000. **MES:** la sesión es binaria, +$1,551 (TP) o −$2,000 (liquidación); el P&L medio de `alternate` es +${g(('MES', 0.0, 'alternate'), 'mean'):,.0f} (IC95 que incluye 0), de LARGO ${g(('MES', 0.0, 'siempre LARGO'), 'mean'):,.0f} y de CORTO +${g(('MES', 0.0, 'siempre CORTO'), 'mean'):,.0f}: la diferencia entre lados es la deriva de la muestra, no una señal. WR_dec = WR_todos = WR_pnl en MES (no hay FLATTEN relevante). **WR_signo ≈ 50 % con `alternate` en las dos: no hay información de dirección.** Un slippage de 1 tick resta ≈ $50 por sesión.\n")
# ---- Parte 2: 728x3
P("## Parte 2 — ¿Por qué 728×3 baja el equilibrio 0.72 pp? ¿Se remidió el WR con esa geometría?\n")
P("**Respuesta corta sobre la medición: NO se remidió.** En H1 (y en E §4, F1, G4, H6 §3) el eje «WR» es una **etiqueta**: la deriva en ticks/día se calibra **una sola vez** con `xfa/worlds.py::drift_for_wr(..., sl=364, tp=364)`, que simula el bracket nominal 364/364 con 1 contrato y colchón 10⁹ (sin MLL), y esa **misma deriva** se aplica a la geometría que se evalúe. El «equilibrio de 728×3 = 47.72 %» es, por tanto, «la deriva que equivale a 47.72 % en un bracket 364/364»; **no** es el WR_dec que se mediría operando 728×3. A continuación se remide.\n")
# 2a. WR remedido por geometria y etiqueta
geoms = ((364, 364, "3×364"), (728, 728, "3×728"))
LV = {}
P("### 2a. WR_dec remedido con cada geometría, a la misma deriva (etiqueta de WR en el eje)\n")
P("`nominal` = bracket simétrico sin MLL, 1 contrato (lo que mide la etiqueta). `con MLL, colchón inicial $2,000` = 3 micros: la liquidación ocurre a **667 ticks** ($2,000 / $3) y el TP está a 728. `con MLL, colchón $2,178` = tras el 1.er TP (balance ≈ colchón ≈ $2,178): la liquidación está a ≈ 726 ticks, de nuevo casi simétrico. Cada celda es el WR_dec **por sesión** sobre los 443 días reales (ambos lados); n decididas pequeño en 3×728 ⇒ ruido de ± 4–5 pp. (No se usa la razón TP/decididas acumulada en vidas simuladas: está sesgada por la regla de parada, porque cada vida termina con una liquidación.)\n")
P("| etiqueta de WR | geometría | nominal | con MLL, colchón inicial $2,000 | con MLL, colchón $2,178 | % de sesiones decididas (colchón $2,000) |\n|---|---|---|---|---|---|")
sub = type(clean)([d for d, m in zip(clean.dates, mk) if m], clean.ref[mk], clean.op[mk], clean.hi[mk], clean.lo[mk], clean.cl[mk], [])
def wr_k(dd_, nc, cush, sl, tp, dm):
    t = a_ = 0.0
    for s_ in (1, -1):
        k, _ = sim_day(dd_, s_, nc, cush, slip=0.0, exit_slip=0.0, sl=sl, tp=tp, fee=0.0, tick_usd=1.0, drift=dm); t += (k == 0).mean(); a_ += ((k == 1) | (k == 2)).mean()
    return t / (t + a_), (t + a_) / 2
for wr in (0.45, 0.474, 0.485, 0.50, 0.52):
    dm = 0.0 if abs(wr - 0.50) < 1e-9 else drift_for_wr(clean, mk, wr)
    for sl, tp, nm in geoms:
        nom = wr_k(sub, 1, 1e9, sl, tp, dm)[0]; m0, dec0 = wr_k(sub, 3, 2000.0, sl, tp, dm); m1 = wr_k(sub, 3, 2178.0, sl, tp, dm)[0]
        days = BarDays(clean, MGC["tick_usd"], MGC["fee"], sl, tp, slip=(0.0,), mask=mk, cush_max=9000.0, drift=dm, stop_frac=0.5)
        r = simulate_life(days, Rules(), pol_fixed(3, sl, tp), n=40000, seed=21, record_k=14); LV[(wr, sl)] = dict(r=r)
        P(f"| {wr * 100:.1f} % | {nm} | {nom * 100:.1f} % | {m0 * 100:.1f} % | {m1 * 100:.1f} % | {dec0 * 100:.0f} % |")
    print("  2a", wr, round(time.time() - t0), "s", flush=True)
P("\nLectura: en 3×364 la etiqueta se cumple (el MLL de 667 ticks no toca un bracket de 364). **En 3×728 el WR_dec por sesión con colchón $2,000 es ≈ 4–5 pp MENOR que la etiqueta** (liquidación a 667 < TP a 728: martingala ⇒ 667/(667+728) = 47.8 %; con tiempo finito, además, la barrera más cercana se toca más), y vuelve a ≈ la etiqueta tras el primer TP (colchón ≈ $2,178). **El 728×3 no baja el equilibrio por un WR mayor ni por simetría: su WR_dec real es peor que el de la etiqueta.**\n")
# 2b. que cambia: composicion de las vidas
P("### 2b. Qué cambia de verdad: composición de las vidas (a deriva = etiqueta 50 % y 48.5 %)\n")
P("| etiqueta | geometría | sesiones decididas por vida (TP / SL / liquidación) | sesiones FLATTEN por vida | P(≥ 1 pago) | cobrado por XFA | vida media (días) | P(muere sin cobrar nada) |\n|---|---|---|---|---|---|---|---|")
for wr in (0.50, 0.485):
    for sl, tp, nm in geoms:
        r = LV[(wr, sl)]["r"]; net = r["pay_net"].sum(1)
        P(f"| {wr * 100:.1f} % | {nm} | {r['tp'].mean():.2f} / {r['sl'].mean():.2f} / {r['liq'].mean():.2f} | {r['flat'].mean():.2f} | {(r['npay'] > 0).mean() * 100:.1f} % | ${net.mean():,.0f} | {r['life'].mean():.1f} | {((r['npay'] == 0) & (~r['alive'])).mean() * 100:.1f} % |")
# 2c. z* (ambas etapas, costos A = $240) y WR remedido en z*
P("\n### 2c. La medida comparable entre geometrías: deriva z* necesaria para neto anual = 0 (misma convención que H1: deriva en las dos etapas; slip empírico de 7 obs.; costos A $240) y WR_dec remedido en z*\n")
OBS = (0.0, 1.0, 0.0, 3.0, -1.0, 1.0, 3.0); ES = tuple(sorted(set(OBS))); EP = tuple(OBS.count(s_) / 7 for s_ in ES)
sig_s = float(np.std(mes.cl[:, -1])); zs = (-0.16, -0.12, -0.09, -0.07, -0.05, -0.03, 0.0)
cbz = {z: combine_bank(mes, 100000, "P0", ES, EP, seed=11, drift=z * sig_s) for z in zs}
P("| geometría | neto $/año a z = 0 (costos A) | z* (μ/σ de la sesión) | etiqueta de WR equivalente (bracket 364 nominal) | **WR_dec remedido en z*: colchón $2,000** | colchón $2,178 |\n|---|---|---|---|---|---|")
ZS = {}
for sl, tp, nm in geoms:
    vals = []
    for z in zs:
        days = BarDays(clean, MGC["tick_usd"], MGC["fee"], sl, tp, slip=(0.0,), mask=mk, cush_max=9000.0, drift=z * sig_m, stop_frac=0.5)
        life, pday, pnet = xfa_bank(days, Rules(), pol_fixed(3, sl, tp), 60000, seed=21); vals.append(run_chain(cbz[z][0], cbz[z][1], life, pday, pnet, n=30000, seed=5, ops=240.0)["net"].mean())
    vals = np.array(vals); ze = next((zs[i] + (zs[i + 1] - zs[i]) * (-vals[i]) / (vals[i + 1] - vals[i]) for i in range(len(zs) - 1) if vals[i] < 0 <= vals[i + 1]), float("nan"))
    lab = wr_k(sub, 1, 1e9, 364, 364, ze * sig_m)[0]; w0 = wr_k(sub, 3, 2000.0, sl, tp, ze * sig_m)[0]; w1 = wr_k(sub, 3, 2178.0, sl, tp, ze * sig_m)[0]; ZS[nm] = (ze, lab, w0, w1, vals[-1])
    P(f"| {nm} | ${vals[-1]:,.0f} | {ze:+.3f} | {lab * 100:.2f} % | **{w0 * 100:.2f} %** | {w1 * 100:.2f} % |")
    print("  2c", nm, round(time.time() - t0), "s", flush=True)
P(f"\n**Diferencia de equilibrio en la etiqueta, medida aquí con una rejilla de z (resolución ± 0.2 pp; H1 reportó −0.72 como paso de la cascada tras el finish-line, y −0.67 como componente aislado en H1b): {(ZS['3×728'][1] - ZS['3×364'][1]) * 100:+.2f} pp.** **Diferencia en WR_dec por sesión remedido con cada geometría (colchón $2,000): {(ZS['3×728'][2] - ZS['3×364'][2]) * 100:+.2f} pp.** Si el segundo número es negativo o ≈ 0, el 728×3 necesita *menos deriva*, no *menos WR*: el «−0.72 pp» (entre −0.5 y −0.8 según el método) es un efecto de la estructura de pagos medido en una escala —la etiqueta del bracket 364 nominal— que no corresponde a la geometría evaluada.\n")
# 2d. descomposición con geometrías contrafactuales
P("### 2d. Descomposición: ¿importa la simetría 667/728? Geometrías contrafactuales a la misma deriva (etiqueta 50 % y 48.5 %)\n")
P("| etiqueta | TP / SL (ticks) | decididas por vida (TP / SL / liq.) | FLATTEN por vida | P(≥ 1 pago) | cobrado por XFA | pago medio si cobra | vida (días) |\n|---|---|---|---|---|---|---|---|")
for wr in (0.50, 0.485):
    dm = 0.0 if wr == 0.50 else drift_for_wr(clean, mk, wr)
    for sl, tp in ((364, 364), (546, 546), (667, 667), (667, 728), (728, 728)):
        days = BarDays(clean, MGC["tick_usd"], MGC["fee"], sl, tp, slip=(0.0,), mask=mk, cush_max=9000.0, drift=dm, stop_frac=0.5)
        r = simulate_life(days, Rules(), pol_fixed(3, sl, tp), n=40000, seed=21, record_k=14); net = r["pay_net"].sum(1); pay = r["npay"] > 0
        P(f"| {wr * 100:.1f} % | TP {tp} / SL {sl} | {r['tp'].mean():.2f} / {r['sl'].mean():.2f} / {r['liq'].mean():.2f} | {r['flat'].mean():.2f} | {pay.mean() * 100:.1f} % | ${net.mean():,.0f} | ${net[pay].mean():,.0f} | {r['life'].mean():.1f} |")
    print("  2d", wr, round(time.time() - t0), "s", flush=True)
P("\nLectura (cifras de la tabla): el efecto de ensanchar de 364 a 728 es **monótono** (546 queda en medio) y **no depende de la simetría 667/728** (TP 728 / SL 667 ≈ 728/728). Existe **ya a deriva 0** (etiqueta 50 %: $824 vs $647), así que **no es cosecha de deriva ni mejor puntería**. Cambia la composición: las sesiones decididas por vida (sin contar la liquidación final) caen de ≈ 3.5 a ≈ 0.9, los FLATTEN suben de ≈ 5.4 a ≈ 8.8, la vida casi no cambia (9.9 → 10.7 días) y P(≥ 1 pago) baja (33.0 → 28.1 %), pero el pago cuando llega es mayor (ver 2e).\n")
# 2e. tamaño de los pagos
P("### 2e. Dónde está el dinero: tamaño de los pagos (deriva 0)\n")
P("| geometría | P(≥ 1 pago) | pagos por vida que cobra | P(≥ 2 pagos) | primer pago neto medio | pago neto medio (todos) | mediana de días al 1.er pago | p90 |\n|---|---|---|---|---|---|---|---|")
for sl, tp, nm in geoms:
    days = BarDays(clean, MGC["tick_usd"], MGC["fee"], sl, tp, slip=(0.0,), mask=mk, cush_max=9000.0, drift=0.0, stop_frac=0.5)
    r = simulate_life(days, Rules(), pol_fixed(3, sl, tp), n=60000, seed=21, record_k=14); net = r["pay_net"]; pay = r["npay"] > 0; kk = (net > 0).sum(1)
    P(f"| {nm} | {pay.mean() * 100:.1f} % | {kk[pay].mean():.2f} | {(kk >= 2).mean() * 100:.1f} % | ${r['paid_first'][pay].mean():,.0f} | ${net[net > 0].mean():,.0f} | {np.median(r['first_pay_day'][pay]):.0f} | {np.percentile(r['first_pay_day'][pay], 90):.0f} |")
P("\n**Mecanismo (lo que muestran las cifras; la causa última dentro del motor no se aisló con un experimento de apagado):** con 3×728 cada sesión ganadora suma ≈ $2,178 en lugar de ≈ $1,092 y cada FLATTEN positivo cuenta igual para los 5 días ≥ $150; cuando la cuenta llega a ser elegible su saldo —y por tanto el 50 % que se puede retirar (tope $2,000)— es mayor: el **primer pago medio sube de $1,051 a $1,335 y el pago medio de $1,235 a $1,519**, con la misma proporción de vidas con ≥ 2 pagos (10.1 vs 10.3 %). Es **estructura de pagos y de saldo**, no WR. Además un solo TP de $2,178 supera los +$2,000 que fijan el piso del MLL en $0 (`rules.lock`), cosa que en 3×364 exige dos TP seguidos.\n")
open(os.path.join(HERE, "resultados_H1c.md"), "w", encoding="utf-8").write("\n".join(out))
