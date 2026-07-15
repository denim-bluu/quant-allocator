## The decision

A quarterly review should use one narrated, print-clean pack assembled from analyses that have already cleared their own evidence gates. The pack should compute nothing, soften nothing, and disclose every section as rendered, refused, or unavailable at the manager’s transparency tier.

This is a composition decision, not a new manager verdict. The pack exists because separate dashboards and analytic tabs are easy to ignore, while an engagement document sits inside the meeting where the decision is discussed. Its safety comes from binding every number and conclusion to a certified source payload and failing the build when narration departs from that evidence.

## Why the obvious answer fails

The familiar answer is a dashboard with one tab per analysis. The source evidence records roughly $25\%$ adoption for that pattern: a separate analytic can remain technically correct and still improve no decision because nobody opens it at the review moment.

Simply pasting the same panels into a document creates a different risk. Handwritten narration can round a certified value, drop an interval, or turn a refusal into a confident conclusion. “Sharpe near 0.7” sounds harmless, but it is neither the certified reported value nor the certified de-smoothed value. A summary can also declare skill where the source card explicitly says the sample is insufficient.

The failure is not prose itself. It is prose without a constrained evidence boundary. The engagement pack therefore treats narration as a checked projection around immutable numbers, not as a place to recompute or improvise.

## The intuition

Think of the pack as an ordered section registry followed by two doors.

The first door asks whether the manager’s data tier is sufficient. Returns-only $R$ sits below exposure $E$, which sits below position-level $P$. A section needing a richer tier is omitted from the body but listed in a “not shown at this tier” footer.

The second door asks whether the source metric’s sample gate has cleared. A section whose tier is sufficient but whose evidence is too thin appears as a labelled refusal. It explains what the metric would show and what evidence is missing, without asserting the gated claim.

Only sections that pass both doors render their certified intervals or verdicts. Nothing disappears silently. A missing section is itself decision-relevant evidence about transparency or power.

## A small numerical example

Consider fictional Manager Q at tier $R$, with $48$ monthly observations.

The uncertainty-honest tear sheet requires returns only and is not separately power-gated, so it renders. Its reported Sharpe is $0.71$, with a $95\%$ interval from $-0.26$ to $1.67$. After de-smoothing, the point falls to $0.60$, with a $95\%$ interval from $-0.29$ to $1.46$. Annualized alpha is $+3.2\%$, but its $90\%$ interval is $-4.4\%$ to $+10.8\%$. The points are estimates; the intervals show the range the record supports; the verdict remains provisional because zero is still plausible.

Posterior skill standing also accepts tier $R$, but the registered threshold is null: no track length in the measured sampler range separates a true information ratio of $0.5$ from luck. That section is **refused**, not empty.

Exposure drift requires tier $E$. Manager Q is at $R$, so that section is **omitted** and disclosed in the footer as available at tier $E$.

Now consider the sentence: “The reported Sharpe of 0.71 pulls down to 0.60 once smoothing is undone.” The narration check extracts $\{0.71,0.60\}$ and verifies both tokens occur in the tear-sheet payload. The sentence passes. “A Sharpe near 0.7” extracts a number not present in the payload and fails the pack. The rule is deliberately literal because a plausible wrong number is worse than a missing sentence.

## The method

### Resolve every registered section

For section $s$, let $r(\cdot)$ map tiers $(R,E,P)$ to ranks $(0,1,2)$. If the manager’s tier is below the section’s minimum tier,

$$
\operatorname{state}(s)=\texttt{omitted}
\quad\text{when}\quad
r(\text{tier}_{\mathrm{mgr}})<r(\text{tier}_{s}).
$$

If the tier passes, let $q$ be the manager’s relevant evidence quantity—months, trades, or exits—and let $\tau$ be the source metric’s threshold from the power registry:

$$
\operatorname{state}(s)=
\begin{cases}
\texttt{rendered}, & q\ge\tau,\\
\texttt{refused}, & q<\tau\text{ or }\tau=\varnothing.
\end{cases}
$$

