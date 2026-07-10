# E2 · Narrated Engagement-Pack Generator — Method Spec

**Status:** Reviewed — method gate passed 2026-07-07 (rulings in §8)
**Date:** 2026-07-07
**Card:** [`2026-07-05-idea-cards.md` → "E2 · Narrated engagement-pack generator"](../2026-07-05-idea-cards.md)
**Demo page:** rendered pack (`e2.html`), authored alongside the S2 tear sheet — the print-clean composition of one manager's certified sections.

---

## 1. What this is

E2 assembles one document. Every other card in this portfolio produces a
*fragment* — S1 a posterior strip on whether a manager's skill is real, S2 a
tear sheet of honest performance intervals, M1 a drift panel on exposures, M3 a
drawdown band, M5 a "say-do" row comparing what a manager wrote to what the book
did. None of those fragments is where the decision gets made. The decision gets
made over **one piece of paper an allocator reads across the table** in a
quarterly business review (QBR). E2 is the layer that takes a single manager's
certified fragments, orders them, drafts the connecting sentences between them,
and prints the result as one clean per-manager, per-quarter pack. That is the
whole product: a document, not an analytic.

The important word is *certified*. E2 **computes nothing of its own** — it holds
no estimator, runs no bootstrap, fits no model. It reads the JSON that the source
cards already emit (each number already carrying its interval and its source),
selects the sections this manager's data tier and the power gates permit, and
writes the prose that turns a grid of intervals into a conversation. Its entire
reason to exist is to do that composition **without ever softening the honesty
the source cards enforce**: every number still arrives with its interval and its
provenance, and the pack never states a claim the source card's own gate refuses.
The audience is the investment team preparing for a QBR; a manager-facing variant
comes later, inside the E1 transparency ladder, with adjustable controls.

- **Decisions improved:** **engage** (the QBR pack *is* the conversation
  artifact) and, transitively, the **adoption of every other card** — an
  analytic nobody reads improves no decision.
- **What it is not:** not an analytics engine (it holds no estimator), not a
  framework (right-level engineering: no plugin system before three real
  consumers exist), and not a model that writes numbers — the narration stage
  writes prose *around* certified numbers it may not alter or invent.

## 2. Why we use it

**The decision problem.** A quarterly review runs on a document. The team needs
one artifact per manager that says, honestly, where that manager stands — is the
performance real once you strip the accounting smoothing, does the book match
what the letters promised, is there enough track record to say anything at all —
and it needs that artifact to be trusted enough that the allocator reads it
instead of asking for "the real numbers" later. The naive alternative is a
dashboard: put every card's output in a web app and let the reader click through
tabs. We measured this failure mode directly (internal Sweep E): dashboards land
at roughly **25% adoption** — the separate-tab problem, where the analytic is
never wrong because it is never opened. Packaging is not decoration here; it is a
functional requirement. An analytic that improves no decision because nobody
reads it is a failure of E2's job, not of the analytic.

**Why a narrated pack is the dangerous-but-right answer.** The reason nobody has
just glued the fragments into one narrated PDF is that *narration is an honesty
problem*. The moment you let prose connect certified numbers, two failure modes
open up. First, **numbers drift from their sources**: a hand-written summary says
"a Sharpe near 0.7" when the certified value is 0.60 after de-smoothing, or
rounds an interval away, or quietly restates a point estimate without its band.
Second, **claims outrun their gates**: the prose asserts "the manager has genuine
skill" for a track record too short for any test to support that — the exact
false-precision the whole program exists to refuse. A dashboard is safer *only*
because it never writes a sentence. E2's bet is that you can have the sentence
*and* the safety, if — and only if — the connecting prose is generated into a
constrained slot and then checked, number by number, against the payload it came
from. That deterministic check is what makes narration safe to ship (§3, §6.2).
The pack wins the adoption a dashboard loses, without spending the honesty a
dashboard preserves by staying mute.

## 3. How it works

### 3.1 The mental model, before any notation

Picture the pack as a printing press with a strict foreman. There is a fixed
**menu of sections** the press *can* print (the section registry). For a given
manager, each menu item goes through two yes/no doors — is this manager's data
rich enough (the tier door) and is the track record long enough for this claim
(the power door) — and comes out in exactly one of **three states**:

- **rendered** — both doors passed; the section prints with its numbers and a
  lead-in sentence;
- **refused** — the section belongs to this manager's tier, but the track record
  is too short, so the section prints a *labelled empty state* saying what it
  would show and how much data it would need. The refusal is content, not a gap;
- **omitted** — the section needs a richer data tier than this manager has, so it
  does not print in the body but is **listed in a "not shown at this tier"
  footer** with the tier it would need. Absence is always disclosed.

The one rule that makes the whole thing trustworthy: **a section is never
silently dropped.** Every menu item ends in one of those three visible outcomes.

