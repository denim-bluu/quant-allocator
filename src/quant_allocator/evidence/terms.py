from __future__ import annotations

import json
import sqlite3
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from types import MappingProxyType
from typing import Literal, Mapping, cast

from .checks import EvidenceRefusal, refuse
from .model import (
    DatasetSliceRequest,
    JSONValue,
    ReceiptReference,
    SnapshotBundle,
    SnapshotBundleRequest,
    canonical_bytes,
    digest_id,
    machine_id,
    normalize_utc,
    sha256,
    validate_identifier,
)
from .lineage import make_receipt, resolve_span, store_receipt, verify_receipt
from .snapshot import _BUNDLE_DOMAIN, as_known_bundle, snapshot_bytes

P4AccessContext = Literal[
    "public",
    "pre-hire-public",
    "shortlisted-nda",
    "funded-commingled",
    "funded-private-partnership",
    "segregated-mandate",
]

P4ProjectionKind = Literal[
    "term_document",
    "term_clause",
    "term_relation",
    "scenario_input",
    "calculation_policy",
    "method_boundary_policy",
    "predecessor_request_scaffold",
    "prior_carry_event",
    "prior_carry_allocation",
    "prior_lot_transition",
    "opening_carry_lot",
    "carry_return",
    "deal_cash_lot",
    "opening_reserve_lot",
    "materiality_policy",
    "materiality_comparison_basis",
    "rounding_policy",
]

P4_SCENARIO_DATASETS = MappingProxyType(
    {
        "public": ("dataset:p4-scenarios-public", "public-scenario-research"),
        "pre-hire-public": ("dataset:p4-scenarios-prehire", "prehire-scenario-research"),
        "shortlisted-nda": (
            "dataset:p4-scenarios-shortlisted",
            "shortlisted-scenario-diligence",
        ),
        "funded-commingled": (
            "dataset:p4-scenarios-funded-commingled",
            "commingled-scenario-monitoring",
        ),
        "funded-private-partnership": (
            "dataset:p4-scenarios-funded-private",
            "private-scenario-governance",
        ),
        "segregated-mandate": (
            "dataset:p4-scenarios-segregated",
            "segregated-scenario-governance",
        ),
    }
)

P4_POSITIVE_ENTITY_RECORDS = MappingProxyType(
    {
        "public": (
            "legal-entity:p4-public-case",
            "legal-entity",
            "Synthetic Public Terms Case",
        ),
        "pre-hire-public": (
            "legal-entity:p4-prehire-case",
            "legal-entity",
            "Synthetic Pre-Hire Terms Case",
        ),
        "shortlisted-nda": (
            "legal-entity:p4-shortlisted-case",
            "legal-entity",
            "Synthetic Shortlisted Terms Case",
        ),
        "funded-commingled": (
            "legal-entity:p4-commingled-case",
            "legal-entity",
            "Synthetic Commingled Terms Case",
        ),
        "funded-private-partnership": (
            "legal-entity:p4-private-case",
            "legal-entity",
            "Synthetic Private Partnership Terms Case",
        ),
        "segregated-mandate": (
            "legal-entity:p4-segregated-case",
            "legal-entity",
            "Synthetic Segregated Terms Case",
        ),
    }
)

P4_POSITIVE_ENTITY_BY_SCENARIO_DATASET = MappingProxyType(
    {
        P4_SCENARIO_DATASETS[context][0]: entity[0]
        for context, entity in P4_POSITIVE_ENTITY_RECORDS.items()
    }
)

_P4_PROJECTION_KINDS = frozenset(P4ProjectionKind.__args__)
_LOWER_HEX_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def _require_identifier(value: str) -> str:
    try:
        return validate_identifier(value)
    except EvidenceRefusal as exc:
        raise ValueError(f"invalid identifier: {value!r}") from exc


