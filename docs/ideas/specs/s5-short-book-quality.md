# S5 · Short-Book Quality Score — Method Spec

**Status: Reviewed — method gate passed 2026-07-07 (rulings in §8)**
**Date:** 2026-07-07
**Card:** [`docs/ideas/2026-07-05-idea-cards.md`](../2026-07-05-idea-cards.md) § S5
**Demo:** gallery page `s5.html` (two-manager hedge-vs-alpha split; fully synthetic, §5)

---

## 1. What this is

S5 answers one underwriting question about a long/short manager: **is the short
book a source of alpha, or is it an expensive beta hedge?** Every equity
long/short book shorts for two reasons at once — to offset the long book's
market exposure (the hedge) and, allegedly, to profit from name-specific
insight on the short side (the alpha). Fees are charged as if both are true.
S5 decomposes the short sleeve's profit and loss into exactly those two
components — a **hedge component** (what the sleeve earned simply by being
short factor exposure) and an **alpha component** (what it earned from
idiosyncratic, name-specific moves) — and then asks whether the alpha
component survives two honest corrections: an uncertainty interval, and the
**cost of borrowing the shares**. Alongside the decomposition it reports the
short sleeve's **hit rate** (how often a short pick beat an uninformed pick),
power-gated so it only renders when the trade count can support it.

The output is a per-manager short-book panel: the hedge share of the sleeve's
P&L, the borrow-cost-adjusted short alpha with its interval, the gated hit
rate, and a verdict chip. The consumer is the **investment team at
underwriting and re-underwriting** — the moment when "this manager runs 160
gross, 20 net, with a genuine short book" is being priced — and the
**engagement conversation** with transparent long/short managers. The
decisions it feeds are **size** (a book whose shorts are pure hedge is a
long-alpha product wearing a beta overlay, and should be sized and priced as
one) and **redeem** (paying long/short fees for hedge-only shorts, when the
long book alone does not clear the bar, is a documented redemption input —
never a mechanical rule).

## 2. Why we use it

The naive read of a short book is the sign of its P&L: "the shorts made money
in the drawdown — they're adding value." That number is almost entirely
uninformative, because a short sleeve *mechanically* makes money whenever the
market falls: being short 0.7 gross of ~beta-1 names is a −0.7 market position
before any skill enters. In a down year the most uninformed short basket in
the world posts a profit, and in a melt-up the most brilliant short-seller
posts a loss. **The sign of the sleeve's P&L is the sign of the market, not
the sign of the skill.** Judging a short book on it rewards whoever happened
to be graded in a down market.

The equally naive opposite — ignore the shorts, judge the whole book on its
blended return — hides the fee question. A manager whose shorts are pure
hedge is selling long-book stock-picking plus an index hedge. The hedge is
real and useful, but it is replicable with index futures at near-zero cost
and no borrow fees; the long/short fee schedule prices it as if it were
skill. Sweep B lists short-book quality as an explicit platform review item
(catalog #10) precisely because platforms internally separate these two
components; allocator-side, almost nobody does.

What S5 wins over both naive reads: it **removes the market from the
question**. The decomposition credits the hedge component to the hedge —
honestly, as a real and priced service — and then asks the residual, on its
own merits, the only question that justifies short-side fees: *net of factor
exposure and net of borrow costs, with an honest interval, is there anything
here?* On the simulator this is testable against known ground truth: a
manager whose shorts genuinely carry signal and a manager whose shorts are
noise-picked beta offset are generated side by side, and the score must tell
them apart (§5, §6.3).

- **Decisions improved:** **size** — underwrite the mandate as what it
  measurably is (long alpha + cheap-to-replicate hedge, or genuine two-sided
  alpha); **redeem** — a documented "paying alpha fees for hedge" finding
  feeds the redemption discussion.
- **Customer:** investment team (underwriting); manager-facing engagement for
  transparent long/short mandates (inside the E1 ladder relationship only).

## 3. How it works

### 3.1 The mental model, before any math

Picture the short sleeve as its own little portfolio: 25 short positions,
totaling −0.7 of the book. Each month, each shorted stock's return splits
into two pieces — the part that any stock with its factor exposures would
have delivered (its market/size/value component), and the part specific to
the name (its idiosyncratic move). Because the sleeve's positions are known
at tier P, so is the split of its P&L: the **hedge component** is the sleeve's
measured factor exposures times the factor returns, and the **alpha
component** is the sleeve's weights times the idiosyncratic returns. The two
add up to the sleeve's P&L exactly — the decomposition is accounting, not
estimation, which is why the card's power verdict calls the classification
Robust: it is measurement.

Now the two demo managers. Both run identical structures — same gross, same
net, same long book quality. The first picks shorts on genuine name-specific
insight; the second picks shorts on nothing (an uninformed basket that exists
only to offset the longs). Both sleeves show a large hedge component —
**around 80% of the P&L variance in both cases** — because that is what
shorting 0.7 gross of equities does regardless of skill. The difference is
entirely in the residual: the first manager's alpha component compounds
steadily upward; the second's wanders around zero. The hedge share tells you
what the sleeve mostly *is*; the residual, interval-reported and net of
borrow, tells you whether the fees on it are buying anything.

One more correction matters and is routinely skipped: **shorting is not
free**. Borrowed shares carry a lending fee — a few tens of basis points a
year for easy-to-borrow ("general collateral") names, punitively more for
crowded specials. A gross short alpha of +1.5%/yr on a sleeve paying 2%/yr in
borrow fees is a *negative*-value activity. S5 always reports short alpha
net of borrow, and in the live build uses the manager's actual per-name
fees where disclosed.

### 3.2 A worked toy example

Three shorts, each at weight −10% of the book, with market betas 1.0, 1.5,
and 0.5. The sleeve's market exposure is

$$x = (-0.10)(1.0) + (-0.10)(1.5) + (-0.10)(0.5) = -0.30 .$$

**Month 1 — the market falls 5%.** The hedge component is
$(-0.30) \times (-5\%) = +1.5\%$. Suppose the three names' idiosyncratic
returns are −2%, −1%, −3% (all three picks were right: the names fell for
name-specific reasons too). The alpha component is
$(-0.10)(-0.02) + (-0.10)(-0.01) + (-0.10)(-0.03) = +0.6\%$. The sleeve
prints $+1.5\% + 0.6\% = +2.1\%$.

**Month 2 — the market rises 3%.** The hedge component is
$(-0.30) \times (+3\%) = -0.9\%$. Idiosyncratic returns: +2%, −4%, −1% (one
pick wrong, two right); the alpha component is
$(-0.10)(+0.02 - 0.04 - 0.01) = +0.3\%$. The sleeve prints
$-0.9\% + 0.3\% = -0.6\%$.

Read the two months together and the whole card is in them. The naive read
says "the shorts made +2.1% in month 1 — short alpha!" — but +1.5 of the +2.1
points was just *being short in a down month*, the payoff of a position an
index future replicates. In month 2 the sleeve **lost** money overall while
the short *picks* **added** +0.3% — skill was present in the losing month.
Across both months the hedge component swings ±1% or more with the market
while the alpha component quietly adds +0.3 to +0.6% — most of the sleeve's
*variance* is hedge, all of its *judgeable skill* is in the small steady
residual. The hit rate over the two months: 5 of the 6 position-months had a
negative idiosyncratic return (a short wins when its name-specific move is
down), a pooled 83% — obviously meaningless at n = 6, which is exactly why
§3.5 gates this statistic on trade count. Finally the borrow drag: 30% short
gross at a flat 2%/yr fee costs $0.30 \times 2\% = 0.6\%$/yr — 5 bps a month,
every month, straight off the alpha component.

### 3.3 The decomposition (tier P: measurement, not estimation)

For a manager with position weights $w_{i,t}$ (fractions of NAV, negative for
shorts), define the short sleeve $w^-_{i,t} = \min(w_{i,t}, 0)$. With a factor
model of the cross-section, the sleeve's monthly return splits as

$$
r^S_t \;=\; \underbrace{x_t^\top f_t}_{\text{hedge}}
\;+\; \underbrace{\textstyle\sum_i w^-_{i,t}\,\varepsilon_{i,t}}_{\text{alpha}},
\qquad
x_t \;=\; B^\top w^-_t
$$

where:

- $r^S_t$ — the short sleeve's return contribution in month $t$ (in units of
  book NAV, a monthly decimal).
