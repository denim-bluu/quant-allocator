import hashlib
import json
from collections import Counter
from dataclasses import FrozenInstanceError, fields, replace
from datetime import UTC, datetime
from inspect import signature

import pytest
import quant_allocator.evidence.fixtures.terms as terms_fixtures_module
import quant_allocator.evidence.terms as terms_module

from quant_allocator.evidence.fixtures.terms import (
    P4_AUTHORED_NEGATIVE_CASE_IDS,
    P4_DOCUMENT_DATASETS,
    P4_METHOD_POLICY_DATASET,
    P4_NEGATIVE_DATASET,
    P4_NEGATIVE_BUNDLE_CASES,
    P4_POSITIVE_CASE_IDS,
    P4_POSITIVE_ENTITY_RECORDS,
    P4_POSITIVE_SCENARIO_IDS,
    P4_PROJECTION_KINDS,
    P4_SCENARIO_DATASETS,
    P4_SCENARIO_CONTEXTS,
    P4_SCENARIO_FAMILY_BY_ID,
    P4_TERMS_CUTOFFS,
    P4_TOPOLOGY_ADVERSARY_IDS,
    build_p4_method_policy_bundle,
    build_p4_terms_bundle,
    build_terms_fixture,
    p4_method_policy_bundle_request,
    p4_terms_bundle_request,
    p4_terms_negative_bundle_request,
)
from quant_allocator.evidence.checks import EvidenceRefusal
from quant_allocator.evidence.lineage import resolve_span
from quant_allocator.evidence.model import (
    DatasetSliceRequest,
    SnapshotBundleRequest,
    canonical_bytes,
    normalize_utc,
)
from quant_allocator.evidence.schema import connect, initialize
from quant_allocator.evidence.snapshot import as_known_bundle

from quant_allocator.evidence.terms import (
    P4TermProjection,
    P4TermProjectionSet,
    P4ProjectionLineage,
    PredecessorRequestScaffoldRecord,
    load_p4_term_projections,
    load_predecessor_request_scaffold,
    validate_p4_positive_bundle_request,
    verify_p4_projection_receipt,
)


def _lineage(decision_at: str = "2024-01-31T23:59:59.000000Z") -> P4ProjectionLineage:
    digest = "0" * 64
    return P4ProjectionLineage(
        evidence_item_id=f"evidence:sha256:{digest}",
        evidence_span_id=f"span:sha256:{digest}",
        source_record_id=f"source-record:sha256:{digest}",
        dataset_observation_id=f"dataset-observation:sha256:{digest}",
        dataset_version_id=f"dataset-version:sha256:{digest}",
        evidence_right_id=f"right:sha256:{digest}",
        dataset_delivery_partition_id=f"dataset-partition:sha256:{digest}",
        dataset_observation_partition_link_id=f"dataset-observation-partition:sha256:{digest}",
        snapshot_digest=f"snapshot:sha256:{digest}",
        slice_receipt_id=f"receipt:sha256:{digest}",
        join_receipt_id=f"receipt:sha256:{'1' * 64}",
        decision_at=decision_at,
        source_schema_id="schema:p4-scenario-input-v1",
        source_field="/source_text",
    )


def _projection(payload) -> P4TermProjection:
    return P4TermProjection(
        projection_id=f"p4-term-projection:sha256:{'2' * 64}",
        projection_kind="scenario_input",
        record_key="scenario:p4-p1-opening-nav",
        scenario_id="p4-p1-opening-nav",
        document_key=None,
        payload=payload,
        lineage=_lineage(),
        projection_receipt_id=f"receipt:sha256:{'3' * 64}",
    )


def _built_terms_fixture():
    conn = connect()
    initialize(conn)
    build_terms_fixture(conn)
    return conn


def _projection_set_with_rows(projection_set, rows):
    rows = tuple(rows)
    projection_digest = hashlib.sha256(
        canonical_bytes(
            tuple(
                {
                    "projection_id": row.projection_id,
                    "projection_kind": row.projection_kind,
                    "record_key": row.record_key,
                    "scenario_id": row.scenario_id,
                    "document_key": row.document_key,
                    "payload": row.payload,
                    "lineage": row.lineage,
                    "projection_receipt_id": row.projection_receipt_id,
                }
                for row in rows
            )
        )
    ).hexdigest()
    return replace(projection_set, rows=rows, projection_digest=projection_digest)


def test_p29_scaffolds_bind_only_original_request_and_source_closure() -> None:
    conn = _built_terms_fixture()
    context = "funded-private-partnership"
    amended = load_p4_term_projections(
        conn, build_p4_terms_bundle(conn, cutoff_name="amended", access_context=context)
    )
    side_letter = load_p4_term_projections(
        conn,
        build_p4_terms_bundle(conn, cutoff_name="side-letter", access_context=context),
    )

    p29b = load_predecessor_request_scaffold(
        conn, amended, "scaffold:p4-p29b-from-p29a"
    )
    p29c = load_predecessor_request_scaffold(
        conn, side_letter, "scaffold:p4-p29c-from-p29b"
    )

    assert p29b.expected_predecessor_scenario_id == "p4-p29a"
    assert p29b.predecessor_bundle_request.decision_at == P4_TERMS_CUTOFFS["early"]
    assert p29c.expected_predecessor_scenario_id == "p4-p29b"
    assert p29c.predecessor_bundle_request.decision_at == P4_TERMS_CUTOFFS["amended"]
    assert not any(
        row.projection_kind == "predecessor_request_scaffold"
        and row.payload["value"]["expected_predecessor_scenario_id"] == "p4-p29a"
        for row in load_p4_term_projections(
            conn, build_p4_terms_bundle(conn, cutoff_name="early", access_context=context)
        ).rows
    )

    forbidden = {
        "predecessor_result_id",
        "predecessor_result_receipt_id",
        "predecessor_result_value_digest",
        "predecessor_projection_set_digest",
        "predecessor_closing_state_fingerprint",
        "predecessor_verification_envelope",
    }
    for projection_set, scaffold in ((amended, p29b), (side_letter, p29c)):
        row = projection_set.require_record(scaffold.projection_id)
        value = row.payload["value"]
        manifests = conn.execute(
            "SELECT request_json FROM snapshot_bundle_manifest WHERE request_json=?",
            (value["predecessor_request_json"],),
        ).fetchall()
        assert len(manifests) == 1
        manifest = manifests[0]
        assert manifest["request_json"] == value["predecessor_request_json"]
        assert manifest["request_json"].encode() == canonical_bytes(
            scaffold.predecessor_bundle_request
        )
        assert forbidden.isdisjoint(value)


def test_p29_opening_reserve_lots_preserve_cross_period_identity_and_balances() -> None:
    conn = _built_terms_fixture()
    context = "funded-private-partnership"
    amended = load_p4_term_projections(
        conn, build_p4_terms_bundle(conn, cutoff_name="amended", access_context=context)
    )
    side_letter = load_p4_term_projections(
        conn,
        build_p4_terms_bundle(conn, cutoff_name="side-letter", access_context=context),
    )

    values = {
        row.record_key: row.payload["value"]
        for row in (*amended.rows, *side_letter.rows)
        if row.projection_kind in {"deal_cash_lot", "opening_reserve_lot"}
    }
    a_cash = values[f"deal-cash-lot:p4-p29a:a:{context}"]
    b_cash = values[f"deal-cash-lot:p4-p29b:b:{context}"]
    a_amended = values[f"opening-reserve-lot:p4-p29b:a:{context}"]
    a_side_letter = values[f"opening-reserve-lot:p4-p29c:a:{context}"]
    b_side_letter = values[f"opening-reserve-lot:p4-p29c:b:{context}"]
    assert {
        key: a_amended[key]
        for key in (
            "lot_id",
            "source_cash_lot_id",
            "source_event_id",
            "source_allocation_id",
            "deal_id",
            "currency",
        )
    } == {
        key: a_side_letter[key]
        for key in (
            "lot_id",
            "source_cash_lot_id",
            "source_event_id",
            "source_allocation_id",
            "deal_id",
            "currency",
        )
    }
    assert (a_amended["economic_balance"], a_amended["settled_balance"]) == (
        "20",
        "20",
    )
    assert (a_side_letter["economic_balance"], a_side_letter["settled_balance"]) == (
        "15",
        "15",
    )
    assert (b_side_letter["economic_balance"], b_side_letter["settled_balance"]) == (
        "10",
        "10",
    )
    assert (
        a_cash["lot_id"],
        a_cash["source_event"],
        a_cash["source_allocation_id"],
        a_cash["deal_id"],
        a_cash["currency"],
        a_cash["economic_balance"],
        a_cash["settled_balance"],
    ) == (
        "lot:p4-p29a:a-cash",
        "event:p4-p29a:realization",
        "allocation:p4-p29a:a-reserve",
        "deal:A",
        "USD",
        "120",
        "120",
    )
    assert (
        b_cash["lot_id"],
        b_cash["source_event"],
        b_cash["source_allocation_id"],
        b_cash["deal_id"],
        b_cash["currency"],
        b_cash["economic_balance"],
        b_cash["settled_balance"],
    ) == (
        "lot:p4-p29b:b-cash",
        "event:p4-p29b:reserve-add",
        "allocation:p4-p29b:b-reserve",
        "deal:B",
        "USD",
        "10",
        "10",
    )


@pytest.mark.parametrize(
    ("field", "replacement"),
    (
        ("expected_predecessor_scenario_id", "p4-p29b"),
        ("predecessor_cutoff", "2024-01-30T23:59:59.000000Z"),
        ("predecessor_request_digest", "0" * 64),
        ("predecessor_request_json", "{}"),
    ),
)
def test_predecessor_scaffold_refuses_control_mutations(field, replacement) -> None:
    conn = _built_terms_fixture()
    projection_set = load_p4_term_projections(
        conn,
        build_p4_terms_bundle(
            conn,
            cutoff_name="amended",
            access_context="funded-private-partnership",
        ),
    )
    row = next(
        row
        for row in projection_set.rows
        if row.record_key.startswith("scaffold:p4-p29b-from-p29a:")
    )
    value = dict(row.payload["value"])
    value[field] = replacement
    with pytest.raises(EvidenceRefusal):
        terms_module._validate_predecessor_request_closure(
            value,
            "scaffold:p4-p29b-from-p29a",
            "p4-p29a",
            "early",
            "funded-private-partnership",
        )


def test_predecessor_scaffold_refuses_continuity_balance_mutation_after_reseal() -> None:
    conn = _built_terms_fixture()
    projection_set = load_p4_term_projections(
        conn,
        build_p4_terms_bundle(
            conn,
            cutoff_name="amended",
            access_context="funded-private-partnership",
        ),
    )
    lot = next(
        row
        for row in projection_set.rows
        if row.record_key.startswith("opening-reserve-lot:p4-p29b:a:")
    )
    payload = dict(lot.payload)
    value = dict(payload["value"])
    value["settled_balance"] = "19"
    payload["value"] = value
    mutated = replace(lot, payload=payload)
    mutated_set = _projection_set_with_rows(
        projection_set,
        (mutated if row is lot else row for row in projection_set.rows),
    )

    with pytest.raises(EvidenceRefusal):
        terms_module._validate_p29_continuity(
            mutated_set, "funded-private-partnership", "amended"
        )


