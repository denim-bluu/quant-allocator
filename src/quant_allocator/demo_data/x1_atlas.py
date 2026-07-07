"""X1 tier & power atlas SAMPLER generator (gallery design §5 — not full vol. 1).

NUMERIC OUTPUT IS HELD FOR THE NUMERICS GATE. Reads the shared grid
(x_grid.build_grid) — the same cells the X2 playground renders — and reshapes
three sampler exhibits: power curves, a tier-degradation table, and a PowerGate
registry snippet in the X1 spec §2 schema.
"""

from __future__ import annotations

from pathlib import Path

from quant_allocator.demo_data import x_grid
from quant_allocator.demo_data._emit import SITE_DATA_DIR, write_json

SAMPLER_IC_LEVELS = (0.02, 0.04, 0.10)  # labeled by measured IR (docket D-13).
SAMPLER_HALF_LIFE = 12.0
SAMPLER_SIZING = 0.8
DEGRADATION_T = 48


def _measured_ir(payloads, ic) -> float:
    # Mean true-alpha IR proxy at the longest T: true annualized alpha / its dispersion.
    cell = payloads[(ic, SAMPLER_HALF_LIFE, SAMPLER_SIZING, x_grid.T_MAX, "E")].analytics["alpha_ols"]
    band = (cell["hi"] - cell["lo"]) / 2.0
    return float(cell["point"] / band) if band > 0 else 0.0


def build(out_dir: Path = SITE_DATA_DIR) -> Path:
    payloads, thresholds, meta = x_grid.build_grid()

    power_curves = []
    for ic in SAMPLER_IC_LEVELS:
        ols = [
            payloads[(ic, SAMPLER_HALF_LIFE, SAMPLER_SIZING, T, "R")].analytics["alpha_ols"]["power"]
            for T in x_grid.T_GRID
        ]
        # X1 spec §3.2: posterior scored at R/E only; the sampler labels it against
        # the R-tier curve (OLS vs shrinkage posterior on the same tier).
        posterior = [
            payloads[(ic, SAMPLER_HALF_LIFE, SAMPLER_SIZING, T, "R")].analytics["alpha_posterior"]["power"]
            for T in x_grid.T_GRID
        ]
        power_curves.append({
            "ic": ic,
            "measured_ir": round(_measured_ir(payloads, ic), 3),
            "T": list(x_grid.T_GRID),
            "ols_ttest": [round(p, 4) for p in ols],
            "posterior": [round(p, 4) for p in posterior],
        })

    def _alpha_cell(tier):
        return payloads[
            (x_grid.PINNED_EFFECT_IC, SAMPLER_HALF_LIFE, SAMPLER_SIZING, DEGRADATION_T, tier)
        ].analytics["alpha_ols"]

    p_cell = payloads[
        (x_grid.PINNED_EFFECT_IC, SAMPLER_HALF_LIFE, SAMPLER_SIZING, DEGRADATION_T, "P")
    ].analytics
    degradation_table = {
        "T": DEGRADATION_T,
        "ic": x_grid.PINNED_EFFECT_IC,
        "alpha_estimation": {
            "R": {"power": round(_alpha_cell("R")["power"], 4), "rmse": round(_alpha_cell("R")["rmse"], 6)},
            "E": {"power": round(_alpha_cell("E")["power"], 4), "rmse": round(_alpha_cell("E")["rmse"], 6)},
        },
        "sizing_skill_P": {"power": round(p_cell["sizing_slope"]["power"], 4)},
        "hit_rate_P": {"power": round(p_cell["hit_rate"]["power"], 4)},
        "drift_detection": "deferred (exposure-drift detector, X1 spec §3.2 — docket D-11)",
    }

    # Exhibit 3: registry snippet (X1 spec §2 schema) for the two most quotable gates.
    hit_threshold = thresholds.get(("hit_rate", "P"), float("inf"))
    alpha_threshold = thresholds.get(("alpha_ols", "R"), float("inf"))
    registry_snippet = {
        "version": 1,
        "run": {"seed": meta["seed"], "replications": meta["n_reps"], "atlas_volume": "sampler"},
        "metrics": {
            "hit_rate": {
                "min_tier": "P",
                "gate_quantity": "independent_trades",
                # X1 spec §2: an inf threshold ("never reaches the gate target in the
                # measured range") is not valid JSON — map to null (matches
                # x2_playground._short_payload's convention).
                "threshold": None if hit_threshold == float("inf") else hit_threshold,
                "effect": "separate hit 55% from 50%",
                "power_at_threshold": x_grid.GATE_POWER_TARGET,
                "size": 0.05,
            },
            "ols_alpha_ttest": {
                "min_tier": "R",
                "gate_quantity": "months",
                "threshold": None if alpha_threshold == float("inf") else alpha_threshold,
                "effect": "true IR 0.5",
                "power_at_threshold": x_grid.GATE_POWER_TARGET,
                "size": 0.05,
            },
        },
    }

    document = {
        "meta": {
            "generator": "x1_atlas",
            "view": "sampler",
            "seed": meta["seed"],
            "n_reps": meta["n_reps"],
        },
        "power_curves": power_curves,
        "degradation_table": degradation_table,
        "registry_snippet": registry_snippet,
    }
    return write_json(out_dir / "x1_atlas.json", document)
