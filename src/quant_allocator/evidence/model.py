from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass, is_dataclass, replace
from datetime import UTC, date, datetime
from typing import Any, Mapping, TypeAlias

from .checks import refuse, require

JSONValue: TypeAlias = None | bool | int | float | str | list["JSONValue"] | dict[str, "JSONValue"]
_ID = re.compile(r"^[a-z][a-z0-9-]*(?::(?:sha256:[0-9a-f]{64}|[a-z0-9][a-z0-9-]*))*$")


def normalize_utc(value: datetime) -> str:
    if value.tzinfo is None or value.utcoffset() is None:
        refuse("invalid-utc")
    return value.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def validate_identifier(value: str) -> str:
    if not _ID.fullmatch(value):
        refuse("invalid-id", value=value)
    return value


def _jsonable(value: Any) -> JSONValue:
    if is_dataclass(value):
        return _jsonable(asdict(value))
    if isinstance(value, datetime):
        return normalize_utc(value)
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Mapping):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [_jsonable(v) for v in value]
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    raise TypeError(type(value).__name__)


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        _jsonable(value), sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode()


def sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def digest_id(namespace: str, value: Any) -> str:
    validate_identifier(namespace)
    return f"{namespace}:sha256:{sha256(canonical_bytes(value))}"


