"""Parte J, J8: estrategia del primer día XFA (mié 28-oct, FOMC). H0-0 por candidata XFA, tabla de decisión con IC95 y pruebas pareadas, efecto FOMC. -> resultados_J8.md
    cd glitch/experimentos/parteJ; GLITCH_MGC_PARQUET=... PYTHONPATH=../.. python3 j8_primer_dia_xfa.py [--quick]
Todo es MODELADO sobre 488 días reales de MGC (7:15 → 14:25 CT, contrato dominante). Semillas fijas. No toca producción."""
import argparse, math, os, sys, time, datetime as dt
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "..", "xfa")); sys.path.insert(0, os.path.join(HERE, "..", "preservacion"))
from daydata import sim_day, load_days
from strategies.geometry_pure import decide_side, trading_day_index
from worlds import MGC, MGC_PARQUET, drift_for_wr, gold_mask, mgc_days
from xfa_engine import BarDays, Policy, Rules, pol_fixed, simulate_life
ap = argparse.ArgumentParser(); ap.add_argument("--quick", action="store_true"); A = ap.parse_args()
B = 12 if A.quick else 40; N_PT = 20000 if A.quick else 60000; N_BS = 4000 if A.quick else 8000; SEED = 20261026
t0 = time.time(); out = []; P = lambda s="": (print(s, flush=True), out.append(s))
clean = mgc_days(True); mk = gold_mask(clean, True)
rng = np.random.default_rng(SEED)
def blocks(npool, Bn):
    nb = math.ceil(npool / 5); st = rng.integers(0, npool - 4, size=(Bn, nb)); return (st[:, :, None] + np.arange(5)).reshape(Bn, -1)[:, :npool]
def ci(x): return np.percentile(x, 2.5), np.percentile(x, 97.5)
EMP8 = (-1.0, 0.0, 1.0, 3.0); EMP8_P = (1 / 8, 3 / 8, 2 / 8, 2 / 8)       # 7 obs de Eric + una 8.ª INFERIDA (=0) a partir de «media 0.9, N=8» (suma 7 → 0.875): NO VERIFICADA
BAR_FOMC_RELEASE = (13 * 60 - (7 * 60 + 15)) // 5                            # índice de la barra de 5 min que empieza a las 13:00 CT (7:15 + 5·i)

P("# resultados_J8 — Estrategia del primer día XFA (miércoles 28-oct-2026, día de FOMC)\n")
P("**Fuentes y estado.** Días reales de 5 min de MGC (datos limpios de contrato, `GLITCH_MGC_PARQUET`; 488 días, 443 sin la ventana de oro 14-nov-2025 → 26-ene-2026), reproducidos con el motor `sim_day` / `xfa_engine` de las Partes A/D: **MODELADO sobre historia real**. No son sesiones vivas (no tengo el CSV de TopstepX ni el Gist). Fechas FOMC: `fomc_dates.txt` (federalreserve.gov, consultada 20-oct): MEDIDO. Dirección de producción: `strategies/geometry_pure.py::decide_side(trading_day_index(fecha), 'alternate')` (código en `main`, a387a70).")
sides = {d: decide_side(trading_day_index(d), "alternate") for d in (dt.date(2026, 10, 27), dt.date(2026, 10, 28), dt.date(2026, 10, 29))}
P(f"**Dirección de producción (calculada con el código, no supuesta):** mar 27-oct → {'LARGO' if sides[dt.date(2026,10,27)]==1 else 'CORTO'}; **mié 28-oct → {'LARGO' if sides[dt.date(2026,10,28)]==1 else 'CORTO'}**; jue 29-oct → {'LARGO' if sides[dt.date(2026,10,29)]==1 else 'CORTO'} (MES y MGC usan el mismo índice). Si la activación de la XFA consume un día (el modelo supone 1), el primer día XFA sería el jueves: se reporta también ese caso.")
P("**Etiquetas de configuración (J8.1).** «XFA / Cerebro 2» = MGC, 3 micros, SL = TP = 364 ticks, `alternate`, entrada 7:13–7:15 CT, flatten 14:30 CT (`CANDIDATES['MGC']` = `xfa_mgc_config('50K')`). «Combine / Cerebro 1» = MES nc 40, TP 32, liquidación por MLL a 40 ticks (el SL de 100 no opera), 9:35 → 14:30 CT. **Las cifras de este archivo son de XFA/MGC salvo que diga MES.** Supuestos comunes: comisión MGC $1.92 por micro round-turn; stop llenado a 0.5 (convención C1); slippage de entrada: ver cada sección.\n")

