"""S7 predecessor-portability evidence tests."""

from __future__ import annotations

import json
from dataclasses import fields, replace
from datetime import UTC, datetime
from inspect import signature
from typing import Any

import pytest

from quant_allocator.evidence.fixtures.s7 import (
    S7_CUTOFFS,
    build_s7_fixture,
    s7_source_requests,
    verify_s7_manifest,
)
from quant_allocator.evidence.lineage import make_receipt, store_receipt
from quant_allocator.evidence.model import (
    ReceiptReference,
    SnapshotBundleRequest,
    canonical_bytes,
    sha256,
)
from quant_allocator.evidence.projections import project_entity_relationships
from quant_allocator.evidence.schema import connect, initialize
from quant_allocator.evidence.snapshot import as_known_bundle

from quant_allocator.flagships.track_record_provenance.portability import (
    PORTABILITY_CAVEAT,
    PortabilityEvidenceFinding,
    PortabilityEvidenceResult,
    PortabilitySegmentRefusal,
    PortabilityState,
    _RelationshipEvidence,
    _classify_relationships,
    _relationship_evidence,
    assess_s7_portability_evidence,
    portability_evidence_result_bytes,
    verify_s7_portability_evidence_receipt,
)


def _time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _keys(value: object) -> set[str]:
    if isinstance(value, dict):
        return set(value) | {key for child in value.values() for key in _keys(child)}
    if isinstance(value, list):
        return {key for child in value for key in _keys(child)}
    return set()


def _relation(
    key: str,
    relation_type: str,
    source: str,
    target: str,
    *,
    start: str,
    end: str | None = None,
    scope: str,
) -> _RelationshipEvidence:
    is_point = relation_type in {"predecessor_claim", "contradicts_transfer"}
    return _RelationshipEvidence(
        f"relationship:{key}",
        f"item:{key}",
        f"span:{key}",
        f"observation:{key}",
        f"version:{key}",
        relation_type,
        source,
        target,
        "point" if is_point else "interval",
        _time(start) if is_point else None,
        None if is_point else _time(start),
        None if is_point or end is None else _time(end),
        scope,
    )


CLAIM = _relation(
    "claim",
    "predecessor_claim",
    "manager:prior",
    "manager:current",
    start="2024-01-01T00:00:00Z",
    scope="identity-claim",
)
PRIOR_LEAD = _relation(
    "prior-lead",
    "employed_by",
    "person:lead",
    "manager:prior",
    start="2020-01-01T00:00:00Z",
    end="2024-01-01T00:00:00Z",
    scope="employment",
)
CURRENT_LEAD = _relation(
    "current-lead",
    "employed_by",
    "person:lead",
    "manager:current",
    start="2024-01-01T00:00:00Z",
    scope="employment",
)
OVERLAPPING_CURRENT_LEAD = _relation(
    "overlapping-current-lead",
    "employed_by",
    "person:lead",
    "manager:current",
    start="2023-06-01T00:00:00Z",
    scope="employment",
)
PRIOR_SUPPORT = _relation(
    "prior-support",
    "employed_by",
    "person:support",
    "manager:prior",
    start="2020-01-01T00:00:00Z",
    scope="employment",
)
SCOPE_FOUR = _relation(
    "scope-four",
    "transfer_scope",
    "person:support",
    "strategy:four",
    start="2023-01-01T00:00:00Z",
    scope="strategy:four",
)
CONTRADICTION_FIVE = _relation(
    "contradiction-five",
    "contradicts_transfer",
    "person:support",
    "strategy:five",
    start="2024-06-01T00:00:00Z",
    scope="strategy:five",
)


@pytest.fixture(scope="module")
def real_portability() -> tuple[Any, Any, PortabilityEvidenceResult, PortabilityEvidenceResult]:
    conn = connect()
    initialize(conn)
    manifest = build_s7_fixture(conn)
    assert verify_s7_manifest(conn, manifest)
    early = assess_s7_portability_evidence(conn, manifest, cutoff_name="early")
    latest = assess_s7_portability_evidence(conn, manifest, cutoff_name="latest")
    assert verify_s7_manifest(conn, manifest)
    return conn, manifest, early, latest


