import numpy as np
import pandas as pd
import pytest

from quant_allocator.simulator.returns_only import (
    ReturnsOnlyConfig,
    simulate_returns_only_manager,
)


def test_shape_index_and_reproducibility():
    cfg = ReturnsOnlyConfig(strategy="macro", n_months=60, seed=1)
    a = simulate_returns_only_manager(cfg)
    b = simulate_returns_only_manager(cfg)
    assert len(a) == 60
    assert isinstance(a.index, pd.PeriodIndex)
    pd.testing.assert_series_equal(a, b)


def test_skill_shifts_mean_return_on_long_sample():
    base = ReturnsOnlyConfig(strategy="credit", n_months=120_000, seed=2)
    skilled = ReturnsOnlyConfig(
        strategy="credit", n_months=120_000, skill_annual_alpha=0.06, seed=2
    )
    gap_annualized = 12 * (
        simulate_returns_only_manager(skilled).mean()
        - simulate_returns_only_manager(base).mean()
    )
    assert np.isclose(gap_annualized, 0.06 - 0.02, atol=0.01)


def test_unknown_strategy_raises():
    with pytest.raises(ValueError, match="unknown strategy"):
        simulate_returns_only_manager(ReturnsOnlyConfig(strategy="event"))
