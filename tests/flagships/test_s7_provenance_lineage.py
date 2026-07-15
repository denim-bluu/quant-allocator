"""Lineage-admission boundary tests for S7 provenance."""

from datetime import date
from decimal import Decimal

import pytest

from quant_allocator.flagships.track_record_provenance.lineage import (
    LineageExclusion,
    LineageRefusal,
    build_lineage_segments,
)


def test_lineage_admission_requires_resolved_mapping_and_effective_x3_membership() -> None:
    """Canonical-null rows stay separate one-source unmatched exclusions."""
    result = build_lineage_segments(
        (
            _lineage_row(
                "observation:admitted",
                effective_from=date(2024, 1, 1),
                effective_to=date(2024, 2, 1),
                value=Decimal("0.0100"),
            ),
            {
                "observation_id": "observation:unmatched-a",
                "dataset_id": "dataset:s7-a",
                "source_label": "Shared Label",
                "mapping_status": "unresolved",
                "canonical_entity_id": None,
                "x3_membership_effective": True,
            },
            {
                "observation_id": "observation:unmatched-b",
                "dataset_id": "dataset:s7-b",
                "source_label": "Shared Label",
                "mapping_status": "unresolved",
                "canonical_entity_id": None,
                "x3_membership_effective": True,
            },
            {
                "observation_id": "observation:missing-membership",
                "dataset_id": "dataset:s7-a",
                "source_label": "Mapped but not eligible",
                "mapping_status": "resolved",
                "canonical_entity_id": "strategy:s7-ineligible",
                "x3_membership_effective": False,
            },
        )
    )

    assert result.admitted_observation_ids == ("observation:admitted",)
    assert result.unmatched_exclusions == (
        ("dataset:s7-a", "observation:unmatched-a", "unmatched"),
        ("dataset:s7-b", "observation:unmatched-b", "unmatched"),
        ("dataset:s7-a", "observation:missing-membership", "unmatched"),
    )


def _lineage_row(
    observation_id: str,
    *,
    effective_from: date,
    effective_to: date,
    value: Decimal,
) -> dict[str, object]:
    relationship_graph = (
        {
            "entity_relationship_id": "relationship:s7-offers",
            "relation_type": "offers",
            "source_entity_id": "manager:s7-boundary",
            "target_entity_id": "strategy:s7-boundary",
            "temporal_type": "interval",
            "effective_from": "2024-01-01T00:00:00.000000Z",
            "effective_to": None,
        },
        {
            "entity_relationship_id": "relationship:s7-reported-through",
            "relation_type": "reported_through",
            "source_entity_id": "strategy:s7-boundary",
            "target_entity_id": "composite:s7-boundary",
            "temporal_type": "interval",
            "effective_from": "2024-01-01T00:00:00.000000Z",
            "effective_to": None,
        },
        {
            "entity_relationship_id": "relationship:s7-implemented-by",
            "relation_type": "implemented_by",
            "source_entity_id": "composite:s7-boundary",
            "target_entity_id": "vehicle:s7-boundary",
            "temporal_type": "interval",
            "effective_from": "2024-01-01T00:00:00.000000Z",
            "effective_to": None,
        },
        {
            "entity_relationship_id": "relationship:s7-advised-by",
            "relation_type": "advised_by",
            "source_entity_id": "manager:s7-boundary",
            "target_entity_id": "adviser:s7-boundary",
            "temporal_type": "interval",
            "effective_from": "2024-01-01T00:00:00.000000Z",
            "effective_to": None,
        },
        {
            "entity_relationship_id": "relationship:s7-legal-identity",
            "relation_type": "legal_identity",
            "source_entity_id": "adviser:s7-boundary",
            "target_entity_id": "legal-entity:s7-boundary",
            "temporal_type": "interval",
            "effective_from": "2024-01-01T00:00:00.000000Z",
            "effective_to": None,
        },
    )
    return {
        "observation_id": observation_id,
        "dataset_id": "dataset:s7-lineage",
        "mapping_status": "resolved",
        "canonical_entity_id": "vehicle:s7-boundary",
        "entity_grain": "vehicle",
        "x3_membership_effective": True,
        "mapping_ids": (f"mapping:{observation_id}", "mapping:x3-boundary"),
        "observation_membership_link_ids": (f"membership-link:{observation_id}",),
        "membership_ids": ("membership:s7-boundary",),
        "basis_id": "basis:s7-net-usd-monthly",
        "temporal_type": "interval",
        "effective_from": effective_from,
        "effective_to": effective_to,
        "observed_at": effective_from,
        "value": value,
        "relationship_graph": relationship_graph,
    }


def _segment_summary(result: object) -> tuple[tuple[object, ...], ...]:
    return tuple(
        (
            segment.segment_id,
            segment.canonical_entity_id,
            segment.entity_grain,
            segment.effective_from,
            segment.effective_to,
            segment.observation_ids,
        )
        for segment in result.segments
    )


