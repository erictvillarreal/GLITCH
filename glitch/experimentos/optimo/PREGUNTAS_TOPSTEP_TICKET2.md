# Ticket a Topstep — versión corta para aplicar el finish-line y decidir tamaño (28-oct-2026)

Pega el bloque en inglés tal cual en Trader Support (una sola solicitud, preguntas numeradas) y guarda **número de ticket y fecha**; pégame la respuesta literal y fijo cada parámetro en el motor. Las preguntas 1–4 son las que **desbloquean el finish-line** y el tamaño adaptativo; 5–8 desbloquean 728×3 / más cuentas; 9–10 son de costos.

## Bloque para copiar (inglés)

> Hello Topstep Support. I trade Trading Combines and Express Funded Accounts with an automated strategy through the TopstepX/ProjectX API, from a personal device (no VPS/VPN), under one profile. Could you please answer the following in writing? Short factual answers are enough.
>
> **1. Position-size changes inside a Combine.** In a $50K Trading Combine my bot trades one position per day and *reduces the number of contracts as the account approaches the Profit Target* (for example, from 40 micros to a smaller size once one winning trade would be enough to reach the target), and uses a larger size when the account is far from the target. Is changing position size from one day to the next based on the account balance or the distance to the target allowed? Does it fall under any Prohibited Conduct or Responsible Trading Program (RTP) criterion? If yes, which one?
>
> **2. RTP measurable criteria.** What are the numeric thresholds and the time window used to flag "trading the maximum position size on a majority of trades", "losers larger than winners", "multiple accounts hitting the MLL on the same day" and "no stops"? Is a written warning always sent before any restriction (DLL, Consistency-only payout path)? If I am flagged, how do I get out of RTP?
>
> **3. Consistency rule in the Combine.** For the 55% rule in a $50K Combine: is it "best single day's profit must be below 55% of the Profit Target" or "below 55% of total profit at the time of passing"? Are losing days ignored when determining the best day, and is the day measured at 3:10 PM CT or at 4:00 PM CT?
>
> **4. Minimum days and passing mid-session.** Is there a minimum number of trading days to pass a Combine ("as few as two days"), and does a day count if I place a single trade? If my balance reaches the Profit Target in the middle of a session, is the Combine passed immediately or at the end of the day (Max Loss Limit is end-of-day vs. real-time)?
>
> **5. Brackets.** My strategy uses a fixed bracket on micro gold of 364 ticks stop and 364 ticks target (3 contracts) and, in some tests, 728/728. In the Combine on MES I use a 32-tick target with a 100-tick stop on up to 40 micros. Do these bracket sizes fall under "tight brackets" or any other Prohibited Trading Strategy? Is a stop distance larger than the Maximum Loss Limit allowed?
>
> **6. Multiple accounts, same signals.** May I run the same strategy and the same signals on several Combines/XFAs at the same time under one profile (separate accounts, orders sent from my personal device)? Is there a maximum number of simultaneous Combines and of active XFAs, and does copying the same trades across my own accounts count as account stacking or copy-trading?
>
> **7. Excessive purchases/resets.** I buy and reset Combines many times per year (roughly 40–55 per account per year, each after an MLL breach). Is there a threshold at which this is considered "excessive purchases of Trading Combines or Resets"? Would I receive a warning first?
>
> **8. Express Funded Account payout details.** For the Standard path on a $50K XFA: confirm (a) payout = 50% of balance, cap $2,000, minimum payout $125; (b) a "winning day" is ≥ $150 **net of commissions/fees**; (c) after the first payout the Maximum Loss Limit moves to $0 permanently; (d) the profit requirement for the second and later payouts ("profit since the last payout ≥ $0.01"). Is the day for winning-day and consistency purposes locked at 3:10 PM CT?
>
> **9. API billing.** Is the ProjectX/TopstepX API subscription ($14.50/month with the code) charged per profile or per active account? If charged per active account, is it paused when a Combine is closed/passed and before the XFA is activated?
>
> **10. Topstep Labs XFAs.** For the $250K Freedom Combine and the $25K/$50K Static Combines: what is the payout percentage and rule set of their Express Funded Accounts (payout as % of balance, minimum payout, Daily Loss Limit in the XFA, full scaling-plan table by balance)? Is "trading the full Maximum Loss Limit in one trade" acceptable under the Responsible Trading Advantage?

## Qué desbloquea cada respuesta

| # | Si la respuesta es… | Qué hago en el motor / el código |
|---|---|---|
| 1 | Permitido, sin criterio de RTP | Se aplica el finish-line (parche C1) y, si conviene, el tamaño óptimo por estado de la DP (`optimo/`); sube P(pasar) y baja el costo |
| 1 | Marcado por RTP | No se aplica; se usa tamaño fijo y se modela RTP (DLL + XFA Consistency) como escenario |
| 2 | Umbrales numéricos | Calibro el tamaño máximo y la frecuencia para no cruzarlos |
| 3–4 | Fórmula exacta / pase intradía | Ajusto el motor (hoy: mejor día ≤ 55 % del beneficio total, piso de cierre) y el momento óptimo de dejar de operar |
| 5 | Permitido | Evalúo 728×3 (+$512 a +$1,402 por cuenta y año) y brackets > MLL |
| 6–7 | Permitido / umbral | Habilita escalar cuentas y define cuántas compras al año |
| 8 | Confirma o corrige | Fija pago, día ganador neto, piso en $0 |
| 9 | Por cuenta activa / pausable | Recalculo OPS (hoy $245–640/año) |
| 10 | Reglas de Labs | Cierro o descarto el piloto del $250K |