def test_portability_contract_has_five_states_exact_copy_and_no_score_fields() -> None:
    assert tuple(state.value for state in PortabilityState) == (
        "documented-claim",
        "partial-support",
        "contradicted",
        "unresolved",
        "refused",
    )
    assert (
        PORTABILITY_CAVEAT
        == "Documented lineage is not evidence that historical skill transferred."
    )
    field_names = {field.name for field in fields(PortabilityEvidenceFinding)}
    assert not field_names & {
        "alpha",
        "skill",
        "skill_score",
        "portable_score",
        "probability",
        "rank",
        "recommendation",
    }


def test_portability_core_emits_five_ruled_states_without_claim_broadening() -> None:
    early = _time("2024-03-31T23:59:59Z")
    latest = _time("2024-09-30T23:59:59Z")

    documented = _classify_relationships((CLAIM,), cutoff=early)
    assert [finding.state for finding in documented] == [
        PortabilityState.DOCUMENTED_CLAIM
    ]
    assert documented[0].claimed_scope == "identity-claim"
    assert "historical-skill-transfer-evidence" in documented[0].missing_evidence

    partial = _classify_relationships(
        (CLAIM, PRIOR_LEAD, CURRENT_LEAD), cutoff=early
    )
    partial_finding = next(
        finding
        for finding in partial
        if finding.state is PortabilityState.PARTIAL_SUPPORT
    )
    assert partial_finding.person_entity_id == "person:lead"
    assert partial_finding.claimed_scope == "employment-chronology"
    assert "employment-intervals-abut-no-overlap" in partial_finding.reason_codes
    assert "employment-overlap-evidence" in partial_finding.missing_evidence

    unresolved = _classify_relationships(
        (CLAIM, PRIOR_SUPPORT, SCOPE_FOUR), cutoff=early
    )
    unresolved_finding = next(
        finding
        for finding in unresolved
        if finding.state is PortabilityState.UNRESOLVED
    )
    assert unresolved_finding.person_entity_id == "person:support"
    assert unresolved_finding.claimed_scope == "strategy:four"
    assert unresolved_finding.missing_evidence == (
        "current-team-employment-evidence",
    )

    refused = _classify_relationships((PRIOR_LEAD,), cutoff=early)
    assert len(refused) == 1
    assert refused[0].state is PortabilityState.REFUSED
    assert refused[0].reason_codes == ("predecessor-identity-edge-missing",)

    before_contradiction = _classify_relationships(
        (CLAIM, PRIOR_SUPPORT, SCOPE_FOUR, CONTRADICTION_FIVE), cutoff=early
    )
    assert not [
        finding
        for finding in before_contradiction
        if finding.state is PortabilityState.CONTRADICTED
    ]
    after_contradiction = _classify_relationships(
        (CLAIM, PRIOR_SUPPORT, SCOPE_FOUR, CONTRADICTION_FIVE), cutoff=latest
    )
    contradiction = next(
        finding
        for finding in after_contradiction
        if finding.state is PortabilityState.CONTRADICTED
    )
    assert contradiction.person_entity_id == "person:support"
    assert contradiction.claimed_scope == "strategy:five"
    assert SCOPE_FOUR.relationship_id not in contradiction.relationship_ids


def test_portability_core_binds_scope_and_contradiction_to_same_person_and_scope() -> None:
    latest = datetime(2024, 9, 30, 23, 59, 59, tzinfo=UTC)
    other_person_scope = replace(
        SCOPE_FOUR,
        relationship_id="relationship:other-person-scope",
        evidence_item_id="item:other-person-scope",
        evidence_span_id="span:other-person-scope",
        observation_id="observation:other-person-scope",
        version_id="version:other-person-scope",
        source_entity_id="person:other",
        target_entity_id="strategy:five",
        scope="strategy:five",
    )
    findings = _classify_relationships(
        (
            CLAIM,
            PRIOR_SUPPORT,
            SCOPE_FOUR,
            other_person_scope,
            CONTRADICTION_FIVE,
        ),
        cutoff=latest,
    )
    contradiction = next(
        finding
        for finding in findings
        if finding.state is PortabilityState.CONTRADICTED
    )
    assert other_person_scope.relationship_id not in contradiction.relationship_ids
    assert SCOPE_FOUR.relationship_id not in contradiction.relationship_ids


