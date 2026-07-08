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
# P2 spec §6.6 / §8 ruling 4 (NUMERICS-GATE): Open-Protocol E-tier coarsening granularity
# (beta units). A real E-tier disclosure buckets factor betas; the demo coarsens on opt-in.
OP_BUCKET_WIDTH = 0.05


@dataclass(frozen=True)
class ManagerDataTiers:
    returns_only: pd.Series
    exposures: pd.DataFrame
    transparency: pd.DataFrame


def emit_tiers(
    market: FactorMarket, history: ManagerHistory, *, coarsen_e_tier: bool = False
) -> ManagerDataTiers:
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
    if coarsen_e_tier:
        beta_cols = [c for c in exposures.columns if c.startswith("beta_")]
        exposures[beta_cols] = (exposures[beta_cols] / OP_BUCKET_WIDTH).round() * OP_BUCKET_WIDTH

    transparency = weights.stack(future_stack=True).rename("weight").reset_index()
    transparency = transparency[transparency["weight"] != 0.0].reset_index(drop=True)

    return ManagerDataTiers(
        returns_only=history.monthly_returns.copy(),
        exposures=exposures,
        transparency=transparency,
    )
