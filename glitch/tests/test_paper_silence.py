"""Pruebas del silencio de paper (scheduler/paper_silence.py): solo con DRY_RUN=true y la variable en 'true'; las fallas siempre avisan; default sin cambios."""
import logging
from scheduler.paper_silence import paper_silent, wrap_send


def _mk():
    sent, log = [], logging.getLogger("t_paper_silence")
    return sent, (lambda m: sent.append(m)), log


def test_silent_requires_dry_run_and_true():
    assert paper_silent(True, "true") and paper_silent(True, " TRUE ")
    assert not paper_silent(False, "true")          # modo real: nunca silencia
    assert not paper_silent(True, None) and not paper_silent(True, "") and not paper_silent(True, "1") and not paper_silent(True, "false")


def test_default_returns_same_function():
    sent, f, log = _mk()
    assert wrap_send(f, False, log) is f


def test_silent_swallows_routine_messages():
    sent, f, log = _mk(); s = wrap_send(f, True, log)
    s("S10GLITCH - COMBINE - MES | INICIO DE DIA\nDia 33 de paper"); s("[OPEN]\nSymbol: MES"); s("[CLOSE]")
    assert sent == []


def test_silent_still_sends_failures():
    sent, f, log = _mk(); s = wrap_send(f, True, log)
    s("PREFIX\nSTATUS: ERROR\nERROR: front-month resolution failed"); s("PREFIX\nSTATUS: ALERTA\nalgo"); s("PREFIX\nSTATUS: BLOCKED\nx")
    assert len(sent) == 3


def test_real_mode_wrap_is_identity_even_with_variable():
    sent, f, log = _mk()
    assert wrap_send(f, paper_silent(False, "true"), log) is f