# ───────────────────────── Parte A: H0-0 por candidata XFA ─────────────────────────
P("## A. H0-0 por candidata XFA (P&L neto por sesión, MGC, 488 días; colchón 9,000 como en `resultados_H1c.md` salvo la columna «LIQ día 1»)\n")
P("`alternate (histórico)` = la alternancia que habría tocado en cada fecha real (la misma que H0-0 de H1c); `alternate (promedio L/C)` = promedio de LARGO y CORTO, que es lo que espera una alternancia de paridad desconocida. **Slip de entrada 0** (sin supuesto). «LIQ día 1» = P(la sesión toca la liquidación por MLL) con el colchón inicial de $2,000 (la XFA arranca con 2,000 de colchón).\n")
CAND = [("3×364 (producción)", 3, 364, 364, "14:25"), ("3×728", 3, 728, 728, "14:25"), ("1 micro, 364", 1, 364, 364, "14:25"), ("4 micros, 364 (1.ª etapa de 4→1)", 4, 364, 364, "14:25"),
        ("3×364, flatten 13:30", 3, 364, 364, "13:25"), ("3×364, flatten 12:00", 3, 364, 364, "11:55"), ("3×364, flatten 10:30", 3, 364, 364, "10:25")]
_dd = {}
def dd_for(last):
    if last not in _dd:
        h, m = map(int, last.split(":")); _dd[last] = clean if last == "14:25" else load_days(MGC_PARQUET, MGC["ref_hm"], h * 60 + m, MGC["tick"], fill_gaps=True, dominant_contract=True)
    return _dd[last]
PL = None
P("| candidata | regla | n | P&L neto medio/sesión [IC95] | desvío | ≥ +$150 | ≤ −$150 | TP % | SL+LIQ % | FLATTEN % | WR_dec | LIQ día 1 (colchón $2,000) |\n|---|---|---|---|---|---|---|---|---|---|---|---|")
H00 = {}
for nm, nc, sl, tp, last in CAND:
    dd = dd_for(last); D = dd.D
    if PL is None or PL.shape[1] != D: PL = blocks(D, 1000)
    alt = np.array([decide_side(trading_day_index(d), "alternate") for d in dd.dates])
    r = {s: sim_day(dd, s, nc, 9000.0, slip=0.0, exit_slip=0.0, sl=sl, tp=tp, fee=MGC["fee"], tick_usd=MGC["tick_usd"], stop_frac=0.5) for s in (1, -1)}
    rl = {s: sim_day(dd, s, nc, 2000.0, slip=0.0, exit_slip=0.0, sl=sl, tp=tp, fee=MGC["fee"], tick_usd=MGC["tick_usd"], stop_frac=0.5) for s in (1, -1)}
    for rn, kk, pp, kl in (("alternate (histórico)", np.where(alt == 1, r[1][0], r[-1][0]), np.where(alt == 1, r[1][1], r[-1][1]), np.where(alt == 1, rl[1][0], rl[-1][0])),
                           ("siempre LARGO (= mié 28)", r[1][0], r[1][1], rl[1][0]), ("siempre CORTO", r[-1][0], r[-1][1], rl[-1][0]),
                           ("alternate (promedio L/C)", None, None, None)):
        if kk is None:
            pp = 0.5 * (r[1][1] + r[-1][1]); kk = None
            mp = np.array([pp[q].mean() for q in PL]); tpf = 0.5 * ((r[1][0] == 0).astype(float) + (r[-1][0] == 0)); sf = 0.5 * (((r[1][0] == 1) | (r[1][0] == 2)).astype(float) + ((r[-1][0] == 1) | (r[-1][0] == 2)))
            ff = 0.5 * ((r[1][0] == 3).astype(float) + (r[-1][0] == 3)); ge = 0.5 * ((r[1][1] >= 150).astype(float) + (r[-1][1] >= 150)); le = 0.5 * ((r[1][1] <= -150).astype(float) + (r[-1][1] <= -150))
            lq = 0.5 * ((rl[1][0] == 2).astype(float) + (rl[-1][0] == 2))
            wd = tpf.mean() / max(tpf.mean() + sf.mean(), 1e-9)
            P(f"| {nm} | {rn} | {D} | ${pp.mean():+,.1f} [{ci(mp)[0]:+,.1f}, {ci(mp)[1]:+,.1f}] | ${pp.std():,.0f} | {ge.mean() * 100:.1f} % | {le.mean() * 100:.1f} % | {tpf.mean() * 100:.1f} | {sf.mean() * 100:.1f} | {ff.mean() * 100:.1f} | {wd * 100:.1f} % | {lq.mean() * 100:.1f} % |")
            H00[(nm, rn)] = dict(mean=pp.mean(), ci=ci(mp)); continue
        tpf = (kk == 0).astype(float); sf = ((kk == 1) | (kk == 2)).astype(float)
        mp = np.array([pp[q].mean() for q in PL]); wd = tpf.sum() / max((tpf + sf).sum(), 1)
        P(f"| {nm} | {rn} | {D} | ${pp.mean():+,.1f} [{ci(mp)[0]:+,.1f}, {ci(mp)[1]:+,.1f}] | ${pp.std():,.0f} | {np.mean(pp >= 150) * 100:.1f} % | {np.mean(pp <= -150) * 100:.1f} % | {tpf.mean() * 100:.1f} | {sf.mean() * 100:.1f} | {np.mean(kk == 3) * 100:.1f} | {wd * 100:.1f} % | {np.mean(kl == 2) * 100:.1f} % |")
        H00[(nm, rn)] = dict(mean=pp.mean(), ci=ci(mp))
    print("  A", nm, round(time.time() - t0), "s", flush=True)
