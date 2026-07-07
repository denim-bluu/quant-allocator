# M5 · Say–Do Gap Monitor — Method Spec

**Date:** 2026-07-06
**Status:** Reviewed (2026-07-06) — implementation-ready
**Card:** [`2026-07-05-idea-cards.md` → "M5 · Say–do gap monitor"](../2026-07-05-idea-cards.md)
**Demo page:** [`2026-07-05-wave1-gallery-design.md` §5 "M5 · Say–do split screen"](../../superpowers/specs/2026-07-05-wave1-gallery-design.md)

---

## 1. Problem & decision hook

Letters exist for every manager — they are the one universal, R-tier source
of stated views — while the book that expresses those views is observable
only at E or P for the transparent subset. The question the team asks by hand
each quarter — *does the portfolio match the letter?* — is the reconciliation
nobody does systematically. M5 extracts each stated view, scores it against the
measured book, and surfaces the drift between narrative and positioning with
the quote and the measurement side by side.

- **Decisions improved:** **monitor** (narrative-vs-book drift is an early
  warning that leads the return series) and **engage** (a specific, sourced
  talking point beats a generic quarterly template).
- **Customer:** investment team; meeting-prep for engagement conversations.
- **What it is not:** not a redemption trigger, not an audit verdict, and never
  a claim about a real letter the eval harness (§4) has not cleared first. A
  contradiction is "communication drift worth a conversation," full stop.

## 2. Data contract per tier

The card degrades by tier: extraction runs everywhere; alignment claims appear
only where measured positioning exists.

| Tier | Inputs the live version needs | What the card produces |
| --- | --- | --- |
| **R** | Manager letters (PDF/text), dated. Public fund letters only in the repo. | View **inventory** and **internal-consistency-over-time** (has a stated view flipped between letters without acknowledgement?). **No alignment claims** — there is nothing measured to align against. |
| **E** | R + exposure summaries: factor betas, sector weights, duration buckets, gross/net — per period, aligned to letter dates. | Adds alignment of each view against the matching **exposure bucket** (direction and magnitude of the tilt over the stated horizon). |
| **P** | E + position/holdings files. | Adds **name-level** alignment (the specific positions that do or do not express the view). |

**Frequency & alignment:** exposures/positions at each manager's native
cadence (monthly E, quarterly-or-better P); letters at their publication dates.
A view is scored over its **stated horizon**, defaulting to **one quarter**
when the letter leaves horizon unstated.

**Compliance (standing):** letters committed to the public repo are public
fund letters from unaffiliated managers only — never a filer with an implied
relationship to the employer's roster.

## 3. Methodology

Two stages, hard division of labor: **the LLM only reads text; the scoring is
deterministic code.** Nothing probabilistic touches the label.

### 3.1 View extraction (LLM structured output)

Each letter is parsed into zero or more **views**. A view is:

- **direction** ∈ {long/constructive, short/cautious, neutral-explicit}
- **theme** — free text (e.g., "US front-end duration", "energy equities")
- **instrument mapping** — the measurable handle: a factor, sector, asset
  class, or duration bucket that the E/P feed reports
- **horizon** — stated, or the literal value `"unstated"`
- **conviction** ∈ {1, 2, 3} — read from hedging language (1 = heavily hedged
  "we are watching…", 3 = unhedged "we have materially added…")
- **quote span** — the verbatim sentence(s) the view is drawn from
- **letter date**

Every extracted view **carries its verbatim quote**: claims always ship with
receipts. A view whose theme cannot be mapped to any instrument the feed
reports is retained in the inventory but marked **unmappable** and never
scored — the card does not invent a measurement to match a sentence.

### 3.2 Alignment scoring (deterministic)

For each mapped view, take the manager's measured series for that instrument
(E tier: the exposure bucket; P tier: the net position in the named exposure)
and compare the **stated direction** against the **realized level or change**
over the horizon. Each instrument class carries a materiality threshold `δ`
(the dead-band below which a move is noise, not a statement) calibrated from
the simulator's honest-wander distribution (§4):

- **aligned** — the realized exposure moves in the stated direction by at least
  `δ` within the horizon (for `neutral-explicit`, the exposure *stays* within
  `±δ` of its start).
