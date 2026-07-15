"""Bind E3's authored corpus and graph facts to the canonical evidence substrate."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Sequence

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
from quant_allocator.evidence.lineage import resolve_span
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
    SnapshotBundle,
    SnapshotBundleRequest,
    SourceRecordRecord,
    canonical_bytes,
    machine_id,
    sha256,
    with_machine_id,
)
from quant_allocator.evidence.schema import connect, initialize, schema_digest
from quant_allocator.evidence.snapshot import as_known_bundle
from quant_allocator.flagships.saydo.corpus import Document

E3_DECISION_AT = datetime(2024, 6, 30, 23, 59, 59, 999999, tzinfo=UTC)
_RECEIVED_AT = datetime(2024, 6, 1, tzinfo=UTC)
_CORRECTION_AT = datetime(2024, 7, 1, tzinfo=UTC)
_RIGHT_AT = datetime(2024, 1, 1, tzinfo=UTC)
_EMPTY_DELIVERY_AT = datetime(2024, 5, 1, tzinfo=UTC)
_DATASET_ID = "dataset:e3-authored-corpus"
_ACCESS_CONTEXT = "shortlisted-synthetic-demo"
_LICENCE_PURPOSE = "research-demo"
_SCHEMA_ID = "schema:e3-authored-record-v1"
_RELATIONSHIP_DOC_ID = "E3-RELATIONSHIPS"


@dataclass(frozen=True)
class E3EvidenceStore:
    conn: sqlite3.Connection
    document_ids: tuple[str, ...]
    evidence_right_id: str
    document_item_ids: dict[str, str]
    document_span_ids: dict[str, str]
    relationship_item_id: str
    relationship_span_ids: tuple[str, ...]
    entity_relationship_ids: dict[tuple[str, str, str], str]
    schema_digest: str


def _month(value: str) -> datetime:
    return datetime.strptime(value, "%Y-%m").replace(tzinfo=UTC)


def _entity_id(kind: str, identifier: str) -> str:
    slug = identifier.lower().replace("_", "-")
    return f"{kind}:{slug}"


def build_e3_evidence(corpus: Sequence[Document]) -> E3EvidenceStore:
    """Ingest the authored E3 inputs once and return their stable evidence handles."""

    # Imported lazily to avoid a module cycle with the generator that owns the authored text.
    from quant_allocator.demo_data.e3_knowledge import (
        RELATIONSHIP_RECORD_AS_OF,
        RELATIONSHIP_RECORD_TEXT,
        _RELATIONSHIP_SENTENCES,
    )

    conn = connect()
    initialize(conn)
    entities = [
        EntityRecord(_entity_id("strategy", "ELS"), "strategy", "Equity long/short"),
        EntityRecord(_entity_id("manager", "CLC"), "manager", "Corvid Lane Capital"),
        EntityRecord(_entity_id("manager", "SPA"), "manager", "Selby Point Advisors"),
        EntityRecord(_entity_id("manager", "WGC"), "manager", "Wexford Green Capital"),
        EntityRecord(_entity_id("person", "EV"), "person", "Elena Voss"),
        EntityRecord(_entity_id("person", "PA"), "person", "Priya Anand"),
    ]
    entities.extend(
        EntityRecord(_entity_id("document", document.doc_id), "document", document.doc_id)
        for document in corpus
    )
    entities.extend(
        [
            EntityRecord(
                _entity_id("document", _RELATIONSHIP_DOC_ID), "document", _RELATIONSHIP_DOC_ID
            ),
            EntityRecord(_entity_id("view", "V-LIQ-LETTER"), "view", "V-LIQ-LETTER"),
            EntityRecord(_entity_id("view", "V-LIQ-MEETING"), "view", "V-LIQ-MEETING"),
            EntityRecord(_entity_id("theme", "LIQ"), "theme", "Liquidity"),
            EntityRecord(_entity_id("meeting", "M-2024-05"), "meeting", "M-2024-05"),
        ]
    )
    ingest_entities(conn, entities)
    ingest_datasets(
        conn,
        [
            DatasetRecord(
                _DATASET_ID,
                "E3 authored corpus",
                "authored-demo",
                "manager-receipt",
                "v1",
                "synthetic",
                _LICENCE_PURPOSE,
            )
        ],
    )
    schema = {
        "type": "object",
        "required": ["doc_id", "doc_type", "manager_code", "author", "text", "as_of", "purpose"],
        "properties": {
            key: {"type": "string"}
            for key in ("doc_id", "doc_type", "manager_code", "author", "text", "as_of", "purpose")
        },
    }
    ingest_payload_schemas(
        conn,
        [
            PayloadSchemaRecord(
                _SCHEMA_ID, "e3-authored-record", schema, sha256(canonical_bytes(schema))
            ),
            PayloadSchemaRecord(
                "schema:generic-v1",
                "generic-record",
                {"type": "object"},
                sha256(canonical_bytes({"type": "object"})),
            ),
        ],
    )
    right = with_machine_id(
        "right",
        EvidenceRightRecord(
            "",
            "right-series:e3-authored-corpus",
            1,
            _DATASET_ID,
            _ACCESS_CONTEXT,
            _LICENCE_PURPOSE,
            "active",
            "retain-after-expiry",
            _RIGHT_AT,
            _RIGHT_AT,
            None,
        ),
    )
    ingest_rights(conn, [right])

    records = [
        (
            document.doc_id,
            document.doc_type,
            document.manager_code,
            document.author,
            document.text,
            document.as_of,
            "retrieval",
            _entity_id("document", document.doc_id),
        )
        for document in corpus
    ]
    records.append(
        (
            _RELATIONSHIP_DOC_ID,
            "relationship_record",
            "",
            "authored-demo",
            RELATIONSHIP_RECORD_TEXT,
            RELATIONSHIP_RECORD_AS_OF,
            "graph-only",
            _entity_id("document", _RELATIONSHIP_DOC_ID),
        )
    )
    sources = [
        with_machine_id(
            "source-record",
            SourceRecordRecord("", _DATASET_ID, "authored-demo", doc_id, "document"),
        )
        for doc_id, *_ in records
    ]
    ingest_source_records(conn, sources)
    source_by_doc = {doc_id: source for (doc_id, *_), source in zip(records, sources, strict=True)}

    items = []
    for doc_id, doc_type, manager_code, author, text, as_of, purpose, entity_id in records:
        payload = {
            "doc_id": doc_id,
            "doc_type": doc_type,
            "manager_code": manager_code,
            "author": author,
            "text": text,
            "as_of": as_of,
            "purpose": purpose,
        }
        items.append(
            with_machine_id(
                "evidence",
                EvidenceItemRecord(
                    "",
                    right.evidence_right_id,
                    source_by_doc[doc_id].source_record_id,
                    sha256(canonical_bytes(payload)),
                    "e3-authored-record",
                    _SCHEMA_ID,
                    "point",
                    _month(as_of),
                    None,
                    None,
                    date.fromisoformat(f"{as_of}-01"),
                    None,
                    None,
                    _RECEIVED_AT,
                    None,
                    1,
                    None,
                    "received",
                    _ACCESS_CONTEXT,
                    "v1",
                    "synthetic",
                    _LICENCE_PURPOSE,
                    payload,
                    canonical_entity_type="document",
                    canonical_entity_id=entity_id,
                ),
            )
        )
    ingest_items(conn, items)
    item_by_doc = {doc_id: item for (doc_id, *_), item in zip(records, items, strict=True)}
    spans = []
    document_span_ids: dict[str, str] = {}
    for doc_id, _, _, _, text, *_ in records:
        span = with_machine_id(
            "span",
            EvidenceSpanRecord(
                "",
                item_by_doc[doc_id].evidence_item_id,
                "/text",
                0,
                len(text),
                sha256(text.encode()),
            ),
        )
        spans.append(span)
        document_span_ids[doc_id] = span.evidence_span_id
    relationship_spans = []
    cursor = 0
    for sentence in _RELATIONSHIP_SENTENCES:
        start = RELATIONSHIP_RECORD_TEXT.index(sentence, cursor)
        end = start + len(sentence)
        cursor = end
        span = with_machine_id(
            "span",
            EvidenceSpanRecord(
                "",
                item_by_doc[_RELATIONSHIP_DOC_ID].evidence_item_id,
                "/text",
                start,
                end,
                sha256(sentence.encode()),
            ),
        )
        relationship_spans.append(span)
        spans.append(span)
    ingest_spans(conn, spans)

    manifest_source = with_machine_id(
        "source-record",
        SourceRecordRecord(
            "", _DATASET_ID, "authored-demo", "E3-EMPTY-MANIFEST", "delivery-manifest"
        ),
    )
    ingest_source_records(conn, [manifest_source])
    manifest_text = "The May delivery manifest contains no authored E3 records."
    manifest_payload = {
        "doc_id": "E3-EMPTY-MANIFEST",
        "doc_type": "relationship_record",
        "manager_code": "",
        "author": "authored-demo",
        "text": manifest_text,
        "as_of": "2024-05",
        "purpose": "graph-only",
    }
    manifest_item = with_machine_id(
        "evidence",
        EvidenceItemRecord(
            "",
            right.evidence_right_id,
            manifest_source.source_record_id,
            sha256(canonical_bytes(manifest_payload)),
            "e3-authored-record",
            _SCHEMA_ID,
            "point",
            _EMPTY_DELIVERY_AT,
            None,
            None,
            date(2024, 5, 1),
            None,
            None,
            _EMPTY_DELIVERY_AT,
            None,
            1,
            None,
            "received",
            _ACCESS_CONTEXT,
            "v1",
            "synthetic",
            _LICENCE_PURPOSE,
            manifest_payload,
        ),
    )
    ingest_items(conn, [manifest_item])
    manifest_span = with_machine_id(
        "span",
        EvidenceSpanRecord(
            "",
            manifest_item.evidence_item_id,
            "/text",
            0,
            len(manifest_text),
            sha256(manifest_text.encode()),
        ),
    )
    ingest_spans(conn, [manifest_span])
    empty_partition_seed = [
        {
            "partition_key": "may-empty",
            "partition_status": "expected-received",
            "expected_record_count": 0,
            "received_record_count": 0,
            "received_content_sha256": sha256(b"e3-empty-delivery"),
        }
    ]
    initial_version = with_machine_id(
        "dataset-version",
        DatasetVersionRecord(
            "",
            _DATASET_ID,
            "2024-05-empty",
            right.evidence_right_id,
            None,
            None,
            _EMPTY_DELIVERY_AT,
            None,
            sha256(b"e3-empty-delivery"),
            "full-snapshot",
            "not-inferable",
            "complete",
            expected_partition_manifest(empty_partition_seed),
            received_partition_manifest(empty_partition_seed),
            1,
            1,
            reconstruction_manifest(()),
            0,
        ),
    )
    ingest_dataset_versions(conn, [initial_version])
    initial_partition = with_machine_id(
        "dataset-partition",
        DatasetDeliveryPartitionRecord(
            "",
            initial_version.dataset_version_id,
            "may-empty",
            "expected-received",
            manifest_item.evidence_item_id,
            manifest_span.evidence_span_id,
            sha256(b"e3-empty-delivery"),
            0,
            0,
        ),
    )
    ingest_dataset_delivery_partitions(conn, [initial_partition])

    observations_seed = [
        {
            "source_record_id": source_by_doc[doc_id].source_record_id,
            "evidence_item_id": item_by_doc[doc_id].evidence_item_id,
            "observation_status": "present",
        }
        for doc_id, *_ in records
    ]
    partition_seed = [
        {
            "partition_key": "june",
            "partition_status": "expected-received",
            "expected_record_count": len(records),
            "received_record_count": len(records),
            "received_content_sha256": sha256(canonical_bytes([row[0] for row in records])),
        }
    ]
    version = with_machine_id(
        "dataset-version",
        DatasetVersionRecord(
            "",
            _DATASET_ID,
            "2024-06",
            right.evidence_right_id,
            None,
            None,
            _RECEIVED_AT,
            None,
            sha256(canonical_bytes([item.content_sha256 for item in items])),
            "full-snapshot",
            "not-inferable",
            "complete",
            expected_partition_manifest(partition_seed),
            received_partition_manifest(partition_seed),
            1,
            1,
            reconstruction_manifest(observations_seed),
            len(observations_seed),
            initial_version.dataset_version_id,
        ),
    )
    ingest_dataset_versions(conn, [version])
    observations = [
        with_machine_id(
            "dataset-observation",
            DatasetObservationRecord(
                "", version.dataset_version_id, item_by_doc[doc_id].evidence_item_id, "present"
            ),
        )
        for doc_id, *_ in records
    ]
    ingest_dataset_observations(conn, observations)
    observation_by_doc = {
        doc_id: obs for (doc_id, *_), obs in zip(records, observations, strict=True)
    }
    partition = with_machine_id(
        "dataset-partition",
        DatasetDeliveryPartitionRecord(
            "",
            version.dataset_version_id,
            "june",
            "expected-received",
            item_by_doc[_RELATIONSHIP_DOC_ID].evidence_item_id,
            relationship_spans[0].evidence_span_id,
            partition_seed[0]["received_content_sha256"],
            len(records),
            len(records),
        ),
    )
    ingest_dataset_delivery_partitions(conn, [partition])
    ingest_dataset_observation_partition_links(
        conn,
        [
            with_machine_id(
                "dataset-observation-partition",
                DatasetObservationPartitionLinkRecord(
                    "", obs.dataset_observation_id, partition.dataset_delivery_partition_id
                ),
            )
            for obs in observations
        ],
    )

    correction_text = (
        RELATIONSHIP_RECORD_TEXT
        + " A July clerical correction confirms that the June relationship facts are unchanged."
    )
    correction_payload = {
        "doc_id": _RELATIONSHIP_DOC_ID,
        "doc_type": "relationship_record",
        "manager_code": "",
        "author": "authored-demo",
        "text": correction_text,
        "as_of": "2024-07",
        "purpose": "graph-only",
    }
    correction_item = with_machine_id(
        "evidence",
        EvidenceItemRecord(
            "",
            right.evidence_right_id,
            source_by_doc[_RELATIONSHIP_DOC_ID].source_record_id,
            sha256(canonical_bytes(correction_payload)),
            "e3-authored-record",
            _SCHEMA_ID,
            "point",
            _CORRECTION_AT,
            None,
            None,
            date(2024, 7, 1),
            None,
            None,
            _CORRECTION_AT,
            None,
            2,
            item_by_doc[_RELATIONSHIP_DOC_ID].evidence_item_id,
            "received",
            _ACCESS_CONTEXT,
            "v1",
            "synthetic",
            _LICENCE_PURPOSE,
            correction_payload,
            canonical_entity_type="document",
            canonical_entity_id=_entity_id("document", _RELATIONSHIP_DOC_ID),
        ),
    )
    ingest_items(conn, [correction_item])
    correction_sentence = (
        "A July clerical correction confirms that the June relationship facts are unchanged."
    )
    correction_span = with_machine_id(
        "span",
        EvidenceSpanRecord(
            "",
            correction_item.evidence_item_id,
            "/text",
            len(RELATIONSHIP_RECORD_TEXT) + 1,
            len(correction_text),
            sha256(correction_sentence.encode()),
        ),
    )
    ingest_spans(conn, [correction_span])
    correction_seed = [
        {
            "source_record_id": source_by_doc[_RELATIONSHIP_DOC_ID].source_record_id,
            "evidence_item_id": correction_item.evidence_item_id,
            "observation_status": "present",
        }
    ]
    correction_partition_seed = [
        {
            "partition_key": "july-correction",
            "partition_status": "expected-received",
            "expected_record_count": 1,
            "received_record_count": 1,
            "received_content_sha256": correction_item.content_sha256,
        }
    ]
    corrected_reconstruction_seed = [
        row
        for row in observations_seed
        if row["source_record_id"] != source_by_doc[_RELATIONSHIP_DOC_ID].source_record_id
    ] + correction_seed
    correction_version = with_machine_id(
        "dataset-version",
        DatasetVersionRecord(
            "",
            _DATASET_ID,
            "2024-07-correction",
            right.evidence_right_id,
            None,
            None,
            _CORRECTION_AT,
            None,
            correction_item.content_sha256,
            "delta",
            "explicit-tombstone-only",
            "complete",
            expected_partition_manifest(correction_partition_seed),
            received_partition_manifest(correction_partition_seed),
            1,
            1,
            reconstruction_manifest(corrected_reconstruction_seed),
            len(corrected_reconstruction_seed),
            version.dataset_version_id,
            version.dataset_version_id,
        ),
    )
    ingest_dataset_versions(conn, [correction_version])
    correction_observation = with_machine_id(
        "dataset-observation",
        DatasetObservationRecord(
            "", correction_version.dataset_version_id, correction_item.evidence_item_id, "present"
        ),
    )
    ingest_dataset_observations(conn, [correction_observation])
    correction_partition = with_machine_id(
        "dataset-partition",
        DatasetDeliveryPartitionRecord(
            "",
            correction_version.dataset_version_id,
            "july-correction",
            "expected-received",
            correction_item.evidence_item_id,
            correction_span.evidence_span_id,
            correction_item.content_sha256,
            1,
            1,
        ),
    )
    ingest_dataset_delivery_partitions(conn, [correction_partition])
    ingest_dataset_observation_partition_links(
        conn,
        [
            with_machine_id(
                "dataset-observation-partition",
                DatasetObservationPartitionLinkRecord(
                    "",
                    correction_observation.dataset_observation_id,
                    correction_partition.dataset_delivery_partition_id,
                ),
            )
        ],
    )

    relationship_ids: dict[tuple[str, str, str], str] = {}
    relationship_specs = [
        (
            "authored_by",
            _entity_id("document", "L-2024Q1"),
            _entity_id("person", "EV"),
            9,
            None,
            None,
        ),
        (
            "authored_by",
            _entity_id("document", "MTG-2024-05"),
            _entity_id("person", "EV"),
            10,
            None,
            None,
        ),
        (
            "authored_by",
            _entity_id("document", "L-2023Q4"),
            _entity_id("person", "PA"),
            11,
            None,
            None,
        ),
        (
            "employed_by",
            _entity_id("person", "EV"),
            _entity_id("manager", "CLC"),
            6,
            "2024-01-01T00:00:00.000000Z",
            None,
        ),
        (
            "employed_by",
            _entity_id("person", "EV"),
            _entity_id("manager", "SPA"),
            7,
            "2020-01-01T00:00:00.000000Z",
            "2024-01-01T00:00:00.000000Z",
        ),
        (
            "employed_by",
            _entity_id("person", "PA"),
            _entity_id("manager", "SPA"),
            8,
            "2020-01-01T00:00:00.000000Z",
            None,
        ),
        (
            "attributed_to",
            _entity_id("document", "L-2024Q1"),
            _entity_id("manager", "CLC"),
            12,
            None,
            None,
        ),
        (
            "attributed_to",
            _entity_id("document", "DDQ-2024"),
            _entity_id("manager", "CLC"),
            13,
            None,
            None,
        ),
        (
            "attributed_to",
            _entity_id("document", "L-2023Q4"),
            _entity_id("manager", "SPA"),
            14,
            None,
            None,
        ),
        (
            "attributed_to",
            _entity_id("document", "DDQ-WEX"),
            _entity_id("manager", "WGC"),
            15,
            None,
            None,
        ),
        (
            "expresses",
            _entity_id("document", "L-2024Q1"),
            _entity_id("view", "V-LIQ-LETTER"),
            20,
            None,
            None,
        ),
        (
            "expresses",
            _entity_id("document", "MTG-2024-05"),
            _entity_id("view", "V-LIQ-MEETING"),
            21,
            None,
            None,
        ),
        (
            "about_theme",
            _entity_id("view", "V-LIQ-LETTER"),
            _entity_id("theme", "LIQ"),
            22,
            None,
            None,
        ),
        (
            "about_theme",
            _entity_id("view", "V-LIQ-MEETING"),
            _entity_id("theme", "LIQ"),
            23,
            None,
            None,
        ),
        (
            "discussed_at",
            _entity_id("view", "V-LIQ-MEETING"),
            _entity_id("meeting", "M-2024-05"),
            24,
            None,
            None,
        ),
    ]
    relationship_item = item_by_doc[_RELATIONSHIP_DOC_ID]
    relationship_observation = observation_by_doc[_RELATIONSHIP_DOC_ID]
    for (
        relation_type,
        source_entity,
        target_entity,
        span_index,
        effective_from,
        effective_to,
    ) in relationship_specs:
        effective_at = None if effective_from else "2024-06-01T00:00:00.000000Z"
        identity = {
            "source_evidence_item_id": relationship_item.evidence_item_id,
            "relation_type": relation_type,
            "source_entity_id": source_entity,
            "target_entity_id": target_entity,
            "temporal_type": "interval" if effective_from else "point",
            "effective_at": effective_at,
            "effective_from": effective_from,
            "effective_to": effective_to,
            "version": 1,
        }
        relationship_id = machine_id("entity-relation", identity)
        conn.execute(
            "INSERT INTO entity_relationship VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                relationship_id,
                relationship_item.evidence_item_id,
                relationship_spans[span_index].evidence_span_id,
                version.dataset_version_id,
                relationship_observation.dataset_observation_id,
                relation_type,
                source_entity,
                target_entity,
                identity["temporal_type"],
                effective_at,
                effective_from,
                effective_to,
                1,
                None,
            ),
        )
        relationship_ids[(relation_type, source_entity, target_entity)] = relationship_id
    conn.commit()
    return E3EvidenceStore(
        conn,
        tuple(document.doc_id for document in corpus),
        right.evidence_right_id,
        {
            doc_id: item_by_doc[doc_id].evidence_item_id
            for doc_id in tuple(document.doc_id for document in corpus)
        },
        document_span_ids,
        relationship_item.evidence_item_id,
        tuple(span.evidence_span_id for span in relationship_spans),
        relationship_ids,
        schema_digest(conn),
    )


def e3_snapshot_bundle(
    store: E3EvidenceStore, decision_at: datetime = E3_DECISION_AT
) -> SnapshotBundle:
    request = DatasetSliceRequest(
        _DATASET_ID, _ACCESS_CONTEXT, store.evidence_right_id, _LICENCE_PURPOSE
    )
    bundle_request = SnapshotBundleRequest(
        decision_at, (request,), ("evidence_item_id",), "single-source"
    )
    return as_known_bundle(store.conn, bundle_request)


def documents_as_known_at(store: E3EvidenceStore, bundle: SnapshotBundle) -> tuple[Document, ...]:
    rows = {
        row["payload"]["doc_id"]: row["payload"]
        for row in bundle.slices[0].rows
        if row["payload"].get("purpose") == "retrieval"
    }
    return tuple(
        Document(
            row["doc_id"],
            row["doc_type"],
            row["manager_code"],
            row["author"],
            row["text"],
            row["as_of"],
        )
        for doc_id in store.document_ids
        if (row := rows.get(doc_id)) is not None
    )


def provenance_from_span(conn, evidence_span_id: str) -> dict[str, str]:
    resolved = resolve_span(conn, evidence_span_id)
    row = conn.execute(
        "SELECT payload_json FROM evidence_item WHERE evidence_item_id=?",
        (resolved["evidence_item_id"],),
    ).fetchone()
    payload = json.loads(row["payload_json"])
    return {
        "source_doc": payload["doc_id"],
        "source_span": resolved["text"],
        "as_of": payload["as_of"],
    }
