# S7 Unit-B Shared Representability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the reviewed shared evidence substrate represent S7's inherited-delta, early-lineage, and retroactive-membership adversaries without weakening Unit-A admission or changing the reviewed X3 manifest.

**Architecture:** Projection visibility will accept an inherited row only when the projection's original dataset version is an included typed reference in the persisted slice receipt for that exact slice. Each S7 scenario dataset will author only the missing provisional product-path edges under its existing access context and explicitly tombstone those records in its latest delta, leaving X3 as the unique latest path without changing scenario request scope. The retroactive row will link to an X3 membership first visible at the late cutoff but effective over the earlier observation date.

**Tech Stack:** Python 3.11, SQLite shared evidence schema, frozen fixture contracts, `uv`, `pytest`, `ruff`.

## Global Constraints

- Preserve `SCHEMA_VERSION = 1` and schema digest `43a0f22036e3e6b55fc15a05071e58d7771ff5546cedce7c4ee45155f38b0818`.
- Do not change X3-authored rows, its fixture digest, projection counts, held JSON, or public outputs.
- Do not weaken the exact mapping/membership/relationship identity checks in `track_record_provenance/lineage.py`.
- A projection inherited through a delta is visible only when its original version is sealed as an included `dataset-version` reference by the exact slice receipt.
- Provisional S7 product paths are present at `early` and explicitly removed at `latest`; they must never coexist with X3 paths in a latest-known slice.
- Preserve current public/synthetic-only data, fictional names, publication terms, and no estimator/ranking outputs.
- Keep S7 card-track files read-only during this seam; owned production files are limited to `src/quant_allocator/evidence/**`.
- Review acceptance is requirement-backed and risk-proportionate: Critical and Important findings block; a Minor blocks only when it affects numerical correctness, evidence/receipt closure, required copy, interaction behavior, or publication safety. Other Minors are docketed with an explicit defer rationale and do not trigger another whole-seam review.
- No push or publication.

---

### Task 1: Receipt-authorized inherited projection visibility

**Files:**
- Modify: `src/quant_allocator/evidence/projections.py:8-38`
- Test: `tests/evidence/test_projections.py`
- Test: `tests/evidence/test_s7_fixture.py`

**Interfaces:**
- Consumes: persisted `SnapshotSlice.receipt_id`, `reconstruction_receipt`, `receipt_reference`, `receipt_seal`, and `snapshot_manifest` rows created by `as_known_slice`.
- Produces: unchanged public functions `project_entity_mappings`, `project_universe_memberships`, and `project_entity_relationships`, with contributor-version-aware visibility.

- [ ] **Step 1: Write the failing inherited-delta tests**

Add an exact S7 regression that builds the reviewed fixture, materializes hedge and private `latest-known` slices, and proves the inherited `s7-hf-fee-unresolved` and `s7-private-call` observations have no projected mapping on the current code. Assert the same rows project after the fix. Create `replace(slice_, receipt_id=None)`, `replace(slice_, decision_at=None)`, and stripped-receipt plus in-memory child-to-base `dataset_version_id` mutation controls; require controlled `receipt-incomplete` refusal before projection.

Add a generic adversary in `tests/evidence/test_projections.py` that supplies a slice receipt from a different snapshot and asserts it cannot authorize a projection version absent from the exact slice's sealed version set.

- [ ] **Step 2: Run the failing tests to terminal summaries**

Run:

```bash
uv run pytest tests/evidence/test_s7_fixture.py -k "inherited_projection" -q
uv run pytest tests/evidence/test_projections.py -k "receipt_authorized" -q
```

Expected: the S7 inherited rows have no mapping projection before the implementation; the mismatched-receipt adversary must remain refused.

- [ ] **Step 3: Implement exact receipt-authorized version closure**

In `projections.py`, add a private helper with this boundary:

```python
def _authorized_projection_version_ids(
    conn: sqlite3.Connection,
    snapshot_slice: SnapshotSlice,
) -> set[str]:
    if snapshot_slice.receipt_id is None or snapshot_slice.decision_at is None:
        refuse("receipt-incomplete")
    # Require the persisted snapshot manifest to equal the supplied digest/request/rows.
    # Require the receipt header input digest/value/parameters hashes and seal to match.
    # Return only included dataset-version references from that exact verified receipt.
```

