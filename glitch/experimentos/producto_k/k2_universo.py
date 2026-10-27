"""Parte K, K2: universo de productos con los datos locales — rango de la sesión en $ por contrato, fricción (comisión / rango) y correlación entre productos de los RESULTADOS DIARIOS de un
trade de deriva cero (no solo del precio). -> resultados_K2_datos.md
    cd glitch/experimentos/producto_k; PYTHONPATH=../.. python3 k2_universo.py
MODELADO sobre las barras de 5 min locales (2 años, ventana CT 8:30–15:00). Trade común: entrada 9:35 CT, flatten 14:25 CT (13:10 en ZC, cierra 13:20), dirección `alternate` (el MISMO lado en todos
los productos cada fecha, como en producción), SL = TP = ½ de la mediana del rango de la sesión de ESE producto (en ticks), 1 contrato, comisión de Topstep, sin slippage, stop 0.5."""
import os, sys
import numpy as np
import pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "..", "preservacion")); sys.path.insert(0, os.path.join(HERE, "..", "..")); sys.path.insert(0, os.path.join(HERE, "..", "xfa"))
from daydata import load_days, sim_day
from strategies.geometry_pure import SPECS, decide_side, trading_day_index
DC = os.path.join(HERE, "..", "..", "data_cache")
# producto: (parquet, tick, $/tick, comisión round-turn de la página de Topstep del 26-oct-2026, última barra, fuente del tick)
PROD = {
    "MES": ("mes_5min_2y.parquet", 0.25, 1.25, 1.22, 865, "repo"), "MNQ": ("mnq_5min_2y.parquet", 0.25, 0.50, 1.22, 865, "CME (no re-verificado)"),
    "M2K": ("m2k_5min_2y.parquet", 0.10, 0.50, 1.22, 865, "repo"), "MGC": ("mgc_5min_2y_corrected_window.parquet", 0.10, 1.00, 1.92, 865, "repo"),
    "MCL": ("mcl_5min_2y.parquet", 0.01, 1.00, 1.72, 865, "repo (comisión del repo 1.52; Topstep hoy 1.72)"), "M6E": ("m6e_5min_2y.parquet", 0.0001, 1.25, 1.00, 865, "repo"),
    "ZN": ("zn_5min_2y.parquet", 0.015625, 15.625, 2.62, 865, "repo"), "ZC": ("zc_5min_2y.parquet", 0.25, 12.50, 5.28, 790, "repo"),
    "MBT": ("mbt_5min_2y.parquet", 5.0, 0.50, None, 865, "CME (no re-verificado); datos escasos"),
}
REF = 9 * 60 + 35
out = []; P = lambda s="": (print(s), out.append(s))
days, rng_ticks, pnl, ret = {}, {}, {}, {}
for p, (fn, tick, tv, fee, last, src) in PROD.items():
    try:
        dd = load_days(os.path.join(DC, fn), REF, last, tick, fill_gaps=True, dominant_contract=True)
    except Exception as e:
        P(f"[{p}] error al cargar: {e}"); continue
    days[p] = dd
    hi = np.maximum(dd.hi.max(1), 0.0); lo = np.minimum(dd.lo.min(1), 0.0); rng_ticks[p] = hi - lo
    ret[p] = pd.Series(dd.cl[:, -1] * tick / dd.ref, index=pd.to_datetime(dd.dates))
P("# resultados_K2_datos — universo de productos con los datos locales (2 años, 5 min, 9:35 → 14:25 CT)\n")
P("**Fuente y estado.** MODELADO sobre las barras locales (MEDIDO en el sentido de que son precios reales; el resultado del trade es simulado). Comisiones: página de Topstep del 26-oct-2026 (`help.topstep.com/…/8284213`, extracción automática); ticks y valores: `strategies/geometry_pure.py::SPECS` salvo MNQ y MBT (especificación de CME, no re-verificada). **MYM no tiene datos locales.** Los días son los que tienen cobertura completa de la ventana.\n")
P("## A. Tamaño del movimiento y fricción (1 contrato)\n")
P("| producto | días | rango de la sesión, mediana (ticks) | mediana ($/contrato) | p10 – p90 ($) | comisión RT | comisión / rango mediano | SL = TP común (½ mediana, ticks) | SL en $ por contrato |\n|---|---|---|---|---|---|---|---|---|")
half = {}
for p, (fn, tick, tv, fee, last, src) in PROD.items():
    if p not in days: continue
    r = rng_ticks[p]; med = float(np.median(r)); half[p] = max(int(round(med / 2)), 1)
    fee_s = "—" if fee is None else f"${fee:.2f}"
    P(f"| {p} | {days[p].D} | {med:,.0f} | ${med * tv:,.0f} | ${np.percentile(r, 10) * tv:,.0f} – ${np.percentile(r, 90) * tv:,.0f} | {fee_s} | " + ("—" if fee is None else f"{fee / (med * tv) * 100:.2f} %") + f" | {half[p]:,} | ${half[p] * tv:,.0f} |")
