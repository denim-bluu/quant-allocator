# P2 · Tiered Book X-Ray (Transparency Fusion) — Method Spec

**Date:** 2026-07-07
**Status: Reviewed — method gate passed 2026-07-07 (rulings in §8)**
**Card:** [`docs/ideas/2026-07-05-idea-cards.md`](../2026-07-05-idea-cards.md) § P2
**Demo:** gallery page `p2.html` (15-manager book X-ray; static-fusion demo variant, §3.6; fully synthetic, §5)

This spec is written as a technical blog post: a reader who has followed the S1
(shrinkage), M1 (drift) and X1 (power atlas) specs but has never met a Kalman
filter should be able to build the mental model before the math and reproduce
the estimator from the mock in §4. **P2 does not re-derive the cards it stands
on — it defines the *fusion contract* that binds them into one book-level view.**

---

## 1. What this is

P2 answers the aggregate question the investment team faces every day and no
single-manager card answers: **what is the factor and risk exposure of the whole
book — and how much of that answer can we actually trust?** A book is a portfolio
of managers who sit at different transparency tiers. Some are position-transparent
(we can compute their exposure almost exactly from holdings). Some disclose
risk-report buckets (we see their exposure approximately). Most give us only
monthly returns (we can only *infer* their exposure, noisily, by regression).
Summing their exposures into a single number is easy and dishonest: it throws away
the fact that three of the fifteen contributions are near-exact and twelve are fog.

P2 fuses those mixed-tier contributions into **one posterior book exposure** — a
point estimate *with a credible interval* — where the interval widens exactly as
far as the book's opacity forces it to. It is a **state-space measurement-error
model**: each manager has a latent true exposure path, each tier is an observation
of that path through a known amount of noise (tight for holdings, medium for
buckets, wide for returns-only), and Bayesian filtering combines them. Two things
come out that a naive sum cannot produce: an honest **band** on the book's
exposure, and **per-manager provenance** — which managers, at which tiers, are
responsible for how much of the book's remaining uncertainty. The recurring
punchline is that the book's exposure uncertainty concentrates almost entirely in
the returns-only managers, and the page names them.

The consumers are the **investment team** (the book-level risk view at monitoring
cadence) and **department leadership** (the same view at the portfolio-review
moment). The decisions it feeds are **monitor** — is the *book's* net factor
exposure where we think it is, or has it drifted at the aggregate even while each
manager looks fine? — and **size** — a book whose beta band is wide because its
largest sleeves are opaque is carrying a risk we cannot see, and that is a sizing
and a transparency-demand input. P2 never recommends a trade or a weight; it
*measures the book and states what the measurement is worth.*

## 2. Why we use it

**The decision problem.** Book-level risk aggregation across managers of unequal
transparency is, per Sweeps A, C and D, *unpublished territory* — there is no
standard method for producing one coherent exposure view when the inputs range
from exact holdings to returns-only inference. The team needs the aggregate ("the
book is net +0.18 beta to the market") **and** the honesty about that aggregate
("±0.07, and nearly all of that width is four returns-only sleeves"). One without
the other is either false precision or an unusable shrug.

**Why the naive alternatives fail.**

- *Average the disclosed exposures and stop.* Treating an RBSA-inferred beta from
  36 months of returns as if it were as solid as a beta computed from holdings
  silently claims a precision the data do not have. The book number looks
  authoritative and its true uncertainty is invisible — the exact bare-point sin
  the Interval doctrine forbids for the input that most moves the answer.
- *Use only the position-transparent managers.* Dropping the returns-only sleeves
  because they are noisy discards most of the book (in a realistic roster, the
  majority of capital is returns-only). The book view then describes a minority of
  the assets and misstates the whole.
- *Infer every manager's exposure from returns uniformly.* Levelling everyone down
  to returns-based style analysis throws away the exact information the
  position-transparent and exposure-disclosing managers already gave us — and, at
  36–60 months, buries every exposure in estimation noise (the M1 §2 result:
  returns-based style-drift *inference* is on the do-not-build list, Sweep-C
  **Noise**).

**What fusion wins over all three.** A single posterior that *uses every manager
at the precision their tier actually earns* — exact holdings pull hard, buckets
pull medium, returns pull weakly — so the book estimate is neither false-precise
nor throwing away information, and it carries a band that is honest by construction.
And because the band decomposes by manager, P2 turns "the book is opaque" from a
lament into a **sourced, quantified** statement: *here are the specific sleeves
whose opacity is costing you book-level clarity, and here is exactly how much the
band tightens if they move up a tier.* That last quantity — the measured tightening
of the book band as transparency rises — is the card's reason to exist and its own
kill gate (§6.4): **if E-tier fusion is not measurably tighter than R-tier fusion
on simulated ground truth, the model is decoration and ships as a reconciliation
table instead.**

- **Decisions improved:** **monitor** (the book-level exposure view, with drift at
  the aggregate); **size** (a wide book band from opaque sleeves is a sizing and
  transparency-demand input).
- **Customer:** investment team (book risk view at monitoring cadence); department
  leadership (portfolio-review book view).

**Three boundaries, stated up front.** P2 is a *measurement*, not an allocator:
it produces no weights and no trades — **portfolio construction is card P1**, and
P2 never crosses into it. P2 aggregates each manager's *own* exposure; it does
**not** measure cross-manager holdings **overlap or crowding** — that is card
**M4**, and P2 explicitly does not model the correlation between managers'
exposures (§3.4 states this as a modelling assumption, not an oversight). And P2's
R-tier exposure is a **calibrated inference carrying its full noise**, never a
style-drift *verdict* — it inherits M1's discipline that returns-based exposure at
short tracks is fog to be measured honestly, not a claim to be made.

## 3. How it works

### 3.1 The mental model, before any math

Picture fifteen managers, each holding up a card with their factor exposure
written on it — but each card is behind glass of a different clarity. The
position-transparent manager's glass is nearly clean: you read their beta to two
decimals. The bucket-disclosing manager's glass is frosted: you read their beta to
maybe the first decimal. The returns-only manager's glass is fogged: you can tell
their beta is positive and roughly medium, but the range you can defend is wide.

To get the book's exposure you do **not** average the fifteen readings as if they
were equally legible. You **precision-weight** them: a reading you trust to ±0.02
gets far more say in its own posterior than a reading you trust only to ±0.25. Then
you add up the managers' posteriors weighted by capital to get the book's, and —
because uncertainty adds in quadrature — the book's remaining fog is dominated by
whichever sleeves had the foggiest glass and the most capital. The tool that does
the precision-weighting optimally, and that also lets a manager's exposure *drift
over time* while holdings arrive only quarterly and returns arrive monthly, is a
**Kalman filter over a latent exposure path**. That is the whole idea: read each
manager through the fog their tier imposes, weight by clarity, aggregate by
capital, and the band you get is the honest book band.

Two subtleties turn this into a disciplined estimator, and both are worth intuition
before the formulas.

**Subtlety one — the fog level is not a guess, it is calibrated.** How wide is a
returns-only beta's fog at 48 months? How much does a bucket disclosure cut it?
These per-tier noise levels are **measured on the simulator by card X1**, which
emits all three tiers of the *same* ground-truth book and can therefore count how
far each tier's exposure estimate lands from truth. X1 is a **hard prerequisite,
not a nicety** — without its per-tier measurement-error numbers, P2's band widths
are made up. (§3.5, X1 §4 "RMSE of the point estimate by tier.")

**Subtlety two — exposure drifts, and holdings are stale between filings.** A
manager's true exposure is not a fixed number; it walks (the M1 drift story, at the
book level now). Holdings give a near-exact reading but only on filing dates;
between filings the position-transparent manager is as uncertain as anyone until
the next snapshot. A filter handles this naturally: between observations it *widens*
the band (the exposure could have drifted), and at each new observation it *tightens*
by the incoming tier's precision. The book band therefore breathes — tight just
after a round of filings, wider as they age.

