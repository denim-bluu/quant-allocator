# E2 · Narrated Engagement-Pack Generator — Method Spec

**Status:** Draft — pending method review
**Date:** 2026-07-07
**Card:** [`2026-07-05-idea-cards.md` → "E2 · Narrated engagement-pack generator"](../2026-07-05-idea-cards.md)
**Demo page:** rendered pack (`e2.html`), authored alongside the S2 tear sheet — the print-clean composition of one manager's certified sections.

---

## 1. Problem & decision hook

Every other card in the portfolio produces a *fragment* — S1 a posterior strip,
S2 a tear sheet, M1 a drift panel, M3 a drawdown band, M5 a say–do row. In the
meeting, none of those fragments is where the decision happens; the decision
happens over **one document the allocator reads across the table**. Dashboards
die (Sweep E: ≈25% adoption, the separate-tab failure mode); a narrated
artifact delivered at the decision moment gets used. E2 is the **composition
layer**: one command assembles a manager's certified fragments into a single
per-manager, per-quarter, print-clean pack, with the narration that turns a
grid of intervals into a conversation.

E2 **computes nothing of its own**. It is delivery infrastructure: it reads the
JSON the source cards already emit, selects the sections the manager's tier and
the PowerGate registry permit, orders them, and drafts the connective prose
under an eval harness. Its entire value is that it does this **without ever
softening the honesty the source cards enforce** — every number still arrives
with its interval and its provenance, and the pack never states a claim the
source card's own PowerGate refuses.

- **Decisions improved:** **engage** (the QBR pack is the conversation
  artifact) and, transitively, the **adoption of every other card** — an
  analytic nobody reads improves no decision.
- **Customer:** the investment team (QBR / meeting prep); a manager-facing
  variant later, inside the E1 ladder, with adjustable-output controls.
- **What it is not:** not an analytics engine (it holds no estimator), not a
  framework (right-level engineering: no plugin system before three real
  consumers exist), and not an LLM that writes numbers — the model narrates
  *around* certified numbers it may not alter or invent.

## 2. Data contract per tier

E2's inputs are **not raw data** — they are the *certified render payloads* of
other cards. The tier axis therefore acts one level up: the pack renders only
the sections whose source card can stand at this manager's tier, and the
manager's tier is inherited from those cards, not re-derived here.

| Tier | Inputs E2 consumes | What the pack contains |
| --- | --- | --- |
| **R** | S1 posterior strip JSON; S2 tear-sheet JSON (de-smoothed Sharpe CI, interval alpha, alt-beta chip, drawdown band); M3 drawdown-alarm JSON; M5 view **inventory** (no alignment rung). | The returns-only pack: posterior standing, honest tear sheet, drawdown context, letter-view inventory. Every section present because every source card runs returns-only. |
| **E** | R payloads + M1 exposure-hygiene/drift JSON + M5 **alignment-vs-exposure** rows + S2's measured-vs-inferred exposure panel. | Adds the drift panel and the say–do alignment rows — the pack gains the "does the book match the mandate and the letter" spread. |
| **P** | E payloads + S2 holdings descriptors (active share, concentration) + M5 **name-level** alignment. | Adds position-level descriptors and name-level say–do — the fullest pack. |

**Payload contract (frozen interface E2 depends on).** Each source card's
`render.py` emits typed payloads — `IntervalStat` (point + interval rail +
range text), `VerdictChip` (robust / shrink / noise), `TierBadge`,
`PowerGate` (rendered or refused, with the effect size) — carrying a
`provenance` field naming the source card and the metric key. E2 **binds to
these payload types, never to the estimators behind them**: if S2 changes its
bootstrap, E2 does not change. A payload missing its `provenance` field is a
build error (§3.3), not a silent omission.

**Frequency & alignment:** the pack is assembled per manager per quarter;
each section carries its own as-of date from the source payload, and mixed
cadences (monthly tear sheet, quarterly letter) are labeled at the section
header, never silently aligned.

**Compliance (standing):** letter excerpts reach the pack only through M5's
already-cleared inventory (public fund letters only); E2 introduces no new
data source, so it inherits every source card's compliance posture unchanged.

## 3. Methodology

