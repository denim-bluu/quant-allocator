## The decision

A smooth return history can describe either a genuinely steady strategy or a strategy
that collects small option premiums until a tail loss arrives. The allocator should not
treat those books as equivalent merely because their Sharpe ratios match.

The defensible response is a convexity screen that examines the **shape** of returns,
puts intervals around each diagnostic, and issues an investigation prompt only when a
calibrated set of diagnostics agrees. The result can change pricing, tail sizing, and
the next transparency request. It cannot prove that the manager is short volatility,
and it is never a mechanical redemption trigger.

## Why the obvious answer fails

A linear factor regression sees average sensitivity. Sold optionality lives in the
bend: calm-market premium income followed by disproportionate losses on large moves.
Realized volatility can also look benign until the tail arrives, so a standard tear
sheet is easiest to fool precisely when the risk matters most.

Splitting a 36–60 month track into up and down regimes does not fix the problem. It
halves an already short sample and tempts the reader to invent conditional-alpha claims.
At $T=48$, roughly 40% of observations may be down months, leaving only about 19 months
to identify downside participation.

Smoothing is another confound. An illiquid, honestly marked book can show positive
autocorrelation and low reported volatility without selling optionality. The screen
must first de-smooth the series and then ask about convexity; otherwise it can accuse an
illiquid book of a posture it does not have.

## The intuition

Plot one point for each month, with the market return horizontally and the manager
return vertically. A linear strategy produces a roughly straight cloud. A short-vol
strategy bends downward: it participates relatively well around ordinary moves, then
does worse at the extremes.

Four diagnostics inspect that same geometry from different angles:

1. fit the curvature directly with a squared-market term;
2. compare downside and upside participation;
3. ask whether the manager loses when the market's squared move is large;
4. compare drawdown depth with what the manager's own volatility would normally imply.

Because these diagnostics share the same underlying data and geometry, agreement is
**converging evidence**, not a joint p-value.

## A small numerical example

Take six symmetric market returns and two managers:

| Month | Market $f$ | Linear manager $0.5f$ | Concave manager $0.5f-3f^2+0.0189$ |
| --- | ---: | ---: | ---: |
| 1 | $+0.10$ | $+0.050$ | $+0.039$ |
| 2 | $-0.10$ | $-0.050$ | $-0.061$ |
| 3 | $+0.05$ | $+0.025$ | $+0.036$ |
| 4 | $-0.05$ | $-0.025$ | $-0.014$ |
| 5 | $+0.08$ | $+0.040$ | $+0.040$ |
| 6 | $-0.08$ | $-0.040$ | $-0.040$ |

Both managers average exactly zero. The mean of $f^2$ is 0.0063, so the concave
manager's constant premium, $0.0189=3\times0.0063$, exactly offsets its average
$-3f^2$ giveback.

The equality disappears when we inspect shape. The concave manager's worst month is
$-0.061$, versus $-0.050$ for the linear manager, and fitting a quadratic recovers a
curvature near $-3$. The premium preserved the average; it did not remove the tail.

## The method

The primary diagnostic is the Treynor–Mazuy quadratic regression on the de-smoothed
series:

$$
r_{i,t}=\alpha_i+\beta_i f_t+\gamma_i f_t^2+\varepsilon_{i,t}.
$$

$r_{i,t}$ is manager $i$'s excess return in month $t$, $f_t$ is the market-factor
return, $\alpha_i$ is the intercept, $\beta_i$ is linear beta, and $\gamma_i$ is
curvature. A negative $\gamma_i$ is short-convexity-consistent, but its interval—not
its sign alone—determines whether it contributes evidence.

The Henriksson–Merton companion is

$$
r_{i,t}=\alpha_i+\beta^-_i f_t+\gamma_i\max(f_t,0)+\varepsilon_{i,t},
$$

where $\beta^-_i$ is downside participation and
$\beta^+_i=\beta^-_i+\gamma_i$ is upside participation. A pattern with
$\beta^-_i>\beta^+_i$ is concave. This is a static payoff-shape descriptor, not a
table of alpha in different regimes.

