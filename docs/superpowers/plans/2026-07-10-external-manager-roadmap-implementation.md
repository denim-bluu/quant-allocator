# External-manager roadmap and implementation campaign

> **SUPERSEDED PRODUCT SCOPE — 2026-07-15.** This document is a historical
> implementation record, not an active implementation plan. Its 36-card bitemporal
> platform objective was superseded by the canonical editorial-site charter in
> [`docs/PRODUCT.md`](../../PRODUCT.md). Nothing here blocks website work or becomes
> current unless the user explicitly reauthorizes the product scope and the charter is
> amended.

**Status:** superseded historical plan.

**Baseline:** `main` at `11d8c7f`, 20 live cards, zero planned cards, one
worktree, and a clean published site.

**Goal:** turn the gallery from a method-family catalogue for already-known
managers into a decision-first, point-in-time, multi-asset research system. The
campaign adds the missing underwriting, credit, and private-market methods while
preserving the current numerical, publication, rendering, and interaction gates.

## 1. Scope and definition of done

The campaign is complete only when all of the following are true:

1. Every current and new card declares its decision stages, asset/vehicle scope,
   access context, data modality, decision readiness, evidence role, minimum data,
   claim-specific attestation, validation state, and refusal boundary.
2. The default gallery is a decision journey, with a searchable/faceted catalogue
   as a second view. S/M/P/E/X remain stable internal method families rather than
   the reader's primary navigation.
3. A shared bitemporal evidence layer enforces `available_at <= decision_at` and
   preserves source hashes, revisions, entity lineage, and reconstruction receipts.
4. Sixteen new cards are implemented, independently reviewed, numerically/copy
   gated, and integrated. Together with the existing 20 cards, the site exposes 36
   live cards.
5. Every estimate-bearing output is an interval, a scenario, or an explicit
   refusal. JavaScript switches among committed states and never recomputes an
   estimator.
6. Every method specification renders under strict KaTeX with no active raw
   delimiters, parser failures, errors, or warnings.
7. Every visible control changes the visual and textual evidence it claims to
   control; label-only or ARIA-only changes fail the interaction gate.
8. Desktop/mobile, keyboard, no-JavaScript, URL-state, search, facets, presets,
   empty states, screen geometry, and console gates pass.
9. Publication checks load `tools/.publication_terms` and clear the endpoint tree
   and the publication range under the grandfathered-history policy.
10. The published site is cache-busted and verified, and all campaign branches and
    worktrees are removed.

## 2. Binding product and analytical doctrine

### 2.1 Decision-first information architecture

The six primary stages are:

1. `discover` — Discover opportunities and managers.
2. `underwrite` — Underwrite manager and strategy.
3. `mandate` — Design mandate and terms.
4. `construct` — Construct and fund the portfolio.
5. `monitor` — Monitor and re-underwrite.
6. `govern` — Govern, learn, and attest.

The index defaults to **Journey** and offers **Catalog** as a second view. Cards
render once in the server HTML and remain fully usable without JavaScript. Search,
presets, facets, URL query-state, and history restoration are progressive
enhancements.

### 2.2 Publication state, decision readiness, and evidence role are separate

`status: live` continues to mean only that a page is published. The independent
`decision_readiness` enum is:

- `usable-now`
- `data-conditional`
- `prototype`
- `redesign-required`
- `research-finding`

The independent `evidence_roles` enum is:

- `operational-analysis`
- `governance-workflow`
- `teaching-simulator`
- `negative-result`

The existing 20-card readiness migration is fixed by the research report, with
X2's non-operational teaching boundary made explicit:

- usable-now: S2, M1, P3, E1, E2, X2;
- data-conditional: S1, S3, S4, S5, M4, M6;
- prototype: M2, M3, M5, P1, E3, X1;
- redesign-required: P2;
- research-finding: S6.

X2 is `usable-now` only as a `teaching-simulator`; it never becomes an
operational manager product. All unbuilt cards begin as `data-conditional` or
`prototype`. `validation_status` remains independent of both axes.

