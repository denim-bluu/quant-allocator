from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime
from typing import Mapping, Sequence

from quant_allocator.evidence.checks import refuse
from quant_allocator.evidence.lineage import make_receipt, store_receipt, verify_receipt
from quant_allocator.evidence.model import (
    ReceiptReference,
    SnapshotBundle,
    canonical_bytes,
    normalize_utc,
    sha256,
)
from quant_allocator.flagships.knowledge.operational_evidence import (
    OperationalEvidenceFixture,
    OperationalSourceSchemaManifest,
)

from .core import E4_MIN_INDEPENDENT_GROUPS, E4_STALE_DAYS, METHOD_VERSION, FactContext

OUTPUT_SCHEMA_ID = "schema:generic-v1"
RECEIPT_ALGORITHM = "e4-operational-claim-closure"
RECEIPT_VERSION = "1"
CLAIM_LIVE_CEILINGS = {
    "public_operational_facts": "C",
    "operational_change_graph": "B",
    "operational_evidence_state": "B",
    "reunderwriting_queue": "B",
    "operational_data_boundary_refusals": "D",
    "operational_method_boundary_refusal": "D",
    "synthetic_state_validation": "D",
}
SOURCE_VIEW_DATASETS = {
    "public-only": (
        "dataset:e4-public-registry",
        "dataset:e4-operational-policy",
    ),
    "all-entitled": (
        "dataset:e4-public-registry",
        "dataset:e4-manager-documents",
        "dataset:e4-control-evidence",
        "dataset:e4-independent-references",
        "dataset:e4-operational-policy",
    ),
}


@dataclass(frozen=True, slots=True)
class SourceBundleClosure:
    dataset_id: str
    slice_digest: str
    slice_receipt_id: str
    join_receipt_id: str
    bundle_digest: str


@dataclass(frozen=True, slots=True)
class VerificationEnvelopeClosure:
    join_receipt_id: str
    bundle_digest: str


@dataclass(frozen=True, slots=True)
class FactClosureBinding:
    fact_id: str
    evidence_item_id: str
    evidence_span_id: str
    dataset_observation_id: str
    dataset_version_id: str
    predicate: str
    subject_entity_id: str
    typed_value: str
    temporal_type: str
    effective_at: str | None
    effective_from: str | None
    effective_to: str | None
    entity_relationship_id: str | None
    relationship_source_entity_id: str | None
    relationship_target_entity_id: str | None
    relationship_temporal_type: str | None
    relationship_effective_at: str | None
    relationship_effective_from: str | None
    relationship_effective_to: str | None


@dataclass(frozen=True, slots=True)
class OperationalClaimClosure:
    claim_id: str
    algorithm_version: str
    decision_at: str
    access_view: str
    output_pointer: str
    ordered_source_bundles: tuple[SourceBundleClosure, ...]
    verification_envelope: VerificationEnvelopeClosure
    composite_union_input_digest: str
    method_constants_digest: str
    fact_bindings: tuple[FactClosureBinding, ...]
    references: tuple[ReceiptReference, ...]
    value: object

    @property
    def parameter_payload(self) -> dict[str, object]:
        return {
            "algorithm_version": self.algorithm_version,
            "decision_at": self.decision_at,
            "access_view": self.access_view,
            "output_pointer": self.output_pointer,
            "ordered_source_bundles": [
                {
                    "dataset_id": row.dataset_id,
                    "slice_digest": row.slice_digest,
                    "slice_receipt_id": row.slice_receipt_id,
                    "join_receipt_id": row.join_receipt_id,
                    "bundle_digest": row.bundle_digest,
                }
                for row in self.ordered_source_bundles
            ],
            "verification_envelope": {
                "join_receipt_id": self.verification_envelope.join_receipt_id,
                "bundle_digest": self.verification_envelope.bundle_digest,
            },
            "composite_union_input_digest": self.composite_union_input_digest,
            "method_constants_digest": self.method_constants_digest,
            "fact_bindings": [
                {
                    "fact_id": row.fact_id,
                    "evidence_item_id": row.evidence_item_id,
                    "evidence_span_id": row.evidence_span_id,
                    "dataset_observation_id": row.dataset_observation_id,
                    "dataset_version_id": row.dataset_version_id,
                    "predicate": row.predicate,
                    "subject_entity_id": row.subject_entity_id,
                    "typed_value": row.typed_value,
                    "temporal_type": row.temporal_type,
                    "effective_at": row.effective_at,
                    "effective_from": row.effective_from,
                    "effective_to": row.effective_to,
                    "entity_relationship_id": row.entity_relationship_id,
                    "relationship_source_entity_id": row.relationship_source_entity_id,
                    "relationship_target_entity_id": row.relationship_target_entity_id,
                    "relationship_temporal_type": row.relationship_temporal_type,
                    "relationship_effective_at": row.relationship_effective_at,
                    "relationship_effective_from": row.relationship_effective_from,
                    "relationship_effective_to": row.relationship_effective_to,
                }
                for row in self.fact_bindings
            ],
        }


