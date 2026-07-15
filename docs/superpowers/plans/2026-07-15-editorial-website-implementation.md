# Quant Allocator Editorial Website Implementation Plan

> **COMPLETED HISTORICAL PLAN:** This plan produced the first editorial shell and is not
> active. Its Start Here selection, full-spec article rendering, and exhibit-preservation
> boundaries are superseded by `docs/EDITORIAL_SYSTEM.md` and the active plan named in
> `.harness/current.yaml`.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. The user has selected inline execution with one implementation owner and a single consolidated review at the end.

**Goal:** Rebuild Quant Allocator as a responsive publication-first editorial website while preserving all 23 tested exhibits and their quantitative semantics.

**Architecture:** Keep the existing Python/Jinja static builder and manifest. Shape editorial homepage groups in `build.py`, rebuild the shared shell and homepage templates, and restyle through the existing token/CSS layers. Preserve page-specific exhibit markup and JavaScript; add only reciprocal article/exhibit navigation and output-integrity coverage.

**Tech Stack:** Python, Jinja2, YAML manifest, semantic HTML, CSS, vanilla JavaScript, pytest, KaTeX.

## Global Constraints

- Public static publication; no backend, database, subscription, or dashboard platform.
- Use public or synthetic data and fictional displayed names only.
- Aligrithm governs hierarchy and rhythm; Interval governs quantitative meaning.
- Preserve all committed numerical data, per-card templates, and estimator code.
- Use test-first red-green-refactor for behavior changes.
- Keep merge, push, and publication disabled.
- Defer independent review until the whole rendered site is complete.

---

### Task 1: Editorial Homepage Contract and Data Shape

**Files:**
- Modify: `tests/site/test_gallery.py`
- Modify: `tests/site/test_build.py`
- Modify: `src/quant_allocator/site/build.py`
- Modify: `site/templates/index.html.j2`

**Interfaces:**
- Consumes: existing validated card dictionaries from `load_manifest()`.
- Produces: `start_here`, `pillars`, `featured_cards`, `stages`, and complete `cards` template data; existing `data-*` search corpus remains available.

- [ ] **Step 1: Write failing editorial homepage tests**

Add assertions equivalent to:

```python
assert "Evidence should change what you are allowed to say." in html
assert 'id="start-here"' in html
assert 'id="research"' in html
assert 'id="browse"' in html
for title in (
    "Uncertainty-honest tear-sheet engine",
    "Tier &amp; Power Atlas",
    "Transparency playground",
):
    assert title in html
for pillar, count in (
    ("Signal &amp; skill", 7),
    ("Monitoring", 6),
    ("Portfolio decisions", 3),
    ("Evidence &amp; engagement", 4),
    ("Cross-cutting foundations", 3),
):
    assert pillar in html
    assert f'data-pillar-count="{count}"' in html
assert html.count('data-card-id="') == 23
```

- [ ] **Step 2: Run the focused tests and verify the expected RED**

Run:

```bash
uv run pytest tests/site/test_gallery.py tests/site/test_build.py -q
```

Expected: new editorial assertions fail because the old dashboard-first homepage is still rendered.

- [ ] **Step 3: Shape existing cards for publication sections**

In `build.py`, add fixed presentation metadata only:

```python
START_HERE_IDS = ("s2", "x1", "x2")
FEATURED_IDS = ("s1", "m3", "m4", "p1", "s7")
PILLAR_DETAILS = {
    "S": ("Signal & skill", "Measure skill without rewarding noise."),
    "M": ("Monitoring", "Detect change, deterioration, and hidden concentration."),
    "P": ("Portfolio decisions", "Size, combine, and govern under uncertainty."),
    "E": ("Evidence & engagement", "Gather, challenge, and act on dated evidence."),
    "X": ("Cross-cutting foundations", "Define what the data can support."),
}
```

Derive groups from `view_cards`; do not add manifest fields or change card order.

- [ ] **Step 4: Implement the publication-first homepage**

Replace the dominant journey dashboard with semantic sections for thesis, Start Here,
pillars, selected research, secondary browse controls, and the complete searchable
article index. Retain the existing search `data-*` attributes and no-JavaScript path.

- [ ] **Step 5: Run focused tests and verify GREEN**

Run the same focused pytest command. Expected: pass.

### Task 2: Shared Publication Shell and Article/Exhibit Continuity

**Files:**
- Modify: `tests/site/test_build.py`
- Modify: `tests/site/test_interval_css.py`
- Modify: `site/templates/base.html.j2`
- Modify: `site/templates/spec.html.j2`
- Modify: `site/templates/demo.html.j2`
- Modify: `site/assets/design-tokens.css`
- Modify: `site/assets/interval.css`
- Modify: `site/assets/gallery.css`

**Interfaces:**
- Consumes: `card`, `asset_base`, `site_title`, existing theme script.
- Produces: shared masthead/nav/footer, responsive editorial typography, reciprocal `specs/{id}.html` ↔ `{id}.html` links.

- [ ] **Step 1: Write failing shell and reciprocal-link tests**

Add exact checks:

```python
assert "QUANT ALLOCATOR" in index
assert 'href="#start-here"' in index
assert 'href="#research"' in index
assert 'href="#browse"' in index
assert 'href="../s1.html"' in spec_html
assert "Open the paired exhibit" in spec_html
assert 'href="specs/s1.html"' in demo_html
assert "Read the full article" in demo_html
```

Add CSS contract checks for `.publication-header`, `.editorial-hero`,
`.publication-nav`, `.article-shell`, `.article-link`, a 390px media query, 44px
controls, focus-visible, and reduced-motion.

- [ ] **Step 2: Run focused tests and verify RED**

```bash
uv run pytest tests/site/test_build.py tests/site/test_interval_css.py -q
```

- [ ] **Step 3: Implement the shared shell and reciprocal links**

Use `asset_base` for every root/spec link. Keep `.spec-page__body`, `#card-data`,
`.card-context`, `synthetic-badge`, and all builder-lint furniture unchanged.

- [ ] **Step 4: Implement the extracted design system**

Apply the design spec's exact palette family, serif/sans roles, open container model,
hairline dividers, article line length, mobile single-column collapse, table overflow,
and non-overlapping synthetic badge. Do not restyle page-specific visualizations beyond
what shared tokens naturally change.

- [ ] **Step 5: Run focused tests and verify GREEN**

Run the same focused pytest command. Expected: pass.

### Task 3: Discovery Interaction and Static Output Integrity

**Files:**
- Modify: `tests/site/test_gallery.py`
- Modify: `site/assets/gallery.js` only if grouping selectors changed
- Create: `tests/site/test_output_integrity.py`

**Interfaces:**
- Consumes: generated HTML in a temporary build directory.
- Produces: deterministic search/view/filter behavior and a whole-output relative-link, fragment, ID, and asset gate.

- [ ] **Step 1: Update the JavaScript harness test for the new grouping contract**

Retain tests for `parseQuery`, `serializeState`, `matchesCard`, presets, and the full
search corpus. Add a DOM contract assertion that every results group uses the selector
expected by `gallery.js`.

- [ ] **Step 2: Write the failing static-output integrity test**

Create a stdlib `html.parser.HTMLParser` collector that records `id`, `href`, and `src`.
Build into `tmp_path`; for every generated HTML file require:

```python
assert len(ids) == len(set(ids))
assert not any(value.startswith(("/Users/", "/private/", "file:")) for value in refs)
```

Resolve every relative local path and fragment against the output tree; require the
target file and unique fragment ID to exist. Ignore `http:`, `https:`, `mailto:`, and
empty references.

- [ ] **Step 3: Run the integrity test and verify RED if any output seam is broken**

```bash
uv run pytest tests/site/test_output_integrity.py tests/site/test_gallery.py -q
```

- [ ] **Step 4: Make the smallest markup or JavaScript repair**

Do not broaden the build system. Fix only concrete broken paths, duplicate IDs, grouping
selectors, or state synchronization exposed by the tests.

- [ ] **Step 5: Run the focused integrity and gallery tests and verify GREEN**

Run the same command. Expected: pass.

### Task 4: Rendered QA and Consolidated Final Gate

**Files:**
- Create temporarily, then remove: browser screenshots under `/private/tmp`
- Create: `design-qa.md`
- Modify only if a defect is reproduced: the narrow template/CSS/JS/test file owning it

**Interfaces:**
- Consumes: fresh `site/_build` output and selected concept images.
- Produces: verified desktop/mobile website and a final fidelity ledger whose last line is `final result: passed`.

- [ ] **Step 1: Run one fresh build and serve it locally**

```bash
PYTHONPATH=src uv run python -m quant_allocator.site build
python3 -m http.server 4173 --bind 127.0.0.1 --directory site/_build
```

- [ ] **Step 2: Verify the core website in Browser/IAB**

At 1440×900 and 390×844 inspect the homepage, `s1.html`, and `specs/s1.html`; then
crawl all 47 pages for title, content, console errors, raw math, missing assets, and
horizontal overflow. Exercise theme, nav, Journey/Catalog, search, one preset, one
facet, clear, link round-trip, and browser back/forward.

- [ ] **Step 3: Compare concept and implementation with `view_image`**

Record at least five points: thesis composition, typography, palette, Start Here,
pillar/article rhythm, browse controls, article line length, reciprocal exhibit link,
and mobile collapse. Fix all P0/P1/P2 mismatches.

- [ ] **Step 4: Write the fidelity ledger**

`design-qa.md` must name the selected concepts, screenshots, viewport sizes, mismatches,
fixes, copy diff, intentional deviations, interaction evidence, and end with:

```text
final result: passed
```

- [ ] **Step 5: Run the single consolidated automated gate**

```bash
uv run pytest tests/site --ignore=tests/site/test_publication_check.py -m "not slow and not network" -q
uv run ruff check src/quant_allocator/site tests/site
git diff --check
```

Run `node --check` on every changed JavaScript file and a fresh build. Expect 47 HTML
files.

- [ ] **Step 6: Run and adjudicate the publication scan**

```bash
bash tools/publication_check.sh
```

The scanner is report-only. Inspect its output; do not treat exit zero as proof. Keep
merge, push, and publish disabled.
