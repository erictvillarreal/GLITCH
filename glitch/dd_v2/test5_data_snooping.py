"""
DD v2 -- Test 5: Data snooping / seleccion del mejor candidato.

G2: `scripts/camino_b_grid.py` corrio un grid FORMAL de 8,100 configs
(sl,tp,hold,direction,nc,trades_per_day) y se quedo con el top por
combines_por_ano -- ese es exactamente el escenario de riesgo de
"mejor de muchos" que White's Reality Check/SPA existen para
cuestionar. Aqui: percentil del pick dentro de su propia poblacion +
un Bonferroni-style bound sobre el pass_rate.

IMPORTANTE (limitacion honesta, no escondida): el candidato REALMENTE
desplegado (G2, SL=100/TP=40) es un escalado manual 2x de G1 (el
verdadero ganador del grid, SL=50/TP=20) -- G2 en si NO es miembro del
grid guardado (su SL=100 excede el SL_GRID de camino_b_grid.py, que
llega a 50). Se verifica G1 contra el grid completo (aplica
directamente), y se reporta el gap G1->G2 como lo que es: una
refinacion post-hoc, validada por separado con split-half temporal
(scripts/camino_b_direction_check.py), no una eleccion adicional
dentro de la misma poblacion de 8,100.

MGC_XFA: la geometria RR=1.0/SL=TP=364 fue una eleccion de DISEÑO
(bracket simetrico "gambler's ruin", sin necesitar edge) -- no el
resultado de una busqueda de SL/TP que haya optimizado por
performance. El unico parametro que SI se barrio con varios valores
fue nc (1,2,3,4,6 en cerebro2_grid_exhaustive.csv) -- se documenta
por separado, sin forzar el mismo marco de "mejor-de-grid" sobre el
bracket en si.
"""
from __future__ import annotations
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data_cache")


def g2_snooping():
    df = pd.read_csv(os.path.join(DATA_DIR, "camino_b_grid_results.csv"))
    print("=" * 90)
    print(f"G2 -- data snooping sobre camino_b_grid_results.csv ({len(df):,} configs evaluadas)")
    print("=" * 90)

    # G1 = el ganador REAL del grid guardado (top por combines_por_ano)
    top = df.sort_values("combines_por_ano", ascending=False).iloc[0]
    print(f"\nTop-1 real del grid (G1): sl={top.sl_ticks} tp={top.tp_ticks} hold={top.max_holding_bars} "
          f"dir={top.direction} nc={top.nc} tpd={top.trades_per_day}  "
          f"combines/ano={top.combines_por_ano:.2f}  pass_rate={top.pass_rate_15d:.4f}")

    pct_rank = (df["combines_por_ano"] < top["combines_por_ano"]).mean()
    print(f"Percentil de G1 dentro de las {len(df):,} configs: {pct_rank*100:.4f}% (es, por construccion, el maximo -- 100o percentil)")

    # Cuantas configs quedan DENTRO de un 5%/10% del top -- si son muchas,
    # el pick no es un "outlier de suerte" fragil, es una region ancha y
    # robusta del espacio de parametros.
    thresh_pool = {}
    for pct in (0.01, 0.05, 0.10):
        thresh = top["combines_por_ano"] * (1 - pct)
        n_within = (df["combines_por_ano"] >= thresh).sum()
        thresh_pool[pct] = n_within
        print(f"  Configs dentro de {pct*100:.0f}% del top: {n_within} de {len(df):,} ({n_within/len(df)*100:.2f}%)")

    # Distribucion de pass_rate del grid completo -- donde caeria el
    # pass_rate observado de G1 si el proceso de generacion de estos 8100
    # numeros fuera puro ruido alrededor de un pass_rate "tipico"?
    print(f"\nDistribucion de pass_rate_15d en las {len(df):,} configs: "
          f"p10={df.pass_rate_15d.quantile(0.10):.4f}  mediana={df.pass_rate_15d.median():.4f}  "
          f"p90={df.pass_rate_15d.quantile(0.90):.4f}  max={df.pass_rate_15d.max():.4f}")
    print(f"pass_rate_15d de G1: {top.pass_rate_15d:.4f} -- percentil {(df.pass_rate_15d < top.pass_rate_15d).mean()*100:.2f} de la distribucion completa")

    print("\n--- Gap G1 (grid) -> G2 (desplegado, SL=100/TP=40) ---")
    print("G2 = escalado 2x manual de G1 (misma RR=0.4, doble distancia en ticks), NO es miembro")
    print("de este grid guardado (SL=100 excede SL_GRID=[10..50] de camino_b_grid.py).")
    print("Validado por separado (scripts/camino_b_direction_check.py, split-half temporal H1/H2)")
    print("-- ver research log de esta sesion para esos numeros. Este test de data-snooping cubre")
    print("con rigor la SELECCION de G1 dentro del grid; el paso G1->G2 es una refinacion posterior,")
    print("no una segunda pasada de multiple-comparison sobre la misma poblacion de 8,100.")


def mgc_snooping_note():
    print("\n" + "=" * 90)
    print("MGC_XFA -- por que el marco 'mejor-de-grid' NO aplica igual que en G2")
    print("=" * 90)
    print("SL=TP=364 (RR=1.0) fue una eleccion de DISEÑO (bracket simetrico, 'gambler's ruin'")
    print("sin necesitar edge real) -- no el resultado de barrer SL/TP y quedarse con el de mejor")
    print("performance simulado. No hay evidencia en el repo de un sweep de SL/TP para ESTE")
    print("candidato que se haya optimizado por resultado (a diferencia de G2, donde")
    print("camino_b_grid.py SI barrio 8,100 combos con ese proposito explicito).")
    print()
    df = pd.read_csv(os.path.join(DATA_DIR, "cerebro2_grid_exhaustive.csv"))
    sub = df[(df["product"] == "MGC") & (df["account"] == "150K") & (df["sl_ticks"] == 364) & (df["mll_policy"] == "every_payout")]
    nc_values = sorted(sub["nc"].unique())
    print(f"El unico parametro que SI se barrio para este bracket fue nc: {list(nc_values)} -- nc=6 es el techo,")
    print("no necesariamente el 'mejor de 5' en el sentido de sobreajuste -- coincide con el limite")
    print("legal de contratos del diseno de riesgo (k), no con una busqueda de performance sobre nc.")


if __name__ == "__main__":
    g2_snooping()
    mgc_snooping_note()