P("\nLectura A: ver la sección de conclusiones del reporte; los IC95 son remuestras de bloques de 5 días de la historia real (1,000).\n")

# ───────────────────────── Parte B: tabla de decisión a nivel vida ─────────────────────────
class FixedSide(BarDays):
    def __init__(self, *a, fixed=None, **k): super().__init__(*a, **k); self.fixed = fixed
    def resolve(self, idx, si, side, nc, cush, sl):
        return super().resolve(idx, si, np.full_like(side, self.fixed) if self.fixed is not None else side, nc, cush, sl)
class Day0(BarDays):
    """El día 1 (t = 0) se sortea de `day0` (p. ej. días FOMC históricos); los demás, del pool."""
    sequential = True
    def __init__(self, *a, day0=None, **k): super().__init__(*a, **k); self.day0 = day0
    def draw(self, rng, n, t):
        idx = self.day0[rng.integers(0, len(self.day0), n)] if (t == 0 and self.day0 is not None) else self.pool[rng.integers(0, len(self.pool), n)]
        return idx, rng.choice(len(self.slips), size=n, p=self.slip_p)
def pol41(): return Policy("4→1", lambda st: np.where(st.b < 1500.0, 4, 1), lambda st, g: np.where(st.b >= 1500.0, g, 0.0), 364, 364)
def pol_fn(name, fn, sl=364): return Policy(name, fn, "max", sl, sl)
fomc = [dt.date.fromisoformat(l.strip()) for l in open(os.path.join(HERE, "..", "direccion_e", "fomc_dates.txt")) if l.strip() and not l.startswith("#")]
fidx = np.array([i for i, d in enumerate(clean.dates) if d in set(fomc)], int)
fidx_mk = np.array([i for i in fidx if mk[i]], int)
P(f"## B. Tabla de decisión para el primer día XFA (vidas simuladas hasta liquidación; MGC; slippage de entrada = distribución empírica de 8 obs. {dict(zip(EMP8, EMP8_P))}, **8.ª observación inferida = 0, NO VERIFICADA**; OPS $245/año)\n")
P(f"Cada celda: media sobre {N_PT:,} vidas, IC95 = percentiles de {B} remuestras de bloques de 5 días de los {int(mk.sum())} días del pool (cada una con {N_BS:,} vidas; mismas semillas en todas las políticas ⇒ las **diferencias son pareadas**). «Cobrado» = pagos netos al trader (división 90/10, tope $2,000 por pago, 5 días ≥ $150, regla de ganancia desde el 2.º pago; `xfa_engine.Rules()` por defecto = `RULEBOOK_XFA.md`), **no** descuenta la activación de $149 (igual para todas). «Neto tras OPS» resta $245 × vida/252. La deriva es la etiqueta de WR (nominal 364/364); 50 % = deriva 0 sobre la historia real.\n")
def build(dd, mask_, sl, drift, **kw):
    return BarDays(dd, MGC["tick_usd"], MGC["fee"], sl, sl, slip=EMP8, slip_p=EMP8_P, mask=mask_, cush_max=9000.0, drift=drift, stop_frac=0.5, **kw)
