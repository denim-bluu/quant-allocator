import json
import shutil
import subprocess
from html.parser import HTMLParser
from pathlib import Path

import yaml

from quant_allocator.site.build import build

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_publication_terms() -> tuple[str, ...]:
    # Source banned terms from the gitignored canary instead of inlining them
    # in committed test source. Parsed like tools/publication_check.sh: one term
    # per line, '#' comments and blanks skipped, lowercased. Skip-if-missing:
    # canary is absent from worktrees/CI so this returns () there;
    # tools/publication_check.sh is the enforcing gate.
    canary = Path(__file__).resolve().parents[2] / "tools" / ".publication_terms"
    if not canary.exists():
        return ()
    terms = []
    for line in canary.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            terms.append(line.lower())
    return tuple(terms)


_BANNED = _load_publication_terms()


class _HorizonAttrs(HTMLParser):
    def __init__(self):
        super().__init__()
        self.values = []

    def handle_starttag(self, tag, attrs):
        for key, value in attrs:
            if key == "data-horizons":
                self.values.append(value)

# The exact fields the integration task will paste into cards.yaml to flip S4 live.
_CARD = {
    "id": "s4",
    "title": "Sell-discipline diagnostic",
    "lane": "S",
    "one_liner": "Where the edge leaks — exit timing vs a random-sell counterfactual.",
    "decisions": ["engage", "monitor"],
    "tiers": ["P", "E"],
    "status": "live",
    "demo": "pages/s4-sell.html.j2",
    "data": "s4_sell.json",
    "spec": "s4-sell-discipline.md",
    "golive": {
        "data_ask": (
            "Tier P — transaction history or monthly holdings with exit dates and "
            "security identifiers, plus a factor/risk model for residualization"
        ),
        "sample": (
            "150 exits minimum for the headline gap (~270 bp/exit leaks); ~1,900 exits "
            "for field-size effects; a 30-name low-turnover book never clears"
        ),
        "effort": "M",
    },
}


def _build(tmp_path):
    site = tmp_path / "site"
    shutil.copytree(REPO_ROOT / "site" / "templates", site / "templates")
    shutil.copytree(REPO_ROOT / "site" / "assets", site / "assets")
    (site / "data").mkdir()
    shutil.copy(REPO_ROOT / "site" / "data" / "s4_sell.json", site / "data" / "s4_sell.json")
    specs = tmp_path / "docs" / "ideas" / "specs"
    specs.mkdir(parents=True)
    shutil.copy(
        REPO_ROOT / "docs" / "ideas" / "specs" / "s4-sell-discipline.md",
        specs / "s4-sell-discipline.md",
    )
    (site / "cards.yaml").write_text(yaml.safe_dump([_CARD]), encoding="utf-8")
    build(site, tmp_path / "out", allow_legacy=True)
    return (tmp_path / "out" / "s4.html").read_text(encoding="utf-8"), tmp_path / "out"


def test_provenance_and_page_css(tmp_path):
    html, out = _build(tmp_path)
    assert "synthetic-badge" in html
    assert "SYNTHETIC DATA" in html
    assert "golive-box" in html
    assert 'id="card-data"' in html
    assert "specs/s4.html" in html
    assert "assets/pages/s4.css" in html
    assert (out / "assets" / "pages" / "s4.css").exists()
    assert "assets/s4-sell.js" in html
    assert (out / "assets" / "s4-sell.js").exists()
    assert "What this exhibit shows" in html
    assert "What you are looking at" in html
    assert "How to read it" in html


def test_two_manager_split_and_ghost(tmp_path):
    html, _ = _build(tmp_path)
    assert "Larkspur Ridge Partners" in html
    assert "Redgate Harbor Capital" in html
    assert "culls well" in html
    assert "edge leaks at the exit" in html
    assert "the diagnostic auditing itself" in html
    # Gap rails as IntervalStats with a zero reference (no bare points).
    assert html.count('data-domain="gap"') >= 3
    assert "interval-stat__zero" in html


