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


def test_hit_rate_month_clustered_detection():
    # D-9 gate ruling 2026-07-07: the t-test runs on monthly hit fractions h_t.
    # A persistent 60% monthly hit rate over 100 months is detected; pure coin-flip
    # months are not.
    rng = np.random.default_rng(4)
    n_months, n_positions = 100, 65
    skilled = np.where(rng.random((n_months, n_positions)) < 0.60, 1.0, -1.0)
    est = hit_rate(skilled, gate_quantity=1985.0)
    assert abs(est.point - (skilled > 0).mean()) < 1e-9  # point = pooled p_hat
    assert est.detected is True
    coin_flip = np.where(rng.random((n_months, n_positions)) < 0.50, 1.0, -1.0)
    assert hit_rate(coin_flip, gate_quantity=1985.0).detected is False


def test_hit_rate_clusters_by_month_and_ignores_gate_quantity():
    # Cross-positionally correlated months (every position wins or loses together)
    # must NOT be detected: only ~half the MONTHS are up, however many positions
    # each month holds. A pooled binomial on 6000 observations would fire here.
    rng = np.random.default_rng(5)
    month_signs = np.where(rng.random(100) < 0.5, 1.0, -1.0)
    correlated = np.tile(month_signs[:, None], (1, 60))
    assert hit_rate(correlated, gate_quantity=1985.0).detected is False
    # gate_quantity labels the gate axis only — it must not move the test.
    a = hit_rate(correlated, gate_quantity=50.0)
    b = hit_rate(correlated, gate_quantity=5000.0)
    assert a.se == b.se and a.tstat == b.tstat and a.detected == b.detected


def test_hit_rate_degenerate_inputs_do_not_detect():
    # Fewer than 2 nonzero months -> no clustered variance -> never detect.
    one_month = np.array([[1.0, 1.0, -1.0]])
    est = hit_rate(one_month, gate_quantity=10.0)
    assert est.detected is False and est.se == 0.0
    all_zero = np.zeros((12, 5))
    est_zero = hit_rate(all_zero, gate_quantity=10.0)
    assert est_zero.point == 0.5 and est_zero.detected is False


def test_sizing_slope_fama_macbeth_detects_positive_relationship():
    # RULING 7: per-month cross-sectional slopes b_t, time-series t on mean(b_t).
    rng = np.random.default_rng(3)
    n_months, n_positions = 60, 50
    sizes = rng.uniform(0.01, 0.05, size=(n_months, n_positions))
    contributions = 0.4 * sizes + rng.normal(0.0, 0.002, size=(n_months, n_positions))
    est = sizing_slope(sizes, contributions)
    assert abs(est.point - 0.4) < 0.1  # displayed point = mean(b_t), near the true slope
    assert est.tstat > DETECT_Z
    assert est.detected is True
    noise = rng.normal(0.0, 0.002, size=(n_months, n_positions))
    assert sizing_slope(sizes, noise).detected is False


def test_sizing_slope_month_clustered_noise_is_not_detected():
    # A within-month common shock scaled by |size| inflates the POOLED OLS t but
    # must not fool the Fama-MacBeth test: b_t is just the (zero-mean) shock series.
    rng = np.random.default_rng(7)
    n_months, n_positions = 120, 50
    sizes = rng.uniform(0.01, 0.05, size=(n_months, n_positions))
    month_shock = rng.normal(0.0, 0.05, size=(n_months, 1))
    contributions = sizes * month_shock  # per-month slope = shock, mean 0
    assert sizing_slope(sizes, contributions).detected is False


def test_sizing_slope_guards_degenerate_cross_sections():
    # Equal |size| within every month (sizing_discipline=0 shape): no usable
    # cross-sectional regression -> t=0, never detect.
    sizes = np.full((24, 40), 0.025)
    contributions = np.random.default_rng(8).normal(0.0, 0.01, size=(24, 40))
    est = sizing_slope(sizes, contributions)
    assert est.detected is False and est.tstat == 0.0
    # Fewer than 3 usable months -> same guard.
    tiny_sizes = np.array([[0.01, 0.02, 0.03], [0.01, 0.02, 0.03]])
    tiny_contrib = np.array([[0.001, -0.002, 0.003], [0.0, 0.001, -0.001]])
    assert sizing_slope(tiny_sizes, tiny_contrib).detected is False
