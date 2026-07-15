import sqlite3

import pytest

from quant_allocator.evidence.fixtures import build_core_fixture
from quant_allocator.evidence.fixtures.core import (
    core_observation_id,
    core_record_id,
    core_version_id,
)
from quant_allocator.evidence.fixtures.public_markets import build_public_markets_fixture
from quant_allocator.evidence.model import machine_id
from quant_allocator.evidence.schema import connect, initialize, schema_digest


def _mapping_id(item, key="A", label="A", version=1):
    return machine_id(
        "mapping",
        {
            "source_evidence_item_id": item,
            "source_key": key,
            "source_label": label,
            "taxonomy_version": "v1",
            "version": version,
            "candidate_entity_ids_json": "[]",
        },
    )


def test_schema_is_idempotent_foreign_keyed_and_immutable() -> None:
    conn = connect()
    initialize(conn)
    first = schema_digest(conn)
    initialize(conn)
    assert schema_digest(conn) == first
    assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1
    conn.execute(
        "INSERT INTO canonical_entity(entity_id, entity_type, canonical_name) VALUES (?,?,?)",
        ("manager:aster", "manager", "Aster"),
    )
    with pytest.raises(sqlite3.IntegrityError, match="immutable-record"):
        conn.execute("UPDATE canonical_entity SET canonical_name='Other'")
    with pytest.raises(sqlite3.IntegrityError, match="immutable-record"):
        conn.execute("DELETE FROM canonical_entity")
    columns = {row[1] for row in conn.execute("PRAGMA table_info(evidence_item)")}
    assert "available_at" not in columns
    assert "known_at" not in columns


def test_schema_rejects_invalid_temporal_shapes() -> None:
    conn = connect()
    initialize(conn)
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            """INSERT INTO canonical_entity(
                   entity_id, entity_type, canonical_name, temporal_type, effective_at,
                   effective_from, effective_to
               ) VALUES (?,?,?,?,?,?,?)""",
            (
                "manager:bad",
                "manager",
                "Bad",
                "interval",
                "2024-01-01T00:00:00.000000Z",
                None,
                None,
            ),
        )


def test_raw_sql_projection_cannot_mix_item_span_observation_and_version() -> None:
    conn = connect()
    initialize(conn)
    build_core_fixture(conn)
    item_id = core_record_id(conn, source_key="A")
    manifest_span = conn.execute(
        "SELECT evidence_span_id FROM evidence_span WHERE evidence_item_id!=?", (item_id,)
    ).fetchone()[0]
    with pytest.raises(sqlite3.IntegrityError, match="projection-provenance-mismatch"):
        conn.execute(
            "INSERT INTO entity_mapping VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                _mapping_id(item_id),
                item_id,
                manifest_span,
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
                "point",
                "2024-01-10T00:00:00.000000Z",
                None,
                None,
                1,
                None,
            ),
        )


def test_raw_sql_projection_tables_reject_wrong_digest_ids() -> None:
    conn = connect()
    initialize(conn)
    build_public_markets_fixture(conn)
    for table, id_column, namespace in (
        ("entity_mapping", "entity_mapping_id", "mapping"),
        ("funnel_opportunity", "funnel_opportunity_id", "funnel-opportunity"),
        ("funnel_event", "funnel_event_id", "funnel-event"),
    ):
        row = dict(conn.execute(f"SELECT * FROM {table} LIMIT 1").fetchone())
        predecessor = row[id_column]
        row[id_column] = f"{namespace}:sha256:{'0' * 64}"
        row["version"] = 2
        row["revision_of"] = predecessor
        columns = tuple(row)
        with pytest.raises(sqlite3.IntegrityError, match="machine-id-mismatch"):
            conn.execute(
                f"INSERT INTO {table}({','.join(columns)}) VALUES ({','.join('?' for _ in columns)})",
                tuple(row[column] for column in columns),
            )


def test_raw_sql_projection_revision_cannot_skip_or_cross_logical_record() -> None:
    conn = connect()
    initialize(conn)
    build_core_fixture(conn)
    item_id = core_record_id(conn, source_key="A")
    span_hash = "559aead08264d5795d3909718cdd05abd49572e84fe55590eef31a88a08fdffd"
    span_id = machine_id(
        "span",
        {
            "evidence_item_id": item_id,
            "json_pointer": "/label",
            "start_char": 0,
            "end_char": 1,
            "span_sha256": span_hash,
        },
    )
    conn.execute(
        "INSERT INTO evidence_span VALUES (?,?,?,?,?,?)",
        (
            span_id,
            item_id,
            "/label",
            0,
            1,
            span_hash,
        ),
    )
    base = (
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
        "point",
        "2024-01-10T00:00:00.000000Z",
        None,
        None,
    )
    conn.execute(
        "INSERT INTO entity_mapping VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (_mapping_id(item_id), *base, 1, None),
    )
    with pytest.raises(sqlite3.IntegrityError, match="revision-gap"):
        conn.execute(
            "INSERT INTO entity_mapping VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (_mapping_id(item_id), *base, 1, None),
        )
    with pytest.raises(sqlite3.IntegrityError, match="revision-gap"):
        conn.execute(
            "INSERT INTO entity_mapping VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                _mapping_id(item_id, version=3),
                *base,
                3,
                _mapping_id(item_id),
            ),
        )
    crossed = list(base)
    crossed[4] = "B"
    with pytest.raises(sqlite3.IntegrityError, match="revision-gap"):
        conn.execute(
            "INSERT INTO entity_mapping VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                _mapping_id(item_id, key="B", label="B", version=2),
                *crossed,
                2,
                _mapping_id(item_id),
            ),
        )


def test_raw_sql_rejects_uncontrolled_status_values() -> None:
    conn = connect()
    initialize(conn)
    build_core_fixture(conn)
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            """INSERT INTO evidence_right(
                 evidence_right_id,right_series_id,right_version,dataset_id,access_context,
                 licence_purpose,status,retention_policy,received_at_utc,entitlement_from
               ) VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (
                machine_id(
                    "right",
                    {
                        "right_series_id": "right-series:invalid",
                        "right_version": 1,
                        "dataset_id": "dataset:public-markets",
                        "access_context": "shortlisted-nda",
                        "licence_purpose": "research",
                        "status": "invented",
                        "retention_policy": "retain-after-expiry",
                        "received_at_utc": "2024-01-01T00:00:00.000000Z",
                        "entitlement_from": "2024-01-01T00:00:00.000000Z",
                        "entitlement_to": None,
                        "supersedes_right_id": None,
                    },
                ),
                "right-series:invalid",
                1,
                "dataset:public-markets",
                "shortlisted-nda",
                "research",
                "invented",
                "retain-after-expiry",
                "2024-01-01T00:00:00.000000Z",
                "2024-01-01T00:00:00.000000Z",
            ),
        )
