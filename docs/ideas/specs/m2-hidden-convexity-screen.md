# M2 · Hidden-Convexity / Short-Vol Screen — Method Spec

**Date:** 2026-07-07
**Status:** Draft — pending method review
**Card:** [`docs/ideas/2026-07-05-idea-cards.md`](../2026-07-05-idea-cards.md) § M2
**Demo:** gallery page `m2.html` (wave-2 batch 1; two-manager convexity screen, fully synthetic, §5)

## 1. Problem & decision hook

A smooth Sharpe can hide sold optionality. A manager who quietly writes puts,
runs short-gamma carry, or holds an illiquid book marked to a mean collects a
steady premium that flatters every linear statistic — Sharpe, alpha, beta — right
up to the month the tail arrives. Standard tear sheets are blind to this by
construction: a linear factor regression fits the *average* sensitivity and
discards the **shape** of the payoff, which is exactly where short-vol posture
lives. Sweep D flags non-linearity detection from a return series as white space,
high-value for macro and credit books where the optionality is structural.

This screen surfaces payoff-shape asymmetry from returns alone: a small battery
of **returns-based convexity diagnostics** — a Treynor–Mazuy quadratic term,
Henriksson–Merton up/down beta asymmetry, coskewness with the market factor, and
a drawdown-vs-vol signature — each interval-reported, composited into a **flag for
investigation, never a verdict**.

Decisions improved: **monitor** — left-tail exposure surfaced before it detonates,
on a sheet that cannot be fooled by a benign realized vol; **redeem** — a persistent
short-vol posture reframes the mandate as a paid-for beta-carry bet, priced and
sized as one.

- **Customer:** investment team; risk-adjacent leadership reporting.
- **What it is not (binds — see §3.2, §4):** M2 does **not** split the sample into
  regimes and tabulate a separate alpha per regime, and it does **not** fit rolling
  or time-varying conditional betas. Those are on the program's do-not-build list at
  36–60 observations (convergence decision §4) — halving an already-tiny sample to
  read a conditional *alpha* is precisely the move Sweep C verdicts Noise. Every
  M2 statistic is a **single static shape coefficient fit over the whole window**,
  interpreted as payoff geometry and reported with an interval, never as a
  regime-conditional return claim. The composite is a prompt to look, not a label
  that a book is short-vol.

## 2. Data contract per tier

Conventions inherit S1 §2 / S2 §2 verbatim: monthly net returns as **decimals** on
a pandas `PeriodIndex` freq `M`; the market factor and any straddle-factor series
aligned on the same months; ≥24 months to enter, ≥36 for full standing; a manager
with more than 2 missing months in the window is excluded and flagged, never
interpolated. **Stage 0 is S2's Getmansky–Lo–Makarov unsmoothing** (S2 §3.1): the
screen runs on the de-smoothed series so that mark-smoothing autocorrelation is not
misread as convexity — the two are distinct tells and the screen must not conflate
them (§4).

| Tier | Inputs the live version needs | What the card produces |
| --- | --- | --- |
| **R** (native) | Monthly net returns; market-factor return series; **Fung–Hsieh PTFS straddle-factor series** for the §3.5 rung (external, public — see §7) | The whole screen: Treynor–Mazuy γ, HM up/down beta gap, market coskewness, drawdown-vs-vol signature, each as an IntervalStat, and the composite evidence tally. |
| **E** | R + reported exposure/optionality summaries (gross gamma/vega, net premium, option notional where disclosed) | **Confirmation panel**: the inferred short-vol posture set beside the *reported* optionality — agreement raises confidence, disagreement is itself a conversation. Measurement beside inference, never overwriting it. |
| **P** | E + position/holdings with instrument detail | **Direct payoff inspection**: the actual written options / convex instruments that the returns-based screen could only infer. At P the screen is corroboration; the book is the truth. |

The screen is *designed* for the R rung — its reason to exist is the returns-only
majority whose optionality is never disclosed. E and P do not sharpen the R
estimators; they **confirm or contradict** them, and that gap is the product at
those tiers.

## 3. Methodology

