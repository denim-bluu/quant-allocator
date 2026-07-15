## The decision

Can monthly returns reveal whether a manager sizes conviction well or how quickly the
manager’s alpha decays? Those traits matter, but they are natively visible in positions
and trades. A returns-only claim needs to prove that enough of the process survives
aggregation into one monthly number.

The answer from the current public evidence is a refusal. The real-path pilot tested
six pre-committed signatures against two traits and produced **0 SHIP, 1 WEAK TELL,
and 11 NULL** results. The lone weak tell was significant in the direction opposite
to the mechanism declared before the run. It is an anomaly, not a usable classifier.

That pilot is not the confirmatory study. The confirmatory verdict remains unknown by
design until a fresh, pre-registered simulation grid, nuisance overlays, and untouched
seed are run. Even if one signature later ships, it can become only a weak prior nudge
after external validation. For an individual manager today, the operational verdict
is: **do not classify sizing discipline or alpha decay from monthly returns alone**.

## Why the obvious answer fails

A monthly manager return sums the outcomes of dozens of positions. Different signal
ages, conviction weights, factor moves, leverage choices, and idiosyncratic shocks are
compressed into one observation. The subtle texture created by sizing or decay can be
smaller than the noise floor.

The usual research workflow makes this worse. If an analyst tries many features,
windows, and directions, then reports the winner, some “tell” will appear by chance.
With six independent tests at 5% each, the probability that at least one false alarm
appears is

$$
1-0.95^6\approx26\%.
$$

The tests here are correlated, but the principle remains: scanning a family and
quoting the best member requires accounting for the scan.

An open-ended feature screen with false-discovery-rate control answers the wrong
question. This is not a setting where a tolerable fraction of many discoveries may be
false. One false operational tell is enough to poison manager selection. The method
therefore uses a small, frozen family and controls the probability of any false claim
across that family.

## The intuition

Monthly returns may contain faint fingerprints of hidden process.

A conviction-weighted book can have more variable effective breadth than an equal-
weighted book, potentially creating higher volatility-of-volatility or fatter tails.
A fast-decaying signal can front-load return, potentially making a rolling information
ratio trend downward. These mechanisms justify testing candidate signatures.

They do not justify trusting them. Staggered rebalancing mixes positions of many ages,
smearing decay at the book level. Market regimes, leverage changes, smoothing, and
option-like overlays can create the same autocorrelation, skew, kurtosis, or drawdown
shape without any difference in sizing or alpha decay.

Pre-registration converts those stories into predictions. The family, directions,
window lengths, simulation cells, test, usable-effect threshold, and verdict taxonomy
are fixed before the confirmatory run. A result that arrives in the wrong direction
cannot be relabeled after inspection. A null cannot be rescued by quietly adding a
seventh feature.

## A small numerical example

Suppose four disciplined-sizing synthetic managers have an excess-kurtosis signature
of $\{0.9,1.4,0.6,1.1\}$, while four equal-weight managers have
$\{0.3,0.8,-0.1,0.5\}$.

The area under the receiver-operating-characteristic curve, or AUC, asks how often a
random disciplined manager has the higher signature value than a random equal-weight
manager. There are $4\times4=16$ cross-class pairs.

The values 0.9, 1.4, 0.6, and 1.1 win 4, 4, 3, and 4 of their pairings. Therefore

$$
\widehat{\mathrm{AUC}}=\frac{4+4+3+4}{16}=\frac{15}{16}=0.9375.
$$

An AUC of 0.5 is blind; 1.0 separates the classes perfectly. This toy value is
intentionally obvious. In the pilot, the best stand-in signature reached only 0.605,
and the real-path pilot’s lone anomaly did not clear the registered direction and
usability rules.

The AUC is rank-based. A monotone rescaling of kurtosis changes none of the pair
orderings, so the analyst does not gain another opportunity to tune a raw cutoff after
seeing the data.

## The method

Two population contrasts are frozen. H-SIZE compares managers with sizing discipline
0.8 against otherwise identical managers at 0.0. H-DECAY compares a three-month alpha
half-life with a 36-month half-life. Each class contains managers generated under known
truth.

Six return-only signatures are pre-committed: lag-one autocorrelation, the coefficient
of variation of rolling six-month volatility, skewness, excess kurtosis, maximum-
drawdown shape scaled by $\hat\sigma\sqrt T$, and the time slope of rolling 12-month
information ratio. Only directions declared before the run can support a SHIP verdict.

For signature values $s_i^+$ and $s_j^-$ in positive and negative classes, the
Mann–Whitney AUC is

$$
\widehat A=\frac{1}{n_+n_-}\sum_{i=1}^{n_+}\sum_{j=1}^{n_-}
\left[\mathbf 1(s_i^+>s_j^-)+\frac12\mathbf 1(s_i^+=s_j^-)\right].
$$

$n_+$ and $n_-$ are class sizes and ties count half. At 500 managers per class, the
null standard error is approximately

$$
\mathrm{SE}_0(\widehat A)=
\sqrt{\frac{n_++n_-+1}{12n_+n_-}}
=\sqrt{\frac{1001}{3{,}000{,}000}}\approx0.0183.
$$

