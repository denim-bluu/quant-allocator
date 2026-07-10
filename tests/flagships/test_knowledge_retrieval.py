from quant_allocator.flagships.knowledge.graph import (
    GraphFixture,
    connect_graph,
    ingest_fixture,
    initialize_schema,
)
from quant_allocator.flagships.knowledge.retrieval import (
    BM25_B,
    BM25_K1,
    GRAPH_EXPANSION_HOPS,
    RETRIEVAL_TOPK,
    RRF_K,
    bm25_scores,
    dense_scores,
    graph_rank,
    hybrid_rank,
    rank_scores,
)
from quant_allocator.flagships.saydo.corpus import build_corpus
from tests.flagships.test_knowledge_graph import SPAN, _row, graph_fixture


QUERY = "corvid lane liquidity 2024"


def _retrieval_graph():
    fixture = graph_fixture()
    tables = {name: list(rows) for name, rows in fixture.tables.items()}
    tables["document"].append(
        _row(
            doc_id="DDQ-2024",
            doc_type="ddq",
            text="Corvid Lane offers quarterly redemption with notice.",
            date="2024-02",
            file_path="authored/DDQ-2024.txt",
            ingest_date="2024-06",
        )
    )
    tables["attributed_to"].append(_row(doc_id="DDQ-2024", manager_id="CLC"))
    # Ensure the note is recovered only through Elena's employment path.
    assert not any(row["doc_id"] == "MTG-2024-05" for row in tables["attributed_to"])
    conn = connect_graph()
    initialize_schema(conn)
    ingest_fixture(conn, GraphFixture(tables))
    return conn


def test_binding_retrieval_constants_are_named_and_fixed():
    assert (BM25_K1, BM25_B, RRF_K) == (1.5, 0.75, 60)
    assert GRAPH_EXPANSION_HOPS == 1
    assert RETRIEVAL_TOPK == 10


def test_current_fixture_pins_lexical_and_dense_failure_modes():
    docs = build_corpus(include_ddq_and_notes=True)
    bm25 = rank_scores(bm25_scores(QUERY, docs))
    dense = rank_scores(dense_scores(QUERY, docs))
    assert bm25.index("MTG-2024-05") + 1 == 5
    assert dense.index("DDQ-WEX") + 1 == 2


def test_plain_and_graph_top_three_orders_are_exact():
    docs = build_corpus(include_ddq_and_notes=True)
    plain = [row.doc_id for row in hybrid_rank(QUERY, docs)]
    graph = [row.doc_id for row in graph_rank(QUERY, docs, _retrieval_graph())]
    assert plain[:3] == ["DDQ-2024", "DDQ-WEX", "L-2024Q1"]
    assert graph[:3] == ["DDQ-2024", "L-2024Q1", "MTG-2024-05"]


def test_rankings_are_deterministic_and_graph_is_one_hop_only():
    docs = build_corpus(include_ddq_and_notes=True)
    conn = _retrieval_graph()
    first = graph_rank(QUERY, docs, conn)
    second = graph_rank(QUERY, docs, conn)
    assert first == second
    assert "DDQ-WEX" not in {row.doc_id for row in first}
    assert next(row for row in first if row.doc_id == "MTG-2024-05").rank == 3
    assert SPAN  # fixture receipt remains a concrete source sentence