@pytest.mark.parametrize("mutation", ("missing", "duplicate", "cross-cutoff"))
def test_predecessor_scaffold_refuses_cardinality_and_cross_cutoff(mutation) -> None:
    conn = _built_terms_fixture()
    projection_set = load_p4_term_projections(
        conn,
        build_p4_terms_bundle(
            conn,
            cutoff_name="amended",
            access_context="funded-private-partnership",
        ),
    )
    scaffold = next(
        row
        for row in projection_set.rows
        if row.record_key.startswith("scaffold:p4-p29b-from-p29a:")
    )
    if mutation == "missing":
        rows = tuple(row for row in projection_set.rows if row is not scaffold)
    elif mutation == "duplicate":
        rows = (
            *projection_set.rows,
            replace(scaffold, projection_id=f"p4-term-projection:sha256:{'f' * 64}"),
        )
    else:
        projection_set = replace(
            projection_set,
            decision_at=normalize_utc(P4_TERMS_CUTOFFS["side-letter"]),
        )
        rows = projection_set.rows
    mutated_set = _projection_set_with_rows(projection_set, rows)
    with pytest.raises(EvidenceRefusal):
        load_predecessor_request_scaffold(
            conn, mutated_set, "scaffold:p4-p29b-from-p29a"
        )


def test_predecessor_scaffold_requires_persisted_original_bundle_manifest() -> None:
    conn = _built_terms_fixture()
    projection_set = load_p4_term_projections(
        conn,
        build_p4_terms_bundle(
            conn,
            cutoff_name="amended",
            access_context="funded-private-partnership",
        ),
    )
    row = next(
        row
        for row in projection_set.rows
        if row.record_key.startswith("scaffold:p4-p29b-from-p29a:")
    )
    request_json = row.payload["value"]["predecessor_request_json"]
    conn.execute("DROP TRIGGER immutable_delete_snapshot_bundle_manifest")
    conn.execute(
        "DELETE FROM snapshot_bundle_manifest WHERE request_json=?", (request_json,)
    )

    with pytest.raises(EvidenceRefusal):
        load_predecessor_request_scaffold(
            conn, projection_set, "scaffold:p4-p29b-from-p29a"
        )


@pytest.mark.parametrize(
    "field",
    (
        "evidence_item_id",
        "evidence_span_id",
        "source_record_id",
        "dataset_observation_id",
        "dataset_version_id",
        "evidence_right_id",
        "dataset_delivery_partition_id",
        "dataset_observation_partition_link_id",
        "snapshot_digest",
        "slice_receipt_id",
        "join_receipt_id",
    ),
)
def test_predecessor_scaffold_refuses_resealed_lineage_mutations(field) -> None:
    conn = _built_terms_fixture()
    projection_set = load_p4_term_projections(
        conn,
        build_p4_terms_bundle(
            conn,
            cutoff_name="amended",
            access_context="funded-private-partnership",
        ),
    )
    scaffold = next(
        row
        for row in projection_set.rows
        if row.record_key.startswith("scaffold:p4-p29b-from-p29a:")
    )
    namespace = getattr(scaffold.lineage, field).split(":", 1)[0]
    mutated = replace(
        scaffold,
        lineage=replace(scaffold.lineage, **{field: f"{namespace}:sha256:{'f' * 64}"}),
    )
    with pytest.raises(EvidenceRefusal):
        terms_module._validate_predecessor_projection_closure(mutated, scaffold)


def test_predecessor_scaffold_refuses_resealed_projection_receipt_mutation() -> None:
    conn = _built_terms_fixture()
    projection_set = load_p4_term_projections(
        conn,
        build_p4_terms_bundle(
            conn,
            cutoff_name="amended",
            access_context="funded-private-partnership",
        ),
    )
    scaffold = next(
        row
        for row in projection_set.rows
        if row.record_key.startswith("scaffold:p4-p29b-from-p29a:")
    )
    mutated = replace(
        scaffold, projection_receipt_id=f"receipt:sha256:{'f' * 64}"
    )
    with pytest.raises(EvidenceRefusal):
        terms_module._validate_predecessor_projection_closure(mutated, scaffold)


def test_predecessor_scaffold_refuses_resealed_row_reordering() -> None:
    conn = _built_terms_fixture()
    projection_set = load_p4_term_projections(
        conn,
        build_p4_terms_bundle(
            conn,
            cutoff_name="amended",
            access_context="funded-private-partnership",
        ),
    )
    targets = tuple(
        row
        for row in projection_set.rows
        if row.record_key.startswith(
            ("opening-reserve-lot:p4-p29b:a:", "deal-cash-lot:p4-p29b:b:")
        )
    )
    replacements = []
    for target, order in zip(targets, reversed(tuple(row.payload["value"]["continuity_order"] for row in targets))):
        payload = dict(target.payload)
        value = dict(payload["value"])
        value["continuity_order"] = order
        payload["value"] = value
        replacements.append(replace(target, payload=payload))
    replacement_by_id = {row.projection_id: row for row in replacements}
    mutated_set = _projection_set_with_rows(
        projection_set,
        (replacement_by_id.get(row.projection_id, row) for row in projection_set.rows),
    )
    with pytest.raises(EvidenceRefusal):
        terms_module._validate_p29_continuity(
            mutated_set, "funded-private-partnership", "amended"
        )


@pytest.mark.parametrize(
    "mutation",
    (
        "source-value",
        "source-order",
        "right",
        "purpose",
        "join-key",
        "join-order",
        "join-policy",
        "partial",
    ),
)
def test_predecessor_scaffold_refuses_resealed_request_closure_mutations(
    mutation,
) -> None:
    conn = _built_terms_fixture()
    projection_set = load_p4_term_projections(
        conn,
        build_p4_terms_bundle(
            conn,
            cutoff_name="amended",
            access_context="funded-private-partnership",
        ),
    )
    scaffold = next(
        row
        for row in projection_set.rows
        if row.record_key.startswith("scaffold:p4-p29b-from-p29a:")
    )
    value = dict(scaffold.payload["value"])
    if mutation == "partial":
        value.pop("predecessor_join_policy")
    else:
        request = json.loads(value["predecessor_request_json"])
        if mutation == "source-value":
            request["sources"][0]["canonical_entity_ids"] = [
                "legal-entity:p4-mutated"
            ]
        elif mutation == "source-order":
            request["sources"].reverse()
        elif mutation == "right":
            request["sources"][0]["evidence_right_id"] = f"right:sha256:{'f' * 64}"
        elif mutation == "purpose":
            request["sources"][0]["licence_purpose"] = "mutated-purpose"
        elif mutation == "join-key":
            request["join_keys"] = ["source_record_id"]
        elif mutation == "join-order":
            request["join_keys"] = ["source_record_id", "canonical_entity_id"]
        else:
            request["join_policy"] = "mutated-policy"
        request_json = canonical_bytes(request).decode()
        value["predecessor_request_json"] = request_json
        value["predecessor_request_digest"] = hashlib.sha256(
            request_json.encode()
        ).hexdigest()
        value["predecessor_source_dataset_ids"] = [
            source["dataset_id"] for source in request["sources"]
        ]
        value["predecessor_join_keys"] = request["join_keys"]
        value["predecessor_join_policy"] = request["join_policy"]
    with pytest.raises(EvidenceRefusal):
        terms_module._validate_predecessor_request_closure(
            value,
            "scaffold:p4-p29b-from-p29a",
            "p4-p29a",
            "early",
            "funded-private-partnership",
        )


@pytest.mark.parametrize(
    ("cutoff_name", "record_prefix", "field"),
    tuple(
        (cutoff_name, record_prefix, field)
        for cutoff_name, record_prefix in (
            ("amended", "deal-cash-lot:p4-p29a:a:"),
            ("amended", "deal-cash-lot:p4-p29b:b:"),
        )
        for field in (
            "lot_id",
            "source_event",
            "source_allocation_id",
            "deal_id",
            "currency",
            "economic_balance",
            "settled_balance",
        )
    )
    + tuple(
        (cutoff_name, record_prefix, field)
        for cutoff_name, record_prefix in (
            ("amended", "opening-reserve-lot:p4-p29b:a:"),
            ("side-letter", "opening-reserve-lot:p4-p29c:a:"),
            ("side-letter", "opening-reserve-lot:p4-p29c:b:"),
        )
        for field in (
            "lot_id",
            "source_cash_lot_id",
            "source_event_id",
            "source_allocation_id",
            "deal_id",
            "currency",
            "economic_balance",
            "settled_balance",
        )
    ),
)
def test_predecessor_scaffold_refuses_resealed_continuity_field_mutations(
    cutoff_name, record_prefix, field
) -> None:
    conn = _built_terms_fixture()
    projection_set = load_p4_term_projections(
        conn,
        build_p4_terms_bundle(
            conn,
            cutoff_name=cutoff_name,
            access_context="funded-private-partnership",
        ),
    )
    target = next(row for row in projection_set.rows if row.record_key.startswith(record_prefix))
    payload = dict(target.payload)
    value = dict(payload["value"])
    value[field] = "mutated"
    payload["value"] = value
    mutated = replace(target, payload=payload)
    mutated_set = _projection_set_with_rows(
        projection_set,
        (mutated if row is target else row for row in projection_set.rows),
    )
    with pytest.raises(EvidenceRefusal):
        terms_module._validate_p29_continuity(
            mutated_set, "funded-private-partnership", cutoff_name
        )


def test_p29_continuity_validator_refuses_unexpected_unique_extra_directly() -> None:
    conn = _built_terms_fixture()
    projection_set = load_p4_term_projections(
        conn,
        build_p4_terms_bundle(
            conn,
            cutoff_name="amended",
            access_context="funded-private-partnership",
        ),
    )
    source = next(row for row in projection_set.rows if row.projection_kind == "deal_cash_lot")
    extra = replace(
        source,
        projection_id=f"p4-term-projection:sha256:{'f' * 64}",
        record_key="deal-cash-lot:p4-p29-extra:funded-private-partnership",
    )
    mutated_set = _projection_set_with_rows(projection_set, (*projection_set.rows, extra))
    with pytest.raises(EvidenceRefusal):
        terms_module._validate_p29_continuity(
            mutated_set, "funded-private-partnership", "amended"
        )


