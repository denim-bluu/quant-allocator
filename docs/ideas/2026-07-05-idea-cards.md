# Idea Portfolio — 20 Cards

**Date:** 2026-07-05
**Status:** Proposed at convergence; selection and 90-day plan in
[`2026-07-05-convergence-decision.md`](2026-07-05-convergence-decision.md)
**Inputs:** Sweeps A–E (`docs/briefs/`), war-game spec §8
(`docs/superpowers/specs/2026-07-05-quant-allocator-wargame-design.md`),
simulator substrate (`src/quant_allocator/`).

## How to read a card

- **Tiers:** R = monthly returns only · E = exposure/risk-report summaries ·
  P = position/trade-level transparency. Every card states what each rung buys.
- **Power verdict:** grounded in Sweep C's robust/shrink/noise taxonomy. Most
  cards carry a *prior* verdict; the Tier & Power Atlas (X1) replaces priors
  with measured curves from the simulator. A card is provisional until its
  atlas cell runs.
- **Scores (1–5):** seat = current-seat impact · senior = senior-role
  (PM-engagement) case · public = public-portfolio value · methods = methods
  mastery. 5 = decisive/differentiating, 3 = solid, 1 = marginal.
- **Effort:** S ≈ 1–3 build sessions, M ≈ 4–8, L ≈ 9+ (one session = a
  focused evening/weekend block with subagent-driven execution).
- **Compliance (all cards):** public or synthetic data only; the repo is
  treated as public; no employer-internal facts or manager names, ever.

**Lanes:** S = skill & inference · M = monitoring & early warning ·
P = portfolio construction & governance · E = engagement & knowledge ·
X = meta / infrastructure.

---

## Lane S — Skill measurement & inference

### S1 · Hierarchical Bayesian alpha engine ("the skill ledger") — FLAGSHIP

- **Problem & decision:** Raw per-manager alphas at 36–60 monthly obs are
  noise (IR 0.5 → t ≈ 1.0 at T=60); rankings on them are luck-hiring.
  Replace point alphas with posterior alphas that pool the cross-section.
  Improves **select** (rank on posterior, not noise) and **size** (posterior
  uncertainty feeds allocation directly).
- **Customer:** Investment team (primary); department leadership (roster view).
- **Tier rungs:** R — full model runs on returns alone, for every manager.
  E — exposure summaries pin betas, shrinking alpha-variance (Pástor–Stambaugh
  logic: better-identified betas sharpen alpha). P — holdings-based evidence
  (breadth, IC where measurable) tightens the skill prior; formal fusion is
  card P2.
- **Method (Sweep C grounding):** Random-effects model per strategy s:
  α_i ~ N(μ_s, τ_s²), strategy-appropriate factor sets (FF5+MOM for equity
  L/S; Fung–Hsieh 7 for macro/trend; credit set on GLM-unsmoothed returns).
  Informative hyperpriors on τ from published HF panels (Kosowski–Naik–Teo;
  Harvey–Liu) because at n = tens the hyperparameters are themselves noisy —
  report prior-sensitivity as a first-class output. PyMC/NUTS. Outputs per
  manager: posterior mean α, 90% credible interval, P(α>0), shrinkage weight.
  Sweep C's verdict: hierarchical shrinkage is *the method of choice* at this N.
- **Power verdict:** Prior (Sweep C): Robust — designed for this regime.
  Simulator test: calibration/coverage against known true alphas (do 90%
  intervals cover 90%?), rank-recovery vs. OLS baseline. Atlas cells: T ∈
  {36,48,60} × roster size {10,20,40} × dispersion.
- **MVP & effort:** M. Model + coverage tests on a 20-manager synthetic
  roster + one public-data demo (factor-index proxies); skill-ledger table
  and per-manager posterior strip rendered as an Interval pack. Thin decision
  layer: advisory weight *bands* from posterior mean/sd buckets — explicitly
  not an optimizer (that is card P1).
- **Wow-demo:** Side-by-side: OLS ranking vs. posterior ranking on a
  simulated roster where true skill is known — the OLS list is visibly
  reshuffled by luck, the posterior list isn't. Then the same engine on real
  public fund-index data with honest intervals.
- **Scores:** seat 5 · senior 4 · public 4 · methods 5
- **Risks & kill criteria:** Statistical — hyperprior sensitivity too large
  (posterior rankings flip across reasonable τ priors) ⇒ demote to
  interval-only reporting (S2) and document. Political — "your alpha is
  shrunk" needs help-not-audit framing (Sweep E). Vendor — none productizes
  this (Sweep D white space).
- **JD mapping:** Current: manager selection/monitoring, quantitative tooling.
  Vision: factor research, P&L-driver judgment, portfolio-construction input.
- **Sequencing:** Substrate ready (simulator + FF5 adapter). Feeds S2 (posterior
  strip on tear sheets), P1 (allocation), P2 (fusion). Consumes X1 thresholds.

### S2 · Uncertainty-honest tear-sheet engine — QUICK WIN

- **Problem & decision:** Standard manager tear sheets report point Sharpe/IR
  with no intervals, on smoothed NAVs, against generic benchmarks — the exact
  practice Sweeps A and C document as misleading at small N. Build the
  always-on per-manager panel that is honest by construction. Improves
  **monitor** (every manager, every month) and **select** (screening with
  stated uncertainty).
- **Customer:** Investment team; the pack doubles as meeting-prep material.
- **Tier rungs:** R — the full sheet runs returns-only: de-smoothed Sharpe with
  CI, factor regression with interval-reported alpha, alt-beta gate, drawdown
  panel. E — adds *measured* exposures next to regression-inferred ones (drift
  panel-lite). P — adds holdings descriptors that are measurement, not
  estimation: active share, concentration, top-position weight.
