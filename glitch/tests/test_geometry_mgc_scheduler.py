"""
Glitch — Tests para scheduler/geometry_mgc_scheduler.py (09-sep-2026)

Cubre la logica de reinicio de intento de Combine (misma logica que
geometry_scheduler.py, ver tests/test_geometry_parity.py, pero con los
umbrales de la cuenta 150K: profit_target=$9,000, mll_distance=$4,500,
confirmados contra core/prop_firm.py::TOPSTEP_150K, distintos de los
$3,000/$2,000 de G2/50K) y los umbrales de ENTRY_WAIT_MINUTES.
"""
import os

os.environ.setdefault("MASSIVE_API_KEY", "test-key-not-real")
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "test-token-not-real")
os.environ.setdefault("TELEGRAM_CHAT_ID", "test-chat-not-real")
os.environ.setdefault("GITHUB_GIST_TOKEN", "test-gist-token-not-real")
os.environ.setdefault("GIST_ID", "test-gist-id-not-real")

import pytest

import scheduler.geometry_mgc_scheduler as scheduler


class TestAttemptResetThresholds:
    def test_profit_target_matches_topstep_150k(self):
        from core.prop_firm import TOPSTEP_150K
        assert scheduler.PROFIT_TARGET == TOPSTEP_150K.profit_target == 9_000

    def test_mll_threshold_matches_topstep_150k_negated(self):
        from core.prop_firm import TOPSTEP_150K
        assert scheduler.MLL_THRESHOLD == -TOPSTEP_150K.mll_distance == -4_500

    def test_thresholds_distinct_from_g2_50k(self):
        """Confirma explicitamente que NO se reusaron por accidente los
        umbrales de la cuenta 50K de G2 -- ver instruccion del usuario de
        confirmar el tamaño de cuenta real antes de hardcodear."""
        assert scheduler.PROFIT_TARGET != 3_000
        assert scheduler.MLL_THRESHOLD != -2_000


class TestCurrentIntento:
    def test_empty_log_is_attempt_1(self):
        assert scheduler._current_intento([]) == 1

    def test_returns_highest_intento_seen(self):
        log = [
            {"date": "2026-09-01", "result": "TP", "pnl": 4500, "intento": 1},
            {"date": "2026-09-02", "result": "SL", "pnl": -300, "intento": 2},
        ]
        assert scheduler._current_intento(log) == 2

    def test_entries_without_intento_field_default_to_1(self):
        log = [{"date": "2026-09-01", "result": "TP", "pnl": 500}]
        assert scheduler._current_intento(log) == 1


class TestAttemptPnl:
    def test_sums_only_current_attempt(self):
        log = [
            {"date": "2026-09-01", "result": "TP", "pnl": 9000, "intento": 1},
            {"date": "2026-09-02", "result": "SL", "pnl": -600, "intento": 2},
        ]
        assert scheduler._attempt_pnl(log, 1) == 9000
        assert scheduler._attempt_pnl(log, 2) == -600

    def test_empty_attempt_is_zero(self):
        assert scheduler._attempt_pnl([], 1) == 0


class TestAttemptDaysElapsed:
    def test_no_entries_yet_is_zero(self):
        assert scheduler._attempt_days_elapsed([], 2, "2026-09-10") == 0

    def test_counts_from_first_entry_of_that_attempt_only(self):
        log = [
            {"date": "2026-09-01", "result": "SL", "pnl": -4500, "intento": 1},
            {"date": "2026-09-05", "result": "TP", "pnl": 600, "intento": 2},
        ]
        assert scheduler._attempt_days_elapsed(log, 2, "2026-09-08") == 4


class TestCheckAttemptReset:
    """Los 3 casos pedidos explicitamente, contra los umbrales reales de
    la cuenta 150K de este candidato."""

    def test_pase_at_exact_target(self):
        assert scheduler._check_attempt_reset(9000, 9000, -4500) == "PASE"

    def test_pase_when_overshooting_target(self):
        assert scheduler._check_attempt_reset(9800, 9000, -4500) == "PASE"

    def test_quiebre_at_exact_mll(self):
        assert scheduler._check_attempt_reset(-4500, 9000, -4500) == "QUIEBRE"

    def test_quiebre_when_overshooting_floor(self):
        assert scheduler._check_attempt_reset(-5200, 9000, -4500) == "QUIEBRE"

    def test_normal_case_no_event_between_thresholds(self):
        assert scheduler._check_attempt_reset(2000, 9000, -4500) is None
        assert scheduler._check_attempt_reset(-2000, 9000, -4500) is None
        assert scheduler._check_attempt_reset(0, 9000, -4500) is None

    def test_normal_case_just_short_of_either_threshold(self):
        assert scheduler._check_attempt_reset(8999.99, 9000, -4500) is None
        assert scheduler._check_attempt_reset(-4499.99, 9000, -4500) is None

    def test_uses_scheduler_own_constants_correctly(self):
        """Confirma que los umbrales reales del modulo (no numeros de
        prueba) tambien producen el veredicto esperado."""
        assert scheduler._check_attempt_reset(
            scheduler.PROFIT_TARGET, scheduler.PROFIT_TARGET, scheduler.MLL_THRESHOLD
        ) == "PASE"
        assert scheduler._check_attempt_reset(
            scheduler.MLL_THRESHOLD, scheduler.PROFIT_TARGET, scheduler.MLL_THRESHOLD
        ) == "QUIEBRE"


