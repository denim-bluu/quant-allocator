"""Contract tests for the deterministic S7 provenance exhibit."""

from __future__ import annotations

import hashlib
import json
import math
import re
from itertools import product
from pathlib import Path

import pytest

from quant_allocator.demo_data import s7_provenance
from quant_allocator.demo_data._emit import SITE_DATA_DIR
from quant_allocator.flagships.track_record_provenance.model import (
    FORBIDDEN_ESTIMATOR_OR_RANKING_FIELDS,
)


@pytest.fixture(scope="module")
def s7_data(tmp_path_factory: pytest.TempPathFactory) -> dict:
    path = s7_provenance.build(out_dir=tmp_path_factory.mktemp("s7-data"))
    return json.loads(path.read_text(encoding="utf-8"))


def test_exact_24_full_method_states_and_default(tmp_path) -> None:
    data = json.loads(s7_provenance.build(out_dir=tmp_path).read_text(encoding="utf-8"))
    expected_keys = {
        "|".join(parts)
        for parts in product(
            ("public-equity", "hedge-fund", "credit", "private-market"),
            ("early", "latest"),
            ("lineage", "basis", "audit"),
        )
    }

    assert set(data["states"]) == expected_keys
    assert data["meta"]["state_count"] == 24
    assert data["meta"]["default_state"] == "hedge-fund|early|lineage"
    required = {
        "scenario",
        "cutoff",
        "view",
        "decision_at",
        "access_contexts",
        "revision_modes",
        "analytic_bundle_digest",
        "audit_bundle_digest",
        "join_receipt_ids",
        "lineage_segments",
        "basis_breaks",
        "vintage_findings",
        "portability_findings",
        "panel",
        "exclusions",
        "refusals",
        "receipt_ids",
        "conclusion",
        "limitation",
        "what_changed",
    }
    assert all(set(state) == required for state in data["states"].values())


def test_meta_scenarios_and_claim_inventory_match_the_ruled_contract(s7_data: dict) -> None:
    assert set(s7_data) == {"meta", "scenarios", "states", "claims"}
    assert s7_data["meta"]["state_axes"] == {
        "scenario": ["public-equity", "hedge-fund", "credit", "private-market"],
        "cutoff": ["early", "latest"],
        "view": ["lineage", "basis", "audit"],
    }
    assert set(s7_data["scenarios"]) == {
        "public-equity",
        "hedge-fund",
        "credit",
        "private-market",
    }
    assert len({row["label"] for row in s7_data["scenarios"].values()}) == 4
    expected_ceilings = {
        "track_lineage": "B",
        "point_in_time_vintage_audit": "B",
        "basis_breaks": "B",
        "comparable_native_panel": "B",
        "predecessor_portability_evidence": "C",
        "historical_selection_refusal": "B",
        "performance_estimator_refusal": "D",
    }
    assert set(s7_data["claims"]) == set(expected_ceilings)
    for claim_id, ceiling in expected_ceilings.items():
        claim = s7_data["claims"][claim_id]
        assert claim["current_attestation"] == "D"
        assert claim["live_attestation_ceiling"] == ceiling
        assert claim["validation_status"] == "live-calibration-required"
        assert claim["receipt_required"] is True
        assert claim["output_pointers"]
        assert set(claim["applicable_by_state"]) == set(s7_data["states"])
        assert set(claim["receipt_ids_by_state"]) == set(s7_data["states"])
        for state_key, applicable in claim["applicable_by_state"].items():
            assert bool(claim["receipt_ids_by_state"][state_key]) is applicable

    for claim_id in ("basis_breaks", "comparable_native_panel"):
        claim = s7_data["claims"][claim_id]
        assert not claim["applicable_by_state"]["public-equity|early|basis"]
        assert claim["receipt_ids_by_state"]["public-equity|early|basis"] == []
        assert claim["applicable_by_state"]["hedge-fund|early|basis"]
    portability = s7_data["claims"]["predecessor_portability_evidence"]
    assert portability["applicable_by_state"]["hedge-fund|early|lineage"]
    assert not portability["applicable_by_state"]["credit|early|lineage"]