def _latest_projected_membership_for_observation(
    conn: object, observation_id: str, cutoff_name: str
) -> dict[str, object]:
    """Return the shared latest-known membership for an S7 observation's X3 source."""
    from quant_allocator.evidence.fixtures.s7 import S7_CUTOFFS
    from quant_allocator.evidence.fixtures.x3 import build_x3_fixture
    from quant_allocator.evidence.model import DatasetSliceRequest
    from quant_allocator.evidence.projections import (
        project_entity_mappings,
        project_universe_memberships,
    )
    from quant_allocator.evidence.snapshot import as_known_slice

    linked = conn.execute(
        "SELECT membership.entity_mapping_id,mapping.source_key,source.dataset_id "
        "FROM observation_membership_link link "
        "JOIN universe_membership membership USING(universe_membership_id) "
        "JOIN entity_mapping mapping ON mapping.entity_mapping_id=membership.entity_mapping_id "
        "JOIN evidence_item item ON item.evidence_item_id=mapping.source_evidence_item_id "
        "JOIN source_record source USING(source_record_id) "
        "WHERE link.dataset_observation_id=?",
        (observation_id,),
    ).fetchone()
    assert linked is not None
    x3_manifest = build_x3_fixture(conn)
    snapshot_slice = as_known_slice(
        conn,
        decision_at=S7_CUTOFFS[cutoff_name],
        request=DatasetSliceRequest(
            linked["dataset_id"],
            x3_manifest.access_contexts[linked["dataset_id"]],
            x3_manifest.right_ids[linked["dataset_id"]],
            "x3-research",
            revision_mode="latest-known",
        ),
    )
    latest_mapping = next(
        mapping
        for mapping in project_entity_mappings(conn, snapshot_slice)
        if mapping["source_key"] == linked["source_key"]
    )
    return next(
        membership
        for membership in project_universe_memberships(conn, snapshot_slice)
        if membership["entity_mapping_id"] == latest_mapping["entity_mapping_id"]
    )


def test_lineage_segments_use_stable_ids_and_half_open_boundaries() -> None:
    """An end exactly at the next start is contiguous, never an overlap."""
    january = _lineage_row(
        "observation:s7-january",
        effective_from=date(2024, 1, 1),
        effective_to=date(2024, 2, 1),
        value=Decimal("0.0100"),
    )
    february = _lineage_row(
        "observation:s7-february",
        effective_from=date(2024, 2, 1),
        effective_to=date(2024, 3, 1),
        value=Decimal("0.0200"),
    )

    forward = build_lineage_segments((january, february))
    reversed_rows = build_lineage_segments((february, january))

    forward_segments = _segment_summary(forward)
    assert forward_segments == _segment_summary(reversed_rows)
    assert forward_segments[0][0]
    assert forward_segments == (
        (
            forward_segments[0][0],
            "vehicle:s7-boundary",
            "vehicle",
            date(2024, 1, 1),
            date(2024, 3, 1),
            ("observation:s7-january", "observation:s7-february"),
        ),
    )
    assert forward.refusals == ()


def test_lineage_admission_reconciles_unique_fully_bound_observations() -> None:
    """Duplicate IDs and provenance-empty rows never count as admitted segments."""
    bound = _lineage_row(
        "observation:s7-bound",
        effective_from=date(2024, 1, 1),
        effective_to=date(2024, 2, 1),
        value=Decimal("0.0100"),
    )
    duplicate = build_lineage_segments((bound, dict(bound)))

    assert duplicate.admitted_observation_ids == ()
    assert duplicate.segments == ()
    assert duplicate.unmatched_exclusions == (
        LineageExclusion(
            "dataset:s7-lineage",
            "observation:s7-bound",
            "entity-mapping-ambiguous",
        ),
    )

    incomplete = dict(bound)
    del incomplete["mapping_ids"]
    missing_provenance = build_lineage_segments((incomplete,))

    assert missing_provenance.admitted_observation_ids == ()
    assert missing_provenance.segments == ()
    assert missing_provenance.unmatched_exclusions == (
        LineageExclusion(
            "dataset:s7-lineage",
            "observation:s7-bound",
            "receipt-incomplete",
        ),
    )


def test_lineage_admission_refuses_relationship_paths_without_shared_ids() -> None:
    """Effective edge fields cannot substitute for persisted relationship IDs."""
    row = _lineage_row(
        "observation:s7-missing-path-ids",
        effective_from=date(2024, 1, 1),
        effective_to=date(2024, 2, 1),
        value=Decimal("0.0100"),
    )
    row["relationship_graph"] = tuple(
        {
            key: value
            for key, value in edge.items()
            if key != "entity_relationship_id"
        }
        for edge in row["relationship_graph"]
    )

    result = build_lineage_segments((row,))

    assert result.admitted_observation_ids == ()
    assert result.segments == ()
    assert result.refusals == (
        LineageRefusal(
            "lineage-relationship-missing", "vehicle:s7-boundary", "vehicle"
        ),
    )


