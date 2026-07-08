import shutil
from pathlib import Path

import yaml

from quant_allocator.site.build import build

REPO_ROOT = Path(__file__).resolve().parents[2]

_CARD = {
    "id": "s3", "title": "Sizing & alpha-decay lab", "lane": "S",
    "one_liner": "When a book makes money, is the edge in the picking, the sizing, or the holding?",
    "decisions": ["size", "select"], "tiers": ["P"], "status": "live",
    "demo": "pages/s3-lab.html.j2", "data": "s3_lab.json", "spec": "s3-sizing-decay-lab.md",
    "golive": {
        "data_ask": "Dated position snapshots (signed weights) + trades (entry/exit) + factor returns (P)",
        "sample": "A book clearing ~780 independent trades (65-name, 25%-turnover reaches it in ~3-4 years)",
        "effort": "M",
    },
}


def _build(tmp_path):
    site = tmp_path / "site"
    shutil.copytree(REPO_ROOT / "site" / "templates", site / "templates")
    shutil.copytree(REPO_ROOT / "site" / "assets", site / "assets")
    (site / "data").mkdir()
    shutil.copy(REPO_ROOT / "site" / "data" / "s3_lab.json", site / "data" / "s3_lab.json")
    specs = tmp_path / "docs" / "ideas" / "specs"
    specs.mkdir(parents=True)
    shutil.copy(REPO_ROOT / "docs" / "ideas" / "specs" / "s3-sizing-decay-lab.md",
                specs / "s3-sizing-decay-lab.md")
    (site / "cards.yaml").write_text(yaml.safe_dump([_CARD]), encoding="utf-8")
    build(site, tmp_path / "out")
    return (tmp_path / "out" / "s3.html").read_text(encoding="utf-8"), tmp_path / "out"


def test_provenance_and_page_assets(tmp_path):
    html, out = _build(tmp_path)
    assert "synthetic-badge" in html
    assert "golive-box" in html
    assert 'id="card-data"' in html
    assert "specs/s3.html" in html
    assert "assets/pages/s3.css" in html and (out / "assets" / "pages" / "s3.css").exists()
    assert "assets/s3-lab.js" in html and (out / "assets" / "s3-lab.js").exists()
    assert '<span class="tier-badge" data-tier="P">' in html


def test_what_this_exhibit_shows(tmp_path):
    html, _ = _build(tmp_path)
    assert "What this exhibit shows" in html
    assert "What you are looking at" in html
    assert "How to read it" in html


def test_picker_sizer_split_and_verdict(tmp_path):
    html, _ = _build(tmp_path)
    assert "Meridian Arc Capital" in html and "Kelso Bay Partners" in html
    assert html.count('class="verdict-chip"') >= 2
    assert html.count('class="interval-stat"') >= 2          # slopes as IntervalStats, no bare points
    assert "leaving a conviction premium on the table" in html
    assert "this is a sizing conversation" in html


def test_powergate_refusal_arithmetic(tmp_path):
    html, _ = _build(tmp_path)
    assert "power-gate" in html
    assert "insufficient N" in html
    assert "174" in html
    assert "indistinguishable from luck" in html
    # Pin the binding "174 of ~780 independent trades" refusal arithmetic verbatim. The
    # template's {% if gate.hit_rate_threshold %} block renders across a line break, so "of"
    # and "~780" are separated by a newline + indent, not a single space — match that exactly
    # so the assertion actually fails if the ~780 figure disappears from the refusal copy.
    assert "174 of\n      ~780\n      independent trades" in html


def test_cluster_axis_and_reference_effect_statements(tmp_path):
    html, _ = _build(tmp_path)
    assert "cluster axis: date" in html
    assert "never clears 80%" in html and "T &le; 120" in html or "T ≤ 120" in html


def test_decay_curve_entry_premium_and_wide_single_band(tmp_path):
    html, _ = _build(tmp_path)
    assert "half-life" in html
    assert "entry" in html                                   # entry month shown separately (§3.5)
    assert "s3-decay" in html                                # the decay SVG exhibit
