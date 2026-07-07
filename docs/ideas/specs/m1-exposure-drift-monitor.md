# M1 · Exposure Hygiene & Drift Monitor — Method Spec

**Date:** 2026-07-07
**Status:** Draft — pending method review
**Card:** [`2026-07-05-idea-cards.md` → "M1 · Exposure hygiene & drift monitor"](../2026-07-05-idea-cards.md)
**Demo page:** wave-2 gallery page `m1.html` (planned; monitoring batch, weeks 3–4)
**Fulfils:** X1 atlas docket **D-11** — the exposure-drift detector deferred out
of `x1-tier-power-atlas.md` §3.2 into this card's lane. §3–§4 below define that
detector and its calibration.

---

## 1. Problem & decision hook

A mandate states bands — "beta-neutral stock picking," "gross ≤ 2.0×,"
"duration inside ±1 year" — and the risk report discloses the exposures that
either respect them or do not. The quarterly question the team asks by hand is
narrow and answerable: **does the book still sit inside its stated bands, and is
the return stream becoming "accidental factor" rather than intended alpha?**
M1 reads the *measured* exposure path against the *stated* band and flags
**sustained drift** — a band excursion that persists — distinct from the
month-to-month **honest wander** every rotating book exhibits. Sweep B calls
this the single most transplantable platform analytic at the exposure tier.

- **Decisions improved:** **monitor** (drift leads the return series — a book
  quietly loading net beta is a risk-report event before it is a performance
  event) and **engage** (the quarterly-review centrepiece: a specific, measured,
  sourced change to discuss, not a generic template).
- **Customer:** investment team on the quarterly cycle; engagement conversations.
- **What it is not.** Not a returns-based style-drift *estimator*. Returns-based
  rolling-beta drift inference at 36–60 months is on the program's **do-not-build
  list** (convergence §4: "returns-based style-drift *inference* — measurement at
  E/P instead") and Sweep C verdicts it **Noise**. M1 is the *measurement-at-E/P*
  answer to exactly that: it reads the disclosed exposure path directly and never
  regresses a time-varying beta out of returns to manufacture a drift claim. The
  R-tier rolling-beta view exists only as a **labelled descriptive fallback**
  (§3.6), carrying a noise chip, never a verdict. It is also not a redemption
  trigger — a breach is an invitation to explain, never a rule that fires capital.

## 2. Data contract per tier

The card *is* the tier axis for drift: measurement is native at E, sharpens at
P, and degrades to inference-that-does-not-clear at R.

| Tier | Inputs the live version needs | What the card produces |
| --- | --- | --- |
| **E** (native) | Risk-report exposure summaries — per period, per manager: net & gross exposure, factor betas, sector/region weights, duration buckets — Open-Protocol-aligned; **plus the stated bands** (from mandate/letters), one band spec per exposure class. | The whole monitor: instantaneous band-breach flags (measurement) **and** the calibrated **sustained-drift alarm** (§3.3), plus the **factor-share-of-variance** drift panel (§3.5). This is the Robust rung. |
| **P** | E + position/holdings files. | **Attribution of the drift**: which names / sub-sleeves drove the net-beta walk (the sustained breach decomposed to position deltas). Sharpens the *why*, not the *whether*. |
| **R** (fallback) | Monthly returns + a factor set only. | A 24-month **rolling-beta** path (RBSA, Sharpe 1992), rendered **descriptive-only** behind a **noise chip**: "returns-inferred, not measured — no drift verdict at this track length." Present for the tier-degradation contrast, never as a claim. |

**Frequency & alignment.** Exposures at each manager's native cadence (monthly
or quarterly E; quarterly-or-better P); the stated band is a step function keyed
to mandate/letter dates (a band can be re-negotiated — a band *change* is not a
breach). All exposure classes carry the same units they are stated in: net/gross
in exposure units, factor betas in beta units, sector/region in weight ppt,
duration in years.

**Compliance (standing).** Any real exposure feed committed to the public repo
uses public disclosures of unaffiliated managers only; the demo runs entirely on
simulator emissions. No employer-internal risk-report content, ever.

## 3. Methodology

The division of labour is: **the measurement is exact; the inference is the
persistence classification, and that is what gets calibrated.** Everything in
§3.1–§3.2 is measurement (Robust by construction). §3.3–§3.5 is the
calibrated-rule layer that separates *drift* from *wander* — the D-11 deliverable.

