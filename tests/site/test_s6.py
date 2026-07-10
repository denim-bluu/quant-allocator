import shutil
from pathlib import Path

import yaml

from quant_allocator.site.build import build

REPO_ROOT = Path(__file__).resolve().parents[2]

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
    build(site, tmp_path / "out")
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


def test_pilot_label_and_registration_document(tmp_path):
    html, _ = _build(tmp_path)
    assert "PILOT" in html
    assert "everything you are about to see was committed before the run" in html
    assert "hard-capped, pre-committed family" in html
    assert "FDR" in html and "not an FDR" in html
    # The forking-paths footnote does the naive-scan arithmetic (~26%).
    assert "26%" in html or "26 %" in html
    assert html.index("0 ship / 1 weak tell / 11 null") < html.index("Panel 1")
    assert "Panel 2 · PILOT" in html or "Panel 2 &middot; PILOT" in html


def test_verdict_grid_no_bare_points(tmp_path):
    html, _ = _build(tmp_path)
    # Two contrast blocks, six rows each; every AUC is an IntervalStat + a VerdictChip.
    assert "H-SIZE" in html and "H-DECAY" in html
    assert html.count('class="interval-stat"') >= 12
    assert html.count('class="verdict-chip"') >= 12
    # adj p is always paired with the deciding-cell count (never bare).
    assert "deciding cells" in html
    # A null is rendered first-class, with the same standing as a discovery.
    assert 'data-verdict="null"' in html
    assert "a finding, not an absence" in html


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
