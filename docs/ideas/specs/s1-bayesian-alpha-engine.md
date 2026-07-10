# S1 · Hierarchical Bayesian Alpha Engine — Method Spec

**Date:** 2026-07-06
**Status:** Authored — implementation-ready
**Card:** [`docs/ideas/2026-07-05-idea-cards.md`](../2026-07-05-idea-cards.md) § S1
**Demo:** gallery page `s1.html` (posterior strip; closed-form variant, §3.7)

## 1. What this is

This engine takes a roster of managers, each with a short track record of
monthly returns, and produces for every one of them a **posterior alpha**: an
uncertainty-adjusted estimate shrunk toward the relevant strategy peer group.
Alongside each estimate it reports an honest uncertainty band (a 90% credible
interval), the probability that the manager's true skill is positive, and an
advisory capital band. The audience is an allocator deciding whom to hire, whom
to size up, and how to talk to a manager about their numbers — at the moment
when the only evidence available is three to five years of monthly returns.

The core move is *shrinkage*. Instead of trusting each manager's own trailing
alpha at face value, the engine pulls every estimate partway toward the average
of that manager's strategy peers. How far it pulls is not arbitrary: a manager
whose own record is short and noisy gets pulled hard, and a manager whose record
is long and clean barely moves. The output replaces a single confident-looking
number ("this manager made 6% alpha") with a calibrated statement ("skill is
most likely around 3%, and here is the range we can actually defend"). That
honesty is the product.

## 2. Why we use it

The decision problem is ranking managers on skill when the data are too thin to
measure skill precisely. At 36–60 monthly observations, a per-manager
ordinary-least-squares (OLS) alpha is mostly noise. Concretely: a genuinely good
manager with a true annualized information ratio of 0.5 produces an expected
t-statistic of only about $0.5\sqrt{60/12} \approx 1.1$. Against a standard 5%
two-sided test, that is statistical power below 30% — the good manager fails to
look significant more than two times in three. A ranking built directly on these
estimates can therefore reward an extreme sampling draw rather than durable skill.

The naive alternatives fail for reasons worth stating plainly. *Rank on trailing
alpha* is the default, and it is exactly the failure above: the top of the list
is dominated by sampling noise. *Apply a significance filter* (keep only
managers whose alpha is statistically significant) throws away almost every real
manager, because at this sample size almost nobody clears the bar — and the few
who do are disproportionately the lucky. False-discovery-rate machinery, built
for thousands of simultaneous tests, has nothing to work with at $n$ = tens of
managers; there simply is not enough cross-sectional signal to estimate a null
distribution. Shrinkage instead borrows strength across the cross-section and
carries its own uncertainty. Whether that improves rank recovery is an empirical
validation question, not a property established by the pinned gallery roster.

The engine improves three decisions:

- **Select** — rank on the posterior mean and on $P(\alpha_i > 0)$, not on raw
  trailing alpha.
- **Size** — map posterior uncertainty to advisory weight bands, so a
  wide-interval manager is not sized like a narrow-interval one.
- **Engage** — "your alpha interval, honestly stated" replaces false precision
  in a manager conversation.

## 3. How it works

### 3.1 The mental model, in prose

Imagine two managers in the same strategy group. One has a 60-month record and a
trailing alpha of 6%. The other has a 36-month record and a trailing alpha of
6%. They report the same number, but they have not earned the same belief: the
longer record is stronger evidence. Shrinkage formalizes exactly this. It asks,
for each manager, *how much does this manager's own data actually tell us?* —
and blends the manager's own estimate with the group's average in that
proportion. Lots of clean data: trust the manager's own number. Little noisy
data: trust the group average. The blending weight is the whole idea.

Where does the group average get its authority? From the other managers in the
strategy. If credit-relative-value managers as a class have historically shown a
skill dispersion of a few percent, that fact is informative about any one
credit-RV manager whose own record is too short to speak for itself. This is why
the model is *hierarchical*: individual managers are treated as draws from a
strategy-level distribution, and estimating that distribution lets each manager
borrow strength from the others.

### 3.2 A worked toy example

Take one manager with an OLS alpha of $\hat\alpha^{\text{OLS}} = 0.20$
(annualized, i.e. 20%) and a standard error on that estimate of
$\text{se} = 0.10$. Suppose the strategy peer group's average alpha is
$\hat\mu = 0.08$ and the estimated true dispersion of skill across the group is
$\hat\tau = 0.10$ (so $\hat\tau^2 = 0.01$, and $\text{se}^2 = 0.01$ as well).

The shrinkage weight is

$$w = \frac{\hat\tau^2}{\hat\tau^2 + \text{se}^2}
     = \frac{0.01}{0.01 + 0.01} = 0.5.$$

So the posterior alpha is a 50/50 blend:

$$\hat\alpha^{\text{post}} = w\,\hat\alpha^{\text{OLS}} + (1-w)\,\hat\mu
     = 0.5 \times 0.20 + 0.5 \times 0.08 = 0.14.$$

The 20% trailing number becomes a 14% posterior estimate — pulled 6 points
toward the peer mean because the manager's own estimate was exactly as noisy as
the spread of skill in the group. If that same manager had a longer record, its
$\text{se}$ would shrink; say $\text{se} = 0.05$, so $\text{se}^2 = 0.0025$.
Then $w = 0.01 / (0.01 + 0.0025) = 0.8$, and the posterior is
$0.8 \times 0.20 + 0.2 \times 0.08 = 0.176$ — much closer to the manager's own
number, because now the data speak louder. Same trailing alpha, different belief:
that is the mechanism, and everything below is this idea made precise and
hierarchical.

### 3.3 The observation model

For manager $i$ in strategy group $s(i)$, in month $t$, with excess return
$y_{i,t}$ and factor-return vector $f_t$:

$$y_{i,t} = \alpha_i + \beta_i^\top f_t + \varepsilon_{i,t}, \qquad
\varepsilon_{i,t} \sim \mathcal{N}(0, \sigma_i^2)$$

where:

- $y_{i,t}$ — manager $i$'s return in month $t$, in excess of the risk-free rate
  (a monthly decimal, e.g. 0.01 for 1%).
- $\alpha_i$ — manager $i$'s true skill: average return not explained by factor
  exposure. This is the quantity we want.
- $\beta_i$ — manager $i$'s vector of factor loadings (exposures).
- $f_t$ — the vector of factor returns in month $t$ (the same for all managers
  in a strategy).
- $\varepsilon_{i,t}$ — the idiosyncratic residual: what the factors do not
  explain in month $t$.
- $\sigma_i$ — the standard deviation of that residual (manager $i$'s
  idiosyncratic volatility).
- $\mathcal{N}(0, \sigma_i^2)$ — states that residuals are Normal with mean zero
  and variance $\sigma_i^2$.

In words: each month's return is skill, plus factor exposure times factor
returns, plus mean-zero noise. All quantities are **monthly decimals**
internally; reporting annualizes $\alpha$ by ×12 and volatilities by ×√12. A
Student-t error variant (heavier tails, with degrees of freedom
$\nu \sim \text{Gamma}(2, 0.1)$ constrained to $\nu > 2$) is available as a
robustness re-run for fat-tailed strategies, not the default.

### 3.4 The pooling structure (what makes it hierarchical)

$$\alpha_i \sim \mathcal{N}(\mu_{s(i)}, \tau_{s(i)}^2), \qquad
\mu_s \sim \mathcal{N}\!\big(0,\; (0.02/12)^2\big), \qquad
\tau_s \sim \text{HalfNormal}(0.03/12)$$

where:

- $\mu_s$ — the average true alpha of strategy group $s$ (the peer mean each
  manager is shrunk toward).
- $\tau_s$ — the dispersion of true skill *within* group $s$: how spread out
  genuine alphas are across managers of the same strategy. This is the
  load-bearing quantity.
- $\alpha_i \sim \mathcal{N}(\mu_{s(i)}, \tau_{s(i)}^2)$ — each manager's true
  alpha is a draw from their group's skill distribution.
- The $\mu_s$ and $\tau_s$ lines are *hyperpriors*: our prior beliefs about the
  group-level quantities before seeing data. Scales are monthly decimals, so
  $0.02/12$ is a 2%-per-year scale expressed monthly.

The hyperprior scale on $\tau_s$ is the most consequential modeling choice.
At $n$ = tens of managers, $\tau_s$ is only weakly identified by the data, so
the prior on it has to carry real information rather than being a throwaway.
Published cross-sectional dispersions of *skill* (not of raw, noisy alpha) in
hedge-fund panels — the posterior-alpha dispersions in Kosowski–Naik–Teo, the
random-effects estimates in Harvey–Liu (both summarized in §3.8) — put plausible
annualized $\tau$ in the 1–4% range. A $\text{HalfNormal}(3\%/\text{yr})$ prior
covers that range while still letting the data pull the estimate downward toward
zero if the roster shows little real dispersion. **Prior sensitivity is a
first-class output of this engine, not an appendix** (§3.6).

### 3.5 Betas and idiosyncratic volatility

$$\beta_i \sim \mathcal{N}(b_s, \Sigma_s), \qquad
\sigma_i \sim \text{HalfNormal}(0.05)$$

where $b_s$ and $\Sigma_s$ are weakly informative, per-strategy prior mean and
covariance for the factor loadings, and the $\text{HalfNormal}(0.05)$ prior on
$\sigma_i$ says idiosyncratic monthly volatility is positive and on the order of
a few percent. The betas are estimated jointly with alpha, so uncertainty about
factor exposure correctly widens the alpha interval rather than being hidden.

At data tier E (see §6.1) we replace the diffuse $\beta_i$ prior with
$\mathcal{N}(\hat\beta_i^{\text{measured}}, 0.10^2)$ per factor: measured
exposures pin the betas near their observed values, which removes
beta-estimation noise from the alpha and tightens the interval. This is the
engine's concrete argument for exposure transparency — the value of that
transparency shows up directly as a narrower alpha band. It is the
Pástor–Stambaugh mechanism (§3.8): a sharper prior on the loadings sharpens the
inference on skill.

### 3.6 Estimation, outputs, and the sensitivity protocol

**Estimation and convergence gates.** The full model is fit by Markov-chain
Monte Carlo (MCMC) in PyMC using the No-U-Turn Sampler (NUTS): 4 chains ×
1,000 draws after 1,000 tuning steps. The $\alpha_i$ are given a **non-centered
parameterization** (mandatory — see §7 for why): with small groups the direct
"centered" form produces a pinched funnel geometry that the sampler cannot
explore, throwing divergences. Merge-blocking convergence gates: the
Gelman–Rubin statistic $\hat R < 1.01$ on every parameter, bulk effective sample
size (ESS) > 400, and zero divergences. A run that fails these gates is a bug,
not a result — its numbers are not reported.

**Outputs.** Per manager: posterior mean $\alpha_i$ (annualized), a 90% credible
interval, $P(\alpha_i > 0)$, and the shrinkage movement (posterior vs OLS, in
basis points and in rank places). Per strategy: posterior $\mu_s$ and $\tau_s$.

**Sensitivity protocol.** Because the $\tau$ prior is load-bearing, the engine
re-fits at $\tau$-prior scales of ×0.5 and ×2 and reports the Kendall-$\tau$ rank
stability across the three fits. If top-quartile membership flips for more than
2 of 20 managers across that range, the engine reports **"prior-dominated at this
sample"** and the decision layer falls back to interval-only reporting (the S2
tearsheet). That is the kill criterion doing its job — surfacing when the data
cannot support a ranking — not a failure being hidden.