### 3.2 A worked toy example with small numbers

Three managers, equal capital weight (1/3 each), each reporting a net market beta
through a different tier's fog. Take a weak common prior on any manager's beta of
mean **0.20** and sd **0.50** (`BOOK_PRIOR_MEAN`, `BOOK_PRIOR_SD`), and the pinned
per-tier measurement sds `EXPOSURE_MEAS_SD` = {P: 0.02, E: 0.08, R: 0.25}:

| Manager | Tier | Observed β | Posterior sd | Provenance (share of book **variance**) |
| --- | --- | --- | --- | --- |
| P-mgr | P (holdings) | +0.30 | 0.0200 | 0.7% |
| E-mgr | E (buckets) | +0.50 | 0.0790 | 11.0% |
| R-mgr | R (returns) | +0.20 | 0.2236 | 88.3% |

Read one row to see the mechanism. The R-manager's posterior sd is
$\sqrt{1/(1/0.50^2 + 1/0.25^2)} = \sqrt{1/20} = 0.2236$ — the weak prior barely
tightens a returns-only reading, so its fog survives almost intact. The
P-manager's holdings reading is trusted to 0.02, so its posterior is essentially
its observation.

The **book beta** is the capital-weighted sum of the three posterior means,
$\tfrac13(0.300 + 0.493 + 0.200) = 0.331$, and — because the managers are treated
as independent — its variance is the weighted sum of squares,
$\tfrac19(0.0200^2 + 0.0790^2 + 0.2236^2) = 0.006293$, so the book sd is **0.0793**
and the 90% credible interval is $\pm 1.645 \times 0.0793 = \pm 0.130$:

$$\textbf{book } \beta = +0.331 \pm 0.130 \ (90\%).$$

Now the provenance punchline. The R-manager alone contributes
$0.0500 / 0.05664 = 88.3\%$ of the book's exposure variance — **one returns-only
sleeve is responsible for seven-eighths of the book's remaining fog.** And the
tiering is not fate: upgrade that one manager from R to E and the book sd falls to
**0.0378** (52% tighter); upgrade to P and it falls to **0.0280** (65% tighter).
Same three managers, same book beta, radically different confidence — bought by
transparency on the *single* sleeve the provenance decomposition fingered. That is
the entire P2 thesis in three managers; §5 scales it to fifteen. (These are the
mock's actual outputs, §4.)

### 3.3 The state-space measurement-error model (the live estimator)

**The latent state.** For manager $i$ and factor $j$ (a scalar shown; the vector
case runs one filter per factor to first order, §3.4), the true exposure is a
**path** that evolves month to month:

$$x_{i,t} = x_{i,t-1} + d_{i,t} + w_{i,t}, \qquad w_{i,t} \sim \mathcal{N}(0,\ q_i^2).$$

where:

- $x_{i,t}$ — manager $i$'s **true** factor exposure (e.g. net market beta) at
  month $t$; the latent quantity we are estimating.
- $d_{i,t}$ — a **drift** term: a known or estimated deterministic walk in the
  exposure, supplied by the **M1 drift monitor** (M1 §3.3 CUSUM onset/slope). For an
  honest, non-drifting manager $d_{i,t} = 0$.
- $w_{i,t}$ — **process noise**: the honest month-to-month wander of an active book
  as names rotate, Normal with sd $q_i$ (`FILTER_PROCESS_SD`). This is what makes
  the band *grow* between observations.
- $q_i$ — the process-noise sd, the exposure's natural monthly wander (tied to the
  manager's turnover; M1 §3.4's autocorrelated-wander scale).

**The tier observation equations.** Each tier is a noisy reading of the *same*
latent $x_{i,t}$, differing only in its noise variance:

$$y^{\text{P}}_{i,t} = x_{i,t} + v^{\text{P}}_{i,t}, \quad
y^{\text{E}}_{i,t} = x_{i,t} + v^{\text{E}}_{i,t}, \quad
y^{\text{R}}_{i,t} = x_{i,t} + v^{\text{R}}_{i,t}, \qquad
v^{\tau}_{i,t} \sim \mathcal{N}(0,\ r_\tau^2),$$

with $r_{\text{P}} < r_{\text{E}} < r_{\text{R}}$.

where:

- $y^{\tau}_{i,t}$ — the exposure **observed** at tier $\tau$: from holdings (P),
  from Open-Protocol risk buckets (E), or from a returns regression (R).
- $v^{\tau}_{i,t}$ — the tier's **measurement error**: Normal, mean zero, variance
  $r_\tau^2$. This is a classic *errors-in-variables* term — we observe the latent
  exposure through noise of *known* variance.
- $r_\tau$ — the per-tier measurement sd (`EXPOSURE_MEAS_SD`), **calibrated by X1**
  (§3.5). Holdings are near-exact ($r_{\text{P}}$ small); buckets are coarsened
  ($r_{\text{E}}$ medium); returns-only inference is noisy ($r_{\text{R}}$ large).
- A month with **no filing at any tier** contributes no observation — the filter
  does a pure *time-update* (predict, no correct), and the band widens by $q_i$.

**Bayesian filtering.** For each manager the Kalman recursion alternates a
**predict** step (push the state forward, grow the variance by process noise) and,
whenever an observation arrives, an **update** step (pull the state toward the
observation by the Kalman gain, shrink the variance):

$$\text{predict:}\quad \hat x^{-}_t = \hat x_{t-1} + d_t,\quad P^{-}_t = P_{t-1} + q^2;$$
$$\text{update:}\quad K_t = \frac{P^{-}_t}{P^{-}_t + r_\tau^2},\quad
\hat x_t = \hat x^{-}_t + K_t\,(y_t - \hat x^{-}_t),\quad P_t = (1 - K_t)\,P^{-}_t.$$

