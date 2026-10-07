"""Pruebas del motor de reglas de Bulenox con los EJEMPLOS numericos de su propio centro de ayuda (bulenox.com/es/help-center, leido 08-oct-2026). SANDBOX / R&D."""
import os, sys
import pytest
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from bulenox.rules import plan, payout_rules, split, commission_rt, SIZES
from bulenox.account import BulenoxAccount, Breach


def eod_close(acc, new_balance):
    acc.balance = new_balance; acc.day_traded = True; acc.day_realized = 0.0; acc.end_of_day()


def test_eod_example_100k_from_help_center():
    """HC qualification: cuenta de $100,000, DD EOD $3,000: dia1 cierra 101,000 -> umbral 97,000->98,000; dia2 100,500 -> sigue 98,000; dia3 102,500 -> 99,500."""
    a = BulenoxAccount(plan("qualification", 100_000, 2))
    assert a.threshold == -3_000
    eod_close(a, 1_000); assert a.threshold == -2_000
    eod_close(a, 500); assert a.threshold == -2_000
    eod_close(a, 2_500); assert a.threshold == -500


def test_master_lock_50k_from_help_center():
    """HC master: Master 50K, DD $2,500: al cerrar en $52,600 el umbral queda fijo en $50,100 (permanente)."""
    a = BulenoxAccount(plan("qualification", 50_000, 2), stage="master")
    eod_close(a, 2_600); assert a.threshold == 100 and a.locked
    eod_close(a, 5_000); assert a.threshold == 100
    assert not a.dll_active()                                            # el DLL se elimina al fijarse el drawdown


def test_option1_dynamic_example_from_help_center():
    """HC qualification Opcion 1: DD dinamico $3,000 (100K); beneficio no realizado 800 -> umbral 97,800; se cierra con +500 realizado -> el umbral sigue en 97,800."""
    a = BulenoxAccount(plan("qualification", 100_000, 1), prod="MES", tick=0.25, tv=1.25)
    a.pos = None
    # simular posicion de 1 micro con +800 no realizado: precio sube 800/1.25*0.25 = 160 puntos (se ignoran comisiones para el ejemplo)
    a.open(1, 1, 5000.0); a.balance += a._comm_side(1); a.day_realized += a._comm_side(1)   # revertir comision del ejemplo
    a._check_at(5000.0 + 800 / 1.25 * 0.25)
    assert abs(a.threshold - (-3_000 + 800)) < 1e-6
    a.pos.tp = None
    a._close(5000.0 + 500 / 1.25 * 0.25, "ejemplo"); a.balance += a._comm_side(1)           # +500 realizado sin comision
    assert abs(a.balance - 500) < 1e-6 and abs(a.threshold - (-2_200)) < 1e-6


def test_option1_master_example():
    """HC master Opcion 1: Master 50K DD $2,500: a $51,000 el umbral pasa a 48,500; a $52,600 queda fijo en 50,100."""
    a = BulenoxAccount(plan("qualification", 50_000, 1), stage="master")
    a.open(1, 1, 5000.0); a.balance += a._comm_side(1); a.day_realized += a._comm_side(1)
    a._check_at(5000.0 + 1_000 / 1.25 * 0.25); assert abs(a.threshold - (-1_500)) < 1e-6
    a._check_at(5000.0 + 2_600 / 1.25 * 0.25); assert abs(a.threshold - 100) < 1e-6 and a.locked
    a._check_at(5000.0 + 4_000 / 1.25 * 0.25); assert abs(a.threshold - 100) < 1e-6


def test_scaling_table_50k_and_cap_enforced():
    p = plan("qualification", 50_000, 2)
    assert [p.micros_cap(c) for c in (0, 1_500, 1_501, 4_000, 4_001)] == [20, 20, 40, 40, 70]
    a = BulenoxAccount(p)
    with pytest.raises(Breach): a.open(1, 21, 5000.0)
    a.open(1, 20, 5000.0)


def test_dll_is_soft_and_resets_next_session():
    a = BulenoxAccount(plan("qualification", 50_000, 2))     # DLL $1,100
    a.open(1, 20, 5000.0)                                    # 20 micros -> $25 por tick-de-0.25pt? ($1.25*20)
    a.step_extreme(5000.0 - 1_100 / 25 * 0.25 - 0.5)         # pierde ~ $1,100 + comisiones
    assert a.dll_hit and a.status == "active" and a.pos is None
    with pytest.raises(Breach): a.open(1, 1, 5000.0)
    a.end_of_day()
    a.open(1, 1, 5000.0)                                     # se reanuda en la siguiente sesion


def test_breach_suspends_and_reset_fee():
    a = BulenoxAccount(plan("qualification", 50_000, 2))
    a.balance = -2_400; a.pos = None
    a.open(1, 10, 5000.0)                                    # comision ~ $6.1
    with pytest.raises(Breach): a.step_extreme(4900.0)
    assert a.status == "suspended" and plan("qualification", 50_000, 2).reset_fee == 78.0


