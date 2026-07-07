"""Synthetic equity long/short manager with dialable ground-truth skill.

Generative model: each month the manager receives, per asset, a noisy signal
about that month's standardized idiosyncratic return. Signal quality is
`information_coefficient` for fresh picks and decays with holding age at
`alpha_half_life_months`. Each month the oldest `rebalance_fraction` of each
side is replaced by the freshest-signal candidates. Sizes interpolate between
signal-proportional (sizing_discipline=1) and equal-weight (0), scaled to hit
target_gross / target_net exactly.

Sizing uses signal magnitude within each side, so an aged long whose refreshed
signal turned negative is sized by conviction magnitude, not direction.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from quant_allocator.simulator.market import FactorMarket

_MANAGER_STREAM = 1


@dataclass(frozen=True)
class ManagerConfig:
    n_long: int = 40
    n_short: int = 25
    target_gross: float = 1.6
    target_net: float = 0.2
    information_coefficient: float = 0.05
    alpha_half_life_months: float = 6.0
    sizing_discipline: float = 1.0
    rebalance_fraction: float = 0.25
    seed: int = 0
    # M3 spec §4: 0-based month at which the fresh IC steps to zero (alpha death).
    # None (default) or a value >= n_months is the honest, byte-identical manager.
    death_month: int | None = None


@dataclass(frozen=True)
class ManagerHistory:
    config: ManagerConfig
    weights: pd.DataFrame
    monthly_returns: pd.Series
    true_alpha_returns: pd.Series


def effective_information_coefficient(
    age_months: float | np.ndarray, config: ManagerConfig
) -> np.ndarray:
    age = np.asarray(age_months, dtype=float)
    return config.information_coefficient * 0.5 ** (age / config.alpha_half_life_months)


def _side_weights(
    names: list[str], signals: pd.Series, total: float, sign: float, discipline: float
) -> pd.Series:
    strength = signals.loc[names].abs()
    raw = discipline * strength + (1.0 - discipline) * 1.0
    return sign * total * raw / raw.sum()


def simulate_manager(market: FactorMarket, config: ManagerConfig) -> ManagerHistory:
    if not 0.0 <= config.information_coefficient <= 1.0:
        raise ValueError(
            f"information_coefficient must be in [0, 1], got {config.information_coefficient}"
        )
    if not 0.0 <= config.sizing_discipline <= 1.0:
        raise ValueError(f"sizing_discipline must be in [0, 1], got {config.sizing_discipline}")
    if not 0.0 < config.rebalance_fraction <= 1.0:
        raise ValueError(
            f"rebalance_fraction must be in (0, 1], got {config.rebalance_fraction}"
        )
    if config.n_long + config.n_short > len(market.betas.index):
        raise ValueError(
            f"book size {config.n_long + config.n_short} exceeds asset universe "
            f"of {len(market.betas.index)}"
        )
    if config.death_month is not None and config.death_month < 0:
        raise ValueError(f"death_month must be >= 0 or None, got {config.death_month}")

    rng = np.random.default_rng([config.seed, _MANAGER_STREAM])
    months = market.idio_returns.index
    assets = market.betas.index
    # Full-history std is deliberate in-sample scaling for synthetic ground truth; z is never emitted to allocator views.
    z = market.idio_returns / market.idio_returns.std()
    noise = rng.standard_normal(z.shape)

    ages: dict[str, int] = {}
    longs: list[str] = []
    shorts: list[str] = []
    weight_rows: list[pd.Series] = []

    n_rep_long = round(config.rebalance_fraction * config.n_long)
    n_rep_short = round(config.rebalance_fraction * config.n_short)

    for t in range(len(months)):
        for name in ages:
            ages[name] += 1

        if t > 0:
            drop_long = sorted(longs, key=lambda n: (-ages[n], n))[:n_rep_long]
            drop_short = sorted(shorts, key=lambda n: (-ages[n], n))[:n_rep_short]
            for name in (*drop_long, *drop_short):
                ages.pop(name)
            longs = [n for n in longs if n not in set(drop_long)]
            shorts = [n for n in shorts if n not in set(drop_short)]

        age_vec = pd.Series(0.0, index=assets)
        for name, age in ages.items():
            age_vec[name] = float(age)
        ic_eff = effective_information_coefficient(age_vec.to_numpy(), config)
        if config.death_month is not None and t >= config.death_month:
            # Alpha death: fresh IC -> 0, so signals collapse to pure noise (M3 §4).
            # The pre-drawn `noise` array is untouched, so death_month=None is byte-identical.
            ic_eff = np.zeros_like(ic_eff)
        signals = pd.Series(
            ic_eff * z.iloc[t].to_numpy() + np.sqrt(1.0 - ic_eff**2) * noise[t],
            index=assets,
        )

        held = set(longs) | set(shorts)
        candidates = signals.drop(index=list(held)).sort_values()
        need_long = config.n_long - len(longs)
        need_short = config.n_short - len(shorts)
        new_longs = list(candidates.index[-need_long:]) if need_long else []
        new_shorts = list(candidates.index[:need_short]) if need_short else []
        longs += new_longs
        shorts += new_shorts
        for name in (*new_longs, *new_shorts):
            ages[name] = 0

        long_total = (config.target_gross + config.target_net) / 2.0
        short_total = (config.target_gross - config.target_net) / 2.0
        weights = pd.Series(0.0, index=assets)
        weights.loc[longs] = _side_weights(
            longs, signals, long_total, 1.0, config.sizing_discipline
        )
        weights.loc[shorts] = _side_weights(
            shorts, signals, short_total, -1.0, config.sizing_discipline
        )
        weight_rows.append(weights)

    weights = pd.DataFrame(weight_rows, index=months)
    weights.index.name = "month"
    weights.columns.name = "asset"
    monthly_returns = (weights * market.asset_returns).sum(axis=1)
    true_alpha_returns = (weights * market.idio_returns).sum(axis=1)
    return ManagerHistory(
        config=config,
        weights=weights,
        monthly_returns=monthly_returns,
        true_alpha_returns=true_alpha_returns,
    )
