from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime


@dataclass(frozen=True, slots=True)
class CoverageSelection:
    entity_grain: str
    selected_dataset_ids: tuple[str, ...]
    target_grid_id: str
    active_only: bool
    freshness_policy_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.entity_grain or any(token in self.entity_grain for token in ("/", "|", ",")):
            raise ValueError("X3 requires one canonical entity grain")
        if not self.selected_dataset_ids or not self.target_grid_id:
            raise ValueError("X3 requires selected datasets and a target grid")


@dataclass(frozen=True, slots=True)
class Refusal:
    pointer: str
    code: str
    detail: str


@dataclass(frozen=True, slots=True)
class CellCount:
    cell_id: str
    dimensions: str
    canonical_members: int
    source_rows: int


@dataclass(frozen=True, slots=True)
class SourceNovelty:
    dataset_id: str
    canonical_members_lost: int


@dataclass(frozen=True, slots=True)
class QueueItem:
    cell_id: str
    target_priority: str
    reason: str
    detail: str


@dataclass(frozen=True, slots=True)
class CoverageResult:
    decision_at: datetime
    entity_grain: str
    denominator_label: str
    eligible_target_cells: int
    excluded_target_cells: int
    target_cells_observed: int
    source_rows: int
    canonical_members: int
    unresolved_rows: int
    ambiguous_rows: int
    inactive_members: int
    exact_counts_by_cell: tuple[CellCount, ...]
    source_novelty: tuple[SourceNovelty, ...]
    queue: tuple[QueueItem, ...]
    excluded_cells: tuple[str, ...]
    refusals: tuple[Refusal, ...]

    def __post_init__(self) -> None:
        if self.decision_at.tzinfo is None or self.decision_at.utcoffset() is None:
            raise ValueError("decision_at must be timezone-aware UTC")
        if self.decision_at.utcoffset().total_seconds() != 0:
            raise ValueError("decision_at must be timezone-aware UTC")
        object.__setattr__(self, "decision_at", self.decision_at.astimezone(UTC))


@dataclass(frozen=True, slots=True)
class FunnelSummary:
    cohort_label: str
    entry_stage: str
    outcome_stage: str
    entry_count: int
    outcome_count: int
    conversion_interval: tuple[float, float] | None
    evaluation_receipt_ids: tuple[str, ...]
    refusal: Refusal