where:

- $\hat x^{-}_t,\ P^{-}_t$ — the **predicted** (prior-to-observation) state mean and
  variance at month $t$.
- $K_t$ — the **Kalman gain**, between 0 and 1: the fraction of the way the estimate
  moves toward a new observation. A precise tier ($r_\tau$ small) gives $K_t$ near 1
  (trust the reading); a noisy tier gives $K_t$ near 0 (barely move).
- $\hat x_t,\ P_t$ — the **filtered** (post-observation) state mean and variance —
  the current best estimate of manager $i$'s exposure and its uncertainty.

In words: exposure is allowed to drift, so the estimate's uncertainty grows every
month; each disclosure pulls the estimate toward its reading in proportion to how
much that tier is trusted, and shrinks the uncertainty accordingly. This is the
optimal linear-Gaussian filter (Kalman 1960; §3.7).

**The book aggregate.** The book exposure is the capital-weighted sum of the
managers' filtered exposures:

$$B_t = \sum_{i} c_i\,x_{i,t}, \qquad
\mathbb{E}[B_t] = \sum_i c_i\,\hat x_{i,t}, \qquad
\operatorname{Var}[B_t] = \sum_i c_i^2\,P_{i,t}.$$

where:

- $c_i$ — manager $i$'s **capital weight** in the book ($\sum_i c_i = 1$).
- $\mathbb{E}[B_t],\ \operatorname{Var}[B_t]$ — the **book** exposure's posterior
  mean and variance; the 90% band is $\mathbb{E}[B_t] \pm 1.645\sqrt{\operatorname{Var}[B_t]}$.

The variance is a **sum of squares**, which is why the book's fog concentrates in
the few sleeves with the largest $c_i^2 P_{i,t}$ — the provenance decomposition of
§3.2. **Distributional assumptions, stated plainly:** exposures and all noise terms
are Gaussian; the tier measurement variances $r_\tau^2$ are known (from X1);
managers' exposures are treated as **conditionally independent given the book** —
P2 does *not* model cross-manager exposure correlation, because that correlation is
crowding/overlap and belongs to **card M4** (§2 boundary). Under independence the
book variance is a clean quadratic sum; correlated sleeves would add covariance
cross-terms P2 deliberately omits.

### 3.4 The fusion contract — what each tier's card contributes

P2's own new content is the *fusion*; the per-manager exposure evidence it fuses is
produced by cards already specified. Naming the contract precisely — and citing,
not re-deriving — is this spec's job.

| Tier | Exposure observation $y^\tau_{i,t}$ comes from | Source card | Measurement sd $r_\tau$ |
| --- | --- | --- | --- |
| **R** | The **factor-β posterior** co-estimated with alpha in the hierarchical model — its posterior mean is $y^{\text{R}}$, its posterior sd feeds $r_{\text{R}}$. | **S1 §3.3, §3.5** (import the β posterior; do **not** re-fit) | wide (X1) |
| **E** | The **measured net/gross/factor-β path** disclosed in Open-Protocol risk buckets — the same path M1's drift monitor reads. | **M1 §3.1, §3.5** (consume the measured $x_{j,t}$) | medium (X1) |
| **P** | The **near-exact exposure computed from holdings** at each snapshot date (weights × security betas), sharpened on the short side by the hedge/alpha decomposition. | holdings emission + **S5 §3** (short-sleeve factor split) | small (X1) |

Two cross-cutting contributions complete the contract:

- **Drift ($d_{i,t}$) is M1's output.** The state-evolution drift term is not
  invented in P2 — where M1's CUSUM has flagged a sustained exposure walk for a
  manager, its estimated onset and slope populate $d_{i,t}$, so the book filter
  tracks a *drifting* sleeve rather than lagging behind a stale reading. A
  non-drifting manager contributes $d_{i,t}=0$ and the filter is pure wander.
- **P-tier stability is S3/S4's provenance annotation.** How stable is a holdings
  snapshot between filings? A high-turnover book (S3's sizing/decay lab reads its
  trade cadence) drifts faster between snapshots than a low-turnover one, and a book
  with deteriorating **sell discipline** (S4) is churning its exposure — both raise
  the *effective* process noise $q_i$ applied to a P-tier sleeve between filings.
  P2 consumes S3/S4 **only where P-tier**, and only as a qualifier on $q_i$, never
  as a new exposure estimate. This is the honest use of the position-level cards:
  they tell the filter how fast to widen a stale holdings reading.
- **The per-tier variances $r_\tau$ are X1's calibration.** X1 §4 measures the
  RMSE of the factor-β estimate by tier on simulator ground truth; those RMSEs are
  $r_{\text{R}}, r_{\text{E}}, r_{\text{P}}$. This is the hard prerequisite: P2's
  band widths are X1's measured degradation, not assertions.

**Vector factors.** The exposure is really a vector (market, size, value, …). v1
runs **one filter per factor** (treating factors as independently observed), which
is exact when the tier noise is factor-diagonal and a stated first-order
approximation otherwise; a full multivariate filter with a factor-covariance
observation model is flagged **`FILTER_VECTOR_JOINT` (provisional — per-factor in
v1)** and deferred to the P-phase build.

### 3.5 Where the tier noise numbers come from (the X1 dependency, made concrete)

The whole band rests on $r_{\text{P}} < r_{\text{E}} < r_{\text{R}}$, and those
three numbers are the atlas's, not P2's. X1 (§4, §5 Exhibit 2) already scores
factor-β estimation by tier — returns-tier vs exposure-tier — and reports the RMSE
of the point estimate per cell. P2 consumes a **new atlas row**: the factor-β
**measurement-error sd by tier** at each $(T, \text{effect})$ cell, which is the
same quantity X1 already computes, surfaced as $r_\tau$. This is named as an X1
docket item (§6.3), with byte-identical-default discipline: until the atlas
volume-1 exposure rows land, the `EXPOSURE_MEAS_SD` constants carry the provisional
values in §3.2 and are flagged NUMERICS-GATE. P2 never hand-picks a band width the
atlas has not measured — that is the discipline the whole program keeps.

### 3.6 The static-fusion demo variant (what the gallery shows)

The live estimator is the time-indexed Kalman filter. But at a *single* review
date, with one observation per manager and the process-noise/time dimension folded
into the tier variance, the filter collapses to a **normal-normal conjugate
update** — the pencil-and-paper special case, exactly as S1's closed-form shrinkage
is the demo face of its full MCMC engine. Drop the time index; give each manager a
prior $x_i \sim \mathcal{N}(m_0, s_0^2)$ and one tier observation $y_i$ with
variance $r_{\tau(i)}^2$; the posterior is

