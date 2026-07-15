"""Public-contract tests for S7 track-record provenance."""

import json
from dataclasses import FrozenInstanceError, asdict, fields, replace
from datetime import date
from decimal import Decimal

import pytest

from quant_allocator.evidence.fixtures.terms import build_s7_terms_sources
from quant_allocator.evidence.fixtures.x3 import build_x3_fixture
from quant_allocator.evidence.schema import connect, initialize
from quant_allocator.flagships.track_record_provenance.model import (
    FORBIDDEN_ESTIMATOR_OR_RANKING_FIELDS,
    EntityGrain,
    PolicyRefusalContract,
    TRACK_RECORD_PROVENANCE_CONTRACT,
    TrackObservation,
)


def test_track_record_provenance_exposes_named_public_contract() -> None:
    """S7 starts with a stable no-estimator/refusal contract boundary."""
    assert TRACK_RECORD_PROVENANCE_CONTRACT


def test_track_observation_preserves_source_decimal_without_float_coercion() -> None:
    """S7 contract values stay exact until a later admitted-panel task."""
    source_value = Decimal("0.0100")

    observation = TrackObservation(
        observation_id="observation:s7-1",
        source_record_id="source-record:s7-1",
        evidence_item_id="evidence:s7-1",
        dataset_observation_id="dataset-observation:s7-1",
        canonical_entity_id="strategy:s7-1",
        entity_grain=EntityGrain.STRATEGY,
        observed_at=date(2024, 1, 31),
        value=source_value,
        value_kind="total-return",
        basis_signature_id="basis:s7-1",
        version=1,
    )

    assert observation.value is source_value
    assert isinstance(observation.value, Decimal)
    with pytest.raises(ValueError, match="s7-decimal-required"):
        TrackObservation(
            observation_id="observation:s7-float",
            source_record_id="source-record:s7-1",
            evidence_item_id="evidence:s7-1",
            dataset_observation_id="dataset-observation:s7-1",
            canonical_entity_id="strategy:s7-1",
            entity_grain=EntityGrain.STRATEGY,
            observed_at=date(2024, 1, 31),
            value=0.01,  # type: ignore[arg-type]
            value_kind="total-return",
            basis_signature_id="basis:s7-1",
            version=1,
        )


def test_entity_grain_is_closed_to_the_public_s7_enum() -> None:
    """A S7 row cannot choose an arbitrary or stringly typed entity grain."""
    assert EntityGrain.STRATEGY.value == "strategy"
    with pytest.raises(ValueError, match="s7-entity-grain-invalid"):
        TrackObservation(
            observation_id="observation:s7-invalid-grain",
            source_record_id="source-record:s7-1",
            evidence_item_id="evidence:s7-1",
            dataset_observation_id="dataset-observation:s7-1",
            canonical_entity_id="strategy:s7-1",
            entity_grain="arbitrary",  # type: ignore[arg-type]
            observed_at=date(2024, 1, 31),
            value=Decimal("0.0100"),
            value_kind="total-return",
            basis_signature_id="basis:s7-1",
            version=1,
        )


def test_track_observation_excludes_caller_authored_knowledge_time() -> None:
    """Only the evidence substrate may derive availability or knowledge time."""
    names = {field.name for field in fields(TrackObservation)}
    assert {"available_at", "known_at", "knowledge_at"}.isdisjoint(names)
    with pytest.raises(TypeError, match="available_at"):
        TrackObservation(
            observation_id="observation:s7-time",
            source_record_id="source-record:s7-1",
            evidence_item_id="evidence:s7-1",
            dataset_observation_id="dataset-observation:s7-1",
            canonical_entity_id="strategy:s7-1",
            entity_grain=EntityGrain.STRATEGY,
            observed_at=date(2024, 1, 31),
            value=Decimal("0.0100"),
            value_kind="total-return",
            basis_signature_id="basis:s7-1",
            version=1,
            available_at="caller-authored",  # type: ignore[call-arg]
        )


def test_forbidden_estimator_and_ranking_fields_cannot_be_constructed() -> None:
    """The model cannot carry the estimator or ranking outputs owned by other cards."""
    names = {field.name for field in fields(TrackObservation)}
    assert set(FORBIDDEN_ESTIMATOR_OR_RANKING_FIELDS).isdisjoint(names)
    with pytest.raises(TypeError, match="alpha"):
        TrackObservation(
            observation_id="observation:s7-alpha",
            source_record_id="source-record:s7-1",
            evidence_item_id="evidence:s7-1",
            dataset_observation_id="dataset-observation:s7-1",
            canonical_entity_id="strategy:s7-1",
            entity_grain=EntityGrain.STRATEGY,
            observed_at=date(2024, 1, 31),
            value=Decimal("0.0100"),
            value_kind="total-return",
            basis_signature_id="basis:s7-1",
            version=1,
            alpha=Decimal("0.01"),  # type: ignore[call-arg]
        )


