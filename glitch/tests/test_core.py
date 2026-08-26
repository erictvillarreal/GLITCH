"""
Glitch — Test Suite (Topstep-specific, 2026 rules)
===================================================
Run: pytest tests/ -v
"""
import pytest
import numpy as np
import pandas as pd

from core.prop_firm import TOPSTEP_50K, TOPSTEP_100K, TOPSTEP_150K, get_spec
from core.account import TopstepCombineAccount, CombineStatus
from simulation.monte_carlo import DailyReturnDist, TopstepMonteCarloSimulator
from simulation.triple_barrier import (
    label_triple_barrier, BarrierConfig, walk_forward_validate,
    statistical_summary, extract_daily_pnl_from_labels
)


# ══════════════════════════════════════════════════════════
# 1. Spec / config
# ══════════════════════════════════════════════════════════

class TestTopstepSpec:
    def test_50k_hard_numbers(self):
        s = TOPSTEP_50K
        assert s.account_size        == 50_000
        assert s.mll_distance        == 2_000
        assert s.profit_target       == 3_000
        assert s.daily_loss_limit    == 1_000
        assert s.consistency_cap_pct == 0.50
        assert s.max_mini_contracts  == 5

    def test_starting_floor(self):
        assert TOPSTEP_50K.starting_floor == 48_000

    def test_floor_lock_level(self):
        assert TOPSTEP_50K.floor_lock_level == 50_000

    def test_consistency_max_day(self):
        # best day must be < 50% of $3,000 target = $1,500
        assert TOPSTEP_50K.consistency_max_day_usd == 1_500

    def test_three_sizes_exist(self):
        for sz in ["50K", "100K", "150K"]:
            s = get_spec(sz)
            assert s.profit_target > 0

    def test_mll_ratio_50k(self):
        # Topstep 50K: profit_target / mll_distance = 3000/2000 = 1.5
        assert TOPSTEP_50K.profit_target / TOPSTEP_50K.mll_distance == pytest.approx(1.5)

    def test_mll_ratio_100k(self):
        # 100K: 6000/3000 = 2.0
        assert TOPSTEP_100K.profit_target / TOPSTEP_100K.mll_distance == pytest.approx(2.0)

    def test_unknown_size_raises(self):
        with pytest.raises(ValueError):
            get_spec("200K")


# ══════════════════════════════════════════════════════════
# 2. Account state machine
# ══════════════════════════════════════════════════════════

