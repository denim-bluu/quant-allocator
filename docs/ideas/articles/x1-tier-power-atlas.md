## The decision

Before a manager metric is allowed to speak, require a pre-registered effect, a calibrated false-alarm rate, and a measured sample threshold at the relevant transparency tier. If the simulated study does not clear those conditions, the metric’s registry entry remains closed or explicitly has no threshold.

The Tier & Power Atlas is an advanced reference and governance tool. It does not decide whether a manager is good. It decides whether a proposed estimate, interval, or verdict has enough evidence to be shown at all.

Its durable output is a machine-readable PowerGate registry. Downstream articles and exhibits consume that registry rather than hand-copying attractive thresholds.

## Why the obvious answer fails

Rules such as “three years is enough” ignore the effect being detected, the metric’s false-alarm rate, and the data tier. The same tenure may be useful for a strong signal with measured exposures and nearly powerless for a weak returns-only signal.

A threshold without an effect size is also meaningless. “About 780 trades” answers a specific question: how many independent trades are needed to distinguish a $55\%$ hit rate from $50\%$ at specified error rates. It is not a universal position-data minimum.

Power alone can mislead. A test can appear powerful by firing too often when no effect exists. The false-alarm rate—test size—must be checked before any detection rate is interpreted.

Finally, power measured by simulation is itself an estimate. Printing $0.80$ without its Monte Carlo interval replaces one kind of false precision with another.

## The intuition

For one atlas cell, fix the true effect, transparency tier, sample length, and all simulator conditions. Generate many independent synthetic records. Run the pre-registered metric on each record and record whether it fires.

When the effect is present, the fraction of detections estimates **power**. When the effect is zero, the same fraction estimates **size**, the false-alarm rate. Sweep the relevant sample quantity from small to large. The first quantity whose measured power reaches $0.80$, while size remains controlled, is the candidate threshold.

Repeat at returns $R$, exposure $E$, and position $P$ tiers. Differences in thresholds show what transparency buys in measured reliability rather than adjectives.

## A small numerical example

Consider an alpha $t$-test at returns-only transparency. The synthetic manager’s true annual information ratio is $0.5$, and the track length is $T=48$ months. The rule declares detection when the absolute $t$-statistic exceeds $1.96$.

Across $1{,}000$ independent paths, suppose $252$ cross the threshold. The power estimate is

$$
\widehat{\pi}=\frac{252}{1{,}000}=0.252.
$$

$\widehat{\pi}$ is an estimate of the probability that this test detects a true $IR=0.5$ manager after four years. It says detection occurs only about one quarter of the time.

Now set true skill to zero. If $51$ of $1{,}000$ paths still cross $1.96$, estimated size is

$$
\widehat{\alpha}=\frac{51}{1{,}000}=0.051.
$$

That is close to the intended $5\%$ false-alarm rate, so the low power is meaningful rather than the result of an obviously distorted test.

The estimate still needs an interval. Near a proportion of $0.5$, $1{,}000$ replications imply a Monte Carlo standard error of approximately

$$
\sqrt{\frac{0.25}{1{,}000}}\approx1.6\%.
$$

That reporting floor is why the atlas shows Wilson $95\%$ intervals around power rather than treating one simulated fraction as exact.

## The method

### Link per-bet skill to portfolio detectability

The simulator uses information coefficient $IC$, while allocators often interpret information ratio $IR$. The fundamental law gives

$$
IR\approx IC\sqrt{BR},
$$

where $BR$ is the number of independent bets per year. A modest forecasting edge becomes easier to detect when it is repeated across greater independent breadth.

For an annual information ratio $IR_{\mathrm{ann}}$ and $T$ monthly observations, the alpha test’s noncentrality is

$$
\lambda=IR_{\mathrm{ann}}\sqrt{\frac{T}{12}}.
$$

$\lambda$ measures how far the alternative distribution moves away from the no-skill null. The noncentral-$t$ power is an analytic cross-check on the simulation, not a replacement for it.

### Derive the trade-count reference

For a one-sample hit-rate test, the normal approximation is

$$
n=
\frac{\left[z_{\alpha/2}\sqrt{p_0(1-p_0)}+
z_{\beta}\sqrt{p_1(1-p_1)}\right]^2}
{(p_1-p_0)^2}.
$$

$p_0=0.50$ is the null hit rate, $p_1=0.55$ the alternative, $z_{\alpha/2}=1.96$ the two-sided $5\%$ critical value, and $z_{\beta}=0.842$ the value for $80\%$ power. Substitution gives $n\approx782$, commonly summarized as roughly $780$ independent trades.

### Put an interval around every simulated rate

For $k$ detections in $n$ replications, let $\widehat p=k/n$. The Wilson center and half-width are

