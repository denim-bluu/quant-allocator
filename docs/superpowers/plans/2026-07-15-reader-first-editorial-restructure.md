# Reader-First Editorial Restructure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to
> implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the current harness-first publication into a guided reader-first
curriculum while preserving reviewed calculations, committed data, and publication
safeguards.

**Architecture:** Keep the Python/Jinja static generator. Add an optional public-article
source beside each reviewed method spec, make the shared templates progressively
disclose technical governance, and use the existing manifest plus small presentation
maps for curriculum metadata. Prove the contract on S2 before rolling it through the
homepage, remaining articles, and dense exhibits.

**Tech Stack:** Python 3.11, Jinja2, Python-Markdown, YAML, semantic HTML, CSS, vanilla
JavaScript, pytest, KaTeX, in-app Browser.

## Global Constraints

- Authority: `docs/PRODUCT.md`, then `docs/EDITORIAL_SYSTEM.md`, then this plan.
- Evidence: `docs/audits/2026-07-15-reader-journey-audit.md`.
- Public or synthetic data only; all displayed manager and fund names remain fictional.
- Do not change committed numerical JSON, generators, estimators, or method-spec rulings
  unless a failing test proves a required correctness repair.
- A numerical re-review is required only when a displayed value, calculation,
  quantitative claim, or semantic interpretation changes.
- Browser JavaScript may select committed states or map values to pixels; it may not
  recompute estimators.
- Use one shared-seam integration owner. Content tracks may edit only assigned public
  article files after the S2 contract is green.
- Use explicit `git add <paths>` and commits without attribution trailers.
- Keep merge, push, and publication false. Defer consolidated whole-site review until
  the reader-first rollout is complete.

---

### Task 1: Activate the cold-session-safe reader-first objective

**Files:**

- Modify: `tests/harness/test_current_context.py`
- Modify: `.harness/current.yaml`
- Modify: `.harness/README.md`
- Modify: `AGENTS.md`

**Interfaces:**

- Consumes: `docs/PRODUCT.md`, `docs/EDITORIAL_SYSTEM.md`, this plan, and the audit.
- Produces: one discoverable active objective with the S2 pilot as its next action.

- [ ] **Step 1: Write the failing harness assertions.** Require
  `editorial_system == "docs/EDITORIAL_SYSTEM.md"`, the exact audit path, this exact
  active-plan path, `current_task == "WEBSITE-EDITORIAL-R1-S2-PILOT"`, false outward
  authority, and an active plan opening that cites both the editorial system and audit.

- [ ] **Step 2: Verify RED.** Run:

  ```bash
  env UV_CACHE_DIR=/private/tmp/quant-allocator-uv-cache uv run pytest \
    tests/harness/test_current_context.py -q
  ```

  Expected: failure because the completed-release harness has no editorial-system,
  audit, or active-plan fields.

- [ ] **Step 3: Update the compact harness.** Set:

  ```yaml
  editorial_system: docs/EDITORIAL_SYSTEM.md
  evidence_record: docs/audits/2026-07-15-reader-journey-audit.md
  scheduler:
    current_task: WEBSITE-EDITORIAL-R1-S2-PILOT
    active_plan: docs/superpowers/plans/2026-07-15-reader-first-editorial-restructure.md
    next_action: >-
      Implement the S2 reader-first public article and exhibit pilot without changing
      committed numerics, then verify desktop and 390px rendering.
  verification:
    current_level: reader-first-restructure-in-progress
    required:
      - targeted-site-tests
      - fresh-static-build
      - output-integrity
      - rendered-desktop-mobile-qa
      - scoped-publication-canary
      - consolidated-final-review
  ```

  Preserve the P4 parked block and keep merge, push, and publish false. Update normal
  initialization so website tasks read the named editorial system before the active
  plan. Reject `COMPLETED HISTORICAL PLAN` and `HISTORICAL FIRST REDESIGN` as active-plan
  authority.

- [ ] **Step 4: Verify GREEN.** Run the same harness test; expect all tests to pass.

- [ ] **Step 5: Commit.** Explicitly stage the four files and this plan; commit:
  `chore(harness): activate reader-first S2 pilot`.

### Task 2: Separate S2's public article from its reviewed method spec

**Files:**

- Create: `docs/ideas/articles/s2-uncertainty-honest-tear-sheet.md`
- Modify: `site/cards.yaml`
- Modify: `src/quant_allocator/site/build.py`
- Modify: `site/templates/spec.html.j2`
- Modify: `site/assets/interval.css`
- Modify: `tests/site/test_s2.py`
- Modify: `tests/site/test_manifest.py`
- Modify: `tests/site/test_specs.py`
- Modify: `tests/site/test_interval_css.py`
- Modify: `tests/site/test_build.py`

