import shutil
from pathlib import Path

import yaml

from quant_allocator.site.build import build

REPO_ROOT = Path(__file__).resolve().parents[2]

_CARD = {
    "id": "p1",
    "title": "Allocation under alpha uncertainty",
    "lane": "P",
    "one_liner": "Given posterior skill, how much capital? Sizing that consumes uncertainty.",
    "decisions": ["size", "redeem"],
    "tiers": ["R", "E", "P"],
    "status": "live",
    "demo": "pages/p1-allocation.html.j2",
    "data": "p1_allocation.json",
    "spec": "p1-allocation-uncertainty.md",
    "golive": {
        "data_ask": "S1's tier-R inputs (monthly net returns >=36m for >=10 managers with strategy "
                    "labels, factor sets, risk-free) plus a per-manager residual vol (S2 de-smoothed).",
        "sample": "Any T renders honest bands (width carries the honesty); decisive bands need "
                  "T >= 48 and true skill dispersion >= 2%/yr.",
        "effort": "S (+M for the wave-3 policy-regret study).",
    },
}


def _build(tmp_path):
    site = tmp_path / "site"
    shutil.copytree(REPO_ROOT / "site" / "templates", site / "templates")
    shutil.copytree(REPO_ROOT / "site" / "assets", site / "assets")
    (site / "data").mkdir()
    shutil.copy(REPO_ROOT / "site" / "data" / "p1_allocation.json",
                site / "data" / "p1_allocation.json")
    specs = tmp_path / "docs" / "ideas" / "specs"
    specs.mkdir(parents=True)
    shutil.copy(REPO_ROOT / "docs" / "ideas" / "specs" / "p1-allocation-uncertainty.md",
                specs / "p1-allocation-uncertainty.md")
    (site / "cards.yaml").write_text(yaml.safe_dump([_CARD]), encoding="utf-8")
    build(site, tmp_path / "out")
    return (tmp_path / "out" / "p1.html").read_text(encoding="utf-8"), tmp_path / "out"


def test_provenance_and_assets(tmp_path):
    html, out = _build(tmp_path)
    assert "synthetic-badge" in html
    assert "golive-box" in html
    assert 'id="card-data"' in html
    assert "specs/p1.html" in html
    assert "assets/pages/p1.css" in html
    assert (out / "assets" / "pages" / "p1.css").exists()
    assert "assets/p1-allocation.js" in html
    assert (out / "assets" / "p1-allocation.js").exists()


def test_exhibit_explainer_present(tmp_path):
    html, _ = _build(tmp_path)
    assert "What this exhibit shows" in html
    assert "What you are looking at" in html
    assert "How to read it" in html


def test_gate_ruled_copy_substrings(tmp_path):
    html, _ = _build(tmp_path)
    assert "10th&ndash;90th percentile of posterior-draw weights" in html   # §8.1 band label
    assert "residual volatility constant at 8%/yr" in html                  # §8.2 disclosure
    assert "treat manager posteriors as independent" in html               # §8.3 provisional
    assert "policy-regret study" in html and "pending" in html             # §8.4 study pending
    assert "every band on this page is advisory" in html                   # §8.4 advisory
    assert "fund-or-not" in html                                           # §5 fund-or-not signal
    assert "point optimizer" in html                                       # §5 cautionary contrast


def test_b10_headline_and_contrast_rendered(tmp_path):
    html, _ = _build(tmp_path)
    # Server-rendered from the committed JSON: the headline manager and its verdict.
    assert "Cinderbank Capital" in html
    # 20 band rows, each an IntervalStat (no bare points).
    assert html.count('class="interval-stat"') >= 20
    # The naive-OLS contrast marker and the fund-or-not chip render.
    assert "p1-naive" in html
    assert "p1-chip--fund" in html
    # PowerGate refusal with its threshold arithmetic.
    assert "power-gate" in html
    assert "T &ge; 48" in html or "T ≥ 48" in html


def test_tau_dial_is_precomputed(tmp_path):
    html, _ = _build(tmp_path)
    # The skepticism dial snaps among precomputed τ-scale states (x2/M3 idiom); no client compute.
    assert "data-dial" in html or "p1-dial" in html
    assert "skepticism" in html
