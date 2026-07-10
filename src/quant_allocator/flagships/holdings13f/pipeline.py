"""M6 §3.3 13F emitter: a pure, deterministic view over a signed-weight panel.

emit_13f_long_book down-samples to quarter-ends, crops to longs and 13(f)-eligible names,
and renormalizes the survivors to reported market-value shares. It draws no random numbers
and consumes no RNG stream tag (the overlays.py discipline, M6 §6.6), so a manager never
viewed through it is byte-identical to one who is.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

M6_TOP_N = 5
M6_PERSISTENCE_TOPK = 10
M6_OVERLAP_DEPTH = 25
M6_COVERAGE_MIN = 0.60
M6_OPTION_FLAG_SHARE = 0.10
M6_FILING_LAG_DAYS = 45
M6_CAVEATS = (
    "45-day staleness: every filing is labelled with as-of and known-at dates.",
    "Longs-only: shorts and net exposure are invisible to Form 13F.",
    "Coverage holes: positions omitted under SEC withholding, non-US, and non-equity "
    "positions may be missing.",
    "Option-notional distortion: option lines are excluded from v1 share calculations.",
)


@dataclass(frozen=True)
class Concentration:
    """Exact concentration descriptors for one reported long book."""

    top_n_weight: float
    hhi: float
    effective_names: float


@dataclass(frozen=True)
class HoldingsVerdict:
    """Coverage-gated M6 read with dated receipts and structural caveats."""

    coverage: float
    coverage_pass: bool
    concentration: Concentration | None
    overlap: float | None
    persistence: dict[str, int]
    option_share: float
    option_heavy: bool
    as_of: pd.Timestamp
    known_at: pd.Timestamp
    caveats: tuple[str, ...]


def _aligned_bool(mask: pd.Series | None, index: pd.Index, *, default: bool) -> pd.Series:
    if mask is None:
        return pd.Series(default, index=index, dtype=bool)
    return mask.reindex(index).fillna(default).astype(bool)


def concentration(book: pd.Series, *, top_n: int = M6_TOP_N) -> Concentration:
    """Top-N share, Herfindahl, and inverse-Herfindahl effective name count."""
    if top_n <= 0:
        raise ValueError(f"top_n must be positive, got {top_n}")
    values = book.fillna(0.0).to_numpy(dtype=float)
    if np.any(values < 0.0):
        raise ValueError("reported book shares must be non-negative")
    top_weight = float(np.sort(values)[::-1][:top_n].sum())
    hhi = float(values @ values)
    effective = float("inf") if hhi == 0.0 else 1.0 / hhi
    return Concentration(top_n_weight=top_weight, hhi=hhi, effective_names=effective)


def conviction_persistence(
    panel: pd.DataFrame, *, k: int = M6_PERSISTENCE_TOPK
) -> dict[str, int]:
    """Consecutive reported quarters for the latest quarter's positive top-K names."""
    if k <= 0:
        raise ValueError(f"k must be positive, got {k}")
    if panel.empty:
        return {}
    latest = panel.iloc[-1]
    names = latest[latest > 0.0].sort_values(ascending=False, kind="stable").index[:k]
    held = panel.gt(0.0)
    out: dict[str, int] = {}
    for name in names:
        run = 0
        for present in held[name].iloc[::-1]:
            if not present:
                break
            run += 1
        out[str(name)] = run
    return out


def cosine_overlap(
    a: pd.Series, b: pd.Series, *, depth: int = M6_OVERLAP_DEPTH
) -> float:
    """Cosine after independently retaining each reported book's top-depth names."""
    if depth <= 0:
        raise ValueError(f"depth must be positive, got {depth}")
    a_top = a.fillna(0.0).nlargest(depth)
    b_top = b.fillna(0.0).nlargest(depth)
    names = a_top.index.union(b_top.index)
    a_values = a_top.reindex(names, fill_value=0.0).to_numpy(dtype=float)
    b_values = b_top.reindex(names, fill_value=0.0).to_numpy(dtype=float)
    denominator = float(np.linalg.norm(a_values) * np.linalg.norm(b_values))
    return 0.0 if denominator == 0.0 else float(a_values @ b_values / denominator)


def coverage_ratio(
    true_weights: pd.Series,
    eligible: pd.Series,
    *,
    option_mask: pd.Series | None = None,
) -> float:
    """Usable 13F share of the true positive long book; shorts never enter."""
    longs = true_weights.clip(lower=0.0).fillna(0.0)
    total = float(longs.sum())
    if total == 0.0:
        return 0.0
    eligible_aligned = _aligned_bool(eligible, longs.index, default=False)
    options = _aligned_bool(option_mask, longs.index, default=False)
    usable = eligible_aligned & ~options
    return float(longs[usable].sum() / total)


