from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from types import MappingProxyType
from typing import Mapping, Sequence

from quant_allocator.evidence.model import SnapshotBundle, machine_id
from quant_allocator.flagships.knowledge.operational_evidence import (
    OperationalEvidenceFixture,
    operational_source_bundle,
    operational_verification_bundle,
)

from .core import (
    FactContext,
    OperationalAnalysis,
    _context_from_row,
    analyze_operational_evidence,
    with_state_receipts,
)
from .receipts import (
    build_operational_closure,
    persist_operational_receipt,
    verify_operational_receipt,
)


@dataclass(frozen=True, slots=True)
class OperationalBuiltState:
    cutoff_key: str
    source_view: str
    decision_at: datetime
    selected_dataset_ids: tuple[str, ...]
    analytic_bundles: tuple[SnapshotBundle, ...]
    audit_bundles: tuple[SnapshotBundle, ...]
    verification_bundle: SnapshotBundle
    analysis: OperationalAnalysis
    claim_receipts: Mapping[str, str]


def _bundles(
    fixture: OperationalEvidenceFixture,
    *,
    selected_dataset_ids: tuple[str, ...],
    decision_at: datetime,
    revision_mode: str,
    include_unresolved: bool,
) -> tuple[SnapshotBundle, ...]:
    return tuple(
        operational_source_bundle(
            fixture,
            dataset_id=dataset_id,
            decision_at=decision_at,
            revision_mode=revision_mode,
            include_unresolved=include_unresolved,
        )
        for dataset_id in selected_dataset_ids
    )


def _raw_contexts(
    fixture: OperationalEvidenceFixture, bundles: Sequence[SnapshotBundle]
) -> tuple[FactContext, ...]:
    contexts: dict[str, FactContext] = {}
    for bundle in bundles:
        for row in bundle.slices[0].rows:
            context = _context_from_row(fixture, row)
            contexts.setdefault(context.fact.fact_id, context)
    return tuple(sorted(contexts.values(), key=lambda row: row.fact.fact_id))


def _receipt(
    fixture: OperationalEvidenceFixture,
    *,
    claim_id: str,
    decision_at: datetime,
    source_view: str,
    output_pointer: str,
    audit_bundles: tuple[SnapshotBundle, ...],
    verification_bundle: SnapshotBundle,
    contexts: Sequence[FactContext],
    value: object,
    disposition: str = "included",
    role: str = "input",
) -> str:
    closure = build_operational_closure(
        fixture,
        claim_id=claim_id,
        decision_at=decision_at,
        access_view=source_view,
        output_pointer=output_pointer,
        source_bundles=audit_bundles,
        verification_bundle=verification_bundle,
        contexts=contexts,
        value=value,
        disposition=disposition,
        role=role,
    )
    receipt_id = persist_operational_receipt(fixture.conn, closure)
    verify_operational_receipt(
        fixture.conn,
        receipt_id=receipt_id,
        source_bundles=audit_bundles,
        verification_bundle=verification_bundle,
        closure=closure,
    )
    return receipt_id


def _state_identifier(fact_key: tuple[str, str, str, str, str]) -> str:
    return machine_id("operational-evidence-state", {"fact_key": fact_key})


