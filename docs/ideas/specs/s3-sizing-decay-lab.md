# S3 · Sizing & Alpha-Decay Lab — Method Spec

**Status: Reviewed — method gate passed 2026-07-07 (rulings in §8)**
**Date:** 2026-07-07
**Card:** [`docs/ideas/2026-07-05-idea-cards.md`](../2026-07-05-idea-cards.md) § S3
**Demo:** gallery page `s3.html` (picker-vs-sizer split + decay curve + holding decomposition + PowerGate refusal; fully synthetic, §5)

---

## 1. What this is

S3 is a **trade-level lab** for one question an allocator can only ask of a
position-transparent manager: *when this book makes money, is the edge in the
picking, the sizing, or the holding?* Three separate managers can post the same
headline return for three completely different reasons — one picks the right
names and equal-weights them, one picks ordinary names but sizes conviction
brilliantly, one picks well but clings to positions long after the edge has
decayed. The tear sheet cannot tell them apart. Their trades can.

The lab computes three diagnostics from a manager's dated positions and trades:

- an **event-time alpha-decay curve** — line every position up by months-since-
  entry and trace the idiosyncratic return it earns as it ages, so you can read
  off how long this manager's edge actually lasts;
- a **sizing-vs-outcome curve** — ask whether the manager's bigger positions
  actually earned more, and measure the return their conviction added over an
  equal-weight version of the same book;
- a **holding-period decomposition** — split the book's total alpha by the age at
  which it was earned, so you can see what fraction comes from fresh positions
  versus stale ones.

Every one of these is **trade-level**, which means every one is **power-gated**.
The discriminating power of a hit-rate or sizing statistic is set by the number
of independent trades behind it, and the Tier & Power Atlas (card X1) has
measured exactly where that power arrives. A concentrated thirty-name book that
turns over slowly never accumulates enough trades to separate skill from luck in
a decade; a high-turnover quant book clears the bar in a few years. Below the bar
the lab renders **"insufficient N," never a number** — the refusal is the
product, not a failure of it. The audience is manager-facing engagement (for the
transparent managers whose trades we can see) and the investment team underwriting
high-turnover books where the power actually clears.

## 2. Why we use it

The decision the lab serves is not primarily *hire or fire* — it is **size the
mandate and shape the engagement**. A manager with genuine name-selection skill
but flat or inverted sizing is not a redemption; it is a coaching or a resizing
conversation ("your picks are real, but you are leaving the conviction premium on
the table"). A manager whose alpha decays in six weeks but who holds positions for
two years is running the wrong turnover, not the wrong strategy. These are
*constructive* findings — the specific, P&L-driver-level feedback that
distinguishes a partner from a monitor — and none of them is reachable from
returns alone.

The naive alternatives fail in instructive ways. *Read the headline Sharpe* tells
you the book made money, not why, so it cannot separate the picker from the sizer
and cannot tell you which lever to pull. *Compute a raw hit rate and quote it*
("this manager is right 54% of the time") ignores that a hit rate on a few hundred
correlated position-months has an enormous error bar — quoting the point number is
exactly the bare-point sin the house forbids, and at a concentrated book the honest
interval swamps the estimate. *Run a pooled cross-sectional regression of return on
position size and read the t-statistic* looks rigorous and is badly wrong: the
positions within a month share common factor and idiosyncratic shocks, so the
pooled standard error understates the true one — the X1 gate measured the
understatement at roughly 40% for this estimator — and a manager gets told their
sizing is "significant" on evidence that is nothing of the kind. What the lab wins
is each diagnostic computed **properly** (month-clustered inference, cluster-
bootstrap intervals) and **gated** against a measured power threshold, so a number
appears only when the trade count can support it.

- **Decisions improved:** **size** — a manager with real picks but weak sizing is
  a resize/coach case, not a redeem; **select** — underwriting high-turnover quant
  books where the power clears and the sizing/decay signatures are underwritable.
- **Customer:** manager-facing engagement (transparent managers); the investment
  team for underwriting.

S3 shares its event-study machinery with the [sell-discipline diagnostic
(S4)](s4-sell-discipline.md) and its trade-count power gate with the [Tier & Power
Atlas (X1)](x1-tier-power-atlas.md); it is the P-tier sibling of the returns-only
research bet [S6](s6-returns-only-signatures.md), and §6.1 states precisely where
that boundary sits.

## 3. How it works

### 3.1 The mental model, before any math

Picture a manager's book as a stream of positions, each with a birthday (the month
it entered) and a size. Three simple regroupings of that stream answer the three
questions.

**Line the positions up by age.** Forget which calendar month it is; ask instead,
*for every position that is one month old, what idiosyncratic return did it earn
this month? For every position that is six months old?* Average within each age and
you get a curve: the alpha a position earns as a function of how long it has been
held. A manager whose edge is fresh insight will show a curve that starts high and
decays; a manager whose names keep working for years shows a flat one. The **rate**
at which the curve falls is the manager's alpha half-life, and it tells you the
turnover the book *should* be running.

**Sort the positions by size.** Within each month, ask whether the bigger bets
earned more than the smaller ones. If a manager truly knows which ideas are best
and sizes accordingly, their largest positions should, on average, out-earn their
smallest — the sizing curve slopes up. If they size by habit or by liquidity rather
than by conviction, the curve is flat. And there is a clean counterfactual sitting
right next to the real book: *what would this manager have earned holding exactly
these names equal-weighted?* The gap between the real book and its equal-weight
shadow is the **realized value of the manager's sizing** — the properly-computed
version of the "optimal-vs-actual" gap the manager-analytics vendors sell.

**Bucket the alpha by age.** Add up all the alpha the book earned and ask what
fraction was earned by positions in their first quarter versus positions over a
year old. This is the decay curve's blunt cousin, and it answers the turnover
question in dollars: "eighty percent of your P&L is earned in the first six months;
the forty percent of your gross sitting in year-plus positions contributes almost
nothing."

The catch that governs everything: each of these averages is only as trustworthy
as the number of *independent* trades behind it, and trades within a month are not
independent (a factor move hits them all) nor are the months of a single name (it
is the same bet). So the honest lab counts effective trades, compares that count to
a measured power threshold, and stays silent when the count falls short.

### 3.2 A worked toy example

**The sizing curve, by hand.** Take one month of a manager's book, three long
positions, with sizes (gross weights) and the active return each earned that month —
"active" meaning in excess of the equal-weight average of the universe:

| Position | size $|w|$ | active return $r-\bar r$ | contribution $w(r-\bar r)$ |
| --- | --- | --- | --- |
| A | 0.02 | +0.0% | 0.0000 |
| B | 0.04 | +2.5% | 0.0010 |
| C | 0.06 | +6.7% | 0.0040 |

The sizing slope for this month is the ordinary-least-squares slope of contribution
on size across these three names. With sizes centred at their mean $\bar{|w|}=0.04$,
the deviations are $[-0.02, 0, +0.02]$, so

