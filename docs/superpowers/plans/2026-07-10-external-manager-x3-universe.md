# X3 · Manager-universe and sourcing-funnel coverage map — implementation plan

> **For track implementers:** execute this plan task by task in the assigned
> worktree. Act only on the dispatch and the files listed here. Do not create a
> worktree, edit shared seams, publish, or make an unreviewed numerical-policy
> decision.

**Status:** implementation-ready only after the evidence-substrate contract and
this card's independent method review pass.

**Campaign dependency:**
`docs/superpowers/plans/2026-07-10-external-manager-roadmap-implementation.md`.
The campaign plan controls if this plan conflicts with it. The future X3 method
spec's section 8 rulings will control if sections 1–7 of that spec conflict.

**Goal:** ship a deterministic discovery exhibit that answers which
manager/strategy/product/geography/vehicle cells are visible in each named,
point-in-time source and internal funnel stage, then emits an auditable sourcing
work queue. X3 measures source-conditioned and policy-grid coverage. It does not
estimate the number of managers in the world and does not rank manager quality.

**Architecture:** X3 consumes reviewed per-dataset bitemporal snapshot bundles,
shared evidence projections, typed references, and reconstruction receipts. It
adds only a pure `universe_coverage` method package, card-local hidden truth labels,
a deterministic generator over shared synthetic evidence fixtures, held JSON, one
server-rendered page, and a small JavaScript state switcher. Entity mappings,
canonical relationships, universe memberships, target-grid versions, opportunity
definitions, funnel schemas containing transition/reason dictionaries, cohort
policies and evaluations/memberships, and funnel events are
shared point-in-time evidence projections; X3 neither stores nor re-resolves them.
JavaScript selects among precomputed states; it never resolves entities, computes
coverage, estimates conversion, or ranks a cell.

**Tech stack:** Python 3.11+ · stdlib dataclasses/enums · the shared stdlib
SQLite evidence layer and shared NumPy-generated fixture · no X3-local RNG ·
Jinja2 · vanilla ES5 JavaScript · pytest.

**Reviewed Task-0 substrate ruling (2026-07-11):** reviewed fixture tip
`b748ea7` exposes the controlled `evaluate_funnel_cohort(conn, snapshot_slice,
*, funnel_cohort_id=...)` projection and persisted evaluation receipts. It may
support exact labelled cohort stage counts after its own completeness, window,
right, schema, mapping, and cell gates pass. The fixture manifest also binds the
unresolved prerequisite `typed-mandate-brief-cohort-projection-required` because
the shared opportunity projection has no typed mandate-brief/cohort-key columns.
Until that prerequisite closes, X3 refuses every funnel-conversion interval,
target-cell conversion, and mandate-brief/cohort inference; affected queue rows
resolve to `funnel_unavailable` before any downstream backlog reason. X3 imports
the real reviewed API directly and adds no adapter or local assignment logic.
The reviewed `universe_membership` projection also lacks the plan-assumed
`canonical_cell_id`, and `target_grid_cell` has no canonical-entity link. X3 may
render exact source/mapping/member totals and exact eligible/excluded authored-grid
totals, but it must refuse canonical target-cell observation, novelty-by-cell,
coverage-by-cell, and any queue verdict requiring that link with
`typed-membership-cell-projection-required`. No label, ordinal, geography, or
taxonomy-string heuristic may replace the missing typed projection.

---

## 1. Binding method boundary

### 1.1 The unit of analysis

X3 consumes the corrected shared canonical types and effective-dated relationship
projections. The intended identity path is:

```text
manager firm --managed-or-advised-by--> adviser / legal entity
manager firm|adviser / legal entity --offers--> strategy
strategy --reported-through--> composite
strategy|composite --implemented-by--> vehicle
vehicle --issues--> share class
strategy|vehicle|share class --available-as--> mandate / account
```

A source row may describe a manager firm, regulated adviser/legal entity,
strategy, composite, vehicle, share class, or mandate. Those are not
interchangeable, and some relationships are many-to-many rather than a single
parent tree. Every metric declares exactly one `entity_grain`, or renders separate
numerators and denominators by canonical type. There is no combined
"strategy/composite/vehicle" product total. A firm-only public registration row
can establish firm presence at `manager` grain but cannot silently become a
strategy or vehicle. A vehicle row cannot silently establish a composite history.
A funnel opportunity declares one canonical entity type and ID and retains its
separate immutable opportunity ID.

The default coverage panel is `strategy` grain. Separate source-presence panels
may show manager, adviser/legal-entity, composite, vehicle, or share-class grain,
each with its own labelled denominator. Shared effective-dated relationship
projections support drill-through but never coerce one entity type into another.

### 1.2 What X3 can say

For a named source snapshot, access context, target-grid version, and decision
time, X3 may emit:

1. exact source-record and resolved-canonical-entity counts;
2. exact unresolved, ambiguous, inactive, and newly observed counts;
3. exact coverage of the allocator-authored target-cell grid;
4. exact source-union and leave-one-source-out novelty counts;
5. exact funnel counts by stage and target cell;
6. funnel conversion proportions with binomial intervals when the event ledger
   is complete and the provisional denominator gate passes;
7. a categorical sourcing work queue whose reasons are visible; and
8. entity-resolution precision/recall intervals and discovery recall measured
   only against the fully known hidden synthetic universe.

Every result names its denominator. `12 / 18 target cells observed in the
selected sources` is valid. `67% of the global manager universe covered` is not.

### 1.3 What X3 must refuse

X3 always refuses:

- a global manager, product, strategy, or asset denominator;
- a claim that a commercial, public, or manager-supplied database is complete;
- discovery recall against the real world when the hidden population is unknown;
- a manager-quality, expected-return, hire, allocation, or conviction ranking;
- cross-strategy comparison of managers or products;
- a product count that conflates firm, strategy, composite, and vehicle rows;
- historical discovery reconstructed from today's survivors, taxonomy, aliases,
  or latest-restated memberships;
- conversion inference from an incomplete, accepted-only, or backfilled funnel;
- a source-conditioned result when the source snapshot/version, receipt time,
  evidence right, target-grid version, or canonical entity mapping is missing;
- a cell-priority verdict when the target cell has no approved sourcing mandate;
  and
- any `quality`, `best manager`, `top manager`, `recommended manager`, or
  `probability of hire success` output field.

The core copy obligation is:

> **This map measures the named sources and funnel, not the manager universe of
> the world. It prioritizes research cells, never managers.**

Tests pin that sentence and prohibit global-denominator and manager-ranking
fields throughout Python results, JSON, and rendered HTML.

### 1.4 Research-cell queue, not a scalar manager score

For each eligible approved target cell, the method emits exactly one of these reasoned
states in precedence order:

1. `repair_identity` — source rows exist but unresolved/ambiguous identities
   block a canonical count at the selected entity grain;
2. `refresh_source` — every qualifying source snapshot is stale under the named
   source-specific freshness policy;
3. `source_gap` — no canonical entity at the selected grain is observed in the
   selected approved sources;
4. `funnel_unavailable` — same-grain entities are observed, but the complete
   receipted funnel bundle needed to distinguish screening, diligence, and
   representation is unavailable;
5. `screening_backlog` — same-grain entities are observed but none has reached
   the internal screened stage;
6. `diligence_backlog` — screened same-grain entities exist but none is in active
   or closed diligence;
7. `represented` — at least one same-grain opportunity reached the cell's
   approved completion stage.

`not_targeted` is never a queue state. Ineligible or excluded target-grid cells
remain in the typed exclusion ledger with the grid's reason and receipt, but they
do not enter the coverage denominator or research queue.

The page groups queue items by reason, then sorts deterministically by
`target_priority`, taxonomy key, and cell ID. `target_priority` is an explicit,
versioned internal-governance field such as `required`, `desired`, or `observe`;
it is not inferred from manager data. X3 never emits an opaque weighted score.

---

## 2. Dependency and ownership boundary

### 2.1 Required reviewed evidence interfaces

The substrate owner, not X3, owns immutable ingestion, source-record/version
observations, entity and relationship storage, entitlements, source hashes,
revision chains, bitemporal selection, projections, typed references, and bundle
digests. X3 may not ship until the corrected evidence plan has closed its
independent review and exposes these shared calls. The funnel calls below are a
**future Phase-2 prerequisite**, not an API claimed to exist at review tip
`1112d69`: that tip lacks the typed opportunity and cohort-evaluation/membership
projections and still couples events directly to cohorts. A later unconditional
Phase-2 review tip must expose and receipt the corrected interface before X3 Task
1 starts.

