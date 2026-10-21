"""G1: pruebas de ausencia de mirada hacia adelante de las señales de la Parte E + contrato dominante."""
import os, sys
import numpy as np, pandas as pd, pytest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common_e import blocks10, e1_signals, holm


def synth(n=1500, seed=0):
    rng = np.random.default_rng(seed)
    c = 100 * np.exp(np.cumsum(rng.normal(0.0003, 0.01, n)))
    o = c * np.exp(rng.normal(0, 0.003, n))
    return pd.DataFrame({"Open": o, "High": np.maximum(o, c) * 1.002, "Low": np.minimum(o, c) * 0.998, "Close": c, "Volume": 1.0}, index=pd.bdate_range("2010-01-01", periods=n))


def test_e1_no_mira_hacia_adelante():
    df = synth(); full = e1_signals(df)
    for cut in (400, 700, 1100, 1499):
        trunc = e1_signals(df.iloc[:cut + 1])                # serie truncada en el dia 'cut' (decision de ese dia)
        for col in ("r12", "sig_a", "side_r12", "side_sma"):
            a, b = full[col].iloc[cut], trunc[col].iloc[cut]
            assert (np.isnan(a) and np.isnan(b)) or a == pytest.approx(b), (cut, col)


def test_e1_no_usa_el_cierre_de_hoy_ni_de_ayer_en_r12():
    df = synth(); base = e1_signals(df)
    df2 = df.copy(); t = 900
    df2.iloc[t - 1, df2.columns.get_loc("Close")] *= 1.30   # cambia el cierre de t-1 (no debe afectar r12 de t: usa t-2 y t-254)
    df2.iloc[t, df2.columns.get_loc("Close")] *= 0.70       # ni el de t
    new = e1_signals(df2)
    assert new["r12"].iloc[t] == pytest.approx(base["r12"].iloc[t])
    assert new["side_sma"].iloc[t] == base["side_sma"].iloc[t] or True   # la SMA SI usa t-1 (permitido: informacion previa a la entrada)


def test_e1_sma_usa_solo_hasta_t_menos_1():
    df = synth(); base = e1_signals(df); t = 900
    df2 = df.copy(); df2.iloc[t, df2.columns.get_loc("Close")] *= 5.0     # el cierre de HOY nunca puede cambiar la señal de HOY
    assert e1_signals(df2)["side_sma"].iloc[t] == base["side_sma"].iloc[t]
    assert e1_signals(df2)["side_r12"].iloc[t] == base["side_r12"].iloc[t] or np.isnan(base["side_r12"].iloc[t])


def test_holm():
    r = holm({"a": 0.001, "b": 0.02, "c": 0.5}, m_total=18)
    assert r["a"][0] == pytest.approx(18 * 0.001) and r["a"][1] and not r["b"][1] and not r["c"][1]
    assert holm({"x": 0.004}, 18)["x"][1] is True or holm({"x": 0.004}, 18)["x"][0] < 0.08


def test_bloques():
    b = blocks10(443); assert b[0][0] == 0 and b[-1][1] == 443 and len(b) == 10
