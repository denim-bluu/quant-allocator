# P1 · Allocation Under Alpha Uncertainty — Method Spec

**Status: Reviewed — method gate passed 2026-07-07 (rulings in §8)**
**Date:** 2026-07-07
**Card:** [`docs/ideas/2026-07-05-idea-cards.md`](../2026-07-05-idea-cards.md) § P1
**Extends:** [S1 · Hierarchical Bayesian alpha engine](s1-bayesian-alpha-engine.md) — P1 consumes S1's posterior *distributions*, never its point estimates alone
**Demo:** gallery page `p1.html` (advisory band chart on the certified S1 roster; §5)

---

## 1. What this is

P1 answers the question that follows immediately after S1: *given a posterior
belief about each manager's skill, how much capital does each one get?* The
S1 skill ledger ends with a per-manager posterior — a mean alpha, a posterior
standard deviation, a credible interval, a $P(\alpha > 0)$. P1 is the layer
that turns those posteriors into **advisory allocation bands**: for each
manager, a capital *range* ("this manager's evidence supports 4–10% of the
book"), not a single optimized weight. The band is computed by asking the
sizing rule not once but thousands of times — once per posterior draw — and
reporting the spread of answers. A manager whose skill is precisely estimated
gets a narrow band; a manager whose record is short and noisy gets a wide one.
**The width of the band is the honesty.**

The one thing P1 refuses to produce is the thing a textbook optimizer
produces: a single vector of "optimal" weights. That refusal is not modesty —
it is the method. A point-estimate optimizer fed noisy alphas is an
*estimation-error maximizer* (Michaud's phrase, unpacked in §2–§3): it
allocates most aggressively exactly where the inputs are most wrong. And it is
also the allocator's governance reality: capital moves through investment-
committee decisions, redemption terms, notice periods, and relationship
management — not through an auto-rebalancer. What the committee needs from the
quantitative layer is a defensible *range* and a flag when the current
allocation sits outside it. P1 delivers exactly that: per-manager bands, a
naive-optimizer contrast so the reader sees what the bands are protecting them
from, and a fund-or-not signal for the marginal names whose band floor sits at
zero.

The consumers are the **investment team** (the sizing memo per manager) and
**department leadership** (the roster allocation view). The decisions it
feeds are **size** (primary — how much capital, stated as a band) and
**redeem/re-up** (a manager whose band floor hits 0% is a name where funding
at all is genuinely open; a manager whose current weight exits their band is a
review trigger, with hysteresis so the trigger does not flap).

## 2. Why we use it

The decision problem: the roster has posterior skill estimates with honest
uncertainty attached, and capital must be divided. The default tool — plug
expected returns into a mean-variance optimizer (MVO) and read off the weights
— fails at this sample size, and it fails in a specifically treacherous way:
**the optimizer treats its inputs as exact, and it is most aggressive
precisely where the inputs are least reliable.**

The mechanism deserves to be stated plainly, because it is the single most
consequential fact about portfolio construction with estimated alphas. An
optimizer is a maximizer. Handed a cross-section of estimated alphas — each
one equal to true skill plus estimation noise — it loads up on the *largest*
estimates. But the largest estimates are disproportionately the ones whose
noise term happened to be positive: selecting on the maximum of noisy
estimates selects on the noise. The optimizer therefore systematically
overweights the overestimated and shorts or zeroes the underestimated, and its
promised portfolio alpha — computed from those same noisy inputs — is
biased upward exactly when its realized alpha is impaired. Michaud (1989)
named this behaviour: the MVO is an **estimation-error maximizer**. Best &
Grauer (1991) quantified the input sensitivity — tiny perturbations of the
mean vector produce violent reallocations, especially when assets are
correlated. Chopra & Ziemba (1993) sized the damage: at typical risk
tolerance, errors in *means* cost roughly **eleven times** as much realized
utility as errors in variances. The alpha vector is both the input the
optimizer is most sensitive to and — at 36–60 monthly observations — the input
we estimate worst. That combination is the disease.

Concretely (§3.2 works the arithmetic): two managers with 90% correlated
return streams and estimated alphas of 10% and 8% — a 2%/yr estimated edge
spread, well inside the noise at this sample size — drive an unconstrained MVO
to **+156% / −56%** of the book. And the sign of that 2% spread flips in
**41%** of posterior draws: the optimizer has taken a violent long/short
position on a coin flip.

The naive alternatives all fail for stated reasons. *Plug in the point alphas
anyway, add constraints*: constraints cap the damage (they are why real
portfolios do not literally short managers) but do not fix the ranking error —
the corner solutions the constrained optimizer picks are still driven by
noise, and the output still carries false precision, a single confident weight
per manager. *Use the S1 posterior means instead of OLS alphas*: strictly
better inputs — the means are already shrunk — but a bare point weight still
throws away the posterior's second moment; two managers with the same
posterior mean and very different posterior sds would get identical weights,
which wastes exactly the information S1 worked to produce (§5's matched pair
shows what honoring it buys). *Equal-weight everything*: the honest null, and
P1 keeps it as the benchmark the whole card must beat (§6.3) — but it ignores
skill evidence entirely, and when the posterior *does* separate managers,
leaving that information unused has a real opportunity cost. What the
posterior-draw band wins: it consumes the entire posterior — mean *and*
width — and returns an allocation statement whose confidence is calibrated to
the evidence, plus an explicit contrast showing what point-optimization would
have done.

- **Decisions improved:** **size** — capital bands proportionate to evidence,
  not to noise; **redeem/re-up** — band-floor-at-zero names and
  out-of-band current weights as calibrated review triggers with hysteresis.
- **Customer:** investment team (per-manager sizing memo); department
  leadership (roster allocation view).

## 3. How it works

### 3.1 The mental model, before any math

The posterior from S1 is a *set of plausible worlds*, not a number. In one
world drawn from the posterior, Ashfen's true alpha is 15% and Cinderbank's is
9%; in the next draw it is 8% and 14%. The point-optimizer's mistake is to
pick one world — the point estimate — and size as if it were certain. The fix
is almost embarrassingly direct: **run the sizing rule in every plausible
world, and look at the distribution of answers.** Draw an alpha vector from
the joint posterior, allocate under that draw, record the weights; repeat ten
thousand times. Each manager now has not a weight but a *distribution of
weights* — and the 10th-to-90th percentile of that distribution is the
advisory band.

The band has exactly the property an allocation statement should have. Where
the posterior is tight — long records, strong evidence — the sizing rule gives
nearly the same answer in every world, and the band is narrow: the evidence
*supports* a decisive allocation. Where the posterior is wide, the answers
disagree across worlds, and the band is wide: the honest statement is "the
evidence supports anything from 4% to 10%, and choosing within that range is
a judgement call, not a calculation." The band widens *mechanically* with
posterior width — no tuning parameter makes it honest; it inherits honesty
from S1.

This is Michaud's resampling insight with one upgrade. Michaud (1998)
resampled by parametric bootstrap around the *point* estimates — simulate data
from the estimates, re-estimate, re-optimize, average. We draw from the
**posterior** instead: S1 already did the hard inferential work of saying
which alpha vectors are plausible (with shrinkage, pooling, and honest
widths), so drawing from it is both statistically coherent (it is exactly the
Bayesian decision-theory object; Jorion 1986 and Scherer's critique of ad-hoc
resampling both point here) and free — the posterior is sitting in the
ledger.

One more piece of intuition before the formulas: even for a *single* manager
with no cross-sectional competition, uncertainty about skill should shrink the
bet. The classic Kelly bet size is edge over variance, $f = \mu/\sigma^2$. If
$\mu$ is not known but believed with posterior variance
$\sigma_\mu^2$, the growth-optimal bet against the *predictive* return
distribution inflates the denominator: $f = \mu/(\sigma^2 + \sigma_\mu^2)$.
Parameter uncertainty acts exactly like extra return variance, and the honest
bet is strictly smaller. §3.4 makes this precise; it is the same
"uncertainty consumes capital" mechanism that makes the bands widen.

### 3.2 A worked toy example

**The blow-up.** Two managers in the same strategy, annual residual vol
$\sigma = 10\%$ each, return correlation $\rho = 0.9$. Estimated (point)
alphas: $\hat\alpha_1 = 10\%$, $\hat\alpha_2 = 8\%$. The unconstrained MV tilt
is $\Sigma^{-1}\hat\alpha$ (§3.3); for equal vols this is proportional to

$$
\big(\hat\alpha_1 - \rho\,\hat\alpha_2,\;\; \hat\alpha_2 - \rho\,\hat\alpha_1\big)
= (0.10 - 0.9 \times 0.08,\;\; 0.08 - 0.9 \times 0.10)
= (0.028,\; -0.010).
$$

Normalizing to a fully invested budget: $0.028/0.018 = +1.556$ and
$-0.010/0.018 = -0.556$ — the optimizer puts **+156% of the book on manager 1
and −56% on manager 2**, on the strength of a 2-point alpha spread. Note what
the algebra just did: at high correlation the optimizer stops caring about the
alphas' *levels* and bets on their *difference*, levered up by
$1/(1-\rho^2)$ — and the difference of two noisy estimates is noisier than
either.

**Why that is indefensible.** Suppose each alpha carries a posterior sd of 6%
(typical for these sample sizes — compare the S1 ledger's posterior sds of
3–5% *after* shrinkage). Treating the two posteriors as independent, the
spread $\hat\alpha_1 - \hat\alpha_2 = 2\%$ has sd
$\sqrt{0.06^2 + 0.06^2} = 8.49\%$, so the probability the true spread has the
*opposite sign* is $\Phi(-0.02/0.0849) = \Phi(-0.236) \approx 41\%$. The
+156%/−56% position is a maximal-conviction bet on a proposition that is
41%-likely to be backwards. Re-run the same unconstrained optimizer across
posterior draws and the "answer" for manager 1's weight spans multiples of the
book in both directions — the honest summary of the unconstrained problem is
that *the data do not determine the weights at all*. Constraints (long-only,
budget, caps) are what make the resampled answer a usable object; §3.5–3.6
build exactly that.

**The single-bet shrink.** One edge, $\mu = 8\%$/yr on residual vol
$\sigma = 10\%$. Full Kelly says $f = 0.08/0.10^2 = 8.0$ — an absurd 8× levered
bet, which is the first lesson (Kelly's raw output at fund-level numbers is
never actionable; it is a *ceiling*, not a size). Now admit the posterior sd
on $\mu$ is 6%: $f = 0.08/(0.10^2 + 0.06^2) = 0.08/0.0136 = 5.88$ — parameter
uncertainty alone cuts the growth-optimal size by **26%**, before any
risk-aversion haircut. The house half-Kelly of the uncertainty-aware size is
$2.94$. Same direction as the bands: **uncertainty consumes capital.**

### 3.3 The disease made precise: MVO and error maximization

The textbook allocation. With expected excess returns (for us: alphas)
$\alpha$ and return covariance $\Sigma$ across $n$ managers, the unconstrained
mean-variance investor with risk aversion $\gamma$ holds

$$
w^* = \frac{1}{\gamma}\,\Sigma^{-1}\alpha
$$

where:

- $\alpha$ — the $n$-vector of true expected alphas (annualized decimals).
  The optimizer *assumes this is known*; in practice it receives an estimate
  $\hat\alpha = \alpha + \eta$ with estimation noise $\eta$.
- $\Sigma$ — the $n \times n$ covariance matrix of the managers' (residual)
  returns; $\Sigma^{-1}$ is its inverse.
- $\gamma$ — the investor's risk-aversion coefficient; it scales the overall
  gross but cancels once weights are normalized to a budget.
- $w^*$ — the optimal weight vector *if $\alpha$ and $\Sigma$ were known*.

In words: tilt toward high alpha, penalize variance, and — through
$\Sigma^{-1}$ — exploit correlations by pairing longs against shorts. Every
term of that sentence is correct at true parameters and dangerous at
estimated ones:

- **Selection on noise.** $w^*(\hat\alpha)$ loads on the largest entries of
  $\hat\alpha$; conditional on being largest, an estimate is biased upward
  ($\mathbb{E}[\eta_i \mid \hat\alpha_i \text{ ranked top}] > 0$). The
  portfolio concentrates in the names whose luck was best, and the in-sample
  portfolio alpha $\hat\alpha^\top w^*(\hat\alpha)$ overstates the
  achievable alpha — the optimizer *maximizes into the error*.
- **Correlation leverage.** As §3.2's closed form shows, for correlated
  assets the tilt is driven by alpha *differences* scaled by
  $1/(1-\rho^2)$: at $\rho = 0.9$ the optimizer bets 5.3× harder on the
  spread than an uncorrelated book would — and spreads of noisy estimates
  are the noisiest objects available.
- **The asymmetry of input errors.** Chopra & Ziemba (1993): the realized
  cash-equivalent loss from errors in means is roughly 11× the loss from
  errors in variances (≈2× for covariances) at conventional risk tolerance.
  The alpha vector is simultaneously the most damaging input to get wrong and
  the one with by far the widest error bars at $T \le 60$ (S1 §2: a true
  IR 0.5 gives $t \approx 1.1$ at $T = 60$).

This is why "get a better optimizer" is the wrong instinct. The solver is
fine; the *inputs are distributions, not points*, and the fix must consume
them as such. Two classical repairs exist: shrink the means before optimizing
(Jorion's Bayes–Stein; Black–Litterman's equilibrium anchor — and S1 has
already done this, better, with a hierarchical posterior), and propagate the
remaining uncertainty *through* the optimization (Michaud's resampling; the
Bayesian decision-theoretic version below). P1 is the second repair, applied
on top of the first: **S1 fixed the mean; P1 consumes the variance.**

### 3.4 Consuming the posterior, part I: uncertainty-shrunk sizing

The single-manager case makes the mechanism exact. Under the maintained model,
next period's return on manager $i$'s alpha stream is
$r_i = \alpha_i + \varepsilon_i$ with $\varepsilon_i \sim \mathcal N(0, \sigma_i^2)$,
and S1 delivers the posterior $\alpha_i \sim \mathcal N(m_i, s_i^2)$. The
*predictive* distribution of $r_i$ — integrating the posterior over
$\alpha_i$ — is then $\mathcal N(m_i,\; \sigma_i^2 + s_i^2)$, and the
growth-optimal (Kelly) or equivalently Bayes-mean-variance size against the
predictive distribution is

$$
f_i \;=\; \frac{m_i}{\sigma_i^2 + s_i^2}
\qquad\text{versus the plug-in}\qquad
f_i^{\text{plug}} \;=\; \frac{m_i}{\sigma_i^2}
$$

where:

- $m_i$ — manager $i$'s posterior mean alpha (S1's `posterior_alpha`).
- $s_i$ — manager $i$'s posterior standard deviation (S1's `posterior_sd`):
  how uncertain we remain about the true alpha after shrinkage.
