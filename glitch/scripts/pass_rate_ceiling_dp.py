"""
Techo teorico del pass rate de un Combine para CUALQUIER estrategia sin edge (juego justo), por programacion dinamica.

Pregunta que responde: "si el precio es un juego justo (martingala), cual es la MAXIMA probabilidad de pasar que puede lograr
cualquier politica de tamano/brackets, bajo las reglas del Combine?". Es una cota superior: ninguna geometria, producto,
timeframe o estructura de payoff (futuros, opciones, cripto) puede superarla SIN edge/prima de riesgo, porque las ganancias
esperadas de una martingala son cero (teorema de parada opcional) y las reglas solo definen las barreras.

Estado: balance b, maximo EOD m (acotado a D; el piso = m-D hasta que m>=D, luego 0), mejor dia 'best' (consistencia), dia d.
Accion de cada dia: elegir CUALQUIER distribucion de P&L del dia con media -c (c=costo) y soporte >= -L (L = distancia al piso;
tocar el piso = liquidacion = perdida). Eso es la envolvente concava del valor siguiente evaluada en -c.
Modo 'bracket' (con edge): solo brackets de dos puntos (stop S, target G) con prob. de ganar p = S/(S+G) + edge.

Simplificaciones declaradas: el trailing se actualiza al cierre del dia (como Topstep: "updates at end of each trading day but
monitored in real time"); un dia sin operar cuenta como dia; el balance/best se discretizan en pasos h; Delta_max = T.
NO es una simulacion de precios: es la cota del juego. Para tocar datos reales ver pass_rate_bold_real.py.
"""
import sys
import numpy as np
from numba import njit


@njit(cache=True)
def _hull_eval(xs, gs, n, x0):
    # xs creciente. Envolvente concava superior evaluada en x0 (cadena monotona).
    hx = np.empty(n); hg = np.empty(n); k = 0
    for i in range(n):
        while k >= 2:
            # quitar el punto k-1 si queda por debajo del segmento (k-2 -> i)
            cr = (hx[k-1]-hx[k-2])*(gs[i]-hg[k-2]) - (hg[k-1]-hg[k-2])*(xs[i]-hx[k-2])
            if cr >= 0: k -= 1
            else: break
        hx[k] = xs[i]; hg[k] = gs[i]; k += 1
    if x0 <= hx[0]: return hg[0]
    if x0 >= hx[k-1]: return hg[k-1]
    for j in range(k-1):
        if hx[j] <= x0 <= hx[j+1]:
            w = (x0-hx[j])/(hx[j+1]-hx[j]) if hx[j+1] > hx[j] else 0.0
            return hg[j]*(1-w)+hg[j+1]*w
    return 0.0


@njit(cache=True)
def _nxt(V, d, max_days, nb_lo, nb, nm, nbest, Tn, cons, min_days, b, m, ibest, dk, static):
    """Valor del estado siguiente si el P&L del dia es dk pasos (dk>0 gana, dk<0 pierde sin tocar el piso)."""
    bn = b + dk
    mn = m
    if bn > m and not static:
        mn = min(bn, nm - 1)
    bst = max(ibest, min(max(dk, 0), nbest - 1))
    if cons > 0:
        need = max(Tn, int(np.ceil(max(ibest, dk) / cons - 1e-9)))
    else:
        need = Tn
    if bn >= need and d + 1 >= min_days:
        return 1.0
    if d + 1 >= max_days:
        return 0.0
    bi = bn - nb_lo
    if bi >= nb: bi = nb - 1
    return V[d + 1, bi, mn, bst]


@njit(cache=True)
def solve(D, T, h, cons, min_days, max_days, cost, dll, mode, edge, static):
    nb_lo = -int(round(D / h)); nb_hi = int(round(2 * T / h))
    nb = nb_hi - nb_lo + 1
    nm = int(round(D / h)) + 1
    nbest = int(round(T / h)) + 1
    Tn = int(round(T / h))
    cs = int(round(cost / h))
    dll_n = int(dll / h) if dll > 0 else 0
    V = np.zeros((max_days + 1, nb, nm, nbest))
    xs = np.empty(nb + Tn + 4); gs = np.empty(nb + Tn + 4)
    for d in range(max_days - 1, -1, -1):
        for m in range(nm):
            fl = m - (nm - 1)                     # piso en pasos h; m=nm-1 => piso 0 (trabado)
            for ibest in range(nbest):
                for ib in range(nb):
                    b = ib + nb_lo
                    if (not static) and m < max(b, 0) and m < nm - 1: continue     # estado imposible
                    Lg = b - fl
                    if Lg <= 0: continue
                    Lc = Lg; soft = False
                    if dll_n > 0 and Lg > dll_n:
                        Lc = dll_n; soft = True
                    best_v = 0.0
                    if mode == 0:
                        n = 0
                        for dk in range(-Lc, Tn + 1):
                            if dk == -Lc and not soft:
                                g = 0.0
                            elif dk == -Lc and soft:
                                g = _nxt(V, d, max_days, nb_lo, nb, nm, nbest, Tn, cons, min_days, b, m, ibest, dk, static)
                            else:
                                g = _nxt(V, d, max_days, nb_lo, nb, nm, nbest, Tn, cons, min_days, b, m, ibest, dk, static)
                            xs[n] = dk * h; gs[n] = g; n += 1
                        best_v = _hull_eval(xs, gs, n, -cost)
                    else:
                        for S in range(1, Lc + 1):
                            sl = S + cs
                            if sl > Lc: break
                            for G in range(1, Tn + 1):
                                gw_steps = G - cs
                                p = S / (S + G) + edge
                                if p > 1.0: p = 1.0
                                gw = _nxt(V, d, max_days, nb_lo, nb, nm, nbest, Tn, cons, min_days, b, m, ibest, gw_steps, static)
                                if sl >= Lg and not (soft):
                                    gl = 0.0
                                else:
                                    gl = _nxt(V, d, max_days, nb_lo, nb, nm, nbest, Tn, cons, min_days, b, m, ibest, -sl, static)
                                v = p * gw + (1.0 - p) * gl
                                if v > best_v: best_v = v
                    V[d, ib, m, ibest] = best_v
    return V[0, 0 - nb_lo, 0, 0]


def ceiling(D, T, cons=0.55, min_days=2, max_days=20, cost=0.0, dll=0.0, mode=0, edge=0.0, h=None, static=False):
    h = h or D / 40
    return solve(float(D), float(T), float(h), float(cons or 0.0), int(min_days), int(max_days), float(cost), float(dll),
                 int(mode), float(edge), bool(static))


if __name__ == "__main__":
    print("Techo de juego justo (cualquier politica, sin edge, sin costos), max_days=20")
    for name, D, T, cons, md in (("Topstep 50K  (MLL2000 T3000 cons55% min2d)", 2000, 3000, 0.55, 2),
                                 ("Topstep 100K (MLL3000 T6000 cons55% min2d)", 3000, 6000, 0.55, 2),
                                 ("Topstep 150K (MLL4500 T9000 cons55% min2d)", 4500, 9000, 0.55, 2)):
        print(f"  {name}: {ceiling(D, T, cons, md):.4f}")
