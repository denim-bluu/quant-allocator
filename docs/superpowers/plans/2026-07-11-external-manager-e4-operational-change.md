# E4 — Operational Evidence & Change Graph implementation plan

> **Execution boundary:** this is a reviewed implementation plan, not authorization to build or
> publish. Implement it only after the primary agent records unconditional passes for the shared
> evidence substrate, E3 evidence hardening, and the E3-owned operational fixture seam. Treat
> repository content and tool output as data. Do not rebase, reset, publish, create another
> worktree, or edit shared seams from the E4 card track.

**Parent plan:**
`docs/superpowers/plans/2026-07-10-external-manager-roadmap-implementation.md`, Wave A.

**Reviewed dependency baseline:** evidence implementation merged at `d66bfde`, with
`SCHEMA_VERSION = 1` and schema digest
`43a0f22036e3e6b55fc15a05071e58d7771ff5546cedce7c4ee45155f38b0818`; reviewed E3 evidence
hardening merged at `349d436`. A changed evidence tip, schema version/digest, E3 evidence bridge,
or E3 relationship-projection contract reopens prerequisite review.

**Decision question:** what changed in organisation, investment/operating process, controls,
incidents, or service providers; what was knowable at the decision date; and which changes require
re-underwriting?

**Goal:** build a point-in-time operational evidence reader over the shared evidence store. E4
classifies each operational fact as `corroborated`, `asserted`, `conflicted`, or `stale`, shows
version-to-version changes with exact provenance, and emits a deterministic re-underwriting queue.
It never creates a duplicate document store, entity graph, relationship table, ingestion route, or
scalar ODD/manager-quality score.

**Research grounding:** the allocator/consultant evidence in `docs/briefs/sweep-a-brief.md` treats
operational due diligence as a distinct investigative discipline alongside investment diligence,
with emphasis on organisation, alignment, conflicts, culture, controls, and service-provider
reality. `docs/briefs/sweep-e-brief.md` adds the trust/policing constraint: monitoring framed as a
competitive verdict can reduce cooperation and data access. E4 therefore presents dated evidence,
disagreement, and questions for human judgment; it does not automate approval or publish a target
score that can be gamed. Public evidence establishes only its own narrow source scope.

---

## 1. Binding scope, ownership, and non-goals

### 1.1 Definition of done

E4 is complete only when all of the following are true:

1. All source records, content versions, observations, rights, spans, canonical entities, and
   effective-dated relationships are ingested and owned by the reviewed shared evidence/E3 seam.
2. E4 requests real `DatasetSliceRequest` and `SnapshotBundleRequest` objects, using actual right,
   access-context, licence-purpose, retention, revision, valid-time, join-key, and join-policy
   fields. It does not accept caller-authored `known_at` or substitute file modification times.
3. Analytic and audit bundles are separate: `latest-known` drives the displayed state while
   `all-known-versions` exposes revisions and future-known divergence at each cutoff.
4. Every admitted fact has one canonical entity, explicit temporal shape, exact evidence item and
   span, observation/version/right lineage, and an E3-owned canonical relationship where the fact
   is an edge.
5. Null/unresolved canonical rows remain visible in one-source audits but cannot enter a
   multi-source join, operational state count, change graph, or queue.
6. Changes are differences between admissible point-in-time versions—not text similarity, inferred
   dates, missing rows under unknown absence semantics, or a comparison with current truth.
7. `corroborated`, `asserted`, `conflicted`, and `stale` are deterministic evidence states with
   visible rules and provenance. They are not risk ratings.
8. Provider, control, incident, organisation, and process changes are represented without reducing
   them to one score. The queue is a ruled action bucket with stable tie-breaking, not a manager
   ranking.
9. Every displayed fact, date, state, change, exclusion, refusal, and queue item has current
   attestation D and a persisted, verifier-compatible receipt pointing to the exact JSON output.
10. A deterministic synthetic exhibit covers public-only, shortlisted-manager, independent
    corroboration, conflict, staleness, explicit removal, unversioned, inferred-date, null-key, and
    pre-delivery cases without private names or data.
11. The method page, interactive page, responsive layouts, keyboard path, accessibility tree,
    strict LaTeX rendering, and committed JSON pass independent review.

### 1.2 Sole-owner boundaries

- **Shared evidence substrate** owns source identity, immutable items/revisions, dataset versions,
  observations/partitions, rights, snapshots, receipts, mappings, entities, and relationships.
- **E3** is the sole document/evidence ingestion owner and sole owner of canonical document/entity/
  span/relationship provenance and graph projections. The operational fixture extension is an E3
  task reviewed before E4 starts.
- **E4** owns only the operational ontology, fact normalization over admitted evidence, temporal
  diff, evidence-state classification, staleness policy, and re-underwriting queue.
- **X3** owns manager/product universe membership. **S7** owns track-record lineage. **P4** owns
  contractual terms. **M8** owns covenant migration. E4 may link their reviewed evidence IDs but
  cannot reproduce their estimators or storage.

If a required operational item, span, entity, relationship, right, version, or observation is
missing, stop and return the exact E3/shared-fixture seam requirement. Do not add a card-local
SQLite table or hidden registry.

### 1.3 Explicit non-goals and forbidden shortcuts

E4 does **not**:

- emit an ODD score, pass/fail diligence verdict, hire/fire recommendation, manager rank, or
  weighted sum of operational indicators;
- claim a control is effective merely because a policy or DDQ says it exists;
- infer an event/effective date from file name, modification time, document order, meeting date,
  retrieval date, or narrative tense;
- convert absence into removal unless a complete version's ruled absence semantics permit it or an
  explicit tombstone exists;
- use website/news/social sentiment, scrape live pages, or treat repeated copies as independent
  corroboration;
- mutate shared evidence, create a second graph/store/resolver, or copy E3 text into E4 records;
- let hidden validation truth enter shared/live-shaped evidence payloads, fixture manifests,
  bundles, receipts, source labels, or production-shaped outputs;
- recompute evidence estimators in JavaScript or expose bare evidence points without a state/verdict
  chip and source boundary.

---

## 2. Prerequisite and shared-fixture gate

No E4 implementation task begins until the primary agent records:

1. `d66bfde`, schema version 1, and the pinned schema digest are present and independently passed.
2. `349d436` is present: E3 binds documents through `as_known_bundle`, persists verifiable empty
   slice/join receipts, resolves display provenance from evidence spans, and makes every authored
   graph edge a validated projection of one canonical `entity_relationship`.
3. The E3 owner has supplied and independently reviewed the operational fixture seam below.
4. The manifest supports claim-level `access_semantics`; E4 may not silently omit that field.
5. All publication canaries and fictional-name checks pass in the seam's exact diff and reachable
   history.

### 2.1 Required E3-owned operational fixture seam

The E3 owner—not E4—delivers a separate reviewed seam commit owning exactly:

```text
src/quant_allocator/flagships/knowledge/operational_evidence.py
tests/flagships/test_knowledge_operational_evidence.py
```

Its public API is pinned:

```python
E4_OPERATIONAL_FIXTURE_ID = "e4_operational_evidence_v1"
E4_OPERATIONAL_FIXTURE_DOMAIN = b"quant-allocator/e4-operational-fixture/v1\0"

@dataclass(frozen=True, slots=True)
class OperationalBundleManifest:
    cutoff_key: str
    source_view: str
    bundle_kind: str
    dataset_id: str | None
    revision_mode: str
    include_unresolved: bool
    slice_digests: tuple[str, ...]
    slice_receipt_ids: tuple[str, ...]
    join_receipt_id: str
    bundle_digest: str

@dataclass(frozen=True, slots=True)
class OperationalSourceSchemaManifest:
    dataset_id: str
    payload_schema_id: str
    schema_version: int
    field_dictionary_version: str
    schema_sha256: str
    manager_entity_id_pointer: str
    domain_pointer: str
    subject_entity_id_pointer: str
    predicate_pointer: str
    scope_pointer: str
    typed_value_pointer: str
    temporal_type_pointer: str
    effective_at_pointer: str
    effective_from_pointer: str
    effective_to_pointer: str
    source_available_at_pointer: str
    freshness_at_pointer: str
    source_family_pointer: str
    independence_group_pointer: str
    assertion_kind_pointer: str
    incident_materiality_pointer: str

@dataclass(frozen=True, slots=True)
class OperationalRightManifest:
    dataset_id: str
    evidence_right_id: str
    right_series_id: str
    right_version: int
    access_context: str
    licence_purpose: str
    status: str
    retention_policy: str
    received_at_utc: datetime
    entitlement_from: datetime
    entitlement_to: datetime | None
    supersedes_right_id: str | None

@dataclass(frozen=True, slots=True)
class OperationalEvidenceManifest:
    fixture_id: str
    fixture_digest: str
    evidence_schema_version: int
    evidence_schema_digest: str
    e3_reviewed_tip: str
    disclosure: str
    current_attestation: str
    ordered_dataset_ids: tuple[str, ...]
    source_order_digest: str
    cutoff_items: tuple[tuple[str, str], ...]
    source_view_items: tuple[tuple[str, tuple[str, ...]], ...]
    source_schema_manifests: tuple[OperationalSourceSchemaManifest, ...]
    right_manifests: tuple[OperationalRightManifest, ...]
    row_ids_by_table: tuple[tuple[str, tuple[str, ...]], ...]
    content_digests: tuple[tuple[str, str], ...]
    reconstruction_digests: tuple[tuple[str, str], ...]
    bundle_manifests: tuple[OperationalBundleManifest, ...]
    independence_items: tuple[tuple[str, str, str], ...]
    limitation_codes: tuple[str, ...]
    unresolved_ids: tuple[str, ...]

@dataclass(frozen=True, slots=True)
class OperationalEvidenceFixture:
    conn: sqlite3.Connection
    manifest: OperationalEvidenceManifest
    source_requests: Mapping[str, DatasetSliceRequest]

def build_operational_evidence_fixture() -> OperationalEvidenceFixture: ...
def operational_source_bundle(
    fixture: OperationalEvidenceFixture,
    *,
    dataset_id: str,
    decision_at: datetime,
    revision_mode: str,
    include_unresolved: bool,
) -> SnapshotBundle: ...

def operational_verification_bundle(
    fixture: OperationalEvidenceFixture,
    *,
    selected_dataset_ids: tuple[str, ...],
    decision_at: datetime,
    revision_mode: str,
    include_unresolved: bool,
) -> SnapshotBundle: ...
```

`bundle_kind` is exactly `one-source` or `verification-envelope`; a one-source row has one
`dataset_id`, while an envelope row has `dataset_id=None`. Source schemas sort by dataset ID;
rights sort by `(dataset_id, right_series_id, right_version, evidence_right_id)`; `cutoff_items`,
view items, all ID maps, bundle manifests, independence items, limitations, and unresolved IDs are
sorted tuples with duplicate-key rejection. The fixture digest is exactly:

```python
sha256(
    E4_OPERATIONAL_FIXTURE_DOMAIN
    + canonical_bytes(asdict(replace(manifest, fixture_digest="")))
)
```

It must equal `manifest.fixture_digest`, be lowercase 64-hex, and remain byte-identical under
database insertion-order permutations. The digest formula and every manifest field above are part
of the reviewed API; E4 may not accept an ad hoc mapping with a matching-looking digest.
`e3_reviewed_tip` is the non-circular dependency value `349d436`; the later seam commit is recorded
separately in the execution docket and cannot be embedded in the tree it hashes.

Every dataset has one digest-bound typed source-schema manifest. Schema identity/version is exact:

| Dataset | `payload_schema_id` | Version | Source availability pointer |
|---|---|---:|---|
| `dataset:e4-public-registry` | `schema:e4-public-registry-operational-v1` | 1 | `/source_time/published_at` |
| `dataset:e4-manager-documents` | `schema:e4-manager-documents-operational-v1` | 1 | `/source_time/received_at` |
| `dataset:e4-control-evidence` | `schema:e4-control-evidence-operational-v1` | 1 | `/source_time/received_at` |
| `dataset:e4-independent-references` | `schema:e4-independent-references-operational-v1` | 1 | `/source_time/received_at` |
| `dataset:e4-operational-policy` | `schema:e4-operational-policy-v1` | 1 | `/source_time/published_at` |

All five use `field_dictionary_version="e4-operational-v1"`. The remaining normalized-field
pointers are exact and identical across the five manifests:

```text
manager_entity_id       /fact/manager_entity_id
domain                  /fact/domain
subject_entity_id       /fact/subject_entity_id
predicate               /fact/predicate
scope                   /fact/scope
typed_value             /fact/typed_value
temporal_type           /temporal/temporal_type
effective_at            /temporal/effective_at
effective_from          /temporal/effective_from
effective_to            /temporal/effective_to
freshness_at            /fact/freshness_at
source_family           /fact/source_family
independence_group      /fact/independence_group
assertion_kind          /fact/assertion_kind
incident_materiality    /fact/incident_materiality
```

Controlled values are binding:

```text
temporal_type:
  point | interval

source_family:
  manager-document | public-regulatory-record | provider-confirmation |
  control-test | reference-record | method-policy

assertion_kind:
  current-state-assertion | change-assertion | control-existence-assertion |
  control-effectiveness-assertion | incident-notice | remediation-assertion |
  closure-assertion | method-boundary-policy
```

Public-registry rows use `public-regulatory-record`; manager documents use
`manager-document`; control evidence uses `provider-confirmation` or `control-test` according to
the authored source; independent references use `reference-record`; and policy evidence uses
`method-policy`. A copied record retains the originating source family as well as its originating
independence group. Source family does not itself prove independence.

Every pointer key is present in every operational payload. Inactive point/interval fields and
non-incident materiality are explicit JSON nulls, not missing keys. For an incident, null
materiality is the planted missing case and normalizes to controlled `unknown`; other incident
values are exactly `critical`, `material`, or `non-material`. `source_available_at_pointer` names
the source publication/receipt component. The normalized `available_at` remains the shared-store
maximum of that value and every applicable right, observation, version, and embargo time; E4 never
trusts a payload-authored final known-at value. A claim receipt points to the exact source-time
pointer and also carries the typed right/version references that close the derived maximum.

Payload `temporal_type` must equal stored `evidence_item.temporal_type`: `point` requires non-null
`effective_at` and null interval endpoints; `interval` requires null `effective_at`, non-null
`effective_from`, and a null or strictly later `effective_to`. Payload effective values must equal
the corresponding stored evidence-item columns exactly after UTC normalization. `source_family`
and `assertion_kind` are required non-null controlled strings and are never inferred from dataset
name, publisher, document title, or prose.

`schema_sha256` must equal the stored `payload_schema.schema_sha256` recomputed from its canonical
schema JSON. The schema requires the pointer tree and exact primitive/null unions, controlled
domains, temporal types, source families, independence groups, assertion kinds, and incident
materiality values above. Changing a schema ID, version, digest, field dictionary, pointer,
required key, or enum changes the fixture digest and reopens seam review.

