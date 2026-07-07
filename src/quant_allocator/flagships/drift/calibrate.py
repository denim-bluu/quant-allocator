"""Null-calibration harness for the M1 sustained-drift alarm (M1 spec §4).

Calibrate-then-measure, order enforced by the spec: (1) on the honest-wander null,
pick the CUSUM decision interval h that meets the per-manager-year false-alarm
budget; (2) with h fixed, measure detection and delay on the drift alternative, each
with a Wilson 95% interval. The null is the simulator's actual AUTOCORRELATED
honest-wander distribution — never a closed-form iid ARL (M1 §3.4): calibrating on an
iid null under-sets h and over-fires when the real book's turnover serially correlates
the wander. The draw helpers are the only simulator import in the drift lane.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from quant_allocator.flagships.drift import detector
from quant_allocator.flagships.drift.bands import BandSpec
from quant_allocator.simulator.manager import ManagerConfig, NetBetaDrift, simulate_manager
from quant_allocator.simulator.market import MarketConfig, simulate_market
from quant_allocator.simulator.tiers import emit_tiers


def wilson_interval(successes: int, n: int, z: float = 1.96) -> tuple[float, float]:
    # Wilson score interval for a binomial proportion (M1 spec §4.4: no bare rate).
    if n == 0:
        return (0.0, 1.0)
    phat = successes / n
    z2 = z * z
    denom = 1.0 + z2 / n
    center = (phat + z2 / (2 * n)) / denom
    half = (z / denom) * math.sqrt(phat * (1 - phat) / n + z2 / (4 * n * n))
    return (max(0.0, center - half), min(1.0, center + half))


def false_alarm_rate(
    null_paths: list[np.ndarray], band: BandSpec, k: float, h: float, months_per_year: int = 12
) -> tuple[float, int, int]:
    # Per-manager-year rate: alarming null paths / total manager-years observed.
    n_alarming = sum(1 for p in null_paths if detector.cusum_alarm(p, band, k, h).fired)
    manager_years = sum(len(p) for p in null_paths) / months_per_year
    rate = n_alarming / manager_years if manager_years > 0 else 0.0
    return (rate, n_alarming, len(null_paths))


def calibrate_threshold(
    null_paths: list[np.ndarray],
    band: BandSpec,
    k: float,
    budget_per_year: float,
    h_grid: np.ndarray,
    months_per_year: int = 12,
) -> float:
    # Smallest h on the grid meeting the budget = most sensitive detector that still
    # respects the false-alarm budget (M1 spec §4.1). h is chosen by calibration, not
    # a free dial.
    for h in np.sort(h_grid):
        rate, _, _ = false_alarm_rate(null_paths, band, k, float(h), months_per_year)
        if rate <= budget_per_year:
            return float(h)
    return float("inf")


@dataclass(frozen=True)
class DetectionResult:
    rate: float
    wilson_lo: float
    wilson_hi: float
    n_detected: int
    n_paths: int
    median_delay: float | None


def measure_detection(
    alt_paths: list[np.ndarray],
    band: BandSpec,
    k: float,
    h: float,
    drift_onset: int,
    detection_window: int,
    z: float = 1.96,
) -> DetectionResult:
    # P(alarm within `detection_window` months of the series start) and the detection-
    # delay distribution among detected paths (M1 spec §4.2).
    delays: list[int] = []
    n_detected = 0
    for p in alt_paths:
        alarm = detector.cusum_alarm(p, band, k, h)
        if alarm.fired and alarm.alarm_month <= detection_window:
            n_detected += 1
            delays.append(detector.detection_delay(alarm.alarm_month, drift_onset))
    n = len(alt_paths)
    rate = n_detected / n if n else 0.0
    lo, hi = wilson_interval(n_detected, n, z)
    median_delay = float(np.median(delays)) if delays else None
    return DetectionResult(
        rate=rate,
        wilson_lo=lo,
        wilson_hi=hi,
        n_detected=n_detected,
        n_paths=n,
        median_delay=median_delay,
    )


def _simulate_book(
    seed: int, n_assets: int, n_months: int, target_net: float,
    drift: NetBetaDrift | None, manager_kwargs: dict,
):
    market = simulate_market(MarketConfig(n_assets=n_assets, n_months=n_months, seed=seed))
    history = simulate_manager(
        market,
        ManagerConfig(target_net=target_net, net_drift=drift, **manager_kwargs),
    )
    return market, history


def draw_beta_paths(
    n_paths: int, base_seed: int, n_assets: int, n_months: int, target_net: float,
    drift: NetBetaDrift | None, manager_kwargs: dict,
) -> list[np.ndarray]:
    # Each path = one honest-wander (drift=None) or drifted manager, seeded by a
    # distinct market seed so the ensemble is the autocorrelated null / alternative.
    paths = []
    for i in range(n_paths):
        market, history = _simulate_book(
            base_seed + i, n_assets, n_months, target_net, drift, manager_kwargs
        )
        exposures = emit_tiers(market, history).exposures
        paths.append(exposures["beta_market"].to_numpy())
    return paths


def draw_rolling_beta_paths(
    n_paths: int, base_seed: int, n_assets: int, n_months: int, target_net: float,
    drift: NetBetaDrift | None, window: int, manager_kwargs: dict,
) -> list[np.ndarray]:
    # R-tier: infer the net market beta from returns via RBSA, on the SAME managers.
    paths = []
    for i in range(n_paths):
        market, history = _simulate_book(
            base_seed + i, n_assets, n_months, target_net, drift, manager_kwargs
        )
        rbeta = detector.rolling_beta_path(
            history.monthly_returns.to_numpy(), market.factor_returns.to_numpy(), window
        )
        paths.append(rbeta)
    return paths
