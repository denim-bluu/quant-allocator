from datetime import UTC, date, datetime

import pytest

from quant_allocator.evidence.checks import EvidenceRefusal
from quant_allocator.evidence.ingest import (
    ingest_dataset_observations,
    ingest_dataset_versions,
    ingest_datasets,
    ingest_entities,
    ingest_items,
    ingest_payload_schemas,
    ingest_rights,
    ingest_source_records,
    reconstruct_dataset_version,
    reconstruction_manifest,
)
from quant_allocator.evidence.model import (
    DatasetObservationRecord,
    DatasetRecord,
    DatasetVersionRecord,
    EntityRecord,
    EvidenceItemRecord,
    EvidenceRightRecord,
    PayloadSchemaRecord,
    SourceRecordRecord,
    canonical_bytes,
    sha256,
    with_machine_id,
)
from quant_allocator.evidence.schema import connect, initialize

T = datetime(2024, 1, 2, tzinfo=UTC)
TEST_RIGHT = with_machine_id(
    "right",
    EvidenceRightRecord(
        "",
        "right-series:r",
        1,
        "dataset:returns",
        "shortlisted-nda",
        "research",
        "active",
        "retain-after-expiry",
        T,
        T,
        None,
    ),
)


def _base(conn):
    ingest_entities(conn, [EntityRecord("manager:aster", "manager", "Aster")])
    ingest_datasets(
        conn,
        [
            DatasetRecord(
                "dataset:returns", "Returns", "manager", "manager-receipt", "v1", "nda", "research"
            )
        ],
    )
    ingest_rights(
        conn,
        [TEST_RIGHT],
    )
    schema = {"type": "object"}
    ingest_payload_schemas(
        conn,
        [
            PayloadSchemaRecord(
                "schema:generic-v1", "generic-record", schema, sha256(canonical_bytes(schema))
            )
        ],
    )


def _version(
    version_id: str,
    label: str,
    manifest: str,
    *,
    predecessor=None,
    base=None,
    mode="full-snapshot",
    complete="complete",
):
    return with_machine_id(
        "dataset-version",
        DatasetVersionRecord(
            "",
            "dataset:returns",
            label,
            TEST_RIGHT.evidence_right_id,
            None,
            None,
            T,
            None,
            "a" * 64,
            mode,
            "explicit-tombstone-only",
            complete,
            "b" * 64,
            "b" * 64,
            1,
            1,
            manifest if complete == "complete" else None,
            1 if complete == "complete" else None,
            predecessor,
            base,
        ),
    )


def _item(item_id: str, source_id: str, payload: dict, version=1, revision=None):
    return with_machine_id(
        "evidence",
        EvidenceItemRecord(
            "",
            TEST_RIGHT.evidence_right_id,
            source_id,
            sha256(canonical_bytes(payload)),
            "generic-record",
            "schema:generic-v1",
            "point",
            T,
            None,
            None,
            date(2024, 1, 2),
            None,
            None,
            T,
            None,
            version,
            revision,
            "received",
            "shortlisted-nda",
            "v1",
            "nda",
            "research",
            payload,
            canonical_entity_id="manager:aster",
        ),
    )


def test_ingest_is_idempotent_and_keeps_content_separate_from_vintages() -> None:
    conn = connect()
    initialize(conn)
    _base(conn)
    source = with_machine_id(
        "source-record", SourceRecordRecord("", "dataset:returns", "manager", "A", "manager")
    )
    ingest_source_records(conn, [source])
    item = _item("", source.source_record_id, {"value": 1})
    ingest_items(conn, [item])
    ingest_items(conn, [item])
    row = {
        "source_record_id": source.source_record_id,
        "evidence_item_id": item.evidence_item_id,
        "observation_status": "present",
    }
    manifest = reconstruction_manifest([row])
    v1 = _version("", "v1", manifest)
    v2 = _version("", "v2", manifest, predecessor=v1.dataset_version_id)
    ingest_dataset_versions(conn, [v2, v1])
    ingest_dataset_observations(
        conn,
        [
            with_machine_id(
                "dataset-observation",
                DatasetObservationRecord(
                    "", v1.dataset_version_id, item.evidence_item_id, "present"
                ),
            ),
            with_machine_id(
                "dataset-observation",
                DatasetObservationRecord(
                    "", v2.dataset_version_id, item.evidence_item_id, "present"
                ),
            ),
        ],
    )
    assert conn.execute("SELECT count(*) FROM evidence_item").fetchone()[0] == 1
    assert conn.execute("SELECT count(*) FROM dataset_observation").fetchone()[0] == 2
    assert reconstruct_dataset_version(conn, v2.dataset_version_id).rows == (row,)


def test_revision_gap_and_incomplete_version_refuse() -> None:
    conn = connect()
    initialize(conn)
    _base(conn)
    source = with_machine_id(
        "source-record", SourceRecordRecord("", "dataset:returns", "manager", "A", "manager")
    )
    ingest_source_records(conn, [source])
    first = _item("", source.source_record_id, {"value": 1})
    ingest_items(conn, [first])
    with pytest.raises(EvidenceRefusal, match="revision-gap"):
        ingest_items(
            conn,
            [
                _item(
                    "",
                    source.source_record_id,
                    {"value": 3},
                    version=3,
                    revision=first.evidence_item_id,
                )
            ],
        )
    incomplete = _version("", "bad", "", complete="incomplete")
    ingest_dataset_versions(conn, [incomplete])
    with pytest.raises(EvidenceRefusal, match="incomplete-dataset-version"):
        reconstruct_dataset_version(conn, incomplete.dataset_version_id)
