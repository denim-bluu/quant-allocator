"""Shared Monte-Carlo grid engine for the X1 atlas and X2 playground.

ONE grid computation serves both cards (X2 spec §2: the playground is a strict
subset of the atlas grid, never a parallel computation). The 450 dial cells
collapse to 30 simulation configs: T is a prefix truncation of one T_MAX=120
manager path, and tier is three emissions of the same book. Configs run under
multiprocessing with a per-config cache. Numeric output is HELD FOR THE NUMERICS
NUMERICS GATE.
"""

from __future__ import annotations

import multiprocessing as mp
import os
import pickle
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from quant_allocator.demo_data import x_metrics
from quant_allocator.flagships.skill_ledger.empirical import shrink_alphas
from quant_allocator.simulator.manager import ManagerConfig, simulate_manager
from quant_allocator.simulator.market import MarketConfig, simulate_market
from quant_allocator.simulator.tiers import emit_tiers

GRID_BASE_SEED = 20260706
N_REPS = 500
IC_GRID = (0.0, 0.02, 0.04, 0.07, 0.10)
HALF_LIFE_GRID = (3.0, 12.0, 36.0)
SIZING_GRID = (0.0, 0.8)
T_GRID = (24, 36, 48, 60, 120)
TIER_GRID = ("R", "E", "P")
T_MAX = 120
# NUMERICS-GATE (docket D-1): N_ASSETS=120 (universe for atlas managers) is not
# spec-pinned; it sets book-selection breadth and runtime.
N_ASSETS = 120
N_LONG = 40
N_SHORT = 25
REBALANCE_FRACTION = 0.25
CODE_VERSION = "c2"
RUNTIME_BUDGET_SECONDS = 3000  # 50 min: margin under the one-hour ceiling (X2 spec §7).
WILSON_Z = 1.96  # X1 spec §3.3 / §8.4: Wilson 95% interval on a MC proportion.
# X1 spec §4.2: size within 5% +/- 1.5pp systematic; the cell's Wilson HW covers MC
# noise on top (at N_REPS=500 the HW alone is ~1.9pp, so a bare 1.5pp gate would
# false-fail ~12% of IC=0 cells).
SIZE_TOL_SYSTEMATIC = 0.015
_FACTOR_COLS = ("beta_market", "beta_size", "beta_value", "beta_momentum")
_CACHE_DIR = Path(__file__).resolve().parents[3] / "site" / "_grid_cache"


@dataclass(frozen=True)
class SimConfig:
    ic: float
    half_life: float
    sizing: float
    index: int


@dataclass(frozen=True)
class AnalyticStats:
    point: float
    lo: float
    hi: float
    power: float
    wilson_hw: float
    n_detect: int
    n_reps: int
    rmse: float
    gate_quantity: float


@dataclass(frozen=True)
class CellStats:
    ic: float
    half_life: float
    sizing: float
    T: int
    tier: str
    analytics: dict[str, AnalyticStats]


def base_configs() -> list[SimConfig]:
    configs: list[SimConfig] = []
    index = 0
    for ic in IC_GRID:
        for half_life in HALF_LIFE_GRID:
            for sizing in SIZING_GRID:
                configs.append(SimConfig(ic=ic, half_life=half_life, sizing=sizing, index=index))
                index += 1
    return configs


def _config_seed(base_seed: int, cfg_index: int, rep: int) -> int:
    # Independent bit stream per (config, rep) via SeedSequence (X1 spec §3.3).
    state = np.random.SeedSequence([base_seed, cfg_index, rep]).generate_state(1)[0]
    return int(state)


def _wilson_half_width(k: int, n: int, z: float = WILSON_Z) -> float:
    # X1 spec §8.4: Wilson 95% half-width on a MC proportion.
    if n == 0:
        return 0.0
    p = k / n
    denom = 1.0 + z**2 / n
    half = (z * np.sqrt(p * (1 - p) / n + z**2 / (4 * n**2))) / denom
    # Report the symmetric half-width around the centre (both bounds are within [0,1]).
    return float(half)


def _simulate_rep(cfg: SimConfig, seed: int):
    # NUMERICS-GATE (docket D-12): one manager path at T_MAX with an independent market
    # per rep (market and manager streams are decorrelated by stream tag; whether to
    # share one market per config is a runtime-strategy choice to confirm).
    market = simulate_market(MarketConfig(n_assets=N_ASSETS, n_months=T_MAX, seed=seed))
    history = simulate_manager(
        market,
        ManagerConfig(
            n_long=N_LONG,
            n_short=N_SHORT,
            information_coefficient=cfg.ic,
            alpha_half_life_months=cfg.half_life,
            sizing_discipline=cfg.sizing,
            rebalance_fraction=REBALANCE_FRACTION,
            seed=seed,
        ),
    )
    tiers = emit_tiers(market, history)
    returns = history.monthly_returns.to_numpy()
    true_alpha = history.true_alpha_returns.to_numpy()
    factors = market.factor_returns.to_numpy()
    betas_path = tiers.exposures[list(_FACTOR_COLS)].to_numpy()
    weights = history.weights.to_numpy()
    asset_returns = market.asset_returns.to_numpy()
    contributions = weights * asset_returns  # per position-month P&L contribution
    sizes = np.abs(weights)
    return returns, true_alpha, factors, betas_path, contributions, sizes


