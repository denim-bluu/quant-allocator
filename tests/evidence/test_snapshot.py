from datetime import UTC, date, datetime

from quant_allocator.evidence.fixtures import build_core_fixture
from quant_allocator.evidence.fixtures.core import core_right_id
from quant_allocator.evidence.ingest import ingest_datasets, ingest_rights
from quant_allocator.evidence.ingest import (
    expected_partition_manifest,
    ingest_dataset_delivery_partitions,
    ingest_dataset_observation_partition_links,
    ingest_dataset_observations,
    ingest_dataset_versions,
    ingest_items,
    ingest_source_records,
    ingest_spans,
    received_partition_manifest,
    reconstruction_manifest,
)
from quant_allocator.evidence.model import (
    DatasetRecord,
    DatasetDeliveryPartitionRecord,
    DatasetObservationPartitionLinkRecord,
    DatasetObservationRecord,
    DatasetSliceRequest,
    DatasetVersionRecord,
    EvidenceItemRecord,
    EvidenceRightRecord,
    EvidenceSpanRecord,
    SnapshotBundleRequest,
    SourceRecordRecord,
    canonical_bytes,
    sha256,
    with_machine_id,
)
from quant_allocator.evidence.schema import connect, initialize
from quant_allocator.evidence.snapshot import (
    as_known_bundle,
    as_known_slice,
    bundle_bytes,
    export_snapshot,
    snapshot_bytes,
)


def _request() -> DatasetSliceRequest:
    return DatasetSliceRequest(
        "dataset:public-markets", "shortlisted-nda", core_right_id("public-markets"), "research"
    )


def test_snapshots_exclude_future_vintages_and_latest_revision_is_selected_first() -> None:
    conn = connect()
    initialize(conn)
    build_core_fixture(conn)
    early = as_known_slice(conn, decision_at=datetime(2024, 2, 1, tzinfo=UTC), request=_request())
    late = as_known_slice(conn, decision_at=datetime(2024, 4, 1, tzinfo=UTC), request=_request())
    assert sorted((r["payload"]["label"], r["payload"]["value"]) for r in early.rows) == [
        ("A", 1),
        ("B", 1),
        ("D", 1),
    ]
    assert sorted((r["payload"]["label"], r["payload"]["value"]) for r in late.rows) == [
        ("A", 1),
        ("B", 2),
        ("C", 1),
    ]
    assert early.digest != late.digest
    assert snapshot_bytes(early) == snapshot_bytes(early)


def test_bundle_is_deterministic_and_commits_to_join_policy() -> None:
    conn = connect()
    initialize(conn)
    build_core_fixture(conn)
    request = SnapshotBundleRequest(
        datetime(2024, 4, 1, tzinfo=UTC), (_request(),), ("canonical_entity_id",), "exact-canonical"
    )
    first = as_known_bundle(conn, request)
    second = as_known_bundle(conn, request)
    assert first == second
    assert bundle_bytes(first) == bundle_bytes(second)


def test_bundle_and_export_are_invariant_to_source_and_receipt_order(tmp_path) -> None:
    conn = connect()
    initialize(conn)
    build_core_fixture(conn)
    now = datetime(2024, 1, 10, tzinfo=UTC)
    ingest_datasets(
        conn,
        [
            DatasetRecord(
                "dataset:empty", "Empty", "public", "manager-receipt", "v1", "nda", "research"
            )
        ],
    )
    ingest_rights(
        conn,
        [
            with_machine_id(
                "right",
                EvidenceRightRecord(
                    "",
                    "right-series:empty",
                    1,
                    "dataset:empty",
                    "shortlisted-nda",
                    "research",
                    "active",
                    "retain-after-expiry",
                    now,
                    now,
                    None,
                ),
            )
        ],
    )
    empty_right = conn.execute(
        "SELECT evidence_right_id FROM evidence_right WHERE dataset_id='dataset:empty'"
    ).fetchone()[0]
    empty = DatasetSliceRequest("dataset:empty", "shortlisted-nda", empty_right, "research")
    first_request = SnapshotBundleRequest(
        datetime(2024, 4, 1, tzinfo=UTC),
        (_request(), empty),
        ("canonical_entity_id",),
        "exact-canonical",
    )
    second_request = SnapshotBundleRequest(
        datetime(2024, 4, 1, tzinfo=UTC),
        (empty, _request()),
        ("canonical_entity_id",),
        "exact-canonical",
    )
    first = as_known_bundle(conn, first_request)
    second = as_known_bundle(conn, second_request)
    assert first.bundle_digest == second.bundle_digest
    receipts = (
        {"receipt_id": "receipt:z", "value": 2},
        {"receipt_id": "receipt:a", "value": 1},
    )
    first_paths = export_snapshot(first, receipts, tmp_path / "a")
    second_paths = export_snapshot(second, reversed(receipts), tmp_path / "b")
    assert [path.read_bytes() for path in first_paths] == [
        path.read_bytes() for path in second_paths
    ]