This makes the usable threshold of AUC 0.65 about 8.2 null standard errors above
blind. A practically usable signal should not be missed at this replication count.

Familywise significance is assessed with a Westfall–Young max-statistic permutation.
Labels are shuffled, all six AUCs are recomputed, and the largest absolute deviation
from 0.5 is recorded. Repeating that scan 5,000 times constructs the null distribution
of the best result one would obtain merely because six correlated signatures were
inspected.

Shipping requires two conditions in every deciding cell:

$$
\min_c\widehat A^{\mathrm{dir}}_{j,c}>0.65
\quad\text{and}\quad
\max_c\tilde p_{j,c}\le0.05.
$$

$\widehat A^{\mathrm{dir}}_{j,c}$ is signature $j$’s AUC oriented to its declared
direction in cell $c$, and $\tilde p_{j,c}$ is its familywise-adjusted p-value. A
statistically real effect below 0.65 is a WEAK TELL. Failure of familywise significance
in any deciding cell is NULL. Significance and usability are separate claims.

## What the evidence changes

The pilot changes the practical answer more than a speculative positive would. It
shows that the protocol can detect a real deviation, reject its promotion when the
direction is wrong, and publish nulls with the same standing as a discovery.

The real-path pilot used a bounded grid, 150 managers per class, 2,000 permutations,
and a smoothing stress. It found zero signatures eligible to ship. The sole weak tell
was drawdown shape under H-SIZE: familywise-adjusted $p\approx0.007$, but disciplined-
sizing books showed shallower rather than deeper normalized drawdowns, opposite to the
frozen positive direction. A post-hoc analysis could have marketed the reversal. The
registered analysis records it as an anomaly requiring a new version and fresh seed
before any contrary mechanism is tested.

The result is still labeled PILOT. The full confirmatory run will use 500 managers per
class per cell, 12 H-SIZE deciding cells, 8 H-DECAY cells, 5,000 permutations, a
60-month deciding horizon, and both smoothing and written-put stresses. Its outcome is
not inferred from the pilot.

## What the allocator does next

1. Keep the individual-manager verdict at refusal: returns alone do not support an
   operational sizing or decay classification.
2. Use the pilot as a demonstration of protocol behavior, not as the confirmatory
   result.
3. Freeze the final registration, including the untouched confirmatory seed, before
   running any deciding cell.
4. Run null-size and planted-effect positive controls before interpreting the registered
   grid.
5. Publish every SHIP, WEAK TELL, and NULL as registered, including overlay failures.
6. If anything ships, validate it on transparent managers whose exposures, positions,
   or trades provide independent truth labels before showing a roster-facing chip.

## Limits and go-live

- **Evidence status.** The public counts are pilot evidence. The confirmatory outcome
  remains unknown until the pre-registered run completes.
- **Data ask.** The confirmatory study needs no external data; it is fully synthetic
  and uses monthly returns by construction. Exposure and position data enter later as
  external-validation labels only.
- **Sample.** The registered grid uses **500 managers per class per cell**. A live use
  observes one manager, so even a shipped AUC is only a weak prior nudge.
- **Interpretation.** AUC 0.65 means a random cross-class pair is ordered correctly
  about two times in three. It is not a probability that a particular manager belongs
  to either class.
- **Power floor.** Effects below about AUC 0.55 can return NULL because of limited
  resolution. The publishable negative is therefore bounded: no candidate reaches a
  usable 0.65 across the deciding grid, and sub-0.55 whispers are operationally
  irrelevant.
- **Confounds.** Return smoothing, leverage changes, volatility regimes, option-like
  overlays, AUM growth, and one dominant drawdown can mimic the candidate signatures.
- **Protocol integrity.** Peeking at the confirmatory seed, changing a window, or moving
  a threshold voids the run. A changed hypothesis requires version two and a new seed.
- **Decision ceiling.** Even a SHIP result remains a conversation prompt after external
  validation. It never becomes a manager score, rank, or standalone screen.

## Key takeaways

- Monthly returns are a highly aggregated and confounded view of sizing and decay.
- A pre-registered family makes both positive and null results credible.
- Familywise control asks whether a result survives having inspected all six
  signatures.
- Statistical significance below the AUC 0.65 usability bar is a weak tell, not a
  product.
- The pilot found 0 SHIP, 1 direction-reversed WEAK TELL, and 11 NULL results.
- Until confirmatory and external-validation gates pass, individual-manager
  classification is refused.

## References

- Brian Nosek, Charles Ebersole, Alexander DeHaven, and David Mellor, “The
  Preregistration Revolution,” *Proceedings of the National Academy of Sciences*,
  2018.
- Peter Westfall and S. Stanley Young, *Resampling-Based Multiple Testing*, 1993.
- James Hanley and Barbara McNeil, “The Meaning and Use of the Area under a Receiver
  Operating Characteristic Curve,” *Radiology*, 1982.
- Mila Getmansky, Andrew Lo, and Igor Makarov, “An Econometric Model of Serial
  Correlation and Illiquidity in Hedge Fund Returns,” *Journal of Financial
  Economics*, 2004.
- Rick Di Mascio, Anton Lines, and Narayan Naik, “Alpha Decay,” working paper, 2017.
