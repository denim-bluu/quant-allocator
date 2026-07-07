import numpy as np
import pandas as pd
import pytest
from scipy import stats

from quant_allocator.flagships.tearsheet.pipeline import _invert_ma2
from quant_allocator.simulator.overlays import (
    SmoothingOverlay,
    WrittenPutOverlay,
    apply_smoothing_overlay,
    apply_written_put_overlay,
)


def _market_factor(n_months: int = 240, seed: int = 0) -> pd.Series:
    rng = np.random.default_rng([seed, 99])
    idx = pd.period_range("2000-01", periods=n_months, freq="M", name="month")
    # Monthly market-factor draws ~ N(0.06/12, (0.16/sqrt(12))^2), matching MarketConfig.
    return pd.Series(rng.normal(0.06 / 12.0, 0.16 / np.sqrt(12.0), n_months), index=idx)


def _returns(mkt: pd.Series, seed: int = 1) -> pd.Series:
    rng = np.random.default_rng([seed, 98])
    return pd.Series(rng.normal(0.005, 0.02, len(mkt)), index=mkt.index, name="mgr")


def test_kappa_zero_recovers_input_series_byte_identical():
    mkt = _market_factor()
    base = _returns(mkt)
    overlay = WrittenPutOverlay(strike_moneyness=1.0, overlay_notional=0.0)
    result = apply_written_put_overlay(base, mkt, overlay)
    pd.testing.assert_series_equal(result, base)


def test_fair_premium_preserves_sample_mean():
    mkt = _market_factor()
    base = _returns(mkt)
    overlay = WrittenPutOverlay(strike_moneyness=1.0, overlay_notional=0.5)
    result = apply_written_put_overlay(base, mkt, overlay)
    # Fair premium zeroes the overlay's realized sample-mean contribution exactly.
    assert np.isclose(result.mean(), base.mean(), atol=1e-12)


def test_overlay_fattens_left_tail():
    mkt = _market_factor()
    base = _returns(mkt)
    overlay = WrittenPutOverlay(strike_moneyness=1.0, overlay_notional=0.8)
    result = apply_written_put_overlay(base, mkt, overlay)
    assert result.min() < base.min()
    assert stats.skew(result.to_numpy()) < stats.skew(base.to_numpy())


def test_recovers_injected_notional():
    mkt = _market_factor()
    base = _returns(mkt)
    kappa = 0.6
    overlay = WrittenPutOverlay(strike_moneyness=1.0, overlay_notional=kappa)
    result = apply_written_put_overlay(base, mkt, overlay)
    sigma = float(mkt.std())
    strike = -1.0 * sigma
    payoff = np.maximum(strike - mkt.to_numpy(), 0.0)
    expected = base.to_numpy() + kappa * payoff.mean() - kappa * payoff
    np.testing.assert_allclose(result.to_numpy(), expected, atol=1e-12)


def test_flat_premium_when_fair_disabled():
    mkt = _market_factor()
    base = _returns(mkt)
    overlay = WrittenPutOverlay(
        strike_moneyness=1.0, overlay_notional=0.5, premium_annual=0.12, fair_premium=False
    )
    result = apply_written_put_overlay(base, mkt, overlay)
    sigma = float(mkt.std())
    payoff = np.maximum(-1.0 * sigma - mkt.to_numpy(), 0.0)
    expected = base.to_numpy() + 0.12 / 12.0 - 0.5 * payoff
    np.testing.assert_allclose(result.to_numpy(), expected, atol=1e-12)


