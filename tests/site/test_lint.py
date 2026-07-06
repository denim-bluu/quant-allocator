import shutil

import yaml

import pytest

from pathlib import Path

from quant_allocator.site.build import BuildError, _lint_outputs, build

REPO_ROOT = Path(__file__).resolve().parents[2]

VALID_PAGE = '<span class="synthetic-badge"></span><dl class="golive-box"></dl>'


def _card(**overrides):
    card = {"id": "t1", "status": "live"}
    card.update(overrides)
    return card


def _write_page(out_dir, card_id, html):
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"{card_id}.html").write_text(html, encoding="utf-8")


def _write_spec(out_dir, card_id):
    specs = out_dir / "specs"
    specs.mkdir(parents=True, exist_ok=True)
    (specs / f"{card_id}.html").write_text("<html></html>", encoding="utf-8")


def test_lint_passes_for_valid_nondoctrine(tmp_path):
    _write_page(tmp_path, "t1", VALID_PAGE)
    _write_spec(tmp_path, "t1")
    _lint_outputs([_card()], tmp_path)


def test_lint_missing_synthetic_badge_raises(tmp_path):
    _write_page(tmp_path, "t1", '<dl class="golive-box"></dl>')
    _write_spec(tmp_path, "t1")
    with pytest.raises(BuildError, match="synthetic-badge"):
        _lint_outputs([_card()], tmp_path)


def test_lint_missing_golive_raises(tmp_path):
    _write_page(tmp_path, "t1", '<span class="synthetic-badge"></span>')
    _write_spec(tmp_path, "t1")
    with pytest.raises(BuildError, match="golive-box"):
        _lint_outputs([_card()], tmp_path)


def test_lint_dangling_spec_link_raises(tmp_path):
    _write_page(tmp_path, "t1", VALID_PAGE)
    with pytest.raises(BuildError, match="spec link target missing"):
        _lint_outputs([_card()], tmp_path)


def test_lint_doctrine_requires_usage_note(tmp_path):
    _write_page(tmp_path, "e1", '<aside class="usage-note"></aside>')
    _write_spec(tmp_path, "e1")
    _lint_outputs([_card(id="e1", doctrine=True)], tmp_path)


def test_lint_doctrine_missing_usage_note_raises(tmp_path):
    _write_page(tmp_path, "e1", "<article></article>")
    _write_spec(tmp_path, "e1")
    with pytest.raises(BuildError, match="usage-note"):
        _lint_outputs([_card(id="e1", doctrine=True)], tmp_path)


def test_build_fails_on_missing_data_file(tmp_path):
    site = tmp_path / "site"
    shutil.copytree(REPO_ROOT / "site" / "templates", site / "templates")
    shutil.copytree(REPO_ROOT / "site" / "assets", site / "assets")
    (site / "templates" / "pages" / "t1.html.j2").write_text(
        "{% extends 'demo.html.j2' %}", encoding="utf-8"
    )
    (site / "data").mkdir()
    specs = tmp_path / "docs" / "ideas" / "specs"
    specs.mkdir(parents=True)
    (specs / "t1.md").write_text("# t1", encoding="utf-8")
    (site / "cards.yaml").write_text(
        yaml.safe_dump(
            [
                {
                    "id": "t1",
                    "title": "Test card",
                    "lane": "S",
                    "one_liner": "x",
                    "decisions": ["select"],
                    "tiers": ["R"],
                    "status": "live",
                    "demo": "pages/t1.html.j2",
                    "data": "t1.json",
                    "spec": "t1.md",
                    "golive": {"data_ask": "R", "sample": "36m", "effort": "S"},
                }
            ]
        ),
        encoding="utf-8",
    )
    with pytest.raises(BuildError, match="missing data file"):
        build(site, tmp_path / "out")


def test_real_demo_page_has_furniture(tmp_path):
    site = tmp_path / "site"
    shutil.copytree(REPO_ROOT / "site" / "templates", site / "templates")
    shutil.copytree(REPO_ROOT / "site" / "assets", site / "assets")
    (site / "templates" / "pages" / "t1.html.j2").write_text(
        "{% extends 'demo.html.j2' %}", encoding="utf-8"
    )
    (site / "data").mkdir()
    (site / "data" / "t1.json").write_text('{"ok": true}', encoding="utf-8")
    specs = tmp_path / "docs" / "ideas" / "specs"
    specs.mkdir(parents=True)
    (specs / "t1.md").write_text("# t1", encoding="utf-8")
    (site / "cards.yaml").write_text(
        yaml.safe_dump(
            [
                {
                    "id": "t1",
                    "title": "Test card",
                    "lane": "S",
                    "one_liner": "x",
                    "decisions": ["select"],
                    "tiers": ["R"],
                    "status": "live",
                    "demo": "pages/t1.html.j2",
                    "data": "t1.json",
                    "spec": "t1.md",
                    "golive": {"data_ask": "R", "sample": "36m", "effort": "S"},
                }
            ]
        ),
        encoding="utf-8",
    )
    build(site, tmp_path / "out")
    html = (tmp_path / "out" / "t1.html").read_text(encoding="utf-8")
    assert "synthetic-badge" in html
    assert "golive-box" in html
    assert 'id="card-data"' in html
    assert "specs/t1.html" in html
