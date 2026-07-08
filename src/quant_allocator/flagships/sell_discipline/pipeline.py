"""S4 spec §3 — the sell-discipline counterfactual gap. Pure functions, no I/O.

S4 owns its OWN exit alignment (spec §8.4: no shared S3/S4 event-study kernel in v1).
An exit is a held-then-gone transition in a position-transparency weights frame; the
gap scores the sold name's forward residual against the equal-weighted incumbent pool
it was sold out of (the closed-form random-sell counterfactual, spec §3.3), and the
curve renders that gap at every forward horizon (spec §3.5). Uncertainty is IMPORTED
from P3 (cohort_block_bootstrap, design_effect) with the calendar month as the cohort;
the roster view is IMPORTED from S1 (shrink_alphas). No estimator is re-implemented here.

Numeric outputs feed a demo generator HELD FOR THE NUMERICS GATE.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

# Spec §8.7 constants (confirmed at the method-review gate).
S4_HORIZON_MONTHS = 4          # headline forgone-alpha horizon; the slider renders 1..MAX.
S4_MAX_HORIZON_MONTHS = 6      # slider maximum (spec §5).
S4_BOOTSTRAP_REPS = 2000       # month-cohort block-bootstrap reps (reuses P3's convention).
S4_MIN_EXITS_GAP = 150         # headline gap refuses below this (spec §6.3 / §8.7).
S4_MIN_EXITS_BUCKET = 60       # trend buckets below this are refused (spec §3.7 / §8.7).
# NUMERICS-GATE S4-D1: minimum-detectable-gap multiplier = 2.8 x se (5% size, 80% power,
# spec §6.3). The gate confirms the two-sided normal-approximation constant.
S4_MDG_FACTOR = 2.8
# NUMERICS-GATE S4-D2: block-bootstrap seed (deterministic band; P3 owns stream tag 11).
S4_BOOTSTRAP_SEED = 20260707


@dataclass(frozen=True)
class ExitEvent:
    exit_month: int   # execution month e (spec §3.3 tau_e): first month the name is absent.
    name: str


@dataclass(frozen=True)
class GapResult:
    n_exits: int
    horizon: int
    gap: float                    # CG(H): mean per-exit gap at the given horizon.
    per_exit_gaps: np.ndarray     # (n,) per-exit gap at the given horizon.
    exit_months: np.ndarray       # (n,) execution-month cohort ids for the block bootstrap.
    curve: np.ndarray             # (horizon,) C(h): cumulative average out-performance.
    per_exit_curve: np.ndarray    # (n, horizon) per-exit cumulative curve.


def extract_exits(weights: pd.DataFrame) -> list[ExitEvent]:
    # Full-liquidation exits only (spec §6.1 / §8.6: S4_PARTIAL_TRIMS = full exits only).
    held = weights.to_numpy() != 0.0
    names = list(weights.columns)
    n_months = held.shape[0]
    exits: list[ExitEvent] = []
    for col, name in enumerate(names):
        for e in range(1, n_months):
            if held[e - 1, col] and not held[e, col]:
                exits.append(ExitEvent(exit_month=e, name=name))
    exits.sort(key=lambda ev: (ev.exit_month, ev.name))
    return exits


def holdings_by_month(weights: pd.DataFrame) -> list[set[str]]:
    held = weights.to_numpy() != 0.0
    names = np.array(weights.columns)
    return [set(names[held[m]].tolist()) for m in range(held.shape[0])]


def counterfactual_gap(
    residuals: pd.DataFrame,
    holdings: list[set[str]],
    exits: list[ExitEvent],
    horizon: int,
) -> GapResult:
    # residuals: months x assets factor-adjusted returns (the simulator's ground-truth
    # idio in the demo, zero estimation error, spec §3.4).
    resid = residuals.to_numpy()
    col_of = {name: i for i, name in enumerate(residuals.columns)}
    n_months = resid.shape[0]

    per_exit_curve: list[np.ndarray] = []
    months: list[int] = []
    for ev in exits:
        e, j = ev.exit_month, ev.name
        if e + horizon > n_months - 1:      # need residual rows e+1 .. e+horizon
            continue
        pool = sorted(holdings[e - 1] - {j})
        if not pool:
            continue
        pool_cols = [col_of[k] for k in pool]
        sold_fwd = resid[e + 1 : e + 1 + horizon, col_of[j]]            # (horizon,)
        pool_fwd = resid[e + 1 : e + 1 + horizon, pool_cols].mean(axis=1)  # (horizon,)
        # Cumulative per-horizon gap: C(h) contribution for this exit (spec §3.5).
        gap_path = np.cumsum(sold_fwd) - np.cumsum(pool_fwd)
        per_exit_curve.append(gap_path)
        months.append(e)

    if not per_exit_curve:
        raise ValueError("no exits have a full forward window at the requested horizon")

    curve_matrix = np.vstack(per_exit_curve)          # (n, horizon)
    per_exit_gaps = curve_matrix[:, horizon - 1]      # gap at the requested horizon
    return GapResult(
        n_exits=curve_matrix.shape[0],
        horizon=horizon,
        gap=float(per_exit_gaps.mean()),
        per_exit_gaps=per_exit_gaps,
        exit_months=np.asarray(months, dtype=int),
        curve=curve_matrix.mean(axis=0),
        per_exit_curve=curve_matrix,
    )


from quant_allocator.flagships.decision_audit.aggregate import (   # noqa: E402
    cohort_block_bootstrap,
    design_effect,
)
from quant_allocator.flagships.skill_ledger.empirical import (     # noqa: E402
    ShrinkageResult,
    shrink_alphas,
)


def intra_cohort_correlation_signed(values, cohort_ids) -> float:
    # One-way random-effects ICC(1) WITHOUT P3's [0, 1] clamp: a selective exit rule
    # stratifies month cohorts, giving rho_c < 0 and a design effect below 1 (spec §3.6).
    # P3's clamped intra_cohort_correlation is a monitor-side false-alarm guard and would
    # suppress exactly the sub-1 deff S4 must report, so S4 keeps its own signed version.
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
    m0 = (n - sum(s * s for s in sizes) / n) / (k - 1)
    denom = ms_between + (m0 - 1) * ms_within
    if denom == 0:
        return 0.0
    return float((ms_between - ms_within) / denom)   # UNCLAMPED (can be negative)


@dataclass(frozen=True)
class GapBand:
    se: float
    ci_lo: float
    ci_hi: float
    design_effect: float
    intra_cohort_rho: float
    events_per_cohort: float
    n_cohorts: int
    min_detectable_gap: float
    gated: bool


def gap_band(result, *, reps=S4_BOOTSTRAP_REPS, seed=S4_BOOTSTRAP_SEED,
             min_exits=S4_MIN_EXITS_GAP) -> GapBand:
    se, (lo, hi) = cohort_block_bootstrap(
        result.per_exit_gaps, result.exit_months, reps, seed)
    cohorts = list(dict.fromkeys(result.exit_months.tolist()))
    m_bar = result.n_exits / len(cohorts) if cohorts else float(result.n_exits)
    rho = intra_cohort_correlation_signed(result.per_exit_gaps, result.exit_months)
    return GapBand(
        se=se, ci_lo=lo, ci_hi=hi,
        design_effect=design_effect(m_bar, rho),
        intra_cohort_rho=rho,
        events_per_cohort=m_bar,
        n_cohorts=len(cohorts),
        min_detectable_gap=S4_MDG_FACTOR * se,
        gated=bool(result.n_exits < min_exits),
    )


def curve_band(result, *, reps=S4_BOOTSTRAP_REPS, seed=S4_BOOTSTRAP_SEED):
    # One month-cohort bootstrap band per forward horizon column (spec §3.5 curve band).
    bands: list[tuple[float, float, float]] = []
    for h in range(result.horizon):
        _se, (lo, hi) = cohort_block_bootstrap(
            result.per_exit_curve[:, h], result.exit_months, reps, seed)
        bands.append((float(result.curve[h]), float(lo), float(hi)))
    return bands


@dataclass(frozen=True)
class BucketStat:
    label: str
    n_exits: int
    gap: float
    ci_lo: float
    ci_hi: float
    se: float
    sufficient: bool


def trend_buckets(per_exit_gaps, exit_months, bucket_labels, *,
                  reps=S4_BOOTSTRAP_REPS, seed=S4_BOOTSTRAP_SEED,
                  min_exits=S4_MIN_EXITS_BUCKET) -> list[BucketStat]:
    # A descriptive within-manager series (spec §3.7): NOT a persistence test. Each
    # bucket's band resamples its own month cohorts; buckets below min_exits are refused.
    gaps = np.asarray(per_exit_gaps, dtype=float)
    months = np.asarray(exit_months)
    labels = np.asarray(bucket_labels)
    out: list[BucketStat] = []
    for label in dict.fromkeys(labels.tolist()):
        mask = labels == label
        g = gaps[mask]
        se, (lo, hi) = cohort_block_bootstrap(g, months[mask], reps, seed)
        out.append(BucketStat(
            label=str(label), n_exits=int(mask.sum()), gap=float(g.mean()),
            ci_lo=float(lo), ci_hi=float(hi), se=se,
            sufficient=bool(mask.sum() >= min_exits)))
    return out


def roster_shrink(gaps, ses) -> ShrinkageResult:
    # Spec §3.7 roster view: shrink per-manager gaps toward the transparent-roster mean
    # via S1's closed-form empirical-Bayes (imported, never re-fit). One roster group.
    gaps = np.asarray(gaps, dtype=float)
    return shrink_alphas(gaps, np.asarray(ses, dtype=float), np.zeros(len(gaps), dtype=int))


def verdict_chip(band: GapBand) -> str:
    # Sign convention (spec §3.2): positive gap = sold names beat the book = the exits
    # leak; negative = the exits cull well; a straddle = no better than a random sell.
    if band.ci_hi < 0.0:
        return "culls well"
    if band.ci_lo > 0.0:
        return "edge leaks at the exit"
    return "indistinguishable from a random sell"
