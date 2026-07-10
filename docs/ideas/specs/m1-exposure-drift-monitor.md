# M1 · Exposure Hygiene & Drift Monitor — Method Spec

**Date:** 2026-07-07
**Status:** Reviewed — method gate passed 2026-07-07 (rulings in §8)
**Card:** [`2026-07-05-idea-cards.md` → "M1 · Exposure hygiene & drift monitor"](../2026-07-05-idea-cards.md)
**Demo page:** wave-2 gallery page `m1.html` (planned; monitoring batch, weeks 3–4)
**Fulfils:** X1 atlas docket **D-11** — the exposure-drift detector deferred out
of `x1-tier-power-atlas.md` §3.2 into this card's lane. The sections below define
that detector and its calibration.

This spec is written as a technical blog post: a motivated reader with no prior
exposure to statistical process control should be able to follow it end to end,
build the mental model before meeting the math, and reproduce the estimator from
the mock implementation in §4.

---

## 1. What this is

A mandate states **bands** — plain-English limits the manager agreed to live
inside. "Beta-neutral stock picking." "Gross exposure no more than 2.0×."
"Portfolio duration inside ±1 year." Each quarter the manager's risk report
discloses the actual exposures, and someone on the investment team reads them
against those bands by hand. M1 is the analytic that does that reading
automatically and, crucially, tells the difference between two things that look
alike on a single month's report: a book that has genuinely **drifted** out of its
lane and is staying there, versus a book that merely **wandered** a hair over the
line for one month because its names rotated — the honest, self-correcting jitter
every active book shows.

What it produces, concretely, is a monitoring panel for one manager: the measured
exposure path drawn against its stated band, an **alarm** that lights up only when
a band excursion has *persisted* long enough to be drift rather than noise, and a
second panel that watches whether the return stream is quietly becoming
"accidental factor" (index-like beta the client is not paying for) rather than the
intended idiosyncratic alpha. The customer is the investment team on its quarterly
cycle, and the decision moment is quarterly-review preparation — the panel turns
"here is a template of things a manager might have done" into "here is the
specific, measured, sourced change worth asking about." Sweep B calls this the
single most transplantable platform analytic at the exposure tier.

## 2. Why we use it

**The decision problem.** Two decisions hang on this reading. The first is
**monitor**: drift *leads* the return series. A book that is quietly loading net
market beta is a risk-report event months before it becomes a performance event,
so catching the exposure change early is strictly more useful than waiting for the
returns to reveal it. The second is **engage**: the quarterly review needs a
specific, defensible talking point — "your measured net beta has walked to 0.45
against a stated ±0.10 band; can you walk us through why?" — not a generic
checklist. M1 supplies exactly that sourced, measured item.

**Why the naive alternatives fail.**

- *A single-month band-breach flag over-fires.* An active book turns its names over
  constantly; on any given month it can poke a hair past a band edge purely because
  of that rotation, then fall back the next month. Firing an alarm on the first
  month over the line would cry wolf on a book that is behaving exactly as intended.
  The intuition to hold: one month over the band is not evidence of drift — a *run*
  of months over the band, each adding to the last, is. The flag throws away the
  accumulating evidence that a run carries.
- *Inferring drift from returns is even worse here.* The tempting shortcut is to
  regress the manager's returns on a set of style indices and watch the fitted betas
  move over a rolling window (returns-based style analysis, §3 below). At the
  36–60-month track lengths we actually have, those rolling betas are so noisy that a
  real, economically meaningful drift is buried in estimation error. The program's
  convergence review puts "returns-based style-drift *inference*" on the explicit
  **do-not-build list** and Sweep C verdicts it **Noise**.

**What M1 wins over both.** It reads the *disclosed* exposure directly — the
measurement is exact, not inferred — and it layers a *calibrated* persistence test
on top that separates drift from wander with a stated, honest false-alarm rate. It
is the "measure at the exposure tier instead of inferring from returns" answer to
exactly the drift question the do-not-build list forbids inferring. Two boundaries
matter: M1 is **not** a returns-based style-drift estimator (it never regresses a
time-varying beta out of returns to manufacture a drift claim), and it is **not** a
redemption trigger — a breach is an invitation to explain, never a rule that fires
capital. The returns-based rolling-beta view survives only as a **labelled
descriptive fallback** (§3, R tier), carrying a noise chip, never a verdict.

## 3. How it works

### 3.1 The mental model, in prose

Picture the manager's net-beta reading plotted month by month, with a horizontal
band drawn at the mandate's stated limits. Most months the reading bounces around
inside the band. Occasionally it steps just outside. The question is never "is it
outside right now?" — that is a one-month accident — but "has it been outside, and
*staying* outside, long enough that chance rotation cannot explain it?"

The tool that answers this is a running tally. Every month the reading sits above
the upper band edge, we add the amount by which it exceeds the edge to a running
sum — but we first subtract a small **allowance**, a permitted amount of honest
overshoot. If a month is only a whisker over the edge (less than the allowance),
the tally actually *shrinks*, and a floor keeps it from going below zero. So an
isolated poke over the line decays back to zero and is forgotten. But a *sustained*
walk beyond the edge overwhelms the allowance every month, and the tally climbs and
climbs. When the tally crosses a **decision threshold**, we declare drift. That
running tally is Page's cumulative sum — the CUSUM — and it is the entire idea:
cumulative sums detect a persistent shift that an instantaneous flag misses,
because they *accumulate* the evidence a run of small excursions carries instead of
judging each month in isolation.

The one subtle part is where the decision threshold comes from. It is not a number
we pick by taste. We set it by simulating the book under *no* drift — pure honest
wander — many times, and choosing the threshold high enough that the tally rarely
crosses it by chance. That is the calibration, and §3.4 explains why the simulation
must be an *autocorrelated* one.

