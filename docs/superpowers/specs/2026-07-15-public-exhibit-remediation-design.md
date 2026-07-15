# Public Exhibit Remediation Design

**Status:** Approved for implementation

**Approved direction:** Reader-facing remediation of all 23 public exhibit/article pairs, based on the rendered audit completed on 2026-07-15.

## 1. Goal

Make every public Quant Allocator exhibit understandable without repository context and make every focal visual match the analytical structure it claims to show, while preserving the existing numerical claims, synthetic/public data boundary, and technical depth of the articles.

The remediation must leave readers with three clear layers:

1. **Exhibit:** the allocator question, direct answer or refusal, one focal example, and the visual needed to understand it.
2. **Article:** intuition, naive failure, quantitative method, worked example, notation, limitations, and action.
3. **Technical evidence:** provenance, reproducibility, access requirements, validation status, and exact source records, disclosed only when requested.

## 2. Scope

### Included

- Remove or translate internal codes and process language from all rendered public surfaces.
- Add a rendered-public-text regression check for prohibited internal vocabulary classes.
- Replace the misleading representations for:
  - Manager knowledge graph & retrieval.
  - Track-record provenance inspector.
  - Manager-universe & sourcing-funnel coverage map.
- Redesign the focal presentation for:
  - Returns-only sizing & decay signatures.
  - Hidden-convexity / short-vol screen.
  - 13F long-book intelligence.
  - Allocation under alpha uncertainty.
  - Operational evidence & change graph.
  - Tier & Power Atlas.
- Correct the Tiered book X-ray public projection so it agrees with its methodology article.
- Apply the approved vocabulary and ordering cleanup to the remaining exhibits.
- Verify the final publication on desktop and mobile through the in-app browser.

### Excluded

- New cards, new platform services, or revival of parked P4 work.
- Changes to statistical estimators, synthetic generators, or committed quantitative values unless a rendered claim is currently inconsistent with its approved article.
- A global evidence database, production knowledge graph, live data adapters, or standing monitoring dashboard.
- Pixel-level cloning of Aligrithm.

## 3. Alternatives considered

### A. Lexical cleanup only

Remove codes such as `E3-owned`, rename badges, and leave existing exhibits structurally unchanged.

This is fast but insufficient. It would not repair exhibits that call a node/edge inventory a graph, a table sequence a coverage map, or a validation protocol the focal reader story.

### B. Reader-first public projection with targeted visual replacement — selected

Preserve the existing method and data substrate. Change the public projection, replacing only the visual forms that do not match their data shape and simplifying the rest through progressive disclosure.

This is the selected approach because it improves comprehension without reopening numerical work or rebuilding the publication platform.

### C. Rebuild the publication from scratch

Replace the template, data, and navigation systems with a new site implementation.

This is rejected as unnecessary scope. The current typography, article substrate, static build, and strongest exhibits are usable foundations.

## 4. Public vocabulary contract

### Remove from visible public prose

- Bare card and lane IDs such as `S1`, `M4`, `E3`, and `X1` when used as unexplained nouns.
- Single-letter pillar chips `S`, `M`, `P`, `E`, and `X`.
- Repository and workflow language such as `wave-3`, `repository history`, `ship rule`, `PILOT pilot`, `committed JSON`, and `fixture`.
- Raw manager, document, relationship, hypothesis, and database IDs when a readable label exists.
- Raw claim IDs, receipt hashes, state keys, output pointers, reason codes, and access-semantics tokens.

### Translate at first use

- `R / E / P` becomes `Returns only / Exposure summaries / Positions and trades`; the letter may appear only after the full phrase is introduced and only where repeated comparison benefits from it.
- `Power gate` becomes a plain statement of the minimum sample or evidence needed.
- `Refusal` becomes a direct explanation that the result is not calculated because required evidence is missing.
- `Receipt` becomes `Source record`. Cryptographic identifiers remain available in the
  repository evidence and committed data, but are not rendered in public HTML.
- `Evidence-conditioned` becomes `Based only on evidence available by this date`.
- Attestation and live-ceiling letters become readable readiness states such as `Synthetic demonstration` or `Requires live-data validation`.

### Keep and define locally

Posterior, shrinkage, credible interval, confidence interval, Wilson interval, statistical power, false-alarm rate, Monte Carlo uncertainty, information coefficient, AUC, alpha half-life, CUSUM, and counterfactual.

## 5. Visual grammar

Each exhibit must use a visual that matches its analytical data shape:

| Analytical structure | Required visual family |
|---|---|
| Estimate plus uncertainty | Shared-scale dot/interval or bar/interval display |
| Time or revision history | Timeline or aligned time series |
| Pairwise overlap | Heat map with a selected-pair detail |
| Ranked retrieval results | Ranked list comparison |
| Typed relationships | Small connected layered graph with labelled edges |
| Missing pipeline link | Evidence flow with an explicit broken connector |
| Payoff shape | Scatterplot or payoff curve |
| Evidence admission/exclusion | Flow from source observations through checks to admitted/excluded outcomes |
| Threshold reliability | Labelled power curve with threshold and uncertainty |

Every focal visual must provide visible units, comparable scales, direct labels, a plain takeaway, and the decision implication. Estimate-bearing outputs retain intervals or explicit refusal states.

## 6. Page-specific designs

### 6.1 Manager knowledge graph & retrieval

Replace the separate node and edge columns with three coordinated views:

1. A ranked-result comparison for the active query, labelling each result as relevant, wrong manager, or missed paraphrase.
2. One query-centred, left-to-right evidence path from dated source to author, manager, topic, and underwriting claim. Connectors use plain relationship verbs. An unrelated-manager result appears as a muted excluded branch.
3. A validation strip separating the illustrative top-three result from formal recall-at-ten. The formal result receives visual priority when it shows no validated uplift.

Mobile renders the selected path as a vertical sequence rather than shrinking a full network.

### 6.2 Track-record provenance inspector

Replace the audit-console table wall with:

1. Source observations.
2. Identity, basis, date, and continuity checks.
3. Admitted observations and excluded observations, with one plain exclusion reason per row.
4. A two-clock timeline distinguishing when performance occurred from when it became knowable or was revised.

Exact source records and hashes remain in collapsed technical evidence.

### 6.3 Manager-universe coverage

Render the current evidence chain explicitly:

1. Named source rows.
2. Resolved strategies.
3. Missing strategy-to-target-cell assignment.
4. Eligible target cells.
5. Coverage not calculated.

The missing assignment is a visible broken connector with a plain explanation. A target-cell heat map is added only if valid cell assignments exist; the current fixture must not imply coverage that cannot be calculated.

### 6.4 High-friction redesigns

- **Returns-only signatures:** begin with two processes monthly returns fail to distinguish, then one classifier-versus-usability comparison and the refusal. Preregistration is technical evidence.
- **Hidden convexity:** begin with paired market-return versus manager-return payoff shapes, then use diagnostic intervals as corroboration.
- **13F intelligence:** define Form 13F locally and lead with a six-quarter concentration trajectory. The exact holdings table becomes supporting detail.
- **Allocation uncertainty:** use one shared zero-to-cap scale across managers and directly mark naive and uncertainty-aware weights.
- **Operational change:** make the dual-time timeline and action queue primary. Show one relationship path only when it explains a conflict.
- **Tier & Power Atlas:** lead with one returns-only versus measured-exposure comparison at two track lengths, with labelled axes, the 80% threshold, and the borderline interval.
- **Tiered book X-ray:** make reconciliation and manager-level intervals the current honest output. Any fused teaching scenario is explicitly labelled provisional and cannot be presented as the operational result.

## 7. Shared exhibit order

Every exhibit follows this order unless the visual itself is the opening answer:

1. Decision question.
2. Direct answer, takeaway, or refusal.
3. Focal example and visual.
4. Short `How to read it` guidance adjacent to the visual.
5. Decision implication.
6. Optional further analysis.
7. Limitations.
8. Collapsed technical evidence and readiness.

The `What this exhibit shows` block must not delay the focal visual with implementation status, repository provenance, or cross-card references.

## 8. Responsive and accessibility behavior

- At 390 CSS pixels, headings may wrap but must not crowd the decision question out of the initial reading sequence.
- Dense desktop diagrams receive a mobile composition designed for the same meaning; they are not merely scaled down.
- Relationship diagrams have an accessible sequential equivalent.
- Charts use direct labels and do not rely on colour alone.
- Controls retain visible focus, explicit pressed/selected state, and meaningful labels.
- Long identifiers never dominate the screen-reader or visual reading order.

## 9. Testing and review

### Test-first implementation

Each behavioral or rendered-copy change begins with the smallest failing site test. Tests inspect built HTML and, where applicable, the existing committed data rather than duplicating template logic.

### Required automated checks

- Targeted site tests for every changed exhibit.
- A rendered-public-text test covering internal code and process-language classes.
- Static build and output-integrity checks.
- Ruff on changed Python and test paths.

### Rendered QA

Use the in-app browser to inspect:

- Every replaced or redesigned exhibit at desktop and 390-pixel mobile width.
- One representative simplified exhibit from each publication pillar.
- Interactive state changes for the knowledge graph, operational change, transparency playground, and any other retained controls.
- Page identity, meaningful DOM content, console health, absence of framework overlays, screenshot evidence, and interaction proof.

### Review boundary

Use one consolidated final editorial/visual review after implementation. Re-run independent numerical review only if a calculation, estimator, generated value, or quantitative claim changes.

## 10. Implementation boundaries

- The primary agent owns shared templates, site-wide vocabulary rules, integration, and outward actions.
- Delegated tracks may edit only explicitly assigned page templates/assets/tests and must remain file-disjoint.
- No new frontend framework or visualization dependency is introduced.
- JavaScript may map committed values to pixels and reveal precomputed states; it may not recompute estimators.
- Existing unrelated changes and parked P4 work remain untouched.
- Merge, push, and publication remain separately gated by `.harness/current.yaml` and direct user approval.

## 11. Acceptance criteria

The remediation is ready for integration when:

1. No visible main-path prose requires card IDs, repository history, claim IDs, raw receipts, attestation letters, state keys, or access-semantics tokens to be understood.
2. All 23 exhibits have a direct question and a focal answer, takeaway, or refusal before technical evidence.
3. The three replacement exhibits render the specified connected flow, evidence path, or missing-link structure.
4. High-friction exhibits use the visual forms specified in section 6.4.
5. Articles preserve technical depth and no approved quantitative meaning changes silently.
6. Targeted tests, static build, output integrity, publication scan, and consolidated final review pass.
7. Desktop and mobile rendered QA shows no blocking comprehension, layout, interaction, or console defect.
