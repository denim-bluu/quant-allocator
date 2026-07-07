"""M1 drift monitor generator: simulator exposure/return paths -> CUSUM demo JSON.

NUMERIC OUTPUT IS HELD FOR THE NUMERICS GATE — this JSON does not publish
until certified. The demo imports detector.py and calibrate.py so the demo numbers
and any future live numbers come from the SAME code path (M1 spec §5); only the
input differs (simulator emission here vs a real risk report live).

The centerpiece: a beta-neutral manager (stated net-beta band [-0.10, +0.10]) whose
MEASURED net market beta walks 0.10 -> 0.45 over the window; the CUSUM lights up at
the sustained-breach onset with the honest-wander null band behind the path; a
TierBadge marks this measured (E); the R-tier rolling-beta version is rendered greyed
behind a noise chip to make the tier degradation visible (M1 spec §5, §3.6).

The measurement is exact (Robust); the sustained-drift ALARM is a calibrated rule
(gate ruling): its threshold h is set on the simulator's autocorrelated
honest-wander null, never asserted.
"""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np

from quant_allocator.demo_data._emit import SITE_DATA_DIR, write_json
from quant_allocator.flagships.drift import bands, calibrate, detector
from quant_allocator.simulator.manager import ManagerConfig, NetBetaDrift, simulate_manager
from quant_allocator.simulator.market import MarketConfig, simulate_market
from quant_allocator.simulator.tiers import emit_tiers

BASE_SEED = 20260707
MANAGER_CODE = "M01"
# FICTIONAL display name (repo rule: no real manager names; banner discloses).
MANAGER_NAME = "Harrowgate Neutral"
STRATEGY = "equity_market_neutral"
MONITORED_CLASS = "beta_market"

# --- Book & horizon (Docket D-M1-2: demo-sized market for CI-affordable calibration) ---
N_ASSETS_DEMO = 120
DEMO_HORIZON = 60
MANAGER_IC = 0.05
MANAGER_SEED = 0

# --- Stated band & measured walk (M1 spec §"constants") ---
# NUMERICS-GATE: beta-neutral baseline target_net; measured beta_market wanders here (band edge).
DEMO_NET_BASE = 0.10
# NUMERICS-GATE DEMO_DRIFT_WALK: visual path walks 0.10 -> 0.45 (total_walk 0.35), larger
# than the pinned 0.30 for visual clarity (M1 spec §"constants").
DEMO_DRIFT_WALK = 0.35
DEMO_DRIFT_ONSET = 12
DEMO_DRIFT_RAMP = 12

# --- Detector knobs (M1 spec §3.3, §"constants") ---
# NUMERICS-GATE CUSUM_ALLOWANCE_K: allowance = fraction x pinned monthly drift step.
CUSUM_ALLOWANCE_FRACTION = 0.5
# NUMERICS-GATE PINNED_DRIFT_EFFECT: 0.30 net-beta walk over 12 months (X1 §3.4).
PINNED_DRIFT_EFFECT = 0.30
CUSUM_ALLOWANCE_K = CUSUM_ALLOWANCE_FRACTION * (PINNED_DRIFT_EFFECT / 12.0)
# NUMERICS-GATE: h search grid, in accumulated-exposure units; h is CALIBRATED, not free.
H_GRID = np.round(np.arange(0.02, 1.50, 0.02), 4)
# NUMERICS-GATE FALSE_ALARM_BUDGET: 0.05 per manager-year (1-in-20) size target (M1 §4.1).
FALSE_ALARM_BUDGET = 0.05
# NUMERICS-GATE K_CONSEC / M_WINDOW: 3-of-4 simple run-length rung (M1 spec §"constants").
K_CONSEC = 3
M_WINDOW = 4
RBSA_WINDOW = 24

