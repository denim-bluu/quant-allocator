from __future__ import annotations

from collections import Counter
from datetime import datetime

from quant_allocator.evidence.model import canonical_bytes
from quant_allocator.flagships.knowledge.operational_evidence import (
    build_operational_evidence_fixture,
    operational_source_bundle,
)
from quant_allocator.flagships.operational_change import analyze_operational_evidence


def _analysis(cutoff_key: str, source_view: str):
    fixture = build_operational_evidence_fixture()
    decision_at = datetime.fromisoformat(
        dict(fixture.manifest.cutoff_items)[cutoff_key].replace("Z", "+00:00")
    )
    selected = dict(fixture.manifest.source_view_items)[source_view]
    analytic = tuple(
        operational_source_bundle(
            fixture,
            dataset_id=dataset_id,
            decision_at=decision_at,
            revision_mode="latest-known",
            include_unresolved=False,
        )
        for dataset_id in selected
    )
    audit = tuple(
        operational_source_bundle(
            fixture,
            dataset_id=dataset_id,
            decision_at=decision_at,
            revision_mode="all-known-versions",
            include_unresolved=True,
        )
        for dataset_id in selected
    )
    return fixture, analyze_operational_evidence(
        fixture,
        analytic_bundles=analytic,
        audit_bundles=audit,
        decision_at=decision_at,
    )


def test_normalization_uses_shared_rows_and_excludes_null_canonical_keys() -> None:
    _, analysis = _analysis("latest", "all-entitled")
    assert analysis.facts
    assert all(fact.manager_entity_id == "manager:e4-northbridge" for fact in analysis.facts)
    assert all(fact.evidence_item_id and fact.evidence_span_id for fact in analysis.facts)
    assert all(fact.dataset_observation_id and fact.dataset_version_id for fact in analysis.facts)
    assert all(fact.evidence_right_id for fact in analysis.facts)
    assert len(analysis.exclusions) >= 2
    assert {row.reason_code for row in analysis.exclusions} == {"canonical-entity-unresolved"}
    excluded_items = {row.evidence_item_id for row in analysis.exclusions}
    assert not excluded_items.intersection(fact.evidence_item_id for fact in analysis.facts)


def test_point_in_time_revision_diff_refusals_and_removal_are_visible() -> None:
    _, early = _analysis("early", "all-entitled")
    _, latest = _analysis("latest", "all-entitled")
    early_values = {(fact.scope, fact.typed_value) for fact in early.facts}
    latest_values = {(fact.scope, fact.typed_value) for fact in latest.facts}
    assert ("fund-administration", "provider:e4-admin-a") in early_values
    assert ("fund-administration", "provider:e4-admin-b") in latest_values
    assert any(change.change_kind == "modified" for change in latest.changes)
    assert any(change.change_kind == "corrected" for change in latest.changes)
    assert any(change.change_kind == "explicitly-removed" for change in latest.changes)
    assert {row.reason_code for row in latest.refusals} >= {
        "inferred-date-refused",
        "unversioned-change-refused",
    }
    assert not any(change.fact_key[4] == "change-date-provenance" for change in latest.changes)


def test_state_and_queue_outputs_are_deterministic_and_unscored() -> None:
    _, first = _analysis("latest", "all-entitled")
    _, second = _analysis("latest", "all-entitled")
    assert canonical_bytes(first) == canonical_bytes(second)
    assert {state.state for state in first.states} <= {
        "corroborated",
        "asserted",
        "conflicted",
        "stale",
    }
    assert all(item.action_bucket for item in first.queue)
    payload = canonical_bytes(first).decode().lower()
    assert "odd_score" not in payload and "manager_rank" not in payload


def test_latest_held_gate_matches_the_reviewed_fixture_contract() -> None:
    _, analysis = _analysis("latest", "all-entitled")

    assert len(analysis.facts) == 16
    assert len(analysis.states) == 10
    assert Counter(state.state for state in analysis.states) == {
        "corroborated": 1,
        "asserted": 3,
        "conflicted": 3,
        "stale": 3,
    }
    assert Counter(item.action_bucket for item in analysis.queue) == {
        "immediate-clarification": 4,
        "scheduled-reunderwrite": 4,
        "evidence-refresh": 2,
    }


def test_provider_direct_does_not_corroborate_a_process_fact() -> None:
    _, analysis = _analysis("latest", "all-entitled")
    process_state = next(
        state
        for state in analysis.states
        if state.fact_key[1:] == (
            "process",
            "process:e4-nav-review",
            "operates-process",
            "nav-review",
        )
    )
    contexts = {
        context.fact.fact_id: context
        for context in analysis.fact_contexts
        if context.fact.fact_id in process_state.supporting_fact_ids
    }

    assert {context.fact.independence_group for context in contexts.values()} == {
        "manager-self",
        "provider-direct",
    }
    assert process_state.state == "asserted"


def test_unknown_incident_materiality_precedes_staleness_in_queue() -> None:
    _, analysis = _analysis("latest", "all-entitled")
    state = next(
        state
        for state in analysis.states
        if state.fact_key[1:] == (
            "incident",
            "incident:e4-nav-delay",
            "affected",
            "materiality-unreported",
        )
    )
    item = next(item for item in analysis.queue if item.fact_key == state.fact_key)
    context = next(
        context
        for context in analysis.fact_contexts
        if context.fact.fact_id in state.supporting_fact_ids
    )

    assert state.state == "stale"
    assert context.incident_materiality == "unknown"
    assert item.action_bucket == "immediate-clarification"