$$P_i = \left(\frac{1}{s_0^2} + \frac{1}{r_{\tau(i)}^2}\right)^{-1}, \qquad
\hat x_i = P_i\left(\frac{m_0}{s_0^2} + \frac{y_i}{r_{\tau(i)}^2}\right),$$

and the book posterior is the $c_i$-weighted aggregate of §3.3. This is what the
demo page computes and what the §4 mock runs; the gallery footnote states it uses
this variant and points here. The static variant is the intuition and the demo; the
filter is the product.

### 3.7 What the canonical papers contribute

- **Kalman (1960), "A New Approach to Linear Filtering and Prediction Problems"
  (*Trans. ASME*).** Derived the recursive optimal estimator for a linear-Gaussian
  state-space system: predict the state forward, correct it by each observation
  weighted by a gain that balances process and measurement noise. P2's temporal
  fusion *is* this filter, with the tiers as observations of one latent exposure —
  the direct methodological anchor for §3.3.
- **Durbin & Koopman, *Time Series Analysis by State Space Methods* (2nd ed.).** The
  modern treatment of state-space models with **irregular and mixed-frequency**
  observations, including the correct handling of missing observations as pure
  time-updates. This is exactly P2's situation — monthly E buckets, quarterly P
  holdings, returns-derived R readings — and it justifies the "no filing ⇒ predict
  only, band widens" rule.
- **Fuller (1987), *Measurement Error Models* (errors-in-variables).** The
  statistical theory of estimating a relationship when a variable is observed
  through noise of known variance. It is why treating an RBSA beta as if it were
  exact is a *bias*, not just imprecision, and why the honest move is to carry each
  tier's $r_\tau^2$ explicitly — the errors-in-variables reading of the tier
  observation equations.
- **Gelman, Carlin, Stern, Dunson, Vehtari & Rubin, *BDA3*, ch. 5 & 13.** Bayesian
  hierarchical aggregation and precision-weighted pooling — the book posterior is a
  precision-weighted fusion under a weak common prior, the same machinery S1 uses to
  shrink alphas, here applied to exposures. Grounds the demo's conjugate variant and
  the choice of a weakly-informative common prior.
- **Open Protocol Enabling Technology (OPET / AIMA risk-reporting template).** Not a
  paper but the **E-tier data standard**: the risk-exposure bucket schema that
  defines what an E disclosure contains and how coarse it is. Its bucket granularity
  is what sets $r_{\text{E}}$ (the coarsening in §6.3), and it is the standardisation
  ask the go-live box names.

## 4. How to implement

The reference implementation below is **self-contained teaching code** — paste it
into a fresh file, it runs on `numpy` alone, no project imports and no repo paths.
It implements the same formulas as §3: the normal-normal measurement posterior
(§3.6), the capital-weighted book aggregate and its provenance decomposition
(§3.3), the information-gain comparison (§2, §6.4 gate), and the 1-D Kalman filter
over a latent exposure path (§3.3). Running it reproduces every number quoted in
§3.2 and §5 from first principles.

