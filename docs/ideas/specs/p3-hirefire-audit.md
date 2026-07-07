# P3 · Hire/Fire Decision Audit & Journal — Method Spec

**Status: Reviewed (2026-07-07) — implementation-ready**
**Date:** 2026-07-07
**Card:** [`docs/ideas/2026-07-05-idea-cards.md`](../2026-07-05-idea-cards.md) § P3
**Demo:** gallery page `p3.html` (counterfactual cohort panel + one journal
scorecard; fully synthetic decision history — see §5)

---

## 1. What this is

P3 is a **decision audit**: it treats each hire, fire, or considered-but-kept
manager as an *event* and asks a single question — did the allocator's timing
add value, measured against the alternative it passed over? It produces two
things. A **prospective decision journal**: a short record filled in at the
moment of every decision — the thesis, the alpha the decision is underwritten
on, the horizon, and the kill criterion that would reverse it — all committed
*before* the outcome is known. And a **retrospective counterfactual ledger**:
for each past event, what the acted-on manager did next versus what the
passed-over alternative did next, compounded forward and reported as a signed
gap where positive always means "the decision helped."

The audience is department leadership (governance) and the team's own future
self, and the decision moment is the investment-committee packet just before a
termination or funding vote. The subject under audit is **the allocator's
decision, not the manager's skill** — P3 never ranks managers, never claims
performance persists, and never issues a verdict on a single termination. Its
honest posture is that a real allocator makes only a handful of these decisions
a year, so for years the data supports **description and prior-updating, not
statistical significance**. Saying that plainly, on the page, is the product.

## 2. Why we use it

The motivating fact comes from Goyal & Wahal (2008): plan sponsors hire
managers after strong trailing three-year performance and fire after weak
trailing performance, yet the **fired managers subsequently match or beat the
newly hired ones**. The round-trip adds no value — the *timing* is the mistake.
Almost no allocator backtests its own hire/fire timing; the decision that most
moves the book is the one least measured. P3 exists to close that gap.

Why do the naive alternatives fail?

- **Judging a termination by the manager's later collapse (or recovery).**
  This is outcome bias: scoring a decision by how it *felt* in hindsight rather
  than whether it met the bar set in advance. A good decision can draw a bad
  outcome and a bad decision can get lucky; grading on the outcome rewards luck
  and punishes discipline. The prospective journal is the fix — you cannot
  rewrite a thesis you wrote down before the result.
- **Auditing only the actions you took.** If you review only the managers you
  actually hired and fired, you have survivorship-biased your own decision set:
  the manager you *considered* firing and kept is the control arm you threw
  away. Recording holds-under-review is what makes this a decision audit rather
  than an action audit.
- **Comparing a fired manager to cash, or to nothing.** A decision's value is
  only defined against the alternative it passed over. Firing a manager who
  then returned +10% looks terrible until you see the replacement returned
  +12% — the fire helped. The counterfactual is the whole game.
- **Reaching for a p-value.** With events in the tens, and decisions in one
  market episode sharing a common forward path, a single allocator's audit
  cannot reach significance in a career. Pretending otherwise — computing a
  naive standard error and declaring a "skilled committee" — is the failure the
  card is built to avoid.

What P3 wins: it **calibrates the bar for termination** against the base rate
that firing often destroys value (improving *redeem* decisions), and it
**imposes pre-commitment discipline** — a written thesis and kill criterion —
that defends the next selection against outcome bias (improving *select*
decisions). The customer is department leadership and the team's own future
self.

**What it is not:** not a manager-persistence test (§6 draws that boundary),
not a significance claim on any career-length sample, and — in this public repo
— never run on real decisions. The repo version is synthetic by standing rule;
real adoption is leadership's call.

## 3. How it works

### 3.1 The mental model, in prose

Think of the analytic as two instruments bolted together.

The **journal** is a discipline device. Before you act, you write down why, what
you expect, over what horizon, and what would make you reverse. That written
record is the only clean way to grade the *decision* later, because it fixes the
bar before the draw. This half pays off on day one — no data, no sample, no
forward window required.

The **ledger** is deterministic accounting. Once a decision is old enough to
have a forward window, you compound what the acted-on manager did next and what
the passed-over alternative did next, and you take the difference. There is no
hypothesis test here — it is arithmetic over returns, presented as individual
stories with receipts.

Only one number ever crosses events: the **average** decision value-add, the
estimate of the allocator's process skill. Because the sample is tiny and
correlated, that average is shrunk toward a prior pinned at zero — the
Goyal–Wahal base rate — and reported as an interval that will straddle zero for
years. The refusal to over-claim is the point.

