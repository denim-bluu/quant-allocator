from __future__ import annotations

import hashlib
import json
from pathlib import Path

from quant_allocator.demo_data import e4_operational_change
from quant_allocator.demo_data._emit import SITE_DATA_DIR


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _publication_terms() -> tuple[str, ...]:
    path = Path(__file__).resolve().parents[2] / "tools" / ".publication_terms"
    if not path.exists():
        return ()
    return tuple(
        line.strip().lower()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    )


def test_schema_six_states_and_exact_interaction_contract(tmp_path: Path) -> None:
    data = _load(e4_operational_change.build(out_dir=tmp_path))
    assert {
        "meta",
        "evidence",
        "state_summary",
        "facts",
        "changes",
        "relationships",
        "reunderwriting_queue",
        "refusals",
        "validation",
        "interaction_states",
        "claim_receipts",
        "claim_inventory",
        "exclusions",
    } == set(data)
    assert tuple(data["meta"]["interaction_state_keys"]) == e4_operational_change.STATE_KEYS
    assert tuple(data["interaction_states"]) == e4_operational_change.STATE_KEYS
    expected = {
        "key",
        "cutoff",
        "source_view",
        "access_context",
        "selected_dataset_ids",
        "source_bundle_receipts",
        "composite_union_receipt_id",
        "state_counts",
        "refusal_count",
        "fact_ids",
        "change_ids",
        "relationship_ids",
        "queue_ids",
        "exclusion_ids",
        "data_boundary_refusal_ids",
        "method_boundary_refusal_id",
        "refusal_ids",
        "claim_receipt_ids",
        "visible_id_sets",
    }
    assert all(set(state) == expected for state in data["interaction_states"].values())


def test_claim_inventory_preserves_section_six_access_and_attestation(tmp_path: Path) -> None:
    data = _load(e4_operational_change.build(out_dir=tmp_path))
    permissioned = [
        "shortlisted-nda",
        "funded-commingled",
        "funded-private-partnership",
        "segregated-mandate",
    ]
    all_contexts = ["public", "pre-hire-public", *permissioned]
    expected = {
        "public_operational_facts": (
            "/facts",
            "evidence-graph",
            ["public", "pre-hire-public"],
            "all-required-per-selected-dataset",
            "C",
        ),
        "operational_change_graph": (
            "/changes",
            "evidence-graph",
            permissioned,
            "all-required-per-selected-dataset",
            "B",
        ),
        "operational_evidence_state": (
            "/state_summary",
            "verdict",
            permissioned,
            "all-required-per-selected-dataset",
            "B",
        ),
        "reunderwriting_queue": (
            "/reunderwriting_queue",
            "exact-measurement",
            permissioned,
            "all-required-per-selected-dataset",
            "B",
        ),
        "operational_data_boundary_refusals": (
            "/refusals/data-boundary",
            "refusal",
            all_contexts,
            "refusal-per-inadmissible-input",
            "D",
        ),
        "operational_method_boundary_refusal": (
            "/refusals/method-boundary",
            "refusal",
            all_contexts,
            "refusal-in-every-context",
            "D",
        ),
        "synthetic_state_validation": (
            "/validation",
            "exact-measurement",
            ["public"],
            "synthetic-fixture-only",
            "D",
        ),
    }
    inventory = {row["claim_id"]: row for row in data["claim_inventory"]}
    assert set(inventory) == set(expected)
    for claim_id, (pointer, output_type, contexts, semantics, ceiling) in expected.items():
        row = inventory[claim_id]
        assert row == {
            "claim_id": claim_id,
            "output_pointer": pointer,
            "output_type": output_type,
            "access_contexts": contexts,
            "access_semantics": semantics,
            "current_attestation": "D",
            "live_attestation_ceiling": ceiling,
            "receipt_required": True,
        }


