# Sweep D — Data & Tooling Landscape

## 1. State of practice

An allocator quant team sits between two data realities: a rich, free public layer (regulatory filings, academic factor libraries) that is powerful but lagged and long-biased, and a mature commercial layer where risk models, crowding data, and allocator-workflow platforms are already productized. The winning posture is to buy the commoditized infrastructure (security-level risk models, factor data feeds, aggregation plumbing) and build the thin, proprietary layer that encodes the firm's own manager-selection edge — especially returns-based analytics that work when you only have a monthly return stream.

Public filings give real but partial position transparency. Form 13F is quarterly, filed up to 45 days after quarter-end, and covers only long US-listed 13(f) securities — no shorts, no non-US, no cash, and options reported at notional/share equivalents that can distort weights. Confidential-treatment requests and permitted restatements let managers legally hide or delay positions, and academic work documents strategic misreporting. Its one big virtue: it is survivorship-bias-free (all historical filers remain). N-PORT gives monthly holdings for '40-Act registered funds (relevant only where a manager runs a mutual-fund vehicle), but public disclosure is currently limited to the third month of each quarter at a 60-day lag — and the regime is in flux (2024 expansion vs. a Feb 2026 SEC proposal to scale it back). Short-interest data is free and bi-monthly from FINRA; the SEC's new aggregate monthly short disclosure (Rule 13f-2 / Form SHO) was remanded by the Fifth Circuit in Aug 2025, so its go-live is uncertain (low confidence). ETFs are the transparency bright spot: Rule 6c-11 mandates full daily holdings, free on issuer sites (except semi-transparent active ETFs).

Commercial vendors cluster into four non-overlapping jobs: (1) security-level factor risk (MSCI Barra; Axioma, now owned by SimCorp/Deutsche Börse) — deep covariance/optimizer/attribution engines that require holdings; (2) allocator portfolio-intelligence platforms (SEI Novus) — aggregation, look-through, peer/13F "smart-money" analytics, manager monitoring; (3) positioning/crowding (MSCI Crowding) and factor-exposure visualization for due diligence (Confluence Style Analytics); (4) PM behavioral analytics (Essentia) — trade-level decision skill, sold to managers but with a Behavioral Alpha Benchmark allocators use for assessment. Open-source covers optimization and performance math but nothing allocator-native.

**Build-vs-buy by capability area:**

| Capability | Verdict | Rationale |
|---|---|---|
| Security-level multi-factor risk model + optimizer | **Buy** (Barra/Axioma) | Decades of estimation, covariance, industry taxonomy; rebuilding is a multi-year sink with no edge |
| Returns-based style/factor exposure of external managers | **Build** | Ken French/AQR factors + rolling regressions; works on monthly returns alone — core edge for tiered transparency |
| Portfolio aggregation, look-through, manager monitoring | **Buy or thin-build** (SEI Novus) | Plumbing-heavy, low differentiation; build only if workflow is idiosyncratic |
| Factor & hedge-fund crowding / positioning | **Buy or approximate** (MSCI Crowding) | Proprietary flow data hard to replicate; 13F gives a rough free proxy |
| Behavioral / trade-decision analytics | **Buy** (Essentia) | Needs position/trade-level data; only for the few transparent managers |
| Performance & risk metrics library | **Adopt OSS** (empyrical-reloaded) | Commodity math; don't reinvent Sharpe/drawdown/VaR |
| Portfolio optimization / capital sizing | **Build on OSS** (skfolio, Riskfolio-Lib) | Mature convex/HRP backends; wrap with firm constraints |
| Bayesian manager-skill / small-sample inference | **Build** (PyMC) | No vendor productizes this well — genuine white space |
| 13F/N-PORT ingestion & "smart-money" analytics | **Build** (free data) or buy Novus | Cheap to prototype; edge is in the interpretation layer |

## 2. Best sources (annotated links)

**Public data**
- SEC Form 13F data sets & FAQ — bulk quarterly holdings, structured files; read the FAQ on confidential treatment and amendments. https://www.sec.gov/data-research/sec-markets-data/form-13f-data-sets and https://www.sec.gov/rules-regulations/staff-guidance/division-investment-management-frequently-asked-questions/frequently-asked-questions-about-form-13f
- SEC N-PORT reporting rule status (Federal Register, Feb 2026 proposal) — confirms current public-disclosure cadence is in flux. https://www.federalregister.gov/documents/2026/02/23/2026-03460/form-n-port-reporting
- FINRA Short Interest — free bi-monthly consolidated short interest. https://www.finra.org/filing-reporting/regulatory-filing-systems/short-interest
- SEC Rule 13f-2 / Form SHO adopting release (note Fifth Circuit remand, status uncertain). https://www.sec.gov/files/rules/final/2023/34-98738.pdf
- Kenneth R. French Data Library — free factor returns (FF3/FF5, momentum, industry), monthly/daily; not point-in-time (definitions and underlying CRSP data get revised/back-filled). https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html
- AQR Data Sets — free QMJ, Betting-Against-Beta, Time-Series Momentum, Value & Momentum Everywhere, Century of Factor Premia; updated monthly, credit required. https://www.aqr.com/Insights/Datasets
- Global-q factor library (Hou-Xue-Zhang q4/q5) — free, updated through Dec 2024. https://global-q.org/factors.html
- Andrea Frazzini's data library (BAB/QMJ construction files). https://pages.stern.nyu.edu/~afrazzin/data_library.htm

