"""Deterministic E4 point-in-time operational-change exhibit."""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

from quant_allocator.demo_data._emit import SITE_DATA_DIR, write_json
from quant_allocator.evidence.model import machine_id, normalize_utc
from quant_allocator.flagships.knowledge.operational_evidence import (
    build_operational_evidence_fixture,
)
from quant_allocator.flagships.operational_change import build_operational_output

STATE_KEYS = tuple(
    sorted(
        f"{cutoff}|{source_view}"
        for cutoff in ("early", "middle", "latest")
        for source_view in ("public-only", "all-entitled")
    )
)
DEFAULT_STATE = "latest|all-entitled"
DOMAIN_FILTERS = ("all", "organisation", "process", "control", "provider", "incident")
STATE_FILTERS = ("all", "corroborated", "asserted", "conflicted", "stale")
VIEW_FILTERS = ("timeline", "graph", "table")
STATE_ORDER = {
    value: index
    for index, value in enumerate(("conflicted", "stale", "corroborated", "asserted"))
}
DOMAIN_ORDER = {value: index for index, value in enumerate(DOMAIN_FILTERS[1:])}


def _claim_inventory() -> list[dict[str, Any]]:
    permissioned = [
        "shortlisted-nda",
        "funded-commingled",
        "funded-private-partnership",
        "segregated-mandate",
    ]
    all_contexts = ["public", "pre-hire-public", *permissioned]
    rows = (
        (
            "public_operational_facts",
            "/facts",
            "evidence-graph",
            ["public", "pre-hire-public"],
            "all-required-per-selected-dataset",
            "C",
        ),
        (
            "operational_change_graph",
            "/changes",
            "evidence-graph",
            permissioned,
            "all-required-per-selected-dataset",
            "B",
        ),
        (
            "operational_evidence_state",
            "/state_summary",
            "verdict",
            permissioned,
            "all-required-per-selected-dataset",
            "B",
        ),
        (
            "reunderwriting_queue",
            "/reunderwriting_queue",
            "exact-measurement",
            permissioned,
            "all-required-per-selected-dataset",
            "B",
        ),
        (
            "operational_data_boundary_refusals",
            "/refusals/data-boundary",
            "refusal",
            all_contexts,
            "refusal-per-inadmissible-input",
            "D",
        ),
        (
            "operational_method_boundary_refusal",
            "/refusals/method-boundary",
            "refusal",
            all_contexts,
            "refusal-in-every-context",
            "D",
        ),
        (
            "synthetic_state_validation",
            "/validation",
            "exact-measurement",
            ["public"],
            "synthetic-fixture-only",
            "D",
        ),
    )
    return [
        {
            "claim_id": claim_id,
            "output_pointer": pointer,
            "output_type": output_type,
            "access_contexts": list(contexts),
            "access_semantics": semantics,
            "current_attestation": "D",
            "live_attestation_ceiling": ceiling,
            "receipt_required": True,
        }
        for claim_id, pointer, output_type, contexts, semantics, ceiling in rows
    ]


def _json_value(value: Any) -> Any:
    if isinstance(value, datetime):
        return normalize_utc(value)
    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_value(item) for item in value]
    return value


def _bundle_receipts(bundles) -> list[dict[str, str]]:
    rows = []
    for bundle in bundles:
        slice_ = bundle.slices[0]
        rows.append(
            {
                "dataset_id": slice_.request.dataset_id,
                "slice_digest": slice_.digest,
                "slice_receipt_id": slice_.receipt_id,
                "join_receipt_id": bundle.join_receipt_id,
                "bundle_digest": bundle.bundle_digest,
            }
        )
    return rows


