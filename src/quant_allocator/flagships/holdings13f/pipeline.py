"""M6 §3.3 13F emitter: a pure, deterministic view over a signed-weight panel.

emit_13f_long_book down-samples to quarter-ends, crops to longs and 13(f)-eligible names,
and renormalizes the survivors to reported market-value shares. It draws no random numbers
and consumes no RNG stream tag (the overlays.py discipline, M6 §6.6), so a manager never
viewed through it is byte-identical to one who is.
"""

from __future__ import annotations

import pandas as pd


def emit_13f_long_book(
    weights: pd.DataFrame, quarter_ends: pd.PeriodIndex, eligible: pd.Series
) -> pd.DataFrame:
    """Reported long-book shares per quarter (M6 §3.3).

    weights: month x asset signed portfolio weights.
    quarter_ends: the months to snapshot (the last business month of each quarter).
    eligible: per-asset boolean 13(f)-eligibility, indexed like weights.columns.

    Returns a quarter_end x asset frame of shares that sum to 1 over the visible names in
    each quarter (a quarter with no visible long renormalizes to all zeros).
    """
    eligible_aligned = eligible.reindex(weights.columns).fillna(False).to_numpy()
    # Accept quarter-spanning periods (freq "3M") as well as explicit quarter-end months:
    # snapshot at each quarter's first month, the quarter-end label the caller names
    # (M6 §3.3). asfreq keeps the emitter pure and index-freq agnostic.
    snapshot_months = quarter_ends
    if isinstance(quarter_ends, pd.PeriodIndex) and quarter_ends.freq != weights.index.freq:
        snapshot_months = quarter_ends.asfreq(weights.index.freqstr, how="start")
    snapshots = weights.loc[snapshot_months]
    longs = snapshots.clip(lower=0.0)
    # Column-wise mask: zero every ineligible name. eligible_aligned is ordered like
    # weights.columns, so the multiply broadcasts across rows and crops whole columns
    # (DataFrame.where aligns a Series on the row index, not columns, so it cannot be used).
    visible = longs * eligible_aligned
    totals = visible.sum(axis=1)
    shares = visible.div(totals.where(totals != 0.0), axis=0).fillna(0.0)
    shares.index.name = "quarter_end"
    shares.columns.name = "asset"
    return shares