- $\sigma_i$ — the residual (idiosyncratic) volatility of the manager's
  return stream: the risk that remains even if $\alpha_i$ were known.
- $f_i$ — the uncertainty-aware sizing fraction; $f_i^{\text{plug}}$ the one
  that pretends $s_i = 0$.

In words: **posterior variance enters the denominator on equal footing with
return variance.** Not knowing the edge is risk, and it is priced exactly like
risk. The ratio $f_i / f_i^{\text{plug}} = \sigma_i^2/(\sigma_i^2 + s_i^2)$ is
a shrinkage factor on *size*, the precise sizing analogue of S1's shrinkage
weight on *alpha* — the same $\text{signal}^2/(\text{signal}^2+\text{noise}^2)$
form, doing the same honest work one layer downstream. With §3.2's numbers
($\sigma = 10\%$, $s = 6\%$) the factor is $0.01/0.0136 = 0.74$: a 26% haircut
from parameter uncertainty alone.

Two practical notes. First, raw Kelly output is a *ceiling*: at fund-level
Sharpe ratios it prescribes multiple turns of leverage, so the house
convention is fractional Kelly (½ or less) *of the uncertainty-aware size*,
plus the hard governance cap of §3.6 — the fraction and cap are stated
controls, not hidden defaults. Second, this closed form is the intuition, not
the estimator: the roster problem is joint (managers compete for one budget,
under correlation and constraints), which closed forms do not survive. The
production estimator is the resampling of §3.5 — and the Kelly-fraction bound
survives *inside* it, as the per-draw sizing rule.

