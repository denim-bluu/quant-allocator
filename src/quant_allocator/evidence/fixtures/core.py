from __future__ import annotations

from datetime import UTC, date, datetime

from ..ingest import (
    ingest_dataset_delivery_partitions,
    ingest_dataset_observations,
    ingest_dataset_observation_partition_links,
    ingest_dataset_versions,
    ingest_datasets,
    ingest_entities,
    ingest_items,
    ingest_payload_schemas,
    ingest_rights,
    ingest_source_records,
    ingest_spans,
    expected_partition_manifest,
    received_partition_manifest,
    reconstruction_manifest,
)
from ..model import (
    DatasetObservationRecord,
    DatasetObservationPartitionLinkRecord,
    DatasetRecord,
    DatasetDeliveryPartitionRecord,
    DatasetVersionRecord,
    EntityRecord,
    EvidenceItemRecord,
    EvidenceRightRecord,
    EvidenceSpanRecord,
    PayloadSchemaRecord,
    SourceRecordRecord,
    canonical_bytes,
    machine_id,
    sha256,
    with_machine_id,
)


def core_right_id(slug: str) -> str:
    jan = datetime(2024, 1, 10, tzinfo=UTC)
    return machine_id(
        "right",
        {
            "right_series_id": f"right-series:{slug}",
            "right_version": 1,
            "dataset_id": f"dataset:{slug}",
            "access_context": "shortlisted-nda",
            "licence_purpose": "research",
            "status": "active",
            "retention_policy": "retain-after-expiry",
            "received_at_utc": jan,
            "entitlement_from": jan,
            "entitlement_to": None,
            "supersedes_right_id": None,
        },
    )


def core_record_id(conn, *, source_key: str, version: int = 1) -> str:
    return conn.execute(
        """SELECT i.evidence_item_id FROM evidence_item i
           JOIN source_record s USING(source_record_id)
           WHERE s.dataset_id='dataset:public-markets' AND s.source_record_key=? AND i.version=?""",
        (source_key, version),
    ).fetchone()[0]


def core_source_id(conn, source_key: str) -> str:
    return conn.execute(
        "SELECT source_record_id FROM source_record WHERE dataset_id='dataset:public-markets' AND source_record_key=?",
        (source_key,),
    ).fetchone()[0]


def core_version_id(conn, label: str) -> str:
    return conn.execute(
        "SELECT dataset_version_id FROM dataset_version WHERE dataset_id='dataset:public-markets' AND version_label=?",
        (label,),
    ).fetchone()[0]


def core_observation_id(conn, label: str, source_key: str) -> str:
    return conn.execute(
        """SELECT o.dataset_observation_id FROM dataset_observation o
           JOIN dataset_version v USING(dataset_version_id)
           JOIN evidence_item i USING(evidence_item_id)
           JOIN source_record s USING(source_record_id)
           WHERE v.dataset_id='dataset:public-markets' AND v.version_label=? AND s.source_record_key=?""",
        (label, source_key),
    ).fetchone()[0]