### 3.7 The closed-form demo variant (what the gallery shows)

The full engine is MCMC, but there is a special case with a pencil-and-paper
answer, and the gallery page uses exactly that case so the mechanism is visible
without a sampler. If we plug in each manager's estimated idiosyncratic
volatility $\hat\sigma_i$ (treating it as known rather than co-estimated), the
Normal-prior/Normal-likelihood posterior for $\alpha_i$ has the closed form

$$\hat\alpha_i^{\text{post}} = w_i\,\hat\alpha_i^{\text{OLS}} +
(1 - w_i)\,\hat\mu_s, \qquad
w_i = \frac{\hat\tau^2}{\hat\tau^2 + \text{se}(\hat\alpha_i)^2}$$

where:

- $\hat\alpha_i^{\text{OLS}}$ — manager $i$'s raw OLS alpha from the factor
  regression.
- $\text{se}(\hat\alpha_i)$ — the standard error of that OLS alpha (how noisy the
  raw estimate is; shrinks as the record lengthens).
- $\hat\mu_s$ — the estimated group mean alpha.
- $\hat\tau^2$ — the estimated true skill variance within the group.
- $w_i$ — the shrinkage weight: the fraction of the way the posterior sits toward
  the manager's own estimate rather than the peer mean.

In words: the posterior is a precision-weighted blend of the manager's own
number and the peer mean, and the weight is exactly the ratio of true-skill
variance to (true-skill variance + estimation variance). When the estimate is
precise ($\text{se}$ small), $w_i \to 1$ and the manager keeps their own number;
when it is noisy ($\text{se}$ large), $w_i \to 0$ and the manager is pulled to
the peer mean.

