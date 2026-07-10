"""P2 static mixed-tier book fusion demo data.

The demo runs the real simulator tier emissions and the pure P2 fusion code.  Its
measurement-error values remain provisional pending the atlas exposure rows.
"""

from __future__ import annotations

import statistics
from dataclasses import replace
from pathlib import Path

import numpy as np

from quant_allocator.demo_data._emit import SITE_DATA_DIR, write_json
from quant_allocator.flagships.book_xray import fusion
from quant_allocator.flagships.tearsheet.pipeline import regress
from quant_allocator.simulator.manager import ManagerConfig, simulate_manager
from quant_allocator.simulator.market import MarketConfig, simulate_market
from quant_allocator.simulator.tiers import OP_BUCKET_WIDTH, emit_tiers

# P2 §8.1 (NUMERICS-GATE): approved for the demo, provisional until atlas volume 1.
EXPOSURE_MEAS_SD = {"P": 0.02, "E": 0.08, "R": 0.25}
BOOK_PRIOR_MEAN = 0.20  # NUMERICS-GATE: weak common prior mean.
BOOK_PRIOR_SD = 0.50  # NUMERICS-GATE: deliberately diffuse common prior sd.
INFO_GAIN_FLOOR = 0.20  # NUMERICS-GATE: minimum all-R to all-at-least-E tightening.
DEMO_BOOK_N = 15
N_MONTHS = 60  # NUMERICS-GATE: synthetic regression horizon, not a live sample claim.
N_ASSETS = 180  # NUMERICS-GATE: gallery-scale shared market.
MARKET_SEED = 20260710
MANAGER_SEED_BASE = 202607100
R_NOISE_DIAL = (0.15, 0.25, 0.35)  # NUMERICS-GATE: skepticism states.
CREDIBLE_LEVEL = 0.90

P2_NAMES = (
    "Westermark Strategies",
    "Juniper Vale Partners",
    "Sedgewick Advisors",
    "Ravenna Point",
    "Oakhurst Capital",
    "Halstead Partners",
    "Norwood Crest",
    "Talbot Reach",
    "Ternhaven Capital",
    "Greyloft Partners",
    "Verling Capital",
    "Vantage Row",
    "Cormorant Capital",
    "Emberly Partners",
    "Dunmore Advisors",
)
P2_TIERS = (
    "R", "R", "E", "R", "P", "R", "E", "R", "R", "E", "P", "R", "E", "R", "R"
)
_RAW_CAPITAL_WEIGHTS = np.array(
    [8, 6, 9, 5, 12, 4, 7, 5, 10, 6, 11, 4, 7, 5, 6], dtype=float
)


def _config(*, r_sd: float = EXPOSURE_MEAS_SD["R"]) -> fusion.FusionConfig:
    return fusion.FusionConfig(
        exposure_meas_sd={"P": EXPOSURE_MEAS_SD["P"], "E": EXPOSURE_MEAS_SD["E"], "R": r_sd},
        prior_mean=BOOK_PRIOR_MEAN,
        prior_sd=BOOK_PRIOR_SD,
        credible_level=CREDIBLE_LEVEL,
        info_gain_floor=INFO_GAIN_FLOOR,
    )


def _book_payload(book: fusion.BookPosterior) -> dict:
    return {
        "point": book.mean,
        "sd": book.sd,
        "ci_lo": book.ci_lo,
        "ci_hi": book.ci_hi,
        "level": CREDIBLE_LEVEL,
    }


def _tier_provenance(result: fusion.FusedBook, tiers: tuple[str, ...]) -> dict[str, float]:
    return {
        tier: float(sum(result.provenance[i] for i, value in enumerate(tiers) if value == tier))
        for tier in ("R", "E", "P")
    }


def _observations() -> tuple[np.ndarray, tuple[str, ...]]:
    market = simulate_market(
        MarketConfig(n_assets=N_ASSETS, n_months=N_MONTHS, seed=MARKET_SEED)
    )
    values: list[float] = []
    sources: list[str] = []
    for index, tier in enumerate(P2_TIERS):
        history = simulate_manager(
            market,
            ManagerConfig(
                information_coefficient=0.02 + 0.004 * index,
                seed=MANAGER_SEED_BASE + index,
            ),
        )
        if tier == "R":
            fit = regress(
                history.monthly_returns.to_numpy(),
                market.factor_returns.to_numpy(),
                market.config.factor_names,
            )
            values.append(float(fit.betas[0]))
            sources.append("returns_regression_proxy")
        elif tier == "E":
            emitted = emit_tiers(market, history, coarsen_e_tier=True)
            values.append(float(emitted.exposures["beta_market"].iloc[-1]))
            sources.append("coarsened_exposure_emission")
        else:
            emitted = emit_tiers(market, history)
            values.append(float(emitted.exposures["beta_market"].iloc[-1]))
            sources.append("position_transparent_emission")
    return np.array(values), tuple(sources)