E2 is a **deterministic composition pipeline with one LLM stage** (narration),
and the division of labor mirrors M5's: the numbers are fixed by the source
cards and the composition is deterministic code; the LLM only writes prose, and
what it writes is checked against the numbers before it renders. Four
deterministic stages plus one gated narration stage.

### 3.1 Section registry — what can appear at all

The pack is defined by a **section registry**: an ordered list of section
descriptors, each naming its source card, the payload key it renders, its
`min_tier`, and the PowerGate metric key that governs it. The registry is a
committed table (one row per section), so a reviewer sees every section the
pack can ever contain, and in what order, at a glance — no section is
conjured by prose or by the LLM. Adding a card to the pack is adding a
registry row, not writing code (right-level: this is a table, not a plugin
system).

### 3.2 Tier-and-power gating — what actually renders

Each registry section passes through two gates in order, and the outcome is
one of three states — **never** a silent drop:

1. **Tier gate.** If the manager's tier `<` the section's `min_tier`, the
   section is **omitted** and listed in the pack's "not shown at this tier"
   footer with the tier it would need. Absence is itself disclosed.
2. **Power gate.** For a section whose metric is gated, look up the X1
   **PowerGate registry** (`site/data/powergate_registry.json`, X1 §2) at this
   manager's `gate_quantity` (N, trade count, exits). If measured power `<` the
   registry threshold, the section renders the **PowerGate refusal
   empty-state** — the dashed panel naming the metric and the N it would need —
   exactly as the standalone card would. *The refusal is content, not a gap.*

The gating logic is **read-only against the registry**: E2 chooses no
threshold. The section's `min_tier` and the registry's `threshold` are the
source card's and X1's constants respectively — flagged here as **inherited,
not authored**, so the numerics gate audits them in X1/S-card specs, not
this one.

### 3.3 Honesty invariants — the load-bearing rules

These are enforced by the builder as **lint checks that fail the pack build**,
not as authoring conventions. This is the whole point of the card.

- **INV-1 · No bare point.** Every statistic in the pack renders as an
  `IntervalStat` or a `VerdictChip`; a bare point estimate anywhere in the pack
  body is a build failure. E2 inherits S2's design-system lint (S2 §3) and
  extends it to the composed document — including into narration prose (§3.4).
- **INV-2 · Number carries provenance.** Every rendered number traces to a
  payload `provenance` field naming its source card and metric. A number with
  no provenance chain cannot render (the payload contract, §2). The pack's
  footer lists, per section, which card certified it.
- **INV-3 · The pack never overrides a gate.** If a source card's PowerGate
  refuses a claim, the pack **cannot** assert it — not in a panel (§3.2) and
  not in prose (§3.4). A killed or do-not-build analytic (persistence
  rankings, FDR luck-screens, regime-split alphas, conditional betas,
  returns-based style-drift inference — convergence §4) has **no registry
  section and no certified payload**, so it is structurally unreachable: the
  pack cannot narrate a claim no card is allowed to make.
- **INV-4 · Provenance survives paper.** The SYNTHETIC badge and per-section
  provenance print (the print CSS already keeps the badge visible on paper,
  `interval.css` `@media print`). An honest screen that becomes a dishonest
  printout is the failure mode this invariant closes.

### 3.4 Narration under a structured-template harness

The LLM's **only** job is the connective prose: the one- to three-sentence
lead-in that says *why this section matters for the decision* and the
cross-section summary at the top. It is constrained hard:

- **Slot-filled, not free-form.** Narration is generated into a **structured
  template** whose numeric slots are filled **only** from the section's
  payload fields — the model receives the payload and a template, and returns
  prose with the numbers already bound. It does not choose numbers; it phrases
  around them.
- **Numeric-provenance check (deterministic, post-generation).** Every numeral
  and interval in the generated prose must appear verbatim in the section's
  payload. A number in the narration that is **not** in the payload is a
  hallucination and **fails the pack** (INV-1/INV-2 in prose form). This is the
  same posture as M5 §3: nothing probabilistic touches a number.
- **Gate-respect check.** Narration for a section in the refusal state may
  describe *what the metric would show and why it can't yet* — never assert the
  refused claim (INV-3).
