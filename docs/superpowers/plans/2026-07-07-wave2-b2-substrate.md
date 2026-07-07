# Wave-2 Batch-2 Shared Simulator Substrate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the five gate-approved, default-OFF simulator extensions that the S3/S4/S5/S6 build tracks all depend on — a decaying held-name edge (`alpha_persistence`, S3), an AR(1) idiosyncratic-persistence filter (`idio_ar1`, S4), a four-value exit-selection dial (`exit_style`, S4), a decorrelated short-signal panel (`short_information_coefficient`, S5), and a pure-function return-smoothing overlay (`SmoothingOverlay`, S6). Every dial is byte-identical to the current simulator at its default so that no existing test and no committed `site/data/*.json` changes.

**Architecture:** Four of the five extensions are optional fields on the existing frozen `ManagerConfig`/`MarketConfig`, each guarded so that when OFF the code path and the RNG consumption are unchanged (the `death_month`/`net_drift` precedent). The fifth (`SmoothingOverlay`) is a new pure-function pair in `simulator/overlays.py` alongside `WrittenPutOverlay` — deterministic, RNG-free, identity at zero parameters. Two dials consume randomness (`exit_style="random"`, `short_information_coefficient`); each draws from its own `np.random.default_rng([seed, tag])` generator under a **new named integer stream tag**, drawn *after* the existing manager `noise` array so the main stream stays byte-identical. The new tags are registered in `tests/simulator/test_manager.py::test_rng_stream_tags_are_distinct`, the test that pins the simulator stream-tag enumeration.

**Tech Stack:** Python 3.11+, numpy, pandas. `np.random.default_rng([seed, stream_tag])` per-module streams. pytest (`pythonpath=["src"]`, `addopts="-m 'not network'"`). ruff line-length 100. Package/venv manager: `uv`.

## Global Constraints

