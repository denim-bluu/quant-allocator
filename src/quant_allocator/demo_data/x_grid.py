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
# c7: Fama-MacBeth sizing_slope (RULING 7) on top of c6's equal-weight-
# counterfactual trade-metric contributions (RULING 5) and plain clustered
# hit-rate SE (RULING 6). The cache stores computed AnalyticStats, so
# engine/kernel changes must invalidate it.
CODE_VERSION = "c7"
RUNTIME_BUDGET_SECONDS = 3000  # 50 min: margin under the one-hour ceiling (X2 spec §7).
WILSON_Z = 1.96  # X1 spec §3.3 / §8.4: Wilson 95% interval on a MC proportion.
# X1 spec §4.2: size within 5% +/- 1.5pp systematic; the cell's Wilson HW covers MC
# noise on top (at N_REPS=500 the HW alone is ~1.9pp, so a bare 1.5pp gate would
# false-fail ~12% of IC=0 cells).
SIZE_TOL_SYSTEMATIC = 0.015
# GATE RULED 2026-07-07 (two-tier size bands): EXACT tests (alpha_ols — both the R
# estimated-beta and E/P pinned variants) keep the tight SIZE_TOL_SYSTEMATIC band.
# APPROXIMATE tests (sharpe Lo-SE, month-clustered hit_rate, pooled sizing_slope)
# get this wide implementation-sanity band: deviations inside it are FINDINGS the
# IC=0 column displays (e.g. Lo-SE under-coverage at hl=3 is real content);
# deviations outside it are bugs.
SIZE_TOL_APPROX = 0.05
# Analytics whose detection rule is an exact size-controlled test at IC=0.
_EXACT_SIZE_ANALYTICS = ("alpha_ols",)
# GATE RULED 2026-07-07 (posterior tripwire): alpha_posterior is EXEMPT from the 5%
# size band — an informative-prior decision rule is not a size-controlled
# frequentist test; its IC=0 rate is atlas CONTENT (the false-attribution price of
# borrowing strength). The invariant keeps only a degeneracy tripwire:
# 0 = collapsed prior (the old same-config-clone bug), >= this bound = runaway prior.
POSTERIOR_SIZE_TRIPWIRE = 0.25
_FACTOR_COLS = ("beta_market", "beta_size", "beta_value", "beta_momentum")
_CACHE_DIR = Path(__file__).resolve().parents[3] / "site" / "_grid_cache"

GATE_POWER_TARGET = 0.80  # X1 spec §3.4: threshold = smallest gate quantity with power >= 0.80.
ROBUST_POWER = 0.80  # NUMERICS-GATE (docket D-3): provisional VerdictChip band, "per Sweep C".
NOISE_POWER = 0.50  # NUMERICS-GATE (docket D-3): provisional VerdictChip band, "per Sweep C".
# GATE RULED 2026-07-07 (docket D-13): PINNED_EFFECT_IC=0.04 kept — engine-measured
# realized IR 0.65 (ref slice), nearest grid point to the spec's IR-0.5 target
# (X1 §3.4). The reference cell is (IC=0.04, half-life=12, sizing=0.8).
# gate 2026-07-07: all-inf frequentist thresholds at this reference effect are
# CERTIFIED as content — only the shrinkage posterior at E-tier reaches 80% power
# within T<=120 at the reference effect — the atlas headline.
PINNED_EFFECT_IC = 0.04
REF_HALF_LIFE = 12.0
REF_SIZING = 0.8
GATE_UNITS = {
    "alpha_ols": "months",
    "alpha_posterior": "months",
    "sharpe": "months",
    "hit_rate": "independent_trades",
    "sizing_slope": "independent_trades",
}
_RETURNS_METRICS = ("alpha_ols", "alpha_posterior", "sharpe")
_TRADE_METRICS = ("hit_rate", "sizing_slope")


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


@dataclass(frozen=True)
class EstimatorArrays:
    # Per-rep alpha estimates for one (config, T, estimator), kept out of run_config
    # so build_grid can pool them across the IC axis for the posterior cohort.
    point: np.ndarray
    se: np.ndarray
    true: np.ndarray


@dataclass(frozen=True)
class ConfigResult:
    # One config's full contribution to the grid: its T x tier CellStats, the
    # per-(T, estimator) estimate arrays the posterior pools over, and the config's
    # realized IR (median over reps at T_MAX) used to label the atlas curves.
    cells: list[CellStats]
    estimates: dict[int, dict[str, EstimatorArrays]]
    realized_ir: float


