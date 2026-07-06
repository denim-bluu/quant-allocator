import numpy as np

from quant_allocator.flagships.tearsheet.pipeline import (
    DrawdownHypothesis,
    drawdown_band,
)


def test_band_is_ordered_and_contains_a_healthy_path():
    rng = np.random.default_rng(0)
    returns = rng.normal(0.01, 0.03, size=48)
    hyp = DrawdownHypothesis(sharpe_annual=1.0, vol_annual=0.03 * np.sqrt(12))
    band = drawdown_band(returns, hyp)
    assert len(band.realized) == 48
    # Envelope ordering: deeper percentiles are deeper drawdowns (more negative).
    assert np.all(band.p50 >= band.p95 - 1e-9)
    assert np.all(band.p95 >= band.p99 - 1e-9)
    assert band.breaches_p99 in (True, False)


def test_extreme_realized_drawdown_breaches_p99():
    rng = np.random.default_rng(1)
    returns = rng.normal(0.01, 0.02, size=60)
    returns[20:28] = -0.15  # an implausible crash under the benign hypothesis
    hyp = DrawdownHypothesis(sharpe_annual=1.5, vol_annual=0.02 * np.sqrt(12))
    band = drawdown_band(returns, hyp)
    assert band.breaches_p99 is True


def test_determinism_same_seed_same_band():
    rng = np.random.default_rng(2)
    returns = rng.normal(0.008, 0.03, size=48)
    hyp = DrawdownHypothesis(sharpe_annual=0.8, vol_annual=0.03 * np.sqrt(12))
    a = drawdown_band(returns, hyp, seed=99)
    b = drawdown_band(returns, hyp, seed=99)
    assert np.array_equal(a.p99, b.p99)
