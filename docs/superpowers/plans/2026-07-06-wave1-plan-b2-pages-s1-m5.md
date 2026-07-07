# Wave-1 Plan B2 — S1 & M5 Demo Pages Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship two honest-mockup demo pages — S1 "Posterior strip" and M5 "Say–do split screen" — that render the already-certified `s1_ledger.json` and `m5_saydo.json` through the frozen Interval component contracts, and flip both cards to `status: live` in the manifest.

**Architecture:** The static-site builder (`quant_allocator.site.build`) already inlines each live card's committed JSON into a `#card-data` block. This plan adds a single enabling builder change — parse that JSON once with the stdlib `json` module and pass it to the template as `card_data` — so every number is rendered **server-side by Jinja, verbatim from the reviewed JSON**. The pages are therefore complete and print-clean with no JavaScript; page-level JS is layered enhancement only (map interval values to pixel band widths, sort/reshuffle the ledger, draw the M5 exposure sparkline, toggle focus). No statistics are ever computed in the browser.

**Tech Stack:** Python 3.12, Jinja2 templates, vanilla ES5-style JS (no build step, no dependencies), pytest build-level tests, ruff. The builder must remain free of numpy/pandas (`json` is stdlib and keeps the existing import-isolation test green).

## Global Constraints

These are binding, pinned decisions. Every task's requirements implicitly include this section. Values are copied verbatim from the lead-reviewer-pinned brief.

- **Branch:** `wave1-plan-b2-pages`, from `main`.
- **Plan doc:** `docs/superpowers/plans/2026-07-06-wave1-plan-b2-pages-s1-m5.md` (this file).
- **Scope is exactly:** two demo page templates rendering the two committed JSON files, manifest flips to `status: live` with go-live boxes, page-level JS, and build-integration tests. NO new generators, NO changes to `site/data/*.json`, NO cosmetic CSS overhaul (site-wide visual QA is a later pass — add only the component/page CSS the two pages need, in the existing stylesheet `site/assets/interval.css`).
- **"90% interval" label:** Every credible/confidence band displayed is labeled exactly `90% interval` (numerics gate obligation, Q1).
- **δ dead-band label:** The M5 δ dead-band is labeled exactly `illustrative, uncalibrated` wherever δ is shown (numerics gate obligation, Q5).
- **No statistics in the browser:** JS may map values to pixels, sort, and toggle — every displayed NUMBER comes verbatim from the inline JSON (the `#card-data` block that `demo.html.j2` already emits). Server-side Jinja rendering of those same numbers (unit conversion decimal→percent and rounding for display only) is allowed; inferential computation is not.
- **S1 headline visual:** the OLS-rank → posterior-rank reshuffle (7 of 20 managers move). Each manager renders an IntervalStat pair (OLS band vs posterior band) using the frozen `.interval-stat` DOM contract.
- **M5 page:** split screen — left "Said" (letter quote, direction, conviction), right "Did" (measured move vs δ dead-band on the exposure path), verdict rendered with the `.verdict-chip` contract states `aligned` / `partial` / `contradicted`.
- **Go-live box contents:** drafted from each method spec's go-live section (data ask / sample required / effort), one line each, honest.
- **Tests are build-level:** render the site to a tmp dir and assert (a) lint passes, (b) required copy present (`90% interval`, `illustrative, uncalibrated`, SYNTHETIC badge, go-live box), (c) the component DOM classes appear, (d) the builder still never imports numpy/pandas (the existing `test_site_build_import_isolation` keeps passing).
- **Model policy:** implementers (this plan carries complete code so implementation is transcription), senior task reviewers, senior final whole-branch review (the branch carries no new numbers), copy-obligation spot-check before merge.

### Frozen DOM contracts (from the design spec §6 + `interval.css`)

Reuse these class structures verbatim — do not invent variants:

- **IntervalStat** (the only sanctioned way to render a statistic):
  ```html
  <div class="interval-stat" data-lo="…" data-point="…" data-hi="…">
    <span class="interval-stat__label">LABEL</span>
    <span class="interval-stat__value">+12.0%</span>
    <div class="interval-stat__rail">
      <div class="interval-stat__band"></div>
      <div class="interval-stat__point"></div>
    </div>
    <span class="interval-stat__range">90% interval …</span>
  </div>
  ```
  `__band` `left`/`width` and `__point` `left` are set by page JS (pixel mapping); everything else is server-rendered.
- **VerdictChip:** `<span class="verdict-chip" data-verdict="STATE">STATE</span>` — existing states `robust|shrink|noise`; this plan adds `aligned|partial|contradicted` styling for M5.
- **TierBadge / SyntheticBadge / GoLiveBox:** emitted by `demo.html.j2` already; the page templates do not re-emit them.

---

## File Structure

| File | Responsibility | Action |
| --- | --- | --- |
| `src/quant_allocator/site/build.py` | Parse each live card's JSON once and pass `card_data` (dict) to the template, alongside the existing `card_data_json` string. | Modify |
| `site/assets/interval.css` | Add the ledger, say-do split, sparkline, advisory-band, and `aligned/partial/contradicted` verdict-chip classes the two pages need. | Modify (append) |
| `site/templates/pages/s1-ledger.html.j2` | S1 posterior-strip page: reshuffle headline, per-manager IntervalStat pairs, rank-movement marks, closed-form footnote. | Create |
| `site/templates/pages/m5-saydo.html.j2` | M5 say–do split screen: per-view Said/Did panels, δ dead-band, verdict chips, honesty note. | Create |
| `site/assets/s1-ledger.js` | Map interval values to pixel band widths (shared domain); OLS/posterior sort toggle. No numbers computed or displayed. | Create |
| `site/assets/m5-saydo.js` | Draw each exposure sparkline + δ dead-band from `#card-data` (value→pixel); focus-the-contradiction toggle. | Create |
| `site/cards.yaml` | Flip `s1` and `m5` entries to `status: live` with `demo`/`data`/`spec`/`golive` keys. | Modify |
| `tests/site/test_s1.py` | Build-level assertions for the S1 page. | Create |
| `tests/site/test_m5.py` | Build-level assertions for the M5 page. | Create |
| `tests/site/test_interval_css.py` | Add a test for the new page/component CSS classes. | Modify |
| `tests/site/test_build.py` | Update the planned-tile count (19→18→17) and add `s1`/`m5` live-link assertions as each flips. | Modify |