### 3.2 A worked toy example with small numbers

Take an upper band edge $U = 0.10$ (a beta-neutral mandate's ceiling) and an
allowance $k = 0.05$. Suppose the measured net beta over six months reads:

| Month | $x_t$ | $x_t - U$ | $(x_t - U) - k$ | $S^{+}_t = \max(0,\, S^{+}_{t-1} + \text{col}_4)$ |
| --- | --- | --- | --- | --- |
| 1 | 0.12 | +0.02 | −0.03 | max(0, 0 − 0.03) = **0.00** |
| 2 | 0.09 | −0.01 | −0.06 | max(0, 0 − 0.06) = **0.00** |
| 3 | 0.18 | +0.08 | +0.03 | max(0, 0 + 0.03) = **0.03** |
| 4 | 0.22 | +0.12 | +0.07 | max(0, 0.03 + 0.07) = **0.10** |
| 5 | 0.25 | +0.15 | +0.10 | max(0, 0.10 + 0.10) = **0.20** |
| 6 | 0.24 | +0.14 | +0.09 | max(0, 0.20 + 0.09) = **0.29** |

Month 1 is over the edge but only slightly, so after the allowance the tally stays
at zero — correctly treated as noise. Month 2 is back inside, tally still zero.
From month 3 the book is decisively and persistently over the edge; the tally
accumulates 0.03, 0.10, 0.20, 0.29. If the calibrated threshold were $h = 0.15$,
the alarm fires at **month 5** — several months into a genuine walk, once the
evidence has accumulated, not on the month-1 blip. That lag between the drift's
onset and the alarm is the **detection delay**, and reporting its distribution honestly (rather than pretending detection
is instantaneous) is the performance statement M1 makes.

### 3.3 The math

**Bands and the measured path.** For each monitored exposure class $j$ (net beta,
gross, a factor beta, a sector weight, …) the mandate supplies a band $[L_j, U_j]$.
The risk report supplies the realised path $x_{j,t}$.

where:
- $j$ — the exposure class being monitored (one CUSUM pair runs per class).
- $t$ — the observation index, in the manager's native reporting cadence (months).
- $L_j,\, U_j$ — the stated lower and upper band edges for class $j$, in that
  class's own units (beta units for a beta, exposure units for gross, weight
  percentage points for a sector, years for duration).
- $c_j = (L_j + U_j)/2$ — the band centre; $w_j = (U_j - L_j)/2$ — the band
  half-width. (Defined here for completeness; the CUSUM uses the edges directly.)
- $x_{j,t}$ — the **disclosed, measured** exposure for class $j$ at time $t$. No
  estimation happens here — $x_{j,t}$ is read off the risk report, not inferred.

When a mandate leaves a class's band unstated, the monitor substitutes a declared
default (`NET_BETA_BAND_DEFAULT`, see the constants table in §6) and marks the band
*assumed*, so a reader never mistakes a default for a stated limit.

**The instantaneous band-breach flag (pure measurement — Robust).**

$$\text{breach}_{j,t} = \mathbb{1}\{x_{j,t} < L_j - \delta_j \ \lor\ x_{j,t} > U_j + \delta_j\}$$

where:
- $\mathbb{1}\{\cdot\}$ — the indicator: 1 if the condition holds, 0 otherwise.
- $\delta_j$ — a per-class **materiality dead-band** (`DELTA_BAND`): the move below
  which an excursion is disclosure noise, not a statement of position.
- $\lor$ — logical "or" (breach on either side of the band).

In words: the flag is 1 whenever the exposure sits materially outside its band on
*this* observation. It is exact and always honest — but it is **trigger-happy**,
because an autocorrelated book poking a hair over $U_j$ for one month is not
drifting. That is precisely why the instantaneous flag is not the alarm; it is the
raw material the persistence layer consumes.

**The sustained-drift alarm — one-sided CUSUM (the D-11 estimator).** Drift is a
*sustained* excursion. The textbook detector for a persistent shift against a
target, tuned to ignore transient noise, is Page's (1954) cumulative sum. Run two
one-sided accumulators per class against the two band edges, in the exposure's own
units:

$$S^{+}_{j,t} = \max\!\big(0,\; S^{+}_{j,t-1} + (x_{j,t} - U_j) - k_j\big),
\qquad
S^{-}_{j,t} = \max\!\big(0,\; S^{-}_{j,t-1} + (L_j - x_{j,t}) - k_j\big),$$

with $S^{\pm}_{j,0}=0$.

where:
- $S^{+}_{j,t}$ — the upper accumulator: the running tally of excess *above* the
  upper edge, net of the allowance, floored at zero.
- $S^{-}_{j,t}$ — the lower accumulator, symmetric, for excursions *below* the lower
  edge.
- $k_j$ — the **allowance** (`CUSUM_ALLOWANCE_K`), set to a fraction of the pinned
  drift's monthly step. It is the slack that lets honest wander above the edge decay
  back toward zero; a *sustained* walk beyond the edge out-accumulates $k_j$ and
  climbs. (In control-chart language, $k$ is the "reference value," conventionally
  set to about half the shift you want to catch.)
- $\max(0, \cdot)$ — the reflecting floor: the tally never goes negative, so a run
  of quiet months resets the evidence rather than banking negative credit.

The alarm fires the first time $S^{+}_{j,t} > h_j$ or $S^{-}_{j,t} > h_j$.

