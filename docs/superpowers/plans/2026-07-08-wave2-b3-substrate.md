# Wave-2 Batch-3 Shared Substrate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the gate-approved, default-OFF simulator and generator extensions the M4/M6/E3/P2 batch-3 build tracks depend on — a per-asset dollar-ADV field on `MarketConfig` (M4), a shared crowded sub-signal dial on `ManagerConfig` (M4), the pure `emit_13f_long_book` view plus its eligibility mask and non-13(f) long-share dial (M6), the shared say-do corpus generator extended to DDQs + meeting notes behind a default-off flag with a planted retrieval-eval set (E3), and an opt-in E-tier bucket-coarsening emission (P2). Every default is byte-identical to the current code, so no existing test and no committed `site/data/*.json` changes.

**Architecture:** The two M4 dials and the M6 mask/dial are optional fields on the frozen `MarketConfig`/`ManagerConfig` and two new attributes on the frozen `FactorMarket`, each guarded so that when OFF the code path *and* the RNG consumption are unchanged (the `death_month` / `net_drift` / batch-2 precedent). Only the two M4 dials consume randomness: the per-asset dollar-ADV vector draws from `np.random.default_rng([seed, _LIQUIDITY_STREAM])` and the crowded sub-signal draws from `np.random.default_rng([crowd_seed, _CROWD_STREAM])` — each a **separate generator on a new named integer stream tag**, so the main market (tag 0) and manager (tag 1) streams stay byte-identical. `emit_13f_long_book`, the eligibility mask, the E3 corpus generator, and the P2 coarsening are all **RNG-free** (the `overlays.py` discipline) and take no stream tag. The two new tags are registered in `tests/simulator/test_manager.py::test_rng_stream_tags_are_distinct`, the test that pins the simulator stream-tag enumeration.

**Tech Stack:** Python 3.11+, numpy, pandas. `np.random.default_rng([seed, stream_tag])` per-module streams. pytest (`pythonpath=["src"]`, `addopts="-m 'not network'"`). ruff line-length 100. Package/venv manager: `uv`.

## Global Constraints

- **Byte-identity invariant (load-bearing).** Every dial default reproduces the current output byte-for-byte. Each dial gets a **dial-guard test** asserting identical output at its default (the batch-2 precedent in `tests/simulator/test_manager_dials.py`: `pd.testing.assert_frame_equal` on weights, `assert_series_equal` on the return series; `assert_frame_equal` on market frames). The existing `tests/simulator/`, `tests/flagships/`, and `tests/demo_data/*::test_byte_for_byte_determinism_and_matches_committed` suites MUST stay green; do **not** edit any existing test's expected values. The **only** existing test this plan edits is `test_rng_stream_tags_are_distinct`, and only to widen its distinctness set (never a numeric expectation). Verified after every task by the *Automated Verification* block.
- **Each active dial gets a minimal effect test** — the dialed behavior moves the right statistic in the right direction (e.g. `crowd_participation>0` raises the cross-manager signal correlation toward the stated shared fraction; `noneligible_long_share>0` lowers the 13F coverage of the emitted book; coarsening rounds E-tier betas onto the `OP_BUCKET_WIDTH` grid).
- **Committed demo JSON regenerates unchanged.** No demo generator passes any new dial, and the E3 corpus generator / P2 coarsening are new code no existing demo imports, so every `site/data/*.json` (notably `site/data/m5_saydo.json`) must regenerate byte-for-byte. This is guarded by the existing `tests/demo_data/*` determinism suite, run after every task.
- **M5 corpus/eval byte-identity (explicit guard).** *This plan creates* the shared say-do corpus generator (see the conflict note below); its **flag-off (letters-only) output must be deterministic and stable** across calls, guarded by an explicit test (`test_corpus_flag_off_is_letters_only_and_deterministic`). M5's existing committed output (`site/data/m5_saydo.json`) is unaffected because `demo_data/m5_saydo.py` does not import the corpus generator — pinned by the M5 determinism guard above.
- **No `hash()`-derived seeds anywhere.** Named integer stream tags only. The two RNG-consuming dials use module-level constants `_LIQUIDITY_STREAM` (in `simulator/market.py`) and `_CROWD_STREAM` (in `simulator/manager.py`), each passed as the second element of `np.random.default_rng([seed, tag])`. The repo's same-seed-collision history is why this is explicit.
- **New stream tags (chosen, non-colliding).** `_LIQUIDITY_STREAM = 5` (per-asset dollar-ADV vector, M4) and `_CROWD_STREAM = 6` (shared crowded sub-signal, M4). TAKEN simulator-family tags are `0` (market), `1` (manager), `2` (returns_only), `3` (`_EXIT_RANDOM_STREAM`), `4` (`_SHORT_SIGNAL_STREAM`) — all batch-2, merged. Other in-repo tags (flagship/test modules): `7, 11, 12, 13, 14, 15, 42, 43, 98, 99`. Tags `5` and `6` collide with none and continue the simulator-family sequence (0–4 → 5, 6). Both are registered in `test_rng_stream_tags_are_distinct` (widened from 5 to 7 tags). **The M4 spec §6.6 proposed tags 3 and 4 are superseded** — M4 §8 ruling 3 already directs the batch-3 plan to take the next free tags against the widened registry; this plan honors that ruling with 5 and 6.
- **Named constants with spec citations.** Provisional numerics are named module-level constants, cited, and flagged `# NUMERICS-GATE`: `MARKET_ADV_RANGE` (M4 §6.3), `OP_BUCKET_WIDTH = 0.05` (P2 §6.6 / §8 ruling 4). Effect magnitudes used in tests (`crowd_participation` demo value, `ineligible_asset_fraction`, `noneligible_long_share`) are **caller-supplied**, never hardcoded in the dial. Interpretation choices (ADV draw distribution; crowd-blend variance convention; slots-vs-gross for the non-13(f) share; the authored eligibility spread) are documented inline with `# NUMERICS-GATE`.
- **Repo is public.** No AI-assistant / vendor brand names (the wave brief's banned-word list, any casing) anywhere in code, comments, tests, or the authored corpus text. No employer-internal facts, processes, or manager names. Fictional demo names only, drawn from the gate-approved rosters (E3 §8 ruling 6: Corvid Lane Capital, Selby Point Advisors, Wexford Green Capital, Elena Voss, Priya Anand). No commit trailers, no assistant-attribution in commit messages.
- **Test invocation** always uses `-m "not slow and not network"`; **foreground commands only** (no `&`, no background jobs).
- **Model policy.** Senior implementer (generative statistical + IR-substrate code), senior task reviewer. This plan renders no certified numbers and writes no new committed JSON — the acceptance bar is "default output unchanged + each dial recovers its known injected effect." Provisional constants are flagged for the numerics gate, not certified here.
- **Branch:** `wave2-b3-substrate`. Conventional commits (`feat:`/`test:`/`docs:`), **no trailers**.

### Conflict note (found against existing code — read before Task 4)

The brief and E3 §6.4 assume **M5 already ships a synthetic-corpus generator and an eval harness** that E3 extends. It does **not**. The merged M5 implementation is only `flagships/saydo/alignment.py` (the deterministic scorer) plus `demo_data/m5_saydo.py`, whose letter excerpts are **authored constants inside the demo**, not output of a shared generator. There is no `flagships/saydo/extraction.py`, no `harness.py`, and no corpus generator anywhere in the repo. Consequences, handled in this plan:

1. **Task 4 creates** the shared corpus generator (`flagships/saydo/corpus.py`) rather than extending one. Its **letters-only default is the byte-identical baseline**; the DDQ + meeting-note emitters sit behind `include_ddq_and_notes=False`. The "M5 letter corpus byte-identical" guard becomes a **flag-off determinism guard** (there is no pre-existing committed corpus output to regress against; `m5_saydo.json` is untouched, as noted above).
2. **M5's extraction `harness.py` is out of scope for this substrate plan** and remains an E3 *build-track* prerequisite. This plan delivers the corpus generator and the **planted retrieval-relevance eval set** (E3 §6.4's named substrate); it does not build the extraction harness. Flag this to the E3 build track.

