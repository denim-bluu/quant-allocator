# Wave 1 — Idea Gallery & Litmus Pack Design

**Date:** 2026-07-05
**Status:** Approved (section-by-section review)
**Scope:** The idea-gallery static site (shell + index), demo pages and
method specs for six litmus cards — the selected five (S1, S2, X1, X2, E1)
plus M5, pulled forward from wave 2 for AI/ML visibility in the litmus pack
(Joon, 2026-07-06) — demo-data generators, and publication to a new public
GitHub repo with GitHub Pages.
**Governing docs:** demo-layer spec
(`2026-07-05-demo-layer-design.md` — Interval tokens, typography, chart
rules, doctrine), convergence decision memo
(`docs/ideas/2026-07-05-convergence-decision.md` §6–§7 — honest-mockup
contract, spec template, wave plan), idea cards
(`docs/ideas/2026-07-05-idea-cards.md`).

## 1. Architecture

**Approach chosen:** minimal Python static-site builder (Jinja2 templates +
Markdown/KaTeX spec rendering). Rejected: pure hand-authored pages (conflicts
with rendering rich HTML specs; 20-page shell duplication) and off-the-shelf
SSGs (toolchain/theme fights the hand-controlled Interval identity).

**Load-bearing decision — numbers are computed locally, committed, and
reviewed; CI only renders.** `demo_data` generators run on the developer
machine and write deterministic, seeded JSON into `site/data/` (committed).
Every number on the site is therefore reviewable as a PR diff, which is the
numerics gate artifact. The GitHub Actions workflow installs only
template dependencies, builds HTML, and deploys — it never computes
statistics and never touches the network for data.

## 2. Repository layout (new files)

```
site/
  cards.yaml                    # manifest: all 20 cards (schema §3)
  templates/
    base.html.j2                # shell: head, tokens, nav, footer, theme toggle
    index.html.j2               # 20 tiles grouped by lane
    demo.html.j2                # demo-page skeleton: badges, go-live box, spec link
    spec.html.j2                # rendered method-spec page
    pages/                      # per-card content templates extending demo.html.j2
      x2-playground.html.j2
      s2-tearsheet.html.j2
      x1-atlas.html.j2
      s1-ledger.html.j2
      m5-saydo.html.j2
      e1-ladder.html.j2
  assets/
    design-tokens.css           # Interval tokens, light + dark (values from demo-layer spec §3)
    interval.css                # components (§6)
    interval.js                 # theme toggle + playground dial logic (vanilla)
    katex/                      # vendored KaTeX (pinned 0.16.x: css, fonts, katex.min.js, auto-render)
  data/                         # committed generator output
    x2_playground.json
    s2_tearsheet.json
    x1_atlas.json
    s1_ledger.json
    m5_saydo.json
  _build/                       # builder output (gitignored)
src/quant_allocator/
  demo_data/
    __init__.py
    __main__.py                 # python -m quant_allocator.demo_data build [card|all]
    roster.py                   # shared seeded synthetic-roster construction
    s1_ledger.py  s2_tearsheet.py  x1_atlas.py  x2_playground.py  m5_saydo.py
  site/
    __init__.py
    __main__.py                 # python -m quant_allocator.site build
    build.py                    # render, lint, copy (§7)
docs/ideas/specs/
  s1-bayesian-alpha-engine.md
  s2-tear-sheet-engine.md
  x1-tier-power-atlas.md
  x2-transparency-playground.md
  m5-say-do-gap.md
  e1-transparency-ladder.md
.github/workflows/pages.yml
README.md                       # portfolio-grade (§10)
LICENSE                         # MIT
```

New Python dependencies: `jinja2`, `markdown`, `pyyaml` (added to
`pyproject.toml`). Tests continue under the existing pytest setup.

## 3. Manifest schema (`site/cards.yaml`)

One entry per card, all 20 present from day one:

```yaml
- id: s1                # lowercase card id
  title: Hierarchical Bayesian alpha engine
  lane: S               # S | M | P | E | X
  one_liner: Posterior alpha across the roster — rank on skill, not luck.
  decisions: [select, size]
  tiers: [R, E, P]      # rungs the card defines
  status: live          # live | planned
  doctrine: false       # true only for process cards (E1): suppresses SYNTHETIC badge
  demo: pages/s1-ledger.html.j2   # required when status: live
  data: s1_ledger.json            # required when the page shows numbers
  spec: s1-bayesian-alpha-engine.md   # required when status: live
```

Wave 1: S1, S2, X1, X2, E1, M5 are `live`; the other 14 are `planned` (no
`demo`/`data`/`spec` keys). The builder fails if a `live` entry is missing a
required key or if a referenced file does not exist.

## 4. Site information architecture

- **Index** (`/index.html`): header with the program thesis (one sentence) and
  a site-wide banner: "All data on this site is synthetic or public.";
  20 tiles grouped by lane (S, M, P, E, X), each tile: title, one-liner,
  decision chips, tier badges, status (live tiles link to their page;
  planned tiles are visibly dimmed with a "wave 2" chip — honest placeholders,
  not dead links).
- **Demo pages** (`/<id>.html`): rendered from `pages/<id>.html.j2` within
  `demo.html.j2`, which guarantees the standard furniture: SYNTHETIC badge
  (unless `doctrine: true`), TierBadge row, compact methodology block,
  **go-live box** (three labeled fields: *data ask*, *sample required*,
  *build effort* — content per page in §5), link to the spec page.
- **Spec pages** (`/specs/<id>.html`): Markdown+LaTeX source rendered into
  `spec.html.j2` with KaTeX auto-render (client-side, self-hosted).
- **Themes:** light default site-wide; X2 playground page defaults dark
  (demo-layer spec); toggle persists via `localStorage`, honoring the
  token-level light/dark definitions.
- **Print:** demo pages carry print CSS (A4, page-break rules) per the
  demo-layer spec; the S2 pack and E1 ladder are the wave-1 print showcases.

## 5. The five pages — content requirements