def test_s7_l18_overlap_is_only_partial_support_without_transfer_scope() -> None:
    findings = _classify_relationships(
        (CLAIM, PRIOR_LEAD, OVERLAPPING_CURRENT_LEAD),
        cutoff=_time("2024-03-31T23:59:59Z"),
    )
    partial = next(
        finding
        for finding in findings
        if finding.state is PortabilityState.PARTIAL_SUPPORT
    )
    assert partial.person_entity_id == "person:lead"
    assert partial.claimed_scope == "employment-chronology"
    assert partial.reason_codes == ("person-chronology-without-transfer-scope",)
    assert "transfer-scope-evidence" in partial.missing_evidence
    assert partial.caveat == PORTABILITY_CAVEAT


def test_portability_public_api_accepts_no_caller_authored_evidence_or_time() -> None:
    assert tuple(signature(assess_s7_portability_evidence).parameters) == (
        "conn",
        "manifest",
        "cutoff_name",
    )
    assert tuple(signature(verify_s7_portability_evidence_receipt).parameters) == (
        "conn",
        "receipt_id",
        "manifest",
        "cutoff_name",
    )
    with pytest.raises(TypeError):
        assess_s7_portability_evidence(  # type: ignore[call-arg]
            object(),
            object(),
            cutoff_name="early",
            scenario="credit",
        )
    with pytest.raises(TypeError):
        assess_s7_portability_evidence(  # type: ignore[call-arg]
            object(),
            object(),
            cutoff_name="early",
            predecessor_segment=object(),
        )
    assert callable(portability_evidence_result_bytes)


def test_real_fixture_portability_is_evidence_only_and_point_in_time(
    real_portability: tuple[Any, Any, PortabilityEvidenceResult, PortabilityEvidenceResult],
) -> None:
    _, manifest, early, latest = real_portability
    early_contract = next(
        contract
        for contract in manifest.bundle_contracts
        if contract.scenario == "hedge-fund" and contract.cutoff_name == "early"
    )
    latest_contract = next(
        contract
        for contract in manifest.bundle_contracts
        if contract.scenario == "hedge-fund" and contract.cutoff_name == "latest"
    )
    assert early.bundle_digest == early_contract.analytic_bundle_digest
    assert early.join_receipt_id == early_contract.analytic_join_receipt_id
    assert latest.bundle_digest == latest_contract.analytic_bundle_digest
    assert latest.join_receipt_id == latest_contract.analytic_join_receipt_id
    assert early.terms_snapshot_digest == dict(
        early_contract.analytic_slice_digests
    )["dataset:s7-lineage-terms"]
    assert latest.terms_snapshot_digest == dict(
        latest_contract.analytic_slice_digests
    )["dataset:s7-lineage-terms"]

    assert {finding.state for finding in early.findings} == {
        PortabilityState.DOCUMENTED_CLAIM,
        PortabilityState.PARTIAL_SUPPORT,
        PortabilityState.UNRESOLVED,
    }
    assert {finding.state for finding in latest.findings} == {
        PortabilityState.DOCUMENTED_CLAIM,
        PortabilityState.PARTIAL_SUPPORT,
        PortabilityState.CONTRADICTED,
        PortabilityState.UNRESOLVED,
    }
    claim = next(
        finding
        for finding in latest.findings
        if finding.state is PortabilityState.DOCUMENTED_CLAIM
    )
    assert claim.predecessor_entity_id == "manager:x3-01"
    assert claim.current_entity_id == "manager:x3-00"
    assert claim.claimed_scope == "identity-claim"
    assert claim.person_entity_id is None
    assert len(claim.relationship_ids) == 1
    assert claim.missing_evidence == (
        "historical-skill-transfer-evidence",
        "process-continuity-evidence",
        "team-transfer-evidence",
    )

    partial = next(
        finding
        for finding in latest.findings
        if finding.state is PortabilityState.PARTIAL_SUPPORT
    )
    assert partial.person_entity_id == "person:s7-lead"
    assert partial.claimed_scope == "employment-chronology"
    assert "employment-intervals-abut-no-overlap" in partial.reason_codes
    assert "transfer-scope-evidence" in partial.missing_evidence

    unresolved = next(
        finding
        for finding in latest.findings
        if finding.state is PortabilityState.UNRESOLVED
    )
    assert unresolved.person_entity_id == "person:s7-support"
    assert unresolved.claimed_scope == "strategy:x3-04"
    assert unresolved.missing_evidence == (
        "current-team-employment-evidence",
    )

    assert not [
        finding
        for finding in early.findings
        if finding.state is PortabilityState.CONTRADICTED
    ]
    contradiction = next(
        finding
        for finding in latest.findings
        if finding.state is PortabilityState.CONTRADICTED
    )
    assert contradiction.person_entity_id == "person:s7-support"
    assert contradiction.claimed_scope == "strategy:x3-05"
    assert contradiction.boundary_at == datetime(2024, 6, 1, tzinfo=UTC)
    assert not {
        "entity-relation:sha256:705df9ddd8743d031327b8094604c0348aa56ee0e9d6a5f50f69bd4893154b04"
    } & set(contradiction.relationship_ids)


