"""
Solo LECTURA (el usuario lo corre: requiere GITHUB_GIST_TOKEN y GIST_ID). Audita geometry_mes_log.json (G2, Combine 50K):
por cada intento, la secuencia real de resultados/PnL y como termino segun la regla del scheduler (PASE al llegar a +$3,000,
QUIEBRE al tocar el piso trailing), y cuantos PASE se lograron con exactamente 2 TP vs. mas. Contrasta el pass rate empirico contra
lo que implica la contabilidad del propio paper (SL = -$5,049 -> QUIEBRE al primer SL): pass ~= WR^2 (~0.48 con WR 0.73), vs el
81.4% teorico del simulador (que asume perdida limitada a -$1,000 por DLL). Ver GLITCH_RESEARCH_LOG.md, 24-sep-2026.
"""
import os, sys
from math import comb
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from execution.gist_store import load_log
from core.prop_firm import TOPSTEP_50K

TARGET, MLL = TOPSTEP_50K.profit_target, -TOPSTEP_50K.mll_distance


def binom_sf(k, n, p):  # P(X >= k)
    return sum(comb(n, i) * p**i * (1 - p) ** (n - i) for i in range(k, n + 1))


log = [e for e in load_log("geometry_mes_log.json") if e.get("result") in ("TP", "SL", "FLATTEN")]
by = {}
for e in log:
    by.setdefault(e.get("intento", 1), []).append(e)
tp = sum(e["result"] == "TP" for e in log); sl = sum(e["result"] == "SL" for e in log); fl = sum(e["result"] == "FLATTEN" for e in log)
wr = tp / (tp + sl) if tp + sl else float("nan")
print(f"Ciclos resueltos: {len(log)} | TP={tp} SL={sl} FLATTEN={fl} | WR condicional={wr:.3f}")
for k in ("TP", "SL", "FLATTEN"):
    v = [e["pnl"] for e in log if e["result"] == k]
    if v: print(f"  pnl medio {k}: ${sum(v)/len(v):,.0f} (min ${min(v):,.0f}, max ${max(v):,.0f})")
passes = blows = open_ = 0
print("\nPor intento (regla del scheduler):")
for i in sorted(by):
    run = peak = 0.0; end = "EN CURSO"; seq = []
    for e in by[i]:
        run += e["pnl"]; peak = max(peak, run); seq.append(f"{e['result']}{e['pnl']:+,.0f}")
        if run >= TARGET: end = "PASE"; break
        if run <= min(peak + MLL, 0.0): end = "QUIEBRE"; break
    passes += end == "PASE"; blows += end == "QUIEBRE"; open_ += end == "EN CURSO"
    print(f"  #{i}: {end:9s} pnl_final=${run:+,.0f} | {' '.join(seq)}")
n = passes + blows
if n:
    print(f"\nPass rate empirico: {passes}/{n} = {passes/n:.1%}  (intentos en curso: {open_})")
    p_paper = wr ** 2
    print(f"Lo que implica la contabilidad del propio paper (PASE = 2 TP antes de cualquier SL): WR^2 = {p_paper:.1%}")
    print(f"Simulador teorico (perdida limitada a -$1,000 por DLL): 81.4%")
    print(f"P(>= {passes} PASE de {n} | p={p_paper:.2f}) = {binom_sf(passes, n, p_paper):.3f}")
