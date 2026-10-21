"""G1 — ausencia de mirada hacia adelante en las señales de 5 min (E2/E5) y calculo manual de R / gap."""
import datetime as dt, os, sys
import numpy as np, pandas as pd
import pytest
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from common_e import intraday_signals, prior_stat


def _mk(days=6, ref_hm=570):
    """Barras sinteticas de 5 min 8:30-9:50 CT (UTC-5 en octubre) con un contrato por dia salvo `cambio`."""
    rows = []; rng = np.random.default_rng(1)
    for i in range(days):
        d = dt.datetime(2026, 10, 5 + i, 8, 30)
        for k in range(17):
            ts = pd.Timestamp(d + dt.timedelta(minutes=5 * k), tz="America/Chicago").tz_convert("UTC")
            p = 5000 + 10 * i + rng.normal(0, 1)
            rows.append((ts, p, p + 1, p - 1, p + rng.normal(0, 0.5), 100, "MESZ6"))
    return pd.DataFrame(rows, columns=["ts", "open", "high", "low", "close", "volume", "contract"]).set_index("ts")


def test_R_y_gap_a_mano():
    df = _mk(); s = intraday_signals(df, 570)
    d0, d1 = s.index[0], s.index[1]
    x1 = df.tz_convert("America/Chicago"); x1 = x1[x1.index.date == d1]; x0 = df.tz_convert("America/Chicago"); x0 = x0[x0.index.date == d0]
    pref = float(x1[x1.index.hour * 60 + x1.index.minute == 570]["close"].iloc[0])
    assert s["R"].iloc[1] == pytest.approx(np.log(pref / float(x0["close"].iloc[-1])))
    assert s["gap"].iloc[1] == pytest.approx(np.log(float(x1["open"].iloc[0]) / float(x0["close"].iloc[-1])))
    assert np.isnan(s["R"].iloc[0])


def test_no_mirada_adelante_sintetico():
    df = _mk(); full = intraday_signals(df, 570)
    for t in range(1, 6):
        d = full.index[t]
        cut = df.tz_convert("America/Chicago"); cut = cut[(cut.index.date < d) | ((cut.index.date == d) & (cut.index.hour * 60 + cut.index.minute <= 570))].tz_convert("UTC")
        part = intraday_signals(cut, 570)
        assert part.loc[d, "R"] == pytest.approx(full.loc[d, "R"]) and part.loc[d, "gap"] == pytest.approx(full.loc[d, "gap"])


def test_cambio_de_contrato_da_nan():
    df = _mk(); idx = df.tz_convert("America/Chicago").index
    df.loc[idx.date >= dt.date(2026, 10, 8), "contract"] = "MESH7"
    s = intraday_signals(df, 570)
    assert np.isnan(s["R"].loc[dt.date(2026, 10, 8)]) and not np.isnan(s["R"].loc[dt.date(2026, 10, 9)])


def test_umbral_previo_excluye_el_dia_actual():
    r = pd.Series(np.r_[np.ones(60), [100.0]], index=range(61))
    thr = prior_stat(r, 60, "median")
    assert thr.iloc[60] == 1.0            # el dia 60 (valor 100) no entra en su propio umbral
    assert np.isnan(thr.iloc[59])


@pytest.mark.skipif(not os.environ.get("GLITCH_MGC_PARQUET"), reason="requiere el parquet de MGC")
def test_no_mirada_adelante_datos_reales():
    for path, ref_hm in ((os.environ["GLITCH_MGC_PARQUET"], 435),):
        df = pd.read_parquet(path); full = intraday_signals(df, ref_hm)
        loc = df.tz_convert("America/Chicago"); dates = list(full.index)
        bad = 0; tested = 0
        for d in dates[60::40]:
            cut = loc[(loc.index.date < d) | ((loc.index.date == d) & (loc.index.hour * 60 + loc.index.minute <= ref_hm))].tz_convert("UTC")
            part = intraday_signals(cut, ref_hm)
            if d not in part.index: continue          # dia sin barras hasta la referencia (apertura tardia)
            if np.isnan(full.loc[d, "R"]) and np.isnan(part.loc[d, "R"]): continue
            tested += 1
            if full.loc[d, "contract"] != part.loc[d, "contract"]: continue   # el contrato dominante se elige con el volumen del dia (conocido ex ante como front month)
            bad += not (abs(full.loc[d, "R"] - part.loc[d, "R"]) < 1e-12)
        assert tested > 5 and bad == 0
