## Problem

- S7 determines whether a supplied track record is complete, comparable, point-in-time, and evidentially portable to the current team or process.
- It reconstructs return, composite, vehicle, and share-class lineage without estimating alpha, skill, Sharpe, IRR, PME, or manager rank.

## Evidence envelope

- S7 consumes the reviewed Phase-2 source, content, observation, snapshot, mapping, relationship, entitlement, and receipt APIs; it does not duplicate them.
- Each included observation must map to one declared entity grain, one lineage segment, one source version, and one complete basis signature at the decision cutoff.
- Every displayed finding and refusal maps to a claim-manifest entry with current class D.

For observation $o$, proposed native panel $p$, and decision cutoff $t$, admission is the
product of the required binary gates:

$$
A(o,p,t)=I_{\mathrm{right}} I_{\mathrm{identity}} I_{\mathrm{membership}}
I_{\mathrm{complete}} I_{\mathrm{basis}} I_{\mathrm{modality}} \in \{0,1\}.
$$

Here $I_{\mathrm{right}}$ is one only when the required access right and licence permit the
source at $t$; $I_{\mathrm{identity}}$ when its mapping is uniquely resolved; and
$I_{\mathrm{membership}}$ when the reviewed X3 membership covers the requested grain and date.
$I_{\mathrm{complete}}$ requires a usable version and source-appropriate absence semantics;
$I_{\mathrm{basis}}$ requires a complete compatible basis signature; and
$I_{\mathrm{modality}}$ requires the observation's native data kind to match $p$. S7 admits an
observation only when $A=1$; any zero produces the applicable refusal or exclusion.

For two observations $o_i$ and $o_j$, exact comparability also requires

$$
B(o_i)=B(o_j)
\iff
(g_i,f_i,c_i,r_i,q_i,\phi_i,b_i,v_i)
=(g_j,f_j,c_j,r_j,q_j,\phi_j,b_j,v_j).
$$

The controlled signature $B$ contains entity grain $g$, frequency and calendar $f$, currency and
FX treatment $c$, return or cash-flow kind $r$, gross/net and fee basis $q$, benchmark identity
and version $\phi$, valuation policy $b$, and composite-membership definition and version $v$.
Missing values are not wildcards: an inapplicable field must be declared as such by the native
panel kind, otherwise the basis gate fails. These are admission gates, not estimators: they
neither calculate performance nor convert observations into alpha, skill, Sharpe, IRR, PME, or a
rank.

## Lineage and basis

- S7 uses X3's reviewed effective-dated entity, product, and universe memberships; it does not infer a roster from return rows.
- A new segment begins at an identity, composite-membership, fee, currency/FX, benchmark, frequency/calendar, valuation, cash-flow, predecessor, gap, or overlap boundary.
- Gross and net histories are different bases, and S7 may not normalize them using an assumed fee load.

## Vintage audit

- The analytic view requests `revision_mode=latest-known`, while the audit view separately requests `revision_mode=all-known-versions` at the same decision cutoff.
- Audit findings include return backfills, restatements, retroactive membership, later-dead products, tombstones, and non-inferable absence.
- A later-known fact may be displayed with its effective date and first-known date without changing what was knowable earlier.

The knowledge lag for one versioned fact is the elapsed time between its economic date and the
date on which the evidence first became available:

$$
L_{\mathrm{known}} = \mathrm{first\_known\_at} - \mathrm{effective\_at}.
$$

Here $L_{\mathrm{known}}$ is the elapsed knowledge lag, $\mathrm{first\_known\_at}$ is the
first-known time recorded by the evidence substrate, and $\mathrm{effective\_at}$ is the
effective time of the underlying fact. The lag describes knowability; it is not a performance
estimate.

When a reviewed bundle contains an exact, versioned FX return and the ruled conversion contract,
the only permitted currency transformation is:

$$
1 + R^{\mathrm{base}}_t
= \left(1 + R^{\mathrm{local}}_t\right)
  \left(1 + R^{\mathrm{FX}}_t\right).
$$

