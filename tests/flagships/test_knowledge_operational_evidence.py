from __future__ import annotations

import json
import re
import sqlite3
from collections import Counter, defaultdict
from dataclasses import asdict, replace
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from quant_allocator.evidence.checks import EvidenceRefusal
from quant_allocator.evidence.entitlements import resolve_query_right
from quant_allocator.evidence.ingest import (
    expected_partition_manifest,
    received_partition_manifest,
    reconstruct_dataset_version,
)
from quant_allocator.evidence.lineage import verify_receipt
from quant_allocator.evidence.model import canonical_bytes, machine_id, normalize_utc, sha256
from quant_allocator.evidence.projections import (
    project_entity_mappings,
    project_entity_relationships,
)
from quant_allocator.evidence.schema import SCHEMA_VERSION, schema_digest
from quant_allocator.flagships.knowledge.operational_evidence import (
    E4_OPERATIONAL_FIXTURE_DOMAIN,
    E4_OPERATIONAL_FIXTURE_ID,
    OperationalEvidenceManifest,
    _build_operational_evidence_fixture,
    build_operational_evidence_fixture,
    operational_source_bundle,
    operational_verification_bundle,
    verify_operational_fixture_receipt,
)

DATASET_IDS = (
    "dataset:e4-control-evidence",
    "dataset:e4-independent-references",
    "dataset:e4-manager-documents",
    "dataset:e4-operational-policy",
    "dataset:e4-public-registry",
)
SCHEMA_IDS = {
    "dataset:e4-public-registry": "schema:e4-public-registry-operational-v1",
    "dataset:e4-manager-documents": "schema:e4-manager-documents-operational-v1",
    "dataset:e4-control-evidence": "schema:e4-control-evidence-operational-v1",
    "dataset:e4-independent-references": "schema:e4-independent-references-operational-v1",
    "dataset:e4-operational-policy": "schema:e4-operational-policy-v1",
}
COMMON_POINTERS = {
    "manager_entity_id_pointer": "/fact/manager_entity_id",
    "domain_pointer": "/fact/domain",
    "subject_entity_id_pointer": "/fact/subject_entity_id",
    "predicate_pointer": "/fact/predicate",
    "scope_pointer": "/fact/scope",
    "typed_value_pointer": "/fact/typed_value",
    "temporal_type_pointer": "/temporal/temporal_type",
    "effective_at_pointer": "/temporal/effective_at",
    "effective_from_pointer": "/temporal/effective_from",
    "effective_to_pointer": "/temporal/effective_to",
    "freshness_at_pointer": "/fact/freshness_at",
    "source_family_pointer": "/fact/source_family",
    "independence_group_pointer": "/fact/independence_group",
    "assertion_kind_pointer": "/fact/assertion_kind",
    "incident_materiality_pointer": "/fact/incident_materiality",
}
HIDDEN_KEYS = {
    "expected_state",
    "expected_change",
    "expected_queue",
    "expected_classification",
    "hidden_truth",
    "manager_rank",
    "odd_score",
}
STALE_DAYS = {
    "organisation": 180,
    "process": 180,
    "control": 365,
    "provider": 365,
    "incident": 90,
}


def _pointer(payload: object, pointer: str) -> object:
    value = payload
    for token in pointer.lstrip("/").split("/"):
        assert isinstance(value, dict)
        value = value[token.replace("~1", "/").replace("~0", "~")]
    return value


def _schema_pointer_exists(schema: dict[str, object], pointer: str) -> None:
    node: object = schema
    for token in pointer.lstrip("/").split("/"):
        assert isinstance(node, dict)
        properties = node.get("properties")
        assert isinstance(properties, dict)
        assert token in properties
        node = properties[token]


def _publication_terms() -> tuple[str, ...]:
    path = Path(__file__).resolve().parents[2] / "tools" / ".publication_terms"
    if not path.exists():
        return ()
    return tuple(line.strip().lower() for line in path.read_text().splitlines() if line.strip())


def test_manifest_contract_schemas_rights_and_digest_are_exact() -> None:
    fixture = build_operational_evidence_fixture()
    manifest = fixture.manifest

    assert E4_OPERATIONAL_FIXTURE_ID == "e4_operational_evidence_v1"
    assert E4_OPERATIONAL_FIXTURE_DOMAIN == b"quant-allocator/e4-operational-fixture/v1\0"
    assert manifest.fixture_id == E4_OPERATIONAL_FIXTURE_ID
    assert manifest.evidence_schema_version == SCHEMA_VERSION == 1
    assert manifest.evidence_schema_digest == schema_digest(fixture.conn)
    assert manifest.e3_reviewed_tip == "349d436"
    assert manifest.current_attestation == "D"
    assert manifest.ordered_dataset_ids == DATASET_IDS
    assert re.fullmatch(r"[0-9a-f]{64}", manifest.fixture_digest)
    expected = sha256(
        E4_OPERATIONAL_FIXTURE_DOMAIN
        + canonical_bytes(asdict(replace(manifest, fixture_digest="")))
    )
    assert manifest.fixture_digest == expected

    schemas = {row.dataset_id: row for row in manifest.source_schema_manifests}
    assert tuple(schemas) == DATASET_IDS
    for dataset_id, row in schemas.items():
        assert row.payload_schema_id == SCHEMA_IDS[dataset_id]
        assert row.schema_version == 1
        assert row.field_dictionary_version == "e4-operational-v1"
        stored = fixture.conn.execute(
            "SELECT * FROM payload_schema WHERE payload_schema_id=?",
            (row.payload_schema_id,),
        ).fetchone()
        schema = json.loads(stored["schema_json"])
        assert row.schema_sha256 == stored["schema_sha256"] == sha256(canonical_bytes(schema))
        for field, pointer in COMMON_POINTERS.items():
            assert getattr(row, field) == pointer
            _schema_pointer_exists(schema, pointer)
        expected_source_time = (
            "/source_time/published_at"
            if dataset_id in {"dataset:e4-public-registry", "dataset:e4-operational-policy"}
            else "/source_time/received_at"
        )
        assert row.source_available_at_pointer == expected_source_time
        _schema_pointer_exists(schema, expected_source_time)

    rights = tuple(
        sorted(
            manifest.right_manifests,
            key=lambda row: (
                row.dataset_id,
                row.right_series_id,
                row.right_version,
                row.evidence_right_id,
            ),
        )
    )
    assert manifest.right_manifests == rights
    assert {row.status for row in rights} >= {"active", "expired", "revoked", "superseded"}
    for row in rights:
        stored = fixture.conn.execute(
            "SELECT * FROM evidence_right WHERE evidence_right_id=?",
            (row.evidence_right_id,),
        ).fetchone()
        assert stored is not None
        assert row.dataset_id == stored["dataset_id"]
        assert row.right_series_id == stored["right_series_id"]
        assert row.right_version == stored["right_version"]
        assert row.access_context == stored["access_context"]
        assert row.licence_purpose == stored["licence_purpose"]
        assert row.status == stored["status"]
        assert row.retention_policy == stored["retention_policy"]
        assert normalize_utc(row.received_at_utc) == stored["received_at_utc"]
        assert normalize_utc(row.entitlement_from) == stored["entitlement_from"]
        assert (normalize_utc(row.entitlement_to) if row.entitlement_to else None) == stored[
            "entitlement_to"
        ]
        assert row.supersedes_right_id == stored["supersedes_right_id"]


