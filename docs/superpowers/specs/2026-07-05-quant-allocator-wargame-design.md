# Quant-Allocator Research Campaign — War-Game Plan

**Date:** 2026-07-05
**Status:** Approved in section-by-section review; pending final review of this written spec
**Owner:** Joon Kang
**Executor:** the assistant (the lead reviewer orchestrator + senior research sub-agents)

---

## 1. Mission

Build the research agenda and analytics that treat an allocator's external hedge
fund managers the way a multi-manager platform's PM Engagement team treats
internal PMs — adapted to the allocator's decisions (**select, size, monitor,
engage, redeem**) and the allocator's data reality (**tiered transparency**),
across all hedge fund strategies, with fundamental equity long/short as the
flagship deep-dive module.

The structural tension that defines the whole project space: a platform sees
every fill; an allocator sees monthly returns for everyone, risk reports for
many, position transparency for some, and letters/meetings for all. Every
analytic here is therefore an exercise in **inference under partial
transparency**, plus the relationship/engagement layer both role descriptions
emphasize.

Two customers, two altitudes:

- **Per-manager:** Is this manager skilled? Where does the P&L come from? Is
  the process degrading? What feedback would improve risk-adjusted returns?
- **Cross-manager:** How to size, combine, and net managers? What does the
  aggregate book look like in factor/crowding space? When to add, trim, redeem?

## 2. Locked scope decisions

| Decision | Choice | Consequence |
| --- | --- | --- |
| Optimization objective | All four axes: current-seat impact, senior-role case, public skill portfolio, methods mastery | Rubric scores all four; flagships must stack ≥3 axes rather than maximize one |
| Manager universe | All hedge fund strategies | Strategy-agnostic core analytics; fundamental equity L/S is the flagship deep module |
| Data-tier base case | Tiered by design | Every analytic ships in three rungs: returns-only, exposures, transparency |
| Build depth | Memos + 1–2 flagship prototypes | Repo holds docs, substrate, and flagships — not a full toolkit build-out |
| Campaign structure | Dual-track | Landscape sweeps and substrate build run in parallel, then converge |

## 3. Focus lanes

1. **Manager skill measurement & P&L decomposition.** Strategy-agnostic core:
   factor-adjusted alpha with strategy-appropriate factor sets (equity factor
   models; Fung–Hsieh-style factors for macro/trend; credit factors). Equity
   L/S module adds holdings-level skill: hit rate/slugging, sizing curves,
   alpha decay, short-book quality.
2. **Portfolio construction at two altitudes.** Within-manager diagnostics
   (concentration, factor hygiene, gross/net discipline — the material for
   engagement conversations) and cross-manager book construction
   (overlap/crowding/netting, factor aggregation, allocation under alpha
   uncertainty, redemption/re-up timing).
3. **Monitoring & early warning.** Style drift, crowding spikes,
   drawdown-regime behavior, and the "say–do gap": does the portfolio match
   the letter?
4. **LLM/document intelligence & knowledge institutionalization.** Letters,
   DDQs, transcripts, meeting notes → structured, queryable manager knowledge.
   Directly evidences the current JD's "institutionalizing and expanding the
   team's collective domain knowledge."
5. **Prototyping substrate.** Public data adapters + synthetic manager
   simulator (Track 2, Section 7).

## 4. Non-goals

- **Security-level alpha research** — that is the managers' job; wrong seat.
- **Execution/TCA/microstructure** — no order flow in an allocator seat.
- **Anything intraday.**
- **Derivative-pricing or structured-product cashflow engines** — credit and
  structured products remain literacy, not projects.
- **Rebuilding the Risk department's VaR plumbing** — integrate, don't compete.
- **Enterprise data-platform builds** — prototype-grade data engineering only.
- **Chatbots without a decision hook.**

## 5. Cross-cutting technical themes

Every idea card is tested against these:

- **Small-N / low-frequency inference.** With tens of managers and monthly
  data, statistical power is the enemy. Default toolkit: shrinkage,
  hierarchical Bayes, and explicit power tests via the simulator.
- **Point-in-time discipline and survivorship/backfill bias** in any
  manager-universe claim or dataset.
- **Tiered degradation.** Returns-only → exposures → transparency versions of
  each analytic, each rung documented for what it buys.