- $w^-_t$ — the vector of short position weights in month $t$ (each $\le 0$).
- $B$ — the matrix of per-name factor loadings (row = name, column = factor):
  each stock's exposures to market, size, value, momentum, etc.
- $x_t$ — the sleeve's **measured factor exposure vector** in month $t$: the
  weighted sum of the shorted names' loadings. For a typical hedge book its
  market entry is strongly negative (the offset to the long book).
- $f_t$ — the factor returns in month $t$.
- $\varepsilon_{i,t}$ — name $i$'s idiosyncratic (factor-model residual)
  return in month $t$.
- $x_t^\top f_t$ — the **hedge component**: what any basket with these
  loadings would have returned.
- $\sum_i w^-_{i,t}\varepsilon_{i,t}$ — the **alpha component**: the P&L of
  the name-specific moves, the only part short-side skill can produce.

In words: the sleeve's P&L is its measured exposures times the factor returns,
plus its weights times the idiosyncratic surprises — and given positions and a
factor model, this is an exact identity (the reference implementation asserts
it to machine precision). At tier P nothing here is a regression: $w^-_t$ is
observed, $B$ comes from the risk model, and the split follows. This is the
same pinned-exposure mechanism the X1 atlas uses for its tier-E/P alpha cells,
applied to one sleeve.

Two summary statistics follow.

**Hedge share** — the fraction of the sleeve's variance the hedge explains:

$$
\text{HS} \;=\; 1 - \frac{\operatorname{Var}(a_t)}{\operatorname{Var}(r^S_t)},
\qquad a_t = \textstyle\sum_i w^-_{i,t}\,\varepsilon_{i,t}
$$

where $a_t$ is the alpha component defined above and the variances are sample
variances over the window. In words: how much of what the short book *does*,
month to month, is factor offset. HS near 1 means the sleeve behaves like an
index hedge; HS is **descriptive** — it carries no significance claim and
needs none, because it is a ratio of measured quantities.

**Gross and borrow-adjusted short alpha** — the mean of the alpha component,
annualized, minus the cost of carrying the shorts:

$$
\alpha^S = 12 \cdot \operatorname{mean}(a_t),
\qquad
\alpha^S_{\text{net}} = \alpha^S - c,
\qquad
c = 12 \cdot \operatorname{mean}_t \Big( \textstyle\sum_i \tfrac{\phi_{i,t}}{12}\,\lvert w^-_{i,t}\rvert \Big)
$$

where:

- $\alpha^S$ — the annualized gross short alpha (×12 converts the monthly
  mean; the S1/S2 house convention).
- $\phi_{i,t}$ — the annualized borrow fee on name $i$ in month $t$ (the
  securities-lending fee the manager pays to hold the short).
- $\lvert w^-_{i,t}\rvert$ — the short gross in name $i$.
- $c$ — the annualized borrow drag: the fee-weighted short gross, averaged
  over the window.
- $\alpha^S_{\text{net}}$ — the number the verdict is read from: what the
  short picks earned **after** paying to hold them.

In words: gross short alpha is the average idiosyncratic P&L of the sleeve;
the borrow drag is a deterministic fee bill proportional to how much is
shorted and how expensive each name is to borrow; net alpha is what remains.
The drag enters as a level adjustment, not a regression term, because it is a
known cost, not a risk exposure. In the demo the per-name fee is a flat
general-collateral assumption (**`BORROW_COST_ANNUAL` = 2%/yr, provisional —
NUMERICS-GATE**; §6.5 discusses why flat, and D'Avolio's evidence on the real
fee distribution); the live P-tier build uses actual per-name fees where the
manager or prime broker discloses them.

Uncertainty on $\alpha^S$ is not optional: the alpha component $a_t$ is a
monthly series like any return series, and its mean at $T \le 60$ is noisy.
The live build reuses the S2 tear-sheet interval machinery on $a_t$ — the
HAC (Newey–West) interval cross-checked against a block bootstrap, widened to
the looser of the two — so the panel renders an IntervalStat, never a bare
point.

### 3.4 The fallback ladder (tiers E and R: what degrades, what refuses)

**Tier E (exposure summaries).** Risk reports in the Open Protocol style
disclose long-side and short-side factor exposures separately, but not the
sleeve's return series. That buys the **factor split only** (the card's E
rung): the short sleeve's measured exposure path $x_t$, the hedge-offset
check (does $x_t$ track the *complement* of the long book's exposures — a
hedge signature — or does it move independently?), and the hedge component
$x_t^\top f_t$ reconstructed against published factor returns. What E cannot
buy is the alpha component: without the sleeve's return series the residual
$a_t$ is unobservable, so **no short-alpha estimate renders at E** — the
panel says so rather than inferring it.