def test_every_payload_resolves_all_pointers_and_matches_stored_temporal_shape() -> None:
    fixture = build_operational_evidence_fixture()
    schemas = {row.dataset_id: row for row in fixture.manifest.source_schema_manifests}
    rows = fixture.conn.execute(
        "SELECT i.*,s.dataset_id FROM evidence_item i "
        "JOIN source_record s USING(source_record_id) ORDER BY evidence_item_id"
    ).fetchall()
    assert rows
    for row in rows:
        payload = json.loads(row["payload_json"])
        manifest = schemas[row["dataset_id"]]
        assert row["payload_schema_id"] == manifest.payload_schema_id
        assert row["field_dictionary_version"] == manifest.field_dictionary_version
        for field in COMMON_POINTERS:
            _pointer(payload, getattr(manifest, field))
        source_value = _pointer(payload, manifest.source_available_at_pointer)
        assert source_value is not None
        assert _pointer(payload, manifest.temporal_type_pointer) == row["temporal_type"]
        assert _pointer(payload, manifest.effective_at_pointer) == row["effective_at"]
        assert _pointer(payload, manifest.effective_from_pointer) == row["effective_from"]
        assert _pointer(payload, manifest.effective_to_pointer) == row["effective_to"]
        assert not HIDDEN_KEYS.intersection(payload)
        assert not HIDDEN_KEYS.intersection(payload["fact"])

        envelope = fixture.conn.execute(
            "SELECT available_at FROM evidence_envelope WHERE evidence_item_id=? "
            "ORDER BY available_at DESC LIMIT 1",
            (row["evidence_item_id"],),
        ).fetchone()
        assert envelope is not None
        source_available = datetime.fromisoformat(str(source_value).replace("Z", "+00:00"))
        derived_available = datetime.fromisoformat(envelope["available_at"].replace("Z", "+00:00"))
        assert derived_available >= source_available


def test_source_requests_bundles_receipts_and_empty_pre_delivery_are_real() -> None:
    fixture = build_operational_evidence_fixture()
    cutoffs = dict(fixture.manifest.cutoff_items)
    source_views = dict(fixture.manifest.source_view_items)
    assert tuple(cutoffs) == ("early", "latest", "middle")
    assert source_views == {
        "all-entitled": (
            "dataset:e4-public-registry",
            "dataset:e4-manager-documents",
            "dataset:e4-control-evidence",
            "dataset:e4-independent-references",
            "dataset:e4-operational-policy",
        ),
        "public-only": (
            "dataset:e4-public-registry",
            "dataset:e4-operational-policy",
        ),
    }
    for dataset_id, request in fixture.source_requests.items():
        assert dataset_id == request.dataset_id
        assert request.licence_purpose == "e4-research"
        right = fixture.conn.execute(
            "SELECT * FROM evidence_right WHERE evidence_right_id=?",
            (request.evidence_right_id,),
        ).fetchone()
        assert right["dataset_id"] == dataset_id
        assert right["status"] == "active"
        assert right["access_context"] == request.access_context

    early = datetime.fromisoformat(cutoffs["early"].replace("Z", "+00:00"))
    empty = operational_source_bundle(
        fixture,
        dataset_id="dataset:e4-control-evidence",
        decision_at=early,
        revision_mode="latest-known",
        include_unresolved=False,
    )
    assert empty.slices[0].rows == ()
    assert empty.slices[0].receipt_id is not None
    verify_receipt(fixture.conn, empty.slices[0].receipt_id, empty)
    verify_receipt(fixture.conn, empty.join_receipt_id, empty)

    latest = datetime.fromisoformat(cutoffs["latest"].replace("Z", "+00:00"))
    selected = source_views["all-entitled"]
    envelope = operational_verification_bundle(
        fixture,
        selected_dataset_ids=selected,
        decision_at=latest,
        revision_mode="latest-known",
        include_unresolved=False,
    )
    assert len(envelope.slices) == len(selected)
    assert all(slice_.rows for slice_ in envelope.slices)
    for slice_ in envelope.slices:
        assert slice_.receipt_id is not None
        verify_receipt(fixture.conn, slice_.receipt_id, envelope)
    assert (
        fixture.conn.execute(
            "SELECT count(*) FROM reconstruction_receipt WHERE receipt_id=?",
            (envelope.join_receipt_id,),
        ).fetchone()[0]
        == 1
    )
    assert (
        fixture.conn.execute(
            "SELECT count(*) FROM receipt_seal WHERE receipt_id=?",
            (envelope.join_receipt_id,),
        ).fetchone()[0]
        == 1
    )
    refs = fixture.conn.execute(
        "SELECT disposition,reference_type FROM receipt_reference WHERE receipt_id=?",
        (envelope.join_receipt_id,),
    ).fetchall()
    assert any(row["disposition"] == "excluded" for row in refs)
    assert not any(
        row["disposition"] == "included" and row["reference_type"] == "evidence-item"
        for row in refs
    )


