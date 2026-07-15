from dataclasses import replace
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
from quant_allocator.evidence.model import (
    DatasetSliceRequest,
    ReceiptReference,
    canonical_bytes,
    machine_id,
    sha256,
)
from quant_allocator.evidence.projections import evaluate_funnel_cohort, project_entity_mappings
from quant_allocator.evidence.schema import connect, initialize
from quant_allocator.evidence.snapshot import as_known_slice


def _context(conn):
    item = core_record_id(conn, source_key="A")
    span = machine_id(
        "span",
        {
            "evidence_item_id": item,
            "json_pointer": "/label",
            "start_char": 0,
            "end_char": 1,
            "span_sha256": sha256(b"A"),
        },
    )
    conn.execute(
        "INSERT INTO evidence_span VALUES (?,?,?,?,?,?)", (span, item, "/label", 0, 1, sha256(b"A"))
    )
    return item, span, core_version_id(conn, "v1"), core_observation_id(conn, "v1", "A")


def _mapping_id(item, *, version=1):
    return machine_id(
        "mapping",
        {
            "source_evidence_item_id": item,
            "source_key": "A",
            "source_label": "A",
            "taxonomy_version": "v1",
            "version": version,
            "candidate_entity_ids_json": "[]",
        },
    )


def test_same_event_ledger_supports_two_cohort_window_definitions() -> None:
    conn = connect()
    initialize(conn)
    build_core_fixture(conn)
    common = _context(conn)
    opportunity_id = machine_id(
        "funnel-opportunity",
        {
            "source_evidence_item_id": common[0],
            "evidence_span_id": common[1],
            "entity_mapping_id": None,
            "source_opportunity_key": "opportunity-a1",
            "product_entity_id": "manager:aster-quay",
            "entity_grain": "product",
            "temporal_type": "point",
            "effective_at": "2024-01-10T00:00:00.000000Z",
            "effective_from": None,
            "effective_to": None,
            "version": 1,
        },
    )
    schema_id = machine_id(
        "funnel-schema",
        {
            "source_evidence_item_id": common[0],
            "stage_dictionary_json": '["accepted"]',
            "transition_rules_json": "[]",
            "reason_dictionary_json": "[]",
            "completeness_status": "complete",
            "version": 1,
        },
    )
    event_id = machine_id(
        "funnel-event",
        {
            "funnel_opportunity_id": opportunity_id,
            "funnel_schema_id": schema_id,
            "source_evidence_item_id": common[0],
            "entity_mapping_id": None,
            "funnel_stage": "accepted",
            "reason_code": "accepted",
            "effective_at": "2024-01-10T00:00:00.000000Z",
            "version": 1,
        },
    )

    def cohort_id(label, end):
        return machine_id(
            "funnel-cohort",
            {
                "source_evidence_item_id": common[0],
                "funnel_schema_id": schema_id,
                "cohort_label": label,
                "inclusion_rule_json": "{}",
                "exclusion_rule_json": "{}",
                "entity_grain": "product",
                "entry_stage": "accepted",
                "outcome_stage": "accepted",
                "accepted_only": 1,
                "entry_window_from": "2024-01-01T00:00:00.000000Z",
                "entry_window_to": end,
                "observation_window_end": end,
                "completeness_status": "complete",
                "absence_rule": "no-outcome-observed",
                "censor_policy": "right-censor",
                "right_censor_at": end,
                "version": 1,
            },
        )

    conn.execute(
        "INSERT INTO funnel_opportunity VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            opportunity_id,
            *common,
            None,
            "opportunity-a1",
            "A1",
            "product",
            "manager:aster-quay",
            "point",
            "2024-01-10T00:00:00.000000Z",
            None,
            None,
            1,
            None,
        ),
    )
    conn.execute(
        "INSERT INTO funnel_schema VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (
            schema_id,
            *common,
            '["accepted"]',
            "[]",
            "[]",
            "complete",
            1,
            None,
        ),
    )
    conn.execute(
        "INSERT INTO funnel_event VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            event_id,
            *common,
            None,
            None,
            opportunity_id,
            schema_id,
            "accepted",
            "accepted",
            "accepted",
            "2024-01-10T00:00:00.000000Z",
            1,
            None,
        ),
    )
    for suffix, end in (
        ("narrow", "2024-02-01T00:00:00.000000Z"),
        ("wide", "2024-04-01T00:00:00.000000Z"),
    ):
        conn.execute(
            "INSERT INTO funnel_cohort VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                cohort_id(suffix, end),
                *common,
                schema_id,
                suffix,
                "{}",
                "{}",
                "product",
                "accepted",
                "accepted",
                1,
                "2024-01-01T00:00:00.000000Z",
                end,
                end,
                "complete",
                "no-outcome-observed",
                "right-censor",
                end,
                1,
                None,
            ),
        )
    request = DatasetSliceRequest(
        "dataset:public-markets", "shortlisted-nda", core_right_id("public-markets"), "research"
    )
    snapshot = as_known_slice(conn, decision_at=datetime(2024, 2, 1, tzinfo=UTC), request=request)
    narrow = evaluate_funnel_cohort(
        conn, snapshot, funnel_cohort_id=cohort_id("narrow", "2024-02-01T00:00:00.000000Z")
    )
    wide = evaluate_funnel_cohort(
        conn, snapshot, funnel_cohort_id=cohort_id("wide", "2024-04-01T00:00:00.000000Z")
    )
    assert narrow["links"][0]["funnel_event_id"] == wide["links"][0]["funnel_event_id"]
    assert (
        narrow["links"][0]["funnel_cohort_event_link_id"]
        != wide["links"][0]["funnel_cohort_event_link_id"]
    )


