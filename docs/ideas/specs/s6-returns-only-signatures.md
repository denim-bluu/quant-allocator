# S6 · Returns-Only Sizing & Decay Signatures — Method Spec

**Status: Reviewed — method gate passed 2026-07-07 (rulings in §8)**
**Date:** 2026-07-07
**Card:** [`docs/ideas/2026-07-05-idea-cards.md`](../2026-07-05-idea-cards.md) § S6
**Demo:** gallery page `s6.html` (the pre-registration document + the verdict grid, nulls rendered first-class; fully synthetic, §5)

---

## 1. What this is

S6 is not an estimator, a monitor, or a score. It is a **pre-registered hypothesis
test**, and the pre-registration protocol itself is the product. The question under
test: *do monthly net returns alone carry any usable information about a manager's
sizing discipline or alpha half-life?* Both quantities are natively **position-tier**
analytics — a sizing curve needs the positions (card S3), a decay curve needs the
trades — but most of the roster reports returns only. If even a weak returns-only
proxy existed, it would cover the *many* rather than the transparent few. Nobody has
published one; several vendors imply they have one. The honest way to resolve that is
not to build a proxy and admire it, but to **commit in advance** to a small family of
candidate signatures, a test statistic, a significance discipline, and the exact
simulation cells that will decide — and then run the test once, on managers whose
sizing discipline and alpha half-life are *known by construction*, and publish
whatever comes out.

