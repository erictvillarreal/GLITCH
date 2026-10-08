"""Tarea 1 — Validacion FUERA DE MUESTRA de TP 32 vs TP 40 (G2/MES, nc=40, SL nominal 100; liquidacion del MLL real a 40 ticks), Combine Topstep 50K con reglas reales.
(1) 10 bloques temporales contiguos de los 515 dias: win rate (TP antes que el stop), P(pasar), media/mediana/P(perdida) anual del pipeline (motor validado), TP32 vs TP40 PAREADOS por bloque;
(2) walk-forward con expansion: se elige el mejor TP de K=13 candidatos con los bloques de entrenamiento y se mide en el bloque siguiente; (3) reality check (White) con bootstrap por bloques de 10 dias sobre los 13 TP;
(4) punto de equilibrio y win rate observado. SANDBOX / R&D, offline. Uso: python -m scripts.tp32_oos_validation"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
from scripts.g2_real_rules_scan import build_tables, simulate, INF
from scripts.decision_breakdown import setup, H, SKIP, OPS, HAIR
from dd_cash.engine_real_cal import simulate as pipe_sim

K = (20, 25, 28, 30, 31, 32, 33, 34, 35, 36, 40, 45, 50)       # TP (ticks) probados en este analisis (13)
NB = 10


def wilson(k, n, z=1.96):
    p = k / n; d = 1 + z * z / n; c = p + z * z / (2 * n); m = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (c - m) / d, (c + m) / d


def passrate(T, idx, tp, n=20000, seed=7):
    return simulate(T, idx, 40, tp, 100, dll=False, cons=0.55, n=n, max_days=30, seed=seed)["pass_rate"]


def pipeline_net(tp, D, acc_cache):
    acc, real, nd = acc_cache[tp]
    r = pipe_sim(acc, D, real=real, lag=2, skip=SKIP)
    take = np.concatenate([np.zeros((D.shape[0], 5)), r["take_d"].astype(float)[:, :-5]], axis=1)
    return take.sum(1) * HAIR - r["fee_d"].astype(float).sum(1) - acc.cs.monthly_fee - OPS * 12


if __name__ == "__main__":
    lines = []; P = lambda s: (print(s), lines.append(s))
    T = build_tables(); adv, tpt, flat = T; nd = len(adv); blocks = np.array_split(np.arange(nd), NB)
    P(f"VALIDACION FUERA DE MUESTRA de TP 32 vs TP 40 — {nd} dias de MES, {NB} bloques contiguos de ~{nd//NB} dias; Combine 50K reglas reales (MLL en tiempo real, consistencia 55%, min 2 dias)")
    P(f"Valores de TP probados en ESTE analisis: K={len(K)} {K}. En todo el proyecto el grid de geometrias (Camino B bajo reglas reales: 1,080 configs; Parte B: 767 configs; barridos del 5-8 oct) suma >1,800 configuraciones.")
    # ---- 4) equilibrio y win rate
    P("\n[1] PUNTO DE EQUILIBRIO Y WIN RATE OBSERVADO (win = el TP se toca antes que el stop; barra ambigua = stop primero)")
    for tp in (32, 40):
        for lbl, sl in (("stop EFECTIVO 40 ticks (liquidacion del MLL con nc=40; lo que pasa en el Combine)", 40), ("stop NOMINAL 100 ticks (Practice/paper; el MLL de 150K no vincula)", 100)):
            ok = tpt[:, tp] < adv[:, sl]; k = int(ok.sum()); lo, hi = wilson(k, nd)
            be0 = sl / (sl + tp); loss = sl * 50 + 48.8; win = tp * 50 - 48.8; be1 = loss / (win + loss)
            per_block = [np.mean(ok[b]) for b in blocks]
            P(f"  TP{tp} / {lbl}: WR observado {k/nd:.1%} [IC95% {lo:.1%}-{hi:.1%}] | equilibrio sin comision {be0:.1%}, con comision {be1:.1%} | exceso sobre equilibrio (con comision) {k/nd-be1:+.1%} | por bloque min {min(per_block):.0%} max {max(per_block):.0%}")
    P("  -> el win rate de TP 32 NO supera su punto de equilibrio (tampoco el de TP 40): no hay edge de direccion; la ventaja de TP 32 es de ESTRUCTURA (dos TP netos de $1,551 suman $3,102 >= $3,000), no de acertar mas.")
    # ---- 1) bloques
    P("\n[2] POR BLOQUE (pareado, mismos numeros aleatorios): P(pasar el Combine) TP32 vs TP40")
    d_pass = []
    for i, b in enumerate(blocks):
        a, c = passrate(T, b, 32, seed=11 + i), passrate(T, b, 40, seed=11 + i)
        d_pass.append(a - c)
        P(f"  bloque {i+1:2d} ({len(b)} dias): TP32 {a:.1%} | TP40 {c:.1%} | diferencia {a-c:+.1%}")
    d_pass = np.array(d_pass)
    rng = np.random.default_rng(1); bs = np.array([d_pass[rng.integers(0, NB, NB)].mean() for _ in range(20000)])
    npos = int((d_pass > 0).sum())
    # prueba de signos
    from math import comb
    p_sign = sum(comb(NB, k) for k in range(npos, NB + 1)) / 2 ** NB
    P(f"  diferencia media {d_pass.mean():+.1%}; TP32 gana en {npos}/{NB} bloques (prueba de signos unilateral p={p_sign:.3f}); IC95% bootstrap por bloques [{np.percentile(bs,2.5):+.1%}, {np.percentile(bs,97.5):+.1%}]")
    # ---- pipeline anual por bloque
    P("\n[3] PIPELINE ANUAL por bloque (motor validado, 12 meses, payouts -25%, compartido $59.5/mes): media, mediana, P(perdida) con dias muestreados solo de ese bloque")
    acc_cache = {tp: setup("50K", 40, tp, 100, 3) for tp in (32, 40)}
    nd2 = acc_cache[32][2]; blocks2 = np.array_split(np.arange(nd2), NB)
    rows = []
    for i, b in enumerate(blocks2):
        D = np.random.default_rng(100 + i).choice(b, size=(6000, H))
        r32, r40 = pipeline_net(32, D, acc_cache), pipeline_net(40, D, acc_cache)
        rows.append((r32.mean(), np.median(r32), np.mean(r32 < 0), r40.mean(), np.median(r40), np.mean(r40 < 0)))
        P(f"  bloque {i+1:2d}: TP32 media ${r32.mean():>6,.0f} mediana ${np.median(r32):>6,.0f} P(<0) {np.mean(r32<0):.0%} | TP40 media ${r40.mean():>6,.0f} mediana ${np.median(r40):>6,.0f} P(<0) {np.mean(r40<0):.0%}")
    R = np.array(rows); dm = R[:, 0] - R[:, 3]
    bs2 = np.array([dm[rng.integers(0, NB, NB)].mean() for _ in range(20000)])
    P(f"  promedio entre bloques: TP32 media ${R[:,0].mean():,.0f} (mediana ${R[:,1].mean():,.0f}, P(<0) {R[:,2].mean():.0%}) vs TP40 media ${R[:,3].mean():,.0f} (mediana ${R[:,4].mean():,.0f}, P(<0) {R[:,5].mean():.0%}); "
      f"diferencia de la media ${dm.mean():+,.0f}/año, TP32 mejor en {(dm>0).sum()}/{NB} bloques, IC95% bootstrap por bloques [${np.percentile(bs2,2.5):+,.0f}, ${np.percentile(bs2,97.5):+,.0f}]")
    # ---- 2) walk-forward
    P("\n[4] WALK-FORWARD con expansion: se elige el mejor TP de K=13 con los bloques de entrenamiento y se mide en el bloque siguiente (fuera de muestra)")
    sel = []; lift = []
    for j in range(2, NB):
        train = np.concatenate(blocks[:j]); test = blocks[j]
        scores = {tp: passrate(T, train, tp, n=12000, seed=5) for tp in K}
        best = max(scores, key=scores.get)
        o_sel, o40, o32 = passrate(T, test, best, seed=21 + j), passrate(T, test, 40, seed=21 + j), passrate(T, test, 32, seed=21 + j)
        sel.append(best); lift.append((o_sel, o40, o32))
        P(f"  entrena bloques 1-{j} -> elige TP{best} ({scores[best]:.1%} en entrenamiento) | bloque {j+1} fuera de muestra: elegido {o_sel:.1%} | TP40 {o40:.1%} | TP32 {o32:.1%}")
    L = np.array(lift)
    P(f"  promedio fuera de muestra: TP elegido {L[:,0].mean():.1%} | TP40 {L[:,1].mean():.1%} | TP32 fijo {L[:,2].mean():.1%}; TP elegidos {sorted(set(sel))}; el elegido supera a TP40 en {(L[:,0]>L[:,1]).sum()}/{len(L)} bloques y TP32 fijo supera a TP40 en {(L[:,2]>L[:,1]).sum()}/{len(L)}")
    # ---- 3) reality check
    P("\n[5] REALITY CHECK (White) sobre los K=13 TP vs benchmark TP40: bootstrap por bloques de 10 dias, B=200")
    full = np.arange(nd)
    d_k = {tp: passrate(T, full, tp, n=40000, seed=3) - passrate(T, full, 40, n=40000, seed=3) for tp in K if tp != 40}
    P("  diferencia de P(pasar) frente a TP40 en toda la muestra: " + ", ".join(f"TP{tp} {d_k[tp]:+.1%}" for tp in d_k))
    V = max(d_k.values()); best_tp = max(d_k, key=d_k.get)
    Vstar = []; d32 = []
    for b in range(200):
        starts = rng.integers(0, nd - 10, int(np.ceil(nd / 10)))
        pool = np.concatenate([np.arange(s, s + 10) for s in starts])[:nd]
        base = passrate(T, pool, 40, n=6000, seed=100 + b)
        dd = {tp: passrate(T, pool, tp, n=6000, seed=100 + b) - base for tp in d_k}
        Vstar.append(max(dd[tp] - d_k[tp] for tp in d_k)); d32.append(dd[32])
    p_rc = float(np.mean(np.array(Vstar) >= V)); d32 = np.array(d32)
    P(f"  mejor candidato en la muestra: TP{best_tp} ({V:+.1%}); p-valor del reality check (maximo entre 13) = {p_rc:.3f}")
    P(f"  TP32 vs TP40: diferencia en la muestra {d_k[32]:+.1%}; IC95% bootstrap por bloques [{np.percentile(d32,2.5):+.1%}, {np.percentile(d32,97.5):+.1%}]; p unilateral sin corregir {np.mean(d32 - d_k[32] >= d_k[32]):.3f}")
    # ---- conclusion
    ok_blocks = npos >= 7; ci_pos = np.percentile(bs, 2.5) > 0
    verdict = "SI" if (ok_blocks and ci_pos and p_rc < 0.10) else ("NO" if np.percentile(bs, 97.5) < 0 else "NO CONCLUYENTE")
    P(f"\nCONCLUSION: ¿la ventaja de TP 32 sobrevive fuera de muestra? -> {verdict}. Diferencia en P(pasar) {d_pass.mean():+.1%} (IC95% por bloques [{np.percentile(bs,2.5):+.1%}, {np.percentile(bs,97.5):+.1%}]); "
      f"reality check p={p_rc:.3f} con K=13; anual {dm.mean():+,.0f} USD (IC95% [{np.percentile(bs2,2.5):+,.0f}, {np.percentile(bs2,97.5):+,.0f}]).")
    open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dd_cash", "tp32_oos_validation_report.txt"), "w").write("\n".join(lines))