def test_renewed_right_retains_lawfully_acquired_predecessor_evidence() -> None:
    conn = connect()
    initialize(conn)
    build_core_fixture(conn)
    jan = datetime(2024, 1, 1, tzinfo=UTC)
    feb = datetime(2024, 2, 1, tzinfo=UTC)
    mar = datetime(2024, 3, 1, tzinfo=UTC)
    ingest_datasets(
        conn,
        [
            DatasetRecord(
                "dataset:renew", "Renew", "manager", "manager-receipt", "v1", "nda", "research"
            )
        ],
    )
    renew_v1 = with_machine_id(
        "right",
        EvidenceRightRecord(
            "",
            "right-series:renew",
            1,
            "dataset:renew",
            "shortlisted-nda",
            "research",
            "active",
            "retain-after-expiry",
            jan,
            jan,
            feb,
        ),
    )
    renew_v2 = with_machine_id(
        "right",
        EvidenceRightRecord(
            "",
            "right-series:renew",
            2,
            "dataset:renew",
            "shortlisted-nda",
            "research",
            "active",
            "retain-after-expiry",
            mar,
            mar,
            None,
            renew_v1.evidence_right_id,
        ),
    )
    ingest_rights(conn, [renew_v1, renew_v2])
    fact_source = with_machine_id(
        "source-record", SourceRecordRecord("", "dataset:renew", "manager", "A", "product")
    )
    manifest_source = with_machine_id(
        "source-record", SourceRecordRecord("", "dataset:renew", "manager", "MANIFEST", "document")
    )
    ingest_source_records(conn, [fact_source, manifest_source])
    fact = {"label": "A", "value": 1}
    manifest_payload = {"label": "all", "value": 1}
    fact_item = with_machine_id(
        "evidence",
        EvidenceItemRecord(
            "",
            renew_v1.evidence_right_id,
            fact_source.source_record_id,
            sha256(canonical_bytes(fact)),
            "generic-record",
            "schema:generic-v1",
            "point",
            jan,
            None,
            None,
            date(2024, 1, 1),
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
            fact,
        ),
    )
    manifest_item = with_machine_id(
        "evidence",
        EvidenceItemRecord(
            "",
            renew_v1.evidence_right_id,
            manifest_source.source_record_id,
            sha256(canonical_bytes(manifest_payload)),
            "generic-record",
            "schema:generic-v1",
            "point",
            jan,
            None,
            None,
            date(2024, 1, 1),
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
    )
    ingest_items(conn, [fact_item, manifest_item])
    manifest_span = with_machine_id(
        "span",
        EvidenceSpanRecord("", manifest_item.evidence_item_id, "/label", 0, 3, sha256(b"all")),
    )
    ingest_spans(conn, [manifest_span])
    rows = [
        {
            "source_record_id": fact_source.source_record_id,
            "evidence_item_id": fact_item.evidence_item_id,
            "observation_status": "present",
        }
    ]
    partition_rows = [
        {
            "partition_key": "all",
            "partition_status": "expected-received",
            "expected_record_count": 1,
            "received_record_count": 1,
            "received_content_sha256": sha256(b"renew-v1"),
        }
    ]
    version = with_machine_id(
        "dataset-version",
        DatasetVersionRecord(
            "",
            "dataset:renew",
            "v1",
            renew_v1.evidence_right_id,
            None,
            None,
            jan,
            None,
            sha256(b"renew-v1"),
            "full-snapshot",
            "not-inferable",
            "complete",
            expected_partition_manifest(partition_rows),
            received_partition_manifest(partition_rows),
            1,
            1,
            reconstruction_manifest(rows),
            1,
        ),
    )
    ingest_dataset_versions(conn, [version])
    observation = with_machine_id(
        "dataset-observation",
        DatasetObservationRecord(
            "", version.dataset_version_id, fact_item.evidence_item_id, "present"
        ),
    )
    ingest_dataset_observations(conn, [observation])
    partition = with_machine_id(
        "dataset-partition",
        DatasetDeliveryPartitionRecord(
            "",
            version.dataset_version_id,
            "all",
            "expected-received",
            manifest_item.evidence_item_id,
            manifest_span.evidence_span_id,
            sha256(b"renew-v1"),
            1,
            1,
        ),
    )
    ingest_dataset_delivery_partitions(conn, [partition])
    ingest_dataset_observation_partition_links(
        conn,
        [
            with_machine_id(
                "dataset-observation-partition",
                DatasetObservationPartitionLinkRecord(
                    "",
                    observation.dataset_observation_id,
                    partition.dataset_delivery_partition_id,
                ),
            )
        ],
    )
    request = DatasetSliceRequest(
        "dataset:renew", "shortlisted-nda", renew_v2.evidence_right_id, "research"
    )
    retained = as_known_slice(conn, decision_at=datetime(2024, 4, 1, tzinfo=UTC), request=request)
    assert [row["payload"]["value"] for row in retained.rows] == [1]
