# Wave-1 Plan A — Gallery Shell Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the static-site shell for the quant-allocator idea gallery — a Jinja2 + Markdown/KaTeX Python builder that renders a 20-card index, the Interval design system, one live doctrine demo page (E1), spec-page rendering, a builder CLI, and the CI/publication furniture — without any demo-data generators or the five data pages (those are Plan B).

**Architecture:** A single dependency-light builder module `quant_allocator.site.build` validates a YAML manifest (`site/cards.yaml`), renders an index and per-card demo/spec pages through Jinja2 templates, copies self-hosted assets, and runs an honest-mockup lint that fails loudly on any provenance-badge or referenced-file violation. Numbers are never computed here — the builder only renders committed inputs, enforced by an import-isolation test. Pages deploy via a GitHub Actions workflow that installs only template dependencies.

**Tech Stack:** Python ≥3.11, Jinja2 (templates), python-markdown (spec rendering), PyYAML (manifest), vendored KaTeX 0.16.21 (client-side math), vanilla JS (theme toggle), hand-authored CSS (Interval design tokens). Tests: pytest with `pythonpath=["src"]`. Lint: ruff line-length 100. Package/venv manager: `uv`.

## Global Constraints
- python >=3.11; ruff line-length 100.
- New deps limited to `jinja2`, `markdown`, `pyyaml` (runtime); `quant_allocator.site` must never import numpy/pandas/simulator modules (a test enforces this).
- Builder failures are loud `BuildError`s naming the offending file and the violated rule — nothing is silently skipped.
- Every demo page output must contain the synthetic-badge (unless the card sets `doctrine: true`) and the golive-box (or, for doctrine cards, the usage-note variant) — the build fails otherwise.
- All site assets are self-hosted (no CDN references in shipped HTML); KaTeX is vendored and committed.
- The repo is treated as public — no employer-internal facts or manager names anywhere in code, comments, commits, or committed data.
- The existing test suite stays green and ruff stays clean after every task.
- All commands run through `uv` (the project venv is `.venv`, Python 3.11). Use `uv run pytest ...`, `uv run python ...`, `uv run ruff ...`. Commit after each task with conventional prefixes (`feat:`/`test:`/`docs:`/`chore:`); **no commit trailers**.

**Public builder interface** (module `quant_allocator.site.build`), frozen across tasks:
- `class BuildError(Exception)` — message always names the offending file and the violated rule.
- `load_manifest(path: Path) -> list[dict]` — strict validation (schema below); referenced files must exist.
- `build(site_dir: Path, out_dir: Path) -> None` — validate manifest → render index → render live demo pages → render specs → copy assets → lint outputs.
- CLI: `python -m quant_allocator.site build [--site-dir site/] [--out site/_build/]`.

**Manifest schema** (`site/cards.yaml`): required keys per entry `{id, title, lane, one_liner, decisions, tiers, status}`; `lane ∈ {S,M,P,E,X}`; `status ∈ {live, planned}`; unknown keys rejected. `live` entries additionally require `demo`, `spec`, and (unless `doctrine: true`) `data` and `golive`; doctrine `live` entries require `usage_note` instead of `data`/`golive`. `golive` is `{data_ask, sample, effort}`. Referenced files must exist on disk (demo under `site/templates/`, data under `site/data/`, spec under `docs/ideas/specs/`).

**Reference resolution (pinned):** `load_manifest(path)` treats `site_dir = path.parent`. It resolves `demo` under `site_dir/templates/`, `data` under `site_dir/data/`, and `spec` under `site_dir.parent/docs/ideas/specs/` (specs live outside `site/`). The fixed single-argument signature forces this repo-relative resolution — it is intentional, not incidental.

**Theme mechanics:** tokens on `:root` (light values); `:root[data-theme="dark"]` overrides. Each page's `<html>` carries `data-default-theme` (always `"light"` in Plan A). An inline head script (before CSS) reads `localStorage["qa-theme"]`; if absent it uses `data-default-theme`; it sets `data-theme` immediately (no flash). The header toggle cycles light/dark and persists to `qa-theme`.

---

## Task 1: Scaffolding, dependencies, and strict manifest validation

**Files:**
- Modify: `pyproject.toml` (via `uv add`)
- Modify: `.gitignore`
- Create: `src/quant_allocator/site/__init__.py`
- Create: `src/quant_allocator/site/build.py`
- Create: `site/` directory skeleton (`site/templates/`, `site/assets/`, `site/data/`)
- Create: `tests/site/__init__.py`
- Test: `tests/site/test_manifest.py`

**Interfaces:**
- Consumes: `site/cards.yaml` path (and, for live entries, files under `site/templates/`, `site/data/`, `docs/ideas/specs/`).
- Produces: `BuildError`, `load_manifest(path) -> list[dict]`.

- [ ] **Step 1: Add runtime dependencies.**
  Run:
  ```bash
  uv add jinja2 markdown pyyaml
  ```
  Expected output ends with a resolution summary and `+ jinja2`, `+ markdown`, `+ pyyaml` (plus transitive deps like `markupsafe`) added. Confirm `pyproject.toml` `[project].dependencies` now lists `jinja2`, `markdown`, and `pyyaml` alongside `numpy` and `pandas`.

- [ ] **Step 2: Create the directory skeleton and package files.**
  Run:
  ```bash
  mkdir -p site/templates/pages site/assets/katex/contrib site/assets/katex/fonts site/data tests/site
  touch src/quant_allocator/site/__init__.py tests/site/__init__.py
  ```
  Then create `src/quant_allocator/site/__init__.py` with exactly:
  ```python
  """Static-site builder for the quant-allocator idea gallery (render-only; no numerics)."""
  ```

- [ ] **Step 3: Add build output to `.gitignore`.**
  Append these two lines to `.gitignore`:
  ```
  site/_build/
  tools/.publication_terms
  ```
  (The second line is used by Task 9; adding it now keeps `.gitignore` edits in one place.)

- [ ] **Step 4: Write the failing manifest test.**
  Create `tests/site/test_manifest.py`:
  ```python
  import yaml

  import pytest

  from quant_allocator.site.build import BuildError, load_manifest


  def _write_manifest(tmp_path, entries):
      site_dir = tmp_path / "site"
      site_dir.mkdir(parents=True, exist_ok=True)
      manifest = site_dir / "cards.yaml"
      manifest.write_text(yaml.safe_dump(entries), encoding="utf-8")
      return manifest


  def _make_live_files(tmp_path):
      site_dir = tmp_path / "site"
      (site_dir / "templates" / "pages").mkdir(parents=True, exist_ok=True)
      (site_dir / "templates" / "pages" / "t1.html.j2").write_text("x", encoding="utf-8")
      (site_dir / "data").mkdir(parents=True, exist_ok=True)
      (site_dir / "data" / "t1.json").write_text("{}", encoding="utf-8")
      specs = tmp_path / "docs" / "ideas" / "specs"
      specs.mkdir(parents=True, exist_ok=True)
      (specs / "t1.md").write_text("# t1", encoding="utf-8")


  def _planned_entry():
      return {
          "id": "s1",
          "title": "Skill ledger",
          "lane": "S",
          "one_liner": "Posterior alpha across the roster.",
          "decisions": ["select", "size"],
          "tiers": ["R", "E", "P"],
          "status": "planned",
      }


  def _live_entry():
      return {
          "id": "t1",
          "title": "Test card",
          "lane": "S",
          "one_liner": "A live card.",
          "decisions": ["select"],
          "tiers": ["R"],
          "status": "live",
          "demo": "pages/t1.html.j2",
          "data": "t1.json",
          "spec": "t1.md",
          "golive": {"data_ask": "R", "sample": "36m", "effort": "S"},
      }


  def test_valid_planned_entry_loads(tmp_path):
      manifest = _write_manifest(tmp_path, [_planned_entry()])
      cards = load_manifest(manifest)
      assert cards[0]["id"] == "s1"


  def test_valid_live_entry_loads(tmp_path):
      _make_live_files(tmp_path)
      manifest = _write_manifest(tmp_path, [_live_entry()])
      cards = load_manifest(manifest)
      assert cards[0]["status"] == "live"


  def test_missing_required_key_raises(tmp_path):
      entry = _planned_entry()
      del entry["one_liner"]
      manifest = _write_manifest(tmp_path, [entry])
      with pytest.raises(BuildError, match="missing required keys"):
          load_manifest(manifest)


  def test_invalid_lane_raises(tmp_path):
      entry = _planned_entry()
      entry["lane"] = "Z"
      manifest = _write_manifest(tmp_path, [entry])
      with pytest.raises(BuildError, match="invalid lane"):
          load_manifest(manifest)


  def test_invalid_status_raises(tmp_path):
      entry = _planned_entry()
      entry["status"] = "shipped"
      manifest = _write_manifest(tmp_path, [entry])
      with pytest.raises(BuildError, match="invalid status"):
          load_manifest(manifest)


  def test_unknown_key_raises(tmp_path):
      entry = _planned_entry()
      entry["surprise"] = True
      manifest = _write_manifest(tmp_path, [entry])
      with pytest.raises(BuildError, match="unknown keys"):
          load_manifest(manifest)


  def test_live_missing_required_key_raises(tmp_path):
      _make_live_files(tmp_path)
      entry = _live_entry()
      del entry["spec"]
      manifest = _write_manifest(tmp_path, [entry])
      with pytest.raises(BuildError, match="missing required keys"):
          load_manifest(manifest)


  def test_live_missing_data_file_raises(tmp_path):
      _make_live_files(tmp_path)
      (tmp_path / "site" / "data" / "t1.json").unlink()
      manifest = _write_manifest(tmp_path, [_live_entry()])
      with pytest.raises(BuildError, match="missing data file"):
          load_manifest(manifest)


  def test_live_dangling_spec_raises(tmp_path):
      _make_live_files(tmp_path)
      (tmp_path / "docs" / "ideas" / "specs" / "t1.md").unlink()
      manifest = _write_manifest(tmp_path, [_live_entry()])
      with pytest.raises(BuildError, match="missing spec file"):
          load_manifest(manifest)
  ```

