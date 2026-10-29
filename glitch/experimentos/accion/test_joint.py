"""Pruebas de JointDays con proveedores falsos (sin datos)."""
import os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import types
H = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [os.path.join(H, '..', 'xfa'), os.path.join(H, '..', 'preservacion')]
sys.modules.setdefault("accion_lib", types.ModuleType("accion_lib"))
lib = sys.modules["accion_lib"]
for k in ("provider", "SPEC", "drift_of", "pay_fn", "TR", "TE", "WRS", "EMP8", "EMP8_P", "N_SEL", "N_REP", "B", "blocks", "t0"):
    setattr(lib, k, None)
import xfa_joint as j


class Fake:
    def __init__(self, kind, pnl): self.kind, self.pnl, self.calls = kind, pnl, []
    slips = (0.0,); slip_p = np.array([1.0])
    def resolve(self, idx, si, side, nc, cush, sl):
        self.calls.append((nc.copy(), cush.copy(), sl.copy()))
        n = len(idx); return np.full(n, self.kind, np.int8), np.where(nc > 0, self.pnl, 0.0)


def mk(A, B): return j.JointDays(A, B, np.arange(10), np.arange(10), 1.0, 2.0)


def test_codec_and_sum_of_pnl():
    d = mk(Fake(3, 100.0), Fake(3, 50.0)); k, p = d.resolve(np.zeros(4, int), np.zeros(4, int), np.ones(4, int), np.full(4, 3 * 1000 + 8), np.full(4, 2000.0), np.full(4, 364 * 10000 + 80))
    assert (p == 150.0).all() and (k == 3).all()
    assert (d.A.calls[0][0] == 3).all() and (d.B.calls[0][0] == 8).all() and (d.A.calls[0][2] == 364).all() and (d.B.calls[0][2] == 80).all()


def test_second_trade_sees_a_reduced_cushion():
    d = mk(Fake(3, 0.0), Fake(3, 0.0)); d.resolve(np.zeros(1, int), np.zeros(1, int), np.ones(1, int), np.array([3 * 1000 + 8]), np.array([2000.0]), np.array([364 * 10000 + 80]))
    assert abs(d.B.calls[0][1][0] - (2000.0 - 364 * 3 * 1.0 - 2.0 * 3)) < 1e-9


def test_liquidation_in_either_leg_kills_the_day():
    for ka, kb in ((2, 3), (3, 2), (2, 2)):
        d = mk(Fake(ka, 10.0), Fake(kb, 10.0)); k, p = d.resolve(np.zeros(1, int), np.zeros(1, int), np.ones(1, int), np.array([1008]), np.array([2000.0]), np.array([364 * 10000 + 80]))
        assert k[0] == 2 and p[0] == 0.0


def test_no_second_leg_when_ncB_is_zero():
    d = mk(Fake(3, 100.0), Fake(3, 50.0)); k, p = d.resolve(np.zeros(1, int), np.zeros(1, int), np.ones(1, int), np.array([3000]), np.array([2000.0]), np.array([364 * 10000 + 1]))
    assert p[0] == 100.0
