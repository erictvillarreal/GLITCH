"""ACCIÓN: dos trades por día en la MISMA XFA (MGC 7:15 + MES 9:35), el lado alternado igual en ambos (como producción). Idea: más tiros independientes por día ⇒ más días ≥ $150 ⇒ primer pago más rápido.
Aproximación CONSERVADORA del MLL: el 2.º trade (MES) ve un colchón reducido en el SL completo del 1.º (MGC), aunque el 1.º haya ganado; los dos juntos nunca superan el tope del escalado.
-> resultados_ACCION_JOINT.md       cd glitch/experimentos/accion; GLITCH_MGC_PARQUET=... PYTHONPATH=../.. python3 xfa_joint.py [--quick]"""
import os, sys, time
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from accion_lib import *   # noqa: F401,F403
from xfa_engine import Policy, Rules, simulate_life, plan_cap


class JointDays:
    """Proveedor de días con dos trades. nc codificado ncA*1000 + ncB; sl codificado slA*10000 + slB."""
    sequential = False
    def __init__(self, A, B, mapA, mapB, tvA, feeA):
        self.A, self.B, self.mapA, self.mapB, self.tvA, self.feeA = A, B, np.asarray(mapA), np.asarray(mapB), tvA, feeA
        self.slips, self.slip_p = A.slips, A.slip_p
    def draw(self, rng, n):
        return rng.integers(0, len(self.mapA), n), rng.choice(len(self.slips), size=n, p=self.slip_p)
    def resolve(self, idx, si, side, nc, cush, sl):
        ncA, ncB = nc // 1000, nc % 1000; slA, slB = sl // 10000, sl % 10000
        kA, pA = self.A.resolve(self.mapA[idx], si, side, ncA, cush, slA)
        cushB = np.maximum(cush - slA * ncA * self.tvA - self.feeA * ncA, 0.0)          # conservador: el MGC pierde su SL completo antes de que el MES opere
        kB, pB = self.B.resolve(self.mapB[idx], si, side, ncB, cushB, slB)
        liq = (kA == 2) | (kB == 2)
        return np.where(liq, 2, 3).astype(np.int8), np.where(liq, 0.0, pA + pB)


def common_maps(ddA, ddB):
    ia = {d: i for i, d in enumerate(ddA.dates)}; ib = {d: i for i, d in enumerate(ddB.dates)}
    com = sorted(set(ia) & set(ib)); return [ia[d] for d in com], [ib[d] for d in com]


def run_joint(ddA, ddB, planA, planB, driftA, driftB, n, seed, pool=None, slip=(1.0,), slipp=None, pay="max"):
    slA, tpA, ncA = planA; slB, tpB, ncB = planB
    A = provider("MGC", ddA, slA, tpA, driftA, slip, slipp); B = provider("MES", ddB, slB, tpB, driftB, slip, slipp)
    mA, mB = common_maps(ddA, ddB); days = JointDays(A, B, mA, mB, SPEC["MGC"]["tv"], SPEC["MGC"]["fee"])
    if pool is not None: days.mapA, days.mapB = days.mapA[pool], days.mapB[pool]
    tvA, fA, tvB, fB = SPEC["MGC"]["tv"], SPEC["MGC"]["fee"], SPEC["MES"]["tv"], SPEC["MES"]["fee"]
    def fnc(st):
        a = np.minimum(ncA, plan_cap(st.b, "MGC")); b_ = np.maximum(np.minimum(ncB, plan_cap(st.b, "MES") - a), 0)
        # el 2.º trade (MES) solo se abre si cabe, con su SL completo, en el colchón que deja el SL completo del 1.º (MGC): nunca se abre «ya condenado»
        room = np.floor(np.maximum(st.cushion - slA * a * tvA - fA * a, 0.0) / (slB * tvB + fB))
        b_ = np.minimum(b_, room).astype(int)
        return (a * 1000 + b_).astype(int)
    r = simulate_life(days, Rules(scaling=False), Policy("j", fnc, pay_fn(pay), int(slA) * 10000 + int(slB), 1), n=n, seed=seed, record_k=14)
    pd_, pn = r["pay_day"], r["pay_net"]; fp = r["first_pay_day"]; dead = ~r["alive"]
    cum = lambda T: float(np.where((pd_ >= 0) & (pd_ < T), pn, 0.0).sum(1).mean())
    return dict(life_paid=float(r["paid"].mean()), cum10=cum(10), cum20=cum(20), cum30=cum(30), cum60=cum(60), p1=float((r["npay"] >= 1).mean()),
                f10=float(((fp >= 0) & (fp < 10)).mean()), f20=float(((fp >= 0) & (fp < 20)).mean()), f30=float(((fp >= 0) & (fp < 30)).mean()),
                med=float(np.median(fp[fp >= 0]) + 1) if (fp >= 0).any() else float("nan"), d3=float(((r["life"] <= 3) & dead).mean()), dead_np=float(((r["npay"] == 0) & dead).mean()), life=float(r["life"].mean()))


