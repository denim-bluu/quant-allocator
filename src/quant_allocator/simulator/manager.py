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
# S5 spec §6.5 / §8.7: the decorrelated short-signal noise panel draws under its own
# stream tag, AFTER the main manager noise, so short_information_coefficient=None is
# byte-identical. S4's exit-random dial (Task 5) takes tag 3.
_SHORT_SIGNAL_STREAM = 4
# S4 spec §3.8 / §8.5: exit_style="random" draws uniform incumbent choices under its
# own stream tag, AFTER the main manager noise, so exit_style="age" is byte-identical.
_EXIT_RANDOM_STREAM = 3
# M4 spec §6.6 / §8 ruling 3: the shared crowded sub-signal draws under its OWN stream tag,
# from a crowd_seed shared across participating managers, AFTER the main manager noise, so
# crowd_participation=0.0 is byte-identical. Tags 0-4 taken; ADV took 5 (market.py).
_CROWD_STREAM = 6
# S4 spec §3.8 / §8.7: disposition trailing-gain lookback (months). NUMERICS-GATE.
S4_DISPOSITION_TRAIL_MONTHS = 3
_EXIT_STYLES = ("age", "signal", "disposition", "random")


@dataclass(frozen=True)
class NetBetaDrift:
    """Linear net-beta drift schedule on target_net (M1 spec §4, ruled linear form).

    target_net at month t = base target_net
        + total_walk * clip((t - onset_month) / ramp_months, 0, 1).
    A book with net_drift=None is the honest manager; drift rescales the long/short
    side totals only, so it changes neither candidate selection nor RNG consumption.
    """

    total_walk: float
    ramp_months: int
    onset_month: int = 0


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
    # M1 spec §4: linear net-beta drift schedule on target_net (None = honest manager).
    net_drift: NetBetaDrift | None = None
    # M3 spec §4: 0-based month at which the fresh IC steps to zero (alpha death).
    # None (default) or a value >= n_months is the honest, byte-identical manager.
    death_month: int | None = None
    # S3 spec §6.5: deterministic decaying held-name edge on realized idio.
    # 0.0 (default) is byte-identical (edge term is zero, no RNG consumed). Demo 0.5.
    # NUMERICS-GATE: the edge scales by the PER-NAME idio std (the std the manager
    # already uses for z-scoring), not a single market-wide idio_vol.
    alpha_persistence: float = 0.0
    # S5 spec §6.5: separate short-side picking skill. None (default) keeps the single
    # signal panel (byte-identical, no new draws); a value draws a decorrelated short
    # panel under _SHORT_SIGNAL_STREAM and picks/sizes shorts on it. Demo 0.06.
    short_information_coefficient: float | None = None
    # S4 spec §3.8: which incumbents each side retires. "age" (default) is the current
    # oldest-first replacement (byte-identical). "signal"/"disposition" are the S4
    # disciplined/flawed managers; "random" is the validation-only specificity control
    # and consumes RNG under _EXIT_RANDOM_STREAM.
    exit_style: str = "age"
    # M4 spec §6.6: fraction of fresh-signal NOISE VARIANCE drawn from a crowded sub-signal
    # shared (via crowd_seed) across participating managers. 0.0 (default) draws no crowd
    # RNG and is byte-identical. NUMERICS-GATE: variance-fraction convention; short panel
    # left uncontaminated in v1.
    crowd_participation: float = 0.0
    # M4 spec §6.6: seed of the SHARED crowd generator; managers sharing it draw the same
    # crowded sub-signal. Ignored when crowd_participation == 0.0.
    crowd_seed: int = 0


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


def _incumbent_directional_signal(
    names: list[str], sign: float, ic_base: float, half_life: float,
    ages: dict[str, int], z_row: np.ndarray, noise_row: np.ndarray, asset_pos: dict[str, int]
) -> dict[str, float]:
    """Refreshed conviction of held `names` in their held direction at month t:
    sign * (ic_eff(age) * z + sqrt(1 - ic_eff^2) * noise). Higher = stronger edge."""
    out: dict[str, float] = {}
    for name in names:
        col = asset_pos[name]
        ic_eff = ic_base * 0.5 ** (ages[name] / half_life)
        raw = ic_eff * z_row[col] + np.sqrt(1.0 - ic_eff**2) * noise_row[col]
        out[name] = sign * raw
    return out