### 2.3 Data and evidence doctrine

R/E/P remains a supported-transparency capability ladder, not minimum required
data. New first-class data modalities are `returns`, `documents`, `exposures`,
`holdings`, `trades`, `cashflows-nav`, `operating-data`, `filings`, and
`mandate-terms`.

Access contexts are:

- `public` — public filings or genuinely public datasets;
- `pre-hire-public` — cold prospecting and public manager material;
- `shortlisted-nda` — NDA, RFI, DDQ, and data-room diligence;
- `funded-commingled` — recurring pooled-vehicle reporting;
- `funded-private-partnership` — LP reports, capital notices, and negotiated
  private-market schedules;
- `segregated-mandate` — account-level positions, trades, cash, and guidelines;
- `internal-governance` — allocator decisions, funnels, and evidence rights.

Attestation is claim-specific:

- A — independently reconstructable evidence;
- B — reproducible manager output;
- C — evidence-backed interpretation or disclosed scenario;
- D — illustrative synthetic evidence.

No card may silently convert a C/D result into an A/B finding. Every visible
estimate, scenario, verdict, and refusal belongs to one manifest `claims` entry
with its own output type, access context, current attestation, live attestation
ceiling, validation state, receipt requirement, and refusal condition. A/B outputs
require reconstruction receipts. Rendered badges use `current_attestation`; the
higher ceiling appears only as a go-live capability.

### 2.4 Point-in-time doctrine

The shared evidence envelope contains:

```text
source_system, source_record_id, content_sha256
entity_type, entity_id, manager_id, strategy_id, composite_id
vehicle_id, share_class_id, mandate_id, investment_id
effective_from, effective_to, as_of_date
published_at, received_at_utc, entitlement_from, embargo_until, available_at
version, revision_of, publication_status
dataset_id, dataset_version, universe_membership_id
access_context, evidence_right_id
base_currency, gross_net_fee_basis, valuation_policy_id
benchmark_id, benchmark_version, field_dictionary_version
sensitivity_class, licence_purpose
```

`available_at` is derived, never caller-supplied:

```text
available_at = max(all applicable receipt, entitlement, publication, and embargo times)
```

Public sources use their documented publication or first-observed timestamp;
manager and internal sources use receipt time; licensed sources additionally
respect the evidence right. Every timestamp is timezone-aware UTC. Effective
intervals are half-open: `[effective_from, effective_to)`.

Every historical analysis consumes
`as_known_at(decision_at, access_context, evidence_right_id)`. The query first
filters entitlement, receipt, universe-membership, and effective intervals, then
selects only revisions whose complete revision chain was known by the cutoff.
Canonical snapshot order is dataset, canonical entity ID, field dictionary,
effective interval, available time, version, and evidence item ID.

Missing receipt timestamps, evidence rights, dataset/universe vintages, overwritten
history, unresolved or future revision links, benchmark versions, or canonical
entity keys force refusal rather than an imputed date.

## 3. Stable card identifiers

Existing IDs remain unchanged. New cards retain the existing method-family naming
scheme so implementation internals stay stable while the UI navigates by decision.

Method families remain:

- S — skill, underwriting inference, and implementation quality;
- M — monitoring and early warning;
- P — portfolio construction, mandate economics, and governance;
- E — engagement, knowledge, and evidence consumption;
- X — cross-card infrastructure, discovery coverage, and research doctrine.

