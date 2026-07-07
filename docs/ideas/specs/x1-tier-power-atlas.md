# X1 · Tier & Power Atlas — Method Spec

**Date:** 2026-07-06
**Status:** Authored — implementation-ready
**Card:** [`docs/ideas/2026-07-05-idea-cards.md`](../2026-07-05-idea-cards.md) § X1
**Demo:** gallery page `x1.html` (sampler); the playground (X2) is the
interactive face of this study.

## 1. Problem & decision hook

Two questions sit under every analytic in the portfolio: **how much data
until this metric means anything** (the power axis), and **how much does it
degrade from position-level to exposure-level to returns-only observation**
(the tier axis). Neither is published anywhere for allocator analytics
(Sweeps B and C). The simulator answers both by construction: it emits all
three tiers of the *same* known ground truth, so every metric can be scored
against the truth at every tier and sample size.

The atlas's product is not a document alone — it is the **PowerGate
registry**: a machine-readable thresholds file that decides which analytics
are allowed to render, for which manager, at which tenure. Every gated card
(S2–S5, M1–M4, P1) and every gallery page consumes it. Decisions improved:
all of them, at the meta level — the atlas is what keeps the rest of the
program honest.

## 2. Data contract

No external data. Input surface = the simulator's dials; output surface =
two artifacts with pinned schemas.

**Consumed (simulator):** `ManagerConfig` dials — information coefficient,
alpha half-life, sizing discipline, book size/breadth, rebalance fraction,
gross/net — plus `T` (sample length) and the three tier emissions
(returns-only, exposure summaries, positions/trades).

**Produced (frozen interface — consumers depend on this):**
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
`gate_quantity` at which measured power ≥ 0.80 against the stated effect at
size 0.05. Plus the atlas document itself (tables + SVG power curves).

## 3. Methodology — experimental design

### 3.1 Grid (volume 1)

Primary factors: IC ∈ {0, 0.02, 0.04, 0.07, 0.10} × alpha half-life months
∈ {3, 12, 36} × T ∈ {24, 36, 48, 60, 120} — 75 cells. Holdings-tier metrics
add breadth ∈ {30, 100, 300} and sizing discipline ∈ {0, 0.8} on the
relevant subset. IC = 0 cells are not filler: they measure **size** (false-
alarm rate), and a test whose size is distorted gets no power claim at all
(§4). Nuisance stress (volume 1, coarse): market-vol regime ×{0.75, 1.25}
on a 10-cell subsample, to bound how conclusions move with simulator
realism.

### 3.2 Metric set (volume 1, hard-capped)

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
tier-degradation delta for a metric is the difference in power/RMSE across
its playable tiers at identical ground truth.

### 3.3 Estimands per (metric, tier, cell)

Power = P(detect | effect present); size = P(detect | IC = 0); bias and
RMSE of the point estimate; interval coverage where the metric ships an
interval. Replications: ≥1,000 seeded paths per cell — Monte Carlo SE of a
power estimate near 0.5 is $\sqrt{0.25/1000} \approx 1.6\%$, adequate for
0.80-threshold placement; report Wilson 95% intervals on every power
number. Seeding: one base seed; child streams per (cell, replication) via
the simulator's existing stream-tag convention — no shared bit streams.

### 3.4 Threshold extraction

For each (metric, tier): fit the power curve over the gate quantity (T for
returns metrics, trade count for holdings metrics) by monotone
interpolation; `threshold` = smallest quantity with power ≥ 0.80 against
the pinned effect size. Pinned effects (volume 1): alpha metrics — true
IR 0.5; hit rate — 55% vs 50%; sizing slope — discipline 0.8 vs 0;
drift — a 0.3 net-beta walk over 12 months. Effects are stated in the
registry so no gate is ever quoted without its effect size.

## 4. Power & validation plan (validation of the atlas itself)

1. **Analytic cross-checks** where closed forms exist, measured power must
   match within MC error: binomial power for hit rate (the ~780 number is
   derivable by hand — §8.1), noncentral-t power for the alpha t-test under
   ideal assumptions. Disagreement beyond MC error localizes a simulator or
   harness artifact — investigate before publishing anything.