@pytest.mark.parametrize("mutation", ("missing", "partial", "duplicate"))
def test_p29_continuity_validator_requires_exact_cardinality_directly(mutation) -> None:
    conn = _built_terms_fixture()
    projection_set = load_p4_term_projections(
        conn,
        build_p4_terms_bundle(
            conn,
            cutoff_name="amended",
            access_context="funded-private-partnership",
        ),
    )
    target = next(
        row
        for row in projection_set.rows
        if row.record_key.startswith("opening-reserve-lot:p4-p29b:a:")
    )
    if mutation == "missing":
        rows = tuple(row for row in projection_set.rows if row is not target)
    elif mutation == "duplicate":
        rows = (
            *projection_set.rows,
            replace(target, projection_id=f"p4-term-projection:sha256:{'f' * 64}"),
        )
    else:
        payload = dict(target.payload)
        value = dict(payload["value"])
        value.pop("source_cash_lot_id")
        payload["value"] = value
        partial = replace(target, payload=payload)
        rows = tuple(partial if row is target else row for row in projection_set.rows)
    mutated_set = _projection_set_with_rows(projection_set, rows)
    with pytest.raises(EvidenceRefusal):
        terms_module._validate_p29_continuity(
            mutated_set, "funded-private-partnership", "amended"
        )


def test_predecessor_projection_closure_validator_is_directly_load_bearing() -> None:
    conn = _built_terms_fixture()
    projection_set = load_p4_term_projections(
        conn,
        build_p4_terms_bundle(
            conn,
            cutoff_name="amended",
            access_context="funded-private-partnership",
        ),
    )
    scaffold = next(
        row
        for row in projection_set.rows
        if row.record_key.startswith("scaffold:p4-p29b-from-p29a:")
    )
    mutated = replace(
        scaffold,
        projection_receipt_id=f"receipt:sha256:{'f' * 64}",
    )
    with pytest.raises(EvidenceRefusal):
        terms_module._validate_predecessor_projection_closure(mutated, scaffold)


def test_every_held_case_has_complete_controlled_projection_inventory() -> None:
    conn = connect()
    initialize(conn)
    manifest = build_terms_fixture(conn)
    positive_rows = {
        row.projection_id: row
        for cutoff_name in P4_TERMS_CUTOFFS
        for access_context in P4_SCENARIO_DATASETS
        for row in load_p4_term_projections(
            conn,
            build_p4_terms_bundle(
                conn,
                cutoff_name=cutoff_name,
                access_context=access_context,
            ),
        ).rows
    }.values()
    scenario_rows = tuple(
        row for row in positive_rows if row.projection_kind == "scenario_input"
    )
    scenario_ids = {row.scenario_id for row in scenario_rows}

    assert scenario_ids == set(P4_POSITIVE_SCENARIO_IDS)
    assert scenario_ids.isdisjoint(P4_NEGATIVE_BUNDLE_CASES)
    assert all(
        isinstance(row.payload["value"]["expected_full_precision"], str)
        and isinstance(row.payload["value"]["expected_settlement_precision"], str)
        and row.payload["value"]["calculation_policy_projection_key"]
        and isinstance(row.payload["value"]["dependency_projection_keys"], tuple)
        for row in scenario_rows
    )
    assert Counter(P4_SCENARIO_FAMILY_BY_ID.values())["p4-p1"] == 5
    assert len(P4_POSITIVE_CASE_IDS) == 43
    assert len(P4_POSITIVE_SCENARIO_IDS) == 47
    assert set(manifest.projection_counts) == set(P4_PROJECTION_KINDS)
    assert all(manifest.projection_counts[kind] > 0 for kind in P4_PROJECTION_KINDS)
    assert set(manifest.negative_bundle_results) == set(P4_NEGATIVE_BUNDLE_CASES)

    relation_types = {
        row.payload["value"]["relation_type"]
        for row in positive_rows
        if row.projection_kind == "term_relation"
    }
    method_rows = load_p4_term_projections(conn, build_p4_method_policy_bundle(conn)).rows
    policy_families = {
        row.payload["value"]["policy_family"]
        for row in (*positive_rows, *method_rows)
        if row.projection_kind
        in {
            "calculation_policy",
            "materiality_policy",
            "rounding_policy",
            "method_boundary_policy",
        }
    }
    lot_families = {
        row.payload["value"]["lot_family"]
        for row in positive_rows
        if row.projection_kind
        in {
            "deal_cash_lot",
            "opening_reserve_lot",
            "opening_carry_lot",
            "carry_return",
            "prior_lot_transition",
        }
    }
    assert relation_types == {
        "amends",
        "supersedes",
        "investor_override",
        "clarifies",
        "incorporates",
    }
    assert policy_families == {
        "calculation",
        "materiality",
        "rounding",
        "method-boundary",
    }
    assert lot_families == {
        "deal-cash",
        "opening-reserve",
        "opening-carry",
        "carry-return",
        "prior-transition",
    }

    for cutoff_name in P4_TERMS_CUTOFFS:
        for access_context in P4_SCENARIO_DATASETS:
            rows = load_p4_term_projections(
                conn,
                build_p4_terms_bundle(
                    conn,
                    cutoff_name=cutoff_name,
                    access_context=access_context,
                ),
            ).rows
            rows_by_key = {row.record_key: row for row in rows}
            assert len(rows_by_key) == len(rows)
            for row in (item for item in rows if item.projection_kind == "scenario_input"):
                value = row.payload["value"]
                calculation_key = value["calculation_policy_projection_key"]
                assert rows_by_key[calculation_key].projection_kind == "calculation_policy"
                dependency_keys = value["dependency_projection_keys"]
                assert len(dependency_keys) == len(set(dependency_keys))
                assert set(dependency_keys) <= set(rows_by_key)
                materiality_key = value["materiality_basis_projection_key"]
                if row.scenario_id in {"p4-p18", "p4-p33"}:
                    assert rows_by_key[materiality_key].projection_kind == (
                        "materiality_comparison_basis"
                    )
                else:
                    assert materiality_key is None

    for case_id in P4_AUTHORED_NEGATIVE_CASE_IDS:
        bundle = as_known_bundle(conn, p4_terms_negative_bundle_request(case_id=case_id))
        rows = tuple(row for slice_ in bundle.slices for row in slice_.rows)
        assert len(rows) == 1
        value = rows[0]["payload"]["value"]
        assert value["scenario_id"] == case_id
        assert isinstance(value["expected_refusal_family"], str)
        assert isinstance(value["adversarial_source"], str)


def test_critical_scenarios_have_exact_dependency_rows_and_controlled_values() -> None:
    conn = connect()
    initialize(conn)
    build_terms_fixture(conn)
    context = "shortlisted-nda"
    rows = load_p4_term_projections(
        conn,
        build_p4_terms_bundle(
            conn,
            cutoff_name="side-letter",
            access_context=context,
        ),
    ).rows
    rows_by_key = {row.record_key: row for row in rows}
    scenarios = {
        row.scenario_id: row
        for row in rows
        if row.projection_kind == "scenario_input"
    }
    expected_dependencies = {
        "p4-p13": (
            f"prior-carry-event:p4-p13:a-old:{context}",
            f"prior-carry-allocation:p4-p13:a-old:{context}",
            f"opening-carry-lot:p4-p13:a-old:{context}",
            f"prior-carry-event:p4-p13:b-old:{context}",
            f"prior-carry-allocation:p4-p13:b-old:{context}",
            f"opening-carry-lot:p4-p13:b-old:{context}",
            f"prior-lot-transition:p4-p13:a-current:{context}",
        ),
        "p4-p29a": (f"deal-cash-lot:p4-p29a:a:{context}",),
        "p4-p29b": (
            f"scaffold:p4-p29b-from-p29a:{context}",
            f"opening-reserve-lot:p4-p29b:a:{context}",
            f"prior-lot-transition:p4-p29b:a-release:{context}",
            f"deal-cash-lot:p4-p29b:b:{context}",
            f"prior-lot-transition:p4-p29b:b-add:{context}",
        ),
        "p4-p29c": (
            f"scaffold:p4-p29c-from-p29b:{context}",
            f"opening-reserve-lot:p4-p29c:a:{context}",
            f"opening-reserve-lot:p4-p29c:b:{context}",
            f"prior-lot-transition:p4-p29c:a-release:{context}",
            f"prior-lot-transition:p4-p29c:b-release:{context}",
        ),
        "p4-p30": (
            f"prior-carry-event:p4-p30:a-old:{context}",
            f"prior-carry-allocation:p4-p30:a-old:{context}",
            f"opening-carry-lot:p4-p30:a-paid:{context}",
            f"prior-carry-event:p4-p30:b-old:{context}",
            f"prior-carry-allocation:p4-p30:b-old:{context}",
            f"opening-carry-lot:p4-p30:b-escrow:{context}",
            f"prior-lot-transition:p4-p30:a-current:{context}",
            f"prior-lot-transition:p4-p30:b-current:{context}",
        ),
        "p4-p30b": (
            f"prior-carry-event:p4-p30b:a-old:{context}",
            f"prior-carry-allocation:p4-p30b:a-old:{context}",
            f"opening-carry-lot:p4-p30b:a-paid:{context}",
            f"prior-carry-event:p4-p30b:b-old:{context}",
            f"prior-carry-allocation:p4-p30b:b-old:{context}",
            f"opening-carry-lot:p4-p30b:b-escrow:{context}",
            f"carry-return:p4-p30b:a-historical:{context}",
            f"prior-lot-transition:p4-p30b:a-current:{context}",
            f"carry-return:p4-p30b:b-current:{context}",
        ),
        "p4-p30c": (
            f"prior-carry-event:p4-p30c:b-old:{context}",
            f"prior-carry-allocation:p4-p30c:b-old:{context}",
            f"opening-carry-lot:p4-p30c:b-escrow:{context}",
            f"carry-return:p4-p30c:b-historical:{context}",
            f"prior-lot-transition:p4-p30c:b-release:{context}",
        ),
    }
    assert {
        scenario_id: scenarios[scenario_id].payload["value"][
            "dependency_projection_keys"
        ]
        for scenario_id in expected_dependencies
    } == expected_dependencies
    assert all(key in rows_by_key for keys in expected_dependencies.values() for key in keys)
    kind_by_key_prefix = {
        "scaffold": "predecessor_request_scaffold",
        "deal-cash-lot": "deal_cash_lot",
        "opening-reserve-lot": "opening_reserve_lot",
        "prior-carry-event": "prior_carry_event",
        "prior-carry-allocation": "prior_carry_allocation",
        "opening-carry-lot": "opening_carry_lot",
        "carry-return": "carry_return",
        "prior-lot-transition": "prior_lot_transition",
    }
    for keys in expected_dependencies.values():
        for key in keys:
            assert rows_by_key[key].projection_kind == kind_by_key_prefix[
                key.split(":", 1)[0]
            ]
    expected_value_fields = {
        f"opening-carry-lot:p4-p13:a-old:{context}": {
            "paid": "18", "escrow": "0", "returned": "0", "deal_id": "deal:A"
        },
        f"opening-carry-lot:p4-p13:b-old:{context}": {
            "paid": "12", "escrow": "0", "returned": "0", "deal_id": "deal:B"
        },
        f"prior-lot-transition:p4-p13:a-current:{context}": {
            "opening": "0", "closing": "10", "deal_id": "deal:A"
        },
        f"deal-cash-lot:p4-p29a:a:{context}": {
            "amount": "120", "deal_id": "deal:A"
        },
        f"opening-reserve-lot:p4-p29b:a:{context}": {
            "original": "20", "remaining": "20", "deal_id": "deal:A"
        },
        f"opening-reserve-lot:p4-p29c:a:{context}": {
            "original": "20", "remaining": "15", "deal_id": "deal:A"
        },
        f"opening-reserve-lot:p4-p29c:b:{context}": {
            "original": "10", "remaining": "10", "deal_id": "deal:B"
        },
        f"opening-carry-lot:p4-p30:a-paid:{context}": {
            "paid": "20", "escrow": "0", "returned": "0", "deal_id": "deal:A"
        },
        f"opening-carry-lot:p4-p30:b-escrow:{context}": {
            "paid": "0", "escrow": "10", "returned": "0", "deal_id": "deal:B"
        },
        f"opening-carry-lot:p4-p30b:a-paid:{context}": {
            "paid": "12", "escrow": "0", "returned": "3", "deal_id": "deal:A"
        },
        f"opening-carry-lot:p4-p30b:b-escrow:{context}": {
            "paid": "0", "escrow": "11", "returned": "0", "deal_id": "deal:B"
        },
        f"carry-return:p4-p30b:a-historical:{context}": {
            "amount": "3", "target_bucket": "paid", "deal_id": "deal:A"
        },
        f"carry-return:p4-p30b:b-current:{context}": {
            "amount": "2", "target_bucket": "escrow", "deal_id": "deal:B"
        },
        f"opening-carry-lot:p4-p30c:b-escrow:{context}": {
            "paid": "0", "escrow": "9", "returned": "2", "deal_id": "deal:B"
        },
        f"prior-lot-transition:p4-p30c:b-release:{context}": {
            "opening": "9", "closing": "4", "deal_id": "deal:B"
        },
    }
    for key, expected_fields in expected_value_fields.items():
        value = rows_by_key[key].payload["value"]
        assert {field: value[field] for field in expected_fields} == expected_fields
    assert not any(
        rows_by_key[key].projection_kind == "opening_reserve_lot"
        for key in expected_dependencies["p4-p29a"]
    )
    assert {
        key: rows_by_key[key].payload["value"]["remaining"]
        for key in expected_dependencies["p4-p29c"]
        if rows_by_key[key].projection_kind == "opening_reserve_lot"
    } == {
        f"opening-reserve-lot:p4-p29c:a:{context}": "15",
        f"opening-reserve-lot:p4-p29c:b:{context}": "10",
    }
    assert scenarios["p4-p2"].payload["value"]["controlled_inputs"] == (
        "2023-01-31->2023-02-01:3650*.01*1 actual/365-fixed;"
        "2023-01-31->2023-03-02:900*.02*30 actual/360;"
        "2023-01-15->2023-02-15:1200*.03*30 30/360-US;"
        "2023-12-31->2024-01-01:36500*.01*1/365;"
        "2024-02-29->2024-03-01:36600*.01*1/366 ISDA",
    )
    p25_value = scenarios["p4-p25"].payload["value"]
    assert {
        key: p25_value[key]
        for key in (
            "controlled_inputs",
            "expected_full_precision",
            "expected_settlement_precision",
        )
    } == {
        "controlled_inputs": (
            "D=150;capital=100;preferred=8;c=.20;g=1;residual=40;"
            "typed_ordered_cash_lots=A105,B45;reserve=none",
        ),
        "expected_full_precision": (
            "aggregate_LP=140;aggregate_GP=10;per_deal_A=105,B=45;"
            "aggregate_cash_and_share_tie"
        ),
        "expected_settlement_precision": (
            "A:capital_LP100+preferred_LP5;"
            "B:preferred_LP3+catchup_GP2+residual_LP32+residual_GP8;"
            "every_line_has_cash_lot_and_deal"
        ),
    }


