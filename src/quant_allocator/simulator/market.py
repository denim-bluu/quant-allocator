"""Synthetic factor-model equity market: the ground-truth world managers trade in."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

MONTHS_PER_YEAR = 12


@dataclass(frozen=True)
class MarketConfig:
    n_assets: int = 500
    n_months: int = 60
    factor_names: tuple[str, ...] = ("market", "size", "value", "momentum")
    factor_annual_means: tuple[float, ...] = (0.06, 0.02, 0.03, 0.04)
    factor_annual_vols: tuple[float, ...] = (0.16, 0.08, 0.10, 0.12)
    idio_annual_vol_range: tuple[float, float] = (0.20, 0.45)
    start_month: str = "2020-01"
    seed: int = 0


@dataclass(frozen=True)
class FactorMarket:
    config: MarketConfig
    betas: pd.DataFrame
    factor_returns: pd.DataFrame
    idio_returns: pd.DataFrame

    @property
    def asset_returns(self) -> pd.DataFrame:
        systematic = self.factor_returns.to_numpy() @ self.betas.to_numpy().T
        return (
            pd.DataFrame(
                systematic, index=self.factor_returns.index, columns=self.betas.index
            )
            + self.idio_returns
        )


def simulate_market(config: MarketConfig) -> FactorMarket:
    rng = np.random.default_rng(config.seed)
    months = pd.period_range(config.start_month, periods=config.n_months, freq="M")
    assets = pd.Index([f"A{i:04d}" for i in range(config.n_assets)], name="asset")
    factors = list(config.factor_names)

    monthly_means = np.asarray(config.factor_annual_means) / MONTHS_PER_YEAR
    monthly_vols = np.asarray(config.factor_annual_vols) / np.sqrt(MONTHS_PER_YEAR)
    factor_returns = pd.DataFrame(
        rng.normal(monthly_means, monthly_vols, size=(config.n_months, len(factors))),
        index=months,
        columns=factors,
    )

    market_beta = rng.normal(1.0, 0.25, size=config.n_assets)
    style_betas = rng.normal(0.0, 0.5, size=(config.n_assets, len(factors) - 1))
    betas = pd.DataFrame(
        np.column_stack([market_beta, style_betas]), index=assets, columns=factors
    )

    low, high = config.idio_annual_vol_range
    idio_monthly_vols = rng.uniform(low, high, size=config.n_assets) / np.sqrt(MONTHS_PER_YEAR)
    idio_returns = pd.DataFrame(
        rng.normal(0.0, idio_monthly_vols, size=(config.n_months, config.n_assets)),
        index=months,
        columns=assets,
    )
    return FactorMarket(
        config=config, betas=betas, factor_returns=factor_returns, idio_returns=idio_returns
    )
