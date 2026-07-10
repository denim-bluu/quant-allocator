# M2 · Hidden-Convexity / Short-Vol Screen — Method Spec

**Date:** 2026-07-07
**Status:** Reviewed — method gate passed 2026-07-07 (rulings in §8)
**Card:** [`docs/ideas/2026-07-05-idea-cards.md`](../2026-07-05-idea-cards.md) § M2
**Demo:** gallery page `m2.html` (wave-2 batch 1; two-manager convexity screen, fully synthetic, §5)

---

## 1. What this is

This screen reads a manager's monthly return track and asks one narrow question:
**is the shape of the payoff hiding sold optionality?** A book that quietly sells
insurance — writes puts, runs short-gamma carry, or holds an illiquid position
marked to a slow-moving average — collects a small, steady premium every calm month
and pays it all back, and more, the month a tail arrives. The premium flatters every
*average-based* number on a tear sheet (Sharpe, alpha, beta) right up until the
payback. The screen looks past the average at the geometry of the return stream and
produces a small battery of **convexity diagnostics**, each reported with an
uncertainty interval, composited into a single flag that says only "this is worth a
closer look," never "this book is short volatility."

It is built for an investment team and the risk-adjacent leadership they report to,
and it is meant to be read at monitoring cadence — the moment where you decide whether
to keep watching a manager (**monitor**) or to reprice and resize the mandate
(**redeem**). Its whole reason to exist is the common case where all you have is a
return series and a market index: the optionality is never disclosed, so it has to be
*inferred from the returns themselves*. When holdings or exposure reports are
available they do not sharpen the inference — they confirm or contradict it, and that
comparison is the product at those richer data tiers.

## 2. Why we use it

The decision problem is that a smooth Sharpe can be a warning, and the standard
tear sheet cannot tell you when. Consider two managers who report the *same* Sharpe
to two decimals over the same window. One earns it by taking honest, roughly
symmetric market risk. The other earns it by selling downside protection: most months
the premium lands and the track looks pristine; occasionally the market falls hard and
the book gives back far more than a symmetric position would. On the linear tear
sheet these two are indistinguishable, because a linear factor regression fits the
*average* sensitivity to the market and throws away the part of the payoff that bends
— which is exactly where short-vol posture lives.

Why do the naive alternatives fail? The obvious move — "split the sample into good and
bad markets and compare the manager's performance in each" — is statistically hopeless
at the sample sizes we actually have (36–60 monthly observations). Splitting a tiny
sample in two to read a *conditional average return* halves an already-underpowered
estimate and invites you to over-read noise; it is on the program's do-not-build list
for exactly this reason (see §3 and §6). The other naive move — trusting realized
volatility — is precisely what a short-vol book defeats: its month-to-month vol looks
benign, and the danger is in the tail the vol does not see.

What the screen wins is a way to surface left-tail exposure **before it detonates**,
on a sheet that a benign realized vol cannot fool, and to reframe a persistent
short-vol posture as what it is: a paid-for beta-carry bet that should be **sized and
priced as one**, not mistaken for uncorrelated alpha. The framing is load-bearing and
deliberately non-accusatory. A short-vol posture is a legitimate strategy, not
misconduct; the screen's copy is "this book's returns carry a concave,
short-volatility signature — here is what that implies for tail sizing," never "the
smooth Sharpe is fake." The **redeem** decision it feeds is about mispricing, not
integrity. And because a published short-vol *score* would get gamed (a manager can
reshape marks to dodge a single coefficient), the deliverable is an **investigation
prompt, never a mechanical trigger**: the flag opens a look, it does not fire a
redemption.

## 3. How it works

### 3.1 The mental model, before any math

Picture the manager's monthly return on the vertical axis and the market's monthly
return on the horizontal axis, and imagine scattering one dot per month. A purely
linear book — take some fixed fraction of the market — traces a **straight line**
through the cloud. A book that has *sold* optionality traces a line that **bends
downward at the ends**: it keeps up on small moves but gives back disproportionately
on large moves of either sign. That downward bend is *negative convexity*, and it is
the single geometric fact every diagnostic in this screen is trying to detect from a
different angle.

Four ideas follow from that picture, and each becomes one diagnostic:

1. **Fit the bend directly.** Add a squared-market term to the regression; the
   coefficient on it *is* the curvature. Negative curvature is the bend we are looking
   for. (Treynor–Mazuy, §3.3.)
2. **Compare the two ends.** Measure how much of the market the book takes when the
   market rises versus when it falls. A short-vol book participates *more* on the way
   down than on the way up. (Henriksson–Merton, §3.4.)
3. **Ask a model-free question.** Are the manager's worst months the months when the
   market's *squared* move — its realized variance — is largest? If so the return
   stream is effectively short the market's volatility. (Coskewness, §3.5.)
4. **Look at the fingerprint in the drawdown.** A short-vol book looks calm month to
   month but draws down violently: its worst peak-to-trough loss is deeper than its
   own volatility should be able to produce. (Drawdown-vs-vol, §3.6.)

None of these is a verdict on its own. They are four windows onto the *same* bend, so
when several agree the honest reading is "converging evidence," not a manufactured
joint p-value (§3.8). And one preparatory step matters before any of them run: an
illiquid book that marks slowly manufactures its own smooth-looking vol and positive
autocorrelation, which can *masquerade* as convexity. So the screen first runs a
de-smoothing pass (§6, inherited from the S2 tear-sheet pipeline) and then reads the
diagnostics on the *de-smoothed* series — smoothing and convexity are distinct tells
and the screen must not conflate them.