class TestAccountStateMachine:

    def _account(self):
        return TopstepCombineAccount(TOPSTEP_50K)

    # ── Initial state ──────────────────────────────────────
    def test_initial_balance(self):
        a = self._account()
        assert a.balance   == 50_000
        assert a.mll_floor == 48_000
        assert a.status    == CombineStatus.ACTIVE

    # ── EOD floor mechanics ────────────────────────────────
    def test_floor_does_not_move_on_losing_day(self):
        a = self._account()
        a.start_day()
        a.record_trade_pnl(-500)
        a.end_of_day()
        # Balance = 49_500. New floor candidate = 49_500 - 2_000 = 47_500 < 48_000
        assert a.mll_floor == 48_000   # no movement

    def test_floor_moves_up_on_profitable_eod(self):
        a = self._account()
        a.start_day()
        a.record_trade_pnl(600)
        a.end_of_day()
        # Balance = 50_600. Floor = 50_600 - 2_000 = 48_600
        assert a.mll_floor == pytest.approx(48_600)

    def test_floor_never_moves_down(self):
        a = self._account()
        # Day 1: win $800
        a.start_day(); a.record_trade_pnl(800); a.end_of_day()
        floor_after_win = a.mll_floor
        # Day 2: lose $400
        a.start_day(); a.record_trade_pnl(-400); a.end_of_day()
        assert a.mll_floor == floor_after_win   # unchanged

    def test_floor_locks_at_starting_balance(self):
        a = self._account()
        # Win enough to push floor up to 50_000 (= account_size)
        # Need balance = 52_000 → floor = 50_000 = lock
        a.start_day(); a.record_trade_pnl(2_200); a.end_of_day()
        assert a.mll_floor == 50_000
        assert a.mll_floor_locked

    def test_no_further_floor_movement_after_lock(self):
        a = self._account()
        a.start_day(); a.record_trade_pnl(2_200); a.end_of_day()
        assert a.mll_floor_locked
        a.start_day(); a.record_trade_pnl(1_000); a.end_of_day()
        assert a.mll_floor == 50_000  # stays locked

    # ── BLOWN_MLL ──────────────────────────────────────────
    def test_blown_when_eod_balance_at_floor(self):
        a = self._account()
        # Floor = 48_000. Lose exactly $2_000 → balance = 48_000 = floor
        a.start_day(); a.record_trade_pnl(-2_000); a.end_of_day()
        assert a.status == CombineStatus.BLOWN_MLL

    def test_blown_when_eod_balance_below_floor(self):
        a = self._account()
        a.start_day(); a.record_trade_pnl(-2_001); a.end_of_day()
        assert a.status == CombineStatus.BLOWN_MLL
        assert not a.is_alive

    def test_winning_day_then_big_loss_can_blow(self):
        a = self._account()
        # Day 1: win $1_000 → floor moves to 49_000
        a.start_day(); a.record_trade_pnl(1_000); a.end_of_day()
        assert a.mll_floor == 49_000
        # Day 2: lose $2_001 → balance = 49_999 > floor? No: 51_000 - 2_001 = 48_999 < 49_000
        a.start_day(); a.record_trade_pnl(-2_001); a.end_of_day()
        assert a.status == CombineStatus.BLOWN_MLL

    # ── DLL (soft) ─────────────────────────────────────────
    def test_dll_pauses_session_not_fatal(self):
        a = self._account()
        a.start_day()
        a.record_trade_pnl(-1_001)    # past $1,000 DLL
        assert a.day_paused
        # End of day — account survives (balance = 48,999 < 48,000? no: 50,000 - 1,001 = 48,999 > 48,000)
        a.end_of_day()
        assert a.status == CombineStatus.ACTIVE   # reset to active next day

    def test_dll_hit_then_eod_still_above_floor(self):
        a = self._account()
        a.start_day(); a.record_trade_pnl(-1_001); a.end_of_day()
        assert a.is_alive

    # ── PASS conditions ────────────────────────────────────
    def test_pass_requires_profit_target(self):
        a = self._account()
        a.start_day(); a.record_trade_pnl(2_999); a.end_of_day()
        assert a.status == CombineStatus.ACTIVE   # not yet

    def test_pass_when_target_hit_consistency_ok(self):
        a = self._account()
        # Day 1: $500, Day 2: $500, Day 3: $500, Day 4: $500, Day 5: $500, Day 6: $500 → total $3000
        # best day $500 = 16.7% < 50% → OK
        for _ in range(6):
            a.start_day(); a.record_trade_pnl(500); a.end_of_day()
        assert a.status == CombineStatus.PASSED

    def test_consistency_gated_when_best_day_too_high(self):
        a = self._account()
        # Day 1: $1_600 (>= 50% of $3_000 = $1_500)
        # Day 2: $1_600 → total = $3_200, best = $1_600, ratio = 50% → gated
        a.start_day(); a.record_trade_pnl(1_600); a.end_of_day()
        a.start_day(); a.record_trade_pnl(1_600); a.end_of_day()
        # 1600/3200 = 50% → >= 0.50 → gated
        assert a.status == CombineStatus.CONSISTENCY_GATED

    def test_consistency_gated_then_resolved(self):
        a = self._account()
        # Day 1: $1_600 — big day
        a.start_day(); a.record_trade_pnl(1_600); a.end_of_day()
        # Day 2: $1_500 → total = $3_100, best = $1_600, ratio = 51.6% gated
        a.start_day(); a.record_trade_pnl(1_500); a.end_of_day()
        assert a.status == CombineStatus.CONSISTENCY_GATED
        # Day 3-5: $400/day → total = $4_300, best = $1_600, ratio = 37.2% → PASS
        for _ in range(3):
            a.start_day(); a.record_trade_pnl(400); a.end_of_day()
        assert a.status == CombineStatus.PASSED

    # ── Properties ────────────────────────────────────────
    def test_mll_buffer(self):
        a = self._account()
        a.start_day(); a.record_trade_pnl(500); a.end_of_day()
        # balance=50_500, floor=48_500
        assert a.mll_buffer == pytest.approx(2_000)

    def test_consistency_ratio(self):
        a = self._account()
        a.start_day(); a.record_trade_pnl(400); a.end_of_day()
        a.start_day(); a.record_trade_pnl(600); a.end_of_day()
        # best=600, cum=1000 → ratio=0.60
        assert a.consistency_ratio == pytest.approx(0.60)

    def test_summary_has_required_keys(self):
        a = self._account()
        s = a.summary()
        for k in ["status","balance","mll_floor","mll_buffer","cumulative_profit",
                  "best_day","consistency_ratio","profit_progress"]:
            assert k in s