def test_each_pair_reuses_one_full_method_result_across_three_views(s7_data: dict) -> None:
    for scenario, cutoff in product(
        ("public-equity", "hedge-fund", "credit", "private-market"),
        ("early", "latest"),
    ):
        states = [s7_data["states"][f"{scenario}|{cutoff}|{view}"] for view in s7_provenance.VIEWS]
        normalized = [
            {
                key: value
                for key, value in state.items()
                if key not in {"view", "conclusion", "what_changed"}
            }
            for state in states
        ]
        assert normalized[0] == normalized[1] == normalized[2]
        assert {state["view"] for state in states} == set(s7_provenance.VIEWS)
        assert len({state["conclusion"] for state in states}) == 3
        assert len({state["what_changed"] for state in states}) == 3


def test_actual_early_latest_values_and_revision_findings_are_held(s7_data: dict) -> None:
    states = s7_data["states"]
    public_early = states["public-equity|early|basis"]["panel"]["rows"][0]
    public_latest = states["public-equity|latest|basis"]["panel"]["rows"][0]
    assert public_early["source_value"] == public_latest["source_value"] == "0.0060"
    assert public_early["admitted_value"] == "0.02612000"
    assert public_latest["admitted_value"] == "0.02410800"
    assert public_early["fx_observation_id"] != public_latest["fx_observation_id"]

    hedge_early = states["hedge-fund|early|basis"]["panel"]
    hedge_latest = states["hedge-fund|latest|basis"]["panel"]
    assert [row["source_value"] for row in hedge_early["rows"]] == [
        "0.0060",
        "0.0100",
        "-0.0030",
    ]
    assert [row["source_value"] for row in hedge_latest["rows"]] == [
        "0.0060",
        "0.0080",
        "-0.0030",
    ]
    assert len(hedge_early["excluded_row_ids"]) == len(hedge_latest["excluded_row_ids"]) == 1

    private_early = states["private-market|early|basis"]["panel"]["rows"]
    private_latest = states["private-market|latest|basis"]["panel"]["rows"]
    early_nav = next(row for row in private_early if row["observed_at"] == "2024-03-31")
    latest_nav = next(row for row in private_latest if row["observed_at"] == "2024-03-31")
    assert early_nav["admitted_value"] == "85000000.00"
    assert latest_nav["admitted_value"] == "80000000.00"
    assert early_nav["observation_id"] != latest_nav["observation_id"]

    latest_findings = states["hedge-fund|latest|audit"]["vintage_findings"]
    restatement = next(row for row in latest_findings if row["finding_type"] == "return-restatement")
    assert restatement["prior_value"] == "0.0100"
    assert restatement["later_value"] == "0.0080"
    assert restatement["effective_at"].startswith("2024-02-29")
    assert restatement["first_known_at"].startswith("2024-09-15")
    assert {row["finding_type"] for row in latest_findings} == {
        "return-backfill",
        "return-restatement",
        "later-dead-product",
        "absence-not-inferable",
        "withdrawal-or-tombstone",
        "retroactive-membership",
    }


