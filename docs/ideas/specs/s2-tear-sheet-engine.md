# S2 · Uncertainty-Honest Tear-Sheet Engine — Method Spec

**Date:** 2026-07-06
**Status:** Reviewed (2026-07-06) — implementation-ready
**Card:** [`docs/ideas/2026-07-05-idea-cards.md`](../2026-07-05-idea-cards.md) § S2
**Demo:** gallery page `s2.html` (single-manager print pack; fully synthetic factors, §5)

---

## 1. What this is

This is a **per-manager tear sheet** — the one-page performance summary an
allocator reads to decide whether to keep, add to, engage, or redeem a manager.
The difference from a normal tear sheet is a single discipline: **nothing on the
page is a bare number.** A conventional sheet prints "Sharpe 1.4, alpha +3%/yr"
as if those were facts. This engine prints "Sharpe 0.71, and with four years of
monthly data that is anywhere from about 0 to 1.7" — the estimate *and* the
honest width of what the track record can actually support. Every statistic
ships as an **interval** (a point plus a range), and every judgement ships as a
calibrated **chip** (a short verdict such as *robust*, *shrink toward the
benchmark*, or *too noisy to call*).

It is meant to be the **always-on layer**: run on every manager, every month.
The decision moments it serves are *monitor* (is this manager still behaving as
underwritten?), *select* (screen candidates by stated uncertainty rather than by
a point ranking that pretends to a precision it does not have), *engage* (hand
the manager their own honest sheet — a reciprocity gesture — and let a flagged
factor-exposure chip open a conversation about fees), and *redeem* (decide
whether a drawdown is ordinary or genuinely alarming under the story you are
paying for). The engine invents no new statistics. Its whole value is that it
**composes established, peer-reviewed estimators in the right order and attaches
an honest error bar to each one**, so an allocator is never misled by false
precision.

## 2. Why we use it

The decision problem is that manager performance is measured on **short, dirty
samples**, and the naive tear sheet hides both problems.

**Short.** Hedge-fund track records that reach the underwriting table are
typically 36 to 60 monthly observations — three to five years. That is far too
little data to pin down a Sharpe ratio. Estimation error alone means a reported
Sharpe of 1.0 at four years has a 95% confidence interval of roughly $[0, 2]$:
the same track record is statistically consistent with *no skill* and with
*world-class skill*. A point Sharpe printed without that interval is not a
summary, it is an overclaim. Ranking managers by point Sharpe — the default
screen — is therefore ranking mostly on noise.

**Dirty.** Illiquid books (credit, private-ish strategies, anything marked to
model) report **smoothed** returns: this month's reported number is partly a
carryover of last month's true move, because stale marks bleed across reporting
periods. Smoothing has a specific, damaging effect on the statistics. It
*understates volatility* (the denominator of the Sharpe), which *flatters the
Sharpe*; it *biases factor betas toward zero*, making a manager look more
market-neutral than they are; and it *manufactures positive autocorrelation*,
which breaks the standard annualization arithmetic and inflates the headline
number a second time. So the two failure modes compound: the reported Sharpe is
biased *upward* by smoothing and reported *without* the wide error bar that the
short sample demands.

Naive alternatives fail in ways worth naming. **A point Sharpe with a
$\times\sqrt{12}$ annualization** assumes returns are serially independent —
exactly the assumption smoothing violates — so it double-counts the inflation.
**A single "significance star"** collapses a rich uncertainty into a
true/false claim and still says nothing about *how* uncertain. **Comparing raw
Sharpes across managers** compares numbers computed on differently-smoothed,
differently-lengthed samples as if they were on the same footing. What this
engine wins is the ability to say, out loud and by construction, *how much a
track record actually resolves* — which turns a noisy point ranking into a
defensible, uncertainty-aware read, and turns an accusatory "your Sharpe is
fake" into a calibrated "at this track length the data cannot yet separate your
skill from factor exposure."

## 3. How it works

### 3.1 The mental model, in prose

Picture the pipeline as **six stations a return series passes through**, in a
fixed order, each one adding an honest number to the sheet:

1. **Unsmooth.** Undo the mark-smoothing so the volatility (and therefore the
   Sharpe) is computed on the manager's *economic* returns, not their
   accounting-smoothed ones.
2. **Regress.** Explain the returns with a factor model to separate *alpha*
   (skill) from *beta* (paid-for exposure you could buy cheaply).
3. **Interval machinery.** Attach a confidence interval to the Sharpe and to
   the alpha — the core honesty step.
4. **MPPM.** Compute a *manipulation-proof* performance number and place it
   beside the Sharpe; a gap between them is a tell that the payoff has been
   reshaped.
5. **Alt-beta gate.** If the alpha interval includes zero, raise a calibrated
   chip that says so — a prompt for a fees-for-beta conversation, not a verdict
   of "no skill."
6. **Drawdown band.** Plot the realized drawdown against a simulated envelope
   of what drawdowns *should* look like if the manager's claimed skill is real,
   so you can see whether a loss is ordinary or extreme.

The order matters: unsmoothing runs first because every downstream number
(vol, Sharpe, its interval, the drawdown simulation) should be computed on the
economic returns, not the smoothed ones.

