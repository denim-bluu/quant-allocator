# S7 Shared Typed Fixture Seam Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the separately reviewed, deterministic shared evidence fixture that makes every S7 provenance, basis, vintage, membership, relationship, and method-policy test representable without adding card-local evidence machinery.

**Architecture:** A new `fixtures.s7` orchestrator composes the reviewed X3 fixture with eight S7-namespaced datasets populated by bounded additive helpers in the four existing multi-asset fixture modules. Every authored fact uses a strict record-kind schema, canonical field spans, machine-derived IDs, typed projections, and shared snapshot receipts; a persisted manifest verifier compares the supplied database with a pristine rebuild and leaves the two new computed digest literals to an independent digest gate. The seam does not change the evidence schema, X3, E3, or any card code.

**Tech Stack:** Python 3.11, SQLite, PyYAML-compatible canonical JSON payloads, `dataclasses`, `Decimal`, `pytest`, Ruff, and the existing `quant_allocator.evidence` ingest/projection/snapshot/receipt APIs.

## Global Constraints

- Edit only the seven implementation files listed in **File ownership**. No schema, X3, E3, demo-data, card, JSON, site, CSS, JavaScript, or method-spec file is in scope.
- Work from a branch that contains main audit tip `60bdccb9ab9a110c6b9aa43191054ad111a133e5` and claim-access seam `1ff72ec3c2f3eeb19af65294bd559671e400c167`.
- Task 0 requires final reviewed X3 implementation tip `d7b2e794367acd5a5b2573e4f7e7a20493326a37`, merged at `a3713fcf83ed026f71bffe710d1804ab6418dbc0`, to be an ancestor of the implementation branch. An open review finding, dirty substituted implementation, absent merge, or different final tip stops all fixture work.
- Preserve evidence `SCHEMA_VERSION = 1` and schema digest `43a0f22036e3e6b55fc15a05071e58d7771ff5546cedce7c4ee45155f38b0818`; no migration or new table is permitted.
- Build and verify the reviewed X3 fixture through `build_x3_fixture(conn)` and `verify_x3_manifest(conn, manifest)`. Never reproduce its mappings, memberships, relationships, cutoffs, or receipts in S7 code.
- Preserve X3 `source_status` exactly as `active | inactive | closed | unknown`; never store, derive, or rename an X3 status to `dead`. A dead display/audit label requires separate, S7-owned, receipted vintage/death evidence first known by the applicable cutoff.
- Do not modify the pinned X3 authored closure. All new rows use `dataset:s7-*`, S7 source keys, and S7-owned receipt policies; `verify_x3_manifest` must pass before and after S7 construction.
- All displayed names and scenario codes are fictional. No employer, real manager, licensed source, credential, or hidden truth enters tracked files.
- Every value-bearing payload uses a strict record-kind schema with `additionalProperties: false`; no S7 evidence item may use `schema:generic-v1`.
- Numeric source values are authored as decimal strings and parsed with `Decimal`; no float is admitted to source payloads, manifest arithmetic, or equality assertions.
- Every required payload field has exactly one canonical `EvidenceSpanRecord` over its canonical JSON bytes. Relationship and policy rows bind the exact semantic field span, not a document-level surrogate.
- Every admitted product observation has exactly one resolved S7 mapping and exactly one `observation_membership_link` to an X3 membership visible at the same cutoff and valid time. Supporting FX, benchmark, manifest, and policy rows are explicitly inapplicable to membership.
- Null canonical keys never cross-dataset join. The two same-labelled null rows remain separate one-source audit exclusions.
- Existing fixture builders retain their current behavior. New S7 helpers run only through `build_s7_fixture`.
- Use `as_known_bundle`, `make_receipt`, `store_receipt`, and `verify_receipt`; never construct snapshot or receipt rows by hand.
- No alpha, Sharpe, IRR, PME, score, rank, recommendation, performance estimate, or hidden expected label may appear in source payloads or manifest fields. The method-policy statement may name prohibited estimands only to state the refusal boundary.
- The new closure and manifest SHA-256 literals are digest-gate outputs. Do not guess, preselect, or regenerate until a value happens to match. The independent gate records the exact values before they are pinned.
- Run focused tests in the foreground with `uv`; do not run the whole repository suite in one process.
- Commit only explicit paths, without attribution trailers. Do not merge, rebase, push, publish, or alter another worktree from a fixture track.

---

## File ownership

| File | Responsibility |
|---|---|
| `src/quant_allocator/evidence/fixtures/s7.py` | Public contract, scenario/request registry, orchestrator, policy hook, manifest payload/digest, pristine/persisted verifier |
| `src/quant_allocator/evidence/fixtures/public_markets.py` | Additive public-equity, hedge-fund, FX, and benchmark source authoring helpers |
| `src/quant_allocator/evidence/fixtures/credit.py` | Additive monthly-liquid and quarterly-valuation credit source helper |
| `src/quant_allocator/evidence/fixtures/private_markets.py` | Additive irregular cash-flow and versioned-NAV source helper |
| `src/quant_allocator/evidence/fixtures/terms.py` | Additive basis-term, predecessor/team relationship, and method-policy source helper |
| `src/quant_allocator/evidence/fixtures/__init__.py` | Export only the reviewed S7 public API |
| `tests/evidence/test_s7_fixture.py` | Complete fixture, PIT, closure, adversary, determinism, and digest-pin contract |

No other file may be edited. If an implementation appears to require `schema.py`, `model.py`, `ingest.py`, `projections.py`, `snapshot.py`, `lineage.py`, `fixtures/x3.py`, or the E3 bridge, stop and return the exact missing capability to the primary agent.

## Public API and immutable types

`src/quant_allocator/evidence/fixtures/s7.py` owns this exact public surface:

```python
S7_FIXTURE_ID = "s7_evidence_v1"
S7_AUTHORED_CLOSURE_CONTRACT_VERSION = "s7-authored-closure-v1"
S7_SCHEMA_SHA256 = "43a0f22036e3e6b55fc15a05071e58d7771ff5546cedce7c4ee45155f38b0818"
S7_SCENARIOS = ("public-equity", "hedge-fund", "credit", "private-market")
S7_DATASET_IDS = (
    "dataset:s7-public-registered",
    "dataset:s7-hedge-composite",
    "dataset:s7-credit-lineage",
    "dataset:s7-private-cashflow-nav",
    "dataset:s7-fx",
    "dataset:s7-benchmark",
    "dataset:s7-lineage-terms",
    "dataset:s7-method-boundary",
)
S7_CUTOFFS = MappingProxyType(
    {
        "early": X3_CUTOFFS["early"],
        "latest": X3_CUTOFFS["latest"],
    }
)

@dataclass(frozen=True, slots=True)
class S7MethodPolicyEvidence:
    policy_id: str
    dataset_id: str
    payload_schema_id: str
    payload_schema_sha256: str
    item_id: str
    span_id: str
    observation_id: str
    version_id: str
    right_id: str
    snapshot_digest: str
    slice_receipt_id: str
    bundle_digest: str
    join_receipt_id: str
    payload_sha256: str

@dataclass(frozen=True, slots=True)
class S7ScenarioContract:
    scenario: str
    dataset_ids: tuple[str, ...]
    canonical_product_ids: tuple[str, ...]
    source_record_ids: tuple[str, ...]
    mapping_ids: tuple[str, ...]
    membership_ids: tuple[str, ...]
    source_statuses: tuple[tuple[str, str], ...]
    observation_membership_link_ids: tuple[str, ...]
    relationship_ids: tuple[str, ...]
    death_evidence_item_ids: tuple[str, ...]
    death_evidence_span_ids: tuple[str, ...]

@dataclass(frozen=True, slots=True)
class S7BundleContract:
    scenario: str
    cutoff_name: str
    analytic_slice_digests: tuple[tuple[str, str], ...]
    audit_slice_digests: tuple[tuple[str, str], ...]
    analytic_slice_receipt_ids: tuple[tuple[str, str], ...]
    audit_slice_receipt_ids: tuple[tuple[str, str], ...]
    analytic_bundle_digest: str
    audit_bundle_digest: str
    analytic_join_receipt_id: str
    audit_join_receipt_id: str

@dataclass(frozen=True, slots=True)
class S7FixtureManifest:
    fixture_id: str
    fixture_digest: str
    closure_digest: str
    schema_version: int
    schema_digest: str
    x3_fixture_digest: str
    dataset_ids: tuple[str, ...]
    payload_schema_digests: tuple[tuple[str, str], ...]
    source_record_records: tuple[tuple[object, ...], ...]
    item_records: tuple[tuple[object, ...], ...]
    span_records: tuple[tuple[object, ...], ...]
    right_records: tuple[tuple[object, ...], ...]
    version_records: tuple[tuple[object, ...], ...]
    partition_records: tuple[tuple[object, ...], ...]
    observation_records: tuple[tuple[object, ...], ...]
    mapping_records: tuple[tuple[object, ...], ...]
    observation_membership_link_records: tuple[tuple[object, ...], ...]
    relationship_records: tuple[tuple[object, ...], ...]
    receipt_ids: tuple[str, ...]
    scenario_contracts: tuple[S7ScenarioContract, ...]
    bundle_contracts: tuple[S7BundleContract, ...]
    policy: S7MethodPolicyEvidence
    limitation_codes: tuple[str, ...]

def build_s7_fixture(conn: sqlite3.Connection) -> S7FixtureManifest: ...
def verify_s7_manifest(conn: sqlite3.Connection, manifest: S7FixtureManifest) -> bool: ...
def s7_manifest_payload(manifest: S7FixtureManifest) -> dict[str, object]: ...
def s7_manifest_digest(manifest: S7FixtureManifest) -> str: ...
def s7_authored_closure_digest(conn: sqlite3.Connection) -> str: ...
def s7_source_requests(
    manifest: S7FixtureManifest,
    *,
    scenario: str,
    cutoff_name: str,
    revision_mode: str,
) -> tuple[DatasetSliceRequest, ...]: ...
def s7_policy_bundle(
    conn: sqlite3.Connection, manifest: S7FixtureManifest
) -> SnapshotBundle: ...
```

`revision_mode` accepts exactly `latest-known | all-known-versions`; unknown scenarios, cutoffs, or modes raise `ValueError` before a request is built. Public exports in `fixtures/__init__.py` are limited to these constants, dataclasses, and functions.

## Exact dataset, right, and purpose inventory

| Dataset ID | Module | Access context | Licence purpose | Availability | Required record kinds |
|---|---|---|---|---|---|
| `dataset:s7-public-registered` | `public_markets.py` | `public` | `s7-research` | `public-publication` | `s7-periodic-return` |
| `dataset:s7-hedge-composite` | `public_markets.py` | `shortlisted-nda` | `s7-research` | `manager-receipt` | `s7-periodic-return` |
| `dataset:s7-credit-lineage` | `credit.py` | `segregated-mandate` | `s7-research` | `manager-receipt` | `s7-credit-return` |
| `dataset:s7-private-cashflow-nav` | `private_markets.py` | `funded-private-partnership` | `s7-research` | `manager-receipt` | `s7-private-cashflow`, `s7-private-nav` |
| `dataset:s7-fx` | `public_markets.py` | `public` | `s7-research` | `public-publication` | `s7-fx-return` |
| `dataset:s7-benchmark` | `public_markets.py` | `public` | `s7-research` | `public-publication` | `s7-benchmark-return` |
| `dataset:s7-lineage-terms` | `terms.py` | `shortlisted-nda` | `s7-research` | `manager-receipt` | `s7-basis-term`, `s7-relationship-evidence`, `s7-death-evidence` |
| `dataset:s7-method-boundary` | `terms.py` | `public` | `s7-research` | `public-publication` | `s7-method-policy` |