def _schema_pointers(row: OperationalSourceSchemaManifest) -> tuple[str, ...]:
    return (
        row.manager_entity_id_pointer,
        row.domain_pointer,
        row.subject_entity_id_pointer,
        row.predicate_pointer,
        row.scope_pointer,
        row.typed_value_pointer,
        row.temporal_type_pointer,
        row.effective_at_pointer,
        row.effective_from_pointer,
        row.effective_to_pointer,
        row.source_available_at_pointer,
        row.freshness_at_pointer,
        row.source_family_pointer,
        row.independence_group_pointer,
        row.assertion_kind_pointer,
        row.incident_materiality_pointer,
    )


def _source_closures(source_bundles: Sequence[SnapshotBundle]) -> tuple[SourceBundleClosure, ...]:
    rows: list[SourceBundleClosure] = []
    for bundle in source_bundles:
        if len(bundle.slices) != 1 or bundle.slices[0].receipt_id is None:
            refuse("operational-source-bundle-invalid")
        slice_ = bundle.slices[0]
        rows.append(
            SourceBundleClosure(
                slice_.request.dataset_id,
                slice_.digest,
                slice_.receipt_id,
                bundle.join_receipt_id,
                bundle.bundle_digest,
            )
        )
    dataset_ids = tuple(row.dataset_id for row in rows)
    if len(dataset_ids) != len(set(dataset_ids)):
        refuse("operational-source-bundle-duplicate")
    return tuple(rows)


def _fact_binding(
    fixture: OperationalEvidenceFixture, context: FactContext
) -> FactClosureBinding:
    fact = context.fact
    relationship_source = None
    relationship_target = None
    relationship_temporal_type = None
    relationship_effective_at = None
    relationship_effective_from = None
    relationship_effective_to = None
    if fact.entity_relationship_id is not None:
        relationship = fixture.conn.execute(
            "SELECT source_entity_id,target_entity_id,temporal_type,effective_at,effective_from,"
            "effective_to FROM entity_relationship "
            "WHERE entity_relationship_id=?",
            (fact.entity_relationship_id,),
        ).fetchone()
        if relationship is None:
            refuse("operational-receipt-relationship-missing")
        relationship_source = relationship["source_entity_id"]
        relationship_target = relationship["target_entity_id"]
        relationship_temporal_type = relationship["temporal_type"]
        relationship_effective_at = relationship["effective_at"]
        relationship_effective_from = relationship["effective_from"]
        relationship_effective_to = relationship["effective_to"]
    return FactClosureBinding(
        fact.fact_id,
        fact.evidence_item_id,
        fact.evidence_span_id,
        fact.dataset_observation_id,
        fact.dataset_version_id,
        fact.predicate,
        fact.subject_entity_id,
        fact.typed_value,
        fact.temporal_type,
        normalize_utc(fact.effective_at) if fact.effective_at else None,
        normalize_utc(fact.effective_from) if fact.effective_from else None,
        normalize_utc(fact.effective_to) if fact.effective_to else None,
        fact.entity_relationship_id,
        relationship_source,
        relationship_target,
        relationship_temporal_type,
        relationship_effective_at,
        relationship_effective_from,
        relationship_effective_to,
    )


def _reference_id(row: sqlite3.Row) -> str:
    columns = {
        "dataset-observation": "dataset_observation_id",
        "dataset-version": "dataset_version_id",
        "evidence-item": "evidence_item_id",
        "evidence-right": "evidence_right_id",
        "evidence-span": "evidence_span_id",
        "entity-mapping": "entity_mapping_id",
        "entity-relationship": "entity_relationship_id",
        "snapshot": "snapshot_digest",
        "source-record": "source_record_id",
    }
    try:
        return row[columns[row["reference_type"]]]
    except KeyError:
        refuse("operational-receipt-reference-invalid")


