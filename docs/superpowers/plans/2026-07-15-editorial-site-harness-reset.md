# Editorial Site Harness Reset Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace stale platform-campaign authority with a compact, repository-backed editorial-site objective while preserving P4 as parked, resumable history.

**Architecture:** Add one canonical product charter and one small YAML current-state record, then route agents through them from `AGENTS.md`. Preserve historical plans and ledgers, but mark the only falsely active roadmap and the two P4 plans as superseded or parked; update ignored continuation files without making them authority.

**Tech Stack:** Markdown, YAML, Python 3.11, PyYAML, pytest, existing static-site builder.

## Global Constraints

- Quant Allocator is a public, static editorial research publication and project-idea bank.
- Aligrithm governs editorial structure and composition; Interval governs quantitative semantics.
- The 36-card bitemporal-platform campaign is superseded product scope.
- P4 is parked and is not a website prerequisite.
- Use public or synthetic data only; every displayed manager and fund name is fictional.
- Never name an employer or include employer-internal facts in tracked artifacts.
- Preserve independently certified data and numerical results; this plan changes no site data.
- Load publication terms from `tools/.publication_terms`; never copy them into tracked files.
- Use explicit `git add <path>` only; no `git add -A`, reset, rebase, push, or publication.
- Keep both P4 worktrees and branches untouched.

---

### Task 1: Pin the current-context contract with failing tests

**Files:**
- Create: `tests/harness/test_current_context.py`

**Interfaces:**
- Consumes: planned `docs/PRODUCT.md`, `.harness/current.yaml`, `.harness/README.md`, `AGENTS.md`, and the three tracked campaign-plan banners.
- Produces: a focused regression gate preventing the platform roadmap or P4 from becoming current work silently.

- [ ] **Step 1: Create the focused failing test**

```python
from __future__ import annotations

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
CURRENT = ROOT / ".harness" / "current.yaml"
PRODUCT = ROOT / "docs" / "PRODUCT.md"
ROADMAP = ROOT / "docs" / "superpowers" / "plans" / (
    "2026-07-10-external-manager-roadmap-implementation.md"
)
P4_CARD = ROOT / "docs" / "superpowers" / "plans" / (
    "2026-07-11-external-manager-p4a-fees-terms.md"
)
P4_FIXTURE = ROOT / "docs" / "superpowers" / "plans" / (
    "2026-07-11-p4-shared-terms-fixture-seam.md"
)


def _current() -> dict:
    return yaml.safe_load(CURRENT.read_text(encoding="utf-8"))


def test_product_charter_is_the_canonical_editorial_objective():
    text = PRODUCT.read_text(encoding="utf-8")
    assert "Canonical product authority" in text
    assert "editorial research publication and project-idea bank" in text
    assert "Deep engineering follows explicit approval" in text
    assert "Aligrithm" in text
    assert "Interval" in text
    assert "not a production allocator platform" in text


def test_current_context_selects_website_design_and_no_platform_plan():
    current = _current()
    assert current["version"] == 1
    assert current["product_charter"] == "docs/PRODUCT.md"
    assert current["objective"]["id"] == "editorial-site"
    assert current["objective"]["mode"] == "website-first"
    assert current["scheduler"]["active_plan"] is None
    assert current["scheduler"]["current_task"] == "WEBSITE-DESIGN-T1"
    assert "Aligrithm" in current["scheduler"]["next_action"]
    assert current["authority"]["push"] is False
    assert current["authority"]["publish"] is False


def test_p4_is_parked_with_exact_recovery_tips():
    parked = _current()["parked_work"]["p4"]
    assert parked["status"] == "parked"
    assert parked["website_prerequisite"] is False
    assert parked["resume_requires"] == "explicit-user-approval-and-product-fit-review"
    assert parked["fixture_branch"] == "codex/roadmap-p4-terms-fixture-impl"
    assert parked["fixture_tip"] == "b0596db"
    assert parked["card_branch"] == "codex/roadmap-p4-impl"
    assert parked["card_tip"] == "7c2964f"


def test_agent_guide_routes_through_product_and_current_context():
    text = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    assert "Read `docs/PRODUCT.md` first" in text
    assert "Read `.harness/current.yaml` second" in text
    assert "may not broaden" in text
    assert "historical evidence" in text


def test_platform_roadmap_and_p4_plans_are_not_active_instructions():
    roadmap = ROADMAP.read_text(encoding="utf-8")
    p4_card = P4_CARD.read_text(encoding="utf-8")
    p4_fixture = P4_FIXTURE.read_text(encoding="utf-8")
    assert "SUPERSEDED PRODUCT SCOPE" in roadmap[:800]
    assert "not an active implementation plan" in roadmap[:800]
    assert "PARKED OPTIONAL RESEARCH" in p4_card[:800]
    assert "PARKED OPTIONAL RESEARCH" in p4_fixture[:800]
    assert "not a website prerequisite" in p4_card[:800]
    assert "not a website prerequisite" in p4_fixture[:800]


def test_harness_readme_keeps_history_out_of_normal_initialization():
    text = (ROOT / ".harness" / "README.md").read_text(encoding="utf-8")
    assert "Normal initialization" in text
    assert "Do not initialize from" in text
    assert ".superpowers/sdd/progress.md" in text
```

