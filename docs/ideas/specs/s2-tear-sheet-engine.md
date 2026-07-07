# S2 · Uncertainty-Honest Tear-Sheet Engine — Method Spec

**Date:** 2026-07-06
**Status:** Reviewed (2026-07-06) — implementation-ready
**Card:** [`docs/ideas/2026-07-05-idea-cards.md`](../2026-07-05-idea-cards.md) § S2
**Demo:** gallery page `s2.html` (single-manager print pack; fully synthetic factors, §5)

## 1. Problem & decision hook

Standard manager tear sheets report a point Sharpe and a point alpha, computed
on smoothed NAVs against a generic benchmark, with no interval attached. At
36–60 monthly observations that is false precision: a reported Sharpe of 1.4
can carry a 95% confidence interval as wide as $[0.2, 1.6]$ once estimation
error and serial correlation are honestly propagated, and the same smoothing
that flatters the Sharpe also biases betas toward zero and understates
volatility. This engine is the **always-on per-manager panel that is honest by
construction**: every statistic ships as an interval, every verdict as a
calibrated chip, no number as a bare point. It invents no estimators — it
*composes established ones in the right order* (Getmansky–Lo–Makarov
unsmoothing → factor regression → Lo/Ledoit–Wolf intervals → MPPM → drawdown
band) under the Interval design system. Its differentiation is discipline.

Decisions improved: **monitor** — every manager, every month, on a sheet that
cannot overstate confidence; **select** — screening with stated uncertainty
instead of point rankings; **engage** — the manager receives their own honest
sheet (rung-1 reciprocity in the E1 ladder), the alt-beta chip opening a
fees-for-beta conversation rather than closing a case; **redeem** — the
drawdown panel says whether a drawdown is consistent with the paid-for skill
hypothesis.

## 2. Data contract per tier

Conventions follow the S1 spec §2 verbatim: monthly net returns as **decimals**
on a pandas `PeriodIndex` with freq `M`; factor returns aligned on the same
months; annualize returns/alpha by ×12 and volatilities by ×√12; a manager with
more than 2 missing months in the window is excluded and flagged, never
silently interpolated; ≥24 months to enter, ≥36 for full standing.

| Tier | Inputs | What it buys |
| --- | --- | --- |
| R (minimum) | Monthly net returns per manager; risk-free series; strategy label; strategy-appropriate factor returns on the same months | The **whole sheet** — de-smoothed Sharpe with CI, factor regression with interval alpha, alt-beta gate, MPPM, drawdown band. Everything in §3 runs returns-only. |
| E | Manager-reported factor / sector / gross / net exposure summaries (Open Protocol-aligned) | A **measured-vs-inferred exposure panel**: regression betas beside reported exposures; disagreement is flagged as a *question*, not an accusation. |
| P | Holdings / trade snapshots | **Measurement-only** holdings descriptors: active share, top-10 weight, HHI concentration. No estimation happens at P in this card — trade-level skill estimation is cards S3/S4. |

Factor sets by strategy (S1 §2): FF5+MOM for equity L/S; Fung–Hsieh 7 for
macro/trend; credit set **on unsmoothed returns** (stage 1 is a prerequisite,
not an option). Wave-1 uses synthetic factors; real-FF5 is a wave-3 upgrade —
the adapter already exists at `src/quant_allocator/adapters/french.py`.

## 3. Methodology

The pipeline is six pure stages over a returns series and a factor frame,
executed in this order; each stage names its estimator exactly. **Rendering
rule (all stages):** every statistic is an **IntervalStat** (point + interval
rail + range text), every verdict a **VerdictChip** (robust / shrink / noise
per Sweep C), and a **bare point estimate is a design-system lint error** — the
builder's honest-mockup lint (gallery design §7) fails the page if one appears.

### 3.1 Unsmoothing — Getmansky–Lo–Makarov (2004)

Observed returns are a moving average of the true (economic) returns:

$$r^{\text{obs}}_t = \theta_0 r_t + \theta_1 r_{t-1} + \theta_2 r_{t-2},
\qquad \sum_{k=0}^{2}\theta_k = 1,\quad \theta_k \ge 0.$$

