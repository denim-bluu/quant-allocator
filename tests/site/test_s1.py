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
