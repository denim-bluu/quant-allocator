# S1 · Hierarchical Bayesian Alpha Engine — Method Spec

**Date:** 2026-07-06
**Status:** Authored — implementation-ready
**Card:** [`docs/ideas/2026-07-05-idea-cards.md`](../2026-07-05-idea-cards.md) § S1
**Demo:** gallery page `s1.html` (posterior strip; closed-form variant, §3.6)

## 1. Problem & decision hook

At 36–60 monthly observations, per-manager OLS alphas are noise: a genuinely
good manager with true annualized information ratio 0.5 produces an expected
t-statistic of about $0.5\sqrt{60/12} \approx 1.1$ — power below 30% against
a 5% two-sided test. Rankings built on such estimates hire luck. This engine
replaces per-manager point alphas with **posterior alphas that pool the
cross-section**: each manager's estimate is shrunk toward their strategy
peers by exactly as much as their own data fails to speak.

Decisions improved: **select** — rank on posterior mean and $P(\alpha_i>0)$,
not raw trailing alpha; **size** — posterior uncertainty maps to advisory
weight bands; **engage** — "your alpha interval, honestly stated" replaces
false precision in conversations.

## 2. Data contract per tier

| Tier | Inputs | What it buys |
| --- | --- | --- |
| R (minimum) | Monthly net returns per manager (decimals, `PeriodIndex` freq `M`); ≥24 months to enter, ≥36 for full standing; strategy label per manager; risk-free series; strategy-appropriate factor returns aligned on the same months | The full model runs. |
| E | Monthly (or quarterly) factor/sector/gross/net buckets (Open Protocol-aligned) | Measured exposures center tight priors on $\beta_i$ (§3.3), removing beta-estimation noise from the alpha — the Pástor–Stambaugh effect. |
| P | Holdings/trade snapshots → breadth and, where measurable, IC | Enters v1 only as a documented prior adjustment on the manager's skill scale; formal tier fusion is card P2, not this engine. |

Factor sets by strategy: FF5 + momentum for equity L/S; Fung–Hsieh 7 for
macro/trend; credit set on **GLM-unsmoothed** returns (unsmoothing is a
required pre-processing step for illiquid strategies — see the S2 spec §3
for the shared pipeline). Missing months: a manager with more than 2 gaps in
the window is excluded and flagged, never silently interpolated.

## 3. Methodology

### 3.1 Observation model

For manager $i$ in strategy group $s(i)$, month $t$, with excess return
$y_{i,t}$ and factor vector $f_t$:

$$y_{i,t} = \alpha_i + \beta_i^\top f_t + \varepsilon_{i,t}, \qquad
\varepsilon_{i,t} \sim \mathcal{N}(0, \sigma_i^2)$$

All quantities are **monthly decimals** internally; reporting annualizes
$\alpha$ by ×12 and volatilities by ×√12. A Student-t error variant
($\nu \sim \text{Gamma}(2, 0.1)$, $\nu > 2$) is the robustness re-run, not
the default.

### 3.2 Pooling structure

$$\alpha_i \sim \mathcal{N}(\mu_{s(i)}, \tau_{s(i)}^2), \qquad
\mu_s \sim \mathcal{N}(0,\; (0.02/12)^2), \qquad
\tau_s \sim \text{HalfNormal}(0.03/12)$$

The hyperprior scales are the load-bearing choice. At $n$ = tens of
managers, $\tau_s$ is weakly identified, so it must carry real prior
information: published cross-sectional dispersions of *skill* (not raw
alpha) in hedge-fund panels — Kosowski–Naik–Teo posterior alphas,
Harvey–Liu random-effects estimates — put plausible annualized $\tau$ in
the 1–4% range. HalfNormal(3%/yr) covers that range while letting the data
pull downward. **Prior sensitivity is a first-class output, not an
appendix** (§3.5).

### 3.3 Betas and idiosyncratic vol

$$\beta_i \sim \mathcal{N}(b_s, \Sigma_s) \text{ (weakly informative,
per-strategy scales)}, \qquad \sigma_i \sim \text{HalfNormal}(0.05)$$