$R^{\mathrm{local}}_t$ is the local-currency investment return for period $t$,
$R^{\mathrm{FX}}_t$ is the receipted currency return into the base currency for the same period,
and $R^{\mathrm{base}}_t$ is the resulting deterministic base-currency observation. Missing or
mismatched FX evidence refuses the transformation.

## Portability

- Predecessor and team portability states are `documented-claim`, `partial-support`, `contradicted`, `unresolved`, or `refused`.
- Person overlap alone never transfers a track record; a predecessor return segment remains attributed to its original entity.
- The page must state that documented lineage is not evidence that historical skill transferred.

## Refusals

- Refusal precedence starts with access, right, licence, and dataset completeness before identity, membership, lineage, basis, and portability failures.
- Missing or non-inferable X3 membership/dead-product scope, ambiguous mappings, incomplete basis fields, and incompatible panel kinds prevent admission.
- The unconditional performance-estimator refusal is receipted in every access context and state, even though it consumes no performance series.

## Synthetic exhibit

- The generator emits 24 precomputed states: four source shapes, two cutoffs, and three views.
- The source shapes cover public equity, hedge fund, credit, and private-market records without claiming universal availability.
- The default server-rendered state is `hedge-fund|early|lineage` and remains complete without JavaScript.

## Reviewed exhibit reconciliation — 2026-07-13

- The reviewed authority is the 370,982-byte committed `s7_provenance.json` with SHA-256
  `773311cf14d1e93fd5a6bd0e047ab69dc6a25b1feaf4cf48ff58301e6c5fd056`: 24 exact states,
  seven claims, and default `hedge-fund|early|lineage`.
- Result examples are the committed source observations or deterministic transformations, not
  teaching targets. The same public-equity local observation `0.0060` is admitted as
  `0.02612000` with FX series version `1` at the early cutoff and `0.02410800` with version `2`
  at the latest cutoff. The hedge-fund February observation is `0.0100` early and `0.0080`
  latest. The private-market March NAV is `85000000.00` early and `80000000.00` latest.
- The representative credit panel is refused with binding reason
  `frequency-calendar-incomparable`; its receipt also preserves the valuation, comparison-kind,
  and silent-stitch reasons. Public-equity states retain the reviewed method evidence, while the
  `basis_breaks` and `comparable_native_panel` claims are explicitly inapplicable at public access
  and therefore have empty claim-receipt arrays.
- The unconditional `/refusals/performance-estimator` boundary uses receipt
  `receipt:sha256:d227471a3a0bec2583ce35580749cd4b61cb364415c63add60318164aa792c4b`
  in every state. Every claim remains current class D; live ceilings are separate evidence
  requirements and do not upgrade the synthetic exhibit.
- There are no provisional numerical constants. The state axes, default state, refusal
  precedence, and controlled basis fields are interface policy, not tuned display values.

## Validation

- Verification proves that every receipt reference is reachable from its bundle and that a changed included or excluded fact changes the appropriate receipt.
- Planted adversarial cases cover revisions, dead products, absence semantics, ambiguous mappings, basis breaks, private NAV revisions, and attempted estimator leakage.
- An independent reviewer re-derives identity, lineage, basis, vintage, portability, receipt, and rendered-copy gates before JSON is released for integration.

## Page contract

- The page shows source scope, entity lineage, basis breaks, latest-known versus all-known versions, vintage findings, portability, an admitted native panel or refusal, receipts, and go-live requirements.
- Exact observed return and cash-flow values are labelled as source observations rather than estimates; no estimate-bearing bare point appears.
- Browser code may select precomputed states and map values to pixels, but may not join, transform, estimate, rank, or create a verdict.

## Binding rulings

- S7 emits a comparable panel only at one controlled entity grain and one native data modality after identity, membership, completeness, and basis gates pass.
- Private-market records remain an irregular cash-flow/NAV provenance panel; S7 does not create monthly returns or a performance statistic.
- Missing shared substrate capability is returned to its owner as an exact requirement; S7 must not create card-local evidence tables, resolver, universe, revision engine, or receipt format.
