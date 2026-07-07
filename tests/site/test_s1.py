from pathlib import Path

from quant_allocator.site.build import build

REPO_ROOT = Path(__file__).resolve().parents[2]


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


def test_s1_page_script_loaded(tmp_path):
    out = tmp_path / "out"
    build(REPO_ROOT / "site", out)
    html = (out / "s1.html").read_text(encoding="utf-8")
    assert "assets/s1-ledger.js" in html
    assert (out / "assets" / "s1-ledger.js").exists()
