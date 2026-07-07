# M3 · Simulation-Calibrated Drawdown Alarms — Method Spec

**Status: Reviewed (the lead reviewer, 2026-07-07) — implementation-ready**
**Date:** 2026-07-07
**Card:** [`docs/ideas/2026-07-05-idea-cards.md`](../2026-07-05-idea-cards.md) § M3
**Demo:** gallery page `m3.html` (roster heat-list + two-manager same-drawdown split; fully synthetic, §5)

## 1. Problem & decision hook

"Down 15% ⇒ put it on review" is the drawdown rule everyone uses and nobody
defends. A −12% drawdown is an ordinary Tuesday for a high-vol trend book and a
1-in-300 event for a smooth credit fund; a flat threshold fires on the healthy
CTA and sleeps through the credit book whose alpha has quietly died. The card's
fix — and the [S2 tear-sheet](s2-tear-sheet-engine.md) §3.6 drawdown panel is
its **M3-lite preview** — is to replace the flat rule with each manager's **own
simulated null**: Monte-Carlo the drawdown distribution under the maintained
skill hypothesis (claimed or S1-posterior Sharpe, de-smoothed vol, fitted
AR(1)) and ask whether the *realized* path is ordinary or extreme against
**that** distribution.

S2 ships the machinery — the MC null-path generator and a pointwise
50/95/99 envelope — but stops one step short of an alarm. **That last step is
where the statistics get subtle, and it is the whole of M3.** S2's
`breaches_p99` flag asks "did the path dip below the *pointwise* 99th percentile
at *any* month?" — a **familywise** question answered with a **pointwise** band,
so its false-alarm rate is nowhere near 1% (§3.1). This is a known open issue,
recorded at the gate as **D-20** ("the pointwise (not familywise) p99
envelope semantics are a gate question for how the page renders breaches").
M3 is the answer: a **familywise-calibrated alarm** with a stated per-manager
and per-roster false-alarm budget, hysteresis so it does not flap, and a null
that carries the S1 posterior's uncertainty rather than a plugged-in point.

- **Decisions improved:** **redeem** — an alarm reads "this drawdown is
  inconsistent with the skill hypothesis we are paying for," a calibrated review
  trigger, not a gut call; **monitor** — a roster heat-list leadership can read
  at a glance, with its false-alarm count stated on the tin.
- **Customer:** investment team (per-manager panel, embedded in the S2 sheet);
  department leadership (roster heat-list).
- **What it is not:** never an auto-redeem rule (a review trigger, full stop —
  §6); never a claim that *this* drawdown *proves* the alpha is gone (raw
  drawdown inference at T ≤ 60 is Noise — one episode dominates — §3.7); and not
  a bare "breached the band" verdict that hides how much the band moves when the
  maintained hypothesis moves (§3.6, §4).

## 2. Data contract per tier

M3 is **returns-native**: it needs the realized path plus a maintained
hypothesis, both of which the R tier already carries. Higher tiers refine the
null, they do not unlock the card.

| Tier | Inputs the live version needs | What the card produces |
| --- | --- | --- |
| **R** (minimum) | Monthly net returns per manager (decimals, `PeriodIndex` freq `M`; S1/S2 §2 conventions); a **maintained Sharpe hypothesis** — the S1 posterior Sharpe *distribution* when the skill ledger is available, the manager's claimed/prospectus Sharpe as a point otherwise; risk-free series. | The **whole alarm**: familywise-calibrated drawdown band, max-drawdown alarm statistic, GREEN/AMBER/RED level with hysteresis, and the roster heat-list entry. Everything in §3 runs returns-only. |
| **E** | R + vol-targeting / gross-exposure context (Open Protocol-aligned) | A **sharper null**: a stated vol target replaces the returns-estimated vol as the band's volatility input, and gross-leverage context bounds the plausible Sharpe fan — narrower, better-motivated bands, not a different alarm. |
| **P** | — | **n/a** (card §"Tier rungs"). Holdings do not refine a drawdown null; M3 stays returns-and-exposure only. |

**Frequency & window.** Monthly returns at each manager's native cadence. The
familywise budget (§3.3) is stated over an explicit **review window** — the
manager's evaluated track length `T` in v1; whether the live default is a
rolling window instead is flagged **`ALARM_WINDOW` (provisional)**.

**Compliance (standing):** synthetic managers in the repo; any real-data rung
uses the manager's own returns and a publicly stated or internally maintained
Sharpe — no employer-internal facts in code, docs, or the committed demo JSON.

## 3. Methodology

M3 sits **on top of** the S2 §3.6 machinery. The MC null-path generator, the
de-smoothed vol from S2 stage 1, and the fitted AR(1) are **imported, not
re-derived** (§5). Everything below is the alarm layer S2 deliberately left as
"card M3."

### 3.1 The pointwise-versus-familywise gap (why S2's band is not an alarm)

S2 draws a **pointwise** envelope: at each month `t`, the 1st percentile of the
null drawdown *at that month*. Read as a chart it is honest — "at this month, in
isolation, how deep is a 99th-percentile drawdown?" Read as an **alarm** —
`np.any(realized < p99)`, S2's `breaches_p99` — it commits the classic
multiple-comparisons error. A monitor scans **all `T` months** and fires if the
path breaches **anywhere**; that is a familywise event, and its probability
under the null is not 1%.

Define, for a chosen per-month tail level `α` (S2 uses `α = 0.01`):

$$
p_{\text{point}} = \Pr\big(D_t < q_\alpha(t)\big)\ \text{for a fixed }t = \alpha,
\qquad
p_{\text{family}} = \Pr\!\Big(\exists\, t \le T:\ D_t < q_\alpha(t)\Big) \gg \alpha,
$$

where $D_t$ is the running drawdown and $q_\alpha(t)$ the pointwise band. Even
under **independence**, $p_{\text{family}} \approx 1-(1-\alpha)^{T_{\text{eff}}}$;
the drawdown path is highly autocorrelated (a drawdown persists across months),
so the *effective* number of independent looks $T_{\text{eff}}$ is smaller than
`T` — but for `α = 0.01` and `T = 48` the familywise breach rate of a pointwise
99th band still lands in the low tens of percent, not 1%. **A pointwise band
read as an event is an alarm that cries wolf.** §4 gate 2 measures exactly this
inflation on the simulator so the correction is shown to be necessary, not
asserted.

### 3.2 The alarm statistic — path max-drawdown, familywise by construction

The clean fix is to alarm on a **path-level scalar**, not a per-month band. The
natural statistic is the **maximum drawdown** over the review window:

$$
\text{MDD} = -\min_{t \le T} D_t = \max_{t \le T}\Big(1 - \tfrac{W_t}{\max_{s\le t} W_s}\Big),
\qquad W_t = \prod_{u\le t}(1+r_u).
$$

One scalar per path ⇒ **no multiplicity**. Simulate `N` null paths (§3.6),
compute each path's MDD, and the null distribution of MDD is exact. The alarm
threshold at familywise level `α` is the upper-`α` quantile of that null MDD
distribution, so an α-level MDD alarm has **exactly** an α familywise
false-alarm rate — by construction, no correction factor to tune.

**Plottable equivalent (for the panel).** The scalar test has a chart form that
preserves the "where on the path" story S2's panel tells. For each null path
compute the **running max-drawdown-to-date** $M_t = -\min_{s\le t} D_s$, and take
the α-quantile of $M_t$ at each `t`. This is a **monotone non-decreasing**
envelope (a running-worst band), and "the realized running-MDD exits the band at
the window end" is *identically* the event "realized MDD exceeds the α-quantile
of null MDD." So the panel plots the realized running-MDD against a familywise
band, and a breach on that chart **is** a calibrated α event — unlike S2's
pointwise band, where a breach is not. This is the direct answer to gate note
D-20's "how the page renders breaches."

**Secondary channel (flagged).** Drawdown *depth* misses a slow bleed that never
gets deep but stays underwater for years. A second path scalar — **time
underwater** (longest run of consecutive months with $D_t < 0$), calibrated the
same way — catches duration where MDD catches depth. Whether v1 ships one
channel or both is flagged **`ALARM_CHANNELS` (provisional)**; the default
recommendation is **depth in v1, duration as the first extension**, to keep the
budget arithmetic (§3.3) single-statistic and legible.

### 3.3 Alarm levels and the per-manager budget

Three levels, each pinned to a familywise quantile of the null MDD, each with a
**stated false-alarm budget** — the probability it fires on a manager whose book
genuinely matches the maintained hypothesis, over one review window:

| Level | Fires when realized MDD exceeds… | Familywise budget (healthy manager) |
| --- | --- | --- |
| **GREEN** | — (MDD inside the 95th-pct null band) | — |
| **AMBER** | the **95th**-percentile null MDD | ≤ 5% per review window |
| **RED** | the **99th**-percentile null MDD | ≤ 1% per review window |

The budgets are **`ALARM_LEVELS` (provisional — AMBER 5% / RED 1%)**. Because
the statistic is a single scalar, "budget" is not a hope — it is the definition
of the quantile, and §4 gate 1 confirms the simulator honors it within MC error.
The alarm's headline is always the calibrated statement — *"MDD −18% sits at the
99.4th percentile of the null under the maintained Sharpe"* — never a bare
"−18%, breached."

### 3.4 The roster budget — the second multiplicity layer

A leadership heat-list across `N` managers has its **own** multiplicity, and it
is the one that quietly discredits monitoring systems. If each healthy manager's
RED fires at 1% familywise, a roster of `N = 40` healthy managers expects
$0.4$ false REDs *per review*, and

$$
\Pr(\text{≥1 false RED on a healthy roster of }40) = 1 - 0.99^{40} \approx 0.33.
$$

A third of clean reviews would surface a red flag. M3's honest move is to
**state the expected false-RED count on the heat-list itself**:
$\mathbb{E}[\text{false RED}] = N \times \text{(per-manager RED rate)}$, printed
beside the list ("2 REDs this review; ~0.4 expected by chance on a healthy
roster of 40"). Leadership reads the flags **with the multiplicity in view** —
the count is a feature of the pitch, exactly like a working PowerGate.

An **optional** roster-familywise tightening (shrink per-manager α so the
roster-level rate hits a budget) is offered but **off by default**: at `N = 40`
a Bonferroni tightening to a 1% roster budget sets per-manager α ≈ 0.00025,
which at T ≤ 60 destroys detection power (§4). The default — report the
expected-false count, do not silently correct — is the right level.

**Not an FDR screen.** This roster budget controls **monitor false-alarms**
(drawdowns), which the do-not-build list permits; it is **not** the prohibited
*FDR luck-screen on alphas at roster scale* (convergence decision §4). M3 runs
no cross-manager alpha-discovery test; it reports one honest count so a
heat-list is not read naively. The distinction is stated on the page.

### 3.5 Hysteresis — arming and clearing (no flapping)

A single-threshold alarm chatters when the drawdown hovers at the line. M3 uses
a **two-threshold (Schmitt-trigger) rule**: the level that *arms* an alarm is
not the level that *clears* it.

- **Arm RED** when realized MDD first exceeds the 99th-pct null band.
- **Hold RED** until the drawdown **recovers** — the current drawdown climbs
  back inside the **95th**-pct band (the AMBER line, not the RED line) **and**
  stays there for **`HYSTERESIS_CLEAR_MONTHS` (provisional — 2)** consecutive
  months. Only then does it step down.
- Symmetric arm/clear for AMBER↔GREEN.

The gap between the arm line (99th) and the clear line (95th) is the hysteresis
band; requiring a short persistence run past the clear line kills single-month
flip-flops around a boundary. The clear rule is stated as **recovery of the
drawdown**, not "N months elapsed," so the alarm tracks the manager's actual
condition, not the calendar.

### 3.6 The null — posterior-informed, not plugged-in

The maintained hypothesis is the single most important input, and S2's M3-lite
plugs it in as a **point** Sharpe. That silently claims we know the true Sharpe
exactly — a bare-point sin the Interval doctrine forbids for the input that most
moves the answer. M3 propagates its uncertainty.

**With the S1 skill ledger (preferred).** The null becomes a **posterior-
predictive** drawdown distribution. For each of `N` MC paths: (i) **draw** a
Sharpe $SR^{(j)}$ from the manager's S1 posterior (the ledger's posterior
alpha/vol, S1 §3.5–3.6); (ii) simulate the AR(1) return path at that Sharpe,
with de-smoothed vol from S2 stage 1 and fitted AR(1) autocorrelation; (iii)
record its MDD. The resulting null MDD distribution is **wider** than any single
plug-in, because it folds in "we are not certain how good this manager is." The
alarm quantiles (§3.3) are read off *this* posterior-predictive distribution.
This is the Interval-compliant alarm: it fires on evidence the drawdown is
extreme **even granting our uncertainty about the paid-for skill.**

**Without S1 (fallback).** Use the claimed Sharpe as a **point**, but never
silently — render the alarm level across a **Sharpe fan** (the card's explicit
requirement: "report alarm level across a Sharpe range"), e.g. claimed Sharpe
×{0.5, 1.0, 1.5}. The panel shows RED-at-claimed alongside AMBER-at-half, so the
reader sees how much the verdict leans on the maintained number. The Dietvorst
dial (§6) makes that fan interactive.

**Second-order inputs.** De-smoothed vol and the AR(1) coefficient also carry
estimation error; v1 plugs them as points because the Sharpe fan dominates the
band width at T ≤ 60. Whether the posterior-predictive draw should also sample
vol/AR(1) (a fuller nested MC) is flagged **`NULL_NESTED_MC` (provisional —
Sharpe-only in v1)**.

### 3.7 What M3 does not do (do-not-build adjacency)

- **No raw drawdown inference.** M3 never claims a drawdown *proves* skill is
  gone. At T ≤ 60 raw DD inference is Noise (Sweep C — one episode dominates the
  path). M3 is legitimate **only as a simulation-calibrated rule**: it says
  "extreme *relative to the stated null*," which is a calibrated flag, not a
  verdict on the alpha.
- **No regime splits, no conditional betas, no persistence test** (convergence
  §4). The null is a stationary AR(1) under one maintained Sharpe; M3 does not
  slice the path into regimes or fit time-varying parameters.
- **No FDR alpha-screen** (§3.4) and **no auto-redeem** (§6). An alarm is a
  review trigger routed to a human, never a mechanical redemption.

## 4. Power & validation plan

Validation runs on the simulator; cells contribute to the X1 atlas
([`x1-tier-power-atlas.md`](x1-tier-power-atlas.md)) as this card's rows. Grid
follows the atlas convention: $T \in \{36, 48, 60\}$ × strategy family ×
smoothing level × true (pre-death) Sharpe, ≥1,000 seeded replications per cell
(per-module RNG streams; Wilson 95% intervals on every rate — X1 §3.3). The
card's two named atlas axes are **time-to-detection** (manager whose true alpha
dies at month `k`) versus **false-alarm rate** (healthy manager).

