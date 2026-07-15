from datetime import UTC, datetime

from quant_allocator.flagships.universe_coverage.coverage import build_coverage
from quant_allocator.flagships.universe_coverage.model import CoverageSelection


def _selection() -> CoverageSelection:
    return CoverageSelection(
        entity_grain="strategy",
        selected_dataset_ids=("source:a", "source:b"),
        target_grid_id="grid:1",
        active_only=True,
        freshness_policy_ids=("fresh:a", "fresh:b"),
    )


def test_coverage_deduplicates_canonical_entities_and_reconciles_exclusions() -> None:
    mappings = (
        {"entity_mapping_id": "m1", "mapping_status": "resolved", "canonical_entity_id": "strategy:1", "source_entity_type": "strategy", "dataset_version_id": "source:a"},
        {"entity_mapping_id": "m2", "mapping_status": "resolved", "canonical_entity_id": "strategy:1", "source_entity_type": "strategy", "dataset_version_id": "source:b"},
        {"entity_mapping_id": "m3", "mapping_status": "ambiguous", "canonical_entity_id": None, "source_entity_type": "strategy", "dataset_version_id": "source:a"},
    )
    memberships = (
        {"entity_mapping_id": "m1", "membership_status": "active", "canonical_cell_id": "cell:a"},
        {"entity_mapping_id": "m2", "membership_status": "active", "canonical_cell_id": "cell:a"},
        {"entity_mapping_id": "m3", "membership_status": "active", "canonical_cell_id": "cell:b"},
    )
    cells = (
        {"target_grid_cell_id": "cell:a", "eligibility_status": "eligible", "dimensions_json": '{"asset_class":"equity"}', "exclusion_reason": None},
        {"target_grid_cell_id": "cell:b", "eligibility_status": "eligible", "dimensions_json": '{"asset_class":"credit"}', "exclusion_reason": None},
        {"target_grid_cell_id": "cell:x", "eligibility_status": "excluded", "dimensions_json": '{"asset_class":"other"}', "exclusion_reason": "not-targeted"},
    )
    result = build_coverage(datetime(2024, 9, 30, tzinfo=UTC), mappings, memberships, cells, selection=_selection())
    assert result.source_rows == 3
    assert result.canonical_members == 1
    assert result.target_cells_observed == 1
    assert (result.eligible_target_cells, result.excluded_target_cells) == (2, 1)
    assert result.ambiguous_rows == 1
    assert result.denominator_label == "eligible allocator target-grid cells at strategy grain"
    assert {row.reason for row in result.queue} == {"funnel_unavailable", "repair_identity"}


def test_coverage_is_order_invariant() -> None:
    mappings = ({"entity_mapping_id": "m1", "mapping_status": "resolved", "canonical_entity_id": "strategy:1", "source_entity_type": "strategy", "dataset_version_id": "source:a"},)
    memberships = ({"entity_mapping_id": "m1", "membership_status": "active", "canonical_cell_id": "cell:a"},)
    cells = ({"target_grid_cell_id": "cell:a", "eligibility_status": "eligible", "dimensions_json": "{}", "exclusion_reason": None},)
    one = build_coverage(datetime(2024, 9, 30, tzinfo=UTC), mappings, memberships, cells, selection=_selection())
    two = build_coverage(datetime(2024, 9, 30, tzinfo=UTC), tuple(reversed(mappings)), tuple(reversed(memberships)), tuple(reversed(cells)), selection=_selection())
    assert one == two