where:
- $h_j$ — the **decision interval** (`CUSUM_THRESHOLD_H`). This is **not a free
  parameter**: it is chosen by calibration on the null (§3.4 and §6) so the
  per-manager-year false-alarm rate meets `FALSE_ALARM_BUDGET`. Raising $h_j$ lowers
  false alarms but lengthens detection delay; lowering it does the reverse.

In words: two tallies watch the two edges; whichever crosses its calibrated
threshold first declares a sustained drift, and *when* it crosses (the run length
from drift onset) is the detection delay. CUSUM's output is naturally
interval-friendly — it reports not just *whether* but *when*, and the
detection-delay distribution, not a single point, is the honest performance
statement.

**Why this and not rolling-beta inference.** CUSUM operates on the *measured* path
$x_{j,t}$ point-in-time (card doctrine: "drift = exposure change point-in-time, not
rolling-beta inference"). It never fits a time-varying beta from returns — it
accumulates disclosed excursions. All the statistical content lives in separating
*persistent* from *transient*, and that content is resolved against the simulator
null, not asserted.

**Simple sibling (the run-length rung).** For consumers who want a one-line rule, a
**k-of-m** rung fires when the exposure sits outside $[L_j-\delta_j, U_j+\delta_j]$
for `K_CONSEC` of the last `M_WINDOW` observations. `K_CONSEC` is calibrated on the
same null to the same budget. It is strictly weaker than CUSUM (it ignores excursion
*magnitude* — a hair over the edge counts the same as a mile) and is offered as the
plain-language version, with CUSUM as the reported detector.

### 3.4 The honest-wander null and why iid calibration over-fires

This is the load-bearing calibration point: **the null is autocorrelated.** A
rotating book turns over roughly every $1/\text{rebalance\_fraction} \approx 4$
months (the simulator default), so the honest-wander path $x_{j,t}$ under *no*
injected drift is serially correlated — consecutive months are not independent
draws; this month's reading is close to last month's because most of the book is
unchanged.

Why this matters for $h_j$: autocorrelated wander produces **longer natural runs**
above the edge than independent (iid) noise would, because once the path drifts a
little high it tends to *stay* a little high for a few months. A decision interval
$h_j$ calibrated against an iid null — which assumes each month is a fresh
independent coin flip — would therefore be set **too low**, and the detector would
**over-fire** on ordinary rotation. M1 calibrates $h_j$ (and `K_CONSEC`) against the
**simulator-emitted honest-wander distribution itself** — the actual autocorrelated
null — never a closed-form iid average-run-length formula. This is the same
discipline S2's drawdown band and M3's alarm apply: thresholds are set on the
realistic null, not a convenient analytic one. §4 (the mock implementation) makes
the iid-vs-autocorrelated gap concrete with runnable code.

### 3.5 Factor-share-of-variance drift ("accidental factor")

The card's second question — "is the return stream increasingly accidental factor
versus intended alpha?" — is a hygiene metric, not a skill metric. Using the
*measured* factor-beta vector $b_t$ and a factor covariance $\Sigma_f$ (from the
factor returns), the factor-explained share of predicted variance is

$$\text{FS}_t = \frac{b_t^{\top}\Sigma_f\, b_t}{b_t^{\top}\Sigma_f\, b_t + \hat\sigma^2_{\text{idio}}}.$$

where:
- $b_t$ — the measured factor-beta vector at time $t$ (one entry per factor).
- $\Sigma_f$ — the factor return covariance matrix; the disclosed/estimated factor
  covariance. At E it is the public factor set (FF5+MOM equity, Fung–Hsieh
  macro/trend, per S1 §2), so this panel is measurement over measured inputs.
- $b_t^{\top}\Sigma_f\, b_t$ — the variance the factor exposures alone would predict
  (the "systematic" piece).
- $\hat\sigma^2_{\text{idio}}$ — the **estimated** idiosyncratic variance (the
  residual, "paid-for alpha" piece). The hat marks it as an estimate, which is why
  this panel is estimate-bearing, not pure measurement.
- $\text{FS}_t$ — the fraction of predicted variance attributable to factors,
  between 0 and 1.

In words: $\text{FS}_t$ near 0 means the book's disclosed risk is almost all
idiosyncratic (the alpha the client pays for); $\text{FS}_t$ climbing toward 1 means
the risk is migrating toward factor exposure (accidental beta). The trend over the
window (`FACTOR_SHARE_WINDOW`) is tested against the honest-wander null of
$\text{FS}_t$ (the same calibration machinery) and reported as a **slope
IntervalStat with a VerdictChip** — never a bare "factor share up."

### 3.6 Tier degradation (E native → P sharpens → R does not clear)

Identical ground truth, three honesty levels — the campaign thesis at exposure
altitude:

- **E** — measured path → CUSUM alarm + factor-share drift. **Robust** measurement;
  calibrated-rule alarm. TierBadge: *measured (E)*.
- **P** — same alarm, plus **attribution**: the position-level deltas that compose
  the net-beta walk (which names loaded the drift). Sharpens the *why*, not the
  *whether*.
- **R** — a 24-month **rolling-beta** path (Sharpe 1992 returns-based style analysis,
  `RBSA_WINDOW`). Rendered **descriptive only** behind a **noise chip**; the atlas
  (§6 validation plan) measures exactly how much later and how much noisier the R
  path detects the same 0.3 net-beta walk than the E path does. The R rung's job in
  this card is to *demonstrate* the degradation, not to make a call.

### 3.7 What the canonical papers showed, and why they apply here

- **Page (1954), "Continuous Inspection Schemes," *Biometrika*.** Page introduced
  the cumulative-sum procedure and the sequential-detection framing: instead of
  testing each observation against a limit in isolation, accumulate the signed
  departures from a target and raise an alarm when the accumulation crosses a
  boundary. The paper showed this scheme detects a genuine, sustained shift in a
  process mean far faster (for a given false-alarm rate) than any test that looks at
  one observation at a time. That is exactly M1's problem — a sustained shift in a
  disclosed exposure — so the one-sided CUSUM is the direct, appropriate tool.
- **Montgomery, *Introduction to Statistical Quality Control* (CUSUM/EWMA
  chapters).** Montgomery is the standard reference for *designing* a CUSUM in
  practice: how the allowance $k$ and decision interval $h$ trade false-alarm rate
  against detection delay, how performance is quantified by average run length, and —
  the point M1 leans on hardest — why control charts must be calibrated on the
  **in-control (null) distribution** rather than a wished-for analytic one. It
  justifies our insistence on calibrating $h$ against the realistic null.
- **Sharpe (1992), "Asset Allocation: Management Style and Performance
  Measurement," *JPM*.** Sharpe introduced returns-based style analysis: regress a
  manager's returns on a set of style-index returns to *infer* the exposures the
  manager holds. Rolling that regression turns it into a drift proxy. The paper's own
  logic tells us why it is the weak rung here: the inferred exposures carry
  estimation variance that shrinks only slowly with track length, so at 36–60 months
  a real, modest net-beta walk is buried in that variance. This is the R tier —
  present to demonstrate the degradation, not to make a call.
- **Falk & Kosfeld (2006), "The Hidden Costs of Control," *AER*.** They showed
  experimentally that explicit monitoring which reads as *control* can *reduce* the
  monitored party's cooperation — people withdraw effort when they feel policed.
  Applied here: a drift panel delivered as an accusation makes the manager withdraw
  the very exposure disclosure the E rung depends on. This is the empirical basis for
  M1's "worth a conversation, never you-broke-your-mandate" delivery framing (§6
  adoption), shared with M5.

