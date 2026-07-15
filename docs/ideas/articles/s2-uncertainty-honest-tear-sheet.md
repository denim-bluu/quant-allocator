## The decision

A tear sheet is supposed to compress a manager's track record into something an
allocator can act on. The usual version compresses too aggressively. It prints a
Sharpe ratio, alpha, and maximum drawdown as if each were a known property of the
manager rather than an estimate from a short and imperfect sample.

The synthetic example in the paired exhibit has 48 monthly observations. Its reported
Sharpe is **0.71**, but the 95% interval runs from **−0.26 to 1.67**. After undoing the
return smoothing, the Sharpe falls to **0.60**, with a 95% interval from **−0.29 to
1.46**. Annualized alpha is **+3.2%**, while its 90% interval spans **−4.4% to +10.8%**.

Those are not three weak results. They are three unresolved results. The record remains
consistent with useful skill, but it does not yet separate that skill from noise and
factor exposure. The defensible decision is therefore to **keep monitoring, avoid a
conviction add based on the point estimates, and open a fees-for-beta conversation**.

That is the purpose of an uncertainty-honest tear sheet: every estimate carries the
range the observed track can support, and every verdict says what that range permits or
refuses.

## Why the obvious answer fails

Two problems make manager tear sheets unusually easy to overread.

First, the samples are short. A manager arriving at an underwriting table often has
only 36–60 monthly observations. With four years of returns, the sampling uncertainty
around a Sharpe ratio is large enough that an apparently attractive point can remain
consistent with both no skill and exceptional skill. Ranking managers by those points
mostly ranks who received the most favorable noise.

Second, the observations can be dirty. Illiquid or model-marked books often report
smoothed returns: part of an economic move appears this month and the rest bleeds into
later months. Smoothing preserves the long-run mean but suppresses reported volatility.
Because volatility is the denominator of the Sharpe ratio, the headline Sharpe rises
without any improvement in the underlying economics.

The standard shortcuts make this worse:

- Annualizing a monthly Sharpe by multiplying by $\sqrt{12}$ assumes serial
  independence, precisely what smoothed marks violate.
- A significance star turns a wide range of plausible values into a binary decoration.
- Comparing raw Sharpes treats differently smoothed and differently aged records as
  though they were measured on the same basis.
- A factor alpha without an interval invites the reader to treat a noisy residual as
  independently demonstrated skill.

The mistake is not using Sharpe or alpha. The mistake is asking their point estimates
to carry more certainty than the track record contains.

## The intuition

Think of the tear sheet as a sequence of questions rather than a list of metrics.

1. **What volatility did the portfolio economically experience?** Undo material
   smoothing before computing risk-adjusted performance.
2. **What part of the return is explained by familiar factors?** Estimate alpha and
   beta on the economic series.
3. **How wide is the uncertainty?** Put intervals around Sharpe and alpha instead of
   printing bare points.
4. **Does another performance lens tell the same story?** Compare Sharpe with a
   manipulation-proof performance measure.
5. **Is the drawdown unusual under the maintained skill hypothesis?** Compare the
   realized path with a simulated reference envelope, while being explicit about what
   that envelope can and cannot prove.

Order matters. If factor regression, intervals, and drawdown simulation use the
smoothed series, every downstream conclusion inherits a volatility estimate known to be
too low.

## A small numerical example

Suppose an illiquid book's true monthly returns have a mean of 1% and a standard
deviation of $\sigma_r=1.00\%$. The manager reports each month as 70% of the current
economic return and 30% of the previous one:

$$
r^{\mathrm{obs}}_t = 0.7r_t + 0.3r_{t-1}.
$$

Assume the true monthly returns are serially uncorrelated. The average return is still
1%, because the weights sum to one. The variances of the two independent pieces add:

$$
\sigma^2_{\mathrm{obs}}
= (0.7^2+0.3^2)\sigma_r^2
=0.58\sigma_r^2.
$$

Therefore:

$$
\sigma_{\mathrm{obs}}=\sqrt{0.58}\times1.00\%\approx0.76\%.
$$

Nothing about the book became safer. Reporting simply spread each economic move across
two months. Yet a naive tear sheet divides the same mean by 0.76% rather than 1.00%,
inflating the Sharpe by approximately
$1/\sqrt{0.58}\approx1.31$, or **31%**.

