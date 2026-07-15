# Quant Allocator Editorial System

**Status:** Binding reader-facing specification

**Approved direction:** 2026-07-15 reader-journey audit and the user's instruction
to harden the findings and begin implementation

**Higher authority:** `docs/PRODUCT.md`

**Evidence record:** `docs/audits/2026-07-15-reader-journey-audit.md`

## 1. Purpose and authority boundary

Quant Allocator is a curriculum and research publication before it is an archive or
evidence browser. This document governs the order, framing, navigation, and responsive
presentation of public pages.

The authority split is deliberate:

- `docs/PRODUCT.md` governs the product objective and platform boundary.
- This document governs the public reader experience.
- Each reviewed method specification governs that article's arithmetic, definitions,
  claims, and go-live constraints.
- Committed JSON and generators govern displayed quantitative values.

Public editing may shorten, reorder, illustrate, or progressively disclose reviewed
material. It may not change a quantitative claim, remove a material limitation, or
promote a readiness state without the corresponding numerical and publication checks.

## 2. Audit verdict

The current site is visually coherent and technically functional, but its public
reading order is harness-first. It exposes internal method metadata, governance
furniture, multiple competing taxonomies, and implementation records before the
reader reaches the motivating problem, numerical example, or focal visual.

The correction is an editorial projection over the existing research substrate, not a
new platform and not a numerical rewrite.

Preserve these strengths:

- the thesis, restrained paper-and-ink visual system, and readable prose measure;
- intervals, provenance labels, maturity labels, and explicit refusal states;
- synthetic/public-data disclosure and fictional displayed names;
- concrete worked examples such as S2's unsmoothing calculation;
- semantic headings, skip navigation, visible focus, and precomputed interactions;
- the reviewed method specifications and committed exhibit data.

## 3. One primary information architecture

### 3.1 Homepage order

The homepage has one primary path and three secondary discovery layers, in this order:

1. Publication thesis and reader promise.
2. A short guided Start Here curriculum.
3. Five research pillars as the primary corpus taxonomy.
4. A compact featured/latest reading list.
5. The full browse and filter tool as optional discovery.

Do not present Start Here, pillars, featured exhibits, allocator journey, and the
catalog as equal first-level choices. Allocator stage, evidence availability, maturity,
and asset/vehicle scope are filters. They are not parallel site architectures.

The homepage must not render an empty stage. A control labelled as a view switch must
change the organization it names; a compactness switch must instead be labelled
`Detailed` / `Compact`.

Every research entry exposes two unambiguous actions where both surfaces exist:

- `Read article`
- `View exhibit`

The global `Exhibits` destination must be a complete exhibit index. If only a subset is
shown, label it `Featured exhibits`.

### 3.2 Start Here curriculum

The initial route is:

1. **S2 · Uncertainty-honest tear-sheet engine**
   - Trap: treating a point estimate as evidence.
   - Ability: read track-record statistics as uncertain estimates and know when to
     refuse a conclusion.
2. **S1 · Hierarchical Bayesian alpha engine**
   - Trap: treating a noisy ranking as a ranking of manager skill.
   - Ability: understand shrinkage, partial pooling, and posterior rank uncertainty.
3. **M3 · Simulation-calibrated drawdown alarms**
   - Trap: applying the same flat drawdown threshold to unlike managers.
   - Ability: compare a realized drawdown with the manager-specific null and treat an
     alarm as a review trigger rather than an automatic redemption.

Each step states the entering trap, the ability gained, reading time, difficulty, and
why the following step comes next. X1 and X2 remain advanced reference tools rather
than introductory lessons.

## 4. Public article contract

### 4.1 Source separation

The reviewed method specification and the public article are distinct sources:

- The method specification remains complete and unchanged unless a claim or method is
  being corrected.
- The public article is explicitly referenced by the card manifest when available.
- Until a public article exists, the legacy specification rendering may remain as a
  temporary fallback, clearly treated as unmigrated content.
- The public page links to `Technical method and provenance` separately from the main
  narrative.

Repository dates, review status, card IDs, source paths, demo filenames, implementation
dockets, verbatim execution output, reconciliation records, and review rulings do not
belong in the main narrative.

### 4.2 Reading sequence

Every migrated article follows this sequence:

1. Decision or problem in concrete terms.
2. Short thesis stating what changes and why it matters.
3. The familiar but naive approach and its failure mechanism.
4. Intuition in plain language.
5. A small numerical example with every step interpreted.
6. Formal method and notation, with every symbol defined near first use.
7. One decisive inline visual or paired exhibit state.
8. Interpretation: what the result permits, refuses, or changes.
9. Limitations, failure conditions, and go-live evidence.
10. What the allocator would do next.
11. Key takeaways, references, and the next curriculum step.

