import pytest
import sqlite3

from quant_allocator.evidence.checks import EvidenceRefusal, audit_receipt, require_foreign_keys
from quant_allocator.evidence.fixtures import build_core_fixture
from quant_allocator.evidence.fixtures.core import core_source_id
from quant_allocator.evidence.lineage import make_receipt, store_receipt
from quant_allocator.evidence.model import ReceiptReference
from quant_allocator.evidence.schema import connect, initialize


def test_connection_and_receipt_completeness_are_explicit() -> None:
    conn = connect()
    initialize(conn)
    build_core_fixture(conn)
    receipt = make_receipt(
        claim_id="claim:test",
        output_locator="/value",
        input_digest="a" * 64,
        output_schema_id="schema:generic-v1",
        current_attestation="D",
        live_attestation_ceiling="B",
        algorithm_id="identity",
        algorithm_version="1",
        parameters={},
        value=1,
        references=(
            ReceiptReference(
                "/value",
                "source-record",
                core_source_id(conn, "A"),
                "excluded",
                "out-of-window",
                "schema:generic-v1",
                "/",
                "filter",
            ),
        ),
    )
    store_receipt(conn, receipt)
    require_foreign_keys(conn)
    assert audit_receipt(conn, receipt.receipt_id) == {"included": 0, "excluded": 1, "refused": 0}
    conn.execute("PRAGMA foreign_keys=OFF")
    with pytest.raises(EvidenceRefusal, match="foreign-keys-disabled"):
        require_foreign_keys(conn)


def test_receipt_store_rolls_back_header_references_and_seal_on_failure() -> None:
    conn = connect()
    initialize(conn)
    build_core_fixture(conn)
    invalid = make_receipt(
        claim_id="claim:test",
        output_locator="/value",
        input_digest="a" * 64,
        output_schema_id="schema:generic-v1",
        current_attestation="D",
        live_attestation_ceiling="B",
        algorithm_id="identity",
        algorithm_version="1",
        parameters={},
        value=1,
        references=(
            ReceiptReference(
                "/value",
                "source-record",
                core_source_id(conn, "A"),
                "included",
                "",
                "schema:generic-v1",
                "/",
                "invented-role",
            ),
        ),
    )
    with pytest.raises(sqlite3.IntegrityError):
        store_receipt(conn, invalid)
    assert (
        conn.execute(
            "SELECT count(*) FROM reconstruction_receipt WHERE receipt_id=?", (invalid.receipt_id,)
        ).fetchone()[0]
        == 0
    )
    assert (
        conn.execute(
            "SELECT count(*) FROM receipt_reference WHERE receipt_id=?", (invalid.receipt_id,)
        ).fetchone()[0]
        == 0
    )
    assert (
        conn.execute(
            "SELECT count(*) FROM receipt_seal WHERE receipt_id=?", (invalid.receipt_id,)
        ).fetchone()[0]
        == 0
    )