def test_policy_refusal_contract_pins_the_reviewed_s7_fixture_policy() -> None:
    """The future refusal recipe is closed over the reviewed fixture handle."""
    conn = connect()
    initialize(conn)
    build_x3_fixture(conn)
    policy, bundle = build_s7_terms_sources(conn)

    policy_version = conn.execute(
        "SELECT delivery_mode FROM dataset_version WHERE dataset_version_id=?",
        (policy.version_id,),
    ).fetchone()
    policy_item = conn.execute(
        "SELECT payload_schema_id,content_sha256,payload_json FROM evidence_item "
        "WHERE evidence_item_id=?",
        (policy.item_id,),
    ).fetchone()
    assert policy_version is not None
    assert policy_item is not None
    policy_payload = json.loads(policy_item["payload_json"])

    contract = PolicyRefusalContract.from_fixture(conn=conn, policy=policy)

    assert contract.claim_id == "performance_estimator_refusal"
    assert contract.output_pointer == "/refusals/performance-estimator"
    assert contract.current_attestation == "D"
    assert contract.live_attestation_ceiling == "D"
    assert contract.access_semantics == "refusal-in-every-context"
    assert contract.policy_id == policy.policy_id == "s7-method-boundary/v1"
    assert contract.policy_dataset_id == policy.dataset_id == "dataset:s7-method-boundary"
    assert contract.policy_access_context == "public"
    assert contract.policy_dataset_delivery_mode == policy_version["delivery_mode"]
    assert contract.policy_licence_purpose == "s7-research"
    assert contract.policy_payload_schema_id == policy_item["payload_schema_id"] == policy.payload_schema_id
    assert contract.policy_payload_schema_sha256 == policy.payload_schema_sha256
    assert contract.policy_payload_sha256 == policy_item["content_sha256"] == policy.payload_sha256
    assert policy_payload == {
        "policy_id": contract.policy_id,
        "output_pointer": contract.output_pointer,
        "prohibited_outputs": "alpha|sharpe|irr|pme|skill|manager-ranking",
        "statement": (
            "S7 reconstructs lineage and basis-qualified panels; it does not estimate alpha, "
            "Sharpe, IRR, PME, skill, or manager ranking."
        ),
    }
    assert contract.policy_item_id == policy.item_id
    assert contract.policy_span_id == policy.span_id
    assert contract.policy_observation_id == policy.observation_id
    assert contract.policy_version_id == policy.version_id
    assert contract.policy_right_id == policy.right_id
    assert contract.policy_snapshot_digest == policy.snapshot_digest
    assert contract.policy_slice_receipt_id == policy.slice_receipt_id
    assert contract.policy_bundle_digest == policy.bundle_digest == bundle.bundle_digest
    assert contract.policy_join_receipt_id == policy.join_receipt_id == bundle.join_receipt_id
    assert contract.policy_join_receipt_binding == "parameters-and-input-digest-only"
    assert contract.policy_included_reference_roles == (
        ("policy-item", "evidence-item", policy.item_id, "included", "input"),
        ("policy-span", "evidence-span", policy.span_id, "included", "input"),
        ("policy-observation", "dataset-observation", policy.observation_id, "included", "input"),
        ("policy-version", "dataset-version", policy.version_id, "included", "input"),
        ("policy-right", "evidence-right", policy.right_id, "included", "filter"),
        ("policy-snapshot", "snapshot", policy.snapshot_digest, "included", "input"),
    )
    assert contract.policy_parameter_identity == (
        policy.item_id,
        policy.span_id,
        policy.observation_id,
        policy.version_id,
        policy.right_id,
        policy.snapshot_digest,
        bundle.bundle_digest,
        bundle.join_receipt_id,
        policy_item["payload_schema_id"],
        policy.payload_schema_sha256,
        policy_item["content_sha256"],
    )
    contract_values = asdict(contract)
    required_fields = (
        "policy_access_context",
        "policy_dataset_delivery_mode",
        "policy_licence_purpose",
        "policy_payload_schema_id",
        "policy_payload_schema_sha256",
        "policy_payload_sha256",
        "policy_included_reference_roles",
        "policy_join_receipt_binding",
        "policy_parameter_identity",
    )
    assert set(required_fields).issubset(contract_values)
    assert "policy_refusal_receipt_id" not in contract_values
    for field_name in required_fields:
        missing_field_values = dict(contract_values)
        del missing_field_values[field_name]
        with pytest.raises(TypeError, match=field_name):
            PolicyRefusalContract(**missing_field_values)
    for field_name, incorrect_value, error_code in (
        ("policy_access_context", "licensed", "policy_access_context"),
        ("policy_dataset_delivery_mode", "delta", "policy_dataset_delivery_mode"),
        ("policy_licence_purpose", "other-purpose", "policy_licence_purpose"),
        ("policy_join_receipt_binding", "typed-reference", "policy_join_receipt_binding"),
        ("policy_included_reference_roles", (), "reference-roles-invalid"),
        ("policy_item_id", "evidence-item:other", "reference-roles-invalid"),
        ("policy_span_id", "evidence-span:other", "reference-roles-invalid"),
        ("policy_observation_id", "dataset-observation:other", "reference-roles-invalid"),
        ("policy_version_id", "dataset-version:other", "reference-roles-invalid"),
        ("policy_right_id", "evidence-right:other", "reference-roles-invalid"),
        ("policy_snapshot_digest", "snapshot:other", "reference-roles-invalid"),
    ):
        with pytest.raises(ValueError, match=error_code):
            replace(contract, **{field_name: incorrect_value})
    # The production fixture is immutable; remove only its local test guard to prove the
    # factory refuses a tampered persisted delivery identity rather than trusting its handle.
    conn.execute("DROP TRIGGER immutable_update_dataset_version")
    conn.execute(
        "UPDATE dataset_version SET delivery_mode='delta',base_dataset_version_id=dataset_version_id "
        "WHERE dataset_version_id=?",
        (policy.version_id,),
    )
    with pytest.raises(ValueError, match="fixture-delivery-identity-invalid"):
        PolicyRefusalContract.from_fixture(conn=conn, policy=policy)
    conn.execute(
        "UPDATE dataset_version SET delivery_mode='full-snapshot',base_dataset_version_id=NULL "
        "WHERE dataset_version_id=?",
        (policy.version_id,),
    )
    conn.execute("DROP TRIGGER immutable_update_evidence_item")
    conn.execute(
        "UPDATE evidence_item SET payload_json=? WHERE evidence_item_id=?",
        (json.dumps({**policy_payload, "policy_id": "s7-method-boundary/tampered"}), policy.item_id),
    )
    with pytest.raises(ValueError, match="fixture-payload-identity-invalid"):
        PolicyRefusalContract.from_fixture(conn=conn, policy=policy)
    with pytest.raises(FrozenInstanceError):
        contract.output_pointer = "/refusals/other"  # type: ignore[misc]