def test_all_scenario_triples_have_canonical_exact_values() -> None:
    expected = {
        "p4-p1-opening-nav": ("base=opening-nav;m=.036;days=10 actual/360;opening_nav=1000", "management_fee=1.00;base_substitution=false", "management_fee=1.00;projection_set=opening-nav"),
        "p4-p1-daily-nav": ("base=daily-nav;m=.036;days=10 actual/360;daily_nav=900 for days1-5,1100 for days6-10", "weighted_average_nav=1000;management_fee=1.00;base_substitution=false", "management_fee=1.00;projection_set=daily-nav"),
        "p4-p1-weighted-average-nav": ("base=weighted-average-nav;m=.036;days=10 actual/360;weighted_average_nav=1000", "management_fee=1.00;base_substitution=false", "management_fee=1.00;projection_set=weighted-average-nav"),
        "p4-p1-committed-capital": ("base=committed-capital;m=.036;days=10 actual/360;committed_capital=1200", "management_fee=1.20;base_substitution=false", "management_fee=1.20;projection_set=committed-capital"),
        "p4-p1-invested-capital": ("base=invested-capital;m=.036;days=10 actual/360;invested_capital=800", "management_fee=.80;base_substitution=false", "management_fee=.80;projection_set=invested-capital"),
        "p4-p2": ("2023-01-31->2023-02-01:3650*.01*1 actual/365-fixed;2023-01-31->2023-03-02:900*.02*30 actual/360;2023-01-15->2023-02-15:1200*.03*30 30/360-US;2023-12-31->2024-01-01:36500*.01*1/365;2024-02-29->2024-03-01:36600*.01*1/366 ISDA", "day_count_fees=.10,1.50,3.00,1.00,1.00;ISDA_parts=1.00+1.00;ISDA_sum=2.00", "day_count_fees=.10,1.50,3.00,1.00,1.00;year_split_sum=parts"),
        "p4-p3": ("H=105;K=104;V*=110;p=.20;hurdle=hard;combination=max", "T=max(H,K)=105;E=V*-T=5;P=pE=1", "T=105;E=5;P=1"),
        "p4-p4": ("H=103;K=105;V*=110;p=.20;hurdle=hard;combination=max", "T=max(H,K)=105;E=V*-T=5;P=pE=1", "T=105;E=5;P=1"),
        "p4-p5": ("H=105;O=100;K=104;V*=110;p=.20;hurdle=hard;combination=additive", "T=H+(K-O)=109;E=V*-T=1;P=.20;absolute_level_double_count=false", "T=109;E=1;P=.20"),
        "p4-p6": ("prior_threshold=P4-P5-T109;V*=114;p=.20;soft_bases=gain-over-hwm,gain-over-opening-nav,projected-C8", "after_crossing_E=5,10,8;P=1,2,1.6", "at_or_below_threshold_E=0;P=0"),
        "p4-p7": ("path=P4-P3;H=105;V*=110;P=1;update_clauses=post-fee,pre-fee;valuation=interim,crystallization", "post_fee_H_next=109;pre_fee_H_next=110;interim_H_next=105", "next_history_opening_H=exact_prior_close"),
        "p4-p8": ("series_A=100->110,H=100;series_B_new=105->110,H=105;p=.20;hurdle=none", "fee_A=2;fee_B=1;aggregate_fee=3;subscription_profit=0", "each_series_NAV_identity=exact;aggregate_NAV_identity=exact"),
        "p4-p9a": ("fund_fee=2;raw_liability_legacy=1.50;raw_liability_subscriber=1.00;subscriber_credit=.50;direction=credit", "final_liability_legacy=1.50;subscriber=.50;aggregate=2", "subscription_profit=0;series_and_aggregate_tie"),
        "p4-p9b": ("fund_fee=2;raw_liability_legacy=1.50;raw_liability_subscriber=0;subscriber_debit=.50;direction=debit", "final_liability_legacy=1.50;subscriber=.50;aggregate=2", "subscription_profit=0;series_and_aggregate_tie"),
        "p4-p10": ("deal=A;eligible_fee_amount=10;offset_rate=.80;liability_before=12;beneficiary=LP;one_fee_offset_event=after-contribution-realization-writeoff-before-reserve-preferred-tiers", "offset_benefit=8;liability_after=4;D_g_unchanged_without_contribution", "closing_liability_A=4;aggregate=4;next_opening_A=4;next_opening_aggregate=4;later_offset_event=false"),
        "p4-p11": ("typed_cash_lot=deal-A120;D_g=120;reserve_target=20;fee_offset=none;clawback=none;tiers_LP=90,GP=10", "reserve_line=A/source-lot,vehicle,20;tiers_consume=100;unrounded_identity=120=20+90+10", "reserve_settled_total=20;settled_allocated_total=120;cash_rounding_residual=0;reserve_common_settlement_count=1"),
        "p4-p12": ("D_g=120;reserve=none;clawback=none;gross_tiers_LP=100,GP=20;escrow_rate=.25", "LP=100;GP_gross=20;GP_paid=15;carry_escrow=5", "identity=120=100+15+5;GP_gross=20"),
        "p4-p13": ("opening_settled_cash_paid_lots=A-old18,B-old12;returned=0;prior_hypothetical_GP_paid=30;current_GP_allocation_bridge=A-current10;settled_permitted_ceiling=cZ_cash30;path_authored_current_lot=false", "opening_and_current_lot_layers_tie_per_deal_and_aggregate;Gnet_cash=40;cash_obligation_C=10;reverse_attribution=A-current10;obligations_A=10,B=0", "current_D_g_identity=unchanged;economic_entitlement_layer=unchanged;closing_to_next_opening_lots=exact"),
        "p4-p14": ("holdback=none;G0=0;L0=20;c=.20;g=1;cash>=5", "Y*=5;GP=5;cumulative_GP_share=5/25=.20", "GP=5;LP=0;full_catchup_complete"),
        "p4-p15": ("G0=0;L0=1;c=.20;g=.80;cash>entitlement", "Y*=1/3 at policy precision;GP=4/15;LP=1/15", "GP=4/15;LP=1/15;pre_settlement_rounding=false"),
        "p4-p16": ("amount=100 USD;rate=.80 EUR per USD;direction=direct;fixing=matching", "converted=80 EUR;conversion_count=1", "converted=80 EUR;declared_stage_count=1"),
        "p4-p17": ("amount=100 USD;rate=1.25 USD per EUR;direction=inverse;fixing=matching", "converted=80 EUR;conversion_count=1", "converted=80 EUR;declared_stage_count=1"),
        "p4-p18": ("baseline=100;counterfactual=105;absolute_threshold=5;equality_is_outside=false,true", "signed_delta=5;absolute_delta=5", "equality_false=inside;equality_true=outside"),
        "p4-p19": ("prior_H=120;crystallization_V*=110;P=2;reset=perpetual,periodic-post-fee", "perpetual_H_close=120;periodic_H_close=108", "next_opening_H=selected_exact_close"),
        "p4-p20": ("O=100;opening_clock=2026-01-01;crystallization=2026-07-01;post_fee_NAV=108;reset=never,each-crystallization-post-NAV", "never_O=100,clock=2026-01-01;each_O=108,clock=2026-07-01", "next_opening_base_and_clock=selected_exact_close"),
        "p4-p21": ("unitized:u0=10,hu=10,flow=+2units;cash-additive:H=100,subscription=20,redemption=5;none:flows=0", "unitized_H_close=120;cash_additive_H_close=115;none_H_close=100", "none_with_nonzero_flow=refuse"),
        "p4-p22": ("H=105;K=104;O=100;V*=110;p=.20;hurdle=soft;combination=max;base=gain-over-opening-NAV", "T=105;activated_base=10;P=2", "at_V*=105:P=0"),
        "p4-p23": ("same_profitable_interim_and_close;rules=event-only-date,period-end;events=named,unnamed", "interim_event_only_fee_and_HWM=unchanged;named_event_crystallizes_once;period_end_crystallizes_once", "each_crystallization_appends=one_state_transition"),
        "p4-p24": (
            "bases=opening-capital100,unreturned-contributions100;"
            "simple=.10*1 ACT/365 year;compound=.10*2 ACT/365 years;"
            "segments=30 days ACT/360,30 days 30/360-US,leap-year ISDA",
            "simple_accrual=10;compound_cumulative=21;"
            "each_segment=canonical_day_count_fraction;"
            "closing_preferred=opening_preferred+accrual",
            "simple_accrual=10;compound_cumulative=21;"
            "all_segment_amounts_settle_from_full_precision;"
            "closing_preferred_identity=exact",
        ),
        "p4-p28a": (
            "scope=whole-fund;deals=A,B;eligible_fees_A=6,B=4;"
            "offset_rate=.80;opening_liabilities_A=7,B=5;"
            "aggregate_eligible_fee=10;aggregate_opening_liability=12;"
            "current_tiers_allocations_distributions=complete_before_offset;"
            "offset_timing=period-end-before-sole-closing-state",
            "offsets_A=4.8,B=3.2;closing_liabilities_A=2.2,B=1.8;"
            "aggregate_offset=8;aggregate_closing_liability=4;"
            "current_D_g_tiers_allocations_distributions=unchanged",
            "next_opening_liabilities_A=2.2,B=1.8;aggregate=4;"
            "next_opening_complete_deal_and_aggregate_state=prior_close",
        ),
        "p4-p28b": (
            "scope=deal-by-deal;deals=A,B;eligible_fees_A=6,B=4;"
            "offset_rate=.80;opening_liabilities_A=7,B=5;"
            "aggregate_eligible_fee=10;aggregate_opening_liability=12;"
            "ordered_fee_offset_events=A,B;"
            "event_timing=after-distribution-before-sole-closing-state",
            "offsets_A=4.8,B=3.2;closing_liabilities_A=2.2,B=1.8;"
            "each_closing_deal_liability=sole_offset_liability_after;"
            "aggregate_offset=8;aggregate_closing_liability=4",
            "next_opening_liabilities_A=2.2,B=1.8;aggregate=4;"
            "next_opening_complete_deal_and_aggregate_state=prior_close;"
            "swapped_or_missing_deal_state=refuse-before-output",
        ),
        "p4-p25": ("D=150;capital=100;preferred=8;c=.20;g=1;residual=40;typed_ordered_cash_lots=A105,B45;reserve=none", "aggregate_LP=140;aggregate_GP=10;per_deal_A=105,B=45;aggregate_cash_and_share_tie", "A:capital_LP100+preferred_LP5;B:preferred_LP3+catchup_GP2+residual_LP32+residual_GP8;every_line_has_cash_lot_and_deal"),
        "p4-p26": ("scope=deal-by-deal;deal_A:D=60,capital=40,preferred=4,c=.20,g=1,residual=15", "deal_A_LP=40+4+12=56;deal_A_GP=1+3=4", "every_line_deal=A;deal_B_balances=unchanged"),
        "p4-p27": ("preferred=8;post_capital_cash=50;c=.20;g=1;carried_profit_bases=including-preferred,excluding-preferred", "including:catchup=2,residual_GP=8;excluding:catchup=0,carryable=42,residual_GP=8.4", "each_basis_GP_share=.20_of_own_denominator"),
        "p4-p28c": ("opening_liabilities_A=7,B=5;eligible_fee_A=6;offset_rate_A=.80;eligible_fee_B=0;operative_entries_A=1,B=0", "A_offset=4.8;A_close=2.2;B_close=5;aggregate_open=12;aggregate_close=7.2", "second_A_entry_or_any_B_entry_or_B_drift_or_wrong_aggregate=refuse"),
        "p4-p29a": ("period=first;predecessor_request=null;prior_result=null;derived_predecessor_envelope=null;opening_inventory=empty;deal_A_cash_lot=120;new_reserve=20", "generated_A_reserve_lot_original=20,remaining=20;add_transition=0->20;tiers_consume=100", "closing_reserve_A=20;aggregate=20;inventory_sum=20"),
        "p4-p29b": ("period=second;source_closed_predecessor_scaffold=P4-P29a-exact-request;prior_result=P4-P29a;release_input_id=stable-A-release,economic=5,settled=5,lot=A,event=A,deal=A,projection=A;D0=100;new_reserve_B=10", "predecessor_and_current_bundles_verify_at_own_cutoffs;A_transition_economic_and_settled=20->15;release_cash_lot_A=5;D_g=105;B_add=0->10;tiers_consume=95", "next_opening_dual_layers=prior_close;closing_A=15,B=10;aggregate_reserve=25;deal_ownership_A=15,B=10"),
        "p4-p29c": ("period=third;source_closed_predecessor_scaffold=P4-P29b-exact-request;prior_result=P4-P29b;opening_A=15,B=10;release_A=15,B=4;D0=0;new_reserve=0", "predecessor_and_current_bundles_verify_at_own_cutoffs;A_transition=15->0;B_transition=10->6;D_g=19", "closing_inventory_retains_A=0,B=6;aggregate_reserve=6;next_opening_complete_state_and_fresh_metadata=exact"),
        "p4-p30": ("opening_stable_settled_cash_lots=A-paid20,B-escrow10;returned=0;current_GP_bridges=A-paid7.5,B-escrow2.5;settled_permitted_ceiling=30", "opening_dual_balances_tie;Gnet_cash=40;clawback=10;reverse_attribution=B-current2.5,A-current7.5", "next_partial_release_B=5;same_lot_id_source_lineage;both_layers_update_and_copy_exactly"),
        "p4-p30b": ("prior_A_paid_original=15;prior_B_escrow_original=11;historical_A_return=3,target=paid;opening_A_paid=12,returned=3;current_A_paid=7;current_B_return=2,target=escrow;Z=40;c=.20", "B_escrow=11->9,returned=0->2;closing_outstanding=28;C=20;reverse_walk=7,9,4", "obligations_A=11,B=9;prior_and_current_transitions_exact;per_deal_and_aggregate_tie"),
        "p4-p30c": ("prior_B_escrow_original_economic_and_settled=11;historical_return=2;opening_B_paid=0,escrow=9,returned=2;current_release_input_economic=5,settled=5;same_B_lot_event_deal_projection", "same_input_id_on_holdback_and_transition;closing_B_paid=5,escrow=4,returned=2,remaining=9;Gnet_cash_and_economic_entitlement=unchanged", "next_projection_copies_both_layers_exact_fingerprint_with_fresh_metadata"),
        "p4-p31": ("direct_rate=.80 EUR/USD;pre-tier_target_event=100;post-tier_target_allocation=25;final-output_target=10", "distinct_target_ids_convert_once_to=80,20,8", "wrong_or_missing_target_or_stage=refuse"),
        "p4-p32": (
            "minor=.01;ordered_cash_lots=A1.005,B1.005;primary_D=2.01;"
            "reserve_target=1.005;reserve_owner=A;"
            "modes=half-even,half-up,down;settlement_stage=common-final;"
            "edge_C_raw=.004;edge_D=2.014",
            "half-even=1.00+1.00,residual=.01;"
            "half-up=1.01+1.01,residual=-.01;"
            "down=1.00+1.00,residual=.01;"
            "A_economic_reserve=1.005;A_settled_reserve=1.00,1.01,1.00;"
            "reserve_settled_total=A_settled_reserve;"
            "C_settled=0,skip_residual_ownership;"
            "residual_owner=B_final_settled_positive_segment",
            "next_opening_copies_economic_and_settled_layers;"
            "release_cap=settled_cash;economic_release=ruled_economic_delta;"
            "residual_never_mutates_A_or_C",
        ),
        "p4-p33": ("ordered_scenarios=baseline,counterfactual;canonical_controlled_values=100,105;each_scenario_and_result_linked_to_verified_basis;changed_dimension=controlled-value", "fresh_resolution_binds_both_scenario_and_projection_ids;identity_free_semantic_remainder=byte_equal;signed_delta=5", "missing_swapped_noncanonical_cross_cutoff_or_second_dimension=refuse-before-verdict"),
        "p4-p34": (
            "liquid_events=management-fee,performance-fee;"
            "closed_segments=reserve,capital,preferred,catchup,residual,carry-escrow;"
            "reserve_totals=zero,nonzero;residuals=liquid,closed;"
            "zero_settled_raw_line=P4-P32-C-.004",
            "liquid_deal_and_cash_lot_ids=null;liquid_reserve_total=0;"
            "closed_non_residual_inherits=marginal_cash_lot_and_deal;"
            "reserve_event=reserve;reserve_beneficiary=vehicle;"
            "reserve_count=once_in_reserve_settled_and_common_settled_totals;"
            "residual_inherits=final_settled_positive_segment_lot_and_deal",
            "wrong_kind_event_lot_deal_beneficiary_reserve_omission_"
            "reserve_double_count_or_residual_mutation=refuse",
        ),
        "p4-p35": (
            "paths=P4-P25-two-deal,P4-P32-reserve,P4-P30c-stable-lot;"
            "snapshots=complete-aggregate-and-deal;"
            "nonzero_residual_variant=settlement-present",
            "aggregate_equals_deal_sum;event_links=exact;"
            "reserve_changes=canonically_consumed_cash_lot_deals_only;"
            "lot_create_release_return=one-stable-id-exact-before-after;"
            "closing_event=zero-change-terminal",
            "mutated_event_order_affected_deals_reserve_ownership_cash_lot_source_"
            "lot_id_source_balance_unaffected_row_aggregate_sum_continuity_"
            "settlement_presence_closing_lot_tuple_or_final_snapshot=refuse",
        ),
        "p4-p36": (
            "management_fee=.506;performance_fee=.497;minor_unit=.01;"
            "mode=half-even;stage=final-settlement;residual_beneficiary=vehicle",
            "economic_gross_total=1.003;unrounded_allocated_total=1.003;"
            "settlement_target_total=1.00;economic_to_settlement_delta=-.003;"
            "management_line=.51;performance_line=.50;"
            "settled_allocated_total=1.01;cash_rounding_residual=-.01",
            "settled_identity=1.00=1.01-.01;"
            "settled_NAV_uses_settlement_target_total=1.00;"
            "vehicle_cash_residual_applied_once;sub_minor_delta_not_cash",
        ),
    }

    assert set(expected) == set(P4_POSITIVE_SCENARIO_IDS)
    assert {
        scenario_id: terms_fixtures_module._P4_SCENARIO_CONTROLLED_VALUES[scenario_id]
        for scenario_id in expected
    } == expected