### 3.5 Consuming the posterior, part II: posterior-draw resampled allocation

The house estimator. Inputs: the S1 posterior per manager
$(m_i, s_i)$ for $i = 1 \dots n$, a residual-risk input $\sigma_i$ per
manager, and an allocation rule $\mathcal A$ (§3.6) mapping an alpha vector to
weights under the stated constraints. Algorithm:

1. **Draw** an alpha vector $\alpha^{(d)}$ from the joint posterior:
   $\alpha_i^{(d)} \sim \mathcal N(m_i, s_i^2)$, independently across managers
   in v1 (the closed-form S1 posteriors are independent given the group
   parameters; carrying the full joint posterior including group-level
   uncertainty is the live-build upgrade, noted in §6.4).
2. **Allocate** in that world: $w^{(d)} = \mathcal A(\alpha^{(d)})$.
3. **Repeat** for $d = 1 \dots N_{\text{draws}}$ and collect the per-manager
   weight distribution $\{w_i^{(d)}\}$.
4. **Report** per manager:

$$
\text{band}_i = \Big[\,Q_{10}\big(w_i^{(d)}\big),\; Q_{90}\big(w_i^{(d)}\big)\Big],
\qquad
\text{anchor}_i = \operatorname{median}\big(w_i^{(d)}\big),
\qquad
z_i = \Pr\big(w_i^{(d)} = 0\big)
$$

where:

- $Q_{10}, Q_{90}$ — the 10th and 90th percentiles across draws: the
  **advisory band**, the range of allocations the posterior evidence supports.
  (The 10/90 choice is **`P1_BAND_PCT` (provisional — see §6.4)**.)
- $\operatorname{median}(w_i^{(d)})$ — the band's **anchor**, the single most
  defensible summary if one number is demanded; rendered as a tick inside the
  band, never alone (Interval doctrine: no bare points).
- $z_i$ — the fraction of worlds in which the rule allocates manager $i$
  **nothing**. For long-only rules this is (approximately) the posterior
  probability the manager's alpha is not competitive-positive — the
  **fund-or-not signal**. A funded name with a 0% band floor and large $z_i$
  is a name where the honest statement is "funding at all is a judgement
  call," which is redeem/re-up-relevant information no point weight can carry.

