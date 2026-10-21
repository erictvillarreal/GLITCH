"""Pruebas de la PROPUESTA de sizing (NO DESPLEGAR). Correr:  python -m pytest -q test_sizing_pure.py"""
import math
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
from sizing_pure import nc_for_day, tp_net_per_contract  # noqa: E402
from strategies.geometry_pure import CANDIDATES  # noqa: E402

CFG = CANDIDATES["MES"]
KW = dict(tp_ticks=CFG.tp_ticks, tick_value_usd=CFG.spec.tick_value_usd, commission_roundturn=CFG.spec.commission_roundturn)


def test_fixed_es_el_comportamiento_actual():
    for need in (-50.0, 0.0, 100.0, 3000.0):
        assert nc_for_day("fixed", CFG.nc, need_usd=need, **KW) == CFG.nc


def test_finish_line_no_excede_el_cap_ni_baja_de_1():
    for need in (-500.0, 0.0, 1.0, 100.0, 1598.8, 3000.0, 10 ** 6):
        n = nc_for_day("finish_line", CFG.nc, need_usd=need, **KW)
        assert 1 <= n <= CFG.nc


def test_finish_line_formula():
    per = tp_net_per_contract(CFG.tp_ticks, CFG.spec.tick_value_usd, CFG.spec.commission_roundturn, 3.0)
    assert per == pytest.approx(29 * 1.25 - 1.22)
    assert nc_for_day("finish_line", CFG.nc, need_usd=100.0, **KW) == math.ceil(100.0 / per) == 3
    assert nc_for_day("finish_line", CFG.nc, need_usd=1598.8, **KW) == CFG.nc          # 46 contratos > cap 40 -> cap
    n = nc_for_day("finish_line", CFG.nc, need_usd=700.0, **KW)
    assert n * per >= 700.0 and (n - 1) * per < 700.0


def test_modo_invalido_y_cap_invalido():
    with pytest.raises(ValueError):
        nc_for_day("martingala", 40, need_usd=1.0, **KW)
    with pytest.raises(ValueError):
        nc_for_day("fixed", 0, need_usd=1.0, **KW)


def test_tp_que_no_cubre_costos_no_achica():
    assert nc_for_day("finish_line", 40, need_usd=100.0, tp_ticks=2, tick_value_usd=1.25, commission_roundturn=1.22) == 40
