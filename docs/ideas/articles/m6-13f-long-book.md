## The decision

Form 13F offers a free quarterly view of a manager's reported US long book. It can
support precise descriptions of the **visible filing**: concentration, effective
breadth, quarters-held, and peer overlap.

It cannot support a claim about the complete fund without confronting what the filing
omits. The view is delayed, longs-only, US-focused, and subject to non-public omission
requests and option-value distortions. The allocator should use it for monitoring and
engagement, with a coverage gate that refuses concentration or overlap when the visible
crop is too small.

## Why the obvious answer fails

Reading one filing as a static “what they own” list underuses the data. Lining up
quarters can reveal whether reported positions persist while the book concentrates.

Treating the same filings as a complete portfolio overreaches. A market-neutral manager
can look like a concentrated long-only investor because the shorts are absent. Foreign
holdings, swaps, non-reportable securities, and non-public positions may also be
missing. A concentration statistic can be exact for the filing and badly wrong for the
fund.

Copycat-return or alpha claims add another unsupported step. A filing can arrive up to
45 days after quarter end, by which time the manager may have traded. The method here
does not predict returns. It measures the reported crop and makes its blindness visible.

## The intuition

Treat a 13F as a redacted photograph developed six weeks late. First label the crop:
which positions are eligible, long, and visible? Then normalize the visible market
values into a reported long-book vector.

Across one filing, measure how much sits in the largest positions and how many equal-
weight names would create the same concentration. Across several filings, count how
many consecutive quarters today's top names have appeared. Across filers, compare the
angles between reported holdings vectors.

Finally ask whether the photograph covers enough of the real long book to justify those
descriptions. If it does not, refusal is more informative than an exact calculation on
an unrepresentative fragment.

## A small numerical example

Suppose a synthetic filer begins with five equal reported longs:

$$
(0.20,0.20,0.20,0.20,0.20).
$$

Six quarters later the reported shares are

$$
(0.684,0.158,0.079,0.053,0.026).
$$

Top-three weight rises from

$$
0.20+0.20+0.20=0.600
$$

to

$$
0.684+0.158+0.079=0.921.
$$

The Herfindahl index, the sum of squared shares, rises from 0.200 to 0.503. Effective
breadth is its inverse, so it falls from $1/0.200=5.00$ to approximately
$1/0.503=1.99$. The visible book changed from five equal positions to the concentration
equivalent of roughly two equal positions.

If the same top three names appeared in all six filings, the change is concentration
among persistent reported holdings rather than rotation into new names. That is a
specific meeting question, not a forecast.

Coverage determines whether the result can be generalized. A visible crop covering
90.5% of the true synthetic long weight can pass a provisional 60% gate. A second crop
covering only 20% must refuse the concentration verdict even though its filing-level
arithmetic is exact.

## The method

Let $w_{n,m(q)}$ be the signed portfolio weight in security $n$ at quarter-end month
$m(q)$, and let $\mathcal E$ be the set of 13(f)-eligible securities. The reported
long-book share is

$$
v_n^{(q)}=
\frac{\mathbb{1}[n\in\mathcal E]\max(w_{n,m(q)},0)}
{\sum_k\mathbb{1}[k\in\mathcal E]\max(w_{k,m(q)},0)}.
$$

The indicator removes ineligible names; $\max(w,0)$ removes shorts; the denominator
renormalizes visible longs to sum to one. The output is exact for the reported crop.

For filing $q$, top-$N$ concentration, Herfindahl concentration, and effective breadth
are

$$
C_N^{(q)}=\sum_{n\in\operatorname{top-}N(v^{(q)})}v_n^{(q)},\qquad
H^{(q)}=\sum_n(v_n^{(q)})^2,\qquad
N_{\text{eff}}^{(q)}=\frac{1}{H^{(q)}}.
$$

Reported-holding persistence is a consecutive-quarter count. For a current top name
$n$, $\operatorname{QH}_n$ is the longest unbroken run ending now for which the name's
reported share is positive. It is not an entry-dated tenure estimate and never becomes
an alpha-decay half-life.

