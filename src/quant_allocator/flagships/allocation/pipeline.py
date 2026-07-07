"""P1 §3.5-§3.7 allocation under alpha uncertainty — pure functions.

Posterior-draw resampled allocation: Michaud's resampling architecture with S1's
posterior as the input distribution. Draw an alpha vector per posterior, allocate
it under the long-only diagonal Kelly rule (§3.6), and report the 10-90 advisory
band, median anchor, and P(w=0) fund-or-not signal per manager (§3.5). band_action
applies the §3.7 Schmitt-trigger hysteresis (trigger on the 10-90 band, clear on
the inner 25-75 band). No I/O, no rendering; numpy only.

Numeric outputs feed a demo generator HELD FOR THE NUMERICS GATE. AllocationConfig
carries every §6.4 provisional constant as a named field.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class AllocationConfig:
    # NUMERICS-GATE P1_ALLOC_CAP (§6.4, §8.6): per-manager governance cap in the within-draw rule.
    alloc_cap: float = 0.20
    # NUMERICS-GATE P1_N_DRAWS (§6.4, §8.6): posterior draws behind the bands (closed-form => cheap).
    n_draws: int = 50_000
    # NUMERICS-GATE P1_BAND_PCT (§8.1): advisory-band percentiles (a decision range, not a CI).
    band_pct: tuple[float, float] = (10.0, 90.0)
    # NUMERICS-GATE P1_HYSTERESIS_BANDS (§3.7, §8.1): inner clear band for the review hysteresis.
    clear_pct: tuple[float, float] = (25.0, 75.0)
    # NUMERICS-GATE P1_SIGMA_DEMO (§6.4, §8.2): demo constant residual annual vol (isolates the
    # posterior as the sole driver of band width). Live: per-manager de-smoothed vol (S2 pipeline).
    sigma_demo: float = 0.08
    # NUMERICS-GATE P1_KELLY_FRACTION (§6.4, §8.6): fractional-Kelly ceiling; binds live gross-sizing
    # extensions only — v1's budgeted (sum-to-one) rule does not lever, so this is inert in v1.
    kelly_fraction: float = 0.5
    # A funded name is one whose anchor clears this weight (fund-or-not vs numerical dust).
    funded_eps: float = 0.005
    # Cap-and-redistribute passes: a fixed-point iteration; the bound is a safety rail, not a knob (§4).
    cap_passes: int = 50


def allocate_one_draw(
    alphas: np.ndarray, sigmas: np.ndarray, cap: float, *, cap_passes: int = 50
) -> np.ndarray:
    """§3.6 within-draw rule: w_i proportional to max(0, alpha_i) / sigma_i^2, renormalized to
    sum 1, then capped at `cap` per manager with the excess redistributed pro-rata to the uncapped
    names. Long-only (a short is a weight of zero, i.e. redeem), fully invested, diagonal risk only
    (§3.6 deliberately omits the off-diagonal of Sigma). Returns zeros if no alpha is positive."""
    alphas = np.asarray(alphas, dtype=float)
    sigmas = np.asarray(sigmas, dtype=float)
    score = np.maximum(0.0, alphas) / sigmas**2
    total = float(score.sum())
    if total == 0.0:
        return np.zeros_like(alphas)
    weights = score / total
    for _ in range(cap_passes):
        over = weights > cap
        if not over.any():
            break
        excess = float((weights[over] - cap).sum())
        weights = np.where(over, cap, weights)
        under = (~over) & (weights > 0.0)
        if not under.any():
            break
        weights = np.where(under, weights + excess * weights / weights[under].sum(), weights)
    return weights
