# M4 · Crowding & Overlap Radar — Method Spec

**Status: Reviewed — method gate passed 2026-07-07 (rulings in §8)**
**Date:** 2026-07-07
**Card:** [`docs/ideas/2026-07-05-idea-cards.md`](../2026-07-05-idea-cards.md) § M4
**Demo:** gallery page `m4.html` (roster overlap heat-map + two-manager unwind panel; fully synthetic, §5)

---

## 1. What this is

M4 is a **crowding radar**. It looks across a whole roster of managers who trade
the same name universe and answers one narrow question: *is our diversification
real, or are these managers the same trade wearing different labels?* It does this
by measurement, not inference — it reads each manager's **holdings** (or the best
proxy the data tier allows), computes how much of any two books is literally the
same position, adjusts that overlap for how hard the shared names are to exit, and
then runs a **common-holder unwind scenario**: if every manager crowded into a name
had to sell it at once into a stressed market, how many days of trading volume would
the combined footprint represent? The output is a per-pair overlap number, a roster
heat-map, and an unwind stress panel — each carrying its own caveats about what the
data tier can and cannot see.

The consumers are the **investment team**, who see the book-level overlap between
managers they think of as diversifiers, and **department leadership**, who see the
roster heat-map and the aggregate unwind footprint at the sizing and monitoring
moment. The decisions it feeds are **size** — cap aggregate exposure to a crowded
theme so the roster is not secretly one concentrated bet — and **monitor / redeem**
— crowded, illiquid books are the ones that exit first and worst in a stress, so a
high liquidity-adjusted overlap is a standing flag. M4 **measures** crowding; it does
not **allocate**. It hands its overlap numbers to the P1 allocation card as an input
constraint (a crowding cap), and it never computes weights itself. Everything M4
produces is a point-in-time measurement delivered to a human, with the reliability of
each rung stated on its face.

## 2. Why we use it

An allocator's whole premise is diversification: a dozen managers, a dozen
independent edges, a portfolio steadier than any one of them. That premise is a
**hypothesis about holdings** — and it is routinely false in ways returns cannot
show you until it is too late. Two "diversifying" managers can run substantially the
same book: the same handful of high-conviction longs, the same crowded short. On the
way up nothing looks wrong — both post good numbers, their return correlation is
unremarkable, the roster looks balanced. The danger is entirely in the **exit**: when
a crowded, illiquid trade turns, every holder reaches for the same door at once, and
the combined footprint moves days of volume against itself. That is the mechanism
behind the sharpest hedge-fund drawdowns on record — the August 2007 quant unwind is
the canonical case — and it is invisible to any monitor that looks only at returns.

The naive alternatives fail for reasons worth stating plainly. *Look at return
correlations between managers.* At 36–60 monthly observations a pairwise manager
return correlation is mostly noise (the same small-sample problem the P1 spec §3.2
dissects for the covariance matrix), and worse, it is a **lagging** signal — the
correlation only spikes once the crowd has already co-moved, which is exactly the
moment you needed the warning a quarter earlier. *Trust the strategy labels.* Two
managers filed under "equity long/short" and "event-driven" can hold the same names;
the label is not the book. *Buy a crowding feed.* Vendor crowding products exist
(MSCI-class), and the convergence decision's buy verdict stands for the security-level
factor machinery — but no vendor sells the **roster-specific** overlap between *your*
managers, and the free public rung (13F) is a sanity check any allocator can build.

What holdings overlap wins over all of these is that it is a **measurement, not an
estimate**. Point-in-time position overlap has no small-sample problem: if two
managers each hold a name at 4% of book, that 4% is a fact about today's portfolio,
not a parameter inferred from a short noisy history. This is the same distinction
that makes the P1 card refuse to estimate a manager-return covariance matrix at
$T \le 60$ and instead defer correlation-aware risk to holdings and the house factor
model. **M4 is the holdings side of that refusal made into a product**: it measures
the overlap directly rather than trying to back it out of returns.

- **Decisions improved:** **size** — cap aggregate exposure to a crowded theme, so
  the roster is not one levered bet in disguise; **monitor / redeem** — a high
  liquidity-adjusted overlap is a standing exit-risk flag, because crowded illiquid
  books unwind first and worst (Brown–Howard–Lundblad).
- **Customer:** investment team (book-level pairwise overlap); department leadership
  (roster heat-map and aggregate unwind footprint).

## 3. How it works

### 3.1 The mental model, before any math

Picture two managers' books laid side by side as bars over the same list of names.
Overlap is the shaded area where the bars coincide *in the same direction* — a name
both hold long, or both hold short. If that shaded area is a large fraction of either
book, the two managers are, to that extent, the same trade. That is the entire
primitive: **overlap is the common area of two holdings profiles.**

Two refinements turn the primitive into something an allocator can act on, and both
are worth building intuition for before the formulas.

**Refinement one — not all overlap is equally dangerous.** A shared position in a
mega-cap you can exit in an afternoon is very different from a shared position in a
thin name that would take the whole crowd a week to unwind. The raw overlap counts
both the same; the **liquidity-adjusted** overlap re-weights the shared names by how
long they take to exit, so crowding that sits in illiquid names — precisely the
crowding that hurts in a stress — counts for more. This is the difference between "we
hold 22% of the same book by dollars" and "but 52% of our combined *unwind time* is
in the same three thin names." The second number is the one that matters when the
trade turns.

**Refinement two — the danger is a joint event, not a per-manager one.** One manager
holding an illiquid name is a position; five managers holding the same illiquid name
is a **crowd**, and the crowd's risk is that they all try to leave together. So M4
does not stop at pairwise overlap: it aggregates the common holders of each name into
a **combined footprint** and asks how many days of (stressed) trading volume that
footprint represents. A name that is nine days of volume for the crowd is a name where
the exit is the trade — the first to gap in a liquidation, and the reason a "5%
position" can cost far more than 5% to get out of.

