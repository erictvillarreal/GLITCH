"""Pruebas de k0a/k0c con clientes falsos (sin red ni llaves)."""
import datetime as dt, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import k0a_massive_probe as a, k0c_databento_cost as c

TODAY = dt.date(2026, 10, 27)


def fake_get(oldest_year):
    def get(path, params):
        if path == "/futures/v1/contracts":
            ref = dt.date.fromisoformat(params["date"]); yrs = (TODAY - ref).days / 365.25
            if yrs > 12: return 200, {"results": []}
            return 200, {"results": [{"ticker": params["product_code"] + "Z6", "type": "single", "first_trade_date": "2019-05-06", "last_trade_date": "2026-12-18"},
                                      {"ticker": params["product_code"] + "H7", "type": "single", "last_trade_date": "2027-03-19"}, {"ticker": params["product_code"] + "Z6-H7", "type": "spread"}]}
        if path.startswith("/futures/v1/aggs/"):
            if "window_start_gte" in params:
                yrs = (TODAY - dt.date.fromisoformat(params["window_start_gte"])).days / 365.25
                return (200, {"results": [{"window_start": 1}] * 50}) if yrs <= oldest_year else (403, {"status": "NOT_AUTHORIZED"})
            return 200, {"results": [{"window_start": int((dt.datetime.now(dt.timezone.utc) - dt.timedelta(minutes=10)).timestamp() * 1e9), "close": 1.0}]}
        raise AssertionError(path)
    return get


def test_massive_depth_stops_at_plan_limit():
    r = a.probe_product(fake_get(2.1), "MES", TODAY)
    ok = [x["years_back"] for x in r["refs"] if x.get("n_bars_5m_in_7d_sample")]
    assert max(ok) == 2 and any(x.get("aggs_http") == 403 for x in r["refs"])
    assert all(x["n_contracts"] == 2 for x in r["refs"] if "n_contracts" in x and x["years_back"] <= 10)       # spreads/combos excluidos


def test_massive_resolutions_report_delay():
    r = a.probe_resolutions(fake_get(5), "MGC", TODAY)
    assert r["ticker"] == "MGCZ6" and 550 < r["5min"]["age_s_of_last_bar"] < 700


class FakeMeta:
    def get_cost(self, **k): return 0.5 if "ES" in k["symbols"][0] else 0.25
    def get_record_count(self, **k): return 1000
    def get_billable_size(self, **k): return 56000
    def get_dataset_range(self, **k): return {"start": "2010-06-06"}


class FakeDB: metadata = FakeMeta()


def test_databento_costs_use_continuous_volume_symbols_and_never_download():
    rows = c.costs(FakeDB(), ["ES", "MGC"], "2010-06-06", "2026-10-27", log=lambda *_: None)
    assert [r["symbol"] for r in rows] == ["ES.v.0", "MGC.v.0"] and rows[0]["usd"] == 0.5 and rows[1]["records"] == 1000
    assert c.main(["--symbols", "ES"], client=FakeDB()) == 0
