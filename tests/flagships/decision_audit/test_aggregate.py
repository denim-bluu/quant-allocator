# tests/flagships/decision_audit/test_aggregate.py
import math

import numpy as np
import pytest

from quant_allocator.flagships.decision_audit import aggregate as agg
from quant_allocator.flagships.skill_ledger.empirical import shrink_alphas


def test_posterior_pulls_toward_zero_and_weight_in_unit_interval():
    post, post_sd, ci, w, prob = agg.posterior_toward_null(
        v_bar=0.03, se=0.05, prior_scale=0.02, level=0.90
    )
    assert 0.0 < w < 1.0
    assert abs(post) < abs(0.03)      # shrunk toward the pinned null (0)
    assert ci[0] < post < ci[1]
    assert 0.0 <= prob <= 1.0


def test_posterior_matches_house_shrinkage_identity():
    # The P3 posterior is the SAME normal-normal closed form as S1 3.6
    # (skill_ledger/empirical.py) with the grand mean pinned. Prove equivalence:
    # feed our formula the emergent mu/tau2 that shrink_alphas derives, and it must
    # reproduce shrink_alphas element-wise. (empirical.py is imported, not modified.)
    alphas = np.array([0.04, -0.01, 0.02, 0.05])
    ses = np.array([0.03, 0.05, 0.04, 0.02])
    groups = np.array(["g", "g", "g", "g"])
    res = shrink_alphas(alphas, ses, groups)
    mu = float(res.group_mean[0])
    tau = math.sqrt(float(res.group_tau2[0]))
    for i in range(len(alphas)):
        post, post_sd, _, _, prob = agg.posterior_toward_null(
            v_bar=float(alphas[i]), se=float(ses[i]), prior_scale=tau,
            level=0.90, prior_mean=mu,
        )
        assert post == pytest.approx(res.posterior_alpha[i], rel=1e-9)
        assert post_sd == pytest.approx(res.posterior_sd[i], rel=1e-9)
        assert prob == pytest.approx(res.prob_positive[i], rel=1e-6)


def test_design_effect_worked_example():
    # spec 8, note 1: 20 events, 4 per cohort, rho=0.5 => deff=2.5 => N_eff=8.
    deff = agg.design_effect(m_bar=4.0, rho=0.5)
    assert deff == pytest.approx(2.5)
    assert 20 / deff == pytest.approx(8.0)


def test_intra_cohort_correlation_high_when_cohorts_separated():
    # Events identical within a cohort, very different across cohorts => rho -> ~1.
    values = np.array([1.0, 1.0, 1.0, 9.0, 9.0, 9.0])
    cohorts = np.array(["a", "a", "a", "b", "b", "b"])
    rho = agg.intra_cohort_correlation(values, cohorts)
    assert rho > 0.8


def test_cohort_block_bootstrap_is_deterministic():
    values = np.array([0.02, -0.01, 0.03, 0.00, 0.04, -0.02])
    cohorts = np.array(["a", "a", "b", "b", "c", "c"])
    se1, ci1 = agg.cohort_block_bootstrap(values, cohorts, reps=500, seed=7)
    se2, ci2 = agg.cohort_block_bootstrap(values, cohorts, reps=500, seed=7)
    assert se1 == se2
    assert ci1 == ci2


def test_events_to_detectability_scales_with_design_effect():
    n_low = agg.events_to_detectability(
        true_gap=0.02, per_event_sd=0.05, rho=0.0, events_per_cohort=1.0,
        prior_scale=0.02, level=0.90,
    )
    n_high = agg.events_to_detectability(
        true_gap=0.02, per_event_sd=0.05, rho=0.5, events_per_cohort=4.0,
        prior_scale=0.02, level=0.90,
    )
    assert n_high > n_low            # cohort correlation raises the bar
    assert math.isinf(
        agg.events_to_detectability(0.0, 0.05, 0.0, 1.0, 0.02, 0.90)
    )                                # a zero true edge is never detectable


def test_aggregate_gates_raw_mean_on_effective_events():
    # 15 events in 5 cohorts of 3 with positive intra-cohort correlation:
    # N_eff should fall below the 12-event gate, so the raw mean is refused.
    rng = np.random.default_rng(0)
    cohort_shocks = {c: rng.normal(0.0, 0.03) for c in "abcde"}
    values, cohorts = [], []
    for c in "abcde":
        for _ in range(3):
            values.append(cohort_shocks[c] + rng.normal(0.0, 0.005))
            cohorts.append(c)
    res = agg.aggregate_value_add(np.array(values), np.array(cohorts))
    assert res.n_events == 15
    assert res.n_effective < agg.MIN_EVENTS_FOR_AGGREGATE
    assert res.raw_mean_gated is True
    # The posterior renders regardless of the gate (the gate ruling: shrunk posterior
    # renders at any N; the raw mean is what is gated).
    assert res.posterior_ci[0] < res.posterior_mean < res.posterior_ci[1]
