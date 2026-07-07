import json

import pytest

from quant_allocator.demo_data import m3_alarms
from quant_allocator.demo_data._emit import SITE_DATA_DIR

pytestmark = pytest.mark.slow  # 10_000-path alarms x ~14 managers; offline generator


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_schema_and_two_manager_split(tmp_path):
    data = _load(m3_alarms.build(out_dir=tmp_path))
    assert data["meta"]["generator"] == "m3_alarms"
    assert data["meta"]["window"] == "full_track"
    assert data["meta"]["n_paths"] == 10000
    split = {m["role"]: m for m in data["split"]}
    assert set(split) == {"trend", "credit"}
    # Same realized -12% drawdown, opposite verdicts (the centerpiece).
    assert abs(split["trend"]["realized_mdd"] - 0.12) <= 0.01
    assert abs(split["credit"]["realized_mdd"] - 0.12) <= 0.01
    assert split["trend"]["level"] == "green"
    assert split["credit"]["level"] == "red"
    # The credit book's -12% sits deep in its own null; the trend book's does not.
    assert split["credit"]["mdd_percentile"] >= 95.0
    assert split["trend"]["mdd_percentile"] < 95.0
    # Each manager carries a precomputed Sharpe fan for the Dietvorst dial.
    for m in split.values():
        assert len(m["fan"]) == 3
        for entry in m["fan"]:
            assert entry["level"] in {"green", "amber", "red"}
            assert "sharpe" in entry and "mdd_percentile" in entry
        assert len(m["band"]["band_red"]) == m["months"]
        assert len(m["band"]["running_mdd_realized"]) == m["months"]


def test_roster_heat_list_and_expected_false_count(tmp_path):
    data = _load(m3_alarms.build(out_dir=tmp_path))
    roster = data["roster"]
    assert roster["size"] == len(roster["managers"])
    # Fictional names only (drawn from the house roster).
    from quant_allocator.demo_data.roster import MANAGER_NAMES
    for mgr in roster["managers"]:
        assert mgr["name"] in MANAGER_NAMES.values()
        assert mgr["level"] in {"green", "amber", "red"}
    # The printed count is N x per-manager RED budget (spec §3.4), not a fitted number.
    assert roster["expected_false_red"] == roster["size"] * 0.01
    assert roster["observed_red"] == sum(m["level"] == "red" for m in roster["managers"])


def test_byte_for_byte_determinism_and_matches_committed(tmp_path):
    first = m3_alarms.build(out_dir=tmp_path).read_bytes()
    second = m3_alarms.build(out_dir=tmp_path).read_bytes()
    assert first == second
    committed = (SITE_DATA_DIR / "m3_alarms.json").read_bytes()
    assert first == committed
