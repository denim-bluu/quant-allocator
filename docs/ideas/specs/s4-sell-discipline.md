# S4 · Sell-Discipline Diagnostic ("Where the Edge Leaks") — Method Spec

**Status: Reviewed — method gate passed 2026-07-07 (rulings in §8)**
**Date:** 2026-07-07
**Card:** [`docs/ideas/2026-07-05-idea-cards.md`](../2026-07-05-idea-cards.md) § S4
**Demo:** gallery page `s4.html` (two-manager exit split + forgone-alpha curve; fully synthetic, §5)

---

## 1. What this is

S4 measures the quality of a manager's **sell decisions** — separately from the
quality of their buys. For every realized exit in a position-transparent book it
asks one question: *did the name you chose to sell go on to do better or worse
than the names you chose to keep?* The benchmark is deliberately humble: a
**random-sell counterfactual** — a ghost manager who, at the same moment, with
the same book, sells a position chosen at random. If a manager's actual sells
systematically underperform even that coin-flipping ghost, the manager is
destroying value at the exit specifically, no matter how good the entries are.
This is the best-documented professional-investor deficit in the literature
(Akepanidtaworn, Di Mascio, Imas & Schmidt, *Selling Fast and Buying Slow* —
§3.9), and it is measurable, coachable, and not an attack on anyone's thesis
work.

The output is a **counterfactual gap**: the average forward alpha of the sold
names minus the forward alpha of the book they were sold out of, over a stated
post-exit window, delivered as an IntervalStat with a block-bootstrap band —
never a bare point. Alongside it, a **forgone-alpha curve** shows *when* the
leak accrues ("the names you sell keep beating your book for four months"), and
a trend strip shows whether the discipline is improving or deteriorating —
gated, because a quarter of exits is usually too few to say anything.

The consumers are **manager-facing engagement** (primary — this is the purest
PM-coaching artifact in the portfolio, and it ships only inside the E1
transparency-ladder relationship) and the **investment team watchlist**
(a decision-quality trend that leads returns). The decisions it improves are
**engage** — the highest-value, least-threatening feedback an allocator can
bring to a manager conversation — and **monitor**. Deterioration plus a refusal
to engage is a *soft* redemption input routed to a human; it is never a
mechanical rule.

## 2. Why we use it

An allocator watching a transparent book has no vocabulary for exit quality.
The tear sheet shows the blended result of entries, sizing, holding, and exits;
a bad quarter gets attributed to "the longs didn't work," and the one
consistently fixable behavior in the book — selling the wrong names — stays
invisible because nobody computes the counterfactual. The naive alternatives
all fail in instructive ways. *"Did the stock go up after you sold?"* confounds
exit skill with market direction: in a rising market every sell looks like a
mistake. *"Compare sold names to the index"* confounds it with the manager's
factor tilts and universe. The SFBS design fixes both at once: the
counterfactual sells **from the same book at the same moment**, so market
direction, factor exposure, and universe cancel by construction, and what is
left is pure *selection* skill at the exit — did you pick the right name to
kill?

The empirical warrant is unusually strong. Akepanidtaworn et al. studied
institutional PMs (portfolios averaging ~$570m) and found genuine skill in
buying alongside selling that **underperforms the random-sell benchmark** —
buys are slow, researched decisions; sells are fast, heuristic reactions to
extreme past returns. The deficit concentrates exactly where behavioral theory
predicts: disposition-style selling (realize the winners, ride the losers —
Shefrin & Statman, Odean, §3.9) throws away names whose edge has not finished
paying. Because the deficit is concentrated, visible, and orthogonal to the
manager's idea generation, it is the ideal engagement opener (Sweep E): telling
a PM "your buys add value and your exits give a third of it back" is help, not
audit — provided the framing rules of §6.6 hold.

- **Decisions improved:** **engage** — a coachable, quantified deficit with the
  uncertainty stated, delivered inside the E1 ladder; **monitor** — a
  per-manager decision-quality trend with honest gates.
- **Customer:** manager-facing engagement (primary); investment team watchlist.

What S4 wins over doing nothing: the single decision-quality number the
platform world (Essentia-class, Sweep B/D) sells to managers, rebuilt on the
allocator's side of the table, power-gated, and interval-honest.

## 3. How it works

### 3.1 The mental model, before any math

Freeze a manager's book at the moment of a sale. Forty names; the manager sells
one. A ghost manager standing in the same room sells one too — but picks it by
lottery. Both books then run forward untouched for a few months. If the
manager's sells are *skilled*, the names they kill should go on to do **worse**
than the book average — the manager is culling spent ideas, and beats the
ghost. If the sells are *flawed* in the disposition style — selling whatever
has run up the most, because banking a win feels like closure — the manager
systematically kills names whose edge is still paying, and the sold names go on
to **beat** the book they were thrown out of. The ghost, who at least kills at
random, does better.

Averaging that comparison over hundreds of exits is the whole diagnostic. One
subtlety does real work: the ghost's expected pick is just the **equal-weighted
average of the names the manager could have sold** — so we never need to
actually draw random names; the counterfactual has a closed form (the book-mean
forward return), which removes lottery noise from the estimate. This is
precisely the SFBS benchmark.

The second half of the mental model is a warning, and it is the deepest finding
in this spec: **an exit decision can only leak alpha that the world lets it
carry forward.** If a name's future excess return is unpredictable at the
moment of the sale — no momentum in the manager's edge, no persistence in the
idiosyncratic return — then *every* exit rule, brilliant or idiotic, produces a
zero gap: there is nothing forward-looking to throw away. The diagnostic
measures the *interaction* of exit behavior with forward-predictable alpha.
This is verified, not asserted, in §3.8 and §4 — and it dictates the simulator
extension the demo needs.

### 3.2 A worked toy example

A book holds four names, A–D, at 25% each. At the end of June the manager sells
**D**. Over the next two months the **factor-adjusted** (residual) returns
cumulate to:

| Name | Status at sale | Forward 2-month residual return |
| --- | --- | --- |
| D | **sold** | **+3.0%** |
| A | kept | +1.0% |
| B | kept | 0.0% |
| C | kept | −1.0% |

The counterfactual pool is the book the sale was chosen from: {A, B, C, D}. The
ghost's expected forward return is the mean of the names *other than* the one
actually sold — (+1.0 + 0.0 − 1.0)/3 = **0.0%**. The gap for this exit is

$$g_1 = (+3.0\%) - (0.0\%) = +3.0\ \text{pp}.$$

Read it in words: the name the manager chose to kill went on to beat the
average name they kept by 3 points in two months. A random sell would have done
better. That is a leak.

