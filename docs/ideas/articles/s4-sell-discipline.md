## The decision

A manager’s return blends the quality of buys, sizing, holding, and sells. When value
is lost, the tear sheet cannot show whether the leak occurred at the exit. The sell-
discipline diagnostic isolates that decision by comparing each sold name with the
names the manager could have sold instead.

The benchmark is a random-sell ghost operating on the same book at the same moment.
If sold names subsequently underperform the kept book, the manager culled well. If
they outperform, the exit gave away value that remained in the idea. The result is an
average counterfactual gap per exit with a block-bootstrap interval, not a bare point.

In the paired synthetic exhibit, disciplined exits produce a gap of **−372 basis
points per exit**, with a 90% interval from **−532 to −212**. Disposition-style exits
produce **+222 basis points**, with an interval from **+42 to +390**. The random ghost
reads **+28 basis points**, with an interval from **−149 to +201**. These loud,
teaching-scale effects show the mechanism. They support an engagement question, not a
mechanical redemption rule.

## Why the obvious answer fails

“Did the stock rise after it was sold?” is not a sell-quality test. In a rising market,
almost every sale looks regrettable. Comparing the sold name with an index is also
inadequate because the name and the index can carry different factors and come from
different opportunity sets.

The useful comparison freezes the manager’s own book at the sale. A random ghost then
sells from the same incumbent set. Market direction, calendar time, and much of the
universe effect are shared by both legs. Factor-adjusting the forward returns handles
the remaining exposure mismatch.

Uncertainty creates a second failure. Exits often arrive in monthly cohorts, and names
sold together share the same forward months and comparison pool. Treating every sale
as independent makes an interval too narrow. A quarterly trend is especially easy to
overread: around 18 exits per quarter in the synthetic book produce a standard error
of roughly 290 basis points in the underlying power analysis, while the displayed
worst-bucket standard error is about 820 basis points. The quarterly chart correctly
refuses.

## The intuition

Imagine a manager holding forty names and selling one. The question is not whether the
sale made money in isolation. It is whether the manager selected the right incumbent
to remove.

The random ghost provides a humble baseline. Rather than simulate lotteries, use the
average forward return of the eligible names the manager kept. That average is exactly
the expected outcome of choosing one of them uniformly at random, without adding
lottery noise.

The sign convention is the key:

- A positive gap means the sold name beat the kept book after the sale: value leaked.
- A negative gap means the sold name lagged the kept book: the manager culled well.
- An interval spanning zero means the evidence does not distinguish the sell rule from
  random selection.

The method can detect a leak only when forward residual returns carry some persistence.
If tomorrow’s name-specific return is unpredictable at the moment of sale, every sell
rule has an expected gap of zero. Exit behavior and forward-predictable alpha must both
be present.

## A small numerical example

At the end of June, a four-name equal-weight book sells D. Over the following two
months, factor-adjusted returns are +3.0% for D, while kept names A, B, and C return
+1.0%, 0.0%, and −1.0%.

The random-sell ghost’s expected result is the average of the kept names:

$$
\frac{1.0\%+0.0\%-1.0\%}{3}=0.0\%.
$$

The exit gap is therefore

$$
g_1=3.0\%-0.0\%=+3.0\text{ percentage points}.
$$

The positive sign says the killed name beat the survivors. This sale leaked.

Now suppose a second exit sells B. B returns −1.5% over the next two months, while the
kept names average +0.5%. Then

$$
g_2=-1.5\%-0.5\%=-2.0\text{ percentage points}.
$$

This was a good cull. Across the two exits, the average gap is

$$
\widehat{CG}=\frac{3.0-2.0}{2}=+0.5\text{ percentage points per exit}.
$$

The point is slightly positive, but two exits cannot support a verdict. The estimate
needs an interval and enough exits for the intended effect size.

## The method

Let exit $e$ occur for sold name $j_e$ in month $\tau_e$. Let $P_e$ contain the
incumbent names eligible to have been sold instead, excluding both the sold name and
fresh purchases made in the exit month. For a forward horizon of $H$ months,

$$
G_e=
\sum_{h=1}^{H}a_{j_e,\tau_e+h}
-\frac{1}{|P_e|}\sum_{k\in P_e}\sum_{h=1}^{H}a_{k,\tau_e+h},
\qquad
\widehat{CG}(H)=\frac{1}{n}\sum_{e=1}^{n}G_e.
$$

$a_{i,t}$ is name $i$’s factor-adjusted return in month $t$, $P_e$ is the
counterfactual pool, $H$ is the stated forward horizon, and $n$ is the number of exits
with a complete forward window. The default scalar uses four months, while the public
view exposes committed horizons from one through six so the verdict cannot hide at a
hand-picked horizon.

Fresh buys are excluded because they were selected on current signals and were not
part of the sell decision. Including them can inflate the comparison pool and
manufacture phantom sell skill.

Factor adjustment uses

$$
a_{i,t}=r_{i,t}-\hat\beta_i^\top f_t,
$$

