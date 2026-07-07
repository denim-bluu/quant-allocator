"""Deterministic drift statistics over a measured exposure path (M1 spec §3).

Pure functions of numpy arrays and a BandSpec — no I/O, no simulator import, no
random numbers. The measurement (breach flags) is exact; the sustained-drift alarm
is Page's (1954) one-sided CUSUM, whose only statistical content is separating a
*persistent* excursion from transient wander — resolved by the threshold h that
calibrate.py sets on the autocorrelated null (M1 spec §3.3-§3.4).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from quant_allocator.flagships.drift.bands import BandSpec


def breach_flags(path: np.ndarray, band: BandSpec) -> np.ndarray:
    # M1 spec §3.2: exact instantaneous flag with the materiality dead-band δ.
    path = np.asarray(path, dtype=float)
    return (path < band.lower - band.delta) | (path > band.upper + band.delta)


@dataclass(frozen=True)
class DriftAlarm:
    fired: bool
    alarm_month: int | None
    s_plus: np.ndarray
    s_minus: np.ndarray
    side: str | None


def cusum_alarm(path: np.ndarray, band: BandSpec, k: float, h: float) -> DriftAlarm:
    # M1 spec §3.3: two one-sided accumulators against the band edges, in the
    # exposure's own units. S+ accumulates excursions above U beyond allowance k;
    # S- accumulates excursions below L. The alarm fires at the first month either
    # accumulator exceeds the calibrated decision interval h.
    path = np.asarray(path, dtype=float)
    n = path.shape[0]
    s_plus = np.zeros(n)
    s_minus = np.zeros(n)
    alarm_month: int | None = None
    side: str | None = None
    sp = 0.0
    sm = 0.0
    for t in range(n):
        sp = max(0.0, sp + (path[t] - band.upper) - k)
        sm = max(0.0, sm + (band.lower - path[t]) - k)
        s_plus[t] = sp
        s_minus[t] = sm
        if alarm_month is None:
            if sp > h:
                alarm_month, side = t, "upper"
            elif sm > h:
                alarm_month, side = t, "lower"
    return DriftAlarm(
        fired=alarm_month is not None,
        alarm_month=alarm_month,
        s_plus=s_plus,
        s_minus=s_minus,
        side=side,
    )


def detection_delay(alarm_month: int | None, drift_onset: int) -> int | None:
    # Months from the (known-in-simulation) drift onset to the alarm (M1 spec §4.2).
    if alarm_month is None:
        return None
    return alarm_month - drift_onset


def run_length_rung(
    path: np.ndarray, band: BandSpec, k_consec: int, m_window: int
) -> int | None:
    # M1 spec §3.3 simple sibling: fires the first month the exposure sits outside
    # [L-δ, U+δ] for k_consec of the last m_window observations. Strictly weaker than
    # CUSUM (ignores excursion magnitude); offered as the plain-language rung.
    outside = breach_flags(path, band).astype(int)
    for t in range(m_window - 1, outside.shape[0]):
        if outside[t - m_window + 1 : t + 1].sum() >= k_consec:
            return t
    return None


def factor_share(betas_row: np.ndarray, factor_cov: np.ndarray, idio_var: float) -> float:
    # M1 spec §3.5: factor-explained share of predicted variance. Estimate-bearing
    # via σ̂²_idio (the lead reviewer §3.5 ruling) — rendered as a slope IntervalStat, not a point.
    betas_row = np.asarray(betas_row, dtype=float)
    factor_var = float(betas_row @ np.asarray(factor_cov, dtype=float) @ betas_row)
    denom = factor_var + idio_var
    return factor_var / denom if denom > 0 else 0.0


def factor_share_path(betas: np.ndarray, factor_cov: np.ndarray, idio_var: float) -> np.ndarray:
    betas = np.asarray(betas, dtype=float)
    return np.array([factor_share(row, factor_cov, idio_var) for row in betas])


def rolling_beta_path(returns: np.ndarray, factors: np.ndarray, window: int) -> np.ndarray:
    # M1 spec §3.6 R-tier: Sharpe (1992) RBSA as a drift proxy — rolling OLS of returns
    # on the factor set; the market-factor (column 0) coefficient is the inferred net
    # market beta. Deliberately the weak rung: at short windows the rolling multivariate
    # regression's estimation variance buries a real net-beta walk (M1 §8).
    returns = np.asarray(returns, dtype=float)
    factors = np.asarray(factors, dtype=float)
    n = returns.shape[0]
    out = np.full(n, np.nan)
    for t in range(window - 1, n):
        y = returns[t - window + 1 : t + 1]
        x = factors[t - window + 1 : t + 1]
        design = np.column_stack([np.ones(window), x])
        coef, *_ = np.linalg.lstsq(design, y, rcond=None)
        out[t] = coef[1]  # market-factor beta (design column 1)
    return out