$\tau=\varnothing$ means no observed sample in the measured range clears the bar. E2 reads that result; it never chooses or overrides it.

### Preserve four honesty invariants

Every statistic is an interval or an explicit verdict, never an estimate-bearing bare point. Every number carries source-card provenance. The pack cannot override a refusal, including in prose. Provenance and the synthetic-data disclosure survive printing.

The section registry is the complete contract. An analysis with no approved source payload and no registry row cannot enter through narration. This makes killed or unreviewed analytics structurally unreachable.

### Constrain and test narration

Narration fills a structured slot around payload values. Let $A$ be the set of numeric tokens in the prose and $B$ those in the certified payload. Numeric faithfulness is

$$
F=\frac{|A\cap B|}{|A|}.
$$

The gate is $F=1.00$: one invented numeral fails the pack. The hallucinated-claim maximum is $0$, and gate-respect accuracy must be $1.00$. Auto-narration remains a draft and is human-edited before shipping.

If the narration harness misses those gates after $2$ prompt or model iterations, auto-narration is cut. The pack ships with deterministic section headers and template captions. Composition survives; probabilistic prose does not.

## What the evidence changes

For Manager Q, the pack supports a narrow conversation: performance looks modest after de-smoothing, the alpha interval includes zero, skill standing refuses at the current evidence, and exposure drift is unavailable at tier $R$.

That evidence does not permit “the manager has skill,” “the manager lacks skill,” or “the portfolio has drifted.” It permits three more precise statements: the tear sheet is rendered with wide intervals, the skill claim is refused by its power gate, and the exposure analysis is omitted because its data right is absent.

The pack’s contribution is therefore adoption with preserved uncertainty. It does not create a stronger conclusion by placing several weak conclusions on one page.

## What the allocator does next

Before each quarterly review, collect the certified section payloads and their as-of dates. Resolve the registry in order, keeping mixed cadences visible rather than pretending that a monthly return panel and a quarterly letter share one timestamp.

Review every refusal and omission as part of meeting preparation. A refusal may motivate more observation; an omission may motivate the next rung of the transparency ladder. Neither should be silently deleted for visual neatness.

Human-edit the connective prose, rerun the numeric and gate-respect checks, and use the document in the review itself. Any manager-facing version should remain help-framed and expose adjustable assumptions where the source method supports them.

## Limits and go-live

- E2 has no estimator, no statistical power curve, and no data ask of its own.
- Inputs are certified payloads, not raw returns, exposures, or positions. Each source section inherits its own data, provenance, and sample requirements.
- The power registry must exist before gated live sections can resolve honestly.
- At tier $R$, the pack can use returns-based and document-native sections. Tier $E$ adds exposure drift and say–do alignment; tier $P$ adds supported position-level descriptors and name-level alignment.
- Narration must clear numeric faithfulness $1.00$, zero unsupported claims, and gate-respect accuracy $1.00$; all narration is still human-edited.
- Failure after $2$ narration iterations triggers deterministic captions, not a relaxed threshold.
- The pack never upgrades a source card’s maturity or authorizes a hire, add, redeem, or manager ranking.

## Key takeaways

- The engagement pack composes certified evidence; it does not calculate new evidence.
- Every section is rendered, refused, or omitted-and-footnoted.
- A refused claim remains refused in the narration.
- Every numeral in prose must appear verbatim in its certified payload.
- A document used in the decision moment can solve an adoption problem without weakening the analytical gates.
- If auto-narration fails, deterministic captions are the safe fallback.

## References

- Dietvorst, Berkeley J., Joseph P. Simmons, and Cade Massey. “Overcoming Algorithm Aversion.” *Management Science*, 2018.
- Falk, Armin, and Michael Kosfeld. “The Hidden Costs of Control.” *American Economic Review*, 2006.
- Es and coauthors. *RAGAS*, 2023, on evaluating faithfulness to retrieved context.
