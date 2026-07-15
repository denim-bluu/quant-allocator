import hashlib
import json
from pathlib import Path

import pytest

from quant_allocator.demo_data import e3_knowledge
from quant_allocator.demo_data._emit import SITE_DATA_DIR
from quant_allocator.flagships.saydo.corpus import build_corpus


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _publication_terms() -> tuple[str, ...]:
    path = Path(__file__).resolve().parents[2] / "tools" / ".publication_terms"
    if not path.exists():
        return ()
    return tuple(
        line.strip().lower()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    )


def test_schema_and_binding_fallback_states(tmp_path):
    data = _load(e3_knowledge.build(out_dir=tmp_path))
    assert {
        "meta",
        "evidence",
        "graph_candidate",
        "retrieval",
        "retrieval_gate",
        "brief",
    } <= data.keys()
    assert data["meta"]["active_retrieval"] == "hybrid_search"
    assert data["meta"]["graph_status"] == "candidate_gate_not_cleared"
    assert data["meta"]["extraction"] == "authored_demo_only"
    assert data["meta"]["dense_backend"] == "authored_concept_table_demo_only"
    assert data["meta"]["corpus_count"] == 5
    assert data["meta"]["graph_receipt_doc_ids"] == [e3_knowledge.RELATIONSHIP_RECORD_ID]
    evidence = data["evidence"]
    assert evidence["decision_at"] == "2024-06-30T23:59:59.999999Z"
    assert evidence["access_context"] == "shortlisted-synthetic-demo"
    assert evidence["licence_purpose"] == "research-demo"
    assert evidence["record_count"] == 6
    assert len(evidence["receipt_ids"]) == 2