def test_each_context_and_cutoff_has_the_exact_scenario_set() -> None:
    conn = connect()
    initialize(conn)
    build_terms_fixture(conn)
    for cutoff_name in P4_TERMS_CUTOFFS:
        for context in P4_SCENARIO_DATASETS:
            expected = set(P4_SCENARIO_CONTEXTS[context])
            if cutoff_name == "early":
                expected -= {"p4-p29b", "p4-p29c"}
            elif cutoff_name == "amended":
                expected.discard("p4-p29c")
            rows = load_p4_term_projections(
                conn,
                build_p4_terms_bundle(
                    conn,
                    cutoff_name=cutoff_name,
                    access_context=context,
                ),
            ).rows
            assert {
                row.scenario_id
                for row in rows
                if row.projection_kind == "scenario_input"
            } == expected
            rows_by_key = {row.record_key: row for row in rows}
            for row in (
                item for item in rows if item.projection_kind == "scenario_input"
            ):
                calculation = rows_by_key[
                    row.payload["value"]["calculation_policy_projection_key"]
                ]
                rounding_key = calculation.payload["value"][
                    "rounding_policy_projection_key"
                ]
                assert rows_by_key[rounding_key].projection_kind == "rounding_policy"


def test_load_p4_term_projections_closes_every_supported_reference() -> None:
    conn = connect()
    initialize(conn)
    build_terms_fixture(conn)
    bundle = build_p4_terms_bundle(
        conn,
        cutoff_name="amended",
        access_context="segregated-mandate",
    )

    projection_set = load_p4_term_projections(conn, bundle)

    assert tuple(source.dataset_id for source in bundle.request.sources) == tuple(
        sorted(
            (
                P4_DOCUMENT_DATASETS["document:p4-segregated-ima"][0],
                "dataset:p4-scenarios-segregated",
                "dataset:terms",
            )
        )
    )
    expected_entity_id = "legal-entity:p4-segregated-case"
    assert all(
        source.canonical_entity_ids == (expected_entity_id,)
        and source.include_unresolved is False
        for source in bundle.request.sources
    )
    assert projection_set.bundle_digest == bundle.bundle_digest
    assert projection_set.decision_at == normalize_utc(P4_TERMS_CUTOFFS["amended"])
    assert projection_set.rows == tuple(
        sorted(projection_set.rows, key=lambda row: row.projection_id)
    )
    assert {row.projection_kind for row in projection_set.rows} == {
        "term_document",
        "scenario_input",
        "calculation_policy",
        "rounding_policy",
        "materiality_policy",
        "materiality_comparison_basis",
        "deal_cash_lot",
        "opening_reserve_lot",
    }
    supported = {
        "evidence-item",
        "source-record",
        "dataset-observation",
        "evidence-span",
        "evidence-right",
        "dataset-version",
        "dataset-delivery-partition",
        "dataset-observation-partition-link",
        "snapshot",
    }
    for row in projection_set.rows:
        verify_p4_projection_receipt(conn, bundle, row)
        assert resolve_span(conn, row.lineage.evidence_span_id)["text"]
        reference_types = {
            ref[0]
            for ref in conn.execute(
                "SELECT reference_type FROM receipt_reference WHERE receipt_id=?",
                (row.projection_receipt_id,),
            )
        }
        assert reference_types == supported
        assert conn.execute(
            "SELECT count(*) FROM receipt_reference WHERE receipt_id=?",
            (row.projection_receipt_id,),
        ).fetchone()[0] == 9


