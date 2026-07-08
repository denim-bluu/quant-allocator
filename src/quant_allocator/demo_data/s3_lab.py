"""S3 sizing & alpha-decay lab generator: three synthetic books -> JSON.

NUMERIC OUTPUT IS HELD FOR THE NUMERICS GATE. The demo numbers and any future
live numbers come from the SAME sizing_lab pipeline (§6.9); only the input data is
synthetic. Centerpiece: Meridian Arc Capital (sizer) and Kelso Bay Partners
(picker) hold IDENTICAL picks and differ only in sizing discipline, so they look a
tier apart on returns while the Fama-MacBeth sizing slope certifies the whole gap;
Thornwood Select's concentrated 30-name book accumulates only 174 independent
trades, below the gate, so the lab REFUSES to render a slope (§5).

The sizing leg runs on the v1 book (§6.4); the decay/holding legs use the
alpha_persistence=0.5 substrate dial (§6.5) whose known half-life the curve recovers.
numpy only; no new runtime dependency. CI renders the page from this JSON only.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from quant_allocator.demo_data._emit import SITE_DATA_DIR, write_json
from quant_allocator.flagships.sizing_lab import pipeline as sp
from quant_allocator.simulator.manager import ManagerConfig, simulate_manager
from quant_allocator.simulator.market import MarketConfig, simulate_market

# Fictional manager names (§8 ruling 6; no roster.py or cross-card collisions).
SIZER_NAME = "Meridian Arc Capital"
PICKER_NAME = "Kelso Bay Partners"
GATE_NAME = "Thornwood Select"

# NUMERICS-GATE: named demo seeds/dials. Distinct integer stream tags, no hash() seeds.
SPLIT_MARKET_SEED = 20260731
SPLIT_MANAGER_SEED = 20260732
GATE_MARKET_SEED = 20260733
GATE_MANAGER_SEED = 20260734
DECAY_MARKET_SEED_BASE = 20260740
DECAY_MANAGER_SEED_BASE = 20260900
N_ASSETS = 300
SPLIT_MONTHS = 120
GATE_MONTHS = 48
DECAY_MONTHS = 120
N_DECAY_REPS = 60              # NUMERICS-GATE: pooled reps for the half-life fit (teaching used 120)
SPLIT_IC = 0.10               # §5 / §8 ruling 2: strong sizing effect (discipline 0.9 on IC 0.10)
GATE_IC = 0.10
DECAY_IC = 0.08
DECAY_DISCIPLINE = 0.7
DECAY_HALF_LIFE = 6.0         # the dial the decay curve must recover
ALPHA_PERSISTENCE_DEMO = 0.5  # NUMERICS-GATE (§6.5): demo default; v1 legs use 0.0

# Re-exported for the page/test (curve length is DECAY_MAX_AGE + 1).
DECAY_MAX_AGE = sp.DECAY_MAX_AGE


def _reconstruct_ages(weights: np.ndarray, config) -> np.ndarray:
    # Exact holding ages from the weight panel. build_panel's generic consecutive-run age
    # (S3 §3.3) is off by the simulator's same-month drop-and-re-add: a name that is the
    # oldest of its side (dropped) yet still carries a nonzero weight was re-selected that
    # month and its age reset to 0 with no gap in the weight panel. The simulator's exit is
    # purely age-ordered (oldest first, name tiebreak), so replaying that rule against the
    # observed weights recovers the true age with no RNG/signal — the 1e-9 cross-check in
    # _panel_from_history self-validates it.
    assert config.exit_style == "age", "s3_lab._reconstruct_ages only replays the exit_style='age' rule"
    n_months, n_names = weights.shape
    n_rep_long = round(config.rebalance_fraction * config.n_long)
    n_rep_short = round(config.rebalance_fraction * config.n_short)
    ages = np.full((n_months, n_names), -1, dtype=int)
    current: dict[int, int] = {}  # name index -> holding age
    for t in range(n_months):
        for j in current:
            current[j] += 1
        if t > 0:
            longs = [j for j in current if weights[t - 1, j] > 0.0]
            shorts = [j for j in current if weights[t - 1, j] < 0.0]
            drop = sorted(longs, key=lambda j: (-current[j], j))[:n_rep_long]
            drop += sorted(shorts, key=lambda j: (-current[j], j))[:n_rep_short]
            for j in drop:
                del current[j]
        for j in range(n_names):
            if weights[t, j] != 0.0:
                current.setdefault(j, 0)  # survivor keeps age; new entry / re-add -> 0
            else:
                current.pop(j, None)
        for j, age in current.items():
            ages[t, j] = age
    return ages


def _panel_from_history(market, history) -> sp.PositionPanel:
    # Reconstruct the realized-idio panel (base idio + the §6.5 persistence edge) and
    # cross-check it against the simulator's aggregate true_alpha_returns (drift guard).
    weights = history.weights.to_numpy()
    base_idio = market.idio_returns.to_numpy()
    ages = _reconstruct_ages(weights, history.config)
    side = np.sign(weights)
    persist = history.config.alpha_persistence
    if persist == 0.0:
        realized = base_idio
    else:
        idio_std = market.idio_returns.std().to_numpy()
        held = ages >= 0
        decay = 0.5 ** (np.where(held, ages, 0) / history.config.alpha_half_life_months)
        edge = persist * side * decay * idio_std[None, :] * held
        realized = base_idio + edge
    reconstructed = (weights * realized).sum(axis=1)
    if not np.allclose(reconstructed, history.true_alpha_returns.to_numpy(), atol=1e-9):
        raise RuntimeError("realized-idio reconstruction diverged from the simulator")
    return sp.PositionPanel(weights=weights, idio=realized, ages=ages, side=side)


def _split_histories():
    market = simulate_market(
        MarketConfig(n_assets=N_ASSETS, n_months=SPLIT_MONTHS, seed=SPLIT_MARKET_SEED)
    )
    base = dict(n_long=40, n_short=25, rebalance_fraction=0.25,
                information_coefficient=SPLIT_IC, seed=SPLIT_MANAGER_SEED)
    sizer = simulate_manager(market, ManagerConfig(sizing_discipline=0.9, **base))
    picker = simulate_manager(market, ManagerConfig(sizing_discipline=0.0, **base))
    return market, sizer, picker


def _split_manager_payload(role, name, market, history) -> dict:
    panel = _panel_from_history(market, history)
    est = sp.sizing_slope_estimate(panel)
    ci = sp.cluster_bootstrap(
        lambda p: sp.sizing_slope_estimate(p).point, panel, sp.SIZING_BOOTSTRAP_N,
        np.random.default_rng([sp.S3_BOOTSTRAP_STREAM, SPLIT_MANAGER_SEED]))
    alpha, ir = sp.annualized_alpha_ir(panel)
    c = history.config
    return {
        "role": role, "name": name,
        "alpha_annual": alpha, "ir": ir,
        "slope": {"point": est.point, "se": est.se, "tstat": est.tstat,
                  "detected": bool(est.detected), "ci_low": ci.lo, "ci_high": ci.hi},
        "independent_trades": sp.independent_trades(
            c.n_long, c.n_short, c.rebalance_fraction, SPLIT_MONTHS),
        "sizing_scatter": _scatter(panel),
    }


def _scatter(panel) -> list[dict]:
    # A per-position (|w|, active contribution) sample the page plots; capped for JSON size.
    hedged = panel.idio - panel.idio.mean(axis=1, keepdims=True)
    contrib = panel.weights * hedged
    rows, cols = np.where(panel.weights != 0.0)
    step = max(1, len(rows) // 400)  # NUMERICS-GATE: scatter downsample cap (~400 points)
    return [{"size": float(abs(panel.weights[t, j])), "contribution": float(contrib[t, j])}
            for t, j in zip(rows[::step], cols[::step])]


def _decay_payload() -> dict:
    panels = []
    for r in range(N_DECAY_REPS):
        market = simulate_market(
            MarketConfig(n_assets=N_ASSETS, n_months=DECAY_MONTHS, seed=DECAY_MARKET_SEED_BASE + r)
        )
        history = simulate_manager(market, ManagerConfig(
            n_long=40, n_short=25, rebalance_fraction=0.10, information_coefficient=DECAY_IC,
            sizing_discipline=DECAY_DISCIPLINE, alpha_half_life_months=DECAY_HALF_LIFE,
            alpha_persistence=ALPHA_PERSISTENCE_DEMO, seed=DECAY_MANAGER_SEED_BASE + r))
        panels.append(_panel_from_history(market, history))
    # display scale (half-life is scale-invariant)
    idio_vol = float(np.nanmean([np.nanstd(p.idio) for p in panels]))
    curve = sp.decay_curve(panels, idio_vol, sp.DECAY_MAX_AGE)
    hl_pooled = sp.fit_half_life(curve, np.arange(1, sp.DECAY_MAX_AGE + 1))
    hl_0_12 = sp.fit_half_life(curve, np.arange(0, sp.DECAY_MAX_AGE + 1))
    single = sp.cluster_bootstrap(
        lambda p: sp.fit_half_life(sp.decay_curve([p], idio_vol, sp.DECAY_MAX_AGE),
                                   np.arange(1, sp.DECAY_MAX_AGE + 1)),
        panels[0], sp.SIZING_BOOTSTRAP_N // 4,
        np.random.default_rng([sp.S3_BOOTSTRAP_STREAM, DECAY_MANAGER_SEED_BASE]))
    return {
        "curve": [None if not np.isfinite(v) else float(v) for v in curve.values],
        "counts": [int(c) for c in curve.counts],
        "half_life_pooled": hl_pooled, "half_life_ages_0_12": hl_0_12,
        "single_manager_ci": {"lo": single.lo, "hi": single.hi},
        "dial_truth": DECAY_HALF_LIFE, "idio_vol": idio_vol,
    }


def _holding_payload() -> dict:
    market = simulate_market(
        MarketConfig(n_assets=N_ASSETS, n_months=DECAY_MONTHS, seed=DECAY_MARKET_SEED_BASE)
    )
    history = simulate_manager(market, ManagerConfig(
        n_long=40, n_short=25, rebalance_fraction=0.10, information_coefficient=DECAY_IC,
        sizing_discipline=DECAY_DISCIPLINE, alpha_half_life_months=DECAY_HALF_LIFE,
        alpha_persistence=ALPHA_PERSISTENCE_DEMO, seed=DECAY_MANAGER_SEED_BASE))
    panel = _panel_from_history(market, history)
    return {"shares": sp.holding_decomposition(panel)}


def _powergate_payload(registry: dict) -> dict:
    market = simulate_market(
        MarketConfig(n_assets=N_ASSETS, n_months=GATE_MONTHS, seed=GATE_MARKET_SEED)
    )
    history = simulate_manager(market, ManagerConfig(
        n_long=20, n_short=10, rebalance_fraction=0.10, information_coefficient=GATE_IC,
        sizing_discipline=0.9, seed=GATE_MANAGER_SEED))
    c = history.config
    trades = sp.independent_trades(c.n_long, c.n_short, c.rebalance_fraction, GATE_MONTHS)
    metrics = registry.get("metrics", {})
    sizing_threshold = metrics.get("sizing_slope", {}).get("threshold")
    hit_threshold = metrics.get("hit_rate", {}).get("threshold")
    renders = sizing_threshold is not None and trades >= sizing_threshold
    return {
        "name": GATE_NAME, "independent_trades": trades,
        "sizing_threshold": sizing_threshold, "hit_rate_threshold": hit_threshold,
        "renders_slope": bool(renders),
        # §8 ruling 2: at the atlas REFERENCE effect the sizing slope never clears 80% within T<=120.
        "reference_effect_never_clears": True,
    }


def _read_registry(registry_path: Path) -> dict:
    # The committed registry is an integration dependency (see plan Handoff). Until it is
    # materialized the file is absent, so the generator degrades to an empty (null-threshold)
    # registry and the page renders the honest "no measured tenure suffices" statement.
    if not registry_path.exists():
        return {"version": None, "metrics": {}}
    return json.loads(registry_path.read_text(encoding="utf-8"))


def build(out_dir: Path = SITE_DATA_DIR,
          registry_path: Path = SITE_DATA_DIR / "powergate_registry.json") -> Path:
    registry = _read_registry(registry_path)
    market, sizer, picker = _split_histories()
    sizer_p = _split_manager_payload("sizer", SIZER_NAME, market, sizer)
    picker_p = _split_manager_payload("picker", PICKER_NAME, market, picker)
    payload = {
        "meta": {
            "generator": "s3_lab",
            "cluster_axes": list(sp.CLUSTER_AXES),
            "holding_buckets": [b[2] for b in sp.HOLDING_BUCKETS],
            "bootstrap_n": sp.SIZING_BOOTSTRAP_N,
            "decay_max_age": sp.DECAY_MAX_AGE,
            "alpha_persistence_demo": ALPHA_PERSISTENCE_DEMO,
            "registry_version": registry.get("version"),
        },
        "split": [sizer_p, picker_p],
        "sizing_value": {"gap_annual": sizer_p["alpha_annual"] - picker_p["alpha_annual"]},
        "decay": _decay_payload(),
        "holding": _holding_payload(),
        "powergate": _powergate_payload(registry),
    }
    return write_json(out_dir / "s3_lab.json", payload)
