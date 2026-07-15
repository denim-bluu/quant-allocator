"""Minimal S7 lineage admission boundary over already-projected rows."""

from __future__ import annotations

import sqlite3
from collections import Counter
from dataclasses import dataclass
from datetime import date
from typing import Mapping, NamedTuple

from quant_allocator.evidence.model import digest_id


class LineageExclusion(NamedTuple):
    """A one-source observation that cannot enter an admitted lineage segment."""

    dataset_id: str
    observation_id: str
    reason_code: str


class LineageSegment(NamedTuple):
    """A deterministic contiguous interval at one canonical entity grain."""

    segment_id: str
    canonical_entity_id: str
    entity_grain: str
    effective_from: date
    effective_to: date
    observation_ids: tuple[str, ...]
    mapping_ids: tuple[str, ...]
    observation_membership_link_ids: tuple[str, ...]
    membership_ids: tuple[str, ...]
    relationship_ids: tuple[str, ...]


class LineageRefusal(NamedTuple):
    """A controlled failure to assign rows to a one-owner lineage segment."""

    reason_code: str
    canonical_entity_id: str
    entity_grain: str


@dataclass(frozen=True, slots=True)
class LineageAdmissionResult:
    """Segment-owned rows plus typed exclusions and lineage refusals."""

    admitted_observation_ids: tuple[str, ...]
    unmatched_exclusions: tuple[LineageExclusion, ...]
    segments: tuple[LineageSegment, ...] = ()
    refusals: tuple[LineageRefusal, ...] = ()


def _relationship_covers_row(
    relationship: Mapping[str, object],
    row: Mapping[str, object],
) -> bool:
    """Return whether one effective-dated relationship covers the row's native time."""
    if relationship.get("temporal_type") != "interval":
        return False
    relationship_from = _point_date(relationship.get("effective_from"))
    relationship_to = _point_date(relationship.get("effective_to"))
    effective_from = row.get("effective_from")
    effective_to = row.get("effective_to")
    if not isinstance(effective_from, date) or not isinstance(effective_to, date):
        return False
    if row.get("temporal_type") == "point":
        return relationship_from is not None and relationship_from <= effective_from and (
            relationship_to is None or effective_from < relationship_to
        )
    return (
        row.get("temporal_type") == "interval"
        and relationship_from is not None
        and relationship_from <= effective_from
        and (relationship_to is None or effective_to <= relationship_to)
    )


def _edge_identity(edge: Mapping[str, object]) -> tuple[object, ...]:
    identifier = edge.get("entity_relationship_id")
    if isinstance(identifier, str) and identifier:
        return (identifier,)
    return ()


def _entity_paths_for_row(
    row: Mapping[str, object],
    canonical_entity_id: str,
    entity_grain: str,
) -> tuple[tuple[tuple[object, ...], ...], ...]:
    """Resolve complete effective X3 manager/product/adviser/legal paths for one row."""
    relationship_graph = row.get("relationship_graph")
    if not isinstance(relationship_graph, tuple):
        return ()
    edges = tuple(
        edge
        for edge in relationship_graph
        if isinstance(edge, Mapping)
        and _relationship_covers_row(edge, row)
    )

    product_paths: list[tuple[str, tuple[Mapping[str, object], ...]]] = []
    if entity_grain == "strategy":
        product_paths.append((canonical_entity_id, ()))
    elif entity_grain == "composite":
        product_paths.extend(
            (str(edge["source_entity_id"]), (edge,))
            for edge in edges
            if edge.get("relation_type") == "reported_through"
            and edge.get("target_entity_id") == canonical_entity_id
            and isinstance(edge.get("source_entity_id"), str)
        )
    elif entity_grain == "vehicle":
        for implementation in edges:
            if not (
                implementation.get("relation_type") == "implemented_by"
                and implementation.get("target_entity_id") == canonical_entity_id
                and isinstance(implementation.get("source_entity_id"), str)
            ):
                continue
            composite_id = str(implementation["source_entity_id"])
            product_paths.extend(
                (str(reporting["source_entity_id"]), (reporting, implementation))
                for reporting in edges
                if reporting.get("relation_type") == "reported_through"
                and reporting.get("target_entity_id") == composite_id
                and isinstance(reporting.get("source_entity_id"), str)
            )
    else:
        return ()

    complete_paths: set[tuple[tuple[object, ...], ...]] = set()
    for strategy_id, product_edges in product_paths:
        for offering in edges:
            if not (
                offering.get("relation_type") == "offers"
                and offering.get("target_entity_id") == strategy_id
                and isinstance(offering.get("source_entity_id"), str)
            ):
                continue
            manager_id = str(offering["source_entity_id"])
            for advice in edges:
                if not (
                    advice.get("relation_type") == "advised_by"
                    and advice.get("source_entity_id") == manager_id
                    and isinstance(advice.get("target_entity_id"), str)
                ):
                    continue
                adviser_id = str(advice["target_entity_id"])
                for legal in edges:
                    if (
                        legal.get("relation_type") == "legal_identity"
                        and legal.get("source_entity_id") == adviser_id
                        and isinstance(legal.get("target_entity_id"), str)
                    ):
                        path_edges = (offering, *product_edges, advice, legal)
                        path = tuple(_edge_identity(edge) for edge in path_edges)
                        if all(path):
                            complete_paths.add(path)
    return tuple(sorted(complete_paths, key=repr))