### 3.2 A worked toy example with small numbers

Take six months of a symmetric market factor and two managers who will turn out to
report the *same* average return:

| Month | Market $f$ | Honest $r=0.5f$ | Short-vol $r=0.5f-3f^2+0.0189$ |
| --- | --- | --- | --- |
| 1 | $+0.10$ | $+0.050$ | $+0.039$ |
| 2 | $-0.10$ | $-0.050$ | $-0.061$ |
| 3 | $+0.05$ | $+0.025$ | $+0.036$ |
| 4 | $-0.05$ | $-0.025$ | $-0.014$ |
| 5 | $+0.08$ | $+0.040$ | $+0.040$ |
| 6 | $-0.08$ | $-0.040$ | $-0.040$ |

Both managers average **exactly zero** over the six months — the $+0.0189$ added to
the short-vol book is a flat *premium* that offsets, on average, the $-3f^2$ it gives
back (the mean of $f^2$ here is $0.0063$, and $3\times0.0063=0.0189$). So a mean- or
Sharpe-based comparison sees two identical books. But look at the down-months (2, 4,
6): the short-vol book's worst month is $-0.061$, deeper than the honest book's
$-0.050$, and every large move is shaded worse. The premium is the calm; the bend is
the bill.

Now fit the two regressions of §3.3–3.4 to the short-vol column:

- **Treynor–Mazuy** regresses $r$ on $f$ and $f^2$. Because the short-vol column was
  *built* as $0.5f - 3f^2 + \text{const}$, the fit recovers a curvature coefficient of
  about $\gamma=-3$: strongly negative, the short-convexity signature.
- **Henriksson–Merton** splits the slope at zero. On the three up-months the book
  takes less of the market than on the three down-months, so the *downside*
  participation exceeds the *upside* participation — the same bend, read as an
  asymmetry between the two ends.

That is the whole idea in miniature: two books that are identical on every average
statistic are cleanly separated the moment you fit the shape instead of the average.
The rest of this section makes each diagnostic precise and honest about its noise.

### 3.3 Treynor–Mazuy quadratic convexity — the primary tell

Regress the (de-smoothed) excess return on the market factor **and its square**:

$$r_{i,t} = \alpha_i + \beta_i\, f^{\text{mkt}}_t + \gamma_i\,\big(f^{\text{mkt}}_t\big)^2 + \varepsilon_{i,t}.$$

where:

- $r_{i,t}$ — manager $i$'s de-smoothed excess return in month $t$ (decimal).
- $f^{\text{mkt}}_t$ — the market factor's return in month $t$ (decimal).
- $\alpha_i$ — the intercept (the book's mean return net of its linear and quadratic
  market exposure).
- $\beta_i$ — the *linear* market sensitivity (ordinary beta).
- $\gamma_i$ — the **curvature** of the payoff in the market factor. This is the
  quantity of interest.
- $\varepsilon_{i,t}$ — the residual, assumed mean-zero; its serial dependence is
  handled by the block bootstrap (§6), not assumed away.

In words: $\gamma_i$ measures how the book's market participation *changes* as the
market move gets bigger. A **persistently negative $\gamma$ is the short-convexity
signature** — the manager gives back on large moves of either sign relative to a
linear book, which is the return profile of a written straddle.

This is Treynor & Mazuy (1966) read *backwards*. Their paper introduced the
quadratic term to test whether mutual-fund managers *time the market* — a genuine
market-timer holds more beta when the market is about to rise, which shows up as
$\gamma>0$. We invert their test: a short-vol book carries $\gamma<0$. The same
one-coefficient regression that once looked for skill now looks for sold optionality.
It is one coefficient fit over the *whole* sample — not a regime split.

Two honest caveats travel with $\gamma$ and are surfaced on the sheet:

1. $(f^{\text{mkt}})^2$ has little spread when the sample is short ($T\le 60$), so the
   standard error of $\gamma$ is large (§6). The chip states the $\gamma$ *interval*,
   never the sign alone.
2. $\gamma$ and $\alpha$ are partly confounded: a concave payoff depresses the mean
   (the $\gamma f^2$ term is on average negative when $\gamma<0$), so a reader who
   trusts $\alpha$ while ignoring $\gamma$ is **double-counting** the premium as skill.

### 3.4 Henriksson–Merton up/down beta asymmetry

Fit the single dual-beta regression over the whole window:

$$r_{i,t} = \alpha_i + \beta^{-}_i\, f^{\text{mkt}}_t + \gamma_i\,\max\!\big(f^{\text{mkt}}_t, 0\big) + \varepsilon_{i,t},$$

where:

- $\beta^{-}_i$ — **downside participation**: the slope that applies in every month
  (the market term is present whether $f$ is positive or negative).
- $\max(f^{\text{mkt}}_t, 0)$ — the market return kept only in up-months, zero
  otherwise; the "hockey-stick" regressor that lets the up-slope differ.
- $\gamma_i$ — the *extra* slope that applies only in up-months, so **upside
  participation** is $\beta^{+}_i = \beta^{-}_i + \gamma_i$.
- other symbols as in §3.3.

In words: $\beta^{-}$ is how much of the market the book takes when the market falls,
$\beta^{+}$ is how much it takes when the market rises. The tell is
$\beta^{-} > \beta^{+}$ (equivalently $\gamma<0$): **more participation on the way
down than on the way up** — a concave, short-vol profile. This is
Henriksson & Merton (1981), whose dual-beta regression was, like Treynor–Mazuy, a
market-timing test; we again read it backwards, as a payoff-shape descriptor.

