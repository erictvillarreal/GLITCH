"""Parte G, G1b: distribución real de slippage de entrada a partir del historial de fills.
Entrada: CSV con columnas `date,side,nc,ref,fill[,hour_ct]` (side = LONG/SHORT o 1/-1; ref = referencia pre-trade del mensaje [OPEN] del Pi; fill = precio de fill de TopstepX).
Un historial de operaciones de TopstepX SOLO trae el fill: la referencia hay que tomarla de los mensajes [OPEN] de Telegram (o de `exec` en el historial del Gist una vez desplegado C3).
Sin argumentos usa las 2 observaciones de Eric (19 y 20-oct). -> resultados_G1b.md.   python g1b_slippage_estimator.py [archivo.csv]"""
import csv, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
TICK = {"MES": 0.25, "MGC": 0.10}
def load(path):
    rows = []
    for r in csv.DictReader(open(path)):
        s = {"LONG": 1, "SHORT": -1, "1": 1, "-1": -1}[r["side"].strip().upper()]
        rows.append((r["date"], s, int(r["nc"]), float(r["ref"]), float(r["fill"]), r.get("hour_ct", "")))
    return rows
def slip(side, ref, fill, tick=0.25): return side * (fill - ref) / tick
def summarize(rows, tick=0.25, seed=20261024):
    s = np.array([slip(r[1], r[3], r[4], tick) for r in rows]); n = len(s)
    rng = np.random.default_rng(seed)
    bs = np.array([rng.choice(s, n).mean() for _ in range(10000)]) if n > 1 else np.array([np.nan])
    return dict(n=n, mean=float(s.mean()), sd=float(s.std(ddof=1)) if n > 1 else float("nan"), ci=(float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))), p_gt1=float(np.mean(s > 1)), p_ge2=float(np.mean(s >= 2)), s=s)
if __name__ == "__main__":
    if len(sys.argv) > 1: rows = load(sys.argv[1]); src = sys.argv[1]
    else:
        rows = [("2026-10-19", -1, 40, 7743.25, 7743.00, "09:3x"), ("2026-10-20", 1, 40, 7780.50, 7781.25, "09:3x")]; src = "2 observaciones de Eric (19-oct SHORT, 20-oct LONG; fuente: mensajes [OPEN] y TopstepX)"
    r = summarize(rows)
    out = ["# resultados_G1b — distribución de slippage de entrada (ticks; + = adverso)\n", f"Fuente: {src}.\n",
           f"- N = {r['n']}; valores: {', '.join(f'{x:+.2f}' for x in r['s'])}; media {r['mean']:+.2f}; desvío {r['sd']:.2f}; IC95 bootstrap de la media [{r['ci'][0]:+.2f}, {r['ci'][1]:+.2f}]; P(s > 1) = {r['p_gt1']:.2f}; P(s ≥ 2) = {r['p_ge2']:.2f}.",
           "- **Potencia:** con N = 2 el IC no significa nada (el bootstrap de 2 puntos es degenerado). Para estimar la media con EE ≈ 0.4 tick hacen falta ≈ 25–30 sesiones si σ ≈ 2 ticks (**supuesto**); para separar 1 de 2 ticks de media, ≈ 30; para P(s > 1) con ±17 pp, ≈ 30. **Sin potencia hoy.**",
           "- El historial de operaciones de TopstepX no basta por sí solo: trae el fill pero no la referencia. Necesita: (a) los mensajes [OPEN] de Telegram (referencia) o (b) el parche C3 (`exec.ref_price`, `exec.fill_price`, `exec.t_*`).",
           "- Los fills de MES nc 10 y MEStest son útiles para separar **sistemático vs aleatorio**: el sistemático debería crecer con el tamaño (nc 10 vs 40) y el aleatorio no."]
    open(os.path.join(HERE, "resultados_G1b.md"), "w").write("\n".join(out)); print("\n".join(out))
