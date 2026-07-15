## The decision

Measure coverage only against a named, versioned target grid and named source snapshots at one canonical entity grain. Use the result to prioritize research cells, never to estimate the global manager universe or rank manager quality.

The current evidence permits exact source, mapping, membership, and authored-grid counts. It refuses observed-cell coverage and cell-level queue verdicts because the source records do not explicitly assign strategies to target cells. It also refuses funnel conversion intervals because opportunities have not been explicitly assigned to complete, dated cohorts.

Those refusals are the central result. A count is not automatically a denominator, and a source row is not automatically a unique strategy.

## Why the obvious answer fails

A database can contain hundreds of rows without establishing what those rows represent. Firms, strategies, composites, vehicles, and share classes are different grains. Adding them together produces a large number with no coherent estimand.

Duplicate source records create another illusion. Two datasets may describe the same strategy under different labels. Counting rows overstates represented entities; collapsing them without a resolved mapping hides ambiguity.

The most tempting mistake is to divide observed rows by an imagined global denominator and call the result market coverage. The denominator is unknown. The method therefore measures only documented policy cells in an allocator-authored target grid.

Funnel conversion can fail similarly. Stage counts are exact only when cohort eligibility, event completeness, absence semantics, rights, and observation windows are explicit. A ratio over an incomplete denominator is not a rough interval; it is a refused estimand.

## The intuition

Start with a policy grid: the combinations of characteristics the allocator has chosen to research. Mark each cell eligible or excluded, and keep excluded cells in a separate ledger.

Then choose one entity grain and resolve each selected source row to that grain. Resolved rows can enter canonical counts; ambiguous and unresolved mappings remain visible but do not enter as settled entities.

Finally, ask which eligible cells contain at least one visible resolved entity. That ratio is source-conditioned grid coverage. It says how well the named sources represent the chosen research map. It says nothing about all managers or products in the world.

## A small numerical example

In the default synthetic state—latest cutoff, public-plus-pre-hire sources, cross-asset scope—the source projections contain $835$ mapping rows and $835$ membership rows. They resolve to $24$ active strategy identifiers, with $1$ ambiguous row. The authored grid contains $21$ eligible cells and $3$ excluded cells labelled as outside the target.

It would be easy to report $24/21$, $835/21$, or some deduplicated variant as “coverage.” Every one would be wrong. The current membership projection has no canonical target-cell link, so the method cannot determine which of the $21$ eligible cells those $24$ resolved strategies occupy.

The correct output is therefore:

- exact mapping, membership, entity, eligible-cell, and excluded-cell counts;
- an explicit ambiguous identity row;
- **refused** observed-cell coverage, novelty-by-cell, and dependent queue verdicts.

The estimate is absent because the join is absent. The refusal preserves the difference between a known numerator component and a valid coverage ratio.

## The method

### Define a source-conditioned estimand

Let $G^{\mathrm{eligible}}_{t,q}$ be the eligible target cells at cutoff $t$ and entity grain $q$. For selected source set $S$, define

$$
O_{g,t,q}(S)=
\mathbf 1\{\text{at least one resolved entity of grain }q
\text{ is visible in cell }g\}.
$$

$O_{g,t,q}(S)$ is $1$ when eligible cell $g$ is observed and $0$ otherwise. Source-conditioned grid coverage is

$$
C_{t,q}(S)=
\frac{\sum_{g\in G^{\mathrm{eligible}}_{t,q}}O_{g,t,q}(S)}
{|G^{\mathrm{eligible}}_{t,q}|}.
$$

The denominator is the documented eligible policy grid. Excluded cells never enter it. If the source memberships cannot be linked explicitly to grid cells, $C_{t,q}(S)$ refuses.

For source $s$, leave-one-source-out novelty is

$$
N_s=|U(S)\setminus U(S\setminus\{s\})|,
$$

where $U(S)$ is the canonical entity union across selected sources. $N_s$ is an exact set difference at a stated cutoff and grain, not a source-quality score.

### Resolve identity before counting