- [ ] **Step 2: Run the test and confirm the intended RED state**

Run:

```bash
uv run pytest tests/harness/test_current_context.py -q
```

Expected: collection succeeds and tests fail because `docs/PRODUCT.md`, `.harness/current.yaml`, and `.harness/README.md` do not yet exist.

- [ ] **Step 3: Commit the RED contract**

```bash
git add tests/harness/test_current_context.py
git commit -m "test(harness): pin editorial site authority reset"
```

---

### Task 2: Create the canonical product charter and compact harness state

**Files:**
- Create: `docs/PRODUCT.md`
- Create: `.harness/README.md`
- Create: `.harness/current.yaml`
- Modify: `AGENTS.md`
- Modify: `README.md`

**Interfaces:**
- Consumes: the approved design at `docs/superpowers/specs/2026-07-15-editorial-site-harness-reset-design.md`.
- Produces: the complete normal initialization surface for fresh agents.

- [ ] **Step 1: Create `docs/PRODUCT.md` with this structure and binding language**

```markdown
# Quant Allocator Product Charter

**Status:** Canonical product authority
**Last approved:** 2026-07-15

## Objective

Quant Allocator is a public, static editorial research publication and project-idea
bank about quantitative methods for allocator decisions under partial transparency.
The public artifact is the product: long-form technical articles paired with honest
synthetic or public exhibits.

It is not a production allocator platform, enterprise evidence system, or standing
monitoring dashboard. Deep engineering follows explicit approval; it never becomes a
prerequisite merely because an implementation plan describes it.

## Reader and decisions

Write for a motivated reader who wants to understand how a quantitative allocator
could select, size, monitor, engage with, and redeem external managers. The site must
work both as a structured curriculum and as a project-idea bank.

## Editorial form

Aligrithm is the primary reference for publication structure, reading rhythm,
research pillars, article discovery, and long-form composition. This is not a
pixel-level clone. Quant Allocator uses a clear thesis, a Start Here path, topical
pillars, a readable article index, and long-form pieces combining intuition,
mathematics, code, evidence, and limitations.

Interval remains the quantitative semantic system. Intervals, provenance labels,
and refusal states communicate what the evidence supports. Aligrithm governs
editorial composition; Interval governs quantitative meaning.

## Article and exhibit contract

Every idea has a long-form article and, where useful, a compact exhibit. Articles
explain what the method is, why it matters, why naive alternatives fail, how it
works, a small numerical example, defined notation, self-contained teaching code,
honest limits, go-live requirements, references, and questions the reader should
be able to answer.

Exhibits use synthetic or public data and explain “What this exhibit shows” and
“How to read it.” Static narration is the default. Interaction is used only when
changing state is part of the teaching argument.

## Publication correctness

- Use public or synthetic data only and fictional displayed names.
- Never include an employer identity or employer-internal fact.
- Support every displayed quantitative claim with committed article/exhibit data.
- Use an interval, scenario, or explicit refusal for estimate-bearing outputs.
- Independently check load-bearing arithmetic before publication.
- Check rendered desktop/mobile layout, formulas, copy, links, and visible controls.
- Load publication terms from the gitignored canary file before every push.
- Push or publish only with explicit user approval.

These are page- and claim-level gates. They do not require a shared production
database, global receipt graph, or hardened engine for every article.

## Scope boundaries

The 36-card bitemporal-platform roadmap is superseded product scope. P4 and its
fixture work are parked optional research and are not website prerequisites. Existing
committed work remains available for later reuse.

No plan may add cards, engines, platform layers, or publication prerequisites beyond
this charter without an explicit user decision and a charter amendment.

## Authority

1. Direct user instruction.
2. This product charter.
3. `.harness/current.yaml`.
4. Approved specifications cited by the current task.
5. The single active plan named by the current harness, if any.
6. Historical plans, ledgers, handoffs, reports, and Git history as evidence only.

A lower authority may add implementation detail but may not broaden a higher one.
```

