# M5 · Say–Do Gap Monitor — Method Spec

**Date:** 2026-07-06
**Status:** Reviewed (2026-07-06) — implementation-ready
**Card:** [`2026-07-05-idea-cards.md` → "M5 · Say–do gap monitor"](../2026-07-05-idea-cards.md)
**Demo page:** [`2026-07-05-wave1-gallery-design.md` §5 "M5 · Say–do split screen"](../../superpowers/specs/2026-07-05-wave1-gallery-design.md)

---

## 1. What this is

Every external manager writes letters. They are the one universal source of a
manager's *stated* views — what they say they believe and how they say they are
positioned. Separately, for the managers who share it, we can *measure* what the
book actually did: its factor exposures, sector weights, duration, net. M5 puts
those two things next to each other. It reads each stated view out of the letter,
finds the matching measurement, and reports — for each view — whether the book
moved the way the letter said it would. The output is a set of side-by-side rows:
the manager's own sentence on the left, the measured exposure path on the right,
and a one-word verdict.

The reader is the investment team, and the moment is meeting preparation. Before
an engagement call, someone wants to know: *does this manager's portfolio match
the story in their letter?* Today that reconciliation is done by hand, if at all,
one manager at a time. M5 does it systematically and hands back a sourced talking
point — a specific quote paired with a specific measurement — instead of a generic
quarterly template. It is deliberately **not** a redemption trigger, **not** an
audit verdict, and **never** a claim about a real letter until the evaluation
harness in §6 has cleared the extraction quality. A mismatch means "communication
drift worth a conversation," and nothing stronger.

## 2. Why we use it

The decision this feeds is **monitoring** a roster of managers and **preparing**
for the conversations that keep those relationships productive. The specific gap
it closes: a manager can *say* one thing in prose and *do* another in the book,
and by the time that divergence shows up in returns it is old news. Narrative-vs-
book drift tends to lead the return series — a manager who has quietly reversed a
stated tilt is telling you something before the P&L does. Catching it early is the
whole point.

Why don't the naive alternatives work?

- **Read the letters and trust them.** Letters are written to be read; they are
  the manager's best case for their own positioning. Taking them at face value
  measures nothing — it just re-states the manager's claim. The value is in the
  *reconciliation*, not the reading.
- **Watch the returns.** By the time a stated-but-abandoned view shows up as
  underperformance, the information is stale and confounded with everything else
  in the book. Returns are a lagging, low-resolution signal for "is the manager
  doing what they said."
- **Let an LLM read the letter and the exposures and just tell you if they
  agree.** This is the tempting one, and it is the trap. A language model asked
  to render a judgment ("aligned or contradicted?") produces a *plausible-sounding*
  label with no stable, auditable definition behind it. Re-run it and the label
  can move. Ask it about a borderline case and you cannot tell whether it applied
  a 0.05 threshold or a 0.30 one, because there is no threshold — there is a vibe.
  For an output that goes into a conversation with a manager, "the model felt it
  was a contradiction" is not defensible.

What M5 wins over all three is a verdict that is **cheap** (no waiting for
returns), **early** (it reads the letter the day it lands), and — critically —
**auditable**: every label is produced by a rule you can write on a whiteboard,
applied to a measurement you can point at, next to the exact sentence it judges.

## 3. How it works

### 3.1 The mental model, in prose

Think of it as an assembly line with two stations, and a strict rule about which
station is allowed to do which job.

**Station one reads. Station two scores.** A language model is *only* allowed to
read the letter and turn prose into structured facts: "this sentence expresses a
*cautious* view on *momentum*, over roughly *two quarters*, stated with *moderate*
conviction, and here is the verbatim sentence." That is a reading task —
extracting who-said-what — and language models are good at it. The model is **not**
allowed to decide whether the manager was right, aligned, or contradicted. That
judgment is handed to station two: plain deterministic code that looks up the
measured exposure, computes how far it moved, compares that to a fixed threshold,
and returns a label. The same inputs always produce the same label. There is no
model in station two.

The reason for the split is the trap from §2. Extraction is a reading problem the
LLM handles well; scoring is a judgment we need to be **reproducible and
defensible**, so we refuse to let anything probabilistic touch it. The label is a
consequence of a rule and a number, not an opinion.

Two facts fall out of this design that are worth stating plainly:

- **Claims always ship with receipts.** Every extracted view carries the exact
  sentence it came from. The output row shows the quote, so the reader can check
  the extraction themselves.
- **The card never invents a measurement.** If a view is about a theme we cannot
  map to any exposure the feed reports ("we like management's capital discipline"),
  the view is kept in the inventory but marked *unmappable* and never scored. We do
  not manufacture a number to match a sentence.

### 3.2 A worked toy example

Take one view. A manager's letter, dated April, says:

> "Given how crowded momentum has become, we have been trimming our exposure to
> the factor and expect to stay cautious."

Station one extracts: direction = **cautious/short**, instrument = **momentum
beta**, horizon = **two quarters**, conviction = **moderate**, plus that verbatim
sentence.

Station two now scores it. It looks up the manager's measured momentum beta:

- at the letter date it was **0.00**,
- two quarters later it was **+0.15**.

So the exposure **moved by +0.15** over the horizon. The manager said they were
getting *more cautious* on momentum — that is a stated move in the **negative**
direction. But the book went the other way: momentum beta rose. The dead-band for
factor betas is **δ = 0.10** (moves smaller than this are noise, not a statement).
The realized move against the stated direction is 0.15, which is bigger than 0.10,
so the verdict is **contradicted** — and the row shows the quote next to the
"0.00 → +0.15" path so the reader sees exactly why.

Change one number and the verdict changes. If the book had drifted only to
**+0.06**, the move (0.06) would be *inside* the dead-band — too small to call
either way — and the verdict would be **partial**, not contradicted. That is the
whole mechanism: a stated direction, a measured move, and a threshold.

### 3.3 The extraction schema (station one)

Each letter is parsed into zero or more **views**. A view is:

- **direction** ∈ {long/constructive, short/cautious, neutral-explicit}
- **theme** — free text (e.g., "US front-end duration", "energy equities")
- **instrument mapping** — the measurable handle: a factor, sector, asset class,
  or duration bucket that the E/P feed actually reports
- **horizon** — the stated horizon, or the literal value `"unstated"`
- **conviction** ∈ {1, 2, 3} — read from hedging language (1 = heavily hedged,
  "we are watching…"; 3 = unhedged, "we have materially added…")
- **quote span** — the verbatim sentence(s) the view is drawn from
- **letter date**

A view whose theme cannot be mapped to any instrument the feed reports is retained
in the inventory but marked **unmappable** and never scored.

### 3.4 The scoring rule (station two), stated formally

For a mapped view, take the manager's measured series for that instrument over the
view's horizon and compare the **stated direction** to the **realized move**.

**where:**