```python
source_slices = tuple(
    DatasetSliceRequest(
        dataset_id=source.dataset_id,
        access_context=source.access_context,
        evidence_right_id=source.evidence_right_id,
        licence_purpose=source.licence_purpose,
        valid_at=decision_at,
        require_universe_membership=True,
    )
    for source in selected_sources
)

coverage_bundle = as_known_bundle(
    conn,
    SnapshotBundleRequest(
        decision_at=decision_at,
        sources=source_slices + (target_grid_slice,),
        join_keys=("canonical_entity_id", "target_grid_cell_id"),
        join_policy="x3-source-union-v1",
    ),
)

funnel_bundle = as_known_bundle(
    conn,
    SnapshotBundleRequest(
        decision_at=decision_at,
        sources=(
            opportunity_slice,
            funnel_schema_slice,
            cohort_definition_slice,
            funnel_event_slice,
        ),
        join_keys=("opportunity_id",),
        join_policy="x3-funnel-cohort-v1",
    ),
)

coverage_projections = {
    snapshot_slice.request.dataset_id: {
        "mappings": project_entity_mappings(conn, snapshot_slice),
        "relationships": project_entity_relationships(conn, snapshot_slice),
        "memberships": project_universe_memberships(conn, snapshot_slice),
        "target_grids": project_target_grids(conn, snapshot_slice),
    }
    for snapshot_slice in coverage_bundle.slices
}

funnel_projections = {
    snapshot_slice.request.dataset_id: {
        "opportunities": project_funnel_opportunities(conn, snapshot_slice),
        "schemas": project_funnel_schemas(conn, snapshot_slice),
        "cohorts": project_funnel_cohorts(conn, snapshot_slice),
        "events": project_funnel_events(conn, snapshot_slice),
    }
    for snapshot_slice in funnel_bundle.slices
}

# Cross-slice assignment is substrate-owned and bundle-receipted. Task 0 replaces
# the ellipsis only with the later reviewed Phase-2 signature.
cohort_assignments = project_funnel_cohort_evaluations(...)
```

If the corrected substrate names the controlled assignment projection
`project_funnel_cohort_memberships` rather than
`project_funnel_cohort_evaluations`, the Phase-2 ruling records that one exact
name and X3 imports it directly. X3 must not probe for both names, create a local
adapter, or derive cohort membership itself. The exact corrected Phase-2 tip also
pins whether the assignment function accepts the bundle alone or additional typed
arguments; X3 copies that reviewed signature rather than guessing. Transitions and reason codes live in
the versioned `FunnelSchema`; there is no transition-dictionary dataset slice or
projection.

Every dataset has its own `DatasetSliceRequest` naming the exact dataset, right,
access context, licence purpose, and temporal selector. A multi-source claim uses
AND semantics: every required slice must pass; a right for one dataset never
authorizes another. A one-source claim still uses a one-source
`SnapshotBundleRequest`. Coverage and funnel use separate bundles because their
declared joins differ; X3 never row-position joins or label-matches slices.

Shared projections retain typed references to source items/spans, dataset
versions, rights, mappings, memberships, grid cells, opportunities, funnel
schemas, cohort policies, cohort evaluations/memberships, and events. Each X3 claim receipt binds the ordered
slice digests, composite input digest, shared join-receipt ID, bundle digest,
algorithm/parameter/value digests, and included, excluded, and refused typed
references. Receipt verification must fail if any required source, right,
dataset-version, exclusion, join rule, or output field is omitted.

The substrate derives all knowledge and availability times from source evidence,
dataset-version observations, and rights. Neither X3 models nor generator inputs
accept `available_at`, `known_at`, `first_known_at`, or a card-local mapping,
membership, grid, relationship, opportunity, funnel schema, cohort assignment, or funnel
projection. X3 may validate shared projection completeness and refuse it; it may
not repair or replace it.

### 2.2 X3-owned domain interfaces

Create only result/configuration and pure-analysis interfaces in
`src/quant_allocator/flagships/universe_coverage/`. Shared evidence projection
types are imported from `quant_allocator.evidence`; X3 does not duplicate them:

```python
@dataclass(frozen=True, slots=True)
class CoverageSelection:
    entity_grain: str
    selected_dataset_ids: tuple[str, ...]
    target_grid_id: str
    active_only: bool
    freshness_policy_ids: tuple[str, ...]


@dataclass(frozen=True)
class CoverageResult:
    decision_at: datetime
    entity_grain: str
    denominator_label: str
    eligible_target_cells: int
    excluded_target_cells: int
    target_cells_observed: int
    source_rows: int
    canonical_members: int
    unresolved_rows: int
    ambiguous_rows: int
    inactive_members: int
    exact_counts_by_cell: tuple[CellCount, ...]
    source_novelty: tuple[SourceNovelty, ...]
    funnel_by_cell: tuple[FunnelCell, ...]
    queue: tuple[QueueItem, ...]
    refusals: tuple[Refusal, ...]
    receipt: ReconstructionReceipt


def build_coverage(
    coverage_bundle: SnapshotBundle,
    memberships: Sequence[UniverseMembership],
    target_grids: Sequence[TargetGrid],
    funnel_summary: FunnelSummary | None,
    *,
    selection: CoverageSelection,
) -> CoverageResult: ...


def build_funnel_summary(
    funnel_bundle: SnapshotBundle,
    opportunities: Sequence[FunnelOpportunity],
    schemas: Sequence[FunnelSchema],
    cohorts: Sequence[FunnelCohort],
    cohort_evaluations: Sequence[FunnelCohortEvaluation],
    events: Sequence[FunnelEvent],
) -> FunnelSummary: ...


def entity_resolution_audit(
    predictions: Sequence[EntityMapping],
    hidden_truth_labels: Sequence[TruthPair],
) -> ResolutionAudit: ...


def synthetic_discovery_audit(
    observed: Sequence[UniverseMembership],
    hidden_universe: Sequence[HiddenMember],
) -> DiscoveryAudit: ...
```

`TruthPair` and `HiddenMember` are the only card-local evidence-like fixture types;
they validate the authored synthetic regime and never enter a live claim receipt.
No interface takes a current roster or caller-authored knowledge time. No
interface returns a manager score or accepts performance as a feature.

### 2.3 Shared-seam escalation

If the reviewed evidence layer cannot represent one of these facts, stop and hand
the exact schema requirement to the substrate owner. Do not add a card-local
SQLite table, evidence graph, entity registry, relationship table, hash store,
revision engine, resolver, or projection.
Likewise, X3 does not own E3 document extraction, E4 operational facts, or S7
track-record/composite lineage.

---

## 3. Entity and universe-membership contract

### 3.1 Canonical identity

Canonical IDs are immutable surrogate IDs. Legal names, trading names, domains,
regulatory IDs, and source labels are versioned aliases, not primary keys. Mergers,
rebrands, team moves, and predecessor claims create dated relationships; they do
not rewrite old records.

Each shared source-to-canonical mapping projection has:

```text
mapping_id
dataset_id, dataset_version, source_record_id
source_entity_type
canonical_entity_type, canonical_entity_id
mapping_status = accepted | ambiguous | rejected | unresolved
match_rule = exact_external_id | exact_crosswalk | compound_exact | reviewed_manual
candidate_entity_ids
effective_from, effective_to
source item/span, dataset version, acquisition right, licence purpose
derived available_at
version, revision_of
evidence_item_ids
```

The shared relationship projection likewise records relationship type, both
typed entity IDs, effective interval, mapping/taxonomy version, derived
availability, revision chain, and typed evidence references. X3 consumes only
relationships known by the bundle cutoff. It does not infer `adviser -> strategy`
from labels or force a many-to-many relation into `parent_entity_id`.

Automatic acceptance is intentionally narrow:

1. an exact, type-compatible external identifier or reviewed crosswalk; or
2. a unique compound exact match on normalized legal name, jurisdiction, entity
   type, and manager-controlled domain, with no conflicting identifier.

String similarity may generate a candidate set for review but cannot auto-merge.
A collision, type conflict, multiple candidate, or time-incompatible match becomes
`ambiguous`. Ambiguous and unresolved rows stay visible and never enter canonical
product counts.

### 3.2 Universe membership

One membership row means: *the named source snapshot represented this named
source record as this entity, with this source-declared status, as known at this
time*. It does not mean the product exists globally, is investable, is suitable,
or is good.

The shared membership projection supplies:

```text
membership_id
dataset_id, dataset_version, source_record_id
member_entity_type, canonical_entity_id
source_status = active | inactive | closed | unknown
source_strategy_label, source_geography_label, source_vehicle_label
canonical_cell_id, taxonomy_mapping_version
effective_from, effective_to
derived available_at
version, revision_of, publication_status
evidence_right_id, sensitivity_class, licence_purpose
content_sha256, evidence_item_ids
```