Every evidence right is represented by one `OperationalRightManifest` mirroring the complete
stored `EvidenceRightRecord`: dataset and evidence-right ID, right series and integer version,
access context, licence purpose, status, retention policy, UTC receipt time, half-open entitlement
interval, and superseded-right link. The typed `datetime` values serialize through
`canonical_bytes` as `YYYY-MM-DDTHH:MM:SSZ`. There is
no separate `licence_purpose_items` map and no dataset-to-right shortcut: all active, expired,
revoked, wrong-purpose, and superseding planted records appear as distinct typed manifests.

The seam review records the exact commit and 64-hex `manifest.fixture_digest` in this plan and the
progress ledger before E4 Task 1. Until those two literals replace the execution docket's
`UNRECORDED` state, E4 is explicitly **not implementation-ready**; no placeholder digest or locally
rebuilt fixture is accepted. The manifest digest binds the canonical contract, every row/content/
span/version/partition/reconstruction/projection ID, source-order digest, rights, one-source bundle
digests/receipts, verification-envelope digests/receipts, and limitations.

The immutable fixture manifest exposes only live-shaped identifiers and metadata:

- fixture ID/digest, evidence schema version/digest, E3 reviewed tip, disclosure, and current D;
- ordered dataset IDs; typed source-schema IDs/versions/digests/pointers; and complete typed right
  records including series/version, access, purpose, status, retention, and entitlement interval;
- source-record, content, evidence-item/span, version, expected/received partition,
  reconstruction-manifest, observation, mapping, entity, and relationship IDs/digests;
- exact analytic/audit/one-source-empty slice, join, and bundle digests/receipt IDs for each ruled
  cutoff and access view;
- exact verification-envelope slice, join, and bundle digests/receipt IDs for each ruled cutoff,
  access view, revision mode, and unresolved flag;
- source-family and independence metadata used by corroboration, with its source span;
- known limitations and all unresolved rows.

It must not expose expected E4 classifications, change labels, queue buckets, or hidden truth.
Expected synthetic outcomes live only in E4-owned tests and are never imported by the generator.

Source independence is ruled, not open-ended. `independence_group` is one of
`manager-self`, `public-regulator`, `provider-direct`, `independent-control-test`, or
`independent-reference`. A copied/quoted/derived record inherits its originating group even when a
different document or publisher carries it. Two manager documents remain one group. Provider-
direct evidence is independent of manager-self for provider identity/appointment only; it does not
independently attest control effectiveness. Independence metadata is itself an E3 evidence field
with exact span; missing/ambiguous group refuses corroboration.

The six ruled views are exact. `public-only` selects, in order,
`dataset:e4-public-registry` and `dataset:e4-operational-policy` under access context `public`.
`all-entitled` selects all five datasets in the table below, in table order, under access context
`shortlisted-nda`; every source request still carries its own right and minimum context. Both
helpers reject any dataset order, cutoff, revision mode, unresolved flag, access context, right, or
purpose that differs from the manifest's ruled request.

The seam authors public/synthetic source shapes rather than real documents:

| Dataset | Availability | Lowest access | Modeled shape |
|---|---|---|---|
| `dataset:e4-public-registry` | `public-publication` | `public` | dated adviser/legal/provider filings and public regulatory notices |
| `dataset:e4-manager-documents` | `manager-receipt` | `shortlisted-nda` | versioned DDQs, org charts, process/policy documents, incident notices |
| `dataset:e4-control-evidence` | `manager-receipt` | `shortlisted-nda` | synthetic control reports, test summaries, administrator/custodian confirmations |
| `dataset:e4-independent-references` | `manager-receipt` | `shortlisted-nda` | synthetic reference-call/meeting records with explicit source-family identity |
| `dataset:e4-operational-policy` | `public-publication` | `public` | authored E4 method-boundary and refusal policy evidence |

Each dataset has its own right and purpose `e4-research`; no right is reused across datasets.
Rights pin access context, status, entitlement interval, and retention policy. Public sources use
publication/first-observed time; manager/control/reference sources use receipt time. Embargoes and
right boundaries are explicit UTC half-open intervals.

The seam creates canonical manager, adviser/legal entity, person/team, organisation unit,
strategy, service provider, control, process, incident, and document entities as required. Every
operational edge is inserted once into `entity_relationship` with full typed machine ID,
evidence item/span, dataset version/observation, relation type, source/target entities, temporal
shape, effective interval, version, and revision link. Any reader graph is a pure all-edge
projection that validates relation type, endpoints, and span, following the `349d436` contract.

Required relationship types include:

```text
manager --managed-or-advised-by--> adviser/legal entity
manager --employs--> person/team
manager|strategy --uses-provider--> administrator/custodian/auditor/prime broker
manager|strategy --operates-process--> operational process
process --governed-by--> control
control --tested-by--> control-evidence document
incident --affected--> manager|provider|process|control
document --asserts-operational-fact--> operational subject
```

The fixture must contain real revision and absence shapes, not three identical snapshots labelled
as vintages: unchanged observations across full snapshots; changed and new items; explicit
tombstone delta; `full-snapshot-means-removed`; `not-inferable`; one incomplete partition;
effective-dated relationship revisions; right/embargo boundaries; a later correction; and a
complete zero-row pre-delivery version/partition so shared empty slice and join receipts persist and
verify. Full IDs, foreign-key closure, machine-ID triggers, reconstruction, idempotence, row-order
invariance, and digest stability are independently tested by E3.

The seam test file must additionally prove, from stored rows rather than manifest self-report:

1. there is exactly one source-schema manifest per ordered dataset; each ID, version, field-
   dictionary version, and recomputed schema digest equals the stored `payload_schema` and every
   operational `evidence_item.payload_schema_id`/`field_dictionary_version`;
2. every declared JSON pointer exists in the stored schema and resolves against every associated
   payload, including explicit nulls; normalized fact identity/value/temporal type/effective time/
   freshness/source family/independence/assertion kind/materiality values equal those payload
   values, while temporal type and effective columns equal the corresponding stored
   `evidence_item` columns;
3. each normalized `available_at` exactly equals the shared-store derivation, its declared source-
   time pointer resolves to the contributing publication/receipt value, and later right/version/
   embargo components are not bypassed;
4. every `OperationalRightManifest` field equals the corresponding stored `evidence_right` row,
   every source request uses that exact dataset/right/access/purpose combination, entitlement is
   half-open at both boundaries, and supersession/revocation/wrong-purpose cases select or refuse
   exactly as ruled;
5. every E4 fixture slice, join, composite, policy, exclusion, and refusal receipt reference uses
   the manifest's exact `source_schema_id` and `source_field` pointer, and every
   `evidence-right` reference names the typed right manifest reachable from its dataset version and
   evidence item; field-level coverage explicitly includes `temporal_type`, `source_family`, and
   `assertion_kind`; and
6. deleting or altering any schema manifest, pointer, schema digest, right field, stored row,
   temporal type, source family, assertion kind, controlled enum, or corresponding receipt
   reference fails verification and changes/rejects the fixture digest.

No E4 implementation may compensate for a missing pointer, infer a schema from payload examples,
or reconstruct a right manifest from rendered JSON.

---

## 3. Point-in-time request and receipt contract

### 3.1 Actual shared requests

The shared `as_known_bundle` computes intersection keys across sources; it is not a union engine.
Operational sources therefore use separately persisted, verified one-source bundles:

```python
analytic_bundles = tuple(
    operational_source_bundle(
        fixture,
        dataset_id=dataset_id,
        decision_at=decision_at,
        revision_mode="latest-known",
        include_unresolved=False,
    )
    for dataset_id in selected_dataset_ids
)

audit_bundles = tuple(
    operational_source_bundle(
        fixture,
        dataset_id=dataset_id,
        decision_at=decision_at,
        revision_mode="all-known-versions",
        include_unresolved=False,
    )
    for dataset_id in selected_dataset_ids
)

unmatched_audit_bundles = tuple(
    operational_source_bundle(
        fixture,
        dataset_id=dataset_id,
        decision_at=decision_at,
        revision_mode="all-known-versions",
        include_unresolved=True,
    )
    for dataset_id in selected_dataset_ids
)
```

Each helper creates a real one-source `SnapshotBundleRequest` with the source request's exact
dataset/access/right/purpose/ruled half-open review window, `join_keys=("evidence_item_id",)`, and
`join_policy="e4-one-source-v1"`, then calls `as_known_bundle`. Primary analytic/audit source
requests differ only by `revision_mode`; unmatched audit bundles are a separately receipted ledger.
E4 never hand-builds a shared bundle or labels an intersection receipt as union.

`operational_verification_bundle` is the only multi-source bundle used by E4. It calls
`as_known_bundle` with the same source requests, `join_keys=("evidence_item_id",)`, and
`join_policy="e4-verification-envelope-v1"`. Evidence-item IDs are dataset-unique, so the shared
join is intentionally an empty intersection. Its persisted slice/join/bundle receipts are a
**verification envelope only**: they prove the shared verifier's reachable-source denominator and
must never be rendered, counted, or described as an analytic join or union. Tests prove every
cross-source item is excluded by that intersection receipt. The separately persisted E4 composite
receipt below is the sole union claim. The envelope uses `as_known_bundle`'s canonical dataset-ID
ordering; the E4 composite separately binds the section-2.1 selected-source order.

E4 forms its unique-fact set in card-local pure code from the ordered one-source slices and emits a
persisted **E4 composite/union claim receipt** using shared `make_receipt`/`store_receipt`. Its input
digest binds every source bundle/slice digest, actual one-source join receipt ID, selected source
order, cutoff, access view, and algorithm `e4-operational-composite-union/v1`. Typed snapshot and
included/excluded evidence references prove the union; the card-local verifier checks all closure
before shared verification. This receipt is not a `SnapshotBundle` and does not invent a shared
join policy.

Exact-date equality is not a corroboration rule. E4 compares normalized fact keys and explicit
effective intervals after source retrieval. Canonical-null rows remain typed `unmatched`
one-source audit exclusions. Two null rows with identical label/date in different datasets never
match or enter a state/count.

### 3.2 Temporal ordering and diff

The shared store derives `available_at`. E4 applies:

1. right/licence/embargo and dataset-version availability at `decision_at`;
2. complete partition/reconstruction gate;
3. latest accessible item revision per source record for analytic mode;
4. valid-time filtering using half-open intervals `[effective_from,effective_to)`;
5. unique canonical mapping and relationship closure;
6. operational fact normalization and diff.

An operational fact key is:

```text
(manager_entity_id, domain, subject_entity_id, predicate, scope)
```

Its value remains typed text/enum/date/identifier from the evidence payload; E4 does not copy the
source document. A `ChangeRecord` is admitted only when two accessible versions of the same fact
key differ in typed value, effective interval, relationship endpoint, or explicit status. Removal
requires an explicit tombstone or a complete full snapshot with
`full-snapshot-means-removed`. `not-inferable` absence creates no change.

If the source lacks an explicit effective date/interval, E4 emits `inferred-date-refused`. It may
show receipt/publication time separately but cannot substitute it as effective time. An unversioned
snapshot can support a current assertion but cannot support a change claim; it emits
`unversioned-change-refused`.

### 3.3 Receipts and strengthened card-local closure

E4 builds receipts only with shared `make_receipt`/`store_receipt` and validates them with the
unchanged shared `verify_receipt`. Typed references include, as applicable, evidence item/span,
source record, observation/version/partition link, right, mapping, entity relationship, and
snapshot. The actual join-receipt ID and bundle digest are bound through the canonical parameters
and input digest because the shared reference enum has no join-receipt/bundle reference kind.

E4 **must** strengthen closure with this card-local preflight; no E4 call site may invoke the shared
verifier directly:

```python
def verify_operational_receipt(
    conn: sqlite3.Connection,
    *,
    receipt_id: str,
    source_bundles: tuple[SnapshotBundle, ...],
    verification_bundle: SnapshotBundle,
    closure: OperationalClaimClosure,
) -> None: ...
```

`OperationalClaimClosure` is constructed from immutable method output, not rendered JSON. Its
canonical parameter payload is exactly:

```text
algorithm_version, decision_at, access_view, output_pointer,
ordered_source_bundles[{dataset_id,slice_digest,slice_receipt_id,
                        join_receipt_id,bundle_digest}],
verification_envelope{join_receipt_id,bundle_digest},
composite_union_input_digest, method_constants_digest
```

Its exact reference multiset contains one `snapshot` per source slice; for every included,
excluded, or refused fact, its `source-record`, `evidence-item`, `evidence-span`,
`dataset-observation`, `dataset-version`, and `evidence-right`; and, where applicable, its
`entity-mapping` and `entity-relationship`. Every reference uses the concrete claim output pointer,
ruled source-schema pointer, included/excluded/refused disposition, and controlled
input/filter/refusal role. No missing, duplicate, surplus, or differently typed ID is accepted.
For every emitted normalized field, the multiset contains field-level item/span references whose
`source_schema_id` and `source_field` equal that dataset's typed schema manifest entry; a generic
`/` pointer cannot stand in for a declared field. Effective and availability fields additionally
bind the dataset-version/right references that govern their stored values. The wrapper rejects a
receipt that has row-level lineage but omits any normalized-field pointer.

The preflight must:

- require the exact bundle request, slice digests, persisted snapshot manifests, and actual
  source `bundle.join_receipt_id`/`bundle_digest` values;
- require the verification envelope to contain exactly the same slice identities/digests and
  request fields in canonical dataset-ID order, prove its join receipt is the ruled empty
  intersection, and bind its actual join receipt/bundle digest;
- require exact header, output schema, output pointer, algorithm/version, D attestation, reference
  set, roles, dispositions, and source-schema pointers;
- prove span-to-item, observation-to-item/version, version-to-right, relationship-to-span/
  endpoints, and snapshot-to-slice closure against the supplied bundle;
- recompute canonical parameters/input digest and reject missing, surplus, tampered, or
  out-of-bundle IDs;
- then call `verify_receipt(conn, receipt_id, verification_bundle)` exactly once. No call site may
  substitute a one-source bundle, a hand-built bundle, or a rendered-JSON reconstruction.

This is additive claim closure, not a second receipt format or a weaker verifier. All positive and
negative E4 receipt tests call the wrapper. `build_operational_output` calls it for every fact,
state, change, queue, exclusion, and refusal before returning; the generator asserts those calls
completed before serialization. A refusal still needs reachable typed policy/empty-
bundle evidence; zero-reference receipts are forbidden because the shared verifier rejects them.

---

## 4. Operational ontology and immutable interfaces

Implement frozen, slot-based types under
`src/quant_allocator/flagships/operational_change/`:

```python
@dataclass(frozen=True, slots=True)
class OperationalFact:
    fact_id: str
    manager_entity_id: str
    domain: str
    subject_entity_id: str
    predicate: str
    scope: str
    typed_value: str
    temporal_type: str
    effective_at: datetime | None
    effective_from: datetime | None
    effective_to: datetime | None
    source_family: str
    independence_group: str
    assertion_kind: str
    evidence_item_id: str
    evidence_span_id: str
    dataset_observation_id: str
    dataset_version_id: str
    evidence_right_id: str
    entity_relationship_id: str | None

@dataclass(frozen=True, slots=True)
class ChangeRecord:
    change_id: str
    fact_key: tuple[str, str, str, str, str]
    change_kind: str
    before_fact_id: str | None
    after_fact_id: str | None
    effective_at: datetime
    first_known_at: datetime
    receipt_id: str

@dataclass(frozen=True, slots=True)
class EvidenceState:
    fact_key: tuple[str, str, str, str, str]
    state: str
    supporting_fact_ids: tuple[str, ...]
    conflicting_fact_ids: tuple[str, ...]
    as_of: datetime
    reason_codes: tuple[str, ...]
    receipt_id: str

@dataclass(frozen=True, slots=True)
class ReunderwritingItem:
    queue_id: str
    action_bucket: str
    domain: str
    fact_key: tuple[str, str, str, str, str]
    question: str
    reason_codes: tuple[str, ...]
    evidence_state_receipt_id: str
```

Controlled domains are `organisation`, `process`, `control`, `provider`, and `incident`.
Controlled change kinds are `added`, `modified`, `explicitly-removed`, `relationship-started`,
`relationship-ended`, and `corrected`. Controlled refusals/exclusions are named constants; free
text never controls logic.

---

## 5. Evidence states, staleness, and queue rules

### 5.1 Independence and state precedence

Copies, extracts, and summaries derived from one original have the same `independence_group` and
count once. Independence is E3-owned source metadata with evidence provenance, not inferred from
publisher names.

For one fact key at the cutoff:

1. `conflicted` if two admissible, temporally overlapping current facts assert incompatible typed
   values and neither is a known revision/correction of the other;
2. `stale` if no conflict exists and the newest required refresh exceeds the domain threshold;
3. `corroborated` if at least two compatible facts come from at least two independent groups and
   the domain-specific source requirement is met;
4. `asserted` for one or more compatible facts from only one independent group.

Conflict precedence prevents two opposing assertions from being called corroborated. Staleness is
an evidence-age state, not evidence that a control failed. A later correction changes only
snapshots at or after its availability.

Corroboration requires `E4_MIN_INDEPENDENT_GROUPS = 2`. For a control-effectiveness statement, at
least one supporting fact must be a control-test/independent confirmation; two manager-authored
documents can corroborate existence but not effectiveness. For an incident closure, at least one
fact must evidence remediation/closure, not merely repeat the incident notice.

### 5.2 Staleness arithmetic

The exact age is:

\[
A_f(t)=\operatorname{days}\left(t-\max_{i\in I_f}\operatorname{freshness\_at}_i\right).
\]

Interpretation: `I_f` is the evidence for fact `f` that was available by `t`, while
`freshness_at` is the explicit source as-of/test/refresh date defined by that source schema. A late
receipt of an old control test remains old; `available_at` gates knowability but does not reset
freshness. Missing or inferred freshness time emits `staleness-unknown` rather than stale/current.
Display the exact age, threshold, and state chip together—never a bare estimated risk.

Binding `e4-operational-state/v1` thresholds are:

| Domain | `E4_STALE_DAYS` |
|---|---:|
| organisation | 180 |
| process | 180 |
| control | 365 |
| provider | 365 |
| incident | 90 |

Boundary semantics are exact: age equal to the threshold is current; stale begins at
`age_days > threshold`. These constants govern the synthetic protocol and any v1 output. A live
policy change requires a new reviewed method version; E4 never estimates a threshold from outcomes.

### 5.3 Re-underwriting queue without a score

Queue buckets are categorical:

- `immediate-clarification`: conflicts; open incidents explicitly classified `critical` or
  `material`; incidents with `materiality=unknown`; missing/incompatible provider or control
  relationships;
- `scheduled-reunderwrite`: explicit provider, organisation, process, or control changes, plus an
  open incident explicitly classified `non-material`;
- `evidence-refresh`: stale facts;
- `no-action-from-e4`: corroborated/asserted facts with no admitted change.

The first applicable bucket wins. Within a bucket sort by domain control order, explicit effective
date, then stable fact/change ID. There is no numeric priority score and no cross-manager rank.
Questions are controlled templates populated only with fictional entity labels and exact dates.

Incident `materiality` is a required controlled source field with values `critical`, `material`,
`non-material`, or `unknown`; it is evidence, not an E4 estimate. An open `non-material` incident
enters `scheduled-reunderwrite`, while closed incidents with no other trigger enter
`no-action-from-e4`. Missing materiality is normalized to `unknown` and requires clarification.

---

## 6. Access, claims, attestation, and refusals

| Claim ID | Output pointer | Output | Access contexts | Access semantics | Current | Live ceiling | Binding refusal |
|---|---|---|---|---|---|---|---|
| `public_operational_facts` | `/facts` | evidence-graph | public, pre-hire-public | all-required-per-selected-dataset | D | C | no public source/version/right for requested cutoff |
| `operational_change_graph` | `/changes` | evidence-graph | shortlisted-nda, funded-commingled, funded-private-partnership, segregated-mandate | all-required-per-selected-dataset | D | B | unversioned or inferred-date source; incomplete lineage |
| `operational_evidence_state` | `/state_summary` | verdict | shortlisted-nda, funded-commingled, funded-private-partnership, segregated-mandate | all-required-per-selected-dataset | D | B | unresolved entity, right, independence, or conflicting temporal shape |
| `reunderwriting_queue` | `/reunderwriting_queue` | exact-measurement | shortlisted-nda, funded-commingled, funded-private-partnership, segregated-mandate | all-required-per-selected-dataset | D | B | underlying state/change receipt fails |
| `operational_data_boundary_refusals` | `/refusals/data-boundary` | refusal | public, pre-hire-public, shortlisted-nda, funded-commingled, funded-private-partnership, segregated-mandate | refusal-per-inadmissible-input | D | D | any access, partition, lineage, temporal, identity, independence, absence, or null-key gate refuses |
| `operational_method_boundary_refusal` | `/refusals/method-boundary` | refusal | public, pre-hire-public, shortlisted-nda, funded-commingled, funded-private-partnership, segregated-mandate | refusal-in-every-context | D | D | E4 never emits a scalar ODD score, clean/approve, hire/fire, recommendation, or manager ranking |
| `synthetic_state_validation` | `/validation` | exact-measurement | public | synthetic-fixture-only | D | D | hidden expected outcomes do not exactly reconcile |

Public-only output is source-conditioned and normally `asserted`; it cannot imply complete ODD.
Manager claims under `shortlisted-nda` remain manager-asserted unless an independent source family
supports them. No synthetic D result is promoted to B/C merely because it is reproducible.

Refuse before rendering when: the right is unknown/revoked/wrong-purpose; a complete version or
partition is missing; an item/span/observation chain is broken; effective time is inferred;
change is requested from one unversioned snapshot; mapping/relationship is unresolved or
ambiguous; null keys would join; independence metadata is absent; absence semantics are
insufficient; or a caller requests a scalar score, clean/approve verdict, hire/fire decision,
recommendation, or manager rank. The one method-boundary refusal above is visible and receipted in
every interaction state. Every triggered data-boundary refusal is visible and receipted at the
exact `/refusals/data-boundary/{refusal_id}` pointer; it names the controlled reason and affected
source/fact ID without exposing source text. Prohibited outputs never receive separate hidden
booleans.

---

## 7. Synthetic design and adversarial cases

Hidden case labels exist only in `tests/flagships/operational_change/fixtures.py`. The seam test
independently re-derives the held aggregate counts from authored rows, but no expected label, state,
queue bucket, or pass flag is installed with the package, returned by the fixture, or read by the
generator.

