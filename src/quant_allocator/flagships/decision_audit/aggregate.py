"""P3 spec 3.5 — the aggregate process-value-add posterior.

The one place a number crosses events. It is NOT a new estimator: it is the S1
3.6 normal-normal closed form (skill_ledger/empirical.py), with the grand mean
PINNED at the Goyal-Wahal null (0) and a fixed prior scale rather than an
estimated tau. test_aggregate.test_posterior_matches_house_shrinkage_identity
proves the algebra is identical to the house function (which is imported for that
proof and never modified).

Effective N is honest: decisions in one market episode share a forward path, so
their value-adds are correlated and the effective sample is far below the event
count. The cohort block bootstrap is the reported standard error; the design
effect 1 + (m_bar - 1)*rho is the intuition and the cross-check. The raw-mean
PowerGate fires on EFFECTIVE events (spec 3.5: below MIN_EVENTS_FOR_AGGREGATE the
panel refuses a value-add average) — see docket P3-D2 for why the gate compares
N_eff, not the raw count, so a cohort-correlated N=15 is still refused.
"""

from __future__ import annotations

import math
import statistics
from dataclasses import dataclass

import numpy as np

# NUMERICS-GATE P3-D1: prior scale on decision value-add, provisional 2%/yr, sourced
# from the cross-sponsor dispersion of Goyal-Wahal round-trip differentials. The
# exact dispersion figure is verified against Goyal & Wahal (2008) at the numerics
# gate; the citation is pinned in demo_data/p3_hirefire.py.
DECISION_VALUE_PRIOR_SCALE = 0.02
# NUMERICS-GATE P3-D2: below this many EFFECTIVE events the raw mean is refused (the
# shrunk posterior still renders — spec gate ruling). 12 stands as the gate.
MIN_EVENTS_FOR_AGGREGATE = 12
POSTERIOR_CI_LEVEL = 0.90
# NUMERICS-GATE P3-D3: cohort block-bootstrap replications (reuses the S2 bootstrap
# rep count convention). Deterministic via the seed + stream tag below.
BOOTSTRAP_REPS = 2000
AGGREGATE_SEED = 20260707
_BOOTSTRAP_STREAM = 11


@dataclass(frozen=True)
class PosteriorResult:
    n_events: int
    n_cohorts: int
    events_per_cohort: float
    intra_cohort_rho: float
    design_effect: float
    n_effective: float
    raw_mean: float
    raw_se: float
    raw_mean_ci: tuple[float, float]
    raw_mean_gated: bool
    posterior_mean: float
    posterior_sd: float
    posterior_ci: tuple[float, float]
    shrinkage_weight: float
    prob_positive: float
    verdict: str  # "indistinguishable" | "distinguishable"


def _z(level: float) -> float:
    return statistics.NormalDist().inv_cdf(0.5 + level / 2.0)


def posterior_toward_null(v_bar, se, prior_scale, level, prior_mean=0.0):
    # S1 3.6 identity: w = tau^2 / (tau^2 + se^2); post = w*v_bar + (1-w)*mu;
    # post_sd = sqrt(w*se^2). prob = Phi(post / post_sd).
    tau2 = float(prior_scale) ** 2
    se2 = float(se) ** 2
    w = tau2 / (tau2 + se2) if (tau2 + se2) > 0 else 0.0
    post = w * float(v_bar) + (1.0 - w) * float(prior_mean)
    post_sd = math.sqrt(w * se2)
    z = _z(level)
    ci = (post - z * post_sd, post + z * post_sd)
    if post_sd == 0.0:
        prob = 1.0 if post > 0.0 else 0.0
    else:
        prob = statistics.NormalDist().cdf(post / post_sd)
    return post, post_sd, ci, w, prob


