## The decision

Operational due diligence should route a small number of explicit evidence questions: what changed, what source supports the fact, what was knowable at the decision cutoff, and what now requires clarification, re-underwriting, or refresh.

It should not compress those questions into a scalar operational-risk score. The evidence graph preserves conflicts, stale facts, source dependence, and unknown incident materiality because those distinctions change the next action. A missing or incompatible input produces a visible refusal, not an invented “clean” state.

## Why the obvious answer fails

Operational evidence usually arrives as documents that mix current assertions, historical changes, controls, incidents, and copied claims. Reading the newest document as the newest truth confuses three different clocks: when a fact was effective, when a document was published or received, and when the allocator is making the decision.

A second mistake is double-counting. Two documents can repeat the same originating source. Counting them as independent corroboration makes copied evidence look stronger than it is.

A third is scalar scoring. A single operational-due-diligence score hides whether the underlying problem is a conflict, a stale control test, an open incident with unknown materiality, or an explicit provider change. Those cases require different actions. Aggregation makes the output easier to rank and harder to trust.

Finally, silence is ambiguous. A fact missing from a later document does not prove removal unless the source contract says a complete snapshot’s absence means removal or provides an explicit tombstone.

## The intuition

Treat every operational claim as a dated fact with a typed key, a typed value, a source lineage, and two time dimensions.

The analytic view asks: what evidence was admissible and knowable by cutoff $t$? The audit view asks: what versions, corrections, and source records led there? Rights, licence purpose, embargo, delivery completeness, and first-known time are checked before the fact’s effective interval is considered.

Once admissible evidence is assembled, classify the current state without smoothing away disagreement. Conflict outranks stale, corroborated, and asserted. Then send the fact to the first applicable categorical queue. The queue is a routing device, not a score.

## A small numerical example

Suppose a manager document states that a process is operating, and a provider-direct document repeats that process assertion. There are two source records, but they do not create two independent confirmations of the process. Provider-direct evidence is independent for the provider’s identity and appointment, not for a manager’s process or control effectiveness.

The fact therefore remains **asserted**, not **corroborated**. Corroboration requires at least two compatible independence groups that are in scope for the predicate being tested.

Now add an open incident whose materiality field is null. The method normalizes null materiality to **unknown**. Because unknown materiality on an open incident is decision-relevant uncertainty, the item enters **immediate clarification** before any stale-evidence rule is considered.

This example distinguishes four output types. The source statements are evidence. Their typed current state is a verdict. The queue placement is an exact categorical routing result. Any request for a clean/approve score is refused.

## The method

### Key each fact at the decision-relevant grain

An operational fact uses the key

$$
(m,d,s,p,c),
$$

where $m$ is the manager entity, $d$ the operational domain, $s$ the subject entity, $p$ the predicate, and $c$ the scope. The value is typed; source prose is not copied into the analytic output.

Effective intervals are half-open. If an interval ends at time $t$, it is not active at $t$. Publication or first-known time governs when the allocator could know a fact, but it cannot substitute for the fact’s effective date. A change requires an explicit point date or interval.

Admitted change types are added, modified, corrected, explicitly removed, relationship started, and relationship ended. An unversioned assertion may be shown as current evidence, but it cannot establish change.

### Preserve source independence and evidence age

Compatible copies within the same independence group count once. Corroboration requires at least two independence groups. Control effectiveness needs a control test or independent confirmation, and incident closure needs remediation or closure evidence.

Evidence age for fact $f$ at cutoff $t$ is

$$
A_f(t)=\operatorname{days}\left(
t-\max_{i\in I_f}\operatorname{freshness\_at}_i
\right).
$$

$I_f$ is the set of evidence available by $t$, and $\operatorname{freshness\_at}_i$ is the source’s explicit as-of, test, or refresh date. Receipt time does not make old evidence fresh.

Stale begins strictly after $180$ days for organization and process facts, $365$ days for controls and providers, and $90$ days for incidents.

### Route the first applicable action

The queue uses this precedence:

1. **Immediate clarification:** conflicts, critical or material open incidents, unknown incident materiality, or incompatible provider/control relationships.
2. **Scheduled re-underwrite:** explicit provider, organization, process, or control changes and open non-material incidents.
3. **Evidence refresh:** stale evidence.
4. **No action from this method:** compatible current evidence with no admitted change.

Items within a bucket sort by controlled domain order, effective date, and a stable ordering key. No weight or scalar severity score is introduced.

## What the evidence changes

In the synthetic result, the latest cutoff using all permitted sources admits $16$ analytic facts across $10$ current keys. The exact state inventory is $1$ corroborated, $3$ asserted, $3$ conflicted, and $3$ stale. The action queue contains $4$ immediate clarifications, $4$ scheduled re-underwrites, and $2$ evidence refreshes.

Those counts are exact outputs of the authored synthetic example, not estimates of operational-risk frequencies. They show that a single manager state can contain corroborated, asserted, conflicted, and stale facts at once. That is precisely what a scalar score would erase.

The evidence supports routing work. It does not support “operationally clean,” approval, manager ranking, hiring, firing, or a recommendation.

## What the allocator does next

Open the immediate-clarification queue first. Resolve conflicts, unknown incident materiality, and incompatible relationships against their source records.

Then schedule explicit provider, organization, process, or control changes for re-underwriting. Request refreshes for facts that crossed their domain-specific age boundary. Leave compatible current evidence with no admitted change in the no-action category.

For each item, retain the decision cutoff and reconstruct both the latest-known analytic view and the all-known-versions audit view. Do not infer a change date from document arrival, infer removal from silence, or treat a provider repetition as independent process corroboration.

## Limits and go-live

- All displayed manager entities and operational records are authored synthetic evidence. The counts are example outcomes, not calibrated risk rates.
- Public scope is limited to admissible public sources. Permissioned claims require the appropriate right and access context.
- Go-live requires versioned operational sources for every intended source family, revision and absence mode, and access context.
- Each source needs explicit effective and first-known time, canonical entity and relationship provenance, independence spans, per-dataset rights, complete delivery evidence, and reproducible source records.
- Validation requires at least one reviewed live-shaped case per intended source family, revision mode, absence mode, access context, and planted refusal boundary. This is coverage validation, not an estimator sample threshold.
- The interactive surface may switch among exactly six precomputed point-in-time states: three cutoffs crossed with public-sources-only and all-permitted-sources views. Browser controls may filter those precomputed memberships; they may not join evidence or classify facts.
- Copied sources retain their originating independence group. Inferred change dates remain source-quality facts, and unresolved rows remain audit-only.

## Key takeaways

- Effective time and first-known time answer different questions.
- Two documents are not independent when they repeat one source.
- Silence removes a fact only under explicit ruled absence semantics.
- Conflict and unknown incident materiality route before staleness.
- The output is a categorical work queue, never a scalar operational score.
- Missing rights, lineage, time, delivery, identity, or independence evidence produces refusal.

## References

The operational-evidence method is self-contained and specifies no external bibliography. Its claims rest on the temporal, independence, change, and refusal rules explained above.