where $r_{i,t}$ is total security return, $f_t$ is the factor-return vector, and
$\hat\beta_i$ is the security’s estimated loading vector. A live build uses a
defensible security-level risk model; the synthetic exhibit observes idiosyncratic
returns directly and therefore contains no factor-estimation error.

The forgone-alpha curve repeats $\widehat{CG}(h)$ at each forward month $h$. A rising
curve that plateaus after three months says the sold names continued to beat the kept
book for roughly three months, after which the forgone edge was spent.

Uncertainty comes from resampling whole exit-month cohorts. That preserves common
forward months and shared pool legs. The result is an estimate, a 90% interval, a
verdict conditional on the interval, or a refusal when the exit count is inadequate.

## What the evidence changes

Larkspur Ridge Partners and Redgate Harbor Capital have identical entry skill in the
synthetic world. Only their exit rules differ. Larkspur sells its lowest-conviction
incumbents and produces 546 exits; Redgate sells its largest trailing three-month
winners and produces 500.

Larkspur’s cumulative gap follows −187, −330, −387, and −372 basis points over months
one through four. Redgate’s follows +130, +231, +240, and +222. Redgate’s leak builds
for about three months and then plateaus. The ghost’s interval spans zero, showing that
the benchmark behaves as a benchmark should.

The difference between the two managers is roughly 590 basis points per exit in this
pinned world. It is deliberately loud: the persistence and signal settings are about
5–10 times the field magnitudes cited by the method review. The evidence teaches the
sign, comparison, and interval. It does not support extrapolating the synthetic gap to
a live manager.

The structural-null result is equally important. With no idiosyncratic persistence,
disciplined, random, and disposition-style rules all produce gaps near zero. An exit-
style dial alone cannot create a valid leak; the return process must carry predictable
residual alpha beyond the sale.

## What the allocator does next

1. Confirm the exit record, security identifiers, incumbent pool, and complete forward
   return windows before computing a gap.
2. Use residual rather than raw returns so factor mismatch does not masquerade as exit
   skill.
3. Inspect the random ghost first. If its interval does not behave as a zero control,
   stop and diagnose the construction.
4. Read the gap interval with the forgone-alpha curve and exit count. Do not promote a
   point whose interval spans zero.
5. Refuse quarterly trends below their bucket gate and fall back to yearly or pooled
   evidence.
6. Bring a material leak to the manager as an adjustable, shared question about the
   sale horizon and attention process. Keep any redemption implication human and
   downstream.

## Limits and go-live

- **Data ask.** The full diagnostic needs transaction history or monthly holdings with
  full exit dates and security identifiers, plus a credible factor or risk model.
  Exposure summaries provide hints only; monthly returns alone produce a refusal.
- **Sample.** The headline gap requires at least **150 exits**, enough only for an
  egregious leak of about **270 basis points per exit**. Resolving a field-sized
  75-basis-point effect requires about **1,900 exits**, generally two to four years
  for a high-turnover book.
- **Audience.** A 30-name, low-turnover book cannot reach the field-effect threshold
  on a practical horizon. The gate should say so rather than stretching the window.
- **Resolution.** Monthly holdings identify full exits only. Partial trims are outside
  the current method, and daily transactions improve exit dating and horizon detail.
- **Synthetic loudness.** The public example uses persistent residuals and large
  effects for teaching. Live bands inherit risk-model estimation error and will widen.
- **Coverage.** If the block-bootstrap interval fails nominal coverage across realistic
  clustering, the verdict is removed and the curve becomes descriptive only.
- **Horizon stability.** The sign must remain stable across horizons two through six;
  otherwise the control is a verdict-shopping device.
- **Decision ceiling.** Sell discipline is an engagement and monitoring input. It is
  never a manager ranking or automatic redemption trigger.

## Key takeaways

- Judge a sale against the names the manager could have sold, not against market
  direction.
- Positive gap means the sold names beat the kept book and value leaked; negative means
  disciplined culling.
- The counterfactual pool excludes fresh buys and uses factor-adjusted forward returns.
- Exit cohorts are dependent, so uncertainty must resample whole months.
- No forward predictability means no sell rule can have a nonzero expected gap.
- Low exit counts and short trend buckets require explicit refusal.

## References

- Lawrence Akepanidtaworn, Rick Di Mascio, Alex Imas, and Lawrence Schmidt, “Selling
  Fast and Buying Slow: Heuristics and Trading Performance of Institutional
  Investors,” *Journal of Finance*, 2023.
- Hersh Shefrin and Meir Statman, “The Disposition to Sell Winners Too Early and Ride
  Losers Too Long,” *Journal of Finance*, 1985.
- Terrance Odean, “Are Investors Reluctant to Realize Their Losses?” *Journal of
  Finance*, 1998.
- Andrea Frazzini, “The Disposition Effect and Underreaction to News,” *Journal of
  Finance*, 2006.
- Hans Künsch, “The Jackknife and the Bootstrap for General Stationary Observations,”
  *Annals of Statistics*, 1989.
