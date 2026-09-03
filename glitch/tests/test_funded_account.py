"""
Glitch — Tests de core/funded_account.py (01-sep-2026)
==========================================================
Ninguno de estos tests existia antes de esta sesion -- el modulo se
usaba sin cobertura. Cubre la maquina de estados de XFAAccount, el
toggle mll_reset_policy (agregado en esta misma sesion para poder
correr AMBOS escenarios del MLL post-payout como sensibilidad, en vez
de un solo comportamiento hardcodeado), y una verificacion basica de
forma/sanidad de simulate_xfa_paths()/simulate_xfa_lifetime().
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pytest

from core.funded_account import (
    XFAAccount, XFASpec, XFAStatus, XFA_50K,
    simulate_xfa_paths, simulate_xfa_lifetime,
)


class TestXFAAccountBasics:

    def test_starts_at_zero_balance_and_active(self):
        acct = XFAAccount(XFA_50K)
        assert acct.balance == 0.0
        assert acct.status == XFAStatus.ACTIVE
        assert acct.mll_floor == -XFA_50K.mll_distance

    def test_winning_day_counts_only_when_net_pnl_meets_threshold(self):
        acct = XFAAccount(XFA_50K)
        acct.start_day()
        acct.record_trade_pnl(149.99)  # justo debajo del umbral de $150
        acct.end_of_day()
        assert acct.winning_days_count == 0

        acct.start_day()
        acct.record_trade_pnl(150.0)  # exactamente en el umbral
        acct.end_of_day()
        assert acct.winning_days_count == 1

    def test_losing_day_does_not_count_as_winning(self):
        acct = XFAAccount(XFA_50K)
        acct.start_day()
        acct.record_trade_pnl(-500.0)
        acct.end_of_day()
        assert acct.winning_days_count == 0
        assert acct.status == XFAStatus.ACTIVE

    def test_five_winning_days_triggers_payout_eligible(self):
        acct = XFAAccount(XFA_50K)
        for _ in range(5):
            acct.start_day()
            acct.record_trade_pnl(200.0)
            acct.end_of_day()
        assert acct.winning_days_count == 5
        assert acct.status == XFAStatus.PAYOUT_ELIGIBLE

    def test_mll_breach_is_permanent(self):
        acct = XFAAccount(XFA_50K)
        acct.start_day()
        acct.record_trade_pnl(-XFA_50K.mll_distance - 1)  # rompe el floor inicial
        acct.end_of_day()
        assert acct.status == XFAStatus.BLOWN_MLL
        assert not acct.is_alive

        # una vez tronada, mas trades no la reviven
        acct.start_day()
        acct.record_trade_pnl(10_000.0)
        acct.end_of_day()
        assert acct.status == XFAStatus.BLOWN_MLL

    def test_floor_ratchets_up_only_and_locks_at_spec_distance(self):
        acct = XFAAccount(XFA_50K)
        acct.start_day()
        acct.record_trade_pnl(5_000.0)
        acct.end_of_day()
        floor_after_gain = acct.mll_floor
        assert floor_after_gain > -XFA_50K.mll_distance  # subio

        acct.start_day()
        acct.record_trade_pnl(-1_000.0)  # perdida, pero no rompe el floor ya subido
        acct.end_of_day()
        assert acct.mll_floor == floor_after_gain  # el floor NO baja
        assert acct.is_alive

    def test_inactivity_closes_account_after_threshold(self):
        acct = XFAAccount(XFA_50K)
        for _ in range(XFA_50K.inactivity_close_days - 1):
            acct.end_of_day(no_trade_today=True)
        assert acct.is_alive
        acct.end_of_day(no_trade_today=True)
        assert acct.status == XFAStatus.INACTIVE_CLOSED
        assert not acct.is_alive


class TestPayoutAndMLLResetPolicy:

    def _make_eligible_account(self, mll_reset_policy: str) -> XFAAccount:
        acct = XFAAccount(XFA_50K, mll_reset_policy=mll_reset_policy)
        for _ in range(5):
            acct.start_day()
            acct.record_trade_pnl(1_000.0)  # dias ganadores grandes, para tener balance de sobra
            acct.end_of_day()
        assert acct.status == XFAStatus.PAYOUT_ELIGIBLE
        return acct

    def test_request_payout_reduces_balance_and_resets_winning_days(self):
        acct = self._make_eligible_account("every_payout")
        balance_before = acct.balance
        take = acct.request_payout()
        assert take > 0
        assert acct.balance < balance_before
        assert acct.winning_days_count == 0
        assert acct.lifetime_payouts == 1
        assert acct.status == XFAStatus.ACTIVE

    def test_request_payout_raises_if_not_eligible(self):
        acct = XFAAccount(XFA_50K)
        with pytest.raises(RuntimeError):
            acct.request_payout()

    def test_every_payout_policy_resets_floor_to_zero_every_time(self):
        acct = self._make_eligible_account("every_payout")
        acct.request_payout()
        assert acct.mll_floor == 0.0

        # segundo ciclo de 5 dias ganadores -> segundo payout
        for _ in range(5):
            acct.start_day()
            acct.record_trade_pnl(1_000.0)
            acct.end_of_day()
        floor_before_second_payout = acct.mll_floor
        assert floor_before_second_payout != 0.0  # trailing normal lo subio de nuevo
        acct.request_payout()
        assert acct.mll_floor == 0.0  # "every_payout" lo fuerza a 0 OTRA VEZ

    def test_first_payout_only_policy_does_not_reset_floor_on_second_payout(self):
        acct = self._make_eligible_account("first_payout_only")
        acct.request_payout()
        assert acct.mll_floor == 0.0  # la primera vez SI se fuerza a 0

        for _ in range(5):
            acct.start_day()
            acct.record_trade_pnl(1_000.0)
            acct.end_of_day()
        floor_before_second_payout = acct.mll_floor
        assert floor_before_second_payout != 0.0
        acct.request_payout()
        # "first_payout_only": la segunda vez NO se fuerza -- el floor
        # sigue exactamente donde el trailing normal ya lo tenia
        assert acct.mll_floor == floor_before_second_payout

    def test_both_policies_agree_on_first_payout(self):
        """La ambiguedad es sobre pagos SUBSECUENTES, no el primero -- ambas politicas deben coincidir ahi."""
        acct_a = self._make_eligible_account("every_payout")
        acct_b = self._make_eligible_account("first_payout_only")
        acct_a.request_payout()
        acct_b.request_payout()
        assert acct_a.mll_floor == acct_b.mll_floor == 0.0


class _ConstantDist:
    """Distribucion trivial para tests deterministas -- mismo pnl todos los dias."""
    def __init__(self, daily_pnl: float):
        self.daily_pnl = daily_pnl

    def sample(self, n, rng):
        return np.full(n, self.daily_pnl)


class TestSimulateXfaPaths:

    def test_all_paths_reach_eligible_with_strongly_positive_dist(self):
        dist = _ConstantDist(300.0)  # siempre gana $300/dia, mucho mas que el minimo
        result = simulate_xfa_paths(dist, spec=XFA_50K, n_paths=200, max_days=30, seed=1)
        assert result["prob_eligible"] == 1.0
        assert result["prob_blown"] == 0.0
        assert result["avg_days_to_eligible"] == pytest.approx(5.0)

    def test_all_paths_blow_with_strongly_negative_dist(self):
        dist = _ConstantDist(-XFA_50K.mll_distance - 100)
        result = simulate_xfa_paths(dist, spec=XFA_50K, n_paths=200, max_days=30, seed=1)
        assert result["prob_blown"] == 1.0
        assert result["prob_eligible"] == 0.0


class TestSimulateXfaLifetime:

    def test_returns_expected_keys_and_reasonable_values(self):
        dist = _ConstantDist(300.0)
        for policy in ("every_payout", "first_payout_only"):
            result = simulate_xfa_lifetime(dist, spec=XFA_50K, mll_reset_policy=policy,
                                            n_paths=100, max_days=60, seed=1)
            assert result["mll_reset_policy"] == policy
            assert result["avg_lifetime_payouts"] > 0
            assert 0.0 <= result["prob_still_alive_at_horizon"] <= 1.0
            assert 0.0 <= result["prob_never_reached_first_payout"] <= 1.0

    def test_strongly_negative_dist_never_reaches_first_payout(self):
        dist = _ConstantDist(-XFA_50K.mll_distance - 100)
        result = simulate_xfa_lifetime(dist, spec=XFA_50K, n_paths=100, max_days=30, seed=1)
        assert result["prob_never_reached_first_payout"] == 1.0
        assert result["avg_lifetime_payouts"] == 0.0
