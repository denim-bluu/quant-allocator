"""The deterministic composition pipeline (spec §3.2, §3.5).

Pure function of (manager section bodies, gate quantities, PowerGate registry)
-> pack payload. No estimators, no RNG, no I/O beyond what the caller passes in.
Each registry row resolves to exactly one of {rendered, refused, omitted} — a
section is never silently dropped. The assembled pack is validated by lint_pack
before it is returned, so a dishonest pack cannot leave this function.
"""

from __future__ import annotations

import re

from quant_allocator.flagships.packs.lints import lint_pack
from quant_allocator.flagships.packs.registry import (
    SECTION_REGISTRY,
    SectionDescriptor,
    TIER_ORDER,
)

_NUMERAL = re.compile(r"[+-]?\d+(?:\.\d+)?%?")


def _effect_numerals(effect: str) -> list[str]:
    return _NUMERAL.findall(effect or "")


def _rendered(descriptor: SectionDescriptor, body: dict | None) -> dict:
    body = body or {}
    return {
        "section_id": descriptor.section_id,
        "title": descriptor.title,
        "source_card": descriptor.source_card,
        "min_tier": descriptor.min_tier,
        "state": "rendered",
        "provenance": body.get(
            "provenance",
            {"card": descriptor.source_card, "metric": descriptor.payload_key, "as_of": ""},
        ),
        "narration": body.get("narration"),
        "display_numbers": body.get("display_numbers", []),
        "stats": body.get("stats", []),
        "views": body.get("views", []),
    }


def _refused(descriptor: SectionDescriptor, metric: dict, measured: int, narration: str | None) -> dict:
    effect = metric.get("effect", "")
    # The refused section's certified numbers are the gate's own: the measured N
    # and the effect size. No manager statistic renders (it is gated out).
    effect_numbers = _effect_numerals(effect)
    return {
        "section_id": descriptor.section_id,
        "title": descriptor.title,
        "source_card": descriptor.source_card,
        "min_tier": descriptor.min_tier,
        "state": "refused",
        "provenance": {"card": descriptor.source_card, "metric": descriptor.gate_metric, "as_of": ""},
        "narration": narration,
        "display_numbers": [str(measured), *effect_numbers],
        "gate": {
            "metric": descriptor.gate_metric,
            "quantity": metric.get("gate_quantity"),
            "measured": measured,
            "threshold": metric.get("threshold"),
            "effect": effect,
        },
    }


def _omitted(descriptor: SectionDescriptor, reason: str) -> dict:
    return {
        "section_id": descriptor.section_id,
        "title": descriptor.title,
        "source_card": descriptor.source_card,
        "min_tier": descriptor.min_tier,
        "state": "omitted",
        "provenance": {"card": descriptor.source_card, "metric": "", "as_of": ""},
        "narration": None,
        "display_numbers": [],
        "omitted": {"needs_tier": descriptor.min_tier, "reason": reason},
    }


def resolve_section(
    descriptor: SectionDescriptor,
    manager_tier: str,
    sections_in: dict[str, dict],
    gate_quantities: dict[str, int],
    powergate_registry: dict,
    refusal_narration: dict[str, str],
    omitted_reason: dict[str, str],
) -> dict:
    if TIER_ORDER[manager_tier] < TIER_ORDER[descriptor.min_tier]:
        return _omitted(descriptor, omitted_reason.get(descriptor.section_id, ""))

    if descriptor.gate_metric is not None:
        metric = powergate_registry["metrics"][descriptor.gate_metric]
        quantity_name = metric["gate_quantity"]
        measured = gate_quantities.get(quantity_name, 0)
        threshold = metric.get("threshold")
        if threshold is None or measured < threshold:
            return _refused(descriptor, metric, measured,
                            refusal_narration.get(descriptor.section_id))

    return _rendered(descriptor, sections_in.get(descriptor.payload_key))


def compose(
    meta: dict,
    sections_in: dict[str, dict],
    gate_quantities: dict[str, int],
    powergate_registry: dict,
    summary: str,
    refusal_narration: dict[str, str],
    omitted_reason: dict[str, str],
    registry: tuple[SectionDescriptor, ...] = SECTION_REGISTRY,
) -> dict:
    sections = [
        resolve_section(descriptor, meta["tier"], sections_in, gate_quantities,
                        powergate_registry, refusal_narration, omitted_reason)
        for descriptor in registry
    ]
    footer = {
        "provenance": [
            {"section": s["section_id"], "title": s["title"], "certified_by": s["provenance"]["card"]}
            for s in sections if s["state"] in {"rendered", "refused"}
        ],
        "omitted": [
            {"section": s["section_id"], "title": s["title"], "needs_tier": s["omitted"]["needs_tier"]}
            for s in sections if s["state"] == "omitted"
        ],
    }
    pack = {"meta": meta, "summary": summary, "sections": sections, "footer": footer}
    lint_pack(pack)
    return pack