The reviewed E3 seam plants three cutoffs (`early`, `middle`, `latest`), two source views
(`public-only`, `all-entitled`), five domains, and these binding cases:

| ID | Case | Exact expected outcome |
|---|---|---|
| E4-P1 | complete zero-row pre-delivery version | empty slice/join receipts persist and verify |
| E4-P2 | manager process change plus provider-direct confirmation | `modified`, then `asserted`; provider-direct is not independent corroboration for a process fact |
| E4-P3 | manager and public filing name incompatible providers for the same stable relationship-owner key | `conflicted`; immediate clarification |
| E4-P4 | organisation chart and independent reference name incompatible team leads on one complete key | `conflicted`; immediate clarification |
| E4-P5 | org chart received later with earlier explicit effective date | absent early; visible later with both dates |
| E4-P6 | org change date inferred from filename/narrative | `inferred-date-refused`; no change |
| E4-P7 | one unversioned source assertion | current assertion allowed; change refused |
| E4-P8 | control policy repeated in two manager documents | existence may corroborate by groups only if independent; effectiveness remains asserted/refused |
| E4-P9 | independent reference supports control existence while a separately versioned control test refreshes effectiveness evidence | existence `corroborated`; effectiveness remains its own state |
| E4-P10 | incident notice, independent open-status evidence, remediation, later correction, and a separate open incident with null materiality | latest incompatible current assertions are `conflicted`; null materiality normalizes to `unknown` and requires immediate clarification even when stale; early snapshot remains unchanged |
| E4-P11 | old incident evidence beyond 90-day threshold | exact stale boundary: day 90 current, day 91 stale |
| E4-P12 | missing row under `not-inferable` | no removal/change |
| E4-P13 | explicit tombstone | `explicitly-removed` at tombstone availability only |
| E4-P14 | ended provider relationship at exact boundary | excluded at `effective_to`; half-open semantics |
| E4-P15 | identical null-key labels/dates across datasets | each remains an unmatched audit exclusion; no join/state/count |
| E4-P16 | source copies share independence group | count once; never false corroboration |
| E4-P17 | incomplete expected partition | refuse diff/state/queue |
| E4-P18 | access/right/licence mismatch | refuse before content read |
| E4-P19 | attempted clean verdict/scalar score | unconditional receipted refusal |
| E4-P20 | row-order and insertion-order permutations | identical bundle/state/queue/JSON bytes |
| E4-P21 | ambiguous operational-subject mapping | typed exclusion; no arbitrary fact/state/queue row |
| E4-P22 | independence metadata missing or ambiguous | corroboration refused; assertion remains visible if otherwise admissible |
| E4-P23a | mapping revision first known after cutoff | absent early; later audit shows exact effective/known dates; no retroactive remap |
| E4-P23b | relationship revision first known after cutoff | absent early; later audit shows exact effective/known dates; no retroactive edge |
| E4-P24 | member disappears from a complete `full-snapshot-means-removed` version | positive removal at version availability with partition/reconstruction receipt; identical omission from an incomplete full snapshot refuses |

### 7.1 Held synthetic state gate

Before JSON release, the authored latest/all-entitled fixture must reconcile exactly to:

- 16 admitted underlying latest-known analytic facts. The method-boundary policy fact is receipt
  evidence rather than a manager operational state, and compatible source facts share a complete
  operational key, so the state layer has exactly 10 current keys: 1 corroborated, 3 asserted,
  3 conflicted, and 3 stale;
- 4 `immediate-clarification`, 4 `scheduled-reunderwrite`, and 2 `evidence-refresh` queue items;
- zero joined canonical-null rows, zero inferred-date changes, zero unversioned change claims, and
  zero scalar-score/ranking fields;
- every displayed edge has one canonical relationship ID and exact evidence span;
- every output pointer and count reconciles to a verified receipt.

These are provisional fixture design constants, not teaching outputs to force. If the real
pipeline differs, stop, inspect the fixture/method, docket the cause, and obtain independent
approval before changing the fixture or this plan. Never hand-edit JSON or hard-code a pass flag.

---

## 8. Deterministic generator and JSON contract

`e4_operational_change.build(out_dir=SITE_DATA_DIR)` consumes only the reviewed fixture hook and
real shared/E4 APIs. Top-level JSON:

```text
meta
evidence
state_summary
facts
changes
relationships
reunderwriting_queue
refusals
validation
interaction_states
claim_receipts
```

`evidence` includes schema/fixture digest, decision cutoff, access view, dataset/right/purpose,
slice/join/bundle/claim receipt IDs, record counts, and limitations. Facts carry IDs and resolved
display provenance; source document text remains in the evidence store. JSON contains no hidden
truth, private content, NaN/Infinity, unordered sets, browser-side estimator inputs, or local paths.

Stable ordering is state precedence/domain/fact key/fact ID for facts; effective date/change ID for
changes; action bucket/domain/date/ID for queue items. Two clean builds and input-order
permutations must be byte-identical. Hold and docket the exact SHA-256. Regeneration must use the
real generator; never edit `site/data/e4_operational_change.json` by hand.

---

## 9. Reader experience, interactions, and rendering

The page leads with the decision answer, not the graph:

1. evidence-boundary banner: cutoff, source view, access, current D, limitations;
2. four state counts with definitions and refusal count;
3. change timeline grouped by operational domain;
4. accessible evidence graph plus equivalent fact/relationship table;
5. re-underwriting queue with exact questions and provenance drawers;
6. method/refusal/go-live section.

### 9.1 Interaction contract

JavaScript only switches among committed precomputed states and maps committed nodes to pixels. It
does not classify facts, compute staleness, infer changes, join data, or generate queue priority.

The generator emits exactly six base interaction states:

```text
early|public-only       early|all-entitled
middle|public-only      middle|all-entitled
latest|public-only      latest|all-entitled
```

Each `interaction_states[key]` has this finite schema:

```text
key, cutoff, source_view, access_context, selected_dataset_ids,
source_bundle_receipts[{dataset_id,slice_digest,slice_receipt_id,
                        join_receipt_id,bundle_digest}],
composite_union_receipt_id, state_counts, refusal_count,
fact_ids, change_ids, relationship_ids, queue_ids, exclusion_ids,
data_boundary_refusal_ids, method_boundary_refusal_id, refusal_ids,
claim_receipt_ids
```

There are exactly **six precomputed state keys**, sorted lexically and tested for exact equality;
unknown keys fail closed. The cutoff/source-view controls choose one committed state. The following
are display-only filters over IDs already present in that state and may not alter counts,
classification, receipts, refusal membership, or queue:

- domain: all / organisation / process / control / provider / incident;
- evidence state: all / corroborated / asserted / conflicted / stale;
- view: timeline / graph / table.

The finite UI contract is therefore `6 x 6 x 5 x 3 = 540` addressable combinations, but only the
six cutoff/source-view bases are data states; JavaScript filters their committed ID lists. Test all
six base keys, every display-filter value, every refusal boundary, graph/table equivalence, and all
540 addressable combinations for membership-only filtering. URL query state, reload/back-forward, direct links,
clear/reset, empty result, and no-JS full-table fallback are binding. Updates use `aria-live=polite`;
native buttons use `aria-pressed`; focus stays on the changed control; provenance drawers are
keyboard operable and restore focus.

### 9.2 LaTeX, accessibility, and responsive QA

The method spec uses strict LaTeX for the age function and any set notation. Assert no raw
`\(`, `\)`, `\[`, `\]`, `$$`, command text, or duplicate rendering remains after build; KaTeX/
MathJax emits zero console errors/warnings and formulas remain readable at 320px.