The group-level quantities are filled in by *empirical Bayes* — estimating the
prior from the data itself via the method of moments:

$$\hat\mu_s = \operatorname{mean}\big(\hat\alpha^{\text{OLS}}_{i \in s}\big),
\qquad
\hat\tau^2 = \max\!\Big(0,\;
\operatorname{var}\big(\hat\alpha^{\text{OLS}}_{i \in s}\big)
- \overline{\text{se}^2}\Big).$$

The second line is the crux and worth reading in words: the *observed* spread of
OLS alphas across the group, $\operatorname{var}(\hat\alpha^{\text{OLS}})$, is
inflated by estimation noise — it equals true-skill spread *plus* average
estimation variance. Subtracting the average estimation variance
$\overline{\text{se}^2}$ backs out the true-skill spread $\hat\tau^2$. If the
observed spread is no larger than what pure noise would produce, the subtraction
hits the $\max(0, \cdot)$ floor: $\hat\tau^2 = 0$, meaning "no detectable skill
dispersion," and every manager is shrunk all the way to the peer mean. That is
the correct answer when the roster genuinely cannot be told apart.

The gallery page's footnote states it uses this variant and points here. The
live build is the full hierarchical MCMC model; this closed form is the
intuition, not the product.

### 3.8 What the canonical papers showed