Acceptance gates:

1. **Familywise false-alarm calibration (the load-bearing gate).** On healthy
   managers (true return process = the maintained hypothesis), the measured RED
   familywise rate is **≤ 1% within MC error**, AMBER **≤ 5%** — the budget M3
   promises and the pointwise band cannot keep. This is the gate that justifies
   the whole card.
2. **Pointwise-inflation demonstration.** Measure S2's *pointwise*-band
   familywise breach rate on the same healthy managers and report it beside the
   corrected rate. Expected: low tens of percent versus the calibrated 1%. This
   is the evidence D-20 asks for — the correction is shown, not claimed.
3. **Detection / time-to-detection.** Inject alpha death at month `k` (IC steps
   to zero at `k`; **simulator extension required — see below**) and report the
   detection rate within a review horizon and the median months-to-first-RED, as
   a curve against pre-death Sharpe and `T`. Reported as an operating
   characteristic traded against gate 1, never a single threshold.
4. **Maintained-hypothesis sensitivity.** Sweep the plugged Sharpe across the
   §3.6 fan and report how the RED rate moves; with S1, report **coverage of the
   posterior-predictive band** (does the realized MDD fall inside the stated
   quantile at the nominal frequency, within ±5 pp). The card's stated
   statistical risk — "sensitivity to the maintained-hypothesis inputs" — is
   measured here, not hand-waved.
