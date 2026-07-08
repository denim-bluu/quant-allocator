"""S6 §3.4 — the six FROZEN returns-only signature kernels.

Each is a pure function of a monthly net-return array r_1..r_T (spec §4 reference
implementation, verbatim). The family is hard-capped at six and its members,
windows, and order are frozen by the method-review gate (§8.1): no signature may
be added, removed, or re-windowed under the amendment rule (§3.2). Mirrors the
x_metrics.py kernel style — no simulation, no I/O, no cross-cell logic.

Numeric outputs feed a generator HELD FOR THE NUMERICS GATE.
"""

from __future__ import annotations

from collections.abc import Callable

import numpy as np

# §3.4 / §8.1 (FROZEN): the vol-of-vol window (6 months) and the rolling-IR window
# (12 months). Part of the frozen family under the amendment rule — not NUMERICS-GATE.
S6_ROLLING_WINDOWS = (6, 12)


def sig_autocorr(r: np.ndarray) -> float:
    """Lag-1 sample autocorrelation of monthly returns (§3.4 row 1)."""
    r = np.asarray(r, dtype=float)
    r = r - r.mean()
    denom = float(np.sum(r * r))
    return float(np.sum(r[:-1] * r[1:]) / denom) if denom > 0 else 0.0


def sig_vol_of_vol(r: np.ndarray, w: int = S6_ROLLING_WINDOWS[0]) -> float:
    """Coefficient of variation of the rolling w-month volatility (§3.4 row 2)."""
    r = np.asarray(r, dtype=float)
    rolling = np.array([r[i:i + w].std(ddof=1) for i in range(len(r) - w + 1)])
    return float(rolling.std(ddof=1) / rolling.mean()) if rolling.mean() > 0 else 0.0


def sig_skew(r: np.ndarray) -> float:
    """Sample skewness of monthly returns (§3.4 row 3)."""
    r = np.asarray(r, dtype=float)
    sd = r.std(ddof=1)
    if sd == 0.0:
        return 0.0
    z = (r - r.mean()) / sd
    return float(np.mean(z ** 3))


def sig_kurtosis(r: np.ndarray) -> float:
    """Excess kurtosis of monthly returns (§3.4 row 4)."""
    r = np.asarray(r, dtype=float)
    sd = r.std(ddof=1)
    if sd == 0.0:
        return 0.0
    z = (r - r.mean()) / sd
    return float(np.mean(z ** 4) - 3.0)


def sig_drawdown_shape(r: np.ndarray) -> float:
    """Max drawdown normalized by the diffusive scale sigma * sqrt(T) (§3.4 row 5)."""
    r = np.asarray(r, dtype=float)
    wealth = np.cumprod(1.0 + r)
    peak = np.maximum.accumulate(wealth)
    mdd = float((1.0 - wealth / peak).max())
    sd = r.std(ddof=1)
    return float(mdd / (sd * np.sqrt(len(r)))) if sd > 0 else 0.0


def sig_rolling_ir_slope(r: np.ndarray, w: int = S6_ROLLING_WINDOWS[1]) -> float:
    """OLS time-slope of the rolling w-month information ratio (§3.4 row 6)."""
    r = np.asarray(r, dtype=float)
    ir = np.array([
        r[i:i + w].mean() / r[i:i + w].std(ddof=1) if r[i:i + w].std(ddof=1) > 0 else 0.0
        for i in range(len(r) - w + 1)
    ])
    x = np.arange(len(ir), dtype=float)
    x -= x.mean()
    denom = float(x @ x)
    return float((x @ (ir - ir.mean())) / denom) if denom > 0 else 0.0


# FROZEN §3.4 family, in table-row order. The verdict grid and the familywise test
# iterate this dict; its keys and order are part of the registration.
SIGNATURES: dict[str, Callable[[np.ndarray], float]] = {
    "autocorr": sig_autocorr,
    "vol_of_vol": sig_vol_of_vol,
    "skew": sig_skew,
    "kurtosis": sig_kurtosis,
    "drawdown_shape": sig_drawdown_shape,
    "rolling_ir_slope": sig_rolling_ir_slope,
}
