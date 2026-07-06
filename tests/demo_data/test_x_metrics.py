import numpy as np

from quant_allocator.demo_data.x_metrics import (
    DETECT_Z,
    MONTHS_PER_YEAR,
    hit_rate,
    ols_alpha,
    pinned_alpha,
    sharpe_lo,
    sizing_slope,
)


def test_ols_alpha_recovers_intercept_and_detects_strong_signal():
    rng = np.random.default_rng(0)
    T = 120
    factors = rng.normal(0.0, 0.04, size=(T, 4))
    betas = np.array([1.0, 0.2, -0.1, 0.3])
    returns = 0.01 + factors @ betas + rng.normal(0.0, 0.008, size=T)
    est = ols_alpha(returns, factors, true_alpha=0.12)
    assert abs(est.point - 0.12) < 0.04  # annualized ~0.01*12
    assert est.detected is True
    assert est.se > 0.0


def test_pinned_alpha_is_true_alpha_when_betas_known():
    rng = np.random.default_rng(1)
    T = 60
    factors = rng.normal(0.0, 0.04, size=(T, 4))
    betas_path = np.tile([1.0, 0.2, -0.1, 0.3], (T, 1))
    idio = rng.normal(0.004, 0.01, size=T)
    returns = (factors * betas_path).sum(axis=1) + idio
    est = pinned_alpha(returns, betas_path, factors, true_alpha=idio.mean() * MONTHS_PER_YEAR)
    # Pinning true betas isolates the idio (true-alpha) stream exactly.
    assert np.isclose(est.point, idio.mean() * MONTHS_PER_YEAR, rtol=1e-9)


def test_sharpe_lo_detection_flags_track_length():
    rng = np.random.default_rng(2)
    strong = rng.normal(0.02, 0.02, size=120)
    weak = rng.normal(0.001, 0.05, size=24)
    assert sharpe_lo(strong).detected is True
    assert sharpe_lo(weak).detected is False


def test_hit_rate_binomial_detection():
    contributions = np.array([1.0] * 470 + [-1.0] * 330)  # 58.75% hits, n large
    est = hit_rate(contributions, n_trades=800)
    assert abs(est.point - 0.5875) < 1e-9
    assert est.detected is True
    flat = np.array([1.0] * 405 + [-1.0] * 395)  # ~50.6%, indistinguishable
    assert hit_rate(flat, n_trades=800).detected is False


def test_sizing_slope_detects_positive_relationship():
    rng = np.random.default_rng(3)
    sizes = rng.uniform(0.01, 0.05, size=500)
    contributions = 0.4 * sizes + rng.normal(0.0, 0.002, size=500)  # bigger bets earn more
    est = sizing_slope(sizes, contributions)
    assert est.tstat > DETECT_Z
    assert est.detected is True
    noise = rng.normal(0.0, 0.002, size=500)
    assert sizing_slope(sizes, noise).detected is False