- [ ] **Step 2: Create `.harness/current.yaml`**

```yaml
version: 1
updated_at: "2026-07-15"
product_charter: docs/PRODUCT.md
objective:
  id: editorial-site
  mode: website-first
  outcome: >-
    Build a public static editorial research publication and project-idea bank with
    Aligrithm-style composition and Interval quantitative semantics.
scheduler:
  current_task: WEBSITE-DESIGN-T1
  active_plan: null
  next_action: >-
    Capture the Aligrithm reference and current rendered site, then write and review
    the website-first design specification before changing page code.
parked_work:
  p4:
    status: parked
    website_prerequisite: false
    resume_requires: explicit-user-approval-and-product-fit-review
    fixture_branch: codex/roadmap-p4-terms-fixture-impl
    fixture_tip: b0596db
    card_branch: codex/roadmap-p4-impl
    card_tip: 7c2964f
authority:
  merge: false
  push: false
  publish: false
verification:
  current_level: documentation-reset
  required:
    - harness-context
    - focused-site-build
    - publication-scan
```

- [ ] **Step 3: Create `.harness/README.md`**

```markdown
# Quant Allocator Current Context

## Normal initialization

1. Read `docs/PRODUCT.md`.
2. Read `.harness/current.yaml`.
3. Read `AGENTS.md`.
4. Read only the specification or plan explicitly named by the current task.
5. Verify the Git branch and worktree before editing.

Do not initialize from `.superpowers/sdd/progress.md`, old continuation prompts,
completed implementation plans, or review reports. They are historical evidence for
targeted archaeology only.

The current harness is intentionally small. It records the product objective, current
task, next action, parked work, verification level, and outward-action authority. It
does not select models, estimate token use, or turn the historical backlog into active
work.
```

- [ ] **Step 4: Update `AGENTS.md` authority and anti-drift rules**

Replace the current “Authority and sources of truth” section with:

```markdown
## Authority and sources of truth

1. Read `docs/PRODUCT.md` first. It is the canonical product authority.
2. Read `.harness/current.yaml` second. It names the current objective, task, next
   action, parked work, and outward-action authority.
3. Read only the approved specification or implementation plan cited by the current
   task. A plan may add implementation detail but may not broaden the product charter.
4. Treat `.superpowers/sdd/progress.md`, old plans, handoffs, reports, and Git history
   as historical evidence, not normal initialization or automatic continuation.
5. In each method spec, section 8 rulings govern that article's arithmetic and claims;
   they do not govern the overall product roadmap.
6. The primary agent owns synthesis, scope rulings, integration, and publication.
```

Add this paragraph immediately after the authority list:

```markdown
No agent may resume parked work, add a card or platform layer, or create a new
publication prerequisite without explicit user approval and, when product scope changes,
an amendment to `docs/PRODUCT.md`.
```

- [ ] **Step 5: Align the opening and repository map in `README.md`**

Use this opening:

```markdown
# Quant Allocator

A public editorial research publication and project-idea bank about quantitative
methods for allocator decisions under partial transparency. Each idea combines a
long-form technical article with an honest synthetic or public exhibit: what the
method claims, why the decision is hard, what the data can support, and what would be
needed to use it live.

**Thesis:** Every allocator analytic is an exercise in inference under partial
transparency.
```