$$b_t = \frac{\sum_i (|w_i|-\bar{|w|})\,c_i}{\sum_i (|w_i|-\bar{|w|})^2}
      = \frac{(-0.02)(0) + (0)(0.001) + (0.02)(0.004)}{(0.02)^2 + 0 + (0.02)^2}
      = \frac{0.00008}{0.0008} = 0.10.$$

A positive slope: the biggest position (C) earned the most, so this manager's
conviction was rewarded this month. Now imagine the same three names sized
**equal-weight**, all at $|w| = 0.04$. The size deviations are all zero, the
denominator collapses, and the slope is undefined — an equal-weight month carries
*no* sizing information, which is exactly right, and the lab skips it. The full
estimator (§3.4) does this month by month and averages the slopes.

**The decay curve, by hand.** Suppose a manager's edge is such that a freshly
entered name earns, in expectation, a +2.0% idiosyncratic return in its first month,
and that this edge halves every 6 months. Then a position that is 6 months old
should earn about +1.0%, and a 12-month-old position about +0.5%. Averaging the
directional idiosyncratic return of every position at each age traces exactly this
decaying curve, and fitting a line to its logarithm recovers the 6-month half-life.
The lab's job is to recover that number, with an honest interval, from a real book —
and §5 shows it landing at 6.04 months against a dialled truth of 6.0 when enough
positions are pooled, while a single manager's estimate carries a wide band.

### 3.3 The trade-level primitives, symbol by symbol

Everything runs on a manager's **position panel**: for each month $t$ and each name
$i$ the book holds, a signed weight $w_{i,t}$ (positive long, negative short) and a
holding age $a_{i,t}$ (months since that position was entered). Alongside it sits the
name's **idiosyncratic return** $\tilde r_{i,t}$ — its return with factor exposure
removed — because we are measuring skill, not beta.

$$
\text{side}_{i,t} = \operatorname{sign}(w_{i,t}), \qquad
c_{i,t} = w_{i,t}\,(\tilde r_{i,t} - \bar{\tilde r}_t), \qquad
\bar{\tilde r}_t = \frac{1}{N_t}\sum_{j} \tilde r_{j,t}.
$$

where:

- $w_{i,t}$ — the signed portfolio weight of name $i$ in month $t$ (a decimal; the
  book's gross is $\sum_i |w_{i,t}|$).
- $a_{i,t}$ — the **holding age** of the position: $0$ in its entry month, $1$ the
  next month, and so on. Entry and exit dates make this observable; it is the axis
  the decay curve and the holding decomposition are built on.
- $\tilde r_{i,t}$ — the **idiosyncratic return** of name $i$ in month $t$: the raw
  return minus its factor-explained part $\beta_i^\top f_t$. Factor-adjustment is a
  required pre-step so the curves measure name-selection skill, not a shared factor
  tilt.
- $\bar{\tilde r}_t$ — the cross-sectional mean idiosyncratic return across the
  universe in month $t$; subtracting it defines the **equal-weight counterfactual**
  (what a position earned *relative to* holding the universe equal-weighted).
- $\text{side}_{i,t}$ — $+1$ for a long, $-1$ for a short; it re-orients a short's
  return so that "the bet worked" is always positive.
- $c_{i,t}$ — the position's **active contribution**: its weight times its return in
  excess of the equal-weight month. This single quantity is the input to both the
  sizing curve and the hit rate, and building it against the equal-weight
  counterfactual is what removes a book's net-long drift bias (a subtlety the X1
  grid ruling documents: raw $w\tilde r$ carries a spurious positive bias at zero
  skill; $w(\tilde r - \bar{\tilde r})$ does not).

**Distributional stance.** We treat each month's cross-section as one draw and each
name's tenure as one bet; we make **no** parametric assumption on the return
distribution (the intervals are bootstrap, not Gaussian). The one assumption that
matters is the clustering structure: contributions are correlated *within a month*
(common shocks) and *within a name* (the same position across months), and the
inference must respect both or it will overstate its own confidence.

### 3.4 Sizing-vs-outcome — the Fama–MacBeth slope

The sizing curve asks whether bigger positions earned more. The disciplined way to
test it is **Fama–MacBeth**: run the cross-sectional regression *within each month*,
then average the monthly slopes and take the standard error from how much those
monthly slopes vary — never a single pooled regression across all position-months.

$$
b_t = \frac{\sum_{i \in \mathcal H_t} \big(|w_{i,t}| - \overline{|w|}_t\big)\,c_{i,t}}
           {\sum_{i \in \mathcal H_t} \big(|w_{i,t}| - \overline{|w|}_t\big)^2},
\qquad
\hat b = \frac{1}{M}\sum_{t=1}^{M} b_t,
\qquad
\operatorname{se}(\hat b) = \frac{s_b}{\sqrt{M}},
\qquad
\hat t = \frac{\hat b}{\operatorname{se}(\hat b)}.
$$

where:

- $\mathcal H_t$ — the set of names held in month $t$ with a defined size and return.
- $|w_{i,t}|$ — the position's size; $\overline{|w|}_t$ its cross-sectional mean that
  month, so the regressor is size **centred within the month**.
- $b_t$ — the month-$t$ sizing slope: extra active contribution per unit of size.
  A month with (near-)equal sizes has $\overline{|w|}$-deviations of zero, a
  singular regression, and is dropped — an equal-weight book yields no slope by
  construction.
- $M$ — the number of usable months; $s_b$ — the sample standard deviation of the
  $b_t$ across months; $\operatorname{se}(\hat b)$ — the **month-clustered** standard
  error, which is the whole point: it is built from the spread of independent monthly
  estimates, so it automatically accounts for the within-month correlation that a
  pooled regression ignores.
- $\hat t$ — the test statistic; the slope is called distinguishable from luck when
  $|\hat t| > 1.96$ **and** the trade count clears the X1 gate (§6.4). Both
  conditions, never just the first.

In words: measure the size–return relationship one month at a time, then let the
month-to-month variability of those measurements tell you how uncertain the average
is. This is the estimator the X1 grid already ships as its `sizing_slope` kernel —
S3 consumes it, it does not reinvent it. The **realized value of sizing** reported
alongside the slope is the counterfactual gap: the book's actual alpha minus the
alpha of the same names held equal-weight. In the demo (§5) that gap is +4.1%/yr,
and the slope's job is to certify it is real, not luck.

### 3.5 The event-time alpha-decay curve

Line every position up by holding age and average its **directional** standardized
idiosyncratic return:

$$
D(m) = \frac{1}{|\mathcal A_m|}\sum_{(i,t)\in \mathcal A_m}
        \text{side}_{i,t}\;\frac{\tilde r_{i,t}}{\sigma_{\tilde r}},
\qquad
\mathcal A_m = \{(i,t): a_{i,t} = m,\; w_{i,t}\neq 0\}.
$$

where:

- $\mathcal A_m$ — every position-month whose holding age is exactly $m$; $|\mathcal
  A_m|$ its count, which shrinks as $m$ grows (fewer positions survive to old age)
  and drives the curve's precision.
- $\sigma_{\tilde r}$ — the idiosyncratic-return scale, used to standardize so the
  curve reads in signal units rather than percent.
- $D(m)$ — the mean directional idiosyncratic return at holding age $m$: the alpha a
  typical position earns in its $m$-th month. The **half-life** $H$ is read from a
  log-linear fit, $D(m) \approx D_1\, 2^{-(m-1)/H}$, over ages $m \ge 1$.

Two honesty notes are built into the estimator. First, **fit from age 1, not age 0**:
the entry month carries an extra selection premium (the position was *chosen* that
month because its signal was strongest), which sits on top of the ongoing decaying
edge and would bias the half-life short if included; §5 shows the fit moving from
5.5 months (ages 0–12) to 6.04 (ages 1–12, matching the 6.0 truth) once the entry
premium is excluded. Second, **the curve is only as long as the turnover allows**:
a book that retires a quarter of each side every month rarely holds anything past
age four, so its decay curve simply stops there — you cannot observe a decay you
never hold long enough to see. This turnover-versus-horizon tension is a first-class
finding (§6.3), not a bug.

### 3.6 Holding-period decomposition

The blunt, dollar-denominated companion to the decay curve: attribute total book
alpha to holding-age buckets.

$$
S_{[\ell,h]} = \frac{\displaystyle\sum_{i,t:\,\ell\le a_{i,t}\le h} w_{i,t}\,\tilde r_{i,t}}
                    {\displaystyle\sum_{i,t} w_{i,t}\,\tilde r_{i,t}}.
$$

where $S_{[\ell,h]}$ is the share of the book's total idiosyncratic alpha earned by
positions whose age fell in the bucket $[\ell,h]$ months. The bucket edges are a
named constant **`HOLDING_BUCKETS` (provisional — {0–2, 3–5, 6–11, 12+ months})**.
The decomposition converts "your alpha decays with a 6-month half-life" into "53% of
your P&L is earned in the first quarter and your year-plus positions contribute 1%"
(§5) — the sentence that actually moves a turnover decision.

### 3.7 Cluster-bootstrap intervals — why not a textbook standard error

Every number above needs an interval, and the naive interval is wrong for the same
reason the pooled sizing regression is wrong: the observations are clustered. Two
positions in the same month share a factor and idiosyncratic-month shock (a **date**
cluster); the same name across months is one repeated bet (a **name** cluster).
Ignoring either inflates the effective sample size and shrinks the interval to a
lie. S3 uses a **cluster bootstrap**: resample whole clusters with replacement,
recompute the statistic, and read the interval off the resampled distribution.

The demo and the reference code resample **months** (the date cluster), which
captures the dominant effect — a single big factor month moves every held position
at once, and is the larger of the two effective-$N$ killers. The full live build
adds the **name** axis via the two-way cluster-robust variance of Cameron, Gelbach &
Miller (§3.9), so a name that recurs across many months is not counted as many
independent trades. Whether the demo ships one-way or two-way is a named constant
**`CLUSTER_AXES` (provisional — date in the demo, date×name live)**; the number of
bootstrap resamples is **`SIZING_BOOTSTRAP_N` (provisional — 2,000; stable 2.5/97.5
percentiles need more than a few hundred)**.

### 3.8 What the lab does *not* do — do-not-build adjacency

S3 sits next to three prohibited or separately-owned analytics, and the boundaries
are load-bearing:

- **No standalone persistence ranking.** The convergence decision's do-not-build
  list bars *cross-manager* persistence rankings (does last year's winner win next
  year?) at $n$ = tens of managers. S3's decay curve is a **within-manager event
  study** — how one book's positions age — not a cross-manager persistence test. It
  ranks nothing across managers and makes no claim about return persistence between
  evaluation windows.
- **No FDR luck-screen, no regime split, no conditional beta.** The lab runs one
  factor-adjustment (a static, pre-registered factor set) and one clustered test per
  statistic. It does not slice the track into regimes, fit time-varying betas at 36–
  60 months, or run a cross-manager multiple-testing screen on alphas — all four are
  on the do-not-build list, and none is needed here.
- **Entry, not exit.** The decay curve is aligned on position **entry**. The
  mirror-image question — do this manager's **sells** underperform a random-sell
  counterfactual? — is card **S4**, which reuses this same event-study machinery on
  exit dates. S3 measures how alpha decays *while held*; S4 measures whether it is
  given back *at the sell*. Keeping them separate keeps each one's copy honest.
- **Not the returns-only version.** The E tier gets *nothing* credible from this lab
  (§6.2), and the R tier — inferring sizing or decay signatures from monthly returns
  — is the explicit research question of card **S6**, not a fallback rung of S3. S3
  is P-tier native and says so.

### 3.9 What the canonical papers contribute

- **Fama & MacBeth (1973), "Risk, Return, and Equilibrium," *JPE*.** Introduced the
  estimate-monthly-then-average-the-slopes procedure whose whole purpose is a
  standard error robust to within-month cross-sectional correlation. §3.4 is a
  direct application: the sizing slope is a Fama–MacBeth coefficient, and its
  month-clustered SE is the reason a pooled regression's t-statistic is not to be
  trusted.
- **Clarke, de Silva & Thorley (2002), "Portfolio Constraints and the Fundamental
  Law of Active Management," *FAJ*.** Generalized Grinold–Kahn to $\text{IR} =
  \text{IC}\cdot\sqrt{\text{BR}}\cdot\text{TC}$, where the **transfer coefficient**
  TC measures how faithfully a book's actual weights express its signals. The sizing
  curve is an empirical read on TC: a flat slope is a low transfer coefficient — good
  picks, poorly transmitted into position sizes — which is precisely the "coach, do
  not redeem" diagnosis.
- **Grinold & Kahn, *Active Portfolio Management*.** The fundamental law itself
  ($\text{IR}\approx\text{IC}\sqrt{\text{BR}}$) supplies the breadth axis: a book's
  discriminating power scales with the number of independent bets, which is why the
  power gate counts trades and why a concentrated book is starved of evidence.
- **Gârleanu & Pedersen (2013), "Dynamic Trading with Predictable Returns and
  Transaction Costs," *Journal of Finance*.** Formalized how a decaying alpha signal
  sets an optimal holding period and trading speed — trade toward a moving target,
  faster when the signal decays faster. This is the decision the decay curve informs:
  the measured half-life is the input to the turnover a book *should* run, and the
  holding decomposition is the audit of whether it does.
- **Cameron, Gelbach & Miller (2011), "Robust Inference with Multiway Clustering,"
  *JBES*.** Gave the two-way (date × name) cluster-robust variance estimator. §3.7's
  live-build interval is theirs: cluster on both axes so neither overlapping-position
  nor common-month dependence is mistaken for independent evidence.