**Tier R (returns only).** A blended long/short return series does not
identify its sleeves: infinitely many long/short splits produce the same
total, so long/short attribution from returns alone is underdetermined. The
honest R rung is **refusal** — the panel renders the PowerGate refusal state
("short-book attribution requires disclosed sleeve returns or positions")
plus descriptive gross/net from whatever the manager states. One disclosed
exception: some managers report the short sleeve's monthly return separately
in letters. Where that series exists, S5 runs the **S2-style factor
regression on the disclosed sleeve**:

$$
r^S_t = \alpha^S_{\text{reg}} + \beta^\top f_t + u_t
$$

where $\alpha^S_{\text{reg}}$ is the regression intercept (annualized ×12),
$\beta$ is a *constant* fitted exposure vector, and $u_t$ the residual. The
regression $R^2$ stands in for the hedge share and the intercept (with the
S2 HAC + bootstrap interval) for gross short alpha — with two honest
degradations stated on the panel: the sleeve series is **self-reported**
(chip: "manager-disclosed attribution"), and a constant-beta regression
cannot separate selection alpha from **hedge timing**. If the manager varies
the hedge ratio with skill (or luck), the covariance between the moving
exposure $x_t$ and the factor returns lands in the intercept — the regression
alpha is selection alpha *plus* timing P&L. At P the pinned decomposition
attributes timing to the hedge component exactly (the exposure path is
measured month by month); at R-disclosed it cannot. This gap is a measured
tier-degradation delta in the validation plan (§6.3, gate 4) — the atlas-style
statement of what P buys over R. Note this stays inside the do-not-build
line: S5 never *fits* time-varying betas from returns; at P the time-varying
exposure is **measured**, which is the M1 doctrine (measurement where
measurement exists, no estimation in its place).

### 3.5 The short-side hit rate (gated)

The batting-average question — "how often is a short pick right?" — is asked
against an *active* benchmark, not raw price direction: a short is a good pick
if the name did worse than the month's cross-section, whether or not markets
fell. Following the X1 grid's convention (which exists to kill the mechanical
bias that raw contributions carry), the per-position-month contribution is

$$
g_{i,t} = w^-_{i,t}\,\big(r_{i,t} - \bar r_t\big)
$$

where $r_{i,t}$ is name $i$'s total return, $\bar r_t$ is the month's
cross-sectional (equal-weight universe) mean return, and $g_{i,t} > 0$ marks
a successful short position-month (the shorted name underperformed the
month's market). The hit rate is the share of short position-months with
$g_{i,t} > 0$, and the test against 50% is **month-clustered**: monthly hit
fractions $h_t$ are computed first and the t-statistic uses their spread,
because positions within a month co-move (a pooled binomial test overstates
the sample massively — the X1 numerics gate ruled this for the long book and
the same ruling binds here).

Power is the binding constraint, and the arithmetic is unforgiving. Detecting
a 55% hit rate against 50% at 80% power needs on the order of **780
independent trades** (Sweep C; the S3 card's line). Using the X1 atlas's
independent-trade count (initial book + monthly turnover × window), a 25-name
short book turning over a quarter of the book each month accumulates
$25 + 6 \times 60 \approx 385$ round trips in five years — half the
requirement; the detectable edge at that sample is roughly a **7-point** hit
rate (57% vs 50%), so a modest genuine edge cannot be certified. Even a
ten-year window at this breadth ($25 + 6 \times 120 = 745$) sits just under
the 780 line. The consequence is a design rule, not a footnote: **below the
gate the panel renders "insufficient N," never a hit-rate number.** The gate
threshold is consumed from the X1 PowerGate registry once S5's atlas cells run
(**`SHORT_TRADE_GATE`, provisional — interim value: the 780-trade line —
NUMERICS-GATE**).

### 3.6 The verdict chip

The panel's chip combines the two calibrated statements (never the
descriptive one alone):

- **"Short alpha, calibrated"** — the borrow-adjusted alpha interval excludes
  zero from above. Renders regardless of hedge share: a sleeve can be 80%
  hedge by variance *and* carry real alpha — the two claims are not in
  tension, and the copy says so.
- **"No detectable short alpha net of borrow"** — the interval includes or
  sits below zero. Explicitly *not* "there is no alpha": absence of evidence
  is stated as such, with the interval shown.
- **"Insufficient N"** — the PowerGate refusal, when the trade count (for the
  hit rate) or the window (for the interval) cannot support a claim.

The hedge share renders beside the chip as a descriptive stat with a plain
gloss ("~80% of this sleeve's month-to-month behavior is factor offset").
When HS exceeds **`HEDGE_SHARE_HIGH` = 0.75 (provisional — NUMERICS-GATE)**
*and* the alpha verdict is "no detectable," the panel adds the fee
implication line — the card's wow-demo sentence — in underwriting language:
"this sleeve is priced as alpha and measures as hedge; an index overlay
replicates the hedge component at near-zero fee and no borrow." Per-name
classification (this short is alpha, that one is hedge) ships only as a
**descriptive table** in v1: a single name is held for a handful of months,
and per-name inference at monthly frequency is a claim the data cannot
support — the sleeve-level statements are the calibrated product.

### 3.7 What the canonical papers contribute

- **Boehmer, Jones & Zhang (2008), "Which Shorts Are Informed?"
  (*Journal of Finance*).** Using proprietary order data, showed that
  institutional short sales strongly predict negative abnormal returns —
  heavily shorted stocks underperform lightly shorted ones by economically
  large margins. This is the warrant that genuine short-side stock-picking
  skill exists and is measurable at all: the card is not testing for a
  phantom. It also frames the underwriting stakes — informed shorting is
  real, so distinguishing managers who have it from managers who do not is
  worth fees-level money.
- **D'Avolio (2002), "The Market for Borrowing Stock" (*Journal of Financial
  Economics*).** The institutional map of the securities-lending market:
  most stocks are "general collateral" borrowable at a few tens of basis
  points, while a small tail of "specials" carries fees of hundreds of basis
  points or more, and recalls happen. This grounds S5's borrow adjustment —
  why a flat GC-level constant is an honest *demo* assumption, and why the
  live build must use per-name fees: the expensive tail is exactly where
  aggressive short books live.
- **Drechsler & Drechsler (2016), "The Shorting Premium."** Documented that
  the apparent alpha to shorting expensive-to-borrow stocks is largely eaten
  by the borrow fee itself — gross and fee-adjusted short returns tell
  different stories. This is the direct evidence for reporting
  $\alpha^S_{\text{net}}$, never $\alpha^S$ alone: a gross short alpha that
  does not clear the fee is not alpha the allocator can buy.