- **Communication artifacts as first-class outputs** — tear sheets, PM packs,
  QBR decks are deliverables, not afterthoughts.

## 6. Track 1 — Landscape sweeps

Five parallel deep-research sub-agents (senior), timeboxed to one session.
Each produces a 1–2 page brief: *state of practice → best sources → white
space → implications for idea cards*.

| Sweep | Mission | Answers | Seed sources |
| --- | --- | --- | --- |
| A. Allocator/FoF quant practice | What sophisticated allocators do and publish | What is table stakes vs. white space for an allocator quant team? | CPPIB/Future Fund/CalSTRS materials; Albourne/Aksia/Mercer methods; fund-selection canon: persistence literature, Bayesian fund alphas (Baks–Metrick–Wachter; Pástor–Stambaugh), false-discovery control (Barras–Scaillet–Wermers), FoF value-add evidence |
| B. Platform PM-engagement practice | The frontier the manager's vision points at | What does "good" look like, and which pieces transplant to each allocator data tier? | BAM PM Engagement and Citadel/P72/MLP equivalents via job postings, talks, podcasts, alumni writing; extract the analytics catalog (sizing curves, alpha-decay curves, PM report cards, crowding dashboards, factor-hygiene reviews) |
| C. Methods literature | The statistics per data tier | Which methods are actually robust at 36–60 monthly observations? | Returns-based: style analysis, conditional factor models, Fung–Hsieh factors. Holdings-based: active share, ICs, trade-level skill decomposition. Crowding measures; drawdown/regime models; hierarchical Bayesian manager models |
| D. Data & tooling | What to prototype on; what already exists commercially | Build vs. buy per candidate idea — never rebuild an existing product | Public: 13F, N-PORT, short interest, ETF holdings, Ken French/AQR factor libraries, HFR/SG index families. Vendors: Barra/Axioma, Novus, Essentia, MSCI crowding. OSS: skfolio, Riskfolio-Lib, alphalens, PyMC |
| E. Adoption & influence | Why PM-facing analytics get used vs. shelved | How to package for stakeholder buy-in and manager trust | Artifact design (tear sheets, QBR packs); trust dynamics of engagement (helping, not auditing); how platform teams monetize research internally |

Sub-agent prompts include the compliance guardrail: public sources only.

## 7. Track 2 — Prototyping substrate

Runs in parallel with the sweeps. Hard-capped at two components, **zero
analytics** until convergence:

1. **Public data adapters.** Point-in-time-clean loaders: SEC EDGAR 13F
   (quarterly long books of real managers — the pseudo-transparency tier),
   factor return libraries (Ken French, AQR, Fung–Hsieh replication),
   fund/index return series as returns-only proxies, ETF/N-PORT holdings.
   Thin, boring, correct.
2. **Synthetic manager simulator.** Generates realistic hedge-fund books —
   equity L/S done properly (positions, trades, factor tilts), plus
   deliberately crude macro/credit return-stream generators — with dialable
   ground truth: true alpha level, alpha half-life, sizing discipline,
   crowding participation, turnover, vol targeting, gross/net policy. Each
   simulated manager emits all three data tiers of itself: returns-only,
   exposure summaries, full transparency.

The simulator is the strategic piece, for three reasons:

- **Compliance, structurally solved.** Every demo runs on synthetic or public
  data; the repo can be public; methods transfer internally by swapping
  adapters.
- **Power testing.** Ground truth is known, so every proposed analytic gets a
  power test — "can this metric detect a true skill difference from 36 monthly
  observations, or is it noise theater?" Ideas that fail are killed or demoted
  to the transparency tier before anyone builds them internally.
- **Portfolio artifact.** The simulator is interview-grade work in its own
  right.

## 8. Convergence — the idea portfolio

the lead reviewer-level synthesis turns the sweeps into the primary deliverable: **a
curated portfolio of ~20 project ideas with detailed contexts.**

**Idea card template** (uniform across all cards):

