"""Emit the three allocator transparency tiers from one simulated manager.

The same ground-truth book is viewed as: returns-only (what every allocator
gets), exposure summaries (what risk reports disclose), and position-level
transparency (managed-account style). Emission only — no analytics here.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from quant_allocator.simulator.manager import ManagerHistory
from quant_allocator.simulator.market import FactorMarket

TOP_N_CONCENTRATION = 10


@dataclass(frozen=True)
class ManagerDataTiers:
    returns_only: pd.Series
    exposures: pd.DataFrame
    transparency: pd.DataFrame


def emit_tiers(market: FactorMarket, history: ManagerHistory) -> ManagerDataTiers:
    weights = history.weights

    gross = weights.abs().sum(axis=1)
    top10_share = (
        weights.abs().apply(lambda row: row.nlargest(TOP_N_CONCENTRATION).sum(), axis=1)
        / gross
    )
    exposures = (weights @ market.betas).add_prefix("beta_")
    exposures.insert(0, "gross", gross)
    exposures.insert(1, "net", weights.sum(axis=1))
    exposures["top10_share"] = top10_share

    transparency = weights.stack(future_stack=True).rename("weight").reset_index()
    transparency = transparency[transparency["weight"] != 0.0].reset_index(drop=True)

    return ManagerDataTiers(
        returns_only=history.monthly_returns.copy(),
        exposures=exposures,
        transparency=transparency,
    )