@pytest.mark.parametrize(
    "field_name",
    ("mapping_ids", "observation_membership_link_ids", "membership_ids"),
)
def test_lineage_admission_rejects_blank_projection_reference_ids(
    field_name: str,
) -> None:
    """Present-but-blank projection references cannot satisfy provenance closure."""
    row = _lineage_row(
        "observation:s7-blank-reference",
        effective_from=date(2024, 1, 1),
        effective_to=date(2024, 2, 1),
        value=Decimal("0.0100"),
    )
    row[field_name] = (
        ("", "mapping:x3-boundary") if field_name == "mapping_ids" else ("",)
    )

    result = build_lineage_segments((row,))

    assert result.admitted_observation_ids == ()
    assert result.segments == ()
    assert result.unmatched_exclusions == (
        LineageExclusion(
            "dataset:s7-lineage",
            "observation:s7-blank-reference",
            "receipt-incomplete",
        ),
    )


def test_lineage_segment_identity_binds_projection_and_path_references() -> None:
    """A segment exposes and hashes every mapping, link, membership, and path ID."""
    january = _lineage_row(
        "observation:s7-january",
        effective_from=date(2024, 1, 1),
        effective_to=date(2024, 2, 1),
        value=Decimal("0.0100"),
    )
    february = _lineage_row(
        "observation:s7-february",
        effective_from=date(2024, 2, 1),
        effective_to=date(2024, 3, 1),
        value=Decimal("0.0200"),
    )

    baseline = build_lineage_segments((january, february)).segments[0]

    assert baseline.mapping_ids == (
        "mapping:observation:s7-february",
        "mapping:observation:s7-january",
        "mapping:x3-boundary",
    )
    assert baseline.observation_membership_link_ids == (
        "membership-link:observation:s7-february",
        "membership-link:observation:s7-january",
    )
    assert baseline.membership_ids == ("membership:s7-boundary",)
    assert baseline.relationship_ids == (
        "relationship:s7-offers",
        "relationship:s7-reported-through",
        "relationship:s7-implemented-by",
        "relationship:s7-advised-by",
        "relationship:s7-legal-identity",
    )

    february["mapping_ids"] = (*february["mapping_ids"], "mapping:x3-revised")
    changed = build_lineage_segments((january, february)).segments[0]

    assert changed.segment_id != baseline.segment_id


def test_lineage_segments_split_at_unique_effective_relationship_path_change() -> None:
    """A unique path revision at a valid boundary starts a reviewable segment."""
    january = _lineage_row(
        "observation:s7-january",
        effective_from=date(2024, 1, 1),
        effective_to=date(2024, 2, 1),
        value=Decimal("0.0100"),
    )
    february = _lineage_row(
        "observation:s7-february",
        effective_from=date(2024, 2, 1),
        effective_to=date(2024, 3, 1),
        value=Decimal("0.0200"),
    )
    february["relationship_graph"] = tuple(
        {
            **edge,
            "entity_relationship_id": f"{edge['entity_relationship_id']}:revision-2",
            "effective_from": "2024-02-01T00:00:00.000000Z",
        }
        for edge in february["relationship_graph"]
    )

    result = build_lineage_segments((january, february))

    assert result.refusals == ()
    assert tuple(
        (segment.effective_from, segment.effective_to, segment.observation_ids)
        for segment in result.segments
    ) == (
        (date(2024, 1, 1), date(2024, 2, 1), ("observation:s7-january",)),
        (date(2024, 2, 1), date(2024, 3, 1), ("observation:s7-february",)),
    )


def test_lineage_segments_refuse_non_positive_effective_intervals() -> None:
    """An admitted zero-width half-open interval has no assignable lineage span."""
    result = build_lineage_segments(
        (
            _lineage_row(
                "observation:s7-empty-interval",
                effective_from=date(2024, 2, 1),
                effective_to=date(2024, 2, 1),
                value=Decimal("0.0100"),
            ),
        )
    )

    assert result.admitted_observation_ids == ()
    assert _segment_summary(result) == ()
    assert isinstance(result.refusals[0], LineageRefusal)
    assert result.refusals == (
        LineageRefusal("lineage-invalid-interval", "vehicle:s7-boundary", "vehicle"),
    )


def test_lineage_segments_refuse_mixed_entity_grains_for_one_candidate() -> None:
    """One canonical candidate cannot stitch composite and vehicle observations."""
    vehicle = _lineage_row(
        "observation:s7-vehicle",
        effective_from=date(2024, 1, 1),
        effective_to=date(2024, 2, 1),
        value=Decimal("0.0100"),
    )
    composite = _lineage_row(
        "observation:s7-composite",
        effective_from=date(2024, 2, 1),
        effective_to=date(2024, 3, 1),
        value=Decimal("0.0200"),
    )
    composite["entity_grain"] = "composite"

    result = build_lineage_segments((vehicle, composite))

    assert result.admitted_observation_ids == ()
    assert _segment_summary(result) == ()
    assert len(result.refusals) == 1
    assert isinstance(result.refusals[0], LineageRefusal)
    assert result.refusals[0].reason_code == "entity-grain-mismatch"
    assert result.refusals[0].canonical_entity_id == "vehicle:s7-boundary"