That is the whole idea, and it immediately explains the demo's punchline. Two managers
an allocator files as diversifiers — one a concentrated long book, one an
event-driven book — share only **22%** of their positions by raw dollar weight and
have a return-vector cosine of just **0.07**, so by every returns-and-labels lens they
look independent. But their overlap is concentrated in three thin names, so in
**unwind space** they are **52%** the same book, and the most crowded shared name
represents **8.8 days** of stressed volume for the two of them combined. Nothing about
the raw overlap changed; the liquidity lens simply revealed that the diversification
was illusory exactly where it was expensive.

### 3.2 A worked toy example

Take two long-only managers over a tiny five-name universe, each book expressed as
**gross-normalized weights** (absolute weights summing to 1, so the numbers read as
"fraction of book"):

- Manager A: $w^A = [0.40,\ 0.30,\ 0.20,\ 0.10,\ 0.00]$
- Manager B: $w^B = [0.15,\ 0.00,\ 0.10,\ 0.10,\ 0.65]$

The **common-weight overlap** is the sum, over names both hold in the same direction,
of the smaller of the two weights — the literally-shared fraction of book:

$$
O_{AB} = \sum_n \min(|w^A_n|,\ |w^B_n|) = 0.15 + 0.00 + 0.10 + 0.10 + 0.00 = 0.35.
$$

So 35% of the book is common: whichever manager you stand on, a third of their
positions is also the other's. The **cosine** of the two weight vectors tells a
different, complementary story — it measures the *angle* between the books, and it is
pulled down hard by B's large idiosyncratic bet on name 5:

$$
\cos(w^A, w^B) = \frac{w^A \cdot w^B}{\|w^A\|\,\|w^B\|}
= \frac{0.09}{0.548 \times 0.682} = 0.24.
$$

The two numbers disagree on purpose: common-weight overlap answers "what fraction of
book is shared?" (0.35) while cosine answers "how aligned are the books as directional
bets?" (0.24, lower because B's book points mostly at a name A does not hold). M4
reports the common-weight overlap as the headline — it is the one that reads directly
as a percentage of shared book — and carries the cosine as a companion angle. These
are the exact numbers the §4 reference code prints.

### 3.3 The overlap measures

Let a roster of managers share a name universe of $N$ names. Each manager $a$ has a
signed weight vector $w^a \in \mathbb{R}^N$ (positive = long, negative = short),
**gross-normalized** so $\sum_n |w^a_n| = 1$.

**Common-weight (directional) overlap.**

$$
O_{ab} = \sum_{n=1}^{N} \min(|w^a_n|,\ |w^b_n|)\ \cdot\ \mathbb{1}\!\left[\operatorname{sign}(w^a_n) = \operatorname{sign}(w^b_n)\right]
$$

where:

- $w^a_n$ — manager $a$'s gross-normalized weight in name $n$ (a decimal fraction of
  book; sign encodes long/short).
- $\min(|w^a_n|,\ |w^b_n|)$ — the shared magnitude in name $n$: the most of that name
  the two books hold *in common*.
- $\mathbb{1}[\operatorname{sign}(w^a_n) = \operatorname{sign}(w^b_n)]$ — an indicator
  that counts a name **only when both hold it the same direction**; a name A is long
  and B is short is not crowding, it is an offset, and must not add to overlap.
- $O_{ab} \in [0, 1]$ — the fraction of book the two managers hold in common. $O_{ab}=0$
  is disjoint books; $O_{ab}=1$ is identical books.

In words: walk the shared universe, and for every name both managers hold the same way,
add the smaller of the two weights. This is the **directional Bray–Curtis similarity**
of the two gross-normalized books (Bray & Young, §3.9): for two profiles that each sum
to 1, $\sum_n \min$ is exactly the Bray–Curtis overlap, and the sign indicator restricts
it to same-direction crowding.

**Cosine companion.** The angle between the signed weight vectors,

$$
\cos(w^a, w^b) = \frac{\sum_n w^a_n w^b_n}{\sqrt{\sum_n (w^a_n)^2}\ \sqrt{\sum_n (w^b_n)^2}},
$$

reported alongside $O_{ab}$ because it weights large shared positions more heavily
(squares in the norm) and so flags *concentrated* shared bets that the linear
common-weight measure can under-state. Neither measure is "the" overlap; the pair is
the read.

### 3.4 The liquidity lens and the unwind stress

Raw overlap treats a shared dollar in a mega-cap the same as a shared dollar in a
microcap. The **liquidity adjustment** fixes that by re-expressing each book in
**days-to-cover** — the trading days needed to exit each position — and measuring
overlap in *that* space.

**Days-to-cover.** For manager $a$'s dollar position $D^a_n$ in name $n$ with dollar
average daily volume $\text{ADV}_n$:

$$
\text{DTC}^a_n = \frac{|D^a_n|}{\phi\,\cdot\,\text{ADV}_n}
$$

where:

- $D^a_n$ — manager $a$'s **dollar** position in name $n$ (weight × AUM).
- $\text{ADV}_n$ — name $n$'s dollar average daily volume (the new liquidity input, §6.6).
- $\phi$ — the **participation limit**: the fraction of a day's volume one can trade
  without outsized impact. Provisional **`PARTICIPATION_LIMIT_M4` = 0.20** (NUMERICS-GATE).
- $\text{DTC}^a_n$ — trading days to unwind the position at that participation rate.

**Liquidity-adjusted overlap.** Turn each book into its vector of **signed unwind-time
shares** — each name's fraction of the book's total days-to-cover, carrying the position
sign — and take the common-weight overlap of *those* vectors:

$$
s^a_n = \operatorname{sign}(D^a_n)\,\frac{\text{DTC}^a_n}{\sum_m \text{DTC}^a_m},
\qquad
O^{\text{liq}}_{ab} = \sum_n \min(|s^a_n|,\ |s^b_n|)\ \mathbb{1}\!\left[\operatorname{sign}(s^a_n) = \operatorname{sign}(s^b_n)\right]
$$

where:

- $s^a_n$ — the share of manager $a$'s **total unwind time** spent in name $n$ (signed).
  Illiquid names have large DTC and so dominate this vector even at modest dollar weight.
