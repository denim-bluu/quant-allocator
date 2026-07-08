"""S3 §3 sizing & alpha-decay lab — pure functions over a position panel.

Every diagnostic is trade-level and therefore power-gated (S3 §1). The sizing
slope IS the X1 grid's Fama-MacBeth kernel (x_metrics.sizing_slope, §6.9/§8.5) —
this module only assembles its (|w|, active-contribution) inputs. The decay and
holding legs are S3's own pure functions (§8 ruling 5: no shared S3/S4 kernel in
v1). No rendering, no I/O; numeric outputs feed a generator HELD FOR THE NUMERICS
GATE.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass

import numpy as np

from quant_allocator.demo_data.x_metrics import Estimate, sizing_slope

# NUMERICS-GATE (§8 ruling 4): holding-age buckets (lo, hi inclusive, label).
HOLDING_BUCKETS: tuple[tuple[int, int, str], ...] = (
    (0, 2, "0-2m"), (3, 5, "3-5m"), (6, 11, "6-11m"), (12, 200, "12m+"),
)
# NUMERICS-GATE (§8 ruling 4): cluster-bootstrap resamples for stable 2.5/97.5 tails.
SIZING_BOOTSTRAP_N = 2000
# NUMERICS-GATE (§8 ruling 4): longest holding age the decay curve reaches.
DECAY_MAX_AGE = 12
# NUMERICS-GATE (§8 ruling 4): per-age render floor; ages with fewer entries are not drawn.
MIN_ENTRIES_PER_AGE = 30
# §8 ruling 1: the demo resamples the DATE cluster only (months); date x name is live.
CLUSTER_AXES: tuple[str, ...] = ("date",)
# Named RNG stream tag for every S3 bootstrap (no hash()-derived seeds).
S3_BOOTSTRAP_STREAM = 16

__all__ = [
    "PositionPanel", "DecayCurve", "Interval", "build_panel", "sizing_slope_estimate",
    "annualized_alpha_ir", "decay_curve", "fit_half_life", "holding_decomposition",
    "independent_trades", "cluster_bootstrap", "HOLDING_BUCKETS", "SIZING_BOOTSTRAP_N",
    "DECAY_MAX_AGE", "MIN_ENTRIES_PER_AGE", "CLUSTER_AXES", "S3_BOOTSTRAP_STREAM",
]


@dataclass(frozen=True)
class PositionPanel:
    weights: np.ndarray  # (T, N) signed portfolio weights, 0 where unheld
    idio: np.ndarray     # (T, N) realized idiosyncratic returns
    ages: np.ndarray     # (T, N) int holding age (0 in entry month), -1 where unheld
    side: np.ndarray     # (T, N) +1 long / -1 short / 0 unheld


@dataclass(frozen=True)
class DecayCurve:
    ages: np.ndarray     # (max_age + 1,)
    values: np.ndarray   # D(m): mean directional standardized idio at age m (nan if unpopulated)
    counts: np.ndarray   # |A_m|: position-months behind each D(m)


@dataclass(frozen=True)
class Interval:
    point: float
    lo: float
    hi: float


def build_panel(weights: np.ndarray, idio: np.ndarray) -> PositionPanel:
    """Reconstruct holding ages and side from a signed weight panel (S3 §3.3).

    A name is held iff its weight is nonzero; age is the length of the current
    consecutive-held run (0 in the entry month). This is correct ONLY when every
    re-entry is separated from its prior exit by at least one zero-weight month.
    Books with same-month drop-and-re-add (e.g. the simulator's exit_style="age"
    rule combined with signal-driven re-selection, which can drop and re-select
    a name in the same rebalance with no zero-weight gap in between) will get
    WRONG ages from this function — it cannot detect that case from weights
    alone. Such books must source ages from trade records or a config-aware
    replay, as demo_data/s3_lab.py's `_reconstruct_ages` does.
    """
    weights = np.asarray(weights, dtype=float)
    idio = np.asarray(idio, dtype=float)
    held = weights != 0.0
    ages = np.full(weights.shape, -1, dtype=int)
    for j in range(weights.shape[1]):
        run = -1
        for t in range(weights.shape[0]):
            run = run + 1 if held[t, j] else -1
            ages[t, j] = run
    side = np.sign(weights)
    return PositionPanel(weights=weights, idio=idio, ages=ages, side=side)


def _active_contributions(panel: PositionPanel) -> np.ndarray:
    # c_{i,t} = w · (r̃ − r̄ₜ): weight times return in excess of the equal-weight month.
    hedged = panel.idio - panel.idio.mean(axis=1, keepdims=True)
    return panel.weights * hedged


def sizing_slope_estimate(panel: PositionPanel) -> Estimate:
    # §3.4 Fama-MacBeth slope: assemble (|w|, active contributions) and call the X1 kernel.
    return sizing_slope(np.abs(panel.weights), _active_contributions(panel))


def annualized_alpha_ir(panel: PositionPanel) -> tuple[float, float]:
    # Book idiosyncratic alpha stream and its annualized IR (§4 `annualised`).
    monthly = (panel.weights * panel.idio).sum(axis=1)
    alpha_annual = float(monthly.mean()) * 12.0
    vol = float(monthly.std(ddof=1))
    ir = float(monthly.mean()) / vol * np.sqrt(12.0) if vol > 0 else 0.0
    return alpha_annual, ir


def independent_trades(n_long: int, n_short: int, rebalance_fraction: float, n_months: int) -> int:
    # X1 §3.4 gate quantity: initial book + turnover accumulated over T months.
    # NOTE (see plan Handoff): x_grid._independent_trades hardcodes the atlas book, so it
    # cannot size an arbitrary book; this is the same formula, parameterized for S3's books.
    per_month = round(rebalance_fraction * n_long) + round(rebalance_fraction * n_short)
    return int(n_long + n_short + per_month * n_months)


def cluster_bootstrap(
    statistic: Callable[[PositionPanel], float],
    panel: PositionPanel,
    n: int,
    rng: np.random.Generator,
) -> Interval:
    # §3.7 date-cluster bootstrap: resample whole months with replacement, recompute, read
    # the 2.5/97.5 percentiles. Months are the dominant effective-N killer (a factor month
    # moves every held position at once); date x name is the live extension.
    n_months = panel.weights.shape[0]
    draws = np.empty(n)
    for b in range(n):
        idx = rng.integers(0, n_months, n_months)
        resampled = PositionPanel(
            weights=panel.weights[idx], idio=panel.idio[idx],
            ages=panel.ages[idx], side=panel.side[idx],
        )
        draws[b] = statistic(resampled)
    return Interval(
        point=float(statistic(panel)),
        lo=float(np.percentile(draws, 2.5)),
        hi=float(np.percentile(draws, 97.5)),
    )


def decay_curve(
    panels: Sequence[PositionPanel], idio_vol: float, max_age: int = DECAY_MAX_AGE
) -> DecayCurve:
    # §3.5 event-time curve: pool positions across panels by holding age m, average the
    # directional standardized idio side·(r̃/σ). Ages below MIN_ENTRIES_PER_AGE stay nan so the
    # curve truncates where turnover stops holding names long enough to observe decay (§6.3).
    total = np.zeros(max_age + 1)
    count = np.zeros(max_age + 1)
    for panel in panels:
        z = panel.idio / idio_vol
        for m in range(max_age + 1):
            rows, cols = np.where((panel.ages == m) & (panel.weights != 0.0))
            if len(rows):
                total[m] += float(np.sum(panel.side[rows, cols] * z[rows, cols]))
                count[m] += len(rows)
    values = np.divide(total, count, out=np.full(max_age + 1, np.nan), where=count > 0)
    values[count < MIN_ENTRIES_PER_AGE] = np.nan
    return DecayCurve(ages=np.arange(max_age + 1), values=values, counts=count)


def fit_half_life(curve: DecayCurve, ages_used: np.ndarray) -> float:
    # §3.5: H = -ln 2 / slope of log D(m) on age, fit over ages_used (>= 1 to drop the
    # entry-selection premium). Only finite, positive D(m) contribute.
    ages_used = np.asarray(ages_used)
    values = curve.values[ages_used]
    ok = np.isfinite(values) & (values > 0)
    if ok.sum() < 2:
        return float("nan")
    slope = np.polyfit(ages_used[ok], np.log(values[ok]), 1)[0]
    return float(-np.log(2.0) / slope)


def holding_decomposition(
    panel: PositionPanel, buckets: tuple[tuple[int, int, str], ...] = HOLDING_BUCKETS
) -> dict[str, float]:
    # §3.6: share of total idiosyncratic alpha w·r̃ attributable to each holding-age bucket.
    contribution = panel.weights * panel.idio
    total = float(contribution.sum())
    held = panel.weights != 0.0
    return {
        label: float(contribution[(panel.ages >= lo) & (panel.ages <= hi) & held].sum()) / total
        for lo, hi, label in buckets
    }
