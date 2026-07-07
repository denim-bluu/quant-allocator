# Wave-2 Simulator Dials Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add three small, backward-compatible, default-OFF dials to the synthetic-manager simulator so the M1/M2/M3 screens have ground-truth postures to detect: a written-put short-vol overlay (M2), a linear net-beta drift schedule (M1), and a piecewise-IC alpha-death event (M3).

**Architecture:** M2 lands as a new pure-function module `simulator/overlays.py` composed onto any return series — it imports neither simulator, draws no randomness, and is deterministic given a market-factor series. M1 and M3 are two new optional fields on the existing frozen `ManagerConfig` (`net_drift`, `death_month`), each `None` by default and each guarded so that when it is OFF the manager's code path and its RNG consumption are unchanged. No existing demo generator passes any dial argument, so every committed `site/data/*.json` regenerates byte-for-byte.

**Tech Stack:** Python 3.11+, numpy, pandas. `np.random.default_rng([seed, stream_tag])` per-module streams (market=0, manager=1, returns_only=2). pytest. ruff (line-length 100).

## Global Constraints

- **Plan review (2026-07-07): APPROVED.** One addition — the overlay's
  in-sample fair-premium convention is a deliberate look-ahead for controlled
  experiments; any atlas row built on it must state the convention in its
  methodology (a real short-vol book's premium is ex-ante). Binding on the M2
  build track.

- **Byte-identity invariant (load-bearing).** The default configuration must reproduce every existing committed output byte-for-byte. The existing simulator determinism tests (`tests/simulator/`) and the demo determinism tests (`tests/demo_data/*::test_byte_for_byte_determinism_and_matches_committed`, covering `s2_tearsheet.json`, `m5_saydo.json`, `s1_ledger.json` and the manager-derived atlas outputs) MUST stay green **untouched** — do not edit those test files. This is verified after every task by running `pytest tests/simulator tests/demo_data -q`.
- **Every dial defaults OFF.** `WrittenPutOverlay` is only ever constructed by a caller that opts in; `overlay_notional` (κ) `= 0` recovers the input series exactly. `ManagerConfig.net_drift` defaults `None`; `ManagerConfig.death_month` defaults `None`. When OFF, each new field is skipped behind an `is not None` guard and alters neither the weights nor the pre-drawn RNG arrays.
- **No new RNG streams.** All three dials are deterministic transforms of already-drawn streams (the market factor, the pre-drawn manager `noise` array) or of an input series. None draws a random number, so no new per-module stream tag is introduced and the existing tags 0/1/2 are untouched. The repo's Critical same-seed-collision history is why this is explicit: if a future variant adds stochastic jitter it must claim a fresh tag `3`; this plan does not, and states so in code comments.
- **Named constants with spec citations.** The only provisional numeric default introduced inside the dial code is the overlay's `fair_premium=True` (`M2_OVERLAY_FAIR`, M2 spec §4). All effect magnitudes (κ ranges, the `PINNED_DRIFT_EFFECT` 0.30-over-12-months walk, `DEMO_DRIFT_WALK` 0.10→0.45, the alpha-death month `k` grid) are **caller-supplied**, never hardcoded in the dial, so the X1 atlas sweeps them without editing simulator code.
- **NUMERICS-GATE flags.** Provisional choices are flagged `# NUMERICS-GATE` inline: the overlay `fair_premium` default, the strike sign/moneyness convention, and (in the plan text) the atlas magnitudes that callers will pin.
- **Model policy.** senior implementer (this is generative statistical code), senior task reviewer. No page or JSON output is produced by this plan — it extends the simulator only. Therefore **no numerics gate applies beyond the byte-identity invariant above**; there are no rendered numbers to review, and the acceptance bar is "default output unchanged + new dials recover their known injected effect."
- **Branch:** `wave2-simulator-dials`. Conventional commits, **no trailers**.

---

## File Structure

- `src/quant_allocator/simulator/overlays.py` (**new**) — `WrittenPutOverlay` dataclass + `apply_written_put_overlay(returns, market_factor, overlay)` pure function. M2 §4/§5. No simulator imports, no RNG.
- `src/quant_allocator/simulator/manager.py` (**modify**) — add `NetBetaDrift` dataclass, two optional `ManagerConfig` fields (`net_drift`, `death_month`), their guards, a `_target_net_path` helper, and two guarded lines inside the monthly loop.
- `tests/simulator/test_overlays.py` (**new**) — overlay behavior + κ=0 byte-identity + guards.
- `tests/simulator/test_manager_dials.py` (**new**) — drift + death behavior, OFF-equals-honest byte-identity, RNG-untouched proofs, guards. (Kept separate from the untouched `tests/simulator/test_manager.py`.)

Execution order: Task 1 (overlay — isolated new file, lands first per M2 §5 sequencing), then Task 2 (death dial), then Task 3 (drift dial, which edits `manager.py` after Task 2's edits are in place).

---

### Task 1: Written-Put Overlay Dial (M2 short-vol posture)

**Files:**
- Create: `src/quant_allocator/simulator/overlays.py`
- Test: `tests/simulator/test_overlays.py`

**Interfaces:**
- Consumes: nothing from other tasks. Callers pass a `pd.Series` of returns and a `pd.Series` market factor on the *same* index (e.g. `market.factor_returns["market"]` for the equity manager, or any market proxy for the returns-only archetype — M2 §5 "both can wear it").
- Produces:
  - `WrittenPutOverlay(strike_moneyness: float, overlay_notional: float, premium_annual: float = 0.0, fair_premium: bool = True)` — frozen dataclass.
  - `apply_written_put_overlay(returns: pd.Series, market_factor: pd.Series, overlay: WrittenPutOverlay) -> pd.Series` — returns a new series `returns + overlay_return`, same index and name.

- [ ] **Step 1: Write the failing tests**

Create `tests/simulator/test_overlays.py`:

```python
import numpy as np
import pandas as pd
import pytest
from scipy import stats

from quant_allocator.simulator.overlays import (
    WrittenPutOverlay,
    apply_written_put_overlay,
)


def _market_factor(n_months: int = 240, seed: int = 0) -> pd.Series:
    rng = np.random.default_rng([seed, 99])
    idx = pd.period_range("2000-01", periods=n_months, freq="M", name="month")
    # Monthly market-factor draws ~ N(0.06/12, (0.16/sqrt(12))^2), matching MarketConfig.
    return pd.Series(rng.normal(0.06 / 12.0, 0.16 / np.sqrt(12.0), n_months), index=idx)


def _returns(mkt: pd.Series, seed: int = 1) -> pd.Series:
    rng = np.random.default_rng([seed, 98])
    return pd.Series(rng.normal(0.005, 0.02, len(mkt)), index=mkt.index, name="mgr")


def test_kappa_zero_recovers_input_series_byte_identical():
    mkt = _market_factor()
    base = _returns(mkt)
    overlay = WrittenPutOverlay(strike_moneyness=1.0, overlay_notional=0.0)
    result = apply_written_put_overlay(base, mkt, overlay)
    pd.testing.assert_series_equal(result, base)


def test_fair_premium_preserves_sample_mean():
    mkt = _market_factor()
    base = _returns(mkt)
    overlay = WrittenPutOverlay(strike_moneyness=1.0, overlay_notional=0.5)
    result = apply_written_put_overlay(base, mkt, overlay)
    # Fair premium zeroes the overlay's realized sample-mean contribution exactly.
    assert np.isclose(result.mean(), base.mean(), atol=1e-12)


def test_overlay_fattens_left_tail():
    mkt = _market_factor()
    base = _returns(mkt)
    overlay = WrittenPutOverlay(strike_moneyness=1.0, overlay_notional=0.8)
    result = apply_written_put_overlay(base, mkt, overlay)
    assert result.min() < base.min()
    assert stats.skew(result.to_numpy()) < stats.skew(base.to_numpy())


def test_recovers_injected_notional():
    mkt = _market_factor()
    base = _returns(mkt)
    kappa = 0.6
    overlay = WrittenPutOverlay(strike_moneyness=1.0, overlay_notional=kappa)
    result = apply_written_put_overlay(base, mkt, overlay)
    sigma = float(mkt.std())
    strike = -1.0 * sigma
    payoff = np.maximum(strike - mkt.to_numpy(), 0.0)
    expected = base.to_numpy() + kappa * payoff.mean() - kappa * payoff
    np.testing.assert_allclose(result.to_numpy(), expected, atol=1e-12)


def test_flat_premium_when_fair_disabled():
    mkt = _market_factor()
    base = _returns(mkt)
    overlay = WrittenPutOverlay(
        strike_moneyness=1.0, overlay_notional=0.5, premium_annual=0.12, fair_premium=False
    )
    result = apply_written_put_overlay(base, mkt, overlay)
    sigma = float(mkt.std())
    payoff = np.maximum(-1.0 * sigma - mkt.to_numpy(), 0.0)
    expected = base.to_numpy() + 0.12 / 12.0 - 0.5 * payoff
    np.testing.assert_allclose(result.to_numpy(), expected, atol=1e-12)


def test_invalid_overlays_raise():
    mkt = _market_factor(n_months=24)
    base = _returns(mkt)
    with pytest.raises(ValueError, match="overlay_notional"):
        apply_written_put_overlay(base, mkt, WrittenPutOverlay(1.0, -0.1))
    with pytest.raises(ValueError, match="strike_moneyness"):
        apply_written_put_overlay(base, mkt, WrittenPutOverlay(-1.0, 0.5))
    misaligned = base.reset_index(drop=True)
    with pytest.raises(ValueError, match="share an index"):
        apply_written_put_overlay(misaligned, mkt, WrittenPutOverlay(1.0, 0.5))
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/simulator/test_overlays.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'quant_allocator.simulator.overlays'`.

- [ ] **Step 3: Write the overlay module**

Create `src/quant_allocator/simulator/overlays.py`:

```python
"""Composable return overlays that give a manager a posture the core generator lacks.

M2 spec (`docs/ideas/specs/m2-hidden-convexity-screen.md`) §4/§5: the
`WrittenPutOverlay` gives an otherwise-honest manager a short-vol posture — it
collects a steady premium and pays out on large down-moves of a reference market
factor, the return profile of a written put. The overlay is a pure, deterministic
function of a return series and a market-factor series: it draws no random numbers,
so it consumes no RNG stream (the manager/market tags 0/1/2 are untouched) and
cannot perturb the byte-identical output of any generator that does not opt in.
`overlay_notional` (kappa) = 0 recovers the input series exactly.

It is a free function, not a method on either simulator, precisely so both the
equity manager and the returns-only generator can "wear it" (M2 §5) by composing
it onto their emitted return series, without this module importing either one.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

MONTHS_PER_YEAR = 12


@dataclass(frozen=True)
class WrittenPutOverlay:
    """Short-vol overlay parameters (M2 §4).

    strike_moneyness: OTM distance of the written put below a zero market-factor
        return, in market-factor sigma units (the put pays when the factor falls
        more than this many sigma below zero).  # NUMERICS-GATE: sign/moneyness convention.
    overlay_notional: kappa, the written-put notional as a fraction of the book.
        kappa = 0 recovers the honest manager exactly.
    premium_annual: flat annual carry, used only when fair_premium is False.
    fair_premium: M2_OVERLAY_FAIR. When True (default), the premium is set so the
        overlay's realized sample-mean contribution is exactly zero: the book's
        in-sample level (Sharpe numerator) is preserved while only the left tail
        fattens.  # NUMERICS-GATE: M2_OVERLAY_FAIR default True (M2 §4).
    """

    strike_moneyness: float
    overlay_notional: float
    premium_annual: float = 0.0
    fair_premium: bool = True


def apply_written_put_overlay(
    returns: pd.Series, market_factor: pd.Series, overlay: WrittenPutOverlay
) -> pd.Series:
    """Add a written-put overlay return to a manager's return series.

    overlay_return_t = premium - kappa * max(strike - f_mkt_t, 0),
    with strike = -strike_moneyness * sigma(f_mkt). Deterministic given the inputs.
    """
    if overlay.overlay_notional < 0.0:
        raise ValueError(
            f"overlay_notional (kappa) must be >= 0, got {overlay.overlay_notional}"
        )
    if overlay.strike_moneyness < 0.0:
        raise ValueError(f"strike_moneyness must be >= 0, got {overlay.strike_moneyness}")
    if not returns.index.equals(market_factor.index):
        raise ValueError("returns and market_factor must share an index")

    sigma = float(market_factor.std())
    strike = -overlay.strike_moneyness * sigma
    payout = overlay.overlay_notional * np.maximum(strike - market_factor.to_numpy(), 0.0)

    if overlay.fair_premium:
        # Premium equal to the mean payout zeroes the overlay's realized sample-mean
        # contribution: level preserved, tail fattened (M2 §4, M2_OVERLAY_FAIR).
        premium = float(payout.mean())
    else:
        premium = overlay.premium_annual / MONTHS_PER_YEAR

    overlay_return = premium - payout
    return returns + pd.Series(overlay_return, index=returns.index, name=returns.name)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/simulator/test_overlays.py -q`
Expected: PASS (6 passed).

- [ ] **Step 5: Run ruff and the guard suite**

Run: `ruff check src/quant_allocator/simulator/overlays.py tests/simulator/test_overlays.py`
Expected: `All checks passed!`

Run: `pytest tests/simulator tests/demo_data -q`
Expected: PASS — no existing test changed (the new module is not imported by any generator, so every committed JSON is byte-identical).

- [ ] **Step 6: Commit**

```bash
git add src/quant_allocator/simulator/overlays.py tests/simulator/test_overlays.py
git commit -m "feat: add composable written-put overlay dial (M2 short-vol posture)"
```

---

### Task 2: Piecewise-IC Alpha-Death Dial (M3)

**Files:**
- Modify: `src/quant_allocator/simulator/manager.py` (add `death_month` field + guard + one guarded loop line)
- Test: `tests/simulator/test_manager_dials.py`

**Interfaces:**
- Consumes: existing `ManagerConfig`, `simulate_manager`, `ManagerHistory` from `manager.py`; `MarketConfig`, `simulate_market` from `market.py`.
- Produces:
  - `ManagerConfig.death_month: int | None = None` — M3 §4. When set, the fresh information coefficient steps to zero at this 0-based month index (alpha death); `None` (or `>= n_months`) is the honest, byte-identical manager.

- [ ] **Step 1: Write the failing tests**

Create `tests/simulator/test_manager_dials.py`:

```python
import numpy as np
import pandas as pd
import pytest

from quant_allocator.simulator.manager import ManagerConfig, simulate_manager
from quant_allocator.simulator.market import MarketConfig, simulate_market


def _market(n_months: int = 60, seed: int = 3):
    return simulate_market(MarketConfig(n_assets=300, n_months=n_months, seed=seed))


def test_death_none_matches_beyond_horizon_no_op():
    market = _market(n_months=48)
    cfg = ManagerConfig(information_coefficient=0.15, seed=7)
    honest = simulate_manager(market, cfg)
    # death at/after the horizon can never fire -> byte-identical to the honest run.
    beyond = simulate_manager(market, ManagerConfig(information_coefficient=0.15, seed=7, death_month=48))
    pd.testing.assert_frame_equal(honest.weights, beyond.weights)


def test_predeath_weights_are_byte_identical_to_honest():
    # The RNG (noise) is pre-drawn once; death only zeroes ic_eff from month k on,
    # so every month before k selects and sizes identically to the honest manager.
    market = _market(n_months=60)
    k = 30
    honest = simulate_manager(market, ManagerConfig(information_coefficient=0.15, seed=9))
    dying = simulate_manager(
        market, ManagerConfig(information_coefficient=0.15, seed=9, death_month=k)
    )
    pd.testing.assert_frame_equal(honest.weights.iloc[:k], dying.weights.iloc[:k])


def test_alpha_dies_after_death_month():
    market = _market(n_months=120, seed=5)
    k = 60
    dying = simulate_manager(
        market, ManagerConfig(information_coefficient=0.20, seed=11, death_month=k)
    )
    pre = dying.true_alpha_returns.iloc[:k].mean()
    post = dying.true_alpha_returns.iloc[k:].mean()
    assert pre > 0
    assert post < pre  # skill is gone after death; post-k alpha collapses toward zero


def test_negative_death_month_raises():
    market = _market(n_months=24)
    with pytest.raises(ValueError, match="death_month"):
        simulate_manager(market, ManagerConfig(death_month=-1))
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/simulator/test_manager_dials.py -q`
Expected: FAIL with `TypeError: ... unexpected keyword argument 'death_month'`.

- [ ] **Step 3: Add the `death_month` field to `ManagerConfig`**

In `src/quant_allocator/simulator/manager.py`, edit the `ManagerConfig` dataclass (currently ending at `seed: int = 0`) to append the field:

```python
@dataclass(frozen=True)
class ManagerConfig:
    n_long: int = 40
    n_short: int = 25
    target_gross: float = 1.6
    target_net: float = 0.2
    information_coefficient: float = 0.05
    alpha_half_life_months: float = 6.0
    sizing_discipline: float = 1.0
    rebalance_fraction: float = 0.25
    seed: int = 0
    # M3 spec §4: 0-based month at which the fresh IC steps to zero (alpha death).
    # None (default) or a value >= n_months is the honest, byte-identical manager.
    death_month: int | None = None
```

- [ ] **Step 4: Add the death-month guard**

In `simulate_manager`, immediately after the existing `if config.n_long + config.n_short > len(market.betas.index):` guard block (the last of the current guards, ending with its `)`), add:

```python
    if config.death_month is not None and config.death_month < 0:
        raise ValueError(f"death_month must be >= 0 or None, got {config.death_month}")
```

- [ ] **Step 5: Apply the death step inside the monthly loop**

In `simulate_manager`, find the line:

```python
        ic_eff = effective_information_coefficient(age_vec.to_numpy(), config)
```

and replace it with:

```python
        ic_eff = effective_information_coefficient(age_vec.to_numpy(), config)
        if config.death_month is not None and t >= config.death_month:
            # Alpha death: fresh IC -> 0, so signals collapse to pure noise (M3 §4).
            # The pre-drawn `noise` array is untouched, so death_month=None is byte-identical.
            ic_eff = np.zeros_like(ic_eff)
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `pytest tests/simulator/test_manager_dials.py -q`
Expected: PASS (4 passed).

- [ ] **Step 7: Run ruff and the byte-identity guard suite**

Run: `ruff check src/quant_allocator/simulator/manager.py tests/simulator/test_manager_dials.py`
Expected: `All checks passed!`

Run: `pytest tests/simulator tests/demo_data -q`
Expected: PASS — in particular the untouched `tests/simulator/test_manager.py` and every `test_byte_for_byte_determinism_and_matches_committed` stay green (no generator passes `death_month`, so all committed JSON is byte-identical).

- [ ] **Step 8: Commit**

```bash
git add src/quant_allocator/simulator/manager.py tests/simulator/test_manager_dials.py
git commit -m "feat: add piecewise-IC alpha-death dial to equity manager (M3)"
```

---

### Task 3: Linear Net-Beta Drift Dial (M1)

**Files:**
- Modify: `src/quant_allocator/simulator/manager.py` (add `NetBetaDrift` dataclass, `net_drift` field, guard, `_target_net_path` helper, two guarded loop lines)
- Test: `tests/simulator/test_manager_dials.py` (append)

**Interfaces:**
- Consumes: the Task-2 state of `manager.py` (`ManagerConfig` now carries `death_month`).
- Produces:
  - `NetBetaDrift(total_walk: float, ramp_months: int, onset_month: int = 0)` — frozen dataclass. M1 §4, ruled **linear schedule on `target_net`** (NOT candidate-selection tilt).
  - `ManagerConfig.net_drift: NetBetaDrift | None = None` — when set, `target_net` walks linearly from its base by `total_walk` over `ramp_months`, starting at `onset_month`, then holds. `None` is the honest, byte-identical manager. Drift rescales side totals only — it touches neither candidate selection nor the RNG.

- [ ] **Step 1: Write the failing tests**

Append to `tests/simulator/test_manager_dials.py`:

```python
from quant_allocator.simulator.manager import NetBetaDrift


def test_drift_none_matches_zero_walk_no_op():
    market = _market(n_months=48)
    honest = simulate_manager(market, ManagerConfig(information_coefficient=0.1, seed=4))
    zero_walk = simulate_manager(
        market,
        ManagerConfig(
            information_coefficient=0.1,
            seed=4,
            net_drift=NetBetaDrift(total_walk=0.0, ramp_months=12),
        ),
    )
    pd.testing.assert_frame_equal(honest.weights, zero_walk.weights)


def test_net_exposure_walks_linearly():
    market = _market(n_months=48)
    base_net = 0.10
    walk = 0.35  # DEMO_DRIFT_WALK 0.10 -> 0.45 (M1 constants table)  # NUMERICS-GATE magnitude
    ramp = 12
    hist = simulate_manager(
        market,
        ManagerConfig(
            information_coefficient=0.1,
            target_net=base_net,
            seed=4,
            net_drift=NetBetaDrift(total_walk=walk, ramp_months=ramp),
        ),
    )
    realized_net = hist.weights.sum(axis=1).to_numpy()
    t = np.arange(len(realized_net), dtype=float)
    expected_net = base_net + walk * np.clip(t / ramp, 0.0, 1.0)
    np.testing.assert_allclose(realized_net, expected_net, atol=1e-8)


def test_drift_leaves_gross_unchanged():
    market = _market(n_months=48)
    hist = simulate_manager(
        market,
        ManagerConfig(
            information_coefficient=0.1,
            target_net=0.10,
            seed=4,
            net_drift=NetBetaDrift(total_walk=0.35, ramp_months=12),
        ),
    )
    gross = hist.weights.abs().sum(axis=1)
    assert np.allclose(gross, 1.6, atol=1e-8)


def test_pre_onset_weights_are_byte_identical_to_honest():
    # Drift only rescales side totals from onset on; before onset the book is the
    # honest manager exactly (same selection, same RNG).
    market = _market(n_months=60)
    onset = 24
    honest = simulate_manager(
        market, ManagerConfig(information_coefficient=0.1, target_net=0.10, seed=8)
    )
    drifting = simulate_manager(
        market,
        ManagerConfig(
            information_coefficient=0.1,
            target_net=0.10,
            seed=8,
            net_drift=NetBetaDrift(total_walk=0.35, ramp_months=12, onset_month=onset),
        ),
    )
    pd.testing.assert_frame_equal(honest.weights.iloc[:onset], drifting.weights.iloc[:onset])


def test_drift_out_of_band_raises():
    market = _market(n_months=24)
    with pytest.raises(ValueError, match="drifted net"):
        # base 0.2 + walk 1.6 = 1.8 >= target_gross 1.6 -> short side would go non-positive.
        simulate_manager(
            market,
            ManagerConfig(seed=1, net_drift=NetBetaDrift(total_walk=1.6, ramp_months=12)),
        )


def test_drift_bad_ramp_raises():
    market = _market(n_months=24)
    with pytest.raises(ValueError, match="ramp_months"):
        simulate_manager(
            market,
            ManagerConfig(seed=1, net_drift=NetBetaDrift(total_walk=0.2, ramp_months=0)),
        )
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/simulator/test_manager_dials.py -q`
Expected: FAIL with `ImportError: cannot import name 'NetBetaDrift'`.

- [ ] **Step 3: Add the `NetBetaDrift` dataclass**

In `src/quant_allocator/simulator/manager.py`, directly above the `ManagerConfig` dataclass, add:

```python
@dataclass(frozen=True)
class NetBetaDrift:
    """Linear net-beta drift schedule on target_net (M1 spec §4, ruled linear form).

    target_net at month t = base target_net
        + total_walk * clip((t - onset_month) / ramp_months, 0, 1).
    A book with net_drift=None is the honest manager; drift rescales the long/short
    side totals only, so it changes neither candidate selection nor RNG consumption.
    """

    total_walk: float
    ramp_months: int
    onset_month: int = 0
```

- [ ] **Step 4: Add the `net_drift` field to `ManagerConfig`**

Edit the `ManagerConfig` dataclass to add `net_drift` above the Task-2 `death_month` field so both dial fields sit together:

```python
    seed: int = 0
    # M1 spec §4: linear net-beta drift schedule on target_net (None = honest manager).
    net_drift: NetBetaDrift | None = None
    # M3 spec §4: 0-based month at which the fresh IC steps to zero (alpha death).
    # None (default) or a value >= n_months is the honest, byte-identical manager.
    death_month: int | None = None
```

- [ ] **Step 5: Add the `_target_net_path` helper**

In `manager.py`, directly above `def simulate_manager(`, add:

```python
def _target_net_path(config: ManagerConfig, n_months: int) -> np.ndarray:
    """Per-month target_net. Constant (= config.target_net) when drift is OFF, so the
    honest manager is byte-identical; a linear ramp that holds at base+total_walk when ON.
    """
    if config.net_drift is None:
        return np.full(n_months, config.target_net)
    drift = config.net_drift
    t = np.arange(n_months, dtype=float)
    progress = np.clip((t - drift.onset_month) / drift.ramp_months, 0.0, 1.0)
    return config.target_net + drift.total_walk * progress
```

- [ ] **Step 6: Add the drift guard**

In `simulate_manager`, immediately after the Task-2 `death_month` guard, add:

```python
    if config.net_drift is not None:
        drift = config.net_drift
        if drift.ramp_months <= 0:
            raise ValueError(f"net_drift.ramp_months must be > 0, got {drift.ramp_months}")
        if drift.onset_month < 0:
            raise ValueError(f"net_drift.onset_month must be >= 0, got {drift.onset_month}")
        extreme_net = config.target_net + drift.total_walk
        if abs(extreme_net) >= config.target_gross:
            raise ValueError(
                f"drifted net {extreme_net} must stay within "
                f"(-target_gross, target_gross)=(-{config.target_gross}, {config.target_gross})"
            )
```

- [ ] **Step 7: Compute the net path and use it in the loop**

In `simulate_manager`, find the line that assigns the pre-drawn noise and the month index (`months = market.idio_returns.index`); directly after the `n_rep_short = round(...)` line (just before `for t in range(len(months)):`), add:

```python
    net_path = _target_net_path(config, len(months))
```

Then inside the loop, find:

```python
        long_total = (config.target_gross + config.target_net) / 2.0
        short_total = (config.target_gross - config.target_net) / 2.0
```

and replace with:

```python
        target_net_t = net_path[t]
        long_total = (config.target_gross + target_net_t) / 2.0
        short_total = (config.target_gross - target_net_t) / 2.0
```

- [ ] **Step 8: Run tests to verify they pass**

Run: `pytest tests/simulator/test_manager_dials.py -q`
Expected: PASS (10 passed — Task 2's 4 plus Task 3's 6).

- [ ] **Step 9: Run ruff and the full byte-identity guard suite**

Run: `ruff check src/quant_allocator/simulator/manager.py tests/simulator/test_manager_dials.py`
Expected: `All checks passed!`

Run: `pytest tests/simulator tests/demo_data -q`
Expected: PASS. The untouched `tests/simulator/test_manager.py::test_gross_and_net_targets_hit_every_month` still passes because `_target_net_path` returns the constant base when `net_drift is None`; every `test_byte_for_byte_determinism_and_matches_committed` stays green because no generator passes `net_drift`.

- [ ] **Step 10: Commit**

```bash
git add src/quant_allocator/simulator/manager.py tests/simulator/test_manager_dials.py
git commit -m "feat: add linear net-beta drift dial to equity manager (M1)"
```

---

## Self-Review

**1. Spec coverage.**
- M2 §4 written-put overlay (`premium_annual`, `strike_moneyness`, `overlay_notional` κ; fair premium so in-sample level is unchanged while the left tail fattens; κ=0 recovers the honest manager) → Task 1, all four parameters present, `fair_premium` implements `M2_OVERLAY_FAIR`, κ=0 byte-identity tested.
- M1 §4 "Alternative (true drift)" + ruled linear schedule on `target_net` (NOT candidate-selection tilt) → Task 3, `NetBetaDrift` is a pure linear ramp on `target_net`, rescaling side totals only; the RULED-out tilt is not built.
- M3 §4 piecewise-IC (IC steps to zero at month k) → Task 2, `death_month` zeroes fresh IC from month k.
- Global: all three default OFF and are byte-identity-verified; no new RNG stream (all deterministic transforms of pre-drawn arrays); guards mirror the existing dial-guard style; conventional commits, no trailers; branch `wave2-simulator-dials`.

**2. Placeholder scan.** No TBD/TODO/"handle edge cases"/"similar to Task N" — every step shows complete code and exact commands with expected output.

**3. Type consistency.** `WrittenPutOverlay` / `apply_written_put_overlay` signatures match between Task 1's Interfaces, code, and tests. `NetBetaDrift(total_walk, ramp_months, onset_month=0)` and `ManagerConfig.net_drift` / `.death_month` field names are identical across the dataclass definition, the guards, `_target_net_path`, the loop edits, and every test. `_target_net_path(config, n_months) -> np.ndarray` is called with `len(months)`. The loop variable `target_net_t` is defined before use.

**4. Byte-identity strategy (restate).** Each dial is inert when OFF: the overlay is a separate module no generator imports; `net_drift=None` makes `_target_net_path` return the constant base (identical side totals) and never touches RNG; `death_month=None` skips the `ic_eff` zeroing and leaves the pre-drawn `noise` array untouched. All randomness in `simulate_manager` is drawn once, up front, independent of any dial, so an OFF dial cannot shift the stream. The pre-onset / pre-death / κ=0 tests plus the untouched `test_byte_for_byte_determinism_and_matches_committed` suite prove it.

**5. Flagged constants (NUMERICS-GATE).** In-dial: overlay `fair_premium=True` (`M2_OVERLAY_FAIR`) and the strike sign/moneyness convention (`strike = -moneyness * sigma`). Caller-supplied (flagged in tests / plan text, not hardcoded in the dial): overlay κ ranges, `PINNED_DRIFT_EFFECT` (0.30 over 12 months), `DEMO_DRIFT_WALK` (0.10→0.45), and the alpha-death month `k` grid — the atlas pins these without editing simulator code.

## Execution Handoff

**Plan complete and saved to `docs/superpowers/plans/2026-07-07-wave2-simulator-dials.md`. Two execution options:**

**1. Subagent-Driven (recommended)** — dispatch a fresh subagent per task, review between tasks, fast iteration.

**2. Inline Execution** — execute tasks in this session using executing-plans, batch execution with checkpoints.

**Which approach?**
</content>
</invoke>