Five diagnostics over a de-smoothed return series and a market-factor series,
each a pure function returning a point and an interval; then one composite tally.
**Rendering rule (all diagnostics):** every statistic is an **IntervalStat**, every
verdict a **VerdictChip** (robust / shrink / noise per Sweep C), and a bare point
estimate is a design-system lint error (S2 §3, gallery honest-mockup lint). All
intervals use the **studentized circular block bootstrap** from S2 §3.3
(`B = M2_BOOTSTRAP_B`, default 2,000; block length ≈ $T^{1/3}$) so the reported
uncertainty already carries the serial dependence these third-moment and
interaction estimators are especially fragile to.

### 3.1 Treynor–Mazuy quadratic convexity — the primary tell

Regress the (de-smoothed) excess return on the market factor **and its square**:

$$r_{i,t} = \alpha_i + \beta_i\, f^{\text{mkt}}_t + \gamma_i\,\big(f^{\text{mkt}}_t\big)^2 + \varepsilon_{i,t}.$$

$\gamma_i$ is the curvature of the payoff in the market factor. A **persistently
negative $\gamma$ is the short-convexity signature**: the manager gives back on
large moves of either sign relative to a linear book — the return profile of a
written straddle. This is Treynor–Mazuy (1966) read *backwards*: their market-timers
wanted $\gamma>0$; a short-vol book carries $\gamma<0$. It is one coefficient over
the whole sample — not a regime split. Two honest caveats travel with it, both
surfaced on the sheet: (i) $(f^{\text{mkt}})^2$ has little spread at $T\le 60$, so
$\text{SE}(\gamma)$ is large (§4); (ii) $\gamma$ and $\alpha$ are partly confounded —
a concave payoff depresses the mean, so a naive reader who trusts $\alpha$ while
ignoring $\gamma$ is double-counting. The chip states the $\gamma$ interval, never
the sign alone.

### 3.2 Henriksson–Merton up/down beta asymmetry

Fit the single dual-beta regression over the whole window:

$$r_{i,t} = \alpha_i + \beta^{-}_i\, f^{\text{mkt}}_t + \gamma_i\,\max\!\big(f^{\text{mkt}}_t, 0\big) + \varepsilon_{i,t},$$

so $\beta^{-}_i$ is downside participation and $\beta^{+}_i = \beta^{-}_i + \gamma_i$
is upside participation. The tell is $\beta^{-} > \beta^{+}$ (i.e. $\gamma<0$): more
market participation when the market falls than when it rises — a concave, short-vol
profile. **This is where the do-not-build caution binds hardest and must be stated
on the sheet.** The down-leg is identified only off down-months, of which a
positive-drift market leaves roughly $T\cdot P(f<0)\approx 0.4\,T$ — about **19 at
T = 48**. So $\beta^{-}$ is effectively a ~19-observation estimate and its interval
is wide. M2 handles this by (a) reporting the up/down gap as an IntervalStat that
will honestly be wide, and (b) **never converting the split into a conditional-alpha
table** — the banned analytic. The interaction term is a payoff-shape descriptor;
it is not, and is never rendered as, "the manager's alpha in down markets."

### 3.3 Coskewness with the market factor — Harvey–Siddique (2000)

Standardized coskewness of the manager's return with the market:

$$\widehat{\text{coskew}}_i = \frac{\frac{1}{T}\sum_t (r_{i,t}-\bar r_i)\,(f^{\text{mkt}}_t-\bar f)^2}{\hat\sigma_{r_i}\,\hat\sigma_f^2}.$$

Negative coskewness means the manager's returns are worst when the market's squared
move (its realized variance) is largest — the return stream is short the market's
volatility. It is the model-free cousin of §3.1: where Treynor–Mazuy fits the
curvature parametrically, coskewness measures it as a co-moment, so agreement
between the two is genuine corroboration rather than one statistic in two costumes.
Third co-moments are the noisiest objects on the sheet: the sampling SE of plain
skewness is $\approx\sqrt{6/T}\approx 0.35$ at T = 48, and coskewness inherits that
fragility — so the estimate is compared against a **normal-calibrated band**
(`M2_COSKEW_BAND`, provisional, set from the simulator §4), and only a coskewness
outside the band counts toward the tally.

### 3.4 Drawdown-vs-vol signature

Short-vol books look calm and draw down violently: benign month-to-month volatility,
fat left tail. The signature is the ratio of realized maximum drawdown to annualized
volatility, referenced to what a Gaussian (or fitted-AR(1), reusing S2 §3.6) return
stream of the *same* vol and length would produce:

$$Z^{\text{DD}}_i = \frac{\text{MaxDD}_i}{\hat\sigma_i} \Big/ q^{\text{null}}_{\text{DD/vol}}(T),$$

where $q^{\text{null}}$ is the simulation-calibrated median drawdown-to-vol ratio for
a no-skill stream at length $T$. A signature above the `M2_DDVOL_QUANTILE`
(provisional 95th) percentile of the null flags a drawdown deeper than the manager's
own volatility should produce. This reuses S2's drawdown-band machinery (§3.6) — it
is not a new estimator, it is that band read for asymmetry. **Corroborating, not
primary:** the Sharpe-vs-MPPM gap and the GLM smoothing $\theta$ from the S2 pipeline
are surfaced alongside (a large gap plus high $\theta$ is the classic smoothed
short-vol tell), but they are *supporting evidence in the tally*, because a large gap
also fires on ordinary manipulation and high $\theta$ also fires on honest
illiquidity — neither is convexity-specific on its own.

### 3.5 Fung–Hsieh straddle-factor loadings (external-data rung)

Where the FH primitive trend-following straddle (PTFS) factor series is available,
regress the return on it: a **persistently negative** loading is a direct short-vol
posture (the manager is on the other side of the lookback straddle). This is the most
literature-blessed of the diagnostics (Fung–Hsieh 2001) but the most data-hungry —
it needs the external factor series (§7) and the straddle betas are themselves noisy
at $T\le 60$ (the card's Sweep-C prior: *Shrink*). It is therefore an **optional
rung**: present when the series is loaded, and gated exactly like the others.

### 3.6 The composite — an evidence tally, not a score

The screen does **not** collapse the diagnostics into a single scalar. It renders an
**evidence tally**: each diagnostic contributes one of {short-vol-consistent,
inconclusive, convex/benign} based on whether its *interval* clears its band in the
short-vol direction. The composite verdict is
`SHORT-VOL POSTURE — INVESTIGATE` only when at least `M2_COMPOSITE_K` (provisional 3)
of the playable diagnostics agree in the short-vol direction **and** the PowerGate
for the current $T$ is open (§4); otherwise the sheet shows the individual
IntervalStats and a `NOISE` chip on the composite, i.e. "not resolvable at this track
length." The diagnostics are only *approximately* independent (they all read the same
left-tail geometry), so the tally is presented as **converging evidence, not a
p-value** — the honest framing is "four windows onto the same shape agree," never a
manufactured joint significance.

## 4. Power & validation plan

**This is the load-bearing section.** Every M2 diagnostic is a third-moment or
interaction estimator — the lowest-power objects computable from a short return
series. The screen earns the right to render only by proving, on the simulator, that
its false-alarm rate is controlled at the sample sizes we actually have. Cells are
contributed to the X1 atlas ([`x1-tier-power-atlas.md`](x1-tier-power-atlas.md)) as
this card's rows; M2 also motivates the **one new simulator dial** the card names.

**Simulator extension — the written-put overlay dial.** The equity manager
(`simulator/manager.py`) and the crude returns-only generator
(`simulator/returns_only.py`) have no short-vol posture today. Add a
`WrittenPutOverlay` with three named parameters — `premium_annual` (the carry the
manager collects), `strike_moneyness` (OTM distance in market-factor σ units), and
`overlay_notional` $\kappa$ — producing a monthly overlay return
$o_t = \text{premium}_t - \kappa\cdot\max(\text{strike} - f^{\text{mkt}}_t,\,0)$
added to the manager's stream. The premium is set so that at each $\kappa$ the
overlay's *expected* contribution is ≈ 0 (`M2_OVERLAY_FAIR = True`, provisional):
the point of the dial is a book whose **in-sample Sharpe is unchanged** while the
left tail fattens — which is exactly what makes the screen's job hard and the
wow-demo honest. $\kappa = 0$ recovers the honest manager.

**The confound that defines the false-alarm axis.** The dangerous false positive is
not a random honest manager — it is an **honest-but-smooth** one: an illiquid book
with high GLM $\theta$ and genuine positive autocorrelation but *no* sold optionality.
Smoothing and convexity both dent the linear picture, and a lazy screen calls both
short-vol. So the size axis of the grid is honest-but-smooth managers (θ dialed up,
$\kappa = 0$), and the pass bar is that the screen does **not** flag them. Running the
diagnostics on the S2-de-smoothed series (§2) is the first defense; the calibration
proves it works.