if __name__ == "__main__":
    out = []; P = lambda s="": (print(s, flush=True), out.append(s))
    MGCP = (364, 364, 3); mA_tr = TR["MGC"]; mB_tr = TR["MES"]
    GJ = [(sl, max(int(round(rho * sl)), 1), nc) for sl in (60, 100, 170) for rho in (1.0, 2.0) for nc in (3, 5, 8)]
    sc = []
    for pl in GJ:
        r = run_joint(TR["MGC"], TR["MES"], MGCP, pl, drift_of("MGC", 0.5), drift_of("MES", 0.5), N_SEL, 21); sc.append((r["cum30"] + 0.25 * r["life_paid"], pl))
    sc.sort(key=lambda x: -x[0]); top = [s[1] for s in sc[:2]]; print("  selección", round(time.time() - t0), "s", flush=True)
    mA, mB = common_maps(TE["MGC"], TE["MES"]); rng = np.random.default_rng(20261029); pools = blocks(len(mA), B, rng)
    P("# resultados_ACCION_JOINT — MGC 3×364 (7:15) + MES (9:35) el mismo día en la misma XFA\n")
    P(f"**Fuente y estado.** MODELADO; {len(mA)} fechas comunes del tramo reciente (selección del plan MES en el tramo viejo con WR 50 %). MLL: aproximación conservadora (el MES ve el colchón menos el SL completo del MGC). Slippage: distribución empírica de 8 obs. (8.ª inferida = 0, NO VERIFICADA). Los dos trades llevan el mismo lado (función de la fecha).\n")
    rows = {}
    for nm, planB in (("MGC solo 3×364 (mismas fechas)", (1, 1, 0)), ("MGC + MES " + str(top[0]), top[0]), ("MGC + MES " + str(top[1]), top[1])):
        for wr in WRS:
            dA, dB = drift_of("MGC", wr), drift_of("MES", wr)
            pt = run_joint(TE["MGC"], TE["MES"], MGCP, planB, dA, dB, N_REP, 22, slip=EMP8, slipp=EMP8_P)
            bs = [run_joint(TE["MGC"], TE["MES"], MGCP, planB, dA, dB, 4000, 22, pool=pools[b], slip=EMP8, slipp=EMP8_P) for b in range(B)]
            rows[(nm, wr)] = (pt, bs)
        print("  ", nm, round(time.time() - t0), "s", flush=True)
    base = "MGC solo 3×364 (mismas fechas)"
    for wr in WRS:
        P(f"\n### WR {wr * 100:.1f} %\n")
        P("| plan | cobrado a 10 d | a 20 d | **a 30 d** [IC95] | Δ a 30 d vs MGC solo (pareada) [IC95] | vida entera | P(1.er pago ≤ 10 / 20 / 30 d) | mediana días | P(muerte ≤ 3 d) |\n|---|---|---|---|---|---|---|---|---|")
        for nm in [base] + [k[0] for k in rows if k[1] == wr and k[0] != base]:
            pt, bs = rows[(nm, wr)]; v = np.array([x["cum30"] for x in bs]); bv = np.array([x["cum30"] for x in rows[(base, wr)][1]]); d = v - bv
            P(f"| {nm} | ${pt['cum10']:,.0f} | ${pt['cum20']:,.0f} | **${pt['cum30']:,.0f}** [{np.percentile(v, 2.5):,.0f}, {np.percentile(v, 97.5):,.0f}] | " + ("—" if nm == base else f"${pt['cum30'] - rows[(base, wr)][0]['cum30']:+,.0f} [{np.percentile(d, 2.5):+,.0f}, {np.percentile(d, 97.5):+,.0f}]") +
              f" | ${pt['life_paid']:,.0f} | {pt['f10'] * 100:.0f} / {pt['f20'] * 100:.0f} / {pt['f30'] * 100:.0f} % | {pt['med']:.0f} | {pt['d3'] * 100:.0f} % |")
    open(os.path.join(HERE, "resultados_ACCION_JOINT.md"), "w", encoding="utf-8").write("\n".join(out) + "\n"); print("OK", round(time.time() - t0), "s")