def _counterfactual(
    weights: np.ndarray,
    observations: np.ndarray,
    tiers: tuple[str, ...],
    config: fusion.FusionConfig,
    key: str,
    label: str,
) -> dict:
    result = fusion.fuse_book(weights, observations, tiers, config)
    return {"key": key, "label": label, **_book_payload(result.book)}


def build_payload() -> dict:
    weights = _RAW_CAPITAL_WEIGHTS / _RAW_CAPITAL_WEIGHTS.sum()
    observations, sources = _observations()
    config = _config()
    actual = fusion.fuse_book(weights, observations, P2_TIERS, config)
    gain = fusion.transparency_counterfactuals(weights, observations, P2_TIERS, config)
    z = statistics.NormalDist().inv_cdf(0.5 + CREDIBLE_LEVEL / 2.0)

    managers = []
    for index, posterior in enumerate(actual.manager_posteriors):
        managers.append(
            {
                "code": f"P2-{index + 1:02d}",
                "name": P2_NAMES[index],
                "tier": P2_TIERS[index],
                "capital_weight": float(weights[index]),
                "observation": float(observations[index]),
                "observation_source": sources[index],
                "posterior": {
                    "point": posterior.mean,
                    "sd": posterior.sd,
                    "ci_lo": posterior.mean - z * posterior.sd,
                    "ci_hi": posterior.mean + z * posterior.sd,
                    "level": CREDIBLE_LEVEL,
                },
                "variance_share": float(actual.provenance[index]),
            }
        )

    all_r_tiers = ("R",) * DEMO_BOOK_N
    all_e_tiers = tuple("P" if tier == "P" else "E" for tier in P2_TIERS)
    counterfactuals = [
        _counterfactual(weights, observations, all_r_tiers, config, "all_r", "All R tier"),
        _counterfactual(weights, observations, P2_TIERS, config, "actual", "Actual mix"),
        _counterfactual(
            weights, observations, all_e_tiers, config, "all_e", "Every sleeve at least E"
        ),
    ]

    dial_states = []
    for r_sd in R_NOISE_DIAL:
        dial_config = replace(
            config,
            exposure_meas_sd={"P": EXPOSURE_MEAS_SD["P"], "E": EXPOSURE_MEAS_SD["E"], "R": r_sd},
        )
        dial_result = fusion.fuse_book(weights, observations, P2_TIERS, dial_config)
        dial_states.append(
            {
                "r_sd": r_sd,
                "book": _book_payload(dial_result.book),
                "tier_provenance": _tier_provenance(dial_result, P2_TIERS),
                "observations": [float(value) for value in observations],
            }
        )

    return {
        "meta": {
            "generator": "p2_xray",
            "demo_variant": "static_fusion_demo",
            "live_filter_status": "wave_3",
            "exposure_error_source": "provisional_pending_atlas_rows",
            "r_observation_source": "synthetic_returns_regression_proxy",
            "market_seed": MARKET_SEED,
            "manager_seed_base": MANAGER_SEED_BASE,
            "n_assets": N_ASSETS,
            "n_months": N_MONTHS,
            "n_managers": DEMO_BOOK_N,
        },
        "constants": {
            "exposure_meas_sd": EXPOSURE_MEAS_SD,
            "prior_mean": BOOK_PRIOR_MEAN,
            "prior_sd": BOOK_PRIOR_SD,
            "credible_level": CREDIBLE_LEVEL,
            "info_gain_floor": INFO_GAIN_FLOOR,
            "op_bucket_width": OP_BUCKET_WIDTH,
        },
        "book": _book_payload(actual.book),
        "unfused_book": {
            "label": "un-fused — tiers not reconciled",
            "point": float(weights @ observations),
        },
        "managers": managers,
        "tier_provenance": _tier_provenance(actual, P2_TIERS),
        "counterfactuals": counterfactuals,
        "information_gate": {
            "all_r_sd": gain.all_r_sd,
            "actual_sd": gain.actual_sd,
            "all_e_sd": gain.all_e_sd,
            "actual_gain": 1.0 - gain.actual_sd / gain.all_r_sd,
            "gain": gain.gain_all_r_to_all_e,
            "floor": gain.floor,
            "renders": gain.renders,
            "fallback": "manager_by_manager_reconciliation",
        },
        "tier_monotonicity": fusion.tier_monotonicity(
            weights, observations, P2_TIERS, config
        ),
        "r_noise_dial": dial_states,
        "reconciliation_rows": [
            {
                "code": manager["code"],
                "name": manager["name"],
                "tier": manager["tier"],
                "observation": manager["observation"],
                "observation_source": manager["observation_source"],
            }
            for manager in managers
        ],
    }


def build(out_dir: Path = SITE_DATA_DIR) -> Path:
    return write_json(out_dir / "p2_xray.json", build_payload())


if __name__ == "__main__":
    print(build())
