"""Portable E3 retrieval: BM25, authored dense stand-in, RRF, and graph candidate.

The dense channel is deliberately an authored concept table for the synthetic
demo. It is not an embedding model and makes no claim about live semantic
retrieval quality. All ranking ties break by document ID.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass

from quant_allocator.flagships.knowledge.graph import (
    entity_link_manager,
    graph_candidates,
)
from quant_allocator.flagships.saydo.corpus import Document

# E3 §8 ruling 5: fixed demo/retrieval constants.
BM25_K1 = 1.5
BM25_B = 0.75
RRF_K = 60
RETRIEVAL_TOPK = 10
# E3 §8 ruling 2: v1 has no two-hop theme expansion.
GRAPH_EXPANSION_HOPS = 1

_TOKEN = re.compile(r"[a-z0-9]+")
_CONCEPT_OF_TERM = {
    "duration": "duration",
    "liquidity": "liquidity",
    "redemption": "liquidity",
    "gates": "liquidity",
    "cash": "liquidity",
    "buffers": "liquidity",
    "notice": "liquidity",
    "withdrawals": "liquidity",
    "momentum": "momentum",
    "energy": "energy",
    "net": "net_exposure",
}
_CONCEPTS = ("duration", "liquidity", "momentum", "energy", "net_exposure")


@dataclass(frozen=True)
class RankedPassage:
    doc_id: str
    score: float
    rank: int


def tokenize(text: str) -> tuple[str, ...]:
    return tuple(_TOKEN.findall(text.lower()))


def bm25_scores(query: str, documents: Sequence[Document]) -> dict[str, float]:
    if not documents:
        return {}
    query_terms = tokenize(query)
    tokenized = {document.doc_id: tokenize(document.text) for document in documents}
    n_docs = len(tokenized)
    average_length = sum(len(tokens) for tokens in tokenized.values()) / n_docs
    document_frequency: Counter[str] = Counter()
    for tokens in tokenized.values():
        document_frequency.update(set(tokens))

    scores: dict[str, float] = {}
    for doc_id, tokens in tokenized.items():
        term_frequency = Counter(tokens)
        score = 0.0
        for term in query_terms:
            frequency = term_frequency[term]
            if frequency == 0:
                continue
            docs_with_term = document_frequency[term]
            inverse_frequency = math.log(
                1.0 + (n_docs - docs_with_term + 0.5) / (docs_with_term + 0.5)
            )
            denominator = frequency + BM25_K1 * (
                1.0 - BM25_B + BM25_B * len(tokens) / average_length
            )
            score += inverse_frequency * frequency * (BM25_K1 + 1.0) / denominator
        scores[doc_id] = score
    return scores


def concept_vector(text: str) -> tuple[float, ...]:
    counts = Counter(
        _CONCEPT_OF_TERM[token]
        for token in tokenize(text)
        if token in _CONCEPT_OF_TERM
    )
    return tuple(float(counts.get(concept, 0)) for concept in _CONCEPTS)


def _cosine(left: Sequence[float], right: Sequence[float]) -> float:
    dot = sum(x * y for x, y in zip(left, right, strict=True))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if left_norm == 0.0 or right_norm == 0.0:
        return 0.0
    return dot / (left_norm * right_norm)


def dense_scores(query: str, documents: Sequence[Document]) -> dict[str, float]:
    query_vector = concept_vector(query)
    return {
        document.doc_id: _cosine(query_vector, concept_vector(document.text))
        for document in documents
    }


def rank_scores(scores: dict[str, float]) -> list[str]:
    return [doc_id for doc_id, _ in sorted(scores.items(), key=lambda item: (-item[1], item[0]))]


def reciprocal_rank_fusion(
    rankings: Sequence[Sequence[str]], *, rrf_k: int = RRF_K
) -> list[RankedPassage]:
    scores: dict[str, float] = {}
    for ranking in rankings:
        for position, doc_id in enumerate(ranking, start=1):
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (rrf_k + position)
    ordered = rank_scores(scores)
    return [
        RankedPassage(doc_id=doc_id, score=scores[doc_id], rank=rank)
        for rank, doc_id in enumerate(ordered, start=1)
    ]


def hybrid_rank(query: str, documents: Sequence[Document]) -> list[RankedPassage]:
    lexical = rank_scores(bm25_scores(query, documents))
    dense = rank_scores(dense_scores(query, documents))
    return reciprocal_rank_fusion((lexical, dense))


def graph_rank(query: str, documents: Sequence[Document], conn) -> list[RankedPassage]:
    manager_id = entity_link_manager(conn, query)
    if manager_id is None:
        return []
    candidate_ids = set(graph_candidates(conn, manager_id))
    candidates = [document for document in documents if document.doc_id in candidate_ids]
    return hybrid_rank(query, candidates)