---

## File Structure

- `src/quant_allocator/simulator/market.py` (**modify**) — add `_LIQUIDITY_STREAM = 5`, `MARKET_ADV_RANGE`, `MarketConfig.adv_dollar_range` + `MarketConfig.ineligible_asset_fraction`, the `adv_dollar` and `eligible` attributes on `FactorMarket`, the ADV draw (separate stream) and the authored eligibility helper. Byte-identical at defaults.
- `src/quant_allocator/simulator/manager.py` (**modify**) — add `_CROWD_STREAM = 6`, `ManagerConfig.crowd_participation` + `crowd_seed`, `ManagerConfig.noneligible_long_share`, their guards, the guarded crowd-noise blend, and the guarded ineligible-long-slot reservation. All guarded so defaults are byte-identical.
- `src/quant_allocator/simulator/tiers.py` (**modify**) — add `OP_BUCKET_WIDTH`, an `emit_tiers(..., coarsen_e_tier=False)` option that rounds the E-tier factor betas to the bucket grid; default recovers the exact current emission.
- `src/quant_allocator/flagships/holdings13f/__init__.py` + `pipeline.py` (**new**) — `emit_13f_long_book(weights, quarter_ends, eligible) -> reported_shares`, a pure RNG-free view.
- `src/quant_allocator/flagships/saydo/corpus.py` (**new**) — `Document`, `build_corpus(include_ddq_and_notes=False)`, `planted_relevance()`; authored constants, RNG-free.
- `tests/simulator/test_market_dials.py` (**modify**) — add ADV byte-identity + effect + guard tests and eligibility-mask tests.
- `tests/simulator/test_manager_dials.py` (**modify**) — add `crowd_participation` and `noneligible_long_share` dial-guard + effect + guard tests.
- `tests/simulator/test_manager.py` (**modify, one test only**) — widen `test_rng_stream_tags_are_distinct` to register tags 5 and 6.
- `tests/simulator/test_tiers.py` (**modify or new**) — add E-tier coarsening byte-identity + effect + guard tests.
- `tests/flagships/test_holdings13f.py` (**new**) — emitter tests (down-sample, longs-only, eligible-only, renormalize, RNG-free stability).
- `tests/flagships/test_saydo_corpus.py` (**new**) — flag-off determinism guard, flag-on adds DDQ/notes, planted-relevance integrity.

**Execution order:** Task 1 (M4 ADV — isolated to `market.py`, adds tag 5). Task 2 (M4 crowd — isolated to `manager.py`, adds tag 6). Task 3 (M6 — market eligibility mask + `emit_13f_long_book` + manager non-13(f) dial; groups the three M6 pieces). Task 4 (E3 corpus generator + planted eval set — isolated new module). Task 5 (P2 E-tier coarsening — `tiers.py`). Task 6 is a no-code full-suite byte-identity verification.

---

## Automated Verification

Run after **every** task (all foreground):

```bash
uv run pytest tests/simulator tests/flagships -m "not slow and not network" -q
uv run pytest tests/demo_data -m "not slow and not network" -q
uv run ruff check src tests
```

The `tests/demo_data` run is the committed-JSON byte-identity guard: no dial is passed by any demo generator, so every `site/data/*.json` must regenerate unchanged.

---

## Task 1: `MarketConfig.adv_dollar_range` — per-asset dollar ADV (M4 substrate)

**Files:**
- Modify: `src/quant_allocator/simulator/market.py`
- Test: `tests/simulator/test_market_dials.py` (add tests)
- Modify: `tests/simulator/test_manager.py` (register tag 5 in the distinctness test only)

**Interfaces:**
- `MarketConfig.adv_dollar_range: tuple[float, float] = MARKET_ADV_RANGE` — the per-asset dollar average-daily-volume range (M4 §3.4 liquidity input). Drawn **log-uniformly** across the range so the vector spans the orders of magnitude a real equity universe shows. `# NUMERICS-GATE`: both the range `MARKET_ADV_RANGE` and the log-uniform draw shape are provisional (M4 §6.3 / §8 ruling 5).
- `FactorMarket.adv_dollar: pd.Series` — per-asset dollar ADV, indexed by asset. Always computed (cheap) so the attribute is uniform across markets; a build that never reads it is unaffected.
- **Byte-identity mechanism:** the ADV vector draws from a **separate generator** `np.random.default_rng([config.seed, _LIQUIDITY_STREAM])`, never touching the stream-0 `rng`. Every existing stream-0 draw (factors, betas, idio vols, innovations) is therefore byte-identical regardless of the new draw. `MARKET_ADV_RANGE = (2e6, 5e8)`.

- [ ] **Step 1: Write the failing tests.**

Add to `tests/simulator/test_market_dials.py` (keep existing imports/tests):

```python
def test_adv_dollar_is_byte_identical_to_pre_adv_generator():
    # The ADV vector draws on its own stream, so every stream-0 frame is unchanged.
    base = simulate_market(MarketConfig(n_assets=120, n_months=60, seed=3))
    explicit = simulate_market(
        MarketConfig(n_assets=120, n_months=60, seed=3, adv_dollar_range=(2e6, 5e8))
    )
    pd.testing.assert_frame_equal(base.idio_returns, explicit.idio_returns)
    pd.testing.assert_frame_equal(base.factor_returns, explicit.factor_returns)
    pd.testing.assert_frame_equal(base.betas, explicit.betas)


def test_adv_dollar_range_does_not_perturb_the_market_stream():
    # A different ADV range must not move any stream-0 draw (separate generator).
    wide = simulate_market(MarketConfig(n_assets=120, n_months=60, seed=3))
    narrow = simulate_market(
        MarketConfig(n_assets=120, n_months=60, seed=3, adv_dollar_range=(1e7, 1e7))
    )
    pd.testing.assert_frame_equal(wide.idio_returns, narrow.idio_returns)


def test_adv_dollar_is_within_range_and_seed_reproducible():
    m = simulate_market(MarketConfig(n_assets=400, n_months=12, seed=3))
    adv = m.adv_dollar
    assert list(adv.index) == list(m.betas.index)
    assert (adv >= 2e6).all() and (adv <= 5e8).all()
    again = simulate_market(MarketConfig(n_assets=400, n_months=12, seed=3))
    pd.testing.assert_series_equal(adv, again.adv_dollar)


def test_adv_dollar_range_out_of_band_raises():
    with pytest.raises(ValueError, match="adv_dollar_range"):
        simulate_market(MarketConfig(adv_dollar_range=(5e8, 2e6)))  # low > high
    with pytest.raises(ValueError, match="adv_dollar_range"):
        simulate_market(MarketConfig(adv_dollar_range=(-1.0, 5e8)))  # non-positive
```

