import json

from quant_allocator.demo_data import m1_drift
from quant_allocator.demo_data._emit import SITE_DATA_DIR


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_schema_is_valid(tmp_path):
    data = _load(m1_drift.build(out_dir=tmp_path))
    assert data["meta"]["monitored_class"] == "beta_market"
    assert data["meta"]["tier"] == "E"
    band = data["band"]
    assert band["lower"] == -0.10 and band["upper"] == 0.10
    v = data["visual"]
    assert len(v["beta_path"]) == len(v["months"]) == m1_drift.DEMO_HORIZON
    assert len(v["s_plus"]) == m1_drift.DEMO_HORIZON
    assert len(v["wander_p50"]) == m1_drift.DEMO_HORIZON
    for stat in (data["operating"]["detection_e"], data["operating"]["detection_r"]):
        assert stat["ci_lo"] <= stat["rate"] <= stat["ci_hi"]
    slope = data["factor_share"]["slope"]
    assert slope["ci_lo"] <= slope["point"] <= slope["ci_hi"]


def test_demo_alarm_fires_after_drift_onset(tmp_path):
    # The authored centerpiece: the CUSUM lights up on the sustained walk, and only
    # after the drift begins (never before onset).
    data = _load(m1_drift.build(out_dir=tmp_path))
    v = data["visual"]
    assert v["alarm_month"] is not None
    assert v["alarm_month"] >= v["drift_onset"]


def test_e_tier_clears_and_beats_r_tier(tmp_path):
    # Tier-degradation, measured: E (measured path) detects the pinned walk at a usable
    # operating point; R (rolling-beta inference) detects less (M1 spec §3.6, §4.3).
    data = _load(m1_drift.build(out_dir=tmp_path))
    op = data["operating"]
    assert op["size_e"]["rate"] <= op["budget_per_year"] + 1e-9
    assert op["detection_e"]["rate"] >= m1_drift.DETECTION_FLOOR
    assert op["detection_e"]["rate"] >= op["detection_r"]["rate"]
    assert data["alarm_cleared"] is True


def test_wander_band_is_ordered(tmp_path):
    data = _load(m1_drift.build(out_dir=tmp_path))
    v = data["visual"]
    for lo, mid, hi in zip(v["wander_p05"], v["wander_p50"], v["wander_p95"]):
        assert lo <= mid <= hi


def test_factor_share_rises_over_the_walk(tmp_path):
    # As net beta walks up, the factor-explained share of variance rises (M1 §3.5).
    data = _load(m1_drift.build(out_dir=tmp_path))
    assert data["factor_share"]["slope"]["point"] > 0.0
    assert data["factor_share"]["verdict"] == "rising"


def test_byte_for_byte_determinism_and_matches_committed(tmp_path):
    first = m1_drift.build(out_dir=tmp_path).read_bytes()
    second = m1_drift.build(out_dir=tmp_path).read_bytes()
    assert first == second
    committed = (SITE_DATA_DIR / "m1_drift.json").read_bytes()
    assert first == committed
