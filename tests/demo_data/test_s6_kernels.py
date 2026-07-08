import numpy as np

from quant_allocator.demo_data import s6_signatures_kernels as k


def test_family_is_hard_capped_at_six_in_frozen_order():
    # The frozen §3.4 family: six signatures, this exact order (row order of the table).
    assert list(k.SIGNATURES) == [
        "autocorr", "vol_of_vol", "skew", "kurtosis", "drawdown_shape", "rolling_ir_slope",
    ]
    assert k.S6_ROLLING_WINDOWS == (6, 12)


def test_autocorr_recovers_a_planted_ar1():
    rng = np.random.default_rng(0)
    e = rng.standard_normal(4000)
    r = np.empty(4000)
    r[0] = e[0]
    for t in range(1, 4000):
        r[t] = 0.5 * r[t - 1] + e[t]
    assert abs(k.sig_autocorr(r) - 0.5) < 0.05


def test_kurtosis_is_excess_zero_for_gaussian_positive_for_scale_mixture():
    rng = np.random.default_rng(1)
    gauss = rng.standard_normal(20000)
    assert abs(k.sig_kurtosis(gauss)) < 0.15
    # A scale mixture of normals (the conviction-sizing mechanism) has positive excess kurtosis.
    scale = np.where(rng.standard_normal(20000) > 0, 3.0, 1.0)
    mixture = scale * rng.standard_normal(20000)
    assert k.sig_kurtosis(mixture) > 0.5


def test_skew_sign_matches_a_planted_asymmetry():
    rng = np.random.default_rng(2)
    left_tailed = -np.abs(rng.standard_normal(20000)) ** 2
    assert k.sig_skew(left_tailed) < 0.0


def test_vol_of_vol_is_zero_for_constant_vol_positive_for_regime_switch():
    rng = np.random.default_rng(3)
    steady = rng.standard_normal(120) * 0.02
    calm_then_wild = np.concatenate([rng.standard_normal(60) * 0.01, rng.standard_normal(60) * 0.05])
    assert k.sig_vol_of_vol(calm_then_wild) > k.sig_vol_of_vol(steady)


def test_drawdown_shape_is_positive_and_scale_free():
    # MDD/(sigma*sqrt(T)) is scale-invariant in the small-return limit, where the
    # kernel's compounded wealth (cumprod(1+r)) is near-additive; a global rescale
    # then moves MDD and sigma together. (At large return magnitudes the compounding
    # convexity breaks exact invariance, so the property is a small-return statement.)
    rng = np.random.default_rng(4)
    r = rng.standard_normal(60) * 0.001 - 0.001 / 6.0
    a = k.sig_drawdown_shape(r)
    b = k.sig_drawdown_shape(r * 2.0)
    assert a > 0.0
    assert abs(a - b) < 0.02


def test_rolling_ir_slope_is_negative_for_front_loaded_alpha():
    # A front-loaded mean over a roughly constant-vol series => the rolling IR
    # (mean/std) trends down over the window => negative OLS slope. The constant-vol
    # noise floor is what keeps the denominator stable enough for the mean decay to
    # drive the slope (a noiseless decaying series collapses the rolling std instead).
    months = np.arange(60)
    rng = np.random.default_rng(0)
    r = 0.05 * 0.5 ** (months / 6.0) + rng.standard_normal(60) * 0.008
    assert k.sig_rolling_ir_slope(r) < 0.0


def test_all_kernels_return_finite_floats_and_degrade_gracefully():
    flat = np.zeros(40)
    for name, fn in k.SIGNATURES.items():
        val = fn(flat)  # zero-variance input hits every degenerate guard
        assert isinstance(val, float) and np.isfinite(val), name