- [ ] **Step 5: Run the test and watch it fail.**
  ```bash
  uv run pytest tests/site/test_manifest.py -q
  ```
  Expected: collection error / failure — `ModuleNotFoundError: No module named 'quant_allocator.site.build'` (the module does not exist yet).

- [ ] **Step 6: Implement `build.py` with `BuildError` and `load_manifest`.**
  Create `src/quant_allocator/site/build.py`:
  ```python
  """Render-only static-site builder for the idea gallery.

  This module validates the card manifest and (in later tasks) renders the site.
  It must never import numpy, pandas, or simulator modules: the builder renders
  committed inputs, it does not compute statistics.
  """

  from __future__ import annotations

  from pathlib import Path

  import yaml

  REQUIRED_KEYS = {"id", "title", "lane", "one_liner", "decisions", "tiers", "status"}
  OPTIONAL_KEYS = {"doctrine", "demo", "data", "spec", "golive", "usage_note"}
  ALLOWED_KEYS = REQUIRED_KEYS | OPTIONAL_KEYS
  VALID_LANES = {"S", "M", "P", "E", "X"}
  VALID_STATUSES = {"live", "planned"}
  GOLIVE_KEYS = {"data_ask", "sample", "effort"}


  class BuildError(Exception):
      """Raised when the manifest or a rendered output violates a build rule.

      The message always names the offending file and the rule that failed.
      """


  def load_manifest(path: Path) -> list[dict]:
      """Load and strictly validate the card manifest at ``path``.

      ``site_dir`` is ``path.parent``. Referenced files are resolved relative to
      the repo layout: demo under ``site_dir/templates``, data under
      ``site_dir/data``, spec under ``site_dir.parent/docs/ideas/specs``.
      """
      site_dir = path.parent
      raw = yaml.safe_load(path.read_text(encoding="utf-8"))
      if not isinstance(raw, list):
          raise BuildError(f"{path}: manifest must be a YAML list of card entries")

      cards: list[dict] = []
      for index, entry in enumerate(raw):
          _validate_entry(entry, index, path, site_dir)
          cards.append(entry)
      return cards


  def _validate_entry(entry: object, index: int, path: Path, site_dir: Path) -> None:
      if not isinstance(entry, dict):
          raise BuildError(f"{path}: entry #{index} is not a mapping")

      card_id = entry.get("id", f"#{index}")

      missing = REQUIRED_KEYS - entry.keys()
      if missing:
          raise BuildError(
              f"{path}: card '{card_id}' is missing required keys: {sorted(missing)}"
          )

      unknown = entry.keys() - ALLOWED_KEYS
      if unknown:
          raise BuildError(f"{path}: card '{card_id}' has unknown keys: {sorted(unknown)}")

      if entry["lane"] not in VALID_LANES:
          raise BuildError(
              f"{path}: card '{card_id}' has invalid lane '{entry['lane']}' "
              f"(must be one of {sorted(VALID_LANES)})"
          )

      if entry["status"] not in VALID_STATUSES:
          raise BuildError(
              f"{path}: card '{card_id}' has invalid status '{entry['status']}' "
              f"(must be one of {sorted(VALID_STATUSES)})"
          )

      if entry["status"] == "live":
          _validate_live_entry(entry, card_id, path, site_dir)


  def _validate_live_entry(entry: dict, card_id: str, path: Path, site_dir: Path) -> None:
      is_doctrine = entry.get("doctrine", False)

      required_live = {"demo", "spec"}
      required_live |= {"usage_note"} if is_doctrine else {"data", "golive"}
      missing = required_live - entry.keys()
      if missing:
          raise BuildError(
              f"{path}: live card '{card_id}' is missing required keys: {sorted(missing)}"
          )

      if not is_doctrine:
          golive = entry["golive"]
          if not isinstance(golive, dict) or GOLIVE_KEYS - golive.keys():
              raise BuildError(
                  f"{path}: live card '{card_id}' golive must define keys {sorted(GOLIVE_KEYS)}"
              )

      referenced = {
          "demo": site_dir / "templates" / entry["demo"],
          "spec": site_dir.parent / "docs" / "ideas" / "specs" / entry["spec"],
      }
      if not is_doctrine:
          referenced["data"] = site_dir / "data" / entry["data"]

      for kind, file_path in referenced.items():
          if not file_path.exists():
              raise BuildError(
                  f"{path}: live card '{card_id}' references missing {kind} file: {file_path}"
              )
  ```

- [ ] **Step 7: Run the test and watch it pass.**
  ```bash
  uv run pytest tests/site/test_manifest.py -q
  ```
  Expected: `9 passed`.

- [ ] **Step 8: Confirm ruff is clean and commit.**
  ```bash
  uv run ruff check src/quant_allocator/site tests/site
  git add -A && git commit -m "feat: manifest validation and site package scaffolding"
  ```
  Expected: ruff prints `All checks passed!`; commit succeeds.

---

## Task 2: Design tokens, base + index templates, theme toggle, manifest, and `build()` v1

**Files:**
- Create: `site/assets/design-tokens.css`
- Create: `site/assets/interval.js`
- Create: `site/templates/base.html.j2`
- Create: `site/templates/index.html.j2`
- Create: `site/cards.yaml` (all 20 cards, `status: planned`)
- Modify: `src/quant_allocator/site/build.py` (add `build`, `_render_index`, `_copy_assets`)
- Test: `tests/site/test_build.py`

**Interfaces:**
- Consumes: `site/cards.yaml`, `site/templates/*.j2`, `site/assets/*`.
- Produces: `build(site_dir, out_dir)` rendering `out_dir/index.html` and copying `out_dir/assets/`.

- [ ] **Step 1: Create the design tokens stylesheet.**
  Create `site/assets/design-tokens.css` (values copied verbatim from the demo-layer spec §3; the three dark tokens the spec omits are pinned as `--track: #1C222B`, `--band: rgba(79,179,165,0.18)`, `--warn: #C9893B`):
  ```css
  :root {
    --paper: #FBFBF9;
    --ink: #1F2428;
    --dim: #5C6470;
    --line: #E4E3DD;
    --track: #EEEDE7;
    --accent: #10685E;
    --band: rgba(16, 104, 94, 0.16);
    --pos: #3D7A4E;
    --neg: #B04A3E;
    --warn: #99621D;
  }

  :root[data-theme="dark"] {
    --paper: #13161B;
    --ink: #D5DCE4;
    --dim: #828D9B;
    --line: #272E38;
    --track: #1C222B;
    --accent: #4FB3A5;
    --band: rgba(79, 179, 165, 0.18);
    --pos: #55B97C;
    --neg: #E05252;
    --warn: #C9893B;
    --data: #E8A33D;
  }

  * {
    box-sizing: border-box;
  }

  html {
    color-scheme: light dark;
  }

  body {
    margin: 0;
    background: var(--paper);
    color: var(--ink);
    font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
    font-size: 16px;
    line-height: 1.55;
    font-variant-numeric: tabular-nums;
  }

  h1,
  h2,
  h3 {
    letter-spacing: -0.015em;
    text-wrap: balance;
    line-height: 1.2;
  }

  a {
    color: var(--accent);
  }
  ```

- [ ] **Step 2: Create the theme-toggle script.**
  Create `site/assets/interval.js`:
  ```javascript
  (function () {
    "use strict";
    var STORAGE_KEY = "qa-theme";

    function currentTheme() {
      return document.documentElement.getAttribute("data-theme") || "light";
    }

    function applyTheme(theme) {
      document.documentElement.setAttribute("data-theme", theme);
      try {
        localStorage.setItem(STORAGE_KEY, theme);
      } catch (e) {
        /* localStorage unavailable (private mode / file://) — theme still applies */
      }
    }

    function init() {
      var toggle = document.querySelector("[data-theme-toggle]");
      if (!toggle) {
        return;
      }
      toggle.addEventListener("click", function () {
        applyTheme(currentTheme() === "dark" ? "light" : "dark");
      });
    }

    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", init);
    } else {
      init();
    }
  })();
  ```

- [ ] **Step 3: Create the base template.**
  Create `site/templates/base.html.j2`:
  ```jinja
  <!doctype html>
  <html lang="en" data-default-theme="{{ default_theme | default('light') }}">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{{ page_title | default('Idea Gallery') }} · {{ site_title }}</title>
    <script>
      (function () {
        var stored = null;
        try { stored = localStorage.getItem("qa-theme"); } catch (e) {}
        var root = document.documentElement;
        root.setAttribute("data-theme", stored || root.getAttribute("data-default-theme") || "light");
      })();
    </script>
    <link rel="stylesheet" href="{{ asset_base | default('') }}assets/design-tokens.css">
    <link rel="stylesheet" href="{{ asset_base | default('') }}assets/interval.css">
    {% block head_extra %}{% endblock %}
  </head>
  <body>
    <a class="skip-link" href="#main">Skip to content</a>
    <header class="site-header">
      <div class="site-header__title">{{ site_title }}</div>
      <nav class="site-nav" aria-label="Primary">
        <a href="{{ asset_base | default('') }}index.html">Gallery</a>
      </nav>
      <button type="button" class="theme-toggle" data-theme-toggle
              aria-label="Toggle light or dark theme">Theme</button>
    </header>
    <div class="site-banner" role="note">All data on this site is synthetic or public.</div>
    <main id="main" class="site-main">
      {% block content %}{% endblock %}
    </main>
    <footer class="site-footer">
      <span>MIT License</span>
      <a href="{{ repo_url }}">Source repository</a>
    </footer>
    <script src="{{ asset_base | default('') }}assets/interval.js"></script>
    {% block body_scripts %}{% endblock %}
  </body>
  </html>
  ```