## 4. How to implement

The reference implementation below is **self-contained teaching code** — paste it
into a fresh file and it runs on `numpy` alone, no project imports and no repo
paths. It implements every formula of §3: the dialable ground-truth book generator
(§3.3), the Fama–MacBeth sizing slope with a month-cluster bootstrap (§3.4, §3.7),
the event-time decay curve and its half-life fit (§3.5), the holding-period
decomposition (§3.6), and the independent-trade power-gate quantity (§6.4). The
`alpha_persistence` argument is the named simulator extension of §6.5: with it
**off** (`0.0`) a held name's idiosyncratic return is serially independent — the
v1 simulator — so all expected alpha is earned in the entry month; with it **on** a
name keeps earning a decaying fraction of its entry edge, which is what gives the
decay curve a known half-life to recover.

```python
"""Self-contained sizing & alpha-decay lab (teaching code). numpy only.

Generates an L/S book from four dials — picking skill (IC), alpha half-life,
sizing discipline, turnover — then runs the three S3 analytics: the Fama-MacBeth
sizing slope with a month-cluster bootstrap, the event-time alpha-decay curve,
and the holding-period decomposition. alpha_persistence is the named simulator
extension (section 6): off (0.0) = the v1 book (all alpha earned at entry); on =
a decaying held-name edge that gives the decay curve a known half-life.
"""

import numpy as np


# --- 1. Ground-truth generator: an L/S book with dialable skill ---------------

def simulate_book(ic, half_life, discipline, rebalance_fraction, n_long, n_short,
                  n_names, n_months, idio_vol, rng, alpha_persistence=0.0):
    """Return (weights, idio, ages, side), each shape (n_months, n_names).

    Each month: score every name by a signal whose correlation with that month's
    idiosyncratic return is `ic` decayed by holding age at `half_life`; buy the
    top names, sell the bottom, retire the oldest `rebalance_fraction` of each
    side, and size by conviction (`discipline` blends signal-proportional toward
    equal-weight). alpha_persistence > 0 adds a decaying entry edge to each held
    name's realized idio; = 0 recovers the v1 book.
    """
    idio = rng.normal(0.0, idio_vol, size=(n_months, n_names))
    noise = rng.standard_normal((n_months, n_names))
    weights = np.zeros((n_months, n_names))
    ages_out = np.full((n_months, n_names), -1, dtype=int)
    side_out = np.zeros((n_months, n_names))
    ages, side = {}, {}
    longs, shorts = [], []
    n_rep_long = round(rebalance_fraction * n_long)
    n_rep_short = round(rebalance_fraction * n_short)

    for t in range(n_months):
        for name in ages:
            ages[name] += 1
        if t > 0:  # retire the oldest slice of each side
            drop_l = sorted(longs, key=lambda n: (-ages[n], n))[:n_rep_long]
            drop_s = sorted(shorts, key=lambda n: (-ages[n], n))[:n_rep_short]
            for name in (*drop_l, *drop_s):
                ages.pop(name); side.pop(name)
            longs = [n for n in longs if n not in set(drop_l)]
            shorts = [n for n in shorts if n not in set(drop_s)]

        z = idio[t] / idio_vol
        held = set(longs) | set(shorts)
        cand = [i for i in range(n_names) if i not in held]
        cand_signal = ic * z[cand] + np.sqrt(1 - ic**2) * noise[t, cand]
        order = np.argsort(cand_signal)
        need_l, need_s = n_long - len(longs), n_short - len(shorts)
        new_l = [cand[i] for i in order[-need_l:]] if need_l else []
        new_s = [cand[i] for i in order[:need_s]] if need_s else []
        longs += new_l; shorts += new_s
        for name in new_l:
            ages[name] = 0; side[name] = 1.0
        for name in new_s:
            ages[name] = 0; side[name] = -1.0

        if alpha_persistence > 0:  # section-6 extension: decaying entry edge
            for name in (*longs, *shorts):
                idio[t, name] += (alpha_persistence * side[name]
                                  * 0.5 ** (ages[name] / half_life) * idio_vol)

        signal = np.zeros(n_names)
        for name in (*longs, *shorts):
            ic_eff = ic * 0.5 ** (ages[name] / half_life)
            signal[name] = ic_eff * z[name] + np.sqrt(1 - ic_eff**2) * noise[t, name]

        gross, net = 1.6, 0.2
        long_total, short_total = (gross + net) / 2, (gross - net) / 2
        for names, total, sgn in [(longs, long_total, 1.0), (shorts, short_total, -1.0)]:
            strength = np.abs(signal[names])
            raw = discipline * strength + (1 - discipline)  # 1 = conviction, 0 = equal-weight
            weights[t, names] = sgn * total * raw / raw.sum()
        for name, age in ages.items():
            ages_out[t, name] = age; side_out[t, name] = side[name]
    return weights, idio, ages_out, side_out


# --- 2. Sizing-vs-outcome: the Fama-MacBeth slope -----------------------------

def sizing_slope(weights, idio):
    """Average per-month cross-sectional slope of active contribution on |size|.

    Each month, regress w*(r - r_bar) on |w| across held names; the slope b_t
    asks 'did bigger positions earn more active return?'. Average the b_t
    (Fama-MacBeth) and take the SE from their month-to-month spread -- a month
    cluster, since a common factor shock moves every position together.
    """
    hedged = idio - idio.mean(axis=1, keepdims=True)   # active vs equal-weight month
    contribution = weights * hedged
    monthly = []
    for t in range(weights.shape[0]):
        held = weights[t] != 0.0
        size = np.abs(weights[t, held])
        if held.sum() < 3 or size.std() < 1e-12:       # equal-weight month has no slope
            continue
        centred = size - size.mean()
        monthly.append((centred @ contribution[t, held]) / (centred @ centred))
    monthly = np.asarray(monthly)
    point = float(monthly.mean())
    se = float(monthly.std(ddof=1) / np.sqrt(len(monthly)))
    return point, se, point / se, monthly


def month_block_bootstrap(weights, idio, n_boot, rng):
    """Resample whole months (date clusters) to bound the sizing slope."""
    n_months = weights.shape[0]
    draws = np.empty(n_boot)
    for b in range(n_boot):
        idx = rng.integers(0, n_months, n_months)
        draws[b] = sizing_slope(weights[idx], idio[idx])[0]
    return np.percentile(draws, 2.5), np.percentile(draws, 97.5)


# --- 3. Event-time alpha-decay curve ------------------------------------------

def decay_curve(reps, idio_vol, max_age):
    """Pool positions across managers by holding age; D(m) = mean of
    side * (idio / idio_vol) over all positions of age m."""
    total = np.zeros(max_age + 1)
    count = np.zeros(max_age + 1)
    for weights, idio, ages, side in reps:
        z = idio / idio_vol
        for m in range(max_age + 1):
            rows, cols = np.where((ages == m) & (weights != 0.0))
            if len(rows):
                total[m] += np.sum(side[rows, cols] * z[rows, cols])
                count[m] += len(rows)
    return total / count


def fit_half_life(curve, ages_used):
    """Half-life from a log-linear fit of the decay curve over the given ages."""
    values = curve[ages_used]
    ok = np.isfinite(values) & (values > 0)
    slope = np.polyfit(ages_used[ok], np.log(values[ok]), 1)[0]
    return -np.log(2) / slope


# --- 4. Holding-period decomposition ------------------------------------------

def holding_decomposition(weights, idio, ages, buckets):
    """Share of total idiosyncratic alpha earned in each holding-age bucket."""
    contribution = weights * idio
    total = contribution.sum()
    return {label: contribution[(ages >= lo) & (ages <= hi) & (weights != 0.0)].sum() / total
            for lo, hi, label in buckets}


# --- 5. The power gate: independent trades ------------------------------------

def independent_trades(n_long, n_short, rebalance_fraction, n_months):
    """X1 atlas gate quantity: initial book + turnover accumulated over T months."""
    per_month = round(rebalance_fraction * n_long) + round(rebalance_fraction * n_short)
    return n_long + n_short + per_month * n_months


def annualised(weights, idio):
    monthly = (weights * idio).sum(axis=1)
    return monthly.mean() * 12, monthly.mean() / monthly.std(ddof=1) * np.sqrt(12)


if __name__ == "__main__":
    idio_vol = 0.30 / np.sqrt(12)
    book = lambda ic, disc, reb, T, seed, persist=0.0, N=120, nl=40, ns=25: simulate_book(
        ic, 6.0, disc, reb, nl, ns, N, T, idio_vol, np.random.default_rng(seed), persist)

    # (A) Sizing leg -- the picker/sizer pair (same picks, only sizing differs).
    print("Sizing leg (same picks, ic=0.10, T=120, 25% turnover; v1 book):")
    for label, disc in [("sizer ", 0.9), ("picker", 0.0)]:
        w, idio, ages, side = book(0.10, disc, 0.25, 120, 42)
        point, se, t, _ = sizing_slope(w, idio)
        lo, hi = month_block_bootstrap(w, idio, 400, np.random.default_rng(1))
        alpha, ir = annualised(w, idio)
        print(f"  {label}: alpha={alpha:+.4f} IR={ir:.2f} slope={point:+.5f} "
              f"t={t:+.2f} boot95%=[{lo:+.5f},{hi:+.5f}]")

    # (B) Decay leg -- pooled over managers recovers the dialled half-life.
    reps = [book(0.08, 0.7, 0.10, 120, 7000 + s, persist=0.5) for s in range(120)]
    curve = decay_curve(reps, idio_vol, max_age=12)
    hl = fit_half_life(curve, np.arange(1, 13))
    print(f"\nDecay leg (half-life dial = 6.0): D(0)={curve[0]:.3f} D(6)={curve[6]:.3f} "
          f"D(12)={curve[12]:.3f}; fitted half-life (ages 1-12) = {hl:.2f} months")

    # (C) Holding decomposition.
    w, idio, ages, side = book(0.08, 0.7, 0.10, 120, 42, persist=0.5)
    shares = holding_decomposition(w, idio, ages,
                                   [(0, 2, "0-2m"), (3, 5, "3-5m"), (6, 11, "6-11m"), (12, 200, "12m+")])
    print("Holding decomposition:", {k: f"{v:.1%}" for k, v in shares.items()})

    # (D) Power gate -- trades accumulated, and the concentrated book that fails it.
    print(f"\nIndependent trades: T=48 -> {independent_trades(40,25,0.25,48)}, "
          f"T=120 -> {independent_trades(40,25,0.25,120)}; "
          f"30-name book T=48 -> {independent_trades(20,10,0.10,48)}")
```