Five papers underwrite the design; each is here because it settles a specific
choice.

- **Baks, Metrick & Wachter (2001, *Journal of Finance*).** Frames manager
  selection as a prior over skill and asks how a Bayesian investor with any prior
  belief should allocate. The lesson the engine takes: even an investor who is
  quite skeptical that alpha exists will still allocate to managers whose data
  are strong enough — shrinkage does not mean giving up on skill, it means
  demanding proportionate evidence.
- **Kosowski, Naik & Teo (2007, *Journal of Financial Economics*).** Applies a
  Bayesian, cross-sectional approach to hedge-fund alphas and shows the resulting
  posterior alphas predict future performance better than raw OLS alphas do.
  This is the direct empirical warrant that the shrinkage move improves
  out-of-sample manager ranking, which is exactly what §2 claims.
- **Harvey & Liu (2018, *Review of Financial Studies*).** Provides the modern
  random-effects / multiple-testing treatment of fund alphas, formalizing how to
  pool information across funds and haircut individual estimates for luck. It is
  the reference implementation this engine's hierarchical structure mirrors.
- **Pástor & Stambaugh (2002, *Journal of Financial Economics*).** Shows that
  bringing in information about a fund's factor exposures sharpens the inference
  about its alpha. This is the mechanism behind the tier-E upgrade in §3.5:
  pinning betas with measured exposures tightens the alpha interval.
- **Gelman (2006).** Analyzes prior choice for group-level variance parameters in
  hierarchical models and argues for half-Normal (folded-Normal) priors over the
  traditional inverse-gamma, which behaves badly when the variance is near zero —
  precisely our regime. This is why $\tau_s$ carries a $\text{HalfNormal}$ prior
  rather than the textbook conjugate default.

### 3.9 The decision layer (thin, advisory)

Advisory weight bands are read off the posterior *t-ratio*
$m_i = \mathbb{E}[\alpha_i] / \text{sd}(\alpha_i)$ — the posterior mean divided
by the posterior standard deviation. Four bands:

- $m_i < 0$ → **review**
- $0 \le m_i < 0.5$ → **minimum**
- $0.5 \le m_i < 1$ → **standard**
- $m_i \ge 1$ → **conviction**

Each band maps to a capital *range* (not a point), with floors and caps stated
in the pack. This layer is explicitly advisory — the actual portfolio optimizer
is a separate card (P1).

