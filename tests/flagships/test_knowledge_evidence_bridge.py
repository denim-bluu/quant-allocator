from datetime import UTC, datetime

from quant_allocator.demo_data.e3_knowledge import RELATIONSHIP_RECORD_ID
from quant_allocator.evidence.lineage import verify_receipt
from quant_allocator.flagships.knowledge.evidence_bridge import (
    E3_DECISION_AT,
    build_e3_evidence,
    documents_as_known_at,
    e3_snapshot_bundle,
    provenance_from_span,
)
from quant_allocator.flagships.saydo.corpus import build_corpus


def test_e3_bridge_materializes_only_retrieval_documents_as_known_at() -> None:
    expected = build_corpus(include_ddq_and_notes=True)
    store = build_e3_evidence(expected)

    before = e3_snapshot_bundle(store, decision_at=datetime(2024, 5, 31, 23, 59, 59, tzinfo=UTC))
    june = e3_snapshot_bundle(store, decision_at=E3_DECISION_AT)
    july = e3_snapshot_bundle(store, decision_at=datetime(2024, 7, 31, 23, 59, 59, tzinfo=UTC))

    assert documents_as_known_at(store, before) == ()
    assert before.slices[0].receipt_id is not None
    verify_receipt(store.conn, before.slices[0].receipt_id, before)
    verify_receipt(store.conn, before.join_receipt_id, before)
    assert documents_as_known_at(store, june) == tuple(expected)
    assert documents_as_known_at(store, july) == tuple(expected)
    assert RELATIONSHIP_RECORD_ID not in {doc.doc_id for doc in documents_as_known_at(store, june)}
    assert (
        store.conn.execute(
            "SELECT count(*) FROM evidence_item JOIN source_record USING(source_record_id) "
            "WHERE source_record_key=?",
            (RELATIONSHIP_RECORD_ID,),
        ).fetchone()[0]
        == 2
    )


def test_e3_bridge_resolves_display_provenance_from_canonical_span() -> None:
    store = build_e3_evidence(build_corpus(include_ddq_and_notes=True))
    span_id = store.document_span_ids["L-2024Q1"]

    assert provenance_from_span(store.conn, span_id) == {
        "source_doc": "L-2024Q1",
        "source_span": build_corpus(include_ddq_and_notes=True)[0].text,
        "as_of": "2024-03",
    }


def test_every_authored_graph_edge_has_one_canonical_relationship() -> None:
    store = build_e3_evidence(build_corpus(include_ddq_and_notes=True))
    counts = dict(
        store.conn.execute(
            "SELECT relation_type,count(*) FROM entity_relationship GROUP BY relation_type"
        ).fetchall()
    )
    assert counts == {
        "about_theme": 2,
        "attributed_to": 4,
        "authored_by": 3,
        "discussed_at": 1,
        "employed_by": 3,
        "expresses": 2,
    }
    rows = store.conn.execute(
        "SELECT entity_relationship_id,relation_type,source_entity_id,target_entity_id "
        "FROM entity_relationship"
    ).fetchall()
    assert len(rows) == len(store.entity_relationship_ids) == 15
    for row in rows:
        key = (row["relation_type"], row["source_entity_id"], row["target_entity_id"])
        assert row["entity_relationship_id"] == store.entity_relationship_ids[key]
        assert row["entity_relationship_id"].startswith("entity-relation:sha256:")