def reported_option_share(
    true_weights: pd.Series, eligible: pd.Series, option_mask: pd.Series
) -> float:
    """Option value divided by total reportable positive value before v1 exclusion."""
    longs = true_weights.clip(lower=0.0).fillna(0.0)
    eligible_aligned = _aligned_bool(eligible, longs.index, default=False)
    options = _aligned_bool(option_mask, longs.index, default=False)
    reportable = longs[eligible_aligned]
    total = float(reportable.sum())
    return 0.0 if total == 0.0 else float(longs[eligible_aligned & options].sum() / total)


def holdings_view(
    panel: pd.DataFrame,
    true_weights: pd.Series,
    eligible: pd.Series,
    *,
    peer_book: pd.Series | None = None,
    option_mask: pd.Series | None = None,
    coverage_min: float = M6_COVERAGE_MIN,
    as_of: pd.Timestamp,
    known_at: pd.Timestamp,
) -> HoldingsVerdict:
    """Build the exact visible-crop descriptors and suppress book verdicts on refusal."""
    if panel.empty:
        raise ValueError("panel must contain at least one reported quarter")
    if not 0.0 <= coverage_min <= 1.0:
        raise ValueError(f"coverage_min must be in [0, 1], got {coverage_min}")
    as_of_ts = pd.Timestamp(as_of)
    known_at_ts = pd.Timestamp(known_at)
    if known_at_ts < as_of_ts:
        raise ValueError(f"known_at {known_at_ts} must not precede as_of {as_of_ts}")

    coverage = coverage_ratio(true_weights, eligible, option_mask=option_mask)
    passes = coverage >= coverage_min
    latest = panel.iloc[-1]
    descriptor = concentration(latest) if passes else None
    overlap = cosine_overlap(latest, peer_book) if passes and peer_book is not None else None
    options = _aligned_bool(option_mask, true_weights.index, default=False)
    option_share = reported_option_share(true_weights, eligible, options)
    return HoldingsVerdict(
        coverage=coverage,
        coverage_pass=passes,
        concentration=descriptor,
        overlap=overlap,
        persistence=conviction_persistence(panel),
        option_share=option_share,
        option_heavy=option_share > M6_OPTION_FLAG_SHARE,
        as_of=as_of_ts,
        known_at=known_at_ts,
        caveats=M6_CAVEATS,
    )


def emit_13f_long_book(
    weights: pd.DataFrame,
    quarter_ends: pd.PeriodIndex,
    eligible: pd.Series,
    *,
    option_mask: pd.Series | None = None,
) -> pd.DataFrame:
    """Reported long-book shares per quarter, snapshotted at each quarter's LAST
    (quarter-end) month (M6 §3.3).

    weights: month x asset signed portfolio weights.
    quarter_ends: the months to snapshot (the last business month of each quarter).
    eligible: per-asset boolean 13(f)-eligibility, indexed like weights.columns.

    Returns a quarter_end x asset frame of shares that sum to 1 over the visible names in
    each quarter (a quarter with no visible long renormalizes to all zeros).
    """
    eligible_aligned = _aligned_bool(eligible, weights.columns, default=False)
    options = _aligned_bool(option_mask, weights.columns, default=False)
    usable = (eligible_aligned & ~options).to_numpy()
    # Accept quarter-spanning periods (freq "3M") as well as explicit quarter-end months:
    # snapshot at each quarter's LAST month -- 13F reports positions as of the last
    # business day of the quarter (M6 §3.3), never the quarter's first month. asfreq
    # keeps the emitter pure and index-freq agnostic.
    snapshot_months = quarter_ends
    if isinstance(quarter_ends, pd.PeriodIndex) and quarter_ends.freq != weights.index.freq:
        snapshot_months = quarter_ends.asfreq(weights.index.freqstr, how="end")
    snapshots = weights.loc[snapshot_months]
    longs = snapshots.clip(lower=0.0)
    # Column-wise mask: zero every ineligible name. eligible_aligned is ordered like
    # weights.columns, so the multiply broadcasts across rows and crops whole columns
    # (DataFrame.where aligns a Series on the row index, not columns, so it cannot be used).
    visible = longs * usable
    totals = visible.sum(axis=1)
    shares = visible.div(totals.where(totals != 0.0), axis=0).fillna(0.0)
    shares.index.name = "quarter_end"
    shares.columns.name = "asset"
    return shares
