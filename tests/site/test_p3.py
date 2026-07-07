# tests/site/test_p3.py
import shutil
from pathlib import Path

import yaml

from quant_allocator.site.build import build

REPO_ROOT = Path(__file__).resolve().parents[2]

# The exact values the integration task will paste into cards.yaml to flip P3 live.
P3_LIVE_FIELDS = {
    "status": "live",
    "demo": "pages/p3-hirefire.html.j2",
    "data": "p3_hirefire.json",
    "spec": "p3-hirefire-audit.md",
    "golive": {
        "data_ask": (
            "A prospectively-maintained decision journal (dates + type + pre-committed "
            "thesis, expected alpha, horizon, kill criterion) + monthly net returns for "
            "every manager touched by a decision (tier R, roster-wide)"
        ),
        "sample": (
            "None for the journal; the aggregate renders an average only above 12 "
            "effective events, and even then as an interval that straddles zero for years"
        ),
        "effort": "S",
    },
}


def _build_with_p3_live(tmp_path):
    site_dst = tmp_path / "site"
    shutil.copytree(REPO_ROOT / "site", site_dst)
    # build() resolves specs at site_dir.parent/docs/ideas/specs — mirror that tree.
    shutil.copytree(REPO_ROOT / "docs" / "ideas" / "specs", tmp_path / "docs" / "ideas" / "specs")

    manifest_path = site_dst / "cards.yaml"
    cards = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    for card in cards:
        if card["id"] == "p3":
            card.update(P3_LIVE_FIELDS)
    manifest_path.write_text(
        yaml.safe_dump(cards, sort_keys=False, allow_unicode=True), encoding="utf-8"
    )

    out = tmp_path / "out"
    build(site_dst, out)
    return (out / "p3.html").read_text(encoding="utf-8"), out


def test_p3_provenance_and_furniture(tmp_path):
    html, out = _build_with_p3_live(tmp_path)
    assert "synthetic-badge" in html
    assert "SYNTHETIC DATA" in html
    assert "golive-box" in html
    assert 'id="card-data"' in html
    assert "specs/p3.html" in html
    assert (out / "specs" / "p3.html").exists()
    # New page CSS is loaded via head_extra and copied by _copy_assets.
    assert "assets/pages/p3.css" in html
    assert (out / "assets" / "pages" / "p3.css").exists()


def test_p3_powergate_refuses_raw_average(tmp_path):
    # Gate ruling: the raw mean is refused; the banner is the pitch.
    html, _ = _build_with_p3_live(tmp_path)
    assert "power-gate" in html
    assert "not a track record" in html
    assert "Effective N" in html


def test_p3_posterior_is_intervalstat_with_base_rate_chip(tmp_path):
    # Gate ruling: the shrunk posterior renders at any N as an interval; the chip
    # "indistinguishable from the base rate" is the product, not a failure state.
    html, _ = _build_with_p3_live(tmp_path)
    assert 'data-domain="valueadd"' in html
    assert "90% interval" in html
    assert 'class="verdict-chip"' in html
    assert "indistinguishable from the base rate" in html
    assert "pinned at the Goyal" in html
    assert "2%/yr" in html   # prior scale, DECISION_VALUE_PRIOR_SCALE citation on page


def test_p3_detectability_one_liner_not_atlas(tmp_path):
    # Gate ruling: the MC atlas cell is CUT; the closed-form one-liner ships instead.
    html, _ = _build_with_p3_live(tmp_path)
    assert ("first exclude zero at" in html) or ("no attainable decision count" in html)
    assert "Monte" not in html   # no Monte-Carlo atlas language on the page


def test_p3_counterfactual_panel_and_ledger(tmp_path):
    html, _ = _build_with_p3_live(tmp_path)
    assert "p3-cohort" in html                 # fired-vs-replacement forward SVG
    assert html.count('class="p3-event ') >= 15  # the per-event ledger, never averaged
    # All three counterfactual rungs surface as receipts.
    assert "replacement-paired" in html
    assert "peer-median" in html
    assert "benchmark" in html


def test_p3_scorecard_shows_precommitments(tmp_path):
    html, _ = _build_with_p3_live(tmp_path)
    assert "Thesis (pre-committed)" in html
    assert "Kill criterion (pre-committed)" in html
    assert "Kill criterion met?" in html


def test_p3_script_loaded(tmp_path):
    html, out = _build_with_p3_live(tmp_path)
    assert "assets/p3-hirefire.js" in html
    assert (out / "assets" / "p3-hirefire.js").exists()
