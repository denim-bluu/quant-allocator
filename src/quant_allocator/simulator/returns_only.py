"""Deliberately crude returns-only generators for non-equity manager archetypes.

Spec Section 7: macro/credit managers exist in the simulator only at the
returns-only tier — synthetic strategy factors plus an alpha stream. Enough
for cross-strategy aggregation experiments; not a market microcosm.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

MONTHS_PER_YEAR = 12

STRATEGY_FACTORS: dict[str, dict[str, tuple[float, float]]] = {
    "macro": {"trend": (0.05, 0.12), "rates_carry": (0.03, 0.06), "fx_carry": (0.03, 0.08)},
    "credit": {"credit_spread": (0.04, 0.07), "rates": (0.02, 0.05)},
}


@dataclass(frozen=True)
class ReturnsOnlyConfig:
    strategy: str = "macro"
    n_months: int = 60
    skill_annual_alpha: float = 0.02
    alpha_annual_vol: float = 0.04
    start_month: str = "2020-01"
    seed: int = 0


def simulate_returns_only_manager(config: ReturnsOnlyConfig) -> pd.Series:
    if config.strategy not in STRATEGY_FACTORS:
        raise ValueError(
            f"unknown strategy {config.strategy!r}; expected one of {sorted(STRATEGY_FACTORS)}"
        )
    rng = np.random.default_rng(config.seed)
    months = pd.period_range(config.start_month, periods=config.n_months, freq="M")

    total = np.zeros(config.n_months)
    for annual_mean, annual_vol in STRATEGY_FACTORS[config.strategy].values():
        factor = rng.normal(
            annual_mean / MONTHS_PER_YEAR,
            annual_vol / np.sqrt(MONTHS_PER_YEAR),
            size=config.n_months,
        )
        exposure = rng.uniform(0.2, 1.0)
        total += exposure * factor

    alpha = rng.normal(
        config.skill_annual_alpha / MONTHS_PER_YEAR,
        config.alpha_annual_vol / np.sqrt(MONTHS_PER_YEAR),
        size=config.n_months,
    )
    return pd.Series(total + alpha, index=months, name=f"{config.strategy}_manager")
