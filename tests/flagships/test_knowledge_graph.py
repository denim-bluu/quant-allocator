import sqlite3

import pytest

from quant_allocator.demo_data.e3_knowledge import _graph_fixture
from quant_allocator.flagships.knowledge.evidence_bridge import build_e3_evidence
from quant_allocator.flagships.knowledge.graph import (
    EDGE_TABLES,
    NODE_TABLES,
    GraphFixture,
    candidate_paths,
    entity_link_manager,
    graph_candidates,
    ingest_fixture,
    initialize_schema,
)
from quant_allocator.flagships.saydo.corpus import build_corpus

SPAN = "The portfolio manager walked through how redemption gates would apply under stress"


def graph_fixture() -> GraphFixture:
    fixture, _ = _fixture_and_store()
    tables = {name: [dict(row) for row in rows] for name, rows in fixture.tables.items()}
    tables["document"] = [row for row in tables["document"] if row["doc_id"] != "DDQ-2024"]
    tables["attributed_to"] = [
        row for row in tables["attributed_to"] if row["doc_id"] != "DDQ-2024"
    ]
    return GraphFixture(tables)


def _row(**values):
    """Compatibility adapter for retrieval tests that extend the canonical fixture."""

    fixture, _ = _fixture_and_store()
    if "doc_type" in values:
        table, key = "document", "doc_id"
    elif {"doc_id", "manager_id"} <= values.keys():
        table, key = "attributed_to", "doc_id"
    else:
        raise KeyError(values)
    match = next(row for row in fixture.tables[table] if row[key] == values[key])
    return {**match, **{name: value for name, value in values.items() if name != "text"}}


def _fixture_and_store():
    corpus = build_corpus(include_ddq_and_notes=True)
    store = build_e3_evidence(corpus)
    return _graph_fixture(corpus, store), store


def _loaded_graph():
    fixture, store = _fixture_and_store()
    initialize_schema(store.conn)
    ingest_fixture(store.conn, fixture)
    return store.conn


def test_schema_uses_canonical_entities_spans_and_relationships() -> None:
    fixture, store = _fixture_and_store()
    initialize_schema(store.conn)
    tables = {
        row[0] for row in store.conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }
    assert set(NODE_TABLES) <= tables
    assert set(EDGE_TABLES) <= tables
    for table in NODE_TABLES:
        columns = {row["name"] for row in store.conn.execute(f'PRAGMA table_info("{table}")')}
        assert {"canonical_entity_id", "evidence_span_id"} <= columns
        assert {"source_doc", "source_span", "as_of"}.isdisjoint(columns)
    for table in EDGE_TABLES:
        assert "entity_relationship_id" in {
            row["name"] for row in store.conn.execute(f'PRAGMA table_info("{table}")')
        }
    ingest_fixture(store.conn, fixture)
    for table in EDGE_TABLES:
        for row in store.conn.execute(f'SELECT * FROM "{table}"'):
            relationship = store.conn.execute(
                "SELECT relation_type,evidence_span_id FROM entity_relationship "
                "WHERE entity_relationship_id=?",
                (row["entity_relationship_id"],),
            ).fetchone()
            assert relationship["relation_type"] == table
            assert relationship["evidence_span_id"] == row["evidence_span_id"]


def test_bad_evidence_span_and_dangling_edge_fail() -> None:
    fixture, store = _fixture_and_store()
    initialize_schema(store.conn)
    tables = {name: [dict(row) for row in rows] for name, rows in fixture.tables.items()}
    tables["view"][0]["evidence_span_id"] = "span:sha256:" + "0" * 64
    with pytest.raises(sqlite3.IntegrityError):
        ingest_fixture(store.conn, GraphFixture(tables))

    fixture, store = _fixture_and_store()
    initialize_schema(store.conn)
    tables = {name: [dict(row) for row in rows] for name, rows in fixture.tables.items()}
    tables["authored_by"][0]["entity_relationship_id"] = tables["expresses"][0][
        "entity_relationship_id"
    ]
    with pytest.raises(sqlite3.IntegrityError, match="canonical relationship projection"):
        ingest_fixture(store.conn, GraphFixture(tables))

    fixture, store = _fixture_and_store()
    initialize_schema(store.conn)
    tables = {name: [dict(row) for row in rows] for name, rows in fixture.tables.items()}
    tables["authored_by"][0]["doc_id"] = "MISSING"
    with pytest.raises(sqlite3.IntegrityError):
        ingest_fixture(store.conn, GraphFixture(tables))


def test_entity_link_and_one_hop_candidates_are_unchanged() -> None:
    conn = _loaded_graph()
    assert entity_link_manager(conn, "What did Corvid-Lane Capital say?") == "CLC"
    assert graph_candidates(conn, "CLC") == ["DDQ-2024", "L-2024Q1", "MTG-2024-05"]
    assert candidate_paths(conn, "CLC", "MTG-2024-05") == ("authored_by:EV->employed_by:CLC",)
    assert "DDQ-WEX" not in graph_candidates(conn, "CLC")


def test_employment_end_is_half_open_at_boundary() -> None:
    fixture, store = _fixture_and_store()
    initialize_schema(store.conn)
    tables = {name: [dict(row) for row in rows] for name, rows in fixture.tables.items()}
    for document in tables["document"]:
        if document["doc_id"] == "L-2024Q1":
            document["date"] = "2024-01"
    ingest_fixture(store.conn, GraphFixture(tables))
    assert candidate_paths(store.conn, "SPA", "L-2024Q1") == ()


def test_insertion_order_does_not_change_candidate_order() -> None:
    fixture, store = _fixture_and_store()
    initialize_schema(store.conn)
    reversed_fixture = GraphFixture(
        {name: list(reversed(rows)) for name, rows in fixture.tables.items()}
    )
    ingest_fixture(store.conn, reversed_fixture)
    assert graph_candidates(store.conn, "CLC") == ["DDQ-2024", "L-2024Q1", "MTG-2024-05"]