def _relationship(
    fixture,
    relationship_id: str,
    *,
    state_key: str,
    fact_ids: list[str],
    receipt_id: str,
) -> dict[str, Any]:
    row = fixture.conn.execute(
        "SELECT * FROM entity_relationship WHERE entity_relationship_id=?", (relationship_id,)
    ).fetchone()
    if row is None:
        raise ValueError("operational-relationship-missing")
    labels = {
        entity_id: name
        for entity_id, name in fixture.conn.execute(
            "SELECT entity_id,canonical_name FROM canonical_entity WHERE entity_id IN (?,?)",
            (row["source_entity_id"], row["target_entity_id"]),
        )
    }
    return {
        "relationship_id": relationship_id,
        "relation_type": row["relation_type"],
        "source_entity_id": row["source_entity_id"],
        "source_label": labels[row["source_entity_id"]],
        "target_entity_id": row["target_entity_id"],
        "target_label": labels[row["target_entity_id"]],
        "effective_from": row["effective_from"],
        "effective_to": row["effective_to"],
        "evidence_item_id": row["source_evidence_item_id"],
        "evidence_span_id": row["evidence_span_id"],
        "linked_fact_ids_by_state": {state_key: fact_ids},
        "receipt_ids_by_state": {state_key: receipt_id},
    }


def _fact_row(context, receipts: Mapping[str, str], state_key: str) -> dict[str, Any]:
    fact = context.fact
    row = _json_value(asdict(fact))
    row.update(
        {
            "dataset_id": context.dataset_id,
            "source_record_id": context.source_record_id,
            "available_at": normalize_utc(context.available_at),
            "freshness_at": normalize_utc(context.freshness_at)
            if context.freshness_at
            else None,
            "incident_materiality": context.incident_materiality,
            "source_schema_id": context.source_schema_id,
            "receipt_ids_by_state": {state_key: receipts[f"/facts/{fact.fact_id}"]},
        }
    )
    return row


def _merge_catalog(
    catalog: dict[str, dict[str, Any]], row: dict[str, Any], *, state_key: str
) -> None:
    identifier = str(
        row.get("fact_id")
        or row.get("change_id")
        or row.get("relationship_id")
        or row.get("exclusion_id")
        or row.get("refusal_id")
    )
    existing = catalog.get(identifier)
    if existing is None:
        catalog[identifier] = row
        return
    if "receipt_ids_by_state" in row:
        existing["receipt_ids_by_state"].update(row["receipt_ids_by_state"])
    if "linked_fact_ids_by_state" in row:
        existing["linked_fact_ids_by_state"].update(row["linked_fact_ids_by_state"])


def _state_row(state, state_key: str) -> dict[str, Any]:
    return {
        "state_id": machine_id("operational-evidence-state", {"fact_key": state.fact_key}),
        **_json_value(asdict(state)),
    }