def test_build_lineage_from_s7_projections_preserves_mapping_and_membership_provenance() -> None:
    """The adapter consumes shared snapshot projections, not caller-authored row dictionaries."""
    from quant_allocator.evidence.fixtures.s7 import (
        S7_CUTOFFS,
        build_s7_fixture,
        s7_source_requests,
    )
    from quant_allocator.evidence.model import SnapshotBundleRequest
    from quant_allocator.evidence.projections import project_entity_mappings
    from quant_allocator.evidence.schema import connect, initialize
    from quant_allocator.evidence.snapshot import as_known_bundle

    conn = connect()
    initialize(conn)
    manifest = build_s7_fixture(conn)
    cutoff_name = "early"

    def scenario_projection_rows(scenario: str) -> tuple[tuple[str, dict[str, object]], ...]:
        bundle = as_known_bundle(
            conn,
            SnapshotBundleRequest(
                S7_CUTOFFS[cutoff_name],
                s7_source_requests(
                    manifest,
                    scenario=scenario,
                    cutoff_name=cutoff_name,
                    revision_mode="latest-known",
                ),
                ("field_dictionary_version",),
                "s7-track-lineage-v1",
            ),
        )
        return tuple(
            (snapshot_slice.request.dataset_id, mapping)
            for snapshot_slice in bundle.slices
            for mapping in project_entity_mappings(conn, snapshot_slice)
        )

    public_rows = scenario_projection_rows("public-equity")
    hedge_rows = scenario_projection_rows("hedge-fund")
    same_label_exclusions = {
        (dataset_id, str(mapping["dataset_observation_id"]), "unmatched")
        for dataset_id, mapping in (*public_rows, *hedge_rows)
        if mapping["source_label"] == "s7-null-same-label"
        and mapping["mapping_status"] == "unresolved"
    }
    expected_admitted_ids = {
        str(mapping["dataset_observation_id"])
        for _, mapping in (*public_rows, *hedge_rows)
        if mapping["mapping_status"] == "resolved"
        and isinstance(mapping["canonical_entity_id"], str)
            and conn.execute(
                "SELECT 1 FROM observation_membership_link link "
                "JOIN universe_membership membership USING(universe_membership_id) "
                "JOIN entity_mapping mapping USING(dataset_observation_id) "
                "WHERE link.dataset_observation_id=? AND membership.membership_status='active' "
                "AND ((membership.temporal_type='point' "
                "AND membership.effective_at=mapping.effective_at) "
                "OR (membership.temporal_type='interval' "
                "AND membership.effective_from<=mapping.effective_at "
                "AND (membership.effective_to IS NULL "
                "OR mapping.effective_at<membership.effective_to)))",
            (mapping["dataset_observation_id"],),
        ).fetchone()
        is not None
    }
    assert len(same_label_exclusions) == 2
    assert expected_admitted_ids
    late_only_retro_ids = {
        str(row[0])
        for row in conn.execute(
            "SELECT link.dataset_observation_id FROM observation_membership_link link "
            "JOIN universe_membership membership USING(universe_membership_id) "
            "JOIN entity_mapping x3_mapping USING(entity_mapping_id) "
            "WHERE x3_mapping.source_key='x3-source-0003'"
        )
    }
    assert len(late_only_retro_ids) == 1
    overlap_ids = {
        str(mapping["dataset_observation_id"])
        for _, mapping in hedge_rows
        if mapping["source_key"] == "s7-hf-overlap"
    }
    assert len(overlap_ids) == 1
    expected_early_admitted_ids = (
        expected_admitted_ids - late_only_retro_ids - overlap_ids
    )

    from quant_allocator.flagships.track_record_provenance.lineage import (
        build_lineage_from_s7_projections,
    )

    public = build_lineage_from_s7_projections(
        conn, manifest, scenario="public-equity", cutoff_name=cutoff_name
    )
    hedge = build_lineage_from_s7_projections(
        conn, manifest, scenario="hedge-fund", cutoff_name=cutoff_name
    )

    exclusions = {
        (exclusion.dataset_id, exclusion.observation_id, exclusion.reason_code)
        for result in (public, hedge)
        for exclusion in result.unmatched_exclusions
    }
    assert all(
        isinstance(exclusion, LineageExclusion)
        for result in (public, hedge)
        for exclusion in result.unmatched_exclusions
    )
    assert same_label_exclusions <= exclusions
    assert tuple(
        sorted((*public.admitted_observation_ids, *hedge.admitted_observation_ids))
    ) == tuple(sorted(expected_early_admitted_ids))
    exclusion_ids = {
        exclusion.observation_id
        for result in (public, hedge)
        for exclusion in result.unmatched_exclusions
    }
    assert expected_early_admitted_ids.isdisjoint(exclusion_ids)
    assert late_only_retro_ids <= exclusion_ids
    assert overlap_ids <= exclusion_ids
    assert public.refusals == ()
    assert hedge.refusals == (
        LineageRefusal("lineage-overlap", "composite:x3-01", "composite"),
    )


