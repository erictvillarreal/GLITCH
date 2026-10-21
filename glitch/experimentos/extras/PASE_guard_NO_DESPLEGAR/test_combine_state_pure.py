"""Pruebas de la PROPUESTA combine_status (NO DESPLEGAR). Ejemplos numericos tomados de help.topstep.com/8284208 (leido 20-oct-2026)."""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
import pytest
from combine_state_pure import combine_status


def test_objetivo_sube_con_mejor_dia_1800():
    s = combine_status([1800.0, -800.0])
    assert s["target"] == pytest.approx(1800 / 0.55) and round(s["target"]) == 3273 and s["status"] == "ACTIVO"


def test_objetivo_sube_a_4000_con_mejor_dia_2200():
    assert combine_status([1800.0, 2200.0])["target"] == pytest.approx(4000.0)


def test_pase_en_dos_dias_si_el_mejor_dia_no_pasa_el_55_por_ciento():
    s = combine_status([1600.0, 1450.0])          # 1600/3050 = 52 %
    assert s["profit"] == 3050.0 and s["status"] == "PASE"


def test_dos_dias_con_mejor_dia_mayor_al_55_no_pasan():
    s = combine_status([1900.0, 1200.0])          # 3100 pero 1900/3100 = 61 % -> objetivo 3454
    assert s["status"] == "ACTIVO" and s["target"] == pytest.approx(1900 / 0.55)


def test_un_solo_dia_nunca_pasa():
    assert combine_status([3200.0])["status"] == "ACTIVO"


def test_el_piso_sube_y_la_perdida_hasta_el_piso_es_quiebre():
    s = combine_status([1401.2, -2000.0])          # pico 1401.2 -> piso -598.8; balance -598.8
    assert s["status"] == "QUIEBRE" and s["floor"] == pytest.approx(-598.8)


def test_perdedores_no_reinician_el_mejor_dia():
    s = combine_status([1800.0, -1500.0, 1000.0])
    assert s["best_day"] == 1800.0 and s["target"] == pytest.approx(1800 / 0.55)