Each dataset has one stable `right-series:<dataset slug>`, right version `1`, active status, `retain-after-expiry`, and entitlement beginning `2024-01-01T00:00:00Z`. A positive scenario uses only the access context in this table; alternative contexts are refusal tests, not duplicate positive fixtures.

## Strict record-kind schemas and spans

Every schema ID ends in `-v1`, lists every field below in `required`, sets each field to JSON `string`, sets `additionalProperties: false`, and stores `sha256(canonical_bytes(schema))`.

| Schema ID | Exact required fields |
|---|---|
| `schema:s7-periodic-return-v1` | `source_product_key`, `period_end`, `return_value`, `return_kind`, `gross_net`, `currency`, `frequency`, `calendar`, `management_fee_basis`, `incentive_fee_basis`, `benchmark_id`, `benchmark_version`, `benchmark_convention`, `valuation_policy_id`, `cashflow_convention` |
| `schema:s7-credit-return-v1` | periodic-return fields plus `income_treatment`, `price_treatment`, `default_recovery_treatment`, `cash_treatment`, `duration_convention` |
| `schema:s7-private-cashflow-v1` | `source_product_key`, `event_id`, `event_date`, `event_kind`, `amount`, `currency`, `recallable`, `fee_expense_treatment`, `cashflow_convention` |
| `schema:s7-private-nav-v1` | `source_product_key`, `valuation_date`, `nav`, `currency`, `valuation_policy_id`, `published_at`, `frequency`, `calendar` |
| `schema:s7-fx-return-v1` | `series_id`, `period_end`, `fx_return`, `base_currency`, `quote_currency`, `quotation_direction`, `hedge_treatment`, `rule_id` |
| `schema:s7-benchmark-return-v1` | `benchmark_id`, `benchmark_version`, `period_end`, `return_value`, `return_convention`, `currency`, `frequency`, `calendar` |
| `schema:s7-basis-term-v1` | `term_id`, `source_product_key`, `effective_from`, `effective_to`, `term_kind`, `value`, `unit`, `scope` |
| `schema:s7-relationship-evidence-v1` | `relationship_key`, `relation_type`, `source_entity_id`, `target_entity_id`, `effective_from`, `effective_to`, `assertion`, `scope` |
| `schema:s7-death-evidence-v1` | `finding_type`, `source_record_key`, `canonical_product_id`, `effective_at`, `first_known_at`, `affected_observation_ids`, `reason_code` |
| `schema:s7-method-policy-v1` | `policy_id`, `output_pointer`, `statement`, `prohibited_outputs` |

For every item, render `canonical_bytes(payload).decode()` and create exactly one span for each `/<field>` over the encoded field value. The relationship edge uses the `/assertion` span; the policy hook uses the `/statement` span. Tests recompute offsets, bytes, hashes, and `machine_id("span", ...)` rather than trusting authored coordinates.

## Four scenario source shapes

| Scenario | Exact source components | Canonical X3 grain | Positive output kind |
|---|---|---|---|
| `public-equity` | registered share-class return, public FX, versioned benchmark | `vehicle` | total/excess return lineage |
| `hedge-fund` | manager composite return plus fee and team/predecessor evidence | `composite` | net-return lineage |
| `credit` | monthly liquid-credit and quarterly valuation-based credit rows | `strategy` | separate native-frequency panels; cross-frequency refusal |
| `private-market` | irregular calls/distributions and quarterly NAV versions | `vehicle` | cash-flow/NAV lineage only |

Source share-class, mandate, sleeve, feeder, and LP-interest keys map to the existing X3 `vehicle`, `composite`, or `strategy` grain; they do not create a new canonical product type. The only new canonical entities are two fictional people used for team chronology. Product/adviser/legal/composite/vehicle closure comes from the verified X3 relationship projection.

## Authored PIT and refusal matrix

The builders use stable source keys and the exact planted behavior below. Decimal strings are illustrative source facts, not estimator outputs.