- $O^{\text{liq}}_{ab} \in [0, 1]$ — the fraction of **unwind footprint** the two books
  hold in common. It reads *higher* than the raw dollar overlap $O_{ab}$ exactly when
  the shared names are the thin ones — which is when crowding is dangerous.

In words: the liquidity-adjusted overlap is the same common-area measure as §3.3, but
computed after re-scaling each book so that a name counts in proportion to how long it
takes to get out of, not how many dollars are in it. When $O^{\text{liq}}_{ab} \gg
O_{ab}$, the diversification is illusory precisely in the exit.

**Common-holder unwind stress.** Crowding's cost is a joint liquidation. For each name,
sum the **combined footprint** across all managers who hold it the same direction, and
express it as days of volume in a **stressed** regime where volume is depressed:

$$
\text{DoV}_n = \frac{\sum_{a \in H_n} |D^a_n|}{\delta\,\cdot\,\text{ADV}_n}
$$

where:

- $H_n$ — the set of managers holding name $n$ in the crowded direction.
- $\sum_{a \in H_n} |D^a_n|$ — the crowd's combined dollar footprint in name $n$.
- $\delta$ — the **stress volume factor**: fraction of normal ADV that trades in a
  stressed regime. Provisional **`STRESS_VOLUME_DELTA_M4` = 0.5** (NUMERICS-GATE) —
  Sweep C's caveat that unwind scenarios must stress volumes to depressed regimes, not
  assume normal liquidity.
- $\text{DoV}_n$ — days of stressed volume the crowd's combined footprint represents in
  name $n$. The worst-name $\text{DoV}$ is the headline exit-risk number.

**Illustrative impact cost (flagged, not robust).** A days-of-volume figure is a robust
measurement; converting it to a **dollar** loss requires an impact model, which is an
assumption, not a measurement. Under a square-root impact law the crowd's liquidation
cost in name $n$ is approximately

$$
\text{cost}_n \approx \gamma\,\sigma_n\,\sqrt{\frac{\sum_{a \in H_n} |D^a_n|}{\delta\,\text{ADV}_n}}
$$

where $\sigma_n$ is the name's daily return volatility and $\gamma$ is an impact
coefficient — provisional **`IMPACT_GAMMA_M4` = 1.0** (NUMERICS-GATE), **the most
assumption-laden constant in the card**. The demo renders the days-of-volume as the
robust core and the dollar impact only as a clearly-labelled illustrative overlay
(§5), never as a prediction.

### 3.5 The tier ladder — what each rung can and cannot see

M4's reliability is entirely a function of what the data tier lets it observe. The card
defines four rungs, strongest to weakest, and the honesty of the card is that each
rung's blind spots are rendered as first-class caveats, not hidden.

- **P (position transparency) — the robust rung.** Full position-level holdings per
  manager. Every measure in §3.3–3.4 runs exactly as written; overlap, liquidity
  adjustment, and unwind stress are all point-in-time measurements with no small-sample
  problem. This is the rung the simulator demo runs on (P-tier holdings via `emit_tiers`).
- **13F — the free public proxy.** Quarterly SEC 13F filings give **long US equity**
  positions with a **45-day lag** and confidentiality-treatment (CTR) holes. The overlap
  math is identical, but the input is stale (up to a quarter-plus old), **longs-only**
  (shorts and non-US invisible, so L/S overlap is understated), and incomplete (CTR
  names missing). Every 13F view carries a TierBadge stating all four limits. This is the
  **live rung** for long US books, and its staleness is measured, not asserted (§6.4 gate 3).
- **E (exposure summaries) — factor crowding only.** With factor/sector/gross/net
  buckets but no names, M4 can measure **common tilts** (are the managers crowded into
  the same factors?) but not name-level overlap. A coarser, still-useful read.
- **R (returns only) — a descriptive chip, no inference.** With returns alone M4 can
  cluster managers by return co-movement and render a **descriptive** crowding chip.
  This rung makes **no predictive or inferential claim** — at $T \le 60$ a manager
  return correlation is noise (the do-not-build list bars returns-based style *inference*;
  §6.1), so the R chip is explicitly labelled "descriptive, not a measurement of holdings
  crowding," and it never feeds the unwind scenario or a size cap.

### 3.6 Measurement versus prediction — the honesty split

M4 makes two very different kinds of claim, and conflating them is the trap the card
must avoid.

**The measurement is robust.** Overlap, liquidity-adjusted overlap, and days-of-volume
are facts about today's holdings (at the P rung) or today's best proxy (13F). They have
no estimation error beyond the data's own staleness; there is no $T$ in the formulas.
The Sweep C power verdict is explicit: point-in-time crowding measurement is **Robust**.

