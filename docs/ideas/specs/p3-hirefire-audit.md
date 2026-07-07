# P3 · Hire/Fire Decision Audit & Journal — Method Spec

**Status: Reviewed (the lead reviewer, 2026-07-07) — implementation-ready**
**Date:** 2026-07-07
**Card:** [`docs/ideas/2026-07-05-idea-cards.md`](../2026-07-05-idea-cards.md) § P3
**Demo:** gallery page `p3.html` (counterfactual cohort panel + one journal
scorecard; fully synthetic decision history, §5)

## 1. Problem & decision hook

Goyal–Wahal (2008): plan sponsors hire managers after strong trailing
three-year performance and fire after weak trailing performance, yet the
**fired managers subsequently match or beat the newly hired ones**. The
round-trip adds no value — the timing is the mistake. Almost no allocator
backtests its *own* hire/fire timing; the decision that most moves the book is
the one least measured. P3 turns governance into data along two axes: a
**prospective decision journal** (thesis, expected alpha, horizon, and kill
criteria pre-committed at the moment of the hire or fire) and a
**retrospective counterfactual ledger** (what the fired manager did *after*
firing, the hired manager *after* hiring, each against the alternative the
decision passed over).

The subject under audit is **the allocator's decision, not the manager's
skill**. P3 never ranks managers, never claims performance persists, and never
issues a verdict on a single termination. Its unit of analysis is the *event*
— a hire, a fire, a considered-but-retained hold — and its honest posture is
that an allocator makes a handful of these per year, so for years the data
supports **description and prior-updating, not significance**. Saying that
plainly, on the page, is the product.

Decisions improved: **redeem** — the ledger calibrates the bar for
termination against the base rate that firing often destroys value; **select**
— the journal imposes pre-commitment discipline (a written thesis and kill
criterion) that defends the next decision against outcome bias. Customer:
department leadership (governance) and the team's own future self.

**What it is not:** not a manager-persistence test (§4 draws that boundary
against the do-not-build list), not a significance claim on any career-length
sample, and — in this public repo — never run on real decisions. The repo
version is synthetic by standing rule; real adoption is leadership's call.

## 2. Data contract per tier

P3 is a **decision-level** analytic, so its tier axis is unusual: the tier of
manager *transparency* barely matters, because the inputs are decision dates
and forward return series that exist for the whole roster by construction.
What tiers here is the **counterfactual quality** — how cleanly the passed-over
alternative can be priced.

| Tier | Inputs the live version needs | What the card produces |
| --- | --- | --- |
| **R (minimum)** | The decision journal (dates + type + pre-committed fields, §3.1); monthly net returns for every manager touched by a decision; strategy labels; risk-free + strategy factor set (shared with S2/S1) | The **whole card** — per-event counterfactual ledger, factor-adjusted forward-return gaps, the shrinkage posterior on decision value-add, and the journal scorecard. Everything in §3 runs returns-only. |
| **E** | R + exposure summaries for the managers in each event | Sharpens the counterfactual by adjusting forward gaps for *measured* factor tilts rather than regression-inferred ones — a "was this a bet on the manager or on a factor that happened to pay?" annotation. Does **not** change the estimand. |
| **P** | Not applicable | Holdings buy nothing here: the estimand is a decision's forward return gap, which is a returns-tier quantity. Position-level skill attribution is cards S3/S4, not this one. |

**Alignment & conventions (shared with S1/S2 §2):** monthly net returns as
decimals on a pandas `PeriodIndex` freq `M`; forward windows measured in whole
months from the decision date; a manager with more than 2 missing months
inside a forward window is flagged and that window is marked incomplete, never
silently interpolated. Where a fired manager stops reporting after termination,
the forward series falls back to a **public strategy-index proxy** with an
explicit `proxied` flag — the counterfactual is only as honest as its label.

**Compliance (standing):** in the repo, decision histories are **synthetic
only** — no real hire/fire dates, no real manager names, ever. Governance data
is the most employer-internal surface in the portfolio; the public artifact is
the *method*, not any decision.

## 3. Methodology

Two halves with a hard division of labor. The **journal** (§3.1) is a
prospective discipline instrument — a schema filled at the decision moment. The
**ledger** (§3.2–3.4) is deterministic accounting over forward returns; nothing
in it is a hypothesis test. The **posterior** (§3.5) is the one estimator, and
it is the house shrinkage method (S1), not a parallel invention.

### 3.1 The decision journal (prospective, pre-commitment)

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
  hire↔fire, or `peer-median` / `benchmark` when unpaired (§3.3)

