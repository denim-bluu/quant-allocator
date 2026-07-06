# Wave-1 Plan B1 — Demo-Data Substrate + S1/M5 Generators Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

> **NUMERICS ARE HELD FOR THE NUMERICS GATE.** Nothing in this plan merges to `main` or publishes. Every JSON file this plan produces (`site/data/s1_ledger.json`, `site/data/m5_saydo.json`) is committed to a **branch** and stays there until a later numerics-gate pass certifies the numbers (annualization, alignment, seeding are the named failure modes — gallery design §8). The self-consistency tests in this plan catch transcription errors mechanically; **they do not replace the gate.**

**Goal:** Build the local-only `quant_allocator.demo_data` generation package plus two of the five wave-1 demo-data generators — S1 (skill-ledger posterior strip) and M5 (say–do exposure paths + alignment) — as analytic library code (`flagships/skill_ledger/empirical.py`, `flagships/saydo/alignment.py`) + seeded, deterministic committed JSON under `site/data/` + self-consistency tests.

**Architecture:** Two layers. (1) **Analytic library** under `src/quant_allocator/flagships/` — pure functions transcribed verbatim from the S1 and M5 method specs (numpy only; no PyMC, no LLM, no network). (2) **Local generation package** `src/quant_allocator/demo_data/` — consumes the existing simulator (`simulator.market`, `simulator.manager`, `simulator.tiers`) to build seeded synthetic rosters/exposure paths, runs them through the analytic library, and writes deterministic JSON via a shared writer. A CLI (`python -m quant_allocator.demo_data build [card|all]`) drives it. `demo_data` runs on the developer machine only; it is **never** imported by `quant_allocator.site` (the CI builder renders committed JSON, it never computes).

**Tech Stack:** Python ≥3.11, numpy ≥2.4 (analytic + simulator), pandas ≥3.0 (simulator emissions), Python stdlib `json`/`statistics`/`math` (writer, normal CDF, z-quantile). Tests: pytest with `pythonpath=["src"]`. Lint: ruff line-length 100. Package/venv manager: `uv` (`uv run pytest`, `uv run ruff check`, `uv run python -m …`).

## Global Constraints

- **Formulas are transcribed verbatim from the named spec sections, with a `# <spec> §X` citation comment in the code.** No statistical method is derived or chosen in this plan.
- **Every generator task emits committed JSON and carries in its task header:** `Numeric output is HELD FOR NUMERICS GATE — do not merge or publish until certified.`
- **Self-consistency tests are mandatory per generator** and are real, assertion-bearing tests: (a) JSON schema validity; (b) byte-for-byte determinism across two runs (same seed → identical file) **and** regeneration matches the committed file; (c) domain invariants — for S1: shrinkage weight `w ∈ [0,1]`; posterior mean lies between the OLS estimate and the group prior mean; posterior interval no wider than the OLS interval; `P(α>0) ∈ [0,1]`; for M5: every alignment label ∈ `{aligned, partial, contradicted}`; a planted-contradiction fixture (stated cautious + measured move against ≥ δ) labels `contradicted`; a planted-aligned fixture labels `aligned`.
- **`quant_allocator.demo_data` is a LOCAL-ONLY generation package.** It legitimately imports numpy/pandas/simulator (it runs locally, not in CI). It is **never** imported by `quant_allocator.site`. Import-safety from the site builder's perspective is NOT a requirement for `demo_data`.
- **The analytic library** (`flagships/skill_ledger/empirical.py`, `flagships/saydo/alignment.py`) is numpy-only — **no PyMC, no LLM, no network**. `empirical.py` is unit-agnostic pure math; annualization lives in the generator, not the analytic function.
- **Determinism:** distinct RNG streams via the existing `numpy.random.default_rng([seed, tag])` convention already used by the simulator; JSON written with **sorted keys + fixed float precision (6 decimals) + trailing newline** so diffs are stable (gallery design §8).
- **Repo is public** — no employer-internal facts or manager names anywhere in code, comments, commits, or committed data. Manager codes are neutral (`A01…A10`, `B01…B10`, `M07`).
- **Commits:** conventional prefixes (`feat:` / `test:` / `chore:` / `docs:`), **NO commit trailers**. All commands run through `uv`. Existing test suite stays green and ruff stays clean after every task.
- **OUT OF SCOPE (do not build):** the other three generators (`s2_tearsheet`, `x1_atlas`, `x2_playground`), the page templates that render this JSON, the live PyMC model (`skill_ledger/model.py`), the M5 LLM `extraction.py`, and the M5 eval `harness.py`. These are separate later plans.

---

## the lead reviewer Numerics-Gate Docket

The drafter surfaced 7 numeric ambiguities rather than inventing answers. The
controller (senior) triaged them. **Implementation proceeds on the provisional
values below — all are named constants at module top; the lead reviewer flips a constant and
regenerates (one command) if it disposes differently. Nothing merges or
publishes until the lead reviewer clears this docket against the committed JSON.**

**Confirmed by the controller (spec-settled or plain math — NOT gate items):**
- **τ̂² per group** (`empirical.py`): §3.2 writes α_i ~ N(μ_s, τ_s²) — the *s*
  subscript is per-strategy. Per-group is correct.
- **se(α) annualized ×12** (`roster.py`): annual_α = 12·monthly_α ⇒ se scales
  ×12 (linear); the √12 is for volatility only (variance additive). Correct.

**Held for the lead reviewer (provisional default → the lead reviewer confirms or flips):**
| # | Question | Constant | Provisional | Why the lead reviewer |
| --- | --- | --- | --- | --- |
| Q1 | OLS interval distribution (level=90% confirmed) | `_Z90` vs t-quantile | normal-z (1.6449) | normal vs Student-t(T−k−1) is a finite-sample honesty call; affects OLS interval width |
| Q3 | τ² sample-variance ddof | `ddof=1` | unbiased | method-of-moments τ² convention; affects shrinkage magnitude (the headline reshuffle) |
| Q5 | δ dead-bands (M5) | `DELTA_TABLE` | beta 0.10, net 0.05 | §4 calibrates δ to a ≤1-in-20 false-contradiction budget; demo δ is illustrative (page must say so), live δ is a calibration |
| Q6 | `|move|<δ` against direction → label | rule in `score_alignment` | `partial` | dead-band edge case; verified the demo's 3 views never hit it |
| Q7 | neutral-explicit `|move|>δ` → label | rule in `score_alignment` | `contradicted` | complement of the aligned rule; demo may not use a neutral-explicit view |

**Gate procedure when the lead reviewer refreshes:** review this docket + the committed
`s1_ledger.json` / `m5_saydo.json` diffs; for any flip, change the named
constant and re-run `python -m quant_allocator.demo_data build all`; the
determinism test proves the regeneration is clean. Only then may B1 merge.

---

## Task 1: `demo_data` package scaffolding + shared JSON writer (`_emit.py`) + CLI

**Files:**
- Create: `src/quant_allocator/demo_data/__init__.py`
- Create: `src/quant_allocator/demo_data/_emit.py`
- Create: `src/quant_allocator/demo_data/__main__.py`
- Create: `tests/demo_data/__init__.py`
- Test: `tests/demo_data/test_emit.py`
- Test: `tests/demo_data/test_cli.py`

