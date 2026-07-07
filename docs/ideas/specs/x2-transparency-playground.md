# X2 · Transparency Playground — Method Spec

**Date:** 2026-07-06
**Status:** Reviewed (2026-07-06) — implementation-ready
**Card:** [`docs/ideas/2026-07-05-idea-cards.md`](../2026-07-05-idea-cards.md) § X2
**Demo:** gallery page `x2.html` (dark default) — the interactive face of the X1 atlas ([`x1-tier-power-atlas.md`](x1-tier-power-atlas.md)).

---

## 1. What this is

This page is a set of dials and a few live-updating readouts. You drag a dial —
the length of a manager's track record, say, or which transparency tier you are
standing in — and a set of statistics on screen redraw themselves: an estimated
alpha with a band around it, a one-word verdict (*robust*, *shrink*, or *noise*),
and a gate that is either open or shut. Nothing is computed while you drag. Every
number you can land on was calculated in advance and shipped inside the page as a
frozen table; the dials only *choose which precomputed answer to show*. It is a
teaching instrument, not an analytic — its output is understanding, not an
estimate you would trade on.

The audience is a decision-maker, not a statistician: a leader deciding whether
the team's habit of *reporting a range instead of a single number* is worth the
apparent loss of confidence, or an outside reader judging whether the program
knows what it is doing. The decision moment is a conversation — the page is meant
to be projected and dragged live while a room watches a confident-looking claim
dissolve into an honest grey band the moment the track record gets short enough.
It exists to answer one question physically: *why does this team report intervals
at all?* Read as a table of power curves, that argument convinces statisticians
and moves no one. Made draggable, it lands in a single gesture.

## 2. Why we use it

The campaign thesis is a claim about honesty under uncertainty: **what each
transparency tier can honestly claim, and at what sample size.** That thesis is
built from power curves and credible bands — exactly the material that a
spreadsheet renders inert. A stakeholder shown a table of detection probabilities
nods and forgets it. The naïve alternative — a slide that asserts "short track
records are unreliable" — fails for a deeper reason: it *tells* rather than
*shows*, so the listener never feels the arithmetic that makes it true, and a
told fact is a fact one argues with. The claim that a two-year record cannot
separate a skilled manager from a lucky one sounds like caution, even like
excuse-making, until you watch the band do it.

This page wins by making the thesis **physically manipulable**. Drag one dial and
watch an interval widen, a verdict flip from *robust* to *noise*, a power gate
slam shut with the exact threshold it failed printed on its face. The reader is no
longer being asked to trust an assertion; they are watching a measured surface
respond. It improves **engage** at the meta level — internally it teaches
leadership *why the team reports intervals at all*, and externally it is the single
best portfolio artifact the program ships, because it demonstrates statistical
honesty rather than claiming it. And it wins cheaply: because it computes nothing,
it can never disagree with the study it visualizes. Every number traces to a cell
of the X1 atlas; the page invents no precision the Monte-Carlo grid does not have.

## 3. How it works

### The mental model, in prose

Picture a large filing cabinet. Each drawer is labelled with a full setting of the
five dials — a particular skill level, a particular alpha decay speed, a particular
sizing discipline, a particular track length, a particular transparency tier.
Inside each drawer is a small card holding the answers for that exact
configuration: the estimated alpha and its band, the verdict, the gate. The X1
atlas study filled every drawer in advance by simulating hundreds of managers under
each setting and measuring what an honest analyst would have concluded. This page
is the front of that cabinet. When you move a dial you are not *computing* a new
card — you are sliding open a different drawer that was filled long ago.

This is why the dials **snap** to fixed positions instead of gliding smoothly. The
cabinet only has drawers at the settings the study actually simulated. A smooth
slider would let you stop *between* two drawers, and the page would have to invent a
card for a setting nobody measured — it would draw a curve through points the
simulator never evaluated. That invented card would look exactly as authoritative
as a real one, which is precisely the dishonesty the page exists to refuse. The
surface here is **measured, not modelled**: we do not have a formula that predicts
the answer at an arbitrary setting, we have a grid of simulated answers. Snapping
is not a UI limitation; it is the whole ethical point. Show the ladder of computed
rungs and nothing between them.

### A worked toy example