class TestAttemptPeak:
    """PORTADO (16-sep-2026, ver GLITCH_RESEARCH_LOG.md) desde
    geometry_scheduler.py -- gap de paridad ya identificado. Tambien es
    la base del floor trailing real (TestAttemptTrailingFloor abajo)."""

    def test_tracks_running_max_within_attempt(self):
        log = [
            {"date": "2026-09-01", "result": "TP", "pnl": 3000, "intento": 1},
            {"date": "2026-09-02", "result": "TP", "pnl": 1000, "intento": 1},
            {"date": "2026-09-03", "result": "SL", "pnl": -2000, "intento": 1},
        ]
        # running: 3000, 4000, 2000 -> peak=4000
        assert scheduler._attempt_peak(log, 1) == 4000

    def test_does_not_leak_across_attempts(self):
        log = [
            {"date": "2026-09-01", "result": "TP", "pnl": 9000, "intento": 1},
            {"date": "2026-09-02", "result": "TP", "pnl": 100, "intento": 2},
        ]
        assert scheduler._attempt_peak(log, 2) == 100


class TestAttemptTrailingFloor:
    """
    CORREGIDO (16-sep-2026, ver GLITCH_RESEARCH_LOG.md): floor trailing
    REAL de Topstep -- antes de este fix, _check_attempt_reset() siempre
    comparaba contra MLL_THRESHOLD fijo, ignorando cualquier pico
    intermedio. Verificado contra el Gist real de este mismo candidato
    (auditoria retrospectiva, scripts/audit_mgc_trailing_mll_2026_09_16.py)
    que la formula de abajo reproduce el mismo floor que el ratchet
    completo de TopstepMonteCarloSimulator.
    """

    def test_no_peak_equals_flat_mll_threshold(self):
        log = [
            {"date": "2026-09-01", "result": "SL", "pnl": -1000, "intento": 1},
        ]
        assert scheduler._attempt_trailing_floor(log, 1) == scheduler.MLL_THRESHOLD == -4500

    def test_floor_ratchets_up_with_a_real_peak(self):
        """Mismo caso real auditado el 16-sep-2026: pico de $906 ->
        floor sube a 906 + MLL_THRESHOLD = 906 - 4500 = -3594 (numero
        real confirmado por el usuario contra el Gist)."""
        log = [
            {"date": "2026-09-01", "result": "TP", "pnl": 906, "intento": 1},
        ]
        assert scheduler._attempt_trailing_floor(log, 1) == pytest.approx(906 + scheduler.MLL_THRESHOLD) == pytest.approx(-3594)

    def test_floor_never_exceeds_zero(self):
        log = [
            {"date": "2026-09-01", "result": "TP", "pnl": 5000, "intento": 1},
        ]
        assert scheduler._attempt_trailing_floor(log, 1) == 0.0

    def test_floor_does_not_leak_across_attempts(self):
        log = [
            {"date": "2026-09-01", "result": "TP", "pnl": 5000, "intento": 1},
            {"date": "2026-09-02", "result": "SL", "pnl": -100, "intento": 2},
        ]
        assert scheduler._attempt_trailing_floor(log, 2) == scheduler.MLL_THRESHOLD


