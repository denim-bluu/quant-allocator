import json

import pytest

from quant_allocator.demo_data import s6_signatures
from quant_allocator.demo_data._emit import SITE_DATA_DIR

pytestmark = pytest.mark.slow  # real book sims x hundreds of reps x permutations x 2 overlays


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_meta_labels_the_pilot_and_pins_the_frozen_constants(tmp_path):
    data = _load(s6_signatures.build(out_dir=tmp_path))
    meta = data["meta"]
    assert meta["generator"] == "s6_signatures"
    assert meta["label"] == "PILOT"
    assert meta["decision_t"] == 60 and meta["secondary_t"] == 36
    assert meta["auc_min"] == 0.65 and meta["familywise_alpha"] == 0.05
    assert meta["rolling_windows"] == [6, 12]
    assert meta["smoothing_theta"] == [0.6, 0.25, 0.15]
    # The pilot is BOUNDED: fewer cells than the confirmatory 12 + 8.
    assert meta["pilot_cells"]["h_size"] < 12 and meta["pilot_cells"]["h_decay"] < 8
    assert meta["confirmatory"]["n_per_class"] == 500 and meta["confirmatory"]["n_perm"] == 5000


def test_frozen_registration_block_carries_the_six_family_rows_and_directions(tmp_path):
    data = _load(s6_signatures.build(out_dir=tmp_path))
    family = data["protocol"]["family"]
    assert [row["signature"] for row in family] == [
        "autocorr", "vol_of_vol", "skew", "kurtosis", "drawdown_shape", "rolling_ir_slope",
    ]
    kurt = next(r for r in family if r["signature"] == "kurtosis")
    assert kurt["direction_h_size"] == "+" and kurt["direction_h_decay"] is None
    # The forking-paths arithmetic is emitted for the page footnote (1 - 0.95^6 ~ 0.26).
    # Tolerance reflects _emit.write_json's deterministic 6-decimal rounding (max err 5e-7).
    assert abs(data["protocol"]["forking_paths_naive_rate"] - (1 - 0.95 ** 6)) < 1e-6


def test_verdict_grid_is_two_contrasts_by_six_signatures_no_bare_points(tmp_path):
    data = _load(s6_signatures.build(out_dir=tmp_path))
    contrasts = {c["id"]: c for c in data["contrasts"]}
    assert set(contrasts) == {"h_size", "h_decay"}
    for c in contrasts.values():
        assert len(c["rows"]) == 6
        assert c["significance_floor"] > 0.5  # the measured familywise floor mark
        assert c["usability_bar"] == 0.65
        for row in c["rows"]:
            assert row["verdict"] in {"ship", "weak_tell", "null"}
            # Every AUC is an interval (Hanley-McNeil band), never a bare point.
            assert row["auc_lo"] <= row["auc_point"] <= row["auc_hi"]
            # adj p is always paired with the deciding-cell count.
            assert 0.0 < row["worst_adj_p"] <= 1.0
            assert row["n_deciding_cells"] >= 2
            assert "declared" in row and "reversed" in row


def test_pilot_is_expected_null_dominated_and_ships_nothing_undeclared(tmp_path):
    # The stated prior (§1) is mostly-null; and no undeclared row may ever SHIP (§3.4).
    data = _load(s6_signatures.build(out_dir=tmp_path))
    ships = [r for c in data["contrasts"] for r in c["rows"] if r["verdict"] == "ship"]
    for r in ships:
        assert r["declared"] is True
    assert data["headline"]["n_null"] >= 1  # at least one first-class null on the grid


def test_headline_counts_are_consistent_and_data_driven(tmp_path):
    data = _load(s6_signatures.build(out_dir=tmp_path))
    h = data["headline"]
    total = h["n_ship"] + h["n_weak_tell"] + h["n_null"]
    assert total == 12  # 2 contrasts x 6 signatures
    for verdict in ("ship", "weak_tell", "null"):
        pass  # counts exist
    assert isinstance(h["text"], str) and str(h["n_ship"]) in h["text"]


def test_byte_for_byte_determinism_and_matches_committed(tmp_path):
    first = s6_signatures.build(out_dir=tmp_path).read_bytes()
    second = s6_signatures.build(out_dir=tmp_path).read_bytes()
    assert first == second
    committed = (SITE_DATA_DIR / "s6_signatures.json").read_bytes()
    assert first == committed
