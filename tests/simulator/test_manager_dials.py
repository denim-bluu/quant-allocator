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


def test_alpha_persistence_zero_is_byte_identical():
    market = _market(n_months=120)
    base = simulate_manager(market, ManagerConfig(information_coefficient=0.10, seed=7))
    off = simulate_manager(
        market, ManagerConfig(information_coefficient=0.10, seed=7, alpha_persistence=0.0)
    )
    pd.testing.assert_frame_equal(base.weights, off.weights)
    pd.testing.assert_series_equal(base.true_alpha_returns, off.true_alpha_returns)
    pd.testing.assert_series_equal(base.monthly_returns, off.monthly_returns)


def test_alpha_persistence_leaves_weights_but_lifts_realized_alpha():
    market = _market(n_months=120, seed=5)
    base = simulate_manager(market, ManagerConfig(information_coefficient=0.10, seed=7))
    persist = simulate_manager(
        market, ManagerConfig(information_coefficient=0.10, seed=7, alpha_persistence=0.5)
    )
    # Selection/sizing read the ORIGINAL idio, so weights are byte-identical...
    pd.testing.assert_frame_equal(base.weights, persist.weights)
    # ...but held names now earn a side-aligned decaying edge -> more realized alpha.
    assert persist.true_alpha_returns.mean() > base.true_alpha_returns.mean()


def test_negative_alpha_persistence_raises():
    market = _market(n_months=24)
    with pytest.raises(ValueError, match="alpha_persistence"):
        simulate_manager(market, ManagerConfig(alpha_persistence=-0.1))


def test_short_ic_none_is_byte_identical():
    market = _market(n_months=120)
    base = simulate_manager(market, ManagerConfig(information_coefficient=0.10, seed=7))
    off = simulate_manager(
        market,
        ManagerConfig(information_coefficient=0.10, seed=7, short_information_coefficient=None),
    )
    pd.testing.assert_frame_equal(base.weights, off.weights)
    pd.testing.assert_series_equal(base.true_alpha_returns, off.true_alpha_returns)


def test_short_ic_zero_makes_short_side_a_noise_basket():
    # long IC high, short IC 0 -> the SHORT sleeve earns no idiosyncratic edge while the
    # long sleeve keeps its skill. Compare the short-sleeve realized idio alpha.
    market = _market(n_months=240, seed=5)
    skilled_short = simulate_manager(
        market,
        ManagerConfig(information_coefficient=0.10, seed=7, short_information_coefficient=0.10),
    )
    noise_short = simulate_manager(
        market,
        ManagerConfig(information_coefficient=0.10, seed=7, short_information_coefficient=0.0),
    )
    def short_alpha(h):
        return (h.weights.clip(upper=0.0) * market.idio_returns).sum(axis=1).mean()

    assert short_alpha(skilled_short) > short_alpha(noise_short)


def test_short_ic_draws_a_decorrelated_panel_not_the_long_one():
    # A set short IC equal to the long IC still differs from the single-panel manager,
    # because the short side now reads an INDEPENDENT noise panel (stream tag 4), not
    # the long panel -> the book changes even though the two ICs match.
    market = _market(n_months=120)
    single = simulate_manager(market, ManagerConfig(information_coefficient=0.10, seed=7))
    split = simulate_manager(
        market,
        ManagerConfig(information_coefficient=0.10, seed=7, short_information_coefficient=0.10),
    )
    assert not single.weights.equals(split.weights)


def test_short_ic_out_of_band_raises():
    market = _market(n_months=24)
    with pytest.raises(ValueError, match="short_information_coefficient"):
        simulate_manager(market, ManagerConfig(short_information_coefficient=1.5))
    with pytest.raises(ValueError, match="short_information_coefficient"):
        simulate_manager(market, ManagerConfig(short_information_coefficient=-0.1))


def test_exit_style_age_is_byte_identical():
    market = _market(n_months=120)
    base = simulate_manager(market, ManagerConfig(information_coefficient=0.10, seed=7))
    aged = simulate_manager(
        market, ManagerConfig(information_coefficient=0.10, seed=7, exit_style="age")
    )
    pd.testing.assert_frame_equal(base.weights, aged.weights)
    pd.testing.assert_series_equal(base.true_alpha_returns, aged.true_alpha_returns)