def _visible_id_sets(
    *,
    facts: list[dict[str, Any]],
    changes: list[dict[str, Any]],
    relationships: list[dict[str, Any]],
    queue: list[dict[str, Any]],
    states: list[dict[str, Any]],
    state_key: str,
) -> dict[str, dict[str, Any]]:
    fact_by_id = {row["fact_id"]: row for row in facts}
    state_by_fact: dict[str, str] = {}
    state_by_key: dict[tuple[str, ...], dict[str, Any]] = {}
    for row in states:
        state_by_key[tuple(row["fact_key"])] = row
        for fact_id in (*row["supporting_fact_ids"], *row["conflicting_fact_ids"]):
            state_by_fact[fact_id] = row["state"]
    change_links = {}
    for row in changes:
        state = state_by_key.get(tuple(row["fact_key"]))
        current_ids = (
            [*state["supporting_fact_ids"], *state["conflicting_fact_ids"]] if state else []
        )
        change_links[row["change_id"]] = sorted(
            {
                *(identifier for identifier in (row["before_fact_id"], row["after_fact_id"]) if identifier),
                *current_ids,
            }
        )
        row["linked_fact_ids_by_state"] = {state_key: change_links[row["change_id"]]}
    queue_links = {}
    for row in queue:
        state = state_by_key[tuple(row["fact_key"])]
        queue_links[row["queue_id"]] = sorted(
            [*state["supporting_fact_ids"], *state["conflicting_fact_ids"]]
        )
        row["linked_fact_ids_by_state"] = {state_key: queue_links[row["queue_id"]]}

    result = {}
    for domain in DOMAIN_FILTERS:
        for evidence_state in STATE_FILTERS:
            visible_facts = [
                fact_id
                for fact_id, fact in fact_by_id.items()
                if (domain == "all" or fact["domain"] == domain)
                and (evidence_state == "all" or state_by_fact.get(fact_id) == evidence_state)
            ]
            visible_fact_set = set(visible_facts)
            visible_changes = [
                row["change_id"]
                for row in changes
                if (domain == "all" or row["fact_key"][1] == domain)
                and (
                    evidence_state == "all"
                    or bool(visible_fact_set.intersection(change_links[row["change_id"]]))
                )
            ]
            visible_relationships = [
                row["relationship_id"]
                for row in relationships
                if visible_fact_set.intersection(row["linked_fact_ids_by_state"][state_key])
            ]
            visible_queue = [
                row["queue_id"]
                for row in queue
                if visible_fact_set.intersection(queue_links[row["queue_id"]])
            ]
            for view in VIEW_FILTERS:
                key = f"{domain}|{evidence_state}|{view}"
                result[key] = {
                    "fact_ids": visible_facts,
                    "change_ids": visible_changes,
                    "relationship_ids": visible_relationships,
                    "queue_ids": visible_queue,
                    "empty": not any(
                        (visible_facts, visible_changes, visible_relationships, visible_queue)
                    ),
                }
    return result


def _state_payload(fixture, cutoff_key: str, source_view: str):
    built = build_operational_output(fixture, cutoff_key=cutoff_key, source_view=source_view)
    analysis = built.analysis
    state_key = f"{cutoff_key}|{source_view}"
    contexts = {row.fact.fact_id: row for row in analysis.fact_contexts}
    facts = [
        _fact_row(contexts[fact.fact_id], built.claim_receipts, state_key)
        for fact in analysis.facts
    ]
    changes = []
    for change in analysis.changes:
        pointer = f"/changes/{change.change_id}"
        changes.append(
            {
                **_json_value(asdict(change)),
                "receipt_ids_by_state": {state_key: built.claim_receipts[pointer]},
            }
        )
    states = [_state_row(state, state_key) for state in analysis.states]
    queue = []
    for item in analysis.queue:
        pointer = f"/reunderwriting_queue/{item.queue_id}"
        queue.append(
            {
                **_json_value(asdict(item)),
                "receipt_ids_by_state": {state_key: built.claim_receipts[pointer]},
            }
        )
    exclusions = []
    for row in analysis.exclusions:
        pointer = f"/exclusions/{row.exclusion_id}"
        exclusions.append(
            {
                **_json_value(asdict(row)),
                "receipt_ids_by_state": {state_key: built.claim_receipts[pointer]},
            }
        )
    refusals = []
    for row in analysis.refusals:
        refusals.append(
            {
                **_json_value(asdict(row)),
                "receipt_ids_by_state": {state_key: built.claim_receipts[row.output_pointer]},
            }
        )
    relationship_fact_ids: dict[str, list[str]] = {}
    for fact in analysis.facts:
        if fact.entity_relationship_id is not None:
            relationship_fact_ids.setdefault(fact.entity_relationship_id, []).append(fact.fact_id)
    relationships = [
        _relationship(
            fixture,
            relationship_id,
            state_key=state_key,
            fact_ids=sorted(fact_ids),
            receipt_id=built.claim_receipts[f"/relationships/{relationship_id}"],
        )
        for relationship_id, fact_ids in sorted(relationship_fact_ids.items())
    ]
    visible_id_sets = _visible_id_sets(
        facts=facts,
        changes=changes,
        relationships=relationships,
        queue=queue,
        states=states,
        state_key=state_key,
    )
    state_counts = dict(sorted(Counter(row.state for row in analysis.states).items()))
    interaction = {
        "key": state_key,
        "cutoff": cutoff_key,
        "source_view": source_view,
        "access_context": "public" if source_view == "public-only" else "shortlisted-nda",
        "selected_dataset_ids": list(built.selected_dataset_ids),
        "source_bundle_receipts": _bundle_receipts(built.analytic_bundles),
        "composite_union_receipt_id": built.claim_receipts["/facts"],
        "state_counts": state_counts,
        "refusal_count": len(refusals) + 1,
        "fact_ids": [row.fact_id for row in analysis.facts],
        "change_ids": [row.change_id for row in analysis.changes],
        "relationship_ids": [row["relationship_id"] for row in relationships],
        "queue_ids": [row.queue_id for row in analysis.queue],
        "exclusion_ids": [row.exclusion_id for row in analysis.exclusions],
        "data_boundary_refusal_ids": [row.refusal_id for row in analysis.refusals],
        "method_boundary_refusal_id": built.claim_receipts["/refusals/method-boundary"],
        "refusal_ids": [
            *(row.refusal_id for row in analysis.refusals),
            "method-boundary",
        ],
        "claim_receipt_ids": sorted(set(built.claim_receipts.values())),
        "visible_id_sets": visible_id_sets,
    }
    return built, facts, changes, states, queue, exclusions, refusals, relationships, interaction