- [ ] **Step 4: Create the index template.**
  Create `site/templates/index.html.j2`:
  ```jinja
  {% extends "base.html.j2" %}

  {% macro tile_body(card) %}
  <h3 class="card-tile__title">{{ card.title }}</h3>
  <p class="card-tile__oneliner">{{ card.one_liner }}</p>
  <div class="card-tile__meta">
    {% for decision in card.decisions %}<span class="decision-chip">{{ decision }}</span>{% endfor %}
  </div>
  <div class="card-tile__tiers">
    {% for tier in card.tiers %}<span class="tier-badge" data-tier="{{ tier }}">{{ tier }}</span>{% endfor %}
  </div>
  {% endmacro %}

  {% block content %}
  <section class="gallery-intro">
    <h1>Idea Gallery</h1>
    <p class="gallery-thesis">Every analytic here is an exercise in inference under partial transparency.</p>
  </section>
  {% for lane in lanes %}
  <section class="lane" aria-labelledby="lane-{{ lane.key }}">
    <h2 class="lane__heading" id="lane-{{ lane.key }}">{{ lane.heading }}</h2>
    <div class="card-grid">
      {% for card in lane.cards %}
      {% if card.status == "live" %}
      <a class="card-tile" href="{{ asset_base | default('') }}{{ card.id }}.html">
        {{ tile_body(card) }}
      </a>
      {% else %}
      <div class="card-tile card-tile--planned">
        <span class="card-tile__wave">wave 2</span>
        {{ tile_body(card) }}
      </div>
      {% endif %}
      {% endfor %}
    </div>
  </section>
  {% endfor %}
  {% endblock %}
  ```

- [ ] **Step 5: Create the manifest with all 20 cards (all planned).**
  Create `site/cards.yaml`:
  ```yaml
  - id: s1
    title: Hierarchical Bayesian alpha engine
    lane: S
    one_liner: Posterior alpha across the roster — rank on skill, not luck.
    decisions: [select, size]
    tiers: [R, E, P]
    status: planned
  - id: s2
    title: Uncertainty-honest tear-sheet engine
    lane: S
    one_liner: Every statistic as an interval with a verdict — honest by construction.
    decisions: [monitor, select]
    tiers: [R, E, P]
    status: planned
  - id: s3
    title: Sizing & alpha-decay lab
    lane: S
    one_liner: Picking, sizing, or holding? Trade-level event studies, power-gated.
    decisions: [size, select]
    tiers: [P, E]
    status: planned
  - id: s4
    title: Sell-discipline diagnostic
    lane: S
    one_liner: Where the edge leaks — exit timing vs a random-sell counterfactual.
    decisions: [engage, monitor]
    tiers: [P, E]
    status: planned
  - id: s5
    title: Short-book quality score
    lane: S
    one_liner: Is short alpha real, or just an expensive beta hedge?
    decisions: [size, redeem]
    tiers: [P, E, R]
    status: planned
  - id: s6
    title: Returns-only sizing & decay signatures
    lane: S
    one_liner: Can monthly returns alone reveal sizing or decay? A pre-registered test.
    decisions: [monitor, select]
    tiers: [R]
    status: planned
  - id: m1
    title: Exposure hygiene & drift monitor
    lane: M
    one_liner: Does the book respect its stated bands, or is drift creeping in?
    decisions: [monitor, engage]
    tiers: [E, P, R]
    status: planned
  - id: m2
    title: Hidden-convexity / short-vol screen
    lane: M
    one_liner: A smooth Sharpe can hide sold optionality — surface the short-vol posture.
    decisions: [monitor, redeem]
    tiers: [R, E, P]
    status: planned
  - id: m3
    title: Simulation-calibrated drawdown alarms
    lane: M
    one_liner: Drawdown alarms tuned to each manager's own null, not a flat rule.
    decisions: [redeem, monitor]
    tiers: [R, E]
    status: planned
  - id: m4
    title: Crowding & overlap radar
    lane: M
    one_liner: Is our diversification illusory — are the managers the same trade?
    decisions: [size, monitor, redeem]
    tiers: [P, E, R]
    status: planned
  - id: m5
    title: Say–do gap monitor
    lane: M
    one_liner: Does the portfolio match the letter? Say vs do, side by side.
    decisions: [monitor, engage]
    tiers: [R, E, P]
    status: planned
  - id: m6
    title: 13F long-book intelligence
    lane: M
    one_liner: Mining free quarterly 13F filings for per-manager conviction signals.
    decisions: [monitor, engage]
    tiers: [P]
    status: planned
  - id: p1
    title: Allocation under alpha uncertainty
    lane: P
    one_liner: Given posterior skill, how much capital? Sizing that consumes uncertainty.
    decisions: [size, redeem]
    tiers: [R, E, P]
    status: planned
  - id: p2
    title: Tiered book X-ray
    lane: P
    one_liner: One book-level factor view fusing managers across transparency tiers.
    decisions: [monitor, size]
    tiers: [R, E, P]
    status: planned
  - id: p3
    title: Hire/fire decision audit & journal
    lane: P
    one_liner: Backtest your own hire/fire timing — governance turned into data.
    decisions: [redeem, select]
    tiers: [R]
    status: planned
  - id: e1
    title: Trust-preserving transparency ladder
    lane: E
    one_liner: The escalating-data-ask playbook — each rung's ask, reciprocity, and math.
    decisions: [engage]
    tiers: [R, E, P]
    status: planned
  - id: e2
    title: Narrated engagement-pack generator
    lane: E
    one_liner: One command renders a per-manager, print-clean engagement pack.
    decisions: [engage]
    tiers: [R, E, P]
    status: planned
  - id: e3
    title: Manager knowledge graph & retrieval
    lane: E
    one_liner: Structured memory over letters and notes, anchored to decision hooks.
    decisions: [engage, select]
    tiers: [R, E, P]
    status: planned
  - id: x1
    title: Tier & Power Atlas
    lane: X
    one_liner: How much data until a metric means anything — the tier & power atlas.
    decisions: [select, monitor, engage]
    tiers: [R, E, P]
    status: planned
  - id: x2
    title: Transparency playground
    lane: X
    one_liner: Drag the dials and watch honest claims dissolve into grey.
    decisions: [engage]
    tiers: [R, E, P]
    status: planned
  ```

- [ ] **Step 6: Write the failing build test.**
  Create `tests/site/test_build.py`:
  ```python
  from pathlib import Path

  from quant_allocator.site.build import build

  REPO_ROOT = Path(__file__).resolve().parents[2]

  EXPECTED_TITLES = [
      "Hierarchical Bayesian alpha engine",
      "Uncertainty-honest tear-sheet engine",
      "Sizing & alpha-decay lab",
      "Sell-discipline diagnostic",
      "Short-book quality score",
      "Returns-only sizing & decay signatures",
      "Exposure hygiene & drift monitor",
      "Hidden-convexity / short-vol screen",
      "Simulation-calibrated drawdown alarms",
      "Crowding & overlap radar",
      "Say–do gap monitor",
      "13F long-book intelligence",
      "Allocation under alpha uncertainty",
      "Tiered book X-ray",
      "Hire/fire decision audit & journal",
      "Trust-preserving transparency ladder",
      "Narrated engagement-pack generator",
      "Manager knowledge graph & retrieval",
      "Tier & Power Atlas",
      "Transparency playground",
  ]


  def test_index_lists_all_cards(tmp_path):
      out = tmp_path / "out"
      build(REPO_ROOT / "site", out)
      index = (out / "index.html").read_text(encoding="utf-8")
      assert "All data on this site is synthetic or public." in index
      assert index.count("card-tile__title") == 20
      # NOTE: Task 6 flips e1 to live; update this count to 19 there.
      assert index.count("card-tile--planned") == 20
      for title in EXPECTED_TITLES:
          assert title in index


  def test_assets_copied(tmp_path):
      out = tmp_path / "out"
      build(REPO_ROOT / "site", out)
      assert (out / "assets" / "design-tokens.css").exists()
      assert (out / "assets" / "interval.js").exists()
  ```

- [ ] **Step 7: Run the test and watch it fail.**
  ```bash
  uv run pytest tests/site/test_build.py -q
  ```
  Expected: `AttributeError` / `ImportError` — `build` is not yet defined in `build.py`.

- [ ] **Step 8: Implement `build()` v1, `_render_index`, and `_copy_assets`.**
  In `src/quant_allocator/site/build.py`, replace the import block at the top:
  ```python
  from __future__ import annotations

  from pathlib import Path

  import yaml
  ```
  with:
  ```python
  from __future__ import annotations

  import shutil
  from pathlib import Path

  import yaml
  from jinja2 import Environment, FileSystemLoader
  ```
  Then, immediately after the `GOLIVE_KEYS = {...}` line, add:
  ```python
  # Placeholder repo URL; set the real one at Pages enablement (see docs/PUBLISHING.md).
  REPO_URL = "https://github.com/USERNAME/quant-allocator"
  SITE_TITLE = "Quant Allocator — Idea Gallery"
  LANE_ORDER = ["S", "M", "P", "E", "X"]
  LANE_HEADINGS = {
      "S": "S — Skill & inference",
      "M": "M — Monitoring & early warning",
      "P": "P — Portfolio construction & governance",
      "E": "E — Engagement & knowledge",
      "X": "X — Meta / infrastructure",
  }
  ```
  Then append these three functions to the end of the file:
  ```python
  def build(site_dir: Path, out_dir: Path) -> None:
      """Validate the manifest and render the index, then copy assets."""
      cards = load_manifest(site_dir / "cards.yaml")

      env = Environment(
          loader=FileSystemLoader(str(site_dir / "templates")),
          autoescape=True,
      )
      env.globals["repo_url"] = REPO_URL
      env.globals["site_title"] = SITE_TITLE

      out_dir.mkdir(parents=True, exist_ok=True)
      _render_index(env, cards, out_dir)
      _copy_assets(site_dir, out_dir)


  def _render_index(env: Environment, cards: list[dict], out_dir: Path) -> None:
      lanes = [
          {
              "key": lane,
              "heading": LANE_HEADINGS[lane],
              "cards": [card for card in cards if card["lane"] == lane],
          }
          for lane in LANE_ORDER
      ]
      html = env.get_template("index.html.j2").render(
          lanes=lanes, page_title="Idea Gallery", asset_base="", default_theme="light"
      )
      (out_dir / "index.html").write_text(html, encoding="utf-8")


  def _copy_assets(site_dir: Path, out_dir: Path) -> None:
      dest = out_dir / "assets"
      if dest.exists():
          shutil.rmtree(dest)
      shutil.copytree(site_dir / "assets", dest)
  ```

- [ ] **Step 9: Run the test and watch it pass.**
  ```bash
  uv run pytest tests/site/test_build.py -q
  ```
  Expected: `2 passed`.