### 3.2 A worked toy example

Take a tiny illiquid book whose *true* monthly returns average 1% with a true
month-to-month standard deviation of $\sigma_r = 1.00\%$, and — matching the
assumption the unsmoothing model rests on (§3.3.1) — no serial correlation:
each true month is an independent draw. The manager reports it smoothed, so
each reported month is 70% this month's true return and 30% last month's:

$$r^{\text{obs}}_t = 0.7\,r_t + 0.3\,r_{t-1}.$$

Run the smoothing *forward* first. The mean is conserved
($0.7 \times 1\% + 0.3 \times 1\% = 1\%$), but for uncorrelated true returns the
variances of the two independent pieces add:

$$\sigma^2_{\text{obs}} = (0.7^2 + 0.3^2)\,\sigma^2_r = 0.58\,\sigma^2_r,
\qquad\text{so}\qquad
\sigma_{\text{obs}} = \sqrt{0.58} \times 1.00\% \approx 0.76\%.$$

The reported volatility is only 76% of the truth. A tear sheet that computes
Sharpe on the reported series divides the same excess mean by a denominator
that is too small by the factor $1/\sqrt{0.58} \approx 1.31$ — a Sharpe
inflated by roughly 31%, out of thin air.

Unsmoothing simply inverts that step: the true standard deviation is
$\sigma_{\text{obs}} / \sqrt{0.58} = 0.76\% / 0.7616 = 1.00\%$ — the honest
denominator, recovered exactly, and the inflated Sharpe cut back down. (In a
real sample the reconciliation is exact only in expectation: a finite draw of
"uncorrelated" returns has some accidental sample autocorrelation, so recovered
numbers wobble around the truth.) That single correction is station 1.
Everything else on the sheet then runs on the recovered economic series.

### 3.3 The math

Notation is defined at first use. Throughout, returns are **monthly net
returns as decimals** (0.01 = 1%), $T$ is the number of monthly observations,
and annualization uses $\times 12$ for means/alphas and $\times\sqrt{12}$ for
volatilities (the caveat on $\sqrt{12}$ is the whole point of §3.3.3).

#### 3.3.1 Unsmoothing — Getmansky–Lo–Makarov (2004)

Model the observed return as a moving average of the true (economic) returns:

$$r^{\text{obs}}_t = \theta_0 r_t + \theta_1 r_{t-1} + \theta_2 r_{t-2},
\qquad \sum_{k=0}^{2}\theta_k = 1,\quad \theta_k \ge 0.$$

where:
- $r^{\text{obs}}_t$ — the **reported** return in month $t$ (what the manager
  sends you).
