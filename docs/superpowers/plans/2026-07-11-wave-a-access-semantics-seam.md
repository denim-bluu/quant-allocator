# Wave-A Claim Access Semantics Seam Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task.

**Goal:** Add one strict, shared claim-level access-semantics contract that unblocks X3, S7, S8, M7, P4, and P5 without weakening the production manifest or conflating current synthetic attestation with live-data authorization.

**Architecture:** The site manifest remains the source of truth. Every claim must name one controlled access semantic; production rows are explicitly migrated, while the existing `allow_legacy=True` test-fixture upgrader supplies its own compatibility value. The builder validates the semantic, includes it in search, and renders claim-derived access badges; card-level access contexts remain exactly the union of claim contexts and keep their existing gallery-filter meaning.

**Tech Stack:** Python, PyYAML, Jinja2, pytest, static HTML.

## Global Constraints

- `access_semantics` is mandatory in `CLAIM_KEYS`; there is no production default or partial-schema fallback.
- Controlled values are exactly `exact-per-dataset`, `exact-per-selected-dataset`, `all-required-per-selected-dataset`, `all-required-per-dataset`, `refusal-per-inadmissible-input`, `refusal-in-every-context`, and `synthetic-fixture-only`.
- Current attestation, live ceiling, access contexts, and access semantics remain independent. Current D never implies `synthetic-fixture-only` by itself.
- The 20 existing claims migrate explicitly: `s1`, `s2`, `s3`, `s4`, `s5`, `m1`, `m2`, `m3`, `m4`, `m5`, `p1`, `p2`, `p3`, `e1`, `e2`, and `e3` use `all-required-per-selected-dataset`; `m6` uses `exact-per-selected-dataset`; `s6` uses `refusal-in-every-context`; and `x1`/`x2` use `synthetic-fixture-only` because their live ceilings remain D and their claims are explicitly simulation/teaching outputs.
- The legacy upgrader may add `all-required-per-selected-dataset` only behind explicit `allow_legacy=True`.
- Card-level `access_contexts` must continue to equal the union of claim access contexts exactly.
- Gallery `data-access` filtering continues to use claim access-context union, not access-semantic tokens.
- Search must include every claim's access semantic.
- Every demo page must render a visible, claim-derived access-semantics badge for every claim; no card-level inferred substitute is allowed.
- No statistics, card JSON, estimator, generator, method-spec mathematics, or browser-side arithmetic changes.
- Use existing typography, chips, and decision-context layout; do not invent a new design system.
- Run only bounded site tests, Ruff, strict build, and publication checks; do not push or publish.

---

### Task 1: Strict manifest contract and explicit production migration

**Files:**

- Modify: `src/quant_allocator/site/build.py`
- Modify: `site/cards.yaml`
- Modify: `tests/site/test_manifest.py`
- Modify: `tests/site/test_lint.py`

**Interfaces:**

- Produces: `VALID_ACCESS_SEMANTICS: set[str]` and mandatory `claim["access_semantics"]` validation.
- Preserves: `load_manifest(path, allow_legacy=False)` strict production behavior and exact claim-access union.

- [ ] Add failing manifest tests proving omission, unknown values, and non-string values refuse; all seven controlled values load; a production row with the field deleted refuses; explicit legacy upgrade still succeeds and emits `all-required-per-selected-dataset`.
- [ ] Run `uv run pytest tests/site/test_manifest.py -m "not slow and not network" -q` and confirm the new tests fail for the missing contract.
- [ ] Add `access_semantics` to `CLAIM_KEYS`, define the exact seven-value controlled set, validate membership with a claim-specific `BuildError`, and add the compatibility value only inside `_upgrade_legacy_entry`.
- [ ] Add the exact per-card semantics from Global Constraints explicitly to every existing claim in `site/cards.yaml` and add an explicit reviewed value to strict test fixtures such as `tests/site/test_lint.py`; do not add a production fallback.
- [ ] Re-run the focused test and require PASS.
- [ ] Review `git diff --check` and commit only these files as `feat(site): require claim access semantics` without trailers.

### Task 2: Search and visible claim-derived access badges

**Files:**

- Modify: `src/quant_allocator/site/build.py`
- Modify: `site/templates/demo.html.j2`
- Modify: `tests/site/test_gallery.py`
- Modify: `tests/site/test_build.py`

**Interfaces:**

- Consumes: validated `claim["access_semantics"]` from Task 1.
- Produces: search-corpus inclusion and one visible badge per claim while preserving `data-access` context filtering.

- [ ] Add failing tests that require every access semantic in the rendered search corpus; prove `data-access` remains the exact claim-context union and does not contain semantic tokens; render a real demo and require one semantic badge per claim with the exact claim ID and controlled value.
- [ ] Run `uv run pytest tests/site/test_gallery.py tests/site/test_build.py -m "not slow and not network" -q` and confirm the new assertions fail.
- [ ] Add `access_semantics` to `_search_corpus` claim fields. In `demo.html.j2`, add an `Access semantics` decision-context row that iterates every claim and renders the claim ID plus `labels[claim.access_semantics]` in the existing chip language.
- [ ] Add readable labels for all six controlled values to `TOKEN_LABELS`; do not add a new gallery facet or change JavaScript filtering.
- [ ] Run the focused manifest/gallery/build tests, Ruff on changed Python/tests, and `PYTHONPATH=src uv run python -m quant_allocator.site build`; require PASS and zero manifest/card-count drift.
- [ ] Load `tools/.publication_terms` and run the required case-insensitive word-boundary endpoint/range scan; inspect the report-only output. Run `git diff --check` and confirm no trailers.
- [ ] Commit only these files as `feat(site): render claim access semantics` without trailers.

## Independent review gate

An independent reviewer must inspect the full task range and return both unconditional spec-compliance PASS and code-quality PASS. The reviewer must prove:

- all 20 production claims match the explicit per-card migration map and there is no production default;
- the seven-value set exactly matches the reviewed X3/S7/M7/P4/E4 contracts;
- missing/unknown semantics fail before rendering;
- `allow_legacy=True` remains the only compatibility path;
- search includes semantics, access filtering remains context-based, and every demo badge comes from a claim row;
- current D/live-ceiling/access-context meanings are not collapsed into one field;
- bounded tests, strict build, publication scan, and clean diff pass.

Critical or Important findings return to the implementer and require re-review before merge.