def build(out_dir: Path = SITE_DATA_DIR) -> Path:
    manifest_fixture = build_operational_evidence_fixture()
    facts: dict[str, dict[str, Any]] = {}
    changes: dict[str, dict[str, Any]] = {}
    relationships: dict[str, dict[str, Any]] = {}
    exclusions: dict[str, dict[str, Any]] = {}
    data_refusals: dict[str, dict[str, Any]] = {}
    state_summary: dict[str, list[dict[str, Any]]] = {}
    queue: dict[str, list[dict[str, Any]]] = {}
    interactions: dict[str, dict[str, Any]] = {}
    claim_receipts: dict[str, dict[str, str]] = {}
    method_refusal_receipts: dict[str, str] = {}
    validation_receipts: dict[str, str] = {}
    evidence_states: dict[str, dict[str, Any]] = {}

    for state_key in STATE_KEYS:
        fixture = build_operational_evidence_fixture()
        cutoff_key, source_view = state_key.split("|", 1)
        (
            built,
            state_facts,
            state_changes,
            states,
            state_queue,
            state_exclusions,
            state_refusals,
            state_relationships,
            interaction,
        ) = _state_payload(fixture, cutoff_key, source_view)
        for row in state_facts:
            _merge_catalog(facts, row, state_key=state_key)
        for row in state_changes:
            _merge_catalog(changes, row, state_key=state_key)
        for row in state_relationships:
            _merge_catalog(relationships, row, state_key=state_key)
        for row in state_exclusions:
            _merge_catalog(exclusions, row, state_key=state_key)
        for row in state_refusals:
            _merge_catalog(data_refusals, row, state_key=state_key)
        state_summary[state_key] = states
        queue[state_key] = state_queue
        interactions[state_key] = interaction
        claim_receipts[state_key] = dict(built.claim_receipts)
        method_refusal_receipts[state_key] = built.claim_receipts["/refusals/method-boundary"]
        validation_receipts[state_key] = built.claim_receipts["/validation"]
        evidence_states[state_key] = {
            "decision_at": normalize_utc(built.decision_at),
            "source_view": source_view,
            "access_context": interaction["access_context"],
            "selected_dataset_ids": list(built.selected_dataset_ids),
            "source_bundle_receipts": interaction["source_bundle_receipts"],
            "verification_envelope": {
                "join_receipt_id": built.verification_bundle.join_receipt_id,
                "bundle_digest": built.verification_bundle.bundle_digest,
            },
        }
        fixture.conn.close()

    latest_states = state_summary[DEFAULT_STATE]
    latest_queue = queue[DEFAULT_STATE]
    observed = {
        "facts": len(interactions[DEFAULT_STATE]["fact_ids"]),
        "keys": len(latest_states),
        "states": dict(sorted(Counter(row["state"] for row in latest_states).items())),
        "queue": dict(sorted(Counter(row["action_bucket"] for row in latest_queue).items())),
    }
    fact_state_rank: dict[str, int] = {}
    for rows in state_summary.values():
        for row in rows:
            rank = STATE_ORDER[row["state"]]
            for fact_id in (*row["supporting_fact_ids"], *row["conflicting_fact_ids"]):
                fact_state_rank[fact_id] = min(fact_state_rank.get(fact_id, rank), rank)

    ordered_facts = sorted(
        facts.values(),
        key=lambda row: (
            fact_state_rank.get(row["fact_id"], len(STATE_ORDER)),
            DOMAIN_ORDER[row["domain"]],
            tuple(row[field] for field in ("manager_entity_id", "domain", "subject_entity_id", "predicate", "scope")),
            row["fact_id"],
        ),
    )
    ordered_changes = sorted(
        changes.values(), key=lambda row: (row["effective_at"], row["change_id"])
    )
    ordered_relationships = sorted(
        relationships.values(),
        key=lambda row: (
            row["relation_type"],
            row["source_entity_id"],
            row["target_entity_id"],
            row["relationship_id"],
        ),
    )
    ordered_exclusions = sorted(
        exclusions.values(),
        key=lambda row: (row["reason_code"], row["source_record_id"], row["exclusion_id"]),
    )
    ordered_data_refusals = sorted(
        data_refusals.values(),
        key=lambda row: (row["reason_code"], row["affected_id"], row["refusal_id"]),
    )

    payload = {
        "meta": {
            "generator": "e4_operational_change",
            "fixture_id": manifest_fixture.manifest.fixture_id,
            "fixture_digest": manifest_fixture.manifest.fixture_digest,
            "evidence_schema_version": manifest_fixture.manifest.evidence_schema_version,
            "evidence_schema_digest": manifest_fixture.manifest.evidence_schema_digest,
            "default_state": DEFAULT_STATE,
            "interaction_state_keys": list(STATE_KEYS),
            "current_attestation": "D",
            "live_attestation_ceilings": {
                "public_operational_facts": "C",
                "permissioned_analysis": "B",
                "refusals_and_validation": "D",
            },
            "disclosure": manifest_fixture.manifest.disclosure,
        },
        "evidence": {
            "states": evidence_states,
            "limitations": list(manifest_fixture.manifest.limitation_codes),
            "ordered_dataset_ids": list(manifest_fixture.manifest.ordered_dataset_ids),
        },
        "state_summary": state_summary,
        "facts": ordered_facts,
        "changes": ordered_changes,
        "relationships": ordered_relationships,
        "reunderwriting_queue": queue,
        "refusals": {
            "data_boundary": ordered_data_refusals,
            "method_boundary": {
                "state": "refused",
                "reason_code": "scalar-operational-judgement-prohibited",
                "prohibited_outputs": [
                    "scalar ODD score",
                    "clean or approve verdict",
                    "hire or fire decision",
                    "recommendation",
                    "manager rank",
                ],
                "output_pointer": "/refusals/method-boundary",
                "receipt_ids_by_state": method_refusal_receipts,
            },
        },
        "validation": {
            "state": "derived",
            "latest_all_entitled": observed,
            "receipt_ids_by_state": validation_receipts,
        },
        "interaction_states": interactions,
        "claim_inventory": _claim_inventory(),
        "claim_receipts": claim_receipts,
        "exclusions": ordered_exclusions,
    }
    manifest_fixture.conn.close()
    return write_json(out_dir / "e4_operational_change.json", payload)