def _relationship_ids(
    path: tuple[tuple[object, ...], ...],
) -> tuple[str, ...]:
    """Expose exact shared relationship IDs without card-local substitutes."""
    if any(
        len(edge) != 1 or not isinstance(edge[0], str) or not edge[0]
        for edge in path
    ):
        raise ValueError("s7-lineage-relationship-identity-invalid")
    return tuple(str(edge[0]) for edge in path)


def _row_reference_ids(
    row: Mapping[str, object], plural_key: str, singular_key: str
) -> tuple[str, ...]:
    values = row.get(plural_key)
    if values is not None:
        if (
            isinstance(values, tuple)
            and values
            and all(isinstance(value, str) and bool(value) for value in values)
        ):
            return values
        return ()
    value = row.get(singular_key)
    return (value,) if isinstance(value, str) and value else ()


def _segment_from_rows(
    rows: list[Mapping[str, object]],
    *,
    canonical_entity_id: str,
    entity_grain: str,
    path: tuple[tuple[object, ...], ...],
) -> LineageSegment:
    """Build one path-stable segment and bind all projection references into its ID."""
    observation_ids = tuple(str(row["observation_id"]) for row in rows)
    mapping_ids = tuple(
        sorted(
            {
                identifier
                for row in rows
                for identifier in _row_reference_ids(row, "mapping_ids", "mapping_id")
            }
        )
    )
    observation_membership_link_ids = tuple(
        sorted(
            {
                identifier
                for row in rows
                for identifier in _row_reference_ids(
                    row,
                    "observation_membership_link_ids",
                    "observation_membership_link_id",
                )
            }
        )
    )
    membership_ids = tuple(
        sorted(
            {
                identifier
                for row in rows
                for identifier in _row_reference_ids(
                    row, "membership_ids", "membership_id"
                )
            }
        )
    )
    relationship_ids = _relationship_ids(path)
    effective_from = rows[0]["effective_from"]
    effective_to = (
        rows[-1]["effective_from"]
        if rows[0].get("temporal_type") == "point"
        else rows[-1]["effective_to"]
    )
    if not isinstance(effective_from, date) or not isinstance(effective_to, date):
        raise ValueError("s7-lineage-temporal-boundary-invalid")
    identity = {
        "canonical_entity_id": canonical_entity_id,
        "entity_grain": entity_grain,
        "effective_from": effective_from,
        "effective_to": effective_to,
        "observation_ids": observation_ids,
        "mapping_ids": mapping_ids,
        "observation_membership_link_ids": observation_membership_link_ids,
        "membership_ids": membership_ids,
        "relationship_ids": relationship_ids,
    }
    return LineageSegment(
        digest_id("lineage-segment", identity),
        canonical_entity_id,
        entity_grain,
        effective_from,
        effective_to,
        observation_ids,
        mapping_ids,
        observation_membership_link_ids,
        membership_ids,
        relationship_ids,
    )


