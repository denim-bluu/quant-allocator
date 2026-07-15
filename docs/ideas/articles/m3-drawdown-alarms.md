## The decision

A drawdown has no decision meaning until it is compared with the loss path that the
manager's own risk process could plausibly generate. The same 12% loss can be routine
for a high-volatility trend book and extreme for a smooth credit book.

This article is Foundation Step 3 because it corrects two traps at once. It replaces a
flat house threshold with a manager-specific simulated null, and it replaces a
pointwise chart breach with a **familywise-calibrated** path alarm. The resulting GREEN,
AMBER, or RED state is a review trigger. It is never automatic redemption and never
proof that alpha has died.

## Why the obvious answer fails

A rule such as “down 15%, place on review” ignores volatility, autocorrelation, track
length, and the skill hypothesis the allocator is paying for. It overreacts to naturally
volatile books and underreacts to smooth books whose losses are unusual at much smaller
depths.

A manager-specific pointwise band still fails if it is scanned through time. Suppose
each of ten independent monthly looks has a 1% false-breach probability. The chance of
at least one breach is

$$
1-0.99^{10}\approx9.6\%,
$$

not 1%. Across 48 independent looks it is about 38%. Drawdowns are dependent, so 38%
is not the live answer, but the mechanism remains: a 99th-percentile **per-month** band
does not create a 1%-false-alarm **whole-path** rule.

Finally, plugging a single Sharpe estimate into the null pretends manager skill is
known. A 36–60 month Sharpe is uncertain; ignoring that uncertainty narrows the null
and makes the alarm overconfident.

## The intuition

For each manager, simulate many complete return histories under a maintained
hypothesis: the skill level being underwritten, de-smoothed volatility, and a simple
one-lag dependence structure. Compute one number from each simulated path—the deepest
peak-to-trough loss. Those maximum drawdowns form the manager's null distribution.

The realized maximum drawdown is then placed on that distribution. An ordinary
percentile is GREEN. Crossing the null's 95th percentile is AMBER; crossing its 99th is
RED under the provisional alarm budgets.

Testing one maximum per path solves the scanning problem by construction. Every month
is already folded into the path maximum, so the threshold answers the familywise
question the monitor actually asks.

## A small numerical example

Consider two managers with the same realized 12% drawdown.

For a smooth book running at 6% annual volatility, suppose the simulated 95th- and
99th-percentile maximum-drawdown depths are 9% and 11%. A 12% realized depth is beyond
the 99th-percentile line, so the state is RED.

For a trend book running at 20% annual volatility, suppose the corresponding depths are
34% and 42%. The same 12% loss is well inside the 95th-percentile line, so the state is
GREEN.

The arithmetic did not redefine 12%. It changed the reference class. The low-volatility
book should almost never lose that much under its maintained process; the high-volatility
book does so routinely.

The RED state says “this path is extreme under the maintained hypothesis.” It does not
say why the loss occurred, that the model is correctly specified, or that redemption is
the right response.

## The method

For monthly net return $r_u$, cumulative wealth, current drawdown, and maximum drawdown
are

$$
W_t=\prod_{u\le t}(1+r_u),\qquad
D_t=1-\frac{W_t}{\max_{s\le t}W_s},\qquad
\operatorname{MDD}=\max_{t\le T}D_t.
$$

$W_t$ is wealth from a starting value of one; $D_t$ is the fraction below the running
peak; $T$ is the evaluated track length; and $\operatorname{MDD}$ is one scalar per
path.

Simulate $N$ null paths and calculate their MDD values. If $q_{0.95}$ and $q_{0.99}$
are the 95th and 99th percentiles of that distribution, the provisional rule is:

- GREEN when realized MDD is no deeper than $q_{0.95}$;
- AMBER when it exceeds $q_{0.95}$ but not $q_{0.99}$;
- RED when it exceeds $q_{0.99}$.

The chart can show the same test through running maximum drawdown
$M_t=\max_{s\le t}D_s$. Its simulated quantile band widens through time. At the current
window endpoint, a breach is the same event as the scalar MDD test, unlike a scanned
pointwise drawdown envelope.