- $r_t$ — the **true economic** return in month $t$ (unobserved; what actually
  happened to the portfolio's value).
- $\theta_0, \theta_1, \theta_2$ — **smoothing weights**: how much of each of
  the current and two prior true months bleeds into this reported month.

The two constraints ($\theta_k$ non-negative and summing to one) make the kernel
a *convex average*: it redistributes return across adjacent months without
changing the long-run mean. **Assumption:** the true returns $r_t$ are serially
uncorrelated (all the autocorrelation you see in reported returns is an artefact
of smoothing, not real economic dynamics) — this is what lets the model treat
the observed series as a moving average of white-ish innovations.

The weights are estimated by **maximum likelihood** — fit an MA(2) process to
the observed returns and normalize its coefficients to sum to one. The fitted
$\theta_k$ are themselves a **first-class illiquidity diagnostic**: large
$\theta_1, \theta_2$ mean a lot of return is bleeding across months, i.e. marks
are stale and the book is illiquid. They are printed on the sheet, not hidden as
an intermediate.

The mean is conserved but the **variance is not**. Because the $\theta_k$ are a
convex average, $\sum_k \theta_k^2 \le \left(\sum_k \theta_k\right)^2 = 1$, and
for uncorrelated true returns:

$$\sigma^2_{\text{obs}} = \Big(\textstyle\sum_k \theta_k^2\Big)\,\sigma^2_r,
\qquad\text{so}\qquad
\sigma_r = \frac{\sigma_{\text{obs}}}{\sqrt{\sum_k \theta_k^2}} \ge
\sigma_{\text{obs}}.$$

where $\sigma_{\text{obs}}$ is the standard deviation of the reported series and
$\sigma_r$ that of the economic series. In words: **the true volatility is
larger than the reported volatility**, by the factor $1/\sqrt{\sum_k\theta_k^2}$,
so the de-smoothed Sharpe is **lower** than the reported one. The engine
reconstructs the economic series by inverting the moving-average filter and
recomputes vol and Sharpe from it.

**What Getmansky, Lo and Makarov showed** (JFE 2004): hedge-fund reported
returns exhibit autocorrelation far beyond what any tradeable strategy could
sustain, and this is best explained not by predictability but by *smoothed
marks* on illiquid holdings; they formalize the moving-average model above,
show the weights recover an illiquidity ordering that matches asset class, and
show that de-smoothing materially raises measured volatility and lowers measured
Sharpe. That is exactly the correction we need before any Sharpe is quoted.

**When it is skipped:** if the fitted $\theta_0 \ge 0.95$ there is no material
smoothing, so de-smoothing would only inject estimator noise; the sheet skips it
and prints a note saying so.

#### 3.3.2 Factor regression

Ordinary least squares of the (de-smoothed, where applicable) *excess* return on
the strategy-appropriate factor set:

$$r_t - r_{f,t} = \alpha + \sum_j \beta_j\,f_{j,t} + \varepsilon_t.$$

where:
- $r_{f,t}$ — the **risk-free** return in month $t$; $r_t - r_{f,t}$ is the
  excess return.
- $\alpha$ — the **intercept**, the average monthly return *not* explained by
  the factors; annualized $\times 12$, this is the manager's estimated skill.
- $f_{j,t}$ — the return of **factor** $j$ in month $t$ (e.g. the market, size,
  value, momentum factors).
- $\beta_j$ — the manager's **loading** (exposure) on factor $j$.
- $\varepsilon_t$ — the residual, the part of the return no factor explains.

Factor sets by strategy: **FF5+MOM** (the five Fama–French factors plus
momentum) for equity long/short; the **Fung–Hsieh 7** for macro/trend; a credit
set for credit — always computed **on the unsmoothed returns**, because
smoothing biases the $\beta_j$ toward zero. The outputs are the point $\alpha$
(annualized) and the $\beta_j$, which feed the interval machinery, the alt-beta
gate, and the tier-E exposure panel.

**What Fung and Hsieh showed** (FAJ 2004): trend-following and macro hedge-fund
returns are well described by a small set of *option-like* factors (lookback
straddles on bonds, currencies, commodities, plus equity and rate factors); the
often-quoted ~80% $R^2$ applies to *diversified* fund-of-funds portfolios, not
to single managers — a caveat we carry so we never overclaim the fit on one
book.

#### 3.3.3 Interval machinery

Three interval sources, reported together so the reader sees when they agree and
when they diverge.

**Sharpe standard error — Lo (2002).** For the per-period (monthly) Sharpe
ratio $\widehat{SR} = \hat\mu / \hat\sigma$ (estimated mean excess return over
estimated standard deviation), the closed-form asymptotic standard error is:

$$SE(\widehat{SR}) \approx \sqrt{\frac{1 + \tfrac{1}{2}\widehat{SR}^{\,2}}{T}}.$$

where the $\tfrac{1}{2}\widehat{SR}^{\,2}$ term is the extra uncertainty from
having to *estimate the denominator* $\hat\sigma$ rather than knowing it. This
is the cheap, always-available interval. It is computed on the monthly Sharpe
and annualized **explicitly**: under serial independence both the point and the
SE scale by $\sqrt{12}$; under positive serial correlation the correct scaling
factor is *smaller* than $\sqrt{12}$ (the "$\sqrt{12}$ trap" below), which is
precisely why unsmoothing runs first.

**What Lo showed** (FAJ 2002): the Sharpe ratio is a statistic with sampling
error like any other; he derives its standard error (the formula above for the
iid case, and a serial-correlation-corrected version), and shows that annualizing
a monthly Sharpe by $\sqrt{12}$ is only valid under independence — with the
positive autocorrelation typical of hedge funds, the naive $\sqrt{12}$
**overstates** the annual Sharpe. Both results are load-bearing here: the error
bar and the annualization caveat.

**Production Sharpe CI — Ledoit–Wolf (2008).** A **studentized circular block
bootstrap**, $B = 2{,}000$ resamples, block length $\approx T^{1/3}$ (≈4 at
$T=48$). where:
- a **block** is a consecutive run of months resampled together, so the
  autocorrelation *within* the block is preserved (iid resampling would destroy
  the very serial dependence that matters).
- **circular** means the series is wrapped end-to-start before blocking, so
  every observation has equal chance of appearing — no edge months are
  under-weighted.
- **studentized** means we bootstrap the *t-statistic* $(\widehat{SR}^* -
  \widehat{SR})/SE^*$ rather than the raw Sharpe, which buys second-order
  accuracy under fat tails.

This is the CI the sheet shows once it clears coverage validation (§6). **What
Ledoit and Wolf showed** (JEF 2008): they build a robust confidence interval and
test for the *difference* of two Sharpe ratios that is valid under the fat tails
and serial correlation real return series exhibit, using exactly this
studentized time-series bootstrap — giving honest coverage where the closed-form
SE, derived under cleaner assumptions, can be too tight.

**Alpha CI — HAC (Newey–West).** The alpha's standard error uses a
**heteroskedasticity- and autocorrelation-consistent** (HAC) estimator —
Newey–West with lag $\approx T^{1/4}$ (≈3 at $T=48$) — which inflates the naive
OLS standard error to account for residual serial correlation and changing
variance. A block bootstrap runs as a cross-check; on material disagreement the
sheet widens to the *looser* of the two and flags it. A HAC standard error is
the standard defensive choice whenever regression residuals are not clean iid
noise, which return-series residuals never are.

#### 3.3.4 MPPM — Goetzmann–Ingersoll–Spiegel–Welch

The **manipulation-proof performance measure** with risk-aversion parameter
$\rho = 3$:

$$\widehat{\Theta}_\rho = \frac{1}{(1-\rho)\,\Delta t}\,
\ln\!\left(\frac{1}{T}\sum_{t=1}^{T}
\Big(\frac{1+r_t}{1+r_{f,t}}\Big)^{1-\rho}\right),
\qquad \Delta t = \tfrac{1}{12}.$$

where:
- $\rho$ — the **risk-aversion** of a hypothetical power-utility investor; $3$
  is the paper's conventional choice.
- $\Delta t = \tfrac{1}{12}$ — the length of one period in years, which
  annualizes the measure.
- the ratio $(1+r_t)/(1+r_{f,t})$ is the manager's **gross return relative to
  cash** in month $t$.

In words, $\widehat{\Theta}_\rho$ is the **annualized certainty-equivalent
excess return** of a CRRA (constant relative risk aversion — power-utility)
investor holding the manager: the guaranteed return
that would make that investor exactly as happy as the manager's risky record.
It is reported **beside** the Sharpe. A large **Sharpe-vs-MPPM gap** flags
manipulation or hidden optionality: the two agree for well-behaved
distributions and diverge when the payoff has been reshaped (tails sold,
marks smoothed). The gap feeds card M2 later; here it is a printed flag, not a
verdict.

**What Goetzmann, Ingersoll, Spiegel and Welch showed** ("Sharpening Sharpe
Ratios"): they prove that any performance measure that cannot be gamed by an
uninformed manager must take essentially this power-utility form; because
$\widehat{\Theta}_\rho$ is a monotone function of expected power utility over the
*realized* return distribution, no repackaging of the payoff (leverage, writing
options, smoothing marks, return timing) that a rational $\rho$-investor would
not genuinely prefer can raise it. The Sharpe ratio, by contrast, *is* gameable —
selling tail options lifts the mean while barely moving reported volatility — so
the gap between them is a manipulation tell.

#### 3.3.5 Alt-beta gate

If the factor **alpha's 90% CI contains zero**, the sheet renders the chip
**"provisionally alternative beta"** and *states the interval*, never just the
label — e.g. "alpha 90% CI $[-1.2\%, +3.1\%]$/yr — not distinguishable from
factor beta at this track length." It is a **calibration statement about track
length**, not a claim the manager has no skill: with more data the interval
would tighten and might well clear zero. It is the opener for the fees-for-beta
conversation — if what you are paying alpha fees for is not yet distinguishable
from exposure you could buy cheaply, that is worth discussing, without accusing
anyone.

#### 3.3.6 Drawdown band

The realized drawdown path (the running peak-to-trough decline) is plotted
against a **simulation-calibrated band**. A Monte Carlo of the *maintained
hypothesis* — the claimed or S1-posterior Sharpe (the Sharpe estimate from card
S1's Bayesian skill ledger, when that companion analytic is available), the
de-smoothed volatility
from station 1, and a fitted **AR(1)** autocorrelation (one-lag persistence) —
generates the null distribution of drawdown paths, and the band is the
**50 / 95 / 99th percentile envelope** at each horizon. If the manager's
skill is real, the realized path should sit inside the band; a path that punches
through the 99th-percentile envelope is a drawdown that is *extreme* under the
story you are paying for. This is **M3-lite** — a lightweight preview of card
M3, the dedicated drawdown-alarm module: it shows whether a loss is
ordinary or alarming, but the full alarm logic (hysteresis, time-to-detection,
roster heat-list) is card M3, which slots into this same panel when built.

## 4. How to implement

The following is **self-contained teaching code** — paste it into a fresh file,
`pip install numpy scipy`, and it runs. It implements the same formulas as §3:
the unsmoothing filter, Lo's Sharpe SE, the studentized block-bootstrap CI, the
Newey–West alpha SE, and the MPPM. It is deliberately written from scratch (no
project imports) so the mechanics are visible; the production pipeline factors
the same math into pure stage functions (§6).

```python
"""Uncertainty-honest tear-sheet core: unsmoothing + Sharpe intervals.

All returns are monthly decimals (0.01 == 1%). T is the sample length.
Annualization: means/alphas x12, volatilities and Sharpe x sqrt(12).
"""
from __future__ import annotations

import numpy as np
from scipy.optimize import minimize

MONTHS_PER_YEAR = 12
ANNUAL_VOL = np.sqrt(MONTHS_PER_YEAR)


# --- Stage 1: Getmansky-Lo-Makarov unsmoothing (MA(2)) --------------------

def unsmooth(returns: np.ndarray) -> dict:
    """Recover the economic return series from smoothed reported returns.

    Model: r_obs_t = theta0*r_t + theta1*r_{t-1} + theta2*r_{t-2}, with the
    thetas non-negative and summing to 1. We fit an MA(2) to the de-meaned
    reported returns by conditional maximum likelihood (minimize the sum of
    squared innovations), then normalize the MA coefficients so they sum to 1.
    """
    x = returns - returns.mean()          # de-mean; the kernel conserves mean
    T = x.size

    def conditional_ssr(b: np.ndarray) -> float:
        # MA(2) in invertible form x_t = e_t + b1 e_{t-1} + b2 e_{t-2};
        # recover innovations e_t recursively and return their sum of squares.
        b1, b2 = b
        e = np.zeros(T)
        for t in range(T):
            prev1 = e[t - 1] if t >= 1 else 0.0
            prev2 = e[t - 2] if t >= 2 else 0.0
            e[t] = x[t] - b1 * prev1 - b2 * prev2
        return float(e @ e)

    # Fit b1, b2 by conditional MLE (Gaussian => least squares on innovations).
    fit = minimize(conditional_ssr, x0=np.array([0.2, 0.0]), method="Nelder-Mead")
    b1, b2 = fit.x
    raw = np.array([1.0, max(b1, 0.0), max(b2, 0.0)])  # enforce theta_k >= 0
    theta = raw / raw.sum()                            # enforce sum(theta) = 1

    # Variance is NOT conserved: sigma_obs^2 = sum(theta^2) * sigma_true^2.
    vol_ratio = np.sqrt(np.sum(theta ** 2))            # sigma_obs / sigma_true
    desmoothed_vol = returns.std(ddof=1) / vol_ratio

    # Reconstruct the economic series by inverting the MA filter with theta.
    u = np.zeros(T)
    for t in range(T):
        prev1 = u[t - 1] if t >= 1 else 0.0
        prev2 = u[t - 2] if t >= 2 else 0.0
        u[t] = (x[t] - theta[1] * prev1 - theta[2] * prev2) / theta[0]
    desmoothed_series = returns.mean() + u

    applied = theta[0] < 0.95   # skip de-smoothing when there is no real smoothing
    return {
        "theta": theta,
        "vol_ratio": vol_ratio,
        "desmoothed_vol": desmoothed_vol,
        "desmoothed_series": desmoothed_series,
        "applied": applied,
    }


# --- Stage 3a: Sharpe point + Lo (2002) standard error --------------------

def sharpe_and_lo_se(excess: np.ndarray) -> tuple[float, float]:
    """Annualized Sharpe and Lo's closed-form standard error.

    Monthly SR = mean/std; Lo SE = sqrt((1 + SR^2/2) / T). Under the iid
    assumption both scale to annual by sqrt(12).
    """
    T = excess.size
    sr_monthly = excess.mean() / excess.std(ddof=1)
    se_monthly = np.sqrt((1.0 + 0.5 * sr_monthly ** 2) / T)
    return sr_monthly * ANNUAL_VOL, se_monthly * ANNUAL_VOL


# --- Stage 3b: Ledoit-Wolf studentized circular block bootstrap CI --------

def sharpe_block_bootstrap_ci(
    excess: np.ndarray,
    level: float = 0.95,
    n_boot: int = 2000,
    seed: int = 0,
) -> tuple[float, float]:
    """Studentized circular block-bootstrap CI for the annualized Sharpe.

    Blocks (length ~ T^(1/3)) preserve within-block autocorrelation; the
    circular wrap gives every observation equal resampling weight; studentizing
    the t-statistic (SR* - SR)/SE* buys accuracy under fat tails.
    """
    rng = np.random.default_rng(seed)
    T = excess.size
    block = max(1, round(T ** (1 / 3)))
    n_blocks = int(np.ceil(T / block))
    wrapped = np.concatenate([excess, excess[:block]])  # circular wrap

    sr_hat, se_hat = sharpe_and_lo_se(excess)

    t_stats = np.empty(n_boot)
    for i in range(n_boot):
        starts = rng.integers(0, T, size=n_blocks)
        sample = np.concatenate([wrapped[s:s + block] for s in starts])[:T]
        sr_b, se_b = sharpe_and_lo_se(sample)
        t_stats[i] = (sr_b - sr_hat) / se_b   # studentized pivot

    tail = 1.0 - level
    lo_q, hi_q = np.quantile(t_stats, [tail / 2, 1 - tail / 2])
    # Invert the pivot: CI = SR_hat - SE_hat * [hi_q, lo_q].
    return sr_hat - se_hat * hi_q, sr_hat - se_hat * lo_q


# --- Stage 3c: factor alpha with Newey-West (HAC) standard error -----------

def alpha_newey_west(excess: np.ndarray, factors: np.ndarray, level: float = 0.90):
    """OLS alpha on a factor set, annualized, with a Newey-West HAC SE.

    factors: (T, k) matrix of factor returns. Returns (alpha_annual, ci_lo,
    ci_hi, betas). The HAC variance inflates the OLS SE to absorb residual
    serial correlation, using a Bartlett kernel with lag ~ T^(1/4).
    """
    T = excess.size
    X = np.column_stack([np.ones(T), factors])   # intercept + factors
    xtx_inv = np.linalg.inv(X.T @ X)
    coef = xtx_inv @ X.T @ excess
    resid = excess - X @ coef

    lag = max(1, round(T ** (1 / 4)))
    S = (X * resid[:, None]).T @ (X * resid[:, None])   # lag-0 term
    for L in range(1, lag + 1):
        w = 1.0 - L / (lag + 1)                          # Bartlett weight
        g = (X[L:] * resid[L:, None]).T @ (X[:-L] * resid[:-L, None])
        S += w * (g + g.T)
    cov = xtx_inv @ S @ xtx_inv
    se_alpha = np.sqrt(cov[0, 0])

    z = 1.645 if level == 0.90 else 1.96
    a_annual = coef[0] * MONTHS_PER_YEAR
    half = z * se_alpha * MONTHS_PER_YEAR
    return a_annual, a_annual - half, a_annual + half, coef[1:]


# --- Stage 4: manipulation-proof performance measure -----------------------

def mppm(returns: np.ndarray, rf: np.ndarray, rho: float = 3.0) -> float:
    """Annualized manipulation-proof performance measure (GISW)."""
    dt = 1.0 / MONTHS_PER_YEAR
    ratio = (1.0 + returns) / (1.0 + rf)
    return float(np.log(np.mean(ratio ** (1.0 - rho))) / ((1.0 - rho) * dt))


if __name__ == "__main__":
    rng = np.random.default_rng(7)
    true_r = 0.004 + 0.02 * rng.standard_normal(48)          # economic returns
    obs = 0.7 * true_r + 0.2 * np.roll(true_r, 1) + 0.1 * np.roll(true_r, 2)
    rf = np.full(48, 0.02 / 12)

    u = unsmooth(obs)
    excess_obs = obs - rf
    excess_eco = u["desmoothed_series"] - rf

    print("theta:", np.round(u["theta"], 3), "vol ratio:", round(u["vol_ratio"], 3))
    print("reported Sharpe + 95% CI:",
          np.round(sharpe_block_bootstrap_ci(excess_obs), 2))
    print("de-smoothed Sharpe + 95% CI:",
          np.round(sharpe_block_bootstrap_ci(excess_eco), 2))
    print("MPPM:", round(mppm(obs, rf), 4))
```

## 5. Reading the demo

The gallery page `s2.html` runs the whole pipeline on **one synthetic manager**
— *Kestrelmoor Partners* (code M07), equity long/short, **48 months**, tier R,
risk-free 2.0%/yr (synthetic). Every number below is the demo's actual output;
the demo generator imports the same pipeline the live sheet would use, so the
mapping from visual element to method is exact.

**Decision first:** keep monitoring and open a fees-for-beta conversation; do not
add on the point estimates. The known-truth construction exercises de-smoothing,
interval estimation, factor attribution, and drawdown-refusal mechanics. It does
not establish external calibration, predictive accuracy, or a conclusion about a
live manager.

- **De-smoothing panel.** Two side-by-side **interval stats**: reported Sharpe
  **0.71** (95% interval $[-0.26, 1.67]$) and de-smoothed Sharpe **0.60** (95%
  interval $[-0.29, 1.46]$). The fitted kernel is
  $\theta = (0.82,\ 0.18,\ 0.00)$ with vol ratio 0.84 — mild but real smoothing,
  which is why the economic Sharpe (0.60) sits below the reported one (0.71).
  **The band under each point is the confidence interval**; note it straddles
  zero — four years cannot rule out no-skill for this manager. The **MPPM
  (ρ=3) of +3.1%/yr** prints beside the Sharpe as the manipulation check; read
  the *gap* to the Sharpe, not the level.
- **Factor regression panel.** One **interval stat** for annualized alpha:
  **+3.2%** with a **90% interval of $[-4.4\%, +10.8\%]$**, beside the four
  factor betas (market 0.23, size 0.07, value −0.09, momentum 0.24). Because
  that 90% interval **contains zero**, the **verdict chip** reads
  **"provisionally alternative beta"** and states the interval — a calibration
  statement that 48 months cannot yet separate this alpha from factor exposure,
  and an opener for a fees conversation, not an accusation.
- **Drawdown panel.** The realized drawdown path (worst point about −10.5%)
  against the **pointwise 50 / 95 / 99th percentile null envelope** (fitted
  AR(1) = −0.04). The realized path **stays within the 99th-percentile
  envelope** — an ordinary drawdown under the paid-for-skill hypothesis, not an
  alarm.
- **Monthly-returns strip.** The raw 48-month series, for context beneath the
  estimated statistics.

**What an allocator should conclude:** Kestrelmoor looks *fine but unproven*.
The point numbers are respectable (Sharpe 0.6–0.7, alpha +3%/yr, an ordinary
drawdown), but every interval is wide and the alpha interval includes zero — so
the honest read is "consistent with real skill, not yet demonstrated at this
track length," which argues for continued monitoring and a fees-for-beta
conversation rather than a conviction add.

**Displayed-field reproduction map.**

| Displayed field | JSON field | Generator | Enforcing test |
| --- | --- | --- | --- |
| Reported/de-smoothed Sharpe and intervals | `statistics.sharpe_{reported,desmoothed}` | `demo_data/s2_tearsheet.py` | `tests/demo_data/test_s2_tearsheet.py` |
| Smoothing kernel and volatility ratio | `theta`, `unsmoothing.vol_ratio` | `demo_data/s2_tearsheet.py` | `tests/demo_data/test_s2_tearsheet.py` |
| Alpha, interval, and factor betas | `statistics.alpha`, `factor_betas` | `demo_data/s2_tearsheet.py` | `tests/demo_data/test_s2_tearsheet.py` |
| Alternative-beta chip | `alt_beta` | `demo_data/s2_tearsheet.py` | `tests/site/test_s2.py` |
| Drawdown envelope and realized path | `drawdown_band` | `demo_data/s2_tearsheet.py` | `tests/demo_data/test_s2_tearsheet.py` |
| Monthly-return strip | `monthly_returns` | `demo_data/s2_tearsheet.py` | `tests/site/test_s2.py` |

## 6. Honest limits & go-live

**Data contract per tier.** Conventions follow the S1 spec §2 verbatim: monthly
net returns as **decimals** on a pandas `PeriodIndex` with freq `M`; factor
returns aligned on the same months; annualize returns/alpha by ×12 and
volatilities by ×√12; a manager with more than 2 missing months in the window is
excluded and flagged, never silently interpolated; ≥24 months to enter, ≥36 for
full standing.

| Tier | Inputs | What it buys |
| --- | --- | --- |
| R (minimum) | Monthly net returns per manager; risk-free series; strategy label; strategy-appropriate factor returns on the same months | The **whole sheet** — de-smoothed Sharpe with CI, factor regression with interval alpha, alt-beta gate, MPPM, drawdown band. Everything in §3 runs returns-only. |
| E | Manager-reported factor / sector / gross / net exposure summaries (Open Protocol-aligned) | A **measured-vs-inferred exposure panel**: regression betas beside reported exposures; disagreement is flagged as a *question*, not an accusation. |
| P | Holdings / trade snapshots | **Measurement-only** holdings descriptors: active share, top-10 weight, HHI concentration. No estimation happens at P in this card — trade-level skill estimation is cards S3/S4. |

Factor sets by strategy (S1 §2): FF5+MOM for equity L/S; Fung–Hsieh 7 for
macro/trend; credit set **on unsmoothed returns** (stage 1 is a prerequisite,
not an option). Wave-1 uses synthetic factors; real-FF5 is a wave-3 upgrade —
the adapter already exists at `src/quant_allocator/adapters/french.py`.

**Power & validation plan.** Validation runs on the simulator; cells are
contributed to the X1 atlas ([`x1-tier-power-atlas.md`](x1-tier-power-atlas.md))
as this card's rows. Grid: $T \in \{36, 48, 60\}$ × strategy family × smoothing
level × true Sharpe, with seeded replications per cell (per-module RNG streams).
Acceptance gates:

1. **Alt-beta chip operating characteristics.** False-alarm rate (chip fires on
   a true-skill manager) and detection rate (chip fires on a true alt-beta
   manager) at each $T$; both curves reported, not a single threshold.
2. **CI coverage.** Empirical coverage of the Sharpe CI (Ledoit–Wolf) and the
   alpha CI (HAC) on simulated managers within **±5 pp of nominal**.
3. **Drawdown-band false-alarm rate.** On healthy managers, the fraction
   breaching the 99th-percentile envelope is **≤ the stated envelope
   percentile** (a calibrated 99th band false-alarms ≤1% of the time).
4. **θ-recovery.** Simulator returns passed through a *known* MA(2) smoother;
   the stage-1 MLE recovers the injected $\theta_k$ within tolerance, and the
   de-smoothed vol recovers the pre-smoothing vol.

**Kill criterion.** If Sharpe or alpha CI coverage is off by more than ±5 pp
*after* the Ledoit–Wolf bootstrap variant, the sheet ships **Lo-SE intervals
labeled "approximate"** — never an unlabeled interval claiming a coverage it
does not have. A miscalibrated interval sold as exact is worse than an honest
approximation. The demo's numbers are **illustrative and uncalibrated** until
these gates pass; every interval label and disclosure sentence on the page is a
numerics-gate obligation, not decoration.

**Implementation architecture.**

- `src/quant_allocator/flagships/tearsheet/pipeline.py` — stages 1–6 as **pure
  functions over a returns series + factor frame**: `unsmooth(returns) ->
  UnsmoothResult` (θ estimates + de-smoothed series), `regress(returns,
  factors) -> FactorFit`, `sharpe_intervals(returns) -> SharpeStats` (Lo SE +
  Ledoit–Wolf bootstrap), `alpha_interval(fit) -> AlphaStats` (HAC + bootstrap
  cross-check), `mppm(returns, rf, rho=3) -> float`, `drawdown_band(returns,
  hypothesis) -> DrawdownBand`. No rendering, no I/O in this module.
- `src/quant_allocator/flagships/tearsheet/render.py` — pack JSON emission
  (IntervalStat / VerdictChip / TierBadge payloads). The **demo generator
  (`demo_data/s2_tearsheet.py`) imports `pipeline.py`** — demo numbers and live
  numbers come from the *same code path*; only the input data differs
  (synthetic vs real). This is the load-bearing architectural commitment.
- Depends: `numpy` plus `scipy` — **scipy is a new runtime dependency**,
  added when this pipeline lands (optimizer for the MA(2) MLE; bootstrap and
  HAC are numpy-implementable). It runs only in local generation — CI never
  computes (gallery design §1). Also: the simulator (validation), the FF5
  adapter (`adapters/french.py`, wave-3 real-factor variant only). No PyMC —
  this card is estimator composition, not Bayesian inference.
- Effort: **S–M (~4 sessions)**: pipeline stages 2, validation grid 1, pack +
  demo page 1. Wave-1 ships on fully synthetic factors (no CI network
  dependency, no factor-data redistribution question); real-FF5 is a wave-3
  upgrade.

**Adoption & packaging.** The sheet **is the always-on layer** — every manager,
every month — and it is the first consumer of the Interval design system (this
card births `design-tokens.css` alongside the shell). It doubles as **rung-1
reciprocity in the E1 ladder**: the manager receives their own honest sheet,
which is what a returns-only relationship earns. Copy rules (Sweep E doctrine):
chips read as **calibration, not accusation** — always "what this track length
supports," never "your Sharpe is fake." The alt-beta chip is a **fee-conversation
opener**, not a dismissal, and always shows the interval so the manager sees
exactly what the data does and does not resolve. The S1 **posterior strip**
embeds when the skill ledger is available (S1 §3.6): the posterior alpha
IntervalStat sits beside the regression alpha, and the drawdown band uses the S1
posterior Sharpe as its maintained hypothesis when present, the claimed Sharpe
otherwise.

**Go-live requirements.**

- **Data ask:** monthly net returns (tier R) + a risk-free series + the chosen
  factor set for the manager's strategy. Tier E adds reported exposure summaries
  (measured-vs-inferred panel); tier P adds holdings snapshots (descriptors
  only).
- **Sample required:** ≥36 months for full standing (≥24 to render with an
  explicit short-track caveat). The alt-beta and drawdown panels are honest at
  any $T$ because their outputs are intervals and calibrated bands, not points.
- **Build effort:** S–M (~4 sessions). Real-FF5 factors are a wave-3 upgrade
  (adapter already built); wave-1 ships on synthetic factors.
- **Go-live box (demo page):** data ask = monthly returns (R); sample =
  ≥36 months; effort = S–M.

## 7. Deeper reading

**Canonical papers (read in this order), each with what it contributes:**

- **Lo (2002, FAJ)** — the Sharpe-ratio standard error and the
  annualization-under-autocorrelation result. Gives us the cheap closed-form
  interval and the warning that $\times\sqrt{12}$ overstates the annual Sharpe
  when returns are positively autocorrelated.
- **Getmansky–Lo–Makarov (2004, JFE)** — the moving-average smoothing model and
  de-smoothing. Explains hedge-fund return autocorrelation as smoothed illiquid
  marks, and gives the filter that recovers economic volatility and Sharpe.
- **Ledoit–Wolf (2008, JEF)** — studentized bootstrap confidence intervals for
  the Sharpe ratio. Provides the production CI that keeps honest coverage under
  fat tails and serial correlation, where the closed-form SE can be too tight.
- **Goetzmann–Ingersoll–Spiegel–Welch ("Sharpening Sharpe Ratios")** — the MPPM
  and its manipulation-proofness. Gives the power-utility performance measure no
  payoff-reshaping can game, so its gap to the Sharpe is a manipulation tell.
- **Fung–Hsieh (2004, FAJ)** — the 7-factor macro/trend model. Supplies the
  option-like factor set for trend followers; note the ~80% $R^2$ claim applies
  to diversified fund-of-funds portfolios, not single funds.

**Questions you should be able to answer after reading this page:**

- **State the T=48 Sharpe CI width from Lo's formula for annualized SR = 1**
  (annualized SE ≈ 0.51/yr, 95% CI roughly $[0, 2]$) and explain it to a
  non-quant: "with four years of monthly data a headline Sharpe of 1.0 is
  indistinguishable from both zero skill and world-class — not a criticism, just
  the arithmetic of four years."
- **Why can a de-smoothed Sharpe drop by a third?** Smoothing hides volatility,
  so the reported denominator is too small; restoring true vol (dividing by
  $\sqrt{\sum\theta_k^2} < 1$) can cut the ratio substantially for an illiquid
  book.
- **Explain the $\sqrt{12}$ trap.** Annualizing a monthly Sharpe by $\sqrt{12}$
  assumes zero serial correlation; with positive autocorrelation the correct
  scaling is *smaller* than $\sqrt{12}$, so naive annualization overstates the
  Sharpe — and smoothing manufactures exactly that positive autocorrelation, so
  a smoothed fund's headline number is inflated twice over. Unsmoothing (§3.3.1)
  is what maps it back.
- **Why is MPPM manipulation-proof?** It is the annualized certainty-equivalent
  return of a power-utility investor; being a monotone function of expected
  utility over the realized distribution, no payoff reshaping the investor would
  not genuinely prefer can raise it — unlike the Sharpe, which selling tails can
  game.
- **What does the alt-beta chip claim, and what does it not?** It says the
  factor-alpha 90% interval includes zero *at this track length* — a resolution
  statement and a fees-for-beta prompt — **not** that the manager is talentless
  or the alpha truly zero.
- **Why block-bootstrap rather than iid?** iid resampling of autocorrelated
  returns destroys the serial dependence that inflates the annual Sharpe, so its
  CIs are too tight; resampling blocks (length ≈ $T^{1/3}$) preserves within-block
  dependence, the circular wrap weights every observation equally, and
  studentizing buys second-order accuracy under fat tails.