Take the setting the page opens on: skill level IC = 0.04, alpha half-life 12
months, sizing discipline 0.8, track length T = 48 months, tier R (returns-only).
The card in that drawer reads, for annualized alpha, a point estimate of **0.053**
(5.3% a year) with a 95% band running from **−0.0295 to +0.1249** — from minus 3%
to plus 12.5%. Because that band straddles zero, an honest analyst cannot rule out
"no skill at all," so the verdict chip reads **noise**. The manager may well be
good; forty-eight months of returns simply cannot prove it.

Now drag track length T to 120 months and switch the tier dial to E (exposures
pinned). A different drawer opens. Its alpha card reads **0.0482** with a band of
**+0.0018 to +0.0921** — the lower edge has just cleared zero. The verdict flips to
**shrink**: there is now enough evidence to say the alpha is probably positive,
though smaller than the headline. Two dials moved, and a claim that was
indistinguishable from luck became defensible. That single flip *is* the thesis.
Nothing was recomputed in your browser — you opened two drawers the study had
already filled.

### The math behind the dials

The page runs no statistics itself; the estimators live in the X1 spec (its §3.2–§3.4)
and the S1 closed-form shrinkage. What follows is the *why* behind each dial — the
laws the offline grid encodes, so a reader understands what they are watching.

**Detectability rises with skill — the fundamental law of active management
(Grinold & Kahn).**

```
IR ≈ IC · √BR
```

where:

- **IR** = the *information ratio* — a manager's annualized active return divided by
  their annualized active risk. Higher IR means skill that stands out more against
  its own noise, so it is easier to detect in a finite sample.
- **IC** = the *information coefficient* — the cross-sectional correlation between
  the manager's forecasts and the returns that actually followed. This is the *skill*
  dial. Values run 0 to 0.10 on the page.
- **BR** = *breadth* — the number of genuinely independent bets the manager makes per
  year.

In words: skill you can detect is skill (IC) amplified by how many independent
chances you get to display it (√BR). Raising the IC dial raises IR and so raises the
probability that a finite track record separates this manager from a coin-flipper.
Grinold & Kahn showed that active performance decomposes into exactly these two
pieces — *how good your forecasts are* and *how often you act on them independently* —
which is why those are the axes the atlas sweeps and the axes worth dialling.

**Interval width shrinks as √T — Sharpe-ratio statistics (Lo, 2002).**

For a track record of **T** monthly observations, assuming returns are independent
and identically distributed, the standard error of an *estimated* Sharpe ratio **SR**
is approximately

```
SE(SR) ≈ √( (1 + SR² / 2) / T )
```

and the 95% band half-width is `≈ 1.96 · SE(SR)`, where:

- **SR** = the estimated Sharpe ratio (mean return over standard deviation, per period);
- **T** = the number of observations (the *track length* dial, in months);
- the **1.96** is the standard-normal 95% multiplier; the `SR²/2` term is the
  correction for the ratio being estimated rather than known.

In words: the band around a performance estimate narrows in proportion to `1/√T`,
**not** `1/T`. That square root is the most visceral thing on the page. It means a
manager with a short record sits in the honest-grey zone *by arithmetic*, not by
suspicion — halving your uncertainty demands four times the history, so a 24-month
manager is genuinely, structurally harder to certify than a 120-month one. Lo (2002)
derived the sampling distribution of the Sharpe ratio and showed exactly this scaling
(and how it worsens when returns are autocorrelated); the T dial is that result made
draggable.

**The verdict carries its own uncertainty — the Wilson half-width.**

Each cell's verdict rests on a *measured power*: the fraction of simulated managers in
that drawer whose statistic cleared the detection bar. That fraction is itself an
estimate from a finite number of simulations, so it has an error bar. We report the
**Wilson score interval** half-width:

```
half_width ≈ ( z / (1 + z²/n) ) · √( p̂(1 − p̂)/n + z² / (4n²) )
```

where:

- **p̂** = the measured power (a proportion between 0 and 1);
- **n** = the number of simulated managers in the cell (≥ 500 for the v1 grid);
- **z** = 1.96, the 95% standard-normal multiplier.

