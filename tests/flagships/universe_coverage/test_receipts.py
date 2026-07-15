from dataclasses import asdict, replace

import pytest

from quant_allocator.evidence.fixtures.x3 import X3_CUTOFFS, build_x3_fixture
from quant_allocator.evidence.model import DatasetSliceRequest
from quant_allocator.evidence.projections import (
    evaluate_funnel_cohort,
    project_funnel_cohorts,
    project_funnel_events,
)
from quant_allocator.evidence.schema import connect, initialize
from quant_allocator.evidence.snapshot import as_known_slice
from quant_allocator.flagships.universe_coverage.receipts import (
    X3ClaimReceiptContract,
    build_verification_envelope,
    persist_x3_claim_receipt,
    verify_x3_claim_receipt,
)
from quant_allocator.flagships.universe_coverage.funnel import build_funnel_summary


def _case():
    conn = connect()
    initialize(conn)
    manifest = build_x3_fixture(conn)
    cutoff = X3_CUTOFFS["latest"]
    slice_ = as_known_slice(
        conn,
        decision_at=cutoff,
        request=DatasetSliceRequest(
            "dataset:x3-target-grid",
            manifest.access_contexts["dataset:x3-target-grid"],
            manifest.right_ids["dataset:x3-target-grid"],
            manifest.licence_purposes["dataset:x3-target-grid"],
            valid_at=cutoff,
        ),
    )
    bundle = build_verification_envelope(
        conn,
        state_key="latest|public-plus-prehire|cross-asset",
        decision_at=cutoff,
        slices=(slice_,),
    )
    contract = X3ClaimReceiptContract(
        "target_cell_observation",
        "/target_grid/observed_cells",
        "latest|public-plus-prehire|cross-asset",
        ("public", "pre-hire-public", "shortlisted-nda", "internal-governance"),
        "B",
        None,
        "typed-membership-cell-projection-required",
    )
    receipt_id = persist_x3_claim_receipt(conn, bundle=bundle, contract=contract)
    return conn, bundle, contract, receipt_id


def test_claim_receipt_verifies_through_shared_verifier() -> None:
    conn, bundle, contract, receipt_id = _case()
    verify_x3_claim_receipt(conn, receipt_id=receipt_id, bundle=bundle, contract=contract)
    references = conn.execute(
        "SELECT snapshot_digest, disposition, role, reason_code "
        "FROM receipt_reference WHERE receipt_id=? ORDER BY disposition, role",
        (receipt_id,),
    ).fetchall()
    assert {row["snapshot_digest"] for row in references} == {row.digest for row in bundle.slices}
    assert {(row["disposition"], row["role"]) for row in references} == {
        ("included", "input"),
        ("refused", "refusal"),
    }
    assert all(row["reason_code"] == contract.refusal_code for row in references if row["role"] == "refusal")


@pytest.mark.parametrize(
    "changed",
    (
        {"output_pointer": "/target_grid/wrong"},
        {"state_key": "early|public-only|cross-asset"},
        {"access_contexts": ("public",)},
        {"refusal_code": "wrong-prerequisite"},
    ),
)
def test_pointer_state_access_and_reference_substitutions_refuse(changed) -> None:
    conn, bundle, contract, receipt_id = _case()
    with pytest.raises(ValueError, match="x3-claim-(receipt-contract|access-context)-mismatch"):
        verify_x3_claim_receipt(
            conn,
            receipt_id=receipt_id,
            bundle=bundle,
            contract=replace(contract, **changed),
        )


def test_verification_envelope_substitution_refuses() -> None:
    conn, bundle, contract, receipt_id = _case()
    with pytest.raises(ValueError, match="x3-claim-receipt-contract-mismatch"):
        verify_x3_claim_receipt(
            conn,
            receipt_id=receipt_id,
            bundle=replace(bundle, bundle_digest="bundle:sha256:" + "0" * 64),
            contract=contract,
        )


@pytest.mark.parametrize(
    "request_change",
    (
        {"dataset_id": "dataset:x3-public-adviser"},
        {"evidence_right_id": "right:substituted-but-unverified"},
        {"access_context": "public"},
        {"licence_purpose": "substituted-purpose"},
    ),
)
def test_slice_request_substitutions_refuse_even_when_digest_and_receipt_are_preserved(
    request_change,
) -> None:
    conn, bundle, contract, receipt_id = _case()
    original = bundle.slices[0]
    changed = replace(original, request=replace(original.request, **request_change))
    with pytest.raises(ValueError):
        verify_x3_claim_receipt(
            conn,
            receipt_id=receipt_id,
            bundle=replace(bundle, slices=(changed,)),
            contract=contract,
        )


def test_slice_row_substitution_refuses_when_digest_and_receipt_are_preserved() -> None:
    conn, bundle, contract, receipt_id = _case()
    original = bundle.slices[0]
    changed = replace(original, rows=original.rows[:-1])
    with pytest.raises(ValueError):
        verify_x3_claim_receipt(
            conn,
            receipt_id=receipt_id,
            bundle=replace(bundle, slices=(changed,)),
            contract=contract,
        )


def test_claim_context_must_authorize_every_referenced_slice() -> None:
    conn, bundle, contract, _receipt_id = _case()
    public_only = replace(contract, access_contexts=("public",))
    with pytest.raises(ValueError, match="x3-claim-access-context-mismatch"):
        persist_x3_claim_receipt(conn, bundle=bundle, contract=public_only)


