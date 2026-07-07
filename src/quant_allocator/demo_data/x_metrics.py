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


def hit_rate(contributions_by_month, gate_quantity) -> Estimate:
    # X1 spec §3.2: hit rate vs 0.5, tested by a month-clustered t-test on the
    # monthly hit fractions h_t. Input is the ACTIVE (equal-weight-counterfactual)
    # contribution matrix w*(r - r_bar_month) — RULING 5, built in
    # x_grid._simulate_rep — which zeroes the net-long drift bias at IC=0.
    # NUMERICS-GATE (docket D-9) gate ruling 2026-07-07: month-clustered t-test
    # (cross-positional correlation makes any pooled-n binomial miscalibrated);
    # proxy labels the gate axis only.
    # h_t autocorrelation measured ≈ 0 post-demeaning; plain clustered SE suffices —
    # NW variant tested and rejected at the gate, see c-gate-fix-report Round 3.
    del gate_quantity
    contributions = np.asarray(contributions_by_month, dtype=float)
    monthly_fractions = []
    for month_row in contributions:
        nonzero = month_row[month_row != 0.0]
        if len(nonzero):
            monthly_fractions.append(float((nonzero > 0.0).mean()))
    # Display point stays the pooled hit rate over all nonzero position-months.
    all_nonzero = contributions[contributions != 0.0]
    p_hat = float((all_nonzero > 0.0).mean()) if len(all_nonzero) else 0.5
    if len(monthly_fractions) < 2:
        return Estimate(p_hat, 0.0, 0.0, False, 0.5)
    h = np.asarray(monthly_fractions, dtype=float)
    se = float(h.std(ddof=1) / np.sqrt(len(h)))  # clustered SE of the monthly mean
    tstat = (float(h.mean()) - 0.5) / se if se > 0 else 0.0
    return Estimate(p_hat, se, tstat, abs(tstat) > DETECT_Z, 0.5)


def sizing_slope(sizes_by_month, contributions_by_month) -> Estimate:
    # X1 spec §3.2: sizing-curve slope t > 1.96 vs an equal-weight counterfactual.
    # NUMERICS-GATE (docket D-10) gate ruling 2026-07-07 (RULING 5): the input
    # contribution is w*(r - r_bar_month), so the slope IS "slope vs an
    # equal-weight counterfactual" in the spec's own wording.
    # gate ruling 2026-07-07: Fama–MacBeth — within-month cross-positional
    # correlation understates the pooled OLS SE ~40% (measured t-sd 1.66);
    # month-clustering for a cross-sectional slope, mirroring the hit-rate ruling.
    # The DISPLAYED point is mean(b_t) itself: displaying one estimator while
    # testing another is the label/inference mismatch this gate already rejected.
    sizes = np.abs(np.asarray(sizes_by_month, dtype=float))
    contributions = np.asarray(contributions_by_month, dtype=float)
    monthly_slopes = []
    for size_row, contrib_row in zip(sizes, contributions):
        held = size_row != 0.0
        x = size_row[held]
        # Guard: a month with ~zero cross-sectional std of |size| is a
        # near-singular per-month regression (relevant at sizing_discipline=0) —
        # skip it.
        if held.sum() < 3 or float(x.std()) < 1e-12:
            continue
        x_centered = x - x.mean()
        monthly_slopes.append(
            float((x_centered @ contrib_row[held]) / (x_centered @ x_centered))
        )
    # Guard: fewer than 3 usable months -> no Fama-MacBeth inference.
    if len(monthly_slopes) < 3:
        return Estimate(0.0, 0.0, 0.0, False, 0.0)
    b = np.asarray(monthly_slopes, dtype=float)
    point = float(b.mean())
    se = float(b.std(ddof=1) / np.sqrt(len(b)))
    tstat = point / se if se > 0 else 0.0
    return Estimate(point, se, tstat, tstat > DETECT_Z, 0.0)
