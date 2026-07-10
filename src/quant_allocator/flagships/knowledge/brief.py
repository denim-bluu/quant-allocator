"""Document-native E3 meeting brief using E2's pack lint contract."""

from __future__ import annotations

from collections.abc import Sequence

from quant_allocator.flagships.packs.lints import lint_pack

_TIER_ORDER = {"R": 0, "E": 1, "P": 2}


def _validate_source_identity(
    source: dict | None, manager_id: str, manager_name: str, label: str
) -> None:
    if source is None:
        return
    if (
        source.get("manager_id") != manager_id
        or source.get("manager_name") != manager_name
    ):
        raise ValueError(
            f"{label} manager identity does not match {manager_id}/{manager_name}"
        )


def _latest_as_of(rows: Sequence[dict]) -> str:
    return max((str(row.get("as_of", "")) for row in rows), default="")


def _document_section(section_id: str, title: str, rows: Sequence[dict]) -> dict:
    return {
        "section_id": section_id,
        "title": title,
        "source_card": "e3",
        "min_tier": "R",
        "state": "rendered",
        "provenance": {
            "card": "e3",
            "metric": section_id,
            "as_of": _latest_as_of(rows),
        },
        "narration": None,
        "display_numbers": [],
        "stats": [],
        "views": list(rows),
    }


def _source_section(section_id: str, title: str, source_card: str, source: dict) -> dict:
    return {
        "section_id": section_id,
        "title": title,
        "source_card": source_card,
        "min_tier": "E" if source_card == "m5" else "R",
        "state": "rendered",
        "provenance": source["provenance"],
        "narration": source.get("narration"),
        "display_numbers": source.get("display_numbers", []),
        "stats": source.get("stats", []),
        "views": source.get("views", []),
    }


def _omitted_source(
    section_id: str,
    title: str,
    source_card: str,
    needs_tier: str,
    reason: str,
) -> dict:
    return {
        "section_id": section_id,
        "title": title,
        "source_card": source_card,
        "min_tier": needs_tier,
        "state": "omitted",
        "provenance": {"card": source_card, "metric": "unavailable", "as_of": ""},
        "narration": None,
        "display_numbers": [],
        "omitted": {"needs_tier": needs_tier, "reason": reason},
    }


def compose_meeting_brief(
    *,
    manager_id: str,
    manager_name: str,
    tier: str,
    stated_views: Sequence[dict],
    open_questions: Sequence[dict],
    m5_section: dict | None = None,
    s2_section: dict | None = None,
) -> dict:
    """Compose only sources that belong to the named manager.

    The current authored Corvid fixture has no same-manager M5 or S2 payload.
    Those panels are therefore explicit omissions, never relabelled M07 output.
    """

    if tier not in _TIER_ORDER:
        raise ValueError(f"unknown tier {tier!r}")
    _validate_source_identity(m5_section, manager_id, manager_name, "M5 source")
    _validate_source_identity(s2_section, manager_id, manager_name, "S2 source")

    sections = [
        _document_section("stated_views", "Last stated views", stated_views),
        _document_section("open_questions", "Open questions carried over", open_questions),
    ]

    if _TIER_ORDER[tier] < _TIER_ORDER["E"]:
        sections.append(
            _omitted_source(
                "say_do",
                "Say-do flags",
                "m5",
                "E",
                "requires tier E and a same-manager M5 source",
            )
        )
    elif m5_section is None:
        sections.append(
            _omitted_source(
                "say_do",
                "Say-do flags",
                "m5",
                "E",
                "same-manager M5 source unavailable",
            )
        )
    else:
        sections.append(_source_section("say_do", "Say-do flags", "m5", m5_section))

    if s2_section is None:
        sections.append(
            _omitted_source(
                "tear_sheet",
                "Honest tear sheet",
                "s2",
                "R",
                "same-manager S2 source unavailable",
            )
        )
    else:
        sections.append(_source_section("tear_sheet", "Honest tear sheet", "s2", s2_section))

    brief = {
        "meta": {
            "manager_id": manager_id,
            "manager_name": manager_name,
            "tier": tier,
            "scope": "document_native_partial_brief",
        },
        "summary": "Document-native preparation; unavailable same-manager sources are named.",
        "sections": sections,
        "footer": {
            "omitted": [
                {
                    "section": section["section_id"],
                    "reason": section["omitted"]["reason"],
                }
                for section in sections
                if section["state"] == "omitted"
            ]
        },
    }
    lint_pack(brief)
    return brief
