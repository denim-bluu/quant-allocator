## The decision

Once the allocator has a posterior distribution for each manager's skill, the next
question is not “what is the optimal weight?” It is “what range of allocations can the
evidence defend?”

The method runs a simple constrained sizing rule across many plausible alpha draws and
reports each manager's 10th-to-90th percentile weight range. A tight skill posterior
produces a narrow allocation band. A short, noisy record produces a wide band or a floor
at zero. The width is not presentation uncertainty; it is the range of capital answers
implied by plausible skill worlds.

These bands are advisory. They support sizing and re-underwriting conversations, not an
auto-rebalancer or mechanical redemption.

## Why the obvious answer fails

A point mean-variance optimizer treats estimated alphas as known. Because it maximizes,
it loads most heavily on the largest estimates—and the largest estimates are
disproportionately those with the most favorable noise. Michaud called this
**estimation-error maximization**.

Constraints cap the visible damage but do not repair the mechanism. A long-only cap can
turn violent long/short weights into corner allocations, yet the ordering still comes
from noisy point estimates and the output still claims one precise weight.

Replacing raw alpha with a shrunk posterior mean helps, but it still discards posterior
width. Two managers with the same posterior mean and different uncertainty would receive
the same point weight. Equal weight avoids false precision and remains the benchmark,
but it discards useful skill evidence when the posterior genuinely separates managers.

## The intuition

A skill posterior describes many plausible worlds. In one draw, manager A has the
stronger alpha; in the next, manager B does. Instead of selecting one world and calling
its answer optimal, allocate in every world and retain the distribution of weights.

If the same manager receives roughly the same weight across draws, the evidence supports
a decisive capital range. If the weight moves from zero to the cap depending on the
draw, the evidence does not determine the allocation. A committee choice inside that
range is judgment, not missing mathematics.

Parameter uncertainty also behaves like additional risk. If expected alpha is uncertain,
the predictive return distribution is wider than the ordinary return distribution. A
defensible bet must shrink even before governance caps and liquidity constraints enter.

## A small numerical example

Take two managers with annual residual volatility of 10% and return correlation
$\rho=0.9$. Their point alpha estimates are 10% and 8%. The unconstrained mean-variance
tilt is proportional to

$$
(0.10-0.9\times0.08,\ 0.08-0.9\times0.10)=(0.028,-0.010).
$$

Normalizing the two entries to sum to one gives

$$
\left(\frac{0.028}{0.018},\frac{-0.010}{0.018}\right)
=(1.556,-0.556).
$$

The optimizer proposes +156% in manager 1 and -56% in manager 2 on a two-percentage-
point alpha spread.

Now give each alpha a posterior standard deviation of 6% and, for this small example,
treat them as independent. The spread's standard deviation is

$$
\sqrt{0.06^2+0.06^2}=0.0849.
$$

The probability that the true spread has the opposite sign is
$\Phi(-0.02/0.0849)\approx41\%$. The optimizer has expressed maximal conviction on a
ranking that is close to a coin flip.

The single-manager mechanism is equally stark. For posterior mean alpha $m=8\%$,
residual volatility $\sigma=10\%$, and posterior alpha uncertainty $s=6\%$, plug-in
Kelly size is $0.08/0.10^2=8.0$. Uncertainty-aware size is

$$
\frac{0.08}{0.10^2+0.06^2}=5.88,
$$

a 26% reduction before any fractional-Kelly haircut. Neither raw output is an
actionable fund weight; the calculation shows the direction of the correction.

## The method

Suppose the skill model supplies manager $i$ with posterior alpha

$$
\alpha_i\sim\mathcal N(m_i,s_i^2),
$$

where $m_i$ is posterior mean skill and $s_i$ is its standard deviation. If residual
return noise has variance $\sigma_i^2$, the predictive variance is
$\sigma_i^2+s_i^2$. The uncertainty-aware one-bet sizing direction is

$$
f_i=\frac{m_i}{\sigma_i^2+s_i^2},
$$

rather than $m_i/\sigma_i^2$. Uncertain alpha consumes capital like additional risk.

For the roster, draw an alpha vector $\alpha^{(d)}$ from the posterior. In each draw
$d$, apply the deliberately simple long-only rule

