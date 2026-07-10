from pathlib import Path

from quant_allocator.site.build import build

REPO_ROOT = Path(__file__).resolve().parents[2]


def _build(tmp_path):
    out = tmp_path / "out"
    build(REPO_ROOT / "site", out)
    return (out / "x1.html").read_text(encoding="utf-8"), out


def test_x1_provenance_and_headline(tmp_path):
    html, out = _build(tmp_path)
    assert "synthetic-badge" in html
    assert "golive-box" in html
    assert 'id="card-data"' in html
    assert "specs/x1.html" in html
    assert (out / "specs" / "x1.html").exists()
    # Atlas headline copy obligation.
    assert "only the E-tier shrinkage posterior reaches 80% power within a 10-year record" in html
    # Gallery explainer obligation.
    assert "What this exhibit shows" in html
    assert "82.0%" in html
    assert "78.8%" in html
    assert "75.2%" in html
    assert "82.4%" in html
    assert "spans the 80% bar" in html


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
    assert "point &plusmn; Wilson half-width" in html


def test_x1_degradation_table(tmp_path):
    html, _ = _build(tmp_path)
    # Degradation table powers verbatim from the JSON (at T=48, IC=0.04).
    assert "25.2%" in html  # alpha_estimation R power
    assert "31.8%" in html  # alpha_estimation E power
    assert "13.2%" in html  # hit_rate_P power
    assert "23.4%" in html  # sizing_skill_P power
    assert "deferred" in html  # drift_detection
    assert html.count("Wilson 95%") >= 4


def test_x1_registry_snippet_null_thresholds(tmp_path):
    html, _ = _build(tmp_path)
    # Null thresholds render as the no-tenure statement, not "null".
    assert "no tenure in the measured range suffices" in html
    assert "x1-registry" in html


def test_x1_script_loaded(tmp_path):
    html, out = _build(tmp_path)
    assert "assets/x1-atlas.js" in html
    assert (out / "assets" / "x1-atlas.js").exists()