Run `uv run pytest tests/simulator/test_market_dials.py -q` — fails (no field / attribute yet).

- [ ] **Step 2: Add the constant, the stream tag, and the config field.**

In `src/quant_allocator/simulator/market.py`, below `_MARKET_STREAM = 0`:

```python
# M4 spec §6.6 / §8 ruling 5: the per-asset dollar-ADV vector draws on its OWN stream tag,
# a separate generator from the stream-0 market draws, so every existing draw is
# byte-identical and a build that never reads adv_dollar is unaffected. Simulator-family
# tags 0-4 are taken (market/manager/returns_only/exit-random/short-signal, batch-2).
_LIQUIDITY_STREAM = 5
# M4 spec §6.3 (NUMERICS-GATE): provisional per-asset dollar average-daily-volume range,
# spanning microcap-to-megacap. Drawn log-uniformly (see _draw_adv_dollar).
MARKET_ADV_RANGE = (2e6, 5e8)
```

Add the field to `MarketConfig` (after `idio_ar1`):

```python
    # M4 spec §3.4 / §6.6: per-asset dollar ADV range for the liquidity lens. Drawn on
    # _LIQUIDITY_STREAM (separate generator) so it is byte-identical to the pre-ADV
    # market. NUMERICS-GATE: MARKET_ADV_RANGE and the log-uniform draw are provisional.
    adv_dollar_range: tuple[float, float] = MARKET_ADV_RANGE
```

- [ ] **Step 3: Add the draw helper and the guard, and store the attribute.**

Add the module-level helper (below `_apply_idio_ar1`):

```python
def _draw_adv_dollar(assets: pd.Index, adv_range: tuple[float, float], seed: int) -> pd.Series:
    """Per-asset dollar ADV, log-uniform over adv_range (M4 §3.4). Drawn on a SEPARATE
    generator (_LIQUIDITY_STREAM) so the stream-0 market draws stay byte-identical."""
    low, high = adv_range
    liq_rng = np.random.default_rng([seed, _LIQUIDITY_STREAM])
    log_adv = liq_rng.uniform(np.log(low), np.log(high), size=len(assets))
    return pd.Series(np.exp(log_adv), index=assets, name="adv_dollar")
```

Add the `FactorMarket` attribute (after `idio_returns`):

```python
    idio_returns: pd.DataFrame
    adv_dollar: pd.Series
```

Add the guard at the top of `simulate_market` (after the `idio_ar1` guard):

```python
    low, high = config.adv_dollar_range
    if not (0.0 < low <= high):
        raise ValueError(
            f"adv_dollar_range must be (low, high) with 0 < low <= high, got {config.adv_dollar_range}"
        )
```

At the return of `simulate_market`, compute and pass the attribute (the stream-0 `rng` draws are untouched; the ADV draw uses its own generator via the helper):

```python
    adv_dollar = _draw_adv_dollar(assets, config.adv_dollar_range, config.seed)
    return FactorMarket(
        config=config,
        betas=betas,
        factor_returns=factor_returns,
        idio_returns=idio_returns,
        adv_dollar=adv_dollar,
    )
```

Run `uv run pytest tests/simulator/test_market_dials.py -q` — passes.

- [ ] **Step 4: Register stream tag 5 in the distinctness test.**

In `tests/simulator/test_manager.py`, widen **only** `test_rng_stream_tags_are_distinct` (do not touch any other test):

```python
def test_rng_stream_tags_are_distinct():
    from quant_allocator.simulator import manager, market, returns_only

    tags = {
        market._MARKET_STREAM,
        manager._MANAGER_STREAM,
        returns_only._RETURNS_ONLY_STREAM,
        manager._SHORT_SIGNAL_STREAM,
        manager._EXIT_RANDOM_STREAM,
        market._LIQUIDITY_STREAM,
    }
    assert len(tags) == 6
```

Run `uv run pytest tests/simulator/test_manager.py -q` — passes.

- [ ] **Step 5: Verify and commit.** Run *Automated Verification*. Commit: `feat: per-asset dollar-ADV field on MarketConfig (M4 substrate)`.

---

## Task 2: `ManagerConfig.crowd_participation` — shared crowded sub-signal (M4 substrate)

**Files:**
- Modify: `src/quant_allocator/simulator/manager.py`
- Test: `tests/simulator/test_manager_dials.py` (add tests)
- Modify: `tests/simulator/test_manager.py` (register tag 6 in the distinctness test only)

**Interfaces:**
- `ManagerConfig.crowd_participation: float = 0.0` — the fraction of the manager's fresh-signal **noise variance** that comes from a common crowded sub-signal. `0.0` (default) draws no crowd RNG and is **byte-identical**. Guard: `0.0 <= crowd_participation <= 1.0`.
- `ManagerConfig.crowd_seed: int = 0` — the seed of the **shared** crowd generator. Managers that share `crowd_seed` draw the *same* crowded sub-signal, so their books become correlated by a known ground-truth fraction (M4 §6.4 gate 1). Ignored when `crowd_participation == 0.0`.
- **Mechanism (byte-identical at 0.0):** after the existing `noise = rng.standard_normal(z.shape)` draw, when `crowd_participation > 0` draw `crowd_noise` from `np.random.default_rng([crowd_seed, _CROWD_STREAM])` and replace `noise` with the variance-preserving convex blend `sqrt(1 - c) * noise + sqrt(c) * crowd_noise`. At `c = 0` the branch is skipped, `noise` is untouched, and the crowd generator is never constructed → byte-identical. `# NUMERICS-GATE`: `crowd_participation` is defined as the shared **variance** fraction (matching the existing `ic*z + sqrt(1-ic^2)*noise` idiom); the alternative amplitude-fraction reading is flagged. The blend contaminates the primary signal panel only; whether it also contaminates the decorrelated short panel (`_SHORT_SIGNAL_STREAM`) is left uncontaminated in v1 and flagged.

- [ ] **Step 1: Write the failing tests.**

Add to `tests/simulator/test_manager_dials.py` (the `_market` helper and imports already exist):