def test_active_exit_styles_change_the_book():
    market = _market(n_months=120)
    base = simulate_manager(market, ManagerConfig(information_coefficient=0.10, seed=7))
    for style in ("signal", "disposition", "random"):
        alt = simulate_manager(
            market, ManagerConfig(information_coefficient=0.10, seed=7, exit_style=style)
        )
        assert not base.weights.equals(alt.weights)


def test_exit_random_is_seed_reproducible_and_consumes_its_stream():
    market = _market(n_months=120)
    a = simulate_manager(
        market, ManagerConfig(information_coefficient=0.10, seed=7, exit_style="random")
    )
    b = simulate_manager(
        market, ManagerConfig(information_coefficient=0.10, seed=7, exit_style="random")
    )
    pd.testing.assert_frame_equal(a.weights, b.weights)  # deterministic given seed + tag
    c = simulate_manager(
        market, ManagerConfig(information_coefficient=0.10, seed=8, exit_style="random")
    )
    assert not a.weights.equals(c.weights)  # a different seed draws different exits


def test_signal_exit_beats_disposition_under_persistence():
    # S4 ground truth: under idio persistence, selling the lowest-signal incumbents
    # (disciplined) retains names whose edge still pays, while selling trailing winners
    # (disposition) forgoes forward alpha -> signal earns more realized true alpha.
    market = simulate_market(MarketConfig(n_assets=300, n_months=240, seed=5, idio_ar1=0.4))
    signal = simulate_manager(
        market, ManagerConfig(information_coefficient=0.10, seed=11, exit_style="signal")
    )
    dispo = simulate_manager(
        market, ManagerConfig(information_coefficient=0.10, seed=11, exit_style="disposition")
    )
    assert signal.true_alpha_returns.mean() > dispo.true_alpha_returns.mean()


def test_bad_exit_style_raises():
    market = _market(n_months=24)
    with pytest.raises(ValueError, match="exit_style"):
        simulate_manager(market, ManagerConfig(exit_style="bogus"))


def test_crowd_participation_zero_is_byte_identical():
    market = _market(n_months=120)
    base = simulate_manager(market, ManagerConfig(information_coefficient=0.10, seed=7))
    off = simulate_manager(
        market, ManagerConfig(information_coefficient=0.10, seed=7, crowd_participation=0.0)
    )
    pd.testing.assert_frame_equal(base.weights, off.weights)
    pd.testing.assert_series_equal(base.true_alpha_returns, off.true_alpha_returns)
    pd.testing.assert_series_equal(base.monthly_returns, off.monthly_returns)


def test_crowd_participation_shared_seed_correlates_two_managers():
    # Two managers on the same market, same crowd_seed, high participation: their books
    # overlap far more than two independent managers (the ground-truth crowding M4 reads).
    market = _market(n_months=240, seed=5)
    indep_a = simulate_manager(market, ManagerConfig(information_coefficient=0.10, seed=1))
    indep_b = simulate_manager(market, ManagerConfig(information_coefficient=0.10, seed=2))
    crowd_a = simulate_manager(
        market,
        ManagerConfig(information_coefficient=0.10, seed=1, crowd_participation=0.8, crowd_seed=99),
    )
    crowd_b = simulate_manager(
        market,
        ManagerConfig(information_coefficient=0.10, seed=2, crowd_participation=0.8, crowd_seed=99),
    )

    def held_overlap(x, y):  # mean fraction of long names co-held month by month
        lx = x.weights > 0.0
        ly = y.weights > 0.0
        both = (lx & ly).sum(axis=1)
        either = (lx | ly).sum(axis=1).replace(0, np.nan)
        return float((both / either).mean())

    assert held_overlap(crowd_a, crowd_b) > held_overlap(indep_a, indep_b)


def test_crowd_participation_changes_the_book_but_not_the_stream_of_others():
    market = _market(n_months=120)
    base = simulate_manager(market, ManagerConfig(information_coefficient=0.10, seed=7))
    crowded = simulate_manager(
        market,
        ManagerConfig(information_coefficient=0.10, seed=7, crowd_participation=0.5, crowd_seed=1),
    )
    assert not base.weights.equals(crowded.weights)


def test_crowd_participation_out_of_band_raises():
    market = _market(n_months=24)
    with pytest.raises(ValueError, match="crowd_participation"):
        simulate_manager(market, ManagerConfig(crowd_participation=1.5))
    with pytest.raises(ValueError, match="crowd_participation"):
        simulate_manager(market, ManagerConfig(crowd_participation=-0.1))