Unsmoothing reverses that distortion:

$$
\sigma_r=\frac{0.76\%}{\sqrt{0.58}}\approx1.00\%.
$$

This example is deliberately small. In a real sample, the smoothing weights must be
estimated and true returns will contain accidental serial correlation. The recovery is
therefore uncertain rather than exact. But the mechanism is the same: restore the
economic denominator before interpreting the ratio.

## The method

### Restore economic returns

Model the reported return as a moving average of the current and two previous economic
returns:

$$
r^{\mathrm{obs}}_t
=\theta_0r_t+\theta_1r_{t-1}+\theta_2r_{t-2},
\qquad
\sum_{k=0}^{2}\theta_k=1,
\quad \theta_k\ge0.
$$

Here $r^{\mathrm{obs}}_t$ is the reported return, $r_t$ is the unobserved economic
return, and the $\theta_k$ values describe how a move is spread across reporting
months. Larger lag weights indicate more stale-mark behavior. The paired synthetic
example estimates $(\theta_0,\theta_1,\theta_2)=(0.82,0.18,0.00)$ and an economic-to-
reported volatility ratio that lowers the Sharpe from 0.71 to 0.60.

The model assumes the serial dependence being removed is reporting-induced smoothing.
If the return process has genuine economic autocorrelation, aggressive unsmoothing can
misattribute it. The weights are therefore printed as diagnostics rather than hidden as
implementation detail.

### Separate alpha from factor exposure

Regress the de-smoothed excess return on a strategy-appropriate factor set:

$$
r_t-r_{f,t}=\alpha+\sum_j\beta_jf_{j,t}+\varepsilon_t.
$$

$r_{f,t}$ is the monthly risk-free return, $f_{j,t}$ is factor $j$, $\beta_j$ is the
manager's exposure to that factor, and $\alpha$ is the remaining average monthly return.
The exhibit annualizes alpha by multiplying by 12 and uses a heteroskedasticity- and
autocorrelation-consistent uncertainty estimate.

The synthetic record produces market, size, value, and momentum betas of approximately
0.23, 0.07, −0.09, and 0.24. Its annualized alpha point is +3.2%, but the 90% interval
includes zero. That interval—not the positive point—is why the verdict remains
`provisionally alternative beta`.

### Attach intervals to the headline statistics

For a monthly Sharpe estimate $\widehat{SR}$ from $T$ observations, a useful
closed-form approximation is:

$$
SE(\widehat{SR})\approx
\sqrt{\frac{1+\tfrac12\widehat{SR}^{\,2}}{T}}.
$$

The $1/T$ term is the short-sample penalty. The
$\tfrac12\widehat{SR}^{\,2}$ term reflects the extra uncertainty from estimating
volatility rather than knowing it. The published exhibit uses a studentized circular
block bootstrap for the displayed Sharpe interval so that serial dependence and fat
tails are not discarded; the closed-form result remains a transparent diagnostic.

Alpha uses a Newey–West standard error, with a block-bootstrap cross-check. If the two
methods materially disagree, the honest response is to widen the interval or refuse a
strong claim—not to select the narrower result.

### Add a manipulation-resistant cross-check

The manipulation-proof performance measure asks what constant excess return would give
a risk-averse investor the same realized utility as the manager's return distribution.
It is shown beside the Sharpe because tail selling, smoothing, and payoff reshaping can
flatter a mean-volatility ratio. The synthetic example's MPPM is about +3.1% per year.
The useful object is the gap between the two performance stories, not a new league table
based on MPPM alone.

### Put drawdown in a reference distribution

The exhibit simulates drawdown paths under a maintained hypothesis using the estimated
volatility, skill assumption, and fitted one-lag dependence. It plots pointwise 50th,
95th, and 99th-percentile envelopes against the realized path.

The synthetic manager's worst drawdown is about −10.5% and remains inside the displayed
99th-percentile envelope. This supports the limited statement that the loss is not
visually extreme under that reference construction. It does **not** create a calibrated
scanning alarm: repeatedly checking a pointwise band over many months raises the chance
of at least one false breach. M3 supplies the familywise alarm logic later in the Start
Here path.

## What the evidence changes

The corrected sheet changes the decision in three ways.