def test_lineage_projection_classifies_planted_ambiguous_mapping_without_placeholder() -> None:
    """The planted L8 ambiguity is typed, while canonical-null L8a stays unmatched."""
    from quant_allocator.evidence.fixtures.s7 import build_s7_fixture
    from quant_allocator.evidence.schema import connect, initialize
    from quant_allocator.flagships.track_record_provenance.lineage import (
        build_lineage_from_s7_projections,
    )

    conn = connect()
    initialize(conn)
    manifest = build_s7_fixture(conn)
    planted = {
        str(row["source_key"]): row
        for row in conn.execute(
            "SELECT mapping.source_key,mapping.mapping_status,"
            "mapping.dataset_observation_id,version.dataset_id "
            "FROM entity_mapping mapping "
            "JOIN dataset_version version USING(dataset_version_id) "
            "WHERE version.dataset_id='dataset:s7-hedge-composite' "
            "AND mapping.source_key IN ('s7-hf-ambiguous','s7-null-same-label')"
        )
    }
    ambiguous = planted["s7-hf-ambiguous"]
    canonical_null = planted["s7-null-same-label"]
    assert ambiguous["mapping_status"] == "ambiguous"
    assert canonical_null["mapping_status"] == "unresolved"

    result = build_lineage_from_s7_projections(
        conn, manifest, scenario="hedge-fund", cutoff_name="latest"
    )

    ambiguous_id = str(ambiguous["dataset_observation_id"])
    canonical_null_id = str(canonical_null["dataset_observation_id"])
    assert ambiguous_id != canonical_null_id
    assert {ambiguous_id, canonical_null_id}.isdisjoint(
        result.admitted_observation_ids
    )
    assert all(
        {ambiguous_id, canonical_null_id}.isdisjoint(segment.observation_ids)
        for segment in result.segments
    )
    exclusions = {
        exclusion.observation_id: exclusion
        for exclusion in result.unmatched_exclusions
    }
    assert exclusions[ambiguous_id] == LineageExclusion(
        str(ambiguous["dataset_id"]),
        ambiguous_id,
        "entity-mapping-ambiguous",
    )
    assert exclusions[canonical_null_id] == LineageExclusion(
        str(canonical_null["dataset_id"]),
        canonical_null_id,
        "unmatched",
    )


@pytest.mark.parametrize("cutoff_name", ("early", "latest"))
def test_s7_l9_real_fixture_refuses_overlapping_ownership_paths(
    cutoff_name: str,
) -> None:
    """The named L9 row is fully accounted for and never assigned a winner."""
    from quant_allocator.evidence.fixtures.s7 import build_s7_fixture
    from quant_allocator.evidence.schema import connect, initialize
    from quant_allocator.flagships.track_record_provenance.lineage import (
        build_lineage_from_s7_projections,
    )

    conn = connect()
    initialize(conn)
    manifest = build_s7_fixture(conn)
    overlap = conn.execute(
        "SELECT m.dataset_observation_id,m.canonical_entity_id,v.dataset_id "
        "FROM entity_mapping m JOIN dataset_observation o "
        "USING(dataset_observation_id) JOIN dataset_version v "
        "USING(dataset_version_id) WHERE m.source_key='s7-hf-overlap'"
    ).fetchone()
    assert overlap is not None
    assert overlap["canonical_entity_id"] == "composite:x3-01"

    result = build_lineage_from_s7_projections(
        conn, manifest, scenario="hedge-fund", cutoff_name=cutoff_name
    )
    observation_id = str(overlap["dataset_observation_id"])

    assert observation_id not in result.admitted_observation_ids
    assert all(
        observation_id not in segment.observation_ids for segment in result.segments
    )
    assert LineageExclusion(
        str(overlap["dataset_id"]), observation_id, "lineage-overlap"
    ) in result.unmatched_exclusions
    assert result.refusals == (
        LineageRefusal("lineage-overlap", "composite:x3-01", "composite"),
    )


def test_lineage_membership_selects_latest_known_content_before_historical_validity() -> None:
    """A latest-known membership may end before cutoff and still cover an old observation."""
    from quant_allocator.evidence.fixtures.s7 import build_s7_fixture
    from quant_allocator.evidence.schema import connect, initialize

    conn = connect()
    initialize(conn)
    manifest = build_s7_fixture(conn)
    linked_observation = conn.execute(
        "SELECT mapping.dataset_observation_id FROM entity_mapping mapping "
        "WHERE mapping.source_key='s7-public-main:2024-01'"
    ).fetchone()[0]
    latest_membership = _latest_projected_membership_for_observation(
        conn, linked_observation, "latest"
    )
    conn.execute("DROP TRIGGER immutable_update_universe_membership")
    conn.execute(
        "UPDATE universe_membership SET membership_status='active',temporal_type='interval',"
        "effective_at=NULL,effective_from=?,effective_to=? WHERE universe_membership_id=?",
        (
            "2024-01-01T00:00:00.000000Z",
            "2024-02-01T00:00:00.000000Z",
            latest_membership["universe_membership_id"],
        ),
    )

    from quant_allocator.flagships.track_record_provenance.lineage import (
        build_lineage_from_s7_projections,
    )

    result = build_lineage_from_s7_projections(
        conn, manifest, scenario="public-equity", cutoff_name="latest"
    )

    assert linked_observation in result.admitted_observation_ids


