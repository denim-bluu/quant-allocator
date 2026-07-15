from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from .validation import wilson_interval


@dataclass(frozen=True, slots=True)
class TruthPair:
    pair_id: str
    is_match: bool
    predicted_match: bool


@dataclass(frozen=True, slots=True)
class HiddenMember:
    canonical_entity_id: str
    target_cell_id: str


@dataclass(frozen=True, slots=True)
class ResolutionAudit:
    true_positives: int
    false_positives: int
    false_negatives: int
    true_negatives: int
    precision_interval: tuple[float, float]
    recall_interval: tuple[float, float]
    gate_passes: bool
    fallback: str


@dataclass(frozen=True, slots=True)
class DiscoveryAudit:
    observed_hidden: int
    hidden_denominator: int
    recall: float
    label: str = "synthetic fixture recall"


def entity_resolution_audit(labels: Sequence[TruthPair]) -> ResolutionAudit:
    tp = sum(row.is_match and row.predicted_match for row in labels)
    fp = sum(not row.is_match and row.predicted_match for row in labels)
    fn = sum(row.is_match and not row.predicted_match for row in labels)
    tn = sum(not row.is_match and not row.predicted_match for row in labels)
    precision = wilson_interval(tp, tp + fp)
    recall = wilson_interval(tp, tp + fn)
    passes = fp == 0 and tp >= 381 and precision[0] >= 0.99 and recall[0] >= 0.95
    return ResolutionAudit(
        tp,
        fp,
        fn,
        tn,
        precision,
        recall,
        passes,
        "exact-id-and-reviewed-crosswalk-only" if not passes else "not-required",
    )


def synthetic_discovery_audit(
    observed_ids: Sequence[str], hidden_universe: Sequence[HiddenMember]
) -> DiscoveryAudit:
    hidden = {row.canonical_entity_id for row in hidden_universe}
    observed = len(hidden.intersection(observed_ids))
    return DiscoveryAudit(observed, len(hidden), observed / len(hidden) if hidden else 0.0)