| ID | Card | Primary stage | Initial maturity |
|---|---|---|---|
| X3 | Manager-universe & sourcing-funnel coverage map | discover | data-conditional |
| S7 | Track-record provenance inspector | underwrite | data-conditional |
| E4 | Operational evidence & change graph | underwrite | data-conditional |
| P4 | Fee, terms & carry engine | mandate | data-conditional |
| M7 | Liquidity & redemption mismatch lab | underwrite | data-conditional |
| S8 | Strategy fingerprint & peer benchmarker | discover | prototype |
| P5 | Mandate & benchmark design sandbox | mandate | prototype |
| S9 | Private-market cash-flow benchmark | underwrite | data-conditional |
| M8 | Borrower health & covenant migration | monitor | data-conditional |
| M9 | NAV vintage & mark-revision audit | monitor | data-conditional |
| P6 | Calls, distributions & unfunded forecast | construct | prototype |
| P8 | Financing & counterparty common-failure map | construct | data-conditional |
| S10 | Structured-credit waterfall replay | underwrite | prototype |
| S11 | Operating value-creation calibration | underwrite | prototype |
| P7 | Co-investment offer-funnel audit | govern | prototype |
| S12 | Capacity & slippage frontier | underwrite | data-conditional |

The evidence/vintage layer is infrastructure, not a seventeenth card. E3 becomes
its reader-facing document/entity/provenance surface.

## 4. Manifest and gallery contract

After migration, every card requires:

```yaml
decision_question: "..."
primary_stage: underwrite
stages: [underwrite, construct]
asset_classes: [cross-asset]
vehicle_types: [pooled-fund]
access_contexts: [shortlisted-nda, funded-commingled]
supported_data_modalities: [returns, documents]
minimum_data_modalities: [returns]
decision_readiness: data-conditional
evidence_roles: [operational-analysis]
minimum_data: "..."
validation_status: live-calibration-required
claims:
  - id: posterior_interval
    output_type: interval
    access_contexts: [shortlisted-nda]
    current_attestation: D
    live_attestation_ceiling: B
    validation_status: live-calibration-required
    receipt_required: true
    refusal: "Historical vintages or comparable roster are missing."
```

Validation requires non-empty fields, enum membership, no duplicate enum values,
`primary_stage in stages`, unique claim IDs, claim-level access/attestation,
minimum modalities being a subset of supported modalities, and independent
validation of `status`, `decision_readiness`, `evidence_roles`, and
`validation_status`. The builder must allow a published prototype, teaching
simulator, or research finding. Every committed synthetic demo claim has
`current_attestation: D`; A/B may appear only as a separately labelled live
ceiling and require a reconstruction receipt.

Controlled asset classes are `cross-asset`, `public-equity`, `hedge-funds`,
`rates-macro`, `fixed-income-credit`, `structured-credit`,
`private-credit`, `private-equity`, and `real-assets`. Controlled vehicle
types are `pooled-fund`, `fund-of-funds`, `segregated-mandate`,
`drawdown-fund`, `co-investment`, and `public-filing-portfolio`.

Controlled validation states are `synthetic-demo-verified`,
`protocol-ready`, `live-calibration-required`, `redesign-required`, and
`negative-result`. Controlled output types are `exact-measurement`,
`interval`, `scenario-set`, `distribution`, `evidence-graph`, `verdict`,
and `refusal`.

### Index behavior

- Hero: “What are you trying to decide?”
- Six stage jump links with counts.
- Journey/Catalog native-button toggle with `aria-pressed`.
- Search across title, decision question, one-liner, and controlled metadata.
- Quick presets: returns only; holdings; screen managers; IC preparation;
  credit/private markets.
- Facets: stage, asset/vehicle, access, data modality, maturity; advanced
  attestation and method family.
- OR inside a facet/preset and AND across independent facets.
- Result count in `aria-live=polite`, explicit empty state, and one Clear action.
- Query-string serialization and back/forward restoration.
- No JSON-bearing HTML attributes; use validated token lists and escaped text.

### Card presentation

Index tiles show only decision question, maturity, minimum data, and asset scope.
Demo pages receive a compact context block with stage, maturity, minimum data,
scope, access, validation, and attestation. Full refusal and method details remain
on the demo/spec page.

### Access and claim matrix for the 16 new cards

