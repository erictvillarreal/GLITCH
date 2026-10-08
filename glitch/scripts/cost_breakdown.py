"""Tarea 2 — desglose de costos por escenario A-F (los mismos de scripts/decision_breakdown.py), por cuenta y total, 12 meses desde 19-oct-2026 (255 dias habiles), motor validado con calendario.
Por cuenta: payouts brutos, payouts tras el -25% (liquidacion en tiempo real de la XFA, log 24/25-sep), fees de Combine (renovaciones + reinicios + compras nuevas), activaciones, tarifa INICIAL del Combine
(CORRECCION: los scripts decision_breakdown/simulate_glitch_horizons la omitian: -$49 por cuenta 50K / -$199 por cuenta 150K), costo compartido $59.5/mes x 12 cobrado UNA vez (los scripts previos cobraban 13 meses),
caja neta; media, mediana, p10, p90. Conteos por año: intentos de Combine = 1 inicial + reinicios (quiebres del Combine, mismo precio que la mensualidad) + compras nuevas (quiebres de la XFA), activaciones, XFA muertas.
Cuentas con las MISMAS senales (correlacion perfecta). SANDBOX / R&D. Uso: python -m scripts.cost_breakdown"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
from scripts.decision_breakdown import setup, H, SKIP, DAYS, OPS, HAIR
from dd_cash.engine_real_cal import simulate

SCEN = [("A. 50K, TP 40, 1 cuenta (lo que corre)", "50K", 40, 40, 3, 1), ("B. 50K, TP 32, 1 cuenta", "50K", 40, 32, 3, 1), ("C. 50K, TP 32, 2 cuentas", "50K", 40, 32, 3, 2),
        ("D. 50K, TP 32, 3 cuentas", "50K", 40, 32, 3, 3), ("E. 150K, TP 32, 1 cuenta", "150K", 90, 32, 6, 1), ("F. 150K, TP 32, 2 cuentas", "150K", 90, 32, 6, 2)]


def run_cfg(size, nc, tp, nx, T=30000, seed=2026):
    acc, real, nd = setup(size, nc, tp, 100, nx)
    D = np.random.default_rng(seed).integers(0, nd, (T, H))
    r = simulate(acc, D, real=real, lag=2, skip=SKIP)
    fee0 = acc.cs.monthly_fee
    gross = r["take_d"].astype(np.float64)
    take = np.concatenate([np.zeros((T, 5)), gross[:, :-5]], axis=1)             # cobro 5 dias despues; lo no cobrado al cierre del horizonte no cuenta
    return dict(gross=gross.sum(1), cobrado_bruto=take.sum(1), fee_c=r["fee_c_d"].astype(np.float64).sum(1), fee_a=r["fee_a_d"].astype(np.float64).sum(1), fee0=np.full(T, fee0),
                n_att=r["n_att"].astype(float), n_b0=r["n_b0"].astype(float), n_b1=r["n_b1"].astype(float), n_pass=r["n_pass"].astype(float), n_pay=r["n_pay"].astype(float),
                monthly=fee0, fee_total=r["fee_d"].astype(np.float64).sum(1))


def stats(x):
    return f"{x.mean():>8,.0f} {np.median(x):>8,.0f} {np.percentile(x,10):>8,.0f} {np.percentile(x,90):>8,.0f}"


if __name__ == "__main__":
    lines = []; P = lambda s: (print(s), lines.append(s))
    ops12 = OPS * 12
    P(f"DESGLOSE DE COSTOS POR ESCENARIO — 12 meses desde 19-oct-2026 (255 dias habiles), motor validado, payouts con ajuste -{(1-HAIR):.0%}, cobro de payouts 5 dias despues, costo compartido ${OPS}/mes x12 = ${ops12:,.0f} una sola vez")
    cache = {}
    for name, size, nc, tp, nx, n in SCEN:
        key = (size, nc, tp, nx)
        if key not in cache: cache[key] = run_cfg(size, nc, tp, nx)
        c = cache[key]
        pay_adj = c["cobrado_bruto"] * HAIR
        fees_comb = c["fee_c"]; renewals = fees_comb - c["monthly"] * (c["n_b0"] + c["n_b1"])     # renovaciones = fees de Combine - (reinicios + compras nuevas) x precio
        net_acct = pay_adj - fees_comb - c["fee_a"] - c["fee0"]                                   # por cuenta, SIN compartido
        total = n * net_acct - ops12
        P(f"\n{name}")
        P(f"{'':44s}{'media':>8s} {'mediana':>8s} {'p10':>8s} {'p90':>8s}   (USD por cuenta y año salvo la fila TOTAL)")
        rows = [("payouts brutos (motor, cobrados en el horizonte)", c["cobrado_bruto"]), (f"payouts tras el -{(1-HAIR):.0%}", pay_adj),
                ("fees de Combine (renov.+reinicios+compras nuevas)", fees_comb), ("   de los cuales renovaciones mensuales", renewals),
                ("activaciones", c["fee_a"]), ("tarifa inicial del Combine (1 compra)", c["fee0"]), ("neto por cuenta (sin compartido)", net_acct)]
        for lbl, x in rows:
            P(f"  {lbl:42s}{stats(x)}")
        P(f"  {'costo compartido (una vez, todas las cuentas)':42s}{ops12:>8,.0f}")
        P(f"  {'NETO TOTAL con N=%d cuenta(s)' % n:42s}{stats(total)}   P(<0)={np.mean(total<0):.0%}   P(>=7k)={np.mean(total>=7000):.0%}")
        att = 1 + c["n_b0"] + c["n_b1"]
        P(f"  compras/reinicios de Combine por AÑO y por cuenta: intentos totales {att.mean():.1f} (p90 {np.percentile(att,90):.0f}) = 1 inicial + {c['n_b0'].mean():.1f} reinicios + {c['n_b1'].mean():.1f} compras nuevas tras morir la XFA; "
          f"activaciones {c['n_pass'].mean():.1f}; pagos pedidos {c['n_pay'].mean():.1f}")
        P(f"  TOTAL con N={n}: intentos de Combine {n*att.mean():.0f}/año (~{n*att.mean()/12:.1f}/mes), de ellos reinicios {n*c['n_b0'].mean():.0f}, compras nuevas {n*(1+c['n_b1'].mean()):.0f}, activaciones de XFA {n*c['n_pass'].mean():.0f}")
    open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dd_cash", "cost_breakdown_report.txt"), "w").write("\n".join(lines))
