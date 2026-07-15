# Operational evidence and change graph

## The problem

Operational due diligence is usually delivered as documents that mix current assertions,
historical changes, controls, incidents, and copied claims. A document arriving today does not make
its contents true today, and two documents are not independent evidence when both repeat the same
source. E4 reconstructs what was knowable at a decision cutoff and routes evidence questions without
turning them into an ODD score.

The exhibit uses authored synthetic records and fictional entities. It is a method demonstration,
not a diligence verdict, recommendation, or manager ranking.

## Evidence boundary

E4 consumes the reviewed `e4_operational_evidence_v1` fixture. The shared evidence layer owns source
records, immutable item revisions, rights, dataset versions and partitions, canonical entities,
mappings, relationships, snapshots, and receipts. E4 does not create another evidence store.

For each source, `latest-known` supplies the analytic view and `all-known-versions` supplies the
audit view. Rights, licence purpose, embargoes, reconstruction completeness, and receipt time are
applied before valid time. Effective intervals are half-open: an interval ending at time $t$ is not
active at $t$.

The operational fact key is

$$
(m,d,s,p,c),
$$

where $m$ is manager entity, $d$ domain, $s$ subject entity, $p$ predicate, and $c$ scope. The value
is the typed source value; source prose is never copied into the E4 output.

## Dates and changes

An explicit point date or interval is mandatory for a change. Publication or receipt time controls
when the allocator could know a fact but cannot substitute for its effective date. A single
unversioned assertion may be displayed as current evidence but cannot establish change.

Changes are `added`, `modified`, `corrected`, `explicitly-removed`, `relationship-started`, or
`relationship-ended`. Silence removes a row only under an explicit tombstone or a complete full
snapshot whose ruled absence semantics are `full-snapshot-means-removed`. `not-inferable` silence
creates no change.

## Evidence state

For compatible current facts, source copies sharing an independence group count once. State
precedence is conflict, stale, corroborated, then asserted. Corroboration requires at least two
independence groups. A control-effectiveness claim requires a control test or independent
confirmation, and incident closure requires remediation or closure evidence.

Provider-direct evidence is independent only for provider identity and appointment facts. It does
not independently corroborate a manager's process assertion or control effectiveness. Incident
materiality stored as null is normalized to `unknown`; an open unknown-materiality incident enters
immediate clarification before the stale-evidence queue rule.

Evidence age is

$$
A_f(t)=\operatorname{days}\left(t-\max_{i\in I_f}\operatorname{freshness\_at}_i\right).
$$

Here $I_f$ is evidence available by decision time $t$; `freshness_at` is the source's explicit
as-of, test, or refresh date. Receipt time does not refresh old evidence. Stale begins strictly
after 180 days for organisation/process, 365 days for control/provider, and 90 days for incidents.

## Re-underwriting queue

The queue is categorical, never scored. The first applicable bucket wins:

1. `immediate-clarification` for conflicts, critical/material open incidents, unknown incident
   materiality, or incompatible provider/control relationships;
2. `scheduled-reunderwrite` for explicit provider, organisation, process, or control changes and
   open non-material incidents;
3. `evidence-refresh` for stale evidence;
4. `no-action-from-e4` for compatible current evidence without an admitted change.

Within a bucket, items sort by controlled domain order, effective date, and stable ID.

## Reconciled synthetic result

At the latest all-entitled cutoff, the reviewed pipeline admits 16 analytic facts over 10 current
keys. The exact state inventory is 1 corroborated, 3 asserted, 3 conflicted, and 3 stale. The queue
contains 4 immediate clarifications, 4 scheduled re-underwrites, and 2 evidence refreshes. The
provider-confirmed process fact remains asserted because provider-direct evidence is out of scope
for process corroboration. The stale open incident with unreported materiality is routed to
immediate clarification because null materiality normalizes to unknown.

These are held synthetic fixture outcomes, not calibrated operational-risk rates. The committed
artifact also preserves four explicit limitations: copied sources share their originating group;
an inferred change date is only a source-quality fact; public scope is source-limited; and
unresolved rows remain audit-only.

## Claims and refusals

All demo claims are current D and receipt-backed. Positive public facts have live ceiling C;
permissioned change, state, and queue claims have live ceiling B; method/data refusals and synthetic
validation remain D. Every data-boundary refusal is visible at its own output pointer. The method
boundary always refuses scalar ODD scores, clean/approve verdicts, hire/fire decisions,
recommendations, and manager ranks.

## Validation and interaction boundary

The committed exhibit contains exactly six point-in-time base states: three cutoffs crossed with
public-only and all-entitled source views. Domain, evidence-state, and timeline/graph/table controls
filter only committed IDs. JavaScript never joins sources, computes age, classifies a fact, infers a
change, or prioritizes the queue.

Go-live requires permissioned versioned operational sources covering each intended source family,
revision and absence mode, access context, explicit effective/receipt time, canonical mapping,
relationship provenance, independence span, right, complete delivery, and reconstruction receipt.