5. **Roster-budget check.** On a healthy synthetic roster of size `N`, the
   measured expected false-RED count matches $N \times$ (per-manager RED rate)
   within MC error, validating the number the heat-list prints (§3.4).

**Simulator dependency (honest).** The current
`simulator/manager.py` has a constant `information_coefficient` with age-decay
but **no mid-track death event**; gate 3 needs a piecewise-IC extension (IC → 0
at month `k`). This is a **named validation prerequisite**, small, and flagged
as such — not assumed present.

**Kill criterion.** If the familywise RED rate cannot be held within budget
**across the maintained-hypothesis uncertainty range** — i.e., the band is so
sensitive to the Sharpe input that no honest single budget exists — M3 **ships
as a descriptive band only**: the panel states the realized MDD's percentile
under the stated null and the S2-style envelope, with **no GREEN/AMBER/RED
level and no roster heat-list**, recorded in writing per converge-or-cut. A
miscalibrated alarm sold as a 1% event is worse than an honest percentile.

## 5. Implementation architecture

The commitment is **reuse S2's MC machinery, add only the alarm layer.**

- **Refactor (small) in
  `src/quant_allocator/flagships/tearsheet/pipeline.py`:** extract the null-path
  simulation currently inside `drawdown_band` into a reusable primitive
  `simulate_null_drawdowns(hypothesis, t, n_paths, seed) -> troughs` (the
  `n_paths × T` matrix of running drawdowns). `drawdown_band` keeps its exact
  behavior by calling it and taking pointwise percentiles; M3 calls it and takes
  path scalars. **No estimator is duplicated.**