- [ ] **Step 10: Confirm ruff clean and commit.**
  ```bash
  uv run ruff check src/quant_allocator/site tests/site
  git add -A && git commit -m "feat: design tokens, base and index templates, manifest, build v1"
  ```
  Expected: `All checks passed!`; commit succeeds.

---

## Task 3: `interval.css` — full component set and print CSS

**Files:**
- Create: `site/assets/interval.css`
- Test: `tests/site/test_interval_css.py`

**Interfaces:**
- Consumes: the frozen component DOM contracts below (future Plan B pages consume these class names — treat them as a frozen API).
- Produces: `site/assets/interval.css`, copied verbatim into `out_dir/assets/` by `build()`.

**Frozen component DOM contracts** (interval.css styles exactly these):
```html
<div class="interval-stat" data-verdict="robust|shrink|noise">
  <span class="interval-stat__label">SHARPE (DE-SMOOTHED, ANN.)</span>
  <span class="interval-stat__value">0.74</span>
  <div class="interval-stat__rail">
    <div class="interval-stat__band" style="left:12%;width:56%"></div>
    <div class="interval-stat__point" style="left:38%"></div>
  </div>
  <span class="interval-stat__range">95% CI 0.11 – 1.38</span>
</div>

<div class="power-gate">
  <span class="power-gate__title">HIT RATE</span>
  <p class="power-gate__reason">Needs ≈780 independent trades to separate 55% from coin-flip; this book has 112.</p>
</div>

<span class="tier-badge" data-tier="R|E|P">R</span>
<span class="verdict-chip" data-verdict="robust|shrink|noise">shrink</span>
<span class="synthetic-badge">SYNTHETIC DATA</span>

<dl class="golive-box">
  <dt>Data ask</dt><dd>Monthly returns (R)</dd>
  <dt>Sample required</dt><dd>≥ 36 months</dd>
  <dt>Build effort</dt><dd>S</dd>
</dl>
```

- [ ] **Step 1: Write the failing CSS-presence test.**
  Create `tests/site/test_interval_css.py`:
  ```python
  from pathlib import Path

  REPO_ROOT = Path(__file__).resolve().parents[2]
  CSS_PATH = REPO_ROOT / "site" / "assets" / "interval.css"

  REQUIRED_TOKENS = [
      ".interval-stat",
      ".interval-stat__label",
      ".interval-stat__value",
      ".interval-stat__rail",
      ".interval-stat__band",
      ".interval-stat__point",
      ".interval-stat__range",
      ".power-gate",
      ".power-gate__title",
      ".power-gate__reason",
      ".tier-badge",
      ".verdict-chip",
      '[data-verdict="robust"]',
      '[data-verdict="shrink"]',
      '[data-verdict="noise"]',
      ".synthetic-badge",
      ".golive-box",
      ".usage-note",
      ".card-tile",
      ".card-tile--planned",
      ".decision-chip",
      ".pack-page",
      ".ladder-rung",
      "@media print",
      "@page",
      "prefers-reduced-motion",
      ":focus-visible",
  ]


  def test_interval_css_defines_all_contract_classes():
      css = CSS_PATH.read_text(encoding="utf-8")
      missing = [token for token in REQUIRED_TOKENS if token not in css]
      assert not missing, f"interval.css missing: {missing}"
  ```

- [ ] **Step 2: Run the test and watch it fail.**
  ```bash
  uv run pytest tests/site/test_interval_css.py -q
  ```
  Expected: failure — `FileNotFoundError` (interval.css does not exist yet).

- [ ] **Step 3: Create `interval.css` with the full component set and print CSS.**
  Create `site/assets/interval.css`:
  ```css
  /* Labels: 10px uppercase, +0.10em tracking (demo-layer spec typography). */
  .interval-stat__label,
  .power-gate__title,
  .tier-badge,
  .synthetic-badge,
  .card-tile__wave,
  .golive-box dt {
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: 0.10em;
    color: var(--dim);
  }

  /* Cards: 8px radius, 1px hairline, no shadows. */
  .card-tile,
  .golive-box,
  .power-gate,
  .interval-stat {
    border: 1px solid var(--line);
    border-radius: 8px;
  }

  /* IntervalStat: point + rail + range text. */
  .interval-stat {
    display: grid;
    gap: 6px;
    padding: 12px 14px;
    background: var(--paper);
  }

  .interval-stat__value {
    font-size: 22px;
    font-weight: 600;
    color: var(--ink);
    font-variant-numeric: tabular-nums;
  }

  .interval-stat__rail {
    position: relative;
    height: 4px;
    background: var(--track);
    border-radius: 2px;
  }

  .interval-stat__band {
    position: absolute;
    top: 0;
    height: 4px;
    background: var(--band);
    border-radius: 2px;
  }

  .interval-stat__point {
    position: absolute;
    top: -3px;
    width: 2px;
    height: 10px;
    background: var(--accent);
  }

  .interval-stat__range {
    font-size: 12px;
    color: var(--dim);
    font-variant-numeric: tabular-nums;
  }

  .interval-stat[data-verdict="shrink"] .interval-stat__point {
    background: var(--warn);
  }

  .interval-stat[data-verdict="noise"] .interval-stat__point {
    background: var(--dim);
  }

  /* PowerGate: dashed empty-state, dim only, no accent inside. */
  .power-gate {
    border-style: dashed;
    border-color: var(--dim);
    padding: 14px;
    color: var(--dim);
    background: transparent;
  }

  .power-gate__reason {
    margin: 6px 0 0;
    font-size: 13px;
    color: var(--dim);
  }

  /* TierBadge: 1px solid line, letter + optional label. */
  .tier-badge {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 2px 6px;
    border: 1px solid var(--line);
    border-radius: 4px;
    color: var(--dim);
  }

  /* VerdictChip: outline chips, transparent bg. */
  .verdict-chip {
    display: inline-flex;
    padding: 2px 8px;
    border: 1px solid currentColor;
    border-radius: 999px;
    background: transparent;
    font-size: 11px;
    text-transform: lowercase;
  }

  .verdict-chip[data-verdict="robust"] {
    color: var(--accent);
  }

  .verdict-chip[data-verdict="shrink"] {
    color: var(--warn);
  }

  .verdict-chip[data-verdict="noise"] {
    color: var(--dim);
  }

  /* SyntheticBadge: fixed top-right, warn outline chip. */
  .synthetic-badge {
    position: fixed;
    top: 10px;
    right: 10px;
    z-index: 50;
    padding: 3px 8px;
    border: 1px solid var(--warn);
    border-radius: 4px;
    color: var(--warn);
    background: var(--paper);
  }

  /* GoLiveBox: three labeled fields. */
  .golive-box {
    display: grid;
    grid-template-columns: max-content 1fr;
    gap: 4px 16px;
    padding: 14px 16px;
    margin: 20px 0;
  }

  .golive-box dt {
    align-self: center;
  }

  .golive-box dd {
    margin: 0;
    color: var(--ink);
  }

  /* UsageNote: doctrine-card replacement for the go-live box. */
  .usage-note {
    border-left: 3px solid var(--accent);
    padding: 8px 16px;
    margin: 20px 0;
  }

  /* Header / banner / footer. */
  .site-header {
    display: flex;
    align-items: center;
    gap: 16px;
    padding: 12px 20px;
    border-bottom: 1px solid var(--line);
  }

  .site-header__title {
    font-weight: 600;
  }

  .site-nav {
    margin-left: auto;
  }

  .theme-toggle {
    border: 1px solid var(--line);
    border-radius: 6px;
    background: transparent;
    color: var(--ink);
    padding: 4px 10px;
    cursor: pointer;
  }

  .site-banner {
    padding: 6px 20px;
    font-size: 12px;
    color: var(--dim);
    border-bottom: 1px solid var(--line);
  }

  .site-main {
    max-width: 960px;
    margin: 0 auto;
    padding: 24px 20px;
  }

  .site-footer {
    display: flex;
    gap: 16px;
    padding: 20px;
    border-top: 1px solid var(--line);
    font-size: 12px;
    color: var(--dim);
  }

  .skip-link {
    position: absolute;
    left: -9999px;
  }

  .skip-link:focus {
    left: 8px;
    top: 8px;
  }

  /* Index tiles. */
  .card-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
    gap: 16px;
  }

  .card-tile {
    display: block;
    padding: 16px;
    background: var(--paper);
    color: inherit;
    text-decoration: none;
  }

  .card-tile--planned {
    opacity: 0.55;
  }

  .card-tile__title {
    margin: 0 0 6px;
    font-size: 16px;
  }

  .card-tile__oneliner {
    margin: 0 0 12px;
    font-size: 13px;
    color: var(--dim);
  }

  .card-tile__meta,
  .card-tile__tiers {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
  }

  .card-tile__tiers {
    margin-top: 8px;
  }

  .decision-chip {
    padding: 2px 8px;
    border: 1px solid var(--line);
    border-radius: 999px;
    font-size: 11px;
    color: var(--dim);
  }

  .card-tile__wave {
    display: inline-block;
    margin-bottom: 8px;
    padding: 2px 6px;
    border: 1px solid var(--warn);
    border-radius: 4px;
    color: var(--warn);
  }

  /* Demo page + badge row. */
  .badge-row {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-bottom: 12px;
  }

  .spec-link {
    margin-top: 24px;
  }

  /* Pack / ladder (print showcase). */
  .pack-page {
    max-width: 720px;
  }

  .ladder-rung {
    padding: 16px 0;
    border-top: 1px solid var(--line);
  }

  .ladder-rung__heading {
    font-size: 17px;
  }

  .ladder-rung__scope {
    color: var(--dim);
    font-weight: 400;
  }

  .ladder-rung__body dt {
    margin-top: 8px;
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: 0.10em;
    color: var(--dim);
  }

  .ladder-rung__body dd {
    margin: 2px 0 0;
  }

  .ladder-standing {
    margin-top: 24px;
  }

  /* Tables scroll inside their own overflow container. */
  .spec-page__body table,
  .demo-page table {
    display: block;
    overflow-x: auto;
    border-collapse: collapse;
    font-variant-numeric: tabular-nums;
  }

  .spec-page__body th,
  .spec-page__body td {
    border: 1px solid var(--line);
    padding: 6px 10px;
    text-align: left;
  }

  /* Accessibility. */
  a:focus-visible,
  button:focus-visible,
  .card-tile:focus-visible {
    outline: 2px solid var(--accent);
    outline-offset: 2px;
  }

  @media (prefers-reduced-motion: reduce) {
    * {
      transition: none !important;
      animation: none !important;
    }
  }

  /* Print: hide nav + toggle; provenance survives paper. */
  @media print {
    .site-nav,
    .theme-toggle,
    .skip-link {
      display: none !important;
    }

    .site-banner {
      display: block !important;
    }

    .synthetic-badge {
      position: static;
      display: inline-block !important;
    }

    .pack-page section {
      break-inside: avoid;
    }

    @page {
      margin: 18mm;
    }
  }
  ```

