from __future__ import annotations

from dataclasses import replace
from datetime import datetime

import pytest

from quant_allocator.evidence.checks import EvidenceRefusal
from quant_allocator.flagships.knowledge.operational_evidence import (
    build_operational_evidence_fixture,
    operational_source_bundle,
    operational_verification_bundle,
)
from quant_allocator.flagships.operational_change import (
    analyze_operational_evidence,
    build_operational_closure,
    persist_operational_receipt,
    verify_operational_receipt,
)


def _receipt_case():
    fixture = build_operational_evidence_fixture()
    decision_at = datetime.fromisoformat(
        dict(fixture.manifest.cutoff_items)["latest"].replace("Z", "+00:00")
    )
    selected = dict(fixture.manifest.source_view_items)["all-entitled"]
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
    envelope = operational_verification_bundle(
        fixture,
        selected_dataset_ids=selected,
        decision_at=decision_at,
        revision_mode="all-known-versions",
        include_unresolved=True,
    )
    analysis = analyze_operational_evidence(
        fixture,
        analytic_bundles=analytic,
        audit_bundles=audit,
        decision_at=decision_at,
    )
    state = analysis.states[0]
    context_by_id = {row.fact.fact_id: row for row in analysis.fact_contexts}
    contexts = tuple(
        context_by_id[identifier]
        for identifier in state.supporting_fact_ids + state.conflicting_fact_ids
    )
    value = {
        "fact_key": state.fact_key,
        "state": state.state,
        "reason_codes": state.reason_codes,
    }
    closure = build_operational_closure(
        fixture,
        claim_id="operational_evidence_state",
        decision_at=decision_at,
        access_view="all-entitled",
        output_pointer="/state_summary/0",
        source_bundles=audit,
        verification_bundle=envelope,
        contexts=contexts,
        value=value,
    )
    receipt_id = persist_operational_receipt(fixture.conn, closure)
    return fixture, audit, envelope, closure, receipt_id


def test_receipt_has_exact_field_pointers_and_verifies_through_wrapper() -> None:
    fixture, audit, envelope, closure, receipt_id = _receipt_case()
    verify_operational_receipt(
        fixture.conn,
        receipt_id=receipt_id,
        source_bundles=audit,
        verification_bundle=envelope,
        closure=closure,
    )
    refs = fixture.conn.execute(
        "SELECT source_schema_id,source_field,reference_type,role,disposition "
        "FROM receipt_reference WHERE receipt_id=?",
        (receipt_id,),
    ).fetchall()
    assert refs
    assert all(row["source_field"] != "/" for row in refs)
    assert {row["role"] for row in refs} == {"input"}
    assert {row["disposition"] for row in refs} == {"included"}
    assert {row["reference_type"] for row in refs} >= {
        "dataset-observation",
        "dataset-version",
        "evidence-item",
        "evidence-right",
        "evidence-span",
        "snapshot",
        "source-record",
    }


def test_wrong_pointer_bundle_or_value_refuses_receipt_closure() -> None:
    fixture, audit, envelope, closure, receipt_id = _receipt_case()
    with pytest.raises(EvidenceRefusal, match="operational-receipt-header-mismatch"):
        verify_operational_receipt(
            fixture.conn,
            receipt_id=receipt_id,
            source_bundles=audit,
            verification_bundle=envelope,
            closure=replace(closure, output_pointer="/state_summary/wrong"),
        )
    with pytest.raises(EvidenceRefusal, match="operational-receipt-source-order-mismatch"):
        verify_operational_receipt(
            fixture.conn,
            receipt_id=receipt_id,
            source_bundles=tuple(reversed(audit[:-1])),
            verification_bundle=envelope,
            closure=closure,
        )


