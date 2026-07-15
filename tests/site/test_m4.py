import shutil
from html.parser import HTMLParser
from pathlib import Path

import yaml

from quant_allocator.site.build import build

REPO_ROOT = Path(__file__).resolve().parents[2]


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
    start = html.index('<section class="m4-intro">')
    end = html.index('<details class="evidence-appendix">', start)
    return html[start:end]


def _load_publication_terms():
    path = REPO_ROOT / "tools" / ".publication_terms"
    if not path.exists():
        return ()
    return tuple(
        line.strip().lower()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    )


_CARD = {
    "id": "m4",
    "title": "Crowding & overlap radar",
    "lane": "M",
    "one_liner": "Is our diversification illusory — are the managers the same trade?",
    "decisions": ["size", "monitor", "redeem"],
    "tiers": ["P", "E", "R"],
    "status": "live",
    "demo": "pages/m4-crowding.html.j2",
    "data": "m4_crowding.json",
    "spec": "m4-crowding-overlap-radar.md",
    "golive": {
        "data_ask": (
            "Position-level holdings aligned to a shared name universe, plus per-name "
            "dollar ADV and daily volatility; the public rung later consumes public "
            "filings through the shared adapter"
        ),
        "sample": (
            "None for the point-in-time measurement; predictive loss and any size-cap "
            "recommendation remain refused until atlas gate 2 clears"
        ),
        "effort": "M–L",
    },
}


def _build(tmp_path):
    site = tmp_path / "site"
    shutil.copytree(REPO_ROOT / "site" / "templates", site / "templates")
    shutil.copytree(REPO_ROOT / "site" / "assets", site / "assets")
    (site / "data").mkdir()
    shutil.copy(
        REPO_ROOT / "site" / "data" / "m4_crowding.json",
        site / "data" / "m4_crowding.json",
    )
    specs = tmp_path / "docs" / "ideas" / "specs"
    specs.mkdir(parents=True)
    shutil.copy(
        REPO_ROOT / "docs" / "ideas" / "specs" / "m4-crowding-overlap-radar.md",
        specs / "m4-crowding-overlap-radar.md",
    )
    (site / "cards.yaml").write_text(
        yaml.safe_dump([_CARD], sort_keys=False, allow_unicode=True), encoding="utf-8"
    )
    out = tmp_path / "out"
    build(site, out, allow_legacy=True)
    return (out / "m4.html").read_text(encoding="utf-8"), out


def test_page_furniture_assets_and_spec(tmp_path):
    html, out = _build(tmp_path)
    assert "SYNTHETIC DATA" in html
    assert 'id="card-data"' in html
    assert "golive-box" in html
    assert "What this exhibit shows" in html
    assert "What you are looking at" in html
    assert "How to read it" in html
    assert "specs/m4.html" in html
    assert (out / "specs" / "m4.html").exists()
    assert "assets/pages/m4.css" in html
    assert "assets/m4-crowding.js" in html
    assert (out / "assets" / "pages" / "m4.css").exists()
    assert (out / "assets" / "m4-crowding.js").exists()


def test_exact_snapshot_measurements_and_centerpiece(tmp_path):
    html, _ = _build(tmp_path)
    assert "Hollowmere Capital" in html
    assert "Brackenford Partners" in html
    assert html.count("exact for this snapshot; no sampling interval") == 3
    assert "Signed holdings-vector cosine" in html
    assert "not a return-correlation estimate" in html
    assert html.count('data-domain="overlap"') == 2
    assert 'data-domain="cosine"' in html
    assert '<span class="interval-stat__value" id="m4-cosine-value">0.327</span>' in html


def test_m4_heatmap_precedes_guide_and_uses_full_evidence_labels(tmp_path):
    html, _ = _build(tmp_path)
    content = _page_content(html)
    visible = _visible_text(content)
    assert content.index('id="m4-heatmap-title"') < content.index('class="m4-guide"')
    assert "Position holdings" in visible
    assert "Exposure summaries" in visible
    assert "Returns only" in visible
    for prohibited in (
        "P-tier",
        "gate 2",
        "gate 3",
        "M4 measures",
        "P1 may",
        "CTR coverage holes",
    ):
        assert prohibited not in visible


def test_pair_selector_updates_values_data_and_rail_geometry():
    script = (REPO_ROOT / "site" / "assets" / "m4-crowding.js").read_text(encoding="utf-8")
    assert "function updateStat" in script
    assert 'stat.dataset.lo = String(value)' in script
    assert 'stat.dataset.point = String(value)' in script
    assert 'stat.dataset.hi = String(value)' in script
    assert 'querySelector(".interval-stat__band")' in script
    assert 'querySelector(".interval-stat__point")' in script
    assert 'updateStat("m4-raw", data.heatmap.raw[i][j], "overlap")' in script
    assert 'updateStat("m4-cosine", data.heatmap.cosine[i][j], "cosine")' in script


def test_heatmap_and_stress_controls_are_accessible_and_precomputed(tmp_path):
    html, _ = _build(tmp_path)
    assert 'role="grid"' in html
    assert html.count('role="gridcell"') == 36
    assert html.count("liquidity-adjusted overlap") >= 36
    assert 'id="m4-stress-delta"' in html
    assert 'class="m4-slider__range"' in html
    assert 'id="m4-unwind-bars"' in html
    assert "illustrative impact" in html
    assert "illustrative &mdash; not a forecast" in html


def test_heatmap_cells_and_stress_slider_keep_minimum_touch_targets():
    css = (REPO_ROOT / "site" / "assets" / "pages" / "m4.css").read_text(encoding="utf-8")
    mobile = css.split("@media (max-width: 700px) {", 1)[1]
    cell_rule = mobile.split(".m4-cell {", 1)[1].split("}", 1)[0]
    range_rule = css.split(".m4-slider__range {", 1)[1].split("}", 1)[0]

    assert "min-width: 44px" in cell_rule
    assert "min-height: 44px" in cell_rule
    assert "min-width: 44px" in range_rule
    assert "min-height: 44px" in range_rule


def test_measurement_prediction_split_and_kill_rule(tmp_path):
    html, _ = _build(tmp_path)
    visible = _visible_text(_page_content(html))
    assert "Scenario, not forecast" in html
    assert "No predicted loss or size-cap" in html
    assert "If predictive validation fails, the measurement stays" in html
    assert "This exhibit measures crowding; it does not allocate" in html
    assert "never computes portfolio weights" in visible


def test_tier_limits_and_public_view_withheld(tmp_path):
    html, _ = _build(tmp_path)
    assert 'data-tier="P"' in html
    assert 'data-tier="E"' in html
    assert 'data-tier="R"' in html
    assert "Position holdings" in html
    assert "Exposure summaries" in html
    assert "Returns only" in html
    assert "Factor crowding only" in html
    assert "not a holdings measurement" in html
    assert "Public-filings view unavailable" in html
    assert "Form 13F" in html
    assert "45-day lag" in html
    assert "longs-only" in html
    assert "coverage gaps in the filing universe" in html
    assert "non-US blindness" in html


def test_golive_values_and_publication_terms(tmp_path):
    html, _ = _build(tmp_path)
    assert "Position-level holdings aligned to a shared name universe" in html
    assert "predictive loss and any size-cap" in html
    lowered = html.lower()
    for term in _load_publication_terms():
        assert term not in lowered