## 4. How to implement

Below is a self-contained, numpy-style reference implementation — the estimator
written from scratch as teaching code. It has no dependency on this project; paste
it into a fresh file and adapt. It implements the **same** formulas as §3: the
one-sided CUSUM of §3.3, the null-calibration sweep of §3.4, and the factor-share
metric of §3.5. Constant *names* match the spec's constants table (§6); the
illustrative numeric values are for teaching only.

```python
"""M1 exposure-drift monitor — reference implementation (teaching code).

Implements the one-sided CUSUM sustained-drift alarm and its null-calibration
sweep from first principles. Pure numpy; no project imports. The values chosen
here are illustrative and uncalibrated -- a live deployment calibrates the
decision interval h on the realistic autocorrelated null (calibrate_h below).
"""

import numpy as np

# --- Provisional constants (names match the spec's constants table) ----------
FALSE_ALARM_BUDGET = 0.05      # target false alarms per manager-year (1-in-20)
CUSUM_ALLOWANCE_K = 0.0125     # allowance k, per class (0.5 x pinned monthly step)
NET_BETA_BAND = (-0.10, 0.10)  # NET_BETA_BAND_DEFAULT: (L, U)
DELTA_BAND = 0.05              # net-beta materiality dead-band, delta_j


def one_sided_cusum(path, lower, upper, k):
    """Run the two one-sided CUSUM accumulators of spec section 3.3.

    S_plus tallies excess above the upper edge; S_minus tallies excess below
    the lower edge; each is floored at zero so a quiet spell resets the
    evidence. Returns both accumulator traces in the exposure's own units.

        S_plus[t]  = max(0, S_plus[t-1]  + (x[t] - upper) - k)
        S_minus[t] = max(0, S_minus[t-1] + (lower - x[t]) - k)
    """
    x = np.asarray(path, dtype=float)
    s_plus = np.zeros_like(x)
    s_minus = np.zeros_like(x)
    for t in range(len(x)):
        prev_plus = s_plus[t - 1] if t > 0 else 0.0
        prev_minus = s_minus[t - 1] if t > 0 else 0.0
        s_plus[t] = max(0.0, prev_plus + (x[t] - upper) - k)
        s_minus[t] = max(0.0, prev_minus + (lower - x[t]) - k)
    return s_plus, s_minus


def cusum_alarm(path, lower, upper, k, h):
    """Fire when either accumulator first crosses the decision interval h.

    Returns (fired, onset_index). onset_index is the first month the alarm
    would trip -- the run length that, measured from the true drift onset,
    is the detection DELAY (spec section 3.2 / 3.3).
    """
    s_plus, s_minus = one_sided_cusum(path, lower, upper, k)
    crossed = np.where((s_plus > h) | (s_minus > h))[0]
    if crossed.size == 0:
        return False, None
    return True, int(crossed[0])


def factor_share(betas, factor_cov, idio_var):
    """Factor-explained share of predicted variance, FS_t (spec section 3.5).

        FS = (b' Sigma_f b) / (b' Sigma_f b + sigma^2_idio)

    Estimate-bearing: idio_var is an estimate, so a live panel ships FS as a
    slope interval + verdict, never a bare 'factor share up'.
    """
    b = np.asarray(betas, dtype=float)
    systematic = float(b @ np.asarray(factor_cov, dtype=float) @ b)
    return systematic / (systematic + float(idio_var))
```

The calibration sweep is the real work — and it is where the autocorrelated-null
point of §3.4 becomes code. We generate many honest-wander paths, and for a grid of
candidate thresholds $h$ we measure the realised false-alarm rate, then pick the
smallest $h$ that meets the budget. Generating the null as an **AR(1)** process
(serially correlated) rather than iid is the whole lesson: run it both ways and the
iid null hands you a smaller $h$ that will over-fire in production.