def test_lineage_membership_uses_latest_projected_x3_revision_not_active_parent() -> None:
    """An inactive X3 revision suppresses its S7-linked parent at the latest cutoff."""
    from quant_allocator.evidence.fixtures.s7 import build_s7_fixture
    from quant_allocator.evidence.schema import connect, initialize

    conn = connect()
    initialize(conn)
    manifest = build_s7_fixture(conn)
    linked_observation = conn.execute(
        "SELECT mapping.dataset_observation_id FROM entity_mapping mapping "
        "WHERE mapping.source_key='s7-public-main:2024-01'"
    ).fetchone()[0]
    latest_membership = _latest_projected_membership_for_observation(
        conn, linked_observation, "latest"
    )
    conn.execute("DROP TRIGGER immutable_update_universe_membership")
    conn.execute(
        "UPDATE universe_membership SET membership_status='inactive' "
        "WHERE universe_membership_id=?",
        (latest_membership["universe_membership_id"],),
    )

    from quant_allocator.flagships.track_record_provenance.lineage import (
        build_lineage_from_s7_projections,
    )

    result = build_lineage_from_s7_projections(
        conn, manifest, scenario="public-equity", cutoff_name="latest"
    )

    assert linked_observation not in result.admitted_observation_ids


def test_lineage_membership_refuses_future_started_projected_revision() -> None:
    """The latest active X3 revision must cover the S7 observation interval itself."""
    from quant_allocator.evidence.fixtures.s7 import build_s7_fixture
    from quant_allocator.evidence.schema import connect, initialize

    conn = connect()
    initialize(conn)
    manifest = build_s7_fixture(conn)
    linked_observation = conn.execute(
        "SELECT mapping.dataset_observation_id FROM entity_mapping mapping "
        "WHERE mapping.source_key='s7-public-main:2024-01'"
    ).fetchone()[0]
    latest_membership = _latest_projected_membership_for_observation(
        conn, linked_observation, "early"
    )
    conn.execute("DROP TRIGGER immutable_update_universe_membership")
    conn.execute(
        "UPDATE universe_membership SET membership_status='active',temporal_type='interval',"
        "effective_at=NULL,effective_from=?,effective_to=NULL "
        "WHERE universe_membership_id=?",
        (
            "2024-02-01T00:00:00.000000Z",
            latest_membership["universe_membership_id"],
        ),
    )

    from quant_allocator.flagships.track_record_provenance.lineage import (
        build_lineage_from_s7_projections,
    )

    result = build_lineage_from_s7_projections(
        conn, manifest, scenario="public-equity", cutoff_name="early"
    )

    assert linked_observation not in result.admitted_observation_ids


def test_lineage_projection_refuses_multiple_resolved_mappings_per_observation() -> None:
    """A second resolved S7 root mapping is ambiguity, never a duplicate panel row."""
    from quant_allocator.evidence.fixtures.s7 import build_s7_fixture
    from quant_allocator.evidence.model import machine_id
    from quant_allocator.evidence.schema import connect, initialize
    from quant_allocator.flagships.track_record_provenance.lineage import (
        build_lineage_from_s7_projections,
    )

    conn = connect()
    initialize(conn)
    manifest = build_s7_fixture(conn)
    original = dict(
        conn.execute(
            "SELECT * FROM entity_mapping WHERE source_key='s7-public-main:2024-01'"
        ).fetchone()
    )
    original["source_key"] = "s7-public-main:2024-01:duplicate-resolved"
    original["entity_mapping_id"] = machine_id(
        "mapping",
        {
            key: original[key]
            for key in (
                "source_evidence_item_id",
                "source_key",
                "source_label",
                "taxonomy_version",
                "version",
                "candidate_entity_ids_json",
            )
        },
    )
    columns = tuple(original)
    conn.execute(
        f"INSERT INTO entity_mapping ({','.join(columns)}) "
        f"VALUES ({','.join('?' for _ in columns)})",
        tuple(original[column] for column in columns),
    )

    result = build_lineage_from_s7_projections(
        conn, manifest, scenario="public-equity", cutoff_name="latest"
    )

    observation_id = str(original["dataset_observation_id"])
    assert observation_id not in result.admitted_observation_ids
    assert tuple(
        exclusion
        for exclusion in result.unmatched_exclusions
        if exclusion.observation_id == observation_id
    ) == (
        LineageExclusion(
            str(
                conn.execute(
                    "SELECT dataset_id FROM dataset_version "
                    "WHERE dataset_version_id=?",
                    (original["dataset_version_id"],),
                ).fetchone()[0]
            ),
            observation_id,
            "entity-mapping-ambiguous",
        ),
    )


