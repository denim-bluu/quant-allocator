"""E3 authored knowledge/retrieval fallback generator.

The active output is deterministic hybrid search. The SQLite graph is emitted
only as a candidate evaluation because the current one-query corpus cannot clear
the binding recall-at-ten paired gate. No real-document extraction runs here.
"""

from __future__ import annotations

from pathlib import Path

from quant_allocator.demo_data._emit import SITE_DATA_DIR, write_json
from quant_allocator.flagships.knowledge.brief import compose_meeting_brief
from quant_allocator.flagships.knowledge.eval import evaluate_gate, evaluate_retrieval
from quant_allocator.flagships.knowledge.graph import (
    GraphFixture,
    candidate_paths,
    connect_graph,
    graph_candidates,
    ingest_fixture,
    initialize_schema,
)
from quant_allocator.flagships.knowledge.retrieval import (
    RETRIEVAL_TOPK,
    RankedPassage,
    bm25_scores,
    dense_scores,
    graph_rank,
    hybrid_rank,
    rank_scores,
)
from quant_allocator.flagships.saydo.corpus import (
    Document,
    build_corpus,
    planted_relevance,
)

MANAGER_ID = "CLC"
MANAGER_NAME = "Corvid Lane Capital"
MANAGER_TIER = "R"
QUERY = "corvid lane liquidity 2024"
ILLUSTRATIVE_K = 3
APPROVED_NAMES = (
    "Corvid Lane Capital",
    "Elena Voss",
    "Priya Anand",
    "Selby Point Advisors",
    "Wexford Green Capital",
)

_NODE_ID = {
    "strategy": "strategy_id",
    "manager": "manager_id",
    "person": "person_id",
    "document": "doc_id",
    "view": "view_id",
    "theme": "theme_id",
    "meeting": "meeting_id",
}
_NODE_LABEL = {
    "strategy": "label",
    "manager": "name",
    "person": "name",
    "document": "doc_id",
    "view": "direction",
    "theme": "label",
    "meeting": "meeting_id",
}
_EDGE_ENDPOINTS = {
    "authored_by": ("doc_id", "person_id"),
    "attributed_to": ("doc_id", "manager_id"),
    "employed_by": ("person_id", "manager_id"),
    "expresses": ("doc_id", "view_id"),
    "about_theme": ("view_id", "theme_id"),
    "discussed_at": ("view_id", "meeting_id"),
}


def _sentences(document: Document) -> list[str]:
    return document.text.split(". ")


def _span(documents: dict[str, Document], doc_id: str, index: int = 0) -> str:
    sentence = _sentences(documents[doc_id])[index]
    if not sentence.endswith("."):
        sentence += "."
    return sentence


def _fact(
    documents: dict[str, Document], provenance_doc_id: str, span_index: int = 0, **values
) -> dict:
    return {
        **values,
        "source_doc": provenance_doc_id,
        "source_span": _span(documents, provenance_doc_id, span_index),
        "as_of": documents[provenance_doc_id].as_of,
    }