def _independent_trades(T: int) -> float:
    # X1 spec §3.4/§8.1: gate quantity for trade-level metrics. Independent entries
    # ~ initial book + turnover per month over T (docket D-9).
    per_month = round(REBALANCE_FRACTION * N_LONG) + round(REBALANCE_FRACTION * N_SHORT)
    return float(N_LONG + N_SHORT + per_month * T)


def _aggregate(points, trues, detects, gate_quantity) -> AnalyticStats:
    points = np.asarray(points, dtype=float)
    detects = np.asarray(detects, dtype=bool)
    n = len(points)
    k = int(detects.sum())
    power = k / n if n else 0.0
    finite_true = np.asarray(trues, dtype=float)
    valid = np.isfinite(finite_true)
    rmse = (
        float(np.sqrt(np.mean((points[valid] - finite_true[valid]) ** 2)))
        if valid.any()
        else float("nan")
    )
    return AnalyticStats(
        point=float(np.median(points)),
        lo=float(np.percentile(points, 2.5)),
        hi=float(np.percentile(points, 97.5)),
        power=power,
        wilson_hw=_wilson_half_width(k, n),
        n_detect=k,
        n_reps=n,
        rmse=rmse,
        gate_quantity=gate_quantity,
    )


def _posterior_stats(estimates, T) -> AnalyticStats:
    # S1 shrinkage posterior over the cell cohort, detect P(a>0)>0.95. gate
    # ruling: an IntervalStat labeled "posterior alpha" carries the SHRUNK posterior
    # means — reporting raw tier points under a posterior label would mislabel.
    points = np.array([e.point for e in estimates])
    ses = np.array([e.se for e in estimates])
    shrunk = shrink_alphas(points, ses, np.zeros(len(estimates), dtype=int))
    detect = shrunk.prob_positive > 0.95
    return _aggregate(
        shrunk.posterior_alpha, [e.true for e in estimates], detect, float(T)
    )


def run_config(cfg, n_reps=N_REPS, base_seed=GRID_BASE_SEED, use_cache=True) -> list[CellStats]:
    cache_path = _CACHE_DIR / (
        f"cfg{cfg.index}_ic{cfg.ic}_hl{cfg.half_life}_sd{cfg.sizing}"
        f"_seed{base_seed}_n{n_reps}_{CODE_VERSION}.pkl"
    )
    if use_cache and cache_path.exists():
        # Trusted local-only cache: this module reads only its own writes under
        # site/_grid_cache/ (gitignored), keyed by (config, seed, code-version).
        return pickle.loads(cache_path.read_bytes())

    reps = [_simulate_rep(cfg, _config_seed(base_seed, cfg.index, r)) for r in range(n_reps)]
    cells: list[CellStats] = []
    for T in T_GRID:
        # Per-rep point estimates for this T-prefix, by analytic.
        ols = [x_metrics.ols_alpha(r[:T], f[:T], ta[:T].mean() * 12) for r, ta, f in
               ((rep[0], rep[1], rep[2]) for rep in reps)]
        pinned = [
            x_metrics.pinned_alpha(rep[0][:T], rep[3][:T], rep[2][:T], rep[1][:T].mean() * 12)
            for rep in reps
        ]
        sharpe = [x_metrics.sharpe_lo(rep[0][:T]) for rep in reps]
        # X1 spec §3.2: posterior scored at R/E with the tier's own alpha estimates;
        # omitting it at P is deliberate.
        posterior_by_tier = {"R": _posterior_stats(ols, T), "E": _posterior_stats(pinned, T)}
        trades = _independent_trades(T)
        hit = [
            x_metrics.hit_rate(rep[4][:T].ravel(), trades) for rep in reps
        ]
        sizing = [x_metrics.sizing_slope(rep[5][:T].ravel(), rep[4][:T].ravel()) for rep in reps]

        for tier in TIER_GRID:
            analytics: dict[str, AnalyticStats] = {}
            # Alpha OLS (R) vs pinned (E/P) — X1 §3.2 tier semantics.
            alpha_src = ols if tier == "R" else pinned
            analytics["alpha_ols"] = _aggregate(
                [e.point for e in alpha_src], [e.true for e in alpha_src],
                [e.detected for e in alpha_src], float(T),
            )
            if tier in posterior_by_tier:
                analytics["alpha_posterior"] = posterior_by_tier[tier]
            analytics["sharpe"] = _aggregate(
                [e.point for e in sharpe], [e.true for e in sharpe],
                [e.detected for e in sharpe], float(T),
            )
            if tier == "P":
                analytics["hit_rate"] = _aggregate(
                    [e.point for e in hit], [e.true for e in hit],
                    [e.detected for e in hit], trades,
                )
                analytics["sizing_slope"] = _aggregate(
                    [e.point for e in sizing], [e.true for e in sizing],
                    [e.detected for e in sizing], trades,
                )
            cells.append(CellStats(cfg.ic, cfg.half_life, cfg.sizing, T, tier, analytics))

    if use_cache:
        _CACHE_DIR.mkdir(parents=True, exist_ok=True)
        cache_path.write_bytes(pickle.dumps(cells))
    return cells


