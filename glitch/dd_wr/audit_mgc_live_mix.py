"""
Solo LECTURA de geometry_mgc_log.json (Gist real). Requiere GITHUB_GIST_TOKEN y GIST_ID
(los corre el usuario). Reporta la mezcla real TP/SL/FLATTEN de Cerebro 2, el WR condicional
(la convencion del Telegram: TP/(TP+SL), excluye FLATTEN), y la compara contra el bar-walk
de backtest (T3 reciente 23.8%, historico 2 años, promedio 51%) con un test binomial exacto.
"""
import os, sys
from math import comb
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from execution.gist_store import load_log

LOG = "geometry_mgc_log.json"
REF = {"T3 reciente (23.8%)": 0.238, "ultimos 120d (27.5%)": 0.275, "2 años promedio (50.9%)": 0.509, "T1 (78.4%)": 0.784}


def binom_two_sided(k, n, p):
    pk = comb(n, k) * p**k * (1 - p)**(n - k)
    return sum(comb(n, i) * p**i * (1 - p)**(n - i) for i in range(n + 1)
               if comb(n, i) * p**i * (1 - p)**(n - i) <= pk + 1e-15)


def main():
    log = load_log(LOG)
    res = [e for e in log if e.get("result") in ("TP", "SL", "FLATTEN")]
    rec = [e for e in log if e.get("result") == "RECONCILED"]
    n = len(res)
    print(f"Entradas: {len(log)} | resueltas TP/SL/FLATTEN: {n} | RECONCILED (excluidas): {len(rec)}")
    for e in sorted(res, key=lambda x: x.get("date", "")):
        print(f"  {e.get('date')} {e.get('direction')} {e.get('result'):8s} pnl={e.get('pnl')} intento={e.get('intento')}")
    tp = sum(e["result"] == "TP" for e in res); sl = sum(e["result"] == "SL" for e in res); fl = sum(e["result"] == "FLATTEN" for e in res)
    print(f"\nMezcla: TP={tp} SL={sl} FLATTEN={fl}  (FLATTEN share {fl/n:.1%})" if n else "sin datos")
    if tp + sl:
        print(f"WR condicional TP/(TP+SL) = {tp/(tp+sl):.3f} (n={tp+sl})  <- convencion del Telegram (_paper_progress)")
    print(f"WR incondicional TP/total = {tp/n:.3f}" if n else "")
    pnls = [e.get("pnl", 0) for e in res]
    if n:
        fl_p = [e.get("pnl", 0) for e in res if e["result"] == "FLATTEN"]
        print(f"PnL total=${sum(pnls):,.0f} medio/trade=${sum(pnls)/n:,.0f} | backtest RR=1: -$54 (2 años), FLATTEN medio backtest +$13..+$112")
        if fl_p: print(f"PnL medio de FLATTEN en vivo=${sum(fl_p)/len(fl_p):,.0f}")
        print(f"dias con pnl>=+150: {sum(p>=150 for p in pnls)}/{n} (backtest 46%) | pnl<=-2000: {sum(p<=-2000 for p in pnls)}/{n} (backtest 26%)")
        print("\nTest binomial exacto (dos colas) del FLATTEN share observado vs cada referencia de backtest:")
        for k, p in REF.items():
            print(f"  vs {k}: p={binom_two_sided(fl, n, p):.3f}")
        print("(con n<20 estos tests casi nunca rechazan nada: son evidencia debil, no confirmacion)")


if __name__ == "__main__":
    main()
