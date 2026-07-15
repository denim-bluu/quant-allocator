"""S7 policy-refusal receipt closure tests."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import replace
from typing import Any

import pytest

from quant_allocator.evidence.checks import EvidenceRefusal
from quant_allocator.evidence.fixtures.terms import build_s7_terms_sources
from quant_allocator.evidence.fixtures.x3 import build_x3_fixture
from quant_allocator.evidence.fixtures.s7 import S7MethodPolicyEvidence
from quant_allocator.evidence.lineage import make_receipt, store_receipt
from quant_allocator.evidence.model import ReceiptReference, SnapshotBundle, canonical_bytes, sha256
from quant_allocator.evidence.schema import connect, initialize
from quant_allocator.flagships.track_record_provenance.inspector import (
    verify_s7_policy_refusal_receipt,
)


def _policy_parameters(
    policy: S7MethodPolicyEvidence, policy_bundle: SnapshotBundle
) -> dict[str, object]:
    return {
        "policy_id": policy.policy_id,
        "policy_item_id": policy.item_id,
        "policy_span_id": policy.span_id,
        "policy_observation_id": policy.observation_id,
        "policy_version_id": policy.version_id,
        "policy_right_id": policy.right_id,
        "policy_snapshot_digest": policy.snapshot_digest,
        "policy_bundle_digest": policy_bundle.bundle_digest,
        "policy_join_receipt_id": policy_bundle.join_receipt_id,
        "policy_payload_schema_id": policy.payload_schema_id,
        "policy_payload_schema_sha256": policy.payload_schema_sha256,
        "policy_payload_sha256": policy.payload_sha256,
    }


def _policy_input_digest(parameters: Mapping[str, object]) -> str:
    return sha256(canonical_bytes({"policy-refusal-input": dict(parameters)}))


def _policy_references(
    policy: S7MethodPolicyEvidence,
    *,
    extra: Iterable[ReceiptReference] = (),
) -> tuple[ReceiptReference, ...]:
    output = "/refusals/performance-estimator"
    schema = policy.payload_schema_id
    return (
        ReceiptReference(output, "evidence-item", policy.item_id, "included", "", schema, "/", "input"),
        ReceiptReference(
            output, "evidence-span", policy.span_id, "included", "", schema, "/statement", "input"
        ),
        ReceiptReference(
            output,
            "dataset-observation",
            policy.observation_id,
            "included",
            "",
            schema,
            "/",
            "input",
        ),
        ReceiptReference(
            output, "dataset-version", policy.version_id, "included", "", schema, "/", "input"
        ),
        ReceiptReference(
            output, "evidence-right", policy.right_id, "included", "", schema, "/", "filter"
        ),
        ReceiptReference(
            output, "snapshot", policy.snapshot_digest, "included", "", schema, "/", "input"
        ),
        *extra,
    )


def _store_policy_refusal(
    conn: Any,
    policy: S7MethodPolicyEvidence,
    policy_bundle: SnapshotBundle,
    *,
    parameters: Mapping[str, object] | None = None,
    references: Iterable[ReceiptReference] | None = None,
) -> str:
    value = {"policy_id": policy.policy_id, "output_pointer": "/refusals/performance-estimator"}
    receipt_parameters = dict(parameters or _policy_parameters(policy, policy_bundle))
    receipt = make_receipt(
        claim_id="performance_estimator_refusal",
        output_locator="/refusals/performance-estimator",
        input_digest=_policy_input_digest(receipt_parameters),
        output_schema_id="s7-provenance-output/v1",
        current_attestation="D",
        live_attestation_ceiling="D",
        algorithm_id="s7-method-boundary/v1",
        algorithm_version="1",
        parameters=receipt_parameters,
        value=value,
        references=references or _policy_references(policy),
    )
    return store_receipt(conn, receipt)


def _policy_fixture() -> tuple[Any, S7MethodPolicyEvidence, SnapshotBundle]:
    conn = connect()
    initialize(conn)
    build_x3_fixture(conn)
    policy, policy_bundle = build_s7_terms_sources(conn)
    return conn, policy, policy_bundle


def test_s7_l1_l2_vintage_audit_uses_exact_paired_revision_modes() -> None:
    from decimal import Decimal

    from quant_allocator.evidence.fixtures.s7 import build_s7_fixture
    from quant_allocator.flagships.track_record_provenance.vintage import (
        RecordVintageFinding,
        audit_s7_vintages,
    )

    conn = connect()
    initialize(conn)
    manifest = build_s7_fixture(conn)

    early = audit_s7_vintages(
        conn, manifest, scenario="hedge-fund", cutoff_name="early"
    )
    late = audit_s7_vintages(
        conn, manifest, scenario="hedge-fund", cutoff_name="latest"
    )
    early_contract = next(
        contract
        for contract in manifest.bundle_contracts
        if contract.scenario == "hedge-fund" and contract.cutoff_name == "early"
    )
    late_contract = next(
        contract
        for contract in manifest.bundle_contracts
        if contract.scenario == "hedge-fund" and contract.cutoff_name == "latest"
    )

    assert early.analytic_bundle_digest == early_contract.analytic_bundle_digest
    assert early.audit_bundle_digest == early_contract.audit_bundle_digest
    assert late.analytic_bundle_digest == late_contract.analytic_bundle_digest
    assert late.audit_bundle_digest == late_contract.audit_bundle_digest
    assert early.analytic_bundle_digest != early.audit_bundle_digest
    assert late.analytic_bundle_digest != late.audit_bundle_digest
    assert not [
        finding
        for finding in early.findings
        if finding.finding_type == "return-restatement"
    ]

    restatements = [
        finding
        for finding in late.findings
        if finding.finding_type == "return-restatement"
    ]
    assert len(restatements) == 1
    restatement = restatements[0]
    assert isinstance(restatement, RecordVintageFinding)
    assert restatement.prior_value == Decimal("0.0100")
    assert restatement.later_value == Decimal("0.0080")
    assert restatement.effective_at.isoformat() == "2024-02-29T00:00:00+00:00"
    assert restatement.first_known_at.isoformat() == "2024-09-15T00:00:00+00:00"
    assert restatement.receipt_id in late.receipt_ids


def test_s7_l3_backfill_and_death_are_separate_late_receipted_findings() -> None:
    from quant_allocator.evidence.fixtures.s7 import build_s7_fixture
    from quant_allocator.flagships.track_record_provenance.vintage import (
        audit_s7_vintages,
    )

    conn = connect()
    initialize(conn)
    manifest = build_s7_fixture(conn)

    early_before = audit_s7_vintages(
        conn, manifest, scenario="hedge-fund", cutoff_name="early"
    )
    late = audit_s7_vintages(
        conn, manifest, scenario="hedge-fund", cutoff_name="latest"
    )
    early_after = audit_s7_vintages(
        conn, manifest, scenario="hedge-fund", cutoff_name="early"
    )

    assert early_before == early_after
    assert not {
        finding.finding_type for finding in early_before.findings
    } & {"return-backfill", "later-dead-product"}
    backfills = [
        finding
        for finding in late.findings
        if finding.finding_type == "return-backfill"
    ]
    deaths = [
        finding
        for finding in late.findings
        if finding.finding_type == "later-dead-product"
    ]
    assert len(backfills) == len(deaths) == 1
    backfill = backfills[0]
    death = deaths[0]
    source_key = conn.execute(
        "SELECT source_record_key FROM source_record WHERE source_record_id=?",
        (backfill.source_record_id,),
    ).fetchone()[0]
    assert source_key == "s7-hf-closed:2023-12"
    assert backfill.effective_at.isoformat() == "2023-12-31T00:00:00+00:00"
    assert backfill.first_known_at.isoformat() == "2024-09-15T00:00:00+00:00"
    assert death.effective_at.isoformat() == "2023-12-31T00:00:00+00:00"
    assert death.first_known_at.isoformat() == "2024-09-01T00:00:00+00:00"
    assert death.affected_observation_ids == backfill.affected_observation_ids
    assert death.receipt_id != backfill.receipt_id
    assert {death.receipt_id, backfill.receipt_id} <= set(late.receipt_ids)


def test_s7_l4_l5_l6_distinguish_coverage_inheritance_and_tombstone() -> None:
    from quant_allocator.evidence.fixtures.s7 import build_s7_fixture
    from quant_allocator.flagships.track_record_provenance.vintage import (
        CoverageVintageFinding,
        RecordVintageFinding,
        audit_s7_vintages,
    )

    conn = connect()
    initialize(conn)
    manifest = build_s7_fixture(conn)

    early = audit_s7_vintages(
        conn, manifest, scenario="hedge-fund", cutoff_name="early"
    )
    late = audit_s7_vintages(
        conn, manifest, scenario="hedge-fund", cutoff_name="latest"
    )

    coverage = [
        finding
        for finding in late.findings
        if isinstance(finding, CoverageVintageFinding)
        and finding.dataset_id == "dataset:s7-hedge-composite"
    ]
    assert len(coverage) == 1
    assert coverage[0].finding_type == "absence-not-inferable"
    assert coverage[0].reason_code == "absence-not-inferable"
    assert coverage[0].receipt_id in late.receipt_ids
    refusals = [
        refusal
        for refusal in late.historical_selection_refusals
        if refusal.dataset_id == "dataset:s7-hedge-composite"
    ]
    assert len(refusals) == 1
    assert refusals[0].reason_code == "membership-absence-not-inferable"
    assert refusals[0].receipt_id in late.receipt_ids

    source_ids = {
        row[0]: row[1]
        for row in conn.execute(
            "SELECT source_record_key,source_record_id FROM source_record "
            "WHERE dataset_id='dataset:s7-hedge-composite'"
        )
    }
    record_findings = [
        finding for finding in late.findings if isinstance(finding, RecordVintageFinding)
    ]
    assert source_ids["s7-hf-not-inferable"] not in {
        finding.source_record_id for finding in record_findings
    }
    assert not [
        finding
        for finding in record_findings
        if finding.source_record_id == source_ids["s7-hf-inherited"]
        and finding.finding_type == "withdrawal-or-tombstone"
    ]
    tombstones = [
        finding
        for finding in record_findings
        if finding.source_record_id == source_ids["s7-hf-tombstoned"]
        and finding.finding_type == "withdrawal-or-tombstone"
    ]
    assert len(tombstones) == 1
    tombstone = tombstones[0]
    assert tombstone.reason_code == "manager-withdrawal"
    assert tombstone.effective_at.isoformat() == "2024-02-29T00:00:00+00:00"
    assert tombstone.first_known_at.isoformat() == "2024-09-15T00:00:00+00:00"
    assert len(tombstone.affected_observation_ids) == 2
    assert not [
        finding
        for finding in early.findings
        if isinstance(finding, RecordVintageFinding)
        and finding.finding_type == "withdrawal-or-tombstone"
    ]
    tombstone_refs = conn.execute(
        "SELECT dataset_observation_id,disposition,reason_code FROM receipt_reference "
        "WHERE receipt_id=? AND reference_type='dataset-observation' ORDER BY ordinal",
        (tombstone.receipt_id,),
    ).fetchall()
    assert {row[0] for row in tombstone_refs} == set(
        tombstone.affected_observation_ids
    )
    assert {tuple(row[1:]) for row in tombstone_refs} == {
        ("included", ""),
        ("excluded", "manager-withdrawal"),
    }


def test_s7_l7_retro_membership_is_late_visible_with_exact_x3_closure() -> None:
    from quant_allocator.evidence.fixtures.s7 import (
        build_s7_fixture,
        verify_s7_manifest,
    )
    from quant_allocator.flagships.track_record_provenance.vintage import (
        RecordVintageFinding,
        audit_s7_vintages,
        verify_s7_vintage_receipt,
    )

    conn = connect()
    initialize(conn)
    manifest = build_s7_fixture(conn)

    early = audit_s7_vintages(
        conn, manifest, scenario="hedge-fund", cutoff_name="early"
    )
    late = audit_s7_vintages(
        conn, manifest, scenario="hedge-fund", cutoff_name="latest"
    )

    assert not [
        finding
        for finding in early.findings
        if finding.finding_type == "retroactive-membership"
    ]
    retro = [
        finding
        for finding in late.findings
        if finding.finding_type == "retroactive-membership"
    ]
    assert len(retro) == 1
    finding = retro[0]
    assert isinstance(finding, RecordVintageFinding)
    assert finding.effective_at.isoformat() == "2024-01-01T00:00:00+00:00"
    assert finding.first_known_at.isoformat() == "2024-09-01T00:00:00+00:00"
    assert len(finding.mapping_ids) == 1
    assert len(finding.membership_ids) == 1
    assert len(finding.observation_membership_link_ids) == 1

    early_reference_ids = {
        row[0]
        for receipt_id in early.receipt_ids
        for row in conn.execute(
            "SELECT coalesce(entity_mapping_id,universe_membership_id,"
            "observation_membership_link_id) FROM receipt_reference "
            "WHERE receipt_id=? AND reference_type IN "
            "('entity-mapping','universe-membership','observation-membership-link')",
            (receipt_id,),
        )
    }
    assert not early_reference_ids & {
        *finding.mapping_ids,
        *finding.membership_ids,
        *finding.observation_membership_link_ids,
    }
    late_reference_ids = {
        row[0]
        for row in conn.execute(
            "SELECT coalesce(entity_mapping_id,universe_membership_id,"
            "observation_membership_link_id) FROM receipt_reference "
            "WHERE receipt_id=? AND reference_type IN "
            "('entity-mapping','universe-membership','observation-membership-link')",
            (finding.receipt_id,),
        )
    }
    assert not late_reference_ids
    assert verify_s7_manifest(conn, manifest)
    verify_s7_vintage_receipt(
        conn,
        manifest,
        scenario="hedge-fund",
        cutoff_name="latest",
        receipt_id=finding.receipt_id,
    )


@pytest.mark.parametrize("forbidden_argument", ("known_at", "roster", "memberships", "mappings"))
def test_s7_l20_vintage_api_rejects_caller_authored_time_state(
    forbidden_argument: str,
) -> None:
    from quant_allocator.flagships.track_record_provenance.vintage import (
        audit_s7_vintages,
    )

    with pytest.raises(TypeError, match="unexpected keyword argument"):
        audit_s7_vintages(
            None,
            None,
            scenario="hedge-fund",
            cutoff_name="early",
            **{forbidden_argument: object()},
        )


def test_s7_l22_builder_order_preserves_findings_receipts_and_json_bytes() -> None:
    from quant_allocator.evidence.fixtures.credit import build_s7_credit_sources
    from quant_allocator.evidence.fixtures.private_markets import (
        build_s7_private_market_sources,
    )
    from quant_allocator.evidence.fixtures.public_markets import (
        build_s7_public_market_sources,
    )
    from quant_allocator.evidence.fixtures.s7 import build_s7_fixture
    from quant_allocator.evidence.fixtures.terms import build_s7_terms_sources
    from quant_allocator.flagships.track_record_provenance.vintage import (
        audit_s7_vintages,
        vintage_result_bytes,
    )

    normal = connect()
    initialize(normal)
    normal_manifest = build_s7_fixture(normal)

    permuted = connect()
    initialize(permuted)
    build_x3_fixture(permuted)
    for builder in (
        build_s7_terms_sources,
        build_s7_private_market_sources,
        build_s7_credit_sources,
        build_s7_public_market_sources,
    ):
        builder(permuted)
    permuted_manifest = build_s7_fixture(permuted)

    normal_result = audit_s7_vintages(
        normal,
        normal_manifest,
        scenario="hedge-fund",
        cutoff_name="latest",
    )
    permuted_result = audit_s7_vintages(
        permuted,
        permuted_manifest,
        scenario="hedge-fund",
        cutoff_name="latest",
    )

    assert normal_manifest == permuted_manifest
    assert normal_result == permuted_result
    assert normal_result.receipt_ids == permuted_result.receipt_ids
    assert vintage_result_bytes(normal_result) == vintage_result_bytes(permuted_result)


def test_s7_l23_substrate_conflict_emits_no_vintage_output() -> None:
    from quant_allocator.evidence.fixtures.s7 import build_s7_fixture
    from quant_allocator.flagships.track_record_provenance.vintage import (
        audit_s7_vintages,
    )

    conn = connect()
    initialize(conn)
    manifest = build_s7_fixture(conn)
    target = conn.execute(
        "SELECT i.evidence_item_id FROM evidence_item i JOIN source_record s "
        "USING(source_record_id) WHERE s.dataset_id='dataset:s7-hedge-composite' "
        "AND i.record_kind='s7-periodic-return' ORDER BY i.evidence_item_id LIMIT 1"
    ).fetchone()[0]
    before = conn.execute(
        "SELECT COUNT(*) FROM reconstruction_receipt WHERE claim_id IN "
        "('s7_vintage_finding','s7_historical_selection_refusal')"
    ).fetchone()[0]
    for trigger in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='trigger' AND tbl_name='evidence_item' "
        "AND sql LIKE '%BEFORE UPDATE%'"
    ).fetchall():
        conn.execute(f'DROP TRIGGER "{trigger[0]}"')
    conn.execute(
        "UPDATE evidence_item SET payload_json='{}' WHERE evidence_item_id=?", (target,)
    )

    with pytest.raises(ValueError, match="s7-substrate-conflict"):
        audit_s7_vintages(
            conn, manifest, scenario="hedge-fund", cutoff_name="latest"
        )
    after = conn.execute(
        "SELECT COUNT(*) FROM reconstruction_receipt WHERE claim_id IN "
        "('s7_vintage_finding','s7_historical_selection_refusal')"
    ).fetchone()[0]
    assert after == before


def test_s7_l24_public_lineage_renders_but_historical_selection_refuses() -> None:
    from quant_allocator.evidence.fixtures.s7 import build_s7_fixture
    from quant_allocator.flagships.track_record_provenance.lineage import (
        build_lineage_from_s7_projections,
    )
    from quant_allocator.flagships.track_record_provenance.vintage import (
        CoverageVintageFinding,
        audit_s7_vintages,
        verify_s7_vintage_receipt,
    )

    conn = connect()
    initialize(conn)
    manifest = build_s7_fixture(conn)

    result = audit_s7_vintages(
        conn, manifest, scenario="public-equity", cutoff_name="latest"
    )
    coverage = [
        finding
        for finding in result.findings
        if isinstance(finding, CoverageVintageFinding)
        and finding.dataset_id == "dataset:s7-public-registered"
    ]
    refusals = [
        refusal
        for refusal in result.historical_selection_refusals
        if refusal.dataset_id == "dataset:s7-public-registered"
    ]
    assert len(coverage) == len(refusals) == 1
    assert refusals[0].reason_code == "dead-product-vintage-missing"
    assert refusals[0].reason_codes == ("dead-product-vintage-missing",)
    assert refusals[0].receipt_id in result.receipt_ids
    verify_s7_vintage_receipt(
        conn,
        manifest,
        scenario="public-equity",
        cutoff_name="latest",
        receipt_id=refusals[0].receipt_id,
    )

    source_observation = conn.execute(
        "SELECT o.dataset_observation_id FROM dataset_observation o "
        "JOIN evidence_item i USING(evidence_item_id) "
        "JOIN source_record s USING(source_record_id) "
        "WHERE s.source_record_key='s7-public-no-archive' "
        "AND o.observation_status='present'"
    ).fetchone()[0]
    lineage = build_lineage_from_s7_projections(
        conn, manifest, scenario="public-equity", cutoff_name="latest"
    )
    assert source_observation in lineage.admitted_observation_ids
    assert not hasattr(coverage[0], "source_record_id")


def test_s7_policy_refusal_receipt_accepts_exact_reviewed_policy_closure() -> None:
    conn, policy, policy_bundle = _policy_fixture()
    receipt_id = _store_policy_refusal(conn, policy, policy_bundle)

    verify_s7_policy_refusal_receipt(
        conn, receipt_id=receipt_id, policy_bundle=policy_bundle, policy=policy
    )


def test_s7_policy_refusal_receipt_rejects_surplus_typed_reference() -> None:
    conn, policy, policy_bundle = _policy_fixture()
    receipt_id = _store_policy_refusal(
        conn,
        policy,
        policy_bundle,
        references=_policy_references(
            policy,
            extra=(
                ReceiptReference(
                    "/refusals/performance-estimator",
                    "evidence-item",
                    policy.item_id,
                    "included",
                    "",
                    policy.payload_schema_id,
                    "/",
                    "filter",
                ),
            ),
        ),
    )

    with pytest.raises(EvidenceRefusal, match="s7-policy-refusal-closure-invalid"):
        verify_s7_policy_refusal_receipt(
            conn, receipt_id=receipt_id, policy_bundle=policy_bundle, policy=policy
        )


def test_s7_policy_refusal_receipt_rejects_existing_reference_role_mutation() -> None:
    conn, policy, policy_bundle = _policy_fixture()
    references = list(_policy_references(policy))
    assert len(references) == 6
    references[3] = replace(references[3], role="filter")
    receipt_id = _store_policy_refusal(
        conn, policy, policy_bundle, references=references
    )

    with pytest.raises(EvidenceRefusal, match="s7-policy-refusal-closure-invalid"):
        verify_s7_policy_refusal_receipt(
            conn, receipt_id=receipt_id, policy_bundle=policy_bundle, policy=policy
        )


def test_s7_policy_refusal_receipt_rejects_join_receipt_outside_canonical_parameters() -> None:
    conn, policy, policy_bundle = _policy_fixture()
    parameters = _policy_parameters(policy, policy_bundle)
    parameters["policy_join_receipt_id"] = policy.slice_receipt_id
    receipt_id = _store_policy_refusal(
        conn, policy, policy_bundle, parameters=parameters
    )

    with pytest.raises(EvidenceRefusal, match="s7-policy-refusal-closure-invalid"):
        verify_s7_policy_refusal_receipt(
            conn, receipt_id=receipt_id, policy_bundle=policy_bundle, policy=policy
        )


def test_s7_policy_refusal_receipt_rejects_tampered_policy_span_offset() -> None:
    conn, policy, policy_bundle = _policy_fixture()
    receipt_id = _store_policy_refusal(conn, policy, policy_bundle)
    for trigger in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='trigger' AND tbl_name='evidence_span' "
        "AND sql LIKE '%BEFORE UPDATE%'"
    ).fetchall():
        conn.execute(f'DROP TRIGGER "{trigger[0]}"')
    conn.execute(
        "UPDATE evidence_span SET start_char=1 WHERE evidence_span_id=?", (policy.span_id,)
    )

    with pytest.raises(EvidenceRefusal, match="s7-policy-refusal-closure-invalid"):
        verify_s7_policy_refusal_receipt(
            conn, receipt_id=receipt_id, policy_bundle=policy_bundle, policy=policy
        )


@pytest.mark.parametrize(
    ("field_name", "value"),
    (("revision_mode", "all-known-versions"), ("include_unresolved", False)),
)
def test_s7_policy_refusal_receipt_rejects_spoofed_supplied_bundle_request(
    field_name: str, value: object
) -> None:
    conn, policy, policy_bundle = _policy_fixture()
    receipt_id = _store_policy_refusal(conn, policy, policy_bundle)
    source = replace(policy_bundle.request.sources[0], **{field_name: value})
    spoofed_bundle = replace(
        policy_bundle,
        request=replace(policy_bundle.request, sources=(source,)),
        slices=(replace(policy_bundle.slices[0], request=source),),
    )

    with pytest.raises(EvidenceRefusal, match="s7-policy-refusal-closure-invalid"):
        verify_s7_policy_refusal_receipt(
            conn, receipt_id=receipt_id, policy_bundle=spoofed_bundle, policy=policy
        )
