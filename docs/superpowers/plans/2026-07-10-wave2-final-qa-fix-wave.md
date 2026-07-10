# Wave 2 final-QA fix wave

**Status:** implementation plan — held for re-verification and a numerics/copy
checkpoint before republishing.

**Published baseline:** `3f4d75f` (20 live cards, zero planned).

## 1. Why this wave exists

The wave-close audit used a researched, decision-first rubric plus a live browser
pass over the gallery, all 20 demos, all 20 method specs, and every visible control.
The browser pass captured 54 screenshots at 1440×1000.

The site is not release-clean despite a successful Pages build:

- S3, S4, and S5 ship malformed JSON-bearing HTML attributes. Their scripts abort,
  leaving charts, rails, or dial readouts blank.
- Fourteen specs retain raw math fragments and five show explicit parser errors.
- P1 changes dial text without changing the primary interval geometry.
- Several pages overstate what their synthetic construction or public-data crop
  establishes.
- S5 renders a certified hit-rate result at 745 trades although its binding line is
  780.
- Carried S4/S6 presentation obligations remain incomplete.

This plan repairs those failures without changing an estimator, inventing a new
threshold, or broadening a card's method.

## 2. Binding editorial and numerical rulings

1. **S1 is a shrinkage exhibit, not proof of skill recovery.** The pinned roster's
   posterior ordering is slightly worse than OLS against known truth. Keep the
   certified seven-rank reshuffle; remove claims that it separates skill from luck.
2. **S3 measures sizing contribution in a controlled synthetic path.** It does not
   certify manager intent or a live conviction premium. Existing contextual values
   remain descriptive scenario outputs.
3. **S5 obeys the already-approved 780-trade certification line.** Both 745- and
   385-trade cases refuse the hit-rate estimate. The threshold does not move.
4. **M2 exposes its existing ±0.35 coskew decision band.** No diagnostic verdict
   changes.
5. **M6 describes reported-long persistence.** `Conviction` may remain only in the
   engagement question, never as an inferred fact or signal label.
6. **X1 shows Monte Carlo uncertainty already implied by its simulations.** The
   E-tier point gate reaches 80% at 120 months; the R-tier point estimate is 0.788,
   while its Wilson interval spans 0.80. No power estimate changes.
7. **Synthetic evidence must name its transfer boundary at the decision point.** It
   may demonstrate mechanism execution, directional sensitivity, constraint
   behavior, or refusal logic. It does not establish prevalence, external
   calibration, predictive accuracy, intent, or real-committee skill.
8. **Interaction is part of the result.** Every visible control must update its
   claimed visual and textual state from committed precomputed data. Label-only or
   text-only changes fail.
9. **Math rendering is a release gate.** Every formula must reach KaTeX as one
   contiguous valid expression; raw delimiters or parser-error output block release.

## 3. Track A — shared spec integrity

**Branch:** `codex/wave2-finalqa-math`

**Owned files:**

- `src/quant_allocator/site/build.py`
- `site/templates/spec.html.j2`
- `tests/site/test_specs.py`
- `docs/ideas/specs/p1-allocation-uncertainty.md`
- `docs/ideas/specs/m1-exposure-drift-monitor.md`
- `docs/ideas/specs/m2-hidden-convexity-screen.md`
- `docs/ideas/specs/e2-engagement-pack.md`

### Implementation

- Add a Python-Markdown inline processor that protects balanced `$$…$$` before
  `$…$`, including multiline display math, as an `AtomicString` before emphasis and
  escape processing but after inline code protection.
- Preserve delimiters for the existing client renderer. Keep fenced and inline code
  excluded and keep escaped currency `\$` literal.
- Render math only inside `.spec-page__body`. Record an aggregate
  `data-math-render-status="ok|error"` and fail loudly on parser errors.
- Correct the four invalid P1 source expressions from `w^\*` to `w^*`.
- Reconcile the stale top statuses for the reviewed M1, M2, and E2 specs.
- This track exclusively owns the complete M1, M2, P1, and E2 spec files, not
  individual lines. Other tracks must return any additional requested spec wording
  to this owner rather than editing those files.

### Tests

- Unit fixture: inline underscores, multiline display math, escaped braces/hash/
  underscores, `texttt`, emphasis outside math, inline/fenced code containing dollar
  signs, and escaped currency.
- Build exactly 20 specs. In pre-JavaScript HTML, require balanced contiguous
  delimiters and reject any HTML tag inside a math range.
- Extract every expression and parse it with bundled KaTeX in throw-on-error mode;
  report spec ID and expression index. Raw delimiters are expected at this stage.