def test_commissions_are_per_side_and_counted():
    assert commission_rt("MES") == pytest.approx(1.22) and commission_rt("MGC") == pytest.approx(1.52) and commission_rt("M6E") == pytest.approx(1.00)
    a = BulenoxAccount(plan("qualification", 50_000, 2)); a.open(1, 10, 5000.0)
    assert a.balance == pytest.approx(-6.1)
    a.flatten(5000.0); assert a.balance == pytest.approx(-12.2)


def test_master_payout_example_50k_from_help_center():
    """HC master: pago minimo $1,000 requiere saldo >= 50,000 + 2,600 + 1,000 = 53,600; tras el pago quedan >= 52,600."""
    a = BulenoxAccount(plan("qualification", 50_000, 2), stage="master")
    a.balance = 3_599; a.cycle_days = 10; a.cycle_best_day = 300
    assert a.payout_limits()[0] == 0
    a.balance = 3_600
    mx, why = a.payout_limits(); assert mx == 1_000 and why == "ok"
    net = a.request_payout(); assert net == 1_000 and a.balance == 2_600


def test_master_consistency_example_from_help_center():
    """HC master: P&L total $5,000 con mejor dia $2,500 = 50% -> no cumple 40%; con $7,500 = 33.33% -> si."""
    a = BulenoxAccount(plan("qualification", 50_000, 2), stage="master")
    a.cycle_days = 10; a.balance = 5_000; a.cycle_best_day = 2_500
    assert a.payout_limits()[0] == 0
    a.balance = 7_500
    assert a.payout_limits()[0] > 0


def test_master_caps_first_three_then_none_and_split_first_10k():
    r = payout_rules("master", 50_000)
    assert r.caps[:3] == (1_500.0,) * 3 and r.caps[3] == float("inf")
    assert split(0, 1_500, r) == 1_500 and split(9_000, 2_000, r) == 1_000 + 1_000 * 0.9 and split(10_000, 1_000, r) == 900


def test_fast_track_examples_from_help_center():
    """HC fast-track: 50K llega a $53,000 (objetivo 3,000); max 1-3 = $2,000; un retiro de $2,000 deja $51,000 > limite bloqueado $50,100."""
    a = BulenoxAccount(plan("fast_track", 50_000, 2), stage="fast_track")
    a.threshold = 100.0; a.locked = True
    a.balance = 3_000; a.cycle_best_day = 600                            # 20% de 3,000
    mx, why = a.payout_limits(); assert mx == 2_000 and why == "ok"
    a.request_payout(); assert a.balance == 1_000 and a.balance > a.threshold
    # 2.o ciclo (ejemplo de 25K): ciclo inicia en 26,500; objetivo 1,000 -> 27,500 es el colchon; solicitud minima 1,000 al llegar a 28,500
    b = BulenoxAccount(plan("fast_track", 25_000, 2), stage="fast_track"); b.threshold = 100.0; b.locked = True
    b.pay_n = 1; b.cycle_start_balance = 1_500; b.balance = 2_500; b.cycle_best_day = 250                # 27,500: objetivo cumplido, nada retirable
    assert b.payout_limits()[0] == 0
    b.balance = 3_500; b.cycle_best_day = 400; mx, why = b.payout_limits(); assert mx == 1_000, (mx, why)


def test_momentum_master_limits():
    r = payout_rules("momentum_master", 50_000)
    assert r.min_balance == 3_000 and r.min_request == 1_000 and r.caps == (1_500.0, 2_000.0, 2_500.0, 3_000.0) and r.win_day_min == 150.0 and r.consistency == (0.35,)
    a = BulenoxAccount(plan("momentum", 50_000, 2), stage="momentum_master")
    a.cycle_win_days = 5; a.balance = 2_999; a.cycle_best_day = 200
    assert a.payout_limits()[0] == 0
    a.balance = 3_000; a.cycle_best_day = 1_000                          # 33% de 3,000
    assert a.payout_limits()[0] == 1_500


def test_plans_match_pasted_pricing_pages():
    q = {s: plan("qualification", s, 2) for s in SIZES}
    assert [q[s].price for s in SIZES] == [145, 175, 215, 325] and [q[s].dll for s in SIZES] == [500, 1_100, 2_200, 3_300] and [q[s].target for s in SIZES] == [1_500, 3_000, 6_000, 9_000]
    assert [q[s].max_micros for s in SIZES] == [30, 70, 120, 150]
    m = {s: plan("momentum", s, 2) for s in SIZES}
    assert [m[s].price for s in SIZES] == [94, 143, 248, 358] and [m[s].drawdown for s in SIZES] == [1_000, 2_250, 4_000, 5_500] and [m[s].dll for s in SIZES] == [600, 1_200, 2_500, 3_300]
    f = {s: plan("fast_track", s, 2) for s in SIZES}
    assert [f[s].price for s in SIZES] == [338, 488, 648, 788] and f[25_000].dll is None and [f[s].max_micros for s in SIZES] == [20, 40, 80, 120]