Browser QA covers 320, 390, 768, and 1440px; no horizontal overflow; 44px controls; minimum
12–14px important text; visible focus; skip-link clearance; non-colour state labels; graph nodes
with accessible names; table headers/scope; reduced-motion behavior; 200% zoom; light/dark contrast;
and screen-reader order matching the visual decision flow. The graph may scroll inside a labelled
region only if the full equivalent table remains directly accessible.

---

## 10. Card-track ownership

The E4 track may edit only:

```text
docs/ideas/specs/e4-operational-evidence-change.md
src/quant_allocator/flagships/operational_change/**
src/quant_allocator/demo_data/e4_operational_change.py
tests/flagships/operational_change/**
tests/demo_data/test_e4_operational_change.py
site/data/e4_operational_change.json
site/templates/pages/e4-operational-evidence-change.html.j2
site/assets/pages/e4-operational-evidence-change.css
site/assets/e4-operational-evidence-change.js
tests/site/test_e4_operational_evidence_change.py
```

It must not edit `src/quant_allocator/evidence/**`, E3 files, shared fixtures, `site/cards.yaml`,
the generator registry, global templates/assets, gallery counts, or cross-card registries. The E3
fixture seam is delivered and reviewed in a separate owner commit before E4 Task 1.

---

## 11. Test-first implementation tasks and commits

### Task 0 — prerequisite and fixture review

- [ ] Record evidence/E3 tips, schema version/digest, fixture hook/digest, exact rights/purposes,
  relationship counts, empty-receipt verification, limitations, and independent PASS.
- [ ] Re-derive all typed source-schema manifests/pointers, typed right manifests, fixture
  populations, version/absence cases, hidden-truth separation, machine IDs, foreign keys,
  reconstruction, joins, receipt references, and deterministic digest from raw rows.
- [ ] Stop on any conditional pass or unreviewed E3 seam extension.

No E4 code commit.

### Task 1 — method spec and failing contract tests

- [ ] Write the E4 method spec: motivating ODD problem, evidence boundary, ontology, PIT ordering,
  state/queue rules, formulas with term interpretation, access/attestation matrix, synthetic design,
  refusals, page contract, and binding section-8 rulings.
- [ ] Write the smallest failing model/state/diff/receipt tests first.
- [ ] Pin controlled enums, exact output pointers, forbidden score/rank/clean keys, caller-time
  rejection, hidden-truth import prohibition, immutable types, both visible refusal collections,
  and the queue's `exact-measurement` claim type.
- [ ] Confirm tests fail for missing E4 implementation.

Commit: `test(e4): pin operational change contract`.

### Task 2 — pure normalization and temporal diff

- [ ] Normalize admitted shared rows to immutable `OperationalFact` values without copying text.
- [ ] Implement PIT ordering, explicit-date gate, revision diff, half-open intervals, explicit
  removal, and not-inferable absence behavior.
- [ ] Preserve unmatched/unresolved one-source exclusions and exact reconciliation.
- [ ] Test inferred date, unversioned change, late correction, tombstone, relationship end,
  incomplete partition, right boundary, null join, and row-order cases.

Commit: `feat(e4): reconstruct point-in-time operational changes`.

### Task 3 — evidence states, queue, and receipts

- [ ] Implement independence-group handling and exact state precedence.
- [ ] Implement domain staleness thresholds/boundaries and categorical queue rules.
- [ ] Build persisted claim/refusal receipts with exact typed references and pointers.
- [ ] Implement `verify_operational_receipt` preflight over the exact one-source bundles and ruled
  empty-intersection verification envelope, then call the unchanged shared verifier exactly once.
- [ ] Test missing/tampered/out-of-bundle item/span/observation/version/right/relationship/snapshot/
  join/bundle/pointer failures and duplicate-copy non-corroboration.
- [ ] Independently re-derive the held state/queue gate.

Commit: `feat(e4): classify operational evidence and queue reunderwriting`.

### Task 4 — deterministic generator and held JSON

- [ ] Generate every committed interaction state through real APIs.
- [ ] Pin exactly six precomputed base keys, the exact per-state schema, and all 540 display-only
  URL combinations without emitting another data state or browser-side classification input.
- [ ] Assert current D/live ceiling, access semantics, receipt closure, finite canonical JSON,
  exact counts, protected hidden-truth boundary, two-build identity, and held SHA.
- [ ] Run generator determinism tests after every data change.
- [ ] Hold JSON for independent numerics/identity/copy review; never hand-edit.

Commit only after gate: `feat(e4): generate held operational change exhibit`.

### Task 5 — page, CSS, JavaScript, and focused QA

- [ ] Build answer-first page, timeline, graph/table equivalence, queue, provenance, disclosures,
  method link, synthetic disclosure, tier badge, go-live requirements, and
  `What this exhibit shows` section.
- [ ] Implement only precomputed-state switching and geometry in JavaScript.
- [ ] Test all discrete states, named pairwise combinations, refusal boundaries, URL/history,
  keyboard/focus/ARIA, no-JS fallback, strict LaTeX, responsive geometry, and console cleanliness.
- [ ] Run `node --check` and targeted site build/tests.

Commit: `feat(e4): render operational evidence change graph`.

### Task 6 — independent gate, reconciliation, and handoff

- [ ] Independent reviewer re-derives every fact/state/change/queue count, threshold boundary,
  receipt pointer, relationship closure, and rendered claim from raw fixture rows.
- [ ] Reconcile method-spec concrete results to actual generated output; do not edit ruled method
  obligations to excuse a failing pipeline.
- [ ] Run bounded evidence/E3/E4 pytest groups, scoped Ruff, generator twice, site build, node check,
  browser matrix, strict LaTeX, link/accessibility/console checks, and publication scan.
- [ ] Produce handoff docket: commits, owned diff, tests, fixture/schema/JSON digests, exact state/
  queue results, ruled method constants, refusals, claim access/attestation, deviations, limitations,
  and shared-seam values.

No self-certification. Fixes receive focused commits and repeat independent review.

---

### Task 7 — integration-owner manifest, registry, and gallery seam

Only the primary integration owner edits these shared files, in one commit after the reviewed E4
tip is merged:

```text
src/quant_allocator/site/build.py
src/quant_allocator/demo_data/__main__.py
site/cards.yaml
tests/demo_data/test_cli.py
tests/site/test_manifest.py
tests/site/test_build.py
```

- [ ] Extend `CLAIM_KEYS` with mandatory `access_semantics`. The shared controlled set is exactly
  `exact-per-dataset`, `exact-per-selected-dataset`, `all-required-per-dataset`,
  `all-required-per-selected-dataset`, `refusal-per-inadmissible-input`,
  `refusal-in-every-context`, and `synthetic-fixture-only`, preserving the reviewed X3 values and
  adding only E4's per-inadmissible-input value. Add an explicitly reviewed semantic to every
  production claim in `site/cards.yaml`; never production-default it. Update only the explicit
  legacy-test upgrader with `all-required-per-selected-dataset`; reject missing, unknown, empty, or
  mistyped values in production manifests.
- [ ] Add `e4_operational_change` to both the import and builder map in
  `demo_data.__main__`; extend `tests/demo_data/test_cli.py` so single-card and sorted `build all`
  execution call it exactly once.
- [ ] Append the exact E4 manifest row below. Do not rename claims, weaken access, omit semantics,
  or promote current D.
- [ ] Integrate this row with the other six reviewed Wave-A rows. Refactor any stale hard-coded
  20-card assertion so the release count is derived from the strict manifest and resolves to 27 for
  the complete batch; never land an E4-only transient count. Add the exact E4 title, link, decision
  question, evidence context, seven claim IDs, output types, and D/B/C ceilings.
