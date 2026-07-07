import json

from quant_allocator.demo_data import e2_pack
from quant_allocator.demo_data._emit import SITE_DATA_DIR


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_schema_and_manager(tmp_path):
    data = _load(e2_pack.build(out_dir=tmp_path))
    assert data["meta"]["manager_code"] == "M07"
    assert data["meta"]["manager_name"] == "Kestrelmoor Partners"
    assert data["meta"]["tier"] == "R"
    ids = [s["section_id"] for s in data["sections"]]
    assert ids == ["posterior_standing", "tear_sheet", "say_do", "exposure_drift"]


def test_three_section_states_present(tmp_path):
    data = _load(e2_pack.build(out_dir=tmp_path))
    states = {s["section_id"]: s["state"] for s in data["sections"]}
    assert states["posterior_standing"] == "refused"   # X1 null threshold
    assert states["tear_sheet"] == "rendered"
    assert states["say_do"] == "rendered"
    assert states["exposure_drift"] == "omitted"        # tier R < E
    # Never silently dropped: the omission is footnoted (title + tier).
    assert data["footer"]["omitted"] == [
        {"section": "exposure_drift", "title": "Exposure hygiene & drift", "needs_tier": "E"}
    ]


def test_rendered_stats_are_intervals_or_verdicts(tmp_path):
    data = _load(e2_pack.build(out_dir=tmp_path))
    tear = next(s for s in data["sections"] if s["section_id"] == "tear_sheet")
    kinds = {stat["kind"] for stat in tear["stats"]}
    assert kinds <= {"interval", "verdict"}
    # De-smoothed Sharpe carries a full interval (no bare point).
    interval = next(s for s in tear["stats"] if s["kind"] == "interval")
    assert {"point", "ci_lo", "ci_hi"} <= interval.keys()


def test_refusal_carries_gate_not_a_number(tmp_path):
    data = _load(e2_pack.build(out_dir=tmp_path))
    standing = next(s for s in data["sections"] if s["section_id"] == "posterior_standing")
    assert standing["gate"]["metric"] == "ols_alpha_ttest"
    assert standing["gate"]["threshold"] is None
    assert standing["gate"]["measured"] == 48
    assert "stats" not in standing  # a refused section renders no statistic


def test_narration_is_numerically_faithful(tmp_path):
    # The generator calls compose -> lint_pack; if narration invented a number
    # the build would already have raised. This asserts the committed values.
    data = _load(e2_pack.build(out_dir=tmp_path))
    tear = next(s for s in data["sections"] if s["section_id"] == "tear_sheet")
    assert "0.71" in tear["display_numbers"]
    assert "0.60" in tear["display_numbers"]


def test_byte_for_byte_determinism_and_matches_committed(tmp_path):
    first = e2_pack.build(out_dir=tmp_path).read_bytes()
    second = e2_pack.build(out_dir=tmp_path).read_bytes()
    assert first == second
    committed = (SITE_DATA_DIR / "e2_pack.json").read_bytes()
    assert first == committed
