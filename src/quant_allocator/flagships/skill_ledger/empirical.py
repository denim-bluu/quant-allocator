"""S1 §3.6 closed-form normal-normal shrinkage + §3.7 advisory weight bands.

Unit-agnostic pure math: inputs are point estimates and their standard errors
in one consistent unit (the S1 generator passes annualized values), outputs in
the same unit. numpy only — no PyMC. The live MCMC model is skill_ledger/model.py
(out of scope here); this closed form is both the demo path and a legitimate
library function (S1 spec §3.6, §5).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class ShrinkageResult:
    posterior_alpha: np.ndarray
    posterior_sd: np.ndarray
    shrinkage_weight: np.ndarray
    prob_positive: np.ndarray
    posterior_t_ratio: np.ndarray
    group_mean: np.ndarray
    group_tau2: np.ndarray


def _standard_normal_cdf(z: np.ndarray) -> np.ndarray:
    # Phi(z) = 0.5(1 + erf(z/sqrt2)); math.erf is exact and stdlib-only.
    return 0.5 * (1.0 + np.vectorize(math.erf)(z / math.sqrt(2.0)))


def shrink_alphas(
    ols_alphas: np.ndarray, ses: np.ndarray, groups: np.ndarray
) -> ShrinkageResult:
    ols_alphas = np.asarray(ols_alphas, dtype=float)
    ses = np.asarray(ses, dtype=float)
    groups = np.asarray(groups)
    n = len(ols_alphas)
    posterior_alpha = np.empty(n)
    posterior_sd = np.empty(n)
    shrinkage_weight = np.empty(n)
    group_mean = np.empty(n)
    group_tau2 = np.empty(n)

    for group in np.unique(groups):
        mask = groups == group
        alphas = ols_alphas[mask]
        se2 = ses[mask] ** 2
        # S1 spec §3.6: mu_hat_s = mean(ols in s); tau_hat^2 = max(0, var(ols) - mean(se^2)).
        mu = float(alphas.mean())
        tau2 = max(0.0, float(alphas.var(ddof=1)) - float(se2.mean()))
        # S1 spec §3.6: w_i = tau_hat^2 / (tau_hat^2 + se(alpha_i)^2).
        w = tau2 / (tau2 + se2)
        # S1 spec §3.6: alpha_post = w*ols + (1 - w)*mu_hat.
        post = w * alphas + (1.0 - w) * mu
        # S1 spec §8 note 1: posterior precision = 1/tau^2 + 1/se^2, so posterior
        # variance = tau^2·se^2 / (tau^2 + se^2) = w·se^2 (algebraically identical,
        # and numerically safe when tau2 -> 0 => w -> 0 => sd -> 0).
        post_sd = np.sqrt(w * se2)
        posterior_alpha[mask] = post
        posterior_sd[mask] = post_sd
        shrinkage_weight[mask] = w
        group_mean[mask] = mu
        group_tau2[mask] = tau2

    # Posterior t-ratio m_i = E[alpha_i]/sd(alpha_i) (S1 spec §3.5, §3.7).
    with np.errstate(divide="ignore", invalid="ignore"):
        t_ratio = posterior_alpha / posterior_sd
    prob_positive = _standard_normal_cdf(t_ratio)
    # Degenerate posterior (sd == 0, tau2 floored to 0): P(alpha>0) is a step.
    degenerate = posterior_sd == 0.0
    prob_positive = np.where(
        degenerate, np.where(posterior_alpha > 0.0, 1.0, 0.0), prob_positive
    )
    t_ratio = np.where(
        degenerate, np.where(posterior_alpha > 0.0, np.inf, -np.inf), t_ratio
    )
    return ShrinkageResult(
        posterior_alpha=posterior_alpha,
        posterior_sd=posterior_sd,
        shrinkage_weight=shrinkage_weight,
        prob_positive=prob_positive,
        posterior_t_ratio=t_ratio,
        group_mean=group_mean,
        group_tau2=group_tau2,
    )


def advisory_band(t_ratio: float) -> str:
    # S1 spec §3.7: four advisory bands from the posterior t-ratio m_i.
    if t_ratio < 0.0:
        return "review"
    if t_ratio < 0.5:
        return "minimum"
    if t_ratio < 1.0:
        return "standard"
    return "conviction"