**Task order rationale:** CSS first (Task 1) so the pages have styling to land against. Then S1 (Task 2) carries the one-time builder change because it is the first consumer of parsed `card_data`. M5 (Task 3) reuses it. A final integration task (Task 4) verifies the whole site, ruff, and the import-isolation guard.

---

### Task 1: Component & page CSS

**Files:**
- Modify: `site/assets/interval.css` (append at end of file)
- Test: `tests/site/test_interval_css.py`

**Interfaces:**
- Consumes: existing design tokens from `design-tokens.css` (`--line`, `--dim`, `--ink`, `--accent`, `--pos`, `--neg`, `--warn`, `--paper`, `--band`, `--track`).
- Produces: CSS classes consumed by Tasks 2 and 3 — `.ledger*`, `.rank-move*`, `.advisory-band`, `.saydo*`, `.conviction-dot*`, `.saydo-spark*`, and `.verdict-chip[data-verdict="aligned|partial|contradicted"]`.

- [ ] **Step 1: Write the failing test**

Add to `tests/site/test_interval_css.py` (a new function; leave the existing `REQUIRED_TOKENS` test untouched):

```python
PAGE_TOKENS = [
    ".ledger",
    ".ledger-row",
    ".ledger-row--mover",
    ".rank-move--up",
    ".rank-move--down",
    ".advisory-band",
    '.verdict-chip[data-verdict="aligned"]',
    '.verdict-chip[data-verdict="partial"]',
    '.verdict-chip[data-verdict="contradicted"]',
    ".saydo-row",
    ".saydo-side--said",
    ".saydo-side--did",
    ".saydo-quote",
    ".conviction-dot",
    ".conviction-dot--on",
    ".saydo-spark__band",
    ".saydo-spark__line",
    ".saydo-illustrative",
    ".saydo--focus",
]


def test_interval_css_defines_page_classes():
    css = CSS_PATH.read_text(encoding="utf-8")
    missing = [token for token in PAGE_TOKENS if token not in css]
    assert not missing, f"interval.css missing page classes: {missing}"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src pytest tests/site/test_interval_css.py::test_interval_css_defines_page_classes -v`
Expected: FAIL — `interval.css missing page classes: [...]`

- [ ] **Step 3: Append the CSS**

Append verbatim to the end of `site/assets/interval.css`:

```css
/* === S1 ledger (posterior strip) ================================= */
.ledger-intro {
  margin: 8px 0 20px;
}

.ledger-headline {
  font-size: 15px;
  line-height: 1.5;
}

.ledger-controls {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px;
  margin-top: 12px;
}

.sort-toggle {
  border: 1px solid var(--line);
  border-radius: 6px;
  background: transparent;
  color: var(--ink);
  padding: 4px 10px;
  cursor: pointer;
  font: inherit;
}

.ledger-legend {
  font-size: 12px;
  color: var(--dim);
}

.ledger {
  display: grid;
  gap: 12px;
}

.ledger-row {
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 12px 14px;
  background: var(--paper);
}

.ledger-row--mover {
  border-left: 3px solid var(--accent);
}

.ledger-row__head {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 10px;
  margin-bottom: 8px;
}

.ledger-row__code {
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}

.ledger-row__meta {
  font-size: 12px;
  color: var(--dim);
}

.advisory-band {
  margin-left: auto;
  padding: 2px 8px;
  border: 1px solid currentColor;
  border-radius: 999px;
  font-size: 11px;
  text-transform: lowercase;
  color: var(--dim);
}

.advisory-band[data-band="review"] { color: var(--neg); }
.advisory-band[data-band="minimum"] { color: var(--dim); }
.advisory-band[data-band="standard"] { color: var(--accent); }
.advisory-band[data-band="conviction"] { color: var(--pos); }

.ledger-row__ranks {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
  font-size: 13px;
  font-variant-numeric: tabular-nums;
}

.rank-move {
  font-size: 12px;
  font-variant-numeric: tabular-nums;
}

.rank-move--up { color: var(--pos); }
.rank-move--down { color: var(--neg); }
.rank-move--same { color: var(--dim); }

.ledger-row__stats {
  display: grid;
  grid-template-columns: 1fr 1fr auto;
  gap: 12px;
  align-items: center;
}

@media (max-width: 640px) {
  .ledger-row__stats {
    grid-template-columns: 1fr;
  }
}

.ledger-row__prob {
  display: grid;
  gap: 4px;
  justify-items: end;
}

.ledger-row__prob-value {
  font-size: 18px;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}

.ledger-footnote {
  margin-top: 20px;
  font-size: 12px;
  color: var(--dim);
}

/* === VerdictChip alignment states (M5) =========================== */
.verdict-chip[data-verdict="aligned"] { color: var(--pos); }
.verdict-chip[data-verdict="partial"] { color: var(--warn); }
.verdict-chip[data-verdict="contradicted"] { color: var(--neg); }

/* === M5 say-do split screen ====================================== */
.saydo-intro {
  margin: 8px 0 20px;
}

.saydo-headline {
  font-size: 15px;
  line-height: 1.5;
}

.saydo-honesty {
  margin: 12px 0;
  padding: 8px 14px;
  border-left: 3px solid var(--warn);
  font-size: 13px;
  color: var(--dim);
}

.saydo-focus {
  border: 1px solid var(--line);
  border-radius: 6px;
  background: transparent;
  color: var(--ink);
  padding: 4px 10px;
  cursor: pointer;
  font: inherit;
}

.saydo {
  display: grid;
  gap: 16px;
}

.saydo-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0;
  border: 1px solid var(--line);
  border-radius: 8px;
  overflow: hidden;
  background: var(--paper);
  transition: opacity 0.15s ease;
}

@media (max-width: 640px) {
  .saydo-row {
    grid-template-columns: 1fr;
  }
}

.saydo-row--contradicted {
  border-color: var(--neg);
}

.saydo--focus .saydo-row:not(.saydo-row--contradicted) {
  opacity: 0.4;
}

.saydo-side {
  padding: 14px 16px;
}

.saydo-side--did {
  border-left: 1px solid var(--line);
}

@media (max-width: 640px) {
  .saydo-side--did {
    border-left: none;
    border-top: 1px solid var(--line);
  }
}

.saydo-side__label {
  display: block;
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: 0.10em;
  color: var(--dim);
  margin-bottom: 8px;
}

.saydo-quote {
  margin: 0 0 10px;
  padding-left: 10px;
  border-left: 2px solid var(--line);
  font-style: italic;
}

.saydo-view,
.saydo-measure {
  display: grid;
  grid-template-columns: max-content 1fr;
  gap: 2px 12px;
  margin: 0;
  font-size: 13px;
}

.saydo-view dt,
.saydo-measure dt {
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: 0.10em;
  color: var(--dim);
  align-self: center;
}

.saydo-view dd,
.saydo-measure dd {
  margin: 0;
  font-variant-numeric: tabular-nums;
}

.saydo-conviction {
  display: inline-flex;
  gap: 4px;
  align-items: center;
}

.conviction-dot {
  width: 8px;
  height: 8px;
  border-radius: 999px;
  border: 1px solid var(--dim);
}

.conviction-dot--on {
  background: var(--accent);
  border-color: var(--accent);
}

.saydo-exposure {
  margin: 10px 0;
}

.saydo-spark {
  display: block;
  width: 100%;
  height: 40px;
}

.saydo-spark__band {
  fill: var(--band);
}

.saydo-spark__line {
  fill: none;
  stroke: var(--accent);
  stroke-width: 1.5;
  vector-effect: non-scaling-stroke;
}

.saydo-illustrative {
  font-size: 11px;
  color: var(--warn);
}

.saydo-footnote {
  margin-top: 20px;
  font-size: 12px;
  color: var(--dim);
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src pytest tests/site/test_interval_css.py -v`
Expected: PASS (both the existing and the new test)

- [ ] **Step 5: Commit**

```bash
git add site/assets/interval.css tests/site/test_interval_css.py
git commit -m "feat(site): add S1 ledger + M5 say-do component CSS"
```

---

### Task 2: Builder `card_data` pass-through + S1 posterior-strip page

**Files:**
- Modify: `src/quant_allocator/site/build.py` (imports + `_render_demo_pages`)
- Create: `site/templates/pages/s1-ledger.html.j2`
- Create: `site/assets/s1-ledger.js`
- Modify: `site/cards.yaml` (flip the `s1` entry to live)
- Modify: `tests/site/test_build.py` (planned count 19→18, add `s1` live link)
- Test: `tests/site/test_s1.py`

**Interfaces:**
- Consumes: CSS classes from Task 1; `demo.html.j2` blocks `demo_content`, `methodology`, `body_scripts`; base template block `body_scripts`.
- Produces (builder): the demo-page render now passes `card_data` — the JSON-parsed dict (`dict | None`) — to every demo template, in addition to `card_data_json` (the raw string, unchanged). Templates read `card_data.managers`, `card_data.groups`, `card_data.meta`.

- [ ] **Step 1: Write the failing test**

Create `tests/site/test_s1.py`:

```python
from pathlib import Path

from quant_allocator.site.build import build

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_s1_page_provenance_and_copy(tmp_path):
    out = tmp_path / "out"
    build(REPO_ROOT / "site", out)
    html = (out / "s1.html").read_text(encoding="utf-8")
    # Provenance furniture from demo.html.j2.
    assert "synthetic-badge" in html
    assert "SYNTHETIC DATA" in html
    assert "golive-box" in html
    # copy obligation: every band labeled exactly "90% interval".
    assert "90% interval" in html
    # Inline JSON block + spec link.
    assert 'id="card-data"' in html
    assert "specs/s1.html" in html
    assert (out / "specs" / "s1.html").exists()


def test_s1_page_component_dom_and_numbers(tmp_path):
    out = tmp_path / "out"
    build(REPO_ROOT / "site", out)
    html = (out / "s1.html").read_text(encoding="utf-8")
    # 20 managers x 2 IntervalStats (OLS + posterior), rendered server-side.
    assert html.count('class="interval-stat"') == 40
    assert "interval-stat__band" in html
    # Reshuffle headline computed in-template from the certified JSON.
    assert "7 of 20 managers change rank" in html
    # A number verbatim from the JSON: A10 posterior point 0.254274 -> +25.4%.
    assert "+25.4%" in html
    # Doctrine: certainty is never displayed as 1.00; capped at >0.99
    # (A08/A10 carry prob_positive == 1.0 from 6-digit rounding).
    assert "&gt;0.99" in html
    assert ">1.00<" not in html


def test_s1_page_script_loaded(tmp_path):
    out = tmp_path / "out"
    build(REPO_ROOT / "site", out)
    html = (out / "s1.html").read_text(encoding="utf-8")
    assert "assets/s1-ledger.js" in html
    assert (out / "assets" / "s1-ledger.js").exists()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src pytest tests/site/test_s1.py -v`