def build_operational_output(
    fixture: OperationalEvidenceFixture, *, cutoff_key: str, source_view: str
) -> OperationalBuiltState:
    try:
        decision_at = datetime.fromisoformat(
            dict(fixture.manifest.cutoff_items)[cutoff_key].replace("Z", "+00:00")
        )
        selected_dataset_ids = tuple(dict(fixture.manifest.source_view_items)[source_view])
    except KeyError as exc:
        raise ValueError("operational-state-key-unknown") from exc

    analytic_bundles = _bundles(
        fixture,
        selected_dataset_ids=selected_dataset_ids,
        decision_at=decision_at,
        revision_mode="latest-known",
        include_unresolved=False,
    )
    audit_bundles = _bundles(
        fixture,
        selected_dataset_ids=selected_dataset_ids,
        decision_at=decision_at,
        revision_mode="all-known-versions",
        include_unresolved=True,
    )
    verification_bundle = operational_verification_bundle(
        fixture,
        selected_dataset_ids=selected_dataset_ids,
        decision_at=decision_at,
        revision_mode="all-known-versions",
        include_unresolved=True,
    )
    analysis = analyze_operational_evidence(
        fixture,
        analytic_bundles=analytic_bundles,
        audit_bundles=audit_bundles,
        decision_at=decision_at,
    )
    analytic_by_id = {row.fact.fact_id: row for row in analysis.fact_contexts}
    audit_contexts = _raw_contexts(fixture, audit_bundles)
    audit_by_id = {row.fact.fact_id: row for row in audit_contexts}
    audit_by_item = {row.fact.evidence_item_id: row for row in audit_contexts}
    receipts: dict[str, str] = {}

    facts_claim = (
        "public_operational_facts" if source_view == "public-only" else "operational_change_graph"
    )
    receipts["/facts"] = _receipt(
        fixture,
        claim_id=facts_claim,
        decision_at=decision_at,
        source_view=source_view,
        output_pointer="/facts",
        audit_bundles=audit_bundles,
        verification_bundle=verification_bundle,
        contexts=tuple(audit_by_id[fact.fact_id] for fact in analysis.facts),
        value={"fact_ids": tuple(fact.fact_id for fact in analysis.facts)},
    )
    for fact in analysis.facts:
        pointer = f"/facts/{fact.fact_id}"
        receipts[pointer] = _receipt(
            fixture,
            claim_id=facts_claim,
            decision_at=decision_at,
            source_view=source_view,
            output_pointer=pointer,
            audit_bundles=audit_bundles,
            verification_bundle=verification_bundle,
            contexts=(audit_by_id[fact.fact_id],),
            value=asdict(fact),
        )

    relationship_contexts: dict[str, list[FactContext]] = {}
    for context in analysis.fact_contexts:
        relationship_id = context.fact.entity_relationship_id
        if relationship_id is not None:
            relationship_contexts.setdefault(relationship_id, []).append(context)
    for relationship_id, contexts in sorted(relationship_contexts.items()):
        pointer = f"/relationships/{relationship_id}"
        receipts[pointer] = _receipt(
            fixture,
            claim_id=facts_claim,
            decision_at=decision_at,
            source_view=source_view,
            output_pointer=pointer,
            audit_bundles=audit_bundles,
            verification_bundle=verification_bundle,
            contexts=tuple(contexts),
            value={
                "relationship_id": relationship_id,
                "fact_ids": tuple(context.fact.fact_id for context in contexts),
            },
        )

    state_receipts: dict[tuple[str, str, str, str, str], str] = {}
    for state in analysis.states:
        pointer = f"/state_summary/{_state_identifier(state.fact_key)}"
        contexts = tuple(
            analytic_by_id[identifier]
            for identifier in state.supporting_fact_ids + state.conflicting_fact_ids
        )
        state_receipts[state.fact_key] = _receipt(
            fixture,
            claim_id="operational_evidence_state",
            decision_at=decision_at,
            source_view=source_view,
            output_pointer=pointer,
            audit_bundles=audit_bundles,
            verification_bundle=verification_bundle,
            contexts=contexts,
            value=asdict(state),
        )
        receipts[pointer] = state_receipts[state.fact_key]

    change_receipts: dict[str, str] = {}
    for change in analysis.changes:
        pointer = f"/changes/{change.change_id}"
        contexts = tuple(
            audit_by_id[identifier]
            for identifier in (change.before_fact_id, change.after_fact_id)
            if identifier is not None and identifier in audit_by_id
        )
        change_receipts[change.change_id] = _receipt(
            fixture,
            claim_id="operational_change_graph",
            decision_at=decision_at,
            source_view=source_view,
            output_pointer=pointer,
            audit_bundles=audit_bundles,
            verification_bundle=verification_bundle,
            contexts=contexts,
            value=asdict(change),
        )
        receipts[pointer] = change_receipts[change.change_id]

    exclusion_receipts: dict[str, str] = {}
    for exclusion in analysis.exclusions:
        pointer = f"/exclusions/{exclusion.exclusion_id}"
        exclusion_receipts[exclusion.exclusion_id] = _receipt(
            fixture,
            claim_id="operational_data_boundary_refusals",
            decision_at=decision_at,
            source_view=source_view,
            output_pointer=pointer,
            audit_bundles=audit_bundles,
            verification_bundle=verification_bundle,
            contexts=(audit_by_item[exclusion.evidence_item_id],),
            value=asdict(exclusion),
            disposition="excluded",
            role="filter",
        )
        receipts[pointer] = exclusion_receipts[exclusion.exclusion_id]

    refusal_receipts: dict[str, str] = {}
    for refusal in analysis.refusals:
        pointer = refusal.output_pointer
        context = audit_by_id.get(refusal.affected_id) or audit_by_item.get(refusal.affected_id)
        if context is None:
            raise ValueError("operational-refusal-context-missing")
        refusal_receipts[refusal.refusal_id] = _receipt(
            fixture,
            claim_id="operational_data_boundary_refusals",
            decision_at=decision_at,
            source_view=source_view,
            output_pointer=pointer,
            audit_bundles=audit_bundles,
            verification_bundle=verification_bundle,
            contexts=(context,),
            value=asdict(refusal),
            disposition="refused",
            role="refusal",
        )
        receipts[pointer] = refusal_receipts[refusal.refusal_id]

    analysis = with_state_receipts(
        analysis,
        state_receipts=state_receipts,
        change_receipts=change_receipts,
        exclusion_receipts=exclusion_receipts,
        refusal_receipts=refusal_receipts,
    )
    state_by_key = {row.fact_key: row for row in analysis.states}
    for item in analysis.queue:
        pointer = f"/reunderwriting_queue/{item.queue_id}"
        state = state_by_key[item.fact_key]
        contexts = tuple(
            analytic_by_id[identifier]
            for identifier in state.supporting_fact_ids + state.conflicting_fact_ids
        )
        receipts[pointer] = _receipt(
            fixture,
            claim_id="reunderwriting_queue",
            decision_at=decision_at,
            source_view=source_view,
            output_pointer=pointer,
            audit_bundles=audit_bundles,
            verification_bundle=verification_bundle,
            contexts=contexts,
            value=asdict(item),
        )

    policy_contexts = tuple(
        context
        for context in audit_contexts
        if context.fact.assertion_kind == "method-boundary-policy"
    )
    if len(policy_contexts) != 1:
        raise ValueError("operational-method-policy-context-invalid")
    method_pointer = "/refusals/method-boundary"
    receipts[method_pointer] = _receipt(
        fixture,
        claim_id="operational_method_boundary_refusal",
        decision_at=decision_at,
        source_view=source_view,
        output_pointer=method_pointer,
        audit_bundles=audit_bundles,
        verification_bundle=verification_bundle,
        contexts=policy_contexts,
        value={
            "state": "refused",
            "reason_code": "scalar-operational-judgement-prohibited",
        },
        disposition="refused",
        role="refusal",
    )
    validation_pointer = "/validation"
    receipts[validation_pointer] = _receipt(
        fixture,
        claim_id="synthetic_state_validation",
        decision_at=decision_at,
        source_view=source_view,
        output_pointer=validation_pointer,
        audit_bundles=audit_bundles,
        verification_bundle=verification_bundle,
        contexts=policy_contexts,
        value={
            "fact_count": len(analysis.facts),
            "state_count": len(analysis.states),
            "queue_count": len(analysis.queue),
        },
    )
    return OperationalBuiltState(
        cutoff_key,
        source_view,
        decision_at,
        selected_dataset_ids,
        analytic_bundles,
        audit_bundles,
        verification_bundle,
        analysis,
        MappingProxyType(dict(sorted(receipts.items()))),
    )
