import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np, pandas as pd
from dd_wr.product_sweep import PRODUCTS, load_sessions, walk_all

def per_contract(stem, tick, tv, comm, sl, tp, entry_m, flat_m):
    S = load_sessions(stem)
    t = walk_all(S, tick, tv, comm, 1, sl, tp, entry_m, flat_m)
    return t.set_index("date")["pnl"]

def build():
    stem, tick, tv, comm, cap, om, fm, _ = PRODUCTS["MGC"]
    mgc = per_contract(stem, tick, tv, comm, 364, 364, om + 13, fm)                       # MGC_XFA 364/364, 7:13 CT
    mes = per_contract("mes_5min_2y", 0.25, 1.25, 1.22, 100, 40, 9 * 60 + 45, 14 * 60 + 30)  # G2 100/40, ~9:45 CT
    df = pd.concat([mgc.rename("mgc"), mes.rename("mes")], axis=1).dropna()
    return df