- **New module `src/quant_allocator/flagships/alarms/pipeline.py`:** pure
  functions over the null troughs —
  `max_drawdown_null(troughs) -> np.ndarray` (per-path MDD),
  `familywise_band(troughs, levels) -> AlarmBand` (running-MDD quantile
  envelope, §3.2), and
  `alarm_state(returns, hypothesis, *, prev_state, roster_size) -> AlarmVerdict`
  carrying level, the realized MDD percentile, the hysteresis state, and the
  §3.4 expected-false-RED count. No rendering, no I/O (S2 §5 convention).
- **Posterior-informed null:** `alarm_state` accepts `hypothesis` as **either** a
  `DrawdownHypothesis` (point, fallback) **or** a `PosteriorHypothesis` (Sharpe
  draws from the S1 ledger); the second path does the §3.6 posterior-predictive
  draw. The S1 posterior is consumed via the existing `skill_ledger`
  `empirical.py` closed-form output — **import, do not re-fit** (no PyMC in M3).
- **Demo — `src/quant_allocator/demo_data/m3_alarms.py`** (imports the pipeline;
  same code path as any live build, only the input data is synthetic). The
  **wow-demo**: two synthetic managers with the **same realized −12% drawdown** —
  a high-vol trend book (GREEN: −12% is inside its 95th band) and a smooth credit
  book (RED: −12% sits at the 99.7th percentile of *its* null). Plus a small
  **roster heat-list** with the expected-false-RED count printed. Emits committed
  JSON to `site/data/m3_alarms.json` via `_emit.write_json`; **CI renders the
  page from that JSON only — CI never computes** (demo-layer doctrine).