| ID | Lowest realistic access | Strongest claim at that access | Higher access needed for |
|---|---|---|---|
| X3 | public / pre-hire-public | source-conditioned universe and funnel coverage | internal funnel conversion and rejection analysis |
| S7 | shortlisted-nda | record lineage, basis breaks, and backfill flags | independent NAV/cash reconciliation |
| E4 | shortlisted-nda | dated manager-asserted operational changes | independently corroborated controls/provider facts |
| P4 | shortlisted-nda | contractual payoff scenarios | funded reconciliation to administrator/custodian cash |
| M7 | shortlisted-nda | terms plus disclosed liquidity-bucket scenarios | position/financing mismatch verdict |
| S8 | shortlisted-nda | interval-aware fingerprint | named peer cohort after universe/power gates |
| P5 | shortlisted-nda | feasible scenario set from supplied objectives | live breach/cost validation under a segregated mandate |
| S9 | shortlisted-nda data room | cash-flow performance from supplied history | A-class LP/admin cash and facility reconciliation |
| M8 | funded-private-partnership | contractual covenant states and descriptive migration | independently reconstructed cash/default/recovery events |
| M9 | funded-private-partnership | vintage/revision evidence | independent mark triangulation with audit/trade/exit data |
| P6 | funded-private-partnership + internal-governance | conditional portfolio liquidity paths | calibrated allocator-wide forecasts with complete inactive funds |
| P8 | shortlisted-nda | disclosed counterparty/financing dependency scenarios | netted exposure and margin replay from operative agreements |
| S10 | public deal documents or NDA deal room | contractual scenario replay | trustee/admin base-case reconciliation |
| S11 | shortlisted-nda data room | frozen-underwriting versus supplied actuals | independently attested realised value bridge |
| P7 | internal-governance | complete offer-funnel/process calibration | outcome comparison using S9/S11 evidence |
| S12 | shortlisted-nda | illustrative holdings/liquidity capacity scenarios | execution-calibrated frontier and TCA under funded/segregated access |

The Boolean `pre_hire_applicable` is prohibited because it can contradict
claim-level access. The manifest derives discoverability from the claims.

### Accessibility and responsive contract

- Focused skip link participates in layout and never covers the header.
- Interactive targets are at least 44px; important text is at least 12–14px.
- Native fieldsets, labels, buttons, selects, `hidden`, and `aria-pressed`.
- Focus remains on the changed control; result updates are announced.
- Mobile facets collapse; card grid is one column; no horizontal overflow at
  320, 390, 768, or 1440px.
- No-JavaScript output includes every card and direct link.

## 5. Shared evidence and fixture substrate

Implement under `src/quant_allocator/evidence/`:

- `model.py` — immutable record and entity types;
- `schema.py` — stdlib SQLite schema, keys, triggers, and migrations;
- `ingest.py` — hashing, version/revision validation, and idempotent ingestion;
- `snapshot.py` — deterministic bitemporal snapshot queries;
- `lineage.py` — analytic-field to evidence-item receipts;
- `entitlements.py` — access-right and embargo evaluation;
- `universe.py` — dataset/product membership vintages and dead-product retention;
- `checks.py` — completeness, mutation, cycle, and leakage gates;
- `fixtures/core.py` — canonical entities, timestamps, revisions, and refusals;
- `fixtures/public_markets.py` — returns/composites/universe vintages;
- `fixtures/credit.py` — borrowers, covenants, facilities, and counterparties;
- `fixtures/private_markets.py` — cash flows, NAV vintages, and operating data;
- `fixtures/terms.py` — governing terms, precedence, and cash mapping.

The substrate test suite must prove:

- updates/deletes fail;
- revision graphs are acyclic and complete;
- later-received records never enter earlier snapshots;
- latest-restated and point-in-time histories visibly diverge in a planted case;
- canonical snapshots and receipts are byte-identical under row-order changes;
- backfilled dead products cannot appear before their first-known membership;
- team membership, benchmark, entitlement, and access intervals respect half-open
  UTC boundaries;
