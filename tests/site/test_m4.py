import shutil
from pathlib import Path

import yaml

from quant_allocator.site.build import build

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_publication_terms():
    path = REPO_ROOT / "tools" / ".publication_terms"
    if not path.exists():
        return ()
    return tuple(
        line.strip().lower()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    )


_CARD = {
    "id": "m4",
    "title": "Crowding & overlap radar",
    "lane": "M",
    "one_liner": "Is our diversification illusory — are the managers the same trade?",
    "decisions": ["size", "monitor", "redeem"],
    "tiers": ["P", "E", "R"],
    "status": "live",
    "demo": "pages/m4-crowding.html.j2",
    "data": "m4_crowding.json",
    "spec": "m4-crowding-overlap-radar.md",
    "golive": {
        "data_ask": (
            "Position-level holdings aligned to a shared name universe, plus per-name "
            "dollar ADV and daily volatility; the public rung later consumes public "
            "filings through the shared adapter"
        ),
        "sample": (
            "None for the point-in-time measurement; predictive loss and any size-cap "
            "recommendation remain refused until atlas gate 2 clears"
        ),
        "effort": "M–L",
    },
}


def _build(tmp_path):
    site = tmp_path / "site"
    shutil.copytree(REPO_ROOT / "site" / "templates", site / "templates")
    shutil.copytree(REPO_ROOT / "site" / "assets", site / "assets")
    (site / "data").mkdir()
    shutil.copy(
        REPO_ROOT / "site" / "data" / "m4_crowding.json",
        site / "data" / "m4_crowding.json",
    )
    specs = tmp_path / "docs" / "ideas" / "specs"
    specs.mkdir(parents=True)
    shutil.copy(
        REPO_ROOT / "docs" / "ideas" / "specs" / "m4-crowding-overlap-radar.md",
        specs / "m4-crowding-overlap-radar.md",
    )
    (site / "cards.yaml").write_text(
        yaml.safe_dump([_CARD], sort_keys=False, allow_unicode=True), encoding="utf-8"
    )
    out = tmp_path / "out"
    build(site, out)
    return (out / "m4.html").read_text(encoding="utf-8"), out


def test_page_furniture_assets_and_spec(tmp_path):
    html, out = _build(tmp_path)
    assert "SYNTHETIC DATA" in html
    assert 'id="card-data"' in html
    assert "golive-box" in html
    assert "What this exhibit shows" in html
    assert "What you are looking at" in html
    assert "How to read it" in html
    assert "specs/m4.html" in html
    assert (out / "specs" / "m4.html").exists()
    assert "assets/pages/m4.css" in html
    assert "assets/m4-crowding.js" in html
    assert (out / "assets" / "pages" / "m4.css").exists()
    assert (out / "assets" / "m4-crowding.js").exists()


def test_exact_snapshot_measurements_and_centerpiece(tmp_path):
    html, _ = _build(tmp_path)
    assert "Hollowmere Capital" in html
    assert "Brackenford Partners" in html
    assert html.count("exact for this snapshot; no sampling interval") == 3
    assert "Signed holdings-vector cosine" in html
    assert "not a return-correlation estimate" in html
    assert html.count('data-domain="overlap"') == 2
    assert 'data-domain="cosine"' in html
    assert '<span class="interval-stat__value" id="m4-cosine-value">0.327</span>' in html


def test_pair_selector_updates_values_data_and_rail_geometry():
    script = (REPO_ROOT / "site" / "assets" / "m4-crowding.js").read_text(encoding="utf-8")
    assert "function updateStat" in script
    assert 'stat.dataset.lo = String(value)' in script
    assert 'stat.dataset.point = String(value)' in script
    assert 'stat.dataset.hi = String(value)' in script
    assert 'querySelector(".interval-stat__band")' in script
    assert 'querySelector(".interval-stat__point")' in script
    assert 'updateStat("m4-raw", data.heatmap.raw[i][j], "overlap")' in script
    assert 'updateStat("m4-cosine", data.heatmap.cosine[i][j], "cosine")' in script


def test_heatmap_and_stress_controls_are_accessible_and_precomputed(tmp_path):
    html, _ = _build(tmp_path)
    assert 'role="grid"' in html
    assert html.count('role="gridcell"') == 36
    assert html.count("liquidity-adjusted overlap") >= 36
    assert 'id="m4-stress-delta"' in html
    assert 'id="m4-unwind-bars"' in html
    assert "illustrative impact" in html
    assert "illustrative &mdash; not a forecast" in html


def test_measurement_prediction_split_and_kill_rule(tmp_path):
    html, _ = _build(tmp_path)
    assert "Scenario, not forecast" in html
    assert "No predicted loss or size-cap" in html
    assert "If gate 2 fails, the measurement stays" in html
    assert "M4 measures crowding; it does not allocate" in html
    assert "never computes portfolio weights" in html


def test_tier_limits_and_public_view_withheld(tmp_path):
    html, _ = _build(tmp_path)
    assert 'data-tier="P"' in html
    assert 'data-tier="E"' in html
    assert 'data-tier="R"' in html
    assert "Factor crowding only" in html
    assert "not a holdings measurement" in html
    assert "13F view withheld pending degradation gate" in html
    assert "45-day lag" in html
    assert "longs-only" in html
    assert "CTR coverage holes" in html
    assert "non-US blindness" in html


def test_golive_values_and_publication_terms(tmp_path):
    html, _ = _build(tmp_path)
    assert "Position-level holdings aligned to a shared name universe" in html
    assert "predictive loss and any size-cap" in html
    lowered = html.lower()
    for term in _load_publication_terms():
        assert term not in lowered