def _graph_fixture(corpus: list[Document]) -> GraphFixture:
    documents = {document.doc_id: document for document in corpus}
    document_rows = [
        {
            "doc_id": document.doc_id,
            "doc_type": document.doc_type,
            "text": document.text,
            "date": document.as_of,
            "file_path": f"authored/{document.doc_id}.txt",
            "ingest_date": "2024-06",
            "source_doc": document.doc_id,
            "source_span": document.text,
            "as_of": document.as_of,
        }
        for document in corpus
    ]
    return GraphFixture(
        tables={
            "strategy": [
                _fact(
                    documents,
                    "L-2024Q1",
                    strategy_id="ELS",
                    label="Equity long/short",
                )
            ],
            "manager": [
                _fact(
                    documents,
                    "L-2024Q1",
                    1,
                    manager_id="CLC",
                    name="Corvid Lane Capital",
                    tier="R",
                    strategy_id="ELS",
                    tier_grant_date="2024-01",
                ),
                _fact(
                    documents,
                    "L-2023Q4",
                    manager_id="SPA",
                    name="Selby Point Advisors",
                    tier="R",
                    strategy_id="ELS",
                    tier_grant_date="2023-01",
                ),
                _fact(
                    documents,
                    "DDQ-WEX",
                    1,
                    manager_id="WGC",
                    name="Wexford Green Capital",
                    tier="R",
                    strategy_id="ELS",
                    tier_grant_date="2024-01",
                ),
            ],
            "person": [
                _fact(
                    documents,
                    "MTG-2024-05",
                    person_id="EV",
                    name="Elena Voss",
                    role="Portfolio manager",
                ),
                _fact(
                    documents,
                    "L-2023Q4",
                    person_id="PA",
                    name="Priya Anand",
                    role="Portfolio manager",
                ),
            ],
            "document": document_rows,
            "view": [
                _fact(
                    documents,
                    "L-2024Q1",
                    view_id="V-LIQ-LETTER",
                    direction="neutral-explicit",
                    horizon="quarterly",
                    conviction=2,
                ),
                _fact(
                    documents,
                    "MTG-2024-05",
                    view_id="V-LIQ-MEETING",
                    direction="neutral-explicit",
                    horizon="stress",
                    conviction=2,
                ),
            ],
            "theme": [
                _fact(
                    documents,
                    "L-2024Q1",
                    theme_id="LIQ",
                    label="Liquidity",
                )
            ],
            "meeting": [
                _fact(
                    documents,
                    "MTG-2024-05",
                    meeting_id="M-2024-05",
                    date="2024-05",
                    attendees="Elena Voss",
                    linked_doc_id="MTG-2024-05",
                )
            ],
            "authored_by": [
                _fact(documents, "L-2024Q1", doc_id="L-2024Q1", person_id="EV"),
                _fact(
                    documents,
                    "MTG-2024-05",
                    doc_id="MTG-2024-05",
                    person_id="EV",
                ),
                _fact(documents, "L-2023Q4", doc_id="L-2023Q4", person_id="PA"),
            ],
            "attributed_to": [
                _fact(documents, "L-2024Q1", doc_id="L-2024Q1", manager_id="CLC"),
                _fact(documents, "DDQ-2024", doc_id="DDQ-2024", manager_id="CLC"),
                _fact(documents, "L-2023Q4", doc_id="L-2023Q4", manager_id="SPA"),
                _fact(documents, "DDQ-WEX", doc_id="DDQ-WEX", manager_id="WGC"),
            ],
            "employed_by": [
                _fact(
                    documents,
                    "MTG-2024-05",
                    person_id="EV",
                    manager_id="CLC",
                    from_date="2024-01",
                    to_date=None,
                ),
                _fact(
                    documents,
                    "L-2023Q4",
                    person_id="EV",
                    manager_id="SPA",
                    from_date="2020-01",
                    to_date="2023-12",
                ),
                _fact(
                    documents,
                    "L-2023Q4",
                    person_id="PA",
                    manager_id="SPA",
                    from_date="2020-01",
                    to_date=None,
                ),
            ],
            "expresses": [
                _fact(
                    documents,
                    "L-2024Q1",
                    doc_id="L-2024Q1",
                    view_id="V-LIQ-LETTER",
                ),
                _fact(
                    documents,
                    "MTG-2024-05",
                    doc_id="MTG-2024-05",
                    view_id="V-LIQ-MEETING",
                ),
            ],
            "about_theme": [
                _fact(
                    documents,
                    "L-2024Q1",
                    view_id="V-LIQ-LETTER",
                    theme_id="LIQ",
                ),
                _fact(
                    documents,
                    "MTG-2024-05",
                    view_id="V-LIQ-MEETING",
                    theme_id="LIQ",
                ),
            ],
            "discussed_at": [
                _fact(
                    documents,
                    "MTG-2024-05",
                    view_id="V-LIQ-MEETING",
                    meeting_id="M-2024-05",
                )
            ],
        }
    )


def _provenance(row: dict) -> dict:
    return {key: row[key] for key in ("source_doc", "source_span", "as_of")}


def _graph_payload(fixture: GraphFixture, conn) -> dict:
    nodes = []
    for node_type, id_key in _NODE_ID.items():
        for row in fixture.tables[node_type]:
            nodes.append(
                {
                    "node_id": row[id_key],
                    "node_type": node_type,
                    "label": row[_NODE_LABEL[node_type]],
                    "tier": row.get("tier"),
                    "tier_grant_date": row.get("tier_grant_date"),
                    "provenance": _provenance(row),
                }
            )
    edges = []
    for edge_type, (source_key, target_key) in _EDGE_ENDPOINTS.items():
        for row in fixture.tables[edge_type]:
            source = row[source_key]
            target = row[target_key]
            edges.append(
                {
                    "edge_id": f"{edge_type}:{source}:{target}",
                    "edge_type": edge_type,
                    "source": source,
                    "target": target,
                    "provenance": _provenance(row),
                }
            )
    candidates = graph_candidates(conn, MANAGER_ID)
    return {
        "status": "candidate_gate_not_cleared",
        "expansion_hops": 1,
        "nodes": sorted(nodes, key=lambda row: (row["node_type"], row["node_id"])),
        "edges": sorted(edges, key=lambda row: row["edge_id"]),
        "candidate_doc_ids": candidates,
        "candidate_paths": {
            doc_id: list(candidate_paths(conn, MANAGER_ID, doc_id))
            for doc_id in candidates
        },
    }


