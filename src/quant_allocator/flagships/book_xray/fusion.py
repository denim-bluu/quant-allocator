"""P2 static measurement-error fusion for a mixed-transparency manager book.

The gallery uses the normal-normal single-review-date special case.  The temporal
filter remains wave-3 scope.  This module is pure: no simulator, I/O, or rendering.
"""

from __future__ import annotations

import math
import statistics
from dataclasses import dataclass, field
from typing import Mapping, Sequence

import numpy as np


def _default_measurement_sds() -> dict[str, float]:
    # P2 §8.1 (NUMERICS-GATE): provisional until the atlas exposure rows land.
    return {"P": 0.02, "E": 0.08, "R": 0.25}


@dataclass(frozen=True)
class FusionConfig:
    exposure_meas_sd: Mapping[str, float] = field(default_factory=_default_measurement_sds)
    prior_mean: float = 0.20
    prior_sd: float = 0.50
    credible_level: float = 0.90
    info_gain_floor: float = 0.20


@dataclass(frozen=True)
class MeasurementPosterior:
    mean: float
    sd: float


@dataclass(frozen=True)
class BookPosterior:
    mean: float
    sd: float
    ci_lo: float
    ci_hi: float


@dataclass(frozen=True)
class FusedBook:
    manager_posteriors: tuple[MeasurementPosterior, ...]
    book: BookPosterior
    provenance: np.ndarray


def measurement_posterior(
    prior_mean: float, prior_sd: float, observation: float, meas_sd: float
) -> MeasurementPosterior:
    """Normal-normal update for one manager's latent factor exposure."""
    values = (prior_mean, prior_sd, observation, meas_sd)
    if not all(math.isfinite(value) for value in values):
        raise ValueError("posterior inputs must be finite")
    if prior_sd <= 0.0 or meas_sd <= 0.0:
        raise ValueError("prior_sd and meas_sd must be positive")
    prior_precision = 1.0 / prior_sd**2
    measurement_precision = 1.0 / meas_sd**2
    variance = 1.0 / (prior_precision + measurement_precision)
    mean = variance * (
        prior_precision * prior_mean + measurement_precision * observation
    )
    return MeasurementPosterior(mean=float(mean), sd=float(math.sqrt(variance)))


def _book_arrays(capital_weights, posterior_means, posterior_sds):
    weights = np.asarray(capital_weights, dtype=float)
    means = np.asarray(posterior_means, dtype=float)
    sds = np.asarray(posterior_sds, dtype=float)
    if weights.ndim != 1 or means.ndim != 1 or sds.ndim != 1:
        raise ValueError("book inputs must be one-dimensional")
    if not (len(weights) == len(means) == len(sds)):
        raise ValueError("book inputs must have the same length")
    if len(weights) == 0:
        raise ValueError("book inputs cannot be empty")
    if not np.isfinite(weights).all() or not np.isfinite(means).all() or not np.isfinite(sds).all():
        raise ValueError("book inputs must be finite")
    if (weights < 0.0).any() or not np.isclose(weights.sum(), 1.0, atol=1e-12):
        raise ValueError("capital weights must be non-negative and sum to 1")
    if (sds <= 0.0).any():
        raise ValueError("posterior sds must be positive")
    return weights, means, sds


def book_posterior(
    capital_weights, posterior_means, posterior_sds, *, level: float = 0.90
) -> BookPosterior:
    """Capital-weighted book posterior under conditional manager independence."""
    if not 0.0 < level < 1.0:
        raise ValueError("credible level must lie in (0, 1)")
    weights, means, sds = _book_arrays(
        capital_weights, posterior_means, posterior_sds
    )
    mean = float(weights @ means)
    variance = float((weights**2) @ (sds**2))
    sd = math.sqrt(variance)
    z = statistics.NormalDist().inv_cdf(0.5 + level / 2.0)
    return BookPosterior(
        mean=mean,
        sd=sd,
        ci_lo=mean - z * sd,
        ci_hi=mean + z * sd,
    )


def provenance(capital_weights, posterior_sds) -> np.ndarray:
    """Per-manager share of the book exposure variance."""
    weights = np.asarray(capital_weights, dtype=float)
    sds = np.asarray(posterior_sds, dtype=float)
    if weights.ndim != 1 or sds.ndim != 1 or len(weights) != len(sds):
        raise ValueError("weights and posterior_sds must be aligned one-dimensional arrays")
    if not np.isfinite(weights).all() or not np.isfinite(sds).all():
        raise ValueError("provenance inputs must be finite")
    if (weights < 0.0).any() or (sds <= 0.0).any():
        raise ValueError("weights must be non-negative and posterior sds positive")
    contributions = (weights**2) * (sds**2)
    total = float(contributions.sum())
    if total <= 0.0:
        raise ValueError("book exposure variance must be positive")
    return contributions / total


def fuse_book(
    capital_weights,
    observations,
    tiers: Sequence[str],
    config: FusionConfig,
) -> FusedBook:
    """Fuse one observation per manager at the precision earned by its tier."""
    observations_array = np.asarray(observations, dtype=float)
    weights = np.asarray(capital_weights, dtype=float)
    if len(tiers) != len(observations_array) or len(weights) != len(observations_array):
        raise ValueError("weights, observations, and tiers must have the same length")
    posteriors: list[MeasurementPosterior] = []
    for observation, tier in zip(observations_array, tiers, strict=True):
        if tier not in config.exposure_meas_sd:
            raise ValueError(f"unknown transparency tier {tier!r}")
        posteriors.append(
            measurement_posterior(
                config.prior_mean,
                config.prior_sd,
                float(observation),
                float(config.exposure_meas_sd[tier]),
            )
        )
    means = np.array([posterior.mean for posterior in posteriors])
    sds = np.array([posterior.sd for posterior in posteriors])
    return FusedBook(
        manager_posteriors=tuple(posteriors),
        book=book_posterior(weights, means, sds, level=config.credible_level),
        provenance=provenance(weights, sds),
    )