Expected: FAIL — s1 is still `planned`, so `s1.html` is never rendered (`FileNotFoundError`).

- [ ] **Step 3: Modify the builder to pass parsed `card_data`**

In `src/quant_allocator/site/build.py`, add the `json` import. Change the import block near the top:

```python
from __future__ import annotations

import shutil
from pathlib import Path
```

to:

```python
from __future__ import annotations

import json
import shutil
from pathlib import Path
```

Then replace the entire `_render_demo_pages` function with:

```python
def _render_demo_pages(
    env: Environment, cards: list[dict], site_dir: Path, out_dir: Path
) -> None:
    for card in cards:
        if card["status"] != "live":
            continue
        card_data_json = ""
        card_data = None
        if not card.get("doctrine", False):
            card_data_json = (site_dir / "data" / card["data"]).read_text(encoding="utf-8")
            card_data = json.loads(card_data_json)
        html = env.get_template(card["demo"]).render(
            page_title=card["title"],
            card=card,
            card_data_json=card_data_json,
            card_data=card_data,
            asset_base="",
            default_theme="light",
        )
        (out_dir / f"{card['id']}.html").write_text(html, encoding="utf-8")
```

(`json` is stdlib — the builder still imports neither numpy nor pandas, so `test_site_build_import_isolation` stays green.)

- [ ] **Step 4: Create the S1 page template**

Create `site/templates/pages/s1-ledger.html.j2`:

```jinja
{% extends "demo.html.j2" %}

{% block demo_content %}
{% set ns = namespace(movers=0) %}
{% for m in card_data.managers %}
  {% if m.ols_rank != m.posterior_rank %}{% set ns.movers = ns.movers + 1 %}{% endif %}
{% endfor %}

<section class="ledger-intro">
  <p class="ledger-headline">
    Shrinking each manager toward their strategy peers reshuffles the ranking:
    <strong>{{ ns.movers }} of {{ card_data.meta.n_managers }} managers change rank</strong>
    once luck is separated from skill. Rankings built on raw OLS alpha hire the lucky.
  </p>
  <div class="ledger-controls">
    <button type="button" class="sort-toggle" data-sort-toggle data-order="ols">
      Order by: OLS rank
    </button>
    <span class="ledger-legend">
      <span class="rank-move rank-move--up">&#9650;</span> rose &middot;
      <span class="rank-move rank-move--down">&#9660;</span> fell after shrinkage
    </span>
  </div>
</section>

<section class="ledger" data-ledger>
  {% for m in card_data.managers | sort(attribute='ols_rank') %}
  {% set delta = m.ols_rank - m.posterior_rank %}
  <article class="ledger-row{% if delta != 0 %} ledger-row--mover{% endif %}"
           data-ols-rank="{{ m.ols_rank }}"
           data-posterior-rank="{{ m.posterior_rank }}">
    <header class="ledger-row__head">
      <span class="ledger-row__code">{{ m.code }}</span>
      <span class="ledger-row__meta">group {{ m.group }} &middot; {{ m.months }} months</span>
      <span class="advisory-band" data-band="{{ m.advisory_band }}">{{ m.advisory_band }}</span>
    </header>

    <div class="ledger-row__ranks">
      <span class="rank-pair">OLS #{{ m.ols_rank }} &rarr; posterior #{{ m.posterior_rank }}</span>
      {% if delta > 0 %}
        <span class="rank-move rank-move--up">&#9650; {{ delta }}</span>
      {% elif delta < 0 %}
        <span class="rank-move rank-move--down">&#9660; {{ -delta }}</span>
      {% else %}
        <span class="rank-move rank-move--same">&mdash; held</span>
      {% endif %}
    </div>

    <div class="ledger-row__stats">
      <div class="interval-stat"
           data-lo="{{ m.ols_alpha.ci_lo }}"
           data-point="{{ m.ols_alpha.point }}"
           data-hi="{{ m.ols_alpha.ci_hi }}">
        <span class="interval-stat__label">OLS alpha (annual)</span>
        <span class="interval-stat__value">{{ "%+.1f"|format(m.ols_alpha.point * 100) }}%</span>
        <div class="interval-stat__rail">
          <div class="interval-stat__band"></div>
          <div class="interval-stat__point"></div>
        </div>
        <span class="interval-stat__range">90% interval {{ "%+.1f"|format(m.ols_alpha.ci_lo * 100) }}% &hellip; {{ "%+.1f"|format(m.ols_alpha.ci_hi * 100) }}%</span>
      </div>

      <div class="interval-stat"
           data-lo="{{ m.posterior_alpha.ci_lo }}"
           data-point="{{ m.posterior_alpha.point }}"
           data-hi="{{ m.posterior_alpha.ci_hi }}">
        <span class="interval-stat__label">Posterior alpha (annual)</span>
        <span class="interval-stat__value">{{ "%+.1f"|format(m.posterior_alpha.point * 100) }}%</span>
        <div class="interval-stat__rail">
          <div class="interval-stat__band"></div>
          <div class="interval-stat__point"></div>
        </div>
        <span class="interval-stat__range">90% interval {{ "%+.1f"|format(m.posterior_alpha.ci_lo * 100) }}% &hellip; {{ "%+.1f"|format(m.posterior_alpha.ci_hi * 100) }}%</span>
      </div>

      <div class="ledger-row__prob">
        <span class="interval-stat__label">P(&alpha; &gt; 0)</span>
        {# Doctrine: never display certainty — 1.0 in the JSON is 6-digit rounding. #}
        <span class="ledger-row__prob-value">{% if m.prob_positive > 0.99 %}&gt;0.99{% elif m.prob_positive < 0.01 %}&lt;0.01{% else %}{{ "%.2f"|format(m.prob_positive) }}{% endif %}</span>
      </div>
    </div>
  </article>
  {% endfor %}
</section>

<p class="ledger-footnote">
  This gallery page uses the closed-form normal&ndash;normal shrinkage variant
  (empirical-Bayes moment estimates per strategy group). The live build is the
  full hierarchical MCMC model &mdash; the demo formula is the intuition, not the
  product. See method spec &sect;3.6.
</p>
{% endblock %}

{% block methodology %}
<p>Each manager's raw OLS alpha is shrunk toward their strategy-group mean by the
weight their track length earns: a short, noisy record is pulled hard toward the
peer mean; a long, clean record barely moves. The band shown is the 90% interval;
a bare point alpha is never shown without it.</p>
<p>Shrinkage never claims &ldquo;your alpha was cut&rdquo; &mdash; it reports
&ldquo;shrunk toward strategy peers by the weight your track length earns.&rdquo;
Ranking on the posterior mean and P(&alpha; &gt; 0) is what separates skill from
luck at 36&ndash;60 months.</p>
{% endblock %}

{% block body_scripts %}
<script src="{{ asset_base | default('') }}assets/s1-ledger.js"></script>
{% endblock %}
```

