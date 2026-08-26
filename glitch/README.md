# Proyecto Glitch — Quantitative Prop Firm Engine

> *"You do not need a winning market strategy. You need a strategy optimised for the geometry of the payout system."*

---

## Overview

Glitch is a quantitative engine for maximising **expected value across prop firm challenge attempts** by exploiting the structural **convex payoff asymmetry** of funded trading accounts.

- **Loss is capped** at the challenge fee (fixed premium)
- **Upside is uncapped** relative to cost basis
- The goal is not market prediction — it is **risk geometry optimisation**

This is modelled as a call option structure: pay a fixed premium, receive scalable upside if the option expires in-the-money (challenge passed).

---

## Architecture

```
glitch/
├── core/
│   ├── prop_firm.py        # PropFirmConfig — all firm rules as typed dataclasses
│   └── account.py          # AccountState — state machine with hard constraint enforcement
├── simulation/
│   ├── monte_carlo.py      # Vectorised Monte Carlo simulator (10k paths < 1s)
│   └── optimizer.py        # Grid search over (WR × RR × risk%) parameter space
├── risk/
│   └── geometry.py         # Kelly criterion, position sizing, drawdown analytics
├── strategies/             # Strategy implementations (ORB, mean-reversion, scalp)
├── brokers/                # Broker API adapters (MT5, cTrader, Rithmic)
├── tests/
│   └── test_core.py        # 38 tests — 100% passing
├── notebooks/              # Research notebooks
└── configs/                # YAML firm configs
```

---

## Two Challenges

### Challenge 1 — Maximise P(pass challenge)
- High win-rate, low variance, controlled drawdown exposure
- Strategy geometry matches the constraint boundaries of the firm
- Tested via Monte Carlo with 10k–50k paths per configuration

### Challenge 2 — Maximise net realised EV post-funding
- Strategy shift in funded phase: higher RR tolerance, payout extraction logic
- System-level EV = P(pass) × E[payout | funded] − challenge_cost

---

## Supported Firms

| Firm | Account Size | Challenge Fee | Phase 1 Target | Max DD |
|------|-------------|---------------|----------------|--------|
| FTMO | $100k | $540 | 10% | 10% |
| MyForexFunds | $100k | $299 | 8% | 12% |
| Apex Trader | $50k | $222 | 6% | 3% |
| The Funded Trader | $100k | $499 | 10% | 10% |

---

## Quick Start

```bash
pip install -r requirements.txt
pytest tests/ -v
```

```python
from core.prop_firm import load_firm
from simulation.monte_carlo import MonteCarloSimulator, StrategyParams

firm = load_firm("ftmo_100k")
strategy = StrategyParams(
    win_rate=0.65,
    rr=1.5,
    risk_per_trade_pct=0.006,
    trades_per_day=3,
)
sim = MonteCarloSimulator(firm, strategy, n_paths=20_000)
results = sim.run()
print(results.summary())
```

---

## Grid Search — Finding Optimal Parameters

```python
from simulation.optimizer import GridSearchOptimizer
from core.prop_firm import load_firm

firm = load_firm("ftmo_100k")
opt = GridSearchOptimizer(firm, n_paths=5000)
df = opt.run()
print(opt.top_n(df, 10))
```

---

## Key Quantitative Insight

At zero expected value (EV = 0 per trade), pass rates differ dramatically by strategy geometry:

| Win Rate | RR | Risk/Trade | P(Pass Phase 1) |
|----------|-----|------------|-----------------|
| 25% | 3.0 | 0.5% | ~8% |
| 40% | 1.5 | 0.5% | ~22% |
| 65% | 1.5 | 0.6% | ~95%+ |
| 75% | 0.33 | 0.5% | ~0% (can't reach target) |

**Variance reduction, not alpha, determines challenge pass rate.**

---

## Statistical Validation Standards

All results reported with:
- Wilson score confidence intervals (95%)
- Minimum 10,000 Monte Carlo paths
- Walk-forward out-of-sample validation
- Sharpe ratio, max drawdown, profit factor

---

## Roadmap

- [x] Core prop firm rules engine
- [x] Account state machine
- [x] Monte Carlo simulator
- [x] Risk geometry / Kelly sizing
- [x] Grid search optimizer
- [x] Full test suite (38 tests)
- [ ] Strategy implementations (ORB, VWAP, scalp)
- [ ] Broker API adapters (MT5 / cTrader)
- [ ] Live monitoring dashboard
- [ ] Payout extraction logic
- [ ] Multi-account portfolio manager
- [ ] GitHub Actions CI/CD pipeline


## DeviceId generado: 9818ba62-27d2-418f-837e-14af70314cad