In words: this is how much the verdict itself would wobble if we re-ran the
simulation. We show it rather than hide it — the band is an estimate, and so is our
confidence in the band. *(Erratum 2026-07-07, numerics gate: an earlier draft
attached this half-width to "the band itself." The computed quantity is the power
proportion's half-width — the verdict's own Monte-Carlo uncertainty — and the page
copy now says so.)*

### What each dial does, in one line each

- **IC (skill)** → detectability, via `IR ≈ IC·√BR`: more skill is easier to prove.
- **Alpha half-life** → why *measured* alpha decays. A short half-life means the
  manager's edge fades fast, so a long sample "sees" mostly dead alpha and the
  estimate shrinks — even when the early skill was real.
- **Sizing discipline** → whether trade-level analytics (tier P) have any signal to
  detect; disciplined sizing (0.8) makes the sizing-curve slope estimable.
- **T (track length)** → interval width, shrinking as `√T` per Lo (2002).
- **Tier** → *what pinning betas buys*. See below; this is the star control.

### Tier semantics (v1) — the same ground truth at three honesty levels

The tier selector is the centre of the page: one true manager, viewed at three
levels of disclosure.

- **R** = returns-only estimates. Betas (the manager's exposures to common factors)
  are *estimated* from the return stream, which adds estimation noise to the alpha.
- **E** = betas *pinned* to the true emitted exposures (the S1 §3.3 mechanism). With
  the exposures known rather than fitted, the alpha band visibly narrows. This page
  *is* the argument for rung 2 of the transparency ladder — the width shrinking when
  you move R→E is, literally, the case for asking managers to disclose exposures.
  Removing beta-estimation error is the Pástor–Stambaugh logic in capital-of-certainty
  terms.
- **P** = adds trade-level analytics — hit rate and sizing-curve slope — behind
  **power gates** that open only when the cell's trade count clears the atlas
  threshold. A closed gate means the record does not contain enough independent trades
  to say anything about the batting average, and the gate names the threshold it
  failed.

## 4. How to implement

Below is a self-contained, from-scratch sketch of the page's data logic — paste-able
into a fresh file and adaptable. It exists to make one principle concrete: **the page
does no statistics.** Its only jobs are to *snap* a requested dial value to a computed
rung and to *look up* the frozen card. The only real formula it carries is the Wilson
half-width, shown here so the footnote number in §3 is reproducible; the two "laws"
are included purely as intuition helpers with a loud note that the page never calls
them.

```python
"""Transparency-playground data logic, written from scratch as teaching code.

The guiding rule: NO CLIENT MATH. The page never computes a statistic for a
manager. It snaps the dials to a measured grid point and reads a precomputed
card. The Wilson half-width below is the ONE statistic shown, and it was
computed offline by the grid generator, not in the browser — it is reproduced
here only so a reader can verify the number.
"""

from bisect import bisect_left

# The measured grid — the only settings the study actually simulated.
GRID = {
    "ic":        [0.0, 0.02, 0.04, 0.07, 0.10],
    "half_life": [3, 12, 36],            # months
    "sizing":    [0.0, 0.8],
    "T":         [24, 36, 48, 60, 120],  # months
    "tier":      ["R", "E", "P"],
}


def snap_to_grid(dial: str, requested: float) -> float:
    """Return the nearest computed rung for a numeric dial.

    A smooth slider would let the user stop between rungs; interpolating a card
    for an unmeasured setting would invent precision the Monte-Carlo grid does
    not have. So we snap to the closest simulated value and show only that.
    """
    rungs = GRID[dial]
    pos = bisect_left(rungs, requested)
    if pos == 0:
        return rungs[0]
    if pos == len(rungs):
        return rungs[-1]
    below, above = rungs[pos - 1], rungs[pos]
    # Tie or nearer-below goes to `below`; otherwise `above`.
    return below if (requested - below) <= (above - requested) else above


def cell_key(ic: float, half_life: int, sizing: float, T: int, tier: str) -> str:
    """Build the flat key that addresses one drawer of the cabinet.

    Format matches the committed JSON: "ic|half_life|sizing|T|tier", each value
    formatted the way it was written at build time (%g drops trailing zeros).
    """
    return "|".join(("%g" % ic, "%g" % half_life, "%g" % sizing,
                     "%g" % T, tier))


def lookup_cell(cells: dict, ic, half_life, sizing, T, tier) -> dict:
    """Snap every dial, then read the precomputed card. No arithmetic on the
    manager's numbers happens here — this is the whole point."""
    key = cell_key(
        snap_to_grid("ic", ic),
        snap_to_grid("half_life", half_life),
        snap_to_grid("sizing", sizing),
        snap_to_grid("T", T),
        tier,  # categorical: chosen directly, nothing to snap
    )
    return cells[key]  # e.g. {"alpha": [point, lo, hi, verdict, gate, thr, unit, wilson], ...}


def wilson_half_width(p_hat: float, n: int, z: float = 1.96) -> float:
    """95% Wilson-score half-width for a proportion — the verdict's own
    Monte-Carlo uncertainty. Computed OFFLINE by the generator; reproduced here
    only to make the footnote checkable."""
    denom = 1.0 + z * z / n
    centre_spread = p_hat * (1.0 - p_hat) / n + z * z / (4.0 * n * n)
    return (z / denom) * (centre_spread ** 0.5)


# --- Intuition helpers: the laws the OFFLINE grid encodes. --------------------
# The page never calls these. They are here so a reader can feel why the dials
# move the readouts the way they do (see §3).

def information_ratio(ic: float, breadth: float) -> float:
    """Fundamental law of active management (Grinold & Kahn): IR ≈ IC·√BR."""
    return ic * breadth ** 0.5


def sharpe_band_half_width(sr: float, T: int, z: float = 1.96) -> float:
    """95% half-width of an estimated Sharpe ratio for iid returns (Lo, 2002).
    Note the 1/√T shrinkage — halving the band needs 4x the history."""
    standard_error = ((1.0 + sr * sr / 2.0) / T) ** 0.5
    return z * standard_error


if __name__ == "__main__":
    # The page's actual default drawer, addressed by snapping.
    demo_cells = {
        "0.04|12|0.8|48|R": {
            "alpha": [0.053, -0.0295, 0.1249, "noise", "closed",
                      None, "months", 0.03796],
        }
    }
    card = lookup_cell(demo_cells, ic=0.041, half_life=11, sizing=0.8,
                       T=47, tier="R")           # sloppy inputs snap to the grid
    point, lo, hi, verdict, *_ = card["alpha"]
    print(f"alpha {point:.3f}  band [{lo:.4f}, {hi:.4f}]  verdict={verdict}")
    # -> alpha 0.053  band [-0.0295, 0.1249]  verdict=noise
```

The real page is static HTML plus vanilla JavaScript that does exactly this: read
the inlined JSON, snap the dials, look up the tuple, repaint. No server, no
framework, no in-browser math.

## 5. Reading the demo

The page opens dark-themed on the default drawer (IC = 0.04, half-life 12, sizing 0.8,
T = 48, tier R). Here is how each visual element maps to the method:

- **The dials** are rows of buttons, not sliders — because the grid is measured, they
  **snap**. The five dials are the tuple `[ic, half_life, sizing, T, tier]` that
  addresses a cell.
- **The IntervalStat** (one per analytic) is the drawer's card made visible: a point
  marker on a rail with a shaded **band** = the 95% credible interval `[lo, hi]`. When
  you drag T, watch the band *animate* wider or narrower — that motion is the `√T` law.
- **The VerdictChip** is the one-word conclusion. It reads **noise** when the band
  straddles zero (skill indistinguishable from luck), **shrink** when there is evidence
  of a smaller-than-headline effect, **robust** when the effect is clearly supported.
- **The PowerGate** is open or shut. A shut gate on a P-tier analytic means the record
  lacks enough independent trades to estimate it, and the gate prints the threshold it
  failed; when no threshold is reached in the measured range, it says so plainly.
- **The Wilson footnote** under each analytic states the ±half-width on that cell's
  measured power — the verdict's own error bar. It is shown, never hidden.
- **The false-alarm banner** appears when you set IC = 0: at zero skill there is nothing
  to detect, so any "detection" is a *false-alarm rate*, not power. The banner says so.

What an allocator should conclude from the actual numbers: at the default setting the
alpha reads a healthy-looking 5.3% a year, but its band (−3.0% to +12.5%) covers zero,
so the honest verdict is **noise** — forty-eight months of returns cannot certify this
manager. Stretch T to 120 and pin exposures (tier E) and the alpha band tightens to
+0.2% to +9.2% and the verdict becomes **shrink**. The lesson is not that the manager
changed; it is that *evidence*, not talent, is what a short record is missing — and that
disclosing exposures (R→E) buys real certainty for free.

## 6. Honest limits & go-live

### Data contract

There is **no live-data tier and no external data.** The only input is one committed
JSON file; the only output is DOM. Because the page never runs against a real manager,
the usual "fields the live version needs" contract is replaced by the **grid contract
with X1**: the playground is a strict subset of the atlas registry, never a parallel
computation.

**Consumed:** `site/data/x2_playground.json`, delivered as an inlined
`<script type="application/json">` block (robust under `file://` and when printed). A
cell is addressed by its dial tuple `[ic, half_life, sizing, T, tier]`. **Per-cell
payload** — for each analytic (annualized alpha and Sharpe at all tiers; hit rate and
sizing-curve slope additionally at tier P):

- an **IntervalStat**: median point + 95% band across simulated managers, `[point, lo, hi]`;
- a **VerdictChip** state: `robust | shrink | noise`;
- a **PowerGate** state: `open | closed`, plus gate quantity, threshold, and units
  (e.g. `["closed", 780, "independent_trades"]`);
- an **MC-uncertainty footnote**: the Wilson 95% half-width on the cell's *measured
  power* — the verdict's own uncertainty — carried as a number and shown, not hidden.

Data budget is held at the schema level: keys are **short arrays, not verbose objects**,
and every value is rounded to **4 significant figures**. The byte layout is pinned by the
demo-data generator task in Plan B; this spec fixes only the budget and the rounding rule.

### Grid dials and starter grid (provisional constants)

Dials snap to exactly: IC ∈ {0, 0.02, 0.04, 0.07, 0.10}; alpha half-life (months) ∈
{3, 12, 36}; sizing discipline ∈ {0.0, 0.8}; T (months) ∈ {24, 36, 48, 60, 120}; tier
∈ {R, E, P}. That is **450 cells**, with **≥ 500 simulated managers per cell** for the
v1 starter grid. A dial change swaps the displayed cell; it never blends two.

### Validation — the grid must not misrepresent the atlas

The playground computes no statistics, so "validation" means the starter grid faithfully
reflects the study. Two families of check.

**(a) Grid sanity invariants — shared with the atlas (X1 §4).** Power and band width are
**monotone in T and in IC up to Monte-Carlo noise** (a violation blocks the JSON build);
**size ≈ 5% at IC = 0** — the IC = 0 column measures the false-alarm rate, and a cell that
"detects" skill where there is none is a bug; every IntervalStat band contains its own
point estimate; gates are `closed` exactly when the cell's gate quantity is below threshold.

**(b) v1 → v2 upgrade check — the honesty gate.** v2 regenerates the grid **wholesale from
atlas vol. 1** (≥ 1,000 reps) — it **replaces** the starter grid, it does not merge with it.
The upgrade script counts **verdict flips** between the v1 grid and atlas vol. 1, cell by
cell. If any cell's verdict flips (robust↔shrink↔noise), the v1 page was showing a claim the
real study does not support — it was misleading. The v2 regeneration note states this plainly,
names every flipped cell, and the page is not re-publicized until the count is reported. **A
silent swap is forbidden.**

### Kill / honesty rules (non-negotiable)

1. Dials **snap** to computed cells, never gliding between them.
2. Every number **traces to a committed JSON cell** — no interpolation, no client math.
3. The **SYNTHETIC badge is always on**.
4. The **go-live box is replaced** by the statement that this page never goes live against
   a real manager — it is the thesis, not a product.
5. **Monte-Carlo uncertainty of the verdict is shown**, not hidden — the Wilson footnote
   states that the power (and so the band it certifies) is itself an estimate.

### Go-live — there is none

Unlike every other card, the honest answer here is that the playground is a communication
device and stays **synthetic forever**; it never consumes a real manager's data, so the
go-live box is replaced by a standing statement. The only "release" event is the **v1 → v2
upgrade**: when atlas vol. 1 lands, the starter grid is regenerated wholesale (§(b) above),
the verdict-flip count reported, and — only if the honesty gate is clean or its flips are
disclosed — the page re-publicized. Compute budget: the same single-machine envelope as the
atlas (under an hour), since the grid is a subset of X1's.

### Implementation & adoption notes

- **Grid generator:** `src/quant_allocator/demo_data/x2_playground.py` imports the simulator
  and the **S1 closed-form shrinkage** (posterior-alpha variant) — it reimplements neither.
  It runs the 450 cells × ≥ 500 managers, applies the §(a) invariants as build-time
  assertions, rounds to 4 s.f., and writes `site/data/x2_playground.json` with sorted keys
  and fixed precision so the diff is reviewable (the numerics gate).
- **Page:** static HTML + vanilla JS. On any dial change it looks up the cell tuple and
  repaints IntervalStats (animated width), VerdictChips (flip), and PowerGates (dashed
  empty-state naming the threshold). No server, no framework, no in-browser math.
- **Theme:** **dark by default** per the demo-layer spec (Terminal-derived tokens); the
  site-wide toggle still works.
- **Data budget:** committed JSON stays **≤ ~300 KB**, enforced by the rounding rule and
  short-array keys above; a build that exceeds it fails.
- **Numbers computed locally, committed as JSON, CI renders only** — the generator runs on
  the developer machine; continuous integration never computes statistics nor touches the
  network. **Effort:** S–M (~3 sessions for v1); v2 is a regeneration, not a rebuild.
- **How to run it in a live conversation.** This page is deliberately **kill-the-dashboard**
  (Sweep E): it is used *in* a conversation — projected, dragged live while the room watches
  a claim dissolve — not left as a standing browser tab that decays to 25% adoption. The
  interaction *is* the teaching moment; a static screenshot cannot make the point. The move
  that carries the whole thesis in one gesture: *"Drag T from 120 down to 36 and watch every
  claim you thought you could make dissolve into honest grey."* Publicly, the same gesture is
  the single best portfolio artifact the program ships.

## 7. Deeper reading

**Canonical references, with what each contributes:**

- **Grinold & Kahn — the fundamental law of active management (`IR ≈ IC·√BR`).** They showed
  that a manager's information ratio decomposes into skill (the information coefficient) and
  breadth (independent bets per year), scaled as `IC·√BR`. That decomposition is why the atlas
  sweeps IC and breadth as its axes, and why raising the IC dial raises detectability on this
  page.
- **Lo (2002, *Financial Analysts Journal*) — the statistics of the Sharpe ratio.** Lo derived
  the sampling distribution of an *estimated* Sharpe ratio and showed its standard error scales
  as `1/√T` (worsening under autocorrelation). That result is the T dial: it is why an interval
  narrows with the square root of tenure, not linearly, so short-record managers sit in the
  honest-grey zone by arithmetic.
- **The X1 atlas spec (`x1-tier-power-atlas.md`) — the source of truth for every cell rendered.**
  The playground defends none of the numbers itself; it defers entirely to the atlas, rendering a
  precomputed subset of that study's grid.

*(Presenting uncertainty to non-statisticians: show the interval **moving**. Never say
"heteroskedasticity" or "noncentral t" — let the band widen and the verdict flip do the talking.
A closed PowerGate naming its threshold is more honest, and more memorable, than any p-value.)*

**Questions you should be able to answer after reading this page:**

- **Why do the dials snap rather than glide?** Because the power surface is measured, not
  modelled — the study only simulated a grid of settings, and interpolating between them would
  invent precision the Monte-Carlo grid does not have. Snapping shows the ladder of computed rungs
  and nothing between them.
- **Why does the page have no go-live path?** Because it is a communication device, not an
  analytic — it never consumes a real manager's data and stays synthetic forever; the only release
  event is the v1 → v2 atlas regeneration.
- **Without jargon, why is the same manager's alpha band wide at T = 36 and tight at T = 120?**
  Because uncertainty shrinks with the square root of how much history you have: more months mean a
  steadier estimate, and quadrupling the history only halves the band. A short record is not
  suspicious — it is simply thin evidence, and the band widens to say so honestly.