At tier E, replace the $\beta_i$ prior with
$\mathcal{N}(\hat\beta_i^{\text{measured}}, 0.10^2)$ per factor — measured
exposures pin the betas, and the alpha interval tightens accordingly. This
is the engine's concrete argument for rung 2 of the transparency ladder
(E1): the value of exposure transparency is visible as interval width.

### 3.4 Estimation and convergence gates

PyMC, NUTS, 4 chains × 1,000 draws after 1,000 tuning steps,
**non-centered parameterization** for $\alpha_i$ (mandatory: with small
groups the centered form produces funnel geometry and divergences).
Merge-blocking gates: $\hat R < 1.01$ on every parameter, bulk ESS > 400,
zero divergences. A run failing gates is a bug, not a result.

### 3.5 Outputs and sensitivity

Per manager: posterior mean $\alpha_i$ (annualized), 90% credible interval,
$P(\alpha_i > 0)$, and the shrinkage movement (posterior vs OLS, in bps and
in rank places). Per strategy: posterior $\mu_s$, $\tau_s$. Sensitivity
protocol: re-fit at τ-prior scales ×0.5 and ×2; report Kendall-τ rank
stability across the three fits. If top-quartile membership flips for more
than 2 of 20 managers across that range, the engine reports "prior-dominated
at this sample" and the decision layer falls back to interval-only reporting
(S2) — that is the kill criterion doing its job, not a failure to hide.

### 3.6 Closed-form demo variant (what the gallery shows)

With $\hat\sigma_i$ plugged in, the normal-normal posterior is

$$\hat\alpha_i^{\text{post}} = w_i\,\hat\alpha_i^{\text{OLS}} +
(1 - w_i)\,\hat\mu_s, \qquad
w_i = \frac{\hat\tau^2}{\hat\tau^2 + \text{se}(\hat\alpha_i)^2}$$

with empirical-Bayes moment estimates
$\hat\mu_s = \text{mean}(\hat\alpha^{\text{OLS}}_{i \in s})$ and
$\hat\tau^2 = \max\!\big(0,\; \text{var}(\hat\alpha^{\text{OLS}}) -
\overline{\text{se}^2}\big)$. The gallery page uses exactly this; its
footnote says so and points here. The live build is the full MCMC model —
the demo formula is the intuition, not the product.

### 3.7 Decision layer (thin, advisory)

Advisory weight bands from the posterior *t-ratio*
$m_i = \mathbb{E}[\alpha_i]/\text{sd}(\alpha_i)$: four bands
($m < 0$: review; $0 \le m < 0.5$: minimum; $0.5 \le m < 1$: standard;
$m \ge 1$: conviction), each band a capital *range*, with floors/caps stated
in the pack. Explicitly advisory — the optimizer is card P1.

## 4. Power & validation plan

Simulator grid (known true alphas): roster size ∈ {10, 20, 40} × T ∈
{36, 48, 60} × true annualized skill dispersion ∈ {1%, 2%, 4%} × 1–3
strategy groups; ≥200 seeded replications per cell (per-module RNG streams).

Acceptance gates, per cell:

1. **Coverage:** empirical coverage of the 90% credible interval within
   ±5 pp of nominal.
2. **Rank recovery:** Kendall τ between posterior ranking and true-alpha
   ranking beats the OLS ranking's Kendall τ in ≥90% of replications.
3. **Calibration:** $P(\alpha>0)$ bins are monotone against realized
   frequency (reliability curve visually and by slope test).
4. **Hyperparameter recovery:** posterior $\tau_s$ interval contains the
   true dispersion in ≥85% of replications.

Failing gate 1 or 3 kills the engine as specified (miscalibrated
uncertainty is worse than none). Failing gate 2 in the low-dispersion cells
only is an honest finding to report: when nobody differs, no method ranks.
These cells are contributed to the Atlas (X1) as its S1 rows.

## 5. Implementation architecture