$$
w_i^{(d)}\propto
\frac{\max(0,\alpha_i^{(d)})}{\sigma_i^2},
\qquad \sum_iw_i^{(d)}=1,
\qquad w_i^{(d)}\le c.
$$

$w_i^{(d)}$ is manager $i$'s weight in draw $d$, and $c$ is a governance cap,
provisionally 20%. Negative drawn alpha receives zero because an allocator cannot short
a manager. The live rule uses de-smoothed manager-specific residual volatility; the
teaching exhibit holds volatility constant to isolate posterior uncertainty.

After many draws, report

$$
\operatorname{band}_i=
\left[Q_{10}(w_i^{(d)}),Q_{90}(w_i^{(d)})\right],
$$

$$
\operatorname{anchor}_i=\operatorname{median}(w_i^{(d)}),
\qquad
z_i=\Pr(w_i^{(d)}=0).
$$

The band is the advisory range; the median is an anchor displayed inside it, never as a
bare target; and $z_i$ is the fraction of plausible worlds in which the rule does not
fund the manager.

Action uses hysteresis. Exiting the 10–90 band triggers a review; the trigger clears
only after the current weight re-enters the inner 25–75 band. A zero floor with material
$z_i$ opens a fund-or-not conversation rather than firing a redemption.

## What the evidence changes

The band makes two forms of uncertainty visible. First, it shows when a point optimizer
has concentrated beyond the range supported by the posterior. Second, it distinguishes
managers with similar expected skill but different evidence quality: the less certain
manager receives a wider range and often a lower floor.

The method preserves a critical possible negative result. The posterior-band policy
must be tested against equal weight and point optimization on known-truth synthetic
worlds. If it cannot beat equal weight at realistic skill dispersion, the tilt is
killed. The publishable finding would be that the available records do not support
sizing on skill; the bands may remain as uncertainty communication around an equal-
weight anchor.

## What the allocator does next

1. Confirm that each skill posterior passed its upstream data and calibration gates.
2. Supply de-smoothed residual volatility and the roster's hard governance caps.
3. Compare current weights with the bands, treating band exits as review prompts.
4. Investigate zero-floor managers and the qualitative reasons to remain inside the
   range.
5. Use better exposure evidence to tighten posteriors before demanding more precision
   from the allocation layer.

## Limits and go-live

The public roster and allocation draws are synthetic. Live returns-only input requires at
least 36 monthly observations for at least 10 managers, strategy labels, aligned factor
sets, a risk-free series, and per-manager de-smoothed residual volatility. Managers
excluded by the skill model receive no band.

Bands can render at any admissible track length because width carries the uncertainty.
Decisive language—floors clear of zero and reliable improvement over point optimization—
is limited to validated cells, expected realistically around $T\ge48$ and true annual
skill dispersion of at least 2%. That boundary is a validation target, not a promise
that an observed live roster satisfies the unobservable dispersion condition.

The policy-regret study must compare posterior anchors, point optimization, and equal
weight under identical constraints. Band coverage must place the truth-optimized weight
inside the 10–90 band about 80% of the time, within five percentage points. The current
independent-manager posterior draws are provisional; group-level dependence is expected
to widen bands slightly. Fees, gates, notice periods, joint risk, and holdings crowding
remain separate inputs rather than hidden omissions.

## Key takeaways

- Point optimization amplifies noise in expected returns.
- Posterior variance should reduce size, not disappear after alpha estimation.
- Advisory bands are quantiles of weights across plausible skill worlds.
- A zero floor means funding is genuinely unresolved, not that redemption is automatic.
- Equal weight is the benchmark; failure to beat it kills the tilt and preserves the
  negative result.

## References

- Richard Michaud, “The Markowitz Optimization Enigma: Is ‘Optimized’ Optimal?”,
  *Financial Analysts Journal*, 1989.
- Vijay Chopra and William Ziemba, “The Effect of Errors in Means, Variances, and
  Covariances on Optimal Portfolio Choice,” 1993.
- Philippe Jorion, “Bayes–Stein Estimation for Portfolio Analysis,” *Journal of
  Financial and Quantitative Analysis*, 1986.
- Richard Michaud, *Efficient Asset Management*, 1998.
- Leonard MacLean, Edward Thorp, and William Ziemba, eds., *The Kelly Capital Growth
  Investment Criterion*, 2011.
