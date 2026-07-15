import shutil
from html.parser import HTMLParser
from pathlib import Path

import yaml

from quant_allocator.site.build import build

REPO_ROOT = Path(__file__).resolve().parents[2]


class _VisibleText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.hidden = 0
        self.parts = []

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

_CARD = {
    "id": "s6",
    "title": "Returns-only sizing & decay signatures",
    "lane": "S",
    "one_liner": "Can monthly returns alone reveal sizing or decay? A pre-registered test.",
    "decisions": ["monitor", "select"],
    "tiers": ["R"],
    "status": "live",
    "demo": "pages/s6-signatures.html.j2",
    "data": "s6_signatures.json",
    "spec": "s6-returns-only-signatures.md",
    "golive": {
        "data_ask": "None — 100% simulator (tier R by construction)",
        "sample": "The pre-registered grid (500 managers per class per cell)",
        "effort": "M–L",
    },
}


def _build(tmp_path):
    site = tmp_path / "site"
    shutil.copytree(REPO_ROOT / "site" / "templates", site / "templates")
    shutil.copytree(REPO_ROOT / "site" / "assets", site / "assets")
    (site / "data").mkdir()
    shutil.copy(REPO_ROOT / "site" / "data" / "s6_signatures.json",
                site / "data" / "s6_signatures.json")
    specs = tmp_path / "docs" / "ideas" / "specs"
    specs.mkdir(parents=True)
    shutil.copy(REPO_ROOT / "docs" / "ideas" / "specs" / "s6-returns-only-signatures.md",
                specs / "s6-returns-only-signatures.md")
    (site / "cards.yaml").write_text(yaml.safe_dump([_CARD]), encoding="utf-8")
    build(site, tmp_path / "out", allow_legacy=True)
    return (tmp_path / "out" / "s6.html").read_text(encoding="utf-8"), tmp_path / "out"


def test_provenance_and_page_assets(tmp_path):
    html, out = _build(tmp_path)
    assert "synthetic-badge" in html
    assert "golive-box" in html
    assert 'id="card-data"' in html
    assert "specs/s6.html" in html
    assert "assets/pages/s6.css" in html and (out / "assets" / "pages" / "s6.css").exists()
    assert "assets/s6-signatures.js" in html and (out / "assets" / "s6-signatures.js").exists()
    assert "What this exhibit shows" in html


def test_refusal_and_reader_comparisons_precede_protocol(tmp_path):
    html, _ = _build(tmp_path)
    visible = _visible_text(html)
    assert "Monthly returns do not support an operational sizing or decay classification" in html
    assert "0 usable signals / 1 weak signal / 11 indistinguishable results" in html
    assert "Disciplined sizing versus equal weighting" in html
    assert "Fast decay versus slow decay" in html
    assert "One weak signal, still below usability" in html
    assert '<details class="s6-protocol">' in html
    assert html.index("Monthly returns do not support") < html.index("Disciplined sizing versus equal weighting")
    assert html.index("Disciplined sizing versus equal weighting") < html.index('<details class="s6-protocol">')
    assert "false-discovery rate" in html
    # The forking-paths footnote does the naive-scan arithmetic (~26%).
    assert "26%" in html or "26 %" in html
    for internal_term in ("PILOT", "SHIP", "H-SIZE", "H-DECAY", "wave-3", "ship rule", "repository history"):
        assert internal_term not in visible


def test_verdict_grid_no_bare_points(tmp_path):
    html, _ = _build(tmp_path)
    # One focal row plus the remaining eleven rows preserve all twelve reviewed intervals.
    assert html.count('class="interval-stat"') >= 12
    assert html.count('class="verdict-chip"') >= 12
    # adj p is always paired with the deciding-cell count (never bare).
    assert "deciding cells" in html
    # A null is rendered first-class, with the same standing as a discovery.
    assert 'data-verdict="null"' in html
    assert "an informative result, not missing evidence" in html


def test_two_threshold_honesty_and_single_manager_refusal(tmp_path):
    html, _ = _build(tmp_path)
    assert "usability" in html and "significance" in html  # both rail marks named
    assert "power-gate" in html
    assert "2 times in 3" in html                          # AUC 0.65 pair-odds
    assert "unknown by design" in html                     # confirmatory outcome disclaimer


def test_auc_rail_uses_full_domain_and_marks_null(tmp_path):
    html, out = _build(tmp_path)
    js = (out / "assets" / "s6-signatures.js").read_text(encoding="utf-8")
    assert "var LO = 0.0, HI = 1.0" in js
    assert "s6-rail__null" in html
    assert "data-domain-min=\"0\"" in html
    assert "data-domain-max=\"1\"" in html
    assert "0.326" in html


def test_s6_spec_pins_pilot_exclusion_and_reversal(tmp_path):
    _, out = _build(tmp_path)
    html = (out / "specs" / "s6.html").read_text(encoding="utf-8")
    assert "0 SHIP, 1 WEAK TELL, 11 NULL" in html
    assert "written-put stress axis" in html
    assert "excluded from the bounded pilot" in html
    assert "drawdown_shape" in html
    assert "opposite" in html