## 4. How to implement

Below is a self-contained, numpy-only reference implementation of the §3.7
closed-form variant. Paste it into a fresh file and adapt it; it depends on
nothing in this project. It computes OLS alpha and its standard error from
returns and factors, then applies the empirical-Bayes shrinkage and posterior
summaries using the exact formulas of §3.7.

```python
"""Closed-form empirical-Bayes shrinkage for manager alphas (teaching code).

Implements the normal-normal posterior of the S1 method spec, section 3.7:
    posterior_mean = w * ols_alpha + (1 - w) * group_mean
    w = tau2 / (tau2 + se**2)
with method-of-moments (empirical-Bayes) estimates of the group mean and the
true-skill variance tau2. numpy only; no project imports.
"""

from math import erf, sqrt

import numpy as np

# Two-tailed 90% z-score: P(|Z| < 1.6449) = 0.90.
Z_90 = 1.6448536269514722


def normal_cdf(x: float) -> float:
    """Standard-normal CDF via the error function (no scipy needed)."""
    return 0.5 * (1.0 + erf(x / sqrt(2.0)))


def ols_alpha_and_se(returns: np.ndarray, factors: np.ndarray) -> tuple[float, float]:
    """Fit y = alpha + beta @ f + eps by OLS; return (alpha, se(alpha)).

    Parameters
    ----------
    returns : shape (T,)   monthly excess returns (decimals).
    factors : shape (T, k) monthly factor returns aligned to the same months.

    The alpha is the intercept; its standard error comes from the usual
    OLS covariance sigma^2 * (X'X)^-1, with sigma^2 the residual variance.
    All quantities stay in monthly decimals here and are annualized by the
    caller.
    """
    n_months = returns.shape[0]
    # Design matrix: a column of ones (intercept = alpha) plus the factors.
    design = np.column_stack([np.ones(n_months), factors])  # shape (T, k+1)

    # Ordinary least squares, solved stably via lstsq (the normal equations).
    coefficients, *_ = np.linalg.lstsq(design, returns, rcond=None)
    alpha = coefficients[0]

    # Residual variance with the standard degrees-of-freedom correction.
    residuals = returns - design @ coefficients
    dof = n_months - design.shape[1]
    residual_var = float(residuals @ residuals) / dof

    # Var(coefficients) = residual_var * (X'X)^-1; alpha is the [0, 0] entry.
    xtx_inv = np.linalg.inv(design.T @ design)
    se_alpha = sqrt(residual_var * xtx_inv[0, 0])
    return float(alpha), se_alpha


def empirical_bayes_shrinkage(
    ols_alphas: np.ndarray,
    ses: np.ndarray,
) -> dict[str, np.ndarray]:
    """Shrink a group's OLS alphas toward their peer mean (section 3.7).

    Parameters
    ----------
    ols_alphas : shape (n,) OLS alpha per manager in ONE strategy group.
    ses        : shape (n,) standard error of each OLS alpha.

    Returns per-manager posterior summaries plus the group-level estimates.
    Call once per strategy group; managers are only pooled with their peers.
    """
    # Empirical-Bayes group mean: the average of the raw estimates.
    group_mean = float(np.mean(ols_alphas))

    # Method-of-moments true-skill variance: observed spread of the estimates
    # minus the average estimation variance. Observed spread = true spread +
    # noise, so subtracting the noise backs out the true spread. Floor at 0:
    # if the estimates are no more spread out than noise alone would make them,
    # there is no detectable skill dispersion and everyone shrinks fully.
    observed_var = float(np.var(ols_alphas, ddof=1))
    mean_estimation_var = float(np.mean(ses**2))
    tau2 = max(0.0, observed_var - mean_estimation_var)

    # Shrinkage weight per manager: true-skill variance as a fraction of
    # (true-skill variance + this manager's estimation variance). Precise
    # estimates (small se) keep their own number; noisy ones pull to the mean.
    weights = tau2 / (tau2 + ses**2)

    # Posterior mean: precision-weighted blend of own estimate and peer mean.
    posterior_mean = weights * ols_alphas + (1.0 - weights) * group_mean

    # Posterior variance = 1 / (1/tau2 + 1/se^2). When tau2 == 0 the posterior
    # collapses onto the peer mean, so its per-manager variance is zero.
    if tau2 > 0.0:
        posterior_var = 1.0 / (1.0 / tau2 + 1.0 / ses**2)
    else:
        posterior_var = np.zeros_like(ses)
    posterior_sd = np.sqrt(posterior_var)

    # 90% credible interval and P(alpha > 0) from the Normal posterior.
    ci_low = posterior_mean - Z_90 * posterior_sd
    ci_high = posterior_mean + Z_90 * posterior_sd
    prob_positive = np.array(
        [normal_cdf(m / s) if s > 0 else float(m > 0)
         for m, s in zip(posterior_mean, posterior_sd)]
    )

    return {
        "group_mean": np.full_like(ols_alphas, group_mean),
        "tau": np.full_like(ols_alphas, sqrt(tau2)),
        "shrinkage_weight": weights,
        "posterior_mean": posterior_mean,
        "posterior_sd": posterior_sd,
        "ci_low": ci_low,
        "ci_high": ci_high,
        "prob_positive": prob_positive,
    }


if __name__ == "__main__":
    # Toy group of three managers (annualized alphas and their std errors).
    alphas = np.array([0.20, 0.08, -0.03])
    errors = np.array([0.10, 0.06, 0.09])
    result = empirical_bayes_shrinkage(alphas, errors)
    for i, code in enumerate(["M1", "M2", "M3"]):
        print(
            f"{code}: OLS {alphas[i]:+.3f} -> post "
            f"{result['posterior_mean'][i]:+.3f} "
            f"(w={result['shrinkage_weight'][i]:.2f}, "
            f"P(a>0)={result['prob_positive'][i]:.2f})"
        )
```

