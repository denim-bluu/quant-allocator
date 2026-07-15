## The decision

Use the Transparency Playground as a synthetic, precomputed teaching surface. It should demonstrate how track length and disclosure change the claims an allocator may honestly make, but it must never be interpreted as a finding about a real manager.

The page’s most important design choice is refusal to interpolate. Every dial snaps to one simulated setting. Moving a control selects a precomputed estimate, interval, verdict, and evidence-sufficiency state; it does not calculate a new statistic in the browser.

This playground is an advanced reference tool and communication device. Its outcome is understanding, not an operational manager decision.

## Why the obvious answer fails

A table of power numbers is accurate but inert. A slide saying “short track records are unreliable” asks the audience to trust a cautionary slogan. Neither makes the uncertainty mechanism visible.

A smooth interactive slider looks more persuasive but is less honest. If the atlas simulated only discrete settings, a value between two settings has no measured cell. Drawing an interpolated estimate would create precision the study never produced and present it with the same visual authority as an observed simulation result.

Live client-side statistics create another failure mode: the teaching page could disagree with the calibration study it is supposed to explain. The playground avoids that problem by carrying no estimator. It selects from the study's fixed table and shows the Monte Carlo uncertainty of the selected verdict.

## The intuition

Imagine a cabinet whose drawers are labelled by five settings: information coefficient, alpha half-life, sizing discipline, track length, and evidence level. The study fills every drawer offline. Each drawer contains an annualized-alpha estimate and interval, a Sharpe result, a verdict, and a statement of whether the available evidence is sufficient.

The interface opens one drawer at a time. A dial therefore has rungs, not a continuum. If a requested setting was not simulated, the control moves to the nearest measured rung.

This makes the lesson concrete: shorten the track and intervals widen; disclose measured exposures and beta uncertainty falls; reveal positions and new trade-level questions become possible, but only when enough independent trades have been observed.

## A small numerical example

The default synthetic state uses $IC=0.04$, alpha half-life $12$ months, sizing discipline $0.8$, track length $T=48$ months, and returns-only evidence.

Its annualized alpha estimate is $0.053$, or $5.3\%$, with a $95\%$ interval from $-0.0295$ to $+0.1249$. In percentage terms, the record supports roughly $-3.0\%$ to $+12.5\%$. The estimate is positive, but the interval crosses zero. The verdict is therefore **noise**: this evidence cannot separate positive skill from luck.

Now select $T=120$ months with measured exposure summaries, where exposures pin the betas. The precomputed alpha estimate is $0.0482$, with interval $+0.0018$ to $+0.0921$. The lower edge has moved above zero, so the verdict changes to **shrink**. The estimate is still not a declaration that the full headline effect is robust; it says the evidence supports a positive but smaller effect.

The manager’s simulated ground truth did not change between these drawers. The evidence did. More history reduced sampling uncertainty, and measured exposures reduced beta-estimation uncertainty. That before-and-after comparison is the teaching argument.

## The method

### Explain the dials without recomputing them

The skill dial follows the fundamental law

$$
IR\approx IC\sqrt{BR},
$$

where $IR$ is annual information ratio, $IC$ is per-bet forecast correlation, and $BR$ is independent breadth. Higher skill or breadth makes a real effect easier to distinguish from noise.

For an estimated Sharpe ratio $SR$ over $T$ independent monthly observations, a useful approximation is

$$
SE(SR)\approx
\sqrt{\frac{1+SR^2/2}{T}}.
$$

$SE(SR)$ is the sampling standard error. The key term is $1/\sqrt{T}$: halving uncertainty requires roughly four times the history. Autocorrelation can make the simple approximation too optimistic, which is why the playground renders the offline atlas result rather than relying on this browser-side formula.

### Show uncertainty in the power estimate

Each drawer’s minimum-evidence decision relies on a power estimate $\widehat p$ from $n$ simulated managers. The Wilson $95\%$ half-width is

$$
\frac{z}{1+z^2/n}
\sqrt{
\frac{\widehat p(1-\widehat p)}{n}
+\frac{z^2}{4n^2}
},
$$

with $z=1.96$. This is uncertainty in the measured power—and therefore in the verdict based on that power—not a second interval around the manager’s alpha.

### Preserve what each evidence level means

- **Returns only** estimates factor betas from returns, adding uncertainty to alpha.
- **Exposure summaries** pin betas to measured exposures, narrowing the alpha interval.
- **Positions and trades** add trade-level hit-rate and sizing diagnostics, each requiring enough independent trades.

The starter grid has $5$ information-coefficient rungs, $3$ half-lives, $2$ sizing settings, $5$ track lengths, and $3$ evidence levels: $450$ exact settings. Each setting uses at least $500$ simulated managers. Values are rounded to $4$ significant figures and stored as precomputed study results.

Browser JavaScript selects the requested combination, repaints the known state, updates the URL, and announces the change. It does not estimate alpha, calculate power, interpolate, or decide whether evidence is sufficient.

## What the evidence changes

The default point estimate looks healthy, but the interval and verdict refuse a skill claim. At longer tenure and exposure transparency, the interval no longer includes zero and the verdict changes. The evidence permits a narrower positive claim; it does not show a change in underlying talent.

The interface also distinguishes missing evidence from a negative finding. With positions and trades, too few independent trades prevent hit-rate or sizing analysis. “Not enough data to estimate” is different from “no skill detected,” and both differ from a robust verdict.

When $IC=0$, detections are false alarms rather than power. The page labels that state explicitly so a high detection rate cannot masquerade as sensitivity.

## What the allocator does next

Use one instructed comparison rather than exploring the full grid without a question. Start at the $120$-month state with measured exposures; then reduce track length or evidence and ask which part of the conclusion disappears and why.

Read the point, interval, verdict, and evidence-sufficiency statement separately. A positive point inside an interval spanning zero remains unresolved. A verdict can also carry Monte Carlo uncertainty even when the displayed alpha interval appears narrow.

For any operational manager question, leave the playground. Consult the relevant method and its own data, provenance, and go-live requirements. The playground never supplies a manager-specific result.

## Limits and go-live

- The page stays synthetic forever. It has no live-manager data path and no operational readiness claim.
- Every value must trace to one precomputed simulated setting. Dials snap; interpolation and client-side estimators are prohibited.
- The synthetic disclosure is always visible, and the simulator must never be described as an operational manager finding.
- The starter grid uses at least $500$ simulated managers per setting. The full validation study uses at least $1{,}000$ and replaces the starter grid wholesale.
- The upgrade must report every cell whose verdict changes between versions. Silent replacement is prohibited.
- Grid validation checks approximate monotonicity in track length and skill up to Monte Carlo noise, size near $5\%$ at $IC=0$, interval containment of the displayed point, and consistent minimum-evidence decisions.
- Future updates require regeneration of the complete study grid. There is no real-data go-live event.

## Key takeaways

- The playground selects measured states; it does not estimate new ones.
- Snapping is an honesty rule, not a user-interface compromise.
- The same simulated manager can move from **noise** to **shrink** when the evidence becomes stronger.
- Track-length uncertainty falls with $1/\sqrt{T}$, not $1/T$.
- Exposure summaries demonstrate what measured exposures buy; positions and trades introduce trade-level minimum samples.
- The playground teaches how to read evidence and is never evidence about a real manager.

## References

- Grinold, Richard, and Ronald Kahn. *Active Portfolio Management*, on the fundamental law $IR\approx IC\sqrt{BR}$.
- Lo, Andrew W. “The Statistics of Sharpe Ratios.” *Financial Analysts Journal*, 2002.