Add `docs/PRODUCT.md` to the repository map as the canonical product charter.

- [ ] **Step 6: Run the focused test**

Run:

```bash
uv run pytest tests/harness/test_current_context.py -q
```

Expected: the charter/current-state tests pass; plan-banner tests remain RED until Task 3.

- [ ] **Step 7: Commit the canonical context surface**

```bash
git add docs/PRODUCT.md .harness/README.md .harness/current.yaml AGENTS.md README.md
git commit -m "docs: make editorial site the canonical product"
```

---

### Task 3: Supersede the platform roadmap and park P4

**Files:**
- Modify: `docs/superpowers/plans/2026-07-10-external-manager-roadmap-implementation.md`
- Modify: `docs/superpowers/plans/2026-07-11-external-manager-p4a-fees-terms.md`
- Modify: `docs/superpowers/plans/2026-07-11-p4-shared-terms-fixture-seam.md`

**Interfaces:**
- Consumes: `docs/PRODUCT.md` and `.harness/current.yaml`.
- Produces: explicit historical/parked status at every tracked plan that could otherwise restart the platform campaign.

- [ ] **Step 1: Add this banner below the roadmap title**

```markdown
> **SUPERSEDED PRODUCT SCOPE — 2026-07-15.** This document is a historical
> implementation record, not an active implementation plan. Its 36-card bitemporal
> platform objective was superseded by the canonical editorial-site charter in
> [`docs/PRODUCT.md`](../../PRODUCT.md). Nothing here blocks website work or becomes
> current unless the user explicitly reauthorizes the product scope and the charter is
> amended.
```

Change the existing status line to:

```markdown
**Status:** superseded historical plan.
```

- [ ] **Step 2: Add this banner below each P4 plan title**

```markdown
> **PARKED OPTIONAL RESEARCH — 2026-07-15.** This plan is preserved for
> resumability but is not active and is not a website prerequisite. Resume only after
> explicit user approval and a fresh product-fit review under
> [`docs/PRODUCT.md`](../../PRODUCT.md). The current parking state lives in
> [`.harness/current.yaml`](../../../.harness/current.yaml).
```

- [ ] **Step 3: Run the full harness-context test and formatting checks**

```bash
uv run pytest tests/harness/test_current_context.py -q
uv run ruff check tests/harness/test_current_context.py
git diff --check
```

Expected: all context tests pass; Ruff and diff checks are clean.

- [ ] **Step 4: Commit the tracked status reset**

```bash
git add docs/superpowers/plans/2026-07-10-external-manager-roadmap-implementation.md docs/superpowers/plans/2026-07-11-external-manager-p4a-fees-terms.md docs/superpowers/plans/2026-07-11-p4-shared-terms-fixture-seam.md tests/harness/test_current_context.py
git commit -m "docs: supersede platform campaign and park P4"
```

---

### Task 4: Reset ignored continuation documents without rewriting history

**Files:**
- Modify: `.superpowers/sdd/continue-prompt.md` (ignored)
- Modify: `.superpowers/sdd/global-constraints.md` (ignored)
- Modify: the primary P4 takeover handoff in `.superpowers/sdd/` (ignored)
- Modify: `.superpowers/sdd/codex-p4-r4-continuation-handoff.md` (ignored)
- Modify: `.superpowers/sdd/progress.md` (ignored, append only)

**Interfaces:**
- Consumes: tracked `docs/PRODUCT.md` and `.harness/current.yaml`.
- Produces: a safe local cold-start route plus preserved P4 recovery details.

- [ ] **Step 1: Replace `continue-prompt.md` with a short cold-start route**

```markdown
# Quant Allocator continuation

Start from the tracked repository authority, not this historical folder:

1. Read `docs/PRODUCT.md`.
2. Read `.harness/current.yaml`.
3. Read `AGENTS.md`.
4. Verify the current Git branch and status.

Current objective: website-first editorial publication and project-idea bank.
Current task: write and review the Aligrithm-grounded website design specification.
The 36-card platform campaign is superseded. P4 is parked and must not resume without
explicit user approval and a fresh product-fit review.

No push or publication is authorized by this continuation note.
```

- [ ] **Step 2: Replace `global-constraints.md` with current durable constraints**

