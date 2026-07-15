"""Deterministic X3 exhibit built only from reviewed shared evidence projections."""

from __future__ import annotations

import json
from dataclasses import asdict
from functools import lru_cache
from itertools import product
from pathlib import Path

from quant_allocator.demo_data._emit import SITE_DATA_DIR, write_json
from quant_allocator.demo_data.x3_truth import HIDDEN_STRATEGIES, TRUTH_PAIRS
from quant_allocator.evidence.fixtures.x3 import (
    X3_AUTHORED_CLOSURE_SHA256,
    X3_CUTOFFS,
    X3_SCOPE_PRESETS,
    X3_SOURCE_VIEWS,
    build_x3_fixture,
    verify_x3_manifest,
)
from quant_allocator.evidence.model import DatasetSliceRequest
from quant_allocator.evidence.projections import (
    evaluate_funnel_cohort,
    project_entity_mappings,
    project_funnel_cohorts,
    project_funnel_events,
    project_target_grids,
    project_universe_memberships,
)
from quant_allocator.evidence.schema import connect, initialize
from quant_allocator.evidence.snapshot import as_known_slice
from quant_allocator.flagships.universe_coverage.audit import (
    entity_resolution_audit,
    synthetic_discovery_audit,
)
from quant_allocator.flagships.universe_coverage.funnel import build_funnel_summary
from quant_allocator.flagships.universe_coverage.receipts import (
    X3ClaimReceiptContract,
    build_verification_envelope,
    persist_x3_claim_receipt,
)

DISCLAIMER = (
    "This map measures the named sources and funnel, not the manager universe of the world. "
    "It prioritizes research cells, never managers."
)
_PUBLIC = (
    "dataset:x3-public-adviser",
    "dataset:x3-registered-fund",
    "dataset:x3-holdings-filer",
)
_PREHIRE = ("dataset:x3-strategy-export", "dataset:x3-rfi-ddq")
_TARGET = "dataset:x3-target-grid"
_FUNNEL = "dataset:x3-funnel-event"

_CLAIM_SPECS = (
    ("public_source_membership", "/sources/public", ("public",), "A", "exact-per-dataset", "none"),
    (
        "prehire_source_membership",
        "/sources/prehire",
        ("pre-hire-public", "shortlisted-nda"),
        "B",
        "exact-per-selected-dataset",
        "none",
    ),
    (
        "entity_resolution_state",
        "/entity_resolution",
        ("public", "pre-hire-public", "shortlisted-nda"),
        "B",
        "all-required-per-selected-dataset",
        "none",
    ),
    (
        "target_cell_observation",
        "/target_grid/observed_cells",
        ("public", "pre-hire-public", "shortlisted-nda", "internal-governance"),
        "B",
        "all-required-per-dataset",
        "typed-membership-cell-projection-required",
    ),
    (
        "source_union_novelty",
        "/source_novelty",
        ("public", "pre-hire-public", "shortlisted-nda", "internal-governance"),
        "B",
        "all-required-per-dataset",
        "none",
    ),
    (
        "funnel_stage_counts",
        "/funnel/stage_counts",
        ("internal-governance",),
        "B",
        "all-required-per-dataset",
        "none",
    ),
    (
        "funnel_conversion",
        "/funnel/conversion",
        ("internal-governance",),
        "B",
        "all-required-per-dataset",
        "typed-mandate-brief-cohort-projection-required",
    ),
    (
        "research_cell_queue",
        "/queue",
        ("public", "pre-hire-public", "shortlisted-nda", "internal-governance"),
        "C",
        "all-required-per-dataset",
        "typed-membership-cell-projection-required",
    ),
    ("synthetic_entity_recall", "/validation/entity_resolution", ("public",), "D", "synthetic-fixture-only", "none"),
    ("synthetic_discovery_recall", "/validation/discovery", ("public",), "D", "synthetic-fixture-only", "none"),
    (
        "global_universe_coverage",
        "/claims/global",
        ("public", "pre-hire-public", "shortlisted-nda", "internal-governance"),
        "none",
        "refusal-in-every-context",
        "global-universe-denominator-unknown",
    ),
    (
        "manager_quality_ranking",
        "/claims/ranking",
        ("public", "pre-hire-public", "shortlisted-nda", "internal-governance"),
        "none",
        "refusal-in-every-context",
        "manager-quality-ranking-prohibited",
    ),
)


def _request(manifest, dataset_id: str, cutoff):
    return DatasetSliceRequest(
        dataset_id=dataset_id,
        access_context=manifest.access_contexts[dataset_id],
        evidence_right_id=manifest.right_ids[dataset_id],
        licence_purpose=manifest.licence_purposes[dataset_id],
        valid_at=cutoff,
        require_universe_membership=dataset_id in _PUBLIC + _PREHIRE,
    )


