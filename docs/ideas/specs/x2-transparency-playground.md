# X2 · Transparency Playground — Method Spec

**Date:** 2026-07-06
**Status:** Reviewed (the lead reviewer, 2026-07-06) — implementation-ready
**Card:** [`docs/ideas/2026-07-05-idea-cards.md`](../2026-07-05-idea-cards.md) § X2
**Demo:** gallery page `x2.html` (dark default) — the interactive face of the X1 atlas ([`x1-tier-power-atlas.md`](x1-tier-power-atlas.md)).

## 1. Problem & decision hook

The campaign thesis — *what each transparency tier can honestly claim, at what
sample size* — is an argument made of power curves and credible bands. Read as a
table it convinces statisticians; it does not move a stakeholder. This page makes
the thesis **physically manipulable**: drag a dial and watch an IntervalStat
widen, a VerdictChip flip to noise, a PowerGate slam shut with the threshold it
failed named on its face. It is a **communication device, not an analytic**: it
computes nothing in the browser, rendering a precomputed subset of the exact cells
the X1 atlas produces (its §3.1 grid, its §3.2 metrics), shipped as committed JSON
— the interactive face of that study. Its job is education, not estimation. It
improves **engage** at the meta level: internally, teaching leadership *why the
team reports intervals at all*; externally, it is the single best portfolio
artifact the program ships. Every number traces to an atlas cell; the page invents
no precision the Monte Carlo grid does not have.

## 2. Data contract

No live-data tier and no external data. The only input is one committed JSON file;
the only output is DOM. Because the page never runs against a real manager, the
usual "fields the live version needs" contract is replaced by the **grid contract
with X1** — the playground is a strict subset of the atlas registry, never a
parallel computation.

**Consumed:** `site/data/x2_playground.json`, an inlined
`<script type="application/json">` block (robust under `file://` and print). A
cell is addressed by its dial tuple `[ic, half_life, sizing, T, tier]`. **Per-cell
payload** — for each analytic (annualized alpha and Sharpe at all tiers; hit rate
and sizing-curve slope additionally at P):

- an **IntervalStat**: median point + 95% band across simulated managers
  `[point, lo, hi]`;
- a **VerdictChip** state: `robust | shrink | noise`;
- a **PowerGate** state: `open | closed` plus gate quantity, threshold, and units
  (e.g. `["closed", 780, "independent_trades"]`);