- **Engelberg, Reed & Ringgenberg (2018), "Short-Selling Risk"
  (*Journal of Finance*).** Showed that the *risk* of borrow-fee spikes and
  recalls — not just their level — deters arbitrage and predicts returns.
  This is why S5 treats borrow-crowding context (short interest,
  days-to-cover on top shorts) as a stress lens on the sleeve, and why that
  overlay is deferred rather than faked (§6.4): squeeze dynamics are a real
  phenomenon the v1 simulator does not credibly reproduce.
- **Grinold & Kahn, *Active Portfolio Management* (2nd ed.), the fundamental
  law.** $\text{IR} \approx \text{IC}\sqrt{\text{breadth}}$: skill per pick
  times the square root of the number of independent picks. The short sleeve
  of a typical book has *low breadth* (25 names, monthly turnover), which is
  the deep reason §3.5's power arithmetic is so binding — and why the same
  true IC that is certifiable on a high-turnover quant short book is
  undetectable on a concentrated one.

## 4. How to implement

The reference implementation below is **self-contained teaching code** — paste
it into a fresh file; it runs on `numpy` alone, no project imports. It builds
a small factor market, simulates the two demo managers (identical long books,
short books differing only in short-side signal quality), and computes every
§3 statistic: the exact hedge/alpha decomposition (§3.3, with the identity
asserted), hedge share, gross and borrow-adjusted short alpha, and the
month-clustered short hit rate (§3.5). Running it prints the §5 numbers.

```python
"""S5 short-book quality score — self-contained reference mock (numpy only).

Two synthetic long/short managers differ ONLY in short-side signal quality:
  - the alpha-short book: shorts carry a real idiosyncratic forecast (short IC > 0);
  - the hedge-short book: shorts are picked on pure noise (short IC = 0), so the
    sleeve is a beta offset and nothing more.
Both books target the same gross and net, so both sleeves hedge the long book's
market exposure; the question the score answers is whether the shorts do anything
BEYOND that offset.

Per short sleeve it computes:
  hedge share          = 1 - Var(idiosyncratic sleeve P&L) / Var(total sleeve P&L)
  gross short alpha    = intercept of the sleeve's factor regression (annualized)
  borrow-adjusted alpha = gross short alpha - flat borrow-cost drag
  short hit rate       = active batting average of short position-months,
                         month-clustered t-test against 50%
"""

from math import sqrt

import numpy as np

MONTHS_PER_YEAR = 12
_MARKET_STREAM, _MANAGER_STREAM = 0, 1


# --- a tiny factor market (self-contained analogue of a factor-model world) --
def make_market(n_assets: int, n_months: int, seed: int):
    """Factor returns, per-asset betas, idiosyncratic returns, total returns."""
    rng = np.random.default_rng([seed, _MARKET_STREAM])
    annual_means = np.array([0.06, 0.02, 0.03])   # market, size, value
    annual_vols = np.array([0.16, 0.08, 0.10])
    factor_returns = rng.normal(
        annual_means / MONTHS_PER_YEAR,
        annual_vols / sqrt(MONTHS_PER_YEAR),
        size=(n_months, 3),
    )
    market_beta = rng.normal(1.0, 0.25, size=n_assets)
    style_betas = rng.normal(0.0, 0.5, size=(n_assets, 2))
    betas = np.column_stack([market_beta, style_betas])          # (n_assets, 3)
    idio_vols = rng.uniform(0.20, 0.45, size=n_assets) / sqrt(MONTHS_PER_YEAR)
    idio_returns = rng.normal(0.0, idio_vols, size=(n_months, n_assets))
    asset_returns = factor_returns @ betas.T + idio_returns
    return factor_returns, betas, idio_returns, asset_returns


# --- a manager with SEPARATE long-side and short-side signal quality ---------
def simulate_weights(idio_returns, *, n_long, n_short, gross, net,
                     long_ic, short_ic, seed):
    """Monthly book weights. Longs picked on a long-signal panel at long_ic;
    shorts picked on a SECOND, decorrelated signal panel at short_ic.
    short_ic = 0 makes the short sleeve an uninformed (pure-hedge) basket."""
    n_months, n_assets = idio_returns.shape
    rng = np.random.default_rng([seed, _MANAGER_STREAM])
    z = idio_returns / idio_returns.std()          # standardized ground truth
    noise_long = rng.standard_normal((n_months, n_assets))
    noise_short = rng.standard_normal((n_months, n_assets))
    signal_long = long_ic * z + sqrt(1.0 - long_ic**2) * noise_long
    signal_short = short_ic * z + sqrt(1.0 - short_ic**2) * noise_short

    long_total = (gross + net) / 2.0
    short_total = (gross - net) / 2.0
    weights = np.zeros((n_months, n_assets))
    for t in range(n_months):
        longs = set(np.argsort(signal_long[t])[-n_long:])        # best longs
        shorts = [i for i in np.argsort(signal_short[t])         # worst shorts,
                  if i not in longs][:n_short]                   # disjoint
        weights[t, list(longs)] = long_total / n_long            # equal-weight
        weights[t, shorts] = -short_total / n_short              # sleeves
    return weights


# --- the S5 decomposition: hedge vs alpha, borrow-adjusted -------------------
def short_sleeve_quality(weights, betas, factor_returns, idio_returns,
                         borrow_annual):
    """Decompose the short sleeve's monthly P&L and score it."""
    short_w = np.where(weights < 0.0, weights, 0.0)   # short weights only (<= 0)
    exposure_path = short_w @ betas                   # sleeve factor exposures
    hedge_pnl = (exposure_path * factor_returns).sum(axis=1)   # systematic part
    alpha_pnl = (short_w * idio_returns).sum(axis=1)           # idiosyncratic part
    sleeve_pnl = hedge_pnl + alpha_pnl               # exact identity (see check)

    # Hedge share: fraction of sleeve P&L variance the factor offset explains.
    hedge_share = 1.0 - alpha_pnl.var(ddof=1) / sleeve_pnl.var(ddof=1)

    # Gross short alpha: intercept of the sleeve's factor regression (plain OLS
    # SE here for teaching; the live build reuses the S2 HAC + bootstrap CI).
    n_months = len(sleeve_pnl)
    design = np.column_stack([np.ones(n_months), factor_returns])
    coef, *_ = np.linalg.lstsq(design, sleeve_pnl, rcond=None)
    resid = sleeve_pnl - design @ coef
    dof = n_months - design.shape[1]
    resid_var = float(resid @ resid) / dof
    se_alpha_monthly = sqrt(resid_var * np.linalg.inv(design.T @ design)[0, 0])
    alpha_annual = float(coef[0]) * MONTHS_PER_YEAR
    se_annual = se_alpha_monthly * MONTHS_PER_YEAR

    # Borrow drag: flat annual fee on average short gross (demo assumption).
    short_gross = np.abs(short_w).sum(axis=1).mean()
    borrow_drag_annual = borrow_annual * short_gross
    return {
        "hedge_pnl": hedge_pnl,
        "alpha_pnl": alpha_pnl,
        "sleeve_pnl": sleeve_pnl,
        "hedge_share": hedge_share,
        "alpha_annual": alpha_annual,
        "alpha_t": alpha_annual / se_annual,
        "borrow_adj_annual": alpha_annual - borrow_drag_annual,
        "borrow_drag_annual": borrow_drag_annual,
    }


def short_hit_rate(weights, asset_returns):
    """Active batting average of the short sleeve: share of short position-months
    with active contribution w * (r - month cross-sectional mean) > 0, tested
    against 50% with a month-clustered t (cross-positional correlation makes a
    pooled binomial test miscalibrated)."""
    hedged = asset_returns - asset_returns.mean(axis=1, keepdims=True)
    contributions = np.where(weights < 0.0, weights, 0.0) * hedged
    monthly_fractions = []
    for month_row in contributions:
        nonzero = month_row[month_row != 0.0]
        if len(nonzero):
            monthly_fractions.append(float((nonzero > 0.0).mean()))
    pooled = contributions[contributions != 0.0]
    hit = float((pooled > 0.0).mean())
    h = np.asarray(monthly_fractions)
    se = float(h.std(ddof=1) / sqrt(len(h)))
    t_stat = (float(h.mean()) - 0.5) / se
    return hit, t_stat


if __name__ == "__main__":
    N_ASSETS, SEED = 120, 7
    BORROW_ANNUAL = 0.02       # flat 2%/yr general-collateral assumption (named)
    BOOK = dict(n_long=40, n_short=25, gross=1.6, net=0.2)

    for n_months in (120, 60):
        factor_returns, betas, idio, asset_returns = make_market(
            N_ASSETS, n_months, SEED)
        print(f"\n=== T = {n_months} months ===")
        for name, short_ic in [("alpha-short book", 0.06),
                               ("hedge-short book", 0.00)]:
            w = simulate_weights(idio, long_ic=0.06, short_ic=short_ic,
                                 seed=SEED, **BOOK)
            q = short_sleeve_quality(w, betas, factor_returns, idio,
                                     BORROW_ANNUAL)
            hit, hit_t = short_hit_rate(w, asset_returns)
            # Identity check: hedge + alpha reproduces the sleeve P&L exactly.
            true_sleeve = (np.where(w < 0, w, 0.0) * asset_returns).sum(axis=1)
            assert np.max(np.abs(q["sleeve_pnl"] - true_sleeve)) < 1e-12
            print(f"{name} (short IC = {short_ic:.2f})")
            print(f"  hedge share               : {q['hedge_share']*100:5.1f}%")
            print(f"  gross short alpha (ann)   : {q['alpha_annual']*100:+5.2f}%"
                  f"  (t = {q['alpha_t']:+.2f})")
            print(f"  borrow-adjusted alpha     : {q['borrow_adj_annual']*100:+5.2f}%"
                  f"  (drag {q['borrow_drag_annual']*100:.2f}%/yr)")
            print(f"  short hit rate            : {hit*100:5.1f}%"
                  f"  (t = {hit_t:+.2f} vs 50%)")
```