**Interfaces:**
- Consumes: nothing (stdlib only).
- Produces:
  - `SITE_DATA_DIR: Path` — repo-relative `site/data/` directory (resolved from `_emit.py`'s location).
  - `round_floats(obj: Any, ndigits: int = 6) -> Any` — recursively round every float in a JSON-able structure.
  - `write_json(path: Path, data: dict, *, ndigits: int = 6) -> Path` — write `data` with sorted keys, indent 2, 6-decimal floats, trailing newline; returns `path`.
  - `main(argv: list[str] | None = None) -> int` — CLI entry; `_builders() -> dict[str, Callable[[], Path]]` registry (empty in this task; later tasks add entries).

- [ ] **Step 1: Create the package and test directories.**
  Run:
  ```bash
  mkdir -p src/quant_allocator/demo_data tests/demo_data
  touch tests/demo_data/__init__.py
  ```
  Then create `src/quant_allocator/demo_data/__init__.py` with exactly:
  ```python
  """Local-only demo-data generation package.

  Consumes numpy/pandas and the simulator to build seeded synthetic rosters and
  exposure paths, then writes deterministic JSON into site/data/. NEVER imported
  by quant_allocator.site (the CI builder renders committed JSON; it never
  computes). Run locally: python -m quant_allocator.demo_data build [card|all].
  """
  ```

- [ ] **Step 2: Write the failing writer test.**
  Create `tests/demo_data/test_emit.py`:
  ```python
  import json

  from quant_allocator.demo_data._emit import round_floats, write_json


  def test_round_floats_recurses_into_nested_structures():
      data = {"b": 0.123456789, "a": [1.111111119, {"c": 2.0}]}
      rounded = round_floats(data, ndigits=6)
      assert rounded["b"] == 0.123457
      assert rounded["a"][0] == 1.111111
      assert rounded["a"][1]["c"] == 2.0


  def test_write_json_is_sorted_indented_and_newline_terminated(tmp_path):
      path = write_json(tmp_path / "out.json", {"z": 1.0, "a": 2.0})
      text = path.read_text(encoding="utf-8")
      assert text.endswith("\n")
      assert text.index('"a"') < text.index('"z"')  # keys sorted
      assert json.loads(text) == {"a": 2.0, "z": 1.0}


  def test_write_json_is_byte_for_byte_deterministic(tmp_path):
      payload = {"m": [{"code": "A01", "x": 0.3333333333}, {"code": "A02", "x": 0.6}]}
      first = write_json(tmp_path / "a.json", payload).read_bytes()
      second = write_json(tmp_path / "b.json", payload).read_bytes()
      assert first == second
  ```

- [ ] **Step 3: Run the writer test to verify it fails.**
  Run: `uv run pytest tests/demo_data/test_emit.py -q`
  Expected: FAIL / collection error — `ModuleNotFoundError: No module named 'quant_allocator.demo_data._emit'`.

- [ ] **Step 4: Implement `_emit.py`.**
  Create `src/quant_allocator/demo_data/_emit.py`:
  ```python
  """Deterministic JSON writer shared by every demo-data generator.

  Sorted keys + fixed float precision + trailing newline make committed JSON a
  stable PR diff — that diff is the artifact the numerics gate reviews
  (gallery design §8).
  """

  from __future__ import annotations

  import json
  from pathlib import Path
  from typing import Any

  # site/data/ resolved relative to this file: demo_data/_emit.py -> repo/site/data
  SITE_DATA_DIR = Path(__file__).resolve().parents[3] / "site" / "data"


  def round_floats(obj: Any, ndigits: int = 6) -> Any:
      if isinstance(obj, float):
          return round(obj, ndigits)
      if isinstance(obj, dict):
          return {key: round_floats(value, ndigits) for key, value in obj.items()}
      if isinstance(obj, (list, tuple)):
          return [round_floats(value, ndigits) for value in obj]
      return obj


  def write_json(path: Path, data: dict, *, ndigits: int = 6) -> Path:
      path.parent.mkdir(parents=True, exist_ok=True)
      text = json.dumps(round_floats(data, ndigits), sort_keys=True, indent=2)
      path.write_text(text + "\n", encoding="utf-8")
      return path
  ```

- [ ] **Step 5: Run the writer test to verify it passes.**
  Run: `uv run pytest tests/demo_data/test_emit.py -q`
  Expected: PASS (3 passed).

- [ ] **Step 6: Write the failing CLI test.**
  Create `tests/demo_data/test_cli.py`:
  ```python
  import pytest

  from quant_allocator.demo_data.__main__ import main


  def test_build_unknown_card_errors():
      with pytest.raises(SystemExit):
          main(["build", "does-not-exist"])


  def test_build_all_with_empty_registry_is_a_noop():
      # Registry is empty until the S1/M5 generator tasks register their builders.
      assert main(["build", "all"]) == 0
  ```

- [ ] **Step 7: Run the CLI test to verify it fails.**
  Run: `uv run pytest tests/demo_data/test_cli.py -q`
  Expected: FAIL / collection error — no module `quant_allocator.demo_data.__main__`.

- [ ] **Step 8: Implement `__main__.py`.**
  Create `src/quant_allocator/demo_data/__main__.py`:
  ```python
  """CLI: python -m quant_allocator.demo_data build [card|all].

  Each generator registers a zero-argument builder that writes its JSON into
  site/data/ and returns the written path. Later tasks add entries to
  _builders(); this scaffolding task ships it empty.
  """

  from __future__ import annotations

  import argparse
  import sys
  from collections.abc import Callable
  from pathlib import Path


  def _builders() -> dict[str, Callable[[], Path]]:
      # Generators register here as later tasks add them (Task 4: s1_ledger, Task 6: m5_saydo).
      return {}


  def main(argv: list[str] | None = None) -> int:
      parser = argparse.ArgumentParser(prog="quant_allocator.demo_data")
      sub = parser.add_subparsers(dest="command", required=True)
      build = sub.add_parser("build", help="build one card by id, or 'all'")
      build.add_argument("card", help="card id (e.g. s1_ledger, m5_saydo) or 'all'")
      args = parser.parse_args(argv)

      builders = _builders()
      if args.card == "all":
          for card_id, builder in sorted(builders.items()):
              path = builder()
              print(f"wrote {path}")
          return 0
      if args.card not in builders:
          parser.error(f"unknown card {args.card!r}; known: {sorted(builders)} or 'all'")
      path = builders[args.card]()
      print(f"wrote {path}")
      return 0


  if __name__ == "__main__":
      sys.exit(main())
  ```

- [ ] **Step 9: Run the CLI test to verify it passes.**
  Run: `uv run pytest tests/demo_data/test_cli.py -q`
  Expected: PASS (2 passed). Note: `parser.error(...)` raises `SystemExit`, satisfying the unknown-card test.

- [ ] **Step 10: Ruff + commit.**
  Run: `uv run ruff check src/quant_allocator/demo_data tests/demo_data`
  Expected: `All checks passed!`
  ```bash
  git add src/quant_allocator/demo_data tests/demo_data
  git commit -m "feat: demo_data package scaffolding, deterministic JSON writer, and build CLI"
  ```

---

## Task 2: Shared synthetic roster (`roster.py`)

Builds the 20-manager, two-strategy-group synthetic roster the S1 generator consumes: per manager a code, group, track length `T`, ground-truth annualized alpha, and the OLS alpha estimate + standard error from regressing the manager's monthly returns on the simulator's factor returns.

**Files:**
- Create: `src/quant_allocator/demo_data/roster.py`
- Test: `tests/demo_data/test_roster.py`

**Interfaces:**
- Consumes: `simulator.market.{MarketConfig, simulate_market}`, `simulator.manager.{ManagerConfig, simulate_manager}`.
- Produces:
  - `@dataclass(frozen=True) RosterManager` with fields: `code: str`, `group: str`, `months: int`, `true_alpha_annual: float`, `ols_alpha_annual: float`, `ols_se_annual: float`.
  - `ols_alpha_and_se(returns: np.ndarray, factors: np.ndarray) -> tuple[float, float]` — regress `returns` (shape `T`) on `factors` (shape `T×k`) with intercept; return `(intercept, se_of_intercept)` in **monthly** units.
  - `build_skill_ledger_roster(base_seed: int = BASE_SEED) -> list[RosterManager]` — 20 managers, groups `"A"` (10) and `"B"` (10).
  - Module constants `BASE_SEED = 20260706`, `GROUP_CODES = ("A", "B")`.

- [ ] **Step 1: Write the failing roster test.**
  Create `tests/demo_data/test_roster.py`:
  ```python
  import numpy as np

  from quant_allocator.demo_data.roster import (
      RosterManager,
      build_skill_ledger_roster,
      ols_alpha_and_se,
  )


  def test_ols_recovers_planted_intercept_and_positive_se():
      rng = np.random.default_rng(0)
      T = 60
      factors = rng.normal(0.0, 0.04, size=(T, 3))
      true_betas = np.array([0.8, -0.3, 0.5])
      y = 0.01 + factors @ true_betas + rng.normal(0.0, 0.02, size=T)
      alpha, se = ols_alpha_and_se(y, factors)
      assert abs(alpha - 0.01) < 0.01
      assert se > 0.0


  def test_roster_has_twenty_managers_in_two_groups_of_ten():
      roster = build_skill_ledger_roster()
      assert len(roster) == 20
      assert all(isinstance(m, RosterManager) for m in roster)
      groups = [m.group for m in roster]
      assert groups.count("A") == 10 and groups.count("B") == 10
      codes = [m.code for m in roster]
      assert codes == sorted(set(codes))  # unique, sorted
      assert all(m.months in (36, 48, 60) for m in roster)
      assert all(np.isfinite(m.ols_alpha_annual) and m.ols_se_annual > 0 for m in roster)


  def test_roster_is_deterministic():
      a = build_skill_ledger_roster()
      b = build_skill_ledger_roster()
      assert [m.code for m in a] == [m.code for m in b]
      assert [m.ols_alpha_annual for m in a] == [m.ols_alpha_annual for m in b]
      assert [m.true_alpha_annual for m in a] == [m.true_alpha_annual for m in b]
  ```

- [ ] **Step 2: Run the roster test to verify it fails.**
  Run: `uv run pytest tests/demo_data/test_roster.py -q`
  Expected: FAIL — `ModuleNotFoundError: No module named 'quant_allocator.demo_data.roster'`.

- [ ] **Step 3: Implement `roster.py`.**

  <!-- CONTROLLER-CONFIRMED (not a gate item): OLS alpha se annualized ×12 (linear scaling of a location parameter, S1 §3.1 "annualizes α by ×12"), NOT ×√12 (reserved for volatilities). se of a ×12-scaled quantity scales ×12 by mathematical necessity. Implement as written. -->

  Create `src/quant_allocator/demo_data/roster.py`:
  ```python
  """Seeded synthetic roster for the S1 skill ledger.

  Two strategy groups of ten managers each. Per manager: a ground-truth
  annualized alpha (from the simulator's known idiosyncratic contribution) and an
  OLS alpha estimate + standard error from regressing the manager's monthly
  returns on the simulator's factor returns. Track lengths vary across managers
  so shorter records earn more shrinkage in Task 4.
  """

  from __future__ import annotations

  from dataclasses import dataclass

  import numpy as np

  from quant_allocator.simulator.manager import ManagerConfig, simulate_manager
  from quant_allocator.simulator.market import MarketConfig, simulate_market

  MONTHS_PER_YEAR = 12
  BASE_SEED = 20260706
  GROUP_CODES = ("A", "B")
  _N_PER_GROUP = 10
  _MARKET_MONTHS = 60
  _N_ASSETS = 300
  _T_CYCLE = (36, 48, 60)  # track length per manager, cycled within a group
  # Per-group max information coefficient sets the true-skill dispersion spread.
  _GROUP_IC_MAX = {"A": 0.12, "B": 0.08}


  @dataclass(frozen=True)
  class RosterManager:
      code: str
      group: str
      months: int
      true_alpha_annual: float
      ols_alpha_annual: float
      ols_se_annual: float


  def ols_alpha_and_se(returns: np.ndarray, factors: np.ndarray) -> tuple[float, float]:
      # S1 spec §3.1 observation model: y = alpha + beta·f + eps. Intercept is alpha.
      design = np.column_stack([np.ones(len(returns)), factors])
      coef, *_ = np.linalg.lstsq(design, returns, rcond=None)
      residual = returns - design @ coef
      dof = len(returns) - design.shape[1]
      sigma2 = float(residual @ residual) / dof
      cov = sigma2 * np.linalg.inv(design.T @ design)
      alpha = float(coef[0])
      se_alpha = float(np.sqrt(cov[0, 0]))
      return alpha, se_alpha


  def build_skill_ledger_roster(base_seed: int = BASE_SEED) -> list[RosterManager]:
      roster: list[RosterManager] = []
      for group_index, group in enumerate(GROUP_CODES):
          market = simulate_market(
              MarketConfig(n_assets=_N_ASSETS, n_months=_MARKET_MONTHS, seed=base_seed + group_index)
          )
          factor_returns = market.factor_returns.to_numpy()
          ic_max = _GROUP_IC_MAX[group]
          for i in range(_N_PER_GROUP):
              ic = ic_max * i / (_N_PER_GROUP - 1)  # spread from 0 (noise) to ic_max (skill)
              months = _T_CYCLE[i % len(_T_CYCLE)]
              manager_seed = base_seed * 10 + group_index * 100 + i
              history = simulate_manager(
                  market, ManagerConfig(information_coefficient=ic, seed=manager_seed)
              )
              returns = history.monthly_returns.to_numpy()[:months]
              factors = factor_returns[:months]
              alpha, se = ols_alpha_and_se(returns, factors)
              true_alpha = float(history.true_alpha_returns.to_numpy()[:months].mean())
              roster.append(
                  RosterManager(
                      code=f"{group}{i + 1:02d}",
                      group=group,
                      months=months,
                      # S1 spec §3.1: reporting annualizes alpha by ×12 (and its se linearly).
                      true_alpha_annual=true_alpha * MONTHS_PER_YEAR,
                      ols_alpha_annual=alpha * MONTHS_PER_YEAR,
                      ols_se_annual=se * MONTHS_PER_YEAR,
                  )
              )
      return roster
  ```

- [ ] **Step 4: Run the roster test to verify it passes.**
  Run: `uv run pytest tests/demo_data/test_roster.py -q`
  Expected: PASS (3 passed).

- [ ] **Step 5: Ruff + commit.**
  Run: `uv run ruff check src/quant_allocator/demo_data/roster.py tests/demo_data/test_roster.py`
  Expected: `All checks passed!`
  ```bash
  git add src/quant_allocator/demo_data/roster.py tests/demo_data/test_roster.py
  git commit -m "feat: seeded two-group synthetic roster with OLS alpha and standard error"
  ```

---

## Task 3: S1 closed-form shrinkage + advisory bands (`skill_ledger/empirical.py`)

The §3.6 empirical-Bayes normal-normal shrinkage and §3.7 advisory weight bands, as unit-agnostic pure functions (numpy only, no PyMC). This is the real analytic library function the S1 generator imports; the live PyMC build (`model.py`) is out of scope.

**Files:**
- Create: `src/quant_allocator/flagships/__init__.py`
- Create: `src/quant_allocator/flagships/skill_ledger/__init__.py`
- Create: `src/quant_allocator/flagships/skill_ledger/empirical.py`
- Create: `tests/flagships/__init__.py`
- Test: `tests/flagships/test_empirical.py`

**Interfaces:**
- Consumes: nothing (numpy + stdlib only).
- Produces:
  - `@dataclass(frozen=True) ShrinkageResult` with `np.ndarray` fields (length `n`, input order): `posterior_alpha`, `posterior_sd`, `shrinkage_weight`, `prob_positive`, `posterior_t_ratio`, `group_mean`, `group_tau2`.
  - `shrink_alphas(ols_alphas: np.ndarray, ses: np.ndarray, groups: np.ndarray) -> ShrinkageResult` — §3.6 shrinkage computed **within each group**.
  - `advisory_band(t_ratio: float) -> str` — §3.7, returns one of `"review" | "minimum" | "standard" | "conviction"`.

- [ ] **Step 1: Write the failing analytic test.**
  Create `tests/flagships/test_empirical.py`:
  ```python
  import numpy as np

  from quant_allocator.flagships.skill_ledger.empirical import (
      advisory_band,
      shrink_alphas,
  )


  def test_shrinkage_weight_matches_closed_form_by_hand():
      # S1 spec §3.6: mu_hat = mean(ols); tau2 = max(0, var(ols, ddof=1) - mean(se^2));
      # w = tau2 / (tau2 + se^2); post = w*ols + (1-w)*mu_hat.
      ols = np.array([0.02, 0.06, -0.01])
      ses = np.array([0.03, 0.03, 0.03])
      groups = np.array(["A", "A", "A"])
      mu = ols.mean()
      tau2 = max(0.0, ols.var(ddof=1) - (ses**2).mean())
      w = tau2 / (tau2 + ses**2)
      expected_post = w * ols + (1.0 - w) * mu
      result = shrink_alphas(ols, ses, groups)
      assert np.allclose(result.shrinkage_weight, w)
      assert np.allclose(result.posterior_alpha, expected_post)
      assert np.allclose(result.group_mean, mu)


  def test_weights_within_unit_interval_and_posterior_between_ols_and_prior():
      ols = np.array([0.05, -0.03, 0.01, 0.09])
      ses = np.array([0.02, 0.05, 0.04, 0.03])
      groups = np.array(["A", "A", "A", "A"])
      r = shrink_alphas(ols, ses, groups)
      assert np.all(r.shrinkage_weight >= 0.0) and np.all(r.shrinkage_weight <= 1.0)
      lo = np.minimum(ols, r.group_mean)
      hi = np.maximum(ols, r.group_mean)
      assert np.all(r.posterior_alpha >= lo - 1e-12)
      assert np.all(r.posterior_alpha <= hi + 1e-12)


  def test_posterior_sd_no_wider_than_se_and_prob_in_unit_interval():
      ols = np.array([0.05, -0.03, 0.01, 0.09])
      ses = np.array([0.02, 0.05, 0.04, 0.03])
      groups = np.array(["A", "A", "A", "A"])
      r = shrink_alphas(ols, ses, groups)
      assert np.all(r.posterior_sd <= ses + 1e-12)
      assert np.all(r.prob_positive >= 0.0) and np.all(r.prob_positive <= 1.0)


  def test_groups_are_shrunk_independently():
      ols = np.array([0.10, 0.12, -0.05, -0.07])
      ses = np.array([0.03, 0.03, 0.03, 0.03])
      groups = np.array(["A", "A", "B", "B"])
      r = shrink_alphas(ols, ses, groups)
      assert np.isclose(r.group_mean[0], np.mean([0.10, 0.12]))
      assert np.isclose(r.group_mean[2], np.mean([-0.05, -0.07]))


  def test_zero_dispersion_group_collapses_to_prior_without_error():
      # tau2 hits its floor of 0 (spec §8 note 4): posterior == group mean, sd == 0.
      ols = np.array([0.04, 0.04, 0.04])
      ses = np.array([0.05, 0.05, 0.05])
      groups = np.array(["A", "A", "A"])
      r = shrink_alphas(ols, ses, groups)
      assert np.allclose(r.shrinkage_weight, 0.0)
      assert np.allclose(r.posterior_alpha, 0.04)
      assert np.allclose(r.posterior_sd, 0.0)
      assert np.all(r.prob_positive == 1.0)  # mean > 0, degenerate posterior


  def test_advisory_bands_at_boundaries():
      # S1 spec §3.7: m<0 review; 0<=m<0.5 minimum; 0.5<=m<1 standard; m>=1 conviction.
      assert advisory_band(-0.1) == "review"
      assert advisory_band(0.0) == "minimum"
      assert advisory_band(0.49) == "minimum"
      assert advisory_band(0.5) == "standard"
      assert advisory_band(0.99) == "standard"
      assert advisory_band(1.0) == "conviction"
      assert advisory_band(3.0) == "conviction"
  ```

- [ ] **Step 2: Run the analytic test to verify it fails.**
  Run: `uv run pytest tests/flagships/test_empirical.py -q`
  Expected: FAIL — `ModuleNotFoundError: No module named 'quant_allocator.flagships'`.

- [ ] **Step 3: Create the package `__init__.py` files.**
  Run:
  ```bash
  mkdir -p src/quant_allocator/flagships/skill_ledger tests/flagships
  touch tests/flagships/__init__.py
  ```
  Create `src/quant_allocator/flagships/__init__.py`:
  ```python
  """Flagship analytic engines (numpy-only library code shared by demo and live builds)."""
  ```
  Create `src/quant_allocator/flagships/skill_ledger/__init__.py`:
  ```python
  """S1 hierarchical Bayesian alpha engine — closed-form demo variant lives in empirical.py."""
  ```

- [ ] **Step 4: Implement `empirical.py`.**

  <!-- CONTROLLER-CONFIRMED: (1) tau_hat^2 PER GROUP is correct — §3.2 writes alpha_i ~ N(mu_s, tau_s^2), the s subscript is per-strategy. Implement as written. HELD FOR NUMERICS (Q3 docket): (2) sample variance ddof=1 is PROVISIONAL — keep the `ddof=1` as a visible choice; the lead reviewer confirms the method-of-moments tau^2 convention before certifying. -->

  Create `src/quant_allocator/flagships/skill_ledger/empirical.py`:
  ```python
  """S1 §3.6 closed-form normal-normal shrinkage + §3.7 advisory weight bands.

  Unit-agnostic pure math: inputs are point estimates and their standard errors
  in one consistent unit (the S1 generator passes annualized values), outputs in
  the same unit. numpy only — no PyMC. The live MCMC model is skill_ledger/model.py
  (out of scope here); this closed form is both the demo path and a legitimate
  library function (S1 spec §3.6, §5).
  """

  from __future__ import annotations

  import math
  from dataclasses import dataclass

  import numpy as np


  @dataclass(frozen=True)
  class ShrinkageResult:
      posterior_alpha: np.ndarray
      posterior_sd: np.ndarray
      shrinkage_weight: np.ndarray
      prob_positive: np.ndarray
      posterior_t_ratio: np.ndarray
      group_mean: np.ndarray
      group_tau2: np.ndarray


  def _standard_normal_cdf(z: np.ndarray) -> np.ndarray:
      # Phi(z) = 0.5(1 + erf(z/sqrt2)); math.erf is exact and stdlib-only.
      return 0.5 * (1.0 + np.vectorize(math.erf)(z / math.sqrt(2.0)))


  def shrink_alphas(
      ols_alphas: np.ndarray, ses: np.ndarray, groups: np.ndarray
  ) -> ShrinkageResult:
      ols_alphas = np.asarray(ols_alphas, dtype=float)
      ses = np.asarray(ses, dtype=float)
      groups = np.asarray(groups)
      n = len(ols_alphas)
      posterior_alpha = np.empty(n)
      posterior_sd = np.empty(n)
      shrinkage_weight = np.empty(n)
      group_mean = np.empty(n)
      group_tau2 = np.empty(n)

      for group in np.unique(groups):
          mask = groups == group
          alphas = ols_alphas[mask]
          se2 = ses[mask] ** 2
          # S1 spec §3.6: mu_hat_s = mean(ols in s); tau_hat^2 = max(0, var(ols) - mean(se^2)).
          mu = float(alphas.mean())
          tau2 = max(0.0, float(alphas.var(ddof=1)) - float(se2.mean()))
          # S1 spec §3.6: w_i = tau_hat^2 / (tau_hat^2 + se(alpha_i)^2).
          w = tau2 / (tau2 + se2)
          # S1 spec §3.6: alpha_post = w*ols + (1 - w)*mu_hat.
          post = w * alphas + (1.0 - w) * mu
          # S1 spec §8 note 1: posterior precision = 1/tau^2 + 1/se^2, so posterior
          # variance = tau^2·se^2 / (tau^2 + se^2) = w·se^2 (algebraically identical,
          # and numerically safe when tau2 -> 0 => w -> 0 => sd -> 0).
          post_sd = np.sqrt(w * se2)
          posterior_alpha[mask] = post
          posterior_sd[mask] = post_sd
          shrinkage_weight[mask] = w
          group_mean[mask] = mu
          group_tau2[mask] = tau2

      # Posterior t-ratio m_i = E[alpha_i]/sd(alpha_i) (S1 spec §3.5, §3.7).
      with np.errstate(divide="ignore", invalid="ignore"):
          t_ratio = posterior_alpha / posterior_sd
      prob_positive = _standard_normal_cdf(t_ratio)
      # Degenerate posterior (sd == 0, tau2 floored to 0): P(alpha>0) is a step.
      degenerate = posterior_sd == 0.0
      prob_positive = np.where(
          degenerate, np.where(posterior_alpha > 0.0, 1.0, 0.0), prob_positive
      )
      t_ratio = np.where(
          degenerate, np.where(posterior_alpha > 0.0, np.inf, -np.inf), t_ratio
      )
      return ShrinkageResult(
          posterior_alpha=posterior_alpha,
          posterior_sd=posterior_sd,
          shrinkage_weight=shrinkage_weight,
          prob_positive=prob_positive,
          posterior_t_ratio=t_ratio,
          group_mean=group_mean,
          group_tau2=group_tau2,
      )


  def advisory_band(t_ratio: float) -> str:
      # S1 spec §3.7: four advisory bands from the posterior t-ratio m_i.
      if t_ratio < 0.0:
          return "review"
      if t_ratio < 0.5:
          return "minimum"
      if t_ratio < 1.0:
          return "standard"
      return "conviction"
  ```

- [ ] **Step 5: Run the analytic test to verify it passes.**
  Run: `uv run pytest tests/flagships/test_empirical.py -q`
  Expected: PASS (7 passed).

- [ ] **Step 6: Ruff + commit.**
  Run: `uv run ruff check src/quant_allocator/flagships tests/flagships`
  Expected: `All checks passed!`
  ```bash
  git add src/quant_allocator/flagships tests/flagships
  git commit -m "feat: S1 closed-form empirical-Bayes shrinkage and advisory weight bands"
  ```

---

## Task 4: S1 generator + committed JSON + self-consistency tests (`s1_ledger.py`)

> **Numeric output is HELD FOR NUMERICS GATE — do not merge or publish until certified.**

Assembles the roster (Task 2) + shrinkage (Task 3) into `site/data/s1_ledger.json`, registers the builder in the CLI, and adds the mandatory self-consistency tests.

**Files:**
- Create: `src/quant_allocator/demo_data/s1_ledger.py`
- Modify: `src/quant_allocator/demo_data/__main__.py` (register `s1_ledger`)
- Create: `site/data/s1_ledger.json` (generated output — held for gate)
- Test: `tests/demo_data/test_s1_ledger.py`
- Modify: `tests/demo_data/test_cli.py` (registry now non-empty)

**Interfaces:**
- Consumes: `roster.build_skill_ledger_roster`, `roster.RosterManager`, `roster.GROUP_CODES`, `roster.BASE_SEED`; `empirical.shrink_alphas`, `empirical.advisory_band`; `_emit.{SITE_DATA_DIR, write_json}`.
- Produces: `build(out_dir: Path = SITE_DATA_DIR) -> Path` writing `s1_ledger.json`; `CREDIBLE_LEVEL = 0.90`; `_Z90` (90% two-sided normal quantile).

- [ ] **Step 1: Write the failing self-consistency test.**
  Create `tests/demo_data/test_s1_ledger.py`:
  ```python
  import json

  import numpy as np

  from quant_allocator.demo_data import s1_ledger
  from quant_allocator.demo_data._emit import SITE_DATA_DIR


  def _load(path):
      return json.loads(path.read_text(encoding="utf-8"))


  def test_schema_is_valid(tmp_path):
      data = _load(s1_ledger.build(out_dir=tmp_path))
      assert data["meta"]["n_managers"] == 20
      assert data["meta"]["credible_level"] == 0.90
      assert {g["group"] for g in data["groups"]} == {"A", "B"}
      assert len(data["managers"]) == 20
      keys = {
          "code", "group", "months", "true_alpha_annual", "ols_alpha",
          "posterior_alpha", "prob_positive", "shrinkage_weight",
          "ols_rank", "posterior_rank", "advisory_band",
      }
      for m in data["managers"]:
          assert keys <= set(m)
          assert set(m["ols_alpha"]) == {"point", "ci_lo", "ci_hi"}
          assert set(m["posterior_alpha"]) == {"point", "ci_lo", "ci_hi"}
          assert m["advisory_band"] in {"review", "minimum", "standard", "conviction"}


  def test_byte_for_byte_determinism_and_matches_committed(tmp_path):
      first = s1_ledger.build(out_dir=tmp_path).read_bytes()
      second = s1_ledger.build(out_dir=tmp_path).read_bytes()
      assert first == second
      committed = (SITE_DATA_DIR / "s1_ledger.json").read_bytes()
      assert first == committed  # regeneration matches the committed file


  def test_domain_invariants(tmp_path):
      data = _load(s1_ledger.build(out_dir=tmp_path))
      for m in data["managers"]:
          w = m["shrinkage_weight"]
          assert 0.0 <= w <= 1.0
          assert 0.0 <= m["prob_positive"] <= 1.0
          group_mean = next(g["mu_hat_annual"] for g in data["groups"] if g["group"] == m["group"])
          post = m["posterior_alpha"]["point"]
          ols = m["ols_alpha"]["point"]
          assert min(ols, group_mean) - 1e-6 <= post <= max(ols, group_mean) + 1e-6
          ols_width = m["ols_alpha"]["ci_hi"] - m["ols_alpha"]["ci_lo"]
          post_width = m["posterior_alpha"]["ci_hi"] - m["posterior_alpha"]["ci_lo"]
          assert post_width <= ols_width + 1e-6

      ranks_ols = sorted(m["ols_rank"] for m in data["managers"])
      ranks_post = sorted(m["posterior_rank"] for m in data["managers"])
      assert ranks_ols == list(range(1, 21))
      assert ranks_post == list(range(1, 21))
  ```

- [ ] **Step 2: Run the test to verify it fails.**
  Run: `uv run pytest tests/demo_data/test_s1_ledger.py -q`
  Expected: FAIL — `ModuleNotFoundError: No module named 'quant_allocator.demo_data.s1_ledger'`.

- [ ] **Step 3: Implement `s1_ledger.py`.**

  <!-- NUMERICS-GATE: resolve before implementing — the OLS interval level and distribution are unpinned. S1 spec §3.5 pins the POSTERIOR interval at 90% credible; the design (§5) says only "OLS alpha {point, CI}" without a level or distribution. This plan provisionally renders BOTH the OLS and posterior intervals at a 90% two-sided NORMAL quantile (z = 1.6448536…, _Z90) so they are directly comparable and the "posterior no wider than OLS" invariant reduces to posterior_sd ≤ se. Confirm before certifying: OLS level (90% vs 95%) and distribution (normal z vs Student-t with T−k−1 df). If Student-t is chosen, keep the invariant test's core assertion (posterior_sd ≤ se) which is multiplier-independent. -->

  Create `src/quant_allocator/demo_data/s1_ledger.py`:
  ```python
  """S1 skill-ledger generator: roster -> closed-form shrinkage -> site/data/s1_ledger.json.

  NUMERIC OUTPUT IS HELD FOR THE NUMERICS GATE — this JSON does not publish
  until the numbers are certified. The page (gallery design §5 "S1 · Posterior
  strip") reshuffles managers between OLS and posterior rank; that reshuffle is the
  visual.
  """

  from __future__ import annotations

  import statistics
  from pathlib import Path

  import numpy as np

  from quant_allocator.demo_data._emit import SITE_DATA_DIR, write_json
  from quant_allocator.demo_data.roster import (
      GROUP_CODES,
      build_skill_ledger_roster,
  )
  from quant_allocator.flagships.skill_ledger.empirical import advisory_band, shrink_alphas

  CREDIBLE_LEVEL = 0.90
  # 90% two-sided normal quantile: P(Z <= _Z90) = 0.95. Stdlib, no magic literal.
  _Z90 = statistics.NormalDist().inv_cdf(0.95)


  def _ranks_descending(values: list[float], codes: list[str]) -> dict[str, int]:
      # Rank 1 = largest alpha; ties broken by code for determinism.
      order = sorted(range(len(values)), key=lambda i: (-values[i], codes[i]))
      return {codes[i]: rank for rank, i in enumerate(order, start=1)}


  def build(out_dir: Path = SITE_DATA_DIR) -> Path:
      roster = build_skill_ledger_roster()
      codes = [m.code for m in roster]
      groups = np.array([m.group for m in roster])
      ols = np.array([m.ols_alpha_annual for m in roster])
      ses = np.array([m.ols_se_annual for m in roster])

      result = shrink_alphas(ols, ses, groups)

      ols_points = ols.tolist()
      post_points = result.posterior_alpha.tolist()
      ols_ranks = _ranks_descending(ols_points, codes)
      post_ranks = _ranks_descending(post_points, codes)

      managers = []
      for i, m in enumerate(roster):
          managers.append(
              {
                  "code": m.code,
                  "group": m.group,
                  "months": m.months,
                  "true_alpha_annual": m.true_alpha_annual,
                  "ols_alpha": {
                      "point": ols[i],
                      "ci_lo": ols[i] - _Z90 * ses[i],
                      "ci_hi": ols[i] + _Z90 * ses[i],
                  },
                  "posterior_alpha": {
                      "point": result.posterior_alpha[i],
                      "ci_lo": result.posterior_alpha[i] - _Z90 * result.posterior_sd[i],
                      "ci_hi": result.posterior_alpha[i] + _Z90 * result.posterior_sd[i],
                  },
                  "prob_positive": result.prob_positive[i],
                  "shrinkage_weight": result.shrinkage_weight[i],
                  "ols_rank": ols_ranks[m.code],
                  "posterior_rank": post_ranks[m.code],
                  "advisory_band": advisory_band(float(result.posterior_t_ratio[i])),
              }
          )

      groups_out = []
      for group in GROUP_CODES:
          idx = next(i for i, m in enumerate(roster) if m.group == group)
          groups_out.append(
              {
                  "group": group,
                  "n": sum(1 for m in roster if m.group == group),
                  "mu_hat_annual": float(result.group_mean[idx]),
                  "tau_hat_annual": float(np.sqrt(result.group_tau2[idx])),
              }
          )

      payload = {
          "meta": {
              "generator": "s1_ledger",
              "n_managers": len(roster),
              "n_groups": len(GROUP_CODES),
              "credible_level": CREDIBLE_LEVEL,
          },
          "groups": groups_out,
          "managers": managers,
      }
      return write_json(out_dir / "s1_ledger.json", payload)
  ```
  Note on floats: `ols[i]` and friends are numpy scalars; `write_json`'s `round_floats` rounds Python floats. Convert at assembly by wrapping numeric fields in `float(...)`. **Update the four `ols_alpha`/`posterior_alpha` numeric fields, `prob_positive`, `shrinkage_weight`, and `true_alpha_annual` to `float(...)`** so the writer sees plain floats:
  ```python
                  "true_alpha_annual": float(m.true_alpha_annual),
                  "ols_alpha": {
                      "point": float(ols[i]),
                      "ci_lo": float(ols[i] - _Z90 * ses[i]),
                      "ci_hi": float(ols[i] + _Z90 * ses[i]),
                  },
                  "posterior_alpha": {
                      "point": float(result.posterior_alpha[i]),
                      "ci_lo": float(result.posterior_alpha[i] - _Z90 * result.posterior_sd[i]),
                      "ci_hi": float(result.posterior_alpha[i] + _Z90 * result.posterior_sd[i]),
                  },
                  "prob_positive": float(result.prob_positive[i]),
                  "shrinkage_weight": float(result.shrinkage_weight[i]),
  ```
  (Apply these `float(...)` wrappers in place of the raw-numpy versions shown in the first code block.)

- [ ] **Step 4: Register the builder in the CLI.**
  In `src/quant_allocator/demo_data/__main__.py`, replace the body of `_builders()`:
  ```python
  def _builders() -> dict[str, Callable[[], Path]]:
      from quant_allocator.demo_data import s1_ledger

      return {"s1_ledger": s1_ledger.build}
  ```

- [ ] **Step 5: Update the CLI test for the now-registered builder.**
  In `tests/demo_data/test_cli.py`, replace `test_build_all_with_empty_registry_is_a_noop` with:
  ```python
  def test_build_all_builds_registered_cards(tmp_path, monkeypatch):
      import quant_allocator.demo_data.s1_ledger as s1_ledger

      calls = []
      monkeypatch.setattr(s1_ledger, "build", lambda: calls.append("s1_ledger") or tmp_path)
      assert main(["build", "all"]) == 0
      assert calls == ["s1_ledger"]
  ```

- [ ] **Step 6: Run the tests to verify they pass.**
  Run: `uv run pytest tests/demo_data/test_s1_ledger.py tests/demo_data/test_cli.py -q`
  Expected: FAIL on `test_byte_for_byte_determinism_and_matches_committed` (committed file does not exist yet) — all others PASS. This is expected; the committed file is generated in the next step.

- [ ] **Step 7: Generate the committed JSON.**
  Run: `uv run python -m quant_allocator.demo_data build s1_ledger`
  Expected: prints `wrote .../site/data/s1_ledger.json`. Inspect the diff:
  Run: `git --no-pager diff --stat site/data/s1_ledger.json` (a new file with 20 managers + 2 groups).

- [ ] **Step 8: Re-run the S1 tests (now including the committed-file check).**
  Run: `uv run pytest tests/demo_data/test_s1_ledger.py -q`
  Expected: PASS (3 passed) — determinism and committed-file match now hold.

- [ ] **Step 9: Full suite + ruff + commit.**
  Run: `uv run pytest -q && uv run ruff check src tests`
  Expected: all tests pass; `All checks passed!`
  ```bash
  git add src/quant_allocator/demo_data/s1_ledger.py src/quant_allocator/demo_data/__main__.py \
          tests/demo_data/test_s1_ledger.py tests/demo_data/test_cli.py site/data/s1_ledger.json
  git commit -m "feat: S1 skill-ledger generator with committed JSON held for numerics gate"
  ```

---

## Task 5: M5 deterministic alignment engine (`saydo/alignment.py`)

The §3.2 deterministic alignment scoring — the `δ` threshold table and the aligned/partial/contradicted rule engine — as pure functions over a stated direction and a measured move. No LLM, no network.

**Files:**
- Create: `src/quant_allocator/flagships/saydo/__init__.py`
- Create: `src/quant_allocator/flagships/saydo/alignment.py`
- Test: `tests/flagships/test_alignment.py`

**Interfaces:**
- Consumes: nothing (stdlib only).
- Produces:
  - `DIRECTIONS` — the three stated-view directions `("long/constructive", "short/cautious", "neutral-explicit")` (M5 spec §3.1).
  - `DELTA_TABLE: dict[str, float]` — per-instrument materiality thresholds (M5 spec §3.2).
  - `score_alignment(direction: str, move: float, delta: float) -> str` — returns `"aligned" | "partial" | "contradicted"`.

- [ ] **Step 1: Write the failing alignment test.**
  Create `tests/flagships/test_alignment.py`:
  ```python
  import pytest

  from quant_allocator.flagships.saydo.alignment import (
      DIRECTIONS,
      score_alignment,
  )


  def test_planted_contradiction_labels_contradicted():
      # Worked rule (M5 spec §3.2): stated short/cautious + measured move against by >= delta.
      assert score_alignment("short/cautious", move=+0.6, delta=0.5) == "contradicted"


  def test_planted_aligned_labels_aligned():
      assert score_alignment("long/constructive", move=+0.6, delta=0.5) == "aligned"


  def test_long_view_scoring():
      assert score_alignment("long/constructive", move=+0.15, delta=0.10) == "aligned"
      assert score_alignment("long/constructive", move=+0.05, delta=0.10) == "partial"
      assert score_alignment("long/constructive", move=-0.15, delta=0.10) == "contradicted"


  def test_short_view_scoring():
      assert score_alignment("short/cautious", move=-0.15, delta=0.10) == "aligned"
      assert score_alignment("short/cautious", move=-0.05, delta=0.10) == "partial"
      assert score_alignment("short/cautious", move=+0.15, delta=0.10) == "contradicted"


  def test_neutral_view_scoring():
      assert score_alignment("neutral-explicit", move=0.02, delta=0.05) == "aligned"
      assert score_alignment("neutral-explicit", move=-0.02, delta=0.05) == "aligned"
      assert score_alignment("neutral-explicit", move=0.20, delta=0.05) == "contradicted"


  def test_boundary_at_exactly_delta_is_material():
      assert score_alignment("long/constructive", move=+0.10, delta=0.10) == "aligned"
      assert score_alignment("short/cautious", move=+0.10, delta=0.10) == "contradicted"


  def test_every_label_is_in_the_allowed_set():
      labels = {
          score_alignment(d, move=m, delta=0.10)
          for d in DIRECTIONS
          for m in (-0.3, -0.05, 0.0, 0.05, 0.3)
      }
      assert labels <= {"aligned", "partial", "contradicted"}


  def test_unknown_direction_raises():
      with pytest.raises(ValueError):
          score_alignment("mildly bullish", move=0.1, delta=0.1)
  ```

- [ ] **Step 2: Run the alignment test to verify it fails.**
  Run: `uv run pytest tests/flagships/test_alignment.py -q`
  Expected: FAIL — `ModuleNotFoundError: No module named 'quant_allocator.flagships.saydo'`.

- [ ] **Step 3: Implement `alignment.py`.**

  <!-- NUMERICS-GATE: resolve before implementing — the delta table values are UNCALIBRATED authored constants. M5 spec §3.2/§4 says each instrument-class delta is calibrated from the simulator's honest-wander distribution so the false-contradiction rate sits at a stated budget (<= 1-in-20 views); the demo uses authored constants pending that calibration. Confirm the beta-unit delta (0.10) and net-exposure delta (0.05) before certifying. Also confirm two rule choices the spec §3.2 does not fully pin: (a) a sub-threshold move against the stated direction (|move| < delta) is labeled "partial" here (the dead-band = "no material statement"), since {aligned, partial, contradicted} has no neutral label; (b) the §3.2 second partial clause ("sign right but timing outside the stated horizon") is a live-build refinement and is NOT implemented — the demo scores the move strictly over the stated horizon window (see m5_saydo.py), so it is never exercised. -->

  Create `src/quant_allocator/flagships/saydo/__init__.py`:
  ```python
  """M5 say-do gap monitor. alignment.py is the deterministic scorer (no LLM)."""
  ```
  Create `src/quant_allocator/flagships/saydo/alignment.py`:
  ```python
  """M5 §3.2 deterministic alignment scoring.

  The LLM only reads text; the scoring is deterministic code — nothing
  probabilistic touches the label (M5 spec §3). This module compares a stated
  direction against the realized move of the measured series over the horizon,
  using a per-instrument materiality dead-band delta.
  """

  from __future__ import annotations

  # M5 spec §3.1 stated-view directions.
  DIRECTIONS = ("long/constructive", "short/cautious", "neutral-explicit")

  # M5 spec §3.2: per-instrument-class materiality thresholds, declared in one
  # table so a reviewer sees every rule at once. UNCALIBRATED demo constants
  # (see the NUMERICS-GATE note in this task): factor beta in beta units, net in
  # net-exposure units.
  DELTA_TABLE: dict[str, float] = {
      "beta_market": 0.10,
      "beta_size": 0.10,
      "beta_value": 0.10,
      "beta_momentum": 0.10,
      "net": 0.05,
  }

  _DIRECTION_SIGN = {"long/constructive": 1.0, "short/cautious": -1.0}


  def score_alignment(direction: str, move: float, delta: float) -> str:
      # M5 spec §3.2. neutral-explicit: aligned if the exposure stays within +/-delta
      # of its start; otherwise it moved away from the stated flat stance.
      if direction == "neutral-explicit":
          return "aligned" if abs(move) <= delta else "contradicted"
      if direction not in _DIRECTION_SIGN:
          raise ValueError(
              f"unknown direction {direction!r}; expected one of {DIRECTIONS}"
          )
      # Project the move onto the stated direction: positive = moved as stated.
      projected = _DIRECTION_SIGN[direction] * move
      if projected >= delta:  # aligned: moved in stated direction by >= delta
          return "aligned"
      if projected <= -delta:  # contradicted: moved against stated direction by >= delta
          return "contradicted"
      return "partial"  # |move| < delta: inside the dead-band, no material statement
  ```

- [ ] **Step 4: Run the alignment test to verify it passes.**
  Run: `uv run pytest tests/flagships/test_alignment.py -q`
  Expected: PASS (8 passed).

- [ ] **Step 5: Ruff + commit.**
  Run: `uv run ruff check src/quant_allocator/flagships/saydo tests/flagships/test_alignment.py`
  Expected: `All checks passed!`
  ```bash
  git add src/quant_allocator/flagships/saydo tests/flagships/test_alignment.py
  git commit -m "feat: M5 deterministic say-do alignment engine with delta threshold table"
  ```

---

## Task 6: M5 generator + committed JSON + self-consistency tests (`m5_saydo.py`)

> **Numeric output is HELD FOR NUMERICS GATE — do not merge or publish until certified.**

Builds one synthetic manager's exposure paths from the simulator, scores three authored views against them with the Task 5 engine, and writes `site/data/m5_saydo.json`. Two views align; one contradicts (the centerpiece). Letter excerpts, directions, themes, convictions, and horizons are authored constants (gallery design §5; M5 spec §4 "Demo vs. live").

**Files:**
- Create: `src/quant_allocator/demo_data/m5_saydo.py`
- Modify: `src/quant_allocator/demo_data/__main__.py` (register `m5_saydo`)
- Create: `site/data/m5_saydo.json` (generated output — held for gate)
- Test: `tests/demo_data/test_m5_saydo.py`
- Modify: `tests/demo_data/test_cli.py` (registry now has two cards)

**Interfaces:**
- Consumes: `simulator.market.{MarketConfig, simulate_market}`, `simulator.manager.{ManagerConfig, simulate_manager}`, `simulator.tiers.emit_tiers`; `flagships.saydo.alignment.{score_alignment, DELTA_TABLE}`; `_emit.{SITE_DATA_DIR, write_json}`.
- Produces: `build(out_dir: Path = SITE_DATA_DIR) -> Path` writing `m5_saydo.json`; module constants `BASE_SEED = 20260706`, `MANAGER_CODE = "M07"`, `LETTER_MONTH_INDEX = 3`, `HORIZON_MONTHS = 6`, and the authored `VIEWS` list.

- [ ] **Step 1: Write the failing self-consistency test.**
  Create `tests/demo_data/test_m5_saydo.py`:
  ```python
  import json
  from collections import Counter

  from quant_allocator.demo_data import m5_saydo
  from quant_allocator.demo_data._emit import SITE_DATA_DIR


  def _load(path):
      return json.loads(path.read_text(encoding="utf-8"))


  def test_schema_is_valid(tmp_path):
      data = _load(m5_saydo.build(out_dir=tmp_path))
      assert data["meta"]["manager_code"] == "M07"
      assert data["meta"]["horizon_months"] == 6
      assert len(data["views"]) == 3
      for v in data["views"]:
          assert {"view_id", "letter_date", "direction", "theme", "instrument",
                  "horizon_months", "conviction", "quote", "measured", "label"} <= set(v)
          assert set(v["measured"]) == {"start", "end", "move", "delta"}
          assert v["direction"] in {"long/constructive", "short/cautious", "neutral-explicit"}
      assert set(data["exposure_paths"]) == {"beta_market", "beta_value", "beta_momentum", "net"}


  def test_labels_are_two_aligned_one_contradicted(tmp_path):
      data = _load(m5_saydo.build(out_dir=tmp_path))
      labels = Counter(v["label"] for v in data["views"])
      assert all(lbl in {"aligned", "partial", "contradicted"} for lbl in labels)
      assert labels["aligned"] == 2
      assert labels["contradicted"] == 1


  def test_byte_for_byte_determinism_and_matches_committed(tmp_path):
      first = m5_saydo.build(out_dir=tmp_path).read_bytes()
      second = m5_saydo.build(out_dir=tmp_path).read_bytes()
      assert first == second
      committed = (SITE_DATA_DIR / "m5_saydo.json").read_bytes()
      assert first == committed


  def test_measured_move_matches_start_and_end(tmp_path):
      data = _load(m5_saydo.build(out_dir=tmp_path))
      for v in data["views"]:
          assert abs(v["measured"]["move"] - (v["measured"]["end"] - v["measured"]["start"])) < 1e-6
  ```

- [ ] **Step 2: Run the test to verify it fails.**
  Run: `uv run pytest tests/demo_data/test_m5_saydo.py -q`
  Expected: FAIL — `ModuleNotFoundError: No module named 'quant_allocator.demo_data.m5_saydo'`.

- [ ] **Step 3: Implement `m5_saydo.py`.**

  <!-- NUMERICS-GATE: resolve before implementing — three demo-construction choices to confirm at the numerics gate. (1) Instrument mapping: the design §5 example themes (duration, energy equities) do not exist in the equity simulator, which emits factor betas + net; the three authored views are mapped onto beta_momentum / beta_value / net, and the "cautious on duration" example is rendered as "trimmed momentum risk" on beta_momentum. (2) The base seed (20260706), manager (IC 0.08, seed 1), letter month (index 3) and horizon (6 months) were chosen so the measured moves are beta_value +0.173 (long -> aligned), beta_momentum +0.203 (stated short -> contradicted), net 0.0 (neutral -> aligned); if a numpy build yields different draws, run _scan_seeds() (Step 3b) and update BASE_SEED so the label multiset stays {aligned, aligned, contradicted}. (3) The delta values come from alignment.DELTA_TABLE (also gated in Task 5). -->

  Create `src/quant_allocator/demo_data/m5_saydo.py`:
  ```python
  """M5 say-do generator: simulator exposure paths + three authored views -> JSON.

  NUMERIC OUTPUT IS HELD FOR THE NUMERICS GATE — this JSON does not publish
  until certified. The exposure paths are measured from the simulator; the letter
  excerpts, directions, themes, convictions and horizons are AUTHORED constants
  (gallery design §5; M5 spec §4 "Demo vs. live"). Two views align with the book;
  one contradicts it (the visual centerpiece). The page carries the honesty note
  that the live build requires the synthetic-letter eval harness to pass.
  """

  from __future__ import annotations

  from pathlib import Path

  from quant_allocator.demo_data._emit import SITE_DATA_DIR, write_json
  from quant_allocator.flagships.saydo.alignment import DELTA_TABLE, score_alignment
  from quant_allocator.simulator.manager import ManagerConfig, simulate_manager
  from quant_allocator.simulator.market import MarketConfig, simulate_market
  from quant_allocator.simulator.tiers import emit_tiers

  BASE_SEED = 20260706
  MANAGER_CODE = "M07"
  STRATEGY = "equity_long_short"
  N_ASSETS = 300
  N_MONTHS = 18
  MANAGER_IC = 0.08
  MANAGER_SEED = 1
  LETTER_MONTH_INDEX = 3
  HORIZON_MONTHS = 6
  _PATH_INSTRUMENTS = ("beta_market", "beta_value", "beta_momentum", "net")

  # Authored letter excerpts. Each view maps to a measurable exposure the simulator
  # emits (M5 spec §3.1 instrument mapping). Directions/themes/quotes are fixed
  # constants; the label is computed by the deterministic engine from the measured
  # move (M5 spec §3.2).
  VIEWS = [
      {
          "view_id": 1,
          "direction": "neutral-explicit",
          "theme": "disciplined net exposure",
          "instrument": "net",
          "conviction": 3,
          "quote": (
              "We continue to run the book at a disciplined, near-flat net "
              "exposure and have not chased the rally."
          ),
      },
      {
          "view_id": 2,
          "direction": "long/constructive",
          "theme": "value factor tilt",
          "instrument": "beta_value",
          "conviction": 2,
          "quote": (
              "We have leaned further into cheaper, higher-quality names, "
              "adding to our value tilt over the coming two quarters."
          ),
      },
      {
          "view_id": 3,
          "direction": "short/cautious",
          "theme": "trimmed momentum risk",
          "instrument": "beta_momentum",
          "conviction": 2,
          "quote": (
              "Given how crowded momentum has become, we have been trimming "
              "our exposure to the factor and expect to stay cautious."
          ),
      },
  ]


  def _exposure_paths():
      market = simulate_market(MarketConfig(n_assets=N_ASSETS, n_months=N_MONTHS, seed=BASE_SEED))
      history = simulate_manager(
          market, ManagerConfig(information_coefficient=MANAGER_IC, seed=MANAGER_SEED)
      )
      exposures = emit_tiers(market, history).exposures
      exposures.index = exposures.index.astype(str)  # PeriodIndex -> "YYYY-MM"
      return exposures


  def build(out_dir: Path = SITE_DATA_DIR) -> Path:
      exposures = _exposure_paths()
      months = list(exposures.index)
      start_i = LETTER_MONTH_INDEX
      end_i = LETTER_MONTH_INDEX + HORIZON_MONTHS
      letter_date = months[start_i]

      views_out = []
      for view in VIEWS:
          instrument = view["instrument"]
          delta = DELTA_TABLE[instrument]
          series = exposures[instrument]
          start = float(series.iloc[start_i])
          end = float(series.iloc[end_i])
          move = end - start
          views_out.append(
              {
                  "view_id": view["view_id"],
                  "letter_date": letter_date,
                  "direction": view["direction"],
                  "theme": view["theme"],
                  "instrument": instrument,
                  "horizon_months": HORIZON_MONTHS,
                  "conviction": view["conviction"],
                  "quote": view["quote"],
                  "measured": {"start": start, "end": end, "move": move, "delta": delta},
                  "label": score_alignment(view["direction"], move, delta),
              }
          )

      exposure_paths = {
          instrument: [
              {"month": month, "value": float(exposures[instrument].iloc[i])}
              for i, month in enumerate(months)
          ]
          for instrument in _PATH_INSTRUMENTS
      }

      payload = {
          "meta": {
              "generator": "m5_saydo",
              "manager_code": MANAGER_CODE,
              "strategy": STRATEGY,
              "horizon_months": HORIZON_MONTHS,
          },
          "delta_table": {k: DELTA_TABLE[k] for k in _PATH_INSTRUMENTS},
          "views": views_out,
          "exposure_paths": exposure_paths,
      }
      return write_json(out_dir / "m5_saydo.json", payload)


  def _scan_seeds(seeds=range(0, 100)) -> None:
      # Recovery helper (see the NUMERICS-GATE note): print seeds whose three authored
      # views yield exactly {aligned, aligned, contradicted}. Not part of the build.
      from collections import Counter

      for seed in seeds:
          market = simulate_market(MarketConfig(n_assets=N_ASSETS, n_months=N_MONTHS, seed=seed))
          history = simulate_manager(
              market, ManagerConfig(information_coefficient=MANAGER_IC, seed=MANAGER_SEED)
          )
          exposures = emit_tiers(market, history).exposures
          labels = Counter()
          for view in VIEWS:
              series = exposures[view["instrument"]]
              move = float(series.iloc[LETTER_MONTH_INDEX + HORIZON_MONTHS]) - float(
                  series.iloc[LETTER_MONTH_INDEX]
              )
              labels[score_alignment(view["direction"], move, DELTA_TABLE[view["instrument"]])] += 1
          if labels["aligned"] == 2 and labels["contradicted"] == 1:
              print(f"seed {seed}: {dict(labels)}")
  ```

- [ ] **Step 4: Register the builder in the CLI.**
  In `src/quant_allocator/demo_data/__main__.py`, replace the body of `_builders()`:
  ```python
  def _builders() -> dict[str, Callable[[], Path]]:
      from quant_allocator.demo_data import m5_saydo, s1_ledger

      return {"m5_saydo": m5_saydo.build, "s1_ledger": s1_ledger.build}
  ```

- [ ] **Step 5: Update the CLI test to cover both registered cards.**
  In `tests/demo_data/test_cli.py`, replace `test_build_all_builds_registered_cards` with:
  ```python
  def test_build_all_builds_registered_cards(tmp_path, monkeypatch):
      import quant_allocator.demo_data.m5_saydo as m5_saydo
      import quant_allocator.demo_data.s1_ledger as s1_ledger

      calls = []
      monkeypatch.setattr(s1_ledger, "build", lambda: calls.append("s1_ledger") or tmp_path)
      monkeypatch.setattr(m5_saydo, "build", lambda: calls.append("m5_saydo") or tmp_path)
      assert main(["build", "all"]) == 0
      assert sorted(calls) == ["m5_saydo", "s1_ledger"]
  ```

- [ ] **Step 6: Run the tests to verify pre-commit state.**
  Run: `uv run pytest tests/demo_data/test_m5_saydo.py tests/demo_data/test_cli.py -q`
  Expected: FAIL only on `test_byte_for_byte_determinism_and_matches_committed` (committed file not written yet); all other assertions PASS. Critically, `test_labels_are_two_aligned_one_contradicted` must PASS — if it fails, the seed no longer yields the intended labels: run `uv run python -c "from quant_allocator.demo_data.m5_saydo import _scan_seeds; _scan_seeds()"`, set `BASE_SEED` to a printed seed, and re-run.

- [ ] **Step 7: Generate the committed JSON.**
  Run: `uv run python -m quant_allocator.demo_data build m5_saydo`
  Expected: prints `wrote .../site/data/m5_saydo.json`. Inspect: `git --no-pager diff --stat site/data/m5_saydo.json`.

- [ ] **Step 8: Re-run the M5 tests (now including the committed-file check).**
  Run: `uv run pytest tests/demo_data/test_m5_saydo.py -q`
  Expected: PASS (4 passed).

- [ ] **Step 9: Full suite + ruff + commit.**
  Run: `uv run pytest -q && uv run ruff check src tests`
  Expected: all tests pass; `All checks passed!`
  ```bash
  git add src/quant_allocator/demo_data/m5_saydo.py src/quant_allocator/demo_data/__main__.py \
          tests/demo_data/test_m5_saydo.py tests/demo_data/test_cli.py site/data/m5_saydo.json
  git commit -m "feat: M5 say-do generator with committed JSON held for numerics gate"
  ```

---

## Final verification (whole plan)

- [ ] **Regenerate both cards and confirm no diff** (proves the committed files match current code):
  Run: `uv run python -m quant_allocator.demo_data build all && git status --porcelain site/data/`
  Expected: `build all` prints both `wrote …` lines; `git status --porcelain site/data/` prints nothing (committed JSON is byte-identical to regenerated output).
- [ ] **Full suite + ruff clean:**
  Run: `uv run pytest -q && uv run ruff check src tests`
  Expected: all tests pass; `All checks passed!`
- [ ] **Confirm `demo_data` is never imported by `quant_allocator.site`:**
  Run: `grep -rn "demo_data" src/quant_allocator/site/ || echo "clean: site never imports demo_data"`
  Expected: `clean: site never imports demo_data`.
- [ ] **Reminder:** both `site/data/*.json` files remain HELD FOR THE NUMERICS GATE. Do not merge to `main` or enable publication until the lead reviewer certifies the numbers. Resolve every `<!-- NUMERICS-GATE: … -->` marker (Tasks 2, 3, 4, 5, 6) at that gate.