```python
def test_crowd_participation_zero_is_byte_identical():
    market = _market(n_months=120)
    base = simulate_manager(market, ManagerConfig(information_coefficient=0.10, seed=7))
    off = simulate_manager(
        market, ManagerConfig(information_coefficient=0.10, seed=7, crowd_participation=0.0)
    )
    pd.testing.assert_frame_equal(base.weights, off.weights)
    pd.testing.assert_series_equal(base.true_alpha_returns, off.true_alpha_returns)
    pd.testing.assert_series_equal(base.monthly_returns, off.monthly_returns)


def test_crowd_participation_shared_seed_correlates_two_managers():
    # Two managers on the same market, same crowd_seed, high participation: their books
    # overlap far more than two independent managers (the ground-truth crowding M4 reads).
    market = _market(n_months=240, seed=5)
    indep_a = simulate_manager(market, ManagerConfig(information_coefficient=0.10, seed=1))
    indep_b = simulate_manager(market, ManagerConfig(information_coefficient=0.10, seed=2))
    crowd_a = simulate_manager(
        market,
        ManagerConfig(information_coefficient=0.10, seed=1, crowd_participation=0.8, crowd_seed=99),
    )
    crowd_b = simulate_manager(
        market,
        ManagerConfig(information_coefficient=0.10, seed=2, crowd_participation=0.8, crowd_seed=99),
    )

    def held_overlap(x, y):  # mean fraction of long names co-held month by month
        lx = x.weights > 0.0
        ly = y.weights > 0.0
        both = (lx & ly).sum(axis=1)
        either = (lx | ly).sum(axis=1).replace(0, np.nan)
        return float((both / either).mean())

    assert held_overlap(crowd_a, crowd_b) > held_overlap(indep_a, indep_b)


def test_crowd_participation_changes_the_book_but_not_the_stream_of_others():
    market = _market(n_months=120)
    base = simulate_manager(market, ManagerConfig(information_coefficient=0.10, seed=7))
    crowded = simulate_manager(
        market,
        ManagerConfig(information_coefficient=0.10, seed=7, crowd_participation=0.5, crowd_seed=1),
    )
    assert not base.weights.equals(crowded.weights)


def test_crowd_participation_out_of_band_raises():
    market = _market(n_months=24)
    with pytest.raises(ValueError, match="crowd_participation"):
        simulate_manager(market, ManagerConfig(crowd_participation=1.5))
    with pytest.raises(ValueError, match="crowd_participation"):
        simulate_manager(market, ManagerConfig(crowd_participation=-0.1))
```

Run `uv run pytest tests/simulator/test_manager_dials.py -q` — fails.

- [ ] **Step 2: Add the stream tag, the fields, and the guard.**

Add the module-level constant near the other stream tags in `manager.py`:

```python
# M4 spec §6.6 / §8 ruling 3: the shared crowded sub-signal draws under its OWN stream tag,
# from a crowd_seed shared across participating managers, AFTER the main manager noise, so
# crowd_participation=0.0 is byte-identical. Tags 0-4 taken; ADV took 5 (market.py).
_CROWD_STREAM = 6
```

Add the fields to `ManagerConfig` (after `exit_style`):

```python
    # M4 spec §6.6: fraction of fresh-signal NOISE VARIANCE drawn from a crowded sub-signal
    # shared (via crowd_seed) across participating managers. 0.0 (default) draws no crowd
    # RNG and is byte-identical. NUMERICS-GATE: variance-fraction convention; short panel
    # left uncontaminated in v1.
    crowd_participation: float = 0.0
    # M4 spec §6.6: seed of the SHARED crowd generator; managers sharing it draw the same
    # crowded sub-signal. Ignored when crowd_participation == 0.0.
    crowd_seed: int = 0
```

Add the guard inside `simulate_manager` (after the `exit_style` guard):

```python
    if not 0.0 <= config.crowd_participation <= 1.0:
        raise ValueError(
            f"crowd_participation must be in [0, 1], got {config.crowd_participation}"
        )
```

- [ ] **Step 3: Blend the crowd sub-signal into the noise panel (guarded).**

Immediately after `noise = rng.standard_normal(z.shape)`:

```python
    if config.crowd_participation > 0.0:
        c = config.crowd_participation
        crowd_noise = np.random.default_rng(
            [config.crowd_seed, _CROWD_STREAM]
        ).standard_normal(z.shape)
        # Variance-preserving convex blend: a share c of the noise variance is the shared
        # crowded sub-signal, so participating managers correlate by a known fraction.
        noise = np.sqrt(1.0 - c) * noise + np.sqrt(c) * crowd_noise
```

Because the blend reassigns `noise` before the month loop, every downstream use (`signals`, the `"signal"` exit conviction) reads the crowded panel; at `c = 0.0` the branch is skipped and `noise` is the exact pre-drawn array → byte-identical.

Run `uv run pytest tests/simulator/test_manager_dials.py -q` — passes.

- [ ] **Step 4: Register stream tag 6 in the distinctness test.**

Widen `test_rng_stream_tags_are_distinct` in `tests/simulator/test_manager.py` to seven distinct tags:

```python
def test_rng_stream_tags_are_distinct():
    from quant_allocator.simulator import manager, market, returns_only

    tags = {
        market._MARKET_STREAM,
        manager._MANAGER_STREAM,
        returns_only._RETURNS_ONLY_STREAM,
        manager._SHORT_SIGNAL_STREAM,
        manager._EXIT_RANDOM_STREAM,
        market._LIQUIDITY_STREAM,
        manager._CROWD_STREAM,
    }
    assert len(tags) == 7
```

Run `uv run pytest tests/simulator/test_manager.py -q` — passes.

- [ ] **Step 5: Verify and commit.** Run *Automated Verification*. Commit: `feat: crowd_participation shared-subsignal dial with crowd stream tag (M4 substrate)`.

---

## Task 3: M6 substrate — 13F emitter + eligibility mask + non-13(f) long-share dial

**Files:**
- Modify: `src/quant_allocator/simulator/market.py` (authored eligibility mask + `FactorMarket.eligible`)
- Modify: `src/quant_allocator/simulator/manager.py` (`noneligible_long_share` dial)
- New: `src/quant_allocator/flagships/holdings13f/__init__.py`, `src/quant_allocator/flagships/holdings13f/pipeline.py`
- Test: `tests/simulator/test_market_dials.py`, `tests/simulator/test_manager_dials.py`, `tests/flagships/test_holdings13f.py` (new)

**Interfaces:**
- `MarketConfig.ineligible_asset_fraction: float = 0.0` — the authored fraction of the asset universe that is **not** 13(f)-eligible. `0.0` (default) → all eligible. **Deterministic authored assignment, no RNG** (M6 §8 ruling 5): an evenly-spread mask, so eligibility does not correlate with the (index-ordered but random-valued) betas. Guard: `0.0 <= ineligible_asset_fraction < 1.0`.
- `FactorMarket.eligible: pd.Series` — per-asset boolean 13(f)-eligibility, indexed by asset. Always attached; RNG-free, so it carries no byte-identity risk.
- `emit_13f_long_book(weights, quarter_ends, eligible) -> pd.DataFrame` — the pure view: for each quarter-end month take the snapshot, clip to longs (`max(w, 0)`), mask to eligible names, renormalize to shares summing to 1 over the survivors (a quarter of all-zero survivors renormalizes to all zeros). Indexed by quarter-end month × asset. **RNG-free, no stream tag** (the `overlays.py` discipline).
- `ManagerConfig.noneligible_long_share: float = 0.0` — the target fraction of the manager's **long slots** placed in ineligible names, so its 13F coverage drops below 1. `0.0` (default) reserves no slots → selection identical → **byte-identical**. Reads `market.eligible`. Guard: `0.0 <= noneligible_long_share <= 1.0`. `# NUMERICS-GATE`: slots-fraction (implemented) vs gross-fraction; the target-count rounding; shorts untouched (13F is longs-only).