def metrics(r):
    dead = ~r["alive"]; fp = r["first_pay_day"]
    return dict(paid=r["paid"].mean(), p1=(r["npay"] >= 1).mean(), d1=((r["life"] <= 1) & dead).mean(), d3=((r["life"] <= 3) & dead).mean(), life=r["life"].mean(),
                med=(np.median(fp[fp >= 0]) + 1) if (fp >= 0).any() else float("nan"), first=r["paid_first"][fp >= 0].mean() if (fp >= 0).any() else float("nan"))
POL = [("3×364 alternate (producción)", dict(sl=364), pol_fixed(3, 364, 364)),
       ("3×728", dict(sl=728), pol_fixed(3, 728, 728)),
       ("4→1 micros (4 hasta saldo $1,500, luego 1)", dict(sl=364), pol41()),
       ("1 micro toda la vida", dict(sl=364), pol_fixed(1, 364, 364)),
       ("1 micro la 1.ª semana (5 días), luego 3", dict(sl=364), pol_fn("1m-sem", lambda st: np.where(st.t < 5, 1, 3))),
       ("1 micro SOLO el día 1, luego 3", dict(sl=364), pol_fn("1m-d1", lambda st: np.where(st.t < 1, 1, 3))),
       ("NO operar el día 1, luego 3", dict(sl=364), pol_fn("skip-d1", lambda st: np.where(st.t < 1, 0, 3))),
       ("3×364 siempre LARGO (sin respaldo fuera de muestra)", dict(sl=364, fixed=1), pol_fixed(3, 364, 364)),
       ("3×364 siempre CORTO (sin respaldo fuera de muestra)", dict(sl=364, fixed=-1), pol_fixed(3, 364, 364)),
       ("3×364, flatten 12:00 CT", dict(sl=364, last="11:55"), pol_fixed(3, 364, 364)),
       ("3×364, flatten 10:30 CT", dict(sl=364, last="10:25"), pol_fixed(3, 364, 364))]
LABELS = (("WR 50 % (deriva 0)", 0.50), ("WR 47.4 % (≈ el medido)", 0.474))
RES = {}
pools_bs = blocks(int(mk.sum()), B)                                           # posiciones dentro del pool
def run_policy(spec, pol, dm, parity, day0=None):
    last = spec.get("last", "14:25"); dd = dd_for(last); mask_ = gold_mask(dd, True)
    kw = {}
    if "fixed" in spec: cls = FixedSide; kw["fixed"] = spec["fixed"]
    elif day0 is not None: cls = Day0; kw["day0"] = day0
    else: cls = BarDays
    days = cls(dd, MGC["tick_usd"], MGC["fee"], spec["sl"], spec["sl"], slip=EMP8, slip_p=EMP8_P, mask=mask_, cush_max=9000.0, drift=dm, stop_frac=0.5, **kw)
    base_pool = days.pool.copy()
    pt = metrics(simulate_life(days, Rules(), pol, n=N_PT, seed=21, start_parity=parity))
    bs = []
    for q in pools_bs:
        days.pool = base_pool[q % len(base_pool)]
        bs.append(metrics(simulate_life(days, Rules(), pol, n=N_BS, seed=21, start_parity=parity)))
    return pt, bs
for lab, wr in LABELS:
    dm = 0.0 if abs(wr - 0.5) < 1e-9 else drift_for_wr(clean, mk, wr)
    for parity, ptag in ((0, "mié 28-oct = LARGO"), (1, "jue 29-oct = CORTO")):
        if parity == 1 and lab != LABELS[0][0]: continue
        for nm, spec, pol in POL:
            if parity == 1 and nm not in (POL[0][0], POL[1][0], POL[2][0], POL[3][0], POL[4][0], POL[5][0], POL[6][0]): continue
            RES[(lab, ptag, nm)] = run_policy(spec, pol, dm, parity)
        print("  B", lab, ptag, round(time.time() - t0), "s", flush=True)
