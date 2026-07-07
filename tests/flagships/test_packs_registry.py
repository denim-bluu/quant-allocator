from quant_allocator.flagships.packs.registry import (
    SECTION_REGISTRY,
    SectionDescriptor,
    TIER_ORDER,
)

# Killed / do-not-build analytics have NO registry section (INV-3: structurally
# unreachable — the pack cannot narrate a claim no card is allowed to make).
FORBIDDEN_CARDS = {"persistence", "fdr_luck", "regime_split", "conditional_beta", "style_drift"}
KNOWN_CARDS = {"s1", "s2", "m5", "m1"}


def test_registry_is_ordered_and_typed():
    assert len(SECTION_REGISTRY) == 4
    assert all(isinstance(d, SectionDescriptor) for d in SECTION_REGISTRY)
    ids = [d.section_id for d in SECTION_REGISTRY]
    assert ids == ["posterior_standing", "tear_sheet", "say_do", "exposure_drift"]


def test_registry_min_tiers_and_gates():
    by_id = {d.section_id: d for d in SECTION_REGISTRY}
    assert by_id["posterior_standing"].min_tier == "R"
    assert by_id["posterior_standing"].gate_metric == "ols_alpha_ttest"
    assert by_id["tear_sheet"].gate_metric is None
    assert by_id["exposure_drift"].min_tier == "E"


def test_registry_only_names_allowed_cards():
    for d in SECTION_REGISTRY:
        assert d.source_card in KNOWN_CARDS
        assert d.source_card not in FORBIDDEN_CARDS
        assert d.min_tier in TIER_ORDER
