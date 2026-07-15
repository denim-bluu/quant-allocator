from datetime import UTC, datetime

import sqlite3
import pytest

from quant_allocator.evidence.checks import EvidenceRefusal
from quant_allocator.evidence.fixtures import build_core_fixture
from quant_allocator.evidence.fixtures.core import core_right_id, core_source_id, core_version_id
from quant_allocator.evidence.fixtures.public_markets import build_public_markets_fixture
from quant_allocator.evidence.lineage import make_receipt, store_receipt, verify_receipt
from quant_allocator.evidence.model import (
    DatasetSliceRequest,
    ReceiptReference,
    SnapshotBundleRequest,
)
from quant_allocator.evidence.schema import connect, initialize
from quant_allocator.evidence.snapshot import as_known_bundle


def test_receipt_is_deterministic_and_typed_references_are_order_independent() -> None:
    conn = connect()
    initialize(conn)
    build_core_fixture(conn)
    refs = (
        ReceiptReference(
            "/value",
            "dataset-version",
            core_version_id(conn, "v1"),
            "included",
            "",
            "schema:generic-v1",
            "/value",
            "input",
        ),
        ReceiptReference(
            "/value",
            "source-record",
            core_source_id(conn, "A"),
            "excluded",
            "out-of-window",
            "schema:generic-v1",
            "/value",
            "filter",
        ),
    )
    first = make_receipt(
        claim_id="claim:test",
        output_locator="/value",
        input_digest="a" * 64,
        output_schema_id="schema:generic-v1",
        current_attestation="D",
        live_attestation_ceiling="B",
        algorithm_id="identity",
        algorithm_version="1",
        parameters={},
        value={"value": 1},
        references=refs,
    )
    second = make_receipt(
        claim_id="claim:test",
        output_locator="/value",
        input_digest="a" * 64,
        output_schema_id="schema:generic-v1",
        current_attestation="D",
        live_attestation_ceiling="B",
        algorithm_id="identity",
        algorithm_version="1",
        parameters={},
        value={"value": 1},
        references=tuple(reversed(refs)),
    )
    assert first == second
    assert store_receipt(conn, first) == first.receipt_id
    assert store_receipt(conn, first) == first.receipt_id


def test_valid_disappearance_receipt_verifies_against_full_denominator() -> None:
    conn = connect()
    initialize(conn)
    build_core_fixture(conn)
    source = DatasetSliceRequest(
        "dataset:public-markets", "shortlisted-nda", core_right_id("public-markets"), "research"
    )
    bundle = as_known_bundle(
        conn,
        SnapshotBundleRequest(
            datetime(2024, 4, 1, tzinfo=UTC),
            (source,),
            ("canonical_entity_id",),
            "exact-canonical",
        ),
    )
    verify_receipt(conn, bundle.slices[0].receipt_id, bundle)
    stored = conn.execute(
        "SELECT * FROM receipt_reference WHERE receipt_id=? ORDER BY ordinal LIMIT 1",
        (bundle.slices[0].receipt_id,),
    ).fetchone()
    columns = tuple(stored.keys())
    values = [stored[column] for column in columns]
    values[columns.index("ordinal")] = 999
    with pytest.raises(sqlite3.IntegrityError, match="receipt-sealed"):
        conn.execute(
            f"INSERT INTO receipt_reference({','.join(columns)}) VALUES ({','.join('?' for _ in columns)})",
            values,
        )
    reference_columns = {
        "evidence-right": "evidence_right_id",
        "dataset-version": "dataset_version_id",
        "dataset-delivery-partition": "dataset_delivery_partition_id",
        "dataset-observation": "dataset_observation_id",
        "evidence-item": "evidence_item_id",
        "source-record": "source_record_id",
        "dataset-observation-partition-link": "dataset_observation_partition_link_id",
    }
    original = conn.execute(
        "SELECT * FROM receipt_reference WHERE receipt_id=? ORDER BY ordinal",
        (bundle.slices[0].receipt_id,),
    ).fetchall()
    bad_refs = tuple(
        ReceiptReference(
            row["output_field"],
            row["reference_type"],
            row[reference_columns[row["reference_type"]]],
            row["disposition"],
            row["reason_code"],
            row["source_schema_id"],
            "/label/does-not-exist",
            row["role"],
        )
        for row in original
    )
    invalid = make_receipt(
        claim_id="claim:snapshot-slice",
        output_locator="/rows",
        input_digest=bundle.slices[0].digest,
        output_schema_id="schema:generic-v1",
        current_attestation="D",
        live_attestation_ceiling="B",
        algorithm_id="as-known-slice",
        algorithm_version="1",
        parameters={},
        value=bundle.slices[0].rows,
        references=bad_refs,
    )
    store_receipt(conn, invalid)
    with pytest.raises(EvidenceRefusal, match="invalid-json-pointer"):
        verify_receipt(conn, invalid.receipt_id, bundle)


def test_delta_receipt_verifies_base_inherited_change_new_and_tombstone_lineage() -> None:
    conn = connect()
    initialize(conn)
    build_public_markets_fixture(conn)
    source = DatasetSliceRequest(
        "dataset:public-markets", "shortlisted-nda", core_right_id("public-markets"), "research"
    )
    bundle = as_known_bundle(
        conn,
        SnapshotBundleRequest(
            datetime(2024, 5, 20, tzinfo=UTC),
            (source,),
            ("canonical_entity_id",),
            "exact-canonical",
        ),
    )
    verify_receipt(conn, bundle.slices[0].receipt_id, bundle)
    refs = conn.execute(
        "SELECT reference_type,disposition FROM receipt_reference WHERE receipt_id=?",
        (bundle.slices[0].receipt_id,),
    ).fetchall()
    assert ("dataset-observation-partition-link", "excluded") in map(tuple, refs)
    assert ("dataset-observation-partition-link", "included") in map(tuple, refs)