def test_deeper_moneyness_weakens_the_tail_monotonically():
    # Deeper-OTM strikes pay off less often and less deeply: the worst month
    # and the total payout must both shrink monotonically in strike_moneyness.
    mkt = _market_factor()
    base = _returns(mkt)
    kappa = 0.8
    mins, payouts = [], []
    for moneyness in (0.5, 1.0, 2.0):
        overlay = WrittenPutOverlay(strike_moneyness=moneyness, overlay_notional=kappa)
        result = apply_written_put_overlay(base, mkt, overlay)
        mins.append(float(result.min()))
        strike = -moneyness * float(mkt.std())
        payouts.append(float(np.maximum(strike - mkt.to_numpy(), 0.0).sum()))
    assert mins[0] <= mins[1] <= mins[2]  # shallower strike => worse worst-month
    assert payouts[0] > payouts[1] > payouts[2]  # strictly less total payoff deeper OTM


def test_invalid_overlays_raise():
    mkt = _market_factor(n_months=24)
    base = _returns(mkt)
    with pytest.raises(ValueError, match="overlay_notional"):
        apply_written_put_overlay(base, mkt, WrittenPutOverlay(1.0, -0.1))
    with pytest.raises(ValueError, match="strike_moneyness"):
        apply_written_put_overlay(base, mkt, WrittenPutOverlay(-1.0, 0.5))
    misaligned = base.reset_index(drop=True)
    with pytest.raises(ValueError, match="share an index"):
        apply_written_put_overlay(misaligned, mkt, WrittenPutOverlay(1.0, 0.5))


def _iid_returns(n_months: int = 240, seed: int = 5) -> pd.Series:
    rng = np.random.default_rng([seed, 97])
    idx = pd.period_range("2000-01", periods=n_months, freq="M", name="month")
    return pd.Series(rng.normal(0.005, 0.02, n_months), index=idx, name="mgr")


def _lag1_autocorr(x: np.ndarray) -> float:
    c = x - x.mean()
    return float(c[1:] @ c[:-1] / (c @ c))


def test_identity_theta_recovers_input_series_byte_identical():
    base = _iid_returns()
    result = apply_smoothing_overlay(base, SmoothingOverlay(theta=(1.0, 0.0, 0.0)))
    pd.testing.assert_series_equal(result, base)


def test_smoothing_injects_positive_lag1_autocorrelation():
    base = _iid_returns()
    result = apply_smoothing_overlay(base, SmoothingOverlay(theta=(0.60, 0.25, 0.15)))
    # An iid series has ~zero lag-1 autocorr; the MA(2) kernel injects a positive one
    # (the Getmansky-Lo-Makarov illiquidity-marking confound S6 stresses).
    assert abs(_lag1_autocorr(base.to_numpy())) < 0.15
    assert _lag1_autocorr(result.to_numpy()) > 0.20


def test_recovers_injected_kernel_known_values():
    base = _iid_returns(n_months=6)
    theta = (0.60, 0.25, 0.15)
    result = apply_smoothing_overlay(base, SmoothingOverlay(theta=theta))
    r = base.to_numpy()
    expected = theta[0] * r.copy()
    expected[1:] += theta[1] * r[:-1]
    expected[2:] += theta[2] * r[:-2]
    np.testing.assert_allclose(result.to_numpy(), expected, atol=1e-12)


def test_convention_is_inverse_of_s2_unsmoother():
    # The overlay smooths; the S2 stage's causal deconvolution _invert_ma2 unsmooths.
    # On centered returns with the same theta they are exact inverses (S6 sec 8.2).
    base = _iid_returns()
    theta = np.array([0.60, 0.25, 0.15])
    centered = base - base.mean()
    smoothed = apply_smoothing_overlay(centered, SmoothingOverlay(theta=tuple(theta)))
    recovered = _invert_ma2(smoothed.to_numpy(), theta)
    np.testing.assert_allclose(recovered, centered.to_numpy(), atol=1e-9)


def test_invalid_smoothing_overlays_raise():
    base = _iid_returns(n_months=24)
    with pytest.raises(ValueError, match="sum to 1"):
        apply_smoothing_overlay(base, SmoothingOverlay(theta=(0.8, 0.1, 0.05)))
    with pytest.raises(ValueError, match="non-negative"):
        apply_smoothing_overlay(base, SmoothingOverlay(theta=(1.2, -0.1, -0.1)))