| Case | Stable source key(s) | Exact authored behavior |
|---|---|---|
| S7-L1 and S7-L2 | `s7-hf-main:2024-02` | version 1 net return `0.0100`, received before early; child version 2 `0.0080`, received before latest |
| S7-L3 | `s7-hf-closed:2023-12`, `s7-hf-death-evidence` | return row absent from the early full snapshot and present in the latest complete version; X3 status remains exactly `closed`, while a separate S7 `later-dead-product` item/span first known before the latest cutoff supports the latest dead audit label without rewriting the early denominator |
| S7-L4 | `s7-hf-not-inferable` | omitted from a complete full snapshot whose absence semantics are `not-inferable` |
| S7-L5 | `s7-hf-inherited` | present in base full snapshot, omitted from complete delta, inherited by reconstruction |
| S7-L6 | `s7-hf-tombstoned` | present in base, then `explicitly-removed` by complete delta at latest availability |
| S7-L7 | `s7-hf-retro-member` | economic effective date precedes the X3 membership's first-known date; early audit cannot see it, latest audit can |
| S7-L8 | `s7-hf-ambiguous` | one row with two candidate X3 IDs and `mapping_status="ambiguous"` |
| S7-L8a | `s7-null-same-label` in public and hedge datasets | identical source label and date, two separate unresolved mappings, no canonical ID, no cross-dataset joined row |
| S7-L9 | `s7-hf-overlap` | two S7 relationship intervals own the same instant for one product |
| S7-L10 and S7-L11 | `s7-hf-gross-break`, `s7-hf-fee-unresolved` | gross-to-net hard break; separate net row with missing fee basis represented by empty string and refused |
| S7-L12 and S7-L13 | `s7-public-eur`, `s7-fx-eur-usd:2024-02` | missing-FX refusal plus FX version 1 `0.0200` and child version 2 `0.0180` |
| S7-L14 | `s7-public-benchmark-v1`, `s7-public-benchmark-v2` | same benchmark label, distinct exact benchmark versions |
| S7-L15 | `s7-credit-liquid`, `s7-credit-private` | monthly total-return row versus quarterly valuation-based row; no interpolation |
| S7-L16 | `s7-private-nav:2024-03-31` | NAV version 1 `85000000.00`, child version 2 `80000000.00`; early/latest values diverge |
| S7-L17 | `s7-predecessor-unsourced` | matching display label but no `predecessor_claim` relationship edge |
| S7-L18 | `s7-team-partial` | employment overlap exists but no `transfer_scope` edge for the claimed strategy |
| S7-L19 | `s7-team-boundary` | predecessor employment ends exactly `2024-01-01T00:00:00Z`, the new segment start |
| S7-L20 | X3 snapshot memberships | fixture exposes only membership IDs derived from visible X3 slices; no present-day roster tuple exists |
| S7-L21 | `s7-hf-ambiguous` exclusion | exact mapping, observation, source, span, and refusal references are available for omission-tamper tests |
| S7-L22 | all S7 rows | canonical sort and machine IDs make reversed module and insertion order byte-identical |
| S7-L23 | every source item | persisted payload/content-hash mutation makes `verify_s7_manifest` return false |
| S7-L24 | `s7-public-no-archive` | exact current lineage exists, but no archived/dead-product scope is authored |

The private fixture also includes one capital call, one distribution, one fee/expense event, and one NAV at irregular dates. The public and hedge fixtures each include at least three monthly rows so segment ordering and row reconciliation are non-vacuous.

## X3 membership and observation-link closure

`build_s7_fixture` builds and verifies X3 first, requests the exact X3 source slices at `S7_CUTOFFS`, and uses only `project_entity_mappings`, `project_universe_memberships`, `project_entity_relationships`, and `require_member`. For each S7 product observation:

1. create one S7 mapping tied to that exact item/span/version/observation;
2. resolve its canonical ID to an X3 membership visible in the selected X3 slice;
3. require matching canonical entity and valid half-open interval, and copy X3 `source_status` without normalization as exactly one of `active | inactive | closed | unknown`;
4. create `observation_membership_link` with `machine_id("observation-membership", {"dataset_observation_id": observation_id, "universe_membership_id": membership_id})`;
5. record the exact IDs in the scenario manifest.

Ambiguous, unresolved, and future membership rows have no positive link and are listed as typed exclusions. `closed` may link as historical membership but remains visibly `closed`; `unknown` remains `unknown` and cannot support a complete-denominator claim. A dead label is produced only when the separate S7 death item, exact span, affected observations, canonical product, effective time, first-known time, and receipt all verify at the cutoff. Tests assert zero duplicate links, zero cross-product links, no closed-to-dead status mutation, and that every admitted observation has cardinality exactly one.

`membership_ids` preserve the substrate row identities used by `observation_membership_link`; `source_statuses` come from the final reviewed X3 source-status contract. S7 never exposes the substrate table's historical `membership_status` token as `source_status`, and no table token may silently upgrade `closed` to a dead label.

## Relationship and team chronology

`dataset:s7-lineage-terms` authors one exact item/span per edge, following the merged E3 bridge's provenance pattern without importing E3 content or IDs. It adds two fictional people and these controlled edges:

```text
employed_by(person:s7-lead, manager:x3-01, [2020-01-01, 2024-01-01))
employed_by(person:s7-lead, manager:x3-00, [2024-01-01, open))
employed_by(person:s7-support, manager:x3-01, [2020-01-01, open))
predecessor_claim(manager:x3-01, manager:x3-00, point 2024-01-01)
transfer_scope(person:s7-support, strategy:x3-04, [2023-01-01, open))
contradicts_transfer(person:s7-support, strategy:x3-05, point 2024-06-01)
```

The partial-support case intentionally has employment but no transfer-scope edge. Each relationship row carries its S7 item, exact `/assertion` span, dataset version, and observation. X3-owned product/adviser/legal relationships remain unchanged and are referenced from X3 slices.

## Exact method-policy evidence

The policy payload is exactly:

```python
{
    "policy_id": "s7-method-boundary/v1",
    "output_pointer": "/refusals/performance-estimator",
    "statement": (
        "S7 reconstructs lineage and basis-qualified panels; it does not estimate "
        "alpha, Sharpe, IRR, PME, skill, or manager ranking."
    ),
    "prohibited_outputs": "alpha|sharpe|irr|pme|skill|manager-ranking",
}
```

It is the sole non-manifest item in a complete, one-source, public, full-snapshot policy dataset. `build_s7_fixture` calls `as_known_bundle` with one policy request, join keys `("evidence_item_id",)`, join policy `s7-method-policy-v1`, and latest cutoff. `S7MethodPolicyEvidence` binds the exact item, `/statement` span, observation, version, right, snapshot digest, slice receipt, bundle digest, join receipt, schema digest, and payload digest. `s7_policy_bundle` reconstructs that bundle from the manifest and refuses any mismatch.

---

### Task 0: Dependency and ownership docket

**Files:** None.

**Interfaces:**
- Consumes: reviewed main, evidence, access, E3, X3 fixture, and final X3 implementation tips.
- Produces: a recorded go/no-go docket; no code or commit.