- **Depends:** the simulator (validation + the piecewise-IC extension for gate
  3), the S2 pipeline (MC machinery + de-smoothed vol), the S1 ledger (optional
  posterior null; falls back to a claimed-Sharpe fan). **numpy only** for the
  demo; no new runtime dependency.
- **Effort:** **S** (card estimate). Pure simulation on existing substrate; the
  refactor is a lift-and-name, the alarm layer is a few pure functions, the
  simulator extension is the only new generative code.

## 6. Adoption & packaging

The alarm is **conversation and governance material**, and the framing is
load-bearing (Sweep E):

- **"Worth a review conversation," never "redeem."** The alarm is an input to a
  human redemption decision, routed to the investment team and (for RED) the
  leadership heat-list — **never a mechanical trigger** (the card's political
  kill criterion). Goodhart: an alarm published as a hard redemption rule gets
  gamed — managers manage the book to the band — so it ships as a flag on a
  review, not an automatic action.
- **Kill the dashboard.** M3 does **not** add a standing always-on alarm screen.
  It surfaces in two places that already have the reader's attention: **inside
  the S2 tear sheet's drawdown panel** (the per-manager view, replacing S2's
  M3-lite band with the calibrated one) and a **review-cadence roster heat-list**
  delivered at the decision moment. No separate-tab monitor to go stale
  (Sweep E: the standing dashboard dies at 25% adoption).
