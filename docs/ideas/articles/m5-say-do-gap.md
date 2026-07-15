## The decision

Manager letters state what a manager believes and how the book is positioned. Exposure
reports show what the book actually did. The allocator's useful question is whether the
two align over the horizon the manager named.

The public method separates reading from judgment. A language model may extract a
structured view and its verbatim source sentence. It may not decide whether that view
was followed. Deterministic code compares the stated direction with the measured
exposure move and returns aligned, partial, contradicted, or unmappable.

A contradiction is communication drift worth a conversation. It is not misconduct, a
probability, or a redemption trigger.

## Why the obvious answer fails

Reading letters without reconciling them simply restates the manager's narrative.
Waiting for returns is late and confounded: many exposures can produce the same P&L.

The more tempting shortcut is to ask a language model whether prose and positions
“agree.” That produces a plausible label without a stable rule. A borderline case can
move between runs, and the reader cannot identify the threshold that drove the answer.
For a manager conversation, an unrepeatable judgment is not defensible.

The opposite extreme—forcing every sentence into a measurable theme—also fails. Some
views have no matching exposure bucket. Inventing a proxy would turn missing evidence
into false precision. The correct state is **unmappable**, retained with its source but
not scored.

## The intuition

Think of two stations. Station one reads. It extracts direction, theme, measurable
instrument, horizon, conviction, date, and the exact quote. Station two scores. It
looks up the measured exposure series, calculates its move, and applies a fixed
materiality threshold.

The separation gives each tool the job it can defend. Language models are useful for
turning prose into structured candidates. Plain code is useful for applying the same
rule to the same numbers every time.

The receipt travels with the result: quote on one side, exposure path and threshold on
the other. A reader can disagree with the mapping or the threshold without having to
trust a hidden model judgment.

## A small numerical example

A synthetic April letter says:

> Given how crowded momentum has become, we have been trimming our exposure to the
> factor and expect to stay cautious.

Station one extracts a cautious direction on momentum beta, a two-quarter horizon, and
the verbatim sentence. At the letter date, measured momentum beta is 0.00. Two quarters
later it is $+0.15$, so the realized move is

$$
m=0.15-0.00=+0.15.
$$

For a cautious view the direction sign is $\sigma=-1$. With a factor-beta dead-band
$\delta=0.10$, the move in the stated direction is

$$
\sigma m=(-1)(+0.15)=-0.15.
$$

Because $-0.15\le-0.10$, the deterministic label is **contradicted**. The manager said
momentum exposure was being reduced, while measured beta rose materially.

If beta had ended at $+0.06$, then $\sigma m=-0.06$ would remain inside the dead-band.
The label would be **partial**. The method would refuse to turn a small move into a
strong claim.

## The method

For a mapped directional view, let $x(t)$ be the measured exposure, $t_0$ the letter
date, and $t_1$ the end of the stated horizon. Define

$$
s=x(t_0),\qquad e=x(t_1),\qquad m=e-s.
$$

$s$ and $e$ are the starting and ending exposures; $m$ is the realized move. Let
$\sigma=+1$ for constructive or long and $\sigma=-1$ for cautious or short. Let
$\delta$ be the materiality dead-band for the instrument class.

The label is

$$
\begin{cases}
\text{aligned}, & \sigma m\ge\delta,\\
\text{contradicted}, & \sigma m\le-\delta,\\
\text{partial}, & |\sigma m|<\delta.
\end{cases}
$$

A right-signed move completed only after the stated horizon is also partial. When the
letter says an exposure will remain neutral, there is no direction sign. Alignment then
means the entire path stayed within $\pm\delta$ of its starting value; leaving that band
is contradicted.

The label is intentionally not probabilistic. Given the extracted view, measured path,
and threshold, it is fixed. Distributional work happens offline when $\delta$ is
calibrated so ordinary noise rarely produces a false contradiction.

The extraction itself requires separate evaluation. Precision and recall are measured
for direction, theme mapping, instrument mapping, horizon, conviction, and quote span.
Alignment labels are checked with a three-by-three confusion matrix so systematic
over-calling of contradiction cannot hide inside an aggregate score.

## What the evidence changes

The result turns “the story feels different from the book” into a sourced row whose
logic is inspectable. An aligned row confirms only that the measured exposure moved in
the stated direction. It does not validate the investment thesis. A contradicted row
identifies a communication gap; it does not establish deception.

At returns-only transparency, letters can support a view inventory and consistency
checks across letters, but not alignment. Without exposure measurements, the method
refuses the label. Exposure summaries support factor, sector, duration, gross, and net
alignment. Positions can add name-level receipts.

The public demonstration remains illustrative until the extraction evaluation clears.
No real-letter claim is promoted from a hand-authored example.

## What the allocator does next

1. Verify the letter date, source, entity, and quoted span.
2. Review the theme-to-instrument mapping before interpreting the label.
3. Confirm that exposure definitions and dates align with the stated horizon.
4. Bring the quote, path, and dead-band to the manager conversation without
   editorializing.
5. Record any mapping correction and rerun the deterministic score.

## Limits and go-live

The public letter and manager are synthetic. A live inventory needs dated public fund
letters. Alignment additionally needs exposure summaries sharing the same entity and
period; positions are required for name-level alignment. An unstated horizon defaults
to one quarter.

This is not a sample-size problem. It is an extraction-and-labeling quality problem.
Before a real-letter alignment can render, precision and recall must each be at least
0.80 on the core extraction slots, and alignment accuracy must be at least 0.80 on a
synthetic corpus with planted truth. If the gate still fails after two prompt or model
iterations, the method remains limited to its synthetic demonstration.

Dead-bands must be calibrated on honest noisy paths to a false-contradiction target of
at most one view in twenty. Demo thresholds remain labelled illustrative and
uncalibrated. Missing provenance, exposure definitions, or temporal alignment produce
refusal, not an inferred label.

## Key takeaways

- Language models extract structured claims; deterministic code scores alignment.
- Every label needs the verbatim quote, measured path, and visible threshold.
- Unmappable views remain in the inventory and are never forced into a proxy.
- “Contradicted” means materially inconsistent under a stated rule, not dishonest.
- Real-letter output stays gated until slot-level extraction and alignment evaluation
  pass.

## References

- Armin Falk and Michael Kosfeld, “The Hidden Costs of Control,” *American Economic
  Review*, 2006.
- Marilyn Strathern, “‘Improving Ratings’: Audit in the British University System,”
  1997.
- Berkeley Dietvorst, Joseph Simmons, and Cade Massey, “Overcoming Algorithm Aversion,”
  *Management Science*, 2018.
- Christopher Manning, Prabhakar Raghavan, and Hinrich Schütze, *Introduction to
  Information Retrieval*.