def test_lineage_projection_excludes_snapshot_observation_without_mapping() -> None:
    """A visible source observation with zero mapping roots remains a typed exclusion."""
    from quant_allocator.evidence.fixtures.s7 import build_s7_fixture
    from quant_allocator.evidence.schema import connect, initialize
    from quant_allocator.flagships.track_record_provenance.lineage import (
        build_lineage_from_s7_projections,
    )

    conn = connect()
    initialize(conn)
    manifest = build_s7_fixture(conn)
    mapping = conn.execute(
        "SELECT mapping.entity_mapping_id,mapping.dataset_observation_id,"
        "version.dataset_id FROM entity_mapping mapping "
        "JOIN dataset_version version USING(dataset_version_id) "
        "WHERE mapping.source_key='s7-public-main:2024-01'"
    ).fetchone()
    conn.execute("DROP TRIGGER immutable_delete_entity_mapping")
    conn.execute(
        "DELETE FROM entity_mapping WHERE entity_mapping_id=?",
        (mapping["entity_mapping_id"],),
    )

    result = build_lineage_from_s7_projections(
        conn, manifest, scenario="public-equity", cutoff_name="latest"
    )

    observation_id = str(mapping["dataset_observation_id"])
    assert observation_id not in result.admitted_observation_ids
    assert tuple(
        exclusion
        for exclusion in result.unmatched_exclusions
        if exclusion.observation_id == observation_id
    ) == (
        LineageExclusion(
            str(mapping["dataset_id"]),
            observation_id,
            "entity-mapping-unresolved",
        ),
    )


def test_lineage_projection_preserves_multiple_links_to_one_latest_membership() -> None:
    """Multiple links resolving to one latest membership remain explicit provenance."""
    from quant_allocator.evidence.fixtures.s7 import build_s7_fixture
    from quant_allocator.evidence.model import machine_id
    from quant_allocator.evidence.schema import connect, initialize
    from quant_allocator.flagships.track_record_provenance.lineage import (
        build_lineage_from_s7_projections,
    )

    conn = connect()
    initialize(conn)
    manifest = build_s7_fixture(conn)
    linked_observation = conn.execute(
        "SELECT mapping.dataset_observation_id FROM entity_mapping mapping "
        "WHERE mapping.source_key='s7-public-main:2024-01'"
    ).fetchone()[0]
    existing_membership_id = conn.execute(
        "SELECT universe_membership_id FROM observation_membership_link "
        "WHERE dataset_observation_id=?",
        (linked_observation,),
    ).fetchone()[0]
    alternative_membership_id = conn.execute(
        "SELECT membership.universe_membership_id FROM universe_membership membership "
        "JOIN entity_mapping mapping USING(entity_mapping_id) "
        "JOIN evidence_item item "
        "ON item.evidence_item_id=membership.source_evidence_item_id "
        "JOIN source_record source USING(source_record_id) "
        "WHERE source.dataset_id='dataset:x3-registered-fund' "
        "AND mapping.canonical_entity_id='vehicle:x3-00' "
        "AND membership.membership_status='active' "
        "AND membership.universe_membership_id<>? "
        "ORDER BY membership.universe_membership_id LIMIT 1",
        (existing_membership_id,),
    ).fetchone()[0]
    link_id = machine_id(
        "observation-membership",
        {
            "dataset_observation_id": linked_observation,
            "universe_membership_id": alternative_membership_id,
        },
    )
    conn.execute(
        "INSERT INTO observation_membership_link VALUES (?,?,?)",
        (link_id, linked_observation, alternative_membership_id),
    )

    result = build_lineage_from_s7_projections(
        conn, manifest, scenario="public-equity", cutoff_name="latest"
    )

    assert linked_observation in result.admitted_observation_ids
    segment = next(
        segment
        for segment in result.segments
        if linked_observation in segment.observation_ids
    )
    assert {
        link_id,
        conn.execute(
            "SELECT observation_membership_link_id "
            "FROM observation_membership_link "
            "WHERE dataset_observation_id=? AND universe_membership_id=?",
            (linked_observation, existing_membership_id),
        ).fetchone()[0],
    } <= set(segment.observation_membership_link_ids)
    assert {existing_membership_id, alternative_membership_id} <= set(
        segment.membership_ids
    )


@pytest.mark.parametrize(
    ("scenario", "expected_observations", "expected_bounds"),
    (
        ("public-equity", 7, (date(2024, 1, 31), date(2024, 3, 31))),
        ("credit", 2, (date(2024, 2, 29), date(2024, 3, 31))),
    ),
)
def test_lineage_projection_keeps_native_point_observations_in_segments(
    scenario: str,
    expected_observations: int,
    expected_bounds: tuple[date, date],
) -> None:
    """Monthly/native points form an extent without invented one-day gap intervals."""
    from quant_allocator.evidence.fixtures.s7 import build_s7_fixture
    from quant_allocator.evidence.schema import connect, initialize
    from quant_allocator.flagships.track_record_provenance.lineage import (
        build_lineage_from_s7_projections,
    )

    conn = connect()
    initialize(conn)
    manifest = build_s7_fixture(conn)

    result = build_lineage_from_s7_projections(
        conn, manifest, scenario=scenario, cutoff_name="latest"
    )

    assert len(result.admitted_observation_ids) == expected_observations
    assert len(result.segments) == 1
    assert result.refusals == ()
    assert (
        result.segments[0].effective_from,
        result.segments[0].effective_to,
    ) == expected_bounds
    assert len(result.segments[0].observation_ids) == expected_observations