- future restatements and future `revision_of` links never enter earlier snapshots;
- conflicting revisions and timezone-boundary cases fail deterministically;
- missing time/entity/benchmark fields force named refusals;
- no file modification time is used as a receipt-time substitute.

No downstream generator may ship until this contract passes independent review.
E3 is the sole owner of document extraction, entity-scoped retrieval, and evidence
spans over this store. E4 consumes those evidence IDs and adds only the operational
ontology, temporal diff, conflicts/staleness rules, and re-underwriting queue. S7
owns return/composite/vehicle lineage. X3 owns product/universe/funnel membership.
None creates a second evidence graph or ingestion path.

## 6. Wave A — universal underwriting spine

### X3 — Manager-universe & sourcing-funnel coverage map

**Question:** Which manager/product/strategy/geography cells are represented in
each source and funnel stage, and where should sourcing effort go next?

**Inputs:** point-in-time source membership, active/inactive products, aliases,
strategy/geography/vehicle taxonomy, first-known dates, funnel events, and
source-specific opportunity measures.

**Method:** canonical entity resolution; source-conditioned coverage maps; product
entry/exit history; search-funnel conversion; unsearched-cell gaps; hidden authored
universe for entity/discovery recall. It ranks research cells, never manager quality.

**Refuse:** a global coverage percentage when the denominator is unknown; manager
ranking across incomparable strategies; historical discovery using today's
survivors or backfilled membership.

### S7 — Track-record provenance inspector

**Question:** Is the supplied history complete, comparable, point-in-time, and
portable to the current team/process?

**Inputs:** returns, composite/vehicle/share-class lineage, fee/currency/benchmark
basis, membership history, dead products, predecessor/team chronology, and source
vintages.

**Method:** deterministic entity/segment lineage; backfill and retroactive-membership
flags; basis-change breaks; predecessor portability evidence; comparable-panel
emission. No alpha estimator.

**Refuse:** historical selection without vintages/dead products; silent stitching;
net comparison across unresolved fee bases; incomplete entity mapping.

**Dependency:** consumes X3's reviewed entity/product/universe membership contract.

### E4 — Operational evidence & change graph

**Question:** What changed in organisation, process, controls, or service providers,
and what evidence supports the claim?

**Inputs:** versioned DDQs, org charts, policies, provider records, incidents,
meetings, references, and public filings.

**Method:** operational ontology and point-in-time diff over the shared evidence
store and E3 evidence spans; corroborated/asserted/conflicted/stale states;
re-underwriting question queue. No duplicate ingestion/graph schema and no scalar
ODD score.

**Refuse:** clean/approve verdicts from incomplete evidence; inferred dates; change
claims from an unversioned snapshot.

### P4 — Fee, terms & carry engine

**Question:** What do the governing terms charge under each path, and do actual
cash flows reconcile?

**Inputs:** IMA/LPA/PPM, amendments/side letters, fee/carry/hurdle/waterfall terms,
NAV/capital accounts, contributions/distributions, and currency conventions.

**Method:** exact liquid-fund fee engine; closed-ended waterfall; precedence graph;
disclosed payoff scenarios. Wave A ships contractual scenarios only. The ex-post
private-fund administrator/custodian cash reconciliation lands as P4b after S9's
event-ledger contract is reviewed.

**Refuse:** unresolved document precedence, missing fee basis, incomplete cash-flow
mapping, unknown FX convention, or absent materiality policy for pass/fail.

### M7 — Liquidity & redemption mismatch lab

**Question:** Can assets become cash before investors or financing providers can
demand it?

**Inputs:** redemption/gate/side-pocket terms, liquidity buckets, positions, ADV,
financing/collateral, and investor-liability states.

**Method:** contractual redemption timeline; E-tier bucket ranges; P-tier
liquidation curves; precomputed participation, haircut, margin, and redemption
scenarios.

**Refuse:** returns-only liquidity claims; incomplete terms/coverage/financing;
stale position timestamps. Stress outputs are scenarios, not forecasts.