def _incumbent_trailing_gain(
    names: list[str], sign: float, idio: np.ndarray, t: int, trail: int, asset_pos: dict[str, int]
) -> dict[str, float]:
    """Directional trailing gain over [max(0, t - trail), t): sign * sum(past idio)."""
    lo = max(0, t - trail)
    window = idio[lo:t]
    return {name: sign * float(window[:, asset_pos[name]].sum()) for name in names}


def _target_net_path(config: ManagerConfig, n_months: int) -> np.ndarray:
    """Per-month target_net. Constant (= config.target_net) when drift is OFF, so the
    honest manager is byte-identical; a linear ramp that holds at base+total_walk when ON.
    """
    if config.net_drift is None:
        return np.full(n_months, config.target_net)
    drift = config.net_drift
    t = np.arange(n_months, dtype=float)
    progress = np.clip((t - drift.onset_month) / drift.ramp_months, 0.0, 1.0)
    return config.target_net + drift.total_walk * progress


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
    if config.alpha_persistence < 0.0:
        raise ValueError(f"alpha_persistence must be >= 0, got {config.alpha_persistence}")
    if config.short_information_coefficient is not None and not (
        0.0 <= config.short_information_coefficient <= 1.0
    ):
        raise ValueError(
            "short_information_coefficient must be in [0, 1] or None, got "
            f"{config.short_information_coefficient}"
        )
    if config.exit_style not in _EXIT_STYLES:
        raise ValueError(f"exit_style must be one of {_EXIT_STYLES}, got {config.exit_style!r}")
    if not 0.0 <= config.crowd_participation <= 1.0:
        raise ValueError(
            f"crowd_participation must be in [0, 1], got {config.crowd_participation}"
        )
    if config.net_drift is not None:
        drift = config.net_drift
        if drift.ramp_months <= 0:
            raise ValueError(f"net_drift.ramp_months must be > 0, got {drift.ramp_months}")
        if drift.onset_month < 0:
            raise ValueError(f"net_drift.onset_month must be >= 0, got {drift.onset_month}")
        extreme_net = config.target_net + drift.total_walk
        if abs(extreme_net) >= config.target_gross:
            raise ValueError(
                f"drifted net {extreme_net} must stay within "
                f"(-target_gross, target_gross)=(-{config.target_gross}, {config.target_gross})"
            )

    rng = np.random.default_rng([config.seed, _MANAGER_STREAM])
    months = market.idio_returns.index
    assets = market.betas.index
    # Full-history std is deliberate in-sample scaling for synthetic ground truth; z is never emitted to allocator views.
    idio_std = market.idio_returns.std()
    z = market.idio_returns / idio_std
    noise = rng.standard_normal(z.shape)
    if config.crowd_participation > 0.0:
        c = config.crowd_participation
        crowd_noise = np.random.default_rng(
            [config.crowd_seed, _CROWD_STREAM]
        ).standard_normal(z.shape)
        # Variance-preserving convex blend: a share c of the noise variance is the shared
        # crowded sub-signal, so participating managers correlate by a known fraction.
        noise = np.sqrt(1.0 - c) * noise + np.sqrt(c) * crowd_noise
    short_ic = config.short_information_coefficient
    noise_short = (
        np.random.default_rng([config.seed, _SHORT_SIGNAL_STREAM]).standard_normal(z.shape)
        if short_ic is not None
        else None
    )
    exit_rng = (
        np.random.default_rng([config.seed, _EXIT_RANDOM_STREAM])
        if config.exit_style == "random"
        else None
    )
    asset_pos = {name: i for i, name in enumerate(assets)}
    idio_matrix = market.idio_returns.to_numpy()

    persistence_on = config.alpha_persistence != 0.0
    if persistence_on:
        idio_std_arr = idio_std.to_numpy()
        idio_edge = np.zeros((len(months), len(assets)))

    ages: dict[str, int] = {}
    longs: list[str] = []
    shorts: list[str] = []
    weight_rows: list[pd.Series] = []

    n_rep_long = round(config.rebalance_fraction * config.n_long)
    n_rep_short = round(config.rebalance_fraction * config.n_short)
    net_path = _target_net_path(config, len(months))

    for t in range(len(months)):
        for name in ages:
            ages[name] += 1

        if t > 0:
            if config.exit_style == "age":
                drop_long = sorted(longs, key=lambda n: (-ages[n], n))[:n_rep_long]
                drop_short = sorted(shorts, key=lambda n: (-ages[n], n))[:n_rep_short]
            elif config.exit_style == "signal":
                z_row = z.iloc[t].to_numpy()
                long_conv = _incumbent_directional_signal(
                    longs, 1.0, config.information_coefficient, config.alpha_half_life_months,
                    ages, z_row, noise[t], asset_pos,
                )
                short_ic_base = config.information_coefficient if short_ic is None else short_ic
                short_noise_row = noise[t] if short_ic is None else noise_short[t]
                short_conv = _incumbent_directional_signal(
                    shorts, -1.0, short_ic_base, config.alpha_half_life_months,
                    ages, z_row, short_noise_row, asset_pos,
                )
                drop_long = sorted(longs, key=lambda n: (long_conv[n], n))[:n_rep_long]
                drop_short = sorted(shorts, key=lambda n: (short_conv[n], n))[:n_rep_short]
            elif config.exit_style == "disposition":
                trail = S4_DISPOSITION_TRAIL_MONTHS
                long_gain = _incumbent_trailing_gain(longs, 1.0, idio_matrix, t, trail, asset_pos)
                short_gain = _incumbent_trailing_gain(shorts, -1.0, idio_matrix, t, trail, asset_pos)
                drop_long = sorted(longs, key=lambda n: (-long_gain[n], n))[:n_rep_long]
                drop_short = sorted(shorts, key=lambda n: (-short_gain[n], n))[:n_rep_short]
            else:  # "random"
                drop_long = [longs[i] for i in exit_rng.permutation(len(longs))[:n_rep_long]]
                drop_short = [shorts[i] for i in exit_rng.permutation(len(shorts))[:n_rep_short]]
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
        if short_ic is None:
            short_signals = signals
        else:
            short_ic_eff = short_ic * 0.5 ** (age_vec.to_numpy() / config.alpha_half_life_months)
            if config.death_month is not None and t >= config.death_month:
                short_ic_eff = np.zeros_like(short_ic_eff)
            short_signals = pd.Series(
                short_ic_eff * z.iloc[t].to_numpy()
                + np.sqrt(1.0 - short_ic_eff**2) * noise_short[t],
                index=assets,
            )

        held = set(longs) | set(shorts)
        need_long = config.n_long - len(longs)
        need_short = config.n_short - len(shorts)
        long_candidates = signals.drop(index=list(held)).sort_values()
        new_longs = list(long_candidates.index[-need_long:]) if need_long else []
        short_candidates = short_signals.drop(index=list(held | set(new_longs))).sort_values()
        new_shorts = list(short_candidates.index[:need_short]) if need_short else []
        longs += new_longs
        shorts += new_shorts
        for name in (*new_longs, *new_shorts):
            ages[name] = 0

        if persistence_on:
            decay = config.alpha_persistence
            hl = config.alpha_half_life_months
            for name in longs:
                col = asset_pos[name]
                idio_edge[t, col] = decay * 0.5 ** (ages[name] / hl) * idio_std_arr[col]
            for name in shorts:
                col = asset_pos[name]
                idio_edge[t, col] = -decay * 0.5 ** (ages[name] / hl) * idio_std_arr[col]

        target_net_t = net_path[t]
        long_total = (config.target_gross + target_net_t) / 2.0
        short_total = (config.target_gross - target_net_t) / 2.0
        weights = pd.Series(0.0, index=assets)
        weights.loc[longs] = _side_weights(
            longs, signals, long_total, 1.0, config.sizing_discipline
        )
        weights.loc[shorts] = _side_weights(
            shorts, short_signals, short_total, -1.0, config.sizing_discipline
        )
        weight_rows.append(weights)

    weights = pd.DataFrame(weight_rows, index=months)
    weights.index.name = "month"
    weights.columns.name = "asset"
    if persistence_on:
        edge_df = pd.DataFrame(idio_edge, index=months, columns=assets)
        realized_idio = market.idio_returns + edge_df
        realized_asset_returns = market.asset_returns + edge_df
        monthly_returns = (weights * realized_asset_returns).sum(axis=1)
        true_alpha_returns = (weights * realized_idio).sum(axis=1)
    else:
        monthly_returns = (weights * market.asset_returns).sum(axis=1)
        true_alpha_returns = (weights * market.idio_returns).sum(axis=1)
    return ManagerHistory(
        config=config,
        weights=weights,
        monthly_returns=monthly_returns,
        true_alpha_returns=true_alpha_returns,
    )
