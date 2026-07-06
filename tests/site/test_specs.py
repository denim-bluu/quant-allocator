import shutil

import yaml

from pathlib import Path

from quant_allocator.site.build import build

REPO_ROOT = Path(__file__).resolve().parents[2]


def _fixture_site(tmp_path):
    site = tmp_path / "site"
    shutil.copytree(REPO_ROOT / "site" / "templates", site / "templates")
    shutil.copytree(REPO_ROOT / "site" / "assets", site / "assets")
    (site / "templates" / "pages").mkdir(exist_ok=True)
    (site / "templates" / "pages" / "t1.html.j2").write_text(
        "{% extends 'demo.html.j2' %}", encoding="utf-8"
    )
    (site / "data").mkdir()
    (site / "data" / "t1.json").write_text("{}", encoding="utf-8")
    specs = tmp_path / "docs" / "ideas" / "specs"
    specs.mkdir(parents=True)
    (specs / "t1.md").write_text(
        "# Spec\n\nInline math $\\alpha$ here.\n\n"
        "| a | b |\n| --- | --- |\n| 1 | 2 |\n",
        encoding="utf-8",
    )
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
    return site


def test_spec_renders_math_untouched_and_table(tmp_path):
    site = _fixture_site(tmp_path)
    build(site, tmp_path / "out")
    html = (tmp_path / "out" / "specs" / "t1.html").read_text(encoding="utf-8")
    assert r"$\alpha$" in html
    assert "<table>" in html