- [ ] Record these exact minimum dependencies: main `60bdccb9ab9a110c6b9aa43191054ad111a133e5`; evidence merge `d66bfde`; schema implementation `2c3365307874fb6a858e53ea53d21c8a91e305ab`; E3 bridge `43b3650bb9f0edab82d4002d2194eafdfd176bd3`; X3 fixture closure `89f05d7c3705870f0024501af43cfc4b647536a7` merged at `b748ea7`; access seam `1ff72ec3c2f3eeb19af65294bd559671e400c167`; final reviewed X3 implementation `d7b2e794367acd5a5b2573e4f7e7a20493326a37`, merged at `a3713fcf83ed026f71bffe710d1804ab6418dbc0`.
- [ ] Require the primary agent to record an unconditional independent PASS for `d7b2e79` and prove merge `a3713fc` is an ancestor of the fixture implementation branch. If that review or ancestry is absent, conditional, superseded, or has an open Important/Critical finding, stop.
- [ ] Verify `verify_x3_manifest` passes on a pristine connection at the recorded final tip and record `X3_AUTHORED_MANIFEST_SHA256`, `X3_AUTHORED_CLOSURE_SHA256`, and `X3_AUTHORED_SCHEMA_SHA256` from that tip.
- [ ] Confirm the assigned branch/worktree and the exact seven-file ownership list above. Stop if any owned file has unrelated changes.
- [ ] Confirm `tools/.publication_terms` exists in the checkout used for eventual publication checks; do not print its contents.

Run:

```bash
git merge-base --is-ancestor 60bdccb HEAD
git merge-base --is-ancestor 1ff72ec HEAD
git merge-base --is-ancestor d7b2e79 HEAD
git merge-base --is-ancestor a3713fc HEAD
git status --short
```

Expected: all four ancestor checks return zero, the X3 commit exists, and the owned paths are clean. No commit.

---

### Task 1: Pin the public contract and failing fixture boundary

**Files:**
- Create: `src/quant_allocator/evidence/fixtures/s7.py`
- Modify: `src/quant_allocator/evidence/fixtures/__init__.py`
- Create: `tests/evidence/test_s7_fixture.py`

**Interfaces:**
- Consumes: constants and X3 APIs named above.
- Produces: the exact constants, dataclasses, validation-only request registry, and function signatures in **Public API and immutable types**.

- [ ] Add a failing test importing every public symbol and asserting the exact four scenarios, eight datasets, two cutoffs, function signatures, and frozen+slotted dataclasses.

```python
def test_s7_public_contract_is_exact_and_closed() -> None:
    assert S7_FIXTURE_ID == "s7_evidence_v1"
    assert S7_SCENARIOS == ("public-equity", "hedge-fund", "credit", "private-market")
    assert tuple(S7_CUTOFFS) == ("early", "latest")
    assert set(S7_DATASET_IDS) == EXPECTED_EIGHT_DATASETS
    assert fields(S7MethodPolicyEvidence)[0].name == "policy_id"
    assert S7FixtureManifest.__dataclass_params__.frozen is True
```

- [ ] Run the single test and confirm RED because `fixtures.s7` does not exist:

```bash
uv run pytest tests/evidence/test_s7_fixture.py::test_s7_public_contract_is_exact_and_closed -q
```

- [ ] Add the exact constants, dataclasses, dataset/request registry, validators, and public exports. Function bodies that depend on authored rows must raise `RuntimeError("s7-fixture-not-built")`; no empty successful manifest is allowed.
- [ ] Re-run the public-contract test and add tests that dataclass equality is insertion-order independent for tuple-sorted fields.
- [ ] Run focused tests and Ruff:

```bash
uv run pytest tests/evidence/test_s7_fixture.py -k 'public_contract or immutable' -q
uv run ruff check src/quant_allocator/evidence/fixtures/s7.py src/quant_allocator/evidence/fixtures/__init__.py tests/evidence/test_s7_fixture.py
git diff --check
```

- [ ] Review the diff and commit only these paths:

```bash
git add src/quant_allocator/evidence/fixtures/s7.py src/quant_allocator/evidence/fixtures/__init__.py tests/evidence/test_s7_fixture.py
git commit -m "feat(evidence): define s7 fixture contract"
```

---

### Task 2: Author strict schemas and the method-policy bundle

**Files:**
- Modify: `src/quant_allocator/evidence/fixtures/s7.py`
- Modify: `src/quant_allocator/evidence/fixtures/terms.py`
- Test: `tests/evidence/test_s7_fixture.py`

**Interfaces:**
- Consumes: `S7MethodPolicyEvidence`, shared ingest/snapshot APIs.
- Produces: `build_s7_terms_sources(conn)`, strict basis/relationship/policy schemas, and `s7_policy_bundle`.

- [ ] Write failing tests that require the exact three terms-module datasets, schemas, complete policy version/partition/observation, one policy item, exact `/statement` span, separately receipted `s7-death-evidence`, and shared-verifier-valid slice/join receipts.
- [ ] Add independent substitution tests for policy item, span, observation, version, right, snapshot, slice receipt, bundle digest, join receipt, schema digest, payload digest, and output pointer.
- [ ] Run the policy tests and confirm RED because the datasets and policy hook are absent:

```bash
uv run pytest tests/evidence/test_s7_fixture.py -k 'policy or terms_schema' -q
```

- [ ] Implement `build_s7_terms_sources(conn)` idempotently. Use the exact inventory, schemas, payload, relationships, and spans above; ingest through shared functions and call `as_known_bundle` for policy receipts.
- [ ] Implement `s7_policy_bundle` by rebuilding the exact request and comparing every `S7MethodPolicyEvidence` field before returning the bundle.
- [ ] Require all relationship items to carry exact item/span/version/observation closure; duplicate relationship identity or unsupported endpoint refuses during construction.
- [ ] Run focused tests, the adjacent E3 bridge test that protects the shared relationship pattern, and Ruff:

```bash
uv run pytest tests/evidence/test_s7_fixture.py -k 'policy or terms_schema or relationship' -q
uv run pytest tests/flagships/test_knowledge_evidence_bridge.py -q
uv run ruff check src/quant_allocator/evidence/fixtures/s7.py src/quant_allocator/evidence/fixtures/terms.py tests/evidence/test_s7_fixture.py
git diff --check
```

- [ ] Commit:

```bash
git add src/quant_allocator/evidence/fixtures/s7.py src/quant_allocator/evidence/fixtures/terms.py tests/evidence/test_s7_fixture.py
git commit -m "feat(evidence): author s7 policy and lineage terms"
```

---

### Task 3: Author public, hedge, FX, and benchmark PIT sources

**Files:**
- Modify: `src/quant_allocator/evidence/fixtures/public_markets.py`
- Modify: `src/quant_allocator/evidence/fixtures/s7.py`
- Test: `tests/evidence/test_s7_fixture.py`

**Interfaces:**
- Consumes: strict schema/span helper from `s7.py`, X3 cutoffs.
- Produces: `build_s7_public_market_sources(conn)` and the public/hedge/FX/benchmark source closure.

- [ ] Write failing tests for the exact four datasets, rights, schemas, source keys, at least three monthly rows per positive series, and S7-L1 through L14 plus L24 source facts.
- [ ] Require early/latest actual values for the return and FX revisions, inherited delta omission, explicit tombstone, not-inferable absence, closed-product backfill, separately receipted S7 death evidence, same-label null rows, fee break, missing fee basis, and benchmark-version mismatch.
- [ ] Confirm RED:

```bash
uv run pytest tests/evidence/test_s7_fixture.py -k 'public_source or hedge_source or fx or benchmark or l1 or l14 or l24' -q
```

- [ ] Implement `build_s7_public_market_sources(conn)` without changing `build_public_markets_fixture`. Ingest full/delta versions, complete partition manifests, observations, reconstruction lineage, strict spans, and authored revision chains exactly as specified.
- [ ] Ensure early and latest use source availability rather than caller-authored flags. Delta omission inherits `s7-hf-inherited`; tombstone removes only `s7-hf-tombstoned`.
- [ ] Run focused and adjacent delivery tests:

```bash
uv run pytest tests/evidence/test_s7_fixture.py -k 'public or hedge or fx or benchmark or delta or tombstone or absence' -q
uv run pytest tests/evidence/test_fixtures.py tests/evidence/test_snapshot.py tests/evidence/test_lineage.py -m "not slow and not network" -q
uv run ruff check src/quant_allocator/evidence/fixtures/public_markets.py src/quant_allocator/evidence/fixtures/s7.py tests/evidence/test_s7_fixture.py
git diff --check
```

- [ ] Commit:

```bash
git add src/quant_allocator/evidence/fixtures/public_markets.py src/quant_allocator/evidence/fixtures/s7.py tests/evidence/test_s7_fixture.py
git commit -m "feat(evidence): author s7 liquid PIT sources"
```

---

### Task 4: Author credit and private-market native sources

**Files:**
- Modify: `src/quant_allocator/evidence/fixtures/credit.py`
- Modify: `src/quant_allocator/evidence/fixtures/private_markets.py`
- Modify: `src/quant_allocator/evidence/fixtures/s7.py`
- Test: `tests/evidence/test_s7_fixture.py`

**Interfaces:**
- Consumes: strict schema/span helper and scenario registry.
- Produces: `build_s7_credit_sources(conn)` and `build_s7_private_market_sources(conn)`.

- [ ] Write failing tests for exact rights/schemas and the monthly liquid-credit versus quarterly valuation-based row. Assert native dates/frequencies survive and no interpolated month is authored.
- [ ] Write failing tests for one call, distribution, fee/expense event, quarterly NAV, NAV child revision, irregular event dates, and actual `85000000.00 -> 80000000.00` early/latest divergence.
- [ ] Confirm RED:

```bash
uv run pytest tests/evidence/test_s7_fixture.py -k 'credit or private or l15 or l16' -q
```

- [ ] Implement both additive builders with strict payload schemas, item revisions, complete versions/partitions/observations, canonical spans, and no monthly return derivation for private rows.
- [ ] Prove the existing `build_credit_fixture` and `build_private_markets_fixture` outputs remain byte-identical when the new S7 helpers are not called.
- [ ] Run focused and adjacent tests:

```bash
uv run pytest tests/evidence/test_s7_fixture.py -k 'credit or private or native_frequency or nav_revision' -q
uv run pytest tests/evidence/test_fixtures.py -q
uv run ruff check src/quant_allocator/evidence/fixtures/credit.py src/quant_allocator/evidence/fixtures/private_markets.py src/quant_allocator/evidence/fixtures/s7.py tests/evidence/test_s7_fixture.py
git diff --check
```

- [ ] Commit:

```bash
git add src/quant_allocator/evidence/fixtures/credit.py src/quant_allocator/evidence/fixtures/private_markets.py src/quant_allocator/evidence/fixtures/s7.py tests/evidence/test_s7_fixture.py
git commit -m "feat(evidence): author s7 native credit and private sources"
```

---

### Task 5: Close X3 mappings, memberships, observation links, and relationships

**Files:**
- Modify: `src/quant_allocator/evidence/fixtures/s7.py`
- Modify: `src/quant_allocator/evidence/fixtures/terms.py`
- Test: `tests/evidence/test_s7_fixture.py`

**Interfaces:**
- Consumes: final X3 manifest, source observations from Tasks 2-4.
- Produces: exact S7 mapping/link/relationship IDs and complete `S7ScenarioContract` values.

