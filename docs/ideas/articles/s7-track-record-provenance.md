## The decision

Before an allocator estimates performance, the history itself has to be admissible.
Are all observations attached to the correct vehicle and composite? Were they known at
the decision date? Do the fee, currency, benchmark, calendar, valuation, and membership
bases match? Does a predecessor record actually belong to the current team and process?

The track-record provenance inspector answers those questions before any alpha,
Sharpe, IRR, PME, skill estimate, or manager rank is attempted. It admits an
observation only when access, identity, membership, completeness, basis, and native
data modality all pass. A zero on any gate produces an exclusion or refusal rather
than a silently repaired panel.

The resulting decision is deliberately prior to performance: either construct one
comparable native-frequency panel with a complete lineage and basis, or refuse the
panel and identify the exact missing evidence. The inspector never upgrades provenance evidence
into a claim that historical skill transferred.

## Why the obvious answer fails

A spreadsheet of dated returns looks ready for analysis even when its rows were not
knowable together. A later database can backfill an old return, revise a composite,
drop a dead product, or replace a preliminary NAV. Using the latest file to reconstruct
an earlier decision gives the analyst information the allocator did not have then.

Basis differences create a second trap. Gross and net returns are not interchangeable.
Local and base currency are not interchangeable. A monthly total return cannot be
stitched to an irregular private-market cash-flow record. A benchmark change or
composite-membership revision can split what looks like one continuous series into
separate economic segments.

Identity is equally load-bearing. A team member’s presence at two firms does not make
the predecessor entity’s track record portable. Nor can return rows define the
historical opportunity set: missing dead products and retroactive membership can make
an apparent selection universe look cleaner than the one actually available.

The naive answer is to normalize, stitch, and calculate. The correct answer is to
prove comparability first and leave incompatible observations separate.

## The intuition

Think of every observation as traveling with a passport.

The passport names the entity and lineage segment, source version, first-known time,
access right, native data kind, and full basis. An observation without one required
field is not “mostly comparable.” It is inadmissible for that proposed panel.

There are two clocks. The effective date says when the economic fact belongs. The
first-known date says when evidence of that fact became available. A return effective
in February but first published in May can appear in a latest-known history viewed in
June. It cannot be inserted into what was knowable in March.

There are also two views of revision. The analytic view can request the latest version
known by the cutoff. The audit view requests every version known by the same cutoff.
Keeping both prevents the final value from erasing the fact that the record changed.

## A small numerical example

Suppose a public-equity observation is a 0.60% local-currency return. The reconciled
early-cutoff output implies that the source-linked FX return used in the transformation is
2.00%. The only permitted transformation is multiplicative:

$$
1+R_t^{\mathrm{base}}
=(1+R_t^{\mathrm{local}})(1+R_t^{\mathrm{FX}}).
$$

Therefore

$$
R_t^{\mathrm{base}}=(1.006)(1.020)-1=0.02612000,
$$

or 2.612%. This is a deterministic transformed observation, not an estimate.

At a later cutoff, the local observation remains 0.60%; the reconciled output implies
that the source-linked FX series used in the transformation is now 1.80%. The same ruled
contract gives

$$
R_t^{\mathrm{base}}=(1.006)(1.018)-1=0.02410800,
$$

or 2.4108%. The early value must not be rewritten as though the later FX version had
always been known. Both the effective value and its first-known version belong in the
audit.

The same principle applies without currency conversion. In the synthetic states, a
hedge-fund February observation is 1.00% at the early cutoff and 0.80% at the latest;
a private-market March NAV moves from 85 million to 80 million. Those are vintage
findings, not performance verdicts.

## The method

For observation $o$, proposed native panel $p$, and decision cutoff $t$, admission is

$$
A(o,p,t)=
I_{\mathrm{right}}
I_{\mathrm{identity}}
I_{\mathrm{membership}}
I_{\mathrm{complete}}
I_{\mathrm{basis}}
I_{\mathrm{modality}}
\in\{0,1\}.
$$

$I_{\mathrm{right}}$ requires permission and licence at the cutoff.
$I_{\mathrm{identity}}$ requires an unambiguous entity mapping.
$I_{\mathrm{membership}}$ requires the requested entity and date to belong to the
reviewed universe. $I_{\mathrm{complete}}$ requires a usable source version and
explicit absence semantics. $I_{\mathrm{basis}}$ requires every comparison field.
$I_{\mathrm{modality}}$ requires the observation to match the panel’s native data
kind. Because the indicators multiply, one failed gate makes $A=0$.

Exact comparability between observations also requires equal controlled basis
signatures:

$$
B(o_i)=B(o_j)
\iff
(g_i,f_i,c_i,r_i,q_i,\phi_i,b_i,v_i)
=(g_j,f_j,c_j,r_j,q_j,\phi_j,b_j,v_j).
$$