```python
def honest_wander_paths(n_paths, n_months, phi, sigma, centre, rng):
    """Simulate honest-wander null paths as an AR(1) process (spec section 3.4).

    phi is the month-to-month persistence: phi = 0 is the (wrong) iid null;
    phi ~ 0.75 mimics a book that turns over every ~4 months, so a reading
    that runs high tends to STAY high for a few months -- longer natural runs
    above the edge than iid noise, which is exactly why h must be calibrated
    on the autocorrelated null, not an iid one.
    """
    paths = np.empty((n_paths, n_months))
    for i in range(n_paths):
        x = centre
        for t in range(n_months):
            x = centre + phi * (x - centre) + rng.normal(0.0, sigma)
            paths[i, t] = x
    return paths


def false_alarm_rate(paths, lower, upper, k, h, months_per_year=12):
    """Fraction of manager-YEARS in which the CUSUM raises a (false) alarm.

    On the null there is no drift, so every alarm is false. We normalise by
    the number of manager-years so the rate is comparable to FALSE_ALARM_BUDGET.
    """
    n_paths, n_months = paths.shape
    manager_years = n_paths * n_months / months_per_year
    false_alarms = 0
    for path in paths:
        fired, _ = cusum_alarm(path, lower, upper, k, h)
        if fired:
            false_alarms += 1
    return false_alarms / manager_years


def calibrate_h(paths, lower, upper, k, budget, h_grid):
    """Pick the SMALLEST decision interval h whose false-alarm rate <= budget.

    Smallest-h-that-clears keeps detection delay as short as the budget allows.
    A detector whose size is not pinned this way earns no detection claim.
    Returns None if no h on the grid meets the budget (e.g. the far noisier
    R-tier rolling-beta series -- the refusal is itself the measured verdict).
    """
    for h in sorted(h_grid):
        if false_alarm_rate(paths, lower, upper, k, h) <= budget:
            return h
    return None


if __name__ == "__main__":
    rng = np.random.default_rng(0)
    lower, upper = NET_BETA_BAND
    centre = 0.0
    h_grid = np.linspace(0.02, 2.0, 100)

    # The correct, autocorrelated null vs the wrong iid null.
    auto_null = honest_wander_paths(2000, 60, phi=0.75, sigma=0.05,
                                    centre=centre, rng=rng)
    iid_null = honest_wander_paths(2000, 60, phi=0.0, sigma=0.05,
                                   centre=centre, rng=rng)

    h_auto = calibrate_h(auto_null, lower, upper, CUSUM_ALLOWANCE_K,
                         FALSE_ALARM_BUDGET, h_grid)
    h_iid = calibrate_h(iid_null, lower, upper, CUSUM_ALLOWANCE_K,
                        FALSE_ALARM_BUDGET, h_grid)

    # Expect h_iid < h_auto: the iid null under-sets the threshold and would
    # over-fire on a real, autocorrelated book.
    print(f"h calibrated on autocorrelated null: {h_auto:.3f}")
    print(f"h calibrated on iid null (too low):  {h_iid:.3f}")
```

The two blocks together are the whole estimator: a deterministic detector (pure
functions over a path and a band) and a stochastic calibration harness that sets the
one threshold the detector cannot pick for itself. Detection power and delay against
a true-drift alternative are measured by running `cusum_alarm` at the calibrated
`h_auto` over drift paths and recording the onset index — the delay.

## 5. Reading the demo

The gallery page shows **one synthetic manager** — "Harrowgate Neutral," an equity
market-neutral book with a stated net-beta band of $[-0.10, +0.10]$, observed for 60
months — whose **measured** net beta walks from about 0.10 to 0.45 over the window
(`DEMO_DRIFT_WALK`, deliberately larger than the pinned 0.30 for visual clarity).
Every number on the page comes from the committed `site/data/m1_drift.json`; the
demo generator imports the *same* detector code the live monitor would run, so demo
numbers and live numbers share one code path.

How each visual element maps to the method:

- **The exposure path (accent line)** is the measured net beta $x_t$ — exact,
  Robust, disclosed, not inferred.
- **The dashed horizontal band** is the stated $[L, U] = [-0.10, +0.10]$ mandate
  band from §3.1.
- **The shaded envelope behind the path** is the honest-wander null band (5th–95th
  percentile) from the autocorrelated null of §3.4 — the range a *non-drifting* book
  of this type occupies. The measured path leaving that envelope and staying out is
  the visual signature of drift.
- **The alarm marker** is where the one-sided CUSUM crosses its calibrated
  threshold: in the committed data the drift onset is month 12 and the alarm fires at
  **month 18** — a six-month detection delay, shown honestly rather than pretended
  away.
- **The TierBadge "E · measured"** marks the whole panel as measurement, not
  inference — the load-bearing distinction of this card.
- **The R-tier chart** is the 24-month rolling-beta inference (Sharpe 1992), rendered
  greyed behind a **noise chip** reading "no drift verdict at this track length." It
  is present only to make the degradation visible.
- **The two detection IntervalStats** report, with Wilson 95% intervals: E detection
  **100%** (CI 98.7%–100%, median delay 7 months) versus R detection **0%** (CI
  0%–1.3%). Same ground truth, two honesty levels.
- **The factor-share IntervalStat** reports the slope of $\text{FS}_t$ as
  $+0.0065$/month (95% interval $+0.0049 \ldots +0.0080$) with a "rising factor
  share" verdict — the accidental-factor drift, shipped as a slope interval because
  it is estimate-bearing (§3.5).