def _full_funnel_case(*, cutoff_key="latest", claim_id="funnel_stage_counts"):
    conn = connect()
    initialize(conn)
    manifest = build_x3_fixture(conn)
    cutoff = X3_CUTOFFS[cutoff_key]
    dataset_id = "dataset:x3-funnel-event"
    slice_ = as_known_slice(
        conn,
        decision_at=cutoff,
        request=DatasetSliceRequest(
            dataset_id,
            manifest.access_contexts[dataset_id],
            manifest.right_ids[dataset_id],
            manifest.licence_purposes[dataset_id],
            valid_at=cutoff,
        ),
    )
    events = {row["funnel_event_id"]: row for row in project_funnel_events(conn, slice_)}
    summaries = []
    for cohort in project_funnel_cohorts(conn, slice_):
        if cohort["completeness_status"] != "complete":
            continue
        evaluated = evaluate_funnel_cohort(
            conn, slice_, funnel_cohort_id=cohort["funnel_cohort_id"]
        )
        links = [
            {**row, "stage_reached": events[row["funnel_event_id"]]["funnel_stage"]}
            for row in evaluated["links"]
        ]
        summaries.append(
            asdict(
                build_funnel_summary(
                    cohort_label=cohort["cohort_label"],
                    entry_stage=cohort["entry_stage"],
                    outcome_stage=cohort["outcome_stage"],
                    links=links,
                    typed_mandate_projection_available=False,
                )
            )
        )
    summaries.sort(key=lambda row: row["cohort_label"])
    evaluation_ids = tuple(
        sorted({item for row in summaries for item in row["evaluation_receipt_ids"]})
    )
    bundle = build_verification_envelope(
        conn,
        state_key=f"{cutoff_key}|full-synthetic-funnel|cross-asset|claim:{claim_id}",
        decision_at=cutoff,
        slices=(slice_,),
    )
    value = (
        summaries
        if claim_id == "funnel_stage_counts"
        else {"conversion_interval": None, "stage_counts": summaries}
    )
    contract = X3ClaimReceiptContract(
        claim_id,
        "/funnel/stage_counts" if claim_id == "funnel_stage_counts" else "/funnel/conversion",
        f"{cutoff_key}|full-synthetic-funnel|cross-asset",
        ("internal-governance",),
        "B",
        value,
        "" if claim_id == "funnel_stage_counts" else "typed-mandate-brief-cohort-projection-required",
        evaluation_ids,
    )
    return conn, bundle, contract


def test_full_funnel_claim_binds_and_verifies_exact_168_evaluation_receipts() -> None:
    conn, bundle, contract = _full_funnel_case()
    assert len(contract.evaluation_receipt_ids) == 168
    receipt_id = persist_x3_claim_receipt(conn, bundle=bundle, contract=contract)
    verify_x3_claim_receipt(conn, receipt_id=receipt_id, bundle=bundle, contract=contract)
    for changed in (
        (),
        contract.evaluation_receipt_ids[:-1],
        contract.evaluation_receipt_ids + ("receipt:sha256:" + "0" * 64,),
    ):
        with pytest.raises(ValueError, match="x3-evaluation-receipt-set"):
            persist_x3_claim_receipt(
                conn,
                bundle=bundle,
                contract=replace(contract, evaluation_receipt_ids=changed),
            )


@pytest.mark.parametrize("claim_id", ("funnel_stage_counts", "funnel_conversion"))
def test_latest_full_funnel_refuses_empty_evaluation_contract(claim_id) -> None:
    conn, bundle, contract = _full_funnel_case(claim_id=claim_id)
    empty_value = [] if claim_id == "funnel_stage_counts" else {
        "conversion_interval": None,
        "stage_counts": [],
    }
    with pytest.raises(ValueError, match="x3-evaluation-receipt-applicability-mismatch"):
        persist_x3_claim_receipt(
            conn,
            bundle=bundle,
            contract=replace(contract, value=empty_value, evaluation_receipt_ids=()),
        )


@pytest.mark.parametrize("claim_id", ("funnel_stage_counts", "funnel_conversion"))
def test_latest_full_funnel_refuses_missing_stage_row_receipts(claim_id) -> None:
    conn, bundle, contract = _full_funnel_case(claim_id=claim_id)
    rows = contract.value if claim_id == "funnel_stage_counts" else contract.value["stage_counts"]
    partial_rows = rows[:-1]
    partial_value = partial_rows if claim_id == "funnel_stage_counts" else {
        "conversion_interval": None,
        "stage_counts": partial_rows,
    }
    partial_ids = tuple(
        sorted({receipt_id for row in partial_rows for receipt_id in row["evaluation_receipt_ids"]})
    )
    assert 0 < len(partial_ids) < 168
    with pytest.raises(ValueError, match="x3-evaluation-receipt-applicability-mismatch"):
        persist_x3_claim_receipt(
            conn,
            bundle=bundle,
            contract=replace(
                contract,
                value=partial_value,
                evaluation_receipt_ids=partial_ids,
            ),
        )


@pytest.mark.parametrize("cutoff_key", ("early", "middle"))
@pytest.mark.parametrize("claim_id", ("funnel_stage_counts", "funnel_conversion"))
def test_inapplicable_full_funnel_accepts_only_empty_evaluation_contract(
    cutoff_key, claim_id
) -> None:
    conn, bundle, contract = _full_funnel_case(cutoff_key=cutoff_key, claim_id=claim_id)
    assert not contract.evaluation_receipt_ids
    receipt_id = persist_x3_claim_receipt(conn, bundle=bundle, contract=contract)
    verify_x3_claim_receipt(
        conn,
        receipt_id=receipt_id,
        bundle=bundle,
        contract=contract,
    )
    with pytest.raises(ValueError, match="x3-evaluation-receipt-applicability-mismatch"):
        persist_x3_claim_receipt(
            conn,
            bundle=bundle,
            contract=replace(
                contract,
                evaluation_receipt_ids=("receipt:sha256:" + "0" * 64,),
            ),
        )
