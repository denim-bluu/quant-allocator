## The decision

A short sleeve can make money for two very different reasons. It can offset the long
book’s factor exposure, or it can profit from name-specific insight. The first is a
real hedge that can often be replicated cheaply. The second is the skill for which a
long/short fee schedule is usually charged.

The short-book quality method decomposes sleeve P&L into those two components, then
asks whether residual short alpha survives uncertainty and borrow costs. The hedge
share is a descriptive measurement. Borrow-adjusted alpha is an estimate with an
interval. The hit rate is a separate trade-level statistic that refuses below its
power gate.

In the paired synthetic exhibit, two structurally identical books are both about 80%
hedge by variance. Saxbridge Capital nevertheless has borrow-adjusted short alpha of
+5.58% a year, with a 90% interval from +2.39% to +8.89%. Drybrook Capital has +0.66%,
with an interval from −2.27% to +3.62%. The decision is not “high hedge share is bad.”
It is to underwrite one mandate as two-sided alpha and the other as long alpha plus a
hedge whose fee-relevant residual remains unresolved.

## Why the obvious answer fails

The sign of short-sleeve P&L mostly reveals the market environment. A short basket
mechanically profits when markets fall and loses when they rise. An uninformed beta
hedge can look brilliant in a drawdown; a skilled short seller can lose money in a
rally while still adding name-specific value.

Looking only at the blended long/short return hides the opposite problem. A manager
whose shorts are pure factor offset may be delivering a useful risk service, but an
index overlay can replicate much of that service without stock-borrow costs. The
allocator cannot judge whether fees buy short-side skill until the factor payoff and
name-specific payoff are separated.

Borrow makes gross alpha incomplete. A sleeve earning 1.5% gross while paying 2% in
borrow does not deliver positive short alpha to the investor. Low breadth creates a
second limit: a 25-name sleeve with quarter-turnover can remain below a modest hit-rate
power threshold even after a decade.

## The intuition

Treat the short sleeve as a portfolio in its own right. Each shorted stock’s return has
a factor-explained part and an idiosyncratic part. Multiplying those parts by the
negative position weights splits the sleeve return exactly:

- The factor part is the hedge component: what these exposures earn from market,
  size, value, momentum, and other specified factors.
- The idiosyncratic part is the alpha component: the P&L that name-specific short
  selection can produce.

At the position tier this is accounting, not a regression. The weights and factor
loadings are observed. Uncertainty enters when the monthly alpha component is averaged
over a limited track record.

Hedge share and short alpha answer different questions. A sleeve can be 80% hedge by
variance and still contain meaningful residual alpha. Conversely, a low hedge share
does not prove skill. The fee question is answered by the borrow-adjusted alpha
interval, not the descriptive share alone.

## A small numerical example

Suppose the sleeve holds three shorts at −10% each, with market betas 1.0, 1.5, and
0.5. Its total market exposure is

$$
x=(-0.10)(1.0)+(-0.10)(1.5)+(-0.10)(0.5)=-0.30.
$$

In month one, the market falls 5%. The hedge component is

$$
(-0.30)(-5\%)=+1.5\%.
$$

If the three names’ idiosyncratic returns are −2%, −1%, and −3%, the alpha component
is

$$
(-0.10)(-0.02)+(-0.10)(-0.01)+(-0.10)(-0.03)=+0.6\%.
$$

The sleeve earns +2.1%, but 1.5 of those points came from factor offset. Calling all
2.1 points short alpha would be wrong.

In month two, the market rises 3%, so the hedge loses 0.9%. If idiosyncratic returns
are +2%, −4%, and −1%, the alpha component is +0.3%. The sleeve loses 0.6% overall
even though the short picks add value. Skill and headline P&L have opposite signs.

Finally, 30% short gross at a flat 2% annual borrow fee costs
$0.30\times2\%=0.6\%$ of NAV per year, or five basis points per month. That cost is
subtracted from the residual alpha because it is a fee bill, not a risk factor.

## The method

Let $w_{i,t}$ be name $i$’s weight in month $t$, with negative values for shorts, and
define $w^-_{i,t}=\min(w_{i,t},0)$. The sleeve return is

$$
r^S_t=
\underbrace{x_t^\top f_t}_{\text{hedge}}
+\underbrace{\sum_i w^-_{i,t}\varepsilon_{i,t}}_{\text{alpha}},
\qquad
x_t=B^\top w^-_t.
$$

$B$ is the matrix of security factor loadings, $x_t$ is the measured short-sleeve
exposure vector, $f_t$ is the factor-return vector, and $\varepsilon_{i,t}$ is the
security’s idiosyncratic return. With positions and a risk model, the two components
add back to the sleeve return exactly.

Let $a_t=\sum_iw^-_{i,t}\varepsilon_{i,t}$ be the monthly alpha component. Hedge
share is

$$
\mathrm{HS}=1-\frac{\operatorname{Var}(a_t)}
{\operatorname{Var}(r^S_t)}.
$$

HS near one means most of the sleeve’s monthly variation is factor offset. It is a
description, not a significance claim.