- **Method (Sweep C grounding):** Pipeline: Getmansky–Lo–Makarov unsmoothing
  (MA(2) default, θ estimated) → strategy-appropriate factor set → Lo /
  Ledoit–Wolf bootstrap CIs on Sharpe and alpha → MPPM (ρ=3) alongside Sharpe
  (manipulation check) → simulation-calibrated drawdown band (M3-lite).
  Fung–Hsieh alpha CI crossing zero ⇒ "provisionally alternative beta" chip —
  the fees-for-beta conversation from Sweep A. Every statistic renders as an
  IntervalStat with a VerdictChip (robust/shrink/noise per Sweep C's table);
  nothing renders as a bare point.
- **Power verdict:** Prior (Sweep C): Shrink — every component is a
  shrink-verdict method *composed honestly* (intervals, not points). Atlas
  cells: false-alarm and detection rates of the alt-beta gate and DD band at
  T ∈ {36,48,60}.
- **MVP & effort:** S–M. Returns-only rung on a synthetic 8-manager roster +
  real FF5 factors; first Interval pack (this births `design-tokens.css`).
- **Wow-demo:** One printed A4 pack: a manager whose reported Sharpe is 1.4
  but whose de-smoothed, interval-reported Sharpe is [0.2, 1.6] with a
  "provisionally alternative beta" chip — the whole campaign thesis on one page.
- **Scores:** seat 5 · senior 3 · public 4 · methods 4
- **Risks & kill criteria:** Statistical — low (measurement + established
  estimators). Political — chips must read as calibration, not accusation
  (Sweep E copy doctrine). Vendor — tear sheets exist everywhere; the
  differentiation is the uncertainty discipline, so if intervals get stripped
  by consumers the card has failed its purpose (watch for this in adoption).
- **JD mapping:** Current: manager monitoring, institutionalizing standards.
  Vision: communication craft, factor literacy.
- **Sequencing:** Substrate ready. First consumer of the Interval design
  system. S1 posterior strip and M3 alarms slot in later.

### S3 · Sizing & alpha-decay lab

- **Problem & decision:** For position-transparent managers, is the edge in
  picking, sizing, or holding? Platforms treat sizing curves and decay curves
  as core PM-engagement analytics (Sweep B catalog #4–5); allocators rarely
  compute them. Improves **size** (of the mandate: a manager with real picks
  but inverted sizing is a coach-or-resize case, not a redeem) and **select**
  (underwriting high-turnover quant books where power clears).
- **Customer:** Manager-facing engagement (transparent managers); investment
  team for underwriting.
- **Tier rungs:** P — native habitat: trades and positions. E — honestly
  *nothing* credible (Sweep C); turnover-based staleness hints only, labeled
  descriptive. R — the research question of card S6, not this card.
- **Method (Sweep C grounding):** Event-study on trades: entry-aligned,
  factor-adjusted forward-alpha curves with cluster-bootstrap SEs (by date and
  name — overlapping positions and common factor moves slash effective N).
  Sizing: realized alpha per unit gross by position-size decile vs.
  equal-weight counterfactual (the Alpha Theory optimal-vs-actual gap,
  computed properly). Hit rate/slugging reported only above power thresholds.
- **Power verdict:** Prior (Sweep C): Shrink, hard-gated — hit-rate
  discrimination (55% vs 50%) needs ~780 independent trades at 80% power;
  a 30-name book never clears in 5 years; high-turnover books clear in 1–2.
  Below threshold the card renders "insufficient N," never a number.
  Atlas cells: trades/year × years × breadth grid for each statistic.
- **MVP & effort:** M. Simulator already emits positions/trades with known
  IC, half-life, and sizing discipline — compute the full lab on synthetic
  managers and verify it recovers the dials.
- **Wow-demo:** Two simulated managers with identical returns, different
  ground truth (picker vs. sizer); the lab tells them apart — and the
  PowerGate shows exactly when it stops being able to.
- **Scores:** seat 3 · senior 5 · public 4 · methods 4
- **Risks & kill criteria:** Statistical — decade-scale data needs for
  concentrated books (mitigated by gates). Political — sizing feedback to an
  external manager must be adjustable-output framed (Dietvorst). Vendor —
  Essentia/Alpha Theory sell adjacent products to managers; ours is the
  allocator-side, power-gated version (Sweep D: build lane).
- **JD mapping:** Current: manager monitoring depth. Vision: the literal
  BAM-catalog analytics (sizing curves, alpha decay) — strongest single
  senior-role evidence.
- **Sequencing:** Substrate ready for synthetic; consumes X1 gates. Real-data
  rung needs a transparent-manager proxy (13F quarterly is too coarse for
  decay — flag honestly).

### S4 · Sell-discipline diagnostic ("where the edge leaks")

- **Problem & decision:** The best-documented PM deficit: buys add value,
  sells underperform even a random-sell counterfactual (Akepanidtaworn–Di
  Mascio–Imas–Schmidt 2023). Concentrated, visible, and not an attack on the
  manager's thesis work — the ideal engagement opener (Sweep E). Improves
  **engage** (highest-value, least-threatening feedback) and **monitor**
  (a decision-quality trend that leads returns).
- **Customer:** Manager-facing engagement (primary); investment team watchlist.
- **Tier rungs:** P/transaction — native: needs exit dates. E — exit-behavior
  hints from gross/turnover dynamics, labeled low-confidence. R — none; do
  not fake it.
- **Method (Sweep C/E grounding):** For each realized exit, forward return of
  the sold name vs. a random-sell counterfactual drawn from the same book at
  the same date (SFBS design), factor-adjusted, cluster-bootstrapped.
  Split entry-timing vs. exit-timing value. Report as "alpha retained
  through exit" curves with intervals; trend it by quarter. Deterioration
  plus refusal to engage = soft redemption input, never a mechanical rule
  (Goodhart; Sweep E).
- **Power verdict:** Prior (Sweep C): Shrink — power scales with round-trips;
  same gating machinery as S3. Atlas cells: exits/year × years grid;
  detectable exit-deficit size vs. sample.
- **MVP & effort:** M. Simulator managers with short alpha half-life +
  sluggish rebalancing exhibit hold-too-long leakage organically — test
  whether the diagnostic recovers it; add an explicit exit-lag dial if not.
- **Wow-demo:** "Your alpha accrues for 60 trading days and you give a third
  back after day 90" — one chart, adjustable threshold slider, help-framed
  copy. The Essentia-style artifact, built honestly.
- **Scores:** seat 3 · senior 5 · public 4 · methods 4
- **Risks & kill criteria:** Statistical — few exits ⇒ gated silence.
  Political — the single most sensitive analytic in the portfolio; ships only
  inside the E1 ladder relationship, adjustable-output only. Kill the
  manager-facing version (keep internal) if any pilot conversation reads as
  audit.
- **JD mapping:** Current: manager engagement support. Vision: PM coaching on
  P&L drivers — the purest PM-engagement artifact in the portfolio.
- **Sequencing:** After S3 (shares the event-study machinery). Possible
  simulator dial addition (exit-lag).

### S5 · Short-book quality score

- **Problem & decision:** Is short alpha real, or are shorts just expensive
  beta hedges? Changes how the mandate is underwritten and sized (a
  hedge-short book is a beta-timing bet and should be priced as one).
  Improves **size** and **redeem**.
- **Customer:** Investment team (underwriting); engagement for transparent L/S.
- **Tier rungs:** P — classify each short: alpha-short (idiosyncratic
  co-movement, name-specific entry/exit) vs. hedge-short (tracks long-book
  factor complement). E — short-side factor split only. R — long/short
  attribution from returns is underdetermined; descriptive gross/net only.
- **Method (Sweep C/B grounding):** Position-level decomposition of short
  P&L into factor-hedge vs. idiosyncratic components; borrow-crowding overlay
  from FINRA short interest (free, bi-monthly) as squeeze-stress context;
  days-to-cover on top shorts. Event-study alpha on shorts where trade count
  clears gates (S3 machinery).
- **Power verdict:** Prior (Sweep C): Shrink for short-alpha estimation
  (trade-count-gated); Robust for the hedge-vs-alpha *classification*
  (measurement). Atlas cells: share with S3.
- **MVP & effort:** M–L. Needs simulator short-book realism beyond v1
  (borrow-cost/squeeze behavior absent) and the FINRA adapter — both deferred
  substrate.
- **Wow-demo:** A manager's "short alpha" panel: 80% of short P&L is
  factor hedge; the residual, gated, is indistinguishable from zero — with
  the fee implication spelled out.
- **Scores:** seat 3 · senior 4 · public 3 · methods 3
- **Risks & kill criteria:** Data — borrow-cost realism is hard to fake
  credibly; if the synthetic version can't be made honest, defer the card
  rather than demo a toy. Vendor — none allocator-side (platform-internal
  analytics don't transplant).
- **JD mapping:** Current: manager monitoring. Vision: short-book quality is
  an explicit platform review item (Sweep B catalog #10).
- **Sequencing:** After S3; needs FINRA adapter + simulator short-book work.

### S6 · Returns-only sizing/decay signatures — RESEARCH BET

- **Problem & decision:** Sizing curves and decay curves are position-tier
  analytics, but most managers are returns-only. Sweep B flags "inferring
  sizing discipline or alpha-decay signatures from monthly returns" as
  high-value, low-confidence white space. If even a weak returns-only proxy
  exists, it covers the *many*, not the few. Improves **monitor** and
  **select** — if it works.
- **Customer:** Investment team (returns-only majority of the roster).
- **Tier rungs:** R — the whole point. E/P — used only as validation labels
  (does the proxy agree with the measured truth where truth is visible?).
- **Method (Sweep C grounding):** Pre-registered protocol on the simulator:
  generate managers differing *only* in sizing discipline or alpha half-life
  (dials exist), hold everything else at realistic nuisance levels; test
  candidate statistics — autocorrelation structure of the alpha proxy,
  vol-of-vol, return asymmetry, drawdown-shape features, rolling-IR
  stability — for discrimination (target: AUC > 0.65 at T=60 across the
  nuisance grid). Report negative results as first-class findings.
- **Power verdict:** Unknown — that is the card. Sweep C gives no prior;
  the closest analogue (returns-based style drift) verdicts Noise, so the
  burden of proof is on the card. Atlas cells: the protocol *is* an atlas
  extension.
- **MVP & effort:** M–L (research risk, not build risk). The simulator's
  decorrelated per-module RNG streams make the falsification clean.
- **Wow-demo:** Either outcome demos: "we found a returns-only sizing tell
  (AUC 0.71)" or "we tested 6 candidate tells; none survive — do not trust
  anyone selling this" (the honest-negative is itself portfolio-grade).
- **Scores:** seat 3 · senior 4 · public 4 · methods 5
- **Risks & kill criteria:** Statistical — likely partial or null result;
  kill after the pre-registered grid completes, publish the answer either
  way. Do not ship any proxy that fails the grid.
- **JD mapping:** Current: research capability. Vision: original factor/skill
  research — a platform would notice this result either way.
- **Sequencing:** After X1 vol 1 (reuses its harness). Zero external data.

---

## Lane M — Monitoring & early warning

### M1 · Exposure hygiene & drift monitor

- **Problem & decision:** From risk-report summaries alone: does the manager
  respect their own stated gross/net/beta bands, and is the return stream
  increasingly "accidental factor" vs. intended alpha? Sweep B calls this the
  single most transplantable platform analytic at the E tier. Improves
  **monitor** and **engage** (the quarterly-review centerpiece: specific,
  measured drift to discuss).
- **Customer:** Investment team (quarterly cycle); engagement conversations.
- **Tier rungs:** E — native: measured exposures, band adherence, drift as
  direct measurement (Robust per Sweep C). P — sharpens to position-level
  attribution of the drift. R — RBSA fallback, rendered descriptive-only with
  a noise chip (returns-based drift detection at this N verdicts Noise).
- **Method (Sweep C grounding):** No estimation where measurement exists:
  stated bands (from mandate/letters) vs. realized exposure paths; factor
  share of predicted P&L (x'f vs. residual); drift = exposure change
  point-in-time, not rolling-beta inference. Alarm thresholds set on
  simulator-emitted exposure summaries.
- **Power verdict:** Prior (Sweep C): Robust (T2/T3 measurement); the
  returns-based rung is Noise and is labeled so. Atlas cells: false-alarm
  rate of band-breach flags under honest wander vs. true drift.
- **MVP & effort:** S–M. Simulator emits exposure summaries with known true
  drift; the tear-sheet (S2) hosts the panel.
- **Wow-demo:** A manager whose letter says "beta-neutral stock picking"
  while the measured net-beta path walks from 0.1 to 0.45 — TierBadge showing
  this is measured (E), not inferred.
- **Scores:** seat 4 · senior 4 · public 3 · methods 3
- **Risks & kill criteria:** Data — real-world E-tier feeds vary in quality;
  Open Protocol alignment (Sweep A) is the standardization ask (via E1).
  Political — band-breach copy must invite explanation, not accuse.
- **JD mapping:** Current: manager monitoring. Vision: factor-hygiene review
  is Sweep B catalog #2 verbatim.
- **Sequencing:** After S2 (hosts it). Simulator sufficient.

### M2 · Hidden-convexity / short-vol screen

- **Problem & decision:** A smooth Sharpe can hide sold optionality; linear
  factor reports miss payoff shape. Sweep D flags non-linearity detection
  from return series as white space, high-value for macro/credit books.
  Improves **monitor** and **redeem** (left-tail exposure surfaced before it
  detonates).
- **Customer:** Investment team; risk-adjacent leadership reporting.
- **Tier rungs:** R — native: the screen exists precisely for returns-only
  books. E — confirms with reported optionality/convexity positions if
  present. P — direct payoff inspection.
- **Method (Sweep C grounding):** Composite of (i) Fung–Hsieh straddle-factor
  loadings (persistently negative = short-vol posture), (ii) return-shape
  stats: coskewness with market, drawdown-to-vol asymmetry vs.
  normal-calibrated bands, (iii) GLM smoothing θ + Sharpe-vs-MPPM gap
  (smoothness + manipulation-proof gap = classic short-vol tell). Each
  component interval-reported; composite is a flag for *investigation*, not a
  verdict.
- **Power verdict:** Prior (Sweep C): Shrink — straddle betas are noisy at
  T≤60; the composite must be simulation-calibrated. Atlas cells: inject
  short-vol payoff into the simulator (new dial), measure detection vs.
  false-alarm on honest-but-smooth managers.
- **MVP & effort:** M. Requires a small simulator extension (short-vol /
  written-put overlay dial) — the crude credit generator partially covers.
- **Wow-demo:** Two simulated managers, identical Sharpe 1.1; the screen
  lights one up as short-vol — then the stress month arrives and the flagged
  one loses 4× more. Receipts included.
- **Scores:** seat 4 · senior 3 · public 4 · methods 4
- **Risks & kill criteria:** Statistical — if calibrated false-alarm rate
  exceeds ~1-in-5 on honest managers at T=48, the screen is noise theater;
  kill or lengthen the window. Data — none needed beyond substrate.
- **JD mapping:** Current: monitoring across all-HF universe (macro/credit
  literacy). Vision: tail-risk literacy in portfolio construction.
- **Sequencing:** Simulator dial first; then screen; hosts in S2 sheets.

### M3 · Simulation-calibrated drawdown alarms

- **Problem & decision:** Ad-hoc rules ("down 15% = review") ignore that DD
  depth depends on vol, autocorrelation, and horizon; they fire on healthy
  managers and sleep through broken ones. Improves **redeem** (alarm =
  "this DD is inconsistent with the skill hypothesis we're paying for") and
  **monitor**.
- **Customer:** Investment team; a roster heat-list for leadership.
- **Tier rungs:** R — native (needs only returns + a maintained Sharpe
  hypothesis). E — vol-targeting/gross context refines the null. P — n/a.
- **Method (Sweep C grounding):** van Hemert et al. (2020): Monte Carlo the
  DD distribution under the maintained hypothesis (claimed/posterior Sharpe,
  de-smoothed vol, estimated autocorrelation); alarm when realized DD crosses
  a chosen quantile (e.g., 99th) of that null; hysteresis to prevent flapping.
  Uses S1 posterior Sharpe when available, claimed Sharpe otherwise.
- **Power verdict:** Prior (Sweep C): Shrink — legitimate *as a
  simulation-calibrated rule*; raw DD inference at T≤60 is Noise (one episode
  dominates). Atlas cells: time-to-detection for a manager whose true alpha
  dies at month k vs. false-alarm rate on healthy managers.
- **MVP & effort:** S. Pure simulation on existing substrate.
- **Wow-demo:** The alarm panel: same −12% drawdown is a non-event for the
  high-vol CTA and a 99.7th-percentile breach for the smooth credit book.
- **Scores:** seat 4 · senior 3 · public 3 · methods 4
- **Risks & kill criteria:** Statistical — sensitivity to the maintained-
  hypothesis inputs; report alarm level across a Sharpe range (adjustable
  output per Sweep E). Political — an alarm is a review trigger, never an
  auto-redeem.
- **JD mapping:** Current: monitoring/redemption discipline. Vision:
  risk-governance literacy (platform DD rules context).
- **Sequencing:** Substrate ready; slots into S2 sheets; demo in wave 2
  batch 1, first monitoring card in the post-buy-in build order.

### M4 · Crowding & overlap radar

- **Problem & decision:** "Is our diversification illusory — are the managers
  the same trade?" Platform-grade crowding surveillance (Sweep B #9) rebuilt
  allocator-side from whatever tier exists. Improves **size** (cap aggregate
  themes) and **monitor**/**redeem** (crowded, illiquid books exit first in
  stress; Brown–Howard–Lundblad).
- **Customer:** Investment team (book-level); department leadership.
- **Tier rungs:** P — pairwise position overlap, liquidity-adjusted
  (days-to-cover-weighted) concentration: Robust measurement. 13F — free
  proxy for long US books: stale (45-day lag), longs-only, CTR holes — all
  rendered as first-class caveats. E — factor-crowding only (common tilts).
  R — return-correlation clustering, descriptive chip.
- **Method (Sweep C grounding):** Overlap = cosine/common-weight measures on
  holdings; liquidity adjustment by position ADV share; unwind stress =
  common-holder fire-sale scenario (impact ∝ overlap × ADV share, volumes
  stressed to depressed regimes per Sweep C's caveat). Factor crowding at E
  from shared tilt extremes. Validation caveat carried honestly: public
  evidence is long-only US equity.
- **Power verdict:** Prior (Sweep C): Robust (point-in-time measurement, no
  small-T problem); the *predictive* claim is the gated part. Atlas cells:
  multi-manager simulator roster with dialed common-signal participation →
  does measured overlap predict simulated unwind losses?
- **MVP & effort:** M–L. Synthetic roster version on substrate now (managers
  share a market/universe by design); real-data rung needs the 13F adapter
  (deferred) and a crowding-participation dial (deferred).
- **Wow-demo:** The roster heat-map: two "diversifying" managers are 34%
  the same book liquidity-adjusted; the unwind scenario shows the combined
  footprint moving 9 days of volume.
- **Scores:** seat 4 · senior 4 · public 4 · methods 3
- **Risks & kill criteria:** Data — 13F staleness/blind spots (shorts,
  non-US) can make the proxy misleading for L/S; ship with caveats or not at
  all. Vendor — MSCI Crowding exists (buy-or-approximate verdict): ours is
  the free sanity-check rung plus the roster-specific overlap nobody sells.
- **JD mapping:** Current: monitoring, book-level risk. Vision: platform
  crowding surveillance analog.
- **Sequencing:** Synthetic MVP after X1; real-data rung after 13F adapter +
  crowding dial.

### M5 · Say–do gap monitor

- **Problem & decision:** Does the portfolio match the letter? Letters state
  views for every manager (R-tier universal); positioning is observable at
  E/P for many. LLM-extract the stated views, score alignment against
  observed positioning, and surface drift between narrative and book.
  Improves **monitor** (narrative-drift as early warning) and **engage**
  (specific, sourced conversation material).
- **Customer:** Investment team; meeting-prep for engagement.
- **Tier rungs:** R — extraction runs on letters alone (view inventory,
  internal consistency over time). E — alignment vs. exposure summaries
  (direction/magnitude of tilts). P — alignment vs. actual positions.
- **Method (grounding):** LLM structured extraction (view = direction, theme,
  horizon, conviction, date) with an *evaluation harness before any claim*:
  synthetic letters generated from simulator ground truth — written to agree
  or disagree with the book by design — give measurable extraction and
  alignment accuracy. Alignment scoring maps views to factor/sector
  exposures; disagreement is reported with the quote and the measured
  exposure side by side (receipts, not vibes). Real-data demo on public HF
  letters only.
- **Power verdict:** Not a small-N statistical problem — an extraction-
  accuracy problem: gate is eval-harness precision/recall (target ≥0.8/0.8 on
  synthetic corpus) before any real-letter claim. Atlas: n/a; own eval set.
- **MVP & effort:** M–L. Needs the synthetic-letter corpus generator
  (deferred substrate, small) + eval harness + one public-letter demo.
- **Wow-demo:** Split screen: "the letter says cautious on duration" — quote,
  date — next to the measured +2.3y duration extension the same quarter.
- **Scores:** seat 4 · senior 3 · public 4 · methods 3
- **Risks & kill criteria:** Model — extraction accuracy below gate ⇒ do not
  ship claims (the harness exists to enforce this). Political — framed as
  "communication drift worth a conversation," never "caught you." Compliance —
  public letters only in the repo, always.
- **JD mapping:** Current: the AI/ML bullet made concrete + monitoring.
  Vision: narrative-vs-positioning is a genuine platform engagement topic.
- **Sequencing:** Demo page in wave 2 (hand-authored synthetic letter);
  hardened build after the letter-corpus generator; gateway card for E3
  (shares corpus + extraction). First lane-4 card in the post-buy-in order.

### M6 · 13F long-book intelligence

- **Problem & decision:** For US-long-book managers, free quarterly holdings
  exist; almost no allocator systematically mines them per-manager.
  Concentration, conviction persistence, crowding vs. 13F peers,
  short-interest stress on top longs. Improves **monitor** and **engage**
  (concrete talking points from public data).
- **Customer:** Investment team; engagement prep.
- **Tier rungs:** This card *is* the pseudo-P tier from public data; R/E
  rungs n/a. Caveats are the design: 45-day lag, longs-only, CTR holes,
  option-notional distortion (Sweep D) rendered as first-class TierBadge
  caveats on every view.
- **Method (grounding):** Point-in-time 13F panel (survivorship-free by
  construction); descriptors: top-N weight, HHI, conviction persistence
  (quarters-held of top positions), overlap vs. peer filers, FINRA
  short-interest on top longs. All measurement (Robust per Sweep C); no
  return-prediction claims.
- **Power verdict:** Prior (Sweep C): Robust as measurement; any predictive
  use is out of scope v1. Atlas: n/a (no estimation).
- **MVP & effort:** M. Blocked on the 13F adapter (deferred substrate; the
  parsing pain — amendments, CTR, options — is the real work).
- **Wow-demo:** A public filer's conviction timeline: the top-5 book, held
  quarters, and the quarter the concentration doubled — all from free data.
- **Scores:** seat 3 · senior 3 · public 4 · methods 3
- **Risks & kill criteria:** Data — regulatory flux (Sweep D flags N-PORT
  cadence and 13f-2 as unstable; 13F itself is stable). Political — using
  public filings of *unaffiliated* managers only in the repo. Vendor —
  Novus sells this (thin-build verdict): build only the interpretation layer.
- **JD mapping:** Current: monitoring tooling. Vision: holdings literacy.
- **Sequencing:** After 13F adapter; feeds M4's real-data rung.

---

## Lane P — Portfolio construction & governance

### P1 · Allocation under alpha uncertainty

- **Problem & decision:** Given posterior skill (S1), how much capital does
  each manager get? Point-estimate MVO maximizes into noise; the decision
  layer must consume the *posterior*, not the mean. Improves **size**
  (primary) and **redeem**/re-up (posterior-threshold rules with hysteresis).
- **Customer:** Investment team; the sizing memo is leadership-facing.
- **Tier rungs:** Inherits S1's rungs — the allocation layer is
  tier-agnostic once posteriors exist; tighter tiers ⇒ tighter posteriors ⇒
  more decisive weights (making the value of transparency *quantifiable in
  capital terms* — a genuinely novel engagement argument: "position-level
  transparency would move your allocation band from 2–4% to 3–6%").
- **Method (Sweep C/D grounding):** Posterior-draw resampled optimization
  (Michaud-style but over PyMC posterior draws, not bootstrap), or robust
  optimization over the credible set — skfolio/Riskfolio backends (Sweep D:
  build on OSS, don't rebuild solvers); marginal factor-risk contribution
  constraints (buy-the-risk-model doctrine); turnover penalty. Policy
  comparison on simulator: posterior policy vs. equal-weight vs.
  point-estimate MVO, realized utility over many worlds.
- **Power verdict:** Prior: the *inference* is S1's (Robust); the decision
  layer's test is economic — does the posterior policy beat equal-weight
  out-of-sample in simulation with realistic alpha dispersion? If
  equal-weight ties, that finding is itself decision-grade (and cheaper).
  Atlas cells: policy-regret grid.
- **MVP & effort:** M–L. Depends on S1. MVP = weight-band recommender +
  policy-comparison study; full optimizer later if the study earns it.
- **Wow-demo:** The "many worlds" chart: point-estimate MVO's realized
  utility distribution (fat left tail from noise-chasing) vs. the posterior
  policy's — plus the transparency-value line above.
- **Scores:** seat 4 · senior 4 · public 4 · methods 5
- **Risks & kill criteria:** Statistical — if posterior policy ≤ equal-weight
  across the realistic grid, publish that and kill the optimizer (keep
  bands). Political — sizing recommendations are advisory bands, never
  auto-trades.
- **JD mapping:** Current: sizing decisions. Vision: portfolio-construction
  advisory — the second-strongest senior-role card after S3/S4.
- **Sequencing:** Demo (many-worlds chart) in wave 2; real build strictly
  after S1 — first flagship-scale extension in the post-buy-in order.

### P2 · Tiered book X-ray (transparency fusion)

- **Problem & decision:** The aggregate question the team faces daily: one
  coherent factor/risk view of a book whose managers sit at different
  transparency tiers — position-rich exact, exposure-tier approximate,
  returns-only inferred — with uncertainty that degrades gracefully by tier.
  Sweeps A, C, and D all flag this fusion as unpublished territory. Improves
  **monitor** (book-level) and **size**.
- **Customer:** Investment team + department leadership (the book view).
- **Tier rungs:** The card *is* the tier axis: R managers contribute RBSA
  posteriors (wide), E managers contribute Open Protocol-style buckets
  (medium), P managers contribute holdings (tight) — one posterior book
  exposure with per-manager provenance.
- **Method (Sweep C grounding):** State-space measurement-error model:
  latent exposure path x_t per manager; observation equations per tier
  (returns: y = x'f + α + ε; OP buckets: noisy aggregation of x; holdings:
  near-exact x at snapshot dates); Bayesian filtering for the posterior book.
  The atlas (X1) supplies the measurement-error calibrations per tier — X1 is
  a hard prerequisite, not a nicety.
- **Power verdict:** Prior (Sweep C): the fusion is white space — no
  published verdict exists. Gate: E-tier posterior bands must be measurably
  tighter than R-tier bands on simulated ground truth (information gain test);
  if not, the model is decoration.
- **MVP & effort:** L. The most ambitious card in the portfolio; a research
  program disguised as a project. MVP = two-tier fusion (R+E) on a synthetic
  roster before touching P.
- **Wow-demo:** The book X-ray: one factor-exposure view of a 15-manager
  synthetic book, each manager's contribution shaded by tier-driven
  uncertainty — the campaign thesis at cross-manager altitude.
- **Scores:** seat 5 · senior 4 · public 5 · methods 5
- **Risks & kill criteria:** Statistical — model instability at roster scale
  or no measurable information gain ⇒ fall back to the reconciliation-table
  version (Sweep A's Open Protocol alignment) and document. Effort — hard
  time-box: if the two-tier MVP isn't standing after its allotted phase, park
  it with a written post-mortem.
- **JD mapping:** Current: the aggregate-book question is the team's daily
  reality. Vision: cross-book risk aggregation is platform-core.
- **Sequencing:** Strictly after X1 and S1. The designated phase-2 flagship
  candidate — highest ceiling in the portfolio, deferred on feasibility, not
  on value.

### P3 · Hire/fire decision audit & decision journal

- **Problem & decision:** Goyal–Wahal: sponsors hire on trailing
  outperformance, fire on underperformance, and fired managers subsequently
  match new hires. Almost no allocator backtests its *own* decision timing.
  A decision journal (pre-commitment: thesis, expected alpha, kill criteria
  at hire) plus a cohort audit (fired vs. replacement vs. held) turns
  governance into data. Improves **redeem** (calibrates the bar) and
  **select** (pre-commitment discipline).
- **Customer:** Department leadership (governance); the team's future self.
- **Tier rungs:** R only — needs decision dates + manager returns; works for
  the entire roster by construction. E/P — n/a.
- **Method (grounding):** Journal schema (Mauboussin/Kahneman pre-commitment,
  Sweep E); audit = event-time cohort tracking with the same interval
  discipline as S2 (small-N applies to *our* decisions too — a handful of
  hire/fire events supports description, not significance claims; say so).
- **Power verdict:** Prior (Sweep C): decisions at n = a-few-per-year are
  descriptive territory for years; the journal's value is prospective
  discipline, not retrospective significance. Rendered honestly.
- **MVP & effort:** S. Schema + tracker + a Goyal–Wahal replication demo on
  synthetic decision histories.
- **Wow-demo:** The counterfactual panel: "the fired cohort's next-3y return
  vs. their replacements" on synthetic data — the chart every IC should see
  before the next termination vote.
- **Scores:** seat 3 · senior 3 · public 3 · methods 3
- **Risks & kill criteria:** Political — auditing the team's own decisions is
  delicate; internal adoption is leadership's call; the repo version stays
  synthetic. No statistical kill (it's a discipline artifact).
- **JD mapping:** Current: institutionalizing decision knowledge. Vision:
  decision-process rigor.
- **Sequencing:** Independent; any time. Memo + small tool.

---

## Lane E — Engagement & knowledge

### E1 · Trust-preserving transparency ladder — QUICK WIN (memo)

- **Problem & decision:** Transparency is the binding input to every other
  card, and it is granted, not owed. Falk–Kosfeld: monitoring that signals
  distrust makes agents withdraw effort — and managers withdraw transparency.
  Codify the escalating-data-ask playbook: what to ask for at each
  relationship stage, what the manager receives back, and the collaborative/
  contractual framing (AIMA SMA doctrine, Open Protocol as the standard ask).
  Improves **engage** (primary) and protects the data tier every other card
  runs on — the E-brief's point that *protecting the tier is itself a design
  goal*.
- **Customer:** Manager-facing engagement; the team's negotiation playbook.
- **Tier rungs:** The ladder *is* the R→E→P path. Each rung specifies: the
  ask, the reciprocity (e.g., E-tier ⇒ peer-relative hygiene pack back to the
  manager; P-tier ⇒ sizing/decay lab access), and the power argument — "we
  ask for exposures when the returns-only interval can't answer a question we
  both care about" (the ask justified by the math, not by suspicion).
- **Method (grounding):** Sweep E doctrine end-to-end: advice framing
  (Bonaccio–Dalal), adjustable outputs (Dietvorst 2018), help-not-audit copy,
  in-workflow delivery; Sweep A's Open Protocol as the industry-standard
  E-tier template.
- **Power verdict:** n/a — process artifact. Its "power test" is whether
  transparency grants survive contact with the analytics.
- **MVP & effort:** S (<1 week). A memo in this repo + a publishable essay
  version.
- **Wow-demo:** The one-page ladder itself: three rungs, each with
  ask/reciprocity/power-justification — the document a senior allocator
  would forward.
- **Scores:** seat 4 · senior 4 · public 3 · methods 2
- **Risks & kill criteria:** None statistical. Political — generic enough to
  publish (no employer process detail), specific enough to use.
- **JD mapping:** Current: manager engagement, institutionalizing practice.
  Vision: the allocator-as-coach loop (E-brief white space — no public
  playbook exists).
- **Sequencing:** None. Week-1 deliverable.

### E2 · Narrated engagement-pack generator

- **Problem & decision:** Dashboards die (≈25% adoption; separate-tab
  failure mode); narrated artifacts delivered at the decision moment get
  used (Sweep E). Productize the doctrine: one command renders a per-manager,
  per-quarter HTML pack (Interval system, print CSS) whose sections are
  selected by tier and power, with narrative blocks drafted by LLM and edited
  by a human, and adjustable-output controls in any manager-facing version.
  Improves **engage** and the adoption of *every* other card.
- **Customer:** Investment team (QBR prep); manager-facing versions later.
- **Tier rungs:** Tier-aware by construction — the pack renders only what the
  manager's tier and the PowerGate registry (X1) permit; TierBadges on every
  section.
- **Method (grounding):** Templated composition over analytics JSON
  (S2/M1/M3/S1 outputs); PowerGate-aware section selection; Dietvorst
  adjustable blocks (priors/thresholds as controls); help-not-audit copy
  patterns as a linted style guide, not tribal knowledge.
- **Power verdict:** n/a — delivery infrastructure; inherits gates from the
  registry.
- **MVP & effort:** Grows organically: S2's pack is v0.1; each flagship demo
  extends it. Standalone effort S per increment.
- **Wow-demo:** `python -m quant_allocator.packs render --manager 7` → a
  print-clean A4 pack with narration, intervals, chips, and gates — the
  kill-the-dashboard argument as a working artifact.
- **Scores:** seat 4 · senior 4 · public 4 · methods 2
- **Risks & kill criteria:** Scope — must not become a framework before it
  has three real consumers (right-level engineering; one small app maximum
  per demo doctrine). LLM narration ships only human-edited.
- **JD mapping:** Current: communication tooling. Vision: the packaging craft
  Sweep B job specs demand ("outstanding written and oral communication").
- **Sequencing:** Born inside S2; formalized after two more consumers exist.

### E3 · Manager knowledge graph & retrieval

- **Problem & decision:** Letters, DDQs, meeting notes hold the team's
  collective memory, unqueryable. Structured extraction into an entity model
  (manager, strategy, person, view, theme, meeting, document — with dates and
  provenance) plus hybrid retrieval, anchored to decision hooks: meeting-prep
  briefs, say–do inputs, "what did they say about liquidity in 2024?"
  Improves **engage** (prepared conversations) and **select** (institutional
  memory at underwriting). Directly the "institutionalizing domain knowledge"
  JD bullet.
- **Customer:** Investment team (daily); the team's future members.
- **Tier rungs:** Orthogonal to R/E/P — documents exist for every manager;
  the graph *records* each manager's tier and what was promised when.
- **Method (grounding):** LLM extraction → typed tables + light graph layer
  (DuckDB/SQLite; no graph-DB until the graph earns it — right-level
  engineering); hybrid retrieval (BM25 + embeddings) with graph expansion;
  extraction eval on the synthetic corpus (shared with M5). The spec's
  non-goal stands: no chatbot without a decision hook — the hooks are the
  product.
- **Power verdict:** n/a statistically; gate = retrieval/extraction eval vs.
  a plain-RAG baseline. If the graph doesn't beat plain RAG on the eval set,
  simplify to extraction tables + search and say so.
- **MVP & effort:** M–L. Needs the synthetic letter/DDQ corpus (shared with
  M5); public letters for the real demo.
- **Wow-demo:** Meeting-prep brief, one command: last quarter's stated views,
  open questions from prior notes, say–do flags, and the tear-sheet — the
  30-minute prep done in 30 seconds.
- **Scores:** seat 5 · senior 3 · public 3 · methods 3
- **Risks & kill criteria:** Scope — graph complexity must be earned (kill
  criterion above). Public-portfolio differentiation — RAG demos are
  commonplace in 2026; the schema and decision hooks are the differentiator,
  and the card is honest that the tech is not the point.
- **JD mapping:** Current: the verbatim "institutionalizing and expanding the
  team's collective domain knowledge" bullet + AI/ML. Vision: supporting
  infrastructure.
- **Sequencing:** After the letter-corpus generator; pairs with M5 (shared
  extraction + eval).

---

## Lane X — Meta / infrastructure

### X1 · Tier & Power Atlas — FLAGSHIP

- **Problem & decision:** The two questions under every other card: *how much
  data until this metric means anything* (power axis), and *how much does it
  degrade from P to E to R* (tier axis). Sweep B: the tier-degradation map is
  unpublished anywhere; Sweep C: small-sample power tables for holdings
  metrics barely exist. The simulator was built precisely for this — it emits
  all three tiers of the same known ground truth. The atlas is the campaign
  thesis ("inference under partial transparency") made measurable. Improves
  **select/monitor/engage** at the meta level: it decides which analytics are
  allowed to render, for which manager, at which tenure.
- **Customer:** The team (what to trust per tier); every other card (its
  thresholds); the public portfolio (nothing like it exists).
- **Tier rungs:** The card *is* the tier axis — each analytic measured at P,
  E, and R emissions of identical ground truth, with the degradation
  quantified ("what E loses vs. P; what R loses vs. E").
- **Method (Sweep C grounding):** Designed Monte Carlo: grid over simulator
  dials (IC ∈ {0, .02, .04, .07, .10}, alpha half-life, sizing discipline,
  T ∈ {24,36,48,60,120}, breadth, turnover) × metrics (OLS alpha t, posterior
  alpha, Sharpe CIs, hit rate, slugging, sizing-curve slope, decay curve,
  drift detectors, overlap) × tiers; ≥1,000 seeded paths per cell (per-module
  RNG streams already decorrelated). Outputs: (a) the atlas document — power
  curves, bias tables, tier-degradation deltas; (b) a machine-readable
  thresholds JSON: the **PowerGate registry** every analytic and pack
  consumes.
- **Power verdict:** n/a — this card *produces* the verdicts. Sweep C's table
  is its hypothesis set; the atlas confirms, refines, or overturns each row.
- **MVP & effort:** M (vol. 1: returns-tier metrics + hit-rate/sizing
  basics). Vol. 2 (holdings metrics deep, fusion calibrations for P2) later.
- **Wow-demo:** The degradation table for one beloved analytic: "sizing skill:
  detectable at P with 300 trades; at E, undetectable at any realistic N; at
  R, unknown pending S6" — honesty as a product. Plus the playground (X2) as
  its interactive face.
- **Scores:** seat 4 · senior 5 · public 5 · methods 5
- **Risks & kill criteria:** Modeling — conclusions are conditional on
  simulator realism; publish the dial ranges and stress the nuisance grid so
  the conditionality is explicit. Scope — hard cap vol. 1 at the named
  metric set; the grid must not sprawl.
- **JD mapping:** Current: methods leadership, institutionalizing standards.
  Vision: the allocator↔platform bridge — "here is the platform analytic,
  here is what survives at your tier" is the PM-engagement interview answer.
- **Sequencing:** Substrate ready. Feeds every gated card (S2–S5, M1–M4, P1)
  and is a hard prerequisite for P2. X2 is its interactive face.

### X2 · Transparency playground — QUICK WIN

- **Problem & decision:** The thesis needs a communication device: *see* what
  each transparency tier can honestly claim as skill, sample, and disclosure
  vary. An interactive page where dials (IC, alpha half-life, sizing
  discipline, T, tier) drive what renders — IntervalStats widening, verdicts
  flipping to noise, PowerGates closing. Improves **engage** internally
  (educating stakeholders on why the team reports intervals) and is the
  single best public artifact.
- **Customer:** Department leadership and stakeholders (the education tool);
  the public portfolio.
- **Tier rungs:** The tier selector is the star control — same ground truth,
  three honesty levels.
- **Method (grounding):** Precomputed scenario grid (a subset of X1's cells)
  shipped as JSON; dials snap to grid points; static HTML/CSS/JS in the
  Interval dark theme; GitHub Pages. No server, no framework (demo-layer
  spec, locked).
- **Power verdict:** n/a — it renders X1's verdicts; ships v1 on a starter
  grid (computed directly from the simulator) and upgrades when atlas vol. 1
  lands.
- **MVP & effort:** S–M. Grid computation + one well-crafted page.
- **Wow-demo:** It is the wow-demo. Drag T from 120 down to 36 and watch
  every claim you thought you could make dissolve into honest grey.
- **Scores:** seat 3 · senior 4 · public 5 · methods 4
- **Risks & kill criteria:** Scope — one page, precomputed only ("one small
  app maximum"). If the starter grid misleads relative to atlas vol. 1,
  regenerate before publicizing.
- **JD mapping:** Current: stakeholder communication. Vision: the
  teach-the-PM craft, demonstrated.
- **Sequencing:** Simulator ready; starter grid immediately, v2 after X1.
  Births the Interval dark theme (design-layer spec §5).
