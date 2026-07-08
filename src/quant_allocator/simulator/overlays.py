"""Composable return overlays that give a manager a posture the core generator lacks.

Two overlays live here: `WrittenPutOverlay` (a short-vol posture) and
`SmoothingOverlay` (an MA(2) return-smoothing kernel, S6 §3.7). Both are pure,
deterministic functions of a return series that draw no random numbers.

M2 spec (`docs/ideas/specs/m2-hidden-convexity-screen.md`) §4/§5: the
`WrittenPutOverlay` gives an otherwise-honest manager a short-vol posture — it
collects a steady premium and pays out on large down-moves of a reference market
factor, the return profile of a written put. The overlay is a pure, deterministic
function of a return series and a market-factor series: it draws no random numbers,
so it consumes no RNG stream (the manager/market tags 0/1/2 are untouched) and
cannot perturb the byte-identical output of any generator that does not opt in.
`overlay_notional` (kappa) = 0 recovers the input series exactly.

It is a free function, not a method on either simulator, precisely so both the
equity manager and the returns-only generator can "wear it" (M2 §5) by composing
it onto their emitted return series, without this module importing either one.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

MONTHS_PER_YEAR = 12


@dataclass(frozen=True)
class WrittenPutOverlay:
    """Short-vol overlay parameters (M2 §4).

    strike_moneyness: OTM distance of the written put below a zero market-factor
        return, in market-factor sigma units (the put pays when the factor falls
        more than this many sigma below zero).  # NUMERICS-GATE: sign/moneyness convention.
    overlay_notional: kappa, the written-put notional as a fraction of the book.
        kappa = 0 recovers the honest manager exactly.
    premium_annual: flat annual carry, used only when fair_premium is False.
    fair_premium: M2_OVERLAY_FAIR. When True (default), the premium is set so the
        overlay's realized sample-mean contribution is exactly zero: the book's
        in-sample level (Sharpe numerator) is preserved while only the left tail
        fattens.  # NUMERICS-GATE: M2_OVERLAY_FAIR default True (M2 §4).
    """

    strike_moneyness: float
    overlay_notional: float
    premium_annual: float = 0.0
    fair_premium: bool = True


def apply_written_put_overlay(
    returns: pd.Series, market_factor: pd.Series, overlay: WrittenPutOverlay
) -> pd.Series:
    """Add a written-put overlay return to a manager's return series.

    overlay_return_t = premium - kappa * max(strike - f_mkt_t, 0),
    with strike = -strike_moneyness * sigma(f_mkt). Deterministic given the inputs.
    """
    if overlay.overlay_notional < 0.0:
        raise ValueError(
            f"overlay_notional (kappa) must be >= 0, got {overlay.overlay_notional}"
        )
    if overlay.strike_moneyness < 0.0:
        raise ValueError(f"strike_moneyness must be >= 0, got {overlay.strike_moneyness}")
    if not returns.index.equals(market_factor.index):
        raise ValueError("returns and market_factor must share an index")

    sigma = float(market_factor.std())
    strike = -overlay.strike_moneyness * sigma
    payout = overlay.overlay_notional * np.maximum(strike - market_factor.to_numpy(), 0.0)

    if overlay.fair_premium:
        # Premium equal to the mean payout zeroes the overlay's realized sample-mean
        # contribution: level preserved, tail fattened (M2 §4, M2_OVERLAY_FAIR).
        premium = float(payout.mean())
    else:
        premium = overlay.premium_annual / MONTHS_PER_YEAR

    overlay_return = premium - payout
    return returns + pd.Series(overlay_return, index=returns.index, name=returns.name)


_MA_SUM_TOL = 1e-9


@dataclass(frozen=True)
class SmoothingOverlay:
    """GLM-style MA(2) return-smoothing overlay (S6 spec §3.7).

    theta: the convex smoothing kernel (theta0, theta1, theta2), theta_k >= 0 and
        sum(theta) = 1, in the SAME parameterization as the S2 unsmoothing stage
        (tearsheet/pipeline.py): theta0 is the contemporaneous, dominant weight.
        theta = (1, 0, 0) recovers the input series exactly.  # NUMERICS-GATE: S6
        stress grid theta in {identity, (0.60, 0.25, 0.15)} (S6 §8.2).

    The overlay injects the lag-1/lag-2 autocorrelation that illiquidity marking
    gives real fund series (Getmansky-Lo-Makarov) — a nuisance confound, drawing
    no random numbers, so it consumes no RNG stream. With the pre-sample returns
    treated as zero it is the exact causal inverse of the S2 de-smoother's
    _invert_ma2, so overlay and de-smoother are convention-inverses.
    """

    theta: tuple[float, float, float]


def apply_smoothing_overlay(returns: pd.Series, overlay: SmoothingOverlay) -> pd.Series:
    """Apply the MA(2) smoothing kernel to a return series.

    observed_t = theta0 * r_t + theta1 * r_{t-1} + theta2 * r_{t-2},
    with pre-sample returns (t-1, t-2 < 0) treated as zero. Deterministic; RNG-free.
    """
    theta = np.asarray(overlay.theta, dtype=float)
    if np.any(theta < 0.0):
        raise ValueError(f"smoothing theta must be non-negative, got {overlay.theta}")
    if abs(float(theta.sum()) - 1.0) > _MA_SUM_TOL:
        raise ValueError(f"smoothing theta must sum to 1, got {overlay.theta} (sum {theta.sum()})")

    r = returns.to_numpy()
    observed = theta[0] * r.copy()
    observed[1:] += theta[1] * r[:-1]
    observed[2:] += theta[2] * r[:-2]
    return pd.Series(observed, index=returns.index, name=returns.name)
