"""Parte G, G3: comparación de productos con los datos de 5 min locales (2 años) y las comisiones leídas en el Help Center el 24-oct-2026. -> resultados_G3.md
    GLITCH_DATA=<carpeta data_cache> python g3_productos.py"""
import os, sys
import numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__))
DC = os.environ.get("GLITCH_DATA", os.path.join(os.path.dirname(os.environ["GLITCH_MGC_PARQUET"])))
# producto: (archivo, tick, $/tick, round-turn all-in $ [Help Center 24-oct-2026], tope Combine 50K en micros [geometry_pure.SPECS, leido del Help Center el 25-ago], hora de entrada CT (min), flatten CT (min))
PR = {"MES": ("mes_5min_2y", 0.25, 1.25, 1.22, 50, 9 * 60 + 35, 14 * 60 + 30), "MNQ": ("mnq_5min_2y", 0.25, 0.50, 1.22, None, 9 * 60 + 35, 14 * 60 + 30),
      "M2K": ("m2k_5min_2y", 0.10, 0.50, 1.22, 50, 9 * 60 + 35, 14 * 60 + 30), "MGC": ("mgc_5min_2y_corrected_window", 0.10, 1.00, 1.92, 30, 7 * 60 + 15, 14 * 60 + 30),
      "MCL": ("mcl_5min_2y", 0.01, 1.00, 1.72, 30, 9 * 60 + 35, 14 * 60 + 30)}
out = []; P = lambda s="": (print(s, flush=True), out.append(s))
P("# resultados_G3 — comparación de productos (ventana real de cada producto; 2 años de 5 min; contrato dominante por día)\n")
P("Costos: round-turn **todo incluido** (comisión + exchange + regulatorio) por contrato, del artículo de comisiones y tarifas del Help Center de Topstep (consultado el 24-oct-2026; sin fecha de vigencia en la página). Hay un aviso de que CME sube cuotas desde el 1-oct-2026 y para MCL la tabla y el aviso no son consistentes entre sí (NO VERIFICADO cuál es el valor vigente; se usa $1.72). **MYM:** el artículo lo lista a $1.22 pero no hay datos de 5 min locales → sin filas de rango/liquidez. Topes de contratos del Combine 50K: de `geometry_pure.SPECS` (leídos del Help Center el 25-ago-2026; **MNQ y MYM no están en esa tabla: NO VERIFICADO**). Topes del XFA: MGC restringido a 12/18/31 micros según saldo (`RULEBOOK_XFA.md`).\n")
P("| producto | días | rango mediano de la ventana (ticks) | rango mediano $/contrato | round-turn $ | costo % del rango | volumen mediano por barra de 5 min en la hora de entrada (contratos) | 40 contratos como % de esa barra | tope Combine 50K (micros) |\n|---|---|---|---|---|---|---|---|---|")
for k, (stem, tick, tv, rt, cap, e_m, f_m) in PR.items():
    p = os.path.join(DC, stem + ".parquet")
    if not os.path.exists(p): P(f"| {k} | sin archivo | | | ${rt} | | | | {cap} |"); continue
    d = pd.read_parquet(p).tz_convert("America/Chicago"); d["date"] = d.index.date; d["m"] = d.index.hour * 60 + d.index.minute
    rng, vol = [], []
    for dt_, x in d.groupby("date"):
        if "contract" in x.columns and x.contract.nunique() > 1: x = x[x.contract == x.groupby("contract")["volume"].sum().idxmax()]
        w = x[(x.m >= e_m) & (x.m <= f_m)]
        if len(w) < 40: continue
        rng.append((w.high.max() - w.low.min()) / tick); ee = x[(x.m >= e_m) & (x.m < e_m + 10)]
        if len(ee): vol.append(ee.volume.median())
    r = np.array(rng); mv = float(np.median(vol)) if vol else float("nan")
    P(f"| {k} | {len(r)} | {np.median(r):,.0f} | ${np.median(r) * tv:,.0f} | ${rt} | {rt / (np.median(r) * tv) * 100:.3f} % | {mv:,.0f} | {40 / mv * 100 if mv == mv else float('nan'):.1f} % | {cap if cap else 'NO VERIFICADO'} |")
P("\nLectura: el round-turn es **0.3–1.6 % del rango de la ventana** (MNQ el más barato en proporción, MCL el más caro): importa poco frente al tamaño de las barreras (en MES, 40 contratos pagan $48.80 de comisión contra un TP de $1,600, 3 %). **La diferencia real entre productos es la liquidez a la hora de entrada**: 40 contratos son 0.2–0.3 % de una barra de 5 min en MES/MNQ, pero 3.6–7.2 % en MGC, M2K y MCL (barras de ≈ 560–1,100 contratos): ahí el slippage sistemático de tamaño grande **sí** puede ser mayor que en MES (inferencia, sin medir). Un segundo producto vale sobre todo por la **correlación** con el primero (G4), no por costo. Geometría validada en este repo: solo MES (Combine) y MGC (XFA); en la consolidación de Camino B (GLITCH_RESEARCH_LOG) M2K quedó casi empatado (≈ 1.4 %); MNQ/MYM/MCL no tienen geometría validada. Los rangos son de 2 años de 5 min; **no hay fills de ningún otro producto**.")
open(os.path.join(HERE, "resultados_G3.md"), "w").write("\n".join(out))