- **contradicted** — the realized exposure moves **against** the stated
  direction by at least `δ`. *Worked rule:* stated `short/cautious` on duration
  **and** a measured duration extension ≥ 0.5y within the horizon ⇒
  **contradicted**.
- **partial** — direction is correct but the move stays inside the dead-band,
  or the sign is right but the timing falls outside the stated horizon.

Thresholds `δ` are per-instrument-class constants (duration in years, factor
beta in beta units, sector in weight ppt), declared in one table so a reviewer
sees every rule at once. The output row is always `{quote, extracted view,
measured series over horizon, label}` — presented, never editorialized.

## 4. Power & validation plan

**This is the load-bearing section.** M5 is not a small-N statistical problem;
it is an **extraction-and-labeling-accuracy** problem, and the instrument that
governs it is the **synthetic-letter eval harness**. No claim about a real
letter is ever displayed unless the harness has passed.

**Ground-truth by construction.** The synthetic-letter corpus generator
(wave-3 stretch substrate) emits letters from simulator ground truth with
**planted views** whose agreement labels are known by construction: for a
given synthetic manager whose true exposure path is set by the simulator, a
letter is written to *agree*, *partially agree*, or *contradict* that path on
each planted view. Because the generator plants the schema slots and the truth
labels, both extraction correctness and alignment correctness are measurable
without human annotation.

**Metrics (per schema slot, not aggregate).** Report extraction
**precision/recall per slot** — direction, theme-mapping, instrument mapping,
horizon, conviction, quote-span — because a single aggregate accuracy hides a
slot that is failing (e.g., 0.9 overall while conviction is a coin flip).
Separately report **alignment-label accuracy** (aligned/partial/contradicted
vs. the planted truth) as a 3×3 confusion matrix, so a directional bias
(over-calling "contradicted") is visible.

**Go/no-go gate.** Extraction **precision ≥ 0.8 AND recall ≥ 0.8** on the
core slots, **and** alignment accuracy ≥ 0.8. Meet the gate ⇒ the real-letter
rung is allowed to render. Miss it after **two prompt/model iterations** ⇒ the
card **stays demo-only** — this is the kill criterion, recorded in writing per
converge-or-cut, not extended silently.

**Threshold calibration.** The dead-bands `δ` (§3.2) are set from the
simulator: run honest-but-noisy managers whose book genuinely tracks the
letter and choose `δ` so their false-contradiction rate sits at a stated
budget (target ≤ 1-in-20 views). "Contradicted" then means *materially
inconsistent*, not *moved a basis point*.

**Demo vs. live.** The wave-1 demo renders **illustrative** extraction from a
hand-authored synthetic letter (three excerpts, one contradiction as the visual
centerpiece), with the honesty note — carried by the page badge and go-live
box — that the live build requires this harness to pass.

## 5. Implementation architecture

Module home: **`quant_allocator/flagships/saydo/`**

- `extraction.py` — LLM structured-output calls returning the §3.1 view
  schema; one call per letter, schema-validated on return; unmappable views
  flagged, not dropped.
- `alignment.py` — **deterministic** scoring: instrument→series resolver,
  the `δ` threshold table, the aligned/partial/contradicted rule engine, and
  the side-by-side output rows. No LLM in this file.
- `harness.py` — the eval harness: loads the synthetic corpus, runs extraction
  and alignment against planted truth, emits per-slot precision/recall, the
  alignment confusion matrix, and the pass/fail gate verdict.

**Dependencies:** the **synthetic-letter corpus generator** (wave-3 stretch
substrate, shared with E3) is a hard prerequisite for the harness and thus for
any real-letter claim; exposure/position series come from simulator emissions
(demo) and the E/P adapters (live). The demo page's exposure paths come from
`demo_data/m5_saydo.py`, with the letter excerpts and annotations as authored
constants there.

**Effort:** M–L, harness included — the extraction prompt and corpus generator
are the real work; the alignment engine is small and testable.

**Sequencing:** demo pulled forward into wave 1; hardened build after the
corpus generator; first lane-4 (AI/ML) card in the post-buy-in order; gateway
for E3, which shares the corpus and extraction layer.