- [ ] **Step 4: Run the test and watch it pass.**
  ```bash
  uv run pytest tests/site/test_interval_css.py -q
  ```
  Expected: `1 passed`.

- [ ] **Step 5: Commit.**
  ```bash
  uv run ruff check tests/site
  git add -A && git commit -m "feat: interval.css component set and print stylesheet"
  ```
  Expected: `All checks passed!`; commit succeeds.

---

## Task 4: Spec pipeline — vendored KaTeX, `spec.html.j2`, Markdown rendering, math passthrough

**Files:**
- Create: `site/assets/katex/*` (vendored, committed)
- Create: `site/templates/spec.html.j2`
- Modify: `src/quant_allocator/site/build.py` (add `_render_specs`; call it from `build()`)
- Test: `tests/site/test_specs.py`

**Interfaces:**
- Consumes: live cards' `spec` Markdown files under `docs/ideas/specs/`.
- Produces: `out_dir/specs/<id>.html` per live card; math delimiters pass through untouched for client-side KaTeX.

- [ ] **Step 1: Vendor KaTeX 0.16.21 (self-hosted, committed).**
  Run exactly (from the repo root):
  ```bash
  mkdir -p site/assets/katex/contrib site/assets/katex/fonts
  curl -fsSL https://cdn.jsdelivr.net/npm/katex@0.16.21/dist/katex.min.css \
    -o site/assets/katex/katex.min.css
  curl -fsSL https://cdn.jsdelivr.net/npm/katex@0.16.21/dist/katex.min.js \
    -o site/assets/katex/katex.min.js
  curl -fsSL https://cdn.jsdelivr.net/npm/katex@0.16.21/dist/contrib/auto-render.min.js \
    -o site/assets/katex/contrib/auto-render.min.js
  KATEX_FONTS=(AMS-Regular Caligraphic-Bold Caligraphic-Regular Fraktur-Bold \
    Fraktur-Regular Main-Bold Main-BoldItalic Main-Italic Main-Regular \
    Math-BoldItalic Math-Italic SansSerif-Bold SansSerif-Italic \
    SansSerif-Regular Script-Regular Size1-Regular Size2-Regular \
    Size3-Regular Size4-Regular Typewriter-Regular)
  for font in "${KATEX_FONTS[@]}"; do
    curl -fsSL "https://cdn.jsdelivr.net/npm/katex@0.16.21/dist/fonts/KaTeX_${font}.woff2" \
      -o "site/assets/katex/fonts/KaTeX_${font}.woff2"
  done
  ```
  Verify (expected `23`: css + js + auto-render + 20 fonts):
  ```bash
  find site/assets/katex -type f | wc -l
  ```
  Expected output: `      23`.

- [ ] **Step 2: Create the spec template.**
  Create `site/templates/spec.html.j2`:
  ```jinja
  {% extends "base.html.j2" %}

  {% block head_extra %}
  <link rel="stylesheet" href="{{ asset_base | default('') }}assets/katex/katex.min.css">
  {% endblock %}

  {% block content %}
  <article class="spec-page">
    <a class="spec-page__back" href="{{ asset_base | default('') }}index.html">← Gallery</a>
    <div class="spec-page__body">
      {{ spec_html | safe }}
    </div>
  </article>
  {% endblock %}

  {% block body_scripts %}
  <script defer src="{{ asset_base | default('') }}assets/katex/katex.min.js"></script>
  <script defer src="{{ asset_base | default('') }}assets/katex/contrib/auto-render.min.js"></script>
  <script>
    window.addEventListener("DOMContentLoaded", function () {
      renderMathInElement(document.body, {
        delimiters: [
          { left: "$$", right: "$$", display: true },
          { left: "$", right: "$", display: false }
        ]
      });
    });
  </script>
  {% endblock %}
  ```
  (The deferred external scripts execute before `DOMContentLoaded`, so `renderMathInElement` is defined when the listener fires.)

- [ ] **Step 3: Write the failing spec test.**
  Create `tests/site/test_specs.py`:
  ```python
  import shutil

  import yaml

  from pathlib import Path

  from quant_allocator.site.build import build

  REPO_ROOT = Path(__file__).resolve().parents[2]


  def _fixture_site(tmp_path):
      site = tmp_path / "site"
      shutil.copytree(REPO_ROOT / "site" / "templates", site / "templates")
      shutil.copytree(REPO_ROOT / "site" / "assets", site / "assets")
      (site / "templates" / "pages").mkdir(exist_ok=True)
      (site / "templates" / "pages" / "t1.html.j2").write_text("", encoding="utf-8")
      (site / "data").mkdir()
      (site / "data" / "t1.json").write_text("{}", encoding="utf-8")
      specs = tmp_path / "docs" / "ideas" / "specs"
      specs.mkdir(parents=True)
      (specs / "t1.md").write_text(
          "# Spec\n\nInline math $\\alpha$ here.\n\n"
          "| a | b |\n| --- | --- |\n| 1 | 2 |\n",
          encoding="utf-8",
      )
      (site / "cards.yaml").write_text(
          yaml.safe_dump(
              [
                  {
                      "id": "t1",
                      "title": "Test card",
                      "lane": "S",
                      "one_liner": "x",
                      "decisions": ["select"],
                      "tiers": ["R"],
                      "status": "live",
                      "demo": "pages/t1.html.j2",
                      "data": "t1.json",
                      "spec": "t1.md",
                      "golive": {"data_ask": "R", "sample": "36m", "effort": "S"},
                  }
              ]
          ),
          encoding="utf-8",
      )
      return site


  def test_spec_renders_math_untouched_and_table(tmp_path):
      site = _fixture_site(tmp_path)
      build(site, tmp_path / "out")
      html = (tmp_path / "out" / "specs" / "t1.html").read_text(encoding="utf-8")
      assert r"$\alpha$" in html
      assert "<table>" in html
  ```

- [ ] **Step 4: Run the test and watch it fail.**
  ```bash
  uv run pytest tests/site/test_specs.py -q
  ```
  Expected: failure — `FileNotFoundError` for `out/specs/t1.html` (specs are not rendered yet). Note: the fixture live card has a `pages/t1.html.j2` demo file so `load_manifest` passes; `build()` at this task renders index + specs only (demo-page rendering arrives in Task 5).

- [ ] **Step 5: Add Markdown import, extensions constant, and `_render_specs`.**
  In `src/quant_allocator/site/build.py`, change the import block to add `markdown`:
  ```python
  from __future__ import annotations

  import shutil
  from pathlib import Path

  import markdown
  import yaml
  from jinja2 import Environment, FileSystemLoader
  ```
  Add this constant next to the other constants (e.g. under `LANE_HEADINGS`):
  ```python
  MARKDOWN_EXTENSIONS = ["tables", "fenced_code", "toc"]
  ```
  Append `_render_specs` to the end of the file:
  ```python
  def _render_specs(env: Environment, cards: list[dict], site_dir: Path, out_dir: Path) -> None:
      template = env.get_template("spec.html.j2")
      specs_dir = site_dir.parent / "docs" / "ideas" / "specs"
      out_specs = out_dir / "specs"
      out_specs.mkdir(parents=True, exist_ok=True)
      for card in cards:
          if card["status"] != "live":
              continue
          source = specs_dir / card["spec"]
          body_html = markdown.markdown(
              source.read_text(encoding="utf-8"), extensions=MARKDOWN_EXTENSIONS
          )
          html = template.render(
              page_title=card["title"],
              card=card,
              spec_html=body_html,
              asset_base="../",
              default_theme="light",
          )
          (out_specs / f"{card['id']}.html").write_text(html, encoding="utf-8")
  ```
  Update `build()` to call it — replace the body of `build()` with:
  ```python
  def build(site_dir: Path, out_dir: Path) -> None:
      """Validate the manifest, render the index and specs, then copy assets."""
      cards = load_manifest(site_dir / "cards.yaml")

      env = Environment(
          loader=FileSystemLoader(str(site_dir / "templates")),
          autoescape=True,
      )
      env.globals["repo_url"] = REPO_URL
      env.globals["site_title"] = SITE_TITLE

      out_dir.mkdir(parents=True, exist_ok=True)
      _render_index(env, cards, out_dir)
      _render_specs(env, cards, site_dir, out_dir)
      _copy_assets(site_dir, out_dir)
  ```

- [ ] **Step 6: Run the test and watch it pass.**
  ```bash
  uv run pytest tests/site/test_specs.py -q
  ```
  Expected: `1 passed`.

- [ ] **Step 7: Confirm ruff clean and commit (KaTeX vendored files included).**
  ```bash
  uv run ruff check src/quant_allocator/site tests/site
  git add -A && git commit -m "feat: spec pipeline with vendored KaTeX and markdown rendering"
  ```
  Expected: `All checks passed!`; commit succeeds.

---

## Task 5: Demo-page skeleton and honest-mockup lint

**Files:**
- Create: `site/templates/demo.html.j2`
- Modify: `src/quant_allocator/site/build.py` (add `_render_demo_pages`, `_lint_outputs`; call both from `build()`)
- Test: `tests/site/test_lint.py`

**Interfaces:**
- Consumes: live cards' `demo` templates and (non-doctrine) `data` JSON.
- Produces: `out_dir/<id>.html` per live card; `_lint_outputs(cards, out_dir)` raises `BuildError` on any provenance/link violation.