def _segment_rows(
    rows: list[Mapping[str, object]],
) -> tuple[
    tuple[LineageSegment, ...],
    tuple[LineageRefusal, ...],
    tuple[LineageExclusion, ...],
]:
    grouped: dict[str, list[Mapping[str, object]]] = {}
    for row in rows:
        canonical_entity_id = row.get("canonical_entity_id")
        entity_grain = row.get("entity_grain")
        effective_from = row.get("effective_from")
        effective_to = row.get("effective_to")
        if not (
            isinstance(canonical_entity_id, str)
            and isinstance(entity_grain, str)
            and isinstance(effective_from, date)
            and isinstance(effective_to, date)
        ):
            continue
        grouped.setdefault(canonical_entity_id, []).append(row)

    segments: list[LineageSegment] = []
    refusals: list[LineageRefusal] = []
    exclusions: list[LineageExclusion] = []
    for canonical_entity_id, group in sorted(grouped.items()):
        entity_grains = {str(row["entity_grain"]) for row in group}
        if len(entity_grains) != 1:
            refusals.append(
                LineageRefusal(
                    "entity-grain-mismatch",
                    canonical_entity_id,
                    "|".join(sorted(entity_grains)),
                )
            )
            continue
        entity_grain = entity_grains.pop()
        ordered = sorted(
            group,
            key=lambda row: (
                row["effective_from"],
                row["effective_to"],
                row["observation_id"],
            ),
        )
        row_paths = tuple(
            _entity_paths_for_row(row, canonical_entity_id, entity_grain)
            for row in ordered
        )
        if not row_paths or any(len(paths) == 0 for paths in row_paths):
            refusals.append(
                LineageRefusal(
                    "lineage-relationship-missing", canonical_entity_id, entity_grain
                )
            )
            continue
        if any(len(paths) > 1 for paths in row_paths):
            refusals.append(
                LineageRefusal("lineage-overlap", canonical_entity_id, entity_grain)
            )
            exclusions.extend(
                LineageExclusion(
                    str(row["dataset_id"]),
                    str(row["observation_id"]),
                    "lineage-overlap",
                )
                for row in ordered
            )
            continue

        temporal_types = {row.get("temporal_type", "interval") for row in ordered}
        boundary_reason: str | None = None
        if len(temporal_types) != 1 or not temporal_types <= {"point", "interval"}:
            boundary_reason = "lineage-overlap"
        temporal_type = next(iter(temporal_types)) if len(temporal_types) == 1 else None
        for row in ordered:
            effective_from = row["effective_from"]
            effective_to = row["effective_to"]
            if not isinstance(effective_from, date) or not isinstance(effective_to, date):
                raise ValueError("s7-lineage-temporal-boundary-invalid")
            if temporal_type == "interval" and effective_from >= effective_to:
                boundary_reason = "lineage-invalid-interval"
                break
            if temporal_type == "point" and effective_from != effective_to:
                boundary_reason = "lineage-invalid-interval"
                break
        if boundary_reason is None and temporal_type == "interval":
            previous_to = ordered[0]["effective_to"]
            for row in ordered[1:]:
                effective_from = row["effective_from"]
                effective_to = row["effective_to"]
                if effective_from > previous_to:
                    boundary_reason = "lineage-gap"
                    break
                if effective_from < previous_to:
                    boundary_reason = "lineage-overlap"
                    break
                previous_to = effective_to
        if boundary_reason is None and temporal_type == "point":
            for index, row in enumerate(ordered[1:], start=1):
                if (
                    row["effective_from"] == ordered[index - 1]["effective_from"]
                    and row_paths[index][0] != row_paths[index - 1][0]
                ):
                    boundary_reason = "lineage-overlap"
                    break
        if boundary_reason is not None:
            refusals.append(
                LineageRefusal(boundary_reason, canonical_entity_id, entity_grain)
            )
            if boundary_reason == "lineage-overlap":
                exclusions.extend(
                    LineageExclusion(
                        str(row["dataset_id"]),
                        str(row["observation_id"]),
                        boundary_reason,
                    )
                    for row in ordered
                )
            continue

        current_rows = [ordered[0]]
        current_path = row_paths[0][0]
        for row, paths in zip(ordered[1:], row_paths[1:], strict=True):
            if paths[0] != current_path:
                segments.append(
                    _segment_from_rows(
                        current_rows,
                        canonical_entity_id=canonical_entity_id,
                        entity_grain=entity_grain,
                        path=current_path,
                    )
                )
                current_rows = [row]
                current_path = paths[0]
            else:
                current_rows.append(row)
        segments.append(
            _segment_from_rows(
                current_rows,
                canonical_entity_id=canonical_entity_id,
                entity_grain=entity_grain,
                path=current_path,
            )
        )
    return tuple(segments), tuple(refusals), tuple(exclusions)