- Problem & decision improved (select / size / monitor / engage / redeem)
- Customer (investment team, manager-facing engagement, department leadership)
- Data-tier rungs: returns-only / exposures / transparency versions and what each buys
- Method sketch, grounded in Sweep C
- Power verdict from the simulator
- MVP scope & effort
- Wow-demo — the artifact that makes a stakeholder lean forward
- Four-axis scores (1–5): current-seat impact · senior-role case · public-portfolio value · methods mastery
- Risks & kill criteria (statistical, political, data, vendor-duplication)
- JD mapping: which bullets of the current JD and the manager's-vision JD it evidences
- Sequencing: dependencies on substrate or other ideas

**Prioritization rubric:** four axes + feasibility + time-to-first-demo.
Flagships are chosen for axis-stacking (strong on ≥3 axes), not single-axis
maximums.

**Workshop output:** 2 flagships + 3 quick wins + a 90-day plan. Per the
build-depth decision, 1–2 of the selected flagships get prototyped in this
repo; both get full idea cards regardless. The remaining cards form a
documented backlog — itself serving the "institutionalizing domain knowledge"
mandate.

**Illustrative flagship candidates** (non-binding; the workshop decides):

- Tiered manager skill tear-sheet engine (strategy-aware factor-adjusted alpha, conditional performance, drawdown fingerprints)
- Say–do gap monitor (LLM-extracted stated views vs. observed positioning)
- Crowding & overlap radar across managers, with unwind stress scenarios
- Allocation under alpha uncertainty (hierarchical-Bayes manager alphas → book construction)
- Sizing & alpha-decay lab (transparency tier; the classic PM-engagement analytic)
- Manager knowledge graph + retrieval over letters/DDQs/notes

## 9. Execution policy — models, effort, agents

- **Main loop:** the lead reviewer as orchestrator. Reserved for heavy reasoning:
  cross-sweep synthesis, idea-card generation, rubric scoring, power-analysis
  design, spec/doc quality.
- **Sub-agents:** landscape sweeps and mechanical tasks run on senior
  (Agent tool, `model: senior`), dispatched in parallel.
- **Reasoning effort:** `/effort high` as the session default for running
  phases (dispatch, monitoring, substrate scaffolding, brief QC);
  `/effort max` reserved for the convergence session (idea-card synthesis and
  prioritization). Effort is user-controlled via `/effort`.
- **Compliance guardrail in every sub-agent prompt:** public sources only; no
  employer-internal facts, manager names, or portfolio details in this repo, ever.
  The repo is treated as public at all times; Joon translates methods
  internally.

## 10. Cadence

- **Session 1–2:** Both tracks. Sweeps A–E dispatched as parallel senior
  agents; substrate scaffolding begins. User steers between sessions with
  coarse, non-confidential signals ("we'd never get that data"; "stakeholder X
  cares about Y").
- **Session 3:** Convergence. Review idea portfolio, score, shortlist
  (2 flagships + 3 quick wins), draft the 90-day plan.
- **Session 4+:** Flagship builds on the standing substrate.
- **Timeboxes are hard:** sweeps get one session; research that isn't
  converging gets cut, not extended.

## 11. Risks & mitigations

| Risk | Mitigation |
| --- | --- |
| Statistical power (defining technical risk of allocator analytics) | Simulator power tests gate every idea (Section 7) |
| Relationship framing — engagement analytics reading as "gotcha" | Sweep E owns packaging doctrine: analytics must read as helping the manager; a manager who feels audited stops giving transparency |
| Survivorship/backfill bias | Bias note on every universe claim; point-in-time discipline in all adapters |
| Compliance | Public/synthetic data only; no employer specifics or manager names; repo treated as public |
| Vendor duplication | Sweep D runs build-vs-buy on every candidate |
| Over-research | Sweeps serve the idea cards; timeboxed, converge-or-cut |

## 12. Success criteria

1. The curated ~20-card idea portfolio with detailed contexts — the primary ask.
2. Five landscape briefs that double as a domain map.
3. 1–2 working flagship prototypes on public/synthetic data in this repo.
4. A 90-day execution plan.
5. Joon can narrate the senior-role story with artifacts, not aspirations.

## 13. Target repo layout

```
docs/
  superpowers/specs/      # this spec + future design docs
  briefs/                 # sweep outputs (A–E)
  ideas/                  # idea cards + prioritization
src/quant_allocator/
  adapters/               # public data loaders (13F, factors, returns)
  simulator/              # synthetic manager generator
  flagships/              # post-convergence prototypes
```