**This is where the do-not-build caution binds hardest, and it must be stated on the
sheet.** The down-leg is identified only off down-months, and a market with positive
drift leaves roughly $T\cdot P(f<0)\approx 0.4\,T$ of them — about **19 down-months at
$T = 48$**. So $\beta^{-}$ is effectively a ~19-observation estimate and its interval
is honestly wide. The screen handles this by (a) reporting the up/down gap as an
interval that will visibly be wide, and (b) **never** converting the split into a
conditional-alpha table. The interaction term is a *static payoff-shape descriptor*;
it is not, and is never rendered as, "the manager's alpha in down markets." That
conditional-return claim is the banned analytic.

### 3.5 Coskewness with the market factor — Harvey–Siddique (2000)

Standardized coskewness of the manager's return with the market:

$$\widehat{\text{coskew}}_i = \frac{\frac{1}{T}\sum_t (r_{i,t}-\bar r_i)\,(f^{\text{mkt}}_t-\bar f)^2}{\hat\sigma_{r_i}\,\hat\sigma_f^2}.$$

where:

- $\bar r_i,\ \bar f$ — the sample means of the manager and market returns.
- $\hat\sigma_{r_i}$ — the manager's return standard deviation; $\hat\sigma_f^2$ — the
  market's return variance. Dividing by them makes the statistic scale-free.
- $T$ — the number of months.

In words: negative coskewness means the manager's returns are **worst exactly when the
market's squared move — its realized variance — is largest**, i.e. the return stream
is short the market's volatility. It is the model-free cousin of §3.3: where
Treynor–Mazuy fits the curvature *parametrically*, coskewness measures it as a
*co-moment*, so agreement between the two is genuine corroboration rather than one
statistic wearing two costumes. Harvey & Siddique (2000) showed that assets with
negative coskewness earn a premium precisely because investors dislike this property —
which is *why* a short-vol book is being paid, and why the posture is a priced bet
rather than free alpha.

Third co-moments are the noisiest objects on the sheet. The sampling standard error of
plain skewness is $\approx\sqrt{6/T}\approx 0.35$ at $T = 48$, and coskewness inherits
that fragility. So the estimate is compared against a **normal-calibrated band**
(`M2_COSKEW_BAND`, provisional, set from the simulator §6), and only a coskewness
outside that band counts toward the tally.

### 3.6 Drawdown-vs-vol signature

Short-vol books look calm and draw down violently: benign month-to-month volatility,
fat left tail. The signature is the ratio of realized maximum drawdown to volatility,
referenced to what a *no-skill* return stream of the same volatility and length would
produce:

$$Z^{\text{DD}}_i = \frac{\text{MaxDD}_i}{\hat\sigma_i} \Big/ q^{\text{null}}_{\text{DD/vol}}(T),$$

where:

- $\text{MaxDD}_i$ — the manager's realized maximum peak-to-trough drawdown over the
  window.
- $\hat\sigma_i$ — the manager's return volatility.
- $q^{\text{null}}_{\text{DD/vol}}(T)$ — the simulation-calibrated *median*
  drawdown-to-vol ratio for a no-skill (Gaussian or fitted-AR(1)) stream at length
  $T$. Dividing by it removes the mechanical fact that longer or more-volatile tracks
  draw down more, leaving only the *excess* asymmetry.

In words: a signature above the `M2_DDVOL_QUANTILE` (provisional 95th) percentile of
the null flags a drawdown deeper than the manager's own volatility should be able to
produce. This reuses the S2 drawdown-band machinery — it is not a new estimator, it is
that band read for asymmetry.

This diagnostic is **corroborating, not primary.** Two related quantities from the S2
pipeline are surfaced alongside it — the Sharpe-vs-MPPM gap (MPPM is the
manipulation-proof performance measure of Goetzmann–Ingersoll–Spiegel–Welch) and the
GLM smoothing parameter $\theta$. A large Sharpe-vs-MPPM gap *plus* high $\theta$ is
the classic smoothed short-vol tell. But they are *supporting* evidence in the tally,
because a large gap also fires on ordinary return manipulation and high $\theta$ also
fires on honest illiquidity — neither is convexity-specific on its own.

### 3.7 Fung–Hsieh straddle-factor loadings (external-data rung)

Where the Fung–Hsieh primitive trend-following straddle (PTFS) factor series is
available, regress the return on it: a **persistently negative** loading is a direct
short-vol posture (the manager is on the other side of the lookback straddle). Fung &
Hsieh (2001) showed that trend-following hedge-fund returns look like *long* positions
in these lookback-straddle factors; a manager loading *negatively* on them is short
that optionality. This is the most literature-blessed of the diagnostics but the most
data-hungry — it needs the external factor series (§6.5) and the straddle betas are
themselves noisy at $T\le 60$. It is therefore an **optional rung**: present only when
the series is loaded, and gated exactly like the others. On the demo it renders as an
honest *unplayed* power-gate, because the PTFS adapter is not yet built — the demo
never fabricates a factor series it does not have.

### 3.8 The composite — an evidence tally, not a score

The screen does **not** collapse the diagnostics into a single scalar. It renders an
**evidence tally**: each playable diagnostic contributes one of
{short-vol-consistent, inconclusive, convex/benign} based on whether its *interval*
clears its band in the short-vol direction. The composite verdict reads
`SHORT-VOL POSTURE — INVESTIGATE` only when at least `M2_COMPOSITE_K` (provisional 3)
of the playable diagnostics agree in the short-vol direction **and** the power gate
for the current $T$ is open (§6); otherwise the sheet shows the individual intervals
and a `NOISE` chip on the composite — "not resolvable at this track length."

