## The decision

The allocator needs one book-level factor view even though managers provide unequal
transparency. A holdings-derived beta, a disclosed risk bucket, and a returns-inferred
beta cannot be added as if they carried the same precision.

The proposed solution is a measurement-error model that fuses each sleeve at the
precision its data tier earns and returns a book exposure interval plus provenance for
the remaining uncertainty. But the current method is **redesign-required**, not
decision-ready: the tier-error rows and joint multi-factor covariance needed to license
the fused view are not calibrated. Until they are, the honest product is a reconciliation
table with tier-specific bands, not a single posterior presented as settled fact.

## Why the obvious answer fails

A capital-weighted average of point betas hides that some inputs are near measurements
and others are noisy estimates. The resulting book number looks precise because the
uncertainty was discarded, not because the book is well known.

Dropping opaque managers is not a solution. It can leave the view describing only a
minority of capital. Re-estimating every manager from returns makes the opposite error:
it throws away holdings and disclosed exposures, reducing the whole roster to the
noisiest tier.

A fusion model with invented tier noise is equally unacceptable. Precision weighting
is only as honest as its measurement-error inputs. If the returns, exposure, and
holdings error variances have not been calibrated on common ground truth, the interval
width is a design choice wearing statistical notation.

## The intuition

Picture each manager's beta behind glass. Holdings make the glass nearly clear,
exposure buckets frost it, and returns-only inference leaves it foggy. The model should
not average the legibility of the cards. It should give each manager's observation the
weight justified by that manager's glass.

After estimating each sleeve, aggregate by capital. Book uncertainty becomes a sum of
squared capital-weighted sleeve uncertainties, so large opaque sleeves dominate. That
decomposition is useful in its own right: it names where an additional transparency ask
would most tighten the book view.

In a live temporal model, the glass also ages. A holdings snapshot can be precise on its
date and less informative each month after, because exposure can drift. A Kalman filter
widens uncertainty between observations and tightens it when a new reading arrives.

## A small numerical example

Take three equal-weight managers and a weak prior beta of 0.20 with standard deviation
0.50. Their observed betas are 0.30 from holdings, 0.50 from exposure buckets, and 0.20
from returns. Use the demonstration's **provisional** measurement standard deviations

$$
r_P=0.02,\qquad r_E=0.08,\qquad r_R=0.25.
$$

The resulting posterior standard deviations are approximately 0.0200, 0.0790, and
0.2236. The returns-only sleeve remains much less certain.

The posterior means are approximately 0.300, 0.493, and 0.200, so book beta is

$$
B=\frac{0.300+0.493+0.200}{3}=0.331.
$$

Under the example's independence assumption, book variance is

$$
\operatorname{Var}(B)=
\frac{0.0200^2+0.0790^2+0.2236^2}{9}=0.006293.
$$

The standard deviation is 0.0793, giving a 90% interval half-width of
$1.645\times0.0793=0.130$:

$$
B=0.331\pm0.130\quad(90\%).
$$

The returns-only manager contributes 88.3% of the sum of sleeve variances. Upgrading
that one observation to the exposure tier would reduce book standard deviation to
0.0378, 52% tighter; holdings precision would reduce it to 0.0280, 65% tighter.

This is a teaching calculation on provisional error values. It demonstrates the
mechanism, not current live calibration.

## The method

For manager $i$ and factor $j$, let $x_{i,t}$ be the latent true exposure at month $t$.
A simple state evolution is

$$
x_{i,t}=x_{i,t-1}+d_{i,t}+w_{i,t},
\qquad w_{i,t}\sim\mathcal N(0,q_i^2).
$$

$d_{i,t}$ is a measured drift term when the exposure-drift method supports one;
$w_{i,t}$ is ordinary exposure wander; and $q_i$ controls how quickly an old reading
loses precision.

At transparency tier $\tau\in\{R,E,P\}$, observe

$$
y_{i,t}^{\tau}=x_{i,t}+v_{i,t}^{\tau},
\qquad v_{i,t}^{\tau}\sim\mathcal N(0,r_\tau^2).
$$