**The prediction is gated.** The *claim that measured overlap forecasts unwind losses* —
that a high-overlap crowd will actually co-drawdown when the trade turns — is an
empirical hypothesis, and it is the part that must earn its keep on the atlas (§6.4).
M4 does not assert it; it *tests* it, by dialing common-signal participation up in the
simulator and asking whether measured overlap predicts simulated co-drawdown in a
stress. Until that gate passes, the unwind panel is framed as a **scenario** ("if the
crowd liquidated together, here is the footprint"), never a **forecast** ("this crowd
will lose X%"). The days-of-volume is what-you-hold; the loss is what-might-happen, and
the page keeps them visually and verbally distinct.

### 3.7 What M4 does not do — the P1 boundary

M4 **measures** crowding; it does not **allocate**. This boundary is load-bearing and
stated in both directions: the P1 allocation spec (§6.1) names M4 as the owner of
cross-manager overlap and crowding caps, "consumed as constraints when both cards are
live," and P1's §3.2 deliberately refuses to build an estimated manager-correlation
matrix into its optimizer. M4 is the other half of that refusal. It emits a crowding
**measurement** (an overlap number per pair, an aggregate footprint per theme) that P1
consumes as an **input cap**. M4 does **not** compute weights, does not build or invert a
correlation matrix, and does not smuggle a mean-variance optimizer in through the back
door of a "crowding-aware objective." The correlation-levered spread bet that P1 §3.2
dissects is exactly what a crowding *optimizer* would re-introduce at roster scale;
M4 stays on the measurement side of the line by design.

### 3.8 What the canonical papers contribute

- **Brown, Howard & Lundblad (2022), "Crowded Trades and Tail Risk"
  (*Review of Financial Studies*).** The direct empirical warrant: hedge-fund positions
  that are more crowded — more commonly held, especially in less liquid names — suffer
  larger drawdowns in liquidity stress. This is why M4's exit-risk flag weights overlap
  by liquidity rather than treating all shared names alike, and why the card's monitor /
  redeem hook ("crowded illiquid books exit first") is grounded, not asserted.
- **Khandani & Lo (2011), "What Happened to the Quants in August 2007?"
  (*Journal of Financial Markets*).** The canonical anatomy of a common-holder unwind:
  a cluster of managers running similar factor books deleveraged into each other over a
  few days, and the mechanical price impact — not any change in fundamentals — produced
  the losses. M4's unwind-stress scenario is a static, roster-scale sketch of exactly this
  mechanism, which is why the scenario stresses volume to a depressed regime.
- **Bray & Curtis (1957), on ecological similarity indices.** The origin of the
  $\sum \min / \sum$ overlap coefficient M4 uses for two normalized profiles. Naming the
  measure ties it to a well-understood similarity index with known behaviour (bounded,
  interpretable as shared fraction), rather than an ad-hoc score.
- **Almgren, Thum, Hauptmann & Li (2005), "Direct Estimation of Equity Market Impact."**
  The square-root impact law behind the illustrative cost in §3.4: liquidation cost scales
  with the square root of the traded fraction of volume. M4 uses it only to render an
  illustrative overlay on the robust days-of-volume core, with its coefficient flagged for
  the numerics gate — impact modelling is a buy-or-approximate, not a claim M4 defends.

## 4. How to implement

The reference implementation below is **self-contained teaching code** — paste it into a
fresh file, it runs on `numpy` alone. It implements the same formulas as §3: gross
normalization, the common-weight and cosine overlaps (§3.3), days-to-cover, the
liquidity-adjusted overlap in unwind space (§3.4), and the common-holder unwind stress
(§3.4). It uses no project imports and no repo paths.

```python
"""M4 crowding & overlap radar — self-contained teaching mock (numpy only).

Implements the overlap and unwind measures of the M4 method spec, sections 3.3
and 3.4: directional common-weight overlap, the cosine companion, days-to-cover,
the liquidity-adjusted (unwind-space) overlap, and the common-holder unwind
stress. numpy only; no project imports.
"""

import numpy as np


# ---------------------------------------------------------------------------
# 1. Pairwise holdings overlap (directional Bray-Curtis on gross-normalized
#    weights) and the cosine companion (section 3.3).
# ---------------------------------------------------------------------------
def gross_normalize(weights):
    """Scale a signed weight vector so the gross (sum of |w|) is 1."""
    weights = np.asarray(weights, dtype=float)
    return weights / np.abs(weights).sum()


def common_weight_overlap(w_a, w_b):
    """Directional common-weight overlap in [0, 1]: the fraction of book two
    managers literally hold in common, counting only SAME-SIGN positions."""
    w_a, w_b = gross_normalize(w_a), gross_normalize(w_b)
    same_sign = (np.sign(w_a) == np.sign(w_b)) & (w_a != 0) & (w_b != 0)
    return float(np.sum(np.minimum(np.abs(w_a), np.abs(w_b))[same_sign]))


def cosine_overlap(w_a, w_b):
    """Cosine similarity of the two signed weight vectors (angle, not shared %)."""
    w_a, w_b = np.asarray(w_a, float), np.asarray(w_b, float)
    denom = np.linalg.norm(w_a) * np.linalg.norm(w_b)
    return float(w_a @ w_b / denom) if denom else 0.0


# ---------------------------------------------------------------------------
# 2. Liquidity lens: days-to-cover of a dollar position, and a liquidity-
#    adjusted overlap measured in unwind (days-to-cover) space (section 3.4).
# ---------------------------------------------------------------------------
def days_to_cover(dollar_position, adv_dollar, participation=0.20):
    """Trading days to unwind a position at a max participation rate of daily $ volume."""
    return np.abs(dollar_position) / (participation * np.asarray(adv_dollar, float))


def liquidity_adjusted_overlap(dollars_a, dollars_b, adv_dollar, participation=0.20):
    """Common-weight overlap measured in DAYS-TO-COVER (unwind) space, not dollar
    space. Each book becomes a vector of per-name unwind-time shares; the overlap
    of those vectors is the fraction of UNWIND FOOTPRINT the two books hold in
    common. Illiquid shared names dominate unwind time, so this reads higher than
    the raw dollar overlap exactly when crowding sits in thin names."""
    dtc_a = days_to_cover(dollars_a, adv_dollar, participation)
    dtc_b = days_to_cover(dollars_b, adv_dollar, participation)
    share_a = np.sign(dollars_a) * dtc_a / dtc_a.sum()   # signed unwind-time share
    share_b = np.sign(dollars_b) * dtc_b / dtc_b.sum()
    return common_weight_overlap(share_a, share_b)


# ---------------------------------------------------------------------------
# 3. Common-holder unwind stress: days of (stressed) volume the crowd's combined
#    footprint represents per name (section 3.4).
# ---------------------------------------------------------------------------
def unwind_days_of_volume(dollar_positions_by_manager, adv_dollar, stress_delta=0.5):
    """Per-name days of (stressed) volume the crowd's combined footprint represents.
    dollar_positions_by_manager: (n_managers, n_names) same-direction dollar sizes."""
    combined = np.abs(np.asarray(dollar_positions_by_manager, float)).sum(axis=0)
    stressed_adv = stress_delta * np.asarray(adv_dollar, float)
    return combined / stressed_adv


if __name__ == "__main__":
    # -- Worked toy (section 3.2): 5 names, two long-only books. ------------
    a = [0.40, 0.30, 0.20, 0.10, 0.00]
    b = [0.15, 0.00, 0.10, 0.10, 0.65]
    print("== Toy overlap ==")
    print(f"common-weight overlap = {common_weight_overlap(a, b):.3f}")   # 0.350
    print(f"cosine overlap        = {cosine_overlap(a, b):.3f}")          # 0.241

    # -- Demo pair (sections 3.1 / 5): two 'diversifying' books whose shared
    #    names are the thin ones. 7 names: N1-N3 shared (thin), N4-N5
    #    Hollowmere-only (liquid), N6-N7 Brackenford-only (liquid).
    #    AUM $500mm each; ADV in $mm/day. ------------------------------------
    labels = ["N1", "N2", "N3", "N4", "N5", "N6", "N7"]
    adv = np.array([25.0, 35.0, 30.0, 120.0, 110.0, 130.0, 115.0])   # $mm/day
    aum = 500.0                                                      # $mm each
    hollowmere = np.array([0.10, 0.08, 0.06, 0.42, 0.34, 0.00, 0.00])
    brackenford = np.array([0.12, 0.07, 0.05, 0.00, 0.00, 0.40, 0.36])
    dollars_h, dollars_b = hollowmere * aum, brackenford * aum
    print("\n== Demo pair: Hollowmere x Brackenford ==")
    print(f"raw common-weight overlap   = {common_weight_overlap(hollowmere, brackenford):.3f}")  # 0.220
    print(f"cosine overlap              = {cosine_overlap(hollowmere, brackenford):.3f}")          # 0.066
    print(f"liquidity-adjusted overlap  = {liquidity_adjusted_overlap(dollars_h, dollars_b, adv):.3f}")  # 0.519

    # Unwind stress on the commonly-held names (same-sign, both nonzero).
    common = (np.sign(hollowmere) == np.sign(brackenford)) & (hollowmere != 0) & (brackenford != 0)
    dollars = np.vstack([np.abs(dollars_h), np.abs(dollars_b)])
    dollars[:, ~common] = 0.0
    dov = unwind_days_of_volume(dollars, adv, stress_delta=0.5)
    print("\n== Unwind stress (stressed volume = 50% of normal) ==")
    for i, nm in enumerate(labels):
        if common[i]:
            print(f"  {nm}: combined ${dollars[:, i].sum():5.1f}mm, ADV ${adv[i]:5.0f}mm"
                  f" -> {dov[i]:4.1f} days of volume")
    worst = np.where(common, dov, 0.0)
    print(f"worst common name: {labels[worst.argmax()]} at {worst.max():.1f} days of volume")  # N1, 8.8
```

Running it prints the toy overlap (0.350 common-weight, 0.241 cosine), then the demo
pair: a raw dollar overlap of **0.220** and a cosine of just **0.066** — two books that
look independent — against a liquidity-adjusted overlap of **0.519**, because the
shared names N1–N3 are the thin ones. The unwind stress then shows the most crowded
shared name (N1) at **8.8 days** of stressed volume for the two managers combined. The
diversification was illusory exactly where it was expensive — the demo's punchline,
reproduced from first principles.

## 5. Reading the demo

The gallery page `m4.html` is fully synthetic (§6 compliance): a roster of managers
simulated on **one shared market** (one name universe, many managers — the substrate
already models this), rendered at the **P tier** (full holdings). It has three parts.

**The two-manager unwind panel — the centrepiece.** Two managers an allocator files as
diversifiers:

- **Hollowmere Capital** — a concentrated long book (its largest bets in liquid names
  N4–N5).
- **Brackenford Partners** — an event-driven book (its largest bets in liquid names
  N6–N7).

By the lenses an allocator usually trusts they look independent: **22%** raw dollar
overlap, a return-vector cosine of **0.07**. But their overlap concentrates in three
thin shared names, so their **liquidity-adjusted overlap is 52%** — in unwind space
they are more than half the same book. The panel's unwind scenario shows the most
crowded shared name at **8.8 days** of stressed volume for the two combined.

How each visual element maps to the method:

- **The two overlap numbers** (raw 22% vs liquidity-adjusted 52%) = §3.3 and §3.4. The
  gap between them *is the finding*: crowding hidden in the illiquid tail. Rendered as
  two IntervalStats side by side, the second annotated "of combined unwind time."
- **The unwind bar chart** = §3.4 days-of-volume per shared name, worst name (8.8 days)
  highlighted. The bars are the **robust** measurement (what the crowd holds); an
  optional dashed **illustrative-impact** overlay (the §3.4 square-root cost) is drawn
  separately and labelled "illustrative — not a forecast," keeping measurement and
  prediction visually distinct (§3.6).
- **The liquidity dial** = a Dietvorst-style control on the stress volume factor $\delta$
  (§3.4): drag stressed volume from normal down to a crisis regime and watch the
  days-of-volume stretch. The output is an input to judgement, not a verdict.

**The roster heat-map.** A small grid of synthetic managers; each cell is the
liquidity-adjusted overlap of a pair, shaded by intensity. The diversifier pair above
is the hot cell an allocator would not have expected. The heat-map is the "is our
diversification illusory?" question answered at a glance.

**The tier ladder and the power gate.** A TierBadge strip shows what each rung sees:
P (the demo's robust rung), 13F (the live rung, badged stale / longs-only / CTR-holes /
non-US-blind), E (factor crowding only), R (a descriptive return-clustering chip,
labelled "not a holdings measurement"). The **PowerGate** is the honest refusal on the
*predictive* claim: the panel measures overlap robustly, but "high overlap ⇒ this crowd
will co-drawdown" is a **gated hypothesis** (§6.4), so the page renders the unwind as a
**scenario** and refuses to print a predicted loss until the atlas gate passes.

What an allocator should conclude from these numbers: the returns-and-labels view said
Hollowmere and Brackenford were diversifiers; M4 shows that where it counts — the exit —
they are the same trade, and the roster's real concentration is larger than the pair
count suggests. That is a **size** decision (cap the shared theme) and a **monitor** flag
(this pair unwinds together), delivered as a measurement with its data-tier caveats on
its face.

## 6. Honest limits & go-live

### 6.1 What M4 does not do (do-not-build adjacency)

- **No allocation rule, no optimizer.** M4 measures crowding and hands the number to P1
  as an input cap (§3.7); it never computes weights, never builds or inverts a
  manager-correlation matrix, and never wraps a mean-variance objective around the
  overlap score. P1 §6.1 assigns crowding caps to M4 as a *measurement* consumed as a
  constraint — this card defines the measurement, full stop.
- **No returns-based crowding inference.** The R rung is a **descriptive** chip only; at
  $T \le 60$ a manager return correlation is noise, and returns-based style-drift
  *inference* is on the do-not-build list (convergence §4). M4 measures holdings, or
  says honestly that at the R tier it can only cluster co-movement descriptively.
- **No persistence tests, no FDR luck-screens, no regime-split or conditional-beta
  alphas** (do-not-build list). M4 runs no cross-manager alpha test; crowding is a
  holdings measurement, not a skill claim.
- **No predictive claim without the gate.** The unwind panel is a **scenario** until
  §6.4's atlas gate shows measured overlap predicts simulated co-drawdown; the page
  frames it as such (§3.6).

### 6.2 Data contract per tier

M4 is **holdings-native**: its robust rung needs positions, and the weaker rungs degrade
gracefully to exposures and returns with their limits stated.

| Tier | Inputs the live version needs | What the card produces |
| --- | --- | --- |
| **P** (robust) | Position-level holdings per manager (name, signed weight or dollar size), aligned to a shared name universe; per-name dollar **ADV** and daily return vol for the liquidity lens and unwind stress. | The **whole radar**: pairwise common-weight and cosine overlap, liquidity-adjusted (unwind-space) overlap, roster heat-map, and the common-holder unwind stress (days-of-volume + illustrative impact). |
| **13F** (live public rung) | Quarterly SEC 13F filings (long US equity, 45-day lag, CTR holes) via the shared 13F adapter; ADV/vol from public market data. | The **same overlap math on a stale, longs-only, US-only proxy** — every view badged with the four limits (staleness, longs-only, CTR gaps, non-US blind). L/S overlap is understated; caveats are the design (§3.5). |
| **E** | Factor / sector / gross / net exposure buckets (Open Protocol-aligned) | **Factor crowding only**: common-tilt overlap across managers (are they crowded into the same factors?), no name-level overlap and no unwind stress. |
| **R** (minimum) | Monthly net returns per manager | A **descriptive** return-co-movement clustering **chip** — explicitly not a holdings measurement, no unwind scenario, no size cap (§3.5, §6.1). |

**Frequency & universe.** Holdings at each tier's native cadence (13F quarterly; P as
delivered). The shared name universe is the market both managers trade; the P-tier demo
gets it for free from the simulator (one market, many managers).