Every dataset version declares `delivery_mode = full-snapshot | delta`,
predecessor/base version,
`reconstruction_manifest_sha256`, expected and received partition keys, explicit
completeness state, row count, and `absence_semantics = not-inferable |
full-snapshot-means-removed | explicit-tombstone-only`. A full snapshot may link an unchanged logical content
version as a new dataset-version observation; it need not create a no-op content
revision. A missing row implies exit/inactivity only when the version is a
certified complete `full-snapshot`, all expected partitions are present, and
`absence_semantics=full-snapshot-means-removed`. Under
`explicit-tombstone-only`, only an explicit receipted tombstone implies removal;
under `not-inferable`, absence never does. A `delta` missing a row never implies
removal without the required tombstone. If a rendered bundle contains constituent
slices with different per-version modes, X3 may label the bundle `mixed` only as
a derived display summary; `mixed` is not a dataset-version request or stored
value. Any unmet condition refuses exit, coverage-loss, and complete-denominator
inference. Dead/inactive products remain queryable. Backfilled history is gated by
its shared derived availability; it cannot appear before the later version was
known.

`canonical_cell_id` is a dated mapping to a versioned target taxonomy, not a
property copied permanently onto the entity. A later taxonomy remap must not alter
an earlier decision snapshot.

### 3.3 Funnel membership

The funnel is event-sourced. Allowed stages are:

```text
discovered -> contacted -> rfi_received -> screened -> diligence
           -> ic_ready -> approved -> funded
```

Terminal or side states are:

```text
declined, manager_withdrew, unavailable, paused, duplicate, out_of_scope
```

Every shared opportunity projection retains immutable `opportunity_id`, declared
canonical entity type/ID, mandate brief/cohort keys, creation event, terminal
status, and source references. Every event retains its authored point time,
derived availability, source, reason code, opportunity ID, and revision chain. A
correction supersedes an event; it never overwrites it.

The opportunity dataset version names a versioned opportunity payload schema. A
separately versioned `FunnelSchema` contains the stage/state and reason
dictionaries, allowed starts and transitions, terminal/side states, correction
semantics, completeness rule, and impossible paths. A separate versioned cohort
definition declares entry stage, exit stage, inclusion and exclusion rules,
cohort start/end, observation-window end, right-censor policy, and entity grain.
The shared cohort-evaluation/membership projection receipts each included and
excluded opportunity against that definition. Stage conversion uses the first
valid schema transition known by the cutoff and publishes the opportunity,
schema, cohort, assignment, and event versions. It does not infer missing earlier
stages or assign opportunities locally.

Before any funnel interval, every required dataset slice must have a passing
right/access/licence receipt. Opportunity/event delivery must be a certified
complete `full-snapshot` with `full-snapshot-means-removed`, or a reconstructable
`delta` whose active/terminal coverage is proven through explicit tombstones and
`explicit-tombstone-only`. `not-inferable` absence cannot support a cohort
denominator. The receipt must cover active and terminal opportunities,
included/excluded events, the funnel schema, cohort definition, cohort
evaluations/memberships, and cutoff. An accepted-only log, missing opportunity
IDs, incomplete dataset version, nonqualifying absence semantics, impossible
schema transition, unelapsed window, or unversioned opportunity/funnel-schema/
cohort evidence forces conversion refusal. Exact visible
extract counts may remain only as explicitly labelled extract counts; they are not
cohort stage counts.

Funnel `opportunity_id` distinguishes repeated consideration of the same product
for different mandate briefs. Canonical product identity must therefore not be
used as the funnel event key.

### 3.4 Target-grid contract

The target grid is allocator-authored policy, not a discovery estimate. Each
version declares entity grain, controlled strategy, geography, and vehicle
buckets, target priority, approved completion stage, effective interval,
`eligibility_status = eligible | excluded`, explicit exclusion reason, denominator
rule/version, and typed evidence receipt. Historical analyses use the grid version
available at the decision time.

Only `eligible` cells at the selected entity grain enter the denominator and
queue. Every included and excluded cell is a typed receipt reference. Excluded or
out-of-scope cells render only in the exclusion ledger as `not_targeted` with the
source reason; they cannot appear in the matrix denominator, numerator, gap count,
or queue. The method refuses if eligible plus excluded cells do not reconcile to
the receipted grid version.

---

## 4. Realistic source-shape contract

All committed records are fictional synthetic fixtures. The schemas below model
realistic delivery shapes, but no licensed database row, manager document, actual
funnel record, or restricted source content enters the repository.

### 4.1 Public sources

| Synthetic source adapter | Realistic shape modelled | Fields used by X3 | Boundary |
|---|---|---|---|
| `public_adviser_register` | periodic structured registration snapshot with adviser ID, legal name, registration/reporting state, jurisdiction, business attributes, related private-fund identifiers, and filing date | firm/legal-entity presence, exact public ID, effective/available dates | adviser presence is not product coverage; registration is not quality |
| `public_registered_fund_filings` | filing/fund/series/class tables with registrant and series identifiers, filing period, submission timestamp, and public portfolio/report metadata | registered vehicle identity, public series/class relationships, receipt time | registered funds only; not hedge/private-product coverage |
| `public_holdings_filer_list` | quarterly filer identity and filing metadata for institutional managers above the filing rule's scope | public manager/filer presence and stale receipt evidence | a filer is not a manager-product universe; listed long holdings do not identify all strategies |