def pm(vals, f=lambda x: f"{x:,.0f}"):
    return f"{f(np.mean(vals))} [{f(np.percentile(vals, 2.5))}, {f(np.percentile(vals, 97.5))}]"
def table(lab, ptag, base_nm=POL[0][0]):
    P(f"\n### {lab} — primer día XFA: {ptag}\n")
    P("| política | cobrado esperado por XFA [IC95] | Δ vs 3×364 (pareada) [IC95] | ¿distinguible? | P(≥ 1 pago) [IC95] | P(muerte en 3 días) [IC95] | P(muerte el día 1) | vida (días) | mediana días al 1.er pago | 1.er pago medio | neto tras OPS $245/año |\n|---|---|---|---|---|---|---|---|---|---|---|")
    bpt, bbs = RES[(lab, ptag, base_nm)]
    for nm, spec, pol in POL:
        if (lab, ptag, nm) not in RES: continue
        pt, bs = RES[(lab, ptag, nm)]
        pv = np.array([x["paid"] for x in bs]); dv = pv - np.array([x["paid"] for x in bbs])
        lo, hi = np.percentile(dv, 2.5), np.percentile(dv, 97.5)
        dist = "—" if nm == base_nm else ("SÍ" if (lo > 0 or hi < 0) else "NO")
        net = pt["paid"] - 245.0 * pt["life"] / 252.0
        P(f"| {nm} | ${pt['paid']:,.0f} [{np.percentile(pv, 2.5):,.0f}, {np.percentile(pv, 97.5):,.0f}] | " + ("—" if nm == base_nm else f"${pt['paid'] - bpt['paid']:+,.0f} [{lo:+,.0f}, {hi:+,.0f}]") +
          f" | {dist} | {pt['p1'] * 100:.1f} % [{np.percentile([x['p1'] for x in bs], 2.5) * 100:.1f}, {np.percentile([x['p1'] for x in bs], 97.5) * 100:.1f}] | {pt['d3'] * 100:.1f} % [{np.percentile([x['d3'] for x in bs], 2.5) * 100:.1f}, {np.percentile([x['d3'] for x in bs], 97.5) * 100:.1f}] | {pt['d1'] * 100:.1f} % | {pt['life']:.1f} | {pt['med']:.0f} | ${pt['first']:,.0f} | ${net:,.0f} |")
for lab, wr in LABELS:
    table(lab, "mié 28-oct = LARGO")
table(LABELS[0][0], "jue 29-oct = CORTO")
P("\n«¿distinguible?» = el IC95 de la diferencia pareada excluye 0. Este IC cuenta la incertidumbre del conjunto de días históricos y el ruido de simulación; **no** cuenta cambio de régimen, el slippage real de MGC (no medido) ni el WR verdadero.")

# ───────────────────────── Parte C: efecto FOMC ─────────────────────────
P("\n## C. Efecto FOMC en MGC (J8.3) — geometría de producción, entrada 7:15 CT, flatten 14:30 CT\n")
dates = clean.dates
fo = np.array([d in set(fomc) for d in dates]); n_f = int(fo.sum())
P(f"Días FOMC (día del anuncio, 13:00 CT) dentro de la muestra de MGC: **{n_f}** de {clean.D} (ventana {dates[0]} → {dates[-1]}). Es una muestra pequeña: cualquier diferencia debajo es **anecdótica**, no prueba.\n")
def first_touch(dd, side, sl, tp):
    fav = dd.hi if side == 1 else -dd.lo; adv = dd.lo if side == 1 else -dd.hi
    fh = np.where((fav >= tp).any(1), (fav >= tp).argmax(1), 10 ** 6); ah = np.where((-adv >= sl).any(1), (-adv >= sl).argmax(1), 10 ** 6)
    return np.minimum(fh, ah)