The fields are entity grain $g$, frequency and calendar $f$, currency and FX treatment
$c$, return or cash-flow kind $r$, gross/net and fee basis $q$, benchmark identity and
version $\phi$, valuation policy $b$, and composite-membership definition and version
$v$. Missing fields are not wildcards. A field must either be present or be explicitly
inapplicable for the native panel kind.

Every break in identity, membership, fee, currency, benchmark, calendar, valuation,
cash-flow treatment, predecessor attribution, gap, or overlap begins a new lineage
segment. No assumed fee load converts gross to net. Private-market cash flows and NAVs
remain an irregular provenance panel rather than being coerced into monthly returns.

Knowability is summarized by

$$
L_{\mathrm{known}}=
\mathrm{first\_known\_at}-\mathrm{effective\_at}.
$$

This lag describes how long evidence took to arrive. It is not a performance estimate.
Portability is recorded as documented claim, partial support, contradicted, unresolved,
or refused; person overlap alone never reassigns a predecessor segment.

## What the evidence changes

The paired synthetic exhibit contains **24 precomputed states**: four source shapes,
two cutoffs, and three views. It covers public equity, hedge fund, credit, and private-
market examples without claiming those sources are universally available.

The cutoff comparison surfaces revisions rather than overwriting them. The public-
equity FX conversion changes because the documented FX version changes. The hedge-fund
return and private-market NAV retain their early and latest values. Each is labeled as
an exact source observation or deterministic transformation, never as an estimate.

The credit panel reaches a stronger conclusion by refusing. Its frequency and calendar
bases are incompatible; the evidence also preserves valuation,
comparison-kind, and silent-stitch failures. The inspector does not “fix” the panel by resampling
or filling gaps.

All values remain synthetic examples. Stronger live conclusions would require independently
reconstructable source evidence; the demonstration does not promote itself. Across
every state, the unconditional performance boundary remains: the inspector emits no alpha,
Sharpe, IRR, PME, skill, or manager ranking.

## What the allocator does next

1. Set the decision cutoff before requesting a history.
2. Resolve entity, product, composite, vehicle, and share-class lineage independently
   of the return rows.
3. Request both the latest-known analytic view and the all-known-versions audit view at
   that same cutoff.
4. Compare complete basis signatures and split the history whenever a controlled field
   changes.
5. Reconcile included and excluded observations, including dead products, tombstones,
   and non-inferable absences.
6. Treat predecessor portability as a separately evidenced claim. Keep the original
   entity attribution even where support is strong.
7. Pass only an admitted native panel to the appropriate downstream estimator and its
   own validation gates.

## Limits and go-live

- **Data ask.** Live use needs archived source vintages and observations; full, delta,
  and tombstone semantics; entity, composite, vehicle, and share-class lineage;
  fee, currency, benchmark, calendar, and valuation basis; universe memberships and
  dead products; predecessor and team evidence; per-dataset rights; and complete
  reconstruction records.
- **Validation coverage.** Go-live requires at least one real, permissioned case in
  each intended source shape, including one known revision or backfill and one basis
  break. This is validation coverage, not an estimator sample-size threshold.
- **No universal availability.** The four synthetic source shapes demonstrate the
  interface. They do not claim the same evidence can be obtained for every manager.
- **No silent normalization.** Missing FX, fees, benchmark versions, calendars, or
  valuation policies cause refusal. They are not filled with assumptions.
- **No modality conversion.** Private-market cash-flow and NAV records remain native;
  the method does not manufacture periodic returns.
- **Portability ceiling.** Documented lineage does not prove that historical skill
  transferred to the current team or process.
- **Historical selection.** A point-in-time selection claim refuses without archived
  vintages, dead products, first-known times, and an exact denominator.
- **Decision ceiling.** Provenance inspection determines what may enter a downstream
  analysis. It does not perform that analysis.

## Key takeaways

- A track record must pass rights, identity, membership, completeness, basis, and
  modality gates before performance analysis.
- Effective time and first-known time answer different questions; later revisions must
  not rewrite earlier knowability.
- Exact basis signatures prevent silent stitching across fees, currencies, benchmarks,
  calendars, valuations, and composite definitions.
- Source observations and deterministic transformations are measurements, not skill
  estimates.
- Person overlap does not transfer a predecessor entity’s record.
- Refusing an incomparable panel is a usable result, not missing analysis.

## References

- *Track-record provenance inspector: technical method and provenance*, the governing
  definition of admission, basis, vintage, lineage, portability, and refusal rules.
- *Track-record provenance inspector: paired synthetic exhibit*, the 24-state worked
  record covering public-equity, hedge-fund, credit, and private-market source shapes.
