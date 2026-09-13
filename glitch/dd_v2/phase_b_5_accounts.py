"""
DD v2 -- Fase B: proyeccion de NEGOCIO (no de robustez estadistica) de
5 cuentas XFA/MGC_XFA_150K simultaneas, mismo motor de 2 etapas ya
validado (scripts/cerebro2_cashflow_monte_carlo.py), extendido de 1 a
5 cuentas. ETIQUETADO EXPLICITO: esto es PROYECCION, no resultado
confirmado -- nunca reportar un promedio lineal como numero principal.

HALLAZGO ARQUITECTONICO QUE DETERMINA EL DISEÑO DE ESTE SCRIPT (ver
GLITCH_RESEARCH_LOG.md): strategies/geometry_pure.py::decide_side() es
una funcion PURA de trading_day_index(fecha) -- NO hay ninguna fuente
de aleatoriedad por cuenta. Si 5 cuentas reales corren la MISMA
geometria sobre el MISMO producto (MGC) el MISMO dia, las 5 abren el
MISMO lado, contra el MISMO precio de mercado -- estan, en la
practica, replicando el MISMO trade 5 veces, no 5 apuestas
independientes. Por eso este script reporta DOS escenarios,
etiquetados sin ambiguedad:

  (a) CORRELACIONADO (realista, dado el codigo real): las 5 cuentas
      comparten el MISMO resultado dia a dia (mismo evento de
      Combine, mismo episodio de XFA) -- el "diversificador" que se
      pierde es CERO. Equivalente a simular 1 cuenta y multiplicar
      por 5 -- pero se simula explicitamente igual, no se asume el
      atajo algebraico, para poder reportar tambien el colchon de
      capital con el mismo pipeline.
  (b) INDEPENDIENTE (NO realista para este diseño -- se reporta como
      referencia/cota superior de que TANTO se estaria sobre-
      estimando el beneficio de diversificacion si se asumiera sin
      evidencia, exactamente el error que el usuario pidio explicitamente
      no cometer).

WR=0.50 (mismo que scripts/cerebro2_cashflow_monte_carlo.py -- el gap
de WR encontrado el 13-sep-2026 resulto ser un bug de medicion de esta
sesion, no una discrepancia real, ver research log -- 0.4940 real y
0.5020 denso son estadisticamente indistinguibles, se mantiene el 0.50
ya validado para comparabilidad directa con el numero de negocio ya
publicado, $31,257 mediana a 1 cuenta).
"""
from __future__ import annotations
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np

from scripts.cerebro2_cashflow_monte_carlo import build_combine_pool, build_xfa_pool, percentile_table

N_ACCOUNTS = 5
N_TRAJECTORIES = 20_000
HORIZON_DAYS = 365
SEED = 7


def run_correlated(combine_pool, xfa_pool, n_accounts=N_ACCOUNTS, n_trajectories=N_TRAJECTORIES,
                    horizon_days=HORIZON_DAYS, seed=SEED):
    """Las n_accounts cuentas comparten CADA evento (mismo pass/fail de
    Combine, mismo episodio de XFA si pasan) -- una sola secuencia de
    aleatoriedad por trayectoria, aplicada identica a las n_accounts."""
    rng = np.random.default_rng(seed)
    n_pass_pool, n_blown_pool = len(combine_pool["pass_days_pool"]), len(combine_pool["blown_days_pool"])
    n_xfa_pool = len(xfa_pool["payout_usd_pool"])
    fee_monthly, fee_activation = combine_pool["fee_monthly"], combine_pool["fee_activation"]
    pass_rate = combine_pool["pass_rate"]

    total_payouts, min_cash_l = [], []
    for _ in range(n_trajectories):
        days_elapsed, cash_per_account, min_cash_total = 0.0, 0.0, 0.0
        total_payout_per_account = 0.0

        while days_elapsed < horizon_days:
            cash_per_account -= fee_monthly
            min_cash_total = min(min_cash_total, cash_per_account * n_accounts)

            passed = rng.random() < pass_rate
            if passed:
                days = combine_pool["pass_days_pool"][rng.integers(0, n_pass_pool)]
            else:
                days = combine_pool["blown_days_pool"][rng.integers(0, n_blown_pool)]
            days_elapsed += days

            if passed:
                cash_per_account -= fee_activation
                min_cash_total = min(min_cash_total, cash_per_account * n_accounts)
                idx = rng.integers(0, n_xfa_pool)
                episode_payout = xfa_pool["payout_usd_pool"][idx]
                episode_days = xfa_pool["days_pool"][idx]
                days_elapsed += episode_days
                cash_per_account += episode_payout
                total_payout_per_account += episode_payout

        total_payouts.append(total_payout_per_account * n_accounts)  # las 5 ganan/pierden igual, mismo evento
        min_cash_l.append(-min_cash_total)

    return {"total_payout": np.array(total_payouts), "capital_colchon": np.array(min_cash_l)}