class TestAttemptWinningDays:
    """22-sep-2026, pedido explicito del usuario -- contador REAL de
    elegibilidad de payout de Topstep (5 dias con PnL neto >= $150),
    DISTINTO de equity/balance acumulado (_attempt_pnl)."""

    def test_min_winning_day_usd_matches_xfa_150k(self):
        from core.funded_account import XFA_150K
        assert scheduler.MIN_WINNING_DAY_USD == XFA_150K.min_winning_day_usd == 150.0
        assert scheduler.WINNING_DAYS_REQUIRED == XFA_150K.winning_days_required == 5

    def test_counts_days_at_or_above_threshold_only(self):
        log = [
            {"date": "2026-09-01", "result": "TP", "pnl": 2184, "intento": 1},   # cuenta
            {"date": "2026-09-02", "result": "SL", "pnl": -2196, "intento": 1},  # no cuenta
            {"date": "2026-09-03", "result": "TP", "pnl": 149.99, "intento": 1},  # justo debajo, no cuenta
            {"date": "2026-09-04", "result": "TP", "pnl": 150.0, "intento": 1},  # exacto, SI cuenta
        ]
        assert scheduler._attempt_winning_days(log, 1) == 2

    def test_flatten_with_pnl_above_threshold_counts_too(self):
        """La regla es sobre el PnL del dia, no sobre que barrera se
        toco -- un FLATTEN que por lo que sea cerro en +$150 o mas
        tambien es un dia ganador elegible."""
        log = [{"date": "2026-09-01", "result": "FLATTEN", "pnl": 300, "intento": 1}]
        assert scheduler._attempt_winning_days(log, 1) == 1

    def test_does_not_leak_across_attempts(self):
        log = [
            {"date": "2026-09-01", "result": "TP", "pnl": 2184, "intento": 1},
            {"date": "2026-09-02", "result": "TP", "pnl": 2184, "intento": 2},
        ]
        assert scheduler._attempt_winning_days(log, 2) == 1

    def test_reconciled_entry_never_counts_as_winning_day(self):
        """Una posicion pendiente sin resolver (RECONCILED) nunca cuenta
        como dia ganador, aunque su pnl estimado sea >= $150 -- misma
        exclusion ya aplicada a equity/peak via _attempt_entries()."""
        log = [{"date": "2026-09-01", "result": "RECONCILED", "pnl": 5000,
                "pnl_estimated": True, "reconciled": True, "intento": 1}]
        assert scheduler._attempt_winning_days(log, 1) == 0

    def test_high_equity_with_zero_winning_days_is_possible(self):
        """Confirma explicitamente que equity acumulado y dias ganadores
        son criterios INDEPENDIENTES -- un intento puede tener equity
        positivo alto sin ningun dia individual >= $150 (ej. muchos
        dias pequeños), pedido explicito del usuario de no confundirlos."""
        log = [{"date": f"2026-09-{d:02d}", "result": "TP", "pnl": 50, "intento": 1} for d in range(1, 11)]
        assert scheduler._attempt_pnl(log, 1) == 500  # equity alto
        assert scheduler._attempt_winning_days(log, 1) == 0  # pero ningun dia individual califica

    def test_low_or_negative_equity_with_five_winning_days_is_possible(self):
        log = [
            {"date": "2026-09-01", "result": "TP", "pnl": 200, "intento": 1},
            {"date": "2026-09-02", "result": "TP", "pnl": 200, "intento": 1},
            {"date": "2026-09-03", "result": "TP", "pnl": 200, "intento": 1},
            {"date": "2026-09-04", "result": "TP", "pnl": 200, "intento": 1},
            {"date": "2026-09-05", "result": "TP", "pnl": 200, "intento": 1},
            {"date": "2026-09-06", "result": "SL", "pnl": -1200, "intento": 1},  # equity: 1000-1200=-200
        ]
        assert scheduler._attempt_pnl(log, 1) == -200
        assert scheduler._attempt_winning_days(log, 1) == 5