### 3.2 A worked toy example (small concrete numbers)

Suppose you fire manager A and fund manager B in the same quarter. Over the next
three years, A (net of the risk-free rate) compounds to a forward excess return
of **+18%**, and B compounds to **+12%**. The fire's value-add is
`replacement − fired = 12% − 18% = −6%`: keeping A would have been better, so
this fire *hurt* by six points. Note the sign — even though A "did fine," the
decision is judged against the alternative you chose instead.

Now suppose you have twenty such events, but they cluster four to a quarter
across five quarters, and value-adds within a quarter are correlated at
ρ = 0.5 (they share the same market episode). The naive sample size is 20, but
the **design effect** is `1 + (4 − 1)·0.5 = 2.5`, so the *effective* sample is
`20 / 2.5 = 8` independent-equivalent events. If those twenty value-adds average
−3%/yr with a spread (standard deviation) of 8%/yr, the honest standard error is
`8% / √8 = 2.83%/yr`, not `8% / √20 = 1.79%/yr`. With a prior scale of τ = 2%/yr
pinned at zero, the shrinkage weight is
`w = τ² / (τ² + se²) = 4 / (4 + 8) = 0.33`, so the posterior point is
`0.33·(−3%) + 0.67·0 = −1%/yr` — pulled two-thirds of the way back to the base
rate, exactly because eight noisy events cannot overrule the prior. That is the
whole method in miniature.

### 3.3 The journal (prospective, pre-commitment)

Every hire, fire, or considered-hold is recorded **at the time of the
decision**, before the outcome is known, as a `DecisionRecord`:

- **type** ∈ {hire, fire, hold-under-review}
- **manager id**, **decision date**
- **thesis** — free text: why now, what the decision expects to capture
- **expected annualized alpha** — the number the decision is underwritten on
- **horizon** — the stated period over which the thesis should prove out
  (defaulting to `JOURNAL_DEFAULT_HORIZON_YEARS`, provisional **3y**, the
  Goyal–Wahal evaluation window)
- **kill criteria** — the pre-committed condition that would reverse the
  decision (e.g., "cut if trailing 2y factor-adjusted alpha < −2%/yr")
- **counterfactual designation** — the replacement manager id for a paired
  hire↔fire, or `peer-median` / `benchmark` when unpaired (§3.6)

The **hold-under-review** record is load-bearing: auditing only actions (hires
and fires) survivorship-biases your own decision set. The manager you
*considered* firing and kept is the control arm. Recording holds is what makes
the ledger a decision audit rather than an action audit. The journal's value is
prospective and immediate — pre-committing the thesis and the kill criterion is
the only clean defense against outcome bias (§7), and it delivers on day one,
before a single event has a forward window long enough to score.

### 3.4 Event-time forward returns (deterministic)

All accounting is in **event time**: month 0 is the decision date, and every
event is tracked forward over `AUDIT_HORIZONS_YEARS` (provisional **{1, 2, 3}y**).
For manager $i$ decided at date $d$, the forward excess return over horizon $h$
is the cumulative excess over the risk-free series:

$$R^{\text{fwd}}_i(d, h) = \prod_{t=d+1}^{d+12h}\big(1 + r_{i,t} - r_{f,t}\big) - 1.$$

where:
- $R^{\text{fwd}}_i(d, h)$ — cumulative forward excess return of manager $i$,
  measured from decision date $d$ over $h$ years
- $r_{i,t}$ — manager $i$'s **net** monthly return in calendar month $t$ (decimal)
- $r_{f,t}$ — the risk-free monthly return in month $t$ (decimal)
- $d$ — the decision month, i.e. event time 0
- $h$ — the horizon in years; $12h$ is the window length in months
- $\prod_{t=d+1}^{d+12h}$ — the product runs over the first $12h$ months *after*
  the decision

In words: compound the monthly excess-of-risk-free returns across the forward
window, then subtract 1 to turn a growth factor into a return.

A **factor-adjusted** variant replaces the raw excess with the cumulative
regression alpha over the same forward window, using the S2 factor pipeline
(strategy-appropriate factor set, de-smoothed where illiquid). Both are
reported: the raw gap is what leadership feels; the factor-adjusted gap
separates "we picked a better manager" from "the factor the manager was tilted
to happened to pay." A hire that looks brilliant on raw forward return but zero
on factor-adjusted return was a factor bet, not a selection.

### 3.5 Signed decision value-add per event

