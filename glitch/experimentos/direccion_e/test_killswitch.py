"""Pruebas deterministas del kill-switch propuesto (NO DESPLEGAR)."""
import os, sys
import pytest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from killswitch_NO_DESPLEGAR import ALTERNATE, RULE, killswitch


def seq(wins, n=60): return [1] * wins + [0] * (n - wins)


def test_umbral_exacto():
    assert killswitch(seq(27)) == RULE          # 27/60 = 45.0 %: no es < 45 %
    assert killswitch(seq(26)) == ALTERNATE     # 26/60 = 43.3 %


def test_sin_historia_suficiente_es_alternate():
    assert killswitch([1] * 59) == ALTERNATE and killswitch([]) == ALTERNATE


def test_cambio_de_signo_de_la_señal_fuerza_alternate():
    assert killswitch([1] * 60, signal_flipped=True) == ALTERNATE


def test_solo_cuentan_las_ultimas_60():
    assert killswitch([0] * 100 + seq(40)) == RULE and killswitch([1] * 100 + seq(20)) == ALTERNATE


def test_determinista_y_sin_mutar_la_entrada():
    x = seq(30); y = list(x)
    assert [killswitch(x) for _ in range(5)] == [RULE] * 5 and x == y


def test_entrada_invalida():
    with pytest.raises(ValueError):
        killswitch([2] * 60)
