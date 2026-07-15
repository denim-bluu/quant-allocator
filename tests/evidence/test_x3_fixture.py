from __future__ import annotations

import json
import sqlite3
from dataclasses import fields, replace
from datetime import UTC, datetime
from types import MappingProxyType

import pytest
import quant_allocator.evidence.fixtures.x3 as x3_fixture
from quant_allocator.evidence.checks import EvidenceRefusal
from quant_allocator.evidence.fixtures.x3 import (
    X3_AUTHORED_CLOSURE_CONTRACT_VERSION,
    X3_AUTHORED_CLOSURE_SHA256,
    X3_AUTHORED_MANIFEST_SHA256,
    X3_AUTHORED_SCHEMA_SHA256,
    X3_CUTOFFS,
    X3_FIXTURE_ID,
    X3_SCOPE_PRESETS,
    X3_SOURCE_VIEWS,
    build_x3_fixture,
    verify_x3_manifest,
    x3_authored_closure_digest,
    x3_manifest_digest,
    x3_manifest_payload,
)
from quant_allocator.evidence.lineage import make_receipt, store_receipt
from quant_allocator.evidence.model import (
    DatasetSliceRequest,
    ReceiptReference,
    canonical_bytes,
    machine_id,
    sha256,
)
from quant_allocator.evidence.projections import (
    evaluate_funnel_cohort,
    project_entity_mappings,
    project_entity_relationships,
    project_funnel_cohorts,
    project_funnel_events,
    project_funnel_opportunities,
    project_funnel_schemas,
    project_target_grids,
    project_universe_memberships,
)
from quant_allocator.evidence.schema import connect, initialize
from quant_allocator.evidence.snapshot import as_known_slice


def _built():
    conn = connect()
    initialize(conn)
    manifest = build_x3_fixture(conn)
    return conn, manifest


def _count(conn, table: str, where: str = "1=1") -> int:
    return int(conn.execute(f"SELECT count(*) FROM {table} WHERE {where}").fetchone()[0])


def _insert_row(conn, table: str, row: dict[str, object]) -> None:
    columns = tuple(row)
    conn.execute(
        f"INSERT INTO {table} ({','.join(columns)}) VALUES "
        f"({','.join('?' for _ in columns)})",
        tuple(row[column] for column in columns),
    )


def _add_downstream_projections(conn) -> tuple[str, str]:
    template_relationship = conn.execute(
        "SELECT * FROM entity_relationship ORDER BY entity_relationship_id LIMIT 1"
    ).fetchone()
    assert template_relationship is not None
    dataset_id = "dataset:downstream-research"
    dataset = dict(
        conn.execute(
            "SELECT d.* FROM dataset d JOIN source_record s USING(dataset_id) "
            "JOIN evidence_item i USING(source_record_id) WHERE i.evidence_item_id=?",
            (template_relationship["source_evidence_item_id"],),
        ).fetchone()
    )
    dataset.update(dataset_id=dataset_id, label="Downstream research")
    _insert_row(conn, "dataset", dataset)

    right = dict(
        conn.execute(
            "SELECT er.* FROM evidence_right er JOIN evidence_item i "
            "ON i.acquisition_right_id=er.evidence_right_id WHERE i.evidence_item_id=?",
            (template_relationship["source_evidence_item_id"],),
        ).fetchone()
    )
    right.update(
        right_series_id="right-series:downstream-research",
        right_version=1,
        dataset_id=dataset_id,
        supersedes_right_id=None,
    )
    right["evidence_right_id"] = machine_id(
        "right", {key: value for key, value in right.items() if key != "evidence_right_id"}
    )
    _insert_row(conn, "evidence_right", right)

    source = dict(
        conn.execute(
            "SELECT s.* FROM source_record s JOIN evidence_item i USING(source_record_id) "
            "WHERE i.evidence_item_id=?",
            (template_relationship["source_evidence_item_id"],),
        ).fetchone()
    )
    source.update(dataset_id=dataset_id, source_record_key="downstream-x3-link")
    source["source_record_id"] = machine_id(
        "source-record",
        {
            "dataset_id": source["dataset_id"],
            "source_system": source["source_system"],
            "source_record_key": source["source_record_key"],
        },
    )
    _insert_row(conn, "source_record", source)

    item = dict(
        conn.execute(
            "SELECT * FROM evidence_item WHERE evidence_item_id=?",
            (template_relationship["source_evidence_item_id"],),
        ).fetchone()
    )
    item.update(
        acquisition_right_id=right["evidence_right_id"],
        source_record_id=source["source_record_id"],
        version=1,
        revision_of=None,
    )
    item["evidence_item_id"] = machine_id(
        "evidence",
        {"source_record_id": item["source_record_id"], "version": item["version"]},
    )
    _insert_row(conn, "evidence_item", item)

    span = dict(
        conn.execute(
            "SELECT * FROM evidence_span WHERE evidence_span_id=?",
            (template_relationship["evidence_span_id"],),
        ).fetchone()
    )
    span["evidence_item_id"] = item["evidence_item_id"]
    span["evidence_span_id"] = machine_id(
        "span", {key: value for key, value in span.items() if key != "evidence_span_id"}
    )
    _insert_row(conn, "evidence_span", span)

    version = dict(
        conn.execute(
            "SELECT * FROM dataset_version WHERE dataset_version_id=?",
            (template_relationship["dataset_version_id"],),
        ).fetchone()
    )
    version.update(
        dataset_id=dataset_id,
        version_label="v1",
        acquisition_right_id=right["evidence_right_id"],
        predecessor_dataset_version_id=None,
        base_dataset_version_id=None,
    )
    version["dataset_version_id"] = machine_id(
        "dataset-version",
        {key: value for key, value in version.items() if key != "dataset_version_id"},
    )
    _insert_row(conn, "dataset_version", version)

    observation = dict(
        conn.execute(
            "SELECT * FROM dataset_observation WHERE dataset_observation_id=?",
            (template_relationship["dataset_observation_id"],),
        ).fetchone()
    )
    observation.update(
        dataset_version_id=version["dataset_version_id"],
        evidence_item_id=item["evidence_item_id"],
        observation_status="present",
        disappearance_reason=None,
    )
    observation["dataset_observation_id"] = machine_id(
        "dataset-observation",
        {
            "dataset_version_id": observation["dataset_version_id"],
            "evidence_item_id": observation["evidence_item_id"],
            "observation_status": observation["observation_status"],
        },
    )
    _insert_row(conn, "dataset_observation", observation)

    provenance = (
        item["evidence_item_id"],
        span["evidence_span_id"],
        version["dataset_version_id"],
        observation["dataset_observation_id"],
    )
    relation_type = "downstream_predecessor"
    source_entity_id = "manager:x3-00"
    target_entity_id = "strategy:x3-00"
    identity = {
        "source_evidence_item_id": item["evidence_item_id"],
        "relation_type": relation_type,
        "source_entity_id": source_entity_id,
        "target_entity_id": target_entity_id,
        "temporal_type": "interval",
        "effective_at": None,
        "effective_from": "2024-01-01T00:00:00.000000Z",
        "effective_to": None,
        "version": 1,
    }
    relationship_id = machine_id("entity-relation", identity)
    conn.execute(
        "INSERT INTO entity_relationship VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            relationship_id,
            *provenance,
            relation_type,
            source_entity_id,
            target_entity_id,
            "interval",
            None,
            "2024-01-01T00:00:00.000000Z",
            None,
            1,
            None,
        ),
    )

    mapping = dict(
        conn.execute("SELECT * FROM entity_mapping ORDER BY entity_mapping_id LIMIT 1").fetchone()
    )
    mapping.update(
        source_evidence_item_id=item["evidence_item_id"],
        evidence_span_id=span["evidence_span_id"],
        dataset_version_id=version["dataset_version_id"],
        dataset_observation_id=observation["dataset_observation_id"],
        source_key="downstream-source-x3-00",
        source_label="Downstream X3 strategy reference",
        source_entity_type="strategy",
        canonical_entity_id="strategy:x3-00",
        mapping_status="resolved",
        resolution_rule="authored-exact",
        candidate_entity_ids_json="[]",
        version=1,
        revision_of=None,
    )
    mapping["entity_mapping_id"] = machine_id(
        "mapping",
        {
            "source_evidence_item_id": mapping["source_evidence_item_id"],
            "source_key": mapping["source_key"],
            "source_label": mapping["source_label"],
            "taxonomy_version": mapping["taxonomy_version"],
            "version": mapping["version"],
            "candidate_entity_ids_json": mapping["candidate_entity_ids_json"],
        },
    )
    _insert_row(conn, "entity_mapping", mapping)
    conn.commit()
    return relationship_id, mapping["entity_mapping_id"]


