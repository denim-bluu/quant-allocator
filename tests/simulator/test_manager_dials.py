import numpy as np
import pandas as pd
import pytest

from quant_allocator.simulator.manager import ManagerConfig, NetBetaDrift, simulate_manager
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
    # Skill is GONE, not merely reduced: post-death selection is pure noise, so
    # the post-k alpha must collapse toward zero, not just shrink (review note).
    assert abs(post) < pre / 4


def test_negative_death_month_raises():
    market = _market(n_months=24)
    with pytest.raises(ValueError, match="death_month"):
        simulate_manager(market, ManagerConfig(death_month=-1))


def test_drift_none_matches_zero_walk_no_op():
    market = _market(n_months=48)
    honest = simulate_manager(market, ManagerConfig(information_coefficient=0.1, seed=4))
    zero_walk = simulate_manager(
        market,
        ManagerConfig(
            information_coefficient=0.1,
            seed=4,
            net_drift=NetBetaDrift(total_walk=0.0, ramp_months=12),
        ),
    )
    pd.testing.assert_frame_equal(honest.weights, zero_walk.weights)


def test_net_exposure_walks_linearly():
    market = _market(n_months=48)
    base_net = 0.10
    walk = 0.35  # DEMO_DRIFT_WALK 0.10 -> 0.45 (M1 constants table)  # NUMERICS-GATE magnitude
    ramp = 12
    hist = simulate_manager(
        market,
        ManagerConfig(
            information_coefficient=0.1,
            target_net=base_net,
            seed=4,
            net_drift=NetBetaDrift(total_walk=walk, ramp_months=ramp),
        ),
    )
    realized_net = hist.weights.sum(axis=1).to_numpy()
    t = np.arange(len(realized_net), dtype=float)
    expected_net = base_net + walk * np.clip(t / ramp, 0.0, 1.0)
    np.testing.assert_allclose(realized_net, expected_net, atol=1e-8)


def test_drift_leaves_gross_unchanged():
    market = _market(n_months=48)
    hist = simulate_manager(
        market,
        ManagerConfig(
            information_coefficient=0.1,
            target_net=0.10,
            seed=4,
            net_drift=NetBetaDrift(total_walk=0.35, ramp_months=12),
        ),
    )
    gross = hist.weights.abs().sum(axis=1)
    assert np.allclose(gross, 1.6, atol=1e-8)


def test_pre_onset_weights_are_byte_identical_to_honest():
    # Drift only rescales side totals from onset on; before onset the book is the
    # honest manager exactly (same selection, same RNG).
    market = _market(n_months=60)
    onset = 24
    honest = simulate_manager(
        market, ManagerConfig(information_coefficient=0.1, target_net=0.10, seed=8)
    )
    drifting = simulate_manager(
        market,
        ManagerConfig(
            information_coefficient=0.1,
            target_net=0.10,
            seed=8,
            net_drift=NetBetaDrift(total_walk=0.35, ramp_months=12, onset_month=onset),
        ),
    )
    pd.testing.assert_frame_equal(honest.weights.iloc[:onset], drifting.weights.iloc[:onset])


def test_drift_out_of_band_raises():
    market = _market(n_months=24)
    with pytest.raises(ValueError, match="drifted net"):
        # base 0.2 + walk 1.6 = 1.8 >= target_gross 1.6 -> short side would go non-positive.
        simulate_manager(
            market,
            ManagerConfig(seed=1, net_drift=NetBetaDrift(total_walk=1.6, ramp_months=12)),
        )


def test_drift_bad_ramp_raises():
    market = _market(n_months=24)
    with pytest.raises(ValueError, match="ramp_months"):
        simulate_manager(
            market,
            ManagerConfig(seed=1, net_drift=NetBetaDrift(total_walk=0.2, ramp_months=0)),
        )