The public fixture fields are informed by the official [Form ADV data
description](https://www.sec.gov/foia-services/frequently-requested-documents/form-adv-data),
[Form N-PORT dataset description](https://www.sec.gov/data-research/sec-markets-data/form-n-port-data-sets),
and [Form 13F FAQ](https://www.sec.gov/rules-regulations/staff-guidance/division-investment-management-frequently-asked-questions/frequently-asked-questions-about-form-13f).
Those references establish source shape and scope, not completeness for X3.

### 4.2 Pre-hire sources

| Synthetic source adapter | Realistic shape modelled | Fields used by X3 | Boundary |
|---|---|---|---|
| `strategy_database_export` | received snapshot of manager-populated product rows: firm/product IDs, status, strategy taxonomy, geography, vehicle, inception, AUM date, returns-through date, last update, and export version | source-conditioned product membership, status, taxonomy labels, staleness, first known date | self-reported/licensed universe; denominator is this snapshot only |
| `rfi_ddq_register` | one row per request/response package with manager, strategy, vehicle, request/receipt dates, response version, declared status, and document evidence IDs | shortlisted membership and funnel transitions | receipt establishes what the allocator knew; DDQ response is manager-asserted |
| `conference_referral_log` | referral/source note with source label, event date, received date, tentative firm/product label, geography, and reviewer state | discovered candidates and unresolved-identity queue | tentative names never enter canonical counts before resolution |

The strategy-database fixture mirrors the collection mechanics described in the
provider's public [data-collection
process](https://www.nasdaq.com/solutions/evestment/global-database/data-collection-process),
including manager-populated product data and recurring updates. It does not copy
provider data, field text, coverage claims, or provider-specific taxonomy.

### 4.3 Internal-governance sources

| Synthetic source adapter | Shape | Fields used by X3 | Boundary |
|---|---|---|---|
| `target_grid` | versioned approved cell policy | cell denominator and reason precedence | policy coverage, never world coverage |
| `sourcing_funnel_opportunities` | certified complete opportunity register or reconstructable delta with immutable opportunity ID, declared entity grain, mandate brief, created/terminal state, schema version, and controlled absence semantics | opportunity denominator and repeated-product separation | accepted-only, incomplete, or `not-inferable` register refuses cohort counts |
| `funnel_schema` | versioned stage/state and reason dictionaries with allowed starts, transitions, terminals, side states, correction rules, completeness, and effective interval | event validation | unversioned or stale schema refuses conversion; no separate transition dataset |
| `funnel_cohort_policy` | versioned entry/exit stage, inclusion/exclusion, cohort dates, observation window, censoring rule, and entity grain | exact cohort construction | no post-hoc cohort or inferred window |
| shared cohort evaluation/membership | typed included/excluded opportunity-to-cohort assignment projected by the corrected evidence substrate | receipted cohort denominator | missing assignment projection blocks X3; X3 never derives it locally |
| `sourcing_funnel_events` | certified complete full snapshot or reconstructable point-event delta with opportunity ID, reason, event time, receipt evidence, revision, and schema versions | exact complete-cohort stage counts, conversion intervals, backlog | missing partitions, nonqualifying absence semantics, or invalid history permits labelled extract counts only |
| `sourcing_research_log` | dated cell-level search action and next review date | searched/unsearched distinction and freshness | activity is not manager quality |
| `entity_review_queue` | accepted/ambiguous/rejected mapping decisions with evidence | entity-resolution state and audit | reviewed mappings remain B-class unless independently reconstructable |

Internal fixtures contain no real people, employers, mandates, comments, or
manager names. They use fictional codes and constrained reason enums.

### 4.4 Minimum viable access by output

| Output | Lowest access | Required evidence shape | Refusal condition |
|---|---|---|---|
| public source presence | `public` | archived public snapshot, source ID, publication/first-observed time | missing snapshot/version or entity type |
| pre-hire source presence | `pre-hire-public` | received export or public manager material with receipt | unversioned latest-only export |
| shortlisted source coverage | `shortlisted-nda` | received RFI/DDQ register and evidence IDs | no receipt or unresolved identity |
| target-cell coverage | `internal-governance` plus selected source rights | versioned target grid and selected source memberships | unknown grid/source denominator |
| funnel counts/conversion | `internal-governance` | separately versioned, fully receipted opportunity, funnel-schema, cohort, cohort-evaluation/membership, and event evidence | any missing right/version/schema/projection, accepted-only log, `not-inferable` absence, incomplete partition, invalid schema transition, or unelapsed window |
| hidden-universe recall | synthetic demo only | complete authored truth table | any live/global interpretation |

---

## 5. Claim, access, and attestation matrix

Every committed demo claim starts at D because all displayed evidence is
synthetic. A live ceiling is a capability, not the badge rendered on the demo.

| Claim ID | Output type | Access contexts | Current | Live ceiling | Receipt | Live validation/refusal |
|---|---|---|---|---|---|---|
| `public_source_membership` | exact measurement | public | D | A | required | public snapshot can be independently re-fetched/reconstructed; otherwise B or refuse |
| `prehire_source_membership` | exact measurement | pre-hire-public, shortlisted-nda | D | B | required | source export and field dictionary reproduce counts; missing vintage refuses |
| `entity_resolution_state` | exact measurement + verdict | public, pre-hire-public, shortlisted-nda | D | B | required | exact/reviewed mapping evidence; ambiguous rows excluded from canonical counts |
| `target_cell_observation` | exact measurement | internal-governance plus every selected source right/purpose | D | B | required | versioned eligible/excluded target grid and same-grain source memberships; denominator label and cell receipts mandatory |
| `source_union_novelty` | exact measurement | internal-governance plus every selected source right/purpose | D | B | required | same decision cutoff, grain, taxonomy, per-dataset access, and receipted join across sources; otherwise refuse |
| `funnel_stage_counts` | exact measurement | all required internal-governance funnel evidence | D | B | required | complete opportunity/event versions, qualifying absence semantics, funnel schema, cohort and assignment projections, and elapsed window; incomplete data permits labelled extract counts only |
| `funnel_conversion` | interval | all required internal-governance funnel evidence | D | B | required | per-dataset receipts, completeness/absence, cohort/window, schema transitions, assignment projection, and denominator gate; below gate emits complete-cohort counts plus refusal |
| `research_cell_queue` | verdict | internal-governance grid/funnel plus every selected source right/purpose | D | C | required | eligible policy target and visible reason; incomplete funnel emits `funnel_unavailable`; no scalar score |
| `synthetic_entity_recall` | interval | synthetic demo | D | D | required | hidden authored truth only; never generalized to live data |
| `synthetic_discovery_recall` | exact measurement | synthetic demo | D | D | required | complete hidden authored universe only |
| `global_universe_coverage` | refusal | all | D | none | required | always refuses because denominator is unknown |
| `manager_quality_ranking` | refusal | all | D | none | required | always refuses because X3 does not assess quality |

Reconstruction receipts include, for every required dataset, dataset/version,
delivery/completeness and absence semantics, access context, exact right, licence
purpose, disposition, and slice digest. They also include the target-grid and
denominator-rule versions; entity/relationship/mapping/membership versions;
opportunity, funnel-schema, cohort, cohort-evaluation/membership, and observation-window versions;
decision cutoff; canonical row-order digest; composite input digest; shared join
receipt and bundle digest; included/excluded/refused typed references; algorithm
and parameter digests; and output digest. Multi-source validation is AND, never
"any listed access is enough."

---

## 6. Source-conditioned coverage and refusal logic

### 6.1 Exact metrics

For a selected set of source snapshots \(S\), eligible target-grid cells
\(G^{\mathrm{eligible}}_{t,q}\), decision time \(t\), and one declared canonical
entity grain \(q\), define:

\[
O_{g,t,q}(S)=\mathbf{1}\{\text{at least one resolved canonical entity of type }q
\text{ in cell }g\text{ is visible in }S\text{ as known at }t\}.
\]

The target-grid observation coverage is:

\[
C_{t,q}(S)=
\frac{\sum_{g\in G^{\mathrm{eligible}}_{t,q}} O_{g,t,q}(S)}
{|G^{\mathrm{eligible}}_{t,q}|}.
\]

Interpretation: the numerator counts eligible approved target cells represented
by at least one resolved entity at the declared grain in the selected sources;
the denominator is the eligible subset of the allocator-authored grid at that
same grain. Excluded cells are receipted separately and do not enter either term.
It is not a manager-universe coverage rate.
Because this is an exact measurement of the received snapshot, the page displays
the numerator and denominator rather than a sampling interval.

For source \(s\), the leave-one-source-out novelty count is:

\[
N_{s,t,q}=\left|U_{t,q}(S)\setminus U_{t,q}(S\setminus\{s\})\right|,
\]

where \(U_{t,q}\) is the set of resolved canonical IDs of exactly type \(q\).
This is order independent and says how many observed canonical entities at that
grain disappear when the named source is removed. Results at different entity
grains render separately and are never added. It is not a source-quality score.

### 6.2 Funnel conversion

For a dated opportunity cohort, conversion from stage \(a\) to stage \(b\) is:

\[
\hat p_{a\rightarrow b}=\frac{n_b}{n_a},
\]

where \(n_a\) counts unique eligible opportunity IDs reaching stage \(a\) and
\(n_b\) counts the subset reaching stage \(b\) within the disclosed observation
window. Display the exact ratio and a two-sided Wilson interval. Do not infer
causality, future hit rate, or manager quality.

If \(n_a\) is below `X3_FUNNEL_RATE_MIN_DENOM`, emit the exact complete-cohort
counts and a `count_only_insufficient_cohort` refusal instead of a conversion
estimate. Right-censored cohorts without the named elapsed observation window
refuse conversion. Incomplete/unknown-absence ledgers emit only labelled visible
extract counts, never \(n_a\), \(n_b\), or an interval.

### 6.3 Deterministic refusal precedence

Whole-result refusal precedes partial results in this order:

1. naive/future time or any required dataset's missing/mismatched
   right/access/licence purpose;
2. incomplete or conflicting revision chain;
3. missing/incomplete source dataset version or unknown required absence semantics;
4. missing target-grid/taxonomy version;
5. absent canonical entity type or impossible hierarchy;
6. requested global denominator or manager ranking.

Partial exclusions then apply row by row: unresolved/ambiguous mappings, stale
sources, wrong-grain rows, ineligible target cells, out-of-scope entity types, and
inactive status as selected. Each excluded count and excluded grid cell remains
visible with a typed receipt reference. The page must never hide exclusions to
improve a coverage percentage.

---

## 7. Hidden synthetic universe and planted failures

### 7.1 Shared evidence fixture and card-local truth labels

The evidence-substrate seam owner builds one fully synthetic, fully receipted
`x3_evidence_v1` fixture before X3 implementation. X3 consumes that shared fixture
through the same ingestion, bundle, and projection APIs used by every card; it
does not generate card-local rights, dataset versions, source records, mappings,
memberships, relationships, target grids, opportunities, funnel schemas, cohorts,
cohort evaluations/memberships, or events. All displayed names are fictional and verified unique across
committed JSON. The shared fixture contains:

- 24 fictional manager firms and adviser/legal entities;
- 72 canonical product units across strategy, composite, and vehicle levels;
- 24 approved target cells spanning public equity, hedge funds, rates/macro,
  fixed-income/credit, structured credit, private credit, private equity, and
  real assets, multiple geographies, and pooled/drawdown/segregated vehicles;
- three decision cutoffs and corresponding target-grid versions;
- active, inactive, closed, newly launched, renamed, and dead products;
- repeated source records for the same product, firm-only rows, vehicle/composite
  near-collisions, rebrands, and source taxonomy disagreements;
- source evidence sufficient for 420 labelled positive identity pairs and 420
  hard negative pairs;
- public, pre-hire, shortlisted, and internal-funnel source views, each with a
  distinct observation mechanism; and
- at least 80 funnel opportunities, including repeated opportunities for the same
  product and terminal states.

X3 owns only an immutable `x3_truth.py` table mapping shared fixture source keys to
synthetic hidden canonical truth, plus hidden-universe eligibility labels. Truth
labels are excluded from live claim inputs and receipts; they feed only D-tier
synthetic validation. Tests prove every label points to a shared fixture source
key and that the analysis never reads truth labels while building live-shaped
coverage, novelty, funnel, or queue outputs.

Counts are provisional fixture design constants. Neither the seam owner nor X3
implementer may tune them to make the exhibit pass. If runtime or readability
requires a change, docket and independently approve the new value before shared
fixture regeneration and card generation.

### 7.2 Shared named random streams

The shared fixture exposes its fixed base seed and named integer stream tags in
its receipt metadata. Stream ownership stays in the evidence fixture package so
another card cannot generate a divergent copy. It uses
`np.random.default_rng([base_seed, stream_tag])`; `hash()`, label-derived seeds,
iteration-order seeds, and seed scanning are forbidden. X3 truth labels are
authored constants and use no RNG. X3 tests assert shared tags are unique, the
fixture ID/digest is pinned, and input-order permutations leave bundle, receipt,
and output bytes unchanged.

### 7.3 Planted leakage and refusal cases

The fixture must include and test all of these:

1. a dead product backfilled into a later source export;
2. an alias/crosswalk learned after the earliest decision date;
3. a merger and rebrand whose current canonical relationship was not yet known;
4. a taxonomy remap learned after an earlier target-grid decision;
5. a source row published before but received after the cutoff;
6. a licensed row received but not yet entitled at the cutoff;
7. a revised funnel event that reverses an earlier stage;
8. an accepted-only funnel extract that omits declined opportunities;
9. duplicate source rows that would inflate counts without canonical identity;
10. a firm-only registration record that cannot count as a product;
11. an ambiguous name collision that must not auto-merge;
12. a source snapshot whose absence semantics are unknown;
13. an inactive product retained in history but excluded from the active-only view;
14. an unknown target-grid denominator request; and
15. explicit requests for global coverage and manager ranking;
16. consecutive `full-snapshot` versions containing an unchanged member, a changed
    member, a new member, and a disappeared member under both
    `full-snapshot-means-removed` and `not-inferable` contracts, plus a `delta`
    using `explicit-tombstone-only`;
17. an incomplete expected partition that blocks absence and funnel completeness;
18. two opportunities for one canonical strategy under different mandate briefs;
19. an impossible event transition and a stale `funnel_schema` version;
20. an eligible and an excluded cell whose omission from typed receipt references
    fails verification; and
21. one selected source whose expired/mismatched right proves multi-source AND
    refusal even when every other slice passes.

The demo should contain at least one visible example of cases 1, 2, 9, 10, and 11.
The remaining cases may appear in the refusal ledger and tests.

---

## 8. Validation and power gates

### 8.1 Entity-resolution validation

Against the hidden labelled pair table, report precision and recall with Wilson
95% intervals. The provisional synthetic gate is:

```text
precision lower bound >= 0.99
recall lower bound >= 0.95
zero entity-type conflicts among accepted links
zero ambiguous links entering canonical counts
```

The precision gate has a binding finite-sample floor. At perfect observed
precision, \(\hat p=1\), the two-sided Wilson lower bound reduces to:

\[
L_{\mathrm{Wilson}}(n, n)
=\frac{n}{n+z^2}.
\]

For \(z=1.96\) and required lower bound \(g=0.99\), solve:

\[
\frac{n}{n+z^2}\ge g
\quad\Longleftrightarrow\quad
n\ge\frac{g z^2}{1-g}
=380.3184.
\]

Therefore the gate requires at least **381 accepted true-positive links and zero
accepted false positives** even before considering recall. At \(n=381\), the
lower bound is approximately \(0.990018\); 160 accepted positives could not pass.
The authored demo target is 410 accepted true positives from 420 labelled
positives, zero false positives from 420 hard negatives. At runtime the shared
Wilson helper must compute the bounds from the emitted confusion matrix; tests
independently re-derive them from raw truth labels and assert the minimum-accepted
formula. No pass flag or teaching value is hard-coded.

The implementer must not tune the fixture, exact rules, or confidence level after
seeing the result. If the gate fails, the active demo falls back to exact-ID and
reviewed-crosswalk matches only; compound matches remain a labelled candidate.
The failed result remains visible.

These intervals validate the authored synthetic perturbation regime only. They do
not certify live global identity resolution. Live deployment needs a separately
adjudicated, time-frozen sample by source and entity type.

### 8.2 Discovery-recall validation

For the synthetic fixture only, the hidden universe supplies the exact denominator:

\[
R_{S}^{\mathrm{synthetic}}=
\frac{|U_t(S)\cap U_t^{\mathrm{hidden}}|}{|U_t^{\mathrm{hidden}}|}.
\]

Emit exact numerator and denominator by source combination and target cell. Plant
at least one cell absent from every source so the demo cannot show perfect recall.
The page labels this `synthetic fixture recall`; it never labels it `market
coverage` or a live quality metric.

There is no live global discovery-recall gate. A live source may only report
source-conditioned exact counts and controlled audit recall against a separately
frozen, known roster whose construction is disclosed.

### 8.3 Funnel validation

Before emitting a conversion interval, assert:

- unique opportunity IDs;
- allowed event states and transitions;
- complete active/terminal opportunity coverage for the cohort;
- event time and available time at or before the cutoff;
- observation window elapsed or right-censoring disclosed;
- no future revision in the snapshot; and
- denominator at least `X3_FUNNEL_RATE_MIN_DENOM`.

The demo plants one sufficiently large source-to-screen cohort and one sparse
diligence-to-approval cohort. The first displays a Wilson interval; the second
displays counts plus refusal.

### 8.4 Point-in-time and determinism tests

Tests must prove:

- `as_known_bundle(... decision_at=t)` excludes later receipts, entitlements,
  mappings, relationships, target grids, backfilled memberships, and revisions;
- a latest-restated run visibly differs from an earlier point-in-time run;
- inactive and dead products remain in historical snapshots;
- half-open effective intervals behave exactly at the boundary;
- source row order, funnel event order, mapping order, and dictionary order do not
  affect results or receipt hashes;
- duplicate source listings resolve to one canonical product without deleting the
  duplicate evidence;
- ambiguous mappings are excluded and counted;
- exact counts reconcile from cell detail to totals;
- source novelty re-derives from canonical set differences;
- funnel stage counts and Wilson intervals independently re-derive;
- every result receipt names every consumed included/excluded/refused typed
  evidence reference; and
- every result receipt also names every required dataset/version/right/purpose,
  excluded grid cell, shared join receipt, and bundle digest;
- the Wilson precision test proves 380 perfect accepted links fail and 381 pass;
- two generator runs and the committed JSON are byte-identical.

---

## 9. Provisional constants docket

Every constant below remains a named numerics-gate item. Equality semantics are
binding unless independent review changes them before implementation.

| ID | Constant/rule | Provisional value | Gate question |
|---|---|---|---|
| X3-D1 | hidden firms/products/target cells | 24 / 72 / 24 | enough collisions and sparse cells without an unreadable page? |
| X3-D2 | labelled identity pairs | 420 positive / 420 hard negative; authored target 410 TP / 0 FP | enough precision/recall resolution for both lower-bound gates? |
| X3-D3 | entity precision lower bound | at least 0.99, equality passes; at least 381 accepted TP and 0 FP | finite-sample floor re-derived at runtime? |
| X3-D4 | entity recall lower bound | at least 0.95, equality passes | does fallback preserve honesty if this misses? |
| X3-D5 | interval method | two-sided Wilson 95%, z=1.96 | suitable for entity and funnel proportions? |
| X3-D6 | minimum funnel denominator | 20, equality passes | enough for an interval to be more useful than counts? |
| X3-D7 | funnel opportunities | at least 80 | enough one large and one sparse planted cohort? |
| X3-D8 | source freshness | adapter-declared; demo public 120d, strategy export 90d, RFI 180d | freshness is source policy, not one global number |
| X3-D9 | queue precedence | identity, stale, source gap, funnel unavailable, screen, diligence, represented | does this order preserve explicit refusal before downstream backlog inference? |
| X3-D10 | auto-match rules | exact ID/crosswalk or unique compound exact | prohibit fuzzy auto-merge |
| X3-D11 | decision cutoffs | three authored UTC quarter-end snapshots | sufficient to demonstrate backfill/leakage visibly? |
| X3-D12 | shared fixture seed/stream tags | owned and receipted by `x3_evidence_v1`; no X3-local RNG | tags unique and fixture digest pinned? |
| X3-D13 | synthetic missing cell | at least one absent from all selected sources | prevents a misleading perfect-recall exhibit |
| X3-D14 | target priority | required, desired, observe | governance input only; no inferred weight/score |

The independent reviewer may revise provisional values. The implementer must not
change them silently or scan seeds/constants to recover a preferred headline.

---

## 10. Deterministic generator and JSON contract

Create `src/quant_allocator/demo_data/x3_universe.py`. The generator:

1. loads the pinned shared `x3_evidence_v1` fixture and verifies its fixture,
   schema, source, and receipt digests;
2. ingests only those shared records through the common evidence harness into a
   temporary database;
3. constructs an explicit `DatasetSliceRequest` for every selected source,
   target-grid, opportunity, funnel-schema, cohort, and event dataset, then
   consumes the shared cohort-evaluation/membership projection;
4. queries shared bundles/projections at three decision cutoffs and exactly three
   source/access presets;
5. loads card-local hidden truth labels only for the two synthetic D-tier audits;
6. runs the real X3 pure methods and shared receipt verification;
7. independently re-derives the visible audits from raw projections and truth
   labels, including the Wilson finite-sample floor;
8. emits finite, sorted JSON through `_emit.write_json`; and
9. never creates card-local evidence, resolves an entity, performs seed scanning,
   accesses a network, or delegates computation to the browser.

The JSON top-level contract is:

```text
meta
claim_attestation
taxonomy
source_catalog
states
entity_resolution_audit
synthetic_discovery_audit
refusal_ledger
method_receipts
provisional_constants
```

Each `states` entry is keyed by a stable token, not by free text:

```text
<decision-cutoff>|<source-preset>|<scope-preset>
```

The state key set is exactly the Cartesian product of three cutoffs, three source
presets (`public-only`, `public-plus-prehire`, `full-synthetic-funnel`), and three
scope presets, for exactly \(3\times3\times3=27\) states. Generator and browser
tests compare the exact 27-key set, not only its length; any missing or fourth
source preset fails.

Each state includes entity grain, exact totals, eligible and excluded grid counts,
denominator label/rule/version, cell matrix, source novelty, funnel extract or
complete-cohort counts/intervals, cohort/window/schema versions, research queue,
excluded-row and excluded-cell ledgers, refusals, per-dataset slice receipts,
shared join receipt, bundle digest, and claim receipt ID. No state contains a
mixed-grain total, global coverage field, or manager score.

Committed JSON is held until the independent numerics/copy/attestation gate. It
must never be hand-edited or tuned toward the plan's illustrative counts.

---

## 11. Page and precomputed interaction contract

### 11.1 Server-rendered baseline

The X3 page renders the default latest/public-plus-pre-hire/cross-asset state in
HTML before JavaScript. It includes:

- the binding source-conditioned disclaimer;
- current stage, decision readiness, minimum data, asset scope, access,
  validation, and current attestation context;
- per-dataset source/right/purpose receipts, shared join receipt, bundle digest,
  and explicit entity-grain/eligible-denominator label;
- a target-cell matrix with exact same-grain canonical-entity and complete funnel
  cohort counts;
- an unresolved/ambiguous/inactive/wrong-grain exclusion ledger and a separate
  `not_targeted` excluded-cell ledger;
- leave-one-source-out novelty counts;
- the research-cell work queue with visible reason and target priority;
- entity-resolution precision/recall intervals and gate state;
- synthetic hidden-universe recall, permanently labelled D and synthetic;
- a global-denominator refusal and manager-ranking refusal;
- `What this exhibit shows`, method link, synthetic disclosure, tier badges, and
  go-live requirements; and
- accessible tables for every visual map.

No-JavaScript output remains complete and useful.

### 11.2 Controls

The page has three native control groups:

1. decision cutoff: early, middle, latest;
2. source/access preset: public only, public + pre-hire, full synthetic funnel;
3. scope preset: cross-asset, liquid public markets, credit/private markets.

The source preset names only the discovery sources. Every coverage state also
requires the internal-governance target-grid slice; a funnel-dependent queue or
interval additionally requires all four funnel slices. Thus `public-only` never
means that a public right authorizes the target grid or funnel.

The generator precomputes every declared state. JavaScript performs a dictionary
lookup, replaces text/table/SVG attributes from the selected state, updates the
URL query string, and announces the state through `aria-live=polite`. It does not
resolve aliases, calculate counts/ratios/intervals, or decide queue reasons.

Every control must change both visual and textual evidence. Unsupported state keys
fall back to the server-rendered default and show a refusal; there is no
interpolation.

### 11.3 Focused interaction tests

Browser verification covers:

- exact enumeration and successful lookup of all 27 declared state keys, with no
  missing or extra source preset;
- both endpoints and the middle decision cutoff;
- every source/access preset;
- every scope preset;
- named pairwise combinations plus planted refusal combinations;
- URL reload and back/forward restoration;
- keyboard-only control and focus preservation;
- `aria-live` result update;
- no JavaScript estimator signatures or math-derived displayed values;
- 320, 390, 768, and 1440px geometry with no horizontal overflow;
- no-JavaScript default completeness;
- strict KaTeX rendering for all spec formulas with zero raw delimiters, errors,
  warnings, or console messages; and
- a fresh screenshot at desktop and mobile widths for review.

Continuous controls are prohibited on X3; all states are discrete and fully
precomputed.

---

## 12. Exact owned files

The X3 track exclusively owns:

```text
docs/superpowers/plans/2026-07-10-external-manager-x3-universe.md
docs/ideas/specs/x3-manager-universe.md
src/quant_allocator/flagships/universe_coverage/__init__.py
src/quant_allocator/flagships/universe_coverage/model.py
src/quant_allocator/flagships/universe_coverage/audit.py
src/quant_allocator/flagships/universe_coverage/coverage.py
src/quant_allocator/flagships/universe_coverage/funnel.py
src/quant_allocator/flagships/universe_coverage/receipts.py
src/quant_allocator/flagships/universe_coverage/validation.py
src/quant_allocator/demo_data/x3_truth.py
src/quant_allocator/demo_data/x3_universe.py
tests/flagships/universe_coverage/__init__.py
tests/flagships/universe_coverage/test_audit.py
tests/flagships/universe_coverage/test_coverage.py
tests/flagships/universe_coverage/test_funnel.py
tests/flagships/universe_coverage/test_receipts.py
tests/flagships/universe_coverage/test_validation.py
tests/demo_data/test_x3_universe.py
site/data/x3_universe.json
site/templates/pages/x3-universe.html.j2
site/assets/pages/x3.css
site/assets/x3-universe.js
tests/site/test_x3.py
```

The card track must not edit:

```text
src/quant_allocator/evidence/**
src/quant_allocator/demo_data/__main__.py
site/cards.yaml
src/quant_allocator/site/build.py
site/templates/base.html.j2
site/templates/demo.html.j2
site/templates/index.html.j2
site/assets/gallery.css
site/assets/gallery.js
site/assets/interval.css
tests/site/test_build.py
tests/site/test_manifest.py
tests/site/test_gallery.py
any cross-card registry or shared fixture
```

If page-local CSS needs a global design token not yet present, use an existing
token or request the seam owner to add one; do not edit global CSS.

---

## 13. Implementation tasks and commits

### Task 0 — independent plan and substrate gate

- [ ] An adversarial reviewer checks the global-denominator refusal, entity
  hierarchy, target-grid denominator, source shapes, queue precedence, attestation
  ceilings, provisional constants, and overlap with S7/E3/E4/P7.
- [ ] The evidence reviewer confirms a later corrected Phase-2 tip—not
  `1112d69`—has passed unconditional review and exposes the required membership,
  entity-mapping, canonical-relationship, target-grid,
  `project_funnel_opportunities`, `project_funnel_schemas`,
  `project_funnel_cohorts`, the one ruled
  `project_funnel_cohort_evaluations`/`project_funnel_cohort_memberships` API,
  `project_funnel_events`, typed opportunity/assignment receipts, and no
  card-local storage or knowledge-time inputs.
- [ ] The seam owner supplies the exact `x3_evidence_v1` fixture hook and pinned
  digests requested in section 14.3; X3 does not begin with a copied fixture.
- [ ] The integration owner records rulings in this plan and the progress ledger.
- [ ] If either review fails, stop; do not scaffold the card.

Commit any approved plan-ruling edits alone:
`docs(x3): record universe coverage method rulings`.

### Task 1 — method spec and failing contract tests

- [ ] Write `docs/ideas/specs/x3-manager-universe.md` with the motivating sourcing
  problem, entity hierarchy, source-conditioned estimands, queue method, formula
  interpretation, access/attestation table, synthetic design, validation, page
  contract, and binding section 8 rulings.
- [ ] Write the smallest failing model/resolution/coverage/funnel tests first.
- [ ] Pin forbidden APIs and output keys for global coverage and manager ranking.
- [ ] Pin exact exclusion visibility, denominator labels, and refusal precedence.
- [ ] Run the targeted tests and confirm failure for missing implementation.

Commit: `test(x3): pin source-conditioned universe coverage contract`.

### Task 2 — shared-projection consumption and universe coverage core

- [ ] Implement immutable domain types with timezone-aware UTC validation.
- [ ] Consume shared mapping and relationship outcomes; reject any card-local
  resolver/projection path and keep ambiguous/unresolved outcomes visible.
- [ ] Implement entity-type-safe canonical counts and target-cell observation.
- [ ] Implement leave-one-source-out novelty and excluded-row reconciliation.
- [ ] Emit reconstruction receipts from slice/composite/join/bundle digests and
  typed included/excluded/refused references.
- [ ] Test order invariance, duplicate evidence preservation, hierarchy conflicts,
  time boundaries, and denominator reconciliation.
- [ ] Run focused pytest and ruff.

Commit: `feat(x3): source-conditioned entity and coverage core`.

### Task 3 — event-sourced funnel and queue logic

- [ ] Implement valid event transitions, opportunity-cohort construction, exact
  stage counts, right-censor checks, and Wilson intervals.
- [ ] Implement count-only refusal below the denominator gate.
- [ ] Implement the categorical research-cell queue and binding reason precedence.
- [ ] Plant invalid, revised, accepted-only, sparse, and repeated-opportunity tests.
- [ ] Prove that performance data cannot enter the queue API.
- [ ] Run focused pytest and ruff.

Commit: `feat(x3): event-sourced funnel coverage and work queue`.

### Task 4 — card-local truth validation and leakage suite

- [ ] Add only the card-local hidden-universe and labelled-pair truth tables,
  cross-checking every key against `x3_evidence_v1`.
- [ ] Implement entity precision/recall Wilson intervals and fallback gate.
- [ ] Implement synthetic-only discovery recall with exact numerator/denominator.
- [ ] Add every planted leakage/refusal case in section 7.3.
- [ ] Prove early snapshots exclude future rows/mappings/taxonomies/revisions and
  differ from the latest-restated view.
- [ ] Run focused tests and ruff; obtain independent arithmetic re-derivation.

Commit: `feat(x3): point-in-time discovery validation and refusals`.

### Task 5 — deterministic generator and held JSON

- [ ] Generate all precomputed cutoff/source/scope states through the real method
  and shared evidence APIs, consuming but never regenerating the shared fixture.
- [ ] Independently re-derive every displayed exact count, set difference, Wilson
  interval, queue reason, and receipt digest in generator tests.
- [ ] Assert fictional-name uniqueness across every committed JSON file.
- [ ] Assert no private/licensed source content, free-form internal comments, or
  prohibited manager-ranking/global-denominator fields enter JSON.
- [ ] Assert finite JSON, deterministic key ordering, two-build byte identity, and
  equality to the held committed JSON.
- [ ] Assert the exact 27 state keys and prove every claim's multi-source receipt
  uses AND semantics over its required dataset slices.
- [ ] Hold JSON for independent numerics/copy/attestation review; never hand-edit.

Commit after the gate: `feat(x3): deterministic universe and funnel exhibit data`.

### Task 6 — page, interactions, and focused site tests

- [ ] Write the server-rendered page, page-local CSS, and precomputed-state JS.
- [ ] Render every required disclosure, receipt, exclusion, refusal, attestation,
  validation state, `What this exhibit shows`, method link, and go-live condition.
- [ ] Provide accessible table alternatives and 44px controls.
- [ ] Write one-card fixture-manifest tests that do not edit shared seams.
- [ ] Pin the binding disclaimer and absence of ranking/global-coverage language.
- [ ] Test that each control changes visual and textual evidence and JS performs no
  estimators.
- [ ] Run `node --check`, targeted site tests, and ruff where applicable.

Commit: `feat(x3): source-conditioned sourcing coverage exhibit`.

### Task 7 — spec reconciliation and track handoff

- [ ] Reconcile spec section 5 only to actual committed JSON results; do not tune
  the generator toward teaching values.
- [ ] Add a dated reconciliation note and constant/result delta docket.
- [ ] Confirm JSON is unchanged after spec reconciliation.
- [ ] Run bounded regression commands in section 15.
- [ ] Produce the complete handoff in section 16.

Commit: `docs(x3): reconcile universe exhibit to reviewed output`.

---

## 14. Shared-seam integration handoff

The integration owner, not the X3 track, adds the generator registry entry,
manifest row, gallery counts, and common fixture hooks.

### 14.1 Generator registry

```python
from quant_allocator.demo_data import x3_universe

"x3_universe": x3_universe.build,
```

### 14.2 Manifest row

```yaml
- id: x3
  title: Manager-universe & sourcing-funnel coverage map
  lane: X
  one_liner: See which target cells the named sources and funnel represent, without inventing a global denominator.
  decision_question: Which target cells are represented, unresolved, stale, or still unsearched?
  primary_stage: discover
  stages: [discover, underwrite, govern]
  asset_classes: [cross-asset]
  vehicle_types: [pooled-fund, fund-of-funds, segregated-mandate, drawdown-fund]
  access_contexts: [public, pre-hire-public, shortlisted-nda, internal-governance]
  supported_data_modalities: [documents, filings, operating-data]
  minimum_data_modalities: [filings]
  decision_readiness: data-conditional
  evidence_roles: [operational-analysis, governance-workflow]
  minimum_data: Versioned source membership, canonical entity mapping, target-grid version, receipt times, and funnel events for internal conversion claims.
  validation_status: live-calibration-required
  status: live
  demo: pages/x3-universe.html.j2
  data: x3_universe.json
  spec: x3-manager-universe.md
  claims:
    - id: public_source_membership
      output_type: exact-measurement
      access_contexts: [public]
      access_semantics: exact-per-dataset
      current_attestation: D
      live_attestation_ceiling: A
      validation_status: live-calibration-required
      receipt_required: true
      refusal: The public dataset version, publication time, canonical grain, right, purpose, or reconstruction receipt is missing.
    - id: prehire_source_membership
      output_type: exact-measurement
      access_contexts: [pre-hire-public, shortlisted-nda]
      access_semantics: exact-per-selected-dataset
      current_attestation: D
      live_attestation_ceiling: B
      validation_status: live-calibration-required
      receipt_required: true
      refusal: The selected pre-hire dataset lacks a complete receipted version, field dictionary, right, purpose, or canonical grain.
    - id: entity_resolution_state
      output_type: exact-measurement
      access_contexts: [public, pre-hire-public, shortlisted-nda]
      access_semantics: all-required-per-selected-dataset
      current_attestation: D
      live_attestation_ceiling: B
      validation_status: live-calibration-required
      receipt_required: true
      refusal: A required shared mapping or relationship projection, typed reference, entity grain, or dataset right is absent or ambiguous.
    - id: target_cell_observation
      output_type: exact-measurement
      access_contexts: [public, pre-hire-public, shortlisted-nda, internal-governance]
      access_semantics: all-required-per-dataset
      current_attestation: D
      live_attestation_ceiling: B
      validation_status: live-calibration-required
      receipt_required: true
      refusal: Any selected source or target-grid dataset lacks its exact right, purpose, complete version, shared projection, included/excluded cell receipt, or bundle join receipt.
    - id: source_union_novelty
      output_type: exact-measurement
      access_contexts: [public, pre-hire-public, shortlisted-nda, internal-governance]
      access_semantics: all-required-per-dataset
      current_attestation: D
      live_attestation_ceiling: B
      validation_status: live-calibration-required
      receipt_required: true
      refusal: Any selected source fails its dataset-specific access or the sources differ in cutoff, entity grain, taxonomy, completeness, join rule, or receipt coverage.
    - id: funnel_stage_counts
      output_type: exact-measurement
      access_contexts: [internal-governance]
      access_semantics: all-required-per-dataset
      current_attestation: D
      live_attestation_ceiling: B
      validation_status: live-calibration-required
      receipt_required: true
      refusal: Opportunity, funnel-schema, cohort, cohort-assignment, event, completeness, absence, right, purpose, or observation-window evidence is incomplete; only labelled extract counts may remain.
    - id: funnel_conversion
      output_type: interval
      access_contexts: [internal-governance]
      access_semantics: all-required-per-dataset
      current_attestation: D
      live_attestation_ceiling: B
      validation_status: live-calibration-required
      receipt_required: true
      refusal: Any opportunity, funnel-schema, cohort, cohort-assignment, event, completeness, absence, right, purpose, window, or denominator gate fails.
    - id: research_cell_queue
      output_type: verdict
      access_contexts: [public, pre-hire-public, shortlisted-nda, internal-governance]
      access_semantics: all-required-per-dataset
      current_attestation: D
      live_attestation_ceiling: C
      validation_status: live-calibration-required
      receipt_required: true
      refusal: Any selected source, eligible target cell, entity grain, completion stage, queue reason, right, purpose, or typed exclusion receipt is not explicitly versioned.
    - id: synthetic_entity_recall
      output_type: interval
      access_contexts: [public]
      access_semantics: synthetic-fixture-only
      current_attestation: D
      live_attestation_ceiling: D
      validation_status: synthetic-demo-verified
      receipt_required: true
      refusal: The card-local truth labels do not exactly reconcile to the pinned shared fixture or the Wilson gate cannot be independently reproduced.
    - id: synthetic_discovery_recall
      output_type: exact-measurement
      access_contexts: [public]
      access_semantics: synthetic-fixture-only
      current_attestation: D
      live_attestation_ceiling: D
      validation_status: synthetic-demo-verified
      receipt_required: true
      refusal: A complete authored hidden-universe denominator is unavailable or the output is requested as a live/global claim.
    - id: global_universe_coverage
      output_type: refusal
      access_contexts: [public, pre-hire-public, shortlisted-nda, internal-governance]
      access_semantics: refusal-in-every-context
      current_attestation: D
      live_attestation_ceiling: D
      validation_status: synthetic-demo-verified
      receipt_required: true
      refusal: The global manager and product denominator is unknown.
    - id: manager_quality_ranking
      output_type: refusal
      access_contexts: [public, pre-hire-public, shortlisted-nda, internal-governance]
      access_semantics: refusal-in-every-context
      current_attestation: D
      live_attestation_ceiling: D
      validation_status: synthetic-demo-verified
      receipt_required: true
      refusal: X3 prioritizes research cells and never ranks manager quality.
  golive:
    data_ask: Per-dataset rights, purposes, complete version manifests and exact absence rules; shared entity, relationship, membership and grid projections; and complete opportunity, funnel-schema, cohort, cohort-assignment and event evidence with typed bundle receipts.
    sample: Exact source and eligible-cell counts have no minimum; conversion intervals require at least 20 eligible opportunities in the disclosed complete cohort, while the synthetic entity precision gate requires at least 381 accepted true-positive links and zero false positives.
    effort: L
```

`access_semantics` is a required Wave-A manifest-schema seam. For
`all-required-per-dataset`, the claim is authorized only when every selected
dataset request passes its own right, access context, licence purpose, and
retention policy; the displayed `access_contexts` list is not OR authorization.
`exact-per-selected-dataset` means the one selected dataset's exact context is
required, not every alternative context in the list. Refusal claims remain
visible in every listed context. Manifest tests derive page access badges from
these claim rows and fail a missing visible claim or omitted semantic.

If the seam owner's controlled modality list does not permit `operating-data` for
internal funnel events, the seam owner must add a dedicated controlled
`governance-events` modality or record a reviewed mapping. X3 must not silently
mislabel funnel events as documents.

### 14.3 Required shared-fixture and schema seam

Before X3 implementation, the integration/evidence owner supplies a shared,
tested fixture hook outside X3 ownership:

```python
fixture = build_evidence_fixture("x3_evidence_v1")
```

The returned manifest must expose `fixture_id`, schema version, fictional-name
attestation, base seed and named stream tags, ordered dataset IDs, dataset-version,
source-content, and reconstruction-manifest digests, expected/received partitions,
version completeness, delivery/absence semantics,
rights/purposes, canonical entities/relationships, and final fixture digest. It
must include source-shaped public-adviser, public-registered-fund,
public-holdings-filer, strategy-export, RFI/DDQ, target-grid,
funnel-opportunity, funnel-schema, funnel-cohort, and funnel-event
datasets. Shared tests, not X3, certify ingestion, unchanged-row observations
across full vintages, projections, rights, typed references, and byte stability.

The same seam registers or confirms:

- the exact later evidence-tip SHA and unconditional review PASS; dataset-version
  `delivery_mode` is only `full-snapshot | delta`, absence semantics are only
  `not-inferable | full-snapshot-means-removed | explicit-tombstone-only`, and any
  bundle-level `mixed` label is derived rather than stored or requested;
- corrected canonical `manager`, `adviser`/`legal-entity`, `strategy`,
  `composite`, `vehicle`, `share-class`, and `mandate` types plus effective-dated
  relationship projections;
- `x3-source-union-v1` and `x3-funnel-cohort-v1` declared join policies with typed
  join receipts and composite/bundle digests;
- typed opportunity, funnel-schema, cohort, cohort-evaluation/membership, and event
  projections including immutable opportunity ID, schema-contained transition and
  reason dictionaries, entity grain, completeness, inclusion/exclusion, censoring,
  and window fields;
- the manifest `access_semantics` field and controlled values shown in section
  14.2; and
- a fixture handoff docket containing exact builder path, test path, fixture
  digest, dataset IDs, right IDs, licence purposes, projection schema IDs, and
  unresolved limitations.

X3 supplies only sorted truth-label keys in `x3_truth.py`; it does not copy or
extend the shared fixture. Missing any item above blocks Task 1.

### 14.4 Expected integration deltas

- Wave A integration adds X3 as the first of seven new rows; the site total moves
  from 20 toward 27 only at the Wave A seam commit.
- `PYTHONPATH=src uv run python -m quant_allocator.demo_data build x3_universe`
  becomes valid after registry integration.
- The release harness derives page counts from the manifest; no X3 track changes a
  hard-coded page total.

---

## 15. Verification commands

Run in the foreground and in bounded groups:

```bash
uv run pytest tests/flagships/universe_coverage/test_audit.py \
  tests/flagships/universe_coverage/test_coverage.py \
  -m "not slow and not network" -q

uv run pytest tests/flagships/universe_coverage/test_funnel.py \
  tests/flagships/universe_coverage/test_validation.py \
  -m "not slow and not network" -q

uv run pytest tests/demo_data/test_x3_universe.py \
  -m "not slow and not network" -q

uv run pytest tests/site/test_x3.py \
  -m "not slow and not network" -q

uv run ruff check src/quant_allocator/flagships/universe_coverage \
  src/quant_allocator/demo_data/x3_universe.py \
  tests/flagships/universe_coverage tests/demo_data/test_x3_universe.py \
  tests/site/test_x3.py

node --check site/assets/x3-universe.js
```

After integration, the integration owner additionally runs:

```bash
PYTHONPATH=src uv run python -m quant_allocator.demo_data build x3_universe
PYTHONPATH=src uv run python -m quant_allocator.site build
uv run pytest tests/site/test_manifest.py tests/site/test_build.py \
  tests/site/test_gallery.py tests/site/test_x3.py \
  -m "not slow and not network" -q
```

The independent reviewer re-runs the method arithmetic from raw fixture rows,
not from rendered JSON totals.

---

## 16. Independent review, publication, and handoff gates

### 16.1 Independent card review

A reviewer who did not implement X3 must:

- re-derive entity precision/recall intervals, source set differences, target-cell
  counts, funnel cohorts, Wilson intervals, queue precedence, and receipt hashes;
- explicitly re-derive the Wilson perfect-precision threshold
  \(\lceil 0.99(1.96)^2/(1-0.99)\rceil=381\), then recompute the emitted confusion
  matrix bounds from raw truth labels;
- inspect point-in-time snapshots for every planted leakage case;
- confirm no global denominator or manager-quality ranking survives in API, JSON,
  HTML, alt text, metadata, or copy;
- confirm public/pre-hire/internal source claims stay within their access and
  attestation ceilings;
- confirm synthetic validation is never generalized to live discovery recall;
- check every formula and binding refusal in the rendered method spec; and
- docket every provisional constant, deviation, and unresolved live-calibration
  item.

The implementer cannot self-certify these gates.

### 16.2 Handoff report

The X3 track ends with:

```text
commits
owned-file diff
targeted tests and exact results
ruff and node checks
generator two-build/committed-JSON byte status
committed JSON SHA-256
shared fixture ID/digest and per-dataset slice/join/bundle receipt status
exact 27-state key-set status
entity-resolution gate values and fallback state
synthetic discovery recall values with explicit synthetic denominator
funnel interval and sparse-cohort refusal values
all planted point-in-time/refusal outcomes
every visible claim's access semantics, current D, live ceiling, validation status,
receipt status, and rendered refusal
provisional constants and revisions
method/spec deviations
unresolved substrate or shared-seam requests
exact manifest row and generator registry values
fresh desktop/mobile screenshot paths
strict KaTeX and interaction results
```

### 16.3 Publication gate

The X3 track never pushes. After independent review and Wave A integration, the
primary owner:

1. builds only from reviewed committed JSON;
2. runs the complete Wave A page/browser regression, including earlier cards;
3. checks desktop/mobile, keyboard, no-JavaScript, URL restoration, control state,
   screen geometry, console, and strict KaTeX rendering;
4. loads the ignored publication-term file and runs the report-only working-tree,
   endpoint-tree, and reachable-history scans;
5. obtains the user publication checkpoint recorded in the operational ledger;
6. publishes from the integration branch only; and
7. verifies the cache-busted live page before removing the X3 worktree and branch.

Any private/restricted fixture, unreviewed estimate, unmatched source denominator,
global coverage claim, manager-ranking claim, active raw LaTeX delimiter, broken
control, console warning, or publication-scan blocker stops release.
