"""Information-retrieval metrics and E3's binding paired fallback gate."""

from __future__ import annotations

import math
import random
from collections.abc import Sequence, Set

from quant_allocator.flagships.knowledge.retrieval import RankedPassage

RETRIEVAL_GATE_UPLIFT = 0.10
# NUMERICS-GATE E3-D5: deterministic paired-bootstrap settings for the live-sized eval.
PAIRED_BOOTSTRAP_SEED = 20260710
PAIRED_BOOTSTRAP_REPS = 10_000
# A single paired observation cannot provide a non-singleton paired distribution.
MIN_PAIRED_QUERIES = 2


def _ids(ranking: Sequence[str | RankedPassage]) -> list[str]:
    return [row.doc_id if isinstance(row, RankedPassage) else row for row in ranking]


def recall_at_k(
    ranking: Sequence[str | RankedPassage], relevant: Set[str], k: int
) -> float:
    if not relevant:
        return 0.0
    hits = sum(doc_id in relevant for doc_id in _ids(ranking)[:k])
    return hits / len(relevant)


def precision_at_k(
    ranking: Sequence[str | RankedPassage], relevant: Set[str], k: int
) -> float:
    if k <= 0:
        raise ValueError("k must be positive")
    hits = sum(doc_id in relevant for doc_id in _ids(ranking)[:k])
    return hits / k


def reciprocal_rank(ranking: Sequence[str | RankedPassage], relevant: Set[str]) -> float:
    for position, doc_id in enumerate(_ids(ranking), start=1):
        if doc_id in relevant:
            return 1.0 / position
    return 0.0


def ndcg_at_k(ranking: Sequence[str | RankedPassage], relevant: Set[str], k: int) -> float:
    """Binary nDCG; the current planted set carries no graded relevance labels."""

    gains = [1.0 if doc_id in relevant else 0.0 for doc_id in _ids(ranking)[:k]]
    discounted_gain = sum(gain / math.log2(position + 1) for position, gain in enumerate(gains, 1))
    ideal_hits = min(len(relevant), k)
    ideal_gain = sum(1.0 / math.log2(position + 1) for position in range(1, ideal_hits + 1))
    return discounted_gain / ideal_gain if ideal_gain else 0.0


def wilson_interval(successes: int, trials: int) -> tuple[float, float]:
    if trials <= 0 or not 0 <= successes <= trials:
        raise ValueError("Wilson interval requires 0 <= successes <= trials and trials > 0")
    z = 1.959963984540054
    rate = successes / trials
    denominator = 1.0 + z * z / trials
    centre = (rate + z * z / (2.0 * trials)) / denominator
    radius = z * math.sqrt(
        rate * (1.0 - rate) / trials + z * z / (4.0 * trials * trials)
    ) / denominator
    return max(0.0, centre - radius), min(1.0, centre + radius)


def paired_bootstrap_interval(
    differences: Sequence[float],
    *,
    seed: int = PAIRED_BOOTSTRAP_SEED,
    n_reps: int = PAIRED_BOOTSTRAP_REPS,
) -> tuple[float, float]:
    if not differences:
        raise ValueError("paired bootstrap requires at least one difference")
    if n_reps <= 0:
        raise ValueError("n_reps must be positive")
    rng = random.Random(seed)
    size = len(differences)
    means = sorted(
        sum(rng.choice(differences) for _ in range(size)) / size for _ in range(n_reps)
    )
    lower = means[int(0.025 * (n_reps - 1))]
    upper = means[int(0.975 * (n_reps - 1))]
    return lower, upper


def _metrics(
    ranking: Sequence[str | RankedPassage], relevant: Set[str], k: int
) -> dict[str, object]:
    ids = _ids(ranking)
    hits = sum(doc_id in relevant for doc_id in ids[:k])
    return {
        "recall": recall_at_k(ids, relevant, k),
        "precision": precision_at_k(ids, relevant, k),
        "mrr": reciprocal_rank(ids, relevant),
        "ndcg": ndcg_at_k(ids, relevant, k),
        "hits": hits,
        "relevant": len(relevant),
        "recall_wilson": wilson_interval(hits, len(relevant)),
    }


def evaluate_retrieval(
    baseline: Sequence[str | RankedPassage],
    graph_candidate: Sequence[str | RankedPassage],
    relevant: Set[str],
    *,
    k: int,
) -> dict[str, object]:
    return {
        "k": k,
        "baseline": _metrics(baseline, relevant, k),
        "graph_candidate": _metrics(graph_candidate, relevant, k),
        "relevance": "binary",
    }


def evaluate_gate(paired_results: Sequence[dict[str, object]]) -> dict[str, object]:
    differences = [
        float(result["graph_candidate"]["recall"])
        - float(result["baseline"]["recall"])
        for result in paired_results
    ]
    uplift = sum(differences) / len(differences) if differences else 0.0
    interval = None
    if len(differences) < MIN_PAIRED_QUERIES:
        state = "insufficient"
    else:
        interval = paired_bootstrap_interval(differences)
        state = (
            "pass"
            if uplift >= RETRIEVAL_GATE_UPLIFT and interval[0] > 0.0
            else "fail"
        )

    graph_cleared = state == "pass"
    return {
        "state": state,
        "query_count": len(differences),
        "uplift": uplift,
        "required_uplift": RETRIEVAL_GATE_UPLIFT,
        "paired_interval": interval,
        "interval_rule": "lower_bound_above_zero",
        "active_retrieval": "graph_augmented" if graph_cleared else "hybrid_search",
        "graph_status": "active" if graph_cleared else "candidate_gate_not_cleared",
    }
