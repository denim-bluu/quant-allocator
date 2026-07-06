import numpy as np

from quant_allocator.flagships.tearsheet.pipeline import THETA0_SKIP, unsmooth


def _smooth(true_returns, theta):
    # Observed = theta0*r_t + theta1*r_{t-1} + theta2*r_{t-2} (S2 spec §3.1).
    obs = np.full_like(true_returns, np.nan)
    for t in range(len(true_returns)):
        acc = theta[0] * true_returns[t]
        if t >= 1:
            acc += theta[1] * true_returns[t - 1]
        if t >= 2:
            acc += theta[2] * true_returns[t - 2]
        obs[t] = acc
    return obs[2:]  # drop warm-up months with incomplete kernel


def test_recovers_injected_theta_within_tolerance():
    rng = np.random.default_rng(7)
    true_returns = rng.normal(0.008, 0.03, size=600)
    injected = np.array([0.6, 0.3, 0.1])
    observed = _smooth(true_returns, injected)
    result = unsmooth(observed)
    assert result.applied is True
    assert np.allclose(result.theta.sum(), 1.0, atol=1e-6)
    assert np.all(result.theta >= -1e-9)
    # Recovery within tolerance (MLE on a finite sample).
    assert np.allclose(result.theta, injected, atol=0.08)


def test_desmoothed_vol_is_larger_than_observed_vol():
    rng = np.random.default_rng(11)
    true_returns = rng.normal(0.008, 0.03, size=400)
    observed = _smooth(true_returns, np.array([0.5, 0.3, 0.2]))
    result = unsmooth(observed)
    assert result.vol_ratio < 1.0  # sqrt(sum theta^2) <= 1
    assert observed.std(ddof=1) / result.vol_ratio > observed.std(ddof=1)
    assert np.isclose(result.desmoothed.std(ddof=1), observed.std(ddof=1) / result.vol_ratio, rtol=0.02)


def test_skips_when_no_material_smoothing():
    rng = np.random.default_rng(3)
    clean = rng.normal(0.008, 0.03, size=200)  # theta0 ~ 1 => skip
    result = unsmooth(clean)
    assert result.applied is False
    assert result.skip_reason is not None
    assert np.allclose(result.theta, [1.0, 0.0, 0.0])
    assert np.allclose(result.desmoothed, clean)
    assert result.theta[0] >= THETA0_SKIP  # sanity: skip path leaves inputs untouched
