"""Deterministic shared evidence fixture for S7 track provenance."""

from __future__ import annotations

import sqlite3
import json
from dataclasses import dataclass, fields, replace
from datetime import UTC, datetime
from types import MappingProxyType
from typing import Any, Mapping, Sequence

from ..ingest import (
    expected_partition_manifest,
    ingest_dataset_delivery_partitions,
    ingest_dataset_observation_partition_links,
    ingest_dataset_observations,
    ingest_dataset_versions,
    ingest_datasets,
    ingest_items,
    ingest_payload_schemas,
    ingest_rights,
    ingest_source_records,
    ingest_spans,
    received_partition_manifest,
    reconstruction_manifest,
)
from ..model import (
    DatasetDeliveryPartitionRecord,
    DatasetObservationPartitionLinkRecord,
    DatasetObservationRecord,
    DatasetRecord,
    DatasetSliceRequest,
    DatasetVersionRecord,
    EvidenceItemRecord,
    EvidenceRightRecord,
    EvidenceSpanRecord,
    PayloadSchemaRecord,
    SnapshotBundle,
    SourceRecordRecord,
    canonical_bytes,
    machine_id,
    sha256,
    with_machine_id,
)
from .x3 import X3_CUTOFFS

S7_FIXTURE_ID = "s7_evidence_v1"
S7_AUTHORED_CLOSURE_CONTRACT_VERSION = "s7-authored-closure-v1"
S7_SCHEMA_SHA256 = "43a0f22036e3e6b55fc15a05071e58d7771ff5546cedce7c4ee45155f38b0818"
S7_SCENARIOS = ("public-equity", "hedge-fund", "credit", "private-market")
S7_DATASET_IDS = (
    "dataset:s7-public-registered",
    "dataset:s7-hedge-composite",
    "dataset:s7-credit-lineage",
    "dataset:s7-private-cashflow-nav",
    "dataset:s7-fx",
    "dataset:s7-benchmark",
    "dataset:s7-lineage-terms",
    "dataset:s7-method-boundary",
)
S7_CUTOFFS = MappingProxyType({"early": X3_CUTOFFS["early"], "latest": X3_CUTOFFS["latest"]})

_SCENARIO_DATASETS = {
    "public-equity": (
        "dataset:s7-public-registered",
        "dataset:s7-fx",
        "dataset:s7-benchmark",
    ),
    "hedge-fund": ("dataset:s7-hedge-composite", "dataset:s7-lineage-terms"),
    "credit": ("dataset:s7-credit-lineage",),
    "private-market": ("dataset:s7-private-cashflow-nav",),
}

_MANIFEST_SCHEMA_ID = "schema:s7-delivery-manifest-v1"
_MANIFEST_FIELDS = ("dataset_id", "record_count", "version_label")
_S7_JOIN_KEYS = ("field_dictionary_version",)
S7_RELATIONSHIP_FIELDS = (
    "relationship_key",
    "relation_type",
    "source_entity_id",
    "target_entity_id",
    "effective_from",
    "effective_to",
    "assertion",
    "scope",
)
_S7_PROVISIONAL_PATH_SPECS = MappingProxyType(
    {
        "public-equity": (
            ("s7-public-path-offers", "offers", "manager:x3-00", "strategy:x3-00"),
            (
                "s7-public-path-reported",
                "reported_through",
                "strategy:x3-00",
                "composite:x3-00",
            ),
            (
                "s7-public-path-implemented",
                "implemented_by",
                "composite:x3-00",
                "vehicle:x3-00",
            ),
            (
                "s7-public-path-legal",
                "legal_identity",
                "adviser:x3-00",
                "legal-entity:x3-00",
            ),
        ),
        "hedge-fund": (
            ("s7-hedge-path-offers", "offers", "manager:x3-00", "strategy:x3-00"),
            (
                "s7-hedge-path-reported",
                "reported_through",
                "strategy:x3-00",
                "composite:x3-00",
            ),
            (
                "s7-hedge-path-legal",
                "legal_identity",
                "adviser:x3-00",
                "legal-entity:x3-00",
            ),
        ),
        "credit": (
            ("s7-credit-path-offers", "offers", "manager:x3-01", "strategy:x3-04"),
            (
                "s7-credit-path-advised",
                "advised_by",
                "manager:x3-01",
                "adviser:x3-01",
            ),
            (
                "s7-credit-path-legal",
                "legal_identity",
                "adviser:x3-01",
                "legal-entity:x3-01",
            ),
        ),
        "private-market": (
            ("s7-private-path-offers", "offers", "manager:x3-02", "strategy:x3-08"),
            (
                "s7-private-path-reported",
                "reported_through",
                "strategy:x3-08",
                "composite:x3-08",
            ),
            (
                "s7-private-path-implemented",
                "implemented_by",
                "composite:x3-08",
                "vehicle:x3-08",
            ),
            (
                "s7-private-path-advised",
                "advised_by",
                "manager:x3-02",
                "adviser:x3-02",
            ),
            (
                "s7-private-path-legal",
                "legal_identity",
                "adviser:x3-02",
                "legal-entity:x3-02",
            ),
        ),
    }
)


def s7_provisional_relationship_items(
    scenario: str, available_at: datetime
) -> tuple[dict[str, object], ...]:
    """Return the immutable scenario-owned early lineage bridge as fixture items."""

    try:
        specs = _S7_PROVISIONAL_PATH_SPECS[scenario]
    except KeyError as exc:
        raise ValueError("s7-unknown-scenario") from exc
    effective_from = datetime(2024, 1, 1, tzinfo=UTC)
    scope = f"provisional-lineage:{scenario}"
    return tuple(
        {
            "source_key": key,
            "record_kind": "s7-relationship-evidence",
            "payload": dict(
                zip(
                    S7_RELATIONSHIP_FIELDS,
                    (
                        key,
                        relation_type,
                        source_entity_id,
                        target_entity_id,
                        "2024-01-01T00:00:00Z",
                        "",
                        (
                            f"S7 {scenario} evidence provisionally links "
                            f"{source_entity_id} to {target_entity_id}."
                        ),
                        scope,
                    ),
                    strict=True,
                )
            ),
            "available_at": available_at,
            "effective_from": effective_from,
            "temporal_type": "interval",
            "source_entity_type": "relationship",
        }
        for key, relation_type, source_entity_id, target_entity_id in specs
    )


def _strict_schema(schema_id: str, record_kind: str, field_names: Sequence[str]):
    schema = {
        "type": "object",
        "required": list(field_names),
        "properties": {name: {"type": "string"} for name in field_names},
        "additionalProperties": False,
    }
    return PayloadSchemaRecord(schema_id, record_kind, schema, sha256(canonical_bytes(schema)))


def _value_span(item_id: str, payload: Mapping[str, str], field_name: str) -> EvidenceSpanRecord:
    value = payload[field_name]
    start = 0
    end = len(value)
    return with_machine_id(
        "span",
        EvidenceSpanRecord("", item_id, f"/{field_name}", start, end, sha256(value.encode())),
    )


def _s7_right_id(dataset_id: str, access_context: str, licence_purpose: str) -> str:
    at = datetime(2024, 1, 1, tzinfo=UTC)
    return machine_id(
        "right",
        {
            "right_series_id": f"right-series:{dataset_id.removeprefix('dataset:')}",
            "right_version": 1,
            "dataset_id": dataset_id,
            "access_context": access_context,
            "licence_purpose": licence_purpose,
            "status": "active",
            "retention_policy": "retain-after-expiry",
            "received_at_utc": at,
            "entitlement_from": at,
            "entitlement_to": None,
            "supersedes_right_id": None,
        },
    )