def test_lineage_basis_portability_and_exclusion_counts_are_exact(s7_data: dict) -> None:
    states = s7_data["states"]
    expected_lineage = {
        "public-equity|early|lineage": (1, 7, 8),
        "public-equity|latest|lineage": (1, 7, 4),
        "hedge-fund|early|lineage": (1, 7, 17),
        "hedge-fund|latest|lineage": (2, 7, 15),
        "credit|early|lineage": (1, 2, 3),
        "credit|latest|lineage": (1, 2, 0),
        "private-market|early|lineage": (1, 4, 5),
        "private-market|latest|lineage": (1, 4, 0),
    }
    for key, (segments, admitted, excluded) in expected_lineage.items():
        state = states[key]
        assert len(state["lineage_segments"]) == segments
        assert sum(len(row["observation_ids"]) for row in state["lineage_segments"]) == admitted
        assert len(state["exclusions"]) == excluded
        identities = {
            (row["dataset_id"], row["observation_id"], row["reason_code"])
            for row in state["exclusions"]
        }
        assert len(identities) == excluded

    assert states["public-equity|early|basis"]["basis_breaks"][0]["reason_codes"] == [
        "benchmark-basis-incomparable",
        "silent-stitch-prohibited",
    ]
    assert states["hedge-fund|latest|basis"]["basis_breaks"][0]["reason_codes"] == [
        "fee-basis-incomparable"
    ]
    assert states["credit|latest|basis"]["basis_breaks"][0]["reason_codes"] == [
        "frequency-calendar-incomparable",
        "valuation-basis-incomparable",
        "comparison-kind-incompatible",
        "silent-stitch-prohibited",
    ]
    assert states["private-market|latest|basis"]["basis_breaks"] == []

    early_states = [row["state"] for row in states["hedge-fund|early|lineage"]["portability_findings"]]
    latest_states = [row["state"] for row in states["hedge-fund|latest|lineage"]["portability_findings"]]
    assert early_states == ["documented-claim", "partial-support", "unresolved"]
    assert latest_states == ["contradicted", "documented-claim", "partial-support", "unresolved"]
    for scenario in ("public-equity", "credit", "private-market"):
        assert states[f"{scenario}|latest|lineage"]["portability_findings"] == []
        assert "not-assessed-no-authenticated-predecessor-bundle" in s7_data["scenarios"][scenario]["portability_scope"]


def test_policy_refusal_is_identical_receipted_and_unconditional(s7_data: dict) -> None:
    receipt_ids = set()
    for state_key, state in s7_data["states"].items():
        refusals = [
            row
            for row in state["refusals"]
            if row["pointer"] == "/refusals/performance-estimator"
        ]
        assert len(refusals) == 1
        refusal = refusals[0]
        assert refusal["current_attestation"] == refusal["live_attestation_ceiling"] == "D"
        assert refusal["receipt_id"].startswith("receipt:sha256:")
        assert refusal["receipt_id"] in state["receipt_ids"]
        assert s7_data["claims"]["performance_estimator_refusal"]["receipt_ids_by_state"][state_key] == [
            refusal["receipt_id"]
        ]
        receipt_ids.add(refusal["receipt_id"])
    assert len(receipt_ids) == 1


def _keys(value: object) -> set[str]:
    if isinstance(value, dict):
        return set(value) | {key for child in value.values() for key in _keys(child)}
    if isinstance(value, list):
        return {key for child in value for key in _keys(child)}
    return set()


def _floats(value: object):
    if isinstance(value, float):
        yield value
    elif isinstance(value, dict):
        for child in value.values():
            yield from _floats(child)
    elif isinstance(value, list):
        for child in value:
            yield from _floats(child)


def _publication_terms() -> tuple[str, ...]:
    path = Path(__file__).resolve().parents[2] / "tools" / ".publication_terms"
    if not path.exists():
        return ()
    return tuple(
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    )


def test_json_is_finite_source_safe_and_has_no_estimator_output_keys(s7_data: dict) -> None:
    assert set(FORBIDDEN_ESTIMATOR_OR_RANKING_FIELDS).isdisjoint(_keys(s7_data))
    assert all(math.isfinite(value) for value in _floats(s7_data))
    serialized = json.dumps(s7_data, sort_keys=True)
    assert not re.search(r"(?:NaN|Infinity|-Infinity)", serialized)
    assert not {"raw_document", "internal_note", "free_form_text", "manager_name"} & _keys(s7_data)
    for term in _publication_terms():
        assert not re.search(rf"\b{re.escape(term)}\b", serialized, flags=re.IGNORECASE)


def test_byte_identity_digest_and_committed_artifact(tmp_path: Path) -> None:
    first = s7_provenance.build(out_dir=tmp_path).read_bytes()
    second = s7_provenance.build(out_dir=tmp_path).read_bytes()
    assert first == second
    assert hashlib.sha256(first).hexdigest() == hashlib.sha256(second).hexdigest()
    assert first == (SITE_DATA_DIR / "s7_provenance.json").read_bytes()
