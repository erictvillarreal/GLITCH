#!/usr/bin/env python3
"""GLITCH — Parte K, K0(b): profundidad REAL del histórico de ProjectX (SOLO LECTURA). Correr EN EL PI (necesita el entorno del ejecutor y su venv).

Para cada producto: contratos disponibles (nombre, vencimiento, activeContract, tickSize/tickValue, descripción), el contrato activo, el precio actual y la
antigüedad de su última barra (= latencia del dato; Massive tiene ~10 min de retraso), la ventana horaria de la última sesión completa y la profundidad máxima
disponible de barras de 5 min (búsqueda por bisección) para el contrato activo y, si la API los lista, para contratos ya vencidos.
NO coloca, modifica ni cancela nada: solo `Contract/available`, `Contract/search` e `History/retrieveBars`. Limita su ritmo (≈ 3 llamadas/s) y su total (--max-calls).
Uso (en el Pi; el repo del Pi (main) no trae esta carpeta: copia el archivo suelto, p. ej. con scp, a ~/k0b_projectx_depth.py):
                 cd ~/glitch/glitch && ~/glitch-env/bin/python ~/k0b_projectx_depth.py --env-file ~/.glitch_pi.env | tee ~/k0b_salida.txt
                 opciones: --products MES,MNQ,... --json out.json --max-calls 400
Pegar la salida completa en el chat (no contiene credenciales)."""
from __future__ import annotations
import argparse, datetime as dt, json, os, re, sys, time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, os.getcwd())      # en el Pi el script se copia suelto: correrlo desde ~/glitch/glitch para que `brokers.projectx` se encuentre
DEFAULT_PRODUCTS = "MES,MNQ,MYM,M2K,MGC,MCL,M6E,M6B,MBT,MET,SIL,MHG,MNG,ZN,ZB,ZF,ZT,ZC,ZS,ZW,6E,6B,GC,CL,ES,NQ,YM,RTY"
_NAME = re.compile(r"^(.+?)([FGHJKMNQUVXZ])(\d{1,2})$")
FMT = "%Y-%m-%dT%H:%M:%SZ"
AGES_DAYS = (7, 30, 90, 180, 365, 540, 730, 1095, 1460, 1825, 2555, 3650)


def product_root(name: str):
    m = _NAME.match(str(name or ""))
    return m.group(1) if m else None


def bars_in_window(post, contract_id, start: dt.datetime, end: dt.datetime, unit: int = 2, unit_number: int = 5, limit: int = 400, live: bool = False) -> list:
    resp = post("/api/History/retrieveBars", {"contractId": contract_id, "live": live, "startTime": start.strftime(FMT), "endTime": end.strftime(FMT),
                                              "unit": unit, "unitNumber": unit_number, "limit": limit, "includePartialBar": False})
    bars = resp if isinstance(resp, list) else (resp or {}).get("bars", []) or []
    return sorted(bars, key=lambda b: str(b.get("t", "")))


def has_data_at_age(post, contract_id, now, age_days, window_days: int = 5) -> bool:
    start = now - dt.timedelta(days=age_days)
    return len(bars_in_window(post, contract_id, start, start + dt.timedelta(days=window_days), limit=50)) > 0


def oldest_available(post, contract_id, now, ages=AGES_DAYS, refine_steps: int = 6) -> dict:
    """Mayor antigüedad (días) con datos: recorre `ages`, luego bisecta entre el último acierto y el primer fallo. None si ni 7 días tienen datos."""
    hit, miss = None, None
    for a in ages:
        if has_data_at_age(post, contract_id, now, a):
            hit = a
        else:
            miss = a
            break
    if hit is None:
        return {"oldest_age_days": None, "first_bar": None}
    lo, hi = hit, miss
    if hi is not None:
        for _ in range(refine_steps):
            mid = (lo + hi) // 2
            if mid == lo:
                break
            if has_data_at_age(post, contract_id, now, mid):
                lo = mid
            else:
                hi = mid
    start = now - dt.timedelta(days=lo)
    bars = bars_in_window(post, contract_id, start, start + dt.timedelta(days=5), limit=50)
    return {"oldest_age_days": lo, "first_bar": bars[0].get("t") if bars else None, "censored_at_max_age": miss is None}


def last_session_shape(post, contract_id, now, tz_offset_hours: int = -5) -> dict:
    """Barras de 5 min de la última sesión completa de lun-vie (≥ 1 día atrás): primera, última y cantidad (horario de la sesión)."""
    d = (now - dt.timedelta(days=1)).date()
    while d.weekday() >= 5:
        d -= dt.timedelta(days=1)
    start = dt.datetime.combine(d, dt.time(0, 0), tzinfo=dt.timezone.utc)
    bars = bars_in_window(post, contract_id, start, start + dt.timedelta(days=1), limit=1000)
    return {"date": d.isoformat(), "n_bars_5m": len(bars), "first": bars[0].get("t") if bars else None, "last": bars[-1].get("t") if bars else None}