The expected outcome, stated up front, is **mostly null**. The nearest analogue in
the convergence review — returns-based style-drift inference — carries a Noise verdict
at 36–60 monthly observations, and the burden of proof sits entirely on this card.
That is why the deliverable is a *protocol plus its verdicts*, in which a null is a
first-class finding with the same standing as a discovery. A confirmed null is
directly useful to the allocator twice over: it is a defense against anyone selling
returns-only "sizing analytics," and it is the sharpest possible argument for the
transparency ask ("we measured that this cannot be inferred from returns — this is
why we ask for exposures"). A confirmed positive — a signature that clears the
pre-registered bar across the whole nuisance grid — would be a genuinely new,
publishable returns-only tell, adopted cautiously as a *conversation prompt* for the
**monitor** and **select** decisions, never as a standalone score.

The consumers are the **investment team** (whatever survives becomes a labeled chip
on the returns-only majority of the roster; whatever dies becomes a documented
"cannot be inferred from returns" note) and the **program itself** (the verdict
either extends the X1 atlas with a new row or closes a research question in writing).

## 2. Why we use it

Sweep B flags "inferring sizing discipline or alpha-decay signatures from monthly
returns" as high-value, low-confidence white space: high-value because sizing
discipline and alpha decay are exactly what a returns-only allocator most wants to
know and least can see; low-confidence because the mechanism that would print those
traits onto a monthly return series is weak. A manager's monthly return is one number
summing ~65 positions; the idiosyncratic noise of the book dwarfs the second-order
texture that sizing style or signal aging might add. The prior, honestly stated, is
that the fingerprint mostly washes out.

The naive approaches to this question fail in instructive ways. *Build the proxy and
backtest it* is the vendor route: pick features until something separates two groups
of managers in-sample, then sell the survivor. With enough candidate features and
freedom to choose thresholds after looking, something always "works" — that is a
garden of forking paths, and the result is unfalsifiable by construction. *Screen a
large feature pool with FDR control* is the academic route, and it is on this
program's **do-not-build list** for exactly this setting: FDR machinery is built for
thousands of simultaneous tests where a tolerable fraction of false discoveries is
acceptable; here the candidate family is small, the deliverable is a yes/no on a
named hypothesis, and *one* falsely shipped tell poisons the product. What
pre-registration wins instead is **credibility in both directions**: because the
family, the bar, and the deciding cells are frozen before any run, a positive cannot
be a forking-paths artifact, and a null cannot be quietly reframed as "we just need
more features."

The simulator makes the test cleanly falsifiable in a way no real-world panel can:
`sizing_discipline` and `alpha_half_life_months` are literal dials on the synthetic
manager, so we can generate populations that differ *only* in the trait under test,
hold every nuisance at realistic levels, and know the truth of every label. Sweep C
gives no power prior for this card — the *absence* of a prior is the card. The
protocol is an X1-atlas extension: its cells land in the atlas as new rows either way.

- **Decisions improved:** **monitor** and **select** — *if* a tell ships, a weak,
  labeled prior nudge on returns-only managers; if none ships, a published negative
  that protects both decisions from false vendors and strengthens the E1
  transparency ask.
- **Customer:** investment team (the returns-only majority of the roster); the
  research program (an atlas row and a closed question either way).

## 3. How it works

### 3.1 The mental model, before any math

Think of a monthly return series as a badly smudged fingerprint of the process that
generated it. Two managers with identical skill but different *sizing styles* run
different books: the conviction-weighted manager concentrates capital in a few names
when conviction is dispersed, so the book's effective breadth — and therefore its
monthly variance — wobbles from month to month; the equal-weight manager holds a
steady, diversified book with a steadier variance. A return series whose variance
wobbles is a *scale mixture*, and scale mixtures have signatures: higher vol-of-vol,
fatter tails (excess kurtosis). Similarly, two managers with different *alpha
half-lives* spend their skill differently through time: the fast-decay manager's
edge lives in the first weeks after each rebalance; the slow-decay manager's edge
persists. Over a fixed evaluation window that can leave traces — a rolling
information ratio that drifts, drawdowns that cluster late once the early alpha
fades.

So candidate mechanisms exist. The reason to expect them to *mostly fail* is
aggregation: the book rebalances only a quarter of each side per month, so position
ages are staggered and the book-level series averages over the whole age
distribution, smearing the decay fingerprint; and the idiosyncratic noise floor of a
65-position book is large relative to the second-moment texture sizing adds. The
question is quantitative — *does any residue survive at T = 60 months?* — and the
only honest way to answer a question you expect to answer "no" is to fix the entire
test before looking. That is what pre-registration is: converting *postdiction*
(finding a pattern and explaining it) into *prediction* (naming the pattern, the
threshold, and the data that will judge it, in advance).

One more piece of intuition before the formulas: the test statistic is the **AUC** —
the probability that a randomly chosen manager from the positive class (say,
disciplined sizing) shows a *higher* signature value than a randomly chosen manager
from the negative class. AUC = 0.5 means the signature is blind; AUC = 1.0 means it
separates the classes perfectly. The card's usability bar, AUC > 0.65, is
deliberately modest — "right about 2 times in 3 on a random pair" — and even that
modest bar is far above what a statistically *detectable* whisper of signal
delivers. Holding those two thresholds apart — *detectable* versus *usable* — is the
central discipline of this card, and §3.6 makes it formal.

### 3.2 The pre-registration protocol — what is frozen, and when

The protocol freezes six things **before the confirmatory run**, in a dated,
committed document (the repo's git history is the timestamping authority; the demo
page renders the document verbatim):

1. **The hypotheses** — two named contrasts with pre-declared directions per
   signature (§3.3).
2. **The signature family** — six returns-only statistics, exact formulas including
   window lengths, hard-capped (§3.4). No signature may be added, removed, or
   re-windowed after the first look at any deciding cell.
3. **The deciding cells** — the exact simulator dial settings, evaluation horizons,
   replication count, and a **fresh confirmatory seed** (§3.7). Pilot runs (including
   this spec's §4 mock and the demo page) burn their own seeds; the confirmatory run
   uses a seed named in the frozen document and never used before.
4. **The test statistic and the significance discipline** — Mann–Whitney AUC per
   (signature, cell), Westfall–Young max-statistic familywise control per contrast
   family at α = 0.05 (§3.5–3.6).
5. **The ship rule** — the two-part usability bar of §3.6, with all constants named.
6. **The verdict taxonomy** — SHIP / WEAK TELL / NULL, each with its exact
   definition and its page rendering (§3.6), so no outcome can be re-labeled after
   the fact.

**Amendment rule.** Any change after first look — a new candidate signature, a
different window, a moved threshold — voids the registration. The change is allowed,
but it creates a **version-2 protocol** with a fresh confirmatory seed and its own
document; results under the old protocol are reported as-registered, permanently.
This is the discipline that makes the null publishable: a null that could have been
amended away is not a finding.

### 3.3 The hypotheses and a worked toy example

Two contrasts, each a two-class discrimination problem on populations of simulated
managers identical in every dial except the trait under test:

- **H-SIZE** — positive class: `sizing_discipline = 0.8`; negative class:
  `sizing_discipline = 0.0` (equal-weight). Everything else identical.
- **H-DECAY** — positive class: `alpha_half_life_months = 3` (fast decay); negative
  class: `alpha_half_life_months = 36` (slow). Everything else identical. The
  extreme contrast is deliberate: if returns cannot separate half-life 3 from 36,
  finer distinctions are settled *a fortiori*.

Each contrast carries a **pre-declared direction** per signature, from the §3.1
mechanisms (the full table is in §3.4). Directions matter: a signature that comes
out significant in the *opposite* direction to its declared mechanism is not a
discovery with a sign flip — it is an anomaly to be explained, and it cannot ship
under this registration (§3.6). The §4 pilot produces exactly one such reversal,
which is the best advertisement for the rule.

**A worked toy example of the statistic.** Take 4 disciplined-sizing managers whose
excess-kurtosis signature comes out {0.9, 1.4, 0.6, 1.1} and 4 equal-weight managers
at {0.3, 0.8, −0.1, 0.5}. The AUC asks: across all 4 × 4 = 16 cross-class pairs, how
often does the disciplined manager show the higher value? Count them: 0.9 beats all
four (4 wins); 1.4 beats all four (4); 0.6 beats 0.3, −0.1, 0.5 but loses to 0.8
(3); 1.1 beats all four (4). Total 15 of 16, so

$$
\widehat{\text{AUC}} = \frac{15}{16} = 0.9375 .
$$

A perfectly blind signature would win about 8 of 16 (AUC ≈ 0.5). The §4 code checks
this exact toy case. At realistic scale nothing looks like 0.94 — the pilot's best
signature manages 0.605 — which is why the machinery below is about *small
deviations from 0.5*, measured carefully.

### 3.4 The signature family — six pre-committed statistics

The family is **hard-capped at six**, each chosen for a stated mechanism, each with
its known confound named in advance. All are computed from the monthly net return
series $r_1, \dots, r_T$ alone.

| # | Signature | Formula (see §4 for code) | Mechanism | Direction H-SIZE | Direction H-DECAY | Known live confound |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | `autocorr` | lag-1 sample autocorrelation | a persistently decaying alpha mean adds trend-induced positive autocorrelation; the slower the decay, the longer the trend persists | none declared | **−** (fast decay ⇒ *less* trend ⇒ lower) | **return smoothing** (Getmansky–Lo–Makarov): illiquidity marks dominate live lag-1 autocorrelation |
| 2 | `vol_of_vol` | CV of rolling 6-month volatility | conviction sizing ⇒ month-to-month wobble in effective breadth ⇒ time-varying book variance | **+** | none declared | leverage changes, vol regimes |
| 3 | `skew` | sample skewness | asymmetric conviction between book sides | none declared | none declared | option-like overlays (M2's written-put posture) |
| 4 | `kurtosis` | excess kurtosis | a scale mixture of normals has fat tails; conviction sizing makes the book a scale mixture | **+** | none declared | fat-tailed underlying markets, overlays |
| 5 | `drawdown_shape` | MDD ÷ ($\hat\sigma\sqrt{T}$) | vol clustering deepens MDD relative to the iid diffusive scale; a mid-window alpha death leaves a late, deep underwater stretch | **+** | **+** | one-episode dominance (M3 §6: a drawdown is n ≈ 1) |
| 6 | `rolling_ir_slope` | OLS time-slope of rolling 12-month IR | front-loaded alpha ⇒ the rolling IR trends down over the window | none declared | **−** (fast decay ⇒ more negative slope) | AUM growth, regime luck |

Rows marked "none declared" are still computed and reported in every cell (the
familywise test covers the whole family regardless), but a signature can only
**ship** for a contrast where its direction was declared — an undeclared row that
comes out significant is registered as an anomaly for a possible v2 hypothesis,
never claimed as a discovery of this run.

Window lengths (6 months for the vol-of-vol, 12 for the rolling IR) are part of the
frozen family: **`S6_ROLLING_WINDOWS` = (6, 12) (provisional — NUMERICS-GATE)**. The
gate may re-set them once, before the confirmatory seed is drawn; after that they
are immutable under the amendment rule.

### 3.5 The test statistic — AUC, exactly

For one signature $s$ and one deciding cell, compute $s$ on every simulated manager
in both classes, giving values $\{s^+_i\}_{i=1}^{n_+}$ and $\{s^-_j\}_{j=1}^{n_-}$.
The Mann–Whitney AUC is

$$
\widehat{A} \;=\; \frac{1}{n_+ n_-} \sum_{i=1}^{n_+} \sum_{j=1}^{n_-}
\Big[ \mathbf{1}\big(s^+_i > s^-_j\big) \;+\; \tfrac{1}{2}\,\mathbf{1}\big(s^+_i = s^-_j\big) \Big] .
$$

where:

- $s^+_i$ — the signature value of the $i$-th manager in the **positive class**
  (the class the pre-declared direction says should score *higher*).
- $s^-_j$ — the signature value of the $j$-th manager in the negative class.
- $n_+, n_-$ — the class sizes (**`S6_N_PER_CLASS` = 500 each, provisional —
  NUMERICS-GATE**; equal to the X1 grid's `N_REPS`, so the confirmatory run reuses
  the grid's replication convention unchanged).
- $\mathbf{1}(\cdot)$ — the indicator function: 1 if the condition holds, else 0;
  ties count half (the Mann–Whitney convention).
- $\widehat{A}$ — the estimated probability that a random positive-class manager
  outranks a random negative-class one. $\widehat{A} = 0.5$ is a blind signature.

In words: the AUC is the fraction of cross-class manager pairs the signature orders
correctly. It is rank-based, so it is invariant to any monotone rescaling of the
signature — no threshold on the raw statistic needs choosing, which removes one
forking path by construction.

Under the null $A = 0.5$, the Hanley–McNeil standard error is

$$
\text{SE}_0(\widehat{A}) \;=\; \sqrt{\frac{n_+ + n_- + 1}{12\, n_+ n_-}} ,
$$

where the symbols are as above. At $n_+ = n_- = 500$ this gives
$\text{SE}_0 = \sqrt{1001/3{,}000{,}000} \approx 0.0183$, i.e. a 95% null band of
roughly ±0.036 around 0.5 **per test in isolation**. Two consequences worth holding
onto: (i) the grid cleanly resolves small effects — an observed AUC of 0.605 sits
$0.105/0.0183 \approx 5.7$ null standard errors from blind; and (ii) the usability
bar 0.65 sits $0.15/0.0183 \approx 8.2$ null standard errors out, so **a genuinely
usable tell cannot be missed at this replication count** — power against a true
AUC ≥ 0.65 is essentially 1 even after the familywise adjustment below. If the grid
returns NULL, it is because the tell is absent or tiny, not because the test was
underpowered. (These closed-form numbers are cross-checks; inference itself is by
permutation, which is exact and needs no normal approximation.)

### 3.6 Significance discipline — familywise over a pre-committed family, and the two-part ship rule

**The multiplicity problem, stated honestly.** Six signatures per contrast, tested
at 5% each, would false-alarm on *some* signature far more often than 5% of the
time — under independence $1 - 0.95^6 \approx 26\%$ per cell. Any procedure that
scans a family and reports the best member must pay for the scan. This program's
do-not-build list prohibits the FDR route (screening an open-ended candidate pool
and tolerating a fraction of false discoveries); what fits this card is the opposite
discipline: a **small, closed, pre-committed family with familywise control** — the
probability of even one false "this signature carries information" claim across the
family is held at α.

**The Westfall–Young max-statistic test.** Under the null for a given cell, the two
classes are generated from identical configurations except the dial, and the null
hypothesis is that the dial leaves the signature's distribution unchanged — so class
labels are **exchangeable**, and permuting them generates the exact joint null
distribution of all six AUCs *including their mutual correlation* (all six
signatures are computed from the same return paths, so they are far from
independent — a Bonferroni correction would waste power on correlation the
permutation absorbs for free). For $B$ label permutations, signature $j$'s
familywise-adjusted p-value is

$$
\tilde p_j \;=\; \frac{1 + \#\Big\{ b \le B :\;
\max_{k \in \text{family}} \big|\widehat{A}^{(b)}_k - 0.5\big| \;\ge\;
\big|\widehat{A}_j - 0.5\big| \Big\}}{B + 1} .
$$

where:

- $\widehat{A}_j$ — signature $j$'s observed AUC in this cell.
- $\widehat{A}^{(b)}_k$ — signature $k$'s AUC recomputed on the $b$-th random
  relabeling of the pooled managers (class sizes preserved).
- $\max_k |\cdot - 0.5|$ — the **max deviation over the whole family** in that
  permutation: the quantity a scan of six signatures actually realizes under the
  null. Comparing each observed deviation to the null distribution of the *max* is
  what makes $\tilde p_j$ familywise.
- $B$ — the permutation count (**`S6_N_PERM` = 5,000 provisional — NUMERICS-GATE**);
  the +1 in numerator and denominator makes the p-value valid at finite $B$.
- $\tilde p_j$ — the probability, under "no signature carries any information," that
  a family scan of this size would produce a deviation at least as large as
  signature $j$'s. Declaring $\tilde p_j \le \alpha$ controls the familywise error
  at $\alpha$ (**`S6_FAMILYWISE_ALPHA` = 0.05 provisional — NUMERICS-GATE**).

In words: instead of asking "is this signature's AUC surprising on its own?", we ask
"is it surprising *even given that we looked at six?*" — and we answer by replaying
the whole six-signature scan thousands of times on relabeled data where the truth is
known to be nothing. The deviation is two-sided ($|\widehat{A}-0.5|$) so that a
significant *reversal* of a declared direction is detected as significant — and then
handled by the direction rule below, not celebrated. The two contrasts are separate
registered hypotheses; each carries its own family of six at α = 0.05 (the verdicts
are decision-separable: a sizing tell and a decay tell would ship, or die,
independently).

**The two-part ship rule.** Statistical significance is *necessary but not
sufficient*. Pre-registered, per (signature, contrast):

$$
\text{SHIP}(j) \iff
\underbrace{\min_{c \,\in\, \text{deciding cells}} \widehat{A}^{\,\text{dir}}_{j,c} \;>\; A_{\min}}_{\text{usable everywhere}}
\quad\text{and}\quad
\underbrace{\max_{c \,\in\, \text{deciding cells}} \tilde p_{j,c} \;\le\; \alpha}_{\text{significant everywhere}}
$$

where:

- $\widehat{A}^{\,\text{dir}}_{j,c}$ — signature $j$'s AUC in cell $c$, **oriented by
  the pre-declared direction** (for a "−" declaration the statistic is negated
  before ranking, so the declared direction always reads as AUC > 0.5). A signature
  with no declared direction for the contrast cannot ship for it.
- $A_{\min}$ — the usability bar, **`S6_AUC_MIN` = 0.65 (provisional —
  NUMERICS-GATE**; the card's stated target)**.
- the min/max over $c$ — **worst-case over the nuisance grid** (§3.7). Requiring
  every deciding cell to pass is an intersection–union test: it *cannot* inflate the
  familywise error beyond the per-cell α (demanding more passes only makes false
  shipping rarer), so no further correction across cells is needed — the cell
  dimension is handled by worst-casing, the signature dimension by Westfall–Young.

**The verdict taxonomy (frozen).** Per (signature, contrast):

| Verdict | Definition | What it becomes |
| --- | --- | --- |
| **SHIP** | passes both parts of the ship rule in every deciding cell | a labeled, weak-prior chip on returns-only managers — pending the external-validity rung (§6.3) |
| **WEAK TELL** | $\tilde p \le \alpha$ in every deciding cell, but worst-case directional AUC ≤ $A_{\min}$ — *or* significant in the direction **opposite** to the declaration | a published finding ("statistically real, too weak to use" / "direction anomaly"), never a product |
| **NULL** | not familywise-significant in at least one deciding cell | a published negative, first-class: rendered with the same visual weight as any discovery |

The gap between the significance floor and the usability bar is the card's central
honesty device, and it is wide: at 500 per class the familywise critical deviation
is roughly ±0.05 around 0.5 (measured on the §4 pilot: an observed deviation of
0.051 earns $\tilde p = 0.032$; 0.044 earns ≈ 0.08–0.13), so the machinery can
*detect* AUC ≈ 0.55 whispers — and the ship rule then correctly refuses to sell
them. "Significant" is a statement about sample size; "usable" is a statement about
the world.

### 3.7 The deciding cells — the X1 grid as the bench

The confirmatory run consumes the existing X1 grid substrate directly — the same
simulated managers, the same seeding convention, no new estimator and no new
simulation engine:

- **Simulator dials** (`simulator/manager.py::ManagerConfig`): `sizing_discipline`
  ∈ {0.0, 0.8} and `alpha_half_life_months` ∈ {3, 36} are the contrast dials —
  both already exist and already span the X1 grid's `SIZING_GRID` and
  `HALF_LIFE_GRID`. `information_coefficient` is the nuisance axis. Neither
  `death_month` nor `net_drift` is used (both stay at their honest defaults).
- **Grid machinery** (`demo_data/x_grid.py`): the per-(config, rep) `SeedSequence`
  stream convention (`_config_seed`), the replication count `N_REPS = 500`, and —
  for the pilot only — the cached per-rep monthly-return arrays that `run_config`
  already produces. S6 adds a signatures kernel module in the `x_metrics.py` style
  (pure functions of a return array, no simulation, no cross-cell logic) and an
  aggregation layer that computes AUCs and permutation p-values across reps.
- **Atlas conventions**: every reported rate carries its interval (Wilson for
  proportions, Hanley–McNeil/bootstrap bands for AUCs — §5), per-module RNG streams
  keep cells independent, and the finished cells are contributed to the X1 atlas as
  this card's rows.

**Deciding cells, pre-registered.** Evaluation horizon $T$ = **`S6_DECISION_T` = 60
(provisional — NUMERICS-GATE**; the card's stated target horizon)**, with $T = 36$
reported alongside as a labeled secondary (how much worse the short window is, is
itself atlas content — never part of the ship rule).

- **H-SIZE**: positive class (ic, hl, **0.8**) vs negative class (ic, hl, **0.0**),
  over the nuisance grid ic ∈ {0.02, 0.04, 0.07, 0.10} × hl ∈ {3, 12, 36} —
  **12 deciding cells**.
- **H-DECAY**: positive class (ic, **3**, sd) vs negative class (ic, **36**, sd),
  over ic ∈ {0.02, 0.04, 0.07, 0.10} × sd ∈ {0.0, 0.8} — **8 deciding cells**.
- The ic = 0 column is computed and displayed as a labeled side exhibit (what does
  "sizing discipline" even mean for a zero-skill book?) but is **not** deciding: a
  tell must work where skill exists, because that is where the decisions are.

**Nuisance realism (the live-confound axes).** A tell that works on clean simulator
output and dies under realistic return contamination is worse than no tell. Two
overlay axes stress the family on a pre-registered subset of cells:

1. **Return smoothing** — the dominant live confound for `autocorr` (and, through
   the de-noised vol, for `vol_of_vol`): illiquidity marking gives real fund series
   lag-1 autocorrelation that has nothing to do with alpha decay
   (Getmansky–Lo–Makarov, §3.8). The simulator has **no smoothing overlay today**;
   a small GLM-style MA(2) overlay in the `overlays.py` pattern (a pure,
   deterministic function of a return series, consuming no RNG stream, with
   θ = (0,0,…) recovering the input exactly) is a **named validation prerequisite**
   of this card — the same kind of small, flagged simulator extension M3 needed for
   its `death_month`.
2. **Short-vol posture** — the existing `WrittenPutOverlay` (M2's machinery,
   consumed as-is) contaminates `skew`/`kurtosis`/`drawdown_shape` with an
   option-like return profile that mimics a sizing fingerprint without any sizing.

A signature that ships must hold its bar on the overlay-stressed cells too; the
overlay grid values are **`S6_NUISANCE_OVERLAYS` (provisional — NUMERICS-GATE)**.

**Seed hygiene.** Every pilot — the §4 mock, the demo page's generator, any
exploratory run — burns seeds that are thereby disqualified. The confirmatory run
uses **`S6_CONFIRM_SEED` (provisional — NUMERICS-GATE)**: a fresh base seed written
into the frozen registration document *before* the run, so that no tuning informed
by pilot draws can leak into the verdict. This costs one full grid recomputation
(the X1 cache does not apply to a new seed) and is worth exactly what it costs.

### 3.8 What the canonical papers contribute

- **Westfall & Young (1993), *Resampling-Based Multiple Testing*.** The
  max-statistic permutation method of §3.6: control the familywise error by
  comparing each test to the null distribution of the *maximum* over the family,
  computed by resampling, so the correction automatically adapts to the correlation
  among tests. This is the house's multiplicity tool (M3 uses the same logic on
  path maxima); here it is the significance discipline itself.
- **Hanley & McNeil (1982), "The Meaning and Use of the Area under a ROC Curve"
  (*Radiology*).** Established the identity AUC = Mann–Whitney U statistic (the
  probability of correctly ordering a random cross-class pair) and the standard
  error formulas of §3.5. This is why the card's "AUC > 0.65" target is a
  well-defined, rank-based, threshold-free quantity rather than a classifier
  accuracy at some arbitrary cut.
- **Getmansky, Lo & Makarov (2004), "An Econometric Model of Serial Correlation and
  Illiquidity in Hedge Fund Returns" (*JFE*).** Showed that the strong lag-1
  autocorrelation in fund returns is mostly *smoothed marks*, not any property of
  the alpha process. This is the named confound that (a) forces the smoothing
  overlay onto the nuisance grid and (b) caps how much a live `autocorr` tell could
  ever be trusted even if it shipped on the simulator.
- **Di Mascio, Lines & Naik (2017), "Alpha Decay" (working paper).** Measured alpha
  decay directly from institutional *trading records* — the P-tier ground truth.
  Its lesson for S6 is framing: decay is real and measurable *from positions*; the
  open question this card tests is whether any residue of it survives aggregation
  into monthly book returns. It is also the external-validation template for a
  shipped tell (§6.3).
- **Nosek, Ebersole, DeHaven & Mellor (2018), "The Preregistration Revolution"
  (*PNAS*).** The methodological frame: pre-registration converts postdiction into
  prediction by committing hypotheses, analyses, and decision rules before the data
  are seen, which is what licenses publishing the null. §3.2's freeze list and
  amendment rule are this paper's discipline applied to a simulation study.

## 4. How to implement

The reference implementation below is **self-contained teaching code** — paste it
into a fresh file, it runs on `numpy` alone in about half a minute. It implements
the full §3 pipeline end-to-end: a stripped-down return generator with the two dials
(standing in for the real simulator so the file has no project imports), the
hard-capped six-signature family (§3.4), the rank-based Mann–Whitney AUC (§3.5),
the Westfall–Young max-statistic familywise test (§3.6), and the worst-case-over-
nuisance verdict logic with the SHIP / WEAK TELL / NULL taxonomy. The confirmatory
build swaps the toy generator for `simulate_manager` via the X1 grid machinery
(§3.7) and changes nothing else — the signatures, the AUC, and the permutation test
are generator-agnostic by construction.

```python
"""S6 pre-registered returns-only signature test — self-contained teaching mock.

Question: can MONTHLY RETURNS ALONE discriminate a manager's sizing discipline
or alpha half-life? We pre-commit a small family of returns-only signatures,
measure each one's AUC as a two-class discriminator on paths with known dials,
and control the FAMILYWISE error across the pre-committed family with a
Westfall-Young max-statistic permutation test. Nothing ships unless its
worst-case AUC clears a pre-registered bar across the whole nuisance grid.
numpy only; no project imports.
"""

from __future__ import annotations

import numpy as np

# --- pre-registered constants (frozen before any run) ----------------------
AUC_MIN = 0.65            # usability bar a tell must clear to ship
FAMILYWISE_ALPHA = 0.05   # familywise error target across the family
N_PERM = 5000             # Westfall-Young permutations
DECISION_T = 60           # evaluation horizon (months)
N_PER_CLASS = 500         # managers per dial class (matches the X1 grid reps)


# --- 1. a stripped-down manager return path ---------------------------------
def simulate_returns(n, T, sizing, half_life, ic, rng):
    """(n, T) monthly net returns. Idiosyncratic noise DOMINATES; the dials
    leave only a faint fingerprint — exactly the regime the card interrogates.

    sizing in [0,1] : conviction-weight concentration. Higher -> monthly book
                      variance varies more month to month (a scale mixture).
    half_life (mo)  : alpha decay. Shorter -> the alpha mean fades early.
    ic              : signal strength; scales the alpha level.
    """
    idio_vol = 0.035                                  # 3.5%/mo noise floor
    months = np.arange(T)
    decay = 0.5 ** (months / half_life)               # (T,) decaying alpha shape
    alpha_mean = ic * 0.20 * decay                    # (T,) monthly alpha mean
    # Sizing fingerprint: concentrated conviction books have a month-to-month
    # varying effective breadth -> heteroskedastic book returns, same mean.
    base = rng.standard_normal((n, T))
    vv_shock = rng.standard_normal((n, T))
    het = 1.0 + 0.25 * sizing * vv_shock              # heteroskedastic scaler
    idio = idio_vol * het * base
    return alpha_mean[None, :] + idio


# --- 2. the pre-committed signature family (returns-only, hard-capped) ------
def sig_autocorr(r):
    """Lag-1 sample autocorrelation of monthly returns."""
    r = r - r.mean()
    return float(np.sum(r[:-1] * r[1:]) / np.sum(r * r)) if np.sum(r * r) > 0 else 0.0


def sig_vol_of_vol(r, w=6):
    """Coefficient of variation of the rolling w-month volatility."""
    rolling = np.array([r[i:i + w].std(ddof=1) for i in range(len(r) - w + 1)])
    return float(rolling.std(ddof=1) / rolling.mean()) if rolling.mean() > 0 else 0.0


def sig_skew(r):
    """Sample skewness of monthly returns."""
    z = (r - r.mean()) / r.std(ddof=1)
    return float(np.mean(z ** 3))


def sig_kurtosis(r):
    """Excess kurtosis of monthly returns."""
    z = (r - r.mean()) / r.std(ddof=1)
    return float(np.mean(z ** 4) - 3.0)


def sig_drawdown_shape(r):
    """Max drawdown normalized by the diffusive scale sigma * sqrt(T)."""
    wealth = np.cumprod(1.0 + r)
    peak = np.maximum.accumulate(wealth)
    mdd = (1.0 - wealth / peak).max()
    return float(mdd / (r.std(ddof=1) * np.sqrt(len(r)))) if r.std(ddof=1) > 0 else 0.0


def sig_rolling_ir_slope(r, w=12):
    """OLS time-slope of the rolling w-month information ratio."""
    ir = np.array([r[i:i + w].mean() / r[i:i + w].std(ddof=1)
                   for i in range(len(r) - w + 1)])
    x = np.arange(len(ir), dtype=float)
    x -= x.mean()
    return float((x @ (ir - ir.mean())) / (x @ x)) if (x @ x) > 0 else 0.0


SIGNATURES = {
    "autocorr": sig_autocorr,
    "vol_of_vol": sig_vol_of_vol,
    "skew": sig_skew,
    "kurtosis": sig_kurtosis,
    "drawdown_shape": sig_drawdown_shape,
    "rolling_ir_slope": sig_rolling_ir_slope,
}


# --- 3. AUC (Mann-Whitney) and its familywise permutation test --------------
def mann_whitney_auc(pos, neg):
    """P(signature ranks a random positive-class manager above a random
    negative-class one); ties count half. Rank form, O(n log n):
    AUC = (R_pos - n_pos(n_pos+1)/2) / (n_pos * n_neg)."""
    pos = np.asarray(pos)
    neg = np.asarray(neg)
    n_pos, n_neg = pos.size, neg.size
    allv = np.concatenate([pos, neg])
    order = allv.argsort()
    ranks = np.empty_like(order, dtype=float)
    ranks[order] = np.arange(1, len(allv) + 1)
    # Average ranks over ties (the Mann-Whitney tie convention).
    _, inverse, counts = np.unique(allv, return_inverse=True, return_counts=True)
    sums = np.zeros(len(counts))
    np.add.at(sums, inverse, ranks)
    ranks = (sums / counts)[inverse]
    u = ranks[:n_pos].sum() - n_pos * (n_pos + 1) / 2.0
    return float(u) / (n_pos * n_neg)


def familywise_maxauc_test(sig_pos, sig_neg, rng, n_perm=N_PERM):
    """Westfall-Young max-statistic familywise-adjusted p-values.

    sig_pos, sig_neg : dict signature -> per-manager values for the two dial
                       classes. Null: labels are exchangeable (all AUC = 0.5).
    Adjusted p_j = fraction of permutations whose MAX |AUC - 0.5| over the
    whole family reaches signature j's observed |AUC - 0.5|. The max statistic
    absorbs the correlation among signatures (they share one return path), so
    this is exact familywise control over a small pre-committed family —
    NOT an FDR screen over an open candidate pool.
    """
    names = list(sig_pos)
    observed = {n: mann_whitney_auc(sig_pos[n], sig_neg[n]) for n in names}
    observed_dev = {n: abs(observed[n] - 0.5) for n in names}
    combined = {n: np.concatenate([sig_pos[n], sig_neg[n]]) for n in names}
    n_pos = len(next(iter(sig_pos.values())))
    total = n_pos + len(next(iter(sig_neg.values())))
    exceed_count = {n: 0 for n in names}
    for _ in range(n_perm):
        idx = rng.permutation(total)
        pos_idx, neg_idx = idx[:n_pos], idx[n_pos:]
        max_dev = max(
            abs(mann_whitney_auc(combined[n][pos_idx], combined[n][neg_idx]) - 0.5)
            for n in names
        )
        for n in names:
            if max_dev >= observed_dev[n]:
                exceed_count[n] += 1
    adjusted_p = {n: (exceed_count[n] + 1) / (n_perm + 1) for n in names}
    return observed, adjusted_p


def signatures_for_class(n, sizing, half_life, ic, seed):
    rng = np.random.default_rng(seed)
    returns = simulate_returns(n, DECISION_T, sizing, half_life, ic, rng)
    return {name: np.array([fn(returns[i]) for i in range(n)])
            for name, fn in SIGNATURES.items()}


# --- 4. the two pre-registered contrasts across the nuisance IC grid --------
if __name__ == "__main__":
    # Toy AUC check (the section-3 worked example): 4 disciplined vs 4
    # undisciplined kurtosis values -> 15 of 16 pairs won -> AUC = 0.9375.
    toy_pos = np.array([0.9, 1.4, 0.6, 1.1])
    toy_neg = np.array([0.3, 0.8, -0.1, 0.5])
    print(f"toy AUC = {mann_whitney_auc(toy_pos, toy_neg):.4f} (15/16 = 0.9375)")

    NUISANCE_IC = (0.02, 0.04, 0.07, 0.10)
    rng = np.random.default_rng(20260707)

    def run_contrast(name, pos_kw, neg_kw):
        print(f"\n=== {name} contrast  (worst deciding cell over IC grid, T={DECISION_T}) ===")
        worst = {s: 1.0 for s in SIGNATURES}      # min AUC over nuisance cells
        worst_p = {s: 0.0 for s in SIGNATURES}    # its familywise-adjusted p
        for ic in NUISANCE_IC:
            pos = signatures_for_class(N_PER_CLASS, ic=ic, seed=int(ic * 1e6) + 1, **pos_kw)
            neg = signatures_for_class(N_PER_CLASS, ic=ic, seed=int(ic * 1e6) + 2, **neg_kw)
            observed, adjusted_p = familywise_maxauc_test(pos, neg, rng)
            for s in SIGNATURES:
                if observed[s] < worst[s]:
                    worst[s], worst_p[s] = observed[s], adjusted_p[s]
        for s in SIGNATURES:
            if worst[s] > AUC_MIN and worst_p[s] < FAMILYWISE_ALPHA:
                verdict = "SHIP"
            elif worst_p[s] < FAMILYWISE_ALPHA:
                verdict = "WEAK TELL"                # significant, below the bar
            else:
                verdict = "NULL"
            print(f"  {s:18s} worst AUC={worst[s]:.3f}  adj p={worst_p[s]:.3f}"
                  f"  -> {verdict}")

    run_contrast("SIZING (discipline 0.8 vs 0.0)",
                 pos_kw={"sizing": 0.8, "half_life": 12.0},
                 neg_kw={"sizing": 0.0, "half_life": 12.0})
    run_contrast("DECAY (half-life 3 vs 36)",
                 pos_kw={"sizing": 0.8, "half_life": 3.0},
                 neg_kw={"sizing": 0.8, "half_life": 36.0})
```

Run it and it prints (verbatim — this output was produced by executing the file
above; the toy generator's fingerprint strengths are illustrative stand-ins, so
these are **pilot** numbers demonstrating the protocol, not the card's answer):

```text
toy AUC = 0.9375 (15/16 = 0.9375)

=== SIZING (discipline 0.8 vs 0.0) contrast  (worst deciding cell over IC grid, T=60) ===
  autocorr           worst AUC=0.459  adj p=0.129  -> NULL
  vol_of_vol         worst AUC=0.574  adj p=0.001  -> WEAK TELL
  skew               worst AUC=0.496  adj p=1.000  -> NULL
  kurtosis           worst AUC=0.605  adj p=0.000  -> WEAK TELL
  drawdown_shape     worst AUC=0.474  adj p=0.621  -> NULL
  rolling_ir_slope   worst AUC=0.499  adj p=1.000  -> NULL

=== DECAY (half-life 3 vs 36) contrast  (worst deciding cell over IC grid, T=60) ===
  autocorr           worst AUC=0.456  adj p=0.084  -> NULL
  vol_of_vol         worst AUC=0.501  adj p=1.000  -> NULL
  skew               worst AUC=0.498  adj p=1.000  -> NULL
  kurtosis           worst AUC=0.463  adj p=0.223  -> NULL
  drawdown_shape     worst AUC=0.603  adj p=0.000  -> WEAK TELL
  rolling_ir_slope   worst AUC=0.551  adj p=0.032  -> WEAK TELL
```

Twelve verdicts, **zero SHIPs** — and the pattern is the whole §3 story in
miniature. Four signatures are *statistically real* (the permutation test resolves
their whisper of signal decisively — `kurtosis` at 0.605 sits ≈ 5.7 null standard
errors from blind) yet every one falls short of the 0.65 usability bar, so the ship
rule correctly refuses them. The mechanistically-declared directions mostly behave
(`kurtosis` and `vol_of_vol` up for disciplined sizing; `drawdown_shape` up for fast
decay; `autocorr` below 0.5 for fast decay, as declared, though not significant).
And one row is the pre-registration lesson made flesh: `rolling_ir_slope` under
H-DECAY is familywise-significant at 0.551 — **in the direction opposite to its
declaration** (fast decay was declared to give the *more negative* IR slope; the
paths say otherwise, plausibly because half-life-3 alpha is dead so early that the
fitted slope is flattened by the long driftless tail, while half-life-36 declines
steadily through the entire window). Under the frozen taxonomy that is a WEAK TELL
anomaly to document for a possible v2 hypothesis — not a discovery with the sign
quietly flipped.

## 5. Reading the demo

The gallery page `s6.html` is fully synthetic (§6.2 compliance) and deliberately
unusual for the gallery: its centerpiece is a *document*, not a chart.

**Panel 1 — the pre-registration document.** Rendered verbatim, dated, with its
commit hash: the two hypotheses with their direction table (§3.3–3.4), the frozen
six-signature family with exact formulas, the deciding cells and the confirmatory
seed name, the ship rule with its constants, the verdict taxonomy, and the amendment
rule. The point the page makes before showing a single number: *everything you are
about to see was committed before the run*. A "what would have happened without
this" footnote does the forking-paths arithmetic — scanning six signatures per
contrast at a naive per-test 5% false-alarms on some signature roughly 26% of the
time per cell; a vendor free to scan dozens of features and pick the winner
essentially always "finds" a tell.

**Panel 2 — the verdict grid.** Two contrast blocks (H-SIZE, H-DECAY) × six
signature rows. Each row is:

- an **IntervalStat**: the worst-deciding-cell directional AUC as the point, a 95%
  band (Hanley–McNeil SE at the observed AUC; bootstrap variant at the gate), drawn
  on a rail that marks **both** thresholds — the familywise significance floor
  (≈ 0.55 at this replication count) and the usability bar at 0.65. The gap between
  the two marks is the page's central graphic: the zone where a signature is *real
  but useless*, which is where every significant pilot row lands.
- a **VerdictChip**: SHIP / WEAK TELL / NULL per the frozen taxonomy. NULL chips get
  the same visual weight as SHIP chips — a null here is a finding, not an absence.
  The `rolling_ir_slope` × H-DECAY row carries its "direction reversed vs
  declaration" flag with the mechanism note from §4.
- the familywise-adjusted p and the deciding-cell count, always together ("adj
  p = 0.032 across 8 deciding cells"), never a bare point.

**Panel 3 — the honest headline and the sim-to-live ladder.** The pilot headline:
*"Two contrasts, six pre-committed signatures, zero shippable tells — four
statistically-real whispers, all below the usability bar."* Next to it, the
PowerGate-style refusal explains what even a SHIP would and would not mean: an AUC
of 0.65 orders a random pair correctly 2 times in 3 — for a **single** manager it
shifts the odds barely (about a 0.5-standard-deviation separation between class
distributions under a binormal read), which is why the decision hook is a
conversation prompt, never a score. A small ladder diagram shows the three
evidentiary rungs: simulator verdict (this page) → external validation on E/P-labeled
managers where truth is visible (§6.3) → any roster-facing use.

**Demo-vs-live split, stated on the page.** The demo's numbers are a **pilot**: the
protocol executed end-to-end on the stand-in generator of §4 (the demo generator
`s6_signatures.py` upgrade path runs the same signature kernels on actual
`simulate_manager` paths via the cached X1 grid reps, still labeled PILOT). The
**confirmatory run** — full simulator, overlay nuisance cells, fresh
`S6_CONFIRM_SEED` — is the card's research deliverable, and its outcome is unknown
by design; the page says so in exactly those words. Committed JSON to
`site/data/s6_signatures.json` via `_emit.write_json`; CI renders from JSON only and
never computes (demo-layer doctrine).

What an allocator should conclude from the pilot: the protocol works — it detects
real whispers, refuses to sell them, catches a direction reversal that a
non-registered analysis would have marketed as a discovery, and renders its nulls
with full standing. Whether the *simulator* verdict lands SHIP or NULL, the reader
has already seen the instrument that makes either answer trustworthy.

## 6. Honest limits & go-live

### 6.1 What S6 does not do (do-not-build adjacency)

- **No FDR luck-screen.** The do-not-build list prohibits FDR screening at roster
  scale, and S6's discipline is the stated opposite: a hard-capped, pre-committed
  family of six signatures per contrast under **familywise** (Westfall–Young)
  control. There is no open candidate pool, no discovery quota, and no tolerance for
  a fraction of false tells. The distinction is printed on the page.
- **No persistence test, no regime splits, no conditional betas.** The contrasts
  compare populations of managers at *fixed, known* dial values; nothing is split by
  market regime, nothing is estimated time-varying, and no manager's future
  performance is predicted from their past ranking.
- **No returns-based style-drift inference.** That adjacent idea carries a Noise
  verdict at 36–60 observations and stays dead. S6 tests a *different* question
  (cross-sectional trait discrimination at n = 500 per class on known truth, not
  time-series drift detection on one manager at T ≤ 60) — and its design allows the
  same Noise answer to be returned about itself.
- **No per-manager score ships from this card as specified.** Even a SHIP verdict
  produces, at most, a labeled weak-prior chip *after* the §6.3 external-validity
  rung; a WEAK TELL or NULL produces page copy and an atlas row, nothing on any
  manager's sheet.

### 6.2 Data contract per tier

S6 is the returns-tier card by construction — the R rung is the entire question.
E/P never feed the signatures; they exist solely as **truth labels for validation**.

| Tier | Inputs the card uses | Role |
| --- | --- | --- |
| **R** (the whole point) | Monthly net returns per manager (decimals, `PeriodIndex` freq `M`, house conventions); ≥ `S6_DECISION_T` months. In the confirmatory run these are simulator-emitted; in any live application they are the roster's actual return streams. | The **entire signature family** — every statistic in §3.4 is a pure function of the return series. |
| **E** | Measured gross/concentration summaries (Open Protocol-aligned) | **Validation labels only**: measured concentration is a coarse sizing-discipline truth proxy, so E-tier managers form the first external-validity panel — does the simulator-shipped tell agree with measured truth where truth is visible? Never an input to the tell. |
| **P** | Position/trade-level sizing curves (S3 machinery) and holdings-measured decay (Di Mascio–Lines–Naik-style) | The **strong validation labels**: position-tier ground truth for both traits on the transparent few. Same role — labels, not inputs. |

**Compliance (standing):** the confirmatory run is 100% simulator — zero external
data (the card's stated sequencing advantage). Any later real-data validation rung
uses managers' own returns plus their voluntarily provided E/P summaries; no
employer-internal facts in code, docs, or committed demo JSON; all demo managers
synthetic.

### 6.3 The sim-to-live gap (the card's honest ceiling)

A SHIP verdict on the simulator proves *possibility in the simulator's world*, not
truth about real managers. The generative model has one sizing mechanism and one
decay mechanism; real books have many of each, plus the confounds §3.4 names
(smoothing, overlays, leverage policy, AUM growth). The overlay nuisance cells
(§3.7) close part of that gap; the rest is closed only by the external-validity
rung: score the shipped signature on real E/P-labeled managers and measure the AUC
against measured truth. **No roster-facing use precedes that rung** — this is a
pre-commitment of the same standing as the ship rule. Conversely, a NULL verdict on
the simulator is *strong* evidence for the live world: if the fingerprint does not
survive even in a clean world where the trait is the only difference between
classes, it will not survive a dirtier one.

### 6.4 Power & validation plan

Cells contribute to the X1 atlas
([`x1-tier-power-atlas.md`](x1-tier-power-atlas.md)) as this card's rows,
following the atlas conventions (per-module RNG streams; every Monte-Carlo rate
carries its Wilson 95% interval).

Power statements, from §3.5's closed forms and the §4 pilot measurements:

- **Against a usable tell (AUC ≥ 0.65):** at 500 per class, 0.65 sits ≈ 8.2 null
  standard errors from 0.5; power ≈ 1 even after the familywise adjustment. A
  usable tell cannot slip through undetected.
- **Familywise resolution floor:** the measured critical deviation of the
  six-signature max-statistic at 500 per class is ≈ ±0.05 (pilot: deviation 0.051 →
  adj p 0.032; 0.074 → 0.001). Effects between AUC ≈ 0.55 and 0.65 are reliably
  *detected and refused* — the WEAK TELL band exists as a measured region, not a
  hypothetical.
- **Where power genuinely runs out:** effects below AUC ≈ 0.55 can land NULL by
  power rather than by absence. The published NULL statement is therefore worded as
  a bound, not an absolute: "no signature reaches AUC 0.55 across the deciding
  cells" — which is precisely enough to kill any practical use.

Acceptance gates for the confirmatory run:

1. **Size (the load-bearing gate).** On null contrasts — two populations at
   *identical* dials, different seeds — every signature's familywise rejection rate
   is ≤ α within the Wilson interval, per contrast family. A miscalibrated
   permutation harness invalidates everything downstream; this gate runs first.
2. **Toy-recovery (positive control).** On a planted-fingerprint generator (the §4
   toy with its fingerprint strength turned up), the harness must SHIP the planted
   signature. A protocol that cannot detect a planted effect proves nothing when it
   returns NULL on the real question.
3. **The registered run itself.** Execute the frozen protocol at `S6_CONFIRM_SEED`;
   record all 12 + 8 deciding-cell verdict rows; publish the verdict grid
   as-registered, whatever it says.
4. **Nuisance-overlay stress.** Re-score any SHIP or WEAK TELL row on the
   smoothing- and written-put-overlay cells; a SHIP that fails under overlays is
   downgraded to WEAK TELL with the failing overlay named.

**Simulator dependency (honest).** The contrast and nuisance dials
(`sizing_discipline`, `alpha_half_life_months`, `information_coefficient`) all
exist. The **return-smoothing overlay does not** and is this card's one named
simulator prerequisite (small; the `overlays.py` pure-function pattern; gate 4).

### 6.5 Kill criteria

- **Statistical (pre-registered).** The grid completes and decides; the card is
  killed *as a proxy product* the moment the confirmatory run returns no SHIP — and
  the null is published with full standing, per the card ("kill after the
  pre-registered grid completes, publish the answer either way"). No sub-bar tell
  ships regardless of its p-value; no post-hoc family extension rescues a null
  (amendment rule, §3.2).
- **Protocol integrity.** If the registration is broken — a peeked seed, a
  re-windowed signature after first look, a threshold moved — the run is void and
  restarts as v2 with fresh seeds. A "positive" from a broken registration is worth
  less than no result.
- **Political.** A WEAK TELL published as a finding must never be marketed or
  consumed as a manager screen; if any consumer wires a WEAK TELL (or an
  unvalidated SHIP) into selection or monitoring workflow, the page copy is pulled
  and rewritten. The Goodhart case is acute here: a published returns-only tell
  invites managers to manage the *signature*, which is another reason the ship bar
  is high and the external-validity rung is mandatory.

### 6.6 How it ships in the repo

The commitment is **reuse the X1 harness; add only kernels, a test layer, and a
document.**

- **New module `src/quant_allocator/demo_data/s6_signatures_kernels.py`** (name
  final at the gate): the six signature functions in the `x_metrics.py` style —
  pure functions of a return array, no simulation, no I/O. The frozen family lives
  here, one function per row of §3.4's table.
- **New module `src/quant_allocator/demo_data/s6_protocol.py`**: the Mann–Whitney
  AUC, the Westfall–Young familywise test, the directional ship rule, and the
  verdict taxonomy — pure functions over per-class signature arrays. Consumes the
  X1 grid's cached per-rep return arrays (`run_config` reps) for the pilot; runs
  fresh `simulate_manager` paths at `S6_CONFIRM_SEED` for the confirmatory run,
  reusing `x_grid._config_seed`'s `SeedSequence` convention verbatim.
- **The registration document** `docs/ideas/s6-preregistration.md`: the §3.2 freeze
  list instantiated with final constants, committed before the confirmatory run;
  the demo page renders it.
- **Simulator extension (prerequisite):** the GLM-style smoothing overlay in
  `src/quant_allocator/simulator/overlays.py`, mirroring `WrittenPutOverlay`'s
  contract (pure, deterministic, RNG-free, identity at zero parameters).
- **Demo — `src/quant_allocator/demo_data/s6_signatures.py`**: runs the protocol
  end-to-end on simulator paths (pilot seed), emits committed JSON to
  `site/data/s6_signatures.json` via `_emit.write_json`; CI renders only.
- **Substrate consumed:** the simulator (`manager.py` dials; `overlays.py` incl.
  the new smoothing overlay), the X1 grid machinery (`x_grid.py` configs, seeding,
  rep cache, Wilson helper; `x_metrics.py` as the kernel pattern), and the X1 atlas
  as the destination for the cells. **Not consumed:** S1 shrinkage, the S2
  pipeline, M3 alarms, P3 aggregates — S6 is a hypothesis test on populations, not
  a per-manager estimator, and it borrows no posterior machinery.
- **Effort:** **M–L** (card estimate) — research risk, not build risk: the kernels
  and test layer are days; the runs, the overlay stress, and the write-up either
  way are the substance.

### 6.7 Adoption & packaging

The framing is load-bearing and asymmetric by outcome:

- **If NULL (the expected case):** the page becomes standing reference material —
  *"we tested six candidate returns-only tells under a pre-registered protocol;
  none survive; do not trust anyone selling this."* It is cited in E1 transparency
  conversations as the measured cost of returns-only reporting, and it hardens the
  allocator against vendor claims. The null is marketed exactly as hard as a
  discovery would have been.
- **If SHIP:** the tell enters a probation lane — external validation on E/P-labeled
  managers (§6.3) before any roster surface; then, at most, a labeled chip on the
  S2 sheet ("returns pattern consistent with X — simulator-validated, externally
  validated on N managers; a question for the meeting, not a score"), with its AUC
  and both validation rungs cited on hover. Never a ranking input, never a
  standalone screen.
- **WEAK TELLs** are published in the atlas row and the page's finding list, with
  the explicit label "statistically real, unusable at this strength" — the honest
  middle that both vendors and naive skeptics erase.

**Who sees what, when:** the investment team sees the verdict page once per
protocol version (this is review-cadence research material, not a standing
monitor — no dashboard); the E1 ladder cites the null verdicts in engagement
conversations; leadership sees the one-line outcome in the program review.

### 6.8 Go-live requirements (demo-page box, expanded)

- **Data ask:** none external — the confirmatory run is 100% simulator (tier R by
  construction). The optional external-validity rung later needs E/P summaries for
  a handful of transparent managers as labels.
- **Sample required:** the protocol runs at the X1 grid's replication scale
  (500 managers per class per cell); a *live* application of any shipped tell reads
  one manager against a population and is honest only as a weak prior nudge —
  stated on the page with the §5 single-manager odds arithmetic.
- **Build effort:** M–L — kernels and test layer small; the runs, the smoothing
  overlay, and the publish-either-way write-up are the work. Sequenced **after X1
  vol. 1** (reuses its harness and, for the pilot, its cell cache).
- **Go-live box (demo page):** data ask = none (simulator); sample = the
  pre-registered grid; effort = M–L; deliverable = the verdict, published either
  way.

**Provisional constants (all NUMERICS-GATE):** `S6_AUC_MIN` = 0.65 ·
`S6_FAMILYWISE_ALPHA` = 0.05 · `S6_N_PERM` = 5,000 · `S6_N_PER_CLASS` = 500 ·
`S6_DECISION_T` = 60 (T = 36 secondary) · `S6_ROLLING_WINDOWS` = (6, 12) ·
`S6_NUISANCE_OVERLAYS` (smoothing θ grid; written-put κ grid) · `S6_CONFIRM_SEED`
(drawn and committed at registration, before the run) · the direction table of
§3.4 (frozen at the gate with the family).

## 7. Deeper reading

**Canonical references (read in this order):**

1. **Nosek, Ebersole, DeHaven & Mellor (2018), "The Preregistration Revolution,"
   *PNAS*.** Why committing hypotheses, analyses, and decision rules before seeing
   data converts postdiction into prediction — and why that is what makes a null
   result publishable. The card's methodological charter.
2. **Westfall & Young (1993), *Resampling-Based Multiple Testing*.** Familywise
   control by permuting the max statistic over a family of correlated tests —
   exact under exchangeability, adaptive to the tests' correlation, and the
   principled small-family alternative to both Bonferroni (too conservative here)
   and FDR (the wrong error rate here).
3. **Hanley & McNeil (1982), "The Meaning and Use of the Area under a ROC Curve,"
   *Radiology*.** AUC = Mann–Whitney = P(correctly ordering a random cross-class
   pair), plus its standard errors — the identity that makes "AUC > 0.65" a
   threshold-free, rank-based target.
4. **Getmansky, Lo & Makarov (2004), *JFE*.** Serial correlation in fund returns is
   mostly smoothed marks, not alpha dynamics — the confound that disciplines the
   `autocorr` signature and forces the smoothing overlay onto the nuisance grid.
5. **Di Mascio, Lines & Naik (2017), "Alpha Decay" (working paper).** Alpha decay
   measured properly, from institutional trading records — the P-tier ground truth
   this card asks whether monthly returns can shadow, and the template for
   validating a shipped tell externally.

**Questions you should be able to answer after reading this page:**

- **State the two hypotheses and why the burden of proof sits on the card.** What
  the nearest analogue's Noise verdict implies, why staggered rebalancing smears
  the decay fingerprint at book level, and why the honest prior is mostly-null.
- **Compute a small AUC by hand.** Reproduce the 15/16 = 0.9375 toy example, state
  the Mann–Whitney identity, and explain why rank-invariance removes a forking
  path (no raw-statistic threshold to choose).
- **Explain familywise vs FDR to a non-statistician, in this card's terms.** Six
  pre-committed signatures at naive 5% each false-alarm on *something* ~26% of the
  time; Westfall–Young replays the whole scan on relabeled data and asks whether
  the observed deviation beats the null *max*; FDR answers a different question
  (what fraction of my many discoveries are false?) that is both prohibited here
  and wrong for a product where one false tell is fatal.
- **Defend the two-threshold honesty.** Why "significant" (a statement about
  n = 500 per class resolving AUC ≈ 0.55) and "usable" (0.65 across the worst
  nuisance cell) are different claims, why the pilot's four WEAK TELLs land exactly
  in the gap, and why publishing that gap is the card's central product.
- **Explain the direction rule with the pilot's own anomaly.** Why
  `rolling_ir_slope` coming out significant *opposite* to its declared direction is
  not a discovery with a sign flip — and give the mechanistic post-hoc story (the
  long dead tail flattens the fast-decay slope) plus what would be required to
  promote it (a v2 registration with a fresh seed).
- **State what even a SHIP would not mean.** AUC 0.65 orders a random *pair* right
  2 times in 3; applied to a single manager it is a whisper (≈ 0.5 sd of class
  separation), which is why the decision hook is a conversation prompt after
  external validation — never a score, never a screen.
- **Explain the seed-hygiene rule.** Why the confirmatory run must use a fresh,
  pre-committed seed that no pilot has touched, what leaks if it doesn't, and why
  the repo's commit history is the timestamping authority.

## 8. Method-review gate rulings (2026-07-07)

1. **The family, the direction table, and the windows are frozen as printed
   in §3.4** — six signatures, `S6_ROLLING_WINDOWS` = (6, 12), no re-set. Any
   later change is a version-2 protocol under the amendment rule.
2. **`S6_NUISANCE_OVERLAYS` set (provisional pending registration):** the
   smoothing-overlay stress grid is θ ∈ {identity, (0.60, 0.25, 0.15)} — a
   moderate GLM-style MA(2) profile inside the Getmansky–Lo–Makarov reported
   range, in the **same θ parameterization as the S2 unsmoothing stage** so
   the overlay and the house de-smoother are convention-inverses; the
   written-put stress cell uses the M2 demo's certified `WrittenPutOverlay`
   setting. Final values are re-stated in the registration document before
   the confirmatory seed is drawn.
3. **AUC interval convention:** Hanley–McNeil SE at the observed AUC for the
   page bands, with a bootstrap cross-check at the numerics gate.
4. **Cache and seed hygiene:** the pilot may reuse cached X1 grid reps; the
   confirmatory run takes **no cache** and runs at `S6_CONFIRM_SEED`, which is
   drawn and committed in `docs/ideas/s6-preregistration.md` at registration
   time (wave-3 scope — not now). The demo ships PILOT-labeled, and the demo
   JSON's verdicts come from the protocol run on actual `simulate_manager`
   paths at a pilot seed; §4's stand-in-generator numbers are the spec's
   teaching exhibit only and must not appear as the page's verdict grid.
5. **Constants confirmed:** `S6_AUC_MIN` = 0.65, `S6_FAMILYWISE_ALPHA` = 0.05,
   `S6_N_PERM` = 5,000, `S6_N_PER_CLASS` = 500, `S6_DECISION_T` = 60 (T = 36
   secondary, never deciding).
6. **The smoothing overlay is approved as batch-2 shared substrate**
   (`overlays.py` pure-function pattern: deterministic, RNG-free, identity at
   zero parameters, dial-guard test mandatory).