Run it and the T = 120 block prints the §5 demo numbers: the alpha-short book
at hedge share 82.7%, gross short alpha +4.92%/yr (t = +3.55),
borrow-adjusted +3.52%, hit rate 52.5% (t = +2.99); the hedge-short book at
hedge share 80.1%, gross alpha −0.11%/yr (t = −0.08), borrow-adjusted
**−1.51%**, hit rate 50.1% (t = +0.15). The T = 60 block then prints the
honesty lesson §6.3 turns into a validation gate: on this single seed the
*pure-hedge* book posts a nominally significant hit rate (52.1%, t = +2.02)
— a five-year window of a 25-name sleeve is lucky-draw territory, which is
exactly why the trade-count gate exists.

## 5. Reading the demo

The gallery page `s5.html` is fully synthetic (SYNTHETIC badge; §6.6
compliance) and is built as a two-manager split — the S5 analogue of M3's
same-drawdown centerpiece. Two managers with **identical structures** (160
gross / 20 net, 40 longs, 25 shorts, same long-side skill) and **identical
headline returns to the naked eye**, differing only in ground truth the
simulator knows:

- **Kestrel Point Partners** — shorts carry genuine signal (short-side
  IC = 0.06, equal to its long side). Panel: hedge share **82.7%**; gross
  short alpha **+4.92%/yr** with a clearly-positive interval (t = +3.55);
  borrow-adjusted alpha **+3.52%/yr** after the 1.40%/yr drag (2%/yr flat fee
  on 0.70 average short gross); hit rate **52.5%** (month-clustered
  t = +2.99). Chip: **"Short alpha, calibrated."**
- **Drybrook Capital** — shorts picked on pure noise (short-side IC = 0): an
  uninformed basket that exists to offset the longs. Panel: hedge share
  **80.1%**; gross short alpha **−0.11%/yr**, dead on zero (t = −0.08);
  borrow-adjusted alpha **−1.51%/yr**; hit rate **50.1%** (t = +0.15). Chip:
  **"No detectable short alpha net of borrow"** — plus the fee-implication
  line, because HS > 0.75: *"~80% of this sleeve is factor offset an index
  overlay replicates at near-zero fee and no borrow."*

The point the page makes: both books look like "real" long/short mandates,
both sleeves are ~80% hedge by variance — **the hedge share alone does not
convict anyone** — and the entire fee-relevant difference lives in the
residual, which only an interval-reported, borrow-adjusted decomposition
surfaces. The demo window is ten years (**`S5_DEMO_MONTHS` = 120,
provisional — NUMERICS-GATE**), deliberately generous: the honest message is
that *even with* a decade of positions, the hit-rate certification barely
clears (745 round trips vs the ~780-trade line), and at a realistic five-year
window the gate refuses.

How each visual element maps to the method:

- **The cumulative-P&L split chart** (per manager) — the sleeve's compounded
  P&L drawn as two stacked series: the hedge component $x_t^\top f_t$ and the
  alpha component $a_t$ (§3.3). Kestrel's alpha line grinds steadily upward;
  Drybrook's wanders around zero while both hedge lines swing with the
  market. This chart *is* the decomposition identity, drawn.
- **The borrow-adjusted alpha rail** — an IntervalStat: the point is
  $\alpha^S_{\text{net}}$, the band is its 90% interval, with a tick showing
  the gross $\alpha^S$ so the borrow drag is visible as the gap.