Sign conventions are unified so that **positive always means the decision
helped**, regardless of type:

- **Hire:** $V_e = R^{\text{fwd}}_{\text{hired}} - R^{\text{fwd}}_{\text{counterfactual}}$
  — the hire beat the alternative.
- **Fire:** $V_e = R^{\text{fwd}}_{\text{replacement}} - R^{\text{fwd}}_{\text{fired}}$
  — the fire helped iff what replaced the manager did better than keeping them.
  This is exactly the Goyal–Wahal round-trip, and its historical sign is
  *negative* on average.
- **Hold-under-review:** $V_e = R^{\text{fwd}}_{\text{held}} - R^{\text{fwd}}_{\text{peer-median}}$
  — retaining beat replacing at the median.

where:
- $V_e$ — the signed value-add of event $e$ (positive = the decision helped)
- $R^{\text{fwd}}_{\text{hired}}$, $R^{\text{fwd}}_{\text{fired}}$,
  $R^{\text{fwd}}_{\text{replacement}}$, $R^{\text{fwd}}_{\text{held}}$ — the
  forward excess returns (§3.4) of the acted-on manager
- $R^{\text{fwd}}_{\text{counterfactual}}$, $R^{\text{fwd}}_{\text{peer-median}}$
  — the forward excess return of the passed-over alternative (§3.6)

Each event ships as a row: `{decision type, date, manager, counterfactual rung,
horizon, forward gap (raw + factor-adjusted), journal thesis, kill-criterion
met?}`. The per-event ledger is presented as **individual stories with
receipts**, never averaged away — at realistic N the stories *are* the honest
output.

### 3.6 The counterfactual resolver (the crux)

A decision's value is only defined against the alternative it passed over. P3
resolves the counterfactual by a fixed hierarchy, most-paired first, and labels
which rung was used on every event:

1. **Replacement-paired** — when a fire and a hire are linked (the manager hired
   to fund the terminated mandate), the two forward paths are compared directly.
   The cleanest comparison; requires a clean mapping in the journal.
2. **Peer-median** — when unpaired, compare against the median forward return of
   same-strategy managers over the identical event-time window. Controls for the
   strategy's fortunes so the decision is judged against *what a typical manager
   in that lane did next*, not against cash.
3. **Benchmark** — the floor: the strategy index. Always available, but
   conflates decision skill with market beta, so it is the last resort and is
   flagged as such.

The hierarchy exists because each rung trades cleanliness for availability: the
paired comparison is cleanest but needs a linked hire/fire, and the benchmark is
always available but noisiest. Labelling the rung on every event keeps the
reader honest about which kind of comparison they are looking at.

### 3.7 The aggregate posterior — shrinkage toward the Goyal–Wahal null

The one place a number crosses events is the estimate of the allocator's
**process value-add**: the average $V_e$. This is a small-N pooling problem
identical in shape to S1's cross-manager alpha, and it is solved with **the same
house estimator, not a new one** — the S1 closed-form normal-normal shrinkage
(imported from the skill engine, not re-derived).

The twist is the prior. The grand mean is **pinned at zero** — the Goyal–Wahal
reference-class base rate that sponsor hire/fire timing adds nothing — with
prior scale `DECISION_VALUE_PRIOR_SCALE` (provisional **2%/yr**, sourced from the
cross-sponsor dispersion of round-trip differentials). The allocator's own
accumulating events update this prior:

$$\hat V^{\text{post}} = w\,\bar V + (1-w)\cdot 0, \qquad
w = \frac{\tau^2}{\tau^2 + \widehat{\text{se}}(\bar V)^2}.$$

where:
- $\hat V^{\text{post}}$ — the posterior (shrunk) estimate of process value-add
- $\bar V$ — the mean of the per-event value-adds $V_e$
- $\tau$ — the prior scale, `DECISION_VALUE_PRIOR_SCALE` (provisional 2%/yr)
- $\widehat{\text{se}}(\bar V)$ — the standard error of the mean, computed on the
  **effective** (not the raw) sample size — see below
- $0$ — the pinned grand mean, the Goyal–Wahal null
- $w$ — the shrinkage weight in $[0, 1]$: how much the data is allowed to move
  the estimate off the prior

In words: the posterior is a weighted blend of the observed mean and the pinned
zero, and the weight rises only as the data becomes precise relative to the
prior. For years, $w$ is small — the data barely moves the posterior off the
null. The posterior ships as an **IntervalStat** whose interval will straddle
zero for a long time, carrying a **VerdictChip** that reads *"indistinguishable
from the base rate at this decision count"* — which is not a failure to
conclude, it is the conclusion.