def test_sign_convention_and_demo_live_disclosure(tmp_path):
    html, _ = _build(tmp_path)
    # Sign convention stated cold (spec §5 / gate-ruled copy).
    assert "positive gap = the sold names beat the book = the exits leak" in html
    # Mandatory demo-vs-live disclosure (spec §8.3, test-pinned).
    assert "ground-truth" in html
    assert "teaching-scale" in html
    assert "order\n" not in html  # sanity: sentence not truncated; see full-string check next
    assert "the measured field effect in the literature is an order\n      of magnitude smaller" in html \
        or "an order of magnitude smaller" in html


def test_horizon_slider_and_curve(tmp_path):
    html, _ = _build(tmp_path)
    assert 'id="s4-horizon"' in html
    assert 'class="s4-slider__range"' in html
    assert "s4-curve" in html
    assert "Forward horizon" in html
    parser = _HorizonAttrs()
    parser.feed(html)
    assert len(parser.values) == 5
    for value in parser.values:
        states = json.loads(value)
        assert [state["horizon"] for state in states] == [1, 2, 3, 4, 5, 6]
    assert 'data-horizons="[{&#34;' in html


def test_horizon_slider_keeps_a_minimum_touch_target():
    css = (REPO_ROOT / "site" / "assets" / "interval.css").read_text(encoding="utf-8")
    range_rule = css.split(".s4-slider__range {", 1)[1].split("}", 1)[0]
    assert "min-width: 44px" in range_rule
    assert "min-height: 44px" in range_rule


