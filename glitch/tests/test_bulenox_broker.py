"""SimBroker: un dia completo de ejecucion bajo las reglas de Bulenox (cierre natural por TP/SL, DLL suave, tope de contratos, cuenta suspendida). SANDBOX / R&D."""
import os, sys
import pytest
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from bulenox.rules import plan
from bulenox.account import BulenoxAccount, Breach
from bulenox.broker_port import SimBroker, AccountState


def broker(opt=2, name="qualification"):
    return SimBroker(BulenoxAccount(plan(name, 50_000, opt)))


def test_bracket_tp_day_and_eod():
    b = broker(); b.place_bracket(1, 10, 5000.0, 5010.0, 4990.0)
    b.on_bar(5004.0, 4998.0, 5003.0); assert b.account_state().position_qty == 10
    b.on_bar(5012.0, 5002.0, 5011.0); st = b.account_state()
    assert st.position_qty == 0 and st.balance == pytest.approx(10 * 40 * 1.25 - 12.2)       # 10 micros x 40 ticks x $1.25 - comisiones
    b.end_of_day(); assert b.account_state().status == "active"


def test_contract_cap_scales_with_cash_on_hand():
    b = broker()
    with pytest.raises(Breach): b.place_bracket(1, 21, 5000.0, 5010.0, 4990.0)
    b.acct.balance = 1_600.0
    assert b.account_state().micros_cap == 40
    b.place_bracket(1, 40, 5000.0, 5010.0, 4990.0)


def test_dll_pauses_the_session_not_the_account():
    b = broker(); b.place_bracket(1, 20, 5000.0, 6000.0, 4000.0)       # bracket muy lejano: el DLL se activa antes
    b.on_bar(5000.0, 4978.0, 4979.0)                                   # -22 pts * $100/pt = -$2,200 > DLL
    st = b.account_state(); assert st.dll_hit and st.position_qty == 0 and st.status == "active"
    with pytest.raises(Breach): b.place_bracket(1, 1, 4979.0, 4990.0, 4970.0)
    b.end_of_day(); b.place_bracket(1, 1, 4979.0, 4990.0, 4970.0)


def test_drawdown_breach_suspends_account():
    b = broker(); b.acct.balance = -2_300.0
    b.place_bracket(1, 20, 5000.0, 5100.0, 4000.0)
    b.on_bar(5000.0, 4990.0, 4991.0)
    assert b.account_state().status == "suspended"
    with pytest.raises(Breach): b.place_bracket(1, 1, 5000.0, 5010.0, 4990.0)