P("| geometría | lado | grupo | n | P&L neto medio/sesión | TP % | SL+LIQ % | FLATTEN % | |P&L| medio | peor sesión | sesiones sin resolver a las 13:00 CT |\n|---|---|---|---|---|---|---|---|---|---|---|")
perm = {}
for nm, nc, sl, tp in (("3×364", 3, 364, 364), ("3×728", 3, 728, 728), ("1 micro, 364", 1, 364, 364)):
    for side, sn in ((1, "LARGO (mié 28)"), (-1, "CORTO")):
        k, p = sim_day(clean, side, nc, 2000.0, slip=0.0, exit_slip=0.0, sl=sl, tp=tp, fee=MGC["fee"], tick_usd=MGC["tick_usd"], stop_frac=0.5)
        ft = first_touch(clean, side, sl, tp)
        for gname, g in (("FOMC", fo), ("resto", ~fo)):
            P(f"| {nm} | {sn} | {gname} | {int(g.sum())} | ${p[g].mean():+,.1f} | {np.mean(k[g] == 0) * 100:.0f} | {np.mean((k[g] == 1) | (k[g] == 2)) * 100:.0f} | {np.mean(k[g] == 3) * 100:.0f} | ${np.abs(p[g]).mean():,.0f} | ${p[g].min():+,.0f} | {np.mean(ft[g] >= BAR_FOMC_RELEASE) * 100:.0f} % |")
        # prueba de permutación (diferencia FOMC − resto), 20,000 permutaciones
        pr = np.random.default_rng(SEED + 1); obs_m = p[fo].mean() - p[~fo].mean(); obs_a = np.abs(p[fo]).mean() - np.abs(p[~fo]).mean()
        cm = ca = 0
        for _ in range(20000):
            q = pr.permutation(len(p)); f_ = q[:n_f]; r_ = q[n_f:]
            cm += abs(p[f_].mean() - p[r_].mean()) >= abs(obs_m); ca += abs(np.abs(p[f_]).mean() - np.abs(p[r_]).mean()) >= abs(obs_a)
        perm[(nm, sn)] = (obs_m, cm / 20000, obs_a, ca / 20000)
P("\n**Diferencia FOMC − resto y p de permutación (20,000, bilateral):**\n\n| geometría | lado | Δ P&L medio | p | Δ |P&L| medio | p |\n|---|---|---|---|---|---|")
for (nm, sn), (om, pm_, oa, pa) in perm.items(): P(f"| {nm} | {sn} | ${om:+,.1f} | {pm_:.2f} | ${oa:+,.1f} | {pa:.2f} |")
# eventos posteriores al anuncio: primer toque de ±364 ticks (desde la referencia 7:15 CT) después de las 13:00 CT
up = clean.hi >= 364; dn = clean.lo <= -364
iu = np.where(up.any(1), up.argmax(1), 10 ** 6); idn = np.where(dn.any(1), dn.argmax(1), 10 ** 6); ftq = np.minimum(iu, idn)
late = (ftq >= BAR_FOMC_RELEASE) & (ftq < 10 ** 6)
P("\n**Primer toque de ±364 ticks por día FOMC** (barrera simétrica de la geometría de producción; el lado del trade decide si es TP o SL):\n")
P("| fecha FOMC | primer toque (CT) | dirección | cierre del día (ticks) | ¿después de las 13:00? |\n|---|---|---|---|---|")
for i in np.nonzero(fo)[0]:
    f_ = ftq[i]
    if f_ < 10 ** 6:
        tm = 7 * 60 + 15 + 5 * int(f_); P(f"| {dates[i]} | {tm // 60}:{tm % 60:02d} | {'arriba' if iu[i] < idn[i] else 'abajo'} | {int(clean.cl[i, -1])} | {'**SÍ**' if f_ >= BAR_FOMC_RELEASE else 'no'} |")
    else: P(f"| {dates[i]} | — (sin toque) | — | {int(clean.cl[i, -1])} | no |")