def build_core_fixture(conn) -> None:
    jan = datetime(2024, 1, 10, tzinfo=UTC)
    mar = datetime(2024, 3, 10, tzinfo=UTC)
    ingest_entities(
        conn,
        [
            EntityRecord("manager:aster-quay", "manager", "Aster Quay"),
            EntityRecord("adviser:northglass", "adviser", "Northglass Advisory"),
            EntityRecord("legal-entity:aster-one", "legal-entity", "Aster One Vehicle"),
            EntityRecord("legal-entity:aster-two", "legal-entity", "Aster Two Vehicle"),
        ],
    )
    ingest_datasets(
        conn,
        [
            DatasetRecord(
                f"dataset:{slug}", label, "manager", "manager-receipt", "v1", "nda", "research"
            )
            for slug, label in (
                ("public-markets", "Public markets"),
                ("credit", "Credit"),
                ("private-markets", "Private markets"),
                ("terms", "Governing terms"),
            )
        ],
    )
    rights = [
        with_machine_id(
            "right",
            EvidenceRightRecord(
                "",
                f"right-series:{slug}",
                1,
                f"dataset:{slug}",
                "shortlisted-nda",
                "research",
                "active",
                "retain-after-expiry",
                jan,
                jan,
                None,
            ),
        )
        for slug in ("public-markets", "credit", "private-markets", "terms")
    ]
    ingest_rights(conn, rights)
    right_ids = {right.dataset_id: right.evidence_right_id for right in rights}
    schema = {"type": "object", "required": ["label", "value"]}
    ingest_payload_schemas(
        conn,
        [
            PayloadSchemaRecord(
                "schema:generic-v1", "generic-record", schema, sha256(canonical_bytes(schema))
            )
        ],
    )
    records = [
        with_machine_id(
            "source-record",
            SourceRecordRecord("", "dataset:public-markets", "manager", key, "product"),
        )
        for key in "ABCD"
    ]
    records.append(
        with_machine_id(
            "source-record",
            SourceRecordRecord("", "dataset:public-markets", "manager", "MANIFEST", "document"),
        )
    )
    ingest_source_records(conn, records)
    source_ids = {record.source_record_key: record.source_record_id for record in records}

    def item(key: str, version: int, value: int, received: datetime, revision: str | None = None):
        payload = {"label": key, "value": value}
        return with_machine_id(
            "evidence",
            EvidenceItemRecord(
                "",
                right_ids["dataset:public-markets"],
                source_ids[key],
                sha256(canonical_bytes(payload)),
                "generic-record",
                "schema:generic-v1",
                "point",
                received,
                None,
                None,
                date(2024, 1, 10),
                None,
                None,
                received,
                None,
                version,
                revision,
                "received",
                "shortlisted-nda",
                "v1",
                "nda",
                "research",
                payload,
                canonical_entity_id="manager:aster-quay",
            ),
        )

    manifest_payload = {"label": "all", "value": 1}
    items = [
        item("A", 1, 1, jan),
        item("B", 1, 1, jan),
        item("D", 1, 1, jan),
        item(
            "B",
            2,
            2,
            mar,
            machine_id("evidence", {"source_record_id": source_ids["B"], "version": 1}),
        ),
        item("C", 1, 1, mar),
        with_machine_id(
            "evidence",
            EvidenceItemRecord(
                "",
                right_ids["dataset:public-markets"],
                source_ids["MANIFEST"],
                sha256(canonical_bytes(manifest_payload)),
                "generic-record",
                "schema:generic-v1",
                "point",
                jan,
                None,
                None,
                date(2024, 1, 10),
                None,
                None,
                jan,
                None,
                1,
                None,
                "received",
                "shortlisted-nda",
                "v1",
                "nda",
                "research",
                manifest_payload,
            ),
        ),
    ]
    ingest_items(conn, items)
    item_ids = {(item.source_record_id, item.version): item.evidence_item_id for item in items}
    manifest_item_id = item_ids[(source_ids["MANIFEST"], 1)]
    manifest_span = with_machine_id(
        "span",
        EvidenceSpanRecord("", manifest_item_id, "/label", 0, 3, sha256(b"all")),
    )
    ingest_spans(
        conn,
        [manifest_span],
    )
    v1_rows = [_row(source_ids[key], item_ids[(source_ids[key], 1)]) for key in "ABD"]
    v2_rows = [
        _row(source_ids["A"], item_ids[(source_ids["A"], 1)]),
        _row(source_ids["B"], item_ids[(source_ids["B"], 2)]),
        _row(source_ids["C"], item_ids[(source_ids["C"], 1)]),
    ]
    partition_specs = {
        version: [
            {
                "partition_key": "all",
                "partition_status": "expected-received",
                "expected_record_count": 3,
                "received_record_count": 3,
                "received_content_sha256": sha256(f"public-v{version}".encode()),
            }
        ]
        for version in (1, 2)
    }
    versions = [
        with_machine_id(
            "dataset-version",
            DatasetVersionRecord(
                "",
                "dataset:public-markets",
                "v1",
                right_ids["dataset:public-markets"],
                None,
                None,
                jan,
                None,
                "1" * 64,
                "full-snapshot",
                "full-snapshot-means-removed",
                "complete",
                expected_partition_manifest(partition_specs[1]),
                received_partition_manifest(partition_specs[1]),
                1,
                1,
                reconstruction_manifest(v1_rows),
                3,
            ),
        ),
    ]
    versions.append(
        with_machine_id(
            "dataset-version",
            DatasetVersionRecord(
                "",
                "dataset:public-markets",
                "v2",
                right_ids["dataset:public-markets"],
                None,
                None,
                mar,
                None,
                "3" * 64,
                "full-snapshot",
                "full-snapshot-means-removed",
                "complete",
                expected_partition_manifest(partition_specs[2]),
                received_partition_manifest(partition_specs[2]),
                1,
                1,
                reconstruction_manifest(v2_rows),
                3,
                versions[0].dataset_version_id,
            ),
        )
    )
    ingest_dataset_versions(conn, versions)
    observations = []
    for dataset_version, keys in ((versions[0], "ABD"), (versions[1], "ABC")):
        for key in keys:
            item_version = 2 if dataset_version is versions[1] and key == "B" else 1
            observations.append(
                with_machine_id(
                    "dataset-observation",
                    DatasetObservationRecord(
                        "",
                        dataset_version.dataset_version_id,
                        item_ids[(source_ids[key], item_version)],
                        "present",
                    ),
                )
            )
    observations.append(
        with_machine_id(
            "dataset-observation",
            DatasetObservationRecord(
                "",
                versions[1].dataset_version_id,
                item_ids[(source_ids["D"], 1)],
                "explicitly-removed",
                "absent-from-complete-full-snapshot",
            ),
        )
    )
    ingest_dataset_observations(conn, observations)
    partitions = [
        with_machine_id(
            "dataset-partition",
            DatasetDeliveryPartitionRecord(
                "",
                versions[version - 1].dataset_version_id,
                "all",
                "expected-received",
                manifest_item_id,
                manifest_span.evidence_span_id,
                sha256(f"public-v{version}".encode()),
                3,
                3,
            ),
        )
        for version in (1, 2)
    ]
    ingest_dataset_delivery_partitions(conn, partitions)
    partition_by_version = {
        row.dataset_version_id: row.dataset_delivery_partition_id for row in partitions
    }
    ingest_dataset_observation_partition_links(
        conn,
        [
            with_machine_id(
                "dataset-observation-partition",
                DatasetObservationPartitionLinkRecord(
                    "",
                    observation.dataset_observation_id,
                    partition_by_version[observation.dataset_version_id],
                ),
            )
            for observation in observations
        ],
    )


