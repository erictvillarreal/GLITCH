"""Parte J, J4-a: ¿vale la pena un kill-switch por colchón del MLL? Simula la política «tamaño limitado por el colchón» frente a la de producción (3×364). -> resultados_J4a.md
    cd glitch/experimentos/parteJ; GLITCH_MGC_PARQUET=... PYTHONPATH=../.. python3 j4a_killswitch_sim.py [--quick]
MODELADO. Misma base que J8 (MGC 443 días, slippage empírico de 8 obs., stop 0.5, OPS aparte). Semillas fijas."""
import argparse, math, os, sys, time
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "..", "xfa")); sys.path.insert(0, os.path.join(HERE, "..", "preservacion"))
from worlds import MGC, drift_for_wr, gold_mask, mgc_days
from xfa_engine import BarDays, Policy, Rules, pol_fixed, simulate_life
ap = argparse.ArgumentParser(); ap.add_argument("--quick", action="store_true"); A = ap.parse_args()
B = 12 if A.quick else 30; N_PT = 20000 if A.quick else 60000; N_BS = 4000 if A.quick else 8000; SEED = 20261026
t0 = time.time(); out = []; P = lambda s="": (print(s, flush=True), out.append(s))
clean = mgc_days(True); mk = gold_mask(clean, True)
EMP8 = (-1.0, 0.0, 1.0, 3.0); EMP8_P = (1 / 8, 3 / 8, 2 / 8, 2 / 8)
rng = np.random.default_rng(SEED)
def blocks(npool, Bn):
    nb = math.ceil(npool / 5); st = rng.integers(0, npool - 4, size=(Bn, nb)); return (st[:, :, None] + np.arange(5)).reshape(Bn, -1)[:, :npool]
pools_bs = blocks(int(mk.sum()), B)
PER_MICRO = 364 * MGC["tick_usd"] + MGC["fee"] + 3 * MGC["tick_usd"]          # pérdida máxima por micro: SL + comisión + 3 ticks de margen de slippage
def cushion_nc(minimum_stop):
    # nc = micros que caben en el colchón (pérdida máxima < colchón), tope 3; `minimum_stop`: por debajo de ese colchón no se opera
    return lambda st: np.where(st.cushion >= minimum_stop, np.clip(np.floor(st.cushion / PER_MICRO), 0, 3), 0).astype(int)
POL = [("3×364 (producción, sin guardia)", pol_fixed(3, 364, 364)),
       (f"guardia: nc = ⌊colchón / ${PER_MICRO:,.0f}⌋ (máx 3), no opera si < ${PER_MICRO:,.0f}", Policy("g1", cushion_nc(PER_MICRO), "max", 364, 364)),
       ("guardia estricta: igual, pero no opera si el colchón < $800", Policy("g2", cushion_nc(800.0), "max", 364, 364)),
       ("guardia solo-1-micro: con colchón < $1,200 opera 1 micro (si cabe)", Policy("g3", lambda st: np.where(st.cushion >= 1200.0, 3, np.where(st.cushion >= PER_MICRO, 1, 0)).astype(int), "max", 364, 364))]
def metrics(r):
    dead = ~r["alive"]
    return dict(paid=r["paid"].mean(), p1=(r["npay"] >= 1).mean(), life=r["life"].mean(), liq=(r["liq"] > 0).mean(), d3=((r["life"] <= 3) & dead).mean(), dtrade=r["dtrade"].mean())