- [ ] **Step 5: Create the S1 page JS**

Create `site/assets/s1-ledger.js`:

```javascript
(function () {
  "use strict";

  // Map each IntervalStat's lo/point/hi onto a shared pixel domain so bands
  // are visually comparable. Reads verbatim numbers already rendered as data-*
  // attributes; computes only pixel positions, never a displayed number.
  function positionBands() {
    var stats = Array.prototype.slice.call(
      document.querySelectorAll(".ledger .interval-stat")
    );
    if (!stats.length) {
      return;
    }
    var los = stats.map(function (s) { return parseFloat(s.dataset.lo); });
    var his = stats.map(function (s) { return parseFloat(s.dataset.hi); });
    var min = Math.min.apply(null, los);
    var max = Math.max.apply(null, his);
    var span = max - min;
    if (span <= 0) {
      return;
    }
    stats.forEach(function (s) {
      var lo = parseFloat(s.dataset.lo);
      var hi = parseFloat(s.dataset.hi);
      var point = parseFloat(s.dataset.point);
      var band = s.querySelector(".interval-stat__band");
      var mark = s.querySelector(".interval-stat__point");
      band.style.left = ((lo - min) / span) * 100 + "%";
      band.style.width = ((hi - lo) / span) * 100 + "%";
      mark.style.left = ((point - min) / span) * 100 + "%";
    });
  }

  // Reorder ledger rows between OLS-rank and posterior-rank order (the reshuffle).
  function initSort() {
    var toggle = document.querySelector("[data-sort-toggle]");
    var ledger = document.querySelector("[data-ledger]");
    if (!toggle || !ledger) {
      return;
    }
    toggle.addEventListener("click", function () {
      var order = toggle.dataset.order === "ols" ? "posterior" : "ols";
      toggle.dataset.order = order;
      toggle.textContent =
        "Order by: " + (order === "ols" ? "OLS rank" : "posterior rank");
      var attr = order === "ols" ? "olsRank" : "posteriorRank";
      var rows = Array.prototype.slice.call(ledger.querySelectorAll(".ledger-row"));
      rows.sort(function (a, b) {
        return parseInt(a.dataset[attr], 10) - parseInt(b.dataset[attr], 10);
      });
      rows.forEach(function (row) { ledger.appendChild(row); });
    });
  }

  function init() {
    positionBands();
    initSort();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
```

- [ ] **Step 6: Flip the `s1` manifest entry to live**

In `site/cards.yaml`, replace the `s1` entry (currently lines 1–7):

```yaml
- id: s1
  title: Hierarchical Bayesian alpha engine
  lane: S
  one_liner: Posterior alpha across the roster — rank on skill, not luck.
  decisions: [select, size]
  tiers: [R, E, P]
  status: planned
```

with:

```yaml
- id: s1
  title: Hierarchical Bayesian alpha engine
  lane: S
  one_liner: Posterior alpha across the roster — rank on skill, not luck.
  decisions: [select, size]
  tiers: [R, E, P]
  status: live
  demo: pages/s1-ledger.html.j2
  data: s1_ledger.json
  spec: s1-bayesian-alpha-engine.md
  golive:
    data_ask: Monthly net returns for the roster (R), with strategy labels
    sample: ≥36 months × ≥10 managers
    effort: M
```

- [ ] **Step 7: Update the shared index-count test**

In `tests/site/test_build.py`, the flip makes two cards live (e1 + s1), so 18 tiles remain planned. Change:

```python
    assert index.count("card-tile--planned") == 19
    assert 'href="e1.html"' in index
```

to:

```python
    assert index.count("card-tile--planned") == 18
    assert 'href="e1.html"' in index
    assert 'href="s1.html"' in index
```

- [ ] **Step 8: Run the tests to verify they pass**

Run: `PYTHONPATH=src pytest tests/site/test_s1.py tests/site/test_build.py tests/site/test_cli.py -v`
Expected: PASS (including `test_site_build_import_isolation` — the builder still imports no numpy/pandas)

- [ ] **Step 9: Commit**

```bash
git add src/quant_allocator/site/build.py site/templates/pages/s1-ledger.html.j2 site/assets/s1-ledger.js site/cards.yaml tests/site/test_build.py tests/site/test_s1.py
git commit -m "feat(site): S1 posterior-strip demo page (live)"
```