### S8 — Strategy fingerprint & peer benchmarker

**Question:** What risk process does the record resemble, and which comparison set
is stable enough to name?

**Inputs:** monthly net returns, declared strategy, asset-specific factors,
historical universe vintages/dead products, and optional measured exposures.

**Method:** reuse S2 interval-aware fitting; asset-specific features;
missingness-aware distance; bootstrap peer stability; explicit out-of-distribution
state.

**Refuse:** named peers without calibrated false association/detection/stability
gates; generic equity factors on credit; discovery from a current survivor roster.

**Dependency:** consumes X3, S7, and S2. It cannot name a peer set before the X3
universe and S7 comparability contracts clear.

### P5 — Mandate & benchmark design sandbox

**Question:** Which benchmark, constraints, economics, liquidity, and reporting
rights produce feasible non-dominated structures?

**Inputs:** S7/S8 record and strategy evidence, E4 operational constraints, P4
economics, M7 liquidity, objectives, risk budget, and candidate benchmarks.

**Method:** benchmark coverage/stability screen; exact constraint engine; scenario
propagation; transparent enumeration/Pareto set. No automatic recommendation.

**Refuse:** missing objectives/precedence/benchmark version/economics/liquidity;
operational concerns converted to numeric penalties without an approved mapping.

## 7. Wave B — credit and private-market primitives

### S9 — Private-market cash-flow benchmark

Reconstruct TVPI/DPI/RVPI, KS-PME, benchmark sensitivity, reported IRR, and an
explicit facility-adjusted reconstruction only where every facility draw,
repayment, interest, and fee maps to the LP cash ledger. The counterfactual
convention must be stated; otherwise emit sensitivity scenarios rather than one
neutral number. Active-fund output remains valuation-dependent.

### M8 — Borrower health & covenant migration

Model covenant-specific direction/denominator/headroom. Contractual states are
`compliant`, `breach`, `waived`, and `cured`; allocator `watch` is a
separate documented heuristic. Definition resets and amendments are events, never
apparent improvement. Default-probability claims remain refused absent a separately
validated outcome model. M8 consumes E4's versioned covenant/amendment evidence.

### M9 — NAV vintage & mark-revision audit

Build full vintage triangles, revision matrices, source-independence maps, and later
audit/trade/financing/exit calibration. Never overwrite prior marks or claim an
unobservable true NAV. Missing historical vintages force refusal.

### P6 — Calls, distributions & unfunded forecast

Consume S9 event ledgers and M9 vintages. Produce conditional path distributions,
not points, using rolling-origin point-in-time evaluation, interval coverage, and
liquidity-shortfall scores. Preserve inactive funds and correlated call regimes.
Where rolling-origin coverage cannot be estimated, fall back to an explicitly
uncalibrated scenario range or refuse; never label sparse history calibrated.

After S9 review, P4b adds ex-post fee/carry/facility cash reconciliation against the
same canonical event ledger. P4b does not create a second cash-flow schema.

## 8. Wave C — specialist research

### P8 — Financing & counterparty common-failure map

Typed manager-counterparty/legal-entity/network graph with precomputed failure,
haircut, margin, non-renewal, and trapped-collateral scenarios. No default
probabilities; refuse netting without operative agreements and jurisdiction data.
Consumes E4 evidence, M7 liquidity states, and P4 governing terms.

### S10 — Structured-credit waterfall replay

Deterministic collateral/fee/hedge/trigger/interest/principal/reserve engine with
cash conservation and trustee-report reconciliation. Scenario-only; not a rating,
price, or recommendation. Adversarial fixtures cover trigger priority, fee
seniority, recovery timing, reserve releases, and deliberately contradictory deal
documents. Consumes P4 terms and S9 cash-flow conventions.

### S11 — Operating value-creation calibration

