"""Parte G, G2-T4 (V3): barreras escaladas por ATR en MGC (PREREGISTRO_G2.md). Misma regla que el pre-registro; motor de la Parte D con tablas por (lado, nc, ancho). -> resultados_G2_T4.md, g2_t4.json
    GLITCH_MGC_PARQUET=... python run_g2_t4.py"""
import json, math, os, sys, time
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "..", "xfa")); sys.path.insert(0, os.path.join(HERE, "..", "preservacion"))
from chain import combine_bank, run_chain, xfa_bank
from daydata import load_days, sim_day
from worlds import MGC, drift_for_wr, gold_mask, mgc_days
from xfa_engine import BarDays, Rules, pol_fixed
SEED = 20261024
t0 = time.time(); out = []; P = lambda s="": (print(s, flush=True), out.append(s))
dd = mgc_days(True); D = dd.D; mk = gold_mask(dd, True)
Rt = np.maximum(dd.hi.max(1), 0) - np.minimum(dd.lo.min(1), 0)
m20 = np.full(D, np.nan)
for t in range(20, D): m20[t] = Rt[t - 20:t].mean()
k = 364.0 / np.nanmedian(m20)                              # constante de calibracion (pre-registro)
Wd = np.where(np.isnan(m20), 364, np.clip(np.round(k * m20 / 50.0) * 50.0, 200, 800)).astype(int)
ncd = np.clip(np.round(1092.0 / Wd), 1, 6).astype(int)
valid = ~np.isnan(m20)
P("# resultados_G2_T4 — barreras escaladas por ATR en MGC (V3)\n")
P(f"k = {k:.3f} (= 364 / mediana de la media de 20 rangos = {np.nanmedian(m20):.0f} ticks). W_t en [200, 800] a pasos de 50; nc_t = clip(round(1092/W_t), 1, 6). Distribución de W: " + ", ".join(f"{w}: {int((Wd[valid] == w).sum())}" for w in sorted(set(Wd[valid]))) + ".\n")

class ScaledDays(BarDays):
    """Igual que BarDays pero el ancho y los contratos del dia vienen de Wd[idx], ncd[idx] (la politica solo decide si opera: nc > 0)."""
    def __init__(self, *a, Wd, ncd, **kw):
        super().__init__(*a, **kw); self.Wd, self.ncd, self._sc = Wd, ncd, {}
    def tab(self, side, ncv, w):
        key = (side, ncv, w)
        if key not in self._sc:
            K = np.empty((self.nb, self.dd.D), np.int8); Pn = np.empty((self.nb, self.dd.D))
            for b in range(self.nb):
                kk, pp = sim_day(self.dd, side, ncv, max(b * self.step, 1e-9), slip=self.slips[0], exit_slip=self.exit_slip, sl=w, tp=w, order=self.order, fee=self.fee, tick_usd=self.tick_usd, drift=self.drift, stop_frac=self.stop_frac)
                K[b], Pn[b] = kk, pp
            self._sc[key] = (K, Pn)
        return self._sc[key]
    def resolve(self, idx, si, side, nc, cush, sl):
        n = len(idx); kind = np.full(n, 3, np.int8); pnl = np.zeros(n)
        bins = np.clip(np.floor(cush / self.step + 1e-9).astype(int), 0, self.nb - 1)
        w_i, n_i = self.Wd[idx], self.ncd[idx]
        for w in np.unique(w_i):
            for ncv in np.unique(n_i[w_i == w]):
                for sd in (1, -1):
                    m = (nc > 0) & (w_i == w) & (n_i == ncv) & (side == sd)
                    if not m.any(): continue
                    K, Pn = self.tab(sd, int(ncv), int(w)); kind[m] = K[bins[m], idx[m]]; pnl[m] = Pn[bins[m], idx[m]]
        return kind, pnl

pool_mask = valid & mk
NB = 60000
def run(scaled, drift=0.0, pool=None, nb=NB, seed=21):
    if scaled: days = ScaledDays(dd, MGC["tick_usd"], MGC["fee"], 364, 364, slip=(0.0,), mask=pool_mask, cush_max=9000.0, drift=drift, stop_frac=0.5, Wd=Wd, ncd=ncd)
    else: days = BarDays(dd, MGC["tick_usd"], MGC["fee"], 364, 364, slip=(0.0,), mask=pool_mask, cush_max=9000.0, drift=drift, stop_frac=0.5)
    return days
def bank(days, nb=NB, seed=21):
    life, pday, pnet = xfa_bank(days, Rules(), pol_fixed(3, 364, 364), nb, seed=seed)
    return life, pday, pnet
mes = load_days(); cb = combine_bank(mes, 100000, "P0", (1.0, 3.0), (0.5, 0.5), seed=11)
res = {}
for nm, sc in (("fijo 3×364", False), ("ATR", True)):
    dz = run(sc); life, pday, pnet = bank(dz)
    r = run_chain(cb[0], cb[1], life, pday, pnet, n=40000, seed=5)
    res[nm] = dict(cobrado=float(pnet.sum(1).mean()), p1=float((pnet.sum(1) > 0).mean()), net=float(r["net"].mean()), life=float(life.mean()), days=dz)
    print("  ", nm, round(time.time() - t0), flush=True)