def test_task3_manifest_and_projection_cardinalities_are_exact() -> None:
    conn = connect()
    initialize(conn)
    manifest = build_terms_fixture(conn)

    assert len(manifest.bundle_case_records) == 39
    assert len(manifest.join_receipt_ids) == 38
    assert len(manifest.projection_ids) == 1041
    assert len(manifest.projection_receipt_ids) == 1041
    assert len(set(manifest.projection_receipt_ids.values())) == 1041
    placeholders = ",".join("?" for _ in manifest.projection_receipt_ids)
    assert conn.execute(
        f"SELECT count(*) FROM receipt_reference WHERE receipt_id IN ({placeholders})",
        tuple(manifest.projection_receipt_ids.values()),
    ).fetchone()[0] == 9369


def test_task3_manifest_and_receipts_rebuild_deterministically() -> None:
    closures = []
    for _ in range(2):
        conn = connect()
        initialize(conn)
        manifest = build_terms_fixture(conn)
        receipt_ids = tuple(
            sorted(
                {
                    *manifest.slice_receipt_ids.values(),
                    *manifest.join_receipt_ids.values(),
                    *manifest.projection_receipt_ids.values(),
                }
            )
        )
        placeholders = ",".join("?" for _ in receipt_ids)
        join_receipt_ids = tuple(sorted(manifest.join_receipt_ids.values()))
        join_placeholders = ",".join("?" for _ in join_receipt_ids)
        bundle_manifest_rows = conn.execute(
            f"SELECT * FROM snapshot_bundle_manifest "
            f"WHERE join_receipt_id IN ({join_placeholders}) ORDER BY bundle_digest",
            join_receipt_ids,
        ).fetchall()
        snapshot_ids = tuple(
            sorted(
                {
                    snapshot_id
                    for row in bundle_manifest_rows
                    for _, snapshot_id in json.loads(row["slice_digests_json"])
                }
            )
        )
        snapshot_placeholders = ",".join("?" for _ in snapshot_ids)
        closures.append(
            (
                manifest,
                tuple(tuple(row) for row in bundle_manifest_rows),
                tuple(
                    tuple(row)
                    for row in conn.execute(
                        f"SELECT * FROM snapshot_manifest "
                        f"WHERE snapshot_digest IN ({snapshot_placeholders}) "
                        "ORDER BY snapshot_digest",
                        snapshot_ids,
                    )
                ),
                tuple(
                    tuple(row)
                    for row in conn.execute(
                        f"SELECT * FROM reconstruction_receipt "
                        f"WHERE receipt_id IN ({placeholders}) ORDER BY receipt_id",
                        receipt_ids,
                    )
                ),
                tuple(
                    tuple(row)
                    for row in conn.execute(
                        f"SELECT * FROM receipt_reference "
                        f"WHERE receipt_id IN ({placeholders}) "
                        "ORDER BY receipt_id,ordinal",
                        receipt_ids,
                    )
                ),
                tuple(
                    tuple(row)
                    for row in conn.execute(
                        f"SELECT * FROM receipt_seal "
                        f"WHERE receipt_id IN ({placeholders}) ORDER BY receipt_id",
                        receipt_ids,
                    )
                ),
            )
        )

    assert closures[0] == closures[1]


def test_all_positive_requests_have_exact_and_authorized_document_topology() -> None:
    expected_documents = {
        "public": ("document:p4-public-liquid-prospectus",),
        "pre-hire-public": ("document:p4-private-ppm",),
        "shortlisted-nda": (
            "document:p4-segregated-ima",
            "document:p4-private-ppm",
            "document:p4-whole-fund-lpa",
            "document:p4-deal-by-deal-lpa",
        ),
        "funded-commingled": (
            "document:p4-public-liquid-prospectus",
            "document:p4-private-ppm",
            "document:p4-whole-fund-lpa",
        ),
        "funded-private-partnership": (
            "document:p4-private-ppm",
            "document:p4-whole-fund-lpa",
            "document:p4-deal-by-deal-lpa",
        ),
        "segregated-mandate": ("document:p4-segregated-ima",),
    }
    for cutoff_index, cutoff_name in enumerate(P4_TERMS_CUTOFFS):
        for context, scenario_row in P4_SCENARIO_DATASETS.items():
            request = p4_terms_bundle_request(
                cutoff_name=cutoff_name, access_context=context
            )
            expected = {
                P4_DOCUMENT_DATASETS[document_id][0]
                for document_id in expected_documents[context]
            }
            expected.add(scenario_row[0])
            if cutoff_index >= 1 and context in {
                "shortlisted-nda",
                "funded-commingled",
                "funded-private-partnership",
                "segregated-mandate",
            }:
                expected.add("dataset:terms")
            if cutoff_index >= 2 and context in {
                "shortlisted-nda",
                "funded-commingled",
                "funded-private-partnership",
            }:
                expected.add("dataset:p4-doc-side-letter")
            assert tuple(source.dataset_id for source in request.sources) == tuple(
                sorted(expected)
            )
            entity_id = P4_POSITIVE_ENTITY_RECORDS[context][0]
            assert all(
                source.canonical_entity_ids == (entity_id,)
                and source.include_unresolved is False
                for source in request.sources
            )
            assert validate_p4_positive_bundle_request(request) == context


def test_positive_request_rejects_every_selector_and_scope_mutation() -> None:
    request = p4_terms_bundle_request(
        cutoff_name="side-letter",
        access_context="funded-private-partnership",
    )
    substitute = P4_POSITIVE_ENTITY_RECORDS["funded-commingled"][0]
    for index, source in enumerate(request.sources):
        for selector in (
            (),
            (substitute,),
            (*source.canonical_entity_ids, substitute),
            (substitute, *source.canonical_entity_ids),
        ):
            sources = list(request.sources)
            sources[index] = replace(source, canonical_entity_ids=selector)
            with pytest.raises(EvidenceRefusal, match="p4-term-bundle-request-invalid"):
                validate_p4_positive_bundle_request(
                    replace(request, sources=tuple(sources))
                )
        for mutation in (
            replace(source, include_unresolved=True),
            replace(source, licence_purpose="wrong-purpose"),
        ):
            sources = list(request.sources)
            sources[index] = mutation
            with pytest.raises(EvidenceRefusal, match="p4-term-bundle-request-invalid"):
                validate_p4_positive_bundle_request(
                    replace(request, sources=tuple(sources))
                )
    with pytest.raises(EvidenceRefusal, match="p4-term-bundle-request-invalid"):
        validate_p4_positive_bundle_request(
            replace(request, sources=tuple(reversed(request.sources)))
        )


