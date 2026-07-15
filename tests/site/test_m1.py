import shutil
from html.parser import HTMLParser

import yaml

from quant_allocator.site.build import build


class _VisibleText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
        self.hidden = 0

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style", "template"}:
            self.hidden += 1

    def handle_endtag(self, tag):
        if tag in {"script", "style", "template"} and self.hidden:
            self.hidden -= 1

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data)


def _visible_text(html):
    parser = _VisibleText()
    parser.feed(html)
    return " ".join(" ".join(parser.parts).split())


def _page_content(html):
    start = html.index('<section class="m1-intro">')
    end = html.index('<details class="evidence-appendix">', start)
    return html[start:end]

M1_LIVE = {
    "status": "live",
    "demo": "pages/m1-drift.html.j2",
    "data": "m1_drift.json",
    "spec": "m1-exposure-drift-monitor.md",
    "golive": {
        "data_ask": "Exposure summaries (E) + stated bands; + positions (P); R rolling-beta needs returns + a factor set",
        "sample": "n/a per-window — measurement exact at any T; the alarm renders only where the X1 registry says the detector clears",
        "effort": "S–M (incl. the null-calibration harness and the net-beta-drift dial)",
    },
}


def _build_with_m1_live(tmp_path):
    repo_root = __import__("pathlib").Path(__file__).resolve().parents[2]
    tmp_site = tmp_path / "site"
    shutil.copytree(repo_root / "site", tmp_site)
    # build() validates every live card's spec file at site_dir.parent/docs/ideas/specs,
    # so the tmp tree needs the specs and public articles beside the copied site dir.
    shutil.copytree(repo_root / "docs" / "ideas" / "specs", tmp_path / "docs" / "ideas" / "specs")
    shutil.copytree(
        repo_root / "docs" / "ideas" / "articles",
        tmp_path / "docs" / "ideas" / "articles",
    )
    cards = yaml.safe_load((tmp_site / "cards.yaml").read_text(encoding="utf-8"))
    for card in cards:
        if card["id"] == "m1":
            card.clear()
            card.update({"id": "m1", "title": "Exposure hygiene & drift monitor", "lane": "M",
                         "one_liner": "Does the book respect its stated bands, or is drift creeping in?",
                         "decisions": ["monitor", "engage"], "tiers": ["E", "P", "R"], **M1_LIVE})
    (tmp_site / "cards.yaml").write_text(yaml.safe_dump(cards, sort_keys=False, allow_unicode=True), encoding="utf-8")
    out = tmp_path / "out"
    build(tmp_site, out, allow_legacy=True)
    return (out / "m1.html").read_text(encoding="utf-8"), out


def test_m1_provenance_and_components(tmp_path):
    html, out = _build_with_m1_live(tmp_path)
    assert "synthetic-badge" in html            # SYNTHETIC badge from demo.html.j2
    assert "SYNTHETIC DATA" in html
    assert "golive-box" in html
    assert 'id="card-data"' in html
    assert (out / "specs" / "m1.html").exists()
    assert "assets/pages/m1.css" in html        # page CSS wired via head_extra
    assert (out / "assets" / "pages" / "m1.css").exists()
    assert "assets/m1-drift.js" in html
    assert (out / "assets" / "m1-drift.js").exists()


def test_m1_measurement_vs_calibrated_rule_copy(tmp_path):
    # Spec verdict-split ruling: measurement is Robust; the alarm is a CALIBRATED RULE.
    html, _ = _build_with_m1_live(tmp_path)
    assert "calibrated rule" in html
    assert "autocorrelated" in html             # the null-calibration point (§3.4)
    assert 'class="tier-badge" data-tier="E"' in html


def test_m1_chart_precedes_guide_and_defines_cusum(tmp_path):
    html, _ = _build_with_m1_live(tmp_path)
    content = _page_content(html)
    assert content.index('class="m1-drift-chart"') < content.index('class="m1-guide"')
    assert "cumulative sum (CUSUM)" in _visible_text(content)
    assert "running total of sustained deviations" in _visible_text(content)


def test_m1_public_copy_uses_reader_facing_evidence_terms(tmp_path):
    html, _ = _build_with_m1_live(tmp_path)
    visible = _visible_text(_page_content(html))
    for prohibited in (
        "E detection",
        "R detection",
        "E measures",
        "R only infers",
        "power gate",
        "0.50 floor",
        "T=",
        "X1",
    ):
        assert prohibited not in visible
    assert "Exposure-summary detection" in visible
    assert "Returns-only detection" in visible


def test_m1_tier_degradation_and_noise_chip(tmp_path):
    # R rung is descriptive-only behind a noise chip; E and R detection shown as intervals.
    html, _ = _build_with_m1_live(tmp_path)
    assert 'data-verdict="noise"' in html
    assert "no drift verdict at this track length" in html
    assert "Wilson 95%" in html                 # detection intervals, no bare rate
    assert html.count('class="interval-stat"') >= 3   # E det, R det, factor-share slope


def test_m1_factor_share_is_estimate_bearing(tmp_path):
    # spec §3.5 ruling: factor share ships as a slope interval + verdict, not pure measurement.
    html, _ = _build_with_m1_live(tmp_path)
    assert "Factor-share slope" in html
    assert "95% interval" in html


def test_m1_power_gate_renders_operating_characteristics(tmp_path):
    html, _ = _build_with_m1_live(tmp_path)
    assert 'class="power-gate"' in html
    assert "false-alarm budget" in html
    assert "manager-year" in html


def test_m1_gallery_explainer_present(tmp_path):
    # Editorial explainer block near the top of the exhibit.
    html, _ = _build_with_m1_live(tmp_path)
    assert "What this exhibit shows" in html


def test_m1_decision_adjacent_synthetic_boundary(tmp_path):
    html, _ = _build_with_m1_live(tmp_path)
    bridge = html.split('href="specs/m1.html"', 1)[0].rsplit('<p class="m1-note">', 1)[1]
    assert "calibrated synthetic path" in bridge
    assert "mechanism" in bridge
    assert "does not establish" in bridge
    assert "live manager" in bridge