---

### Task 3: M5 say–do split-screen page

**Files:**
- Create: `site/templates/pages/m5-saydo.html.j2`
- Create: `site/assets/m5-saydo.js`
- Modify: `site/cards.yaml` (flip the `m5` entry to live)
- Modify: `tests/site/test_build.py` (planned count 18→17, add `m5` live link)
- Test: `tests/site/test_m5.py`

**Interfaces:**
- Consumes: CSS from Task 1; the builder `card_data` pass-through from Task 2; `demo.html.j2` blocks and the `#card-data` inline JSON. Reads `card_data.views` (each `{quote, direction, theme, conviction, instrument, label, letter_date, horizon_months, measured{start,end,move,delta}}`), `card_data.meta.horizon_months`, and (in JS) `card_data.exposure_paths[instrument]` (list of `{month, value}`).
- Produces: `m5.html`.

- [ ] **Step 1: Write the failing test**

Create `tests/site/test_m5.py`:

```python
from pathlib import Path

from quant_allocator.site.build import build

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_m5_page_provenance_and_copy(tmp_path):
    out = tmp_path / "out"
    build(REPO_ROOT / "site", out)
    html = (out / "m5.html").read_text(encoding="utf-8")
    assert "synthetic-badge" in html
    assert "SYNTHETIC DATA" in html
    assert "golive-box" in html
    # numerics gate: the delta dead-band is labeled illustrative wherever shown.
    assert "illustrative, uncalibrated" in html
    assert 'id="card-data"' in html
    assert "specs/m5.html" in html
    assert (out / "specs" / "m5.html").exists()


def test_m5_page_verdict_contract_and_quotes(tmp_path):
    out = tmp_path / "out"
    build(REPO_ROOT / "site", out)
    html = (out / "m5.html").read_text(encoding="utf-8")
    # VerdictChip contract states present in the data (aligned + contradicted;
    # "partial" is a supported state exercised by CSS, not by this dataset).
    assert 'data-verdict="aligned"' in html
    assert 'data-verdict="contradicted"' in html
    assert 'class="verdict-chip"' in html
    # The contradiction row is the centerpiece.
    assert 'saydo-row--contradicted' in html
    # Verbatim quote from the JSON (receipts always ship with claims).
    assert "crowded momentum has become" in html


def test_m5_page_script_loaded(tmp_path):
    out = tmp_path / "out"
    build(REPO_ROOT / "site", out)
    html = (out / "m5.html").read_text(encoding="utf-8")
    assert "assets/m5-saydo.js" in html
    assert (out / "assets" / "m5-saydo.js").exists()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src pytest tests/site/test_m5.py -v`
Expected: FAIL — m5 is still `planned`, so `m5.html` is never rendered.

- [ ] **Step 3: Create the M5 page template**

Create `site/templates/pages/m5-saydo.html.j2`:

```jinja
{% extends "demo.html.j2" %}

{% block demo_content %}
<section class="saydo-intro">
  <p class="saydo-headline">
    One synthetic manager letter, three stated views, read against the measured
    book. Two views match the positioning; one contradicts it &mdash; shown side
    by side, quote and measurement together, so the reader draws the conclusion.
  </p>
  <aside class="saydo-honesty" role="note">
    The extraction shown here is <strong>illustrative</strong>. The live build
    renders a real-letter claim only after the synthetic-letter eval harness
    passes its gate (extraction precision &ge; 0.8 and recall &ge; 0.8, alignment
    accuracy &ge; 0.8). See method spec &sect;4.
  </aside>
  <button type="button" class="saydo-focus" data-saydo-focus>Focus the contradiction</button>
</section>

<section class="saydo" data-saydo>
  {% for v in card_data.views %}
  <article class="saydo-row saydo-row--{{ v.label }}"
           data-instrument="{{ v.instrument }}"
           data-label="{{ v.label }}">
    <div class="saydo-side saydo-side--said">
      <span class="saydo-side__label">Said &middot; {{ v.letter_date }}</span>
      <blockquote class="saydo-quote">{{ v.quote }}</blockquote>
      <dl class="saydo-view">
        <dt>Direction</dt><dd>{{ v.direction }}</dd>
        <dt>Theme</dt><dd>{{ v.theme }}</dd>
        <dt>Conviction</dt>
        <dd class="saydo-conviction" aria-label="conviction {{ v.conviction }} of 3">
          {% for i in range(3) %}<span class="conviction-dot{% if i < v.conviction %} conviction-dot--on{% endif %}"></span>{% endfor %}
        </dd>
      </dl>
    </div>

    <div class="saydo-side saydo-side--did">
      <span class="saydo-side__label">Did &middot; {{ card_data.meta.horizon_months }}-month horizon</span>
      <div class="saydo-exposure"
           data-instrument="{{ v.instrument }}"
           data-start="{{ v.measured.start }}"
           data-end="{{ v.measured.end }}"
           data-delta="{{ v.measured.delta }}">
        <svg class="saydo-spark" viewBox="0 0 100 40" preserveAspectRatio="none" aria-hidden="true"></svg>
      </div>
      <dl class="saydo-measure">
        <dt>{{ v.instrument }}</dt>
        <dd>{{ "%+.3f"|format(v.measured.start) }} &rarr; {{ "%+.3f"|format(v.measured.end) }}
            (move {{ "%+.3f"|format(v.measured.move) }})</dd>
        <dt>Dead-band &delta;</dt>
        <dd>&plusmn;{{ "%.2f"|format(v.measured.delta) }}
            <span class="saydo-illustrative">illustrative, uncalibrated</span></dd>
      </dl>
      <span class="verdict-chip" data-verdict="{{ v.label }}">{{ v.label }}</span>
    </div>
  </article>
  {% endfor %}
</section>

<p class="saydo-footnote">
  &ldquo;Communication drift worth a conversation,&rdquo; never &ldquo;caught
  you.&rdquo; Every row shows the verbatim quote and the measured series side by
  side and stops there. The dead-band &delta; is illustrative, uncalibrated in
  this demo; the live build sets each &delta; from the simulator so a stated
  false-contradiction budget holds. See method spec &sect;3.2 and &sect;4.
</p>
{% endblock %}

{% block methodology %}
<p>Two stages with a hard division of labor: an LLM reads the letter text and
emits a structured view (direction, theme, instrument, conviction, quote span);
deterministic code scores that view against the measured exposure path. Nothing
probabilistic touches the label.</p>
<p>A view is <em>aligned</em> when the exposure moves in the stated direction by
at least the dead-band &delta; over the horizon, <em>contradicted</em> when it
moves against the stated direction by at least &delta;, and <em>partial</em> when
the move stays inside the dead-band &mdash; in either direction &mdash; making no
material statement. A stated-flat view is <em>aligned</em> only while the
exposure stays inside &plusmn;&delta;, <em>contradicted</em> beyond it. In this
demo &delta; is illustrative, uncalibrated; the live build calibrates it from
the simulator's honest-wander distribution.</p>
{% endblock %}

{% block body_scripts %}
<script src="{{ asset_base | default('') }}assets/m5-saydo.js"></script>
{% endblock %}
```