- **The power gate** states the calibration: the alarm was calibrated on 300
  honest-wander paths to a 0.05/manager-year false-alarm budget (achieved 0.047), and
  detection of the pinned 0.30 walk is 100% by $T=48$ — above the 0.50 floor — so the
  alarm renders and the R rung does not.

**What an allocator should conclude from these numbers.** At the exposure tier, a
0.30 net-beta walk over twelve months is caught essentially every time, within a
handful of months, at a controlled one-in-twenty-per-year false-alarm cost. Trying
to catch the *same* walk from returns via rolling beta catches it *zero* times at 48
months. The contrast is the entire tier-degradation thesis in one panel: **measure
the exposure; do not infer it.**

## 6. Honest limits & go-live

### 6.1 Data contract per tier

The card *is* the tier axis for drift: measurement is native at E, sharpens at P,
and degrades to inference-that-does-not-clear at R.

| Tier | Inputs the live version needs | What the card produces |
| --- | --- | --- |
| **E** (native) | Risk-report exposure summaries — per period, per manager: net & gross exposure, factor betas, sector/region weights, duration buckets — Open-Protocol-aligned; **plus the stated bands** (from mandate/letters), one band spec per exposure class. | The whole monitor: instantaneous band-breach flags (measurement) **and** the calibrated **sustained-drift alarm** (§3.3), plus the **factor-share-of-variance** drift panel (§3.5). This is the Robust rung. |
| **P** | E + position/holdings files. | **Attribution of the drift**: which names / sub-sleeves drove the net-beta walk (the sustained breach decomposed to position deltas). Sharpens the *why*, not the *whether*. |
| **R** (fallback) | Monthly returns + a factor set only. | A 24-month **rolling-beta** path (RBSA, Sharpe 1992), rendered **descriptive-only** behind a **noise chip**: "returns-inferred, not measured — no drift verdict at this track length." Present for the tier-degradation contrast, never as a claim. |

**Frequency & alignment.** Exposures at each manager's native cadence (monthly or
quarterly E; quarterly-or-better P); the stated band is a step function keyed to
mandate/letter dates (a band can be re-negotiated — a band *change* is not a
breach). All exposure classes carry the units they are stated in: net/gross in
exposure units, factor betas in beta units, sector/region in weight ppt, duration in
years.

**Compliance (standing).** Any real exposure feed committed to the public repo uses
public disclosures of unaffiliated managers only; the demo runs entirely on
simulator emissions. No employer-internal risk-report content, ever.

### 6.2 Power & validation plan

M1 contributes the **exposure-drift-detector rows** to the X1 atlas
([`x1-tier-power-atlas.md`](x1-tier-power-atlas.md) §3.2 metric row; §3.4 pinned
effect **"a 0.3 net-beta walk over 12 months"**; §4 size discipline). The card's
demo consumes those rows; the calibration below *produces* them.

**Two ground-truth worlds.**

1. **Null (honest wander).** The simulator today pins `target_gross`/`target_net`
   exactly every month (`simulator/manager.py`); the net-beta path still wanders as
   names rotate, with **no injected trend**. Running the honest-wander manager across
   seeds gives the autocorrelated null directly — no dial needed for the size
   measurement.
2. **Alternative (true drift).** A **net-beta drift dial** — a small simulator
   extension: a linear (or logistic) schedule on `target_net` that walks the book by
   the pinned `PINNED_DRIFT_EFFECT` over 12 months. This is the one deferred substrate
   M1 needs (analogous to M2's short-vol dial and S4's exit-lag dial); the null and
   the whole demo stand without it, but the *detection* numbers require it.

**Calibration then measurement (order matters — X1 §4).**

1. **Size first.** On the honest-wander null, choose $h_j$ / `K_CONSEC` so the
   per-manager-year false-alarm rate meets `FALSE_ALARM_BUDGET` (target 1-in-20). A
   detector whose size is not pinned earns no detection claim (X1 §4.2).
2. **Detection & delay.** With $h_j$ fixed, on the drift-dial alternative, measure
   P(alarm within horizon) **and** the **detection-delay** distribution (median
   months from drift onset to alarm) at each $T \in \{24,36,48,60,120\}$ (X1 §3.1
   grid), at tiers E and R.
3. **Tier-degradation delta.** Detection/delay at **E (measured)** minus at **R
   (rolling-beta)** at identical ground truth — the atlas's degradation number for
   this metric. Expectation: E clears at the pinned effect; R lags badly or never
   clears (the do-not-build verdict, *measured*).
4. **Reporting.** Every power/size number ships with a **Wilson 95% interval**
   (≥1,000 seeded paths per cell, X1 §3.3); no bare rate.

**Kill / demote criterion (converge-or-cut).** If the E-tier CUSUM cannot separate
the 0.3/12-month walk from honest wander at a usable operating point (target:
detection ≥ 0.5 with size ≤ `FALSE_ALARM_BUDGET` by $T=48$) after the
allowance/window are tuned, the sustained-drift rung is **demoted to the
instantaneous measured-breach flag only** (§3.3, pure measurement, no persistence
claim) and the finding recorded in writing — never an uncalibrated alarm sold as a
drift verdict.

### 6.3 Implementation architecture (the live system)

Module home: **`quant_allocator/flagships/drift/`**

- `bands.py` — the stated-band schema (per class $[L_j,U_j]$, keyed to mandate/letter
  dates) and the `DELTA_BAND` materiality table, declared in one place so a reviewer
  sees every dead-band at once (the M5 §3.2 pattern).
- `detector.py` — **deterministic**, pure functions over an exposure DataFrame + a
  band spec: `breach_flags(...)`, `cusum_alarm(path, band, k, h) ->
  DriftAlarm(fired, onset, run_length, delay)`, `run_length_rung(...)`,
  `factor_share_drift(betas, factor_cov, idio_var)`. No I/O, no simulator import.