**Interfaces:**

- Consumes: optional manifest key `article`, existing key `spec`, and reviewed S2
  calculations/copy.
- Produces: the existing `specs/s2.html` URL with a reader-facing body and a separate
  `Technical method and provenance` source link.
- Fallback: a live card without `article` continues to render its method spec until its
  migration task lands.

- [ ] **Step 1: Write the failing source-boundary tests.** Require:

  ```python
  assert "Why the obvious answer fails" in public_html
  assert "A small numerical example" in public_html
  assert "What the evidence changes" in public_html
  assert "Limits and go-live" in public_html
  assert "Key takeaways" in public_html
  assert "Technical method and provenance" in public_html
  assert public_html.index("A small numerical example") < public_html.index("The method")
  for internal in ("**Date:**", "**Status:**", "**Card:**", "**Demo:**",
                   "Displayed field", "JSON field"):
      assert internal not in public_body_source
  ```

  Move the reproduction-map assertion to the unchanged method-spec source. Add manifest
  tests for a valid article file and the named `missing article file` failure. Make the
  corpus math test count expressions from `article` when present, otherwise `spec`.

- [ ] **Step 2: Verify RED.** Run:

  ```bash
  env UV_CACHE_DIR=/private/tmp/quant-allocator-uv-cache uv run pytest \
    tests/site/test_s2.py tests/site/test_manifest.py tests/site/test_specs.py \
    tests/site/test_interval_css.py tests/site/test_build.py -q
  ```

  Expected: failure because `article` is not a valid manifest key and the public page
  still renders the method spec.

- [ ] **Step 3: Add the optional article contract.** Add `article` to `OPTIONAL_KEYS`.
  `_validate_live_entry()` resolves it under `docs/ideas/articles/` and reports a named
  missing-file error. `_render_specs()` chooses the article source when present, retains
  the current spec fallback, uses one `markdown.Markdown` instance with `toc`, and passes
  `article_toc`, `is_public_article`, and `method_source_url` to the template.

- [ ] **Step 4: Write the S2 public article.** Use the exact heading sequence required by
  `docs/EDITORIAL_SYSTEM.md`. Preserve the reviewed unsmoothing example, interval values,
  factor-attribution limits, pointwise-drawdown warning, go-live requirements, and
  references. Do not copy implementation dockets, review rulings, or full code listings.

- [ ] **Step 5: Add reading scaffolding.** The S2 page shows `Foundation · 12 min ·
  Intermediate`, a short contents list, paired exhibit links at both ends, key
  takeaways, `Next in this path: S1`, and a separate technical-method link. Legacy pages
  retain their current rendering until migrated.

- [ ] **Step 6: Contain display math.** Add:

  ```css
  .spec-page__body .katex-display {
    max-width: 100%;
    overflow-x: auto;
    overflow-y: hidden;
  }
  ```

  Preserve keyboard scrolling and add a mobile focus style. Bump `ASSET_VERSION` once
  and update the exact cache-busting assertion.

- [ ] **Step 7: Verify GREEN.** Run the focused command from Step 2. Then build and assert
  that S2 body width does not exceed 390px in Browser.

- [ ] **Step 8: Commit.** Stage only the named files; commit:
  `feat(editorial): add reader-first S2 article`.

### Task 3: Put S2's focal evidence before governance

**Files:**

- Modify: `site/templates/demo.html.j2`
- Modify: `site/templates/pages/s2-tearsheet.html.j2`
- Modify: `site/assets/interval.css`
- Modify: `site/assets/pages/s2.css`
- Modify: `tests/site/test_s2.py`
- Modify: `tests/site/test_build.py`

**Interfaces:**

- Consumes: existing S2 committed JSON and template values.
- Produces: additive shared `demo_lead` / `decision_context` blocks and an S2-only
  reader-first order without changing the other 22 exhibit bodies.

- [ ] **Step 1: Write the failing order and annotation tests.** Require the rendered S2
  order:

  ```text
  decision takeaway → reported/de-smoothed focal comparison →
  collapsed Evidence and readiness → further analysis
  ```

  Assert a labelled `<figure>` for the focal comparison, visible zero/scale labels on
  interval rails, visible month/drawdown labels and legend for the drawdown chart, a
  visible monthly-return time/units label, and the unchanged `card-context` content
  inside a `<details class="evidence-appendix">`.