- [ ] **Step 1: Write the failing tests (eligibility mask + emitter).**

Add to `tests/simulator/test_market_dials.py`:

```python
def test_eligible_default_is_all_true_and_byte_identical():
    base = simulate_market(MarketConfig(n_assets=120, n_months=24, seed=3))
    explicit = simulate_market(
        MarketConfig(n_assets=120, n_months=24, seed=3, ineligible_asset_fraction=0.0)
    )
    assert base.eligible.all()
    assert list(base.eligible.index) == list(base.betas.index)
    pd.testing.assert_frame_equal(base.idio_returns, explicit.idio_returns)
    pd.testing.assert_series_equal(base.eligible, explicit.eligible)


def test_eligible_fraction_marks_expected_count_deterministically():
    m = simulate_market(MarketConfig(n_assets=100, n_months=12, seed=3, ineligible_asset_fraction=0.3))
    assert (~m.eligible).sum() == 30
    again = simulate_market(
        MarketConfig(n_assets=100, n_months=12, seed=3, ineligible_asset_fraction=0.3)
    )
    pd.testing.assert_series_equal(m.eligible, again.eligible)
    # A different eligibility fraction must not perturb the stream-0 market draws.
    pd.testing.assert_frame_equal(m.idio_returns, again.idio_returns)


def test_ineligible_fraction_out_of_band_raises():
    with pytest.raises(ValueError, match="ineligible_asset_fraction"):
        simulate_market(MarketConfig(ineligible_asset_fraction=1.0))
    with pytest.raises(ValueError, match="ineligible_asset_fraction"):
        simulate_market(MarketConfig(ineligible_asset_fraction=-0.1))
```

Create `tests/flagships/test_holdings13f.py`:

```python
import numpy as np
import pandas as pd

from quant_allocator.flagships.holdings13f.pipeline import emit_13f_long_book


def _panel():
    months = pd.period_range("2024-01", periods=6, freq="M", name="month")
    assets = pd.Index([f"A{i}" for i in range(4)], name="asset")
    # A0,A1 long; A2 short; A3 long. Quarter-ends: 2024-03, 2024-06.
    data = np.tile([0.4, 0.2, -0.3, 0.1], (6, 1))
    return pd.DataFrame(data, index=months, columns=assets)


def test_longs_only_and_renormalized_to_shares():
    weights = _panel()
    eligible = pd.Series(True, index=weights.columns)
    q = pd.period_range("2024-03", periods=2, freq="3M")
    book = emit_13f_long_book(weights, q, eligible)
    # short A2 dropped; longs 0.4/0.2/0.1 renormalize to 4/7, 2/7, 1/7.
    row = book.loc[book.index[0]]
    assert row["A2"] == 0.0
    np.testing.assert_allclose(row[["A0", "A1", "A3"]].to_numpy(), [4 / 7, 2 / 7, 1 / 7])
    assert np.isclose(row.sum(), 1.0)


def test_ineligible_names_are_cropped_before_renormalization():
    weights = _panel()
    eligible = pd.Series([True, True, True, False], index=weights.columns)  # A3 ineligible
    q = pd.period_range("2024-03", periods=1, freq="3M")
    book = emit_13f_long_book(weights, q, eligible)
    row = book.loc[book.index[0]]
    assert row["A3"] == 0.0
    np.testing.assert_allclose(row[["A0", "A1"]].to_numpy(), [4 / 6, 2 / 6])


def test_emitter_is_deterministic_and_rng_free():
    weights = _panel()
    eligible = pd.Series(True, index=weights.columns)
    q = pd.period_range("2024-03", periods=2, freq="3M")
    pd.testing.assert_frame_equal(
        emit_13f_long_book(weights, q, eligible), emit_13f_long_book(weights, q, eligible)
    )
```

Run both — fail (no field / module yet).

- [ ] **Step 2: Add the eligibility mask on the market.**

In `market.py`, add the authored helper (below `_draw_adv_dollar`):

```python
def _authored_eligible_mask(assets: pd.Index, ineligible_fraction: float) -> pd.Series:
    """Deterministic authored 13(f)-eligibility mask (M6 §8 ruling 5): no RNG. Marks an
    evenly-SPREAD set of positions ineligible so eligibility does not correlate with the
    index-ordered betas. NUMERICS-GATE: the spread rule and fraction are provisional."""
    n = len(assets)
    n_ineligible = round(ineligible_fraction * n)
    eligible = np.ones(n, dtype=bool)
    if n_ineligible > 0:
        stride = n / n_ineligible
        positions = (np.arange(n_ineligible) * stride).astype(int)
        eligible[positions] = False
    return pd.Series(eligible, index=assets, name="eligible")
```

Add the field to `MarketConfig` (after `adv_dollar_range`):

```python
    # M6 spec §6.6 / §8 ruling 5: authored fraction of the universe that is NOT 13(f)-
    # eligible. 0.0 (default) -> all eligible. Deterministic authored assignment, no RNG.
    ineligible_asset_fraction: float = 0.0
```

Add the `FactorMarket` attribute (after `adv_dollar`):

```python
    adv_dollar: pd.Series
    eligible: pd.Series
```

Add the guard (after the `adv_dollar_range` guard):

```python
    if not 0.0 <= config.ineligible_asset_fraction < 1.0:
        raise ValueError(
            f"ineligible_asset_fraction must be in [0, 1), got {config.ineligible_asset_fraction}"
        )
```

Compute and pass it in the return:

```python
    eligible = _authored_eligible_mask(assets, config.ineligible_asset_fraction)
    return FactorMarket(
        config=config,
        betas=betas,
        factor_returns=factor_returns,
        idio_returns=idio_returns,
        adv_dollar=adv_dollar,
        eligible=eligible,
    )
```

Run `uv run pytest tests/simulator/test_market_dials.py -q` — eligibility tests pass.

- [ ] **Step 3: Implement the 13F emitter.**

Create `src/quant_allocator/flagships/holdings13f/__init__.py`:

```python
"""M6 13F long-book intelligence. pipeline.py is the pure RNG-free emitter/descriptor layer."""
```

Create `src/quant_allocator/flagships/holdings13f/pipeline.py`:

```python
"""M6 §3.3 13F emitter: a pure, deterministic view over a signed-weight panel.

emit_13f_long_book down-samples to quarter-ends, crops to longs and 13(f)-eligible names,
and renormalizes the survivors to reported market-value shares. It draws no random numbers
and consumes no RNG stream tag (the overlays.py discipline, M6 §6.6), so a manager never
viewed through it is byte-identical to one who is.
"""

from __future__ import annotations

import pandas as pd


def emit_13f_long_book(
    weights: pd.DataFrame, quarter_ends: pd.PeriodIndex, eligible: pd.Series
) -> pd.DataFrame:
    """Reported long-book shares per quarter (M6 §3.3).

    weights: month x asset signed portfolio weights.
    quarter_ends: the months to snapshot (the last business month of each quarter).
    eligible: per-asset boolean 13(f)-eligibility, indexed like weights.columns.

    Returns a quarter_end x asset frame of shares that sum to 1 over the visible names in
    each quarter (a quarter with no visible long renormalizes to all zeros).
    """
    eligible_aligned = eligible.reindex(weights.columns).fillna(False).to_numpy()
    snapshots = weights.loc[quarter_ends]
    longs = snapshots.clip(lower=0.0)
    visible = longs.where(pd.Series(eligible_aligned, index=weights.columns), other=0.0)
    totals = visible.sum(axis=1)
    shares = visible.div(totals.where(totals != 0.0), axis=0).fillna(0.0)
    shares.index.name = "quarter_end"
    shares.columns.name = "asset"
    return shares
```

Run `uv run pytest tests/flagships/test_holdings13f.py -q` — passes.

- [ ] **Step 4: Write the failing tests (non-13(f) long-share dial).**

Add to `tests/simulator/test_manager_dials.py`:

```python
from quant_allocator.flagships.holdings13f.pipeline import emit_13f_long_book


def _quarter_ends(index):
    return index[2::3]  # every third month, mirroring quarter-end down-sampling


def test_noneligible_long_share_zero_is_byte_identical():
    market = simulate_market(
        MarketConfig(n_assets=300, n_months=120, seed=3, ineligible_asset_fraction=0.3)
    )
    base = simulate_manager(market, ManagerConfig(information_coefficient=0.10, seed=7))
    off = simulate_manager(
        market, ManagerConfig(information_coefficient=0.10, seed=7, noneligible_long_share=0.0)
    )
    pd.testing.assert_frame_equal(base.weights, off.weights)
    pd.testing.assert_series_equal(base.monthly_returns, off.monthly_returns)


def test_noneligible_long_share_lowers_13f_coverage():
    market = simulate_market(
        MarketConfig(n_assets=300, n_months=120, seed=3, ineligible_asset_fraction=0.3)
    )
    visible_mgr = simulate_manager(market, ManagerConfig(information_coefficient=0.10, seed=7))
    hidden_mgr = simulate_manager(
        market, ManagerConfig(information_coefficient=0.10, seed=7, noneligible_long_share=0.5)
    )
    q = _quarter_ends(market.idio_returns.index)

    def mean_coverage(history):
        longs = history.weights.loc[q].clip(lower=0.0)
        visible = longs.where(market.eligible, other=0.0)
        return float((visible.sum(axis=1) / longs.sum(axis=1)).mean())

    assert mean_coverage(hidden_mgr) < mean_coverage(visible_mgr)


def test_noneligible_long_share_out_of_band_raises():
    market = _market(n_months=24)
    with pytest.raises(ValueError, match="noneligible_long_share"):
        simulate_manager(market, ManagerConfig(noneligible_long_share=1.5))
    with pytest.raises(ValueError, match="noneligible_long_share"):
        simulate_manager(market, ManagerConfig(noneligible_long_share=-0.1))
```

Run `uv run pytest tests/simulator/test_manager_dials.py -q` — fails.

- [ ] **Step 5: Add the dial field, guard, and guarded ineligible-slot reservation.**

Add to `ManagerConfig` (after `crowd_seed`):

```python
    # M6 spec §6.6: target fraction of long SLOTS placed in ineligible names, so 13F
    # coverage drops below 1. 0.0 (default) reserves no slots -> byte-identical. Reads
    # market.eligible. NUMERICS-GATE: slots-fraction (not gross); rounding; shorts untouched.
    noneligible_long_share: float = 0.0
```

Add the guard (after the `crowd_participation` guard):

```python
    if not 0.0 <= config.noneligible_long_share <= 1.0:
        raise ValueError(
            f"noneligible_long_share must be in [0, 1], got {config.noneligible_long_share}"
        )
```

Replace the current new-long selection line inside the month loop —

```python
        long_candidates = signals.drop(index=list(held)).sort_values()
        new_longs = list(long_candidates.index[-need_long:]) if need_long else []
```

— with a guarded split (the `else` branch is the current code verbatim, guaranteeing byte-identity at the default):

```python
        if config.noneligible_long_share > 0.0 and need_long:
            eligible_mask = market.eligible
            n_inelig_held = sum(1 for name in longs if not eligible_mask[name])
            n_inelig_target = round(config.noneligible_long_share * config.n_long)
            need_inelig = max(0, min(need_long, n_inelig_target - n_inelig_held))
            inelig_cands = signals[~eligible_mask].drop(index=list(held)).sort_values()
            new_inelig = list(inelig_cands.index[-need_inelig:]) if need_inelig else []
            picked = held | set(new_inelig)
            need_elig = need_long - len(new_inelig)
            elig_cands = signals[eligible_mask].drop(index=list(picked)).sort_values()
            new_longs = (new_inelig + list(elig_cands.index[-need_elig:])) if need_elig else new_inelig
        else:
            long_candidates = signals.drop(index=list(held)).sort_values()
            new_longs = list(long_candidates.index[-need_long:]) if need_long else []
```

Run `uv run pytest tests/simulator/test_manager_dials.py -q` — passes.

- [ ] **Step 6: Verify and commit.** Run *Automated Verification*. Commit: `feat: 13F emitter, eligibility mask, and non-13(f) long-share dial (M6 substrate)`.

---

## Task 4: E3 substrate — shared say-do corpus generator + planted retrieval-eval set

**Files:**
- New: `src/quant_allocator/flagships/saydo/corpus.py`
- Test: `tests/flagships/test_saydo_corpus.py` (new)

**Conflict-aware scope (see the Conflict note in Global Constraints):** M5 ships no corpus generator, so this task **creates** the shared generator. The **letters-only default is the byte-identical baseline**; the DDQ + meeting-note emitters sit behind `include_ddq_and_notes=False`. The generator is authored constants, RNG-free (the M5 / E3 §8 ruling 4 "demo facts are authored constants" discipline). The authored corpus reproduces E3 §3.2's six-document hero (query "corvid lane liquidity 2024" with its planted relevant set and the wrong-firm distractor) so the E3 build track's retrieval eval is measurable without human annotation.

**Interfaces:**
- `Document(doc_id, doc_type, manager_code, author, text, as_of)` — a frozen dataclass; `doc_type in {"letter", "ddq", "meeting_note"}`. Authored constants; no vendor / AI brand names in `text` (banned-word discipline).
- `build_corpus(include_ddq_and_notes: bool = False) -> list[Document]` — returns the authored **letters** always; appends the authored **DDQs + meeting notes** when the flag is `True`. Deterministic order, RNG-free.
- `planted_relevance() -> list[dict]` — the query → relevant-document ground truth planted at generation time (E3 §6.4): each entry `{query_id, query, theme, entity, relevant_doc_ids}`. `relevant_doc_ids` references documents that only exist when the flag is on (the meeting note is the §3.2 hero); a helper documents that the retrieval eval must build the corpus with the flag on.

