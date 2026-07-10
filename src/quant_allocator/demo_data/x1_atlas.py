"""X1 tier & power atlas SAMPLER generator (gallery design §5 — not full vol. 1).

NUMERIC OUTPUT IS HELD FOR THE NUMERICS GATE. Reads the shared grid
(x_grid.build_grid) — the same cells the X2 playground renders — and reshapes
three sampler exhibits: power curves, a tier-degradation table, and a PowerGate
registry snippet in the X1 spec §2 schema.
"""

from __future__ import annotations

import math
from pathlib import Path

from quant_allocator.demo_data import x_grid
from quant_allocator.demo_data._emit import SITE_DATA_DIR, write_json

SAMPLER_IC_LEVELS = (0.02, 0.04, 0.10)  # labeled by the engine's realized IR (docket D-13).
SAMPLER_HALF_LIFE = 12.0
SAMPLER_SIZING = 0.8
DEGRADATION_T = 48


def _wilson_summary(power: float, n: int) -> dict:
    """Display-ready point +/- Wilson half-width from an emitted MC proportion."""
    z = x_grid.WILSON_Z
    denominator = 1.0 + z * z / n
    radicand = power * (1.0 - power) / n + z * z / (4.0 * n * n)
    half_width = (z / denominator) * math.sqrt(radicand)
    return {
        "n": n,
        "half_width": round(half_width, 6),
        "lo": round(max(0.0, power - half_width), 6),
        "hi": round(min(1.0, power + half_width), 6),
    }


def build(out_dir: Path = SITE_DATA_DIR) -> Path:
    payloads, thresholds, meta = x_grid.build_grid()
    realized_ir_by_ic = meta["realized_ir_by_ic"]

    power_curves = []
    for ic in SAMPLER_IC_LEVELS:
        ols_cells = [
            payloads[(ic, SAMPLER_HALF_LIFE, SAMPLER_SIZING, T, "R")].analytics["alpha_ols"]
            for T in x_grid.T_GRID
        ]
        # X1 spec §3.2: posterior scored at R/E only; the sampler labels it against
        # the R-tier curve (OLS vs shrinkage posterior on the same tier).
        posterior_cells = [
            payloads[(ic, SAMPLER_HALF_LIFE, SAMPLER_SIZING, T, "R")].analytics["alpha_posterior"]
            for T in x_grid.T_GRID
        ]
        ols = [round(cell["power"], 4) for cell in ols_cells]
        posterior = [round(cell["power"], 4) for cell in posterior_cells]
        power_curves.append(
            {
                "ic": ic,
                # Engine's realized IR for this IC at the sampler slice (D-13): the
                # measured effect size the OLS/posterior curves are detecting.
                "realized_ir": round(realized_ir_by_ic[ic], 3),
                "T": list(x_grid.T_GRID),
                "ols_ttest": ols,
                "ols_ttest_wilson": [_wilson_summary(power, meta["n_reps"]) for power in ols],
                "posterior": posterior,
                "posterior_wilson": [_wilson_summary(power, meta["n_reps"]) for power in posterior],
            }
        )

    def _alpha_cell(tier):
        return payloads[
            (x_grid.PINNED_EFFECT_IC, SAMPLER_HALF_LIFE, SAMPLER_SIZING, DEGRADATION_T, tier)
        ].analytics["alpha_ols"]

    p_cell = payloads[
        (x_grid.PINNED_EFFECT_IC, SAMPLER_HALF_LIFE, SAMPLER_SIZING, DEGRADATION_T, "P")
    ].analytics
    alpha_r = _alpha_cell("R")
    alpha_e = _alpha_cell("E")
    hit_rate = p_cell["hit_rate"]
    sizing_skill = p_cell["sizing_slope"]

    def _degradation_row(cell, *, include_rmse=False):
        power = round(cell["power"], 4)
        row = {"power": power, "wilson": _wilson_summary(power, meta["n_reps"])}
        if include_rmse:
            row["rmse"] = round(cell["rmse"], 6)
        return row

    degradation_table = {
        "T": DEGRADATION_T,
        "ic": x_grid.PINNED_EFFECT_IC,
        "alpha_estimation": {
            "R": _degradation_row(alpha_r, include_rmse=True),
            "E": _degradation_row(alpha_e, include_rmse=True),
        },
        "sizing_skill_P": _degradation_row(sizing_skill),
        "hit_rate_P": _degradation_row(hit_rate),
        "drift_detection": "deferred (exposure-drift detector, X1 spec §3.2 — docket D-11)",
    }

    max_months = max(x_grid.T_GRID)

    def _headline_cell(ic, tier):
        return payloads[(ic, SAMPLER_HALF_LIFE, SAMPLER_SIZING, max_months, tier)].analytics[
            "alpha_posterior"
        ]

    def _headline_result(cell):
        power = round(cell["power"], 4)
        return {"power": power, "wilson": _wilson_summary(power, meta["n_reps"])}

    e_reference = _headline_cell(x_grid.PINNED_EFFECT_IC, "E")
    r_reference = _headline_cell(x_grid.PINNED_EFFECT_IC, "R")
    r_false_attribution = _headline_cell(0.0, "R")
    headline = {
        "reference": {
            "ic": x_grid.PINNED_EFFECT_IC,
            "realized_ir": round(realized_ir_by_ic[x_grid.PINNED_EFFECT_IC], 3),
            "half_life": SAMPLER_HALF_LIFE,
            "sizing": SAMPLER_SIZING,
            "target_power": x_grid.GATE_POWER_TARGET,
            "max_months": max_months,
        },
        "e_tier": {
            **_headline_result(e_reference),
            "threshold_months": int(thresholds[("alpha_posterior", "E")]),
        },
        "r_tier": {**_headline_result(r_reference), "threshold_months": None},
        "r_tier_false_attribution": {
            **_headline_result(r_false_attribution),
            "ic": 0.0,
            "months": max_months,
        },
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
        "headline": headline,
        "power_curves": power_curves,
        "degradation_table": degradation_table,
        "registry_snippet": registry_snippet,
    }
    return write_json(out_dir / "x1_atlas.json", document)
