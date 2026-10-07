"""Prueba de 'realidad' (maximo estadistico por permutacion, estilo Westfall-Young) sobre TODAS las combinaciones producto x hora x regla de direccion exploradas.
Estructura estandar en unidades de rango: TP = 0.35*R, SL = 0.10*R ticks (R = rango diario mediano entrada->flatten). Reglas: alternar, siempre largo, siempre corto.
Nulo: en cada dia se elige al azar el resultado largo o corto (exitoso bajo simetria); se registra el MAXIMO |t| sobre todas las combinaciones. p corregido = P(max_nulo >= max_observado).
Tambien reporta la media de la mezcla L/S (centro del nulo) para ver si la estructura misma se aparta de un juego justo. SANDBOX / R&D."""
import os, sys, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
from scripts.tables_generic import build, median_range_ticks, INF
from scripts.xfa_search import ENTRIES, EARLY_MGC
from strategies.geometry_pure import trading_day_index

def outc(tab, tp, sl):
    tb = tab["tpt"][:, tp]; ab = tab["adv"][:, sl]
    return np.where(tb < ab, float(tp), np.where(ab < INF, -float(sl), tab["flat"]))

if __name__ == "__main__":
    combos = []
    for prod in ("MES", "MNQ", "M2K", "MGC", "MCL", "M6E"):
        ents = dict(ENTRIES); 
        if prod == "MGC": ents.update(EARLY_MGC)
        for en, em in ents.items():
            R = median_range_ticks(prod, em); tp = max(2, int(round(0.35 * R))); sl = max(1, int(round(0.10 * R)))
            L = build(prod, em, side_mode="always_long"); S = build(prod, em, side_mode="always_short")
            oL, oS = outc(L, tp, sl), outc(S, tp, sl)
            alt = np.array([1 if trading_day_index(dt.date.fromisoformat(d)) % 2 == 0 else -1 for d in L["dates"]])
            combos.append((prod, en, tp, sl, oL, oS, alt))
    def tstat(o): return o.mean() / (o.std(ddof=1) / np.sqrt(len(o)))
    obs = []
    for prod, en, tp, sl, oL, oS, alt in combos:
        for rule, o in (("alternar", np.where(alt == 1, oL, oS)), ("largo", oL), ("corto", oS)):
            obs.append((tstat(o), prod, en, rule, tp, sl, o.mean(), (oL.mean() + oS.mean()) / 2))
    obs.sort(reverse=True)
    print(f"{len(combos)} combinaciones producto x hora, {len(obs)} pruebas (x3 reglas). Top-10 por t:")
    for t, prod, en, rule, tp, sl, mu, mix in obs[:10]:
        print(f"   t={t:+.2f}  {prod} {en} {rule:9s} tp={tp} sl={sl}  EV={mu:+.2f} ticks (mezcla L/S {mix:+.2f})")
    rng = np.random.default_rng(11); NP = 400; mx = np.empty(NP)
    for p in range(NP):
        best = -9
        for prod, en, tp, sl, oL, oS, alt in combos:
            n = len(oL)
            for _ in range(3):
                o = np.where(rng.random(n) < 0.5, oL, oS)
                t = tstat(o)
                if t > best: best = t
        mx[p] = best
    tobs = obs[0][0]
    print(f"\nNulo (signos aleatorios por dia, {NP} permutaciones): maximo t esperado sin direccion: mediana {np.median(mx):.2f}, p95 {np.percentile(mx,95):.2f}")
    print(f"t maximo observado = {tobs:.2f} -> p corregido (Westfall-Young) = {np.mean(mx >= tobs):.3f}")
    # media de la mezcla L/S por combinacion: desviacion estructural respecto a un juego justo
    mixes = sorted([((oL.mean() + oS.mean()) / 2, prod, en) for prod, en, tp, sl, oL, oS, alt in combos], reverse=True)
    print("\nMezcla L/S (EV ticks/trade con signo aleatorio) - top 6 y bottom 3:")
    for m, prod, en in mixes[:6] + mixes[-3:]:
        print(f"   {prod} {en}: {m:+.2f}")
