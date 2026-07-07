from pathlib import Path

from quant_allocator.site.build import build

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_e1_ladder_page(tmp_path):
    build(REPO_ROOT / "site", tmp_path / "out")
    html = (tmp_path / "out" / "e1.html").read_text(encoding="utf-8")
    for rung in ["Rung 1", "Rung 2", "Rung 3"]:
        assert rung in html
    assert "synthetic-badge" not in html
    assert "usage-note" in html
    assert "What this exhibit shows" in html
    assert "Standing rules" in html
    assert (tmp_path / "out" / "specs" / "e1.html").exists()