- an **MC-uncertainty footnote**: the Wilson 95% half-width on the cell's
  measured power — the verdict's own uncertainty — carried as a number and
  shown, not hidden. *(Erratum 2026-07-07, copy gate: an earlier draft
  attached this to "the band itself"; the computed quantity is the power
  proportion's half-width, and the page copy says so.)*

Data budget (§5) is held at the schema level: keys are **short arrays, not verbose
objects**, and every value is rounded to **4 significant figures**. The byte layout
is pinned by the demo-data generator task in Plan B; this spec fixes only the
budget and the rounding rule.

## 3. Methodology

Light math only — the estimators live in the X1 spec (§3.2–§3.4) and the S1
closed-form shrinkage. The playground's method is the *presentation contract*.

**Dials (snap-to-grid only, no interpolation).** Interpolating between computed
cells would invent precision the MC grid does not have, so dials snap to exactly:
IC ∈ {0, 0.02, 0.04, 0.07, 0.10}; alpha half-life (months) ∈ {3, 12, 36}; sizing
discipline ∈ {0.0, 0.8}; T (months) ∈ {24, 36, 48, 60, 120}; tier ∈ {R, E, P}.
That is **450 cells**, with **≥500 simulated managers per cell** for the v1
starter grid. A dial change swaps the displayed cell; it never blends two.

**Tier semantics (v1) — the tier selector is the star control, same ground
truth at three honesty levels:**

- **R** = returns-only estimates; betas are *estimated* from the return stream.
- **E** = betas *pinned* to the true emitted exposures (the S1 §3.3 mechanism),
  visibly narrowing the alpha band. This page is the argument for rung 2 of the
  transparency ladder — the width shrinking *is* the case for the E ask.
- **P** = adds trade-level analytics (hit rate, sizing-curve slope) behind
  PowerGates that open only when the cell's trade count clears the atlas threshold.

The smooth laws behind the dials (IR ≈ IC·√BR, the √T narrowing of intervals)
tempt a continuous slider — but the power surface is measured, not modelled, so a
glide would draw a curve through points the simulator never evaluated; the honest
UI shows the ladder of computed rungs and nothing between them.

## 4. Power & validation plan

The playground computes no statistics, so "validation" means **the starter grid
does not misrepresent the atlas.** Two families of check.

**(a) Grid sanity invariants — shared with the atlas (X1 §4):** power and band
width are **monotone in T and in IC up to MC noise** (a violation blocks the JSON
build); **size ≈ 5% at IC = 0** (the IC = 0 column measures false-alarm rate — a
cell that "detects" skill where there is none is a bug); every IntervalStat band
contains its own point estimate; gates are `closed` exactly when the cell's gate
quantity is below threshold.

**(b) v1 → v2 upgrade check — the honesty gate.** v2 regenerates the grid
**wholesale from atlas vol. 1** (≥1,000 reps) — it **replaces the starter grid,
it does not merge with it.** The upgrade script counts **verdict flips** between
the v1 grid and atlas vol. 1, cell by cell. If any cell's verdict flips
(robust↔shrink↔noise), the v1 page was showing a claim the real study does not
support — it was misleading. The v2 regeneration note states this plainly, names
every flipped cell, and the page is not re-publicized until the count is
reported. A silent swap is forbidden.

## 5. Implementation architecture

- **Grid generator:** `src/quant_allocator/demo_data/x2_playground.py` imports
  the simulator and the **S1 closed-form shrinkage** (posterior alpha variant) —
  it reimplements neither. It runs the 450 cells × ≥500 managers, applies §4(a)
  invariants as build-time assertions, rounds to 4 s.f., and writes
  `site/data/x2_playground.json` with sorted keys and fixed precision so the diff
  is reviewable (the numerics gate).
- **Page:** static HTML + vanilla JS. `interval.js` reads the inlined JSON and,
  on any dial change, looks up the cell tuple and repaints IntervalStats (animated
  width), VerdictChips (flip), and PowerGates (dashed empty-state naming the
  threshold). No server, no framework, no in-browser math.
- **Theme:** **dark by default** per the demo-layer spec (Terminal-derived
  tokens); the site-wide toggle still works.
- **Data budget:** committed JSON stays **≤ ~300 KB**, enforced by the rounding
  rule and short-array keys above; a build that exceeds it fails.
- **Numbers computed locally, committed as JSON, CI renders only** — the generator
  runs on the developer machine; GitHub Actions never computes statistics nor
  touches the network. **Effort:** S–M (~3 sessions for v1); v2 is a regeneration,
  not a rebuild.

## 6. Adoption & packaging

**Primary internal use — educating stakeholders on why the team reports
intervals.** Deliberately **kill-the-dashboard** (Sweep E): the playground is used
*in* a conversation — projected, dragged live while the room watches a claim
dissolve — not left as a standing browser tab that decays to 25% adoption. The
interaction *is* the teaching moment; a static screenshot cannot make the point.

**Public use — the single best portfolio artifact.** "Drag T from 120 down to 36
and watch every claim you thought you could make dissolve into honest grey" is the
whole thesis in one gesture.

**UX honesty rules (non-negotiable):** (1) dials **snap** to computed cells, never
gliding between them; (2) every number **traces to a committed JSON cell** — no
interpolation, no client math; (3) the **SYNTHETIC badge is always on**; (4) the
**go-live box is replaced** by the statement that *this page never goes live
against a real manager — it is the thesis, not a product*; (5) **MC uncertainty of
the band is shown**, not hidden — the Wilson footnote states the band is itself an
estimate.

## 7. Go-live requirements

**There is no go-live.** Unlike every other card, the honest answer here is that
the playground is a communication device and stays synthetic forever; it never
consumes a real manager's data, so the go-live box is replaced by the standing
statement above. The only "release" event is the **v1 → v2 upgrade**: when atlas
vol. 1 lands, the starter grid is regenerated wholesale (§4b), the verdict-flip
count reported, and — only if the honesty gate is clean or its flips are disclosed
— the page re-publicized. Compute budget: the same single-machine envelope as the
atlas (under an hour), since the grid is a subset of X1's.

## 8. Learning notes

**What each dial teaches (derivations to own):**

- **IC → power** via the fundamental law, IR ≈ IC·√BR (Grinold–Kahn): raising IC
  raises the information ratio and so the detectability of skill.
- **half-life → why measured alpha decays**: a short half-life means a long sample
  "sees" mostly dead alpha, so the estimate shrinks even when early skill was real.
- **T → interval width shrinking as √T** (Lo 2002): the most visceral thing to
  drag — width is not linear in tenure, so short-track-record managers sit in the
  honest-grey zone by arithmetic, not by suspicion.
- **tier → what pinning betas buys**: R→E narrows the alpha band by removing
  beta-estimation error (Pástor–Stambaugh logic); P opens trade-level gates. The
  narrowing is the transparency-ladder argument in capital-of-certainty terms.

**Presenting uncertainty to non-statisticians:** show the interval *moving*. Never
say "heteroskedasticity" or "noncentral t" — let the band widen and the verdict
flip do the talking. A closed PowerGate naming its threshold is more honest and
more memorable than any p-value.

**Canonical references:** (1) **Grinold & Kahn** — the fundamental law
(IR ≈ IC·√BR), the IC/breadth axes' rationale; (2) **Lo (2002, FAJ)** — Sharpe-
ratio statistics and interval width scaling with √T, behind the T dial;
(3) **the X1 atlas spec** (`x1-tier-power-atlas.md`) — source of truth for every
cell rendered; the playground defends none of the numbers itself, it defers.

**Defend unaided:** why the dials snap rather than glide (the grid is measured,
not modelled — interpolation would invent precision); why the page has no go-live
path; and, without jargon, why the same manager's alpha band is wide at T=36 and
tight at T=120.
