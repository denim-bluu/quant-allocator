from datetime import UTC, datetime

import pytest

from quant_allocator.evidence.checks import EvidenceRefusal
from quant_allocator.evidence.fixtures import build_core_fixture
from quant_allocator.evidence.fixtures.core import (
    core_observation_id,
    core_record_id,
    core_right_id,
    core_version_id,
)
from quant_allocator.evidence.model import DatasetSliceRequest, machine_id, sha256
from quant_allocator.evidence.schema import connect, initialize
from quant_allocator.evidence.universe import require_member


def test_membership_end_boundary_is_excluded() -> None:
    conn = connect()
    initialize(conn)
    build_core_fixture(conn)
    item_id = core_record_id(conn, source_key="A")
    span_id = machine_id(
        "span",
        {
            "evidence_item_id": item_id,
            "json_pointer": "/label",
            "start_char": 0,
            "end_char": 1,
            "span_sha256": sha256(b"A"),
        },
    )
    mapping_id = machine_id(
        "mapping",
        {
            "source_evidence_item_id": item_id,
            "source_key": "A",
            "source_label": "A",
            "taxonomy_version": "v1",
            "version": 1,
            "candidate_entity_ids_json": "[]",
        },
    )
    membership_id = machine_id(
        "membership",
        {
            "source_evidence_item_id": item_id,
            "entity_mapping_id": mapping_id,
            "dataset_version_id": core_version_id(conn, "v1"),
            "membership_status": "active",
            "taxonomy_version": "v1",
            "temporal_type": "interval",
            "effective_at": None,
            "effective_from": "2024-01-01T00:00:00.000000Z",
            "effective_to": "2024-02-01T00:00:00.000000Z",
            "version": 1,
        },
    )
    conn.execute(
        "INSERT INTO evidence_span VALUES (?,?,?,?,?,?)",
        (span_id, item_id, "/label", 0, 1, sha256(b"A")),
    )
    conn.execute(
        "INSERT INTO entity_mapping VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            mapping_id,
            item_id,
            span_id,
            core_version_id(conn, "v1"),
            core_observation_id(conn, "v1", "A"),
            "A",
            "A",
            "product",
            "manager:aster-quay",
            "resolved",
            "[]",
            "exact",
            "v1",
            "interval",
            None,
            "2024-01-01T00:00:00.000000Z",
            "2024-02-01T00:00:00.000000Z",
            1,
            None,
        ),
    )
    conn.execute(
        "INSERT INTO universe_membership VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            membership_id,
            item_id,
            span_id,
            core_version_id(conn, "v1"),
            core_observation_id(conn, "v1", "A"),
            mapping_id,
            "active",
            "v1",
            "interval",
            None,
            "2024-01-01T00:00:00.000000Z",
            "2024-02-01T00:00:00.000000Z",
            1,
            None,
        ),
    )
    request = DatasetSliceRequest(
        "dataset:public-markets", "shortlisted-nda", core_right_id("public-markets"), "research"
    )
    with pytest.raises(EvidenceRefusal, match="universe-member-not-known"):
        require_member(
            conn,
            universe_membership_id=membership_id,
            slice_request=request,
            decision_at=datetime(2024, 4, 1, tzinfo=UTC),
            valid_at=datetime(2024, 2, 1, tzinfo=UTC),
        )