- Pin that reviewed live specs cannot say `pending method review`.

Expected data delta: none.

## 4. Track B — S-card correctness and interaction

**Branch:** `codex/wave2-finalqa-s`

**Owned files:** S1/S2/S3/S4/S5/S6 page templates, page scripts and page CSS where
needed; their method specs and focused tests; S5 pipeline, generator tests, and
`site/data/s5_shortbook.json`. This track does not edit `site/cards.yaml`.

### S1

- Frame the seven-rank reshuffle as peer shrinkage and uncertainty-aware ordering.
- Remove `skill not luck`, `hire the lucky`, and equivalent causal claims.
- State that the pinned roster does not prove better true-skill recovery; repeated-
  grid rank recovery and live calibration remain gates.
- Add a compact displayed-field → JSON field → generator → enforcing-test table to
  the spec.

### S2

- Add a decision-first opening and a decision-adjacent synthetic transfer boundary.
- State which mechanism the known-truth construction exercises and which external
  calibration or live-manager conclusion it does not establish.
- Add the same compact displayed-field → JSON field → generator → enforcing-test
  reproduction table to the spec.

### S3

- Encode every structured HTML attribute with `tojson|forceescape`.
- Keep browser code as a renderer of committed states only.
- Relabel contextual alpha/IR/gap outputs as realized synthetic-path values with a
  neutral descriptive verdict.
- Replace intent/conviction certification with sizing-contribution language and add
  the synthetic transfer boundary.

### S4

- Encode both horizon payloads safely.
- Make horizon states 1–6 update curve point count, rail geometry, printed point,
  interval, and exit count from the precomputed state.
- Replace nonexistent `quarterly toggle` and `tier tabs` with static-view language.

### S5

- Encode all structured attributes safely and server-render the default borrow
  readout.
- Remove the separate 500-trade render floor. Use the approved 780 line for the
  hit-rate render gate.
- At 745 and 385 trades, suppress the hit-rate point and t statistic and state the
  exact shortfall. Borrow-adjusted alpha panels remain available.
- Regenerate S5 JSON. Expected delta: the two hit-rate `renders` booleans only;
  numerical fields remain identical.

### S6

- Put `0 ship / 1 weak tell / 11 null` immediately after the pilot banner.
- Add an explicit PILOT chip to Panel 2.
- Use the full AUC domain `[0,1]`, show a null mark at 0.5, and render reversed/sub-
  0.5 signals left of null instead of clamping them together.
- Reconcile the spec to the current pilot result and test-pin the written-put
  exclusion and reversal note.

### Tests

- Parse every structured attribute through HTML parsing plus `json.loads`.
- Pin S1 copy boundaries and the seven-rank result.
- Exercise S4 at horizons 1, 4, and 6 across text, attributes, paths, and rails.
- Boundary-test S5 at 779/780; prove refused HTML contains no hit-rate points/t stats.
- Pin S6 ordering, PILOT labels, domain, null mark, exclusion, and reversal language.
- Run S5 byte determinism and inspect the exact JSON delta.

## 5. Track C — monitoring and portfolio repairs

**Branch:** `codex/wave2-finalqa-mp`

**Owned cards:** M1, M2, M6, P1, P3. This track does not edit shared templates,
`site/cards.yaml`, or the complete M1/M2/P1 spec files owned by Track A.

### M1

- Put the calibrated-synthetic-mechanism and external-validity boundary beside the
  first method link. This track changes only the M1 demo template and focused page
  test; Track A retains the complete M1 spec.

### M2

- Emit the existing `M2_COSKEW_BAND = 0.35` in JSON.
- Show the ±0.35 decision band on the coskew rail and explain why an interval that
  clears zero can still be inconclusive.
- Preserve the existing 3-of-4 verdict.
- Do not edit the M2 spec; Track A owns it completely.

### M6

- Rename factual headings and spec prose to reported-long/holding persistence.
- Keep `walk us through the conviction?` only as an engagement question.
- Update stale test fixtures that still require the old signal label.

### P1

- For every precomputed skepticism state, update row and IntervalStat attributes,
  displayed point/range, band and marker geometry, readout, and ARIA state.
- Use a fixed per-row domain derived from all committed states plus the naive marker.
- Do not recompute any estimator in JavaScript.
- Measure and, only if failing, correct selected-button text/background and focus-
  indicator contrast. Test the active state; do not turn this into a sitewide colour
  redesign.
- Do not edit the P1 spec; Track A owns it completely.

### P3

