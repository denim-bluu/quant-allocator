"""E3 authored knowledge/retrieval fallback generator.

The active output is deterministic hybrid search. The SQLite graph is emitted
only as a candidate evaluation because the current one-query corpus cannot clear
the binding recall-at-ten paired gate. No real-document extraction runs here.
"""

from __future__ import annotations

from pathlib import Path

from quant_allocator.demo_data._emit import SITE_DATA_DIR, write_json
from quant_allocator.flagships.knowledge.brief import compose_meeting_brief
from quant_allocator.flagships.knowledge.evidence_bridge import (
    E3_DECISION_AT,
    E3EvidenceStore,
    build_e3_evidence,
    documents_as_known_at,
    e3_snapshot_bundle,
    provenance_from_span,
)
from quant_allocator.flagships.knowledge.eval import evaluate_gate, evaluate_retrieval
from quant_allocator.flagships.knowledge.graph import (
    GraphFixture,
    candidate_paths,
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
RELATIONSHIP_RECORD_ID = "E3-RELATIONSHIPS"
RELATIONSHIP_RECORD_AS_OF = "2024-06"
_RELATIONSHIP_SENTENCES = (
    "E3-RELATIONSHIPS is an authored relationship record dated 2024-06.",
    "Corvid Lane Capital is an Equity long/short manager at tier R, granted 2024-01.",
    "Selby Point Advisors is an Equity long/short manager at tier R, granted 2023-01.",
    "Wexford Green Capital is an Equity long/short manager at tier R, granted 2024-01.",
    "Elena Voss is a Portfolio manager.",
    "Priya Anand is a Portfolio manager.",
    "Elena Voss was employed by Corvid Lane Capital from 2024-01 with no recorded end date.",
    "Elena Voss was employed by Selby Point Advisors from 2020-01 through 2023-12.",
    "Priya Anand was employed by Selby Point Advisors from 2020-01 with no recorded end date.",
    "Elena Voss authored document L-2024Q1.",
    "Elena Voss authored document MTG-2024-05.",
    "Priya Anand authored document L-2023Q4.",
    "Document L-2024Q1 is attributed to Corvid Lane Capital.",
    "Document DDQ-2024 is attributed to Corvid Lane Capital.",
    "Document L-2023Q4 is attributed to Selby Point Advisors.",
    "Document DDQ-WEX is attributed to Wexford Green Capital.",
    "Meeting M-2024-05 occurred in 2024-05 with attendee Elena Voss and linked document MTG-2024-05.",
    "View V-LIQ-LETTER is a neutral-explicit quarterly view with conviction 2.",
    "View V-LIQ-MEETING is a neutral-explicit stress view with conviction 2.",
    "Theme LIQ is labelled Liquidity.",
    "Document L-2024Q1 expresses view V-LIQ-LETTER.",
    "Document MTG-2024-05 expresses view V-LIQ-MEETING.",
    "View V-LIQ-LETTER is about theme LIQ.",
    "View V-LIQ-MEETING is about theme LIQ.",
    "View V-LIQ-MEETING was discussed at meeting M-2024-05.",
)
RELATIONSHIP_RECORD_TEXT = " ".join(_RELATIONSHIP_SENTENCES)

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
_EDGE_ENTITY_TYPES = {
    "authored_by": ("document", "person"),
    "attributed_to": ("document", "manager"),
    "employed_by": ("person", "manager"),
    "expresses": ("document", "view"),
    "about_theme": ("view", "theme"),
    "discussed_at": ("view", "meeting"),
}


def _sentences(document: Document) -> list[str]:
    return document.text.split(". ")


def _span(documents: dict[str, Document], doc_id: str, index: int = 0) -> str:
    sentence = _sentences(documents[doc_id])[index]
    if not sentence.endswith("."):
        sentence += "."
    return sentence


def _relationship_fact(span_index: int, **values) -> dict:
    return {**values, "_span_index": span_index}


def _canonical_entity_id(table: str, identifier: str) -> str:
    return f"{table}:{identifier.lower()}"


def _graph_fixture(corpus: list[Document], store: E3EvidenceStore) -> GraphFixture:
    document_rows = [
        {
            "doc_id": document.doc_id,
            "doc_type": document.doc_type,
            "date": document.as_of,
            "file_path": f"authored/{document.doc_id}.txt",
            "ingest_date": "2024-06",
            "canonical_entity_id": _canonical_entity_id("document", document.doc_id),
            "evidence_item_id": store.document_item_ids[document.doc_id],
            "evidence_span_id": store.document_span_ids[document.doc_id],
        }
        for document in corpus
    ]
    document_rows.append(
        {
            "doc_id": RELATIONSHIP_RECORD_ID,
            "doc_type": "relationship_record",
            "date": RELATIONSHIP_RECORD_AS_OF,
            "file_path": "authored/E3-RELATIONSHIPS.txt",
            "ingest_date": RELATIONSHIP_RECORD_AS_OF,
            "canonical_entity_id": _canonical_entity_id("document", RELATIONSHIP_RECORD_ID),
            "evidence_item_id": store.relationship_item_id,
            "evidence_span_id": store.relationship_span_ids[0],
        }
    )
    fixture = GraphFixture(
        tables={
            "strategy": [
                _relationship_fact(
                    1,
                    strategy_id="ELS",
                    label="Equity long/short",
                )
            ],
            "manager": [
                _relationship_fact(
                    1,
                    manager_id="CLC",
                    name="Corvid Lane Capital",
                    tier="R",
                    strategy_id="ELS",
                    tier_grant_date="2024-01",
                ),
                _relationship_fact(
                    2,
                    manager_id="SPA",
                    name="Selby Point Advisors",
                    tier="R",
                    strategy_id="ELS",
                    tier_grant_date="2023-01",
                ),
                _relationship_fact(
                    3,
                    manager_id="WGC",
                    name="Wexford Green Capital",
                    tier="R",
                    strategy_id="ELS",
                    tier_grant_date="2024-01",
                ),
            ],
            "person": [
                _relationship_fact(
                    4,
                    person_id="EV",
                    name="Elena Voss",
                    role="Portfolio manager",
                ),
                _relationship_fact(
                    5,
                    person_id="PA",
                    name="Priya Anand",
                    role="Portfolio manager",
                ),
            ],
            "document": document_rows,
            "view": [
                _relationship_fact(
                    17,
                    view_id="V-LIQ-LETTER",
                    direction="neutral-explicit",
                    horizon="quarterly",
                    conviction=2,
                ),
                _relationship_fact(
                    18,
                    view_id="V-LIQ-MEETING",
                    direction="neutral-explicit",
                    horizon="stress",
                    conviction=2,
                ),
            ],
            "theme": [
                _relationship_fact(
                    19,
                    theme_id="LIQ",
                    label="Liquidity",
                )
            ],
            "meeting": [
                _relationship_fact(
                    16,
                    meeting_id="M-2024-05",
                    date="2024-05",
                    attendees="Elena Voss",
                    linked_doc_id="MTG-2024-05",
                )
            ],
            "authored_by": [
                _relationship_fact(9, doc_id="L-2024Q1", person_id="EV"),
                _relationship_fact(
                    10,
                    doc_id="MTG-2024-05",
                    person_id="EV",
                ),
                _relationship_fact(11, doc_id="L-2023Q4", person_id="PA"),
            ],
            "attributed_to": [
                _relationship_fact(12, doc_id="L-2024Q1", manager_id="CLC"),
                _relationship_fact(13, doc_id="DDQ-2024", manager_id="CLC"),
                _relationship_fact(14, doc_id="L-2023Q4", manager_id="SPA"),
                _relationship_fact(15, doc_id="DDQ-WEX", manager_id="WGC"),
            ],
            "employed_by": [
                _relationship_fact(
                    6,
                    person_id="EV",
                    manager_id="CLC",
                    from_date="2024-01",
                    to_date=None,
                ),
                _relationship_fact(
                    7,
                    person_id="EV",
                    manager_id="SPA",
                    from_date="2020-01",
                    to_date="2023-12",
                ),
                _relationship_fact(
                    8,
                    person_id="PA",
                    manager_id="SPA",
                    from_date="2020-01",
                    to_date=None,
                ),
            ],
            "expresses": [
                _relationship_fact(
                    20,
                    doc_id="L-2024Q1",
                    view_id="V-LIQ-LETTER",
                ),
                _relationship_fact(
                    21,
                    doc_id="MTG-2024-05",
                    view_id="V-LIQ-MEETING",
                ),
            ],
            "about_theme": [
                _relationship_fact(
                    22,
                    view_id="V-LIQ-LETTER",
                    theme_id="LIQ",
                ),
                _relationship_fact(
                    23,
                    view_id="V-LIQ-MEETING",
                    theme_id="LIQ",
                ),
            ],
            "discussed_at": [
                _relationship_fact(
                    24,
                    view_id="V-LIQ-MEETING",
                    meeting_id="M-2024-05",
                )
            ],
        }
    )
    bound: dict[str, list[dict]] = {}
    for table, rows in fixture.tables.items():
        id_key = _NODE_ID.get(table)
        bound[table] = []
        for original in rows:
            row = dict(original)
            span_index = row.pop("_span_index", None)
            if span_index is not None:
                row["evidence_span_id"] = store.relationship_span_ids[span_index]
            if id_key is not None and table != "document":
                row["canonical_entity_id"] = _canonical_entity_id(table, str(row[id_key]))
            if table in _EDGE_ENDPOINTS:
                source_key, target_key = _EDGE_ENDPOINTS[table]
                source_kind, target_kind = _EDGE_ENTITY_TYPES[table]
                row["entity_relationship_id"] = store.entity_relationship_ids[
                    (
                        table,
                        _canonical_entity_id(source_kind, str(row[source_key])),
                        _canonical_entity_id(target_kind, str(row[target_key])),
                    )
                ]
            bound[table].append(row)
    return GraphFixture(tables=bound)


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
                    "evidence_span_id": row["evidence_span_id"],
                    **(
                        {"evidence_item_id": row["evidence_item_id"]}
                        if row.get("evidence_item_id")
                        else {}
                    ),
                    "provenance": provenance_from_span(conn, row["evidence_span_id"]),
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
                    "from_date": row.get("from_date"),
                    "to_date": row.get("to_date"),
                    "evidence_span_id": row["evidence_span_id"],
                    **(
                        {"entity_relationship_id": row["entity_relationship_id"]}
                        if row.get("entity_relationship_id")
                        else {}
                    ),
                    "provenance": provenance_from_span(conn, row["evidence_span_id"]),
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
            doc_id: list(candidate_paths(conn, MANAGER_ID, doc_id)) for doc_id in candidates
        },
    }