- [ ] **Step 1: Create the demo-page skeleton.**
  Create `site/templates/demo.html.j2`:
  ```jinja
  {% extends "base.html.j2" %}

  {% block content %}
  <article class="demo-page">
    <div class="badge-row">
      {% if not card.doctrine %}<span class="synthetic-badge">SYNTHETIC DATA</span>{% endif %}
      {% for tier in card.tiers %}<span class="tier-badge" data-tier="{{ tier }}">{{ tier }}</span>{% endfor %}
    </div>
    <h1 class="demo-page__title">{{ card.title }}</h1>
    <p class="demo-page__oneliner">{{ card.one_liner }}</p>

    {% if not card.doctrine %}
    <script type="application/json" id="card-data">{{ card_data_json | safe }}</script>
    {% endif %}

    {% block demo_content %}{% endblock %}

    <section class="demo-methodology">
      <h2>Methodology</h2>
      {% block methodology %}{% endblock %}
    </section>

    {% if card.doctrine %}
    <aside class="usage-note">
      <h2>How to use this</h2>
      <p>{{ card.usage_note }}</p>
    </aside>
    {% else %}
    <dl class="golive-box">
      <dt>Data ask</dt><dd>{{ card.golive.data_ask }}</dd>
      <dt>Sample required</dt><dd>{{ card.golive.sample }}</dd>
      <dt>Build effort</dt><dd>{{ card.golive.effort }}</dd>
    </dl>
    {% endif %}

    <p class="spec-link">
      <a href="{{ asset_base | default('') }}specs/{{ card.id }}.html">Full method spec →</a>
    </p>
  </article>
  {% endblock %}
  ```

- [ ] **Step 2: Write the failing lint tests.**
  Create `tests/site/test_lint.py`:
  ```python
  import shutil

  import yaml

  import pytest

  from pathlib import Path

  from quant_allocator.site.build import BuildError, _lint_outputs, build

  REPO_ROOT = Path(__file__).resolve().parents[2]

  VALID_PAGE = '<span class="synthetic-badge"></span><dl class="golive-box"></dl>'


  def _card(**overrides):
      card = {"id": "t1", "status": "live"}
      card.update(overrides)
      return card


  def _write_page(out_dir, card_id, html):
      out_dir.mkdir(parents=True, exist_ok=True)
      (out_dir / f"{card_id}.html").write_text(html, encoding="utf-8")


  def _write_spec(out_dir, card_id):
      specs = out_dir / "specs"
      specs.mkdir(parents=True, exist_ok=True)
      (specs / f"{card_id}.html").write_text("<html></html>", encoding="utf-8")


  def test_lint_passes_for_valid_nondoctrine(tmp_path):
      _write_page(tmp_path, "t1", VALID_PAGE)
      _write_spec(tmp_path, "t1")
      _lint_outputs([_card()], tmp_path)


  def test_lint_missing_synthetic_badge_raises(tmp_path):
      _write_page(tmp_path, "t1", '<dl class="golive-box"></dl>')
      _write_spec(tmp_path, "t1")
      with pytest.raises(BuildError, match="synthetic-badge"):
          _lint_outputs([_card()], tmp_path)


  def test_lint_missing_golive_raises(tmp_path):
      _write_page(tmp_path, "t1", '<span class="synthetic-badge"></span>')
      _write_spec(tmp_path, "t1")
      with pytest.raises(BuildError, match="golive-box"):
          _lint_outputs([_card()], tmp_path)


  def test_lint_dangling_spec_link_raises(tmp_path):
      _write_page(tmp_path, "t1", VALID_PAGE)
      with pytest.raises(BuildError, match="spec link target missing"):
          _lint_outputs([_card()], tmp_path)


  def test_lint_doctrine_requires_usage_note(tmp_path):
      _write_page(tmp_path, "e1", '<aside class="usage-note"></aside>')
      _write_spec(tmp_path, "e1")
      _lint_outputs([_card(id="e1", doctrine=True)], tmp_path)


  def test_lint_doctrine_missing_usage_note_raises(tmp_path):
      _write_page(tmp_path, "e1", "<article></article>")
      _write_spec(tmp_path, "e1")
      with pytest.raises(BuildError, match="usage-note"):
          _lint_outputs([_card(id="e1", doctrine=True)], tmp_path)


  def test_build_fails_on_missing_data_file(tmp_path):
      site = tmp_path / "site"
      shutil.copytree(REPO_ROOT / "site" / "templates", site / "templates")
      shutil.copytree(REPO_ROOT / "site" / "assets", site / "assets")
      (site / "templates" / "pages" / "t1.html.j2").write_text(
          "{% extends 'demo.html.j2' %}", encoding="utf-8"
      )
      (site / "data").mkdir()
      specs = tmp_path / "docs" / "ideas" / "specs"
      specs.mkdir(parents=True)
      (specs / "t1.md").write_text("# t1", encoding="utf-8")
      (site / "cards.yaml").write_text(
          yaml.safe_dump(
              [
                  {
                      "id": "t1",
                      "title": "Test card",
                      "lane": "S",
                      "one_liner": "x",
                      "decisions": ["select"],
                      "tiers": ["R"],
                      "status": "live",
                      "demo": "pages/t1.html.j2",
                      "data": "t1.json",
                      "spec": "t1.md",
                      "golive": {"data_ask": "R", "sample": "36m", "effort": "S"},
                  }
              ]
          ),
          encoding="utf-8",
      )
      with pytest.raises(BuildError, match="missing data file"):
          build(site, tmp_path / "out")


  def test_real_demo_page_has_furniture(tmp_path):
      site = tmp_path / "site"
      shutil.copytree(REPO_ROOT / "site" / "templates", site / "templates")
      shutil.copytree(REPO_ROOT / "site" / "assets", site / "assets")
      (site / "templates" / "pages" / "t1.html.j2").write_text(
          "{% extends 'demo.html.j2' %}", encoding="utf-8"
      )
      (site / "data").mkdir()
      (site / "data" / "t1.json").write_text('{"ok": true}', encoding="utf-8")
      specs = tmp_path / "docs" / "ideas" / "specs"
      specs.mkdir(parents=True)
      (specs / "t1.md").write_text("# t1", encoding="utf-8")
      (site / "cards.yaml").write_text(
          yaml.safe_dump(
              [
                  {
                      "id": "t1",
                      "title": "Test card",
                      "lane": "S",
                      "one_liner": "x",
                      "decisions": ["select"],
                      "tiers": ["R"],
                      "status": "live",
                      "demo": "pages/t1.html.j2",
                      "data": "t1.json",
                      "spec": "t1.md",
                      "golive": {"data_ask": "R", "sample": "36m", "effort": "S"},
                  }
              ]
          ),
          encoding="utf-8",
      )
      build(site, tmp_path / "out")
      html = (tmp_path / "out" / "t1.html").read_text(encoding="utf-8")
      assert "synthetic-badge" in html
      assert "golive-box" in html
      assert 'id="card-data"' in html
      assert "specs/t1.html" in html
  ```

- [ ] **Step 3: Run the tests and watch them fail.**
  ```bash
  uv run pytest tests/site/test_lint.py -q
  ```
  Expected: `ImportError: cannot import name '_lint_outputs'` (the function does not exist yet).

- [ ] **Step 4: Add `_render_demo_pages` and `_lint_outputs`, and wire them into `build()`.**
  Append both functions to the end of `src/quant_allocator/site/build.py`:
  ```python
  def _render_demo_pages(env: Environment, cards: list[dict], site_dir: Path, out_dir: Path) -> None:
      for card in cards:
          if card["status"] != "live":
              continue
          card_data_json = ""
          if not card.get("doctrine", False):
              card_data_json = (site_dir / "data" / card["data"]).read_text(encoding="utf-8")
          html = env.get_template(card["demo"]).render(
              page_title=card["title"],
              card=card,
              card_data_json=card_data_json,
              asset_base="",
              default_theme="light",
          )
          (out_dir / f"{card['id']}.html").write_text(html, encoding="utf-8")


  def _lint_outputs(cards: list[dict], out_dir: Path) -> None:
      """Fail loudly if any live page is missing its provenance furniture or spec link."""
      for card in cards:
          if card["status"] != "live":
              continue
          page_path = out_dir / f"{card['id']}.html"
          html = page_path.read_text(encoding="utf-8")

          if card.get("doctrine", False):
              if "usage-note" not in html:
                  raise BuildError(
                      f"{page_path}: doctrine card '{card['id']}' output missing usage-note block"
                  )
          else:
              if "synthetic-badge" not in html:
                  raise BuildError(
                      f"{page_path}: card '{card['id']}' output missing synthetic-badge"
                  )
              if "golive-box" not in html:
                  raise BuildError(
                      f"{page_path}: card '{card['id']}' output missing golive-box"
                  )

          spec_target = out_dir / "specs" / f"{card['id']}.html"
          if not spec_target.exists():
              raise BuildError(
                  f"{page_path}: card '{card['id']}' spec link target missing: {spec_target}"
              )
  ```
  Replace the body of `build()` with the final pipeline:
  ```python
  def build(site_dir: Path, out_dir: Path) -> None:
      """Validate the manifest, render index/specs/demo pages, copy assets, lint."""
      cards = load_manifest(site_dir / "cards.yaml")

      env = Environment(
          loader=FileSystemLoader(str(site_dir / "templates")),
          autoescape=True,
      )
      env.globals["repo_url"] = REPO_URL
      env.globals["site_title"] = SITE_TITLE

      out_dir.mkdir(parents=True, exist_ok=True)
      _render_index(env, cards, out_dir)
      _render_specs(env, cards, site_dir, out_dir)
      _render_demo_pages(env, cards, site_dir, out_dir)
      _copy_assets(site_dir, out_dir)
      _lint_outputs(cards, out_dir)
  ```

- [ ] **Step 5: Run the tests and watch them pass.**
  ```bash
  uv run pytest tests/site/test_lint.py -q
  ```
  Expected: `8 passed`.

- [ ] **Step 6: Run the full new suite and commit.**
  ```bash
  uv run pytest tests/site -q && uv run ruff check src/quant_allocator/site tests/site
  git add -A && git commit -m "feat: demo-page skeleton and honest-mockup lint"
  ```
  Expected: all site tests pass; `All checks passed!`; commit succeeds.

---

## Task 6: E1 ladder page — flip e1 to live (doctrine), full build passes lint

