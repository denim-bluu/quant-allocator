# X3 · Manager-universe and sourcing-funnel coverage map

**Status:** implementation candidate; independent numerical and publication gates remain open.

## 1. The problem

An allocator can count rows in a database without knowing whether those rows describe firms,
strategies, composites, or vehicles, whether two rows are the same entity, or whether an absent
row means a true exit. X3 prevents those category errors. It measures the named, receipted
source snapshots against an allocator-authored target grid at one canonical entity grain.

> **This map measures the named sources and funnel, not the manager universe of the world. It
> prioritizes research cells, never managers.**

## 2. Source-conditioned estimand

For eligible target cells $G^{\mathrm{eligible}}_{t,q}$, cutoff $t$, entity grain $q$,
and selected source set $S$, define

$$
O_{g,t,q}(S)=\mathbf{1}\{\text{at least one resolved entity of type }q
\text{ is visible in cell }g\}.
$$

Then

$$
C_{t,q}(S)=\frac{\sum_{g\in G^{\mathrm{eligible}}_{t,q}}O_{g,t,q}(S)}
{|G^{\mathrm{eligible}}_{t,q}|}.
$$

The numerator is observed eligible policy cells. The denominator is the receipted policy grid,
not a market-size estimate. Excluded cells remain visible in a separate `not_targeted` ledger.
Leave-one-source-out novelty is the canonical set difference
$N_s=|U(S)\setminus U(S\setminus\{s\})|$; it is not a source-quality score.

## 3. Identity, funnel, and queue

Only shared mappings with status `resolved` enter canonical counts. Ambiguous and unresolved
rows remain visible. Duplicate source evidence is retained while canonical IDs are deduplicated.
The queue is categorical, in this precedence: `repair_identity`, `refresh_source`, `source_gap`,
`funnel_unavailable`, `screening_backlog`, `diligence_backlog`, `represented`.

The reviewed substrate can evaluate event-linked cohorts and receipt exact stage counts. Its
fixture manifest still requires `typed-mandate-brief-cohort-projection-required`. Therefore X3
does not emit funnel conversion intervals, target-cell conversion, or mandate-brief inference.
Every affected state shows a pointer-specific refusal and uses `funnel_unavailable` before a
downstream backlog reason.

The current shared membership projection also has no canonical target-cell link. Exact
source/mapping/member totals and exact eligible/excluded authored-grid totals remain valid, but
target-cell observation, novelty-by-cell, coverage-by-cell, and queue verdicts that require the
link refuse with `typed-membership-cell-projection-required`. X3 performs no label, ordinal,
geography, or taxonomy-string inference.

## 4. Validation

Synthetic entity resolution reports two-sided 95% Wilson intervals. For perfect precision,

$$
L(n,n)=\frac{n}{n+1.96^2}.
$$

The gate $L\ge0.99$ therefore requires
$n\ge\lceil0.99(1.96)^2/(1-0.99)\rceil=381$. Equality passes. Recall also requires a lower
bound of at least 0.95. These gates validate only the authored synthetic perturbation regime.
Synthetic discovery recall uses a complete hidden fixture denominator and is never generalized
to live market coverage.

## 5. Reconciliation to generated output (2026-07-11)

The deterministic payload contains the exact 27-state Cartesian product. In the server default
(`latest|public-plus-prehire|cross-asset`), the reviewed projections emit 835 mapping rows, 835
membership rows, 24 resolved active strategy IDs, one ambiguous row, 21 eligible authored cells,
and three excluded `not_targeted` cells. Observed-cell coverage remains null/refused because the
typed membership-to-cell projection is absent.

The synthetic identity audit emits 410 true positives, zero false positives, ten false negatives,
and 420 true negatives. Its 95% Wilson lower bounds are 0.990717 for precision and 0.956732 for
recall, so the authored synthetic gate clears without fallback. Synthetic fixture discovery recall
is 23/24 (0.958333); this is not live market coverage.

In the latest full-funnel state, the shared evaluation receipts support labelled included counts
of 75 entry / 59 screened for `x3-discovered-to-screen` and 75 entry / 7 approved for
`x3-diligence-to-approved`. No conversion interval is emitted because the typed mandate-brief
prerequisite remains open. These are implementation outputs awaiting independent arithmetic and
copy review; the implementer does not certify them.

The shared pins remain fixture manifest
`14a159d4547960c937485d328c3b270051daba7114e54f1380869466a11275e0`, authored closure
`c5054f17d2e95bf6e80ba7c63a5a8f10f849f7e989f12cf9447d0d308744ac32`, and schema
`43a0f22036e3e6b55fc15a05071e58d7771ff5546cedce7c4ee45155f38b0818`.

## 6. Access and attestation

All displayed values are fictional synthetic evidence at current attestation D. Public,
pre-hire, shortlisted, target-grid, and funnel datasets each require their exact right, access
context, licence purpose, version, and receipt. Multi-source authorization uses AND semantics.
Live ceilings are A for independently reconstructable public membership, B for receipted
pre-hire/coverage/funnel measurements, C for the research-cell queue, and none for global
coverage or manager ranking.

## 7. Page contract

The server-rendered latest/public-plus-prehire/cross-asset state remains complete without
JavaScript. Three native control groups select only among exactly 27 precomputed states. Each
change updates text and visual evidence, the URL, focus-preserving controls, and an `aria-live`
summary. Browser code performs no estimator, entity-resolution, cohort, or queue arithmetic.

## 8. Binding rulings

1. One result uses one canonical entity grain; mixed-grain totals are prohibited.
2. Eligible grid cells form the denominator; excluded cells are separately receipted.
3. Global manager/product coverage and manager-quality ranking always refuse.
4. The binding disclaimer in section 1 appears in Python/JSON/HTML tests.
5. The shared `evaluate_funnel_cohort` API may support exact labelled stage counts only.
6. The typed mandate-brief prerequisite blocks every conversion interval and target-cell or
   mandate-brief conversion inference; the queue emits `funnel_unavailable`.
7. The missing typed membership-to-cell link blocks target-cell observation, novelty-by-cell,
   coverage-by-cell, and dependent queue verdicts; no heuristic may replace it.
8. Precision/recall use two-sided Wilson 95% intervals; 380 perfect links fail and 381 pass.
9. Truth labels are card-local audit inputs and never enter production state inputs or receipts.
10. JavaScript selects exact precomputed states and performs no statistical computation.
11. All production output is fictional synthetic D-tier evidence and requires independent review.