def _ranked_passages(ranking: list[RankedPassage], documents: dict[str, Document]) -> list[dict]:
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
    authored_corpus = build_corpus(include_ddq_and_notes=True)
    store = build_e3_evidence(authored_corpus)
    bundle = e3_snapshot_bundle(store, E3_DECISION_AT)
    corpus = list(documents_as_known_at(store, bundle))
    documents = {document.doc_id: document for document in corpus}
    planted = planted_relevance()
    query_fixture = planted[0]
    relevant = set(query_fixture["relevant_doc_ids"])

    fixture = _graph_fixture(corpus, store)
    conn = store.conn
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
            "graph_receipt_doc_ids": [RELATIONSHIP_RECORD_ID],
            "active_retrieval": gate["active_retrieval"],
            "graph_status": gate["graph_status"],
            "extraction": "authored_demo_only",
            "dense_backend": "authored_concept_table_demo_only",
        },
        "evidence": {
            "schema_version": "evidence-v1",
            "schema_digest": store.schema_digest,
            "decision_at": bundle.slices[0].decision_at,
            "access_context": bundle.slices[0].request.access_context,
            "evidence_right_id": store.evidence_right_id,
            "licence_purpose": bundle.slices[0].request.licence_purpose,
            "slice_digest": bundle.slices[0].digest,
            "join_receipt_id": bundle.join_receipt_id,
            "bundle_digest": bundle.bundle_digest,
            "record_count": len(bundle.slices[0].rows),
            "receipt_ids": [bundle.slices[0].receipt_id, bundle.join_receipt_id],
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
