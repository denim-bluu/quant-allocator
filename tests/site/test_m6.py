import shutil
from pathlib import Path

import yaml

from quant_allocator.site.build import build

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_publication_terms() -> tuple[str, ...]:
    canary = REPO_ROOT / "tools" / ".publication_terms"
    if not canary.exists():
        return ()
    return tuple(
        line.strip().lower()
        for line in canary.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    )


_BANNED = _load_publication_terms()

_CARD = {
    "id": "m6",
    "title": "13F long-book intelligence",
    "lane": "M",
    "one_liner": "Reported-long concentration and persistence prompts from quarterly 13F filings.",
    "decisions": ["monitor", "engage"],
    "tiers": ["P"],
    "status": "live",
    "demo": "pages/m6-holdings.html.j2",
    "data": "m6_holdings.json",
    "spec": "m6-13f-long-book.md",
    "golive": {
        "data_ask": (
            "Public SEC EDGAR Form 13F quarterly filings, a 13(f)-eligibility reference, "
            "and a value-to-shares source; FINRA short interest plus ADV is required only "
            "for the deferred short-interest lens"
        ),
        "sample": (
            "Any history supports a snapshot, but concentration and overlap require "
            "coverage of at least 0.60; several quarters are required for persistence "
            "and trajectory"
        ),
        "effort": "M",
    },
}


def _build(tmp_path):
    site = tmp_path / "site"
    shutil.copytree(REPO_ROOT / "site" / "templates", site / "templates")
    shutil.copytree(REPO_ROOT / "site" / "assets", site / "assets")
    (site / "data").mkdir()
    shutil.copy(REPO_ROOT / "site" / "data" / "m6_holdings.json", site / "data")
    specs = tmp_path / "docs" / "ideas" / "specs"
    specs.mkdir(parents=True)
    shutil.copy(REPO_ROOT / "docs" / "ideas" / "specs" / _CARD["spec"], specs)
    (site / "cards.yaml").write_text(yaml.safe_dump([_CARD]), encoding="utf-8")
    out = tmp_path / "out"
    build(site, out)
    return (out / "m6.html").read_text(encoding="utf-8"), out


def test_page_furniture_and_accessible_timeline(tmp_path):
    html, out = _build(tmp_path)
    assert "SYNTHETIC DATA" in html
    assert "golive-box" in html
    assert "specs/m6.html" in html
    assert "assets/pages/m6.css" in html
    assert (out / "assets" / "pages" / "m6.css").exists()
    assert "What this exhibit shows" in html
    assert "What you are looking at" in html
    assert "How to read it" in html
    assert "Reported-long timeline" in html
    assert "<caption>" in html
    assert html.count('scope="col"') >= 6
    assert "m6-holdings.js" not in html


def test_centerpiece_receipts_and_method_boundaries(tmp_path):
    html, out = _build(tmp_path)
    intro = html.split('<section class="m6-intro">', 1)[1].split("</section>", 1)[0]
    crossing = html.split('<p class="m6-crossing">', 1)[1].split("</p>", 1)[0]
    assert "Vesper Lane Capital" in html
    assert "This fully synthetic 13F-style filing crop shows" in intro
    assert intro.count("as of") == 2
    assert intro.count("known at") == 2
    assert intro.count("45-day lag") == 2
    assert 'data-receipt="crossing"' in crossing
    assert "as of" in crossing
    assert "known at" in crossing
    assert "45-day lag" in crossing
    assert "as of" in html
    assert "known at" in html
    assert "45-day lag" in html
    assert "crowding caps belong to M4" in html
    assert "quarterly survival at filing granularity" in html
    assert "never a half-life and never entry-dated" in html
    assert "walk us through the conviction?" in html
    assert html.lower().count("conviction") == 1
    spec_html = (out / "specs" / "m6.html").read_text(encoding="utf-8")
    assert "conviction" not in spec_html.lower()
    assert "not a return prediction" in html


def test_coverage_gate_suppresses_hensley_book_verdicts(tmp_path):
    html, _ = _build(tmp_path)
    vesper = html.split('data-filer="vesper"', 1)[1].split("</article>", 1)[0]
    hensley = html.split('data-filer="hensley"', 1)[1].split("</article>", 1)[0]
    assert 'data-stat="concentration"' in vesper
    assert 'data-stat="overlap"' in vesper
    assert "CoverageGate pass" in vesper
    assert 'data-stat="concentration"' not in hensley
    assert 'data-stat="overlap"' not in hensley
    assert "CoverageGate refusal" in hensley
    assert "visible names" in hensley


def test_finra_placeholder_and_caveat_ledger(tmp_path):
    html, _ = _build(tmp_path)
    assert "requires FINRA adapter" in html
    assert "days-to-cover number is shown" not in html
    assert "Staleness" in html
    assert "Longs-only" in html
    assert "Coverage holes" in html
    assert "Option-notional" in html
    assert "option lines are excluded" in html


def test_golive_and_publication_canary(tmp_path):
    html, _ = _build(tmp_path)
    assert "Public SEC EDGAR Form 13F" in html
    assert "coverage of at least 0.60" in html
    lowered = html.lower()
    for banned in _BANNED:
        assert banned not in lowered