The diagnostics are only *approximately* independent — they all read the same
left-tail geometry — so the tally is presented as **converging evidence, not a
p-value**. This framing is binding: "four windows onto the same shape agree" is honest;
a manufactured joint significance would not be. And crucially, we do **not** need an
independence assumption to justify the threshold `M2_COMPOSITE_K`, because the
false-alarm gate (§6) measures the *composite's* false-alarm rate directly on the
simulator — the correlation between diagnostics is priced *empirically*, not assumed
away. The threshold is calibrated, not derived.

## 4. How to implement

The block below is **self-contained teaching code**: paste it into a fresh file,
`pip install numpy`, and it runs. It re-implements the §3 formulas from scratch — the
two regressions, the coskewness co-moment, the drawdown-vs-vol signature, a small
block bootstrap for the intervals, and the evidence tally — with no dependency on any
production module. The production estimators (§6.4) follow the identical formulas but
import their bootstrap and de-smoothing from the shared tear-sheet pipeline; this
version inlines simplified versions of both so the logic is visible end to end.

```python
"""Returns-based convexity screen — teaching implementation.

Every estimator below is a pure function of a manager return series and a
market-factor series. Each returns a point estimate, a bootstrap interval, and a
short-vol-direction verdict. A tiny evidence tally combines the verdicts into a
composite. Formulas mirror sections 3.3-3.8 of this spec.
"""

from dataclasses import dataclass
import numpy as np


@dataclass
class Diagnostic:
    """One convexity diagnostic: point estimate, bootstrap interval, and a verdict
    of 'short-vol-consistent' | 'inconclusive' | 'convex-benign'."""
    name: str
    point: float
    ci_lo: float
    ci_hi: float
    verdict: str


def _ols(design: np.ndarray, y: np.ndarray) -> np.ndarray:
    """Ordinary least squares coefficients for y ~ design (design includes an
    intercept column). Returns the coefficient vector."""
    coeffs, *_ = np.linalg.lstsq(design, y, rcond=None)
    return coeffs


def treynor_mazuy_gamma(r: np.ndarray, f: np.ndarray) -> float:
    """Curvature coefficient gamma from  r = a + b*f + gamma*f**2 + e  (section 3.3).
    A negative gamma is the short-convexity signature."""
    design = np.column_stack([np.ones_like(f), f, f ** 2])
    _, _, gamma = _ols(design, r)
    return float(gamma)


def henriksson_merton_gap(r: np.ndarray, f: np.ndarray) -> float:
    """Up-minus-down participation gap (beta_plus - beta_minus) from the dual-beta
    fit  r = a + beta_minus*f + gamma*max(f, 0) + e  (section 3.4). The gap equals
    gamma; a negative gap means MORE participation on the way down."""
    up_leg = np.maximum(f, 0.0)
    design = np.column_stack([np.ones_like(f), f, up_leg])
    _, _, gamma = _ols(design, r)
    return float(gamma)  # beta_plus - beta_minus


def market_coskew(r: np.ndarray, f: np.ndarray) -> float:
    """Standardized coskewness of the manager return with the market (section 3.5).
    Negative means the manager is worst when the market's squared move is largest."""
    r_dev = r - r.mean()
    f_dev = f - f.mean()
    numerator = np.mean(r_dev * f_dev ** 2)
    denominator = r.std() * f.var()
    return float(numerator / denominator)


def drawdown_vs_vol(r: np.ndarray, null_median_ratio: float) -> float:
    """Realized max-drawdown-to-vol ratio, divided by the no-skill null median for
    this track length (section 3.6). Above 1 means the book draws down deeper than
    its own volatility should produce. `null_median_ratio` comes from the simulator."""
    equity_curve = np.cumsum(r)                 # additive-return proxy for the path
    running_peak = np.maximum.accumulate(equity_curve)
    max_drawdown = np.max(running_peak - equity_curve)
    realized_ratio = max_drawdown / r.std()
    return float(realized_ratio / null_median_ratio)


def _circular_block_bootstrap(
    r: np.ndarray, f: np.ndarray, statistic, n_boot: int, seed: int
) -> np.ndarray:
    """Resample (r, f) pairs in circular blocks of length ~T**(1/3) to preserve
    serial dependence, recomputing `statistic` on each resample (section 6.2).
    Returns the bootstrap distribution of the statistic."""
    rng = np.random.default_rng(seed)
    T = len(r)
    block_len = max(1, int(round(T ** (1 / 3))))
    n_blocks = int(np.ceil(T / block_len))
    r_ext = np.concatenate([r, r])              # wrap around for circular blocks
    f_ext = np.concatenate([f, f])
    draws = np.empty(n_boot)
    for b in range(n_boot):
        starts = rng.integers(0, T, size=n_blocks)
        idx = np.concatenate([np.arange(s, s + block_len) for s in starts])[:T]
        draws[b] = statistic(r_ext[idx], f_ext[idx])
    return draws


def _verdict(ci_lo: float, ci_hi: float, band_lo: float, band_hi: float) -> str:
    """Map an interval against a normal-calibrated band to a tally token. Short-vol
    lives in the negative direction, so an interval sitting fully below the band's
    lower edge is 'short-vol-consistent'; fully above is 'convex-benign'; an interval
    straddling the band is 'inconclusive'."""
    if ci_hi < band_lo:
        return "short-vol-consistent"
    if ci_lo > band_hi:
        return "convex-benign"
    return "inconclusive"


def run_diagnostic(name, r, f, statistic, band, n_boot=2000, seed=0) -> Diagnostic:
    """Compute one diagnostic end to end: point, bootstrap interval, verdict."""
    point = statistic(r, f)
    draws = _circular_block_bootstrap(r, f, statistic, n_boot, seed)
    ci_lo, ci_hi = np.percentile(draws, [5, 95])   # 90% interval
    verdict = _verdict(ci_lo, ci_hi, band[0], band[1])
    return Diagnostic(name, point, float(ci_lo), float(ci_hi), verdict)


def evidence_tally(diagnostics, k, power_gate_open) -> dict:
    """Composite verdict (section 3.8). Flags 'SHORT-VOL POSTURE - INVESTIGATE' only
    when at least k playable diagnostics are short-vol-consistent AND the power gate
    for this track length is open. This is converging evidence, never a joint
    p-value: k is calibrated on the simulator, not derived from an independence
    assumption."""
    short_vol_count = sum(d.verdict == "short-vol-consistent" for d in diagnostics)
    if power_gate_open and short_vol_count >= k:
        label, chip = "SHORT-VOL POSTURE - INVESTIGATE", "shrink"
    else:
        label, chip = "NOT RESOLVABLE AT THIS TRACK LENGTH", "noise"
    return {
        "short_vol_count": short_vol_count,
        "playable_count": len(diagnostics),
        "k": k,
        "label": label,
        "chip": chip,
    }


if __name__ == "__main__":
    rng = np.random.default_rng(42)
    T = 48
    f = rng.normal(0.005, 0.045, T)                 # market factor, slight drift
    honest = 0.5 * f + rng.normal(0.0, 0.02, T)     # linear book
    short_vol = 0.5 * f - 2.2 * np.maximum(-f, 0.0) # concave: gives back on down moves
    short_vol = short_vol + 0.006 + rng.normal(0.0, 0.02, T)

    # Bands would come from the simulator; illustrative placeholders here.
    tm_band, hm_band, cs_band = (-1.0, 1.0), (-0.3, 0.3), (-0.35, 0.35)

    for label, r in [("honest", honest), ("short_vol", short_vol)]:
        diags = [
            run_diagnostic("treynor_mazuy", r, f, treynor_mazuy_gamma, tm_band),
            run_diagnostic("updown_beta", r, f, henriksson_merton_gap, hm_band),
            run_diagnostic("market_coskew", r, f, market_coskew, cs_band),
        ]
        composite = evidence_tally(diags, k=3, power_gate_open=T >= 48)
        print(label, composite["label"])
        for d in diags:
            print(f"  {d.name:14s} {d.point:+.3f} "
                  f"[{d.ci_lo:+.3f}, {d.ci_hi:+.3f}]  {d.verdict}")
```