Change `_project` to require exact `(source_evidence_item_id, dataset_observation_id)` membership plus `row["dataset_version_id"]` in that authorized set. Do not accept a contributor merely because it belongs to the same dataset or revision chain. Keep latest-revision-before-valid-time filtering unchanged.

Rely on the existing `validate_provenance_*` schema trigger and `test_raw_sql_projection_cannot_mix_item_span_observation_and_version` for exact persisted item/observation/version pairing; do not rematerialize a canonical slice inside each projection call.

- [ ] **Step 4: Run focused and generic projection verification**

```bash
uv run pytest tests/evidence/test_projections.py -m "not slow and not network" -q
uv run pytest tests/evidence/test_s7_fixture.py -k "projection or inherited" -m "not slow and not network" -q
uv run ruff check src/quant_allocator/evidence/projections.py tests/evidence/test_projections.py tests/evidence/test_s7_fixture.py
git diff --check
```

Every command must terminate with its final summary.

- [ ] **Step 5: Commit Task 1**

```bash
git add src/quant_allocator/evidence/projections.py tests/evidence/test_projections.py tests/evidence/test_s7_fixture.py
git commit -m "fix(evidence): project receipt-authorized inherited rows"
```

---

### Task 2: Early-only provisional S7 product paths

**Files:**
- Modify: `src/quant_allocator/evidence/fixtures/public_markets.py:327-585`
- Modify: `src/quant_allocator/evidence/fixtures/credit.py:26-130`
- Modify: `src/quant_allocator/evidence/fixtures/private_markets.py:187-313`
- Modify: `src/quant_allocator/evidence/fixtures/terms.py:2338-2515`
- Modify: `src/quant_allocator/evidence/fixtures/s7.py:570-850`
- Test: `tests/evidence/test_s7_fixture.py`

**Interfaces:**
- Consumes: existing S7 terms schema, delta/tombstone semantics, X3 canonical IDs, and downstream-coexistence ownership rule.
- Produces: complete early S7 paths for `vehicle:x3-00`, `composite:x3-00`, `strategy:x3-04`, and `vehicle:x3-08` inside the existing scenario/access scopes; latest-known slices omit those provisional S7 path rows and use the unchanged X3 graph.

- [ ] **Step 1: Write the failing early/latest path tests**

Add one fixture test that invokes `build_lineage_from_s7_projections` only as a consumer assertion. At `early`, require the planted public EUR row, hedge fee row, both credit rows, and private call/NAV rows to avoid `lineage-relationship-missing`. At `latest`, require exactly one complete relationship path per admitted canonical entity and assert no provisional S7 path relationship ID is projected. Pin the unchanged X3 fixture digest before and after S7 build.

- [ ] **Step 2: Run the failing path test**

```bash
uv run pytest tests/evidence/test_s7_fixture.py -k "provisional_path" -q
```

Expected: all four early scenarios currently fail `lineage-relationship-missing`.

- [ ] **Step 3: Author the bounded provisional path inventory**

Define one shared immutable specification helper in `s7.py`, then author the missing edges inside the scenario dataset that already carries the correct evidence right/access context. Reuse the one X3 edge visible at `early` (`manager:x3-00 -> adviser:x3-00`). Public and hedge require separate source rows because they do not share a source dataset, but hedge stops at composite grain and therefore does not duplicate public's `implemented_by` edge:

```text
public-equity (`dataset:s7-public-registered`), four rows:
               manager:x3-00 -> strategy:x3-00 -> composite:x3-00 -> vehicle:x3-00,
               adviser:x3-00 -> legal-entity:x3-00
hedge-fund (`dataset:s7-lineage-terms`), three rows:
               manager:x3-00 -> strategy:x3-00 -> composite:x3-00,
               adviser:x3-00 -> legal-entity:x3-00
credit (`dataset:s7-credit-lineage`), three rows:
               manager:x3-01 -> strategy:x3-04,
               manager:x3-01 -> adviser:x3-01 -> legal-entity:x3-01
private-market (`dataset:s7-private-cashflow-nav`), five rows:
               manager:x3-02 -> strategy:x3-08 -> composite:x3-08 -> vehicle:x3-08,
               manager:x3-02 -> adviser:x3-02 -> legal-entity:x3-02
```