# --- Calibration ensemble sizes (Docket D-M1-2) ---
# NUMERICS-GATE: demo-fidelity path counts; the full atlas (X1 D-11) uses >= 1000 across
# the full T-grid. Sized so build() runs in CI in a few seconds while Wilson intervals
# stay meaningful.
N_NULL_PATHS = 300
N_ALT_PATHS = 300
DETECTION_WINDOW = 48  # the kill-criterion tenure T (M1 spec §4 kill criterion)
# NUMERICS-GATE DETECTION_FLOOR: detection >= 0.5 at size <= budget by T=48 or the alarm
# demotes to the measured-breach flag only (M1 spec §4 kill/demote criterion).
DETECTION_FLOOR = 0.5
WILSON_Z = 1.96

_MANAGER_KWARGS = {"information_coefficient": MANAGER_IC, "seed": MANAGER_SEED}
_FACTOR_NAMES = ("market", "size", "value", "momentum")


def _visual_manager():
    market = simulate_market(
        MarketConfig(n_assets=N_ASSETS_DEMO, n_months=DEMO_HORIZON, seed=BASE_SEED)
    )
    drift = NetBetaDrift(
        total_walk=DEMO_DRIFT_WALK, ramp_months=DEMO_DRIFT_RAMP, onset_month=DEMO_DRIFT_ONSET
    )
    history = simulate_manager(
        market, ManagerConfig(target_net=DEMO_NET_BASE, net_drift=drift, **_MANAGER_KWARGS)
    )
    return market, history