def _scope_cells(rows, scope: str):
    liquid = {"public-equity", "hedge-funds", "rates-macro"}
    private = {"fixed-income-credit", "structured-credit", "private-credit", "private-equity", "real-assets"}
    allowed = None if scope == "cross-asset" else liquid if scope == "liquid-public-markets" else private
    return [row for row in rows if allowed is None or json.loads(row["dimensions_json"])["asset_class"] in allowed]


def _source_state(conn, manifest, cutoff, preset: str):
    dataset_ids = _PUBLIC + (() if preset == "public-only" else _PREHIRE)
    slices = {dataset_id: as_known_slice(conn, decision_at=cutoff, request=_request(manifest, dataset_id, cutoff)) for dataset_id in dataset_ids}
    mappings = []
    memberships = []
    canonical_by_dataset = {}
    for dataset_id, slice_ in slices.items():
        projected_mappings = project_entity_mappings(conn, slice_)
        projected_memberships = project_universe_memberships(conn, slice_)
        membership_mapping_ids = {row["entity_mapping_id"] for row in projected_memberships if row["membership_status"] == "active"}
        canonical = {
            row["canonical_entity_id"]
            for row in projected_mappings
            if row["entity_mapping_id"] in membership_mapping_ids
            and row["mapping_status"] == "resolved"
            and row["canonical_entity_id"]
            and row["canonical_entity_id"].startswith("strategy:")
        }
        canonical_by_dataset[dataset_id] = canonical
        mappings.extend(projected_mappings)
        memberships.extend(projected_memberships)
    all_canonical = set().union(*canonical_by_dataset.values()) if canonical_by_dataset else set()
    novelty = {
        dataset_id: len(all_canonical - set().union(*(values for key, values in canonical_by_dataset.items() if key != dataset_id)))
        for dataset_id in canonical_by_dataset
    }
    return slices, mappings, memberships, all_canonical, novelty


def _funnel_state(conn, manifest, cutoff, enabled: bool) -> tuple[dict, object | None]:
    refusal = {
        "pointer": "/funnel/conversion",
        "code": "typed-mandate-brief-cohort-projection-required",
        "detail": "Exact labelled stage counts may render; conversion and mandate-brief inference refuse.",
    }
    if not enabled:
        return {"stage_counts": [], "conversion_interval": None, "refusal": refusal}, None
    slice_ = as_known_slice(conn, decision_at=cutoff, request=_request(manifest, _FUNNEL, cutoff))
    events = {row["funnel_event_id"]: row for row in project_funnel_events(conn, slice_)}
    summaries = []
    for cohort in project_funnel_cohorts(conn, slice_):
        if cohort["completeness_status"] != "complete":
            continue
        evaluated = evaluate_funnel_cohort(conn, slice_, funnel_cohort_id=cohort["funnel_cohort_id"])
        links = []
        for row in evaluated["links"]:
            event = events[row["funnel_event_id"]]
            links.append({**row, "stage_reached": event["funnel_stage"]})
        summary = build_funnel_summary(
            cohort_label=cohort["cohort_label"],
            entry_stage=cohort["entry_stage"],
            outcome_stage=cohort["outcome_stage"],
            links=links,
            typed_mandate_projection_available=False,
        )
        summaries.append(asdict(summary))
    return (
        {
            "stage_counts": sorted(summaries, key=lambda row: row["cohort_label"]),
            "conversion_interval": None,
            "slice_receipt_id": slice_.receipt_id,
            "refusal": refusal,
        },
        slice_,
    )