**Files:**
- Create: `site/templates/pages/e1-ladder.html.j2`
- Verify exists (do NOT modify): `docs/ideas/specs/e1-transparency-ladder.md`
- Modify: `site/cards.yaml` (flip `e1` to live)
- Modify: `tests/site/test_build.py` (update planned count 20 → 19)
- Test: `tests/site/test_e1.py`

**Interfaces:**
- Consumes: the e1 manifest entry (doctrine), the ladder page template, the spec stub.
- Produces: `out_dir/e1.html` (three rungs, no synthetic-badge, usage-note) and `out_dir/specs/e1.html`.

- [ ] **Step 1: Create the E1 ladder page template (verbatim content).**
  Create `site/templates/pages/e1-ladder.html.j2`:
  ```jinja
  {% extends "demo.html.j2" %}

  {% block demo_content %}
  <article class="pack-page ladder">
    <p class="ladder__intro">Transparency is granted, not owed. Every rung below pairs an ask with what the manager receives back, and with the statistical reason the ask exists — the ask is justified by the math, not by suspicion.</p>

    <section class="ladder-rung">
      <h2 class="ladder-rung__heading">Rung 1 — Monthly returns <span class="ladder-rung__scope">(every manager, default)</span></h2>
      <dl class="ladder-rung__body">
        <dt>The ask</dt>
        <dd>Monthly net returns, delivered timely.</dd>
        <dt>In return</dt>
        <dd>Our uncertainty-honest tear sheet of the manager — what we can and cannot conclude at their track length, stated plainly.</dd>
        <dt>Why the math asks</dt>
        <dd>At 36–60 months, returns support interval statements about Sharpe and factor mix, and little else; we will not pretend otherwise.</dd>
      </dl>
    </section>

    <section class="ladder-rung">
      <h2 class="ladder-rung__heading">Rung 2 — Exposure summaries <span class="ladder-rung__scope">(Open Protocol-aligned)</span></h2>
      <dl class="ladder-rung__body">
        <dt>The ask</dt>
        <dd>Monthly factor, sector, gross and net buckets in the industry-standard Open Protocol format.</dd>
        <dt>In return</dt>
        <dd>A peer-relative factor-hygiene pack and drift review, framed as help — the manager sees everything we compute.</dd>
        <dt>Why the math asks</dt>
        <dd>Returns alone cannot separate skill from style at this sample size; measured exposures pin the betas, which tightens the alpha interval — a question both sides want answered.</dd>
      </dl>
    </section>

    <section class="ladder-rung">
      <h2 class="ladder-rung__heading">Rung 3 — Positions <span class="ladder-rung__scope">(quarterly lag acceptable)</span></h2>
      <dl class="ladder-rung__body">
        <dt>The ask</dt>
        <dd>Position files, ideally with trade dates.</dd>
        <dt>In return</dt>
        <dd>The sizing and exit-timing diagnostics platforms give their own PMs — adjustable outputs, the manager keeps interpretive control.</dd>
        <dt>Why the math asks</dt>
        <dd>Sizing and exit skill are only measurable at position level; below this rung those analytics refuse to render rather than fake a number.</dd>
      </dl>
    </section>

    <section class="ladder-standing">
      <h2 class="ladder-standing__heading">Standing rules</h2>
      <ul>
        <li>An escalation is only made with a stated question attached, never as standing surveillance.</li>
        <li>The manager sees every analytic computed on rung-2-or-higher data.</li>
        <li>Asks are contractual and reciprocal.</li>
        <li>A declined ask is recorded and respected, not punished.</li>
      </ul>
    </section>
  </article>
  {% endblock %}

  {% block methodology %}
  <p>This ladder operationalizes the trust-preserving escalation doctrine: each rung's ask is justified by what the statistics can and cannot resolve at the available sample, and each ask is paired with reciprocal value returned to the manager.</p>
  {% endblock %}
  ```

- [ ] **Step 2: Verify the E1 method spec exists — do not create or modify it.**
  The full spec was authored and reviewed before this plan executes
  (commit `2724ccb`). Confirm it is present; if it is missing, STOP and
  report BLOCKED — do not write a stub in its place.
  ```bash
  test -s docs/ideas/specs/e1-transparency-ladder.md && echo OK
  ```
  Expected: `OK`

- [ ] **Step 3: Flip the e1 manifest entry to live (doctrine).**
  In `site/cards.yaml`, replace the entire `e1` entry with:
  ```yaml
  - id: e1
    title: Trust-preserving transparency ladder
    lane: E
    one_liner: The escalating-data-ask playbook — each rung's ask, reciprocity, and math.
    decisions: [engage]
    tiers: [R, E, P]
    status: live
    doctrine: true
    demo: pages/e1-ladder.html.j2
    spec: e1-transparency-ladder.md
    usage_note: One rung per relationship conversation. The 'why the math asks' line is the script.
  ```

- [ ] **Step 4: Update the planned-count assertion in `test_build.py`.**
  In `tests/site/test_build.py`, replace:
  ```python
      # NOTE: Task 6 flips e1 to live; update this count to 19 there.
      assert index.count("card-tile--planned") == 20
  ```
  with:
  ```python
      assert index.count("card-tile--planned") == 19
      assert 'href="e1.html"' in index
  ```

- [ ] **Step 5: Write the failing E1 test.**
  Create `tests/site/test_e1.py`:
  ```python
  from pathlib import Path

  from quant_allocator.site.build import build

  REPO_ROOT = Path(__file__).resolve().parents[2]


  def test_e1_ladder_page(tmp_path):
      build(REPO_ROOT / "site", tmp_path / "out")
      html = (tmp_path / "out" / "e1.html").read_text(encoding="utf-8")
      for rung in ["Rung 1", "Rung 2", "Rung 3"]:
          assert rung in html
      assert "synthetic-badge" not in html
      assert "usage-note" in html
      assert "Standing rules" in html
      assert (tmp_path / "out" / "specs" / "e1.html").exists()
  ```

- [ ] **Step 6: Run the E1 and build tests together.**
  ```bash
  uv run pytest tests/site/test_e1.py tests/site/test_build.py -q
  ```
  Expected: `3 passed` (e1 page test + both build tests).

- [ ] **Step 7: Run the full suite and commit.**
  ```bash
  uv run pytest -q && uv run ruff check src/quant_allocator tests
  git add -A && git commit -m "feat: E1 transparency-ladder doctrine page goes live"
  ```
  Expected: the whole suite (including existing adapter/simulator tests) passes; `All checks passed!`; commit succeeds.

---

## Task 7: Builder CLI and import isolation

**Files:**
- Create: `src/quant_allocator/site/__main__.py`
- Test: `tests/site/test_cli.py`

**Interfaces:**
- Consumes: CLI args `build [--site-dir site/] [--out site/_build/]`.
- Produces: full site build on the real tree; a guarantee that `quant_allocator.site.build` imports without numpy/pandas.

- [ ] **Step 1: Write the failing CLI + isolation tests.**
  Create `tests/site/test_cli.py`:
  ```python
  import os
  import subprocess
  import sys

  from pathlib import Path

  REPO_ROOT = Path(__file__).resolve().parents[2]


  def _run(args, **kwargs):
      env = {**os.environ, "PYTHONPATH": "src"}
      return subprocess.run(
          [sys.executable, *args],
          cwd=REPO_ROOT,
          env=env,
          capture_output=True,
          text=True,
          **kwargs,
      )


  def test_cli_build_smoke(tmp_path):
      out = tmp_path / "out"
      result = _run(["-m", "quant_allocator.site", "build", "--out", str(out)])
      assert result.returncode == 0, result.stderr
      assert (out / "index.html").exists()
      assert (out / "e1.html").exists()
      assert (out / "specs" / "e1.html").exists()


  def test_site_build_import_isolation():
      result = _run(
          [
              "-c",
              "import quant_allocator.site.build, sys; "
              "sys.exit(0 if ('numpy' not in sys.modules and 'pandas' not in sys.modules) else 1)",
          ]
      )
      assert result.returncode == 0, result.stderr
  ```

- [ ] **Step 2: Run the tests and watch them fail.**
  ```bash
  uv run pytest tests/site/test_cli.py -q
  ```
  Expected: `test_cli_build_smoke` fails with a non-zero return code — `python -m quant_allocator.site` has no `__main__.py` yet (`No module named quant_allocator.site.__main__`).

- [ ] **Step 3: Create the CLI entry point.**
  Create `src/quant_allocator/site/__main__.py`:
  ```python
  """CLI entry point: python -m quant_allocator.site build [--site-dir ...] [--out ...]."""

  from __future__ import annotations

  import argparse
  from pathlib import Path

  from quant_allocator.site.build import BuildError, build


  def main(argv: list[str] | None = None) -> None:
      parser = argparse.ArgumentParser(prog="python -m quant_allocator.site")
      subparsers = parser.add_subparsers(dest="command", required=True)

      build_parser = subparsers.add_parser("build", help="Render the static site")
      build_parser.add_argument("--site-dir", type=Path, default=Path("site"))
      build_parser.add_argument("--out", type=Path, default=Path("site/_build"))

      args = parser.parse_args(argv)

      if args.command == "build":
          try:
              build(args.site_dir, args.out)
          except BuildError as error:
              parser.exit(status=2, message=f"build failed: {error}\n")


  if __name__ == "__main__":
      main()
  ```

- [ ] **Step 4: Run the tests and watch them pass.**
  ```bash
  uv run pytest tests/site/test_cli.py -q
  ```
  Expected: `2 passed`.

- [ ] **Step 5: Sanity-run the CLI against the real tree.**
  ```bash
  uv run python -m quant_allocator.site build --out /tmp/qa-site-build
  ls /tmp/qa-site-build
  ```
  Expected: exit 0; listing shows `assets  e1.html  index.html  specs`.

- [ ] **Step 6: Commit.**
  ```bash
  uv run ruff check src/quant_allocator/site tests/site
  git add -A && git commit -m "feat: builder CLI and import-isolation guarantee"
  ```
  Expected: `All checks passed!`; commit succeeds.

---

## Task 8: CI workflow and repo furniture (README, LICENSE)

**Files:**
- Create: `.github/workflows/pages.yml`
- Create: `README.md` (overwrites the existing minimal readme, if any)
- Create: `LICENSE`
- Test: `tests/site/test_repo_furniture.py`

