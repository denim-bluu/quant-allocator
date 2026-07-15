from __future__ import annotations

import sqlite3
from dataclasses import fields
from typing import Any, Iterable, Mapping

from .checks import refuse
from .model import (
    DatasetDeliveryPartitionRecord,
    DatasetObservationRecord,
    DatasetObservationPartitionLinkRecord,
    DatasetRecord,
    DatasetVersionRecord,
    EntityRecord,
    EvidenceItemRecord,
    EvidenceRightRecord,
    EvidenceSpanRecord,
    PayloadSchemaRecord,
    ReconstructedDatasetVersion,
    SourceRecordRecord,
    canonical_bytes,
    require_machine_id,
    normalize_utc,
    sha256,
    validate_identifier,
)


def _value(value: Any) -> Any:
    from datetime import date, datetime

    if isinstance(value, datetime):
        return normalize_utc(value)
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, (dict, list, tuple)):
        return canonical_bytes(value).decode()
    return value


def _insert(conn: sqlite3.Connection, table: str, pk: str, row: Mapping[str, Any]) -> str:
    key = str(row[pk])
    validate_identifier(key)
    existing = conn.execute(f"SELECT * FROM {table} WHERE {pk}=?", (key,)).fetchone()
    cooked = {k: _value(v) for k, v in row.items()}
    if existing is not None:
        for name, value in cooked.items():
            if existing[name] != value:
                refuse("immutable-record", table=table, identifier=key)
        return key
    names = tuple(cooked)
    conn.execute(
        f"INSERT INTO {table}({','.join(names)}) VALUES ({','.join('?' for _ in names)})",
        tuple(cooked[name] for name in names),
    )
    return key


def ingest_entities(conn: sqlite3.Connection, rows: Iterable[EntityRecord]) -> tuple[str, ...]:
    out = []
    for row in sorted(rows, key=lambda x: x.entity_id):
        out.append(
            _insert(
                conn,
                "canonical_entity",
                "entity_id",
                {
                    "entity_id": row.entity_id,
                    "entity_type": row.entity_type,
                    "canonical_name": row.canonical_name,
                    "parent_entity_id": row.parent_entity_id,
                },
            )
        )
    return tuple(out)


def ingest_datasets(conn: sqlite3.Connection, rows: Iterable[DatasetRecord]) -> tuple[str, ...]:
    return tuple(
        _insert(conn, "dataset", "dataset_id", _record(row))
        for row in sorted(rows, key=lambda x: x.dataset_id)
    )


def ingest_payload_schemas(
    conn: sqlite3.Connection, rows: Iterable[PayloadSchemaRecord]
) -> tuple[str, ...]:
    out = []
    for row in sorted(rows, key=lambda x: x.payload_schema_id):
        if sha256(canonical_bytes(row.schema)) != row.schema_sha256:
            refuse("content-hash-mismatch", identifier=row.payload_schema_id)
        out.append(
            _insert(
                conn,
                "payload_schema",
                "payload_schema_id",
                {
                    "payload_schema_id": row.payload_schema_id,
                    "record_kind": row.record_kind,
                    "schema_json": row.schema,
                    "schema_sha256": row.schema_sha256,
                },
            )
        )
    return tuple(out)


def ingest_rights(conn: sqlite3.Connection, rows: Iterable[EvidenceRightRecord]) -> tuple[str, ...]:
    out = []
    for row in sorted(rows, key=lambda x: (x.right_series_id, x.right_version)):
        require_machine_id("right", row.evidence_right_id, row)
        previous = conn.execute(
            "SELECT * FROM evidence_right WHERE right_series_id=? ORDER BY right_version DESC LIMIT 1",
            (row.right_series_id,),
        ).fetchone()
        if row.right_version == 1 and row.supersedes_right_id is not None:
            refuse("revision-cross-record")
        if row.right_version > 1 and (
            previous is None
            or previous["right_version"] != row.right_version - 1
            or row.supersedes_right_id != previous["evidence_right_id"]
        ):
            refuse("revision-gap")
        out.append(_insert(conn, "evidence_right", "evidence_right_id", _record(row)))
    return tuple(out)


