"""Card-local authored truth labels for D-tier X3 validation only."""

from quant_allocator.flagships.universe_coverage.audit import HiddenMember, TruthPair

# The fixture authors reserved x3-source-0000..0839 as labelled pair keys. The first
# 420 are matches (410 accepted, ten deliberately missed); the second 420 are hard
# negatives. These constants never enter coverage/funnel inputs or claim receipts.
TRUTH_PAIRS = tuple(
    TruthPair(f"x3-source-{index:04d}", True, index < 410) for index in range(420)
) + tuple(TruthPair(f"x3-source-{index:04d}", False, False) for index in range(420, 840))

HIDDEN_STRATEGIES = tuple(
    HiddenMember(f"strategy:x3-{index:02d}", f"synthetic-cell:{index:02d}")
    for index in range(24)
)
