from quant_allocator.flagships.universe_coverage.funnel import build_funnel_summary


def test_receipted_stage_counts_preserve_conversion_refusal() -> None:
    summary = build_funnel_summary(
        cohort_label="x3-discovered-to-screen",
        entry_stage="discovered",
        outcome_stage="screened",
        links=tuple(
            {"funnel_opportunity_id": f"o-{i}", "inclusion_disposition": "included", "censor_status": "observed", "evaluation_receipt_id": f"r-{i}", "stage_reached": "screened" if i < 20 else "discovered"}
            for i in range(30)
        ),
        typed_mandate_projection_available=False,
    )
    assert summary.entry_count == 30 and summary.outcome_count == 20
    assert summary.conversion_interval is None
    assert summary.refusal.pointer == "/funnel/conversion"
    assert summary.refusal.code == "typed-mandate-brief-cohort-projection-required"


def test_missing_receipt_refuses_exact_counts() -> None:
    summary = build_funnel_summary(
        cohort_label="c", entry_stage="discovered", outcome_stage="screened",
        links=({"funnel_opportunity_id": "o", "inclusion_disposition": "included", "censor_status": "observed", "evaluation_receipt_id": "", "stage_reached": "screened"},),
        typed_mandate_projection_available=False,
    )
    assert summary.entry_count == 0
    assert summary.refusal.code == "missing-cohort-evaluation-receipt"


def test_outcome_count_includes_later_valid_stages() -> None:
    stages = ("screened", "diligence", "approved", "funded", "discovered")
    summary = build_funnel_summary(
        cohort_label="c",
        entry_stage="discovered",
        outcome_stage="screened",
        links=tuple(
            {"funnel_opportunity_id": f"o-{i}", "inclusion_disposition": "included", "censor_status": "observed", "evaluation_receipt_id": f"r-{i}", "stage_reached": stage}
            for i, stage in enumerate(stages)
        ),
        typed_mandate_projection_available=False,
    )
    assert summary.entry_count == 5
    assert summary.outcome_count == 4
