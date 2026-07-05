# War-Game Sessions 1–2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. **Exception:** Part A tasks (A1–A3) are executed inline by the orchestrator — they require Agent-tool dispatch with model pinning and the lead reviewer-level QC, per spec Section 9.

**Goal:** Execute the dual-track opening of the campaign in `docs/superpowers/specs/2026-07-05-quant-allocator-wargame-design.md` — five landscape-sweep briefs committed to `docs/briefs/`, and a working substrate slice (synthetic manager simulator + Ken French factor adapter) with tests.

**Architecture:** Part A dispatches five parallel research sub-agents (A/B/D/E on senior, C on the lead reviewer) from verbatim prompt files, then QCs their briefs against a checklist. Part B builds the substrate as a `src/` layout Python package: a factor-model market generator, an equity L/S manager simulator with dialable ground truth, a three-tier data emitter, crude returns-only macro/credit generators, and a Ken French data adapter with offline-testable parsing.

**Tech Stack:** Python ≥3.11, uv, pandas, numpy; pytest + ruff (dev). No other dependencies.

## Global Constraints

- Python ≥3.11 (from `pyproject.toml`); package name `quant_allocator`, `src/` layout.
- Runtime dependencies limited to `pandas` and `numpy`; dev dependencies `pytest` and `ruff`. Adding any other dependency requires a plan change.
- **Repo is treated as public at all times:** no employer-internal facts, no manager names, no non-public information — in code, briefs, prompts, or commit messages (spec Section 9).
- **Substrate contains zero analytics** — generators, adapters, and emitters only (spec Section 7). Any metric beyond raw emission belongs to post-convergence work.
- All randomness flows from `numpy.random.default_rng(config.seed)`; every config dataclass carries a `seed` field. Same config ⇒ identical output.
- All return series are **decimals** (0.01 = 1%), monthly frequency, indexed by `pd.PeriodIndex` with `freq="M"`.
- Point-in-time discipline: nothing in an emitted view may leak information a real allocator would not have at that date.
- Network access only inside `adapters/` download functions; all parsing logic must be testable offline. Network tests carry `@pytest.mark.network` and are excluded by default.
- Deferred from spec Section 7, planned post-convergence (serve flagship builds, not convergence): SEC EDGAR 13F adapter, N-PORT/ETF holdings adapters, fund/index return-series adapter; simulator dials for crowding participation and vol targeting, factor correlation structure, and regime dynamics (added when an idea card's power test needs them).

## File Structure

```
docs/briefs/prompts/sweep-{a,b,c,d,e}.md     # verbatim sub-agent prompts (Task A1)
docs/briefs/sweep-{a,b,c,d,e}-brief.md       # sub-agent outputs (Task A2)
src/quant_allocator/__init__.py
src/quant_allocator/simulator/__init__.py
src/quant_allocator/simulator/market.py       # factor-model market generator (Task B2)
src/quant_allocator/simulator/manager.py      # equity L/S book simulator (Task B3)
src/quant_allocator/simulator/tiers.py        # three-tier data emitter (Task B4)
src/quant_allocator/simulator/returns_only.py # crude macro/credit generators (Task B5)
src/quant_allocator/adapters/__init__.py
src/quant_allocator/adapters/french.py        # Ken French factor adapter (Task B6)
tests/simulator/test_market.py
tests/simulator/test_manager.py
tests/simulator/test_tiers.py
tests/simulator/test_returns_only.py
tests/adapters/test_french.py
pyproject.toml                                # modify (Task B1)
README.md                                     # modify (Task B1)
main.py                                       # delete (Task B1, uv scaffold artifact)
```

---

# Part A — Track 1: Landscape sweeps (orchestrator-inline)

### Task A1: Write the five sweep prompt files

**Files:**
- Create: `docs/briefs/prompts/sweep-a.md` … `docs/briefs/prompts/sweep-e.md`

**Interfaces:**
- Produces: five self-contained prompts consumed verbatim by Task A2's Agent dispatches.

Every prompt shares this frame (repeated in full in each file): the researcher persona, the allocator context, the exact four-section output contract, and the guardrails. The sweep-specific mission/questions/sources vary.

- [ ] **Step 1: Write `docs/briefs/prompts/sweep-a.md`**

```markdown
You are a senior quantitative researcher producing a landscape brief for the
quant team of a large institutional allocator (sovereign-wealth-scale,
fund-of-funds style) that invests in external hedge fund managers across
strategies (fundamental equity long/short, macro, credit, quant). The team is
designing analytics that work under tiered transparency: monthly returns for
all managers, exposure/risk-report summaries for many, position-level
transparency for a few.

MISSION: Map what sophisticated allocators and fund-of-funds quant teams
actually do and publish — so this team knows what is table stakes versus
genuine white space.

QUESTIONS TO ANSWER:
- What quantitative manager-evaluation and portfolio-analytics practices do
  leading allocators (e.g., CPPIB, Future Fund, CalSTRS, NZ Super) disclose in
  public reports, papers, and talks?
- What methodologies do consultants (Albourne, Aksia, Mercer, Cambridge)
  publicly describe for manager selection and monitoring?
- What does the academic fund-selection canon conclude, and with what
  caveats: performance persistence; Bayesian fund alphas (Baks–Metrick–
  Wachter; Pastor–Stambaugh); false-discovery control in manager selection
  (Barras–Scaillet–Wermers); evidence on fund-of-funds value-add?
- Which of these practices survive contact with monthly-frequency,
  small-sample data, and which are known to be noise?

SEED SOURCES (start here, then go well beyond): the named papers above; SSRN;
Journal of Portfolio Management; allocator annual reports and published
investment frameworks; consultant white papers.

OUTPUT — return ONLY a markdown brief, 900–1800 words, with exactly these
four sections:
## 1. State of practice
## 2. Best sources (annotated links)
## 3. White space
## 4. Implications for idea cards
(Section 4: at least 5 concrete bullets, each naming the allocator decision
it improves: select / size / monitor / engage / redeem.)

GUARDRAILS: public sources only; include working URLs; never fabricate a
citation — if unsure a source exists, say so explicitly; flag low-confidence
claims; do not include any non-public or firm-internal information.
```

- [ ] **Step 2: Write `docs/briefs/prompts/sweep-b.md`**

```markdown
You are a senior quantitative researcher producing a landscape brief for the
quant team of a large institutional allocator (sovereign-wealth-scale,
fund-of-funds style) that invests in external hedge fund managers across
strategies (fundamental equity long/short, macro, credit, quant). The team is
designing analytics that work under tiered transparency: monthly returns for
all managers, exposure/risk-report summaries for many, position-level
transparency for a few.

MISSION: Reconstruct, from public information, the analytics catalog of
multi-manager platform "PM Engagement"-style quant teams (Balyasny PM
Engagement, and equivalents at Citadel, Point72, Millennium) — the frontier
of PM-facing portfolio analytics — and judge which pieces transplant to each
allocator data tier.

QUESTIONS TO ANSWER:
- What analytics do these teams run for their PMs? Enumerate concretely:
  sizing curves, alpha-decay curves, hit rate/slugging, entry/exit timing,
  PM report cards, crowding dashboards, factor-hygiene reviews, gross/net and
  hedging discipline, short-book quality — and anything else you find.
- How do they engage PMs (cadence, artifacts, framing) so analytics get used?
- For each analytic: which data tier does it minimally require —
  returns-only, exposure summaries, or position-level transparency?
- What do platform alumni and job postings reveal about tooling and skills?

SEED SOURCES (start here, then go well beyond): job postings for "PM
Engagement" / "Portfolio Consulting" / "Risk Advisory" quant roles at
multi-manager platforms; podcasts and conference talks by platform quant
leaders; alumni writing; press profiles of platform risk/analytics functions.

OUTPUT — return ONLY a markdown brief, 900–1800 words, with exactly these
four sections:
## 1. State of practice
## 2. Best sources (annotated links)
## 3. White space
## 4. Implications for idea cards
(Section 4: at least 5 concrete bullets, each naming the allocator decision
it improves: select / size / monitor / engage / redeem. Section 1 must
contain a named catalog of at least 10 distinct analytics with the minimum
data tier for each.)

GUARDRAILS: public sources only; include working URLs; never fabricate a
citation — if unsure a source exists, say so explicitly; flag low-confidence
claims; do not include any non-public or firm-internal information.
```

- [ ] **Step 3: Write `docs/briefs/prompts/sweep-c.md`**

```markdown
You are a senior quantitative researcher producing a landscape brief for the
quant team of a large institutional allocator (sovereign-wealth-scale,
fund-of-funds style) that invests in external hedge fund managers across
strategies (fundamental equity long/short, macro, credit, quant). The team is
designing analytics that work under tiered transparency: monthly returns for
all managers, exposure/risk-report summaries for many, position-level
transparency for a few.

MISSION: Deliver a per-method robustness verdict for the statistics of
manager evaluation at realistic sample sizes — 36–60 monthly observations,
tens of managers. This brief gates which methods the team is allowed to
build on, so the statistical judgment must be rigorous and explicit.

QUESTIONS TO ANSWER — for EACH method below, state what it estimates, its
minimum data tier, its statistical power at 36–60 monthly observations
(with reasoning: estimator variance, bias, multiple-testing exposure), and a
verdict (robust / usable-with-shrinkage / noise-theater at this N):
- Returns-based: factor-model alpha (OLS and conditional), Sharpe-style
  returns-based style analysis, Fung–Hsieh seven-factor model for
  macro/trend, credit factor models.
- Holdings-based: active share, information coefficients, hit rate/slugging,
  trade-level skill decomposition, sizing-skill curves, alpha-decay curves.
- Cross-sectional: performance persistence tests, hierarchical/Bayesian
  shrinkage of manager alphas, false-discovery-rate control.
- Regime/drawdown: drawdown-distribution analysis, regime-conditional
  performance, style-drift detection.
- Crowding: overlap measures, short-interest-based crowding, liquidity-
  adjusted concentration.

SEED SOURCES (start here, then go well beyond): Fung & Hsieh (2004);
Grinold & Kahn; Pastor–Stambaugh (2002); Baks–Metrick–Wachter (2001);
Barras–Scaillet–Wermers (2010); Getmansky–Lo–Makarov (2004) on smoothed
returns; literature on Sharpe-ratio standard errors (Lo 2002; Ledoit–Wolf).

OUTPUT — return ONLY a markdown brief, 900–1800 words, with exactly these
four sections:
## 1. State of practice
## 2. Best sources (annotated links)
## 3. White space
## 4. Implications for idea cards
(Section 1 must contain the per-method verdict table. Section 4: at least 5
concrete bullets, each naming the allocator decision it improves: select /
size / monitor / engage / redeem.)

GUARDRAILS: public sources only; include working URLs; never fabricate a
citation — if unsure a source exists, say so explicitly; flag low-confidence
claims; do not include any non-public or firm-internal information.
```

- [ ] **Step 4: Write `docs/briefs/prompts/sweep-d.md`**

```markdown
You are a senior quantitative researcher producing a landscape brief for the
quant team of a large institutional allocator (sovereign-wealth-scale,
fund-of-funds style) that invests in external hedge fund managers across
strategies (fundamental equity long/short, macro, credit, quant). The team is
designing analytics that work under tiered transparency: monthly returns for
all managers, exposure/risk-report summaries for many, position-level
transparency for a few.

MISSION: Inventory the data and tooling landscape — what the team can
prototype on publicly, and what vendors already solve — so no candidate
project rebuilds an existing product.

QUESTIONS TO ANSWER:
- Public data: SEC EDGAR 13F (coverage, lag, known pitfalls), N-PORT, short
  interest, ETF holdings, Ken French / AQR / q-factor libraries, HFR / SG /
  BarclayHedge index families (what is free vs licensed). For each: access
  method, update frequency, point-in-time caveats, survivorship issues.
- Vendors: Barra/Axioma factor risk, Novus (portfolio intelligence for
  allocators), Essentia Analytics (behavioral alpha for PMs), MSCI crowding,
  StyleAnalytics — what does each actually sell, to whom, at what depth?
- Open source: skfolio, Riskfolio-Lib, alphalens, empyrical, PyMC — maturity,
  scope, gaps for allocator-style analytics.
- For each vendor category: what is the build-vs-buy line for an in-house
  allocator quant team?

SEED SOURCES (start here, then go well beyond): SEC EDGAR documentation;
Ken French data library; AQR data sets page; vendor product pages and case
studies; GitHub repos and docs of the named libraries.

OUTPUT — return ONLY a markdown brief, 900–1800 words, with exactly these
four sections:
## 1. State of practice
## 2. Best sources (annotated links)
## 3. White space
## 4. Implications for idea cards
(Section 1 must contain a build-vs-buy table by capability area. Section 4:
at least 5 concrete bullets, each naming the allocator decision it improves:
select / size / monitor / engage / redeem.)

GUARDRAILS: public sources only; include working URLs; never fabricate a
citation — if unsure a source exists, say so explicitly; flag low-confidence
claims; do not include any non-public or firm-internal information.
```

- [ ] **Step 5: Write `docs/briefs/prompts/sweep-e.md`**

```markdown
You are a senior quantitative researcher producing a landscape brief for the
quant team of a large institutional allocator (sovereign-wealth-scale,
fund-of-funds style) that invests in external hedge fund managers across
strategies (fundamental equity long/short, macro, credit, quant). The team is
designing analytics that work under tiered transparency: monthly returns for
all managers, exposure/risk-report summaries for many, position-level
transparency for a few.

MISSION: Establish the adoption doctrine — why PM- and manager-facing
analytics get used versus shelved, and how quantitative teams package
analysis so investment professionals act on it. Both the allocator's role
and the platform PM-engagement role weight communication and influence
heavily; this brief is the evidence base for that.

QUESTIONS TO ANSWER:
- What is documented (case studies, practitioner writing, vendor material,
  academic work on advice-taking and algorithm aversion) about getting
  fundamental investors to adopt quantitative feedback?
- What artifact designs work: tear sheets, quarterly business reviews, PM
  packs, dashboards? What cadence and framing?
- Trust dynamics of engagement: how do teams position analytics as helping
  the manager rather than auditing them — and what happens to data access
  (transparency) when a manager feels policed?
- How do platform teams "monetize" internal research findings — turn a brief
  into changed PM behavior and P&L?
- What failure modes are documented: dashboard graveyards, metric gaming,
  analytics that damaged the relationship?

SEED SOURCES (start here, then go well beyond): Essentia Analytics case
studies and published PM-behavior research; practitioner essays by platform
and allocator quants; literature on algorithm aversion (Dietvorst et al.)
and advice utilization; product-adoption postmortems in finance.

OUTPUT — return ONLY a markdown brief, 900–1800 words, with exactly these
four sections:
## 1. State of practice
## 2. Best sources (annotated links)
## 3. White space
## 4. Implications for idea cards
(Section 4: at least 5 concrete bullets, each naming the allocator decision
it improves: select / size / monitor / engage / redeem.)

GUARDRAILS: public sources only; include working URLs; never fabricate a
citation — if unsure a source exists, say so explicitly; flag low-confidence
claims; do not include any non-public or firm-internal information.
```

- [ ] **Step 6: Commit**

```bash
git add docs/briefs/prompts/
git commit -m "docs: add verbatim prompts for landscape sweeps A-E"
```

### Task A2: Dispatch the five sweeps in parallel and commit the briefs

**Files:**
- Create: `docs/briefs/sweep-a-brief.md` … `docs/briefs/sweep-e-brief.md`

**Interfaces:**
- Consumes: the five prompt files from Task A1, passed verbatim as Agent prompts.
- Produces: five markdown briefs consumed by Task A3 QC and by the convergence session.

- [ ] **Step 1: Dispatch all five agents in one parallel batch**

One Agent call per sweep, all in a single message, `run_in_background: true`:

| Sweep | Prompt file | `model` | Rationale (spec §9) |
| --- | --- | --- | --- |
| A | `docs/briefs/prompts/sweep-a.md` | `senior` | retrieval-bound |
| B | `docs/briefs/prompts/sweep-b.md` | `senior` | retrieval-bound |
| C | `docs/briefs/prompts/sweep-c.md` | `lead-reviewer` | embedded statistical judgment |
| D | `docs/briefs/prompts/sweep-d.md` | `senior` | retrieval-bound |
| E | `docs/briefs/prompts/sweep-e.md` | `senior` | retrieval-bound |

Each dispatch prepends one line to the file content: "Your final message will
be saved verbatim as the brief file — return ONLY the markdown brief."

- [ ] **Step 2: On completion, save each agent's final message verbatim**

Write each result unchanged to `docs/briefs/sweep-<letter>-brief.md`. No
editing at this step — QC happens in Task A3 so the raw output is preserved
in git history.

- [ ] **Step 3: Commit**

```bash
git add docs/briefs/sweep-*.md
git commit -m "docs: add raw landscape sweep briefs A-E"
```

### Task A3: QC each brief; re-dispatch targeted follow-ups for gaps

**Files:**
- Modify: `docs/briefs/sweep-a-brief.md` … `docs/briefs/sweep-e-brief.md` (only if follow-ups add material)

**Interfaces:**
- Consumes: the five raw briefs from Task A2.
- Produces: QC-passed briefs — the certified inputs to the convergence session.

- [ ] **Step 1: Score every brief against this checklist (orchestrator, the lead reviewer-level)**

Per brief, all must hold:
1. All four required sections present; 800–2000 words.
2. ≥8 distinct credible sources with URLs; spot-check 3 URLs per brief for existence and accurate representation (fabricated citations fail the brief).
3. "White space" names ≥3 gaps specific to the *allocator* seat, not generic quant gaps.
4. "Implications for idea cards" has ≥5 bullets, each mapped to select/size/monitor/engage/redeem.
5. Sweep-specific: B contains the ≥10-analytic catalog with minimum data tier each; C contains the per-method verdict table with explicit small-N reasoning; D contains the build-vs-buy table.
6. No non-public information; no firm-internal references.

- [ ] **Step 2: For each failed criterion, dispatch one targeted follow-up agent**

Same model tier as the original sweep. The follow-up prompt = the original
prompt file content plus: "A prior brief failed this QC criterion:
<criterion>. Produce ONLY the missing material as a markdown fragment."
Append the fragment under the relevant section of the brief file, marked
`<!-- QC follow-up -->`.

- [ ] **Step 3: Commit QC results**

```bash
git add docs/briefs/
git commit -m "docs: QC-pass sweep briefs, append targeted follow-ups"
```

---

# Part B — Track 2: Substrate slice (TDD)

### Task B1: Package scaffolding

**Files:**
- Modify: `pyproject.toml`, `README.md`
- Delete: `main.py`
- Create: `src/quant_allocator/__init__.py`, `src/quant_allocator/simulator/__init__.py`, `src/quant_allocator/adapters/__init__.py`, `tests/__init__.py` (empty), `tests/test_package.py`

**Interfaces:**
- Produces: importable `quant_allocator` package under `src/` layout; `uv run pytest` wired with the `network` marker excluded by default. All later tasks assume this.

- [ ] **Step 1: Add dependencies**

```bash
uv add pandas numpy
uv add --dev pytest ruff
```

- [ ] **Step 2: Configure pytest and delete the scaffold artifact**

In `pyproject.toml`, set
`description = "Public-data adapters and synthetic-manager simulator for allocator analytics research"`,
then append:

```toml
[tool.pytest.ini_options]
pythonpath = ["src"]
testpaths = ["tests"]
addopts = "-m 'not network'"
markers = ["network: requires internet access; excluded by default"]

[tool.ruff]
line-length = 100
```

```bash
rm main.py
```

- [ ] **Step 3: Create package skeleton and smoke test**

All `__init__.py` files empty except `src/quant_allocator/__init__.py`:

```python
"""Public-data adapters and synthetic-manager simulator for allocator analytics research."""
```

`tests/test_package.py`:

```python
def test_package_imports():
    import quant_allocator  # noqa: F401
```

- [ ] **Step 4: Replace README content**

`README.md`:

```markdown
# quant-allocator

Research substrate for allocator-side hedge fund analytics: public-data
adapters and a synthetic manager simulator with dialable ground truth,
emitting three transparency tiers (returns-only, exposures, positions).
All data here is public or synthetic by design.

Campaign spec: `docs/superpowers/specs/2026-07-05-quant-allocator-wargame-design.md`
```

- [ ] **Step 5: Run tests**

Run: `uv run pytest -v`
Expected: `test_package_imports PASSED`, 1 passed.

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml uv.lock README.md src/ tests/ .python-version
git commit -m "feat: scaffold quant_allocator package with src layout and pytest wiring"
```

### Task B2: Factor-model market generator

**Files:**
- Create: `src/quant_allocator/simulator/market.py`
- Test: `tests/simulator/test_market.py` (and empty `tests/simulator/__init__.py`)

**Interfaces:**
- Produces (consumed by B3/B4):
  - `MarketConfig(n_assets, n_months, factor_names, factor_annual_means, factor_annual_vols, idio_annual_vol_range, start_month, seed)` — frozen dataclass, defaults as in code below.
  - `FactorMarket` — frozen dataclass with `config`; `betas: pd.DataFrame` (index=asset ids `A0000…`, columns=factor names); `factor_returns: pd.DataFrame` (PeriodIndex months × factors); `idio_returns: pd.DataFrame` (months × assets); property `asset_returns: pd.DataFrame` (months × assets).
  - `simulate_market(config: MarketConfig) -> FactorMarket`.

- [ ] **Step 1: Write the failing tests**

`tests/simulator/test_market.py`:

```python
import numpy as np
import pandas as pd

from quant_allocator.simulator.market import FactorMarket, MarketConfig, simulate_market


def test_shapes_and_return_identity():
    cfg = MarketConfig(n_assets=50, n_months=24, seed=1)
    mkt = simulate_market(cfg)
    assert mkt.factor_returns.shape == (24, 4)
    assert mkt.betas.shape == (50, 4)
    assert mkt.idio_returns.shape == (24, 50)
    assert isinstance(mkt.factor_returns.index, pd.PeriodIndex)
    expected = (
        mkt.factor_returns.to_numpy() @ mkt.betas.to_numpy().T + mkt.idio_returns.to_numpy()
    )
    np.testing.assert_allclose(mkt.asset_returns.to_numpy(), expected)


def test_seed_reproducibility():
    a = simulate_market(MarketConfig(n_assets=30, n_months=12, seed=7))
    b = simulate_market(MarketConfig(n_assets=30, n_months=12, seed=7))
    pd.testing.assert_frame_equal(a.asset_returns, b.asset_returns)


def test_factor_vol_calibration():
    cfg = MarketConfig(n_assets=10, n_months=6000, seed=3)
    mkt = simulate_market(cfg)
    realized_annual_vol = mkt.factor_returns.std() * np.sqrt(12)
    expected = pd.Series(cfg.factor_annual_vols, index=list(cfg.factor_names))
    assert (realized_annual_vol - expected).abs().max() < 0.02
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/simulator/test_market.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'quant_allocator.simulator.market'`

- [ ] **Step 3: Write the implementation**

`src/quant_allocator/simulator/market.py`:

```python
"""Synthetic factor-model equity market: the ground-truth world managers trade in."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

MONTHS_PER_YEAR = 12


@dataclass(frozen=True)
class MarketConfig:
    n_assets: int = 500
    n_months: int = 60
    factor_names: tuple[str, ...] = ("market", "size", "value", "momentum")
    factor_annual_means: tuple[float, ...] = (0.06, 0.02, 0.03, 0.04)
    factor_annual_vols: tuple[float, ...] = (0.16, 0.08, 0.10, 0.12)
    idio_annual_vol_range: tuple[float, float] = (0.20, 0.45)
    start_month: str = "2020-01"
    seed: int = 0


@dataclass(frozen=True)
class FactorMarket:
    config: MarketConfig
    betas: pd.DataFrame
    factor_returns: pd.DataFrame
    idio_returns: pd.DataFrame

    @property
    def asset_returns(self) -> pd.DataFrame:
        systematic = self.factor_returns.to_numpy() @ self.betas.to_numpy().T
        return (
            pd.DataFrame(
                systematic, index=self.factor_returns.index, columns=self.betas.index
            )
            + self.idio_returns
        )


def simulate_market(config: MarketConfig) -> FactorMarket:
    rng = np.random.default_rng(config.seed)
    months = pd.period_range(config.start_month, periods=config.n_months, freq="M")
    assets = pd.Index([f"A{i:04d}" for i in range(config.n_assets)], name="asset")
    factors = list(config.factor_names)

    monthly_means = np.asarray(config.factor_annual_means) / MONTHS_PER_YEAR
    monthly_vols = np.asarray(config.factor_annual_vols) / np.sqrt(MONTHS_PER_YEAR)
    factor_returns = pd.DataFrame(
        rng.normal(monthly_means, monthly_vols, size=(config.n_months, len(factors))),
        index=months,
        columns=factors,
    )

    market_beta = rng.normal(1.0, 0.25, size=config.n_assets)
    style_betas = rng.normal(0.0, 0.5, size=(config.n_assets, len(factors) - 1))
    betas = pd.DataFrame(
        np.column_stack([market_beta, style_betas]), index=assets, columns=factors
    )

    low, high = config.idio_annual_vol_range
    idio_monthly_vols = rng.uniform(low, high, size=config.n_assets) / np.sqrt(MONTHS_PER_YEAR)
    idio_returns = pd.DataFrame(
        rng.normal(0.0, idio_monthly_vols, size=(config.n_months, config.n_assets)),
        index=months,
        columns=assets,
    )
    return FactorMarket(
        config=config, betas=betas, factor_returns=factor_returns, idio_returns=idio_returns
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/simulator/test_market.py -v`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add src/quant_allocator/simulator/market.py tests/simulator/
git commit -m "feat: factor-model market generator with seeded ground truth"
```

### Task B3: Equity L/S manager simulator

**Files:**
- Create: `src/quant_allocator/simulator/manager.py`
- Test: `tests/simulator/test_manager.py`

**Interfaces:**
- Consumes: `FactorMarket` from B2 (`betas`, `idio_returns`, `asset_returns` as defined there).
- Produces (consumed by B4):
  - `ManagerConfig(n_long, n_short, target_gross, target_net, information_coefficient, alpha_half_life_months, sizing_discipline, rebalance_fraction, seed)` — frozen dataclass.
  - `ManagerHistory` — frozen dataclass: `config`; `weights: pd.DataFrame` (months × all assets, signed, zeros for unheld; `index.name="month"`, `columns.name="asset"`); `monthly_returns: pd.Series`; `true_alpha_returns: pd.Series` (idiosyncratic P&L — the ground truth).
  - `simulate_manager(market: FactorMarket, config: ManagerConfig) -> ManagerHistory`.
  - `effective_information_coefficient(age_months, config) -> np.ndarray` — IC decayed by holding age: `ic * 0.5 ** (age / half_life)`.

**Generative model (documented in the module docstring):** each month the
manager receives, per asset, a noisy signal about that month's standardized
idiosyncratic return; signal quality is `information_coefficient` for fresh
picks and decays with holding age at `alpha_half_life_months` (stale theses
predict less). Each month the oldest `rebalance_fraction` of each book side
is replaced by the freshest-signal candidates. Position sizes interpolate
between signal-proportional (`sizing_discipline=1`) and equal-weight (`=0`),
scaled to hit `target_gross`/`target_net`.

- [ ] **Step 1: Write the failing tests**

`tests/simulator/test_manager.py`:

```python
import numpy as np

from quant_allocator.simulator.manager import (
    ManagerConfig,
    effective_information_coefficient,
    simulate_manager,
)
from quant_allocator.simulator.market import MarketConfig, simulate_market


def test_ic_decays_with_half_life():
    cfg = ManagerConfig(information_coefficient=0.10, alpha_half_life_months=6.0)
    assert effective_information_coefficient(0.0, cfg) == 0.10
    assert np.isclose(effective_information_coefficient(6.0, cfg), 0.05)
    assert np.isclose(effective_information_coefficient(12.0, cfg), 0.025)


def test_gross_and_net_targets_hit_every_month():
    market = simulate_market(MarketConfig(n_assets=200, n_months=36, seed=2))
    hist = simulate_manager(market, ManagerConfig(seed=2))
    gross = hist.weights.abs().sum(axis=1)
    net = hist.weights.sum(axis=1)
    assert np.allclose(gross, 1.6, atol=1e-8)
    assert np.allclose(net, 0.2, atol=1e-8)


def test_skilled_manager_earns_more_true_alpha_than_unskilled():
    market = simulate_market(MarketConfig(n_assets=500, n_months=120, seed=5))
    skilled = simulate_manager(
        market, ManagerConfig(information_coefficient=0.15, seed=11)
    )
    unskilled = simulate_manager(
        market, ManagerConfig(information_coefficient=0.0, seed=11)
    )
    assert skilled.true_alpha_returns.mean() > unskilled.true_alpha_returns.mean()
    assert skilled.true_alpha_returns.mean() > 0


def test_turnover_matches_rebalance_fraction():
    market = simulate_market(MarketConfig(n_assets=300, n_months=48, seed=4))
    cfg = ManagerConfig(rebalance_fraction=0.25, seed=4)
    hist = simulate_manager(market, cfg)
    held = hist.weights != 0.0
    entry_fracs = []
    for t in range(1, len(held)):
        entries = (held.iloc[t] & ~held.iloc[t - 1]).sum()
        entry_fracs.append(entries / (cfg.n_long + cfg.n_short))
    assert abs(np.mean(entry_fracs) - 0.25) < 0.05
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/simulator/test_manager.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'quant_allocator.simulator.manager'`

- [ ] **Step 3: Write the implementation**

`src/quant_allocator/simulator/manager.py`:

```python
"""Synthetic equity long/short manager with dialable ground-truth skill.

Generative model: each month the manager receives, per asset, a noisy signal
about that month's standardized idiosyncratic return. Signal quality is
`information_coefficient` for fresh picks and decays with holding age at
`alpha_half_life_months`. Each month the oldest `rebalance_fraction` of each
side is replaced by the freshest-signal candidates. Sizes interpolate between
signal-proportional (sizing_discipline=1) and equal-weight (0), scaled to hit
target_gross / target_net exactly.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from quant_allocator.simulator.market import FactorMarket


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


@dataclass(frozen=True)
class ManagerHistory:
    config: ManagerConfig
    weights: pd.DataFrame
    monthly_returns: pd.Series
    true_alpha_returns: pd.Series


def effective_information_coefficient(
    age_months: float | np.ndarray, config: ManagerConfig
) -> np.ndarray:
    age = np.asarray(age_months, dtype=float)
    return config.information_coefficient * 0.5 ** (age / config.alpha_half_life_months)


def _side_weights(
    names: list[str], signals: pd.Series, total: float, sign: float, discipline: float
) -> pd.Series:
    strength = signals.loc[names].abs()
    raw = discipline * strength + (1.0 - discipline) * 1.0
    return sign * total * raw / raw.sum()


def simulate_manager(market: FactorMarket, config: ManagerConfig) -> ManagerHistory:
    rng = np.random.default_rng(config.seed)
    months = market.idio_returns.index
    assets = market.betas.index
    z = market.idio_returns / market.idio_returns.std()
    noise = rng.standard_normal(z.shape)

    ages: dict[str, int] = {}
    longs: list[str] = []
    shorts: list[str] = []
    weight_rows: list[pd.Series] = []

    n_rep_long = round(config.rebalance_fraction * config.n_long)
    n_rep_short = round(config.rebalance_fraction * config.n_short)

    for t in range(len(months)):
        for name in ages:
            ages[name] += 1

        if t > 0:
            drop_long = sorted(longs, key=lambda n: (-ages[n], n))[:n_rep_long]
            drop_short = sorted(shorts, key=lambda n: (-ages[n], n))[:n_rep_short]
            for name in (*drop_long, *drop_short):
                ages.pop(name)
            longs = [n for n in longs if n not in set(drop_long)]
            shorts = [n for n in shorts if n not in set(drop_short)]

        age_vec = pd.Series(0.0, index=assets)
        for name, age in ages.items():
            age_vec[name] = float(age)
        ic_eff = effective_information_coefficient(age_vec.to_numpy(), config)
        signals = pd.Series(
            ic_eff * z.iloc[t].to_numpy() + np.sqrt(1.0 - ic_eff**2) * noise[t],
            index=assets,
        )

        held = set(longs) | set(shorts)
        candidates = signals.drop(index=list(held)).sort_values()
        need_long = config.n_long - len(longs)
        need_short = config.n_short - len(shorts)
        new_longs = list(candidates.index[-need_long:]) if need_long else []
        new_shorts = list(candidates.index[:need_short]) if need_short else []
        longs += new_longs
        shorts += new_shorts
        for name in (*new_longs, *new_shorts):
            ages[name] = 0

        long_total = (config.target_gross + config.target_net) / 2.0
        short_total = (config.target_gross - config.target_net) / 2.0
        weights = pd.Series(0.0, index=assets)
        weights.loc[longs] = _side_weights(
            longs, signals, long_total, 1.0, config.sizing_discipline
        )
        weights.loc[shorts] = _side_weights(
            shorts, signals, short_total, -1.0, config.sizing_discipline
        )
        weight_rows.append(weights)

    weights = pd.DataFrame(weight_rows, index=months)
    weights.index.name = "month"
    weights.columns.name = "asset"
    monthly_returns = (weights * market.asset_returns).sum(axis=1)
    true_alpha_returns = (weights * market.idio_returns).sum(axis=1)
    return ManagerHistory(
        config=config,
        weights=weights,
        monthly_returns=monthly_returns,
        true_alpha_returns=true_alpha_returns,
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/simulator/test_manager.py -v`
Expected: 4 passed. (If `test_skilled_manager...` fails on the chosen seeds,
that is a real signal-model bug — do not fix by reseeding; the skilled/
unskilled gap at IC=0.15 over 120 months is many standard errors wide.)

- [ ] **Step 5: Commit**

```bash
git add src/quant_allocator/simulator/manager.py tests/simulator/test_manager.py
git commit -m "feat: equity L/S manager simulator with IC, alpha decay, sizing discipline"
```

### Task B4: Three-tier data emitter

**Files:**
- Create: `src/quant_allocator/simulator/tiers.py`
- Test: `tests/simulator/test_tiers.py`

**Interfaces:**
- Consumes: `FactorMarket.betas` (B2); `ManagerHistory.weights`, `.monthly_returns` (B3).
- Produces:
  - `ManagerDataTiers` — frozen dataclass: `returns_only: pd.Series`; `exposures: pd.DataFrame` (per month: `gross`, `net`, one `beta_<factor>` per factor, `top10_share`); `transparency: pd.DataFrame` (long format: `month`, `asset`, `weight`, nonzero rows only).
  - `emit_tiers(market: FactorMarket, history: ManagerHistory) -> ManagerDataTiers`.

- [ ] **Step 1: Write the failing tests**

`tests/simulator/test_tiers.py`:

```python
import numpy as np
import pandas as pd

from quant_allocator.simulator.manager import ManagerConfig, simulate_manager
from quant_allocator.simulator.market import MarketConfig, simulate_market
from quant_allocator.simulator.tiers import emit_tiers


def _fixture():
    market = simulate_market(MarketConfig(n_assets=100, n_months=12, seed=9))
    history = simulate_manager(market, ManagerConfig(seed=9))
    return market, history


def test_returns_only_tier_matches_portfolio_returns():
    market, history = _fixture()
    tiers = emit_tiers(market, history)
    pd.testing.assert_series_equal(tiers.returns_only, history.monthly_returns)


def test_exposures_tier_reports_true_factor_betas_and_gross_net():
    market, history = _fixture()
    tiers = emit_tiers(market, history)
    expected_betas = history.weights @ market.betas
    for factor in market.config.factor_names:
        np.testing.assert_allclose(
            tiers.exposures[f"beta_{factor}"], expected_betas[factor]
        )
    np.testing.assert_allclose(tiers.exposures["gross"], 1.6, atol=1e-8)
    np.testing.assert_allclose(tiers.exposures["net"], 0.2, atol=1e-8)
    assert ((tiers.exposures["top10_share"] > 0) & (tiers.exposures["top10_share"] <= 1)).all()


def test_transparency_tier_round_trips_to_weights():
    market, history = _fixture()
    tiers = emit_tiers(market, history)
    assert (tiers.transparency["weight"] != 0).all()
    rebuilt = (
        tiers.transparency.pivot(index="month", columns="asset", values="weight")
        .reindex(index=history.weights.index, columns=history.weights.columns)
        .fillna(0.0)
    )
    np.testing.assert_allclose(rebuilt.to_numpy(), history.weights.to_numpy())
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/simulator/test_tiers.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'quant_allocator.simulator.tiers'`

- [ ] **Step 3: Write the implementation**

`src/quant_allocator/simulator/tiers.py`:

```python
"""Emit the three allocator transparency tiers from one simulated manager.

The same ground-truth book is viewed as: returns-only (what every allocator
gets), exposure summaries (what risk reports disclose), and position-level
transparency (managed-account style). Emission only — no analytics here.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from quant_allocator.simulator.manager import ManagerHistory
from quant_allocator.simulator.market import FactorMarket

TOP_N_CONCENTRATION = 10


@dataclass(frozen=True)
class ManagerDataTiers:
    returns_only: pd.Series
    exposures: pd.DataFrame
    transparency: pd.DataFrame


def emit_tiers(market: FactorMarket, history: ManagerHistory) -> ManagerDataTiers:
    weights = history.weights

    gross = weights.abs().sum(axis=1)
    top10_share = (
        weights.abs().apply(lambda row: row.nlargest(TOP_N_CONCENTRATION).sum(), axis=1)
        / gross
    )
    exposures = (weights @ market.betas).add_prefix("beta_")
    exposures.insert(0, "gross", gross)
    exposures.insert(1, "net", weights.sum(axis=1))
    exposures["top10_share"] = top10_share

    transparency = weights.stack().rename("weight").reset_index()
    transparency = transparency[transparency["weight"] != 0.0].reset_index(drop=True)

    return ManagerDataTiers(
        returns_only=history.monthly_returns.copy(),
        exposures=exposures,
        transparency=transparency,
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/simulator/test_tiers.py -v`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add src/quant_allocator/simulator/tiers.py tests/simulator/test_tiers.py
git commit -m "feat: three-tier data emitter (returns-only, exposures, transparency)"
```

### Task B5: Crude macro/credit returns-only generators

**Files:**
- Create: `src/quant_allocator/simulator/returns_only.py`
- Test: `tests/simulator/test_returns_only.py`

**Interfaces:**
- Produces:
  - `ReturnsOnlyConfig(strategy, n_months, skill_annual_alpha, alpha_annual_vol, start_month, seed)` — frozen dataclass; `strategy` ∈ `{"macro", "credit"}`.
  - `simulate_returns_only_manager(config: ReturnsOnlyConfig) -> pd.Series` — monthly decimal returns, PeriodIndex.
  - `STRATEGY_FACTORS: dict[str, dict[str, tuple[float, float]]]` — per-strategy synthetic factor (annual mean, annual vol).

Deliberately crude by spec Section 7: non-equity managers are modeled at the
returns-only tier as `sum(beta_k * factor_k) + alpha_stream` with random
exposures — enough for cross-strategy book aggregation experiments, nothing
more.

- [ ] **Step 1: Write the failing tests**

`tests/simulator/test_returns_only.py`:

```python
import numpy as np
import pandas as pd
import pytest

from quant_allocator.simulator.returns_only import (
    ReturnsOnlyConfig,
    simulate_returns_only_manager,
)


def test_shape_index_and_reproducibility():
    cfg = ReturnsOnlyConfig(strategy="macro", n_months=60, seed=1)
    a = simulate_returns_only_manager(cfg)
    b = simulate_returns_only_manager(cfg)
    assert len(a) == 60
    assert isinstance(a.index, pd.PeriodIndex)
    pd.testing.assert_series_equal(a, b)


def test_skill_shifts_mean_return_on_long_sample():
    base = ReturnsOnlyConfig(strategy="credit", n_months=120_000, seed=2)
    skilled = ReturnsOnlyConfig(
        strategy="credit", n_months=120_000, skill_annual_alpha=0.06, seed=2
    )
    gap_annualized = 12 * (
        simulate_returns_only_manager(skilled).mean()
        - simulate_returns_only_manager(base).mean()
    )
    assert np.isclose(gap_annualized, 0.06 - 0.02, atol=0.01)


def test_unknown_strategy_raises():
    with pytest.raises(ValueError, match="unknown strategy"):
        simulate_returns_only_manager(ReturnsOnlyConfig(strategy="event"))
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/simulator/test_returns_only.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'quant_allocator.simulator.returns_only'`

- [ ] **Step 3: Write the implementation**

`src/quant_allocator/simulator/returns_only.py`:

```python
"""Deliberately crude returns-only generators for non-equity manager archetypes.

Spec Section 7: macro/credit managers exist in the simulator only at the
returns-only tier — synthetic strategy factors plus an alpha stream. Enough
for cross-strategy aggregation experiments; not a market microcosm.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

MONTHS_PER_YEAR = 12

STRATEGY_FACTORS: dict[str, dict[str, tuple[float, float]]] = {
    "macro": {"trend": (0.05, 0.12), "rates_carry": (0.03, 0.06), "fx_carry": (0.03, 0.08)},
    "credit": {"credit_spread": (0.04, 0.07), "rates": (0.02, 0.05)},
}


@dataclass(frozen=True)
class ReturnsOnlyConfig:
    strategy: str = "macro"
    n_months: int = 60
    skill_annual_alpha: float = 0.02
    alpha_annual_vol: float = 0.04
    start_month: str = "2020-01"
    seed: int = 0


def simulate_returns_only_manager(config: ReturnsOnlyConfig) -> pd.Series:
    if config.strategy not in STRATEGY_FACTORS:
        raise ValueError(
            f"unknown strategy {config.strategy!r}; expected one of {sorted(STRATEGY_FACTORS)}"
        )
    rng = np.random.default_rng(config.seed)
    months = pd.period_range(config.start_month, periods=config.n_months, freq="M")

    total = np.zeros(config.n_months)
    for annual_mean, annual_vol in STRATEGY_FACTORS[config.strategy].values():
        factor = rng.normal(
            annual_mean / MONTHS_PER_YEAR,
            annual_vol / np.sqrt(MONTHS_PER_YEAR),
            size=config.n_months,
        )
        exposure = rng.uniform(0.2, 1.0)
        total += exposure * factor

    alpha = rng.normal(
        config.skill_annual_alpha / MONTHS_PER_YEAR,
        config.alpha_annual_vol / np.sqrt(MONTHS_PER_YEAR),
        size=config.n_months,
    )
    return pd.Series(total + alpha, index=months, name=f"{config.strategy}_manager")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/simulator/test_returns_only.py -v`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add src/quant_allocator/simulator/returns_only.py tests/simulator/test_returns_only.py
git commit -m "feat: crude returns-only macro/credit manager generators"
```

### Task B6: Ken French factor adapter

**Files:**
- Create: `src/quant_allocator/adapters/french.py`
- Test: `tests/adapters/test_french.py` (and empty `tests/adapters/__init__.py`)

**Interfaces:**
- Produces:
  - `parse_french_monthly_csv(text: str) -> pd.DataFrame` — pure parser, offline-testable; monthly PeriodIndex, decimal returns.
  - `load_ff5_monthly(cache_dir: Path | None = None) -> pd.DataFrame` — download + cache + parse; network on first call only.
  - `FF5_URL: str` — module constant.

- [ ] **Step 1: Write the failing tests**

`tests/adapters/test_french.py`:

```python
import pandas as pd
import pytest

from quant_allocator.adapters.french import load_ff5_monthly, parse_french_monthly_csv

SAMPLE = """This file was created using the 202412 CRSP database.

,Mkt-RF,SMB,HML,RMW,CMA,RF
192607,    2.96,   -2.56,   -2.43,   -1.48,   -1.18,    0.22
192608,    2.64,   -1.17,    3.82,    0.42,    3.13,    0.25

 Annual Factors: January-December
,Mkt-RF,SMB,HML,RMW,CMA,RF
1927,   29.47,   -2.46,   -3.75,   -1.53,   -4.30,    3.12
"""


def test_parses_monthly_block_only_as_decimals():
    df = parse_french_monthly_csv(SAMPLE)
    assert list(df.columns) == ["Mkt-RF", "SMB", "HML", "RMW", "CMA", "RF"]
    assert df.shape == (2, 6)
    assert isinstance(df.index, pd.PeriodIndex)
    assert df.index[0] == pd.Period("1926-07", freq="M")
    assert df.loc[pd.Period("1926-07", freq="M"), "Mkt-RF"] == pytest.approx(0.0296)


def test_raises_on_text_without_monthly_block():
    with pytest.raises(ValueError, match="no monthly data block"):
        parse_french_monthly_csv("just some text\nwith no data\n")


@pytest.mark.network
def test_download_real_ff5(tmp_path):
    df = load_ff5_monthly(cache_dir=tmp_path)
    assert df.index[0] == pd.Period("1926-07", freq="M")
    assert "Mkt-RF" in df.columns
    assert len(df) > 1000
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/adapters/test_french.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'quant_allocator.adapters.french'` (network test deselected by default).

- [ ] **Step 3: Write the implementation**

`src/quant_allocator/adapters/french.py`:

```python
"""Ken French data library adapter: download, cache, and parse monthly factors."""

from __future__ import annotations

import io
import re
import urllib.request
import zipfile
from pathlib import Path

import pandas as pd

FF5_URL = (
    "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/"
    "F-F_Research_Data_5_Factors_2x3_CSV.zip"
)

_MONTHLY_ROW = re.compile(r"^\s*\d{6}\s*,")


def parse_french_monthly_csv(text: str) -> pd.DataFrame:
    """Parse the monthly block of a Ken French CSV.

    The files carry a free-text preamble, a header row, YYYYMM rows, then
    annual blocks. We take the first run of YYYYMM rows and the header line
    immediately above it. Values are percentages; returned as decimals.
    """
    lines = text.splitlines()
    header: list[str] | None = None
    rows: list[list[str]] = []
    for i, line in enumerate(lines):
        if _MONTHLY_ROW.match(line):
            if header is None:
                header = [cell.strip() for cell in lines[i - 1].split(",")]
            rows.append([cell.strip() for cell in line.split(",")])
        elif header is not None:
            break
    if header is None:
        raise ValueError("no monthly data block found in French CSV")

    df = pd.DataFrame(rows, columns=header)
    month_col = header[0]
    index = pd.to_datetime(df[month_col], format="%Y%m").dt.to_period("M")
    df = df.drop(columns=[month_col]).set_index(pd.PeriodIndex(index, name="month"))
    return df.astype(float) / 100.0


def load_ff5_monthly(cache_dir: Path | None = None) -> pd.DataFrame:
    """Fama-French 5 factors + RF, monthly. Downloads and caches on first call."""
    cache_dir = cache_dir or Path.home() / ".cache" / "quant_allocator"
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path = cache_dir / "ff5_monthly.csv"
    if not cache_path.exists():
        with urllib.request.urlopen(FF5_URL, timeout=30) as response:
            payload = response.read()
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            cache_path.write_bytes(archive.read(archive.namelist()[0]))
    return parse_french_monthly_csv(cache_path.read_text(encoding="latin-1"))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/adapters/test_french.py -v`
Expected: 2 passed, 1 deselected.
Then run once with network to certify the live format assumption:
`uv run pytest tests/adapters/test_french.py -m network -v`
Expected: 1 passed. (If the live format has drifted, fix the parser, not the test.)

- [ ] **Step 5: Run the full suite and lint**

Run: `uv run pytest -v && uv run ruff check .`
Expected: all tests pass (network deselected), no lint errors.

- [ ] **Step 6: Commit**

```bash
git add src/quant_allocator/adapters/ tests/adapters/
git commit -m "feat: Ken French monthly factor adapter with offline-testable parser"
```
