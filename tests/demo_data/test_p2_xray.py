import json
from pathlib import Path

import pytest

from quant_allocator.demo_data import p2_xray

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_roster_tiers_weights_and_names_are_valid(tmp_path):
    data = _load(p2_xray.build(tmp_path))
    assert len(data["managers"]) == p2_xray.DEMO_BOOK_N == 15
    assert {tier: sum(m["tier"] == tier for m in data["managers"])
            for tier in ("R", "E", "P")} == {"R": 9, "E": 4, "P": 2}
    assert sum(m["capital_weight"] for m in data["managers"]) == pytest.approx(1.0)
    names = [m["name"] for m in data["managers"]]
    assert len(set(names)) == len(names)
    assert "Westermark Strategies" in names
    assert "Juniper Vale Partners" in names
    assert "Ternhaven Capital" in names


def test_payload_invariants_and_gate_arithmetic(tmp_path):
    data = _load(p2_xray.build(tmp_path))
    book = data["book"]
    assert book["ci_lo"] <= book["point"] <= book["ci_hi"]
    assert sum(data["tier_provenance"].values()) == pytest.approx(1.0, abs=2e-6)
    gate = data["information_gate"]
    assert gate["gain"] == pytest.approx(
        1.0 - gate["all_e_sd"] / gate["all_r_sd"], abs=5e-6
    )
    assert gate["renders"] == (gate["gain"] >= gate["floor"])
    assert data["tier_monotonicity"]
    assert data["tier_provenance"]["R"] > data["tier_provenance"]["E"]
    assert data["tier_provenance"]["R"] > data["tier_provenance"]["P"]
    expected_unfused = sum(
        manager["capital_weight"] * manager["observation"] for manager in data["managers"]
    )
    assert data["unfused_book"]["point"] == pytest.approx(expected_unfused, abs=2e-6)
    assert data["unfused_book"]["label"] == "un-fused — tiers not reconciled"


def test_observation_sources_match_tiers_and_e_values_use_bucket_grid(tmp_path):
    data = _load(p2_xray.build(tmp_path))
    expected_sources = {
        "R": "returns_regression_proxy",
        "E": "coarsened_exposure_emission",
        "P": "position_transparent_emission",
    }
    width = data["constants"]["op_bucket_width"]
    for manager in data["managers"]:
        assert manager["observation_source"] == expected_sources[manager["tier"]]
        if manager["tier"] == "E":
            assert manager["observation"] / width == pytest.approx(
                round(manager["observation"] / width), abs=1e-9
            )


def test_dial_states_reuse_observations(tmp_path):
    data = _load(p2_xray.build(tmp_path))
    expected = [m["observation"] for m in data["managers"]]
    for state in data["r_noise_dial"]:
        assert state["observations"] == expected


def test_names_do_not_collide_with_other_committed_json():
    other_text = "\n".join(
        path.read_text(encoding="utf-8").lower()
        for path in sorted((REPO_ROOT / "site" / "data").glob("*.json"))
        if path.name != "p2_xray.json"
    )
    for name in p2_xray.P2_NAMES:
        assert name.lower() not in other_text


def test_payload_uses_no_publication_canary_terms(tmp_path):
    canary_path = REPO_ROOT / "tools" / ".publication_terms"
    if not canary_path.exists():
        pytest.skip("local publication canary is not present")
    terms = [
        line.strip().lower()
        for line in canary_path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    payload = p2_xray.build(tmp_path).read_text(encoding="utf-8").lower()
    for term in terms:
        assert term not in payload


def test_byte_for_byte_determinism_and_matches_committed(tmp_path):
    first = p2_xray.build(tmp_path / "first").read_bytes()
    second = p2_xray.build(tmp_path / "second").read_bytes()
    committed = (REPO_ROOT / "site" / "data" / "p2_xray.json").read_bytes()
    assert first == second == committed
