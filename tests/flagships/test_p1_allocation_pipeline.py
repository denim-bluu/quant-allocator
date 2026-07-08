import numpy as np

from quant_allocator.flagships.allocation import pipeline as ap


def test_config_carries_every_gate_constant():
    cfg = ap.AllocationConfig()
    assert cfg.alloc_cap == 0.20          # P1_ALLOC_CAP (§8.6)
    assert cfg.n_draws == 50_000          # P1_N_DRAWS (§8.6)
    assert cfg.band_pct == (10.0, 90.0)   # P1_BAND_PCT (§8.1)
    assert cfg.clear_pct == (25.0, 75.0)  # P1_HYSTERESIS_BANDS clear band (§8.1)
    assert cfg.sigma_demo == 0.08         # P1_SIGMA_DEMO (§8.2)
    assert cfg.kelly_fraction == 0.5      # P1_KELLY_FRACTION (§8.6)


def test_allocate_is_long_only_fully_invested_edge_over_variance():
    # Positive alphas -> weight proportional to alpha/sigma^2; negatives -> zero; sums to 1.
    alphas = np.array([0.10, 0.05, -0.02])
    sigmas = np.full(3, 0.08)
    w = ap.allocate_one_draw(alphas, sigmas, cap=1.0)
    assert w[2] == 0.0                      # long-only: negative alpha gets nothing
    assert abs(w.sum() - 1.0) < 1e-12       # fully invested
    assert w[0] / w[1] == 2.0               # edge-over-variance with equal sigma -> alpha ratio


def test_allocate_all_nonpositive_returns_zeros():
    alphas = np.array([-0.05, -0.01, 0.0])
    w = ap.allocate_one_draw(alphas, np.full(3, 0.08), cap=0.20)
    assert np.array_equal(w, np.zeros(3))   # nothing to fund; not renormalized to garbage


def test_cap_binds_and_redistributes_pro_rata():
    # One dominant name must be capped; the excess flows to the uncapped names pro-rata.
    alphas = np.array([1.0, 0.10, 0.05])
    w = ap.allocate_one_draw(alphas, np.full(3, 0.08), cap=0.50)
    assert abs(w[0] - 0.50) < 1e-9          # capped
    assert abs(w.sum() - 1.0) < 1e-9        # still fully invested
    assert w[1] / w[2] == 2.0               # redistribution preserves the 0.10:0.05 ratio


def test_band_width_tracks_posterior_sd_all_else_equal():
    # Two managers (index 0, 1) share a posterior MEAN but differ in posterior SD; the wider
    # posterior must earn the wider band (§3.5: width is inherited honesty). Independent draws
    # (§8.3). A third absorbing manager is required: under a two-name fully-invested budget
    # w0 == 1 - w1, which forces identical band widths by mirror symmetry regardless of cap —
    # the property is only observable once a manager's weight is not pinned to one peer. A
    # non-binding cap keeps the weights continuous so the sd effect is not masked by the cap.
    post_mean = np.array([0.12, 0.12, 0.20])
    post_sd = np.array([0.02, 0.05, 0.03])
    sigmas = np.full(3, 0.08)
    cfg = ap.AllocationConfig(n_draws=8000, alloc_cap=1.0)
    rng = np.random.default_rng([20260707, 17])
    bands = ap.band_from_posterior(post_mean, post_sd, sigmas, cfg, rng=rng)
    width = bands.ceil - bands.floor
    assert width[1] > width[0]
    # Anchor is inside its own band; the band is a proper interval.
    assert np.all(bands.floor <= bands.anchor)
    assert np.all(bands.anchor <= bands.ceil)
    assert np.all(bands.q25 <= bands.q75)


def test_band_from_posterior_is_deterministic_under_fixed_seed():
    post_mean = np.array([0.10, 0.05, -0.03])
    post_sd = np.array([0.03, 0.04, 0.03])
    sigmas = np.full(3, 0.08)
    cfg = ap.AllocationConfig(n_draws=5000)
    a = ap.band_from_posterior(post_mean, post_sd, sigmas,
                               cfg, rng=np.random.default_rng([20260707, 17]))
    b = ap.band_from_posterior(post_mean, post_sd, sigmas,
                               cfg, rng=np.random.default_rng([20260707, 17]))
    assert np.array_equal(a.floor, b.floor) and np.array_equal(a.ceil, b.ceil)


def test_prob_zero_is_positive_for_a_marginal_name():
    # A name whose posterior mean sits near zero spends a nontrivial fraction of draws at w=0
    # (its drawn alpha goes negative) -> a 0% band floor and a material fund-or-not signal.
    post_mean = np.array([0.20, 0.005])
    post_sd = np.array([0.03, 0.03])
    sigmas = np.full(2, 0.08)
    cfg = ap.AllocationConfig(n_draws=8000)
    bands = ap.band_from_posterior(post_mean, post_sd, sigmas,
                                   cfg, rng=np.random.default_rng([20260707, 17]))
    assert bands.prob_zero[1] > 0.10       # marginal name funded-or-not is genuinely open
    assert bands.floor[1] == 0.0           # its band floor is exactly 0%
    assert bands.prob_zero[0] < 0.01       # the strong name is funded in nearly every world


def _band(floor, q25, q75, ceil):
    return ap.ManagerBand(floor=floor, q25=q25, anchor=0.5 * (q25 + q75),
                          q75=q75, ceil=ceil, prob_zero=0.0)


def test_band_action_fresh_look_inside_and_outside():
    band = _band(0.045, 0.055, 0.070, 0.104)   # B10-shaped band
    assert ap.band_action(0.065, band, prev_state=None).state == "inside"
    # B10 headline: the naive weight (10.8%) sits ABOVE the whole band -> review.
    trip = ap.band_action(0.108, band, prev_state=None)
    assert trip.state == "review"
    assert trip.outside_band is True


def test_band_action_hysteresis_holds_review_until_reentry_of_inner_band():
    band = _band(0.045, 0.055, 0.070, 0.104)
    # Once in review, hovering back inside the OUTER band but not the inner clear band holds review.
    hover = ap.band_action(0.100, band, prev_state="review")   # < ceil but > q75
    assert hover.state == "review"
    # Re-entering the inner 25-75 band clears the review.
    cleared = ap.band_action(0.062, band, prev_state="review")
    assert cleared.state == "inside"
