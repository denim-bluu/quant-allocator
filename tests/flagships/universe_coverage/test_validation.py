from datetime import datetime

import pytest

from quant_allocator.flagships.universe_coverage.model import CoverageSelection
from quant_allocator.flagships.universe_coverage.validation import assert_public_contract, require_aware_utc


def test_naive_decision_time_refuses() -> None:
    with pytest.raises(ValueError, match="timezone-aware UTC"):
        require_aware_utc(datetime(2024, 1, 1))


@pytest.mark.parametrize("key", ["quality", "best_manager", "global_universe_coverage_rate", "probability_of_hire_success"])
def test_manager_ranking_and_global_denominator_keys_are_forbidden(key: str) -> None:
    with pytest.raises(ValueError, match="forbidden X3 output key"):
        assert_public_contract({key: 1})


def test_selection_rejects_mixed_grain() -> None:
    with pytest.raises(ValueError, match="one canonical entity grain"):
        CoverageSelection("strategy/composite", ("a",), "g", True, ("f",))
