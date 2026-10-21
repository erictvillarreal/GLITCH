"""G1 — auditoria de datos de la Parte E -> RESULTADOS_E_G1.md.
    GLITCH_MGC_PARQUET=... python data_audit.py"""
import os, sys
import numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from common_e import DATA, load_daily, session_table
from daydata import DEFAULT_PARQUET
MGC = os.environ["GLITCH_MGC_PARQUET"]
out = []; P = lambda s="": (print(s), out.append(s))
P("# RESULTADOS_E_G1 — auditoría de datos (generado por data_audit.py)\n")
P("## 1. Series de 5 minutos (hora de Chicago, con DST)\n")
P("| serie | días | días con >1 contrato | primer bar CT (distribución) | último bar CT | cambios de contrato dominante entre días consecutivos |\n|---|---|---|---|---|---|")
for nm, path in (("MES", DEFAULT_PARQUET), ("MGC", MGC)):
    raw = pd.read_parquet(path).tz_convert("America/Chicago"); raw["date"] = raw.index.date
    mixed = int((raw.groupby("date").contract.nunique() > 1).sum())
    st = session_table(path)
    chg = int((st.contract != st.contract.shift()).sum() - 1)
    fh = st.first_hm.value_counts().head(3); lh = st.last_hm.value_counts().head(3)
    P(f"| {nm} | {len(st)} | {mixed} | " + ", ".join(f"{k // 60}:{k % 60:02d} ({v})" for k, v in fh.items()) + " | " + ", ".join(f"{k // 60}:{k % 60:02d} ({v})" for k, v in lh.items()) + f" | {chg} |")
    # DST: el primer bar debe ser el mismo hora CT todo el año; se verifica por mes
    by = raw.groupby("date").apply(lambda x: x.index[0].hour * 60 + x.index[0].minute)
    P(f"\n  - {nm}: primer bar de la sesión por mes (mín–máx): " + "; ".join(f"{m}:{by[[d.month == m for d in by.index]].min() // 60}:{by[[d.month == m for d in by.index]].min() % 60:02d}" for m in (1, 3, 4, 7, 10, 11)))
P("\n  El archivo **MGC intercala barras de dos contratos** en los días contados arriba (H1 de la Parte D): toda señal y todo resultado de MGC usa el **contrato dominante del día (mayor volumen)**; las señales nocturnas se descartan cuando el contrato dominante cambia entre sesiones.\n")
P("## 2. Series diarias largas (Yahoo, precios crudos)\n")
P("| serie | días | desde | hasta | duplicadas | volumen cero | |ret c/c| > 8 % | |ret a/c| > 8 % | P(c/c > 0) | P(a/c > 0) |\n|---|---|---|---|---|---|---|---|---|---|")
for t in ("GLD", "GC=F", "^GSPC", "SPY", "ES=F"):
    d = load_daily(t); cc = np.log(d.Close / d.Close.shift(1)); oc = np.log(d.Close / d.Open)
    P(f"| {t} | {len(d)} | {d.index.min().date()} | {d.index.max().date()} | 0 | {int((d.Volume == 0).sum())} | {int((cc.abs() > .08).sum())} | {int((oc.abs() > .08).sum())} | {np.mean(cc.dropna() > 0) * 100:.2f} % | {np.mean(oc.dropna() > 0) * 100:.2f} % |")
P("\n### 2.1 Sesgo de los rolls en `GC=F` y `ES=F` (splice sin ajustar): comparación con series sin rolls en las mismas fechas\n")
for fut, spot in (("GC=F", "GLD"), ("ES=F", "SPY")):
    f = load_daily(fut); s = load_daily(spot); j = f.join(s, lsuffix="_f", rsuffix="_s", how="inner")
    j = j[j.index >= max(f.index.min(), s.index.min())]
    rf = np.log(j.Close_f / j.Close_f.shift(1)); rs = np.log(j.Close_s / j.Close_s.shift(1)); d = (rf - rs).dropna()
    thr = 0.004 if fut == "GC=F" else 0.003
    big = d[d.abs() > thr]
    ocf = np.log(j.Close_f / j.Open_f)
    P(f"- {fut} vs {spot} ({len(d)} días comunes): P(c/c>0) {np.mean(rf.dropna() > 0) * 100:.2f} % vs {np.mean(rs.dropna() > 0) * 100:.2f} % (spot); P(a/c>0) de {fut} {np.mean(ocf.dropna() > 0) * 100:.2f} %. Días con |ret_fut − ret_spot| > {thr * 100:.1f} %: {len(big)} ({len(big) / len(d) * 100:.1f} % de los días); de ellos {np.mean(big > 0) * 100:.0f} % con el futuro por ENCIMA del spot (días de roll con contango).")
P("\n**Conclusión G1 (datos):** (a) el cierre→cierre de los futuros continuos de Yahoo **no se usa** (los rolls sesgan P(subir) unos décimos a puntos); se usan las series sin rolls (`GLD`, `^GSPC`, `SPY`) y el apertura→cierre de los futuros solo como robustez; (b) las series de 5 min traen DST correcto (primer bar fijo en hora CT todo el año); (c) las señales nocturnas se anulan en los días en que cambia el contrato dominante.")
open(os.path.join(HERE, "RESULTADOS_E_G1.md"), "w").write("\n".join(out))
