import json

from quant_allocator.demo_data import x1_atlas
from quant_allocator.demo_data._emit import SITE_DATA_DIR


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_three_exhibits_present(tmp_path):
    data = _load(x1_atlas.build(out_dir=tmp_path))
    assert set(data) >= {"meta", "power_curves", "degradation_table", "registry_snippet"}
    # Exhibit 1: one curve per IC level, each with OLS and posterior series over T.
    curves = data["power_curves"]
    assert len(curves) == len(x1_atlas.SAMPLER_IC_LEVELS)
    for curve in curves:
        assert set(curve) >= {"ic", "measured_ir", "T", "ols_ttest", "posterior"}
        assert len(curve["T"]) == len(curve["ols_ttest"]) == len(curve["posterior"])
    # Exhibit 2: alpha degradation R vs E, plus P-only metrics.
    table = data["degradation_table"]
    assert "alpha_estimation" in table
    assert {"R", "E"} <= set(table["alpha_estimation"])
    # Exhibit 3: registry snippet in the X1 §2 shape.
    snippet = data["registry_snippet"]["metrics"]
    assert "hit_rate" in snippet
    assert {"min_tier", "gate_quantity", "threshold", "power_at_threshold"} <= set(snippet["hit_rate"])


def test_power_curves_rise_with_T(tmp_path):
    data = _load(x1_atlas.build(out_dir=tmp_path))
    top = max(data["power_curves"], key=lambda c: c["ic"])
    assert top["ols_ttest"][-1] >= top["ols_ttest"][0] - 0.1  # monotone up to MC noise


def test_byte_for_byte_determinism_and_matches_committed(tmp_path):
    first = x1_atlas.build(out_dir=tmp_path).read_bytes()
    second = x1_atlas.build(out_dir=tmp_path).read_bytes()
    assert first == second
    committed = (SITE_DATA_DIR / "x1_atlas.json").read_bytes()
    assert first == committed