The **hold-under-review** record is load-bearing: auditing only actions
(hires and fires) survivorship-biases your own decision set. The manager you
*considered* firing and kept is the control arm. Recording holds is what makes
the ledger a decision audit rather than an action audit.

The journal's value is prospective: pre-committing the thesis and the kill
criterion is the only clean defense against **outcome bias** (§8) — scoring a
decision by whether it *felt* right in hindsight rather than whether it met the
bar set in advance. This half of P3 delivers value on day one, before a single
event has a forward window long enough to score.

### 3.2 Event-time forward returns (deterministic)

All accounting is in **event time**: month 0 is the decision date, and every
event is tracked forward over `AUDIT_HORIZONS_YEARS` (provisional
**{1, 2, 3}y**). For manager $i$ decided at date $d$, the forward excess
return over horizon $h$ is the cumulative excess over the risk-free series:

$$R^{\text{fwd}}_i(d, h) = \prod_{t=d+1}^{d+12h}\big(1 + r_{i,t} - r_{f,t}\big) - 1.$$

A **factor-adjusted** variant replaces the raw excess with the cumulative
regression alpha over the forward window, using the S2 factor pipeline
(strategy-appropriate factor set, de-smoothed where illiquid). Both are
reported: the raw gap is what leadership feels; the factor-adjusted gap
separates "we picked a better manager" from "the factor the manager was tilted
to happened to pay." A hire that looks brilliant on raw forward return but
zero on factor-adjusted return was a factor bet, not a selection.

### 3.3 The counterfactual resolver (the crux)

A decision's value is only defined against the alternative it passed over.
P3 resolves the counterfactual by a fixed hierarchy, most-paired first, and
labels which rung was used on every event:

1. **Replacement-paired** — when a fire and a hire are linked (the manager
   hired to fund the terminated mandate), the two forward paths are compared
   directly. The cleanest comparison; requires a clean mapping in the journal.
2. **Peer-median** — when unpaired, compare against the median forward return
   of same-strategy managers over the identical event-time window. Controls
   for the strategy's fortunes so the decision is judged against *what a
   typical manager in that lane did next*, not against cash.
3. **Benchmark** — the floor: the strategy index. Always available, but
   conflates decision skill with market beta, so it is the last resort and is
   flagged as such.

### 3.4 Signed decision value-add per event

Sign conventions are unified so that **positive always means the decision
helped**, regardless of type:

- **Hire:** $V_e = R^{\text{fwd}}_{\text{hired}} - R^{\text{fwd}}_{\text{counterfactual}}$
  (the hire beat the alternative).
- **Fire:** $V_e = R^{\text{fwd}}_{\text{replacement}} - R^{\text{fwd}}_{\text{fired}}$
  (the fire helped iff what replaced the manager did better than keeping them —
  this is exactly the Goyal–Wahal round-trip, and its historical sign is
  *negative* on average).
- **Hold-under-review:** $V_e = R^{\text{fwd}}_{\text{held}} -
  R^{\text{fwd}}_{\text{peer-median}}$ (retaining beat replacing at the median).

Each event ships as a row: `{decision type, date, manager, counterfactual rung,
horizon, forward gap (raw + factor-adjusted), journal thesis, kill-criterion
met?}`. The per-event ledger is presented as **individual stories with
receipts**, never averaged away — at realistic N the stories *are* the honest
output.

### 3.5 The aggregate posterior — shrinkage toward the Goyal–Wahal null

The one place a number crosses events is the estimate of the allocator's
**process value-add**: the average $V_e$. This is a small-N pooling problem
identical in shape to S1's cross-manager alpha, and it is solved with **the
same house estimator, not a new one** — the S1 §3.6 closed-form normal-normal
shrinkage (`skill_ledger/empirical.py`, imported, not re-derived).

The twist is the prior. The grand mean is **pinned at zero** — the
Goyal–Wahal reference-class base rate that sponsor hire/fire timing adds
nothing — with prior scale `DECISION_VALUE_PRIOR_SCALE` (provisional **2%/yr**,
sourced from the cross-sponsor dispersion of round-trip differentials). The
allocator's own accumulating events update this prior:

$$\hat V^{\text{post}} = w\,\bar V + (1-w)\cdot 0, \qquad
w = \frac{\tau^2}{\tau^2 + \widehat{\text{se}}(\bar V)^2}.$$

For years, $w$ is small: the data barely moves the posterior off the null. The
posterior ships as an **IntervalStat** whose interval will straddle zero for a
long time, carrying a **VerdictChip** that reads *"indistinguishable from the
base rate at this decision count"* — which is not a failure to conclude, it is
the conclusion.