### 3.1 Stated bands and the measured exposure path

For each monitored exposure class $j$ (net beta, gross, factor beta, sector
weight, …) the mandate supplies a band $[L_j, U_j]$ with centre
$c_j = (L_j+U_j)/2$ and half-width $w_j = (U_j-L_j)/2$. The risk report supplies
the realised path $x_{j,t}$. **No estimation happens here** — $x_{j,t}$ is
disclosed, not inferred. When a mandate leaves a class's band unstated, the
monitor uses a declared default (`NET_BETA_BAND_DEFAULT`, §"constants") and marks
the band *assumed*, so a reader never mistakes a default for a stated limit.

### 3.2 Instantaneous band-breach flag (pure measurement — Robust)

$\text{breach}_{j,t} = \mathbb{1}\{x_{j,t} < L_j - \delta_j \ \lor\ x_{j,t} > U_j + \delta_j\}$,
where $\delta_j$ is a per-class **materiality dead-band** (`DELTA_BAND`) — the
move below which an excursion is disclosure noise, not a statement. This flag is
exact and always honest; it is also **trigger-happy** — an autocorrelated book
poking a hair over $U_j$ for one month is not drifting. That is precisely why the
instantaneous flag is *not* the alarm; it is the raw material the persistence
layer consumes.

### 3.3 Sustained-drift alarm — one-sided CUSUM (the D-11 estimator)

Drift is a **sustained** excursion. The textbook detector for a persistent shift
against a target, tuned to ignore transient noise, is Page's (1954) **cumulative
sum (CUSUM)**. Run two one-sided accumulators per class against the band edges,
in the exposure's own units:

$$S^{+}_{j,t} = \max\!\big(0,\; S^{+}_{j,t-1} + (x_{j,t} - U_j) - k_j\big),
\qquad
S^{-}_{j,t} = \max\!\big(0,\; S^{-}_{j,t-1} + (L_j - x_{j,t}) - k_j\big),$$

