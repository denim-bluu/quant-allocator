"""The section registry (spec §3.1): the committed ordered table of section
descriptors. A reviewer sees every section the pack can ever contain, and in
what order, at a glance. Adding a card to the pack is adding a row here, not
writing code. Data, not logic.
"""

from __future__ import annotations

from dataclasses import dataclass

# Tier axis, low to high. A section renders only if the manager's tier >= its
# min_tier; below that it is omitted-and-footnoted (never silently dropped).
TIER_ORDER: dict[str, int] = {"R": 0, "E": 1, "P": 2}


@dataclass(frozen=True)
class SectionDescriptor:
    section_id: str
    title: str
    source_card: str  # certifying card id: "s1" | "s2" | "m5" | "m1"
    payload_key: str  # key into the manager payload map; "" when the section carries no rendered payload
    min_tier: str  # inherited from the source card (the lead reviewer audits it in that card's spec, not here)
    gate_metric: str | None  # X1 PowerGate registry metric key, or None when ungated


# Ordered exactly as the pack reads top-to-bottom. min_tier and gate_metric are
# INHERITED constants (source card's / X1's) — flagged in the docket as audited
# elsewhere, not authored here.
SECTION_REGISTRY: tuple[SectionDescriptor, ...] = (
    SectionDescriptor("posterior_standing", "Posterior skill standing", "s1", "", "R", "ols_alpha_ttest"),
    SectionDescriptor("tear_sheet", "Honest tear sheet", "s2", "tear_sheet", "R", None),
    SectionDescriptor("say_do", "Say–do inventory", "m5", "say_do", "R", None),
    SectionDescriptor("exposure_drift", "Exposure hygiene & drift", "m1", "", "E", None),
)
