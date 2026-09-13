"""
DD v2 -- Test 4: Out-of-sample por sub-periodo. MGC ya tenia un split
3-via (scripts/validate_mgc_subperiods_and_direction.py, sobre el
bar-walk denso) -- este script formaliza el MISMO tipo de chequeo
sobre la secuencia REAL de 1 trade/dia (cronologica, la que
efectivamente importa para produccion) para AMBOS candidatos, con un
split 4-via (cuartiles temporales iguales en numero de trading days).
"""
from __future__ import annotations
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from scipy import stats

from dd_v2.common import build_daily_trades, wr_conditional, MES_PATH, MGC_PATH, G2, MGC_XFA


def subperiod_analysis(label: str, df, n_splits: int = 4):
    print(f"\n{'='*90}\n{label} -- split en {n_splits} sub-periodos (cronologico, N total={len(df)})\n{'='*90}")
    n = len(df)
    edges = np.linspace(0, n, n_splits + 1).astype(int)
    wrs = []
    for i in range(n_splits):
        sub = df.iloc[edges[i]:edges[i+1]]
        d0, d1 = sub["session_date"].min().date(), sub["session_date"].max().date()
        wr = wr_conditional(sub)
        n_tp = (sub["label"]==1).sum(); n_sl=(sub["label"]==-1).sum(); n_time=(sub["label"]==0).sum()
        wrs.append(wr)
        print(f"  Q{i+1} [{d0} -> {d1}]  N={len(sub)} (TP={n_tp} SL={n_sl} time={n_time})  WR_condicional={wr:.4f}")

    wrs = np.array(wrs)
    print(f"\n  Rango entre sub-periodos: {wrs.max()-wrs.min():.4f} ({(wrs.max()-wrs.min())*100:.2f}pp)")
    print(f"  Media={wrs.mean():.4f}  Desv.std={wrs.std():.4f}")

    # Chi-cuadrado de homogeneidad: son los WR de los N sub-periodos
    # consistentes con provenir de la MISMA proporcion subyacente?
    tables = []
    for i in range(n_splits):
        sub = df.iloc[edges[i]:edges[i+1]]
        n_tp = int((sub["label"]==1).sum()); n_sl = int((sub["label"]==-1).sum())
        tables.append([n_tp, n_sl])
    tables = np.array(tables)
    chi2, p, dof, _ = stats.chi2_contingency(tables)
    print(f"  Chi-cuadrado de homogeneidad entre sub-periodos: chi2={chi2:.3f}  dof={dof}  p-value={p:.4f}  "
          f"({'RECHAZA homogeneidad -- sub-periodos difieren' if p < 0.05 else 'NO rechaza homogeneidad -- consistente entre sub-periodos'} al 5%)")


if __name__ == "__main__":
    g2_df = build_daily_trades(MES_PATH, "MES", G2.sl_ticks, G2.tp_ticks, G2.max_holding_bars, G2.direction)
    mgc_df = build_daily_trades(MGC_PATH, "MGC", MGC_XFA.sl_ticks, MGC_XFA.tp_ticks, MGC_XFA.max_holding_bars, MGC_XFA.direction)

    subperiod_analysis("G2 (MES, SL=100/TP=40, 1 trade/dia real)", g2_df, n_splits=4)
    subperiod_analysis("MGC_XFA (MGC, SL=TP=364, 1 trade/dia real)", mgc_df, n_splits=4)
    subperiod_analysis("MGC_XFA (MGC, SL=TP=364, 1 trade/dia real) -- 3-via (comparable a validate_mgc_subperiods_and_direction.py)", mgc_df, n_splits=3)
