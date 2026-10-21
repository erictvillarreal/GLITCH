"""§5 del encargo E: (a) inversion de regimen por año de las reglas E1, (b) kill-switch: falsos positivos y potencia por simulacion (semilla fija), (c) mezcla parcial segura. -> RESULTADOS_E_riesgo.md
    python riesgo_e.py"""
import os, sys
import numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from common_e import SEED, e1_signals, load_daily
out = []; P = lambda s="": (print(s), out.append(s))
P("# RESULTADOS_E_riesgo — §5: inversión de régimen, kill-switch y mezcla segura\n")
P("## (a) Inversión de régimen por año — reglas E1 (apertura→cierre, días operados) frente a siempre LARGO\n")
P("| regla | años evaluados | años con exactitud < 50 % | peor año | racha más larga de años < 50 % | años regla > LARGO / igual / < LARGO | cambios de signo de la señal por año (mediana) | % de días con señal fuerte |\n|---|---|---|---|---|---|---|---|")
share = {}
for inst, proxy in (("MGC", "GLD"), ("MES", "^GSPC")):
    df = load_daily(proxy); sg = e1_signals(df)
    for var, col in (("r12", "side_r12"), ("sma", "side_sma")):
        d = pd.DataFrame({"s": sg[col], "o": sg["oc"]}).dropna(); d = d[(d.s != 0) & (d.o != 0)]
        hit = (d.s == d.o).astype(float); lng = (d.o == 1).astype(float)
        ya = hit.groupby(d.index.year).mean(); yl = lng.groupby(d.index.year).mean()
        below = ya < 0.5; run = best = 0
        for b in below: run = run + 1 if b else 0; best = max(best, run)
        s_all = pd.Series(sg[col]).dropna(); flips = (s_all.diff().fillna(0) != 0).groupby(s_all.index.year).sum()
        share[(inst, var)] = float((d.shape[0]) / max((sg["oc"].dropna() != 0).sum(), 1))
        P(f"| {inst} {var} ({proxy}) | {len(ya)} | {int(below.sum())} ({below.mean() * 100:.0f} %) | {ya.idxmin()}: {ya.min() * 100:.0f} % | {best} | {int((ya > yl + 1e-9).sum())} / {int(((ya - yl).abs() <= 1e-9).sum())} / {int((ya < yl - 1e-9).sum())} | {flips.median():.0f} | {share[(inst, var)] * 100:.0f} % |")
P("\nLectura: en los índices la regla de tendencia es SIEMPRE LARGO en la mayoría de los años (igual a LARGO), de modo que su exactitud es la deriva del mercado, no una señal propia. Una regla de tendencia lenta que acierta >50 % en promedio sigue teniendo años por debajo de 50 %; el kill-switch debe soportar rachas así sin disparar por ruido (b).\n")
# ── (b) kill-switch ──
P("## (b) Kill-switch (WR móvil de las últimas W decisiones cerradas < piso → `alternate`): falsos disparos y potencia\n")
P("Simulación de decisiones TP/SL independientes con WR verdadero w (semilla 20261021, 4,000 trayectorias). “Año” = 215 decisiones (MGC: 488 días × 44 % decididos) o 480 (MES). Disparo = al menos una ventana con WR < piso.\n")
rng = np.random.default_rng(SEED)
def trig(w, W, floor, N, paths=4000):
    x = (rng.random((paths, N)) < w).astype(np.int32); c = np.cumsum(np.pad(x, ((0, 0), (1, 0))), axis=1)
    roll = (c[:, W:] - c[:, :-W]) / W; fired = roll < floor - 1e-12
    first = np.where(fired.any(1), fired.argmax(1) + W, N + 1)
    return fired.any(1).mean(), (np.median(first[first <= N]) if (first <= N).any() else np.nan)
P("| W | piso | N decisiones | w = 40 % (rule rota) | w = 45 % | w = 50 % | w = 52 % (regla buena) | w = 55 % | mediana de decisiones hasta el disparo si w = 45 % |\n|---|---|---|---|---|---|---|---|---|")
for W, fl in ((60, 0.45), (120, 0.45), (120, 0.43), (200, 0.45), (200, 0.44)):
    for N in (215, 480):
        r = {w: trig(w, W, fl, N) for w in (0.40, 0.45, 0.50, 0.52, 0.55)}
        P(f"| {W} | {fl * 100:.0f} % | {N} | " + " | ".join(f"{r[w][0] * 100:.0f} %" for w in (0.40, 0.45, 0.50, 0.52, 0.55)) + f" | {r[0.45][1]:.0f} |")
P("\nLectura: con W = 60 y piso 45 % (la especificación del encargo), una regla que SÍ acierta 52 % dispara casi seguro en un año de decisiones: el kill-switch protege, pero también descarta ventajas reales por ruido. Es una decisión de diseño (costo de un falso disparo = volver a `alternate`, que es el estado actual; costo de un falso negativo = operar una regla rota con capital): lo conservador es aceptar los falsos disparos. Propuesta con tests deterministas: `killswitch_NO_DESPLEGAR.py` + `test_killswitch.py` (NO DESPLEGAR).\n")
# ── (c) mezcla parcial segura ──
P("## (c) Mezcla parcial segura (la regla decide solo con señal fuerte; `alternate` en el resto)\n")
P("E1 con lectura 1 ya es una mezcla: opera solo si |r12| ≥ 0.5 σ anual. Fracción de días con señal fuerte (arriba) = peso de la regla; el valor de una ventaja Δ pp se prorratea por esa fracción. Con la ventaja que haría falta (≥ 1–2 pp de WR, §4), una mezcla con 50 % de días con señal da ≈ la mitad del valor ($/pp de §4 × fracción). No se mide ventaja nueva aquí: como ninguna regla pasa G2, la mezcla queda como diseño, no como resultado.\n")
open(os.path.join(HERE, "RESULTADOS_E_riesgo.md"), "w").write("\n".join(out))