- [ ] **Step 1: Write the failing tests.**

Create `tests/flagships/test_saydo_corpus.py`:

```python
from quant_allocator.flagships.saydo.corpus import (
    Document,
    build_corpus,
    planted_relevance,
)

# The wave brief's banned-word list (any casing) must not appear in authored text.
_BANNED = ("claude", "anthropic", "openai", "gpt", "gemini", "copilot")


def test_corpus_flag_off_is_letters_only_and_deterministic():
    first = build_corpus()
    second = build_corpus()
    assert [d.doc_id for d in first] == [d.doc_id for d in second]
    assert all(d.doc_type == "letter" for d in first)
    assert all(isinstance(d, Document) for d in first)


def test_flag_on_adds_ddqs_and_meeting_notes_superset_of_letters():
    off = build_corpus()
    on = build_corpus(include_ddq_and_notes=True)
    off_ids = {d.doc_id for d in off}
    on_ids = {d.doc_id for d in on}
    assert off_ids < on_ids  # strict superset
    added_types = {d.doc_type for d in on if d.doc_id not in off_ids}
    assert added_types == {"ddq", "meeting_note"}


def test_planted_relevance_references_documents_that_exist_with_flag_on():
    corpus_ids = {d.doc_id for d in build_corpus(include_ddq_and_notes=True)}
    queries = planted_relevance()
    assert queries, "at least one planted query"
    for q in queries:
        assert {"query_id", "query", "theme", "entity", "relevant_doc_ids"} <= set(q)
        assert q["relevant_doc_ids"], "each query has a non-empty planted relevant set"
        assert set(q["relevant_doc_ids"]) <= corpus_ids


def test_hero_query_planted_set_matches_e3_worked_example():
    # E3 sec 3.2: "corvid lane liquidity 2024" -> letter + DDQ + meeting note (3 relevant),
    # the wrong-firm (Wexford Green) DDQ is a distractor, NOT in the relevant set.
    hero = next(q for q in planted_relevance() if q["entity"] == "Corvid Lane Capital")
    assert len(hero["relevant_doc_ids"]) == 3
    corpus = {d.doc_id: d for d in build_corpus(include_ddq_and_notes=True)}
    types = sorted(corpus[i].doc_type for i in hero["relevant_doc_ids"])
    assert types == ["ddq", "letter", "meeting_note"]


def test_no_banned_words_in_authored_text():
    for d in build_corpus(include_ddq_and_notes=True):
        lowered = d.text.lower()
        assert not any(word in lowered for word in _BANNED)
```

Run `uv run pytest tests/flagships/test_saydo_corpus.py -q` — fails (module does not exist).

- [ ] **Step 2: Implement the authored corpus generator.**

Create `src/quant_allocator/flagships/saydo/corpus.py`. Author the six-document E3 §3.2 hero set (fictional names from E3 §8 ruling 6 only): the letter `L-2024Q1` and a second letter as the flag-off baseline; `DDQ-2024` (Corvid Lane), `DDQ-WEX` (Wexford Green — the distractor), and `MTG-2024-05` (the paraphrase hero, author Elena Voss) behind the flag. Text is authored prose that reproduces the §3.2 lexical/paraphrase structure (the note says "redemption gates" and "cash buffers", never "liquidity" or "corvid lane"). Keep the module RNG-free and free of banned words.

```python
"""Shared say-do synthetic corpus (E3 §6.4 substrate; M5 letter baseline).

Authored constants, RNG-free (the demo-facts-are-authored discipline, E3 §8 ruling 4).
build_corpus() returns LETTERS only (the byte-identical baseline); the DDQ and
meeting-note emitters are added behind include_ddq_and_notes=False so the letter corpus is
unchanged when the flag is off. planted_relevance() carries the query -> relevant-document
ground truth planted at generation time, reproducing the E3 §3.2 worked example so the
retrieval eval is measurable without human annotation.

Fictional names only (E3 §8 ruling 6): Corvid Lane Capital, Selby Point Advisors,
Wexford Green Capital, Elena Voss, Priya Anand. No real firms; no banned brand names.
"""

from __future__ import annotations

from dataclasses import dataclass

_DOC_TYPES = ("letter", "ddq", "meeting_note")


@dataclass(frozen=True)
class Document:
    doc_id: str
    doc_type: str  # one of _DOC_TYPES
    manager_code: str
    author: str
    text: str
    as_of: str  # "YYYY-MM"


# --- Letters: the flag-off baseline. Authored constants. ---
_LETTERS: tuple[Document, ...] = (
    Document(
        doc_id="L-2024Q1",
        doc_type="letter",
        manager_code="CLC",
        author="Elena Voss",
        as_of="2024-03",
        text=(
            "In the first quarter we remained comfortable with portfolio liquidity and "
            "kept the book positioned for a range of outcomes. Corvid Lane continues to "
            "favour durable cash generators over crowded momentum names."
        ),
    ),
    Document(
        doc_id="L-2023Q4",
        doc_type="letter",
        manager_code="SPA",
        author="Priya Anand",
        as_of="2023-12",
        text=(
            "Selby Point closed the year with a modest net long and a value tilt. We "
            "trimmed several positions into strength and added to higher-quality names."
        ),
    ),
)

# --- DDQs + meeting notes: added only when include_ddq_and_notes=True. ---
_DDQS_AND_NOTES: tuple[Document, ...] = (
    Document(
        doc_id="DDQ-2024",
        doc_type="ddq",
        manager_code="CLC",
        author="Corvid Lane Capital",
        as_of="2024-02",
        text=(
            "Liquidity terms: the fund offers quarterly redemption with ninety day "
            "notice. Corvid Lane maintains a documented liquidity policy reviewed by the "
            "risk committee."
        ),
    ),
    Document(
        doc_id="DDQ-WEX",  # distractor: right topic (liquidity), WRONG firm.
        doc_type="ddq",
        manager_code="WGC",
        author="Wexford Green Capital",
        as_of="2024-02",
        text=(
            "Liquidity and notice terms: investors may redeem semi-annually subject to "
            "standard notice. Wexford Green publishes its liquidity framework annually."
        ),
    ),
    Document(
        doc_id="MTG-2024-05",  # the paraphrase hero: on-topic, shares NO query token.
        doc_type="meeting_note",
        manager_code="CLC",
        author="Elena Voss",
        as_of="2024-05",
        text=(
            "The portfolio manager walked through how redemption gates would apply under "
            "stress and how she sizes cash buffers against a wave of withdrawals. She "
            "described the order in which sleeves would be raised."
        ),
    ),
)


def build_corpus(include_ddq_and_notes: bool = False) -> list[Document]:
    """Authored corpus. Letters only by default (byte-identical baseline); DDQs and
    meeting notes appended when the flag is on. Deterministic order, RNG-free."""
    docs = list(_LETTERS)
    if include_ddq_and_notes:
        docs.extend(_DDQS_AND_NOTES)
    return docs


def planted_relevance() -> list[dict]:
    """Query -> planted relevant-document ground truth (E3 §3.2 / §6.4). The relevant set
    references DDQ/meeting-note docs, so the retrieval eval builds the corpus with the flag
    on. The Wexford Green DDQ (DDQ-WEX) is a deliberate distractor and is NOT relevant."""
    return [
        {
            "query_id": "Q1",
            "query": "corvid lane liquidity 2024",
            "theme": "liquidity",
            "entity": "Corvid Lane Capital",
            "relevant_doc_ids": ("L-2024Q1", "DDQ-2024", "MTG-2024-05"),
        }
    ]
```