Then a narration stage writes the connecting sentences — and a lint reads every
number back out of those sentences and checks each one appears, verbatim, in the
section's certified payload. A single number in the prose that is not in the
payload fails the whole build.

### 3.2 A worked toy example

Take a manager, "Manager Q," at data tier **R** (returns only), with **48**
months of track record. Suppose a two-row registry (plus one higher-tier row):

| Section | `min_tier` | gated? | threshold |
| --- | --- | --- | --- |
| `tear_sheet` (from S2) | R | no | — |
| `posterior_standing` (from S1) | R | yes | needs a track long enough to separate a true information ratio of 0.5 from luck |
| `exposure_drift` (from M1) | E | — | — |

Walk each section through the two doors:

- **`tear_sheet`**: tier door — R ≥ R, passes. Not gated, so no power door. State
  = **rendered**. It prints, say, a reported Sharpe of `0.71` that de-smooths to
  `0.60`, and an alpha interval that spans zero.
- **`posterior_standing`**: tier door — R ≥ R, passes. Power door — at 48 months
  no track length in our sampler atlas separates a true IR of 0.5 from luck, so
  the door fails. State = **refused**. It prints the empty-state naming the metric
  and that 48 months is not enough.
- **`exposure_drift`**: tier door — this manager is tier R but the section needs
  tier E, R < E, fails. State = **omitted**, and it appears in the footer as
  "shown at tier E."

Now the narration. The tear-sheet lead-in is generated as: *"the reported Sharpe
of 0.71 pulls down to 0.60 once smoothing is undone."* The lint extracts the
numerals from that sentence — `{0.71, 0.60}` — and checks each is present in the
tear-sheet payload's numbers. Both are; the sentence passes. If a draft had
instead said *"a Sharpe near 0.7,"* the numeral `0.7` would not appear in the
payload (`0.71` and `0.60` do), and the pack build would fail. That is the entire
safety mechanism, and it is deliberately blunt.

### 3.3 The section registry — the complete contract

The pack is defined by a **section registry**: an ordered list of section
descriptors, each naming its source card, the payload key it renders, its
`min_tier`, and the power-gate metric key that governs it. The registry is a
committed table — one row per section — so a reviewer sees **every section the
pack can ever contain, and in what order, at a glance**. No section is conjured
by prose or by the narration stage; if it is not a registry row, it cannot
appear. Adding a card to the pack is adding a registry row, not writing code
(right-level engineering: this is a table, not a plugin system).

The registry is also what makes a killed analytic *structurally* unreachable. A
do-not-build analytic — persistence rankings, false-discovery luck-screens,
regime-split alphas, conditional betas, returns-based style-drift inference (the
convergence §6 kill list) — has **no registry row and no certified payload**. The
pack has nothing to render and nothing to narrate for it. The pack cannot smuggle
a claim no card is allowed to make, because there is no row through which to
smuggle it.

### 3.4 The two gates — what actually renders

Each registry section passes through two gates **in order**, and the outcome is
one of the three states from §3.1 — never a silent drop.

**Tier gate.** Order the data tiers `R < E < P` (returns-only < exposure < full
position-level). If the manager's tier is *below* the section's `min_tier`, the
section is **omitted** and listed in the footer with the tier it would need.

$$\text{state}(s) = \texttt{omitted} \quad \text{if} \quad \text{rank}(\text{tier}_\text{mgr}) < \text{rank}(s.\texttt{min\_tier})$$

where: $\text{tier}_\text{mgr}$ is the manager's inherited data tier;
$s.\texttt{min\_tier}$ is the section's minimum tier from its registry row; and
$\text{rank}$ maps $R \mapsto 0,\ E \mapsto 1,\ P \mapsto 2$. In words: a section
whose data requirement outranks the manager's tier is withheld from the body and
disclosed in the footer.

**Power gate.** For a section whose metric *is* gated, look up the X1 **PowerGate
registry** (`site/data/powergate_registry.json`, X1 §2) at this manager's
`gate_quantity` (the sample size that matters for that metric — months, trade
count, or exits). Let $q$ be that measured quantity and $\tau$ the registry
threshold for the metric. The section renders only if the measured power reaches
the threshold:

$$\text{state}(s) = \begin{cases} \texttt{rendered} & \text{if } q \ge \tau \\ \texttt{refused} & \text{if } q < \tau \text{ or } \tau = \varnothing \end{cases}$$

where: $q$ is the manager's measured `gate_quantity` for the section's metric;
$\tau$ is the metric's threshold in the X1 registry; and $\tau = \varnothing$
(null) is the *no-threshold* case — no track length in the measured range
suffices, so the section always refuses. In words: below the sample the metric
needs, the section renders the **refusal empty-state** — a dashed panel naming
the metric and the sample it would need — exactly as the standalone card would.
The refusal is content, not a gap.