def run_all_configs(n_reps=N_REPS, processes=None) -> dict[tuple, CellStats]:
    configs = base_configs()
    with mp.Pool(processes=processes) as pool:
        results = pool.map(_run_config_worker, [(c, n_reps) for c in configs])
    grid: dict[tuple, CellStats] = {}
    for cell_list in results:
        for cell in cell_list:
            grid[(cell.ic, cell.half_life, cell.sizing, cell.T, cell.tier)] = cell
    return grid


def _run_config_worker(args) -> list[CellStats]:
    cfg, n_reps = args
    return run_config(cfg, n_reps=n_reps, base_seed=GRID_BASE_SEED, use_cache=True)


def estimate_runtime(sample_configs=2, n_reps=N_REPS, processes=None) -> dict:
    # Measure a few configs at full reps, extrapolate to 30 configs across cores.
    configs = base_configs()[:sample_configs]
    start = time.perf_counter()
    for cfg in configs:
        run_config(cfg, n_reps=n_reps, base_seed=GRID_BASE_SEED, use_cache=False)
    elapsed = time.perf_counter() - start
    per_config = elapsed / max(1, len(configs))
    total = per_config * len(base_configs())
    procs = processes or os.cpu_count() or 1
    wall = total / procs
    return {
        "per_config_seconds": per_config,
        "projected_total_seconds": total,
        "projected_wall_seconds": wall,
        "processes": procs,
        "budget_seconds": RUNTIME_BUDGET_SECONDS,
    }


def assert_grid_invariants(cells: dict[tuple, CellStats]) -> None:
    # X1 spec §4: monotone power/width in T and IC up to MC noise; size ~5% at IC=0.
    for half_life in HALF_LIFE_GRID:
        for sizing in SIZING_GRID:
            for tier in TIER_GRID:
                # Monotone in T at the top IC (power should not fall as T grows).
                top_ic = IC_GRID[-1]
                stats_t = [cells[(top_ic, half_life, sizing, T, tier)].analytics["alpha_ols"]
                           for T in T_GRID]
                for earlier, later in zip(stats_t, stats_t[1:]):
                    # X1 spec §4.3: "up to MC noise" — quantified by the cells' own Wilson half-widths
                    if later.power < earlier.power - (earlier.wilson_hw + later.wilson_hw):
                        raise AssertionError(
                            f"power fell in T at ic={top_ic}, hl={half_life}, sz={sizing}, tier={tier}"
                        )
                # Monotone in IC at the top T.
                stats_ic = [cells[(ic, half_life, sizing, T_MAX, tier)].analytics["alpha_ols"]
                            for ic in IC_GRID]
                for earlier, later in zip(stats_ic, stats_ic[1:]):
                    # X1 spec §4.3: "up to MC noise" — quantified by the cells' own Wilson half-widths
                    if later.power < earlier.power - (earlier.wilson_hw + later.wilson_hw):
                        raise AssertionError(
                            f"power fell in IC at hl={half_life}, sz={sizing}, tier={tier}"
                        )
                # Size ~5% at IC=0 (false-alarm rate, not power).
                size_cell = cells[(0.0, half_life, sizing, T_MAX, tier)].analytics["alpha_ols"]
                size = size_cell.power
                if abs(size - 0.05) > SIZE_TOL_SYSTEMATIC + size_cell.wilson_hw:
                    raise AssertionError(
                        f"size off 5% at IC=0: {size:.3f} (hl={half_life}, sz={sizing}, tier={tier})"
                    )
    # Band contains point everywhere.
    for key, cell in cells.items():
        for name, a in cell.analytics.items():
            if not (a.lo - 1e-9 <= a.point <= a.hi + 1e-9):
                raise AssertionError(f"band excludes point at {key}/{name}")
