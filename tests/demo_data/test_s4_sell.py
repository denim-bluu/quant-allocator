import json

import pytest

from quant_allocator.demo_data import s4_sell
from quant_allocator.demo_data._emit import SITE_DATA_DIR

pytestmark = pytest.mark.slow  # 2000-rep cohort bootstrap x 3 books x (gap + 6 curve + trend)


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_schema_and_three_books(tmp_path):
    data = _load(s4_sell.build(out_dir=tmp_path))
    assert data["meta"]["generator"] == "s4_sell"
    assert data["meta"]["idio_ar1"] == 0.4
    assert data["meta"]["market_seed"] == 8
    roles = {m["role"]: m for m in data["managers"]}
    assert set(roles) == {"disciplined", "disposition", "ghost"}
    assert roles["disciplined"]["name"] == "Larkspur Ridge Partners"
    assert roles["disposition"]["name"] == "Redgate Harbor Capital"


def test_two_manager_split_directions_and_ghost_zero(tmp_path):
    # The centerpiece invariants (spec §5) — signs and straddles, NOT magnitudes.
    data = _load(s4_sell.build(out_dir=tmp_path))
    roles = {m["role"]: m for m in data["managers"]}
    disc = roles["disciplined"]["headline"]
    dispo = roles["disposition"]["headline"]
    ghost = roles["ghost"]["headline"]
    assert disc["ci_hi"] < 0.0          # culls well: band excludes zero, negative
    assert dispo["ci_lo"] > 0.0         # leaks: band excludes zero, positive
    assert ghost["ci_lo"] < 0.0 < ghost["ci_hi"]      # a visible zero
    assert roles["disciplined"]["verdict_chip"] == "culls well"
    assert roles["disposition"]["verdict_chip"] == "edge leaks at the exit"


def test_headline_horizon_and_slider_range(tmp_path):
    data = _load(s4_sell.build(out_dir=tmp_path))
    m = data["managers"][0]
    assert data["meta"]["horizon_months"] == 4
    assert [h["horizon"] for h in m["horizons"]] == [1, 2, 3, 4, 5, 6]
    # n is constant across the slider (exit set fixed at the max horizon).
    assert len({h["n_exits"] for h in m["horizons"]}) == 1
    assert m["n_exits"] >= 150          # the demo book clears the headline gate


def test_curve_is_interval_per_forward_month(tmp_path):
    data = _load(s4_sell.build(out_dir=tmp_path))
    dispo = next(m for m in data["managers"] if m["role"] == "disposition")
    assert len(dispo["curve"]) == data["meta"]["horizon_months"]
    for pt in dispo["curve"]:
        assert pt["lo"] <= pt["point"] <= pt["hi"]


def test_design_effect_reported_and_below_one(tmp_path):
    # Spec §3.6: a selective rule stratifies month cohorts -> deff < 1 (the honest,
    # both-directions behavior). Reported beside the interval.
    data = _load(s4_sell.build(out_dir=tmp_path))
    for m in data["managers"]:
        assert "design_effect" in m["headline"]
    dispo = next(m for m in data["managers"] if m["role"] == "disposition")
    assert dispo["headline"]["design_effect"] < 1.0


def test_trend_yearly_rendered_quarterly_refused(tmp_path):
    data = _load(s4_sell.build(out_dir=tmp_path))
    trend = data["managers"][0]["trend"]
    assert any(b["sufficient"] for b in trend["yearly"])
    assert trend["quarterly_refused"] is True
    assert trend["quarterly_exits_per_bucket"] > 0
    assert trend["quarterly_se_bp"] > 0


def test_roster_shrink_present(tmp_path):
    data = _load(s4_sell.build(out_dir=tmp_path))
    roster = data["roster"]
    assert {r["name"] for r in roster} == {
        "Larkspur Ridge Partners", "Redgate Harbor Capital"}
    for r in roster:
        assert "shrunk_gap" in r and "shrunk_sd" in r


def test_byte_for_byte_determinism_and_matches_committed(tmp_path):
    first = s4_sell.build(out_dir=tmp_path).read_bytes()
    second = s4_sell.build(out_dir=tmp_path).read_bytes()
    assert first == second
    committed = (SITE_DATA_DIR / "s4_sell.json").read_bytes()
    assert first == committed
