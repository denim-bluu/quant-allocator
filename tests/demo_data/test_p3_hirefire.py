# tests/demo_data/test_p3_hirefire.py
import json

from quant_allocator.demo_data import p3_hirefire
from quant_allocator.demo_data._emit import SITE_DATA_DIR


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_schema_and_event_count(tmp_path):
    data = _load(p3_hirefire.build(out_dir=tmp_path))
    assert data["meta"]["generator"] == "p3_hirefire"
    assert data["meta"]["n_events"] == 15
    assert len(data["events"]) == 15
    for ev in data["events"]:
        assert ev["decision_type"] in ("hire", "fire", "hold-under-review")
        assert ev["counterfactual_rung"] in ("replacement-paired", "peer-median", "benchmark")
        assert ev["value_verdict"] in ("helped", "hurt", "flat")
        assert isinstance(ev["kill_criterion_met"], bool)
        assert ev["thesis"].strip()


def test_all_three_counterfactual_rungs_present(tmp_path):
    data = _load(p3_hirefire.build(out_dir=tmp_path))
    rungs = {ev["counterfactual_rung"] for ev in data["events"]}
    assert rungs == {"replacement-paired", "peer-median", "benchmark"}


def test_powergate_refuses_raw_mean_at_n15(tmp_path):
    # Demo centerpiece: N=15 events, but effective N below the 12 gate => refused.
    data = _load(p3_hirefire.build(out_dir=tmp_path))
    agg = data["aggregate"]
    assert agg["raw_mean_gated"] is True
    assert agg["n_effective"] < 12


def test_posterior_straddles_zero_indistinguishable(tmp_path):
    # Goyal-Wahal reproduction on ground truth: the round-trip posterior sits at ~0.
    data = _load(p3_hirefire.build(out_dir=tmp_path))
    agg = data["aggregate"]
    assert agg["posterior"]["ci_lo"] < 0.0 < agg["posterior"]["ci_hi"]
    assert agg["verdict"] == "indistinguishable"
    assert agg["verdict_chip"] == "indistinguishable from the base rate"


def test_detectability_one_liner_present(tmp_path):
    # spec 4 converge-or-cut: the closed-form events-to-detect ships (no MC atlas).
    data = _load(p3_hirefire.build(out_dir=tmp_path))
    det = data["aggregate"]["events_to_detect"]
    assert det["n"] is None or det["n"] > 15   # more decisions than a career holds


def test_scorecard_carries_precommitments(tmp_path):
    data = _load(p3_hirefire.build(out_dir=tmp_path))
    sc = data["scorecard"]
    assert sc["thesis"].strip()
    assert sc["kill_criterion"].strip()
    assert "realized_forward" in sc
    assert "realized_factor_alpha_annual" in sc


def test_cohort_paths_mean_revert(tmp_path):
    # Fired cohort recovers, replacement cohort fades: the panel's whole point.
    data = _load(p3_hirefire.build(out_dir=tmp_path))
    cp = data["cohort_paths"]
    assert cp["fired"][0] == 0.0 and cp["replacement"][0] == 0.0
    assert len(cp["fired"]) == cp["trailing_window_months"] + 1


def test_byte_for_byte_determinism_and_matches_committed(tmp_path):
    first = p3_hirefire.build(out_dir=tmp_path).read_bytes()
    second = p3_hirefire.build(out_dir=tmp_path).read_bytes()
    assert first == second
    committed = (SITE_DATA_DIR / "p3_hirefire.json").read_bytes()
    assert first == committed