def ingest_source_records(
    conn: sqlite3.Connection, rows: Iterable[SourceRecordRecord]
) -> tuple[str, ...]:
    out = []
    for row in sorted(rows, key=lambda x: x.source_record_id):
        require_machine_id("source-record", row.source_record_id, row)
        out.append(_insert(conn, "source_record", "source_record_id", _record(row)))
    return tuple(out)


def ingest_items(conn: sqlite3.Connection, rows: Iterable[EvidenceItemRecord]) -> tuple[str, ...]:
    out = []
    for row in sorted(rows, key=lambda x: (x.source_record_id, x.version)):
        require_machine_id("evidence", row.evidence_item_id, row)
        if sha256(canonical_bytes(row.payload)) != row.content_sha256:
            refuse("content-hash-mismatch", identifier=row.evidence_item_id)
        data = _item_record(row)
        if conn.execute(
            "SELECT 1 FROM evidence_item WHERE evidence_item_id=?", (row.evidence_item_id,)
        ).fetchone():
            out.append(_insert(conn, "evidence_item", "evidence_item_id", data))
            continue
        previous = conn.execute(
            "SELECT evidence_item_id,version,content_sha256 FROM evidence_item WHERE source_record_id=? ORDER BY version DESC LIMIT 1",
            (row.source_record_id,),
        ).fetchone()
        if row.version == 1 and row.revision_of is not None:
            refuse("revision-cross-record")
        if row.version > 1:
            if (
                previous is None
                or previous["version"] != row.version - 1
                or row.revision_of != previous["evidence_item_id"]
            ):
                refuse("revision-gap")
            if previous["content_sha256"] == row.content_sha256:
                refuse("revision-noop")
        policy = conn.execute(
            "SELECT d.availability_policy FROM source_record s JOIN dataset d USING(dataset_id) WHERE s.source_record_id=?",
            (row.source_record_id,),
        ).fetchone()
        if policy is None:
            refuse("missing-source-identity")
        scope = conn.execute(
            """SELECT s.dataset_id,r.dataset_id AS right_dataset,
                      r.access_context,r.licence_purpose
               FROM source_record s JOIN evidence_right r ON r.evidence_right_id=?
               WHERE s.source_record_id=?""",
            (row.acquisition_right_id, row.source_record_id),
        ).fetchone()
        if scope is None or scope["dataset_id"] != scope["right_dataset"]:
            refuse("missing-evidence-right")
        if scope["access_context"] != row.access_context:
            refuse("access-context-mismatch")
        if scope["licence_purpose"] != row.licence_purpose:
            refuse("licence-purpose-mismatch")
        if (
            policy[0] in {"manager-receipt", "internal-receipt", "licensed-receipt"}
            and row.received_at_utc is None
        ):
            refuse("missing-receipt-time")
        if (
            policy[0] == "public-publication"
            and row.published_at is None
            and row.first_observed_at_utc is None
        ):
            refuse("missing-publication-time")
        out.append(_insert(conn, "evidence_item", "evidence_item_id", data))
    return tuple(out)


def ingest_spans(conn: sqlite3.Connection, rows: Iterable[EvidenceSpanRecord]) -> tuple[str, ...]:
    out = []
    for row in sorted(rows, key=lambda x: x.evidence_span_id):
        require_machine_id("span", row.evidence_span_id, row)
        out.append(_insert(conn, "evidence_span", "evidence_span_id", _record(row)))
    return tuple(out)


