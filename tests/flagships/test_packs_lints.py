import pytest

from quant_allocator.flagships.packs import lints
from quant_allocator.flagships.packs.lints import PackLintError, lint_pack, numerals


def _rendered_tear_sheet(narration):
    return {
        "section_id": "tear_sheet",
        "title": "Honest tear sheet",
        "source_card": "s2",
        "min_tier": "R",
        "state": "rendered",
        "provenance": {"card": "s2", "metric": "sharpe_desmoothed", "as_of": "2021-Q2"},
        "narration": narration,
        "display_numbers": ["0.71", "0.60", "90%", "-4.4%", "+10.8%"],
        "stats": [
            {"kind": "interval", "label": "De-smoothed Sharpe", "point": 0.60,
             "ci_lo": -0.29, "ci_hi": 1.46, "level": "95%"},
            {"kind": "verdict", "label": "alt beta", "verdict": "shrink",
             "chip": "provisionally alternative beta"},
        ],
    }


def _refused_standing(narration):
    return {
        "section_id": "posterior_standing",
        "title": "Posterior skill standing",
        "source_card": "s1",
        "min_tier": "R",
        "state": "refused",
        "provenance": {"card": "s1", "metric": "ols_alpha_ttest", "as_of": "2021-Q2"},
        "narration": narration,
        "display_numbers": ["48", "0.5"],
        "gate": {"metric": "ols_alpha_ttest", "quantity": "months",
                 "measured": 48, "threshold": None, "effect": "true IR 0.5"},
    }


def _pack(summary, sections):
    return {"summary": summary, "sections": sections}


def test_numerals_tokenizer():
    assert numerals("Sharpe 0.71 to 0.60, alpha +3.2% over 48 months") == \
        ["0.71", "0.60", "+3.2%", "48"]


def test_faithful_pack_passes():
    lint_pack(_pack(
        "A reported Sharpe of 0.71 de-smooths to 0.60.",
        [_rendered_tear_sheet("The 90% interval spans -4.4% to +10.8%.")],
    ))


def test_hallucinated_number_in_section_fails():
    # 0.85 is not in display_numbers — a plausible wrong number fails the pack.
    with pytest.raises(PackLintError, match="faithfulness"):
        lint_pack(_pack(
            "ok",
            [_rendered_tear_sheet("The de-smoothed Sharpe is actually 0.85.")],
        ))


def test_hallucinated_number_in_summary_fails():
    with pytest.raises(PackLintError, match="faithfulness"):
        lint_pack(_pack(
            "The Sharpe of 0.99 is excellent.",
            [_rendered_tear_sheet("De-smooths to 0.60.")],
        ))


def test_bare_point_stat_fails_inv1():
    section = _rendered_tear_sheet("De-smooths to 0.60.")
    section["stats"].append({"kind": "interval", "label": "bare", "point": 0.3})  # no ci
    with pytest.raises(PackLintError, match="bare point|INV-1"):
        lint_pack(_pack("ok", [section]))


def test_missing_provenance_fails_inv2():
    section = _rendered_tear_sheet("De-smooths to 0.60.")
    section["provenance"] = {"card": "s2"}  # no metric
    with pytest.raises(PackLintError, match="provenance|INV-2"):
        lint_pack(_pack("ok", [section]))


def test_refused_section_that_withholds_the_claim_passes_inv3():
    lint_pack(_pack(
        "Skill standing stays gated at 48 months.",
        [_refused_standing(
            "At 48 months no tenure separates a true IR of 0.5 from luck; "
            "the pack shows the gate, not a number it cannot defend."
        )],
    ))


def test_refused_section_asserting_out_of_gate_number_fails_inv3():
    # A refused section may not smuggle a measured claim (here a fabricated 0.82).
    with pytest.raises(PackLintError, match="gate-respect|INV-3"):
        lint_pack(_pack(
            "ok",
            [_refused_standing("The posterior probability of skill is 0.82.")],
        ))


def test_refused_section_without_refusal_marker_fails_inv3():
    with pytest.raises(PackLintError, match="gate-respect|INV-3"):
        lint_pack(_pack(
            "ok",
            [_refused_standing("Skill standing at 48 months and true IR 0.5.")],
        ))


def test_gate_constants_are_zero_tolerance():
    assert lints.PACK_FAITHFULNESS_MIN == 1.00
    assert lints.PACK_HALLUCINATION_MAX == 0
    assert lints.PACK_GATE_RESPECT_MIN == 1.00
    assert lints.PACK_EVAL_ITERATIONS == 2


def test_m5_fixture_reuse_planted_hallucination_is_caught():
    # M5 fixture reuse (gate ruling): build a say-do inventory section from
    # M5-style authored views, plant a number the inventory does not certify,
    # and assert the faithfulness lint catches it. The R-tier say-do inventory
    # carries no numerals, so ANY numeral in its narration is a hallucination.
    from quant_allocator.demo_data.m5_saydo import VIEWS

    say_do = {
        "section_id": "say_do", "title": "Say-do inventory", "source_card": "m5",
        "min_tier": "R", "state": "rendered",
        "provenance": {"card": "m5", "metric": "letter_views", "as_of": "2021-Q2"},
        "display_numbers": [],
        "views": [{"direction": v["direction"], "theme": v["theme"],
                   "conviction": v["conviction"], "quote": v["quote"]} for v in VIEWS],
        "stats": [],
        "narration": "The manager trimmed momentum by 0.20 over the horizon.",  # 0.20 not certified here
    }
    with pytest.raises(PackLintError, match="faithfulness"):
        lint_pack(_pack("ok", [say_do]))
