"""Simulacion del caso concreto del usuario: Combine 50K con G2 (MES) desde el lun 19-oct-2026 y XFA con Cerebro 2 (MGC), hasta el 31-dic-2026.
Motor validado dd_cash/engine_real.py (copia con calendario: dd_cash/engine_real_cal.py). SANDBOX / R&D: offline, sin credenciales.
Calendario: dias habiles 19-oct..31-dic, sin 26-nov (Thanksgiving) ni 25-dic; 27-nov y 24-dic (cierre anticipado) se tratan como dias SIN operar (el Pi aun no maneja el flatten anticipado).
Escenarios: G2 tal cual con handoff del MGC inmediato; handoff listo el 2-nov y el 1-dic; TP 32 en vez de 40. Lag de activacion XFA tras pasar = 2 dias; cobro de payout 5 dias despues de solicitarlo.
Costos operativos: Massive $43.5 + Pi $1.5 + API $14.5 = $59.5 por mes (21 dias de trading), cobrados al inicio de cada bloque de 21 dias."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np, pandas as pd
from dd_cash.real_pnl import setup
from dd_cash.engine_real_cal import simulate
from scripts.g2_real_rules_scan import build_tables, TV

OPS = 43.5 + 1.5 + 14.5
EARLY = {pd.Timestamp("2026-11-27"), pd.Timestamp("2026-12-24")}
HOL = {pd.Timestamp("2026-11-26"), pd.Timestamp("2026-12-25")}
DAYS = [d for d in pd.bdate_range("2026-10-19", "2026-12-31") if d not in HOL]
H = len(DAYS)
KEY = {"30-oct": "2026-10-30", "13-nov": "2026-11-13", "30-nov": "2026-11-30", "15-dic": "2026-12-15", "31-dic": "2026-12-31"}
KEYIDX = {k: max(i for i, d in enumerate(DAYS) if d <= pd.Timestamp(v)) for k, v in KEY.items()}
SKIP = np.array([d in EARLY for d in DAYS])

def idx_of(date): return next(i for i, d in enumerate(DAYS) if d >= pd.Timestamp(date))

def run(nc, tp, sl, handoff=None, lag=2, cash_lag=5, T=40000, seed=2026, skip=SKIP, single=False):
    acc, real, nd = setup(nc, tp, sl)
    D = np.random.default_rng(seed).integers(0, nd, (T, H))
    lg = np.full(H, lag)
    if handoff is not None:
        h = idx_of(handoff); lg = np.array([max(lag, h - d) for d in range(H)])
    r = simulate(acc, D, real=real, lag=lg, skip=skip, single_episode=single)
    take = r["take_d"].astype(float)
    if cash_lag:
        take = np.concatenate([np.zeros((T, cash_lag)), take[:, :-cash_lag]], axis=1)
    fee = r["fee_d"].astype(float)
    ops = np.zeros(H); ops[::21] = OPS
    cash = np.cumsum(take - fee, axis=1) - np.cumsum(ops)[None, :]
    return r, take, fee, cash

def summarize(label, r, take, fee, cash, out, single=False):
    T = take.shape[0]
    P = lambda s: out.append(s) or print(s)
    P(f"\n### {label}")
    pd_ = r["pass_day"]
    row = "  P(Combine ya pasado) al: " + " | ".join(f"{k} {np.mean((pd_ > 0) & (pd_ - 1 <= i)):.0%}" for k, i in KEYIDX.items())
    P(row)
    passed = pd_ > 0
    if passed.any():
        q = np.percentile(pd_[passed] - 1, [10, 50, 90]).astype(int)
        P("  fecha del pase (entre quienes pasan antes del 31-dic): p10 {} | mediana {} | p90 {}".format(*[DAYS[i].strftime('%d-%b') for i in q]))
    P(f"  Combines comprados (intentos) hasta el 31-dic: media {r['n_att'].mean():.1f} | p50 {np.percentile(r['n_att'],50):.0f} | p90 {np.percentile(r['n_att'],90):.0f}")
    req = r["take_d"].astype(float)
    first = np.where((req > 0).any(1), (req > 0).argmax(1), -1)
    got = first >= 0
    P("  P(>=1 payout SOLICITADO) al: " + " | ".join(f"{k} {np.mean((first >= 0) & (first <= i)):.0%}" for k, i in KEYIDX.items()))
    P(f"  Sin ningun payout al 31-dic: {1 - got.mean():.0%}")
    if got.any():
        q = np.percentile(first[got], [10, 50, 90]).astype(int)
        P("  fecha del 1er payout (entre quienes cobran): p10 {} | mediana {} | p90 {}".format(*[DAYS[i].strftime('%d-%b') for i in q]))
        amt = np.array([req[i, first[i]] for i in np.nonzero(got)[0]])
        P(f"  monto del 1er payout al trader (ya 90%): p10 ${np.percentile(amt,10):,.0f} | p50 ${np.percentile(amt,50):,.0f} | p90 ${np.percentile(amt,90):,.0f} | max ${amt.max():,.0f}")
    tot_req = req.sum(1); tot_cash = take.sum(1)
    npay = (req > 0).sum(1)
    P(f"  payouts al trader solicitados hasta 31-dic: p10 ${np.percentile(tot_req,10):,.0f} | p50 ${np.percentile(tot_req,50):,.0f} | p90 ${np.percentile(tot_req,90):,.0f} | media ${tot_req.mean():,.0f} | n pagos: media {npay.mean():.2f}")
    P(f"  ... de los cuales COBRADOS (5 dias de demora) al 31-dic: p50 ${np.percentile(tot_cash,50):,.0f} | media ${tot_cash.mean():,.0f}")
    fees = fee.sum(1)
    P(f"  fees Topstep hasta 31-dic (Combine + resets + activacion): p50 ${np.percentile(fees,50):,.0f} | p90 ${np.percentile(fees,90):,.0f} | media ${fees.mean():,.0f} ; costos operativos ${OPS * ((H + 20)//21):,.0f}")
    final = cash[:, -1]
    P(f"  NETO en caja al 31-dic (cobrado - fees - ops): p10 ${np.percentile(final,10):,.0f} | p50 ${np.percentile(final,50):,.0f} | p90 ${np.percentile(final,90):,.0f} | media ${final.mean():,.0f} | P(neto<0)={np.mean(final<0):.0%}")
    cushion = -np.minimum(cash.min(1), 0.0)
    P(f"  capital maximo hundido en algun momento (colchon): p50 ${np.percentile(cushion,50):,.0f} | p90 ${np.percentile(cushion,90):,.0f} | p95 ${np.percentile(cushion,95):,.0f} | p99 ${np.percentile(cushion,99):,.0f}")
    # AJUSTE por liquidacion en tiempo real en la XFA: engine_real no la modela; log 24/25-sep (50K nc3): payout medio $822 -> $620 (-25%), P(>=1 pago) 39.6% -> 31.6% (x0.80).
    ops_tot = OPS * ((H + 20) // 21)
    adj = (take * 0.75).sum(1) - fee.sum(1) - ops_tot
    P(f"  [AJUSTADO -25% a payouts por liquidacion en tiempo real de la XFA] NETO al 31-dic: p50 ${np.percentile(adj,50):,.0f} | media ${adj.mean():,.0f} | P(neto<0)={np.mean(adj<0):.0%} ; payouts solicitados media ${tot_req.mean()*0.75:,.0f}" + (f" ; P(>=1 payout) aprox. {np.mean(first>=0)*0.80:.0%}" if single else " ; (P(>=1 payout) con ciclos repetidos no se ajusta de forma simple)"))
    med = np.median(cash, axis=0)
    P("  caja acumulada MEDIANA al: " + " | ".join(f"{k} ${med[i]:,.0f}" for k, i in KEYIDX.items()) + (f" | cruza a >=0 el {DAYS[int(np.argmax(med>=0))].strftime('%d-%b')}" if (med >= 0).any() else " | no cruza a >=0 antes del 31-dic"))

if __name__ == "__main__":
    out = []
    P = lambda s: out.append(s) or print(s)
    P(f"Calendario: {H} dias habiles del {DAYS[0].date()} al {DAYS[-1].date()} (sin 26-nov ni 25-dic); dias sin operar por cierre anticipado: {[d.strftime('%d-%b') for d in EARLY]}")
    # probabilidades del PRIMER dia del Combine con G2 (nc=40, TP40, SL100, MLL $2,000 -> liquidacion a -40 ticks)
    adv, tpt, flat = build_tables()
    tb, ab = tpt[:, 40], adv[:, 40]
    ptp = np.mean(tb < ab); psl = np.mean((tb >= ab) & (ab < 10**6)); pfl = 1 - ptp - psl
    P(f"Primer dia del Combine (G2 nc=40): P(TP +$2,000) = {ptp:.1%} | P(liquidacion -$2,000, Combine perdido) = {psl:.1%} | P(ninguno, flatten 14:30) = {pfl:.1%}   [515 dias de MES, barras de 5 min, SL primero si la barra toca ambos]")
    scen = [("A. G2 tal cual (nc40/TP40/SL100), handoff MGC inmediato, CICLO REPETIDO (si la XFA quiebra se recompra un Combine)", dict(nc=40, tp=40, sl=100)),
            ("A1. G2 tal cual, handoff inmediato, SOLO EL PRIMER CICLO (si la XFA quiebra no se recompra)", dict(nc=40, tp=40, sl=100, single=True)),
            ("B. G2 tal cual, handoff del MGC listo el 2-nov, ciclo repetido", dict(nc=40, tp=40, sl=100, handoff="2026-11-02")),
            ("B1. G2 tal cual, handoff del MGC listo el 2-nov, solo el primer ciclo", dict(nc=40, tp=40, sl=100, handoff="2026-11-02", single=True)),
            ("C. G2 tal cual, handoff del MGC listo el 1-dic, ciclo repetido", dict(nc=40, tp=40, sl=100, handoff="2026-12-01")),
            ("C1. G2 tal cual, handoff del MGC listo el 1-dic, solo el primer ciclo", dict(nc=40, tp=40, sl=100, handoff="2026-12-01", single=True)),
            ("D. TP 32 en vez de 40 (propuesta), handoff inmediato, ciclo repetido", dict(nc=40, tp=32, sl=100)),
            ("D1. TP 32, handoff inmediato, solo el primer ciclo", dict(nc=40, tp=32, sl=100, single=True))]
    for label, kw in scen:
        r, take, fee, cash = run(**kw)
        summarize(label, r, take, fee, cash, out, single=kw.get('single', False))
    open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dd_cash", "glitch_oct19_dec31_report.txt"), "w").write("\n".join(out))