def build_lineage_segments(
    rows: tuple[Mapping[str, object], ...],
) -> LineageAdmissionResult:
    """Admit only resolved, effectively X3-member rows without joining labels."""
    admitted_rows: list[Mapping[str, object]] = []
    unmatched: list[LineageExclusion] = []
    observation_counts = Counter(
        row.get("observation_id")
        for row in rows
        if isinstance(row.get("observation_id"), str)
    )
    duplicate_observations: set[str] = set()
    for row in rows:
        dataset_id = row["dataset_id"]
        observation_id = row["observation_id"]
        if not isinstance(dataset_id, str) or not isinstance(observation_id, str):
            raise ValueError("s7-lineage-row-identity-invalid")
        if observation_counts[observation_id] > 1:
            if observation_id not in duplicate_observations:
                unmatched.append(
                    LineageExclusion(
                        dataset_id, observation_id, "entity-mapping-ambiguous"
                    )
                )
                duplicate_observations.add(observation_id)
            continue
        if (
            row.get("mapping_status") == "resolved"
            and isinstance(row.get("canonical_entity_id"), str)
            and row.get("x3_membership_effective") is True
        ):
            mapping_ids = _row_reference_ids(row, "mapping_ids", "mapping_id")
            link_ids = _row_reference_ids(
                row,
                "observation_membership_link_ids",
                "observation_membership_link_id",
            )
            membership_ids = _row_reference_ids(
                row, "membership_ids", "membership_id"
            )
            if not (
                isinstance(row.get("entity_grain"), str)
                and row.get("temporal_type") in {"point", "interval"}
                and isinstance(row.get("effective_from"), date)
                and isinstance(row.get("effective_to"), date)
                and isinstance(row.get("relationship_graph"), tuple)
                and len(set(mapping_ids)) >= 2
                and link_ids
                and membership_ids
            ):
                unmatched.append(
                    LineageExclusion(dataset_id, observation_id, "receipt-incomplete")
                )
            else:
                admitted_rows.append(row)
        else:
            reason_code = row.get("lineage_exclusion_reason", "unmatched")
            unmatched.append(
                LineageExclusion(
                    dataset_id,
                    observation_id,
                    reason_code if isinstance(reason_code, str) else "unmatched",
                )
            )
    segments, refusals, segment_exclusions = _segment_rows(admitted_rows)
    unmatched.extend(segment_exclusions)
    admitted = tuple(
        observation_id
        for segment in segments
        for observation_id in segment.observation_ids
    )
    if len(admitted) != len(set(admitted)):
        raise ValueError("s7-lineage-observation-reconciliation-invalid")
    return LineageAdmissionResult(admitted, tuple(unmatched), segments, refusals)


_X3_MEMBERSHIP_DATASETS = {
    "vehicle": "dataset:x3-registered-fund",
    "composite": "dataset:x3-strategy-export",
    "strategy": "dataset:x3-rfi-ddq",
}


def _point_date(value: object) -> date | None:
    if not isinstance(value, str):
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def _effective_bounds(snapshot_row: Mapping[str, object]) -> tuple[date, date] | None:
    """Translate projected UTC time without inventing duration for native points."""
    if snapshot_row.get("temporal_type") == "interval":
        start = _point_date(snapshot_row.get("effective_from"))
        end = _point_date(snapshot_row.get("effective_to"))
        return (start, end) if start is not None and end is not None else None
    if snapshot_row.get("temporal_type") == "point":
        instant = _point_date(snapshot_row.get("effective_at"))
        return (instant, instant) if instant is not None else None
    return None


