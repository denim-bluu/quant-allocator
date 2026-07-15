## The decision

Two managers can own the same names and still produce very different returns because
one sizes conviction well and the other does not. A third can pick well but hold names
after their edge has decayed. Monthly returns show the blended outcome; they do not
identify which lever produced it.

The sizing and alpha-decay lab uses dated positions and trades to separate three
questions: did larger positions earn more on the observed path, how quickly did
name-specific edge decay after entry, and which holding ages produced the book’s
alpha? Every estimate carries an interval, and every trade-level claim is power-gated.

In the paired synthetic exhibit, two managers hold identical picks. The disciplined
sizer posts +17.3% idiosyncratic alpha while the equal-weight manager posts +5.7%.
That 11.6-point realized-path difference motivates a sizing conversation. It does not
prove intent or a live premium. A concentrated 30-name book supplies only 174
independent trades over four years, so its sizing panel refuses to render. The
decision is therefore conditional: investigate sizing and holding where the data can
speak; preserve `insufficient N` where it cannot.

## Why the obvious answer fails

A headline Sharpe or alpha says whether the whole book made money. It cannot separate
selection, sizing, and holding discipline. A raw hit rate is not a fix. Position-months
share market and factor shocks, while repeated months of one name are the same economic
bet. Counting them as independent creates a narrow but false interval.

A pooled regression of position return on size makes the same mistake. Positions in
one month share shocks, so a textbook standard error overstates precision; the
supporting power work measured roughly 40% understatement for this estimator. A
positive t-statistic can therefore be a property of the dependence structure rather
than evidence that larger bets worked.

The deeper problem is that the three legs want different books. Fast turnover creates
many independent trades and powers a sizing test, but it truncates the decay curve
because few positions survive to older ages. Slow turnover reveals a long holding-age
path but starves the sizing test of new bets. The lab must let each leg speak or refuse
separately.

## The intuition

Start with three regroupings of the same position history.

First, line positions up by age rather than calendar date. Average the directional,
factor-adjusted return of all one-month-old positions, then all two-month-old
positions, and so on. The resulting curve shows how edge changes as a held idea ages.

Second, within each month, compare the active contribution of large positions with
small positions. If the manager consistently translates stronger insight into larger
weights, the size–outcome curve should slope upward. The equal-weight version of the
same names is the natural controlled comparison.

Third, add the alpha earned in age buckets. That turns an abstract half-life into a
portfolio statement: how much P&L came from fresh positions, and how much capital sat
in stale ones?

None of those regroupings creates independent evidence. The interval must respect
common months and repeated names, and the verdict must respect the number of genuinely
independent trades.

## A small numerical example

Take one month with three long positions. Their absolute weights are 2%, 4%, and 6%.
Their active returns are 0.0%, +2.5%, and +6.7%, producing active contributions of
0.0000, 0.0010, and 0.0040.

Center size at the monthly mean, $\overline{|w|}=0.04$. The monthly sizing slope is

$$
b_t=
\frac{\sum_i(|w_i|-\overline{|w|})c_i}
{\sum_i(|w_i|-\overline{|w|})^2}
=\frac{(-0.02)(0)+(0)(0.001)+(0.02)(0.004)}
{(0.02)^2+0+(0.02)^2}
=0.10.
$$

$|w_i|$ is position size and $c_i$ is its active contribution. The positive slope
says that, in this month, the largest position earned the most. It does not establish
a stable sizing skill: one cross-section supplies almost no evidence.

If all three names were held at 4%, every size deviation would be zero and the
denominator would collapse. The slope would be undefined, correctly recording that an
equal-weight month contains no within-book sizing information.

For holding decay, suppose fresh positions earn +2.0% idiosyncratically in month one
and the edge halves every six months. The expected return is then about +1.0% at age
six and +0.5% at age twelve. The live problem is not drawing that curve; it is
recovering its half-life with an interval from positions whose counts thin out with
age.

## The method

For name $i$ in month $t$, let $w_{i,t}$ be its signed portfolio weight,
$a_{i,t}$ its age in months, and $\tilde r_{i,t}$ its return after removing the
pre-registered factor model. Define active contribution as

$$
c_{i,t}=w_{i,t}\bigl(\tilde r_{i,t}-\bar{\tilde r}_t\bigr),
\qquad
\bar{\tilde r}_t=\frac{1}{N_t}\sum_j\tilde r_{j,t}.
$$

Subtracting the monthly equal-weight mean removes the mechanical net-long bias that
would otherwise make a zero-skill book look positive.

Sizing uses a Fama–MacBeth procedure: estimate a cross-sectional slope $b_t$ inside
each usable month, then average the monthly slopes,

$$
\hat b=\frac{1}{M}\sum_{t=1}^M b_t,
\qquad
\operatorname{se}(\hat b)=\frac{s_b}{\sqrt M}.
$$

$M$ is the number of usable months and $s_b$ is the sample standard deviation of the
monthly slopes. The month-to-month spread, rather than the count of position-months,
sets uncertainty. A slope can be distinguishable from zero only when its test
statistic clears the stated bar and the independent-trade count clears the applicable
power gate.

The decay curve is

