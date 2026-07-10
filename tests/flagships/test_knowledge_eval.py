import pytest

from quant_allocator.flagships.knowledge.eval import (
    MIN_PAIRED_QUERIES,
    PAIRED_BOOTSTRAP_REPS,
    PAIRED_BOOTSTRAP_SEED,
    RETRIEVAL_GATE_UPLIFT,
    evaluate_gate,
    evaluate_retrieval,
    ndcg_at_k,
    paired_bootstrap_interval,
    wilson_interval,
)
from quant_allocator.flagships.knowledge.retrieval import graph_rank, hybrid_rank
from quant_allocator.flagships.saydo.corpus import build_corpus, planted_relevance
from tests.flagships.test_knowledge_retrieval import QUERY, _retrieval_graph


def _rankings():
    documents = build_corpus(include_ddq_and_notes=True)
    plain = hybrid_rank(QUERY, documents)
    graph = graph_rank(QUERY, documents, _retrieval_graph())
    relevant = set(planted_relevance()[0]["relevant_doc_ids"])
    return plain, graph, relevant


def test_gate_constants_and_minimum_paired_evidence_are_named():
    assert RETRIEVAL_GATE_UPLIFT == 0.10
    assert MIN_PAIRED_QUERIES == 2
    assert (PAIRED_BOOTSTRAP_SEED, PAIRED_BOOTSTRAP_REPS) == (20260710, 10_000)


def test_illustrative_top_three_metrics_are_pinned():
    plain, graph, relevant = _rankings()
    result = evaluate_retrieval(plain, graph, relevant, k=3)
    assert result["baseline"]["recall"] == pytest.approx(2 / 3)
    assert result["baseline"]["precision"] == pytest.approx(2 / 3)
    assert result["graph_candidate"]["recall"] == 1.0
    assert result["graph_candidate"]["precision"] == 1.0


def test_current_formal_gate_is_insufficient_and_selects_hybrid():
    plain, graph, relevant = _rankings()
    formal = evaluate_retrieval(plain, graph, relevant, k=10)
    gate = evaluate_gate([formal])
    assert formal["baseline"]["recall"] == 1.0
    assert formal["graph_candidate"]["recall"] == 1.0
    assert gate["uplift"] == 0.0
    assert gate["state"] == "insufficient"
    assert gate["paired_interval"] is None
    assert gate["active_retrieval"] == "hybrid_search"
    assert gate["graph_status"] == "candidate_gate_not_cleared"


def test_gate_requires_both_uplift_and_positive_interval():
    passing = [
        {"baseline": {"recall": 0.5}, "graph_candidate": {"recall": 0.7}},
        {"baseline": {"recall": 0.6}, "graph_candidate": {"recall": 0.8}},
        {"baseline": {"recall": 0.4}, "graph_candidate": {"recall": 0.6}},
    ]
    assert evaluate_gate(passing)["state"] == "pass"

    uncertain = [
        {"baseline": {"recall": 0.1}, "graph_candidate": {"recall": 0.6}},
        {"baseline": {"recall": 0.6}, "graph_candidate": {"recall": 0.5}},
        {"baseline": {"recall": 0.6}, "graph_candidate": {"recall": 0.5}},
        {"baseline": {"recall": 0.1}, "graph_candidate": {"recall": 0.6}},
    ]
    result = evaluate_gate(uncertain)
    assert result["uplift"] >= RETRIEVAL_GATE_UPLIFT
    assert result["paired_interval"][0] <= 0.0
    assert result["state"] == "fail"
    assert result["active_retrieval"] == "hybrid_search"


def test_intervals_are_bounded_and_deterministic_and_ndcg_is_binary():
    first = paired_bootstrap_interval([0.2, 0.1, 0.3], n_reps=500)
    second = paired_bootstrap_interval([0.2, 0.1, 0.3], n_reps=500)
    assert first == second
    assert -1.0 <= first[0] <= first[1] <= 1.0
    wilson = wilson_interval(2, 3)
    assert 0.0 <= wilson[0] <= wilson[1] <= 1.0
    assert ndcg_at_k(["A", "B", "C"], {"B", "C"}, 3) <= 1.0