def latest_quote(post, contract_id, now) -> dict:
    bars = bars_in_window(post, contract_id, now - dt.timedelta(minutes=30), now, unit=2, unit_number=1, limit=50)
    if not bars:
        return {"price": None, "bar_t": None, "age_s": None}
    t = str(bars[-1].get("t"))
    try:
        bt = dt.datetime.fromisoformat(t.replace("Z", "+00:00"))
        age = (now - bt).total_seconds()
    except ValueError:
        age = None
    return {"price": bars[-1].get("c"), "bar_t": t, "age_s": age}


class Budget:
    def __init__(self, post, max_calls: int, sleep_s: float):
        self._post, self.max_calls, self.sleep_s, self.n = post, max_calls, sleep_s, 0

    def __call__(self, path, body):
        if self.n >= self.max_calls:
            raise RuntimeError(f"tope de llamadas ({self.max_calls}) alcanzado")
        self.n += 1
        if self.sleep_s:
            time.sleep(self.sleep_s)
        return self._post(path, body)


def run(post, products, now, with_expired: bool = True, log=print) -> list:
    contracts = post("/api/Contract/available", {"live": False})
    contracts = contracts if isinstance(contracts, list) else (contracts or {}).get("contracts", [])
    by_root = {}
    for c in contracts:
        r = product_root(c.get("name"))
        if r:
            by_root.setdefault(r, []).append(c)
    report = []
    for p in products:
        cs = sorted(by_root.get(p, []), key=lambda c: str(c.get("expirationDate", "")))
        row = {"product": p, "n_contracts": len(cs), "contracts": [{k: c.get(k) for k in ("name", "id", "expirationDate", "activeContract", "tickSize", "tickValue", "description")} for c in cs]}
        if not cs:
            row["note"] = "NO listado en Contract/available"; report.append(row); log(f"== {p}: NO listado"); continue
        active = [c for c in cs if c.get("activeContract") is True]
        chosen = (active or cs)[0]
        row["active_marked"] = bool(active); row["chosen"] = chosen.get("name")
        try:
            row["quote"] = latest_quote(post, chosen["id"], now)
            row["last_session"] = last_session_shape(post, chosen["id"], now)
            row["depth_active"] = oldest_available(post, chosen["id"], now)
        except Exception as e:
            row["error"] = str(e)[:200]
        if with_expired:
            try:
                s = post("/api/Contract/search", {"live": False, "searchText": p})
                lst = s if isinstance(s, list) else (s or {}).get("contracts", []) or []
                names = sorted({c.get("name") for c in lst if product_root(c.get("name")) == p})
                row["search_names"] = names
                old = [c for c in lst if product_root(c.get("name")) == p and str(c.get("expirationDate", "")) < now.strftime("%Y-%m-%d")]
                row["expired_listed"] = len(old)
                if old:
                    oc = sorted(old, key=lambda c: str(c.get("expirationDate", "")))[0]
                    row["depth_oldest_expired"] = {"name": oc.get("name"), **oldest_available(post, oc["id"], now)}
            except Exception as e:
                row["search_error"] = str(e)[:160]
        report.append(row)
        q, d, ls = row.get("quote", {}), row.get("depth_active", {}), row.get("last_session", {})
        log(f"== {p}: {row['n_contracts']} contratos; activo(API)={row['active_marked']} elegido={row['chosen']} tick={chosen.get('tickSize')}/{chosen.get('tickValue')} | "
            f"precio={q.get('price')} edad_barra={q.get('age_s')}s | sesion {ls.get('date')}: {ls.get('n_bars_5m')} barras {ls.get('first')}→{ls.get('last')} | "
            f"profundidad activo={d.get('oldest_age_days')}d (1.ª barra {d.get('first_bar')}) | vencidos listados={row.get('expired_listed')} {row.get('depth_oldest_expired', '')}")
    return report


def main(argv=None, post=None, now=None) -> int:
    ap = argparse.ArgumentParser(description="Profundidad de ProjectX (solo lectura)")
    ap.add_argument("--products", default=DEFAULT_PRODUCTS); ap.add_argument("--env-file", default=os.path.expanduser("~/.glitch_pi.env"))
    ap.add_argument("--json", default=None); ap.add_argument("--max-calls", type=int, default=400); ap.add_argument("--no-expired", action="store_true")
    a = ap.parse_args(argv)
    if post is None:
        try:
            for ln in open(a.env_file):
                ln = ln.strip()
                if ln and not ln.startswith("#") and "=" in ln:
                    k, v = ln.replace("export ", "", 1).split("=", 1); os.environ.setdefault(k.strip(), v.strip().strip("'\""))
        except OSError:
            pass
        from brokers.projectx import ProjectXClient, ProjectXCredentials
        client = ProjectXClient(ProjectXCredentials.from_env(), verbose=False); client.ensure_auth()
        post = Budget(client._post, a.max_calls, 0.35)
    now = now or dt.datetime.now(dt.timezone.utc)
    print(f"# K0(b) ProjectX {now.strftime(FMT)} (solo lectura)")
    rep = run(post, [p.strip() for p in a.products.split(",") if p.strip()], now, with_expired=not a.no_expired)
    if a.json:
        json.dump(rep, open(a.json, "w"), indent=2, default=str)
    print(f"# llamadas realizadas: {getattr(post, 'n', '?')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