def _item_references(
    fixture: OperationalEvidenceFixture,
    *,
    context: FactContext,
    output_pointer: str,
    snapshot_digest: str,
    disposition: str,
    role: str,
) -> tuple[ReceiptReference, ...]:
    schema = next(
        row
        for row in fixture.manifest.source_schema_manifests
        if row.dataset_id == context.dataset_id
    )
    spans = {
        row["json_pointer"]: row["evidence_span_id"]
        for row in fixture.conn.execute(
            "SELECT json_pointer,evidence_span_id FROM evidence_span "
            "WHERE evidence_item_id=? ORDER BY json_pointer,evidence_span_id",
            (context.fact.evidence_item_id,),
        )
    }
    mappings = tuple(
        row[0]
        for row in fixture.conn.execute(
            "SELECT entity_mapping_id FROM entity_mapping WHERE source_evidence_item_id=? "
            "AND dataset_observation_id=? ORDER BY entity_mapping_id",
            (context.fact.evidence_item_id, context.fact.dataset_observation_id),
        )
    )
    version_right = fixture.conn.execute(
        "SELECT acquisition_right_id FROM dataset_version WHERE dataset_version_id=?",
        (context.fact.dataset_version_id,),
    ).fetchone()[0]
    right_ids = tuple(sorted({context.fact.evidence_right_id, version_right}))
    references: list[ReceiptReference] = []
    for pointer in _schema_pointers(schema):
        common = (disposition, "", schema.payload_schema_id, pointer, role)
        references.extend(
            (
                ReceiptReference(
                    output_pointer,
                    "evidence-item",
                    context.fact.evidence_item_id,
                    *common,
                ),
                ReceiptReference(
                    output_pointer,
                    "source-record",
                    context.source_record_id,
                    *common,
                ),
                ReceiptReference(
                    output_pointer,
                    "dataset-observation",
                    context.fact.dataset_observation_id,
                    *common,
                ),
                ReceiptReference(
                    output_pointer,
                    "dataset-version",
                    context.fact.dataset_version_id,
                    *common,
                ),
                ReceiptReference(output_pointer, "snapshot", snapshot_digest, *common),
            )
        )
        references.extend(
            ReceiptReference(output_pointer, "evidence-right", identifier, *common)
            for identifier in right_ids
        )
        if pointer in spans:
            references.append(
                ReceiptReference(output_pointer, "evidence-span", spans[pointer], *common)
            )
        references.extend(
            ReceiptReference(output_pointer, "entity-mapping", identifier, *common)
            for identifier in mappings
        )
        if context.fact.entity_relationship_id:
            references.append(
                ReceiptReference(
                    output_pointer,
                    "entity-relationship",
                    context.fact.entity_relationship_id,
                    *common,
                )
            )
    return tuple(references)


def build_operational_closure(
    fixture: OperationalEvidenceFixture,
    *,
    claim_id: str,
    decision_at: datetime,
    access_view: str,
    output_pointer: str,
    source_bundles: Sequence[SnapshotBundle],
    verification_bundle: SnapshotBundle,
    contexts: Sequence[FactContext],
    value: object,
    disposition: str = "included",
    role: str = "input",
) -> OperationalClaimClosure:
    sources = _source_closures(source_bundles)
    snapshots = {row.dataset_id: row.slice_digest for row in sources}
    references: list[ReceiptReference] = []
    for context in contexts:
        references.extend(
            _item_references(
                fixture,
                context=context,
                output_pointer=output_pointer,
                snapshot_digest=snapshots[context.dataset_id],
                disposition=disposition,
                role=role,
            )
        )
    if not references:
        refuse("operational-receipt-reference-empty")
    constants = {
        "method_version": METHOD_VERSION,
        "minimum_independent_groups": E4_MIN_INDEPENDENT_GROUPS,
        "stale_days": E4_STALE_DAYS,
    }
    return OperationalClaimClosure(
        claim_id,
        RECEIPT_VERSION,
        normalize_utc(decision_at),
        access_view,
        output_pointer,
        sources,
        VerificationEnvelopeClosure(
            verification_bundle.join_receipt_id, verification_bundle.bundle_digest
        ),
        sha256(canonical_bytes(sources)),
        sha256(canonical_bytes(constants)),
        tuple(
            sorted(
                (_fact_binding(fixture, context) for context in contexts),
                key=lambda row: row.fact_id,
            )
        ),
        tuple(references),
        value,
    )


