## The decision

The allocator should audit hire and fire decisions against the alternatives passed
over, while preserving the thesis and reversal rule written **before** outcomes were
known.

The method has two outputs. A prospective journal improves the next decision from the
first entry. A retrospective ledger compounds the acted-on and counterfactual paths,
then reports a signed gap where positive always means the decision helped. Across
events, the aggregate is shrunk toward a zero-value-add base rate and shown as an
interval that may straddle zero for years.

The subject is the allocator's process, not manager skill. No single event becomes a
committee score, a persistence claim, or a mechanical reversal.

## Why the obvious answer fails

Judging a decision from the eventual outcome creates hindsight and outcome bias. A good
decision can draw a bad result; a poor decision can get lucky. Without a pre-committed
thesis, horizon, and kill criterion, the remembered rationale changes after the path is
known.

Auditing only hires and fires discards the control group. A manager considered for
termination and retained is evidence about the decision process too. Excluding those
holds turns a decision audit into a survivorship-biased action log.

Comparing a fired manager with cash is usually the wrong counterfactual. Capital was
redeployed. The decision helped only if the replacement—or the best available proxy for
it—did better.

Finally, event counts are tiny and clustered. Several decisions made in one quarter
share the same forward market episode. A naive p-value treats correlated events as
independent and manufactures a track record that no single allocator can realistically
earn.

## The intuition

The journal fixes the decision rule before the draw. At the vote date, record the
thesis, expected alpha, horizon, kill criterion, and passed-over alternative. That is a
governance instrument, not a prediction model.

The ledger is then deterministic accounting. Put every event at time zero, compound
the acted-on and counterfactual returns over identical forward windows, and subtract.
Every row remains visible with its source and comparison rung.

Only after preserving the event stories should an aggregate be considered. Since the
sample is small and correlated, shrink the observed average toward the external base
rate that hire/fire timing adds nothing. A wide interval around zero is a substantive
finding: the local history has not overruled the reference class.

## A small numerical example

Suppose the allocator fires manager A and funds manager B. Over the following three
years, A compounds to an 18% excess return and B to 12%. Fire value-add is

$$
V=R_{\text{replacement}}-R_{\text{fired}}=12\%-18\%=-6\%.
$$

The decision hurt by six percentage points relative to keeping A.

Now take 20 events arranged as four decisions in each of five quarterly cohorts. If
within-cohort correlation is $\rho=0.5$, the design effect is

$$
1+(4-1)\times0.5=2.5,
$$

so effective sample size is

$$
N_{\text{eff}}=\frac{20}{2.5}=8.
$$

If observed event value-add averages $-3\%$ per year with standard deviation 8%, the
honest standard error is $8\%/\sqrt8=2.83\%$, not $8\%/\sqrt{20}=1.79\%$.

With a zero-centered prior scale $\tau=2\%$ per year, the shrinkage weight is

$$
w=\frac{\tau^2}{\tau^2+\operatorname{se}^2}
=\frac{4}{4+8}=0.33.
$$

The posterior point is $0.33\times(-3\%)=-1\%$ per year. Eight independent-equivalent
events are not enough to move far from the zero base rate.

## The method

Every hire, fire, and hold-under-review receives a prospective record containing the
decision date, type, manager, thesis, expected annual alpha, horizon, kill criterion,
and designated counterfactual. The default horizon is provisionally three years, and
the audit can show one-, two-, and three-year windows.

For manager $i$, decision month $d$, and horizon $h$ years, forward excess return is

$$
R_i^{\text{fwd}}(d,h)=
\prod_{t=d+1}^{d+12h}(1+r_{i,t}-r_{f,t})-1.
$$

$r_{i,t}$ is monthly net return and $r_{f,t}$ is the monthly risk-free return. The
product compounds the first $12h$ months after the decision. A factor-adjusted version
uses the same forward window to distinguish manager selection from a factor bet that
happened to pay.

Signed event value-add $V_e$ is defined so positive always means helpful:

- hire: hired manager minus the passed-over alternative;
- fire: replacement minus fired manager;
- hold-under-review: retained manager minus the peer median.

Counterfactual quality follows a hierarchy: linked replacement first, same-strategy
peer median second, and strategy benchmark last. Every event displays which rung was
used. The benchmark is available but weakest because it mixes manager selection with
beta.

For the aggregate, let $\bar V$ be mean event value-add and $\tau$ the zero-centered
prior scale. The shrunk process estimate is

$$
\widehat V^{\text{post}}=w\bar V,
\qquad
w=\frac{\tau^2}{\tau^2+\widehat{\operatorname{se}}(\bar V)^2}.
$$

The standard error uses cohort-aware effective sample size

$$
N_{\text{eff}}=
\frac{N}{1+(\bar m-1)\rho},
$$

where $N$ is raw events, $\bar m$ is average events per cohort, and $\rho$ is
intra-cohort correlation. A cohort block bootstrap supplies the reported interval; the
design-effect formula explains why the raw count overstates information.

Below the provisional threshold of 12 effective events, the raw average refuses to render. The shrunk
posterior can render at any $N$, but only as an interval with a base-rate verdict.

## What the evidence changes

The audit changes the termination discussion from “the manager has disappointed us” to
“what happened relative to the alternative we chose, under the bar we wrote down at the
time?” That is a stricter and more useful question.

It also preserves a likely negative finding. Goyal and Wahal found that sponsors hired
after strong trailing performance and fired after weak performance, yet fired managers
subsequently matched or beat replacements. The result supplies a zero-value-add prior,
not proof that any specific termination is wrong.

For a single allocator, the aggregate interval may remain indistinguishable from zero
through an entire career. That does not defeat the journal. The prospective discipline,
complete counterfactual roster, and event-level source records can improve governance without
pretending the committee has a statistically significant track record.

## What the allocator does next

1. Journal the thesis, horizon, kill criterion, and counterfactual before the vote.
2. Include hold-under-review decisions so the ledger keeps its control cases.
3. Preserve return coverage for fired managers or label any public proxy explicitly.
4. Review raw and factor-adjusted forward gaps at identical event-time horizons.
5. Use the base rate to calibrate the next decision, not to assign retrospective blame.

## Limits and go-live

The public decision history and manager names are permanently synthetic. A live internal
version requires a prospectively maintained decision journal and monthly net returns for
every manager touched by a decision, roster-wide. Strategy labels, risk-free returns,
and aligned factors support the counterfactual and factor-adjusted views.

The journal has no sample minimum; its discipline begins with the first record. A raw
aggregate appears only above 12 effective events and still requires an interval. Multiple decisions
inside one episode reduce effective $N$, often sharply. Missing forward months are not
interpolated; if a terminated manager stops reporting, any public strategy-index proxy
is visibly marked.

No regime splits, persistence rankings, or multiple-testing screens are supported. The
method's validation checks cohort-block interval coverage and whether a synthetic
trailing-performance allocator reproduces the zero-value-add base rate. A journal
reconstructed after outcomes are known fails the core go-live requirement because it
cannot remove hindsight bias.

## Key takeaways

- Journal decisions before outcomes, including holds that were seriously considered.
- Value-add is defined against the alternative passed over, not against cash by default.
- Cohort correlation can reduce a large-looking event count to a small effective sample.
- The aggregate is shrunk toward a zero-value-add reference-class prior and shown as an
  interval.
- The durable product is prospective decision discipline, not a committee leaderboard.

## References

- Amit Goyal and Sunil Wahal, “The Selection and Termination of Investment Management
  Firms by Plan Sponsors,” *Journal of Finance*, 2008.
- Daniel Kahneman, *Thinking, Fast and Slow*, 2011.
- Michael Mauboussin, *The Success Equation*, 2012.
- Berkeley Dietvorst, Joseph Simmons, and Cade Massey, “Overcoming Algorithm Aversion,”
  *Management Science*, 2018.