The constraints make this a convex smoothing kernel that redistributes return
across months without changing the long-run mean. The $\theta_k$ are estimated
by **maximum likelihood** (MA(2) of the regression residual) and are a
**first-class illiquidity diagnostic in their own right** — large
$\theta_1,\theta_2$ is a smoothing/liquidity flag on the sheet, not merely an
intermediate. The kernel conserves mean but not variance:
$\sigma^2_{\text{obs}} = (\sum_k \theta_k^2)\,\sigma^2_r$ with
$\sum_k \theta_k^2 \le (\sum_k \theta_k)^2 = 1$, so de-smoothed vol
$\sigma_r = \sigma_{\text{obs}}/\sqrt{\sum_k\theta_k^2}$ is **larger** and the
de-smoothed Sharpe **lower**. The engine reconstructs the de-smoothed series
and recomputes vol and Sharpe from it. Applied by default to credit / illiquid
strategies; **skipped with a printed note when $\theta_0 \ge 0.95$** (no
material smoothing — de-smoothing would only add estimator noise).

### 3.2 Factor regression

OLS of the (de-smoothed, where applicable) excess return on the
strategy-appropriate factor set (§2): FF5+MOM equity L/S; Fung–Hsieh 7
macro/trend; credit set on unsmoothed returns. Outputs the point alpha
(annualized ×12) and betas that feed stages 3, 5, and the tier-E panel.

### 3.3 Interval machinery

Three interval sources, reported together so the reader sees agreement or
divergence:

- **Sharpe SE — Lo (2002).** The closed-form
  $SE(\widehat{SR}) \approx \sqrt{(1 + SR^2/2)/T}$ on the **per-period
  (monthly)** Sharpe, annualized *explicitly*: iid, both point and SE scale by
  $\sqrt{12}$; under serial correlation the correct factor is smaller than
  $\sqrt{12}$ (the "$\sqrt{12}$ trap", §8) — which is exactly why stage 1 runs
  first. The cheap, always-available interval.
- **Production Sharpe CI — Ledoit–Wolf (2008).** Studentized **circular block
  bootstrap**, $B = 2{,}000$, block length $\approx T^{1/3}$ rounded (≈4 at
  T=48). Blocks preserve the autocorrelation Lo's formula only approximates;
  studentization gives second-order accuracy under fat tails. The CI the sheet
  shows once it clears validation (§4).
- **Alpha CI — HAC (Newey–West).** Newey–West with lag $\approx T^{1/4}$ (≈3 at
  T=48), block bootstrap as cross-check; on material disagreement the sheet
  widens to the looser of the two and flags it.

### 3.4 MPPM — Goetzmann–Ingersoll–Spiegel–Welch

The manipulation-proof performance measure with risk aversion $\rho = 3$,

$$\widehat{\Theta}_\rho = \frac{1}{(1-\rho)\,\Delta t}\,
\ln\!\left(\frac{1}{T}\sum_{t=1}^{T}
\Big(\frac{1+r_t}{1+r_{f,t}}\Big)^{1-\rho}\right),
\qquad \Delta t = \tfrac{1}{12},$$

reported (annualized) **beside** the Sharpe. A large **Sharpe-vs-MPPM gap** is
a manipulation / hidden-optionality flag: the two agree for well-behaved
distributions and diverge when the payoff has been reshaped (sold tails,
smoothed marks). The gap feeds card M2 later; here it is a printed flag, not a
verdict.

### 3.5 Alt-beta gate