# ══════════════════════════════════════════════════════════
# 3. DailyReturnDist
# ══════════════════════════════════════════════════════════

class TestDailyReturnDist:

    def test_expected_pnl_positive_edge(self):
        d = DailyReturnDist(win_rate=0.60, avg_win=300, avg_loss=200)
        # EV = 0.6*300 - 0.4*200 = 180 - 80 = 100
        assert d.expected_daily_pnl == pytest.approx(100.0)

    def test_expected_pnl_negative_edge(self):
        d = DailyReturnDist(win_rate=0.40, avg_win=200, avg_loss=300)
        # EV = 0.4*200 - 0.6*300 = 80 - 180 = -100
        assert d.expected_daily_pnl == pytest.approx(-100.0)

    def test_edge_ratio(self):
        d = DailyReturnDist(win_rate=0.55, avg_win=300, avg_loss=200)
        assert d.edge_ratio == pytest.approx(1.5)

    def test_from_trade_log(self):
        rng = np.random.default_rng(42)
        pnls = rng.choice([250, -180], size=200, p=[0.6, 0.4]).astype(float)
        d = DailyReturnDist.from_trade_log(pnls)
        assert 0.55 < d.win_rate < 0.65
        assert 200 < d.avg_win < 300
        assert 140 < d.avg_loss < 220

    def test_sample_respects_win_rate(self):
        d = DailyReturnDist(win_rate=0.60, avg_win=300, avg_loss=200)
        rng = np.random.default_rng(0)
        samples = d.sample(50_000, rng)
        actual_wr = (samples > 0).mean()
        assert abs(actual_wr - 0.60) < 0.01


# ══════════════════════════════════════════════════════════
# 4. Monte Carlo simulation
# ══════════════════════════════════════════════════════════

class TestMonteCarloSimulator:

    def _run(self, wr, aw, al, n=10_000, seed=42):
        dist = DailyReturnDist(win_rate=wr, avg_win=aw, avg_loss=al)
        sim  = TopstepMonteCarloSimulator(dist, TOPSTEP_50K, n_paths=n, seed=seed)
        return sim.run()

    def test_zero_ev_nonzero_pass_rate(self):
        # EV = 0.5*200 - 0.5*200 = 0, but should still pass some
        r = self._run(0.50, 200, 200)
        assert 0 < r.pass_rate < 1.0

    def test_strong_edge_high_pass_rate(self):
        r = self._run(0.70, 300, 150)
        assert r.pass_rate > 0.70

    def test_negative_edge_low_pass_rate(self):
        r = self._run(0.35, 150, 300)
        assert r.pass_rate < 0.20

    def test_reproducibility(self):
        r1 = self._run(0.55, 250, 200, seed=7)
        r2 = self._run(0.55, 250, 200, seed=7)
        assert r1.pass_rate == r2.pass_rate
        assert r1.blow_rate == r2.blow_rate

    def test_pass_blow_alive_sum_to_n(self):
        r = self._run(0.50, 200, 180)
        total = r.n_passed + r.n_blown + r.n_cons_gated + r.n_alive
        assert total == r.n_paths

    def test_wilson_ci_brackets_pass_rate(self):
        r = self._run(0.55, 250, 200, n=20_000)
        lo, hi = r.wilson_ci()
        assert lo < r.pass_rate < hi
        assert lo >= 0 and hi <= 1

    def test_ci_width_shrinks_with_more_paths(self):
        r_small = self._run(0.55, 250, 200, n=1_000)
        r_large = self._run(0.55, 250, 200, n=20_000)
        lo_s, hi_s = r_small.wilson_ci()
        lo_l, hi_l = r_large.wilson_ci()
        assert (hi_l - lo_l) < (hi_s - lo_s)

    def test_consistency_gate_high_rr_big_days(self):
        # High avg_win days that exceed $1,500 cap → some consistency gates
        # 2% threshold is realistic (most paths blow MLL before hitting gate)
        r = self._run(0.30, 2_000, 300, n=5_000)
        assert r.consistency_gate_rate > 0.01

    def test_avg_pass_days_positive(self):
        r = self._run(0.65, 300, 180)
        assert r.avg_pass_days is not None
        assert r.avg_pass_days > 0

    # ── Core Glitch hypothesis ─────────────────────────────
    def test_moderate_wr_beats_high_rr_low_wr(self):
        """
        Topstep-specific: high RR / low WR blows MLL more often
        and triggers consistency gate more often.
        Moderate WR + moderate RR wins on pass rate.
        """
        moderate = self._run(0.60, 250, 180, n=20_000)
        high_rr  = self._run(0.30, 1_400, 300, n=20_000)
        assert moderate.pass_rate > high_rr.pass_rate


