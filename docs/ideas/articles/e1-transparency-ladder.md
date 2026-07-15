## The decision

When an analysis needs richer manager data, the allocator should not begin with the data request. It should begin with the decision question that the current evidence cannot answer, then pair the smallest necessary ask with something useful the manager receives in return.

That produces a three-rung transparency ladder: monthly net returns, then exposure summaries, then positions and trade dates. The rule is one rung per relationship conversation. A refusal is recorded and respected; it is not a negative investment signal.

The ladder is a negotiation playbook, not an estimator. Its output is a defensible next ask—or a refusal to ask when no shared question or reciprocal purpose has been stated.

## Why the obvious answer fails

The obvious approach is to request everything that could improve the analysis. Framed as verification—“send positions so we can check the portfolio”—that request makes transparency sound like surveillance.

The risk is not merely an uncomfortable meeting. Research on the hidden costs of control shows that visible control can signal distrust and reduce voluntary cooperation. In an allocator relationship, the manager may respond by narrowing or withdrawing the exposure and position detail on which later analysis depends. The attempt to extract more evidence can destroy the evidence supply.

A second failure is statistical. “More data would be useful” is too vague to justify a sensitive ask. The manager should be able to see the exact question that returns cannot resolve, why exposures or positions would resolve it better, and what analysis will be returned. Without that chain, the ask is an assertion of entitlement rather than a joint investigation.

Finally, transparency depth must not become a quota. A target such as “all managers at the position tier” rewards extraction, not trust. Grant survival is a relationship health check; it is not a score to maximize.

## The intuition

Every rung is a triple:

1. **The ask:** a specific data type, format, cadence, and acceptable lag.
2. **The reciprocity:** an adjustable diagnostic the manager receives back.
3. **The power justification:** the decision question the present tier cannot answer honestly.

At the first rung, monthly net returns support an uncertainty-honest tear sheet. At the second, monthly factor, sector, gross, and net exposure summaries help separate style from skill and support drift review. At the third, positions and trade dates make sizing and exit-timing questions observable.

The statistical refusal does useful relationship work. “The returns-only interval cannot distinguish alpha from style at this track length” is a reason for a focused exposure ask. “We need more transparency” is not.

## A small numerical example

Suppose a manager has a true annual alpha of $3\%$ and annual tracking error of $6\%$. The true annual information ratio is therefore

$$
IR=\frac{3\%}{6\%}=0.5.
$$

With five years of observations, the approximate standard error of annual alpha is

$$
SE(\widehat{\alpha})\approx\frac{6\%}{\sqrt{5}}\approx 2.7\%.
$$

Here $\widehat{\alpha}$ is estimated annual alpha, and the square-root term captures how slowly sampling uncertainty falls. A rough two-standard-error range is

$$
3\%\pm 2(2.7\%)\approx[-2.4\%,+8.4\%].
$$

The manager is genuinely skilled in this constructed example, yet the observed record remains compatible with no alpha. The estimate is positive; the interval refuses the skill verdict.

For $T=60$ monthly observations, the expected alpha test statistic is approximately

$$
t\approx IR\sqrt{\frac{T}{12}}
=0.5\sqrt{5}\approx1.1.
$$

That is only about $20\%$ power—below the roughly $30\%$ upper bound used in the doctrine. In repeated samples from equally skilled managers, the returns-only test would identify skill only about one time in five. The appropriate next conversation is therefore not “prove your alpha.” It is “could monthly measured exposures help us separate persistent style from residual skill?”

## The method

### Rung 1: monthly returns

Ask for timely monthly net-of-fee returns. In return, provide an uncertainty-honest tear sheet that shows estimates, intervals, and refusals at the manager’s actual track length. This is the default rung because it permits basic performance and factor-mix questions without claiming that a short record proves skill.

### Rung 2: exposure summaries

Ask for monthly factor, sector, gross, and net exposure buckets in an Open Protocol-aligned format. The reciprocal artifact is a factor-hygiene and drift review that the manager can inspect and challenge.

The power justification is beta uncertainty. When factor exposures must be inferred from returns, uncertainty in the loadings spills into the alpha estimate. Measured exposures pin those loadings more tightly and can narrow the alpha interval. The ask is thus tied to a shared question: how much of the track record is style, and how much remains after style is accounted for?