def intra_cohort_correlation(values, cohort_ids) -> float:
    # One-way random-effects ICC(1): between-cohort variance share of total.
    values = np.asarray(values, dtype=float)
    cohort_ids = np.asarray(cohort_ids)
    grand = values.mean()
    cohorts = list(dict.fromkeys(cohort_ids.tolist()))
    k = len(cohorts)
    n = len(values)
    if k < 2 or n <= k:
        return 0.0
    ss_between = 0.0
    ss_within = 0.0
    sizes = []
    for c in cohorts:
        grp = values[cohort_ids == c]
        sizes.append(len(grp))
        ss_between += len(grp) * (grp.mean() - grand) ** 2
        ss_within += float(((grp - grp.mean()) ** 2).sum())
    ms_between = ss_between / (k - 1)
    ms_within = ss_within / (n - k) if n > k else 0.0
    m0 = (n - sum(s * s for s in sizes) / n) / (k - 1)  # correction for unequal sizes
    denom = ms_between + (m0 - 1) * ms_within
    if denom <= 0:
        return 0.0
    rho = (ms_between - ms_within) / denom
    return float(min(max(rho, 0.0), 1.0))  # clamp: negative ICC reads as 0 correlation


def design_effect(m_bar: float, rho: float) -> float:
    return 1.0 + (m_bar - 1.0) * rho


def cohort_block_bootstrap(values, cohort_ids, reps, seed):
    # Resample whole cohorts with replacement (spec 3.5): the block is the cohort,
    # so the common forward path inside a cohort is preserved and the interval
    # widens honestly. Reported se = std of the bootstrap means.
    values = np.asarray(values, dtype=float)
    cohort_ids = np.asarray(cohort_ids)
    cohorts = list(dict.fromkeys(cohort_ids.tolist()))
    blocks = [values[cohort_ids == c] for c in cohorts]
    k = len(blocks)
    rng = np.random.default_rng([seed, _BOOTSTRAP_STREAM])
    means = np.empty(reps)
    for b in range(reps):
        pick = rng.integers(0, k, size=k)
        sample = np.concatenate([blocks[i] for i in pick])
        means[b] = sample.mean()
    se = float(means.std(ddof=1))
    lo, hi = np.quantile(means, [0.05, 0.95])  # 90% percentile interval
    return se, (float(lo), float(hi))


def events_to_detectability(true_gap, per_event_sd, rho, events_per_cohort, prior_scale, level) -> float:
    # spec 4 (converge-or-cut ruling): the closed-form one-liner that ships INSTEAD
    # of the cut Monte-Carlo atlas cell. Asymptotically (large N, weight -> 1) the
    # posterior interval excludes zero when |gap| > z*se, se = sd*sqrt(deff/N).
    # Solve for N: N = deff * z^2 * sd^2 / gap^2. Independent of prior_scale in the
    # large-N limit (kept in the signature so the page can annotate the prior).
    if true_gap == 0.0:
        return math.inf
    deff = design_effect(events_per_cohort, rho)
    z = _z(level)
    n = deff * (z ** 2) * (per_event_sd ** 2) / (true_gap ** 2)
    return float(math.ceil(n))


def aggregate_value_add(
    event_values,
    cohort_ids,
    *,
    prior_scale=DECISION_VALUE_PRIOR_SCALE,
    level=POSTERIOR_CI_LEVEL,
    min_events=MIN_EVENTS_FOR_AGGREGATE,
    seed=AGGREGATE_SEED,
) -> PosteriorResult:
    values = np.asarray(event_values, dtype=float)
    cohort_ids = np.asarray(cohort_ids)
    n = len(values)
    cohorts = list(dict.fromkeys(cohort_ids.tolist()))
    k = len(cohorts)
    m_bar = n / k if k else float(n)
    rho = intra_cohort_correlation(values, cohort_ids)
    deff = design_effect(m_bar, rho)
    n_eff = n / deff if deff > 0 else float(n)

    raw_mean = float(values.mean())
    raw_se, raw_ci = cohort_block_bootstrap(values, cohort_ids, BOOTSTRAP_REPS, seed)

    post, post_sd, post_ci, w, prob = posterior_toward_null(
        raw_mean, raw_se, prior_scale, level
    )
    straddles_zero = post_ci[0] <= 0.0 <= post_ci[1]
    return PosteriorResult(
        n_events=n,
        n_cohorts=k,
        events_per_cohort=m_bar,
        intra_cohort_rho=rho,
        design_effect=deff,
        n_effective=n_eff,
        raw_mean=raw_mean,
        raw_se=raw_se,
        raw_mean_ci=raw_ci,
        raw_mean_gated=bool(n_eff < min_events),
        posterior_mean=post,
        posterior_sd=post_sd,
        posterior_ci=post_ci,
        shrinkage_weight=w,
        prob_positive=prob,
        verdict="indistinguishable" if straddles_zero else "distinguishable",
    )
