from pathlib import Path

from quant_allocator.site.build import build

REPO_ROOT = Path(__file__).resolve().parents[2]


def _build(tmp_path):
    out = tmp_path / "out"
    build(REPO_ROOT / "site", out)
    return (out / "x2.html").read_text(encoding="utf-8"), out


def test_x2_provenance_dark_and_standing_note(tmp_path):
    html, out = _build(tmp_path)
    # SYNTHETIC badge stays on (x2 is non-doctrine).
    assert "synthetic-badge" in html
    assert "SYNTHETIC DATA" in html
    # Dark default theme.
    assert 'data-default-theme="dark"' in html
    # Go-live box is replaced by the standing statement, not present.
    assert "golive-replaced" in html
    assert "golive-box" not in html
    assert "the thesis, not a product" in html
    assert "it never goes live" in html
    # Inlined JSON for the dials + spec link.
    assert 'id="card-data"' in html
    assert "specs/x2.html" in html
    assert (out / "specs" / "x2.html").exists()


def test_x2_dials_snap_values(tmp_path):
    html, _ = _build(tmp_path)
    for dial in ["ic", "half_life", "sizing", "T", "tier"]:
        assert 'data-dial="%s"' % dial in html
    # Snap-to-grid values present as button data-values (%g-formatted).
    assert 'data-value="0.04"' in html   # ic
    assert 'data-value="0.1"' in html    # ic
    assert 'data-value="36"' in html     # half_life or T
    assert 'data-value="0.8"' in html    # sizing
    assert 'data-value="120"' in html    # T
    assert 'data-value="R"' in html      # tier
    assert 'data-value="P"' in html


def test_x2_component_scaffolding_and_copy(tmp_path):
    html, _ = _build(tmp_path)
    # IntervalStat + VerdictChip + PowerGate per analytic.
    assert 'class="interval-stat"' in html
    assert 'class="verdict-chip"' in html
    assert 'class="power-gate"' in html
    # Closed gate with null threshold statement.
    assert "no threshold reached in the measured range" in html
    # Wilson half-width footnote shown.
    assert "Wilson" in html
    assert "half-width" in html
    # IC=0 column labeled false-alarm rate.
    assert "false-alarm rate" in html
    # The four analytic slots exist by name.
    for a in ["alpha", "sharpe", "hit_rate", "sizing_slope"]:
        assert 'data-analytic="%s"' % a in html


def test_x2_exhibit_explainer(tmp_path):
    html, _ = _build(tmp_path)
    assert "What this exhibit shows" in html


def test_x2_script_loaded(tmp_path):
    html, out = _build(tmp_path)
    assert "assets/x2-playground.js" in html
    assert (out / "assets" / "x2-playground.js").exists()
