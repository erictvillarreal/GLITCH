"""
Verificacion de G2 (MES 100/40, nc=40, alternar, Combine 50K) contra las reglas OFICIALES vigentes de Topstep
(help.topstep.com, leido 24-sep-2026):
  - Consistency Target 55%: best day <= 55% del profit total; si se excede, el Profit Target SUBE a best_day/0.55
    (NO es una falla). Ejemplo oficial: best day $1,800 -> target $3,273.  (Consistency at Topstep, 8284208)
  - Daily Loss Limit: OPCIONAL en el Combine (se agrega al comprar); $1,000 en 50K; al tocarlo liquida posiciones y
    bloquea la sesion, no es violacion.  (10490293, publicado 30-jun-2026)
  - MLL: piso trailing; tocarlo = cuenta perdida.
Compara: (A) el simulador del repo tal cual, (B) misma dist con 55% ("≤"), (C) semantica oficial con profit NETO,
(D) escenarios reales de liquidacion intradia (DLL on / DLL off) via bar-walk empirico.
"""
import os, sys, dataclasses
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
from core.prop_firm import TOPSTEP_50K
from simulation.monte_carlo import TopstepMonteCarloSimulator
from scripts.camino_b_grid import ExactDayDist
from dd_wr.product_sweep import load_sessions, walk_all

NC, TV, COMM = 40, 1.25, 1.22
WIN = 40 * TV * NC - COMM * NC            # 1951.2 neto
LOSS_SL = 100 * TV * NC + COMM * NC       # 5048.8 (SL 100 ticks)
WR = 0.7018                               # WR calibrado de G2 (punto medio del bracket, ver g2_rescore_baseline.py)
S = TOPSTEP_50K
N = 200_000


def official_sim(draw, cons_pct=0.55, dll=None, max_days=15, seed=1, min_days=2):
    """Semantica oficial: profit NETO; pasa si neto >= max(target, best_day/cons_pct); MLL trailing EOD; DLL opcional (clip)."""
    rng = np.random.default_rng(seed)
    bal = np.zeros(N); floor = np.full(N, -S.mll_distance); alive = np.ones(N, bool)
    best = np.zeros(N); passed = np.zeros(N, bool); pd_ = np.zeros(N, int)
    for d in range(1, max_days + 1):
        p = np.where(alive, draw(N, rng), 0.0)
        if dll: p = np.where(alive & (p < -dll), -dll, p)
        bal += np.where(alive, p, 0.0)
        floor = np.where(alive & (bal - S.mll_distance > floor), np.minimum(bal - S.mll_distance, 0.0), floor)
        blown = alive & (bal <= floor); alive &= ~blown
        best = np.where(alive & (p > best), p, best)
        need = np.maximum(S.profit_target, best / cons_pct)
        ok = alive & (bal >= need) & (d >= min_days)
        passed |= ok; pd_ = np.where(ok & (pd_ == 0), d, pd_); alive &= ~ok
    return passed.mean(), (pd_[passed].mean() if passed.any() else float("nan"))


def bern(wr, w, l):
    return lambda n, rng: np.where(rng.random(n) < wr, w, -l)


print("== (A) simulador del repo TAL CUAL (DLL clip -$1,000, cons 50% estricto, cum solo dias positivos)")
r = TopstepMonteCarloSimulator(ExactDayDist(WR, 2000, 5000, COMM * NC, 1), S, n_paths=N, max_days=15, seed=42).run()
print(f"   pass={r.pass_rate:.4f} blow={r.blow_rate:.4f} dias_pase={r.avg_pass_days:.2f}")
S55 = dataclasses.replace(S, consistency_cap_pct=0.55)
r = TopstepMonteCarloSimulator(ExactDayDist(WR, 2000, 5000, COMM * NC, 1), S55, n_paths=N, max_days=15, seed=42).run()
print(f"== (B) mismo simulador con cap 55%: pass={r.pass_rate:.4f} blow={r.blow_rate:.4f} dias_pase={r.avg_pass_days:.2f}")

print("\n== (C) semantica OFICIAL (neto, 55% -> sube el target), dist binaria WR=0.7018, SL 100 ticks = -$5,049")
for lbl, dll in (("DLL agregado (clip -$1,000, supone que la perdida se limita SIN cambiar el WR)", 1000), ("SIN DLL (default: perdida de -$5,049 rompe el MLL)", None)):
    p, d = official_sim(bern(WR, WIN, LOSS_SL), dll=dll)
    print(f"   {lbl}: pass={p:.4f} dias_pase={d:.2f}")
p50, _ = official_sim(bern(WR, WIN, LOSS_SL), cons_pct=0.50, dll=1000)
print(f"   (referencia: cap 50% en semantica oficial, DLL clip: pass={p50:.4f})")

print("\n== (D) liquidacion INTRADIA real (bar-walk empirico MES, 1 trade/dia 9:45 CT, flatten 14:30, nc=40)")
sess = load_sessions("mes_5min_2y")
def series(sl, tp):
    t = walk_all(sess, 0.25, TV, COMM, 1, sl, tp, 9 * 60 + 45, 14 * 60 + 30)
    return t, t.pnl.values * NC
for lbl, sl, dll in (("base 100/40 (como modela el repo, sin liquidacion)", 100, 1000),
                      ("DLL agregado: liquida a -20 ticks (=-$1,000)", 20, 1000),
                      ("SIN DLL: MLL liquida a -40 ticks (=-$2,000)", 40, None)):
    t, x = series(sl, 40)
    tp_, sl_, fl_ = (t.result == "TP").sum(), (t.result == "SL").sum(), (t.result == "FLATTEN").sum()
    draw = lambda n, rng, x=x: rng.choice(x, size=n)
    p, d = official_sim(draw, dll=dll)
    print(f"   {lbl}: TP/SL/FLAT={tp_}/{sl_}/{fl_} WR_cond={tp_/(tp_+sl_):.3f} media_dia=${x.mean():,.0f} -> pass={p:.4f} dias_pase={d:.2f}")
