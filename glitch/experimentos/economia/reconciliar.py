"""C1 -- Conciliacion de las cifras economicas de una cuenta Topstep 50K (Combine G2/MES + XFA Cerebro 2/MGC). Un solo comando:

    python reconciliar.py --engine-root /ruta/a/checkout/de/research/firm-map-and-labs@6d4b069/glitch [--T 20000] [--quick]

Motor: dd_cash/lever_engine.py (rama research/firm-map-and-labs, commit 6d4b069; NO esta en main). Este script NO modifica ese motor: lo importa y cambia UN supuesto por fila
(puente acumulativo), de la convencion del 26-sep (`engine_real`, ~$4.6k de media) a la convencion actual con friccion real. Ademas valida la P(pase) de la Parte A contra la del
motor (mismas barras, mismos supuestos) y modela por primera vez el Responsible Trading Program (RTP) como regimen alterno (DLL automatico en el Combine + XFA solo ruta Consistency).
Salida: resultados_C1.md.  Semillas fijas. Cada cifra sale de una corrida; los supuestos con su fuente estan en la tabla impresa al final.
"""
from __future__ import annotations

import argparse
import dataclasses as dc
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))


def setup(engine_root):
    sys.path.insert(0, engine_root)
    os.chdir(engine_root)               # el motor lee data_cache/ relativo a su raiz
    from dd_cash import lever_data as LD
    sys.path.insert(0, HERE)
    from lever_engine_ref import simulate, with_ref_anchor
    return LD, simulate, with_ref_anchor


def run_cfg(LD, simulate, S, axis, mask=None, T=20000, seed=2026, lag=2, hair=None):
    """Misma contabilidad que scripts/lever_common.run (payout cobrado 5 dias despues, fees completos, costo compartido $59.5/mes x12 una vez),
    con el haircut explicito: hair=None -> convencion actual (1.0 si hay liquidacion explicita de la XFA, 0.75 si no)."""
    D = LD.draw(len(axis), T, seed, mask)
    r = simulate(S, D, lag=lag, skip=LD.SKIP)
    if hair is None:
        hair = 1.0 if (S.xliq and not S.legacy) else 0.75
    gross = r["take_d"].astype(np.float64)
    take = np.concatenate([np.zeros((D.shape[0], 5)), gross[:, :-5]], axis=1) * hair
    cash = np.cumsum(take - r["fee_d"].astype(np.float64), axis=1)
    ops12 = 59.5 * 12
    net = cash[:, -1] - ops12
    return dict(net=net, att=r["n_att"].astype(float), npass=r["n_pass"].astype(float), npay=r["n_pay"].astype(float), pay=take.sum(1),
                fees=r["fee_d"].astype(np.float64).sum(1) + ops12, blow_d=r["blow_d"], touch=r["blow_d"].sum(1).astype(float))


def summ(n):
    return dict(mean=float(np.mean(n)), med=float(np.median(n)), p10=float(np.percentile(n, 10)), p90=float(np.percentile(n, 90)), pneg=float(np.mean(n < 0)))