- State near the explainer that the generator deliberately reproduces the published
  stylized fact. It tests ledger, counterfactual, shrinkage, and refusal mechanics;
  it does not independently validate the paper or any real committee's skill.

Expected data delta: one additive M2 constant; no verdict or estimate change.

## 6. Track D — engagement and atlas traceability

**Branch:** `codex/wave2-finalqa-ex`

**Owned cards:** E1, E2, X1, X2. This track does not edit `site/cards.yaml` or the
complete E2 spec owned by Track A.

### E1

- State the decision, one-rung reciprocity rule, and zero-data evidence boundary in
  the opening section. Effects on grant survival require tracked pilot outcomes.

### E2

- Bind opening values to named existing section payloads rather than template
  literals. Test with a modified fixture so the headline follows the payload.

### X1

- Emit a named headline block, E-tier threshold result, aligned Wilson half-widths
  for curves, and Wilson values for the degradation table from the existing grid.
- Bind all headline/table numbers to JSON.
- Show server-visible intervals and chart uncertainty. Qualify 0.788 as a point-gate
  result whose Monte Carlo interval spans 0.80.
- Regenerate X1 twice and prove X2 JSON is unchanged.

### X2

- Bind the opening and comparison state to named cells in existing JSON.
- Replace `drag` with `select`, `switch`, or `choose` because the controls are
  discrete buttons.

Expected data delta: additive X1 headline/Wilson fields only; no grid, estimator, or
verdict change.

## 7. Integration seam

**Branch:** `codex/wave2-finalqa-integration`

After all four tracks pass independent review, one seam writer:

- merges reviewed tips in order A → B → C → D;
- changes the S1 gallery line to `Posterior alpha across the roster — shrink noisy
  records before ranking.`;
- changes the X2 gallery line to `Choose the dials and watch honest claims dissolve
  into grey.`;
- updates manifest-copy tests and no other card logic;
- proves existing JSON drift is limited to S5, M2, and X1 with the exact expected
  shapes.

### Held-data sequence

- Track outputs may contain provisional generated-data diffs. Before integration,
  independent numerics/copy reviewers must confirm:
  - only the two S5 `hit_full.renders` booleans flip under the unchanged 780 line;
  - M2's emitted decision band equals the existing `M2_COSKEW_BAND = 0.35`;
  - every X1 Wilson interval is re-derived from emitted power, replication count,
    and declared rounding;
  - no other JSON field, estimator output, or verdict changes.
- The integration branch may then merge the reviewed, still-held JSON with the code
  and copy. It remains off `main` until whole-wave review and the user checkpoint.

## 8. Required verification before the next checkpoint

### Code and data

- Focused tests for every touched card and `tests/site/test_specs.py`.
- Scoped Ruff and JavaScript syntax checks.
- Byte determinism for S5, M2, and X1; X2 remains byte-identical.
- Real site build: 20 demos, 20 specs, zero planned.
- Publication scan: zero new canonical/generic added-line or commit-message hits;
  no attribution trailers.

### Live-equivalent browser pass

- Re-run the 41-page baseline at the same 1440×1000 viewport.
- In post-JavaScript browser DOM, require math-render status `ok`; reject raw
  delimiters outside `pre, code`, `.katex-error`, and KaTeX console errors. Visually
  inspect formerly failing S1/S2/S3/S5/S6/M1/M2/M4/M6/P1/P2/P3/E2/E3 formulas.
- Recheck the exact interaction matrix: index theme; S1 order; S4 horizons 1–6;
  both S5 dials; all six M3 skepticism buttons; M4 pair selection and five stress
  states; M5 focus; every P1 row at 0.5×/1×/2× with geometry, text, attributes,
  readout, and ARIA assertions; all P2 tier-noise states; E3 representative node and
  edge; all 18 X2 states. S3 charts must render non-empty with no console error.
- Recheck S4 horizons 1–6 and all S6 carried findings.
- Validate the server-rendered no-JavaScript conclusion and limitation on all 20
  demos. Check keyboard activation/focus, reduced-motion, and narrow-screen reflow at
  representative shared-template families; name any evidence limit rather than
  claiming full accessibility compliance.
- Capture and inspect before/after screenshots for every repaired interactive state.

## 9. Next user checkpoint

Do not merge the held integration tip into `main` or republish silently. Bring the
user:

- the exact S5 verdict/JSON delta;
- M2's additive decision-band field;
- X1's emitted point estimates and Wilson intervals;
- before/after browser evidence for math and interactions;
- independent whole-wave review and publication-scan result.

Republish only after that checkpoint is approved.