**Effective N, honestly.** $\widehat{\text{se}}(\bar V)$ must not be the naive
$s/\sqrt{N}$: decisions made in the same market episode share a common forward
path, so their $V_e$ are correlated and the effective sample is far below the
event count. Events are clustered by calendar cohort (quarter of decision), and
the standard error carries the **design-effect** inflation:

$$N_{\text{eff}} = \frac{N}{1 + (\bar m - 1)\,\rho}.$$

where:
- $N_{\text{eff}}$ — the independent-equivalent sample size
- $N$ — the raw number of events
- $\bar m$ — the average number of events per cohort (quarter)
- $\rho$ — the intra-cohort correlation of forward gaps (§7)
- $1 + (\bar m - 1)\rho$ — the **design effect**: the factor by which the
  variance of the mean is inflated by within-cohort correlation

In words: correlated events inside a cohort carry less independent information,
so you divide the raw count by the design effect to get the number of "real"
observations, and the standard error becomes $s/\sqrt{N_{\text{eff}}}$. A block
bootstrap over cohorts is the *reported* interval; the design-effect formula is
the intuition and the cross-check.

**The PowerGate.** Below `MIN_EVENTS_FOR_AGGREGATE` (provisional **12** events)
the aggregate panel **refuses to render a raw value-add average at all** and
shows only the per-event ledger with a banner: *"N too small for an average —
these are individual decisions, not a track record."* The refusal is the pitch,
per the honest-mockup contract. The **shrunk posterior**, by contrast, renders
at any N — honesty at small N is exactly what shrinkage buys — and always **as
an interval**; a bare point estimate of process value-add is a design-system
lint error, exactly as in S1/S2.

### 3.8 What the canonical paper showed

**Goyal & Wahal (2008), "The Selection and Termination of Investment Management
Firms by Plan Sponsors" (*Journal of Finance*).** Studying thousands of hiring
and firing decisions by U.S. plan sponsors, the authors found sponsors chase
performance — hiring managers with strong trailing three-year records and firing
those with weak ones — and pay real transition costs to do it. But when they
tracked what happened *next*, the post-firing excess returns of terminated
managers matched or exceeded the post-hiring returns of their replacements: the
round-trip added nothing. This is why P3 pins its prior at zero. The paper does
*not* say any individual termination is wrong — it establishes a **base rate**
for the reference class, which is precisely how P3 uses it: as a prior to be
updated by the allocator's own events, not as a verdict.

## 4. How to implement

The estimator below is self-contained teaching code — paste it into a fresh
file, install `numpy`, and adapt. It implements the same three formulas as §3:
the event-time forward return and signed value-add (§3.4–3.5), the design effect
(§3.7), and the pinned-null shrinkage posterior (§3.7). Nothing here imports
from any repository; the production module reuses the shared skill-engine
shrinkage instead of re-deriving it, but the logic is identical.

