# X1 · Tier & Power Atlas — Method Spec

**Date:** 2026-07-06
**Status:** Authored — implementation-ready
**Card:** [`docs/ideas/2026-07-05-idea-cards.md`](../2026-07-05-idea-cards.md) § X1
**Demo:** gallery page `x1.html` (sampler); the playground (X2) is the
interactive face of this study.

---

## 1. What this is

Every analytic in this portfolio makes a claim of the form "this manager has
skill" or "this exposure has drifted." Before we let any such claim drive a
decision, we need to know two things about it. First, **how much history does
the metric need before its answer means anything?** A skill statistic computed
on two years of monthly returns can look decisive and be pure noise. Second,
**how much does the answer degrade as we lose visibility?** The same metric is
sharper when we can see a manager's individual positions than when we see only
their broad exposures, and sharper still than when we see only their headline
returns. The Tier & Power Atlas measures both, for every metric we ship, and
writes the answers down in a form the rest of the program can consume
mechanically.

The atlas is built for the person deciding *whether a given card is even
allowed to render* for a given manager at a given point in their track record.
Its product is not only a document. It is the **PowerGate registry**: a small,
machine-readable file that says, for each metric and each transparency tier,
the smallest amount of data at which that metric clears an agreed bar of
statistical reliability. Every gated card (S2–S5, M1–M4, P1) and every gallery
page reads this file and refuses to display a verdict the data cannot support.
The atlas is the component that keeps the rest of the program honest about what
its own numbers are worth.

## 2. Why we use it

The decision problem is a trade between two kinds of mistake. If we let a
metric speak too early, we get **false alarms**: we tell an allocator a manager
has skill when the apparent signal is just a lucky sample. If we insist on too
much data before we let it speak, we get **missed detections**: a genuinely
skilled manager goes unrecognised for years because our bar was set by guess
rather than by measurement. Statisticians call the false-alarm rate the *size*
of a test and the detection rate its *power*. Naming a data threshold is
exactly choosing a point on the size-versus-power curve — and the honest way to
choose it is to measure the curve, not to assert it.

