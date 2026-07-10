import shutil
from pathlib import Path

import yaml

from quant_allocator.site.build import build

REPO_ROOT = Path(__file__).resolve().parents[2]

M2_CARD = {
    "id": "m2",
    "title": "Hidden-convexity / short-vol screen",
    "lane": "M",
    "one_liner": "A smooth Sharpe can hide sold optionality — surface the short-vol posture.",
    "decisions": ["monitor", "redeem"],
    "tiers": ["R", "E", "P"],
    "status": "live",
    "demo": "pages/m2-convexity.html.j2",
    "data": "m2_convexity.json",
    "spec": "m2-hidden-convexity-screen.md",
    "golive": {
        "data_ask": "Monthly net returns (R) + a market-factor return series; the straddle rung adds the public Fung–Hsieh PTFS series (adapter not yet built)",
        "sample": "Calibrated false-alarm, not a raw count — composite renders at T ≥ 48 months where honest false-alarm ≤ 0.10",
        "effort": "M",
    },
}


def _build_m2(tmp_path):
    site = tmp_path / "site"
    shutil.copytree(REPO_ROOT / "site" / "templates", site / "templates")
    shutil.copytree(REPO_ROOT / "site" / "assets", site / "assets")
    (site / "data").mkdir()
    shutil.copy(REPO_ROOT / "site" / "data" / "m2_convexity.json", site / "data" / "m2_convexity.json")
    specs = tmp_path / "docs" / "ideas" / "specs"
    specs.mkdir(parents=True)
    shutil.copy(
        REPO_ROOT / "docs" / "ideas" / "specs" / "m2-hidden-convexity-screen.md",
        specs / "m2-hidden-convexity-screen.md",
    )
    (site / "cards.yaml").write_text(yaml.safe_dump([M2_CARD]), encoding="utf-8")
    out = tmp_path / "out"
    build(site, out)
    return (out / "m2.html").read_text(encoding="utf-8"), out


def test_m2_provenance_furniture(tmp_path):
    html, out = _build_m2(tmp_path)
    assert "synthetic-badge" in html
    assert "SYNTHETIC DATA" in html
    assert "golive-box" in html
    assert 'id="card-data"' in html
    assert "specs/m2.html" in html
    assert (out / "specs" / "m2.html").exists()


def test_m2_exhibit_explainer_present(tmp_path):
    html, _ = _build_m2(tmp_path)
    assert "What this exhibit shows" in html


def test_m2_paired_managers_and_components(tmp_path):
    html, _ = _build_m2(tmp_path)
    # Both fictional manager names render.
    assert "Wrenmoor Partners" in html
    assert "Gullwing Point Capital" in html
    # IntervalStats (two Sharpe + the played diagnostics) and VerdictChips present.
    assert html.count('class="interval-stat"') >= 5
    assert 'class="verdict-chip' in html
    assert "95% interval" in html
    assert "90% interval" in html


def test_m2_composite_and_copy_obligations(tmp_path):
    html, _ = _build_m2(tmp_path)
    # numerics gate binding copy.
    assert "converging evidence, not a p-value" in html.lower()
    # Investigation framing, not an accusation.
    assert "SHORT-VOL POSTURE — INVESTIGATE" in html
    # Overlay disclosure obligation — two-sided form per the DK-7 gate ruling:
    # (a) demo premium is rich of fair (the carry seduction), an in-sample
    # look-ahead, not live methodology; (b) atlas detection rows measure at
    # fair premium, the conservative case.
    assert "in-sample" in html.lower()
    assert "not a claim about live methodology" in html.lower()
    assert "rich of fair" in html.lower()
    assert "carry seduction" in html.lower()
    assert "fair premium" in html.lower()
    assert "conservative" in html.lower()
    # HM down-leg honesty stays on the sheet.
    assert "~19" in html
    assert "static payoff-shape descriptor" in html.lower()


def test_m2_straddle_rung_unplayed_refusal(tmp_path):
    html, _ = _build_m2(tmp_path)
    # The external-data rung renders as an honest unplayed power-gate, not a fake stat.
    assert "power-gate" in html
    assert "adapter not yet built" in html
    assert "PTFS" in html


def test_m2_stress_month_receipts_render(tmp_path):
    html, _ = _build_m2(tmp_path)
    assert "Stress-month receipts" in html
    assert "m2-stress-table" in html
    assert "Put payout" in html


def test_m2_css_and_js_wired(tmp_path):
    html, out = _build_m2(tmp_path)
    assert "assets/pages/m2.css" in html
    assert "assets/m2-convexity.js" in html
    assert (out / "assets" / "pages" / "m2.css").exists()
    assert (out / "assets" / "m2-convexity.js").exists()


def test_m2_coskew_band_is_visible_and_verdict_unchanged(tmp_path):
    html, _ = _build_m2(tmp_path)
    coskew = html.split('data-domain="market_coskew"', 1)[1][:1800]
    assert 'data-decision-low="-0.35"' in coskew
    assert 'data-decision-high="0.35"' in coskew
    assert "m2-decision-band" in coskew
    assert "m2-decision-boundary" in coskew
    assert "clears zero" in html
    assert "must clear &minus;0.35" in html
    assert "3 of 4" in html
    script = (REPO_ROOT / "site" / "assets" / "m2-convexity.js").read_text(encoding="utf-8")
    assert 'dataset.decisionLow' in script
    assert 'querySelector(".m2-decision-band")' in script