def _membership_covers_observation(
    membership: Mapping[str, object], snapshot_row: Mapping[str, object]
) -> bool:
    """Require an active membership to cover the observation's effective time."""
    observation_type = snapshot_row.get("temporal_type")
    if observation_type == "point":
        observation_at = snapshot_row.get("effective_at")
        if not isinstance(observation_at, str):
            return False
        if membership.get("temporal_type") == "point":
            return membership.get("effective_at") == observation_at
        membership_from = membership.get("effective_from")
        membership_to = membership.get("effective_to")
        return (
            isinstance(membership_from, str)
            and membership_from <= observation_at
            and (membership_to is None or observation_at < membership_to)
        )
    if observation_type == "interval":
        observation_from = snapshot_row.get("effective_from")
        observation_to = snapshot_row.get("effective_to")
        membership_from = membership.get("effective_from")
        membership_to = membership.get("effective_to")
        return (
            membership.get("temporal_type") == "interval"
            and isinstance(observation_from, str)
            and isinstance(observation_to, str)
            and isinstance(membership_from, str)
            and membership_from <= observation_from
            and (membership_to is None or observation_to <= membership_to)
        )
    return False


def _latest_projection_by_ancestor(
    latest_rows: tuple[Mapping[str, object], ...],
    all_known_rows: tuple[Mapping[str, object], ...],
    *,
    identifier_key: str,
) -> dict[str, Mapping[str, object]]:
    """Index each visible revision-chain identity to its latest-known projected row."""
    all_known_by_id = {
        str(row[identifier_key]): row
        for row in all_known_rows
        if isinstance(row.get(identifier_key), str)
    }
    indexed: dict[str, Mapping[str, object]] = {}
    for latest in latest_rows:
        latest_id = latest.get(identifier_key)
        if not isinstance(latest_id, str):
            continue
        indexed[latest_id] = latest
        parent_id = latest.get("revision_of")
        seen = {latest_id}
        while isinstance(parent_id, str) and parent_id not in seen:
            indexed[parent_id] = latest
            seen.add(parent_id)
            parent = all_known_by_id.get(parent_id)
            parent_id = parent.get("revision_of") if parent is not None else None
    return indexed