def _state(conn, manifest, audit: dict, discovery: dict, cutoff_name: str, preset: str, scope: str) -> dict:
    cutoff = X3_CUTOFFS[cutoff_name]
    slices, mappings, memberships, canonical, novelty = _source_state(conn, manifest, cutoff, preset)
    target_slice = as_known_slice(conn, decision_at=cutoff, request=_request(manifest, _TARGET, cutoff))
    grids = project_target_grids(conn, target_slice)
    grid = grids[-1]
    cells = _scope_cells(
        [dict(row) for row in conn.execute("SELECT * FROM target_grid_cell WHERE target_grid_id=? ORDER BY target_grid_cell_id", (grid["target_grid_id"],))],
        scope,
    )
    eligible = [row for row in cells if row["eligibility_status"] == "eligible"]
    excluded = [row for row in cells if row["eligibility_status"] == "excluded"]
    refusals = [
        {
            "pointer": "/target_grid/observed_cells",
            "code": "typed-membership-cell-projection-required",
            "detail": "The shared membership projection has no canonical target-cell link; no label or ordinal inference is permitted.",
        },
        {
            "pointer": "/funnel/conversion",
            "code": "typed-mandate-brief-cohort-projection-required",
            "detail": "The shared opportunity projection has no typed mandate-brief/cohort-key columns.",
        },
    ]
    funnel, funnel_slice = _funnel_state(conn, manifest, cutoff, preset == "full-synthetic-funnel")
    receipts = {dataset_id: slice_.receipt_id for dataset_id, slice_ in slices.items()}
    receipts[_TARGET] = target_slice.receipt_id
    if funnel.get("slice_receipt_id"):
        receipts[_FUNNEL] = funnel["slice_receipt_id"]
    state = {
        "decision_at": cutoff.isoformat(),
        "source_preset": preset,
        "scope_preset": scope,
        "entity_grain": "strategy",
        "denominator_label": "eligible allocator target-grid cells at strategy grain",
        "source_counts": {
            "source_rows": len(mappings),
            "membership_rows": len(memberships),
            "canonical_members": len(canonical),
            "ambiguous_rows": sum(row["mapping_status"] == "ambiguous" for row in mappings),
            "unresolved_rows": sum(row["mapping_status"] == "unresolved" for row in mappings),
        },
        "target_grid": {
            "grid_id": grid["target_grid_id"],
            "denominator_rule": grid["denominator_rule"],
            "eligible_cells": len(eligible),
            "excluded_cells": len(excluded),
            "observed_cells": None,
            "excluded_ledger": [{"cell_id": row["target_grid_cell_id"], "reason": row["exclusion_reason"], "state": "not_targeted"} for row in excluded],
        },
        "source_novelty": novelty,
        "funnel": funnel,
        "queue": [],
        "slice_receipts": receipts,
        "refusals": refusals,
    }
    state_key = "|".join((cutoff_name, preset, scope))
    envelope_slices = (*slices.values(), target_slice) + (() if funnel_slice is None else (funnel_slice,))
    bundle = build_verification_envelope(
        conn,
        state_key=state_key,
        decision_at=cutoff,
        slices=envelope_slices,
    )
    public_slices = tuple(slices[dataset_id] for dataset_id in _PUBLIC)
    prehire_slices = tuple(
        slices.get(dataset_id)
        or as_known_slice(
            conn,
            decision_at=cutoff,
            request=_request(manifest, dataset_id, cutoff),
        )
        for dataset_id in _PREHIRE
    )
    funnel_evidence_slice = funnel_slice or as_known_slice(
        conn,
        decision_at=cutoff,
        request=_request(manifest, _FUNNEL, cutoff),
    )
    selected_source_slices = tuple(slices.values())
    claim_slices = {
        "public_source_membership": public_slices,
        "prehire_source_membership": prehire_slices,
        "entity_resolution_state": selected_source_slices,
        "target_cell_observation": selected_source_slices + (target_slice,),
        "source_union_novelty": selected_source_slices + (target_slice,),
        "funnel_stage_counts": (funnel_evidence_slice,),
        "funnel_conversion": (funnel_evidence_slice,),
        "research_cell_queue": selected_source_slices
        + (target_slice,)
        + (() if funnel_slice is None else (funnel_slice,)),
        "synthetic_entity_recall": public_slices,
        "synthetic_discovery_recall": public_slices,
        "global_universe_coverage": selected_source_slices + (target_slice,),
        "manager_quality_ranking": selected_source_slices + (target_slice,),
    }
    evaluation_receipt_ids = tuple(
        sorted(
            {
                receipt_id
                for row in funnel["stage_counts"]
                for receipt_id in row.get("evaluation_receipt_ids", ())
            }
        )
    )
    evaluation_receipts_applicable = (
        cutoff_name == "latest" and preset == "full-synthetic-funnel"
    )
    if evaluation_receipts_applicable and len(evaluation_receipt_ids) != 168:
        raise RuntimeError("X3 full-funnel evaluation receipt set must contain exactly 168 IDs")
    if not evaluation_receipts_applicable and evaluation_receipt_ids:
        raise RuntimeError("X3 count-free state cannot bind evaluation receipts")
    claim_values = {
        "public_source_membership": state["source_counts"],
        "prehire_source_membership": state["source_counts"],
        "entity_resolution_state": state["source_counts"],
        "target_cell_observation": None,
        "source_union_novelty": state["source_novelty"],
        "funnel_stage_counts": funnel["stage_counts"],
        "funnel_conversion": {
            "conversion_interval": None,
            "stage_counts": funnel["stage_counts"],
        },
        "research_cell_queue": [],
        "synthetic_entity_recall": audit,
        "synthetic_discovery_recall": discovery,
        "global_universe_coverage": None,
        "manager_quality_ranking": None,
    }
    claim_receipt_ids = {}
    for claim_id, pointer, contexts, ceiling, _semantics, refusal in _CLAIM_SPECS:
        claim_bundle = build_verification_envelope(
            conn,
            state_key=f"{state_key}|claim:{claim_id}",
            decision_at=cutoff,
            slices=claim_slices[claim_id],
        )
        claim_receipt_ids[claim_id] = persist_x3_claim_receipt(
            conn,
            bundle=claim_bundle,
            contract=X3ClaimReceiptContract(
                claim_id=claim_id,
                output_pointer=pointer,
                state_key=state_key,
                access_contexts=contexts,
                live_attestation_ceiling="D" if ceiling == "none" else ceiling,
                value=claim_values[claim_id],
                refusal_code="" if refusal == "none" else refusal,
                evaluation_receipt_ids=(
                    evaluation_receipt_ids if claim_id in {"funnel_stage_counts", "funnel_conversion"} else ()
                ),
            ),
        )
    state["join_receipt_id"] = bundle.join_receipt_id
    state["bundle_digest"] = bundle.bundle_digest
    state["claim_receipt_ids"] = claim_receipt_ids
    return state