**Interfaces:**
- Consumes: the built site (`site/_build`).
- Produces: a Pages deploy workflow and portfolio-grade landing files.

- [ ] **Step 1: Create the GitHub Pages workflow.**
  Create `.github/workflows/pages.yml`:
  ```yaml
  name: Deploy gallery to GitHub Pages

  on:
    push:
      branches: [main]

  permissions:
    contents: read
    pages: write
    id-token: write

  concurrency:
    group: pages
    cancel-in-progress: true

  jobs:
    build-and-deploy:
      runs-on: ubuntu-latest
      environment:
        name: github-pages
        url: ${{ steps.deployment.outputs.page_url }}
      steps:
        - uses: actions/checkout@v4
        - uses: actions/setup-python@v5
          with:
            python-version: "3.12"
        - name: Install template dependencies only
          run: |
            pip install -e . --no-deps
            pip install jinja2 markdown pyyaml
        - name: Build the site
          run: python -m quant_allocator.site build
        - uses: actions/configure-pages@v5
        - uses: actions/upload-pages-artifact@v3
          with:
            path: site/_build
        - id: deployment
          uses: actions/deploy-pages@v4
  ```

- [ ] **Step 2: Create the README (portfolio landing page).**
  Create `README.md`:
  ```markdown
  # Quant Allocator

  A research portfolio of allocator-side analytics for hedge-fund manager
  selection, monitoring, and engagement — built on a synthetic-manager simulator
  and public data only. The gallery presents each idea as an honest mockup: what
  the analytic claims, what data tier it needs, and the statistical reason the
  ask exists.

  **Thesis:** Every analytic here is an exercise in inference under partial
  transparency.

  ## Gallery

  <!-- set after Pages enablement -->
  Live gallery: `https://USERNAME.github.io/quant-allocator/`

  ## Repository map

  - `site/` — the static gallery: card manifest (`cards.yaml`), Jinja2 templates,
    Interval design-system assets, vendored KaTeX, and committed demo data.
  - `src/quant_allocator/site/` — the render-only builder (`build.py`, CLI).
  - `src/quant_allocator/simulator/`, `.../adapters/` — the synthetic-manager
    simulator and public-data adapters that produce the numbers.
  - `docs/ideas/`, `docs/superpowers/` — idea cards, design specs, and plans.
  - `tools/` — publication-readiness scanning.

  ## Data policy

  All data on this site is synthetic or public. No employer-internal facts and no
  real manager names appear anywhere in this repository.

  ## License

  MIT — see `LICENSE`.
  ```

- [ ] **Step 3: Create the LICENSE (MIT).**
  Create `LICENSE`:
  ```text
  MIT License

  Copyright (c) 2026 Joon Kang

  Permission is hereby granted, free of charge, to any person obtaining a copy
  of this software and associated documentation files (the "Software"), to deal
  in the Software without restriction, including without limitation the rights
  to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
  copies of the Software, and to permit persons to whom the Software is
  furnished to do so, subject to the following conditions:

  The above copyright notice and this permission notice shall be included in all
  copies or substantial portions of the Software.

  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
  IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
  FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
  AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
  LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
  OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
  SOFTWARE.
  ```

- [ ] **Step 4: Write and run the furniture test.**
  Create `tests/site/test_repo_furniture.py`:
  ```python
  from pathlib import Path

  import yaml

  REPO_ROOT = Path(__file__).resolve().parents[2]


  def test_pages_workflow_is_valid_yaml():
      workflow = yaml.safe_load(
          (REPO_ROOT / ".github" / "workflows" / "pages.yml").read_text(encoding="utf-8")
      )
      assert "jobs" in workflow
      assert workflow["jobs"]["build-and-deploy"]["runs-on"] == "ubuntu-latest"


  def test_readme_states_thesis_and_data_policy():
      readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
      assert "inference under partial transparency" in readme
      assert "All data on this site is synthetic or public." in readme


  def test_license_is_mit():
      assert "MIT License" in (REPO_ROOT / "LICENSE").read_text(encoding="utf-8")
  ```
  Run:
  ```bash
  uv run pytest tests/site/test_repo_furniture.py -q
  ```
  Expected: `3 passed`.

- [ ] **Step 5: Commit.**
  ```bash
  uv run ruff check tests/site
  git add -A && git commit -m "chore: Pages workflow, portfolio README, and MIT license"
  ```
  Expected: `All checks passed!`; commit succeeds.

---

## Task 9: Publication-readiness scan and publishing runbook

**Files:**
- Create: `tools/publication_check.sh`
- Create: `docs/PUBLISHING.md`
- Test: `tests/site/test_publication_check.py`

**Interfaces:**
- Consumes: the working tree and full git history.
- Produces: a report-only scan (always exits 0) plus the manual publishing runbook.

- [ ] **Step 1: Write the failing scan test.**
  Create `tests/site/test_publication_check.py`:
  ```python
  import subprocess

  from pathlib import Path

  REPO_ROOT = Path(__file__).resolve().parents[2]


  def test_publication_check_runs_and_reports():
      result = subprocess.run(
          ["bash", "tools/publication_check.sh"],
          cwd=REPO_ROOT,
          capture_output=True,
          text=True,
      )
      assert result.returncode == 0
      assert "Publication readiness scan" in result.stdout
      assert "Scan complete." in result.stdout
  ```

- [ ] **Step 2: Run the test and watch it fail.**
  ```bash
  uv run pytest tests/site/test_publication_check.py -q
  ```
  Expected: failure — `bash: tools/publication_check.sh: No such file or directory`, so `bash` exits non-zero and the `returncode == 0` assertion fails.

- [ ] **Step 3: Create the report-only scan script.**
  Create `tools/publication_check.sh` (the committed term list contains only generic provenance markers; sensitive names are added locally in the gitignored `tools/.publication_terms` so they never enter the public repo):
  ```bash
  #!/usr/bin/env bash
  # Publication-readiness scan (REPORT ONLY).
  #
  # A HUMAN reviews every hit and decides — this script never blocks, never
  # rewrites history, and always exits 0.
  #
  # The committed TERMS below are GENERIC provenance markers only. Employer or
  # manager names must NEVER be committed to this public repo; add them to the
  # gitignored file tools/.publication_terms (one term per line, '#' comments
  # allowed) before running the scan locally.
  set -u

  TERMS=(
    "CONFIDENTIAL"
    "INTERNAL USE ONLY"
    "DO NOT DISTRIBUTE"
    "PROPRIETARY"
  )

  LOCAL_TERMS_FILE="$(dirname "$0")/.publication_terms"
  if [[ -f "$LOCAL_TERMS_FILE" ]]; then
    while IFS= read -r line; do
      [[ -n "$line" && "$line" != \#* ]] && TERMS+=("$line")
    done < "$LOCAL_TERMS_FILE"
  fi

  echo "== Publication readiness scan =="
  echo "Terms scanned: ${#TERMS[@]} (generic markers + any local terms)"
  echo

  for term in "${TERMS[@]}"; do
    echo "--- term: ${term} ---"
    echo "[working tree]"
    grep -rniI --exclude-dir=.git --exclude-dir=.venv \
      --exclude-dir=__pycache__ --exclude-dir=_build -- "$term" . \
      || echo "  (no working-tree hits)"
    echo "[git history]"
    git log --all -p -S "$term" 2>/dev/null | grep -i -- "$term" \
      || echo "  (no history hits)"
    echo
  done

  echo "Scan complete. A human must review every hit above before publishing."
  exit 0
  ```
  Make it executable:
  ```bash
  chmod +x tools/publication_check.sh
  ```

- [ ] **Step 4: Run the test and watch it pass.**
  ```bash
  uv run pytest tests/site/test_publication_check.py -q
  ```
  Expected: `1 passed`.

- [ ] **Step 5: Create the publishing runbook.**
  Create `docs/PUBLISHING.md`:
  ```markdown
  # Publishing runbook (manual, last)

  Publication is deliberate and human-gated. Do not automate these steps.

  1. **Populate local sensitive terms.** Create `tools/.publication_terms`
     (gitignored) with any employer or manager names to scan for, one per line.
     This file is never committed.

  2. **Run the readiness scan and review every hit.**
     ```bash
     bash tools/publication_check.sh | less
     ```
     The scan is report-only. Joon reviews all working-tree and git-history hits
     and decides whether any history rewrite is required before the repo goes
     public. Nothing proceeds until this review is done.

  3. **Create the public repository and push.**
     ```bash
     gh repo create quant-allocator --public --source=. --push
     ```

  4. **Enable GitHub Pages.** In the new repo: Settings → Pages → Source:
     "GitHub Actions". The `pages.yml` workflow runs on push to `main`.

  5. **Verify the workflow.** Confirm the "Deploy gallery to GitHub Pages" run
     succeeds and the published gallery renders (index, `e1.html`, `specs/e1.html`).

  6. **Set the gallery URL in the README.** Replace the
     `<!-- set after Pages enablement -->` placeholder and the `USERNAME`
     gallery URL with the real Pages URL, then commit.
  ```

- [ ] **Step 6: Full-suite green check and commit.**
  ```bash
  uv run pytest -q && uv run ruff check src/quant_allocator tests
  git add -A && git commit -m "chore: publication-readiness scan and publishing runbook"
  ```
  Expected: entire suite passes; `All checks passed!`; commit succeeds.

---

## Final verification (after Task 9)

- [ ] **Whole-suite green:** `uv run pytest -q` → all tests pass (existing adapter/simulator tests plus the new `tests/site/` suite).
- [ ] **Ruff clean:** `uv run ruff check .` → `All checks passed!`.
- [ ] **Real build succeeds end-to-end:** `uv run python -m quant_allocator.site build --out /tmp/qa-final && ls /tmp/qa-final /tmp/qa-final/specs` → shows `index.html`, `e1.html`, `assets/`, `specs/e1.html`.
- [ ] **Import isolation holds:** the CLI build never imports numpy/pandas (Task 7 test enforces this).
- [ ] **Plan-B boundary respected:** no demo-data generators, no s1/s2/x1/x2/m5 pages, and no method-spec authoring beyond the E1 stub were added.