def test_future_projection_over_old_item_does_not_leak_into_early_slice() -> None:
    conn = connect()
    initialize(conn)
    build_core_fixture(conn)
    common = _context(conn)
    conn.execute(
        "INSERT INTO entity_mapping VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            _mapping_id(common[0]),
            common[0],
            common[1],
            core_version_id(conn, "v2"),
            core_observation_id(conn, "v2", "A"),
            "A",
            "A",
            "product",
            "manager:aster-quay",
            "resolved",
            "[]",
            "exact",
            "v1",
            "point",
            "2024-03-10T00:00:00.000000Z",
            None,
            None,
            1,
            None,
        ),
    )
    request = DatasetSliceRequest(
        "dataset:public-markets", "shortlisted-nda", core_right_id("public-markets"), "research"
    )
    early = as_known_slice(conn, decision_at=datetime(2024, 2, 1, tzinfo=UTC), request=request)
    assert project_entity_mappings(conn, early) == ()


def test_projection_latest_revision_is_selected_before_valid_time_filter() -> None:
    conn = connect()
    initialize(conn)
    build_core_fixture(conn)
    base = _context(conn)
    common = (
        *base,
        "A",
        "A",
        "product",
        "manager:aster-quay",
        "resolved",
        "[]",
        "exact",
        "v1",
        "point",
    )
    conn.execute(
        "INSERT INTO entity_mapping VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            _mapping_id(base[0]),
            *common,
            "2024-01-10T00:00:00.000000Z",
            None,
            None,
            1,
            None,
        ),
    )
    conn.execute(
        "INSERT INTO entity_mapping VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            _mapping_id(base[0], version=2),
            *common,
            "2024-02-10T00:00:00.000000Z",
            None,
            None,
            2,
            _mapping_id(base[0]),
        ),
    )
    request = DatasetSliceRequest(
        "dataset:public-markets",
        "shortlisted-nda",
        core_right_id("public-markets"),
        "research",
        valid_at=datetime(2024, 1, 10, tzinfo=UTC),
    )
    snapshot = as_known_slice(conn, decision_at=datetime(2024, 2, 20, tzinfo=UTC), request=request)
    assert project_entity_mappings(conn, snapshot) == ()