- [ ] **Step 2: Verify RED.** Run `tests/site/test_s2.py` and `tests/site/test_build.py`;
  expect order and annotation failures.

- [ ] **Step 3: Add shared extension points.** Add an empty `demo_lead` block and an
  overridable `decision_context` block to `demo.html.j2`. Keep the default rendered
  order unchanged for cards without a public article.

- [ ] **Step 4: Recompose S2.** Move its decision sentence and the existing
  reported/de-smoothed comparison into `demo_lead`; place the governance record in the
  collapsed appendix; keep factor, drawdown, and return analysis below. Add prose
  immediately after each visual saying what it changes and what remains uncertain.

- [ ] **Step 5: Verify GREEN and render.** Run the focused tests and inspect desktop
  1440×900 plus mobile 390×844. The main comparison must be visible before the appendix;
  no body overflow or console error is allowed.

- [ ] **Step 6: Commit.** Commit:
  `feat(editorial): lead S2 exhibit with evidence`.

### Task 4: Make the homepage one curriculum with secondary discovery

**Files:**

- Modify: `src/quant_allocator/site/build.py`
- Modify: `site/templates/index.html.j2`
- Create: `site/templates/exhibits.html.j2`
- Modify: `site/templates/base.html.j2`
- Modify: `site/assets/gallery.css`
- Modify: `site/assets/gallery.js` only for heading/state synchronization
- Modify: `tests/site/test_gallery.py`
- Modify: `tests/site/test_build.py`
- Modify: `tests/site/test_output_integrity.py`

**Interfaces:**

- Consumes: `CURRICULUM_IDS = ("s2", "s1", "m3")`, card manifest, and existing facets.
- Produces: hero → guided curriculum → five pillars → featured reading → optional browse,
  plus a complete `exhibits.html` index.

- [ ] **Step 1: Write failing homepage tests.** Require the S2/S1/M3 order; trap,
  ability, time, and difficulty per step; Start Here before pillars; pillars before
  featured reading; browse last; no empty stage; explicit `Read article` / `View exhibit`
  actions; `Detailed` / `Compact` visible labels; and a complete exhibit index with 23
  links.

- [ ] **Step 2: Verify RED.** Run gallery, build, and output-integrity tests; expect the
  old S2/X1/X2 and single-link card assertions to fail.

- [ ] **Step 3: Shape presentation data.** Replace the old start map with the locked
  curriculum and filter empty stages before rendering. Keep evidence facets and search
  data unchanged.

- [ ] **Step 4: Recompose the homepage.** Make Start Here full-width and visually
  primary. Use pillars as the main corpus organization. Replace the linked tile wrapper
  with an article element containing the two explicit actions. Rename the density switch
  without changing its tested query serialization, and use the neutral heading `All
  research` so the compact state does not contradict it.

- [ ] **Step 5: Add the exhibit index.** Generate `exhibits.html` from the same cards;
  no separate registry. Update nav and breadcrumbs to the real index.

- [ ] **Step 6: Verify GREEN and render.** Exercise search, detailed/compact, one preset,
  one facet, clear, back/forward, both card actions, and the exhibit index on desktop and
  mobile.

- [ ] **Step 7: Commit.** Commit:
  `feat(editorial): make curriculum the primary journey`.

### Task 5: Migrate the remaining public articles through the proven contract

**Files:**

- Create: `docs/ideas/articles/<spec filename>` for S1, S3–S7, M1–M6, P1–P3,
  E1–E4, and X1–X3.
- Modify: `site/cards.yaml` (integration owner only).
- Create: `tests/site/test_public_articles.py`.
- Modify: `src/quant_allocator/site/build.py` only for proven shared metadata needs.

**Interfaces:**

- Consumes: each reviewed method spec and the green S2 public-article contract.
- Produces: 23 explicit public article sources; the reviewed specs remain unchanged.

- [ ] **Step 1: Write the failing corpus contract.** For every live card, require an
  existing `article` file, no H1 or repository metadata in its opening, the standard
  problem/example/method/evidence/limits/takeaways sequence, a technical-method link,
  valid internal article links, and a rendered word count between 900 and 3,500 unless a
  named test exception explains the reason.

- [ ] **Step 2: Verify RED.** Expect 22 cards without an article field.

