"""S2 §3 tear-sheet estimator stages as pure functions over a returns series
and a factor frame. No rendering, no I/O (S2 spec §5). Stage 1 (GLM unsmoothing)
lives here; later tasks add stages 2-6 in this same module.

Numeric outputs feed a demo generator that is HELD FOR THE NUMERICS GATE.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.optimize import minimize

# S2 spec §3.1: skip de-smoothing when theta0 >= 0.95 (no material smoothing;
# de-smoothing would only add estimator noise).
THETA0_SKIP = 0.95
_MA_ORDER = 2


@dataclass(frozen=True)
class UnsmoothResult:
    theta: np.ndarray
    desmoothed: np.ndarray
    vol_ratio: float
    applied: bool
    skip_reason: str | None


def _ma2_neg_log_likelihood(theta: np.ndarray, centered: np.ndarray) -> float:
    # Observed returns are MA(2) in the true iid innovations (S2 spec §3.1):
    #   x_t = sigma * (theta0 e_t + theta1 e_{t-1} + theta2 e_{t-2}), e ~ iid N(0,1).
    # Autocovariances of the (unit-sigma) kernel:
    g0 = float(theta @ theta)
    g1 = float(theta[0] * theta[1] + theta[1] * theta[2])
    g2 = float(theta[0] * theta[2])
    n = len(centered)
    # Banded Gaussian log-likelihood via a Toeplitz covariance; sigma^2 profiled out.
    cov = np.zeros((n, n))
    idx = np.arange(n)
    cov[idx, idx] = g0
    cov[idx[:-1], idx[1:]] = g1
    cov[idx[1:], idx[:-1]] = g1
    cov[idx[:-2], idx[2:]] = g2
    cov[idx[2:], idx[:-2]] = g2
    sign, logdet = np.linalg.slogdet(cov)
    if sign <= 0:
        return 1e12
    solve = np.linalg.solve(cov, centered)
    quad = float(centered @ solve)
    sigma2 = quad / n  # MLE of sigma^2 given the kernel shape
    # Concentrated negative log-likelihood (drop constants): (n/2) log(sigma2) + (1/2) logdet.
    return 0.5 * (n * np.log(sigma2) + logdet)


def unsmooth(returns: np.ndarray) -> UnsmoothResult:
    returns = np.asarray(returns, dtype=float)
    centered = returns - returns.mean()
    # Convex smoothing kernel: theta_k >= 0, sum(theta_k) = 1 (S2 spec §3.1).
    constraints = ({"type": "eq", "fun": lambda th: th.sum() - 1.0},)
    bounds = [(0.0, 1.0)] * (_MA_ORDER + 1)
    start = np.array([0.8, 0.15, 0.05])
    best = minimize(
        _ma2_neg_log_likelihood,
        start,
        args=(centered,),
        method="SLSQP",
        bounds=bounds,
        constraints=constraints,
        options={"maxiter": 500, "ftol": 1e-10},
    )
    theta = np.clip(best.x, 0.0, None)
    theta = theta / theta.sum()
    # MA(2) identifiability: reversing the kernel [t0,t1,t2] -> [t2,t1,t0]
    # leaves every autocovariance (g0,g1,g2) unchanged, so the Gaussian
    # likelihood has two equal optima. Select the invertible representation
    # (contemporaneous weight theta0 dominant), which is the one S2 spec §3.1
    # describes and the theta0-skip rule assumes.
    if theta[2] > theta[0]:
        theta = theta[::-1].copy()

    if theta[0] >= THETA0_SKIP:
        return UnsmoothResult(
            theta=np.array([1.0, 0.0, 0.0]),
            desmoothed=returns.copy(),
            vol_ratio=1.0,
            applied=False,
            skip_reason=f"theta0={theta[0]:.3f} >= {THETA0_SKIP} (no material smoothing)",
        )

    # De-smoothed series: reconstruct r_t by inverting the MA(2) filter, then
    # rescale so its vol matches the analytic sqrt(sum theta^2) relation
    # (S2 spec §3.1: sigma_obs^2 = (sum theta_k^2) sigma_r^2).
    vol_ratio = float(np.sqrt(theta @ theta))
    desmoothed = _invert_ma2(centered, theta) + returns.mean()
    # Enforce the variance identity exactly (the filter inversion is approximate
    # at the series edges); mean is conserved by construction.
    current = desmoothed - desmoothed.mean()
    target_std = returns.std(ddof=1) / vol_ratio
    scale = target_std / current.std(ddof=1) if current.std(ddof=1) > 0 else 1.0
    desmoothed = current * scale + returns.mean()
    return UnsmoothResult(
        theta=theta,
        desmoothed=desmoothed,
        vol_ratio=vol_ratio,
        applied=True,
        skip_reason=None,
    )


def _invert_ma2(centered: np.ndarray, theta: np.ndarray) -> np.ndarray:
    # Recover the innovation-scale series by causal deconvolution of the kernel:
    #   r_t = (x_t - theta1 r_{t-1} - theta2 r_{t-2}) / theta0.
    r = np.zeros_like(centered)
    for t in range(len(centered)):
        acc = centered[t]
        if t >= 1:
            acc -= theta[1] * r[t - 1]
        if t >= 2:
            acc -= theta[2] * r[t - 2]
        r[t] = acc / theta[0]
    return r
