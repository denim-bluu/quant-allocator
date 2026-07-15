## The decision

Diversification is not established by having several manager names on a roster. It is a
claim about whether those managers own different risks—and whether they can exit those
risks without selling into one another.

The allocator should measure holdings overlap directly, then re-express the shared
positions in unwind space. The resulting overlap and days-of-volume figures are
point-in-time measurements. A loss estimate is different: until predictive validation
clears, the common-holder unwind is a **scenario**, not a forecast, and it cannot support
an automatic size cap or redemption.

## Why the obvious answer fails

Manager return correlations are both late and noisy. At 36–60 monthly observations,
pairwise correlations can move sharply with a few shared months. More importantly, they
reveal common risk after it has appeared in returns. By then the crowd may already be
trying to leave.

Strategy labels are weaker still. An event-driven manager and an equity long/short
manager can hold the same names. A label describes a process; it does not prove an
independent book.

Raw dollar overlap improves on both, but treats a shared mega-cap and a shared thin name
as equally dangerous. Crowding becomes costly through the exit. The relevant question
is not only “how much do we hold together?” but “how much of our combined unwind time is
concentrated in the same names?”

## The intuition

Lay two gross-normalized books over the same security list. In each name held in the
same direction, shade the smaller of the two weights. Adding those shaded pieces gives
the fraction of book the managers literally share.

Next, replace each position's dollar weight with its days to exit. A small but illiquid
shared position expands; a large liquid one contracts. Recompute the shaded overlap in
that unwind-time space.

Finally, stop looking at managers in pairs. For each crowded name, add every manager's
dollar position and divide by stressed market volume. The result answers a joint-event
question: if the common holders all sold, how many days of stressed volume would their
combined footprint represent?

## A small numerical example

Take two long-only managers over five names, with absolute weights summing to one:

$$
w^A=(0.40,0.30,0.20,0.10,0.00),
$$

$$
w^B=(0.15,0.00,0.10,0.10,0.65).
$$

The common-weight overlap adds the smaller weight in every shared name:

$$
O_{AB}=0.15+0+0.10+0.10+0=0.35.
$$

So 35% of either gross-normalized book is common. The cosine companion is

$$
\cos(w^A,w^B)=
\frac{w^A\cdot w^B}{\lVert w^A\rVert\lVert w^B\rVert}
=\frac{0.09}{0.548\times0.682}\approx0.24.
$$

The two measures differ for a reason. Common weight answers “what fraction is shared?”
Cosine answers “how aligned are the complete directional books?” Manager B's large
position in name 5, which A does not own, pulls the cosine down without changing the
35% shared area.

Now suppose one of the shared names is hard to trade. Even if its dollar weight is only
0.10 in each book, it can dominate both managers' unwind time. Raw overlap remains 35%,
while liquidity-adjusted overlap can be much higher. That change is not an estimate of
future loss; it is a different measurement of what is common.

## The method

Let $w^a_n$ be manager $a$'s signed weight in security $n$, normalized so
$\sum_n|w^a_n|=1$. Directional common-weight overlap is

$$
O_{ab}=\sum_n\min(|w^a_n|,|w^b_n|)
\mathbb{1}\{\operatorname{sign}(w^a_n)=\operatorname{sign}(w^b_n)\}.
$$

The indicator matters. A long position for one manager and a short position for the
other is an offset, not a crowd. $O_{ab}$ ranges from zero for disjoint books to one for
identical gross-normalized books.

For a dollar position $D^a_n$ and dollar average daily volume $\operatorname{ADV}_n$,
days to cover at participation limit $\phi$ are

$$
\operatorname{DTC}^a_n=
\frac{|D^a_n|}{\phi\operatorname{ADV}_n}.
$$

The current specification provisionally sets $\phi=0.20$. Convert each book into signed shares
of total unwind time,

$$
s^a_n=\operatorname{sign}(D^a_n)
\frac{\operatorname{DTC}^a_n}{\sum_m\operatorname{DTC}^a_m},
$$

then apply the same overlap formula to $s^a$ and $s^b$. The result
$O^{\text{liq}}_{ab}$ is the shared fraction of unwind footprint.

For the roster-wide scenario, let $H_n$ be the managers crowded in the same direction
in name $n$. Their combined days of stressed volume are

$$
\operatorname{DoV}_n=
\frac{\sum_{a\in H_n}|D^a_n|}{\delta\operatorname{ADV}_n},
$$

where $\delta$ is stressed volume as a fraction of normal ADV, provisionally 0.5. This
is a footprint scenario. Turning it into dollars with a square-root impact coefficient
adds a model assumption, so any impact cost must be labelled illustrative rather than
predicted.

## What the evidence changes

Holdings overlap can show that two nominal diversifiers share a meaningful part of the
same book even when their return correlation and labels suggest independence. The
liquidity lens then identifies whether that common area is concentrated where exit is
slow.

The evidence supports a roster heat-map, a common-holder footprint, and a targeted
conversation about shared positions. It preserves the negative boundary: the measured
overlap has not, by itself, established that a stress loss will occur. Predictive loss
and a size-cap recommendation remain refused until a validation study shows that higher
measured overlap predicts larger simulated co-drawdown.

Returns-only data receive an even stronger refusal. They can support a descriptive
co-movement chip, not a holdings-crowding measurement and not an unwind scenario.

## What the allocator does next

1. Align holdings to a common security identity and valuation date.
2. Verify signs, gross normalization, AUM, ADV, and daily-volatility inputs.
3. Review raw and liquidity-adjusted overlap together; disagreement is informative.
4. Inspect the names driving the largest common-holder days-of-volume.
5. Use the result as monitoring and conversation material; pass any validated cap to
   the separate allocation process.

## Limits and go-live

The public roster and holdings are synthetic. The robust live rung requires position-
level holdings, signed weights or dollars, a shared security universe, per-name dollar
ADV, and daily volatility. There is no history-length requirement for the point-in-time
measurement.

Public 13F data provide a weaker rung for US long books, but the view is quarterly,
45 days delayed, longs-only, subject to non-public omission requests, and blind to
non-US holdings. It cannot be presented as a complete long/short crowding view. Exposure
summaries support only common factor tilts; returns support only descriptive clustering.

The 0.20 participation limit, 0.5 stressed-volume factor, 1.0 illustrative impact
coefficient, and 0.30 heat-map threshold are provisional calibration constants.
Sensitivity to the liquidity assumptions must be shown. If predictive validation fails,
the heat-map and days-of-volume remain as measurements while loss and size-cap language
are removed.

## Key takeaways

- Manager count and strategy labels do not establish diversification.
- Directional common-weight overlap measures the fraction of book literally shared.
- Liquidity-adjusted overlap asks whether the shared part is also hard to exit.
- Days-of-volume are a measured scenario input; impact loss is model-dependent.
- Prediction, allocation, and redemption remain outside the measurement until their
  separate gates clear.

## References

- Stephen Brown, Andrew Howard, and Christian Lundblad, “Crowded Trades and Tail Risk,”
  *Review of Financial Studies*, 2022.
- Amir Khandani and Andrew Lo, “What Happened to the Quants in August 2007?”,
  *Journal of Financial Markets*, 2011.
- J. Roger Bray and John Curtis, “An Ordination of the Upland Forest Communities of
  Southern Wisconsin,” 1957.
- Robert Almgren, Chee Thum, Emmanuel Hauptmann, and Hong Li, “Direct Estimation of
  Equity Market Impact,” 2005.
