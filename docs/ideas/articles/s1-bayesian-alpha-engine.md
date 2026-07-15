## The decision

An allocator has twenty manager records and needs to decide which deserve further
underwriting and which can support more capital. Ranking the reported alphas is the
obvious move. It is also a ranking of skill mixed with sampling luck.

The hierarchical Bayesian alpha engine changes the question from “who has the highest
trailing alpha?” to “what range of alpha is plausible after the manager’s own evidence
is combined with what is known about comparable strategy peers?” Short, noisy records
are pulled more strongly toward their peer mean. Longer, cleaner records keep more of
their own estimate.

In the paired synthetic roster, shrinkage changes the rank of **7 of 20 managers**.
That reshuffle is descriptive, not proof that the new order is closer to true skill.
Against the simulator’s known truth, the posterior order in this one pinned roster is
slightly worse than the raw OLS order. The defensible decision is therefore to use the
posterior intervals and sensitivity results to guide underwriting conversations, while
refusing to let the ranking drive sizing until repeated-grid rank recovery and live
calibration pass.

## Why the obvious answer fails

At three to five years of monthly observations, manager alpha is hard to distinguish
from noise. A genuinely skilled manager with a true annualized information ratio of
0.5 has an expected t-statistic of only about
$0.5\sqrt{60/12}\approx1.1$ after 60 months. Power against a conventional two-sided
5% test is below 30%. In other words, such a manager fails to look statistically
significant more than two times in three.

Ranking the raw alpha estimates does not solve that problem. The most extreme estimate
is likely to combine genuine skill with an unusually favorable sample. A significance
filter is worse: it discards most genuinely skilled managers and selects the lucky few
whose noisy estimates happened to clear a high bar. False-discovery machinery is not a
substitute when the roster contains tens rather than thousands of managers.

The error is treating unequal evidence as equal. A 20% alpha estimate with a 10-point
standard error should not carry the same weight as a 20% estimate with a 5-point
standard error. The first is much less informative, even though both print the same
headline number.

## The intuition

Shrinkage is a disciplined compromise between a manager’s own estimate and the average
of genuinely comparable peers.

Imagine two managers in the same strategy, both reporting 6% annualized alpha. One has
60 months of returns and the other has 36. The longer record has earned more influence.
The model expresses that by giving each manager a weight based on the ratio of estimated
true skill dispersion to total dispersion, including estimation noise.

If managers in the peer group appear genuinely different and a particular record is
precise, the manager keeps most of its raw estimate. If the group looks homogeneous or
the record is noisy, the estimate moves toward the peer mean. If the observed spread of
manager alphas is no larger than the spread expected from estimation noise, the model
sets detectable skill dispersion to zero and shrinks everyone to the group mean. That
is a refusal to manufacture a ranking where the roster cannot support one.

## A small numerical example

Suppose a manager’s raw annualized alpha estimate is
$\hat\alpha^{\mathrm{OLS}}=0.20$, with standard error
$\mathrm{se}=0.10$. The relevant peer group has an estimated mean
$\hat\mu=0.08$ and an estimated true skill dispersion $\hat\tau=0.10$.

The shrinkage weight is

$$
w=\frac{\hat\tau^2}{\hat\tau^2+\mathrm{se}^2}
=\frac{0.01}{0.01+0.01}=0.5.
$$

Here $w$ is the fraction of the posterior estimate supplied by the manager’s own raw
alpha. Because true-skill variance and estimation variance are equal, the manager and
the peer mean receive equal weight:

$$
\hat\alpha^{\mathrm{post}}
=w\hat\alpha^{\mathrm{OLS}}+(1-w)\hat\mu
=0.5(0.20)+0.5(0.08)=0.14.
$$

The 20% raw estimate becomes a 14% posterior estimate. The six-point movement is not a
penalty. It is the consequence of admitting that the estimate is as noisy as genuine
skill is dispersed across peers.

Now keep the raw alpha and peer group unchanged but reduce the standard error to 0.05,
as a longer or cleaner record might. Then

$$
w=\frac{0.01}{0.01+0.0025}=0.8,
\qquad
\hat\alpha^{\mathrm{post}}=0.8(0.20)+0.2(0.08)=0.176.
$$

The more precise manager retains 17.6%. Same reported alpha, different defensible
belief: that is the whole mechanism.

## The method

For manager $i$ in strategy group $s(i)$ and month $t$, excess return is modeled as

$$
y_{i,t}=\alpha_i+\beta_i^\top f_t+\varepsilon_{i,t},
\qquad
\varepsilon_{i,t}\sim\mathcal N(0,\sigma_i^2).
$$

$y_{i,t}$ is the manager’s monthly return above the risk-free rate, $f_t$ is the
vector of strategy-appropriate factor returns, $\beta_i$ is the manager’s factor
exposure, $\alpha_i$ is the residual average return interpreted as skill under the
model, and $\sigma_i$ is idiosyncratic volatility.

The hierarchy enters through

$$
\alpha_i\sim\mathcal N(\mu_{s(i)},\tau_{s(i)}^2).
$$

