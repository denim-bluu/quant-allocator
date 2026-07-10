# M6 · 13F Long-Book Intelligence — Method Spec

**Status: Reviewed — method gate passed 2026-07-07 (rulings in §8)**
**Date:** 2026-07-07
**Card:** [`docs/ideas/2026-07-05-idea-cards.md`](../2026-07-05-idea-cards.md) § M6
**Demo:** gallery page `m6.html` (one filer's reported-long timeline + concentration rail + peer-overlap chip + CoverageGate refusal; fully synthetic, §5)

---

## 1. What this is

M6 is a **holdings-literacy layer for public 13F filings**. For a US long-book
manager who files a quarterly Form 13F, it reads the one thing that filing actually
exposes — a longs-only list of US-listed positions, 45 days stale — and turns it into
a small set of honest descriptors: how concentrated the reported book is (top-N weight
and an inverse-Herfindahl effective-breadth count), how long the top positions have
survived (reported-holding persistence, in **quarters**), how much the book overlaps the
other filers in the same universe, and — where a public short-interest feed is wired
in — how crowded the shorts are on the manager's largest longs. Every number is a
**measurement of the reported book**, delivered with the filing's staleness, its
longs-only blindness, and its coverage holes rendered as first-class caveats on the
face of the view.

M6 makes **no return-prediction claim and runs no estimator**. It does not say a
concentrated book will outperform, that a persistent position is a good one, or that
an overlap forecasts an unwind. It says exactly what the free data supports: *this is
what this manager's public long book looked like as of the last filing, this is how it
has changed, and this is how much of the real book that picture is allowed to miss.*
The consumers are the **investment team** (a per-filer holdings panel for monitoring)
and **engagement prep** (concrete, sourced talking points drawn entirely from public
records). The decisions it feeds are **monitor** — a concentration or persistence shift
worth noticing between manager updates — and **engage** — a specific question grounded
in a public filing ("your top position doubled to 68% of your reported book over six
quarters; walk us through that change"), never an accusation and never a redemption
trigger.

## 2. Why we use it

Free quarterly holdings for US long books have existed since 1978, and almost no
allocator mines them **systematically, per manager, over time**. The usual failure is
one of two extremes. The under-use extreme reads a single 13F as a curiosity — "here
is what they own" — and never lines up the quarters to see a book concentrate or a
thesis harden. The over-reach extreme treats 13F as an alpha feed: it back-tests
copycat portfolios, ranks managers on holdings "quality," and quietly forgets that the
data is longs-only, 45 days late, and silent about everything the manager hedges with.
Both waste the resource. The first leaves free, survivorship-free evidence on the
table; the second manufactures precision the data cannot support and gets burned when
the hidden half of the book moves.

M6 is deliberately the disciplined middle. It **industrializes the descriptor** — the
same five reads computed the same way for every filer, every quarter, lined up into a
timeline — so the investment team can see change, not just a snapshot. And it
**refuses to over-claim**: every descriptor ships with the caveats that make it honest
(§3.3, §6.3), and the one honest gate it carries (§3.7) *refuses to render a
concentration verdict at all* when the filing covers too little of the real book. What
this wins over both extremes is a monitoring-and-engagement instrument that a manager
cannot dispute (it is their own public filing) and that an allocator can trust
precisely because it never says more than the data allows.

M6 is the card that **is the public pseudo-P rung**. The transparency-tier ladder the
program is built on runs R (returns) → E (exposures) → P (positions); the richest tier
normally requires a managed-account or a transparency relationship (card
[E1](e1-transparency-ladder.md)). 13F is the one place the outside world hands you a
*position* tier for free — but a badly degraded one, and the whole value of M6 is
metering that degradation instead of pretending it away.

- **Decisions improved:** **monitor** — concentration, persistence, and overlap shifts
  visible between manager updates; **engage** — sourced, public, undisputable talking
  points for a manager conversation.
- **Customer:** investment team (per-filer holdings panel); engagement prep
  (meeting material).

## 3. How it works

### 3.1 The mental model, before any math

A 13F filing is a **heavily redacted photograph of a book, developed six weeks late**.
Start from the manager's real portfolio: long and short positions, US and foreign,
listed equities and swaps and options and cash. A 13F shows you a strict subset of that
photograph — the US-listed *long* equity positions above the reporting threshold, and
nothing else — and it reaches you 45 days after the quarter closed, by which time the
manager may have already moved. So the first discipline of M6 is to be honest about
*what is in the photograph and what has been cropped out*: the shorts are gone, the
non-US book is gone, the derivatives are gone or distorted, and any position under a
confidential-treatment request is gone. Everything M6 measures, it measures on **the
visible crop**, and it labels it as such.

Now line up those crops quarter after quarter for one filer. Three simple things
become visible that a single snapshot hides. **Concentration**: is the reported book
spread across many names or piling into a few? A single sum — the top-N weight — and a
single inverse-Herfindahl number — the effective breadth — answer that, and watching
them across quarters shows a book *concentrating* or *diversifying*. **Persistence**:
which of today's top names have been there quarter after quarter, and which are new?
Counting consecutive quarters held turns the timeline into a reported-holding map — long bars
for positions visible across many filings, short bars for recent additions. **Overlap**: how much does this
filer's reported book resemble the other filers' books in the same universe? A cosine
between two holdings vectors answers that as a descriptive number.

The subtle part is the fourth thing, and it is what keeps M6 honest: **coverage**. The
crop is not the book. If a manager's real long book is mostly US-listed equities, the
13F crop is a faithful picture and the concentration number means something. If the
manager runs most of the book through swaps, or files confidential-treatment requests
on their best ideas, or is largely a non-US book, the crop is a *sliver*, and its
concentration number is the concentration of the sliver, not of the book. M6 measures
that coverage fraction and, below a threshold, **refuses to render a book-level verdict
at all** — because a concentration statistic computed on a fragment is worse than no
statistic, it is a confident wrong one.

### 3.2 A worked toy example

Take one filer over six quarters. The real portfolio at each quarter-end has five
US-listed longs (call them N0–N4), one short (S6), and one non-13(f) long (X7, say a
foreign line below the reporting threshold). The 13F crop drops S6 (short) and X7
(non-reportable), keeps N0–N4, and **renormalizes the survivors to reported
market-value shares** so they sum to 1.

In quarter 1 the five longs are equal-weight, so the reported book is
`{N0: 0.20, N1: 0.20, N2: 0.20, N3: 0.20, N4: 0.20}`. Over six quarters the manager
piles into N0. By quarter 6 the reported book is
`{N0: 0.684, N1: 0.158, N2: 0.079, N3: 0.053, N4: 0.026}`.

Read the concentration off each crop. The **top-3 weight** climbs from **0.600** (Q1)
to **0.921** (Q6). The **Herfindahl index** — the sum of squared shares — climbs from
**0.200** to **0.503**, so the **effective breadth** (its inverse) *falls from 5.00
names to 1.99*. In one sentence: over six quarters a five-name equal-weight book
became, in effect, a two-name book, and the quarter it crossed into single-name
territory is Q4, where N0 first exceeds half the reported book (0.513). That is the
demo's punchline — "the quarter the concentration doubled" — and it is literally true:
the Herfindahl more than doubled, the effective breadth more than halved.

Now the persistence read. Of quarter 6's top three names (N0, N1, N2), **each has been
reported in all 6 quarters** — this is concentration in *existing reported holdings*, not a
rotation into new ones. That distinction is the engagement hook: the book did not
change its mind, it doubled down.

The overlap read. A second filer holds Vesper's *tail* names (N1–N4) but avoids the N0
thesis entirely. The cosine between the two reported books is **0.233** — a modest
overlap: they share the periphery, not the core. (M6 reports this number; it does
**not** turn it into a crowding cap — that is card M4, §3.6.)

The coverage read, and the gate. Vesper's Q6 real long book is N0–N4 plus the non-13(f)
line X7. The 13F crop keeps 90.5% of the true long weight (`coverage = 0.905`), so the
concentration verdict renders with a staleness badge but **passes** the CoverageGate.
Contrast a *fragment* filer whose real book is 60% a single non-13(f) line: the 13F
crop keeps only **20.0%** of the true long weight, and the CoverageGate **refuses** —
the panel shows a coverage warning instead of a concentration number, because
concentrating "the visible 20%" says nothing about the book. Same machinery, opposite
outcome, and the difference is stated on the tin.

(Every number in this paragraph is reproduced from first principles by the §4 code.)

### 3.3 The 13F emitter — what a filing exposes, and what it crops out

Everything M6 computes runs on a **reported long-book vector**: one quarterly snapshot
of the manager's US-listed long positions, renormalized to market-value shares. The
emitter is the transform from a full dated position panel to that vector, and it is
also the exact inventory of what 13F destroys. Given a manager's signed portfolio
weights $w_{n,t}$ (asset $n$, month $t$):

$$
v_n^{(q)} = \frac{\mathbb{1}[n \in \mathcal{E}]\,\max\!\big(w_{n,\,m(q)},\, 0\big)}
{\sum_{k}\mathbb{1}[k \in \mathcal{E}]\,\max\!\big(w_{k,\,m(q)},\, 0\big)}
$$

where:

- $w_{n,t}$ — the manager's **signed** portfolio weight on asset $n$ in month $t$
  (positive long, negative short); the full internal book.
- $q$ — a calendar quarter index; $m(q)$ — the **quarter-end month** the snapshot is
  taken from (13F reports positions as of the last business day of the quarter).
- $\mathcal{E}$ — the set of **13(f)-eligible** securities: US-listed equities and a
  defined list of options/convertibles above the reporting threshold. $\mathbb{1}[n \in
  \mathcal{E}]$ is 1 for a reportable name, 0 otherwise.
- $\max(w_{n},0)$ — the **longs-only** crop: short positions contribute nothing to a
  13F (they are simply invisible).
- $v_n^{(q)}$ — the **reported market-value share** of name $n$ in quarter $q$: the
  longs-only, eligible-only weight, renormalized to sum to 1 over the visible names.

In words: take the quarter-end snapshot, throw away every short and every
non-reportable name, and renormalize what survives. This is a **pure, deterministic
transform** — it draws no random numbers and adds nothing to the generative model, so a
manager who is never viewed through it is byte-identical to one who is (the overlays.py
discipline, §6.6). Four structural distortions are baked into that one formula, and M6
renders each as a caveat on every view:

- **Staleness (the 45-day lag).** A filing for a quarter ending, say, 30 June is due by
  14 August. Every M6 view is therefore labeled with **both** an *as-of* date (quarter
  end) and a *known-at* date (filing), and the panel never implies the book is current.
  The lag is a statutory fact (SEC Rule 13f-1), not a provisional constant.
- **Longs-only blindness.** The $\max(\cdot,0)$ crop means a market-neutral or short-
  heavy book is systematically misrepresented; M6 states plainly that its
  "concentration" is *long-book* concentration and says nothing about net exposure.
- **Coverage holes (CTR and non-US).** Positions under a confidential-treatment request
  (CTR) and the entire non-US and non-equity book fall outside $\mathcal{E}$. This is
  the coverage problem §3.7 meters and gates on.
- **Option-notional distortion (Sweep D).** 13F reports certain options at a value that
  can wildly misstate economic exposure (notional vs delta-adjusted). M6 flags any
  filer whose reported value is option-heavy and **down-weights or excludes** those
  lines rather than treating a notional as a share; the exact rule is provisional,
  flagged **`M6_OPTION_HANDLING` (NUMERICS-GATE)**.

### 3.4 The concentration descriptors

On one reported long-book vector $v^{(q)}$ (which sums to 1 by construction), three
deterministic reads. There is **no distributional model here** — these are exact
functions of a holdings vector, not estimates of a parameter, which is precisely why
M6 is "Robust as measurement" (card §"Power verdict") and carries no small-N power
gate. The honesty lives in the *coverage* of $v$, not in a confidence band on these
numbers.

$$
C_N^{(q)} = \sum_{n \in \text{top-}N(v^{(q)})} v_n^{(q)}, \qquad
H^{(q)} = \sum_{n} \big(v_n^{(q)}\big)^2, \qquad
N_{\text{eff}}^{(q)} = \frac{1}{H^{(q)}}
$$

where:

- $C_N^{(q)}$ — the **top-N weight**: the summed share of the $N$ largest reported
  positions. $N$ is provisional, **`M6_TOP_N` (NUMERICS-GATE, default 5)** — the toy
  in §3.2 uses $N=3$ for a five-name book.
- $H^{(q)}$ — the **Herfindahl–Hirschman index** of the reported book: the sum of
  squared shares. $H = 1$ is a one-name book; $H = 1/K$ is $K$ equal-weight names. It
  is the standard concentration measure and needs no tuning.
- $N_{\text{eff}}^{(q)} = 1/H^{(q)}$ — the **effective breadth**: the number of
  equal-weight names that would produce the same Herfindahl. It is the more legible
  twin of $H$ — "this book is *as concentrated as* two equal positions."

In words: top-N weight answers "how much sits in the biggest few," the Herfindahl
answers "how concentrated overall," and its inverse restates that as an intuitive name
count. Lined up across quarters (§3.5's timeline), the *trajectory* of $N_{\text{eff}}$
is the monitor signal — a book whose effective breadth falls from 5 to 2 is
concentrating, whatever the absolute level.

### 3.5 Reported-holding persistence — quarterly, and deliberately not a decay curve

Line the reported books up as a panel $v^{(1)}, \dots, v^{(Q)}$. For each name in the
**latest** quarter's top-$K$, count how many **consecutive quarters, counting back from
now**, it has been reported (share $> 0$):

$$
\text{QH}_n = \max\Big\{ j \ge 1 : v_n^{(Q-i)} > 0 \ \text{for all}\ 0 \le i < j \Big\}
$$

where:

- $\text{QH}_n$ — **quarters-held**: the length of the current unbroken run of quarters
  in which name $n$ has appeared in the reported book, ending at the latest quarter.
- $K$ — the number of top names tracked, provisional **`M6_PERSISTENCE_TOPK`
  (NUMERICS-GATE, default 10)**; the toy uses $K = 3$.

In words: a long bar means a position visible through many filings; a short bar means a
recently reported position. This turns the timeline into a **reported-holding map**,
and the map is the demo's centerpiece (§5).

This descriptor is **quarterly by construction, and that boundary is load-bearing.**
Card [S3](s3-sizing-decay-lab.md) §6.2 rules that 13F is **too coarse for an alpha-
decay curve**: a 45-day-lagged quarterly snapshot "cannot date entries to the month,"
so it cannot support S3's event-time decay estimator. M6 does **not** contradict that
ruling — it makes the *weaker, coarser* claim S3 explicitly leaves on the table.
Quarters-held is a **count of survival at quarterly granularity**, not an entry-dated
decay rate; it never fits a half-life, never aligns on entry month, and never claims to
measure how alpha decays while held. It answers only "has this name persisted in the
public book," which quarterly data *can* support. Where S3 needs monthly entry dates
and refuses 13F, M6 asks a question 13F can actually answer. The two are complementary,
not competing, and the demo copy says so.

### 3.6 Peer overlap — a descriptor, not a cap

Because every filer in a universe trades the same names, two reported books can be
compared directly. For filers $i$ and $j$ in the same quarter, the **cosine overlap**:

$$
O_{ij} = \frac{\sum_n v_n^{(i)}\, v_n^{(j)}}
{\sqrt{\sum_n \big(v_n^{(i)}\big)^2}\ \sqrt{\sum_n \big(v_n^{(j)}\big)^2}}
$$

where:

- $v^{(i)}, v^{(j)}$ — the two filers' reported long-book share vectors on the shared
  name universe.
- $O_{ij} \in [0, 1]$ — the **cosine overlap**: 1 when the two books are identical up to
  scale, 0 when they share no name. The toy's 0.233 (§3.2) is two books that share their
  tail but not their core. The depth of book compared is provisional,
  **`M6_OVERLAP_DEPTH` (NUMERICS-GATE, default top-25 names)**.

In words: overlap is the angle between two holdings vectors — a purely **descriptive**
crowding read, "how much do these two public long books look alike."

**This is a measurement, not an allocation rule, and the boundary is explicit.** The
program assigns crowding *caps* — the decision to size a book down because it is crowded
— to card [M4](2026-07-05-idea-cards.md) (crowding & overlap radar), which
[P1](p1-allocation-uncertainty.md) §6.1 routes there. M6 supplies the per-filer
overlap *number* from public 13F data (M4's own "13F rung" consumes exactly this); it
does **not** build a correlation-matrix optimizer, an unwind-stress scenario, or a
sizing cap. M6 measures overlap; M4 decides what to do about it. Keeping M6 to the
measurement is what keeps it a Robust card rather than a predictive one.

### 3.7 Coverage and the CoverageGate — the honest refusal

The Interval doctrine requires a working gate that **refuses to render below a
threshold**. For an estimation card that gate is statistical power; M6 runs no
estimator, so its gate is **coverage** — the fraction of the true long book the 13F
crop actually captures:

$$
\rho_i^{(q)} = \frac{\sum_n \mathbb{1}[n \in \mathcal{E}]\,\max\!\big(w_{n}^{(i)},0\big)}
{\sum_n \max\!\big(w_{n}^{(i)},0\big)}
$$

where:

- $\rho_i^{(q)}$ — the **coverage ratio**: the share of filer $i$'s true long-book
  weight that lands inside the 13(f)-eligible set. $\rho = 1$ is a fully visible long
  book; $\rho \to 0$ is a book 13F barely sees.
- The numerator is the **visible** long weight (eligible names only); the denominator is
  the **true** long weight — every long position the manager actually holds, reportable
  or not. Shorts appear in neither.

**Distributional note — the one place M6 is not exact.** In the *demo*, the denominator
is known: the simulator hands us the true book, so $\rho$ is computed exactly, and that
is precisely why a synthetic demo can *show what 13F misses* rather than assert it. In
*live* data the denominator is unobservable — you cannot see the positions the filing
hides — so live coverage is **inferred**, not measured: from the count and value of
reported lines against any E-tier gross the manager discloses, from the presence of CTR
amendments, and from the option-notional share (§3.3). Live $\rho$ is therefore itself
uncertain, and the gate is set conservatively. The threshold is provisional,
**`M6_COVERAGE_MIN` (NUMERICS-GATE, default 0.60)**.

The gate: when $\rho_i^{(q)} <$ `M6_COVERAGE_MIN`, M6 **refuses the concentration and
overlap verdicts** and renders a coverage warning in their place. The reasoning is the
§3.1 point made precise: top-N weight, Herfindahl, and cosine overlap on a book that is
mostly hidden are confidently wrong, and a confident wrong number is worse than an
honest refusal. Persistence (§3.5) survives the gate as a hedged descriptor — "these
*visible* names have persisted" — because a survival count does not pretend to
characterize the whole book. This gate is the M6 analog of every other card's
PowerGate, and it is genuinely demonstrable on the simulator, where the true book is
known.

### 3.8 Short-interest stress on top longs — a deferred, named lens

The card lists **FINRA short-interest on the top longs** as a descriptor: a crowding-
stress lens that reads days-to-cover $\text{DTC}_n = \text{SI}_n / \text{ADV}_n$ (short
shares outstanding over average daily volume) on the manager's largest positions, so a
crowded-short name in the top book is flagged as squeeze/unwind-fragile.

M6 treats this exactly as card [S5](s5-short-book-quality.md) treats its borrow-
crowding lens (§6.4–6.5): the FINRA short-interest feed is a **deferred adapter**, and
the demo **does not fabricate it**. S5's discipline is that a squeeze/crowding panel is
either built on the real public feed or carried as an honest gap, never faked — and M6
adopts it verbatim, because inventing a public data series is the one thing an
honest-mockup contract cannot allow. So in v1 M6 **names the FINRA short-interest
adapter as a prerequisite** for this lens and ships the descriptor as the first live
extension; the synthetic demo carries the top-longs list with a "requires FINRA
adapter" TierBadge in the slot rather than a made-up days-to-cover number. And, like
S5, M6 makes **no squeeze prediction**: days-to-cover is a stress *context* on a
crowded long, not a forecast. The flag threshold, when the adapter lands, is
provisional **`M6_DTC_FLAG` (NUMERICS-GATE)**.

### 3.9 What the canonical papers contribute

- **Griffin & Xu (2009), "How Smart Are the Smart Guys? A Unique View from Hedge Fund
  Stock Holdings," *Review of Financial Studies*.** Used 13F holdings to evaluate hedge-
  fund stock selection and found only weak evidence of superior picking — but its
  lasting contribution to M6 is its careful catalog of 13F's *limits*: quarterly
  frequency, the 45-day lag, longs-only coverage, and the difficulty of inferring skill
  from a cropped book. M6's "measurement, never prediction; caveats first" posture is
  this paper's discipline made into a product rule.
- **Agarwal, Jiang, Tang & Yang (2013), "Uncovering Hedge Fund Skill from the Portfolio
  Holdings They Hide," *Journal of Finance*.** Studied the positions funds *withhold*
  via confidential-treatment requests and showed the hidden book differs systematically
  from the disclosed one. This is the direct warrant for M6's coverage construct (§3.7)
  and the CTR caveat (§3.3): the crop is not the book, the omission is not random, and a
  concentration number on the visible slice can badly misstate the whole.
- **Verbeek & Wang (2013), "Better than the Original? The Relative Success of Copycat
  Funds," *Journal of Banking & Finance*.** Showed that portfolios replicated from
  disclosed 13F holdings capture much of the original's return but decay because of the
  45-day disclosure lag — the book you can see is not the book that is being traded.
  This grounds M6's staleness caveat (§3.3) quantitatively: it is *why* every view
  carries both an as-of and a known-at date and makes no currency claim.
- **Kacperczyk, Sialm & Zheng (2005), "On the Industry Concentration of Actively
  Managed Equity Mutual Funds," *Journal of Finance*.** Built holdings-based
  concentration measures (industry Herfindahls) from disclosed positions and treated
  concentration as a meaningful, measurable book characteristic. M6 borrows the
  *measurement* (the Herfindahl on reported shares, §3.4) while deliberately declining
  the *predictive* step — M6 reports concentration, it does not claim concentration
  forecasts returns.
- **Brunnermeier & Nagel (2004), "Hedge Funds and the Technology Bubble," *Journal of
  Finance*** (secondary). Read 13F holdings as a window into what sophisticated managers
  were actually doing through the bubble. The methodological lesson M6 takes is that a
  quarterly holdings panel, lined up over time, is a legitimate lens on *behavior* — how
  a book changed — even where it is a poor lens on *skill*.

## 4. How to implement

The reference implementation below is **self-contained teaching code** — paste it into
a fresh file, it runs on `numpy` alone, with no project imports and no repo paths. It
implements the same operations as §3: the 13F emitter (§3.3), the concentration
descriptors (§3.4), reported-holding persistence (§3.5), cosine peer overlap (§3.6), and the
coverage ratio the CoverageGate reads (§3.7). Short-interest stress (§3.8) is
deliberately absent — it is the deferred FINRA adapter, not faked here. Running the
file reproduces every number in the §3.2 worked example.

```python
"""Self-contained 13F long-book intelligence (teaching code). numpy only.

Turns a manager's dated signed-weight panel into the quarterly, 45-day-lagged,
longs-only view a 13F filing exposes, then computes the M6 descriptors:
top-N concentration, HHI / effective breadth, reported-holding persistence, peer
overlap, and the coverage ratio the CoverageGate reads. No project imports.
"""

import numpy as np


# ---------------------------------------------------------------------------
# 1. The 13F emitter: a PURE transform of an existing signed-weight panel.
#    Keep quarter-end snapshots, drop non-longs, drop non-13(f) names, and
#    renormalize the survivors to reported market-value shares. Draws no RNG,
#    so a manager that never opts in is byte-identical (overlays.py discipline).
# ---------------------------------------------------------------------------
def emit_13f_long_book(signed_weights, quarter_end_rows, eligible_mask):
    """signed_weights : (n_months, n_assets) signed portfolio weights.
       quarter_end_rows: indices of the calendar quarter-end months.
       eligible_mask   : (n_assets,) bool, True where the name is 13(f)-reportable.
       Returns (n_quarters, n_assets) renormalized long-only reported shares.
    """
    snaps = signed_weights[quarter_end_rows, :]           # down-sample to quarterly
    longs = np.clip(snaps, 0.0, None)                     # longs only (shorts invisible)
    longs = longs * eligible_mask                         # non-13(f) names invisible
    totals = longs.sum(axis=1, keepdims=True)
    return np.divide(longs, totals, out=np.zeros_like(longs), where=totals > 0)


# ---------------------------------------------------------------------------
# 2. Concentration descriptors on one reported long book (one quarter).
# ---------------------------------------------------------------------------
def top_n_weight(book, n):
    """Sum of the n largest reported shares (top-N concentration)."""
    return np.sort(book)[::-1][:n].sum()


def hhi(book):
    """Herfindahl-Hirschman index of the reported book: sum of squared shares."""
    return float((book ** 2).sum())


def effective_names(book):
    """Effective breadth = 1 / HHI (the inverse-Herfindahl name count)."""
    h = hhi(book)
    return float("inf") if h == 0 else 1.0 / h


# ---------------------------------------------------------------------------
# 3. Reported-holding persistence: consecutive quarters each current top-K name has
#    been reported, ending at the latest quarter. Quarterly granularity only --
#    this is NOT an entry-dated decay curve (that is card S3, ruled out here).
# ---------------------------------------------------------------------------
def reported_holding_persistence(book_panel, top_k):
    """book_panel: (n_quarters, n_assets). Returns {asset_index: quarters_held}
    for the top_k names of the final quarter (held = reported share > 0)."""
    final = book_panel[-1]
    top = np.argsort(final)[::-1][:top_k]
    held = book_panel > 0.0
    out = {}
    for name in top:
        run = 0
        for q in range(book_panel.shape[0] - 1, -1, -1):
            if held[q, name]:
                run += 1
            else:
                break
        out[int(name)] = run
    return out


# ---------------------------------------------------------------------------
# 4. Peer overlap: cosine similarity of two reported long books. Descriptive
#    only -- M6 measures overlap; the crowding CAP is card M4/P1, not here.
# ---------------------------------------------------------------------------
def cosine_overlap(book_a, book_b):
    denom = np.linalg.norm(book_a) * np.linalg.norm(book_b)
    return 0.0 if denom == 0 else float(book_a @ book_b / denom)


# ---------------------------------------------------------------------------
# 5. Coverage ratio: fraction of the TRUE long book (by weight) the 13F filter
#    keeps. In live data the denominator is unobservable and coverage is
#    inferred; on the simulator the true book is known, which is exactly why
#    the demo can show what 13F misses. The CoverageGate refuses a concentration
#    verdict when this falls below M6_COVERAGE_MIN.
# ---------------------------------------------------------------------------
def coverage_ratio(true_signed_weights, eligible_mask):
    true_long = np.clip(true_signed_weights, 0.0, None)
    total = true_long.sum()
    visible = (true_long * eligible_mask).sum()
    return 0.0 if total == 0 else float(visible / total)


M6_TOP_N = 3             # provisional -- NUMERICS-GATE (default 5 in the live build)
M6_PERSISTENCE_TOPK = 3  # provisional -- NUMERICS-GATE (default 10 in the live build)
M6_COVERAGE_MIN = 0.60   # provisional -- NUMERICS-GATE


if __name__ == "__main__":
    # Six 13(f)-eligible longs (N0..N4), one short (S6), one non-13(f) long (X7).
    assets = ["N0", "N1", "N2", "N3", "N4", "S6", "X7"]
    eligible = np.array([1, 1, 1, 1, 1, 1, 0], dtype=float)  # X7 is not 13(f)-reportable

    # 18 monthly signed-weight rows; constant within each quarter for legibility.
    # Quarter-end months are rows 2, 5, 8, 11, 14, 17 (0-indexed).
    quarterly_signed = np.array([
        #  N0    N1    N2    N3    N4     S6     X7
        [0.16, 0.16, 0.16, 0.16, 0.16, -0.30, 0.08],  # Q1 -- diversified longs
        [0.20, 0.18, 0.16, 0.14, 0.12, -0.30, 0.08],  # Q2
        [0.30, 0.16, 0.14, 0.10, 0.08, -0.30, 0.08],  # Q3
        [0.40, 0.14, 0.10, 0.08, 0.06, -0.30, 0.08],  # Q4
        [0.48, 0.12, 0.08, 0.06, 0.04, -0.30, 0.08],  # Q5
        [0.52, 0.12, 0.06, 0.04, 0.02, -0.30, 0.08],  # Q6 -- concentrated into N0
    ])
    signed_weights = np.repeat(quarterly_signed, 3, axis=0)   # expand to 18 months
    quarter_end_rows = [2, 5, 8, 11, 14, 17]

    book_panel = emit_13f_long_book(signed_weights, quarter_end_rows, eligible)

    print("Reported long book (renormalized shares, S6 short + X7 non-13f dropped):")
    for q, row in enumerate(book_panel, 1):
        shares = {assets[i]: round(float(v), 3) for i, v in enumerate(row) if v > 0}
        print(f"  Q{q}: {shares}")

    print("\nConcentration by quarter:")
    for q, row in enumerate(book_panel, 1):
        print(f"  Q{q}: top-{M6_TOP_N} weight={top_n_weight(row, M6_TOP_N):.3f}  "
              f"HHI={hhi(row):.3f}  effective_names={effective_names(row):.2f}")

    print("\nReported-holding persistence (quarters held, final-quarter top-3):")
    for name, qh in reported_holding_persistence(book_panel, M6_PERSISTENCE_TOPK).items():
        print(f"  {assets[name]}: {qh} quarters")

    # Peer overlap: a second filer that shares Vesper's TAIL names but avoids the
    # N0 thesis -- "same tail, different thesis", a moderate descriptive overlap.
    peer_signed = np.array([0.00, 0.30, 0.20, 0.30, 0.20, -0.20, 0.00])
    peer_book = emit_13f_long_book(peer_signed.reshape(1, -1), [0], eligible)[0]
    print(f"\nPeer cosine overlap (Vesper Q6 vs peer): "
          f"{cosine_overlap(book_panel[-1], peer_book):.3f}")

    # Coverage: Vesper's true book (X7 is a real long but invisible to 13F).
    cov = coverage_ratio(quarterly_signed[-1], eligible)
    gate = "PASS" if cov >= M6_COVERAGE_MIN else "REFUSE"
    print(f"\nCoverage ratio (Vesper Q6): {cov:.3f}  CoverageGate={gate} "
          f"(min={M6_COVERAGE_MIN})")

    # A fragment filer: most of the book is non-13(f), so 13F sees a sliver.
    frag_signed = np.array([0.10, 0.05, 0.0, 0.0, 0.0, -0.20, 0.60])  # X7 dominates
    frag_cov = coverage_ratio(frag_signed, eligible)
    frag_gate = "PASS" if frag_cov >= M6_COVERAGE_MIN else "REFUSE"
    print(f"Coverage ratio (fragment filer): {frag_cov:.3f}  CoverageGate={frag_gate}")
```

Running the file prints the reported book concentrating from an effective breadth of
**5.00 names (Q1)** to **1.99 names (Q6)** — Herfindahl 0.200 → 0.503, top-3 weight
0.600 → 0.921 — the top-3 names each held all **6 quarters**, a peer cosine overlap of
**0.233**, Vesper's coverage **0.905 (PASS)**, and the fragment filer's coverage
**0.200 (REFUSE)**: §3.2's worked example reproduced from first principles, and the
CoverageGate refusing exactly where the book is mostly hidden.

## 5. Reading the demo

The gallery page `m6.html` is fully synthetic (§6 compliance): the "filers" are
simulator managers viewed through the §3.3 emitter, with a **SYNTHETIC** badge and a
standing note that real filings would come from the SEC EDGAR 13F feed. The primary
filer is **Vesper Lane Capital**; the peer set is **Corbin Vale Capital, Bexley Court
Capital, Tanager Hill Capital, Kettering Partners, and Hensley Park Advisors** (authored
fictional names, §6). The page has four parts.

**The reported-long timeline — the centerpiece.** A quarter-by-quarter view of Vesper
Lane's reported top book: a row per top position, a column per quarter, each cell a
reported share, and each name's bar shaded by its **quarters-held** run (§3.5). Two
things are meant to jump out. First, the book *concentrates*: the effective breadth
annotation falls from **6.92 names to 2.78** across six quarters, while the Herfindahl
more than doubles from **0.144 to 0.360**. The panel marks **Q6 as the quarter the top
name (A0001) first crossed 50% of the reported book, reaching 56.1%** — "the quarter
the concentration doubled." The fully synthetic exhibit illustrates what a live adapter
could derive from free filing data; the displayed values do not come from a public feed.
Second, the concentration is a *hardening of existing reported holdings*: the latest top-3 names
(A0001, A0065, and A0038) each
carry a full **6-quarter** held bar, so this is doubling-down, not rotation. That is the
engagement hook, stated as a question, never an accusation.

How each visual element maps to the method:

- **The effective-breadth rail** = the §3.4 inverse-Herfindahl $N_{\text{eff}}$, plotted
  per quarter; the "top-5 weight" figure beside it is $C_N$. Both carry the as-of /
  known-at date pair and a **45-day-lag TierBadge** — the point is never bare.
- **The quarters-held shading** = the §3.5 persistence count; a long bar is an old
  position reported across many quarters, a short bar a recent addition.
- **The peer-overlap chip** = the §3.6 cosine against the pooled peer book — Vesper's
  **0.244** reads "shares the tail, not the thesis." The chip explicitly says *this is a
  descriptive overlap; crowding caps are card M4*, so no reader mistakes it for a sizing
  rule.
- **The short-interest slot** = a top-longs list with a **"requires FINRA adapter"
  TierBadge** in place of any days-to-cover number (§3.8) — the honest gap, not a faked
  panel.

**The CoverageGate contrast.** A second card shows a *fragment* filer (Hensley Park Advisors)
whose real book is mostly non-13(f): coverage **0.20**, below the `M6_COVERAGE_MIN`
line, so the concentration and overlap verdicts **refuse to render** and the panel shows
a coverage warning instead. Placed beside Vesper's **0.822 (renders, with a staleness
badge)**, this is the whole honesty of the card in one comparison: 13F is a usable
position tier for one filer and a mirage for the other, and M6 tells them apart on the
face of the page.

**The caveat ledger.** A standing panel listing the four structural distortions (§3.3)
as first-class TierBadges — staleness (45-day lag), longs-only, coverage holes
(CTR/non-US), option-notional — so the reader confronts what the free data omits before
reading any number.

**§5 numbers reconciled to the real-pipeline generator output on 2026-07-10.** Relative
to the self-contained teaching example, the committed exhibit moves the breadth endpoints
from 5.0/2.0 to 6.92/2.78, the majority crossing from Q4/N0 to Q6/A0001, pooled overlap
from 0.233 to 0.244, and Vesper coverage from 0.905 to 0.822; Hensley's 0.200 refusal is
unchanged. These deltas remain held for the numerics gate; the generator was not forced
to reproduce the teaching-code figures.

What an allocator should conclude: 13F, mined systematically, turns a manager's own
public filings into concrete monitoring and engagement material — Vesper Lane's book
visibly concentrated into a single reported holding over six quarters — **and** the same
system refuses to speak when the filing hides too much of the book. The value is the
discipline as much as the descriptor.

## 6. Honest limits & go-live

### 6.1 What M6 does not do (do-not-build adjacency)

- **No return prediction, no estimator.** M6 makes no claim that a concentrated,
  persistent, or crowded book predicts returns; it runs no regression and fits no
  parameter (card §"Power verdict": Robust as measurement, predictive use out of scope
  v1). This keeps it clear of the do-not-build list's **persistence rankings** and
  **style-drift inference** — reported-holding persistence (§3.5) is a within-filer survival
  *count*, not a cross-manager persistence ranking or a return-persistence claim.
- **No alpha-decay curve.** M6 respects [S3](s3-sizing-decay-lab.md) §6.2 verbatim: 13F
  is too coarse to date entries to the month, so M6 never fits a decay half-life. It
  makes only the coarser quarterly-survival claim S3 leaves available (§3.5).
- **No crowding cap, no optimizer.** M6 measures peer overlap; it builds no correlation-
  matrix optimizer and sets no sizing cap. Crowding caps belong to card
  [M4](2026-07-05-idea-cards.md) ([P1](p1-allocation-uncertainty.md) §6.1 routes them
  there). M6 is the measurement M4's 13F rung consumes, nothing more (§3.6).
- **No faked public feed.** Following [S5](s5-short-book-quality.md) §6.4, the demo
  fabricates no FINRA short-interest series; the short-interest lens is a named deferred
  adapter (§3.8).

### 6.2 Data contract per tier

M6 is unusual: it **is** the public pseudo-P rung, so the standard R → E → P ladder
does not apply in the normal way. There is no returns-only or exposures-only rung that
*produces* M6 — the card's inputs are holdings, full stop. The tiering instead
describes **how good the holdings picture is**.

| Tier | Inputs the live version needs | What the card produces |
| --- | --- | --- |
| **Public-P (13F, native)** | SEC EDGAR **Form 13F** quarterly filings per filer: as-of date, reported name (CUSIP/issuer), and reported market value; plus a 13(f)-eligibility reference and a shares-outstanding/price source to convert value to share weight. | **The whole card on public data:** the emitter (§3.3), concentration (§3.4), reported-holding persistence (§3.5), and peer overlap (§3.6), each behind the CoverageGate (§3.7), with all four structural caveats (§3.3) rendered. |
| **P (transparent manager)** | The manager's own dated position snapshots (via the [E1](e1-transparency-ladder.md) ladder) — the *full* book, shorts and non-US included. | **Coverage becomes exact and the crop disappears:** the same descriptors on the true book, and — this is the point — a *measured* coverage ratio showing exactly how much the manager's public 13F was missing all along. |
| **+ FINRA** | FINRA bi-monthly short-interest + an ADV source. | The **short-interest stress lens** on top longs (§3.8) — days-to-cover context, no squeeze prediction. Named deferred adapter. |

**Frequency & window.** Quarterly, at the filing cadence, with the 45-day lag rendered
as both an as-of and a known-at date on every view. **Atlas:** n/a — M6 runs no
estimator, so it contributes no power cells (card §"Power verdict"); its honest error
is *coverage/staleness distortion*, audited in §6.4, not a small-N power curve.

**Compliance (standing):** synthetic filers in the repo. Any real-data rung uses public
SEC/FINRA filings of **unaffiliated** managers only — **never** any filer with an
implied relationship to the roster (card §"Risks & kill criteria"). No employer-internal
facts, processes, or manager names in code, docs, or the committed demo JSON.

### 6.3 Coverage & staleness honesty (what the numbers promise, and don't)

Every M6 number is a measurement of the **visible crop**, and the card's honesty is in
never letting that be forgotten:

- **Staleness.** A filing is up to 45 days old the day it lands and older thereafter;
  the book may have turned over. M6 states an as-of and a known-at date and makes no
  currency claim. The [Verbeek & Wang (2013)](#) copycat-decay result is the standing
  reason.
- **Longs-only.** "Concentration" is *long-book* concentration; a short-heavy or
  market-neutral book is systematically misrepresented, and M6 says so on the badge.
- **Coverage holes.** CTR positions and the non-US / non-equity book are invisible; the
  CoverageGate (§3.7) refuses a verdict when they dominate. Live coverage is *inferred*,
  not measured (§3.7), so the gate is set conservatively.
- **Option-notional distortion.** Reported option values can wildly misstate economic
  exposure; M6 flags and down-weights option-heavy lines (`M6_OPTION_HANDLING`, §3.3).

### 6.4 Validation plan — a distortion audit, not a power grid

Because M6 estimates nothing, it has no coverage/rank/calibration gates to pass and
contributes no X1 power cells. What it *can* and *must* validate is **how much the 13F
crop distorts the true book** — and the simulator is uniquely suited to this, because it
knows the true book the crop is taken from. This is the same spirit as the X1 atlas
(measure the error you eat at each transparency tier), applied to the public-P rung.

Validation runs on the multi-manager simulator roster (one market, many managers share
the universe by design). For each synthetic filer, compute each descriptor on **both**
the true long book and the 13F crop, and report the distortion:

1. **Concentration distortion.** Top-N weight and Herfindahl on the crop vs the true
   book, as a function of coverage $\rho$ — quantifying how the longs-only, non-US crop
   biases the concentration read. Expected: the crop *overstates* concentration as
   $\rho$ falls (the denominator shrinks to the visible names).
2. **Persistence distortion.** Quarters-held on quarterly crops vs the true monthly
   holding tenure — confirming the descriptor is honest as a *quarterly survival count*
   and does not smuggle in a finer-grained tenure claim.
3. **Coverage-gate calibration.** Across filers with dialed non-13(f) share, confirm the
   CoverageGate refuses exactly the filers whose true-book descriptors the crop cannot
   recover, and passes the rest — i.e. the gate's refusals are the right refusals.
4. **Staleness sensitivity.** Re-derive each descriptor at the 45-day lag vs a
   contemporaneous snapshot and report how much a quarter of drift moves the numbers —
   the empirical version of the Verbeek–Wang decay caveat.

These are **descriptive audits**, reported as distortion curves against coverage and
lag, not pass/fail power gates. They are M6's contribution to the program's error
accounting — the honest price of the free position tier.

**Simulator dependency (honest).** The audit needs the **13F emitter** as a new,
RNG-free view over the existing `simulate_manager` weights panel (§6.6), plus a
per-asset **13(f)-eligibility mask** and a per-manager **non-13(f) long share** dial so
coverage can be swept. Both are small, named prerequisites — see §6.6.

### 6.5 Kill criteria

- **Data.** If the coverage the 13F crop provides is so thin *for the target manager
  population* that the CoverageGate refuses most filers, M6 ships as a **caveat-and-
  refusal instrument only** — it shows the ledger of what 13F omits and the gate, and
  declines to publish concentration verdicts — recorded in writing per converge-or-cut.
  A concentration number sold on a book 13F barely sees is worse than an honest refusal
  (the whole §3.7 argument). The card's own kill line: 13F staleness/blind spots can
  make the proxy misleading for L/S books — **ship with caveats or not at all** (card
  §"Risks & kill criteria").
- **Political.** M6 uses public filings of **unaffiliated** managers only; any filer
  with an implied relationship to the roster is out of scope in the repo, full stop
  (card §"Risks"). And every output is monitoring/engagement material — "a public fact
  worth a conversation" — never a redemption trigger. If a consumer wires a
  concentration or overlap number to automatic action, the card is pulled.
- **Vendor.** Novus and peers sell holdings analytics; M6 builds **only the
  interpretation layer** on free data (card §"Risks": thin-build verdict). If the build
  drifts toward re-creating a commercial holdings platform, it is descoped back to the
  free-data sanity rung.

### 6.6 How it ships in the repo

The commitment is **reuse the simulator's holdings panel; add only a pure emitter and a
descriptor layer.**

- **New substrate — the 13F emitter (named prerequisite).** `simulate_manager` already
  emits a `weights` DataFrame (month × asset, signed) — M6 needs no new generator, only
  a **pure view** over it: `emit_13f_long_book(weights, quarter_ends, eligible_mask) ->
  reported_shares`, a deterministic down-sample + longs-only + eligible-only +
  renormalize transform. Like `overlays.py`, it **draws no RNG and consumes no stream
  tag**, so a manager never viewed through it is **byte-identical** — this is the gate-
  question-not-hidden discipline the brief requires. Two small companion prerequisites:
  a per-asset **13(f)-eligibility mask** on the market (a boolean over the existing asset
  universe) and a per-manager **non-13(f) long-share dial** (default 0.0 → fully
  visible, byte-identical), so coverage can be swept for §6.4. All are additive with
  byte-identical defaults; none touches the manager/market RNG streams (tags 0/1/2).
- **New module `src/quant_allocator/flagships/holdings13f/pipeline.py`:** pure functions
  over a reported-shares panel — `concentration(book)`, reported-holding persistence,
  `cosine_overlap(a, b)`, `coverage_ratio(true_weights, mask)`, and
  `holdings_view(panel, true_weights, mask, *, coverage_min) -> HoldingsVerdict`
  carrying the descriptors, the as-of/known-at dates, the four caveat badges, and the
  CoverageGate outcome. No rendering, no I/O (S2 §5 convention).
- **Demo — `src/quant_allocator/demo_data/m6_holdings.py`** (imports the pipeline; same
  code path as any live build, only the input data is synthetic). Builds a small roster
  of synthetic filers via `simulate_manager`, views them through the emitter, and emits
  committed JSON to `site/data/m6_holdings.json` via `_emit.write_json`. **CI renders
  the page from that JSON only — CI never computes** (demo-layer doctrine).
- **Multi-manager universe:** already present — one `simulate_market`, many
  `simulate_manager` filers share the asset index, so peer overlap (§3.6) needs no new
  substrate beyond the emitter. (This is the same shared-universe fact card M4 relies
  on; M6 supplies the per-filer 13F rung M4 consumes.)
- **Deferred, named:** the **FINRA short-interest adapter** (§3.8) and, for the live
  build, the **SEC EDGAR 13F parser** — the real work is the parsing (amendments, CTR,
  option/CUSIP handling), per card §"MVP & effort".
- **Effort:** **M** (card estimate). The demo and descriptor layer are small pure
  functions on existing substrate; the emitter is a lift-and-name transform; the live
  build's weight is the EDGAR parser, which is deferred.

### 6.7 Adoption & packaging

- **A per-filer holdings panel, not a standing screen.** M6 surfaces where it is read:
  a per-filer reported-long-timeline panel at monitoring cadence and in engagement prep —
  not a separate always-on holdings dashboard to go stale (Sweep E).
- **Caveats are the pitch, not the footnote.** The four structural distortions (§3.3)
  ride as first-class TierBadges on every view, and the CoverageGate refusal is shown as
  a feature. The honesty is the differentiator against a vendor feed that renders a
  confident concentration number with the caveats buried.
- **Engagement framing, always a question.** "Your reported book concentrated into one
  name over six quarters — walk us through that change," never "you are dangerously
  concentrated." Public, sourced, and undisputable (it is the manager's own filing) —
  which is exactly what makes it good engagement material and bad accusation material.
- **Receipts, dated.** Every number shows its as-of and known-at dates and its caveat
  badges; a bare concentration figure with no staleness/coverage context is a design-
  system lint error.

### 6.8 Go-live requirements (demo-page box, expanded)

- **Data ask:** public **SEC EDGAR 13F** quarterly filings (the pseudo-P tier) + a
  13(f)-eligibility reference + a value-to-shares source; **+ FINRA** short-interest and
  an ADV source for the short-interest lens (deferred adapter). A transparent manager's
  own positions (via E1) upgrades coverage from *inferred* to *exact*.
- **Sample required:** **honest at any history** because every output is a measurement,
  not an estimate — but it is only as good as **coverage** allows, and the CoverageGate
  refuses filers whose 13F hides too much of the book. Several quarters are needed for
  the persistence and concentration *trajectory* (the timeline); a single filing gives
  only a snapshot.
- **Build effort:** **M** — pure descriptor layer on existing substrate for the demo;
  the live build's cost is the EDGAR 13F parser (deferred substrate).
- **Go-live box (demo page):** data ask = public 13F (+ FINRA for the short lens);
  sample = any history, but coverage-gated; effort = M (blocked on the 13F adapter).

## 7. Deeper reading

**Canonical references (read in this order):**

1. **Griffin & Xu (2009), "How Smart Are the Smart Guys? A Unique View from Hedge Fund
   Stock Holdings," *Review of Financial Studies*.** 13F holdings as an evaluation
   window and, more importantly for M6, a careful catalog of the data's limits
   (quarterly, lagged, longs-only). The measurement-not-prediction discipline.
2. **Agarwal, Jiang, Tang & Yang (2013), "Uncovering Hedge Fund Skill from the Portfolio
   Holdings They Hide," *Journal of Finance*.** Confidential-treatment (hidden) holdings
   differ systematically from disclosed ones — the warrant for the coverage construct
   and the CTR caveat.
3. **Verbeek & Wang (2013), "Better than the Original? The Relative Success of Copycat
   Funds," *Journal of Banking & Finance*.** 13F-replicated portfolios decay because of
   the 45-day disclosure lag — the quantitative ground for the staleness caveat.
4. **Kacperczyk, Sialm & Zheng (2005), "On the Industry Concentration of Actively
   Managed Equity Mutual Funds," *Journal of Finance*.** Holdings-based Herfindahl
   concentration as a measurable book characteristic — the measurement M6 borrows while
   declining the predictive step.
5. **Brunnermeier & Nagel (2004), "Hedge Funds and the Technology Bubble," *Journal of
   Finance*** (secondary). A quarterly holdings panel over time is a legitimate lens on
   *behavior*, even where it is a poor lens on *skill*.

**Questions you should be able to answer after reading this page:**

- **State what a 13F crops out, and why it matters.** Shorts, non-US, non-equity, CTR
  positions, and (via the 45-day lag) currency — and why the concentration of the
  visible crop can badly misstate the concentration of the book. Explain the emitter
  formula (§3.3) in words.
- **Herfindahl and effective breadth.** Why $H = \sum v_n^2$ measures concentration, why
  $1/H$ is the "effective number of equal-weight names," and why a fall from 5.0 to 2.0
  means a five-name book became, in effect, a two-name book — working the §3.2 numbers by
  hand once.
- **Why quarterly persistence is not a decay curve.** Explain, citing S3 §6.2, why 13F
  cannot date entries to the month and therefore cannot support an alpha-decay half-life
  — and what the *coarser* quarters-held survival count legitimately claims instead.
- **The CoverageGate as the honest refusal.** Why a measurement card still needs a gate,
  why coverage (not statistical power) is the right gate for M6, why live coverage is
  *inferred* rather than measured, and why refusing on a mostly-hidden book is more
  honest than rendering a confident wrong number.
- **Measurement vs allocation.** Why M6 reports peer overlap but sets no crowding cap,
  and where the cap decision lives (M4, routed by P1 §6.1) — the boundary that keeps M6
  a Robust card.
- **Why no faked short-interest.** Why M6, following S5, names the FINRA feed as a
  deferred adapter rather than fabricating a days-to-cover series, and why days-to-cover
  is a stress *context*, never a squeeze forecast.
- **Explain the wow-demo to a non-quant.** "From this manager's own free public filings,
  their reported book concentrated from five roughly-equal positions into one dominant
  name over six quarters — and the same three names have been there the whole time, so
  it is doubling-down, not churn. And when a filer hides most of their book from 13F, the
  tool refuses to guess — it tells you it cannot see enough."

## 8. Method-review gate rulings (2026-07-07)

1. **`M6_COVERAGE_MIN` = 0.60 confirmed provisional.** The demo computes coverage
   exactly (simulator truth) — that contrast is the exhibit. Live coverage is
   *inferred*; the inference recipe (reported-line value vs any disclosed E-tier
   gross, CTR-amendment presence, option-value share) is a live-build design item
   and the gate stays conservative until it exists.
2. **`M6_OPTION_HANDLING` ruled for v1:** option lines are **excluded** from the
   share computation, and a filer is flagged "option-heavy" when reported option
   value exceeds **`M6_OPTION_FLAG_SHARE` = 0.10 (provisional — NUMERICS-GATE)**
   of total reported value. Delta-adjusted treatment is deferred to the live
   EDGAR build.
3. **Short-interest lens:** ships as the labeled placeholder slot with the
   "requires FINRA adapter" badge — confirmed (the S5 no-fake discipline).
   `M6_DTC_FLAG` is set when the adapter lands, not before.
4. **S3-boundary sign-off granted.** Quarters-held is a quarterly survival count
   at filing granularity; §3.5's defense (never a half-life, never entry-dated)
   is binding page copy.
5. **Substrate approved:** `emit_13f_long_book` as a pure RNG-free view (no
   stream tag — the overlays.py discipline); the per-asset 13(f)-eligibility
   mask is a **deterministic authored assignment** (no RNG draw, so no stream
   tag and no byte-identity risk); the per-manager non-13(f) long-share dial
   defaults to 0.0 byte-identical. All three land in the batch-3 substrate plan.
6. **Constants confirmed:** `M6_TOP_N` = 5, `M6_PERSISTENCE_TOPK` = 10,
   `M6_OVERLAP_DEPTH` = top-25. Demo names approved (Vesper Lane, Corbin Vale,
   Bexley Court, Tanager Hill, Kettering, Hensley Park — no collisions).