def _add_x3_sourced_relationship(conn) -> str:
    provenance = conn.execute(
        "SELECT source_evidence_item_id,evidence_span_id,dataset_version_id,"
        "dataset_observation_id FROM entity_relationship "
        "ORDER BY entity_relationship_id LIMIT 1"
    ).fetchone()
    identity = {
        "source_evidence_item_id": provenance["source_evidence_item_id"],
        "relation_type": "x3_extra_relationship",
        "source_entity_id": "manager:x3-00",
        "target_entity_id": "strategy:x3-00",
        "temporal_type": "interval",
        "effective_at": None,
        "effective_from": "2024-01-01T00:00:00.000000Z",
        "effective_to": None,
        "version": 1,
    }
    relationship_id = machine_id("entity-relation", identity)
    conn.execute(
        "INSERT INTO entity_relationship VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            relationship_id,
            *tuple(provenance),
            "x3_extra_relationship",
            "manager:x3-00",
            "strategy:x3-00",
            "interval",
            None,
            "2024-01-01T00:00:00.000000Z",
            None,
            1,
            None,
        ),
    )
    conn.commit()
    return relationship_id


def test_x3_fixture_exact_authored_population_and_views() -> None:
    conn, manifest = _built()

    assert manifest.fixture_id == X3_FIXTURE_ID == "x3_evidence_v1"
    assert tuple(X3_CUTOFFS) == ("early", "middle", "latest")
    assert tuple(X3_SOURCE_VIEWS) == (
        "public-only",
        "public-plus-prehire",
        "full-synthetic-funnel",
    )
    assert tuple(X3_SCOPE_PRESETS) == (
        "cross-asset",
        "liquid-public-markets",
        "credit-private-markets",
    )
    assert manifest.dataset_ids == (
        "dataset:x3-public-adviser",
        "dataset:x3-registered-fund",
        "dataset:x3-holdings-filer",
        "dataset:x3-strategy-export",
        "dataset:x3-rfi-ddq",
        "dataset:x3-target-grid",
        "dataset:x3-funnel-opportunity",
        "dataset:x3-funnel-schema",
        "dataset:x3-funnel-cohort",
        "dataset:x3-funnel-event",
    )
    assert len(manifest.right_ids) == 10
    assert len(manifest.version_ids) == 32

    expected_entities = {
        "manager": 8,
        "adviser": 8,
        "legal-entity": 8,
        "strategy": 24,
        "composite": 24,
        "vehicle": 24,
    }
    assert {
        entity_type: _count(conn, "canonical_entity", f"entity_type='{entity_type}'")
        for entity_type in expected_entities
    } == expected_entities
    assert (
        _count(
            conn,
            "target_grid_cell",
            "target_grid_id IN (SELECT target_grid_id FROM target_grid WHERE source_label LIKE 'X3 target grid%')",
        )
        == 72
    )
    assert (
        _count(conn, "funnel_opportunity", "source_opportunity_key LIKE 'x3-opportunity-%'") == 252
    )
    assert _count(conn, "funnel_event") == 253

    latest_grid = conn.execute(
        "SELECT target_grid_id FROM target_grid WHERE source_label='X3 target grid latest'"
    ).fetchone()[0]
    eligible, excluded = conn.execute(
        "SELECT sum(eligibility_status='eligible'),sum(eligibility_status='excluded') FROM target_grid_cell WHERE target_grid_id=?",
        (latest_grid,),
    ).fetchone()
    assert (eligible, excluded) == (21, 3)
    dimensions = [
        json.loads(row[0])
        for row in conn.execute(
            "SELECT dimensions_json FROM target_grid_cell WHERE target_grid_id=?", (latest_grid,)
        )
    ]
    assert {row["asset_class"] for row in dimensions} == {
        "public-equity",
        "hedge-funds",
        "rates-macro",
        "fixed-income-credit",
        "structured-credit",
        "private-credit",
        "private-equity",
        "real-assets",
    }
    assert {row["vehicle_scope"] for row in dimensions} == {
        "pooled-fund",
        "drawdown-fund",
        "segregated-mandate",
    }


def test_x3_fixture_has_no_shared_hidden_truth_surface() -> None:
    conn, manifest = _built()
    exported = set(dir(x3_fixture)) | set(manifest.__dataclass_fields__)
    assert not {"X3_POSITIVE_PAIRS", "X3_NEGATIVE_PAIRS", "source_truth"} & exported
    assert "x3_truth" not in x3_fixture.__dict__
    payloads = [
        json.loads(row[0])
        for row in conn.execute(
            "SELECT payload_json FROM evidence_item i JOIN source_record s USING(source_record_id) "
            "WHERE s.dataset_id LIKE 'dataset:x3-%'"
        )
    ]
    assert not any(
        key in payload
        for payload in payloads
        for key in ("source_truth", "truth_label", "is_positive_pair", "hidden_universe")
    )


def test_x3_fixture_payloads_are_source_shaped_versioned_and_spanned() -> None:
    conn, manifest = _built()
    schemas = {
        row["payload_schema_id"]: row
        for row in conn.execute(
            "SELECT * FROM payload_schema WHERE payload_schema_id LIKE 'schema:x3-%-source-v1'"
        )
    }
    assert len(schemas) == len(manifest.dataset_ids) == 10
    assert set(manifest.payload_schema_digests) == set(schemas)
    assert set(manifest.field_dictionaries) == set(manifest.dataset_ids)
    assert set(manifest.version_payload_schema_ids) == set(manifest.version_ids)
    assert not conn.execute(
        "SELECT 1 FROM evidence_item i JOIN source_record s USING(source_record_id) "
        "WHERE s.dataset_id LIKE 'dataset:x3-%' AND i.payload_schema_id='schema:generic-v1'"
    ).fetchone()

    for dataset_id in manifest.dataset_ids:
        schema_id = dataset_id.replace("dataset:", "schema:") + "-source-v1"
        schema = json.loads(schemas[schema_id]["schema_json"])
        fields_for_dataset = tuple(manifest.field_dictionaries[dataset_id])
        assert tuple(schema["required"]) == fields_for_dataset
        assert schema["additionalProperties"] is False
        assert schemas[schema_id]["schema_sha256"] == sha256(canonical_bytes(schema))
        items = conn.execute(
            "SELECT i.* FROM evidence_item i JOIN source_record s USING(source_record_id) "
            "WHERE s.dataset_id=? ORDER BY i.evidence_item_id",
            (dataset_id,),
        ).fetchall()
        assert items
        for item in items:
            payload = json.loads(item["payload_json"])
            assert tuple(sorted(payload)) == tuple(sorted(fields_for_dataset))
            assert item["content_sha256"] == sha256(canonical_bytes(payload))
            rendered = canonical_bytes(payload).decode()
            spans = conn.execute(
                "SELECT * FROM evidence_span WHERE evidence_item_id=? ORDER BY json_pointer",
                (item["evidence_item_id"],),
            ).fetchall()
            assert {row["json_pointer"] for row in spans} == {
                f"/{field_name}" for field_name in fields_for_dataset
            }
            assert all(
                row["span_sha256"] == sha256(rendered[row["start_char"] : row["end_char"]].encode())
                for row in spans
            )


def test_x3_fixture_relationships_are_effective_dated_and_provenanced() -> None:
    conn, manifest = _built()
    assert len(manifest.relationship_ids) == 90
    assert _count(conn, "entity_relationship") == 90
    assert {
        row[0]: row[1]
        for row in conn.execute(
            "SELECT relation_type,count(*) FROM entity_relationship GROUP BY relation_type"
        )
    } == {
        "advised_by": 10,
        "implemented_by": 24,
        "legal_identity": 8,
        "offers": 24,
        "reported_through": 24,
    }
    assert not conn.execute(
        "SELECT 1 FROM entity_relationship r "
        "LEFT JOIN evidence_item i ON i.evidence_item_id=r.source_evidence_item_id "
        "LEFT JOIN evidence_span s ON s.evidence_span_id=r.evidence_span_id "
        "LEFT JOIN dataset_version v ON v.dataset_version_id=r.dataset_version_id "
        "LEFT JOIN dataset_observation o ON o.dataset_observation_id=r.dataset_observation_id "
        "LEFT JOIN evidence_right er ON er.evidence_right_id=i.acquisition_right_id "
        "WHERE i.evidence_item_id IS NULL OR s.evidence_item_id!=i.evidence_item_id "
        "OR v.dataset_version_id IS NULL OR o.evidence_item_id!=i.evidence_item_id "
        "OR er.evidence_right_id IS NULL OR r.temporal_type!='interval' "
        "OR r.effective_from IS NULL OR r.effective_at IS NOT NULL"
    ).fetchone()


