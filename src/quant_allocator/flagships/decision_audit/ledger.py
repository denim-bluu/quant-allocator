"""P3 spec 3.2-3.4 — deterministic event-time accounting. No estimator here.

Everything is in EVENT TIME: month 0 is the decision date. Forward gaps are
compounded excess returns; the factor-adjusted variant reuses the S2 factor
regression (imported, never re-implemented). The counterfactual resolver walks
the spec 3.3 hierarchy (replacement-paired -> peer-median -> benchmark) and
labels the rung it used on every event. Sign conventions (spec 3.4) are unified
so POSITIVE always means the decision helped.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from quant_allocator.flagships.tearsheet import pipeline as tp

MONTHS_PER_YEAR = 12
# spec 3.2: every event is tracked forward over these horizons.
AUDIT_HORIZONS_YEARS = (1, 2, 3)
# NUMERICS-GATE P3-D4: dead-band for the per-event value verdict chip. |V_e| below this
# reads "flat"; above, "helped"/"hurt". Provisional 0.5% cumulative — small enough
# that a real gap always resolves, large enough that rounding noise is not a verdict.
VALUE_VERDICT_EPS = 0.005


@dataclass(frozen=True)
class AuditWorld:
    months: tuple[str, ...]
    returns_by_manager: dict[str, np.ndarray]
    strategy_by_manager: dict[str, str]
    factors: np.ndarray
    factor_names: tuple[str, ...]
    rf_monthly: np.ndarray
    benchmark_by_strategy: dict[str, np.ndarray]


@dataclass(frozen=True)
class EventResult:
    decision_type: str
    manager_id: str
    decision_date: str
    horizon_years: int
    counterfactual_rung: str
    subject_forward: float
    counterfactual_forward: float
    forward_gap_raw: float
    forward_gap_factor_adj: float
    value_verdict: str  # "helped" | "hurt" | "flat"
    kill_criterion_met: bool
    thesis: str
    kill_criterion: str
    expected_alpha_annual: float


def month_index(world: AuditWorld, date: str) -> int:
    try:
        return world.months.index(date)
    except ValueError as exc:
        raise ValueError(f"decision_date {date!r} not in world.months") from exc


def _forward_slice(d_index: int, horizon_years: int, length: int) -> slice:
    # spec 3.2: forward window is t = d+1 .. d+12h (whole months, exclusive of month 0).
    end = d_index + MONTHS_PER_YEAR * horizon_years
    if end >= length:
        raise ValueError(
            f"forward window [{d_index + 1}, {end}] exceeds series length {length}"
        )
    return slice(d_index + 1, end + 1)


def forward_excess_return(returns, rf_monthly, d_index: int, horizon_years: int) -> float:
    returns = np.asarray(returns, dtype=float)
    rf_monthly = np.asarray(rf_monthly, dtype=float)
    window = _forward_slice(d_index, horizon_years, len(returns))
    excess = returns[window] - rf_monthly[window]
    return float(np.prod(1.0 + excess) - 1.0)


def forward_cumulative_path(returns, rf_monthly, d_index: int, window_months: int) -> np.ndarray:
    # Event-time cumulative excess wealth-1, starting at 0.0 at month 0.
    returns = np.asarray(returns, dtype=float)
    rf_monthly = np.asarray(rf_monthly, dtype=float)
    end = d_index + window_months
    if end >= len(returns):
        raise ValueError(f"path window exceeds series length {len(returns)}")
    excess = returns[d_index + 1 : end + 1] - rf_monthly[d_index + 1 : end + 1]
    cum = np.cumprod(1.0 + excess) - 1.0
    return np.concatenate([[0.0], cum])


def forward_factor_alpha(
    returns, factors, factor_names, rf_monthly, d_index: int, horizon_years: int
) -> float:
    # spec 3.2: cumulative regression alpha over the forward window. Reuse the S2
    # OLS factor regression (intercept = monthly alpha); compound it over the window.
    returns = np.asarray(returns, dtype=float)
    factors = np.asarray(factors, dtype=float)
    rf_monthly = np.asarray(rf_monthly, dtype=float)
    window = _forward_slice(d_index, horizon_years, len(returns))
    excess = returns[window] - rf_monthly[window]
    fit = tp.regress(excess, factors[window], factor_names)
    months = MONTHS_PER_YEAR * horizon_years
    return float((1.0 + fit.alpha_monthly) ** months - 1.0)


def _peer_ids(world: AuditWorld, strategy: str, exclude: set[str]) -> list[str]:
    return sorted(
        mid
        for mid, strat in world.strategy_by_manager.items()
        if strat == strategy and mid not in exclude
    )


def _peer_median_forward(world, strategy, d_index, horizon_years, exclude) -> float:
    peers = _peer_ids(world, strategy, exclude)
    vals = [
        forward_excess_return(world.returns_by_manager[mid], world.rf_monthly, d_index, horizon_years)
        for mid in peers
    ]
    return float(np.median(vals))


def _peer_median_factor_alpha(world, strategy, d_index, horizon_years, exclude) -> float:
    peers = _peer_ids(world, strategy, exclude)
    vals = [
        forward_factor_alpha(
            world.returns_by_manager[mid], world.factors, world.factor_names,
            world.rf_monthly, d_index, horizon_years,
        )
        for mid in peers
    ]
    return float(np.median(vals))


def _resolve_counterfactual(record, world, d_index, exclude):
    # spec 3.3 hierarchy, most-paired first; returns (rung, cf_raw, cf_factor_adj).
    strategy = world.strategy_by_manager[record.manager_id]
    h = record.horizon_years
    if record.counterfactual in world.returns_by_manager:
        cf_returns = world.returns_by_manager[record.counterfactual]
        cf_raw = forward_excess_return(cf_returns, world.rf_monthly, d_index, h)
        cf_fa = forward_factor_alpha(
            cf_returns, world.factors, world.factor_names, world.rf_monthly, d_index, h
        )
        return "replacement-paired", cf_raw, cf_fa
    if record.counterfactual == "peer-median":
        cf_raw = _peer_median_forward(world, strategy, d_index, h, exclude)
        cf_fa = _peer_median_factor_alpha(world, strategy, d_index, h, exclude)
        return "peer-median", cf_raw, cf_fa
    if record.counterfactual == "benchmark":
        bench = world.benchmark_by_strategy[strategy]
        cf_raw = forward_excess_return(bench, world.rf_monthly, d_index, h)
        cf_fa = forward_factor_alpha(
            bench, world.factors, world.factor_names, world.rf_monthly, d_index, h
        )
        return "benchmark", cf_raw, cf_fa
    raise ValueError(f"unresolvable counterfactual {record.counterfactual!r}")


def _value_verdict(v: float) -> str:
    if v > VALUE_VERDICT_EPS:
        return "helped"
    if v < -VALUE_VERDICT_EPS:
        return "hurt"
    return "flat"


def resolve_event(record, world: AuditWorld) -> EventResult:
    d_index = month_index(world, record.decision_date)
    h = record.horizon_years
    subject = world.returns_by_manager[record.manager_id]
    sub_raw = forward_excess_return(subject, world.rf_monthly, d_index, h)
    sub_fa = forward_factor_alpha(
        subject, world.factors, world.factor_names, world.rf_monthly, d_index, h
    )
    exclude = {record.manager_id}
    if record.counterfactual in world.returns_by_manager:
        exclude.add(record.counterfactual)
    rung, cf_raw, cf_fa = _resolve_counterfactual(record, world, d_index, exclude)

    # spec 3.4 unified signs: positive = the decision helped.
    if record.decision_type == "fire":
        v_raw = cf_raw - sub_raw       # replacement - fired
        v_fa = cf_fa - sub_fa
    else:                              # hire or hold-under-review
        v_raw = sub_raw - cf_raw       # subject - counterfactual
        v_fa = sub_fa - cf_fa

    # Ex-post read of the pre-committed criterion: the forward realized factor alpha over
    # the horizon measured against the pre-set bar — did the outcome trip the bar the
    # allocator committed to, not a re-derivation of a trailing signal.
    realized_alpha_annual = (1.0 + sub_fa) ** (1.0 / h) - 1.0
    kill_met = bool(realized_alpha_annual < record.kill_alpha_threshold_annual)

    return EventResult(
        decision_type=record.decision_type,
        manager_id=record.manager_id,
        decision_date=record.decision_date,
        horizon_years=h,
        counterfactual_rung=rung,
        subject_forward=sub_raw,
        counterfactual_forward=cf_raw,
        forward_gap_raw=v_raw,
        forward_gap_factor_adj=v_fa,
        value_verdict=_value_verdict(v_raw),
        kill_criterion_met=kill_met,
        thesis=record.thesis,
        kill_criterion=record.kill_criterion,
        expected_alpha_annual=record.expected_alpha_annual,
    )


def resolve_events(records, world: AuditWorld) -> list[EventResult]:
    return [resolve_event(record, world) for record in records]