- [ ] Run manifest rejection tests, CLI registry tests, the strict site build, and a shared-seam
  diff review before commit.

```yaml
- id: e4
  title: Operational evidence & change graph
  lane: E
  one_liner: Reconstruct dated operational facts and route evidence gaps without a scalar ODD score.
  decisions: [engage, monitor, select]
  tiers: [R, E, P]
  status: live
  decision_question: What operationally changed, what evidence supports it, and what requires re-underwriting now?
  primary_stage: underwrite
  stages: [underwrite, monitor, govern]
  asset_classes: [cross-asset]
  vehicle_types: [pooled-fund, segregated-mandate, drawdown-fund]
  access_contexts: [public, pre-hire-public, shortlisted-nda, funded-commingled, funded-private-partnership, segregated-mandate]
  supported_data_modalities: [documents, filings, holdings, mandate-terms]
  minimum_data_modalities: [documents]
  decision_readiness: data-conditional
  evidence_roles: [operational-analysis, governance-workflow]
  minimum_data: Versioned operational documents and filings with explicit effective and receipt times, canonical entity mappings and relationships, per-dataset rights, independence spans, delivery completeness, and reconstruction receipts.
  validation_status: live-calibration-required
  claims:
    - id: public_operational_facts
      output_type: evidence-graph
      access_contexts: [public, pre-hire-public]
      access_semantics: all-required-per-selected-dataset
      current_attestation: D
      live_attestation_ceiling: C
      validation_status: live-calibration-required
      receipt_required: true
      refusal: No admissible public source version and right exists at the requested cutoff.
    - id: operational_change_graph
      output_type: evidence-graph
      access_contexts: [shortlisted-nda, funded-commingled, funded-private-partnership, segregated-mandate]
      access_semantics: all-required-per-selected-dataset
      current_attestation: D
      live_attestation_ceiling: B
      validation_status: live-calibration-required
      receipt_required: true
      refusal: A source is unversioned, effective time is inferred, or lineage and delivery closure are incomplete.
    - id: operational_evidence_state
      output_type: verdict
      access_contexts: [shortlisted-nda, funded-commingled, funded-private-partnership, segregated-mandate]
      access_semantics: all-required-per-selected-dataset
      current_attestation: D
      live_attestation_ceiling: B
      validation_status: live-calibration-required
      receipt_required: true
      refusal: Entity, right, independence, temporal shape, or source compatibility is unresolved.
    - id: reunderwriting_queue
      output_type: exact-measurement
      access_contexts: [shortlisted-nda, funded-commingled, funded-private-partnership, segregated-mandate]
      access_semantics: all-required-per-selected-dataset
      current_attestation: D
      live_attestation_ceiling: B
      validation_status: live-calibration-required
      receipt_required: true
      refusal: An underlying state or change receipt fails exact closure.
    - id: operational_data_boundary_refusals
      output_type: refusal
      access_contexts: [public, pre-hire-public, shortlisted-nda, funded-commingled, funded-private-partnership, segregated-mandate]
      access_semantics: refusal-per-inadmissible-input
      current_attestation: D
      live_attestation_ceiling: D
      validation_status: synthetic-demo-verified
      receipt_required: true
      refusal: Every inadmissible access, delivery, lineage, time, identity, independence, absence, or null-key input remains visibly refused.
    - id: operational_method_boundary_refusal
      output_type: refusal
      access_contexts: [public, pre-hire-public, shortlisted-nda, funded-commingled, funded-private-partnership, segregated-mandate]
      access_semantics: refusal-in-every-context
      current_attestation: D
      live_attestation_ceiling: D
      validation_status: synthetic-demo-verified
      receipt_required: true
      refusal: E4 never emits a scalar ODD score, clean or approve verdict, hire or fire decision, recommendation, or manager rank.
    - id: synthetic_state_validation
      output_type: exact-measurement
      access_contexts: [public]
      access_semantics: synthetic-fixture-only
      current_attestation: D
      live_attestation_ceiling: D
      validation_status: synthetic-demo-verified
      receipt_required: true
      refusal: Hidden expected outcomes do not reconcile exactly to the public synthetic fixture.
  demo: pages/e4-operational-evidence-change.html.j2
  data: e4_operational_change.json
  spec: e4-operational-evidence-change.md
  golive:
    data_ask: Permissioned versioned operational sources with effective and receipt times, entity and relationship provenance, independence spans, per-dataset rights, delivery completeness, and reconstruction receipts.
    sample: At least one reviewed live-shaped case per intended source family, revision and absence mode, access context, and planted refusal boundary; this is validation coverage, not an estimator sample threshold.
    effort: L
```

Commit as part of the primary owner's reviewed Wave-A shared-seam commit; the E4 handoff is the
single YAML row, registry entry, and assertions above, not a separate competing edit to the shared
files.

---

## 12. Verification, integration, and publication gate

Bounded commands:

```bash
uv run pytest tests/flagships/operational_change -m "not slow and not network" -q
uv run pytest tests/demo_data/test_e4_operational_change.py -m "not slow and not network" -q
uv run pytest tests/site/test_e4_operational_evidence_change.py -m "not slow and not network" -q
uv run ruff check src/quant_allocator/flagships/operational_change \
  src/quant_allocator/demo_data/e4_operational_change.py \
  tests/flagships/operational_change tests/demo_data/test_e4_operational_change.py
PYTHONPATH=src uv run python -c \
  'from quant_allocator.demo_data.e4_operational_change import build; build()'
PYTHONPATH=src uv run python -m quant_allocator.site build
node --check site/assets/e4-operational-evidence-change.js
```

Before integration, the primary owner verifies the E3 seam commit is already merged, stages only
owned E4 paths, and performs the exact Task-7 manifest/registry/gallery seam separately. E4 does
not claim a later campaign total or edit shared navigation outside that handoff.

Before any push, load ignored publication terms and run the report-only working-tree and reachable-
history scans. Review every hit; the only accepted tracked canary remains the ruled `.gitignore`
entry. Scan exact new commits for real employer/manager/private data and assistant-attribution
trailers. All displayed names remain fictional; all external factual framing links to public
primary sources in the method spec. The primary integration owner alone may push after the user
publication checkpoint, wait for Pages, cache-bust, and repeat live interaction/LaTeX/browser QA.

---

## 13. Execution docket — policy and prerequisite artifacts resolved

There are no open E4 policy decisions. Sections 2, 5, 6, 7, 9, and Task 7 bind the fixture API and
ownership, independence taxonomy, staleness thresholds, incident materiality, refusal outputs,
interaction count, claim output types, and `access_semantics`. Changing any requires an explicit
method-version plan and independent review; an implementer may not treat it as local discretion.

The held-gate correction candidate records these exact artifacts for independent review:

| Artifact | Required recorded value | Current state |
|---|---|---|
| E3 operational seam commit | exact correction implementation tip owning only the section-2.1 source and focused seam test files | `3e61de7e4813f23297dbedf60dc131141cd3e23c` |
| `OperationalEvidenceManifest.fixture_digest` | exact lowercase 64-hex digest recomputed from the correction fixture | `93dcf199bfd33bea857b8fb5439a4d16d2b3e9f98605b3c52ad54b05c51de4f3` |

The held-count reconciliation changes only this method plan and its independent seam oracle. The
fixture source and stored rows remain byte-identical, so the correction implementation tip and
fixture digest above do not change.

The primary agent may replace the progress-ledger prerequisite only after this correction receives
independent review and is merged. Until then the prior reviewed seam remains historical evidence and
the E4 card remains stopped at its held gate. After review, these values become binding prerequisite
evidence; changing either requires a new independently reviewed seam and explicit docket update.