$\mu_s$ is the average true alpha of strategy group $s$ and $\tau_s$ is the
within-strategy dispersion of true skill. The full model estimates alphas, factor
exposures, volatilities, peer means, and skill dispersion jointly. Its output for each
manager is a posterior mean, a 90% credible interval, $P(\alpha_i>0)$, and the amount
of shrinkage relative to OLS.

The public exhibit uses the closed-form normal–normal version so the correction is
visible. Its peer parameters are estimated by

$$
\hat\mu_s=\operatorname{mean}(\hat\alpha^{\mathrm{OLS}}_{i\in s}),
\qquad
\hat\tau^2=max\!\left(0,
\operatorname{var}(\hat\alpha^{\mathrm{OLS}}_{i\in s})
-\overline{\mathrm{se}^2}\right).
$$

The interesting step is the subtraction. The observed cross-sectional spread contains
both real skill dispersion and estimation noise. Subtracting average estimation
variance backs out the detectable real dispersion. The zero floor prevents a negative
variance and carries a substantive verdict: the roster shows no distinguishable skill
dispersion on this basis.

The full model also runs prior sensitivity. If changing the prior scale on $\tau$ by
one-half and two times flips top-quartile membership for more than **2 of 20
managers**, the verdict becomes `prior-dominated at this sample` and the ranking is
refused. Only interval reporting remains.

## What the evidence changes

The synthetic roster shows why the correction matters and why it is not self-
certifying.

Osprey Hollow Partners has raw alpha of +29.3% and posterior alpha of +25.4%; it stays
ranked first because its evidence earns a high weight. Cinderbank Capital starts at
+19.6%, ranked third, but its 36-month record earns a shrinkage weight of only 0.46;
the posterior falls to +13.2% and rank four. Alderbrook Partners moves from −7.4% to
−4.1%, while $P(\alpha>0)$ remains only 0.20.

These are estimates with intervals, not declarations of true skill. The ranking
changes because uncertainty differs across managers. The pinned truth comparison then
adds the crucial negative finding: shrinkage does not improve the true ordering in
this particular roster. That blocks the tempting conclusion that any reshuffle is an
upgrade.

## What the allocator does next

1. Define peer groups before looking at manager rankings; a convenient peer group is
   not necessarily a comparable one.
2. Confirm that returns are monthly, net, point-in-time, and aligned with the risk-free
   and factor series.
3. Inspect posterior intervals and $P(\alpha>0)$ before the posterior rank.
4. Run the half-scale and double-scale prior sensitivity fits and refuse the rank if
   top-quartile membership is unstable.
5. Use measured exposures, when available, to tighten the factor-loading prior rather
   than pretending beta uncertainty does not exist.
6. Treat the output as underwriting and engagement evidence. Capital optimization is a
   separate decision.

## Limits and go-live

- **Synthetic evidence.** The roster demonstrates shrinkage mechanics. Its pinned
  order is not evidence of better live manager selection.
- **Data ask.** Go-live needs comparable monthly net returns, a risk-free series,
  strategy labels, and appropriate factor sets. Full standing requires at least
  **36 months for at least 10 managers**; 24-month records may enter only with reduced
  standing.
- **Missing data.** More than two gaps in the evaluation window excludes and flags a
  manager. Missing months are never silently interpolated.
- **Peer dependence.** Results inherit the peer definition. Combining unlike
  strategies can create a persuasive but meaningless group mean.
- **Prior dependence.** Skill dispersion is weakly identified in small rosters. Prior
  sensitivity is therefore a headline output, not an appendix.
- **Validation gates.** Before ranking informs sizing, repeated synthetic cells must
  show 90% interval coverage within five percentage points of nominal, better true-rank
  recovery than OLS in at least 90% of replications, calibrated positive-skill
  probabilities, and adequate skill-dispersion recovery.
- **Computation refusal.** The full sampler reports nothing unless every parameter has
  $\hat R<1.01$, bulk effective sample size above 400, and zero divergences.
- **Decision ceiling.** A posterior alpha or advisory band does not authorize an
  automatic hire, add, or redemption.

## Key takeaways

- Raw alpha rankings confuse skill with unequal sampling noise.
- Shrinkage gives precise records more influence and pulls noisy records toward a
  comparable peer mean.
- If observed alpha dispersion is no greater than estimation noise, the honest result
  is no detectable ranking.
- Posterior estimates must be read with credible intervals and prior sensitivity.
- The synthetic reshuffle is instructive, but its known-truth ranking is slightly
  worse than OLS in this pinned roster.
- Use the engine to improve questions and calibrate conviction; refuse sizing use until
  the validation gates pass.

## References

- David Baks, Andrew Metrick, and Jessica Wachter, Bayesian manager selection,
  *Journal of Finance*, 2001.
- Robert Kosowski, Narayan Naik, and Melvyn Teo, Bayesian cross-sectional hedge-fund
  alpha analysis, *Journal of Financial Economics*, 2007.
- Campbell Harvey and Yan Liu, random-effects and multiple-testing analysis of fund
  alphas, *Review of Financial Studies*, 2018.
- Luboš Pástor and Robert Stambaugh, factor-exposure information in fund-alpha
  inference, *Journal of Financial Economics*, 2002.
- Andrew Gelman, “Prior Distributions for Variance Parameters in Hierarchical Models,”
  *Bayesian Analysis*, 2006.