Two things to notice, because they are the point of the whole design. First, every
estimator returns an *interval*, not a bare point — a bare point estimate is a design
error here, because these third-moment and interaction statistics are too noisy at
$T\le 60$ to trust as numbers. Second, the tally combines *verdicts*, not *values*: it
never multiplies p-values or assumes the diagnostics are independent. It counts how
many windows agree, and the count-threshold `k` is set empirically (§6.3).

## 5. Reading the demo

The gallery page puts **two fully synthetic managers side by side**: an honest book,
Wrenmoor Partners, and a book carrying a hidden written-put overlay, Gullwing Point
Capital. Over the same 48 months and the same market, **they report the same Sharpe to
two decimals (1.10)** — the exhibit's entire premise. One aside near the top of the
page discloses, in copy that must be read exactly as written, that the overlaid book's
premium is calibrated *in-sample* and set **rich of fair** — above the actuarial cost
of its payouts — so that both books show the same healthy Sharpe: the classic *carry
seduction*. That in-sample calibration is a deliberate look-ahead **for a controlled
demonstration and not a claim about live methodology**; the atlas detection numbers
are measured at **fair premium** (zero in-sample carry), the *conservative* case.

How each visual element maps to the method:

- **The paired Sharpe interval-stats** — one band per manager, with the point marker
  where the reported Sharpe sits. Read them together: the bands overlap almost
  entirely, which is the exhibit's whole point — the linear statistic cannot separate
  the two books.
- **The composite verdict chip** under each manager — Wrenmoor reads `NOT RESOLVABLE
  AT THIS TRACK LENGTH` (a `noise` chip: 0 of 4 playable diagnostics fire); Gullwing
  reads `SHORT-VOL POSTURE — INVESTIGATE` (a `shrink` chip: 3 of 4 fire, at the flag
  threshold $k=3$).
- **The four diagnostic interval-stats** for Gullwing — each a 90% interval with its
  short-vol verdict. Treynor–Mazuy $\gamma$ is strongly negative (point $\approx -6.9$,
  interval entirely below zero), the up/down $\beta$ gap is negative (point
  $\approx -1.05$), and the drawdown-vs-vol signature is elevated — three
  short-vol-consistent windows. Market coskewness is negative (point $\approx -0.55$)
  but its interval still touches its band, so it reads *inconclusive*: an honest
  illustration of how noisy the third co-moment is even when the book really is short
  vol.
- **The up/down-β note** states that the gap is a static payoff-shape descriptor whose
  down-leg rests on ~19 down-months, so its interval is honestly wide — the do-not-
  build honesty stays on the sheet.
- **The unplayed straddle rung** renders as a power-gate, not a fabricated statistic,
  with the reason "requires the external Fung–Hsieh PTFS straddle series; adapter not
  yet built."
- **The stress-month receipts table** lists the months the written put paid out, with
  the market move, both managers' returns, and the put payout — the two books are
  identical until the tail arrives, and the table makes the payback concrete.

