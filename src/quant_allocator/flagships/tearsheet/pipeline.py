"""S2 §3 tear-sheet estimator stages as pure functions over a returns series
and a factor frame. No rendering, no I/O (S2 spec §5). Stage 1 (GLM unsmoothing)
lives here; later tasks add stages 2-6 in this same module.

Numeric outputs feed a demo generator that is HELD FOR THE NUMERICS GATE.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass

import numpy as np
from scipy.optimize import minimize

# S2 spec §3.1: skip de-smoothing when theta0 >= 0.95 (no material smoothing;
# de-smoothing would only add estimator noise).
THETA0_SKIP = 0.95
_MA_ORDER = 2

MONTHS_PER_YEAR = 12
BOOT_REPS = 2000
MPPM_RHO = 3.0
ALPHA_CI_LEVEL = 0.90
SHARPE_CI_LEVEL = 0.95
PIPELINE_SEED = 20260706


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


@dataclass(frozen=True)
class FactorFit:
    alpha_monthly: float
    alpha_annual: float
    betas: np.ndarray
    resid: np.ndarray
    factor_names: tuple[str, ...]
    design: np.ndarray  # [1, factors] design matrix (T×k), for the HAC intercept SE


@dataclass(frozen=True)
class SharpeStats:
    sharpe_annual: float
    lo_se_annual: float
    lo_ci: tuple[float, float]
    boot_ci: tuple[float, float]
    excludes_zero: bool


@dataclass(frozen=True)
class AlphaStats:
    alpha_annual: float
    hac_ci: tuple[float, float]
    boot_ci: tuple[float, float]
    ci: tuple[float, float]
    crosses_zero: bool


def _z(level: float) -> float:
    # Two-sided normal quantile for a central `level` interval.
    return statistics.NormalDist().inv_cdf(0.5 + level / 2.0)


def regress(excess_returns, factors, factor_names) -> FactorFit:
    # S2 spec §3.2: OLS of excess return on the strategy factor set; intercept is alpha.
    excess_returns = np.asarray(excess_returns, dtype=float)
    factors = np.asarray(factors, dtype=float)
    design = np.column_stack([np.ones(len(excess_returns)), factors])
    coef, *_ = np.linalg.lstsq(design, excess_returns, rcond=None)
    resid = excess_returns - design @ coef
    alpha_monthly = float(coef[0])
    return FactorFit(
        alpha_monthly=alpha_monthly,
        alpha_annual=alpha_monthly * MONTHS_PER_YEAR,  # S2 spec §3.2: annualize alpha x12
        betas=coef[1:].copy(),
        resid=resid,
        factor_names=tuple(factor_names),
        design=design,
    )


def sharpe_intervals(returns, *, n_boot=BOOT_REPS, seed=PIPELINE_SEED) -> SharpeStats:
    returns = np.asarray(returns, dtype=float)
    t = len(returns)
    sr_m = float(returns.mean() / returns.std(ddof=1))
    # S2 spec §3.3, Lo (2002): monthly SE ~ sqrt((1 + SR^2/2)/T); annualize point and SE by sqrt(12).
    se_m = float(np.sqrt((1.0 + sr_m**2 / 2.0) / t))
    root12 = np.sqrt(MONTHS_PER_YEAR)
    sr_ann = sr_m * root12
    se_ann = se_m * root12
    z = _z(SHARPE_CI_LEVEL)
    lo_ci = (sr_ann - z * se_ann, sr_ann + z * se_ann)
    boot_ci = _studentized_block_bootstrap_sharpe(returns, sr_m, se_m, n_boot, seed)
    boot_ann = (boot_ci[0] * root12, boot_ci[1] * root12)
    return SharpeStats(
        sharpe_annual=sr_ann,
        lo_se_annual=se_ann,
        lo_ci=lo_ci,
        boot_ci=boot_ann,
        excludes_zero=not (lo_ci[0] <= 0.0 <= lo_ci[1]),
    )


def _studentized_block_bootstrap_sharpe(returns, sr_hat, se_hat, n_boot, seed):
    # S2 spec §3.3, Ledoit-Wolf (2008): studentized circular block bootstrap,
    # block length ~ T^(1/3) rounded (≈4 at T=48).
    t = len(returns)
    block = max(1, round(t ** (1.0 / 3.0)))
    rng = np.random.default_rng([seed, 42])
    tstats = np.empty(n_boot)
    n_blocks = int(np.ceil(t / block))
    for b in range(n_boot):
        starts = rng.integers(0, t, size=n_blocks)
        offsets = (starts[:, None] + np.arange(block)[None, :]) % t  # circular wrap
        sample = returns[offsets.ravel()[:t]]
        sr_b = sample.mean() / sample.std(ddof=1)
        se_b = np.sqrt((1.0 + sr_b**2 / 2.0) / t)
        tstats[b] = (sr_b - sr_hat) / se_b
    # Studentized percentile CI: invert the bootstrap t-distribution.
    lo_q, hi_q = np.quantile(tstats, [(1 - SHARPE_CI_LEVEL) / 2, 1 - (1 - SHARPE_CI_LEVEL) / 2])
    return (sr_hat - hi_q * se_hat, sr_hat - lo_q * se_hat)


def alpha_interval(fit, *, level=ALPHA_CI_LEVEL, n_boot=BOOT_REPS, seed=PIPELINE_SEED) -> AlphaStats:
    # S2 spec §3.3: alpha CI from Newey-West (HAC) with lag ~ T^(1/4); block bootstrap
    # as cross-check; on material disagreement widen to the looser of the two (§3.3).
    resid = fit.resid
    t = len(resid)
    lag = max(0, round(t ** (1.0 / 4.0)))
    # S2 spec §3.3 — NW sandwich [0,0]: residual-mean HAC understates intercept SE when factors have nonzero mean
    se_hac_monthly = _newey_west_intercept_se(fit.design, resid, lag)
    z = _z(level)
    hac_half = z * se_hac_monthly * MONTHS_PER_YEAR
    hac_ci = (fit.alpha_annual - hac_half, fit.alpha_annual + hac_half)
    boot_ci = _block_bootstrap_mean_ci(resid, fit.alpha_annual, level, n_boot, seed)
    # Widen to the looser interval (S2 spec §3.3).
    lo = min(hac_ci[0], boot_ci[0])
    hi = max(hac_ci[1], boot_ci[1])
    ci = (lo, hi)
    return AlphaStats(
        alpha_annual=fit.alpha_annual,
        hac_ci=hac_ci,
        boot_ci=boot_ci,
        ci=ci,
        crosses_zero=bool(ci[0] <= 0.0 <= ci[1]),
    )


def _newey_west_intercept_se(design, resid, lag):
    # HAC (Newey-West) sandwich SE of the OLS intercept (S2 spec §3.3).
    # X = design [1, factors] (T×k), e = OLS residuals, Q = (X'X)^-1.
    # Gamma_j = sum_t (x_t e_t)(x_{t-j} e_{t-j})' (k×k outer products).
    # S = Gamma_0 + sum_{j=1..lag} w_j (Gamma_j + Gamma_j'), Bartlett w_j = 1 - j/(lag+1).
    # V = Q S Q; the monthly intercept SE is sqrt(V[0,0]).
    x = np.asarray(design, dtype=float)
    e = np.asarray(resid, dtype=float)
    q = np.linalg.inv(x.T @ x)
    scores = x * e[:, None]  # rows x_t e_t
    s = scores.T @ scores  # Gamma_0
    for j in range(1, lag + 1):
        weight = 1.0 - j / (lag + 1)  # Bartlett kernel
        gamma_j = scores[j:].T @ scores[:-j]
        s += weight * (gamma_j + gamma_j.T)
    v = q @ s @ q
    return float(np.sqrt(v[0, 0]))


def _block_bootstrap_mean_ci(resid, alpha_annual, level, n_boot, seed):
    t = len(resid)
    block = max(1, round(t ** (1.0 / 3.0)))
    rng = np.random.default_rng([seed, 43])
    n_blocks = int(np.ceil(t / block))
    means = np.empty(n_boot)
    for b in range(n_boot):
        starts = rng.integers(0, t, size=n_blocks)
        offsets = (starts[:, None] + np.arange(block)[None, :]) % t
        means[b] = resid[offsets.ravel()[:t]].mean()
    lo_q, hi_q = np.quantile(means, [(1 - level) / 2, 1 - (1 - level) / 2])
    # resid mean is ~0 by OLS construction; shift the bootstrap spread onto the point alpha.
    spread_lo = (lo_q - means.mean()) * MONTHS_PER_YEAR
    spread_hi = (hi_q - means.mean()) * MONTHS_PER_YEAR
    return (alpha_annual + spread_lo, alpha_annual + spread_hi)


def mppm(returns, rf, rho=MPPM_RHO) -> float:
    # S2 spec §3.4, Goetzmann-Ingersoll-Spiegel-Welch: manipulation-proof measure.
    returns = np.asarray(returns, dtype=float)
    rf = np.asarray(rf, dtype=float)
    dt = 1.0 / MONTHS_PER_YEAR
    ratio = (1.0 + returns) / (1.0 + rf)
    inner = np.mean(ratio ** (1.0 - rho))
    return float(np.log(inner) / ((1.0 - rho) * dt))