def test_real_fixture_segment_link_refuses_without_segment_or_credit_identity(
    real_portability: tuple[Any, Any, PortabilityEvidenceResult, PortabilityEvidenceResult],
) -> None:
    _, _, early, latest = real_portability
    for result in (early, latest):
        refusal = result.segment_link_refusal
        assert isinstance(refusal, PortabilitySegmentRefusal)
        assert (
            refusal.reason_code
            == "predecessor-segment-not-authenticated-in-bundle"
        )
        assert refusal.caveat == PORTABILITY_CAVEAT
        assert refusal.current_attestation == "D"
        assert refusal.live_attestation_ceiling == "C"
        assert not {field.name for field in fields(refusal)} & {
            "segment_id",
            "predecessor_segment_id",
            "observation_ids",
            "predecessor_observation_ids",
        }
        payload = json.loads(portability_evidence_result_bytes(result))
        assert "dataset:s7-credit-lineage" not in str(payload)
        assert "lineage-segment:" not in str(payload)
        assert "dataset-observation:" not in str(payload)
        assert not _keys(payload) & {
            "alpha",
            "skill",
            "skill_score",
            "portable_score",
            "probability",
            "rank",
            "recommendation",
        }


def test_real_fixture_receipts_reference_only_exact_terms_evidence_tuples(
    real_portability: tuple[Any, Any, PortabilityEvidenceResult, PortabilityEvidenceResult],
) -> None:
    conn, _, _, latest = real_portability
    for receipt_id in latest.receipt_ids:
        header = conn.execute(
            "SELECT * FROM reconstruction_receipt WHERE receipt_id=?", (receipt_id,)
        ).fetchone()
        assert header is not None
        assert header["output_schema_id"] == "s7-portability-finding/v1"
        assert header["current_attestation"] == "D"
        assert header["live_attestation_ceiling"] == "C"
        assert header["algorithm_id"] == "s7-portability/v1"
        references = conn.execute(
            "SELECT * FROM receipt_reference WHERE receipt_id=? ORDER BY ordinal",
            (receipt_id,),
        ).fetchall()
        assert references
        for reference in references:
            reference_type = reference["reference_type"]
            if reference_type == "snapshot":
                assert reference["snapshot_digest"] == latest.terms_snapshot_digest
            elif reference_type == "evidence-right":
                dataset_id = conn.execute(
                    "SELECT dataset_id FROM evidence_right WHERE evidence_right_id=?",
                    (reference["evidence_right_id"],),
                ).fetchone()[0]
                assert dataset_id == "dataset:s7-lineage-terms"
            elif reference_type == "dataset-version":
                dataset_id = conn.execute(
                    "SELECT dataset_id FROM dataset_version WHERE dataset_version_id=?",
                    (reference["dataset_version_id"],),
                ).fetchone()[0]
                assert dataset_id == "dataset:s7-lineage-terms"
            elif reference_type == "dataset-observation":
                dataset_id = conn.execute(
                    "SELECT v.dataset_id FROM dataset_observation o "
                    "JOIN dataset_version v USING(dataset_version_id) "
                    "WHERE o.dataset_observation_id=?",
                    (reference["dataset_observation_id"],),
                ).fetchone()[0]
                assert dataset_id == "dataset:s7-lineage-terms"
            elif reference_type == "evidence-item":
                dataset_id = conn.execute(
                    "SELECT s.dataset_id FROM evidence_item i "
                    "JOIN source_record s USING(source_record_id) "
                    "WHERE i.evidence_item_id=?",
                    (reference["evidence_item_id"],),
                ).fetchone()[0]
                assert dataset_id == "dataset:s7-lineage-terms"
                assert reference["source_field"] == "/assertion"
            elif reference_type == "evidence-span":
                dataset_id, pointer = conn.execute(
                    "SELECT sr.dataset_id,sp.json_pointer FROM evidence_span sp "
                    "JOIN evidence_item i USING(evidence_item_id) "
                    "JOIN source_record sr USING(source_record_id) "
                    "WHERE sp.evidence_span_id=?",
                    (reference["evidence_span_id"],),
                ).fetchone()
                assert dataset_id == "dataset:s7-lineage-terms"
                assert pointer == reference["source_field"] == "/assertion"
            elif reference_type == "entity-relationship":
                dataset_id = conn.execute(
                    "SELECT v.dataset_id FROM entity_relationship r "
                    "JOIN dataset_version v USING(dataset_version_id) "
                    "WHERE r.entity_relationship_id=?",
                    (reference["entity_relationship_id"],),
                ).fetchone()[0]
                assert dataset_id == "dataset:s7-lineage-terms"
            else:
                pytest.fail(f"unexpected portability reference type: {reference_type}")


