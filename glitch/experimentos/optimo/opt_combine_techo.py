"""TECHO de P(pasar) del Combine MES (cuenta nueva) con tamaño ÓPTIMO por estado (DP exacta, lado-neutral) frente a P0 (40 fijos) y P3 (finish-line), por geometría (TP) y con/sin slippage.
-> resultados_OPT_COMBINE_TECHO.md        cd glitch/experimentos/optimo; PYTHONPATH=../.. python3 opt_combine_techo.py
MODELADO. DP de horizonte finito (60 días hábiles) con resultados diarios empíricos de MES (días reales, ambos lados promediados para no explotar el ruido de cada lado); el valor en la cuenta nueva es el máximo de P(pasar)
que PUEDE lograr cualquier política de tamaño (0–40 contratos por día) con esa geometría. Slippage de entrada: empírico de 8 obs. (8.ª inferida = 0, NO VERIFICADA) o cero; salida 3 ticks."""
import os, sys, time
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [os.path.join(HERE, "..", "xfa"), os.path.join(HERE, "..", "preservacion")]
import dp as DP
from chain import combine_bank
from daydata import load_days
t0 = time.time(); out = []; P = lambda s="": (print(s, flush=True), out.append(s))
dd = load_days(); EMP8 = (-1.0, 0.0, 1.0, 3.0); EMP8_P = (1 / 8, 3 / 8, 2 / 8, 2 / 8)
P("# resultados_OPT_COMBINE_TECHO — ¿cuánto se puede subir P(pasar) con mejor tamaño? (cuenta nueva, Combine 50K, MES)\n")
P(f"MODELADO ({dd.D} días reales de MES, resultados diarios iid, horizonte 60 días hábiles, rejilla $25). **Techo DP** = máximo P(pasar) alcanzable por CUALQUIER política de tamaño (0–40 contratos por día, adaptativa a saldo y pico). P0 = 40 fijos; P3 = finish-line. Comisión y slippage incluidos; $49 por intento.\n")
rows = []
for sname, (sl_, sp_) in (("slippage empírico (8 obs.)", (EMP8, EMP8_P)), ("slippage 0", ((0.0,), (1.0,)))):
    for tp in (20, 32, 48, 64):
        H0, L0 = DP.build_hist(dd, sl_, sp_, 3.0, sl=100, tp=tp)
        H = np.repeat(H0.mean(axis=0, keepdims=True), 2, axis=0); L = np.repeat(L0.mean(axis=0, keepdims=True), 2, axis=0)
        Vs, pols = DP.solve(H, L, 0, horizon=60); pi, bi = DP.idx_state(50000.0, 50000.0); ceil_ = float(Vs[0][pi, bi])
        res = {}
        for pol in ("P0", "P3"):
            ps, ds = combine_bank(dd, 60000, pol, sl_, sp_, seed=11, exit_slip=3.0, sl_ticks=100, tp_ticks=tp)
            res[pol] = (float(ps.mean()), float(ds.mean()))
        rows.append((sname, tp, ceil_, res)); print("  ", sname, tp, round(time.time() - t0), "s", flush=True)
P("| supuesto | TP (ticks) | P0 (40 fijos) | P3 (finish-line) | **techo DP** | techo − P3 | techo − P0 | compras esperadas por pase: P0 / P3 / techo |\n|---|---|---|---|---|---|---|---|")
for sname, tp, c, r in rows:
    P(f"| {sname} | {tp} | {r['P0'][0] * 100:.1f} % | {r['P3'][0] * 100:.1f} % | **{c * 100:.1f} %** | {(c - r['P3'][0]) * 100:+.1f} pp | {(c - r['P0'][0]) * 100:+.1f} pp | {1 / r['P0'][0]:.2f} / {1 / r['P3'][0]:.2f} / {1 / c:.2f} |")
P("\n**Cota teórica de referencia (sin ventaja):** con piso que sube en tiempo real el máximo es e^(−1)·(2/3) ≈ 24.5 %; con piso que sube con el saldo de **cierre** (el de Topstep) y una sola decisión de tamaño por día se puede superar esa cota; la tabla dice cuánto.")
open(os.path.join(HERE, "resultados_OPT_COMBINE_TECHO.md"), "w", encoding="utf-8").write("\n".join(out) + "\n"); print("OK", round(time.time() - t0), "s")