```python
"""Decision-audit ledger + pinned-null posterior — teaching implementation.

Mirrors the method section formula-for-formula:
  1. event-time forward excess return             (forward_excess_return)
  2. signed per-event value-add (hire/fire/hold)  (event_value_add)
  3. design-effect-deflated shrinkage posterior   (pinned_null_posterior)

Self-contained: `pip install numpy`, paste, adapt. No project imports.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class Decision:
    """One journal row, filled at the decision moment (before the outcome).

    `subject` is the manager acted on (hired / fired / held); `counterfactual`
    is the passed-over alternative (the replacement for a fire, the peer-median
    or benchmark otherwise). Both are monthly net-return series in decimal.
    """

    kind: str                    # "hire", "fire", or "hold"
    subject: np.ndarray          # monthly net returns of the manager acted on
    counterfactual: np.ndarray   # monthly net returns of the alternative
    cohort: int                  # calendar quarter of the decision (cluster key)


def forward_excess_return(
    monthly_returns: np.ndarray, monthly_rf: np.ndarray, horizon_years: int
) -> float:
    """Formula 1: cumulative forward excess return over the horizon window.

    Compounds (1 + r_t - rf_t) across the first 12*horizon_years months after
    the decision, then subtracts 1 to convert a growth factor to a return.
    """
    window = 12 * horizon_years
    excess = monthly_returns[:window] - monthly_rf[:window]
    growth_factor = np.prod(1.0 + excess)
    return float(growth_factor - 1.0)


def event_value_add(
    decision: Decision, monthly_rf: np.ndarray, horizon_years: int
) -> float:
    """Formula 2: signed value-add, unified so positive ALWAYS means it helped.

      hire: hired minus the alternative it beat
      fire: replacement minus the fired manager it removed  (round-trip sign)
      hold: retained manager minus the peer-median it declined to replace with
    """
    subject_fwd = forward_excess_return(decision.subject, monthly_rf, horizon_years)
    alt_fwd = forward_excess_return(decision.counterfactual, monthly_rf, horizon_years)

    if decision.kind in ("hire", "hold"):
        return subject_fwd - alt_fwd
    if decision.kind == "fire":
        # `counterfactual` holds the replacement that funded the mandate.
        return alt_fwd - subject_fwd
    raise ValueError(f"unknown decision kind: {decision.kind!r}")


def design_effect(events_per_cohort: float, rho: float) -> float:
    """Formula 3a: variance inflation from within-cohort correlation.

    1 + (mbar - 1)*rho.  Independent events give 1.0; perfectly correlated
    events in cohorts of size mbar collapse to one effective observation each.
    """
    return 1.0 + (events_per_cohort - 1.0) * rho


def effective_n(n_events: int, events_per_cohort: float, rho: float) -> float:
    """Independent-equivalent sample size: raw N divided by the design effect."""
    return n_events / design_effect(events_per_cohort, rho)


def pinned_null_posterior(
    value_adds: np.ndarray,
    events_per_cohort: float,
    rho: float,
    prior_scale: float,
    z: float = 1.645,   # 90% two-sided normal quantile
) -> dict:
    """Formula 3b: shrink the mean value-add toward a prior PINNED at zero.

    Normal-normal conjugate update with the grand mean FIXED at 0 (the
    Goyal-Wahal base rate), not estimated from the cross-section. The standard
    error uses the design-effect-deflated N, so correlated decisions correctly
    move the posterior less. Returns the shrunk point and a 90% interval.
    """
    value_adds = np.asarray(value_adds, dtype=float)
    n_events = value_adds.size
    mean = float(value_adds.mean())
    sample_sd = float(value_adds.std(ddof=1))

    n_eff = effective_n(n_events, events_per_cohort, rho)
    se = sample_sd / np.sqrt(n_eff)           # honest SE, NOT s / sqrt(N)

    tau2 = prior_scale ** 2
    weight = tau2 / (tau2 + se ** 2)          # in [0, 1]; small when se >> tau
    point = weight * mean + (1.0 - weight) * 0.0

    # Posterior variance of a normal-normal update is weight * se**2.
    posterior_sd = np.sqrt(weight) * se
    return {
        "point": point,
        "ci_lo": point - z * posterior_sd,
        "ci_hi": point + z * posterior_sd,
        "shrinkage_weight": weight,
        "n_effective": n_eff,
    }


if __name__ == "__main__":
    # The demo's own cohort structure: 15 events, ~3 per quarterly cohort,
    # intra-cohort correlation ~= 0.536.
    print(round(design_effect(3.0, 0.535939), 2))    # -> 2.07
    print(round(effective_n(15, 3.0, 0.535939), 2))  # -> 7.24 effective events
```

## 5. Reading the demo

