"""Cuando sumar una SEGUNDA cuenta Topstep 50K (arranque de la 1a: 19-oct-2026). Momentos: (a) mismo dia, (b) al pasar el Combine la 1a, (c) al cobrar su 1er payout, (d) 10/20/40 dias habiles (2/4/8 semanas),
(e) solo si la 1a sigue viva en el mes N (viva = XFA activa; o caja acumulada >= 0). Senales identicas (misma serie, misma trayectoria de dias) y distintas (MES>MGC + MCL>MCL, geometria estructural).
Configuracion principal = 'paso 2' de structural-levers (TP32 + bracket XFA 728x3, slip 0.5, liquidacion explicita); sensibilidad: paso 1 (364x3). Mundo justo (60 mundos), historia real CON y SIN la ventana de oro.
Motor: dd_cash/lever_engine.py (arranque diferido por trayectoria `start`). SANDBOX / R&D. Uso: python -m scripts.stacking_timing"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np, dataclasses as dc
from dd_cash import lever_data as LD
from dd_cash.lever_engine import simulate
from scripts.lever_common import OPS12

lines = []; P = lambda s: (print(s), lines.append(s))
T = 20000; H = LD.H; NEVER = 10 ** 6
OPS_CUM = np.cumsum(np.where(np.arange(H) % 21 == 0, 59.5, 0.0))
SHIFT = 5


def acct(S, D, start=None):
    r = simulate(S, D, lag=2, skip=LD.SKIP, start=start)
    hair = 1.0 if S.xliq else 0.75
    take = np.concatenate([np.zeros((D.shape[0], SHIFT)), r["take_d"].astype(float)[:, :-SHIFT]], axis=1) * hair
    r["cash"] = np.cumsum(take - r["fee_d"].astype(float), axis=1)
    return r


def starts_from(r1, cash1):
    n = r1["take_d"].shape[0]
    out = {}
    out["(a) mismo dia"] = np.zeros(n, int)
    pd_ = r1["pass_day"]; out["(b) al pasar el Combine la 1a"] = np.where(pd_ > 0, pd_, NEVER)
    paid = r1["take_d"] > 0; fp = np.where(paid.any(1), paid.argmax(1) + 1, NEVER); out["(c) al cobrar el 1er payout la 1a"] = fp
    for w, d in ((2, 10), (4, 20), (8, 40)): out[f"(d) {w} semanas despues"] = np.full(n, d)
    md = r1["mode_d"]
    for N in (3, 6):
        d = 21 * N
        out[f"(e1) mes {N} solo si la 1a tiene XFA viva"] = np.where(np.isin(md[:, d - 1], (1, 3)), d, NEVER)
        out[f"(e2) mes {N} solo si la caja de la 1a >= 0"] = np.where(cash1[:, d - 1] >= 0, d, NEVER)
    return out


def metrics(r1, r2, st):
    n = r1["cash"].shape[0]
    tot_path = r1["cash"] + r2["cash"] - OPS_CUM[None, :]
    tot = tot_path[:, -1]; dd = -np.minimum(tot_path.min(1), 0)
    both = (r1["blow_d"] & r2["blow_d"]).sum(1)
    started = st < H
    act = np.where(started, (H - st) / H, 1.0)
    return dict(mean=tot.mean(), med=np.median(tot), pneg=np.mean(tot < 0), cush=np.percentile(dd, 95), peak=np.percentile(dd, 99), both=both.mean(),
                a1=r1["n_att"].mean(), a2=(r2["n_att"][started] / act[started]).mean() if started.any() else 0.0, a2raw=r2["n_att"].mean(), frac=started.mean(), tot=tot,
                p6=np.mean(tot >= 6000))


def table(title, S1, S2, D1, D2):
    r1 = acct(S1, D1); sts = starts_from(r1, r1["cash"])
    P(f"\n--- {title} ---")
    P(f"{'momento de la 2a cuenta':44s}{'media':>7s}{'mediana':>8s}{'P(<0)':>7s}{'P>=6k':>7s}{'colch95':>8s}{'pico99':>8s}{'dias>=2MLL':>11s}{'int.1a':>7s}{'int.2a/ano':>11s}{'int.tot':>8s}{'apila':>7s}")
    one = dict(mean=(r1["cash"][:, -1] - OPS12).mean(), med=np.median(r1["cash"][:, -1] - OPS12), pneg=np.mean(r1["cash"][:, -1] - OPS12 < 0), p6=np.mean(r1["cash"][:, -1] - OPS12 >= 6000))
    dd1 = -np.minimum((r1["cash"] - OPS_CUM[None, :]).min(1), 0)
    P(f"{'solo 1 cuenta (referencia)':44s}{one['mean']:>7,.0f}{one['med']:>8,.0f}{one['pneg']:>7.0%}{one['p6']:>7.0%}{np.percentile(dd1,95):>8,.0f}{np.percentile(dd1,99):>8,.0f}{0.0:>11.1f}{r1['n_att'].mean():>7.1f}{0.0:>11.1f}{r1['n_att'].mean():>8.0f}{0:>7.0%}")
    out = {}
    for name, st in sts.items():
        r2 = acct(S2, D2, start=st); m = metrics(r1, r2, st); out[name] = m
        P(f"{name:44s}{m['mean']:>7,.0f}{m['med']:>8,.0f}{m['pneg']:>7.0%}{m['p6']:>7.0%}{m['cush']:>8,.0f}{m['peak']:>8,.0f}{m['both']:>11.1f}{m['a1']:>7.1f}{m['a2']:>11.1f}{m['a1']+m['a2raw']:>8.0f}{m['frac']:>7.0%}")
    return r1, sts, out


if __name__ == "__main__":
    P("APILAMIENTO — neto total a 12 meses desde 19-oct-2026 (2 cuentas; costo compartido $714 una vez; liquidacion explicita de la XFA; slip 0.5). Colchon/pico = percentil 95/99 de la mayor caja acumulada negativa. 'int.2a/ano' = intentos de la 2a por ano ACTIVO.")
    # ------------- historia real (eje comun A y B)
    ACC = {"A": ("MES", 585, "MGC", 433), "B": ("MCL", 523, "MCL", 523)}
    geo = {k: LD.structural_geometry(*v) for k, v in ACC.items()}
    axis = LD.common_axis([LD.tab(v[0], v[1], kmax=800, tmax=800) for v in ACC.values()] + [LD.tab(v[2], v[3], kmax=800, tmax=800) for v in ACC.values()])
    spec = {k: LD.make_spec(c_prod=v[0], c_entry=v[1], x_prod=v[2], x_entry=v[3], nc=geo[k]["nc"], tp=geo[k]["tp"], x_sl=geo[k]["x_sl"], x_tp=geo[k]["x_tp"], nc_x=geo[k]["nc_x"], slip=0.5, axis=axis)[0] for k, v in ACC.items()}
    nd = len(axis)
    for gl, mask in (("CON oro", None), ("SIN oro", LD.gold_mask(axis))):
        D = LD.draw(nd, T, 2026, mask)
        table(f"HISTORIA REAL {gl} — senales IDENTICAS (A + A)", spec["A"], spec["A"], D, D)
        table(f"HISTORIA REAL {gl} — senales DISTINTAS (A + B: MES>MGC y MCL>MCL)", spec["A"], spec["B"], D, D)
    # ------------- mundo justo
    SA, axA = LD.make_pool_spec(n_worlds=60, **{k: geo["A"][k] for k in ("nc", "tp", "x_sl", "x_tp", "nc_x")}, slip=0.5)
    SB, axB = LD.make_pool_spec(n_worlds=60, c_prod="MCL", c_entry=523, x_prod="MCL", x_entry=523, **{k: geo["B"][k] for k in ("nc", "tp", "x_sl", "x_tp", "nc_x")}, slip=0.5, seed0=7000)
    DA = LD.draw(len(axA), T, 2026); DB = LD.draw(len(axB), T, 2027)
    table("MUNDO JUSTO — senales IDENTICAS (A + A)", SA, SA, DA, DA)
    table("MUNDO JUSTO — senales DISTINTAS (A + B), independientes", SA, SB, DA, DB)
    # ------------- sensibilidad: paso 1 (TP32, XFA 364x3), identicas, mundo justo
    S1, ax1 = LD.make_pool_spec(n_worlds=60, tp=32, x_sl=364, x_tp=364, nc_x=3, slip=0.5)
    D1 = LD.draw(len(ax1), T, 2026)
    table("SENSIBILIDAD paso 1 (TP32, XFA 364x3) — MUNDO JUSTO — senales IDENTICAS", S1, S1, D1, D1)
    open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dd_cash", "stacking_timing_report.txt"), "w").write("\n".join(lines))
