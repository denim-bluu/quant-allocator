"""Reviewed synthetic operational-evidence population owned by the E3 seam."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict, dataclass, replace
from datetime import UTC, datetime
from types import MappingProxyType
from typing import Mapping

from quant_allocator.evidence.checks import refuse
from quant_allocator.evidence.ingest import (
    expected_partition_manifest,
    ingest_dataset_delivery_partitions,
    ingest_dataset_observation_partition_links,
    ingest_dataset_observations,
    ingest_dataset_versions,
    ingest_datasets,
    ingest_entities,
    ingest_items,
    ingest_payload_schemas,
    ingest_rights,
    ingest_source_records,
    ingest_spans,
    received_partition_manifest,
    reconstruction_manifest,
)
from quant_allocator.evidence.lineage import make_receipt, store_receipt, verify_receipt
from quant_allocator.evidence.model import (
    DatasetDeliveryPartitionRecord,
    DatasetObservationPartitionLinkRecord,
    DatasetObservationRecord,
    DatasetRecord,
    DatasetSliceRequest,
    DatasetVersionRecord,
    EntityRecord,
    EvidenceItemRecord,
    EvidenceRightRecord,
    EvidenceSpanRecord,
    PayloadSchemaRecord,
    ReceiptReference,
    SnapshotBundle,
    SnapshotBundleRequest,
    SourceRecordRecord,
    canonical_bytes,
    machine_id,
    normalize_utc,
    sha256,
    with_machine_id,
)
from quant_allocator.evidence.schema import SCHEMA_VERSION, connect, initialize, schema_digest
from quant_allocator.evidence.snapshot import as_known_bundle

E4_OPERATIONAL_FIXTURE_ID = "e4_operational_evidence_v1"
E4_OPERATIONAL_FIXTURE_DOMAIN = b"quant-allocator/e4-operational-fixture/v1\0"
_E3_REVIEWED_TIP = "349d436"
_FIELD_DICTIONARY_VERSION = "e4-operational-v1"
_LICENCE_PURPOSE = "e4-research"
_TYPED_RECEIPT_CLAIM = "claim:e4-operational-fixture-field-closure"
_TYPED_RECEIPT_ALGORITHM = "e4-operational-fixture-field-closure"
_TYPED_RECEIPT_VERSION = "1"

_PUBLIC = "dataset:e4-public-registry"
_MANAGER = "dataset:e4-manager-documents"
_CONTROL = "dataset:e4-control-evidence"
_REFERENCES = "dataset:e4-independent-references"
_POLICY = "dataset:e4-operational-policy"
_DATASET_IDS = tuple(sorted((_PUBLIC, _MANAGER, _CONTROL, _REFERENCES, _POLICY)))
_SCHEMA_IDS = {
    _PUBLIC: "schema:e4-public-registry-operational-v1",
    _MANAGER: "schema:e4-manager-documents-operational-v1",
    _CONTROL: "schema:e4-control-evidence-operational-v1",
    _REFERENCES: "schema:e4-independent-references-operational-v1",
    _POLICY: "schema:e4-operational-policy-v1",
}
_SOURCE_FAMILY = {
    _PUBLIC: "public-regulatory-record",
    _MANAGER: "manager-document",
    _CONTROL: "control-test",
    _REFERENCES: "reference-record",
    _POLICY: "method-policy",
}
_SOURCE_VIEWS = (
    (
        "all-entitled",
        (_PUBLIC, _MANAGER, _CONTROL, _REFERENCES, _POLICY),
    ),
    ("public-only", (_PUBLIC, _POLICY)),
)
_CUTOFFS = (
    ("early", datetime(2024, 3, 31, 23, 59, 59, tzinfo=UTC)),
    ("latest", datetime(2025, 3, 31, 23, 59, 59, tzinfo=UTC)),
    ("middle", datetime(2024, 9, 30, 23, 59, 59, tzinfo=UTC)),
)
_TEMPORAL_TYPES = ("point", "interval")
_DOMAINS = ("organisation", "process", "control", "provider", "incident")
_SOURCE_FAMILIES = (
    "manager-document",
    "public-regulatory-record",
    "provider-confirmation",
    "control-test",
    "reference-record",
    "method-policy",
)
_INDEPENDENCE_GROUPS = (
    "manager-self",
    "public-regulator",
    "provider-direct",
    "independent-control-test",
    "independent-reference",
)
_ASSERTION_KINDS = (
    "current-state-assertion",
    "change-assertion",
    "control-existence-assertion",
    "control-effectiveness-assertion",
    "incident-notice",
    "remediation-assertion",
    "closure-assertion",
    "method-boundary-policy",
)
_INCIDENT_MATERIALITY = ("critical", "material", "non-material")


@dataclass(frozen=True, slots=True)
class OperationalBundleManifest:
    cutoff_key: str
    source_view: str
    bundle_kind: str
    dataset_id: str | None
    revision_mode: str
    include_unresolved: bool
    slice_digests: tuple[str, ...]
    slice_receipt_ids: tuple[str, ...]
    join_receipt_id: str
    bundle_digest: str


@dataclass(frozen=True, slots=True)
class OperationalSourceSchemaManifest:
    dataset_id: str
    payload_schema_id: str
    schema_version: int
    field_dictionary_version: str
    schema_sha256: str
    manager_entity_id_pointer: str
    domain_pointer: str
    subject_entity_id_pointer: str
    predicate_pointer: str
    scope_pointer: str
    typed_value_pointer: str
    temporal_type_pointer: str
    effective_at_pointer: str
    effective_from_pointer: str
    effective_to_pointer: str
    source_available_at_pointer: str
    freshness_at_pointer: str
    source_family_pointer: str
    independence_group_pointer: str
    assertion_kind_pointer: str
    incident_materiality_pointer: str


@dataclass(frozen=True, slots=True)
class OperationalRightManifest:
    dataset_id: str
    evidence_right_id: str
    right_series_id: str
    right_version: int
    access_context: str
    licence_purpose: str
    status: str
    retention_policy: str
    received_at_utc: datetime
    entitlement_from: datetime
    entitlement_to: datetime | None
    supersedes_right_id: str | None


@dataclass(frozen=True, slots=True)
class OperationalEvidenceManifest:
    fixture_id: str
    fixture_digest: str
    evidence_schema_version: int
    evidence_schema_digest: str
    e3_reviewed_tip: str
    disclosure: str
    current_attestation: str
    ordered_dataset_ids: tuple[str, ...]
    source_order_digest: str
    cutoff_items: tuple[tuple[str, str], ...]
    source_view_items: tuple[tuple[str, tuple[str, ...]], ...]
    source_schema_manifests: tuple[OperationalSourceSchemaManifest, ...]
    right_manifests: tuple[OperationalRightManifest, ...]
    row_ids_by_table: tuple[tuple[str, tuple[str, ...]], ...]
    content_digests: tuple[tuple[str, str], ...]
    reconstruction_digests: tuple[tuple[str, str], ...]
    bundle_manifests: tuple[OperationalBundleManifest, ...]
    independence_items: tuple[tuple[str, str, str], ...]
    limitation_codes: tuple[str, ...]
    unresolved_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        _require_sorted_unique(self.ordered_dataset_ids, "ordered-dataset-ids")
        if (
            tuple(row.dataset_id for row in self.source_schema_manifests)
            != self.ordered_dataset_ids
        ):
            raise ValueError("source-schema-manifests")
        _require_keyed(self.cutoff_items, "cutoff-items")
        _require_keyed(self.source_view_items, "source-view-items")
        _require_keyed(self.row_ids_by_table, "row-ids-by-table")
        _require_keyed(self.content_digests, "content-digests")
        _require_keyed(self.reconstruction_digests, "reconstruction-digests")
        _require_sorted_unique(self.limitation_codes, "limitation-codes")
        _require_sorted_unique(self.unresolved_ids, "unresolved-ids")
        right_order = tuple(
            sorted(
                self.right_manifests,
                key=lambda row: (
                    row.dataset_id,
                    row.right_series_id,
                    row.right_version,
                    row.evidence_right_id,
                ),
            )
        )
        if right_order != self.right_manifests:
            raise ValueError("right-manifests")
        bundle_order = tuple(sorted(self.bundle_manifests, key=_bundle_key))
        if bundle_order != self.bundle_manifests or len(set(bundle_order)) != len(bundle_order):
            raise ValueError("bundle-manifests")
        if tuple(sorted(self.independence_items)) != self.independence_items:
            raise ValueError("independence-items")


@dataclass(frozen=True, slots=True)
class OperationalEvidenceFixture:
    conn: sqlite3.Connection
    manifest: OperationalEvidenceManifest
    source_requests: Mapping[str, DatasetSliceRequest]


@dataclass(frozen=True, slots=True)
class _FactSeed:
    dataset_id: str
    source_key: str
    version: int
    domain: str
    subject_entity_id: str
    predicate: str
    scope: str
    typed_value: str
    temporal_type: str
    effective_at: datetime | None
    effective_from: datetime | None
    effective_to: datetime | None
    available_at: datetime
    freshness_at: datetime
    source_family: str
    independence_group: str
    assertion_kind: str
    incident_materiality: str | None = None
    canonical_entity_id: str | None = "manager:e4-northbridge"


def _require_sorted_unique(values: tuple[str, ...], code: str) -> None:
    if values != tuple(sorted(values)) or len(values) != len(set(values)):
        raise ValueError(code)


def _require_keyed(values: tuple[tuple[str, object], ...], code: str) -> None:
    keys = tuple(row[0] for row in values)
    if keys != tuple(sorted(keys)) or len(keys) != len(set(keys)):
        raise ValueError(code)


def _bundle_key(row: OperationalBundleManifest) -> tuple[object, ...]:
    return (
        row.cutoff_key,
        row.source_view,
        row.bundle_kind,
        row.dataset_id or "",
        row.revision_mode,
        row.include_unresolved,
    )


def _dt(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _payload_schema(source_time_key: str) -> dict[str, object]:
    string_or_null = {"type": ["string", "null"]}
    fact_properties: dict[str, object] = {
        "manager_entity_id": {"type": "string"},
        "domain": {"type": "string", "enum": list(_DOMAINS)},
        "subject_entity_id": {"type": "string"},
        "predicate": {"type": "string"},
        "scope": {"type": "string"},
        "typed_value": {"type": "string"},
        "freshness_at": {"type": "string", "format": "date-time"},
        "source_family": {"type": "string", "enum": list(_SOURCE_FAMILIES)},
        "independence_group": {"type": "string", "enum": list(_INDEPENDENCE_GROUPS)},
        "assertion_kind": {"type": "string", "enum": list(_ASSERTION_KINDS)},
        "incident_materiality": {
            "type": ["string", "null"],
            "enum": [*_INCIDENT_MATERIALITY, None],
        },
    }
    temporal_properties: dict[str, object] = {
        "temporal_type": {"type": "string", "enum": list(_TEMPORAL_TYPES)},
        "effective_at": string_or_null,
        "effective_from": string_or_null,
        "effective_to": string_or_null,
    }
    source_properties: dict[str, object] = {
        "published_at": string_or_null,
        "received_at": string_or_null,
    }
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "additionalProperties": False,
        "required": ["fact", "temporal", "source_time"],
        "properties": {
            "fact": {
                "type": "object",
                "additionalProperties": False,
                "required": list(fact_properties),
                "properties": fact_properties,
            },
            "temporal": {
                "type": "object",
                "additionalProperties": False,
                "required": list(temporal_properties),
                "properties": temporal_properties,
            },
            "source_time": {
                "type": "object",
                "additionalProperties": False,
                "required": list(source_properties),
                "properties": source_properties,
            },
        },
        "x-source-availability-pointer": f"/source_time/{source_time_key}",
    }


def _schema_manifest(dataset_id: str, schema_sha256: str) -> OperationalSourceSchemaManifest:
    source_pointer = (
        "/source_time/published_at"
        if dataset_id in {_PUBLIC, _POLICY}
        else "/source_time/received_at"
    )
    return OperationalSourceSchemaManifest(
        dataset_id,
        _SCHEMA_IDS[dataset_id],
        1,
        _FIELD_DICTIONARY_VERSION,
        schema_sha256,
        "/fact/manager_entity_id",
        "/fact/domain",
        "/fact/subject_entity_id",
        "/fact/predicate",
        "/fact/scope",
        "/fact/typed_value",
        "/temporal/temporal_type",
        "/temporal/effective_at",
        "/temporal/effective_from",
        "/temporal/effective_to",
        source_pointer,
        "/fact/freshness_at",
        "/fact/source_family",
        "/fact/independence_group",
        "/fact/assertion_kind",
        "/fact/incident_materiality",
    )


def _right_manifest(row: EvidenceRightRecord) -> OperationalRightManifest:
    return OperationalRightManifest(
        row.dataset_id,
        row.evidence_right_id,
        row.right_series_id,
        row.right_version,
        row.access_context,
        row.licence_purpose,
        row.status,
        row.retention_policy,
        row.received_at_utc,
        row.entitlement_from,
        row.entitlement_to,
        row.supersedes_right_id,
    )


def _entities() -> tuple[EntityRecord, ...]:
    values = (
        ("manager:e4-northbridge", "manager", "Northbridge Ridge Partners"),
        ("adviser:e4-northbridge", "adviser", "Northbridge Ridge Adviser"),
        ("team:e4-investment", "team", "Northbridge Investment Team"),
        ("provider:e4-admin-a", "service-provider", "Alderwick Administration"),
        ("provider:e4-admin-b", "service-provider", "Briarstone Administration"),
        ("provider:e4-admin-c", "service-provider", "Cedarhaven Administration"),
        ("provider:e4-auditor", "service-provider", "Dunmere Audit"),
        ("process:e4-nav-review", "process", "NAV Review Process"),
        ("control:e4-four-eyes", "control", "Four Eyes Review"),
        ("incident:e4-nav-delay", "incident", "NAV Delay Incident"),
    )
    return tuple(EntityRecord(*value) for value in values)


def _fact_seeds() -> tuple[_FactSeed, ...]:
    at = lambda value: datetime.fromisoformat(value).replace(tzinfo=UTC)  # noqa: E731
    return (
        _FactSeed(
            _POLICY,
            "method-boundary",
            1,
            "control",
            "control:e4-four-eyes",
            "method-boundary",
            "operational-reader",
            "dated evidence and questions only",
            "point",
            at("2024-02-01"),
            None,
            None,
            at("2024-02-01"),
            at("2024-02-01"),
            "method-policy",
            "public-regulator",
            "method-boundary-policy",
        ),
        _FactSeed(
            _PUBLIC,
            "provider-filing",
            1,
            "provider",
            "manager:e4-northbridge",
            "uses-provider",
            "fund-administration",
            "provider:e4-admin-a",
            "interval",
            None,
            at("2024-01-01"),
            at("2024-07-01"),
            at("2024-02-15"),
            at("2024-02-15"),
            "public-regulatory-record",
            "public-regulator",
            "current-state-assertion",
        ),
        _FactSeed(
            _PUBLIC,
            "provider-filing",
            2,
            "provider",
            "manager:e4-northbridge",
            "uses-provider",
            "fund-administration",
            "provider:e4-admin-b",
            "interval",
            None,
            at("2024-07-01"),
            None,
            at("2024-08-15"),
            at("2024-08-15"),
            "public-regulatory-record",
            "public-regulator",
            "change-assertion",
        ),
        _FactSeed(
            _PUBLIC,
            "provider-conflict",
            1,
            "organisation",
            "team:e4-investment",
            "maintains-office",
            "head-office",
            "head-office-east",
            "point",
            at("2024-07-01"),
            None,
            None,
            at("2024-08-20"),
            at("2024-08-20"),
            "public-regulatory-record",
            "public-regulator",
            "current-state-assertion",
        ),
        _FactSeed(
            _PUBLIC,
            "provider-conflict",
            2,
            "organisation",
            "team:e4-investment",
            "maintains-office",
            "head-office",
            "head-office-west",
            "point",
            at("2025-01-15"),
            None,
            None,
            at("2025-02-01"),
            at("2025-02-01"),
            "public-regulatory-record",
            "public-regulator",
            "change-assertion",
        ),
        _FactSeed(
            _PUBLIC,
            "removed-office",
            1,
            "organisation",
            "team:e4-investment",
            "maintains-office",
            "regional-office",
            "regional-office-east",
            "point",
            at("2024-02-01"),
            None,
            None,
            at("2024-02-20"),
            at("2024-02-20"),
            "public-regulatory-record",
            "public-regulator",
            "current-state-assertion",
        ),
        _FactSeed(
            _PUBLIC,
            "public-null",
            1,
            "organisation",
            "team:e4-investment",
            "unresolved-label",
            "unmatched-audit",
            "shared-label-2024",
            "point",
            at("2024-08-01"),
            None,
            None,
            at("2024-08-20"),
            at("2024-08-01"),
            "public-regulatory-record",
            "public-regulator",
            "current-state-assertion",
            canonical_entity_id=None,
        ),
        _FactSeed(
            _MANAGER,
            "manager-provider",
            1,
            "provider",
            "manager:e4-northbridge",
            "uses-provider",
            "fund-administration",
            "provider:e4-admin-a",
            "interval",
            None,
            at("2024-01-01"),
            at("2024-07-01"),
            at("2024-02-20"),
            at("2024-02-20"),
            "manager-document",
            "manager-self",
            "current-state-assertion",
        ),
        _FactSeed(
            _MANAGER,
            "manager-provider",
            2,
            "provider",
            "manager:e4-northbridge",
            "uses-provider",
            "fund-administration",
            "provider:e4-admin-c",
            "interval",
            None,
            at("2024-07-01"),
            None,
            at("2024-08-25"),
            at("2024-08-25"),
            "manager-document",
            "manager-self",
            "change-assertion",
        ),
        _FactSeed(
            _MANAGER,
            "organisation-chart",
            1,
            "organisation",
            "team:e4-investment",
            "employs",
            "investment-team-lead",
            "team-lead-v2",
            "point",
            at("2024-05-01"),
            None,
            None,
            at("2024-10-01"),
            at("2024-05-01"),
            "manager-document",
            "manager-self",
            "change-assertion",
        ),
        _FactSeed(
            _MANAGER,
            "process-snapshot",
            1,
            "process",
            "process:e4-nav-review",
            "operates-process",
            "nav-review",
            "monthly-review",
            "point",
            at("2024-06-15"),
            None,
            None,
            at("2024-07-01"),
            at("2024-06-15"),
            "manager-document",
            "manager-self",
            "current-state-assertion",
        ),
        _FactSeed(
            _MANAGER,
            "process-snapshot",
            2,
            "process",
            "process:e4-nav-review",
            "operates-process",
            "nav-review",
            "weekly-review",
            "point",
            at("2024-10-15"),
            None,
            None,
            at("2025-01-10"),
            at("2025-01-10"),
            "manager-document",
            "manager-self",
            "change-assertion",
        ),
        _FactSeed(
            _MANAGER,
            "control-copy-a",
            1,
            "control",
            "control:e4-four-eyes",
            "governed-by",
            "nav-review",
            "four-eyes-policy",
            "point",
            at("2024-03-01"),
            None,
            None,
            at("2024-03-10"),
            at("2024-03-01"),
            "manager-document",
            "manager-self",
            "control-existence-assertion",
        ),
        _FactSeed(
            _MANAGER,
            "control-copy-b",
            1,
            "control",
            "control:e4-four-eyes",
            "governed-by",
            "nav-review",
            "four-eyes-policy",
            "point",
            at("2024-03-01"),
            None,
            None,
            at("2024-03-20"),
            at("2024-03-01"),
            "manager-document",
            "manager-self",
            "control-existence-assertion",
        ),
        _FactSeed(
            _MANAGER,
            "incident-notice",
            1,
            "incident",
            "incident:e4-nav-delay",
            "affected",
            "nav-publication",
            "open",
            "point",
            at("2024-06-01"),
            None,
            None,
            at("2024-06-05"),
            at("2024-06-01"),
            "manager-document",
            "manager-self",
            "incident-notice",
            "material",
        ),
        _FactSeed(
            _MANAGER,
            "incident-notice",
            2,
            "incident",
            "incident:e4-nav-delay",
            "affected",
            "nav-publication",
            "closed",
            "point",
            at("2024-11-15"),
            None,
            None,
            at("2024-12-01"),
            at("2024-11-15"),
            "manager-document",
            "manager-self",
            "remediation-assertion",
            "material",
        ),
        _FactSeed(
            _MANAGER,
            "incident-notice",
            3,
            "incident",
            "incident:e4-nav-delay",
            "affected",
            "nav-publication",
            "closed-corrected",
            "point",
            at("2024-11-15"),
            None,
            None,
            at("2025-02-10"),
            at("2024-11-15"),
            "manager-document",
            "manager-self",
            "closure-assertion",
            "material",
        ),
        _FactSeed(
            _MANAGER,
            "incident-materiality-missing",
            1,
            "incident",
            "incident:e4-nav-delay",
            "affected",
            "materiality-unreported",
            "open",
            "point",
            at("2024-06-01"),
            None,
            None,
            at("2024-06-06"),
            at("2024-06-01"),
            "manager-document",
            "manager-self",
            "incident-notice",
            None,
        ),
        _FactSeed(
            _MANAGER,
            "date-quality-note",
            1,
            "process",
            "process:e4-nav-review",
            "effective-date-source",
            "change-date-provenance",
            "filename-only",
            "point",
            at("2024-08-01"),
            None,
            None,
            at("2024-08-01"),
            at("2024-08-01"),
            "manager-document",
            "manager-self",
            "change-assertion",
        ),
        _FactSeed(
            _MANAGER,
            "not-inferable-member",
            1,
            "organisation",
            "team:e4-investment",
            "maintains-office",
            "satellite-office",
            "satellite-office-west",
            "point",
            at("2024-02-01"),
            None,
            None,
            at("2024-02-20"),
            at("2024-02-20"),
            "manager-document",
            "manager-self",
            "current-state-assertion",
        ),
        _FactSeed(
            _MANAGER,
            "manager-null",
            1,
            "organisation",
            "team:e4-investment",
            "unresolved-label",
            "unmatched-audit",
            "shared-label-2024",
            "point",
            at("2024-08-01"),
            None,
            None,
            at("2024-08-01"),
            at("2024-08-01"),
            "manager-document",
            "manager-self",
            "current-state-assertion",
            canonical_entity_id=None,
        ),
        _FactSeed(
            _CONTROL,
            "control-test",
            1,
            "control",
            "control:e4-four-eyes",
            "tested-by",
            "nav-review",
            "test-completed",
            "point",
            at("2024-04-01"),
            None,
            None,
            at("2024-04-15"),
            at("2024-04-01"),
            "control-test",
            "independent-control-test",
            "control-effectiveness-assertion",
        ),
        _FactSeed(
            _CONTROL,
            "control-test",
            2,
            "control",
            "control:e4-four-eyes",
            "tested-by",
            "nav-review",
            "test-refreshed",
            "point",
            at("2025-01-05"),
            None,
            None,
            at("2025-01-10"),
            at("2025-01-05"),
            "control-test",
            "independent-control-test",
            "change-assertion",
        ),
        _FactSeed(
            _CONTROL,
            "provider-confirmation",
            1,
            "process",
            "process:e4-nav-review",
            "operates-process",
            "nav-review",
            "weekly-review",
            "point",
            at("2024-10-15"),
            None,
            None,
            at("2025-01-12"),
            at("2025-01-10"),
            "provider-confirmation",
            "provider-direct",
            "current-state-assertion",
        ),
        _FactSeed(
            _CONTROL,
            "stale-control",
            1,
            "control",
            "control:e4-four-eyes",
            "tested-by",
            "legacy-test",
            "test-completed",
            "point",
            at("2023-01-01"),
            None,
            None,
            at("2024-02-01"),
            at("2023-01-01"),
            "control-test",
            "independent-control-test",
            "control-effectiveness-assertion",
        ),
        _FactSeed(
            _CONTROL,
            "incident-remediation",
            1,
            "incident",
            "incident:e4-nav-delay",
            "affected",
            "nav-publication",
            "open-confirmed",
            "point",
            at("2024-11-20"),
            None,
            None,
            at("2024-12-10"),
            at("2024-11-20"),
            "control-test",
            "independent-control-test",
            "incident-notice",
            "material",
        ),
        _FactSeed(
            _REFERENCES,
            "provider-reference",
            1,
            "control",
            "control:e4-four-eyes",
            "governed-by",
            "nav-review",
            "four-eyes-policy",
            "point",
            at("2024-03-01"),
            None,
            None,
            at("2024-09-20"),
            at("2024-09-20"),
            "reference-record",
            "independent-reference",
            "current-state-assertion",
        ),
        _FactSeed(
            _REFERENCES,
            "organisation-reference",
            1,
            "organisation",
            "team:e4-investment",
            "employs",
            "investment-team-lead",
            "team-lead-v1",
            "point",
            at("2024-05-01"),
            None,
            None,
            at("2024-11-01"),
            at("2024-05-01"),
            "reference-record",
            "independent-reference",
            "current-state-assertion",
        ),
        _FactSeed(
            _REFERENCES,
            "reference-null",
            1,
            "organisation",
            "team:e4-investment",
            "unresolved-label",
            "unmatched-audit",
            "shared-label-2024",
            "point",
            at("2024-08-01"),
            None,
            None,
            at("2024-09-20"),
            at("2024-08-01"),
            "reference-record",
            "independent-reference",
            "current-state-assertion",
            canonical_entity_id=None,
        ),
    )


def _payload(seed: _FactSeed) -> dict[str, object]:
    is_public = seed.dataset_id in {_PUBLIC, _POLICY}
    source_time = normalize_utc(seed.available_at)
    return {
        "fact": {
            "manager_entity_id": "manager:e4-northbridge",
            "domain": seed.domain,
            "subject_entity_id": seed.subject_entity_id,
            "predicate": seed.predicate,
            "scope": seed.scope,
            "typed_value": seed.typed_value,
            "freshness_at": normalize_utc(seed.freshness_at),
            "source_family": seed.source_family,
            "independence_group": seed.independence_group,
            "assertion_kind": seed.assertion_kind,
            "incident_materiality": seed.incident_materiality,
        },
        "temporal": {
            "temporal_type": seed.temporal_type,
            "effective_at": normalize_utc(seed.effective_at) if seed.effective_at else None,
            "effective_from": (normalize_utc(seed.effective_from) if seed.effective_from else None),
            "effective_to": normalize_utc(seed.effective_to) if seed.effective_to else None,
        },
        "source_time": {
            "published_at": source_time if is_public else None,
            "received_at": None if is_public else source_time,
        },
    }


def _make_rights() -> tuple[EvidenceRightRecord, ...]:
    rows: list[EvidenceRightRecord] = []
    for dataset_id in _DATASET_IDS:
        context = "public" if dataset_id in {_PUBLIC, _POLICY} else "shortlisted-nda"
        primary = with_machine_id(
            "right",
            EvidenceRightRecord(
                "",
                f"right-series:{dataset_id.removeprefix('dataset:')}:primary",
                1,
                dataset_id,
                context,
                _LICENCE_PURPOSE,
                "active",
                "retain-after-expiry",
                datetime(2023, 1, 1, tzinfo=UTC),
                datetime(2023, 1, 1, tzinfo=UTC),
                None,
            ),
        )
        rows.append(primary)
        for suffix, status, purpose in (
            ("expired", "expired", _LICENCE_PURPOSE),
            ("revoked", "revoked", _LICENCE_PURPOSE),
            ("wrong-purpose", "active", "operations-only"),
        ):
            rows.append(
                with_machine_id(
                    "right",
                    EvidenceRightRecord(
                        "",
                        f"right-series:{dataset_id.removeprefix('dataset:')}:{suffix}",
                        1,
                        dataset_id,
                        context,
                        purpose,
                        status,
                        "access-only-while-active",
                        datetime(2022, 1, 1, tzinfo=UTC),
                        datetime(2022, 1, 1, tzinfo=UTC),
                        datetime(2022, 12, 31, tzinfo=UTC),
                    ),
                )
            )
        old = with_machine_id(
            "right",
            EvidenceRightRecord(
                "",
                f"right-series:{dataset_id.removeprefix('dataset:')}:supersession",
                1,
                dataset_id,
                context,
                _LICENCE_PURPOSE,
                "superseded",
                "retain-after-expiry",
                datetime(2022, 1, 1, tzinfo=UTC),
                datetime(2022, 1, 1, tzinfo=UTC),
                datetime(2023, 1, 1, tzinfo=UTC),
            ),
        )
        new = with_machine_id(
            "right",
            EvidenceRightRecord(
                "",
                old.right_series_id,
                2,
                dataset_id,
                context,
                _LICENCE_PURPOSE,
                "active",
                "retain-after-expiry",
                datetime(2023, 1, 1, tzinfo=UTC),
                datetime(2023, 1, 1, tzinfo=UTC),
                None,
                old.evidence_right_id,
            ),
        )
        rows.extend((old, new))
    return tuple(rows)


def _source_records(seeds: tuple[_FactSeed, ...]) -> tuple[SourceRecordRecord, ...]:
    keys = sorted({(seed.dataset_id, seed.source_key) for seed in seeds})
    return tuple(
        with_machine_id(
            "source-record",
            SourceRecordRecord("", dataset_id, "authored-synthetic", source_key, "document"),
        )
        for dataset_id, source_key in keys
    )


def _build_items(
    seeds: tuple[_FactSeed, ...],
    sources: tuple[SourceRecordRecord, ...],
    rights: tuple[EvidenceRightRecord, ...],
) -> tuple[tuple[EvidenceItemRecord, ...], tuple[EvidenceSpanRecord, ...]]:
    source_by_key = {(row.dataset_id, row.source_record_key): row for row in sources}
    right_by_dataset = {
        row.dataset_id: row
        for row in rights
        if row.right_series_id.endswith(":primary") and row.status == "active"
    }
    prior: dict[tuple[str, str], EvidenceItemRecord] = {}
    items: list[EvidenceItemRecord] = []
    spans: list[EvidenceSpanRecord] = []
    span_pointers = (
        "/fact/manager_entity_id",
        "/fact/domain",
        "/fact/subject_entity_id",
        "/fact/predicate",
        "/fact/scope",
        "/fact/typed_value",
        "/fact/freshness_at",
        "/fact/source_family",
        "/fact/independence_group",
        "/fact/assertion_kind",
        "/fact/incident_materiality",
        "/temporal/temporal_type",
        "/temporal/effective_at",
        "/temporal/effective_from",
        "/temporal/effective_to",
        "/source_time/published_at",
        "/source_time/received_at",
    )
    for seed in sorted(seeds, key=lambda row: (row.dataset_id, row.source_key, row.version)):
        key = (seed.dataset_id, seed.source_key)
        previous = prior.get(key)
        if seed.version != (1 if previous is None else previous.version + 1):
            raise ValueError("fixture-item-revision-gap")
        payload = _payload(seed)
        right = right_by_dataset[seed.dataset_id]
        item = with_machine_id(
            "evidence",
            EvidenceItemRecord(
                "",
                right.evidence_right_id,
                source_by_key[key].source_record_id,
                sha256(canonical_bytes(payload)),
                "e4-operational-fact",
                _SCHEMA_IDS[seed.dataset_id],
                seed.temporal_type,
                seed.effective_at,
                seed.effective_from,
                seed.effective_to,
                seed.freshness_at.date(),
                seed.available_at if seed.dataset_id in {_PUBLIC, _POLICY} else None,
                None,
                None if seed.dataset_id in {_PUBLIC, _POLICY} else seed.available_at,
                None,
                seed.version,
                previous.evidence_item_id if previous else None,
                "published" if seed.dataset_id in {_PUBLIC, _POLICY} else "received",
                right.access_context,
                _FIELD_DICTIONARY_VERSION,
                "synthetic",
                _LICENCE_PURPOSE,
                payload,
                canonical_entity_type="manager" if seed.canonical_entity_id else None,
                canonical_entity_id=seed.canonical_entity_id,
                manager_id="manager:e4-northbridge",
            ),
        )
        items.append(item)
        prior[key] = item
        for pointer in span_pointers:
            value = _resolve_pointer(payload, pointer)
            if not isinstance(value, str):
                continue
            spans.append(
                with_machine_id(
                    "span",
                    EvidenceSpanRecord(
                        "", item.evidence_item_id, pointer, 0, len(value), sha256(value.encode())
                    ),
                )
            )
    return tuple(items), tuple(spans)


def _resolve_pointer(payload: Mapping[str, object], pointer: str) -> object:
    value: object = payload
    for token in pointer.lstrip("/").split("/"):
        if not isinstance(value, Mapping):
            raise ValueError(pointer)
        value = value[token]
    return value


def _version_specs(item_by_key: Mapping[tuple[str, str, int], EvidenceItemRecord]):
    def item(dataset: str, key: str, version: int = 1) -> EvidenceItemRecord:
        return item_by_key[(dataset, key, version)]

    return {
        _POLICY: (
            (
                "00-pre-delivery",
                datetime(2024, 1, 1, tzinfo=UTC),
                "full-snapshot",
                "not-inferable",
                "complete",
                (),
            ),
            (
                "01-policy",
                datetime(2024, 2, 1, tzinfo=UTC),
                "full-snapshot",
                "not-inferable",
                "complete",
                ((item(_POLICY, "method-boundary"), "present"),),
            ),
        ),
        _PUBLIC: (
            (
                "00-pre-delivery",
                datetime(2024, 1, 1, tzinfo=UTC),
                "full-snapshot",
                "not-inferable",
                "complete",
                (),
            ),
            (
                "01-early",
                datetime(2024, 2, 28, tzinfo=UTC),
                "full-snapshot",
                "not-inferable",
                "complete",
                (
                    (item(_PUBLIC, "provider-filing", 1), "present"),
                    (item(_PUBLIC, "removed-office"), "present"),
                ),
            ),
            (
                "02-middle",
                datetime(2024, 9, 1, tzinfo=UTC),
                "full-snapshot",
                "full-snapshot-means-removed",
                "complete",
                (
                    (item(_PUBLIC, "provider-filing", 2), "present"),
                    (item(_PUBLIC, "provider-conflict", 1), "present"),
                    (item(_PUBLIC, "public-null"), "present"),
                ),
            ),
            (
                "03-correction",
                datetime(2025, 2, 15, tzinfo=UTC),
                "delta",
                "explicit-tombstone-only",
                "complete",
                (
                    (item(_PUBLIC, "provider-filing", 2), "present"),
                    (item(_PUBLIC, "provider-conflict", 2), "present"),
                ),
            ),
        ),
        _MANAGER: (
            (
                "00-pre-delivery",
                datetime(2024, 1, 1, tzinfo=UTC),
                "full-snapshot",
                "not-inferable",
                "complete",
                (),
            ),
            (
                "01-early",
                datetime(2024, 3, 1, tzinfo=UTC),
                "full-snapshot",
                "not-inferable",
                "complete",
                (
                    (item(_MANAGER, "manager-provider", 1), "present"),
                    (item(_MANAGER, "control-copy-a"), "present"),
                    (item(_MANAGER, "control-copy-b"), "present"),
                    (item(_MANAGER, "not-inferable-member"), "present"),
                ),
            ),
            (
                "02-middle",
                datetime(2024, 9, 1, tzinfo=UTC),
                "delta",
                "explicit-tombstone-only",
                "complete",
                (
                    (item(_MANAGER, "manager-provider", 2), "present"),
                    (item(_MANAGER, "control-copy-a"), "present"),
                    (item(_MANAGER, "control-copy-b"), "explicitly-removed"),
                    (item(_MANAGER, "process-snapshot"), "present"),
                    (item(_MANAGER, "date-quality-note"), "present"),
                    (item(_MANAGER, "manager-null"), "present"),
                    (item(_MANAGER, "incident-notice", 1), "present"),
                    (item(_MANAGER, "incident-materiality-missing"), "present"),
                    (item(_MANAGER, "not-inferable-member"), "present"),
                ),
            ),
            (
                "03-latest-full",
                datetime(2024, 12, 15, tzinfo=UTC),
                "full-snapshot",
                "not-inferable",
                "complete",
                (
                    (item(_MANAGER, "manager-provider", 2), "present"),
                    (item(_MANAGER, "control-copy-a"), "present"),
                    (item(_MANAGER, "process-snapshot", 1), "present"),
                    (item(_MANAGER, "date-quality-note"), "present"),
                    (item(_MANAGER, "manager-null"), "present"),
                    (item(_MANAGER, "organisation-chart"), "present"),
                    (item(_MANAGER, "incident-notice", 2), "present"),
                    (item(_MANAGER, "incident-materiality-missing"), "present"),
                ),
            ),
            (
                "04-correction",
                datetime(2025, 2, 15, tzinfo=UTC),
                "delta",
                "explicit-tombstone-only",
                "complete",
                (
                    (item(_MANAGER, "manager-provider", 2), "present"),
                    (item(_MANAGER, "incident-notice", 3), "present"),
                    (item(_MANAGER, "process-snapshot", 2), "present"),
                ),
            ),
        ),
        _CONTROL: (
            (
                "00-pre-delivery",
                datetime(2024, 1, 1, tzinfo=UTC),
                "full-snapshot",
                "not-inferable",
                "complete",
                (),
            ),
            (
                "01-tests",
                datetime(2024, 5, 1, tzinfo=UTC),
                "full-snapshot",
                "not-inferable",
                "complete",
                (
                    (item(_CONTROL, "control-test"), "present"),
                    (item(_CONTROL, "stale-control"), "present"),
                ),
            ),
            (
                "02-remediation",
                datetime(2024, 12, 15, tzinfo=UTC),
                "delta",
                "explicit-tombstone-only",
                "complete",
                ((item(_CONTROL, "incident-remediation"), "present"),),
            ),
            (
                "03-confirmation",
                datetime(2025, 1, 15, tzinfo=UTC),
                "delta",
                "explicit-tombstone-only",
                "complete",
                ((item(_CONTROL, "provider-confirmation"), "present"),),
            ),
            (
                "04-refresh",
                datetime(2025, 2, 1, tzinfo=UTC),
                "delta",
                "explicit-tombstone-only",
                "complete",
                ((item(_CONTROL, "control-test", 2), "present"),),
            ),
            (
                "99-incomplete",
                datetime(2026, 1, 1, tzinfo=UTC),
                "full-snapshot",
                "not-inferable",
                "incomplete",
                (),
            ),
        ),
        _REFERENCES: (
            (
                "00-pre-delivery",
                datetime(2024, 1, 1, tzinfo=UTC),
                "full-snapshot",
                "not-inferable",
                "complete",
                (),
            ),
            (
                "01-references",
                datetime(2024, 9, 20, tzinfo=UTC),
                "full-snapshot",
                "not-inferable",
                "complete",
                (
                    (item(_REFERENCES, "provider-reference"), "present"),
                    (item(_REFERENCES, "organisation-reference"), "present"),
                    (item(_REFERENCES, "reference-null"), "present"),
                ),
            ),
        ),
    }


def _ingest_versions(
    conn: sqlite3.Connection,
    specs,
    rights: tuple[EvidenceRightRecord, ...],
    manifest_items: Mapping[str, EvidenceItemRecord],
    manifest_spans: Mapping[str, EvidenceSpanRecord],
    reverse_dataset_order: bool = False,
):
    primary_right = {
        row.dataset_id: row for row in rights if row.right_series_id.endswith(":primary")
    }
    versions: dict[tuple[str, str], DatasetVersionRecord] = {}
    observations_by_item: dict[tuple[str, str], DatasetObservationRecord] = {}
    materialized: dict[str, dict[str, tuple[str, str, str]]] = {dataset: {} for dataset in specs}
    dataset_order = tuple(reversed(_DATASET_IDS)) if reverse_dataset_order else _DATASET_IDS
    for dataset_id in dataset_order:
        predecessor: DatasetVersionRecord | None = None
        base: DatasetVersionRecord | None = None
        for label, available, mode, absence, completeness, entries in specs[dataset_id]:
            partition_status = (
                "expected-received" if completeness == "complete" else "expected-missing"
            )
            partition_seed = (
                {
                    "partition_key": f"partition-{label}",
                    "partition_status": partition_status,
                    "expected_record_count": len(entries) if completeness == "complete" else 1,
                    "received_record_count": len(entries) if completeness == "complete" else 0,
                    "received_content_sha256": (
                        sha256(canonical_bytes(tuple(item.evidence_item_id for item, _ in entries)))
                        if completeness == "complete"
                        else None
                    ),
                },
            )
            if mode == "full-snapshot":
                current = {
                    item.source_record_id: (
                        item.source_record_id,
                        item.evidence_item_id,
                        status,
                    )
                    for item, status in entries
                    if status == "present"
                }
            else:
                current = dict(materialized[dataset_id])
                for item, status in entries:
                    if status == "explicitly-removed":
                        current.pop(item.source_record_id, None)
                    else:
                        current[item.source_record_id] = (
                            item.source_record_id,
                            item.evidence_item_id,
                            status,
                        )
            reconstruction_rows = tuple(
                {
                    "source_record_id": source_record_id,
                    "evidence_item_id": evidence_item_id,
                    "observation_status": status,
                }
                for source_record_id, evidence_item_id, status in sorted(current.values())
            )
            right = primary_right[dataset_id]
            version = with_machine_id(
                "dataset-version",
                DatasetVersionRecord(
                    "",
                    dataset_id,
                    label,
                    right.evidence_right_id,
                    available if dataset_id in {_PUBLIC, _POLICY} else None,
                    None,
                    None if dataset_id in {_PUBLIC, _POLICY} else available,
                    (
                        datetime(2024, 10, 15, tzinfo=UTC)
                        if dataset_id == _REFERENCES and label == "01-references"
                        else None
                    ),
                    sha256(canonical_bytes((dataset_id, label, entries))),
                    mode,
                    absence,
                    completeness,
                    expected_partition_manifest(partition_seed),
                    received_partition_manifest(partition_seed),
                    1,
                    1 if completeness == "complete" else 0,
                    reconstruction_manifest(reconstruction_rows)
                    if completeness == "complete"
                    else None,
                    len(reconstruction_rows) if completeness == "complete" else None,
                    predecessor.dataset_version_id if predecessor else None,
                    base.dataset_version_id if mode == "delta" and base else None,
                ),
            )
            ingest_dataset_versions(conn, [version])
            versions[(dataset_id, label)] = version
            observations = tuple(
                with_machine_id(
                    "dataset-observation",
                    DatasetObservationRecord(
                        "",
                        version.dataset_version_id,
                        item.evidence_item_id,
                        status,
                        "explicit-source-tombstone" if status == "explicitly-removed" else None,
                    ),
                )
                for item, status in entries
            )
            ingest_dataset_observations(conn, observations)
            partition = with_machine_id(
                "dataset-partition",
                DatasetDeliveryPartitionRecord(
                    "",
                    version.dataset_version_id,
                    f"partition-{label}",
                    partition_status,
                    manifest_items[dataset_id].evidence_item_id,
                    manifest_spans[dataset_id].evidence_span_id,
                    partition_seed[0]["received_content_sha256"],
                    partition_seed[0]["expected_record_count"],
                    partition_seed[0]["received_record_count"],
                ),
            )
            ingest_dataset_delivery_partitions(conn, [partition])
            links = tuple(
                with_machine_id(
                    "dataset-observation-partition",
                    DatasetObservationPartitionLinkRecord(
                        "",
                        observation.dataset_observation_id,
                        partition.dataset_delivery_partition_id,
                    ),
                )
                for observation in observations
            )
            ingest_dataset_observation_partition_links(conn, links)
            for (item, _), observation in zip(entries, observations, strict=True):
                observations_by_item[(version.dataset_version_id, item.evidence_item_id)] = (
                    observation
                )
            if completeness == "complete":
                materialized[dataset_id] = current
            predecessor = version
            if mode == "full-snapshot" and completeness == "complete":
                base = version
    return versions, observations_by_item


def _insert_relationships(
    conn: sqlite3.Connection,
    seeds: tuple[_FactSeed, ...],
    items: tuple[EvidenceItemRecord, ...],
    spans: tuple[EvidenceSpanRecord, ...],
    versions: Mapping[tuple[str, str], DatasetVersionRecord],
    observations_by_item: Mapping[tuple[str, str], DatasetObservationRecord],
) -> tuple[str, ...]:
    item_by_key = {
        (seed.dataset_id, seed.source_key, seed.version): item
        for seed, item in zip(
            sorted(seeds, key=lambda row: (row.dataset_id, row.source_key, row.version)),
            items,
            strict=True,
        )
    }
    span_by_item_value = {(span.evidence_item_id, span.json_pointer): span for span in spans}
    relation_specs = (
        (
            "managed-or-advised-by",
            _MANAGER,
            "manager-provider",
            1,
            "manager:e4-northbridge",
            "adviser:e4-northbridge",
            "01-early",
            None,
        ),
        (
            "employs",
            _MANAGER,
            "organisation-chart",
            1,
            "manager:e4-northbridge",
            "team:e4-investment",
            "03-latest-full",
            None,
        ),
        (
            "uses-provider",
            _PUBLIC,
            "provider-filing",
            1,
            "manager:e4-northbridge",
            "provider:e4-admin-a",
            "01-early",
            None,
        ),
        (
            "uses-provider",
            _PUBLIC,
            "provider-filing",
            2,
            "manager:e4-northbridge",
            "provider:e4-admin-b",
            "02-middle",
            "public-provider-b",
        ),
        (
            "uses-provider",
            _PUBLIC,
            "provider-filing",
            2,
            "manager:e4-northbridge",
            "provider:e4-admin-b",
            "03-correction",
            "public-provider-b",
        ),
        (
            "uses-provider",
            _MANAGER,
            "manager-provider",
            1,
            "manager:e4-northbridge",
            "provider:e4-admin-a",
            "01-early",
            None,
        ),
        (
            "uses-provider",
            _MANAGER,
            "manager-provider",
            2,
            "manager:e4-northbridge",
            "provider:e4-admin-c",
            "02-middle",
            "manager-provider-c",
        ),
        (
            "uses-provider",
            _MANAGER,
            "manager-provider",
            2,
            "manager:e4-northbridge",
            "provider:e4-admin-c",
            "03-latest-full",
            "manager-provider-c",
        ),
        (
            "uses-provider",
            _MANAGER,
            "manager-provider",
            2,
            "manager:e4-northbridge",
            "provider:e4-admin-c",
            "04-correction",
            "manager-provider-c",
        ),
        (
            "operates-process",
            _MANAGER,
            "process-snapshot",
            1,
            "manager:e4-northbridge",
            "process:e4-nav-review",
            "02-middle",
            None,
        ),
        (
            "operates-process",
            _MANAGER,
            "process-snapshot",
            2,
            "manager:e4-northbridge",
            "process:e4-nav-review",
            "04-correction",
            None,
        ),
        (
            "governed-by",
            _MANAGER,
            "control-copy-a",
            1,
            "process:e4-nav-review",
            "control:e4-four-eyes",
            "01-early",
            None,
        ),
        (
            "governed-by",
            _MANAGER,
            "control-copy-a",
            1,
            "process:e4-nav-review",
            "control:e4-four-eyes",
            "02-middle",
            "governed-by",
        ),
        (
            "tested-by",
            _CONTROL,
            "control-test",
            1,
            "control:e4-four-eyes",
            "document:e4-control-test",
            "01-tests",
            None,
        ),
        (
            "tested-by",
            _CONTROL,
            "control-test",
            2,
            "control:e4-four-eyes",
            "document:e4-control-test",
            "04-refresh",
            None,
        ),
        (
            "operates-process",
            _CONTROL,
            "provider-confirmation",
            1,
            "manager:e4-northbridge",
            "process:e4-nav-review",
            "03-confirmation",
            None,
        ),
        (
            "governed-by",
            _REFERENCES,
            "provider-reference",
            1,
            "process:e4-nav-review",
            "control:e4-four-eyes",
            "01-references",
            None,
        ),
        (
            "affected",
            _MANAGER,
            "incident-notice",
            1,
            "incident:e4-nav-delay",
            "manager:e4-northbridge",
            "02-middle",
            None,
        ),
        (
            "asserts-operational-fact",
            _PUBLIC,
            "provider-filing",
            2,
            "document:e4-provider-filing",
            "provider:e4-admin-b",
            "02-middle",
            None,
        ),
    )
    document_entities = {
        "document:e4-control-test": "Control test evidence",
        "document:e4-provider-filing": "Provider filing evidence",
    }
    ingest_entities(
        conn,
        tuple(
            EntityRecord(identifier, "document", label)
            for identifier, label in document_entities.items()
        ),
    )
    ids: list[str] = []
    prior_relation: dict[str, tuple[str, int]] = {}
    for (
        relation_type,
        dataset_id,
        source_key,
        item_version,
        source_entity_id,
        target_entity_id,
        version_label,
        revision_key,
    ) in relation_specs:
        item = item_by_key[(dataset_id, source_key, item_version)]
        version = versions[(dataset_id, version_label)]
        observation = observations_by_item[(version.dataset_version_id, item.evidence_item_id)]
        seed = next(
            row
            for row in seeds
            if (row.dataset_id, row.source_key, row.version)
            == (dataset_id, source_key, item_version)
        )
        span = span_by_item_value[(item.evidence_item_id, "/fact/typed_value")]
        revision_of, prior_version = prior_relation.get(revision_key or "", (None, 0))
        relationship_version = prior_version + 1
        temporal_type = seed.temporal_type
        effective_at = normalize_utc(seed.effective_at) if seed.effective_at else None
        effective_from = normalize_utc(seed.effective_from) if seed.effective_from else None
        effective_to = normalize_utc(seed.effective_to) if seed.effective_to else None
        if relation_type == "governed-by":
            temporal_type = "interval"
            effective_at = None
            effective_from = "2024-03-01T00:00:00.000000Z"
            effective_to = None if revision_key else "2024-09-01T00:00:00.000000Z"
        identity = {
            "source_evidence_item_id": item.evidence_item_id,
            "relation_type": relation_type,
            "source_entity_id": source_entity_id,
            "target_entity_id": target_entity_id,
            "temporal_type": temporal_type,
            "effective_at": effective_at,
            "effective_from": effective_from,
            "effective_to": effective_to,
            "version": relationship_version,
        }
        identifier = machine_id("entity-relation", identity)
        conn.execute(
            "INSERT INTO entity_relationship VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                identifier,
                item.evidence_item_id,
                span.evidence_span_id,
                version.dataset_version_id,
                observation.dataset_observation_id,
                relation_type,
                source_entity_id,
                target_entity_id,
                temporal_type,
                identity["effective_at"],
                identity["effective_from"],
                identity["effective_to"],
                relationship_version,
                revision_of,
            ),
        )
        ids.append(identifier)
        if revision_key:
            prior_relation[revision_key] = (identifier, relationship_version)
        if relation_type == "governed-by":
            prior_relation["governed-by"] = (identifier, relationship_version)
    return tuple(sorted(ids))


def _insert_mappings(
    conn: sqlite3.Connection,
    seeds: tuple[_FactSeed, ...],
    items: tuple[EvidenceItemRecord, ...],
    spans: tuple[EvidenceSpanRecord, ...],
    versions: Mapping[tuple[str, str], DatasetVersionRecord],
    observations_by_item: Mapping[tuple[str, str], DatasetObservationRecord],
) -> tuple[str, ...]:
    ordered = sorted(seeds, key=lambda row: (row.dataset_id, row.source_key, row.version))
    item_by_key = {
        (seed.dataset_id, seed.source_key, seed.version): item
        for seed, item in zip(ordered, items, strict=True)
    }
    span_by_item = {(span.evidence_item_id, span.json_pointer): span for span in spans}
    specs = (
        (
            _MANAGER,
            "manager-null",
            "02-middle",
            "ambiguous",
            None,
            ("adviser:e4-northbridge", "manager:e4-northbridge"),
            "candidate-review-pending",
            1,
            None,
        ),
        (
            _MANAGER,
            "manager-null",
            "03-latest-full",
            "resolved",
            "manager:e4-northbridge",
            ("manager:e4-northbridge",),
            "reviewed-exact-identifier",
            2,
            "manager-null",
        ),
        (
            _PUBLIC,
            "public-null",
            "02-middle",
            "unresolved",
            None,
            (),
            "unresolved-source",
            1,
            None,
        ),
        (
            _REFERENCES,
            "reference-null",
            "01-references",
            "unresolved",
            None,
            (),
            "unresolved-source",
            1,
            None,
        ),
    )
    identifiers: list[str] = []
    parents: dict[str, str] = {}
    for (
        dataset_id,
        source_key,
        version_label,
        status,
        canonical_entity_id,
        candidates,
        resolution_rule,
        mapping_version,
        revision_key,
    ) in specs:
        item = item_by_key[(dataset_id, source_key, 1)]
        seed = next(
            row
            for row in seeds
            if (row.dataset_id, row.source_key, row.version) == (dataset_id, source_key, 1)
        )
        version = versions[(dataset_id, version_label)]
        observation = observations_by_item[(version.dataset_version_id, item.evidence_item_id)]
        span = span_by_item[(item.evidence_item_id, "/fact/typed_value")]
        candidate_json = canonical_bytes(candidates).decode()
        identity = {
            "source_evidence_item_id": item.evidence_item_id,
            "source_key": source_key,
            "source_label": seed.typed_value,
            "taxonomy_version": _FIELD_DICTIONARY_VERSION,
            "version": mapping_version,
            "candidate_entity_ids_json": candidate_json,
        }
        identifier = machine_id("mapping", identity)
        conn.execute(
            "INSERT INTO entity_mapping VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                identifier,
                item.evidence_item_id,
                span.evidence_span_id,
                version.dataset_version_id,
                observation.dataset_observation_id,
                source_key,
                seed.typed_value,
                "manager",
                canonical_entity_id,
                status,
                candidate_json,
                resolution_rule,
                _FIELD_DICTIONARY_VERSION,
                seed.temporal_type,
                normalize_utc(seed.effective_at) if seed.effective_at else None,
                normalize_utc(seed.effective_from) if seed.effective_from else None,
                normalize_utc(seed.effective_to) if seed.effective_to else None,
                mapping_version,
                parents.get(revision_key or ""),
            ),
        )
        identifiers.append(identifier)
        if dataset_id == _MANAGER and source_key == "manager-null":
            parents["manager-null"] = identifier
    return tuple(sorted(identifiers))


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


def _typed_receipt_parts(
    conn: sqlite3.Connection,
    *,
    item_id: str,
    schema_manifest: OperationalSourceSchemaManifest,
    bundle: SnapshotBundle,
    reverse_references: bool = False,
) -> tuple[str, str, dict[str, object], dict[str, object], tuple[ReceiptReference, ...]]:
    item = conn.execute(
        "SELECT i.*,s.dataset_id,s.source_record_id FROM evidence_item i "
        "JOIN source_record s USING(source_record_id) WHERE evidence_item_id=?",
        (item_id,),
    ).fetchone()
    if item is None or item["dataset_id"] != schema_manifest.dataset_id:
        refuse("operational-typed-receipt-item-mismatch")
    payload = json.loads(item["payload_json"])
    output_locator = f"/operational-items/{item_id}"
    observations = conn.execute(
        "SELECT o.dataset_observation_id,o.dataset_version_id,v.acquisition_right_id "
        "FROM dataset_observation o JOIN dataset_version v USING(dataset_version_id) "
        "WHERE o.evidence_item_id=? ORDER BY o.dataset_observation_id",
        (item_id,),
    ).fetchall()
    if not observations:
        refuse("operational-typed-receipt-observation-missing")
    spans = {
        row["json_pointer"]: row["evidence_span_id"]
        for row in conn.execute(
            "SELECT json_pointer,evidence_span_id FROM evidence_span "
            "WHERE evidence_item_id=? ORDER BY json_pointer",
            (item_id,),
        )
    }
    mapping_ids = tuple(
        row[0]
        for row in conn.execute(
            "SELECT entity_mapping_id FROM entity_mapping "
            "WHERE source_evidence_item_id=? ORDER BY entity_mapping_id",
            (item_id,),
        )
    )
    relationship_ids = tuple(
        row[0]
        for row in conn.execute(
            "SELECT entity_relationship_id FROM entity_relationship "
            "WHERE source_evidence_item_id=? ORDER BY entity_relationship_id",
            (item_id,),
        )
    )
    right_ids = tuple(
        sorted(
            {item["acquisition_right_id"], *(row["acquisition_right_id"] for row in observations)}
        )
    )
    if len(bundle.slices) != 1 or bundle.slices[0].request.dataset_id != item["dataset_id"]:
        refuse("operational-typed-receipt-bundle-mismatch")
    references: list[ReceiptReference] = []
    normalized: dict[str, object] = {}
    for pointer in _schema_pointers(schema_manifest):
        value = _resolve_pointer(payload, pointer)
        normalized[pointer] = value
        output_field = f"{output_locator}{pointer}"
        common = (
            output_field,
            "included",
            "",
            schema_manifest.payload_schema_id,
            pointer,
            "input",
        )
        references.extend(
            (
                ReceiptReference(common[0], "evidence-item", item_id, *common[1:]),
                ReceiptReference(common[0], "source-record", item["source_record_id"], *common[1:]),
                ReceiptReference(common[0], "snapshot", bundle.slices[0].digest, *common[1:]),
            )
        )
        if pointer in spans:
            references.append(
                ReceiptReference(common[0], "evidence-span", spans[pointer], *common[1:])
            )
        references.extend(
            ReceiptReference(
                common[0],
                "dataset-observation",
                row["dataset_observation_id"],
                *common[1:],
            )
            for row in observations
        )
        references.extend(
            ReceiptReference(common[0], "dataset-version", row["dataset_version_id"], *common[1:])
            for row in observations
        )
        references.extend(
            ReceiptReference(common[0], "evidence-right", right_id, *common[1:])
            for right_id in right_ids
        )
        references.extend(
            ReceiptReference(common[0], "entity-mapping", identifier, *common[1:])
            for identifier in mapping_ids
        )
        references.extend(
            ReceiptReference(common[0], "entity-relationship", identifier, *common[1:])
            for identifier in relationship_ids
        )
    parameters = {
        "fixture_id": E4_OPERATIONAL_FIXTURE_ID,
        "e3_reviewed_tip": _E3_REVIEWED_TIP,
        "dataset_id": item["dataset_id"],
        "evidence_item_id": item_id,
        "payload_schema_id": schema_manifest.payload_schema_id,
        "field_dictionary_version": schema_manifest.field_dictionary_version,
        "source_bundle": {
            "slice_digest": bundle.slices[0].digest,
            "slice_receipt_id": bundle.slices[0].receipt_id,
            "join_receipt_id": bundle.join_receipt_id,
            "bundle_digest": bundle.bundle_digest,
        },
        "source_pointers": _schema_pointers(schema_manifest),
    }
    input_digest = sha256(canonical_bytes(parameters))
    if reverse_references:
        references.reverse()
    return output_locator, input_digest, parameters, normalized, tuple(references)


def _make_typed_receipt(
    conn: sqlite3.Connection,
    *,
    item_id: str,
    schema_manifest: OperationalSourceSchemaManifest,
    bundle: SnapshotBundle,
    reverse_references: bool = False,
):
    output_locator, input_digest, parameters, value, references = _typed_receipt_parts(
        conn,
        item_id=item_id,
        schema_manifest=schema_manifest,
        bundle=bundle,
        reverse_references=reverse_references,
    )
    return make_receipt(
        claim_id=_TYPED_RECEIPT_CLAIM,
        output_locator=output_locator,
        input_digest=input_digest,
        output_schema_id="schema:generic-v1",
        current_attestation="D",
        live_attestation_ceiling="D",
        algorithm_id=_TYPED_RECEIPT_ALGORITHM,
        algorithm_version=_TYPED_RECEIPT_VERSION,
        parameters=parameters,
        value=value,
        references=references,
    )


def _persist_typed_receipts(
    conn: sqlite3.Connection,
    *,
    items: tuple[EvidenceItemRecord, ...],
    schema_manifests: tuple[OperationalSourceSchemaManifest, ...],
    requests: Mapping[str, DatasetSliceRequest],
    reverse_order: bool,
) -> tuple[str, ...]:
    schemas = {row.dataset_id: row for row in schema_manifests}
    latest = dict(_CUTOFFS)["latest"]
    bundles = {
        dataset_id: _raw_source_bundle(
            conn,
            request,
            latest,
            "all-known-versions",
            True,
        )
        for dataset_id, request in requests.items()
    }
    ordered_items = tuple(sorted(items, key=lambda row: row.evidence_item_id))
    if reverse_order:
        ordered_items = tuple(reversed(ordered_items))
    receipt_ids: list[str] = []
    for item in ordered_items:
        dataset_id = conn.execute(
            "SELECT dataset_id FROM source_record WHERE source_record_id=?",
            (item.source_record_id,),
        ).fetchone()[0]
        receipt = _make_typed_receipt(
            conn,
            item_id=item.evidence_item_id,
            schema_manifest=schemas[dataset_id],
            bundle=bundles[dataset_id],
            reverse_references=reverse_order,
        )
        store_receipt(conn, receipt)
        receipt_ids.append(receipt.receipt_id)
    return tuple(sorted(receipt_ids))


def _bundle_manifest(
    cutoff_key: str,
    source_view: str,
    bundle_kind: str,
    dataset_id: str | None,
    revision_mode: str,
    include_unresolved: bool,
    bundle: SnapshotBundle,
) -> OperationalBundleManifest:
    receipt_ids = tuple(slice_.receipt_id or "" for slice_ in bundle.slices)
    if any(not identifier for identifier in receipt_ids):
        raise ValueError("slice-receipt-missing")
    return OperationalBundleManifest(
        cutoff_key,
        source_view,
        bundle_kind,
        dataset_id,
        revision_mode,
        include_unresolved,
        tuple(slice_.digest for slice_ in bundle.slices),
        receipt_ids,
        bundle.join_receipt_id,
        bundle.bundle_digest,
    )


def _request_for(
    request: DatasetSliceRequest, revision_mode: str, include_unresolved: bool
) -> DatasetSliceRequest:
    return replace(
        request,
        revision_mode=revision_mode,
        include_unresolved=include_unresolved,
    )


def _raw_source_bundle(
    conn: sqlite3.Connection,
    request: DatasetSliceRequest,
    decision_at: datetime,
    revision_mode: str,
    include_unresolved: bool,
) -> SnapshotBundle:
    source = _request_for(request, revision_mode, include_unresolved)
    return as_known_bundle(
        conn,
        SnapshotBundleRequest(
            decision_at,
            (source,),
            ("evidence_item_id",),
            "e4-one-source-v1",
        ),
    )


def _raw_verification_bundle(
    conn: sqlite3.Connection,
    requests: Mapping[str, DatasetSliceRequest],
    selected_dataset_ids: tuple[str, ...],
    decision_at: datetime,
    revision_mode: str,
    include_unresolved: bool,
) -> SnapshotBundle:
    sources = tuple(
        _request_for(requests[dataset_id], revision_mode, include_unresolved)
        for dataset_id in selected_dataset_ids
    )
    return as_known_bundle(
        conn,
        SnapshotBundleRequest(
            decision_at,
            sources,
            ("evidence_item_id",),
            "e4-verification-envelope-v1",
        ),
    )


def _row_ids(conn: sqlite3.Connection) -> tuple[tuple[str, tuple[str, ...]], ...]:
    tables = {
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
    }
    return tuple(
        (
            table,
            tuple(
                row[0] for row in conn.execute(f"SELECT {column} FROM {table} ORDER BY {column}")
            ),
        )
        for table, column in sorted(tables.items())
    )


def _input_order(values, reverse_insertion: bool):
    values = tuple(values)
    return tuple(reversed(values)) if reverse_insertion else values


def _build_operational_evidence_fixture(*, reverse_insertion: bool) -> OperationalEvidenceFixture:
    """Build the fixture under either of two real ingestion/input orders."""

    conn = connect()
    initialize(conn)
    ingest_entities(conn, _input_order(_entities(), reverse_insertion))
    datasets = tuple(
        DatasetRecord(
            dataset_id,
            dataset_id.removeprefix("dataset:").replace("-", " ").title(),
            "authored-synthetic",
            "public-publication" if dataset_id in {_PUBLIC, _POLICY} else "manager-receipt",
            _FIELD_DICTIONARY_VERSION,
            "synthetic",
            _LICENCE_PURPOSE,
        )
        for dataset_id in _DATASET_IDS
    )
    ingest_datasets(
        conn,
        _input_order(datasets, reverse_insertion),
    )
    schemas: dict[str, dict[str, object]] = {}
    schema_rows: list[PayloadSchemaRecord] = []
    for dataset_id in _DATASET_IDS:
        source_time_key = "published_at" if dataset_id in {_PUBLIC, _POLICY} else "received_at"
        schema = _payload_schema(source_time_key)
        schemas[dataset_id] = schema
        schema_rows.append(
            PayloadSchemaRecord(
                _SCHEMA_IDS[dataset_id],
                "e4-operational-fact",
                schema,
                sha256(canonical_bytes(schema)),
            )
        )
    generic = {"type": "object"}
    schema_rows.append(
        PayloadSchemaRecord(
            "schema:generic-v1", "generic-record", generic, sha256(canonical_bytes(generic))
        )
    )
    ingest_payload_schemas(conn, _input_order(schema_rows, reverse_insertion))
    rights = _make_rights()
    ingest_rights(conn, _input_order(rights, reverse_insertion))
    seeds = _fact_seeds()
    sources = _source_records(seeds)
    ingest_source_records(conn, _input_order(sources, reverse_insertion))
    items, spans = _build_items(seeds, sources, rights)
    ingest_items(conn, _input_order(items, reverse_insertion))
    ingest_spans(conn, _input_order(spans, reverse_insertion))

    ordered_seed_items = tuple(
        zip(
            sorted(seeds, key=lambda row: (row.dataset_id, row.source_key, row.version)),
            items,
            strict=True,
        )
    )
    manifest_items = {
        dataset_id: next(item for seed, item in ordered_seed_items if seed.dataset_id == dataset_id)
        for dataset_id in _DATASET_IDS
    }
    manifest_spans = {
        dataset_id: next(
            span
            for span in spans
            if span.evidence_item_id == item.evidence_item_id
            and span.json_pointer == "/fact/typed_value"
        )
        for dataset_id, item in manifest_items.items()
    }
    item_by_key = {
        (seed.dataset_id, seed.source_key, seed.version): item
        for seed, item in zip(
            sorted(seeds, key=lambda row: (row.dataset_id, row.source_key, row.version)),
            items,
            strict=True,
        )
    }
    versions, observations_by_item = _ingest_versions(
        conn,
        _version_specs(item_by_key),
        rights,
        manifest_items,
        manifest_spans,
        reverse_dataset_order=reverse_insertion,
    )
    _insert_mappings(conn, seeds, items, spans, versions, observations_by_item)
    _insert_relationships(conn, seeds, items, spans, versions, observations_by_item)
    conn.commit()

    primary_rights = {
        row.dataset_id: row for row in rights if row.right_series_id.endswith(":primary")
    }
    requests = {
        dataset_id: DatasetSliceRequest(
            dataset_id,
            primary_rights[dataset_id].access_context,
            primary_rights[dataset_id].evidence_right_id,
            _LICENCE_PURPOSE,
            revision_mode="latest-known",
            include_unresolved=False,
        )
        for dataset_id in _DATASET_IDS
    }
    schema_manifests = tuple(
        _schema_manifest(dataset_id, sha256(canonical_bytes(schemas[dataset_id])))
        for dataset_id in _DATASET_IDS
    )
    bundle_rows: list[OperationalBundleManifest] = []
    for cutoff_key, cutoff in _input_order(_CUTOFFS, reverse_insertion):
        for source_view, selected in _input_order(_SOURCE_VIEWS, reverse_insertion):
            for revision_mode in _input_order(
                ("all-known-versions", "latest-known"), reverse_insertion
            ):
                for include_unresolved in _input_order((False, True), reverse_insertion):
                    selected_input = _input_order(selected, reverse_insertion)
                    for dataset_id in selected_input:
                        bundle = _raw_source_bundle(
                            conn,
                            requests[dataset_id],
                            cutoff,
                            revision_mode,
                            include_unresolved,
                        )
                        bundle_rows.append(
                            _bundle_manifest(
                                cutoff_key,
                                source_view,
                                "one-source",
                                dataset_id,
                                revision_mode,
                                include_unresolved,
                                bundle,
                            )
                        )
                    envelope = _raw_verification_bundle(
                        conn,
                        requests,
                        selected_input,
                        cutoff,
                        revision_mode,
                        include_unresolved,
                    )
                    bundle_rows.append(
                        _bundle_manifest(
                            cutoff_key,
                            source_view,
                            "verification-envelope",
                            None,
                            revision_mode,
                            include_unresolved,
                            envelope,
                        )
                    )

    _persist_typed_receipts(
        conn,
        items=items,
        schema_manifests=schema_manifests,
        requests=requests,
        reverse_order=reverse_insertion,
    )
    right_manifests = tuple(
        sorted(
            (_right_manifest(row) for row in rights),
            key=lambda row: (
                row.dataset_id,
                row.right_series_id,
                row.right_version,
                row.evidence_right_id,
            ),
        )
    )
    span_lookup = {
        (span.evidence_item_id, span.json_pointer): span.evidence_span_id for span in spans
    }
    independence_items = tuple(
        sorted(
            (
                item.evidence_item_id,
                seed.independence_group,
                span_lookup[(item.evidence_item_id, "/fact/independence_group")],
            )
            for seed, item in zip(
                sorted(seeds, key=lambda row: (row.dataset_id, row.source_key, row.version)),
                items,
                strict=True,
            )
        )
    )
    content_digests = tuple(sorted((item.evidence_item_id, item.content_sha256) for item in items))
    reconstruction_digests = tuple(
        sorted(
            (
                row["dataset_version_id"],
                row["reconstruction_manifest_sha256"],
            )
            for row in conn.execute(
                "SELECT dataset_version_id,reconstruction_manifest_sha256 FROM dataset_version "
                "WHERE reconstruction_manifest_sha256 IS NOT NULL"
            )
        )
    )
    unresolved_ids = tuple(
        sorted(
            item.evidence_item_id
            for seed, item in zip(
                sorted(seeds, key=lambda row: (row.dataset_id, row.source_key, row.version)),
                items,
                strict=True,
            )
            if seed.canonical_entity_id is None
        )
    )
    manifest = OperationalEvidenceManifest(
        E4_OPERATIONAL_FIXTURE_ID,
        "",
        SCHEMA_VERSION,
        schema_digest(conn),
        _E3_REVIEWED_TIP,
        "Authored synthetic operational evidence; no real manager, provider, or cash data.",
        "D",
        _DATASET_IDS,
        sha256(canonical_bytes(_DATASET_IDS)),
        tuple((key, normalize_utc(value)) for key, value in _CUTOFFS),
        _SOURCE_VIEWS,
        schema_manifests,
        right_manifests,
        _row_ids(conn),
        content_digests,
        reconstruction_digests,
        tuple(sorted(bundle_rows, key=_bundle_key)),
        independence_items,
        tuple(
            sorted(
                (
                    "copied-sources-share-origin-group",
                    "inferred-change-date-is-a-separate-source-quality-fact",
                    "public-scope-is-source-limited",
                    "unresolved-rows-audit-only",
                )
            )
        ),
        unresolved_ids,
    )
    digest = sha256(
        E4_OPERATIONAL_FIXTURE_DOMAIN
        + canonical_bytes(asdict(replace(manifest, fixture_digest="")))
    )
    manifest = replace(manifest, fixture_digest=digest)
    return OperationalEvidenceFixture(conn, manifest, MappingProxyType(requests))


def build_operational_evidence_fixture() -> OperationalEvidenceFixture:
    """Build the deterministic, public-safe E4 operational evidence fixture."""

    return _build_operational_evidence_fixture(reverse_insertion=False)


def _validate_fixture(fixture: OperationalEvidenceFixture) -> None:
    expected = sha256(
        E4_OPERATIONAL_FIXTURE_DOMAIN
        + canonical_bytes(asdict(replace(fixture.manifest, fixture_digest="")))
    )
    if expected != fixture.manifest.fixture_digest:
        refuse("operational-fixture-digest-mismatch")
    if fixture.manifest.evidence_schema_digest != schema_digest(fixture.conn):
        refuse("operational-fixture-schema-mismatch")
    if _row_ids(fixture.conn) != fixture.manifest.row_ids_by_table:
        refuse("operational-fixture-row-set-mismatch")
    for row in fixture.manifest.source_schema_manifests:
        stored = fixture.conn.execute(
            "SELECT schema_json,schema_sha256 FROM payload_schema WHERE payload_schema_id=?",
            (row.payload_schema_id,),
        ).fetchone()
        if stored is None:
            refuse("operational-source-schema-missing")
        schema = json.loads(stored["schema_json"])
        if (
            stored["schema_sha256"] != row.schema_sha256
            or sha256(canonical_bytes(schema)) != row.schema_sha256
            or row != _schema_manifest(row.dataset_id, row.schema_sha256)
        ):
            refuse("operational-source-schema-mismatch")
        item_rows = fixture.conn.execute(
            "SELECT payload_schema_id,field_dictionary_version FROM evidence_item "
            "JOIN source_record USING(source_record_id) WHERE dataset_id=?",
            (row.dataset_id,),
        ).fetchall()
        if not item_rows or any(
            item["payload_schema_id"] != row.payload_schema_id
            or item["field_dictionary_version"] != row.field_dictionary_version
            for item in item_rows
        ):
            refuse("operational-source-schema-mismatch")
    for row in fixture.manifest.right_manifests:
        stored = fixture.conn.execute(
            "SELECT * FROM evidence_right WHERE evidence_right_id=?", (row.evidence_right_id,)
        ).fetchone()
        if stored is None or (
            stored["dataset_id"],
            stored["right_series_id"],
            stored["right_version"],
            stored["access_context"],
            stored["licence_purpose"],
            stored["status"],
            stored["retention_policy"],
            stored["received_at_utc"],
            stored["entitlement_from"],
            stored["entitlement_to"],
            stored["supersedes_right_id"],
        ) != (
            row.dataset_id,
            row.right_series_id,
            row.right_version,
            row.access_context,
            row.licence_purpose,
            row.status,
            row.retention_policy,
            normalize_utc(row.received_at_utc),
            normalize_utc(row.entitlement_from),
            normalize_utc(row.entitlement_to) if row.entitlement_to else None,
            row.supersedes_right_id,
        ):
            refuse("operational-right-manifest-mismatch")
    actual_content = tuple(
        sorted(
            (
                row["evidence_item_id"],
                sha256(canonical_bytes(json.loads(row["payload_json"]))),
            )
            for row in fixture.conn.execute(
                "SELECT evidence_item_id,payload_json FROM evidence_item"
            )
        )
    )
    if actual_content != fixture.manifest.content_digests:
        refuse("operational-content-digest-mismatch")
    actual_reconstruction = tuple(
        sorted(
            (row["dataset_version_id"], row["reconstruction_manifest_sha256"])
            for row in fixture.conn.execute(
                "SELECT dataset_version_id,reconstruction_manifest_sha256 FROM dataset_version "
                "WHERE reconstruction_manifest_sha256 IS NOT NULL"
            )
        )
    )
    if actual_reconstruction != fixture.manifest.reconstruction_digests:
        refuse("operational-reconstruction-digest-mismatch")
    typed_receipts = fixture.conn.execute(
        "SELECT receipt_id FROM reconstruction_receipt WHERE claim_id=? ORDER BY receipt_id",
        (_TYPED_RECEIPT_CLAIM,),
    ).fetchall()
    item_count = fixture.conn.execute("SELECT count(*) FROM evidence_item").fetchone()[0]
    if len(typed_receipts) != item_count:
        refuse("operational-typed-receipt-set-mismatch")


def verify_operational_fixture_receipt(
    fixture: OperationalEvidenceFixture, *, receipt_id: str
) -> None:
    """Verify exact field-level schema and lineage closure for one seam-owned fact receipt."""

    _validate_fixture(fixture)
    receipt = fixture.conn.execute(
        "SELECT * FROM reconstruction_receipt WHERE receipt_id=?", (receipt_id,)
    ).fetchone()
    if receipt is None or receipt["claim_id"] != _TYPED_RECEIPT_CLAIM:
        refuse("operational-typed-receipt-missing")
    item_ids = {
        row[0]
        for row in fixture.conn.execute(
            "SELECT evidence_item_id FROM receipt_reference WHERE receipt_id=? "
            "AND reference_type='evidence-item'",
            (receipt_id,),
        )
    }
    if len(item_ids) != 1:
        refuse("operational-typed-receipt-item-mismatch")
    item_id = next(iter(item_ids))
    dataset_id = fixture.conn.execute(
        "SELECT s.dataset_id FROM evidence_item i JOIN source_record s USING(source_record_id) "
        "WHERE evidence_item_id=?",
        (item_id,),
    ).fetchone()
    if dataset_id is None:
        refuse("operational-typed-receipt-item-mismatch")
    schema_manifest = next(
        (
            row
            for row in fixture.manifest.source_schema_manifests
            if row.dataset_id == dataset_id[0]
        ),
        None,
    )
    if schema_manifest is None:
        refuse("operational-source-schema-missing")
    latest = _dt(dict(fixture.manifest.cutoff_items)["latest"])
    bundle = _raw_source_bundle(
        fixture.conn,
        fixture.source_requests[dataset_id[0]],
        latest,
        "all-known-versions",
        True,
    )
    expected = _make_typed_receipt(
        fixture.conn,
        item_id=item_id,
        schema_manifest=schema_manifest,
        bundle=bundle,
    )
    if expected.receipt_id != receipt_id:
        refuse("operational-typed-receipt-contract-mismatch")
    persisted_references = tuple(
        ReceiptReference(
            row["output_field"],
            row["reference_type"],
            row[_reference_column(row["reference_type"])],
            row["disposition"],
            row["reason_code"],
            row["source_schema_id"],
            row["source_field"],
            row["role"],
        )
        for row in fixture.conn.execute(
            "SELECT * FROM receipt_reference WHERE receipt_id=? ORDER BY ordinal",
            (receipt_id,),
        )
    )
    if persisted_references != expected.references:
        refuse("operational-typed-receipt-reference-mismatch")
    expected_header = (
        expected.claim_id,
        expected.output_locator,
        expected.input_digest,
        expected.output_schema_id,
        expected.current_attestation,
        expected.live_attestation_ceiling,
        expected.algorithm_id,
        expected.algorithm_version,
        expected.parameters_sha256,
        expected.value_sha256,
    )
    persisted_header = tuple(receipt[key] for key in receipt.keys() if key != "receipt_id")
    if persisted_header != expected_header:
        refuse("operational-typed-receipt-header-mismatch")
    verify_receipt(fixture.conn, receipt_id, bundle)


def _reference_column(reference_type: str) -> str:
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
        return columns[reference_type]
    except KeyError:
        refuse("operational-typed-receipt-reference-mismatch")


def _cutoff_key(manifest: OperationalEvidenceManifest, decision_at: datetime) -> str:
    value = normalize_utc(decision_at)
    for key, cutoff in manifest.cutoff_items:
        if cutoff == value:
            return key
    refuse("unsupported-operational-cutoff")


def operational_source_bundle(
    fixture: OperationalEvidenceFixture,
    *,
    dataset_id: str,
    decision_at: datetime,
    revision_mode: str,
    include_unresolved: bool,
) -> SnapshotBundle:
    """Return one exact, persisted one-source bundle from the ruled fixture matrix."""

    _validate_fixture(fixture)
    if revision_mode not in {"latest-known", "all-known-versions"}:
        refuse("invalid-revision-mode")
    if not isinstance(include_unresolved, bool):
        refuse("invalid-unresolved-mode")
    cutoff_key = _cutoff_key(fixture.manifest, decision_at)
    try:
        request = fixture.source_requests[dataset_id]
    except KeyError:
        refuse("unknown-operational-dataset", dataset_id=dataset_id)
    bundle = _raw_source_bundle(
        fixture.conn, request, decision_at, revision_mode, include_unresolved
    )
    candidates = tuple(
        row
        for row in fixture.manifest.bundle_manifests
        if row.cutoff_key == cutoff_key
        and row.bundle_kind == "one-source"
        and row.dataset_id == dataset_id
        and row.revision_mode == revision_mode
        and row.include_unresolved == include_unresolved
    )
    expected = {
        (
            row.slice_digests,
            row.slice_receipt_ids,
            row.join_receipt_id,
            row.bundle_digest,
        )
        for row in candidates
    }
    actual = (
        tuple(slice_.digest for slice_ in bundle.slices),
        tuple(slice_.receipt_id or "" for slice_ in bundle.slices),
        bundle.join_receipt_id,
        bundle.bundle_digest,
    )
    if actual not in expected:
        refuse("operational-bundle-contract-mismatch")
    return bundle


def operational_verification_bundle(
    fixture: OperationalEvidenceFixture,
    *,
    selected_dataset_ids: tuple[str, ...],
    decision_at: datetime,
    revision_mode: str,
    include_unresolved: bool,
) -> SnapshotBundle:
    """Return the ruled empty-intersection verification envelope, never an analytic join."""

    _validate_fixture(fixture)
    views = {datasets: key for key, datasets in fixture.manifest.source_view_items}
    try:
        source_view = views[selected_dataset_ids]
    except KeyError:
        refuse("operational-source-view-mismatch")
    if revision_mode not in {"latest-known", "all-known-versions"}:
        refuse("invalid-revision-mode")
    if not isinstance(include_unresolved, bool):
        refuse("invalid-unresolved-mode")
    cutoff_key = _cutoff_key(fixture.manifest, decision_at)
    bundle = _raw_verification_bundle(
        fixture.conn,
        fixture.source_requests,
        selected_dataset_ids,
        decision_at,
        revision_mode,
        include_unresolved,
    )
    expected = next(
        (
            row
            for row in fixture.manifest.bundle_manifests
            if row.cutoff_key == cutoff_key
            and row.source_view == source_view
            and row.bundle_kind == "verification-envelope"
            and row.revision_mode == revision_mode
            and row.include_unresolved == include_unresolved
        ),
        None,
    )
    actual = _bundle_manifest(
        cutoff_key,
        source_view,
        "verification-envelope",
        None,
        revision_mode,
        include_unresolved,
        bundle,
    )
    if actual != expected:
        refuse("operational-bundle-contract-mismatch")
    return bundle


__all__ = [
    "E4_OPERATIONAL_FIXTURE_DOMAIN",
    "E4_OPERATIONAL_FIXTURE_ID",
    "OperationalBundleManifest",
    "OperationalEvidenceFixture",
    "OperationalEvidenceManifest",
    "OperationalRightManifest",
    "OperationalSourceSchemaManifest",
    "build_operational_evidence_fixture",
    "operational_source_bundle",
    "operational_verification_bundle",
    "verify_operational_fixture_receipt",
]