def test_relationship_closure_rejects_payload_projection_time_mismatch(
    real_portability: tuple[Any, Any, PortabilityEvidenceResult, PortabilityEvidenceResult],
) -> None:
    conn, manifest, _, _ = real_portability
    bundle = as_known_bundle(
        conn,
        SnapshotBundleRequest(
            S7_CUTOFFS["latest"],
            s7_source_requests(
                manifest,
                scenario="hedge-fund",
                cutoff_name="latest",
                revision_mode="latest-known",
            ),
            ("field_dictionary_version",),
            "s7-track-lineage-v1",
        ),
    )
    terms_slice = next(
        slice_
        for slice_ in bundle.slices
        if slice_.request.dataset_id == "dataset:s7-lineage-terms"
    )
    lead_prior = next(
        row
        for row in project_entity_relationships(conn, terms_slice)
        if row["source_entity_id"] == "person:s7-lead"
        and row["target_entity_id"] == "manager:x3-01"
    )
    assert _relationship_evidence(conn, terms_slice, lead_prior).effective_to == datetime(
        2024, 1, 1, tzinfo=UTC
    )
    tampered = dict(lead_prior)
    tampered["effective_to"] = "2024-01-02T00:00:00.000000Z"
    with pytest.raises(
        ValueError, match="s7-portability-relationship-closure-invalid"
    ):
        _relationship_evidence(conn, terms_slice, tampered)