Running it prints the numbers this spec quotes:

```
Sizing leg (same picks, ic=0.10, T=120, 25% turnover; v1 book):
  sizer : alpha=+0.1232 IR=1.68 slope=+0.01214 t=+4.68 boot95%=[+0.00680,+0.01745]
  picker: alpha=+0.0823 IR=1.25 slope=+0.00327 t=+0.51 boot95%=[-0.00988,+0.01701]

Decay leg (half-life dial = 6.0): D(0)=0.654 D(6)=0.246 D(12)=0.129; fitted half-life (ages 1-12) = 6.04 months
Holding decomposition: {'0-2m': '53.3%', '3-5m': '21.0%', '6-11m': '24.5%', '12m+': '1.2%'}

Independent trades: T=48 -> 833, T=120 -> 1985; 30-name book T=48 -> 174
```

The sizer and picker hold **identical positions** (selection does not depend on
sizing), so their picks, hit rate, and decay curve are the same; the entire +4.1%/yr
gap between them is the sizer's conviction sizing, which the slope certifies (t=4.68,
interval clear of zero) and the picker lacks (t=0.51, interval straddling zero).

## 5. Reading the demo

The gallery page `s3.html` is fully synthetic (§6 compliance). Two synthetic
managers hold **the same book of picks** — same names, same entry and exit dates,
same holding ages — and differ in exactly one thing: how they size. The page has
four parts.

**The picker-vs-sizer split — the centrepiece.** Meridian Arc Capital (the sizer,
sizing discipline 0.9) and Kelso Bay Partners (the picker, equal-weight) run the
identical set of positions:

- **At the returns tier they look like two different-quality books.** Meridian posts
  a +12.3% idiosyncratic alpha (IR 1.68); Kelso posts +8.2% (IR 1.25). An allocator
  screening tear sheets would rank Meridian well ahead and might question Kelso — and
  would have no idea *why* they differ.
- **The sizing curve explains the entire gap.** Meridian's Fama–MacBeth sizing slope
  is **+0.0121, t = 4.68**, with a month-cluster bootstrap interval **[+0.0068,
  +0.0175]** that clears zero: its bigger bets genuinely earned more, and its
  conviction is worth the +4.1%/yr it adds over the equal-weight counterfactual.
  Kelso's slope is **+0.0033, t = 0.51**, interval **[−0.0099, +0.0170]** straddling
  zero: *on the very same picks*, there is no evidence its (absent) sizing helps or
  hurts. The verdict is not "redeem Kelso" — it is "Kelso has real picks and is
  leaving a conviction premium on the table; this is a sizing conversation."

**The alpha-decay curve.** Because the two managers share picks, they share this
exhibit. The curve traces the directional idiosyncratic return by holding age; the
fitted half-life lands at **6.0 months** when positions are pooled across the
validation replications, against a dialled truth of 6.0 (the ages-1-to-12 fit; the
entry month is shown separately because it carries the extra selection premium of
§3.5). For a **single** manager the same fit is far less certain — its bootstrap
interval on the half-life spans roughly 4 to 14 months — and the page shows that
honest width rather than a false-precise point. The reading: "this edge halves in
about half a year, so a book holding names for two years is running stale risk."