def test_point_in_time_revisions_absence_nulls_relationships_and_refusals() -> None:
    fixture = build_operational_evidence_fixture()
    cutoffs = {
        key: datetime.fromisoformat(value.replace("Z", "+00:00"))
        for key, value in fixture.manifest.cutoff_items
    }
    dataset = "dataset:e4-manager-documents"
    early = operational_source_bundle(
        fixture,
        dataset_id=dataset,
        decision_at=cutoffs["early"],
        revision_mode="latest-known",
        include_unresolved=False,
    )
    latest = operational_source_bundle(
        fixture,
        dataset_id=dataset,
        decision_at=cutoffs["latest"],
        revision_mode="latest-known",
        include_unresolved=False,
    )
    audit = operational_source_bundle(
        fixture,
        dataset_id=dataset,
        decision_at=cutoffs["latest"],
        revision_mode="all-known-versions",
        include_unresolved=True,
    )
    assert {row["evidence_item_id"] for row in early.slices[0].rows} != {
        row["evidence_item_id"] for row in latest.slices[0].rows
    }
    assert len(audit.slices[0].rows) > len(latest.slices[0].rows)
    assert any(row["canonical_entity_id"] is None for row in audit.slices[0].rows)
    assert not any(row["canonical_entity_id"] is None for row in latest.slices[0].rows)
    not_inferable_source = fixture.conn.execute(
        "SELECT source_record_id FROM source_record WHERE source_record_key='not-inferable-member'"
    ).fetchone()[0]
    assert any(row["source_record_id"] == not_inferable_source for row in early.slices[0].rows)
    assert not any(row["source_record_id"] == not_inferable_source for row in latest.slices[0].rows)
    assert not fixture.conn.execute(
        "SELECT 1 FROM dataset_observation o JOIN evidence_item i USING(evidence_item_id) "
        "WHERE i.source_record_id=? AND o.observation_status='explicitly-removed'",
        (not_inferable_source,),
    ).fetchone()
    date_quality_payload = json.loads(
        fixture.conn.execute(
            "SELECT payload_json FROM evidence_item i JOIN source_record s USING(source_record_id) "
            "WHERE s.source_record_key='date-quality-note'"
        ).fetchone()[0]
    )
    assert {
        key: date_quality_payload["fact"][key] for key in ("predicate", "scope", "typed_value")
    } == {
        "predicate": "effective-date-source",
        "scope": "change-date-provenance",
        "typed_value": "filename-only",
    }

    modes = {
        (row["delivery_mode"], row["absence_semantics"], row["completeness_status"])
        for row in fixture.conn.execute("SELECT * FROM dataset_version")
    }
    assert ("delta", "explicit-tombstone-only", "complete") in modes
    assert ("full-snapshot", "full-snapshot-means-removed", "complete") in modes
    assert ("full-snapshot", "not-inferable", "complete") in modes
    assert any(status == "incomplete" for _, _, status in modes)
    assert (
        fixture.conn.execute(
            "SELECT count(*) FROM dataset_version WHERE embargo_until IS NOT NULL"
        ).fetchone()[0]
        >= 1
    )
    assert (
        fixture.conn.execute(
            "SELECT count(*) FROM dataset_observation WHERE observation_status='explicitly-removed'"
        ).fetchone()[0]
        >= 1
    )

    relationship_types = {
        row[0] for row in fixture.conn.execute("SELECT relation_type FROM entity_relationship")
    }
    assert relationship_types >= {
        "managed-or-advised-by",
        "employs",
        "uses-provider",
        "operates-process",
        "governed-by",
        "tested-by",
        "affected",
        "asserts-operational-fact",
    }
    assert (
        fixture.conn.execute(
            "SELECT count(*) FROM entity_relationship WHERE revision_of IS NOT NULL"
        ).fetchone()[0]
        >= 1
    )
    revised_relationship = fixture.conn.execute(
        "SELECT child.effective_to AS child_end,parent.effective_to AS parent_end "
        "FROM entity_relationship child JOIN entity_relationship parent "
        "ON parent.entity_relationship_id=child.revision_of "
        "WHERE child.relation_type='governed-by'"
    ).fetchone()
    assert revised_relationship["child_end"] is None
    assert revised_relationship["parent_end"] == "2024-09-01T00:00:00.000000Z"
    assert dict(
        fixture.conn.execute(
            "SELECT mapping_status,count(*) FROM entity_mapping GROUP BY mapping_status"
        ).fetchall()
    ) == {"ambiguous": 1, "resolved": 1, "unresolved": 2}
    assert (
        fixture.conn.execute(
            "SELECT count(*) FROM entity_mapping WHERE revision_of IS NOT NULL"
        ).fetchone()[0]
        == 1
    )
    projected_relationships: set[str] = set()
    projected_mappings: set[str] = set()
    for dataset_id in dict(fixture.manifest.source_view_items)["all-entitled"]:
        bundle = operational_source_bundle(
            fixture,
            dataset_id=dataset_id,
            decision_at=cutoffs["latest"],
            revision_mode="all-known-versions",
            include_unresolved=True,
        )
        projected_relationships.update(
            row["entity_relationship_id"]
            for row in project_entity_relationships(fixture.conn, bundle.slices[0])
        )
        projected_mappings.update(
            row["entity_mapping_id"]
            for row in project_entity_mappings(fixture.conn, bundle.slices[0])
        )
    assert projected_relationships == {
        row[0]
        for row in fixture.conn.execute("SELECT entity_relationship_id FROM entity_relationship")
    }
    assert projected_mappings == {
        row[0] for row in fixture.conn.execute("SELECT entity_mapping_id FROM entity_mapping")
    }

    request = fixture.source_requests[dataset]
    with pytest.raises(EvidenceRefusal, match="licence-purpose-mismatch"):
        operational_source_bundle(
            replace(fixture, source_requests={dataset: replace(request, licence_purpose="wrong")}),
            dataset_id=dataset,
            decision_at=cutoffs["latest"],
            revision_mode="latest-known",
            include_unresolved=False,
        )
    with pytest.raises(EvidenceRefusal, match="unsupported-operational-cutoff"):
        operational_source_bundle(
            fixture,
            dataset_id=dataset,
            decision_at=cutoffs["latest"] + timedelta(seconds=1),
            revision_mode="latest-known",
            include_unresolved=False,
        )
    with pytest.raises(EvidenceRefusal, match="operational-source-view-mismatch"):
        operational_verification_bundle(
            fixture,
            selected_dataset_ids=tuple(
                reversed(dict(fixture.manifest.source_view_items)["public-only"])
            ),
            decision_at=cutoffs["latest"],
            revision_mode="latest-known",
            include_unresolved=False,
        )