class TestReplayPayoutCycles:
    """22-sep-2026, pedido explicito del usuario: extension real de
    Topstep -- el conteo de 5 dias se REINICIA tras cada payout, y a
    partir del SEGUNDO payout se exige ademas profit neto >= $0.01
    desde el balance del payout anterior (el primero esta exento).
    Verificado contra help.topstep.com, ver GLITCH_RESEARCH_LOG.md."""

    def _tp(self, date, pnl=2184, intento=1):
        return {"date": date, "result": "TP", "pnl": pnl, "intento": intento}

    def _sl(self, date, pnl=-2196, intento=1):
        return {"date": date, "result": "SL", "pnl": pnl, "intento": intento}

    def test_no_entries_yet(self):
        state = scheduler._replay_payout_cycles([], 1)
        assert state == {"events": [], "winning_days_since_last": 0, "balance": 0.0, "is_first_payout": True}

    def test_first_payout_fires_at_exactly_5_winning_days_no_profit_condition_needed(self):
        """El primer payout esta EXENTO de la condicion de profit neto
        -- 5 dias ganadores, aunque el intento venga de mucho antes con
        equity bajo, es suficiente por si solo."""
        log = [self._tp(f"2026-09-0{d}") for d in range(1, 6)]
        state = scheduler._replay_payout_cycles(log, 1)
        assert len(state["events"]) == 1
        assert state["events"][0] == {"date": "2026-09-05", "balance": 2184 * 5, "n": 1}
        assert state["winning_days_since_last"] == 0  # se reinicio tras el payout
        assert state["is_first_payout"] is False  # ya paso el primero

    def test_winning_day_count_resets_after_first_payout_not_a_simple_modulo(self):
        """Confirma que el reinicio es un evento REAL (fecha del payout),
        no un simple modulo-5 acumulado -- dias 6,7,8,9 (4 mas, no 5
        mas) NO deben disparar un segundo evento todavia."""
        log = [self._tp(f"2026-09-{d:02d}") for d in range(1, 10)]  # 9 dias ganadores seguidos
        state = scheduler._replay_payout_cycles(log, 1)
        assert len(state["events"]) == 1  # solo el primero (dia 5) -- dia 10 haria falta para el segundo
        assert state["winning_days_since_last"] == 4  # dias 6,7,8,9 desde el primer payout

    def test_second_payout_fires_when_profit_since_last_payout_is_positive(self):
        log = ([self._tp(f"2026-09-0{d}") for d in range(1, 6)]  # payout 1, balance=10920
               + [self._tp(f"2026-09-{d:02d}") for d in range(6, 11)])  # 5 mas, balance=21840 (> 10920)
        state = scheduler._replay_payout_cycles(log, 1)
        assert len(state["events"]) == 2
        assert state["events"][1]["balance"] == 2184 * 10
        assert state["winning_days_since_last"] == 0

    def test_second_payout_blocked_when_profit_since_last_payout_is_negative(self):
        """El caso critico pedido explicitamente por el usuario: 5 dias
        ganadores NUEVOS desde el ultimo payout, pero el balance total
        cayo por debajo del balance del ultimo payout (perdidas grandes
        intercaladas) -- el segundo payout NO debe dispararse."""
        log = [self._tp(f"2026-09-0{d}") for d in range(1, 6)]  # payout 1, balance=10920
        log.append(self._sl("2026-09-06", pnl=-15000))          # balance: 10920-15000=-4080
        log += [self._tp(f"2026-09-{d:02d}") for d in (7, 8, 9, 10, 11)]  # balance final: -4080+10920=6840 (< 10920)
        state = scheduler._replay_payout_cycles(log, 1)
        assert len(state["events"]) == 1  # el segundo NO se disparo -- bloqueado
        assert state["winning_days_since_last"] >= scheduler.WINNING_DAYS_REQUIRED  # sigue "listo", esperando el profit-gate
        profit_since = state["balance"] - state["events"][-1]["balance"]
        assert profit_since < 0.01  # confirma por que esta bloqueado

    def test_blocked_payout_unblocks_on_a_later_day_once_profit_turns_positive(self):
        """Una vez bloqueado, el profit-gate se re-evalua cada dia
        siguiente -- incluyendo un dia que en si mismo NO es ganador,
        si ese dia alcanza a mover el balance por encima del ultimo
        payout."""
        log = [self._tp(f"2026-09-0{d}") for d in range(1, 6)]  # payout 1, balance=10920
        log.append(self._sl("2026-09-06", pnl=-15000))          # balance=-4080
        log += [self._tp(f"2026-09-{d:02d}") for d in (7, 8, 9, 10, 11)]  # balance=6840, bloqueado (5 ganadores desde el payout 1)
        log.append({"date": "2026-09-12", "result": "FLATTEN", "pnl": 4200, "intento": 1})  # balance=11040 (> 10920), NO es dia ganador (<150? no, 4200>=150 en realidad)
        state = scheduler._replay_payout_cycles(log, 1)
        assert len(state["events"]) == 2  # se libero -- el dia 12 empujo el profit-gate a positivo
        assert state["events"][1]["date"] == "2026-09-12"

    def test_does_not_leak_across_attempts(self):
        log = [self._tp(f"2026-09-0{d}", intento=1) for d in range(1, 6)]
        log += [self._tp(f"2026-09-{d:02d}", intento=2) for d in (6, 7)]
        state = scheduler._replay_payout_cycles(log, 2)
        assert state["events"] == []
        assert state["winning_days_since_last"] == 2
        assert state["is_first_payout"] is True  # el intento 2 nunca tuvo un payout propio


class TestCheckPayoutEligibilityCrossed:
    """Funcion PURA, mismo patron que TestCheckAttemptReset -- solo
    dispara cuando HOY agrego un evento NUEVO al historial (el conteo
    de eventos subio), nunca por seguir en el mismo numero de eventos
    (incluyendo el caso bloqueado por el profit-gate)."""

    def test_fires_when_a_new_event_appears(self):
        assert scheduler._check_payout_eligibility_crossed([], [{"date": "d", "balance": 1, "n": 1}]) is True

    def test_does_not_fire_when_event_count_is_unchanged(self):
        one = [{"date": "d", "balance": 1, "n": 1}]
        assert scheduler._check_payout_eligibility_crossed(one, one) is False

    def test_does_not_fire_while_blocked_by_profit_gate(self):
        """El caso critico pedido explicitamente: dias bloqueados (5+
        ganadores desde el ultimo payout, profit-gate no cumplido)
        siguen sin evento nuevo -- no deben re-avisar."""
        one = [{"date": "d1", "balance": 1, "n": 1}]
        assert scheduler._check_payout_eligibility_crossed(one, one) is False

    def test_fires_on_the_second_event_too(self):
        one = [{"date": "d1", "balance": 1, "n": 1}]
        two = one + [{"date": "d2", "balance": 2, "n": 2}]
        assert scheduler._check_payout_eligibility_crossed(one, two) is True