def _claims(receipt_ids: dict[str, str]) -> list[dict]:
    return [
        {
            "claim_id": claim_id,
            "access_contexts": list(contexts),
            "access_semantics": access_semantics,
            "current_attestation": "D",
            "live_ceiling": "D" if ceiling == "none" else ceiling,
            "validation_status": "synthetic-demo-verified" if "synthetic" in claim_id or ceiling == "none" else "live-calibration-required",
            "receipt_required": True,
            "receipt_id": receipt_ids[claim_id],
            "rendered_refusal": refusal,
        }
        for claim_id, _pointer, contexts, ceiling, access_semantics, refusal in _CLAIM_SPECS
    ]


@lru_cache(maxsize=1)
def _build_data() -> dict:
    conn = connect()
    initialize(conn)
    manifest = build_x3_fixture(conn)
    if not verify_x3_manifest(conn, manifest):
        raise RuntimeError("reviewed X3 fixture manifest failed verification")
    audit = entity_resolution_audit(TRUTH_PAIRS)
    latest_strategy_ids = tuple(
        row[0]
        for row in conn.execute("SELECT entity_id FROM canonical_entity WHERE entity_type='strategy' ORDER BY entity_id")
    )
    discovery = synthetic_discovery_audit(latest_strategy_ids[:-1], HIDDEN_STRATEGIES)
    audit_data = asdict(audit)
    discovery_data = asdict(discovery)
    states = {
        "|".join(key): _state(conn, manifest, audit_data, discovery_data, *key)
        for key in product(X3_CUTOFFS, X3_SOURCE_VIEWS, X3_SCOPE_PRESETS)
    }
    default_receipts = states["latest|public-plus-prehire|cross-asset"]["claim_receipt_ids"]
    data = {
        "meta": {
            "card_id": "x3",
            "fixture_id": manifest.fixture_id,
            "fixture_digest": manifest.fixture_digest,
            "authored_closure_digest": X3_AUTHORED_CLOSURE_SHA256,
            "schema_digest": manifest.schema_digest,
            "state_count": len(states),
            "default_state": "latest|public-plus-prehire|cross-asset",
            "current_attestation": "D",
            "disclaimer": DISCLAIMER,
            "synthetic_disclosure": manifest.disclosure,
        },
        "claim_attestation": _claims(default_receipts),
        "taxonomy": {"entity_grain": "strategy", "scope_presets": list(X3_SCOPE_PRESETS)},
        "source_catalog": list(manifest.dataset_ids),
        "states": states,
        "entity_resolution_audit": audit_data,
        "synthetic_discovery_audit": discovery_data,
        "refusal_ledger": [
            {"claim_id": "global_universe_coverage", "pointer": "/claims/global", "code": "global-universe-denominator-unknown"},
            {"claim_id": "manager_quality_ranking", "pointer": "/claims/ranking", "code": "manager-quality-ranking-prohibited"},
            {"claim_id": "funnel_conversion", "pointer": "/funnel/conversion", "code": "typed-mandate-brief-cohort-projection-required"},
            {"claim_id": "target_cell_observation", "pointer": "/target_grid/observed_cells", "code": "typed-membership-cell-projection-required"},
        ],
        "method_receipts": {
            "fixture_verified": True,
            "manifest_digest": manifest.fixture_digest,
            "projection_schema_ids": list(manifest.projection_schema_ids),
            "shared_join_receipts": list(manifest.join_receipt_ids),
            "shared_bundle_digests": list(manifest.bundle_digests),
            "point_in_time_cases": dict(manifest.pit_cases),
        },
        "provisional_constants": {"wilson_z": 1.96, "precision_floor": 0.99, "recall_floor": 0.95, "minimum_perfect_tp": 381, "funnel_rate_minimum": 20},
    }
    conn.close()
    return data


def build(*, out_dir: Path = SITE_DATA_DIR) -> Path:
    return write_json(out_dir / "x3_universe.json", _build_data())