def test_latest_gate_and_corrected_precedence_are_held(tmp_path: Path) -> None:
    data = _load(e4_operational_change.build(out_dir=tmp_path))
    assert data["validation"]["state"] == "derived"
    assert "expected_latest_all_entitled" not in data["validation"]
    assert data["validation"]["latest_all_entitled"] == {
        "facts": 16,
        "keys": 10,
        "states": {"corroborated": 1, "asserted": 3, "conflicted": 3, "stale": 3},
        "queue": {
            "immediate-clarification": 4,
            "scheduled-reunderwrite": 4,
            "evidence-refresh": 2,
        },
    }
    latest_states = data["state_summary"]["latest|all-entitled"]
    process = next(
        row
        for row in latest_states
        if row["fact_key"][1:] == [
            "process",
            "process:e4-nav-review",
            "operates-process",
            "nav-review",
        ]
    )
    assert process["state"] == "asserted"
    unknown_incident = next(
        row
        for row in data["reunderwriting_queue"]["latest|all-entitled"]
        if row["fact_key"][-1] == "materiality-unreported"
    )
    assert unknown_incident["action_bucket"] == "immediate-clarification"


def test_receipts_provenance_and_method_boundary_are_visible(tmp_path: Path) -> None:
    data = _load(e4_operational_change.build(out_dir=tmp_path))
    assert all(state_receipts for state_receipts in data["claim_receipts"].values())
    for state in data["interaction_states"].values():
        assert state["composite_union_receipt_id"].startswith("receipt:sha256:")
        assert state["claim_receipt_ids"]
        assert all(row["slice_receipt_id"] for row in state["source_bundle_receipts"])
    assert data["refusals"]["method_boundary"]["state"] == "refused"
    assert "manager rank" in data["refusals"]["method_boundary"]["prohibited_outputs"]
    assert all(fact["evidence_item_id"] and fact["evidence_span_id"] for fact in data["facts"])
    assert all(fact["dataset_version_id"] and fact["evidence_right_id"] for fact in data["facts"])
    for state_key, receipts in data["claim_receipts"].items():
        for fact in data["facts"]:
            if state_key in fact["receipt_ids_by_state"]:
                assert fact["receipt_ids_by_state"][state_key] == receipts[f"/facts/{fact['fact_id']}"]
        for change in data["changes"]:
            if state_key in change["receipt_ids_by_state"]:
                assert change["receipt_ids_by_state"][state_key] == receipts[
                    f"/changes/{change['change_id']}"
                ]
        for relationship in data["relationships"]:
            if state_key in relationship["receipt_ids_by_state"]:
                assert relationship["receipt_ids_by_state"][state_key] == receipts[
                    f"/relationships/{relationship['relationship_id']}"
                ]
        for item in data["reunderwriting_queue"][state_key]:
            assert item["receipt_ids_by_state"][state_key] == receipts[
                f"/reunderwriting_queue/{item['queue_id']}"
            ]
        for state in data["state_summary"][state_key]:
            assert state["receipt_id"] == receipts[f"/state_summary/{state['state_id']}"]
        for refusal in data["refusals"]["data_boundary"]:
            if state_key in refusal["receipt_ids_by_state"]:
                assert refusal["receipt_ids_by_state"][state_key] == receipts[
                    refusal["output_pointer"]
                ]
        assert data["refusals"]["method_boundary"]["receipt_ids_by_state"][state_key] == receipts[
            "/refusals/method-boundary"
        ]
        assert data["validation"]["receipt_ids_by_state"][state_key] == receipts["/validation"]


def test_no_hidden_truth_score_or_private_content(tmp_path: Path) -> None:
    raw = e4_operational_change.build(out_dir=tmp_path).read_text(encoding="utf-8")
    lowered = raw.lower()
    assert not any(term in lowered for term in _publication_terms())
    assert '"odd_score"' not in lowered
    assert '"manager_rank"' not in lowered
    assert '"expected_outcome"' not in lowered
    assert '"expected_latest_all_entitled"' not in lowered
    assert '"pass_flag"' not in lowered
    assert "/private/" not in lowered and "/users/" not in lowered