```markdown
# Current durable constraints

- `docs/PRODUCT.md` is the product authority; `.harness/current.yaml` is current state.
- The website is a public static editorial publication and project-idea bank.
- Use public or synthetic data only and fictional displayed names.
- Never include an employer identity or employer-internal facts.
- Preserve certified numbers unless the current task explicitly reopens them.
- Validate rendered copy, formulas, links, layout, and changed interactions.
- Load publication terms from `tools/.publication_terms`; never inline them.
- Use explicit staged paths and no automated attribution trailers.
- P4 and the 36-card platform are parked, not blocked prerequisites.
- No merge, push, or publication without explicit user approval.
```

- [ ] **Step 3: Add a no-auto-resume banner to both P4 handoffs**

Insert immediately below each title:

```markdown
> **PARKED — DO NOT AUTO-RESUME (2026-07-15).** The product scope that made P4
> current has been superseded. Preserve this document as the technical recovery record,
> but do not execute its next actions unless the user explicitly reauthorizes P4 after a
> fresh product-fit review. P4 is not a website prerequisite. See `docs/PRODUCT.md` and
> `.harness/current.yaml`.
```

- [ ] **Step 4: Append the strategic reset to `progress.md`**

Append a dated entry recording:

```markdown
## 2026-07-15 — Website-first product and harness reset

The user confirmed that Quant Allocator's product is an Aligrithm-style editorial
research publication and project-idea bank, not the 36-card bitemporal platform. The
platform roadmap is superseded product scope. P4 is parked at fixture tip `b0596db` and
card tip `7c2964f`; both branches/worktrees are preserved, but neither is a website
prerequisite or automatic continuation target.

Tracked authority now routes through `docs/PRODUCT.md`, `.harness/current.yaml`, and
`AGENTS.md`. The next task is an Aligrithm-grounded website design specification. No
push or publication was authorized.
```

- [ ] **Step 5: Verify ignored-file state separately**

Run:

```bash
git status --short
git worktree list --porcelain
```

Expected: ignored `.superpowers/` edits do not enter tracked status; the two P4 worktrees still point to `b0596db` and `7c2964f`.

---

### Task 5: Run the bounded reset gate and commit the verified endpoint

**Files:**
- Modify: no additional product files.
- Verify: all tracked files from Tasks 1–3 and ignored files from Task 4.

**Interfaces:**
- Consumes: completed reset diff.
- Produces: a clean, reviewable local branch ready for the website-design task.

- [ ] **Step 1: Run focused harness and site checks**

```bash
uv run pytest tests/harness/test_current_context.py tests/site/test_build.py tests/site/test_gallery.py -m "not slow and not network" -q
uv run ruff check tests/harness/test_current_context.py
PYTHONPATH=src uv run python -m quant_allocator.site build
git diff --check
```

Expected: all tests pass, Ruff is clean, the site builds 47 HTML outputs, and no whitespace errors appear.

- [ ] **Step 2: Check for contradictory active authority**

Run:

```bash
rg -n "Status:\*\* active implementation plan|\*\*Status:\*\* active implementation plan" docs/superpowers/plans
```

Expected: no result from the superseded external-manager roadmap. Any unrelated result must be adjudicated before completion.

- [ ] **Step 3: Run the report-only publication scan and inspect every result**

```bash
bash tools/publication_check.sh
```

Expected: no new unaccepted match in the reset range. Pre-existing historical findings, if any, remain a push blocker and do not authorize history rewriting.

- [ ] **Step 4: Review exact scope and commit any final test-only correction**

```bash
git status --short
git diff --stat codex/execution-roadmap-implementation..HEAD
git diff --name-only codex/execution-roadmap-implementation..HEAD
git log --format='%H%n%B' codex/execution-roadmap-implementation..HEAD
```

Expected tracked scope: design, plan, product charter, compact harness state, agent/README routing, three plan banners, and one focused harness test. No site source, data, evidence, P4 worktree, or publication output changes.

- [ ] **Step 5: Stop without pushing**

Report tracked commits, ignored local harness edits, verification results, P4 preservation proof, and the next task. Do not push, publish, merge, or delete worktrees.