- [ ] Write failing tests that `build_x3_fixture` and `verify_x3_manifest` pass before S7 construction, then require one mapping and one observation-membership link for every admitted product observation.
- [ ] Add adversaries for future membership, wrong canonical product, wrong cutoff, cross-observation link, duplicate link, ambiguous mapping, mutation of X3 `closed` to `dead`, missing/swapped S7 death item or span, death evidence before `first_known_at`, and caller-supplied current roster.
- [ ] Add tests for all six team relationships, half-open employment boundary, absent predecessor edge, partial-support missing scope, exact support, and sourced contradiction.
- [ ] Confirm RED:

```bash
uv run pytest tests/evidence/test_s7_fixture.py -k 'x3 or membership or observation_link or team or predecessor' -q
```

- [ ] Implement mapping and link construction only from exact X3 projected rows. Use `require_member` for product/cutoff/valid-time equality and record every excluded row without inventing a fabricated link.
- [ ] Add the two person entities and S7-sourced relationship rows. Do not alter or copy X3/E3 rows.
- [ ] Re-run `verify_x3_manifest` after all S7 rows are present and require the original X3 fixture dataclass, closure digest, manifest digest, receipt set, mapping records, and relationship records to remain exact.
- [ ] Run focused X3/S7 tests and Ruff:

```bash
uv run pytest tests/evidence/test_s7_fixture.py -k 'x3 or mapping or membership or observation_link or relationship or team' -q
uv run pytest tests/evidence/test_x3_fixture.py -m "not slow and not network" -q
uv run ruff check src/quant_allocator/evidence/fixtures/s7.py src/quant_allocator/evidence/fixtures/terms.py tests/evidence/test_s7_fixture.py
git diff --check
```

- [ ] Commit:

```bash
git add src/quant_allocator/evidence/fixtures/s7.py src/quant_allocator/evidence/fixtures/terms.py tests/evidence/test_s7_fixture.py
git commit -m "feat(evidence): link s7 sources to reviewed membership"
```

---

### Task 6: Build paired bundles and authoritative manifest closure

**Files:**
- Modify: `src/quant_allocator/evidence/fixtures/s7.py`
- Modify: `src/quant_allocator/evidence/fixtures/__init__.py`
- Test: `tests/evidence/test_s7_fixture.py`

**Interfaces:**
- Consumes: all eight datasets and typed projections.
- Produces: complete `build_s7_fixture`, requests, paired bundle contracts, manifest payload/digest, closure digest, and persisted/pristine verifier.

- [ ] Write failing tests for all eight scenario/cutoff analytic/audit pairs. Requests must have identical source scope, rights, purposes, valid-time settings, join keys, and policy; only `revision_mode` differs. Unknown scenario, cutoff, and revision-mode inputs must raise their exact `s7-unknown-*` `ValueError` before request construction. The built manifest must satisfy `manifest.schema_version == SCHEMA_VERSION == 1` and `type(manifest.schema_version) is int`.
- [ ] Require every slice/join receipt to pass `verify_receipt`; require early/latest actual source values, not only counts or IDs.
- [ ] Write persisted mutation tests for every authored table class: dataset, schema, source, item/payload, span, right, version, partition, observation, observation-partition link, mapping, membership link, relationship, snapshot manifest, receipt header/reference/seal, bundle manifest.
- [ ] Write pristine rebuild, second-build idempotence, reversed module order, reversed insertion order, and tuple-order normalization tests. All manifests, closure bytes, bundle digests, receipt IDs, and policy handles must match exactly.
- [ ] Confirm RED:

```bash
uv run pytest tests/evidence/test_s7_fixture.py -k 'bundle or manifest or pristine or persisted or reversed or idempotent' -q
```

- [ ] Implement `build_s7_fixture` in a transaction: verify X3, invoke the four additive builders in canonical order, build mappings/links/relationships, materialize paired bundles and policy bundle, form sorted manifest records, compute digests, verify, then commit. Roll back on any failure.
- [ ] Implement `s7_authored_closure_digest` from named canonical SQL inventories restricted to S7 rows plus S7 observation links and S7-sourced relationships/receipts. Include every persisted field and receipt reference/seal row.
- [ ] Implement `verify_s7_manifest` without trusting the supplied dataclass: rebuild a pristine fixture in an isolated in-memory connection, compare canonical persisted inventories and receipt sets, recompute all digests, rerun `verify_x3_manifest`, and return `False` on evidence refusal, SQL error, key/type/value error, or assertion failure.
- [ ] Run the full focused fixture file and bounded adjacent evidence tests:

```bash
uv run pytest tests/evidence/test_s7_fixture.py -q
uv run pytest tests/evidence/test_fixtures.py tests/evidence/test_snapshot.py tests/evidence/test_lineage.py tests/evidence/test_projections.py tests/evidence/test_universe.py -m "not slow and not network" -q
uv run ruff check src/quant_allocator/evidence/fixtures/s7.py src/quant_allocator/evidence/fixtures/public_markets.py src/quant_allocator/evidence/fixtures/credit.py src/quant_allocator/evidence/fixtures/private_markets.py src/quant_allocator/evidence/fixtures/terms.py src/quant_allocator/evidence/fixtures/__init__.py tests/evidence/test_s7_fixture.py
git diff --check
```

- [ ] Commit the unpinned but fully recomputable closure implementation:

```bash
git add src/quant_allocator/evidence/fixtures/s7.py src/quant_allocator/evidence/fixtures/__init__.py tests/evidence/test_s7_fixture.py
git commit -m "feat(evidence): close s7 authored fixture manifest"
```

---

### Task 7: Independent digest gate and literal pins

**Files:**
- Modify: `src/quant_allocator/evidence/fixtures/s7.py`
- Test: `tests/evidence/test_s7_fixture.py`