**Compliance (standing):** synthetic managers in the repo; the 13F rung uses only public
SEC filings of **unaffiliated** managers, never any filer with an implied relationship to
the employer's roster — no employer-internal facts in code, docs, or the committed demo
JSON.

### 6.3 Provisional constants (numerics gate)

Every provisional numeric is a **named constant** carried to the numerics gate:

- **`PARTICIPATION_LIMIT_M4` = 0.20** — max fraction of daily volume tradable without
  outsized impact (§3.4). Sets the days-to-cover scale.
- **`STRESS_VOLUME_DELTA_M4` = 0.5** — stressed volume as a fraction of normal ADV
  (§3.4). Sweep C's depressed-regime caveat.
- **`IMPACT_GAMMA_M4` = 1.0** — square-root impact coefficient (§3.4), **the most
  assumption-laden constant**; governs only the illustrative overlay, never the robust
  days-of-volume.
- **`OVERLAP_ALERT_THRESHOLD` = 0.30** (provisional) — the liquidity-adjusted overlap at
  which a roster-heat-map cell is flagged "crowded." A rendering threshold, not an
  inference.
- **`MARKET_ADV_RANGE`** and **`N_ASSETS`** for the multi-manager universe — the new
  ADV substrate's dollar-volume range and the roster's shared-universe size (mirrors the
  X1 grid's `N_ASSETS` docket note). Set book-selection breadth and the liquidity spread.

### 6.4 Power & validation plan

Validation runs on the simulator; cells contribute to the X1 atlas
([`x1-tier-power-atlas.md`](x1-tier-power-atlas.md)) as this card's rows. The atlas axis
is **crowding participation** — a new simulator dial (§6.6) that steers a controllable
fraction of managers' signals to a **shared crowded sub-signal**, so ground-truth
overlap is known and the measurement can be scored against it. Grid follows the atlas
convention: crowding-participation level × roster size × liquidity spread × tier
(P / 13F-proxy), ≥1,000 seeded replications per cell (per-module RNG streams; Wilson 95%
intervals on every rate — X1 §3.3).

Acceptance gates:

1. **Overlap recovery (the measurement gate).** As the crowding-participation dial
   increases, measured liquidity-adjusted overlap must rise **monotonically** and track
   the ground-truth shared fraction within tolerance. This confirms the radar reads the
   crowding that is actually there — the robust-measurement claim.
2. **Predictive gate (the one that earns the exit-risk story).** Inject a stress event —
   the shared crowded sub-signal reverses and the crowd deleverages — and test whether
   **higher measured overlap predicts larger simulated co-drawdown / unwind loss**,
   reported as an operating characteristic (overlap decile vs realized stress loss), not
   a single threshold. This is the gate that converts the unwind panel from scenario to
   supported claim (§3.6); until it passes, the page says so.
3. **13F degradation.** Down-sample the P-tier holdings to **quarterly with a 45-day lag
   and a longs-only mask** (the 13F rung), and measure how much the overlap estimate
   degrades versus the P-tier truth. This quantifies the staleness caveat the 13F
   TierBadge carries — the caveat is measured, not asserted.
4. **Liquidity-lens sensitivity.** Sweep `PARTICIPATION_LIMIT_M4` and
   `STRESS_VOLUME_DELTA_M4` across plausible ranges and report how the liquidity-adjusted
   overlap and days-of-volume move, so the reader sees how much the exit-risk read leans
   on the two liquidity constants.

**Simulator dependency (honest).** Gates 1–2 need the **crowding-participation dial** and
gates 1–4 need the **per-asset ADV field** — both are named new substrate (§6.6), not
assumed present. Everything else runs on the existing multi-manager simulator.

### 6.5 Kill criteria

- **Statistical (predictive).** If gate 2 fails — measured overlap does **not** predict
  simulated co-drawdown across the participation range — M4 **ships as measurement only**:
  the overlap heat-map and days-of-volume stay (they are robust), but the **exit-risk
  framing and any size-cap recommendation are pulled**, recorded in writing per
  converge-or-cut. A crowding number sold as a loss predictor it cannot support is worse
  than an honest overlap measurement.
- **Data (13F).** If gate 3 shows the 13F proxy degrades overlap beyond usefulness for
  L/S books — the longs-only, stale view is *misleading* rather than merely coarse (the
  card's stated data risk) — the 13F rung **ships with caveats or not at all**; it is
  never presented as a clean read of L/S crowding. (Consistent with the S3 spec §6.2
  ruling that 13F is too coarse for decay estimation — M4 uses 13F for point-in-time
  overlap, a robust use, and does not contradict that finding.)
- **Political.** Crowding is a **conversation and sizing input**, never a mechanical
  redemption. An overlap number wired to an automatic action gets gamed (managers dress
  the book around a filing date) and mis-reads the 45-day-stale proxy as live — so it
  ships as a flag routed to a human, not a trigger.

### 6.6 How it ships in the repo

The commitment is **reuse the multi-manager simulator and the P-tier emitter; add the
overlap layer and two small, byte-identical simulator extensions.**

- **New module `src/quant_allocator/flagships/crowding/pipeline.py`:** pure functions over
  holdings — `common_weight_overlap`, `cosine_overlap`, `liquidity_adjusted_overlap`,
  `roster_overlap_matrix`, and `unwind_stress(holdings, adv, *, participation, stress_delta)
  -> UnwindReport` (per-name days-of-volume + illustrative impact). No rendering, no I/O
  (S2 §5 convention). Consumes the P-tier holdings from the existing
  `simulator/tiers.py` `emit_tiers().transparency` — **import, do not re-emit**.
- **New substrate 1 — per-asset ADV on the market (byte-identical).** Add
  `MarketConfig.adv_dollar_range` (default a stated `MARKET_ADV_RANGE`) and draw a
  per-asset dollar-ADV vector on a **new named stream tag** `_LIQUIDITY_STREAM = 3`
  (distinct from market=0, manager=1, returns_only=2). Because the draw is on its own
  stream, every existing market draw is **byte-identical**; a build that does not read
  `adv_dollar` is unaffected. The same discipline as `death_month` / `net_drift`.
- **New substrate 2 — crowding-participation dial (byte-identical).** Add
  `ManagerConfig.crowd_participation` (default **0.0** = the honest, byte-identical
  manager) and a shared `crowd_seed`; when > 0, a fraction of the fresh signal is drawn
  from a **common crowded sub-signal** shared across participating managers, on a new
  named stream tag `_CROWD_STREAM = 4`. At the default 0.0 the manager consumes **zero**
  crowd-stream RNG and its output is byte-identical to today's; only opt-in managers
  crowd. This is the dial the atlas needs (§6.4 gates 1–2).
- **Live rung — the 13F adapter (deferred, shared prerequisite).** The 13F rung consumes
  the **shared 13F adapter** — the same deferred substrate that card M6 builds (M6
  sequencing: "feeds M4's real-data rung"). M4 does not build it; it names it as the
  live-rung prerequisite, and its demo runs on the P-tier simulator holdings meanwhile.
- **Demo — `src/quant_allocator/demo_data/m4_crowding.py`** (imports the pipeline; same
  code path as any live build, only the input data is synthetic). The **wow-demo**: a
  small roster on one shared market, two "diversifying" managers (Hollowmere Capital,
  Brackenford Partners) whose raw overlap (22%) hides a liquidity-adjusted overlap (52%)
  and an 8.8-day worst-name unwind. Emits committed JSON to `site/data/m4_crowding.json`
  via `_emit.write_json`; **CI renders the page from that JSON only — CI never computes**
  (demo-layer doctrine).
- **Depends:** the simulator (multi-manager market + the two byte-identical extensions),
  `simulator/tiers.py` (P-tier holdings), the X1 grid machinery (validation cells), and —
  live only — the shared 13F adapter. **numpy only** for the demo; no new runtime
  dependency. Downstream: **P1** consumes the crowding measurement as a size cap.
- **Effort:** **M–L** (card estimate). The overlap layer is a handful of pure functions;
  the two simulator extensions are small and follow the established byte-identical
  pattern; the atlas cells and the 13F-degradation gate are the real work; the live 13F
  rung waits on the shared adapter.

### 6.7 Adoption & packaging

- **"Is our diversification illusory?"** — the crowding radar is **book-level
  conversation and sizing material**, surfaced where the reader already is: the roster
  heat-map at the sizing / review moment for leadership, the pairwise panel inside the
  book-level view for the investment team. No standing always-on crowding dashboard to go
  stale (Sweep E: the separate-tab monitor dies at 25% adoption).
- **The liquidity dial.** The stress volume factor $\delta$ is an adjustable control
  (§5): drag it to a crisis regime and watch the unwind footprint stretch. The output is
  an input to judgement, not a verdict.
- **Receipts, tiered.** Every crowding read shows its number *with its data tier* —
  *"52% of combined unwind time in three shared names (P-tier holdings)"* or *"34% overlap
  (13F, 45-day-stale, longs-only)"* — never a bare score without its caveat.

**Who sees what, when:** the investment team sees the pairwise overlap and unwind panel
at book-level review; leadership sees the roster heat-map and aggregate footprint at the
sizing moment; the P1 card consumes the measurement as a crowding cap when both are live.
Any manager-facing version lives only inside the E1 transparency-ladder relationship,
framed as the shared question ("how much of your book is the crowd's book?"), never as an
accusation.

### 6.8 Go-live requirements (demo-page box, expanded)

- **Data ask:** position-level holdings (tier P) aligned to a shared name universe, plus
  per-name ADV and daily vol for the liquidity lens; or, for the free rung, 13F filings
  (long US equity, quarterly, 45-day lag) via the shared adapter. Tier E degrades to
  factor crowding; tier R to a descriptive chip.
- **Sample required:** **none for the measurement** — overlap is point-in-time and has no
  small-$T$ problem (Sweep C: Robust). The **predictive** claim (overlap ⇒ unwind loss)
  requires the atlas gate (§6.4 gate 2) before it is asserted.
- **Build effort:** **M–L** — the overlap layer plus two byte-identical simulator
  extensions and the atlas cells; the live 13F rung waits on the shared adapter.
- **Go-live box (demo page):** data ask = holdings (P) or 13F (public rung); sample =
  none for measurement, atlas gate for the predictive claim; effort = M–L.

## 7. Deeper reading

**Canonical references (read in this order):**

1. **Brown, Howard & Lundblad (2022), "Crowded Trades and Tail Risk,"
   *Review of Financial Studies*.** Crowded hedge-fund positions — especially in less
   liquid names — suffer larger drawdowns in liquidity stress. The card's direct
   empirical warrant for weighting overlap by liquidity and for the monitor / redeem hook.
2. **Khandani & Lo (2011), "What Happened to the Quants in August 2007?"
   *Journal of Financial Markets*.** The anatomy of a common-holder unwind: mechanical
   price impact from simultaneous deleveraging, not fundamentals. The mechanism M4's
   unwind-stress scenario sketches at roster scale.
3. **Bray & Curtis (1957), on ecological similarity indices.** The origin of the
   $\sum \min / \sum$ overlap coefficient M4 uses for two normalized holdings profiles —
   a bounded, interpretable "shared fraction" measure with known behaviour.
4. **Almgren, Thum, Hauptmann & Li (2005), "Direct Estimation of Equity Market Impact."**
   The square-root impact law behind the illustrative unwind cost — used only as a
   labelled overlay on the robust days-of-volume core, with its coefficient flagged for
   the numerics gate.

**Questions you should be able to answer after reading this page:**

- **State the overlap measure and its sign discipline.** Explain why M4 counts a name
  toward overlap **only when both managers hold it the same direction** (a long-vs-short
  on the same name is an offset, not crowding), and why the common-weight
  $\sum \min$ on gross-normalized books reads directly as "fraction of book shared."
- **Raw vs liquidity-adjusted overlap.** Explain why two books can be 22% overlapping by
  dollars but 52% overlapping in unwind space — because the shared names are the thin
  ones, and days-to-cover re-weights the book toward whatever is hard to exit. Work the
  demo pair's numbers by hand once.
- **Why measurement, not correlation.** Explain why holdings overlap has no small-sample
  problem while a manager-return correlation at $T \le 60$ is noise, and why that is
  exactly the P1 §3.2 refusal made into a product — M4 measures the overlap directly
  rather than backing it out of returns.
- **The measurement / prediction split.** State which of M4's outputs are robust facts
  (overlap, days-of-volume) and which is a gated hypothesis (overlap predicts unwind
  loss), and why the demo renders the unwind as a **scenario** until the atlas gate
  (§6.4 gate 2) passes.
- **Explain the unwind scenario to a non-quant.** "Five managers each hold a 4% position
  in a thin name; individually fine, but if the trade turns they all sell at once, and
  the combined footprint is nine days of trading volume — so the exit *is* the trade, and
  a 4% position can cost far more than 4% to leave." Why volumes are stressed to a
  depressed regime, not assumed normal.
- **The 13F caveats.** State the four limits of the 13F rung (45-day lag, longs-only, CTR
  holes, non-US blind), why they make it a *sanity-check* rung for long US books rather
  than a clean L/S crowding read, and why point-in-time overlap on 13F is still a robust
  use even though S3 rules 13F too coarse for decay estimation.
- **The P1 boundary.** Explain why M4 stops at measurement and hands P1 a crowding cap,
  and what would go wrong if M4 wrapped an optimizer around the overlap score (the
  correlation-levered spread bet P1 §3.2 dissects, re-introduced at roster scale).

## 8. Method-review gate rulings (2026-07-07)

1. **Core measures approved:** directional Bray–Curtis common-weight overlap with
   the cosine companion; the liquidity-adjusted overlap in days-to-cover space;
   days-of-stressed-volume as the robust core. The square-root impact cost is
   **illustrative-overlay only**, confirmed — it never renders as a forecast and
   `IMPACT_GAMMA_M4` governs nothing else.
2. **The measurement/prediction split is binding page copy.** The unwind panel is
   a *scenario* until the §6.4 gate-2 operating characteristic (overlap decile vs
   simulated co-drawdown) exists; if gate 2 fails, M4 ships measurement-only per
   §6.5 — affirmed as the kill criterion.
3. **New substrate approved in principle** (per-asset dollar ADV on
   `MarketConfig`; `ManagerConfig.crowd_participation` default 0.0), both with
   byte-identical defaults and dial-guard tests. **The proposed stream tags 3 and
   4 are superseded**: the batch-2 substrate plan has claimed tags 3
   (`exit_style` random) and 4 (`short_information_coefficient`). M4's dials take
   the next free tags, assigned at the batch-3 substrate plan against the
   widened `test_rng_stream_tags_are_distinct` registry test.
4. **13F rung:** the shared 13F adapter is M6's build; M4's demo is P-tier only,
   and no 13F view renders before the §6.4 gate-3 degradation measurement
   quantifies the staleness/longs-only caveats it must carry.
5. **Constants confirmed:** `PARTICIPATION_LIMIT_M4` = 0.20,
   `STRESS_VOLUME_DELTA_M4` = 0.5, `IMPACT_GAMMA_M4` = 1.0 (overlay only),
   `OVERLAP_ALERT_THRESHOLD` = 0.30 provisional; `MARKET_ADV_RANGE` and the
   shared-universe `N_ASSETS` are set in the batch-3 substrate plan.
6. **Demo names Hollowmere Capital / Brackenford Partners are approved to M4**
   (first claim). P2's colliding roster names are renamed on P2's side (P2 §8
   ruling 6) — cross-card name uniqueness is now checked against the full
   inventory at every build.
