import json
import math
from pathlib import Path

from quant_allocator.demo_data import m6_holdings
from quant_allocator.demo_data._emit import SITE_DATA_DIR
from quant_allocator.demo_data.roster import MANAGER_NAMES


APPROVED_NAMES = {
    "Vesper Lane Capital",
    "Corbin Vale Capital",
    "Bexley Court Capital",
    "Tanager Hill Capital",
    "Kettering Partners",
    "Hensley Park Advisors",
}


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _walk(value):
    if isinstance(value, dict):
        for key, child in value.items():
            yield key, child
            yield from _walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk(child)


def test_six_filer_schema_and_gate_contrast(tmp_path):
    data = _load(m6_holdings.build(out_dir=tmp_path))
    assert data["meta"]["generator"] == "m6_holdings"
    assert data["meta"]["held_for_gate"] is True
    assert set(data["filers"]) == APPROVED_NAMES
    assert len(data["filers"]) == 6
    assert len(data["vesper"]["timeline"]["quarters"]) == 6

    vesper = data["vesper"]
    hensley = data["hensley"]
    assert vesper["gate"]["pass"] is True
    assert vesper["concentration"] is not None
    assert vesper["overlap"] is not None
    assert hensley["gate"]["pass"] is False
    assert hensley["concentration"] is None
    assert hensley["overlap"] is None
    assert hensley["persistence"]


def test_centerpiece_has_concentration_persistence_and_moderate_overlap(tmp_path):
    data = _load(m6_holdings.build(out_dir=tmp_path))
    vesper = data["vesper"]
    quarters = vesper["timeline"]["quarters"]
    assert quarters[-1]["effective_names"] < quarters[0]["effective_names"] - 1.0
    crossing = vesper["timeline"]["first_majority_crossing"]
    assert crossing is not None
    assert crossing["share"] > 0.50
    latest_top_three = vesper["timeline"]["positions"][:3]
    assert len(latest_top_three) == 3
    assert all(row["quarters_held"] == 6 for row in latest_top_three)
    assert 0.10 <= vesper["overlap"] <= 0.50
    assert 0.75 <= vesper["coverage"] <= 0.98
    assert 0.19 <= data["hensley"]["coverage"] <= 0.21


def test_receipts_options_caveats_and_finra_placeholder(tmp_path):
    data = _load(m6_holdings.build(out_dir=tmp_path))
    for quarter in data["vesper"]["timeline"]["quarters"]:
        assert quarter["as_of"]
        assert quarter["known_at"]
        assert quarter["lag_days"] == 45
    assert len(data["caveats"]) == 4
    assert data["vesper"]["option_share"] == 0.0
    assert data["vesper"]["option_heavy"] is False
    assert data["short_interest"]["status"] == "requires FINRA adapter"
    lowered_keys = {str(key).lower() for key, _ in _walk(data)}
    assert "days_to_cover" not in lowered_keys
    assert "dtc" not in lowered_keys
    assert "short_interest_value" not in lowered_keys


def test_json_is_finite_and_names_do_not_collide(tmp_path):
    data = _load(m6_holdings.build(out_dir=tmp_path))
    assert APPROVED_NAMES.isdisjoint(MANAGER_NAMES.values())
    for _, value in _walk(data):
        if isinstance(value, float):
            assert math.isfinite(value)
    for path in SITE_DATA_DIR.glob("*.json"):
        if path.name == "m6_holdings.json":
            continue
        text = path.read_text(encoding="utf-8").lower()
        for name in APPROVED_NAMES:
            assert name.lower() not in text


def test_byte_for_byte_determinism_and_matches_committed(tmp_path):
    first = m6_holdings.build(out_dir=tmp_path).read_bytes()
    second = m6_holdings.build(out_dir=tmp_path).read_bytes()
    assert first == second
    assert first == (SITE_DATA_DIR / "m6_holdings.json").read_bytes()