def test_x3_manifest_allows_downstream_relationships_targeting_x3_endpoints() -> None:
    conn = connect()
    initialize(conn)
    manifest = build_x3_fixture(conn)
    assert verify_x3_manifest(conn, manifest)
    original_closure_digest = x3_authored_closure_digest(conn)
    original_manifest_payload = x3_manifest_payload(manifest)
    original_projection_counts = dict(manifest.projection_counts)
    original_receipt_inventory = x3_fixture._x3_receipt_ids(conn)  # noqa: SLF001
    original_mapping_records = manifest.mapping_records
    original_records = tuple(
        tuple(row)
        for row in conn.execute(
            "SELECT * FROM entity_relationship WHERE entity_relationship_id IN "
            f"({','.join('?' for _ in manifest.relationship_ids)}) "
            "ORDER BY entity_relationship_id",
            manifest.relationship_ids,
        )
    )

    downstream_id, downstream_mapping_id = _add_downstream_projections(conn)

    assert tuple(
        conn.execute(
            "SELECT s.dataset_id,r.source_entity_id,r.target_entity_id "
            "FROM entity_relationship r "
            "JOIN evidence_item i ON i.evidence_item_id=r.source_evidence_item_id "
            "JOIN source_record s ON s.source_record_id=i.source_record_id "
            "WHERE r.entity_relationship_id=?",
            (downstream_id,),
        ).fetchone()
    ) == ("dataset:downstream-research", "manager:x3-00", "strategy:x3-00")
    assert conn.execute(
        "SELECT source_key FROM entity_mapping WHERE entity_mapping_id=?",
        (downstream_mapping_id,),
    ).fetchone()[0] == "downstream-source-x3-00"
    assert x3_authored_closure_digest(conn) == original_closure_digest
    assert tuple(
        tuple(row)
        for row in conn.execute(
            "SELECT * FROM entity_relationship WHERE entity_relationship_id IN "
            f"({','.join('?' for _ in manifest.relationship_ids)}) "
            "ORDER BY entity_relationship_id",
            manifest.relationship_ids,
        )
    ) == original_records == manifest.relationship_records
    assert manifest.mapping_records == original_mapping_records
    assert manifest.projection_counts == original_projection_counts
    assert manifest.projection_counts["entity_mapping"] == 2501
    assert manifest.projection_counts["entity_relationship"] == 90
    assert x3_fixture._x3_receipt_ids(conn) == original_receipt_inventory  # noqa: SLF001
    rebuilt = build_x3_fixture(conn)
    assert x3_manifest_payload(rebuilt) == original_manifest_payload
    assert rebuilt == manifest
    assert verify_x3_manifest(conn, manifest)


def test_x3_manifest_rejects_extra_x3_sourced_relationship() -> None:
    conn, manifest = _built()
    original_closure_digest = x3_authored_closure_digest(conn)

    relationship_id = _add_x3_sourced_relationship(conn)

    assert conn.execute(
        "SELECT s.dataset_id FROM entity_relationship r "
        "JOIN evidence_item i ON i.evidence_item_id=r.source_evidence_item_id "
        "JOIN source_record s ON s.source_record_id=i.source_record_id "
        "WHERE r.entity_relationship_id=?",
        (relationship_id,),
    ).fetchone()[0].startswith("dataset:x3-")
    assert x3_authored_closure_digest(conn) != original_closure_digest
    assert not verify_x3_manifest(conn, manifest)


def test_x3_fixture_manifest_is_auditable_and_receipted() -> None:
    conn, manifest = _built()
    assert X3_AUTHORED_CLOSURE_CONTRACT_VERSION == "x3-authored-closure-v1"
    assert X3_AUTHORED_CLOSURE_SHA256 == (
        "c5054f17d2e95bf6e80ba7c63a5a8f10f849f7e989f12cf9447d0d308744ac32"
    )
    assert X3_AUTHORED_MANIFEST_SHA256 == (
        "14a159d4547960c937485d328c3b270051daba7114e54f1380869466a11275e0"
    )
    assert X3_AUTHORED_SCHEMA_SHA256 == (
        "43a0f22036e3e6b55fc15a05071e58d7771ff5546cedce7c4ee45155f38b0818"
    )
    assert x3_authored_closure_digest(conn) == X3_AUTHORED_CLOSURE_SHA256
    assert manifest.fixture_digest == X3_AUTHORED_MANIFEST_SHA256
    assert manifest.schema_digest == X3_AUTHORED_SCHEMA_SHA256
    assert manifest.schema_version == "evidence-v1"
    assert len(manifest.schema_digest) == 64
    assert manifest.rng_policy == "no-rng-authored-fixture"
    assert manifest.base_seed is None
    assert manifest.stream_tags == ()
    assert manifest.fictional_name_attestation == "fictional-names-verified"
    assert verify_x3_manifest(conn, manifest)
    assert set(x3_manifest_payload(manifest)) == {
        field.name for field in fields(manifest) if field.name != "fixture_digest"
    }
    assert len(manifest.canonical_entity_ids) == 96
    assert set(manifest.source_content_digests) == set(manifest.dataset_ids)
    assert set(manifest.reconstruction_digests) == set(manifest.version_ids)
    assert set(manifest.partition_digests) == set(manifest.version_ids)
    assert set(manifest.version_contracts) == set(manifest.version_ids)
    assert set(manifest.right_contracts) == set(manifest.dataset_ids)
    assert len(manifest.right_records) == 12
    assert set(manifest.version_records) == set(manifest.version_ids)
    assert set(manifest.partition_records) == set(manifest.version_ids)
    assert all(manifest.partition_records.values())
    renewed_rights = conn.execute(
        "SELECT * FROM evidence_right WHERE right_series_id='right-series:x3-post-entitlement' "
        "ORDER BY right_version"
    ).fetchall()
    assert [row["right_version"] for row in renewed_rights] == [1, 2]
    assert [row["status"] for row in renewed_rights] == ["superseded", "active"]
    assert renewed_rights[1]["supersedes_right_id"] == renewed_rights[0]["evidence_right_id"]
    assert set(manifest.licence_purposes) == set(manifest.dataset_ids)
    assert set(manifest.access_semantics) == set(manifest.dataset_ids)
    assert set(manifest.access_semantics.values()) == {"all-required-per-dataset"}
    assert set(manifest.slice_receipt_ids) == set(manifest.dataset_ids)
    assert set(manifest.slice_digests) == set(manifest.dataset_ids)
    assert all(
        conn.execute("SELECT 1 FROM receipt_seal WHERE receipt_id=?", (receipt_id,)).fetchone()
        for receipt_id in manifest.slice_receipt_ids.values()
    )
    assert manifest.join_policies == (
        "x3-source-union-v1",
        "x3-target-cell-v1",
        "x3-funnel-opportunity-v1",
    )
    assert set(manifest.composite_receipt_ids) == set(manifest.join_policies)
    assert set(manifest.composite_digests) == set(manifest.join_policies)
    assert len(manifest.join_receipt_ids) == len(manifest.bundle_digests) == 3
    assert all(
        conn.execute("SELECT 1 FROM receipt_seal WHERE receipt_id=?", (receipt_id,)).fetchone()
        for receipt_id in manifest.join_receipt_ids
    )
    bundle_rows = conn.execute(
        "SELECT * FROM snapshot_bundle_manifest WHERE bundle_digest IN (?,?,?) ORDER BY bundle_digest",
        manifest.bundle_digests,
    ).fetchall()
    assert len(bundle_rows) == 3
    assert {tuple(json.loads(row["request_json"])["join_keys"]) for row in bundle_rows} == {
        ("canonical_entity_id",),
        ("canonical_entity_id", "target_grid_cell_id"),
        ("opportunity_id",),
    }
    reference_columns = {
        "evidence-item": "evidence_item_id",
        "snapshot": "snapshot_digest",
        "entity-mapping": "entity_mapping_id",
        "target-grid-cell": "target_grid_cell_id",
        "funnel-opportunity": "funnel_opportunity_id",
        "funnel-event": "funnel_event_id",
    }
    for receipt_id in manifest.join_receipt_ids:
        rows = conn.execute(
            "SELECT * FROM receipt_reference WHERE receipt_id=? ORDER BY ordinal",
            (receipt_id,),
        ).fetchall()
        seal = conn.execute(
            "SELECT * FROM receipt_seal WHERE receipt_id=?", (receipt_id,)
        ).fetchone()
        persisted = tuple(
            ReceiptReference(
                row["output_field"],
                row["reference_type"],
                row[reference_columns[row["reference_type"]]],
                row["disposition"],
                row["reason_code"],
                row["source_schema_id"],
                row["source_field"],
                row["role"],
            )
            for row in rows
        )
        assert seal["reference_count"] == len(persisted)
        assert seal["references_sha256"] == sha256(canonical_bytes(persisted))
    assert len(manifest.projection_schema_ids) == 10
    assert len(manifest.cohort_evaluation_counts) == 2
    assert all(
        included + excluded == observed + censored == receipts == 84
        for included, excluded, observed, censored, receipts in manifest.cohort_evaluation_counts.values()
    )
    assert any(counts[1] > 0 for counts in manifest.cohort_evaluation_counts.values())
    assert {counts[3] > 0 for counts in manifest.cohort_evaluation_counts.values()} == {
        False,
        True,
    }
    assert len(manifest.cohort_refusals) == 1
    assert set(manifest.full_population_counts) == set(manifest.dataset_ids)
    assert all(count > 0 for count in manifest.full_population_counts.values())
    assert manifest.source_views == X3_SOURCE_VIEWS
    assert manifest.scope_presets == X3_SCOPE_PRESETS
    assert manifest.api_prerequisites == ("typed-mandate-brief-cohort-projection-required",)
    assert len(manifest.pit_cases) >= 25
    assert all(manifest.limitations)

    tampered = replace(manifest, disclosure=manifest.disclosure + " tampered")
    assert not verify_x3_manifest(conn, tampered)
    reordered = replace(
        manifest,
        source_content_digests=MappingProxyType(
            dict(reversed(tuple(manifest.source_content_digests.items())))
        ),
    )
    assert verify_x3_manifest(conn, reordered)
    assert reordered.fixture_digest == manifest.fixture_digest