Every row is effective from `2024-01-01T00:00:00Z`, uses scope `provisional-lineage:<scenario>`, and has its own authored assertion span. Add one latest delta to public and credit, extend the existing latest private delta, and extend the latest terms delta so each explicitly removes exactly its own provisional source keys. Do not tombstone return/cash-flow/NAV rows, the six portability relationships, fee evidence, or death evidence. Keep `_SCENARIO_DATASETS` unchanged so public, NDA, segregated-mandate, and funded-private rights do not bleed across scenarios.

`build_s7_terms_sources` is invoked once before the closed-product observation is known and again with `death_observation_id`. Create the terms latest delta only in the death-bearing call; creating a tombstone-only child during the first call would make the second call a competing latest child.

Register the identical strict `schema:s7-relationship-evidence-v1` shape in public, credit, private, and terms datasets; do not create scenario-specific schema variants.

Update `_insert_s7_relationships` to load `s7-relationship-evidence` from every S7 scenario dataset's `early` version, and update scenario-contract construction to include only relationship IDs sourced from that scenario's declared datasets. The expected authored inventory is 21 rows: 15 provisional path rows (public 4, hedge 3, credit 3, private 5) plus the existing six hedge portability rows. Keep relationship IDs derived by the shared `machine_id` framing.

**Post-method-review L9 closure amendment (2026-07-13):** the 21-row count above is the reviewed representability-seam baseline. The required planted `s7-hf-overlap` case was not yet represented end to end. Its bounded closure adds one prerequisite `offers` interval and exactly two overlapping `reported_through` ownership intervals in the existing hedge terms dataset, taking the authored inventory to 24 and the hedge scenario count to 12. The overlap row maps to existing `composite:x3-01`; no X3-authored row, universe, access context, or local resolver changes.

Pin final scenario relationship cardinalities as public `4`, hedge `12`, credit `3`, private `5`; the hedge count was `9` at the original seam close and becomes `12` only through the L9 amendment. Scenario-contract count remains `4` and paired-bundle-contract count remains `8`.

- [ ] **Step 4: Prove early presence, latest absence, deterministic closure, and X3 non-regression**

```bash
uv run pytest tests/evidence/test_s7_fixture.py -k "relationship or provisional_path or complete_manifest or deterministic" -m "not slow and not network" -q
uv run pytest tests/evidence/test_x3_fixture.py -k "downstream or manifest_verifier" -m "not slow and not network" -q
uv run ruff check src/quant_allocator/evidence/fixtures/public_markets.py src/quant_allocator/evidence/fixtures/credit.py src/quant_allocator/evidence/fixtures/private_markets.py src/quant_allocator/evidence/fixtures/terms.py src/quant_allocator/evidence/fixtures/s7.py tests/evidence/test_s7_fixture.py
git diff --check
```

Every command must terminate with its final summary.

- [ ] **Step 5: Commit Task 2**

```bash
git add src/quant_allocator/evidence/fixtures/public_markets.py src/quant_allocator/evidence/fixtures/credit.py src/quant_allocator/evidence/fixtures/private_markets.py src/quant_allocator/evidence/fixtures/terms.py src/quant_allocator/evidence/fixtures/s7.py tests/evidence/test_s7_fixture.py
git commit -m "feat(evidence): close early S7 relationship paths"
```

---

### Task 3: Late retroactive-membership closure

**Files:**
- Modify: `src/quant_allocator/evidence/fixtures/s7.py:714-805`
- Test: `tests/evidence/test_s7_fixture.py`

**Interfaces:**
- Consumes: the existing `s7-hf-retro-member` observation and the reviewed X3 late-only logical source `x3-source-0003 -> composite:x3-03`, effective from `2024-01-01` but first visible at the latest cutoff.
- Produces: one persisted observation-membership link whose membership is unavailable at `early`, visible at `latest`, and effective over the January observation.

- [ ] **Step 1: Write the failing cutoff test**

Build the fixture and assert only the planted retro row maps to `composite:x3-03` and has exactly one persisted link. At `early`, require logical source key `x3-source-0003`, its mapping, and its membership to be absent from the receipted X3 slice—not merely a later version-specific ID—and require the row not to be admitted. At `latest`, require that exact logical source/mapping/membership, historical valid-time coverage over `2024-01-31`, one admitted row, and no current-roster fallback.

- [ ] **Step 2: Run the failing cutoff test**

```bash
uv run pytest tests/evidence/test_s7_fixture.py -k "retroactive_membership" -q
```

Expected: zero persisted links on current code.

- [ ] **Step 3: Bind the row to the late-visible membership**