What an allocator should conclude: the two books are indistinguishable on Sharpe, but
the shape diagnostics cleanly flag Gullwing as short-vol-consistent and leave Wrenmoor
unflagged — and the honest reading is *investigate Gullwing's tail and pricing*, not
*Gullwing is misbehaving*.

## 6. Honest limits & go-live

### 6.1 Data contract per tier

Conventions inherit S1 §2 / S2 §2 verbatim: monthly net returns as **decimals** on a
pandas `PeriodIndex` freq `M`; the market factor and any straddle-factor series
aligned on the same months; **≥24 months to enter, ≥36 for full standing**; a manager
with more than 2 missing months in the window is excluded and flagged, never
interpolated. **Stage 0 is S2's Getmansky–Lo–Makarov unsmoothing** (S2 §3.1): the
screen runs on the de-smoothed series so that mark-smoothing autocorrelation is not
misread as convexity — the two are distinct tells and the screen must not conflate
them.

| Tier | Inputs the live version needs | What the card produces |
| --- | --- | --- |
| **R** (native) | Monthly net returns; market-factor return series; **Fung–Hsieh PTFS straddle-factor series** for the §3.7 rung (external, public — see §6.5) | The whole screen: Treynor–Mazuy γ, HM up/down beta gap, market coskewness, drawdown-vs-vol signature, each as an interval stat, and the composite evidence tally. |
| **E** | R + reported exposure/optionality summaries (gross gamma/vega, net premium, option notional where disclosed) | **Confirmation panel**: the inferred short-vol posture set beside the *reported* optionality — agreement raises confidence, disagreement is itself a conversation. Measurement beside inference, never overwriting it. |
| **P** | E + position/holdings with instrument detail | **Direct payoff inspection**: the actual written options / convex instruments that the returns-based screen could only infer. At P the screen is corroboration; the book is the truth. |

The screen is *designed* for the R rung — its reason to exist is the returns-only
majority whose optionality is never disclosed. E and P do not sharpen the R
estimators; they **confirm or contradict** them, and that gap is the product at those
tiers.

### 6.2 Rendering rule

Every statistic is an **interval stat**, every verdict a **verdict chip** (robust /
shrink / noise per Sweep C), and a bare point estimate is a design-system lint error.
All intervals use the **studentized circular block bootstrap** (`B = M2_BOOTSTRAP_B`,
default 2,000; block length ≈ $T^{1/3}$) so the reported uncertainty already carries
the serial dependence these third-moment and interaction estimators are especially
fragile to.

### 6.3 Power & validation plan — the load-bearing section

Every M2 diagnostic is a third-moment or interaction estimator — the lowest-power
objects computable from a short return series. The screen earns the right to render
only by proving, on the simulator, that its false-alarm rate is controlled at the
sample sizes we actually have. Cells are contributed to the X1 tier-power atlas
([`x1-tier-power-atlas.md`](x1-tier-power-atlas.md)) as this card's rows.

**Simulator extension — the written-put overlay dial.** The equity manager and the
crude returns-only generator have no short-vol posture today. The card adds a
`WrittenPutOverlay` with three named parameters — `premium_annual` (the carry the
manager collects), `strike_moneyness` (out-of-the-money distance in market-factor σ
units), and `overlay_notional` $\kappa$ — producing a monthly overlay return

$$o_t = \text{premium}_t - \kappa\cdot\max\!\big(\text{strike} - f^{\text{mkt}}_t,\,0\big)$$

added to the manager's stream. The premium is set so that at each $\kappa$ the
overlay's *expected* contribution is ≈ 0 (`M2_OVERLAY_FAIR = True`, provisional): the
point of the dial is a book whose **in-sample Sharpe is unchanged** while the left tail
fattens — exactly what makes the screen's job hard and the demo honest. $\kappa = 0$
recovers the honest manager. (The demo page deliberately sets the premium *rich of
fair* instead, an in-sample look-ahead disclosed on the page; the validation grid uses
the fair, conservative setting.)

**The confound that defines the false-alarm axis.** The dangerous false positive is not
a random honest manager — it is an **honest-but-smooth** one: an illiquid book with
high GLM $\theta$ and genuine positive autocorrelation but *no* sold optionality.
Smoothing and convexity both dent the linear picture, and a lazy screen calls both
short-vol. So the size axis of the grid is honest-but-smooth managers ($\theta$ dialed
up, $\kappa = 0$), and the pass bar is that the screen does **not** flag them. Running
the diagnostics on the de-smoothed series (§6.1) is the first defense; the calibration
proves it works.

**Atlas grid (M2 rows).** $\kappa \in \{0,\ \text{low},\ \text{med},\ \text{high}\}$
× $T \in \{36, 48, 60, 120\}$ × smoothing $\theta_1 \in \{0,\ \text{mild},\ \text{heavy}\}$
× strategy family {equity L/S, crude credit}, ≥1,000 seeded paths per
cell (per-module RNG streams, X1 §3.3 convention). Estimands per cell: **detection** =
P(composite flags | $\kappa>0$); **size** = P(composite flags | $\kappa=0$), reported
*separately* for honest-smooth vs honest-liquid; and per-diagnostic power curves so the
tally's weakest member is visible.

**Gates.**