First, the reported Sharpe no longer receives automatic priority. De-smoothing reduces
the point estimate, and both intervals remain wide enough that a strong skill claim is
premature.

Second, positive alpha no longer means demonstrated alpha. The +3.2% point sits inside a
range from −4.4% to +10.8%. The range permits real skill but also permits no alpha after
factor exposure. The appropriate chip is therefore a calibration statement about the
track length, not an accusation about the manager.

Third, the drawdown becomes context rather than a trigger. The realized path looks
ordinary under the illustrative null, so the exhibit supplies no evidence for an alarm.
It also refuses to turn a pointwise envelope into an automatic redeem signal.

Taken together, the evidence supports **continued monitoring and a targeted fee/exposure
conversation**. It does not support a conviction add, a point ranking, or an automatic
redemption.

## What the allocator does next

1. Confirm that the 48 monthly returns are net, contemporaneous, and free of silent
   backfills or missing-month interpolation.
2. Replace the synthetic factor series with the strategy-appropriate public or licensed
   factors used in the real underwriting process.
3. Ask the manager whether the estimated smoothing weights are consistent with the
   portfolio's marking and liquidity process.
4. Compare inferred factor exposures with manager-reported exposures when tier-E data
   is available.
5. Continue collecting observations rather than treating a wider interval as a defect
   to be hidden.
6. If drawdown monitoring is decision-relevant, move to M3's familywise-calibrated alarm
   rather than scanning this pointwise band.

## Limits and go-live

This page is an instructional construction, not external calibration evidence.

- **Synthetic inputs.** The manager and factors in the exhibit are synthetic. The
  example proves the rendering and known-truth mechanics, not live predictive accuracy.
- **Unsmoothing assumption.** The moving-average inversion treats observed serial
  dependence as mark smoothing. Genuine economic autocorrelation can make that
  interpretation too strong.
- **Short-track uncertainty.** The sheet can render from 24 months with a short-track
  warning, but full standing requires at least 36 months. More observations tighten
  intervals; they do not guarantee a favorable verdict.
- **Interval calibration.** Production use requires empirical coverage checks across
  track length, strategy family, smoothing level, and true skill. A displayed interval
  that misses its nominal coverage by more than five percentage points must be relabelled
  approximate or replaced with the more conservative validated alternative.
- **Pointwise drawdown envelope.** The chart describes each month in isolation. It is not
  a familywise alarm and must not be used as one.
- **Data ask.** Tier R requires monthly net returns, risk-free returns, a strategy label,
  and aligned strategy factors. Tier E adds reported exposures for measured-versus-
  inferred comparison. Tier P adds holdings descriptors, not new skill estimation in
  this article.
- **Decision ceiling.** No output on this page authorizes an automatic hire, add, or
  redeem decision.

## Key takeaways

- A performance point estimate is incomplete without the uncertainty created by its
  track length.
- Smoothed marks reduce reported volatility and can mechanically flatter Sharpe and
  factor neutrality.
- Unsmoothing must precede Sharpe, alpha, and drawdown interpretation.
- An alpha interval containing zero means the record cannot yet separate skill from
  factor exposure; it does not prove the absence of skill.
- A pointwise drawdown band is descriptive. A monitoring alarm needs a familywise error
  budget.
- The honest action for this synthetic record is monitor and engage, not add or redeem.

## References

- Andrew W. Lo, “The Statistics of Sharpe Ratios,” *Financial Analysts Journal*, 2002.
- Mila Getmansky, Andrew W. Lo, and Igor Makarov, “An Econometric Model of Serial
  Correlation and Illiquidity in Hedge Fund Returns,” *Journal of Financial Economics*,
  2004.
- Olivier Ledoit and Michael Wolf, “Robust Performance Hypothesis Testing with the
  Sharpe Ratio,” *Journal of Empirical Finance*, 2008.
- William Goetzmann, Jonathan Ingersoll, Matthew Spiegel, and Ivo Welch, “Sharpening
  Sharpe Ratios,” *Review of Financial Studies*, 2007.
- Whitney Newey and Kenneth West, “A Simple, Positive Semi-definite,
  Heteroskedasticity and Autocorrelation Consistent Covariance Matrix,” *Econometrica*,
  1987.