- `calibrate.py` — the null-calibration harness: draws honest-wander paths from the
  simulator, sweeps $h_j$/`K_CONSEC` to hit `FALSE_ALARM_BUDGET`, and emits the
  calibrated thresholds. Its outputs are the atlas's D-11 rows and the PowerGate-
  registry entries the gallery/pack consume — **nothing downstream hand-copies a
  threshold** (X1 §6 doctrine).
- Hosts inside the **S2 tear sheet** as the *drift panel* (card: "the tear-sheet (S2)
  hosts the panel") — the exposure path with its band, the CUSUM trace, the
  factor-share strip, a TierBadge, and a PowerGate.

**Demo path (wave-2, honest mockup).** The demo generator
`src/quant_allocator/demo_data/m1_drift.py` **imports `detector.py`** — demo numbers
and live numbers come from the *same code path*, only the input differs (simulator
emission vs real risk report), the S2 §5 load-bearing commitment. The demo shows the
"beta-neutral" manager described in §5; the CUSUM lights up at the sustained-breach
onset with the honest-wander null band behind the path; a **TierBadge** marks this
*measured (E)*, not inferred; and the **R-tier rolling-beta version is rendered
greyed with a noise chip** to make the degradation visible. Working PowerGate and the
"what this needs to go live" box per the honest-mockup contract. **CI renders only** —
the committed `site/data/m1_drift.json` is generated locally and gated; CI never
computes.

**Dependencies.** simulator (exposure emissions ready, `simulator/tiers.py`); the
**net-beta drift dial** (deferred substrate, small) for the detection/alternative
numbers; **numpy only** (CUSUM and the run-length rung are trivial to implement; no
scipy, no PyMC). Effort: **S–M** — the detector is small and testable; the
null-calibration harness is the real work.

**Sequencing.** After S2 (which hosts the panel); simulator sufficient for the null
and the demo; the drift dial unlocks the detection rows. Consumes the X1 grid; its
calibrated thresholds feed the PowerGate registry.

### 6.4 Adoption & packaging

The output is **engagement material**, and the framing is a functional requirement
(Sweep E), not decoration:

- **"Worth a conversation," never "you broke your mandate."** Falk & Kosfeld:
  monitoring that reads as policing makes the manager withdraw the very exposure
  disclosure the E rung runs on. A band-breach headline is delivered as *"the
  measured net beta has walked to 0.45 against a stated ±0.10 — worth understanding
  why,"* with the band, the path, and the onset date shown — the reader draws the
  conclusion.
- **Measured, not accused.** The TierBadge is load-bearing: an E-tier breach is a
  *measurement*, so the conversation is about the number, not about trust. The
  R-tier noise chip is equally load-bearing — it stops the team from acting on a
  returns-inferred "drift" that the data cannot actually support at this track
  length.
- **Never a mechanical trigger.** The alarm is a review input and a watchlist entry,
  never an automatic redemption. Goodhart: a published "drift score" target gets
  gamed (managers disclose coarser buckets); the value is the sourced conversation,
  so it ships as conversation material.

**Who sees what, when.** Internal team gets the full path + alarm + attribution at
quarterly-review prep; any manager-facing version ships only inside the **E1
transparency-ladder** relationship — and the *reciprocity* is real: the drift panel
handed back is a genuine hygiene service, the E-tier rung of the ladder.
**Kill-the-dashboard doctrine:** this is a *panel inside the S2 pack rendered at the
decision moment*, not a standalone always-on dashboard — no new app.

### 6.5 Go-live requirements

- **Data ask:** exposure summaries at the **E** tier (net/gross, factor betas,
  sector/duration buckets), Open-Protocol-aligned, **plus the stated bands** from the
  mandate/letters — the band is as much a required input as the exposure. **+
  positions (P)** for drift attribution. The **R** rolling-beta rung needs only
  returns + a factor set and renders descriptive-only.
- **Sample required:** not a per-window small-N gate — the *measurement* is exact at
  any $T$. The gate is on the **alarm's operating characteristics**: the calibrated
  false-alarm and detection/delay curves come from the atlas (§6.2), and the panel
  renders the alarm only where the registry says the detector clears at the manager's
  cadence and horizon.
- **Data-quality caveat (real world):** E-tier feeds vary in quality and granularity;
  **Open Protocol alignment is the standardisation ask, pursued via the E1 ladder.** A
  feed too coarse to place the exposure against its band renders the *measured-breach
  flag* only, with the sustained-drift alarm gated off and the reason stated.
- **Build effort:** **S–M**, including the null-calibration harness and the small
  net-beta-drift simulator dial.
- **Kill criterion:** detection < 0.5 at the budgeted false-alarm rate by $T=48$ ⇒
  demote to the measured-breach flag only, recorded in writing (§6.2).

### 6.6 Provisional constants (flagged for the numerics gate)

Every value below is a named constant at module top; the numerics gate flips one and
the calibration/demo regenerates deterministically.

| Constant | Provisional value | Role |
| --- | --- | --- |
| `FALSE_ALARM_BUDGET` | 0.05 / manager-year (1-in-20) | Size target the CUSUM $h$ is calibrated to |
| `PINNED_DRIFT_EFFECT` | 0.30 net-beta walk over 12 months | Effect the detector is powered against (X1 §3.4) |
| `NET_BETA_BAND_DEFAULT` | $[-0.10, +0.10]$ | Band assumed when a mandate leaves net beta unstated (marked *assumed*) |
| `DELTA_BAND` | net beta 0.05 · gross 0.15 · factor beta 0.10 · sector 3 ppt · duration 0.25 y | Per-class materiality dead-band $\delta_j$ |
| `CUSUM_ALLOWANCE_K` | 0.5 × pinned monthly drift step (per class) | CUSUM allowance $k_j$ |
| `CUSUM_THRESHOLD_H` | *calibrated on null* (not free) | Decision interval $h_j$; output of §6.2, not a dial |
| `K_CONSEC` / `M_WINDOW` | 3 of 4 | Run-length simple rung (calibrated to same budget) |
| `FACTOR_SHARE_WINDOW` | 12 months | Window for the factor-share trend test |
| `DEMO_DRIFT_WALK` | 0.10 → 0.45 (0.35) | Demo path; larger than the pinned 0.30 for visual clarity |
| `RBSA_WINDOW` | 24 months | R-tier rolling-beta window (descriptive-only) |

## 7. Deeper reading

### 7.1 Canonical references (3–4 to own)

1. **Page, E. S. (1954), "Continuous Inspection Schemes," *Biometrika*** — the CUSUM
   procedure and the sequential-detection framing the alarm is built on. Page showed
   that accumulating signed departures from a target and alarming on the accumulation
   detects a sustained mean shift far faster, for a given false-alarm rate, than any
   test on one observation at a time — precisely M1's problem.
2. **Montgomery, *Introduction to Statistical Quality Control* (CUSUM/EWMA
   chapters)** — average-run-length design, allowance/decision-interval tuning, and
   why control charts calibrate on the in-control (null) distribution rather than a
   convenient analytic one. This is the reference behind M1's insistence on
   calibrating $h$ on the realistic null.
3. **Sharpe, W. (1992), "Asset Allocation: Management Style and Performance
   Measurement," *JPM*** — returns-based style analysis, the R-tier fallback. Its own
   estimation-variance logic is why a rolling version cannot separate a modest
   net-beta walk from noise at 36–60 months; that is the R rung's whole role here.
4. **Falk & Kosfeld (2006), "The Hidden Costs of Control," *AER*** — the
   withdrawal-under-monitoring result the "worth a conversation" framing defends
   against (shared with M5): monitoring that reads as control reduces the very
   cooperation the E rung depends on.

*(Standardisation context: the Open Protocol Enabling Technology / AIMA
exposure-reporting template is the E-tier data standard the go-live ask names.)*

### 7.2 Questions you should be able to answer after reading this page

*The spec program doubles as a curriculum; these are what to be able to defend
unaided.* Supporting notes on each follow.

- **Explain to a non-quant why a single month over the band is not drift, but four
  accumulating months are** — the CUSUM allowance and decision interval in one
  sentence each. (The allowance $k$ is the permitted honest overshoot that a
  one-month blip decays back below; the decision interval $h$ is the
  accumulated-evidence threshold a *sustained* run must cross to declare drift.)
- **State why the false-alarm rate must be calibrated on an autocorrelated null, and
  what happens if you use iid.** Calibrating a run-based or CUSUM detector on an iid
  null under-sets the threshold when the real process is serially correlated, because
  autocorrelation lengthens natural runs. A rotating book's turnover timescale
  ($\approx 1/\text{rebalance\_fraction}$) *is* that correlation. Use iid and you
  over-fire — and the manager stops disclosing. Quote the false-alarm rate you
  actually get, not the iid one you wish you had.
- **Explain what the E rung claims that the R rung cannot.** E *measures* the
  exposure and detects a 0.3 net-beta walk on time; R *infers* it from returns and,
  at 48 months, cannot tell the walk from noise — same ground truth, two honesty
  levels, the whole thesis in one panel. Own *why* R fails: the estimation variance
  of a rolling multivariate regression at short $T$ buries the walk. That is what
  justifies putting the R rung behind a noise chip rather than deleting it — the
  contrast *is* the tier-degradation argument.
- **Say why measurement is not the same as drift-detection.** The exposure *value* is
  measured exactly (Robust). The claim "this is drift, not wander" is an *inference
  about persistence*, and its honesty lives entirely in the null. This is the
  distinction that lets M1 sit next to the do-not-build list without violating it:
  measurement at E/P is allowed and Robust; the persistence classification is a
  **calibrated rule** (like M3's drawdown alarm), not a returns-based beta *estimate*
  (the Noise-verdicted, do-not-build path).
- **Own CUSUM's performance currency, average run length (ARL), by hand.**
  $\text{ARL}_0$ is the mean months to a *false* alarm (you want it large);
  $\text{ARL}_1$ is the mean months to detect a *real* shift (you want it small). Be
  able to say why a single threshold on the raw level (the instantaneous flag) is
  strictly dominated by CUSUM for a *sustained* shift: the level test discards the
  accumulating evidence a run of excursions carries.

---

## Method review (2026-07-07) — APPROVED, implementation-ready

- **Drift-dial form RULED:** a schedule on `target_net` (linear walk), NOT a
  candidate-selection tilt — the tilt confounds effect size with selection dynamics;
  the tilt variant is deferred to atlas vol. 1 as a robustness axis.
- **Verdict split CONFIRMED:** measurement is Robust; the sustained-drift alarm is a
  calibrated rule (M3's framing) — the card's blanket "Robust" is refined accordingly.
- **§3.5 note:** the factor-share panel is estimate-bearing (sigma-hat idio) — its
  slope IntervalStat treatment is the correct rendering; do not describe FS as pure
  measurement in page copy.
- CUSUM `k`/`h`, `FALSE_ALARM_BUDGET`, `DELTA_BAND`, `K_CONSEC` remain numerics-gate
  docket items at build time, calibrated on the autocorrelated null as specified.