# fraccion decidida por bloques (lado alternate; liquidacion con colchon grande)
from strategies.geometry_pure import decide_side, trading_day_index
alt = np.array([decide_side(trading_day_index(d), "alternate") for d in dd.dates])
def dec_frac(scaled):
    f = np.zeros(D)
    for t in range(D):
        w = Wd[t] if scaled else 364; n = ncd[t] if scaled else 3
        kk = sim_day(dd, int(alt[t]), n, 9000.0, slip=0.0, exit_slip=0.0, sl=w, tp=w, fee=MGC["fee"], tick_usd=MGC["tick_usd"], stop_frac=0.5)[0][t]
        f[t] = kk != 3
    return f
fx, fs = dec_frac(False), dec_frac(True)
blocks = [(20, 150), (150, 270), (270, 390), (390, D)]
bx = [fx[a:b].mean() for a, b in blocks]; bs = [fs[a:b].mean() for a, b in blocks]
P("## Fracción decidida (TP o SL) por bloque cronológico (4)\n")
P(f"- Fijo 3×364: {' · '.join(f'{x * 100:.0f} %' for x in bx)} (DE entre bloques = {np.std(bx) * 100:.1f} pp)")
P(f"- ATR:        {' · '.join(f'{x * 100:.0f} %' for x in bs)} (DE entre bloques = {np.std(bs) * 100:.1f} pp) → cambio de la DE: **{(np.std(bs) / np.std(bx) - 1) * 100:+.0f} %** (predicción: ≤ −30 %).")
P("\n## Prueba de dinero (W2: sin la ventana de oro; stop 0.5; Combine hoy P0 mezcla {1,3}; bancos de %d)\n" % NB)
P("| | cobrado por XFA | P(≥1 pago) | vida media (días) | neto $/año/cuenta |\n|---|---|---|---|---|")
for nm, r in res.items(): P(f"| {nm} | ${r['cobrado']:,.0f} | {r['p1'] * 100:.1f} % | {r['life']:.1f} | ${r['net']:,.0f} |")
d_net = res["ATR"]["net"] - res["fijo 3×364"]["net"]; d_cob = res["ATR"]["cobrado"] - res["fijo 3×364"]["cobrado"]
P(f"\nDiferencia ATR − fijo: cobrado {d_cob:+,.0f} por XFA; **neto {d_net:+,.0f} $/año/cuenta** (piso +$500; ruido de nivel ±$100).")
# bootstrap pareado de dias (cobrado por XFA)
B = 100; rng = np.random.default_rng(SEED); pool_idx = np.nonzero(pool_mask)[0]; diffs = []
for b in range(B):
    st = rng.integers(0, len(pool_idx) - 4, size=math.ceil(len(pool_idx) / 5)); rs = (st[:, None] + np.arange(5)[None, :]).ravel()[:len(pool_idx)]; sub = pool_idx[rs]
    vals = []
    for nm in ("fijo 3×364", "ATR"):
        dz = res[nm]["days"]; dz.pool = sub
        life, pday, pnet = xfa_bank(dz, Rules(), pol_fixed(3, 364, 364), 8000, seed=100 + b)
        vals.append(pnet.sum(1).mean())
    diffs.append(vals[1] - vals[0])
diffs = np.array(diffs); p_t4 = float((diffs <= 0).mean())
P(f"- Bootstrap pareado de días ({B} remuestras de la historia, bancos de 8,000): diferencia de cobrado media {diffs.mean():+,.0f}, IC95 [{np.percentile(diffs, 2.5):+,.0f}, {np.percentile(diffs, 97.5):+,.0f}]; **p unilateral (ATR > fijo) = {p_t4:.3f}** (resolución mínima 1/{B}).")
# equilibrio (deriva)
sig = float(np.std(dd.cl[mk][:, -1]))
eq = {}
for nm, sc in (("fijo 3×364", False), ("ATR", True)):
    pts = []
    for wr in (0.47, 0.48, 0.49, 0.50):
        dm = 0.0 if wr == 0.50 else drift_for_wr(dd, mk, wr)
        dz = run(sc, drift=dm); life, pday, pnet = bank(dz, nb=40000)
        pts.append((wr, run_chain(cb[0], cb[1], life, pday, pnet, n=30000, seed=5)["net"].mean()))
    e = next((a + (b - a) * (-na) / (nb_ - na) for (a, na), (b, nb_) in zip(pts, pts[1:]) if na < 0 <= nb_), float("nan")); eq[nm] = (e, pts)
    print("  eq", nm, round(time.time() - t0), flush=True)
P("\n## Equilibrio (ventaja solo en la XFA, misma deriva en ticks/día para ambas geometrías)\n")
for nm, (e, pts) in eq.items(): P(f"- {nm}: " + " · ".join(f"{w * 100:.0f} %: ${n:,.0f}" for w, n in pts) + f" → equilibrio ≈ {e * 100:.1f} %")
P(f"\nCambio del equilibrio: {(eq['ATR'][0] - eq['fijo 3×364'][0]) * 100:+.1f} pp (rechazo si > +0.3 pp).")
json.dump(dict(p_t4=p_t4, d_cob=d_cob, d_net=d_net, sd_ratio=float(np.std(bs) / np.std(bx))), open(os.path.join(HERE, "g2_t4.json"), "w"))
open(os.path.join(HERE, "resultados_G2_T4.md"), "w").write("\n".join(out))