def _row(source_record_id: str, evidence_item_id: str) -> dict[str, str]:
    return {
        "source_record_id": source_record_id,
        "evidence_item_id": evidence_item_id,
        "observation_status": "present",
    }


def add_fact_dataset(conn, *, slug: str, facts: tuple[dict[str, object], ...]) -> None:
    received = datetime(2024, 4, 15, tzinfo=UTC)
    dataset_id = f"dataset:{slug}"
    right_id = conn.execute(
        "SELECT evidence_right_id FROM evidence_right WHERE dataset_id=?", (dataset_id,)
    ).fetchone()[0]
    manifest_source_record = with_machine_id(
        "source-record", SourceRecordRecord("", dataset_id, "manager", "MANIFEST", "document")
    )
    manifest_source = manifest_source_record.source_record_id
    sources = [manifest_source_record]
    sources.extend(
        with_machine_id(
            "source-record",
            SourceRecordRecord(
                "",
                dataset_id,
                "manager",
                str(fact["label"]),
                str(fact["record_kind"]),
            ),
        )
        for index, fact in enumerate(facts, 1)
    )
    ingest_source_records(conn, sources)
    fact_sources = sources[1:]
    manifest_payload = {"label": "all", "value": len(facts)}
    items = [
        with_machine_id(
            "evidence",
            EvidenceItemRecord(
                "",
                right_id,
                manifest_source,
                sha256(canonical_bytes(manifest_payload)),
                "generic-record",
                "schema:generic-v1",
                "point",
                received,
                None,
                None,
                received.date(),
                None,
                None,
                received,
                None,
                1,
                None,
                "received",
                "shortlisted-nda",
                "v1",
                "nda",
                "research",
                manifest_payload,
            ),
        )
    ]
    for index, fact in enumerate(facts, 1):
        payload = dict(fact)
        items.append(
            with_machine_id(
                "evidence",
                EvidenceItemRecord(
                    "",
                    right_id,
                    fact_sources[index - 1].source_record_id,
                    sha256(canonical_bytes(payload)),
                    str(fact["record_kind"]),
                    "schema:generic-v1",
                    "point",
                    received,
                    None,
                    None,
                    received.date(),
                    None,
                    None,
                    received,
                    None,
                    1,
                    None,
                    "received",
                    "shortlisted-nda",
                    "v1",
                    "nda",
                    "research",
                    payload,
                ),
            )
        )
    ingest_items(conn, items)
    fact_items = items[1:]
    span = with_machine_id(
        "span", EvidenceSpanRecord("", items[0].evidence_item_id, "/label", 0, 3, sha256(b"all"))
    )
    span_id = span.evidence_span_id
    ingest_spans(
        conn,
        [span],
    )
    rows = [
        {
            "source_record_id": fact_sources[index - 1].source_record_id,
            "evidence_item_id": fact_items[index - 1].evidence_item_id,
            "observation_status": "present",
        }
        for index in range(1, len(facts) + 1)
    ]
    content_hash = sha256(f"{slug}-v1".encode())
    partitions = [
        {
            "partition_key": "all",
            "partition_status": "expected-received",
            "expected_record_count": len(facts),
            "received_record_count": len(facts),
            "received_content_sha256": content_hash,
        }
    ]
    version = with_machine_id(
        "dataset-version",
        DatasetVersionRecord(
            "",
            dataset_id,
            "v1",
            right_id,
            None,
            None,
            received,
            None,
            content_hash,
            "full-snapshot",
            "not-inferable",
            "complete",
            expected_partition_manifest(partitions),
            received_partition_manifest(partitions),
            1,
            1,
            reconstruction_manifest(rows),
            len(rows),
        ),
    )
    ingest_dataset_versions(conn, [version])
    ingest_dataset_observations(
        conn,
        [
            with_machine_id(
                "dataset-observation",
                DatasetObservationRecord(
                    "",
                    version.dataset_version_id,
                    fact_items[index - 1].evidence_item_id,
                    "present",
                ),
            )
            for index in range(1, len(facts) + 1)
        ],
    )
    partition = with_machine_id(
        "dataset-partition",
        DatasetDeliveryPartitionRecord(
            "",
            version.dataset_version_id,
            "all",
            "expected-received",
            items[0].evidence_item_id,
            span_id,
            content_hash,
            len(facts),
            len(facts),
        ),
    )
    ingest_dataset_delivery_partitions(conn, [partition])
    observations = conn.execute(
        "SELECT dataset_observation_id FROM dataset_observation WHERE dataset_version_id=? ORDER BY dataset_observation_id",
        (version.dataset_version_id,),
    ).fetchall()
    ingest_dataset_observation_partition_links(
        conn,
        [
            with_machine_id(
                "dataset-observation-partition",
                DatasetObservationPartitionLinkRecord(
                    "",
                    row[0],
                    partition.dataset_delivery_partition_id,
                ),
            )
            for row in observations
        ],
    )