class TestPayoutEligibilitySimulatedSequence:
    """Simulacion de varios 'dias' compuestos con las funciones puras
    reales (mismo patron que TestCurrentIntentoAdvancesPastCompletedAttempt
    -- sin invocar run(), que hace I/O de red), para confirmar el
    comportamiento end-to-end del contador + el disparo de una sola vez."""

    def test_crosses_on_day_5_then_never_refires_through_day_8(self):
        paper_log = []
        intento = 1
        fired_days = []
        for day, pnl in enumerate([2184, 2184, 2184, 2184, 2184, 2184, 2184], start=1):
            before = scheduler._replay_payout_cycles(paper_log, intento)["events"]
            paper_log.append({"date": f"2026-09-{day:02d}", "result": "TP", "pnl": pnl, "intento": intento})
            after = scheduler._replay_payout_cycles(paper_log, intento)["events"]
            if scheduler._check_payout_eligibility_crossed(before, after):
                fired_days.append(day)
        assert fired_days == [5]  # dispara UNA sola vez, exactamente el dia que cruza a 5

    def test_after_attempt_resets_the_next_attempt_starts_the_count_at_zero(self):
        """Confirma que un intento NUEVO (post PASE/QUIEBRE) empieza su
        propio conteo desde 0 -- consistente con 'Iniciando intento
        #N+1 desde $0' del mensaje de reinicio ya existente. Escenario:
        un intento QUE YA PASO (PASE real via profit_target), seguido
        del intento siguiente, todavia sin ningun dia registrado."""
        paper_log_tras_pase = [
            {"date": "2026-09-01", "result": "TP", "pnl": 4500, "intento": 1},
            {"date": "2026-09-02", "result": "TP", "pnl": 4500, "intento": 1},  # 9000, PASE
        ]
        intento_nuevo = scheduler._current_intento(paper_log_tras_pase)
        assert intento_nuevo == 2
        state = scheduler._replay_payout_cycles(paper_log_tras_pase, intento_nuevo)
        assert state["events"] == [] and state["winning_days_since_last"] == 0


class TestAttemptResetIntegration:
    def test_full_reset_cycle_after_pass(self):
        # Intento 1: dos TP que acumulan a 9200 -> PASE.
        log = [
            {"date": "2026-09-01", "result": "TP", "pnl": 5000, "intento": 1},
            {"date": "2026-09-02", "result": "TP", "pnl": 4200, "intento": 1},  # acumulado 9200 -> PASE
        ]
        attempt_pnl = scheduler._attempt_pnl(log, 1)
        assert attempt_pnl == 9200
        event = scheduler._check_attempt_reset(attempt_pnl, scheduler.PROFIT_TARGET, scheduler.MLL_THRESHOLD)
        assert event == "PASE"

        # CORREGIDO (10-sep-2026): _current_intento() ahora detecta esto
        # directamente desde los datos guardados, sin necesitar que ya
        # exista ninguna entrada del intento 2 -- mismo fix portado desde
        # geometry_scheduler.py, ver GLITCH_RESEARCH_LOG.md.
        assert scheduler._current_intento(log) == 2

        log.append({"date": "2026-09-03", "result": "SL", "pnl": -300, "intento": 2})
        intento_nuevo = scheduler._current_intento(log)
        assert intento_nuevo == 2
        assert scheduler._attempt_pnl(log, intento_nuevo) == -300
        assert scheduler._attempt_pnl(log, 1) == 9200  # intento 1 no se toca

    def test_full_reset_cycle_after_blow(self):
        log = [
            {"date": "2026-09-01", "result": "SL", "pnl": -2500, "intento": 1},
            {"date": "2026-09-02", "result": "SL", "pnl": -2100, "intento": 1},  # acumulado -4600 -> QUIEBRE
        ]
        attempt_pnl = scheduler._attempt_pnl(log, 1)
        assert attempt_pnl == -4600
        assert scheduler._check_attempt_reset(attempt_pnl, scheduler.PROFIT_TARGET, scheduler.MLL_THRESHOLD) == "QUIEBRE"
        assert scheduler._current_intento(log) == 2  # mismo fix del 10-sep-2026, caso QUIEBRE

    def test_quiebre_detected_via_trailing_floor_even_when_flat_threshold_would_miss_it(self):
        """
        CORREGIDO (16-sep-2026, ver GLITCH_RESEARCH_LOG.md): reproduce
        el patron real reportado por el usuario en este mismo candidato
        (pico intermedio seguido de una caida que rompe el floor
        TRAILING real sin romper el MLL_THRESHOLD fijo). Auditoria
        retrospectiva contra el Gist real (scripts/audit_mgc_trailing_mll_2026_09_16.py)
        confirmo que el intento actual real NO habia llegado a este
        punto todavia -- este test usa numeros sinteticos mas extremos,
        diseñados especificamente para forzar la divergencia y probar
        que el fix la detecta cuando SI ocurre.
        """
        log = [
            {"date": "2026-09-01", "result": "TP", "pnl": 3000, "intento": 1},   # pico=3000, floor trailing sube a 3000-4500=-1500
            {"date": "2026-09-02", "result": "SL", "pnl": -4600, "intento": 1},  # acumulado -1600 -- rompe el floor trailing (-1500) pero NO el fijo (-4500)
        ]
        attempt_pnl = scheduler._attempt_pnl(log, 1)
        assert attempt_pnl == -1600

        # El floor FIJO (el bug, pre-16-sep) NUNCA habria detectado esto.
        assert scheduler._check_attempt_reset(attempt_pnl, scheduler.PROFIT_TARGET, scheduler.MLL_THRESHOLD) is None

        # El floor TRAILING real (el fix) SI lo detecta.
        trailing_floor = scheduler._attempt_trailing_floor(log, 1)
        assert trailing_floor == -1500
        assert scheduler._check_attempt_reset(attempt_pnl, scheduler.PROFIT_TARGET, trailing_floor) == "QUIEBRE"

        # _current_intento() usa el floor trailing internamente -- debe
        # avanzar a intento 2, no quedarse en 1 como antes del fix.
        assert scheduler._current_intento(log) == 2

    def test_does_not_advance_when_drawdown_stays_within_trailing_floor(self):
        """Guardia de regresion -- un pico seguido de una caida que NO
        rompe ni el floor trailing ni el fijo no debe avanzar de intento."""
        log = [
            {"date": "2026-09-01", "result": "TP", "pnl": 3000, "intento": 1},   # floor trailing = -1500
            {"date": "2026-09-02", "result": "SL", "pnl": -1000, "intento": 1},  # acumulado 2000 -- ni cerca de ningun floor
        ]
        assert scheduler._current_intento(log) == 1

    def test_historic_wr_and_cycles_never_reset_across_attempts(self):
        log = [
            {"date": "2026-09-01", "result": "TP", "pnl": 4500, "intento": 1},
            {"date": "2026-09-02", "result": "TP", "pnl": 4600, "intento": 1},  # PASE
            {"date": "2026-09-03", "result": "SL", "pnl": -600, "intento": 2},
        ]
        progress = scheduler._paper_progress(log, "2026-09-03")
        assert progress["n_cycles"] == 3
        assert progress["wr_empirico"] == pytest.approx(2 / 3)