def test_fixture_is_deterministic_tamper_evident_and_public_safe() -> None:
    first = build_operational_evidence_fixture()
    second = build_operational_evidence_fixture()
    assert first.manifest == second.manifest
    assert canonical_bytes(first.manifest) == canonical_bytes(second.manifest)
    assert first.manifest.source_order_digest == sha256(canonical_bytes(DATASET_IDS))
    assert first.manifest.bundle_manifests == tuple(
        sorted(
            first.manifest.bundle_manifests,
            key=lambda row: (
                row.cutoff_key,
                row.source_view,
                row.bundle_kind,
                row.dataset_id or "",
                row.revision_mode,
                row.include_unresolved,
            ),
        )
    )

    row = first.manifest.source_schema_manifests[0]
    changed = replace(
        first.manifest,
        source_schema_manifests=(replace(row, domain_pointer="/wrong"),)
        + first.manifest.source_schema_manifests[1:],
    )
    changed_digest = sha256(
        E4_OPERATIONAL_FIXTURE_DOMAIN + canonical_bytes(asdict(replace(changed, fixture_digest="")))
    )
    assert changed_digest != first.manifest.fixture_digest
    tampered = replace(first, manifest=replace(changed, fixture_digest=changed_digest))
    latest = datetime.fromisoformat(
        dict(first.manifest.cutoff_items)["latest"].replace("Z", "+00:00")
    )
    with pytest.raises(EvidenceRefusal, match="operational-source-schema-mismatch"):
        operational_source_bundle(
            tampered,
            dataset_id=first.manifest.ordered_dataset_ids[0],
            decision_at=latest,
            revision_mode="latest-known",
            include_unresolved=False,
        )

    all_payload = canonical_bytes(second.manifest).decode().lower()
    all_payload += " ".join(
        row[0].lower() for row in second.conn.execute("SELECT payload_json FROM evidence_item")
    )
    assert not any(term in all_payload for term in _publication_terms())
    assert not any(key in all_payload for key in HIDDEN_KEYS)


def test_manifest_type_rejects_duplicate_or_unsorted_contract() -> None:
    fixture = build_operational_evidence_fixture()
    with pytest.raises(ValueError, match="ordered-dataset-ids"):
        OperationalEvidenceManifest(
            **{
                **asdict(fixture.manifest),
                "ordered_dataset_ids": tuple(reversed(fixture.manifest.ordered_dataset_ids)),
            }
        )


def test_all_authored_ids_and_foreign_keys_recompute() -> None:
    fixture = build_operational_evidence_fixture()
    assert fixture.conn.execute("PRAGMA foreign_key_check").fetchall() == []
    contracts = {
        "right": (
            "evidence_right",
            "evidence_right_id",
            (
                "right_series_id",
                "right_version",
                "dataset_id",
                "access_context",
                "licence_purpose",
                "status",
                "retention_policy",
                "received_at_utc",
                "entitlement_from",
                "entitlement_to",
                "supersedes_right_id",
            ),
        ),
        "source-record": (
            "source_record",
            "source_record_id",
            ("dataset_id", "source_system", "source_record_key"),
        ),
        "evidence": ("evidence_item", "evidence_item_id", ("source_record_id", "version")),
        "span": (
            "evidence_span",
            "evidence_span_id",
            ("evidence_item_id", "json_pointer", "start_char", "end_char", "span_sha256"),
        ),
        "dataset-version": (
            "dataset_version",
            "dataset_version_id",
            (
                "dataset_id",
                "version_label",
                "acquisition_right_id",
                "published_at",
                "first_observed_at_utc",
                "received_at_utc",
                "embargo_until",
                "content_sha256",
                "delivery_mode",
                "absence_semantics",
                "completeness_status",
                "expected_partition_manifest_sha256",
                "received_partition_manifest_sha256",
                "expected_partition_count",
                "received_partition_count",
                "predecessor_dataset_version_id",
                "base_dataset_version_id",
                "reconstruction_manifest_sha256",
                "reconstruction_row_count",
            ),
        ),
        "dataset-partition": (
            "dataset_delivery_partition",
            "dataset_delivery_partition_id",
            (
                "dataset_version_id",
                "partition_key",
                "partition_status",
                "manifest_evidence_item_id",
                "manifest_evidence_span_id",
                "received_content_sha256",
                "expected_record_count",
                "received_record_count",
            ),
        ),
        "dataset-observation": (
            "dataset_observation",
            "dataset_observation_id",
            ("dataset_version_id", "evidence_item_id", "observation_status"),
        ),
        "dataset-observation-partition": (
            "dataset_observation_partition_link",
            "dataset_observation_partition_link_id",
            ("dataset_observation_id", "dataset_delivery_partition_id"),
        ),
        "entity-relation": (
            "entity_relationship",
            "entity_relationship_id",
            (
                "source_evidence_item_id",
                "relation_type",
                "source_entity_id",
                "target_entity_id",
                "temporal_type",
                "effective_at",
                "effective_from",
                "effective_to",
                "version",
            ),
        ),
        "mapping": (
            "entity_mapping",
            "entity_mapping_id",
            (
                "source_evidence_item_id",
                "source_key",
                "source_label",
                "taxonomy_version",
                "version",
                "candidate_entity_ids_json",
            ),
        ),
    }
    for namespace, (table, identifier, fields) in contracts.items():
        for row in fixture.conn.execute(f"SELECT * FROM {table}"):
            assert row[identifier] == machine_id(namespace, {field: row[field] for field in fields})