Now a second exit: at the end of August the manager sells **B**, and over
September–October the residuals cumulate to B −1.5%, while the kept names
(A, C, and a new position E) average +0.5%. The gap is
$g_2 = -1.5\% - 0.5\% = -2.0$ pp — this time the sold name underperformed what
was kept: a *good* sell. The **counterfactual gap** over the two exits is the
average,

$$\widehat{CG} = \tfrac{1}{2}(+3.0 - 2.0) = +0.5\ \text{pp},$$

with a sign convention worth memorizing: **positive gap = the sold names beat
the book = the exits leak; negative gap = the exits cull well; zero = the
manager sells no better and no worse than the lottery.** Two exits prove
nothing — the whole of §3.6 and §6.3 is about how many exits it takes before
this average means anything.

### 3.3 Exit events and the counterfactual gap

Let a position-transparent history give the holdings set $B_t$ (the names held
during month $t$) and an exit event $e = (\tau_e, j_e)$: name $j_e$'s last held
month is $\tau_e$; from month $\tau_e + 1$ it is out of the book. For a forward
window of $H$ months, define for each exit

$$
G_e \;=\; \sum_{h=1}^{H} a_{j_e,\,\tau_e+h}
\;-\; \frac{1}{|P_e|} \sum_{k \in P_e} \sum_{h=1}^{H} a_{k,\,\tau_e+h},
\qquad
\widehat{CG}(H) \;=\; \frac{1}{n}\sum_{e=1}^{n} G_e .
$$

where:

- $a_{i,t}$ — name $i$'s **factor-adjusted** (residual) return in month $t$: the
  return left after removing factor exposure (§3.4). Decimal units.
- $\tau_e$ — the exit month of event $e$: the last month the sold name is in the
  book. The sale is decided on month-$\tau_e$ information; month $\tau_e$ itself
  belongs to neither leg (it is the execution month), so the forward window is
  $\tau_e+1, \dots, \tau_e+H$ for **both** legs — the comparison is
  contemporaneous by construction.
- $j_e$ — the name actually sold.
- $P_e$ — the **counterfactual pool**: the names eligible to have been sold
  instead — the book carried *into* the exit month, minus the sold name itself,
  $P_e = B_{\tau_e - 1} \setminus \{j_e\}$. Freshly bought names of month
  $\tau_e$ are **excluded**: the ghost chooses among the incumbents the manager
  was actually choosing among, not among the just-added hot picks (including
  them mechanically biases the pool upward — a bug we hit and fixed in the
  reference mock, §4).
- $H$ — the forgone-alpha horizon in months
  (**`S4_HORIZON_MONTHS` = 4, provisional — NUMERICS-GATE**; the curve of §3.5
  renders every horizon $1..H$ so the choice is visible, not hidden).
- $G_e$ — the per-exit gap: sold name's cumulative forward residual minus the
  equal-weighted pool's. The second term **is** the random-sell counterfactual:
  a uniform draw from $P_e$ has expected forward return equal to the pool mean,
  so using the mean is the zero-variance version of actually drawing lotteries.
- $n$ — the number of exits with a full $H$-month forward window.
- $\widehat{CG}(H)$ — the counterfactual gap: the average leak per exit,
  in return units of the sold position (i.e., per unit of position weight).

In words: for every sale, score how the killed name did against the average
survivor over the next $H$ months, then average the scores. Under the null
hypothesis of **no exit-selection skill** — the sold name is exchangeable with
the pool at the moment of sale — every $G_e$ has expectation zero, so
$\widehat{CG}$ is a calibrated zero-centered statistic; no simulation is needed
to locate its null center, only its width (§3.6).

Equal weighting of the pool (rather than position weighting) matches the
uniform random-sell ghost of SFBS; a position-weighted variant answers a
different question ("what did the *capital* you kept do") and is flagged
**`S4_POOL_WEIGHTING` (provisional — equal-weight, the SFBS convention)** for
the gate.

### 3.4 What "alpha" means here — the factor adjustment

Raw forward returns will not do: exits cluster in time, and a market rally
after a wave of sells would smear direction into every gap even though both
legs share it. The shared-month construction removes the *common* component
exactly ($G_e$ differences two same-month returns), but only insofar as the
sold name and the pool have the **same factor exposure**. They generally do not
(the sold name has one beta; the pool has the average), so both legs use
**residual returns**:

$$
a_{i,t} = r_{i,t} - \hat\beta_i^\top f_t ,
$$

where $r_{i,t}$ is the name's total return, $f_t$ the factor-return vector that
month, and $\hat\beta_i$ the name's estimated loadings. At the P tier the betas
come from a bought security-level risk model or a simple factor regression —
the convergence decision's buy-verdict (Barra/Axioma-class models are **bought,
not built**; §6.1) applies in full. In the demo, residuals are the simulator's
ground-truth idiosyncratic returns — zero estimation error, and the
demo-vs-live split is stated on the page (§5).

The remaining assumption is mild and stated: residuals are mean-zero and
serially exchangeable **under the null**; no distributional form is imposed
beyond what the bootstrap resamples. What the diagnostic *estimates* — forward
persistence in residuals interacted with exit selection — is exactly what it
is supposed to detect, so persistence under the alternative is a feature, not
a violation.

### 3.5 The forgone-alpha curve

The scalar $\widehat{CG}(H)$ says *whether* the exits leak; the curve says
*when*, and the "when" is what a PM can act on. Define, for each forward month
$h \le H$,

$$
C(h) \;=\; \frac{1}{n} \sum_{e=1}^{n} \left[
\sum_{u=1}^{h} a_{j_e,\,\tau_e+u}
- \frac{1}{|P_e|}\sum_{k \in P_e} \sum_{u=1}^{h} a_{k,\,\tau_e+u} \right],
$$