Consume frozen underwriting vintages and actual KPIs. Use an order-invariant value
bridge, forecast-bias/coverage diagnostics, and exact reconciliation. Refuse
manager-level repeatability without cohort power and intact original models.

### P7 — Co-investment offer-funnel audit

Preserve every offered, declined, expired, unavailable, approved, and closed
opportunity. Primary claim is process calibration. Refuse accepted-only analysis and
adjusted comparisons without common support; consume X3 funnel identity, P4
economics, S9 outcomes, and S11 operating evidence where available.

### S12 — Capacity & slippage frontier

Separate returns/AUM description, holdings/liquidity scenarios, and execution-based
implementation-shortfall evidence. A square-root impact curve remains illustrative
until calibrated. Refuse causal AUM-alpha and recommended capacity claims without
execution evidence. Reuse S3 trade ledgers, M4 holdings/liquidity primitives, and M7
liquidity states.

## 9. Implementation waves and ownership

### Phase 0 — roadmap and architecture gate

- Commit this plan.
- Independent review challenges scope, IDs, dependencies, refusal claims, shared
  seams, and whether the plan silently duplicates existing cards.
- Record rulings in this plan and the progress ledger.

### Phase 1 — manifest migration and static Journey

One seam owner edits only:

```text
site/cards.yaml
src/quant_allocator/site/build.py
site/templates/base.html.j2
site/templates/index.html.j2
site/templates/demo.html.j2
site/assets/interval.css
site/assets/gallery.css
site/assets/gallery.js
tests/site/test_manifest.py
tests/site/test_build.py
tests/site/test_gallery.py
tests/site/test_lint.py
tests/site/test_interval_css.py
```

Sequence: failing schema tests; compatibility loader; migrate 20 rows; static
Journey; page context; Catalog/search/facets/presets/query state; responsive and
accessibility gates.

### Phase 2 — evidence substrate

One substrate track owns `src/quant_allocator/evidence/**`, its tests, and shared
fixtures. It may not edit card implementations or shared site seams. An independent
review must adversarially prove bitemporal leakage prevention and immutability.
An E3 hardening task binds its document/entity/provenance output to this store without
changing E3's certified retrieval verdict.

### Phase 3 — Wave A tracks

- A0 serial: X3 universe and sourcing-funnel coverage.
- A1 parallel after X3: S7, E4, P4a terms/precedence/payoff.
- A2 parallel after A1: M7 and S8.
- A3 serial: P5 after all five upstream contracts are reviewed.
- One integration owner adds seven manifest rows, generators, counts, and common
  fixture seams. Total becomes 27 cards.

### Phase 4 — Wave B tracks

- B1 parallel: S9, M8, M9.
- B2 parallel after S9/M9 integration: P4b cash reconciliation and P6.
- One integration owner adds four rows/generators. Total becomes 31 cards.

### Phase 5 — Wave C tracks

- C1 parallel: P8 and S12.
- C2 parallel after dependencies: S10 and S11.
- C3 serial: P7 after X3/P4/S9/S11 contracts are reviewed.
- One integration owner adds five rows/generators. Total becomes 36 cards.

### Card-track file ownership

Each card track exclusively owns:

```text
docs/ideas/specs/<card>.md
src/quant_allocator/flagships/<card-package>/**
src/quant_allocator/demo_data/<generator>.py
tests/flagships/<card-package>/**
tests/demo_data/test_<generator>.py
site/data/<generator>.json
site/templates/pages/<card>.html.j2
site/assets/pages/<card>.css
site/assets/<card>.js
tests/site/test_<card>.py
```

Card tracks never edit `site/cards.yaml`, generator registry, global templates/assets,
cross-card registries, or shared fixtures.

### Card-track commit template

1. Committed card-level implementation plan: reviewed method spec,
   claim/access/attestation matrix, realistic source-shape contract, dependencies,
   synthetic fixture and planted failure, validation/point-in-time design,
   provisional constants, refusal/kill criteria, exact files, and targeted tests.