def test_funded_private_request_rejects_each_removed_document_slice() -> None:
    request = p4_terms_bundle_request(
        cutoff_name="side-letter",
        access_context="funded-private-partnership",
    )
    scenario_dataset_id = P4_SCENARIO_DATASETS["funded-private-partnership"][0]
    document_dataset_ids = tuple(
        source.dataset_id
        for source in request.sources
        if source.dataset_id != scenario_dataset_id
    )

    assert len(document_dataset_ids) == 5
    for removed_dataset_id in document_dataset_ids:
        mutated = replace(
            request,
            sources=tuple(
                source
                for source in request.sources
                if source.dataset_id != removed_dataset_id
            ),
        )
        with pytest.raises(EvidenceRefusal, match="p4-term-bundle-request-invalid"):
            validate_p4_positive_bundle_request(mutated)


def test_removed_shared_document_selector_cannot_yield_positive_projections() -> None:
    conn = connect()
    initialize(conn)
    build_terms_fixture(conn)
    request = p4_terms_bundle_request(
        cutoff_name="side-letter",
        access_context="funded-private-partnership",
    )
    shared_dataset_id = P4_DOCUMENT_DATASETS["document:p4-private-ppm"][0]
    sources = tuple(
        replace(source, canonical_entity_ids=())
        if source.dataset_id == shared_dataset_id
        else source
        for source in request.sources
    )
    mutated = replace(request, sources=sources)

    with pytest.raises(EvidenceRefusal, match="p4-term-bundle-request-invalid"):
        validate_p4_positive_bundle_request(mutated)

    general_bundle = as_known_bundle(conn, mutated)
    shared_slice = next(
        slice_
        for slice_ in general_bundle.slices
        if slice_.request.dataset_id == shared_dataset_id
    )
    assert P4_POSITIVE_ENTITY_RECORDS["funded-commingled"][0] in {
        row["canonical_entity_id"] for row in shared_slice.rows
    }
    with pytest.raises(EvidenceRefusal, match="p4-term-bundle-request-invalid"):
        load_p4_term_projections(conn, general_bundle)


def test_every_positive_bundle_excludes_negative_sources_and_case_ids() -> None:
    conn = connect()
    initialize(conn)
    build_terms_fixture(conn)
    refused_ids = (*P4_AUTHORED_NEGATIVE_CASE_IDS, *P4_TOPOLOGY_ADVERSARY_IDS)

    for cutoff_name in P4_TERMS_CUTOFFS:
        for access_context in P4_SCENARIO_DATASETS:
            bundle = build_p4_terms_bundle(
                conn,
                cutoff_name=cutoff_name,
                access_context=access_context,
            )
            assert P4_NEGATIVE_DATASET[0] not in {
                source.dataset_id for source in bundle.request.sources
            }
            encoded_rows = canonical_bytes(
                tuple(row for slice_ in bundle.slices for row in slice_.rows)
            )
            assert all(case_id.encode() not in encoded_rows for case_id in refused_ids)


def test_partial_document_authorization_never_degrades_to_remaining_sources() -> None:
    conn = connect()
    initialize(conn)
    manifest = build_terms_fixture(conn)
    request = p4_terms_bundle_request(
        cutoff_name="side-letter",
        access_context="funded-private-partnership",
    )
    deal_right = manifest.right_ids["dataset:p4-doc-deal-by-deal-lpa"]
    sources = tuple(
        replace(source, evidence_right_id=deal_right)
        if source.dataset_id == "dataset:p4-doc-side-letter"
        else source
        for source in request.sources
    )
    adversarial = replace(request, sources=sources)

    with pytest.raises(EvidenceRefusal, match="licence-purpose-mismatch"):
        as_known_bundle(conn, adversarial)

    contract = manifest.bundle_case_records[P4_TOPOLOGY_ADVERSARY_IDS[0]]
    assert contract.expected_outcome == "licence-purpose-mismatch"
    assert contract.request_digest == hashlib.sha256(canonical_bytes(adversarial)).hexdigest()


def test_negative_and_method_requests_are_isolated() -> None:
    conn = connect()
    initialize(conn)
    build_terms_fixture(conn)
    for case_id in P4_AUTHORED_NEGATIVE_CASE_IDS:
        request = p4_terms_negative_bundle_request(case_id=case_id)
        assert tuple(source.dataset_id for source in request.sources) == (
            P4_NEGATIVE_DATASET[0],
        )
        assert request.sources[0].canonical_entity_ids == (f"case:{case_id}",)
        bundle = as_known_bundle(conn, request)
        assert {
            row["canonical_entity_id"] for slice_ in bundle.slices for row in slice_.rows
        } <= {f"case:{case_id}"}
        with pytest.raises(EvidenceRefusal, match="p4-term-bundle-request-invalid"):
            load_p4_term_projections(conn, bundle)
    for case_id in ("", "unknown", P4_TOPOLOGY_ADVERSARY_IDS[0]):
        with pytest.raises(EvidenceRefusal, match="p4-term-bundle-request-invalid"):
            p4_terms_negative_bundle_request(case_id=case_id)

    first_case_id, second_case_id = P4_AUTHORED_NEGATIVE_CASE_IDS[:2]
    request = p4_terms_negative_bundle_request(case_id=first_case_id)
    multi_case_request = replace(
        request,
        sources=(
            replace(
                request.sources[0],
                canonical_entity_ids=(f"case:{first_case_id}", f"case:{second_case_id}"),
            ),
        ),
    )
    multi_case_bundle = as_known_bundle(conn, multi_case_request)
    with pytest.raises(EvidenceRefusal, match="p4-term-bundle-request-invalid"):
        load_p4_term_projections(conn, multi_case_bundle)

    method_request = p4_method_policy_bundle_request()
    assert tuple(source.dataset_id for source in method_request.sources) == (
        P4_METHOD_POLICY_DATASET[0],
    )
    method_bundle = build_p4_method_policy_bundle(conn)
    projections = load_p4_term_projections(conn, method_bundle)
    assert tuple(row.projection_kind for row in projections.rows) == (
        "method_boundary_policy",
    )


def test_persisted_positive_request_mutation_refuses_before_projection() -> None:
    conn = connect()
    initialize(conn)
    bundle = build_p4_terms_bundle(
        conn, cutoff_name="early", access_context="public"
    )
    conn.execute("DROP TRIGGER immutable_update_snapshot_bundle_manifest")
    conn.execute(
        "UPDATE snapshot_bundle_manifest SET request_json='{}' WHERE bundle_digest=?",
        (bundle.bundle_digest,),
    )

    with pytest.raises(EvidenceRefusal, match="p4-term-bundle-request-invalid"):
        load_p4_term_projections(conn, bundle)


def test_projection_receipt_seal_mutation_is_detected() -> None:
    conn = connect()
    initialize(conn)
    bundle = build_p4_terms_bundle(
        conn, cutoff_name="early", access_context="public"
    )
    projection = load_p4_term_projections(conn, bundle).rows[0]
    conn.execute("DROP TRIGGER immutable_update_receipt_seal")
    conn.execute(
        "UPDATE receipt_seal SET references_sha256=printf('%064d',0) WHERE receipt_id=?",
        (projection.projection_receipt_id,),
    )

    with pytest.raises(EvidenceRefusal, match="receipt-incomplete"):
        verify_p4_projection_receipt(conn, bundle, projection)


def test_projection_source_closure_mutations_are_detected_at_exact_hop() -> None:
    mutations = (
        (
            "evidence_item",
            "UPDATE evidence_item SET content_sha256=printf('%064d',0) "
            "WHERE evidence_item_id=?",
            "evidence_item_id",
            "payload-schema-mismatch",
        ),
        (
            "evidence_span",
            "UPDATE evidence_span SET json_pointer='/value' "
            "WHERE evidence_span_id=?",
            "evidence_span_id",
            "receipt-incomplete",
        ),
        (
            "evidence_span",
            "UPDATE evidence_span SET start_char=start_char+1 "
            "WHERE evidence_span_id=?",
            "evidence_span_id",
            "machine-id-mismatch",
        ),
        (
            "evidence_span",
            "UPDATE evidence_span SET span_sha256=printf('%064d',0) "
            "WHERE evidence_span_id=?",
            "evidence_span_id",
            "machine-id-mismatch",
        ),
        (
            "evidence_right",
            "UPDATE evidence_right SET licence_purpose='wrong-purpose' "
            "WHERE evidence_right_id=?",
            "evidence_right_id",
            "machine-id-mismatch",
        ),
        (
            "dataset_version",
            "UPDATE dataset_version SET content_sha256=printf('%064d',0) "
            "WHERE dataset_version_id=?",
            "dataset_version_id",
            "machine-id-mismatch",
        ),
        (
            "dataset_delivery_partition",
            "UPDATE dataset_delivery_partition SET received_content_sha256=printf('%064d',0) "
            "WHERE dataset_delivery_partition_id=?",
            "dataset_delivery_partition_id",
            "machine-id-mismatch",
        ),
        (
            "dataset_observation",
            "UPDATE dataset_observation SET observation_status='explicitly-removed' "
            "WHERE dataset_observation_id=?",
            "dataset_observation_id",
            "machine-id-mismatch",
        ),
        (
            "dataset_observation_partition_link",
            "UPDATE dataset_observation_partition_link "
            "SET dataset_delivery_partition_id=("
            "SELECT dataset_delivery_partition_id "
            "FROM dataset_delivery_partition "
            "WHERE dataset_delivery_partition_id != ? LIMIT 1) "
            "WHERE dataset_observation_partition_link_id=?",
            "dataset_observation_partition_link_id",
            "receipt-incomplete",
        ),
    )
    for table, sql, lineage_field, refusal in mutations:
        conn = connect()
        initialize(conn)
        bundle = build_p4_terms_bundle(
            conn, cutoff_name="early", access_context="public"
        )
        projection = load_p4_term_projections(conn, bundle).rows[0]
        conn.execute(f"DROP TRIGGER immutable_update_{table}")
        identifier = getattr(projection.lineage, lineage_field)
        parameters = (identifier, identifier) if table == "dataset_observation_partition_link" else (identifier,)
        conn.execute(sql, parameters)

        with pytest.raises(EvidenceRefusal, match=refusal):
            load_p4_term_projections(conn, bundle)


def test_snapshot_and_bundle_manifest_mutations_are_rejected() -> None:
    mutations = (
        (
            "snapshot_manifest",
            "UPDATE snapshot_manifest SET records_sha256=printf('%064d',0) "
            "WHERE snapshot_digest=?",
            "snapshot_digest",
        ),
        (
            "snapshot_bundle_manifest",
            "UPDATE snapshot_bundle_manifest SET row_count=row_count+1 "
            "WHERE bundle_digest=?",
            "bundle_digest",
        ),
    )
    for table, sql, identifier_kind in mutations:
        conn = connect()
        initialize(conn)
        bundle = build_p4_terms_bundle(
            conn, cutoff_name="early", access_context="public"
        )
        identifier = (
            bundle.slices[0].digest
            if identifier_kind == "snapshot_digest"
            else bundle.bundle_digest
        )
        conn.execute(f"DROP TRIGGER immutable_update_{table}")
        conn.execute(sql, (identifier,))

        with pytest.raises(EvidenceRefusal, match="p4-term-bundle-request-invalid"):
            load_p4_term_projections(conn, bundle)