def _account_event_trace(combine_pool, xfa_pool, rng, horizon_days):
    """Genera la traza (dia_del_evento, cash_acumulado_DESPUES_del_evento)
    de UNA cuenta independiente -- misma logica que run_correlated pero
    para una sola cuenta, devolviendo CADA punto donde el cash cambia
    (no solo el total final) para poder fusionar cronologicamente con
    las otras 4 cuentas y trackear el minimo CONJUNTO real."""
    n_pass_pool, n_blown_pool = len(combine_pool["pass_days_pool"]), len(combine_pool["blown_days_pool"])
    n_xfa_pool = len(xfa_pool["payout_usd_pool"])
    fee_monthly, fee_activation = combine_pool["fee_monthly"], combine_pool["fee_activation"]
    pass_rate = combine_pool["pass_rate"]

    days_elapsed, cash, total_payout = 0.0, 0.0, 0.0
    trace = []
    while days_elapsed < horizon_days:
        cash -= fee_monthly
        trace.append((days_elapsed, cash))
        passed = rng.random() < pass_rate
        if passed:
            days = combine_pool["pass_days_pool"][rng.integers(0, n_pass_pool)]
        else:
            days = combine_pool["blown_days_pool"][rng.integers(0, n_blown_pool)]
        days_elapsed += days

        if passed:
            cash -= fee_activation
            trace.append((days_elapsed, cash))
            idx = rng.integers(0, n_xfa_pool)
            episode_payout = xfa_pool["payout_usd_pool"][idx]
            episode_days = xfa_pool["days_pool"][idx]
            days_elapsed += episode_days
            cash += episode_payout
            total_payout += episode_payout
            trace.append((days_elapsed, cash))
    return trace, total_payout


def run_independent(combine_pool, xfa_pool, n_accounts=N_ACCOUNTS, n_trajectories=N_TRAJECTORIES,
                     horizon_days=HORIZON_DAYS, seed=SEED):
    """Cada una de las n_accounts cuentas dibuja su PROPIA secuencia de
    eventos, independiente de las demas -- el supuesto que el usuario
    pidio explicitamente NO asumir sin evidencia. Se reporta como
    referencia/cota superior, no como el escenario primario.

    Colchon CONJUNTO calculado correctamente: se fusionan cronologicamente
    los eventos de las n_accounts cuentas y se trackea el minimo de la
    SUMA de cash a traves del tiempo -- no solo el cash final (ese enfoque,
    usado en un borrador anterior de este script, subestimaba el colchon
    real al ignorar caidas intermedias que se recuperan antes del dia 365)."""
    rng = np.random.default_rng(seed)
    total_payouts, min_cash_l = [], []

    for _ in range(n_trajectories):
        last_cash = np.zeros(n_accounts)
        events = []  # (dia, indice_cuenta, cash_nuevo)
        total_payout_sum = 0.0
        for a in range(n_accounts):
            trace, total_payout_a = _account_event_trace(combine_pool, xfa_pool, rng, horizon_days)
            for day, cash in trace:
                events.append((day, a, cash))
            total_payout_sum += total_payout_a

        events.sort(key=lambda e: e[0])
        running_min = 0.0
        for day, a, cash in events:
            last_cash[a] = cash
            running_min = min(running_min, last_cash.sum())

        total_payouts.append(total_payout_sum)  # payout BRUTO, mismo criterio que run_correlated/cerebro2_cashflow_monte_carlo.py
        min_cash_l.append(-running_min)

    return {"total_payout": np.array(total_payouts), "capital_colchon": np.array(min_cash_l)}


if __name__ == "__main__":
    print("Construyendo pools (Combine + XFA, mismo motor ya validado)...")
    combine_pool = build_combine_pool()
    xfa_pool = build_xfa_pool("every_payout")

    print(f"\n{'='*100}\nESCENARIO (a) CORRELACIONADO -- realista dado que decide_side() es deterministico por calendario\n{'='*100}")
    corr = run_correlated(combine_pool, xfa_pool)
    percentile_table(corr["total_payout"], "Payout TOTAL combinado, 5 cuentas ($)")
    percentile_table(corr["capital_colchon"], "Capital colchon conjunto necesario ($)")
    print(f"Mediana / 1 cuenta implicita: ${np.median(corr['total_payout'])/N_ACCOUNTS:,.0f}  "
          f"(referencia: $31,257 ya publicado para 1 cuenta)")

    print(f"\n{'='*100}\nESCENARIO (b) INDEPENDIENTE -- NO realista, cota superior de diversificacion (referencia, no recomendacion)\n{'='*100}")
    indep = run_independent(combine_pool, xfa_pool)
    percentile_table(indep["total_payout"], "Payout TOTAL combinado, 5 cuentas ($)")
    percentile_table(indep["capital_colchon"], "Capital colchon conjunto necesario ($)")

    print(f"\n{'='*100}\nCOMPARACION\n{'='*100}")
    print(f"Mediana payout total, correlacionado: ${np.median(corr['total_payout']):,.0f}")
    print(f"Mediana payout total, independiente:  ${np.median(indep['total_payout']):,.0f}")
    print(f"Mediana colchon, correlacionado: ${np.median(corr['capital_colchon']):,.0f}  "
          f"(={np.median(corr['capital_colchon'])/np.median(corr['capital_colchon'])*5:.1f}x de referencia)")
    print(f"p90 colchon, correlacionado: ${np.percentile(corr['capital_colchon'], 90):,.0f}")
    print(f"p90 colchon, independiente:  ${np.percentile(indep['capital_colchon'], 90):,.0f}")