**Atlas grid (M2 rows).** $\kappa \in \{0,\ \text{low},\ \text{med},\ \text{high}\}$
× $T \in \{36, 48, 60, 120\}$ × smoothing $\theta_1 \in \{0,\ \text{mild},\
\text{heavy}\}$ × strategy family {equity L/S, crude credit}, ≥1,000 seeded paths per
cell (per-module RNG streams, X1 §3.3 convention). Estimands per cell: **detection**
= P(composite flags | $\kappa>0$); **size** = P(composite flags | $\kappa=0$),
reported *separately* for honest-smooth vs honest-liquid; and per-diagnostic power
curves so the tally's weakest member is visible.

**Gates.**

1. **Size / false-alarm (the card's kill criterion).** Composite false-alarm on
   honest managers — **including honest-but-smooth** — must sit at or below
   `M2_FALSE_ALARM_MAX` (provisional 0.10) at $T = 48$. The card's stated kill line
   is **1-in-5**: if calibrated false-alarm exceeds 0.20 at $T = 48$, the screen is
   noise theater and is **killed or its minimum window lengthened**, recorded in
   writing per converge-or-cut — not shipped quietly.
2. **PowerGate (what renders).** The composite verdict renders only at $T \ge$
   `M2_MIN_T_FLAG` (provisional 48), the smallest window where gate 1 holds in the
   atlas. Below it the sheet shows the individual IntervalStats with a `NOISE`
   composite chip — the refusal is the honest product.
3. **Interval coverage.** Bootstrap-CI coverage for each diagnostic within ±5 pp of
   nominal on simulated managers (as S2 §4); a diagnostic that cannot be honestly
   interval-reported is dropped from the tally, not shipped with a fake interval.
4. **Recovery.** At `high` $\kappa$ the screen's detection power is reported as a
   curve in $T$; the honest headline is likely "reliable only at $T \ge$ some
   number, and never for a mild overlay at 36 months" — a first-class finding, not a
   failure to bury.

**Regime-split caution, restated as a validation constraint.** No M2 cell estimates
a regime-conditional alpha, and none is added to the atlas. The up/down and quadratic
terms are validated as **shape-coefficient recovery** (does the screen recover the
injected $\kappa$?), never as conditional-return accuracy. This keeps M2 clear of the
do-not-build list while measuring the one thing that list does not forbid: the static
geometry of the payoff.

## 5. Implementation architecture

Module home: **`src/quant_allocator/flagships/convexity/`**

- `diagnostics.py` — the five §3 estimators as **pure functions over a return series
  and a factor frame**: `treynor_mazuy(returns, mkt) -> ConvexityStat`,
  `updown_beta(returns, mkt) -> AsymmetryStat`, `market_coskew(returns, mkt) ->
  CoskewStat`, `drawdown_vol_signature(returns, hypothesis) -> DDVolStat`,
  `straddle_loading(returns, ptfs) -> StraddleStat`. Each returns a point + bootstrap
  interval + band-clearance flag; no rendering, no I/O. The bootstrap and the
  de-smoothing pre-stage are **imported from the S2 tearsheet pipeline**, not
  re-implemented (S2 §5).
- `screen.py` — the §3.6 composite: assembles the tally, consults the PowerGate
  registry (X1) for `M2_MIN_T_FLAG`, emits the composite VerdictChip.
- `render.py` — pack JSON (IntervalStat / VerdictChip / TierBadge payloads); the
  **demo generator (`demo_data/m2_convexity.py`) imports `diagnostics.py` and
  `screen.py`** — demo numbers and live numbers come from the same code path, only
  the input data differs (S2's load-bearing commitment).
- `simulator/overlays.py` (**new**) — the `WrittenPutOverlay` dial (§4), added as a
  composable overlay so both the equity manager and the returns-only generator can
  wear it; unit-tested that it recovers a known $\kappa$ and that `premium` fairness
  holds in expectation.

**Dependencies:** `numpy` + `scipy` (already S2's; bootstrap, OLS, optimizer).
FH PTFS straddle series adapter is a **named prerequisite for the §3.5 rung only**
(the R core runs without it). PyMC not used — M2 is estimator composition, not
Bayesian inference. CI never computes numbers; it renders committed demo JSON
(gallery design §1).

**Effort:** M — diagnostics 1 session (they are small, given S2's bootstrap),
simulator overlay dial + tests 1, validation/atlas grid 1, pack + demo page 1.
**Sequencing:** the overlay dial lands first (it is the fake-data source for the
demo *and* the validation), then the screen, then it hosts inside the S2 tear sheet
as a panel (it does not ship as a standalone dashboard — §6).

## 6. Adoption & packaging

The screen's output is a **posture worth understanding**, not an accusation, and the
framing is load-bearing (Sweep E):

- **"A payoff shape to price, not a fund to indict."** A short-vol posture is not
  misconduct — it is a legitimate strategy that must be *sized and paid for as a
  beta-carry bet*, not as uncorrelated alpha. The copy is "this book's returns carry
  a concave, short-volatility signature — here is what that implies for tail sizing,"
  never "the smooth Sharpe is fake." The redeem decision it feeds is about
  mispricing, not integrity.
- **Kill the dashboard — it hosts in S2.** M2 is a **panel on the tear sheet**
  (S2 §3.6 sits right next to it), not a separate short-vol dashboard. A standalone
  screen would be the 25%-adoption separate-tab failure mode (Sweep E); delivered as
  one section of the always-on sheet, it is read every month in context.
- **Investigation prompt, never a trigger.** The composite flag opens a look — pull
  the E/P confirmation panel, ask the manager about optionality — it is never a
  mechanical redemption rule. Goodhart applies: a published short-vol score gets
  gamed (managers reshape marks to dodge the coskewness band); the value is the
  investigation, so it is delivered as investigation material.

**Who sees what, when:** internal team gets the full tally at monitoring cadence;
any manager-facing version ships only inside the E1 ladder relationship, framed as
"help us understand your tail," and uses the E/P confirmation panel so the
conversation is about the book, not about an inference.

## 7. Go-live requirements

The demo page's "what this needs to go live" box, expanded:

- **Data ask:** monthly net returns (R) + a market-factor return series — the core
  screen runs on these. The §3.5 straddle rung additionally needs the **Fung–Hsieh
  PTFS factor series** (public — David Hsieh's data library; a small adapter, not yet
  built). Tier E adds reported optionality/gross-gamma summaries for the confirmation
  panel; tier P adds instrument-level holdings.
- **Sample required:** the gate is **calibrated false-alarm, not a raw count**. The
  composite verdict renders only at $T \ge$ `M2_MIN_T_FLAG` (provisional 48 months,
  pinned by the atlas), where honest-manager false-alarm — including honest-but-smooth
  — sits ≤ `M2_FALSE_ALARM_MAX` (provisional 0.10). Below that window the individual
  IntervalStats render with a `NOISE` composite chip; the screen never claims a
  posture it cannot support.
- **Build effort:** **M**, including the `WrittenPutOverlay` simulator dial (a
  prerequisite for both the demo and the validation) and reuse of S2's de-smoothing +
  bootstrap.
- **Kill criterion:** calibrated false-alarm > **0.20 at T = 48** on honest managers
  ⇒ the screen is killed or its minimum window lengthened, recorded in writing.

## 8. Learning notes

*The spec program doubles as a curriculum; this is what to be able to defend unaided.*

**Derivations to own (work each by hand once):**

1. **Treynor–Mazuy $\gamma$ as convexity, and its confound with $\alpha$.** Write the
   payoff as a quadratic in $f$; show that a written-straddle payoff
   ($-\kappa\max(K-f,0)$ near the money) has $\gamma<0$ to second order, and that
   $\mathbb{E}[\gamma f^2]<0$ pulls the fitted intercept — so a book with negative
   $\gamma$ *manufactures* apparent $\alpha$. Own why reading $\alpha$ without
   $\gamma$ double-counts.
2. **Why the down-beta is a ~19-observation estimate at T = 48.** With market drift,
   $P(f<0)\approx 0.4$; the Henriksson–Merton down-leg is identified off those months
   only, so $\text{SE}(\beta^{-})\propto 1/\sqrt{0.4\,T}$. Derive it, and thereby why
   splitting the sample *further* (regime-conditional alpha) is statistically hopeless
   here — the do-not-build list is an arithmetic conclusion, not a taste.
3. **Third-moment sampling error.** Sample skewness has SE $\approx\sqrt{6/T}$ under
   normality; at T = 48 that is 0.35. Coskewness inherits this fragility. This single
   number is why the screen is gated and composited rather than trusted point-by-point.
4. **Smoothing ≠ convexity.** GLM smoothing (S2 §3.1) manufactures positive
   autocorrelation and a benign-looking vol; short-vol posture manufactures negative
   convexity and a fat left tail. Both dent the linear picture, but only the second is
   optionality. Own why de-smoothing *first* (running M2 on the de-smoothed series) is
   what keeps an honest illiquid book from being called short-vol — the whole
   false-alarm control in §4 rests on this.

**Provisional constants (numerics gate).** `M2_BOOTSTRAP_B` (2,000),
`M2_COSKEW_BAND`, `M2_DDVOL_QUANTILE` (95th), `M2_COMPOSITE_K` (3),
`M2_MIN_T_FLAG` (48), `M2_FALSE_ALARM_MAX` (0.10), kill line (0.20 @ T=48),
`M2_OVERLAY_FAIR` (True) and the `WrittenPutOverlay` parameter ranges — all pinned by
the atlas, none hard-coded silently.

**Canonical papers (read in this order):**
1. Agarwal & Naik (2004, *RFS*), "Risks and Portfolio Decisions Involving Hedge
   Funds" — the foundational result that many hedge-fund payoffs resemble a **short
   put on the market**; the reason this screen exists.
2. Fung & Hsieh (2001, *RFS*), "The Risk in Hedge Fund Strategies: Theory and Evidence
   from Trend Followers" — the PTFS straddle factors (§3.5) and the option-like view
   of strategy returns.
3. Treynor & Mazuy (1966, *HBR*) and Henriksson & Merton (1981, *JB*) — the quadratic
   and dual-beta market-timing regressions read backwards as convexity diagnostics
   (§3.1–3.2).
4. Harvey & Siddique (2000, *JF*), "Conditional Skewness in Asset Pricing Tests" — the
   coskewness estimator and why negative coskewness is priced (§3.3).
5. Mitchell & Pulvino (2001, *JF*), "Characteristics of Risk and Return in Risk
   Arbitrage" — a worked case where a smooth return stream *is* a written put, for the
   intuition; and Goetzmann–Ingersoll–Spiegel–Welch (MPPM, via S2 §3.4) for the
   manipulation-proof gap used as corroboration.

**Defend unaided:**
- Explain to a non-quant why a Sharpe of 1.1 can be a *warning*: "the calm months
  are the premium; the screen looks for the shape that says a tail is being sold, not
  earned." State the four diagnostics and that they are four windows onto one
  geometry, not four independent votes.
- State precisely **what M2 does not do**: no regime-split alpha, no time-varying
  beta, no conditional-return claim — only a static payoff-shape coefficient with an
  interval — and *why* (the down-beta arithmetic in derivation 2).
- Explain the honest-but-smooth confound and why de-smoothing first is the load-bearing
  false-alarm control — and quote the kill line (1-in-5 at T = 48) that decides whether
  the screen is signal or theater.

---

## Method review (2026-07-07) — APPROVED, implementation-ready

- **`M2_COMPOSITE_K`=3 CONFIRMED as provisional** — no independence assumption
  is needed because gate 1 measures the COMPOSITE's false-alarm rate directly
  on the simulator (correlation between diagnostics is priced empirically).
  The "converging evidence, not a p-value" framing is binding page copy.
- **HM treatment CONFIRMED:** the dual-beta fit is a static payoff-shape
  descriptor; rendering it as a conditional-alpha table is prohibited (do-not-
  build). The ~19-obs down-leg honesty stays on the sheet.
- **Sixth discriminant diagnostic RULED YAGNI:** de-smooth-first + the
  honest-but-smooth size axis is the design; a smoothing-vs-convexity
  discriminant is added ONLY if gate 1 fails on honest-smooth managers —
  recorded as a conditional extension, not built now.
- Overlay-dial fairness (`M2_OVERLAY_FAIR`), bands, K, and the 0.10/0.20
  false-alarm lines remain numerics-gate docket items.
