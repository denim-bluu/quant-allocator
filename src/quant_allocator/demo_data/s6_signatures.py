"""S6 PILOT generator: the pre-registered protocol run end-to-end on REAL
simulate_manager paths at a burned pilot seed (spec §8.4), over a BOUNDED pilot
grid (fewer cells than the confirmatory 12 + 8) so it runs in minutes.

NUMERIC OUTPUT IS HELD FOR THE NUMERICS GATE. The demo is PILOT-labeled: these
verdicts are the protocol's answer on the bounded grid, NOT the spec §4 stand-in
generator's teaching numbers (which must never appear as the verdict grid, §8.4).
The confirmatory run -- full 12 + 8 cells, fresh S6_CONFIRM_SEED, written-put
stress, the registration document -- is wave-3 scope and its outcome is unknown by
design. The signature kernels, the AUC, and the permutation test are
generator-agnostic; only the input paths change between pilot and confirmatory.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from quant_allocator.demo_data import s6_protocol as proto
from quant_allocator.demo_data import s6_signatures_kernels as kern
from quant_allocator.demo_data._emit import SITE_DATA_DIR, write_json
from quant_allocator.demo_data.x_grid import _config_seed
from quant_allocator.simulator.manager import ManagerConfig, simulate_manager
from quant_allocator.simulator.market import MarketConfig, simulate_market
from quant_allocator.simulator.overlays import SmoothingOverlay, apply_smoothing_overlay

# --- burned pilot seed (distinct from GRID_BASE_SEED and any S6_CONFIRM_SEED) ---
S6_PILOT_SEED = 20260721  # NUMERICS-GATE: pilot seeds are burned (§3.7); never reused by the confirm run.

# --- X1-identical simulator setup ---------------------------------------------
N_ASSETS = 120
N_LONG = 40
N_SHORT = 25
REBALANCE_FRACTION = 0.25

# --- bounded pilot grid (NUMERICS-GATE; fewer cells than the confirmatory 12 + 8) ---
S6_PILOT_N_PER_CLASS = 150   # confirmatory S6_N_PER_CLASS = 500
S6_PILOT_N_PERM = 2000       # confirmatory S6_N_PERM = 5000
PILOT_IC = (0.04, 0.10)      # confirmatory ic grid: (0.02, 0.04, 0.07, 0.10)
PILOT_SIZE_HALF_LIFE = 12.0  # H-SIZE nuisance hl held at 12 (confirmatory: {3, 12, 36})
PILOT_DECAY_SIZING = 0.8     # H-DECAY nuisance sizing held at 0.8 (confirmatory: {0.0, 0.8})
# Frozen contrast dials (§3.3).
SIZE_POS_SIZING, SIZE_NEG_SIZING = 0.8, 0.0
DECAY_POS_HL, DECAY_NEG_HL = 3.0, 36.0

# Frozen smoothing overlay stress grid (§8.2): identity + one moderate GLM MA(2).
SMOOTHING_GRID = (
    ("identity", (1.0, 0.0, 0.0)),
    ("smoothed", (0.60, 0.25, 0.15)),
)


# Distinct integer stream index per (contrast, ic, class) so _config_seed gives each
# manager population a decorrelated bit stream (no hash()-seeds; mirrors X1 cfg.index).
def _cell_stream_index(contrast: str, ic: float, is_positive: bool) -> int:
    base = 100 if contrast == "h_size" else 200
    ic_slot = PILOT_IC.index(ic)          # 0 or 1
    return base + ic_slot * 2 + (0 if is_positive else 1)


def _manager_config(ic: float, half_life: float, sizing: float, seed: int) -> ManagerConfig:
    return ManagerConfig(
        n_long=N_LONG, n_short=N_SHORT,
        information_coefficient=ic, alpha_half_life_months=half_life,
        sizing_discipline=sizing, rebalance_fraction=REBALANCE_FRACTION, seed=seed,
    )


def _simulate_returns(ic, half_life, sizing, stream_index) -> list[pd.Series]:
    # One monthly-return Series per rep, X1 _simulate_rep shape, reusing _config_seed verbatim.
    out: list[pd.Series] = []
    for rep in range(S6_PILOT_N_PER_CLASS):
        seed = _config_seed(S6_PILOT_SEED, stream_index, rep)
        market = simulate_market(
            MarketConfig(n_assets=N_ASSETS, n_months=proto.S6_DECISION_T, seed=seed)
        )
        history = simulate_manager(market, _manager_config(ic, half_life, sizing, seed))
        out.append(history.monthly_returns)
    return out


def _signatures_over_class(returns_series, theta, T) -> dict[str, np.ndarray]:
    # Apply the smoothing overlay (identity recovers the input), truncate to horizon T,
    # then evaluate every frozen kernel per manager. Returns signature -> (n_managers,) array.
    overlay = SmoothingOverlay(theta=theta)
    per_sig = {name: np.empty(len(returns_series)) for name in kern.SIGNATURES}
    for i, series in enumerate(returns_series):
        smoothed = apply_smoothing_overlay(series, overlay).to_numpy()[:T]
        for name, fn in kern.SIGNATURES.items():
            per_sig[name][i] = fn(smoothed)
    return per_sig


_CONTRASTS = {
    "h_size": {
        "label": "H-SIZE — sizing discipline 0.8 vs 0.0",
        "pos": {"sizing": SIZE_POS_SIZING, "half_life": PILOT_SIZE_HALF_LIFE},
        "neg": {"sizing": SIZE_NEG_SIZING, "half_life": PILOT_SIZE_HALF_LIFE},
    },
    "h_decay": {
        "label": "H-DECAY — alpha half-life 3 vs 36 (fast vs slow)",
        "pos": {"sizing": PILOT_DECAY_SIZING, "half_life": DECAY_POS_HL},
        "neg": {"sizing": PILOT_DECAY_SIZING, "half_life": DECAY_NEG_HL},
    },
}


def _binding_point(signature, direction, auc, adj_p, ic, overlay_name) -> dict:
    oriented = proto.directional_auc(auc, direction)
    point = oriented if oriented is not None else auc
    se = proto.hanley_mcneil_se(point, S6_PILOT_N_PER_CLASS, S6_PILOT_N_PER_CLASS)
    return {
        "point": float(point),
        "lo": float(max(0.0, point - 1.96 * se)),
        "hi": float(min(1.0, point + 1.96 * se)),
        "adj_p": float(adj_p),
        "ic": float(ic),
        "overlay": overlay_name,
    }


def _run_contrast(contrast_id: str) -> dict:
    spec = _CONTRASTS[contrast_id]
    # Per-signature accumulators over all (ic x theta) deciding conditions.
    names = list(kern.SIGNATURES)
    worst_dir = {n: None for n in names}       # min directional AUC (declared rows)
    worst_dev = {n: -1.0 for n in names}       # max |AUC - 0.5| (for undeclared display)
    worst_adj_p = {n: 0.0 for n in names}      # max adj p (intersection significance)
    any_reversed = {n: False for n in names}
    binding = {n: None for n in names}         # the displayed (point, band, labels) condition
    secondary = {n: None for n in names}       # T = 36 directional AUC, identity theta, worst cell
    crit_devs = []                             # familywise critical deviation per condition
    n_cells = 0

    for ic in PILOT_IC:
        pos_returns = _simulate_returns(ic, spec["pos"]["half_life"], spec["pos"]["sizing"],
                                        _cell_stream_index(contrast_id, ic, True))
        neg_returns = _simulate_returns(ic, spec["neg"]["half_life"], spec["neg"]["sizing"],
                                        _cell_stream_index(contrast_id, ic, False))
        for theta_name, theta in SMOOTHING_GRID:
            n_cells += 1
            sig_pos = _signatures_over_class(pos_returns, theta, proto.S6_DECISION_T)
            sig_neg = _signatures_over_class(neg_returns, theta, proto.S6_DECISION_T)
            # Deterministic per-condition permutation seed (no hash()-seeds).
            cond_seed = _config_seed(S6_PILOT_SEED, 900 + n_cells,
                                     0 if contrast_id == "h_size" else 1)
            res = proto.familywise_maxauc_test(
                sig_pos, sig_neg, seed=cond_seed, n_perm=S6_PILOT_N_PERM
            )
            crit_devs.append(float(np.quantile(res.max_dev_null, 1.0 - proto.S6_FAMILYWISE_ALPHA)))
            for n in names:
                direction = proto.S6_DIRECTIONS[n][contrast_id]
                auc = res.observed[n]
                adj_p = res.adjusted_p[n]
                d_auc = proto.directional_auc(auc, direction)
                worst_adj_p[n] = max(worst_adj_p[n], adj_p)
                significant = adj_p <= proto.S6_FAMILYWISE_ALPHA
                if significant and d_auc is not None and d_auc < 0.5:
                    any_reversed[n] = True
                # Track the binding (displayed) condition.
                if direction is not None:
                    if worst_dir[n] is None or d_auc < worst_dir[n]:
                        worst_dir[n] = d_auc
                        binding[n] = _binding_point(n, direction, auc, adj_p, ic, theta_name)
                else:
                    dev = abs(auc - 0.5)
                    if dev > worst_dev[n]:
                        worst_dev[n] = dev
                        binding[n] = _binding_point(n, direction, auc, adj_p, ic, theta_name)
        # T = 36 secondary at identity theta, worst cell (display only, never deciding).
        sig_pos_s = _signatures_over_class(pos_returns, SMOOTHING_GRID[0][1], proto.S6_SECONDARY_T)
        sig_neg_s = _signatures_over_class(neg_returns, SMOOTHING_GRID[0][1], proto.S6_SECONDARY_T)
        for n in names:
            direction = proto.S6_DIRECTIONS[n][contrast_id]
            d = proto.directional_auc(proto.mann_whitney_auc(sig_pos_s[n], sig_neg_s[n]), direction)
            val = d if d is not None else proto.mann_whitney_auc(sig_pos_s[n], sig_neg_s[n])
            if secondary[n] is None or (d is not None and val < secondary[n]):
                secondary[n] = float(val)

    rows = []
    for n in names:
        direction = proto.S6_DIRECTIONS[n][contrast_id]
        verdict = proto.classify_verdict(
            direction, worst_dir[n], worst_adj_p[n], any_reversed[n]
        )
        rows.append({
            "signature": n,
            "declared": direction is not None,
            "direction": direction,
            "verdict": verdict,
            "reversed": bool(any_reversed[n]),
            "auc_point": binding[n]["point"],
            "auc_lo": binding[n]["lo"],
            "auc_hi": binding[n]["hi"],
            "worst_adj_p": worst_adj_p[n],
            "n_deciding_cells": n_cells,
            "binding_ic": binding[n]["ic"],
            "binding_overlay": binding[n]["overlay"],
            "secondary_t_auc": secondary[n],
        })
    return {
        "id": contrast_id,
        "label": spec["label"],
        "n_deciding_cells": n_cells,
        "significance_floor": 0.5 + max(crit_devs),
        "usability_bar": proto.S6_AUC_MIN,
        "rows": rows,
    }


# FROZEN §3.4 registration content, authored from the spec (rendered verbatim by the page).
_FAMILY_ROWS = [
    {"signature": "autocorr", "formula": "lag-1 sample autocorrelation",
     "mechanism": "a slowly-decaying alpha mean adds trend-induced positive autocorrelation",
     "confound": "return smoothing (Getmansky-Lo-Makarov): illiquidity marks dominate live lag-1"},
    {"signature": "vol_of_vol", "formula": "CV of rolling 6-month volatility",
     "mechanism": "conviction sizing wobbles effective breadth -> time-varying book variance",
     "confound": "leverage changes, vol regimes"},
    {"signature": "skew", "formula": "sample skewness",
     "mechanism": "asymmetric conviction between book sides",
     "confound": "option-like overlays (a written-put posture)"},
    {"signature": "kurtosis", "formula": "excess kurtosis",
     "mechanism": "a scale mixture of normals has fat tails; conviction sizing makes a scale mixture",
     "confound": "fat-tailed underlying markets, overlays"},
    {"signature": "drawdown_shape", "formula": "MDD / (sigma * sqrt(T))",
     "mechanism": "vol clustering deepens MDD; a mid-window alpha death leaves a late deep drawdown",
     "confound": "one-episode dominance (a drawdown is n ~ 1)"},
    {"signature": "rolling_ir_slope", "formula": "OLS time-slope of the rolling 12-month IR",
     "mechanism": "front-loaded alpha -> the rolling IR trends down over the window",
     "confound": "AUM growth, regime luck"},
]


def _registration_block() -> dict:
    family = []
    for row in _FAMILY_ROWS:
        n = row["signature"]
        family.append({
            **row,
            "direction_h_size": proto.S6_DIRECTIONS[n]["h_size"],
            "direction_h_decay": proto.S6_DIRECTIONS[n]["h_decay"],
        })
    return {
        "hypotheses": [
            {"id": "h_size", "positive": "sizing_discipline = 0.8", "negative": "sizing_discipline = 0.0"},
            {"id": "h_decay", "positive": "alpha_half_life_months = 3 (fast)",
             "negative": "alpha_half_life_months = 36 (slow)"},
        ],
        "family": family,
        "forking_paths_naive_rate": 1.0 - 0.95 ** len(kern.SIGNATURES),
        "amendment_rule": (
            "Any change after first look -- a new signature, a different window, a moved "
            "threshold -- voids the registration and starts a version-2 protocol with a fresh "
            "confirmatory seed; results under the old protocol stand as-registered."
        ),
    }


def _headline(contrasts) -> dict:
    rows = [r for c in contrasts for r in c["rows"]]
    n_ship = sum(r["verdict"] == "ship" for r in rows)
    n_weak = sum(r["verdict"] == "weak_tell" for r in rows)
    n_null = sum(r["verdict"] == "null" for r in rows)
    text = (
        f"Two contrasts, six pre-committed signatures, {n_ship} shippable "
        f"tell{'s' if n_ship != 1 else ''} -- {n_weak} statistically-real whisper"
        f"{'s' if n_weak != 1 else ''} below the usability bar, {n_null} null"
        f"{'s' if n_null != 1 else ''}, on the bounded pilot grid."
    )
    return {"n_ship": n_ship, "n_weak_tell": n_weak, "n_null": n_null, "text": text}


def build(out_dir: Path = SITE_DATA_DIR) -> Path:
    contrasts = [_run_contrast("h_size"), _run_contrast("h_decay")]
    payload = {
        "meta": {
            "generator": "s6_signatures",
            "label": "PILOT",
            "pilot_seed": S6_PILOT_SEED,
            "decision_t": proto.S6_DECISION_T,
            "secondary_t": proto.S6_SECONDARY_T,
            "n_per_class": S6_PILOT_N_PER_CLASS,
            "n_perm": S6_PILOT_N_PERM,
            "auc_min": proto.S6_AUC_MIN,
            "familywise_alpha": proto.S6_FAMILYWISE_ALPHA,
            "rolling_windows": list(kern.S6_ROLLING_WINDOWS),
            "smoothing_theta": list(SMOOTHING_GRID[1][1]),
            "pilot_cells": {"h_size": contrasts[0]["n_deciding_cells"],
                            "h_decay": contrasts[1]["n_deciding_cells"]},
            "confirmatory": {"n_per_class": proto.S6_N_PER_CLASS, "n_perm": proto.S6_N_PERM,
                             "cells": {"h_size": 12, "h_decay": 8}, "seed": "S6_CONFIRM_SEED (wave-3)"},
        },
        "protocol": _registration_block(),
        "contrasts": contrasts,
        "headline": _headline(contrasts),
        "single_manager_odds": {
            "auc": proto.S6_AUC_MIN,
            "pair_odds": "orders a random cross-class pair correctly 2 times in 3",
            "single_manager": "about a 0.5-standard-deviation class separation -- a whisper, not a score",
        },
        "ladder": [
            {"rung": 1, "label": "simulator verdict (this page)"},
            {"rung": 2, "label": "external validation on E/P-labeled managers where truth is visible"},
            {"rung": 3, "label": "any roster-facing use"},
        ],
    }
    return write_json(out_dir / "s6_signatures.json", payload)
