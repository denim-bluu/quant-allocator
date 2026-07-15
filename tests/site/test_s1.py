import subprocess
from pathlib import Path

from quant_allocator.site.build import build

REPO_ROOT = Path(__file__).resolve().parents[2]
METHOD_SPEC = REPO_ROOT / "docs" / "ideas" / "specs" / "s1-bayesian-alpha-engine.md"


def test_s1_page_provenance_and_copy(tmp_path):
    out = tmp_path / "out"
    build(REPO_ROOT / "site", out)
    html = (out / "s1.html").read_text(encoding="utf-8")
    # Provenance furniture from demo.html.j2.
    assert "synthetic-badge" in html
    assert "SYNTHETIC DATA" in html
    assert "golive-box" in html
    # numerics gate copy obligation: every band labeled exactly "90% interval".
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


def test_s1_roster_has_one_shared_axis_and_zero_marker_on_every_rail(tmp_path):
    out = tmp_path / "out"
    build(REPO_ROOT / "site", out)
    html = (out / "s1.html").read_text(encoding="utf-8")

    assert html.count('class="ledger-shared-axis"') == 1
    assert "Shared annual alpha scale" in html
    assert "&minus;16.3%" in html
    assert "+37.9%" in html
    assert html.count('class="interval-stat__zero"') == 40


def test_s1_script_uses_one_domain_for_bands_axis_and_zero_markers():
    script_path = REPO_ROOT / "site" / "assets" / "s1-ledger.js"
    harness = r"""
const fs = require("fs"), vm = require("vm");
function node(dataset) {
  return {dataset: dataset || {}, style: {}, attrs: {}, textContent: "",
    setAttribute(k, v) { this.attrs[k] = String(v); }};
}
function stat(lo, point, hi) {
  const band = node(), mark = node(), zero = node();
  const value = node({lo: String(lo), point: String(point), hi: String(hi)});
  value.parts = {band, mark, zero};
  value.querySelector = selector => ({
    ".interval-stat__band": band,
    ".interval-stat__point": mark,
    ".interval-stat__zero": zero
  }[selector]);
  return value;
}
const stats = [stat(-0.25, -0.10, 0.20), stat(0.10, 0.30, 0.50)];
const axis = node();
axis.style.setProperty = (key, value) => { axis.style[key] = value; };
global.document = {
  readyState: "complete",
  querySelectorAll(selector) { return selector === ".ledger .interval-stat" ? stats : []; },
  querySelector(selector) { return selector === "[data-ledger-axis]" ? axis : null; }
};
vm.runInThisContext(fs.readFileSync(process.argv[1], "utf8"));
const expected = 100 / 3;
const zeroPositions = stats.map(item => parseFloat(item.parts.zero.style.left));
const checks = [
  zeroPositions.every(value => Math.abs(value - expected) < 1e-9),
  Math.abs(parseFloat(axis.style["--ledger-zero"]) - expected) < 1e-9,
  stats[0].parts.band.style.left === "0%",
  Math.abs(parseFloat(stats[1].parts.mark.style.left) - 73.33333333333333) < 1e-9
];
if (checks.some(value => !value)) { console.error(checks, stats, axis); process.exit(1); }
"""
    result = subprocess.run(
        ["node", "-e", harness, str(script_path)],
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def test_s1_and_m5_shared_buttons_keep_minimum_touch_targets():
    css = (REPO_ROOT / "site" / "assets" / "interval.css").read_text(encoding="utf-8")
    for selector in (".sort-toggle", ".saydo-focus"):
        rule = css.split(f"{selector} {{", 1)[1].split("}", 1)[0]
        assert "min-width: 44px" in rule
        assert "min-height: 44px" in rule


def test_s1_copy_is_shrinkage_not_true_skill_recovery(tmp_path):
    out = tmp_path / "out"
    build(REPO_ROOT / "site", out)
    html = (out / "s1.html").read_text(encoding="utf-8")
    text = " ".join(html.split())
    assert "7 of 20 managers change rank" in html
    assert "peer shrinkage" in html
    assert "does not prove better true-skill recovery" in html
    assert "Repeated-grid rank recovery and live calibration remain requirements" in text
    template = (REPO_ROOT / "site" / "templates" / "pages" / "s1-ledger.html.j2").read_text()
    for overclaim in ("skill, not luck", "separated from skill", "hire the lucky"):
        assert overclaim not in template


def test_s1_method_spec_has_reproduction_map():
    source = METHOD_SPEC.read_text(encoding="utf-8")
    assert "Displayed field" in source
    assert "JSON field" in source
    assert "s1_ledger.py" in source
    assert "test_s1_ledger.py" in source


def test_s1_page_script_loaded(tmp_path):
    out = tmp_path / "out"
    build(REPO_ROOT / "site", out)
    html = (out / "s1.html").read_text(encoding="utf-8")
    assert "assets/s1-ledger.js" in html
    assert (out / "assets" / "s1-ledger.js").exists()


def test_s1_page_has_exhibit_explainer(tmp_path):
    out = tmp_path / "out"
    build(REPO_ROOT / "site", out)
    html = (out / "s1.html").read_text(encoding="utf-8")
    assert "What this exhibit shows" in html


def test_s1_opens_with_three_focal_managers_before_the_full_roster(tmp_path):
    out = tmp_path / "out"
    build(REPO_ROOT / "site", out)
    html = (out / "s1.html").read_text(encoding="utf-8")

    assert html.count("data-focal-manager=") == 3
    for code in ("A10", "B10", "A07"):
        assert f'data-focal-manager="{code}"' in html
    focal = html.index('class="ledger-focal"')
    guide = html.index('class="exhibit-guide"')
    roster = html.index('<details class="ledger-roster">')
    assert focal < guide < roster
    assert "ordinary least squares (OLS)" in html
    assert 'class="ledger-row__id"' not in html
    for code in ("A10", "B10", "A07"):
        assert f'<p class="ledger-focal__code">{code}' not in html
    assert "Osprey Hollow Partners (A10)" not in html
    assert "Cinderbank Capital (B10)" not in html
    roster_html = html[roster:]
    assert "Explore all 20 managers" in roster_html
    assert roster_html.count('<article class="ledger-row') == 20
