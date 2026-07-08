import json

import pytest

from quant_allocator.demo_data import s3_lab
from quant_allocator.demo_data._emit import SITE_DATA_DIR

pytestmark = pytest.mark.slow  # many simulate_manager loops + SIZING_BOOTSTRAP_N resamples


def _fixture_registry(tmp_path):
    # A populated registry so the refusal copy can quote a threshold; the real committed
    # registry is an integration dependency (see plan Handoff).
    reg = tmp_path / "powergate_registry.json"
    reg.write_text(json.dumps({"version": 1, "metrics": {
        "hit_rate": {"gate_quantity": "independent_trades", "threshold": 780},
        "sizing_slope": {"gate_quantity": "independent_trades", "threshold": 780},
    }}), encoding="utf-8")
    return reg


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_schema_and_picker_sizer_share_identical_picks(tmp_path):
    data = _load(s3_lab.build(out_dir=tmp_path, registry_path=_fixture_registry(tmp_path)))
    assert data["meta"]["generator"] == "s3_lab"
    assert data["meta"]["cluster_axes"] == ["date"]
    split = {m["role"]: m for m in data["split"]}
    assert set(split) == {"sizer", "picker"}
    assert split["sizer"]["name"] == "Meridian Arc Capital"
    assert split["picker"]["name"] == "Kelso Bay Partners"
    # Same picks: identical independent-trade counts and identical holding-age footprint.
    assert split["sizer"]["independent_trades"] == split["picker"]["independent_trades"] == 1985
    # Sizer's slope clears (t and interval), picker's straddles zero.
    assert split["sizer"]["slope"]["tstat"] > 1.96
    assert split["sizer"]["slope"]["ci_low"] > 0.0
    assert split["picker"]["slope"]["ci_low"] < 0.0 < split["picker"]["slope"]["ci_high"]
    # The conviction premium is the alpha gap between the sizer and its equal-weight shadow.
    assert data["sizing_value"]["gap_annual"] == pytest.approx(
        split["sizer"]["alpha_annual"] - split["picker"]["alpha_annual"], abs=1e-9)
    assert data["sizing_value"]["gap_annual"] > 0.0


def test_decay_recovers_half_life_and_reports_wide_single_manager_band(tmp_path):
    data = _load(s3_lab.build(out_dir=tmp_path, registry_path=_fixture_registry(tmp_path)))
    decay = data["decay"]
    assert len(decay["curve"]) == s3_lab.DECAY_MAX_AGE + 1
    assert abs(decay["half_life_pooled"] - 6.0) < 1.0        # pooled fit recovers the 6.0 dial
    assert decay["half_life_ages_0_12"] < decay["half_life_pooled"]  # entry premium biases short
    lo, hi = decay["single_manager_ci"]["lo"], decay["single_manager_ci"]["hi"]
    assert lo < decay["half_life_pooled"] < hi and (hi - lo) > 3.0   # honest wide band


def test_holding_decomposition_and_powergate_refusal(tmp_path):
    data = _load(s3_lab.build(out_dir=tmp_path, registry_path=_fixture_registry(tmp_path)))
    shares = data["holding"]["shares"]
    # Shares sum to 1.0 exactly (verified at 1e-9 on unrounded values in the pipeline test);
    # the JSON rounds each of the 4 shares to 6 decimals, so the loaded sum can drift by up
    # to ~2e-6. A real decomposition bug would be percent-level, so 1e-5 is a safe floor.
    assert abs(sum(v for v in shares.values()) - 1.0) < 1e-5
    gate = data["powergate"]
    assert gate["name"] == "Thornwood Select"
    assert gate["independent_trades"] == 174
    assert gate["renders_slope"] is False                    # below the gate -> refusal
    assert gate["hit_rate_threshold"] == 780                 # read from the registry
    assert gate["reference_effect_never_clears"] is True     # §8 ruling 2 sentence flag


def test_byte_for_byte_determinism_and_matches_committed(tmp_path):
    reg = _fixture_registry(tmp_path)
    first = s3_lab.build(out_dir=tmp_path, registry_path=reg).read_bytes()
    second = s3_lab.build(out_dir=tmp_path, registry_path=reg).read_bytes()
    assert first == second
    committed = (SITE_DATA_DIR / "s3_lab.json").read_bytes()
    assert first == committed


def test_sizer_and_picker_hold_byte_identical_positions():
    import numpy as np
    market, sizer_hist, picker_hist = s3_lab._split_histories()
    del market
    # Only sizing differs -> identical held/unheld pattern, ages, and side.
    assert np.array_equal(sizer_hist.weights.to_numpy() != 0.0,
                          picker_hist.weights.to_numpy() != 0.0)
    assert np.array_equal(np.sign(sizer_hist.weights.to_numpy()),
                          np.sign(picker_hist.weights.to_numpy()))
    # ...but the weight magnitudes genuinely differ (conviction vs equal weight).
    assert not np.allclose(sizer_hist.weights.to_numpy(), picker_hist.weights.to_numpy())