def test_slice_join_and_projection_receipt_header_mutations_are_rejected() -> None:
    for receipt_kind in ("slice", "join", "projection"):
        conn = connect()
        initialize(conn)
        bundle = build_p4_terms_bundle(
            conn, cutoff_name="early", access_context="public"
        )
        projection = load_p4_term_projections(conn, bundle).rows[0]
        receipt_id = {
            "slice": projection.lineage.slice_receipt_id,
            "join": projection.lineage.join_receipt_id,
            "projection": projection.projection_receipt_id,
        }[receipt_kind]
        conn.execute("DROP TRIGGER immutable_update_reconstruction_receipt")
        conn.execute(
            "UPDATE reconstruction_receipt SET algorithm_version='mutated' "
            "WHERE receipt_id=?",
            (receipt_id,),
        )

        with pytest.raises(EvidenceRefusal, match="receipt-incomplete"):
            load_p4_term_projections(conn, bundle)


def test_projection_receipt_reference_and_value_digest_mutations_are_rejected() -> None:
    mutations = (
        (
            "receipt_reference",
            "UPDATE receipt_reference SET role='benchmark' "
            "WHERE receipt_id=? AND ordinal=0",
        ),
        (
            "reconstruction_receipt",
            "UPDATE reconstruction_receipt SET value_sha256=printf('%064d',0) "
            "WHERE receipt_id=?",
        ),
    )
    for table, sql in mutations:
        conn = connect()
        initialize(conn)
        bundle = build_p4_terms_bundle(
            conn, cutoff_name="early", access_context="public"
        )
        projection = load_p4_term_projections(conn, bundle).rows[0]
        conn.execute(f"DROP TRIGGER immutable_update_{table}")
        conn.execute(sql, (projection.projection_receipt_id,))

        with pytest.raises(EvidenceRefusal, match="receipt-incomplete"):
            verify_p4_projection_receipt(conn, bundle, projection)


def test_projection_object_and_bundle_cutoff_mutations_are_rejected() -> None:
    conn = connect()
    initialize(conn)
    bundle = build_p4_terms_bundle(
        conn, cutoff_name="early", access_context="public"
    )
    projection = load_p4_term_projections(conn, bundle).rows[0]
    with pytest.raises(EvidenceRefusal, match="receipt-incomplete"):
        verify_p4_projection_receipt(
            conn,
            bundle,
            replace(projection, record_key="record:substituted"),
        )
    with pytest.raises(EvidenceRefusal, match="receipt-incomplete"):
        verify_p4_projection_receipt(
            conn,
            bundle,
            replace(
                projection,
                payload={**projection.payload, "classification": "substituted"},
            ),
        )
    with pytest.raises(EvidenceRefusal, match="receipt-incomplete"):
        verify_p4_projection_receipt(
            conn,
            bundle,
            replace(
                projection,
                projection_id=f"p4-term-projection:sha256:{'0' * 64}",
            ),
        )

    mutated_request = replace(
        bundle.request,
        decision_at=datetime(2024, 2, 1, tzinfo=UTC),
    )
    with pytest.raises(EvidenceRefusal, match="p4-term-bundle-request-invalid"):
        load_p4_term_projections(conn, replace(bundle, request=mutated_request))


def test_p4_projection_contracts_are_transitively_frozen_and_alias_safe() -> None:
    caller_payload = {"classification": "hypothetical-contract-scenario", "values": ["1.00"]}
    projection = _projection(caller_payload)
    caller_payload["values"].append("2.00")
    caller_payload["classification"] = "mutated"

    assert projection.payload["classification"] == "hypothetical-contract-scenario"
    assert projection.payload["values"] == ("1.00",)
    with pytest.raises(TypeError):
        projection.payload["classification"] = "mutated"
    with pytest.raises(FrozenInstanceError):
        projection.record_key = "scenario:mutated"

    projection_set = P4TermProjectionSet(
        bundle_digest=f"bundle:sha256:{'4' * 64}",
        decision_at="2024-01-31T23:59:59.000000Z",
        rows=(projection,),
        projection_digest="5" * 64,
    )
    assert projection_set.rows_of_kind("scenario_input") == (projection,)
    assert projection_set.require_record(projection.projection_id) is projection


def test_p4_projection_contracts_reject_unsafe_values() -> None:
    with pytest.raises(TypeError, match="float"):
        _projection({"amount": 1.0})
    with pytest.raises(ValueError, match="projection kind"):
        P4TermProjection(
            projection_id=f"p4-term-projection:sha256:{'2' * 64}",
            projection_kind="unknown",
            record_key="scenario:p4-p1",
            scenario_id="p4-p1",
            document_key=None,
            payload={"amount": "1.00"},
            lineage=_lineage(),
            projection_receipt_id=f"receipt:sha256:{'3' * 64}",
        )
    with pytest.raises(ValueError, match="UTC"):
        P4TermProjectionSet(
            bundle_digest=f"bundle:sha256:{'4' * 64}",
            decision_at="2024-01-31T23:59:59",
            rows=(),
            projection_digest="5" * 64,
        )
    with pytest.raises(ValueError, match="identifier"):
        P4TermProjection(
            projection_id="not an id",
            projection_kind="scenario_input",
            record_key="scenario:p4-p1",
            scenario_id="p4-p1",
            document_key=None,
            payload={"amount": "1.00"},
            lineage=_lineage(),
            projection_receipt_id=f"receipt:sha256:{'3' * 64}",
        )
    with pytest.raises(ValueError, match="lowercase"):
        P4TermProjectionSet(
            bundle_digest=f"bundle:sha256:{'4' * 64}",
            decision_at="2024-01-31T23:59:59.000000Z",
            rows=(),
            projection_digest="z" * 64,
        )


def test_digest_bound_decision_times_are_normalized_to_canonical_utc() -> None:
    lineage = _lineage("2024-01-31T23:59:59+00:00")
    projection_set = P4TermProjectionSet(
        bundle_digest=f"bundle:sha256:{'4' * 64}",
        decision_at="2024-01-31T23:59:59+00:00",
        rows=(),
        projection_digest="5" * 64,
    )

    assert lineage.decision_at == "2024-01-31T23:59:59.000000Z"
    assert projection_set.decision_at == "2024-01-31T23:59:59.000000Z"
    with pytest.raises(ValueError, match="lowercase"):
        PredecessorRequestScaffoldRecord(
            projection_id=f"p4-term-projection:sha256:{'7' * 64}",
            expected_predecessor_scenario_id="p4-p29a",
            predecessor_bundle_request=SnapshotBundleRequest(
                decision_at=datetime(2024, 1, 31, tzinfo=UTC),
                sources=(),
                join_keys=("canonical_entity_id",),
                join_policy="exact-inner-v1",
            ),
            predecessor_request_digest="z" * 64,
            lineage=lineage,
            projection_receipt_id=f"receipt:sha256:{'9' * 64}",
        )


def test_predecessor_scaffold_detaches_nested_request_aliases() -> None:
    canonical_entities = ["legal-entity:p4-private-case"]
    source = DatasetSliceRequest(
        dataset_id="dataset:p4-scenarios-funded-private",
        access_context="funded-private-partnership",
        evidence_right_id=f"right:sha256:{'6' * 64}",
        licence_purpose="private-scenario-governance",
        canonical_entity_ids=canonical_entities,
        include_unresolved=False,
    )
    sources = [source]
    join_keys = ["canonical_entity_id"]
    request = SnapshotBundleRequest(
        decision_at=datetime(2024, 1, 31, 23, 59, 59, tzinfo=UTC),
        sources=sources,
        join_keys=join_keys,
        join_policy="exact-inner-v1",
    )
    scaffold = PredecessorRequestScaffoldRecord(
        projection_id=f"p4-term-projection:sha256:{'7' * 64}",
        expected_predecessor_scenario_id="p4-p29a",
        predecessor_bundle_request=request,
        predecessor_request_digest="8" * 64,
        lineage=_lineage(),
        projection_receipt_id=f"receipt:sha256:{'9' * 64}",
    )

    canonical_entities.append("legal-entity:p4-mutated")
    sources.clear()
    join_keys.append("mutated")

    assert scaffold.predecessor_bundle_request is not request
    assert scaffold.predecessor_bundle_request.sources[0] is not source
    assert scaffold.predecessor_bundle_request.sources[0].canonical_entity_ids == (
        "legal-entity:p4-private-case",
    )
    assert scaffold.predecessor_bundle_request.join_keys == ("canonical_entity_id",)
    with pytest.raises(ValueError, match="UTC"):
        PredecessorRequestScaffoldRecord(
            projection_id=f"p4-term-projection:sha256:{'7' * 64}",
            expected_predecessor_scenario_id="p4-p29a",
            predecessor_bundle_request=SnapshotBundleRequest(
                decision_at=datetime(2024, 1, 31),
                sources=(),
                join_keys=("canonical_entity_id",),
                join_policy="exact-inner-v1",
            ),
            predecessor_request_digest="8" * 64,
            lineage=_lineage(),
            projection_receipt_id=f"receipt:sha256:{'9' * 64}",
        )


def test_p4_projection_public_signatures_are_exact() -> None:
    assert tuple(signature(load_p4_term_projections).parameters) == ("conn", "bundle")
    assert tuple(signature(verify_p4_projection_receipt).parameters) == (
        "conn",
        "bundle",
        "projection",
    )
    assert tuple(signature(load_predecessor_request_scaffold).parameters) == (
        "conn",
        "projection_set",
        "projection_id",
    )
    assert tuple(signature(validate_p4_positive_bundle_request).parameters) == ("request",)
    assert PredecessorRequestScaffoldRecord.__dataclass_params__.frozen is True
    assert tuple(field.name for field in fields(P4ProjectionLineage)) == (
        "evidence_item_id",
        "evidence_span_id",
        "source_record_id",
        "dataset_observation_id",
        "dataset_version_id",
        "evidence_right_id",
        "dataset_delivery_partition_id",
        "dataset_observation_partition_link_id",
        "snapshot_digest",
        "slice_receipt_id",
        "join_receipt_id",
        "decision_at",
        "source_schema_id",
        "source_field",
    )
    assert tuple(field.name for field in fields(P4TermProjection)) == (
        "projection_id",
        "projection_kind",
        "record_key",
        "scenario_id",
        "document_key",
        "payload",
        "lineage",
        "projection_receipt_id",
    )
    assert tuple(field.name for field in fields(PredecessorRequestScaffoldRecord)) == (
        "projection_id",
        "expected_predecessor_scenario_id",
        "predecessor_bundle_request",
        "predecessor_request_digest",
        "lineage",
        "projection_receipt_id",
    )
    assert tuple(field.name for field in fields(P4TermProjectionSet)) == (
        "bundle_digest",
        "decision_at",
        "rows",
        "projection_digest",
    )
