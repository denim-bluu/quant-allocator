from pathlib import Path

import json
import shutil

from quant_allocator.site.build import build

REPO_ROOT = Path(__file__).resolve().parents[2]


def _build(tmp_path):
    out = tmp_path / "out"
    build(REPO_ROOT / "site", out)
    return (out / "x1.html").read_text(encoding="utf-8"), out


def _build_with_modified_payload(tmp_path):
    site = tmp_path / "site"
    shutil.copytree(REPO_ROOT / "site", site)
    shutil.copytree(REPO_ROOT / "docs" / "ideas" / "specs", tmp_path / "docs" / "ideas" / "specs")
    shutil.copytree(
        REPO_ROOT / "docs" / "ideas" / "articles",
        tmp_path / "docs" / "ideas" / "articles",
    )
    data_path = site / "data" / "x1_atlas.json"
    data = json.loads(data_path.read_text(encoding="utf-8"))
    data["tier_comparison"]["target_power"] = 0.81
    first = data["tier_comparison"]["rows"][0]
    first["months"] = 54
    first["returns_only"]["power"] = 0.271
    first["measured_exposure"]["power"] = 0.349
    data_path.write_text(json.dumps(data), encoding="utf-8")
    out = tmp_path / "out"
    build(site, out)
    return (out / "x1.html").read_text(encoding="utf-8")


def test_x1_provenance_and_headline(tmp_path):
    html, out = _build(tmp_path)
    assert "synthetic-badge" in html
    assert "golive-box" in html
    assert 'id="card-data"' in html
    assert "specs/x1.html" in html
    assert (out / "specs" / "x1.html").exists()
    assert "Measured exposures cross the 80% detection threshold at 120 months" in html
    # Gallery explainer obligation.
    assert "What this exhibit shows" in html
    assert "82.0%" in html
    assert "78.8%" in html
    assert "75.0%" in html
    assert "82.2%" in html
    assert "spans the 80% threshold" in html


def test_x1_tier_comparison_leads_with_axes_threshold_and_intervals(tmp_path):
    html, _ = _build(tmp_path)
    comparison = html.split('<section class="x1-tier-comparison"', 1)[1].split(
        "</section>", 1
    )[0]
    assert html.index('<section class="x1-tier-comparison"') < html.index("What this exhibit shows")
    assert "Track length (months)" in comparison
    assert "Detection probability" in comparison
    assert "80% reliability threshold" in comparison
    assert "Returns only" in comparison
    assert "Measured exposures" in comparison
    assert "48 months" in comparison and "120 months" in comparison
    assert comparison.count("Wilson 95% interval") == 4
    assert "returns-only interval spans the 80% threshold" in comparison
    assert 'data-target="0.8"' in comparison


def test_x1_power_curves_and_posterior_label(tmp_path):
    html, _ = _build(tmp_path)
    # Realized IR labels drawn from the JSON realized_ir fields.
    assert "realized IR 0.65" in html  # ic 0.04 -> 0.648
    assert "realized IR 1.57" in html  # ic 0.10 -> 1.567
    # Three power-curve SVG exhibits.
    assert html.count("x1-powercurve") >= 3
    # Posterior label copy obligation (false-attribution price of borrowing strength).
    assert "the price of borrowing strength" in html
    assert "false-attribution at IC=0" in html
    assert "data-ols-lo=" in html
    assert "data-ols-hi=" in html
    assert "data-posterior-lo=" in html
    assert "data-posterior-hi=" in html
    assert "Wilson 95% interval" in html


def test_x1_degradation_table(tmp_path):
    html, _ = _build(tmp_path)
    # Degradation table powers verbatim from the JSON (at T=48, IC=0.04).
    assert "25.2%" in html  # alpha_estimation R power
    assert "31.8%" in html  # alpha_estimation E power
    assert "13.2%" in html  # hit_rate_P power
    assert "23.4%" in html  # sizing_skill_P power
    assert "Not calculated" in html  # drift_detection
    assert html.count("Wilson 95%") >= 4
    assert "Returns only" in html
    assert "Measured exposures" in html
    assert "Positions and trades" in html


def test_x1_decision_copy_follows_named_payload_fields(tmp_path):
    html = _build_with_modified_payload(tmp_path)
    comparison = html.split('<section class="x1-tier-comparison"', 1)[1].split(
        "</section>", 1
    )[0]
    assert "81% reliability threshold" in comparison
    assert "54 months" in comparison
    assert "27.1%" in comparison
    assert "34.9%" in comparison
    assert 'data-target="0.81"' in comparison


def test_x1_omits_internal_registry_and_sampler_language(tmp_path):
    html, _ = _build(tmp_path)
    public_page = html.split('<section class="atlas-intro">', 1)[1].split(
        '<details class="evidence-appendix">', 1
    )[0]
    for internal in ("PowerGate registry", "Registry rows", "docket", "sampler"):
        assert internal.lower() not in public_page.lower()


def test_x1_script_loaded(tmp_path):
    html, out = _build(tmp_path)
    assert "assets/x1-atlas.js" in html
    assert (out / "assets" / "x1-atlas.js").exists()
    script = (out / "assets" / "x1-atlas.js").read_text(encoding="utf-8")
    assert "drawTierComparison" in script
    assert 'querySelector(".x1-tier-chart")' in script
    assert "regression" not in script.lower()