def persist_operational_receipt(conn: sqlite3.Connection, closure: OperationalClaimClosure) -> str:
    try:
        live_ceiling = CLAIM_LIVE_CEILINGS[closure.claim_id]
    except KeyError:
        refuse("operational-receipt-claim-unknown")
    receipt = make_receipt(
        claim_id=closure.claim_id,
        output_locator=closure.output_pointer,
        input_digest=sha256(canonical_bytes(closure.parameter_payload)),
        output_schema_id=OUTPUT_SCHEMA_ID,
        current_attestation="D",
        live_attestation_ceiling=live_ceiling,
        algorithm_id=RECEIPT_ALGORITHM,
        algorithm_version=closure.algorithm_version,
        parameters=closure.parameter_payload,
        value=closure.value,
        references=closure.references,
    )
    return store_receipt(conn, receipt)


def _verify_links(
    conn: sqlite3.Connection,
    references: Sequence[ReceiptReference],
    verification_bundle: SnapshotBundle,
    fact_bindings: Sequence[FactClosureBinding],
) -> None:
    snapshots = {slice_.digest for slice_ in verification_bundle.slices}
    binding_by_relationship = {
        row.entity_relationship_id: row
        for row in fact_bindings
        if row.entity_relationship_id is not None
    }
    binding_item_ids = {row.evidence_item_id for row in fact_bindings}
    fields_by_item: dict[str, set[str]] = {}
    for ref in references:
        if ref.reference_type == "evidence-item" and ref.reference_id in binding_item_ids:
            fields_by_item.setdefault(ref.reference_id, set()).add(ref.source_field)
    expected_span_bindings: set[tuple[str, str, str]] = set()
    for item_id, fields in fields_by_item.items():
        expected_span_bindings.update(
            (row["evidence_span_id"], item_id, row["json_pointer"])
            for row in conn.execute(
                "SELECT evidence_span_id,json_pointer FROM evidence_span "
                "WHERE evidence_item_id=? ORDER BY evidence_span_id",
                (item_id,),
            )
            if row["json_pointer"] in fields
        )
    actual_span_bindings: set[tuple[str, str, str]] = set()
    for ref in references:
        if ref.reference_type == "snapshot" and ref.reference_id not in snapshots:
            refuse("operational-receipt-snapshot-mismatch")
        if ref.reference_type == "evidence-span":
            row = conn.execute(
                "SELECT evidence_item_id,json_pointer FROM evidence_span WHERE evidence_span_id=?",
                (ref.reference_id,),
            ).fetchone()
            if (
                row is None
                or row["evidence_item_id"] not in binding_item_ids
                or row["json_pointer"] != ref.source_field
            ):
                refuse("operational-receipt-span-context-mismatch")
            actual_span_bindings.add(
                (ref.reference_id, row["evidence_item_id"], row["json_pointer"])
            )
        if ref.reference_type == "dataset-observation":
            row = conn.execute(
                "SELECT evidence_item_id,dataset_version_id FROM dataset_observation "
                "WHERE dataset_observation_id=?",
                (ref.reference_id,),
            ).fetchone()
            if row is None:
                refuse("operational-receipt-observation-missing")
        if ref.reference_type == "entity-relationship":
            row = conn.execute(
                "SELECT source_evidence_item_id,evidence_span_id,dataset_observation_id,"
                "dataset_version_id,relation_type,source_entity_id,target_entity_id,temporal_type,"
                "effective_at,effective_from,effective_to FROM entity_relationship "
                "WHERE entity_relationship_id=?",
                (ref.reference_id,),
            ).fetchone()
            if row is None:
                refuse("operational-receipt-relationship-missing")
            binding = binding_by_relationship.get(ref.reference_id)
            if binding is None:
                refuse("operational-receipt-relationship-context-mismatch")
            if (
                row["source_evidence_item_id"] != binding.evidence_item_id
                or row["evidence_span_id"] != binding.evidence_span_id
                or row["dataset_observation_id"] != binding.dataset_observation_id
                or row["dataset_version_id"] != binding.dataset_version_id
                or row["relation_type"] != binding.predicate
                or row["source_entity_id"] != binding.relationship_source_entity_id
                or row["target_entity_id"] != binding.relationship_target_entity_id
                or row["temporal_type"] != binding.relationship_temporal_type
                or row["effective_at"] != binding.relationship_effective_at
                or row["effective_from"] != binding.relationship_effective_from
                or row["effective_to"] != binding.relationship_effective_to
            ):
                refuse("operational-receipt-relationship-context-mismatch")
    if actual_span_bindings != expected_span_bindings:
        refuse("operational-receipt-span-context-mismatch")