# The posterior is scored at R (OLS inputs) and E (pinned inputs) only — X1 §3.2.
_POSTERIOR_ESTIMATOR = {"R": "ols", "E": "pinned"}


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
    # GATE RULED 2026-07-07 (RULING 5): BOTH trade metrics (hit_rate, sizing_slope)
    # score EQUAL-WEIGHT-COUNTERFACTUAL contributions w*(r - r_bar_month), where
    # r_bar_month is the universe cross-sectional mean. X1 spec §3.2's own sizing
    # wording is "slope vs an equal-weight counterfactual" — w·(r − r̄) IS that
    # counterfactual; for hit rate it is the standard active batting average ("did
    # the pick beat the month's equal-weight market"), and it zeroes the net-long
    # drift bias at IC=0 by construction (measured bias t ≈ +9 under the raw null).
    # Raw w*r contributions stay available to any other consumer via
    # weights/asset_returns; only the trade-metric input is hedged.
    hedged_returns = asset_returns - asset_returns.mean(axis=1, keepdims=True)
    active_contributions = weights * hedged_returns
    sizes = np.abs(weights)
    return returns, true_alpha, factors, betas_path, active_contributions, sizes


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


def _realized_ir(true_alpha_series) -> float:
    # Annualized IR on the FULL T_MAX true-alpha series of one rep (docket D-13).
    ta = np.asarray(true_alpha_series, dtype=float)
    ann_mean = float(ta.mean()) * 12
    ann_vol = float(ta.std(ddof=1)) * np.sqrt(12.0)
    return ann_mean / ann_vol if ann_vol > 0 else 0.0


def _estimator_arrays(estimates) -> EstimatorArrays:
    return EstimatorArrays(
        point=np.array([e.point for e in estimates], dtype=float),
        se=np.array([e.se for e in estimates], dtype=float),
        true=np.array([e.true for e in estimates], dtype=float),
    )


def run_config(cfg, n_reps=N_REPS, base_seed=GRID_BASE_SEED, use_cache=True) -> ConfigResult:
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
    estimates: dict[int, dict[str, EstimatorArrays]] = {}
    for T in T_GRID:
        # Per-rep point estimates for this T-prefix, by analytic.
        ols = [x_metrics.ols_alpha(rep[0][:T], rep[2][:T], rep[1][:T].mean() * 12) for rep in reps]
        pinned = [
            x_metrics.pinned_alpha(rep[0][:T], rep[3][:T], rep[2][:T], rep[1][:T].mean() * 12)
            for rep in reps
        ]
        sharpe = [x_metrics.sharpe_lo(rep[0][:T]) for rep in reps]
        trades = _independent_trades(T)
        # Both trade metrics take the 2D (month x position) matrices: hit_rate's
        # t-test clusters by month (D-9 gate ruling 2026-07-07) and sizing_slope is
        # Fama-MacBeth over monthly cross-sections (RULING 7); the trades proxy is
        # the gate axis only.
        hit = [x_metrics.hit_rate(rep[4][:T], trades) for rep in reps]
        sizing = [x_metrics.sizing_slope(rep[5][:T], rep[4][:T]) for rep in reps]

        # Per-rep alpha estimate arrays survive out of run_config: the posterior
        # cohort (build_grid) pools these across the IC axis (X1 §3.2).
        ols_arrays = _estimator_arrays(ols)
        pinned_arrays = _estimator_arrays(pinned)
        estimates[T] = {"ols": ols_arrays, "pinned": pinned_arrays}
        # FIX 3 gate ruling — estimation error is measured against the population
        # effect (the cross-rep mean of realized window alpha), not each rep's own
        # realized window mean (which makes pinned-alpha RMSE identically 0).
        alpha_population_target = np.full(len(reps), float(ols_arrays.true.mean()))

        for tier in TIER_GRID:
            analytics: dict[str, AnalyticStats] = {}
            # Alpha OLS (R) vs pinned (E/P) — X1 §3.2 tier semantics.
            alpha_src = ols if tier == "R" else pinned
            analytics["alpha_ols"] = _aggregate(
                [e.point for e in alpha_src], alpha_population_target,
                [e.detected for e in alpha_src], float(T),
            )
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

    realized_ir = float(np.median([_realized_ir(rep[1]) for rep in reps]))
    result = ConfigResult(cells=cells, estimates=estimates, realized_ir=realized_ir)
    if use_cache:
        _CACHE_DIR.mkdir(parents=True, exist_ok=True)
        cache_path.write_bytes(pickle.dumps(result))
    return result