Standardized coskewness asks whether returns are low when the market's squared move is
large:

$$
\widehat{\operatorname{coskew}}_i=
\frac{T^{-1}\sum_t(r_{i,t}-\bar r_i)(f_t-\bar f)^2}
{\widehat\sigma_{r_i}\widehat\sigma_f^2}.
$$

Third moments are fragile. Under normality, sample skewness has standard error roughly
$\sqrt{6/T}$, about 0.35 at $T=48$, so coskewness must clear a calibrated band before
it counts.

The drawdown-to-volatility statistic supplies corroboration. It compares realized
maximum drawdown per unit volatility with a simulated null at the same track length.
A manipulation-proof-performance gap and smoothing estimate can also be shown, but
neither is convexity-specific.

Each playable diagnostic returns an estimate, an interval, and one of
short-vol-consistent, inconclusive, or convex/benign. The provisional composite calls
for investigation when three diagnostics agree **and** the false-alarm gate is open.
It remains a tally, not a score.

## What the evidence changes

The screen can overturn the apparent equivalence created by a common Sharpe ratio. A
linear manager may remain unresolved or benign while a concave manager produces several
intervals that clear in the short-vol direction.

That evidence changes the underwriting question from “is the Sharpe attractive?” to
“what premium is being earned for which left-tail exposure, and is the mandate priced
and sized accordingly?” A short-vol posture can be legitimate. The evidence concerns
economics and transparency, not integrity.

If the intervals do not clear, the negative finding is preserved: individual estimates
remain visible, while the composite says **not resolvable at this track length**. The
screen does not turn weak diagnostics into a confident label.

## What the allocator does next

1. Confirm return dates, net-of-fee status, missing months, and the de-smoothing result.
2. Review the curvature, up/down participation, coskewness, and drawdown diagnostics
   together rather than ranking one coefficient.
3. Ask for reported gamma, vega, premium, or option-notional exposure summaries.
4. Use instrument-level holdings, where available, to confirm or contradict the
   returns-based inference.
5. Revisit tail sizing and fees only through the normal human review process.

## Limits and go-live

The public example is synthetic. The core live screen needs monthly net returns and a
market-factor series. The optional straddle rung additionally needs the public
Fung–Hsieh primitive trend-following-strategy factor series. Until that public series
is connected, the diagnostic must remain visibly not calculated rather than fabricated.

The standard data contract admits a manager at 24 months and gives full standing at 36,
but the **composite** has a stricter provisional minimum of $T=48$. It renders only where
the calibrated false-alarm rate, including honest-but-smooth managers, is at most 0.10.
Below that, the individual interval estimates remain and the composite refuses.

The kill line is a calibrated false-alarm rate above 0.20 at $T=48$: the screen must be
killed or its minimum window lengthened. Bootstrap interval coverage must also remain
within five percentage points of nominal; a diagnostic that fails is removed from the
tally. These thresholds remain provisional calibration inputs, not claims that every live strategy
family is already calibrated.

## Key takeaways

- A smooth Sharpe can be option premium rather than steady alpha.
- Shape diagnostics examine curvature that a linear regression discards.
- De-smoothing must precede convexity inference.
- The four diagnostics are correlated views of one geometry, not independent votes.
- Inconclusive intervals produce a refusal, while agreement produces an investigation
  prompt—not proof or an automatic redemption.

## References

- Vikas Agarwal and Narayan Naik, “Risks and Portfolio Decisions Involving Hedge
  Funds,” *Review of Financial Studies*, 2004.
- William Fung and David Hsieh, “The Risk in Hedge Fund Strategies: Theory and
  Evidence from Trend Followers,” *Review of Financial Studies*, 2001.
- Jack Treynor and Kay Mazuy, “Can Mutual Funds Outguess the Market?”, 1966.
- Roy Henriksson and Robert Merton, “On Market Timing and Investment Performance,”
  *Journal of Business*, 1981.
- Campbell Harvey and Akhtar Siddique, “Conditional Skewness in Asset Pricing Tests,”
  *Journal of Finance*, 2000.