def test_every_typed_receipt_has_exact_field_lineage_and_null_incident_evidence() -> None:
    fixture = build_operational_evidence_fixture()
    receipts = fixture.conn.execute(
        "SELECT receipt_id FROM reconstruction_receipt "
        "WHERE claim_id='claim:e4-operational-fixture-field-closure' ORDER BY receipt_id"
    ).fetchall()
    item_count = fixture.conn.execute("SELECT count(*) FROM evidence_item").fetchone()[0]
    assert len(receipts) == item_count

    schemas = {row.payload_schema_id: row for row in fixture.manifest.source_schema_manifests}
    expected_pointers = {
        row.payload_schema_id: {getattr(row, field) for field in COMMON_POINTERS}
        | {row.source_available_at_pointer}
        for row in schemas.values()
    }
    for receipt in receipts:
        receipt_id = receipt[0]
        verify_operational_fixture_receipt(fixture, receipt_id=receipt_id)
        refs = fixture.conn.execute(
            "SELECT * FROM receipt_reference WHERE receipt_id=? ORDER BY ordinal",
            (receipt_id,),
        ).fetchall()
        assert refs
        schema_ids = {row["source_schema_id"] for row in refs}
        assert len(schema_ids) == 1
        schema_id = next(iter(schema_ids))
        assert {row["source_field"] for row in refs} == expected_pointers[schema_id]
        assert {row["role"] for row in refs} == {"input"}
        assert {row["disposition"] for row in refs} == {"included"}
        assert {row["reference_type"] for row in refs} >= {
            "dataset-observation",
            "dataset-version",
            "evidence-item",
            "evidence-right",
            "snapshot",
            "source-record",
        }

    incident = fixture.conn.execute(
        "SELECT i.* FROM evidence_item i JOIN source_record s USING(source_record_id) "
        "WHERE s.source_record_key='incident-materiality-missing'"
    ).fetchone()
    assert incident is not None
    payload = json.loads(incident["payload_json"])
    assert {
        key: payload["fact"][key]
        for key in ("domain", "assertion_kind", "scope", "incident_materiality")
    } == {
        "domain": "incident",
        "assertion_kind": "incident-notice",
        "scope": "materiality-unreported",
        "incident_materiality": None,
    }
    receipt_id = fixture.conn.execute(
        "SELECT receipt_id FROM receipt_reference WHERE reference_type='evidence-item' "
        "AND evidence_item_id=? AND source_field='/fact/incident_materiality'",
        (incident["evidence_item_id"],),
    ).fetchone()[0]
    materiality_refs = fixture.conn.execute(
        "SELECT reference_type,evidence_span_id FROM receipt_reference "
        "WHERE receipt_id=? AND source_field='/fact/incident_materiality' ORDER BY ordinal",
        (receipt_id,),
    ).fetchall()
    assert {row["reference_type"] for row in materiality_refs} >= {
        "dataset-observation",
        "dataset-version",
        "evidence-item",
        "evidence-right",
        "snapshot",
        "source-record",
    }
    assert not any(row["reference_type"] == "evidence-span" for row in materiality_refs)


def test_reversed_insertion_order_preserves_all_persisted_bundle_and_receipt_rows() -> None:
    canonical = _build_operational_evidence_fixture(reverse_insertion=False)
    reversed_input = _build_operational_evidence_fixture(reverse_insertion=True)
    assert canonical.manifest == reversed_input.manifest
    assert canonical_bytes(canonical.manifest) == canonical_bytes(reversed_input.manifest)

    tables = {
        "snapshot_manifest": "snapshot_digest",
        "snapshot_bundle_manifest": "bundle_digest",
        "reconstruction_receipt": "receipt_id",
        "receipt_reference": "receipt_id,ordinal",
        "receipt_seal": "receipt_id",
    }
    for table, order in tables.items():
        left = [
            tuple(row) for row in canonical.conn.execute(f"SELECT * FROM {table} ORDER BY {order}")
        ]
        right = [
            tuple(row)
            for row in reversed_input.conn.execute(f"SELECT * FROM {table} ORDER BY {order}")
        ]
        assert left == right, table

    for cutoff in dict(canonical.manifest.cutoff_items).values():
        decision_at = datetime.fromisoformat(cutoff.replace("Z", "+00:00"))
        for dataset_id in DATASET_IDS:
            for revision_mode in ("all-known-versions", "latest-known"):
                for include_unresolved in (False, True):
                    left = operational_source_bundle(
                        canonical,
                        dataset_id=dataset_id,
                        decision_at=decision_at,
                        revision_mode=revision_mode,
                        include_unresolved=include_unresolved,
                    )
                    right = operational_source_bundle(
                        reversed_input,
                        dataset_id=dataset_id,
                        decision_at=decision_at,
                        revision_mode=revision_mode,
                        include_unresolved=include_unresolved,
                    )
                    assert canonical_bytes(left) == canonical_bytes(right)