- **x(t)** — the measured exposure for the mapped instrument at time *t* (a factor
  beta in beta units, a sector in weight percentage points, duration in years, or
  net in the book's net unit).
- **t₀** — the letter date; **t₁** — the end of the view's stated horizon
  (defaulting to **one quarter** when the letter leaves the horizon unstated).
- **s = x(t₀)** — the exposure at the letter date ("start").
- **e = x(t₁)** — the exposure at the horizon end ("end").
- **m = e − s** — the realized **move** over the horizon.
- **σ** — the **stated-direction sign**: +1 for long/constructive, −1 for
  short/cautious. (neutral-explicit is handled separately below.)
- **δ** — the **dead-band** (materiality threshold) for that instrument's class: a
  per-instrument-class constant, the size below which a move is treated as noise
  rather than a statement.

For a **directional** view (long or short), define the **signed move in the stated
direction** as **σ · m**, and label:

- **aligned** — when **σ · m ≥ δ**.
  *In words: the exposure moved in the direction the manager stated, by at least
  the materiality threshold, within the horizon.*
- **contradicted** — when **σ · m ≤ −δ**.
  *In words: the exposure moved against the stated direction by at least the
  materiality threshold.*
- **partial** — otherwise: either **|σ · m| < δ** (the move is real but stays
  inside the dead-band, making no material statement), **or** the sign is right but
  the qualifying move only completes *after* the stated horizon ends.
  *In words: consistent-ish, but not a clean, on-time confirmation.*

*Worked rule (the canonical example):* a stated **short/cautious** view on
duration **and** a measured duration extension of **≥ 0.5y** within the horizon ⇒
**contradicted** (the book lengthened duration while the letter said it was getting
more defensive).

For a **neutral-explicit** view (the manager states they are staying flat), there
is no direction to move in; the claim is that the exposure *holds*. So:

- **aligned** — the exposure stays within **±δ** of its start across the horizon.
- **contradicted** — it leaves the **±δ** band (the manager said flat and it moved).

The thresholds **δ** are declared in **one table** — duration in years, factor beta
in beta units, sector in weight ppt, net in net units — so a reviewer sees every
rule at once. The output row is always `{quote, extracted view, measured series
over the horizon, label}`, presented and never editorialized.

**The distributional assumption is confined to δ, not the label.** Notice that
nothing in the labeling step is probabilistic: given *s*, *e*, and *δ*, the label
is fixed. The only place a distribution enters is *offline*, when we choose **δ**
so that an honest manager's ordinary book noise rarely trips a false
"contradicted" (§6). At scoring time, δ is just a number.

### 3.5 Why the label is never probabilistic — and why that is a feature

It would be easy to emit a *confidence*: "78% likely contradicted." We refuse to,
on purpose. A percentage implies a calibrated probability model we do not have and
would not be able to defend to a manager. Worse, it invites the reader to treat a
soft number as a hard fact. A one-word verdict backed by a **visible rule and a
visible measurement** is more honest than a spurious probability: the reader can
see the threshold, see the move, and disagree with the *rule* if they like —
which is exactly the kind of disagreement we want, because the rule is written
down. Reproducibility is the point. Run M5 twice on the same letter and book and
you get the same rows; that is a property a language-model judgment cannot promise.

## 4. How to implement

Below is a self-contained, from-scratch implementation of **station two** — the
deterministic alignment scorer. It implements exactly the rule in §3.4. Paste it
into a fresh file and adapt; it depends only on the standard library. (Station one,
the extraction call, is a separate concern: it produces the `view` dicts this code
consumes.)

```python
"""Deterministic say-do alignment scorer.

Station two of the say-do monitor. Consumes an extracted *view* (produced by an
LLM reading the letter) plus the manager's *measured exposure series*, and returns
one of three labels: "aligned", "partial", "contradicted". No model runs here --
the same inputs always yield the same label. The only tunable is the per-instrument
dead-band `delta`, chosen offline (see the calibration note in the spec).
"""

from __future__ import annotations

# Map the stated direction to a sign. neutral-explicit has no sign; it is scored
# by a separate "did it hold?" rule, so it is intentionally absent here.
DIRECTION_SIGN = {
    "long/constructive": +1.0,
    "short/cautious": -1.0,
}


def score_directional(start: float, end: float, direction: str, delta: float) -> str:
    """Label a directional (long or short) view.

    Parameters
    ----------
    start : float
        Measured exposure at the letter date, x(t0).
    end : float
        Measured exposure at the end of the stated horizon, x(t1).
    direction : str
        "long/constructive" or "short/cautious".
    delta : float
        Dead-band for this instrument class. Moves smaller than delta are noise.

    Returns
    -------
    str
        "aligned", "partial", or "contradicted".
    """
    sign = DIRECTION_SIGN[direction]          # sigma in the spec: +1 long, -1 short
    move = end - start                        # m = e - s, the realized move
    signed_move = sign * move                 # sigma * m: move *in the stated direction*

    if signed_move >= delta:
        # Moved the way the manager said, by at least the materiality threshold.
        return "aligned"
    if signed_move <= -delta:
        # Moved against the stated direction by at least the threshold.
        return "contradicted"
    # Real move, but inside the dead-band: no material statement either way.
    return "partial"


def score_neutral(series: list[float], delta: float) -> str:
    """Label a neutral-explicit view (manager states they are staying flat).

    The claim is that the exposure *holds*, so we check the whole horizon, not just
    the endpoints: aligned only while every point stays within +/- delta of the
    start; contradicted once it leaves the band.

    Parameters
    ----------
    series : list[float]
        Measured exposure at each observation in the horizon, in time order.
        series[0] is the value at the letter date.
    delta : float
        Dead-band for this instrument class.
    """
    start = series[0]
    worst_excursion = max(abs(x - start) for x in series)  # furthest it wandered
    if worst_excursion <= delta:
        return "aligned"
    return "contradicted"


def score_view(view: dict, series: list[float], delta_table: dict[str, float]) -> str:
    """Score one extracted view against its measured series.

    `view` must carry: "direction", "instrument". `series` is the measured
    exposure over the horizon, in time order (series[0] at the letter date,
    series[-1] at the horizon end). `delta_table` maps instrument -> dead-band.

    An unmappable view (no instrument in the delta table) is never scored -- the
    card does not invent a measurement to match a sentence.
    """
    instrument = view["instrument"]
    if instrument not in delta_table:
        return "unmappable"  # kept in the inventory, but no label is asserted

    delta = delta_table[instrument]
    direction = view["direction"]

    if direction == "neutral-explicit":
        return score_neutral(series, delta)
    return score_directional(series[0], series[-1], direction, delta)


if __name__ == "__main__":
    # Reproduces the three demo rows. Dead-bands are illustrative, uncalibrated.
    delta_table = {"beta_value": 0.10, "beta_momentum": 0.10, "net": 0.05}

    # View 2: long value tilt, book leaned in -> aligned.
    print(score_view(
        {"direction": "long/constructive", "instrument": "beta_value"},
        series=[0.017, 0.190], delta_table=delta_table,
    ))  # -> aligned  (signed move +0.173 >= 0.10)

    # View 3: cautious on momentum, but momentum beta rose -> contradicted.
    print(score_view(
        {"direction": "short/cautious", "instrument": "beta_momentum"},
        series=[-0.214, -0.011], delta_table=delta_table,
    ))  # -> contradicted  (signed move -0.203 <= -0.10)

    # View 1: stated flat net, book held at 0.20 -> aligned.
    print(score_view(
        {"direction": "neutral-explicit", "instrument": "net"},
        series=[0.20, 0.20, 0.20], delta_table=delta_table,
    ))  # -> aligned  (never left +/- 0.05 of start)
```

The three `__main__` cases reproduce the demo's three rows exactly, which is the
point: the labels on the gallery page are what this rule returns, not what a model
guessed.

## 5. Reading the demo

The gallery page renders **illustrative** extraction from one hand-authored
synthetic letter — manager **Kestrelmoor Partners**, three stated views, with one
contradiction as the visual centerpiece. Here is how each visual element maps to
the method, and what the numbers say.

- **A row** = one extracted view. Left side ("Said") is station one's output: the
  verbatim quote, the direction, the theme, and a three-dot conviction meter. Right
  side ("Did") is station two's input and output: the measured exposure path over
  the 6-month horizon, its start → end with the realized move, the dead-band δ, and
  the verdict chip.
- **The sparkline** is the measured series x(t) — the actual exposure path the rule
  reads.
- **The dead-band δ** is the materiality threshold from §3.4. On the page it is
  labeled **"illustrative, uncalibrated"** because in the demo δ is a placeholder,
  not a simulator-calibrated number — the honesty note that must travel with it.
- **The verdict chip** is the one-word label — green for **aligned**, red for
  **contradicted** — produced by the deterministic rule, not by a model.

What an allocator should conclude from the actual numbers:

- **Value tilt (aligned).** The letter says the manager leaned into value; the
  measured value beta rose from **+0.017 to +0.190** (a **+0.173** move), well past
  the **0.10** dead-band in the stated direction. Say and do agree.
- **Net exposure (aligned).** The letter says the book stayed at a disciplined net;
  the measured net held flat at **0.20** the whole horizon, never leaving the
  **±0.05** band. Say and do agree.
- **Momentum (contradicted — the centerpiece).** The letter says they were
  *trimming momentum and staying cautious*; the measured momentum beta **rose** from
  **−0.214 to −0.011**, a **+0.203** move *against* the stated cautious direction,
  more than twice the **0.10** dead-band. This is the one row worth a conversation —
  not an accusation, a specific, sourced question to ask.

## 6. Honest limits & go-live

### 6.1 Data contract per tier

The card degrades by tier: extraction runs everywhere; alignment claims appear only
where measured positioning exists.

| Tier | Inputs the live version needs | What the card produces |
| --- | --- | --- |
| **R** | Manager letters (PDF/text), dated. Public fund letters only in the repo. | View **inventory** and **internal-consistency-over-time** (has a stated view flipped between letters without acknowledgement?). **No alignment claims** — there is nothing measured to align against. |
| **E** | R + exposure summaries: factor betas, sector weights, duration buckets, gross/net — per period, aligned to letter dates. | Adds alignment of each view against the matching **exposure bucket** (direction and magnitude of the tilt over the stated horizon). |
| **P** | E + position/holdings files. | Adds **name-level** alignment (the specific positions that do or do not express the view). |

**Frequency & alignment:** exposures/positions at each manager's native cadence
(monthly E, quarterly-or-better P); letters at their publication dates. A view is
scored over its **stated horizon**, defaulting to **one quarter** when the letter
leaves horizon unstated.

**Compliance (standing):** letters committed to the public repo are public fund
letters from unaffiliated managers only — never a filer with an implied
relationship to the employer's roster.

### 6.2 The evaluation harness — the load-bearing gate

M5 is not a small-N statistical problem; it is an **extraction-and-labeling-
accuracy** problem, and the instrument that governs it is the **synthetic-letter
eval harness**. **No claim about a real letter is ever displayed unless the harness
has passed.**

**Ground truth by construction.** A synthetic-letter corpus generator (a shared
substrate) emits letters from simulator ground truth with **planted views** whose
agreement labels are known by construction: for a synthetic manager whose true
exposure path the simulator sets, a letter is written to *agree*, *partially
agree*, or *contradict* that path on each planted view. Because the generator
plants both the schema slots and the truth labels, extraction correctness and
alignment correctness are both measurable without any human annotation.

**Metrics, per schema slot, not aggregate.** Report extraction **precision and
recall per slot** — direction, theme-mapping, instrument mapping, horizon,
conviction, quote-span — because a single aggregate accuracy hides a slot that is
failing (0.9 overall while conviction is a coin flip). Separately report
**alignment-label accuracy** (aligned/partial/contradicted vs. the planted truth)
as a **3×3 confusion matrix**, so a directional bias — over-calling "contradicted"
— is visible.

**Go/no-go gate.** Extraction **precision ≥ 0.8 AND recall ≥ 0.8** on the core
slots, **and** alignment accuracy **≥ 0.8**. Meet the gate ⇒ the real-letter rung
is allowed to render. Miss it after **two prompt/model iterations** ⇒ the card
**stays demo-only** — the kill criterion, recorded in writing per converge-or-cut,
not extended silently.

**Threshold calibration.** The dead-bands **δ** (§3.4) are set from the simulator:
run honest-but-noisy managers whose book genuinely tracks the letter, and choose δ
so their false-contradiction rate sits at a stated budget (target **≤ 1-in-20
views**). "Contradicted" then means *materially inconsistent*, not *moved a basis
point*.

**Demo vs. live.** The wave-1 demo renders illustrative extraction from a
hand-authored synthetic letter (three excerpts, one contradiction as the
centerpiece), with the honesty note — carried by the page badge and the go-live box
— that the live build requires this harness to pass.

### 6.3 Go-live requirements

- **Data ask:** letters (R) for the inventory rung; **+ exposure summaries (E)**
  for alignment; **+ positions (P)** for name-level alignment. Repo letters:
  **public fund letters only**.
- **Sample required:** not a sample-size gate (this is a per-letter analytic). The
  gate is the **eval harness**: extraction precision ≥ 0.8 **and** recall ≥ 0.8,
  alignment accuracy ≥ 0.8 on the synthetic corpus, **before any real claim
  renders**.
- **Build effort:** **M–L**, including the harness and the dependency on the
  synthetic-letter corpus generator.
- **Kill criterion:** below gate after two prompt/model iterations ⇒ card stays
  demo-only, recorded in writing.

### 6.4 How the output must be framed (not cosmetic)

The output is **engagement material**, and the framing is load-bearing:

- **"Communication drift worth a conversation," never "caught you."** Monitoring
  that reads as policing makes a manager withdraw the very transparency (exposure,
  positions) the card depends on. A "say–do gap" headline that reads as a gotcha is
  self-defeating.
- **Receipts, no editorializing.** Every contradiction row shows the verbatim quote
  and the measured series **side by side** and stops there — the reader draws the
  conclusion. No adjectives, no score-shaming.
- **Never a mechanical trigger.** The monitor is an input to a conversation and a
  watchlist, never an automatic redemption rule. A say–do score published as a
  target gets optimized (managers write vaguer letters) rather than improved; the
  card's value is the conversation, so it ships as conversation material, not a
  leaderboard.

**Who sees what, when:** the internal team gets the full inventory + alignment at
meeting-prep time; any manager-facing version ships only inside the transparency-
ladder relationship, framed as help.

### 6.5 Implementation architecture

Module home: **`quant_allocator/flagships/saydo/`**

- `extraction.py` — station one: LLM structured-output calls returning the §3.3
  view schema; one call per letter, schema-validated on return; unmappable views
  flagged, not dropped.
- `alignment.py` — station two: **deterministic** scoring — the instrument→series
  resolver, the δ threshold table, the aligned/partial/contradicted rule engine
  (§3.4), and the side-by-side output rows. No LLM in this file.
- `harness.py` — the eval harness: loads the synthetic corpus, runs extraction and
  alignment against planted truth, emits per-slot precision/recall, the alignment
  confusion matrix, and the pass/fail gate verdict.

The synthetic-letter corpus generator is a hard prerequisite for the harness and
thus for any real-letter claim. Exposure/position series come from simulator
emissions (demo) and the E/P adapters (live). The demo page's exposure paths, the
letter excerpts, and the annotations are authored constants.

## 7. Deeper reading

### 7.1 The canonical references, and what each buys us

1. **Falk & Kosfeld (2006), "The Hidden Costs of Control," *American Economic
   Review*.** In a principal–agent experiment, imposing even a mild control on an
   agent *reduced* the agent's effort relative to the no-control condition: the
   control signaled distrust, and the signal itself was costly. This is why M5's
   framing ("worth a conversation," never an audit) is a functional requirement —
   a say–do monitor presented as policing invites the manager to withdraw the
   exposure and position access the E/P rungs run on.
2. **Goodhart's law — Strathern's (1997) formulation, "'Improving ratings':
   audit in the British university system."** "When a measure becomes a target, it
   ceases to be a good measure." A say–do score surfaced as a ranked target gets
   gamed — managers write vaguer, less falsifiable letters — so the card ships as
   sourced conversation material, never as a mechanical rule or a leaderboard.
3. **Dietvorst, Simmons & Massey (2018), "Overcoming Algorithm Aversion,"
   *Management Science*.** People shelve algorithmic *verdicts* but use algorithmic
   *advice* they can adjust. This governs M5's "input to judgment, not a verdict"
   posture: the card hands over receipts and a rule, and leaves the call to the
   allocator.
4. **Manning, Raghavan & Schütze, *Introduction to Information Retrieval*
   (precision / recall / F1).** The standard basis for the per-slot extraction eval
   in §6.2 — scoring each schema slot with precision and recall (and F1 where one
   number per slot is wanted) rather than one aggregate accuracy that would average
   over slots of different difficulty and hide a failing one.

### 7.2 Questions you should be able to answer after reading this page

- **Why is scoring deterministic and not the LLM's job?** Because the label must
  be reproducible and defensible to a manager. Extraction (reading prose into
  slots) is a task the LLM does well; scoring is a judgment we pin to a visible
  rule and a visible number so it never moves between runs and can be argued with
  on its merits.
- **What exactly separates aligned, partial, and contradicted?** The signed move
  in the stated direction, **σ · m**, against the dead-band δ: ≥ δ is aligned, ≤ −δ
  is contradicted, in between (or right-signed but late) is partial. For a
  neutral-explicit view, aligned means the exposure never left ±δ of its start.
- **Why is there no probability on the label, and why is that better?** Because we
  have no calibrated model to justify a percentage, and a spurious "78%" would read
  as harder than a rule the reader can inspect. A one-word verdict backed by a
  visible threshold is the more honest object.
- **How do we know δ is not arbitrary?** It is calibrated offline from the
  simulator's honest-wander distribution so an honest manager's ordinary noise trips
  a false "contradicted" at most ~1-in-20 times. In the demo it is a placeholder,
  labeled "illustrative, uncalibrated."
- **What has to be true before a real letter renders?** The eval harness must pass:
  extraction precision ≥ 0.8 and recall ≥ 0.8 per core slot, alignment accuracy
  ≥ 0.8 on the synthetic corpus. Miss it after two iterations and the card stays
  demo-only, in writing.
- **How would you design the extraction eval?** Plant known views and truth labels
  at generation time (no human annotation), score precision/recall per schema slot,
  and read alignment accuracy off a 3×3 confusion matrix so a directional bias is
  visible — none of which a single aggregate accuracy would show.