2. Pure method/domain implementation.
3. Deterministic generator plus held JSON and SHA.
4. Page/CSS/JS and focused site tests.
5. Reconcile the spec's concrete results to actual pipeline output.
6. Handoff docket: owned diff, tests, JSON status, provisional constants, exact
   refusal states, attestation by claim, deviations, and shared-seam values.

Implementers do not self-certify numerical gates. Every card receives an
independent arithmetic/copy review before integration.

## 10. Verification and publication gates

### Per task

- smallest failing targeted test first;
- focused pytest slice, ruff, deterministic generator check;
- named integer random-stream tags with collision tests for every synthetic draw;
- `node --check` for every changed JavaScript file;
- scoped diff review and explicit staging;
- no unrelated cleanup.

### Per wave

- independent whole-wave review;
- controller numerics/copy/attestation docket;
- exact committed-JSON delta and SHA review;
- name uniqueness and fictional/public-data scan;
- point-in-time leakage tests;
- targeted build and browser pass for new pages;
- complete browser regression over every page already live in that wave because
  shared templates and assets can regress earlier cards;
- user publication checkpoint before push.

Each card declares an interaction-state contract. For continuous controls, test both
endpoints, one interior state, and every refusal boundary. For discrete controls,
test every state. For combinatorial controls, use named pairwise cases plus all
decision/refusal boundaries rather than an unbounded Cartesian product.

Every spec names the versioned public standard/schema its realistic fixture models.
No non-public manager document, agreement, holding, prompt, or output may enter
tracked files, CI logs, screenshots, or committed JSON.

After each published wave, remove merged track worktrees and branches, prune the
registry, and re-run the reachable-ref publication scan before starting the next
wave.

### Final 73-page release gate

Expected baseline after expansion: index + 36 demos + 36 method specs = 73 pages,
not 57. The release harness must derive this count from the manifest rather than pin
an obsolete literal.

The final browser matrix covers:

- Journey/Catalog, search, every facet and preset, URL reload/history, clear and
  empty state;
- keyboard order, visible focus, 320/390/768/1440 geometry, and no-JS fallback;
- every declared interaction-state contract on all 36 demos;
- all 36 specs with strict math rendering and zero console errors/warnings;
- direct links, disclosures, context blocks, method links, and refusal states.

Before every push:

1. load the ignored publication terms;
2. run the report-only publication script, read and adjudicate every match, then
   scan the endpoint tree and exact publication range under the approved legacy
   history policy;
3. reject new matching blobs/messages/trailers;
4. build from committed JSON without browser-side estimators, using bounded chunks
   rather than one monolithic 36-card test process;
5. push only from the primary integration owner;
6. wait for Pages, cache-bust, and re-run the live release gate.

After successful publication, remove every campaign worktree and branch, prune the
registry, and verify local `main == origin/main`.

## 11. Explicit non-goals and rejected shortcuts

- No single manager-quality or ODD score.
- No website/news/social sentiment ranking.
- No public-filings claim that reconstructs a private fund.
- No monthly interpolation of private NAVs.
- No generic private-markets KPI dashboard without cash-flow reconstruction.
- No accepted-only co-investment model.
- No causal capacity limit from an endogenous AUM/return history.
- No scalar valuation-manipulation label.
- No silently imputed receipt dates, dead-manager removal, or restated-history
  leakage.
- No JavaScript estimator, hidden numerical recomputation, or label-only control.

## 12. Plan gate questions

The independent reviewer must rule on:

1. whether the 16-card scope has any true duplicates with the current 20;
2. whether E3 plus the shared substrate is sufficient without a separate evidence
   card;
3. whether the ID assignments preserve stable method-family semantics;
4. whether any proposed `usable-now` label overstates decision readiness or
   obscures a teaching-only evidence role;
5. whether every claim has a realistic pre-hire/post-hire access contract;
6. which provisional numerical thresholds must remain unnamed until calibration;
7. whether the 73-page final count and browser matrix are complete.