def test_all_rows_availability_partitions_and_version_reconstruction_are_exact() -> None:
    fixture = build_operational_evidence_fixture()
    for table, expected_ids in fixture.manifest.row_ids_by_table:
        identifier = {
            "canonical_entity": "entity_id",
            "dataset": "dataset_id",
            "dataset_delivery_partition": "dataset_delivery_partition_id",
            "dataset_observation": "dataset_observation_id",
            "dataset_observation_partition_link": "dataset_observation_partition_link_id",
            "dataset_version": "dataset_version_id",
            "entity_mapping": "entity_mapping_id",
            "entity_relationship": "entity_relationship_id",
            "evidence_item": "evidence_item_id",
            "evidence_right": "evidence_right_id",
            "evidence_span": "evidence_span_id",
            "payload_schema": "payload_schema_id",
            "reconstruction_receipt": "receipt_id",
            "source_record": "source_record_id",
        }[table]
        actual = tuple(
            row[0]
            for row in fixture.conn.execute(
                f"SELECT {identifier} FROM {table} ORDER BY {identifier}"
            )
        )
        assert actual == expected_ids

    envelopes = fixture.conn.execute(
        "SELECT e.available_at,e.availability_policy,e.published_at AS item_published,"
        "e.first_observed_at_utc AS item_observed,e.received_at_utc AS item_received,"
        "e.embargo_until AS item_embargo,v.published_at AS version_published,"
        "v.first_observed_at_utc AS version_observed,v.received_at_utc AS version_received,"
        "v.embargo_until AS version_embargo,ir.received_at_utc AS item_right_received,"
        "ir.entitlement_from AS item_entitlement,vr.received_at_utc AS version_right_received,"
        "vr.entitlement_from AS version_entitlement FROM evidence_envelope e "
        "JOIN dataset_version v USING(dataset_version_id) "
        "JOIN evidence_right ir ON ir.evidence_right_id=e.acquisition_right_id "
        "JOIN evidence_right vr ON vr.evidence_right_id=v.acquisition_right_id"
    ).fetchall()
    assert envelopes
    floor = "0001-01-01T00:00:00.000000Z"
    for row in envelopes:
        if row["availability_policy"] == "public-publication":
            item_available = row["item_published"] or row["item_observed"]
            version_available = row["version_published"] or row["version_observed"]
        else:
            item_available = row["item_received"]
            version_available = row["version_received"]
        expected = max(
            item_available,
            row["item_embargo"] or floor,
            version_available,
            row["version_embargo"] or floor,
            row["item_right_received"],
            row["item_entitlement"],
            row["version_right_received"],
            row["version_entitlement"],
        )
        assert row["available_at"] == expected

    for version in fixture.conn.execute(
        "SELECT * FROM dataset_version ORDER BY dataset_version_id"
    ):
        partitions = fixture.conn.execute(
            "SELECT * FROM dataset_delivery_partition WHERE dataset_version_id=? "
            "ORDER BY partition_key",
            (version["dataset_version_id"],),
        ).fetchall()
        assert (
            expected_partition_manifest(partitions) == version["expected_partition_manifest_sha256"]
        )
        assert (
            received_partition_manifest(partitions) == version["received_partition_manifest_sha256"]
        )
        if version["completeness_status"] == "complete":
            reconstructed = reconstruct_dataset_version(fixture.conn, version["dataset_version_id"])
            assert (
                reconstructed.reconstruction_manifest_sha256
                == version["reconstruction_manifest_sha256"]
            )
            assert reconstructed.reconstruction_row_count == version["reconstruction_row_count"]
        else:
            with pytest.raises(EvidenceRefusal, match="incomplete-dataset-version"):
                reconstruct_dataset_version(fixture.conn, version["dataset_version_id"])


def test_right_boundaries_and_persisted_closure_rows_refuse_mutation() -> None:
    fixture = build_operational_evidence_fixture()
    for request in fixture.source_requests.values():
        right = fixture.conn.execute(
            "SELECT * FROM evidence_right WHERE evidence_right_id=?",
            (request.evidence_right_id,),
        ).fetchone()
        from_time = datetime.fromisoformat(right["entitlement_from"].replace("Z", "+00:00"))
        resolve_query_right(
            fixture.conn,
            evidence_right_id=request.evidence_right_id,
            decision_at=from_time,
            access_context=request.access_context,
            licence_purpose=request.licence_purpose,
        )
        if right["entitlement_to"] is not None:
            to_time = datetime.fromisoformat(right["entitlement_to"].replace("Z", "+00:00"))
            with pytest.raises(EvidenceRefusal, match="entitlement-not-active"):
                resolve_query_right(
                    fixture.conn,
                    evidence_right_id=request.evidence_right_id,
                    decision_at=to_time,
                    access_context=request.access_context,
                    licence_purpose=request.licence_purpose,
                )

    for right in fixture.conn.execute(
        "SELECT * FROM evidence_right WHERE status!='active' ORDER BY evidence_right_id"
    ):
        received_at = datetime.fromisoformat(right["received_at_utc"].replace("Z", "+00:00"))
        with pytest.raises(EvidenceRefusal, match="right-not-known"):
            resolve_query_right(
                fixture.conn,
                evidence_right_id=right["evidence_right_id"],
                decision_at=received_at - timedelta(microseconds=1),
                access_context=right["access_context"],
                licence_purpose=right["licence_purpose"],
            )
        inside_entitlement = received_at + timedelta(microseconds=1)
        expected_status_code = (
            "right-revoked" if right["status"] == "revoked" else "right-superseded"
        )
        with pytest.raises(EvidenceRefusal, match=expected_status_code):
            resolve_query_right(
                fixture.conn,
                evidence_right_id=right["evidence_right_id"],
                decision_at=inside_entitlement,
                access_context=right["access_context"],
                licence_purpose=right["licence_purpose"],
            )
        entitlement_to = datetime.fromisoformat(right["entitlement_to"].replace("Z", "+00:00"))
        with pytest.raises(EvidenceRefusal, match="entitlement-not-active"):
            resolve_query_right(
                fixture.conn,
                evidence_right_id=right["evidence_right_id"],
                decision_at=entitlement_to,
                access_context=right["access_context"],
                licence_purpose=right["licence_purpose"],
            )

    protected_tables = (
        "payload_schema",
        "evidence_right",
        "dataset_version",
        "dataset_delivery_partition",
        "dataset_observation",
        "entity_mapping",
        "entity_relationship",
        "snapshot_manifest",
        "snapshot_bundle_manifest",
        "reconstruction_receipt",
        "receipt_reference",
        "receipt_seal",
    )
    for table in protected_tables:
        with pytest.raises(sqlite3.IntegrityError, match="immutable-record"):
            fixture.conn.execute(
                f"UPDATE {table} SET rowid=rowid WHERE rowid=(SELECT min(rowid) FROM {table})"
            )
        with pytest.raises(sqlite3.IntegrityError, match="immutable-record"):
            fixture.conn.execute(
                f"DELETE FROM {table} WHERE rowid=(SELECT min(rowid) FROM {table})"
            )