def build_lineage_from_s7_projections(
    conn: sqlite3.Connection,
    manifest: object,
    *,
    scenario: str,
    cutoff_name: str,
) -> LineageAdmissionResult:
    """Derive S7 admission rows from its reviewed fixture snapshot projections."""
    from quant_allocator.evidence.fixtures.s7 import S7_CUTOFFS, s7_source_requests
    from quant_allocator.evidence.fixtures.x3 import build_x3_fixture
    from quant_allocator.evidence.model import DatasetSliceRequest, SnapshotBundleRequest
    from quant_allocator.evidence.projections import (
        project_entity_mappings,
        project_entity_relationships,
        project_universe_memberships,
    )
    from quant_allocator.evidence.snapshot import as_known_bundle, as_known_slice

    requests = s7_source_requests(
        manifest,
        scenario=scenario,
        cutoff_name=cutoff_name,
        revision_mode="latest-known",
    )
    bundle = as_known_bundle(
        conn,
        SnapshotBundleRequest(
            S7_CUTOFFS[cutoff_name],
            requests,
            ("field_dictionary_version",),
            "s7-track-lineage-v1",
        ),
    )
    cutoff = S7_CUTOFFS[cutoff_name]
    s7_relationships = tuple(
        relationship
        for snapshot_slice in bundle.slices
        for relationship in project_entity_relationships(conn, snapshot_slice)
    )
    x3_manifest = build_x3_fixture(conn)
    relationship_dataset_id = "dataset:x3-public-adviser"
    relationship_slice = as_known_slice(
        conn,
        decision_at=cutoff,
        request=DatasetSliceRequest(
            relationship_dataset_id,
            x3_manifest.access_contexts[relationship_dataset_id],
            x3_manifest.right_ids[relationship_dataset_id],
            "x3-research",
            revision_mode="latest-known",
        ),
    )
    relationship_graph = tuple(
        sorted(
            (*project_entity_relationships(conn, relationship_slice), *s7_relationships),
            key=lambda relationship: str(relationship["entity_relationship_id"]),
        )
    )
    linked_memberships: dict[str, list[tuple[str, str, str]]] = {}
    for linked_row in conn.execute(
        "SELECT link.observation_membership_link_id,link.dataset_observation_id,"
        "link.universe_membership_id,membership.entity_mapping_id "
        "FROM observation_membership_link link "
        "JOIN universe_membership membership USING(universe_membership_id) "
        "ORDER BY link.dataset_observation_id,link.observation_membership_link_id"
    ):
        linked_memberships.setdefault(
            str(linked_row["dataset_observation_id"]), []
        ).append(
            (
                str(linked_row["observation_membership_link_id"]),
                str(linked_row["universe_membership_id"]),
                str(linked_row["entity_mapping_id"]),
            )
        )
    x3_memberships_by_linked_id: dict[str, Mapping[str, object]] = {}
    x3_mappings_by_linked_id: dict[str, Mapping[str, object]] = {}
    for entity_grain, dataset_id in _X3_MEMBERSHIP_DATASETS.items():
        request_kwargs = {
            "dataset_id": dataset_id,
            "access_context": x3_manifest.access_contexts[dataset_id],
            "evidence_right_id": x3_manifest.right_ids[dataset_id],
            "licence_purpose": "x3-research",
        }
        x3_slice = as_known_slice(
            conn,
            decision_at=cutoff,
            request=DatasetSliceRequest(
                **request_kwargs,
                revision_mode="latest-known",
            ),
        )
        all_known_slice = as_known_slice(
            conn,
            decision_at=cutoff,
            request=DatasetSliceRequest(
                **request_kwargs,
                revision_mode="all-known-versions",
            ),
        )
        latest_memberships = project_universe_memberships(conn, x3_slice)
        all_known_memberships = project_universe_memberships(conn, all_known_slice)
        latest_mappings = project_entity_mappings(conn, x3_slice)
        all_known_mappings = project_entity_mappings(conn, all_known_slice)
        latest_mappings_by_ancestor = _latest_projection_by_ancestor(
            latest_mappings,
            all_known_mappings,
            identifier_key="entity_mapping_id",
        )
        x3_mappings_by_linked_id.update(latest_mappings_by_ancestor)
        latest_memberships_by_mapping_id = {
            str(membership["entity_mapping_id"]): membership
            for membership in latest_memberships
        }
        x3_memberships_by_linked_id.update(
            _latest_projection_by_ancestor(
                latest_memberships,
                all_known_memberships,
                identifier_key="universe_membership_id",
            )
        )
        for membership in all_known_memberships:
            membership_id = membership.get("universe_membership_id")
            entity_mapping_id = membership.get("entity_mapping_id")
            if not (
                isinstance(membership_id, str) and isinstance(entity_mapping_id, str)
            ):
                continue
            latest_mapping = latest_mappings_by_ancestor.get(entity_mapping_id)
            if latest_mapping is None:
                continue
            latest_membership = latest_memberships_by_mapping_id.get(
                str(latest_mapping["entity_mapping_id"])
            )
            if latest_membership is not None:
                x3_memberships_by_linked_id[membership_id] = latest_membership

    rows: list[Mapping[str, object]] = []
    for snapshot_slice in bundle.slices:
        snapshot_rows = {
            str(snapshot_row["dataset_observation_id"]): snapshot_row
            for snapshot_row in snapshot_slice.rows
        }
        mappings_by_observation: dict[str, list[Mapping[str, object]]] = {}
        for projected_mapping in project_entity_mappings(conn, snapshot_slice):
            projected_observation_id = projected_mapping.get("dataset_observation_id")
            if isinstance(projected_observation_id, str):
                mappings_by_observation.setdefault(projected_observation_id, []).append(
                    projected_mapping
                )
        for observation_id in sorted(snapshot_rows):
            observation_mappings = tuple(mappings_by_observation.get(observation_id, ()))
            resolved_mappings = tuple(
                mapping
                for mapping in observation_mappings
                if mapping.get("mapping_status") == "resolved"
                and isinstance(mapping.get("canonical_entity_id"), str)
            )
            if len(resolved_mappings) != 1:
                mapping_is_ambiguous = len(resolved_mappings) > 1 or any(
                    mapping.get("mapping_status") == "ambiguous"
                    for mapping in observation_mappings
                )
                rows.append(
                    {
                        "dataset_id": snapshot_slice.request.dataset_id,
                        "observation_id": observation_id,
                        "mapping_status": (
                            "ambiguous" if mapping_is_ambiguous else "unresolved"
                        ),
                        "canonical_entity_id": None,
                        "x3_membership_effective": False,
                        "lineage_exclusion_reason": (
                            "entity-mapping-ambiguous"
                            if mapping_is_ambiguous
                            else (
                                "entity-mapping-unresolved"
                                if not observation_mappings
                                else "unmatched"
                            )
                        ),
                    }
                )
                continue
            mapping = resolved_mappings[0]
            canonical_entity_id = mapping.get("canonical_entity_id")
            entity_grain = (
                canonical_entity_id.split(":", 1)[0]
                if isinstance(canonical_entity_id, str)
                else "product"
            )
            links = tuple(linked_memberships.get(observation_id, ()))
            bounds = snapshot_rows.get(observation_id)
            candidates: list[
                tuple[
                    str,
                    str,
                    str,
                    Mapping[str, object],
                    Mapping[str, object],
                ]
            ] = []
            for link_id, linked_membership_id, linked_mapping_id in links:
                projected_membership = x3_memberships_by_linked_id.get(
                    linked_membership_id
                )
                projected_mapping = (
                    x3_mappings_by_linked_id.get(
                        str(projected_membership["entity_mapping_id"])
                    )
                    if projected_membership is not None
                    else None
                )
                if (
                    projected_membership is not None
                    and projected_membership.get("membership_status") == "active"
                    and projected_mapping is not None
                    and projected_mapping.get("mapping_status") == "resolved"
                    and projected_mapping.get("canonical_entity_id")
                    == canonical_entity_id
                    and bounds is not None
                    and _membership_covers_observation(projected_membership, bounds)
                ):
                    candidates.append(
                        (
                            link_id,
                            linked_membership_id,
                            linked_mapping_id,
                            projected_membership,
                            projected_mapping,
                        )
                    )
            candidate_identities = {
                (
                    str(projected_membership["universe_membership_id"]),
                    str(projected_mapping["entity_mapping_id"]),
                )
                for _, _, _, projected_membership, projected_mapping in candidates
            }
            membership_effective = (
                bool(links)
                and len(candidates) == len(links)
                and len(candidate_identities) == 1
            )
            row: dict[str, object] = {
                "dataset_id": snapshot_slice.request.dataset_id,
                "observation_id": observation_id,
                "mapping_status": mapping.get("mapping_status"),
                "canonical_entity_id": canonical_entity_id,
                "entity_grain": entity_grain,
                "x3_membership_effective": membership_effective,
                "mapping_ids": (mapping.get("entity_mapping_id"),),
                "relationship_graph": relationship_graph,
            }
            if bounds is not None:
                row["temporal_type"] = bounds.get("temporal_type")
                effective_bounds = _effective_bounds(bounds)
                if effective_bounds is not None:
                    row["effective_from"], row["effective_to"] = effective_bounds
            if membership_effective:
                _, _, _, projected_membership, projected_mapping = candidates[0]
                row["mapping_ids"] = tuple(
                    sorted(
                        {
                            str(mapping["entity_mapping_id"]),
                            str(projected_mapping["entity_mapping_id"]),
                            *(
                                linked_mapping_id
                                for _, _, linked_mapping_id, _, _ in candidates
                            ),
                        }
                    )
                )
                row["observation_membership_link_ids"] = tuple(
                    sorted(link_id for link_id, _, _, _, _ in candidates)
                )
                row["membership_ids"] = tuple(
                    sorted(
                        {
                            str(projected_membership["universe_membership_id"]),
                            *(
                                linked_membership_id
                                for _, linked_membership_id, _, _, _ in candidates
                            ),
                        }
                    )
                )
            rows.append(row)
    return build_lineage_segments(tuple(rows))