$$
D(m)=\frac{1}{|\mathcal A_m|}
\sum_{(i,t)\in\mathcal A_m}
\operatorname{sign}(w_{i,t})\frac{\tilde r_{i,t}}{\sigma_{\tilde r}},
$$

where $\mathcal A_m$ contains every held position observed at age $m$ and
$\sigma_{\tilde r}$ standardizes idiosyncratic return. A log-linear fit from age one,
not the entry month, estimates the half-life. The entry month is excluded because it
contains an extra selection premium that would bias the estimated decay faster.

Finally, the holding decomposition reports the share of total idiosyncratic alpha
earned at ages 0–2, 3–5, 6–11, and 12+ months. Intervals use clustered inference so
common dates and repeated names are not mistaken for new evidence.

## What the evidence changes

The synthetic comparison separates two managers that returns alone make look like
different pickers. Meridian Arc Capital’s sizing slope is +0.0240 with a
month-clustered interval of [+0.0181, +0.0299]. Kelso Bay Partners, holding the same
names, has a slope of +0.0101 with interval [−0.0083, +0.0293]. The first controlled
association clears zero; the second remains unresolved.

The shared decay curve recovers a pooled half-life of 6.27 months against a dialed
truth of 6.0, while a single-manager interval spans roughly 3 to 11 months. Fitting
from entry month would produce 5.67 months, illustrating why the entry premium must
be excluded.

The holding decomposition says 57% of alpha arrives in months 0–2, 21% in months
3–5, 21% in months 6–11, and under 1% after a year. That supports a turnover
conversation. It does not by itself say what turnover is optimal after costs.

The negative evidence matters equally. At the atlas reference effect, the sizing
slope never reaches 80% power within 120 months, even at 1,985 independent trades.
The roughly 780-trade headline belongs to the 55%-versus-50% hit-rate gate, not a
universal sizing-slope threshold.

## What the allocator does next

1. Confirm that signed positions, entry and exit dates, and security identifiers are
   complete at the manager’s native cadence.
2. Residualize security returns with the stated factor model before attributing skill.
3. Inspect the sizing slope and its interval beside the equal-weight realized-path
   comparison; do not infer the manager’s intent from the association.
4. Check whether the book’s independent-trade count clears the metric-specific power
   gate. If not, preserve the refusal and show the arithmetic.
5. Compare the measured half-life with the holding-age P&L distribution, while
   recognizing that transaction costs and capacity are separate inputs.
6. Frame an inverted or unresolved sizing result as a shared process question, never
   as an automatic redemption trigger.

## Limits and go-live

- **Data ask.** The native tier requires dated signed position snapshots, trades with
  entry and exit dates, and factor returns for idiosyncratic adjustment.
- **Sample.** The hit-rate leg needs roughly **780 independent trades**; a 65-name,
  25%-turnover book reaches the neighborhood in about 3–4 years. A 30-name
  low-turnover book does not clear it in five years.
- **Metric-specific power.** A strong sizing effect reached measured power 0.77 at
  641 trades, 0.93 at 1,025, and 0.99 at 1,985. The reference effect remained below
  80% even at 1,985. The gate must match the effect and metric actually claimed.
- **Observable horizon.** A decay estimate refuses when positions disappear before
  the curve can reveal a half-life. Entry-month alpha may still be described.
- **Tier boundary.** Exposure summaries can support only a descriptive implied
  holding period. Monthly returns alone do not support this lab; that question is
  tested separately and returns a refusal for individual classification.
- **Validation prerequisite.** The synthetic decay leg needs an opt-in persistence
  mechanism whose zero setting leaves the original world unchanged. Without it, the
  honest decay curve is an entry spike followed by zero.
- **Inference.** The live interval must respect both date and name clustering and
  attain nominal coverage on known truth.
- **Decision ceiling.** The lab informs sizing and manager engagement. It does not
  rank managers across the roster or prescribe a mechanical redemption.

## Key takeaways

- Returns blend picking, sizing, and holding; dated positions let the allocator
  separate them.
- Estimate sizing month by month and let monthly variation set uncertainty.
- Fit holding decay from age one so the entry-selection premium does not distort the
  half-life.
- Slow turnover reveals longer decay but weakens sizing power; fast turnover does the
  reverse.
- Power gates are metric- and effect-specific. Below them, `insufficient N` is the
  correct result.
- A measured sizing gap is a controlled-path association and a conversation prompt,
  not a claim about intent.

## References

- Eugene Fama and James MacBeth, “Risk, Return, and Equilibrium: Empirical Tests,”
  *Journal of Political Economy*, 1973.
- Roger Clarke, Harindra de Silva, and Steven Thorley, “Portfolio Constraints and the
  Fundamental Law of Active Management,” *Financial Analysts Journal*, 2002.
- Richard Grinold and Ronald Kahn, *Active Portfolio Management*.
- Nicolae Gârleanu and Lasse Heje Pedersen, “Dynamic Trading with Predictable Returns
  and Transaction Costs,” *Journal of Finance*, 2013.
- A. Colin Cameron, Jonah Gelbach, and Douglas Miller, “Robust Inference with Multiway
  Clustering,” *Journal of Business & Economic Statistics*, 2011.
