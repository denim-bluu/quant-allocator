import pytest

from quant_allocator.flagships.knowledge.brief import compose_meeting_brief


VIEWS = [
    {
        "direction": "neutral-explicit",
        "theme": "liquidity",
        "quote": "We remained comfortable with portfolio liquidity.",
        "source_doc": "L-2024Q1",
        "source_span": "We remained comfortable with portfolio liquidity.",
        "as_of": "2024-03",
    }
]
QUESTIONS = [
    {
        "question": "How would redemption gates apply under stress?",
        "source_doc": "MTG-2024-05",
        "source_span": "The portfolio manager described redemption gates under stress.",
        "as_of": "2024-05",
    }
]


def _matching_source(card):
    return {
        "manager_id": "CLC",
        "manager_name": "Corvid Lane Capital",
        "provenance": {"card": card, "metric": "fixture", "as_of": "2024-05"},
        "stats": [],
        "views": [],
    }


def test_document_native_sections_render_and_missing_sources_are_explicit():
    brief = compose_meeting_brief(
        manager_id="CLC",
        manager_name="Corvid Lane Capital",
        tier="R",
        stated_views=VIEWS,
        open_questions=QUESTIONS,
    )
    states = {section["section_id"]: section["state"] for section in brief["sections"]}
    assert states == {
        "stated_views": "rendered",
        "open_questions": "rendered",
        "say_do": "omitted",
        "tear_sheet": "omitted",
    }
    reasons = {
        section["section_id"]: section["omitted"]["reason"]
        for section in brief["sections"]
        if section["state"] == "omitted"
    }
    assert "tier E" in reasons["say_do"]
    assert "same-manager S2 source unavailable" in reasons["tear_sheet"]
    assert all("provenance" in section for section in brief["sections"])


def test_matching_same_manager_sources_render_at_e_tier():
    brief = compose_meeting_brief(
        manager_id="CLC",
        manager_name="Corvid Lane Capital",
        tier="E",
        stated_views=VIEWS,
        open_questions=QUESTIONS,
        m5_section=_matching_source("m5"),
        s2_section=_matching_source("s2"),
    )
    assert all(section["state"] == "rendered" for section in brief["sections"])


@pytest.mark.parametrize("source_name", ["m5_section", "s2_section"])
def test_different_manager_source_is_rejected(source_name):
    source = _matching_source("m5" if source_name == "m5_section" else "s2")
    source["manager_id"] = "M07"
    source["manager_name"] = "Kestrelmoor Partners"
    with pytest.raises(ValueError, match="manager identity"):
        compose_meeting_brief(
            manager_id="CLC",
            manager_name="Corvid Lane Capital",
            tier="E",
            stated_views=VIEWS,
            open_questions=QUESTIONS,
            **{source_name: source},
        )
