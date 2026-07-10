"""Pure holdings math for the M4 crowding and overlap radar.

The robust outputs are point-in-time measurements.  The square-root impact
overlay is deliberately kept separate from those measurements.
"""

from __future__ import annotations

from typing import Any

import numpy as np

# M4 spec section 8 ruling 5.  Values remain in the batch numerics docket.
PARTICIPATION_LIMIT_M4 = 0.20
STRESS_VOLUME_DELTA_M4 = 0.50
IMPACT_GAMMA_M4 = 1.0
OVERLAP_ALERT_THRESHOLD = 0.30


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
