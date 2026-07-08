"""S5 §3 short-book quality: decompose a short sleeve into hedge vs alpha and
score it. Pure functions over (weights, betas, factor_returns, idio_returns);
no rendering, no I/O (S2 convention).

The decomposition is a tier-P IDENTITY, not a regression (§3.3): given positions
and a factor model, the split of the sleeve's P&L follows exactly. The interval
on the alpha component is the S2 tear-sheet machinery (HAC + block bootstrap,
widen-to-looser) — imported, never reimplemented (§8 ruling 5) — and the
short-side hit rate is the X1 month-clustered kernel (§3.5, shared-grid ruling).

Numeric outputs feed a demo generator HELD FOR THE NUMERICS GATE.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from quant_allocator.demo_data.x_metrics import Estimate, hit_rate
from quant_allocator.flagships.tearsheet.pipeline import (
    BOOT_REPS,
    alpha_interval,
    regress,
)

# NUMERICS-GATE (§8 ruling 1): flat general-collateral demo borrow fee. The 0-5%/yr
# dial makes it adjustable (Dietvorst); live builds use per-name fees where disclosed.
BORROW_COST_ANNUAL = 0.02
# NUMERICS-GATE (§8 ruling 7): hedge-share threshold above which the fee-implication
# line renders (when the alpha verdict is "no detectable").
HEDGE_SHARE_HIGH = 0.75
# NUMERICS-GATE (§8 ruling 8): interim ~780-independent-trade power line for a 55%-vs-50%
# hit rate at 80% power; replaced by the §6.3 gate-2 curves from the X1 registry.
SHORT_TRADE_GATE = 780
# NUMERICS-GATE: render floor for the hit-rate statistic. Below it the trade count is too
# low to display a clustered t (the number would mislead). Sits between the 5-yr window's
# 385 trades (refuse) and the 10-yr window's 745 (render as marginal), honoring §8 ruling 2's
# mandatory T=60-refusal toggle. Distinct from SHORT_TRADE_GATE, the certification line.
SHORT_TRADE_RENDER_MIN = 500
# Alpha interval level (S2 house convention: 90% for alpha).
ALPHA_CI_LEVEL = 0.90
# Decorrelated from S2's PIPELINE_SEED (20260706) and M3's ALARM_SEED (20260707).
S5_INTERVAL_SEED = 20260711

__all__ = [
    "SleeveDecomposition",
    "ShortAlpha",
    "HitRateGate",
    "RegressionFallback",
    "decompose_short_sleeve",
    "hedge_share",
    "borrow_adjusted_alpha",
    "short_hit_rate",
    "short_trade_count",
    "hit_rate_gate",
    "regression_fallback",
    "verdict_chip",
    "BORROW_COST_ANNUAL",
    "HEDGE_SHARE_HIGH",
    "SHORT_TRADE_GATE",
    "SHORT_TRADE_RENDER_MIN",
    "ALPHA_CI_LEVEL",
]

VERDICT_CALIBRATED = "Short alpha, calibrated"
VERDICT_NONE = "No detectable short alpha net of borrow"


@dataclass(frozen=True)
class SleeveDecomposition:
    hedge_pnl: np.ndarray       # (T,) x_t . f_t
    alpha_pnl: np.ndarray       # (T,) sum_i w^-_i eps_i
    sleeve_pnl: np.ndarray      # (T,) hedge + alpha (== short_w . asset_returns, exactly)
    exposure_path: np.ndarray   # (T, F) measured short-sleeve factor exposures x_t = B' w^-
    short_gross: np.ndarray     # (T,) sum_i |w^-_i|


@dataclass(frozen=True)
class ShortAlpha:
    gross_annual: float
    gross_ci: tuple[float, float]
    borrow_drag_annual: float
    net_annual: float
    net_ci: tuple[float, float]
    calibrated: bool            # net interval excludes zero from above (§3.6)


@dataclass(frozen=True)
class HitRateGate:
    hit_rate: float
    hit_t: float
    trades: int
    gate: int
    renders: bool


@dataclass(frozen=True)
class RegressionFallback:
    alpha_annual: float
    ci: tuple[float, float]
    r2: float
    crosses_zero: bool


def decompose_short_sleeve(weights, betas, factor_returns, idio_returns) -> SleeveDecomposition:
    # §3.3: r^S = x'f + sum_i w^-_i eps_i, with x = B' w^-. An exact identity at tier P.
    weights = np.asarray(weights, dtype=float)
    betas = np.asarray(betas, dtype=float)
    factor_returns = np.asarray(factor_returns, dtype=float)
    idio_returns = np.asarray(idio_returns, dtype=float)
    short_w = np.minimum(weights, 0.0)
    exposure_path = short_w @ betas                       # (T, F)
    hedge_pnl = (exposure_path * factor_returns).sum(axis=1)
    alpha_pnl = (short_w * idio_returns).sum(axis=1)
    sleeve_pnl = hedge_pnl + alpha_pnl
    short_gross = np.abs(short_w).sum(axis=1)
    return SleeveDecomposition(
        hedge_pnl=hedge_pnl, alpha_pnl=alpha_pnl, sleeve_pnl=sleeve_pnl,
        exposure_path=exposure_path, short_gross=short_gross,
    )


def hedge_share(decomp: SleeveDecomposition) -> float:
    # §3.3: HS = 1 - Var(alpha) / Var(sleeve). Descriptive; carries no significance claim.
    return 1.0 - float(np.var(decomp.alpha_pnl, ddof=1) / np.var(decomp.sleeve_pnl, ddof=1))


def borrow_adjusted_alpha(
    alpha_pnl, borrow_fee_annual, short_gross, *,
    level=ALPHA_CI_LEVEL, seed=S5_INTERVAL_SEED, n_boot=BOOT_REPS,
) -> ShortAlpha:
    # §3.3 / §8 ruling 5: gross short alpha is 12 x mean(alpha component); its interval is
    # the S2 HAC + block-bootstrap CI (widen-to-looser) applied to the alpha series via an
    # intercept-only regression. The borrow drag is a deterministic level shift, not a
    # regression term (a known cost, not a priced risk).
    alpha_pnl = np.asarray(alpha_pnl, dtype=float)
    t = len(alpha_pnl)
    fit = regress(alpha_pnl, np.empty((t, 0)), ())      # intercept-only: alpha_monthly = mean
    stats = alpha_interval(fit, level=level, seed=seed, n_boot=n_boot)
    drag = float(borrow_fee_annual) * float(np.mean(short_gross))
    net = stats.alpha_annual - drag
    net_ci = (stats.ci[0] - drag, stats.ci[1] - drag)
    return ShortAlpha(
        gross_annual=stats.alpha_annual, gross_ci=stats.ci, borrow_drag_annual=drag,
        net_annual=net, net_ci=net_ci, calibrated=bool(net_ci[0] > 0.0),
    )


def short_hit_rate(weights, asset_returns) -> Estimate:
    # §3.5: active batting average of the short sleeve, month-clustered vs 50%. The active
    # contribution g = w^- (r - r_bar_month) is exactly the X1 shared-grid input (RULING 5).
    weights = np.asarray(weights, dtype=float)
    asset_returns = np.asarray(asset_returns, dtype=float)
    short_w = np.minimum(weights, 0.0)
    hedged = asset_returns - asset_returns.mean(axis=1, keepdims=True)
    return hit_rate(short_w * hedged, None)


def short_trade_count(n_short: int, turnover: float, months: int) -> int:
    # §3.5: initial book + monthly replacements x window (X1 independent-trade convention).
    return int(n_short + round(turnover * n_short) * months)


def hit_rate_gate(weights, asset_returns, *, n_short, turnover, months) -> HitRateGate:
    est = short_hit_rate(weights, asset_returns)
    trades = short_trade_count(n_short, turnover, months)
    return HitRateGate(
        hit_rate=est.point, hit_t=est.tstat, trades=trades, gate=SHORT_TRADE_GATE,
        renders=bool(trades >= SHORT_TRADE_RENDER_MIN),
    )


def regression_fallback(
    sleeve_pnl, factor_returns, factor_names, *, level=ALPHA_CI_LEVEL, seed=S5_INTERVAL_SEED
) -> RegressionFallback:
    # §3.4 (tier R-disclosed): constant-beta factor regression on a disclosed sleeve series.
    # R^2 stands in for the hedge share; the intercept (S2 HAC + bootstrap CI) for gross alpha.
    # The constant-beta form cannot separate selection alpha from hedge timing (caveat on page).
    sleeve_pnl = np.asarray(sleeve_pnl, dtype=float)
    fit = regress(sleeve_pnl, np.asarray(factor_returns, dtype=float), tuple(factor_names))
    stats = alpha_interval(fit, level=level, seed=seed)
    r2 = 1.0 - float(np.var(fit.resid, ddof=1) / np.var(sleeve_pnl, ddof=1))
    return RegressionFallback(
        alpha_annual=stats.alpha_annual, ci=stats.ci, r2=r2, crosses_zero=stats.crosses_zero,
    )


def verdict_chip(short_alpha: ShortAlpha) -> str:
    # §3.6: the chip combines the calibrated statements, never the descriptive one alone.
    return VERDICT_CALIBRATED if short_alpha.calibrated else VERDICT_NONE