def _require_utc(value: str) -> str:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("decision_at must be an aware UTC timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() != UTC.utcoffset(parsed):
        raise ValueError("decision_at must be an aware UTC timestamp")
    return parsed.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _require_sha256(value: str, field_name: str) -> str:
    if not _LOWER_HEX_SHA256.fullmatch(value):
        raise ValueError(f"{field_name} must be a lowercase 64-hex SHA-256 digest")
    return value


def _freeze_json(value):
    if isinstance(value, float):
        raise TypeError("float values are prohibited in P4 controlled payloads")
    if isinstance(value, Mapping):
        if any(not isinstance(key, str) for key in value):
            raise TypeError("P4 controlled payload keys must be strings")
        return MappingProxyType({key: _freeze_json(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_json(item) for item in value)
    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, datetime):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("P4 controlled datetimes must be aware UTC values")
        return value.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    raise TypeError(f"unsupported P4 controlled payload value: {type(value).__name__}")


def _detach_bundle_request(request: SnapshotBundleRequest) -> SnapshotBundleRequest:
    if request.decision_at.tzinfo is None or request.decision_at.utcoffset() is None:
        raise ValueError("predecessor bundle decision_at must be an aware UTC timestamp")
    sources = tuple(
        DatasetSliceRequest(
            dataset_id=source.dataset_id,
            access_context=source.access_context,
            evidence_right_id=source.evidence_right_id,
            licence_purpose=source.licence_purpose,
            canonical_entity_ids=tuple(source.canonical_entity_ids),
            include_unresolved=source.include_unresolved,
            revision_mode=source.revision_mode,
            valid_at=source.valid_at,
            valid_window=None if source.valid_window is None else tuple(source.valid_window),
            require_universe_membership=source.require_universe_membership,
        )
        for source in request.sources
    )
    return SnapshotBundleRequest(
        decision_at=request.decision_at.astimezone(UTC),
        sources=sources,
        join_keys=tuple(request.join_keys),
        join_policy=request.join_policy,
    )


@dataclass(frozen=True, slots=True)
class P4ProjectionLineage:
    evidence_item_id: str
    evidence_span_id: str
    source_record_id: str
    dataset_observation_id: str
    dataset_version_id: str
    evidence_right_id: str
    dataset_delivery_partition_id: str
    dataset_observation_partition_link_id: str
    snapshot_digest: str
    slice_receipt_id: str
    join_receipt_id: str
    decision_at: str
    source_schema_id: str
    source_field: str

    def __post_init__(self) -> None:
        for value in (
            self.evidence_item_id,
            self.evidence_span_id,
            self.source_record_id,
            self.dataset_observation_id,
            self.dataset_version_id,
            self.evidence_right_id,
            self.dataset_delivery_partition_id,
            self.dataset_observation_partition_link_id,
            self.snapshot_digest,
            self.slice_receipt_id,
            self.join_receipt_id,
            self.source_schema_id,
        ):
            _require_identifier(value)
        object.__setattr__(self, "decision_at", _require_utc(self.decision_at))
        if not self.source_field.startswith("/"):
            raise ValueError("source_field must be a JSON pointer")


@dataclass(frozen=True, slots=True)
class P4TermProjection:
    projection_id: str
    projection_kind: P4ProjectionKind
    record_key: str
    scenario_id: str | None
    document_key: str | None
    payload: Mapping[str, JSONValue]
    lineage: P4ProjectionLineage
    projection_receipt_id: str

    def __post_init__(self) -> None:
        _require_identifier(self.projection_id)
        _require_identifier(self.record_key)
        _require_identifier(self.projection_receipt_id)
        if self.scenario_id is not None:
            _require_identifier(self.scenario_id)
        if self.document_key is not None:
            _require_identifier(self.document_key)
        if self.projection_kind not in _P4_PROJECTION_KINDS:
            raise ValueError(f"unknown projection kind: {self.projection_kind!r}")
        object.__setattr__(self, "payload", cast(Mapping[str, JSONValue], _freeze_json(self.payload)))


@dataclass(frozen=True, slots=True)
class PredecessorRequestScaffoldRecord:
    projection_id: str
    expected_predecessor_scenario_id: str
    predecessor_bundle_request: SnapshotBundleRequest
    predecessor_request_digest: str
    lineage: P4ProjectionLineage
    projection_receipt_id: str

    def __post_init__(self) -> None:
        _require_identifier(self.projection_id)
        _require_identifier(self.expected_predecessor_scenario_id)
        _require_identifier(self.projection_receipt_id)
        object.__setattr__(
            self,
            "predecessor_bundle_request",
            _detach_bundle_request(self.predecessor_bundle_request),
        )
        _require_sha256(self.predecessor_request_digest, "predecessor_request_digest")


@dataclass(frozen=True, slots=True)
class P4TermProjectionSet:
    bundle_digest: str
    decision_at: str
    rows: tuple[P4TermProjection, ...]
    projection_digest: str

    def __post_init__(self) -> None:
        _require_identifier(self.bundle_digest)
        object.__setattr__(self, "decision_at", _require_utc(self.decision_at))
        object.__setattr__(self, "rows", tuple(self.rows))
        _require_sha256(self.projection_digest, "projection_digest")
        identifiers = tuple(row.projection_id for row in self.rows)
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("duplicate P4 projection identifier")

    def rows_of_kind(self, kind: P4ProjectionKind) -> tuple[P4TermProjection, ...]:
        if kind not in _P4_PROJECTION_KINDS:
            raise ValueError(f"unknown projection kind: {kind!r}")
        return tuple(row for row in self.rows if row.projection_kind == kind)

    def require_record(self, projection_id: str) -> P4TermProjection:
        _require_identifier(projection_id)
        rows = tuple(row for row in self.rows if row.projection_id == projection_id)
        if len(rows) != 1:
            raise KeyError(projection_id)
        return rows[0]


def load_p4_term_projections(
    conn: sqlite3.Connection, bundle: SnapshotBundle
) -> P4TermProjectionSet:
    return _build_p4_projection_set(conn, bundle, persist=False)


def verify_p4_projection_receipt(
    conn: sqlite3.Connection,
    bundle: SnapshotBundle,
    projection: P4TermProjection,
) -> None:
    expected = tuple(
        row
        for row in _build_p4_projection_set(conn, bundle, persist=False).rows
        if row.projection_id == projection.projection_id
    )
    if len(expected) != 1 or expected[0] != projection:
        refuse("receipt-incomplete")
    verify_receipt(conn, projection.projection_receipt_id, bundle)


def _validate_p4_bundle_persistence(
    conn: sqlite3.Connection, bundle: SnapshotBundle
) -> None:
    from .fixtures.terms import (
        P4_METHOD_POLICY_DATASET,
        P4_TERMS_CUTOFFS,
        p4_method_policy_bundle_request,
        p4_terms_bundle_request,
    )

    dataset_ids = tuple(source.dataset_id for source in bundle.request.sources)
    if dataset_ids == (P4_METHOD_POLICY_DATASET[0],):
        authoritative = p4_method_policy_bundle_request()
    else:
        context = validate_p4_positive_bundle_request(bundle.request)
        cutoff_names = tuple(
            name
            for name, cutoff in P4_TERMS_CUTOFFS.items()
            if normalize_utc(cutoff) == normalize_utc(bundle.request.decision_at)
        )
        if len(cutoff_names) != 1:
            refuse("p4-term-bundle-request-invalid")
        authoritative = p4_terms_bundle_request(
            cutoff_name=cutoff_names[0], access_context=context
        )
    if bundle.request != authoritative:
        refuse("p4-term-bundle-request-invalid")
    if tuple(slice_.request for slice_ in bundle.slices) != bundle.request.sources:
        refuse("p4-term-bundle-request-invalid")
    cutoff = normalize_utc(bundle.request.decision_at)
    for slice_ in bundle.slices:
        if slice_.decision_at != cutoff or slice_.receipt_id is None:
            refuse("receipt-incomplete")
        expected_snapshot = digest_id(
            "snapshot", {"bytes_sha256": sha256(snapshot_bytes(slice_))}
        )
        if slice_.digest != expected_snapshot:
            refuse("receipt-incomplete")
        manifest = conn.execute(
            "SELECT * FROM snapshot_manifest WHERE snapshot_digest=?", (slice_.digest,)
        ).fetchone()
        request_json = canonical_bytes(
            {"request": slice_.request, "decision_at": cutoff}
        ).decode()
        records_sha256 = sha256(
            b"".join(canonical_bytes(row) + b"\n" for row in slice_.rows)
        )
        if (
            manifest is None
            or manifest["request_json"] != request_json
            or manifest["row_count"] != len(slice_.rows)
            or manifest["records_sha256"] != records_sha256
        ):
            refuse("p4-term-bundle-request-invalid")
        slice_receipt = conn.execute(
            "SELECT * FROM reconstruction_receipt WHERE receipt_id=?",
            (slice_.receipt_id,),
        ).fetchone()
        if (
            slice_receipt is None
            or slice_receipt["claim_id"] != "claim:snapshot-slice"
            or slice_receipt["input_digest"] != slice_.digest
            or slice_receipt["algorithm_id"] != "as-known-slice"
            or slice_receipt["parameters_sha256"]
            != sha256(
                canonical_bytes({"request": slice_.request, "decision_at": cutoff})
            )
            or slice_receipt["value_sha256"] != sha256(canonical_bytes(slice_.rows))
        ):
            refuse("receipt-incomplete")
        verify_receipt(conn, slice_.receipt_id, bundle)
    pairs = tuple((slice_.request.dataset_id, slice_.digest) for slice_ in bundle.slices)
    expected_composite = sha256(
        _BUNDLE_DOMAIN
        + canonical_bytes({"request": bundle.request, "slices": pairs})
    )
    expected_bundle_digest = digest_id(
        "bundle",
        {
            "request": bundle.request,
            "slices": pairs,
            "join_receipt_id": bundle.join_receipt_id,
        },
    )
    persisted = conn.execute(
        "SELECT * FROM snapshot_bundle_manifest WHERE bundle_digest=?",
        (bundle.bundle_digest,),
    ).fetchone()
    if (
        bundle.composite_input_digest != expected_composite
        or bundle.bundle_digest != expected_bundle_digest
        or persisted is None
        or persisted["request_json"] != canonical_bytes(bundle.request).decode()
        or persisted["slice_digests_json"] != canonical_bytes(pairs).decode()
        or persisted["composite_input_digest"] != bundle.composite_input_digest
        or persisted["join_receipt_id"] != bundle.join_receipt_id
        or persisted["row_count"] != sum(len(slice_.rows) for slice_ in bundle.slices)
        or persisted["records_sha256"]
        != sha256(b"".join(snapshot_bytes(slice_) for slice_ in bundle.slices))
    ):
        refuse("p4-term-bundle-request-invalid")
    join_receipt = conn.execute(
        "SELECT * FROM reconstruction_receipt WHERE receipt_id=?",
        (bundle.join_receipt_id,),
    ).fetchone()
    if (
        join_receipt is None
        or join_receipt["claim_id"] != "claim:snapshot-join"
        or join_receipt["input_digest"] != expected_composite
        or join_receipt["algorithm_id"] != bundle.request.join_policy
        or join_receipt["parameters_sha256"]
        != sha256(canonical_bytes({"join_keys": bundle.request.join_keys}))
        or join_receipt["value_sha256"] != sha256(canonical_bytes(pairs))
    ):
        refuse("receipt-incomplete")
    verify_receipt(conn, bundle.join_receipt_id, bundle)


def _p4_projection_receipt(
    *,
    bundle: SnapshotBundle,
    projection_id: str,
    projection_kind: P4ProjectionKind,
    payload: Mapping[str, JSONValue],
    lineage: P4ProjectionLineage,
):
    output_locator = f"/projections/{projection_id}"
    parameters = {
        "bundle_digest": bundle.bundle_digest,
        "decision_at": lineage.decision_at,
        "snapshot_digest": lineage.snapshot_digest,
        "slice_receipt_id": lineage.slice_receipt_id,
        "join_receipt_id": lineage.join_receipt_id,
        "projection_id": projection_id,
        "projection_kind": projection_kind,
    }
    value = {"payload": payload, "lineage": lineage}
    references = tuple(
        ReceiptReference(
            output_locator,
            reference_type,
            reference_id,
            "included",
            "",
            lineage.source_schema_id,
            "/source_text" if reference_type == "evidence-span" else "/",
            role,
        )
        for reference_type, reference_id, role in (
            ("evidence-item", lineage.evidence_item_id, "input"),
            ("source-record", lineage.source_record_id, "input"),
            ("dataset-observation", lineage.dataset_observation_id, "denominator"),
            ("evidence-span", lineage.evidence_span_id, "term"),
            ("evidence-right", lineage.evidence_right_id, "filter"),
            ("dataset-version", lineage.dataset_version_id, "denominator"),
            (
                "dataset-delivery-partition",
                lineage.dataset_delivery_partition_id,
                "denominator",
            ),
            (
                "dataset-observation-partition-link",
                lineage.dataset_observation_partition_link_id,
                "denominator",
            ),
            ("snapshot", lineage.snapshot_digest, "input"),
        )
    )
    return make_receipt(
        claim_id="claim:p4-term-projection",
        output_locator=output_locator,
        input_digest=sha256(canonical_bytes({"parameters": parameters, "value": value})),
        output_schema_id=lineage.source_schema_id,
        current_attestation="D",
        live_attestation_ceiling="B",
        algorithm_id="p4-payload-projection",
        algorithm_version="1",
        parameters=parameters,
        value=value,
        references=references,
    )


def _p4_projection_from_row(
    conn: sqlite3.Connection,
    bundle: SnapshotBundle,
    slice_,
    row: Mapping[str, JSONValue],
    *,
    persist: bool,
) -> P4TermProjection:
    payload = row.get("payload")
    if not isinstance(payload, Mapping):
        refuse("payload-schema-mismatch")
    required = {
        "record_key",
        "projection_kind",
        "classification",
        "source_text",
        "span_marker",
        "value",
    }
    if set(payload) != required:
        refuse("payload-schema-mismatch")
    projection_kind = payload["projection_kind"]
    if not isinstance(projection_kind, str) or projection_kind not in _P4_PROJECTION_KINDS:
        refuse("payload-schema-mismatch")
    projection_kind = cast(P4ProjectionKind, projection_kind)
    record_key = payload["record_key"]
    value = payload["value"]
    if not isinstance(record_key, str) or not isinstance(value, Mapping):
        refuse("payload-schema-mismatch")
    item = conn.execute(
        """SELECT i.*,s.dataset_id FROM evidence_item i
           JOIN source_record s USING(source_record_id)
           WHERE i.evidence_item_id=?""",
        (row["evidence_item_id"],),
    ).fetchone()
    source = (
        conn.execute(
            "SELECT * FROM source_record WHERE source_record_id=?",
            (item["source_record_id"],),
        ).fetchone()
        if item is not None
        else None
    )
    expected_schema_id = f"schema:p4-{projection_kind.replace('_', '-')}-v1"
    schema = conn.execute(
        "SELECT * FROM payload_schema WHERE payload_schema_id=?",
        (expected_schema_id,),
    ).fetchone()
    if (
        item is None
        or source is None
        or schema is None
        or item["payload_schema_id"] != expected_schema_id
        or item["record_kind"] != projection_kind.replace("_", "-")
        or schema["record_kind"] != item["record_kind"]
        or json.loads(item["payload_json"]) != payload
        or item["content_sha256"] != sha256(canonical_bytes(payload))
        or item["dataset_id"] != slice_.request.dataset_id
        or item["source_record_id"] != row["source_record_id"]
        or item["acquisition_right_id"] != slice_.request.evidence_right_id
        or machine_id(
            "source-record",
            {
                "dataset_id": source["dataset_id"],
                "source_system": source["source_system"],
                "source_record_key": source["source_record_key"],
            },
        )
        != source["source_record_id"]
        or machine_id(
            "evidence",
            {
                "source_record_id": item["source_record_id"],
                "version": item["version"],
            },
        )
        != item["evidence_item_id"]
        or sha256(canonical_bytes(json.loads(schema["schema_json"])))
        != schema["schema_sha256"]
    ):
        refuse("payload-schema-mismatch")
    right = conn.execute(
        "SELECT * FROM evidence_right WHERE evidence_right_id=?",
        (item["acquisition_right_id"],),
    ).fetchone()
    if right is None or machine_id(
        "right",
        {
            "right_series_id": right["right_series_id"],
            "right_version": right["right_version"],
            "dataset_id": right["dataset_id"],
            "access_context": right["access_context"],
            "licence_purpose": right["licence_purpose"],
            "status": right["status"],
            "retention_policy": right["retention_policy"],
            "received_at_utc": right["received_at_utc"],
            "entitlement_from": right["entitlement_from"],
            "entitlement_to": right["entitlement_to"],
            "supersedes_right_id": right["supersedes_right_id"],
        },
    ) != right["evidence_right_id"]:
        refuse("machine-id-mismatch")
    spans = conn.execute(
        "SELECT * FROM evidence_span WHERE evidence_item_id=? ORDER BY evidence_span_id",
        (item["evidence_item_id"],),
    ).fetchall()
    if len(spans) != 1 or spans[0]["json_pointer"] != "/source_text":
        refuse("receipt-incomplete")
    if machine_id(
        "span",
        {
            "evidence_item_id": spans[0]["evidence_item_id"],
            "json_pointer": spans[0]["json_pointer"],
            "start_char": spans[0]["start_char"],
            "end_char": spans[0]["end_char"],
            "span_sha256": spans[0]["span_sha256"],
        },
    ) != spans[0]["evidence_span_id"]:
        refuse("machine-id-mismatch")
    resolved = resolve_span(conn, spans[0]["evidence_span_id"])
    if (
        resolved["text"] != payload["span_marker"]
        or not isinstance(payload["source_text"], str)
        or payload["source_text"].count(str(payload["span_marker"])) != 1
    ):
        refuse("content-hash-mismatch")
    observation = conn.execute(
        "SELECT * FROM dataset_observation WHERE dataset_observation_id=? "
        "AND evidence_item_id=?",
        (row["dataset_observation_id"], item["evidence_item_id"]),
    ).fetchone()
    links = (
        conn.execute(
            "SELECT * FROM dataset_observation_partition_link "
            "WHERE dataset_observation_id=?",
            (observation["dataset_observation_id"],),
        ).fetchall()
        if observation is not None
        else ()
    )
    partition = (
        conn.execute(
            "SELECT * FROM dataset_delivery_partition "
            "WHERE dataset_delivery_partition_id=?",
            (links[0]["dataset_delivery_partition_id"],),
        ).fetchone()
        if len(links) == 1
        else None
    )
    version = (
        conn.execute(
            "SELECT * FROM dataset_version WHERE dataset_version_id=?",
            (observation["dataset_version_id"],),
        ).fetchone()
        if observation is not None
        else None
    )
    if (
        observation is None
        or len(links) != 1
        or partition is None
        or version is None
        or observation["dataset_version_id"] != partition["dataset_version_id"]
    ):
        refuse("receipt-incomplete")
    if machine_id(
        "dataset-observation",
        {
            "dataset_version_id": observation["dataset_version_id"],
            "evidence_item_id": observation["evidence_item_id"],
            "observation_status": observation["observation_status"],
        },
    ) != observation["dataset_observation_id"]:
        refuse("machine-id-mismatch")
    if machine_id(
        "dataset-observation-partition",
        {
            "dataset_observation_id": links[0]["dataset_observation_id"],
            "dataset_delivery_partition_id": links[0][
                "dataset_delivery_partition_id"
            ],
        },
    ) != links[0]["dataset_observation_partition_link_id"]:
        refuse("machine-id-mismatch")
    if machine_id(
        "dataset-partition",
        {
            "dataset_version_id": partition["dataset_version_id"],
            "partition_key": partition["partition_key"],
            "partition_status": partition["partition_status"],
            "manifest_evidence_item_id": partition["manifest_evidence_item_id"],
            "manifest_evidence_span_id": partition["manifest_evidence_span_id"],
            "received_content_sha256": partition["received_content_sha256"],
            "expected_record_count": partition["expected_record_count"],
            "received_record_count": partition["received_record_count"],
        },
    ) != partition["dataset_delivery_partition_id"]:
        refuse("machine-id-mismatch")
    if machine_id(
        "dataset-version",
        {
            "dataset_id": version["dataset_id"],
            "version_label": version["version_label"],
            "acquisition_right_id": version["acquisition_right_id"],
            "published_at": version["published_at"],
            "first_observed_at_utc": version["first_observed_at_utc"],
            "received_at_utc": version["received_at_utc"],
            "embargo_until": version["embargo_until"],
            "content_sha256": version["content_sha256"],
            "delivery_mode": version["delivery_mode"],
            "absence_semantics": version["absence_semantics"],
            "completeness_status": version["completeness_status"],
            "expected_partition_manifest_sha256": version[
                "expected_partition_manifest_sha256"
            ],
            "received_partition_manifest_sha256": version[
                "received_partition_manifest_sha256"
            ],
            "expected_partition_count": version["expected_partition_count"],
            "received_partition_count": version["received_partition_count"],
            "predecessor_dataset_version_id": version[
                "predecessor_dataset_version_id"
            ],
            "base_dataset_version_id": version["base_dataset_version_id"],
            "reconstruction_manifest_sha256": version[
                "reconstruction_manifest_sha256"
            ],
            "reconstruction_row_count": version["reconstruction_row_count"],
        },
    ) != version["dataset_version_id"]:
        refuse("machine-id-mismatch")
    decision_at = normalize_utc(bundle.request.decision_at)
    lineage_without_receipts = {
        "evidence_item_id": item["evidence_item_id"],
        "evidence_span_id": spans[0]["evidence_span_id"],
        "source_record_id": item["source_record_id"],
        "dataset_observation_id": observation["dataset_observation_id"],
        "dataset_version_id": observation["dataset_version_id"],
        "evidence_right_id": item["acquisition_right_id"],
        "dataset_delivery_partition_id": partition["dataset_delivery_partition_id"],
        "dataset_observation_partition_link_id": links[0][
            "dataset_observation_partition_link_id"
        ],
        "snapshot_digest": slice_.digest,
        "decision_at": decision_at,
        "source_schema_id": expected_schema_id,
        "source_field": "/source_text",
    }
    scenario_id = value.get("scenario_id")
    document_key = value.get("document_id") or value.get("document_key")
    if scenario_id is not None and not isinstance(scenario_id, str):
        refuse("payload-schema-mismatch")
    if document_key is not None and not isinstance(document_key, str):
        refuse("payload-schema-mismatch")
    projection_id = digest_id(
        "p4-term-projection",
        {
            "projection_kind": projection_kind,
            "record_key": record_key,
            "scenario_id": scenario_id,
            "document_key": document_key,
            "decision_at": decision_at,
            "payload": payload,
            "lineage": lineage_without_receipts,
        },
    )
    lineage = P4ProjectionLineage(
        **lineage_without_receipts,
        slice_receipt_id=slice_.receipt_id,
        join_receipt_id=bundle.join_receipt_id,
    )
    receipt = _p4_projection_receipt(
        bundle=bundle,
        projection_id=projection_id,
        projection_kind=projection_kind,
        payload=payload,
        lineage=lineage,
    )
    if persist:
        store_receipt(conn, receipt)
    else:
        persisted = conn.execute(
            "SELECT receipt_id FROM reconstruction_receipt WHERE receipt_id=?",
            (receipt.receipt_id,),
        ).fetchone()
        if persisted is None:
            refuse("receipt-incomplete")
    projection = P4TermProjection(
        projection_id=projection_id,
        projection_kind=projection_kind,
        record_key=record_key,
        scenario_id=cast(str | None, scenario_id),
        document_key=cast(str | None, document_key),
        payload=payload,
        lineage=lineage,
        projection_receipt_id=receipt.receipt_id,
    )
    verify_receipt(conn, receipt.receipt_id, bundle)
    return projection


def _build_p4_projection_set(
    conn: sqlite3.Connection, bundle: SnapshotBundle, *, persist: bool
) -> P4TermProjectionSet:
    _validate_p4_bundle_persistence(conn, bundle)
    rows = tuple(
        sorted(
            (
                _p4_projection_from_row(
                    conn, bundle, slice_, row, persist=persist
                )
                for slice_ in bundle.slices
                for row in slice_.rows
            ),
            key=lambda row: row.projection_id,
        )
    )
    if len(rows) != sum(len(slice_.rows) for slice_ in bundle.slices):
        refuse("receipt-incomplete")
    identifiers = tuple(row.projection_id for row in rows)
    if len(identifiers) != len(set(identifiers)):
        refuse("receipt-incomplete")
    from .fixtures.terms import P4_METHOD_POLICY_DATASET

    dataset_ids = tuple(source.dataset_id for source in bundle.request.sources)
    kinds = tuple(row.projection_kind for row in rows)
    if dataset_ids == (P4_METHOD_POLICY_DATASET[0],):
        if kinds != ("method_boundary_policy",):
            refuse("payload-schema-mismatch")
    elif (
        "scenario_input" not in kinds
        or "calculation_policy" not in kinds
        or "method_boundary_policy" in kinds
    ):
        refuse("payload-schema-mismatch")
    return P4TermProjectionSet(
        bundle_digest=bundle.bundle_digest,
        decision_at=normalize_utc(bundle.request.decision_at),
        rows=rows,
        projection_digest=sha256(
            canonical_bytes(
                tuple(
                    {
                        "projection_id": row.projection_id,
                        "projection_kind": row.projection_kind,
                        "record_key": row.record_key,
                        "scenario_id": row.scenario_id,
                        "document_key": row.document_key,
                        "payload": row.payload,
                        "lineage": row.lineage,
                        "projection_receipt_id": row.projection_receipt_id,
                    }
                    for row in rows
                )
            )
        ),
    )


def _persist_p4_term_projections(
    conn: sqlite3.Connection, bundle: SnapshotBundle
) -> P4TermProjectionSet:
    return _build_p4_projection_set(conn, bundle, persist=True)


def _decode_p4_bundle_request(request_json: str) -> SnapshotBundleRequest:
    try:
        raw = json.loads(request_json)
        sources = tuple(
            DatasetSliceRequest(
                dataset_id=source["dataset_id"],
                access_context=source["access_context"],
                evidence_right_id=source["evidence_right_id"],
                licence_purpose=source["licence_purpose"],
                canonical_entity_ids=tuple(source["canonical_entity_ids"]),
                include_unresolved=source["include_unresolved"],
                revision_mode=source["revision_mode"],
                valid_at=(
                    None
                    if source["valid_at"] is None
                    else datetime.fromisoformat(source["valid_at"].replace("Z", "+00:00"))
                ),
                valid_window=(
                    None
                    if source["valid_window"] is None
                    else tuple(
                        datetime.fromisoformat(item.replace("Z", "+00:00"))
                        for item in source["valid_window"]
                    )
                ),
                require_universe_membership=source["require_universe_membership"],
            )
            for source in raw["sources"]
        )
        request = SnapshotBundleRequest(
            decision_at=datetime.fromisoformat(raw["decision_at"].replace("Z", "+00:00")),
            sources=sources,
            join_keys=tuple(raw["join_keys"]),
            join_policy=raw["join_policy"],
        )
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        refuse("predecessor-scaffold-invalid")
    if canonical_bytes(request).decode() != request_json:
        refuse("predecessor-scaffold-invalid")
    return request


def _require_persisted_p4_bundle(
    conn: sqlite3.Connection,
    request: SnapshotBundleRequest,
    *,
    bundle_digest: str | None = None,
) -> SnapshotBundle:
    request_json = canonical_bytes(request).decode()
    manifests = conn.execute(
        "SELECT * FROM snapshot_bundle_manifest WHERE request_json=?", (request_json,)
    ).fetchall()
    if len(manifests) != 1 or (
        bundle_digest is not None and manifests[0]["bundle_digest"] != bundle_digest
    ):
        refuse("predecessor-scaffold-invalid")
    bundle = as_known_bundle(conn, request)
    if bundle.bundle_digest != manifests[0]["bundle_digest"]:
        refuse("predecessor-scaffold-invalid")
    _validate_p4_bundle_persistence(conn, bundle)
    return bundle


def _validate_predecessor_projection_closure(
    candidate: P4TermProjection, authoritative: P4TermProjection
) -> None:
    if (
        candidate.projection_id != authoritative.projection_id
        or candidate.record_key != authoritative.record_key
        or candidate.payload != authoritative.payload
        or candidate.lineage != authoritative.lineage
        or candidate.projection_receipt_id != authoritative.projection_receipt_id
    ):
        refuse("predecessor-scaffold-invalid")


def _validate_p29_continuity(
    projection_set: P4TermProjectionSet, context: str, cutoff_name: str
) -> None:
    from .fixtures.terms import _p4_scenario_dependency_specs

    scenario_ids = {
        "early": ("p4-p29a",),
        "amended": ("p4-p29a", "p4-p29b"),
        "side-letter": ("p4-p29a", "p4-p29b", "p4-p29c"),
    }
    try:
        expected = tuple(
            (record_key, value)
            for scenario_id in scenario_ids[cutoff_name]
            for record_key, kind, value in _p4_scenario_dependency_specs(
                context, scenario_id
            )
            if kind in {"deal_cash_lot", "opening_reserve_lot"}
        )
    except KeyError:
        refuse("predecessor-scaffold-invalid")
    actual_rows = tuple(
        row
        for row in projection_set.rows
        if row.projection_kind in {"deal_cash_lot", "opening_reserve_lot"}
        and ":p4-p29" in row.record_key
        and row.record_key.endswith(f":{context}")
    )
    try:
        actual_rows = tuple(
            sorted(actual_rows, key=lambda row: row.payload["value"]["continuity_order"])
        )
    except (KeyError, TypeError):
        refuse("predecessor-scaffold-invalid")
    if tuple((row.record_key, row.payload["value"]) for row in actual_rows) != expected:
        refuse("predecessor-scaffold-invalid")


def _validate_predecessor_request_closure(
    value: Mapping[str, JSONValue],
    projection_id: str,
    expected_scenario: str,
    predecessor_cutoff_name: str,
    context: P4AccessContext,
) -> SnapshotBundleRequest:
    from .fixtures.terms import P4_TERMS_CUTOFFS, p4_terms_bundle_request

    required = {
        "scaffold_id",
        "expected_predecessor_scenario_id",
        "predecessor_cutoff",
        "predecessor_source_dataset_ids",
        "predecessor_join_keys",
        "predecessor_join_policy",
        "predecessor_request_json",
        "predecessor_request_digest",
    }
    if set(value) != required or not isinstance(value["predecessor_request_json"], str):
        refuse("predecessor-scaffold-invalid")
    request = _decode_p4_bundle_request(cast(str, value["predecessor_request_json"]))
    authoritative = p4_terms_bundle_request(
        cutoff_name=predecessor_cutoff_name, access_context=context
    )
    if (
        request != authoritative
        or value["scaffold_id"] != projection_id
        or value["expected_predecessor_scenario_id"] != expected_scenario
        or value["predecessor_cutoff"]
        != normalize_utc(P4_TERMS_CUTOFFS[predecessor_cutoff_name])
        or tuple(cast(tuple[str, ...], value["predecessor_source_dataset_ids"]))
        != tuple(source.dataset_id for source in request.sources)
        or tuple(cast(tuple[str, ...], value["predecessor_join_keys"]))
        != request.join_keys
        or value["predecessor_join_policy"] != request.join_policy
        or value["predecessor_request_digest"] != sha256(canonical_bytes(request))
    ):
        refuse("predecessor-scaffold-invalid")
    return request


def load_predecessor_request_scaffold(
    conn: sqlite3.Connection,
    projection_set: P4TermProjectionSet,
    projection_id: str,
) -> PredecessorRequestScaffoldRecord:
    from .fixtures.terms import P4_TERMS_CUTOFFS, p4_terms_bundle_request

    expected_scaffolds = {
        "scaffold:p4-p29b-from-p29a": ("p4-p29a", "early", "amended"),
        "scaffold:p4-p29c-from-p29b": ("p4-p29b", "amended", "side-letter"),
    }
    try:
        expected_scenario, predecessor_cutoff_name, current_cutoff_name = (
            expected_scaffolds[projection_id]
        )
    except KeyError:
        refuse("predecessor-scaffold-invalid")

    current_cutoff = normalize_utc(P4_TERMS_CUTOFFS[current_cutoff_name])
    if projection_set.decision_at != current_cutoff:
        refuse("predecessor-scaffold-invalid")
    current_manifests = conn.execute(
        "SELECT request_json FROM snapshot_bundle_manifest WHERE bundle_digest=?",
        (projection_set.bundle_digest,),
    ).fetchall()
    if len(current_manifests) != 1:
        refuse("predecessor-scaffold-invalid")
    current_request = _decode_p4_bundle_request(current_manifests[0]["request_json"])
    current_bundle = _require_persisted_p4_bundle(
        conn, current_request, bundle_digest=projection_set.bundle_digest
    )
    authoritative_projection_set = load_p4_term_projections(conn, current_bundle)
    if projection_set != authoritative_projection_set:
        refuse("predecessor-scaffold-invalid")
    expected_projection_digest = sha256(
        canonical_bytes(
            tuple(
                {
                    "projection_id": row.projection_id,
                    "projection_kind": row.projection_kind,
                    "record_key": row.record_key,
                    "scenario_id": row.scenario_id,
                    "document_key": row.document_key,
                    "payload": row.payload,
                    "lineage": row.lineage,
                    "projection_receipt_id": row.projection_receipt_id,
                }
                for row in projection_set.rows
            )
        )
    )
    if projection_set.projection_digest != expected_projection_digest:
        refuse("predecessor-scaffold-invalid")

    matching = tuple(
        row
        for row in projection_set.rows
        if row.record_key.startswith(f"{projection_id}:")
    )
    if len(matching) != 1:
        refuse("predecessor-scaffold-invalid")
    row = matching[0]
    if row.projection_kind != "predecessor_request_scaffold":
        refuse("predecessor-scaffold-invalid")
    authoritative_rows = tuple(
        candidate
        for candidate in authoritative_projection_set.rows
        if candidate.record_key == row.record_key
    )
    if len(authoritative_rows) != 1:
        refuse("predecessor-scaffold-invalid")
    _validate_predecessor_projection_closure(row, authoritative_rows[0])
    context = row.record_key.removeprefix(f"{projection_id}:")
    value = row.payload.get("value")
    required = {
        "scaffold_id",
        "expected_predecessor_scenario_id",
        "predecessor_cutoff",
        "predecessor_source_dataset_ids",
        "predecessor_join_keys",
        "predecessor_join_policy",
        "predecessor_request_json",
        "predecessor_request_digest",
    }
    if not isinstance(value, Mapping) or set(value) != required:
        refuse("predecessor-scaffold-invalid")
    request_json = value["predecessor_request_json"]
    if not isinstance(request_json, str):
        refuse("predecessor-scaffold-invalid")
    request = _validate_predecessor_request_closure(
        cast(Mapping[str, JSONValue], value),
        projection_id,
        expected_scenario,
        predecessor_cutoff_name,
        cast(P4AccessContext, context),
    )
    authoritative = p4_terms_bundle_request(
        cutoff_name=predecessor_cutoff_name, access_context=cast(P4AccessContext, context)
    )
    if (
        request != authoritative
        or value["scaffold_id"] != projection_id
        or value["expected_predecessor_scenario_id"] != expected_scenario
        or value["predecessor_cutoff"]
        != normalize_utc(P4_TERMS_CUTOFFS[predecessor_cutoff_name])
        or tuple(value["predecessor_source_dataset_ids"])
        != tuple(source.dataset_id for source in request.sources)
        or tuple(value["predecessor_join_keys"]) != request.join_keys
        or value["predecessor_join_policy"] != request.join_policy
        or value["predecessor_request_digest"] != sha256(canonical_bytes(request))
    ):
        refuse("predecessor-scaffold-invalid")
    predecessor_bundle = _require_persisted_p4_bundle(conn, request)
    predecessor_projection_set = load_p4_term_projections(conn, predecessor_bundle)
    continuity_contracts = {
        "early": (
            (f"deal-cash-lot:p4-p29a:a:{context}", {
                "lot_id": "lot:p4-p29a:a-cash",
                "lot_family": "deal-cash",
                "amount": "120",
                "deal_id": "deal:A",
                "source_event": "event:p4-p29a:realization",
                "source_allocation_id": "allocation:p4-p29a:a-reserve",
                "currency": "USD",
                "economic_balance": "120",
                "settled_balance": "120",
                "continuity_order": 1,
            }),
        ),
        "amended": (
            (f"deal-cash-lot:p4-p29a:a:{context}", {
                "lot_id": "lot:p4-p29a:a-cash",
                "lot_family": "deal-cash",
                "amount": "120",
                "deal_id": "deal:A",
                "source_event": "event:p4-p29a:realization",
                "source_allocation_id": "allocation:p4-p29a:a-reserve",
                "currency": "USD",
                "economic_balance": "120",
                "settled_balance": "120",
                "continuity_order": 1,
            }),
            (f"opening-reserve-lot:p4-p29b:a:{context}", {
                "lot_id": "lot:p4-p29a:a-reserve",
                "lot_family": "opening-reserve",
                "original": "20",
                "remaining": "20",
                "source_cash_lot_id": "lot:p4-p29a:a-cash",
                "source_event_id": "event:p4-p29a:realization",
                "source_allocation_id": "allocation:p4-p29a:a-reserve",
                "deal_id": "deal:A",
                "currency": "USD",
                "economic_balance": "20",
                "settled_balance": "20",
                "continuity_order": 2,
            }),
            (f"deal-cash-lot:p4-p29b:b:{context}", {
                "lot_id": "lot:p4-p29b:b-cash",
                "lot_family": "deal-cash",
                "amount": "10",
                "deal_id": "deal:B",
                "source_event": "event:p4-p29b:reserve-add",
                "source_allocation_id": "allocation:p4-p29b:b-reserve",
                "currency": "USD",
                "economic_balance": "10",
                "settled_balance": "10",
                "continuity_order": 3,
            }),
        ),
        "side-letter": (
            (f"deal-cash-lot:p4-p29a:a:{context}", {
                "lot_id": "lot:p4-p29a:a-cash",
                "lot_family": "deal-cash",
                "amount": "120",
                "deal_id": "deal:A",
                "source_event": "event:p4-p29a:realization",
                "source_allocation_id": "allocation:p4-p29a:a-reserve",
                "currency": "USD",
                "economic_balance": "120",
                "settled_balance": "120",
                "continuity_order": 1,
            }),
            (f"opening-reserve-lot:p4-p29b:a:{context}", {
                "lot_id": "lot:p4-p29a:a-reserve",
                "lot_family": "opening-reserve",
                "original": "20",
                "remaining": "20",
                "source_cash_lot_id": "lot:p4-p29a:a-cash",
                "source_event_id": "event:p4-p29a:realization",
                "source_allocation_id": "allocation:p4-p29a:a-reserve",
                "deal_id": "deal:A",
                "currency": "USD",
                "economic_balance": "20",
                "settled_balance": "20",
                "continuity_order": 2,
            }),
            (f"deal-cash-lot:p4-p29b:b:{context}", {
                "lot_id": "lot:p4-p29b:b-cash",
                "lot_family": "deal-cash",
                "amount": "10",
                "deal_id": "deal:B",
                "source_event": "event:p4-p29b:reserve-add",
                "source_allocation_id": "allocation:p4-p29b:b-reserve",
                "currency": "USD",
                "economic_balance": "10",
                "settled_balance": "10",
                "continuity_order": 3,
            }),
            (f"opening-reserve-lot:p4-p29c:a:{context}", {
                "lot_id": "lot:p4-p29a:a-reserve",
                "lot_family": "opening-reserve",
                "original": "20",
                "remaining": "15",
                "source_cash_lot_id": "lot:p4-p29a:a-cash",
                "source_event_id": "event:p4-p29a:realization",
                "source_allocation_id": "allocation:p4-p29a:a-reserve",
                "deal_id": "deal:A",
                "currency": "USD",
                "economic_balance": "15",
                "settled_balance": "15",
                "continuity_order": 4,
            }),
            (f"opening-reserve-lot:p4-p29c:b:{context}", {
                "lot_id": "lot:p4-p29b:b-reserve",
                "lot_family": "opening-reserve",
                "original": "10",
                "remaining": "10",
                "source_cash_lot_id": "lot:p4-p29b:b-cash",
                "source_event_id": "event:p4-p29b:reserve-add",
                "source_allocation_id": "allocation:p4-p29b:b-reserve",
                "deal_id": "deal:B",
                "currency": "USD",
                "economic_balance": "10",
                "settled_balance": "10",
                "continuity_order": 5,
            }),
        ),
    }
    for candidate_set, cutoff_name in (
        (predecessor_projection_set, predecessor_cutoff_name),
        (projection_set, current_cutoff_name),
    ):
        _validate_p29_continuity(candidate_set, context, cutoff_name)
        continuity_rows = tuple(
            candidate
            for candidate in candidate_set.rows
            if candidate.projection_kind in {"deal_cash_lot", "opening_reserve_lot"}
            and ":p4-p29" in candidate.record_key
            and candidate.record_key.endswith(f":{context}")
        )
        rows_by_key = {candidate.record_key: candidate for candidate in continuity_rows}
        expected_continuity = continuity_contracts[cutoff_name]
        if len(rows_by_key) != len(continuity_rows) or tuple(
            (record_key, rows_by_key[record_key].payload.get("value"))
            for record_key, _ in expected_continuity
            if record_key in rows_by_key
        ) != expected_continuity:
            refuse("predecessor-scaffold-invalid")
    return PredecessorRequestScaffoldRecord(
        projection_id=row.projection_id,
        expected_predecessor_scenario_id=expected_scenario,
        predecessor_bundle_request=request,
        predecessor_request_digest=cast(str, value["predecessor_request_digest"]),
        lineage=row.lineage,
        projection_receipt_id=row.projection_receipt_id,
    )


def validate_p4_positive_bundle_request(request: SnapshotBundleRequest) -> P4AccessContext:
    from .fixtures.terms import (
        P4_TERMS_CUTOFFS,
        _p4_positive_dataset_ids,
        _p4_slice_request,
    )

    scenario_sources = tuple(
        source
        for source in request.sources
        if source.dataset_id in P4_POSITIVE_ENTITY_BY_SCENARIO_DATASET
    )
    if len(scenario_sources) != 1:
        refuse("p4-term-bundle-request-invalid")
    scenario_dataset_id = scenario_sources[0].dataset_id
    contexts = tuple(
        context
        for context, row in P4_SCENARIO_DATASETS.items()
        if row[0] == scenario_dataset_id
    )
    if len(contexts) != 1:
        refuse("p4-term-bundle-request-invalid")
    access_context = cast(P4AccessContext, contexts[0])
    cutoff_names = tuple(
        name
        for name, cutoff in P4_TERMS_CUTOFFS.items()
        if normalize_utc(cutoff) == normalize_utc(request.decision_at)
    )
    if len(cutoff_names) != 1:
        refuse("p4-term-bundle-request-invalid")
    expected_ids = _p4_positive_dataset_ids(
        cutoff_name=cutoff_names[0], access_context=access_context
    )
    entity_id = P4_POSITIVE_ENTITY_BY_SCENARIO_DATASET[scenario_dataset_id]
    expected_sources = tuple(
        _p4_slice_request(
            dataset_id,
            canonical_entity_ids=(entity_id,),
            include_unresolved=False,
        )
        for dataset_id in expected_ids
    )
    if (
        request.sources != expected_sources
        or request.join_keys != ("canonical_entity_id",)
        or request.join_policy != "exact-inner-v1"
    ):
        refuse("p4-term-bundle-request-invalid")
    return access_context
