"""M3 drawdown-alarm generator: two vol-regime managers + a roster -> JSON.

NUMERIC OUTPUT IS HELD FOR THE NUMERICS GATE. The demo numbers and any future
live numbers come from the SAME alarm pipeline (M3 spec §5); only the input data is
synthetic. The centerpiece: two managers with the same realized -12% drawdown — a
high-vol trend book (GREEN: -12% is ordinary against its 20%-vol null) and a smooth
credit book (RED: -12% sits deep in its 6%-vol null). Plus a roster heat-list with its
expected-false-RED count printed (M3 spec §3.4).

M3 is returns-native; the two vol regimes (trend vs credit) span more than the single
equity-L/S simulator produces, so realized paths here are drawn directly from each
manager's own AR(1) null process and seed-scanned to plant a -12% max drawdown. The
alarm CODE PATH is identical to a live build — only the input data is synthetic.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from quant_allocator.demo_data._emit import SITE_DATA_DIR, write_json
from quant_allocator.demo_data.roster import MANAGER_NAMES
from quant_allocator.flagships.alarms import pipeline as ap

BASE_SEED = 20260707
MANAGER_MONTHS = 48
# NUMERICS-GATE: authored target realized max-drawdown for BOTH centerpiece managers.
TARGET_MDD = 0.12
MDD_TOLERANCE = 0.005
# NUMERICS-GATE ALARM_HYPOTHESIS_FAN (provisional — {0.5, 1.0, 1.5} x claimed Sharpe): the
# claimed-Sharpe fallback (spec §3.6) rendered as a fan; the Dietvorst dial snaps among these.
SHARPE_FAN = (0.5, 1.0, 1.5)
# NUMERICS-GATE: authored (claimed Sharpe, annual vol) per centerpiece role.
TREND = {"role": "trend", "name": "Windward Trend Partners", "sharpe": 0.7, "vol": 0.20}
CREDIT = {"role": "credit", "name": "Stillwater Credit Partners", "sharpe": 1.0, "vol": 0.06}
# NUMERICS-GATE: demo roster size (roster count default). E[false RED] = size x RED_BUDGET.
ROSTER_SIZE_M3 = 12
# NUMERICS-GATE: authored roster rows (name code, annual vol, claimed Sharpe, realized-path seed).
# Most are healthy (shallow drawdowns -> GREEN); two are planted tail draws -> RED.
_ROSTER_SPEC = [
    ("A01", 0.18, 0.8, 11), ("A02", 0.15, 0.7, 12), ("A03", 0.22, 0.9, 13),
    ("A04", 0.10, 0.6, 14), ("A05", 0.14, 0.7, 15), ("A06", 0.20, 0.8, 16),
    ("A07", 0.12, 0.6, 17), ("A08", 0.16, 0.7, 18), ("A09", 0.19, 0.8, 19),
    ("A10", 0.11, 0.6, 20), ("B01", 0.07, 0.9, 230), ("B02", 0.06, 1.0, 313),
]


def _simulate_realized(sharpe_annual: float, vol_annual: float, ar1: float, seed: int) -> np.ndarray:
    # One realized return path from the manager's own null process (returns-native demo input).
    rng = np.random.default_rng([seed, 99])
    vol_monthly = vol_annual / np.sqrt(12.0)
    mean_monthly = sharpe_annual / np.sqrt(12.0) * vol_monthly
    innovation_sd = vol_monthly * np.sqrt(1.0 - ar1**2)
    out = np.empty(MANAGER_MONTHS)
    prev = 0.0
    for k in range(MANAGER_MONTHS):
        prev = ar1 * prev + rng.normal(0.0, innovation_sd)
        out[k] = mean_monthly + prev
    return out


def _realized_mdd(returns: np.ndarray) -> float:
    wealth = np.cumprod(1.0 + returns)
    peak = np.maximum.accumulate(wealth)
    return float(-(wealth / peak - 1.0).min())


def _scan_realized_seed(sharpe: float, vol: float, seeds=range(0, 4000)) -> int:
    # Recovery helper (see the NUMERICS-GATE note): return the first seed whose realized path has a
    # max drawdown within tolerance of TARGET_MDD. Planting the authored -12% outcome, house style.
    for seed in seeds:
        returns = _simulate_realized(sharpe, vol, 0.0, seed)
        if abs(_realized_mdd(returns) - TARGET_MDD) <= MDD_TOLERANCE:
            return seed
    raise RuntimeError(f"no seed hit MDD={TARGET_MDD} for sharpe={sharpe}, vol={vol}")


# NUMERICS-GATE: seeds resolved by _scan_realized_seed at authoring time; pinned so the build is
# offline and deterministic (regenerate with _scan_realized_seed if the pipeline math changes).
_TREND_SEED = 3       # _scan_realized_seed(TREND["sharpe"], TREND["vol"]) -> -12% GREEN at 20% vol
_CREDIT_SEED = 405    # scanned for a ~-12% realized MDD that lands RED against the 6%-vol null


def _fan(returns: np.ndarray, sharpe: float, vol: float) -> list[dict]:
    fan = []
    for mult in SHARPE_FAN:
        hyp = ap.DrawdownHypothesis(sharpe_annual=sharpe * mult, vol_annual=vol)
        v = ap.alarm_state(returns, hyp, seed=BASE_SEED)
        fan.append(
            {"sharpe": sharpe * mult, "level": v.level, "mdd_percentile": v.mdd_percentile}
        )
    return fan


def _split_manager(spec: dict, seed: int) -> dict:
    returns = _simulate_realized(spec["sharpe"], spec["vol"], 0.0, seed)
    hyp = ap.DrawdownHypothesis(sharpe_annual=spec["sharpe"], vol_annual=spec["vol"])
    v = ap.alarm_state(returns, hyp, roster_size=ROSTER_SIZE_M3, seed=BASE_SEED)
    return {
        "role": spec["role"],
        "name": spec["name"],
        "vol_annual": spec["vol"],
        "claimed_sharpe": spec["sharpe"],
        "months": MANAGER_MONTHS,
        "realized_mdd": v.realized_mdd,
        "mdd_percentile": v.mdd_percentile,
        "amber_threshold": v.amber_threshold,
        "red_threshold": v.red_threshold,
        "level": v.level,
        "ar1": v.ar1,
        "monthly_returns": [float(x) for x in returns],
        "band": {
            "running_mdd_realized": [float(x) for x in v.band.running_mdd_realized],
            "band_amber": [float(x) for x in v.band.band_amber],
            "band_red": [float(x) for x in v.band.band_red],
        },
        "fan": _fan(returns, spec["sharpe"], spec["vol"]),
    }


def _roster_manager(code: str, vol: float, sharpe: float, seed: int) -> dict:
    returns = _simulate_realized(sharpe, vol, 0.0, seed)
    hyp = ap.DrawdownHypothesis(sharpe_annual=sharpe, vol_annual=vol)
    v = ap.alarm_state(returns, hyp, seed=BASE_SEED)
    return {
        "code": code,
        "name": MANAGER_NAMES[code],
        "realized_mdd": v.realized_mdd,
        "mdd_percentile": v.mdd_percentile,
        "level": v.level,
    }


def build(out_dir: Path = SITE_DATA_DIR) -> Path:
    split = [
        _split_manager(TREND, _TREND_SEED),
        _split_manager(CREDIT, _CREDIT_SEED),
    ]
    roster_managers = [_roster_manager(code, vol, sr, seed) for code, vol, sr, seed in _ROSTER_SPEC]
    observed_red = sum(m["level"] == "red" for m in roster_managers)
    payload = {
        "meta": {
            "generator": "m3_alarms",
            "months": MANAGER_MONTHS,
            "n_paths": ap.DRAWDOWN_PATHS_M3,
            "window": "full_track",
            "amber_budget": ap.AMBER_BUDGET,
            "red_budget": ap.RED_BUDGET,
            "sharpe_fan": list(SHARPE_FAN),
        },
        "split": split,
        "roster": {
            "size": ROSTER_SIZE_M3,
            "managers": roster_managers,
            "observed_red": observed_red,
            "expected_false_red": ROSTER_SIZE_M3 * ap.RED_BUDGET,
        },
    }
    return write_json(out_dir / "m3_alarms.json", payload)


def _scan_roster_reds(seeds=range(0, 200)) -> None:
    # Recovery helper: print (vol, sharpe, seed) combos that yield a RED, for planting the two
    # roster tail draws (B01/B02). Not part of the build.
    for vol, sharpe in ((0.06, 1.0), (0.07, 0.9)):
        hyp = ap.DrawdownHypothesis(sharpe_annual=sharpe, vol_annual=vol)
        for seed in seeds:
            returns = _simulate_realized(sharpe, vol, 0.0, seed)
            v = ap.alarm_state(returns, hyp, n_paths=4000, seed=BASE_SEED)
            if v.level == "red":
                print(f"vol={vol} sharpe={sharpe} seed={seed} mdd={v.realized_mdd:.3f}")
