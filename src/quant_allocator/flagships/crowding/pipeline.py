"""Pure holdings math for the M4 crowding and overlap radar.

The robust outputs are point-in-time measurements.  The square-root impact
overlay is deliberately kept separate from those measurements.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

# M4 spec section 8 ruling 5.  Values remain in the batch numerics docket.
PARTICIPATION_LIMIT_M4 = 0.20
STRESS_VOLUME_DELTA_M4 = 0.50
IMPACT_GAMMA_M4 = 1.0
OVERLAP_ALERT_THRESHOLD = 0.30


@dataclass(frozen=True)
class PairOverlap:
    raw: float
    cosine: float
    liquidity: float


@dataclass(frozen=True)
class RosterOverlap:
    managers: tuple[str, ...]
    raw: pd.DataFrame
    cosine: pd.DataFrame
    liquidity: pd.DataFrame


@dataclass(frozen=True)
class UnwindRow:
    asset: str
    direction: str
    holder_count: int
    combined_dollars: float
    days_stressed_volume: float
    illustrative_impact_rate: float | None


@dataclass(frozen=True)
class UnwindReport:
    rows: tuple[UnwindRow, ...]
    worst: UnwindRow | None


def _vector(values: Any, *, name: str) -> np.ndarray:
    vector = np.asarray(values, dtype=float)
    if vector.ndim != 1:
        raise ValueError(f"{name} must be one-dimensional")
    if not np.isfinite(vector).all():
        raise ValueError(f"{name} must contain only finite values")
    return vector


def _matching_vectors(a: Any, b: Any, *, a_name: str, b_name: str) -> tuple[np.ndarray, np.ndarray]:
    left = _vector(a, name=a_name)
    right = _vector(b, name=b_name)
    if left.shape != right.shape:
        raise ValueError(f"{a_name} and {b_name} must have the same shape")
    return left, right


def gross_normalize(weights: Any) -> np.ndarray:
    """Scale a signed holdings vector so absolute weights sum to one."""
    vector = _vector(weights, name="weights")
    gross = float(np.abs(vector).sum())
    if gross <= 0.0:
        raise ValueError("weights must have strictly positive gross exposure")
    return vector / gross


def common_weight_overlap(w_a: Any, w_b: Any) -> float:
    """Directional common-weight overlap, counting same-sign positions only."""
    left, right = _matching_vectors(w_a, w_b, a_name="w_a", b_name="w_b")
    left = gross_normalize(left)
    right = gross_normalize(right)
    same_direction = (
        (np.sign(left) == np.sign(right)) & (left != 0.0) & (right != 0.0)
    )
    shared = np.minimum(np.abs(left), np.abs(right))
    return float(shared[same_direction].sum())


def cosine_overlap(w_a: Any, w_b: Any) -> float:
    """Signed cosine similarity of two non-empty holdings vectors."""
    left, right = _matching_vectors(w_a, w_b, a_name="w_a", b_name="w_b")
    left_norm = float(np.linalg.norm(left))
    right_norm = float(np.linalg.norm(right))
    if left_norm <= 0.0 or right_norm <= 0.0:
        raise ValueError("cosine vectors must have strictly positive norm")
    return float(np.clip(left @ right / (left_norm * right_norm), -1.0, 1.0))


def days_to_cover(
    dollar_positions: Any,
    adv_dollar: Any,
    *,
    participation: float = PARTICIPATION_LIMIT_M4,
) -> np.ndarray:
    """Absolute position size divided by the tradable share of daily dollar volume."""
    positions, adv = _matching_vectors(
        dollar_positions, adv_dollar, a_name="dollar_positions", b_name="adv_dollar"
    )
    if not 0.0 < participation <= 1.0:
        raise ValueError(f"participation must be in (0, 1], got {participation}")
    if np.any(adv <= 0.0):
        raise ValueError("adv_dollar must be strictly positive")
    return np.abs(positions) / (participation * adv)


def liquidity_adjusted_overlap(
    dollars_a: Any,
    dollars_b: Any,
    adv_dollar: Any,
    *,
    participation: float = PARTICIPATION_LIMIT_M4,
) -> float:
    """Directional overlap after re-expressing each book in unwind-time shares."""
    left, right = _matching_vectors(
        dollars_a, dollars_b, a_name="dollars_a", b_name="dollars_b"
    )
    adv = _vector(adv_dollar, name="adv_dollar")
    if adv.shape != left.shape:
        raise ValueError("adv_dollar and dollar positions must have the same shape")
    dtc_left = days_to_cover(left, adv, participation=participation)
    dtc_right = days_to_cover(right, adv, participation=participation)
    signed_left = np.sign(left) * dtc_left
    signed_right = np.sign(right) * dtc_right
    return common_weight_overlap(signed_left, signed_right)


def pair_overlap(
    dollars_a: Any,
    dollars_b: Any,
    adv_dollar: Any,
    *,
    participation: float = PARTICIPATION_LIMIT_M4,
) -> PairOverlap:
    """Package the three approved pairwise holdings measurements."""
    return PairOverlap(
        raw=common_weight_overlap(dollars_a, dollars_b),
        cosine=cosine_overlap(dollars_a, dollars_b),
        liquidity=liquidity_adjusted_overlap(
            dollars_a, dollars_b, adv_dollar, participation=participation
        ),
    )


def _aligned_inputs(
    dollar_positions: pd.DataFrame, adv_dollar: pd.Series
) -> tuple[pd.DataFrame, pd.Series]:
    if dollar_positions.empty:
        raise ValueError("dollar_positions must not be empty")
    if not dollar_positions.index.is_unique or not dollar_positions.columns.is_unique:
        raise ValueError("dollar_positions labels must be unique")
    if not adv_dollar.index.is_unique:
        raise ValueError("adv_dollar labels must be unique")
    missing = dollar_positions.columns.difference(adv_dollar.index)
    if len(missing):
        raise ValueError(f"adv_dollar is missing assets: {list(missing)}")
    positions = dollar_positions.astype(float)
    adv = adv_dollar.reindex(positions.columns).astype(float)
    if not np.isfinite(positions.to_numpy()).all():
        raise ValueError("dollar_positions must contain only finite values")
    if not np.isfinite(adv.to_numpy()).all() or (adv <= 0.0).any():
        raise ValueError("adv_dollar must be finite and strictly positive")
    if (positions.abs().sum(axis=1) <= 0.0).any():
        raise ValueError("every manager must have strictly positive gross exposure")
    return positions, adv


def roster_overlap_matrix(
    dollar_positions: pd.DataFrame,
    adv_dollar: pd.Series,
    *,
    participation: float = PARTICIPATION_LIMIT_M4,
) -> RosterOverlap:
    """Pairwise raw, signed-cosine, and unwind-space matrices for a roster."""
    positions, adv = _aligned_inputs(dollar_positions, adv_dollar)
    managers = tuple(str(label) for label in positions.index)
    n_managers = len(managers)
    raw = np.eye(n_managers)
    cosine = np.eye(n_managers)
    liquidity = np.eye(n_managers)
    for i in range(n_managers):
        for j in range(i + 1, n_managers):
            result = pair_overlap(
                positions.iloc[i].to_numpy(),
                positions.iloc[j].to_numpy(),
                adv.to_numpy(),
                participation=participation,
            )
            raw[i, j] = raw[j, i] = result.raw
            cosine[i, j] = cosine[j, i] = result.cosine
            liquidity[i, j] = liquidity[j, i] = result.liquidity
    labels = positions.index.copy()
    return RosterOverlap(
        managers=managers,
        raw=pd.DataFrame(raw, index=labels, columns=labels),
        cosine=pd.DataFrame(cosine, index=labels, columns=labels),
        liquidity=pd.DataFrame(liquidity, index=labels, columns=labels),
    )


def unwind_stress(
    dollar_positions: pd.DataFrame,
    adv_dollar: pd.Series,
    *,
    daily_vol: pd.Series | None = None,
    stress_delta: float = STRESS_VOLUME_DELTA_M4,
    impact_gamma: float = IMPACT_GAMMA_M4,
    min_holders: int = 2,
) -> UnwindReport:
    """Aggregate same-direction holder cohorts into stressed days-of-volume.

    Long and short cohorts are intentionally separate.  Opposite-direction books
    are offsets, not one liquidation crowd.
    """
    positions, adv = _aligned_inputs(dollar_positions, adv_dollar)
    if not 0.0 < stress_delta <= 1.0:
        raise ValueError(f"stress_delta must be in (0, 1], got {stress_delta}")
    if impact_gamma < 0.0 or not np.isfinite(impact_gamma):
        raise ValueError("impact_gamma must be finite and non-negative")
    if min_holders < 2:
        raise ValueError("min_holders must be at least 2")
    aligned_vol: pd.Series | None = None
    if daily_vol is not None:
        missing = positions.columns.difference(daily_vol.index)
        if len(missing):
            raise ValueError(f"daily_vol is missing assets: {list(missing)}")
        aligned_vol = daily_vol.reindex(positions.columns).astype(float)
        if not np.isfinite(aligned_vol.to_numpy()).all() or (aligned_vol < 0.0).any():
            raise ValueError("daily_vol must be finite and non-negative")

    rows: list[UnwindRow] = []
    for asset in positions.columns:
        column = positions[asset]
        for direction, selected in (("long", column[column > 0.0]), ("short", column[column < 0.0])):
            if len(selected) < min_holders:
                continue
            combined = float(selected.abs().sum())
            stressed_days = combined / (stress_delta * float(adv[asset]))
            impact = (
                impact_gamma * float(aligned_vol[asset]) * np.sqrt(stressed_days)
                if aligned_vol is not None
                else None
            )
            rows.append(
                UnwindRow(
                    asset=str(asset),
                    direction=direction,
                    holder_count=len(selected),
                    combined_dollars=combined,
                    days_stressed_volume=float(stressed_days),
                    illustrative_impact_rate=None if impact is None else float(impact),
                )
            )
    rows.sort(key=lambda row: (-row.days_stressed_volume, row.asset, row.direction))
    frozen_rows = tuple(rows)
    return UnwindReport(rows=frozen_rows, worst=frozen_rows[0] if frozen_rows else None)