### Rung 3: positions and trade dates

Ask for position files, ideally with trade dates; quarterly lag is acceptable. The reciprocal outputs are adjustable sizing and exit-timing diagnostics.

The relevant sample is now independent trades, not months. To distinguish a $55\%$ hit rate from a $50\%$ coin flip at $80\%$ power with a two-sided $5\%$ test, the approximation is

$$
N\approx
\frac{(1.96+0.84)^2\,0.25}{0.05^2}
\approx780.
$$

$N$ is the number of independent trades; $1.96$ is the two-sided $5\%$ critical value, $0.84$ supplies $80\%$ power, $0.25$ is the variance near an even hit rate, and $0.05$ is the five-point edge. A concentrated 30-name book does not clear that bar in five years; a high-turnover book may clear it in one to two. Below the bar, the analysis refuses rather than printing a fragile batting average.

Across all rungs, four rules apply: state the shared question, show the manager every analysis computed on the granted data, make the ask reciprocal and contractual, and respect a decline without punishment.

## What the evidence changes

The ladder changes transparency from a character judgement into an evidence decision. A wide alpha interval does not imply a weak manager; it establishes that returns alone cannot support the desired conclusion. A closed trade-level power gate does not imply poor sizing; it establishes that the effective sample is insufficient.

The output is therefore a verdict about the next conversation:

- **Ask for exposures** when measured betas address a stated skill-versus-style question.
- **Ask for positions** when trade-level breadth is the missing quantity and the diagnostic can be returned in a useful form.
- **Refuse to escalate** when no decision question, reciprocal artifact, or defensible use has been identified.

## What the allocator does next

Before the meeting, write the question in one sentence and identify the current evidence right. Choose only the next rung. Prepare the reciprocal artifact before asking, including the assumptions or thresholds the manager may adjust.

During the meeting, use the power justification in plain language, explain who will see the data and every analysis derived from it, and agree the format, cadence, lag, and use contract. If the manager declines, record the decision and continue the relationship without treating the decline as a redeem trigger.

Afterward, monitor whether the grant persists once the first diagnostic is returned. Track accepted and declined asks and any post-analysis withdrawal, but do not turn rung depth into a performance target.

## Limits and go-live

This article describes doctrine; it consumes no manager data and has no estimator sample threshold.

- Publication must remain generic: no real manager names, allocator-specific process details, or undisclosed internal thresholds.
- The reciprocal artifacts must exist at least in demonstrable form before an allocator promises them. Otherwise reciprocity is vaporware.
- Rung 1 requires monthly net returns. Rung 2 describes monthly Open Protocol-aligned exposure summaries. Rung 3 describes positions, ideally with trade dates, with quarterly lag acceptable.
- The arithmetic justifies when evidence is too thin; it does not compel a manager to grant access.
- The research on control, advice, and algorithm aversion supports the framing, not a guaranteed relationship outcome in every context.
- Grant survival and escalation acceptance are qualitative validation signals. They must not become quotas.

## Key takeaways

- Ask for the smallest evidence increment that answers a stated decision question.
- Pair every ask with an adjustable, useful diagnostic the manager receives back.
- Five years of returns can leave a real $IR=0.5$ manager statistically unresolved.
- Position-level hit-rate questions can require roughly 780 independent trades.
- A decline is respected, not punished; transparency is granted, not owed.
- The ladder governs engagement. It does not rank managers or authorize investment action.

## References

- Falk, Armin, and Michael Kosfeld. “The Hidden Costs of Control.” *American Economic Review*, 2006.
- Dietvorst, Berkeley J., Joseph P. Simmons, and Cade Massey. “Overcoming Algorithm Aversion.” *Management Science*, 2018.
- Bonaccio, Silvia, and Reeshad S. Dalal. Review of advice-taking research, 2006.
- Goyal, Amit, and Sunil Wahal. Study of institutional manager hiring and firing, 2008.
- Pástor and Stambaugh, on using factor information to tighten inference about manager alpha.
- Open Protocol and AIMA separately managed account guidance on standardized, collaborative transparency.
