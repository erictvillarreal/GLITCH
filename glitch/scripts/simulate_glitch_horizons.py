"""Reconciliacion de horizontes: el MISMO pipeline que corre hoy (Combine 50K con G2 nc40/TP40/SL100 + XFA con Cerebro 2/MGC), motor validado dd_cash/engine_real (copia con calendario),
desde el lun 19-oct-2026 hasta ~oct-2027, con el acumulado en caja (cobrado - fees - costos operativos $59.5/mes) en fechas clave. Calendario aproximado: dias habiles menos 26-nov, 25-dic, 1-ene, 2-abr, 31-may,
5-jul, 6-sep; 27-nov y 24-dic sin operar. Handoff del MGC inmediato (2 dias tras pasar), cobro 5 dias despues de pedir el payout, ciclo repetido (si la XFA quiebra, nuevo Combine). SANDBOX / R&D."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np, pandas as pd
from dd_cash.real_pnl import setup
from dd_cash.engine_real_cal import simulate

OPS = 59.5
HOL = {pd.Timestamp(d) for d in ("2026-11-26", "2026-12-25", "2027-01-01", "2027-04-02", "2027-05-31", "2027-07-05", "2027-09-06")}
EARLY = {pd.Timestamp("2026-11-27"), pd.Timestamp("2026-12-24")}
DAYS = [d for d in pd.bdate_range("2026-10-19", "2027-10-19") if d not in HOL]
H = len(DAYS)
SKIP = np.array([d in EARLY for d in DAYS])
CKS = {"31-dic-2026": "2026-12-31", "31-ene-2027": "2027-01-31", "31-mar-2027": "2027-03-31", "30-jun-2027": "2027-06-30", "30-sep-2027": "2027-09-30", "19-oct-2027 (12 meses)": "2027-10-19"}
CKI = {k: max(i for i, d in enumerate(DAYS) if d <= pd.Timestamp(v)) for k, v in CKS.items()}


def run(nc, tp, sl, T=30000, seed=2026, haircut=1.0, lag=2, cash_lag=5):
    acc, real, nd = setup(nc, tp, sl)
    D = np.random.default_rng(seed).integers(0, nd, (T, H))
    r = simulate(acc, D, real=real, lag=lag, skip=SKIP)
    take = r["take_d"].astype(float) * haircut
    take = np.concatenate([np.zeros((T, cash_lag)), take[:, :-cash_lag]], axis=1)
    ops = np.zeros(H); ops[::21] = OPS
    cash = np.cumsum(take - r["fee_d"].astype(float), axis=1) - np.cumsum(ops)[None, :]
    return cash, take


if __name__ == "__main__":
    out = []; P = lambda s: (print(s), out.append(s))
    P(f"Pipeline que corre hoy (G2 nc40/TP40/SL100 + XFA Cerebro 2), {H} dias habiles desde 19-oct-2026; acumulado en caja por fecha (media | mediana | p10 | p90 | P(<0))")
    for lbl, hc in (("motor tal cual (payouts sin ajuste)", 1.0), ("con ajuste -25% a payouts por liquidacion en tiempo real de la XFA", 0.75)):
        cash, take = run(40, 40, 100, haircut=hc)
        P(f"\n[{lbl}]")
        for k, i in CKI.items():
            c = cash[:, i]
            P(f"  {k:24s}: media ${c.mean():>7,.0f} | mediana ${np.median(c):>7,.0f} | p10 ${np.percentile(c,10):>7,.0f} | p90 ${np.percentile(c,90):>7,.0f} | P(<0) {np.mean(c<0):.0%}")
        med = np.median(cash, axis=0); mean = cash.mean(axis=0)
        i0 = int(np.argmax(med >= 0)) if (med >= 0).any() else None
        P(f"  la caja MEDIANA cruza a >= 0 el {DAYS[i0].strftime('%d-%b-%Y') if i0 is not None else 'nunca en el horizonte'}; la MEDIA cruza el {DAYS[int(np.argmax(mean>=0))].strftime('%d-%b-%Y') if (mean>=0).any() else 'nunca'}")
        m12 = cash[:, CKI['19-oct-2027 (12 meses)']]
        P(f"  ritmo mensual implícito entre 31-mar y 30-sep-2027 (media): ${(cash[:, CKI['30-sep-2027']].mean()-cash[:, CKI['31-mar-2027']].mean())/6:,.0f}/mes")
    open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dd_cash", "glitch_horizons_report.txt"), "w").write("\n".join(out))