def test_receipt_authorized_projection_rejects_receipt_from_other_snapshot() -> None:
    conn = connect()
    initialize(conn)
    build_core_fixture(conn)
    item = core_record_id(conn, source_key="C")
    span = machine_id(
        "span",
        {
            "evidence_item_id": item,
            "json_pointer": "/label",
            "start_char": 0,
            "end_char": 1,
            "span_sha256": sha256(b"C"),
        },
    )
    conn.execute(
        "INSERT INTO evidence_span VALUES (?,?,?,?,?,?)",
        (span, item, "/label", 0, 1, sha256(b"C")),
    )
    mapping_id = machine_id(
        "mapping",
        {
            "source_evidence_item_id": item,
            "source_key": "C",
            "source_label": "C",
            "taxonomy_version": "v1",
            "version": 1,
            "candidate_entity_ids_json": "[]",
        },
    )
    conn.execute(
        "INSERT INTO entity_mapping VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            mapping_id,
            item,
            span,
            core_version_id(conn, "v2"),
            core_observation_id(conn, "v2", "C"),
            "C",
            "C",
            "product",
            "manager:aster-quay",
            "resolved",
            "[]",
            "exact",
            "v1",
            "point",
            "2024-03-10T00:00:00.000000Z",
            None,
            None,
            1,
            None,
        ),
    )
    request = DatasetSliceRequest(
        "dataset:public-markets",
        "shortlisted-nda",
        core_right_id("public-markets"),
        "research",
    )
    early = as_known_slice(conn, decision_at=datetime(2024, 2, 1, tzinfo=UTC), request=request)
    latest = as_known_slice(conn, decision_at=datetime(2024, 4, 1, tzinfo=UTC), request=request)
    assert mapping_id in {row["entity_mapping_id"] for row in project_entity_mappings(conn, latest)}

    with pytest.raises(EvidenceRefusal, match="receipt-incomplete"):
        project_entity_mappings(conn, replace(latest, receipt_id=early.receipt_id))


def test_receipt_authorized_projection_rejects_noncanonical_duplicate_reference() -> None:
    conn = connect()
    initialize(conn)
    build_core_fixture(conn)
    common = _context(conn)
    mapping_id = _mapping_id(common[0])
    conn.execute(
        "INSERT INTO entity_mapping VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            mapping_id,
            *common,
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
    request = DatasetSliceRequest(
        "dataset:public-markets",
        "shortlisted-nda",
        core_right_id("public-markets"),
        "research",
    )
    snapshot = as_known_slice(
        conn, decision_at=datetime(2024, 2, 1, tzinfo=UTC), request=request
    )
    assert {row["entity_mapping_id"] for row in project_entity_mappings(conn, snapshot)} == {
        mapping_id
    }

    conn.execute("SAVEPOINT duplicate_receipt_reference")
    try:
        conn.execute("DROP TRIGGER reject_sealed_receipt_reference")
        conn.execute("DROP TRIGGER immutable_update_receipt_seal")
        stored = conn.execute(
            "SELECT * FROM receipt_reference WHERE receipt_id=? ORDER BY ordinal LIMIT 1",
            (snapshot.receipt_id,),
        ).fetchone()
        assert stored is not None
        columns = tuple(stored.keys())
        values = [stored[column] for column in columns]
        values[columns.index("ordinal")] = conn.execute(
            "SELECT MAX(ordinal)+1 FROM receipt_reference WHERE receipt_id=?",
            (snapshot.receipt_id,),
        ).fetchone()[0]
        conn.execute(
            f"INSERT INTO receipt_reference({','.join(columns)}) "
            f"VALUES ({','.join('?' for _ in columns)})",
            values,
        )

        header_columns = {
            "receipt_id",
            "ordinal",
            "output_field",
            "reference_type",
            "disposition",
            "reason_code",
            "source_schema_id",
            "source_field",
            "role",
        }
        persisted_references = []
        for row in conn.execute(
            "SELECT * FROM receipt_reference WHERE receipt_id=? ORDER BY ordinal",
            (snapshot.receipt_id,),
        ):
            identifiers = [
                row[column]
                for column in row.keys()
                if column not in header_columns and row[column] is not None
            ]
            assert len(identifiers) == 1
            persisted_references.append(
                ReceiptReference(
                    row["output_field"],
                    row["reference_type"],
                    identifiers[0],
                    row["disposition"],
                    row["reason_code"],
                    row["source_schema_id"],
                    row["source_field"],
                    row["role"],
                )
            )
        persisted_references = tuple(persisted_references)
        conn.execute(
            "UPDATE receipt_seal SET reference_count=?,references_sha256=? WHERE receipt_id=?",
            (
                len(persisted_references),
                sha256(canonical_bytes(persisted_references)),
                snapshot.receipt_id,
            ),
        )

        with pytest.raises(EvidenceRefusal, match="receipt-incomplete"):
            project_entity_mappings(conn, snapshot)
    finally:
        conn.execute("ROLLBACK TO duplicate_receipt_reference")
        conn.execute("RELEASE duplicate_receipt_reference")
