"""Synthetic factor-model equity market: the ground-truth world managers trade in."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

MONTHS_PER_YEAR = 12
# Distinct per-module stream tags keep same-seed modules statistically independent.
_MARKET_STREAM = 0


def _apply_idio_ar1(innovations: np.ndarray, rho: float) -> np.ndarray:
    """AR(1) filter preserving stationary marginal variance (S4 §3.8 / §8.5).

    idio_0 = innov_0 (a stationary start reusing the first draw, so no new RNG is
    consumed); idio_t = rho * idio_{t-1} + sqrt(1 - rho**2) * innov_t. rho = 0 returns
    the innovations unchanged -> byte-identical to the iid generator.
    """
    if rho == 0.0:
        return innovations
    scale = np.sqrt(1.0 - rho**2)
    idio = np.empty_like(innovations)
    idio[0] = innovations[0]
    for t in range(1, innovations.shape[0]):
        idio[t] = rho * idio[t - 1] + scale * innovations[t]
    return idio


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
    # S4 spec §3.8 / §8.5: AR(1) coefficient on idiosyncratic returns, a filter on the
    # existing innovation draws. 0.0 (default) is the byte-identical iid generator; a
    # value makes a name's idio edge persist forward. Demo S4_IDIO_AR1_DEMO = 0.4.
    idio_ar1: float = 0.0


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
    if not -1.0 < config.idio_ar1 < 1.0:
        raise ValueError(f"idio_ar1 must be in (-1, 1) for stationarity, got {config.idio_ar1}")
    rng = np.random.default_rng([config.seed, _MARKET_STREAM])
    months = pd.period_range(config.start_month, periods=config.n_months, freq="M", name="month")
    assets = pd.Index([f"A{i:04d}" for i in range(config.n_assets)], name="asset")
    factors = list(config.factor_names)

    monthly_means = np.asarray(config.factor_annual_means) / MONTHS_PER_YEAR
    monthly_vols = np.asarray(config.factor_annual_vols) / np.sqrt(MONTHS_PER_YEAR)
    factor_returns = pd.DataFrame(
        rng.normal(monthly_means, monthly_vols, size=(config.n_months, len(factors))),
        index=months,
        columns=factors,
    )

    # factor_names[0] is treated as the market factor (beta ~ N(1, 0.25)); style betas attach to the rest.
    market_beta = rng.normal(1.0, 0.25, size=config.n_assets)
    style_betas = rng.normal(0.0, 0.5, size=(config.n_assets, len(factors) - 1))
    betas = pd.DataFrame(
        np.column_stack([market_beta, style_betas]), index=assets, columns=factors
    )

    low, high = config.idio_annual_vol_range
    idio_monthly_vols = rng.uniform(low, high, size=config.n_assets) / np.sqrt(MONTHS_PER_YEAR)
    # Innovation draws are IDENTICAL to the iid generator (byte-identity at rho=0).
    innovations = rng.normal(0.0, idio_monthly_vols, size=(config.n_months, config.n_assets))
    idio = _apply_idio_ar1(innovations, config.idio_ar1)
    idio_returns = pd.DataFrame(idio, index=months, columns=assets)
    return FactorMarket(
        config=config, betas=betas, factor_returns=factor_returns, idio_returns=idio_returns
    )