The naive alternatives fail in instructive ways. Picking a round number ("we
need three years of data") ignores the fact that the required history depends
on how strong the effect is and on how much we can see — three years might be
plenty for a strong signal at position-level transparency and hopelessly short
for a weak one at returns-only. Quoting a textbook formula works only for the
handful of metrics that have a clean closed form under idealised assumptions,
and silently breaks the moment the real estimator departs from those
assumptions. Publishing a threshold with no stated effect size is meaningless:
"780 trades" is only an answer once you say "to separate a 55% hit rate from a
coin flip." What the atlas wins is a threshold for **every** metric and tier,
each stamped with the effect it was measured against, each backed by a power
number with an honest error bar, and each reproducible from a seed.

The reason we can do this at all is that we are not measuring against reality —
we are measuring against a **simulator with known ground truth**. In live data
you never know whether a manager truly has skill, so you can never count how
often your metric correctly detects it. The simulator emits all three
transparency tiers of the *same* strategy whose skill we set by hand, so we can
run the metric thousands of times and simply count how often it fires when
skill is present (power) and how often it fires when skill is absent (size).
That counting is the whole method.

## 3. How it works

### 3.1 The mental model, in prose

Picture one experiment. We dial the simulator to a known skill level, ask it to
generate one synthetic track record of length `T`, run our metric on that
record, and write down a single bit: did the metric fire, or not? One track
record tells us almost nothing — the bit is either 0 or 1. So we repeat the
experiment a thousand times with a thousand independent random seeds, at the
same skill level and the same `T`, and count the fraction of the thousand runs
in which the metric fired. That fraction is our estimate of the metric's
**power** at that skill level and that sample size.

Now run the *same* thousand-run experiment with the skill dial set to **zero**.
The metric should almost never fire — there is nothing to detect — but it will
fire some of the time by chance. That fraction is the metric's **size**: its
false-alarm rate. A metric whose size comes out far above the 5% we targeted is
not trustworthy no matter how much power it seems to have, because it is buying
that power by crying wolf. So size is checked first, always.

Sweep `T` from short to long and the power fraction climbs from near the size
floor toward one. The smallest `T` at which the climbing power curve crosses
0.80 is the **threshold** we publish for that metric. Do the whole thing again
at each transparency tier, and the gap between the tiers' thresholds — the
extra history you need when you can see only exposures instead of positions —
is the **tier degradation** the atlas is named for.

### 3.2 A worked toy example

Suppose our metric is the classic alpha *t*-test: estimate a manager's average
monthly excess return, divide by its standard error, and declare "skill" if the
result exceeds 1.96 (the 5%-size cutoff for a two-sided normal test). Set the
simulator so the manager's true annualised information ratio is 0.5 and ask for
`T = 48` months.

Run one path: the estimated *t* comes out 1.4 — below 1.96, so no detection.
Run a second: *t* = 2.3 — detection. Keep going for 1,000 paths and suppose 252
of them cross 1.96. Then the measured power at (IR = 0.5, `T` = 48) is
252 / 1000 = **0.252**, or 25.2%. Reading this off: a genuinely skilled manager
with an IR of 0.5, observed for four years at returns-only transparency, would
be correctly flagged by this test only about a quarter of the time. That single
number — 25.2% — is exactly the returns-tier power the demo reports for alpha
estimation, and it is why a naive "we have four years, so we trust the *t*-test"
is dangerous.

Now set the skill dial to zero and rerun: suppose 51 of 1,000 paths still cross
1.96. The measured size is 0.051 — comfortably close to the 5% we targeted, so
the test is well-calibrated and its power number is meaningful.

### 3.3 The math, symbol by symbol

**Information ratio from information coefficient.** The simulator is dialled in
*information coefficient* (IC, the correlation between forecast and outcome),
but skill is naturally read as an *information ratio* (IR, risk-adjusted excess
return). Grinold & Kahn's fundamental law connects them:

```
IR ≈ IC · sqrt(BR)
```

where:
- `IR` = information ratio, annualised (excess return per unit of active risk);
- `IC` = information coefficient, the per-bet forecasting correlation;
- `BR` = breadth, the number of independent bets per year.

In words: a modest per-bet edge becomes a strong portfolio-level ratio only if
you can place it across many independent bets. This is why breadth is one of
the atlas's axes.

**Detection rule — alpha *t*-test.** For a return series `r_1 … r_T`:

```
t = mean(r) / ( std(r) / sqrt(T) )      detect skill if |t| > 1.96
```

where:
- `mean(r)` = sample mean monthly excess return;
- `std(r)` = sample standard deviation of monthly excess return;
- `T` = number of monthly observations;
- `1.96` = the two-sided 5%-size critical value of the standard normal.

In words: how many standard errors is the average return away from zero; if
that is more than about two, call it skill. Distributional assumption: returns
are treated as independent and identically distributed with finite variance, so
that the *t* statistic is approximately standard normal under the no-skill null.

**Detection rule — hit-rate binomial test.** For `n` independent trades of
which `k` are winners, test the observed win rate `k/n` against a coin flip
(0.5) with a binomial test at 5% size; detect if the two-sided p-value < 0.05.

**Power under the noncentral *t*.** When the *t*-test's assumptions hold, its
power has a closed form through the *noncentrality parameter*:

```
λ = IR_ann · sqrt(T / 12)
```

where:
- `λ` = noncentrality parameter of the *t* distribution under the alternative;
- `IR_ann` = the true annualised information ratio;
- `T / 12` = the record length expressed in years.

In words: the statistic that under the null is centred at zero is, under a real
effect, centred at `λ`; the bigger `λ`, the further the statistic sits past the
1.96 cutoff on average, and the more often it clears it. Power is then the
probability that a noncentral-*t* variate with parameter `λ` exceeds the
critical value. We use this only as an **analytic cross-check** on the
simulated power — where the two disagree beyond Monte Carlo error, something in
the harness or the simulator is wrong and must be found before we publish.

**Sample size for a hit-rate gate.** For the one-sample binomial test the
required number of independent trades to reach power `1 − β` against a specific
alternative is:

```
n = ( z_{α/2}·sqrt(p0·q0) + z_β·sqrt(p1·q1) )^2 / (p1 − p0)^2
```

where:
- `p0`, `q0` = null win rate and its complement (here `p0 = 0.5`, `q0 = 0.5`);
- `p1`, `q1` = alternative win rate and its complement (here `p1 = 0.55`);
- `z_{α/2}` = normal quantile for the chosen size (`z_{0.025} = 1.96`);
- `z_β` = normal quantile for the chosen power (`z_{0.20} = 0.842` for 80%).

Plugging in `p0 = 0.5`, `p1 = 0.55`, `z_{0.025} = 1.96`, `z_{0.20} = 0.842`
gives `n ≈ 782`. In words: to be 80% sure of distinguishing a 55% hitter from a
coin at a 5% false-alarm rate you need roughly 780 independent trades. It is the
single most quotable number in the program, and it is derivable by hand.

**Wilson interval on a Monte Carlo proportion.** Every power number is itself an
estimate — a fraction `k/n` of simulated detections — so it carries sampling
error and must be reported with an interval. We use the Wilson score interval,
which unlike the textbook `p̂ ± z·sqrt(p̂q̂/n)` stays inside `[0, 1]` and behaves
well near 0 and 1:

```
center = (p̂ + z²/2n) / (1 + z²/n)
half   = ( z/(1 + z²/n) ) · sqrt( p̂q̂/n + z²/4n² )
interval = center ± half
```

where:
- `p̂ = k/n` = the observed detection fraction;
- `q̂ = 1 − p̂`;
- `n` = number of replications;
- `z` = normal quantile for the interval level (`z = 1.96` for 95%).

At `n = 1,000` replications the Monte Carlo standard error of a power estimate
near 0.5 is `sqrt(0.25/1000) ≈ 1.6%`. That ±1.6% is the reporting floor for the
atlas: it is small enough to place a 0.80 threshold with confidence but is
always shown, never hidden.

### 3.4 What the canonical papers contribute

- **Grinold & Kahn** — the fundamental law of active management, `IR ≈ IC·√BR`.
  It is the bridge that lets us dial the simulator in IC (a per-bet quantity we
  can reason about) yet report thresholds in IR (the portfolio quantity an
  allocator cares about), and it justifies breadth as an axis of the study.
- **Lo (2002, FAJ)** — showed that the standard error of a Sharpe ratio, and the
  common practice of annualising by `√12`, are wrong under serial correlation,
  and derived the corrected standard error. We use it so the Sharpe-CI metric's
  interval is honest rather than the naive one.
- **Ledoit & Wolf (2008, JEF)** — gave a studentised circular-block bootstrap
  for testing Sharpe-ratio differences that is valid under heavy tails and
  autocorrelation. It supplies the robust variant of the Sharpe-CI metric.
- **Harvey & Liu (2018, RFS)** — framed cross-sectional performance evaluation as
  a multiple-testing / noise-reduction problem, motivating shrinkage of noisy
  per-manager estimates toward a cohort — the mechanism behind the shrinkage
  posterior that outperforms the raw *t*-test in the demo.
- **van Hemert et al. (2020, JPM)** — established simulation-calibrated
  thresholds (backtest the statistic on data with known properties, read the
  threshold off the simulated distribution) as a legitimate design pattern. The
  atlas generalises their move from one statistic to a whole registry.

## 4. How to implement

The estimator below is self-contained teaching code — paste it into a fresh
file, run it, and adapt it. It is written from scratch and imports nothing from
this project; it implements exactly the formulas of §3.3: the alpha *t*-test
detection rule, the Monte Carlo power/size loop, the Wilson interval, threshold
extraction, and the analytic cross-checks (Grinold–Kahn, noncentral-*t*, and the
binomial sample-size formula).

```python
"""A minimal statistical-power measurement loop, from scratch.

Ground truth is known because we generate the data ourselves. We count how
often a metric fires when an effect is present (power) and when it is absent
(size), then read the smallest sample length that clears an 80% power bar.
"""

import numpy as np
from scipy import stats  # used only for normal / noncentral-t quantiles


# --- 1. Ground-truth data generator ------------------------------------------

def simulate_monthly_returns(ir_annual: float, n_months: int,
                             rng: np.random.Generator) -> np.ndarray:
    """Return one synthetic track record of monthly excess returns.

    The manager's *true* annualised information ratio is ``ir_annual``. We fix
    the monthly volatility at 1.0, so the monthly mean that produces that ratio
    is ir_annual / sqrt(12). Setting ir_annual = 0 gives a no-skill manager.
    """
    monthly_sigma = 1.0
    monthly_mean = ir_annual / np.sqrt(12) * monthly_sigma
    return rng.normal(loc=monthly_mean, scale=monthly_sigma, size=n_months)


# --- 2. Detection rule (the metric under test) -------------------------------

def detects_alpha(returns: np.ndarray, crit: float = 1.96) -> bool:
    """Alpha t-test: fire if the mean is > ``crit`` standard errors from zero.

    t = mean / (std / sqrt(T)); detect if |t| > crit. crit = 1.96 is the
    two-sided 5%-size cutoff of the standard normal.
    """
    n = returns.size
    std = returns.std(ddof=1)
    if std == 0:
        return False
    t_stat = returns.mean() / (std / np.sqrt(n))
    return abs(t_stat) > crit


# --- 3. Monte Carlo power / size loop ----------------------------------------

def measure_detection_rate(ir_annual: float, n_months: int, n_reps: int,
                           seed: int) -> tuple[int, int]:
    """Count detections over ``n_reps`` independent synthetic track records.

    Returns (k, n): k detections out of n replications. Call with the true IR
    to get power; call with ir_annual = 0 to get size (the false-alarm rate).
    Each replication draws from an independent child stream of one base seed,
    so results are reproducible and the streams never overlap.
    """
    parent = np.random.SeedSequence(seed)
    detections = 0
    for child in parent.spawn(n_reps):
        rng = np.random.default_rng(child)
        returns = simulate_monthly_returns(ir_annual, n_months, rng)
        detections += int(detects_alpha(returns))
    return detections, n_reps


# --- 4. Wilson 95% interval on the measured proportion -----------------------

def wilson_interval(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score interval for a proportion k/n. Stays inside [0, 1]."""
    p_hat = k / n
    denom = 1 + z**2 / n
    center = (p_hat + z**2 / (2 * n)) / denom
    half = (z / denom) * np.sqrt(p_hat * (1 - p_hat) / n + z**2 / (4 * n**2))
    return center - half, center + half


# --- 5. Threshold extraction: smallest T that reaches 80% power --------------

def find_power_threshold(ir_annual: float, t_grid: list[int], n_reps: int,
                         seed: int, target_power: float = 0.80) -> int | None:
    """Return the smallest sample length in ``t_grid`` with power >= target.

    None means no tenure in the measured range suffices — exactly how the
    PowerGate registry records a metric that never clears the bar.
    """
    for n_months in t_grid:
        k, n = measure_detection_rate(ir_annual, n_months, n_reps, seed)
        power = k / n
        if power >= target_power:
            return n_months
    return None


# --- 6. Analytic cross-checks (must agree with the simulation) ---------------

def ir_from_ic(ic: float, breadth: int) -> float:
    """Grinold-Kahn fundamental law: IR ~= IC * sqrt(breadth)."""
    return ic * np.sqrt(breadth)


def analytic_ttest_power(ir_annual: float, n_months: int,
                         crit: float = 1.96) -> float:
    """Power of the alpha t-test via the noncentral-t distribution.

    Noncentrality lambda = IR_ann * sqrt(T / 12). Power is the mass of a
    noncentral-t (df = T-1) beyond the +/- crit cutoffs.
    """
    lam = ir_annual * np.sqrt(n_months / 12)
    df = n_months - 1
    upper = 1 - stats.nct.cdf(crit, df, lam)
    lower = stats.nct.cdf(-crit, df, lam)
    return upper + lower


def required_trades_binomial(p0: float, p1: float,
                             alpha: float = 0.05, beta: float = 0.20) -> float:
    """Sample size for a one-sample binomial test; ~782 for 0.50 vs 0.55."""
    z_alpha = stats.norm.ppf(1 - alpha / 2)   # 1.96 at alpha = 0.05
    z_beta = stats.norm.ppf(1 - beta)         # 0.842 at beta = 0.20
    numerator = (z_alpha * np.sqrt(p0 * (1 - p0))
                 + z_beta * np.sqrt(p1 * (1 - p1))) ** 2
    return numerator / (p1 - p0) ** 2


if __name__ == "__main__":
    T_GRID = [24, 36, 48, 60, 120]
    N_REPS = 1000
    SEED = 20260706

    # Power at a true IR of 0.5, and size at IR = 0 (should sit near 0.05).
    k_pow, n = measure_detection_rate(0.5, 48, N_REPS, SEED)
    k_size, _ = measure_detection_rate(0.0, 48, N_REPS, SEED)
    lo, hi = wilson_interval(k_pow, n)
    print(f"power(IR=0.5, T=48) = {k_pow/n:.3f}  Wilson95 [{lo:.3f}, {hi:.3f}]")
    print(f"size (IR=0.0, T=48) = {k_size/n:.3f}")

    thr = find_power_threshold(0.5, T_GRID, N_REPS, SEED)
    print(f"threshold (months) = {thr}")
    print(f"binomial n for 0.50 vs 0.55 = {required_trades_binomial(0.5, 0.55):.0f}")
```

## 5. Reading the demo

The gallery sampler (`x1.html`) renders three exhibits, all computed at 500
managers per cell (atlas volume 1 raises that to ≥1,000).

- **Exhibit 1 — power curves.** Three small charts, one per skill level
  (realized IR 0.30, 0.65, 1.57). Each plots two lines against sample length
  `T` (months, 24 to 120): the OLS *t*-test and the shrinkage posterior. The
  dashed horizontal line marks the 80% power bar. The amber poster label above
  them — "~10% false-attribution at IC=0 — the price of borrowing strength" —
  is the posterior's *size*: the cost of the extra power it buys. These curves
  are the returns-only (R-tier) slice: even the shrinkage posterior, the
  fastest climber, has a point estimate just below the 80% bar at the middle
  effect (0.788 at `T` = 120). Its Wilson half-width is 0.035757, so the visible
  point-plus/minus-half-width envelope spans the bar; 0.788 is a point-gate
  decision, not evidence that the underlying power is precisely below 0.80.
  Pinning betas at tier E pushes the posterior point estimate to 0.820 at
  `T` = 120, which is the atlas headline.
- **Exhibit 2 — tier degradation table.** At a fixed cell (`T` = 48, IC = 0.04)
  it shows each analytic's power and RMSE by tier: alpha estimation at
  returns-tier (25.2% power) versus exposure-tier (31.8%), hit rate at
  position-tier (13.2%), sizing skill at position-tier (23.4%), and drift
  detection deferred. The lift from 25.2% to 31.8% is precisely what one extra
  step of transparency buys, stated in power rather than adjectives.
- **Exhibit 3 — PowerGate registry (sampler).** The machine-readable thresholds
  file, shown row per metric. In this sampler both rows carry a null threshold,
  rendered as "no tenure in the measured range suffices" — the honest statement
  that at 500 reps neither metric clears 80% power anywhere in the measured
  span. Each row still carries its effect size, so no gate is ever quoted
  without the effect it was measured against.

What an allocator should conclude: at these effect sizes and this transparency,
four years of monthly data is not enough to trust a raw skill *t*-test, the
shrinkage posterior helps but at a stated false-alarm cost, and every extra tier
of transparency has a measurable, not rhetorical, value.

## 6. Honest limits & go-live

**Data contract.** No external data. The input surface is the simulator's
dials; the output surface is two artifacts with pinned schemas.

*Consumed (simulator):* `ManagerConfig` dials — information coefficient, alpha
half-life, sizing discipline, book size/breadth, rebalance fraction, gross/net —
plus `T` (sample length) and the three tier emissions (returns-only, exposure
summaries, positions/trades).

*Produced (frozen interface — consumers depend on this)* —
`site/data/powergate_registry.json`:

```json
{
  "version": 1,
  "run": {"seed": 42, "replications": 1000, "atlas_volume": 1},
  "metrics": {
    "hit_rate": {
      "min_tier": "P",
      "gate_quantity": "independent_trades",
      "threshold": 780,
      "effect": "separate hit 55% from 50%",
      "power_at_threshold": 0.80,
      "size": 0.05,
      "verdict": "shrink"
    }
  }
}
```

One entry per (metric, tier) pair; `threshold` is the smallest value of
`gate_quantity` at which measured power ≥ 0.80 against the stated effect at size
0.05. Plus the atlas document itself (tables + SVG power curves).

**Experimental grid (volume 1).** Primary factors: IC ∈ {0, 0.02, 0.04, 0.07,
0.10} × alpha half-life months ∈ {3, 12, 36} × T ∈ {24, 36, 48, 60, 120} — 75
cells. Holdings-tier metrics add breadth ∈ {30, 100, 300} and sizing discipline
∈ {0, 0.8} on the relevant subset. The IC = 0 cells are not filler: they measure
size (the false-alarm rate), and a test whose size is distorted gets no power
claim at all. Nuisance stress (volume 1, coarse): market-vol regime × {0.75,
1.25} on a 10-cell subsample, to bound how conclusions move with simulator
realism.

**Metric set (volume 1, hard-capped).** Each detection rule is pre-registered
before any run.

| Metric | Tier(s) scored | Detection rule (pre-registered) |
| --- | --- | --- |
| OLS alpha t-test | R, E | \|t\| > 1.96 |
| Shrunk posterior alpha (S1 §3.6 closed form) | R, E | P(α>0) > 0.95 |
| Sharpe CI (Lo SE; Ledoit–Wolf bootstrap variant) | R | 95% CI excludes 0 |
| Hit rate | P | binomial test vs 0.5 at 5% |
| Sizing-curve slope | P | slope t > 1.96 vs equal-weight counterfactual |
| Alpha-decay shape | P | front-loading contrast t > 1.96 |
| Exposure-drift detector | E (measured) vs R (24m rolling beta) | breach of pre-set band |

Scoring E for the alpha metrics means betas pinned to the emitted exposure
summaries (the S1 §3.3 mechanism); scoring R means betas estimated. The
tier-degradation delta for a metric is the difference in power/RMSE across its
playable tiers at identical ground truth.

**Estimands per (metric, tier, cell).** Power = P(detect | effect present);
size = P(detect | IC = 0); bias and RMSE of the point estimate; interval
coverage where the metric ships an interval. Replications: ≥1,000 seeded paths
per cell — the Monte Carlo standard error of a power estimate near 0.5 is
`sqrt(0.25/1000) ≈ 1.6%`, adequate for placing a 0.80 threshold; report Wilson
95% intervals on every power number. Seeding: one base seed; child streams per
(cell, replication) via the simulator's existing stream-tag convention — no
shared bit streams.

**Threshold extraction.** For each (metric, tier): fit the power curve over the
gate quantity (`T` for returns metrics, trade count for holdings metrics) by
monotone interpolation; `threshold` = smallest quantity with power ≥ 0.80
against the pinned effect size. Pinned effects (volume 1): alpha metrics — true
IR 0.5; hit rate — 55% vs 50%; sizing slope — discipline 0.8 vs 0; drift — a 0.3
net-beta walk over 12 months. Effects are stored in the registry so no gate is
ever quoted without its effect size.

**Validation of the atlas itself (kill criteria).**

1. **Analytic cross-checks.** Where closed forms exist, measured power must
   match within Monte Carlo error: binomial power for the hit rate (the ~780
   number is derivable by hand — §3.3), noncentral-*t* power for the alpha
   *t*-test under ideal assumptions. Disagreement beyond MC error localises a
   simulator or harness artifact — investigate before publishing anything.
2. **Size discipline.** Measured size within 5% ± 1.5 pp; a size-distorted test
   is flagged and its gate is computed from a size-corrected critical value, or
   the metric's row is published as "size-distorted — no gate."
3. **Monotonicity invariants.** Power non-decreasing in `T` and in IC up to MC
   noise; violations block the registry build.
4. **Reproducibility.** Same seed ⇒ byte-identical registry (tested).
5. **Realism bound.** If the coarse nuisance stress flips any verdict
   (robust ↔ noise) across the stressed range, that metric's verdict is
   published as a *range with the driver named*, never a point. The atlas's
   honesty about its own conditionality is part of the product.

**Go-live requirements.** None external — this is a simulator study. Compute
budget: a single machine, under an hour per full volume-1 run (75 cells × 1,000
reps × ~10 ms/sim ≈ tens of minutes; a per-cell cache makes iteration cheap). It
"goes live" when the validation gates pass and the registry replaces the
gallery's starter grid. All figures on the demo are illustrative and
uncalibrated: they are simulator output at 500 reps, provisional until the
volume-1 run at ≥1,000 reps supersedes them.

**Implementation architecture (for build reference).**

- `src/quant_allocator/flagships/atlas/grid.py` — cell dataclasses and the
  volume-1 grid definition (all values as named constants).
- `.../atlas/metrics.py` — each metric a pure function
  `(tier_emission, truth) -> MetricResult(point, interval, detected)`; shared
  nothing, individually unit-tested against hand-computable cases.
- `.../atlas/runner.py` — the Monte Carlo loop, `multiprocessing` over cells,
  per-cell parquet cache keyed by (cell, seed, code-version) so re-runs are
  incremental.
- `.../atlas/registry.py` — threshold extraction + registry JSON emission
  (schema above, sorted keys, fixed precision).
- `.../atlas/report.py` — tables + SVG power curves for the atlas document and
  the gallery sampler.
- Depends: simulator (ready), S1 §3.6 closed form (shared code with the
  skill-ledger `empirical.py` — import, don't duplicate). Effort: M
  (~6 sessions).

**Adoption.** The atlas document is organized per metric, not per
statistic-family: one chapter = one metric = its power curves, its degradation
table, its verdict chip, its registry row. The degradation table doubles as
engagement material ("here is what your transparency tier buys — in statistical
power, not adjectives") and feeds rung justifications in the E1 ladder. The
registry is consumed mechanically by the gallery's PowerGates and the pack
generator; nothing downstream hand-copies a threshold.

The sampler JSON makes that same rule testable. Its named `headline` block
contains the R-tier and E-tier reference points; every power-curve series has an
aligned `*_wilson` array; and every degradation row carries its own `wilson`
object. Each object stores the emitted replication count, half-width, and clipped
point-plus/minus-half-width envelope. The generator re-derives those fields from
the emitted power and replication count; the page binds them without estimating
anything in JavaScript.

## 7. Deeper reading

**Derivations to own:**

1. **The 780-trade number** (one-sample binomial power):
   `n = (z_{α/2}·√(p0·q0) + z_β·√(p1·q1))² / (p1 − p0)²` with `p0 = 0.5`,
   `p1 = 0.55`, `z_{0.025} = 1.96`, `z_{0.20} = 0.842` gives `n ≈ 782`. Work it
   by hand once; it is the single most quotable number in the program.
2. **Power of the alpha *t*-test via the noncentral *t*:** noncentrality
   `λ = IR_ann · √(T/12)` — connects Sweep C's arithmetic to the simulator's
   measurements.
3. **Why size checks precede power claims:** an oversized test buys "power" by
   lying about its false-alarm rate; power comparisons are only meaningful at
   matched size.
4. **The Wilson interval for a Monte Carlo proportion,** and why ±1.6% at 1,000
   reps is the reporting floor.

**Canonical references:** Lo (2002, FAJ) — Sharpe standard error and the
annualisation trap; Ledoit–Wolf (2008, JEF) — studentised bootstrap for Sharpe;
Grinold & Kahn — `IR ≈ IC·√BR`, the breadth axis's rationale; Harvey & Liu
(2018, RFS) — noise-reduction framing for the cross-section; van Hemert et al.
(2020, JPM) — simulation-calibrated thresholds as a design pattern (the atlas
generalises their move). See §3.4 for what each contributes.

**Questions you should be able to answer after reading this page:**

- Derive the 780 number at a whiteboard.
- Explain to a non-statistician why a metric can be "true but useless at our
  sample size."
- State precisely what makes the atlas's conclusions conditional (simulator
  realism) and how the nuisance stress bounds it.
- Explain why the registry stores effect sizes next to thresholds, and why size
  is checked before any power claim is quoted.
