from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime
from typing import Mapping, Sequence

from .model import (
    CellCount,
    CoverageResult,
    CoverageSelection,
    QueueItem,
    Refusal,
    SourceNovelty,
)
from .validation import require_aware_utc


def build_coverage(
    decision_at: datetime,
    mappings: Sequence[Mapping[str, object]],
    memberships: Sequence[Mapping[str, object]],
    target_grid_cells: Sequence[Mapping[str, object]],
    *,
    selection: CoverageSelection,
) -> CoverageResult:
    decision_at = require_aware_utc(decision_at)
    mapping_by_id = {str(row["entity_mapping_id"]): row for row in mappings}
    member_by_mapping: dict[str, list[Mapping[str, object]]] = defaultdict(list)
    for row in memberships:
        member_by_mapping[str(row["entity_mapping_id"])].append(row)

    eligible = sorted(
        (row for row in target_grid_cells if row["eligibility_status"] == "eligible"),
        key=lambda row: str(row["target_grid_cell_id"]),
    )
    excluded = sorted(
        (row for row in target_grid_cells if row["eligibility_status"] == "excluded"),
        key=lambda row: str(row["target_grid_cell_id"]),
    )
    resolved_by_cell: dict[str, set[str]] = defaultdict(set)
    rows_by_cell: dict[str, int] = defaultdict(int)
    datasets_by_entity: dict[str, set[str]] = defaultdict(set)
    inactive = 0
    for mapping_id, mapping in sorted(mapping_by_id.items()):
        for membership in member_by_mapping.get(mapping_id, ()):  # evidence rows remain counted
            cell_id = str(membership.get("canonical_cell_id") or "")
            if cell_id:
                rows_by_cell[cell_id] += 1
            if membership["membership_status"] != "active":
                inactive += 1
                if selection.active_only:
                    continue
            if mapping["mapping_status"] != "resolved":
                continue
            canonical_id = str(mapping.get("canonical_entity_id") or "")
            entity_type = canonical_id.split(":", 1)[0] if ":" in canonical_id else ""
            if entity_type != selection.entity_grain or not cell_id:
                continue
            resolved_by_cell[cell_id].add(canonical_id)
            datasets_by_entity[canonical_id].add(str(mapping.get("dataset_version_id", "unknown")))

    exact = tuple(
        CellCount(
            cell_id=str(row["target_grid_cell_id"]),
            dimensions=json.dumps(json.loads(str(row["dimensions_json"])), sort_keys=True),
            canonical_members=len(resolved_by_cell[str(row["target_grid_cell_id"])]),
            source_rows=rows_by_cell[str(row["target_grid_cell_id"])],
        )
        for row in eligible
    )
    queue = []
    for row in eligible:
        cell_id = str(row["target_grid_cell_id"])
        ambiguous_here = any(
            str(member.get("canonical_cell_id") or "") == cell_id
            and mapping_by_id[str(member["entity_mapping_id"])]["mapping_status"]
            in {"ambiguous", "unresolved"}
            for member in memberships
            if str(member["entity_mapping_id"]) in mapping_by_id
        )
        if ambiguous_here:
            reason, detail = "repair_identity", "Ambiguous or unresolved source rows block a canonical count."
        elif resolved_by_cell[cell_id]:
            reason, detail = "funnel_unavailable", "Typed mandate-brief cohort projection is unavailable."
        else:
            reason, detail = "source_gap", "No same-grain canonical entity is visible in selected sources."
        dimensions = json.loads(str(row["dimensions_json"]))
        queue.append(QueueItem(cell_id, str(dimensions.get("target_priority", "observe")), reason, detail))

    canonical_ids = set().union(*resolved_by_cell.values()) if resolved_by_cell else set()
    novelty = tuple(
        SourceNovelty(dataset_id, sum(dataset_ids == {dataset_id} for dataset_ids in datasets_by_entity.values()))
        for dataset_id in sorted({item for values in datasets_by_entity.values() for item in values})
    )
    return CoverageResult(
        decision_at=decision_at,
        entity_grain=selection.entity_grain,
        denominator_label=f"eligible allocator target-grid cells at {selection.entity_grain} grain",
        eligible_target_cells=len(eligible),
        excluded_target_cells=len(excluded),
        target_cells_observed=sum(bool(row.canonical_members) for row in exact),
        source_rows=len(mappings),
        canonical_members=len(canonical_ids),
        unresolved_rows=sum(row["mapping_status"] == "unresolved" for row in mappings),
        ambiguous_rows=sum(row["mapping_status"] == "ambiguous" for row in mappings),
        inactive_members=inactive,
        exact_counts_by_cell=exact,
        source_novelty=novelty,
        queue=tuple(sorted(queue, key=lambda row: (row.reason, row.target_priority, row.cell_id))),
        excluded_cells=tuple(str(row["target_grid_cell_id"]) for row in excluded),
        refusals=(Refusal("/funnel/conversion", "typed-mandate-brief-cohort-projection-required", "Conversion and downstream backlog inference are unavailable."),),
    )