def _ingest_s7_dataset(
    conn: sqlite3.Connection,
    *,
    dataset_id: str,
    label: str,
    source_system: str,
    availability_policy: str,
    access_context: str,
    licence_purpose: str,
    schemas: Sequence[tuple[str, str, tuple[str, ...]]],
    items: Sequence[Mapping[str, Any]],
    versions: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Ingest one strict S7 dataset and return its stable persisted handles."""

    ingest_datasets(
        conn,
        [
            DatasetRecord(
                dataset_id,
                label,
                source_system,
                availability_policy,
                "s7-v1",
                "synthetic",
                licence_purpose,
            )
        ],
    )
    right_id = _s7_right_id(dataset_id, access_context, licence_purpose)
    at = datetime(2024, 1, 1, tzinfo=UTC)
    ingest_rights(
        conn,
        [
            EvidenceRightRecord(
                right_id,
                f"right-series:{dataset_id.removeprefix('dataset:')}",
                1,
                dataset_id,
                access_context,
                licence_purpose,
                "active",
                "retain-after-expiry",
                at,
                at,
                None,
            )
        ],
    )
    schema_rows = [_strict_schema(*schema) for schema in schemas]
    schema_rows.append(_strict_schema(_MANIFEST_SCHEMA_ID, "s7-delivery-manifest", _MANIFEST_FIELDS))
    ingest_payload_schemas(conn, schema_rows)
    schema_by_kind = {record_kind: schema_id for schema_id, record_kind, _ in schemas}
    fields_by_kind = {record_kind: field_names for _, record_kind, field_names in schemas}

    source_specs = {(str(row["source_key"]), str(row.get("source_entity_type", "product"))) for row in items}
    source_specs.add(("s7-manifest", "document"))
    sources = [
        with_machine_id(
            "source-record", SourceRecordRecord("", dataset_id, source_system, key, entity_type)
        )
        for key, entity_type in sorted(source_specs)
    ]
    ingest_source_records(conn, sources)
    source_by_key = {row.source_record_key: row for row in sources}

    item_rows: list[EvidenceItemRecord] = []
    item_by_key_version: dict[tuple[str, int], EvidenceItemRecord] = {}
    for spec in sorted(items, key=lambda row: (str(row["source_key"]), int(row.get("version", 1)))):
        source_key = str(spec["source_key"])
        item_version = int(spec.get("version", 1))
        payload = dict(spec["payload"])
        record_kind = str(spec["record_kind"])
        if set(payload) != set(fields_by_kind[record_kind]) or not all(
            isinstance(value, str) for value in payload.values()
        ):
            raise ValueError("s7-strict-payload-mismatch")
        available_at = spec["available_at"]
        prior = item_by_key_version.get((source_key, item_version - 1))
        item = with_machine_id(
            "evidence",
            EvidenceItemRecord(
                "",
                right_id,
                source_by_key[source_key].source_record_id,
                sha256(canonical_bytes(payload)),
                record_kind,
                schema_by_kind[record_kind],
                str(spec.get("temporal_type", "point")),
                spec.get("effective_at"),
                spec.get("effective_from"),
                spec.get("effective_to"),
                spec.get("as_of_date", available_at.date()),
                available_at if availability_policy == "public-publication" else None,
                available_at if availability_policy == "public-publication" else None,
                available_at,
                None,
                item_version,
                prior.evidence_item_id if prior else None,
                "received",
                access_context,
                "s7-v1",
                "synthetic",
                licence_purpose,
                payload,
                canonical_entity_type=spec.get("canonical_entity_type"),
                canonical_entity_id=spec.get("canonical_entity_id"),
                manager_id=spec.get("manager_id"),
                strategy_id=spec.get("strategy_id"),
                composite_id=spec.get("composite_id"),
                vehicle_id=spec.get("vehicle_id"),
                base_currency=spec.get("base_currency"),
                gross_net_fee_basis=spec.get("gross_net_fee_basis"),
                valuation_policy_id=spec.get("valuation_policy_id"),
                benchmark_id=spec.get("benchmark_id"),
                benchmark_version=spec.get("benchmark_version"),
            ),
        )
        item_rows.append(item)
        item_by_key_version[(source_key, item_version)] = item

    manifest_items: dict[str, EvidenceItemRecord] = {}
    for index, version_spec in enumerate(versions, 1):
        payload = {
            "dataset_id": dataset_id,
            "record_count": str(len(version_spec["observations"])),
            "version_label": str(version_spec["version_label"]),
        }
        prior = manifest_items.get(str(versions[index - 2]["version_label"])) if index > 1 else None
        available_at = version_spec["available_at"]
        manifest = with_machine_id(
            "evidence",
            EvidenceItemRecord(
                "",
                right_id,
                source_by_key["s7-manifest"].source_record_id,
                sha256(canonical_bytes(payload)),
                "s7-delivery-manifest",
                _MANIFEST_SCHEMA_ID,
                "point",
                available_at,
                None,
                None,
                available_at.date(),
                available_at if availability_policy == "public-publication" else None,
                available_at if availability_policy == "public-publication" else None,
                available_at,
                None,
                index,
                prior.evidence_item_id if prior else None,
                "received",
                access_context,
                "s7-v1",
                "synthetic",
                licence_purpose,
                payload,
            ),
        )
        manifest_items[str(version_spec["version_label"])] = manifest
        item_rows.append(manifest)
    ingest_items(conn, item_rows)

    spans = []
    for item in item_rows:
        payload = dict(item.payload)
        spans.extend(_value_span(item.evidence_item_id, payload, name) for name in payload)
    ingest_spans(conn, spans)
    spans_by_item_field = {(span.evidence_item_id, span.json_pointer): span for span in spans}

    version_rows: list[DatasetVersionRecord] = []
    observations_by_version: dict[str, list[DatasetObservationRecord]] = {}
    materialized_by_version: dict[str, dict[str, dict[str, str]]] = {}
    prior_version: DatasetVersionRecord | None = None
    base_version: DatasetVersionRecord | None = None
    for version_spec in versions:
        label_value = str(version_spec["version_label"])
        # Dataset-observation IDs depend on the version ID, while the version digest depends on
        # the final reconstruction rows. Compute the version from item identities first.
        previous_materialized = (
            dict(materialized_by_version[prior_version.version_label])
            if prior_version is not None and version_spec["delivery_mode"] == "delta"
            else {}
        )
        for source_key, item_version, status, _ in version_spec["observations"]:
            source_id = source_by_key[source_key].source_record_id
            item_id = item_by_key_version[(source_key, item_version)].evidence_item_id
            if status == "explicitly-removed":
                previous_materialized.pop(source_id, None)
            else:
                previous_materialized[source_id] = {
                    "source_record_id": source_id,
                    "evidence_item_id": item_id,
                    "observation_status": "present",
                }
        materialized = tuple(previous_materialized[key] for key in sorted(previous_materialized))
        partitions = [
            {
                "partition_key": "all",
                "partition_status": "expected-received",
                "expected_record_count": len(version_spec["observations"]),
                "received_record_count": len(version_spec["observations"]),
                "received_content_sha256": sha256(canonical_bytes(version_spec["observations"])),
            }
        ]
        available_at = version_spec["available_at"]
        version = with_machine_id(
            "dataset-version",
            DatasetVersionRecord(
                "",
                dataset_id,
                label_value,
                right_id,
                available_at if availability_policy == "public-publication" else None,
                available_at if availability_policy == "public-publication" else None,
                available_at,
                None,
                sha256(canonical_bytes(materialized)),
                str(version_spec["delivery_mode"]),
                str(version_spec["absence_semantics"]),
                "complete",
                expected_partition_manifest(partitions),
                received_partition_manifest(partitions),
                1,
                1,
                reconstruction_manifest(materialized),
                len(materialized),
                prior_version.dataset_version_id if prior_version else None,
                base_version.dataset_version_id if version_spec["delivery_mode"] == "delta" else None,
            ),
        )
        if base_version is None or version_spec["delivery_mode"] == "full-snapshot":
            base_version = version
        # Rebuild observations with the real version ID.
        real_observations = []
        for source_key, item_version, status, reason in version_spec["observations"]:
            item = item_by_key_version[(source_key, item_version)]
            real_observations.append(
                with_machine_id(
                    "dataset-observation",
                    DatasetObservationRecord("", version.dataset_version_id, item.evidence_item_id, status, reason),
                )
            )
        version_rows.append(version)
        observations_by_version[label_value] = real_observations
        materialized_by_version[label_value] = previous_materialized
        prior_version = version
    ingest_dataset_versions(conn, version_rows)

    all_observations = [row for rows in observations_by_version.values() for row in rows]
    ingest_dataset_observations(conn, all_observations)
    partitions = []
    links = []
    for version, version_spec in zip(version_rows, versions, strict=True):
        manifest = manifest_items[version.version_label]
        manifest_span = spans_by_item_field[(manifest.evidence_item_id, "/version_label")]
        received_hash = sha256(canonical_bytes(version_spec["observations"]))
        partition = with_machine_id(
            "dataset-partition",
            DatasetDeliveryPartitionRecord(
                "",
                version.dataset_version_id,
                "all",
                "expected-received",
                manifest.evidence_item_id,
                manifest_span.evidence_span_id,
                received_hash,
                len(version_spec["observations"]),
                len(version_spec["observations"]),
            ),
        )
        partitions.append(partition)
        for observation in observations_by_version[version.version_label]:
            links.append(
                with_machine_id(
                    "dataset-observation-partition",
                    DatasetObservationPartitionLinkRecord(
                        "", observation.dataset_observation_id, partition.dataset_delivery_partition_id
                    ),
                )
            )
    ingest_dataset_delivery_partitions(conn, partitions)
    ingest_dataset_observation_partition_links(conn, links)
    return {
        "dataset_id": dataset_id,
        "right_id": right_id,
        "schemas": tuple(schema_rows),
        "sources": tuple(sources),
        "items": tuple(item_rows),
        "spans": tuple(spans),
        "versions": tuple(version_rows),
        "observations": tuple(all_observations),
        "partitions": tuple(partitions),
        "links": tuple(links),
    }


@dataclass(frozen=True, slots=True)
class S7MethodPolicyEvidence:
    policy_id: str
    dataset_id: str
    payload_schema_id: str
    payload_schema_sha256: str
    item_id: str
    span_id: str
    observation_id: str
    version_id: str
    right_id: str
    snapshot_digest: str
    slice_receipt_id: str
    bundle_digest: str
    join_receipt_id: str
    payload_sha256: str


@dataclass(frozen=True, slots=True)
class S7ScenarioContract:
    scenario: str
    dataset_ids: tuple[str, ...]
    canonical_product_ids: tuple[str, ...]
    source_record_ids: tuple[str, ...]
    mapping_ids: tuple[str, ...]
    membership_ids: tuple[str, ...]
    source_statuses: tuple[tuple[str, str], ...]
    observation_membership_link_ids: tuple[str, ...]
    relationship_ids: tuple[str, ...]
    death_evidence_item_ids: tuple[str, ...]
    death_evidence_span_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class S7BundleContract:
    scenario: str
    cutoff_name: str
    analytic_slice_digests: tuple[tuple[str, str], ...]
    audit_slice_digests: tuple[tuple[str, str], ...]
    analytic_slice_receipt_ids: tuple[tuple[str, str], ...]
    audit_slice_receipt_ids: tuple[tuple[str, str], ...]
    analytic_bundle_digest: str
    audit_bundle_digest: str
    analytic_join_receipt_id: str
    audit_join_receipt_id: str


@dataclass(frozen=True, slots=True)
class S7FixtureManifest:
    fixture_id: str
    fixture_digest: str
    closure_digest: str
    schema_version: int
    schema_digest: str
    x3_fixture_digest: str
    dataset_ids: tuple[str, ...]
    payload_schema_digests: tuple[tuple[str, str], ...]
    source_record_records: tuple[tuple[object, ...], ...]
    item_records: tuple[tuple[object, ...], ...]
    span_records: tuple[tuple[object, ...], ...]
    right_records: tuple[tuple[object, ...], ...]
    version_records: tuple[tuple[object, ...], ...]
    partition_records: tuple[tuple[object, ...], ...]
    observation_records: tuple[tuple[object, ...], ...]
    mapping_records: tuple[tuple[object, ...], ...]
    observation_membership_link_records: tuple[tuple[object, ...], ...]
    relationship_records: tuple[tuple[object, ...], ...]
    receipt_ids: tuple[str, ...]
    scenario_contracts: tuple[S7ScenarioContract, ...]
    bundle_contracts: tuple[S7BundleContract, ...]
    policy: S7MethodPolicyEvidence
    limitation_codes: tuple[str, ...]


def s7_manifest_payload(manifest: S7FixtureManifest) -> dict[str, object]:
    return {field.name: getattr(manifest, field.name) for field in fields(manifest) if field.name != "fixture_digest"}


def s7_manifest_digest(manifest: S7FixtureManifest) -> str:
    return sha256(canonical_bytes(s7_manifest_payload(manifest)))


def _normalize_s7_time(value: str) -> str:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).isoformat(
        timespec="microseconds"
    ).replace("+00:00", "Z")


def _x3_membership_for(
    conn: sqlite3.Connection,
    x3_manifest,
    *,
    canonical_entity_id: str,
    cutoff_name: str,
    source_key: str | None = None,
):
    from ..projections import project_entity_mappings, project_universe_memberships
    from ..snapshot import as_known_slice
    from ..universe import require_member

    entity_type = canonical_entity_id.split(":", 1)[0]
    dataset_id = {
        "vehicle": "dataset:x3-registered-fund",
        "composite": "dataset:x3-strategy-export",
        "strategy": "dataset:x3-rfi-ddq",
    }[entity_type]
    cutoff = S7_CUTOFFS[cutoff_name]
    request = DatasetSliceRequest(
        dataset_id,
        x3_manifest.access_contexts[dataset_id],
        x3_manifest.right_ids[dataset_id],
        "x3-research",
        valid_at=cutoff,
    )
    conn.execute("SAVEPOINT s7_x3_projection")
    try:
        snapshot = as_known_slice(conn, decision_at=cutoff, request=request)
        projected_mappings = tuple(project_entity_mappings(conn, snapshot))
        projected_memberships = tuple(project_universe_memberships(conn, snapshot))
    finally:
        conn.execute("ROLLBACK TO s7_x3_projection")
        conn.execute("RELEASE s7_x3_projection")
    mappings = {
        row["entity_mapping_id"]: row for row in projected_mappings
    }
    candidates = []
    for membership in projected_memberships:
        mapping = mappings.get(membership["entity_mapping_id"])
        if mapping is None or mapping["canonical_entity_id"] != canonical_entity_id:
            continue
        if source_key is not None and mapping["source_key"] != source_key:
            continue
        candidates.append((membership, mapping))
    if not candidates:
        raise ValueError("s7-x3-membership-not-visible")
    membership, mapping = min(candidates, key=lambda pair: pair[0]["universe_membership_id"])
    found = require_member(
        conn,
        universe_membership_id=membership["universe_membership_id"],
        slice_request=request,
        decision_at=cutoff,
        valid_at=cutoff,
    )
    if found != canonical_entity_id:
        raise ValueError("s7-x3-membership-product-mismatch")
    payload = json.loads(
        conn.execute(
            "SELECT payload_json FROM evidence_item WHERE evidence_item_id=?",
            (membership["source_evidence_item_id"],),
        ).fetchone()[0]
    )
    status = payload.get("product_status", "unknown")
    if status not in {"active", "inactive", "closed", "unknown"}:
        status = "unknown"
    return membership, mapping, status


def _insert_s7_relationships(conn: sqlite3.Connection) -> tuple[str, ...]:
    conn.executemany(
        "INSERT OR IGNORE INTO canonical_entity VALUES (?,?,?,?,?,?,?,?)",
        (
            (
                "person:s7-lead",
                "person",
                "S7 Fictional Lead",
                None,
                "interval",
                None,
                "2020-01-01T00:00:00.000000Z",
                None,
            ),
            (
                "person:s7-support",
                "person",
                "S7 Fictional Support",
                None,
                "interval",
                None,
                "2020-01-01T00:00:00.000000Z",
                None,
            ),
        ),
    )
    relationship_dataset_ids = (
        "dataset:s7-public-registered",
        "dataset:s7-credit-lineage",
        "dataset:s7-private-cashflow-nav",
        "dataset:s7-lineage-terms",
    )
    placeholders = ",".join("?" for _ in relationship_dataset_ids)
    rows = conn.execute(
        "SELECT i.evidence_item_id,i.payload_json,i.version,sp.evidence_span_id,"
        "o.dataset_observation_id,o.dataset_version_id,s.dataset_id FROM evidence_item i "
        "JOIN source_record s ON s.source_record_id=i.source_record_id "
        "JOIN evidence_span sp ON sp.evidence_item_id=i.evidence_item_id "
        "JOIN dataset_observation o ON o.evidence_item_id=i.evidence_item_id "
        "JOIN dataset_version v ON v.dataset_version_id=o.dataset_version_id "
        "WHERE i.record_kind='s7-relationship-evidence' AND sp.json_pointer='/assertion' "
        f"AND s.dataset_id IN ({placeholders}) AND v.dataset_id=s.dataset_id "
        "AND v.version_label='early' ORDER BY s.dataset_id,i.evidence_item_id",
        relationship_dataset_ids,
    ).fetchall()
    expected_dataset_counts = {
        "dataset:s7-public-registered": 4,
        "dataset:s7-credit-lineage": 3,
        "dataset:s7-private-cashflow-nav": 5,
        "dataset:s7-lineage-terms": 12,
    }
    actual_dataset_counts = {
        dataset_id: sum(row["dataset_id"] == dataset_id for row in rows)
        for dataset_id in relationship_dataset_ids
    }
    if actual_dataset_counts != expected_dataset_counts:
        raise ValueError("s7-relationship-source-closure-mismatch")
    relationship_ids = []
    for row in rows:
        payload = json.loads(row["payload_json"])
        is_point = payload["relation_type"] in {"predecessor_claim", "contradicts_transfer"}
        effective_at = _normalize_s7_time(payload["effective_from"]) if is_point else None
        effective_from = None if is_point else _normalize_s7_time(payload["effective_from"])
        effective_to = (
            None
            if is_point or not payload["effective_to"]
            else _normalize_s7_time(payload["effective_to"])
        )
        temporal_type = "point" if is_point else "interval"
        identity = {
            "source_evidence_item_id": row["evidence_item_id"],
            "relation_type": payload["relation_type"],
            "source_entity_id": payload["source_entity_id"],
            "target_entity_id": payload["target_entity_id"],
            "temporal_type": temporal_type,
            "effective_at": effective_at,
            "effective_from": effective_from,
            "effective_to": effective_to,
            "version": row["version"],
        }
        relationship_id = machine_id("entity-relation", identity)
        relationship_record = (
            relationship_id,
            row["evidence_item_id"],
            row["evidence_span_id"],
            row["dataset_version_id"],
            row["dataset_observation_id"],
            payload["relation_type"],
            payload["source_entity_id"],
            payload["target_entity_id"],
            temporal_type,
            effective_at,
            effective_from,
            effective_to,
            row["version"],
            None,
        )
        if not conn.execute(
            "SELECT 1 FROM entity_relationship WHERE entity_relationship_id=?",
            (relationship_id,),
        ).fetchone():
            conn.execute(
                "INSERT INTO entity_relationship VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                relationship_record,
            )
        relationship_ids.append(relationship_id)
    if len(relationship_ids) != 24:
        raise ValueError("s7-relationship-closure-mismatch")
    return tuple(sorted(relationship_ids))


def _close_s7_projection_links(conn: sqlite3.Connection, x3_manifest):
    """Bind S7 product observations to reviewed X3 memberships and S7 relationships."""

    from .terms import build_s7_death_bundle, build_s7_terms_sources

    product_kinds = (
        "s7-periodic-return",
        "s7-credit-return",
        "s7-private-cashflow",
        "s7-private-nav",
    )
    placeholders = ",".join("?" for _ in product_kinds)
    rows = conn.execute(
        f"SELECT s.dataset_id,s.source_record_id,s.source_record_key,i.evidence_item_id,"
        f"i.payload_json,i.version AS item_version,i.temporal_type,i.effective_at,"
        f"o.dataset_observation_id,o.observation_status,v.dataset_version_id,v.version_label,"
        f"coalesce(v.published_at,v.first_observed_at_utc,v.received_at_utc) AS available_at "
        f"FROM dataset_observation o JOIN dataset_version v USING(dataset_version_id) "
        f"JOIN evidence_item i USING(evidence_item_id) JOIN source_record s USING(source_record_id) "
        f"WHERE s.dataset_id LIKE 'dataset:s7-%' AND i.record_kind IN ({placeholders}) "
        f"AND o.observation_status='present' ORDER BY s.dataset_id,s.source_record_key,"
        f"available_at,i.version,o.dataset_observation_id",
        product_kinds,
    ).fetchall()
    mapping_rows = []
    link_rows = []
    statuses_by_scenario: dict[str, set[tuple[str, str]]] = {
        scenario: set() for scenario in S7_SCENARIOS
    }
    membership_ids_by_scenario: dict[str, set[str]] = {
        scenario: set() for scenario in S7_SCENARIOS
    }
    dataset_scenario = {
        dataset_id: scenario
        for scenario, dataset_ids in _SCENARIO_DATASETS.items()
        for dataset_id in dataset_ids
    }
    for row in rows:
        scenario = dataset_scenario[row["dataset_id"]]
        payload = json.loads(row["payload_json"])
        source_label = payload["source_product_key"]
        source_key = row["source_record_key"]
        if source_key == "s7-hf-ambiguous":
            canonical_id = None
            mapping_status = "ambiguous"
            candidates = canonical_bytes(("composite:x3-00", "composite:x3-01")).decode()
            rule = "label-collision"
        elif source_key == "s7-null-same-label":
            canonical_id = None
            mapping_status = "unresolved"
            candidates = canonical_bytes(()).decode()
            rule = "null-canonical-key"
        else:
            canonical_id = {
                "public-equity": "vehicle:x3-00",
                "hedge-fund": (
                    "composite:x3-01"
                    if source_key == "s7-hf-overlap"
                    else (
                        "composite:x3-03"
                        if source_key == "s7-hf-retro-member"
                        else (
                            "composite:x3-02"
                            if source_key == "s7-hf-closed:2023-12"
                            else "composite:x3-00"
                        )
                    )
                ),
                "credit": "strategy:x3-04",
                "private-market": "vehicle:x3-08",
            }[scenario]
            mapping_status = "resolved"
            candidates = canonical_bytes(()).decode()
            rule = "s7-reviewed-exact"
        span = conn.execute(
            "SELECT evidence_span_id FROM evidence_span WHERE evidence_item_id=? "
            "AND json_pointer='/source_product_key'",
            (row["evidence_item_id"],),
        ).fetchone()
        if span is None:
            raise ValueError("s7-product-key-span-missing")
        projection_version = 1
        identity = {
            "source_evidence_item_id": row["evidence_item_id"],
            "source_key": source_key,
            "source_label": source_label,
            "taxonomy_version": "x3-taxonomy-v1",
            "version": projection_version,
            "candidate_entity_ids_json": candidates,
        }
        mapping_id = machine_id("mapping", identity)
        mapping_rows.append(
            (
                mapping_id,
                row["evidence_item_id"],
                span[0],
                row["dataset_version_id"],
                row["dataset_observation_id"],
                source_key,
                source_label,
                canonical_id.split(":", 1)[0] if canonical_id else "product",
                canonical_id,
                mapping_status,
                candidates,
                rule,
                "x3-taxonomy-v1",
                row["temporal_type"],
                row["effective_at"],
                None,
                None,
                projection_version,
                None,
            )
        )
        if mapping_status != "resolved":
            continue
        cutoff_name = (
            "latest"
            if source_key == "s7-hf-retro-member"
            or row["available_at"] > _normalize_s7_time("2024-03-31T23:59:59Z")
            else "early"
        )
        membership, _, source_status = _x3_membership_for(
            conn,
            x3_manifest,
            canonical_entity_id=canonical_id,
            cutoff_name=cutoff_name,
            source_key="x3-source-0003" if source_key == "s7-hf-retro-member" else None,
        )
        link_id = machine_id(
            "observation-membership",
            {
                "dataset_observation_id": row["dataset_observation_id"],
                "universe_membership_id": membership["universe_membership_id"],
            },
        )
        link_rows.append(
            (link_id, row["dataset_observation_id"], membership["universe_membership_id"])
        )
        statuses_by_scenario[scenario].add((canonical_id, source_status))
        membership_ids_by_scenario[scenario].add(membership["universe_membership_id"])
    existing_mapping_ids = {
        row[0]
        for row in conn.execute(
            "SELECT entity_mapping_id FROM entity_mapping WHERE source_key LIKE 's7-%'"
        )
    }
    conn.executemany(
        "INSERT INTO entity_mapping VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (row for row in mapping_rows if row[0] not in existing_mapping_ids),
    )
    conn.executemany(
        "INSERT OR IGNORE INTO observation_membership_link VALUES (?,?,?)", link_rows
    )

    closed_observation_id = next(
        row["dataset_observation_id"]
        for row in rows
        if row["source_record_key"] == "s7-hf-closed:2023-12"
    )
    build_s7_terms_sources(conn, death_observation_id=closed_observation_id)
    build_s7_death_bundle(conn)
    relationship_ids = _insert_s7_relationships(conn)
    relationship_dataset_by_id = {
        str(row["entity_relationship_id"]): str(row["dataset_id"])
        for row in conn.execute(
            "SELECT r.entity_relationship_id,s.dataset_id FROM entity_relationship r "
            "JOIN evidence_item i ON i.evidence_item_id=r.source_evidence_item_id "
            "JOIN source_record s ON s.source_record_id=i.source_record_id "
            "WHERE i.record_kind='s7-relationship-evidence'"
        )
    }
    death = conn.execute(
        "SELECT i.evidence_item_id,sp.evidence_span_id FROM evidence_item i "
        "JOIN evidence_span sp USING(evidence_item_id) WHERE i.record_kind='s7-death-evidence' "
        "AND sp.json_pointer='/reason_code'"
    ).fetchone()

    contracts = []
    for scenario in S7_SCENARIOS:
        dataset_ids = _SCENARIO_DATASETS[scenario]
        scenario_mappings = [
            row for row in mapping_rows if row[0] and row[3] and row[5] and row[4]
            and conn.execute(
                "SELECT dataset_id FROM dataset_version WHERE dataset_version_id=?", (row[3],)
            ).fetchone()[0] in dataset_ids
        ]
        scenario_observation_ids = {row[4] for row in scenario_mappings}
        scenario_links = [row for row in link_rows if row[1] in scenario_observation_ids]
        contracts.append(
            S7ScenarioContract(
                scenario,
                dataset_ids,
                tuple(sorted({row[8] for row in scenario_mappings if row[8]})),
                tuple(
                    sorted(
                        {
                            conn.execute(
                                "SELECT source_record_id FROM evidence_item WHERE evidence_item_id=?",
                                (row[1],),
                            ).fetchone()[0]
                            for row in scenario_mappings
                        }
                    )
                ),
                tuple(sorted(row[0] for row in scenario_mappings)),
                tuple(sorted(membership_ids_by_scenario[scenario])),
                tuple(sorted(statuses_by_scenario[scenario])),
                tuple(sorted(row[0] for row in scenario_links)),
                tuple(
                    sorted(
                        relationship_id
                        for relationship_id in relationship_ids
                        if relationship_dataset_by_id[relationship_id] in dataset_ids
                    )
                ),
                (death[0],) if scenario == "hedge-fund" else (),
                (death[1],) if scenario == "hedge-fund" else (),
            )
        )
    return tuple(contracts)


def build_s7_fixture(conn: sqlite3.Connection) -> S7FixtureManifest:
    conn.execute("SAVEPOINT build_s7_fixture")
    try:
        manifest = _build_s7_fixture(conn)
        conn.execute("RELEASE build_s7_fixture")
        return manifest
    except Exception:
        conn.execute("ROLLBACK TO build_s7_fixture")
        conn.execute("RELEASE build_s7_fixture")
        raise


def verify_s7_manifest(conn: sqlite3.Connection, manifest: S7FixtureManifest) -> bool:
    from ..checks import EvidenceRefusal
    from ..schema import connect, initialize
    from .x3 import build_x3_fixture, verify_x3_manifest

    pristine = None
    try:
        if (
            not isinstance(manifest, S7FixtureManifest)
            or manifest.fixture_digest != s7_manifest_digest(manifest)
            or manifest.schema_version != 1
            or type(manifest.schema_version) is not int
            or manifest.schema_digest != S7_SCHEMA_SHA256
            or manifest.dataset_ids != S7_DATASET_IDS
        ):
            return False
        pristine = connect()
        initialize(pristine)
        expected = _build_s7_fixture(pristine)
        if manifest != expected or s7_authored_closure_digest(conn) != expected.closure_digest:
            return False
        x3_manifest = build_x3_fixture(conn)
        if (
            x3_manifest.fixture_digest != manifest.x3_fixture_digest
            or not verify_x3_manifest(conn, x3_manifest)
            or not _s7_manifest_records_match(conn, manifest)
        ):
            return False
        s7_policy_bundle(conn, manifest)
        for contract in manifest.bundle_contracts:
            if _materialize_bundle_contract(conn, manifest, contract.scenario, contract.cutoff_name) != contract:
                return False
        return True
    except (EvidenceRefusal, sqlite3.Error, KeyError, TypeError, ValueError, AssertionError):
        return False
    finally:
        if pristine is not None:
            pristine.close()


def s7_authored_closure_digest(conn: sqlite3.Connection) -> str:
    return sha256(canonical_bytes(_s7_authored_closure_payload(conn)))


def s7_source_requests(
    manifest: S7FixtureManifest,
    *,
    scenario: str,
    cutoff_name: str,
    revision_mode: str,
) -> tuple[DatasetSliceRequest, ...]:
    if scenario not in S7_SCENARIOS:
        raise ValueError("s7-unknown-scenario")
    if cutoff_name not in S7_CUTOFFS:
        raise ValueError("s7-unknown-cutoff")
    if revision_mode not in {"latest-known", "all-known-versions"}:
        raise ValueError("s7-unknown-revision-mode")
    if not isinstance(manifest, S7FixtureManifest):
        raise TypeError("s7-manifest-required")
    rights = {row[3]: row for row in manifest.right_records}
    try:
        return tuple(
            DatasetSliceRequest(
                dataset_id,
                rights[dataset_id][4],
                rights[dataset_id][0],
                rights[dataset_id][5],
                revision_mode=revision_mode,
                include_unresolved=True,
            )
            for dataset_id in _SCENARIO_DATASETS[scenario]
        )
    except (KeyError, IndexError) as exc:
        raise ValueError("s7-manifest-right-mismatch") from exc


def s7_policy_bundle(conn: sqlite3.Connection, manifest: S7FixtureManifest) -> SnapshotBundle:
    from ..lineage import resolve_span, verify_receipt
    from ..model import SnapshotBundleRequest
    from ..snapshot import as_known_bundle

    if not isinstance(manifest, S7FixtureManifest):
        raise TypeError("s7-manifest-required")
    policy = manifest.policy
    request = DatasetSliceRequest(
        "dataset:s7-method-boundary",
        "public",
        policy.right_id,
        "s7-research",
        revision_mode="latest-known",
        include_unresolved=True,
    )
    bundle = as_known_bundle(
        conn,
        SnapshotBundleRequest(
            S7_CUTOFFS["latest"],
            (request,),
            ("evidence_item_id",),
            "s7-method-policy-v1",
        ),
    )
    item = conn.execute(
        "SELECT i.*,s.dataset_id FROM evidence_item i JOIN source_record s USING(source_record_id) "
        "WHERE i.evidence_item_id=?",
        (policy.item_id,),
    ).fetchone()
    span = conn.execute(
        "SELECT * FROM evidence_span WHERE evidence_span_id=?", (policy.span_id,)
    ).fetchone()
    observation = conn.execute(
        "SELECT * FROM dataset_observation WHERE dataset_observation_id=?",
        (policy.observation_id,),
    ).fetchone()
    version = conn.execute(
        "SELECT * FROM dataset_version WHERE dataset_version_id=?", (policy.version_id,)
    ).fetchone()
    right = conn.execute(
        "SELECT * FROM evidence_right WHERE evidence_right_id=?", (policy.right_id,)
    ).fetchone()
    schema = conn.execute(
        "SELECT * FROM payload_schema WHERE payload_schema_id=?", (policy.payload_schema_id,)
    ).fetchone()
    payload = json.loads(item["payload_json"]) if item is not None else {}
    expected_payload = {
        "policy_id": "s7-method-boundary/v1",
        "output_pointer": "/refusals/performance-estimator",
        "statement": (
            "S7 reconstructs lineage and basis-qualified panels; it does not estimate "
            "alpha, Sharpe, IRR, PME, skill, or manager ranking."
        ),
        "prohibited_outputs": "alpha|sharpe|irr|pme|skill|manager-ranking",
    }
    resolved_span = resolve_span(conn, policy.span_id) if span is not None else {}
    if (
        item is None
        or span is None
        or observation is None
        or version is None
        or right is None
        or schema is None
        or payload != expected_payload
        or policy.policy_id != expected_payload["policy_id"]
        or policy.dataset_id != "dataset:s7-method-boundary"
        or item["dataset_id"] != policy.dataset_id
        or item["payload_schema_id"] != policy.payload_schema_id
        or item["content_sha256"] != policy.payload_sha256
        or item["content_sha256"] != sha256(canonical_bytes(payload))
        or schema["schema_sha256"] != policy.payload_schema_sha256
        or schema["schema_sha256"]
        != sha256(canonical_bytes(json.loads(schema["schema_json"])))
        or span["evidence_item_id"] != policy.item_id
        or span["json_pointer"] != "/statement"
        or resolved_span.get("evidence_item_id") != policy.item_id
        or resolved_span.get("json_pointer") != "/statement"
        or resolved_span.get("text") != expected_payload["statement"]
        or observation["evidence_item_id"] != policy.item_id
        or observation["dataset_version_id"] != policy.version_id
        or version["dataset_id"] != policy.dataset_id
        or version["acquisition_right_id"] != policy.right_id
        or right["dataset_id"] != policy.dataset_id
        or right["access_context"] != "public"
        or right["licence_purpose"] != "s7-research"
        or len(bundle.slices) != 1
        or len(bundle.slices[0].rows) != 1
        or bundle.slices[0].rows[0]["evidence_item_id"] != policy.item_id
        or bundle.slices[0].digest != policy.snapshot_digest
        or bundle.slices[0].receipt_id != policy.slice_receipt_id
        or bundle.bundle_digest != policy.bundle_digest
        or bundle.join_receipt_id != policy.join_receipt_id
    ):
        raise ValueError("s7-policy-manifest-mismatch")
    verify_receipt(conn, policy.slice_receipt_id, bundle)
    verify_receipt(conn, policy.join_receipt_id, bundle)
    return bundle


_S7_CLOSURE_QUERIES = {
    "canonical_entity": (
        "SELECT * FROM canonical_entity WHERE entity_id LIKE 'person:s7-%' ORDER BY entity_id"
    ),
    "dataset": "SELECT * FROM dataset WHERE dataset_id LIKE 'dataset:s7-%' ORDER BY dataset_id",
    "payload_schema": (
        "SELECT * FROM payload_schema WHERE payload_schema_id LIKE 'schema:s7-%' "
        "ORDER BY payload_schema_id"
    ),
    "source_record": (
        "SELECT * FROM source_record WHERE dataset_id LIKE 'dataset:s7-%' ORDER BY source_record_id"
    ),
    "evidence_item": (
        "SELECT i.* FROM evidence_item i JOIN source_record s USING(source_record_id) "
        "WHERE s.dataset_id LIKE 'dataset:s7-%' ORDER BY i.evidence_item_id"
    ),
    "evidence_span": (
        "SELECT sp.* FROM evidence_span sp JOIN evidence_item i USING(evidence_item_id) "
        "JOIN source_record s USING(source_record_id) WHERE s.dataset_id LIKE 'dataset:s7-%' "
        "ORDER BY sp.evidence_span_id"
    ),
    "evidence_right": (
        "SELECT * FROM evidence_right WHERE dataset_id LIKE 'dataset:s7-%' ORDER BY evidence_right_id"
    ),
    "dataset_version": (
        "SELECT * FROM dataset_version WHERE dataset_id LIKE 'dataset:s7-%' "
        "ORDER BY dataset_version_id"
    ),
    "dataset_delivery_partition": (
        "SELECT p.* FROM dataset_delivery_partition p JOIN dataset_version v "
        "USING(dataset_version_id) WHERE v.dataset_id LIKE 'dataset:s7-%' "
        "ORDER BY p.dataset_delivery_partition_id"
    ),
    "dataset_observation": (
        "SELECT o.* FROM dataset_observation o JOIN dataset_version v USING(dataset_version_id) "
        "WHERE v.dataset_id LIKE 'dataset:s7-%' ORDER BY o.dataset_observation_id"
    ),
    "dataset_observation_partition_link": (
        "SELECT l.* FROM dataset_observation_partition_link l JOIN dataset_observation o "
        "USING(dataset_observation_id) JOIN dataset_version v USING(dataset_version_id) "
        "WHERE v.dataset_id LIKE 'dataset:s7-%' ORDER BY l.dataset_observation_partition_link_id"
    ),
    "entity_mapping": (
        "SELECT * FROM entity_mapping WHERE source_key LIKE 's7-%' ORDER BY entity_mapping_id"
    ),
    "observation_membership_link": (
        "SELECT DISTINCT l.* FROM observation_membership_link l JOIN entity_mapping m "
        "USING(dataset_observation_id) WHERE m.source_key LIKE 's7-%' "
        "ORDER BY l.observation_membership_link_id"
    ),
    "entity_relationship": (
        "SELECT r.* FROM entity_relationship r JOIN evidence_item i "
        "ON i.evidence_item_id=r.source_evidence_item_id JOIN source_record s "
        "ON s.source_record_id=i.source_record_id WHERE s.dataset_id LIKE 'dataset:s7-%' "
        "ORDER BY r.entity_relationship_id"
    ),
}


def _query_tuples(conn: sqlite3.Connection, sql: str) -> tuple[tuple[object, ...], ...]:
    return tuple(tuple(row) for row in conn.execute(sql))


def _authoritative_s7_bundle_requests(
    conn: sqlite3.Connection,
) -> tuple[str, ...]:
    from ..model import SnapshotBundleRequest

    right_records = _query_tuples(conn, _S7_CLOSURE_QUERIES["evidence_right"])
    requests = []
    for scenario in S7_SCENARIOS:
        for cutoff_name in S7_CUTOFFS:
            for mode in ("latest-known", "all-known-versions"):
                sources = tuple(
                    sorted(
                        _s7_requests_from_right_records(right_records, scenario, mode),
                        key=lambda source: source.dataset_id,
                    )
                )
                requests.append(
                    canonical_bytes(
                        SnapshotBundleRequest(
                            S7_CUTOFFS[cutoff_name],
                            sources,
                            _S7_JOIN_KEYS,
                            "s7-track-lineage-v1",
                        )
                    ).decode()
                )
    rights = {row[3]: row for row in right_records}
    policy_source = DatasetSliceRequest(
        "dataset:s7-method-boundary",
        "public",
        str(rights["dataset:s7-method-boundary"][0]),
        "s7-research",
        revision_mode="latest-known",
        include_unresolved=True,
    )
    death_source = DatasetSliceRequest(
        "dataset:s7-lineage-terms",
        "shortlisted-nda",
        str(rights["dataset:s7-lineage-terms"][0]),
        "s7-research",
        revision_mode="latest-known",
        include_unresolved=True,
    )
    requests.extend(
        (
            canonical_bytes(
                SnapshotBundleRequest(
                    S7_CUTOFFS["latest"],
                    (policy_source,),
                    ("evidence_item_id",),
                    "s7-method-policy-v1",
                )
            ).decode(),
            canonical_bytes(
                SnapshotBundleRequest(
                    S7_CUTOFFS["latest"],
                    (death_source,),
                    ("evidence_item_id",),
                    "s7-death-evidence-v1",
                )
            ).decode(),
        )
    )
    return tuple(sorted(set(requests)))


def _authoritative_s7_bundle_rows(conn: sqlite3.Connection):
    requests = _authoritative_s7_bundle_requests(conn)
    placeholders = ",".join("?" for _ in requests)
    rows = tuple(
        conn.execute(
            f"SELECT * FROM snapshot_bundle_manifest WHERE request_json IN ({placeholders}) "
            f"ORDER BY bundle_digest",
            requests,
        )
    )
    if len(rows) != len(requests):
        raise ValueError("s7-authoritative-bundle-closure-mismatch")
    return rows


def _authoritative_s7_snapshot_rows(conn: sqlite3.Connection):
    digests = tuple(
        sorted(
            {
                digest
                for row in _authoritative_s7_bundle_rows(conn)
                for _, digest in json.loads(row["slice_digests_json"])
            }
        )
    )
    if not digests:
        return ()
    placeholders = ",".join("?" for _ in digests)
    return tuple(
        conn.execute(
            f"SELECT * FROM snapshot_manifest WHERE snapshot_digest IN ({placeholders}) "
            f"ORDER BY snapshot_digest",
            digests,
        )
    )


def _s7_receipt_ids(conn: sqlite3.Connection) -> tuple[str, ...]:
    bundle_rows = _authoritative_s7_bundle_rows(conn)
    snapshot_digests = tuple(row["snapshot_digest"] for row in _authoritative_s7_snapshot_rows(conn))
    identifiers = {row["join_receipt_id"] for row in bundle_rows}
    death_span_receipts = tuple(
        row[0]
        for row in conn.execute(
            "SELECT receipt_id FROM reconstruction_receipt "
            "WHERE claim_id='claim:s7-death-evidence' AND algorithm_id='s7-death-span-v1'"
        )
    )
    if len(death_span_receipts) != 1:
        raise ValueError("s7-death-span-receipt-mismatch")
    identifiers.update(death_span_receipts)
    if snapshot_digests:
        placeholders = ",".join("?" for _ in snapshot_digests)
        identifiers.update(
            row[0]
            for row in conn.execute(
                f"SELECT receipt_id FROM reconstruction_receipt WHERE claim_id='claim:snapshot-slice' "
                f"AND input_digest IN ({placeholders})",
                snapshot_digests,
            )
        )
    return tuple(sorted(identifiers))


def _s7_receipt_rows(conn: sqlite3.Connection, receipt_ids: Sequence[str]):
    if not receipt_ids:
        return ()
    placeholders = ",".join("?" for _ in receipt_ids)
    return tuple(
        tuple(row)
        for table, order_by in (
            ("reconstruction_receipt", "receipt_id"),
            ("receipt_reference", "receipt_id,ordinal"),
            ("receipt_seal", "receipt_id"),
        )
        for row in conn.execute(
            f"SELECT '{table}',* FROM {table} WHERE receipt_id IN ({placeholders}) "
            f"ORDER BY {order_by}",
            tuple(receipt_ids),
        )
    )


def _s7_authored_closure_payload(conn: sqlite3.Connection):
    receipt_ids = _s7_receipt_ids(conn)
    return (
        S7_AUTHORED_CLOSURE_CONTRACT_VERSION,
        tuple((name, _query_tuples(conn, sql)) for name, sql in _S7_CLOSURE_QUERIES.items())
        + (
            ("snapshot_manifest", tuple(tuple(row) for row in _authoritative_s7_snapshot_rows(conn))),
            (
                "snapshot_bundle_manifest",
                tuple(tuple(row) for row in _authoritative_s7_bundle_rows(conn)),
            ),
        ),
        _s7_receipt_rows(conn, receipt_ids),
    )


def _s7_requests_from_right_records(
    right_records: Sequence[tuple[object, ...]], scenario: str, revision_mode: str
) -> tuple[DatasetSliceRequest, ...]:
    rights = {row[3]: row for row in right_records}
    return tuple(
        DatasetSliceRequest(
            dataset_id,
            str(rights[dataset_id][4]),
            str(rights[dataset_id][0]),
            str(rights[dataset_id][5]),
            revision_mode=revision_mode,
            include_unresolved=True,
        )
        for dataset_id in _SCENARIO_DATASETS[scenario]
    )


def _materialize_bundle_contract(
    conn: sqlite3.Connection,
    manifest: S7FixtureManifest,
    scenario: str,
    cutoff_name: str,
) -> S7BundleContract:
    from ..model import SnapshotBundleRequest
    from ..snapshot import as_known_bundle

    analytic = as_known_bundle(
        conn,
        SnapshotBundleRequest(
            S7_CUTOFFS[cutoff_name],
            s7_source_requests(
                manifest,
                scenario=scenario,
                cutoff_name=cutoff_name,
                revision_mode="latest-known",
            ),
            _S7_JOIN_KEYS,
            "s7-track-lineage-v1",
        ),
    )
    audit = as_known_bundle(
        conn,
        SnapshotBundleRequest(
            S7_CUTOFFS[cutoff_name],
            s7_source_requests(
                manifest,
                scenario=scenario,
                cutoff_name=cutoff_name,
                revision_mode="all-known-versions",
            ),
            _S7_JOIN_KEYS,
            "s7-track-lineage-v1",
        ),
    )
    return S7BundleContract(
        scenario,
        cutoff_name,
        tuple((slice_.request.dataset_id, slice_.digest) for slice_ in analytic.slices),
        tuple((slice_.request.dataset_id, slice_.digest) for slice_ in audit.slices),
        tuple((slice_.request.dataset_id, slice_.receipt_id) for slice_ in analytic.slices),
        tuple((slice_.request.dataset_id, slice_.receipt_id) for slice_ in audit.slices),
        analytic.bundle_digest,
        audit.bundle_digest,
        analytic.join_receipt_id,
        audit.join_receipt_id,
    )


def _bundle_contracts_from_rights(
    conn: sqlite3.Connection, right_records: tuple[tuple[object, ...], ...]
) -> tuple[S7BundleContract, ...]:
    from ..model import SnapshotBundleRequest
    from ..snapshot import as_known_bundle

    contracts = []
    for scenario in S7_SCENARIOS:
        for cutoff_name in S7_CUTOFFS:
            bundles = {}
            for label, mode in (
                ("analytic", "latest-known"),
                ("audit", "all-known-versions"),
            ):
                bundles[label] = as_known_bundle(
                    conn,
                    SnapshotBundleRequest(
                        S7_CUTOFFS[cutoff_name],
                        _s7_requests_from_right_records(right_records, scenario, mode),
                        _S7_JOIN_KEYS,
                        "s7-track-lineage-v1",
                    ),
                )
            analytic = bundles["analytic"]
            audit = bundles["audit"]
            contracts.append(
                S7BundleContract(
                    scenario,
                    cutoff_name,
                    tuple((row.request.dataset_id, row.digest) for row in analytic.slices),
                    tuple((row.request.dataset_id, row.digest) for row in audit.slices),
                    tuple((row.request.dataset_id, row.receipt_id) for row in analytic.slices),
                    tuple((row.request.dataset_id, row.receipt_id) for row in audit.slices),
                    analytic.bundle_digest,
                    audit.bundle_digest,
                    analytic.join_receipt_id,
                    audit.join_receipt_id,
                )
            )
    return tuple(contracts)


def _s7_manifest_components(conn: sqlite3.Connection):
    return {
        "payload_schema_digests": tuple(
            tuple(row)
            for row in conn.execute(
                "SELECT payload_schema_id,schema_sha256 FROM payload_schema "
                "WHERE payload_schema_id LIKE 'schema:s7-%' ORDER BY payload_schema_id"
            )
        ),
        "source_record_records": _query_tuples(conn, _S7_CLOSURE_QUERIES["source_record"]),
        "item_records": _query_tuples(conn, _S7_CLOSURE_QUERIES["evidence_item"]),
        "span_records": _query_tuples(conn, _S7_CLOSURE_QUERIES["evidence_span"]),
        "right_records": _query_tuples(conn, _S7_CLOSURE_QUERIES["evidence_right"]),
        "version_records": _query_tuples(conn, _S7_CLOSURE_QUERIES["dataset_version"]),
        "partition_records": _query_tuples(
            conn, _S7_CLOSURE_QUERIES["dataset_delivery_partition"]
        ),
        "observation_records": _query_tuples(conn, _S7_CLOSURE_QUERIES["dataset_observation"]),
        "mapping_records": _query_tuples(conn, _S7_CLOSURE_QUERIES["entity_mapping"]),
        "observation_membership_link_records": _query_tuples(
            conn, _S7_CLOSURE_QUERIES["observation_membership_link"]
        ),
        "relationship_records": _query_tuples(
            conn, _S7_CLOSURE_QUERIES["entity_relationship"]
        ),
        "receipt_ids": _s7_receipt_ids(conn),
    }


def _s7_manifest_records_match(conn: sqlite3.Connection, manifest: S7FixtureManifest) -> bool:
    components = _s7_manifest_components(conn)
    return all(getattr(manifest, name) == value for name, value in components.items())


def _build_s7_fixture(conn: sqlite3.Connection) -> S7FixtureManifest:
    from ..schema import SCHEMA_VERSION
    from .credit import build_s7_credit_sources
    from .private_markets import build_s7_private_market_sources
    from .public_markets import build_s7_public_market_sources
    from .terms import build_s7_terms_sources
    from .x3 import build_x3_fixture, verify_x3_manifest

    x3_manifest = build_x3_fixture(conn)
    if not verify_x3_manifest(conn, x3_manifest):
        raise ValueError("s7-x3-prerequisite-invalid")
    build_s7_public_market_sources(conn)
    build_s7_credit_sources(conn)
    build_s7_private_market_sources(conn)
    policy, _ = build_s7_terms_sources(conn)
    scenario_contracts = _close_s7_projection_links(conn, x3_manifest)
    if not verify_x3_manifest(conn, x3_manifest):
        raise ValueError("s7-x3-coexistence-invalid")
    right_records = _query_tuples(conn, _S7_CLOSURE_QUERIES["evidence_right"])
    bundle_contracts = _bundle_contracts_from_rights(conn, right_records)
    components = _s7_manifest_components(conn)
    limitation_codes = tuple(
        f"S7-L{index}" for index in range(1, 25) if index != 8
    ) + ("S7-L8", "S7-L8a")
    manifest = S7FixtureManifest(
        fixture_id=S7_FIXTURE_ID,
        fixture_digest="",
        closure_digest=s7_authored_closure_digest(conn),
        schema_version=SCHEMA_VERSION,
        schema_digest=S7_SCHEMA_SHA256,
        x3_fixture_digest=x3_manifest.fixture_digest,
        dataset_ids=S7_DATASET_IDS,
        scenario_contracts=scenario_contracts,
        bundle_contracts=bundle_contracts,
        policy=policy,
        limitation_codes=tuple(sorted(limitation_codes)),
        **components,
    )
    manifest = replace(manifest, fixture_digest=s7_manifest_digest(manifest))
    if not _s7_manifest_records_match(conn, manifest):
        raise ValueError("s7-manifest-persisted-mismatch")
    return manifest