In words: the band is the image of the posterior under the allocation rule.
Nothing about it is tuned to look honest; it is honest because the posterior
is, and it degrades gracefully — feed it a tighter posterior (longer record,
or a higher transparency tier via S1's Pástor–Stambaugh mechanism) and the
band narrows *mechanically*. This is the card's engagement argument made
quantitative: the value of transparency is measurable in band width — a
manager can be shown, in percentage points of the book, what tighter evidence
about their process would do to their allocation range (see §5's matched
pair for the arithmetic).

Why draws-from-the-posterior rather than Michaud's bootstrap: the bootstrap
resamples around the *point* estimates, so it inherits their bias (it
resamples the luck along with the skill); the posterior has already shrunk
the luck out (S1 §3), so its draws are centered on defensible beliefs. The
resampling insight is Michaud's; the input distribution is the upgrade.

### 3.6 The within-draw allocation rule (deliberately simple)

Each draw needs an allocation rule, and P1 v1 chooses the simplest rule that
is honest about its own assumptions — because §3.3's lesson is that
sophistication in the *solver* cannot rescue and can easily amplify noise in
the *inputs*:

$$
w_i \;\propto\; \frac{\max(0,\, \alpha_i^{(d)})}{\sigma_i^2},
\qquad
\sum_i w_i = 1,
\qquad
w_i \le c
$$

where:

- $\max(0, \alpha_i^{(d)})$ — the positive part of the drawn alpha: long-only
  (the allocator cannot short a manager; the worst available action is a
  weight of zero, i.e. redeem).
- $\sigma_i$ — residual annual volatility. The **demo** holds this constant
  across managers (**`P1_SIGMA_DEMO` = 0.08 — provisional, §6.4**) so that
  band differences are driven *purely* by the posteriors — the variable the
  card is about. The **live** build uses each manager's de-smoothed residual
  vol from the S2 pipeline.
- $\sum_i w_i = 1$ — fully invested across the roster (the demo's framing;
  a cash/unallocated sleeve is a live-build policy choice).
- $c$ — a per-manager governance cap (**`P1_ALLOC_CAP` = 0.20 — provisional,
  §6.4**), applied by capping and redistributing the excess pro-rata to
  uncapped names.

In words: within one drawn world, weight is edge over variance — the Kelly
direction of §3.4 — normalized to the budget, floored at zero, capped by
governance. What v1 deliberately omits: the off-diagonal of $\Sigma$. A full
$\Sigma^{-1}$ inside each draw would re-introduce exactly the correlation-
levered spread bets §3.2 dissected, now at roster scale, and estimated
manager-level correlations at $T \le 60$ are themselves noisy inputs. The
diagonal rule is the right v1 level; the live path to correlation-awareness is
stated in §6.6 — factor-risk contributions from the house risk model at tier E
(buy-the-risk-model doctrine) and **skfolio/Riskfolio backends** for any
genuine optimization (convergence §4: build on OSS solvers, never rebuild
them). Cross-manager overlap and crowding caps are card M4's job, not a
correlation matrix smuggled in here.

**Relation to S1's advisory pills.** S1 §3.9 maps each manager's posterior
t-ratio to a coarse band label (review/minimum/standard/conviction) —
absolute, per-manager, roster-blind. P1's bands are the roster-aware
refinement: a manager's capital range depends on who else is on the roster and
how strong *their* evidence is, because allocation is a relative decision
under a budget. The pills survive as labels on the P1 chart; the bands carry
the capital numbers.

### 3.7 Acting on bands: the sizing memo and the hysteresis rule

A band is only useful if the actions it licenses are stated. Three, all
advisory:

- **Inside the band** — no action. The current weight is consistent with the
  evidence; re-papering allocations inside the band is churn, and the band's
  width is an explicit turnover damper (wider evidence ⇒ fewer moves).
- **Current weight outside the band** — a *sizing review trigger*, with
  hysteresis borrowed from M3's Schmitt-trigger discipline: trigger when the
  weight exits the 10–90 band, clear only when it re-enters the *inner*
  25–75 band (**`P1_HYSTERESIS_BANDS` (provisional — trigger 10/90, clear
  25/75)**), so a weight hovering at the band edge does not flap the memo.
- **Band floor at 0% with material $z_i$** — the fund-or-not conversation:
  the evidence cannot rule out that this manager deserves nothing. Routed to
  the redeem/re-up review alongside M3's drawdown alarm and S2's alt-beta
  chip; **never** a mechanical redemption (card kill criterion, §6.5).

The memo's copy discipline follows Sweep E: the band is presented as *the
range the evidence supports* — an input to the committee's judgement with the
skepticism dial exposed (§6.7) — never as "the model says 7.4%."

### 3.8 What the canonical papers showed

- **Michaud (1989), "The Markowitz Optimization Enigma: Is 'Optimized'
  Optimal?" (*Financial Analysts Journal*).** Named the disease: fed estimated
  inputs, the mean-variance optimizer acts as an "estimation-error maximizer,"
  loading on the assets whose expected returns are most overestimated and
  producing extreme, unstable, poorly-performing portfolios. P1's §2–§3.3 are
  this argument, worked with our numbers; the card exists because the naive
  path S1's posteriors seem to invite — "great, now optimize" — is exactly
  Michaud's trap.
- **Best & Grauer (1991, *Review of Financial Studies*).** Derived the
  sensitivity of MV weights to mean perturbations analytically and showed the
  weights of correlated assets respond explosively to tiny mean changes while
  the portfolio's expected utility barely moves — the flat-objective /
  violent-weights geometry. This is why reporting *weight bands* rather than
  the argmax is not a loss of information: near the optimum, huge weight
  regions are utility-equivalent, and the point optimizer's precision is fake.
- **Chopra & Ziemba (1993, *Journal of Portfolio Management*).** Measured the
  realized cash-equivalent damage from input errors: means matter ≈11× more
  than variances (≈2× covariances) at conventional risk tolerance. This
  ordering justifies P1's design allocation: all the uncertainty machinery is
  spent on the alpha vector (posterior draws), while risk inputs enter as
  plug-ins in v1 (§6.4 flags the upgrade).
- **Jorion (1986, *Journal of Financial and Quantitative Analysis*),
  "Bayes–Stein Estimation for Portfolio Analysis."** Showed that shrinking
  estimated means toward a grand mean before optimizing dominates plug-in MVO
  out of sample — the first half of the P1+S1 pipeline, established in the
  portfolio context. S1's hierarchical posterior is the modern, uncertainty-
  carrying version of Jorion's shrinkage; P1 is what Jorion's investor still
  needed next: a way to keep the *remaining* uncertainty in the weights.
- **Michaud (1998), *Efficient Asset Management*.** The resampling repair:
  simulate many input vectors consistent with estimation error, optimize in
  each, and study the distribution of portfolios. P1 keeps the architecture
  and swaps the input distribution — posterior draws instead of bootstrap
  around points (§3.5) — which answers the standard critique (resampling around
  biased points propagates the bias) by resampling from a shrunk, calibrated
  belief instead.
- **MacLean, Thorp & Ziemba (2011), *The Kelly Capital Growth Investment
  Criterion*.** The growth-optimal sizing tradition: full Kelly maximizes
  long-run growth but with brutal drawdowns, fractional Kelly trades growth
  for safety, and — the piece P1 leans on — under parameter uncertainty the
  effective edge shrinks and the honest bet shrinks with it (§3.4's
  denominator inflation). Kelly is used as a *ceiling and a direction*, never
  as a prescribed size.

## 4. How to implement

The reference implementation below is **self-contained teaching code** — paste
it into a fresh file; it runs on `numpy` and the standard library alone, with
no project imports. Part A reproduces §3.2's blow-up, part B reproduces §3.4's
uncertainty-aware sizing, and part C computes the §5 demo's actual numbers:
the certified S1 posteriors (transcribed as literals from
`site/data/s1_ledger.json`) pushed through the posterior-draw band machinery
of §3.5–3.6. Every number quoted in this spec is printed by this script.

```python
"""Allocation under alpha uncertainty (P1 method spec) — teaching code.

Self-contained: numpy + stdlib only, no project imports. Three parts:
  A. Why point-estimate optimization explodes (estimation-error maximization).
  B. How consuming the posterior variance shrinks a single bet (Kelly / Bayes-MV).
  C. Posterior-draw resampling -> per-manager advisory weight BANDS on a roster,
     against the naive point-optimized weights, both raw-OLS and posterior-mean.
Run it and the printed numbers are exactly those cited in the spec text.
"""
import math

import numpy as np

# ---------------------------------------------------------------------------
# A. The estimation-error-maximization blow-up (Michaud's critique, concrete).
#    Two highly correlated managers; a 2%/yr estimated edge spread is well
#    inside the noise, yet unconstrained mean-variance takes a violent
#    long/short position on it.
# ---------------------------------------------------------------------------
def mv_budget1(alpha, cov):
    """Unconstrained MV tilt Sigma^{-1} alpha, normalized to a fully-invested
    budget (weights sum to 1). Risk aversion cancels under the normalization;
    shorts are allowed so the blow-up is visible."""
    raw = np.linalg.solve(cov, alpha)
    return raw / raw.sum()

sig, rho = 0.10, 0.90
cov = np.array([[sig**2, rho*sig*sig], [rho*sig*sig, sig**2]])
alpha_point = np.array([0.10, 0.08])                 # a 2%/yr estimated spread
w = mv_budget1(alpha_point, cov)
sd_spread = math.hypot(0.06, 0.06)                   # each posterior sd = 6%/yr
p_flip = 0.5 * (1.0 - math.erf((0.02 / sd_spread) / math.sqrt(2)))
print("A. point-MVO on a 2%% spread  -> %.0f%% / %.0f%%   "
      "(the spread's sign flips in %.0f%% of posterior draws)"
      % (w[0]*100, w[1]*100, p_flip*100))

# ---------------------------------------------------------------------------
# B. Consuming the posterior variance: full-Kelly vs uncertainty-aware size.
#    Full Kelly f = mu/sigma^2 assumes mu is known. Under a posterior on mu
#    with variance var_mu, the growth-optimal / Bayes-MV size inflates the
#    denominator by var_mu -> a strictly smaller bet.
# ---------------------------------------------------------------------------
mu, sigma_r, var_mu = 0.08, 0.10, 0.06**2
f_full = mu / sigma_r**2
f_unc = mu / (sigma_r**2 + var_mu)
print("B. full-Kelly f=%.2f  ->  uncertainty-aware f=%.2f  (-%.0f%%);  "
      "half-Kelly of that = %.2f"
      % (f_full, f_unc, (1 - f_unc/f_full)*100, 0.5*f_unc))

# ---------------------------------------------------------------------------
# C. Posterior-draw resampling on a roster -> advisory weight bands.
#    (code, months, ols_alpha, posterior_mean, posterior_sd) transcribed from
#    the certified S1 ledger (site/data/s1_ledger.json). Diagonal risk with a
#    CONSTANT idiosyncratic vol, so band width is driven purely by
#    posterior-alpha uncertainty (the card's thesis).
# ---------------------------------------------------------------------------
LEDGER = [
    # code  months  ols_alpha  post_mean  post_sd   (annualized decimals)
    ("A01", 36, -0.0742, -0.0405, 0.0481),
    ("A02", 48, +0.0029, +0.0147, 0.0389),
    ("A03", 60, +0.0262, +0.0357, 0.0407),
    ("A04", 36, +0.0013, +0.0212, 0.0501),
    ("A05", 48, +0.0196, +0.0329, 0.0459),
    ("A06", 60, +0.1194, +0.1163, 0.0356),
    ("A07", 36, +0.1773, +0.1632, 0.0434),
    ("A08", 48, +0.2347, +0.2143, 0.0404),
    ("A09", 60, +0.1159, +0.1132, 0.0354),
    ("A10", 36, +0.2929, +0.2543, 0.0468),
    ("B01", 36, -0.0353, +0.0110, 0.0366),
    ("B02", 48, +0.0588, +0.0658, 0.0344),
    ("B03", 60, -0.0010, +0.0259, 0.0334),
    ("B04", 36, +0.0595, +0.0671, 0.0367),
    ("B05", 48, +0.0116, +0.0406, 0.0378),
    ("B06", 60, +0.0811, +0.0802, 0.0314),
    ("B07", 36, +0.1573, +0.1193, 0.0396),
    ("B08", 48, +0.1151, +0.1023, 0.0336),
    ("B09", 60, +0.1374, +0.1192, 0.0317),
    ("B10", 36, +0.1960, +0.1321, 0.0421),
]
codes = [r[0] for r in LEDGER]
ols = np.array([r[2] for r in LEDGER])
means = np.array([r[3] for r in LEDGER])
sds = np.array([r[4] for r in LEDGER])

SIGMA_DEMO = 0.08          # constant idiosyncratic annual vol (demo assumption)
CAP_DEMO = 0.20            # per-manager governance cap
N_DRAWS = 50_000           # posterior draws behind the bands
BAND_PCT = (10, 90)        # advisory band = these percentiles of the weight draws

def allocate(alpha, sigma=SIGMA_DEMO, cap=CAP_DEMO):
    """Long-only, fully-invested diagonal MV/Kelly tilt: weight proportional
    to the positive part of alpha over variance, capped and renormalized."""
    score = np.maximum(0.0, alpha) / sigma**2
    if score.sum() == 0:
        return np.zeros_like(alpha)
    w = score / score.sum()
    for _ in range(50):                    # cap-and-redistribute passes
        over = w > cap
        if not over.any():
            break
        excess = (w[over] - cap).sum()
        w[over] = cap
        under = ~over & (w > 0)
        if not under.any():
            break
        w[under] += excess * w[under] / w[under].sum()
    return w

w_ols = allocate(ols)                      # naive: raw OLS points -> one weight
w_post = allocate(means)                   # better mean, still a bare point
rng = np.random.default_rng(70707)
draws = rng.normal(means, sds, size=(N_DRAWS, len(codes)))
W = np.array([allocate(draws[d]) for d in range(N_DRAWS)])
w_med = np.median(W, axis=0)
lo, hi = np.percentile(W, BAND_PCT, axis=0)

print("\nC. naive point weights vs posterior-draw advisory bands:")
print("   code  mo   ols_a   post_a   sd     w_ols  w_post  floor   med    ceil  width")
for i in np.argsort(-w_med):
    print("   %-4s %3d %+7.4f %+7.4f %.4f  %5.1f%% %5.1f%%  %5.1f%% %5.1f%% %5.1f%%  %4.1fpp"
          % (codes[i], LEDGER[i][1], ols[i], means[i], sds[i], w_ols[i]*100,
             w_post[i]*100, lo[i]*100, w_med[i]*100, hi[i]*100, (hi[i]-lo[i])*100))

i10 = codes.index("B10")
print("\n   B10 headline: OLS-point weight %.1f%% sits ABOVE its whole honest band "
      "[%.1f%%, %.1f%%]" % (w_ols[i10]*100, lo[i10]*100, hi[i10]*100))
print("   top-3 concentration: OLS-naive %.1f%% vs posterior-median %.1f%%"
      % (np.sort(w_ols)[::-1][:3].sum()*100, np.sort(w_med)[::-1][:3].sum()*100))
funded = w_med > 0.005
print("   corr(band width, posterior sd) over %d funded names = %.2f"
      % (funded.sum(), np.corrcoef((hi - lo)[funded], sds[funded])[0, 1]))
for c in ("B09", "B07"):                   # same skill estimate, 60m vs 36m record
    i = codes.index(c)
    print("   matched pair %s (%dm, sd %.4f): floor %.1f%%  med %.1f%%  ceil %.1f%%  "
          "width %.1fpp" % (c, LEDGER[i][1], sds[i], lo[i]*100, w_med[i]*100,
                            hi[i]*100, (hi[i]-lo[i])*100))
pzero = (W == 0).mean(axis=0)
marginal = [codes[i] for i in range(len(codes)) if 0.10 < pzero[i] < 0.99 and means[i] > 0]
print("   funded names whose band floor is 0% (fund-or-not is genuinely open): "
      + ", ".join(marginal))
```

Executed output (verbatim; the seed is fixed, so it reproduces):

```text
A. point-MVO on a 2% spread  -> 156% / -56%   (the spread's sign flips in 41% of posterior draws)
B. full-Kelly f=8.00  ->  uncertainty-aware f=5.88  (-26%);  half-Kelly of that = 2.94

C. naive point weights vs posterior-draw advisory bands:
   code  mo   ols_a   post_a   sd     w_ols  w_post  floor   med    ceil  width
   A10   36 +0.2929 +0.2543 0.0468   16.2%  14.7%   11.0%  14.3%  17.6%   6.6pp
   A08   48 +0.2347 +0.2143 0.0404   13.0%  12.4%    9.2%  12.0%  15.0%   5.8pp
   A07   36 +0.1773 +0.1632 0.0434    9.8%   9.4%    6.2%   9.2%  12.2%   6.0pp
   B10   36 +0.1960 +0.1321 0.0421   10.8%   7.6%    4.5%   7.4%  10.4%   5.8pp
   B09   60 +0.1374 +0.1192 0.0317    7.6%   6.9%    4.5%   6.7%   9.0%   4.5pp
   B07   36 +0.1573 +0.1193 0.0396    8.7%   6.9%    3.9%   6.7%   9.4%   5.5pp
   A06   60 +0.1194 +0.1163 0.0356    6.6%   6.7%    4.0%   6.5%   9.1%   5.1pp
   A09   60 +0.1159 +0.1132 0.0354    6.4%   6.5%    3.9%   6.3%   8.9%   5.0pp
   B08   48 +0.1151 +0.1023 0.0336    6.4%   5.9%    3.4%   5.7%   8.1%   4.8pp
   B06   60 +0.0811 +0.0802 0.0314    4.5%   4.6%    2.3%   4.5%   6.7%   4.5pp
   B04   36 +0.0595 +0.0671 0.0367    3.3%   3.9%    1.2%   3.8%   6.3%   5.2pp
   B02   48 +0.0588 +0.0658 0.0344    3.3%   3.8%    1.2%   3.7%   6.1%   4.9pp
   B05   48 +0.0116 +0.0406 0.0378    0.6%   2.3%    0.0%   2.3%   4.9%   4.9pp
   A03   60 +0.0262 +0.0357 0.0407    1.4%   2.1%    0.0%   2.0%   4.9%   4.9pp
   A05   48 +0.0196 +0.0329 0.0459    1.1%   1.9%    0.0%   1.9%   5.0%   5.0pp
   B03   60 -0.0010 +0.0259 0.0334    0.0%   1.5%    0.0%   1.5%   3.8%   3.8pp
   A04   36 +0.0013 +0.0212 0.0501    0.1%   1.2%    0.0%   1.2%   4.7%   4.7pp
   A02   48 +0.0029 +0.0147 0.0389    0.2%   0.9%    0.0%   0.8%   3.5%   3.5pp
   B01   36 -0.0353 +0.0110 0.0366    0.0%   0.6%    0.0%   0.6%   3.2%   3.2pp
   A01   36 -0.0742 -0.0405 0.0481    0.0%   0.0%    0.0%   0.0%   1.2%   1.2pp

   B10 headline: OLS-point weight 10.8% sits ABOVE its whole honest band [4.5%, 10.4%]
   top-3 concentration: OLS-naive 40.0% vs posterior-median 35.5%
   corr(band width, posterior sd) over 19 funded names = 0.48
   matched pair B09 (60m, sd 0.0317): floor 4.5%  med 6.7%  ceil 9.0%  width 4.5pp
   matched pair B07 (36m, sd 0.0396): floor 3.9%  med 6.7%  ceil 9.4%  width 5.5pp
   funded names whose band floor is 0% (fund-or-not is genuinely open): A02, A03, A04, A05, B01, B03, B05
```

Implementation notes on the loop: the cap-and-redistribute pass is a fixed-
point iteration (cap the over-cap names, hand the excess pro-rata to the
rest); it converges in a handful of passes because each pass strictly grows
the capped set, and the 50-pass bound is a safety rail, not a tuning knob. The
`N_DRAWS = 50,000` run completes in seconds; band Monte-Carlo error at the
10th/90th percentile is well under 0.1pp at that draw count.

## 5. Reading the demo

> Generator-reconciled 2026-07-07: B10 band ceiling 10.4% -> 10.3% and top-3
> band-anchor concentration 35.5% -> 35.4% (MC-seed convention differs from §4
> teaching code — house seed `[P1_SEED, P1_DRAW_STREAM]` with `standard_normal`
> vs §4's `70707`/`normal(means, sds)`; verify at the numerics gate).

The gallery page `p1.html` is a **band chart** on the S1 roster — the same 20
synthetic managers, in the same certified numbers, one step further down the
decision pipeline (the page states: "posteriors from the S1 skill ledger;
this page decides *how much*, that page decided *how good*"). One row per
manager, ordered by band anchor. Each row shows:

- **The advisory band** — a horizontal bar from the 10th to the 90th
  percentile of the manager's weight draws, with the median as the tick
  inside it (an IntervalStat; no bare points).
- **The naive point weight** — a contrasting marker (distinct shape, "point
  optimizer" in the legend) showing the weight a point-estimate allocation on
  **raw OLS alphas** would assign. **The contrast is the exhibit**: where the
  marker sits relative to the band is a per-manager verdict on the naive
  method.
- **The S1 carryovers** — the advisory-band pill (review/minimum/standard/
  conviction) and $P(\alpha > 0)$, so the page reads as the ledger's sequel.
- **A "fund-or-not" chip** on names whose band floor is 0%.

**The headline row.** Cinderbank Capital (B10) — S1's exemplar of a lucky
36-month record — gets **10.8%** of the book from the point optimizer, riding
its raw +19.6% OLS alpha. Its honest band is **[4.5%, 10.3%]**: the naive
weight sits *above the entire range* the posterior evidence supports. The
point optimizer did not just miss the anchor (7.4%); it left the defensible
region altogether, and it did so on the roster's noisiest flattering estimate
— §3.3's selection-on-noise mechanism, visible in one row. Across the top of
the book the same tilt shows up in aggregate: the top-3 concentration is
40.0% under the point optimizer versus 35.4% at the band anchors, with the
excess parked in exactly the short-record names.

**The matched pair — what evidence width is worth in capital.** Petrelwood
Partners (B09, 60 months) and Ashfen Advisors (B07, 36 months) have
*indistinguishable* posterior mean alphas (+11.9%). A point weight — even one
computed from the posterior means — would size them identically. The bands do
not: B09's tighter posterior (sd 3.2% vs 4.0%) earns a **floor of 4.5% vs
3.9%** and a **width of 4.5pp vs 5.5pp**. Same estimated skill, different
strength of evidence, different capital statement. This pair is also the
transparency-value argument in miniature: tightening a manager's posterior sd
by 0.8 points — whether by two more years of track or by the tier-E exposure
transparency that sharpens S1's inference (S1 §3.5) — raises the allocation
floor and narrows the range. The ask ("give us exposure data") now has a
price tag in percentage points of the book.

**The marginal names.** Seven funded managers — A02, A03, A04, A05, B01, B03,
B05 — carry a band floor of exactly **0%**: in a nontrivial fraction of
posterior draws the rule allocates them nothing. The page renders these with
the fund-or-not chip and copy that says what it means: *the evidence is
consistent both with a small allocation and with none; this is a judgement
call, and the chart is telling you so rather than hiding it behind a
confident 1.5%.* Note what the point optimizer does with the same names: it
prints 0.1% or 0.6% — allocations with two significant figures and no
significance.

**How band width tracks evidence.** Across the 19 funded names, band width
correlates 0.48 with posterior sd — visibly imperfect, and the page says why
rather than letting the reader assume noise: width in a *budgeted, capped*
allocation also responds to weight level and to competition from
similar-alpha neighbours (a name in a crowded part of the alpha ordering
swings more between draws). The mechanism is cleanest in the matched pair,
which holds everything else fixed.

**Demo-vs-live split (stated on the page).** SYNTHETIC badge: all inputs are
the certified S1 ledger posteriors on the simulator roster. The demo's
residual vol is a constant `P1_SIGMA_DEMO = 0.08` for every manager — chosen
so band differences are attributable purely to the posteriors — and the demo
draws treat manager posteriors as independent. The live build swaps in
per-manager de-smoothed vols (S2 pipeline) and the full joint posterior
(S1 MCMC draws), and adds the policy-regret evidence of §6.3. No interaction
beyond the standard skepticism dial (§6.7); the chart is the argument.

**What an allocator should conclude:** sizing to the point-optimized column
would concentrate the book in the shortest, luckiest records and would state
false precision on names whose funding is genuinely undecided. The bands
allocate the same budget with the confidence calibrated to the evidence — and
where they are wide, that width *is the finding*, not a failure to conclude.

## 6. Honest limits & go-live

### 6.1 What P1 does not do (do-not-build and buy-verdict adjacency)

- **No optimal-weight product.** The output is advisory bands and review
  triggers; there is no auto-rebalancer, no target-weight file, and no claim
  that any point inside the band is "the" answer. Sizing recommendations are
  advisory bands routed to the committee — the card's political kill
  criterion, restated as scope.
- **No solver rebuild.** Any live-build constrained optimization inside draws
  runs on **skfolio/Riskfolio** backends (convergence §4: buy, don't build).
  v1's within-draw rule (§3.6) is deliberately closed-form.
- **No estimated manager-correlation matrix in v1.** §3.2 is the reason;
  correlation-aware risk enters at tier E via the house factor risk model
  (buy-the-risk-model doctrine), and cross-manager overlap/crowding caps are
  card **M4**, consumed as constraints when both cards are live.
- **No persistence tests, no FDR luck-screens, no regime-split or
  conditional-beta alphas** (do-not-build list, convergence §4). P1 takes
  the S1 posterior as *the* skill statement — it does not re-test, re-screen,
  or regime-condition it. The alpha draws are i.i.d.-across-time by
  assumption; timing allocation to regimes is out of scope everywhere in the
  program.
- **No fee/liquidity optimization in v1.** Netting fees, gates, and notice
  periods into the sizing rule is a live-build extension named in §6.6;
  the demo states its absence.

### 6.2 Data contract per tier

P1 adds **no data requirement of its own** beyond S1's: it is tier-agnostic
once posteriors exist. The tier column below is therefore inherited — what
each rung buys P1 is a tighter posterior, which the band machinery converts
mechanically into capital terms.

| Tier | Inputs (via S1) | What it buys P1 |
| --- | --- | --- |
| **R** (minimum) | S1 run on monthly net returns (S1 §6.1: ≥24m to enter, ≥36m full standing, strategy labels, factor sets, risk-free) + a residual-vol input per manager (de-smoothed, S2 stage 1) | The full band chart for every manager. Bands are wide in proportion to R-tier posterior width — honestly. |
| **E** | S1's tier-E rung: measured exposures pin betas, shrinking posterior alpha sd (Pástor–Stambaugh, S1 §3.5); stated vol targets refine $\sigma_i$ | **Narrower bands and higher floors** for the same manager — the transparency dividend, quantifiable per manager in pp of the book (§5 matched pair). This is the novel engagement number: "exposure transparency moves your band from x–y% to x′–y′%." |
| **P** | S1's tier-P prior adjustment (breadth/IC where measurable); formal fusion is card P2 | Further posterior tightening where S1 admits it; P1 itself consumes only the posterior, so it upgrades automatically when P2 lands. |

Frequency: bands are recomputed at S1's cadence (monthly ledger refresh);
the hysteresis rule (§3.7) governs when a recomputed band produces an action.
A manager excluded by S1's data gates has no posterior and gets **no band** —
the page shows the S1 exclusion flag, not a guess.

### 6.3 Power & validation plan (the economic test)

P1's inference is S1's, already validated (S1 §6.2: coverage, rank recovery,
calibration). What P1 must validate is **economic**: does the posterior-band
policy actually allocate better than the alternatives, in worlds where the
truth is known? The card is explicit about the bar: *if equal-weight ties,
that finding is itself decision-grade — and cheaper.*

**The many-worlds policy-regret study.** On the simulator (existing dials
only — no new simulator dial is needed): draw a world = a roster with known
true alphas from a stated dispersion; emit $T$ months of returns; run S1;
form three policies — (i) **point-MVO** on raw OLS alphas, (ii)
**posterior-band anchors** (the P1 policy), (iii) **equal-weight** — under
identical constraints (long-only, budget, `P1_ALLOC_CAP`); score each policy's
**realized certainty-equivalent utility at the true parameters**; repeat
≥1,000 seeded worlds per cell (per-module RNG streams, X1 conventions,
Wilson intervals on rates). Grid, as X1 atlas cells (the card's named
"policy-regret grid"): $T \in \{36, 48, 60\}$ × roster size
$\{10, 20, 40\}$ × true annualized skill dispersion $\{1\%, 2\%, 4\%\}$ —
matching S1's validation grid so the posterior inputs carry known quality
into the policy layer.

Acceptance gates:

1. **Beat the point optimizer (the exhibit's claim).** The posterior policy's
   realized-utility distribution dominates point-MVO's in mean *and* in left
   tail (the fat left tail of noise-chasing is the card's wow-chart) across
   all cells with dispersion ≥2%.
2. **Beat or honestly tie equal-weight (the kill gate).** If the posterior
   policy fails to beat equal-weight across the realistic-dispersion cells,
   **publish that result and kill the tilt** — the bands survive as
   uncertainty communication around an equal-weight anchor, and the finding
   ("at this roster size and record length, skill evidence is too thin to
   size on") becomes the deliverable. This is the card's stated kill
   criterion, and the X1 atlas rows either side of the boundary show *where*
   sizing-on-evidence starts to pay.
3. **Band calibration.** Across worlds, the realized frequency with which the
   (constrained-)optimal-at-truth weight falls inside each manager's stated
   10–90 band is within ±5pp of 80%. A band that does not contain the truth
   at its stated rate is miscalibrated decoration — same standard S1 holds
   its credible intervals to.
4. **Action-rule economics.** The hysteresis rule (§3.7) is scored on
   turnover versus regret against always-rebalance-to-anchor: the band must
   demonstrably buy fewer moves at negligible utility cost, or the
   band-exit trigger thresholds are retuned at the gate.

**Power statement (X1-grounded).** The policy-regret margin shrinks with
dispersion and $T$: at 1% true dispersion and $T = 36$ the S1 posterior
barely separates managers (S1 §6.2's honest low-dispersion cells), so gate 2
is *expected* to produce ties there — the atlas cell then says so, and the
PowerGate on the live page refuses decisive bands in that regime rather than
manufacturing them.

### 6.4 Provisional constants (NUMERICS-GATE)

Every constant below is provisional and named for the numerics gate:

- **`P1_SIGMA_DEMO` = 0.08** — the demo's constant residual annual vol
  (isolates posterior-driven band differences). Live: per-manager de-smoothed
  vol. Gate question: does the demo's constant-vol simplification mislead
  next to the live behaviour, or is it the cleaner teaching exhibit?
- **`P1_ALLOC_CAP` = 0.20** — per-manager cap in the within-draw rule.
  A governance-policy stand-in; the gate confirms the demo value and the live
  default.
- **`P1_N_DRAWS` = 50,000** — posterior draws behind the bands (demo uses the
  closed-form posterior, so draws are cheap; live MCMC draws may be fewer —
  4,000 from S1's sampler — with the band's MC error restated).
- **`P1_BAND_PCT` = (10, 90)** — the advisory band's percentiles. The gate
  rules whether 10/90 (the demo) or a wider 5/95 is the house advisory range,
  and whether the inner clear-band for hysteresis is 25/75
  (**`P1_HYSTERESIS_BANDS`**).
- **`P1_KELLY_FRACTION` = 0.5** — the fractional-Kelly ceiling multiplier
  referenced in §3.4 for any live gross-sizing use; v1's budgeted rule does
  not lever, so this binds only extensions.
- **Independence of posterior draws across managers (v1)** — flagged as a
  structural provisional: the closed-form S1 posteriors are conditionally
  independent, but group-level uncertainty ($\mu_s, \tau_s$) induces positive
  dependence the live joint-posterior draws will carry. Gate question: how
  much do the demo bands narrow versus joint draws? (Expected direction:
  joint draws *widen* bands slightly, since group-mean uncertainty moves
  peers together.)

### 6.5 Kill criteria

- **Statistical/economic.** Gate 2 of §6.3: posterior policy ≤ equal-weight
  across the realistic grid ⇒ kill the tilt, keep the bands as communication,
  publish the negative result (it is decision-grade: "stop paying for sizing
  models at this N"). Gate 3 failure (miscalibrated bands) ⇒ the bands do not
  ship; interval-only reporting via S1/S2 stands.
- **Upstream.** If S1 reports "prior-dominated at this sample" (S1 §3.6's
  sensitivity kill), P1 has no defensible input and the band chart renders
  S1's refusal, not bands — the PowerGate doing its job one layer downstream.
- **Political.** Bands are advisory. If any consumer wires band boundaries to
  mechanical trades or mechanical redemptions, the card is pulled (Goodhart:
  a band published as a trading rule gets managed-to). The sizing memo's copy
  is help-framed and the skepticism dial stays visible.

### 6.6 How it ships in the repo

Consumes, by name (reuse, never reimplement):

- **`src/quant_allocator/flagships/skill_ledger/empirical.py`** — the S1
  closed-form posterior: `shrink_alphas(...) -> ShrinkageResult`, of which P1
  consumes `posterior_alpha` and `posterior_sd` (and `posterior_t_ratio` for
  the carried pill labels via `advisory_band`). **Import, do not re-fit.**
- **`site/data/s1_ledger.json`** — the certified S1 demo numbers; the P1 demo
  generator reads the posteriors from the same roster build rather than
  re-deriving them, so the two pages can never disagree.
- **`src/quant_allocator/demo_data/roster.py`** — the shared synthetic
  roster (codes, names, groups, record lengths).
- **The simulator (`simulator/manager.py`, existing dials)** — the §6.3
  many-worlds study runs on current machinery; **no new simulator dial is
  required** (the study varies dispersion and $T$, both existing axes).
- **X1 grid machinery (`demo_data/x_grid.py`, `x_metrics.py`)** — the
  policy-regret grid runs as X1 cells with the house seeding/interval
  conventions; results feed the atlas.

New code:

- **`src/quant_allocator/flagships/allocation/pipeline.py`** — pure functions:
  `allocate_one_draw(alphas, sigmas, cap) -> weights` (§3.6),
  `band_from_posterior(post_mean, post_sd, sigmas, config) -> AllocationBands`
  (§3.5: draws, bands, anchors, $z_i$), and
  `band_action(current_weight, bands, prev_state) -> BandAction` (§3.7
  hysteresis). No rendering, no I/O; config dataclass carries every §6.4
  constant as a named field.
- **`src/quant_allocator/demo_data/p1_allocation.py`** — imports the pipeline
  and the S1 roster/posteriors, emits `site/data/p1_allocation.json` via
  `_emit.write_json`; **CI renders the page from that JSON only — CI never
  computes** (demo-layer doctrine). Numbers held for the numerics gate before
  publish, per house rule.
- **Dependencies:** numpy only for demo and v1 pipeline. skfolio/Riskfolio
  enter only if a post-gate live build adds constrained optimization inside
  draws; fee/liquidity terms and M4 crowding caps are named extensions, not
  v1.
- **Effort:** demo + spec **S** on this substrate (the heavy lifting was
  S1's); the policy-regret study **M** (it is a full X1-style grid); card
  total M–L matches the card sheet, with the study as the bulk.

### 6.7 Adoption & packaging

- **The sizing memo, not a dashboard.** P1 output lands as a section of the
  per-manager pack (E2 composition) and a one-page roster view at allocation-
  review cadence — delivered at the decision moment, no standing screen.
- **Bands as negotiating range.** Committee copy: "the evidence supports
  4–10%; where we sit inside that range is our call — here is what would
  narrow it." The band explicitly leaves room for the qualitative factors the
  committee actually debates, which is why it survives contact with
  governance where an "optimal 7.4%" would not.
- **The Dietvorst dial.** The skepticism control from S1 carries through: the
  $\tau$-prior scale dial re-widens the posteriors and the bands respond live
  (precomputed at ×0.5/×1/×2 on the demo). The reader can turn the house
  skepticism up and watch capital ranges widen — the output is an input to
  judgement.
- **The engagement number.** For a manager conversation inside the E1 ladder:
  the per-manager transparency dividend ("exposure reporting would raise your
  band floor by ~0.6pp of the book" — §5's matched-pair arithmetic, computed
  for *that* manager) makes the transparency ask concrete and reciprocal,
  never punitive.
- **Contrast discipline.** The naive point-optimizer column exists on the
  page as the *cautionary contrast* and is labeled as such; it is never
  exported as an actionable number (no bare points leave the page).

### 6.8 Go-live requirements (demo-page box, expanded)

- **Data ask:** whatever S1 needs (tier R minimum: monthly net returns ≥36m
  for ≥10 managers with strategy labels, factor sets, risk-free) — P1 adds
  only per-manager residual vols, which the S2 pipeline already produces.
- **Sample required:** bands render at any S1-admissible $T$ — width carries
  the honesty. *Decisive* bands (floors clear of zero, point-MVO reliably
  beaten) need the §6.3 grid's favourable cells: realistically $T \ge 48$
  and true dispersion ≥2%/yr; the atlas rows state the boundary.
- **Upstream dependency:** S1 live (its MCMC build for joint draws; the
  closed form suffices for a first internal version). M4 caps and fee terms
  are named later extensions.
- **Build effort:** S for the band layer on a running S1; M for the
  policy-regret study that licenses decisive language.
- **Go-live box (demo page):** data ask = S1's (tier R) + residual vols;
  sample = any $T$ for honest bands, $T \ge 48$ & dispersion ≥2% for
  decisive ones; effort = S (+M for the study).

## 7. Deeper reading

**Canonical references (read in this order):**

1. **Michaud (1989), "The Markowitz Optimization Enigma: Is 'Optimized'
   Optimal?", *Financial Analysts Journal*.** The estimation-error-maximizer
   argument: optimizers fed estimated means overweight the overestimated.
   The reason this card refuses to ship an optimizer.
2. **Chopra & Ziemba (1993), "The Effect of Errors in Means, Variances, and
   Covariances on Optimal Portfolio Choice," *Journal of Portfolio
   Management*.** Errors in means cost ≈11× errors in variances — the
   quantitative license for spending all the uncertainty machinery on alphas.
3. **Jorion (1986), "Bayes–Stein Estimation for Portfolio Analysis,"
   *JFQA*.** Shrunk means dominate plug-in MVO out of sample; the portfolio-
   side ancestor of S1's shrinkage and the first half of this card's
   pipeline.
4. **Michaud (1998), *Efficient Asset Management*.** Resampled efficiency —
   optimize across simulated input worlds and study the weight distribution;
   P1 keeps the architecture and swaps bootstrap-around-points for
   posterior draws.
5. **MacLean, Thorp & Ziemba (2011), *The Kelly Capital Growth Investment
   Criterion* (collection).** Growth-optimal sizing, fractional Kelly, and
   sizing under parameter uncertainty — the single-bet mechanism behind
   §3.4's denominator inflation. (Best & Grauer 1991, *RFS*, is the
   supporting read on weight sensitivity; Black & Litterman 1992 the
   alternative mean-repair, superseded here by S1's hierarchical posterior.)

**Derivations to own (work each by hand once):**

1. The two-asset unconstrained MV tilt: from $w \propto \Sigma^{-1}\alpha$
   with equal vols, derive
   $w \propto (\alpha_1 - \rho\alpha_2,\; \alpha_2 - \rho\alpha_1)\,/\,\sigma^2(1-\rho^2)$
   and reproduce §3.2's +156%/−56%. Then compute the sd of the alpha spread
   and the 41% sign-flip probability. This one derivation *is* Michaud's
   critique in miniature.
2. The predictive-variance inflation: with
   $r = \alpha + \varepsilon$, $\varepsilon \sim \mathcal N(0,\sigma^2)$, and
   posterior $\alpha \sim \mathcal N(m, s^2)$, show the predictive
   distribution is $\mathcal N(m, \sigma^2 + s^2)$ and hence the Kelly/
   Bayes-MV size divides by $\sigma^2 + s^2$. Note the reappearance of the
   $\tau^2/(\tau^2 + \text{se}^2)$ shrinkage form from S1 §3.7, now acting on
   size.
3. Why selecting the max of noisy estimates selects noise: for
   $\hat\alpha_i = \alpha_i + \eta_i$ with i.i.d. noise, argue (or simulate)
   that $\mathbb{E}[\eta_i \mid i = \arg\max_j \hat\alpha_j] > 0$, and connect
   it to the optimizer's overweighting of flattered names and the upward bias
   of in-sample portfolio alpha.
4. The band as a pushforward: the advisory band is the 10–90 quantile
   interval of the *image* of the posterior under the allocation map
   $\mathcal A$. Convince yourself why a nonlinear, constrained $\mathcal A$
   makes this interval something no delta-method approximation around the
   point weight can reproduce — the reason we resample instead of
   propagating a variance.

**Questions you should be able to answer after reading this page:**

- Explain "estimation-error maximization" to an investment committee in 60
  seconds, using the two-manager +156%/−56% example and the 41% sign-flip.
- State why constraints alone don't fix point-MVO (they truncate the damage
  but keep the noise-driven ordering and the false precision).
- Explain what an advisory band *is* (quantiles of the weight distribution
  across posterior draws) and why its width is inherited honesty rather than
  a tuned parameter.
- Say what B10's row in the demo proves — the naive weight sitting above the
  entire honest band — and which mechanism put it there.
- Explain why two managers with identical posterior mean alphas can and
  should get different capital statements (the B09/B07 matched pair), and
  how the same arithmetic prices the transparency ask in pp of the book.
- State the card's kill criterion and why "equal-weight ties" would be a
  publishable, decision-grade result rather than a failure.
- Explain why P1 draws from the posterior rather than bootstrapping around
  point estimates, and what that inherits from S1.

## 8. Method-review gate rulings (2026-07-07)

1. **`P1_BAND_PCT` = (10, 90) confirmed** as the advisory band, with
   `P1_HYSTERESIS_BANDS` = trigger 10/90, clear 25/75. The band is a
   *decision range* (quantiles of the weight distribution), not an
   uncertainty interval, so it is not in tension with the 5–95 bootstrap
   bands P3/S4 use for estimates — each page labels its own object, and P1's
   label reads "10th–90th percentile of posterior-draw weights."
2. **`P1_SIGMA_DEMO` = 0.08 constant residual vol approved for the demo** —
   it isolates the posterior as the only driver of band differences, which is
   the card's teaching point. Required page sentence disclosing the
   simplification; live builds use per-manager de-smoothed vols from the S2
   pipeline.
3. **v1 independent posterior draws approved.** The joint-draw upgrade (group
   parameters induce positive dependence; expected direction: bands widen
   slightly) renders on the page as a labeled structural provisional.
4. **The policy-regret study and band-calibration gate (§6.3 gates 1–4) are
   wave-3 scope.** The demo ships with the study named as pending and every
   band labeled advisory. Kill gate 2 — posterior policy fails to beat
   equal-weight ⇒ publish the tie and kill the tilt — is affirmed as binding.
5. **The generator reads posteriors from the same roster build that emits
   `s1_ledger.json`** — never hand-transcribed. §4's ledger literals are
   teaching-code copies and are verified against the certified JSON at the
   batch numerics gate.
6. **Constants confirmed:** `P1_ALLOC_CAP` = 0.20, `P1_N_DRAWS` = 50,000,
   `P1_KELLY_FRACTION` = 0.5 (binds extensions only; v1's budgeted rule does
   not lever). No new simulator dial — confirmed.
