"""Parte H, H5: productos, separando Combine (hoy MES) y XFA (hoy MGC). Proxies marcados. -> resultados_H5.md
    GLITCH_MGC_PARQUET=... python h5_producto.py"""
import math, os, sys
import numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__))
DC = os.path.dirname(os.environ["GLITCH_MGC_PARQUET"])
# producto: (archivo, tick, $/tick, round-turn all-in (Help Center 24-oct), tope Combine 50K en micros (geometry_pure.SPECS, 25-ago; None = NO VERIFICADO), hora de entrada CT (min))
PR = {"MES": ("mes_5min_2y", 0.25, 1.25, 1.22, 50, 9 * 60 + 35), "MNQ": ("mnq_5min_2y", 0.25, 0.50, 1.22, None, 9 * 60 + 35), "M2K": ("m2k_5min_2y", 0.10, 0.50, 1.22, 50, 9 * 60 + 35),
      "MGC": ("mgc_5min_2y_corrected_window", 0.10, 1.00, 1.92, 30, 7 * 60 + 15), "MCL": ("mcl_5min_2y", 0.01, 1.00, 1.72, 30, 9 * 60 + 35)}
FLAT = 14 * 60 + 30
out = []; P = lambda s="": (print(s, flush=True), out.append(s))
P("# resultados_H5 — productos: riesgo por dólar, correlaciones y límites\n")
rows, rets = {}, {}
for k, (stem, tick, tv, rt, cap, e_m) in PR.items():
    d = pd.read_parquet(os.path.join(DC, stem + ".parquet")).tz_convert("America/Chicago"); d["date"] = d.index.date; d["m"] = d.index.hour * 60 + d.index.minute
    R, vol, rr, dts = [], [], [], []
    for dt_, x in d.groupby("date"):
        if "contract" in x.columns and x.contract.nunique() > 1: x = x[x.contract == x.groupby("contract")["volume"].sum().idxmax()]
        w = x[(x.m >= e_m) & (x.m <= FLAT)]
        if len(w) < 40: continue
        R.append((w.high.max() - w.low.min()) / tick); e = x[(x.m >= e_m) & (x.m < e_m + 10)]; vol.append(e.volume.median() if len(e) else np.nan)
        rr.append(np.log(w.close.iloc[-1] / w.close.iloc[0])); dts.append(dt_)
    rets[k] = pd.Series(rr, index=pd.to_datetime(dts)); rows[k] = (np.median(R), np.nanmedian(vol))
P("## 1. Riesgo por dólar con la geometría del Combine escalada al rango del producto (MLL $2,000)\n")
P("Geometría de MES (liquidación a 40 ticks = 0.23 del rango mediano de la ventana, TP 32 = 0.19) trasladada a cada producto **en unidades de su propio rango**; nc = lo necesario para que la liquidación cueste $2,000, topado por el límite del plan. **Si el tope impide usar todo el presupuesto, el TP paga menos y hacen falta más TP para los $3,000 (proxy de dificultad).**\n")
P("| producto | rango mediano ticks | liquidación (ticks) | TP (ticks) | nc necesarios para $2,000 | tope Combine 50K | nc usable | $ por TP (neto de comisión) | TP necesarios para $3,000 | comisión % del $ por TP | volumen/barra de entrada | estado |\n|---|---|---|---|---|---|---|---|---|---|---|---|")
for k, (stem, tick, tv, rt, cap, e_m) in PR.items():
    Rm, vm = rows[k]; liq = max(1, round(0.2326 * Rm)); tp = max(1, round(0.186 * Rm)); need = 2000.0 / (liq * tv); nc = min(math.ceil(need), cap) if cap else math.ceil(need)
    tpd = tp * tv * nc - rt * nc; ntp = math.ceil(3000 / tpd)
    P(f"| {k} | {Rm:,.0f} | {liq} | {tp} | {need:,.0f} | {cap if cap else 'NO VERIFICADO'} | {nc if cap else '—'} | ${tpd:,.0f} | {ntp if cap else '—'} | {rt * nc / (tp * tv * nc) * 100:.1f} % | {vm:,.0f} | rango MEDIDO (2 años); topes: SPECS 25-ago |")