where $C(h)$ is simply $\widehat{CG}(h)$ rendered at every horizon up to $H$ —
the **cumulative average out-performance of the sold names over the kept book,
month by month after the exit**. A rising curve that plateaus at month 3 reads:
"the names you sell keep beating your book for about three months, then the
edge you threw away is spent." That sentence — with its interval — is the
engagement artifact. The curve is the monthly cousin of the card's daily
wow-line ("your alpha accrues for 60 trading days and you give a third back
after day 90"); at monthly resolution the demo's disposition manager plateaus
at three-to-four months (§5). The full entry-to-exit alpha path (how much the
position earned *before* the sale) is S3's entry-aligned event study; S4 owns
the post-exit leg, and the two curves share one clustered event-study kernel
(§6.5).

### 3.6 Uncertainty — the month-cohort block bootstrap

Exits are not independent: the six names sold in the same month share the same
forward market months, and their gaps share the same pool leg. Treating $n$
exits as $n$ independent observations overstates precision, and the house
already owns the fix — **P3's cohort block bootstrap**
(`flagships/decision_audit/aggregate.py`, `cohort_block_bootstrap`): resample
whole **calendar-month cohorts** of exits with replacement, recompute
$\widehat{CG}$ per resample, and report the standard deviation and the 5th–95th
percentile band. The block is the month; if the leak is concentrated in a few
months, the band widens honestly.

$$
\text{deff} = 1 + (\bar m - 1)\,\rho_c ,
$$

where:

- $\bar m$ — the average number of exits per month-cohort (≈ 6 in the demo
  world).
- $\rho_c$ — the intra-cohort correlation of gaps (same-month exits share
  forward months and the pool leg).
- $\text{deff}$ — Kish's design effect, the variance inflation (or deflation)
  relative to an iid treatment of the $n$ gaps. Printed beside the interval,
  exactly as P3 prints it.

An honest measurement from the reference mock (§4): in the demo world the
measured deff is **0.68–0.92** — *below* one — because a selective exit rule
sells "the worst six" (or "the biggest six winners") every month, which
**stratifies** the month cohorts and makes month-mean gaps *more* stable than iid
sampling implies, while the synthetic market has no common shock in residuals.
On live books, imperfect residualization leaves common factor months in the
gaps and pushes deff **above** one. The block bootstrap is kept precisely
because it adapts honestly in both directions; a hard-coded iid se would be
wrong in a direction that varies by book. Same-name repeated round trips
(sell, re-buy, re-sell) create a second, cross-month clustering dimension;
v1 clusters on the month only (the dominant axis at monthly cadence), and
two-way month × name clustering is flagged
**`S4_TWOWAY_CLUSTER` (provisional — month-only in v1)** for the gate.
Bootstrap replications: **`S4_BOOTSTRAP_REPS` = 2,000 (provisional — reuses
P3's `BOOTSTRAP_REPS` convention)**.

### 3.7 The trend, the roster view — and what S4 is *not*

**Trend.** The engagement story wants "is the discipline improving?": bucket
exits by period, render $\widehat{CG}$ per bucket with its band. The honest
catch is sample arithmetic — at ~18 exits per quarter the per-bucket standard
error in the demo world is ≈ 290 bp, several times any plausible effect, so a
quarterly trend is astrology. The trend strip therefore **refuses buckets below
`S4_MIN_EXITS_BUCKET` (provisional — 60 exits) and falls back to yearly or
pooled rendering**; the demo shows the refusal (§5). The trend is a
*descriptive* series of a decision-quality metric within one manager, always
with intervals — it is **not** a persistence test of alpha (do-not-build list),
makes no claim that past $\widehat{CG}$ predicts future returns, and never
ranks managers by trend.

**Roster.** Where several position-transparent managers exist, per-manager gaps
are shrunk toward the transparent-roster mean with the house small-N machinery —
S1's closed-form empirical-Bayes shrinkage
(`flagships/skill_ledger/empirical.py`, `shrink_alphas`), applied to
$\widehat{CG}$ estimates with their bootstrap standard errors. A manager with 80
exits borrows strength from peers exactly as a short-track alpha does. This is a
decision-quality measurement pooled for stability — **not** an FDR luck-screen
on alphas (do-not-build list); no discovery test is run across the roster.

**Adjacency statement (binding).** S4 runs no regime splits, no conditional or
time-varying betas, and no returns-based style inference. The gap is a
within-manager, event-level measurement at the P tier, and at the R tier the
card refuses rather than infer exits from returns (§6.1).

### 3.8 The structural null — why the current simulator cannot leak, and the dials the demo needs

The §3.1 warning made precise. In the current simulator
(`simulator/market.py`), idiosyncratic returns are drawn **independently across
months** — name-level residuals have no persistence. At the moment of any sale,
every name's forward residual is mean-zero regardless of anything the manager
knows or does; hence for *any* exit rule,

$$
\mathbb{E}[G_e] = 0 \quad \text{whenever } a_{i,t} \perp \mathcal{F}_{\tau_e},
$$

where $\mathcal{F}_{\tau_e}$ is everything observable at the exit month. The
reference mock (§4) verifies this: at $\rho = 0$, a disciplined, a random, and
a deliberately disposition-flawed manager all produce
$\widehat{CG} \approx 0$ (+3, −10, +13 bp across 40 seeded worlds — every one
statistically zero, false-positive rate 8–12% at a nominal 10%). Two design
consequences, one honest and one practical:

- **The honest one:** the current simulator is a free *specificity* world — a
  world where the true answer is "no leak is even possible," on which the
  diagnostic must stay silent. It does (§6.3 gate 1 pins this).
- **The practical one:** the card's MVP hope — "short alpha half-life +
  sluggish rebalancing exhibit hold-too-long leakage organically; add an
  exit-lag dial if not" — is answered **negative, with a sharper diagnosis**.
  Hold-too-long behavior *does* cost the simulated manager return (aged
  positions carry no signal — that loss lives in S3's holding-period curves),
  but it **cannot** show up in a post-exit counterfactual, because after the
  sale there is nothing predictable left to forgo. And no *manager-side* dial
  alone can fix this — an exit-lag or disposition dial in an iid world still
  produces a zero gap (verified, §4). The world itself must carry forward
  alpha.

**Named validation prerequisite — the S4 simulator extension (two dials).**
Precedents: M3's `death_month` and M1's `net_drift`, both opt-in,
default-byte-identical dials on `ManagerConfig`.

1. **Market persistence dial** — `MarketConfig.idio_ar1: float = 0.0`
   (`simulator/market.py`): idiosyncratic returns become AR(1),
   $a_{i,t} = \rho\, a_{i,t-1} + \sqrt{1-\rho^2}\,\sigma_i\,\varepsilon_{i,t}$,
   stationary marginal variance preserved so $\rho = 0$ is the current
   generator **byte-identical**. Demo setting
   **`S4_IDIO_AR1_DEMO` = 0.4 (provisional — NUMERICS-GATE)**. Because a
   persistent-idio world also makes the manager's *signal* forward-predictive,
   the dial is opt-in per cell and OFF everywhere outside S4's atlas rows.
2. **Exit-style dial** — `ManagerConfig.exit_style: "age" | "signal" |
   "disposition" = "age"` (`simulator/manager.py`): `"age"` is the current
   oldest-first replacement (byte-identical default; under persistence it is
   approximately exchangeable with the pool → gap ≈ 0);
   `"signal"` sells the lowest-refreshed-signal incumbents (the disciplined
   manager — negative gap under persistence); `"disposition"` sells the
   incumbents with the largest trailing
   **`S4_DISPOSITION_TRAIL_MONTHS` = 3 (provisional)** gain — Shefrin–Statman
   selling made mechanical (positive gap under persistence).

With both dials the demo has ground truth in every direction: disciplined
$\widehat{CG} = -163$ bp (interval excludes zero in 90% of worlds), random
$+8$ bp (15% — consistent with the nominal 10%; Wilson 95% interval [7%, 29%]
at 40 worlds), disposition $+365$ bp (100%) — §4's executed numbers.

### 3.9 What the canonical papers contribute

- **Akepanidtaworn, Di Mascio, Imas & Schmidt (2023), "Selling Fast and Buying
  Slow" (*Journal of Finance*; working paper circulated 2018–2021).** The
  finding and the design. Institutional PMs show buy skill but sell *below* a
  random-sell counterfactual drawn from their own book at the same moment;
  the deficit concentrates in heuristic, extreme-past-return-driven sells and
  *disappears on earnings-announcement days* (when attention is forced onto
  the sold name) — the signature of an attention deficit, not an information
  deficit, and therefore coachable. S4 is this paper's design operationalized
  for an allocator.
- **Shefrin & Statman (1985) and Odean (1998), both *Journal of Finance*.**
  The disposition effect: investors realize winners and ride losers. Odean's
  discount-brokerage evidence made it quantitative — and showed the sold
  winners went on to *outperform* the held losers, the exact positive-gap
  pattern S4's flawed demo manager exhibits. This is the behavioral mechanism
  the `"disposition"` exit dial implements.
- **Frazzini (2006, *Journal of Finance*).** Disposition-driven selling
  interacts with post-news drift: under-reaction makes residual returns
  persist, which is precisely the channel through which selling a winner
  forgoes future alpha. This paper is why the simulator extension is an
  *idio-persistence* dial — persistence is the physical carrier of the leak
  (§3.8), not an incidental nuisance parameter.
- **Künsch (1989, *Annals of Statistics*).** The block bootstrap: resampling
  dependent data in blocks preserves the dependence within them. S4's
  month-cohort resampling (via P3's implementation) is the cluster/block
  variant; Kish (1965) supplies the design-effect diagnostic printed beside
  the band.

## 4. How to implement

The reference implementation below is **self-contained teaching code** — paste
it into a fresh file; it runs on `numpy` alone, uses no project imports and no
repo paths, and is deterministic (fixed integer RNG stream tags — a plain
`hash()` here is process-randomized and silently breaks reproducibility, a bug
this mock had once and now warns about). It implements §3.3's gap with the
incumbent-pool convention, §3.5's curve, §3.6's month-block bootstrap, and
§3.8's two worlds × three exit rules. Runtime ≈ 2 minutes.

```python
"""S4 sell-discipline diagnostic — self-contained teaching code (numpy only).

Reproduces the method spec's worked numbers:
  - IID idio (rho=0, the current simulator's world): the counterfactual gap is
    statistically zero for EVERY exit rule -- there is no forward alpha to leak.
  - Persistent idio (rho=0.4): a disciplined exit shows a negative gap (good), a
    random exit shows ~zero (the counterfactual baseline), and a disposition exit
    ("sell your winners") shows a large positive gap -- the SFBS deficit.
"""
import numpy as np


def simulate_market(n_assets, n_months, rho, idio_vol, rng):
    """One-factor market with AR(1) idiosyncratic returns.

    idio_t = rho * idio_{t-1} + sqrt(1 - rho**2) * idio_vol * eps.
    rho = 0 recovers IID idio (the current simulator); rho > 0 makes a name's
    edge persist forward, which is what an exit decision can leak.
    """
    idio = np.empty((n_months, n_assets))
    innov = np.sqrt(1.0 - rho ** 2)
    prev = rng.normal(0.0, idio_vol, size=n_assets)          # stationary start
    for t in range(n_months):
        eps = rng.normal(0.0, idio_vol, size=n_assets)
        idio[t] = rho * prev + innov * eps
        prev = idio[t]
    return idio


def simulate_manager(idio, k_hold, n_replace, ic, exit_rule, rng, trail=3):
    """Hold k_hold names, replace n_replace each month. Buys pick the highest
    signal; the exit rule chooses which incumbents to sell.

    signal_t = ic * z_t + sqrt(1-ic**2) * noise, z = standardized idio state.
    Because idio persists, signal_t predicts FORWARD idio -- so an exit rule that
    is decoupled from the signal leaks forward alpha.

    exit_rule:
      "disciplined" -> sell lowest-signal incumbents (spent edge).
      "disposition" -> sell largest trailing-gain incumbents (realize winners).
      "random"      -> sell a random incumbent (the counterfactual itself).
    """
    n_months, n_assets = idio.shape
    z = idio / idio.std()
    noise = rng.standard_normal((n_months, n_assets))
    signal = ic * z + np.sqrt(1.0 - ic ** 2) * noise
    cum = np.cumsum(idio, axis=0)

    held = list(np.argsort(signal[0])[-k_hold:])
    holdings = [set(held)]
    exits = []
    for t in range(1, n_months):
        incumbents = np.array(held)
        if exit_rule == "disciplined":
            order = np.argsort(signal[t, incumbents])            # lowest signal first
        elif exit_rule == "disposition":
            gain = cum[t, incumbents] - cum[max(t - trail, 0), incumbents]
            order = np.argsort(-gain)                            # biggest winner first
        elif exit_rule == "random":
            order = rng.permutation(len(incumbents))
        else:
            raise ValueError(exit_rule)
        victims = list(incumbents[order[:n_replace]])
        exits.extend((t, v) for v in victims)
        keep = [n for n in held if n not in set(victims)]
        avail = np.setdiff1d(np.arange(n_assets), np.array(keep))
        buys = avail[np.argsort(signal[t, avail])[-n_replace:]]
        held = keep + list(buys)
        holdings.append(set(held))
    return holdings, exits


def counterfactual_gaps(idio, holdings, exits, horizon):
    """For each exit (t, j): gap = forward return of the sold name minus the
    equal-weighted forward return of the incumbent book carried INTO month t
    (the closed-form expectation of a random sell). Positive gap => the names you
    chose to sell beat the ones you kept => a sell-discipline leak.
    """
    n_months = idio.shape[0]
    gaps, months, per_h = [], [], []
    for (t, j) in exits:
        if t + horizon >= n_months:
            continue
        pool = np.array(sorted(holdings[t - 1] - {j}))          # eligible-to-sell book
        fwd_sold = idio[t + 1:t + 1 + horizon, j].sum()
        fwd_pool = idio[t + 1:t + 1 + horizon, pool].sum(axis=0).mean()
        gaps.append(fwd_sold - fwd_pool)
        months.append(t)
        sold_path = np.cumsum(idio[t + 1:t + 1 + horizon, j])
        pool_path = np.cumsum(idio[t + 1:t + 1 + horizon, pool], axis=0).mean(axis=1)
        per_h.append(sold_path - pool_path)
    return np.array(gaps), np.array(months), np.array(per_h)


def block_bootstrap_ci(gaps, months, reps, rng):
    """Resample whole calendar months with replacement: exits in the same month
    share one forward market path, so the month is the correlated block."""
    uniq = np.unique(months)
    blocks = [gaps[months == m] for m in uniq]
    k = len(blocks)
    means = np.array([
        np.concatenate([blocks[i] for i in rng.integers(0, k, size=k)]).mean()
        for _ in range(reps)
    ])
    lo, hi = np.percentile(means, [5, 95])
    return means.std(), lo, hi


# Fixed per-rule RNG stream tags (house convention: named integer streams, never
# hash(), which is process-randomized and breaks run-to-run reproducibility).
RULE_STREAM = {"disciplined": 1, "disposition": 2, "random": 3}


def one_world(rho, rule, seed, cfg):
    n_assets, n_months, k, r, ic, h, vol = cfg
    rng = np.random.default_rng([seed, RULE_STREAM[rule], int(rho * 100)])
    idio = simulate_market(n_assets, n_months, rho, vol, rng)
    holdings, exits = simulate_manager(idio, k, r, ic, rule, rng)
    gaps, months, per_h = counterfactual_gaps(idio, holdings, exits, h)
    _, lo, hi = block_bootstrap_ci(gaps, months, 1000, rng)
    return gaps.mean(), (lo > 0 or hi < 0), per_h.mean(axis=0)


if __name__ == "__main__":
    cfg = (120, 96, 40, 6, 0.35, 4, 0.05)          # assets, months, hold, replace, ic, H, vol
    N_WORLDS = 40
    for label, rho in [("IID idio (current sim, rho=0)", 0.0),
                       ("persistent idio (rho=0.4)", 0.4)]:
        print(f"\n=== {label} ===  (mean CG over {N_WORLDS} seeded worlds)")
        for rule in ["disciplined", "random", "disposition"]:
            cgs, flags, curves = zip(*[one_world(rho, rule, s, cfg) for s in range(N_WORLDS)])
            cgs = np.array(cgs) * 1e4
            detect = np.mean(flags)
            print(f"  {rule:12s}: CG = {cgs.mean():+7.1f}bp  (sd {cgs.std():5.1f})  "
                  f"CI-excludes-0 in {detect:4.0%} of worlds")
            if rule == "disposition" and rho > 0:
                curve = np.mean(curves, axis=0) * 1e4
                print("     alpha-retained curve (bp by fwd month):",
                      " ".join(f"{v:+.0f}" for v in curve))
```

Run it and it prints, deterministically:

```
=== IID idio (current sim, rho=0) ===  (mean CG over 40 seeded worlds)
  disciplined : CG =    +2.8bp  (sd  43.0)  CI-excludes-0 in  12% of worlds
  random      : CG =   -10.4bp  (sd  42.4)  CI-excludes-0 in  12% of worlds
  disposition : CG =   +12.8bp  (sd  36.2)  CI-excludes-0 in   8% of worlds

=== persistent idio (rho=0.4) ===  (mean CG over 40 seeded worlds)
  disciplined : CG =  -163.1bp  (sd  49.6)  CI-excludes-0 in  90% of worlds
  random      : CG =    +8.4bp  (sd  54.9)  CI-excludes-0 in  15% of worlds
  disposition : CG =  +365.3bp  (sd  74.4)  CI-excludes-0 in 100% of worlds
     alpha-retained curve (bp by fwd month): +224 +311 +349 +365
```

The top panel is §3.8's structural null: in the iid world **no exit rule can
leak** — even the deliberately flawed disposition manager reads +13 bp, and the
90% interval excludes zero at roughly its nominal 10% false-positive rate
(8–12% across rules). The bottom panel is the whole card in four lines: the
disciplined manager *earns* −163 bp per exit (its sells cull spent names), the
random-seller sits at +8 bp (the counterfactual is unbiased — the diagnostic's
own control group), and the disposition manager leaks +365 bp per exit, with
the forgone-alpha curve rising for three months and plateauing — "the names you
sell keep beating your book for a quarter, then the edge you threw away is
spent."

One implementation detail earned by a bug: the counterfactual pool is
`holdings[t - 1] - {j}` — the incumbents. An earlier draft used `holdings[t]`,
which includes the month's fresh buys; under persistence those buys are
selected on hot signals, inflating the pool's forward return and biasing every
gap downward (the random-seller read −148 bp, a phantom "skill"). The pool must
be the set the sell was chosen *from*.

## 5. Reading the demo

The gallery page `s4.html` is fully synthetic (SYNTHETIC badge; simulator
world with `S4_IDIO_AR1_DEMO = 0.4`, demo seed pinned). It renders one world —
seed 8 of the §4 grid, chosen because its random-sell control sits nearest
zero — with two named managers plus the ghost. Both books are 40 names,
6 exits/month (≈72 exits/year, a deliberately high-turnover book — see the
power gate below), identical entry skill; **only the exit rule differs.**

**The two-manager split — the centrepiece.**

- **Larkspur Ridge Partners** (disciplined exits — sells its lowest-conviction
  incumbents): counterfactual gap **−372 bp per exit** [−532, −212], curve
  −187 / −330 / −387 / −372 bp over forward months 1–4, across 546 exits. Verdict
  chip: **culls well** — its sold names underperform the book it keeps.
- **Redgate Harbor Capital** (disposition exits — sells its biggest 3-month
  winners): counterfactual gap **+222 bp per exit** [+42, +390], curve
  +130 / +231 / +240 / +222 bp, across 500 exits. Verdict chip: **edge leaks at
  the exit** — the names it sells keep beating its book for roughly three months
  after the sale.
- **The ghost line:** the random-sell counterfactual on the same books reads
  **+28 bp** [−149, +201], across 501 exits — a visible zero. The page says why
  this line exists: it is the diagnostic auditing itself.

§5 numbers reconciled to the generator output on 2026-07-07; deltas from the
teaching-code figures are flagged for the numerics gate.

How each element maps to the method:

- **The counterfactual-gap rail** = the §3.3 IntervalStat: one point per
  manager (the mean gap per exit), the band is the 5th–95th month-block
  bootstrap interval (§3.6), the zero line is the random-sell ghost. No bare
  points anywhere on the page.
- **The forgone-alpha curve** = §3.5's $C(h)$ with its band: Redgate's rises
  and plateaus (the give-back accrues for ~3 months), Larkspur's dives. The
  **horizon slider** (H = 1..6) is the card's adjustable-output requirement —
  move it and watch the gap, band, exit count, and curve switch among committed
  precomputed states; the verdict does not live
  at one hand-picked horizon.
- **The trend strip** = §3.7: yearly buckets render with wide bands; the
  **quarterly view refuses** — at ~18 exits/quarter the worst-bucket standard
  error (≈ 820 bp) exceeds any plausible effect, and the PowerGate prints
  exactly that arithmetic instead of a chart. The refusal is the pitch.
- **The tier rows** = the §6.1 contract made visible: the P row is the page;
  the E row shows only a low-confidence descriptive chip ("turnover
  accelerates after gains — exit-behavior hint, not a measurement"); the
  R row is a refusal card: *"Exit quality cannot be inferred from monthly
  returns. This page needs transaction-level data."* No number is faked.

**Demo-vs-live split (stated on the page).** The demo's residual returns are
the simulator's ground-truth idio returns — zero estimation error in the factor
adjustment — and the demo world's dials (ρ = 0.4, loud exit flaws) are
teaching-scale: the measured field effect in SFBS is an order of magnitude
smaller (§6.3), which is exactly why the live version is power-gated. A live
build residualizes with a bought risk model and inherits its estimation error;
bands widen accordingly.

What an allocator should conclude: two managers with identical entry skill and
identical-looking tear sheets differ by ~590 bp per exit in sell quality; the
diagnostic separates them cleanly at 500–546 exits per book, states its
uncertainty, refuses the quarterly trend it cannot support, and refuses the R
tier entirely.

## 6. Honest limits & go-live

### 6.1 Data contract per tier

S4 is **transaction-native**: the whole method lives at the P tier, and the
card's own definition forbids faking it lower.

| Tier | Inputs the live version needs | What the card produces |
| --- | --- | --- |
| **P** (native) | Position-level transparency with **exit dates**: transaction history or monthly holdings snapshots (from which exits are extracted as held-then-gone transitions, the `emit_tiers` transparency frame); security identifiers mappable to a factor/risk model; the factor return set (bought risk model per the Sweep D buy-verdict, or an FF-style regression set); ≥ `S4_MIN_EXITS_GAP` exits inside the evaluation window. | The full diagnostic: counterfactual gap with block-bootstrap band, forgone-alpha curve, gated trend, roster-shrunk comparison. |
| **E** | Gross/net, turnover, and factor-bucket dynamics (Open Protocol-aligned) | **Exit-behavior hints only, labeled low-confidence:** e.g. turnover acceleration following gain months — a descriptive chip that motivates asking for the P tier. Never a counterfactual gap, never a verdict. |
| **R** | — | **Refusal.** Exits are unobservable in monthly returns; the card renders its go-live box instead of a number ("do not fake it" — card §Tier rungs). |

**Frequency & extraction.** Monthly holdings are the demo cadence and the
minimum viable grain; daily transaction data (the SFBS grain) strictly improves
both the exit-date precision and the horizon resolution. An exit is a full
liquidation of a name (`weight ≠ 0 → weight = 0`); partial trims are out of
scope for v1 and flagged **`S4_PARTIAL_TRIMS` (provisional — full exits only)**.

**Compliance (standing):** synthetic managers in the repo; any live use sits
inside an existing transparency relationship (E1 ladder) with the manager's
knowledge of what is computed; no employer-internal facts anywhere in code,
docs, or committed demo JSON.

### 6.2 What S4 does not do (do-not-build adjacency)

- **No persistence test.** The trend strip is descriptive, within-manager,
  interval-rendered; it never claims past sell-quality predicts future returns
  and never ranks managers by it.
- **No FDR luck-screen.** The roster view pools via hierarchical shrinkage
  (S1 machinery) — the house small-N method — not via cross-sectional
  discovery tests.
- **No regime splits, no conditional betas.** One stationary factor adjustment
  per evaluation window.
- **No style-drift inference from returns, and no R-tier inference at all.**
- **No mechanical redemption rule.** Deterioration + refusal to engage is a
  *soft* input to a human redemption conversation (card §Risks; Goodhart —
  a published mechanical sell-quality trigger would be gamed by deferring
  exits past the measurement window).

### 6.3 Power & validation plan

Power scales with the number of exits — the card's Sweep C verdict (Shrink,
hard-gated, S3's gating machinery) made concrete with §4's executed numbers.
In the demo world (month-clustered, H = 4): standard error ≈ 50 bp at
**546 exits**; the minimum detectable gap at 5% size / 80% power is
$2.8 \times \text{se} \approx 140$ bp per exit. Scaling by
$\text{se} \propto 1/\sqrt{n}$:

| Exits observed | se (≈) | Detectable gap (80% power) | Book that gets there |
| --- | --- | --- | --- |
| 150 | 95 bp | ≈ 270 bp | concentrated book, ~2 years at 6 exits/month — **egregious leaks only** |
| 546 | 50 bp | ≈ 140 bp | the demo book (≈ 72 exits/yr, 7.6 yr) |
| ~1,900 | 27 bp | ≈ 75 bp — **the SFBS field magnitude** | high-turnover books: ~4 yr at 500 exits/yr, ~2 yr at 1,000 |

The honest reading: a 30-name, low-turnover book **never** clears the
SFBS-magnitude bar (26+ years at 72 exits/yr); S4's live audience is
high-turnover transparent books, and for everyone else the gate speaks. The
headline gap refuses below **`S4_MIN_EXITS_GAP` = 150 exits (provisional —
NUMERICS-GATE)**, and the gate text states the detectable-gap arithmetic, not
just "insufficient N."

Validation runs on the simulator with the §3.8 dials; cells contribute to the
X1 atlas ([`x1-tier-power-atlas.md`](x1-tier-power-atlas.md)) as S4's rows,
on the card's stated axes: **exits/year × years × idio persistence ρ**, ≥ 500
seeded replications per cell via the `x_grid` machinery (per-module RNG
streams; Wilson 95% intervals on every rate).

Acceptance gates:

1. **Specificity / structural null (load-bearing).** At ρ = 0 (the current
   simulator, all exit styles) and at ρ > 0 with `exit_style = "random"`, the
   90% interval excludes zero in ≤ 10% of replications within Wilson error.
   §4 measures 8–15% at 40 worlds — passes provisionally; the full grid pins
   it.
2. **Detection & direction.** At ρ = `S4_IDIO_AR1_DEMO`, the disposition
   manager's gap is positive with the interval excluding zero, the disciplined
   manager's negative, at rates reported as an operating characteristic
   against exits-observed (the atlas curve). §4 measures 100% / 90% at 546
   exits.
3. **Bootstrap coverage.** Empirical coverage of the 90% block-bootstrap
   interval within ±5 pp of nominal across cells, including the deff < 1
   stratified cells (§3.6) — miscalibrated uncertainty kills the card
   (house rule: worse than none).
4. **Pool-convention regression.** The `holdings[t]` bug of §4 is pinned by a
   test: with the fresh-buy-contaminated pool the random-seller must read
   spuriously negative; with the incumbent pool it must not. The bug stays
   fixed.
5. **Horizon robustness.** The verdict's sign is stable across H ∈ {2, …, 6};
   the slider must not be a verdict-shopping device.

**Simulator dependency (honest, named).** Gates 1–5 need the **two-dial S4
extension** of §3.8 (`idio_ar1` on `MarketConfig`, `exit_style` on
`ManagerConfig`) — small, opt-in, default-byte-identical, precedented by
`death_month` (M3) and `net_drift` (M1). The card's original hope that
existing dials suffice is **tested and answered no** (§4, top panel): without
market-side persistence, no exit behavior can produce a nonzero gap, so an
exit-lag dial alone would demo nothing.

### 6.4 Kill criteria

- **Statistical.** If gate 3 fails — the block-bootstrap band cannot hold
  coverage across realistic clustering — the card ships **descriptive-only**:
  the forgone-alpha curve without a verdict chip, recorded in writing per
  converge-or-cut. If the live evaluable audience (books clearing
  `S4_MIN_EXITS_GAP`) turns out to be empty, the card parks as an atlas row
  and an E-tier hint chip, honestly.
- **Political (the card's own words: the most sensitive analytic in the
  portfolio).** Ships **only** inside the E1 transparency-ladder relationship,
  adjustable-output only, help-framed. If any pilot conversation reads as
  audit rather than help, the manager-facing version is killed and the
  diagnostic stays internal (watchlist only). A manager-facing version that
  leaks to a redemption committee unedited is a trust breach that poisons the
  P tier every other card depends on — the framing rules are not cosmetic.

### 6.5 How it ships in the repo

Reuse first; the new estimator is one small pure module.

- **Simulator extension (named prerequisite):** the two §3.8 dials in
  `src/quant_allocator/simulator/market.py` (`idio_ar1`) and
  `src/quant_allocator/simulator/manager.py` (`exit_style`), each opt-in with
  byte-identical defaults and dial-guard tests, mirroring the `death_month` /
  `net_drift` precedents (see `tests/simulator/test_manager_dials.py`).
- **New module `src/quant_allocator/flagships/sell_discipline/pipeline.py`:**
  pure functions — `extract_exits(weights) -> list[ExitEvent]` (held-then-gone
  transitions from the P-tier weights frame),
  `counterfactual_gap(residuals, holdings, exits, horizon) -> GapResult`
  (§3.3 gap + §3.5 curve), no rendering, no I/O (S2 §5 convention).
- **Uncertainty: import, do not re-implement.** The month-cohort resampling
  and deff reporting call P3's
  `flagships/decision_audit/aggregate.py::cohort_block_bootstrap` and
  `design_effect` with the month as the cohort — the cohort machinery is
  identical; only the value being resampled differs.
- **Roster view:** `flagships/skill_ledger/empirical.py::shrink_alphas`
  applied to per-manager gaps and bootstrap ses — import, never re-fit.
- **Shared event-study kernel (S3 sequencing).** S3's entry-aligned curves and
  S4's exit-aligned curves are one clustered event-study kernel with a
  different alignment column. The card builds **after S3** per the convergence
  order; whichever spec is implemented first owns the kernel module, the other
  imports it — no duplication.
- **Demo — `src/quant_allocator/demo_data/s4_sell.py`:** imports the pipeline,
  runs the pinned seed-8 world (two named managers + ghost), emits committed
  JSON to `site/data/s4_sell.json` via `_emit.write_json`; **CI renders from
  JSON only, CI never computes** (demo-layer doctrine).
- **Atlas cells:** S4's exits/year × years × ρ grid rides the
  `demo_data/x_grid.py` / `x_metrics.py` machinery (per-config cache, budget
  discipline).
- **Depends:** simulator (+ the two-dial extension), P3 aggregate, S1
  empirical (roster view), X1 grid, S3-shared kernel. `numpy` only for the
  demo; the live factor adjustment consumes a bought risk model per the
  buy-verdict — no new runtime dependency in this repo.
- **Effort:** **M** (card estimate) — the estimator is small; the simulator
  extension and the validation grid are the real work.

### 6.6 Adoption & packaging

Sweep E doctrine, applied to the touchiest card in the portfolio:

- **Help-framing is load-bearing copy.** "Where the edge leaks," "your buys
  add value — here is where some of it goes back," never "your sells are
  wrong." The SFBS attention story (§3.9) is part of the pitch: the deficit is
  an *attention* pattern, not incompetence, and it improved in-sample when
  attention was forced — that is what makes this coaching, not accusation.
- **Inside the E1 ladder only.** The manager-facing artifact exists within an
  agreed transparency relationship, is shown to the manager before anyone
  else, and the manager knows exactly what is computed. This card is the E1
  ladder's payoff exhibit: the analytic that *requires* trust and rewards it.
- **Adjustable output (Dietvorst).** The horizon slider and the trend
  granularity are user controls; the diagnostic is an input to the PM's own
  judgment, not a verdict handed down.
- **Receipts, calibrated.** Every number carries its band and its n: "+385 bp
  per exit [+292, +479], 546 exits, month-clustered" — and the gates refuse
  out loud with their arithmetic shown.
- **Who sees what, when:** the manager sees their own panel in an engagement
  session (never cold in an email); the investment team sees the watchlist
  trend at monitoring cadence; leadership sees nothing manager-attributed
  unless the engagement escalates — the soft-redemption input is a sentence in
  a review memo, not a dashboard.

### 6.7 Go-live requirements (demo-page box, expanded)

- **Data ask:** tier P — transaction history or monthly holdings with exit
  dates and security identifiers, plus a factor/risk model for
  residualization. Tier E buys hints only; tier R refuses.
- **Sample required:** ≥ **`S4_MIN_EXITS_GAP` = 150 exits** for the headline
  gap (detects ≈ 270 bp/exit leaks); ≈ **1,900 exits** to resolve an
  SFBS-magnitude (75 bp) deficit — i.e., 2–4 years of a high-turnover book;
  a 30-name low-turnover book honestly never clears, and the page says so.
- **Build effort:** **M** — small pure estimator + the named two-dial
  simulator extension + the atlas grid; bootstrap and shrinkage are imported
  from P3/S1.
- **Go-live box (demo page):** data ask = P-tier exits + risk model; sample =
  150 exits minimum, ~1,900 for field-size effects; effort = M; ships inside
  the E1 relationship only.

## 7. Deeper reading

**Canonical references (read in this order):**

1. **Akepanidtaworn, Di Mascio, Imas & Schmidt (2023), "Selling Fast and
   Buying Slow: Heuristics and Trading Performance of Institutional
   Investors," *Journal of Finance*.** The finding, the random-sell
   counterfactual design, and the attention mechanism (the deficit vanishes on
   announcement days). S4 is this paper as an allocator's instrument.
2. **Odean (1998), "Are Investors Reluctant to Realize Their Losses?,"
   *Journal of Finance*** — with **Shefrin & Statman (1985)** for the original
   disposition framing. The behavioral flaw the demo dial implements, and the
   original evidence that sold winners subsequently outperform held losers.
3. **Frazzini (2006), "The Disposition Effect and Underreaction to News,"
   *Journal of Finance*.** Why disposition selling *costs* money: residual
   returns persist (under-reaction), so the winner you sell keeps paying the
   person who bought it from you. The physical carrier of the leak, and the
   justification for the `idio_ar1` dial.
4. **Künsch (1989), "The Jackknife and the Bootstrap for General Stationary
   Observations," *Annals of Statistics*.** Block resampling for dependent
   data — the month-cohort bootstrap's foundation; Kish (1965, *Survey
   Sampling*) for the design effect printed beside every band.
5. **Di Mascio, Lines & Naik (2017), "Alpha Decay" (working paper).**
   Secondary: institutional alpha accrues early in a position's life and
   decays — the entry-side counterpart (S3's territory) that makes exit timing
   a first-order P&L question.

**Questions you should be able to answer after reading this page:**

- **Why is random-sell the right benchmark?** "Did it go up after you sold"
  confounds market direction; "versus the index" confounds factor tilts and
  universe. The ghost sells from the same book at the same moment, so
  everything common cancels and only exit *selection* remains. And why does
  using the pool mean instead of actual lotteries change nothing but the
  noise?
- **State the sign convention cold.** Positive gap = sold names beat the kept
  book = leak; negative = disciplined culling; the random rule must read zero
  — and *why* the random rule reading zero is the diagnostic auditing itself.
- **Why can no exit rule leak in an iid world?** If forward residuals are
  unpredictable at the sale, expected gap is zero for every rule — the
  diagnostic measures exit behavior *interacted with* forward-predictable
  alpha. Hence why the simulator needs the `idio_ar1` dial before the demo can
  show a leak, and why an exit-flaw dial alone was tested and found
  insufficient (§4, top panel).
- **Why does the pool exclude the month's fresh buys?** Fresh buys are
  selected on hot signals; including them inflates the counterfactual and
  manufactures phantom sell-skill for everyone — the mock's one real bug.
  The pool is the set the sell was chosen from.
- **Do the power arithmetic yourself.** se ≈ 50 bp at 546 month-clustered
  exits; detectable gap ≈ 2.8 × se; scale by $1/\sqrt{n}$ to show a 75 bp
  SFBS-size deficit needs ~1,900 exits — and therefore which books this card
  can honestly serve, and what the page must say to everyone else.
- **Why is the quarterly trend refused, and why is that not a persistence
  test either way?** 18 exits ⇒ se ≈ 290 bp ⇒ any quarterly story is noise;
  and even the yearly trend is a descriptive decision-quality series with
  bands, never a claim that past sell-quality predicts future returns.
- **Explain the diagnostic to a PM in three sentences, as help.** "Your buys
  demonstrably add value. On exits, the names you sell keep beating the book
  for about three months — roughly X bp per exit, and here is the band. This
  is the most common, most fixable pattern in the literature: it is an
  attention effect, not a judgment problem."
- **State what S4 does not claim.** Not a redemption trigger, not a manager
  ranking, not a persistence or regime finding — a measured, gated,
  interval-honest description of one decision type, delivered inside a trust
  relationship.

## 8. Method-review gate rulings (2026-07-07)

1. **`S4_POOL_WEIGHTING` — equal-weight confirmed** (the SFBS uniform-ghost
   convention; the pool mean is the closed-form expectation of a uniform
   random sell). The position-weighted variant answers a different question
   and is out of v1.
2. **`S4_TWOWAY_CLUSTER` — month-only in v1, confirmed.** The measured
   deff < 1 (0.68–0.92: selective exit rules stratify month cohorts) makes
   acceptance gate 3 **binding**: block-bootstrap coverage within ±5 pp of
   nominal *including* the deff < 1 cells, or the card ships descriptive-only
   per §6.4.
3. **Demo loudness approved with mandatory disclosure.** ρ = 0.4 with
   IC = 0.35 is teaching-scale (~5–10× SFBS field magnitudes); the §5
   demo-vs-live sentence stating this is required, test-pinned copy.
4. **No shared S3/S4 event-study kernel in v1.** §6.5's "whichever spec is
   implemented first owns the kernel" is superseded: each card implements its
   own event alignment in its own flagship module (both are small pure
   functions with a different alignment column and a different averaged
   quantity). This keeps the parallel build tracks file-disjoint; extraction
   is revisited only if a third consumer appears.
5. **The two-dial simulator extension is approved, with one amendment.**
   `MarketConfig.idio_ar1` must be implemented as a filter on the *existing*
   innovation draws ($a_{i,t} = \rho\,a_{i,t-1} + \sqrt{1-\rho^2}\,
   \sigma_i\,\varepsilon_{i,t}$), so ρ = 0 is byte-identical and no new RNG
   stream is consumed. `ManagerConfig.exit_style` gains a **fourth value
   `"random"`** — validation-only, required by acceptance gate 1's specificity
   control, which the three-value enum of §3.8 could not express; `"random"`
   consumes RNG and takes a new named stream tag in the module registry.
   `"age"` remains the byte-identical default; dial-guard tests mandatory for
   both dials.
6. **`S4_PARTIAL_TRIMS` — full exits only in v1, confirmed.**
7. **Constants confirmed:** `S4_HORIZON_MONTHS` = 4 (slider renders 1..6),
   `S4_MIN_EXITS_GAP` = 150, `S4_MIN_EXITS_BUCKET` = 60,
   `S4_BOOTSTRAP_REPS` = 2,000, `S4_IDIO_AR1_DEMO` = 0.4,
   `S4_DISPOSITION_TRAIL_MONTHS` = 3. Demo world: seed 8 with fixed integer
   stream tags. The `hash()`-seeding reproducibility bug the reference mock
   found is a binding house lesson: **no `hash()`-derived seeds anywhere** —
   named integer stream tags only.
8. **Demo manager names approved:** Larkspur Ridge Partners, Redgate Harbor
   Capital (authored constants; no collisions).