def _percentile_band(paths: list[np.ndarray]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    stack = np.vstack(paths)
    return (
        np.percentile(stack, 5, axis=0),
        np.percentile(stack, 50, axis=0),
        np.percentile(stack, 95, axis=0),
    )


def _slope_interval(series: np.ndarray) -> dict:
    # OLS slope of the factor-share path vs month with a normal-z CI on the slope SE.
    # Estimate-bearing (σ̂²_idio feeds the path); rendered as an IntervalStat (the lead reviewer §3.5).
    t = np.arange(len(series), dtype=float)
    design = np.column_stack([np.ones(len(series)), t])
    coef, *_ = np.linalg.lstsq(design, series, rcond=None)
    resid = series - design @ coef
    dof = max(1, len(series) - 2)
    sigma2 = float(resid @ resid) / dof
    cov = sigma2 * np.linalg.inv(design.T @ design)
    se = float(np.sqrt(cov[1, 1]))
    slope = float(coef[1])
    half = WILSON_Z * se
    return {"point": slope, "ci_lo": slope - half, "ci_hi": slope + half}


def _rolling_band(null_rbeta: list[np.ndarray], delta: float) -> bands.BandSpec:
    # Centre the R-tier band on the honest rolling-beta level (± the net-beta half-width),
    # so the R detector is calibrated on its own null, a fair tier comparison.
    finite = np.concatenate([p[~np.isnan(p)] for p in null_rbeta])
    centre = float(np.median(finite))
    half = (bands.NET_BETA_BAND_DEFAULT[1] - bands.NET_BETA_BAND_DEFAULT[0]) / 2.0
    return bands.BandSpec(lower=centre - half, upper=centre + half, delta=delta)


def _idio_variance(returns: np.ndarray, factors: np.ndarray) -> float:
    design = np.column_stack([np.ones(len(returns)), factors])
    coef, *_ = np.linalg.lstsq(design, returns, rcond=None)
    resid = returns - design @ coef
    return float(resid.var(ddof=1))


def _detection_dict(res: calibrate.DetectionResult) -> dict:
    return {
        "rate": res.rate,
        "ci_lo": res.wilson_lo,
        "ci_hi": res.wilson_hi,
        "n_detected": res.n_detected,
        "n_paths": res.n_paths,
        "median_delay": res.median_delay,
    }


def build(out_dir: Path = SITE_DATA_DIR) -> Path:
    band = bands.band_for_class(MONITORED_CLASS, stated=bands.NET_BETA_BAND_DEFAULT)

    # --- 1. Null ensemble (honest wander): calibrate h_E, h_R + the wander band. ---
    null_beta = calibrate.draw_beta_paths(
        N_NULL_PATHS, BASE_SEED, N_ASSETS_DEMO, DEMO_HORIZON, DEMO_NET_BASE,
        drift=None, manager_kwargs=_MANAGER_KWARGS,
    )
    null_rbeta = calibrate.draw_rolling_beta_paths(
        N_NULL_PATHS, BASE_SEED, N_ASSETS_DEMO, DEMO_HORIZON, DEMO_NET_BASE,
        drift=None, window=RBSA_WINDOW, manager_kwargs=_MANAGER_KWARGS,
    )
    h_e = calibrate.calibrate_threshold(null_beta, band, CUSUM_ALLOWANCE_K, FALSE_ALARM_BUDGET, H_GRID)
    # R-tier rolling-beta centres near the ~0.10 target net beta; calibrate against a band centred there.
    r_band = _rolling_band(null_rbeta, band.delta)
    r_clean = [p[~np.isnan(p)] for p in null_rbeta]
    h_r = calibrate.calibrate_threshold(r_clean, r_band, CUSUM_ALLOWANCE_K, FALSE_ALARM_BUDGET, H_GRID)
    size_rate, size_n_alarm, size_n = calibrate.false_alarm_rate(null_beta, band, CUSUM_ALLOWANCE_K, h_e)

    # --- 2. Alternative ensemble (pinned drift): detection + delay at E and R. ---
    pinned = NetBetaDrift(
        total_walk=PINNED_DRIFT_EFFECT, ramp_months=DEMO_DRIFT_RAMP, onset_month=DEMO_DRIFT_ONSET
    )
    alt_beta = calibrate.draw_beta_paths(
        N_ALT_PATHS, BASE_SEED + 100_000, N_ASSETS_DEMO, DEMO_HORIZON, DEMO_NET_BASE,
        drift=pinned, manager_kwargs=_MANAGER_KWARGS,
    )
    alt_rbeta = calibrate.draw_rolling_beta_paths(
        N_ALT_PATHS, BASE_SEED + 100_000, N_ASSETS_DEMO, DEMO_HORIZON, DEMO_NET_BASE,
        drift=pinned, window=RBSA_WINDOW, manager_kwargs=_MANAGER_KWARGS,
    )
    det_e = calibrate.measure_detection(
        alt_beta, band, CUSUM_ALLOWANCE_K, h_e, DEMO_DRIFT_ONSET, DETECTION_WINDOW, WILSON_Z
    )
    det_r = calibrate.measure_detection(
        [p[~np.isnan(p)] for p in alt_rbeta], r_band, CUSUM_ALLOWANCE_K, h_r,
        max(0, DEMO_DRIFT_ONSET - RBSA_WINDOW + 1), DETECTION_WINDOW, WILSON_Z,
    )

    # --- 3. The single visual manager (the authored 0.10 -> 0.45 walk). ---
    market, history = _visual_manager()
    exposures = emit_tiers(market, history).exposures
    exposures.index = exposures.index.astype(str)
    months = list(exposures.index)
    beta_path = exposures[MONITORED_CLASS].to_numpy()
    alarm = detector.cusum_alarm(beta_path, band, CUSUM_ALLOWANCE_K, h_e)
    wander_p05, wander_p50, wander_p95 = _percentile_band(null_beta)
    rolling = detector.rolling_beta_path(
        history.monthly_returns.to_numpy(), market.factor_returns.to_numpy(), RBSA_WINDOW
    )

    # --- 4. Factor-share drift (estimate-bearing; slope IntervalStat + VerdictChip). ---
    beta_cols = [f"beta_{f}" for f in _FACTOR_NAMES]
    betas = exposures[beta_cols].to_numpy()
    factor_cov = market.factor_returns.cov().to_numpy()
    idio_var = _idio_variance(history.monthly_returns.to_numpy(), market.factor_returns.to_numpy())
    fs_path = detector.factor_share_path(betas, factor_cov, idio_var)
    fs_slope = _slope_interval(fs_path)
    fs_verdict = "rising" if fs_slope["ci_lo"] > 0.0 else "flat"

    alarm_cleared = bool(det_e.rate >= DETECTION_FLOOR and size_rate <= FALSE_ALARM_BUDGET + 1e-9)

    payload = {
        "meta": {
            "generator": "m1_drift",
            "manager_code": MANAGER_CODE,
            "manager_name": MANAGER_NAME,
            "strategy": STRATEGY,
            "months": DEMO_HORIZON,
            "monitored_class": MONITORED_CLASS,
            "tier": "E",
        },
        "band": {
            "lower": band.lower, "upper": band.upper, "delta": band.delta, "assumed": band.assumed
        },
        "cusum": {
            # calibrate_threshold returns inf when no grid h meets the budget (the R
            # tier here); map that sentinel to JSON null so browser JSON.parse of the
            # inlined card-data never chokes on `Infinity` (_emit sentinel convention).
            "k": CUSUM_ALLOWANCE_K,
            "h_e": h_e if math.isfinite(h_e) else None,
            "h_r": h_r if math.isfinite(h_r) else None,
            "allowance_fraction": CUSUM_ALLOWANCE_FRACTION,
        },
        "visual": {
            "months": months,
            "beta_path": [float(x) for x in beta_path],
            "s_plus": [float(x) for x in alarm.s_plus],
            "alarm_month": alarm.alarm_month,
            "drift_onset": DEMO_DRIFT_ONSET,
            "wander_p05": [float(x) for x in wander_p05],
            "wander_p50": [float(x) for x in wander_p50],
            "wander_p95": [float(x) for x in wander_p95],
            "rolling_beta": [None if np.isnan(x) else float(x) for x in rolling],
        },
        "factor_share": {
            "path": [float(x) for x in fs_path],
            "slope": fs_slope,
            "verdict": fs_verdict,
        },
        "operating": {
            "budget_per_year": FALSE_ALARM_BUDGET,
            "pinned_effect": PINNED_DRIFT_EFFECT,
            "detection_window": DETECTION_WINDOW,
            "size_e": {"rate": size_rate, "n_alarming": size_n_alarm, "n_paths": size_n},
            "detection_e": _detection_dict(det_e),
            "detection_r": _detection_dict(det_r),
        },
        "alarm_cleared": alarm_cleared,
    }
    return write_json(out_dir / "m1_drift.json", payload)


def _scan_manager_seeds(seeds=range(0, 40)) -> None:
    # Recovery helper (see the HELD-FOR-GATE note): print seeds where the visual walk's
    # CUSUM fires cleanly after onset and E detection clears the floor above R.
    band = bands.band_for_class(MONITORED_CLASS, stated=bands.NET_BETA_BAND_DEFAULT)
    for seed in seeds:
        market = simulate_market(
            MarketConfig(n_assets=N_ASSETS_DEMO, n_months=DEMO_HORIZON, seed=BASE_SEED)
        )
        drift = NetBetaDrift(
            total_walk=DEMO_DRIFT_WALK, ramp_months=DEMO_DRIFT_RAMP, onset_month=DEMO_DRIFT_ONSET
        )
        history = simulate_manager(
            market,
            ManagerConfig(
                target_net=DEMO_NET_BASE, net_drift=drift,
                information_coefficient=MANAGER_IC, seed=seed,
            ),
        )
        beta_path = emit_tiers(market, history).exposures[MONITORED_CLASS].to_numpy()
        alarm = detector.cusum_alarm(beta_path, band, CUSUM_ALLOWANCE_K, 0.30)
        if alarm.fired and alarm.alarm_month >= DEMO_DRIFT_ONSET:
            print(f"seed {seed}: alarm at month {alarm.alarm_month} (onset {DEMO_DRIFT_ONSET})")
