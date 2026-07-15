from __future__ import annotations

from typing import Mapping, Sequence

from .model import FunnelSummary, Refusal
from .validation import wilson_interval

X3_FUNNEL_RATE_MIN_DENOM = 20
_STAGES = (
    "discovered",
    "contacted",
    "rfi_received",
    "screened",
    "diligence",
    "ic_ready",
    "approved",
    "funded",
)


def build_funnel_summary(
    *,
    cohort_label: str,
    entry_stage: str,
    outcome_stage: str,
    links: Sequence[Mapping[str, object]],
    typed_mandate_projection_available: bool,
) -> FunnelSummary:
    """Summarize substrate-evaluated links without constructing cohort membership."""

    if any(not row.get("evaluation_receipt_id") for row in links):
        return FunnelSummary(
            cohort_label,
            entry_stage,
            outcome_stage,
            0,
            0,
            None,
            (),
            Refusal(
                "/funnel/stage_counts",
                "missing-cohort-evaluation-receipt",
                "Exact counts require a receipt for every shared cohort evaluation.",
            ),
        )
    included = [row for row in links if row["inclusion_disposition"] == "included"]
    entry_count = len({str(row["funnel_opportunity_id"]) for row in included})
    outcome_index = _STAGES.index(outcome_stage)
    outcome_count = len(
        {
            str(row["funnel_opportunity_id"])
            for row in included
            if row.get("stage_reached") in _STAGES
            and _STAGES.index(str(row["stage_reached"])) >= outcome_index
        }
    )
    receipts = tuple(sorted({str(row["evaluation_receipt_id"]) for row in links}))
    if not typed_mandate_projection_available:
        refusal = Refusal(
            "/funnel/conversion",
            "typed-mandate-brief-cohort-projection-required",
            "Exact stage counts are labelled; conversion and mandate-brief inference refuse.",
        )
        interval = None
    elif entry_count < X3_FUNNEL_RATE_MIN_DENOM:
        refusal = Refusal(
            "/funnel/conversion",
            "count-only-insufficient-cohort",
            f"Conversion interval requires at least {X3_FUNNEL_RATE_MIN_DENOM} opportunities.",
        )
        interval = None
    else:
        refusal = Refusal("", "none", "")
        interval = wilson_interval(outcome_count, entry_count)
    return FunnelSummary(
        cohort_label,
        entry_stage,
        outcome_stage,
        entry_count,
        outcome_count,
        interval,
        receipts,
        refusal,
    )