- **Human-edited before ship.** LLM narration is a **draft**; the pack ships
  only after human edit (card kill criterion). The manager-facing variant
  additionally exposes **adjustable-output controls** (Dietvorst): priors and
  alarm thresholds surfaced as controls, so the reader can move the assumption
  and watch the interval respond rather than accept a fixed verdict.

The narration harness itself is validated like M5's extraction harness (§4).

### 3.5 Composition output

The deterministic stages emit a single **pack payload** — an ordered list of
section render-states (rendered / refused / omitted) with their bound narration
— which the Jinja `pack-page` template (already in the gallery, §5) renders to
print-clean HTML. No statistic is computed in this path; the pack is a
**projection** of payloads that already cleared their own cards.

## 4. Power & validation plan

E2 has **no statistical power of its own** — it estimates nothing, so it
contributes no cells to the X1 atlas grid. Its two validation obligations are
(a) that gating is correct and (b) that narration is faithful, and the second
is governed by a **structured-template eval harness modeled directly on M5 §4**
(the say–do card's harness is the template; E2 reuses its shape).

**Gating correctness (deterministic tests).** Over a fixture set of synthetic
managers spanning tiers R/E/P and N spanning each gated metric's threshold,
assert that every section resolves to the correct one of {rendered, refused,
omitted}: a below-threshold section renders the refusal state, an
above-tier section is omitted-and-footnoted, and no section is ever silently
dropped. These are unit tests, not power curves.

**Narration faithfulness (the eval harness, load-bearing).** Ground truth is by
construction: run narration over synthetic packs whose payloads are known, and
because the payload numbers are known, faithfulness is measurable without human
annotation (M5 §4's planted-truth pattern). Metrics, per pack:

1. **Numeric faithfulness** — fraction of numerals/intervals in the prose that
   appear in the payload. Gate: **`PACK_FAITHFULNESS_MIN` = 1.00**
   *(provisional — numerics gate)*: a single invented number fails the
   pack. Zero tolerance, because a plausible wrong number in an engagement pack
   is worse than a missing sentence.
2. **Hallucinated-claim rate** — count of asserted claims with no payload
   support (numeric or verdict). Gate: **`PACK_HALLUCINATION_MAX` = 0** claims
   per pack *(provisional)*.
3. **Gate-respect accuracy** — fraction of refused-state sections whose
   narration correctly withholds the refused claim. Gate:
   **`PACK_GATE_RESPECT_MIN` = 1.00** *(provisional)*: never assert a gated-out
   claim.

**Go/no-go gate.** Meet all three on the synthetic pack corpus ⇒ auto-narration
drafts are allowed (still human-edited). Miss after **`PACK_EVAL_ITERATIONS` =
2** prompt/model iterations *(provisional — mirrors M5's two-iteration kill)* ⇒
the LLM narration stage is **cut** and the pack ships with **section headers +
template captions only** (the deterministic composition still stands; the pack
is less warm but no less honest). Recorded in writing per converge-or-cut,
never extended silently.

**What this deliberately does not validate.** Not the source cards' statistics
— those are gated in their own specs and the X1 atlas. E2 asserting its own
power curve would be exactly the false-precision the program exists to refuse.

## 5. Implementation architecture

Module home: **`src/quant_allocator/flagships/packs/`** — a thin composition
layer, deliberately not a framework.

- `registry.py` — the section registry (§3.1): the committed ordered table of
  section descriptors (source card, payload key, `min_tier`, gate metric key).
  Data, not logic.
- `compose.py` — the deterministic pipeline: reads source-card payloads,
  applies the tier and power gates (§3.2) against
  `site/data/powergate_registry.json`, resolves each section to
  rendered/refused/omitted, and emits the **pack payload**. Pure function of
  (manager payloads, registry) → pack payload. No estimators, no I/O beyond
  reading committed JSON.
- `narrate.py` — the single LLM stage: structured-template generation (§3.4)
  plus the deterministic numeric-provenance and gate-respect checks. Returns
  bound narration or fails loud.
- `harness.py` — the narration eval harness (§4): runs `narrate` over the
  synthetic pack corpus, computes faithfulness / hallucination / gate-respect,
  emits the pass/fail verdict.

**Render path (already exists — E2 adds no rendering engine).** The pack is
rendered by the gallery's existing Jinja builder (`site/templates/` +
`src/quant_allocator/site/build.py`): the `pack-page` container and the print
CSS (`interval.css` `@media print`, `@page` A4 margins) are **already built and
amortized** — the E1 ladder and S2 pack are the wave-1 print showcases E2
generalizes. The builder's iron rule holds: **`build.py` computes nothing and
imports no numpy/pandas/simulator** (gallery design §5) — it renders committed
pack JSON. E2 respects this exactly: `packs/` produces the JSON, the builder
renders it.

**Demo vs. live.**

- **Demo (wave-2, alongside S2):** the pack generator runs offline on the
  **committed section JSON already in `site/data/`** (S1/S2/M5 payloads that
  ship the gallery), producing one manager's committed pack JSON; **CI renders
  only**. Narration in the demo is **hand-authored / human-edited** (the honest
  mockup states the live build adds the auto-narration harness). The demo shows
  a real refusal state and a real omitted-at-tier footer — the honest-mockup
  contract's "working PowerGates" clause, at pack altitude.
- **Live:** `python -m quant_allocator.packs render --manager <id>` composes
  from the source cards' live payloads and drafts narration through the gated
  harness for human edit.

**Dependencies:** the source cards' `render.py` payload contracts (S1, S2, M1,
M3, M5); the X1 PowerGate registry (hard prerequisite for the power gate — no
registry, no gating, so E2's gated sections stay demo-only until X1 vol. 1
lands); an LLM client for `narrate.py` only. No new runtime numeric dependency.

**Effort:** **S per increment** (card estimate). The composition is small; the
narration harness is the real work and is scoped like M5's. E2 is **born inside
S2** (S2's single-manager pack is pack v0.1) and **formalized only after two
more consumers exist** (M-lane monitors) — the card's own anti-framework rule.

## 6. Adoption & packaging

The pack **is** the kill-the-dashboard argument as a working artifact — so the
packaging doctrine is the product, not decoration (Sweep E):

- **Narrated artifact at the decision moment, not a dashboard.** The pack is a
  document the allocator reads in the meeting, print-clean on one A4 flow — not
  a tab someone has to remember to open. Adoption is the metric the card
  exists to move; a beautiful analytic nobody reads is a failure of E2, not of
  the analytic.
- **Help, not audit — inherited, not re-litigated.** Every section's copy
  doctrine is already set by its source card (S2's calibration-not-accusation
  chips, M5's "communication drift worth a conversation"). E2's job is to **not
  break it** in the connective prose: the linted style guide (help-not-audit
  patterns as lint, not tribal knowledge) runs over the narration.
- **Adjustable outputs in any manager-facing version.** Dietvorst: priors and
  thresholds are controls, so the manager can move an assumption and see the
  interval move — the pack opens a conversation, it does not deliver a verdict.
- **Right-level, enforced.** One small app maximum; no plugin architecture, no
  templating DSL, no config system for section order (it is a committed table)
  **until three real consumers exist**. The card's scope kill criterion is a
  first-class design constraint, restated in the registry's one-table form.

**Who sees what, when:** the internal team gets the full pack at QBR prep;
the manager-facing variant ships only inside the E1 ladder relationship, with
adjustable controls and the human-edited narration, framed as reciprocity.

## 7. Go-live requirements

- **Data ask:** none of its own — E2 inherits each constituent card's ask
  (S1/S2 returns for the R pack; M1/M5-E for the exposure spread; S2-P/M5-P for
  name-level). The pack degrades exactly as its sections do.
- **Sample required:** none of its own — the pack's *sections* carry the
  sample gates (the X1 registry). E2's go-live prerequisite is that the
  **PowerGate registry exists** (X1 vol. 1) so the power gate is real and not a
  stub.
- **Narration gate:** auto-narration renders only after the eval harness (§4)
  passes at `PACK_FAITHFULNESS_MIN` / `PACK_HALLUCINATION_MAX` /
  `PACK_GATE_RESPECT_MIN`; below gate after `PACK_EVAL_ITERATIONS` iterations ⇒
  ship deterministic captions only. **All narration is human-edited before
  ship regardless** (LLM narration ships only human-edited — card rule).
- **Build effort:** **S per increment**; born inside S2, formalized after two
  more consumers.
- **Go-live box (demo page):** data ask = inherited per section; sample =
  inherited (registry-gated); effort = S.

## 8. Learning notes

*The spec program doubles as a curriculum; this is what to defend unaided.*

- **Why dashboards die and narrated artifacts live.** The ≈25%-adoption /
  separate-tab failure mode is a *delivery* failure, not an analytics failure:
  the analytic is never wrong, it is never opened. The fix is to move the
  artifact to the decision moment and give it a narrative spine — the same
  information, re-packaged, gets used. Own the argument that **packaging is a
  functional requirement**, and that E2 buying adoption for the whole portfolio
  is worth more than any single new estimator.
- **Composition-over-computation as an architecture.** E2 holds no estimator
  by design: it binds to *payload contracts* (`IntervalStat`, `VerdictChip`,
  `PowerGate`), so a source card can change its internals without touching the
  pack. Own why binding to the *rendered honest output* — not to the math — is
  what lets the honesty invariants (§3.3) be enforced in **one** place instead
  of re-audited per card, and why a do-not-build analytic is *structurally*
  unreachable (no payload, no section) rather than merely discouraged.
- **Structured-template LLM eval, applied to generation not extraction.** M5
  evals *extraction* (did the model read the letter right); E2 evals
  *generation* (did the model write only what the payload supports). The shared
  design: **ground truth by construction** (known payloads), **deterministic
  post-checks** (numeric-provenance, gate-respect), and a **hard faithfulness
  gate at 1.0** because in an engagement pack a confidently wrong number is
  costlier than a missing one. This is the RAG-faithfulness posture — the model
  is grounded to a retrieved context (the payload) and scored on not departing
  from it.
- **Dietvorst adjustable outputs, at document scale.** Fixed verdicts get
  shelved; adjustable, advice-framed outputs get used. Surfacing priors and
  thresholds as controls in the manager-facing pack is the algorithm-aversion
  antidote applied to a whole document, not one chart.
- **Canonical references (3–4 to own):**
  1. Dietvorst, Simmons & Massey (2018), "Overcoming Algorithm Aversion,"
     *Management Science* — adjustable, advice-framed outputs get adopted;
     verdicts get shelved. Governs the manager-facing controls and the
     "conversation, not verdict" posture.
  2. Falk & Kosfeld (2006), "The Hidden Costs of Control," *AER* — the
     help-not-audit framing the narration must preserve, since the pack is the
     manager-facing surface where a policing tone withdraws the transparency
     every section depends on.
  3. The **RAG faithfulness / grounding** literature (e.g., Es et al. 2023,
     *RAGAS*) — faithfulness of generated text to a retrieved context is exactly
     E2's numeric-provenance check; own the metric and why 1.0 is the only
     defensible gate for numbers in a client document.
  4. M5 §4 (this repo) — the structured-template eval harness E2's narration
     harness is modeled on; read them as a pair (extraction vs. generation).

- **Defend unaided:** explain why E2 *cannot* smuggle a killed analytic into a
  pack through prose (INV-3 + the no-payload-no-section structure); state the
  three pack section-states and why *omitted-and-footnoted* beats *silently
  dropped*; and explain why the faithfulness gate is 1.0 and not 0.95.
</content>
</invoke>

---

## Method review (2026-07-07) — APPROVED, implementation-ready

- **Faithfulness gate RULED:** 1.0 zero-tolerance applies to NUMERIC
  faithfulness (any number in prose that mismatches its payload = build
  failure — deterministic check, cheap). Narrative paraphrase quality is
  human-reviewed per the human-edit-regardless rule; no numeric relaxation.
- **INV lint placement RULED (split):** generic invariants (INV-1 bare-point,
  INV-2 provenance) extend the SHARED gallery lint; pack-specific invariants
  (INV-3 gate-respect, INV-4) live in E2's builder. One rule, one home.
- **Narration harness RULED:** reuse M5's synthetic fixtures first, extend
  with pack-level fixtures only where composition introduces new failure
  modes; detail belongs to the build plan.
- Standing dependency honestly stated: the pack's power gate is only as real
  as the X1 PowerGate registry — E2's build order follows the registry, and
  wave-2's demo uses the sampler thresholds with the null-threshold refusal
  state as certified in Plan D.