## 6. Adoption & packaging

The output is **engagement material**, and the framing is load-bearing, not
cosmetic (Sweep E):

- **"Communication drift worth a conversation," never "caught you."** Falk &
  Kosfeld: monitoring that reads as policing makes the manager withdraw the
  very transparency (exposure, positions) the card depends on. A "say–do gap"
  headline that reads as a gotcha is a self-defeating design.
- **Receipts, no editorializing.** Every contradiction row shows the verbatim
  quote and the measured series **side by side** and stops there — the reader
  draws the conclusion. No adjectives, no score-shaming.
- **Never a mechanical trigger.** The monitor is an input to a conversation and
  a watchlist, never an automatic redemption rule. Goodhart: a say–do score
  published as a target gets optimized (managers write vaguer letters) rather
  than improved. The card's value is the conversation, so it is delivered as
  conversation material, not as a leaderboard.

**Who sees what, when:** internal team gets the full inventory + alignment at
meeting-prep time; any manager-facing version ships only inside the E1
transparency-ladder relationship, framed as help.

## 7. Go-live requirements

The demo page's "what this needs to go live" box, expanded:

- **Data ask:** letters (R) for the inventory rung; **+ exposure summaries (E)**
  for alignment; + positions (P) for name-level alignment. Repo letters:
  **public fund letters only**.
- **Sample required:** not a sample-size gate (this is a per-letter analytic).
  The gate is the **eval harness**: extraction precision ≥ 0.8 **and** recall
  ≥ 0.8, alignment accuracy ≥ 0.8 on the synthetic corpus, **before any real
  claim renders**.
- **Build effort:** **M–L**, including the harness and the dependency on the
  synthetic-letter corpus generator (wave-3 stretch).
- **Kill criterion:** below gate after two prompt/model iterations ⇒ card stays
  demo-only, recorded in writing.

## 8. Learning notes

*The spec program doubles as a curriculum; this is what to be able to defend
unaided.*

- **How to design an extraction eval.** Score **per schema slot** with
  precision/recall (and F1 where a single number is wanted per slot), not one
  aggregate accuracy. Aggregate accuracy averages over slots of different
  difficulty and hides a failing one — a 0.9 headline can carry a conviction
  slot at 0.5. Ground truth comes from **planting known labels at generation
  time** so no human annotation is needed and the eval is reproducible; the
  alignment label gets its own confusion matrix so directional bias
  (over-calling "contradicted") is visible, which a scalar accuracy would mask.
- **Goodhart's law, applied to publishing behavioral scores.** "When a measure
  becomes a target, it ceases to be a good measure" (Strathern's 1997
  formulation of Goodhart). A say–do score surfaced as a ranked target is gamed
  — managers write vaguer, less falsifiable letters — so the card ships as
  sourced conversation material, never as a mechanical rule or a leaderboard.
- **Falk–Kosfeld hidden-costs-of-control, in one paragraph.** In their 2006
  *AER* experiment, imposing even a mild control on an agent *reduced* the
  agent's effort versus the no-control condition: the control signaled
  distrust, and the signal itself was costly. For an external allocator this is
  load-bearing — a say–do monitor presented as an audit invites the manager to
  withdraw the exposure and position access the E/P rungs run on. The framing
  ("worth a conversation") is therefore a functional requirement, not courtesy.
- **Canonical references (3–4 to own):**
  1. Falk & Kosfeld (2006), "The Hidden Costs of Control," *American Economic
     Review* — the withdrawal-under-monitoring result the framing defends
     against.
  2. Goodhart's law (Strathern 1997, "'Improving ratings': audit in the
     British university system") — why a published behavioral target degrades.
  3. Dietvorst, Simmons & Massey (2018), "Overcoming Algorithm Aversion,"
     *Management Science* — adjustable, advice-framed outputs get used; verdicts
     get shelved. Governs the "input to judgment, not a verdict" posture.
  4. Manning, Raghavan & Schütze, *Introduction to Information Retrieval*
     (precision/recall/F1) — the standard basis for the per-slot extraction
     eval design.