- `src/quant_allocator/flagships/skill_ledger/model.py` — PyMC model
  builder (`build_model(returns, factors, groups, config) -> pm.Model`);
  config dataclass carries all prior scales as explicit named fields (no
  magic numbers in the model body).
- `.../skill_ledger/empirical.py` — the §3.6 closed-form variant
  (`shrink_alphas(ols_alphas, ses, groups) -> ShrinkageResult`); this is
  what the demo-data generator imports.
- `.../skill_ledger/report.py` — ledger table + pack JSON emission.
- Depends: simulator (validation), factor adapters (FF5 exists; FH7 adapter
  is a named prerequisite for macro coverage), PyMC (new dependency, live
  build only — the demo variant is numpy-only).
- Effort: M (~6 sessions: model 2, validation grid 2, sensitivity 1,
  pack 1). Known risk: divergences on small groups → already mitigated by
  non-centered parameterization and informative hyperpriors; residual cases
  tighten $\tau$ prior and document.

## 6. Adoption & packaging

The ledger pack (Interval system): one row per manager — posterior strip
(IntervalStat), movement-vs-OLS marker, $P(\alpha>0)$, band. Copy rules:
"shrunk toward strategy peers by the weight your track length earns," never
"your alpha was cut." The Dietvorst dial: the pack's appendix exposes the
τ-prior scale as an adjustable input so a skeptical reader can drag the
skepticism up or down and watch bands respond — the output is an input to
judgment, not a verdict. Interval-only reporting throughout; a bare point
alpha is a design-system lint error.

## 7. Go-live requirements

- Data: monthly net returns, ≥36 months, for ≥10 managers with strategy
  labels; chosen factor sets per strategy; risk-free series.
- Infra: Python + PyMC environment; one analyst able to read convergence
  diagnostics (the gates in §3.4 are mechanical).
- Effort: M. Upstream dependency: FH7 factor adapter for macro/trend
  managers (FF5 already built).

## 8. Learning notes

**Derivations to own (work each by hand once):**

1. The normal-normal posterior (§3.6) by completing the square: prior
   $\alpha \sim \mathcal{N}(\mu, \tau^2)$, likelihood
   $\hat\alpha \mid \alpha \sim \mathcal{N}(\alpha, \text{se}^2)$ ⇒
   posterior precision $= 1/\tau^2 + 1/\text{se}^2$; the shrinkage weight
   is precision-weighting. This one derivation is the whole engine's
   intuition.
2. $t \approx \text{IR}_{\text{ann}}\sqrt{T/12}$ from the definition of
   the alpha t-stat — and therefore why T=60 cannot distinguish IR 0.5
   from zero. (Sweep C §1 has the statement; derive it.)
3. Why the non-centered parameterization
   ($\alpha_i = \mu_s + \tau_s \tilde\alpha_i$,
   $\tilde\alpha_i \sim \mathcal{N}(0,1)$) removes the funnel: the
   posterior geometry of $(\tau, \alpha)$ when data are weak.
4. Empirical-Bayes moment estimator for $\tau^2$ (§3.6) and why it can hit
   zero (variance of estimates ≤ average estimation variance ⇒ no
   detectable dispersion).

**Canonical papers (read in this order):** Baks–Metrick–Wachter (2001, JF)
— priors over skill and why even skeptics allocate; Kosowski–Naik–Teo
(2007, JFE) — Bayesian alphas beat OLS alphas for hedge-fund prediction;
Harvey–Liu (2018, RFS) — the modern random-effects reference
implementation; Pástor–Stambaugh (2002, JFE) — why pinning betas sharpens
alpha (the tier-E mechanism); Gelman (2006) — prior choice for group-level
variance (why HalfNormal, not inverse-gamma).

**Defend unaided:** explain shrinkage to an investment committee in 60
seconds without the word "Bayesian"; justify the τ hyperprior scale from
the published panels; state why FDR-style luck control fails at n = tens
(Sweep C) and what this engine does instead; explain what the coverage test
in §4 proves that a backtest cannot.