def test_x3_fixture_plants_point_in_time_and_delivery_cases() -> None:
    conn, manifest = _built()
    dataset_id = "dataset:x3-rfi-ddq"

    def snapshot(cutoff):
        return as_known_slice(
            conn,
            decision_at=cutoff,
            request=DatasetSliceRequest(
                dataset_id,
                manifest.access_contexts[dataset_id],
                manifest.right_ids[dataset_id],
                "x3-research",
                valid_at=cutoff,
            ),
        )

    early = snapshot(X3_CUTOFFS["early"])
    latest = snapshot(X3_CUTOFFS["latest"])
    early_keys = {row["payload"]["source_key"] for row in early.rows}
    latest_keys = {row["payload"]["source_key"] for row in latest.rows}
    assert "x3-source-0004" not in early_keys
    assert "x3-source-0004" in latest_keys
    assert "x3-source-0029" not in early_keys
    assert "x3-source-0029" in latest_keys
    assert "x3-source-0039" in early_keys
    assert "x3-source-0039" not in latest_keys
    assert "x3-source-0034" not in latest_keys

    early_mappings = {row["source_key"]: row for row in project_entity_mappings(conn, early)}
    latest_mappings = {row["source_key"]: row for row in project_entity_mappings(conn, latest)}
    assert (
        early_mappings["x3-source-0009"]["source_label"]
        != latest_mappings["x3-source-0009"]["source_label"]
    )
    strategy_id = "dataset:x3-strategy-export"
    strategy_early = as_known_slice(
        conn,
        decision_at=X3_CUTOFFS["early"],
        request=DatasetSliceRequest(
            strategy_id,
            manifest.access_contexts[strategy_id],
            manifest.right_ids[strategy_id],
            "x3-research",
            valid_at=X3_CUTOFFS["early"],
        ),
    )
    strategy_latest = as_known_slice(
        conn,
        decision_at=X3_CUTOFFS["latest"],
        request=DatasetSliceRequest(
            strategy_id,
            manifest.access_contexts[strategy_id],
            manifest.right_ids[strategy_id],
            "x3-research",
            valid_at=X3_CUTOFFS["latest"],
        ),
    )
    strategy_early_mappings = {
        row["source_key"]: row for row in project_entity_mappings(conn, strategy_early)
    }
    strategy_latest_mappings = {
        row["source_key"]: row for row in project_entity_mappings(conn, strategy_latest)
    }
    assert (
        strategy_early_mappings["x3-source-0013"]["taxonomy_version"]
        != strategy_latest_mappings["x3-source-0013"]["taxonomy_version"]
    )
    public_id = "dataset:x3-public-adviser"
    public_early = as_known_slice(
        conn,
        decision_at=X3_CUTOFFS["early"],
        request=DatasetSliceRequest(
            public_id,
            manifest.access_contexts[public_id],
            manifest.right_ids[public_id],
            "x3-research",
            valid_at=X3_CUTOFFS["early"],
        ),
    )
    public_latest = as_known_slice(
        conn,
        decision_at=X3_CUTOFFS["latest"],
        request=DatasetSliceRequest(
            public_id,
            manifest.access_contexts[public_id],
            manifest.right_ids[public_id],
            "x3-research",
            valid_at=X3_CUTOFFS["latest"],
        ),
    )
    early_relationships = project_entity_relationships(conn, public_early)
    latest_relationships = project_entity_relationships(conn, public_latest)
    assert any(
        row["source_entity_id"] == "manager:x3-00" and row["target_entity_id"] == "adviser:x3-00"
        for row in early_relationships
    )
    assert any(
        row["source_entity_id"] == "manager:x3-00" and row["target_entity_id"] == "adviser:x3-01"
        for row in latest_relationships
    )
    assert not any(
        row["source_entity_id"] == "manager:x3-00" and row["target_entity_id"] == "adviser:x3-00"
        for row in latest_relationships
    )
    revised_relationship = conn.execute(
        "SELECT * FROM entity_relationship WHERE entity_relationship_id=?",
        (manifest.pit_cases["later_relationship_revision"],),
    ).fetchone()
    assert revised_relationship["version"] == 2
    assert revised_relationship["revision_of"]
    assert latest_mappings["x3-source-0014"]["mapping_status"] == "ambiguous"
    assert latest_mappings["x3-source-0014"]["canonical_entity_id"] is None
    memberships = {
        conn.execute(
            "SELECT source_key FROM entity_mapping WHERE entity_mapping_id=?",
            (row["entity_mapping_id"],),
        ).fetchone()[0]: row["membership_status"]
        for row in project_universe_memberships(conn, latest)
    }
    assert memberships["x3-source-0019"] == "inactive"
    assert memberships["x3-source-0024"] == "dead"

    contracts = {
        row["version_label"]: (row["delivery_mode"], row["absence_semantics"])
        for row in conn.execute(
            "SELECT version_label,delivery_mode,absence_semantics FROM dataset_version "
            "WHERE dataset_id='dataset:x3-holdings-filer'"
        )
    }
    assert contracts == {
        "early": ("full-snapshot", "full-snapshot-means-removed"),
        "middle": ("delta", "explicit-tombstone-only"),
        "latest": ("delta", "explicit-tombstone-only"),
    }
    assert any(contract[1] == "not-inferable" for contract in manifest.version_contracts.values())

    registered_versions = conn.execute(
        "SELECT dataset_version_id,version_label FROM dataset_version "
        "WHERE dataset_id='dataset:x3-registered-fund' ORDER BY first_observed_at_utc"
    ).fetchall()
    registered_statuses = {
        label: {
            row[0]: row[1]
            for row in conn.execute(
                "SELECT s.source_record_key,o.observation_status FROM dataset_observation o "
                "JOIN evidence_item i USING(evidence_item_id) "
                "JOIN source_record s USING(source_record_id) WHERE o.dataset_version_id=?",
                (version_id,),
            )
        }
        for version_id, label in registered_versions
    }
    assert all("x3-source-0001" in rows for rows in registered_statuses.values())
    assert "x3-source-0006" in registered_statuses["early"]
    assert "x3-source-0006" not in registered_statuses["middle"]
    assert "x3-source-0026" not in registered_statuses["middle"]
    assert "x3-source-0026" in registered_statuses["latest"]
    registered_labels = {
        row[0]: row[1]
        for row in conn.execute(
            "SELECT v.version_label,m.source_label FROM entity_mapping m "
            "JOIN dataset_version v USING(dataset_version_id) WHERE m.source_key='x3-source-0011'"
        )
    }
    assert registered_labels["early"] != registered_labels["latest"]

    holding_history = conn.execute(
        "SELECT v.version_label,o.observation_status FROM dataset_observation o "
        "JOIN dataset_version v USING(dataset_version_id) "
        "JOIN evidence_item i USING(evidence_item_id) "
        "JOIN source_record s USING(source_record_id) WHERE s.source_record_key='x3-source-0002' "
        "ORDER BY v.first_observed_at_utc"
    ).fetchall()
    assert [tuple(row) for row in holding_history] == [
        ("early", "present"),
        ("middle", "explicitly-removed"),
        ("latest", "present"),
    ]

    late_right = manifest.pit_cases["post_cutoff_entitlement"]
    with pytest.raises(EvidenceRefusal, match="entitlement-not-active"):
        as_known_slice(
            conn,
            decision_at=X3_CUTOFFS["early"],
            request=DatasetSliceRequest(
                "dataset:x3-strategy-export", "pre-hire-public", late_right, "x3-research"
            ),
        )
    with pytest.raises(EvidenceRefusal, match="incomplete-dataset-version"):
        as_known_slice(
            conn,
            decision_at=datetime(2024, 10, 31, tzinfo=UTC),
            request=DatasetSliceRequest(
                "dataset:x3-funnel-event",
                "internal-governance",
                manifest.right_ids["dataset:x3-funnel-event"],
                "x3-research",
            ),
        )
    with pytest.raises(EvidenceRefusal, match="right-retention-forbidden"):
        as_known_slice(
            conn,
            decision_at=datetime(2024, 10, 31, tzinfo=UTC),
            request=DatasetSliceRequest(
                "dataset:x3-strategy-export",
                "pre-hire-public",
                manifest.right_ids["dataset:x3-strategy-export"],
                "x3-research",
                valid_at=datetime(2024, 10, 31, tzinfo=UTC),
            ),
        )