_MACHINE_ID_FIELDS: dict[str, tuple[str, ...]] = {
    "dataset-version": (
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
    "dataset-partition": (
        "dataset_version_id",
        "partition_key",
        "partition_status",
        "manifest_evidence_item_id",
        "manifest_evidence_span_id",
        "received_content_sha256",
        "expected_record_count",
        "received_record_count",
    ),
    "source-record": ("dataset_id", "source_system", "source_record_key"),
    "dataset-observation": (
        "dataset_version_id",
        "evidence_item_id",
        "observation_status",
    ),
    "dataset-observation-partition": (
        "dataset_observation_id",
        "dataset_delivery_partition_id",
    ),
    "right": (
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
    "evidence": ("source_record_id", "version"),
    "span": ("evidence_item_id", "json_pointer", "start_char", "end_char", "span_sha256"),
    "entity-relation": (
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
    "mapping": (
        "source_evidence_item_id",
        "source_key",
        "source_label",
        "taxonomy_version",
        "version",
        "candidate_entity_ids_json",
    ),
    "membership": (
        "source_evidence_item_id",
        "entity_mapping_id",
        "dataset_version_id",
        "membership_status",
        "taxonomy_version",
        "temporal_type",
        "effective_at",
        "effective_from",
        "effective_to",
        "version",
    ),
    "observation-membership": ("dataset_observation_id", "universe_membership_id"),
    "grid": (
        "source_evidence_item_id",
        "source_label",
        "taxonomy_version",
        "denominator_rule",
        "version",
    ),
    "grid-cell": (
        "target_grid_id",
        "dimensions_json",
        "eligibility_status",
        "exclusion_reason",
    ),
    "funnel-opportunity": (
        "source_evidence_item_id",
        "evidence_span_id",
        "entity_mapping_id",
        "source_opportunity_key",
        "product_entity_id",
        "entity_grain",
        "temporal_type",
        "effective_at",
        "effective_from",
        "effective_to",
        "version",
    ),
    "funnel-schema": (
        "source_evidence_item_id",
        "stage_dictionary_json",
        "transition_rules_json",
        "reason_dictionary_json",
        "completeness_status",
        "version",
    ),
    "funnel-cohort": (
        "source_evidence_item_id",
        "funnel_schema_id",
        "cohort_label",
        "inclusion_rule_json",
        "exclusion_rule_json",
        "entity_grain",
        "entry_stage",
        "outcome_stage",
        "accepted_only",
        "entry_window_from",
        "entry_window_to",
        "observation_window_end",
        "completeness_status",
        "absence_rule",
        "censor_policy",
        "right_censor_at",
        "version",
    ),
    "funnel-event": (
        "funnel_opportunity_id",
        "funnel_schema_id",
        "source_evidence_item_id",
        "entity_mapping_id",
        "funnel_stage",
        "reason_code",
        "effective_at",
        "version",
    ),
    "funnel-cohort-event": (
        "funnel_cohort_id",
        "funnel_event_id",
        "funnel_opportunity_id",
        "inclusion_disposition",
        "inclusion_reason_code",
        "evaluation_status",
        "censor_status",
    ),
}

_MACHINE_ID_ATTRIBUTES = {
    "dataset-version": "dataset_version_id",
    "dataset-partition": "dataset_delivery_partition_id",
    "source-record": "source_record_id",
    "dataset-observation": "dataset_observation_id",
    "dataset-observation-partition": "dataset_observation_partition_link_id",
    "right": "evidence_right_id",
    "evidence": "evidence_item_id",
    "span": "evidence_span_id",
}


def machine_id(namespace: str, values: Mapping[str, Any] | Any) -> str:
    """Derive a typed identifier from its complete, versioned identity tuple.

    Known record namespaces reject missing or surplus fields so a caller cannot
    silently derive the same identifier from a shorthand identity.
    """

    fields = _MACHINE_ID_FIELDS.get(namespace)
    if fields is None:
        return digest_id(namespace, values)
    if is_dataclass(values):
        identity = {name: getattr(values, name) for name in fields}
    elif isinstance(values, Mapping):
        identity = {str(key): value for key, value in values.items()}
    else:
        raise TypeError(type(values).__name__)
    if set(identity) != set(fields):
        refuse(
            "invalid-machine-id-input",
            namespace=namespace,
            missing=sorted(set(fields) - set(identity)),
            surplus=sorted(set(identity) - set(fields)),
        )
    return digest_id(namespace, {name: identity[name] for name in fields})


def machine_id_for_record(namespace: str, record: Any) -> str:
    return machine_id(namespace, record)


def require_machine_id(namespace: str, identifier: str, record: Any) -> str:
    expected = machine_id_for_record(namespace, record)
    if identifier != expected:
        refuse("machine-id-mismatch", identifier=identifier, expected=expected)
    return identifier


def with_machine_id(namespace: str, record: Any) -> Any:
    """Return a dataclass record with its ID replaced by the canonical digest ID."""

    try:
        attribute = _MACHINE_ID_ATTRIBUTES[namespace]
    except KeyError:
        refuse("unknown-machine-id-namespace", namespace=namespace)
    if not is_dataclass(record):
        raise TypeError(type(record).__name__)
    return replace(record, **{attribute: machine_id_for_record(namespace, record)})


def contains(start: str, end: str | None, instant: str) -> bool:
    return start <= instant and (end is None or instant < end)


def point_in(start: str, end: str, instant: str) -> bool:
    return start <= instant < end


@dataclass(frozen=True, slots=True)
class EntityRecord:
    entity_id: str
    entity_type: str
    canonical_name: str
    parent_entity_id: str | None = None


@dataclass(frozen=True, slots=True)
class DatasetRecord:
    dataset_id: str
    label: str
    source_system: str
    availability_policy: str
    field_dictionary_version: str
    sensitivity_class: str
    licence_purpose: str


@dataclass(frozen=True, slots=True)
class PayloadSchemaRecord:
    payload_schema_id: str
    record_kind: str
    schema: Mapping[str, JSONValue]
    schema_sha256: str


@dataclass(frozen=True, slots=True)
class EvidenceRightRecord:
    evidence_right_id: str
    right_series_id: str
    right_version: int
    dataset_id: str
    access_context: str
    licence_purpose: str
    status: str
    retention_policy: str
    received_at_utc: datetime
    entitlement_from: datetime
    entitlement_to: datetime | None
    supersedes_right_id: str | None = None


@dataclass(frozen=True, slots=True)
class DatasetVersionRecord:
    dataset_version_id: str
    dataset_id: str
    version_label: str
    acquisition_right_id: str
    published_at: datetime | None
    first_observed_at_utc: datetime | None
    received_at_utc: datetime | None
    embargo_until: datetime | None
    content_sha256: str
    delivery_mode: str
    absence_semantics: str
    completeness_status: str
    expected_partition_manifest_sha256: str
    received_partition_manifest_sha256: str
    expected_partition_count: int
    received_partition_count: int
    reconstruction_manifest_sha256: str | None
    reconstruction_row_count: int | None
    predecessor_dataset_version_id: str | None = None
    base_dataset_version_id: str | None = None


@dataclass(frozen=True, slots=True)
class DatasetDeliveryPartitionRecord:
    dataset_delivery_partition_id: str
    dataset_version_id: str
    partition_key: str
    partition_status: str
    manifest_evidence_item_id: str
    manifest_evidence_span_id: str
    received_content_sha256: str | None
    expected_record_count: int
    received_record_count: int


@dataclass(frozen=True, slots=True)
class SourceRecordRecord:
    source_record_id: str
    dataset_id: str
    source_system: str
    source_record_key: str
    source_entity_type: str


@dataclass(frozen=True, slots=True)
class EvidenceItemRecord:
    evidence_item_id: str
    acquisition_right_id: str
    source_record_id: str
    content_sha256: str
    record_kind: str
    payload_schema_id: str
    temporal_type: str
    effective_at: datetime | None
    effective_from: datetime | None
    effective_to: datetime | None
    as_of_date: date
    published_at: datetime | None
    first_observed_at_utc: datetime | None
    received_at_utc: datetime | None
    embargo_until: datetime | None
    version: int
    revision_of: str | None
    publication_status: str
    access_context: str
    field_dictionary_version: str
    sensitivity_class: str
    licence_purpose: str
    payload: Mapping[str, JSONValue]
    canonical_entity_type: str | None = None
    canonical_entity_id: str | None = None
    manager_id: str | None = None
    strategy_id: str | None = None
    composite_id: str | None = None
    vehicle_id: str | None = None
    share_class_id: str | None = None
    mandate_id: str | None = None
    investment_id: str | None = None
    base_currency: str | None = None
    gross_net_fee_basis: str | None = None
    valuation_policy_id: str | None = None
    benchmark_id: str | None = None
    benchmark_version: str | None = None


@dataclass(frozen=True, slots=True)
class DatasetObservationRecord:
    dataset_observation_id: str
    dataset_version_id: str
    evidence_item_id: str
    observation_status: str
    disappearance_reason: str | None = None


@dataclass(frozen=True, slots=True)
class DatasetObservationPartitionLinkRecord:
    dataset_observation_partition_link_id: str
    dataset_observation_id: str
    dataset_delivery_partition_id: str


@dataclass(frozen=True, slots=True)
class EvidenceSpanRecord:
    evidence_span_id: str
    evidence_item_id: str
    json_pointer: str
    start_char: int
    end_char: int
    span_sha256: str


@dataclass(frozen=True, slots=True)
class ReconstructedDatasetVersion:
    dataset_version_id: str
    base_dataset_version_id: str
    contributing_dataset_version_ids: tuple[str, ...]
    rows: tuple[Mapping[str, JSONValue], ...]
    reconstruction_manifest_sha256: str
    reconstruction_row_count: int


@dataclass(frozen=True, slots=True)
class DatasetSliceRequest:
    dataset_id: str
    access_context: str
    evidence_right_id: str
    licence_purpose: str
    canonical_entity_ids: tuple[str, ...] = ()
    include_unresolved: bool = True
    revision_mode: str = "latest-known"
    valid_at: datetime | None = None
    valid_window: tuple[datetime, datetime] | None = None
    require_universe_membership: bool = False

    def __post_init__(self) -> None:
        if self.valid_at is not None and self.valid_window is not None:
            refuse("invalid-temporal-shape")
        if self.revision_mode not in {"latest-known", "all-known-versions"}:
            refuse("invalid-revision-mode")
        if self.valid_at is not None:
            normalize_utc(self.valid_at)
        if self.valid_window is not None:
            a, b = self.valid_window
            require(normalize_utc(a) < normalize_utc(b), "invalid-interval")


@dataclass(frozen=True, slots=True)
class SnapshotBundleRequest:
    decision_at: datetime
    sources: tuple[DatasetSliceRequest, ...]
    join_keys: tuple[str, ...]
    join_policy: str


@dataclass(frozen=True, slots=True)
class SnapshotSlice:
    request: DatasetSliceRequest
    rows: tuple[Mapping[str, JSONValue], ...]
    digest: str
    receipt_id: str | None = None
    decision_at: str | None = None


@dataclass(frozen=True, slots=True)
class SnapshotBundle:
    request: SnapshotBundleRequest
    slices: tuple[SnapshotSlice, ...]
    composite_input_digest: str
    join_receipt_id: str
    bundle_digest: str


@dataclass(frozen=True, slots=True)
class ReceiptReference:
    output_field: str
    reference_type: str
    reference_id: str
    disposition: str
    reason_code: str
    source_schema_id: str
    source_field: str
    role: str


@dataclass(frozen=True, slots=True)
class ReconstructionReceipt:
    receipt_id: str
    claim_id: str
    output_locator: str
    input_digest: str
    output_schema_id: str
    current_attestation: str
    live_attestation_ceiling: str
    algorithm_id: str
    algorithm_version: str
    parameters_sha256: str
    value_sha256: str
    references: tuple[ReceiptReference, ...]
