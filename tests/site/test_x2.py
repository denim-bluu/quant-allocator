from pathlib import Path

import json
import shutil
import subprocess

from quant_allocator.site.build import build

REPO_ROOT = Path(__file__).resolve().parents[2]


def _build(tmp_path):
    out = tmp_path / "out"
    build(REPO_ROOT / "site", out)
    return (out / "x2.html").read_text(encoding="utf-8"), out


def _build_with_modified_cells(tmp_path):
    site = tmp_path / "site"
    shutil.copytree(REPO_ROOT / "site", site)
    shutil.copytree(REPO_ROOT / "docs" / "ideas" / "specs", tmp_path / "docs" / "ideas" / "specs")
    shutil.copytree(
        REPO_ROOT / "docs" / "ideas" / "articles",
        tmp_path / "docs" / "ideas" / "articles",
    )
    data_path = site / "data" / "x2_playground.json"
    data = json.loads(data_path.read_text(encoding="utf-8"))
    data["cells"]["0.04|12|0.8|48|R"]["alpha"][:3] = [0.061, -0.02, 0.13]
    data["cells"]["0.04|12|0.8|120|E"]["alpha"][:4] = [0.057, 0.004, 0.099, "robust"]
    data_path.write_text(json.dumps(data), encoding="utf-8")
    out = tmp_path / "out"
    build(site, out)
    return (out / "x2.html").read_text(encoding="utf-8")


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
    assert "synthetic teaching example, not a live manager product" in html
    assert "It remains synthetic" in html
    # Inlined JSON for the dials + spec link.
    assert 'id="card-data"' in html
    assert "specs/x2.html" in html
    assert (out / "specs" / "x2.html").exists()


def test_x2_dials_snap_values(tmp_path):
    html, _ = _build(tmp_path)
    for dial in ["ic", "half_life", "sizing", "T", "tier"]:
        assert 'data-dial="%s"' % dial in html
    # Snap-to-grid values present as button data-values (%g-formatted).
    assert 'data-value="0.04"' in html  # ic
    assert 'data-value="0.1"' in html  # ic
    assert 'data-value="36"' in html  # half_life or T
    assert 'data-value="0.8"' in html  # sizing
    assert 'data-value="120"' in html  # T
    assert 'data-value="R"' in html  # tier
    assert 'data-value="P"' in html


def test_x2_dials_have_named_groups_and_touch_targets(tmp_path):
    html, _ = _build(tmp_path)
    css = (REPO_ROOT / "site" / "assets" / "interval.css").read_text(encoding="utf-8")

    assert html.count('<fieldset class="x2-dial"') == 5
    assert html.count('<legend class="x2-dial__label">') == 5
    assert 'aria-label="Track length T (months): 120"' in html
    assert 'aria-label="Evidence available: Exposure summaries"' in html

    button_rule = css.split(".x2-dial__btn {", 1)[1].split("}", 1)[0]
    assert "min-width: 44px" in button_rule
    assert "min-height: 44px" in button_rule


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


def test_x2_exhibit_explainer(tmp_path):
    html, _ = _build(tmp_path)
    assert "What this exhibit shows" in html
    source = (REPO_ROOT / "site" / "templates" / "pages" / "x2-playground.html.j2").read_text()
    assert "Drag" not in source
    assert "drag" not in source


def test_x2_opening_and_comparison_follow_named_cells(tmp_path):
    html = _build_with_modified_cells(tmp_path)
    explainer = html.split('<section class="x2-exhibit"', 1)[1].split(
        '<section class="x2-controls"', 1
    )[0]
    for expected in (
        "0.061",
        "&minus;0.02000",
        "+0.1300",
        "0.057",
        "+0.004000",
        "+0.09900",
        "robust",
    ):
        assert expected in explainer
    for stale in ("0.053", "&minus;0.02951", "+0.1249", "0.0482", "+0.001816", "+0.09213"):
        assert stale not in explainer


def test_x2_leads_with_an_instructed_before_after_comparison(tmp_path):
    html, _ = _build(tmp_path)

    comparison = html.split('<section class="x2-before-after"', 1)[1].split(
        '<section class="x2-controls"', 1
    )[0]
    assert "Before · 48 months · Returns only" in comparison
    assert "After · 120 months · Exposure summaries" in comparison
    assert "What changed" in comparison
    assert "noise" in comparison
    assert "shrink" in comparison


def test_x2_uses_full_public_tier_labels_and_hides_internal_publication_terms(tmp_path):
    html, _ = _build(tmp_path)

    for label in ("Returns only", "Exposure summaries", "Positions and trades"):
        assert label in html
    for token in ('data-value="R"', 'data-value="E"', 'data-value="P"'):
        assert token in html
    for internal in (
        "X1 atlas",
        "committed JSON",
        "tier R",
        "tier E",
        "tier-P",
        "attestation ceiling",
    ):
        assert internal not in html