1. **Size / false-alarm (the card's kill criterion).** Composite false-alarm on honest
   managers — **including honest-but-smooth** — must sit at or below
   `M2_FALSE_ALARM_MAX` (provisional 0.10) at $T = 48$. The card's stated kill line is
   **1-in-5**: if calibrated false-alarm exceeds 0.20 at $T = 48$, the screen is noise
   theater and is **killed or its minimum window lengthened**, recorded in writing per
   converge-or-cut — not shipped quietly.
2. **PowerGate (what renders).** The composite verdict renders only at $T \ge$
   `M2_MIN_T_FLAG` (provisional 48), the smallest window where gate 1 holds in the
   atlas. Below it the sheet shows the individual interval stats with a `NOISE`
   composite chip — the refusal is the honest product.
3. **Interval coverage.** Bootstrap-CI coverage for each diagnostic within ±5 pp of
   nominal on simulated managers (as S2 §4); a diagnostic that cannot be honestly
   interval-reported is dropped from the tally, not shipped with a fake interval.
4. **Recovery.** At `high` $\kappa$ the screen's detection power is reported as a curve
   in $T$; the honest headline is likely "reliable only at $T \ge$ some number, and
   never for a mild overlay at 36 months" — a first-class finding, not a failure to
   bury.

**Regime-split caution, restated as a validation constraint.** No M2 cell estimates a
regime-conditional alpha, and none is added to the atlas. The up/down and quadratic
terms are validated as **shape-coefficient recovery** (does the screen recover the
injected $\kappa$?), never as conditional-return accuracy. This keeps M2 clear of the
do-not-build list while measuring the one thing that list does not forbid: the static
geometry of the payoff.

### 6.4 How it lands in the codebase

Module home: **`src/quant_allocator/flagships/convexity/`**

- `diagnostics.py` — the five §3 estimators as pure functions over a return series and
  a factor frame, each returning a point + bootstrap interval + band-clearance flag; no
  rendering, no I/O. The bootstrap and the de-smoothing pre-stage are **imported from
  the S2 tear-sheet pipeline**, not re-implemented.
- `screen.py` — the §3.8 composite: assembles the tally, consults the PowerGate
  registry (X1) for `M2_MIN_T_FLAG`, emits the composite verdict chip.
- `render.py` — pack the JSON payloads; the demo generator imports `diagnostics.py` and
  `screen.py`, so **demo numbers and live numbers come from the same code path** — only
  the input data differs.
- `simulator/overlays.py` (**new**) — the `WrittenPutOverlay` dial, added as a
  composable overlay so both the equity manager and the returns-only generator can wear
  it; unit-tested that it recovers a known $\kappa$ and that premium fairness holds in
  expectation.

**Dependencies:** `numpy` + `scipy` (already S2's; bootstrap, OLS, optimizer). The FH
PTFS straddle-series adapter is a named prerequisite for the §3.7 rung only (the R core
runs without it). No Bayesian inference — M2 is estimator composition. CI never
computes numbers; it renders committed demo JSON. **Effort: M** — diagnostics ~1
session, simulator overlay dial + tests ~1, validation/atlas grid ~1, pack + demo page
~1. **Sequencing:** the overlay dial lands first (it is the fake-data source for both
the demo and the validation), then the screen, then it hosts inside the S2 tear sheet
as a panel — it does not ship as a standalone dashboard (a separate tab would be the
25%-adoption failure mode); delivered as one section of the always-on sheet, it is read
every month in context.

### 6.5 Go-live requirements

- **Data ask:** monthly net returns (R) + a market-factor return series — the core
  screen runs on these. The §3.7 straddle rung additionally needs the **Fung–Hsieh
  PTFS factor series** (public — David Hsieh's data library; a small adapter, not yet
  built). Tier E adds reported optionality/gross-gamma summaries; tier P adds
  instrument-level holdings.
- **Sample required:** the gate is **calibrated false-alarm, not a raw count**. The
  composite renders only at $T \ge$ `M2_MIN_T_FLAG` (provisional 48 months, pinned by
  the atlas), where honest-manager false-alarm — including honest-but-smooth — sits ≤
  `M2_FALSE_ALARM_MAX` (provisional 0.10). Below that window the individual interval
  stats render with a `NOISE` composite chip.
- **Build effort:** **M**, including the `WrittenPutOverlay` simulator dial and reuse
  of S2's de-smoothing + bootstrap.
- **Kill criterion:** calibrated false-alarm > **0.20 at T = 48** on honest managers ⇒
  the screen is killed or its minimum window lengthened, recorded in writing.

**Who sees what, when:** internal team gets the full tally at monitoring cadence; any
manager-facing version ships only inside the E1 ladder relationship, framed as "help us
understand your tail," and uses the E/P confirmation panel so the conversation is about
the book, not about an inference. The screen is a **panel on the S2 tear sheet**, not a
separate short-vol dashboard, and the composite flag opens an investigation — pull the
E/P confirmation panel, ask the manager about optionality — it is **never** a mechanical
redemption rule.

## 7. Deeper reading

### 7.1 Canonical papers (read in this order)

1. **Agarwal & Naik (2004, *RFS*), "Risks and Portfolio Decisions Involving Hedge
   Funds."** The foundational result that many hedge-fund payoffs resemble a **short
   put on the market** — their returns have option-like, non-linear exposure that a
   linear model misses. This is the reason the screen exists: if the payoffs are
   option-like, you have to fit the shape, not the average.
2. **Fung & Hsieh (2001, *RFS*), "The Risk in Hedge Fund Strategies: Theory and
   Evidence from Trend Followers."** Introduced the PTFS lookback-straddle factors and
   showed trend-following returns load *positively* on them. A manager loading
   *negatively* is short that optionality — the §3.7 rung's direct read.
3. **Treynor & Mazuy (1966, *HBR*) and Henriksson & Merton (1981, *JB*).** The
   quadratic and dual-beta market-*timing* regressions. Their timers wanted positive
   curvature and higher up-beta; we read the same regressions backwards, where negative
   curvature and higher *down*-beta are the short-vol signature (§3.3–3.4).
4. **Harvey & Siddique (2000, *JF*), "Conditional Skewness in Asset Pricing Tests."**
   The coskewness estimator, and the result that negative coskewness is *priced* —
   investors demand a premium to hold it. That is precisely why a short-vol book gets
   paid, and why the posture is a bet to size rather than free alpha (§3.5).
5. **Mitchell & Pulvino (2001, *JF*), "Characteristics of Risk and Return in Risk
   Arbitrage."** A worked case where a smooth return stream *is* a written put — the
   canonical intuition for the whole screen. Pair with Goetzmann–Ingersoll–Spiegel–
   Welch (the MPPM, via S2 §3.4) for the manipulation-proof gap used as corroboration.

### 7.2 Questions you should be able to answer after reading this page

- **Why can a Sharpe of 1.1 be a *warning*?** Because the calm months can be the
  premium on sold insurance, not earned skill. The screen looks for the payoff *shape*
  that says a tail is being sold. State the four diagnostics and that they are four
  windows onto one geometry, not four independent votes.
- **What does M2 deliberately *not* do, and why?** No regime-split alpha, no
  time-varying beta, no conditional-return claim — only a static payoff-shape
  coefficient with an interval. The *why* is the down-beta arithmetic: with market
  drift $P(f<0)\approx 0.4$, so the Henriksson–Merton down-leg rests on only ~19
  down-months at $T=48$ and $\text{SE}(\beta^{-})\propto 1/\sqrt{0.4\,T}$; splitting the
  sample *further* to read a conditional average is statistically hopeless. The
  do-not-build list is an arithmetic conclusion, not a taste.
- **What is the honest-but-smooth confound, and what controls it?** An illiquid book
  that marks slowly manufactures positive autocorrelation and benign vol that can look
  like convexity. De-smoothing the series *first* (§6.1) is the load-bearing
  false-alarm control; the whole size gate in §6.3 rests on it. Quote the kill line —
  1-in-5 at $T=48$ — that decides whether the screen is signal or theater.
- **Why is the composite "converging evidence, not a p-value"?** The diagnostics all
  read the same left-tail geometry, so they are not independent; a joint significance
  would be manufactured. The flag threshold $k=3$ is calibrated on the simulator (the
  composite's own false-alarm rate is measured directly), so no independence assumption
  is needed.

### 7.3 Derivations to own (work each by hand once)

1. **Treynor–Mazuy $\gamma$ as convexity, and its confound with $\alpha$.** Write the
   payoff as a quadratic in $f$; show that a written-straddle payoff
   ($-\kappa\max(K-f,0)$ near the money) has $\gamma<0$ to second order, and that
   $\mathbb{E}[\gamma f^2]<0$ pulls the fitted intercept — so a book with negative
   $\gamma$ *manufactures* apparent $\alpha$. Own why reading $\alpha$ without $\gamma$
   double-counts.
2. **Why the down-beta is a ~19-observation estimate at T = 48.** With market drift,
   $P(f<0)\approx 0.4$; the Henriksson–Merton down-leg is identified off those months
   only, so $\text{SE}(\beta^{-})\propto 1/\sqrt{0.4\,T}$.
3. **Third-moment sampling error.** Sample skewness has SE $\approx\sqrt{6/T}$ under
   normality; at $T = 48$ that is 0.35. Coskewness inherits this fragility. This single
   number is why the screen is gated and composited rather than trusted point-by-point.
4. **Smoothing ≠ convexity.** GLM smoothing manufactures positive autocorrelation and a
   benign-looking vol; short-vol posture manufactures negative convexity and a fat left
   tail. Both dent the linear picture, but only the second is optionality — which is why
   de-smoothing first is what keeps an honest illiquid book from being called short-vol.

**Provisional constants (numerics gate).** `M2_BOOTSTRAP_B` (2,000), `M2_COSKEW_BAND`,
`M2_DDVOL_QUANTILE` (95th), `M2_COMPOSITE_K` (3), `M2_MIN_T_FLAG` (48),
`M2_FALSE_ALARM_MAX` (0.10), kill line (0.20 @ T=48), `M2_OVERLAY_FAIR` (True) and the
`WrittenPutOverlay` parameter ranges — all pinned by the atlas, none hard-coded
silently.

---

## Method review (2026-07-07) — APPROVED, implementation-ready

- **`M2_COMPOSITE_K`=3 CONFIRMED as provisional** — no independence assumption is
  needed because gate 1 measures the COMPOSITE's false-alarm rate directly on the
  simulator (correlation between diagnostics is priced empirically). The "converging
  evidence, not a p-value" framing is binding page copy.
- **HM treatment CONFIRMED:** the dual-beta fit is a static payoff-shape descriptor;
  rendering it as a conditional-alpha table is prohibited (do-not-build). The ~19-obs
  down-leg honesty stays on the sheet.
- **Sixth discriminant diagnostic RULED YAGNI:** de-smooth-first + the honest-but-smooth
  size axis is the design; a smoothing-vs-convexity discriminant is added ONLY if gate 1
  fails on honest-smooth managers — recorded as a conditional extension, not built now.
- Overlay-dial fairness (`M2_OVERLAY_FAIR`), bands, K, and the 0.10/0.20 false-alarm
  lines remain numerics-gate docket items.
</content>