**Effective N, honestly.** $\widehat{\text{se}}(\bar V)$ must not be the naive
$s/\sqrt{N}$: decisions made in the same market episode share a common forward
path, so their $V_e$ are correlated and the effective sample is far below the
event count. Events are clustered by calendar cohort (quarter of decision),
and the standard error carries the **design-effect** inflation

$$N_{\text{eff}} = \frac{N}{1 + (\bar m - 1)\,\rho},$$

with $\bar m$ the average events per cohort and $\rho$ the intra-cohort
correlation of forward gaps (§8.1). A block bootstrap over cohorts is the
reported interval; the design-effect formula is the intuition and the
cross-check.

**The PowerGate.** Below `MIN_EVENTS_FOR_AGGREGATE` (provisional **12**
events) the aggregate panel **refuses to render a value-add number at all** and
shows only the per-event ledger with a banner: *"N too small for an average —
these are individual decisions, not a track record."* The refusal is the pitch,
per the honest-mockup contract. Above the gate, the number renders **as an
interval only**; a bare point estimate of process value-add is a design-system
lint error, exactly as in S1/S2.

## 4. Power & validation plan

**P3 is deliberately not a significance instrument, and the do-not-build list
draws its boundaries.** This section says what it does *not* do as sharply as
what it does.

**What it does not do (do-not-build adjacency, binding):**

- **Not a persistence test.** P3 never claims a manager's performance persists
  or ranks managers on trailing returns. It measures the forward gap of a
  *decision* against its own counterfactual. Standalone persistence rankings
  are on the do-not-build list (Sweep C noise verdict at 36–60 obs); P3 stays
  on the decision side of that line and says so on the page.
- **No regime splits.** Slicing a handful of decisions into "bull-market
  hires" vs "bear-market fires" turns tiny N into tinier N — the exact
  forbidden move. P3 reports the **pooled** posterior only, with an explicit
  caveat that calendar-episode confounding exists and is *not* resolved by
  subsetting.
- **No FDR / luck screens.** With events in the tens, multiple-testing
  machinery is category error; there is nothing to screen.

**What governs it instead: the effective-N story.** The "validation" is that
the intervals are honestly wide. Two checks:

1. **Design-effect calibration.** On the simulator, generate correlated
   forward paths across a decision cohort, confirm the cohort block-bootstrap
   interval recovers nominal coverage while the naive $s/\sqrt{N}$ interval
   under-covers badly. This proves the effective-N deflation is real, not
   decorative.
2. **Base-rate replication.** Drive a synthetic allocator that follows the
   Goyal–Wahal behavioral rule (hire on trailing 3y outperformance, fire on
   underperformance) over a simulator roster with **known true alpha**, and
   confirm the ledger recovers the stylized fact: hired cohorts have high
   trailing but average true alpha (lucky), fired cohorts low trailing but
   average true alpha (unlucky), forward gaps mean-revert, and the round-trip
   value-add posterior sits at ≈0. If the ledger cannot reproduce
   Goyal–Wahal on ground truth where the answer is known, it is not trustworthy
   on real decisions.

**Optional X1 atlas contribution.** P3's honest-N message can be made a
**power curve** and contributed to the X1 atlas ([`x1-tier-power-atlas.md`](x1-tier-power-atlas.md)):
*events-until-the-value-add-interval-excludes-zero*, as a function of true
per-decision alpha gap and intra-cohort correlation $\rho$. The expected shape
— dozens of independent decisions needed to detect even a large true edge,
hundreds once cohort correlation is realistic — quantifies "you will not reach
significance in a career" and reinforces the card's thesis rather than
undercutting it. This is the only atlas cell P3 warrants; it is not a
per-manager metric like S2's.

**No statistical kill criterion.** P3 cannot "fail" a power gate — it is a
discipline artifact whose intervals are honest by construction. Its only kill
risk is political (§6): if the framing reads as blame, the card is withdrawn,
not re-tuned.

## 5. Implementation architecture

Module home: **`src/quant_allocator/flagships/decision_audit/`**

- `journal.py` — the `DecisionRecord` schema (§3.1) as a validated dataclass
  (pydantic if the repo standardizes on it): type, dates, pre-committed fields,
  counterfactual designation. Write-time validation; no scoring here.
- `ledger.py` — **deterministic** event-time accounting: forward-return
  computation (raw + factor-adjusted via the S2 pipeline), the counterfactual
  resolver (§3.3) with its labeled hierarchy, and the signed per-event $V_e$
  rows (§3.4). No estimator in this file.
