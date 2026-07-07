"""M3 §3 alarm layer — pure functions over the S2 null-drawdown troughs.

The alarm statistic is the path max-drawdown (MDD): one scalar per null path, so
an alpha-level MDD test has EXACTLY an alpha familywise false-alarm rate by
construction (M3 spec §3.2) — no multiplicity correction to tune, unlike S2's
pointwise band. This module imports the S2 MC primitive; it re-derives no estimator
(M3 spec §5). No rendering, no I/O.

Numeric outputs feed a demo generator HELD FOR THE NUMERICS GATE.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from quant_allocator.flagships.tearsheet.pipeline import (
    MONTHS_PER_YEAR,
    DrawdownHypothesis,
    _drawdown_path,
    _fit_ar1,
    simulate_null_drawdowns,
)

# NUMERICS-GATE: MC path count ruled at 10_000 (stable 1%-tail quantiles under the
# nested posterior draw need more than S2's 2_000). Verified at the numerics gate.
DRAWDOWN_PATHS_M3 = 10_000
# NUMERICS-GATE ALARM_LEVELS (provisional — AMBER 5% / RED 1% per review window).
AMBER_BUDGET = 0.05
RED_BUDGET = 0.01
# Decorrelated from S2's PIPELINE_SEED (20260706) so the M3 null draws are independent.
ALARM_SEED = 20260707
# Posterior-predictive draws use a distinct RNG stream tag from the point null (7).
POSTERIOR_STREAM = 11
# NUMERICS-GATE (provisional — 2): consecutive months inside the clear line required to step down.
HYSTERESIS_CLEAR_MONTHS = 2

__all__ = [
    "DrawdownHypothesis",
    "PosteriorHypothesis",
    "AlarmBand",
    "AlarmVerdict",
    "max_drawdown_null",
    "familywise_band",
    "alarm_state",
    "hysteresis_sequence",
    "simulate_null_drawdowns",
    "DRAWDOWN_PATHS_M3",
    "AMBER_BUDGET",
    "RED_BUDGET",
    "ALARM_SEED",
]


@dataclass(frozen=True)
class PosteriorHypothesis:
    """Posterior-informed null (M3 spec §3.6): a fan of Sharpe draws (S1 posterior or
    an authored synthetic posterior) plus a de-smoothed vol. Simulating one path per
    drawn Sharpe yields a posterior-predictive MDD distribution — wider than any plug-in."""

    sharpe_draws: np.ndarray
    vol_annual: float


@dataclass(frozen=True)
class AlarmBand:
    months: np.ndarray
    running_mdd_realized: np.ndarray  # realized max-drawdown-to-date, >= 0
    band_amber: np.ndarray            # 95th-pct running-MDD null quantile (arm line)
    band_red: np.ndarray              # 99th-pct running-MDD null quantile (arm line)


@dataclass(frozen=True)
class AlarmVerdict:
    level: str                    # "green" | "amber" | "red"
    realized_mdd: float           # positive depth
    mdd_percentile: float         # percentile of realized MDD in the null MDD distribution
    amber_threshold: float        # 95th-pct null MDD
    red_threshold: float          # 99th-pct null MDD
    ar1: float
    band: AlarmBand
    roster_size: int | None
    expected_false_red: float | None  # N x RED_BUDGET (M3 spec §3.4), None if roster_size is None
    prev_level: str | None


def max_drawdown_null(troughs: np.ndarray) -> np.ndarray:
    # Per-path MDD = -min over the window (troughs <= 0 -> positive depth). One scalar per
    # path => no multiplicity (M3 spec §3.2).
    return -troughs.min(axis=1)


def familywise_band(troughs: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    # Running max-drawdown-to-date per path, then the alpha-quantile at each month.
    # Monotone non-decreasing (a running max is non-decreasing); at the window end it equals
    # the alpha-quantile of null MDD, so "realized running-MDD exits band_red at t=T" IS the
    # calibrated RED event (M3 spec §3.2 — the answer to gate note D-20).
    running = -np.minimum.accumulate(troughs, axis=1)
    band_amber = np.percentile(running, 100.0 * (1.0 - AMBER_BUDGET), axis=0)
    band_red = np.percentile(running, 100.0 * (1.0 - RED_BUDGET), axis=0)
    return band_amber, band_red


def _null_troughs(hypothesis, ar1, t, *, n_paths, seed):
    # Dispatch on the maintained-hypothesis type (M3 spec §5): a point Sharpe (fallback) or
    # a posterior fan (preferred). Two clearly named simulators, one union-typed entry point.
    if isinstance(hypothesis, PosteriorHypothesis):
        return _simulate_posterior_troughs(hypothesis, ar1, t, n_paths=n_paths, seed=seed)
    return simulate_null_drawdowns(hypothesis, ar1, t, n_paths=n_paths, seed=seed)


def alarm_state(
    returns,
    hypothesis,
    *,
    prev_level: str | None = None,
    roster_size: int | None = None,
    n_paths: int = DRAWDOWN_PATHS_M3,
    seed: int = ALARM_SEED,
) -> AlarmVerdict:
    # Single review-window look (M3 spec §3.2-§3.4). The realized MDD scalar is tested against
    # the null MDD distribution; the level is pinned to familywise quantiles, so the budgets in
    # §3.3 are the DEFINITION of the quantiles, not a hope. Hysteresis over a SEQUENCE of looks
    # is hysteresis_sequence (Task 3); this fresh look sets prev_level for the caller.
    returns = np.asarray(returns, dtype=float)
    t = len(returns)
    realized_dd = _drawdown_path(returns)
    realized_mdd = float(-realized_dd.min())
    ar1 = _fit_ar1(returns)

    troughs = _null_troughs(hypothesis, ar1, t, n_paths=n_paths, seed=seed)
    null_mdd = max_drawdown_null(troughs)
    amber_threshold = float(np.percentile(null_mdd, 100.0 * (1.0 - AMBER_BUDGET)))
    red_threshold = float(np.percentile(null_mdd, 100.0 * (1.0 - RED_BUDGET)))
    mdd_percentile = float((null_mdd < realized_mdd).mean() * 100.0)

    if realized_mdd > red_threshold:
        level = "red"
    elif realized_mdd > amber_threshold:
        level = "amber"
    else:
        level = "green"

    band_amber, band_red = familywise_band(troughs)
    band = AlarmBand(
        months=np.arange(t),
        running_mdd_realized=-np.minimum.accumulate(realized_dd),
        band_amber=band_amber,
        band_red=band_red,
    )
    expected_false_red = None if roster_size is None else roster_size * RED_BUDGET
    return AlarmVerdict(
        level=level,
        realized_mdd=realized_mdd,
        mdd_percentile=mdd_percentile,
        amber_threshold=amber_threshold,
        red_threshold=red_threshold,
        ar1=ar1,
        band=band,
        roster_size=roster_size,
        expected_false_red=expected_false_red,
        prev_level=prev_level,
    )


def _simulate_posterior_troughs(
    posterior: PosteriorHypothesis, ar1: float, t: int, *, n_paths: int, seed: int
) -> np.ndarray:
    # Posterior-predictive null (M3 spec §3.6): draw a Sharpe per path from the posterior fan,
    # simulate the AR(1) path at that Sharpe with de-smoothed vol and fitted AR(1). v1 samples
    # Sharpe only (NUMERICS-GATE NULL_NESTED_MC — vol/AR(1) plugged as points).
    rng = np.random.default_rng([seed, POSTERIOR_STREAM])
    vol_monthly = posterior.vol_annual / np.sqrt(MONTHS_PER_YEAR)
    innovation_sd = vol_monthly * np.sqrt(1.0 - ar1**2)
    sharpe_draws = rng.choice(np.asarray(posterior.sharpe_draws, dtype=float), size=n_paths)
    troughs = np.empty((n_paths, t))
    for i in range(n_paths):
        mean_monthly = sharpe_draws[i] / np.sqrt(MONTHS_PER_YEAR) * vol_monthly
        path = np.empty(t)
        prev = 0.0
        for k in range(t):
            eps = rng.normal(0.0, innovation_sd)
            dev = ar1 * prev + eps
            path[k] = mean_monthly + dev
            prev = dev
        troughs[i] = _drawdown_path(path)
    return troughs


_LEVEL_ORDER = {"green": 0, "amber": 1, "red": 2}


def hysteresis_sequence(
    exceeds_amber: np.ndarray,
    exceeds_red: np.ndarray,
    inside_clear: np.ndarray,
    *,
    clear_months: int = HYSTERESIS_CLEAR_MONTHS,
) -> list[str]:
    # Two-threshold Schmitt trigger (M3 spec §3.5): the arm line (running-MDD vs the 99th/95th
    # band) is not the clear line (current drawdown recovered inside the 95th band). Stepping DOWN
    # a level requires clear_months consecutive months of recovery, killing single-month flapping.
    state = "green"
    below_run = 0
    out: list[str] = []
    for t in range(len(exceeds_amber)):
        if exceeds_red[t]:
            state = "red"
        elif exceeds_amber[t] and state != "red":
            state = "amber"
        below_run = below_run + 1 if inside_clear[t] else 0
        if inside_clear[t] and below_run >= clear_months and _LEVEL_ORDER[state] > 0:
            state = "amber" if state == "red" else "green"
            below_run = 0
        out.append(state)
    return out