def test_x2_script_loaded(tmp_path):
    html, out = _build(tmp_path)
    assert "assets/x2-playground.js?v=editorial-v9" in html
    assert "assets/pages/x2.css?v=editorial-v9" in html
    assert (out / "assets" / "x2-playground.js").exists()


def test_x2_controls_announce_the_selected_precomputed_state(tmp_path):
    html, out = _build(tmp_path)
    script = (out / "assets" / "x2-playground.js").read_text(encoding="utf-8")

    assert 'data-x2-announcer' in html
    assert 'aria-live="polite"' in html
    assert "Showing " in script
    assert "Evidence available" not in script


def test_x2_interval_geometry_uses_one_committed_domain_per_analytic():
    script_path = REPO_ROOT / "site" / "assets" / "x2-playground.js"
    data_path = REPO_ROOT / "site" / "data" / "x2_playground.json"
    harness = r"""
const fs = require("fs"), vm = require("vm");
const data = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));

function node() {
  return {
    style: {}, textContent: "", attrs: {}, hidden: false,
    setAttribute(k, v) { this.attrs[k] = String(v); },
    getAttribute(k) { return this.attrs[k]; }
  };
}

const stat = node(), value = node(), range = node(), band = node(), mark = node();
const chip = node(), wilson = node(), reason = node();
const slot = node();
slot.attrs["data-analytic"] = "alpha";
slot.querySelector = selector => ({
  ".interval-stat": stat,
  ".interval-stat__value": value,
  ".interval-stat__range": range,
  ".interval-stat__band": band,
  ".interval-stat__point": mark,
  ".verdict-chip": chip,
  ".x2-wilson__value": wilson,
  ".power-gate__reason": reason
}[selector]);

let click = null;
const controls = node();
controls.attrs = {
  "data-default-ic": "0.04",
  "data-default-half_life": "12",
  "data-default-sizing": "0.8",
  "data-default-T": "24",
  "data-default-tier": "R"
};
controls.addEventListener = (name, fn) => { if (name === "click") click = fn; };

const group = node();
group.attrs["data-dial"] = "T";
const button24 = node(), button120 = node();
[button24, button120].forEach(button => {
  button.classList = {toggle() {}};
  button.closest = selector => selector === ".x2-dial__btn" ? button : group;
});
button24.attrs["data-value"] = "24";
button120.attrs["data-value"] = "120";
group.querySelectorAll = () => [button24, button120];

const cardData = node();
cardData.textContent = JSON.stringify(data);
global.document = {
  readyState: "complete",
  getElementById(id) { return id === "card-data" ? cardData : null; },
  querySelector(selector) {
    if (selector === "[data-dials]") return controls;
    if (selector === "[data-falsealarm]") return null;
    return null;
  },
  querySelectorAll(selector) {
    return selector === ".x2-analytic" ? [slot] : [];
  }
};

vm.runInThisContext(fs.readFileSync(process.argv[1], "utf8"));
if (!click) throw new Error("dial listener was not registered");

const values = [0];
Object.values(data.cells).forEach(cell => {
  if (cell.alpha) values.push(cell.alpha[0], cell.alpha[1], cell.alpha[2]);
});
const min = Math.min(...values), max = Math.max(...values), span = max - min;
const expected = months => {
  const arr = data.cells[`0.04|12|0.8|${months}|R`].alpha;
  return {
    left: (arr[1] - min) / span * 100,
    width: (arr[2] - arr[1]) / span * 100,
    point: (arr[0] - min) / span * 100
  };
};
const observed24 = {
  left: parseFloat(band.style.left),
  width: parseFloat(band.style.width),
  point: parseFloat(mark.style.left)
};
click({target: button120});
const observed120 = {
  left: parseFloat(band.style.left),
  width: parseFloat(band.style.width),
  point: parseFloat(mark.style.left)
};

for (const [observed, wanted] of [[observed24, expected(24)], [observed120, expected(120)]]) {
  for (const key of ["left", "width", "point"]) {
    if (Math.abs(observed[key] - wanted[key]) > 1e-9) {
      throw new Error(`${key}: observed ${observed[key]}, expected ${wanted[key]}`);
    }
  }
}
if (Math.abs(observed24.width - observed120.width) < 1) {
  throw new Error("24- and 120-month interval bands should be visibly different");
}
"""
    result = subprocess.run(
        ["node", "-e", harness, str(script_path), str(data_path)],
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