def fmt(s):
    return f"{s['mean']:,.0f} / {s['med']:,.0f} / P(<0) {s['pneg'] * 100:.0f}%"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--engine-root", default=os.environ.get("GLITCH_ENGINE_ROOT"), help="carpeta glitch/ del checkout de research/firm-map-and-labs @6d4b069")
    ap.add_argument("--T", type=int, default=20000); ap.add_argument("--worlds", type=int, default=30); ap.add_argument("--quick", action="store_true")
    a = ap.parse_args()
    if not a.engine_root:
        sys.exit("falta --engine-root (o GLITCH_ENGINE_ROOT)")
    if a.quick: a.T, a.worlds = 3000, 6
    out_path = os.path.join(HERE, "resultados_C1.md")
    LD, simulate, wra = setup(os.path.abspath(a.engine_root))
    out = []; t0 = time.time()
    P = lambda s="": (print(s, flush=True), out.append(s))
    X = dict(x_sl=364, x_tp=364, nc_x=3)

    def W(ref=True, **kw):
        """mundos: real CON oro, real SIN oro (ventana 14-nov-2025..26-ene-2026). ref=True: el slippage de entrada se modela como el Pi real (TP/SL anclados a la REFERENCIA)."""
        Sr, axr = LD.make_spec(**kw)
        Sr = wra(Sr, ref)
        return {"CON oro": (Sr, axr, None), "SIN oro": (Sr, axr, LD.gold_mask(axr))}

    def Wj(ref=True, **kw):
        """mundo justo: n_worlds mundos sinteticos con signo volteado al azar (sin deriva muestral)."""
        Sf, axf = LD.make_pool_spec(n_worlds=a.worlds, **kw)
        return {"justo": (wra(Sf, ref), axf, None)}

    P("# resultados_C1 (generado por reconciliar.py)\n")
    P(f"T={a.T} trayectorias por celda, 12 meses desde 19-oct-2026, 1 cuenta 50K; neto = payouts cobrados - fees (incluye tarifa inicial y activaciones) - $714 de costos compartidos. Formato: media / mediana / P(neto<0).\n")

    # ── puente acumulativo ───────────────────────────────────────────────────────────────────────────────────────────
    steps = [
        ("S0 Convencion 26-sep (`engine_real`): TP40, reglas del motor validado, XFA serie fija, slip 0, SIN haircut", dict(tp=40, slip=0.0, legacy=True, xliq=False, **X), 1.0, "A"),
        ("S1 + haircut -25% de payouts (proxy de liquidacion XFA usado desde el 24-sep)", dict(tp=40, slip=0.0, legacy=True, xliq=False, **X), 0.75, "A"),
        ("S2 + TP 32 (aprobado 12-oct, NO desplegado)", dict(tp=32, slip=0.0, legacy=True, xliq=False, **X), 0.75, "A"),
        ("S3 + reglas de pago verificadas (min $125, ganancia neta desde el ultimo pago, topes)", dict(tp=32, slip=0.0, xliq=False, **X), 0.75, "A"),
        ("S4 + liquidacion XFA en tiempo real EXPLICITA (reemplaza el haircut)", dict(tp=32, slip=0.0, xliq=True, **X), None, "A"),
        ("S5 + stop llenado en el extremo de la barra (slip 0.5)", dict(tp=32, slip=0.5, xliq=True, **X), None, "A"),
        ("S6a + slippage de entrada 1 tick (lunes 19-oct), bracket anclado a la REFERENCIA como el Pi real", dict(tp=32, slip=0.5, xliq=True, entry_slip=1, **X), None, "A"),
        ("S6b + slippage de entrada 3 ticks (martes 20-oct, inferido), idem", dict(tp=32, slip=0.5, xliq=True, entry_slip=3, **X), None, "A"),
    ]
    rows = []; res_cache = {}
    P("## Puente acumulativo: de la cifra del 26-sep a la convencion actual (una cuenta, 12 meses)\n")
    for label, kw, hair, _ in steps:
        cells = []
        for wname, (S, ax, mask) in {**Wj(nc=40, sl=100, **kw), **W(nc=40, sl=100, **kw)}.items():
            r = run_cfg(LD, simulate, S, ax, mask=mask, T=a.T, hair=hair)
            res_cache[(label, wname)] = r
            cells.append(fmt(summ(r["net"])))
        att = np.mean([res_cache[(label, w)]["att"].mean() for w in ("justo", "CON oro", "SIN oro")]); npass = np.mean([res_cache[(label, w)]["npass"].mean() for w in ("justo", "CON oro", "SIN oro")])
        rows.append([label, *cells, f"{att:.0f} / {npass:.1f}"])
    hdr = ["paso (acumulativo)", "mundo justo", "real CON oro", "real SIN oro", "intentos / pases por ano (prom. 3 mundos)"]
    P("| " + " | ".join(hdr) + " |"); P("|" + "|".join(["---"] * len(hdr)) + "|")
    for r_ in rows: P("| " + " | ".join(r_) + " |")

    # delta por paso (CON oro y SIN oro, media)
    P("\n### Efecto de cada supuesto (diferencia de la MEDIA respecto al paso anterior, $/ano)\n")
    P("| paso | justo | CON oro | SIN oro |"); P("|---|---|---|---|")
    prev = None
    for label, *_ in steps:
        cur = {w: np.mean(res_cache[(label, w)]["net"]) for w in ("justo", "CON oro", "SIN oro")}
        if prev is not None:
            P(f"| {label.split(' ')[0]} {label.split('+')[-1].strip()[:70]} | {cur['justo'] - prev['justo']:+,.0f} | {cur['CON oro'] - prev['CON oro']:+,.0f} | {cur['SIN oro'] - prev['SIN oro']:+,.0f} |")
        prev = cur

    P("\n### Mapa: que version publicada corresponde a que paso\n")
    P("| version publicada | cifra publicada | paso que la reproduce | cifra reproducida aqui (real CON oro / SIN oro / justo, media) |"); P("|---|---|---|---|")
    mm = lambda lab: " / ".join(f"{np.mean(res_cache[(lab, w)]['net']):,.0f}" for w in ("CON oro", "SIN oro", "justo"))
    P(f"| `engine_real` 26-sep | media ~$4.6k (386/mes x12), mediana $3,532 | S0 | {mm(steps[0][0])} |")
    P(f"| `lever_engine` 7-oct (structural-levers) | TP32: $3.3k / $1.9k / $3.7k (CON / SIN / justo) | S4 | {mm(steps[4][0])} |")
    P(f"| doc 13-oct (T1, numero de planeacion ~$2,000) | nc40 TP32: $2.6k / $1.1k / $3.0k | S5 | {mm(steps[5][0])} |")
    P("\n(Las tres cifras eran correctas PARA SU CONVENCION; difieren por supuestos concretos de la tabla de arriba, no por errores de calculo. El unico supuesto que ninguna de las tres modelaba como el Pi real es el ancla del bracket a la referencia.)")

    # ── validacion cruzada de P(pase) (Parte A vs motor) ───────────────────────────────────────────────────────────────
    P("\n## Validacion cruzada: P(pase) por intento, Parte A vs motor (misma entrada 9:45 CT, TP32/SL100, nc40, cuenta nueva, slip de stop 0)\n")
    sys.path.insert(0, os.path.join(HERE, "..", "preservacion"))
    from daydata import load_days
    from sim import OutcomeTable, pol_fixed, run_mc
    dd = load_days(ref_hm=9 * 60 + 45, last_hm=14 * 60 + 30)
    P("| slip de entrada (ticks) | Parte A (replay 492 dias, MC 20k) | motor ANCLA A LA REFERENCIA: real CON oro / SIN oro / justo | motor ancla al FILL (convencion anterior): real CON oro / SIN oro / justo |"); P("|---|---|---|---|")
    for es in (0, 1, 2, 3):
        tabs = {0: OutcomeTable(dd, float(es), 0.0, "adverse", 100, 32, step=10.0)}
        ra = run_mc(pol_fixed(40), tabs, n=20000, seed=5, bal0=50000.0, peak0=50000.0, start_idx=1774, maxdays=40)
        res = {}
        for anchor in (True, False):
            cells = {}
            for wname, (S, ax, mask) in {**Wj(ref=anchor, nc=40, sl=100, tp=32, slip=0.0, xliq=True, entry_slip=es, **X), **W(ref=anchor, nc=40, sl=100, tp=32, slip=0.0, xliq=True, entry_slip=es, **X)}.items():
                D = LD.draw(len(ax), 8000, 7, mask)[:, :40]
                r = simulate(dc.replace(S, K=1), D, lag=2, skip=None)
                cells[wname] = float((r["pass_day"] > 0).mean())
            res[anchor] = cells
        f = lambda d: f"{d['CON oro'] * 100:.1f}% / {d['SIN oro'] * 100:.1f}% / {d['justo'] * 100:.1f}%"
        P(f"| {es} | {ra.p_pass * 100:.1f}% [{ra.ci_pass[0] * 100:.1f},{ra.ci_pass[1] * 100:.1f}] | {f(res[True])} | {f(res[False])} |")
    P("\nLectura: con slip 0 todos coinciden (31-34%). Con slip >= 2 solo la columna 'ancla a la referencia' (la mecanica REAL del Pi: pi_executor.py calcula TP/SL desde el ultimo close y luego manda la orden de mercado) "
      "reproduce el desplome de la Parte A; el ancla al fill (convencion de los reportes del 7 al 13-oct) lo subestima. Mecanismo: con nc=40 y TP 32, dos TP netos suman $3,002 con slip 1 (>= $3,000) pero $2,902 con slip 2 y $2,802 con slip 3 "
      "-> hace falta un TERCER TP y la probabilidad cae de ~30% a ~17%. Es un acantilado, no una pendiente.\n")

    # ── regimen RTP ────────────────────────────────────────────────────────────────────────────────────────────────────
    P("## RTP (Responsible Trading Program), por primera vez modelado como REGIMEN alterno (no como probabilidad)\n")
    P("Fuente (help.topstep.com/13620045, leida 24-sep y citada en el log): el RTP es revision discrecional, no publica umbrales; consecuencias: DLL automatico en Combines nuevas ($1,000 en 50K) y XFA solo ruta Consistency (40%). "
      "NO existe dato para estimar la probabilidad de entrar al RTP; se reportan los dos regimenes puros y el neto de cada uno, y el lector pondera. El patron de G2 toca varios criterios (perdida mayor que ganancia, max position en la mayoria de trades, varias cuentas tocando el MLL el mismo dia).\n")
    kw = dict(nc=40, sl=100, tp=32, slip=0.5, xliq=True, entry_slip=1, **X)
    base = {**Wj(**kw), **W(**kw)}
    kw_rtp = dict(kw, dll=1000.0, path="cons")
    rtp = {**Wj(**kw_rtp), **W(**kw_rtp)}
    P("| regimen (slip entrada 1, stop 0.5) | justo | CON oro | SIN oro |"); P("|---|---|---|---|")
    for lab, wd in (("normal", base), ("RTP: DLL $1,000 en el Combine + XFA ruta Consistency 40%", rtp)):
        P(f"| {lab} | " + " | ".join(fmt(summ(run_cfg(LD, simulate, S, ax, mask=m, T=a.T)["net"])) for (S, ax, m) in wd.values()) + " |")

    # ── rango unico ────────────────────────────────────────────────────────────────────────────────────────────────────
    P("\n## Rango unico (una cuenta, TP32, liquidacion XFA explicita, stop 0.5, XFA vigente MGC 364x3)\n")
    P("| slippage de entrada | justo | CON oro | SIN oro |"); P("|---|---|---|---|")
    final = {}
    for lab, es_list in (("0 ticks (optimista)", [0]), ("1 tick (lunes 19-oct)", [1]), ("mezcla {1,3} 50/50 (observado, N=2)", [1, 3]), ("3 ticks (martes 20-oct, inferido)", [3])):
        cells = []
        for wn in ("justo", "CON oro", "SIN oro"):
            nets = []
            for es in es_list:
                kw = dict(nc=40, sl=100, tp=32, slip=0.5, xliq=True, entry_slip=es, **X)
                S, ax, m = ({**Wj(**kw), **W(**kw)})[wn]
                nets.append(run_cfg(LD, simulate, S, ax, mask=m, T=a.T)["net"])
            n = np.concatenate(nets); final[(lab, wn)] = summ(n); cells.append(fmt(summ(n)))
        P(f"| {lab} | " + " | ".join(cells) + " |")
    P("\n### Sensibilidad: primeros $10,000 de ganancias de por vida al 100% (help.topstep.com/8284233, leido 20-oct-2026: SOLO para traders que entraron al dashboard nuevo antes del 12-ene-2026; elegibilidad de Eric: NO VERIFICADA)\n")
    P("| slippage de entrada | sin beneficio | con beneficio (first100=10,000) |"); P("|---|---|---|")
    for lab, es_list in (("1 tick", [1]), ("mezcla {1,3}", [1, 3])):
        for wn in ("CON oro", "SIN oro"):
            cells = []
            for f100 in (0.0, 10000.0):
                nets = []
                for es in es_list:
                    kw = dict(nc=40, sl=100, tp=32, slip=0.5, xliq=True, entry_slip=es, first100=f100, **X)
                    S, ax, m = ({**Wj(**kw), **W(**kw)})[wn]
                    nets.append(run_cfg(LD, simulate, S, ax, mask=m, T=a.T)["net"])
                cells.append(fmt(summ(np.concatenate(nets))))
            P(f"| {lab}, {wn} | {cells[0]} | {cells[1]} |")
    P(f"\n(tiempo total {time.time() - t0:.0f}s)")
    open(out_path, "w").write("\n".join(out)); print("escrito", out_path)


if __name__ == "__main__":
    main()