- **The borrow dial** (the Dietvorst adjustable control) — a slider sweeping
  the flat borrow assumption across 0–5%/yr (precomputed grid; the page never
  computes). Dragging it shows Drybrook's verdict is robust to the fee
  assumption (its gross alpha is already zero) while Kestrel's net alpha
  stays positive until an implausible ~7%/yr average fee — the skeptical
  reader can try to break the verdict and watch it hold.
- **The hit-rate PowerGate** — at the demo's T = 120 both hit rates render
  with their clustered t; a companion toggle shows the same books at T = 60,
  where the gate flips to **"insufficient N (385 round trips; gate ~780)"**
  and refuses the number. The refusal is the pitch: the T = 60 single-seed
  table in §4 shows a noise book luck-passing a naive test at exactly this
  window.
- **The tier strip** — the same two managers rendered at E (factor split
  only: exposure paths and the hedge-offset check, no alpha claim) and at R
  (the refusal state, with the "manager-disclosed sleeve" exception
  explained). TierBadges on every panel; the strip is the card's honest
  answer to "can't you do this from returns?" — no, and here is exactly what
  each tier buys.
- **The go-live box** — the standing gallery contract (§6.7).

What an allocator should conclude: two mandates that look identical and
charge identical fees measurably differ in what the short-side fee is buying
— one funds genuine name-specific alpha (+3.5%/yr net of borrow, calibrated),
the other funds a beta hedge (−1.5%/yr net of borrow) replicable with
futures. Underwrite and size them as different products.