def test_x3_fixture_funnel_ids_progress_and_cohorts_are_receipted() -> None:
    conn, manifest = _built()
    content_chains = conn.execute(
        "SELECT s.source_record_key,count(*),min(i.version),max(i.version) "
        "FROM evidence_item i JOIN source_record s USING(source_record_id) "
        "WHERE s.source_record_key GLOB 'x3-funnel-event-[0-9][0-9][0-9]' "
        "GROUP BY s.source_record_key"
    ).fetchall()
    assert len(content_chains) == 84
    assert all(tuple(row[1:]) == (3, 1, 3) for row in content_chains)
    assert not conn.execute(
        "SELECT 1 FROM evidence_item child LEFT JOIN evidence_item parent "
        "ON parent.evidence_item_id=child.revision_of "
        "JOIN source_record s ON s.source_record_id=child.source_record_id "
        "WHERE s.source_record_key GLOB 'x3-funnel-event-[0-9][0-9][0-9]' "
        "AND child.version>1 "
        "AND (parent.evidence_item_id IS NULL OR parent.version!=child.version-1 "
        "OR parent.source_record_id!=child.source_record_id)"
    ).fetchone()
    rows = conn.execute(
        "SELECT source_opportunity_key,count(*),count(DISTINCT version) "
        "FROM funnel_opportunity GROUP BY source_opportunity_key"
    ).fetchall()
    assert len(rows) == 84
    assert all((row[1], row[2]) == (3, 3) for row in rows)
    opportunity_chain = conn.execute(
        "SELECT version,revision_of,funnel_opportunity_id FROM funnel_opportunity "
        "WHERE source_opportunity_key='x3-opportunity-000' ORDER BY version"
    ).fetchall()
    assert [row[0] for row in opportunity_chain] == [1, 2, 3]
    assert opportunity_chain[0][1] is None
    assert opportunity_chain[1][1] == opportunity_chain[0][2]
    assert opportunity_chain[2][1] == opportunity_chain[1][2]
    assert _count(conn, "funnel_event", "reason_code='correction-reversal'") == 1
    assert _count(conn, "funnel_event", "reason_code='impossible-transition'") == 1

    dataset_id = "dataset:x3-funnel-event"
    snapshot = as_known_slice(
        conn,
        decision_at=X3_CUTOFFS["latest"],
        request=DatasetSliceRequest(
            dataset_id,
            manifest.access_contexts[dataset_id],
            manifest.right_ids[dataset_id],
            "x3-research",
            valid_at=X3_CUTOFFS["latest"],
        ),
    )
    cohorts = project_funnel_cohorts(conn, snapshot)
    cohort_by_label = {row["cohort_label"]: row for row in cohorts}
    assert set(cohort_by_label) == {
        "x3-discovered-to-screen",
        "x3-diligence-to-approved",
        "x3-accepted-only-incomplete",
    }
    evaluated = [
        evaluate_funnel_cohort(conn, snapshot, funnel_cohort_id=row["funnel_cohort_id"])
        for row in cohorts
        if row["completeness_status"] == "complete"
    ]
    assert all(
        len(result["links"]) == 84
        and all(link["evaluation_receipt_id"] for link in result["links"])
        for result in evaluated
    )
    assert {
        frozenset(link["censor_status"] for link in result["links"]) for result in evaluated
    } == {frozenset({"right-censored"}), frozenset({"observed"})}
    assert {link["inclusion_disposition"] for result in evaluated for link in result["links"]} == {
        "included",
        "excluded",
    }
    with pytest.raises(EvidenceRefusal, match="incomplete-funnel-cohort"):
        evaluate_funnel_cohort(
            conn,
            snapshot,
            funnel_cohort_id=cohort_by_label["x3-accepted-only-incomplete"]["funnel_cohort_id"],
        )

    schemas = project_funnel_schemas(conn, snapshot)
    assert len(schemas) == 1
    stage_dictionary = json.loads(schemas[0]["stage_dictionary_json"])
    transition_dictionary = json.loads(schemas[0]["transition_rules_json"])
    reason_dictionary = json.loads(schemas[0]["reason_dictionary_json"])
    assert stage_dictionary["stages"] == [
        "discovered",
        "contacted",
        "rfi_received",
        "screened",
        "diligence",
        "ic_ready",
        "approved",
        "funded",
    ]
    assert stage_dictionary["side_states"] == [
        "declined",
        "manager_withdrew",
        "unavailable",
        "paused",
        "duplicate",
        "out_of_scope",
    ]
    assert transition_dictionary["allowed_starts"] == ["discovered"]
    assert transition_dictionary["terminal_states"] == [
        "funded",
        *stage_dictionary["side_states"],
    ]
    assert "correction-reversal" in reason_dictionary
    assert "impossible-transition" not in reason_dictionary
    assert manifest.pit_cases["stale_funnel_schema"] not in {
        row["funnel_schema_id"] for row in schemas
    }

    projected_events = project_funnel_events(conn, snapshot)
    assert len(projected_events) == 84
    for event in projected_events:
        payload = json.loads(
            conn.execute(
                "SELECT payload_json FROM evidence_item WHERE evidence_item_id=?",
                (event["source_evidence_item_id"],),
            ).fetchone()[0]
        )
        assert (
            payload["funnel_stage"],
            payload["event_status"],
            payload["reason_code"],
        ) == (
            event["funnel_stage"],
            event["event_status"],
            event["reason_code"],
        )
    revised = next(row for row in projected_events if row["reason_code"] == "correction-reversal")
    parent = conn.execute(
        "SELECT * FROM funnel_event WHERE funnel_event_id=?", (revised["revision_of"],)
    ).fetchone()
    assert parent["event_status"] == "accepted"
    assert revised["event_status"] == "rejected"
    assert manifest.funnel_rate_cases == {
        "discovered-to-screen": (84, 65, "wilson-interval"),
        "diligence-to-approved": (17, 7, "count-only-insufficient-cohort"),
    }


def test_x3_fixture_latest_slices_project_complete_typed_shapes() -> None:
    conn, manifest = _built()
    cutoff = X3_CUTOFFS["latest"]

    sample_entity = {
        "dataset:x3-public-adviser": "manager:x3-00",
        "dataset:x3-registered-fund": "vehicle:x3-00",
        "dataset:x3-holdings-filer": "vehicle:x3-00",
        "dataset:x3-strategy-export": "composite:x3-00",
        "dataset:x3-rfi-ddq": "strategy:x3-00",
    }
    for dataset_id in manifest.coverage_dataset_ids:
        request = DatasetSliceRequest(
            dataset_id=dataset_id,
            access_context=manifest.access_contexts[dataset_id],
            evidence_right_id=manifest.right_ids[dataset_id],
            licence_purpose="x3-research",
            canonical_entity_ids=(sample_entity[dataset_id],)
            if dataset_id in sample_entity
            else (),
            valid_at=cutoff,
            require_universe_membership=dataset_id not in {"dataset:x3-target-grid"},
        )
        snapshot = as_known_slice(conn, decision_at=cutoff, request=request)
        assert snapshot.receipt_id
        if dataset_id == "dataset:x3-target-grid":
            assert len(project_target_grids(conn, snapshot)) == 1
        else:
            assert project_entity_mappings(conn, snapshot)
            assert project_universe_memberships(conn, snapshot)

    funnel_id = "dataset:x3-funnel-event"
    funnel = as_known_slice(
        conn,
        decision_at=cutoff,
        request=DatasetSliceRequest(
            dataset_id=funnel_id,
            access_context=manifest.access_contexts[funnel_id],
            evidence_right_id=manifest.right_ids[funnel_id],
            licence_purpose="x3-research",
            valid_at=cutoff,
        ),
    )
    assert len(project_funnel_opportunities(conn, funnel)) == 84
    assert len(project_funnel_events(conn, funnel)) == 84
    assert len(project_funnel_schemas(conn, funnel)) == 1
    cohorts = project_funnel_cohorts(conn, funnel)
    assert len(cohorts) == 3
    cohort_by_label = {row["cohort_label"]: row for row in cohorts}
    evaluated = evaluate_funnel_cohort(
        conn,
        funnel,
        funnel_cohort_id=cohort_by_label["x3-discovered-to-screen"]["funnel_cohort_id"],
    )
    assert len(evaluated["links"]) == 84


