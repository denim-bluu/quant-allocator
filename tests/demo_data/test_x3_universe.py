import hashlib
import json
from itertools import product

from quant_allocator.demo_data import x3_universe
from quant_allocator.demo_data._emit import SITE_DATA_DIR
from quant_allocator.evidence.fixtures.x3 import X3_CUTOFFS, X3_SCOPE_PRESETS, X3_SOURCE_VIEWS


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_exact_27_state_contract_and_reviewed_fixture_pins(tmp_path) -> None:
    data = _load(x3_universe.build(out_dir=tmp_path))
    expected = {"|".join(parts) for parts in product(X3_CUTOFFS, X3_SOURCE_VIEWS, X3_SCOPE_PRESETS)}
    assert set(data["states"]) == expected
    assert data["meta"]["state_count"] == 27
    assert data["meta"]["fixture_digest"] == "14a159d4547960c937485d328c3b270051daba7114e54f1380869466a11275e0"
    assert data["meta"]["authored_closure_digest"] == "c5054f17d2e95bf6e80ba7c63a5a8f10f849f7e989f12cf9447d0d308744ac32"


def test_states_consume_real_receipted_projections_and_refuse_missing_cell_link(tmp_path) -> None:
    data = _load(x3_universe.build(out_dir=tmp_path))
    for state in data["states"].values():
        assert state["slice_receipts"]
        assert all(state["slice_receipts"].values())
        assert state["source_counts"]["source_rows"] >= state["source_counts"]["canonical_members"]
        assert state["target_grid"]["eligible_cells"] + state["target_grid"]["excluded_cells"] > 0
        assert state["target_grid"]["observed_cells"] is None
        assert state["queue"] == []
        codes = {row["code"] for row in state["refusals"]}
        assert "typed-membership-cell-projection-required" in codes
        assert "typed-mandate-brief-cohort-projection-required" in codes
        assert state["funnel"]["conversion_interval"] is None


def test_entity_audit_rederives_gate_and_truth_never_enters_states(tmp_path) -> None:
    data = _load(x3_universe.build(out_dir=tmp_path))
    audit = data["entity_resolution_audit"]
    assert (audit["true_positives"], audit["false_positives"], audit["false_negatives"], audit["true_negatives"]) == (410, 0, 10, 420)
    assert audit["precision_interval"][0] >= 0.99
    assert audit["recall_interval"][0] >= 0.95
    assert audit["gate_passes"] is True
    serialized_states = json.dumps(data["states"], sort_keys=True)
    assert "truth" not in serialized_states and "hidden" not in serialized_states


def test_global_denominator_ranking_and_conversion_are_visible_refusals(tmp_path) -> None:
    data = _load(x3_universe.build(out_dir=tmp_path))
    codes = {row["claim_id"] for row in data["refusal_ledger"]}
    assert {"global_universe_coverage", "manager_quality_ranking", "funnel_conversion"} <= codes
    assert data["meta"]["disclaimer"] == (
        "This map measures the named sources and funnel, not the manager universe of the world. "
        "It prioritizes research cells, never managers."
    )
    assert len(data["claim_attestation"]) == 12
    expected_access = {
        "public_source_membership": ["public"],
        "prehire_source_membership": ["pre-hire-public", "shortlisted-nda"],
        "entity_resolution_state": ["public", "pre-hire-public", "shortlisted-nda"],
        "target_cell_observation": ["public", "pre-hire-public", "shortlisted-nda", "internal-governance"],
        "source_union_novelty": ["public", "pre-hire-public", "shortlisted-nda", "internal-governance"],
        "funnel_stage_counts": ["internal-governance"],
        "funnel_conversion": ["internal-governance"],
        "research_cell_queue": ["public", "pre-hire-public", "shortlisted-nda", "internal-governance"],
        "synthetic_entity_recall": ["public"],
        "synthetic_discovery_recall": ["public"],
        "global_universe_coverage": ["public", "pre-hire-public", "shortlisted-nda", "internal-governance"],
        "manager_quality_ranking": ["public", "pre-hire-public", "shortlisted-nda", "internal-governance"],
    }
    for row in data["claim_attestation"]:
        assert {
            "access_contexts",
            "access_semantics",
            "current_attestation",
            "live_ceiling",
            "validation_status",
            "receipt_required",
            "receipt_id",
            "rendered_refusal",
        } <= set(row)
        assert row["access_contexts"] == expected_access[row["claim_id"]]
        assert row["receipt_id"].startswith("receipt:sha256:")
    refusal_claims = {
        row["claim_id"]: row
        for row in data["claim_attestation"]
        if row["claim_id"] in {"global_universe_coverage", "manager_quality_ranking"}
    }
    assert {
        claim_id: (
            row["current_attestation"],
            row["live_ceiling"],
            row["validation_status"],
        )
        for claim_id, row in refusal_claims.items()
    } == {
        "global_universe_coverage": ("D", "D", "synthetic-demo-verified"),
        "manager_quality_ranking": ("D", "D", "synthetic-demo-verified"),
    }
    for state in data["states"].values():
        assert state["join_receipt_id"].startswith("receipt:sha256:")
        assert state["bundle_digest"].startswith("bundle:sha256:")
        assert set(state["claim_receipt_ids"]) == set(expected_access)
        assert all(value.startswith("receipt:sha256:") for value in state["claim_receipt_ids"].values())


def test_point_in_time_cases_are_docketed_and_cutoffs_differ(tmp_path) -> None:
    data = _load(x3_universe.build(out_dir=tmp_path))
    cases = data["method_receipts"]["point_in_time_cases"]
    required = {
        "dead_backfill", "late_alias_crosswalk", "merger_rebrand", "late_taxonomy_remap",
        "post_cutoff_receipt", "post_cutoff_entitlement", "revised_funnel_event",
        "accepted_only_extract", "duplicate_source_rows", "firm_only_registration",
        "ambiguous_collision", "not_inferable_absence", "inactive_product",
        "unknown_denominator", "global_coverage_refusal", "manager_ranking_refusal",
        "full_and_delta_absence_matrix", "incomplete_partition", "repeated_opportunity",
        "impossible_or_stale_transition", "typed_eligible_excluded_cells",
        "multi_source_and_right_refusal",
    }
    assert required <= set(cases)
    early = data["states"]["early|public-plus-prehire|cross-asset"]
    latest = data["states"]["latest|public-plus-prehire|cross-asset"]
    assert early["slice_receipts"] != latest["slice_receipts"]
    assert early["source_counts"] != latest["source_counts"]


def test_byte_identity_and_matches_committed(tmp_path) -> None:
    first = x3_universe.build(out_dir=tmp_path).read_bytes()
    second = x3_universe.build(out_dir=tmp_path).read_bytes()
    assert first == second
    assert first == (SITE_DATA_DIR / "x3_universe.json").read_bytes()
    assert hashlib.sha256(first).hexdigest()