The gating logic is **read-only against the registry**: E2 chooses no threshold.
A section's `min_tier` and the registry's $\tau$ are the source card's and X1's
constants respectively — flagged here as **inherited, not authored**, so the
numerics gate audits them in the X1 and S-card specs, not this one.

### 3.5 Honesty invariants — the load-bearing rules

These are enforced by the builder as **lint checks that fail the pack build**,
not as authoring conventions. This is the whole point of the card. (Rule
placement is settled in the method review below: the generic invariants INV-1 and
INV-2 extend the *shared* gallery lint; the pack-specific INV-3 and INV-4 live in
E2's own builder.)

- **INV-1 · No bare point.** Every statistic in the pack renders as an
  `IntervalStat` (a point plus its interval rail and range text) or a
  `VerdictChip` (a robust / shrink / noise label); a bare point estimate anywhere
  in the pack body is a build failure. E2 inherits S2's design-system lint
  (S2 §3) and extends it to the composed document — including into the narration
  prose (§3.6).
- **INV-2 · Number carries provenance.** Every rendered number traces to a
  payload `provenance` field naming its source card and metric. A number with no
  provenance chain cannot render (the payload contract, §6.1). The pack's footer
  lists, per section, which card certified it.
- **INV-3 · The pack never overrides a gate.** If a source card's power gate
  refuses a claim, the pack **cannot** assert it — not in a panel (§3.4) and not
  in prose (§3.6). Combined with the no-row-no-section structure (§3.3), a killed
  analytic is structurally unreachable: the pack cannot narrate a claim no card is
  allowed to make.
- **INV-4 · Provenance survives paper.** The SYNTHETIC badge and per-section
  provenance print (the print CSS keeps the badge visible on paper — `interval.css`
  `@media print`). An honest screen that becomes a dishonest printout is the
  failure mode this invariant closes.

### 3.6 The division of labor with the narration stage

E2 is a **deterministic composition pipeline with exactly one probabilistic
stage** (narration), and the division of labor mirrors M5's: the numbers are
fixed by the source cards, the composition is deterministic code, and the
language model *only* writes prose — prose that is checked against the numbers
before it renders. Four deterministic stages (registry → tier gate → power gate →
compose) plus one gated narration stage.

The narration stage's **only** job is the connective prose: the one- to
three-sentence lead-in that says *why this section matters for the decision*, and
the cross-section summary at the top. It is constrained hard:

- **Slot-filled, not free-form.** Narration is generated into a **structured
  template** whose numeric slots are filled **only** from the section's payload
  fields — the model receives the payload and a template and returns prose with
  the numbers already bound. It does not choose numbers; it phrases around them.
- **Numeric-faithfulness check (deterministic, post-generation).** Every numeral
  and interval in the generated prose must appear verbatim in the section's
  payload. A number in the narration that is **not** in the payload is a
  hallucination and **fails the pack** (INV-1/INV-2 in prose form). Nothing
  probabilistic ever touches a number — the check is set membership, not judgment.
  This is the zero-tolerance lint the whole design rests on: because it is a
  deterministic, cheap, post-hoc check, it is *what makes narration safe* (§6.2
  pins the gate at 1.00). This is the same posture as M5 §3.
- **Gate-respect check.** Narration for a section in the refused state may
  describe *what the metric would show and why it can't yet* — it may **never**
  assert the refused claim (INV-3).
- **Human-edited before ship.** The generated narration is a **draft**; the pack
  ships only after human edit (a card kill criterion). The manager-facing variant
  additionally exposes **adjustable-output controls** (Dietvorst): priors and
  alarm thresholds surfaced as controls, so the reader can move the assumption and
  watch the interval respond rather than accept a fixed verdict.

The narration harness itself is validated like M5's extraction harness (§6.2).

### 3.7 Composition output

The deterministic stages emit a single **pack payload** — an ordered list of
section render-states (rendered / refused / omitted) with their bound narration —
which the Jinja `pack-page` template (§6.3) renders to print-clean HTML. No
statistic is computed in this path; the pack is a **projection** of payloads that
already cleared their own cards.

### 3.8 What the RAG-faithfulness literature contributes

The numeric-faithfulness check is a specialization of a known idea from
retrieval-augmented generation (RAG). The RAGAS work (Es et al., 2023) formalized
**faithfulness** as the degree to which a model's generated text is *entailed by*
the retrieved context it was given, and showed it can be scored automatically
rather than by human annotation. What that literature showed and why it applies
here: a grounded generator should never assert content its context does not
support, and you can *measure* that support without a human in the loop. E2's
payload is the "retrieved context," the narration is the "generated text," and
faithfulness of *numbers* collapses to an exact set-membership test — which is why
E2 can demand a perfect score (1.00) for numerals where general RAG settles for a
graded one. The related M5 §4 harness evaluates the mirror-image task —
*extraction* faithfulness (did the model read the letter's claims correctly) —
and E2's *generation* harness reuses its shape; read them as a pair.

## 4. How to implement

Below is a **self-contained teaching implementation** of the compose-and-lint
pipeline: registry rows → the two gates → the numeric-faithfulness lint. It uses
only the standard library and invents its own tiny payloads so you can paste it
into a fresh file and run it. It is *not* the repo's code — it implements the
same logic §3 describes, at reading size.

```python
"""Minimal engagement-pack compose-and-lint pipeline (teaching version).

Mirrors the E2 method: a committed section registry, two ordered gates
(tier, then power), a three-state resolution (rendered / refused / omitted),
and a deterministic numeric-faithfulness lint over the narration prose.
No estimator lives here: numbers arrive already certified in `payloads`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# --- The section registry: the complete contract (one row per section). -------
# `min_tier` is the source card's constant; `gate_metric` names the power-gate
# key (None means the section is never power-gated). This is data, not logic.

TIER_RANK = {"R": 0, "E": 1, "P": 2}  # returns-only < exposure < position-level


@dataclass(frozen=True)
class SectionRow:
    section_id: str
    title: str
    source_card: str
    min_tier: str
    gate_metric: str | None  # None => not power-gated


REGISTRY: list[SectionRow] = [
    SectionRow("posterior_standing", "Posterior skill standing", "s1", "R", "ols_alpha_ttest"),
    SectionRow("tear_sheet", "Honest tear sheet", "s2", "R", None),
    SectionRow("exposure_drift", "Exposure hygiene & drift", "m1", "E", None),
]


# --- The two gates, in order. Each returns exactly one of three states. --------

def resolve_state(row: SectionRow, manager_tier: str, gate_quantity: int,
                  power_registry: dict[str, int | None]) -> str:
    """Resolve one registry row to 'rendered' | 'refused' | 'omitted'.

    Tier gate first (omitted-and-footnoted if the data tier is too low), then
    the power gate (refused empty-state if the sample is below threshold, or if
    the metric's threshold is null -- no sample in range suffices).
    """
    if TIER_RANK[manager_tier] < TIER_RANK[row.min_tier]:
        return "omitted"  # disclosed in the footer, never silently dropped
    if row.gate_metric is not None:
        threshold = power_registry.get(row.gate_metric)  # X1 constant, read-only
        if threshold is None or gate_quantity < threshold:
            return "refused"  # the empty-state is content, not a gap
    return "rendered"


# --- The numeric-faithfulness lint: the zero-tolerance safety check. -----------

_NUMERAL = re.compile(r"[-+]?\d[\d,]*\.?\d*%?")  # 0.71, +3.2%, -4.4%, 48, 95%


def numerals(text: str) -> set[str]:
    """Every number-shaped token in a string, as an exact-match set."""
    return {m.group() for m in _NUMERAL.finditer(text)}


def faithful(narration: str, payload_numbers: set[str]) -> tuple[bool, set[str]]:
    """A sentence is faithful iff every numeral in it is in the payload.

    Returns (is_faithful, offending_numerals). This is set membership, not
    judgment: one invented number is enough to fail the whole pack (the gate
    PACK_FAITHFULNESS_MIN = 1.00).
    """
    invented = numerals(narration) - payload_numbers
    return (len(invented) == 0, invented)


# --- Compose: registry rows -> resolved, lint-checked sections. ----------------

@dataclass
class PackSection:
    row: SectionRow
    state: str
    narration: str
    offending: set[str] = field(default_factory=set)


def compose(manager_tier: str, gate_quantity: int,
            power_registry: dict[str, int | None],
            payloads: dict[str, set[str]],
            narrations: dict[str, str]) -> list[PackSection]:
    """Project a manager's certified payloads into an ordered pack.

    `payloads[section_id]` is the set of certified number-strings for that
    section; `narrations[section_id]` is the (draft) connective prose. Omitted
    and refused sections carry no rendered numbers, so their narration is linted
    against whatever payload they do expose (e.g. a refusal's measured sample) --
    an invented number anywhere fails the build.
    """
    pack: list[PackSection] = []
    for row in REGISTRY:  # registry order is the pack order
        state = resolve_state(row, manager_tier, gate_quantity, power_registry)
        prose = narrations.get(row.section_id, "")
        payload_numbers = payloads.get(row.section_id, set())
        ok, invented = faithful(prose, payload_numbers)
        if not ok:
            # Fail loud: a plausible wrong number is worse than a missing one.
            raise ValueError(
                f"faithfulness lint failed in {row.section_id!r}: "
                f"{sorted(invented)} not in payload"
            )
        pack.append(PackSection(row, state, prose, invented))
    return pack


# --- A tiny run: Manager Q, tier R, 48 months. --------------------------------

if __name__ == "__main__":
    power_registry = {"ols_alpha_ttest": None}  # null threshold => always refuse
    payloads = {
        "tear_sheet": {"0.71", "0.60"},          # certified by S2
        "posterior_standing": {"48", "0.5"},     # refusal cites its own sample
        # exposure_drift omitted at tier R: no payload needed
    }
    narrations = {
        "tear_sheet": "The reported Sharpe of 0.71 pulls down to 0.60 once "
                      "smoothing is undone.",
        "posterior_standing": "At 48 months no track length separates a true "
                              "IR of 0.5 from luck; the pack shows the gate.",
    }

    pack = compose("R", 48, power_registry, payloads, narrations)
    for section in pack:
        print(f"{section.row.title:28} -> {section.state}")
    # Posterior skill standing     -> refused   (null threshold)
    # Honest tear sheet            -> rendered  (both gates pass, prose faithful)
    # Exposure hygiene & drift     -> omitted   (needs tier E)

    # A hallucinated number fails the build:
    try:
        compose("R", 48, power_registry,
                {"tear_sheet": {"0.71", "0.60"}},
                {"tear_sheet": "A Sharpe near 0.7 after de-smoothing."})
    except ValueError as exc:
        print("REJECTED:", exc)  # '0.7' is not in the payload
```

The two things to notice: the registry order *is* the pack order (no separate
ordering config), and the lint runs on every section — including refused ones,
whose only numbers are the sample the refusal cites — so an invented number
anywhere fails the build. A refusal that says "48 months" is fine only because
`48` is one of that section's certified payload fields.

## 5. Reading the demo

The demo page (`e2.html`) is the composed pack for one synthetic manager,
**Kestrelmoor Partners** (code M07), for **2021-Q2**, at data tier **R**
(returns only). It shows all three section states across four sections, so you
can see the honesty machinery working end-to-end. Every number below is verbatim
from the committed pack JSON.

**The header** gives the manager, tier, quarter, and a one-paragraph summary,
plus an honesty note stating the demo narration is **hand-authored and
human-edited** (the live build would draft it through the faithfulness harness).

**Section 1 — Posterior skill standing (from S1): refused.** This is the
power-gate empty-state made visible. The dashed `power-gate` panel says that at
**48** months, no track length in the sampler atlas separates a true information
ratio of **0.5** from luck (the threshold is null — the *no sample in range
suffices* case). The narration describes what the section *would* hold and why it
can't yet; it asserts no skill claim. Read it as: *we cannot honestly say whether
this manager has skill, and we are showing you that rather than guessing.*

**Section 2 — Honest tear sheet (from S2): rendered.** This is the fully rendered
state. You will see:

- an **interval band** (`interval-stat`) for the reported Sharpe: point **0.71**,
  95% interval **-0.26 … 1.67** — the band is the sampling uncertainty, the tick
  is the point estimate;
- a second interval band for the **de-smoothed Sharpe**: point **0.60**, 95%
  interval **-0.29 … 1.46** — de-smoothing (Getmansky–Lo–Makarov) undoes the
  volatility that smoothed marks hide, which is why 0.71 falls to 0.60;
- an annualized alpha of **+3.2%** with a **90% interval -4.4% … +10.8%** that
  still spans zero;
- a **verdict chip** reading **provisionally alternative beta** (a *shrink*
  verdict) — a track-length statement, not a verdict on skill.

Read it as: *the performance is real but modest once you strip smoothing, and the
alpha interval crossing zero means the track is too short to call it skill.*

**Section 3 — Say–do inventory (from M5): rendered.** Three stated views pulled
from the manager's letter — disciplined net exposure, a value tilt, trimmed
momentum — each printed as a quote with its direction and conviction (out of 3).
At tier R the pack lists *what the manager said*; the alignment of those words
against the *measured* book unlocks at tier E. Read it as: *here is the manager's
stated posture; whether the book matches it needs richer data.*

**Section 4 — Exposure hygiene & drift (from M1): omitted.** This section needs
tier E (exposure summaries) and Kestrelmoor is tier R, so it does not print in
the body. It appears in the **"Not shown at this tier"** footer as "shown at tier
E." Read it as: *this analysis exists but your data does not reach it — and we are
telling you so rather than leaving a silent hole.*

**What an allocator should conclude from this demo:** Kestrelmoor is a
returns-only manager with an honest but unremarkable tear sheet (Sharpe 0.60
de-smoothed, alpha spanning zero), too short a track record to certify skill (the
posterior stays gated), and a stated posture whose say-do check waits on richer
data. Nothing in the pack is asserted beyond what its source card certified — the
mapping is exactly one visual element per certified fact, and every absence is
disclosed.

## 6. Honest limits & go-live

### 6.1 Data contract per tier

E2's inputs are **not raw data** — they are the *certified render payloads* of
other cards. The tier axis therefore acts one level up: the pack renders only the
sections whose source card can stand at this manager's tier, and the manager's
tier is inherited from those cards, not re-derived here.

| Tier | Inputs E2 consumes | What the pack contains |
| --- | --- | --- |
| **R** | S1 posterior strip JSON; S2 tear-sheet JSON (de-smoothed Sharpe CI, interval alpha, alt-beta chip, drawdown band); M3 drawdown-alarm JSON; M5 view **inventory** (no alignment rung). | The returns-only pack: posterior standing, honest tear sheet, drawdown context, letter-view inventory. Every section present because every source card runs returns-only. |
| **E** | R payloads + M1 exposure-hygiene/drift JSON + M5 **alignment-vs-exposure** rows + S2's measured-vs-inferred exposure panel. | Adds the drift panel and the say–do alignment rows — the pack gains the "does the book match the mandate and the letter" spread. |
| **P** | E payloads + S2 holdings descriptors (active share, concentration) + M5 **name-level** alignment. | Adds position-level descriptors and name-level say–do — the fullest pack. |

**Payload contract (frozen interface E2 depends on).** Each source card's
`render.py` emits typed payloads — `IntervalStat` (point + interval rail + range
text), `VerdictChip` (robust / shrink / noise), `TierBadge`, `PowerGate`
(rendered or refused, with the effect size) — carrying a `provenance` field
naming the source card and the metric key. E2 **binds to these payload types,
never to the estimators behind them**: if S2 changes its bootstrap, E2 does not
change. A payload missing its `provenance` field is a build error (§3.5), not a
silent omission.

**Frequency & alignment:** the pack is assembled per manager per quarter; each
section carries its own as-of date from the source payload, and mixed cadences
(monthly tear sheet, quarterly letter) are labeled at the section header, never
silently aligned.

**Compliance (standing):** letter excerpts reach the pack only through M5's
already-cleared inventory (public fund letters only); E2 introduces no new data
source, so it inherits every source card's compliance posture unchanged.

### 6.2 Power & validation plan

E2 has **no statistical power of its own** — it estimates nothing, so it
contributes no cells to the X1 atlas grid. Its two validation obligations are
(a) that gating is correct and (b) that narration is faithful, and the second is
governed by a **structured-template eval harness modeled directly on M5 §4** (the
say–do card's harness is the template; E2 reuses its shape).

**Gating correctness (deterministic tests).** Over a fixture set of synthetic
managers spanning tiers R/E/P and sample sizes straddling each gated metric's
threshold, assert that every section resolves to the correct one of {rendered,
refused, omitted}: a below-threshold section renders the refusal state, an
above-tier section is omitted-and-footnoted, and no section is ever silently
dropped. These are unit tests, not power curves.

**Narration faithfulness (the eval harness, load-bearing).** Ground truth is by
construction: run narration over synthetic packs whose payloads are known, and
because the payload numbers are known, faithfulness is measurable without human
annotation (M5 §4's planted-truth pattern). Metrics, per pack:

1. **Numeric faithfulness** — fraction of numerals/intervals in the prose that
   appear in the payload:
   $$F = \frac{|\,\text{numerals}(\text{prose}) \cap \text{numerals}(\text{payload})\,|}{|\,\text{numerals}(\text{prose})\,|}$$
   where numerals(·) is the set of number-shaped tokens in the text. Gate:
   **`PACK_FAITHFULNESS_MIN` = 1.00** *(provisional — numerics gate)*: a single
   invented number fails the pack. Zero tolerance, because a plausible wrong
   number in an engagement pack is worse than a missing sentence.
2. **Hallucinated-claim rate** — count of asserted claims (numeric or verdict)
   with no payload support. Gate: **`PACK_HALLUCINATION_MAX` = 0** claims per pack
   *(provisional)*.
3. **Gate-respect accuracy** — fraction of refused-state sections whose narration
   correctly withholds the refused claim. Gate: **`PACK_GATE_RESPECT_MIN` = 1.00**
   *(provisional)*: never assert a gated-out claim.

**Go/no-go gate.** Meet all three on the synthetic pack corpus ⇒ auto-narration
drafts are allowed (still human-edited). Miss after **`PACK_EVAL_ITERATIONS` = 2**
prompt/model iterations *(provisional — mirrors M5's two-iteration kill)* ⇒ the
narration stage is **cut** and the pack ships with **section headers + template
captions only** (the deterministic composition still stands; the pack is less
warm but no less honest). Recorded in writing per converge-or-cut, never extended
silently.

**What this deliberately does not validate.** Not the source cards' statistics —
those are gated in their own specs and the X1 atlas. E2 asserting its own power
curve would be exactly the false-precision the program exists to refuse.

### 6.3 Implementation architecture

Module home: **`src/quant_allocator/flagships/packs/`** — a thin composition
layer, deliberately not a framework.

- `registry.py` — the section registry (§3.3): the committed ordered table of
  section descriptors (source card, payload key, `min_tier`, gate metric key).
  Data, not logic.
- `compose.py` — the deterministic pipeline: reads source-card payloads, applies
  the tier and power gates (§3.4) against `site/data/powergate_registry.json`,
  resolves each section to rendered/refused/omitted, and emits the **pack
  payload**. Pure function of (manager payloads, registry) → pack payload. No
  estimators, no I/O beyond reading committed JSON.
- `narrate.py` — the single narration stage: structured-template generation
  (§3.6) plus the deterministic numeric-provenance and gate-respect checks.
  Returns bound narration or fails loud.
- `harness.py` — the narration eval harness (§6.2): runs `narrate` over the
  synthetic pack corpus, computes faithfulness / hallucination / gate-respect,
  emits the pass/fail verdict.

**Render path (already exists — E2 adds no rendering engine).** The pack is
rendered by the gallery's existing Jinja builder (`site/templates/` +
`src/quant_allocator/site/build.py`): the `pack-page` container and the print CSS
(`interval.css` `@media print`, `@page` A4 margins) are **already built and
amortized** — the E1 ladder and S2 pack are the wave-1 print showcases E2
generalizes. The builder's iron rule holds: **`build.py` computes nothing and
imports no numpy/pandas/simulator** (gallery design §5) — it renders committed
pack JSON. E2 respects this exactly: `packs/` produces the JSON, the builder
renders it.

**Demo vs. live.**

- **Demo (wave-2, alongside S2):** the pack generator runs offline on the
  **committed section JSON already in `site/data/`** (S1/S2/M5 payloads that ship
  the gallery), producing one manager's committed pack JSON; **CI renders only**.
  Narration in the demo is **hand-authored / human-edited** (the honest mockup
  states the live build adds the auto-narration harness). The demo shows a real
  refusal state and a real omitted-at-tier footer — the honest-mockup contract's
  "working PowerGates" clause, at pack altitude.
- **Live:** `python -m quant_allocator.packs render --manager <id>` composes from
  the source cards' live payloads and drafts narration through the gated harness
  for human edit.

**Dependencies:** the source cards' `render.py` payload contracts (S1, S2, M1, M3,
M5); the X1 PowerGate registry (hard prerequisite for the power gate — no
registry, no gating, so E2's gated sections stay demo-only until X1 vol. 1 lands);
a language-model client for `narrate.py` only. No new runtime numeric dependency.

**Effort:** **S per increment** (card estimate). The composition is small; the
narration harness is the real work and is scoped like M5's. E2 is **born inside
S2** (S2's single-manager pack is pack v0.1) and **formalized only after two more
consumers exist** (M-lane monitors) — the card's own anti-framework rule.

### 6.4 Go-live requirements

- **Data ask:** none of its own — E2 inherits each constituent card's ask (S1/S2
  returns for the R pack; M1/M5-E for the exposure spread; S2-P/M5-P for
  name-level). The pack degrades exactly as its sections do.
- **Sample required:** none of its own — the pack's *sections* carry the sample
  gates (the X1 registry). E2's go-live prerequisite is that the **PowerGate
  registry exists** (X1 vol. 1) so the power gate is real and not a stub.
- **Narration gate:** auto-narration renders only after the eval harness (§6.2)
  passes at `PACK_FAITHFULNESS_MIN` / `PACK_HALLUCINATION_MAX` /
  `PACK_GATE_RESPECT_MIN`; below gate after `PACK_EVAL_ITERATIONS` iterations ⇒
  ship deterministic captions only. **All narration is human-edited before ship
  regardless** (narration ships only human-edited — card rule).
- **Build effort:** **S per increment**; born inside S2, formalized after two more
  consumers.
- **Go-live box (demo page):** data ask = inherited per section; sample =
  inherited (registry-gated); effort = S.

### 6.5 Adoption & packaging

The pack **is** the kill-the-dashboard argument as a working artifact — so the
packaging doctrine is the product, not decoration (Sweep E):

- **Narrated artifact at the decision moment, not a dashboard.** The pack is a
  document the allocator reads in the meeting, print-clean on one A4 flow — not a
  tab someone has to remember to open. Adoption is the metric the card exists to
  move; a beautiful analytic nobody reads is a failure of E2, not of the analytic.
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

**Who sees what, when:** the internal team gets the full pack at QBR prep; the
manager-facing variant ships only inside the E1 ladder relationship, with
adjustable controls and the human-edited narration, framed as reciprocity.

## 7. Deeper reading

*The spec program doubles as a curriculum; this section collects what to defend
unaided.*

**The ideas worth owning.**

- **Why dashboards die and narrated artifacts live.** The ≈25%-adoption /
  separate-tab failure mode is a *delivery* failure, not an analytics failure: the
  analytic is never wrong, it is never opened. The fix is to move the artifact to
  the decision moment and give it a narrative spine — the same information,
  re-packaged, gets used. Own the argument that **packaging is a functional
  requirement**, and that E2 buying adoption for the whole portfolio is worth more
  than any single new estimator.
- **Composition-over-computation as an architecture.** E2 holds no estimator by
  design: it binds to *payload contracts* (`IntervalStat`, `VerdictChip`,
  `PowerGate`), so a source card can change its internals without touching the
  pack. Own why binding to the *rendered honest output* — not to the math — is
  what lets the honesty invariants (§3.5) be enforced in **one** place instead of
  re-audited per card, and why a do-not-build analytic is *structurally*
  unreachable (no payload, no section) rather than merely discouraged.
- **Structured-template LLM eval, applied to generation not extraction.** M5
  evals *extraction* (did the model read the letter right); E2 evals *generation*
  (did the model write only what the payload supports). The shared design: **ground
  truth by construction** (known payloads), **deterministic post-checks**
  (numeric-provenance, gate-respect), and a **hard faithfulness gate at 1.0**
  because in an engagement pack a confidently wrong number is costlier than a
  missing one. This is the RAG-faithfulness posture — the model is grounded to a
  retrieved context (the payload) and scored on not departing from it.
- **Dietvorst adjustable outputs, at document scale.** Fixed verdicts get
  shelved; adjustable, advice-framed outputs get used. Surfacing priors and
  thresholds as controls in the manager-facing pack is the algorithm-aversion
  antidote applied to a whole document, not one chart.

**Canonical references (3–4 to own).**

1. **Dietvorst, Simmons & Massey (2018), "Overcoming Algorithm Aversion,"
   *Management Science*.** The paper showed people reject an algorithm's forecasts
   after seeing it err, but *keep* using it if they can adjust its output even
   slightly — so advice-framed, adjustable outputs get adopted where fixed
   verdicts get shelved. It governs the manager-facing controls and the
   "conversation, not verdict" posture.
2. **Falk & Kosfeld (2006), "The Hidden Costs of Control," *AER*.** The paper
   showed that visible control signals *reduce* the controlled party's cooperation
   — being policed crowds out goodwill. It is the help-not-audit framing the
   narration must preserve, since the pack is the manager-facing surface where a
   policing tone would withdraw the transparency every section depends on.
3. **RAG faithfulness / grounding (e.g., Es et al., 2023, *RAGAS*).** The work
   showed a generator's fidelity to its retrieved context can be scored
   automatically as *faithfulness* — the fraction of generated claims entailed by
   the context — without human labels. That is exactly E2's numeric-provenance
   check; own the metric and why 1.0 is the only defensible gate for numbers in a
   client document.
4. **M5 §4 (this repo).** The structured-template eval harness E2's narration
   harness is modeled on; read them as a pair (extraction vs. generation).

**Questions you should be able to answer after reading this page.**

- Why *cannot* E2 smuggle a killed analytic into a pack through prose? (INV-3 plus
  the no-payload-no-section structure of §3.3 — there is no registry row to
  narrate through.)
- State the three pack section-states and say why *omitted-and-footnoted* beats
  *silently dropped*.
- Explain why the faithfulness gate is **1.0 and not 0.95** — why a graded
  faithfulness score is acceptable for general RAG prose but not for numbers in an
  engagement pack.
- Walk the tear-sheet lead-in through the numeric-faithfulness lint and show what
  a hand-written "a Sharpe near 0.7" would do to the build.

---

## Method review (2026-07-07) — APPROVED, implementation-ready

- **Faithfulness gate RULED:** 1.0 zero-tolerance applies to NUMERIC
  faithfulness (any number in prose that mismatches its payload = build failure —
  deterministic check, cheap). Narrative paraphrase quality is human-reviewed per
  the human-edit-regardless rule; no numeric relaxation.
- **INV lint placement RULED (split):** generic invariants (INV-1 bare-point,
  INV-2 provenance) extend the SHARED gallery lint; pack-specific invariants
  (INV-3 gate-respect, INV-4) live in E2's builder. One rule, one home.
- **Narration harness RULED:** reuse M5's synthetic fixtures first, extend with
  pack-level fixtures only where composition introduces new failure modes; detail
  belongs to the build plan.
- Standing dependency honestly stated: the pack's power gate is only as real as
  the X1 PowerGate registry — E2's build order follows the registry, and wave-2's
  demo uses the sampler thresholds with the null-threshold refusal state as
  certified in Plan D.
