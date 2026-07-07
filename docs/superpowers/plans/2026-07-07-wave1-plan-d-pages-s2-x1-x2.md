# Wave-1 Plan D — S2 / X1 / X2 Demo Pages Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the three remaining wave-1 gallery demo pages — S2 (uncertainty-honest tear sheet), X1 (tier & power atlas sampler), X2 (transparency playground) — rendering only the already-CERTIFIED committed JSON, flipping each card `live`, all copy obligations test-asserted.

**Architecture:** Each page is a Jinja2 template extending `demo.html.j2` (which supplies the SYNTHETIC badge, tier row, methodology block, go-live furniture, and inlined `<script type="application/json" id="card-data">`), plus one vanilla ES5-IIFE JS file for SVG drawing / band positioning / dial handling, plus a page-specific CSS block appended to `interval.css`. The builder computes nothing; it renders committed inputs. X2 additionally needs two tiny builder capabilities — a dark default theme and a "never-goes-live" standing note in place of the go-live box — added in a dedicated builder-support task.

**Tech Stack:** Python 3.12 · Jinja2 (autoescape) · `quant_allocator.site.build` render-only builder · vanilla JS (no framework, ES5 style, `createElementNS` for SVG) · pytest build-level tests.

## Global Constraints

- **Branch:** `wave1-plan-d-pages`, from `main`. Plan doc: `docs/superpowers/plans/2026-07-07-wave1-plan-d-pages-s2-x1-x2.md`.
- **Scope is exactly:** three demo page templates + page CSS (appended to `interval.css`) + page JS + `cards.yaml` manifest flips + build-level tests + the minimal X2 builder support (theme + standing-note). **NO** generator changes, **NO** JSON changes, **NO** site-wide CSS overhaul, **NO** touching `site/data/*.json` or `src/quant_allocator/demo_data/*`.
- **No statistics computed in the browser.** X2 dials **snap** to computed cells: a dial change is a dictionary lookup of the cell key `"{ic:g}|{half_life:g}|{sizing:g}|{T}|{tier}"` (e.g. `"0.04|12|0.8|48|R"`) — never interpolation, never math. The D-22 per-analytic short array is read **positionally**: `[point, lo, hi, verdict, gate_state, threshold, units, wilson_hw]`.
- **Every displayed number is verbatim from `card_data`** via Jinja format filters (S2/X1, server-rendered) or via JS verbatim lookup + display-formatting only (X2 — the spec's mandated mechanism; unit conversions ×100 and descriptive counts allowed, as in the B2 pages).
- **Copy obligations — each MUST have a test assertion** (verbatim strings pinned per task below):
  - S2: Sharpe bands labeled exactly `95% interval`; alpha band exactly `90% interval`; drawdown envelope labeled `pointwise`; `rf_annual` labeled synthetic; de-smoothing story (reported vs de-smoothed Sharpe side by side, θ shown); alt-beta VerdictChip.
  - X1: power-curve exhibits labeled with the JSON `realized_ir` values; posterior label `cohort-informed; ~10% false-attribution at IC=0 — the price of borrowing strength`; degradation table; registry snippet whose null thresholds render as `no tenure in the measured range suffices`; headline `only the E-tier shrinkage posterior reaches 80% power within a 10-year record`.
  - X2: dark theme by default; dials for ic/half_life/sizing/T/tier; IntervalStat + VerdictChip + PowerGate per analytic; closed PowerGates render a dashed empty state that, when threshold is null, states `no threshold reached in the measured range`; Wilson half-width footnote SHOWN; go-live box REPLACED by the standing statement `this page is the thesis, not a product — it never goes live`; IC=0 column labeled `false-alarm rate`.
- **Provenance furniture** (from `demo.html.j2`, unchanged) must survive on every page: `synthetic-badge`, `golive-box` (or, for X2, `golive-replaced`), inlined `card-data` script, spec link. The honest-mockup lint enforces this.
- **Planned-tile count** in `tests/site/test_build.py` steps down as each card flips: 17 → 16 (S2) → 15 (X1) → 14 (X2).
- **Model policy:** implementers (this plan carries complete code — transcribe, do not design), senior per-task reviewers, senior final whole-branch review, copy-obligation certification before merge (pages render already-CERTIFIED data, so **no new numerics gate** — the gate here is the copy gate, the lead reviewer's).
- **JS style:** vanilla, ES5-style `(function () { "use strict"; ... })()` IIFE like `s1-ledger.js` / `m5-saydo.js`; SVG via `document.createElementNS("http://www.w3.org/2000/svg", …)` following `m5-saydo.js`. One file per page: `site/assets/s2-tearsheet.js`, `x1-atlas.js`, `x2-playground.js`. No new libraries.
- **Data is frozen and certified** (numerics gate cleared 2026-07-07). Field references below are transcribed from the committed JSON; do not recompute.

---

## File Structure

| File | Responsibility | Task |
| --- | --- | --- |
| `site/templates/pages/s2-tearsheet.html.j2` (create) | S2 tear-sheet page content (extends `demo.html.j2`) | 1 |
| `site/assets/s2-tearsheet.js` (create) | S2 band positioning + drawdown SVG + monthly-return strip SVG | 1 |
| `site/assets/interval.css` (append S2 block) | S2 page-specific classes | 1 |
| `site/cards.yaml` (modify `s2` entry) | flip s2 → live | 1 |
| `tests/site/test_s2.py` (create) | S2 build-level tests | 1 |
| `tests/site/test_build.py` (modify count) | planned 17 → 16 | 1 |
| `site/templates/pages/x1-atlas.html.j2` (create) | X1 atlas sampler page content | 2 |
| `site/assets/x1-atlas.js` (create) | X1 power-curve SVGs | 2 |
| `site/assets/interval.css` (append X1 block) | X1 page-specific classes | 2 |
| `site/cards.yaml` (modify `x1` entry) | flip x1 → live | 2 |
| `tests/site/test_x1.py` (create) | X1 build-level tests | 2 |
| `tests/site/test_build.py` (modify count) | planned 16 → 15 | 2 |
| `src/quant_allocator/site/build.py` (modify) | `standing_note` + `theme` support in validation, render, lint | 3 |
| `site/templates/demo.html.j2` (modify) | three-way go-live region (usage-note / golive-replaced / golive-box) | 3 |
| `site/assets/interval.css` (append golive-replaced rule) | standing-note styling | 3 |
| `tests/site/test_lint.py` (add tests) | standing-note lint acceptance | 3 |
| `tests/site/test_manifest.py` (add tests) | standing_note / theme validation | 3 |
| `site/templates/pages/x2-playground.html.j2` (create) | X2 playground page content (dials + analytic scaffolding + standing note) | 4 |
| `site/assets/x2-playground.js` (create) | dial state, cell lookup, DOM repaint, false-alarm banner | 4 |
| `site/assets/interval.css` (append X2 block) | X2 page-specific classes | 4 |
| `site/cards.yaml` (modify `x2` entry) | flip x2 → live (doctrine:false, standing_note, theme:dark) | 4 |
| `tests/site/test_x2.py` (create) | X2 build-level tests | 4 |
| `tests/site/test_build.py` (modify count) | planned 15 → 14 | 4 |

**Run the whole suite** with `python -m pytest tests/site -q` from the repo root after each task.

---

### Task 1: S2 · Uncertainty-honest tear-sheet page

**Files:**
- Create: `site/templates/pages/s2-tearsheet.html.j2`
- Create: `site/assets/s2-tearsheet.js`
- Modify: `site/assets/interval.css` (append the `=== S2 tear sheet ===` block)
- Modify: `site/cards.yaml:15-21` (the `s2` entry)
- Modify: `tests/site/test_build.py:41` (`card-tile--planned` count 17 → 16)
- Test: `tests/site/test_s2.py`

**Interfaces:**
- Consumes (from the builder, unchanged): `demo.html.j2` passes `card` (manifest dict), `card_data` (parsed JSON of `site/data/s2_tearsheet.json`), `card_data_json` (raw string, inlined by `demo.html.j2`), `asset_base` (`""` for demo pages). The S2 template overrides `{% block demo_content %}`, `{% block methodology %}`, `{% block body_scripts %}`.
- `card_data` shape (verbatim from committed JSON): `card_data.statistics.sharpe_reported.{point,ci_lo,ci_hi}` = `{0.708543,-0.26107,1.669494}`; `.sharpe_desmoothed.{point,ci_lo,ci_hi}` = `{0.597257,-0.291789,1.460354}`; `.alpha.{point,ci_lo,ci_hi}` = `{0.032342,-0.043751,0.108435}`; `.mppm.point` = `0.030511`. `card_data.theta` = `[0.824455,0.175545,0.0]`. `card_data.unsmoothing.{applied,skip_reason,vol_ratio}` = `{true,null,0.842936}`. `card_data.factor_betas.{market,momentum,size,value}` = `{0.231408,0.23686,0.070166,-0.091131}`. `card_data.alt_beta.{chip,ci_lo,ci_hi,level}` = `{"provisionally alternative beta",-0.043751,0.108435,0.9}`. `card_data.drawdown_band.{p50,p95,p99,realized,ar1,breaches_p99}` (four 48-element arrays + scalars). `card_data.monthly_returns` (48 floats). `card_data.meta.{manager_code,months,rf_annual,strategy,tier}` = `{"M07",48,0.02,"equity_long_short","R"}`.
- Produces: the rendered `s2.html` and `assets/s2-tearsheet.js`. No other task depends on Task 1 outputs.

- [ ] **Step 1: Write the failing tests**

Create `tests/site/test_s2.py`:

```python
from pathlib import Path

from quant_allocator.site.build import build

REPO_ROOT = Path(__file__).resolve().parents[2]


def _build(tmp_path):
    out = tmp_path / "out"
    build(REPO_ROOT / "site", out)
    return (out / "s2.html").read_text(encoding="utf-8"), out


def test_s2_provenance_and_copy(tmp_path):
    html, out = _build(tmp_path)
    # Provenance furniture from demo.html.j2.
    assert "synthetic-badge" in html
    assert "SYNTHETIC DATA" in html
    assert "golive-box" in html
    assert 'id="card-data"' in html
    assert "specs/s2.html" in html
    assert (out / "specs" / "s2.html").exists()
    # copy obligations (verbatim band labels).
    assert "95% interval" in html   # both Sharpe stats
    assert "90% interval" in html   # alpha stat
    assert "pointwise" in html      # drawdown null envelope
    # rf_annual labeled synthetic.
    assert "2.0%" in html
    assert "(synthetic)" in html


def test_s2_desmoothing_and_altbeta(tmp_path):
    html, _ = _build(tmp_path)
    # De-smoothing story: reported vs de-smoothed Sharpe side by side.
    assert "0.71" in html          # reported Sharpe point (0.708543)
    assert "0.60" in html          # de-smoothed Sharpe point (0.597257)
    # Theta shown.
    assert "0.82" in html          # theta_0 (0.824455)
    # Alt-beta VerdictChip states the label and its CI.
    assert 'class="verdict-chip"' in html
    assert "provisionally alternative beta" in html
    # Interval alpha verbatim.
    assert "+3.2%" in html         # alpha point (0.032342)
    # Two Sharpe IntervalStats + one alpha IntervalStat share the interval-stat class.
    assert html.count('class="interval-stat"') >= 3


def test_s2_drawdown_and_strip(tmp_path):
    html, _ = _build(tmp_path)
    # Drawdown chart + monthly strip SVG scaffolding rendered server-side.
    assert "s2-drawdown" in html
    assert "s2-strip" in html
    # Realized path stays within the 99th-percentile envelope (breaches_p99 == false).
    assert "within the 99th-percentile envelope" in html


def test_s2_script_loaded(tmp_path):
    html, out = _build(tmp_path)
    assert "assets/s2-tearsheet.js" in html
    assert (out / "assets" / "s2-tearsheet.js").exists()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/site/test_s2.py -q`
Expected: FAIL — `s2.html` is not built (card `s2` is still `planned`, so the builder writes no `s2.html`; the read raises `FileNotFoundError`).

- [ ] **Step 3: Create the S2 page template**

Create `site/templates/pages/s2-tearsheet.html.j2` (all numbers via Jinja format filters over `card_data`; the `data-*` attributes feed the JS band-positioner exactly like `s1-ledger.html.j2`):

```jinja
{% extends "demo.html.j2" %}

{% set st = card_data.statistics %}
{% set ab = card_data.alt_beta %}
{% set dd = card_data.drawdown_band %}

{% block demo_content %}
<section class="tearsheet-intro">
  <p class="tearsheet-headline">
    One synthetic manager (<strong>{{ card_data.meta.manager_code }}</strong>, equity
    long/short, {{ card_data.meta.months }} months, tier {{ card_data.meta.tier }}). Every
    statistic ships as an interval with a verdict &mdash; no bare point, no overstated
    confidence. Risk-free {{ "%.1f"|format(card_data.meta.rf_annual * 100) }}%/yr
    <span class="tearsheet-synthetic">(synthetic)</span>.
  </p>
</section>

<section class="tearsheet-panel">
  <h2 class="tearsheet-panel__title">De-smoothing &mdash; reported vs economic Sharpe</h2>
  <p class="tearsheet-note">
    Getmansky&ndash;Lo&ndash;Makarov unsmoothing restores the volatility that smoothed
    marks hide, so the economic Sharpe is lower. Smoothing kernel
    &theta; = ({{ "%.2f"|format(card_data.theta[0]) }},
    {{ "%.2f"|format(card_data.theta[1]) }},
    {{ "%.2f"|format(card_data.theta[2]) }}); vol ratio
    {{ "%.2f"|format(card_data.unsmoothing.vol_ratio) }}. De-smoothing lowers the Sharpe
    from {{ "%.2f"|format(st.sharpe_reported.point) }} to
    {{ "%.2f"|format(st.sharpe_desmoothed.point) }}.
  </p>
  <div class="tearsheet-stat-pair">
    <div class="interval-stat" data-domain="sharpe"
         data-lo="{{ st.sharpe_reported.ci_lo }}"
         data-point="{{ st.sharpe_reported.point }}"
         data-hi="{{ st.sharpe_reported.ci_hi }}">
      <span class="interval-stat__label">Reported Sharpe</span>
      <span class="interval-stat__value">{{ "%.2f"|format(st.sharpe_reported.point) }}</span>
      <div class="interval-stat__rail">
        <div class="interval-stat__band"></div>
        <div class="interval-stat__point"></div>
      </div>
      <span class="interval-stat__range">95% interval {{ "%.2f"|format(st.sharpe_reported.ci_lo) }} &hellip; {{ "%.2f"|format(st.sharpe_reported.ci_hi) }}</span>
    </div>

    <div class="interval-stat" data-domain="sharpe"
         data-lo="{{ st.sharpe_desmoothed.ci_lo }}"
         data-point="{{ st.sharpe_desmoothed.point }}"
         data-hi="{{ st.sharpe_desmoothed.ci_hi }}">
      <span class="interval-stat__label">De-smoothed Sharpe</span>
      <span class="interval-stat__value">{{ "%.2f"|format(st.sharpe_desmoothed.point) }}</span>
      <div class="interval-stat__rail">
        <div class="interval-stat__band"></div>
        <div class="interval-stat__point"></div>
      </div>
      <span class="interval-stat__range">95% interval {{ "%.2f"|format(st.sharpe_desmoothed.ci_lo) }} &hellip; {{ "%.2f"|format(st.sharpe_desmoothed.ci_hi) }}</span>
    </div>
  </div>
  <p class="tearsheet-mppm">
    MPPM (&rho;=3) {{ "%+.1f"|format(st.mppm.point * 100) }}%/yr, shown beside the Sharpe
    as a manipulation check &mdash; the Sharpe&ndash;MPPM <em>gap</em>, not the level, is
    the signal.
  </p>
</section>

<section class="tearsheet-panel">
  <h2 class="tearsheet-panel__title">Factor regression &mdash; interval alpha</h2>
  <div class="tearsheet-factor">
    <div class="interval-stat" data-domain="alpha"
         data-lo="{{ st.alpha.ci_lo }}"
         data-point="{{ st.alpha.point }}"
         data-hi="{{ st.alpha.ci_hi }}">
      <span class="interval-stat__label">Annualized alpha</span>
      <span class="interval-stat__value">{{ "%+.1f"|format(st.alpha.point * 100) }}%</span>
      <div class="interval-stat__rail">
        <div class="interval-stat__band"></div>
        <div class="interval-stat__point"></div>
      </div>
      <span class="interval-stat__range">90% interval {{ "%+.1f"|format(st.alpha.ci_lo * 100) }}% &hellip; {{ "%+.1f"|format(st.alpha.ci_hi * 100) }}%</span>
    </div>
    <dl class="tearsheet-betas">
      <dt>Market</dt><dd>{{ "%.2f"|format(card_data.factor_betas.market) }}</dd>
      <dt>Size</dt><dd>{{ "%.2f"|format(card_data.factor_betas.size) }}</dd>
      <dt>Value</dt><dd>{{ "%.2f"|format(card_data.factor_betas.value) }}</dd>
      <dt>Momentum</dt><dd>{{ "%.2f"|format(card_data.factor_betas.momentum) }}</dd>
    </dl>
  </div>
  <div class="tearsheet-altbeta">
    <span class="verdict-chip" data-verdict="shrink">{{ ab.chip }}</span>
    <span class="tearsheet-altbeta__ci">
      alpha {{ "%.0f"|format(ab.level * 100) }}% CI
      {{ "%+.1f"|format(ab.ci_lo * 100) }}% &hellip; {{ "%+.1f"|format(ab.ci_hi * 100) }}%
      &mdash; not distinguishable from factor beta at this track length.
    </span>
  </div>
</section>

<section class="tearsheet-panel">
  <h2 class="tearsheet-panel__title">Drawdown vs simulation-calibrated null</h2>
  <p class="tearsheet-note">
    The realized drawdown path against the <strong>pointwise</strong> 50 / 95 / 99th
    percentile null envelope (AR(1) {{ "%.2f"|format(dd.ar1) }}). The realized path
    <strong>stays within the 99th-percentile envelope</strong> &mdash; an ordinary
    drawdown under the paid-for-skill hypothesis.
  </p>
  <svg class="s2-drawdown" viewBox="0 0 100 40" preserveAspectRatio="none"
       role="img" aria-label="Realized drawdown against the pointwise null envelope"></svg>
</section>

<section class="tearsheet-panel">
  <h2 class="tearsheet-panel__title">Monthly returns</h2>
  <svg class="s2-strip" viewBox="0 0 100 30" preserveAspectRatio="none"
       role="img" aria-label="Monthly return strip"></svg>
</section>
{% endblock %}

{% block methodology %}
<p>Six pure stages over the return series and a fully synthetic factor set:
unsmoothing (Getmansky&ndash;Lo&ndash;Makarov MA(2)), factor regression, interval
machinery (Lo SE + Ledoit&ndash;Wolf bootstrap for the Sharpe, Newey&ndash;West for the
alpha), MPPM, and the simulation-calibrated drawdown band. Every statistic is an
interval; a bare point is a design-system error.</p>
<p>The alt-beta chip is a <em>calibration statement about track length</em>, not an
accusation: the alpha's 90% interval includes zero at 48 months, which opens a
fees-for-beta conversation &mdash; it does not claim the manager has no skill.</p>
{% endblock %}

{% block body_scripts %}
<script src="{{ asset_base | default('') }}assets/s2-tearsheet.js"></script>
{% endblock %}
```

- [ ] **Step 4: Create the S2 JS**

Create `site/assets/s2-tearsheet.js`:

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

  // Position IntervalStat bands on a shared pixel domain per data-domain group so
  // stats in the same group are visually comparable. Reads verbatim numbers from
  // data-* attributes; computes only pixel positions, never a displayed number.
  function positionBands() {
    var stats = Array.prototype.slice.call(
      document.querySelectorAll(".tearsheet-panel .interval-stat")
    );
    var groups = {};
    stats.forEach(function (s) {
      var key = s.dataset.domain || "_";
      (groups[key] = groups[key] || []).push(s);
    });
    Object.keys(groups).forEach(function (key) {
      var members = groups[key];
      var los = members.map(function (s) { return parseFloat(s.dataset.lo); });
      var his = members.map(function (s) { return parseFloat(s.dataset.hi); });
      var min = Math.min.apply(null, los);
      var max = Math.max.apply(null, his);
      var span = max - min;
      if (span <= 0) {
        return;
      }
      members.forEach(function (s) {
        var lo = parseFloat(s.dataset.lo);
        var hi = parseFloat(s.dataset.hi);
        var point = parseFloat(s.dataset.point);
        var band = s.querySelector(".interval-stat__band");
        var mark = s.querySelector(".interval-stat__point");
        band.style.left = ((lo - min) / span) * 100 + "%";
        band.style.width = ((hi - lo) / span) * 100 + "%";
        mark.style.left = ((point - min) / span) * 100 + "%";
      });
    });
  }

  function makeEl(name, cls) {
    var el = document.createElementNS(SVGNS, name);
    if (cls) {
      el.setAttribute("class", cls);
    }
    return el;
  }

  // Drawdown chart: drawdowns are <= 0, so 0 sits at the top and the deepest
  // envelope point sits at the bottom. Areas for p99/p95, lines for p50/realized.
  function drawDrawdown(band) {
    var svg = document.querySelector(".s2-drawdown");
    if (!svg || !band) {
      return;
    }
    var W = 100;
    var H = 40;
    var all = band.p99.concat(band.p95, band.p50, band.realized);
    var minVal = Math.min.apply(null, all);
    if (minVal >= 0) {
      return;
    }
    var n = band.realized.length;
    function x(i) { return (i / (n - 1)) * W; }
    function y(v) { return (v / minVal) * H; } // v,minVal <= 0 -> [0, H]

    function area(arr, cls) {
      var pts = arr.map(function (v, i) { return x(i) + "," + y(v); });
      pts.push(x(n - 1) + ",0", x(0) + ",0");
      var poly = makeEl("polygon", cls);
      poly.setAttribute("points", pts.join(" "));
      svg.appendChild(poly);
    }
    function line(arr, cls) {
      var pts = arr.map(function (v, i) { return x(i) + "," + y(v); }).join(" ");
      var pl = makeEl("polyline", cls);
      pl.setAttribute("points", pts);
      svg.appendChild(pl);
    }

    area(band.p99, "s2-drawdown__p99");
    area(band.p95, "s2-drawdown__p95");
    line(band.p50, "s2-drawdown__p50");
    line(band.realized, "s2-drawdown__realized");
  }

  // Monthly return strip: bars from a midline, positive up / negative down.
  function drawStrip(returns) {
    var svg = document.querySelector(".s2-strip");
    if (!svg || !returns || !returns.length) {
      return;
    }
    var W = 100;
    var H = 30;
    var mid = H / 2;
    var maxAbs = returns.reduce(function (m, v) {
      return Math.max(m, Math.abs(v));
    }, 0) || 1;
    var bw = W / returns.length;
    returns.forEach(function (v, i) {
      var h = (Math.abs(v) / maxAbs) * (H / 2);
      var rect = makeEl("rect", v >= 0 ? "s2-strip__pos" : "s2-strip__neg");
      rect.setAttribute("x", String(i * bw));
      rect.setAttribute("y", String(v >= 0 ? mid - h : mid));
      rect.setAttribute("width", String(bw * 0.8));
      rect.setAttribute("height", String(h || 0.1));
      svg.appendChild(rect);
    });
  }

  function init() {
    positionBands();
    var data = readCardData();
    if (data) {
      drawDrawdown(data.drawdown_band);
      drawStrip(data.monthly_returns);
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
```

- [ ] **Step 5: Append the S2 CSS block**

Append to `site/assets/interval.css` (after the M5 block at the end of the file):

```css
/* === S2 tear sheet ============================================== */
.tearsheet-intro {
  margin: 8px 0 20px;
}

.tearsheet-headline {
  font-size: 15px;
  line-height: 1.5;
}

.tearsheet-synthetic {
  color: var(--warn);
}

.tearsheet-panel {
  margin: 20px 0;
  padding-top: 16px;
  border-top: 1px solid var(--line);
}

.tearsheet-panel__title {
  font-size: 15px;
  margin: 0 0 10px;
}

.tearsheet-note {
  font-size: 13px;
  color: var(--dim);
  margin: 0 0 12px;
}

.tearsheet-stat-pair,
.tearsheet-factor {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  align-items: start;
}

@media (max-width: 640px) {
  .tearsheet-stat-pair,
  .tearsheet-factor {
    grid-template-columns: 1fr;
  }
}

.tearsheet-mppm {
  margin: 12px 0 0;
  font-size: 13px;
  color: var(--dim);
}

.tearsheet-betas {
  display: grid;
  grid-template-columns: max-content 1fr;
  gap: 2px 12px;
  margin: 0;
  font-size: 13px;
  font-variant-numeric: tabular-nums;
}

.tearsheet-betas dt {
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: 0.10em;
  color: var(--dim);
  align-self: center;
}

.tearsheet-betas dd {
  margin: 0;
}

.tearsheet-altbeta {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 10px;
  margin-top: 12px;
}

.tearsheet-altbeta__ci {
  font-size: 12px;
  color: var(--dim);
  font-variant-numeric: tabular-nums;
}

.s2-drawdown {
  display: block;
  width: 100%;
  height: 160px;
}

.s2-drawdown__p99 { fill: var(--track); }
.s2-drawdown__p95 { fill: var(--band); }
.s2-drawdown__p50 { fill: none; stroke: var(--dim); stroke-width: 1; stroke-dasharray: 2 2; vector-effect: non-scaling-stroke; }
.s2-drawdown__realized { fill: none; stroke: var(--neg); stroke-width: 1.5; vector-effect: non-scaling-stroke; }

.s2-strip {
  display: block;
  width: 100%;
  height: 90px;
}

.s2-strip__pos { fill: var(--pos); }
.s2-strip__neg { fill: var(--neg); }
```

- [ ] **Step 6: Flip the s2 manifest entry to live**

In `site/cards.yaml`, replace the `s2` entry (currently lines 15-21, ending at `status: planned`) with:

```yaml
- id: s2
  title: Uncertainty-honest tear-sheet engine
  lane: S
  one_liner: Every statistic as an interval with a verdict — honest by construction.
  decisions: [monitor, select]
  tiers: [R, E, P]
  status: live
  demo: pages/s2-tearsheet.html.j2
  data: s2_tearsheet.json
  spec: s2-tear-sheet-engine.md
  golive:
    data_ask: Monthly net returns (R) + risk-free series + strategy factor set
    sample: ≥36 months
    effort: S–M
```

- [ ] **Step 7: Step the planned-tile count down in test_build.py**

In `tests/site/test_build.py`, change the assertion at line 41:

```python
    assert index.count("card-tile--planned") == 16
```

- [ ] **Step 8: Run the S2 tests and the full site suite**

Run: `python -m pytest tests/site/test_s2.py tests/site/test_build.py -q`
Expected: PASS (all S2 tests green; `test_index_lists_all_cards` green with the new count).

Run: `python -m pytest tests/site -q`
Expected: PASS (no regressions).

- [ ] **Step 9: Lint check**

Run: `ruff check tests/site/test_s2.py`
Expected: clean.

- [ ] **Step 10: Commit**

```bash
git add site/templates/pages/s2-tearsheet.html.j2 site/assets/s2-tearsheet.js \
        site/assets/interval.css site/cards.yaml \
        tests/site/test_s2.py tests/site/test_build.py
git commit -m "feat(site): S2 uncertainty-honest tear-sheet demo page"
```

---

### Task 2: X1 · Tier & Power Atlas sampler page

**Files:**
- Create: `site/templates/pages/x1-atlas.html.j2`
- Create: `site/assets/x1-atlas.js`
- Modify: `site/assets/interval.css` (append the `=== X1 atlas ===` block)
- Modify: `site/cards.yaml` (the `x1` entry)
- Modify: `tests/site/test_build.py` (`card-tile--planned` count 16 → 15)
- Test: `tests/site/test_x1.py`

**Interfaces:**
- Consumes (unchanged builder): `card`, `card_data` (parsed `site/data/x1_atlas.json`), `card_data_json`, `asset_base`.
- `card_data` shape (verbatim): `card_data.power_curves` is a 3-element list; each item = `{ "T":[24,36,48,60,120], "ic":<float>, "ols_ttest":[5 floats], "posterior":[5 floats], "realized_ir":<float> }` with `realized_ir` = `0.295` (ic 0.02), `0.648` (ic 0.04), `1.567` (ic 0.1). `card_data.degradation_table` = `{ "T":48, "ic":0.04, "alpha_estimation":{"E":{"power":0.318,"rmse":0.03698},"R":{"power":0.252,"rmse":0.040339}}, "hit_rate_P":{"power":0.132}, "sizing_skill_P":{"power":0.234}, "drift_detection":"deferred (exposure-drift detector, X1 spec §3.2 — docket D-11)" }`. `card_data.registry_snippet.metrics` = `{ "hit_rate":{...,"threshold":null}, "ols_alpha_ttest":{...,"threshold":null} }`, each metric with keys `effect, gate_quantity, min_tier, power_at_threshold, size, threshold`. `card_data.registry_snippet.{run,version}`.
- Produces: rendered `x1.html` + `assets/x1-atlas.js`. No downstream task depends on it.

- [ ] **Step 1: Write the failing tests**

Create `tests/site/test_x1.py`:

```python
from pathlib import Path

from quant_allocator.site.build import build

REPO_ROOT = Path(__file__).resolve().parents[2]


def _build(tmp_path):
    out = tmp_path / "out"
    build(REPO_ROOT / "site", out)
    return (out / "x1.html").read_text(encoding="utf-8"), out


def test_x1_provenance_and_headline(tmp_path):
    html, out = _build(tmp_path)
    assert "synthetic-badge" in html
    assert "golive-box" in html
    assert 'id="card-data"' in html
    assert "specs/x1.html" in html
    assert (out / "specs" / "x1.html").exists()
    # Atlas headline copy obligation.
    assert "only the E-tier shrinkage posterior reaches 80% power within a 10-year record" in html


def test_x1_power_curves_and_posterior_label(tmp_path):
    html, _ = _build(tmp_path)
    # Realized IR labels drawn from the JSON realized_ir fields.
    assert "realized IR 0.65" in html   # ic 0.04 -> 0.648
    assert "realized IR 1.57" in html   # ic 0.10 -> 1.567
    # Three power-curve SVG exhibits.
    assert html.count("x1-powercurve") >= 3
    # Posterior label copy obligation (false-attribution price of borrowing strength).
    assert "the price of borrowing strength" in html
    assert "false-attribution at IC=0" in html


def test_x1_degradation_table(tmp_path):
    html, _ = _build(tmp_path)
    # Degradation table powers verbatim from the JSON (at T=48, IC=0.04).
    assert "25.2%" in html   # alpha_estimation R power
    assert "31.8%" in html   # alpha_estimation E power
    assert "13.2%" in html   # hit_rate_P power
    assert "23.4%" in html   # sizing_skill_P power
    assert "deferred" in html  # drift_detection


def test_x1_registry_snippet_null_thresholds(tmp_path):
    html, _ = _build(tmp_path)
    # Null thresholds render as the no-tenure statement, not "null".
    assert "no tenure in the measured range suffices" in html
    assert "x1-registry" in html


def test_x1_script_loaded(tmp_path):
    html, out = _build(tmp_path)
    assert "assets/x1-atlas.js" in html
    assert (out / "assets" / "x1-atlas.js").exists()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/site/test_x1.py -q`
Expected: FAIL — `x1.html` not built (`x1` still `planned`).

- [ ] **Step 3: Create the X1 page template**

Create `site/templates/pages/x1-atlas.html.j2`:

```jinja
{% extends "demo.html.j2" %}

{% set deg = card_data.degradation_table %}
{% set reg = card_data.registry_snippet %}

{% block demo_content %}
<section class="atlas-intro">
  <p class="atlas-headline">
    How much data until a metric means anything? At a reference effect,
    <strong>only the E-tier shrinkage posterior reaches 80% power within a 10-year
    record</strong>. Frequentist tests never clear the bar in the measured range.
  </p>
</section>

<section class="tearsheet-panel">
  <h2 class="tearsheet-panel__title">Exhibit 1 &mdash; power curves: OLS t-test vs shrinkage posterior</h2>
  <p class="atlas-poster-label">
    cohort-informed; ~10% false-attribution at IC=0 &mdash; the price of borrowing strength
  </p>
  <div class="atlas-curves">
    {% for curve in card_data.power_curves %}
    <figure class="atlas-curve">
      <svg class="x1-powercurve" viewBox="0 0 100 44" preserveAspectRatio="none"
           role="img" aria-label="Power vs sample length"
           data-t="{{ curve.T | join(',') }}"
           data-ols="{{ curve.ols_ttest | join(',') }}"
           data-posterior="{{ curve.posterior | join(',') }}"></svg>
      <figcaption class="atlas-curve__cap">
        realized IR {{ "%.2f"|format(curve.realized_ir) }}
        <span class="atlas-curve__legend">
          <span class="atlas-legend atlas-legend--ols">OLS t-test</span>
          <span class="atlas-legend atlas-legend--posterior">posterior</span>
        </span>
      </figcaption>
    </figure>
    {% endfor %}
  </div>
  <p class="tearsheet-note">Dashed line marks the 80% power threshold; x-axis is T (months),
  24 to 120.</p>
</section>

<section class="tearsheet-panel">
  <h2 class="tearsheet-panel__title">Exhibit 2 &mdash; tier degradation (T={{ deg.T }}, IC={{ "%.2f"|format(deg.ic) }})</h2>
  <table class="atlas-degradation">
    <thead>
      <tr><th>Analytic</th><th>Tier</th><th>Power</th><th>RMSE</th></tr>
    </thead>
    <tbody>
      <tr><td>Alpha estimation</td><td>R</td><td>{{ "%.1f"|format(deg.alpha_estimation.R.power * 100) }}%</td><td>{{ "%.4f"|format(deg.alpha_estimation.R.rmse) }}</td></tr>
      <tr><td>Alpha estimation</td><td>E</td><td>{{ "%.1f"|format(deg.alpha_estimation.E.power * 100) }}%</td><td>{{ "%.4f"|format(deg.alpha_estimation.E.rmse) }}</td></tr>
      <tr><td>Hit rate</td><td>P</td><td>{{ "%.1f"|format(deg.hit_rate_P.power * 100) }}%</td><td>&mdash;</td></tr>
      <tr><td>Sizing skill</td><td>P</td><td>{{ "%.1f"|format(deg.sizing_skill_P.power * 100) }}%</td><td>&mdash;</td></tr>
      <tr><td>Drift detection</td><td>E vs R</td><td colspan="2">{{ deg.drift_detection }}</td></tr>
    </tbody>
  </table>
</section>

<section class="tearsheet-panel">
  <h2 class="tearsheet-panel__title">Exhibit 3 &mdash; PowerGate registry (sampler)</h2>
  <p class="tearsheet-note">The machine-readable thresholds file every gated card consumes.
  A null threshold means the metric never reaches 80% power in the measured range.</p>
  <dl class="x1-registry">
    {% for name, m in reg.metrics.items() %}
    <div class="x1-registry__row">
      <dt class="x1-registry__metric">{{ name }}</dt>
      <dd class="x1-registry__body">
        <span class="x1-registry__field">min tier {{ m.min_tier }}</span>
        <span class="x1-registry__field">gate: {{ m.gate_quantity }}</span>
        <span class="x1-registry__field">effect: {{ m.effect }}</span>
        <span class="x1-registry__field">size {{ "%.2f"|format(m.size) }}, power@thr {{ "%.2f"|format(m.power_at_threshold) }}</span>
        <span class="x1-registry__threshold">
          {% if m.threshold is none %}no tenure in the measured range suffices{% else %}threshold {{ m.threshold }} {{ m.gate_quantity }}{% endif %}
        </span>
      </dd>
    </div>
    {% endfor %}
  </dl>
</section>
{% endblock %}

{% block methodology %}
<p>The simulator emits all three transparency tiers of the same known ground truth, so
every metric is scored against the truth at every tier and sample size. Power =
P(detect | effect present); size = P(detect | IC = 0); the IC=0 column is the
false-alarm rate, not filler. Each power number carries a Wilson 95% interval
(±1.6% at 1,000 reps).</p>
<p>The shrinkage posterior borrows strength across a strategy cohort, buying power at
short tenures &mdash; at the cost of ~10% false-attribution at IC=0. That is the price
of borrowing strength, stated plainly rather than hidden.</p>
{% endblock %}

{% block body_scripts %}
<script src="{{ asset_base | default('') }}assets/x1-atlas.js"></script>
{% endblock %}
```

- [ ] **Step 4: Create the X1 JS**

Create `site/assets/x1-atlas.js`:

```javascript
(function () {
  "use strict";

  var SVGNS = "http://www.w3.org/2000/svg";

  function makeEl(name, cls) {
    var el = document.createElementNS(SVGNS, name);
    if (cls) {
      el.setAttribute("class", cls);
    }
    return el;
  }

  function nums(attr) {
    return attr.split(",").map(function (v) { return parseFloat(v); });
  }

  // Draw one power-curve exhibit: power (0..1) on y, T on x, two lines
  // (OLS t-test, posterior) plus a dashed 80%-power reference line.
  function drawCurve(svg) {
    var T = nums(svg.dataset.t);
    var ols = nums(svg.dataset.ols);
    var posterior = nums(svg.dataset.posterior);
    if (!T.length) {
      return;
    }
    var W = 100;
    var H = 44;
    var tMin = T[0];
    var tMax = T[T.length - 1];
    var tSpan = tMax - tMin || 1;
    function x(t) { return ((t - tMin) / tSpan) * W; }
    function y(p) { return H - p * H; } // power in [0,1]

    var ref = makeEl("line", "x1-powercurve__ref");
    ref.setAttribute("x1", "0");
    ref.setAttribute("y1", String(y(0.8)));
    ref.setAttribute("x2", String(W));
    ref.setAttribute("y2", String(y(0.8)));
    svg.appendChild(ref);

    function line(arr, cls) {
      var pts = arr.map(function (p, i) { return x(T[i]) + "," + y(p); }).join(" ");
      var pl = makeEl("polyline", cls);
      pl.setAttribute("points", pts);
      svg.appendChild(pl);
    }
    line(ols, "x1-powercurve__ols");
    line(posterior, "x1-powercurve__posterior");
  }

  function init() {
    Array.prototype.slice
      .call(document.querySelectorAll(".x1-powercurve"))
      .forEach(drawCurve);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
```

- [ ] **Step 5: Append the X1 CSS block**

Append to `site/assets/interval.css` (after the S2 block):

```css
/* === X1 atlas =================================================== */
.atlas-intro {
  margin: 8px 0 20px;
}

.atlas-headline {
  font-size: 15px;
  line-height: 1.5;
}

.atlas-poster-label {
  font-size: 12px;
  color: var(--warn);
  margin: 0 0 12px;
}

.atlas-curves {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}

@media (max-width: 640px) {
  .atlas-curves {
    grid-template-columns: 1fr;
  }
}

.atlas-curve {
  margin: 0;
}

.x1-powercurve {
  display: block;
  width: 100%;
  height: 88px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: var(--paper);
}

.x1-powercurve__ref { stroke: var(--dim); stroke-width: 1; stroke-dasharray: 2 2; vector-effect: non-scaling-stroke; }
.x1-powercurve__ols { fill: none; stroke: var(--dim); stroke-width: 1.5; vector-effect: non-scaling-stroke; }
.x1-powercurve__posterior { fill: none; stroke: var(--accent); stroke-width: 1.5; vector-effect: non-scaling-stroke; }

.atlas-curve__cap {
  font-size: 12px;
  color: var(--dim);
  margin-top: 6px;
  font-variant-numeric: tabular-nums;
}

.atlas-curve__legend {
  display: flex;
  gap: 10px;
  margin-top: 2px;
}

.atlas-legend { font-size: 11px; }
.atlas-legend--ols { color: var(--dim); }
.atlas-legend--posterior { color: var(--accent); }

.atlas-degradation {
  width: 100%;
  font-size: 13px;
}

.atlas-degradation th,
.atlas-degradation td {
  border: 1px solid var(--line);
  padding: 6px 10px;
  text-align: left;
}

.x1-registry {
  display: grid;
  gap: 10px;
  margin: 0;
}

.x1-registry__row {
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 10px 12px;
}

.x1-registry__metric {
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}

.x1-registry__body {
  margin: 6px 0 0;
  display: flex;
  flex-wrap: wrap;
  gap: 6px 14px;
}

.x1-registry__field {
  font-size: 12px;
  color: var(--dim);
}

.x1-registry__threshold {
  font-size: 12px;
  color: var(--warn);
}
```

- [ ] **Step 6: Flip the x1 manifest entry to live**

In `site/cards.yaml`, replace the `x1` entry (`status: planned`) with:

```yaml
- id: x1
  title: Tier & Power Atlas
  lane: X
  one_liner: How much data until a metric means anything — the tier & power atlas.
  decisions: [select, monitor, engage]
  tiers: [R, E, P]
  status: live
  demo: pages/x1-atlas.html.j2
  data: x1_atlas.json
  spec: x1-tier-power-atlas.md
  golive:
    data_ask: None — simulator study
    sample: n/a
    effort: M (vol. 1)
```

- [ ] **Step 7: Step the planned-tile count down**

In `tests/site/test_build.py`, change the assertion:

```python
    assert index.count("card-tile--planned") == 15
```

- [ ] **Step 8: Run the X1 tests and the full suite**

Run: `python -m pytest tests/site/test_x1.py tests/site/test_build.py -q`
Expected: PASS.

Run: `python -m pytest tests/site -q`
Expected: PASS.

- [ ] **Step 9: Lint**

Run: `ruff check tests/site/test_x1.py`
Expected: clean.

- [ ] **Step 10: Commit**

```bash
git add site/templates/pages/x1-atlas.html.j2 site/assets/x1-atlas.js \
        site/assets/interval.css site/cards.yaml \
        tests/site/test_x1.py tests/site/test_build.py
git commit -m "feat(site): X1 tier & power atlas sampler demo page"
```

---

### Task 3: Builder support for X2 — dark theme + never-goes-live standing note

**Why this task exists (the x2 golive-lint resolution):** X2 must (a) keep the SYNTHETIC badge always on and (b) inline its committed JSON for the dials — both are behaviours `demo.html.j2` gives to **non-doctrine** cards (`{% if not card.doctrine %}`). Marking x2 `doctrine: true` would suppress the badge and skip the data inlining (and `build.py` never loads data for doctrine cards), breaking the page and violating X2 spec §6 rule 3. So x2 stays **non-doctrine**, and we make the smallest builder change instead: an optional `standing_note` string that replaces the go-live box, and an optional `theme` field for the dark default. The lint is extended to accept `golive-replaced` in place of `golive-box`. Documented here and in the final summary.

**Files:**
- Modify: `src/quant_allocator/site/build.py` (`OPTIONAL_KEYS`, `_validate_entry`, `_validate_live_entry`, `_render_demo_pages`, `_lint_outputs`)
- Modify: `site/templates/demo.html.j2` (three-way go-live region)
- Modify: `site/assets/interval.css` (append `.golive-replaced` rule)
- Test: `tests/site/test_lint.py` (add), `tests/site/test_manifest.py` (add)

**Interfaces:**
- Produces (consumed by Task 4): a non-doctrine `live` card may carry `standing_note: <str>` (renders `<aside class="golive-replaced">` instead of `<dl class="golive-box">`, and makes `golive` NOT required) and `theme: dark|light` (default `light`; passed to `base.html.j2` as `default_theme` → `data-default-theme`). The lint accepts either `golive-box` or `golive-replaced` on non-doctrine pages.
- Consumes: nothing new.

- [ ] **Step 1: Write the failing lint + manifest tests**

Add to `tests/site/test_lint.py` (uses the existing `_card`, `_write_page`, `_write_spec`, `VALID_PAGE` helpers):

```python
STANDING_PAGE = (
    '<span class="synthetic-badge"></span>'
    '<aside class="golive-replaced">never goes live</aside>'
)


def test_lint_standing_note_accepts_golive_replaced(tmp_path):
    _write_page(tmp_path, "t1", STANDING_PAGE)
    _write_spec(tmp_path, "t1")
    _lint_outputs([_card(standing_note="never goes live")], tmp_path)


def test_lint_missing_both_golive_and_replaced_raises(tmp_path):
    _write_page(tmp_path, "t1", '<span class="synthetic-badge"></span>')
    _write_spec(tmp_path, "t1")
    with pytest.raises(BuildError, match="golive-box"):
        _lint_outputs([_card()], tmp_path)
```

Add to `tests/site/test_manifest.py` (uses existing `_make_live_files`, `_write_manifest`, `_live_entry`):

```python
def test_live_standing_note_satisfies_golive(tmp_path):
    _make_live_files(tmp_path)
    entry = _live_entry()
    del entry["golive"]
    entry["standing_note"] = "this page never goes live"
    manifest = _write_manifest(tmp_path, [entry])
    cards = load_manifest(manifest)
    assert cards[0]["standing_note"] == "this page never goes live"


def test_live_missing_golive_and_standing_note_raises(tmp_path):
    _make_live_files(tmp_path)
    entry = _live_entry()
    del entry["golive"]
    manifest = _write_manifest(tmp_path, [entry])
    with pytest.raises(BuildError, match="missing required keys"):
        load_manifest(manifest)


def test_invalid_theme_raises(tmp_path):
    _make_live_files(tmp_path)
    entry = _live_entry()
    entry["theme"] = "sepia"
    manifest = _write_manifest(tmp_path, [entry])
    with pytest.raises(BuildError, match="invalid theme"):
        load_manifest(manifest)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/site/test_lint.py::test_lint_standing_note_accepts_golive_replaced tests/site/test_manifest.py::test_live_standing_note_satisfies_golive tests/site/test_manifest.py::test_invalid_theme_raises -q`
Expected: FAIL — `standing_note` and `theme` are unknown keys today (`_validate_entry` raises `unknown keys`), and the standing lint path does not exist.

- [ ] **Step 3: Extend build.py — accept the new optional keys**

In `src/quant_allocator/site/build.py`, change line 19 (`OPTIONAL_KEYS`) to:

```python
OPTIONAL_KEYS = {
    "doctrine",
    "demo",
    "data",
    "spec",
    "golive",
    "usage_note",
    "standing_note",
    "theme",
}
```

Add a constant beside `GOLIVE_KEYS` (after line 23):

```python
VALID_THEMES = {"light", "dark"}
```

- [ ] **Step 4: Extend build.py — validate theme and relax the golive requirement**

In `_validate_entry`, after the status-validity check and before the `if entry["status"] == "live":` block (around line 96), add:

```python
    theme = entry.get("theme")
    if theme is not None and theme not in VALID_THEMES:
        raise BuildError(
            f"{path}: card '{card_id}' has invalid theme '{theme}' "
            f"(must be one of {sorted(VALID_THEMES)})"
        )
```

In `_validate_live_entry`, replace the current required-keys assembly (lines 105-106):

```python
    required_live = {"demo", "spec"}
    required_live |= {"usage_note"} if is_doctrine else {"data", "golive"}
```

with:

```python
    required_live = {"demo", "spec"}
    if is_doctrine:
        required_live |= {"usage_note"}
    else:
        required_live |= {"data"}
        if "standing_note" not in entry:
            required_live |= {"golive"}
```

And guard the golive-shape check (lines 113-118) so it only runs when a `golive` key is present:

```python
    if not is_doctrine and "golive" in entry:
        golive = entry["golive"]
        if not isinstance(golive, dict) or GOLIVE_KEYS - golive.keys():
            raise BuildError(
                f"{path}: live card '{card_id}' golive must define keys {sorted(GOLIVE_KEYS)}"
            )
```

- [ ] **Step 5: Extend build.py — pass the per-card theme and relax the lint**

In `_render_demo_pages`, change the render call (lines 208-215) so `default_theme` comes from the card:

```python
        html = env.get_template(card["demo"]).render(
            page_title=card["title"],
            card=card,
            card_data_json=card_data_json,
            card_data=card_data,
            asset_base="",
            default_theme=card.get("theme", "light"),
        )
```

In `_lint_outputs`, replace the non-doctrine `golive-box` check (lines 237-240) with an either/or check:

```python
            if "golive-box" not in html and "golive-replaced" not in html:
                raise BuildError(
                    f"{page_path}: card '{card['id']}' output missing golive-box "
                    f"or standing-note (golive-replaced)"
                )
```

(The `synthetic-badge` check immediately above it stays unchanged; the error message still contains `golive-box`, so the existing `test_lint_missing_golive_raises` still matches.)

- [ ] **Step 6: Add the three-way go-live region to demo.html.j2**

In `site/templates/demo.html.j2`, replace the doctrine/else block (lines 23-34) with:

```jinja
  {% if card.doctrine %}
  <aside class="usage-note">
    <h2>How to use this</h2>
    <p>{{ card.usage_note }}</p>
  </aside>
  {% elif card.standing_note %}
  <aside class="golive-replaced" role="note">
    <h2>No go-live</h2>
    <p>{{ card.standing_note }}</p>
  </aside>
  {% else %}
  <dl class="golive-box">
    <dt>Data ask</dt><dd>{{ card.golive.data_ask }}</dd>
    <dt>Sample required</dt><dd>{{ card.golive.sample }}</dd>
    <dt>Build effort</dt><dd>{{ card.golive.effort }}</dd>
  </dl>
  {% endif %}
```

- [ ] **Step 7: Append the golive-replaced CSS rule**

Append to `site/assets/interval.css` (after the X1 block):

```css
/* === Standing note (never-goes-live pages, e.g. X2) ============= */
.golive-replaced {
  border-left: 3px solid var(--warn);
  padding: 8px 16px;
  margin: 20px 0;
}

.golive-replaced h2 {
  font-size: 13px;
  margin: 0 0 4px;
}
```

- [ ] **Step 8: Run the new tests and the full suite**

Run: `python -m pytest tests/site/test_lint.py tests/site/test_manifest.py -q`
Expected: PASS (new tests green; all existing lint/manifest tests still green — `test_lint_missing_golive_raises` still matches `golive-box`, `test_valid_live_entry_loads` still passes since `golive` remains required when no `standing_note`).

Run: `python -m pytest tests/site -q`
Expected: PASS (S1/M5/E1/S2/X1 pages unaffected — none carry `standing_note` or `theme`).

- [ ] **Step 9: Lint**

Run: `ruff check src/quant_allocator/site/build.py`
Expected: clean.

- [ ] **Step 10: Commit**

```bash
git add src/quant_allocator/site/build.py site/templates/demo.html.j2 \
        site/assets/interval.css tests/site/test_lint.py tests/site/test_manifest.py
git commit -m "feat(site): builder support for dark theme + never-goes-live standing note"
```

---

### Task 4: X2 · Transparency playground page (dark default)

**Files:**
- Create: `site/templates/pages/x2-playground.html.j2`
- Create: `site/assets/x2-playground.js`
- Modify: `site/assets/interval.css` (append the `=== X2 playground ===` block)
- Modify: `site/cards.yaml` (the `x2` entry — flip live, `theme: dark`, `standing_note`)
- Modify: `tests/site/test_build.py` (`card-tile--planned` count 15 → 14)
- Test: `tests/site/test_x2.py`

**Interfaces:**
- Consumes: Task 3's `standing_note` + `theme` builder support; `card`, `card_data` (parsed `site/data/x2_playground.json`), `card_data_json` (inlined for the JS), `default_theme="dark"`.
- `card_data` shape (verbatim): `card_data.meta.dials` = `{ "ic":[0.0,0.02,0.04,0.07,0.1], "half_life":[3.0,12.0,36.0], "sizing":[0.0,0.8], "T":[24,36,48,60,120], "tier":["R","E","P"] }`. `card_data.cells` is a 450-entry object keyed by `"{ic:g}|{half_life:g}|{sizing:g}|{T}|{tier}"` (e.g. `"0.04|12|0.8|48|R"`). Each cell value is an object whose keys are analytic names: R/E cells have `alpha`, `sharpe`; P cells additionally have `hit_rate`, `sizing_slope`. Each analytic value is the **D-22 positional array** `[point, lo, hi, verdict, gate_state, threshold, units, wilson_hw]`; in the committed grid every `gate_state` is `"closed"` and every `threshold` is `null`. Default cell `"0.04|12|0.8|48|R"`: `alpha = [0.053, -0.02951, 0.1249, "noise", "closed", null, "months", 0.03796]`, `sharpe = [0.78, -0.1922, 1.766, "noise", "closed", null, "months", 0.04069]`.
- Produces: rendered `x2.html` + `assets/x2-playground.js`. Terminal task; nothing depends on it.

**Design notes for the implementer:**
- The template renders the **static scaffolding** (dials, four analytic slots, the standing note via `demo.html.j2`, the false-alarm banner, the Wilson footnote labels, the closed-gate statement) so all copy obligations are present in the server output and test-asserted. The **numbers and verdict/gate states** are painted by `x2-playground.js` from the inlined JSON via verbatim lookup + display-formatting only — no browser math, per X2 spec §6. On load the JS paints the default cell.
- Dial buttons carry `data-dial` + `data-value`; numeric dial values are rendered with `"%g"|format` so the JS can concatenate the raw string tokens into the cell key directly (matching the JSON key format: `0.0→"0"`, `0.02→"0.02"`, `12.0→"12"`, `0.8→"0.8"`, `120→"120"`). No float-to-string conversion in the JS key builder.
- Analytic slot descriptors (label, formatter, unit) live in the JS as a lookup table; slots for `hit_rate`/`sizing_slope` are hidden until a cell that contains them (tier P) is selected.

- [ ] **Step 1: Write the failing tests**

Create `tests/site/test_x2.py`:

```python
from pathlib import Path

from quant_allocator.site.build import build

REPO_ROOT = Path(__file__).resolve().parents[2]


def _build(tmp_path):
    out = tmp_path / "out"
    build(REPO_ROOT / "site", out)
    return (out / "x2.html").read_text(encoding="utf-8"), out


def test_x2_provenance_dark_and_standing_note(tmp_path):
    html, out = _build(tmp_path)
    # SYNTHETIC badge stays on (x2 is non-doctrine).
    assert "synthetic-badge" in html
    assert "SYNTHETIC DATA" in html
    # Dark default theme.
    assert 'data-default-theme="dark"' in html
    # Go-live box is replaced by the standing statement, not present.
    assert "golive-replaced" in html
    assert "golive-box" not in html
    assert "the thesis, not a product" in html
    assert "it never goes live" in html
    # Inlined JSON for the dials + spec link.
    assert 'id="card-data"' in html
    assert "specs/x2.html" in html
    assert (out / "specs" / "x2.html").exists()


def test_x2_dials_snap_values(tmp_path):
    html, _ = _build(tmp_path)
    for dial in ["ic", "half_life", "sizing", "T", "tier"]:
        assert 'data-dial="%s"' % dial in html
    # Snap-to-grid values present as button data-values (%g-formatted).
    assert 'data-value="0.04"' in html   # ic
    assert 'data-value="0.1"' in html    # ic
    assert 'data-value="36"' in html     # half_life or T
    assert 'data-value="0.8"' in html    # sizing
    assert 'data-value="120"' in html    # T
    assert 'data-value="R"' in html      # tier
    assert 'data-value="P"' in html


def test_x2_component_scaffolding_and_copy(tmp_path):
    html, _ = _build(tmp_path)
    # IntervalStat + VerdictChip + PowerGate per analytic.
    assert 'class="interval-stat"' in html
    assert 'class="verdict-chip"' in html
    assert 'class="power-gate"' in html
    # Closed gate with null threshold statement.
    assert "no threshold reached in the measured range" in html
    # Wilson half-width footnote shown.
    assert "Wilson" in html
    assert "half-width" in html
    # IC=0 column labeled false-alarm rate.
    assert "false-alarm rate" in html
    # The four analytic slots exist by name.
    for a in ["alpha", "sharpe", "hit_rate", "sizing_slope"]:
        assert 'data-analytic="%s"' % a in html


def test_x2_script_loaded(tmp_path):
    html, out = _build(tmp_path)
    assert "assets/x2-playground.js" in html
    assert (out / "assets" / "x2-playground.js").exists()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/site/test_x2.py -q`
Expected: FAIL — `x2.html` not built (`x2` still `planned`).

- [ ] **Step 3: Create the X2 page template**

Create `site/templates/pages/x2-playground.html.j2`. The `{% macro dial %}` renders a segmented control; numeric values use `"%g"|format`; the default active value is passed in. The four analytic slots carry stable class hooks and the pinned copy strings:

```jinja
{% extends "demo.html.j2" %}

{% macro dial(name, label, values, active, numeric=True) %}
<div class="x2-dial" data-dial="{{ name }}">
  <span class="x2-dial__label">{{ label }}</span>
  <div class="x2-dial__options">
    {% for v in values %}
    {% set token = "%g"|format(v) if numeric else v %}
    <button type="button" class="x2-dial__btn{% if token == active %} x2-dial__btn--active{% endif %}"
            data-value="{{ token }}"
            aria-pressed="{{ 'true' if token == active else 'false' }}">{{ token }}</button>
    {% endfor %}
  </div>
</div>
{% endmacro %}

{% macro analytic_slot(name, label) %}
<article class="x2-analytic" data-analytic="{{ name }}">
  <div class="interval-stat" data-point="" data-lo="" data-hi="" data-verdict="noise">
    <span class="interval-stat__label">{{ label }}</span>
    <span class="interval-stat__value">&mdash;</span>
    <div class="interval-stat__rail">
      <div class="interval-stat__band"></div>
      <div class="interval-stat__point"></div>
    </div>
    <span class="interval-stat__range">95% band</span>
  </div>
  <div class="x2-analytic__meta">
    <span class="verdict-chip" data-verdict="noise">noise</span>
    <span class="x2-wilson">Wilson 95% half-width &plusmn;<span class="x2-wilson__value">&mdash;</span> &mdash; the band is itself an estimate</span>
  </div>
  <div class="power-gate">
    <span class="power-gate__title">power gate</span>
    <p class="power-gate__reason">no threshold reached in the measured range</p>
  </div>
</article>
{% endmacro %}

{% block demo_content %}
<section class="x2-intro">
  <p class="x2-headline">
    Drag the dials. Every claim is a precomputed cell of the X1 atlas &mdash; the page
    computes nothing, it snaps to measured rungs and never interpolates. Watch an interval
    widen, a verdict flip, a gate stay shut.
  </p>
</section>

<section class="x2-controls" data-dials
         data-default-ic="0.04" data-default-half_life="12"
         data-default-sizing="0.8" data-default-T="48" data-default-tier="R">
  {{ dial("ic", "Information coefficient", card_data.meta.dials.ic, "0.04") }}
  {{ dial("half_life", "Alpha half-life (months)", card_data.meta.dials.half_life, "12") }}
  {{ dial("sizing", "Sizing discipline", card_data.meta.dials.sizing, "0.8") }}
  {{ dial("T", "Track length T (months)", card_data.meta.dials.T, "48") }}
  {{ dial("tier", "Transparency tier", card_data.meta.dials.tier, "R", numeric=False) }}
</section>

<div class="x2-falsealarm" data-falsealarm hidden>
  IC = 0: these figures are the <strong>false-alarm rate</strong> &mdash; detection where
  there is no skill, not power.
</div>

<section class="x2-analytics" data-analytics>
  {{ analytic_slot("alpha", "Annualized alpha") }}
  {{ analytic_slot("sharpe", "Sharpe ratio") }}
  {{ analytic_slot("hit_rate", "Hit rate (active batting average)") }}
  {{ analytic_slot("sizing_slope", "Sizing-curve slope (Fama–MacBeth mean b_t)") }}
</section>
{% endblock %}

{% block methodology %}
<p>The page is a communication device, not an analytic: it renders a precomputed subset of
the X1 atlas grid (450 cells, &ge;500 simulated managers each), shipped as committed JSON.
Dials snap to computed cells &mdash; interpolating between them would invent precision the
Monte-Carlo grid does not have.</p>
<p>The tier selector is the star control: the same ground truth at three honesty levels. R
estimates betas from returns; E pins them to the true exposures, narrowing the alpha band;
P adds trade-level analytics behind PowerGates. Every band carries its own Wilson 95%
half-width because the band is itself an estimate.</p>
{% endblock %}

{% block body_scripts %}
<script src="{{ asset_base | default('') }}assets/x2-playground.js"></script>
{% endblock %}
```

- [ ] **Step 4: Create the X2 JS**

Create `site/assets/x2-playground.js`. Reads the inlined JSON once; holds dial state initialised from `data-default-*`; builds the cell key from the raw string tokens; repaints each analytic slot from the D-22 positional arrays; toggles the false-alarm banner when `ic === "0"`:

```javascript
(function () {
  "use strict";

  var DIALS = ["ic", "half_life", "sizing", "T", "tier"];

  // D-22 positional indices.
  var POINT = 0, LO = 1, HI = 2, VERDICT = 3, GATE = 4, THRESHOLD = 5, UNITS = 6, WILSON = 7;

  // Per-analytic display formatters. No math beyond unit scaling for display.
  function pct1(x) {
    var v = (x * 100).toFixed(1);
    return (x >= 0 ? "+" : "") + v + "%";
  }
  function ratio2(x) { return x.toFixed(2); }
  function slope4(x) { return x.toFixed(4); }

  var FORMAT = {
    alpha: { fmt: pct1, band: "95% band " },
    sharpe: { fmt: ratio2, band: "95% band " },
    hit_rate: { fmt: function (x) { return (x * 100).toFixed(1) + "%"; }, band: "95% band " },
    sizing_slope: { fmt: slope4, band: "95% band " }
  };

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

  function readState(controls) {
    var state = {};
    DIALS.forEach(function (d) {
      state[d] = controls.getAttribute("data-default-" + d);
    });
    return state;
  }

  function cellKey(state) {
    return DIALS.map(function (d) { return state[d]; }).join("|");
  }

  function gateReason(arr) {
    if (arr[GATE] === "open") {
      return "gate open — cleared " + arr[THRESHOLD] + " " + arr[UNITS];
    }
    if (arr[THRESHOLD] === null) {
      return "no threshold reached in the measured range";
    }
    return "gate closed — opens at " + arr[THRESHOLD] + " " + arr[UNITS];
  }

  function paintSlot(slot, arr) {
    var name = slot.getAttribute("data-analytic");
    var f = FORMAT[name];
    var stat = slot.querySelector(".interval-stat");
    var value = slot.querySelector(".interval-stat__value");
    var range = slot.querySelector(".interval-stat__range");
    var band = slot.querySelector(".interval-stat__band");
    var mark = slot.querySelector(".interval-stat__point");
    var chip = slot.querySelector(".verdict-chip");
    var wilson = slot.querySelector(".x2-wilson__value");
    var reason = slot.querySelector(".power-gate__reason");

    value.textContent = f.fmt(arr[POINT]);
    range.textContent = f.band + f.fmt(arr[LO]) + " … " + f.fmt(arr[HI]);
    stat.setAttribute("data-verdict", arr[VERDICT]);
    chip.setAttribute("data-verdict", arr[VERDICT]);
    chip.textContent = arr[VERDICT];
    wilson.textContent = arr[WILSON].toFixed(3);
    reason.textContent = gateReason(arr);

    // Position: band spans lo..hi, point placed within it. Pixel layout only.
    var span = arr[HI] - arr[LO];
    band.style.left = "0%";
    band.style.width = "100%";
    mark.style.left = (span > 0 ? ((arr[POINT] - arr[LO]) / span) * 100 : 50) + "%";
  }

  function render(data, state) {
    var cell = data.cells[cellKey(state)];
    var slots = Array.prototype.slice.call(
      document.querySelectorAll(".x2-analytic")
    );
    slots.forEach(function (slot) {
      var name = slot.getAttribute("data-analytic");
      var arr = cell ? cell[name] : null;
      if (arr) {
        slot.hidden = false;
        paintSlot(slot, arr);
      } else {
        slot.hidden = true;
      }
    });
    var banner = document.querySelector("[data-falsealarm]");
    if (banner) {
      banner.hidden = state.ic !== "0";
    }
  }

  function bindDials(controls, onChange) {
    controls.addEventListener("click", function (evt) {
      var btn = evt.target.closest(".x2-dial__btn");
      if (!btn) {
        return;
      }
      var group = btn.closest(".x2-dial");
      var dial = group.getAttribute("data-dial");
      Array.prototype.slice.call(group.querySelectorAll(".x2-dial__btn")).forEach(
        function (b) {
          var on = b === btn;
          b.classList.toggle("x2-dial__btn--active", on);
          b.setAttribute("aria-pressed", on ? "true" : "false");
        }
      );
      onChange(dial, btn.getAttribute("data-value"));
    });
  }

  function init() {
    var data = readCardData();
    var controls = document.querySelector("[data-dials]");
    if (!data || !controls) {
      return;
    }
    var state = readState(controls);
    render(data, state);
    bindDials(controls, function (dial, value) {
      state[dial] = value;
      render(data, state);
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
```

- [ ] **Step 5: Append the X2 CSS block**

Append to `site/assets/interval.css` (after the standing-note rule from Task 3):

```css
/* === X2 playground ============================================== */
.x2-intro {
  margin: 8px 0 20px;
}

.x2-headline {
  font-size: 15px;
  line-height: 1.5;
}

.x2-controls {
  display: grid;
  gap: 12px;
  margin: 0 0 20px;
}

.x2-dial {
  display: grid;
  gap: 6px;
}

.x2-dial__label {
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: 0.10em;
  color: var(--dim);
}

.x2-dial__options {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.x2-dial__btn {
  border: 1px solid var(--line);
  border-radius: 6px;
  background: transparent;
  color: var(--ink);
  padding: 4px 10px;
  cursor: pointer;
  font: inherit;
  font-variant-numeric: tabular-nums;
}

.x2-dial__btn--active {
  border-color: var(--accent);
  color: var(--accent);
}

.x2-falsealarm {
  border: 1px dashed var(--warn);
  border-radius: 8px;
  padding: 8px 14px;
  margin: 0 0 16px;
  font-size: 13px;
  color: var(--warn);
}

.x2-analytics {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}

@media (max-width: 640px) {
  .x2-analytics {
    grid-template-columns: 1fr;
  }
}

.x2-analytic {
  display: grid;
  gap: 10px;
}

.x2-analytic[hidden] {
  display: none;
}

.x2-analytic__meta {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 10px;
}

.x2-wilson {
  font-size: 11px;
  color: var(--dim);
  font-variant-numeric: tabular-nums;
}
```

- [ ] **Step 6: Flip the x2 manifest entry to live (dark theme + standing note)**

In `site/cards.yaml`, replace the `x2` entry (`status: planned`) with:

```yaml
- id: x2
  title: Transparency playground
  lane: X
  one_liner: Drag the dials and watch honest claims dissolve into grey.
  decisions: [engage]
  tiers: [R, E, P]
  status: live
  theme: dark
  demo: pages/x2-playground.html.j2
  data: x2_playground.json
  spec: x2-transparency-playground.md
  standing_note: >-
    This page is the thesis, not a product — it never goes live against a real
    manager. It renders a precomputed subset of the X1 atlas and stays synthetic
    forever; the only release event is the v1 → v2 atlas regeneration.
```

- [ ] **Step 7: Step the planned-tile count down**

In `tests/site/test_build.py`, change the assertion:

```python
    assert index.count("card-tile--planned") == 14
```

- [ ] **Step 8: Run the X2 tests and the full suite**

Run: `python -m pytest tests/site/test_x2.py tests/site/test_build.py -q`
Expected: PASS. Note the `standing_note` YAML folds newlines to spaces, so `test_x2_provenance_dark_and_standing_note` matches `the thesis, not a product` and `it never goes live` as contiguous substrings.

Run: `python -m pytest tests/site -q`
Expected: PASS (full suite green; the builder never imports numpy/pandas — `test_publication_check` / isolation tests stay green because Task 4 adds no imports).

- [ ] **Step 9: Lint**

Run: `ruff check tests/site/test_x2.py`
Expected: clean.

- [ ] **Step 10: Commit**

```bash
git add site/templates/pages/x2-playground.html.j2 site/assets/x2-playground.js \
        site/assets/interval.css site/cards.yaml \
        tests/site/test_x2.py tests/site/test_build.py
git commit -m "feat(site): X2 transparency playground demo page (dark, never-goes-live)"
```

---

## Self-Review

**1. Spec coverage** — walked each source against a task:

- Gallery design §5 X2 (dials, snap-to-grid, per-cell payload, dark default, gates naming threshold): Task 4 template + JS + Task 3 theme. ✅
- Gallery design §5 S2 (reported vs de-smoothed Sharpe, interval alphas, alt-beta chip, MPPM, drawdown band, monthly strip, synthetic factors): Task 1. ✅
- Gallery design §5 X1 (three exhibits: power curves, degradation table, registry snippet): Task 2. ✅
- S2 spec §3 rendering rule (every statistic an IntervalStat, alt-beta VerdictChip), §3.6 pointwise drawdown envelope, §7 go-live box: Task 1 (MPPM rendered as a gap flag, not a bare headline stat, because the certified JSON carries no MPPM CI — documented in the template note). ✅
- X1 spec §2 registry schema, §3.2 metric set, §8 realized-IR/780 content: Task 2 renders the sampler JSON verbatim; null thresholds → the no-tenure statement. ✅
- X2 spec §6 non-negotiables: (1) dials snap — JS uses string-token key lookup, no interpolation ✅; (2) every number traces to a JSON cell — JS verbatim lookup, no client math ✅; (3) SYNTHETIC badge always on — x2 stays non-doctrine ✅; (4) go-live box replaced by the standing statement — `standing_note` + `golive-replaced` ✅; (5) MC uncertainty shown — Wilson footnote ✅.
- Brief copy obligations: every pinned string has a matching test assertion (S2: `95% interval`, `90% interval`, `pointwise`, `(synthetic)`+`2.0%`, de-smoothing `0.71`/`0.60`/`0.82`, alt-beta chip; X1: headline, `realized IR 0.65`/`1.57`, posterior label substrings, degradation `25.2%`/`31.8%`/`13.2%`/`23.4%`, `no tenure in the measured range suffices`; X2: dark theme attr, five dials, `no threshold reached in the measured range`, `Wilson`/`half-width`, `false-alarm rate`, standing statement). ✅
- Planned-tile stepping 17→16→15→14: Tasks 1, 2, 4 each edit the single `test_build.py` assertion. ✅

**2. Placeholder scan** — no `TBD`/`TODO`/"implement later"; every code step carries complete file content or an exact edit with surrounding context and line anchors. ✅

**3. Type/name consistency** — `card_data` field paths match the committed JSON exactly (verified by inspection: `statistics.sharpe_reported.point`, `drawdown_band.p99`, `meta.dials.ic`, cell key format `%g`). JS D-22 indices (`POINT=0…WILSON=7`) match the brief's positional order. CSS class hooks used in templates (`s2-drawdown`, `x1-powercurve`, `x2-analytic`, `golive-replaced`) are the same strings the JS/lint/tests query. `standing_note`/`theme` key names are identical across `cards.yaml`, `build.py`, `demo.html.j2`, and tests. `VALID_THEMES`/`error message "invalid theme"` matches the test's `match="invalid theme"`. ✅

One resolved consistency risk: the lint error message retains the literal `golive-box` so the pre-existing `test_lint_missing_golive_raises` (which asserts `match="golive-box"`) still passes after Task 3's either/or relaxation.