P("\n## B. Trade de deriva cero: resultado diario por producto (SL = TP = ½ rango mediano; 1 contrato; mismo lado en todos los productos cada fecha)\n")
P("| producto | n | P&L neto medio/día | desvío ($) | TP % | SL % | FLATTEN % | WR_dec |\n|---|---|---|---|---|---|---|---|")
for p, (fn, tick, tv, fee, last, src) in PROD.items():
    if p not in days or fee is None: continue
    dd = days[p]; alt = np.array([decide_side(trading_day_index(d), "alternate") for d in dd.dates])
    r = {s: sim_day(dd, s, 1, 9000.0, slip=0.0, exit_slip=0.0, sl=half[p], tp=half[p], fee=fee, tick_usd=tv, stop_frac=0.5) for s in (1, -1)}
    k = np.where(alt == 1, r[1][0], r[-1][0]); x = np.where(alt == 1, r[1][1], r[-1][1])
    pnl[p] = pd.Series(x, index=pd.to_datetime(dd.dates))
    tp, sl_ = np.mean(k == 0), np.mean((k == 1) | (k == 2)); fl = np.mean(k == 3)
    P(f"| {p} | {len(x)} | ${x.mean():+,.1f} | ${x.std():,.0f} | {tp * 100:.0f} | {sl_ * 100:.0f} | {fl * 100:.0f} | {tp / max(tp + sl_, 1e-9) * 100:.1f} % |")
P("\n## C. Correlación de los RESULTADOS DIARIOS de ese trade (Pearson, fechas comunes)\n")
D = pd.DataFrame(pnl).dropna(); names = list(D.columns); C = D.corr()
P(f"{len(D)} fechas comunes.\n")
P("| | " + " | ".join(names) + " |\n|---|" + "---|" * len(names))
for a in names: P(f"| **{a}** | " + " | ".join(f"{C.loc[a, b]:.2f}" for b in names) + " |")
R = pd.DataFrame(ret).dropna(); CR = R.corr()
P("\nPara comparar, correlación del **rendimiento de la ventana** (cierre 14:25 / referencia 9:35) entre productos:\n")
rn = list(R.columns)
P("| | " + " | ".join(rn) + " |\n|---|" + "---|" * len(rn))
for a in rn: P(f"| **{a}** | " + " | ".join(f"{CR.loc[a, b]:.2f}" for b in rn) + " |")
iu = np.triu_indices(len(names), 1); mean_rho = float(np.mean(C.values[iu]))
P(f"\n**Correlación media entre resultados diarios de los {len(names)} productos: {mean_rho:.2f}** ⇒ k_eff = k / (1 + (k − 1)·ρ̄) = {len(names) / (1 + (len(names) - 1) * mean_rho):.1f} trades independientes de {len(names)}.")
P("Pares con resultado diario **correlacionado ≥ 0.5** (el mismo trade): " + (", ".join(f"{a}–{b} ({C.loc[a, b]:.2f})" for i, a in enumerate(names) for b in names[i + 1:] if C.loc[a, b] >= 0.5) or "ninguno") + ".")
P("Pares con correlación **< 0.2** (candidatos a trades distintos): " + (", ".join(f"{a}–{b} ({C.loc[a, b]:.2f})" for i, a in enumerate(names) for b in names[i + 1:] if abs(C.loc[a, b]) < 0.2) or "ninguno") + ".")
P("\n*Limitación:* con SL = TP simétrico y deriva cero el resultado depende sobre todo del signo del movimiento del día; como el lado es el mismo en todos los productos, productos con rendimientos correlacionados darán resultados correlacionados. La correlación de resultados medida en 2 años tiene un error estándar ≈ 0.045 (n ≈ 500).")
open(os.path.join(HERE, "resultados_K2_datos.md"), "w", encoding="utf-8").write("\n".join(out) + "\n")