**The holding-period decomposition.** A stacked bar: **53% of the book's alpha is
earned in the first three months, 21% in months 3–5, 25% in months 6–11, and 1%
beyond a year.** The dollar-denominated turnover verdict — the year-plus tail of the
book is dead weight — sits next to the decay curve that explains why.

**The PowerGate — the honest refusal.** A third synthetic manager, Thornwood Select,
runs a **concentrated 30-name book at low turnover**: over four years it accumulates
only **174 independent trades** (versus the 833 a 65-name 25%-turnover book reaches
at the same tenure, and the ~780 the X1 atlas requires to separate a 55% hitter from
a coin). Its sizing panel does **not** render a slope. It renders **"insufficient N —
174 of ~780 independent trades; sizing skill is indistinguishable from luck for this
book."** Dragging the demo's turnover and tenure dials shows the gate opening as the
trade count climbs past the threshold and slamming shut when it falls below — the
card's promise that the lab "tells you exactly when it stops being able to tell them
apart."

**The go-live box** states the ask plainly: dated position-and-trade snapshots (tier
P), a book whose turnover and tenure clear the ~780-independent-trade sizing gate,
factor returns for the idiosyncratic adjustment, and the `alpha_persistence`
simulator extension for the decay/holding legs' validation. What an allocator should
conclude: two managers who look a tier apart on returns are the same picker with
different sizing discipline, worth a coaching conversation rather than a
reallocation — and for the concentrated book, the honest answer is that the trades
simply cannot support the claim yet.

## 6. Honest limits & go-live

### 6.1 What S3 does not do (do-not-build adjacency)

The full statement is §3.8; in brief, S3 runs **no** cross-manager persistence
ranking, **no** FDR alpha luck-screen, **no** regime split, and **no** time-varying
conditional betas — all four are on the convergence decision's do-not-build list,
and the decay curve is a *within-manager* event study, not a persistence test. S3
aligns on **entry**; the **exit**-aligned mirror (sells versus a random-sell
counterfactual) is card **S4**, which shares this machinery. And S3 is **P-tier
native** — the returns-only inference of sizing/decay signatures is card **S6**, not
a rung of this one.

### 6.2 Data contract per tier

| Tier | Inputs the live version needs | What the card produces |
| --- | --- | --- |
| **P** (native) | Dated **position snapshots** (signed weights per name per month) and **trades** (entry/exit dates, so holding age is observable), plus factor returns for the idiosyncratic adjustment (FF5+MOM for equity L/S). | **The whole lab:** the sizing-vs-outcome curve and its Fama–MacBeth slope, the event-time decay curve and fitted half-life, the holding-period decomposition — each with cluster-bootstrap intervals and a PowerGate. |
| **E** | Exposure/risk summaries + gross turnover | **Honestly almost nothing.** No position sizes ⇒ no sizing curve; no entry dates ⇒ no decay curve. The one descriptive hint is an **implied average holding period** from gross turnover (≈ 1 / turnover), rendered as a **descriptive** staleness chip with a TierBadge, never as an alpha-decay claim. |
| **R** | — | **n/a — this is card S6.** Inferring sizing or decay signatures from returns alone is a separate research bet with its own (unproven) power; S3 does not fake a returns-only rung. |

**Frequency & window.** Monthly position snapshots at the manager's native cadence;
the decay curve's reach is bounded by holding period (§6.3). **Compliance
(standing):** synthetic managers in the repo; any real-data rung uses a
transparent (managed-account) manager's own position data under the E1 ladder — no
employer-internal facts, processes, or manager names in code, docs, or the committed
demo JSON. 13F quarterly holdings are **too coarse** for the decay curve (a 45-day-
lagged quarterly snapshot cannot date entries to the month) — flagged honestly, not
used.

### 6.3 The turnover–horizon–power tension (a first-class finding)

The three legs want **incompatible** turnover regimes, and saying so is part of the
product:

- The **decay curve** needs positions held long enough to observe decay: a 65-name
  book retiring 25% of each side per month rarely holds anything past age 4, so its
  decay curve truncates before a 6-month half-life is even visible. Slower turnover
  lengthens the observable curve.
- The **sizing and hit-rate tests** need **many** independent trades, which comes
  from **faster** turnover. A slow book that shows a beautiful long decay curve is
  simultaneously starved of the trades its sizing test needs.

The lab does not resolve this tension; it **reports each leg against its own gate**
and lets the book's actual turnover decide which legs can speak. A high-turnover
quant book powers the sizing test but shows a short decay curve; a patient
concentrated book shows a long decay curve but cannot power the sizing test. Both
facts are shown, neither is hidden.

### 6.4 Power & validation plan

Validation runs on the simulator, whose dials — `information_coefficient` (picking),
`alpha_half_life_months` (decay), `sizing_discipline` (sizing), `rebalance_fraction`
(turnover) — **are** the ground truth the lab must recover. Cells contribute to the
X1 atlas as this card's P-tier rows. Grid follows the atlas convention: IC × half-
life × sizing discipline × turnover × T ∈ {24,36,48,60,120}, ≥1,000 seeded
replications per cell (per-module RNG streams; Wilson 95% intervals on every rate).

**The gate quantity is independent trades**, exactly as the X1 grid defines it:
`independent_trades(T) = (n_long + n_short) + round(turnover·n_long) +
round(turnover·n_short)) · T`. For the atlas book (65 names, 25% turnover) that is
**833 trades at T=48 and 1,985 at T=120**; for a concentrated 30-name low-turnover
book, **174 in four years**.

Acceptance gates:

1. **Dial recovery (the load-bearing gate).** The sizing slope must be monotone
   increasing in `sizing_discipline` and the fitted half-life must track
   `alpha_half_life_months` within tolerance when pooled. Measured: the ages-1-to-12
   half-life fit lands at **6.04 months against a 6.0 truth** (§5); the sizing slope
   separates discipline-0.9 from discipline-0.0 books cleanly at high trade counts.
   If a statistic does not recover its dial monotonically, it is decoration and is
   demoted to descriptive.
2. **Sizing-slope power curve, cited from X1.** At a **strong** sizing effect
   (disciplined sizing on a high-IC book) the slope reaches 80% power at roughly
   **640–830 independent trades** (measured power 0.77 at 641 trades, 0.93 at 1,025,
   0.99 at 1,985) — consistent with the atlas ~780-trade headline. At the atlas
   **reference** effect (realized IR ≈ 0.65) the slope **never** clears 80% within
   T ≤ 120 (measured power 0.29 at 1,025 trades, 0.43 at 1,985) — the atlas-certified
   ∞ threshold. Both are reported; the gate is set to whichever effect the demo pins.
3. **Interval calibration.** The cluster-bootstrap intervals on the slope and the
   half-life must attain their nominal coverage on simulated ground truth (a 95%
   interval covers the true dial 95% of the time, within Monte-Carlo error). A naive
   (non-clustered) interval is reported alongside to show the inflation it hides —
   the same "show the correction, do not assert it" discipline as M3's pointwise-vs-
   familywise gate.