- **The Dietvorst dial.** The maintained Sharpe is an **adjustable control** on
  the panel — a skepticism slider. Drag it down and watch AMBER become RED; the
  §3.6 fan is the honest picture of how much the verdict leans on the null. The
  output is an input to judgment, not a verdict.
- **Receipts, calibrated.** Every alarm shows its number the honest way — *"MDD
  −18%, 99.4th percentile of the null under the maintained Sharpe (S1
  posterior)"* — and the heat-list shows its expected-false-RED count. No
  adjective, no bare threshold.

**Who sees what, when:** the investment team sees the per-manager panel at
monitoring cadence; leadership sees the roster heat-list, with the false-alarm
count, at review time; any manager-facing version lives only inside the E1
transparency-ladder relationship, framed as the shared question ("is this
drawdown ordinary for a book like yours?"), never as an accusation.

## 7. Go-live requirements

The demo page's "what this needs to go live" box, expanded:

- **Data ask:** monthly net returns (tier R) + a **maintained Sharpe
  hypothesis** — the S1 posterior when the ledger is built, the claimed Sharpe
  (rendered as a fan) otherwise — + a risk-free series. Tier E adds vol-target /
  gross context to sharpen the null; tier P adds nothing.
- **Sample required:** **honest at any `T`** because the output is a calibrated
  band and a stated budget, not a point — but **detection power is low at
  T ≤ 60** (Sweep C), so slow alpha death is caught late; the time-to-detection
  curve (§4 gate 3) states exactly how late. The band never claims to *prove* an
  alpha is dead.
- **Build effort:** **S** — pure simulation on existing substrate, plus the small
  piecewise-IC simulator extension for detection validation.
- **Kill criteria:** **statistical** — band too sensitive to the maintained
  hypothesis to state a single budget ⇒ downgrade to a descriptive percentile,
  no alarm level (§4). **Political** — an alarm is a review trigger, never an
  auto-redeem; if a consumer wires it to automatic action the card is pulled.
- **Go-live box (demo page):** data ask = monthly returns (R) + a maintained
  Sharpe; sample = any `T` (detection improves with `T`); effort = S.

## 8. Learning notes

*The spec program doubles as a curriculum; this is what to be able to defend
unaided.*

- **Familywise vs pointwise error, applied to a scanning monitor.** A band is
  drawn per-month at level α; a monitor that fires on a breach *anywhere* over
  `T` months is asking a max-statistic question, and under the null the
  probability of *some* breach is $\approx 1-(1-\alpha)^{T_{\text{eff}}} \gg
  \alpha$ — with $T_{\text{eff}} < T$ because a drawdown persists across
  autocorrelated months. The disciplined fix is to test a **single path scalar**
  (max drawdown) whose null distribution is exact, so an α-level test has exactly
  α familywise error with no correction to tune. Own why the running-MDD band
  (§3.2) is the *same* test in chart form.
- **Max drawdown as a path statistic.** The MDD of a return path is the max of a
  running-minimum process, not a marginal quantile. For a Brownian motion with
  drift `μ` and vol `σ` over horizon `T`, the **expected** max drawdown has a
  known closed form (Magdon-Ismail & Atiya, 2004) that scales like $\sigma\sqrt{T}$
  in the low-drift regime and is *tamed* by positive drift — which is exactly why
  two books with the same realized −12% sit at different percentiles: same depth,
  different (μ, σ) null. Work the low-drift $\sqrt{T}$ scaling by hand once.
- **Plug-in vs posterior-predictive null.** Plugging a point Sharpe into the null
  understates alarm uncertainty because it ignores that the Sharpe itself is a
  36–60-month estimate. Drawing the Sharpe from the S1 posterior and simulating
  gives a **posterior-predictive** MDD distribution — wider, honest, and the only
  version that lets the alarm claim "extreme *even granting* our uncertainty about
  skill." This is the same move S1 makes for alphas, applied to the drawdown
  null. (Gelman et al., *BDA3*, ch. 6 — posterior-predictive checking.)
- **Why raw drawdown inference fails at T ≤ 60, and what calibration buys.** A
  drawdown is one episode; its depth is dominated by a handful of months, so "the
  drawdown is deep ⇒ the alpha died" is an inference from n≈1. Simulation
  calibration does not manufacture power it doesn't have — it converts an
  un-anchored number into a *calibrated* one ("extreme relative to a stated
  null"), which is a legitimate flag even when a redemption-grade inference is
  not. This is precisely the van Hemert et al. (2020) move: use drawdown as a
  *calibrated rule*, not as an estimator of skill.
- **Hysteresis / the Schmitt trigger.** Borrowed from control theory: a
  single-threshold comparator chatters on a noisy signal crossing the line; two
  thresholds (arm high, clear low) plus a short persistence run give a stable
  state machine. Own why the clear line is the *recovery* of the drawdown, not a
  fixed number of months — the alarm should track condition, not calendar.
- **Canonical references (read in this order):**
  1. **van Hemert, Ganesh, Rohrbach, Roscioni et al. (2020), "Drawdowns,"
     *Journal of Portfolio Management*** — simulation-calibrated drawdown
     thresholds as a design pattern; the card's direct methodological anchor.
  2. **Magdon-Ismail & Atiya (2004), "Maximum Drawdown"** (+ Magdon-Ismail,
     Atiya, Pratap, Abu-Mostafa on the range of Brownian motion) — the closed
     form and $\sqrt{T}$ scaling of expected max drawdown that makes "same depth,
     different percentile" quantitative.
  3. **Westfall & Young (1993), *Resampling-Based Multiple Testing*** — the
     max-statistic / familywise-control logic that §3.1–3.2 apply to a path.
  4. **Gelman, Carlin, Stern, Dunson, Vehtari & Rubin, *Bayesian Data Analysis*
     (3rd ed.), ch. 6** — posterior-predictive distributions, the basis for the
     §3.6 posterior-informed null.
  5. **Bailey & López de Prado (2014/2015) on drawdown and stop-out risk** —
     complementary framing on when a drawdown is consistent with a return
     process (secondary read).

**Defend unaided:**

- State the familywise inflation: a **pointwise** 99th-percentile drawdown band,
  scanned over `T = 48` months, false-alarms far more than 1% of the time —
  explain *why* (max over many looks) and *how M3 fixes it* (test one path
  scalar, MDD, whose α-quantile is α familywise by construction).
- Explain the wow-demo to a non-quant: "the same −12% is a shrug for the trend
  book and a five-alarm fire for the credit book — not because 12% means
  different things, but because a smooth 6%-vol book *should almost never* be
  down 12%, and a 20%-vol trend book is down 12% all the time. The alarm reads
  each manager against their own history, not a house rule."
- Explain the roster count: why a 1%-per-manager RED still yields a one-in-three
  chance of *some* false RED across 40 healthy managers, and why M3 **prints the
  expected-false count** rather than Bonferroni-correcting it away (which would
  kill detection at T ≤ 60) — and why that is *not* the prohibited FDR alpha
  screen.
- State what the alarm does **not** claim: not that the alpha is dead, not an
  auto-redeem — a calibrated "this drawdown is inconsistent with the skill we're
  paying for, at this stated confidence, worth a conversation."

---

## gate review (2026-07-07) — APPROVED, implementation-ready

- **Roster multiplicity RULED:** report-the-expected-false-count default
  CONFIRMED, Bonferroni off by default; the stated distinction from the
  prohibited FDR alpha-screen is upheld and is binding page copy.
- **`ALARM_WINDOW` RULED for v1:** full evaluated track (matches the demo and
  the cleanest budget semantics); rolling window deferred to the live build.
- **Sequential-look honesty (gate addition):** evaluated at review cadence on a
  growing window, the alarm is a SEQUENCE of looks — the stated budgets are
  per-review-window and the page/live doc must say so explicitly. The running-
  MDD band identity holds at the window end only; the panel's alarm state reads
  M_t vs B_t at the current t.
- **MC paths RULED:** `DRAWDOWN_PATHS_M3 = 10_000` provisional (stable 1%-tail
  quantiles under the nested posterior draw need more than S2's 2,000);
  verified at the numerics gate.
- Kill-criterion sensitivity boundary measured at gate 4 as specified.