- **Byte-identity invariant (load-bearing).** Every dial default reproduces the current simulator output byte-for-byte. Each dial gets a **dial-guard test** asserting identical output arrays at its default (the `death_month` precedent in `tests/simulator/test_manager_dials.py`: `pd.testing.assert_frame_equal` on weights, `assert_series_equal` on the return series). The existing `tests/simulator/` and `tests/demo_data/*::test_byte_for_byte_determinism_and_matches_committed` suites MUST stay green; do **not** edit any existing test's expected values. Verified after every task by running the pytest commands in *Automated Verification*.
- **Each active dial gets a minimal effect test** — the dialed behavior moves the right statistic in the right direction (e.g. `alpha_persistence>0` raises realized true alpha; `idio_ar1=ρ` injects lag-1 autocorrelation ≈ ρ with variance preserved; `exit_style="signal"` earns more true alpha than `"disposition"` under persistence).
- **No `hash()`-derived seeds anywhere.** Named integer stream tags only. The two RNG-consuming dials use module-level constants `_EXIT_RANDOM_STREAM` and `_SHORT_SIGNAL_STREAM` in `simulator/manager.py`, each passed as the second element of `np.random.default_rng([config.seed, tag])`. The repo's same-seed-collision history is why this is explicit.
- **New stream tags (chosen, non-colliding).** `_EXIT_RANDOM_STREAM = 3` (uniform incumbent choice for `exit_style="random"`) and `_SHORT_SIGNAL_STREAM = 4` (the second short-signal noise panel). Existing simulator-family tags: market `0`, manager `1`, returns_only `2`; other in-repo tags in flagship/test modules: `7, 11, 12, 13, 14, 15, 42, 43, 98, 99`. Tags `3` and `4` collide with none and continue the simulator-family sequence (0/1/2 → 3/4). Both are registered in `tests/simulator/test_manager.py::test_rng_stream_tags_are_distinct` (the enumeration that pins them) — the only existing test this plan edits, and only to widen its distinctness set, never a numeric expectation.
- **Named constants with spec citations.** The only numeric constant introduced *inside* dial code is `S4_DISPOSITION_TRAIL_MONTHS = 3` (S4 §3.8 / §8.7), the disposition trailing-gain window. All effect magnitudes (`alpha_persistence` demo 0.5, `idio_ar1` demo 0.4, `short_information_coefficient` demo 0.06, the smoothing θ grid) are **caller-supplied**, never hardcoded in the dial. Provisional choices are flagged `# NUMERICS-GATE` inline.
- **Repo is public.** No AI-assistant/vendor brand names (the wave brief's banned-word list, any casing) anywhere in code, comments, tests, commits, or docs. No employer-internal facts, processes, or manager names. No commit trailers, and no assistant-attribution in commit messages.
- **Test invocation** always uses `-m "not slow and not network"`; **foreground commands only** (no `&`, no background jobs).
- **Model policy.** Senior implementer (generative statistical code), senior task reviewer. This plan extends the simulator only — it renders no numbers and writes no JSON — so **no numerics gate applies beyond the byte-identity invariant**. The acceptance bar is "default output unchanged + each dial recovers its known injected effect."
- **Branch:** `wave2-b2-substrate`. Conventional commits (`feat:`/`test:`/`docs:`), **no trailers**.

---

## File Structure

- `src/quant_allocator/simulator/overlays.py` (**modify**) — add `SmoothingOverlay` dataclass + `apply_smoothing_overlay(returns, overlay)` pure function (S6 §3.7). No simulator imports, no RNG.
- `src/quant_allocator/simulator/market.py` (**modify**) — add `MarketConfig.idio_ar1: float = 0.0`, its guard, and an AR(1) filter on the existing innovation draws (S4 §3.8 / §8.5).
- `src/quant_allocator/simulator/manager.py` (**modify**) — add three `ManagerConfig` fields (`alpha_persistence`, `exit_style`, `short_information_coefficient`), their guards, the two new stream-tag constants, exit-style drop helpers, the short-signal panel, and the realized-return edge. All guarded so defaults are byte-identical.
- `tests/simulator/test_overlays.py` (**modify**) — add `SmoothingOverlay` tests (identity byte-identity, autocorrelation injection, S2-unsmoother convention-inverse, guards), mirroring the `WrittenPutOverlay` test shape.
- `tests/simulator/test_market_dials.py` (**new**) — `idio_ar1` byte-identity, persistence+variance, guard. (Kept separate from the untouched `tests/simulator/test_market.py`.)
- `tests/simulator/test_manager_dials.py` (**modify**) — add `alpha_persistence`, `short_information_coefficient`, and `exit_style` dial-guard + effect + guard tests, alongside the existing `death_month`/`net_drift` tests.
- `tests/simulator/test_manager.py` (**modify, one test only**) — extend `test_rng_stream_tags_are_distinct` to register the two new tags.

**Execution order:** Task 1 (smoothing overlay — isolated new code in `overlays.py`, lands first per S6 §8.6). Task 2 (`idio_ar1` — isolated to `market.py`). Then the three `manager.py` dials in dependency order: Task 3 (`alpha_persistence` — realized-return tail, least entangled), Task 4 (`short_information_coefficient` — establishes the per-side `signals`/`short_signals` split and stream tag 4), Task 5 (`exit_style` — reuses the per-side split, adds stream tag 3). Task 6 is a no-code full-suite byte-identity verification.

---

## Automated Verification

Run after **every** task (all foreground):

```bash
uv run pytest tests/simulator -m "not slow and not network" -q
uv run pytest tests/demo_data -m "not slow and not network" -q
uv run ruff check src tests
```

The `tests/demo_data` run is the committed-JSON byte-identity guard: no dial is passed by any demo generator, so every `site/data/*.json` must regenerate unchanged.

---

## Task 1: Return-Smoothing Overlay (S6 nuisance realism)

**Files:**
- Modify: `src/quant_allocator/simulator/overlays.py`
- Test: `tests/simulator/test_overlays.py` (add tests; do not touch existing ones)

**Interfaces:**
- Consumes: a `pd.Series` of returns (e.g. `history.monthly_returns`).
- Produces:
  - `SmoothingOverlay(theta: tuple[float, float, float])` — frozen dataclass; a convex MA(2) kernel, `theta_k >= 0`, `sum(theta) = 1`.
  - `apply_smoothing_overlay(returns: pd.Series, overlay: SmoothingOverlay) -> pd.Series` — returns a new series `observed_t = θ0·r_t + θ1·r_{t-1} + θ2·r_{t-2}` (pre-sample returns treated as 0), same index and name. `theta=(1,0,0)` recovers the input exactly.

**Convention (binding, S6 §8.2):** θ uses the **same parameterization as the S2 unsmoothing stage** (`flagships/tearsheet/pipeline.py`: `x_t = θ0·e_t + θ1·e_{t-1} + θ2·e_{t-2}`, θ0 contemporaneous and dominant, `sum(θ)=1`). The pre-sample-zero edge rule makes `apply_smoothing_overlay` the exact causal inverse of that module's `_invert_ma2`, so the overlay and the house de-smoother are convention-inverses. A test pins this directly.

- [ ] **Step 1: Write the failing tests.**

Append to `tests/simulator/test_overlays.py` (keep all existing imports and tests):

```python
from quant_allocator.simulator.overlays import (
    SmoothingOverlay,
    apply_smoothing_overlay,
)
from quant_allocator.flagships.tearsheet.pipeline import _invert_ma2


def _iid_returns(n_months: int = 240, seed: int = 5) -> pd.Series:
    rng = np.random.default_rng([seed, 97])
    idx = pd.period_range("2000-01", periods=n_months, freq="M", name="month")
    return pd.Series(rng.normal(0.005, 0.02, n_months), index=idx, name="mgr")


def _lag1_autocorr(x: np.ndarray) -> float:
    c = x - x.mean()
    return float(c[1:] @ c[:-1] / (c @ c))


def test_identity_theta_recovers_input_series_byte_identical():
    base = _iid_returns()
    result = apply_smoothing_overlay(base, SmoothingOverlay(theta=(1.0, 0.0, 0.0)))
    pd.testing.assert_series_equal(result, base)


def test_smoothing_injects_positive_lag1_autocorrelation():
    base = _iid_returns()
    result = apply_smoothing_overlay(base, SmoothingOverlay(theta=(0.60, 0.25, 0.15)))
    # An iid series has ~zero lag-1 autocorr; the MA(2) kernel injects a positive one
    # (the Getmansky-Lo-Makarov illiquidity-marking confound S6 stresses).
    assert abs(_lag1_autocorr(base.to_numpy())) < 0.15
    assert _lag1_autocorr(result.to_numpy()) > 0.20


def test_recovers_injected_kernel_known_values():
    base = _iid_returns(n_months=6)
    theta = (0.60, 0.25, 0.15)
    result = apply_smoothing_overlay(base, SmoothingOverlay(theta=theta))
    r = base.to_numpy()
    expected = theta[0] * r.copy()
    expected[1:] += theta[1] * r[:-1]
    expected[2:] += theta[2] * r[:-2]
    np.testing.assert_allclose(result.to_numpy(), expected, atol=1e-12)


def test_convention_is_inverse_of_s2_unsmoother():
    # The overlay smooths; the S2 stage's causal deconvolution _invert_ma2 unsmooths.
    # On centered returns with the same theta they are exact inverses (S6 sec 8.2).
    base = _iid_returns()
    theta = np.array([0.60, 0.25, 0.15])
    centered = base - base.mean()
    smoothed = apply_smoothing_overlay(centered, SmoothingOverlay(theta=tuple(theta)))
    recovered = _invert_ma2(smoothed.to_numpy(), theta)
    np.testing.assert_allclose(recovered, centered.to_numpy(), atol=1e-9)


def test_invalid_smoothing_overlays_raise():
    base = _iid_returns(n_months=24)
    with pytest.raises(ValueError, match="sum to 1"):
        apply_smoothing_overlay(base, SmoothingOverlay(theta=(0.8, 0.1, 0.05)))
    with pytest.raises(ValueError, match="non-negative"):
        apply_smoothing_overlay(base, SmoothingOverlay(theta=(1.2, -0.1, -0.1)))
```

Run `uv run pytest tests/simulator/test_overlays.py -q` — the new tests fail on `ImportError` (symbols do not exist yet).

- [ ] **Step 2: Implement the overlay.**

Append to `src/quant_allocator/simulator/overlays.py` (below `apply_written_put_overlay`), and extend the module docstring's first paragraph to note the second overlay:

```python
_MA_SUM_TOL = 1e-9


@dataclass(frozen=True)
class SmoothingOverlay:
    """GLM-style MA(2) return-smoothing overlay (S6 spec §3.7).

    theta: the convex smoothing kernel (theta0, theta1, theta2), theta_k >= 0 and
        sum(theta) = 1, in the SAME parameterization as the S2 unsmoothing stage
        (tearsheet/pipeline.py): theta0 is the contemporaneous, dominant weight.
        theta = (1, 0, 0) recovers the input series exactly.  # NUMERICS-GATE: S6
        stress grid theta in {identity, (0.60, 0.25, 0.15)} (S6 §8.2).

    The overlay injects the lag-1/lag-2 autocorrelation that illiquidity marking
    gives real fund series (Getmansky-Lo-Makarov) — a nuisance confound, drawing
    no random numbers, so it consumes no RNG stream. With the pre-sample returns
    treated as zero it is the exact causal inverse of the S2 de-smoother's
    _invert_ma2, so overlay and de-smoother are convention-inverses.
    """

    theta: tuple[float, float, float]


def apply_smoothing_overlay(returns: pd.Series, overlay: SmoothingOverlay) -> pd.Series:
    """Apply the MA(2) smoothing kernel to a return series.

    observed_t = theta0 * r_t + theta1 * r_{t-1} + theta2 * r_{t-2},
    with pre-sample returns (t-1, t-2 < 0) treated as zero. Deterministic; RNG-free.
    """
    theta = np.asarray(overlay.theta, dtype=float)
    if np.any(theta < 0.0):
        raise ValueError(f"smoothing theta must be non-negative, got {overlay.theta}")
    if abs(float(theta.sum()) - 1.0) > _MA_SUM_TOL:
        raise ValueError(f"smoothing theta must sum to 1, got {overlay.theta} (sum {theta.sum()})")

    r = returns.to_numpy()
    observed = theta[0] * r.copy()
    observed[1:] += theta[1] * r[:-1]
    observed[2:] += theta[2] * r[:-2]
    return pd.Series(observed, index=returns.index, name=returns.name)
```

Run `uv run pytest tests/simulator/test_overlays.py -q` — all pass (existing + new).

- [ ] **Step 3: Verify and commit.** Run the *Automated Verification* block. Commit: `feat: return-smoothing MA(2) overlay for S6 nuisance realism`.

---

## Task 2: `MarketConfig.idio_ar1` — AR(1) idiosyncratic persistence (S4)

**Files:**
- Modify: `src/quant_allocator/simulator/market.py`
- Test: `tests/simulator/test_market_dials.py` (new)

**Interfaces:**
- `MarketConfig.idio_ar1: float = 0.0` — AR(1) coefficient ρ on the idiosyncratic returns. `0.0` (default) is the current byte-identical generator.
- Semantics (S4 §8.5 amendment — a filter on the **existing** innovation draws, no new RNG stream): `idio_0 = innov_0`; `idio_t = ρ·idio_{t-1} + sqrt(1-ρ²)·innov_t`, where `innov` is the exact `rng.normal(0.0, idio_monthly_vols, …)` array drawn today. Stationary marginal variance `σ_i²` is preserved; `ρ=0` gives `idio = innov` byte-identical. Guard: `|idio_ar1| < 1`.

- [ ] **Step 1: Write the failing tests.**

Create `tests/simulator/test_market_dials.py`:

```python
import numpy as np
import pandas as pd
import pytest

from quant_allocator.simulator.market import MarketConfig, simulate_market


def test_ar1_zero_is_byte_identical():
    base = simulate_market(MarketConfig(n_assets=120, n_months=60, seed=3))
    off = simulate_market(MarketConfig(n_assets=120, n_months=60, seed=3, idio_ar1=0.0))
    pd.testing.assert_frame_equal(base.idio_returns, off.idio_returns)
    pd.testing.assert_frame_equal(base.factor_returns, off.factor_returns)
    pd.testing.assert_frame_equal(base.betas, off.betas)


def test_ar1_injects_persistence_and_preserves_variance():
    rho = 0.4
    base = simulate_market(MarketConfig(n_assets=400, n_months=600, seed=3))
    dialed = simulate_market(MarketConfig(n_assets=400, n_months=600, seed=3, idio_ar1=rho))
    idio = dialed.idio_returns.to_numpy()
    ac1 = np.mean([
        (lambda c: c[1:] @ c[:-1] / (c @ c))(idio[:, j] - idio[:, j].mean())
        for j in range(idio.shape[1])
    ])
    assert abs(ac1 - rho) < 0.05
    # Stationary marginal variance preserved vs the rho=0 innovations.
    assert np.isclose(idio.std(), base.idio_returns.to_numpy().std(), rtol=0.05)


def test_ar1_out_of_band_raises():
    with pytest.raises(ValueError, match="idio_ar1"):
        simulate_market(MarketConfig(idio_ar1=1.0))
    with pytest.raises(ValueError, match="idio_ar1"):
        simulate_market(MarketConfig(idio_ar1=-1.5))
```

Run `uv run pytest tests/simulator/test_market_dials.py -q` — fails (no `idio_ar1` field / filter yet).

- [ ] **Step 2: Add the field and guard.**

In `src/quant_allocator/simulator/market.py`, add the field to `MarketConfig` (after `seed`):

```python
    seed: int = 0
    # S4 spec §3.8 / §8.5: AR(1) coefficient on idiosyncratic returns, a filter on the
    # existing innovation draws. 0.0 (default) is the byte-identical iid generator; a
    # value makes a name's idio edge persist forward. Demo S4_IDIO_AR1_DEMO = 0.4.
    idio_ar1: float = 0.0
```

At the top of `simulate_market`, add the guard before drawing:

```python
def simulate_market(config: MarketConfig) -> FactorMarket:
    if not -1.0 < config.idio_ar1 < 1.0:
        raise ValueError(f"idio_ar1 must be in (-1, 1) for stationarity, got {config.idio_ar1}")
    rng = np.random.default_rng([config.seed, _MARKET_STREAM])
```

- [ ] **Step 3: Filter the innovations.**

Replace the current `idio_returns` construction (the block that builds `idio_returns` from `rng.normal(0.0, idio_monthly_vols, …)`) with:

```python
    low, high = config.idio_annual_vol_range
    idio_monthly_vols = rng.uniform(low, high, size=config.n_assets) / np.sqrt(MONTHS_PER_YEAR)
    # Innovation draws are IDENTICAL to the iid generator (byte-identity at rho=0).
    innovations = rng.normal(0.0, idio_monthly_vols, size=(config.n_months, config.n_assets))
    idio = _apply_idio_ar1(innovations, config.idio_ar1)
    idio_returns = pd.DataFrame(idio, index=months, columns=assets)
```

Add the module-level helper (near the top, below `_MARKET_STREAM`):

```python
def _apply_idio_ar1(innovations: np.ndarray, rho: float) -> np.ndarray:
    """AR(1) filter preserving stationary marginal variance (S4 §3.8 / §8.5).

    idio_0 = innov_0 (a stationary start reusing the first draw, so no new RNG is
    consumed); idio_t = rho * idio_{t-1} + sqrt(1 - rho**2) * innov_t. rho = 0 returns
    the innovations unchanged -> byte-identical to the iid generator.
    """
    if rho == 0.0:
        return innovations
    scale = np.sqrt(1.0 - rho**2)
    idio = np.empty_like(innovations)
    idio[0] = innovations[0]
    for t in range(1, innovations.shape[0]):
        idio[t] = rho * idio[t - 1] + scale * innovations[t]
    return idio
```

Run `uv run pytest tests/simulator/test_market_dials.py -q` — passes.

- [ ] **Step 4: Verify and commit.** Run *Automated Verification*. Commit: `feat: AR(1) idio-persistence dial on MarketConfig (S4 substrate)`.

---

## Task 3: `ManagerConfig.alpha_persistence` — decaying held-name edge (S3)

**Files:**
- Modify: `src/quant_allocator/simulator/manager.py`
- Test: `tests/simulator/test_manager_dials.py` (add tests)

**Interfaces:**
- `ManagerConfig.alpha_persistence: float = 0.0` — when `>0`, each held name's realized idiosyncratic return gains a deterministic edge `alpha_persistence · side · 0.5^(age/half_life) · idio_std_name` in each held month, so a name entered on a strong signal keeps earning a decaying fraction of its entry edge (S3 §6.5). Consumes **no RNG**. `0.0` is byte-identical: the edge term is exactly zero, selection/sizing are untouched (they read the original idio), so weights *and* returns are unchanged. Guard: `alpha_persistence >= 0`.
- `idio_std_name`: the per-name idiosyncratic volatility the manager already uses to z-score signals (`market.idio_returns.std()`). Reusing it keeps the edge in the manager's existing scaling vocabulary and needs no new market field. `# NUMERICS-GATE`: idio_vol interpreted as the per-name idio std.

**Byte-identity note:** the edge enters only the *realized* returns (`monthly_returns`, `true_alpha_returns`), never the signals used to select/size. Selection uses `z` computed from the original `market.idio_returns`. So `weights` are byte-identical for any `alpha_persistence`; only the realized return series move when `>0`.

- [ ] **Step 1: Write the failing tests.**

Add to `tests/simulator/test_manager_dials.py` (keep existing imports/tests; `_market` helper already defined there):

```python
def test_alpha_persistence_zero_is_byte_identical():
    market = _market(n_months=120)
    base = simulate_manager(market, ManagerConfig(information_coefficient=0.10, seed=7))
    off = simulate_manager(
        market, ManagerConfig(information_coefficient=0.10, seed=7, alpha_persistence=0.0)
    )
    pd.testing.assert_frame_equal(base.weights, off.weights)
    pd.testing.assert_series_equal(base.true_alpha_returns, off.true_alpha_returns)
    pd.testing.assert_series_equal(base.monthly_returns, off.monthly_returns)


def test_alpha_persistence_leaves_weights_but_lifts_realized_alpha():
    market = _market(n_months=120, seed=5)
    base = simulate_manager(market, ManagerConfig(information_coefficient=0.10, seed=7))
    persist = simulate_manager(
        market, ManagerConfig(information_coefficient=0.10, seed=7, alpha_persistence=0.5)
    )
    # Selection/sizing read the ORIGINAL idio, so weights are byte-identical...
    pd.testing.assert_frame_equal(base.weights, persist.weights)
    # ...but held names now earn a side-aligned decaying edge -> more realized alpha.
    assert persist.true_alpha_returns.mean() > base.true_alpha_returns.mean()


def test_negative_alpha_persistence_raises():
    market = _market(n_months=24)
    with pytest.raises(ValueError, match="alpha_persistence"):
        simulate_manager(market, ManagerConfig(alpha_persistence=-0.1))
```

Run `uv run pytest tests/simulator/test_manager_dials.py -q` — fails.

- [ ] **Step 2: Add the field and guard.**

Add to `ManagerConfig` (after `death_month`):

```python
    # S3 spec §6.5: deterministic decaying held-name edge on realized idio.
    # 0.0 (default) is byte-identical (edge term is zero, no RNG consumed). Demo 0.5.
    alpha_persistence: float = 0.0
```

Add the guard inside `simulate_manager` (alongside the other guards, e.g. after the `death_month` guard):

```python
    if config.alpha_persistence < 0.0:
        raise ValueError(f"alpha_persistence must be >= 0, got {config.alpha_persistence}")
```

- [ ] **Step 3: Reuse the idio std and accumulate the edge in-loop.**

Change the `z` construction to name the per-asset std (byte-identical — same values):

```python
    idio_std = market.idio_returns.std()
    z = market.idio_returns / idio_std
    noise = rng.standard_normal(z.shape)
```

Before the month loop, prepare the edge accumulator only when the dial is ON:

```python
    persistence_on = config.alpha_persistence != 0.0
    if persistence_on:
        asset_pos = {name: i for i, name in enumerate(assets)}
        idio_std_arr = idio_std.to_numpy()
        idio_edge = np.zeros((len(months), len(assets)))
```

Inside the loop, **after** the block that sets `ages[name] = 0` for the new entries and before `weight_rows.append(...)`, add the guarded accumulation:

```python
        if persistence_on:
            decay = config.alpha_persistence
            hl = config.alpha_half_life_months
            for name in longs:
                col = asset_pos[name]
                idio_edge[t, col] = decay * 0.5 ** (ages[name] / hl) * idio_std_arr[col]
            for name in shorts:
                col = asset_pos[name]
                idio_edge[t, col] = -decay * 0.5 ** (ages[name] / hl) * idio_std_arr[col]
```

- [ ] **Step 4: Fold the edge into realized returns.**

Replace the two return-computation lines at the end of `simulate_manager` with a guarded branch:

```python
    if persistence_on:
        edge_df = pd.DataFrame(idio_edge, index=months, columns=assets)
        realized_idio = market.idio_returns + edge_df
        realized_asset_returns = market.asset_returns + edge_df
        monthly_returns = (weights * realized_asset_returns).sum(axis=1)
        true_alpha_returns = (weights * realized_idio).sum(axis=1)
    else:
        monthly_returns = (weights * market.asset_returns).sum(axis=1)
        true_alpha_returns = (weights * market.idio_returns).sum(axis=1)
```

(The `else` branch is the current code verbatim, guaranteeing byte-identity at the default.)

Run `uv run pytest tests/simulator/test_manager_dials.py -q` — passes.

- [ ] **Step 5: Verify and commit.** Run *Automated Verification*. Commit: `feat: alpha_persistence decaying held-name edge on ManagerConfig (S3 substrate)`.

---

## Task 4: `ManagerConfig.short_information_coefficient` — decorrelated short-signal panel (S5)

**Files:**
- Modify: `src/quant_allocator/simulator/manager.py`
- Test: `tests/simulator/test_manager_dials.py` (add tests)
- Modify: `tests/simulator/test_manager.py` (register stream tag 4 in the distinctness test only)

**Interfaces:**
- `ManagerConfig.short_information_coefficient: float | None = None` — `None` (default) keeps the single-panel behavior (both sides picked from one signal panel) and draws no new RNG: **byte-identical**. A value draws a **second, decorrelated** short-signal noise panel *after* the existing `noise` draw, under the new stream tag `_SHORT_SIGNAL_STREAM = 4`; the short side is then selected and sized on `short_ic·z + sqrt(1-short_ic²)·noise_short` (age-decayed by `alpha_half_life_months`, exactly like the long side). Guard: value in `[0, 1]`. (S5 §6.5 / §8.7.)

**Byte-identity note:** the selection is refactored to be side-aware (`signals` for the long end, `short_signals` for the short end). When `short_information_coefficient is None`, `short_signals` aliases `signals`; picking longs from the top and shorts from the bottom-of-the-remainder is identical to the current single-sort because the top-`need_long` and bottom-`need_short` slices are disjoint (`n_long + n_short <= n_assets` is guarded). The dial-guard test enforces this.

- [ ] **Step 1: Write the failing tests.**

Add to `tests/simulator/test_manager_dials.py`:

```python
def test_short_ic_none_is_byte_identical():
    market = _market(n_months=120)
    base = simulate_manager(market, ManagerConfig(information_coefficient=0.10, seed=7))
    off = simulate_manager(
        market,
        ManagerConfig(information_coefficient=0.10, seed=7, short_information_coefficient=None),
    )
    pd.testing.assert_frame_equal(base.weights, off.weights)
    pd.testing.assert_series_equal(base.true_alpha_returns, off.true_alpha_returns)


def test_short_ic_zero_makes_short_side_a_noise_basket():
    # long IC high, short IC 0 -> the SHORT sleeve earns no idiosyncratic edge while the
    # long sleeve keeps its skill. Compare the short-sleeve realized idio alpha.
    market = _market(n_months=240, seed=5)
    skilled_short = simulate_manager(
        market,
        ManagerConfig(information_coefficient=0.10, seed=7, short_information_coefficient=0.10),
    )
    noise_short = simulate_manager(
        market,
        ManagerConfig(information_coefficient=0.10, seed=7, short_information_coefficient=0.0),
    )
    short_alpha = lambda h: (h.weights.clip(upper=0.0) * market.idio_returns).sum(axis=1).mean()
    assert short_alpha(skilled_short) > short_alpha(noise_short)


def test_short_ic_draws_a_decorrelated_panel_not_the_long_one():
    # A set short IC equal to the long IC still differs from the single-panel manager,
    # because the short side now reads an INDEPENDENT noise panel (stream tag 4), not
    # the long panel -> the book changes even though the two ICs match.
    market = _market(n_months=120)
    single = simulate_manager(market, ManagerConfig(information_coefficient=0.10, seed=7))
    split = simulate_manager(
        market,
        ManagerConfig(information_coefficient=0.10, seed=7, short_information_coefficient=0.10),
    )
    assert not single.weights.equals(split.weights)


def test_short_ic_out_of_band_raises():
    market = _market(n_months=24)
    with pytest.raises(ValueError, match="short_information_coefficient"):
        simulate_manager(market, ManagerConfig(short_information_coefficient=1.5))
    with pytest.raises(ValueError, match="short_information_coefficient"):
        simulate_manager(market, ManagerConfig(short_information_coefficient=-0.1))
```

Run `uv run pytest tests/simulator/test_manager_dials.py -q` — fails.

- [ ] **Step 2: Add the stream-tag constant, the field, and the guard.**

Add the module-level constant near `_MANAGER_STREAM`:

```python
_MANAGER_STREAM = 1
# S5 spec §6.5 / §8.7: the decorrelated short-signal noise panel draws under its own
# stream tag, AFTER the main manager noise, so short_information_coefficient=None is
# byte-identical. S4's exit-random dial (Task 5) takes tag 3.
_SHORT_SIGNAL_STREAM = 4
```

Add to `ManagerConfig` (after `alpha_persistence`):

```python
    # S5 spec §6.5: separate short-side picking skill. None (default) keeps the single
    # signal panel (byte-identical, no new draws); a value draws a decorrelated short
    # panel under _SHORT_SIGNAL_STREAM and picks/sizes shorts on it. Demo 0.06.
    short_information_coefficient: float | None = None
```

Add the guard inside `simulate_manager` (after the `alpha_persistence` guard):

```python
    if config.short_information_coefficient is not None and not (
        0.0 <= config.short_information_coefficient <= 1.0
    ):
        raise ValueError(
            "short_information_coefficient must be in [0, 1] or None, got "
            f"{config.short_information_coefficient}"
        )
```

- [ ] **Step 3: Draw the short panel (guarded) before the loop.**

After `noise = rng.standard_normal(z.shape)`:

```python
    short_ic = config.short_information_coefficient
    noise_short = (
        np.random.default_rng([config.seed, _SHORT_SIGNAL_STREAM]).standard_normal(z.shape)
        if short_ic is not None
        else None
    )
```

- [ ] **Step 4: Build `short_signals` and make selection/sizing side-aware.**

Immediately after the existing `signals = pd.Series(...)` construction (the long panel), add the short panel:

```python
        if short_ic is None:
            short_signals = signals
        else:
            short_ic_eff = short_ic * 0.5 ** (age_vec.to_numpy() / config.alpha_half_life_months)
            if config.death_month is not None and t >= config.death_month:
                short_ic_eff = np.zeros_like(short_ic_eff)
            short_signals = pd.Series(
                short_ic_eff * z.iloc[t].to_numpy()
                + np.sqrt(1.0 - short_ic_eff**2) * noise_short[t],
                index=assets,
            )
```

Replace the selection block (`candidates = signals.drop(...)` … `new_shorts = ...`) with the side-aware version:

```python
        held = set(longs) | set(shorts)
        need_long = config.n_long - len(longs)
        need_short = config.n_short - len(shorts)
        long_candidates = signals.drop(index=list(held)).sort_values()
        new_longs = list(long_candidates.index[-need_long:]) if need_long else []
        short_candidates = short_signals.drop(index=list(held | set(new_longs))).sort_values()
        new_shorts = list(short_candidates.index[:need_short]) if need_short else []
        longs += new_longs
        shorts += new_shorts
        for name in (*new_longs, *new_shorts):
            ages[name] = 0
```

Change the short-side sizing to read `short_signals`:

```python
        weights.loc[longs] = _side_weights(
            longs, signals, long_total, 1.0, config.sizing_discipline
        )
        weights.loc[shorts] = _side_weights(
            shorts, short_signals, short_total, -1.0, config.sizing_discipline
        )
```

Run `uv run pytest tests/simulator/test_manager_dials.py -q` — passes.

- [ ] **Step 5: Register stream tag 4 in the distinctness test.**

In `tests/simulator/test_manager.py`, extend **only** `test_rng_stream_tags_are_distinct`:

```python
def test_rng_stream_tags_are_distinct():
    from quant_allocator.simulator import manager, market, returns_only

    tags = {
        market._MARKET_STREAM,
        manager._MANAGER_STREAM,
        returns_only._RETURNS_ONLY_STREAM,
        manager._SHORT_SIGNAL_STREAM,
    }
    assert len(tags) == 4
```

Run `uv run pytest tests/simulator/test_manager.py -q` — passes.

- [ ] **Step 6: Verify and commit.** Run *Automated Verification*. Commit: `feat: short_information_coefficient decorrelated short panel (S5 substrate)`.

---

## Task 5: `ManagerConfig.exit_style` — exit-selection dial (S4)

**Files:**
- Modify: `src/quant_allocator/simulator/manager.py`
- Test: `tests/simulator/test_manager_dials.py` (add tests)
- Modify: `tests/simulator/test_manager.py` (register stream tag 3 in the distinctness test only)

**Interfaces:**
- `ManagerConfig.exit_style: str = "age"` — which incumbents each side retires: `"age"` (default, current oldest-first replacement — **byte-identical**), `"signal"` (sell the lowest-refreshed-directional-signal incumbents — the disciplined manager), `"disposition"` (sell the largest trailing-`S4_DISPOSITION_TRAIL_MONTHS`-gain incumbents — mechanical disposition selling), `"random"` (validation-only uniform incumbent choice, consuming RNG under `_EXIT_RANDOM_STREAM = 3`). (S4 §3.8 / §8.5.)
- `S4_DISPOSITION_TRAIL_MONTHS = 3` (S4 §3.8 / §8.7) — the trailing-gain lookback for `"disposition"`.

**Directional convention:** conviction/gain is measured in the *held direction*: `side · signal` for `"signal"` (a long's edge is its signal; a short's edge is `−signal`), and `side · Σ trailing idio` for `"disposition"` (a long "wins" when its name rose; a short when it fell). Each side drops the `n_rep` weakest-conviction (`"signal"`) or largest-gain (`"disposition"`) incumbents. The exit decision is made on month-`t` information *before* the drop, using the incumbents' **real** current ages — distinct from the post-drop `signals` array (which resets dropped names to age 0 for re-selection). The `"age"` path is left literally unchanged, so its byte-identity is guaranteed.

**Disposition window (`# NUMERICS-GATE`):** trailing gain uses `market.idio_returns` over the strictly-past window `[max(0, t - trail), t)`; this idio already carries `idio_ar1`'s persistence, which is the S4 world in which disposition selling forgoes forward alpha.

- [ ] **Step 1: Write the failing tests.**

Add to `tests/simulator/test_manager_dials.py`:

```python
def test_exit_style_age_is_byte_identical():
    market = _market(n_months=120)
    base = simulate_manager(market, ManagerConfig(information_coefficient=0.10, seed=7))
    aged = simulate_manager(
        market, ManagerConfig(information_coefficient=0.10, seed=7, exit_style="age")
    )
    pd.testing.assert_frame_equal(base.weights, aged.weights)
    pd.testing.assert_series_equal(base.true_alpha_returns, aged.true_alpha_returns)


def test_active_exit_styles_change_the_book():
    market = _market(n_months=120)
    base = simulate_manager(market, ManagerConfig(information_coefficient=0.10, seed=7))
    for style in ("signal", "disposition", "random"):
        alt = simulate_manager(
            market, ManagerConfig(information_coefficient=0.10, seed=7, exit_style=style)
        )
        assert not base.weights.equals(alt.weights)


def test_exit_random_is_seed_reproducible_and_consumes_its_stream():
    market = _market(n_months=120)
    a = simulate_manager(
        market, ManagerConfig(information_coefficient=0.10, seed=7, exit_style="random")
    )
    b = simulate_manager(
        market, ManagerConfig(information_coefficient=0.10, seed=7, exit_style="random")
    )
    pd.testing.assert_frame_equal(a.weights, b.weights)  # deterministic given seed + tag
    c = simulate_manager(
        market, ManagerConfig(information_coefficient=0.10, seed=8, exit_style="random")
    )
    assert not a.weights.equals(c.weights)  # a different seed draws different exits


def test_signal_exit_beats_disposition_under_persistence():
    # S4 ground truth: under idio persistence, selling the lowest-signal incumbents
    # (disciplined) retains names whose edge still pays, while selling trailing winners
    # (disposition) forgoes forward alpha -> signal earns more realized true alpha.
    market = simulate_market(MarketConfig(n_assets=300, n_months=240, seed=5, idio_ar1=0.4))
    signal = simulate_manager(
        market, ManagerConfig(information_coefficient=0.10, seed=11, exit_style="signal")
    )
    dispo = simulate_manager(
        market, ManagerConfig(information_coefficient=0.10, seed=11, exit_style="disposition")
    )
    assert signal.true_alpha_returns.mean() > dispo.true_alpha_returns.mean()


def test_bad_exit_style_raises():
    market = _market(n_months=24)
    with pytest.raises(ValueError, match="exit_style"):
        simulate_manager(market, ManagerConfig(exit_style="bogus"))
```

The `MarketConfig` import is already present at the top of `test_manager_dials.py`. Run `uv run pytest tests/simulator/test_manager_dials.py -q` — fails.

- [ ] **Step 2: Add the stream-tag constant, the trailing constant, the field, and the guard.**

Add near the stream tags:

```python
# S4 spec §3.8 / §8.5: exit_style="random" draws uniform incumbent choices under its
# own stream tag, AFTER the main manager noise, so exit_style="age" is byte-identical.
_EXIT_RANDOM_STREAM = 3
# S4 spec §3.8 / §8.7: disposition trailing-gain lookback (months).
S4_DISPOSITION_TRAIL_MONTHS = 3
_EXIT_STYLES = ("age", "signal", "disposition", "random")
```

Add to `ManagerConfig` (after `short_information_coefficient`):

```python
    # S4 spec §3.8: which incumbents each side retires. "age" (default) is the current
    # oldest-first replacement (byte-identical). "signal"/"disposition" are the S4
    # disciplined/flawed managers; "random" is the validation-only specificity control
    # and consumes RNG under _EXIT_RANDOM_STREAM.
    exit_style: str = "age"
```

Add the guard inside `simulate_manager` (after the `short_information_coefficient` guard):

```python
    if config.exit_style not in _EXIT_STYLES:
        raise ValueError(f"exit_style must be one of {_EXIT_STYLES}, got {config.exit_style!r}")
```

- [ ] **Step 3: Add the exit-selection helpers.**

Add these module-level functions (below `_side_weights`):

```python
def _incumbent_directional_signal(
    names: list[str], sign: float, ic_base: float, half_life: float,
    ages: dict[str, int], z_row: np.ndarray, noise_row: np.ndarray, asset_pos: dict[str, int]
) -> dict[str, float]:
    """Refreshed conviction of held `names` in their held direction at month t:
    sign * (ic_eff(age) * z + sqrt(1 - ic_eff^2) * noise). Higher = stronger edge."""
    out: dict[str, float] = {}
    for name in names:
        col = asset_pos[name]
        ic_eff = ic_base * 0.5 ** (ages[name] / half_life)
        raw = ic_eff * z_row[col] + np.sqrt(1.0 - ic_eff**2) * noise_row[col]
        out[name] = sign * raw
    return out


def _incumbent_trailing_gain(
    names: list[str], sign: float, idio: np.ndarray, t: int, trail: int, asset_pos: dict[str, int]
) -> dict[str, float]:
    """Directional trailing gain over [max(0, t - trail), t): sign * sum(past idio)."""
    lo = max(0, t - trail)
    window = idio[lo:t]
    return {name: sign * float(window[:, asset_pos[name]].sum()) for name in names}
```

- [ ] **Step 4: Instantiate the exit RNG (guarded) before the loop.**

After the `noise_short` block:

```python
    exit_rng = (
        np.random.default_rng([config.seed, _EXIT_RANDOM_STREAM])
        if config.exit_style == "random"
        else None
    )
```

If `asset_pos` was not already created (it is created in Task 3 only when `persistence_on`), ensure it is available for the exit helpers by building it unconditionally before the loop:

```python
    asset_pos = {name: i for i, name in enumerate(assets)}
    idio_matrix = market.idio_returns.to_numpy()
```

(In Task 3's block, drop the now-redundant local `asset_pos = {...}` line and keep only the `idio_std_arr` / `idio_edge` allocation under `persistence_on`.)

- [ ] **Step 5: Branch the drop step on `exit_style`.**

Replace the `if t > 0:` drop block with:

```python
        if t > 0:
            if config.exit_style == "age":
                drop_long = sorted(longs, key=lambda n: (-ages[n], n))[:n_rep_long]
                drop_short = sorted(shorts, key=lambda n: (-ages[n], n))[:n_rep_short]
            elif config.exit_style == "signal":
                z_row = z.iloc[t].to_numpy()
                long_conv = _incumbent_directional_signal(
                    longs, 1.0, config.information_coefficient, config.alpha_half_life_months,
                    ages, z_row, noise[t], asset_pos,
                )
                short_ic_base = config.information_coefficient if short_ic is None else short_ic
                short_noise_row = noise[t] if short_ic is None else noise_short[t]
                short_conv = _incumbent_directional_signal(
                    shorts, -1.0, short_ic_base, config.alpha_half_life_months,
                    ages, z_row, short_noise_row, asset_pos,
                )
                drop_long = sorted(longs, key=lambda n: (long_conv[n], n))[:n_rep_long]
                drop_short = sorted(shorts, key=lambda n: (short_conv[n], n))[:n_rep_short]
            elif config.exit_style == "disposition":
                trail = S4_DISPOSITION_TRAIL_MONTHS
                long_gain = _incumbent_trailing_gain(longs, 1.0, idio_matrix, t, trail, asset_pos)
                short_gain = _incumbent_trailing_gain(shorts, -1.0, idio_matrix, t, trail, asset_pos)
                drop_long = sorted(longs, key=lambda n: (-long_gain[n], n))[:n_rep_long]
                drop_short = sorted(shorts, key=lambda n: (-short_gain[n], n))[:n_rep_short]
            else:  # "random"
                drop_long = [longs[i] for i in exit_rng.permutation(len(longs))[:n_rep_long]]
                drop_short = [shorts[i] for i in exit_rng.permutation(len(shorts))[:n_rep_short]]
            for name in (*drop_long, *drop_short):
                ages.pop(name)
            longs = [n for n in longs if n not in set(drop_long)]
            shorts = [n for n in shorts if n not in set(drop_short)]
```

The `"age"` branch is byte-identical to the current code (same `sorted(... key=(-age, name))` slice), so the default output is unchanged.

Run `uv run pytest tests/simulator/test_manager_dials.py -q` — passes.

- [ ] **Step 6: Register stream tag 3 in the distinctness test.**

Extend `test_rng_stream_tags_are_distinct` in `tests/simulator/test_manager.py` to include the exit tag (five distinct tags total):

```python
def test_rng_stream_tags_are_distinct():
    from quant_allocator.simulator import manager, market, returns_only

    tags = {
        market._MARKET_STREAM,
        manager._MANAGER_STREAM,
        returns_only._RETURNS_ONLY_STREAM,
        manager._SHORT_SIGNAL_STREAM,
        manager._EXIT_RANDOM_STREAM,
    }
    assert len(tags) == 5
```

Run `uv run pytest tests/simulator/test_manager.py -q` — passes.

- [ ] **Step 7: Verify and commit.** Run *Automated Verification*. Commit: `feat: exit_style selection dial with random-exit stream tag (S4 substrate)`.

---

## Task 6: Full-suite byte-identity verification (no code)

**Files:** none.

- [ ] **Step 1: Run the whole non-slow, non-network suite.**

```bash
uv run pytest -m "not slow and not network" -q
uv run ruff check src tests
```

Confirm: all simulator dial tests pass; the demo-data determinism tests (`tests/demo_data/*::test_byte_for_byte_determinism_and_matches_committed`) are green, proving every committed `site/data/*.json` regenerates byte-for-byte with all five defaults OFF; ruff is clean.

- [ ] **Step 2: Confirm the stream-tag registry.** Grep the simulator module for the tag constants and confirm the enumeration is `{0: market, 1: manager, 2: returns_only, 3: exit-random, 4: short-signal}` with no collisions against the flagship/test tags `{7, 11, 12, 13, 14, 15, 42, 43, 98, 99}`:

```bash
uv run python -c "from quant_allocator.simulator import market, manager, returns_only; print(sorted({market._MARKET_STREAM, manager._MANAGER_STREAM, returns_only._RETURNS_ONLY_STREAM, manager._EXIT_RANDOM_STREAM, manager._SHORT_SIGNAL_STREAM}))"
```

Expected: `[0, 1, 2, 3, 4]`.

- [ ] **Step 3: Final commit (if any doc updates).** No production code changes here; if a plan-status note is added, commit `docs: record wave2-b2 substrate verification`.
```