def run_all_configs(n_reps=N_REPS, processes=None):
    configs = base_configs()
    with mp.Pool(processes=processes) as pool:
        results = pool.map(_run_config_worker, [(c, n_reps) for c in configs])
    grid: dict[tuple, CellStats] = {}
    estimates: dict[tuple, dict] = {}
    realized_ir_by_config: dict[tuple, float] = {}
    for cfg, result in zip(configs, results):
        for cell in result.cells:
            grid[(cell.ic, cell.half_life, cell.sizing, cell.T, cell.tier)] = cell
        config_key = (cfg.ic, cfg.half_life, cfg.sizing)
        estimates[config_key] = result.estimates
        realized_ir_by_config[config_key] = result.realized_ir
    return grid, estimates, realized_ir_by_config


def _run_config_worker(args) -> ConfigResult:
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
    # Cap at the config count: >30 cores cannot parallelize beyond 30 configs.
    procs = min(processes or os.cpu_count() or 1, len(base_configs()))
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
                # Size at IC=0 (false-alarm rate, not power) for EVERY analytic
                # present in the cell — a per-analytic check, since covering only
                # alpha_ols let a miscalibrated trade-metric test (hit_rate, D-9)
                # slip through the gate. Two-tier bands + posterior tripwire per
                # the 2026-07-07 gate rulings (see SIZE_TOL_APPROX /
                # POSTERIOR_SIZE_TRIPWIRE comments).
                size_cell = cells[(0.0, half_life, sizing, T_MAX, tier)]
                for name, a in size_cell.analytics.items():
                    if name == "alpha_posterior":
                        # The upper bound carries the cell's Wilson HW like every
                        # other band here ("up to MC noise", X1 §4.3) so reduced-rep
                        # test grids don't false-trip; at N_REPS=500 the allowance
                        # is ~3pp and the tripwire stays binding.
                        if not (0.0 < a.power < POSTERIOR_SIZE_TRIPWIRE + a.wilson_hw):
                            raise AssertionError(
                                f"posterior degeneracy tripwire at IC=0: "
                                f"size={a.power:.3f} not in (0, {POSTERIOR_SIZE_TRIPWIRE} + hw) "
                                f"(hl={half_life}, sz={sizing}, tier={tier})"
                            )
                        continue
                    tol = (
                        SIZE_TOL_SYSTEMATIC
                        if name in _EXACT_SIZE_ANALYTICS
                        else SIZE_TOL_APPROX
                    )
                    if abs(a.power - 0.05) > tol + a.wilson_hw:
                        raise AssertionError(
                            f"size off 5% at IC=0: {name}={a.power:.3f} "
                            f"(tol={tol}, hl={half_life}, sz={sizing}, tier={tier})"
                        )
    # Band contains point everywhere.
    for key, cell in cells.items():
        for name, a in cell.analytics.items():
            if not (a.lo - 1e-9 <= a.point <= a.hi + 1e-9):
                raise AssertionError(f"band excludes point at {key}/{name}")


@dataclass(frozen=True)
class CellPayload:
    key: tuple
    analytics: dict[str, dict]


def verdict_for(power: float) -> str:
    # Docket D-3: provisional VerdictChip bands from measured power (X1/S2 "per Sweep C").
    if power >= ROBUST_POWER:
        return "robust"
    if power >= NOISE_POWER:
        return "shrink"
    return "noise"


def _threshold_from_curve(gate_quantities, powers) -> float:
    # X1 spec §3.4: smallest gate quantity whose power >= 0.80 (monotone step search).
    pairs = sorted(zip(gate_quantities, powers))
    for quantity, power in pairs:
        if power >= GATE_POWER_TARGET:
            return float(quantity)
    return float("inf")  # never reaches target in the measured range


def extract_thresholds(cells: dict[tuple, CellStats]) -> dict[tuple[str, str], float]:
    thresholds: dict[tuple[str, str], float] = {}
    # Returns metrics: gate quantity = T, at the pinned-effect reference cell (IC->IR 0.5).
    for metric in _RETURNS_METRICS:
        for tier in TIER_GRID:
            quantities, powers = [], []
            for T in T_GRID:
                cell = cells[(PINNED_EFFECT_IC, REF_HALF_LIFE, REF_SIZING, T, tier)]
                if metric in cell.analytics:
                    quantities.append(T)
                    powers.append(cell.analytics[metric].power)
            if quantities:
                thresholds[(metric, tier)] = _threshold_from_curve(quantities, powers)
    # Trade metrics: gate quantity = independent trades, over the reference cell's T sweep.
    for metric in _TRADE_METRICS:
        quantities, powers = [], []
        for T in T_GRID:
            cell = cells[(PINNED_EFFECT_IC, REF_HALF_LIFE, REF_SIZING, T, "P")]
            a = cell.analytics[metric]
            quantities.append(a.gate_quantity)
            powers.append(a.power)
        thresholds[(metric, "P")] = _threshold_from_curve(quantities, powers)
    return thresholds


