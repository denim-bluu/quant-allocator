import numpy as np
import pytest

from quant_allocator.flagships.book_xray import fusion


def test_three_manager_toy_reproduces_spec_mechanics():
    cfg = fusion.FusionConfig()
    observations = np.array([0.30, 0.50, 0.20])
    tiers = ("P", "E", "R")
    weights = np.full(3, 1.0 / 3.0)

    result = fusion.fuse_book(weights, observations, tiers, cfg)

    np.testing.assert_allclose(
        [p.sd for p in result.manager_posteriors],
        [0.019984, 0.078995, 0.223607],
        atol=1e-6,
    )
    assert result.book.mean == pytest.approx(0.330784, abs=1e-6)
    assert result.book.sd == pytest.approx(0.079330, abs=1e-6)
    assert result.provenance[2] == pytest.approx(0.882774, abs=1e-6)


def test_book_posterior_is_order_invariant_and_contains_its_point():
    weights = np.array([0.5, 0.3, 0.2])
    means = np.array([0.1, 0.4, -0.2])
    sds = np.array([0.02, 0.08, 0.25])
    a = fusion.book_posterior(weights, means, sds, level=0.90)
    order = np.array([2, 0, 1])
    b = fusion.book_posterior(weights[order], means[order], sds[order], level=0.90)
    assert b.mean == pytest.approx(a.mean)
    assert b.sd == pytest.approx(a.sd)
    assert b.ci_lo == pytest.approx(a.ci_lo)
    assert b.ci_hi == pytest.approx(a.ci_hi)
    assert a.ci_lo <= a.mean <= a.ci_hi


def test_provenance_is_a_variance_decomposition():
    shares = fusion.provenance(
        np.array([0.5, 0.3, 0.2]), np.array([0.02, 0.08, 0.25])
    )
    assert np.all(shares >= 0.0)
    assert shares.sum() == pytest.approx(1.0)


@pytest.mark.parametrize(
    ("weights", "means", "sds", "level", "match"),
    [
        ([0.6, 0.3], [0.1, 0.2], [0.1, 0.1], 0.9, "sum to 1"),
        ([0.5, 0.5], [0.1], [0.1, 0.1], 0.9, "same length"),
        ([0.5, 0.5], [0.1, 0.2], [0.1, 0.0], 0.9, "positive"),
        ([0.5, 0.5], [0.1, 0.2], [0.1, 0.1], 1.0, "level"),
    ],
)
def test_book_posterior_rejects_invalid_inputs(weights, means, sds, level, match):
    with pytest.raises(ValueError, match=match):
        fusion.book_posterior(weights, means, sds, level=level)


def test_measurement_posterior_rejects_nonpositive_scales():
    with pytest.raises(ValueError, match="positive"):
        fusion.measurement_posterior(0.2, 0.0, 0.3, 0.1)
    with pytest.raises(ValueError, match="positive"):
        fusion.measurement_posterior(0.2, 0.5, 0.3, -0.1)


def test_transparency_counterfactual_clears_teaching_roster_floor():
    weights = np.array([8, 6, 9, 5, 12, 4, 7, 5, 10, 6, 11, 4, 7, 5, 6], dtype=float)
    weights /= weights.sum()
    observations = np.array(
        [0.15, 0.42, 0.05, 0.30, -0.10, 0.55, 0.20, 0.35, 0.12,
         0.28, 0.08, 0.48, 0.18, 0.40, 0.22]
    )
    tiers = ("R", "R", "E", "R", "P", "R", "E", "R", "R",
             "E", "P", "R", "E", "R", "R")

    gain = fusion.transparency_counterfactuals(
        weights, observations, tiers, fusion.FusionConfig()
    )

    assert gain.all_r_sd > gain.actual_sd > gain.all_e_sd
    assert gain.gain_all_r_to_all_e > 0.20
    assert gain.renders


def test_equal_tier_noise_refuses_information_gain():
    config = fusion.FusionConfig(exposure_meas_sd={"P": 0.1, "E": 0.1, "R": 0.1})
    gain = fusion.transparency_counterfactuals(
        [0.5, 0.5], [0.1, 0.4], ("R", "P"), config
    )
    assert gain.gain_all_r_to_all_e == pytest.approx(0.0)
    assert not gain.renders


def test_tier_monotonicity_is_pinned_for_each_manager():
    weights = np.array([0.5, 0.3, 0.2])
    observations = np.array([0.1, 0.4, -0.2])
    assert fusion.tier_monotonicity(
        weights, observations, ("R", "E", "P"), fusion.FusionConfig()
    )
