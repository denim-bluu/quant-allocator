import numpy as np

from quant_allocator.flagships.tearsheet.pipeline import (
    MONTHS_PER_YEAR,
    alpha_interval,
    mppm,
    regress,
    sharpe_intervals,
)


def test_regress_recovers_planted_alpha_and_betas():
    rng = np.random.default_rng(0)
    T = 120
    factors = rng.normal(0.0, 0.04, size=(T, 4))
    betas = np.array([1.0, 0.3, -0.2, 0.4])
    excess = 0.006 + factors @ betas + rng.normal(0.0, 0.01, size=T)
    fit = regress(excess, factors, ("market", "size", "value", "momentum"))
    assert abs(fit.alpha_monthly - 0.006) < 0.004
    assert np.allclose(fit.betas, betas, atol=0.05)
    assert abs(fit.alpha_annual - fit.alpha_monthly * MONTHS_PER_YEAR) < 1e-12


def test_lo_sharpe_se_matches_closed_form():
    rng = np.random.default_rng(1)
    returns = rng.normal(0.01, 0.03, size=48)
    stats = sharpe_intervals(returns)
    sr_m = returns.mean() / returns.std(ddof=1)
    se_m = np.sqrt((1.0 + sr_m**2 / 2.0) / len(returns))
    assert np.isclose(stats.sharpe_annual, sr_m * np.sqrt(MONTHS_PER_YEAR), rtol=1e-9)
    assert np.isclose(stats.lo_se_annual, se_m * np.sqrt(MONTHS_PER_YEAR), rtol=1e-9)
    lo, hi = stats.lo_ci
    assert lo < stats.sharpe_annual < hi


def test_sharpe_excludes_zero_flag_matches_ci():
    rng = np.random.default_rng(2)
    strong = rng.normal(0.02, 0.02, size=120)  # high SR, long T
    weak = rng.normal(0.001, 0.05, size=24)  # near-zero SR, short T
    assert sharpe_intervals(strong).excludes_zero is True
    assert sharpe_intervals(weak).excludes_zero is False


def test_alpha_interval_crosses_zero_flag():
    rng = np.random.default_rng(4)
    T = 48
    factors = rng.normal(0.0, 0.04, size=(T, 4))
    # Alpha indistinguishable from zero at this T (the alt-beta case, S2 spec §3.5).
    excess = 0.0005 + factors @ np.array([1.0, 0.2, 0.1, 0.3]) + rng.normal(0.0, 0.02, size=T)
    fit = regress(excess, factors, ("market", "size", "value", "momentum"))
    stats = alpha_interval(fit)
    lo, hi = stats.ci
    assert lo <= 0.0 <= hi
    assert stats.crosses_zero is True


def test_mppm_penalizes_a_manipulated_tail():
    rng = np.random.default_rng(5)
    base = rng.normal(0.01, 0.02, size=240)
    rf = np.full(240, 0.02 / MONTHS_PER_YEAR)
    manipulated = base.copy()
    manipulated[::20] = -0.25  # sold-tail blow-ups: same-ish mean, fat left tail
    assert mppm(base, rf) > mppm(manipulated, rf)


def test_mppm_matches_hand_value_for_constant_excess():
    # Constant monthly excess g: MPPM annualizes to 12*log(1+g) (S2 spec §3.4).
    T = 36
    rf = np.full(T, 0.0)
    returns = np.full(T, 0.01)
    expected = MONTHS_PER_YEAR * np.log(1.01)
    assert np.isclose(mppm(returns, rf), expected, rtol=1e-9)