$$
\text{center}=
\frac{\widehat p+z^2/(2n)}{1+z^2/n},
$$

$$
\text{half}=
\frac{z}{1+z^2/n}
\sqrt{\frac{\widehat p(1-\widehat p)}{n}+\frac{z^2}{4n^2}}.
$$

With $z=1.96$, the interval is the center plus or minus the half-width. It stays inside $[0,1]$ and behaves better than a naive normal interval near the boundaries.

### Build the registry only after validation

Volume 1 pre-registers metric rules across a $75$-cell primary grid: $5$ information-coefficient settings, $3$ alpha half-lives, and $5$ track lengths. Position-level subsets also vary breadth and sizing discipline. Each cell requires at least $1{,}000$ seeded paths.

For each metric-tier pair, the registry records the gate quantity, pinned effect, smallest quantity reaching power $0.80$, measured size $0.05$, and verdict. A null threshold means no quantity in the measured range suffices.

Validation checks analytic cross-checks, size within $5\%\pm1.5$ percentage points, monotonicity up to Monte Carlo noise, byte-identical reproducibility from the same seed, and nuisance stresses. A test with distorted size gets a corrected critical value or a “size-distorted—no gate” refusal.

## What the evidence changes

The current sampler shows the practical direction without certifying the final registry. At $T=48$ and $IC=0.04$, alpha-estimation power is $25.2\%$ at tier $R$ and $31.8\%$ at tier $E$. Hit-rate power is $13.2\%$ and sizing-skill power $23.4\%$ at tier $P$; drift detection is deferred.

At the middle effect and $T=120$, the returns-tier shrinkage-posterior point is $0.788$, with Wilson interval $[0.750047,0.821561]$, which spans the $0.80$ bar. Pinning betas at tier $E$ raises the point to $0.820$. These are estimates and intervals, not proof that one tier is precisely below and the other precisely above $0.80$.

Both sampler registry rows remain null: no tenure in the measured sampler range clears the required bar. That refusal is part of the result. The sampler uses $500$ managers per cell and remains provisional until the at-least-$1{,}000$-replication volume-1 study passes its gates.

## What the allocator does next

For any proposed metric, state the decision, tier, gate quantity, effect size, false-alarm target, and detection target before running the atlas. Reject requests for a universal tenure threshold without those fields.

When reading a registry row, distinguish the point power estimate from its Wilson interval, the gate verdict from the effect estimate, and a null threshold from missing work. A null threshold is an explicit refusal within the measured domain.

Use tier degradation in manager engagement: show the measured reliability gained from exposure or position data. Do not describe richer transparency as universally “better” when the relevant metric’s power study has not established the difference.

## Limits and go-live

- The atlas uses synthetic ground truth. Its thresholds are conditional on simulator realism, metric specification, effect grid, cadence, and nuisance stresses.
- It requires no external or live manager data.
- The sampler’s $500$-replication cells are illustrative and uncalibrated. Go-live requires the volume-1 run at at least $1{,}000$ seeded paths per cell.
- Size must fall within $5\%\pm1.5$ percentage points, monotonicity and analytic cross-checks must pass, and identical seeds must reproduce identical registry output.
- A nuisance stress that flips a verdict forces a range with the driver named, not a point label.
- Thresholds always travel with their pinned effects: alpha at true $IR=0.5$, hit rate $55\%$ versus $50\%$, sizing discipline $0.8$ versus $0$, and a $0.3$ net-beta walk over $12$ months for drift.
- The atlas governs whether a metric may render. It does not validate a real manager or authorize an allocation decision.

## Key takeaways

- Check false-alarm size before quoting power.
- A sample threshold is meaningful only beside its effect size and transparency tier.
- Roughly $780$ independent trades refers specifically to a $55\%$-versus-$50\%$ hit-rate test at $80\%$ power and $5\%$ size.
- Monte Carlo power is an estimate and needs an interval.
- A null registry threshold is an honest refusal, not a blank.
- The sampler is provisional until the larger validated study supersedes it.

## References

- Grinold, Richard, and Ronald Kahn. *Active Portfolio Management*, on the fundamental law $IR\approx IC\sqrt{BR}$.
- Lo, Andrew W. “The Statistics of Sharpe Ratios.” *Financial Analysts Journal*, 2002.
- Ledoit, Olivier, and Michael Wolf. Robust Sharpe-ratio testing with a studentized circular-block bootstrap. *Journal of Empirical Finance*, 2008.
- Harvey, Campbell, and Yan Liu. Work on noise reduction and multiple testing in performance evaluation. *Review of Financial Studies*, 2018.
- van Hemert and coauthors. Work on simulation-calibrated thresholds. *Journal of Portfolio Management*, 2020.