If the factor **alpha's 90% CI contains zero**, the sheet renders the
VerdictChip **"provisionally alternative beta"** — the fees-for-beta
conversation from Sweep A. The chip **states the CI**, never just the label
("alpha 90% CI $[-1.2\%, +3.1\%]$/yr — not distinguishable from factor beta at
this track length"). It is a *calibration statement about track length*, not a
claim that the manager has no skill.

### 3.6 Drawdown panel

The realized drawdown path is plotted against a **simulation-calibrated band**:
Monte Carlo of the maintained hypothesis (claimed or S1-posterior Sharpe,
de-smoothed vol from stage 1, fitted **AR(1)** autocorrelation) generates the
null distribution of the path, and the band is the **50 / 95 / 99th percentile
envelope**. This is **M3-lite** — it shows whether the observed drawdown is
ordinary or extreme under the paid-for skill hypothesis. The full alarm logic
(hysteresis, time-to-detection, roster heat-list) is card M3, which slots into
this same panel when built.


## 4. Power & validation plan

Validation runs on the simulator; cells are contributed to the X1 atlas
([`x1-tier-power-atlas.md`](x1-tier-power-atlas.md)) as this card's rows. Grid:
$T \in \{36, 48, 60\}$ × strategy family × smoothing level × true Sharpe, with
seeded replications per cell (per-module RNG streams).

Acceptance gates:

1. **Alt-beta chip operating characteristics.** False-alarm rate (chip fires on
   a true-skill manager) and detection rate (chip fires on a true alt-beta
   manager) at each $T$; both curves reported, not a single threshold.
2. **CI coverage.** Empirical coverage of the Sharpe CI (Ledoit–Wolf) and the
   alpha CI (HAC) on simulated managers within **±5 pp of nominal**.
3. **Drawdown-band false-alarm rate.** On healthy managers, the fraction
   breaching the 99th-percentile envelope is **≤ the stated envelope
   percentile** (a calibrated 99th band false-alarms ≤1% of the time).
4. **θ-recovery.** Simulator returns passed through a *known* MA(2) smoother;
   the stage-1 MLE recovers the injected $\theta_k$ within tolerance, and the
   de-smoothed vol recovers the pre-smoothing vol.

**Kill criterion.** If Sharpe or alpha CI coverage is off by more than ±5 pp
*after* the Ledoit–Wolf bootstrap variant, the sheet ships **Lo-SE intervals
labeled "approximate"** — never an unlabeled interval claiming a coverage it
does not have. A miscalibrated interval sold as exact is worse than an honest
approximation.

## 5. Implementation architecture

- `src/quant_allocator/flagships/tearsheet/pipeline.py` — stages 1–6 as **pure
  functions over a returns series + factor frame**: `unsmooth(returns) ->
  UnsmoothResult` (θ estimates + de-smoothed series), `regress(returns,
  factors) -> FactorFit`, `sharpe_intervals(returns) -> SharpeStats` (Lo SE +
  Ledoit–Wolf bootstrap), `alpha_interval(fit) -> AlphaStats` (HAC + bootstrap
  cross-check), `mppm(returns, rf, rho=3) -> float`, `drawdown_band(returns,
  hypothesis) -> DrawdownBand`. No rendering, no I/O in this module.
- `src/quant_allocator/flagships/tearsheet/render.py` — pack JSON emission
  (IntervalStat / VerdictChip / TierBadge payloads). The **demo generator
  (`demo_data/s2_tearsheet.py`) imports `pipeline.py`** — demo numbers and live
  numbers come from the *same code path*; only the input data differs
  (synthetic vs real). This is the load-bearing architectural commitment.
- Depends: `numpy` plus `scipy` — **scipy is a new runtime dependency**,
  added when this pipeline lands (optimizer for the MA(2) MLE; bootstrap and
  HAC are numpy-implementable). It runs only in local generation — CI never
  computes (gallery design §1). Also: the simulator (validation), the FF5
  adapter (`adapters/french.py`, wave-3 real-factor variant only). No PyMC —
  this card is estimator composition, not Bayesian inference.
- Effort: **S–M (~4 sessions)**: pipeline stages 2, validation grid 1, pack +
  demo page 1. Wave-1 ships on fully synthetic factors (no CI network
  dependency, no factor-data redistribution question); real-FF5 is a wave-3
  upgrade.

## 6. Adoption & packaging

The sheet **is the always-on layer** — every manager, every month — and it is
the first consumer of the Interval design system (this card births
`design-tokens.css` alongside the shell). It doubles as **rung-1 reciprocity in
the E1 ladder**: the manager receives their own honest sheet, which is what a
returns-only relationship earns.

Copy rules (Sweep E doctrine): chips read as **calibration, not accusation** —
the framing is always "what this track length supports", never "your Sharpe is
fake". The alt-beta chip is a **fee-conversation opener**, not a dismissal, and
always shows the interval so the manager sees exactly what the data does and
does not resolve.

The S1 **posterior strip** embeds when the skill ledger is available (S1 §3.6):
the posterior alpha IntervalStat sits beside the regression alpha, and the
drawdown band (§3.6) uses the S1 posterior Sharpe as its maintained hypothesis
when present, the claimed Sharpe otherwise.

## 7. Go-live requirements

- **Data ask:** monthly net returns (tier R) + a risk-free series + the chosen
  factor set for the manager's strategy. Tier E adds reported exposure
  summaries (measured-vs-inferred panel); tier P adds holdings snapshots
  (descriptors only).
- **Sample required:** ≥36 months for full standing (≥24 to render with an
  explicit short-track caveat). The alt-beta and drawdown panels are honest at
  any $T$ because their outputs are intervals and calibrated bands, not points.
- **Build effort:** S–M (~4 sessions). Real-FF5 factors are a wave-3 upgrade
  (adapter already built); wave-1 ships on synthetic factors.
- **Go-live box (demo page):** data ask = monthly returns (R); sample =
  ≥36 months; effort = S–M.

## 8. Learning notes

**Derivations to own (work each by hand once):**

1. **Lo's Sharpe SE from the delta method (sketch).** $\widehat{SR} =
   \hat\mu/\hat\sigma$; take the asymptotic joint distribution of
   $(\hat\mu, \hat\sigma^2)$, apply the delta method with gradient
   $(\partial SR/\partial\mu, \partial SR/\partial\sigma^2)$, and for iid normal
   returns the cross-term drops, leaving
   $\mathrm{Var}(\widehat{SR}) \approx (1 + SR^2/2)/T$. Own why the $SR^2/2$
   term appears (estimation error in the *denominator* $\sigma$).
2. **The $\sqrt{12}$ trap.** Annualizing a monthly Sharpe by $\sqrt{12}$
   assumes zero serial correlation. With positive autocorrelation $\rho_1$ the
   correct multi-period scaling factor is **smaller** than $\sqrt{12}$
   (variance of a sum of correlated returns grows faster than the number of
   periods), so naive $\sqrt{12}$ **overstates** the annualized Sharpe. GLM
   smoothing manufactures exactly this positive autocorrelation — so a smoothed
   fund's headline annualized Sharpe is doubly inflated, and unsmoothing (§3.1)
   is what maps the reported number back to something defensible. Map the GLM
   $\theta$'s to liquidity: high $\theta_1,\theta_2$ = returns bleed across
   months = marks are stale = illiquid book.
3. **Why MPPM is manipulation-proof (one paragraph).** MPPM is the annualized
   certainty-equivalent return of a power-utility investor with CRRA $\rho$.
   Being a monotone function of expected power utility over the *realized
   return distribution*, no payoff reshaping a rational $\rho$-investor would
   not genuinely prefer — leverage, selling options, smoothing marks, timing —
   can raise it without truly raising that investor's expected utility. The
   Sharpe ratio, by contrast, is gameable (selling tails lifts the mean, barely
   moving reported vol) — hence the Sharpe-vs-MPPM gap is a manipulation tell.
4. **Block-bootstrap intuition.** iid resampling of autocorrelated returns
   destroys the very serial dependence that inflates the annualized Sharpe, so
   iid-bootstrap CIs are too tight. Resampling **blocks** (length $\approx
   T^{1/3}$) preserves within-block dependence; the *circular* variant wraps the
   series so every observation gets equal resampling weight. Studentizing
   (bootstrapping the t-statistic, not the statistic) buys second-order
   accuracy under fat tails.

**Canonical papers (read in this order):** Lo (2002, FAJ) — the SR standard
error and the annualization-under-autocorrelation result; Getmansky–Lo–Makarov
(2004, JFE) — the MA smoothing model and de-smoothing; Ledoit–Wolf (2008, JEF)
— studentized bootstrap CIs for the Sharpe ratio; Goetzmann–Ingersoll–Spiegel–
Welch ("Sharpening Sharpe Ratios") — the MPPM and its manipulation-proofness;
Fung–Hsieh (2004, FAJ) — the 7-factor macro/trend model (note the 80% R² claim
applies to diversified HF portfolios, not single funds).

**Defend unaided:**

- State the **T=48 Sharpe CI width** from Lo's formula for annualized SR = 1
  (annualized SE $\approx 0.51$/yr, 95% CI roughly $[0, 2]$) and explain it to a
  non-quant: "with four years of monthly data a headline Sharpe of 1.0 is
  indistinguishable from both zero skill and world-class — not a criticism, just
  the arithmetic of four years."
- Explain **why a de-smoothed Sharpe can drop by a third**: smoothing hides
  volatility, so the reported denominator is too small; restoring true vol
  (dividing by $\sqrt{\sum\theta_k^2}<1$) can cut the ratio substantially for an
  illiquid book.
- Explain **what the alt-beta chip does and does not claim**: it says the
  factor-alpha 90% interval includes zero *at this track length* — a resolution
  statement and a fees-for-beta prompt — **not** that the manager is talentless
  or the alpha truly zero.