- [ ] **Step 4: Create the M5 page JS**

Create `site/assets/m5-saydo.js`:

```javascript
(function () {
  "use strict";

  var SVGNS = "http://www.w3.org/2000/svg";

  function readCardData() {
    var el = document.getElementById("card-data");
    if (!el) {
      return null;
    }
    try {
      return JSON.parse(el.textContent);
    } catch (e) {
      return null;
    }
  }

  // Draw one exposure path (value -> pixel) and shade the delta dead-band around
  // the starting exposure. Pure layout; no displayed number is produced here.
  function drawSpark(container, series, delta) {
    var svg = container.querySelector(".saydo-spark");
    if (!svg || !series || series.length < 2) {
      return;
    }
    var start = parseFloat(container.dataset.start);
    var values = series.map(function (p) { return p.value; });
    var lo = Math.min.apply(null, values.concat([start - delta]));
    var hi = Math.max.apply(null, values.concat([start + delta]));
    var span = hi - lo || 1;
    var W = 100;
    var H = 40;

    function x(i) { return (i / (series.length - 1)) * W; }
    function y(v) { return H - ((v - lo) / span) * H; }

    var bandTop = y(start + delta);
    var bandBottom = y(start - delta);
    var band = document.createElementNS(SVGNS, "rect");
    band.setAttribute("x", "0");
    band.setAttribute("y", String(bandTop));
    band.setAttribute("width", String(W));
    band.setAttribute("height", String(bandBottom - bandTop));
    band.setAttribute("class", "saydo-spark__band");
    svg.appendChild(band);

    var points = series
      .map(function (p, i) { return x(i) + "," + y(p.value); })
      .join(" ");
    var line = document.createElementNS(SVGNS, "polyline");
    line.setAttribute("points", points);
    line.setAttribute("class", "saydo-spark__line");
    svg.appendChild(line);
  }

  function initSparks(data) {
    var containers = Array.prototype.slice.call(
      document.querySelectorAll(".saydo-exposure")
    );
    containers.forEach(function (c) {
      var series = data.exposure_paths[c.dataset.instrument];
      drawSpark(c, series, parseFloat(c.dataset.delta));
    });
  }

  function initFocus() {
    var btn = document.querySelector("[data-saydo-focus]");
    var root = document.querySelector("[data-saydo]");
    if (!btn || !root) {
      return;
    }
    btn.addEventListener("click", function () {
      root.classList.toggle("saydo--focus");
    });
  }

  function init() {
    var data = readCardData();
    if (data) {
      initSparks(data);
    }
    initFocus();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
```

- [ ] **Step 5: Flip the `m5` manifest entry to live**

In `site/cards.yaml`, replace the `m5` entry (currently):

```yaml
- id: m5
  title: Say–do gap monitor
  lane: M
  one_liner: Does the portfolio match the letter? Say vs do, side by side.
  decisions: [monitor, engage]
  tiers: [R, E, P]
  status: planned
```

with:

```yaml
- id: m5
  title: Say–do gap monitor
  lane: M
  one_liner: Does the portfolio match the letter? Say vs do, side by side.
  decisions: [monitor, engage]
  tiers: [R, E, P]
  status: live
  demo: pages/m5-saydo.html.j2
  data: m5_saydo.json
  spec: m5-say-do-gap.md
  golive:
    data_ask: Letters (R) + exposure summaries (E)
    sample: n/a — per-letter analytic, eval-harness-gated
    effort: M–L (includes the eval harness)
```

- [ ] **Step 6: Update the shared index-count test**

In `tests/site/test_build.py`, three cards are now live (e1 + s1 + m5), so 17 remain planned. Change:

```python
    assert index.count("card-tile--planned") == 18
    assert 'href="e1.html"' in index
    assert 'href="s1.html"' in index
```

to:

```python
    assert index.count("card-tile--planned") == 17
    assert 'href="e1.html"' in index
    assert 'href="s1.html"' in index
    assert 'href="m5.html"' in index
```

- [ ] **Step 7: Run the tests to verify they pass**

Run: `PYTHONPATH=src pytest tests/site/test_m5.py tests/site/test_build.py -v`
Expected: PASS

- [ ] **Step 8: Commit**