- `aggregate.py` — the shrinkage posterior (§3.5): **imports** the S1
  closed-form (`skill_ledger/empirical.py`), pins the grand mean at the
  Goyal–Wahal null, computes the cohort-clustered interval and design-effect,
  and enforces the `MIN_EVENTS_FOR_AGGREGATE` PowerGate.
- `report.py` — pack JSON: per-event ledger rows, the aggregate IntervalStat +
  VerdictChip, the journal scorecard (thesis vs realized, kill-criterion-met
  flags). Rendering only; no math.

**Demo vs live.** The gallery page renders an **honest mockup on simulator
output** (honest-mockup contract §6): the demo generator
`src/quant_allocator/demo_data/p3_hirefire.py` runs a synthetic Goyal–Wahal
allocator over a simulator roster with known true alpha and emits ~15 synthetic
decisions, then calls `ledger.py`/`aggregate.py` on that history — **demo
numbers and live numbers come from the same code path; only the input decision
log differs** (synthetic vs the team's real journal). The demo shows: the
counterfactual cohort panel (fired-vs-replacement forward paths mean-reverting),
one journal scorecard (a hire with its pre-committed thesis and its 3-years-later
score against those pre-commitments), and the aggregate IntervalStat as a wide
band straddling zero with the *"indistinguishable from the base rate"* chip.

**What the demo shows vs what live adds:** the demo proves the method and the
honesty (Goyal–Wahal reproduced on ground truth, PowerGate visibly refusing an
average at N≈15). The live build adds real decision-log ingestion, real (or
public-proxy) forward return series, and the E-tier factor-tilt annotation.
The repo version **never ingests real governance data** — that boundary is
permanent, not a wave-3 upgrade.

**Dependencies:** the S2 factor pipeline (forward-return adjustment) and the S1
closed-form shrinkage (`empirical.py`) — both imported, neither duplicated. No
new runtime dependency; no PyMC (the pooling is the closed form, not MCMC).
**Effort: S** — schema + deterministic ledger + a small reuse of existing
shrinkage; the Goyal–Wahal replication demo is the bulk of the work.

**Sequencing:** independent of the flagships; buildable any time. Reuses S1 and
S2 code but blocks on neither for the demo (the closed form and factor
regression already exist in the substrate).

## 6. Adoption & packaging

The output is a **governance discipline instrument**, and the framing is a
functional requirement, not courtesy (Sweep E):

- **Prospective discipline, never retrospective blame.** The journal's headline
  is the *next* decision, not the last one. An audit that reads as "here is
  where the committee was wrong" invites the defensiveness that kills adoption;
  an instrument that reads as "here is the base rate our next vote is fighting"
  is a decision aid. The counterfactual panel is framed as calibration of the
  bar, exactly as S2's alt-beta chip is a fee conversation and not an accusation.
- **Score the decision, not the outcome.** Every scorecard shows the
  pre-committed thesis and kill criterion beside the realized path, so a good
  decision with a bad draw is visibly distinguished from a bad decision that got
  lucky (Mauboussin's process-vs-outcome; Kahneman's outcome bias). This is the
  whole reason the journal is filled *before* the outcome.
- **Never a mechanical trigger.** A negative forward gap on one termination is
  never an auto-reversal rule; the ledger is an input to the committee's
  judgment (Dietvorst adjustable-output posture). Publishing a "decision score"
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

## 7. Go-live requirements

The demo page's "what this needs to go live" box, expanded:

- **Data ask:** a maintained **decision journal** (dates + type +
  pre-committed fields) and monthly net returns for every manager touched by a
  decision (tier **R**, roster-wide). The journal is the real ask — it must be
  filled *prospectively*; a journal reconstructed after the fact inherits the
  hindsight bias the card exists to defeat.
- **Sample required:** **none for the journal half** — pre-commitment discipline
  pays from the first record. The ledger's aggregate panel renders an average
  only above `MIN_EVENTS_FOR_AGGREGATE` (provisional 12) events, and even then
  **as an interval that will straddle zero for years** — there is no sample size
  at which a single allocator's decisions reach significance, and the card says
  so rather than implying one is around the corner.
- **Build effort:** **S** — schema, deterministic ledger, reuse of S1/S2 code,
  and the Goyal–Wahal replication demo.
- **Adoption gate (not a build gate):** running P3 on *real* decisions is
  leadership's call; the repo version stays synthetic permanently. The only
  kill risk is the framing failing the blame test (§6).

## 8. Learning notes

*The spec program doubles as a curriculum; this is what to defend unaided.*

**Derivations to own (work each by hand once):**

1. **Why overlapping decisions crush effective N.** Decisions made in the same
   market episode share a common forward path, so their value-adds $V_e$ are
   positively correlated. For $N$ events in cohorts of average size $\bar m$
   with intra-cohort correlation $\rho$, the variance of the mean inflates by
   the **design effect** $1 + (\bar m - 1)\rho$, giving
   $N_{\text{eff}} = N / (1 + (\bar m - 1)\rho)$. Work an example: 20 events,
   4 per cohort, $\rho = 0.5$ ⇒ $N_{\text{eff}} = 20 / 2.5 = 8$. This is why
   the naive $s/\sqrt{N}$ interval lies and the cohort bootstrap is mandatory.
2. **Shrinkage toward a pinned null** (§3.5) — the same normal-normal
   completing-the-square as S1 §3.6, but the grand mean is fixed at the
   Goyal–Wahal base rate (0) rather than estimated from the cross-section. Own
   why $w = \tau^2 / (\tau^2 + \text{se}^2)$ stays near zero for years: at a
   handful of noisy events, $\text{se}^2 \gg \tau^2$, so the posterior barely
   leaves the prior — and that *is* the honest answer.
3. **Outcome bias vs process quality.** A good decision (positive expected
   value against a correct base rate) can draw a bad outcome, and a bad
   decision can get lucky. Scoring by outcome rewards luck and punishes
   discipline. Pre-committed kill criteria are the only clean way to grade the
   *decision*: did it meet the bar set before the draw? Derive why hindsight
   makes reconstructed journals worthless (the realized path contaminates the
   remembered thesis).
4. **Reference-class forecasting.** Goyal–Wahal's cross-sponsor result is your
   **prior**, not your answer; your own accumulating decisions are the
   likelihood that updates it (Kahneman's outside view; Flyvbjerg's
   reference-class forecasting). Own why starting from the base rate — rather
   than from "our committee is above average" — is the disciplined default.

**Canonical references (3–4 to own):**

1. **Goyal & Wahal (2008), "The Selection and Termination of Investment
   Management Firms by Plan Sponsors," *Journal of Finance*** — the round-trip
   result that is P3's prior and the demo's replication target. Know the
   headline: post-firing excess returns of terminated managers match or exceed
   the post-hiring returns of their replacements.
2. **Kahneman (2011), *Thinking, Fast and Slow*** (outcome bias, hindsight,
   the inside/outside view) and Klein's **premortem** — the cognitive case for
   a pre-committed journal.
3. **Mauboussin (2012), *The Success Equation*** — process vs outcome in
   skill-vs-luck domains; why to grade the decision, not the result.
4. **Dietvorst, Simmons & Massey (2018), "Overcoming Algorithm Aversion,"
   *Management Science*** — adjustable, advice-framed outputs get used; verdicts
   get shelved. Governs P3's "input to the committee, not a trigger" posture
   (shared with M5/S2).

**Defend unaided:**

- State the **Goyal–Wahal headline** and precisely what it does and does not
  imply for a *single* allocator (a base rate to fight, not proof any given
  termination is wrong).
- Explain why an allocator's own hire/fire audit **cannot reach significance in
  a career**, using the design-effect deflation — and why that is fine: the
  value is prospective calibration, not a retrospective p-value.
- Justify the **counterfactual hierarchy** (replacement → peer-median →
  benchmark) and why factor-adjusting the forward gap separates selection skill
  from a factor bet that paid.
- Draw the **do-not-build boundary**: why auditing decisions is *not* a
  persistence test, and why regime-splitting the events is the forbidden move.

---

## gate review (2026-07-07) — APPROVED, implementation-ready

- **`MIN_EVENTS_FOR_AGGREGATE` RULED:** it gates the RAW mean display only; the
  SHRUNK posterior IntervalStat renders at any N — honesty at small N is the
  point of shrinkage, and the "indistinguishable from the base rate" chip is
  the product, not a failure state. 12 stands as the raw-mean gate,
  numerics-docket item.
- **`DECISION_VALUE_PRIOR_SCALE` (2%/yr):** verify against the actual
  Goyal-Wahal round-trip dispersion figure at build time — numerics-gate item
  with the citation pinned in the generator.
- **Optional X1 atlas cell RULED OUT (converge-or-cut):** the MC cell
  over-formalizes a card whose thesis is "you will never get there." The
  closed-form one-liner (events-to-detectability at stated rho and gap) ships
  instead.
