import numpy as np
import pytest

from quant_allocator.simulator.manager import (
    ManagerConfig,
    effective_information_coefficient,
    simulate_manager,
)
from quant_allocator.simulator.market import MarketConfig, simulate_market


def test_ic_decays_with_half_life():
    cfg = ManagerConfig(information_coefficient=0.10, alpha_half_life_months=6.0)
    assert effective_information_coefficient(0.0, cfg) == 0.10
    assert np.isclose(effective_information_coefficient(6.0, cfg), 0.05)
    assert np.isclose(effective_information_coefficient(12.0, cfg), 0.025)


def test_gross_and_net_targets_hit_every_month():
    market = simulate_market(MarketConfig(n_assets=200, n_months=36, seed=2))
    hist = simulate_manager(market, ManagerConfig(seed=2))
    gross = hist.weights.abs().sum(axis=1)
    net = hist.weights.sum(axis=1)
    assert np.allclose(gross, 1.6, atol=1e-8)
    assert np.allclose(net, 0.2, atol=1e-8)


def test_skilled_manager_earns_more_true_alpha_than_unskilled():
    market = simulate_market(MarketConfig(n_assets=500, n_months=120, seed=5))
    skilled = simulate_manager(
        market, ManagerConfig(information_coefficient=0.15, seed=11)
    )
    unskilled = simulate_manager(
        market, ManagerConfig(information_coefficient=0.0, seed=11)
    )
    assert skilled.true_alpha_returns.mean() > unskilled.true_alpha_returns.mean()
    assert skilled.true_alpha_returns.mean() > 0


def test_turnover_matches_rebalance_fraction():
    market = simulate_market(MarketConfig(n_assets=300, n_months=48, seed=4))
    cfg = ManagerConfig(rebalance_fraction=0.25, seed=4)
    hist = simulate_manager(market, cfg)
    held = hist.weights != 0.0
    entry_fracs = []
    for t in range(1, len(held)):
        entries = (held.iloc[t] & ~held.iloc[t - 1]).sum()
        entry_fracs.append(entries / (cfg.n_long + cfg.n_short))
    assert abs(np.mean(entry_fracs) - 0.25) < 0.05


def test_rng_stream_tags_are_distinct():
    from quant_allocator.simulator import manager, market, returns_only

    tags = {
        market._MARKET_STREAM,
        manager._MANAGER_STREAM,
        returns_only._RETURNS_ONLY_STREAM,
        manager._SHORT_SIGNAL_STREAM,
        manager._EXIT_RANDOM_STREAM,
        market._LIQUIDITY_STREAM,
    }
    assert len(tags) == 6


def test_invalid_configs_raise():
    market_ = simulate_market(MarketConfig(n_assets=30, n_months=6, seed=1))
    for bad in (
        ManagerConfig(information_coefficient=1.5),
        ManagerConfig(sizing_discipline=-0.1),
        ManagerConfig(rebalance_fraction=0.0),
        ManagerConfig(n_long=20, n_short=20),
    ):
        with pytest.raises(ValueError):
            simulate_manager(market_, bad)


def test_sizing_discipline_adds_alpha():
    market_ = simulate_market(MarketConfig(n_assets=500, n_months=240, seed=6))
    sized = simulate_manager(
        market_, ManagerConfig(information_coefficient=0.10, sizing_discipline=1.0, seed=13)
    )
    equal = simulate_manager(
        market_, ManagerConfig(information_coefficient=0.10, sizing_discipline=0.0, seed=13)
    )
    assert sized.true_alpha_returns.mean() > equal.true_alpha_returns.mean()