def ingest_dataset_versions(
    conn: sqlite3.Connection, rows: Iterable[DatasetVersionRecord]
) -> tuple[str, ...]:
    out = []
    pending = sorted(
        rows, key=lambda item: (item.dataset_id, item.version_label, item.dataset_version_id)
    )
    while pending:
        progress = False
        for row in list(pending):
            require_machine_id("dataset-version", row.dataset_version_id, row)
            if conn.execute(
                "SELECT 1 FROM dataset_version WHERE dataset_version_id=?",
                (row.dataset_version_id,),
            ).fetchone():
                out.append(_insert(conn, "dataset_version", "dataset_version_id", _record(row)))
                pending.remove(row)
                progress = True
                continue
            if (
                row.predecessor_dataset_version_id
                and conn.execute(
                    "SELECT 1 FROM dataset_version WHERE dataset_version_id=?",
                    (row.predecessor_dataset_version_id,),
                ).fetchone()
                is None
            ):
                continue
            if row.delivery_mode == "delta":
                base = conn.execute(
                    "SELECT delivery_mode,completeness_status,dataset_id FROM dataset_version WHERE dataset_version_id=?",
                    (row.base_dataset_version_id,),
                ).fetchone()
                if base is None:
                    continue
                if base[0] != "full-snapshot" or base[1] != "complete" or base[2] != row.dataset_id:
                    refuse("delta-base-missing")
            _validate_version_predecessor(conn, row)
            out.append(_insert(conn, "dataset_version", "dataset_version_id", _record(row)))
            pending.remove(row)
            progress = True
        if not progress:
            refuse("delta-predecessor-invalid")
    return tuple(out)


def _validate_version_predecessor(conn: sqlite3.Connection, row: DatasetVersionRecord) -> None:
    prior = conn.execute(
        """SELECT parent.dataset_version_id FROM dataset_version parent
           WHERE parent.dataset_id=? AND NOT EXISTS (
             SELECT 1 FROM dataset_version child
             WHERE child.predecessor_dataset_version_id=parent.dataset_version_id
           ) ORDER BY parent.dataset_version_id""",
        (row.dataset_id,),
    ).fetchall()
    if not prior and row.predecessor_dataset_version_id is not None:
        refuse("delta-predecessor-invalid")
    if len(prior) > 1 or (prior and row.predecessor_dataset_version_id != prior[0][0]):
        refuse("delta-predecessor-invalid")
    right = conn.execute(
        "SELECT dataset_id,licence_purpose FROM evidence_right WHERE evidence_right_id=?",
        (row.acquisition_right_id,),
    ).fetchone()
    dataset = conn.execute(
        "SELECT licence_purpose FROM dataset WHERE dataset_id=?", (row.dataset_id,)
    ).fetchone()
    if right is None or dataset is None or right["dataset_id"] != row.dataset_id:
        refuse("missing-evidence-right")
    if right["licence_purpose"] != dataset["licence_purpose"]:
        refuse("licence-purpose-mismatch")


def ingest_dataset_delivery_partitions(
    conn: sqlite3.Connection, rows: Iterable[DatasetDeliveryPartitionRecord]
) -> tuple[str, ...]:
    out = []
    for row in sorted(rows, key=lambda x: x.dataset_delivery_partition_id):
        require_machine_id("dataset-partition", row.dataset_delivery_partition_id, row)
        out.append(
            _insert(
                conn, "dataset_delivery_partition", "dataset_delivery_partition_id", _record(row)
            )
        )
    return tuple(out)


def ingest_dataset_observations(
    conn: sqlite3.Connection, rows: Iterable[DatasetObservationRecord]
) -> tuple[str, ...]:
    out = []
    for row in sorted(rows, key=lambda x: x.dataset_observation_id):
        require_machine_id("dataset-observation", row.dataset_observation_id, row)
        out.append(_insert(conn, "dataset_observation", "dataset_observation_id", _record(row)))
    return tuple(out)


def ingest_dataset_observation_partition_links(
    conn: sqlite3.Connection, rows: Iterable[DatasetObservationPartitionLinkRecord]
) -> tuple[str, ...]:
    out = []
    for row in sorted(rows, key=lambda item: item.dataset_observation_partition_link_id):
        require_machine_id(
            "dataset-observation-partition", row.dataset_observation_partition_link_id, row
        )
        out.append(
            _insert(
                conn,
                "dataset_observation_partition_link",
                "dataset_observation_partition_link_id",
                _record(row),
            )
        )
    return tuple(out)


def reconstruction_manifest(rows: Iterable[Mapping[str, Any]]) -> str:
    ordered = sorted(
        (dict(row) for row in rows),
        key=lambda x: (x["source_record_id"], x["evidence_item_id"], x["observation_status"]),
    )
    return sha256(canonical_bytes(ordered))


