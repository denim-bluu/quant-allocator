import json
import math

from quant_allocator.demo_data import x1_atlas
from quant_allocator.demo_data._emit import SITE_DATA_DIR


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_three_exhibits_present(tmp_path):
    data = _load(x1_atlas.build(out_dir=tmp_path))
    assert set(data) >= {
        "meta",
        "tier_comparison",
        "power_curves",
        "degradation_table",
        "registry_snippet",
    }
    comparison = data["tier_comparison"]
    assert comparison["target_power"] == 0.8
    assert [row["months"] for row in comparison["rows"]] == [48, 120]
    for row in comparison["rows"]:
        assert set(row) == {"months", "returns_only", "measured_exposure"}
        for tier in ("returns_only", "measured_exposure"):
            assert set(row[tier]) == {"power", "wilson"}
    # Exhibit 1: one curve per IC level, each with OLS and posterior series over T.
    curves = data["power_curves"]
    assert len(curves) == len(x1_atlas.SAMPLER_IC_LEVELS)
    for curve in curves:
        assert set(curve) >= {
            "ic",
            "realized_ir",
            "T",
            "ols_ttest",
            "posterior",
            "ols_ttest_wilson",
            "posterior_wilson",
        }
        assert len(curve["T"]) == len(curve["ols_ttest"]) == len(curve["posterior"])
        assert len(curve["T"]) == len(curve["ols_ttest_wilson"])
        assert len(curve["T"]) == len(curve["posterior_wilson"])
    # Exhibit 2: alpha degradation R vs E, plus P-only metrics.
    table = data["degradation_table"]
    assert "alpha_estimation" in table
    assert {"R", "E"} <= set(table["alpha_estimation"])
    # Exhibit 3: registry snippet in the X1 §2 shape.
    snippet = data["registry_snippet"]["metrics"]
    assert "hit_rate" in snippet
    assert {"min_tier", "gate_quantity", "threshold", "power_at_threshold"} <= set(
        snippet["hit_rate"]
    )
    headline = data["headline"]
    assert headline["e_tier"]["threshold_months"] == 120
    assert headline["e_tier"]["power"] == 0.82
    assert headline["r_tier"]["power"] == 0.788


def _wilson_half_width(power, n, z=1.96):
    denominator = 1.0 + z * z / n
    radicand = power * (1.0 - power) / n + z * z / (4.0 * n * n)
    return (z / denominator) * math.sqrt(radicand)


def _wilson_center(power, n, z=1.96):
    return (power + z * z / (2.0 * n)) / (1.0 + z * z / n)


def test_every_emitted_wilson_value_rederives_from_power_and_n(tmp_path):
    data = _load(x1_atlas.build(out_dir=tmp_path))
    n = data["meta"]["n_reps"]

    def check(power, wilson):
        expected = _wilson_half_width(power, n)
        center = _wilson_center(power, n)
        assert wilson["n"] == n
        assert wilson["half_width"] == round(expected, 6)
        assert wilson["lo"] == round(max(0.0, center - expected), 6)
        assert wilson["hi"] == round(min(1.0, center + expected), 6)

    for curve in data["power_curves"]:
        for name in ("ols_ttest", "posterior"):
            for power, wilson in zip(curve[name], curve[f"{name}_wilson"]):
                check(power, wilson)
    for row in data["degradation_table"]["alpha_estimation"].values():
        check(row["power"], row["wilson"])
    for name in ("hit_rate_P", "sizing_skill_P"):
        row = data["degradation_table"][name]
        check(row["power"], row["wilson"])
    for name in ("e_tier", "r_tier", "r_tier_false_attribution"):
        row = data["headline"][name]
        check(row["power"], row["wilson"])
    for row in data["tier_comparison"]["rows"]:
        check(row["returns_only"]["power"], row["returns_only"]["wilson"])
        check(row["measured_exposure"]["power"], row["measured_exposure"]["wilson"])


def test_tier_comparison_is_a_projection_of_existing_grid_cells(tmp_path):
    data = _load(x1_atlas.build(out_dir=tmp_path))
    payloads, _, _ = x1_atlas.x_grid.build_grid()
    for row in data["tier_comparison"]["rows"]:
        for tier_name, tier_code in (("returns_only", "R"), ("measured_exposure", "E")):
            cell = payloads[
                (
                    x1_atlas.x_grid.PINNED_EFFECT_IC,
                    x1_atlas.SAMPLER_HALF_LIFE,
                    x1_atlas.SAMPLER_SIZING,
                    row["months"],
                    tier_code,
                )
            ].analytics["alpha_posterior"]
            assert row[tier_name]["power"] == round(cell["power"], 4)


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