class TestCurrentIntentoAdvancesPastCompletedAttempt:
    """
    10-sep-2026, ver GLITCH_RESEARCH_LOG.md -- mismo fix portado desde
    geometry_scheduler.py (bug real reportado en GEOMETRY/MES): el
    `intento_actual += 1` de run() nunca se persistia -- era una
    variable local, se perdia al salir del proceso, y la corrida del
    dia siguiente volvia a calcular el mismo intento ya completado
    desde cero. Estos tests confirman el mismo fix aqui, con los
    umbrales reales de MGC/150K (PROFIT_TARGET=9000, MLL_THRESHOLD=-4500).
    """

    def test_reproduces_the_reported_bug_scenario(self):
        paper_log = [
            {"date": "2026-09-08", "result": "TP", "pnl": 4500, "intento": 1},
            {"date": "2026-09-09", "result": "TP", "pnl": 4500, "intento": 1},  # acumulado exacto: 9000
        ]
        assert scheduler._current_intento(paper_log) == 2  # antes del fix: 1 (el bug reportado)

    def test_attempt_pnl_for_the_new_attempt_is_zero_not_stale_9000(self):
        paper_log = [
            {"date": "2026-09-08", "result": "TP", "pnl": 4500, "intento": 1},
            {"date": "2026-09-09", "result": "TP", "pnl": 4500, "intento": 1},
        ]
        intento = scheduler._current_intento(paper_log)
        assert scheduler._attempt_pnl(paper_log, intento) == 0

    def test_advances_past_a_completed_quiebre_too(self):
        paper_log = [
            {"date": "2026-09-08", "result": "SL", "pnl": -2500, "intento": 1},
            {"date": "2026-09-09", "result": "SL", "pnl": -2100, "intento": 1},  # acumulado: -4600, cruza -4500
        ]
        assert scheduler._current_intento(paper_log) == 2

    def test_does_not_advance_an_attempt_still_in_progress(self):
        """Guardia de regresion -- un intento normal, todavia sin
        cruzar ningun umbral, NO debe avanzar de mas."""
        paper_log = [
            {"date": "2026-09-08", "result": "TP", "pnl": 2000, "intento": 1},
            {"date": "2026-09-09", "result": "SL", "pnl": -500, "intento": 1},  # acumulado: 1500, normal
        ]
        assert scheduler._current_intento(paper_log) == 1

    def test_advances_correctly_even_with_a_reconciled_entry_in_the_mix(self):
        paper_log = [
            {"date": "2026-09-07", "result": "TP", "pnl": 4500, "intento": 1},
            {"date": "2026-09-08", "result": "RECONCILED", "pnl": -9999,
             "pnl_estimated": True, "reconciled": True, "intento": 1},
            {"date": "2026-09-09", "result": "TP", "pnl": 4500, "intento": 1},  # 4500+4500=9000, la RECONCILED no cuenta
        ]
        assert scheduler._current_intento(paper_log) == 2

    def test_full_next_day_simulation_matches_expected_open_message(self):
        paper_log = [
            {"date": "2026-09-08", "result": "TP", "pnl": 4500, "intento": 1},
            {"date": "2026-09-09", "result": "TP", "pnl": 4500, "intento": 1},
        ]
        intento_fin_dia1 = scheduler._current_intento(paper_log)

        intento_inicio_dia2 = scheduler._current_intento(paper_log)
        attempt_pnl_dia2 = scheduler._attempt_pnl(paper_log, intento_inicio_dia2)

        assert intento_inicio_dia2 == intento_fin_dia1 == 2
        assert attempt_pnl_dia2 == 0  # $0 / $9,000 (0.0%) -- NO $9,000 / $9,000 (100.0%)