def test_source_view_order_missing_and_duplicate_bundles_refuse() -> None:
    fixture, audit, envelope, closure, _ = _receipt_case()
    with pytest.raises(EvidenceRefusal, match="operational-receipt-source-order-mismatch"):
        verify_operational_receipt(
            fixture.conn,
            receipt_id=persist_operational_receipt(
                fixture.conn,
                replace(closure, ordered_source_bundles=tuple(reversed(closure.ordered_source_bundles))),
            ),
            source_bundles=tuple(reversed(audit)),
            verification_bundle=envelope,
            closure=replace(
                closure, ordered_source_bundles=tuple(reversed(closure.ordered_source_bundles))
            ),
        )
    with pytest.raises(EvidenceRefusal, match="operational-receipt-source-order-mismatch"):
        verify_operational_receipt(
            fixture.conn,
            receipt_id=persist_operational_receipt(fixture.conn, closure),
            source_bundles=audit[:-1],
            verification_bundle=envelope,
            closure=closure,
        )
    with pytest.raises(EvidenceRefusal, match="operational-source-bundle-duplicate"):
        verify_operational_receipt(
            fixture.conn,
            receipt_id=persist_operational_receipt(fixture.conn, closure),
            source_bundles=(*audit, audit[0]),
            verification_bundle=envelope,
            closure=closure,
        )


def test_unrelated_valid_relationship_id_refuses_exact_fact_context() -> None:
    fixture, audit, envelope, closure, _ = _receipt_case()
    expected_ids = {
        binding.entity_relationship_id
        for binding in closure.fact_bindings
        if binding.entity_relationship_id is not None
    }
    assert expected_ids
    unrelated = fixture.conn.execute(
        "SELECT entity_relationship_id FROM entity_relationship "
        f"WHERE entity_relationship_id NOT IN ({','.join('?' for _ in expected_ids)}) "
        "ORDER BY entity_relationship_id LIMIT 1",
        tuple(sorted(expected_ids)),
    ).fetchone()[0]
    references = tuple(
        replace(ref, reference_id=unrelated)
        if ref.reference_type == "entity-relationship"
        else ref
        for ref in closure.references
    )
    bindings = tuple(
        replace(binding, entity_relationship_id=unrelated)
        if binding.entity_relationship_id is not None
        else binding
        for binding in closure.fact_bindings
    )
    changed = replace(closure, references=references, fact_bindings=bindings)
    receipt_id = persist_operational_receipt(fixture.conn, changed)
    with pytest.raises(EvidenceRefusal, match="operational-receipt-relationship-context-mismatch"):
        verify_operational_receipt(
            fixture.conn,
            receipt_id=receipt_id,
            source_bundles=audit,
            verification_bundle=envelope,
            closure=changed,
        )


def test_field_span_substitution_refuses_exact_source_pointer_binding() -> None:
    fixture, audit, envelope, closure, _ = _receipt_case()
    span_references = [
        reference for reference in closure.references if reference.reference_type == "evidence-span"
    ]
    target = span_references[0]
    substitute = next(
        reference
        for reference in span_references
        if reference.reference_id != target.reference_id
        and reference.source_field != target.source_field
    )
    changed = replace(
        closure,
        references=tuple(
            replace(reference, reference_id=substitute.reference_id)
            if reference == target
            else reference
            for reference in closure.references
        ),
    )
    receipt_id = persist_operational_receipt(fixture.conn, changed)

    with pytest.raises(EvidenceRefusal, match="operational-receipt-span-context-mismatch"):
        verify_operational_receipt(
            fixture.conn,
            receipt_id=receipt_id,
            source_bundles=audit,
            verification_bundle=envelope,
            closure=changed,
        )


def test_field_span_cross_fact_substitution_refuses_exact_item_binding() -> None:
    fixture, audit, envelope, closure, _ = _receipt_case()
    span_references = [
        reference for reference in closure.references if reference.reference_type == "evidence-span"
    ]
    target = span_references[0]
    target_item = fixture.conn.execute(
        "SELECT evidence_item_id FROM evidence_span WHERE evidence_span_id=?",
        (target.reference_id,),
    ).fetchone()[0]
    substitute = next(
        reference
        for reference in span_references
        if reference.source_field == target.source_field
        and fixture.conn.execute(
            "SELECT evidence_item_id FROM evidence_span WHERE evidence_span_id=?",
            (reference.reference_id,),
        ).fetchone()[0]
        != target_item
    )
    changed = replace(
        closure,
        references=tuple(
            replace(reference, reference_id=substitute.reference_id)
            if reference == target
            else reference
            for reference in closure.references
        ),
    )
    receipt_id = persist_operational_receipt(fixture.conn, changed)

    with pytest.raises(EvidenceRefusal, match="operational-receipt-span-context-mismatch"):
        verify_operational_receipt(
            fixture.conn,
            receipt_id=receipt_id,
            source_bundles=audit,
            verification_bundle=envelope,
            closure=changed,
        )