def test_portability_local_verifier_accepts_exact_receipts_and_rejects_tampered_closure(
    real_portability: tuple[Any, Any, PortabilityEvidenceResult, PortabilityEvidenceResult],
) -> None:
    conn, manifest, _, latest = real_portability
    exact_receipt = next(
        finding.receipt_id
        for finding in latest.findings
        if finding.state is PortabilityState.DOCUMENTED_CLAIM
    )
    verify_s7_portability_evidence_receipt(
        conn,
        receipt_id=exact_receipt,
        manifest=manifest,
        cutoff_name="latest",
    )

    wrong_span = conn.execute(
        "SELECT sp.evidence_span_id FROM evidence_span sp "
        "JOIN evidence_item i USING(evidence_item_id) "
        "JOIN source_record s USING(source_record_id) "
        "WHERE s.dataset_id='dataset:s7-lineage-terms' "
        "AND sp.json_pointer!='/assertion' ORDER BY sp.evidence_span_id LIMIT 1"
    ).fetchone()[0]
    credit_digest = next(
        contract.analytic_bundle_digest
        for contract in manifest.bundle_contracts
        if contract.scenario == "credit" and contract.cutoff_name == "latest"
    )
    tampered_parameters = {
        "credit_bundle_digest": credit_digest,
        "constructed_predecessor_segment_id": "lineage-segment:constructed",
        "constructed_segment_observation_ids": ("dataset-observation:constructed",),
    }
    fake = make_receipt(
        claim_id="predecessor_portability_evidence",
        output_locator="/portability/findings/tampered",
        input_digest=sha256(
            canonical_bytes({"s7-portability-input": tampered_parameters})
        ),
        output_schema_id="s7-portability-finding/v1",
        current_attestation="D",
        live_attestation_ceiling="C",
        algorithm_id="s7-portability/v1",
        algorithm_version="1",
        parameters=tampered_parameters,
        value={"state": "documented-claim"},
        references=(
            ReceiptReference(
                "/portability/findings/tampered",
                "evidence-span",
                wrong_span,
                "included",
                "",
                "schema:s7-relationship-evidence-v1",
                "/assertion",
                "input",
            ),
        ),
    )
    store_receipt(conn, fake)
    with pytest.raises(
        ValueError, match="s7-portability-receipt-closure-invalid"
    ):
        verify_s7_portability_evidence_receipt(
            conn,
            receipt_id=fake.receipt_id,
            manifest=manifest,
            cutoff_name="latest",
        )


def test_portability_order_is_deterministic_for_findings_bytes_and_receipts() -> None:
    latest = _time("2024-09-30T23:59:59Z")
    forward_relationships = (
        CLAIM,
        PRIOR_LEAD,
        CURRENT_LEAD,
        PRIOR_SUPPORT,
        SCOPE_FOUR,
        CONTRADICTION_FIVE,
    )
    forward_findings = _classify_relationships(
        forward_relationships, cutoff=latest
    )
    reverse_findings = _classify_relationships(
        tuple(reversed(forward_relationships)), cutoff=latest
    )
    assert forward_findings == reverse_findings

    segment_refusal = PortabilitySegmentRefusal(
        "s7-portability-refusal:sha256:" + "3" * 64,
        "/portability/segment-link-refusal",
        "predecessor-segment-not-authenticated-in-bundle",
        PORTABILITY_CAVEAT,
        "D",
        "C",
        "receipt:sha256:" + "4" * 64,
    )
    result_kwargs = {
        "cutoff_name": "latest",
        "bundle_digest": "bundle:sha256:" + "5" * 64,
        "join_receipt_id": "receipt:sha256:" + "6" * 64,
        "terms_snapshot_digest": "snapshot:sha256:" + "7" * 64,
        "terms_slice_receipt_id": "receipt:sha256:" + "8" * 64,
        "segment_link_refusal": segment_refusal,
        "receipt_ids": tuple(sorted(finding.receipt_id for finding in forward_findings)),
    }
    assert portability_evidence_result_bytes(
        PortabilityEvidenceResult(findings=forward_findings, **result_kwargs)
    ) == portability_evidence_result_bytes(
        PortabilityEvidenceResult(
            findings=tuple(reversed(reverse_findings)),
            **{
                **result_kwargs,
                "receipt_ids": tuple(reversed(result_kwargs["receipt_ids"])),
            },
        )
    )

    references = (
        ReceiptReference(
            "/portability/test",
            "evidence-item",
            "evidence:sha256:" + "1" * 64,
            "included",
            "",
            "schema:generic-v1",
            "/",
            "input",
        ),
        ReceiptReference(
            "/portability/test",
            "snapshot",
            "snapshot:sha256:" + "2" * 64,
            "included",
            "",
            "schema:generic-v1",
            "/",
            "input",
        ),
    )
    parameters = {"ordered": True}
    kwargs = {
        "claim_id": "predecessor_portability_evidence",
        "output_locator": "/portability/test",
        "input_digest": sha256(canonical_bytes(parameters)),
        "output_schema_id": "s7-portability-finding/v1",
        "current_attestation": "D",
        "live_attestation_ceiling": "C",
        "algorithm_id": "s7-portability/v1",
        "algorithm_version": "1",
        "parameters": parameters,
        "value": {"state": "documented-claim"},
    }
    assert make_receipt(references=references, **kwargs) == make_receipt(
        references=tuple(reversed(references)), **kwargs
    )
