"""The five M2 §3 convexity diagnostics as pure functions.

Each takes a (de-smoothed, by the caller) return series and a market-factor
array and returns a DiagnosticStat: a point, a circular-block-bootstrap
interval, a tally verdict, and a `played` flag. No rendering, no I/O. The
short-vol tell is a NEGATIVE coefficient throughout; a diagnostic votes
"short-vol-consistent" only when its interval clears its band in that direction.

Numeric outputs feed a demo generator HELD FOR THE NUMERICS GATE.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from quant_allocator.flagships.convexity.bootstrap import block_bootstrap_ci
from quant_allocator.flagships.tearsheet.pipeline import DrawdownHypothesis, drawdown_band

M2_BOOTSTRAP_B = 2000     # NUMERICS-GATE: bootstrap reps (M2 spec §3, default 2,000). Docket DK-1.
M2_COSKEW_BAND = 0.35     # NUMERICS-GATE: normal-calibrated coskew band ≈ sqrt(6/T) at T=48 (M2 §3.3). Docket DK-2.
M2_DDVOL_QUANTILE = 95    # NUMERICS-GATE: drawdown-vs-vol null percentile; S2 drawdown_band.p95 (M2 §3.4). Docket DK-3.
DIAG_CI_LEVEL = 0.90      # NUMERICS-GATE: diagnostic interval level (matches S2 alpha level). Docket DK-1.

_TM_STREAM = 11
_UPDOWN_STREAM = 12
_COSKEW_STREAM = 13
_DDVOL_STREAM = 14
_STRADDLE_STREAM = 15


@dataclass(frozen=True)
class DiagnosticStat:
    """One diagnostic's point, interval, tally verdict, and playability.

    verdict is exactly one of: "short-vol-consistent", "inconclusive",
    "convex-benign", "not-played". A single uniform record replaces the spec's
    five per-estimator type names because they share an identical shape and the
    composite treats them uniformly (the `name` field carries the distinction).
    """

    name: str
    point: float
    ci_lo: float
    ci_hi: float
    verdict: str
    played: bool


def _classify(ci_lo: float, ci_hi: float, *, short_vol_upper: float, benign_lower: float) -> str:
    # Interval must clear its band in the short-vol (negative) direction to vote.
    if ci_hi < short_vol_upper:
        return "short-vol-consistent"
    if ci_lo > benign_lower:
        return "convex-benign"
    return "inconclusive"


def _ols_coef(design: np.ndarray, y: np.ndarray, index: int) -> float:
    coef, *_ = np.linalg.lstsq(design, y, rcond=None)
    return float(coef[index])


def treynor_mazuy(returns, mkt, *, level=DIAG_CI_LEVEL, n_boot=M2_BOOTSTRAP_B, seed) -> DiagnosticStat:
    # M2 §3.1: r = a + b*f + gamma*f^2 + e; gamma is payoff curvature in the market.
    r = np.asarray(returns, dtype=float)
    f = np.asarray(mkt, dtype=float)

    def gamma(rr, ff):
        return _ols_coef(np.column_stack([np.ones_like(ff), ff, ff**2]), rr, 2)

    point = gamma(r, f)
    lo, hi = block_bootstrap_ci(gamma, (r, f), level=level, n_boot=n_boot, seed=seed, stream_tag=_TM_STREAM)
    return DiagnosticStat("treynor_mazuy", point, lo, hi,
                          _classify(lo, hi, short_vol_upper=0.0, benign_lower=0.0), True)


def updown_beta(returns, mkt, *, level=DIAG_CI_LEVEL, n_boot=M2_BOOTSTRAP_B, seed) -> DiagnosticStat:
    # M2 §3.2 (Henriksson–Merton): r = a + beta_down*f + gamma*max(f,0) + e,
    # beta_up = beta_down + gamma. Reported point = gamma = (beta_up - beta_down);
    # gamma < 0 is the concave short-vol profile. STATIC shape descriptor — never
    # a conditional-alpha table (do-not-build).
    r = np.asarray(returns, dtype=float)
    f = np.asarray(mkt, dtype=float)

    def gap(rr, ff):
        return _ols_coef(np.column_stack([np.ones_like(ff), ff, np.maximum(ff, 0.0)]), rr, 2)

    point = gap(r, f)
    lo, hi = block_bootstrap_ci(gap, (r, f), level=level, n_boot=n_boot, seed=seed, stream_tag=_UPDOWN_STREAM)
    return DiagnosticStat("updown_beta", point, lo, hi,
                          _classify(lo, hi, short_vol_upper=0.0, benign_lower=0.0), True)


def market_coskew(returns, mkt, *, level=DIAG_CI_LEVEL, n_boot=M2_BOOTSTRAP_B, seed) -> DiagnosticStat:
    # M2 §3.3 (Harvey–Siddique): standardized coskewness of returns with the market.
    r = np.asarray(returns, dtype=float)
    f = np.asarray(mkt, dtype=float)

    def coskew(rr, ff):
        rc = rr - rr.mean()
        fc = ff - ff.mean()
        denom = rr.std(ddof=0) * (fc.var(ddof=0))
        return float(np.mean(rc * fc**2) / denom) if denom > 0 else 0.0

    point = coskew(r, f)
    lo, hi = block_bootstrap_ci(coskew, (r, f), level=level, n_boot=n_boot, seed=seed, stream_tag=_COSKEW_STREAM)
    # Band is ±M2_COSKEW_BAND around zero (M2 §3.3): only a coskew outside it votes.
    return DiagnosticStat("market_coskew", point, lo, hi,
                          _classify(lo, hi, short_vol_upper=-M2_COSKEW_BAND, benign_lower=M2_COSKEW_BAND), True)


def drawdown_vol_signature(returns, hypothesis: DrawdownHypothesis, *, level=DIAG_CI_LEVEL,
                           n_boot=M2_BOOTSTRAP_B, seed) -> DiagnosticStat:
    # M2 §3.4: MaxDD relative to the manager's own vol, referenced to the S2
    # simulation-calibrated null. REUSES S2 drawdown_band (§3.6) read for
    # asymmetry — not a new estimator. Short-vol tell: realized MaxDD deeper than
    # the M2_DDVOL_QUANTILE (=95th) null envelope. point = realized MaxDD / median-
    # null MaxDD (>1 == deeper than the null median). Interval by block bootstrap
    # of that ratio (fixed null denominator).
    r = np.asarray(returns, dtype=float)
    band = drawdown_band(r, hypothesis, seed=seed)
    null_median_maxdd = float(band.p50.min())     # deepest point of the null median path (<= 0)
    null_q_maxdd = float(band.p95.min())          # 95th-pct deep null MaxDD (<= 0)

    def ratio(rr):
        wealth = np.cumprod(1.0 + rr)
        realized_maxdd = float((wealth / np.maximum.accumulate(wealth) - 1.0).min())
        return realized_maxdd / null_median_maxdd if null_median_maxdd < 0 else 0.0

    point = ratio(r)
    lo, hi = block_bootstrap_ci(ratio, (r,), level=level, n_boot=n_boot, seed=seed, stream_tag=_DDVOL_STREAM)
    realized_maxdd = point * null_median_maxdd
    # Gate ruling: this rung votes point-vs-null-envelope — the simulated envelope IS the
    # calibrated band for a path statistic (same logic as the M3 alarm); the bootstrap
    # interval shown is descriptive.
    if realized_maxdd < null_q_maxdd:
        verdict = "short-vol-consistent"          # deeper than the 95th-pct null
    elif realized_maxdd > null_median_maxdd:
        verdict = "convex-benign"                 # shallower than the null median
    else:
        verdict = "inconclusive"
    return DiagnosticStat("drawdown_vol", point, lo, hi, verdict, True)


def straddle_loading(returns, ptfs, *, level=DIAG_CI_LEVEL, n_boot=M2_BOOTSTRAP_B, seed) -> DiagnosticStat:
    # M2 §3.5 (Fung–Hsieh): loading on the PTFS straddle factor; negative == short
    # the lookback straddle. Optional rung: unplayed when the external series is
    # absent (the demo never fabricates one).
    if ptfs is None:
        return DiagnosticStat("straddle_loading", float("nan"), float("nan"), float("nan"),
                              "not-played", False)
    r = np.asarray(returns, dtype=float)
    p = np.asarray(ptfs, dtype=float)

    def loading(rr, pp):
        return _ols_coef(np.column_stack([np.ones_like(pp), pp]), rr, 1)

    point = loading(r, p)
    lo, hi = block_bootstrap_ci(loading, (r, p), level=level, n_boot=n_boot, seed=seed, stream_tag=_STRADDLE_STREAM)
    return DiagnosticStat("straddle_loading", point, lo, hi,
                          _classify(lo, hi, short_vol_upper=0.0, benign_lower=0.0), True)