class TestPendingPositionWrappers:
    """09-sep-2026, ver GLITCH_RESEARCH_LOG.md -- hallazgo de la posicion
    SHORT MGCV6 que nunca recibio su CLOSE. Mismo mecanismo que
    geometry_scheduler.py."""

    def test_load_pending_calls_gist_store_with_mgc_pending_filename(self, monkeypatch):
        captured = {}

        def _fake_load_state(filename):
            captured["filename"] = filename
            return {"side": -1}

        monkeypatch.setattr(scheduler, "_gist_load_state", _fake_load_state)
        result = scheduler.load_pending()
        assert captured["filename"] == "geometry_mgc_pending.json"
        assert result == {"side": -1}

    def test_save_pending_calls_gist_store_with_mgc_pending_filename_and_data(self, monkeypatch):
        captured = {}
        monkeypatch.setattr(scheduler, "_gist_save_state",
                             lambda filename, data: captured.update(filename=filename, data=data))
        scheduler.save_pending({"side": -1, "entry": 4415.80})
        assert captured["filename"] == "geometry_mgc_pending.json"
        assert captured["data"] == {"side": -1, "entry": 4415.80}


class TestCurrentIntentoConsidersReconciledEntries:
    """Mismo fix que geometry_scheduler.py -- encontrado al diseñar la
    reconciliacion, aplicado aqui tambien (mismo bug, misma correccion)."""

    def test_reconciled_only_entry_still_advances_current_intento(self):
        log = [
            {"date": "2026-09-01", "result": "TP", "pnl": 4500, "intento": 1},
            {"date": "2026-09-02", "result": "TP", "pnl": 4600, "intento": 1},  # PASE -> intento 2
            {"date": "2026-09-03", "result": "RECONCILED", "pnl": -1000,
             "pnl_estimated": True, "reconciled": True, "intento": 2},
        ]
        assert scheduler._current_intento(log) == 2

    def test_reconciled_entry_alone_never_triggers_reset(self):
        log = [{"date": "2026-09-01", "result": "RECONCILED", "pnl": -8000,
                "pnl_estimated": True, "reconciled": True, "intento": 1}]
        attempt_pnl = scheduler._attempt_pnl(log, scheduler._current_intento(log))
        assert attempt_pnl == 0
        assert scheduler._check_attempt_reset(attempt_pnl, scheduler.PROFIT_TARGET, scheduler.MLL_THRESHOLD) is None


class TestBuildPendingRecord:
    def test_captures_everything_needed_to_reconcile(self):
        record = scheduler._build_pending_record(
            side=-1, direction_str="SHORT", entry_price=4415.80,
            tp_price=4379.40, sl_price=4452.20, ticker="MGCV6",
            today_str="2026-09-09", intento=1, nc=6, sl_ticks=364,
            tp_ticks=364, product_key="MGC_XFA_150K", dry_run=True,
        )
        assert record == {
            "date": "2026-09-09", "side": -1, "direction": "SHORT",
            "entry": 4415.80, "tp_price": 4379.40, "sl_price": 4452.20,
            "ticker": "MGCV6", "nc": 6, "sl_ticks": 364, "tp_ticks": 364,
            "product": "MGC_XFA_150K", "dry_run": True, "intento": 1,
        }


