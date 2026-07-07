import numpy as np
import pandas as pd
import pytest
from scipy import stats

from quant_allocator.simulator.overlays import (
    WrittenPutOverlay,
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