The `ols_alpha_and_se` helper produces the two inputs the shrinkage step needs
(`ols_alphas` and `ses`) from raw returns and factors; in a full run you would
call it once per manager, group the results by strategy, and call
`empirical_bayes_shrinkage` once per group.

## 5. Reading the demo

The gallery page (`s1.html`) is a ledger: one row per manager, 20 managers
across two synthetic strategy groups (A and B). Each row shows the same
manager's alpha twice — once as the raw OLS estimate and once after shrinkage —
so the correction is visible side by side. The headline number is the reshuffle:
**7 of 20 managers change rank** once each estimate is shrunk toward its
strategy peers.

**What you are looking at.** Read one row to see the mechanism. Osprey Hollow
Partners (A10) has the top raw alpha at +29.3%, and after shrinkage it is still
+25.4% and still ranked #1 — a long-tenured, high-conviction manager barely
moves. Contrast Cinderbank Capital (B10): a raw +19.6% (rank #3) is pulled all
the way down to +13.2% (rank #4), because its 36-month record earns a shrinkage
weight of only 0.46 — the peer mean gets nearly as much say as its own number.
Alderbrook Partners (A01) sits at the bottom: a raw −7.4% softens to −4.1%, with
$P(\alpha > 0)$ of just 0.20. Extreme noisy estimates are pulled toward their
peer mean. That produces a different, uncertainty-aware ordering; it does not by
itself prove a better true-skill ordering.

**How to read it.** Each visual element maps to a piece of the method:

- **Two interval bands per row** — the left band is the OLS alpha, the right is
  the posterior alpha. Each band is the 90% credible interval; the tick inside
  it is the point estimate. The posterior band typically sits tighter and closer
  to the group mean than the OLS band.
- **The `OLS #x → posterior #y` line and the ▲/▼ chip** — the rank before and
  after shrinkage; the chip flags whether the manager rose, fell, or held.
  Movers carry an accent stripe down the left edge of the row.
- **The advisory band pill** (review / minimum / standard / conviction) — the
  capital band from the posterior t-ratio $m_i$ of §3.9.
- **$P(\alpha > 0)$** — the posterior probability the manager's true alpha is
  positive. It is capped at ">0.99": the engine never prints certainty, because
  a displayed 1.00 is only six-digit rounding, not proof.
- **The "Order by" toggle** — re-sorts the ledger between OLS and posterior rank
  so you can watch the reshuffle directly.

What an allocator should conclude: the raw ranking and the posterior ranking
disagree for 7 of these 20 managers, and the disagreements are concentrated in
the short-record, heavily-shrunk names. The exhibit demonstrates peer shrinkage,
not better true-skill recovery: against the simulator's known truth, this pinned
roster's posterior order is slightly worse than OLS. Repeated-grid rank recovery
and live calibration remain binding gates before the order informs sizing.

**Displayed-field reproduction map.**

| Displayed field | JSON field | Generator | Enforcing test |
| --- | --- | --- | --- |
| OLS alpha and 90% interval | `managers[].ols_alpha.{point,ci_lo,ci_hi}` | `demo_data/s1_ledger.py` | `tests/demo_data/test_s1_ledger.py` |
| Posterior alpha and 90% interval | `managers[].posterior_alpha.{point,ci_lo,ci_hi}` | `demo_data/s1_ledger.py` | `tests/demo_data/test_s1_ledger.py` |
| OLS → posterior rank | `managers[].{ols_rank,posterior_rank}` | `demo_data/s1_ledger.py` | `tests/site/test_s1.py` |
| Shrinkage weight and positive probability | `managers[].{shrinkage_weight,prob_positive}` | `demo_data/s1_ledger.py` | `tests/demo_data/test_s1_ledger.py` |
| Advisory band | `managers[].advisory_band` | `demo_data/s1_ledger.py` | `tests/demo_data/test_s1_ledger.py` |

## 6. Honest limits & go-live

### 6.1 Data contract per tier

| Tier | Inputs | What it buys |
| --- | --- | --- |
| R (minimum) | Monthly net returns per manager (decimals, `PeriodIndex` freq `M`); ≥24 months to enter, ≥36 for full standing; strategy label per manager; risk-free series; strategy-appropriate factor returns aligned on the same months | The full model runs. |
| E | Monthly (or quarterly) factor/sector/gross/net buckets (Open Protocol-aligned) | Measured exposures center tight priors on $\beta_i$ (§3.5), removing beta-estimation noise from the alpha — the Pástor–Stambaugh effect. |
| P | Holdings/trade snapshots → breadth and, where measurable, information coefficient (IC) | Enters v1 only as a documented prior adjustment on the manager's skill scale; formal tier fusion is card P2, not this engine. |

Factor sets by strategy: FF5 + momentum for equity long/short; Fung–Hsieh 7 for
macro/trend; a credit factor set on **GLM-unsmoothed** returns (return
unsmoothing is a required pre-processing step for illiquid strategies — see the
S2 spec §3 for the shared pipeline). Missing months: a manager with more than 2
gaps in the window is excluded and flagged, never silently interpolated.

### 6.2 Power and validation plan

The engine is validated on a simulator with *known* true alphas, so recovery can
be measured rather than assumed. Grid: roster size ∈ {10, 20, 40} × window
length $T$ ∈ {36, 48, 60} months × true annualized skill dispersion ∈ {1%, 2%,
4%} × 1–3 strategy groups; ≥200 seeded replications per cell (with per-module RNG
streams so cells are independent).

Acceptance gates, per cell:

1. **Coverage** — empirical coverage of the 90% credible interval lands within
   ±5 percentage points of the nominal 90%.
2. **Rank recovery** — the Kendall $\tau$ between the posterior ranking and the
   true-alpha ranking beats the OLS ranking's Kendall $\tau$ in ≥90% of
   replications.
3. **Calibration** — the $P(\alpha > 0)$ bins are monotone against realized
   frequency (checked on a reliability curve, visually and by a slope test).
4. **Hyperparameter recovery** — the posterior $\tau_s$ interval contains the
   true dispersion in ≥85% of replications.

Failing gate 1 or 3 kills the engine as specified: **miscalibrated uncertainty is
worse than none**. Failing gate 2 in the low-dispersion cells *only* is an honest
finding to report, not a defect to hide — when nobody's true skill differs, no
method can rank them. Those cells are contributed to the Atlas (card X1) as its
S1 rows.

### 6.3 Adoption and packaging

The ledger pack follows the Interval design system: one row per manager — a
posterior strip (IntervalStat), a movement-vs-OLS marker, $P(\alpha > 0)$, and
the advisory band. Copy rules are strict: "shrunk toward strategy peers by the
weight your track length earns," never "your alpha was cut." The pack's appendix
exposes the $\tau$-prior scale as an adjustable dial (a Dietvorst-style control),
so a skeptical reader can drag the skepticism up or down and watch the bands
respond — the output is an input to judgment, not a verdict. Interval-only
reporting throughout; a bare point alpha with no band is a design-system lint
error.

### 6.4 Go-live requirements

- **Data:** monthly net returns, ≥36 months, for ≥10 managers with strategy
  labels; the chosen factor sets per strategy; a risk-free series.
- **Infra:** a Python + PyMC environment, and one analyst able to read
  convergence diagnostics (the gates in §3.6 are mechanical).
- **Effort:** M (~6 sessions: model 2, validation grid 2, sensitivity 1, pack 1).
  Upstream dependency: the Fung–Hsieh 7-factor adapter for macro/trend managers
  (FF5 is already built). Known risk: divergences on small groups, already
  mitigated by the non-centered parameterization and informative hyperpriors;
  residual cases tighten the $\tau$ prior and are documented.

### 6.5 Implementation architecture

- `src/quant_allocator/flagships/skill_ledger/model.py` — the PyMC model builder
  (`build_model(returns, factors, groups, config) -> pm.Model`); the config
  dataclass carries all prior scales as explicit named fields (no magic numbers
  in the model body).
- `.../skill_ledger/empirical.py` — the §3.7 closed-form variant
  (`shrink_alphas(ols_alphas, ses, groups) -> ShrinkageResult`); this is what the
  demo-data generator imports.
- `.../skill_ledger/report.py` — the ledger table and pack-JSON emission.
- Depends on: the simulator (for validation), the factor adapters (FF5 exists;
  the FH7 adapter is a named prerequisite for macro coverage), and PyMC (a new
  dependency, live build only — the demo variant is numpy-only).

## 7. Deeper reading

**Canonical papers (read in this order).** Each entry is expanded in §3.8; the
one-line summaries here are the reason each is load-bearing.

- **Baks, Metrick & Wachter (2001, JF)** — priors over skill, and why even a
  skeptic allocates when the evidence is strong enough.
- **Kosowski, Naik & Teo (2007, JFE)** — Bayesian posterior alphas predict
  hedge-fund performance better than OLS alphas; the empirical warrant for
  shrinkage.
- **Harvey & Liu (2018, RFS)** — the modern random-effects reference this
  engine's hierarchy mirrors.
- **Pástor & Stambaugh (2002, JFE)** — pinning factor exposures sharpens the
  alpha inference; the tier-E mechanism.
- **Gelman (2006)** — prior choice for group-level variance, and why
  HalfNormal beats inverse-gamma near zero.

**Derivations to own (work each by hand once).**

1. The normal-normal posterior (§3.7) by completing the square: with prior
   $\alpha \sim \mathcal{N}(\mu, \tau^2)$ and likelihood
   $\hat\alpha \mid \alpha \sim \mathcal{N}(\alpha, \text{se}^2)$, the posterior
   precision is $1/\tau^2 + 1/\text{se}^2$ and the shrinkage weight is just
   precision-weighting. This one derivation is the whole engine's intuition.
2. $t \approx \text{IR}_{\text{ann}}\sqrt{T/12}$ from the definition of the alpha
   t-statistic — and therefore why $T = 60$ cannot distinguish an IR of 0.5 from
   zero (the §2 power statement; derive it).
3. Why the non-centered parameterization
   ($\alpha_i = \mu_s + \tau_s\,\tilde\alpha_i$,
   $\tilde\alpha_i \sim \mathcal{N}(0, 1)$) removes the funnel: what the posterior
   geometry of $(\tau, \alpha)$ looks like when the data are weak, and why the
   sampler stalls in the centered form.
4. The empirical-Bayes moment estimator for $\tau^2$ (§3.7) and why it can hit
   zero: when the variance of the estimates is no larger than the average
   estimation variance, there is no detectable dispersion to find.

**Questions you should be able to answer after reading this page.**

- Explain shrinkage to an investment committee in 60 seconds without using the
  word "Bayesian."
- Justify the $\tau$ hyperprior scale from the published skill-dispersion panels.
- State why FDR-style luck control fails at $n$ = tens of managers, and what this
  engine does instead.
- Explain what the coverage test in §6.2 proves that a backtest cannot.
