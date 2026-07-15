from __future__ import annotations

from datetime import UTC, datetime
from math import sqrt
from typing import Mapping

_FORBIDDEN_PARTS = (
    "quality",
    "best_manager",
    "top_manager",
    "recommended_manager",
    "probability_of_hire_success",
    "global_universe_coverage",
)


def require_aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None or value.utcoffset().total_seconds() != 0:
        raise ValueError("decision time must be timezone-aware UTC")
    return value.astimezone(UTC)


def wilson_interval(successes: int, total: int, z: float = 1.96) -> tuple[float, float]:
    if total <= 0 or not 0 <= successes <= total:
        raise ValueError("invalid binomial counts")
    p = successes / total
    denominator = 1 + z * z / total
    centre = (p + z * z / (2 * total)) / denominator
    half = z * sqrt((p * (1 - p) + z * z / (4 * total)) / total) / denominator
    return centre - half, centre + half


def assert_public_contract(value: object, pointer: str = "") -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            normalized = str(key).lower().replace("-", "_")
            if any(part in normalized for part in _FORBIDDEN_PARTS):
                raise ValueError(f"forbidden X3 output key at {pointer}/{key}")
            assert_public_contract(child, f"{pointer}/{key}")
    elif isinstance(value, (tuple, list)):
        for index, child in enumerate(value):
            assert_public_contract(child, f"{pointer}/{index}")