Peer overlap between reported books $i$ and $j$ is the cosine

$$
O_{ij}=
\frac{\sum_n v_n^{(i)}v_n^{(j)}}
{\sqrt{\sum_n(v_n^{(i)})^2}\sqrt{\sum_n(v_n^{(j)})^2}}.
$$

It is a descriptor, not a crowding cap. Allocation and unwind decisions belong to the
separate crowding and sizing methods.

In synthetic or transparent data, coverage can be measured as

$$
\rho_i^{(q)}=
\frac{\sum_n\mathbb{1}[n\in\mathcal E]\max(w_n^{(i)},0)}
{\sum_n\max(w_n^{(i)},0)}.
$$

Live 13F data do not reveal the denominator, so live coverage is inferred from
additional disclosures, amendments, and option share. That makes coverage an uncertain
input even though the filing descriptors are deterministic.

## What the evidence changes

Quarterly panels can show that a reported long book is concentrating, diversifying, or
retaining the same top positions. Those are sourced public facts with as-of and known-at
dates. They support better questions than a one-off holdings list.

The method preserves several negative findings. Reported persistence is not alpha
persistence. Peer overlap is not a size cap. Concentration is not return prediction.
The short-interest lens remains unplayed until a real FINRA and ADV adapter exists.

Most importantly, an exact filing statistic does not override low coverage. The
coverage warning replaces the verdict when the public crop is likely to misrepresent
the book.

## What the allocator does next

1. Verify the filer, amendment chain, quarter-end as-of date, and filing known-at date.
2. Resolve security identity, eligibility, values, and option lines before normalizing.
3. Read concentration and persistence as reported-long descriptors only.
4. Compare quarters and prepare a sourced question about material change.
5. Seek fuller positions or exposure summaries when coverage is uncertain or refused.

## Limits and go-live

The public example uses synthetic filers. Live use requires versioned SEC EDGAR Form
13F filings, a 13(f)-eligibility reference, and a value-to-shares source. A single filing
supports a snapshot; several quarters are required for persistence and trajectory.

The filing may be 45 days stale, includes longs but not shorts, can omit non-public or
non-US positions, and can misstate economic exposure through option values. In the
current v1 rule, option lines are excluded from share calculations and a filer is
provisionally flagged option-heavy when option value exceeds 10% of reported value.

The provisional coverage threshold is 0.60. Below it, concentration and overlap refuse.
Because live coverage is inferred rather than observed, the inference recipe and its
conservatism require validation. If most target filers fail coverage, the public product
becomes a caveat-and-refusal instrument rather than publishing misleading numbers.

No filing implying a relationship with the allocator, or any real decision context, belongs in the public artifact.
Only public filings of unaffiliated managers and synthetic examples are in scope.

## Key takeaways

- A 13F is a delayed, longs-only crop, not the whole fund.
- Concentration and effective breadth are exact measurements of the visible crop.
- Quarters-held is a coarse survival count, not an alpha-decay estimate.
- Peer overlap describes public long books; it does not allocate capital.
- Coverage is the load-bearing gate, and refusal is the correct output when the crop is
  too small.

## References

- John Griffin and Jin Xu, “How Smart Are the Smart Guys? A Unique View from Hedge Fund
  Stock Holdings,” *Review of Financial Studies*, 2009.
- Vikas Agarwal, Wei Jiang, Yuehua Tang, and Baozhong Yang, “Uncovering Hedge Fund Skill
  from the Portfolio Holdings They Hide,” *Journal of Finance*, 2013.
- Marno Verbeek and Yu Wang, “Better than the Original? The Relative Success of Copycat
  Funds,” *Journal of Banking & Finance*, 2013.
- Marcin Kacperczyk, Clemens Sialm, and Lu Zheng, “On the Industry Concentration of
  Actively Managed Equity Mutual Funds,” *Journal of Finance*, 2005.