- [ ] **Step 3: Dispatch file-disjoint content batches.** Use these ownership sets:

  - Signal: S1, S3, S4, S5, S6, S7.
  - Monitoring/portfolio: M1–M6, P1–P3.
  - Evidence/foundations: E1–E4, X1–X3.

  Each article derives claims and numbers only from its reviewed spec, uses the common
  heading contract, retains material limitations and go-live requirements, and returns
  a source-to-public claim checklist. Tracks do not edit the manifest, builder,
  templates, tests, or shared CSS.

- [ ] **Step 4: Integrate explicitly.** The primary owner reviews each article against
  its source, then adds exact `article` filenames to `site/cards.yaml` in one pass.

- [ ] **Step 5: Verify GREEN.** Run the public-article, manifest, spec-math, build, and
  output-integrity tests. Build all pages and check article links internally.

- [ ] **Step 6: Commit by content batch.** Use three explicit commits ending with:
  `feat(editorial): complete public article corpus`.

### Task 6: Roll out the exhibit contract and simplify dense exceptions

**Files:**

- Modify: `site/templates/demo.html.j2`
- Modify: `site/templates/pages/s1-ledger.html.j2`
- Modify: `site/templates/pages/x2-playground.html.j2`
- Modify: `site/templates/pages/e4-operational-evidence-change.html.j2`
- Modify: `site/templates/pages/s7-provenance.html.j2`
- Modify: corresponding page CSS and focused tests.

**Interfaces:**

- Consumes: all cards now having public articles and the additive blocks proven by S2.
- Produces: evidence-first ordering across the corpus with named dense-page exceptions.

- [ ] **Step 1: Write failing shared-order and dense-page tests.** Require migrated
  exhibits to show focal content before `Evidence and readiness`; S1 to show three focal
  managers before the roster; X2 to show one instructed before/after comparison and a
  `What changed` sentence; E4/S7 to open on one narrated state before advanced tables.

- [ ] **Step 2: Verify RED.** Run only the corresponding page tests.

- [ ] **Step 3: Apply the shared order.** Use the already-proven blocks; do not delete
  context, methodology, go-live, attestation, receipts, or refusal states.

- [ ] **Step 4: Simplify the four outliers.** Use progressive disclosure and existing
  committed states only. Do not create new calculations or data.

- [ ] **Step 5: Verify GREEN and representative rendering.** Inspect one exhibit per
  pillar plus S1, X2, E4, and S7 at desktop/mobile.

- [ ] **Step 6: Commit.** Commit:
  `feat(editorial): complete reader-first exhibit rollout`.

### Task 7: Consolidated rendered and publication gate

**Files:**

- Modify only for reproduced defects: the narrow owning template/CSS/JS/test file.
- Update: `.harness/current.yaml` after all checks pass.

**Interfaces:**

- Consumes: completed reader-first corpus.
- Produces: a clean, locally committed branch ready for a separate merge decision.

- [ ] **Step 1: Run targeted automated checks in bounded foreground commands.** Do not
  combine the heavy suite into one process. Run harness, site contract groups, page
  groups, ruff on changed Python/tests, JavaScript syntax checks, and `git diff --check`.

- [ ] **Step 2: Build fresh static output.** Run:

  ```bash
  PYTHONPATH=src env UV_CACHE_DIR=/private/tmp/quant-allocator-uv-cache \
    uv run python -m quant_allocator.site build
  ```

  Require 48 HTML files: homepage, exhibit index, 23 articles, and 23 exhibits.

- [ ] **Step 3: Run Browser QA.** The flow is: homepage → Start Here S2 → S2 exhibit →
  S1 → M3 → browse/search → exhibit index. Test 1440×900 and 390×844, console health,
  body overflow, formulas, menu, theme, detailed/compact, search, preset, facet, clear,
  back/forward, reciprocal links, and one interaction on S1/X2/E4/S7.

- [ ] **Step 4: Run one adversarial reader review.** Review only editorial coherence,
  accessibility, quantitative-copy fidelity, and publication safety. Do not reopen
  numerical calculations that did not change.

- [ ] **Step 5: Run and adjudicate `tools/publication_check.sh`.** This is report-only;
  every current-tree hit is a blocker. Do not push or publish.

- [ ] **Step 6: Close the harness locally.** Set the task to
  `WEBSITE-EDITORIAL-RESTRUCTURE-COMPLETE`, active plan to null, current level to
  `reader-first-site-locally-verified`, and next action to await explicit merge
  authority. Keep merge, push, and publish false.

- [ ] **Step 7: Commit the verified closeout.** Commit:
  `chore(editorial): close reader-first restructure`.