def test_source_order_semantic_order_and_exact_540_visible_id_sets(tmp_path: Path) -> None:
    data = _load(e4_operational_change.build(out_dir=tmp_path))
    expected_sources = {
        "public-only": ["dataset:e4-public-registry", "dataset:e4-operational-policy"],
        "all-entitled": [
            "dataset:e4-public-registry",
            "dataset:e4-manager-documents",
            "dataset:e4-control-evidence",
            "dataset:e4-independent-references",
            "dataset:e4-operational-policy",
        ],
    }
    state_order = {"conflicted": 0, "stale": 1, "corroborated": 2, "asserted": 3}
    domain_order = {
        "organisation": 0,
        "process": 1,
        "control": 2,
        "provider": 3,
        "incident": 4,
    }
    fact_rank = {}
    for states in data["state_summary"].values():
        for state in states:
            for fact_id in [*state["supporting_fact_ids"], *state["conflicting_fact_ids"]]:
                fact_rank[fact_id] = min(
                    fact_rank.get(fact_id, state_order[state["state"]]),
                    state_order[state["state"]],
                )
    assert data["facts"] == sorted(
        data["facts"],
        key=lambda row: (
            fact_rank.get(row["fact_id"], len(state_order)),
            domain_order[row["domain"]],
            tuple(
                row[field]
                for field in (
                    "manager_entity_id",
                    "domain",
                    "subject_entity_id",
                    "predicate",
                    "scope",
                )
            ),
            row["fact_id"],
        ),
    )
    assert data["changes"] == sorted(
        data["changes"], key=lambda row: (row["effective_at"], row["change_id"])
    )

    total = 0
    facts = {row["fact_id"]: row for row in data["facts"]}
    for state_key, interaction in data["interaction_states"].items():
        assert interaction["selected_dataset_ids"] == expected_sources[interaction["source_view"]]
        assert [row["dataset_id"] for row in interaction["source_bundle_receipts"]] == expected_sources[
            interaction["source_view"]
        ]
        fact_state = {}
        for state in data["state_summary"][state_key]:
            for fact_id in [*state["supporting_fact_ids"], *state["conflicting_fact_ids"]]:
                fact_state[fact_id] = state["state"]
        for domain in e4_operational_change.DOMAIN_FILTERS:
            for evidence_state in e4_operational_change.STATE_FILTERS:
                expected_facts = [
                    fact_id
                    for fact_id in interaction["fact_ids"]
                    if (domain == "all" or facts[fact_id]["domain"] == domain)
                    and (evidence_state == "all" or fact_state.get(fact_id) == evidence_state)
                ]
                expected_fact_set = set(expected_facts)
                for view in e4_operational_change.VIEW_FILTERS:
                    total += 1
                    visible = interaction["visible_id_sets"][f"{domain}|{evidence_state}|{view}"]
                    assert visible["fact_ids"] == expected_facts
                    assert visible["change_ids"] == [
                        row["change_id"]
                        for row in data["changes"]
                        if row["change_id"] in interaction["change_ids"]
                        and (domain == "all" or row["fact_key"][1] == domain)
                        and (
                            evidence_state == "all"
                            or expected_fact_set.intersection(
                                row["linked_fact_ids_by_state"].get(state_key, [])
                            )
                        )
                    ]
                    expected_relationships = [
                        row["relationship_id"]
                        for row in data["relationships"]
                        if row["relationship_id"] in interaction["relationship_ids"]
                        and expected_fact_set.intersection(
                            row["linked_fact_ids_by_state"].get(state_key, [])
                        )
                    ]
                    assert len(visible["relationship_ids"]) == len(
                        set(visible["relationship_ids"])
                    )
                    assert set(visible["relationship_ids"]) == set(expected_relationships)
                    assert visible["queue_ids"] == [
                        row["queue_id"]
                        for row in data["reunderwriting_queue"][state_key]
                        if expected_fact_set.intersection(
                            row["linked_fact_ids_by_state"].get(state_key, [])
                        )
                    ]
                    assert visible["empty"] == (
                        not any(
                            visible[key]
                            for key in (
                                "fact_ids",
                                "change_ids",
                                "relationship_ids",
                                "queue_ids",
                            )
                        )
                    )
    assert total == 540
    assert any(
        visible["empty"]
        for interaction in data["interaction_states"].values()
        for visible in interaction["visible_id_sets"].values()
    )


def test_byte_identity_digest_and_committed_artifact(tmp_path: Path) -> None:
    first = e4_operational_change.build(out_dir=tmp_path).read_bytes()
    second = e4_operational_change.build(out_dir=tmp_path).read_bytes()
    assert first == second
    assert hashlib.sha256(first).hexdigest() == hashlib.sha256(second).hexdigest()
    assert first == (SITE_DATA_DIR / "e4_operational_change.json").read_bytes()