def test_lineage_projection_accepts_supported_real_x3_entity_path() -> None:
    """The reviewed manager-to-vehicle graph supports historical public observations."""
    from quant_allocator.evidence.fixtures.s7 import build_s7_fixture
    from quant_allocator.evidence.schema import connect, initialize
    from quant_allocator.flagships.track_record_provenance.lineage import (
        build_lineage_from_s7_projections,
    )

    conn = connect()
    initialize(conn)
    manifest = build_s7_fixture(conn)

    result = build_lineage_from_s7_projections(
        conn, manifest, scenario="public-equity", cutoff_name="latest"
    )

    assert result.admitted_observation_ids
    assert all(
        refusal.reason_code != "lineage-relationship-missing"
        for refusal in result.refusals
    )


@pytest.mark.parametrize(
    ("relation_type", "source_entity_id", "target_entity_id"),
    (
        ("implemented_by", "composite:x3-00", "vehicle:x3-00"),
        ("advised_by", "manager:x3-00", "adviser:x3-00"),
        ("legal_identity", "adviser:x3-00", "legal-entity:x3-00"),
    ),
)
def test_lineage_projection_refuses_missing_real_x3_entity_path(
    monkeypatch: pytest.MonkeyPatch,
    relation_type: str,
    source_entity_id: str,
    target_entity_id: str,
) -> None:
    """Deleting any required effective X3 edge refuses the entity path deterministically."""
    from quant_allocator.evidence.fixtures import x3 as x3_fixture
    from quant_allocator.evidence.fixtures.s7 import build_s7_fixture
    from quant_allocator.evidence.fixtures.x3 import build_x3_fixture
    from quant_allocator.evidence.schema import connect, initialize
    from quant_allocator.flagships.track_record_provenance.lineage import (
        build_lineage_from_s7_projections,
    )

    conn = connect()
    initialize(conn)
    manifest = build_s7_fixture(conn)
    x3_manifest = build_x3_fixture(conn)
    baseline = build_lineage_from_s7_projections(
        conn, manifest, scenario="public-equity", cutoff_name="latest"
    )
    assert baseline.admitted_observation_ids
    assert all(
        refusal.reason_code != "lineage-relationship-missing"
        for refusal in baseline.refusals
    )

    monkeypatch.setattr(x3_fixture, "build_x3_fixture", lambda _conn: x3_manifest)
    conn.execute("DROP TRIGGER immutable_delete_entity_relationship")
    conn.execute(
        "DELETE FROM entity_relationship WHERE relation_type=? AND source_entity_id=? "
        "AND target_entity_id=?",
        (relation_type, source_entity_id, target_entity_id),
    )

    result = build_lineage_from_s7_projections(
        conn, manifest, scenario="public-equity", cutoff_name="latest"
    )

    assert result.refusals == (
        LineageRefusal("lineage-relationship-missing", "vehicle:x3-00", "vehicle"),
    )


@pytest.mark.parametrize(
    ("rows", "reason_code"),
    (
        (
            (
                _lineage_row(
                    "observation:s7-gap-left",
                    effective_from=date(2024, 1, 1),
                    effective_to=date(2024, 2, 1),
                    value=Decimal("0.0100"),
                ),
                _lineage_row(
                    "observation:s7-gap-right",
                    effective_from=date(2024, 2, 2),
                    effective_to=date(2024, 3, 1),
                    value=Decimal("0.0200"),
                ),
            ),
            "lineage-gap",
        ),
        (
            (
                _lineage_row(
                    "observation:s7-overlap-left",
                    effective_from=date(2024, 1, 1),
                    effective_to=date(2024, 3, 1),
                    value=Decimal("0.0100"),
                ),
                _lineage_row(
                    "observation:s7-overlap-right",
                    effective_from=date(2024, 2, 1),
                    effective_to=date(2024, 4, 1),
                    value=Decimal("0.0200"),
                ),
            ),
            "lineage-overlap",
        ),
    ),
)
def test_lineage_segments_refuse_single_grain_gaps_and_overlaps(
    rows: tuple[dict[str, object], ...], reason_code: str
) -> None:
    """A single canonical vehicle grain cannot choose an owner across a discontinuity."""
    result = build_lineage_segments(rows)

    assert _segment_summary(result) == ()
    assert tuple(
        (refusal.reason_code, refusal.canonical_entity_id, refusal.entity_grain)
        for refusal in result.refusals
    ) == ((reason_code, "vehicle:s7-boundary", "vehicle"),)
