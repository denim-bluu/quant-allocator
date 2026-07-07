import pandas as pd
import pytest

from quant_allocator.simulator.manager import ManagerConfig, simulate_manager
from quant_allocator.simulator.market import MarketConfig, simulate_market


def _market(n_months: int = 60, seed: int = 3):
    return simulate_market(MarketConfig(n_assets=300, n_months=n_months, seed=seed))


def test_death_none_matches_beyond_horizon_no_op():
    market = _market(n_months=48)
    cfg = ManagerConfig(information_coefficient=0.15, seed=7)
    honest = simulate_manager(market, cfg)
    # death at/after the horizon can never fire -> byte-identical to the honest run.
    beyond = simulate_manager(market, ManagerConfig(information_coefficient=0.15, seed=7, death_month=48))
    pd.testing.assert_frame_equal(honest.weights, beyond.weights)


def test_predeath_weights_are_byte_identical_to_honest():
    # The RNG (noise) is pre-drawn once; death only zeroes ic_eff from month k on,
    # so every month before k selects and sizes identically to the honest manager.
    market = _market(n_months=60)
    k = 30
    honest = simulate_manager(market, ManagerConfig(information_coefficient=0.15, seed=9))
    dying = simulate_manager(
        market, ManagerConfig(information_coefficient=0.15, seed=9, death_month=k)
    )
    pd.testing.assert_frame_equal(honest.weights.iloc[:k], dying.weights.iloc[:k])


def test_alpha_dies_after_death_month():
    market = _market(n_months=120, seed=5)
    k = 60
    dying = simulate_manager(
        market, ManagerConfig(information_coefficient=0.20, seed=11, death_month=k)
    )
    pre = dying.true_alpha_returns.iloc[:k].mean()
    post = dying.true_alpha_returns.iloc[k:].mean()
    assert pre > 0
    assert post < pre  # skill is gone after death; post-k alpha collapses toward zero


def test_negative_death_month_raises():
    market = _market(n_months=24)
    with pytest.raises(ValueError, match="death_month"):
        simulate_manager(market, ManagerConfig(death_month=-1))