```python
"""P2 tiered book X-ray — reference implementation (teaching code).

Fuses per-manager, per-tier factor-exposure observations into one posterior
book exposure with per-manager provenance and a tier-degraded band. numpy only.

Two blocks:
  A. Static cross-sectional Gaussian measurement-error fusion  -> the demo variant.
  B. A 1-D Kalman filter over a latent exposure PATH            -> the live model.
"""

import numpy as np

# --- Provisional constants (names match the spec's NUMERICS-GATE table) -------
# Per-tier measurement standard deviation of a single factor beta, from the X1
# atlas exposure rows (provisional until atlas volume-1 supersedes).
EXPOSURE_MEAS_SD = {"P": 0.02, "E": 0.08, "R": 0.25}
BOOK_PRIOR_SD = 0.50        # weak common prior sd on a manager's factor beta
BOOK_PRIOR_MEAN = 0.20      # weak common prior mean (book-neutral-ish)
INFO_GAIN_FLOOR = 0.20      # min fractional band-tightening (E vs R) to render


# --- A. Static measurement-error fusion (the demo variant) --------------------

def measurement_posterior(prior_mean, prior_sd, obs, meas_sd):
    """Normal-normal conjugate update for one manager's latent factor beta.

    posterior precision = prior precision + measurement precision;
    posterior mean = precision-weighted blend of prior and observation.
    """
    prior_prec = 1.0 / prior_sd**2
    meas_prec = 1.0 / meas_sd**2
    post_var = 1.0 / (prior_prec + meas_prec)
    post_mean = post_var * (prior_prec * prior_mean + meas_prec * obs)
    return post_mean, np.sqrt(post_var)


def book_posterior(weights, post_means, post_sds):
    """Capital-weighted book exposure B = sum_i w_i x_i, managers independent.

    mean = sum w_i mu_i ; var = sum w_i^2 sigma_i^2.
    """
    w = np.asarray(weights, float)
    mu = np.asarray(post_means, float)
    sd = np.asarray(post_sds, float)
    book_mean = float(w @ mu)
    book_var = float((w**2) @ (sd**2))
    return book_mean, np.sqrt(book_var)


def provenance(weights, post_sds):
    """Fraction of book exposure VARIANCE each manager contributes."""
    w = np.asarray(weights, float)
    sd = np.asarray(post_sds, float)
    contrib = (w**2) * (sd**2)
    return contrib / contrib.sum()


def fuse_book(weights, observations, tiers):
    """Run per-manager posteriors then fuse. Returns book (mean, sd) + per-mgr sds."""
    post_means, post_sds = [], []
    for obs, tier in zip(observations, tiers):
        m, s = measurement_posterior(BOOK_PRIOR_MEAN, BOOK_PRIOR_SD,
                                     obs, EXPOSURE_MEAS_SD[tier])
        post_means.append(m)
        post_sds.append(s)
    bm, bsd = book_posterior(weights, post_means, post_sds)
    return bm, bsd, np.array(post_sds)


# --- B. 1-D Kalman filter over a latent exposure path (the live model) --------

def kalman_exposure_path(observations, obs_tiers, process_sd,
                         x0=BOOK_PRIOR_MEAN, p0=BOOK_PRIOR_SD**2):
    """Filter a latent net-beta path x_t observed through tier-specific noise.

    State:       x_t = x_{t-1} + w_t,  w_t ~ N(0, process_sd^2)   (drift/wander).
    Observation: y_t = x_t + v_t,      v_t ~ N(0, meas_sd(tier)^2).
    A month with obs_tiers[t] is None is a pure time-update (no filing that month).
    Returns filtered (means, sds).
    """
    x, p = x0, p0
    means, sds = [], []
    for y, tier in zip(observations, obs_tiers):
        # time update (predict): exposure can drift, so variance grows
        p = p + process_sd**2
        if tier is not None:
            r = EXPOSURE_MEAS_SD[tier]**2
            k = p / (p + r)              # Kalman gain
            x = x + k * (y - x)
            p = (1.0 - k) * p
        means.append(x)
        sds.append(np.sqrt(p))
    return np.array(means), np.array(sds)


if __name__ == "__main__":
    Z90 = 1.6448536269514722

    # ---- Worked toy example (spec 3.2): three equal-weight managers ----------
    print("=== Toy: 3 equal-weight managers, one per tier ===")
    w3 = [1/3, 1/3, 1/3]
    obs3 = [0.30, 0.50, 0.20]
    tier3 = ["P", "E", "R"]
    bm, bsd, psd = fuse_book(w3, obs3, tier3)
    prov = provenance(w3, psd)
    for name, o, t, s, pr in zip(["P-mgr", "E-mgr", "R-mgr"], obs3, tier3, psd, prov):
        print(f"  {name} (tier {t}): obs {o:+.2f}  post_sd {s:.4f}  "
              f"provenance {pr*100:4.1f}% of book var")
    print(f"  BOOK beta = {bm:+.3f}  +/- {Z90*bsd:.3f} (90% CI)  [sd {bsd:.4f}]")

    # counterfactual: upgrade the dominating R manager to E, then to P
    _, bsd_e, _ = fuse_book(w3, obs3, ["P", "E", "E"])
    _, bsd_p, _ = fuse_book(w3, obs3, ["P", "E", "P"])
    print(f"  Upgrade R-mgr -> E: BOOK sd {bsd_e:.4f} (tighten {(1-bsd_e/bsd)*100:.0f}%)")
    print(f"  Upgrade R-mgr -> P: BOOK sd {bsd_p:.4f} (tighten {(1-bsd_p/bsd)*100:.0f}%)")

    # ---- 15-manager demo book (spec 5) ---------------------------------------
    print("\n=== Demo book: 15 managers ===")
    tiers = ["R", "R", "E", "R", "P", "R", "E", "R", "R",
             "E", "P", "R", "E", "R", "R"]
    obs = [0.15, 0.42, 0.05, 0.30, -0.10, 0.55, 0.20, 0.35, 0.12,
           0.28, 0.08, 0.48, 0.18, 0.40, 0.22]
    raw_w = [8, 6, 9, 5, 12, 4, 7, 5, 10, 6, 11, 4, 7, 5, 6]
    w = np.array(raw_w, float) / sum(raw_w)

    bm, bsd, psd = fuse_book(w, obs, tiers)
    prov = np.array(provenance(w, psd))
    tiers_arr = np.array(tiers)
    print(f"  BOOK net beta = {bm:+.3f}  +/- {Z90*bsd:.3f} (90% CI)  [sd {bsd:.4f}]")
    for t in ["R", "E", "P"]:
        share = prov[tiers_arr == t].sum()
        n = int((tiers_arr == t).sum())
        print(f"    tier {t}: {n:2d} managers, {share*100:4.1f}% of book-exposure variance")

    _, bsd_E, _ = fuse_book(w, obs, ["E" if t == "R" else t for t in tiers])
    _, bsd_R, _ = fuse_book(w, obs, ["R"] * 15)
    print(f"  Band sd if ALL managers R-tier: {bsd_R:.4f}")
    print(f"  Band sd at ACTUAL tier mix:     {bsd:.4f}  (tighten {(1-bsd/bsd_R)*100:.0f}% vs all-R)")
    print(f"  Band sd if every R upgraded->E: {bsd_E:.4f}  (tighten {(1-bsd_E/bsd)*100:.0f}% vs actual)")
    gain = 1 - bsd_E / bsd_R
    print(f"  Info-gain (all-R -> all>=E): {gain*100:.0f}%  (floor {INFO_GAIN_FLOOR*100:.0f}%): "
          f"{'RENDER' if gain >= INFO_GAIN_FLOOR else 'REFUSE'}")

    # ---- Kalman path (spec 3.3): one manager, monthly E + quarterly P --------
    print("\n=== Kalman: one manager, monthly E buckets + quarterly P holdings ===")
    rng = np.random.default_rng(20260707)  # named integer stream tag, not hash()
    T = 12
    truth = 0.10 + 0.02 * np.arange(T)     # a net-beta walk 0.10 -> 0.32
    obs_seq, tier_seq = [], []
    for t in range(T):
        tier_seq.append("P" if t % 3 == 2 else "E")   # quarterly holdings filing
        obs_seq.append(truth[t] + rng.normal(0, EXPOSURE_MEAS_SD[tier_seq[-1]]))
    means, sds = kalman_exposure_path(obs_seq, tier_seq, process_sd=0.02)
    print("  month  tier   truth   filtered  +/-90%")
    for t in range(T):
        print(f"   {t:2d}    {tier_seq[t]}    {truth[t]:+.3f}   "
              f"{means[t]:+.3f}   {Z90*sds[t]:.3f}")
```

Running it prints, in order: the three-manager toy (book β **+0.331 ± 0.130**, the
R-sleeve owning **88.3%** of the book variance, tightening **52% / 65%** when that
sleeve moves to E / P); the fifteen-manager book (**+0.182 ± 0.068**, tier-R
sleeves owning **92.2%** of the variance against **7.2%** for E and **0.6%** for P);
the information-gain check (all-R band sd **0.0611** → actual **0.0411**, 33%
tighter → all-≥E **0.0180**, a **70%** gain, clearing the 20% floor ⇒ **RENDER**);
and the Kalman path tracking a drifting exposure, its band tightening to **±0.029**
at each quarterly holdings filing and widening to **±0.049** as the reading ages.

## 5. Reading the demo

The gallery page `p2.html` is the **book X-ray**, fully synthetic (§6 compliance),
computed by the §4 static-fusion variant on a 15-manager synthetic book. Every
number comes from the committed `site/data/p2_xray.json`; the demo generator
imports the *same* fusion code a live build would run, only the input data is
synthetic (simulator tier emissions vs real disclosures).

*Section 5 numbers were reconciled to the deterministic generator on 2026-07-10;
deltas from the teaching example remain held for the batch numerics gate.*

**The book-exposure headline — the centrepiece.** One IntervalStat: the book's net
market beta, **+0.229**, with its 90% band **+0.161 to +0.296** (half-width
approximately **0.068**). The point is the
capital-weighted posterior mean; the band is the fused book uncertainty. This is the
"one coherent factor view of a mixed-tier book" the card promises — and it is an
*interval*, never a bare number.