def test_policy_refusal_factory_rejects_substituted_closure_ids() -> None:
    """The fixture factory verifies every persisted policy and bundle closure ID."""
    conn = connect()
    initialize(conn)
    build_x3_fixture(conn)
    policy, _ = build_s7_terms_sources(conn)

    for field_name, outside_id in (
        ("span_id", "evidence-span:outside"),
        ("observation_id", "dataset-observation:outside"),
        ("snapshot_digest", "snapshot:outside"),
        ("slice_receipt_id", "receipt:outside-slice"),
        ("bundle_digest", "bundle:outside"),
        ("join_receipt_id", "receipt:outside-join"),
    ):
        with pytest.raises(ValueError, match="fixture-.*-identity-invalid"):
            PolicyRefusalContract.from_fixture(
                conn=conn,
                policy=replace(policy, **{field_name: outside_id}),
            )


def test_policy_refusal_factory_rejects_same_item_truncated_statement_span() -> None:
    """A persisted same-pointer span must still bind the exact authored statement bytes."""
    from quant_allocator.evidence.ingest import ingest_spans
    from quant_allocator.evidence.model import (
        EvidenceSpanRecord,
        sha256,
        with_machine_id,
    )

    conn = connect()
    initialize(conn)
    build_x3_fixture(conn)
    policy, _ = build_s7_terms_sources(conn)
    payload = json.loads(
        conn.execute(
            "SELECT payload_json FROM evidence_item WHERE evidence_item_id=?",
            (policy.item_id,),
        ).fetchone()[0]
    )
    statement = str(payload["statement"])
    truncated_span = with_machine_id(
        "span",
        EvidenceSpanRecord(
            "",
            policy.item_id,
            "/statement",
            1,
            len(statement),
            sha256(statement[1:].encode()),
        ),
    )
    ingest_spans(conn, (truncated_span,))

    with pytest.raises(ValueError, match="fixture-reference-identity-invalid"):
        PolicyRefusalContract.from_fixture(
            conn=conn,
            policy=replace(policy, span_id=truncated_span.evidence_span_id),
        )
