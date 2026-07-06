import json
from collections import Counter

from quant_allocator.demo_data import m5_saydo
from quant_allocator.demo_data._emit import SITE_DATA_DIR


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_schema_is_valid(tmp_path):
    data = _load(m5_saydo.build(out_dir=tmp_path))
    assert data["meta"]["manager_code"] == "M07"
    assert data["meta"]["horizon_months"] == 6
    assert len(data["views"]) == 3
    for v in data["views"]:
        assert {"view_id", "letter_date", "direction", "theme", "instrument",
                "horizon_months", "conviction", "quote", "measured", "label"} <= set(v)
        assert set(v["measured"]) == {"start", "end", "move", "delta"}
        assert v["direction"] in {"long/constructive", "short/cautious", "neutral-explicit"}
    assert set(data["exposure_paths"]) == {"beta_market", "beta_value", "beta_momentum", "net"}


def test_labels_are_two_aligned_one_contradicted(tmp_path):
    data = _load(m5_saydo.build(out_dir=tmp_path))
    labels = Counter(v["label"] for v in data["views"])
    assert all(lbl in {"aligned", "partial", "contradicted"} for lbl in labels)
    assert labels["aligned"] == 2
    assert labels["contradicted"] == 1


def test_byte_for_byte_determinism_and_matches_committed(tmp_path):
    first = m5_saydo.build(out_dir=tmp_path).read_bytes()
    second = m5_saydo.build(out_dir=tmp_path).read_bytes()
    assert first == second
    committed = (SITE_DATA_DIR / "m5_saydo.json").read_bytes()
    assert first == committed


def test_measured_move_matches_start_and_end(tmp_path):
    data = _load(m5_saydo.build(out_dir=tmp_path))
    for v in data["views"]:
        assert abs(v["measured"]["move"] - (v["measured"]["end"] - v["measured"]["start"])) < 1e-6