class TestReconcilePendingPosition:
    """
    Reproduce el escenario real reportado: SHORT MGCV6, entry=4415.80,
    TP=4379.40, SL=4452.20.
    """

    def _pending_short(self):
        return {
            "date": "2026-09-09", "side": -1, "direction": "SHORT",
            "entry": 4415.80, "tp_price": 4379.40, "sl_price": 4452.20,
            "ticker": "MGCV6", "nc": 6, "sl_ticks": 364, "tp_ticks": 364,
            "product": "MGC_XFA_150K", "dry_run": True, "intento": 1,
        }

    def _pending_long(self):
        return {
            "date": "2026-09-09", "side": 1, "direction": "LONG",
            "entry": 4415.80, "tp_price": 4452.20, "sl_price": 4379.40,
            "ticker": "MGCV6", "nc": 6, "sl_ticks": 364, "tp_ticks": 364,
            "product": "MGC_XFA_150K", "dry_run": True, "intento": 1,
        }

    def test_result_is_always_reconciled_never_a_normal_outcome(self):
        for price in (4360.0, 4460.0, 4415.0):
            entry = scheduler._reconcile_pending_position(self._pending_short(), price,
                                                            tick_value_usd=1.00, tick_size=0.10)
            assert entry["result"] == "RECONCILED"
            assert entry["reconciled"] is True
            assert entry["pnl_estimated"] is True

    def test_short_price_beyond_tp_estimates_tp_clipped_to_barrier(self):
        pending = self._pending_short()
        entry = scheduler._reconcile_pending_position(pending, 4360.0, tick_value_usd=1.00, tick_size=0.10)
        assert entry["estimated_outcome"] == "TP"
        assert entry["exit"] == pending["tp_price"]  # clipped, no el precio crudo
        expected_pnl = (pending["tp_price"] - pending["entry"]) * -1 * 1.00 / 0.10 * pending["nc"]
        assert entry["pnl"] == pytest.approx(round(expected_pnl, 2))
        assert entry["pnl"] > 0

    def test_short_price_beyond_sl_estimates_sl_clipped_to_barrier(self):
        pending = self._pending_short()
        entry = scheduler._reconcile_pending_position(pending, 4460.0, tick_value_usd=1.00, tick_size=0.10)
        assert entry["estimated_outcome"] == "SL"
        assert entry["exit"] == pending["sl_price"]
        assert entry["pnl"] < 0

    def test_short_price_inconclusive_between_barriers(self):
        pending = self._pending_short()
        entry = scheduler._reconcile_pending_position(pending, 4415.0, tick_value_usd=1.00, tick_size=0.10)
        assert entry["estimated_outcome"] == "INCONCLUSIVE"
        assert entry["exit"] == 4415.0

    def test_long_price_beyond_tp_estimates_tp_clipped_to_barrier(self):
        pending = self._pending_long()
        entry = scheduler._reconcile_pending_position(pending, 4460.0, tick_value_usd=1.00, tick_size=0.10)
        assert entry["estimated_outcome"] == "TP"
        assert entry["exit"] == pending["tp_price"]
        assert entry["pnl"] > 0

    def test_long_price_beyond_sl_estimates_sl_clipped_to_barrier(self):
        pending = self._pending_long()
        entry = scheduler._reconcile_pending_position(pending, 4360.0, tick_value_usd=1.00, tick_size=0.10)
        assert entry["estimated_outcome"] == "SL"
        assert entry["exit"] == pending["sl_price"]
        assert entry["pnl"] < 0

    def test_long_price_inconclusive_between_barriers(self):
        pending = self._pending_long()
        entry = scheduler._reconcile_pending_position(pending, 4415.0, tick_value_usd=1.00, tick_size=0.10)
        assert entry["estimated_outcome"] == "INCONCLUSIVE"
        assert entry["exit"] == 4415.0

    def test_preserves_intento_and_identity_fields(self):
        pending = self._pending_short()
        entry = scheduler._reconcile_pending_position(pending, 4415.0, tick_value_usd=1.00, tick_size=0.10)
        assert entry["intento"] == 1
        assert entry["date"] == "2026-09-09"
        assert entry["product"] == "MGC_XFA_150K"
        assert entry["nc"] == 6


class TestPendingPositionFullCycle:
    """Simula exactamente el escenario reportado: SHORT MGCV6 se abre,
    el proceso 'muere' antes del CLOSE, la siguiente corrida reconcilia,
    y un trade nuevo despues no colisiona."""

    def test_interrupted_short_reconciled_then_new_trade_opens_clean(self):
        paper_log = [{"date": "2026-09-05", "result": "TP", "pnl": 2000, "intento": 1}]

        intento = scheduler._current_intento(paper_log)
        pending = scheduler._build_pending_record(
            side=-1, direction_str="SHORT", entry_price=4415.80,
            tp_price=4379.40, sl_price=4452.20, ticker="MGCV6",
            today_str="2026-09-09", intento=intento, nc=6, sl_ticks=364,
            tp_ticks=364, product_key="MGC_XFA_150K", dry_run=True,
        )
        assert intento == 1

        # La siguiente corrida reconcilia con el precio actual.
        reconciled = scheduler._reconcile_pending_position(pending, 4420.0, tick_value_usd=1.00, tick_size=0.10)
        paper_log.append(reconciled)
        pending = {}  # save_pending({}) -- limpio

        assert not pending
        assert reconciled["result"] == "RECONCILED"
        assert reconciled["estimated_outcome"] == "INCONCLUSIVE"  # 4420 esta entre TP y SL
        assert scheduler._attempt_pnl(paper_log, 1) == 2000  # sin cambio -- la reconciliada no cuenta

        # Trade nuevo, real, mismo intento.
        paper_log.append({"date": "2026-09-10", "result": "TP", "pnl": 2184, "intento": 1})
        assert scheduler._current_intento(paper_log) == 1
        assert scheduler._attempt_pnl(paper_log, 1) == 4184  # 2000 + 2184, la reconciliada sigue sin contar
