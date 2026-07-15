## The decision

When a manager's measured exposure moves outside a stated band, the allocator has two
different facts to keep separate. The exposure reading itself may be exact, but the
claim that the book has **drifted** rather than briefly wandered is an inference about
persistence.

The right output is therefore not a one-month breach alert. It is a sourced exposure
path, the applicable mandate band, and a persistence alarm calibrated to a stated
false-alarm budget. A breach that persists becomes a specific engagement question:
*why has measured net beta remained above the agreed range?* It is never an automatic
redemption instruction.

This distinction matters because exposure drift often appears before performance
changes. Waiting for returns can turn an early risk conversation into a late P&L
explanation.

## Why the obvious answer fails

The obvious rule is to flag any month outside the band. That rule confuses measurement
with evidence. Active books rotate, exposures are serially correlated, and a reading can
briefly cross a boundary before returning. A first-breach rule repeatedly cries wolf.

The opposite shortcut is to infer a changing beta from a rolling return regression.
With only 36–60 monthly observations, a moving-window beta is too noisy to support a
drift verdict. It can remain as a descriptive returns-only view, but it cannot be put on
the same footing as a disclosed exposure.

The failure mechanism is the same in both shortcuts: neither accounts for how evidence
accumulates. The one-month flag discards persistence, while the rolling regression adds
estimation noise to a quantity that could have been measured directly.

## The intuition

Imagine a running tally beside the upper mandate boundary. Each month, add the amount by
which the exposure exceeds the boundary, but first subtract a small allowance for honest
overshoot. Floor the tally at zero.

A tiny excursion contributes a negative amount after the allowance, so the tally stays
at zero. Several material excursions in the same direction contribute positive amounts
and accumulate. Once that cumulative evidence crosses a threshold calibrated on
non-drifting books, the monitor can call the pattern sustained drift.

This is Page's cumulative sum, or CUSUM. Its value here is not mathematical novelty. It
matches the decision question: *has a run of disclosed exposures stayed far enough
outside the band for long enough that ordinary rotation is an implausible explanation?*

## A small numerical example

Suppose a beta-neutral mandate has an upper boundary $U=0.10$. Give ordinary overshoot
an allowance $k=0.05$. Six monthly net-beta readings are

$$
0.12, 0.09, 0.18, 0.22, 0.25, 0.24.
$$

For the upper-side tally, start at zero and add $(x_t-U)-k$ each month, never letting
the result fall below zero.

| Month | Net beta $x_t$ | Contribution $(x_t-U)-k$ | Running tally |
| --- | ---: | ---: | ---: |
| 1 | 0.12 | $-0.03$ | 0.00 |
| 2 | 0.09 | $-0.06$ | 0.00 |
| 3 | 0.18 | $+0.03$ | 0.03 |
| 4 | 0.22 | $+0.07$ | 0.10 |
| 5 | 0.25 | $+0.10$ | 0.20 |
| 6 | 0.24 | $+0.09$ | 0.29 |

Month 1 is outside the boundary, but only by 0.02. After the 0.05 allowance it adds no
evidence. From month 3 onward, the overshoot is both material and persistent. If an
illustrative calibrated threshold were $h=0.15$, the tally would cross it in month 5.

The alarm deliberately arrives after the first breach. That delay is the price of not
calling every transient excursion drift, and its distribution must be reported rather
than hidden.

## The method

For exposure class $j$, let $x_{j,t}$ be the disclosed exposure at time $t$ and let
$[L_j,U_j]$ be its stated lower and upper mandate limits. The instantaneous measurement
is

$$
\operatorname{breach}_{j,t}
=\mathbb{1}\{x_{j,t}<L_j-\delta_j\ \lor\ x_{j,t}>U_j+\delta_j\},
$$

where $\delta_j$ is a materiality dead-band in that exposure's units. This flag answers
only whether the current reading is materially outside the range.

Persistence uses two one-sided accumulators:

$$
S^+_{j,t}=\max\!\left(0,S^+_{j,t-1}+(x_{j,t}-U_j)-k_j\right),
$$

$$
S^-_{j,t}=\max\!\left(0,S^-_{j,t-1}+(L_j-x_{j,t})-k_j\right).
$$

$S^+_{j,t}$ and $S^-_{j,t}$ are cumulative evidence above and below the band;
$k_j$ is the permitted overshoot; and $h_j$ is the decision threshold. The sustained
alarm fires when either accumulator exceeds $h_j$.

$h_j$ is not chosen by taste. It must be calibrated on an autocorrelated
**honest-wander null**. A rotating book naturally produces runs because most holdings
remain from one month to the next. An independent-month null understates those runs,
sets the threshold too low, and over-fires.

A second panel can track whether measured factors are taking a larger share of risk:

$$
\operatorname{FS}_t=
\frac{b_t^{\top}\Sigma_f b_t}
{b_t^{\top}\Sigma_f b_t+\widehat\sigma^2_{\text{idio}}}.
$$

Here $b_t$ is the measured factor-beta vector, $\Sigma_f$ is the factor covariance
matrix, and $\widehat\sigma^2_{\text{idio}}$ is estimated idiosyncratic variance. Since
that last input is estimated, a change in factor share needs a slope interval and a
verdict chip. It is not a pure measurement.

## What the evidence changes

The monitor changes a vague concern into three separately labelled outputs:

- an **exact measurement** of the current disclosed exposure;
- a **calibrated verdict** about whether an excursion has persisted;
- an **estimate with an interval** for a trend in factor share.

The returns-only rung preserves a negative finding. It can show a descriptive rolling
beta, but it refuses a drift verdict at short track lengths. More transparency does not
merely improve presentation: exposure data change the question from noisy inference to
direct measurement.

The evidence can support a watchlist entry and a specific conversation. It does not
establish intent, prove a mandate violation, or determine capital action.

## What the allocator does next

1. Verify that the exposure definition and units match the mandate language.
2. Confirm the band in force on each date; a negotiated band change is not a breach.
3. Review the measured path and the alarm onset with the manager.
4. Use positions, when available, to attribute the drift to names or sleeves.
5. Keep capital action with the human review process rather than wiring the alarm to a
   redemption rule.

## Limits and go-live

The public example is synthetic. A live monitor requires dated exposure summaries for
net and gross exposure, factor betas, sector or duration buckets, plus the stated bands
from mandates or letters. Position holdings add attribution. A returns-only fallback
needs monthly returns and a factor set, but remains descriptive.

The exposure measurement is available at any history length. The sustained alarm is
not. It renders only where calibration for the manager's cadence and horizon supports
its false-alarm and detection-delay claims. The current design provisionally targets a
0.05 false-alarm budget per manager-year and a pinned alternative of a 0.30 net-beta
walk over 12 months. These are calibration inputs, not universal economic truths.

The detector must be demoted to the measured-breach flag if it cannot reach detection
of at least 0.50 by $T=48$ at the budgeted false-alarm rate. Coarse exposure feeds that
cannot place a reading against its band receive the same refusal. Open-Protocol-aligned
reporting is the standardization ask.

## Key takeaways

- A disclosed exposure can be exact while a drift label still requires calibration.
- CUSUM keeps transient overshoot from becoming a persistent-drift claim.
- The null must preserve the autocorrelation created by ordinary book rotation.
- Returns-only rolling beta is descriptive at short histories, not a drift verdict.
- An alarm is engagement material and a review trigger, never an automatic redemption.

## References

- E. S. Page, “Continuous Inspection Schemes,” *Biometrika*, 1954.
- Douglas C. Montgomery, *Introduction to Statistical Quality Control*.
- William F. Sharpe, “Asset Allocation: Management Style and Performance
  Measurement,” *Journal of Portfolio Management*, 1992.
- Armin Falk and Michael Kosfeld, “The Hidden Costs of Control,” *American Economic
  Review*, 2006.
