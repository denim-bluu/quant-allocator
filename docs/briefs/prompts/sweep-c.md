You are a senior quantitative researcher producing a landscape brief for the
quant team of a large institutional allocator (sovereign-wealth-scale,
fund-of-funds style) that invests in external hedge fund managers across
strategies (fundamental equity long/short, macro, credit, quant). The team is
designing analytics that work under tiered transparency: monthly returns for
all managers, exposure/risk-report summaries for many, position-level
transparency for a few.

MISSION: Deliver a per-method robustness verdict for the statistics of
manager evaluation at realistic sample sizes — 36–60 monthly observations,
tens of managers. This brief gates which methods the team is allowed to
build on, so the statistical judgment must be rigorous and explicit.

QUESTIONS TO ANSWER — for EACH method below, state what it estimates, its
minimum data tier, its statistical power at 36–60 monthly observations
(with reasoning: estimator variance, bias, multiple-testing exposure), and a
verdict (robust / usable-with-shrinkage / noise-theater at this N):
- Returns-based: factor-model alpha (OLS and conditional), Sharpe-style
  returns-based style analysis, Fung–Hsieh seven-factor model for
  macro/trend, credit factor models.
- Holdings-based: active share, information coefficients, hit rate/slugging,
  trade-level skill decomposition, sizing-skill curves, alpha-decay curves.
- Cross-sectional: performance persistence tests, hierarchical/Bayesian
  shrinkage of manager alphas, false-discovery-rate control.
- Regime/drawdown: drawdown-distribution analysis, regime-conditional
  performance, style-drift detection.
- Crowding: overlap measures, short-interest-based crowding, liquidity-
  adjusted concentration.

SEED SOURCES (start here, then go well beyond): Fung & Hsieh (2004);
Grinold & Kahn; Pastor–Stambaugh (2002); Baks–Metrick–Wachter (2001);
Barras–Scaillet–Wermers (2010); Getmansky–Lo–Makarov (2004) on smoothed
returns; literature on Sharpe-ratio standard errors (Lo 2002; Ledoit–Wolf).

OUTPUT — return ONLY a markdown brief, 900–1800 words, with exactly these
four sections:
## 1. State of practice
## 2. Best sources (annotated links)
## 3. White space
## 4. Implications for idea cards
(Section 1 must contain the per-method verdict table. Section 4: at least 5
concrete bullets, each naming the allocator decision it improves: select /
size / monitor / engage / redeem.)

GUARDRAILS: public sources only; include working URLs; never fabricate a
citation — if unsure a source exists, say so explicitly; flag low-confidence
claims; do not include any non-public or firm-internal information.