def verify_operational_receipt(
    conn: sqlite3.Connection,
    *,
    receipt_id: str,
    source_bundles: tuple[SnapshotBundle, ...],
    verification_bundle: SnapshotBundle,
    closure: OperationalClaimClosure,
) -> None:
    expected_sources = _source_closures(source_bundles)
    try:
        ruled_dataset_ids = SOURCE_VIEW_DATASETS[closure.access_view]
    except KeyError:
        refuse("operational-receipt-source-view-invalid")
    if tuple(row.dataset_id for row in expected_sources) != ruled_dataset_ids:
        refuse("operational-receipt-source-order-mismatch")
    if expected_sources != closure.ordered_source_bundles:
        refuse("operational-receipt-source-bundle-mismatch")
    envelope_slices = tuple(
        sorted(
            (
                slice_.request.dataset_id,
                slice_.digest,
                slice_.receipt_id or "",
            )
            for slice_ in verification_bundle.slices
        )
    )
    source_slices = tuple(
        sorted(
            (row.dataset_id, row.slice_digest, row.slice_receipt_id) for row in expected_sources
        )
    )
    if envelope_slices != source_slices:
        refuse("operational-receipt-envelope-mismatch")
    if closure.verification_envelope != VerificationEnvelopeClosure(
        verification_bundle.join_receipt_id, verification_bundle.bundle_digest
    ):
        refuse("operational-receipt-envelope-mismatch")
    if closure.composite_union_input_digest != sha256(canonical_bytes(expected_sources)):
        refuse("operational-receipt-input-digest-mismatch")
    try:
        live_ceiling = CLAIM_LIVE_CEILINGS[closure.claim_id]
    except KeyError:
        refuse("operational-receipt-claim-unknown")
    expected = make_receipt(
        claim_id=closure.claim_id,
        output_locator=closure.output_pointer,
        input_digest=sha256(canonical_bytes(closure.parameter_payload)),
        output_schema_id=OUTPUT_SCHEMA_ID,
        current_attestation="D",
        live_attestation_ceiling=live_ceiling,
        algorithm_id=RECEIPT_ALGORITHM,
        algorithm_version=closure.algorithm_version,
        parameters=closure.parameter_payload,
        value=closure.value,
        references=closure.references,
    )
    if expected.receipt_id != receipt_id:
        refuse("operational-receipt-header-mismatch")
    persisted = conn.execute(
        "SELECT * FROM reconstruction_receipt WHERE receipt_id=?", (receipt_id,)
    ).fetchone()
    if persisted is None:
        refuse("operational-receipt-missing")
    persisted_refs = tuple(
        ReceiptReference(
            row["output_field"],
            row["reference_type"],
            _reference_id(row),
            row["disposition"],
            row["reason_code"],
            row["source_schema_id"],
            row["source_field"],
            row["role"],
        )
        for row in conn.execute(
            "SELECT * FROM receipt_reference WHERE receipt_id=? ORDER BY ordinal", (receipt_id,)
        )
    )
    if persisted_refs != expected.references:
        refuse("operational-receipt-reference-mismatch")
    _verify_links(conn, persisted_refs, verification_bundle, closure.fact_bindings)
    verify_receipt(conn, receipt_id, verification_bundle)


def receipt_parameters(conn: sqlite3.Connection, receipt_id: str) -> Mapping[str, object]:
    row = conn.execute(
        "SELECT parameters_sha256 FROM reconstruction_receipt WHERE receipt_id=?", (receipt_id,)
    ).fetchone()
    if row is None:
        refuse("operational-receipt-missing")
    return {"parameters_sha256": row[0]}
