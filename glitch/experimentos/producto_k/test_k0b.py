"""Pruebas de k0b_projectx_depth.py con un cliente falso (sin red). Correr: cd glitch/experimentos/producto_k && python3 -m pytest -q test_k0b.py"""
import datetime as dt, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import k0b_projectx_depth as k

NOW = dt.datetime(2026, 10, 27, 13, 0, tzinfo=dt.timezone.utc)


def fake_post(listing_start):
    """Barras de 5 min existen desde `listing_start`; Contract/available lista MESZ6 (activo) y MGCV6/MGCZ6."""
    calls = []

    def post(path, body):
        calls.append(path)
        if path == "/api/Contract/available":
            return {"contracts": [{"id": "C.MES.Z26", "name": "MESZ6", "expirationDate": "2026-12-18", "activeContract": True, "tickSize": 0.25, "tickValue": 1.25},
                                  {"id": "C.MGC.V26", "name": "MGCV6", "expirationDate": "2026-10-28", "activeContract": False, "tickSize": 0.1, "tickValue": 1.0},
                                  {"id": "C.MGC.Z26", "name": "MGCZ6", "expirationDate": "2026-12-29", "activeContract": True, "tickSize": 0.1, "tickValue": 1.0}]}
        if path == "/api/Contract/search":
            return {"contracts": [{"id": "C.MES.H25", "name": "MESH5", "expirationDate": "2025-03-21"}, {"id": "C.MES.Z26", "name": "MESZ6", "expirationDate": "2026-12-18"}]}
        if path == "/api/History/retrieveBars":
            s = dt.datetime.strptime(body["startTime"], k.FMT).replace(tzinfo=dt.timezone.utc); e = dt.datetime.strptime(body["endTime"], k.FMT).replace(tzinfo=dt.timezone.utc)
            ls = listing_start.get(body["contractId"], NOW - dt.timedelta(days=100))
            if e < ls: return {"bars": []}
            t0 = max(s, ls); out = []; t = t0
            while t < e and len(out) < body["limit"]:
                out.append({"t": t.strftime(FMT := k.FMT), "o": 1, "h": 2, "l": 0.5, "c": 1.5, "v": 10}); t += dt.timedelta(minutes=5 * body["unitNumber"] if body["unit"] == 2 else 60)
            return {"bars": out}
        raise AssertionError(path)
    post.calls = calls
    return post


def test_product_root():
    assert [k.product_root(x) for x in ("MESZ6", "MGCV6", "6EZ6", "MCLX6", "ZNZ6", "M2KZ6", "MNQZ6", "NQZ6")] == ["MES", "MGC", "6E", "MCL", "ZN", "M2K", "MNQ", "NQ"]
    assert k.product_root("garbage") is None


def test_oldest_available_bisects_to_the_listing_date():
    post = fake_post({"C.MES.Z26": NOW - dt.timedelta(days=400)})
    r = k.oldest_available(post, "C.MES.Z26", NOW)
    # resolución ± la ventana de 5 días; la 1.ª barra da la fecha exacta
    assert 395 <= r["oldest_age_days"] <= 405 and r["first_bar"] is not None and not r["censored_at_max_age"]


def test_oldest_available_censored_when_data_goes_beyond_the_probe():
    post = fake_post({"C.MES.Z26": NOW - dt.timedelta(days=9000)})
    r = k.oldest_available(post, "C.MES.Z26", NOW)
    assert r["oldest_age_days"] == max(k.AGES_DAYS) and r["censored_at_max_age"] is True


def test_oldest_available_none_when_no_recent_data():
    post = fake_post({"C.MES.Z26": NOW + dt.timedelta(days=1)})
    assert k.oldest_available(post, "C.MES.Z26", NOW)["oldest_age_days"] is None


def test_run_is_read_only_and_reports_unlisted_products():
    post = fake_post({"C.MES.Z26": NOW - dt.timedelta(days=300)})
    rep = k.run(post, ["MES", "MGC", "XYZ"], NOW, log=lambda *_: None)
    assert {c for c in post.calls} <= {"/api/Contract/available", "/api/Contract/search", "/api/History/retrieveBars"}      # nunca Order/*, Position/*
    by = {r["product"]: r for r in rep}
    assert by["XYZ"]["note"].startswith("NO listado") and by["MES"]["chosen"] == "MESZ6" and by["MGC"]["chosen"] == "MGCZ6"
    assert by["MES"]["expired_listed"] == 1 and by["MES"]["quote"]["price"] == 1.5


def test_budget_stops_the_script():
    b = k.Budget(fake_post({}), max_calls=2, sleep_s=0)
    b("/api/Contract/available", {}); b("/api/Contract/available", {})
    try:
        b("/api/Contract/available", {}); assert False
    except RuntimeError as e:
        assert "tope" in str(e)
