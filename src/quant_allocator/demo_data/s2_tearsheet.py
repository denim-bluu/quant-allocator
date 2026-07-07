"""S2 tear-sheet generator: one synthetic manager -> full pipeline -> JSON.

NUMERIC OUTPUT IS HELD FOR THE NUMERICS GATE. The demo numbers and any
future live numbers come from the SAME pipeline code path (S2 spec §5); only the
input data differs (synthetic here). One equity L/S manager, T=48, tier R
(gallery design §5). Every statistic ships as an interval; the alt-beta chip
states its CI (S2 spec §3.5).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from quant_allocator.demo_data._emit import SITE_DATA_DIR, write_json
from quant_allocator.flagships.tearsheet import pipeline as tp
from quant_allocator.simulator.manager import ManagerConfig, simulate_manager
from quant_allocator.simulator.market import MarketConfig, simulate_market

BASE_SEED = 20260706
MANAGER_CODE = "M07"
# FICTIONAL display name (repo rule: no real manager names; banner discloses).
MANAGER_NAME = "Kestrelmoor Partners"
STRATEGY = "equity_long_short"
MANAGER_MONTHS = 48
N_ASSETS = 300
# NUMERICS-GATE D-19: demo-construction config chosen so the alt-beta chip fires and
# de-smoothed Sharpe drops (like B1's M5 seed); _scan_manager_seeds is the recovery helper.
MANAGER_IC = 0.05
MANAGER_HALF_LIFE = 6.0
MANAGER_SEED = 5
# NUMERICS-GATE D-21: RF_ANNUAL is a synthetic risk-free constant (no real rf in the demo).
RF_ANNUAL = 0.02
_FACTOR_NAMES = ("market", "size", "value", "momentum")


def _simulate_manager_07():
    market = simulate_market(
        MarketConfig(n_assets=N_ASSETS, n_months=MANAGER_MONTHS, seed=BASE_SEED)
    )
    history = simulate_manager(
        market,
        ManagerConfig(
            information_coefficient=MANAGER_IC,
            alpha_half_life_months=MANAGER_HALF_LIFE,
            seed=MANAGER_SEED,
        ),
    )
    returns = history.monthly_returns.to_numpy()
    factors = market.factor_returns.to_numpy()
    return returns, factors


def _interval_stat(point, lo, hi) -> dict:
    return {"point": float(point), "ci_lo": float(lo), "ci_hi": float(hi)}


def build(out_dir: Path = SITE_DATA_DIR) -> Path:
    returns, factors = _simulate_manager_07()
    rf = np.full(MANAGER_MONTHS, RF_ANNUAL / tp.MONTHS_PER_YEAR)
    excess = returns - rf

    # Stage 1: unsmoothing (S2 §3.1).
    unsmoothed = tp.unsmooth(returns)
    # Stage 2: factor regression on the (de-smoothed where applied) excess return.
    reg_returns = (unsmoothed.desmoothed - rf) if unsmoothed.applied else excess
    fit = tp.regress(reg_returns, factors, _FACTOR_NAMES)
    # Stage 3: Sharpe intervals, reported vs de-smoothed (S2 §3.1, §3.3).
    sharpe_reported = tp.sharpe_intervals(returns, seed=BASE_SEED)
    sharpe_desmoothed = tp.sharpe_intervals(unsmoothed.desmoothed, seed=BASE_SEED)
    alpha_stats = tp.alpha_interval(fit, seed=BASE_SEED)
    # Stage 4: MPPM beside the Sharpe (S2 §3.4).
    mppm_value = tp.mppm(returns, rf)
    # Stage 6: drawdown band under the maintained (claimed) hypothesis (S2 §3.6).
    hyp = tp.DrawdownHypothesis(
        sharpe_annual=sharpe_desmoothed.sharpe_annual,
        vol_annual=float(unsmoothed.desmoothed.std(ddof=1) * np.sqrt(tp.MONTHS_PER_YEAR)),
    )
    band = tp.drawdown_band(unsmoothed.desmoothed, hyp, seed=BASE_SEED)

    chip = "provisionally alternative beta" if alpha_stats.crosses_zero else "skill supported"

    payload = {
        "meta": {
            "generator": "s2_tearsheet",
            "manager_code": MANAGER_CODE,
            "manager_name": MANAGER_NAME,
            "strategy": STRATEGY,
            "months": MANAGER_MONTHS,
            "tier": "R",
            "rf_annual": RF_ANNUAL,
        },
        "theta": [float(x) for x in unsmoothed.theta],
        "unsmoothing": {
            "applied": unsmoothed.applied,
            "skip_reason": unsmoothed.skip_reason,
            "vol_ratio": float(unsmoothed.vol_ratio),
        },
        "statistics": {
            "sharpe_reported": _interval_stat(
                sharpe_reported.sharpe_annual, *sharpe_reported.boot_ci
            ),
            "sharpe_desmoothed": _interval_stat(
                sharpe_desmoothed.sharpe_annual, *sharpe_desmoothed.boot_ci
            ),
            "alpha": _interval_stat(alpha_stats.alpha_annual, *alpha_stats.ci),
            "mppm": {"point": float(mppm_value)},
        },
        "factor_betas": {
            name: float(beta) for name, beta in zip(_FACTOR_NAMES, fit.betas)
        },
        "alt_beta": {
            "chip": chip,
            "ci_lo": float(alpha_stats.ci[0]),
            "ci_hi": float(alpha_stats.ci[1]),
            "level": tp.ALPHA_CI_LEVEL,
        },
        "drawdown_band": {
            "realized": [float(x) for x in band.realized],
            "p50": [float(x) for x in band.p50],
            "p95": [float(x) for x in band.p95],
            "p99": [float(x) for x in band.p99],
            "breaches_p99": band.breaches_p99,
            "ar1": float(band.ar1),
        },
        "monthly_returns": [float(x) for x in returns],
    }
    return write_json(out_dir / "s2_tearsheet.json", payload)


def _scan_manager_seeds(seeds=range(0, 60)) -> None:
    # Recovery helper (see the NUMERICS-GATE note): print seeds where the alt-beta chip
    # fires (alpha 90% CI crosses zero) and the de-smoothed Sharpe stays below reported.
    for seed in seeds:
        global MANAGER_SEED  # noqa: PLW0603
        saved = MANAGER_SEED
        MANAGER_SEED = seed
        returns, factors = _simulate_manager_07()
        rf = np.full(MANAGER_MONTHS, RF_ANNUAL / tp.MONTHS_PER_YEAR)
        uns = tp.unsmooth(returns)
        reg = (uns.desmoothed - rf) if uns.applied else (returns - rf)
        fit = tp.regress(reg, factors, _FACTOR_NAMES)
        alpha = tp.alpha_interval(fit, seed=BASE_SEED)
        sr_rep = tp.sharpe_intervals(returns, seed=BASE_SEED).sharpe_annual
        sr_des = tp.sharpe_intervals(uns.desmoothed, seed=BASE_SEED).sharpe_annual
        MANAGER_SEED = saved
        if alpha.crosses_zero and sr_des <= sr_rep + 1e-9:
            print(f"seed {seed}: alt-beta fires; SR {sr_rep:.2f}->{sr_des:.2f}")
