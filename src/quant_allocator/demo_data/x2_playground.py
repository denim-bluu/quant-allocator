"""X2 transparency-playground generator: the full 450-cell shared grid, serialized
as short-array cell payloads at 4 significant figures (X2 spec §5).

NUMERIC OUTPUT IS HELD FOR THE NUMERICS GATE. The playground is a STRICT
SUBSET of the atlas grid (X2 spec §2) — it reads x_grid.build_grid, it never
computes a parallel grid. A cell is addressed by its dial tuple; dials snap to
the grid, never interpolate (X2 spec §3).
"""

from __future__ import annotations

from pathlib import Path

from quant_allocator.demo_data import x_grid
from quant_allocator.demo_data._emit import SITE_DATA_DIR, write_json

MAX_BYTES = 300_000  # X2 spec §5 committed-JSON budget.
SIG_FIGS = 4
# Analytic -> payload key; alpha_ols is the displayed "alpha" (X2 spec §2). The
# spec's per-cell fields are annualized alpha and Sharpe at every tier, plus hit
# rate and sizing-curve slope at P only; alpha_posterior is an X1-atlas-only
# analytic and is deliberately not surfaced on this page.
_ANALYTIC_KEYS = {
    "alpha_ols": "alpha",
    "sharpe": "sharpe",
    "hit_rate": "hit_rate",
    "sizing_slope": "sizing_slope",
}


def _cell_key(ic, half_life, sizing, T, tier) -> str:
    # Compact, sortable, snap-to-grid addressable dial tuple.
    return f"{ic:g}|{half_life:g}|{sizing:g}|{T}|{tier}"


# NUMERICS-GATE (docket D-22): the short-array cell payload order is fixed here as
# [point, lo, hi, verdict, gate_state, threshold, units, wilson_hw]. This order
# is a contract shared with the Plan D page author (interval.js reads it
# positionally) — confirm before certifying the numbers.
def _short_payload(a: dict) -> list:
    threshold = a["threshold"]
    # CRITICAL: float("inf") ("never reaches the gate target") is a valid
    # in-memory threshold but is not valid JSON — json.dumps raises on it (and
    # non-strict readers would silently accept the invalid literal `Infinity`).
    # Map it to JSON null so the page can render "no threshold reached" instead.
    threshold_out = None if threshold == float("inf") else threshold
    return [
        a["point"], a["lo"], a["hi"], a["verdict"], a["gate_state"],
        threshold_out, a["units"], a["wilson_hw"],
    ]


def build(out_dir: Path = SITE_DATA_DIR) -> Path:
    payloads, thresholds, meta = x_grid.build_grid()
    cells: dict[str, dict] = {}
    for key, payload in payloads.items():
        ic, half_life, sizing, T, tier = key
        out = {}
        for analytic, out_key in _ANALYTIC_KEYS.items():
            if analytic in payload.analytics:
                out[out_key] = _short_payload(payload.analytics[analytic])
        cells[_cell_key(ic, half_life, sizing, T, tier)] = out

    document = {
        "meta": {
            "generator": "x2_playground",
            "n_cells": len(cells),
            "n_reps": meta["n_reps"],
            "seed": meta["seed"],
            "dials": {
                "ic": list(x_grid.IC_GRID),
                "half_life": list(x_grid.HALF_LIFE_GRID),
                "sizing": list(x_grid.SIZING_GRID),
                "T": list(x_grid.T_GRID),
                "tier": list(x_grid.TIER_GRID),
            },
        },
        "cells": cells,
    }
    path = write_json(out_dir / "x2_playground.json", document, sig=SIG_FIGS)
    size = path.stat().st_size
    if size > MAX_BYTES:  # X2 spec §5: a build that exceeds the budget fails.
        raise AssertionError(f"x2_playground.json is {size} bytes > {MAX_BYTES} budget")
    return path