**Index families (headline free / constituents licensed)**
- HFR — HFRI headline returns visible to registered users; constituent data and full database are subscription/commercial-license. https://www.hfr.com/indices/
- BarclayHedge — free headline monthly strategy indices (self-reported; backfill/survivorship caveats). https://portal.barclayhedge.com/cgi-bin/indices/displayIndices.cgi?indexID=hf
- SG (Société Générale) CTA/Trend indices — publicly published index levels on SG's index site (verify current URL; medium confidence on free depth).

**Vendors**
- SEI Novus — portfolio intelligence for allocators; look-through, peer/13F analytics, manager monitoring. https://www.novus.com/ and https://www.novus.com/product/analytics
- MSCI Equity Factor Models (Barra) and Crowding Solutions. https://www.msci.com/data-and-analytics/factor-investing/equity-factor-models and https://www.msci.com/data-and-analytics/factor-investing/crowding-solutions
- Axioma factor risk models (SimCorp). https://www.simcorp.com/solutions/strategic-solutions/axioma-solutions/axioma-factor-risk-models
- Confluence Style Analytics — factor-exposure visualization (Style Skyline), 28,000+ pre-computed funds, manager due-diligence. https://www.confluence.com/products/style-analytics/
- Essentia Analytics — Behavioral Alpha Benchmark and PM decision analytics. https://www.essentia-analytics.com/product/behavioral-alpha-benchmark/

**Open source**
- skfolio — scikit-learn-based optimization (MVO, HRP, Black-Litterman, robust covariance, CV/stress-testing). https://skfolio.org/ and https://github.com/skfolio/skfolio
- Riskfolio-Lib — cvxpy-based, 24 risk measures, HRP/NCO, risk-parity. https://riskfolio-lib.readthedocs.io/
- alphalens / empyrical (Quantopian, archived) and maintained forks alphalens-reloaded / empyrical-reloaded (Stefan Jansen). https://github.com/quantopian/empyrical and https://pypi.org/project/alphalens-reloaded/
- PyMC — Bayesian hierarchical modeling for manager-skill/small-sample inference. https://www.pymc.io/

## 3. White space

Vendors are strong where holdings exist and weak where they don't — the opposite of the allocator's typical information set. Concrete gaps:

- **Returns-only manager analytics.** Barra, Axioma, Style Analytics, and Essentia all lean on holdings/trade data. For the bulk of managers where the team has only monthly returns, there is no packaged product doing rigorous returns-based style, factor, and regime-exposure decomposition with proper uncertainty bands. This is the clearest build lane.
- **Small-sample manager skill.** With 24–60 monthly observations, frequentist alpha t-stats are noisy. No vendor productizes hierarchical Bayesian partial-pooling (PyMC) to shrink manager alphas toward strategy peers and quantify skill probability.
- **Tiered-transparency fusion.** Nobody stitches the three data tiers (returns for all, risk summaries for many, positions for few) into one coherent exposure/risk view with confidence that degrades gracefully by tier.
- **Free-data crowding proxy.** MSCI Crowding is proprietary; a 13F + short-interest + ETF-flow approximation of manager/factor crowding is buildable and cheap, useful even as a sanity check on the paid feed.
- **Non-linearity / optionality detection.** Returns-based tools rarely flag hidden convexity/short-vol behavior from a return series (e.g., regression on option-like payoffs, drawdown asymmetry) — high value for macro/credit manager monitoring.

## 4. Implications for idea cards

- **Returns-based style engine (improves SELECT and MONITOR).** Rolling multi-factor regressions of manager returns on Ken French + AQR factors to classify true style, detect style drift, and flag closet-index exposure — works for every manager regardless of transparency tier; prototype free.
- **Bayesian manager-skill scorer (improves SELECT and REDEEM).** PyMC hierarchical model pooling managers within strategy to produce a shrunk alpha and a P(skill>0); triggers redemption review when skill probability decays. Genuine white space, no vendor overlap.
- **13F/short-interest crowding & conviction monitor (improves MONITOR and ENGAGE).** For transparent managers, track position concentration, crowding overlap with peers, and short-interest stress on top longs from free SEC/FINRA data; gives concrete talking points for manager engagement calls.
- **Factor-risk contribution and sizing overlay (improves SIZE).** Feed manager exposures (returns-based, or Barra/Axioma where holdings exist) into skfolio/Riskfolio-Lib to size allocations by marginal factor-risk contribution rather than standalone vol — buy the risk model, build the sizing logic.
- **Hidden-convexity / drawdown-asymmetry screen (improves MONITOR and REDEEM).** Return-series tests for short-vol/short-tail behavior that a linear risk report misses; early warning for managers whose smooth Sharpe masks left-tail exposure.
- **Manager fact-sheet aggregation layer (improves SELECT and SIZE).** A thin internal alternative to SEI Novus for peer benchmarking and look-through; build only if workflow is idiosyncratic, otherwise buy — the plumbing is not an edge.

*Confidence flags: N-PORT public-disclosure cadence and Rule 13f-2/Form SHO go-live are both in active regulatory flux (low confidence on current-state specifics — verify at filing time). SG CTA index free-access depth is medium confidence. All vendor capability descriptions are from public product pages, not hands-on evaluation.*
