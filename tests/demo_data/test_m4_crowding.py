import json
import re

import numpy as np
import pytest

from quant_allocator.demo_data import m4_crowding
from quant_allocator.demo_data._emit import SITE_DATA_DIR


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_schema_and_p_tier_provenance(tmp_path):
    data = _load(m4_crowding.build(out_dir=tmp_path))
    assert data["meta"]["tier"] == "P"
    assert data["meta"]["source"] == "emit_tiers().transparency"
    assert data["meta"]["n_managers"] == 6
    assert data["meta"]["n_assets"] == m4_crowding.N_ASSETS_M4
    assert len(data["managers"]) == len(data["heatmap"]["managers"]) == 6
    for key in ("raw", "cosine", "liquidity"):
        matrix = np.asarray(data["heatmap"][key])
        assert matrix.shape == (6, 6)
        assert np.isfinite(matrix).all()


def test_centerpiece_is_hot_and_liquidity_reveals_hidden_overlap(tmp_path):
    data = _load(m4_crowding.build(out_dir=tmp_path))
    pair = data["pair_centerpiece"]
    assert pair["manager_a"] == "Hollowmere Capital"
    assert pair["manager_b"] == "Brackenford Partners"
    assert pair["liquidity"] > pair["raw"]
    assert pair["liquidity"] >= pair["alert_threshold"]
    matrix = np.asarray(data["heatmap"]["liquidity"])
    off_diagonal = matrix[~np.eye(len(matrix), dtype=bool)]
    assert pair["liquidity"] == max(off_diagonal)


def test_stress_scenarios_are_precomputed_and_robust_fields_are_separate(tmp_path):
    data = _load(m4_crowding.build(out_dir=tmp_path))
    scenarios = data["stress_scenarios"]
    assert [row["stress_delta"] for row in scenarios] == list(m4_crowding.STRESS_GRID_M4)
    worst_days = [row["worst"]["days_stressed_volume"] for row in scenarios]
    assert worst_days == sorted(worst_days)
    assert worst_days[-1] == pytest.approx(4.0 * worst_days[0], abs=1e-6)
    for scenario in scenarios:
        for row in scenario["rows"]:
            assert set(row) == {
                "asset",
                "direction",
                "holder_count",
                "combined_dollars",
                "days_stressed_volume",
                "illustrative",
            }
            assert "impact_rate" not in row
            assert row["illustrative"]["impact_rate"] is not None


def _display_names(value, parent_key=None):
    names = []
    if isinstance(value, dict):
        for key, item in value.items():
            if key in {"name", "manager_name"} and isinstance(item, str):
                names.append(item)
            elif key == "names" and isinstance(item, dict):
                names.extend(v for v in item.values() if isinstance(v, str))
            names.extend(_display_names(item, key))
    elif isinstance(value, list):
        for item in value:
            names.extend(_display_names(item, parent_key))
    return names


def _collision_key(name):
    first = re.sub(r"[^a-z]", "", name.lower().split()[0])
    return first[:7]


def test_m4_names_do_not_collide_with_full_committed_inventory():
    m4_names = [row["name"] for row in m4_crowding.MANAGERS]
    assert len(m4_names) == len(set(m4_names))
    other_names = []
    for path in sorted((SITE_DATA_DIR).glob("*.json")):
        if path.name == "m4_crowding.json":
            continue
        other_names.extend(_display_names(_load(path)))
    other_exact = set(other_names)
    other_keys = {_collision_key(name) for name in other_names if name.strip()}
    for name in m4_names:
        assert name not in other_exact
        assert _collision_key(name) not in other_keys


def test_byte_for_byte_determinism_and_matches_committed(tmp_path):
    first = m4_crowding.build(out_dir=tmp_path).read_bytes()
    second = m4_crowding.build(out_dir=tmp_path).read_bytes()
    assert first == second
    assert first == (SITE_DATA_DIR / "m4_crowding.json").read_bytes()


def test_no_nonfinite_json_tokens(tmp_path):
    text = m4_crowding.build(out_dir=tmp_path).read_text(encoding="utf-8")
    assert not any(token in text for token in ("NaN", "Infinity", "-Infinity"))
