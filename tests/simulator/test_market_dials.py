import numpy as np
import pandas as pd
import pytest

from quant_allocator.simulator.market import MarketConfig, simulate_market


def test_ar1_zero_is_byte_identical():
    base = simulate_market(MarketConfig(n_assets=120, n_months=60, seed=3))
    off = simulate_market(MarketConfig(n_assets=120, n_months=60, seed=3, idio_ar1=0.0))
    pd.testing.assert_frame_equal(base.idio_returns, off.idio_returns)
    pd.testing.assert_frame_equal(base.factor_returns, off.factor_returns)
    pd.testing.assert_frame_equal(base.betas, off.betas)


def test_ar1_injects_persistence_and_preserves_variance():
    rho = 0.4
    base = simulate_market(MarketConfig(n_assets=400, n_months=600, seed=3))
    dialed = simulate_market(MarketConfig(n_assets=400, n_months=600, seed=3, idio_ar1=rho))
    idio = dialed.idio_returns.to_numpy()
    ac1 = np.mean([
        (lambda c: c[1:] @ c[:-1] / (c @ c))(idio[:, j] - idio[:, j].mean())
        for j in range(idio.shape[1])
    ])
    assert abs(ac1 - rho) < 0.05
    # Stationary marginal variance preserved vs the rho=0 innovations.
    assert np.isclose(idio.std(), base.idio_returns.to_numpy().std(), rtol=0.05)


def test_ar1_out_of_band_raises():
    with pytest.raises(ValueError, match="idio_ar1"):
        simulate_market(MarketConfig(idio_ar1=1.0))
    with pytest.raises(ValueError, match="idio_ar1"):
        simulate_market(MarketConfig(idio_ar1=-1.5))


def test_adv_dollar_is_byte_identical_to_pre_adv_generator():
    # The ADV vector draws on its own stream, so every stream-0 frame is unchanged.
    base = simulate_market(MarketConfig(n_assets=120, n_months=60, seed=3))
    explicit = simulate_market(
        MarketConfig(n_assets=120, n_months=60, seed=3, adv_dollar_range=(2e6, 5e8))
    )
    pd.testing.assert_frame_equal(base.idio_returns, explicit.idio_returns)
    pd.testing.assert_frame_equal(base.factor_returns, explicit.factor_returns)
    pd.testing.assert_frame_equal(base.betas, explicit.betas)


def test_adv_dollar_range_does_not_perturb_the_market_stream():
    # A different ADV range must not move any stream-0 draw (separate generator).
    wide = simulate_market(MarketConfig(n_assets=120, n_months=60, seed=3))
    narrow = simulate_market(
        MarketConfig(n_assets=120, n_months=60, seed=3, adv_dollar_range=(1e7, 1e7))
    )
    pd.testing.assert_frame_equal(wide.idio_returns, narrow.idio_returns)


def test_adv_dollar_is_within_range_and_seed_reproducible():
    m = simulate_market(MarketConfig(n_assets=400, n_months=12, seed=3))
    adv = m.adv_dollar
    assert list(adv.index) == list(m.betas.index)
    assert (adv >= 2e6).all() and (adv <= 5e8).all()
    again = simulate_market(MarketConfig(n_assets=400, n_months=12, seed=3))
    pd.testing.assert_series_equal(adv, again.adv_dollar)


def test_adv_dollar_range_out_of_band_raises():
    with pytest.raises(ValueError, match="adv_dollar_range"):
        simulate_market(MarketConfig(adv_dollar_range=(5e8, 2e6)))  # low > high
    with pytest.raises(ValueError, match="adv_dollar_range"):
        simulate_market(MarketConfig(adv_dollar_range=(-1.0, 5e8)))  # non-positive


def test_eligible_default_is_all_true_and_byte_identical():
    base = simulate_market(MarketConfig(n_assets=120, n_months=24, seed=3))
    explicit = simulate_market(
        MarketConfig(n_assets=120, n_months=24, seed=3, ineligible_asset_fraction=0.0)
    )
    assert base.eligible.all()
    assert list(base.eligible.index) == list(base.betas.index)
    pd.testing.assert_frame_equal(base.idio_returns, explicit.idio_returns)
    pd.testing.assert_series_equal(base.eligible, explicit.eligible)


def test_eligible_fraction_marks_expected_count_deterministically():
    m = simulate_market(MarketConfig(n_assets=100, n_months=12, seed=3, ineligible_asset_fraction=0.3))
    assert (~m.eligible).sum() == 30
    again = simulate_market(
        MarketConfig(n_assets=100, n_months=12, seed=3, ineligible_asset_fraction=0.3)
    )
    pd.testing.assert_series_equal(m.eligible, again.eligible)
    # A different eligibility fraction must not perturb the stream-0 market draws.
    pd.testing.assert_frame_equal(m.idio_returns, again.idio_returns)


def test_ineligible_fraction_out_of_band_raises():
    with pytest.raises(ValueError, match="ineligible_asset_fraction"):
        simulate_market(MarketConfig(ineligible_asset_fraction=1.0))
    with pytest.raises(ValueError, match="ineligible_asset_fraction"):
        simulate_market(MarketConfig(ineligible_asset_fraction=-0.1))