def test_x3_fixture_is_idempotent_and_deterministic() -> None:
    first_conn, first = _built()
    again = build_x3_fixture(first_conn)
    second_conn, second = _built()
    assert again == first == second
    assert len(first.fixture_digest) == 64

    tables = (
        "canonical_entity",
        "dataset",
        "payload_schema",
        "evidence_right",
        "dataset_version",
        "dataset_delivery_partition",
        "source_record",
        "evidence_item",
        "evidence_span",
        "dataset_observation",
        "dataset_observation_partition_link",
        "entity_mapping",
        "universe_membership",
        "target_grid",
        "target_grid_cell",
        "funnel_opportunity",
        "funnel_schema",
        "funnel_cohort",
        "funnel_cohort_event_link",
        "funnel_event",
        "entity_relationship",
        "reconstruction_receipt",
        "receipt_reference",
        "receipt_seal",
        "snapshot_manifest",
        "snapshot_bundle_manifest",
    )
    assert _dump(first_conn, tables) == _dump(second_conn, tables)


def _drop_immutable_trigger(conn: sqlite3.Connection, table: str, operation: str) -> None:
    conn.execute(f"DROP TRIGGER immutable_{operation}_{table}")


@pytest.mark.parametrize(
    ("closure_class", "table", "operation", "sql"),
    (
        (
            "schema",
            "payload_schema",
            "update",
            "UPDATE payload_schema SET schema_sha256=printf('%064d',0) "
            "WHERE payload_schema_id=(SELECT min(payload_schema_id) FROM payload_schema "
            "WHERE payload_schema_id LIKE 'schema:x3-%')",
        ),
        (
            "source",
            "source_record",
            "update",
            "UPDATE source_record SET source_system='tampered' "
            "WHERE source_record_id=(SELECT min(source_record_id) FROM source_record "
            "WHERE dataset_id LIKE 'dataset:x3-%')",
        ),
        (
            "source-delete",
            "source_record",
            "delete",
            "DELETE FROM source_record WHERE source_record_id=(SELECT min(source_record_id) "
            "FROM source_record WHERE dataset_id LIKE 'dataset:x3-%')",
        ),
        (
            "version",
            "dataset_version",
            "update",
            "UPDATE dataset_version SET content_sha256=printf('%064d',0) "
            "WHERE dataset_version_id=(SELECT min(dataset_version_id) FROM dataset_version "
            "WHERE dataset_id LIKE 'dataset:x3-%')",
        ),
        (
            "partition",
            "dataset_delivery_partition",
            "update",
            "UPDATE dataset_delivery_partition SET received_content_sha256=printf('%064d',0) "
            "WHERE dataset_delivery_partition_id=(SELECT min(dataset_delivery_partition_id) "
            "FROM dataset_delivery_partition)",
        ),
        (
            "right",
            "evidence_right",
            "update",
            "UPDATE evidence_right SET retention_policy='access-only-while-active' "
            "WHERE evidence_right_id=(SELECT min(evidence_right_id) FROM evidence_right "
            "WHERE dataset_id LIKE 'dataset:x3-%')",
        ),
        (
            "mapping-status",
            "entity_mapping",
            "update",
            "UPDATE entity_mapping SET mapping_status='unresolved' "
            "WHERE entity_mapping_id=(SELECT min(entity_mapping_id) FROM entity_mapping "
            "WHERE mapping_status='resolved')",
        ),
        (
            "mapping-label",
            "entity_mapping",
            "update",
            "UPDATE entity_mapping SET source_label='tampered-label' "
            "WHERE entity_mapping_id=(SELECT min(entity_mapping_id) FROM entity_mapping)",
        ),
        (
            "mapping-delete",
            "entity_mapping",
            "delete",
            "DELETE FROM entity_mapping WHERE entity_mapping_id="
            "(SELECT min(entity_mapping_id) FROM entity_mapping)",
        ),
        (
            "mapping-provenance",
            "entity_mapping",
            "update",
            "UPDATE entity_mapping SET evidence_span_id=(SELECT min(evidence_span_id) "
            "FROM evidence_span WHERE evidence_span_id!=entity_mapping.evidence_span_id) "
            "WHERE entity_mapping_id=(SELECT min(entity_mapping_id) FROM entity_mapping)",
        ),
        (
            "relationship-type",
            "entity_relationship",
            "update",
            "UPDATE entity_relationship SET relation_type='tampered' "
            "WHERE entity_relationship_id=(SELECT min(entity_relationship_id) "
            "FROM entity_relationship)",
        ),
        (
            "relationship-effective-interval",
            "entity_relationship",
            "update",
            "UPDATE entity_relationship SET effective_to='2099-01-01T00:00:00.000000Z' "
            "WHERE entity_relationship_id=(SELECT min(entity_relationship_id) "
            "FROM entity_relationship WHERE effective_to IS NULL)",
        ),
        (
            "relationship-delete",
            "entity_relationship",
            "delete",
            "DELETE FROM entity_relationship WHERE entity_relationship_id="
            "(SELECT min(entity_relationship_id) FROM entity_relationship)",
        ),
        (
            "relationship-revision",
            "entity_relationship",
            "update",
            "UPDATE entity_relationship SET revision_of=NULL "
            "WHERE entity_relationship_id=(SELECT min(entity_relationship_id) "
            "FROM entity_relationship WHERE version=2)",
        ),
        (
            "slice",
            "snapshot_manifest",
            "update",
            "UPDATE snapshot_manifest SET records_sha256=printf('%064d',0) "
            "WHERE snapshot_digest=(SELECT min(snapshot_digest) FROM snapshot_manifest)",
        ),
        (
            "slice-delete",
            "snapshot_manifest",
            "delete",
            "DELETE FROM snapshot_manifest WHERE snapshot_digest=(SELECT min(snapshot_digest) "
            "FROM snapshot_manifest)",
        ),
        (
            "receipt",
            "reconstruction_receipt",
            "update",
            "UPDATE reconstruction_receipt SET algorithm_version='tampered' "
            "WHERE receipt_id=(SELECT min(receipt_id) FROM reconstruction_receipt)",
        ),
        (
            "reference",
            "receipt_reference",
            "update",
            "UPDATE receipt_reference SET source_field='/tampered' WHERE (receipt_id,ordinal)="
            "(SELECT receipt_id,ordinal FROM receipt_reference ORDER BY receipt_id,ordinal LIMIT 1)",
        ),
        (
            "reference-delete",
            "receipt_reference",
            "delete",
            "DELETE FROM receipt_reference WHERE (receipt_id,ordinal)=(SELECT receipt_id,ordinal "
            "FROM receipt_reference ORDER BY receipt_id,ordinal LIMIT 1)",
        ),
        (
            "seal",
            "receipt_seal",
            "update",
            "UPDATE receipt_seal SET references_sha256=printf('%064d',0) "
            "WHERE receipt_id=(SELECT min(receipt_id) FROM receipt_seal)",
        ),
        (
            "composite",
            "snapshot_bundle_manifest",
            "update",
            "UPDATE snapshot_bundle_manifest SET composite_input_digest=printf('%064d',0) "
            "WHERE bundle_digest=(SELECT min(bundle_digest) FROM snapshot_bundle_manifest)",
        ),
        (
            "bundle",
            "snapshot_bundle_manifest",
            "update",
            "UPDATE snapshot_bundle_manifest SET records_sha256=printf('%064d',0) "
            "WHERE bundle_digest=(SELECT max(bundle_digest) FROM snapshot_bundle_manifest)",
        ),
    ),
)
def test_x3_manifest_verifier_rejects_persisted_closure_tamper(
    closure_class: str, table: str, operation: str, sql: str
) -> None:
    del closure_class
    base, manifest = _built()
    conn = connect()
    base.backup(conn)
    conn.commit()
    conn.execute("PRAGMA foreign_keys=OFF")
    _drop_immutable_trigger(conn, table, operation)
    conn.execute(sql)
    conn.commit()

    assert not verify_x3_manifest(conn, manifest)


def test_x3_manifest_verifier_rejects_view_scope_and_manifest_mismatch() -> None:
    conn, manifest = _built()
    changed = replace(
        manifest,
        source_views=("tampered-view",),
        scope_presets=("tampered-scope",),
        fixture_digest="",
    )
    changed = replace(changed, fixture_digest=x3_manifest_digest(changed))
    assert not verify_x3_manifest(conn, changed)


def test_x3_manifest_verifier_rejects_regenerated_authored_schema_edit() -> None:
    base, _ = _built()
    conn = connect()
    base.backup(conn)
    conn.commit()
    _drop_immutable_trigger(conn, "payload_schema", "update")
    row = conn.execute(
        "SELECT payload_schema_id,schema_json FROM payload_schema "
        "WHERE payload_schema_id='schema:x3-public-adviser-source-v1'"
    ).fetchone()
    changed_schema = json.loads(row["schema_json"])
    changed_schema["description"] = "accidental local edit"
    conn.execute(
        "UPDATE payload_schema SET schema_json=?,schema_sha256=? WHERE payload_schema_id=?",
        (
            canonical_bytes(changed_schema).decode(),
            sha256(canonical_bytes(changed_schema)),
            row["payload_schema_id"],
        ),
    )
    conn.commit()
    changed = x3_fixture._manifest(  # noqa: SLF001
        conn,
        *x3_fixture._authoritative_x3_inputs(conn),  # noqa: SLF001
    )

    assert not verify_x3_manifest(conn, changed)


