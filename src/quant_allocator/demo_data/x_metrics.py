"""Shared-grid metric kernels: one pure function per (analytic, tier) detection
rule from X1 spec §3.2. No simulation, no cross-cell logic — the grid engine
(x_grid.py) calls these per simulated manager and aggregates the results.

Numeric outputs feed generators HELD FOR THE NUMERICS GATE.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

MONTHS_PER_YEAR = 12
DETECT_Z = 1.96  # X1 spec §3.2: |t| > 1.96 / two-sided 5%.


@dataclass(frozen=True)
class Estimate:
    point: float
    se: float
    tstat: float
    detected: bool
    true: float


def _ols_intercept_se(y: np.ndarray, design: np.ndarray) -> tuple[float, float]:
    coef, *_ = np.linalg.lstsq(design, y, rcond=None)
    resid = y - design @ coef
    dof = len(y) - design.shape[1]
    sigma2 = float(resid @ resid) / dof
    cov = sigma2 * np.linalg.inv(design.T @ design)
    return float(coef[0]), float(np.sqrt(cov[0, 0]))


def ols_alpha(returns, factors, true_alpha) -> Estimate:
    # X1 spec §3.2: OLS alpha t-test at tier R (betas estimated from returns).
    returns = np.asarray(returns, dtype=float)
    factors = np.asarray(factors, dtype=float)
    design = np.column_stack([np.ones(len(returns)), factors])
    alpha_m, se_m = _ols_intercept_se(returns, design)
    alpha_ann = alpha_m * MONTHS_PER_YEAR
    se_ann = se_m * MONTHS_PER_YEAR
    tstat = alpha_ann / se_ann if se_ann > 0 else 0.0
    return Estimate(alpha_ann, se_ann, tstat, abs(tstat) > DETECT_Z, float(true_alpha))


def pinned_alpha(returns, betas_path, factors, true_alpha) -> Estimate:
    # X1 spec §3.2 (tier E/P): betas PINNED to true emitted exposures; alpha is the
    # residual mean once the known systematic return is removed (S1 §3.3 mechanism).
    returns = np.asarray(returns, dtype=float)
    betas_path = np.asarray(betas_path, dtype=float)
    factors = np.asarray(factors, dtype=float)
    systematic = (betas_path * factors).sum(axis=1)
    resid = returns - systematic
    t = len(resid)
    alpha_ann = float(resid.mean()) * MONTHS_PER_YEAR
    se_ann = float(resid.std(ddof=1) / np.sqrt(t)) * MONTHS_PER_YEAR
    tstat = alpha_ann / se_ann if se_ann > 0 else 0.0
    return Estimate(alpha_ann, se_ann, tstat, abs(tstat) > DETECT_Z, float(true_alpha))


def sharpe_lo(returns) -> Estimate:
    # X1 spec §3.2: Sharpe CI (Lo SE) excludes 0. Annualize point and SE by sqrt(12).
    returns = np.asarray(returns, dtype=float)
    t = len(returns)
    sr_m = float(returns.mean() / returns.std(ddof=1))
    se_m = float(np.sqrt((1.0 + sr_m**2 / 2.0) / t))
    root12 = np.sqrt(MONTHS_PER_YEAR)
    sr_ann = sr_m * root12
    se_ann = se_m * root12
    tstat = sr_ann / se_ann if se_ann > 0 else 0.0
    detected = not (sr_ann - DETECT_Z * se_ann <= 0.0 <= sr_ann + DETECT_Z * se_ann)
    return Estimate(sr_ann, se_ann, tstat, detected, float("nan"))


def hit_rate(contributions, n_trades) -> Estimate:
    # X1 spec §3.2: hit rate vs 0.5 by a binomial test (normal approx on n_trades).
    # NUMERICS-GATE (docket D-9): n_trades is the grid engine's independent-trade
    # proxy (turnover-derived count), not len(contributions); provisional pending
    # confirmation of the exact construction.
    contributions = np.asarray(contributions, dtype=float)
    nonzero = contributions[contributions != 0.0]
    p_hat = float((nonzero > 0.0).mean()) if len(nonzero) else 0.5
    se = float(np.sqrt(0.25 / n_trades)) if n_trades > 0 else 0.0
    tstat = (p_hat - 0.5) / se if se > 0 else 0.0
    return Estimate(p_hat, se, tstat, abs(tstat) > DETECT_Z, 0.5)


def sizing_slope(sizes, contributions) -> Estimate:
    # X1 spec §3.2: sizing-curve slope t > 1.96 vs an equal-weight counterfactual —
    # here, the OLS slope of contribution on |position size| pooled over the window.
    # NUMERICS-GATE (docket D-10): pooling per-position-month (|weight|, contribution)
    # pairs and regressing contribution on |weight| is the provisional construction
    # of "slope vs equal-weight counterfactual"; pending confirmation.
    sizes = np.abs(np.asarray(sizes, dtype=float))
    contributions = np.asarray(contributions, dtype=float)
    design = np.column_stack([np.ones(len(sizes)), sizes])
    coef, *_ = np.linalg.lstsq(design, contributions, rcond=None)
    resid = contributions - design @ coef
    dof = len(sizes) - 2
    sigma2 = float(resid @ resid) / dof if dof > 0 else 0.0
    cov = sigma2 * np.linalg.inv(design.T @ design)
    slope = float(coef[1])
    se = float(np.sqrt(cov[1, 1]))
    tstat = slope / se if se > 0 else 0.0
    return Estimate(slope, se, tstat, tstat > DETECT_Z, 0.0)