4. **Zero-skill size discipline.** At `information_coefficient = 0` the sizing slope
   and hit rate must sit at their null (slope ≈ 0, hit rate ≈ 0.5) using the equal-
   weight-counterfactual contribution $w(\tilde r - \bar{\tilde r})$; the X1 grid
   ruling documents that raw $w\tilde r$ carries a spurious positive bias here, which
   the counterfactual removes.

**Simulator dependency (honest).** The sizing leg runs on the **v1 simulator today**
(`sizing_discipline` is real ground truth and `x_metrics.sizing_slope` already
recovers it). The **decay and holding legs do not**: v1's idiosyncratic returns are
serially independent, so a held name earns its entire expected alpha in its entry
month and **zero** thereafter — the `alpha_half_life_months` dial governs signal
freshness for re-selection and re-sizing, not the persistence of a held position's
return. Recovering a half-life from an event-time decay curve therefore requires the
**`alpha_persistence` extension** of §6.5. This is a **named validation
prerequisite**, small and opt-in, exactly as M3 declared `death_month` — not assumed
present.

### 6.5 The named simulator extension: `alpha_persistence`

The decay and holding legs need held positions to carry a **decaying** edge, which
v1 does not model. The extension adds one dial to `ManagerConfig`:

- **`alpha_persistence: float = 0.0`** (a **NUMERICS-GATE** named constant; demo
  default **0.5**). When `> 0`, a held name's realized idiosyncratic return gains a
  deterministic edge `alpha_persistence · side · 0.5^(age/half_life) · idio_vol`
  each month it is held, so a name entered on a strong signal keeps earning a
  decaying fraction of that edge. `alpha_persistence = 0.0` is the **byte-identical**
  v1 manager (the added term is zero, no RNG is consumed, honest-manager output is
  unchanged) — the same opt-in discipline as `death_month` and `net_drift`.

With the extension on, the decay curve recovers the dialled half-life (§5); with it
off, the curve correctly shows a spike-at-entry-then-zero, which is the *true*
(instantaneous) decay of the v1 book — itself an honest finding, but not one that
exercises a half-life.

### 6.6 Kill criteria

- **Statistical — the gate does its job.** If a manager's independent-trade count
  falls below the metric's X1 threshold, the panel renders **"insufficient N"** with
  the count and the threshold, and **no number** — the concentrated-book refusal of
  §5. This is not a failure mode; it is the specified behaviour. The card is *killed*
  only if, in validation, the gated statistics fail to recover their dials even at
  high trade counts (gate 1) — in which case the offending leg ships descriptive-only
  or is cut in writing (converge-or-cut).
- **Statistical — decay unresolved.** If the decay curve's positions thin out before
  a half-life can be fit (short holding, low breadth), the lab reports the **entry-
  month alpha only** and states "holding-decay unresolved at this turnover," never a
  fitted half-life the data cannot support.