Run `uv run pytest tests/flagships/test_saydo_corpus.py -q` — passes.

- [ ] **Step 3: Verify and commit.** Run *Automated Verification* (the `tests/demo_data` run confirms `m5_saydo.json` is byte-identical — the new module is imported by no existing demo). Commit: `feat: shared say-do corpus generator with default-off DDQ/notes and planted eval set (E3 substrate)`.

---

## Task 5: P2 substrate — E-tier bucket coarsening in the tier emission

**Files:**
- Modify: `src/quant_allocator/simulator/tiers.py`
- Test: `tests/simulator/test_tiers.py` (add tests; create the file if absent)

**Interfaces:**
- `OP_BUCKET_WIDTH = 0.05` (P2 §6.6 / §8 ruling 4, `# NUMERICS-GATE`) — the Open-Protocol E-tier coarsening granularity in beta units.
- `emit_tiers(market, history, *, coarsen_e_tier: bool = False) -> ManagerDataTiers` — when `coarsen_e_tier=True`, the **factor-beta columns** of the `exposures` frame (the `beta_*` columns — the E-tier disclosure) are rounded to the nearest `OP_BUCKET_WIDTH`. `False` (default) recovers the exact current emission **byte-identically**. `gross`, `net`, and `top10_share` are not coarsened (they are not the E-tier factor disclosure). `# NUMERICS-GATE`: which columns are the coarsened E-tier disclosure, and the round-half-to-even convention.

- [ ] **Step 1: Write the failing tests.**

Add to `tests/simulator/test_tiers.py` (create if absent):

```python
import numpy as np
import pandas as pd

from quant_allocator.simulator.manager import ManagerConfig, simulate_manager
from quant_allocator.simulator.market import MarketConfig, simulate_market
from quant_allocator.simulator.tiers import OP_BUCKET_WIDTH, emit_tiers


def _history():
    market = simulate_market(MarketConfig(n_assets=200, n_months=48, seed=3))
    history = simulate_manager(market, ManagerConfig(information_coefficient=0.10, seed=7))
    return market, history


def test_coarsen_default_off_is_byte_identical():
    market, history = _history()
    base = emit_tiers(market, history)
    off = emit_tiers(market, history, coarsen_e_tier=False)
    pd.testing.assert_frame_equal(base.exposures, off.exposures)
    pd.testing.assert_series_equal(base.returns_only, off.returns_only)
    pd.testing.assert_frame_equal(base.transparency, off.transparency)


def test_coarsen_rounds_beta_columns_to_bucket_grid():
    market, history = _history()
    coarse = emit_tiers(market, history, coarsen_e_tier=True)
    beta_cols = [c for c in coarse.exposures.columns if c.startswith("beta_")]
    grid = (coarse.exposures[beta_cols] / OP_BUCKET_WIDTH).to_numpy()
    np.testing.assert_allclose(grid, np.round(grid), atol=1e-9)


def test_coarsen_leaves_gross_net_top10_untouched():
    market, history = _history()
    base = emit_tiers(market, history)
    coarse = emit_tiers(market, history, coarsen_e_tier=True)
    for col in ("gross", "net", "top10_share"):
        pd.testing.assert_series_equal(base.exposures[col], coarse.exposures[col])
```

Run `uv run pytest tests/simulator/test_tiers.py -q` — fails.

- [ ] **Step 2: Add the constant and the coarsening option.**

In `tiers.py`, add below `TOP_N_CONCENTRATION`:

```python
# P2 spec §6.6 / §8 ruling 4 (NUMERICS-GATE): Open-Protocol E-tier coarsening granularity
# (beta units). A real E-tier disclosure buckets factor betas; the demo coarsens on opt-in.
OP_BUCKET_WIDTH = 0.05
```

Change the signature and add the guarded coarsening after the `exposures` frame is fully built (after the `exposures["top10_share"] = top10_share` line), leaving the default path untouched:

```python
def emit_tiers(
    market: FactorMarket, history: ManagerHistory, *, coarsen_e_tier: bool = False
) -> ManagerDataTiers:
```

```python
    exposures["top10_share"] = top10_share
    if coarsen_e_tier:
        beta_cols = [c for c in exposures.columns if c.startswith("beta_")]
        exposures[beta_cols] = (exposures[beta_cols] / OP_BUCKET_WIDTH).round() * OP_BUCKET_WIDTH
```

Run `uv run pytest tests/simulator/test_tiers.py -q` — passes.

- [ ] **Step 3: Verify and commit.** Run *Automated Verification* (the `tests/demo_data` run confirms every demo that calls `emit_tiers` still regenerates byte-identical JSON, since none passes `coarsen_e_tier`). Commit: `feat: opt-in E-tier bucket coarsening in tier emission (P2 substrate)`.

---

## Task 6: Full-suite byte-identity verification (no code)

**Files:** none.

- [ ] **Step 1: Run the whole non-slow, non-network suite.**

```bash
uv run pytest -m "not slow and not network" -q
uv run ruff check src tests
```

Confirm: all new substrate dial/emitter/corpus/coarsening tests pass; the demo-data determinism tests (`tests/demo_data/*::test_byte_for_byte_determinism_and_matches_committed`) are green, proving every committed `site/data/*.json` (including `m5_saydo.json`) regenerates byte-for-byte with all new defaults OFF; ruff is clean.

- [ ] **Step 2: Confirm the stream-tag registry.** Verify the enumeration is `{0: market, 1: manager, 2: returns_only, 3: exit-random, 4: short-signal, 5: liquidity/ADV, 6: crowd}` with no collision against the flagship/test tags `{7, 11, 12, 13, 14, 15, 42, 43, 98, 99}`:

```bash
uv run python -c "from quant_allocator.simulator import market, manager, returns_only; print(sorted({market._MARKET_STREAM, manager._MANAGER_STREAM, returns_only._RETURNS_ONLY_STREAM, manager._EXIT_RANDOM_STREAM, manager._SHORT_SIGNAL_STREAM, market._LIQUIDITY_STREAM, manager._CROWD_STREAM}))"
```

Expected: `[0, 1, 2, 3, 4, 5, 6]`.

- [ ] **Step 3: Final commit (if any doc updates).** No production code changes here; if a plan-status note is added, commit `docs: record wave2-b3 substrate verification`.