P("\nLectura: con la geometría relativa al rango, MES necesita ≈ 40 contratos y 2 TP (hoy). **MGC sí puede usar todo el presupuesto de $2,000 con ≈ 20 micros (tope 30) y 2 TP; M2K (necesita 70, tope 50) y MCL (necesita 80, tope 30) no pueden**, y MCL además paga el doble de fricción (8.6 % del TP) y necesita 6 TP; MNQ necesita ≈ 20 contratos (tope NO VERIFICADO). La fricción (comisión como % del $ por TP) va de 1.5 % (MNQ) a 8.6 % (MCL). **Las diferencias reales son el tope de contratos, la fricción y el volumen de la barra de entrada.**\n")
P("## 2. Correlación de los retornos de la ventana (misma ventana de cada producto, 2 años, días comunes)\n")
df = pd.concat(rets, axis=1).dropna(); C = df.corr()
P("| | " + " | ".join(df.columns) + " |\n|---|" + "---|" * len(df.columns))
for k in df.columns: P(f"| **{k}** | " + " | ".join(f"{C.loc[k, j]:.2f}" for j in df.columns) + " |")
P(f"\n({len(df)} días comunes; los retornos van de la entrada al flatten de cada producto, **no del mismo intervalo**: MGC 7:15–14:30, el resto 9:35–14:30. Estado: MEDIDO.) **Hecho clave:** MES, MNQ y M2K se mueven casi juntos (ρ 0.87–0.97): un segundo producto *de índices* no diversifica nada; **MGC y MCL tienen ρ ≈ 0.1–0.2 con MES.** **MYM:** sin datos de 5 min locales y sin descargar el Dow diario: **DESCONOCIDO** (se espera ρ alta con los demás índices; NO medido).\n")
P("## 3. Dos preguntas separadas\n")
P("**(a) Producto para el Combine (hoy MES).** Criterios: liquidez a la hora de entrada, tope que permita el presupuesto completo de $2,000, comisión relativa, geometría validada. **MES cumple los cuatro; MNQ cumple liquidez y costo relativo pero su tope y su geometría no están verificados; M2K/MGC/MCL tienen barras 15× más delgadas (40 contratos = 4–7 % de la barra) y, MGC/MCL, tope 30.** No hay evidencia en este repo de que otro producto mejore P(pasar) a igualdad de presupuesto: **la barrera efectiva es el MLL, no el producto**, y P(TP antes de liquidación) con martingala es 55.6 % en cualquiera.\n")
P("**(b) Producto para la XFA (hoy MGC).** Criterios: rango por contrato, comisión, tope de micros de la XFA (MGC: 12/18/31 según saldo, `RULEBOOK_XFA.md`), reglas de noticias, correlación con el Combine. **MGC ($420 de rango mediano por contrato en la ventana de 7:15 a 14:30; ρ ≈ 0.17 con MES)** es coherente con el Combine de MES como par poco correlacionado. No se probó otro producto en la XFA con el motor de la Parte D (no hay geometría validada ni historia de pagos): **DESCONOCIDO**; cualquier cambio sería sobre todo de correlación entre cuentas (G4) y de comisión, no de dólares por cuenta demostrados.\n")
P("**Hallazgo para G4 (b):** el par realista de dos productos para diversificar es **MES + MGC (ρ de retornos ≈ 0.17, MEDIDO)**, no MES + MNQ/M2K (ρ ≥ 0.87). Un Combine de **MGC con ≈ 20 micros** cabe en el tope y presupuesto (modelado, **sin geometría validada ni slippage medido**): es la prueba de segundo producto con más sentido.\n")
P("**Qué marcaría la diferencia y cómo medirlo:** un segundo producto en una **cuenta Practice** durante 20–30 sesiones (slippage, liquidez, fills) antes de cualquier prueba en Combine/XFA.")
open(os.path.join(HERE, "resultados_H5.md"), "w", encoding="utf-8").write("\n".join(out))