The preferred null is posterior-predictive. For simulated path $j$, draw a Sharpe
$SR^{(j)}$ from the manager's skill posterior, then generate the return path. This
widens the null to carry uncertainty about skill. Without a posterior, show a Sharpe
fan across alternative maintained values rather than hiding reliance on one point.

Alarm state also needs hysteresis. RED arms beyond the 99th-percentile line and clears
only after the **current** drawdown recovers inside the 95th-percentile line for a
provisional two consecutive months. The current drawdown can recover; the historical
maximum cannot.

At roster level, multiplicity returns. With 40 healthy managers and a 1% RED rate per
manager, the expected false RED count is $40\times0.01=0.4$, and the probability of at
least one is

$$
1-0.99^{40}\approx0.33.
$$

The heat list therefore prints its expected false count. It does not silently apply a
power-destroying correction, and it does not pretend this is an alpha-discovery screen.

## What the evidence changes

The evidence turns drawdown depth into a calibrated statement about a specified null.
It permits the allocator to distinguish “ordinary for this manager” from “extreme even
given the uncertainty in our skill assumption.”

It also preserves three refusals. The alarm does not infer that alpha is dead, does not
resolve a misspecified valuation or liquidity process, and does not authorize a trade.
Slow alpha death remains low-power at $T\le60$ because one drawdown episode is effectively
close to one observation.

The provisional design targets 5% AMBER and 1% RED familywise budgets per review window.
Short-track validation measured roughly 2% for the intended 1% RED budget when null
parameters were estimated. That gap must remain visible: the design target is not the
same as achieved calibration.

## What the allocator does next

1. Verify monthly net returns, the risk-free series, de-smoothing, and the evaluated
   window.
2. Challenge the maintained Sharpe and inspect how the verdict moves across the fan.
3. Review exposure, leverage, liquidity, valuation, and manager explanation for an
   AMBER or RED path.
4. Read the roster's observed alarms beside the expected false count.
5. Route any capital decision through the normal human committee process.

## Limits and go-live

The public managers and paths are synthetic. Live use requires monthly net returns, a
maintained Sharpe distribution or clearly labelled point hypothesis, and a risk-free
series. Exposure-tier volatility targets and gross context may sharpen the null;
holdings do not.

The band can be computed at any $T$, but detection power improves slowly and remains low
at $T\le60$. The alarm budget is per explicit review window. Repeated reviews on a
growing track create another sequence of looks, so a per-window budget must not be
presented as a lifetime error rate.

Go-live requires familywise calibration across the maintained-hypothesis range,
posterior-predictive coverage checks, and a validated time-to-detection curve. If the
RED rate cannot be held within budget across that range, GREEN/AMBER/RED and the roster
heat list are removed. Only a descriptive percentile under the stated null remains.

The null must also resemble the manager's valuation and liquidity process. If it
cannot, the correct output is refusal. If a consumer connects the alarm to automatic
redemption, the method is withdrawn.

## Key takeaways

- Drawdown depth is interpretable only relative to a manager-specific null.
- A scanned pointwise band does not control whole-path false alarms.
- Testing maximum drawdown gives familywise control by construction.
- Skill uncertainty belongs inside the simulated null, not outside the chart.
- Roster alarms need an expected-false count.
- Foundation Step 3 ends in a review trigger, never automatic redemption.

## References

- Otto van Hemert, Suresh Ganesh, Janka Rohrbach, Matteo Roscioni et al., “Drawdowns,”
  *Journal of Portfolio Management*, 2020.
- Malik Magdon-Ismail and Amir Atiya, “Maximum Drawdown,” 2004.
- Peter Westfall and S. Stanley Young, *Resampling-Based Multiple Testing*, 1993.
- Andrew Gelman, John Carlin, Hal Stern, David Dunson, Aki Vehtari, and Donald Rubin,
  *Bayesian Data Analysis*, 3rd ed., chapter 6.