**Demo-vs-live split, stated.** Demo numbers are computed from simulator
ground truth ($B$ and $\varepsilon$ known exactly, decomposition exact) by
the same code path a live build would run. A live P-tier deployment replaces
ground truth with: a commercial risk model's loadings for $B$
(buy-don't-build — convergence decision §4), the manager's or prime broker's
per-name borrow fees for $\phi_{i,t}$, and FINRA short-interest /
days-to-cover for the crowding context panel (deferred adapter, §6.5). The
demo carries no squeeze/crowding panel at all rather than a faked one (§6.4).

## 6. Honest limits & go-live

### 6.1 What S5 does not do (do-not-build adjacency)

- **No regime-split tables.** "How do the shorts do in down markets?" is a
  regime-split alpha table — on the do-not-build list (convergence §4). S5
  needs no regime split: the hedge component *already prices* the
  down-market payoff explicitly, every month, without conditioning the
  sample.
- **No time-varying-beta estimation.** At P the exposure path is *measured*;
  at R-disclosed the regression uses constant betas and the panel states the
  timing-leak caveat (§3.4). S5 never fits conditional-beta models from
  returns — also on the do-not-build list.
- **No persistence ranking and no FDR screen.** S5 makes one calibrated
  statement per sleeve per window; it does not rank managers on trailing
  short alpha, test persistence, or run cross-manager discovery screens.
  Roster-level comparison of sleeve alphas, when wanted, goes through the S1
  hierarchical shrinkage (the house method at small N), not a significance
  filter.
- **No squeeze prediction.** Borrow-crowding context (short interest,
  days-to-cover) is a stress *lens*, deferred with the FINRA adapter; S5
  never claims to predict squeezes.
- **Not S3.** Entry-aligned event-study alpha curves on short trades (decay,
  holding-period profiles) are S3's machinery; where a transparent short
  book clears S3's gates, S5's panel links to that lab rather than rebuilding
  it.

### 6.2 Data contract per tier

| Tier | Inputs the live version needs | What the card produces |
| --- | --- | --- |
| **P** (native) | Month-end positions with signed weights (or holdings + NAV); a factor risk model's per-name loadings (bought, per convergence §4); factor returns; per-name borrow fees where disclosed (else the flat assumption, labeled); risk-free series | The **full score**: exact hedge/alpha decomposition, hedge share, borrow-adjusted short alpha with S2-machinery interval, gated hit rate, verdict chip, descriptive per-name table |
| **E** | Short-side factor exposure summaries (Open Protocol-aligned), long-side exposures for the offset check | **Factor split only**: measured short exposure path, hedge-offset check vs the long book's complement, reconstructed hedge component. **No alpha estimate** — the residual is unobservable at E, and the panel says so |
| **R** | Blended monthly returns | **Refusal** (long/short attribution from blended returns is underdetermined) + descriptive stated gross/net. *Exception:* manager-disclosed short-sleeve monthly returns → the §3.4 regression fallback, chipped "manager-disclosed attribution," constant-beta timing caveat stated |

Frequency: monthly, `PeriodIndex` freq `M`, decimals (house convention).
Window: the manager's evaluated track; every statistic renders with the
window stated. Missing position months at P: the decomposition simply skips
them; more than 2 gaps in the window flags the panel as partial (S1
convention).

### 6.3 Power & validation plan

Validation runs on the simulator with known ground truth; cells contribute to
the X1 atlas as S5's rows and **share S3's cells** where the statistic is
shared (hit rate, trade-count gate). New atlas axis required: the short-side
IC (§6.5 prerequisite). Grid: short IC ∈ {0, 0.02, 0.04, 0.07} × long
IC = 0.04 fixed × T ∈ {36, 60, 120} × n_short ∈ {15, 25, 50} ×
turnover {0.25} ; ≥500 seeded replications per cell (per-module RNG streams;
Wilson intervals on every rate, X1 convention).

Acceptance gates:

1. **Size on the hedge book (the load-bearing gate).** At short IC = 0, the
   borrow-adjusted alpha interval excludes zero from above in ≤ the nominal
   rate of replications (a 90% interval → ≤ 5% one-sided within MC error),
   and the month-clustered hit-rate test fires in ≈ 5%. The single-seed
   T = 60 result in §4 (a noise book luck-passing at t = +2.02) is exactly
   the event this gate bounds the frequency of.
2. **Power on the alpha book — reported as curves, not pass/fail.** Detection
   rate of the calibrated-alpha verdict as a function of short IC × T ×
   n_short. These curves *are* the S5 atlas content and set
   `SHORT_TRADE_GATE`; the prior expectation (Sweep C: Shrink,
   trade-count-gated) is that concentrated books need long windows and only
   high-breadth/high-turnover short books certify at T ≤ 60.
3. **Hedge-share accuracy.** The pinned hedge share matches ground truth
   (computable exactly in the simulator) to within MC tolerance —
   measurement behaving as measurement; and the R-disclosed regression $R^2$
   is reported beside it as the tier-degradation delta.
4. **Timing-leak measurement (P vs R-disclosed).** Give the hedge book a
   drifting net via the existing `net_drift` dial (the M1 mechanism — no new
   substrate) and measure how much exposure-timing P&L leaks into the
   R-disclosed regression intercept while the P-tier pinned alpha stays
   clean. This quantifies §3.4's degradation statement instead of asserting
   it.

### 6.4 Kill criteria

- **Data honesty (the card's own kill).** Borrow-cost realism is hard to
  fake credibly. v1 resolves this by *scoping, not simulating*: the demo
  uses a flat, clearly-labeled GC-level fee and ships **no squeeze or
  crowding panel at all** — deferring that rung (with the FINRA adapter and
  any hard-to-borrow simulator work) rather than demoing a toy. If the
  method review judges even the flat-fee demo misleading, the
  borrow-adjustment row renders as a stated assumption band (fee ∈
  [0.3%, 3%]) instead of a point drag — and if *that* still cannot be made
  honest, the card defers, in writing.
- **Statistical.** If gate 1 fails — the score certifies short alpha on
  noise-picked sleeves above nominal rates — the alpha verdict is pulled and
  S5 ships as **classification-only** (hedge share + factor split, all
  descriptive) until fixed. If gate 2 shows no realistic cell (short IC ≤
  0.07, T ≤ 120) certifies at typical concentration, that finding publishes
  as atlas content and the verdict chip's positive state is retired for
  concentrated books: "this cannot be certified at this breadth" is a
  first-class product answer.
- **Political.** The fee-implication line is underwriting language for the
  investment team; any manager-facing version ships only inside the E1
  ladder relationship, framed as the shared question ("what is the short
  book for, and is it priced as what it is?") with the borrow dial exposed —
  never as an accusation. If a pilot conversation reads as audit, the
  manager-facing version is pulled (the S4 precedent).

### 6.5 How it ships in the repo

The commitment: reuse the existing substrate, add one simulator dial and one
thin pipeline.

- **Named simulator prerequisite — the short-side IC split dial.** The
  current `simulator/manager.py` `ManagerConfig` carries a single
  `information_coefficient` driving one signal panel that picks *both* sides
  (longs from the top of the sort, shorts from the bottom) — a
  short-IC-equals-long-IC world by construction, which cannot express the
  demo's hedge-short manager. Extension:
  `short_information_coefficient: float | None = None` — `None` keeps the
  single-panel behavior and consumes no new RNG draws (**byte-identical
  honest manager**, the `death_month`/`net_drift` pattern); a value draws a
  second, decorrelated noise panel *after* the existing draws (long-side
  signals unchanged) and selects/sizes the short side on
  `short_ic * z + sqrt(1 - short_ic^2) * noise_short`. Validation guard:
  value in [0, 1], mirroring the existing IC guard. This dial is also the
  prerequisite for S5's atlas axis (§6.3) and is small (S).
- **New module `src/quant_allocator/flagships/shortbook/pipeline.py`** — pure
  functions, no rendering, no I/O (S2 convention):
  `decompose_short_sleeve(weights, betas, factor_returns, idio_or_riskmodel_resid) -> SleeveDecomposition`
  (the §3.3 identity), `hedge_share(...)`, and
  `borrow_adjusted_alpha(alpha_pnl, borrow_fees, short_gross) -> AlphaStats`.
  **Reused, not reimplemented:** the interval machinery is S2's
  `tearsheet/pipeline.py` (`regress`, `alpha_interval` — HAC + block
  bootstrap, widen-to-looser) applied to the sleeve series for the
  R-disclosed fallback; the hit-rate test is the X1 kernel
  (`demo_data/x_metrics.hit_rate`, month-clustered, on
  $w^-(r - \bar r_t)$ contributions per the shared-grid ruling); the pinned
  mechanism mirrors `x_metrics.pinned_alpha`; tier emission is
  `simulator/tiers.emit_tiers` (P-tier weights, E-tier exposure paths);
  roster-level pooling of sleeve alphas, if rendered, imports
  `skill_ledger/empirical.shrink_alphas` — never a re-fit.
- **Demo — `src/quant_allocator/demo_data/s5_shortbook.py`**: builds the two
  managers (short IC 0.06 vs 0.00) via the new dial, computes the panel via
  the pipeline, precomputes the borrow-dial grid (0–5%/yr) and the
  T ∈ {60, 120} gate toggle, and emits `site/data/s5_shortbook.json` via
  `_emit.write_json`. CI renders from JSON only; CI never computes
  (demo-layer doctrine).
- **Deferred substrate (named, not needed for the demo):** the FINRA
  short-interest adapter (bi-monthly, free) for the live crowding-context
  panel; per-name borrow-fee ingestion (prime-broker or manager files); any
  hard-to-borrow/squeeze simulator realism (deferred with the card's own
  kill criterion, §6.4).
- **Provisional constants (all NUMERICS-GATE):** `BORROW_COST_ANNUAL` = 0.02
  (flat GC demo fee; D'Avolio's distribution says real books are lumpier —
  the dial exposes the assumption); `HEDGE_SHARE_HIGH` = 0.75 (fee-line
  threshold); `SHORT_TRADE_GATE` = the 780-independent-trade line interim,
  replaced by the §6.3 gate-2 curves; `S5_DEMO_MONTHS` = 120 (demo window;
  deliberately generous, stated on the page); demo dials
  `long IC = short IC = 0.06` for the alpha book.
- **Effort:** the card says **M–L**; the demo-scope build is **M** (dial S,
  pipeline + demo M) *because* the L-rated parts — borrow realism and the
  FINRA adapter — are explicitly deferred, not compressed.
- **Sequencing:** after S3 in the post-buy-in order (shared gate machinery
  and, for transparent books, the event-study link); the demo has no S3
  dependency.

### 6.6 Adoption & packaging

- **Underwriting language, help-framed.** The headline is never "your shorts
  add no value." It is: "the short book delivers a measured hedge (real,
  priced service) plus a residual we can/cannot certify as alpha net of
  borrow — here is what that means for how the mandate is priced and sized."
  A hedge-short finding argues for *re-pricing or restructuring* (e.g., long
  book + overlay), not automatically for redemption.
- **Where it renders.** Inside the S2 tear sheet as the short-book panel for
  long/short managers at P (and the factor-split lite version at E); the
  underwriting memo cites the panel. No standing dashboard.
- **Adjustable outputs (Dietvorst).** The borrow-fee dial is the standing
  control; a skeptical reader stress-tests the verdict themselves. The
  hit-rate gate threshold is displayed with its provenance (X1 registry),
  not hidden.
- **Compliance (standing).** Synthetic managers only in the repo; any
  real-data rung uses public sources (FINRA short interest, published factor
  returns) and no employer-internal facts or manager names, ever.

### 6.7 Go-live requirements (demo-page box, expanded)

- **Data ask:** tier P — month-end positions, a risk-model loadings feed
  (bought), per-name borrow fees where available; tier E buys the factor
  split only; tier R is a refusal unless the manager discloses sleeve
  returns. This box *is* the transparency conversation: the card is a
  concrete reason to ask for P.
- **Sample required:** the decomposition and hedge share are honest at any
  T (measurement); the **alpha verdict** needs the interval to speak
  (T ≥ 36 to render, wide until ~60+); the **hit rate** is gated on
  independent trades — a 25-name, quarter-turnover sleeve needs ~10 years
  (745 trades vs the ~780 line); high-turnover short books certify in 1–2
  years. Below gates the panel refuses, and the refusal is stated as the
  product working.
- **Build effort:** M (demo scope; borrow realism and FINRA adapter
  deferred). Upstream: the short-side IC simulator dial (S, named
  prerequisite).

## 7. Deeper reading

**Canonical references (read in this order):**

1. **Boehmer, Jones & Zhang (2008), "Which Shorts Are Informed?" (*JF*).**
   Institutional short flow predicts negative abnormal returns — genuine
   short-side skill exists and is measurable; the card's warrant.
2. **D'Avolio (2002), "The Market for Borrowing Stock" (*JFE*).** The borrow
   market's institutional facts: general collateral vs specials, fee levels,
   recalls — grounds the borrow adjustment and its live per-name data ask.
3. **Drechsler & Drechsler (2016), "The Shorting Premium."** Fee-adjusted
   and gross short returns tell different stories; why
   $\alpha^S_{\text{net}}$, never $\alpha^S$ alone, is the reported number.
4. **Engelberg, Reed & Ringgenberg (2018), "Short-Selling Risk" (*JF*).**
   Borrow-fee and recall *risk* — the reason crowding context matters and
   the reason S5 defers it rather than faking it.
5. **Grinold & Kahn, *Active Portfolio Management*, the fundamental law.**
   IR ≈ IC·√breadth: why the short sleeve's low breadth caps what any test
   can certify at allocator-relevant windows.

**Derivations to own (work each by hand once):**

1. **The decomposition identity.** From $r_i = \beta_i^\top f + \varepsilon_i$,
   show $\sum_i w^-_i r_i = (B^\top w^-)^\top f + \sum_i w^-_i \varepsilon_i$
   — one line of algebra, and the reason the P-tier split is accounting, not
   estimation.
2. **The timing leak.** With a time-varying exposure $x_t$, show the
   constant-beta regression intercept equals the mean alpha component *plus*
   $\operatorname{tr}\,\operatorname{Cov}(x_t, f_t)$-type terms — i.e.,
   hedge-timing P&L masquerades as alpha in the R-disclosed fallback, and
   only the measured exposure path (tier P) removes it.
3. **The hit-rate power line.** From the one-sample proportion test,
   $n \approx (z_{0.975} + z_{0.8})^2\, p(1-p) / \delta^2 \approx 780$ for
   55% vs 50% at 80% power; then convert a 25-name, 25%-turnover sleeve into
   independent trades per the X1 convention (initial book + monthly
   replacements × T) and derive the ~7-point detectable edge at T = 60.
4. **Why borrow enters as a level, not a factor.** The fee bill is a
   deterministic function of gross and fee schedule — a cost, not a priced
   risk exposure; subtracting it from the intercept is the correct treatment
   and putting it in the regression is not.

**Questions you should be able to answer after reading this page:**

- Explain to an investment committee why a short book that made +8% in a down
  year may contain zero short alpha — and why a short book that *lost* money
  may contain plenty (the toy example's two months, retold in 60 seconds).
- State why an ~80% hedge share is not an accusation: hedging is what shorts
  are structurally *for*; the underwriting question is what the residual
  earns net of borrow, and whether the fee schedule prices the sleeve as the
  hedge it mostly is.
- Explain why per-name "this short is alpha, that one is hedge" claims are
  rendered descriptive-only at monthly frequency — and what sleeve-level
  aggregation buys statistically.
- Walk through what each tier buys: P = exact decomposition + timing
  separation + per-name fees + gated hit rate; E = factor split and the
  hedge-offset check, no alpha; R = refusal, because blended returns do not
  identify sleeves — and why the manager-disclosed exception carries both a
  provenance chip and a timing caveat.
- State why the demo's T = 60 luck-pass (a noise sleeve at hit-rate
  t = +2.02) is the argument *for* the trade-count gate, not against the
  method — and what the gate's ~780-trade line is derived from.

## 8. Method-review gate rulings (2026-07-07)

1. **`BORROW_COST_ANNUAL` = 0.02 flat GC approved for the demo** — *because*
   the 0–5%/yr borrow dial makes the assumption adjustable (Dietvorst) and the
   D'Avolio labeling is on the panel. Live builds use per-name fees where
   disclosed; the stated-assumption-band fallback of §6.4 stands if the flat
   fee is ever judged misleading.
2. **`S5_DEMO_MONTHS` = 120 approved**, with the "deliberately generous"
   sentence as required, test-pinned copy, and the T = 60 gate-refusal toggle
   mandatory on the page.
3. **Hedge-share robustness check added to the build plan:** the "~80% in both
   books" claim (§3.1) must hold across a ≥20-seed sweep (both books' hedge
   shares inside ~[0.70, 0.90]); if the sweep fails, the spec copy is
   corrected at the numerics gate. The page quotes the pinned seed's exact
   values either way.
4. **No roster/shrinkage panel in the demo.** The demo is the two-manager
   split only; the `shrink_alphas` roster pooling is live-build scope.
5. **Interval machinery is the S2 pipeline, not the teaching-code OLS SE.**
   The demo JSON's alpha interval comes from `tearsheet/pipeline.py` (HAC +
   block bootstrap, widen-to-looser). §5's quoted t-values are teaching-code
   values and will be re-certified against the generator's pipeline output at
   the batch numerics gate; spec text is updated then if they shift.
6. **Rename:** the alpha-short manager "Kestrel Point Partners" is renamed
   **Saxbridge Capital** — too close to M5/S2's "Kestrelmoor Partners" for
   cross-page reading. "Drybrook Capital" approved.
7. **`short_information_coefficient` dial approved as specified:** default
   `None` is byte-identical (no new draws consumed); an active value draws its
   second, decorrelated short-signal panel *after* all existing draws under a
   new named stream tag; guard value ∈ [0, 1]. Ships in the batch-2
   shared-substrate plan.
8. **`SHORT_TRADE_GATE`:** interim 780-trade line approved; replaced by the
   §6.3 gate-2 power curves and consumed from the X1 registry once S5's atlas
   rows land. `HEDGE_SHARE_HIGH` = 0.75 confirmed.