def _analytic_rows(fixture, *, cutoff_name: str, source_view: str):
    decision_at = datetime.fromisoformat(
        dict(fixture.manifest.cutoff_items)[cutoff_name].replace("Z", "+00:00")
    )
    rows = []
    for dataset_id in dict(fixture.manifest.source_view_items)[source_view]:
        bundle = operational_source_bundle(
            fixture,
            dataset_id=dataset_id,
            decision_at=decision_at,
            revision_mode="latest-known",
            include_unresolved=False,
        )
        rows.extend(bundle.slices[0].rows)
    return decision_at, tuple(rows)


def _latest_analytic_rows(fixture):
    return _analytic_rows(fixture, cutoff_name="latest", source_view="all-entitled")


def _operational_key(row) -> tuple[str, str, str, str, str]:
    fact = row["payload"]["fact"]
    return (
        fact["manager_entity_id"],
        fact["domain"],
        fact["subject_entity_id"],
        fact["predicate"],
        fact["scope"],
    )


def _eligible_independence_groups(key, facts) -> set[str]:
    groups = {row["independence_group"] for row in facts}
    is_provider_appointment = key[1] == "provider" and key[3] == "uses-provider"
    if not is_provider_appointment:
        groups.discard("provider-direct")
    return groups


def _facts_are_corroborated(key, facts) -> bool:
    if len(_eligible_independence_groups(key, facts)) < 2:
        return False
    assertion_kinds = {row["assertion_kind"] for row in facts}
    if "control-effectiveness-assertion" in assertion_kinds and not any(
        row["source_family"] == "control-test" for row in facts
    ):
        return False
    is_incident_closure = key[1] == "incident" and any(
        str(row["typed_value"]).startswith("closed") for row in facts
    )
    if is_incident_closure and not assertion_kinds.intersection(
        {"remediation-assertion", "closure-assertion"}
    ):
        return False
    return True


def _held_gate_summary(fixture):
    decision_at, rows = _latest_analytic_rows(fixture)
    state_rows = tuple(
        row for row in rows if row["payload"]["fact"]["assertion_kind"] != "method-boundary-policy"
    )
    grouped = defaultdict(list)
    for row in state_rows:
        grouped[_operational_key(row)].append(row)

    states = {}
    for key, values in grouped.items():
        facts = [row["payload"]["fact"] for row in values]
        if len({row["typed_value"] for row in facts}) > 1:
            states[key] = "conflicted"
            continue
        freshest = max(
            datetime.fromisoformat(row["freshness_at"].replace("Z", "+00:00")) for row in facts
        )
        if (decision_at - freshest).days > STALE_DAYS[key[1]]:
            states[key] = "stale"
        elif _facts_are_corroborated(key, facts):
            states[key] = "corroborated"
        else:
            states[key] = "asserted"

    audit_by_source = defaultdict(set)
    removed_keys = set()
    for dataset_id in dict(fixture.manifest.source_view_items)["all-entitled"]:
        bundle = operational_source_bundle(
            fixture,
            dataset_id=dataset_id,
            decision_at=decision_at,
            revision_mode="all-known-versions",
            include_unresolved=True,
        )
        for row in bundle.slices[0].rows:
            if row["canonical_entity_id"] is None:
                continue
            audit_by_source[row["source_record_id"]].add(row["evidence_item_id"])
            if row["observation_status"] == "explicitly-removed":
                removed_keys.add(_operational_key(row))
    changed_sources = {source for source, items in audit_by_source.items() if len(items) > 1}
    changed_keys = removed_keys | {
        _operational_key(row) for row in state_rows if row["source_record_id"] in changed_sources
    }
    changed_keys.discard(
        next(
            (
                key
                for key in states
                if key[3:] == ("effective-date-source", "change-date-provenance")
            ),
            None,
        )
    )
    queue_by_key = {}
    for key, state in states.items():
        facts = [row["payload"]["fact"] for row in grouped[key]]
        open_incident = key[1] == "incident" and any(
            str(row["typed_value"]).startswith("open") for row in facts
        )
        incident_materialities = {row["incident_materiality"] or "unknown" for row in facts}
        incident_requires_clarification = open_incident and bool(
            incident_materialities.intersection({"critical", "material", "unknown"})
        )
        if state == "conflicted" or incident_requires_clarification:
            queue_by_key[key] = "immediate-clarification"
        elif key in changed_keys:
            queue_by_key[key] = "scheduled-reunderwrite"
        elif state == "stale":
            queue_by_key[key] = "evidence-refresh"
        else:
            queue_by_key[key] = "no-action-from-e4"
    return rows, grouped, states, queue_by_key


def test_latest_held_gate_has_16_facts_10_keys_and_exact_state_queue_counts() -> None:
    fixture = build_operational_evidence_fixture()
    rows, grouped, states_by_key, queue_by_key = _held_gate_summary(fixture)
    assert len(rows) == 16
    assert len(grouped) == 10
    assert Counter(states_by_key.values()) == {
        "corroborated": 1,
        "asserted": 3,
        "conflicted": 3,
        "stale": 3,
    }
    assert Counter(queue_by_key.values()) == {
        "immediate-clarification": 4,
        "scheduled-reunderwrite": 4,
        "evidence-refresh": 2,
    }


