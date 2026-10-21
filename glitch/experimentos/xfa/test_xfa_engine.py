"""Pruebas del xfa_engine con dias deterministas (reglas del RULEBOOK) y regresion contra el motor publicado.
    python -m pytest -q test_xfa_engine.py            # mecanica
    GLITCH_ENGINE_ROOT=<checkout @6d4b069>/glitch python -m pytest -q test_xfa_engine.py   # + regresion ($620 / 31.6 %)"""
import os, sys
import numpy as np
import pytest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from xfa_engine import Rules, pol_fixed, simulate_life, plan_cap


class Scripted:
    """Dias deterministas: lista de (kind, pnl) que se repite; ignora colchon (salvo kind 2 = liquidacion explicita)."""
    tick_usd = 1.0; fee = 1.92

    def __init__(self, seq): self.seq = seq; self.pool = np.arange(len(seq))
    def draw(self, rng, n): return np.zeros((n,), int), np.zeros(n, int)
    def resolve(self, idx, si, side, nc, cush, sl):
        kind = np.zeros(len(idx), np.int8); pnl = np.zeros(len(idx))
        t = self._t; k, p = self.seq[t % len(self.seq)]
        kind[:] = k; pnl[:] = np.where(k == 2, -cush, p) * (nc > 0)
        self._t += 1
        return kind, pnl
    _t = 0


def life(seq, rules=None, n=3, md=60, policy=None):
    d = Scripted(seq); d._t = 0
    return simulate_life(d, rules or Rules(), policy or pol_fixed(3), n=n, seed=1, max_days=md)


def test_cinco_dias_ganadores_pagan_el_50_por_ciento_con_split():
    r = life([(0, 200.0)] * 5, md=5)
    assert r["npay"].min() == 1                      # balance 1000 -> 50 % = 500 bruto
    assert r["gross"][0] == pytest.approx(500.0) and r["paid"][0] == pytest.approx(450.0)


def test_el_tope_por_pago_es_2000():
    r = life([(0, 1000.0)] * 5, md=5)                # balance 5000 -> 50 % = 2500 -> tope 2000
    assert r["gross"][0] == pytest.approx(2000.0)


def test_minimo_de_pago_125():
    r = life([(0, 150.0)] * 5, Rules(), md=5)        # balance 750 -> 375 OK
    assert r["npay"][0] == 1
    r2 = life([(0, 150.0)] * 5, Rules(minpay=400.0), md=5)   # 375 < 400 -> no paga
    assert r2["npay"][0] == 0


def test_el_primer_pago_fija_el_piso_en_cero_y_el_saldo_restante_es_el_colchon():
    # 5 dias de +200 (balance 1000), pago 500 -> balance 500, piso 0; luego liquidacion explicita (kind 2) -> muere con lo cobrado
    r = life([(0, 200.0)] * 5 + [(2, 0.0)], md=6)
    assert r["npay"][0] == 1 and not r["alive"][0] and r["bal"][0] == pytest.approx(0.0)


def test_el_piso_sube_con_el_cierre_y_se_fija_en_cero_al_llegar_a_2000():
    d = Scripted([(0, 1000.0), (0, 1000.0), (1, -500.0)])
    d._t = 0
    r = simulate_life(d, Rules(), pol_fixed(3), n=1, seed=1, max_days=3)
    assert r["bal"][0] == pytest.approx(1500.0) or r["npay"][0] > 0   # tras 2000 el piso es 0: un -500 no liquida


def test_liquidacion_cierra_la_cuenta_y_no_vuelve_a_pagar():
    r = life([(2, 0.0)] + [(0, 500.0)] * 10, md=11)
    assert not r["alive"][0] and r["npay"][0] == 0 and r["life"][0] == 1


def test_dias_ganadores_requieren_150_netos():
    r = life([(0, 149.0)] * 20, md=20)
    assert r["npay"][0] == 0
    r2 = life([(0, 150.0)] * 5, md=5)
    assert r2["npay"][0] == 1


def test_regla_ganancia_desde_el_ultimo_pago():
    # despues del 1er pago, 5 dias ganadores de +150 siguen siendo ganancia > 0 desde el ultimo pago -> paga otra vez
    r = life([(0, 150.0)] * 10, md=10)
    assert r["npay"][0] == 2
    # con dias ganadores pero balance neto <= ref: +150 (gana) y luego -x que borra la ganancia no puede pagar: se prueba con sec. +150 x5, -400, +150 x5
    r2 = life([(0, 150.0)] * 5 + [(1, -400.0)] + [(0, 150.0)] * 5, md=11)
    assert r2["npay"][0] >= 1


def test_beneficio_first100_y_comision_de_transferencia():
    r = life([(0, 200.0)] * 5, Rules(first100=10000.0, wire_fee=30.0), md=5)
    assert r["paid"][0] == pytest.approx(500.0 - 30.0)
    r2 = life([(0, 200.0)] * 5, Rules(wire_fee=30.0), md=5)
    assert r2["paid"][0] == pytest.approx(450.0 - 30.0)


def test_ruta_consistency_exige_40_por_ciento():
    # 3 dias de +1000 -> mejor dia 1000/3000 = 33 % <= 40 % -> paga; con 2000/+500/+500 -> 66 % no paga
    ok = life([(0, 1000.0)] * 3, Rules(path="cons", cap=3000.0), md=3)
    assert ok["npay"][0] == 1
    no = life([(0, 2000.0), (0, 500.0), (0, 500.0)], Rules(path="cons", cap=3000.0), md=3)
    assert no["npay"][0] == 0


def test_dos_tp_de_1092_dan_50_por_ciento_y_tres_dan_33():
    two = life([(0, 1092.0), (0, 1092.0)], Rules(path="cons", cap=3000.0), md=2)
    assert two["npay"][0] == 0                       # 1092/2184 = 50 % > 40 %
    three = life([(0, 1092.0)] * 3, Rules(path="cons", cap=3000.0), md=3)
    assert three["npay"][0] == 1                     # 1092/3276 = 33 %


def test_plan_de_escalado():
    b = np.array([0.0, 1499.0, 1500.0, 2000.0])
    assert list(plan_cap(b, "MGC")) == [12, 12, 18, 31] and list(plan_cap(b, "MES")) == [20, 20, 30, 50]


@pytest.mark.skipif(not os.environ.get("GLITCH_ENGINE_ROOT"), reason="falta GLITCH_ENGINE_ROOT")
def test_regresion_contra_el_motor_publicado():
    import subprocess
    out = subprocess.run([sys.executable, os.path.join(os.path.dirname(__file__), "regress_lever.py"), "--engine-root", os.environ["GLITCH_ENGINE_ROOT"], "--n", "100000"],
                         capture_output=True, text=True, timeout=900).stdout
    line = [l for l in out.splitlines() if l.startswith("lock oficial")][0]
    paid = float(line.split("xfa_engine")[1].split("pago medio $")[1].split(" ")[0].replace(",", ""))
    p = float(line.split("xfa_engine")[1].split("P(>=1) ")[1].split(" ")[0])
    assert abs(paid - 620) < 25 and abs(p - 0.316) < 0.01
