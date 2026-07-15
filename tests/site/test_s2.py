from pathlib import Path

from quant_allocator.site.build import build

REPO_ROOT = Path(__file__).resolve().parents[2]
PUBLIC_ARTICLE = REPO_ROOT / "docs" / "ideas" / "articles" / (
    "s2-uncertainty-honest-tear-sheet.md"
)
METHOD_SPEC = REPO_ROOT / "docs" / "ideas" / "specs" / "s2-tear-sheet-engine.md"


def _build(tmp_path):
    out = tmp_path / "out"
    build(REPO_ROOT / "site", out)
    return (out / "s2.html").read_text(encoding="utf-8"), out


def test_s2_provenance_and_copy(tmp_path):
    html, out = _build(tmp_path)
    text = " ".join(html.split())
    # Provenance furniture from demo.html.j2.
    assert "synthetic-badge" in html
    assert "SYNTHETIC DATA" in html
    assert "golive-box" in html
    assert 'id="card-data"' in html
    assert "specs/s2.html" in html
    assert (out / "specs" / "s2.html").exists()
    # Gallery explainer section present.
    assert "What this exhibit shows" in html
    # numerics gate copy obligations (verbatim band labels).
    assert "95% interval" in html   # both Sharpe stats
    assert "90% interval" in html   # alpha stat
    assert "pointwise" in html      # drawdown null envelope
    # rf_annual labeled synthetic.
    assert "2.0%" in html
    assert "(synthetic)" in html
    assert "Decision:" in html
    assert "controlled synthetic example" in html
    assert "Manipulation-proof performance measure (MPPM)" in html
    assert "does not establish external calibration" in text


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


def test_s2_reader_first_exhibit_order_and_collapsed_evidence(tmp_path):
    html, _ = _build(tmp_path)

    markers = (
        'id="s2-decision-takeaway"',
        'id="s2-focal-comparison"',
        'class="tearsheet-panel tearsheet-further-analysis"',
        '<details class="evidence-appendix">',
    )
    positions = [html.index(marker) for marker in markers]
    assert positions == sorted(positions)

    lead = html.split('<div class="tearsheet-lead">', 1)[1].split("</div>", 1)[0]
    assert "returns-only evidence" in lead
    assert "tier R" not in lead

    appendix = html.split('<details class="evidence-appendix">', 1)[1].split(
        "</details>", 1
    )[0]
    assert "<summary>Evidence and readiness</summary>" in appendix
    assert 'class="card-context"' in appendix
    assert "Primary stage" in appendix
    assert "Minimum data" in appendix
    assert "Validation" in appendix
    assert "Methodology" in appendix
    assert "golive-box" in appendix


def test_s2_focal_and_time_series_visuals_are_labeled_and_interpreted(tmp_path):
    html, out = _build(tmp_path)

    assert '<figure class="tearsheet-focal"' in html
    assert 'aria-labelledby="s2-focal-title"' in html
    assert "Shared Sharpe scale" in html
    assert html.count('class="interval-stat__scale"') >= 2
    assert html.count('class="interval-stat__zero-label"') >= 2

    assert 'aria-labelledby="s2-drawdown-title s2-drawdown-caption"' in html
    assert "Drawdown (%)" in html
    assert "Month 1" in html
    assert "Month 48" in html
    assert "Realized drawdown" in html
    assert "99th-percentile envelope" in html

    assert 'aria-labelledby="s2-returns-title s2-returns-caption"' in html
    assert "Monthly net return (%)" in html
    assert "What it changes" in html
    assert "What remains uncertain" in html

    assert "assets/pages/s2.css?v=editorial-v8" in html
    assert (out / "assets" / "pages" / "s2.css").is_file()


def test_s2_focal_labels_remain_legible_on_mobile():
    css = (REPO_ROOT / "site" / "assets" / "pages" / "s2.css").read_text(
        encoding="utf-8"
    )
    for selector in (
        ".tearsheet-eyebrow",
        ".tearsheet-focal .interval-stat__label",
        ".interval-stat__scale",
        ".tearsheet-chart__y-axis",
        ".tearsheet-chart__x-axis",
    ):
        rule = css.split(f"{selector} {{", 1)[1].split("}", 1)[0]
        assert "font-size: 0.75rem" in rule


def test_s2_script_loaded(tmp_path):
    html, out = _build(tmp_path)
    assert "assets/s2-tearsheet.js" in html
    assert (out / "assets" / "s2-tearsheet.js").exists()


def test_s2_spec_has_reproduction_map(tmp_path):
    source = METHOD_SPEC.read_text(encoding="utf-8")
    assert "Displayed field" in source
    assert "JSON field" in source
    assert "s2_tearsheet.py" in source
    assert "test_s2_tearsheet.py" in source


def test_s2_public_article_has_reader_sequence_and_separate_method_link(tmp_path):
    _, out = _build(tmp_path)
    html = (out / "specs" / "s2.html").read_text(encoding="utf-8")

    assert PUBLIC_ARTICLE.is_file()
    source = PUBLIC_ARTICLE.read_text(encoding="utf-8")
    headings = (
        "## The decision",
        "## Why the obvious answer fails",
        "## The intuition",
        "## A small numerical example",
        "## The method",
        "## What the evidence changes",
        "## Limits and go-live",
        "## Key takeaways",
        "## References",
    )
    positions = [source.index(heading) for heading in headings]
    assert positions == sorted(positions)
    for internal in (
        "**Date:**",
        "**Status:**",
        "**Card:**",
        "**Demo:**",
        "Displayed field",
        "JSON field",
        "M3",
        "tier-E",
        "Tier R",
        "Tier E",
        "Tier P",
    ):
        assert internal not in source

    assert "simulation-calibrated drawdown alarm" in source.lower()
    lowered_source = source.lower()
    assert "returns-only data" in lowered_source
    assert "exposure summaries" in lowered_source
    assert "positions and trades" in lowered_source

    assert "Technical method and provenance" in html
    assert "Open the paired exhibit" in html
    assert "Foundation · Step 1 of 3" in html
    assert "12 min" in html
    assert "Intermediate" in html
    assert "On this page" in html
    assert "Next in this path" in html
    assert "Hierarchical Bayesian alpha engine" in html
    assert html.count("Open the paired exhibit") == 2