**The provenance waterfall — the punchline.** A bar per manager, ordered by
capital, each shaded by its tier (TierBadge colour) and sized by its **share of the
book's exposure variance**. The reader sees at a glance that the nine returns-only
sleeves own **92.2%** of the book's fog, the four E sleeves **7.2%**, and the two
position-transparent sleeves **0.6%** — even though the P sleeves carry real
capital. The message the page makes unavoidable: *the book's exposure uncertainty
lives almost entirely in the managers you can only see through returns.* Each bar
names the manager (synthetic: Westermark Strategies, Juniper Vale Partners, Sedgewick
Advisors, Ravenna Point, Oakhurst Capital, Halstead Partners, Norwood Crest, Talbot
Reach, Ternhaven Capital, Greyloft Partners, Verling Capital, Vantage Row, Cormorant
Capital, Emberly Partners, Dunmore Advisors), so provenance is *sourced*, not
aggregate.

**The information-gain exhibit — the card's reason to exist.** Three stacked book
bands for the *same* book at three counterfactual transparency levels: **all-R**
(band sd 0.0611), the **actual mix** (0.0411 — 33% tighter than all-R), and
**every-sleeve-≥E** (0.0180 — a 70% reduction from all-R). The exhibit is the
measured answer to "what does transparency buy the book?" — stated in band width,
not adjectives. The **70% > 20% floor** is the PowerGate's RENDER condition (§6.4):
the page shows the gate *passing*, and the go-live box states that a book where
E-fusion is not measurably tighter than R-fusion would trip the gate and fall back
to a reconciliation table.

**How each element maps to the method:**

- **Book IntervalStat** = the §3.3 book aggregate $\mathbb{E}[B] \pm 1.645\sqrt{\operatorname{Var}[B]}$.
- **Provenance bar $i$** = the §3.3 variance share $c_i^2 P_i / \sum_k c_k^2 P_k$.
- **TierBadge on each bar** = the manager's transparency tier (the observation
  equation used).
- **The three information-gain bands** = the §6.4 gate quantity — book band sd at
  all-R, actual, all-≥E.
- **The skepticism dial** = the R-tier `EXPOSURE_MEAS_SD` control; selecting a larger
  returns-tier noise state widens the R sleeves and the book band —
  the Dietvorst move (S1 §6.3 pattern), showing how far the book view leans on the
  atlas's tier-noise numbers.