Special-case only `s7-hf-retro-member` in `_close_s7_projection_links`: map it to `composite:x3-03`, then replace the unconditional skip with `_x3_membership_for(..., canonical_entity_id="composite:x3-03", cutoff_name="latest", source_key="x3-source-0003")`. Persist the normal link identity. Do not add a new X3 membership, alter its dates/status, infer retroactivity from version-ID churn, or add a caller-authored knowledge timestamp.

- [ ] **Step 4: Run focused closure and determinism checks**

```bash
uv run pytest tests/evidence/test_s7_fixture.py -k "retroactive_membership or projection_closure or complete_manifest or deterministic" -m "not slow and not network" -q
uv run ruff check src/quant_allocator/evidence/fixtures/s7.py tests/evidence/test_s7_fixture.py
git diff --check
```

Every command must terminate with its final summary.

- [ ] **Step 5: Commit Task 3**

```bash
git add src/quant_allocator/evidence/fixtures/s7.py tests/evidence/test_s7_fixture.py
git commit -m "feat(evidence): bind late S7 retroactive membership"
```

---

### Task 4: Whole-seam verification and independent review

**Files:**
- Modify only if findings require a bounded correction: files already owned by Tasks 1-3.
- Record local review report: `.superpowers/sdd/s7-unit-b-shared-seam-review.md`

**Interfaces:**
- Produces: one clean reviewed seam tip that can be merged by the primary integration owner into `codex/roadmap-s7-impl` before Unit-B Task 3 resumes.

- [ ] **Step 1: Run the affected substrate and fixture suites in bounded foreground commands**

```bash
uv run pytest tests/evidence/test_projections.py -m "not slow and not network" -q
uv run pytest tests/evidence/test_s7_fixture.py -m "not slow and not network" -q
uv run pytest tests/flagships/test_s7_provenance_model.py tests/flagships/test_s7_provenance_lineage.py tests/flagships/test_s7_provenance_leakage.py -m "not slow and not network" -q
uv run pytest tests/evidence/test_x3_fixture.py -k "downstream or relationship or manifest_verifier" -m "not slow and not network" -q
uv run pytest tests/evidence/test_x3_fixture.py -k "point_in_time_and_delivery_cases or latest_slices_project_complete_typed_shapes" -m "not slow and not network" -q
uv run ruff check src/quant_allocator/evidence/projections.py src/quant_allocator/evidence/fixtures/public_markets.py src/quant_allocator/evidence/fixtures/credit.py src/quant_allocator/evidence/fixtures/private_markets.py src/quant_allocator/evidence/fixtures/s7.py src/quant_allocator/evidence/fixtures/terms.py tests/evidence/test_projections.py tests/evidence/test_s7_fixture.py
git diff --check 2f64f33..HEAD
```

Run each command separately and preserve its terminal exit/final summary. Do not substitute a partial dot stream.

- [ ] **Step 2: Rebuild twice and pin deterministic identities**

In two fresh SQLite connections, build S7 and assert exact equality of fixture manifest, authored closure digest, eight paired bundle contracts, scenario contracts, and all new relationship/link IDs. Confirm `verify_x3_manifest` remains true and its fixture digest is byte-identical before/after S7 build.

- [ ] **Step 3: Run report-only publication and trailer checks**

From a checkout containing `tools/.publication_terms`, run `tools/publication_check.sh`, inspect every match, and require no new tracked canary match. Check commits for prohibited attribution trailers. Do not push.

- [ ] **Step 4: Obtain an independent whole-seam PASS**

Dispatch a read-only reviewer with the anti-injection boundary, frozen base/tip/package SHA-256, this plan, the S7 fixture plan/spec, projection substrate, and all Tasks 1-3 diffs. Require re-derivation of inherited-version authorization, early/latest path uniqueness, retroactive cutoff behavior, deterministic manifest closure, X3 non-regression, and terminal commands. Critical and Important findings block. A Minor blocks only under the Global Constraints risk rule; otherwise record it with an explicit defer rationale and do not restart the whole-seam review.

- [ ] **Step 5: Merge only the reviewed clean tip into the S7 card branch**

The primary integration owner merges the seam into `codex/roadmap-s7-impl`, resolves no shared conflict inside the card track, reruns the seam smoke tests there, updates the local unit/progress ledgers, and then resumes Task 3 from the preserved uncommitted basis work. No push or publication.