```bash
git add site/templates/pages/m5-saydo.html.j2 site/assets/m5-saydo.js site/cards.yaml tests/site/test_build.py tests/site/test_m5.py
git commit -m "feat(site): M5 say-do split-screen demo page (live)"
```

---

### Task 4: Whole-site build integration & isolation verification

**Files:**
- Test: `tests/site/` (full suite) — no new files; this task is a verification gate.

**Interfaces:**
- Consumes: everything from Tasks 1–3.
- Produces: a confirmed green build with the import-isolation guard intact.

- [ ] **Step 1: Run the full site test suite**

Run: `PYTHONPATH=src pytest tests/site/ -v`
Expected: PASS for every test, including `tests/site/test_cli.py::test_site_build_import_isolation` (builder imports no numpy/pandas) and `tests/site/test_cli.py::test_cli_build_smoke`.

- [ ] **Step 2: Run the entire project test suite**

Run: `PYTHONPATH=src pytest -q`
Expected: PASS — no regression in demo-data, simulator, flagships, or adapter tests.

- [ ] **Step 3: Lint**

Run: `ruff check . && ruff format --check .`
Expected: clean (no findings). Note: `ruff` covers Python only; the new `.js`/`.css`/`.j2` files are not linted by ruff and are validated by the build-level tests above.

- [ ] **Step 4: Manual full-build smoke + copy-obligation grep**

Run:
```bash
PYTHONPATH=src uv run python -m quant_allocator.site build --out site/_build
grep -l "90% interval" site/_build/s1.html
grep -l "illustrative, uncalibrated" site/_build/m5.html
grep -c 'class="interval-stat"' site/_build/s1.html   # expect 40
ls site/_build/s1.html site/_build/m5.html site/_build/specs/s1.html site/_build/specs/m5.html
```
Expected: all files present; both greps match; interval-stat count is 40. (`site/_build` is the gitignored CI artifact path.)

- [ ] **Step 5: Optional local eyeball (not a gate)**

Run: `python -m http.server -d site/_build 8000` and open `http://localhost:8000/s1.html` and `/m5.html` to confirm bands position, the sort toggle reshuffles, and the M5 sparklines and focus toggle work. (Screenshot visual QA in light + dark is the separate later Playwright pass per design spec §11 — out of scope for this plan.)

- [ ] **Step 6: Commit (only if any lint fixups were needed)**

```bash
git add -A
git commit -m "chore(site): lint fixups for S1/M5 pages"
```

---

## Notes & deliberately-out-of-scope

- **Spec-page KaTeX:** flipping s1/m5 live renders their method specs (`specs/s1.html`, `specs/m5.html`) for the first time. `spec.html.j2` already wires vendored KaTeX (`site/assets/katex/` present), so their LaTeX renders. No action needed; math display fidelity is part of the later visual-QA pass, not this plan.
- **`delta_table` in `m5_saydo.json`** is redundant with each view's `measured.delta` for display purposes and is intentionally not rendered; per-view δ is the honest, in-context number.
- **No-JS fallback:** all numbers, quotes, verdicts, and range text are server-rendered and print-clean; JS only adds the band bars, sparklines, sort, and focus toggle. This is the sanctioned "JS may map values to pixels, sort, and toggle" behavior.

## Self-Review

**1. Spec coverage.** Design spec §5 "S1 · Posterior strip": manager code, T, OLS alpha {point, CI}, posterior {point, credible interval}, P(α>0), OLS-vs-posterior rank reshuffle with movement marks, advisory band, closed-form footnote — all in Task 2's template. §5 "M5 · Say–do split screen": letter quote + extracted view (direction/theme/conviction), measured exposure vs δ dead-band, verdict chip, contradiction centerpiece, illustrative-extraction honesty note linking §4 — all in Task 3's template. §5 go-live boxes: both drafted from the specs' §7 into `cards.yaml`. Builder §7 honest-mockup lint: unchanged and still enforced (Tasks 2/3 run the full `build()`). §10 import isolation: preserved by using stdlib `json` and re-verified in Task 4. Testing §11: build-level tests added (Tasks 1–4). Covered.

**2. Placeholder scan.** No "TBD"/"TODO"/"add error handling"/"similar to Task N". Every code step carries complete, transcribable content: full CSS block, two full templates, two full JS files, exact manifest YAML, exact test files, and exact old→new edits for `build.py` and `test_build.py`. No dangling references.

**3. Type consistency.** Template field paths match `s1_ledger.json` (`managers[].{code,group,months,ols_alpha.{ci_lo,point,ci_hi},posterior_alpha.{...},ols_rank,posterior_rank,prob_positive,advisory_band}`, `meta.n_managers`) and `m5_saydo.json` (`views[].{quote,direction,theme,conviction,instrument,label,letter_date,measured.{start,end,move,delta}}`, `meta.horizon_months`, `exposure_paths[instrument][].{month,value}`). The builder change adds `card_data` (dict) and JS reads the same JSON via `#card-data`. `dataset.olsRank`/`dataset.posteriorRank` correctly map the `data-ols-rank`/`data-posterior-rank` attributes. Planned-count edits chain consistently: 19 → 18 (Task 2) → 17 (Task 3), matching e1+s1+m5 = 3 live. Consistent.

**4. Plan review (2026-07-06):** approved with three inline fixes — P(α>0) display capped at &lt;0.01 / &gt;0.99 (doctrine: never display certainty as 0.00/1.00; the JSON's 1.0 is 6-digit rounding, not certainty), M5 methodology copy corrected to the actual Q6/Q7 dead-band semantics (partial = inside the dead-band in EITHER direction; stated-flat aligned only within ±δ), and Task 4 commands pinned to `PYTHONPATH=src uv run` + the gitignored `site/_build` output path.
