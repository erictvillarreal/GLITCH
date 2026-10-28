"""Topstep Labs (28-oct-2026): motor rápido para modelar los retos con el GLITCH. NO es producción; MODELADO.
Reutiliza BarDays/simulate_life de xfa_engine (días reales de 5 min). Añade `chal_life`: etapa Combine/Challenge con MLL estático o de cierre (trailing EOD),
límite diario (DLL), consistencia, objetivo y vencimiento, y la calibración de deriva por producto."""
import os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
for p in (os.path.join(HERE, "..", "xfa"), os.path.join(HERE, "..", "preservacion")):
    sys.path.insert(0, p)
from daydata import DayData, sim_day
from xfa_engine import BarDays, Policy, Rules, simulate_life


def chal_life(days, n, seed, target, mll, tick_usd, fee, sl, nc_of, trailing=False, dll=None, consist=0.55, max_days=63, min_days=2):
    """Etapa de reto/Combine hasta pasar, liquidarse (toca el piso) o vencer (max_days hábiles ≈ 90 días naturales).
    nc_of(bal, floor, need) -> contratos por trayectoria. Devuelve dict(passed, fail_liq, days, bal)."""
    rng = np.random.default_rng(seed)
    bal = np.zeros(n); peak = np.zeros(n); floor = np.full(n, -float(mll)); best = np.zeros(n)
    alive = np.ones(n, bool); passed = np.zeros(n, bool); liqd = np.zeros(n, bool); tdays = np.zeros(n, int); dused = np.zeros(n, int)
    par0 = rng.integers(0, 2, n)
    for t in range(max_days):
        a = alive & ~passed
        if not a.any(): break
        side = np.where((par0 + t) % 2 == 0, 1, -1)
        tgt = np.maximum(target, best / consist) if consist else np.full(n, float(target))
        need = np.maximum(tgt - bal, 0.0)
        nc = np.where(a, nc_of(bal, floor, need), 0).astype(int)
        slv = np.full(n, int(sl))
        if dll is not None:
            slv = np.minimum(slv, np.maximum(np.floor((dll - fee * nc) / (np.maximum(nc, 1) * tick_usd)), 1)).astype(int)
        idx, si = days.draw(rng, n)
        kind, pnl = days.resolve(idx, si, side, nc, np.maximum(bal - floor, 0.0), slv)
        traded = a & (nc > 0)
        liq = traded & (kind == 2); ok = a & ~liq
        bal = np.where(ok, bal + pnl, bal); bal = np.where(liq, floor, bal)
        best = np.where(ok & traded, np.maximum(best, pnl), best)
        tdays += traded
        peak = np.where(ok, np.maximum(peak, bal), peak)
        if trailing:
            floor = np.where(ok, np.maximum(floor, np.minimum(peak - mll, 0.0)), floor)
        tgt2 = np.maximum(target, best / consist) if consist else np.full(n, float(target))
        reached = ok & traded & (bal >= tgt2 - 1e-9) & (tdays >= min_days)
        dused = np.where(a, t + 1, dused)
        passed |= reached; liqd |= liq; alive = alive & ~liq
    return dict(passed=passed, fail_liq=liqd, days=dused, bal=bal)


def calib_drift(dd, wr, half_ticks, lo=-60.0, hi=60.0):
    """Deriva (ticks/día a favor del lado) que da WR = TP/(TP+SL) = wr en el bracket nominal simétrico `half_ticks`, 1 contrato, sin comisión ni MLL (como la etiqueta de H1)."""
    def w(dr):
        t = s = 0.0
        for side in (1, -1):
            k, _ = sim_day(dd, side, 1, 1e9, slip=0.0, sl=half_ticks, tp=half_ticks, fee=0.0, tick_usd=1.0, drift=dr)
            t += (k == 0).mean(); s += ((k == 1) | (k == 2)).mean()
        return t / max(t + s, 1e-12)
    if abs(wr - 0.5) < 1e-9: return 0.0
    a, b = lo, hi
    for _ in range(40):
        m = 0.5 * (a + b)
        if w(m) < wr: a = m
        else: b = m
    return 0.5 * (a + b)


def fixed_nc(nc):
    return lambda bal, floor, need: np.full(bal.shape, int(nc))