**Interfaces:**
- Consumes: Task-6 reviewed fixture bytes.
- Produces: independently reviewed `S7_AUTHORED_CLOSURE_SHA256` and `S7_AUTHORED_MANIFEST_SHA256` literals; schema literal remains `S7_SCHEMA_SHA256` above.

- [ ] Primary agent builds a pristine fixture twice and records the two closure and manifest digests plus exact row/receipt counts:

```bash
PYTHONPATH=src uv run python - <<'PY'
from quant_allocator.evidence.fixtures.s7 import build_s7_fixture, s7_authored_closure_digest
from quant_allocator.evidence.schema import connect, initialize
for _ in range(2):
    conn = connect(); initialize(conn)
    manifest = build_s7_fixture(conn)
    print(manifest.fixture_digest, s7_authored_closure_digest(conn))
PY
```

Expected: both lines are byte-identical; each field is lowercase 64-hex. The values are review evidence, not yet authority.

- [ ] An independent reviewer re-derives canonical payload bytes and both SHA-256 values from the persisted SQL inventory without calling `s7_manifest_digest` or `s7_authored_closure_digest`. Any mismatch returns to Task 6.
- [ ] Only after independent equality, copy the two exact reviewed outputs into constants named `S7_AUTHORED_MANIFEST_SHA256` and `S7_AUTHORED_CLOSURE_SHA256`; add tests requiring exact literals, pristine equality, and refusal after one-field mutation followed by a self-consistent dataclass rehash.
- [ ] Require the review docket to record literal values, fixture row counts, receipt counts, the exact Task-6 tip, reviewer identity, commands, and PASS verdict. A missing docket entry blocks commit.
- [ ] Run all focused tests and Ruff:

```bash
uv run pytest tests/evidence/test_s7_fixture.py -q
uv run ruff check src/quant_allocator/evidence/fixtures/s7.py tests/evidence/test_s7_fixture.py
git diff --check
```

- [ ] Commit only reviewed literals and their assertions:

```bash
git add src/quant_allocator/evidence/fixtures/s7.py tests/evidence/test_s7_fixture.py
git commit -m "test(evidence): pin s7 authored fixture closure"
```

---

### Task 8: Final no-estimator and handoff gate

**Files:**
- Test: `tests/evidence/test_s7_fixture.py`
- No production edit unless a focused test exposes a defect in an owned file.

**Interfaces:**
- Consumes: reviewed pinned fixture tip.
- Produces: implementation-ready S7 prerequisite docket and independent review package.

- [ ] Add recursive source-payload/manifest-key tests rejecting `alpha`, `sharpe`, `irr`, `pme`, `skill`, `score`, `rank`, `recommendation`, and hidden expected-label keys everywhere except the exact policy `statement` and `prohibited_outputs` fields.
- [ ] Assert four scenarios, eight datasets, two cutoffs, both revision modes, every S7-L1 through S7-L24 planted fact, and all policy references are covered by named tests.
- [ ] Run final bounded verification:

```bash
uv run pytest tests/evidence/test_s7_fixture.py -q
uv run pytest tests/evidence/test_fixtures.py tests/evidence/test_snapshot.py tests/evidence/test_lineage.py tests/evidence/test_projections.py tests/evidence/test_universe.py tests/evidence/test_x3_fixture.py tests/flagships/test_knowledge_evidence_bridge.py -m "not slow and not network" -q
uv run ruff check src/quant_allocator/evidence/fixtures/s7.py src/quant_allocator/evidence/fixtures/public_markets.py src/quant_allocator/evidence/fixtures/credit.py src/quant_allocator/evidence/fixtures/private_markets.py src/quant_allocator/evidence/fixtures/terms.py src/quant_allocator/evidence/fixtures/__init__.py tests/evidence/test_s7_fixture.py
git diff --check
```

- [ ] Run the required case-insensitive word-boundary publication scan using the ignored `tools/.publication_terms`; require zero disallowed endpoint/range matches, zero commit-message matches, and zero attribution trailers.
- [ ] Confirm the exact implementation range changes only the seven owned files and the worktree is clean.
- [ ] Produce this exact handoff docket:

```text
reviewed_main_tip
reviewed_evidence_tip and schema version/digest
reviewed_e3_bridge_tip
reviewed_x3_fixture_tip, final X3 implementation tip, X3 merge tip, ancestor proof, and unconditional review verdict
S7 fixture tip and commit range
S7 fixture ID, closure contract version, schema/manifest/closure digests
eight dataset IDs; every right ID/context/purpose
every payload schema ID/digest and exact field dictionary
version/partition/reconstruction records per dataset
four scenario contracts with product/mapping/membership/link/relationship IDs, exact X3 source statuses, and separate S7 death-evidence item/span IDs
eight analytic and eight audit bundle contracts
method-policy item/span/observation/version/right/snapshot/slice/bundle/join IDs
row and receipt counts by type
S7-L1 through S7-L24 test names and outcomes
pristine, persisted-tamper, idempotence, reversed-order, X3 non-drift outcomes
focused pytest and Ruff results
publication, trailer, diff-scope, and clean-status results
deviations and unresolved items (must be empty for PASS)
```

- [ ] Dispatch an independent adversarial reviewer. It must return unconditional **spec compliance PASS** and **code quality PASS**, independently recheck membership/product/cutoff equality and digest pins, and identify zero Critical/Important findings before S7 Task 0 may close.
- [ ] If the no-estimator test was the only addition, commit it separately:

```bash
git add tests/evidence/test_s7_fixture.py
git commit -m "test(evidence): close s7 fixture prerequisite gate"
```

Do not merge from the fixture track. The primary agent merges only the independently reviewed tip, records the handoff docket in the campaign ledger, and then authorizes S7 implementation Task 0.