with $S^{\pm}_{j,0}=0$. The **allowance** $k_j$ (`CUSUM_ALLOWANCE_K`, set to a
fraction of the pinned drift's monthly step) is the slack that lets honest wander
above the edge decay back toward zero; a *sustained* walk beyond the edge
out-accumulates $k_j$ and climbs. The alarm fires when
$S^{+}_{j,t} > h_j$ or $S^{-}_{j,t} > h_j$, where the **decision interval**
$h_j$ (`CUSUM_THRESHOLD_H`) is **not a free parameter** — it is *chosen by
calibration on the null* (§4) so the per-manager-year false-alarm rate meets
`FALSE_ALARM_BUDGET`. CUSUM's output is naturally an interval-friendly object:
it reports not just *whether* but *when* (the run length to alarm) and the
**detection delay** distribution is the honest performance statement, not a
single point.

**Why this and not rolling-beta inference.** CUSUM operates on the *measured*
path $x_{j,t}$ point-in-time (card doctrine: "drift = exposure change
point-in-time, not rolling-beta inference"). It never fits a time-varying beta
from returns — it accumulates disclosed excursions. The statistical content is
entirely in separating *persistent* from *transient*, and that content is
resolved against the simulator null, not asserted.

**Simple sibling (run-length rung).** For consumers who want a one-line rule, a
**k-of-m** rung fires when the exposure sits outside $[L_j-\delta_j, U_j+\delta_j]$
for `K_CONSEC` of the last `M_WINDOW` observations. `K_CONSEC` is calibrated on
the same null to the same budget. It is strictly weaker than CUSUM (it ignores
excursion *magnitude*) and is offered as the plain-language version, with CUSUM
as the reported detector.

### 3.4 The honest-wander null and why iid calibration over-fires

The load-bearing calibration point: **the null is autocorrelated.** A rotating
book turns over roughly every $1/\text{rebalance\_fraction} \approx 4$ months
(simulator default), so the honest-wander path $x_{j,t}$ under *no* injected
drift is serially correlated — consecutive months are not independent draws. A
CUSUM threshold $h_j$ calibrated against an iid null would badly **under-set**
$h_j$ and over-fire, because autocorrelated wander produces longer natural runs
above the edge than iid noise would. M1 therefore calibrates $h_j$ (and
`K_CONSEC`) against the **simulator-emitted honest-wander distribution itself**
(§4) — the actual autocorrelated null — never a closed-form iid ARL. This is the
same discipline S2's drawdown band and M3's alarm apply: thresholds are set on
the realistic null, not a convenient analytic one.

### 3.5 Factor-share-of-variance drift ("accidental factor")

The card's second question — "is the return stream increasingly accidental
factor vs intended alpha?" — is a hygiene metric, not a skill metric. Using the
*measured* factor-beta vector $b_t$ and a factor covariance $\Sigma_f$ (from the
factor returns), the factor-explained share of predicted variance is

$$\text{FS}_t = \frac{b_t^{\top}\Sigma_f\, b_t}{b_t^{\top}\Sigma_f\, b_t + \hat\sigma^2_{\text{idio}}}.$$

A rising $\text{FS}_t$ over the window (`FACTOR_SHARE_WINDOW`) means the book's
disclosed risk is migrating from idiosyncratic (paid-for alpha) toward factor
(accidental beta). Trend is tested against the honest-wander null of $\text{FS}_t$
(same calibration machinery), reported as a slope IntervalStat with a VerdictChip
— never a bare "factor share up." $\Sigma_f$ is the disclosed/estimated factor
covariance; at E it is the public factor set (FF5+MOM equity, Fung–Hsieh
macro/trend, per S1 §2), so this panel is measurement over measured inputs.

### 3.6 Tier degradation (E native → P sharpens → R does not clear)

Identical ground truth, three honesty levels — the campaign thesis at exposure
altitude:

- **E** — measured path → CUSUM alarm + factor-share drift. **Robust**
  measurement; calibrated-rule alarm. TierBadge: *measured (E)*.
- **P** — same alarm, plus **attribution**: the position-level deltas that
  compose the net-beta walk (which names loaded the drift). Sharpens *why*.
- **R** — 24-month rolling-beta path (Sharpe 1992 RBSA). Rendered **descriptive
  only** behind a **noise chip**; the atlas (§4) measures exactly how much later
  and how much noisier the R path detects the same 0.3 net-beta walk than the E
  path does. The R rung's job in this card is to *demonstrate* the degradation,
  not to make a call.

## 4. Power & validation plan

M1 contributes the **exposure-drift-detector rows** to the X1 atlas
([`x1-tier-power-atlas.md`](x1-tier-power-atlas.md) §3.2 metric row; §3.4 pinned
effect **"a 0.3 net-beta walk over 12 months"**; §4 size discipline). The card's
demo consumes those rows; the calibration below *produces* them.

**Two ground-truth worlds.**

1. **Null (honest wander).** The simulator today pins `target_gross`/`target_net`
   exactly every month (`simulator/manager.py`); the net-beta path still wanders
   as names rotate, with **no injected trend**. Running the honest-wander manager
   across seeds gives the autocorrelated null directly — no dial needed for the
   size measurement.
2. **Alternative (true drift).** A **net-beta drift dial** — a small simulator
   extension: a linear (or logistic) schedule on `target_net` (or a systematic
   tilt in candidate selection) that walks the book by the pinned
   `PINNED_DRIFT_EFFECT` over 12 months. This is the one deferred substrate M1
   needs (analogous to M2's short-vol dial and S4's exit-lag dial); the null and
   the whole demo stand without it, but the *detection* numbers require it.

**Calibration then measurement (order matters — X1 §4).**

1. **Size first.** On the honest-wander null, choose $h_j$ / `K_CONSEC` so the
   per-manager-year false-alarm rate meets `FALSE_ALARM_BUDGET` (target 1-in-20).
   A detector whose size is not pinned earns no detection claim (X1 §4.2).
2. **Detection & delay.** With $h_j$ fixed, on the drift-dial alternative,
   measure P(alarm within horizon) **and** the **detection-delay** distribution
   (median months from drift onset to alarm) at each $T \in \{24,36,48,60,120\}$
   (X1 §3.1 grid), at tiers E and R.
3. **Tier-degradation delta.** Detection/delay at **E (measured)** minus at
   **R (rolling-beta)** at identical ground truth — the atlas's degradation
   number for this metric. Expectation: E clears at the pinned effect; R lags
   badly or never clears (the do-not-build verdict, *measured*).
4. **Reporting.** Every power/size number ships with a **Wilson 95% interval**
   (≥1,000 seeded paths per cell, X1 §3.3); no bare rate.

**Kill / demote criterion (converge-or-cut).** If the E-tier CUSUM cannot
separate the 0.3/12-month walk from honest wander at a usable operating point
(target: detection ≥ 0.5 with size ≤ `FALSE_ALARM_BUDGET` by $T=48$) after the
allowance/window are tuned, the sustained-drift rung is **demoted to the
instantaneous measured-breach flag only** (§3.2, pure measurement, no persistence
claim) and the finding recorded in writing — never an uncalibrated alarm sold as
a drift verdict.

## 5. Implementation architecture

Module home: **`quant_allocator/flagships/drift/`**

- `bands.py` — the stated-band schema (per class $[L_j,U_j]$, keyed to
  mandate/letter dates) and the `DELTA_BAND` materiality table, declared in one
  place so a reviewer sees every dead-band at once (the M5 §3.2 pattern).
- `detector.py` — **deterministic**, pure functions over an exposure DataFrame +
  a band spec: `breach_flags(...)`, `cusum_alarm(path, band, k, h) ->
  DriftAlarm(fired, onset, run_length, delay)`, `run_length_rung(...)`,
  `factor_share_drift(betas, factor_cov, idio_var)`. No I/O, no simulator import.
- `calibrate.py` — the null-calibration harness: draws honest-wander paths from
  the simulator, sweeps $h_j$/`K_CONSEC` to hit `FALSE_ALARM_BUDGET`, and emits
  the calibrated thresholds. Its outputs are the atlas's D-11 rows and the
  PowerGate-registry entries the gallery/pack consume — **nothing downstream
  hand-copies a threshold** (X1 §6 doctrine).
- Hosts inside the **S2 tear sheet** as the *drift panel* (card: "the tear-sheet
  (S2) hosts the panel") — the exposure path with its band, the CUSUM trace, the
  factor-share strip, a TierBadge, and a PowerGate.

**Demo path (wave-2, honest mockup).** The demo generator
`src/quant_allocator/demo_data/m1_drift.py` **imports `detector.py`** — demo
numbers and live numbers come from the *same code path*, only the input differs
(simulator emission vs real risk report), the S2 §5 load-bearing commitment. The
demo shows a "beta-neutral" manager (stated net-beta band $[-0.10, +0.10]$) whose
**measured** net-beta path walks `DEMO_DRIFT_WALK` (0.10 → 0.45) over the window;
the CUSUM lights up at the sustained-breach onset with the honest-wander null band
behind the path; a **TierBadge** marks this *measured (E)*, not inferred; and the
**R-tier rolling-beta version is rendered greyed with a noise chip** to make the
degradation visible. Working PowerGate and the "what this needs to go live" box
per the honest-mockup contract. **CI renders only** — the committed
`site/data/m1_drift.json` is generated locally and gated; CI never computes.

**Dependencies.** simulator (exposure emissions ready, `simulator/tiers.py`); the
**net-beta drift dial** (deferred substrate, small) for the detection/alternative
numbers; **numpy only** (CUSUM and the run-length rung are trivial to implement;
no scipy, no PyMC). Effort: **S–M** — the detector is small and testable; the
null-calibration harness is the real work.

**Sequencing.** After S2 (which hosts the panel); simulator sufficient for the
null and the demo; the drift dial unlocks the detection rows. Consumes the X1
grid; its calibrated thresholds feed the PowerGate registry.

## 6. Adoption & packaging

The output is **engagement material**, and the framing is a functional
requirement (Sweep E), not decoration:

- **"Worth a conversation," never "you broke your mandate."** Falk & Kosfeld:
  monitoring that reads as policing makes the manager withdraw the very
  exposure disclosure the E rung runs on. A band-breach headline is delivered as
  *"the measured net beta has walked to 0.45 against a stated ±0.10 — worth
  understanding why,"* with the band, the path, and the onset date shown — the
  reader draws the conclusion.
- **Measured, not accused.** The TierBadge is load-bearing: an E-tier breach is
  a *measurement*, so the conversation is about the number, not about trust. The
  R-tier noise chip is equally load-bearing — it stops the team from acting on a
  returns-inferred "drift" that the data cannot actually support at this track
  length.
- **Never a mechanical trigger.** The alarm is a review input and a watchlist
  entry, never an automatic redemption. Goodhart: a published "drift score"
  target gets gamed (managers disclose coarser buckets); the value is the
  sourced conversation, so it ships as conversation material.

**Who sees what, when.** Internal team gets the full path + alarm + attribution
at quarterly-review prep; any manager-facing version ships only inside the **E1
transparency-ladder** relationship — and the *reciprocity* is real: the drift
panel handed back is a genuine hygiene service, the E-tier rung of the ladder.
**Kill-the-dashboard doctrine:** this is a *panel inside the S2 pack rendered at
the decision moment*, not a standalone always-on dashboard — no new app.

## 7. Go-live requirements

- **Data ask:** exposure summaries at the **E** tier (net/gross, factor betas,
  sector/duration buckets), Open-Protocol-aligned, **plus the stated bands** from
  the mandate/letters — the band is as much a required input as the exposure.
  **+ positions (P)** for drift attribution. The **R** rolling-beta rung needs
  only returns + a factor set and renders descriptive-only.
- **Sample required:** not a per-window small-N gate — the *measurement* is exact
  at any $T$. The gate is on the **alarm's operating characteristics**: the
  calibrated false-alarm and detection/delay curves come from the atlas (§4), and
  the panel renders the alarm only where the registry says the detector clears at
  the manager's cadence and horizon.
- **Data-quality caveat (real world):** E-tier feeds vary in quality and
  granularity; **Open Protocol alignment is the standardisation ask, pursued via
  the E1 ladder.** A feed too coarse to place the exposure against its band
  renders the *measured-breach flag* only, with the sustained-drift alarm gated
  off and the reason stated.
- **Build effort:** **S–M**, including the null-calibration harness and the small
  net-beta-drift simulator dial.
- **Kill criterion:** detection < 0.5 at the budgeted false-alarm rate by $T=48$
  ⇒ demote to the measured-breach flag only, recorded in writing (§4).

## 8. Learning notes

*The spec program doubles as a curriculum; this is what to be able to defend
unaided.*

- **CUSUM and average run length (ARL), by hand.** Page's (1954) one-sided CUSUM
  is the sequential-analysis answer to "has the process mean shifted, and when?"
  Own the two knobs: the **allowance** $k$ (reference value, conventionally half
  the shift you want to catch) sets how much transient excursion decays away, and
  the **decision interval** $h$ trades false-alarm rate against detection delay.
  The performance currency is **ARL**: $\text{ARL}_0$ (mean months to a *false*
  alarm — you want it large) vs $\text{ARL}_1$ (mean months to detect a *real*
  shift — you want it small). Be able to say why a single threshold on the raw
  level (the instantaneous flag) is strictly dominated by CUSUM for a *sustained*
  shift: the level test discards the accumulating evidence that a run of
  excursions carries.
- **Why measurement is not the same as drift-detection.** The exposure *value* is
  measured exactly (Robust). The claim "this is drift, not wander" is an
  **inference about persistence**, and its honesty lives entirely in the null.
  This is the distinction that lets M1 sit next to the do-not-build list without
  violating it: measurement at E/P is allowed and Robust; the *persistence
  classification* is a **calibrated rule** (like M3's DD alarm), not a
  returns-based beta *estimate* (which is the Noise-verdicted, do-not-build path).
- **The autocorrelated-null trap.** Calibrating any run-based or CUSUM detector
  on an **iid** null under-sets the threshold when the real process is serially
  correlated, because autocorrelation lengthens natural runs. A rotating book's
  turnover timescale ($\approx 1/\text{rebalance\_fraction}$) *is* that
  correlation. Calibrate on the simulator's actual honest-wander distribution;
  quote the false-alarm rate you actually get, not the iid one you wish you had.
- **RBSA and why it is the weak rung here.** Sharpe's (1992) returns-based style
  analysis regresses returns on style indices to *infer* exposures; a rolling
  window turns it into a drift proxy. At 36–60 months the rolling betas are so
  noisy that a real 0.3 net-beta walk is buried — this is the returns-based
  style-drift *inference* that Sweep C verdicts **Noise** and the program declines
  to build. Owning *why* it fails (estimation variance of a rolling multivariate
  regression at short $T$) is what justifies putting the R rung behind a noise
  chip rather than deleting it: the contrast *is* the tier-degradation argument.
- **Canonical references (3–4 to own):**
  1. Page, E. S. (1954), "Continuous Inspection Schemes," *Biometrika* — the
     CUSUM procedure and the sequential-detection framing the alarm is built on.
  2. Montgomery, *Introduction to Statistical Quality Control* (CUSUM/EWMA
     chapters) — ARL design, allowance/decision-interval tuning, and why control
     charts calibrate on the in-control (null) distribution.
  3. Sharpe, W. (1992), "Asset Allocation: Management Style and Performance
     Measurement," *JPM* — returns-based style analysis, the R-tier fallback and
     the reason it does not clear at this $N$.
  4. Falk & Kosfeld (2006), "The Hidden Costs of Control," *AER* — the
     withdrawal-under-monitoring result the "worth a conversation" framing
     defends against (shared with M5).
  *(Standardisation context: the Open Protocol Enabling Technology / AIMA
  exposure-reporting template is the E-tier data standard the go-live ask names.)*

**Defend unaided:**

- Explain to a non-quant **why a single month over the band is not drift** but
  four accumulating months are — the CUSUM allowance and decision interval in
  one sentence each.
- State **why the false-alarm rate must be calibrated on an autocorrelated null**
  and what happens if you use iid (you over-fire, and the manager stops
  disclosing).
- Explain **what the E rung claims that the R rung cannot**: E *measures* the
  exposure and detects a 0.3 net-beta walk on time; R *infers* it from returns
  and, at 48 months, cannot tell the walk from noise — same ground truth, two
  honesty levels, the whole thesis in one panel.

---

### Provisional constants (flagged for the numerics gate)

Every value below is a named constant at module top; the numerics gate flips one and the
calibration/demo regenerates deterministically.

| Constant | Provisional value | Role |
| --- | --- | --- |
| `FALSE_ALARM_BUDGET` | 0.05 / manager-year (1-in-20) | Size target the CUSUM $h$ is calibrated to |
| `PINNED_DRIFT_EFFECT` | 0.30 net-beta walk over 12 months | Effect the detector is powered against (X1 §3.4) |
| `NET_BETA_BAND_DEFAULT` | $[-0.10, +0.10]$ | Band assumed when a mandate leaves net beta unstated (marked *assumed*) |
| `DELTA_BAND` | net beta 0.05 · gross 0.15 · factor beta 0.10 · sector 3 ppt · duration 0.25 y | Per-class materiality dead-band $\delta_j$ |
| `CUSUM_ALLOWANCE_K` | 0.5 × pinned monthly drift step (per class) | CUSUM allowance $k_j$ |
| `CUSUM_THRESHOLD_H` | *calibrated on null* (not free) | Decision interval $h_j$; output of §4, not a dial |
| `K_CONSEC` / `M_WINDOW` | 3 of 4 | Run-length simple rung (calibrated to same budget) |
| `FACTOR_SHARE_WINDOW` | 12 months | Window for the factor-share trend test |
| `DEMO_DRIFT_WALK` | 0.10 → 0.45 (0.35) | Demo path; larger than the pinned 0.30 for visual clarity |
| `RBSA_WINDOW` | 24 months | R-tier rolling-beta window (descriptive-only) |

---

## Method review (2026-07-07) — APPROVED, implementation-ready

- **Drift-dial form RULED:** a schedule on `target_net` (linear walk), NOT a
  candidate-selection tilt — the tilt confounds effect size with selection
  dynamics; the tilt variant is deferred to atlas vol. 1 as a robustness axis.
- **Verdict split CONFIRMED:** measurement is Robust; the sustained-drift alarm
  is a calibrated rule (M3's framing) — the card's blanket "Robust" is refined
  accordingly.
- **§3.5 note:** the factor-share panel is estimate-bearing (sigma-hat idio) —
  its slope IntervalStat treatment is the correct rendering; do not describe FS
  as pure measurement in page copy.
- CUSUM `k`/`h`, `FALSE_ALARM_BUDGET`, `DELTA_BAND`, `K_CONSEC` remain numerics-
  gate docket items at build time, calibrated on the autocorrelated null as
  specified.