- **Political — the most sensitive analytic in the portfolio.** Sizing and holding
  feedback to an external manager is **adjustable-output only** (Dietvorst): the
  factor set, the age buckets, and the counterfactual are controls the manager can
  move, and the copy is help-not-audit ("here is what your conviction added," never
  "your sizing is wrong"). An **inverted-sizing** finding (a negative slope — the
  manager's bigger bets earned *less*) is the single most delicate output; it ships
  **only** inside an established E1 ladder relationship, framed as a shared question,
  and never as a mechanical redemption trigger (Goodhart, Sweep E).

### 6.7 Adoption & packaging

- **Manager-facing, help-framed, in the QBR.** The lab is engagement material for
  transparent managers, delivered inside the E2 pack at review cadence — not a
  standing dashboard. The sizing curve opens the highest-value, least-threatening
  conversation ("your picks are real; here is the conviction premium you are not
  capturing"), which is why the card's senior-role score is a 5.
- **Every number gated and interval-reported.** No bare slope, no bare hit rate, no
  bare half-life; each renders as an IntervalStat with a VerdictChip and a PowerGate,
  and below threshold the PowerGate refuses. A bare point is a design-system lint
  error.
- **Who sees what, when:** the investment team sees the full lab at underwriting for
  high-turnover books that clear the gate; a manager sees their own lab inside the E1
  relationship, adjustable-output only; leadership sees the one-line verdict
  ("picks real, sizing flat — coach") rather than the trade-level internals.

### 6.8 Go-live requirements

- **Data ask:** tier **P** — dated position snapshots (signed weights) and trades
  (entry/exit dates), plus factor returns for the idiosyncratic adjustment.
- **Sample required:** a book whose turnover and tenure clear the metric's X1 gate —
  roughly **≥780 independent trades** for the sizing/hit-rate legs (a 65-name,
  25%-turnover book reaches this in ~3–4 years; a concentrated 30-name book **never**
  clears in five). The decay leg additionally needs holding periods long enough to
  observe the curve (§6.3).
- **Build effort:** **M** (card estimate) — the sizing leg reuses the X1
  `sizing_slope` kernel; the decay/holding legs and the cluster bootstrap are new
  pure functions; the `alpha_persistence` simulator extension is the only new
  generative code.
- **Go-live box (demo page):** data ask = positions + trades (P); sample = ≥780
  independent trades (high-turnover book); effort = M; needs the `alpha_persistence`
  simulator extension for decay/holding validation.

### 6.9 How it ships in the repo

- **Reuse, do not reimplement.** The sizing slope **is** the X1 grid's
  `demo_data/x_metrics.py::sizing_slope` Fama–MacBeth kernel (month-clustered SE, per
  the 2026-07-07 gate ruling); S3 imports it. The trade-count gate quantity is the X1
  grid's `_independent_trades`, and the thresholds come from the **X1 PowerGate
  registry** (`site/data/powergate_registry.json`) — S3 reads it, never hand-copies a
  number.
- **New module `src/quant_allocator/flagships/sizing_lab/pipeline.py`:** pure
  functions over a position panel — `decay_curve(panel) -> DecayCurve`,
  `fit_half_life(curve) -> HalfLifeEstimate`, `holding_decomposition(panel, buckets)
  -> dict`, and `cluster_bootstrap(statistic, panel, axes, n) -> Interval` (the
  §3.7 date, and later date×name, resampling). No rendering, no I/O.
- **Consumes the simulator:** `simulator/manager.py` (positions/trades with the
  `information_coefficient`, `alpha_half_life_months`, `sizing_discipline`,
  `rebalance_fraction` dials, plus the new `alpha_persistence`) and
  `simulator/tiers.py::emit_tiers` (the P-tier `transparency` position frame).
- **Demo — `src/quant_allocator/demo_data/s3_lab.py`** (imports the pipeline; same
  code path as any live build, only the input data is synthetic). Emits committed
  JSON to `site/data/s3_lab.json` via `_emit.write_json`; **CI renders the page from
  that JSON only — CI never computes** (demo-layer doctrine). **numpy only** for the
  demo; no new runtime dependency.
- **Provisional constants (NUMERICS-GATE):** `alpha_persistence` (demo default 0.5),
  `HOLDING_BUCKETS` ({0–2, 3–5, 6–11, 12+}), `SIZING_BOOTSTRAP_N` (2,000),
  `CLUSTER_AXES` (date in demo, date×name live), `DECAY_MAX_AGE` and
  `MIN_ENTRIES_PER_AGE` (the per-age render floor). Each is a named constant flagged
  in-text for the numerics gate.

## 7. Deeper reading

**Canonical references (read in this order):**

1. **Fama & MacBeth (1973), "Risk, Return, and Equilibrium," *JPE*.** The estimate-
   monthly-then-average procedure and its month-clustered standard error — the
   backbone of the sizing-slope inference and the reason a pooled regression's
   t-statistic overstates the evidence.
2. **Clarke, de Silva & Thorley (2002), "Portfolio Constraints and the Fundamental
   Law," *FAJ*.** The transfer coefficient TC in $\text{IR}=\text{IC}\sqrt{\text{BR}}
   \,\text{TC}$: the sizing curve is an empirical read on TC, and a flat slope is a
   low TC — good picks poorly transmitted into sizes.
3. **Grinold & Kahn, *Active Portfolio Management*.** The fundamental law and the
   breadth axis — why discriminating power scales with independent bets and a
   concentrated book is evidence-starved.
4. **Gârleanu & Pedersen (2013), "Dynamic Trading with Predictable Returns and
   Transaction Costs," *JF*.** Alpha decay sets the optimal holding period — the
   decision the decay curve and holding decomposition inform.
5. **Cameron, Gelbach & Miller (2011), "Robust Inference with Multiway Clustering,"
   *JBES*.** The two-way (date × name) cluster-robust variance — the live-build
   interval that keeps neither overlapping positions nor common months from being
   miscounted as independent evidence.

**Derivations to own (work each by hand once):**

1. **The Fama–MacBeth slope and its SE** (§3.4): show that averaging monthly cross-
   sectional slopes and taking the standard error from their spread gives a variance
   robust to within-month correlation — and why the pooled OLS SE understates it
   (the X1 grid measured ~40% at this estimator).
2. **The equal-weight counterfactual removes the net-long bias** (§3.3): show that
   $w\tilde r$ has a spurious positive expectation at zero skill for a net-long book,
   while $w(\tilde r - \bar{\tilde r})$ does not.
3. **Half-life from a log-linear fit** (§3.5): from $D(m)=D_1\,2^{-(m-1)/H}$ recover
   $H = -\ln 2 / \text{slope}$ of $\log D$ on age, and explain why fitting from age 1
   (not 0) removes the entry-selection premium — the 5.5-vs-6.04 month difference in
   §5.
4. **The independent-trade count and the ~780 number** (§6.4, X1 §3.3): derive the
   one-sample binomial sample size to separate a 55% hitter from a coin at 80% power,
   and map it to the turnover a book needs to reach it in a given tenure.

**Questions you should be able to answer after reading this page:**

- **Tell the picker from the sizer to a non-quant.** Two managers hold the identical
  names; one posts 12% alpha, the other 8%. Why? — because one sizes its conviction
  and the other equal-weights, and the sizing curve (bigger bets earned more, on
  evidence that clears the trade gate) is the whole difference. Why is that a coaching
  conversation, not a redemption?
- **Why a pooled sizing regression lies.** Explain that positions in a month share
  shocks, so a pooled t-statistic counts correlated observations as independent and
  overstates significance — and how Fama–MacBeth and the cluster bootstrap fix it.
- **Why the decay curve and the sizing test want opposite books.** Explain the
  turnover–horizon–power tension: slow turnover shows a long decay curve but starves
  the sizing test of trades; fast turnover powers the sizing test but truncates the
  decay curve.
- **Why v1 cannot show alpha decay, and what the extension buys.** Explain that
  serially-independent idiosyncratic returns mean a held name earns everything at
  entry, so the half-life dial acts on signal freshness, not held-return persistence —
  and why the `alpha_persistence` extension is the honest prerequisite for a decay
  curve with ground truth.
- **State what the lab refuses to say.** For a concentrated book below the trade gate,
  the honest output is "insufficient N," not a hit rate — and why quoting the point
  number would be the bare-point sin the house forbids.

## 8. Method-review gate rulings (2026-07-07)

1. **`CLUSTER_AXES` — date-only in the demo, date×name (Cameron–Gelbach–Miller)
   live**, as proposed in §3.7. The page states which axis is in force.
2. **Which effect pins the sizing PowerGate: the demo's own (strong) effect.**
   The demo book is dialled to a strong sizing effect (discipline 0.9 on
   IC 0.10), so its gate threshold is the strong-effect line (measured power
   0.77 at 641 trades, 0.93 at 1,025 — §6.4 gate 2). The "~780" figure quoted
   in the refusal copy is the *hit-rate* gate and must be attributed to it. The
   page must also state, in one sentence, that at the atlas reference effect
   the sizing slope never clears 80% within T ≤ 120 — so the exhibit cannot be
   read as contradicting the X1 headline. Thresholds are consumed from the X1
   PowerGate registry; S3's atlas cells add the strong-effect sizing row rather
   than hand-copying a number.
3. **`alpha_persistence` approved** as a `ManagerConfig` dial, default **0.0
   byte-identical** (the added term is deterministic — no RNG stream is
   consumed; a dial-guard byte-identity test is mandatory, per the
   `death_month`/`net_drift` precedent). Demo value 0.5 provisional. It is
   deliberately **distinct from S4's `idio_ar1`**: `alpha_persistence` is a
   manager-conditional held-name edge (a free half-life dial for the decay
   curve) and cannot serve S4 — the edge stops at the sale, so a sold name
   carries nothing forward; `idio_ar1` cannot serve S3 — its implied half-life
   is locked to ρ (≈0.76 months at ρ = 0.4), not a free dial. Both ship in the
   batch-2 shared-substrate plan.
4. **Constants confirmed:** `HOLDING_BUCKETS` {0–2, 3–5, 6–11, 12+};
   `SIZING_BOOTSTRAP_N` = 2,000; `DECAY_MAX_AGE` = 12;
   `MIN_ENTRIES_PER_AGE` = 30 provisional (certified at the numerics gate
   against the demo's actual per-age counts).
5. **No shared S3/S4 event-study kernel module in v1** (S4 ruling 4): the
   decay and holding legs live in `flagships/sizing_lab/pipeline.py` as this
   card's own pure functions. Extraction is revisited only if a third consumer
   appears; build tracks stay file-disjoint.
6. **Demo manager names approved** as authored constants in `s3_lab.py`:
   Meridian Arc Capital, Kelso Bay Partners, Thornwood Select (no collisions
   with `roster.py` or other cards' names).