The gallery page renders an **honest mockup on simulator output** (honest-mockup
contract): the demo generator runs a synthetic Goyal–Wahal allocator over a
simulator roster with known true alpha and emits ~15 synthetic decisions, then
runs the exact ledger and posterior above on that history. **Demo numbers and
live numbers come from the same code path; only the input decision log differs**
(synthetic vs the team's real journal). Every visual element maps to the method:

- **The posterior IntervalStat band** is $\hat V^{\text{post}}$ from §3.7. On the
  demo it reads **−0.6%/yr** with a **90% interval of −3.8% … +2.5%** — a wide
  band straddling zero. The tick on the rail is the pinned-zero base rate; the
  dot is the shrunk point. The interval crosses zero, so the estimate is
  indistinguishable from "the timing added nothing."
- **The VerdictChip** reads *"indistinguishable from the base rate"* — the
  conclusion, not a failure state. Beside it, the page states the prior is pinned
  at the Goyal–Wahal null (0) with prior scale **2%/yr**.
- **The PowerGate banner** ("Raw average refused … not a track record") fires
  because effective N is **7.2** — 15 events across **5** quarterly cohorts with
  a **design effect of 2.07** ($15 / 2.07 = 7.24$), below the 12-event gate. The
  raw mean is withheld; only the shrunk interval and the per-event stories show.
- **The detectability one-liner** states that at a true 2%/yr edge and ρ ≈ 0.54,
  the posterior interval would first exclude zero at **≈ 717 decisions** — more
  than a career of governance decisions. This is the closed-form
  events-to-detectability, not a Monte-Carlo atlas cell.
- **The counterfactual cohort chart** plots the event-time forward path of the
  **fired** managers (green) against their **replacements** (red). The fired
  recover and the replacements fade — mean reversion, exactly the Goyal–Wahal
  round-trip. The panel is framed as calibration of the termination bar, not an
  accusation.
- **The journal scorecard** shows one hire graded against its pre-committed
  thesis and kill criterion beside its realized 3-year path — a good decision
  with a bad draw is visibly distinguished from a bad decision that got lucky.
- **The per-event ledger** lists all 15 decisions, each with a left border
  (green = the decision helped, red = it hurt), the raw and factor-adjusted
  forward gaps, the counterfactual rung used (**replacement-paired**,
  **peer-median**, or **benchmark**), and whether the kill criterion was met.
  Nothing is averaged away — at this N the stories are the output.

What an allocator should conclude: on this synthetic history the process
value-add is indistinguishable from the Goyal–Wahal base rate, the audit
correctly refuses to manufacture a track record from 15 correlated decisions,
and the value on offer is the *prospective* discipline of the journal plus a
calibrated bar for the next termination vote — not a retrospective p-value.

## 6. Honest limits & go-live

### 6.1 Data contract per tier

P3 is a **decision-level** analytic, so its tier axis is unusual: the tier of
manager *transparency* barely matters, because the inputs are decision dates and
forward return series that exist for the whole roster by construction. What tiers
here is the **counterfactual quality** — how cleanly the passed-over alternative
can be priced.

| Tier | Inputs the live version needs | What the card produces |
| --- | --- | --- |
| **R (minimum)** | The decision journal (dates + type + pre-committed fields, §3.3); monthly net returns for every manager touched by a decision; strategy labels; risk-free + strategy factor set (shared with S2/S1) | The **whole card** — per-event counterfactual ledger, factor-adjusted forward-return gaps, the shrinkage posterior on decision value-add, and the journal scorecard. Everything in §3 runs returns-only. |
| **E** | R + exposure summaries for the managers in each event | Sharpens the counterfactual by adjusting forward gaps for *measured* factor tilts rather than regression-inferred ones — a "was this a bet on the manager or on a factor that happened to pay?" annotation. Does **not** change the estimand. |
| **P** | Not applicable | Holdings buy nothing here: the estimand is a decision's forward return gap, which is a returns-tier quantity. Position-level skill attribution is cards S3/S4, not this one. |

**Alignment & conventions (shared with S1/S2):** monthly net returns as decimals
on a pandas `PeriodIndex` freq `M`; forward windows measured in whole months from
the decision date; a manager with more than 2 missing months inside a forward
window is flagged and that window is marked incomplete, never silently
interpolated. Where a fired manager stops reporting after termination, the
forward series falls back to a **public strategy-index proxy** with an explicit
`proxied` flag — the counterfactual is only as honest as its label.

**Compliance (standing):** in the repo, decision histories are **synthetic
only** — no real hire/fire dates, no real manager names, ever. Governance data is
the most employer-internal surface in the portfolio; the public artifact is the
*method*, not any decision.

### 6.2 What P3 deliberately does not do (do-not-build boundary)

**P3 is deliberately not a significance instrument, and the do-not-build list
draws its boundaries** as sharply as what it does.

- **Not a persistence test.** P3 never claims a manager's performance persists or
  ranks managers on trailing returns. It measures the forward gap of a *decision*
  against its own counterfactual. Standalone persistence rankings are on the
  do-not-build list (noise verdict at 36–60 observations); P3 stays on the
  decision side of that line and says so on the page.
- **No regime splits.** Slicing a handful of decisions into "bull-market hires"
  vs "bear-market fires" turns tiny N into tinier N — the exact forbidden move.
  P3 reports the **pooled** posterior only, with an explicit caveat that
  calendar-episode confounding exists and is *not* resolved by subsetting.
- **No FDR / luck screens.** With events in the tens, multiple-testing machinery
  is a category error; there is nothing to screen.

### 6.3 What governs it instead — the effective-N story

The "validation" is that the intervals are honestly wide. Two checks on the
simulator:

1. **Design-effect calibration.** Generate correlated forward paths across a
   decision cohort, confirm the cohort block-bootstrap interval recovers nominal
   coverage while the naive $s/\sqrt{N}$ interval under-covers badly. This proves
   the effective-N deflation is real, not decorative.
2. **Base-rate replication.** Drive a synthetic allocator that follows the
   Goyal–Wahal behavioral rule (hire on trailing 3y outperformance, fire on
   underperformance) over a simulator roster with **known true alpha**, and
   confirm the ledger recovers the stylized fact: hired cohorts have high
   trailing but average true alpha (lucky), fired cohorts low trailing but
   average true alpha (unlucky), forward gaps mean-revert, and the round-trip
   value-add posterior sits at ≈ 0. If the ledger cannot reproduce Goyal–Wahal on
   ground truth where the answer is known, it is not trustworthy on real
   decisions.

**Events-to-detectability (the honest-N one-liner).** Rather than a Monte-Carlo
power atlas, P3 ships the closed-form count of events at which the value-add
interval would first exclude zero, as a function of the true per-decision alpha
gap and the intra-cohort correlation ρ. On the demo this is **≈ 717 decisions**
at a 2%/yr edge and ρ ≈ 0.54 — dozens would be needed even for a large true edge
with independent decisions, hundreds once cohort correlation is realistic. The
number quantifies "you will not reach significance in a career" and reinforces
the card's thesis rather than undercutting it. This is the only atlas cell P3
warrants, and it is a closed form, not a per-manager metric.

**No statistical kill criterion.** P3 cannot "fail" a power gate — it is a
discipline artifact whose intervals are honest by construction. Its only kill
risk is political: if the framing reads as blame, the card is withdrawn, not
re-tuned (§6.4).

### 6.4 Adoption & packaging

The output is a **governance discipline instrument**, and the framing is a
functional requirement, not courtesy:

- **Prospective discipline, never retrospective blame.** The journal's headline
  is the *next* decision, not the last one. An audit that reads as "here is where
  the committee was wrong" invites the defensiveness that kills adoption; an
  instrument that reads as "here is the base rate our next vote is fighting" is a
  decision aid. The counterfactual panel is framed as calibration of the bar,
  exactly as S2's alt-beta chip is a fee conversation and not an accusation.
- **Score the decision, not the outcome.** Every scorecard shows the
  pre-committed thesis and kill criterion beside the realized path, so a good
  decision with a bad draw is visibly distinguished from a bad decision that got
  lucky (Mauboussin's process-vs-outcome; Kahneman's outcome bias). This is the
  whole reason the journal is filled *before* the outcome.
- **Never a mechanical trigger.** A negative forward gap on one termination is
  never an auto-reversal rule; the ledger is an input to the committee's
  judgment (Dietvorst's adjustable-output posture). Publishing a "decision score"
  as a target would get gamed — decisions written to look good in the journal
  rather than to be good (Goodhart) — so it ships as reviewable evidence, not a
  leaderboard.
- **Kill the dashboard.** Per the demo doctrine, this is delivered as a
  **narrated pack section** at the decision moment (the IC packet before a
  termination vote), not a standing always-on dashboard nobody opens. One page,
  at the moment of the decision.

**Who sees what, when:** the journal and ledger are leadership-and-committee
facing at decision time. There is no manager-facing version — this audits the
allocator, not the manager. The public repo carries only the synthetic
demonstration.

### 6.5 Go-live requirements

- **Data ask:** a maintained **decision journal** (dates + type + pre-committed
  fields) and monthly net returns for every manager touched by a decision (tier
  **R**, roster-wide). The journal is the real ask — it must be filled
  *prospectively*; a journal reconstructed after the fact inherits the hindsight
  bias the card exists to defeat.
- **Sample required:** **none for the journal half** — pre-commitment discipline
  pays from the first record. The ledger's aggregate panel renders a raw average
  only above `MIN_EVENTS_FOR_AGGREGATE` (provisional 12) events, and even then
  **as an interval that will straddle zero for years** — there is no sample size
  at which a single allocator's decisions reach significance, and the card says
  so rather than implying one is around the corner.
- **Build effort:** **S** — schema, deterministic ledger, reuse of S1/S2 code,
  and the Goyal–Wahal replication demo (the bulk of the work). No new runtime
  dependency; the pooling is the closed form, not MCMC.
- **Adoption gate (not a build gate):** running P3 on *real* decisions is
  leadership's call; the repo version stays synthetic permanently. The only kill
  risk is the framing failing the blame test (§6.4).

**Implementation home (reference):** a decision-audit module
(`src/quant_allocator/flagships/decision_audit/`) with a validated
`DecisionRecord` schema in `journal.py` (write-time validation, no scoring), a
deterministic `ledger.py` (forward returns, the counterfactual resolver, signed
$V_e$ rows), an `aggregate.py` that imports the shared shrinkage
(`skill_ledger/empirical.py`), pins the grand mean at the Goyal–Wahal null,
computes the cohort-clustered interval and design effect, and enforces the
PowerGate, and a rendering-only `report.py`. It depends on the S2 factor pipeline
and the S1 closed-form shrinkage — both imported, neither duplicated. Sequencing:
independent of the flagships, buildable any time.

## 7. Deeper reading

### 7.1 Canonical references

1. **Goyal & Wahal (2008), "The Selection and Termination of Investment
   Management Firms by Plan Sponsors," *Journal of Finance*.** Across thousands
   of plan-sponsor decisions, sponsors hire on strong trailing three-year records
   and fire on weak ones, paying real transition costs — yet the post-firing
   returns of terminated managers match or exceed the post-hiring returns of
   their replacements. The round-trip adds nothing. This is P3's prior (pinned at
   zero) and the demo's replication target; it establishes a *base rate* for the
   reference class, not a verdict on any single termination.
2. **Kahneman (2011), *Thinking, Fast and Slow*** (outcome bias, hindsight, the
   inside/outside view) and Klein's **premortem** — the cognitive case for a
   pre-committed journal: the realized path contaminates the remembered thesis, so
   only a thesis written before the draw can grade the decision cleanly.
3. **Mauboussin (2012), *The Success Equation*** — process versus outcome in
   skill-vs-luck domains; why to grade the decision, not the result. A good
   decision (positive expected value against a correct base rate) can draw a bad
   outcome, and scoring by outcome rewards luck and punishes discipline.
4. **Dietvorst, Simmons & Massey (2018), "Overcoming Algorithm Aversion,"
   *Management Science*** — adjustable, advice-framed outputs get used; verdicts
   get shelved. This governs P3's "input to the committee, not a trigger" posture
   (shared with M5/S2).

Reference-class forecasting ties them together: Goyal–Wahal's cross-sponsor
result is your **prior**, not your answer; your own accumulating decisions are
the likelihood that updates it (Kahneman's outside view; Flyvbjerg's
reference-class forecasting). Starting from the base rate — rather than from "our
committee is above average" — is the disciplined default.

### 7.2 Questions you should be able to answer after reading this page

- State the **Goyal–Wahal headline** and precisely what it does and does not
  imply for a *single* allocator (a base rate to fight, not proof any given
  termination is wrong).
- Explain why an allocator's own hire/fire audit **cannot reach significance in a
  career**, using the design-effect deflation — and why that is fine: the value
  is prospective calibration, not a retrospective p-value. Work the example: 20
  events, 4 per cohort, ρ = 0.5 ⇒ design effect 2.5 ⇒ $N_{\text{eff}} = 8$.
- Own why the shrinkage weight $w = \tau^2 / (\tau^2 + \text{se}^2)$ stays near
  zero for years: at a handful of noisy events, $\text{se}^2 \gg \tau^2$, so the
  posterior barely leaves the prior — and that *is* the honest answer.
- Justify the **counterfactual hierarchy** (replacement → peer-median →
  benchmark) and why factor-adjusting the forward gap separates selection skill
  from a factor bet that paid.
- Explain **outcome bias vs process quality**, and why a journal reconstructed
  after the fact is worthless (the realized path contaminates the remembered
  thesis).
- Draw the **do-not-build boundary**: why auditing decisions is *not* a
  persistence test, and why regime-splitting the events is the forbidden move.

---

## Method review (2026-07-07) — APPROVED, implementation-ready

- **`MIN_EVENTS_FOR_AGGREGATE` RULED:** it gates the RAW mean display only; the
  SHRUNK posterior IntervalStat renders at any N — honesty at small N is the
  point of shrinkage, and the "indistinguishable from the base rate" chip is the
  product, not a failure state. 12 stands as the raw-mean gate, numerics-docket
  item.
- **`DECISION_VALUE_PRIOR_SCALE` (2%/yr):** verify against the actual
  Goyal-Wahal round-trip dispersion figure at build time — numerics-gate item
  with the citation pinned in the generator.
- **Optional X1 atlas cell RULED OUT (converge-or-cut):** the MC cell
  over-formalizes a card whose thesis is "you will never get there." The
  closed-form one-liner (events-to-detectability at stated rho and gap) ships
  instead.
</content>