def test_canonical_retrieval_gate_and_brief_bytes_are_unchanged(tmp_path):
    data = _load(e3_knowledge.build(out_dir=tmp_path))
    expected = {
        "retrieval": "dfff11fbb495e02f860c74b8a04bad681fa529e0d62286483158c2b710728b42",
        "retrieval_gate": "a2cf35c9d72481c39f5781c31016346b7beafdd0b755b8c23eb978ccdc3d1613",
        "brief": "57a4678a2d6ff77469837d446345dac804db0f2c8826411fcb49d5add1f3a597",
    }
    for key, digest in expected.items():
        encoded = json.dumps(
            data[key], sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode()
        assert hashlib.sha256(encoded).hexdigest() == digest


def test_exact_rankings_and_gate_numbers(tmp_path):
    data = _load(e3_knowledge.build(out_dir=tmp_path))
    retrieval = data["retrieval"]
    assert [row["doc_id"] for row in retrieval["plain_hybrid"][:3]] == [
        "DDQ-2024",
        "DDQ-WEX",
        "L-2024Q1",
    ]
    assert [row["doc_id"] for row in retrieval["graph_candidate"][:3]] == [
        "DDQ-2024",
        "L-2024Q1",
        "MTG-2024-05",
    ]
    assert retrieval["lexical_note_rank"] == 5
    assert retrieval["dense_distractor_rank"] == 2
    assert retrieval["illustrative_k3"]["baseline"]["recall"] == pytest.approx(2 / 3)
    assert retrieval["illustrative_k3"]["graph_candidate"]["recall"] == 1.0
    gate = data["retrieval_gate"]
    assert gate["formal_metrics"]["baseline"]["recall"] == 1.0
    assert gate["formal_metrics"]["graph_candidate"]["recall"] == 1.0
    assert gate["uplift"] == 0.0
    assert gate["state"] == "insufficient"
    assert gate["paired_interval"] is None


def test_graph_provenance_and_wrong_firm_exclusion(tmp_path):
    data = _load(e3_knowledge.build(out_dir=tmp_path))
    corpus = {
        document.doc_id: document.text for document in build_corpus(include_ddq_and_notes=True)
    }
    corpus[e3_knowledge.RELATIONSHIP_RECORD_ID] = e3_knowledge.RELATIONSHIP_RECORD_TEXT
    graph = data["graph_candidate"]
    assert {node["node_type"] for node in graph["nodes"]} == {
        "manager",
        "strategy",
        "person",
        "document",
        "view",
        "theme",
        "meeting",
    }
    for fact in [*graph["nodes"], *graph["edges"]]:
        provenance = fact["provenance"]
        assert {"source_doc", "source_span", "as_of"} <= provenance.keys()
        assert provenance["source_doc"] in corpus
        assert provenance["source_span"] in corpus[provenance["source_doc"]]
    assert "DDQ-WEX" in data["meta"]["corpus_doc_ids"]
    assert "DDQ-WEX" not in graph["candidate_doc_ids"]
    assert e3_knowledge.RELATIONSHIP_RECORD_ID not in graph["candidate_doc_ids"]
    assert all(
        row["doc_id"] != e3_knowledge.RELATIONSHIP_RECORD_ID
        for ranking in (
            data["retrieval"]["lexical"],
            data["retrieval"]["plain_hybrid"],
            data["retrieval"]["graph_candidate"],
        )
        for row in ranking
    )


def test_relationship_receipts_substantiate_displayed_claims(tmp_path):
    data = _load(e3_knowledge.build(out_dir=tmp_path))
    graph = data["graph_candidate"]
    managers = {node["node_id"]: node for node in graph["nodes"] if node["node_type"] == "manager"}
    for manager_id, strategy in (
        ("CLC", "Equity long/short"),
        ("SPA", "Equity long/short"),
        ("WGC", "Equity long/short"),
    ):
        node = managers[manager_id]
        span = node["provenance"]["source_span"]
        assert node["label"] in span
        assert f"tier {node['tier']}" in span
        assert node["tier_grant_date"] in span
        assert strategy in span

    people = {node["node_id"]: node for node in graph["nodes"] if node["node_type"] == "person"}
    for node in people.values():
        span = node["provenance"]["source_span"]
        assert node["label"] in span
        assert "Portfolio manager" in span

    names = {
        **{key: node["label"] for key, node in managers.items()},
        **{key: node["label"] for key, node in people.items()},
    }
    employment = [edge for edge in graph["edges"] if edge["edge_type"] == "employed_by"]
    for edge in employment:
        span = edge["provenance"]["source_span"]
        assert names[edge["source"]] in span
        assert names[edge["target"]] in span
        assert edge["from_date"] in span
        if edge["to_date"] is None:
            assert "no recorded end date" in span
        else:
            assert edge["to_date"] in span


def test_partial_brief_names_missing_same_manager_sources(tmp_path):
    brief = _load(e3_knowledge.build(out_dir=tmp_path))["brief"]
    assert brief["meta"]["manager_id"] == "CLC"
    states = {section["section_id"]: section["state"] for section in brief["sections"]}
    assert states["stated_views"] == "rendered"
    assert states["open_questions"] == "rendered"
    assert states["say_do"] == "omitted"
    assert states["tear_sheet"] == "omitted"
    assert "M07" not in json.dumps(brief)


def test_approved_names_and_loaded_publication_terms_are_clean(tmp_path):
    text = e3_knowledge.build(out_dir=tmp_path).read_text(encoding="utf-8")
    lowered = text.lower()
    approved = {
        "Corvid Lane Capital",
        "Selby Point Advisors",
        "Wexford Green Capital",
        "Elena Voss",
        "Priya Anand",
    }
    data = json.loads(text)
    assert set(data["meta"]["approved_names"]) == approved
    assert not any(term in lowered for term in _publication_terms())


def test_byte_for_byte_determinism_and_matches_committed(tmp_path):
    first = e3_knowledge.build(out_dir=tmp_path).read_bytes()
    second = e3_knowledge.build(out_dir=tmp_path).read_bytes()
    assert first == second
    assert first == (SITE_DATA_DIR / "e3_knowledge.json").read_bytes()