def expected_partition_manifest(rows: Iterable[Mapping[str, Any]]) -> str:
    values = sorted(
        (
            {
                "partition_key": row["partition_key"],
                "expected_record_count": row["expected_record_count"],
            }
            for row in rows
        ),
        key=lambda row: row["partition_key"],
    )
    return sha256(canonical_bytes(values))


def received_partition_manifest(rows: Iterable[Mapping[str, Any]]) -> str:
    values = sorted(
        (
            {
                "partition_key": row["partition_key"],
                "received_record_count": row["received_record_count"],
                "received_content_sha256": row["received_content_sha256"],
            }
            for row in rows
            if row["received_record_count"] > 0 or row["partition_status"] == "expected-received"
        ),
        key=lambda row: row["partition_key"],
    )
    return sha256(canonical_bytes(values))


def reconstruct_dataset_version(
    conn: sqlite3.Connection, dataset_version_id: str
) -> ReconstructedDatasetVersion:
    version = conn.execute(
        "SELECT * FROM dataset_version WHERE dataset_version_id=?", (dataset_version_id,)
    ).fetchone()
    if version is None:
        refuse("unknown-dataset-version")
    if version["completeness_status"] != "complete":
        refuse("incomplete-dataset-version")
    chain = _version_chain(conn, version)
    materialized: dict[str, dict[str, Any]] = {}
    for version_id in chain:
        observations = conn.execute(
            """SELECT s.source_record_id,o.evidence_item_id,o.observation_status
               FROM dataset_observation o JOIN evidence_item i USING(evidence_item_id)
               JOIN source_record s USING(source_record_id)
               WHERE o.dataset_version_id=? ORDER BY s.source_record_id,o.evidence_item_id""",
            (version_id,),
        )
        for row in observations:
            if row["observation_status"] == "explicitly-removed":
                materialized.pop(row["source_record_id"], None)
            else:
                materialized[row["source_record_id"]] = dict(row)
    rows = tuple(materialized[key] for key in sorted(materialized))
    digest = reconstruction_manifest(rows)
    if (
        digest != version["reconstruction_manifest_sha256"]
        or len(rows) != version["reconstruction_row_count"]
    ):
        refuse("reconstruction-manifest-mismatch")
    base = (
        dataset_version_id
        if version["delivery_mode"] == "full-snapshot"
        else version["base_dataset_version_id"]
    )
    return ReconstructedDatasetVersion(
        dataset_version_id, base, tuple(chain), rows, digest, len(rows)
    )


def _version_chain(conn: sqlite3.Connection, version: sqlite3.Row) -> list[str]:
    if version["delivery_mode"] == "full-snapshot":
        return [version["dataset_version_id"]]
    chain = []
    current = version
    seen = set()
    while True:
        identifier = current["dataset_version_id"]
        if identifier in seen:
            refuse("delta-predecessor-invalid")
        seen.add(identifier)
        chain.append(identifier)
        if identifier == version["base_dataset_version_id"]:
            break
        parent = current["predecessor_dataset_version_id"]
        if parent is None:
            refuse("delta-base-missing")
        current = conn.execute(
            "SELECT * FROM dataset_version WHERE dataset_version_id=?", (parent,)
        ).fetchone()
        if current is None:
            refuse("delta-predecessor-invalid")
    chain.reverse()
    return chain


def _record(row: Any) -> dict[str, Any]:
    return {field.name: getattr(row, field.name) for field in fields(row)}


def _item_record(row: EvidenceItemRecord) -> dict[str, Any]:
    names = {
        "evidence_item_id",
        "source_record_id",
        "acquisition_right_id",
        "content_sha256",
        "record_kind",
        "payload_schema_id",
        "canonical_entity_id",
        "temporal_type",
        "effective_at",
        "effective_from",
        "effective_to",
        "as_of_date",
        "published_at",
        "first_observed_at_utc",
        "received_at_utc",
        "embargo_until",
        "version",
        "revision_of",
        "publication_status",
        "access_context",
        "field_dictionary_version",
        "sensitivity_class",
        "licence_purpose",
    }
    data = {name: getattr(row, name) for name in names}
    data["payload_json"] = row.payload
    return data