P("# resultados_J4a — ¿un kill-switch por colchón del MLL mejora algo? (simulación)\n")
P(f"**Fuente y estado.** MODELADO sobre 443 días reales de MGC (sin la ventana de oro), motor `xfa_engine`, slippage de entrada = 8 obs. (8.ª inferida = 0, NO VERIFICADA), stop 0.5. Pérdida máxima por micro supuesta: ${PER_MICRO:,.0f} (SL 364 + comisión + 3 ticks). `colchón` = balance − piso del MLL. IC95 = {B} remuestras de bloques de 5 días ({N_BS:,} vidas cada una; semillas comunes ⇒ diferencias pareadas).\n")
for lab, wr in (("WR 50 %", 0.50), ("WR 47.4 %", 0.474)):
    dm = 0.0 if abs(wr - 0.5) < 1e-9 else drift_for_wr(clean, mk, wr)
    days = BarDays(clean, MGC["tick_usd"], MGC["fee"], 364, 364, slip=EMP8, slip_p=EMP8_P, mask=mk, cush_max=9000.0, drift=dm, stop_frac=0.5)
    base_pool = days.pool.copy(); res = {}
    for nm, pol in POL:
        days.pool = base_pool; pt = metrics(simulate_life(days, Rules(), pol, n=N_PT, seed=21))
        bs = []
        for q in pools_bs:
            days.pool = base_pool[q % len(base_pool)]; bs.append(metrics(simulate_life(days, Rules(), pol, n=N_BS, seed=21)))
        res[nm] = (pt, bs)
    P(f"\n### {lab}\n")
    P("| política | cobrado por XFA [IC95] | Δ vs producción (pareada) [IC95] | ¿distinguible? | P(≥ 1 pago) | P(liquidada por MLL) | P(muerte ≤ 3 días) | vida (días) |\n|---|---|---|---|---|---|---|---|")
    bpt, bbs = res[POL[0][0]]
    for nm, _ in POL:
        pt, bs = res[nm]; pv = np.array([x["paid"] for x in bs]); dv = pv - np.array([x["paid"] for x in bbs])
        lo, hi = np.percentile(dv, 2.5), np.percentile(dv, 97.5)
        P(f"| {nm} | ${pt['paid']:,.0f} [{np.percentile(pv, 2.5):,.0f}, {np.percentile(pv, 97.5):,.0f}] | " + ("—" if nm == POL[0][0] else f"${pt['paid'] - bpt['paid']:+,.0f} [{lo:+,.0f}, {hi:+,.0f}]") +
          f" | " + ("—" if nm == POL[0][0] else ("SÍ" if (lo > 0 or hi < 0) else "NO")) + f" | {pt['p1'] * 100:.1f} % | {pt['liq'] * 100:.1f} % | {pt['d3'] * 100:.1f} % | {pt['life']:.1f} |")
    print("  ", lab, round(time.time() - t0), "s", flush=True)
P("\nLectura: ver J4_PARCHES.md (sección a). «P(liquidada por MLL)» es la fracción de vidas que terminan con la cuenta liquidada por Topstep; con la guardia una vida también termina cuando el colchón ya no alcanza ni para 1 micro (queda sin operar, no liquidada).")
open(os.path.join(HERE, "resultados_J4a.md"), "w", encoding="utf-8").write("\n".join(out) + "\n")
print("OK", round(time.time() - t0), "s")

# ── Cadena anual (Combine MES → XFA MGC): ¿la guardia mejora el neto ANUAL por cuenta? ──
from chain import combine_bank, run_chain, xfa_bank
from daydata import load_days
mes = load_days(); sig_m = float(np.std(clean.cl[mk][:, -1])); sig_s = float(np.std(mes.cl[:, -1])); OPS = 245.0
P("\n## Neto anual por cuenta (cadena Combine P0 → XFA, OPS $245, horizonte 252 días; sin remuestreo de días, 30,000 vidas)\n")
P("| política | WR 50 % | WR 47.4 % |\n|---|---|---|")
rows = {nm: [] for nm, _ in POL}
for wr in (0.50, 0.474):
    dm = 0.0 if abs(wr - 0.5) < 1e-9 else drift_for_wr(clean, mk, wr); ds = dm / sig_m * sig_s
    ps, cd = combine_bank(mes, 30000, "P0", EMP8, EMP8_P, seed=11, exit_slip=3.0, drift=ds)
    days = BarDays(clean, MGC["tick_usd"], MGC["fee"], 364, 364, slip=EMP8, slip_p=EMP8_P, mask=mk, cush_max=9000.0, drift=dm, stop_frac=0.5)
    for nm, pol in POL:
        life, pday, pnet = xfa_bank(days, Rules(), pol, 30000, seed=21)
        rows[nm].append(float(run_chain(ps, cd, life, pday, pnet, n=30000, seed=5, ops=0.0)["net"].mean()) - OPS)
for nm, _ in POL: P(f"| {nm} | ${rows[nm][0]:,.0f} | ${rows[nm][1]:,.0f} |")
P("\n(Una vida con guardia que queda sin operar se cierra en el motor tras 30 días sin operar; un operador real abandonaría la cuenta antes y volvería a comprar: el número es conservador para la guardia.)")
open(os.path.join(HERE, "resultados_J4a.md"), "w", encoding="utf-8").write("\n".join(out) + "\n")
print("OK2", round(time.time() - t0), "s")