The formula never carries the explanation alone. Motivation precedes notation; the
numerical example follows closely enough that the reader does not need to remember an
uninterpreted definition across several sections.

### 4.3 Reading scaffolding

A migrated article provides:

- pillar, curriculum position, reading time, and difficulty;
- a short contents list when the article has more than four major sections;
- stable heading anchors;
- a paired exhibit link near the opening and closing;
- `Previous in this path` and `Next in this path`, distinct from publication chronology;
- internal links to published articles rather than GitHub source files.

The main prose remains approximately 65–75 characters per line. Long tables scroll
inside their own containers. Teaching code is selective and explained; complete
implementation listings belong in the technical record.

## 5. Public exhibit contract

The default exhibit order is:

1. Decision question.
2. One-sentence focal takeaway or honest refusal.
3. Main visual, comparison, or worked state.
4. `How to read this` beside or immediately after the visual.
5. Interpretation and decision implication.
6. Further analysis or optional interaction.
7. Limitations.
8. Collapsed `Evidence and readiness` appendix containing provenance, access,
   attestation, validation, data requirements, and methodology.
9. Reciprocal article link and next curriculum step.

The governance information remains present and testable; progressive disclosure changes
its prominence, not its correctness.

Visuals answer a named question. Each quantitative figure includes a visible scale or
units, a benchmark/zero/threshold where relevant, a legend or direct labels, and one
annotation identifying the decision-relevant pattern. A visual is followed immediately
by prose explaining what changed and what did not.

Browser JavaScript may switch among committed states or map values to pixels. It may not
recompute estimators.

## 6. Dense-page rules

- **S1:** narrate three focal managers before offering the complete roster. Interval
  rails share visible anchors and scales.
- **X2:** lead with one instructed before/after comparison. Keep the active inputs and
  resulting outputs visible together, make transparency the primary control, and state
  the reason when a verdict changes.
- **E4 and S7:** open on one narrated decision state. Move receipt tables, audit
  registers, and advanced controls behind clearly labelled technical details.
- **X3:** explain the coverage question and one representative cell before exposing the
  full control and evidence surface.

These are progressive-disclosure requirements, not permission to remove provenance or
refusal states.

## 7. Responsive and accessibility contract

At a 390px viewport:

- the document body has no horizontal overflow;
- display mathematics wraps when safe or scrolls within its own labelled container;
- tables and dense figures scroll within bounded regions rather than widening the page;
- interactive targets are at least 44px by 44px;
- chart labels remain legible or the page uses a mobile-specific simplified figure;
- the menu does not obscure the first meaningful content after interaction;
- color is not the only indication of selection, interval standing, or refusal.

Every chart exposes visible labels sufficient for a sighted reader and an equivalent
text interpretation for assistive technology. Focus order, focus visibility, headings,
landmarks, reduced motion, and theme contrast are part of the rendered gate.

## 8. Implementation and review boundary

Use the existing Python/Jinja static generator, design tokens, committed data, and
page-specific exhibit code. Add a public-article source boundary and shared reader-facing
shells incrementally.

Implement one vertical slice at a time:

1. S2 article and exhibit pilot.
2. Homepage and Start Here route.
3. Shared article/exhibit rollout.
4. Dense-page exceptions.
5. One consolidated rendered and publication gate.

Run targeted tests and rendered checks during each slice. Do not restart whole-corpus
numerical review when only copy order, markup, or CSS changes. A numerical re-review is
required only when displayed values, calculations, statistical claims, or their semantic
interpretation change.

## 9. Non-goals

- No CMS, backend, database, account system, subscription system, or platform layer.
- No new estimator or synthetic-data campaign for this editorial restructure.
- No reopening parked P4 work.
- No pixel clone of Aligrithm and no copying its sepia skin, three-column density, or
  exhaustive route tables.
- No removal of uncertainty, limitations, provenance, or publication safeguards.
- No push, merge, or publication without their separate explicit authority flags.

## 10. Acceptance

The reader-first restructure is complete when:

- a first-time reader can identify one recommended route from the homepage;
- every migrated article begins with the problem and reaches a numerical example or
  decisive visual before implementation/governance detail;
- every migrated exhibit presents its focal evidence before the full readiness record;
- article/exhibit and curriculum continuation work in both directions;
- the homepage, every migrated page, and all dense exceptions pass desktop and 390px
  rendered checks without body overflow;
- all existing quantitative and publication tests remain green;
- the final review finds no unresolved reader-journey or accessibility blocker.
