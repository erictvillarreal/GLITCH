"""T2 — Momento de la TERCERA cuenta (50K). Supone la 2.a cuenta a las 4 semanas (20 dias habiles, recomendacion de stacking-timing) con senales distintas. Terceras senales: C1 = MGC 9:45 > MGC 9:45 (distinta) o
A (identica, referencia). B (MCL) usa el tope oficial de 30 micros (Risk Adjustments 13613539). Momentos: (a) con la 2.a, (b) +4 semanas, (c) +8 semanas, (d) al 1er payout de la 2.a, (e) condicionales (mes 3 / mes 4).
Mundo justo (60 mundos, productos independientes), historia real CON y SIN oro (correlacion real). Motor lever_engine. SANDBOX. Uso: python -m scripts.t2_third_account"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np, dataclasses as dc
from dd_cash import lever_data as LD
from scripts.stacking_timing import acct, OPS_CUM, NEVER
from scripts.lever_common import OPS12

lines = []; P = lambda s: (print(s), lines.append(s))
T = 20000; H = LD.H; S2DAY = 20
ACC = {"A": ("MES", 585, "MGC", 433), "B": ("MCL", 523, "MCL", 523), "C": ("MGC", 585, "MGC", 585)}
GEO = {"A": LD.structural_geometry(*ACC["A"]), "B": LD.structural_geometry(*ACC["B"], cap_nc=30), "C": LD.structural_geometry(*ACC["C"], cap_nc=30)}
KEYS = ("nc", "tp", "x_sl", "x_tp", "nc_x")


def starts3(r1, r2, st2):
    n = r1["take_d"].shape[0]; out = {}
    cash12 = r1["cash"] + r2["cash"] - OPS_CUM[None, :]
    out["(a) con la 2.a (dia 20)"] = np.full(n, S2DAY)
    out["(b) 4 semanas despues de la 2.a"] = np.full(n, S2DAY + 20)
    out["(c) 8 semanas despues de la 2.a"] = np.full(n, S2DAY + 40)
    paid = r2["take_d"] > 0; fp = np.where(paid.any(1), paid.argmax(1) + 1, NEVER); out["(d) al 1er payout de la 2.a"] = fp
    for M in (3, 4):
        d = 21 * M
        out[f"(e1) mes {M}: solo si 1.a y 2.a tienen XFA viva"] = np.where(np.isin(r1["mode_d"][:, d - 1], (1, 3)) & np.isin(r2["mode_d"][:, d - 1], (1, 3)), d, NEVER)
        out[f"(e2) mes {M}: solo si caja de 1.a+2.a (neta de ops) >= 0"] = np.where(cash12[:, d - 1] >= 0, d, NEVER)
    return out


def table(title, S1, S2, S3, D1, D2, D3):
    r1 = acct(S1, D1); st2 = np.full(D1.shape[0], S2DAY); r2 = acct(S2, D2, start=st2)
    sts = starts3(r1, r2, st2)
    P(f"\n--- {title} ---")
    P(f"{'momento de la 3.a cuenta':50s}{'media':>7s}{'mediana':>8s}{'P(<0)':>7s}{'P>=10k':>7s}{'colch95':>8s}{'pico99':>8s}{'d>=2MLL':>8s}{'d>=3MLL':>8s}{'int.tot':>8s}{'apila':>6s}")
    rows = {}
    def line(name, tot_path, blow_sum, att, frac):
        tot = tot_path[:, -1]; dd = -np.minimum(tot_path.min(1), 0)
        P(f"{name:50s}{tot.mean():>7,.0f}{np.median(tot):>8,.0f}{np.mean(tot<0):>7.0%}{np.mean(tot>=10000):>7.0%}{np.percentile(dd,95):>8,.0f}{np.percentile(dd,99):>8,.0f}{(blow_sum>=2).sum(1).mean():>8.1f}{(blow_sum>=3).sum(1).mean():>8.1f}{att:>8.0f}{frac:>6.0%}")
    base_path = r1["cash"] + r2["cash"] - OPS_CUM[None, :]
    line("solo 2 cuentas (referencia)", base_path, r1["blow_d"].astype(int) + r2["blow_d"], r1["n_att"].mean() + r2["n_att"].mean(), 0.0)
    for name, st in sts.items():
        r3 = acct(S3, D3, start=st)
        path = base_path + r3["cash"]; bs = r1["blow_d"].astype(int) + r2["blow_d"] + r3["blow_d"]
        line(name, path, bs, r1["n_att"].mean() + r2["n_att"].mean() + r3["n_att"].mean(), (st < H).mean())
        rows[name] = path[:, -1].mean()
    r3 = acct(S3, D3, start=np.zeros(D1.shape[0], int)); r2z = acct(S2, D2, start=np.zeros(D1.shape[0], int))
    line("(ref) las 3 cuentas el mismo dia 0", r1["cash"] + r2z["cash"] + r3["cash"] - OPS_CUM[None, :], r1["blow_d"].astype(int) + r2z["blow_d"] + r3["blow_d"],
         r1["n_att"].mean() + r2z["n_att"].mean() + r3["n_att"].mean(), 1.0)
    return rows


if __name__ == "__main__":
    P("T2 — 3.a cuenta; neto total a 12 meses desde 19-oct-2026 de 3 cuentas (costo compartido $714 una vez), liquidacion explicita XFA, slip 0.5. 'int.tot' = compras de Combine (iniciales+reinicios+recompras) al ano, las 3 cuentas (proxy RTP). pico99 = p99 de la mayor caja negativa.")
    P("Geometrias estructurales: " + " | ".join(f"{k}: nc {g['nc']} TP {g['tp']} / XFA {g['x_sl']}x{g['nc_x']}" for k, g in GEO.items()))
    axis = LD.common_axis([LD.tab(v[0], v[1], kmax=800, tmax=800) for v in ACC.values()] + [LD.tab(v[2], v[3], kmax=800, tmax=800) for v in ACC.values()])
    spec = {k: LD.make_spec(c_prod=v[0], c_entry=v[1], x_prod=v[2], x_entry=v[3], **{kk: GEO[k][kk] for kk in KEYS}, slip=0.5, axis=axis)[0] for k, v in ACC.items()}
    nd = len(axis)
    for gl, mask in (("CON oro", None), ("SIN oro", LD.gold_mask(axis))):
        D = LD.draw(nd, T, 2026, mask)
        table(f"HISTORIA REAL {gl} — 3.a DISTINTA (A + B[MCL, tope 30] + C[MGC 9:45])", spec["A"], spec["B"], spec["C"], D, D, D)
        table(f"HISTORIA REAL {gl} — 3.a IDENTICA a A (referencia: A + B + A)", spec["A"], spec["B"], spec["A"], D, D, D)
    pools = {k: LD.make_pool_spec(n_worlds=60, c_prod=v[0], c_entry=v[1], x_prod=v[2], x_entry=v[3], **{kk: GEO[k][kk] for kk in KEYS}, slip=0.5, seed0=3000 + 100 * i) for i, (k, v) in enumerate(ACC.items())}
    Ds = {k: LD.draw(len(pools[k][1]), T, 2026 + i) for i, k in enumerate(ACC)}
    table("MUNDO JUSTO — 3.a DISTINTA (productos independientes)", pools["A"][0], pools["B"][0], pools["C"][0], Ds["A"], Ds["B"], Ds["C"])
    open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dd_cash", "t2_third_account_report.txt"), "w").write("\n".join(lines))