def _actual_n_reps(cells: dict[tuple, CellStats]) -> int:
    # Report the reps actually baked into the supplied cells, not the (possibly
    # stale) n_reps argument — matters when a caller passes a pre-built `cells`
    # dict, since every AnalyticStats already carries its true sample size.
    first_cell = next(iter(cells.values()))
    return next(iter(first_cell.analytics.values())).n_reps


def _compute_posterior_cells(estimates) -> dict[tuple, AnalyticStats]:
    # FIX 2: the shrinkage posterior pools the cohort ACROSS THE IC AXIS at fixed
    # (half_life, sizing, T, tier) — 5 ICs x N_REPS heterogeneous managers shrunk
    # together in ONE group — so shrinkage is non-degenerate (pooling same-config
    # clones collapsed the posterior sd to 0, forcing power=1/size=0 everywhere).
    # Each cell then keeps only its own IC's reps: points = that IC's shrunk
    # posterior means, detect = its own prob_positive > 0.95. gate ruling: an
    # IntervalStat labeled "posterior alpha" carries the SHRUNK posterior means.
    posterior: dict[tuple, AnalyticStats] = {}
    for half_life in HALF_LIFE_GRID:
        for sizing in SIZING_GRID:
            for T in T_GRID:
                for tier, estimator in _POSTERIOR_ESTIMATOR.items():
                    per_ic = [
                        estimates[(ic, half_life, sizing)][T][estimator] for ic in IC_GRID
                    ]
                    all_points = np.concatenate([a.point for a in per_ic])
                    all_ses = np.concatenate([a.se for a in per_ic])
                    shrunk = shrink_alphas(
                        all_points, all_ses, np.zeros(len(all_points), dtype=int)
                    )
                    detect_all = shrunk.prob_positive > 0.95
                    start = 0
                    for ic, arrays in zip(IC_GRID, per_ic):
                        length = len(arrays.point)
                        window = slice(start, start + length)
                        start += length
                        # Population effect target, matching the alpha_ols RMSE rule.
                        population_target = np.full(length, float(arrays.true.mean()))
                        posterior[(ic, half_life, sizing, T, tier)] = _aggregate(
                            shrunk.posterior_alpha[window],
                            population_target,
                            detect_all[window],
                            float(T),
                        )
    return posterior


def _inject_posterior(cells, estimates) -> None:
    for key, stats in _compute_posterior_cells(estimates).items():
        cells[key].analytics["alpha_posterior"] = stats


def _ref_realized_ir(realized_ir_by_config) -> dict[float, float]:
    # Realized IR at the reference (half_life, sizing) slice, keyed by IC — labels
    # the X1 atlas exhibit-1 power curves (docket D-13).
    if not realized_ir_by_config:
        return {}
    return {
        ic: realized_ir_by_config[(ic, REF_HALF_LIFE, REF_SIZING)]
        for ic in IC_GRID
        if (ic, REF_HALF_LIFE, REF_SIZING) in realized_ir_by_config
    }


def build_grid(cells=None, estimates=None, realized_ir_by_config=None, n_reps=N_REPS):
    if cells is None:
        cells, estimates, realized_ir_by_config = run_all_configs(n_reps=n_reps)
    if estimates is not None:
        # Posterior is computed here (not in run_config) so the cohort can pool
        # across every config's per-rep estimates once all configs have loaded.
        _inject_posterior(cells, estimates)
    assert_grid_invariants(cells)
    thresholds = extract_thresholds(cells)
    payloads: dict[tuple, CellPayload] = {}
    for key, cell in cells.items():
        rendered: dict[str, dict] = {}
        for name, a in cell.analytics.items():
            threshold = thresholds.get((name, cell.tier), float("inf"))
            gate_state = "closed" if a.gate_quantity < threshold else "open"
            rendered[name] = {
                "point": a.point,
                "lo": a.lo,
                "hi": a.hi,
                "verdict": verdict_for(a.power),
                "gate_state": gate_state,
                "threshold": threshold,
                "gate_quantity": a.gate_quantity,
                "units": GATE_UNITS[name],
                "wilson_hw": a.wilson_hw,
                "power": a.power,
                "rmse": a.rmse,
            }
        payloads[key] = CellPayload(key=key, analytics=rendered)
    run_meta = {
        "seed": GRID_BASE_SEED,
        "n_reps": _actual_n_reps(cells),
        "code_version": CODE_VERSION,
        "realized_ir_by_ic": _ref_realized_ir(realized_ir_by_config),
    }
    return payloads, thresholds, run_meta