# ══════════════════════════════════════════════════════════
# 5. Triple barrier labeling
# ══════════════════════════════════════════════════════════

def _make_synthetic_prices(n=500, seed=0) -> pd.DataFrame:
    """Generate synthetic OHLCV for testing."""
    rng = np.random.default_rng(seed)
    close = 5000 + np.cumsum(rng.normal(0, 10, n))
    noise = rng.uniform(2, 8, n)
    high  = close + noise
    low   = close - noise
    open_ = close - rng.normal(0, 3, n)
    idx   = pd.date_range("2023-01-02", periods=n, freq="B")
    return pd.DataFrame({"open": open_, "high": high, "low": low, "close": close}, index=idx)


class TestTripleBarrier:

    def test_labels_are_valid(self):
        prices  = _make_synthetic_prices()
        signals = np.arange(30, 450, 5)
        cfg     = BarrierConfig(pt_multiplier=2.0, sl_multiplier=1.0, max_holding_bars=10)
        labels  = label_triple_barrier(prices, signals, cfg)
        assert not labels.empty
        assert set(labels["label"].unique()).issubset({-1, 0, 1})

    def test_label_count_matches_valid_signals(self):
        prices  = _make_synthetic_prices()
        signals = np.arange(30, 480, 5)
        labels  = label_triple_barrier(prices, signals)
        # All signals before n-1 should produce a label
        valid   = signals[signals < len(prices) - 1]
        assert len(labels) == len(valid)

    def test_pnl_sign_matches_label(self):
        prices  = _make_synthetic_prices()
        signals = np.arange(40, 460, 8)
        labels  = label_triple_barrier(prices, signals, BarrierConfig(max_holding_bars=15))
        winners = labels[labels["label"] ==  1]
        losers  = labels[labels["label"] == -1]
        if len(winners) > 0:
            assert (winners["pnl_pct"] > 0).all()
        if len(losers) > 0:
            assert (losers["pnl_pct"] < 0).all()

    def test_extract_daily_pnl_returns_array(self):
        prices  = _make_synthetic_prices()
        signals = np.arange(30, 450, 5)
        labels  = label_triple_barrier(prices, signals)
        daily   = extract_daily_pnl_from_labels(labels, prices)
        assert isinstance(daily, np.ndarray)
        assert len(daily) > 0

    def test_walk_forward_produces_folds(self):
        prices = _make_synthetic_prices(n=800)

        def simple_signal_fn(train, test):
            """Every 5th bar in the test window."""
            return np.arange(5, len(test), 5)

        wf = walk_forward_validate(
            prices, simple_signal_fn,
            train_bars=200, test_bars=100, min_trades=5
        )
        assert len(wf) >= 2
        assert "win_rate" in wf.columns

    def test_statistical_summary_structure(self):
        wf_data = pd.DataFrame({
            "fold": [0, 1, 2, 3, 4],
            "n_trades": [50]*5,
            "win_rate": [0.55]*5,
            "avg_win":  [250]*5,
            "avg_loss": [200]*5,
            "rr":       [1.25]*5,
            "ev_per_trade": [30, 20, 40, 15, 35],
            "sharpe": [0.8]*5,
            "train_start": [None]*5,
            "test_start": [None]*5,
            "test_end": [None]*5,
        })
        s = statistical_summary(wf_data)
        assert "p_value_one_sided" in s
        assert "significant_5pct" in s
        assert s["p_value_one_sided"] < 0.05   # all positive EVs → significant


# ══════════════════════════════════════════════════════════
# 6. Minimum sample size calculation
# ══════════════════════════════════════════════════════════

class TestSampleSize:
    def test_minimum_sample_size(self):
        from simulation.grid_search import minimum_sample_size
        n = minimum_sample_size(target_pass_rate=0.50, margin=0.03)
        assert n > 1_000   # should be ~1_067

    def test_tighter_margin_requires_more(self):
        from simulation.grid_search import minimum_sample_size
        n_loose  = minimum_sample_size(0.50, margin=0.05)
        n_tight  = minimum_sample_size(0.50, margin=0.02)
        assert n_tight > n_loose


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