@pytest.mark.parametrize(
    ("authored_class", "table", "sql"),
    (
        (
            "source-record",
            "source_record",
            "UPDATE source_record SET source_entity_type='manager' "
            "WHERE source_record_id=(SELECT min(source_record_id) FROM source_record "
            "WHERE dataset_id='dataset:x3-funnel-event')",
        ),
        (
            "right",
            "evidence_right",
            "UPDATE evidence_right SET retention_policy='access-only-while-active' "
            "WHERE evidence_right_id=(SELECT min(evidence_right_id) FROM evidence_right "
            "WHERE dataset_id LIKE 'dataset:x3-%')",
        ),
        (
            "version",
            "dataset_version",
            "UPDATE dataset_version SET published_at='2024-03-02T00:00:00.000000Z' "
            "WHERE dataset_id='dataset:x3-public-adviser' AND version_label='early'",
        ),
        (
            "partition",
            "dataset_delivery_partition",
            "UPDATE dataset_delivery_partition SET manifest_evidence_span_id=("
            "SELECT min(s.evidence_span_id) FROM evidence_span s "
            "WHERE s.evidence_item_id=dataset_delivery_partition.manifest_evidence_item_id "
            "AND s.evidence_span_id!=dataset_delivery_partition.manifest_evidence_span_id) "
            "WHERE dataset_delivery_partition_id=(SELECT min(dataset_delivery_partition_id) "
            "FROM dataset_delivery_partition)",
        ),
        (
            "observation",
            "dataset_observation",
            "UPDATE dataset_observation SET disappearance_reason='accidental-local-edit' "
            "WHERE dataset_observation_id=(SELECT min(dataset_observation_id) "
            "FROM dataset_observation WHERE observation_status='present')",
        ),
        (
            "bundle",
            "snapshot_bundle_manifest",
            "UPDATE snapshot_bundle_manifest SET row_count=row_count+1 "
            "WHERE bundle_digest=(SELECT min(bundle_digest) FROM snapshot_bundle_manifest)",
        ),
    ),
)
def test_x3_manifest_verifier_rejects_regenerated_authored_row_edit(
    authored_class: str, table: str, sql: str
) -> None:
    del authored_class
    base, _ = _built()
    conn = connect()
    base.backup(conn)
    conn.commit()
    conn.execute("PRAGMA foreign_keys=OFF")
    _drop_immutable_trigger(conn, table, "update")
    conn.execute(sql)
    conn.commit()
    changed = x3_fixture._manifest(  # noqa: SLF001
        conn,
        *x3_fixture._authoritative_x3_inputs(conn),  # noqa: SLF001
    )

    assert not verify_x3_manifest(conn, changed)


def test_x3_manifest_verifier_rejects_regenerated_complete_payload_edit() -> None:
    base, _ = _built()
    conn = connect()
    base.backup(conn)
    conn.commit()
    _drop_immutable_trigger(conn, "evidence_item", "update")
    row = conn.execute(
        "SELECT i.evidence_item_id,i.payload_json FROM evidence_item i "
        "JOIN source_record s USING(source_record_id) "
        "WHERE s.dataset_id='dataset:x3-rfi-ddq' ORDER BY i.evidence_item_id LIMIT 1"
    ).fetchone()
    payload = json.loads(row["payload_json"])
    payload["document_evidence_id"] = "DOC-9999-9"
    conn.execute(
        "UPDATE evidence_item SET payload_json=?,content_sha256=? WHERE evidence_item_id=?",
        (
            canonical_bytes(payload).decode(),
            sha256(canonical_bytes(payload)),
            row["evidence_item_id"],
        ),
    )
    conn.commit()
    changed = x3_fixture._manifest(  # noqa: SLF001
        conn,
        *x3_fixture._authoritative_x3_inputs(conn),  # noqa: SLF001
    )

    assert not verify_x3_manifest(conn, changed)