2. **Size discipline:** measured size within 5% ± 1.5 pp; a size-distorted
   test is flagged and its gate is computed from a size-corrected critical
   value, or the metric's row is published as "size-distorted — no gate."
3. **Monotonicity invariants:** power non-decreasing in T and in IC up to
   MC noise; violations block the registry build.
4. **Reproducibility:** same seed ⇒ byte-identical registry (tested).
5. **Realism bound (kill criterion):** if the coarse nuisance stress flips
   any verdict (robust↔noise) across the stressed range, that metric's
   verdict is published as a *range with the driver named*, never a point.
   The atlas's honesty about its own conditionality is part of the product.

## 5. Implementation architecture

- `src/quant_allocator/flagships/atlas/grid.py` — cell dataclasses and the
  volume-1 grid definition (all values from §3.1 as named constants).
- `.../atlas/metrics.py` — each metric a pure function
  `(tier_emission, truth) -> MetricResult(point, interval, detected)`;
  shared nothing, individually unit-tested against hand-computable cases.
- `.../atlas/runner.py` — MC loop, `multiprocessing` over cells, per-cell
  parquet cache keyed by (cell, seed, code-version) so re-runs are
  incremental.
- `.../atlas/registry.py` — threshold extraction + registry JSON emission
  (schema §2, sorted keys, fixed precision).
- `.../atlas/report.py` — tables + SVG power curves for the atlas document
  and the gallery sampler.
- Runtime envelope: 75 cells × 1,000 reps × O(10 ms)/sim ≈ tens of minutes
  single-machine; the cache makes iteration cheap. Effort: M (~6 sessions).
- Depends: simulator (ready), S1 §3.6 closed form (shared code with the
  skill-ledger `empirical.py` — import, don't duplicate).

## 6. Adoption & packaging

The atlas document is organized per metric, not per statistic-family: one
chapter = one metric = its power curves, its degradation table, its
VerdictChip, its registry row. The degradation table doubles as engagement
material ("here is what your transparency tier buys — in statistical
power, not adjectives") and feeds rung justifications in the E1 ladder.
The registry is consumed mechanically by the gallery's PowerGates and the
pack generator; nothing downstream hand-copies a threshold.

## 7. Go-live requirements

None external — this is a simulator study. Compute budget: single machine,
under an hour per full volume-1 run. It "goes live" when §4's gates pass
and the registry replaces the gallery's starter grid.

## 8. Learning notes

**Derivations to own:**

1. **The 780-trade number** (one-sample binomial power): required
   $n = \big(z_{\alpha/2}\sqrt{p_0 q_0} + z_\beta\sqrt{p_1 q_1}\big)^2 /
   (p_1 - p_0)^2$ with $p_0 = 0.5$, $p_1 = 0.55$, $z_{0.025} = 1.96$,
   $z_{0.20} = 0.842$ gives $n \approx 782$. Work it by hand once; it is
   the single most quotable number in the program.
2. Power of the alpha t-test via the noncentral t: noncentrality
   $\lambda = \text{IR}_{\text{ann}}\sqrt{T/12}$ — connects Sweep C's
   arithmetic to the simulator's measurements.
3. Why size checks precede power claims: an oversized test buys "power"
   by lying about its false-alarm rate; power comparisons are only
   meaningful at matched size.
4. Wilson interval for a Monte Carlo proportion, and why ±1.6% at 1,000
   reps is the reporting floor.

**Canonical references:** Lo (2002, FAJ) — Sharpe SE and the annualization
trap; Ledoit–Wolf (2008, JEF) — studentized bootstrap for Sharpe;
Grinold & Kahn — IR ≈ IC·√BR, the breadth axis's rationale; Harvey & Liu
(2018, RFS) — noise-reduction framing for the cross-section; van Hemert et
al. (2020, JPM) — simulation-calibrated thresholds as a design pattern
(the atlas generalizes their move).

**Defend unaided:** derive the 780 number at a whiteboard; explain to a
non-statistician why a metric can be "true but useless at our sample size";
state precisely what makes the atlas's conclusions conditional (simulator
realism) and how the nuisance stress bounds it; explain why the registry
stores effect sizes next to thresholds.