**The power gate.** The honest refusal: the fusion renders **only** because the
measured information gain (70%) clears `INFO_GAIN_FLOOR`; the page states that below
the floor P2 refuses the single-posterior view and shows the reconciliation table
instead (each manager's exposure listed by tier, un-fused) — the kill fallback made
visible, not hidden.

What an allocator should conclude from these numbers: the book is modestly net-long
the market (+0.23), but nearly all of the uncertainty in that figure is
concentrated in returns-only sleeves; the two managers who give holdings contribute
almost nothing to the book's fog despite real capital; and moving the returns-only
sleeves up even one tier would cut the book's exposure band by more than half — a
quantified, sourced case for demanding transparency exactly where it pays.

## 6. Honest limits & go-live

### 6.1 What P2 does not do (do-not-build adjacency)

- **No allocation.** P2 produces no weights and no trades. Portfolio construction
  is **card P1**; P2 is a measurement that *feeds* sizing judgement, never an
  optimizer. It emits an exposure posterior, full stop.
- **No crowding or overlap.** P2 aggregates each manager's own exposure under a
  cross-manager **independence** assumption (§3.3). Measuring how much two managers
  hold the *same names* — crowding/overlap — is **card M4**; P2 does not compute a
  correlation matrix and does not smuggle one in.
- **No returns-based style-drift *inference* as a verdict, no regime splits, no
  conditional (time-varying) betas** (convergence §4). The R-tier exposure is a
  calibrated inference carrying its full measured noise (M1's discipline); P2 never
  slices the path into regimes or fits time-varying alphas, and the exposure filter
  is a single stationary-noise state model, not a regime model.

### 6.2 Data contract per tier

P2 is **the tier axis at book altitude**: every tier contributes; higher tiers
tighten the book band; none is required to *render* (the fusion runs on whatever mix
exists, and states its band).

| Tier | Inputs the live version needs | What the tier contributes to the book |
| --- | --- | --- |
| **R** (minimum) | Monthly net returns + a strategy factor set per manager (S1 §2 conventions); the **S1 factor-β posterior** (mean + sd). | The returns-only exposure observation $y^{\text{R}}$ with its **wide** $r_{\text{R}}$ — the sleeve enters the book fully, at honest low precision. |
| **E** | R + **Open-Protocol-aligned risk buckets** (net/gross/factor-β/sector), per period; the M1 measured exposure path. | A **medium**-precision observation $y^{\text{E}}$: the book band tightens on this sleeve; drift ($d_{i,t}$) from M1 where flagged. |
| **P** | E + **position/holdings snapshots** (dated); short-side factor split (S5); turnover/sell-discipline reads (S3/S4). | A **near-exact** observation $y^{\text{P}}$ at snapshot dates; S3/S4 raise $q_i$ between filings for churny books; S5 sharpens the short-side factor exposure. |

**Frequency & cadence.** Returns and E buckets at monthly (or the manager's native)
cadence; P holdings at their filing cadence (near-exact on the date, ageing between
— the filter's time-update handles the staleness). The book posterior is a
**filtered current** estimate, timestamped, breathing tighter after a round of
filings and wider as they age.

**Compliance (standing):** synthetic managers in the repo; any real-data rung uses
public disclosures of unaffiliated managers only (SEC/FINRA, public risk reports,
Open-Protocol feeds) — no employer-internal exposures or manager names in code,
docs, or the committed demo JSON.

### 6.3 New substrate required (named prerequisites, gate questions not hidden)

P2 is the portfolio's most ambitious card; it needs substrate beyond what is built.
Named explicitly, with byte-identical-default discipline:

1. **X1 exposure-measurement-error rows (hard prerequisite).** The per-tier factor-β
   measurement sds $r_{\text{P}}, r_{\text{E}}, r_{\text{R}}$ are an X1 atlas output
   (§3.5). X1 already scores factor-β RMSE by tier; P2 needs it surfaced as a
   registry row per $(T, \text{effect})$ cell. Until then `EXPOSURE_MEAS_SD` is
   provisional (§3.2 values), flagged NUMERICS-GATE. **X1 is a hard prerequisite,
   not a nicety** (card + §3.1).
2. **E-tier bucket coarsening in the simulator emission (small, new).** The current
   `simulator/tiers.py` emits *exact* factor betas at the E tier; a real Open-Protocol
   disclosure is **coarsened** into buckets. P2 needs an emission option that rounds
   the E-tier exposure to `OP_BUCKET_WIDTH` granularity (adding a stated
   quantization error that *is* $r_{\text{E}}$'s floor). Byte-identical default:
   coarsening off recovers the exact emission, so no existing generator's output
   changes unless it opts in — the `overlays.py` / `net_drift` discipline.
3. **The multi-manager book itself already exists.** One market, many managers on
   it, all three tiers emitted per manager — `roster.py` already builds a
   multi-manager roster on a shared `simulate_market`, and `emit_tiers` already
   returns returns-only / exposures / transparency per manager. **No new
   generative substrate is needed for the book**; P2 composes existing emissions.
   (This is the honest answer to "does P2 need a 13F-style holdings emitter or a new
   cross-manager universe?" — **no**, because the shared-market roster and the
   three-tier emission are both built.)

### 6.4 Power & validation plan

Validation runs on the simulator with **known ground-truth exposures**, so band
honesty and information gain are *measured*, not asserted; cells contribute to the
X1 atlas as P2's rows. Grid follows the atlas convention: roster size ∈ {10, 15,
40} × tier mix (all-R, realistic-skew, all-P) × $T$ ∈ {36, 48, 60} × true exposure
dispersion, ≥1,000 seeded replications per cell (per-module RNG stream tags; Wilson
95% intervals on every rate — X1 §3.3).

Acceptance gates:

1. **Information gain (the load-bearing gate).** On simulated ground truth, the
   book band at the E-inclusive mix must be **measurably tighter** than the all-R
   band by at least `INFO_GAIN_FLOOR` (provisional 20%), with the tightening's
   Wilson interval excluding zero. This is the card's stated gate: *if E-fusion is
   not tighter than R-fusion, the model is decoration* — and it fails to the §6.5
   reconciliation-table fallback. (Demo measured 70% at the realistic mix.)
2. **Band coverage.** The fused book band's empirical coverage of the true book
   exposure lands within ±5 pp of nominal (90%) across the grid — a miscalibrated
   book band is worse than none (S1 §6.2 discipline).
3. **Provenance faithfulness.** The variance-share decomposition (§3.3) must match,
   within MC error, the actual per-manager contribution to book estimation error
   measured against ground truth — the provenance the page prints is *true*, not
   cosmetic.
4. **Roster-scale stability.** At roster size 40 the filter must remain numerically
   stable (no variance blow-up, no negative $P_t$) and the book posterior must not
   depend on manager ordering — the card's stated "model instability at roster
   scale" risk, measured.
5. **Tier-monotonicity invariant.** Book band sd must be non-increasing as any
   single manager moves R→E→P (more transparency never widens the book), up to MC
   noise; a violation blocks the build.

**Simulator dependency (honest).** Gates need (a) the X1 exposure-measurement-error
rows (§6.3.1) and (b) the E-tier coarsening emission (§6.3.2). Both are named
prerequisites; the demo and gates 1–2 stand on the provisional constants until the
atlas rows supersede them.

### 6.5 Kill criteria

- **Statistical.** If the information-gain gate (§6.4 gate 1) fails — E-fusion not
  measurably tighter than R-fusion — or the filter is unstable at roster scale
  (§6.4 gate 4), P2 **ships as a reconciliation table**, not a single posterior:
  each manager's exposure listed by tier with its own band, un-fused, plus the
  book's naive capital-weighted sum labelled *"un-fused — tiers not reconciled."*
  This is the card's stated fallback (Sweep A's Open-Protocol reconciliation
  alignment), recorded in writing per converge-or-cut. A fused posterior that hides
  an un-earned precision is worse than an honest table.
- **Effort (hard time-box).** P2 is the designated phase-2 flagship; if the two-tier
  (R+E) MVP is not standing after its allotted phase, it is parked with a written
  post-mortem (card risk), never extended silently.
- **Political.** The book view is a *measurement and a transparency-demand input*,
  never an auto-trade or an auto-redeem. If a consumer wires the book band to a
  mechanical sizing rule, the card is pulled (P1 owns sizing; P2 owns the picture).

### 6.6 Provisional constants (flagged for the numerics gate)

Every value is a named constant at module top; the numerics gate flips one and the
fusion/demo regenerates deterministically.

| Constant | Provisional value | Role |
| --- | --- | --- |
| `EXPOSURE_MEAS_SD` (P / E / R) | 0.02 / 0.08 / 0.25 | Per-tier factor-β measurement sd $r_\tau$; **X1 atlas output**, provisional until volume-1 exposure rows |
| `BOOK_PRIOR_MEAN` | 0.20 | Weak common prior mean on a manager's factor β |
| `BOOK_PRIOR_SD` | 0.50 | Weak common prior sd (deliberately diffuse — the tiers, not the prior, carry the information) |
| `INFO_GAIN_FLOOR` | 0.20 (20%) | Minimum E-vs-R band tightening to render (§6.4 gate 1); below it → reconciliation table |
| `FILTER_PROCESS_SD` | 0.02 / month | State-evolution process noise $q_i$ (exposure wander); tied to M1 §3.4 turnover scale |
| `OP_BUCKET_WIDTH` | 0.05 (β units) | Open-Protocol E-tier coarsening granularity (§6.3.2); sets $r_{\text{E}}$'s floor |
| `DEMO_BOOK_N` | 15 | Demo book size (card wow-demo) |
| `FILTER_VECTOR_JOINT` | False (per-factor in v1) | Whether the live filter is multivariate over factors (§3.4) |

### 6.7 Implementation architecture

- **New module `src/quant_allocator/flagships/book_xray/fusion.py`** — pure
  functions over per-manager tier observations: `measurement_posterior(...)`,
  `book_posterior(weights, means, sds)`, `provenance(weights, sds)`, and the live
  `kalman_exposure_path(observations, tiers, process_sd)`. No rendering, no I/O
  (S2 §5 convention). The static functions are the demo; the filter is the live
  estimator — one module, both code paths.
- **Consumes, does not re-fit:** the **S1** β posterior (`skill_ledger/empirical.py`
  or the full model's β draws — import), the **M1** measured exposure path and drift
  onset/slope (`flagships/drift/detector.py`), the **S5** short-sleeve factor split,
  and **S3/S4** turnover/sell-discipline reads for $q_i$ — all as inputs to the
  fusion, never reimplemented here.
- **Reads the X1 registry** for `EXPOSURE_MEAS_SD` (the per-tier $r_\tau$) — nothing
  downstream hand-copies a tier-noise number (X1 §6 doctrine).
- **Demo — `src/quant_allocator/demo_data/p2_xray.py`** (imports `fusion.py`; same
  code path as any live build, synthetic input only). Builds the 15-manager book on
  a shared `simulate_market`, emits tiers per manager via `emit_tiers`, fuses, and
  writes committed JSON to `site/data/p2_xray.json` via `_emit.write_json`; **CI
  renders the page from that JSON only — CI never computes** (demo-layer doctrine).
- **Depends:** X1 (exposure-measurement-error rows — hard), S1 (β posterior), M1
  (measured path + drift), S5 (short split), S3/S4 (P-tier stability qualifier), the
  simulator (multi-manager roster + three-tier emission — built; E-tier coarsening —
  small new). **numpy only** for the demo; no new runtime dependency.
- **Effort:** **L** (card estimate) — the most ambitious card in the portfolio, a
  research program disguised as a project. MVP = **two-tier (R+E) fusion on a
  synthetic roster before touching P** (card), strictly after X1 and S1.

### 6.8 Go-live requirements (demo-page box, expanded)

- **Data ask:** monthly returns + factor set (R) for the whole book; Open-Protocol
  risk buckets (E) where disclosed; dated holdings (P) where position-transparent.
  The book renders at **any** tier mix; higher tiers tighten the band, none is
  required to render.
- **Sample required:** the **fusion** is honest at any $T$ (it is a measurement with
  a stated band); the **information-gain claim** requires the X1 exposure rows to
  supply the per-tier noise, and the gate must clear the `INFO_GAIN_FLOOR` on the
  book's actual mix. Where it does not, the reconciliation table ships instead.
- **Build effort:** **L**, strictly sequenced after X1 (tier-noise calibration) and
  S1 (β posterior); two-tier MVP first, P tier last.
- **Go-live box (demo page):** data ask = returns (R) + buckets (E) + holdings (P),
  any mix; sample = any $T$ to render, X1 rows required for the information-gain
  claim; effort = L (phase-2 flagship).

## 7. Deeper reading

**Canonical references (read in this order):**

1. **Kalman, R. E. (1960), "A New Approach to Linear Filtering and Prediction
   Problems," *Transactions of the ASME — Journal of Basic Engineering*.** The
   recursive optimal estimator for a linear-Gaussian state-space model — predict the
   latent state forward, correct it by each observation weighted by a gain balancing
   process and measurement noise. P2's temporal fusion is exactly this filter, with
   the transparency tiers as observations of one latent exposure path.
2. **Durbin, J. & Koopman, S. J., *Time Series Analysis by State Space Methods*
   (2nd ed.).** The modern reference for state-space models with irregular and
   mixed-frequency observations and the correct treatment of missing data as pure
   time-updates — precisely P2's mixed cadence (monthly buckets, quarterly holdings,
   returns-derived readings).
3. **Fuller, W. A. (1987), *Measurement Error Models*.** The errors-in-variables
   theory of estimating with a variable observed through noise of known variance —
   why carrying each tier's $r_\tau^2$ explicitly is the honest move and why treating
   an inferred beta as exact is a bias, not merely imprecision.
4. **Gelman, Carlin, Stern, Dunson, Vehtari & Rubin, *Bayesian Data Analysis*
   (3rd ed.), ch. 5 & 13.** Hierarchical aggregation and precision-weighted pooling —
   the book posterior as a precision-weighted fusion under a weak common prior, the
   same machinery S1 applies to alphas, here applied to exposures.
5. **Open Protocol Enabling Technology (OPET / AIMA risk-reporting template).** The
   E-tier data standard: the risk-exposure bucket schema whose granularity sets
   $r_{\text{E}}$ and which the go-live transparency ask names (shared with M1).

**Questions you should be able to answer after reading this page:**

- **Explain the fusion to a non-quant.** Why you do not average fifteen exposure
  readings equally, why a reading you trust to ±0.02 should dominate its own
  posterior over one you trust only to ±0.25, and why the book's remaining
  uncertainty concentrates in the opaque, large-capital sleeves (a sum of squares:
  $\operatorname{Var}[B] = \sum c_i^2 P_i$ — the biggest $c_i^2 P_i$ dominates).
- **State what the Kalman filter buys over the static fusion.** Why exposure is a
  *path*, not a fixed number; why the band must *grow* between filings (the exposure
  could have drifted) and *shrink* at each disclosure (a new reading of known
  precision); and why a quarterly holdings snapshot is near-exact on its date but
  ages toward uncertainty until the next one. Work the predict/update recursion by
  hand once.
- **Explain the information-gain gate and why it is the card's reason to exist.** Why
  a fusion that is no tighter at E than at R is *decoration*, how the gate measures
  the book-band tightening on simulator ground truth, and what the reconciliation-
  table fallback is when the gate fails.
- **Draw the boundaries.** Why P2 is not P1 (it measures the book, it does not
  allocate), not M4 (it aggregates each manager's own exposure under independence,
  it does not measure cross-manager overlap/crowding), and not a returns-based
  style-drift *verdict* (the R-tier exposure carries its full measured noise, never
  a claim). Say precisely what independence assumption the book variance rests on and
  what M4 would add.
- **Name the fusion contract.** Which card supplies each tier's exposure observation
  (S1 β posterior at R, M1 measured path at E, holdings + S5 short-split at P), which
  supplies the drift term (M1), which qualifies P-tier stability (S3/S4), and which
  supplies the per-tier measurement-error variances (X1) — and why P2 *cites* rather
  than *re-derives* every one of them.

## 8. Method-review gate rulings (2026-07-07)

1. **X1 exposure-measurement-error rows: confirmed not yet a committed atlas
   output.** They are scheduled as an X1 volume-1 docket item (wave 3). The
   provisional `EXPOSURE_MEAS_SD` values (0.02 / 0.08 / 0.25) are approved for
   the demo, and the page must state their provenance ("provisional pending the
   atlas exposure rows") on the skepticism-dial panel.
2. **Per-factor filtering approved for v1 and the demo** (the demo is
   single-factor net beta); `FILTER_VECTOR_JOINT` stays deferred to the P-phase
   build.
3. **Binding page copy confirmed:** the reconciliation-table fallback (the
   gate-1 failure state) and the cross-manager-independence boundary (overlap
   and crowding belong to M4; the book variance omits covariance cross-terms by
   design). The tier-monotonicity invariant (§6.4 gate 5) is test-pinned at
   build.
4. **E-tier bucket-coarsening emission approved as batch-3 substrate**
   (`OP_BUCKET_WIDTH` = 0.05, off-by-default byte-identical, dial-guard test —
   the `net_drift` discipline).
5. **Demo scope:** the static-fusion variant is the committed exhibit; the
   Kalman-path panel may render as a secondary exhibit from the same generator.
   Constants confirmed: `BOOK_PRIOR_MEAN/SD` = 0.20/0.50, `INFO_GAIN_FLOOR` =
   0.20, `FILTER_PROCESS_SD` = 0.02/mo, `DEMO_BOOK_N` = 15. Sequencing: the P2
   demo builds in batch 3 on the provisional constants; the live filter and the
   info-gain atlas rows are wave-3 scope, strictly after X1 volume 1.
6. **Name collisions ruled (renames on P2's side):** the demo roster's
   "Hollowmere Capital" (claimed by M4), "Brackenfell Partners" (confusable
   with M4's Brackenford Partners), and "Wexford Capital" (confusable with E3's
   Wexford Green Capital) are replaced at build, checked against the full
   cross-card name inventory.
