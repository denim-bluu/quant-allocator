# M3 · Simulation-Calibrated Drawdown Alarms — Method Spec

**Status: Reviewed (2026-07-07) — implementation-ready**
**Date:** 2026-07-07
**Card:** [`docs/ideas/2026-07-05-idea-cards.md`](../2026-07-05-idea-cards.md) § M3
**Demo:** gallery page `m3.html` (roster heat-list + two-manager same-drawdown split; fully synthetic, §5)

---

## 1. What this is

M3 is a **drawdown alarm**. It watches a manager's realized monthly return path and
answers one narrow question: *is this drawdown ordinary or extreme for a book like
this one?* Rather than judge every manager by a single house rule ("down 15% ⇒ put it
on review"), M3 simulates thousands of alternative histories for that **specific**
manager — under the skill level we are paying them to deliver — measures how deep a
drawdown that manager should reach purely by chance, and places the realized drawdown
on that simulated distribution as a percentile. The output is a calibrated verdict:
a GREEN / AMBER / RED level, a one-line receipt that always states the percentile
("MDD −18% sits at the 99.4th percentile of the null under the maintained Sharpe"),
and — across a whole book of managers — a roster heat-list whose false-alarm count is
printed on the tin.

The consumers are the **investment team**, who see a per-manager panel embedded in the
S2 tear sheet during ordinary monitoring, and **department leadership**, who see a
review-cadence roster heat-list at the decision moment. The decision it feeds is
**redeem-or-hold**: an alarm reads "this drawdown is inconsistent with the skill
hypothesis we are paying for," which is a calibrated *review trigger* routed to a
human — never a mechanical redemption, and never a claim that the alpha is provably
dead. Everything M3 produces is an input to a person's judgement, delivered with its
own uncertainty attached.

## 2. Why we use it

"Down 15% ⇒ put it on review" is the drawdown rule everyone uses and nobody defends.
The flaw is statistical illiteracy dressed up as prudence: a −12% drawdown is an
ordinary Tuesday for a high-volatility trend book and a 1-in-300 event for a smooth
credit fund. A flat threshold therefore does exactly the wrong thing in both
directions at once — it **fires on the healthy CTA** whose swings are normal for its
volatility, and it **sleeps through the credit book** whose alpha has quietly died but
whose gentle drawdown never reaches the house number. Same depth, different nulls: the
depth of a drawdown is only interpretable *relative to how deep that manager's book
should go on its own*.

The fix is to replace the flat rule with each manager's **own simulated null**. We
Monte-Carlo the drawdown distribution under the maintained skill hypothesis — the
Sharpe we claim to be buying (from the manager's prospectus, or better, from an S1
skill-ledger posterior), together with a de-smoothed volatility and a fitted AR(1)
autocorrelation — and ask whether the *realized* path is ordinary or extreme against
**that** distribution. What this wins over the naive rule: a redeem signal that is a
calibrated statement rather than a gut call, and a monitor view (the roster heat-list)
that leadership can read at a glance with its expected false-alarm count stated
alongside it.

M3 sits one deliberate step past the [S2 tear-sheet engine](s2-tear-sheet-engine.md).
S2's §3.6 drawdown panel is M3's direct **preview**: S2 already ships the machinery —
the Monte-Carlo null-path generator and a *pointwise* 50/95/99 envelope — but stops
short of an alarm. S2's `breaches_p99` flag asks "did the path dip below the pointwise
99th percentile at *any* month?" That is a **familywise** question answered with a
**pointwise** band, so its true false-alarm rate is nowhere near the 1% the "99th"
label implies (the mechanism is §3.3). This is a known open issue, recorded at the
numerics gate as **D-20** ("the pointwise (not familywise) p99 envelope semantics are
a gate question for how the page renders breaches"). M3 is the answer: a
**familywise-calibrated alarm** with a stated per-manager and per-roster false-alarm
budget, hysteresis so it does not flap, and a null that carries the S1 posterior's
uncertainty rather than a plugged-in point. **That last step is where the statistics
get subtle, and it is the whole of M3.**

- **Decisions improved:** **redeem** — a calibrated review trigger, not a gut call;
  **monitor** — a roster heat-list leadership can read at a glance, with its
  false-alarm count stated on the tin.
- **Customer:** investment team (per-manager panel, embedded in the S2 sheet);
  department leadership (roster heat-list).

## 3. How it works

### 3.1 The mental model, before any math

Picture one manager. We do not know the future, but we *are* willing to state a
hypothesis about their skill: "this is a Sharpe-1.0 book running at 6% annual
volatility with mild mean-reversion." Grant that hypothesis and you can **generate**
the futures it implies — draw a few thousand 48-month return paths from it. Each
simulated path has its own worst peak-to-trough loss, its **maximum drawdown**. Line
up those few thousand maximum drawdowns and you have the *null distribution*: the range
of worst-case losses a book with exactly this skill produces by luck alone. Now take
the manager's **actual** worst drawdown and ask where it falls on that pile. At the
10th percentile? Utterly ordinary — GREEN. Past the 99th? A book this good should
almost never sink that far — RED, worth a conversation.

That is the whole idea, and it immediately explains the demo's punchline. Two managers
both post the same realized −12% drawdown. For a 20%/yr trend book, −12% sits around
the **10th percentile** of its own null — a shrug. For a 6%/yr credit book, −12% sits
near the **99.5th percentile** of *its* null — a five-alarm fire. Nothing about "12%"
changed; the two nulls are simply very different, because a smooth low-volatility book
*should almost never* be down 12%, while a high-volatility book is down 12% all the
time.

Two subtleties turn this simple picture into a disciplined alarm, and both are worth
building intuition for before the formulas.

**Subtlety one — do not scan a per-month band.** A tempting shortcut is to draw a band
at each month (the 99th-percentile drawdown *for that month*) and fire whenever the
realized path pokes below it *anywhere* over the window. This is the classic
multiple-comparisons trap. Concretely: suppose you had **10 independent monthly
looks**, each with a genuine 1% chance of a false breach. The chance of *at least one*
false breach across the ten is `1 − 0.99^10 ≈ 9.6%` — nearly ten times the 1% you
intended. Scan 48 months and (under independence) it is `1 − 0.99^48 ≈ 38%`. A
"99th-percentile" band, read as a scanning alarm, cries wolf a third of the time. The
fix is to stop scanning per-month values and instead test **one number per path** — the
maximum drawdown — whose null distribution already folds every month together.

**Subtlety two — do not pretend you know the skill exactly.** The whole null hangs on
the maintained Sharpe, and a 36–60-month Sharpe estimate is itself uncertain. If we
plug in a single point Sharpe we are silently claiming to know the manager's true skill
exactly, which makes the null artificially narrow and the alarm artificially
confident. The honest move is to **draw** the Sharpe from its posterior on each
simulated path, so the null distribution widens to reflect "we are not certain how good
this manager is." The alarm then only fires when the drawdown is extreme *even granting*
that uncertainty.

### 3.2 The drawdown and the alarm statistic

Everything below runs on the realized monthly return series and the simulated ones the
same way. Start from wealth and drawdown.

$$
W_t = \prod_{u \le t} (1 + r_u), \qquad
D_t = 1 - \frac{W_t}{\max_{s \le t} W_s}, \qquad
\text{MDD} = \max_{t \le T} D_t .
$$

where:

- $r_u$ — the net return in month $u$ (decimal, e.g. `-0.04` for −4%).
- $W_t$ — cumulative wealth after month $t$, starting from $W_0 = 1$; the product of
  gross returns to date.
- $\max_{s \le t} W_s$ — the running peak (high-water mark) up to month $t$.
- $D_t$ — the **running drawdown**: the fractional distance below the high-water mark
  at month $t$. $D_t = 0$ at a new peak; $D_t = 0.12$ means 12% below the peak.
- $\text{MDD}$ — the **maximum drawdown** over the review window: the deepest $D_t$
  reached across all $T$ months. **One scalar per path.**
- $T$ — the review-window length in months (v1: the manager's full evaluated track).

In words: wealth compounds the monthly returns; the drawdown at each month is how far
below the best-ever wealth you have fallen; the maximum drawdown is the worst that ever
got. The MDD is a **max of a running-minimum process** — not a marginal quantile of any
single month — which is exactly why it is the right thing to test.

### 3.3 Pointwise versus familywise — why S2's band is not an alarm

S2 draws a **pointwise** envelope: at each month $t$, the tail quantile of the null
drawdown *at that month*. Read as a chart it is honest — "at this month, in isolation,
how deep is a 99th-percentile drawdown?" Read as an **alarm** (`np.any(realized < band)`,
S2's `breaches_p99`) it commits the multiple-comparisons error. Define, for a chosen
per-month tail level $\alpha$ (S2 uses $\alpha = 0.01$):

$$
p_{\text{point}} = \Pr\big(D_t < q_\alpha(t)\big)\ \text{for a fixed } t = \alpha,
\qquad
p_{\text{family}} = \Pr\!\Big(\exists\, t \le T:\ D_t < q_\alpha(t)\Big) \gg \alpha .
$$

where:

- $\alpha$ — the intended per-look tail probability (e.g. 0.01 for a "99th-percentile"
  band).
- $q_\alpha(t)$ — the pointwise null band at month $t$: the $\alpha$-quantile of the
  simulated drawdown *at that single month*.
- $p_{\text{point}}$ — the chance the path breaches the band **at one fixed month**;
  by construction equal to $\alpha$.
- $p_{\text{family}}$ — the chance the path breaches the band **at some month over the
  whole window**; the quantity a scanning monitor actually realizes.

In words: the pointwise band is calibrated for a single month, but a monitor asks the
*max-over-all-months* question, and the probability of *some* breach is far larger than
the per-month $\alpha$. Even under **independence**,
$p_{\text{family}} \approx 1 - (1 - \alpha)^{T_{\text{eff}}}$, where $T_{\text{eff}}$ is
the effective number of independent looks. Drawdowns are highly autocorrelated (a
drawdown persists across months), so $T_{\text{eff}} < T$ — but for $\alpha = 0.01$ and
$T = 48$ the familywise breach rate of a pointwise 99th band still lands in the low tens
of percent, not 1%. **A pointwise band read as an event is an alarm that cries wolf**,
and §6's validation gate 2 measures exactly this inflation on the simulator so the
correction is shown to be necessary, not asserted.

### 3.4 The fix — path max-drawdown, familywise by construction

The clean fix is to alarm on the **path-level scalar** of §3.2, not a per-month band.
One MDD per path ⇒ **no multiplicity**. Simulate $N_{\text{paths}}$ null paths (§3.7),
compute each path's MDD, and the null distribution of MDD is exact. The alarm threshold
at familywise level $\alpha$ is the upper-$\alpha$ quantile of that null MDD
distribution, so an $\alpha$-level MDD alarm has **exactly** an $\alpha$ familywise
false-alarm rate — by construction, with no correction factor to tune. This is the
disciplined move the multiple-testing literature (Westfall & Young, §7) formalizes:
control the **max statistic** directly rather than patch up a family of per-look tests.

**Plottable equivalent (for the panel).** The scalar test has a chart form that
preserves the "where on the path" story S2's panel tells. For each null path compute the
**running max-drawdown-to-date**,

$$
M_t = \max_{s \le t} D_s ,
$$

where $M_t$ is the worst drawdown seen *up to and including* month $t$ (a monotone
non-decreasing series). Take the $\alpha$-quantile of $M_t$ across null paths at each
$t$ to get a **familywise band** $B_t$ — a running-worst envelope. The event "the
realized running-MDD exits the band at the window end" ($M_T > B_T$) is *identically*
the event "realized MDD exceeds the $\alpha$-quantile of null MDD." So the panel plots
the realized running-MDD against $B_t$, and a breach on that chart **is** a calibrated
$\alpha$ event — unlike S2's pointwise band, where a breach is not. This is the direct
answer to gate note D-20's "how the page renders breaches."

**Secondary channel (flagged).** Drawdown *depth* misses a slow bleed that never gets
deep but stays underwater for years. A second path scalar — **time underwater** (longest
run of consecutive months with $D_t > 0$), calibrated the same way — catches duration
where MDD catches depth. Whether v1 ships one channel or both is flagged
**`ALARM_CHANNELS` (provisional)**; the default recommendation is **depth in v1,
duration as the first extension**, to keep the budget arithmetic (§3.5)
single-statistic and legible.

### 3.5 Alarm levels and the per-manager budget

Three levels, each pinned to a familywise quantile of the null MDD, each with a
**stated false-alarm budget** — the probability it fires on a manager whose book
genuinely matches the maintained hypothesis, over one review window:

| Level | Fires when realized MDD exceeds… | Familywise budget (healthy manager) |
| --- | --- | --- |
| **GREEN** | — (MDD inside the 95th-pct null band) | — |
| **AMBER** | the **95th**-percentile null MDD | ≤ 5% per review window |
| **RED** | the **99th**-percentile null MDD | ≤ 1% per review window |

The budgets are **`ALARM_LEVELS` (provisional — AMBER 5% / RED 1%)**. Because the
statistic is a single scalar, "budget" is not a hope — it is the *definition* of the
quantile, and §6's validation gate 1 confirms the simulator honors it within
Monte-Carlo error. The alarm's headline is always the calibrated statement — *"MDD
−18% sits at the 99.4th percentile of the null under the maintained Sharpe"* — never a
bare "−18%, breached."

A worked micro-example of the levels. Take a smooth 6%/yr book. Simulate its null and
suppose the 95th-percentile null MDD comes out at −9% and the 99th at −11%. A realized
−7% is GREEN (inside −9%); −10% is AMBER (past −9%, inside −11%); −12% is RED (past
−11%). Now take a 20%/yr trend book: its 95th/99th null MDD might be −34% / −42%, so
the *same realized −12%* is deep inside GREEN. Two managers, one drawdown depth,
opposite verdicts — because each is measured against its own null. (These are the
demo's actual numbers; see §5.)

### 3.6 The roster budget — the second multiplicity layer

A leadership heat-list across $N_{\text{mgr}}$ managers has its **own** multiplicity,
and it is the one that quietly discredits monitoring systems. If each healthy manager's
RED fires at 1% familywise, a roster of $N_{\text{mgr}} = 40$ healthy managers expects
$0.4$ false REDs *per review*, and

$$
\Pr(\text{≥1 false RED on a healthy roster of } 40) = 1 - 0.99^{40} \approx 0.33 .
$$

A third of clean reviews would surface a red flag. M3's honest move is to **state the
expected false-RED count on the heat-list itself**:

$$
\mathbb{E}[\text{false RED}] = N_{\text{mgr}} \times (\text{per-manager RED rate}),
$$

printed beside the list ("2 REDs this review; ~0.4 expected by chance on a healthy
roster of 40"). Leadership reads the flags **with the multiplicity in view** — the
count is a feature of the pitch, exactly like a working PowerGate.

An **optional** roster-familywise tightening (shrink per-manager $\alpha$ so the
roster-level rate hits a budget) is offered but **off by default**: at
$N_{\text{mgr}} = 40$ a Bonferroni tightening to a 1% roster budget sets per-manager
$\alpha \approx 0.00025$, which at $T \le 60$ destroys detection power (§6, gate 3). The
default — report the expected-false count, do not silently correct — is the right level.

**Not an FDR screen.** This roster budget controls **monitor false-alarms** (drawdowns),
which the do-not-build list permits; it is **not** the prohibited *FDR luck-screen on
alphas at roster scale* (convergence decision §4). M3 runs no cross-manager
alpha-discovery test; it reports one honest count so a heat-list is not read naively.
The distinction is stated on the page.

### 3.7 The null — posterior-informed, not plugged-in

The maintained hypothesis is the single most important input, and S2's preview plugs it
in as a **point** Sharpe. That silently claims we know the true Sharpe exactly — a
bare-point sin the Interval doctrine forbids for the input that most moves the answer.
M3 propagates its uncertainty.

**With the S1 skill ledger (preferred).** The null becomes a **posterior-predictive**
drawdown distribution. For each of $N_{\text{paths}}$ Monte-Carlo paths:

1. **draw** a Sharpe $SR^{(j)}$ from the manager's S1 posterior (the ledger's posterior
   alpha/vol, S1 §3.5–3.6);
2. **simulate** the AR(1) return path at that Sharpe, with de-smoothed vol from S2 stage
   1 and fitted AR(1) autocorrelation;
3. **record** its MDD.

where:

- $SR^{(j)}$ — the Sharpe used on the $j$-th simulated path, itself a random draw from
  the posterior (not a fixed constant).
- $N_{\text{paths}}$ — the number of simulated null paths (**`DRAWDOWN_PATHS_M3` =
  10,000 provisional**; see §6).

The resulting null MDD distribution is **wider** than any single plug-in, because it
folds in "we are not certain how good this manager is." The alarm quantiles (§3.5) are
read off *this* posterior-predictive distribution. This is the Interval-compliant alarm:
it fires on evidence the drawdown is extreme **even granting our uncertainty about the
paid-for skill.** It is the same move S1 makes for alphas — a posterior-predictive
check (Gelman et al., *BDA3*, ch. 6) — applied to the drawdown null.

**Without S1 (fallback).** Use the claimed Sharpe as a **point**, but never silently —
render the alarm level across a **Sharpe fan** (the card's explicit requirement: "report
alarm level across a Sharpe range"), e.g. claimed Sharpe × {0.5, 1.0, 1.5}. The panel
shows RED-at-claimed alongside AMBER-at-half, so the reader sees how much the verdict
leans on the maintained number. The Dietvorst dial (§6) makes that fan interactive.

**Second-order inputs.** De-smoothed vol and the AR(1) coefficient also carry estimation
error; v1 plugs them as points because the Sharpe fan dominates the band width at
$T \le 60$. Whether the posterior-predictive draw should also sample vol/AR(1) (a fuller
nested MC) is flagged **`NULL_NESTED_MC` (provisional — Sharpe-only in v1)**.

### 3.8 Hysteresis — arming and clearing without flapping

A single-threshold alarm chatters when the drawdown hovers at the line. M3 uses a
**two-threshold (Schmitt-trigger) rule**, borrowed from control theory: the level that
*arms* an alarm is not the level that *clears* it.

- **Arm RED** when realized MDD first exceeds the 99th-pct null band.
- **Hold RED** until the drawdown **recovers** — the *current* drawdown climbs back
  inside the **95th**-pct band (the AMBER line, not the RED line) **and** stays there
  for **`HYSTERESIS_CLEAR_MONTHS` (provisional — 2)** consecutive months. Only then does
  it step down.
- Symmetric arm/clear for AMBER↔GREEN.

The gap between the arm line (99th) and the clear line (95th) is the hysteresis band;
requiring a short persistence run past the clear line kills single-month flip-flops
around a boundary. The clear rule is stated as **recovery of the drawdown**, not "N
months elapsed," so the alarm tracks the manager's actual condition, not the calendar.

### 3.9 What the canonical papers contribute

- **van Hemert, Ganesh, Rohrbach, Roscioni et al. (2020), "Drawdowns"
  (*J. Portfolio Management*).** Showed that raw drawdown depth is a poor standalone
  signal, but that a drawdown compared to a *simulated* distribution under an assumed
  return process becomes a usable, calibrated rule. This is M3's direct methodological
  anchor: use drawdown as a **calibrated flag**, never as an estimator of skill.
- **Magdon-Ismail & Atiya (2004), "Maximum Drawdown."** Derived the closed form for the
  *expected* maximum drawdown of a Brownian path with drift $\mu$ and vol $\sigma$ over
  horizon $T$. In the low-drift regime expected MDD scales like $\sigma\sqrt{T}$ and is
  *tamed* by positive drift. This is precisely why two books with the same realized −12%
  sit at different percentiles: same depth, different $(\mu, \sigma)$ null.
- **Westfall & Young (1993), *Resampling-Based Multiple Testing*.** Established
  max-statistic / familywise control by resampling. §3.3–3.4 apply its logic to a path:
  control the max-over-months statistic (the MDD) directly, and the familywise error is
  exactly $\alpha$ with no ad-hoc correction.
- **Gelman, Carlin, Stern, Dunson, Vehtari & Rubin, *BDA3*, ch. 6.** Posterior-predictive
  distributions: simulate replicate data by drawing parameters from the posterior, not
  by fixing them at a point. §3.7's posterior-informed null is exactly this, applied to
  the drawdown of a return path.

## 4. How to implement

The reference implementation below is **self-contained teaching code** — paste it into a
fresh file, it runs on `numpy` alone. It implements the same formulas as §3: the AR(1)
null generator (§3.7), running drawdown and MDD (§3.2), the familywise running-MDD band
(§3.4), the level logic and budget (§3.5), the posterior-predictive null (§3.7), the
Schmitt-trigger hysteresis (§3.8), and the roster expected-false count (§3.6). It uses no
project imports and no repo paths.

```python
import numpy as np

# ---------------------------------------------------------------------------
# 1. Null-path generator: AR(1) monthly returns at a maintained hypothesis.
#    A Sharpe + annual vol imply a monthly mean and monthly vol; the AR(1)
#    coefficient adds the mild month-to-month autocorrelation real books show.
# ---------------------------------------------------------------------------
def simulate_ar1_paths(sharpe, vol_annual, ar1, months, n_paths, rng):
    """Return an (n_paths, months) array of simulated monthly net returns.

    sharpe      : annualised Sharpe ratio of the maintained hypothesis.
    vol_annual  : annualised volatility (e.g. 0.06 for a 6%/yr book).
    ar1         : AR(1) autocorrelation of monthly returns (can be negative).
    """
    vol_m = vol_annual / np.sqrt(12.0)            # monthly vol
    mean_m = sharpe * vol_annual / 12.0           # monthly mean s.t. annual Sharpe holds
    # Innovation vol chosen so the *stationary* series has vol_m, given AR(1).
    innov_vol = vol_m * np.sqrt(1.0 - ar1 ** 2)
    r = np.empty((n_paths, months))
    prev = rng.normal(0.0, vol_m, size=n_paths)   # stationary start
    for t in range(months):
        eps = rng.normal(0.0, innov_vol, size=n_paths)
        cur = ar1 * prev + eps
        r[:, t] = mean_m + cur                    # add drift back in
        prev = cur
    return r


# ---------------------------------------------------------------------------
# 2. Running drawdown and max drawdown (§3.2).
#    D_t = 1 - W_t / running_peak(W);  MDD = max_t D_t.
# ---------------------------------------------------------------------------
def running_drawdown(returns):
    """(n_paths, months) drawdown series D_t for each path (D_t >= 0)."""
    wealth = np.cumprod(1.0 + returns, axis=1)
    running_peak = np.maximum.accumulate(wealth, axis=1)
    return 1.0 - wealth / running_peak


def max_drawdown(returns):
    """(n_paths,) maximum drawdown per path: MDD = max_t D_t."""
    return running_drawdown(returns).max(axis=1)


def running_mdd(returns):
    """(n_paths, months) running-worst drawdown M_t = max_{s<=t} D_s (monotone)."""
    return np.maximum.accumulate(running_drawdown(returns), axis=1)


# ---------------------------------------------------------------------------
# 3. Posterior-predictive null (§3.7): draw the Sharpe per path instead of
#    plugging a point, so the null widens to reflect skill uncertainty.
#    Pass sharpe_draws=None to fall back to the plug-in null at a fixed Sharpe.
# ---------------------------------------------------------------------------
def null_mdds(sharpe, vol_annual, ar1, months, n_paths, rng, sharpe_draws=None):
    """(n_paths,) null MDDs. If sharpe_draws is given (a callable rng, n -> array),
    each path uses its own drawn Sharpe (posterior-predictive)."""
    if sharpe_draws is None:
        returns = simulate_ar1_paths(sharpe, vol_annual, ar1, months, n_paths, rng)
        return max_drawdown(returns)
    # Posterior-predictive: one Sharpe per path, simulated one path at a time.
    drawn = sharpe_draws(rng, n_paths)            # (n_paths,) Sharpe draws
    out = np.empty(n_paths)
    for j in range(n_paths):
        path = simulate_ar1_paths(drawn[j], vol_annual, ar1, months, 1, rng)
        out[j] = max_drawdown(path)[0]
    return out


# ---------------------------------------------------------------------------
# 4. Familywise band and alarm level (§3.4, §3.5).
#    amber_budget / red_budget are the familywise false-alarm budgets; the
#    thresholds are the (1 - budget) quantiles of the null MDD distribution.
# ---------------------------------------------------------------------------
def familywise_band(returns, amber_budget=0.05, red_budget=0.01):
    """Return (amber_curve, red_curve): the per-month quantile of the running
    MDD across null paths. Plotting the realized running-MDD against these two
    curves is the chart form of the scalar MDD test (§3.4)."""
    m = running_mdd(returns)                      # (n_paths, months)
    amber_curve = np.quantile(m, 1.0 - amber_budget, axis=0)
    red_curve = np.quantile(m, 1.0 - red_budget, axis=0)
    return amber_curve, red_curve


def alarm_level(realized_mdd, null_mdd_samples,
                amber_budget=0.05, red_budget=0.01):
    """Map a realized MDD onto GREEN/AMBER/RED plus its null percentile."""
    amber_thr = np.quantile(null_mdd_samples, 1.0 - amber_budget)
    red_thr = np.quantile(null_mdd_samples, 1.0 - red_budget)
    percentile = 100.0 * np.mean(null_mdd_samples <= realized_mdd)
    if realized_mdd > red_thr:
        level = "red"
    elif realized_mdd > amber_thr:
        level = "amber"
    else:
        level = "green"
    return level, percentile, amber_thr, red_thr


# ---------------------------------------------------------------------------
# 5. Hysteresis (§3.8): a two-threshold state machine. Arm on the RED line,
#    clear only after the drawdown recovers inside the AMBER line and holds
#    there for `clear_months` consecutive months.
# ---------------------------------------------------------------------------
def hysteresis_states(running_mdd_path, amber_curve, red_curve, clear_months=2):
    """Step a single realized running-MDD path through the alarm state machine."""
    state = "green"
    calm = 0                                      # consecutive months inside AMBER
    out = []
    for t, m_t in enumerate(running_mdd_path):
        armed_red = m_t > red_curve[t]
        armed_amber = m_t > amber_curve[t]
        inside_amber = m_t <= amber_curve[t]
        calm = calm + 1 if inside_amber else 0
        if armed_red:
            state = "red"
        elif state == "red":
            if inside_amber and calm >= clear_months:
                state = "amber"                   # step down only after recovery
        elif armed_amber:
            state = "amber"
        elif state == "amber" and inside_amber and calm >= clear_months:
            state = "green"
        out.append(state)
    return out


# ---------------------------------------------------------------------------
# 6. Roster honesty (§3.6): print the expected number of false REDs, do not
#    silently Bonferroni-correct it away.
# ---------------------------------------------------------------------------
def expected_false_reds(n_managers, per_manager_red_rate=0.01):
    """E[false RED] = N * per-manager RED rate — the number the heat-list prints."""
    return n_managers * per_manager_red_rate


# ---------------------------------------------------------------------------
# Worked example: the same -12% drawdown, opposite verdicts.
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    rng = np.random.default_rng(0)
    N_PATHS, MONTHS = 10_000, 48

    for name, vol, sharpe in [("trend  (20%/yr)", 0.20, 0.7),
                              ("credit ( 6%/yr)", 0.06, 1.0)]:
        nulls = null_mdds(sharpe, vol, ar1=-0.2, months=MONTHS,
                          n_paths=N_PATHS, rng=rng)
        level, pct, amber, red = alarm_level(0.12, nulls)
        print(f"{name}: -12% MDD -> {level.upper():5s} "
              f"({pct:5.1f}th pct;  null 95th={amber:.0%}, 99th={red:.0%})")
```

Run it and the trend book prints GREEN (−12% far inside its wide null), the credit book
RED (−12% past its narrow 99th) — the demo's punchline reproduced from first principles.

## 5. Reading the demo

The gallery page `m3.html` is fully synthetic (§6 compliance). It has three parts.

**The two-manager split — the centrepiece.** Two managers post the **same realized
−12% max drawdown**:

- **Windward Trend Partners** — 20%/yr vol, claimed Sharpe 0.7. Realized MDD lands at
  the **10th percentile** of its own null (null 95th/99th band at roughly −34% / −42%).
  Verdict: **GREEN** — an ordinary drawdown for a book this volatile.
- **Stillwater Credit Partners** — 6%/yr vol, claimed Sharpe 1.0. Realized MDD lands at
  the **99.5th percentile** of its null (null 95th/99th band at roughly −9% / −11%).
  Verdict: **RED** — a calibrated reason to review.

How each visual element maps to the method:

- **Verdict chip** (green / amber / red) = the alarm *level* of §3.5 — inside the 95th
  band, past it, or past the 99th.
- **The "Realized max drawdown" rail** = an IntervalStat: the point is the manager's
  realized MDD; the shaded band is *that manager's* null 95th–99th (AMBER–RED)
  thresholds. Same −12% point, very different bands — the whole idea in one graphic.
- **The running max-drawdown chart** = the §3.4 plottable equivalent: the ink line is
  the realized running-MDD $M_t$; the amber and red fills are the familywise band $B_t$.
  A breach at the right-hand (window) edge **is** a calibrated α event.
- **The skepticism dial** = the §3.7 Sharpe fan, precomputed across {0.5, 1.0, 1.5}× the
  claimed Sharpe. Snapping it shows how far the verdict leans on the maintained number
  (the Dietvorst move, §6).

**The roster heat-list.** Twelve synthetic managers; the page prints **2 REDs this
review** against **~0.12 expected by chance** on a healthy roster of 12 (size × the 1%
per-manager RED budget). Each row's percentile is read against that manager's own null.
The list is deliberately shown *with* its expected-false count so leadership never reads
the flags naively — and the page states this is a **monitor** false-alarm count, **not**
an FDR alpha-screen.

**The power gate.** The honest refusal: detection of slow alpha death is low-power at
$T \le 60$ (one drawdown episode is n ≈ 1), so the alarm is a *calibrated flag*, never
proof the alpha is gone and never an auto-redeem.

What an allocator should conclude from these numbers: the flat "−12% ⇒ review" rule
would have treated Windward and Stillwater identically; M3 correctly waves Windward
through and flags Stillwater, *and* tells leadership that on a clean roster of this size
they should expect about 0.12 false REDs — so two observed REDs is a genuine signal, not
roster noise.

## 6. Honest limits & go-live

### 6.1 What M3 does not do (do-not-build adjacency)

- **No raw drawdown inference.** M3 never claims a drawdown *proves* skill is gone. At
  $T \le 60$ raw DD inference is Noise (Sweep C — one episode dominates the path). M3 is
  legitimate **only as a simulation-calibrated rule**: it says "extreme *relative to the
  stated null*," a calibrated flag, not a verdict on the alpha.
- **No regime splits, no conditional betas, no persistence test** (convergence §4). The
  null is a stationary AR(1) under one maintained Sharpe; M3 does not slice the path into
  regimes or fit time-varying parameters.
- **No FDR alpha-screen** (§3.6) and **no auto-redeem** (§6.5). An alarm is a review
  trigger routed to a human, never a mechanical redemption.

### 6.2 Data contract per tier

M3 is **returns-native**: it needs the realized path plus a maintained hypothesis, both
of which the R tier already carries. Higher tiers refine the null; they do not unlock
the card.

| Tier | Inputs the live version needs | What the card produces |
| --- | --- | --- |
| **R** (minimum) | Monthly net returns per manager (decimals, `PeriodIndex` freq `M`; S1/S2 §2 conventions); a **maintained Sharpe hypothesis** — the S1 posterior Sharpe *distribution* when the skill ledger is available, the manager's claimed/prospectus Sharpe as a point otherwise; risk-free series. | The **whole alarm**: familywise-calibrated drawdown band, max-drawdown alarm statistic, GREEN/AMBER/RED level with hysteresis, and the roster heat-list entry. Everything in §3 runs returns-only. |
| **E** | R + vol-targeting / gross-exposure context (Open Protocol-aligned) | A **sharper null**: a stated vol target replaces the returns-estimated vol as the band's volatility input, and gross-leverage context bounds the plausible Sharpe fan — narrower, better-motivated bands, not a different alarm. |
| **P** | — | **n/a** (card §"Tier rungs"). Holdings do not refine a drawdown null; M3 stays returns-and-exposure only. |

**Frequency & window.** Monthly returns at each manager's native cadence. The familywise
budget (§3.5) is stated over an explicit **review window** — the manager's evaluated
track length $T$ in v1; whether the live default is a rolling window instead is flagged
**`ALARM_WINDOW` (provisional)**.

**Compliance (standing):** synthetic managers in the repo; any real-data rung uses the
manager's own returns and a publicly stated or internally maintained Sharpe — no
employer-internal facts in code, docs, or the committed demo JSON.

### 6.3 Calibration honesty (what the budgets promise, and don't)

The AMBER 5% / RED 1% budgets are stated **under the fitted null**. Because the null's
parameters (vol, AR(1), and — in the fallback — the point Sharpe) are themselves
estimated from a short track, realized false-alarm rates can run **above nominal** at
short track lengths: validation at $T = 48$ measured **roughly 2% for the 1% RED
budget**. The demo page carries this disclosure verbatim. The hardened build recalibrates
with parameter-uncertainty-aware nulls (the §3.7 posterior-predictive path is the first
step); until then the stated budgets are the *design* target, and the ~2% figure is the
*measured* short-track slack — both are shown, neither is hidden.

### 6.4 Power & validation plan

Validation runs on the simulator; cells contribute to the X1 atlas
([`x1-tier-power-atlas.md`](x1-tier-power-atlas.md)) as this card's rows. Grid follows
the atlas convention: $T \in \{36, 48, 60\}$ × strategy family × smoothing level × true
(pre-death) Sharpe, ≥1,000 seeded replications per cell (per-module RNG streams; Wilson
95% intervals on every rate — X1 §3.3). The card's two named atlas axes are
**time-to-detection** (manager whose true alpha dies at month $k$) versus **false-alarm
rate** (healthy manager).

Acceptance gates:

1. **Familywise false-alarm calibration (the load-bearing gate).** On healthy managers
   (true return process = the maintained hypothesis), the measured RED familywise rate is
   **≤ 1% within MC error**, AMBER **≤ 5%** — the budget M3 promises and the pointwise
   band cannot keep. This is the gate that justifies the whole card.
2. **Pointwise-inflation demonstration.** Measure S2's *pointwise*-band familywise breach
   rate on the same healthy managers and report it beside the corrected rate. Expected:
   low tens of percent versus the calibrated 1%. This is the evidence D-20 asks for — the
   correction is shown, not claimed.
3. **Detection / time-to-detection.** Inject alpha death at month $k$ (IC steps to zero
   at $k$; **simulator extension required — see below**) and report the detection rate
   within a review horizon and the median months-to-first-RED, as a curve against
   pre-death Sharpe and $T$. Reported as an operating characteristic traded against gate
   1, never a single threshold.
4. **Maintained-hypothesis sensitivity.** Sweep the plugged Sharpe across the §3.7 fan and
   report how the RED rate moves; with S1, report **coverage of the posterior-predictive
   band** (does the realized MDD fall inside the stated quantile at the nominal frequency,
   within ±5 pp). The card's stated statistical risk — "sensitivity to the
   maintained-hypothesis inputs" — is measured here, not hand-waved.
5. **Roster-budget check.** On a healthy synthetic roster of size $N_{\text{mgr}}$, the
   measured expected false-RED count matches $N_{\text{mgr}} \times$ (per-manager RED
   rate) within MC error, validating the number the heat-list prints (§3.6).

**Simulator dependency (honest).** The current `simulator/manager.py` has a constant
`information_coefficient` with age-decay but **no mid-track death event**; gate 3 needs a
piecewise-IC extension (IC → 0 at month $k$). This is a **named validation
prerequisite**, small, and flagged as such — not assumed present.

### 6.5 Kill criteria

- **Statistical.** If the familywise RED rate cannot be held within budget **across the
  maintained-hypothesis uncertainty range** — i.e., the band is so sensitive to the
  Sharpe input that no honest single budget exists — M3 **ships as a descriptive band
  only**: the panel states the realized MDD's percentile under the stated null and the
  S2-style envelope, with **no GREEN/AMBER/RED level and no roster heat-list**, recorded
  in writing per converge-or-cut. A miscalibrated alarm sold as a 1% event is worse than
  an honest percentile.
- **Political.** An alarm is a review trigger, never an auto-redeem; if a consumer wires
  it to automatic action the card is pulled. Goodhart: an alarm published as a hard
  redemption rule gets gamed — managers manage the book to the band — so it ships as a
  flag on a review, not an automatic action.

### 6.6 How it ships in the repo

The commitment is **reuse S2's MC machinery, add only the alarm layer.**

- **Refactor (small) in `src/quant_allocator/flagships/tearsheet/pipeline.py`:** extract
  the null-path simulation currently inside `drawdown_band` into a reusable primitive
  `simulate_null_drawdowns(hypothesis, t, n_paths, seed) -> troughs` (the
  `n_paths × T` matrix of running drawdowns). `drawdown_band` keeps its exact behavior by
  calling it and taking pointwise percentiles; M3 calls it and takes path scalars. **No
  estimator is duplicated.**
- **New module `src/quant_allocator/flagships/alarms/pipeline.py`:** pure functions over
  the null troughs — `max_drawdown_null(troughs) -> np.ndarray` (per-path MDD),
  `familywise_band(troughs, levels) -> AlarmBand` (running-MDD quantile envelope, §3.4),
  and `alarm_state(returns, hypothesis, *, prev_state, roster_size) -> AlarmVerdict`
  carrying level, the realized MDD percentile, the hysteresis state, and the §3.6
  expected-false-RED count. No rendering, no I/O (S2 §5 convention).
- **Posterior-informed null:** `alarm_state` accepts `hypothesis` as **either** a
  `DrawdownHypothesis` (point, fallback) **or** a `PosteriorHypothesis` (Sharpe draws from
  the S1 ledger); the second path does the §3.7 posterior-predictive draw. The S1
  posterior is consumed via the existing `skill_ledger` `empirical.py` closed-form output
  — **import, do not re-fit** (no PyMC in M3).
- **Demo — `src/quant_allocator/demo_data/m3_alarms.py`** (imports the pipeline; same code
  path as any live build, only the input data is synthetic). The **wow-demo**: two
  synthetic managers with the **same realized −12% drawdown** — a high-vol trend book
  (GREEN) and a smooth credit book (RED) — plus a small **roster heat-list** with the
  expected-false-RED count printed. Emits committed JSON to `site/data/m3_alarms.json` via
  `_emit.write_json`; **CI renders the page from that JSON only — CI never computes**
  (demo-layer doctrine).
- **MC paths:** **`DRAWDOWN_PATHS_M3` = 10,000 (provisional)** — stable 1%-tail quantiles
  under the nested posterior draw need more than S2's 2,000; verified at the numerics gate.
- **Depends:** the simulator (validation + the piecewise-IC extension for gate 3), the S2
  pipeline (MC machinery + de-smoothed vol), the S1 ledger (optional posterior null; falls
  back to a claimed-Sharpe fan). **numpy only** for the demo; no new runtime dependency.
- **Effort:** **S** (card estimate). Pure simulation on existing substrate; the refactor is
  a lift-and-name, the alarm layer is a few pure functions, the simulator extension is the
  only new generative code.

### 6.7 Adoption & packaging

The alarm is **conversation and governance material**, and the framing is load-bearing
(Sweep E):

- **"Worth a review conversation," never "redeem."** The alarm is an input to a human
  redemption decision, routed to the investment team and (for RED) the leadership
  heat-list — never a mechanical trigger (the card's political kill criterion).
- **Kill the dashboard.** M3 does **not** add a standing always-on alarm screen. It
  surfaces in two places that already have the reader's attention: **inside the S2 tear
  sheet's drawdown panel** (the per-manager view, replacing the preview band with the
  calibrated one) and a **review-cadence roster heat-list** delivered at the decision
  moment. No separate-tab monitor to go stale (Sweep E: the standing dashboard dies at
  25% adoption).
- **The Dietvorst dial.** The maintained Sharpe is an **adjustable control** on the panel
  — a skepticism slider. Drag it down and watch AMBER become RED; the §3.7 fan is the
  honest picture of how much the verdict leans on the null. The output is an input to
  judgement, not a verdict.
- **Receipts, calibrated.** Every alarm shows its number the honest way — *"MDD −18%,
  99.4th percentile of the null under the maintained Sharpe (S1 posterior)"* — and the
  heat-list shows its expected-false-RED count. No adjective, no bare threshold.

**Who sees what, when:** the investment team sees the per-manager panel at monitoring
cadence; leadership sees the roster heat-list, with the false-alarm count, at review
time; any manager-facing version lives only inside the E1 transparency-ladder
relationship, framed as the shared question ("is this drawdown ordinary for a book like
yours?"), never as an accusation.

### 6.8 Go-live requirements (demo-page box, expanded)

- **Data ask:** monthly net returns (tier R) + a **maintained Sharpe hypothesis** — the
  S1 posterior when the ledger is built, the claimed Sharpe (rendered as a fan) otherwise
  — + a risk-free series. Tier E adds vol-target / gross context to sharpen the null; tier
  P adds nothing.
- **Sample required:** **honest at any $T$** because the output is a calibrated band and a
  stated budget, not a point — but **detection power is low at $T \le 60$** (Sweep C), so
  slow alpha death is caught late; the time-to-detection curve (§6.4 gate 3) states
  exactly how late. The band never claims to *prove* an alpha is dead.
- **Build effort:** **S** — pure simulation on existing substrate, plus the small
  piecewise-IC simulator extension for detection validation.
- **Go-live box (demo page):** data ask = monthly returns (R) + a maintained Sharpe;
  sample = any $T$ (detection improves with $T$); effort = S.

## 7. Deeper reading

**Canonical references (read in this order):**

1. **van Hemert, Ganesh, Rohrbach, Roscioni et al. (2020), "Drawdowns,"
   *Journal of Portfolio Management*.** Showed raw drawdown depth is a poor standalone
   signal but a *simulation-calibrated* drawdown threshold is a usable design pattern —
   drawdown as a calibrated rule, not an estimator of skill. The card's direct
   methodological anchor.
2. **Magdon-Ismail & Atiya (2004), "Maximum Drawdown"** (+ Magdon-Ismail, Atiya, Pratap,
   Abu-Mostafa on the range of Brownian motion). The closed form for the expected max
   drawdown of a drifted Brownian path — scaling like $\sigma\sqrt{T}$ in the low-drift
   regime, tamed by positive drift — which makes "same depth, different percentile"
   quantitative.
3. **Westfall & Young (1993), *Resampling-Based Multiple Testing*.** The max-statistic /
   familywise-control logic that §3.3–3.4 apply to a path: control the max-over-months
   statistic directly and the familywise error is exactly $\alpha$.
4. **Gelman, Carlin, Stern, Dunson, Vehtari & Rubin, *Bayesian Data Analysis* (3rd ed.),
   ch. 6.** Posterior-predictive distributions — simulate replicate data by drawing
   parameters from the posterior, not fixing them at a point — the basis for the §3.7
   posterior-informed null.
5. **Bailey & López de Prado (2014/2015) on drawdown and stop-out risk.** Complementary
   framing on when a drawdown is consistent with a return process (secondary read).

**Questions you should be able to answer after reading this page:**

- **State the familywise inflation.** A *pointwise* 99th-percentile drawdown band, scanned
  over $T = 48$ months, false-alarms far more than 1% of the time — explain *why* (a max
  over many looks; under independence $1 - (1-\alpha)^{T_{\text{eff}}}$, with
  $T_{\text{eff}} < T$ because a drawdown persists across autocorrelated months) and *how
  M3 fixes it* (test one path scalar, the MDD, whose α-quantile is α familywise by
  construction — the same test the running-MDD band shows in chart form).
- **Max drawdown as a path statistic.** Explain why the MDD is the max of a
  running-minimum process, not a marginal quantile, and why in the low-drift regime it
  scales like $\sigma\sqrt{T}$ — so two books with the same realized −12% sit at different
  percentiles because they have different $(\mu, \sigma)$ nulls. Work the $\sqrt{T}$
  scaling by hand once.
- **Plug-in vs posterior-predictive null.** Explain why plugging a *point* Sharpe
  understates alarm uncertainty (it ignores that the Sharpe is itself a 36–60-month
  estimate) and why drawing the Sharpe from the S1 posterior gives a wider, honest null —
  the only version that lets the alarm claim "extreme *even granting* our uncertainty
  about skill." Same move S1 makes for alphas, applied to the drawdown null.
- **Why raw drawdown inference fails at $T \le 60$, and what calibration buys.** A drawdown
  is one episode dominated by a handful of months, so "the drawdown is deep ⇒ the alpha
  died" is an inference from n ≈ 1. Simulation calibration does not manufacture power it
  doesn't have — it converts an un-anchored number into a *calibrated* one ("extreme
  relative to a stated null"), a legitimate flag even when a redemption-grade inference is
  not. Precisely the van Hemert et al. (2020) move.
- **The Schmitt trigger.** Explain why a single-threshold comparator chatters on a noisy
  signal, and why two thresholds (arm high, clear low) plus a short persistence run give a
  stable state machine — and why the clear line is the *recovery* of the drawdown, not a
  fixed number of months (the alarm should track condition, not calendar).
- **Explain the roster count to a non-quant.** Why a 1%-per-manager RED still yields a
  one-in-three chance of *some* false RED across 40 healthy managers, why M3 **prints the
  expected-false count** rather than Bonferroni-correcting it away (which would kill
  detection at $T \le 60$), and why that is *not* the prohibited FDR alpha-screen.
- **Explain the wow-demo to a non-quant.** "The same −12% is a shrug for the trend book and
  a five-alarm fire for the credit book — not because 12% means different things, but
  because a smooth 6%-vol book *should almost never* be down 12%, while a 20%-vol trend
  book is down 12% all the time. The alarm reads each manager against their own history,
  not a house rule."
- **State what the alarm does *not* claim.** Not that the alpha is dead, not an
  auto-redeem — a calibrated "this drawdown is inconsistent with the skill we're paying
  for, at this stated confidence, worth a conversation."

---

## Method review (2026-07-07) — APPROVED, implementation-ready

- **Roster multiplicity RULED:** report-the-expected-false-count default CONFIRMED,
  Bonferroni off by default; the stated distinction from the prohibited FDR alpha-screen
  is upheld and is binding page copy.
- **`ALARM_WINDOW` RULED for v1:** full evaluated track (matches the demo and the cleanest
  budget semantics); rolling window deferred to the live build.
- **Sequential-look honesty (gate addition):** evaluated at review cadence on a growing
  window, the alarm is a SEQUENCE of looks — the stated budgets are per-review-window and
  the page/live doc must say so explicitly. The running-MDD band identity holds at the
  window end only; the panel's alarm state reads M_t vs B_t at the current t.
- **MC paths RULED:** `DRAWDOWN_PATHS_M3 = 10_000` provisional (stable 1%-tail quantiles
  under the nested posterior draw need more than S2's 2,000); verified at the numerics
  gate.
- Kill-criterion sensitivity boundary measured at gate 4 as specified.
