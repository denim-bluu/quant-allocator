import numpy as np

from quant_allocator.flagships.skill_ledger.empirical import (
    advisory_band,
    shrink_alphas,
)


def test_shrinkage_weight_matches_closed_form_by_hand():
    # S1 spec §3.6: mu_hat = mean(ols); tau2 = max(0, var(ols, ddof=1) - mean(se^2));
    # w = tau2 / (tau2 + se^2); post = w*ols + (1-w)*mu_hat.
    ols = np.array([0.02, 0.06, -0.01])
    ses = np.array([0.03, 0.03, 0.03])
    groups = np.array(["A", "A", "A"])
    mu = ols.mean()
    tau2 = max(0.0, ols.var(ddof=1) - (ses**2).mean())
    w = tau2 / (tau2 + ses**2)
    expected_post = w * ols + (1.0 - w) * mu
    result = shrink_alphas(ols, ses, groups)
    assert np.allclose(result.shrinkage_weight, w)
    assert np.allclose(result.posterior_alpha, expected_post)
    assert np.allclose(result.group_mean, mu)


def test_weights_within_unit_interval_and_posterior_between_ols_and_prior():
    ols = np.array([0.05, -0.03, 0.01, 0.09])
    ses = np.array([0.02, 0.05, 0.04, 0.03])
    groups = np.array(["A", "A", "A", "A"])
    r = shrink_alphas(ols, ses, groups)
    assert np.all(r.shrinkage_weight >= 0.0) and np.all(r.shrinkage_weight <= 1.0)
    lo = np.minimum(ols, r.group_mean)
    hi = np.maximum(ols, r.group_mean)
    assert np.all(r.posterior_alpha >= lo - 1e-12)
    assert np.all(r.posterior_alpha <= hi + 1e-12)


def test_posterior_sd_no_wider_than_se_and_prob_in_unit_interval():
    ols = np.array([0.05, -0.03, 0.01, 0.09])
    ses = np.array([0.02, 0.05, 0.04, 0.03])
    groups = np.array(["A", "A", "A", "A"])
    r = shrink_alphas(ols, ses, groups)
    assert np.all(r.posterior_sd <= ses + 1e-12)
    assert np.all(r.prob_positive >= 0.0) and np.all(r.prob_positive <= 1.0)


def test_groups_are_shrunk_independently():
    ols = np.array([0.10, 0.12, -0.05, -0.07])
    ses = np.array([0.03, 0.03, 0.03, 0.03])
    groups = np.array(["A", "A", "B", "B"])
    r = shrink_alphas(ols, ses, groups)
    assert np.isclose(r.group_mean[0], np.mean([0.10, 0.12]))
    assert np.isclose(r.group_mean[2], np.mean([-0.05, -0.07]))


def test_zero_dispersion_group_collapses_to_prior_without_error():
    # tau2 hits its floor of 0 (spec §8 note 4): posterior == group mean, sd == 0.
    ols = np.array([0.04, 0.04, 0.04])
    ses = np.array([0.05, 0.05, 0.05])
    groups = np.array(["A", "A", "A"])
    r = shrink_alphas(ols, ses, groups)
    assert np.allclose(r.shrinkage_weight, 0.0)
    assert np.allclose(r.posterior_alpha, 0.04)
    assert np.allclose(r.posterior_sd, 0.0)
    assert np.all(r.prob_positive == 1.0)  # mean > 0, degenerate posterior


def test_advisory_bands_at_boundaries():
    # S1 spec §3.7: four advisory bands from the posterior t-ratio m_i.
    assert advisory_band(-0.1) == "review"
    assert advisory_band(0.0) == "minimum"
    assert advisory_band(0.49) == "minimum"
    assert advisory_band(0.5) == "standard"
    assert advisory_band(0.99) == "standard"
    assert advisory_band(1.0) == "conviction"
    assert advisory_band(3.0) == "conviction"