def test_three_conflicts_share_complete_keys_and_only_three_keys_are_stale() -> None:
    fixture = build_operational_evidence_fixture()
    _, grouped, states_by_key, _ = _held_gate_summary(fixture)
    conflict_keys = {
        key
        for key, rows in grouped.items()
        if len({row["payload"]["fact"]["typed_value"] for row in rows}) > 1
    }
    assert len(conflict_keys) == 3
    assert all(len({row["source_record_id"] for row in grouped[key]}) >= 2 for key in conflict_keys)
    assert Counter(states_by_key.values())["stale"] == 3


def test_provider_subject_is_stable_while_values_and_relationship_endpoints_differ() -> None:
    fixture = build_operational_evidence_fixture()
    expected_values = {
        ("early", "public-only"): {"provider:e4-admin-a"},
        ("early", "all-entitled"): {"provider:e4-admin-a"},
        ("middle", "public-only"): {"provider:e4-admin-b"},
        ("middle", "all-entitled"): {"provider:e4-admin-b", "provider:e4-admin-c"},
        ("latest", "public-only"): {"provider:e4-admin-b"},
        ("latest", "all-entitled"): {"provider:e4-admin-b", "provider:e4-admin-c"},
    }
    for state_key, expected in expected_values.items():
        _, rows = _analytic_rows(
            fixture,
            cutoff_name=state_key[0],
            source_view=state_key[1],
        )
        provider_rows = [
            row
            for row in rows
            if row["payload"]["fact"]["domain"] == "provider"
            and row["payload"]["fact"]["scope"] == "fund-administration"
        ]
        assert provider_rows
        assert {row["payload"]["fact"]["subject_entity_id"] for row in provider_rows} == {
            "manager:e4-northbridge"
        }
        assert {row["payload"]["fact"]["typed_value"] for row in provider_rows} == expected
        for row in provider_rows:
            relationships = fixture.conn.execute(
                "SELECT r.relation_type,r.source_entity_id,r.target_entity_id,"
                "r.dataset_version_id,r.dataset_observation_id,s.json_pointer "
                "FROM entity_relationship r JOIN evidence_span s USING(evidence_span_id) "
                "WHERE r.source_evidence_item_id=? AND r.dataset_version_id=? "
                "AND r.dataset_observation_id=? AND r.relation_type='uses-provider' "
                "AND s.evidence_item_id=r.source_evidence_item_id "
                "AND s.json_pointer='/fact/typed_value'",
                (
                    row["evidence_item_id"],
                    row["dataset_version_id"],
                    row["dataset_observation_id"],
                ),
            ).fetchall()
            assert len(relationships) == 1
            assert (
                relationships[0]["source_entity_id"] == row["payload"]["fact"]["subject_entity_id"]
            )
            assert relationships[0]["source_entity_id"] in {
                "manager:e4-northbridge",
                "adviser:e4-northbridge",
            }
            assert relationships[0]["target_entity_id"] == row["payload"]["fact"]["typed_value"]

    for target_entity_id, expected_versions in (
        ("provider:e4-admin-b", [1, 2]),
        ("provider:e4-admin-c", [1, 2, 3]),
    ):
        chain = fixture.conn.execute(
            "SELECT entity_relationship_id,version,revision_of FROM entity_relationship "
            "WHERE relation_type='uses-provider' AND target_entity_id=? ORDER BY version",
            (target_entity_id,),
        ).fetchall()
        assert [row["version"] for row in chain] == expected_versions
        assert chain[0]["revision_of"] is None
        assert all(
            child["revision_of"] == parent["entity_relationship_id"]
            for parent, child in zip(chain, chain[1:])
        )


def test_unversioned_provider_confirmation_does_not_corroborate_process_change() -> None:
    fixture = build_operational_evidence_fixture()
    _, rows = _latest_analytic_rows(fixture)
    provider_rows = [
        row for row in rows if row["payload"]["fact"]["source_family"] == "provider-confirmation"
    ]
    assert len(provider_rows) == 1
    provider_row = provider_rows[0]
    provider_fact = provider_row["payload"]["fact"]
    assert provider_fact["assertion_kind"] == "current-state-assertion"
    assert (
        fixture.conn.execute(
            "SELECT count(*) FROM evidence_item WHERE source_record_id=?",
            (provider_row["source_record_id"],),
        ).fetchone()[0]
        == 1
    )

    process_rows = [row for row in rows if _operational_key(row) == _operational_key(provider_row)]
    assert len(process_rows) == 2
    manager_row = next(
        row for row in process_rows if row["payload"]["fact"]["source_family"] == "manager-document"
    )
    manager_fact = manager_row["payload"]["fact"]
    assert manager_fact["assertion_kind"] == "change-assertion"
    assert manager_fact["typed_value"] == provider_fact["typed_value"] == "weekly-review"
    assert manager_fact["independence_group"] != provider_fact["independence_group"]
    _, _, states_by_key, _ = _held_gate_summary(fixture)
    assert states_by_key[_operational_key(provider_row)] == "asserted"
    assert (
        fixture.conn.execute(
            "SELECT count(*) FROM evidence_item WHERE source_record_id=?",
            (manager_row["source_record_id"],),
        ).fetchone()[0]
        == 2
    )


def test_null_incident_materiality_is_unknown_and_immediate_before_staleness() -> None:
    fixture = build_operational_evidence_fixture()
    decision_at, rows = _latest_analytic_rows(fixture)
    incident = next(
        row for row in rows if row["payload"]["fact"]["scope"] == "materiality-unreported"
    )
    fact = incident["payload"]["fact"]
    assert fact["incident_materiality"] is None
    assert (fact["incident_materiality"] or "unknown") == "unknown"
    freshness_at = datetime.fromisoformat(fact["freshness_at"].replace("Z", "+00:00"))
    assert (decision_at - freshness_at).days > STALE_DAYS["incident"]

    _, _, states_by_key, queue_by_key = _held_gate_summary(fixture)
    key = _operational_key(incident)
    assert states_by_key[key] == "stale"
    assert queue_by_key[key] == "immediate-clarification"