def test_x3_manifest_verifier_rejects_unversioned_authored_payload_rule_change(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_payload = x3_fixture._payload  # noqa: SLF001

    def changed_payload(*args, **kwargs):
        payload = original_payload(*args, **kwargs)
        if args[0] == "dataset:x3-registered-fund":
            payload["report_type"] = "changed-authored-rule"
        return payload

    monkeypatch.setattr(x3_fixture, "_payload", changed_payload)
    x3_fixture._authored_x3_closure.cache_clear()  # noqa: SLF001
    conn, changed = _built()
    changed_rows = conn.execute(
        "SELECT count(*) FROM evidence_item i JOIN source_record s USING(source_record_id) "
        "WHERE s.dataset_id='dataset:x3-registered-fund' "
        "AND i.payload_json LIKE '%changed-authored-rule%'"
    ).fetchone()[0]
    assert changed_rows == 169
    assert x3_authored_closure_digest(conn) != X3_AUTHORED_CLOSURE_SHA256

    assert not verify_x3_manifest(conn, changed)
    x3_fixture._authored_x3_closure.cache_clear()  # noqa: SLF001


def test_x3_manifest_verifier_rejects_regenerated_missing_authored_row() -> None:
    base, _ = _built()
    conn = connect()
    base.backup(conn)
    conn.commit()
    conn.execute("PRAGMA foreign_keys=OFF")
    _drop_immutable_trigger(conn, "evidence_right", "delete")
    conn.execute(
        "DELETE FROM evidence_right WHERE right_series_id='right-series:x3-post-entitlement' "
        "AND right_version=2"
    )
    conn.commit()
    changed = x3_fixture._manifest(  # noqa: SLF001
        conn,
        *x3_fixture._authoritative_x3_inputs(conn),  # noqa: SLF001
    )

    assert not verify_x3_manifest(conn, changed)


def test_x3_manifest_verifier_rejects_regenerated_extra_receipt_inventory() -> None:
    conn, _ = _built()
    item = conn.execute(
        "SELECT i.evidence_item_id,i.payload_schema_id FROM evidence_item i "
        "JOIN source_record s USING(source_record_id) WHERE s.dataset_id LIKE 'dataset:x3-%' "
        "ORDER BY i.evidence_item_id LIMIT 1"
    ).fetchone()
    receipt = make_receipt(
        claim_id="claim:x3-extra-local-receipt",
        output_locator="/rows",
        input_digest="x3-extra-local-receipt",
        output_schema_id="schema:generic-v1",
        current_attestation="D",
        live_attestation_ceiling="B",
        algorithm_id="x3-extra-local-receipt",
        algorithm_version="1",
        parameters={},
        value={},
        references=(
            ReceiptReference(
                "/rows",
                "evidence-item",
                item["evidence_item_id"],
                "included",
                "",
                item["payload_schema_id"],
                "/source_key",
                "input",
            ),
        ),
    )
    store_receipt(conn, receipt)
    conn.commit()
    changed = x3_fixture._manifest(  # noqa: SLF001
        conn,
        *x3_fixture._authoritative_x3_inputs(conn),  # noqa: SLF001
    )

    assert not verify_x3_manifest(conn, changed)


def test_x3_manifest_verifier_rejects_missing_receipt_inventory() -> None:
    conn, _ = _built()
    changed = x3_fixture._manifest(  # noqa: SLF001
        conn,
        *x3_fixture._authoritative_x3_inputs(conn),  # noqa: SLF001
    )
    receipt_id = changed.join_receipt_ids[0]
    conn.commit()
    conn.execute("PRAGMA foreign_keys=OFF")
    for table in ("receipt_seal", "receipt_reference", "reconstruction_receipt"):
        _drop_immutable_trigger(conn, table, "delete")
    conn.execute("DELETE FROM receipt_seal WHERE receipt_id=?", (receipt_id,))
    conn.execute("DELETE FROM receipt_reference WHERE receipt_id=?", (receipt_id,))
    conn.execute("DELETE FROM reconstruction_receipt WHERE receipt_id=?", (receipt_id,))
    conn.commit()

    assert not verify_x3_manifest(conn, changed)


def test_x3_manifest_verifier_rejects_rehashed_projection_record_mismatch() -> None:
    conn, manifest = _built()
    mapping_columns = tuple(row[1] for row in conn.execute("PRAGMA table_info(entity_mapping)"))
    mapping_records = [list(row) for row in manifest.mapping_records]
    mapping_records[0][mapping_columns.index("mapping_status")] = "unresolved"
    changed_mapping = replace(
        manifest,
        mapping_records=tuple(tuple(row) for row in mapping_records),
        fixture_digest="",
    )
    changed_mapping = replace(changed_mapping, fixture_digest=x3_manifest_digest(changed_mapping))
    assert not verify_x3_manifest(conn, changed_mapping)

    relationship_columns = tuple(
        row[1] for row in conn.execute("PRAGMA table_info(entity_relationship)")
    )
    relationship_records = [list(row) for row in manifest.relationship_records]
    relationship_records[0][relationship_columns.index("relation_type")] = "tampered"
    changed_relationship = replace(
        manifest,
        relationship_records=tuple(tuple(row) for row in relationship_records),
        fixture_digest="",
    )
    changed_relationship = replace(
        changed_relationship, fixture_digest=x3_manifest_digest(changed_relationship)
    )
    assert not verify_x3_manifest(conn, changed_relationship)


@pytest.mark.parametrize(
    ("case", "table", "where_sql", "updates"),
    (
        (
            "mapping-interval",
            "entity_mapping",
            "source_entity_type='strategy' AND mapping_status='resolved'",
            {"effective_from": "2023-01-01T00:00:00.000000Z"},
        ),
        (
            "mapping-canonical-target",
            "entity_mapping",
            "source_entity_type='strategy' AND mapping_status='resolved' "
            "AND canonical_entity_id!='strategy:x3-23'",
            {"canonical_entity_id": "strategy:x3-23"},
        ),
        (
            "mapping-source-type",
            "entity_mapping",
            "source_entity_type='strategy' AND mapping_status='resolved'",
            {"source_entity_type": "manager"},
        ),
        (
            "mapping-status-label",
            "entity_mapping",
            "mapping_status='resolved'",
            {"mapping_status": "unresolved", "source_label": "tampered-label"},
        ),
        (
            "relationship-type",
            "entity_relationship",
            "relation_type='offers' AND source_entity_id='manager:x3-01'",
            {"relation_type": "tampered"},
        ),
        (
            "relationship-interval",
            "entity_relationship",
            "relation_type='offers' AND source_entity_id='manager:x3-01'",
            {"effective_from": "2023-01-01T00:00:00.000000Z"},
        ),
        (
            "relationship-revision",
            "entity_relationship",
            "relation_type='advised_by' AND source_entity_id='manager:x3-00' AND version=2",
            {"revision_of": None},
        ),
    ),
)
def test_x3_manifest_verifier_rejects_persisted_and_rehashed_semantic_tamper(
    case: str, table: str, where_sql: str, updates: dict[str, object]
) -> None:
    del case
    base, _ = _built()
    conn = connect()
    base.backup(conn)
    conn.commit()
    conn.execute("PRAGMA foreign_keys=OFF")
    _drop_immutable_trigger(conn, table, "update")
    identifier = f"{table}_id"
    row_id = conn.execute(
        f"SELECT {identifier} FROM {table} WHERE {where_sql} ORDER BY {identifier} LIMIT 1"
    ).fetchone()[0]
    assignments = ",".join(f"{column}=?" for column in updates)
    conn.execute(
        f"UPDATE {table} SET {assignments} WHERE {identifier}=?",
        (*updates.values(), row_id),
    )
    conn.commit()
    changed = x3_fixture._manifest(
        conn,
        *x3_fixture._authoritative_x3_inputs(conn),  # noqa: SLF001
    )
    assert changed.fixture_digest == x3_manifest_digest(changed)

    assert not verify_x3_manifest(conn, changed)


def test_x3_manifest_verifier_rejects_persisted_and_rehashed_relationship_provenance() -> None:
    base, _ = _built()
    conn = connect()
    base.backup(conn)
    conn.commit()
    conn.execute("PRAGMA foreign_keys=OFF")
    _drop_immutable_trigger(conn, "entity_relationship", "update")
    target = conn.execute(
        "SELECT entity_relationship_id FROM entity_relationship WHERE relation_type='offers' "
        "AND source_entity_id='manager:x3-01' ORDER BY entity_relationship_id LIMIT 1"
    ).fetchone()[0]
    other = conn.execute(
        "SELECT source_evidence_item_id,evidence_span_id,dataset_version_id,dataset_observation_id "
        "FROM entity_relationship WHERE entity_relationship_id!=? "
        "ORDER BY entity_relationship_id DESC LIMIT 1",
        (target,),
    ).fetchone()
    conn.execute(
        "UPDATE entity_relationship SET source_evidence_item_id=?,evidence_span_id=?,"
        "dataset_version_id=?,dataset_observation_id=? WHERE entity_relationship_id=?",
        (*tuple(other), target),
    )
    conn.commit()
    changed = x3_fixture._manifest(
        conn,
        *x3_fixture._authoritative_x3_inputs(conn),  # noqa: SLF001
    )
    assert changed.fixture_digest == x3_manifest_digest(changed)

    assert not verify_x3_manifest(conn, changed)


def _reinsert_rows_reversed(conn: sqlite3.Connection, table: str, order_by: str) -> None:
    columns = tuple(row[1] for row in conn.execute(f"PRAGMA table_info({table})"))
    rows = conn.execute(f"SELECT * FROM {table} ORDER BY {order_by}").fetchall()
    insert_triggers = conn.execute(
        "SELECT name,sql FROM sqlite_master WHERE type='trigger' AND tbl_name=? "
        "AND lower(sql) LIKE '%before insert%' ORDER BY name",
        (table,),
    ).fetchall()
    for trigger in insert_triggers:
        conn.execute(f'DROP TRIGGER "{trigger[0]}"')
    _drop_immutable_trigger(conn, table, "delete")
    conn.execute(f"DELETE FROM {table}")
    placeholders = ",".join("?" for _ in columns)
    conn.executemany(
        f"INSERT INTO {table} ({','.join(columns)}) VALUES ({placeholders})",
        (tuple(row) for row in reversed(rows)),
    )
    for trigger in insert_triggers:
        conn.execute(trigger[1])
    conn.execute(
        f"CREATE TRIGGER immutable_delete_{table} BEFORE DELETE ON {table} "
        "BEGIN SELECT RAISE(ABORT,'immutable-record'); END"
    )


def test_x3_manifest_verifier_is_insertion_order_invariant() -> None:
    conn, manifest = _built()
    conn.commit()
    conn.execute("PRAGMA foreign_keys=OFF")
    _reinsert_rows_reversed(conn, "source_record", "source_record_id")
    _reinsert_rows_reversed(conn, "entity_mapping", "entity_mapping_id")
    _reinsert_rows_reversed(conn, "entity_relationship", "entity_relationship_id")
    _reinsert_rows_reversed(conn, "snapshot_manifest", "snapshot_digest")

    seals = conn.execute("SELECT * FROM receipt_seal ORDER BY receipt_id").fetchall()
    _drop_immutable_trigger(conn, "receipt_seal", "delete")
    conn.execute("DELETE FROM receipt_seal")
    conn.execute("DROP TRIGGER reject_sealed_receipt_reference")
    _reinsert_rows_reversed(conn, "receipt_reference", "receipt_id,ordinal")
    conn.executemany("INSERT INTO receipt_seal VALUES (?,?,?)", reversed(seals))
    conn.execute(
        "CREATE TRIGGER immutable_delete_receipt_seal BEFORE DELETE ON receipt_seal "
        "BEGIN SELECT RAISE(ABORT,'immutable-record'); END"
    )
    conn.execute(
        "CREATE TRIGGER reject_sealed_receipt_reference BEFORE INSERT ON receipt_reference "
        "WHEN EXISTS (SELECT 1 FROM receipt_seal WHERE receipt_id=NEW.receipt_id) "
        "BEGIN SELECT RAISE(ABORT,'receipt-sealed'); END"
    )
    conn.commit()
    conn.execute("PRAGMA foreign_keys=ON")

    assert conn.execute("PRAGMA foreign_key_check").fetchall() == []
    assert verify_x3_manifest(conn, manifest)


def test_x3_fixture_uses_current_d_and_no_real_names() -> None:
    conn, manifest = _built()
    assert manifest.current_attestation == "D"
    assert manifest.live_attestation_ceiling == "B"
    text = " ".join(
        row[0]
        for row in conn.execute(
            "SELECT canonical_name FROM canonical_entity WHERE entity_id LIKE '%:x3-%'"
        )
    ).lower()
    assert "synthetic" in manifest.disclosure.lower()
    assert "manager" not in text
    assert "fund" not in text


def _dump(conn: sqlite3.Connection, tables: tuple[str, ...]) -> tuple[tuple[str, tuple], ...]:
    out = []
    for table in tables:
        rows = conn.execute(f"SELECT * FROM {table} ORDER BY 1").fetchall()
        out.append((table, tuple(tuple(row) for row in rows)))
    return tuple(out)


def test_cutoffs_are_aware_utc() -> None:
    assert all(value.tzinfo is UTC for value in X3_CUTOFFS.values())
    assert X3_CUTOFFS["early"] == datetime(2024, 3, 31, 23, 59, 59, tzinfo=UTC)