$y_{i,t}^{\tau}$ is the returns-inferred, exposure-disclosed, or holdings-derived
reading. $r_\tau$ is that tier's calibrated measurement error. The model requires
$r_P<r_E<r_R$, but the ordering alone is insufficient; the magnitudes determine the
claimed interval.

The Kalman predict and update steps are

$$
\widehat x_t^-=\widehat x_{t-1}+d_t,
\qquad P_t^-=P_{t-1}+q^2,
$$

$$
K_t=\frac{P_t^-}{P_t^-+r_\tau^2},
\qquad
\widehat x_t=\widehat x_t^-+K_t(y_t-\widehat x_t^-),
\qquad
P_t=(1-K_t)P_t^-.
$$

$P_t$ is posterior variance and $K_t$ is the weight placed on the new observation. A
precise tier has small $r_\tau$ and a gain near one. With no observation, only the
predict step runs and uncertainty grows.

For capital weights $c_i$, book exposure and variance are

$$
\mathbb E[B_t]=\sum_ic_i\widehat x_{i,t},
\qquad
\operatorname{Var}(B_t)=\sum_ic_i^2P_{i,t}.
$$

The second formula assumes manager exposure errors are conditionally independent. A
joint multi-factor and cross-manager treatment would add covariance terms. Crowding and
overlap belong to the holdings-overlap method, not to an unlabelled patch inside this
model.

## What the evidence changes

The toy example shows why transparency should affect both the book estimate and its
uncertainty. It also shows why provenance is decision-relevant: one large opaque sleeve
can account for most of the band width.

What the current evidence does **not** change is equally important. The current design
uses provisional tier errors of 0.02, 0.08, and 0.25 pending the exposure-measurement
rows. A 20% reduction in band width is the provisional minimum information-gain gate,
but it has not licensed a general live claim. Joint multi-factor modality-quality error
is also uncalibrated.

Therefore the current verdict is refusal: do not present one fused book interval as
decision-ready. Present each sleeve's tier, reading, and band in a reconciliation table
until calibration and stability gates pass.

## What the allocator does next

1. Produce common-ground-truth measurement-error rows for returns, exposures, and
   holdings.
2. Calibrate exposure-bucket coarsening and joint multi-factor error rather than assuming
   factor independence.
3. Test 90% band coverage, provenance faithfulness, tier monotonicity, and roster-order
   invariance.
4. Start with a two-tier returns-plus-exposure prototype before adding holdings cadence.
5. Keep sizing with the allocation method and overlap with the crowding method.

## Limits and go-live

The public calculation is synthetic and uses provisional constants. A live book view
needs monthly returns and factor sets for all managers, exposure buckets where disclosed,
dated holdings where available, capital weights, and calibrated modality-quality and
joint-risk inputs.

Any tier mix can be listed honestly at any $T$. The **fusion claim** requires calibrated
tier-error rows and empirical coverage within five percentage points of the nominal 90%
band. Moving a sleeve from returns to exposures to holdings must never widen the book
band. The information-gain interval must exclude zero and exceed the provisional 20%
floor.

If information gain fails, the filter is unstable at roster scale, or joint covariance
remains unsupported, the fallback is mandatory: tier-specific manager rows and an
un-fused capital-weighted sum labelled as such. P2 measures exposure; it does not produce
weights, trades, crowding estimates, or automatic actions.

## Key takeaways

- Mixed-transparency exposures cannot be added as equally precise points.
- A valid fusion needs empirically calibrated error for every modality.
- Large opaque sleeves dominate book uncertainty through $c_i^2P_i$.
- The Kalman filter explains how uncertainty grows between disclosures and shrinks when
  evidence arrives.
- The current method is redesign-required; the reconciliation table is the honest
  output until the missing gates clear.

## References

- Rudolf Kalman, “A New Approach to Linear Filtering and Prediction Problems,” 1960.
- James Durbin and Siem Jan Koopman, *Time Series Analysis by State Space Methods*,
  2nd ed.
- Wayne Fuller, *Measurement Error Models*, 1987.
- Andrew Gelman, John Carlin, Hal Stern, David Dunson, Aki Vehtari, and Donald Rubin,
  *Bayesian Data Analysis*, 3rd ed.
- Open Protocol Enabling Technology / AIMA risk-reporting template.