def test_horizon_control_updates_text_attributes_paths_and_rails(tmp_path):
    html, out = _build(tmp_path)
    assert 'data-horizon-value="point"' in html
    assert 'data-horizon-value="range"' in html
    assert 'data-horizon-value="exits"' in html
    assert "quarterly toggle" not in html
    assert "tier tabs" not in html
    script_path = out / "assets" / "s4-sell.js"
    harness = r"""
const fs = require("fs"), vm = require("vm");
function element(dataset) {
  return {dataset: dataset || {}, style: {}, attrs: {}, children: [], textContent: "",
    setAttribute(k, v) { this.attrs[k] = String(v); },
    appendChild(child) { this.children.push(child); return child; },
    removeChild(child) { this.children.splice(this.children.indexOf(child), 1); },
    get firstChild() { return this.children.length ? this.children[0] : null; }};
}
const states = Array.from({length: 6}, (_, i) => {
  const h = i + 1, gap = h / 1000;
  return {horizon: h, gap, ci_lo: gap - 0.0002, ci_hi: gap + 0.0003, n_exits: h * 10};
});
const band = element(), point = element(), zero = element();
const value = element(), range = element(), exits = element();
const rail = element({horizons: JSON.stringify(states), zero: "0", lo: "0.0008",
  point: "0.001", hi: "0.0013", nExits: "10"});
rail.querySelector = selector => ({
  ".interval-stat__band": band, ".interval-stat__point": point,
  ".interval-stat__zero": zero, '[data-horizon-value="point"]': value,
  '[data-horizon-value="range"]': range, '[data-horizon-value="exits"]': exits
}[selector]);
const svg = element();
const figure = element({horizons: JSON.stringify(states)});
figure.querySelector = selector => selector === ".s4-curve__svg" ? svg : null;
let listener = null;
const slider = {value: "1", addEventListener(name, fn) { if (name === "input") listener = fn; }};
const output = element();
global.document = {
  readyState: "complete",
  createElementNS() { return element(); },
  getElementById(id) { return id === "s4-horizon" ? slider : null; },
  querySelector(selector) { return selector === ".s4-slider__out" ? output : null; },
  querySelectorAll(selector) {
    if (selector === '.interval-stat[data-domain="gap"]') return [rail];
    if (selector === ".s4-curve") return [figure];
    return [];
  }
};
vm.runInThisContext(fs.readFileSync(process.argv[1], "utf8"));
if (!listener) throw new Error("horizon input listener was not registered");
const domainMax = states[5].ci_hi;
const paths = [];
for (const state of states) {
  slider.value = String(state.horizon); listener();
  const expectedLeft = state.ci_lo / domainMax * 100;
  const expectedWidth = (state.ci_hi - state.ci_lo) / domainMax * 100;
  const expectedPoint = state.gap / domainMax * 100;
  const polygon = svg.children.find(child => child.attrs.class === "s4-curve__band");
  const polyline = svg.children.find(child => child.attrs.class === "s4-curve__line");
  const checks = [
    output.textContent === String(state.horizon),
    rail.dataset.lo === String(state.ci_lo), rail.dataset.point === String(state.gap),
    rail.dataset.hi === String(state.ci_hi), rail.dataset.nExits === String(state.n_exits),
    value.textContent === "+" + (state.gap * 10000).toFixed(0) + " bp",
    range.textContent.includes((state.ci_lo * 10000).toFixed(0)),
    range.textContent.includes((state.ci_hi * 10000).toFixed(0)),
    exits.textContent === state.n_exits + " exits",
    Math.abs(parseFloat(band.style.left) - expectedLeft) < 1e-9,
    Math.abs(parseFloat(band.style.width) - expectedWidth) < 1e-9,
    Math.abs(parseFloat(point.style.left) - expectedPoint) < 1e-9,
    svg.children.length === 3,
    polygon.attrs.points.trim().split(/\s+/).length === state.horizon * 2,
    polyline.attrs.points.trim().split(/\s+/).length === state.horizon
  ];
  if (checks.some(result => !result)) { console.error(state, checks); process.exit(1); }
  paths.push(polyline.attrs.points);
}
if (new Set(paths).size !== 6) throw new Error("curve path did not change at every horizon");
"""
    result = subprocess.run(
        ["node", "-e", harness, str(script_path)],
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def test_quarterly_trend_refused_with_arithmetic(tmp_path):
    html, _ = _build(tmp_path)
    assert "power-gate" in html
    assert "Quarterly trend refused" in html
    assert "exits/quarter" in html
    assert "standard error" in html


def test_focal_gap_precedes_guide_and_copy_uses_reader_labels(tmp_path):
    html, _ = _build(tmp_path)
    assert html.index('class="s4-panel"') < html.index('class="s4-exhibit"')
    assert "S4 asks" not in html
    assert "S4 falls back" not in html
    assert "false-discovery-rate (FDR)" in html
    assert "partial pooling" in html
    assert "design effect" in html
    assert "deff " not in html
    for label in ("Positions and trades", "Exposure summaries", "Returns only"):
        assert label in html
    for tier in ("P", "E", "R"):
        assert f'data-tier="{tier}">{tier}</span>' not in html


def test_tier_tabs_and_roster_not_fdr(tmp_path):
    html, _ = _build(tmp_path)
    assert "cannot be inferred from monthly returns" in html   # R-tier refusal
    assert "exit-behavior hint, not a measurement" in html      # E-tier hint
    # roster is not an FDR screen (pinned full phrase, not bare "not"/"FDR" substrings)
    assert (
        "stabilized across small samples, <strong>not</strong> a\n"
        "    false-discovery-rate (FDR) screen for lucky alpha estimates."
    ) in html
    # trend is descriptive, not a persistence test (pinned full phrase)
    assert "within-manager series with intervals — not a\n    persistence test" in html


def test_golive_box_values(tmp_path):
    html, _ = _build(tmp_path)
    assert "transaction history or monthly holdings" in html
    assert "150 exits minimum" in html


def test_no_banned_words(tmp_path):
    html, _ = _build(tmp_path)
    lowered = html.lower()
    for banned in _BANNED:
        assert banned not in lowered
