import pytest

from quant_allocator.flagships.packs.compose import compose, resolve_section
from quant_allocator.flagships.packs.registry import SECTION_REGISTRY

REGISTRY = {"metrics": {
    "ols_alpha_ttest": {"min_tier": "R", "gate_quantity": "months",
                        "threshold": None, "effect": "true IR 0.5"},
    "hit_rate": {"min_tier": "P", "gate_quantity": "independent_trades",
                 "threshold": 400, "effect": "separate hit 55% from 50%"},
}}


def _tear_body():
    return {
        "provenance": {"card": "s2", "metric": "sharpe_desmoothed", "as_of": "2021-Q2"},
        "narration": "Reported Sharpe 0.71 de-smooths to 0.60.",
        "display_numbers": ["0.71", "0.60"],
        "stats": [{"kind": "interval", "label": "De-smoothed Sharpe", "point": 0.60,
                   "ci_lo": -0.29, "ci_hi": 1.46, "level": "95%"}],
    }


def test_below_tier_section_is_omitted_and_footnoted():
    drift = next(d for d in SECTION_REGISTRY if d.section_id == "exposure_drift")
    out = resolve_section(drift, "R", {}, {}, REGISTRY,
                          refusal_narration={}, omitted_reason={"exposure_drift": "requires exposure summaries"})
    assert out["state"] == "omitted"
    assert out["omitted"]["needs_tier"] == "E"
    assert out["omitted"]["reason"] == "requires exposure summaries"


def test_null_threshold_metric_refuses():
    standing = next(d for d in SECTION_REGISTRY if d.section_id == "posterior_standing")
    out = resolve_section(standing, "R", {}, {"months": 48}, REGISTRY,
                          refusal_narration={"posterior_standing":
                              "At 48 months no tenure separates true IR 0.5 from luck; cannot certify yet."},
                          omitted_reason={})
    assert out["state"] == "refused"
    assert out["gate"]["metric"] == "ols_alpha_ttest"
    assert out["gate"]["measured"] == 48
    assert out["gate"]["threshold"] is None
    assert out["display_numbers"] == ["48", "0.5"]


def test_ungated_section_renders():
    tear = next(d for d in SECTION_REGISTRY if d.section_id == "tear_sheet")
    out = resolve_section(tear, "R", {"tear_sheet": _tear_body()}, {}, REGISTRY,
                          refusal_narration={}, omitted_reason={})
    assert out["state"] == "rendered"
    assert out["stats"][0]["point"] == 0.60


def test_no_section_is_ever_silently_dropped():
    pack = compose(
        meta={"manager_code": "M07", "manager_name": "Kestrelmoor Partners",
              "tier": "R", "quarter": "2021-Q2"},
        sections_in={"tear_sheet": _tear_body()},
        gate_quantities={"months": 48},
        powergate_registry=REGISTRY,
        summary="Kestrelmoor, tier R: Sharpe 0.71 de-smooths to 0.60; standing gated at 48 months.",
        refusal_narration={"posterior_standing":
            "At 48 months no tenure separates true IR 0.5 from luck; cannot certify yet."},
        omitted_reason={"exposure_drift": "requires exposure summaries"},
    )
    # Every registry row produced exactly one resolved section.
    assert len(pack["sections"]) == len(SECTION_REGISTRY)
    states = {s["section_id"]: s["state"] for s in pack["sections"]}
    assert set(states.keys()) == {d.section_id for d in SECTION_REGISTRY}
    assert set(states.values()) <= {"rendered", "refused", "omitted"}
    # Footer discloses the omission (with a print-friendly title, not just the id).
    assert pack["footer"]["omitted"] == [
        {"section": "exposure_drift", "title": "Exposure hygiene & drift", "needs_tier": "E"}
    ]


def test_compose_runs_lints_and_rejects_a_hallucinated_summary():
    with pytest.raises(Exception):
        compose(
            meta={"manager_code": "M07", "manager_name": "Kestrelmoor Partners",
                  "tier": "R", "quarter": "2021-Q2"},
            sections_in={"tear_sheet": _tear_body()},
            gate_quantities={"months": 48},
            powergate_registry=REGISTRY,
            summary="The Sharpe of 9.99 is stellar.",  # 9.99 certified by nothing
            refusal_narration={"posterior_standing":
                "At 48 months no tenure separates true IR 0.5 from luck; cannot certify yet."},
            omitted_reason={"exposure_drift": "requires exposure summaries"},
        )