Only source rows attached unambiguously to one strategy enter the resolved count. Ambiguous and unresolved rows remain separately visible. Source evidence is preserved even when duplicate identifiers are consolidated.

Research cells enter a categorical queue in this precedence: identity repair, source refresh, source gap, funnel unavailable, screening backlog, diligence backlog, represented. The first applicable reason wins. Missing explicit links trigger the relevant refusal rather than a label or geography guess.

### Validate the synthetic identity mechanism

Precision and recall use two-sided $95\%$ Wilson intervals. With $n$ perfect accepted links, the lower precision bound is

$$
L(n,n)=\frac{n}{n+1.96^2}.
$$

Requiring $L\ge0.99$ implies

$$
n\ge
\left\lceil
\frac{0.99(1.96)^2}{1-0.99}
\right\rceil
=381.
$$

Equality passes; $380$ perfect links fail. Recall also needs a lower bound of at least $0.95$. These gates validate the authored perturbation regime only, not live market coverage.

## What the evidence changes

The synthetic identity audit contains $410$ true positives, $0$ false positives, $10$ false negatives, and $420$ true negatives. Its Wilson lower bounds are $0.990717$ for precision and $0.956732$ for recall, so the synthetic identity gate clears. Synthetic discovery recall is $23/24=0.958333$, using a complete hidden reference-set denominator; it cannot be generalized to the market.

The latest full-funnel state supports labelled included counts of $75$ entry and $59$ screened for the discovered-to-screen cohort, and $75$ entry and $7$ approved for the diligence-to-approved cohort. No conversion interval is emitted. Explicit opportunity-to-cohort assignment remains missing, so the denominator and target-cell linkage required for that inference are not certified.

The evidence changes research operations by separating exact counts from unresolved claims. It permits source reconciliation and identity-quality validation. It refuses global coverage, target-cell coverage without the explicit link, funnel conversion without the cohort prerequisite, and all manager-quality rankings.

## What the allocator does next

First, add an explicit strategy-to-target-cell assignment. Do not substitute label matching, geography inference, ordinal mapping, or taxonomy strings.

Second, complete the opportunity-to-cohort assignment and its event, completeness, absence, right, purpose, and observation-window evidence. Only then revisit conversion intervals.

Third, use exact unresolved identity, source freshness, and missing-source states to prioritize research cells. Keep the queue categorical and preserve the reason each cell entered it.

For every published count, state the source versions, cutoff, entity grain, target-grid version, included rights and purposes, and reproducible source records.

## Limits and go-live

- All displayed entities, mappings, memberships, target cells, and funnel events are fictional synthetic evidence at the current demonstration tier.
- Live use requires per-dataset rights, licence purposes, access contexts, complete version manifests, exact absence rules, and reproducible source records.
- Shared entity, relationship, membership, and grid records must use explicit references and one canonical grain.
- Exact source and authored-grid counts need no estimator sample threshold, but their scope remains limited to the named documented datasets.
- The synthetic precision gate requires at least $381$ accepted true-positive links with no false positives; recall’s Wilson lower bound must be at least $0.95$.
- Conversion intervals remain unavailable until explicit cohort assignment and complete funnel evidence exist. Target-cell coverage remains unavailable until explicit strategy-to-cell assignment exists.
- Browser controls may choose only among $27$ precomputed states. They may not resolve entities, form cohorts, calculate coverage, or prioritize the queue.
- Global manager/product coverage and manager-quality ranking refuse in every context.

## Key takeaways

- Coverage needs a documented denominator and one canonical entity grain.
- Named-source grid coverage is not global market coverage.
- Exact row counts do not repair a missing membership-to-cell link.
- Identity ambiguity remains visible and outside resolved canonical counts.
- Synthetic identity gates can validate the authored matching regime without validating live discovery coverage.
- The method prioritizes research cells; it never ranks managers.

## References

The manager-universe method is self-contained and specifies no external bibliography. Its claims rest on the source-conditioned coverage, Wilson validation, identity, cohort, and refusal rules explained above.