nl_f = int(late[fo].sum()); pb = late[~fo].mean()
pbin = sum(math.comb(n_f, k) * pb ** k * (1 - pb) ** (n_f - k) for k in range(nl_f, n_f + 1))
P(f"\n**{nl_f} de {n_f} días FOMC ({nl_f / n_f * 100:.0f} %) tuvieron su primer toque de ±364 DESPUÉS de las 13:00 CT, contra {int(late[~fo].sum())} de {int((~fo).sum())} ({pb * 100:.1f} %) en los demás días; P(≥ {nl_f} de {n_f} | tasa base) = {pbin:.4f} (binomial exacta, una cola).** Es el único indicio de un efecto FOMC sobre la geometría: con 3 eventos es frágil y no dice la dirección.")
P("**Corrección a H4:** `resultados_H4.md` y `REPORTE_H.md` §2.3 decían que «≈ 80 % de los días de MGC siguen abiertos a las 13:00 CT». Ese número ignoraba el SL de 364 ticks (el script de H4 contaba solo el TP y la liquidación por colchón de 9,000). **Medido con ambas barreras: 57.8 % de los días siguen sin resolver a las 13:00 CT (56 % en días FOMC)**; los días que se resuelven 'tras' las 13:00 son 1.8 % del total.")
# día 1 condicionado a FOMC: vidas simuladas (WR 50, paridad LARGO)
P("\n### C2. Vidas con el día 1 sorteado de los días FOMC históricos (WR 50 %, mié = LARGO; el resto de los días del pool)\n")
P(f"| política | cobrado esperado [IC95] | P(≥ 1 pago) | P(muerte día 1) | P(muerte en 3 días) | vida |\n|---|---|---|---|---|---|")
ctx = {}
for nm, spec, pol in (POL[0], POL[5], POL[6], POL[3]):
    ptc, bsc = run_policy(spec, pol, 0.0, 0, day0=fidx)
    ctx[nm] = ptc
    pv = np.array([x["paid"] for x in bsc]); P(f"| {nm} | ${ptc['paid']:,.0f} [{np.percentile(pv, 2.5):,.0f}, {np.percentile(pv, 97.5):,.0f}] | {ptc['p1'] * 100:.1f} % | {ptc['d1'] * 100:.1f} % | {ptc['d3'] * 100:.1f} % | {ptc['life']:.1f} |")
    print("  C2", nm, round(time.time() - t0), "s", flush=True)
P(f"\n(Nota: el IC de C2 resortea solo los días del pool; los {len(fidx)} días FOMC del día 1 no se remuestrean ⇒ el IC subestima la incertidumbre de n = {len(fidx)}.)")
P("\n### C3. Diferencias pareadas con el día 1 sorteado de los días FOMC (remuestreando también los días FOMC; WR 50 %, mié = LARGO)\n")
base_r, skip_r, one_r = [], [], []
bfr = np.random.default_rng(SEED + 7)
dd_ = dd_for("14:25"); mk_ = gold_mask(dd_, True)
c3days = [Day0(dd_, MGC["tick_usd"], MGC["fee"], 364, 364, slip=EMP8, slip_p=EMP8_P, mask=mk_, cush_max=9000.0, drift=0.0, stop_frac=0.5, day0=fidx) for _ in range(3)]
for b_ in range(B):
    d0 = fidx[bfr.integers(0, len(fidx), len(fidx))]
    row = []
    for dobj, (nm, spec, pol) in zip(c3days, (POL[0], POL[5], POL[6])):
        dobj.day0 = d0
        row.append(metrics(simulate_life(dobj, Rules(), pol, n=N_BS, seed=21, start_parity=0)))
    base_r.append(row[0]); one_r.append(row[1]); skip_r.append(row[2])
P("| política | Δ cobrado vs 3×364 [IC95] | fracción de remuestras con Δ > 0 | Δ P(muerte en 3 días) [IC95] |\n|---|---|---|---|")
for nm, rr in (("1 micro SOLO el día 1 (FOMC)", one_r), ("NO operar el día 1 (FOMC)", skip_r)):
    dv = np.array([a["paid"] - b["paid"] for a, b in zip(rr, base_r)]); d3 = np.array([a["d3"] - b["d3"] for a, b in zip(rr, base_r)])
    P(f"| {nm} | ${dv.mean():+,.0f} [{np.percentile(dv, 2.5):+,.0f}, {np.percentile(dv, 97.5):+,.0f}] | {np.mean(dv > 0) * 100:.0f} % | {d3.mean() * 100:+.1f} pp [{np.percentile(d3, 2.5) * 100:+.1f}, {np.percentile(d3, 97.5) * 100:+.1f}] |")
open(os.path.join(HERE, "resultados_J8.md"), "w", encoding="utf-8").write("\n".join(out) + "\n")
print("OK", round(time.time() - t0), "s")
