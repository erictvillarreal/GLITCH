#!/usr/bin/env python3
"""GLITCH -- Verificacion SOLO LECTURA de los contratos de ProjectX (T4, 12-oct-2026). Correr EN EL PI (necesita las credenciales del entorno del ejecutor y su venv).
Para cada producto imprime TODOS los contratos que casan con el codigo (nombre, vencimiento, activeContract, tickSize, tickValue, id), cual elegiria
pi_executor.resolve_contract_id y si difiere del de vencimiento mas cercano o de la spec local. Sirve para CONFIRMAR en vivo (NO VERIFICADO hasta correrlo) que la API trae
`activeContract` y que su front month coincide con el de volumen que Topstep exige (help.topstep.com/8284108). No coloca ni cancela nada.
Uso: python3 pi/ops/check_contracts.py [--products MES,MGC] [--env-file ~/.glitch_pi.env] [--json]"""
from __future__ import annotations
import argparse, json, os, sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def analyze(contracts: list, code: str, spec) -> dict:
    """Funcion pura: misma regla que pi_executor.resolve_contract_id (activo -> mas cercano), sin importar el ejecutor."""
    matches = [c for c in contracts if code in c.get("name", "")]
    active = [c for c in matches if c.get("activeContract") is True]
    pool = active or matches
    chosen = sorted(pool, key=lambda c: c.get("expirationDate", ""))[0] if pool else None
    nearest = sorted(matches, key=lambda c: c.get("expirationDate", ""))[0] if matches else None
    issues = []
    if not matches:
        issues.append("SIN contratos")
    if matches and not any("activeContract" in c for c in matches):
        issues.append("la API NO trae el campo activeContract (se usaria el vencimiento mas cercano)")
    if matches and not active and any("activeContract" in c for c in matches):
        issues.append("ningun contrato marcado activo")
    if chosen and nearest and chosen.get("id") != nearest.get("id"):
        issues.append(f"el front month activo ({chosen.get('name')}) NO es el de vencimiento mas cercano ({nearest.get('name')})")
    if chosen:
        ts, tv = chosen.get("tickSize"), chosen.get("tickValue")
        if ts is not None and abs(float(ts) - spec.tick_size) > 1e-9:
            issues.append(f"tickSize API={ts} vs spec={spec.tick_size}")
        if tv is not None and abs(float(tv) - spec.tick_value_usd) > 1e-6:
            issues.append(f"tickValue API={tv} vs spec={spec.tick_value_usd}")
    return {"code": code, "matches": [{k: c.get(k) for k in ("name", "expirationDate", "activeContract", "tickSize", "tickValue", "id")} for c in matches],
            "chosen": None if chosen is None else chosen.get("name"), "nearest": None if nearest is None else nearest.get("name"), "issues": issues}


def main(argv=None, client=None) -> int:
    ap = argparse.ArgumentParser(description="Verificacion de contratos (solo lectura)")
    ap.add_argument("--products", default="MES,MGC")
    ap.add_argument("--env-file", default=os.path.expanduser("~/.glitch_pi.env"))
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    try:
        with open(args.env_file) as f:                  # lector minimo KEY=VALUE (mismo formato que EnvironmentFile); nunca imprime valores
            for raw in f:
                line = raw.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.replace("export ", "", 1).split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip().strip("'\""))
    except OSError:
        pass
    from strategies.geometry_pure import SPECS         # noqa: E402
    if client is None:
        from brokers.projectx import ProjectXClient, ProjectXCredentials   # noqa: E402
        client = ProjectXClient(ProjectXCredentials.from_env(), verbose=False)
    contracts = client.get_contracts(live=False)
    report = [analyze(contracts, p, SPECS[p]) for p in args.products.split(",")]
    if args.json:
        print(json.dumps(report, indent=2, default=str))
    else:
        for r in report:
            print(f"== {r['code']}: elegido={r['chosen']}  mas_cercano={r['nearest']}")
            for m in r["matches"]:
                print(f"   {m['name']:<10} vence {m['expirationDate']}  activo={m['activeContract']}  tick={m['tickSize']}/{m['tickValue']}  id={m['id']}")
            print("   " + ("; ".join(r["issues"]) if r["issues"] else "OK: sin hallazgos"))
    return 1 if any(r["issues"] for r in report) else 0


if __name__ == "__main__":
    sys.exit(main())
