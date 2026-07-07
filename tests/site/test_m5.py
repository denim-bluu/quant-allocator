from pathlib import Path

from quant_allocator.site.build import build

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_m5_page_provenance_and_copy(tmp_path):
    out = tmp_path / "out"
    build(REPO_ROOT / "site", out)
    html = (out / "m5.html").read_text(encoding="utf-8")
    assert "synthetic-badge" in html
    assert "SYNTHETIC DATA" in html
    assert "golive-box" in html
    # numerics gate: the delta dead-band is labeled illustrative wherever shown.
    assert "illustrative, uncalibrated" in html
    assert 'id="card-data"' in html
    assert "specs/m5.html" in html
    assert (out / "specs" / "m5.html").exists()


def test_m5_page_verdict_contract_and_quotes(tmp_path):
    out = tmp_path / "out"
    build(REPO_ROOT / "site", out)
    html = (out / "m5.html").read_text(encoding="utf-8")
    # VerdictChip contract states present in the data (aligned + contradicted;
    # "partial" is a supported state exercised by CSS, not by this dataset).
    assert 'data-verdict="aligned"' in html
    assert 'data-verdict="contradicted"' in html
    assert 'class="verdict-chip"' in html
    # The contradiction row is the centerpiece.
    assert "saydo-row--contradicted" in html
    # Verbatim quote from the JSON (receipts always ship with claims).
    assert "crowded momentum has become" in html


def test_m5_page_script_loaded(tmp_path):
    out = tmp_path / "out"
    build(REPO_ROOT / "site", out)
    html = (out / "m5.html").read_text(encoding="utf-8")
    assert "assets/m5-saydo.js" in html
    assert (out / "assets" / "m5-saydo.js").exists()
