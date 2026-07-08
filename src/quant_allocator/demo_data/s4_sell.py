"""S4 sell-discipline generator: two named managers + the random-sell ghost -> JSON.

NUMERIC OUTPUT IS HELD FOR THE NUMERICS GATE — this JSON does not publish until
certified (cards.yaml stays 'planned'; the integration task flips it). The demo and any
future live build share the SAME pipeline (spec §6.5); only the input book differs.

One shared market (seed 8, idio_ar1 = 0.4) carries forward-predictable idio alpha; three
books share ONE manager seed (identical entry skill) and differ ONLY in exit_style:
"signal" is the disciplined seller (Larkspur — sells its lowest-conviction incumbents),
"disposition" is the flawed seller (Redgate — sells its biggest trailing winners), and
"random" is the ghost (the specificity control, spec §8.5). Demo loudness (rho = 0.4,
IC = 0.35) is teaching-scale and disclosed on the page (spec §8.3).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from quant_allocator.demo_data._emit import SITE_DATA_DIR, write_json
from quant_allocator.flagships.sell_discipline import pipeline as sd
from quant_allocator.simulator.manager import ManagerConfig, simulate_manager
from quant_allocator.simulator.market import MarketConfig, simulate_market

# Spec §8.7 pinned demo world.
MARKET_SEED = 8
S4_IDIO_AR1_DEMO = 0.4
N_ASSETS = 120                 # teaching-code universe (spec §4).
N_MONTHS = 98                  # 91 valid exit-months x 6 = 546 exits at H=6 (spec §5).
DEMO_IC = 0.35                 # teaching-scale entry skill (spec §8.3).
N_LONG = 40                    # 40-name book (spec §5).
N_SHORT = 0                    # single-sided book; the gap is weight-agnostic.
REBALANCE_FRACTION = 0.15      # round(0.15 * 40) = 6 exits/month (~72/yr, spec §5).
# NUMERICS-GATE S4-D3: manager seed authored so seed-8's three books show the clean
# stylized facts (disciplined band < 0, disposition band > 0, ghost straddles 0).
# Recovered via _scan_manager_seeds against the real pipeline at reps=500, seed=7.
# Committed headline: disciplined -372 bp [-532, -212] n=546, disposition +222 bp
# [+42, +390] n=500, ghost +28 bp [-149, +201] n=501.
MANAGER_SEED = 11

# FICTIONAL fund names (repo rule: no real manager names; the site banner discloses).
# Authored constants (spec §8.8); the ghost is the random-sell counterfactual, unnamed.
_MANAGERS = (
    {"role": "disciplined", "name": "Larkspur Ridge Partners", "exit_style": "signal"},
    {"role": "disposition", "name": "Redgate Harbor Capital", "exit_style": "disposition"},
    {"role": "ghost", "name": "Random-sell ghost", "exit_style": "random"},
)


def _simulate(exit_style: str):
    market = simulate_market(MarketConfig(
        n_assets=N_ASSETS, n_months=N_MONTHS, seed=MARKET_SEED, idio_ar1=S4_IDIO_AR1_DEMO))
    history = simulate_manager(market, ManagerConfig(
        n_long=N_LONG, n_short=N_SHORT, information_coefficient=DEMO_IC,
        rebalance_fraction=REBALANCE_FRACTION, seed=MANAGER_SEED, exit_style=exit_style))
    return market, history


def _truncate(res, horizon: int) -> sd.GapResult:
    # Reuse the max-horizon exit set; slice the curve to `horizon` (constant n, spec §5).
    curve_matrix = res.per_exit_curve[:, :horizon]
    per_exit_gaps = curve_matrix[:, horizon - 1]
    return sd.GapResult(
        n_exits=res.n_exits, horizon=horizon, gap=float(per_exit_gaps.mean()),
        per_exit_gaps=per_exit_gaps, exit_months=res.exit_months,
        curve=curve_matrix.mean(axis=0), per_exit_curve=curve_matrix)


def _trend(res_max, periods: list[str]) -> dict:
    headline = _truncate(res_max, sd.S4_HORIZON_MONTHS)
    years = np.array([periods[m][:4] for m in headline.exit_months])
    quarters = np.array([
        f"{periods[m][:4]}Q{(int(periods[m][5:7]) - 1) // 3 + 1}"
        for m in headline.exit_months])
    yearly = sd.trend_buckets(headline.per_exit_gaps, headline.exit_months, years)
    quarterly = sd.trend_buckets(headline.per_exit_gaps, headline.exit_months, quarters)
    per_bucket = float(np.mean([b.n_exits for b in quarterly]))
    worst_se = max(b.se for b in quarterly)
    return {
        "yearly": [{"label": b.label, "n_exits": b.n_exits, "gap": b.gap,
                    "ci_lo": b.ci_lo, "ci_hi": b.ci_hi, "sufficient": b.sufficient}
                   for b in yearly],
        "quarterly_refused": all(not b.sufficient for b in quarterly),
        "quarterly_exits_per_bucket": per_bucket,
        "quarterly_se_bp": worst_se * 1e4,          # basis points for the refusal copy
        "min_exits_bucket": sd.S4_MIN_EXITS_BUCKET,
    }


def _manager_payload(spec: dict) -> dict:
    market, history = _simulate(spec["exit_style"])
    exits = sd.extract_exits(history.weights)
    holdings = sd.holdings_by_month(history.weights)
    # Fix the exit cohort at the MAX horizon so n is constant across the slider.
    res_max = sd.counterfactual_gap(
        market.idio_returns, holdings, exits, horizon=sd.S4_MAX_HORIZON_MONTHS)

    horizons = []
    for h in range(1, sd.S4_MAX_HORIZON_MONTHS + 1):
        res_h = _truncate(res_max, h)
        b = sd.gap_band(res_h)
        horizons.append({
            "horizon": h, "n_exits": res_h.n_exits, "gap": res_h.gap,
            "ci_lo": b.ci_lo, "ci_hi": b.ci_hi, "se": b.se})

    headline = horizons[sd.S4_HORIZON_MONTHS - 1]
    headline_band = sd.gap_band(_truncate(res_max, sd.S4_HORIZON_MONTHS))
    periods = [str(p) for p in market.factor_returns.index]
    return {
        "role": spec["role"],
        "name": spec["name"],
        "exit_style": spec["exit_style"],
        "n_exits": res_max.n_exits,
        "verdict_chip": sd.verdict_chip(headline_band),
        "headline": {
            "gap": headline["gap"], "ci_lo": headline["ci_lo"], "ci_hi": headline["ci_hi"],
            "se": headline_band.se, "design_effect": headline_band.design_effect,
            "intra_cohort_rho": headline_band.intra_cohort_rho,
            "events_per_cohort": headline_band.events_per_cohort,
            "min_detectable_gap": headline_band.min_detectable_gap,
            "gated": headline_band.gated},
        "horizons": horizons,
        "curve": [{"horizon": h + 1, "point": pt, "lo": lo, "hi": hi}
                  for h, (pt, lo, hi) in enumerate(
                      sd.curve_band(_truncate(res_max, sd.S4_HORIZON_MONTHS)))],
        "trend": _trend(res_max, periods),
    }


def build(out_dir: Path = SITE_DATA_DIR) -> Path:
    managers = [_manager_payload(spec) for spec in _MANAGERS]
    named = [m for m in managers if m["role"] != "ghost"]
    gaps = np.array([m["headline"]["gap"] for m in named])
    ses = np.array([m["headline"]["se"] for m in named])
    shrunk = sd.roster_shrink(gaps, ses)
    roster = [
        {"name": m["name"], "raw_gap": m["headline"]["gap"],
         "shrunk_gap": float(shrunk.posterior_alpha[i]),
         "shrunk_sd": float(shrunk.posterior_sd[i])}
        for i, m in enumerate(named)]

    payload = {
        "meta": {
            "generator": "s4_sell",
            "market_seed": MARKET_SEED,
            "manager_seed": MANAGER_SEED,
            "idio_ar1": S4_IDIO_AR1_DEMO,
            "information_coefficient": DEMO_IC,
            "months": N_MONTHS,
            "book_size": N_LONG,
            "exits_per_month": round(REBALANCE_FRACTION * N_LONG),
            "horizon_months": sd.S4_HORIZON_MONTHS,
            "max_horizon_months": sd.S4_MAX_HORIZON_MONTHS,
            "min_exits_gap": sd.S4_MIN_EXITS_GAP,
            "bootstrap_reps": sd.S4_BOOTSTRAP_REPS,
        },
        "managers": managers,
        "roster": roster,
    }
    return write_json(out_dir / "s4_sell.json", payload)


def _scan_manager_seeds(seeds=range(0, 200)) -> None:
    # Recovery helper (HELD-FOR-GATE): print manager seeds whose seed-8 world shows the
    # clean stylized facts — disciplined band < 0, disposition band > 0, ghost straddles 0.
    original_seed = MANAGER_SEED
    try:
        for seed in seeds:
            globals()["MANAGER_SEED"] = seed
            rows = {}
            for spec in _MANAGERS:
                market, history = _simulate(spec["exit_style"])
                exits = sd.extract_exits(history.weights)
                holdings = sd.holdings_by_month(history.weights)
                res = sd.counterfactual_gap(
                    market.idio_returns, holdings, exits, horizon=sd.S4_HORIZON_MONTHS)
                rows[spec["role"]] = sd.gap_band(res, reps=500, seed=7)
            disc, dispo, ghost = rows["disciplined"], rows["disposition"], rows["ghost"]
            if disc.ci_hi < 0 and dispo.ci_lo > 0 and ghost.ci_lo < 0 < ghost.ci_hi:
                print(f"seed {seed}: disc_hi={disc.ci_hi:.4f} dispo_lo={dispo.ci_lo:.4f} "
                      f"ghost=({ghost.ci_lo:.4f},{ghost.ci_hi:.4f})")
    finally:
        globals()["MANAGER_SEED"] = original_seed