Data contracts below are shape-level; the implementation plan pins exact
field names. All JSON is seeded and deterministic (fixed base seed per
generator; cell/manager indices map to distinct child seeds via the
simulator's existing stream-tag mechanism).

### X2 · Transparency playground (dark default)

- Dials (snap to grid): IC ∈ {0, .02, .04, .07, .10}; alpha half-life months
  ∈ {3, 12, 36}; sizing discipline ∈ {0.0, 0.8}; T months ∈ {24, 36, 48, 60,
  120}; tier ∈ {R, E, P}. Grid = 450 cells; ≥500 simulated managers per cell.
- Per cell the JSON carries, per analytic: estimate {point, lo, hi}
  (95% band across paths), verdict (robust/shrink/noise), and gate state
  {open|closed, threshold, units}. Analytics shown: annualized alpha
  (returns regression), Sharpe CI, and at P-tier hit rate and sizing-curve
  slope (gated by trade count).
- Tier semantics v1: R = returns-only estimates; E = betas pinned to true
  exposures (narrower alpha band) + measured drift; P = adds trade-level
  analytics behind PowerGates.
- Page behavior: dial changes swap displayed cell; IntervalStats animate
  width; VerdictChips flip; PowerGates render dashed empty-states naming the
  threshold. Go-live box: *simulator only — this page is the thesis, it never
  goes live against a real manager*.

### S2 · Tear-sheet mock (print showcase)

- One synthetic manager ("Manager 07", equity L/S, T=48, tier R). Panels:
  reported vs de-smoothed Sharpe (IntervalStat pair), interval-reported
  factor alphas vs the synthetic factor set, alt-beta VerdictChip logic
  (alpha CI crossing zero ⇒ "provisionally alternative beta"), MPPM beside
  Sharpe, drawdown chart with simulation-calibrated band (inline SVG from
  Python), monthly-return strip.
- Wave 1 uses fully synthetic factors (no CI network dependency, no
  factor-data redistribution questions); a real-FF5 variant is a wave-3
  upgrade note in the spec.
- Go-live box: data ask = monthly returns (R); sample = ≥36 months;
  effort = S–M.

### X1 · Atlas sampler

- Three exhibits: (1) power curves — P(detect α>0) vs T for true IR ∈
  {0.3, 0.5, 0.8}, OLS t-test vs shrinkage posterior; (2) tier-degradation
  table for three analytics (alpha estimation, drift detection, sizing
  skill) with measured deltas at P/E/R; (3) the PowerGate registry concept —
  a rendered thresholds-JSON snippet. Link prominently to the full spec page.
- Go-live box: data ask = none (simulator study); sample = n/a; effort = M
  (vol. 1).

### S1 · Posterior strip

- 20-manager synthetic roster (two strategy groups), known true alphas.
  Table: manager code, T, OLS alpha {point, CI}, posterior alpha {point,
  credible interval} via closed-form normal-normal shrinkage within strategy
  group, P(α>0), OLS rank vs posterior rank (the reshuffle visual — paired
  columns with movement marks), advisory weight band. Footnote: demo uses
  closed-form shrinkage; the live build is the full hierarchical model
  (spec §5 of the S1 method spec).
- Go-live box: data ask = monthly returns for the roster (R); sample =
  ≥36 months × ≥10 managers; effort = M.

### M5 · Say–do split screen (pulled forward from wave 2)

- One synthetic manager letter (authored content: three short excerpts, each
  stating a view — e.g., cautious on duration, constructive on energy
  equities, disciplined net exposure) rendered side-by-side with measured
  exposure paths from the simulator. Two views agree with the book; one
  contradicts it, and the contradiction row is the visual centerpiece:
  quote + extracted view (direction/theme/horizon) + measured exposure +
  agreement chip.
- Honesty note on the page: the extraction shown is illustrative; the live
  build requires the synthetic-letter eval harness (extraction
  precision/recall ≥ 0.8/0.8 gate) — link to the M5 spec's validation
  section.
- Data: `demo_data/m5_saydo.py` generates the exposure paths (simulator);
  letter excerpts and alignment annotations are authored constants in the
  module. SYNTHETIC badge applies.
- Go-live box: data ask = letters (R) + exposure summaries (E); sample =
  n/a (per-letter analytic, eval-harness-gated); effort = M–L including the
  harness.

### E1 · Transparency ladder (doctrine page)

- The ladder memo authored in wave 1 (it does not exist yet) — single source
  at `docs/ideas/specs/e1-transparency-ladder.md`; the page renders its
  three-rung ladder (per rung: the ask, the reciprocity, the power
  justification) as a designed document. No SYNTHETIC badge
  (`doctrine: true`); print CSS applies. Go-live box replaced by a
  "how to use this" note.

## 6. Component inventory (`interval.css` + `interval.js`)

CSS classes (design rules per demo-layer spec §3–§4): `interval-stat`
(point + rail + range text; the only sanctioned way to render a statistic),
`power-gate` (dashed empty-state naming threshold and unlock condition),
`tier-badge` (R/E/P), `verdict-chip` (robust | shrink | noise variants),
`synthetic-badge` (fixed-position provenance mark), `golive-box` (three
labeled fields), `card-tile` (index), `pack-page` (print container).
JS: theme toggle; playground dial handling (read inlined JSON, update DOM);
KaTeX auto-render init on spec pages. No other JS.

## 7. Builder behavior (`quant_allocator.site.build`)

1. Load and validate `cards.yaml` (schema §3; unknown keys rejected).
2. Render index from manifest.
3. For each `live` card: load its JSON from `site/data/`, inline it into the
   page as `<script type="application/json">` (robust under `file://` and
   print), render the page template.
4. Render each spec: python-markdown (extensions: `tables`, `fenced_code`,
   `toc`) into `spec.html.j2`; math delimiters (`$…$`, `$$…$$`) pass through
   untouched for client-side KaTeX.
5. Copy assets verbatim.
6. **Honest-mockup lint (build fails on violation):** every demo page output
   must contain `synthetic-badge` (unless `doctrine: true`) and `golive-box`
   (or the doctrine note variant); every `live` manifest entry must resolve
   to existing template, data, and spec files; every spec link target must
   exist.
7. All failures are loud errors naming the file and rule; nothing is
   silently skipped.

## 8. Demo-data generators (`quant_allocator.demo_data`)

- CLI: `python -m quant_allocator.demo_data build [card|all]`; writes
  `site/data/<card>.json` with sorted keys and fixed float precision so
  diffs are stable.
- Determinism: fixed base seed per generator; distinct child streams per
  cell/manager via the existing `default_rng([seed, tag])` convention.
- Tests (offline, in the existing suite): JSON schema validity; byte-for-byte
  determinism across two runs; sanity invariants — every interval contains
  its point estimate; playground power/width monotone in T on average;
  posterior intervals ⊆ reasonable bounds; gates closed exactly when below
  threshold.
- Every generator lands via SDD with a **the lead reviewer numerics review** on the
  committed JSON diff (annualization, alignment, seeding are the named
  failure modes).

## 9. Method specs — the six wave-1 documents

Authored per the 8-section template (decision memo §6): problem & decision
hook · data contract per tier · methodology · power & validation plan ·
implementation architecture · adoption & packaging · go-live requirements ·
**learning notes** (derivations to own, canonical papers, defend-unaided
list). Depth: S1 and X1 full (authored end to end); S2 and X2 full
with lighter methodology sections (they compose S1/X1 methods); E1 standard
depth — its methodology section is the adoption literature and the ladder
content itself; M5 standard depth with a full validation section (the
synthetic-letter eval harness is its load-bearing content). Math in LaTeX; figures, where needed, as inline SVG
generated by the demo-data scripts.

## 10. Publication

1. Create public GitHub repo `quant-allocator` (via `gh repo create`),
   push full history (public-safe by standing policy — verified again at
   push time by a final scan for names/internal references).
2. `README.md`: what the project is (one paragraph), the thesis line, link
   to the gallery, repo map, honest-data statement, license note. This is a
   portfolio landing page — written, not generated boilerplate.
3. `LICENSE`: MIT.
4. `.github/workflows/pages.yml`: on push to `main` → checkout,
   setup-python 3.12, `pip install -e . --no-deps && pip install jinja2
   markdown pyyaml`, run the builder, `actions/upload-pages-artifact` +
   `actions/deploy-pages`. Constraint this implies: `quant_allocator.site`
   must never import numpy/pandas/simulator modules (enforced by a test
   that imports it in isolation) — the builder renders, it does not compute.
5. **Pages enablement is manual and last**, after the visual QA gate (§11)
   and Joon's review of the five pages.

## 11. Testing & gates summary

- Existing suite stays green; ruff clean; new tests per §8 plus a builder
  smoke test (full build succeeds on the committed tree; lint rules fire on
  a deliberately broken fixture).
- Visual QA gate before Pages: Playwright screenshots of every page (light +
  dark, desktop + one mobile width), reviewed at the lead reviewer level against the
  demo-layer spec.
- SDD per-task reviews throughout; final whole-branch review (the lead reviewer) before
  merge; the standing compliance scan before the first push.

## 12. Build order

1. **Specs first (the lead reviewer pins, cheaper models draft where §9 allows):**
   S1, X1 → S2, X2, M5, E1 (the math the demos render is pinned before any
   rendering exists).
2. Gallery shell: tokens, components, builder + lint, manifest, index.
3. Demo-data generators + committed JSON (numerics gate per generator).
4. The five pages.
5. README, LICENSE, workflow; create repo + push; screenshots QA; Pages
   enable after sign-off.

## 13. Non-goals (wave 1)

No search, no analytics/tracking, no comment systems, no build watch mode /
dev server beyond a plain `python -m http.server` suggestion, no md→HTML
rendering for docs other than the five idea specs, no real FF5 data in demo
JSON, no additional interactive apps beyond the playground ("one small app
maximum"), no CI-side data computation, ever.