Gross and net annualized short alpha are

$$
\alpha^S=12\operatorname{mean}(a_t),
\qquad
\alpha^S_{\mathrm{net}}=\alpha^S-c,
$$

where $c$ is the annualized borrow bill, calculated from per-name fees and absolute
short weights. The monthly alpha series receives a heteroskedasticity- and
autocorrelation-consistent interval cross-checked against a block bootstrap, with the
looser result governing the display.

The short-side hit rate uses active, not raw, returns:

$$
g_{i,t}=w^-_{i,t}(r_{i,t}-\bar r_t).
$$

$\bar r_t$ is the equal-weight cross-sectional return that month. A successful short
has $g_{i,t}>0$, meaning the shorted name underperformed the month’s universe. Monthly
hit fractions are analyzed as clusters; individual position-months are not treated as
independent trades.

## What the evidence changes

Saxbridge and Drybrook both run 160 gross, 20 net books with 40 longs, 25 shorts, and
the same long-side skill. Their pinned hedge shares are 83.5% and 84.3%. That near-
equality is the first lesson: hedge share alone does not identify short skill.

Saxbridge’s gross short alpha is +6.98% a year, with a 90% interval from +3.79% to
+10.29%. A 1.40% annual borrow drag reduces it to +5.58%, and the net interval remains
above zero. Drybrook’s gross estimate is +2.06%, with an interval from −0.87% to
+5.02%. After the same drag, +0.66% remains, but the interval from −2.27% to +3.62%
refuses a positive-alpha verdict.

Both books also demonstrate why a separate hit-rate gate matters. After ten years,
each supplies 745 independent trades—35 short of the interim 780-trade line. The hit-
rate points and clustered t-statistics do not render. At five years the count is only
385. A noisy point can look persuasive at exactly the samples where the operating
characteristic says not to trust it.

## What the allocator does next

1. Confirm signed month-end positions, factor loadings, factor returns, and the
   evaluated sleeve’s return basis.
2. Reconcile hedge plus alpha back to the observed sleeve P&L before interpreting any
   summary.
3. Read hedge share as a product description, then read the borrow-adjusted alpha
   interval as the fee-relevant skill evidence.
4. Stress the borrow assumption across the disclosed range; use actual per-name fees
   where available.
5. Preserve the hit-rate refusal until the independent-trade gate opens.
6. If the residual remains unresolved while hedge share is high, discuss whether the
   mandate should be priced or structured as long alpha plus an overlay. Do not convert
   that conversation into an automatic redemption.

## Limits and go-live

- **Data ask.** The full score needs signed month-end positions, a bought risk-model
  loadings feed, factor returns, a risk-free series, and per-name borrow fees where
  disclosed.
- **Tier boundary.** Exposure summaries support the factor split only. Blended returns
  cannot identify the sleeves and produce a refusal unless the manager separately
  discloses short-sleeve returns; that fallback carries a constant-beta timing caveat.
- **Sample.** The decomposition and hedge share are valid measurements at any track
  length. The alpha interval needs at least **36 months** to render and remains wide
  until roughly 60 or more.
- **Hit-rate gate.** Detecting 55% versus 50% at 80% power needs about **780
  independent trades**. A 25-name, quarter-turnover sleeve reaches 745 in ten years;
  high-turnover books may certify in one to two years.
- **Borrow realism.** The synthetic exhibit uses a flat 2% annual fee and exposes a
  0–5% sensitivity range. Real specials have a much more uneven fee and recall
  distribution, so live use prefers per-name evidence.
- **Crowding boundary.** The method does not predict squeezes. Short interest and
  days-to-cover are deferred context, not simulated proof.
- **Validation.** If noise-picked sleeves receive positive-alpha verdicts above the
  nominal rate, the verdict is removed and the method becomes classification-only.
- **Decision ceiling.** The output supports underwriting, sizing, repricing, and
  engagement. It is not a cross-manager ranking or mechanical redeem rule.

## Key takeaways

- Short-sleeve P&L combines factor hedging and name-specific alpha.
- A profitable short book in a falling market can contain no short alpha; a losing
  sleeve in a rally can still add residual value.
- Hedge share is descriptive and can be high alongside genuine alpha.
- Borrow-adjusted alpha, with an interval, is the fee-relevant estimate.
- Returns alone do not identify the sleeves, and low trade counts require a hit-rate
  refusal.
- Underwrite hedge-only and two-sided-alpha mandates as different products.

## References

- Ekkehart Boehmer, Charles Jones, and Xiaoyan Zhang, “Which Shorts Are Informed?”
  *Journal of Finance*, 2008.
- Gene D’Avolio, “The Market for Borrowing Stock,” *Journal of Financial Economics*,
  2002.
- Itamar Drechsler and Qingyi Drechsler, “The Shorting Premium.”
- Joseph Engelberg, Adam Reed, and Matthew Ringgenberg, “Short-Selling Risk,”
  *Journal of Finance*, 2018.
- Richard Grinold and Ronald Kahn, *Active Portfolio Management*.