def _ranked_passages(
    ranking: list[RankedPassage], documents: dict[str, Document]
) -> list[dict]:
    return [
        {
            "doc_id": row.doc_id,
            "rank": row.rank,
            "score": row.score,
            "text": documents[row.doc_id].text,
            "provenance": {
                "source_doc": row.doc_id,
                "source_span": documents[row.doc_id].text,
                "as_of": documents[row.doc_id].as_of,
            },
        }
        for row in ranking
    ]


def build(out_dir: Path = SITE_DATA_DIR) -> Path:
    corpus = build_corpus(include_ddq_and_notes=True)
    documents = {document.doc_id: document for document in corpus}
    planted = planted_relevance()
    query_fixture = planted[0]
    relevant = set(query_fixture["relevant_doc_ids"])

    fixture = _graph_fixture(corpus)
    conn = connect_graph()
    initialize_schema(conn)
    ingest_fixture(conn, fixture)

    lexical_ids = rank_scores(bm25_scores(QUERY, corpus))
    lexical_scores = bm25_scores(QUERY, corpus)
    lexical = [
        RankedPassage(doc_id=doc_id, score=lexical_scores[doc_id], rank=rank)
        for rank, doc_id in enumerate(lexical_ids, start=1)
    ]
    dense_ids = rank_scores(dense_scores(QUERY, corpus))
    plain = hybrid_rank(QUERY, corpus)
    graph = graph_rank(QUERY, corpus, conn)

    illustrative = evaluate_retrieval(plain, graph, relevant, k=ILLUSTRATIVE_K)
    formal = evaluate_retrieval(plain, graph, relevant, k=RETRIEVAL_TOPK)
    gate = evaluate_gate([formal])
    gate["formal_metrics"] = formal
    gate["reason"] = (
        "One planted query is below the paired-evidence minimum; at recall@10 the "
        "five-document corpus is saturated."
    )

    stated_views = [
        {
            "direction": "neutral-explicit",
            "theme": "liquidity",
            "quote": _span(documents, "L-2024Q1"),
            "source_doc": "L-2024Q1",
            "source_span": _span(documents, "L-2024Q1"),
            "as_of": documents["L-2024Q1"].as_of,
        }
    ]
    open_questions = [
        {
            "question": "How would redemption gates and cash buffers behave under stress?",
            "source_doc": "MTG-2024-05",
            "source_span": _span(documents, "MTG-2024-05"),
            "as_of": documents["MTG-2024-05"].as_of,
        }
    ]
    brief = compose_meeting_brief(
        manager_id=MANAGER_ID,
        manager_name=MANAGER_NAME,
        tier=MANAGER_TIER,
        stated_views=stated_views,
        open_questions=open_questions,
    )

    payload = {
        "meta": {
            "generator": "e3_knowledge",
            "manager_id": MANAGER_ID,
            "manager_name": MANAGER_NAME,
            "tier": MANAGER_TIER,
            "corpus_count": len(corpus),
            "corpus_doc_ids": sorted(documents),
            "approved_names": list(APPROVED_NAMES),
            "active_retrieval": gate["active_retrieval"],
            "graph_status": gate["graph_status"],
            "extraction": "authored_demo_only",
            "dense_backend": "authored_concept_table_demo_only",
        },
        "graph_candidate": _graph_payload(fixture, conn),
        "retrieval": {
            "query_id": query_fixture["query_id"],
            "query": QUERY,
            "relevant_doc_ids": sorted(relevant),
            "lexical_note_rank": lexical_ids.index("MTG-2024-05") + 1,
            "dense_distractor_rank": dense_ids.index("DDQ-WEX") + 1,
            "lexical": _ranked_passages(lexical, documents),
            "plain_hybrid": _ranked_passages(plain, documents),
            "graph_candidate": _ranked_passages(graph, documents),
            "illustrative_k3": illustrative,
        },
        "retrieval_gate": gate,
        "brief": brief,
    }
    conn.close()
    return write_json(out_dir / "e3_knowledge.json", payload)
